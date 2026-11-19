import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, simpledialog
from tkinter import messagebox, filedialog
import json
import time
import base64
import os

TCP_PORT = 12345
UDP_PORT = 12346
MAX_FILE_SIZE = 5 * 1024 * 1024


class LANConnectClient:

    def __init__(self, window):

        self.window = window
        self.window.title("LANConnect")
        self.window.geometry("850x650")

        self.client = None
        self.reader = None
        self.username = None
        self.server_ip = None
        self.connected = False

        # Interactive TCP/IP demonstration state (chat UI remains unchanged)
        self.demo_window = None
        self.demo_message = ""
        self.demo_sender = ""
        self.demo_recipient = ""
        self.demo_step = 0
        self.demo_after_id = None
        self.demo_autoplay = False

        self.show_login_screen()

    # CLEAR WINDOW
    def clear_window(self):

        for widget in self.window.winfo_children():
            widget.destroy()

    # UDP SERVER DISCOVERY
    def discover_server(self):

        discovery = socket.socket(
            socket.AF_INET,
            socket.SOCK_DGRAM
        )

        discovery.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_BROADCAST,
            1
        )

        discovery.settimeout(2)

        try:
            discovery.sendto(
                b"LANCONNECT_DISCOVER",
                ("255.255.255.255", UDP_PORT)
            )

            response, address = discovery.recvfrom(1024)

            details = json.loads(response.decode())

            return details["server_ip"]

        except (socket.timeout, OSError, json.JSONDecodeError):
            return None

        finally:
            discovery.close()

    # LOGIN SCREEN
    def show_login_screen(self):

        self.clear_window()

        frame = tk.Frame(self.window, padx=35, pady=25)
        frame.pack(expand=True)

        tk.Label(
            frame,
            text="LANConnect",
            font=("Arial", 24, "bold")
        ).pack(pady=8)

        tk.Label(
            frame,
            text="LAN Communication & Monitoring"
        ).pack()

        tk.Label(frame, text="Username").pack(
            anchor="w", pady=(18, 3)
        )

        self.username_entry = tk.Entry(
            frame, font=("Arial", 12), width=30
        )
        self.username_entry.pack()

        tk.Label(frame, text="Password").pack(
            anchor="w", pady=(12, 3)
        )

        self.password_entry = tk.Entry(
            frame, font=("Arial", 12),
            width=30, show="*"
        )
        self.password_entry.pack()

        tk.Button(
            frame,
            text="Login",
            width=25,
            command=lambda: self.connect_to_server("login")
        ).pack(pady=(18, 5))

        tk.Button(
            frame,
            text="Register",
            width=25,
            command=lambda: self.connect_to_server("register")
        ).pack()

        tk.Label(
            frame,
            text="Start server3.py on the server laptop.",
            fg="gray"
        ).pack(pady=18)

    # CONNECT TO SERVER
    def connect_to_server(self, action):

        username = self.username_entry.get().strip()
        password = self.password_entry.get()

        if not username or not password:

            messagebox.showwarning(
                "Missing Details",
                "Enter username and password."
            )
            return

        self.server_ip = self.discover_server()

        if not self.server_ip:

            self.server_ip = simpledialog.askstring(
                "Server IP",
                "Enter server laptop IPv4 address:",
                parent=self.window
            )

        if not self.server_ip:
            return

        try:

            self.client = socket.socket(
                socket.AF_INET,
                socket.SOCK_STREAM
            )

            self.client.connect(
                (self.server_ip, TCP_PORT)
            )

            self.reader = self.client.makefile(
                "r", encoding="utf-8"
            )

            self.send_data({
                "action": action,
                "username": username,
                "password": password
            })

            response = json.loads(
                self.reader.readline()
            )

            if not response.get("ok"):

                messagebox.showerror(
                    "Authentication",
                    response.get("message", "Failed")
                )

                self.client.close()
                self.client = None
                return

            self.username = username
            self.connected = True

            self.show_chat_screen()

            threading.Thread(
                target=self.receive_messages,
                daemon=True
            ).start()

            self.send_data({"action": "history"})
            self.send_data({"action": "users"})

            self.window.after(
                1000,
                self.check_latency
            )

        except OSError as error:

            messagebox.showerror(
                "Connection Error",
                str(error)
            )

            if self.client:
                self.client.close()
                self.client = None

    # SEND JSON DATA
    def send_data(self, data):

        self.client.sendall(
            (json.dumps(data) + "\n").encode("utf-8")
        )

    # CHAT SCREEN
    def show_chat_screen(self):

        self.clear_window()

        self.window.title(
            f"LANConnect - {self.username}"
        )

        header = tk.Frame(
            self.window,
            padx=10,
            pady=8
        )

        header.pack(fill=tk.X)

        tk.Label(
            header,
            text=f"LANConnect | {self.username}",
            font=("Arial", 15, "bold")
        ).pack(side=tk.LEFT)

        tk.Button(
            header,
            text="Refresh Users",
            command=lambda: self.send_data({
                "action": "users"
            })
        ).pack(side=tk.RIGHT)

        main = tk.Frame(self.window)
        main.pack(
            fill=tk.BOTH,
            expand=True,
            padx=10,
            pady=5
        )

        left = tk.Frame(main)
        left.pack(
            side=tk.LEFT,
            fill=tk.BOTH,
            expand=True
        )

        right = tk.Frame(
            main,
            width=230,
            padx=12
        )

        right.pack(
            side=tk.RIGHT,
            fill=tk.Y
        )

        # CHAT AREA
        self.chat_area = scrolledtext.ScrolledText(
            left,
            wrap=tk.WORD,
            state="disabled",
            font=("Arial", 11)
        )

        self.chat_area.pack(
            fill=tk.BOTH,
            expand=True
        )

        self.chat_area.tag_config(
            "self", foreground="blue"
        )

        self.chat_area.tag_config(
            "other", foreground="green"
        )

        self.chat_area.tag_config(
            "system", foreground="gray"
        )

        # MESSAGE CONTROLS
        controls = tk.Frame(left)
        controls.pack(fill=tk.X, pady=7)

        tk.Label(
            controls,
            text="To:"
        ).pack(side=tk.LEFT)

        self.recipient = tk.StringVar(value="ALL")

        self.recipient_box = tk.OptionMenu(
            controls,
            self.recipient,
            "ALL"
        )

        self.recipient_box.pack(
            side=tk.LEFT,
            padx=4
        )

        self.message_entry = tk.Entry(
            controls,
            font=("Arial", 12)
        )

        self.message_entry.pack(
            side=tk.LEFT,
            fill=tk.X,
            expand=True,
            padx=4
        )

        self.message_entry.bind(
            "<Return>",
            lambda event: self.send_message()
        )

        tk.Button(
            controls,
            text="Send",
            command=self.send_message
        ).pack(side=tk.RIGHT)

        tk.Button(
            left,
            text="Send File",
            command=self.send_file
        ).pack(anchor="e")

        # ONLINE USERS
        tk.Label(
            right,
            text="Online Devices",
            font=("Arial", 12, "bold")
        ).pack(anchor="w")

        self.user_list = tk.Listbox(
            right,
            height=8,
            width=25
        )

        self.user_list.pack(
            fill=tk.X,
            pady=5
        )

        # NETWORK MONITOR
        tk.Label(
            right,
            text="Network Monitoring",
            font=("Arial", 12, "bold")
        ).pack(anchor="w", pady=(12, 3))

        self.monitor_label = tk.Label(
            right,
            text="Latency: Measuring...\nTCP Connection\nUDP Discovery",
            justify=tk.LEFT,
            anchor="w"
        )

        self.monitor_label.pack(anchor="w")

        # TCP/IP VISUALIZATION
        # Live TCP/IP Flow title with clickable hyperlink
        flow_title = tk.Frame(right)
        flow_title.pack(fill=tk.X, pady=(14, 4))

        tk.Label(
            flow_title,
            text="Live OSI Flow",
            font=("Arial", 12, "bold")
        ).pack(side=tk.LEFT)

        self.demo_link = tk.Label(
            flow_title,
            text="How it works?",
            fg="blue",
            cursor="hand2",
            font=("Arial", 9, "underline")
        )
        self.demo_link.pack(side=tk.RIGHT)

        self.demo_link.bind(
            "<Button-1>",
            lambda event: self.show_tcp_ip_demo()
        )

        self.flow_direction = tk.Label(
            right,
            text="Waiting for message...",
            fg="gray",
            justify=tk.LEFT,
            wraplength=205
        )

        self.flow_direction.pack(anchor="w")

        self.flow_labels = {}

        layer_names = [
            ("application", "1. Application Layer"),
            ("transport", "2. Transport Layer (TCP)"),
            ("internet", "3. Internet Layer (IP)"),
            ("network", "4. Network Access Layer")
        ]

        for key, title in layer_names:

            layer = tk.Label(
                right,
                text=title + "\nWaiting...",
                bg="#eeeeee",
                fg="#333333",
                justify=tk.LEFT,
                anchor="w",
                padx=6,
                pady=5,
                wraplength=205,
                relief=tk.GROOVE,
                bd=1
            )

            layer.pack(fill=tk.X, pady=2)

            self.flow_labels[key] = layer

        self.flow_queue = []
        self.flow_busy = False

        tk.Label(
            right,
            text=f"Server: {self.server_ip}:{TCP_PORT}",
            fg="gray",
            wraplength=190
        ).pack(anchor="w", pady=12)

        self.display_message(
            "Connected to LANConnect server.",
            "system"
        )

    # DISPLAY MESSAGE
    def display_message(self, message, tag="other"):

        if not hasattr(self, "chat_area"):
            return

        self.chat_area.config(state="normal")

        self.chat_area.insert(
            tk.END,
            message + "\n",
            tag
        )

        self.chat_area.config(state="disabled")
        self.chat_area.yview(tk.END)

    # RECEIVE MESSAGES
    def receive_messages(self):

        try:

            for line in self.reader:

                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue

                self.window.after(
                    0,
                    self.process_message,
                    data
                )

        except (OSError, ValueError):
            pass

        self.connected = False

        self.window.after(
            0,
            lambda: self.display_message(
                "Disconnected from server.",
                "system"
            )
        )

    # PROCESS SERVER RESPONSES
    def process_message(self, data):

        message_type = data.get("type")

        if message_type == "chat":

            sender = data.get("sender", "")
            recipient = data.get("recipient", "ALL")
            text = data.get("message", "")
            time_text = data.get("time", "")

            tag = (
                "self"
                if sender == self.username
                else "other"
            )

            destination = (
                "Group"
                if recipient == "ALL"
                else "Private"
            )

            self.display_message(
                f"[{time_text}] {sender} ({destination}): {text}",
                tag
            )

            direction = (
                "OUT"
                if sender == self.username
                else "IN"
            )

            self.queue_tcp_ip_flow(
                direction,
                sender,
                recipient,
                text
            )

        elif message_type == "system":

            self.display_message(
                data.get("message", ""),
                "system"
            )

        elif message_type == "users":

            self.update_user_list(
                data.get("users", [])
            )

        elif message_type == "history":

            for sender, recipient, message, time_text in data.get("messages", []):

                tag = (
                    "self"
                    if sender == self.username
                    else "other"
                )

                self.display_message(
                    f"[History {time_text}] {sender} -> {recipient}: {message}",
                    tag
                )

        elif message_type == "pong":

            latency = (
                time.time() - data.get("sent", time.time())
            ) * 1000

            self.monitor_label.config(
                text=f"Latency: {latency:.2f} ms\n"
                     f"Online devices: {self.user_list.size()}\n"
                     f"Transport: TCP\nDiscovery: UDP"
            )

        elif message_type == "file":

            self.receive_file(data)

    # UPDATE ONLINE USERS
    def update_user_list(self, users):

        self.user_list.delete(0, tk.END)

        menu = self.recipient_box["menu"]
        menu.delete(0, "end")

        menu.add_command(
            label="ALL",
            command=lambda: self.recipient.set("ALL")
        )

        for user in users:

            name = user["username"]

            self.user_list.insert(
                tk.END,
                f"{name}  {user['ip']}:{user['port']}"
            )

            if name != self.username:

                menu.add_command(
                    label=name,
                    command=lambda value=name:
                    self.recipient.set(value)
                )

    # TCP/IP VISUALIZATION QUEUE
    def queue_tcp_ip_flow(
        self, direction, sender, recipient, message
    ):

        self.flow_queue.append(
            (direction, sender, recipient, message)
        )

        self.demo_message = message
        self.demo_sender = sender
        self.demo_recipient = recipient
        if self.demo_window and self.demo_window.winfo_exists():
            self._reset_demo_for_message(message, sender, recipient)

        if not self.flow_busy:
            self.run_next_flow()

    # START VISUALIZATION
    def run_next_flow(self):

        if not self.flow_queue:
            self.flow_busy = False
            return

        self.flow_busy = True

        direction, sender, recipient, message = (
            self.flow_queue.pop(0)
        )

        if direction == "OUT":

            self.flow_direction.config(
                text=f"OUTGOING: {sender} -> {recipient}",
                fg="#1565c0"
            )

            steps = [
                (
                    "application",
                    "Application Data",
                    f'Message: "{message}"'
                ),
                (
                    "transport",
                    "TCP Segment",
                    "Source/Destination ports and TCP reliability"
                ),
                (
                    "internet",
                    "IP Packet",
                    "Source and destination IP addresses"
                ),
                (
                    "network",
                    "Network Frame",
                    "Frame prepared for local network transmission"
                )
            ]

            completion = "Encapsulation completed!"

        else:

            self.flow_direction.config(
                text=f"INCOMING: {sender} -> {self.username}",
                fg="#16803c"
            )

            steps = [
                (
                    "network",
                    "Network Frame Received",
                    "Frame received from local network"
                ),
                (
                    "internet",
                    "IP Packet Processed",
                    "IP header and destination processed"
                ),
                (
                    "transport",
                    "TCP Segment Processed",
                    "TCP data delivered in order"
                ),
                (
                    "application",
                    "Application Data Delivered",
                    f'Message: "{message}"'
                )
            ]

            completion = "Decapsulation completed!"

        self.animate_tcp_ip(steps, 0, completion)

    # ANIMATE EACH LAYER
    def animate_tcp_ip(self, steps, index, completion):

        if index >= len(steps):

            self.flow_direction.config(
                text=completion,
                fg="#16803c"
            )

            self.window.after(
                1100,
                self.run_next_flow
            )

            return

        key, title, detail = steps[index]

        for label in self.flow_labels.values():

            label.config(
                bg="#eeeeee",
                fg="#333333"
            )

        incoming = (
            "INCOMING"
            in self.flow_direction.cget("text")
        )

        self.flow_labels[key].config(
            text=f"{title}\n{detail}",
            bg="#c8e6c9" if incoming else "#bbdefb",
            fg="#17202a"
        )

        self.window.after(
            750,
            lambda: self.animate_tcp_ip(
                steps,
                index + 1,
                completion
            )
        )

    # INTERACTIVE OSI 7-LAYER PACKET JOURNEY
    # Only the demonstration popup is changed; the original LANConnect chat UI remains intact.
    def show_tcp_ip_demo(self):

        if self.demo_window and self.demo_window.winfo_exists():
            self.demo_window.lift()
            return

        self.demo_window = tk.Toplevel(self.window)
        self.demo_window.title("LANConnect - OSI 7-Layer Demonstration")
        self.demo_window.geometry("1120x850")
        self.demo_window.minsize(980, 760)
        self.demo_window.configure(bg="white")
        self.demo_window.protocol("WM_DELETE_WINDOW", self.close_tcp_ip_demo)

        tk.Label(
            self.demo_window,
            text="How a message travels through the OSI Model",
            font=("Arial", 17, "bold"), bg="white"
        ).pack(pady=(12, 2))

        self.demo_status = tk.Label(
            self.demo_window,
            text="Send a chat message, then use Previous, Next or Auto Play.",
            font=("Arial", 10), fg="#444444", bg="white"
        )
        self.demo_status.pack(pady=(0, 5))

        self.demo_canvas = tk.Canvas(
            self.demo_window, height=690, bg="white", highlightthickness=0
        )
        self.demo_canvas.pack(fill=tk.BOTH, expand=True, padx=8)
        self.demo_canvas.bind("<Configure>", lambda event: self._draw_packet_journey())

        controls = tk.Frame(self.demo_window, bg="white")
        controls.pack(pady=(4, 8))
        tk.Button(controls, text="Previous", width=11, command=self.demo_previous).pack(side=tk.LEFT, padx=5)
        tk.Button(controls, text="Next", width=11, command=self.demo_next).pack(side=tk.LEFT, padx=5)
        self.demo_play_button = tk.Button(controls, text="Auto Play", width=11, command=self.demo_toggle_autoplay)
        self.demo_play_button.pack(side=tk.LEFT, padx=5)
        tk.Button(controls, text="Reset", width=11, command=self.demo_reset).pack(side=tk.LEFT, padx=5)

        tk.Label(
            self.demo_window,
            text=("OSI is a 7-layer reference model. LANConnect sends chat over TCP/IP; "
                  "the OSI layers below explain the corresponding networking functions. "
                  "The server relays messages between clients; this is an educational visualization, not packet capture."),
            font=("Arial", 9), fg="#666666", bg="white", wraplength=1050
        ).pack(pady=(0, 8))

        self.demo_step = 0
        self._draw_packet_journey()

    def _reset_demo_for_message(self, message, sender, recipient):
        self.demo_message = message
        self.demo_sender = sender
        self.demo_recipient = recipient
        if self.demo_window and self.demo_window.winfo_exists():
            self._stop_demo_autoplay()
            self.demo_step = 0
            self._draw_packet_journey()

    def _journey_steps(self):
        return [
            "Application (Layer 7): the chat application creates the message.",
            "Presentation (Layer 6): data representation / encoding is prepared.",
            "Session (Layer 5): the application communication session is managed.",
            "Transport (Layer 4): TCP adds transport information; data becomes a segment.",
            "Network (Layer 3): IP addressing and routing information are applied; segment becomes a packet.",
            "Data Link (Layer 2): local link framing information is applied; packet becomes a frame.",
            "Physical (Layer 1): frame bits are transmitted over the physical medium.",
            "Network transmission: data travels to the LANConnect server, which relays the chat message.",
            "Physical (Layer 1): receiver obtains the incoming bits.",
            "Data Link (Layer 2): frame is interpreted and link-layer information is processed.",
            "Network (Layer 3): IP addressing information is processed.",
            "Transport (Layer 4): TCP reassembles and delivers the ordered data stream.",
            "Session (Layer 5): the communication session is maintained for the application.",
            "Presentation (Layer 6): data is interpreted in the required representation.",
            "Application (Layer 7): the original chat message reaches the receiving application."
        ]

    def _draw_packet_journey(self):
        if not self.demo_window or not self.demo_window.winfo_exists():
            return
        c = self.demo_canvas
        c.delete("all")
        steps = self._journey_steps()
        # Keep the animation index within its 15 valid stages (0..14).
        # This also protects redraws triggered by autoplay/window resizing.
        step = max(0, min(int(self.demo_step), len(steps) - 1))
        self.demo_step = step
        msg = self.demo_message or "Waiting for an actual LANConnect message"
        sender = self.demo_sender or "Sender device"
        receiver = self.demo_recipient or "Receiver device"
        if receiver == "ALL":
            receiver = "Group recipients"

        width = max(c.winfo_width(), 1000)
        center = width // 2
        left_x, right_x = 48, width - 438
        box_w, box_h, gap = 390, 54, 7
        ys = [112 + i * (box_h + gap) for i in range(7)]
        layers = [
            ("7  Application", "Chat message / user data", "#dbeafe", "#2563eb"),
            ("6  Presentation", "Data format, encoding, encryption", "#e0e7ff", "#4f46e5"),
            ("5  Session", "Session establishment and management", "#ede9fe", "#7c3aed"),
            ("4  Transport", "TCP segment — ports, sequencing, reliability", "#fef3c7", "#d97706"),
            ("3  Network", "IP packet — logical addressing and routing", "#ffedd5", "#ea580c"),
            ("2  Data Link", "Frame — MAC addressing and error detection", "#dcfce7", "#16a34a"),
            ("1  Physical", "Bits — electrical / radio / optical signals", "#cffafe", "#0891b2")
        ]

        c.create_text(left_x + box_w/2, 24, text=f"SENDER — ENCAPSULATION\n{sender}",
                      font=("Arial", 11, "bold"), fill="#2563eb")
        c.create_text(right_x + box_w/2, 24, text=f"RECEIVER — DECAPSULATION\n{receiver}",
                      font=("Arial", 11, "bold"), fill="#059669")
        c.create_line(left_x + box_w + 12, 50, right_x - 12, 50,
                      fill="#9ca3af", width=2, dash=(5, 4), arrow=tk.LAST)
        c.create_rectangle(center-55, 36, center+55, 64, fill="white", outline="#635bff", width=2)
        c.create_text(center, 50, text="LANConnect server", font=("Arial", 8, "bold"))

        # Seven sender layers (indices 0..6). Receiver decapsulation
        # starts at step 8 with Physical and finishes at step 14.
        sender_count = min(len(layers), max(0, step + 1))
        receiver_count = min(len(layers), max(0, step - 7))
        sender_texts = [
            f'Application data\n"{msg}"',
            "Presentation data\n[representation / encoding] + data",
            "Session data\n[session context] + presentation data",
            "TCP segment\n[TCP header] + upper-layer data",
            "IP packet\n[IP header] + [TCP segment]",
            "Data-link frame\n[Frame header/trailer] + [IP packet]",
            "Bits\n10110010 ... transmitted signals"
        ]
        receiver_texts = [
            f'Application data\n"{msg}"',
            "Presentation data\nData interpreted for the application",
            "Session data\nSession information handled",
            "TCP data\nTCP header processed; stream delivered",
            "IP packet\nIP header processed",
            "Data-link frame\nFrame header/trailer processed",
            "Bits\nIncoming bits received from medium"
        ]

        # Iterate only over entries that exist in every parallel layer list.
        layer_count = min(
            len(layers), len(ys), len(sender_texts), len(receiver_texts)
        )
        for i in range(layer_count):
            name, detail, fill, accent = layers[i]
            y = ys[i]
            sender_done = i < sender_count
            sender_current = (step == i and i < 7)
            sf = "#bfdbfe" if sender_done else fill
            c.create_rectangle(left_x, y, left_x+box_w, y+box_h, fill=sf,
                               outline=accent, width=3 if sender_current else 1)
            c.create_text(left_x+12, y+14, text=name, anchor="w",
                          fill=accent, font=("Arial", 9, "bold"))
            c.create_text(left_x+12, y+37,
                          text=sender_texts[i] if sender_done else detail,
                          anchor="w", fill="#222222", font=("Arial", 8))

            # Receiver decapsulation progresses bottom-up: Physical to Application.
            reverse_index = layer_count - 1 - i
            receiver_done = receiver_count > reverse_index
            receiver_current = (
                receiver_count == reverse_index + 1 and step >= 8
            )
            rf = "#a7f3d0" if receiver_done else "#f0fdf4"
            rtext = receiver_texts[i] if receiver_done else "Waiting for incoming data..."
            c.create_rectangle(right_x, y, right_x+box_w, y+box_h, fill=rf,
                               outline="#059669", width=3 if receiver_current else 1)
            c.create_text(right_x+12, y+14, text=name, anchor="w",
                          fill="#047857", font=("Arial", 9, "bold"))
            c.create_text(right_x+12, y+37, text=rtext,
                          anchor="w", fill="#222222", font=("Arial", 8))

            if i < 6:
                c.create_text(left_x+box_w/2, y+box_h+gap/2, text="↓",
                              fill="#64748b", font=("Arial", 12, "bold"))
                c.create_text(right_x+box_w/2, y+box_h+gap/2, text="↑",
                              fill="#64748b", font=("Arial", 12, "bold"))

        # Network path and moving packet marker.
        path_y = ys[-1] + box_h + 48
        c.create_text(center, path_y-23, text="NETWORK TRANSMISSION",
                      font=("Arial", 10, "bold"), fill="#111827")
        c.create_line(left_x+20, path_y+5, right_x+box_w-20, path_y+5,
                      fill="#64748b", width=3, arrow=tk.LAST)
        if step <= 6:
            packet_x = left_x + 28
            packet_labels = ["DATA", "PRES", "SESS", "TCP", "IP", "FRAME", "BITS"]
            packet_label = packet_labels[min(step, len(packet_labels) - 1)]
        elif step == 7:
            packet_x = center
            packet_label = "BITS"
        else:
            packet_x = right_x + box_w - 28
            packet_label = "BITS"
        c.create_oval(packet_x-22, path_y-12, packet_x+22, path_y+22,
                      fill="#635bff", outline="#4338ca", width=1)
        c.create_text(packet_x, path_y+5, text=packet_label,
                      fill="white", font=("Arial", 7, "bold"))

        c.create_rectangle(left_x, path_y+34, right_x+box_w, path_y+62,
                           fill="#f8fafc", outline="#d1d5db")
        c.create_text(left_x+10, path_y+48,
                      text=f'Actual LANConnect message: "{msg}"',
                      anchor="w", font=("Arial", 9), fill="#222222")
        self.demo_status.config(text=f"Step {step+1}/{len(steps)} — {steps[step]}")

    def demo_next(self):
        if self.demo_step < len(self._journey_steps()) - 1:
            self.demo_step += 1
            self._draw_packet_journey()
        else:
            self.demo_status.config(text="OSI journey complete — original message delivered.")

    def demo_previous(self):
        self._stop_demo_autoplay()
        if self.demo_step > 0:
            self.demo_step -= 1
            self._draw_packet_journey()

    def demo_toggle_autoplay(self):
        if self.demo_autoplay:
            self._stop_demo_autoplay()
            return
        self.demo_autoplay = True
        self.demo_play_button.config(text="Pause")
        self._demo_autoplay_tick()

    def _demo_autoplay_tick(self):
        if not self.demo_autoplay or not self.demo_window or not self.demo_window.winfo_exists():
            return
        if self.demo_step < len(self._journey_steps()) - 1:
            self.demo_step += 1
            self._draw_packet_journey()
            self.demo_after_id = self.demo_window.after(900, self._demo_autoplay_tick)
        else:
            self._stop_demo_autoplay()

    def _stop_demo_autoplay(self):
        self.demo_autoplay = False
        if self.demo_window and self.demo_window.winfo_exists():
            self.demo_play_button.config(text="Auto Play")
            if self.demo_after_id:
                try:
                    self.demo_window.after_cancel(self.demo_after_id)
                except tk.TclError:
                    pass
        self.demo_after_id = None

    def demo_reset(self):
        self._stop_demo_autoplay()
        self.demo_step = 0
        self._draw_packet_journey()

    def close_tcp_ip_demo(self):
        self._stop_demo_autoplay()
        if self.demo_window and self.demo_window.winfo_exists():
            self.demo_window.destroy()
        self.demo_window = None


    # SEND CHAT MESSAGE
    def send_message(self):

        message = self.message_entry.get().strip()

        if not message:
            return

        if message.lower() == "exit":
            self.close_connection()
            return

        try:

            self.send_data({
                "action": "chat",
                "recipient": self.recipient.get(),
                "message": message
            })

            self.message_entry.delete(0, tk.END)

        except OSError:

            self.display_message(
                "Unable to send message.",
                "system"
            )

    # SEND FILE
    def send_file(self):

        file_path = filedialog.askopenfilename(
            parent=self.window
        )

        if not file_path:
            return

        if os.path.getsize(file_path) > MAX_FILE_SIZE:

            messagebox.showwarning(
                "File Too Large",
                "Maximum file size is 5 MB."
            )

            return

        try:

            with open(file_path, "rb") as file:
                encoded_file = base64.b64encode(
                    file.read()
                ).decode("ascii")

            self.send_data({
                "action": "file",
                "recipient": self.recipient.get(),
                "filename": os.path.basename(file_path),
                "file_data": encoded_file
            })

        except (OSError, socket.error) as error:

            messagebox.showerror(
                "File Error",
                str(error)
            )

    # RECEIVE FILE
    def receive_file(self, data):

        filename = os.path.basename(
            data.get("filename", "received_file")
        )

        answer = messagebox.askyesno(
            "File Received",
            f"{data.get('sender')} sent {filename}. Save it?"
        )

        if not answer:
            return

        save_path = filedialog.asksaveasfilename(
            parent=self.window,
            initialfile=filename
        )

        if save_path:

            try:

                file_bytes = base64.b64decode(
                    data["file_data"]
                )

                with open(save_path, "wb") as file:
                    file.write(file_bytes)

                self.display_message(
                    f"Received {filename} from {data.get('sender')}.",
                    "system"
                )

            except (OSError, ValueError) as error:

                messagebox.showerror(
                    "Save Error",
                    str(error)
                )

    # LATENCY MEASUREMENT
    def check_latency(self):

        if self.connected:

            try:

                self.send_data({
                    "action": "ping",
                    "sent": time.time()
                })

                self.window.after(
                    5000,
                    self.check_latency
                )

            except OSError:

                self.display_message(
                    "Connection lost.",
                    "system"
                )

    # CLOSE CONNECTION
    def close_connection(self):

        self.connected = False

        try:

            if self.client:
                self.client.shutdown(socket.SHUT_RDWR)
                self.client.close()

        except OSError:
            pass

        self.close_tcp_ip_demo()
        self.window.destroy()


if __name__ == "__main__":

    window = tk.Tk()

    app = LANConnectClient(window)

    window.protocol(
        "WM_DELETE_WINDOW",
        app.close_connection
    )

    window.mainloop()