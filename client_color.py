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
            text="Live TCP/IP Flow",
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

    # INTERACTIVE TCP/IP PACKET JOURNEY
    # The chat screen and its existing controls are intentionally unchanged.
    def show_tcp_ip_demo(self):

        if self.demo_window and self.demo_window.winfo_exists():
            self.demo_window.lift()
            return

        self.demo_window = tk.Toplevel(self.window)
        self.demo_window.title("LANConnect - How a Message Travels")
        self.demo_window.geometry("1060x790")
        self.demo_window.minsize(900, 700)
        self.demo_window.configure(bg="white")
        self.demo_window.protocol("WM_DELETE_WINDOW", self.close_tcp_ip_demo)

        tk.Label(
            self.demo_window,
            text="How a message travels across the network",
            font=("Arial", 16, "bold"), bg="white"
        ).pack(pady=(12, 2))

        self.demo_status = tk.Label(
            self.demo_window,
            text="Send a chat message to visualize its journey.",
            font=("Arial", 10), fg="#444444", bg="white"
        )
        self.demo_status.pack(pady=(0, 5))

        self.demo_canvas = tk.Canvas(
            self.demo_window, width=1040, height=600,
            bg="white", highlightthickness=0
        )
        self.demo_canvas.pack(fill=tk.BOTH, expand=True, padx=8)

        controls = tk.Frame(self.demo_window, bg="white")
        controls.pack(pady=(4, 8))

        tk.Button(controls, text="Previous", width=11,
                  command=self.demo_previous).pack(side=tk.LEFT, padx=5)
        tk.Button(controls, text="Next", width=11,
                  command=self.demo_next).pack(side=tk.LEFT, padx=5)
        self.demo_play_button = tk.Button(
            controls, text="Auto Play", width=11,
            command=self.demo_toggle_autoplay
        )
        self.demo_play_button.pack(side=tk.LEFT, padx=5)
        tk.Button(controls, text="Reset", width=11,
                  command=self.demo_reset).pack(side=tk.LEFT, padx=5)

        tk.Label(
            self.demo_window,
            text=("Educational TCP/IP model view of the real chat message. "
                  "LANConnect clients communicate with the server, which relays messages. "
                  "The operating system performs the actual network encapsulation."),
            font=("Arial", 9), fg="#666666", bg="white", wraplength=1000
        ).pack(pady=(0, 8))

        self.demo_step = 0
        self._draw_packet_journey()

    def _reset_demo_for_message(self, message, sender, recipient):
        self.demo_message = message
        self.demo_sender = sender
        self.demo_recipient = recipient
        if self.demo_window and self.demo_window.winfo_exists():
            self.demo_step = 0
            self.demo_autoplay = False
            if self.demo_after_id:
                try:
                    self.demo_window.after_cancel(self.demo_after_id)
                except tk.TclError:
                    pass
                self.demo_after_id = None
            self.demo_play_button.config(text="Auto Play")
            self._draw_packet_journey()

    def _journey_steps(self):
        # Four-layer TCP/IP model: Application, Transport, Internet,
        # and Network Access. Physical bits are shown as transmission,
        # not as a separate TCP/IP layer.
        return [
            "Application layer creates the original chat data.",
            "Transport layer adds a TCP header: data becomes a TCP segment.",
            "Internet layer adds an IP header: segment becomes an IP packet.",
            "Network Access layer adds frame information: packet becomes a frame.",
            "The frame is transmitted across the LAN to the LANConnect server.",
            "The destination side receives the frame at Network Access.",
            "Internet layer processes and removes the IP header.",
            "Transport layer processes TCP and delivers the original data.",
            "Application layer receives the original chat message."
        ]

    def _draw_packet_journey(self):
        if not self.demo_window or not self.demo_window.winfo_exists():
            return

        c = self.demo_canvas
        c.delete("all")
        step = self.demo_step
        steps = self._journey_steps()
        msg = self.demo_message or "Your chat message will appear here"
        sender = self.demo_sender or "Device A"
        receiver = self.demo_recipient or "Device B"
        if receiver == "ALL":
            receiver = "Group recipients"

        # Reference-style device-to-device route, with the server relay shown
        # because LANConnect clients connect to the server rather than directly.
        c.create_text(150, 34, text="💻", font=("Arial", 27))
        c.create_text(150, 68, text=sender, font=("Arial", 10, "bold"))
        c.create_text(890, 34, text="💻", font=("Arial", 27))
        c.create_text(890, 68, text=receiver, font=("Arial", 10, "bold"))
        c.create_line(205, 42, 835, 42, fill="#555555", width=2,
                      dash=(6, 4), arrow=tk.LAST)
        c.create_rectangle(470, 18, 570, 48, outline="#635bff", width=2, fill="white")
        c.create_text(520, 33, text="Chat data", font=("Arial", 9, "bold"))
        c.create_text(520, 70, text="LANConnect server relays the message",
                      fill="#666666", font=("Arial", 9))

        # Four TCP/IP layers on each side.
        left_x, right_x = 75, 675
        box_w, box_h = 290, 66
        ys = [125, 215, 305, 395]
        layer_info = [
            ("Application", "Message / application data", "#dbeafe", "#2563eb"),
            ("Transport", "TCP header + data = TCP segment", "#e0e7ff", "#4f46e5"),
            ("Internet", "IP header + TCP segment = IP packet", "#fef3c7", "#d97706"),
            ("Network Access", "Frame header + IP packet = frame", "#ffedd5", "#ea580c")
        ]

        c.create_text(left_x + box_w/2, 96, text="SENDER — ENCAPSULATION",
                      font=("Arial", 11, "bold"), fill="#2563eb")
        c.create_text(right_x + box_w/2, 96, text="RECEIVER — DECAPSULATION",
                      font=("Arial", 11, "bold"), fill="#059669")

        # Sender stack: each completed step adds one header to the PDU.
        sender_active = min(max(step, 0), 3)
        receiver_active = None
        if step >= 5:
            receiver_active = min(step - 5, 3)

        sender_texts = [
            f'Application data\n"{msg}"',
            f'TCP segment\n[TCP header] + ["{msg}"]',
            f'IP packet\n[IP header] + [TCP segment]',
            f'Network frame\n[Frame header] + [IP packet]'
        ]
        receiver_texts = [
            'Application data\nOriginal message delivered',
            'TCP segment\nTCP header processed / removed',
            'IP packet\nIP header processed / removed',
            'Network frame\nFrame received'
        ]

        for i, (name, detail, fill, accent) in enumerate(layer_info):
            y = ys[i]
            # Sender blocks show the current PDU at each encapsulation stage.
            active_sender = step == i or (step > i and i <= 3)
            sender_fill = "#bfdbfe" if active_sender else fill
            sender_outline = "#2563eb" if step == i else accent
            c.create_rectangle(left_x, y, left_x + box_w, y + box_h,
                               fill=sender_fill, outline=sender_outline,
                               width=3 if step == i else 1)
            c.create_text(left_x + 12, y + 15, text=name, anchor="w",
                          fill=accent, font=("Arial", 10, "bold"))
            c.create_text(left_x + 12, y + 43,
                          text=sender_texts[i] if step >= i else detail,
                          anchor="w", fill="#222222", font=("Arial", 9))

            # Receiver side remains pending until transmission has happened,
            # then the same PDU is progressively decapsulated in reverse.
            rfill = "#d1fae5"
            routline = "#059669"
            rtext = "Waiting for frame..."
            if step >= 5:
                # Reverse mapping: frame, internet, transport, application.
                reverse_index = 3 - i
                if reverse_index <= (step - 5):
                    rfill = "#a7f3d0"
                    routline = "#059669"
                    rtext = receiver_texts[i]
                if step == 8 and i == 0:
                    rtext = f'Application data\n"{msg}"'
            c.create_rectangle(right_x, y, right_x + box_w, y + box_h,
                               fill=rfill, outline=routline,
                               width=3 if (step >= 5 and reverse_index == step - 5) else 1)
            c.create_text(right_x + 12, y + 15, text=name, anchor="w",
                          fill="#047857", font=("Arial", 10, "bold"))
            c.create_text(right_x + 12, y + 43, text=rtext,
                          anchor="w", fill="#222222", font=("Arial", 9))

            if i < 3:
                c.create_text(left_x + box_w/2, y + box_h + 11,
                              text="↓", fill="#666666", font=("Arial", 14))
                c.create_text(right_x + box_w/2, y + box_h + 11,
                              text="↑", fill="#666666", font=("Arial", 14))

        # Network transmission path: packet/frame moves left-to-right.
        c.create_text(520, 493, text="NETWORK TRANSMISSION",
                      font=("Arial", 11, "bold"), fill="#111827")
        c.create_line(120, 525, 920, 525, fill="#6b7280", width=3,
                      arrow=tk.LAST)
        c.create_text(520, 550,
                      text="Frame is carried as bits over the local network; server relays chat data",
                      font=("Arial", 9), fill="#555555")

        # Move packet along route according to the selected step.
        if step <= 3:
            packet_x = 120
            packet_label = ["DATA", "TCP", "IP", "FRAME"][step]
        elif step == 4:
            packet_x = 520
            packet_label = "FRAME"
        else:
            packet_x = 920
            packet_label = "FRAME"

        c.create_oval(packet_x - 25, 505, packet_x + 25, 545,
                      fill="#635bff", outline="#4338ca", width=1)
        c.create_text(packet_x, 525, text=packet_label,
                      fill="white", font=("Arial", 8, "bold"))

        # Show actual chat content without substituting a fixed demo message.
        c.create_rectangle(75, 572, 965, 596,
                           fill="#f8fafc", outline="#d1d5db")
        c.create_text(88, 584, text=f'Actual LANConnect message: "{msg}"',
                      anchor="w", font=("Arial", 9), fill="#222222")

        self.demo_status.config(
            text=f"Step {step + 1}/{len(steps)} — {steps[step]}"
        )

    def demo_next(self):
        if self.demo_step < len(self._journey_steps()) - 1:
            self.demo_step += 1
            self._draw_packet_journey()
        else:
            self.demo_status.config(text="Journey complete — original message delivered.")

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
            self.demo_after_id = self.demo_window.after(650, self._demo_autoplay_tick)
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