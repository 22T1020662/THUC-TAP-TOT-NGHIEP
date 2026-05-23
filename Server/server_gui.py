import socket
import threading
import tkinter as tk
from tkinter import scrolledtext
from datetime import datetime
import time
from protocol import send_data, receive_data

# ================= CONFIG =================
HOST = '0.0.0.0'
PORT = 12345        # Port TCP để chat chính thức
UDP_PORT = 12346    # Port UDP lắng nghe tín hiệu tìm kiếm tự động từ Client

# ================= SERVER SOCKET =================
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(10)

# ================= DATA =================
clients = {}
avatars = {}
login_times = {}

# ================= GUI =================
root = tk.Tk()
root.title("🔌 TCP Chat Server")
root.geometry("750x550")

title = tk.Label(
    root,
    text="TCP CHAT SERVER",
    font=("Arial", 16, "bold"),
    fg="blue"
)
title.pack(pady=5)

# ===== LOG =====
log_area = scrolledtext.ScrolledText(
    root,
    width=90,
    height=20,
    font=("Consolas", 10)
)
log_area.pack(padx=10, pady=5)

# ===== ONLINE USERS =====
online_label = tk.Label(
    root,
    text="👥 Online Users",
    font=("Arial", 12, "bold")
)
online_label.pack()

online_count_label = tk.Label(
    root,
    text="0 users online",
    font=("Arial", 10),
    fg="gray"
)
online_count_label.pack()

online_list = tk.Listbox(
    root,
    width=60,
    height=10,
    font=("Arial", 10)
)
online_list.pack(padx=10, pady=5)

# ================= FUNCTIONS =================
def log(msg):
    timestamp = datetime.now().strftime("%H:%M:%S")
    log_area.insert(tk.END, f"[{timestamp}] {msg}\n")
    log_area.yview(tk.END)

def update_online_list():
    online_list.delete(0, tk.END)

    online_count_label.config(
        text=f"{len(login_times)} users online"
    )
    for username, login_time in login_times.items():
        online_list.insert(
            tk.END,
            f"🟢 {username} - Login: {login_time}"
        )

def broadcast(data, exclude=None):
    disconnected = []
    for client_socket in list(clients.keys()):
        if client_socket == exclude:
            continue
        try:
            send_data(client_socket, data)
        except:
            disconnected.append(client_socket)
    for dc in disconnected:
        remove_client(dc)

def broadcast_online_users():
    data = {
        "type": "online",
        "users": list(login_times.keys())
    }
    broadcast(data)

def remove_client(client_socket):
    if client_socket in clients:
        username = clients[client_socket]
        log(f"❌ {username} disconnected")
        login_times.pop(username, None)
        avatars.pop(username, None)
        clients.pop(client_socket, None)
        try:
            client_socket.close()
        except:
            pass

        update_online_list()
        broadcast_online_users()

# ================= AUTO DISCOVERY SYSTEM (UDP) =================
def udp_broadcast_responder():
    """Luồng chạy ngầm xử lý phản hồi IP cho các Client trong mạng LAN"""
    udp_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Cho phép bind chung port nếu cần thiết tái khởi động nhanh
    udp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        udp_server.bind(("", UDP_PORT))
        log(f"📡 UDP Discovery: Đang mở cổng {UDP_PORT} hỗ trợ Client dò tìm...")
    except Exception as e:
        log(f"⚠️ Lỗi khởi động cổng UDP Discovery: {e}")
        return
    while True:
        try:
            data, addr = udp_server.recvfrom(1024)
            # Kiểm tra mã bắt tay định danh từ Client gửi tới
            if data == b"DISCOVER_CHAT_SERVER":
                # Gửi tín hiệu phản hồi xác nhận vị trí
                udp_server.sendto(b"SERVER_HERE", addr)
                log(f"🔍 Đã định vị và phản hồi IP Server cho Client tại: {addr[0]}")
        except Exception as e:
            # Ghi nhận log trực tiếp lên giao diện Server nếu luồng gặp trục trặc
            root.after(0, lambda: log(f"⚠️ Lỗi luồng UDP Discovery: {e}"))
            break

