# LANConnect – adapted from your OS chat project

This version reuses the original project idea and Tkinter chat-window style from:
- `server3.py`
- `client_color.py`

It expands the simple TCP broadcast chat into a Computer Networks project.

## Project structure

```text
LANConnect_OS_Adapted/
│
├── server3.py
├── client_color.py
├── lanconnect.db       # created automatically when server starts
├── simulations/
│   ├── crc.py
│   └── subnetting.py
└── README.md
```

## Requirements
- Python 3.9+
- Tkinter (included with most standard Windows Python installations)
- No pip packages required

## Run the server
Open a terminal in this folder:

```bash
python server3.py
```

Keep the server terminal open.

## Run a client
Open another terminal:

```bash
python client_color.py
```

Register a new username and password, then log in.

Run the same client on other laptops connected to the same Wi-Fi. The client first tries UDP broadcast discovery. If discovery is blocked, it asks for the server laptop's IPv4 address.

## Find the server IP on Windows
On the server laptop, run:

```bash
ipconfig
```

Find the IPv4 Address under the active Wi-Fi adapter.

If Windows Firewall asks, allow Python on private networks. Both laptops must be on the same local network. Some guest Wi-Fi networks block device-to-device communication.

## Features in this version
- TCP client-server communication
- Multiple connected clients using threads
- UDP broadcast server discovery
- Username registration and login
- Password hashes stored in SQLite
- Group chat and private one-to-one chat
- Online users with IP addresses and port numbers
- File sharing (maximum 5 MB in this demo)
- Message history stored in SQLite
- Application-level round-trip latency display
- CRC and subnetting command-line demonstrations

## Important limitations for your project report
- The password hashing is SHA-256 for classroom demonstration, not a production password-storage scheme.
- Chat and files are not encrypted. Use only on a trusted LAN.
- Latency is application-level round-trip time, not a pure ICMP ping.
- Bandwidth and real packet loss measurement are not implemented yet.
- CRC and subnetting are standalone learning demonstrations.
- ARP, Stop-and-Wait, Go-Back-N and Selective Repeat are not implemented in this version.
