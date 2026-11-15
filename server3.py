import socket
import threading
import datetime
import json
import sqlite3
import hashlib

HOST = "0.0.0.0"
TCP_PORT = 12345
UDP_PORT = 12346
DATABASE = "lanconnect.db"

clients = {}
lock = threading.Lock()


def get_database():
    connection = sqlite3.connect(DATABASE)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT NOT NULL
        )
    """)

    connection.execute("""
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sender TEXT,
            recipient TEXT,
            message TEXT,
            time TEXT
        )
    """)

    connection.commit()
    return connection


def send_data(client_socket, data):
    client_socket.sendall(
        (json.dumps(data) + "\n").encode("utf-8")
    )


def broadcast(data, exclude=None):
    with lock:
        connected = [
            info["socket"]
            for name, info in clients.items()
            if name != exclude
        ]

    for client in connected:
        try:
            send_data(client, data)
        except OSError:
            pass


def get_online_users():
    with lock:
        return [
            {
                "username": name,
                "ip": info["address"][0],
                "port": info["address"][1]
            }
            for name, info in clients.items()
        ]


def send_user_list():
    broadcast({
        "type": "users",
        "users": get_online_users()
    })


def remove_client(client_socket, username):
    if username:
        with lock:
            if (username in clients and
                    clients[username]["socket"] is client_socket):
                del clients[username]

        now = datetime.datetime.now().strftime("%H:%M")

        broadcast({
            "type": "system",
            "message": f"[{now}] {username} left the chat."
        })

        send_user_list()
        print(username, "disconnected")

    try:
        client_socket.close()
    except OSError:
        pass


def save_message(sender, recipient, message):
    connection = get_database()
    now = datetime.datetime.now().strftime("%H:%M")

    connection.execute(
        """INSERT INTO messages(sender, recipient, message, time)
           VALUES (?, ?, ?, ?)""",
        (sender, recipient, message, now)
    )

    connection.commit()
    connection.close()

    return now


def handle_client(client_socket, address):
    username = None
    reader = client_socket.makefile("r", encoding="utf-8")

    try:
        for line in reader:
            try:
                data = json.loads(line)
            except json.JSONDecodeError:
                continue

            action = data.get("action")

            # LOGIN AND REGISTRATION
            if action in ("register", "login"):

                requested_name = data.get("username", "").strip()
                password = data.get("password", "")

                if not requested_name or not password:
                    send_data(client_socket, {
                        "type": "auth",
                        "ok": False,
                        "message": "Username and password required."
                    })
                    continue

                connection = get_database()

                row = connection.execute(
                    "SELECT password FROM users WHERE username=?",
                    (requested_name,)
                ).fetchone()

                password_hash = hashlib.sha256(
                    password.encode()
                ).hexdigest()

                if action == "register":

                    if row:
                        ok = False
                        message = "Username already exists."

                    else:
                        connection.execute(
                            "INSERT INTO users VALUES (?, ?)",
                            (requested_name, password_hash)
                        )

                        connection.commit()

                        ok = True
                        message = "Registration successful."

                else:
                    ok = bool(row and row[0] == password_hash)

                    message = (
                        "Login successful."
                        if ok else "Invalid username or password."
                    )

                connection.close()

                if ok:
                    with lock:
                        if requested_name in clients:
                            ok = False
                            message = "User already logged in."

                        else:
                            username = requested_name

                            clients[username] = {
                                "socket": client_socket,
                                "address": address
                            }

                send_data(client_socket, {
                    "type": "auth",
                    "ok": ok,
                    "message": message,
                    "username": requested_name
                })

                if ok:
                    now = datetime.datetime.now().strftime("%H:%M")

                    broadcast({
                        "type": "system",
                        "message": f"[{now}] {username} joined the chat."
                    }, exclude=username)

                    send_user_list()

                continue

            if not username:
                send_data(client_socket, {
                    "type": "system",
                    "message": "Please login first."
                })
                continue

            # CHAT
            if action == "chat":

                message = data.get("message", "").strip()
                recipient = data.get("recipient", "ALL")

                if not message:
                    continue

                now = save_message(
                    username, recipient, message
                )

                packet = {
                    "type": "chat",
                    "sender": username,
                    "recipient": recipient,
                    "message": message,
                    "time": now
                }

                if recipient == "ALL":
                    broadcast(packet)

                else:
                    with lock:
                        target = clients.get(recipient)

                    if target:
                        try:
                            send_data(target["socket"], packet)
                        except OSError:
                            pass

                    send_data(client_socket, packet)

            # ONLINE USERS
            elif action == "users":

                send_data(client_socket, {
                    "type": "users",
                    "users": get_online_users()
                })

            # CHAT HISTORY
            elif action == "history":

                connection = get_database()

                rows = connection.execute("""
                    SELECT sender, recipient, message, time
                    FROM messages
                    WHERE sender = ?
                    OR recipient = ?
                    OR recipient = 'ALL'
                    ORDER BY id DESC LIMIT 50
                """, (username, username)).fetchall()

                connection.close()

                send_data(client_socket, {
                    "type": "history",
                    "messages": rows[::-1]
                })

            # LATENCY TEST
            elif action == "ping":

                send_data(client_socket, {
                    "type": "pong",
                    "sent": data.get("sent")
                })

            # FILE SHARING
            elif action == "file":

                recipient = data.get("recipient", "ALL")

                packet = {
                    "type": "file",
                    "sender": username,
                    "filename": data.get("filename", "shared_file"),
                    "file_data": data.get("file_data", "")
                }

                if recipient == "ALL":

                    broadcast(packet, exclude=username)

                    send_data(client_socket, {
                        "type": "system",
                        "message": "File shared with all users."
                    })

                else:
                    with lock:
                        target = clients.get(recipient)

                    if target:
                        send_data(target["socket"], packet)

                        send_data(client_socket, {
                            "type": "system",
                            "message": f"File sent to {recipient}."
                        })

                    else:
                        send_data(client_socket, {
                            "type": "system",
                            "message": "User is not online."
                        })

    except (ConnectionResetError, OSError):
        pass

    finally:
        remove_client(client_socket, username)


# UDP SERVER DISCOVERY
def discover_server():

    discovery_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    discovery_socket.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    discovery_socket.bind(("", UDP_PORT))

    print("UDP discovery running...")

    while True:
        try:
            message, address = discovery_socket.recvfrom(1024)

            if message.decode(errors="ignore") == "LANCONNECT_DISCOVER":

                reply = json.dumps({
                    "server_ip": get_local_ip(),
                    "tcp_port": TCP_PORT
                })

                discovery_socket.sendto(
                    reply.encode(),
                    address
                )

        except OSError:
            continue


def get_local_ip():

    test_socket = socket.socket(
        socket.AF_INET,
        socket.SOCK_DGRAM
    )

    try:
        test_socket.connect(("8.8.8.8", 80))
        ip = test_socket.getsockname()[0]

    except OSError:
        ip = "127.0.0.1"

    finally:
        test_socket.close()

    return ip


# START SERVER
def start_server():

    threading.Thread(
        target=discover_server,
        daemon=True
    ).start()

    server = socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    )

    server.setsockopt(
        socket.SOL_SOCKET,
        socket.SO_REUSEADDR,
        1
    )

    server.bind((HOST, TCP_PORT))
    server.listen()

    print("================================")
    print("       LANConnect Server")
    print("================================")
    print("Server IP:", get_local_ip())
    print("TCP Port:", TCP_PORT)
    print("Waiting for clients...")

    try:
        while True:

            client_socket, address = server.accept()

            print("Connected:", address)

            thread = threading.Thread(
                target=handle_client,
                args=(client_socket, address),
                daemon=True
            )

            thread.start()

    except KeyboardInterrupt:
        print("Server shutting down.")

    finally:
        server.close()


if __name__ == "__main__":
    get_database().close()
    start_server()