# ================= HANDLE CLIENT =================
def handle_client(client_socket, addr):
    username = None
    try:
        log(f"🔗 New connection: {addr}")
        # ===== LOGIN =====
        while True:
            data = receive_data(client_socket)
            if not data:
                return
            if "username" in data:
                name = data["username"].strip()

                # ===== CHECK USERNAME =====
                if not name or " " in name:
                    send_data(
                        client_socket,
                        {"type": "invalid_username"}
                    )
                    continue

                if name in login_times:
                    send_data(
                        client_socket,
                        {"type": "username_taken"}
                    )
                    continue

                # ===== LOGIN SUCCESS =====
                username = name
                avatar = data.get("avatar", "")
                avatars[username] = avatar
                clients[client_socket] = username
                login_times[username] = datetime.now().strftime("%H:%M:%S")

                send_data(client_socket, {"type": "ok"})
                log(f"✅ {username} joined")
                update_online_list()
                broadcast_online_users()

                # ===== THÔNG BÁO THAM GIA =====
                join_msg = {
                    "type": "text",
                    "msg": f"[{datetime.now().strftime('%H:%M:%S')}] 🔔 {username} joined the chat",
                    "from": "SERVER"
                }
                broadcast(join_msg)
                break

        # ================= CHAT LOOP =================
        while True:
            data = receive_data(client_socket)
            if not data:
                break
            msg_type = data.get("type")
            
            # ===== TEXT =====
            if msg_type == "text":
                msg = data.get("msg", "")
                log(f"💬 {msg}")
                # ===== PRIVATE CHAT =====
                if msg.startswith("/private"):
                    parts = msg.split(" ", 2)
                    if len(parts) < 3:
                        send_data(client_socket, {
                            "type": "text",
                            "msg": "[SERVER] Sai cú pháp. Dùng: /private username message",
                            "from": "SERVER"
                        })
                        continue

                    target_user = parts[1]
                    private_msg = parts[2]
                    found = False

                    for sock, user in clients.items():
                        if user == target_user:

                            # ===== GỬI CHO NGƯỜI NHẬN =====
                            send_data(sock, {
                                "type": "text",
                                "msg": f"[PRIVATE] {username}: {private_msg}",
                                "from": username,
                                "avatar": avatars.get(username, "")
                            })

                            # ===== GỬI LẠI CHO NGƯỜI GỬI =====
                            send_data(client_socket, {
                                "type": "text",
                                "msg": f"[PRIVATE to {target_user}] {private_msg}",
                                "from": username,
                                "avatar": avatars.get(username, "")
                            })
                            found = True
                            break

                    if not found:
                        send_data(client_socket, {
                            "type": "text",
                            "msg": f"[SERVER] Không tìm thấy user {target_user}",
                            "from": "SERVER"
                        })
                    continue

                # ===== TIN NHẮN THƯỜNG =====
                data["avatar"] = avatars.get(username, "")
                broadcast(data)

            # ===== IMAGE =====
            elif msg_type == "image":
                log(f"🖼 {username} sent image: {data.get('filename')}")
                data["avatar"] = avatars.get(username, "")
                broadcast(data)

            # ===== FILE =====
            elif msg_type == "file":
                log(f"📄 {username} sent file: {data.get('filename')}")
                data["avatar"] = avatars.get(username, "")
                broadcast(data)

            # ===== EMOJI =====
            elif msg_type == "emoji":
                log(f"😃 {username} sent emoji")
                data["avatar"] = avatars.get(username, "")
                broadcast(data)

            # ===== TYPING =====
            elif msg_type == "typing":
                data["avatar"] = avatars.get(username, "")
                broadcast(data, exclude=client_socket)
    except Exception as e:
        log(f"⚠️ Error: {e}")
    finally:
        if username:
            leave_msg = {
                "type": "text",
                "msg": f"[{datetime.now().strftime('%H:%M:%S')}] 🔔 {username} left the chat",
                "from": "SERVER"
            }
            broadcast(leave_msg, exclude=client_socket)
        remove_client(client_socket)

# ================= ACCEPT CONNECTIONS =================
def accept_connections():
    log(f"🟢 Server running on {HOST}:{PORT}")
    while True:
        try:
            client_socket, addr = server.accept()
            threading.Thread(
                target=handle_client,
                args=(client_socket, addr),
                daemon=True
            ).start()
        except Exception as e:
            log(f"⚠️ Accept error: {e}")

# ================= START THREADS =================
# Khởi chạy luồng tiếp nhận TCP kết nối chính từ Client
threading.Thread(
    target=accept_connections,
    daemon=True
).start()

# Khởi chạy luồng xử lý UDP Discovery để Client tự tìm thấy IP Server
threading.Thread(
    target=udp_broadcast_responder,
    daemon=True
).start()

# Khởi động giao diện hiển thị chính
root.mainloop()