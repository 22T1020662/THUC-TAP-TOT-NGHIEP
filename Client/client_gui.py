import socket
import threading
import tkinter as tk
from tkinter import scrolledtext, filedialog, simpledialog, messagebox
from datetime import datetime
import os
import io
from PIL import Image, ImageTk, ImageOps
import time
from protocol import send_data, receive_data

PORT = 12345       # Port TCP để chat chính thức
UDP_PORT = 12346   # Port UDP dùng riêng để tự động tìm Server
HISTORY_FILE = "chat_history.txt" 

def auto_discover_server(udp_port=12346, timeout=3):
    """Phát tín hiệu UDP Broadcast để tìm IP của Server trong mạng LAN"""
    print("Đang quét tìm Server mạng LAN...")
    
    udp_client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    udp_client.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    udp_client.settimeout(timeout)
    try:
        # Gửi mật mã định danh tới toàn mạng LAN
        udp_client.sendto(b"DISCOVER_CHAT_SERVER", ('<broadcast>', udp_port))
        # Chờ Server phản hồi lại
        data, addr = udp_client.recvfrom(1024)
        if data == b"SERVER_HERE":
            print(f" Đã tìm thấy Server tại IP: {addr[0]}")
            return addr[0]  # Trả về IP tìm được
    except socket.timeout:
        print("⏱ Hết thời gian tìm kiếm, không nhận được phản hồi.")
    except Exception as e:
        print(f"Lỗi khi quét LAN: {e}")
    finally:
        udp_client.close()
    return None

# ===== THỰC HIỆN TỰ ĐỘNG TÌM IP SERVER =====
HOST = auto_discover_server(UDP_PORT)

if not HOST:
    messagebox.showwarning("Thông báo", "Không tìm thấy Server tự động trong mạng LAN.\nỨng dụng sẽ thoát.")
    exit()

# ===== KẾT NỐI TCP SAU KHI ĐÃ CÓ IP =====
client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    client.connect((HOST, PORT))
except Exception as e:
    messagebox.showerror("Lỗi", f"Tìm thấy Server ({HOST}) nhưng không kết nối TCP được:\n{e}")
    exit()
    
#=========
username = ""
avatar_path = None
avatar_hex = ""
last_typing_time = 0
typing_timer_id = None
image_refs = []
avatar_images = {}

# ===== LƯU / TẢI LỊCH SỬ =====
def save_chat_history(entry):
    try:
        with open(HISTORY_FILE, "a", encoding="utf-8") as f:
            f.write(entry + "\n")
    except Exception as e:
        print(f"Lỗi lưu lịch sử: {e}")

def load_chat_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        for line in lines:
            try:
                line = line.strip()
                # KIỂM TRA FORMAT
                if line.startswith("[") and "]" in line:
                    # TÁCH THỜI GIAN
                    time_end = line.index("]")
                    # PHẦN SAU TIME
                    content = line[time_end + 1:].strip()
                    # TÁCH USERNAME VÀ MESSAGE
                    if ":" in content:
                        sender, msg = content.split(":", 1)
                        # GỌI LẠI BUBBLE
                        display_text(
                            line,
                            sender.strip(),
                            save_history=False
                        )
            except Exception as e:
                print("Lỗi load history:", e)
# ===== UTILITY =====
def current_time():
    return datetime.now().strftime("%H:%M:%S")

def is_sender_self(sender):
    return sender and sender.strip().lower() == username.strip().lower()
# ===== DISPLAY =====
def get_avatar(sender, avatar_hex=None):
    try:
        if avatar_hex:
            image_bytes = bytes.fromhex(avatar_hex)
            image = Image.open(io.BytesIO(image_bytes))
        else:
            image = Image.new("RGB", (40, 40), color="gray")
        image = image.resize((40, 40))
        image = ImageOps.fit(image, (40, 40))
        photo = ImageTk.PhotoImage(image)
        avatar_images[sender] = photo
        return photo
    except:
        image = Image.new("RGB", (40, 40), color="gray")
        photo = ImageTk.PhotoImage(image)
        avatar_images[sender] = photo
        return photo

def display_text(msg, sender=None, avatar_hex=None, save_history=True):
    chat_display.config(state='normal')
    is_self = is_sender_self(sender)
    try:
        # ===== TÁCH TIME & NỘI DUNG =====
        if msg.startswith('[') and ']' in msg:
            time_end = msg.index(']')
            timestamp = msg[1:time_end]
            content = msg[time_end + 1:].strip()
            if sender and ":" in content:
                prefix, real_content = content.split(":", 1)
                if prefix.strip().lower() == sender.strip().lower():
                    content = real_content.strip()
        else:
            timestamp = current_time()
            content = msg
        if save_history:
            save_chat_history(f"[{timestamp}] {sender}: {content}")

        # ===== CONTAINER & BUBBLE =====
        container = tk.Frame(chat_display, bg="#f2f2f2")
        main_frame = tk.Frame(container, bg="#f2f2f2")
        main_frame.pack(fill=tk.BOTH, expand=True)

        avatar_photo = get_avatar(sender, avatar_hex)
        avatar_label = tk.Label(main_frame, image=avatar_photo, bg="#f2f2f2")
        avatar_label.image = avatar_photo

        bubble_color = "#0084ff" if is_self else "#ffffff"
        text_color = "white" if is_self else "black"
        bubble = tk.Frame(main_frame, bg=bubble_color, padx=12, pady=8)
        name_label = tk.Label(bubble, text="Bạn" if is_self else sender,
                                font=("Arial", 10, "bold"), bg=bubble_color, fg=text_color)
        name_label.pack(anchor="w")
        msg_label = tk.Label(bubble, text=content, font=("Arial", 12),
                                bg=bubble_color, fg=text_color, justify="left", wraplength=300)
        msg_label.pack(anchor="w")

        # Đảo vị trí Avatar nếu là mình gửi
        if is_self:
            avatar_label.pack(side=tk.RIGHT, padx=(5, 10))
            bubble.pack(side=tk.RIGHT, padx=(0, 5), pady=2)
            main_frame.pack(anchor="e") # Căn khung về bên phải
        else:
            avatar_label.pack(side=tk.LEFT, padx=(10, 5))
            bubble.pack(side=tk.LEFT, padx=(0, 10), pady=2)
            main_frame.pack(anchor="w") # Căn khung về bên trái

        # ===== CHÈN VÀO CHAT DISPLAY & CĂN LỀ DÒNG =====
        chat_display.insert(tk.END, "\n") 
        
        # Chèn khung tin nhắn
        chat_display.window_create(tk.END, window=container)
        
        # TẠO TAG CĂN LỀ CHO TIN NHẮN (QUAN TRỌNG)
        align_tag = "align_right" if is_self else "align_left"
        chat_display.tag_add(align_tag, "end-2c") 

        # Chèn thời gian ngay phía dưới
        chat_display.insert(tk.END, f"\n{timestamp}", "right_time" if is_self else "left_time")
        chat_display.insert(tk.END, "\n")

    except Exception as e:
        chat_display.insert(tk.END, f"Lỗi hiển thị: {e}\n")

    # Cấu hình các tag căn lề (có thể mang ra ngoài hàm khởi tạo 1 lần)
    chat_display.tag_config("align_right", justify="right")
    chat_display.tag_config("align_left", justify="left")
    chat_display.tag_config("left_time", foreground="gray", font=("Arial", 8), lmargin1=60)
    chat_display.tag_config("right_time", foreground="gray", font=("Arial", 8), justify="right", rmargin=60)
    chat_display.config(state='disabled')
    chat_display.see(tk.END)

def open_full_image(image_bytes, filename=None):
    try:
        # Tạo một cửa sổ mới (Toplevel) để phóng to ảnh
        top = tk.Toplevel(window)
        top.title(f"Xem ảnh: {filename if filename else 'Image'}")
        top.configure(bg="#222222")  # Nền tối giúp nổi bật ảnh

        # Đọc dữ liệu ảnh gốc từ bytes
        image = Image.open(io.BytesIO(image_bytes))
        
        # Giới hạn kích thước hiển thị theo màn hình
        screen_w = top.winfo_screenwidth() - 200
        screen_h = top.winfo_screenheight() - 200
        
        img_w, img_h = image.size
        if img_w > screen_w or img_h > screen_h:
            image.thumbnail((screen_w, screen_h))
            
        photo = ImageTk.PhotoImage(image)
        
        # Tạo Label hiển thị ảnh phóng to
        lbl_img = tk.Label(top, image=photo, bg="#222222")
        lbl_img.image = photo  # Giữ reference để không bị lỗi xóa bộ nhớ (Garbage Collection)
        lbl_img.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Hàm xử lý khi nhấn nút Tải xuống
        def save_image():
            default_name = filename if filename else "downloaded_image.jpg"
            save_path = filedialog.asksaveasfilename(
                initialfile=default_name,
                defaultextension=".jpg",
                filetypes=[("JPEG Image", "*.jpg"), ("PNG Image", "*.png"), ("All Files", "*.*")]
            )
            if save_path:
                try:
                    with open(save_path, "wb") as f:
                        f.write(image_bytes)  # Ghi trực tiếp bytes gốc để giữ nguyên chất lượng
                    messagebox.showinfo("Thành công", "Đã lưu ảnh về máy thành công!")
                except Exception as ex:
                    messagebox.showerror("Lỗi", f"Không thể lưu ảnh:\n{ex}")
        
        # Nút bấm Tải xuống đặt ở góc dưới cửa sổ phóng to
        btn_download = tk.Button(
            top, 
            text="📥 Tải ảnh xuống", 
            font=("Arial", 11, "bold"), 
            bg="#28a745", 
            fg="white", 
            command=save_image,
            relief="flat",
            pady=6,
            padx=15,
            cursor="hand2"
        )
        btn_download.pack(pady=(0, 15))
    except Exception as e:
        messagebox.showerror("Lỗi", f"Không thể mở ảnh: {e}")
        
def display_image(content_hex, sender, filename=None, avatar_hex=None, is_self=None, save_history=True):
    try:
        if is_self is None:
            is_self = is_sender_self(sender)
        timestamp = current_time()
        if save_history:
            save_chat_history(f"[{timestamp}] {sender}: [Ảnh] {filename if filename else ''}")
        # Xử lý ảnh chính
        image_bytes = bytes.fromhex(content_hex)
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail((200, 200))
        photo = ImageTk.PhotoImage(image)
        image_refs.append(photo)
        # Cấu trúc Container
        container = tk.Frame(chat_display, bg="#f2f2f2")
        main_frame = tk.Frame(container, bg="#f2f2f2")
        main_frame.pack(fill=tk.BOTH, expand=True)
        # Avatar
        avatar_photo = get_avatar(sender, avatar_hex)
        avatar_label = tk.Label(main_frame, image=avatar_photo, bg="#f2f2f2")
        avatar_label.image = avatar_photo
        # Khung chứa ảnh
        img_bubble = tk.Frame(main_frame, bg="#f2f2f2", padx=5, pady=5)
        label = tk.Label(img_bubble, image=photo, bg="#f2f2f2", cursor="hand2")
        label.pack()
        # Căn lề trái/phải
        if is_self:
            avatar_label.pack(side=tk.RIGHT, padx=(5, 10))
            img_bubble.pack(side=tk.RIGHT)
            main_frame.pack(anchor="e")
        else:
            avatar_label.pack(side=tk.LEFT, padx=(10, 5))
            img_bubble.pack(side=tk.LEFT)
            main_frame.pack(anchor="w")
        # click xem ảnh to
        label.bind("<Button-1>", lambda e: open_full_image(image_bytes, filename))

        chat_display.config(state='normal')
        chat_display.insert(tk.END, "\n")
        chat_display.window_create(tk.END, window=container)
        align_tag = "align_right" if is_self else "align_left"
        chat_display.tag_add(align_tag, "end-2c") 
        chat_display.insert(tk.END, f"\n{timestamp}", "right_time" if is_self else "left_time")
        chat_display.insert(tk.END, "\n")
        chat_display.config(state='disabled')
        chat_display.see(tk.END)
    except Exception as e:
        print(f"Lỗi hiển thị ảnh: {e}")

def display_file(sender, filename, avatar_hex=None, filepath=None, is_self=None, save_history=True):
    try:
        if is_self is None:
            is_self = is_sender_self(sender)
        timestamp = current_time()
        if save_history:
            save_chat_history(f"[{timestamp}] {sender}: [File] {filename}")
        container = tk.Frame(chat_display, bg="#f2f2f2")
        main_frame = tk.Frame(container, bg="#f2f2f2")
        main_frame.pack(fill=tk.BOTH, expand=True)
        avatar_photo = get_avatar(sender, avatar_hex)
        avatar_label = tk.Label(main_frame, image=avatar_photo, bg="#f2f2f2")
        bubble_color = "#0084ff" if is_self else "#ffffff"
        file_frame = tk.Frame(main_frame, bg=bubble_color, padx=10, pady=5)
        label_file = tk.Label(file_frame, text=f"📄 {filename}", bg=bubble_color, 
                                fg="white" if is_self else "blue", font=("Arial", 11, "underline"), cursor="hand2")
        label_file.pack(side=tk.LEFT)

        def trigger_save():
            # Hàm save_file cũ 
            save_path = filedialog.asksaveasfilename(initialfile=filename)
            if save_path and os.path.exists(filepath):
                with open(filepath, "rb") as fsrc, open(save_path, "wb") as fdst:
                    fdst.write(fsrc.read())
                messagebox.showinfo("Thành công", "Đã lưu file.")

        label_file.bind("<Button-1>", lambda e: trigger_save())
        if is_self:
            avatar_label.pack(side=tk.RIGHT, padx=(5, 10))
            file_frame.pack(side=tk.RIGHT)
            main_frame.pack(anchor="e")
        else:
            avatar_label.pack(side=tk.LEFT, padx=(10, 5))
            file_frame.pack(side=tk.LEFT)
            main_frame.pack(anchor="w")

        chat_display.config(state='normal')
        chat_display.insert(tk.END, "\n")
        chat_display.window_create(tk.END, window=container)
        chat_display.tag_add("align_right" if is_self else "align_left", "end-2c")
        chat_display.insert(tk.END, f"\n{timestamp}", "right_time" if is_self else "left_time")
        chat_display.insert(tk.END, "\n")
        chat_display.config(state='disabled')
        chat_display.see(tk.END)
    except Exception as e:
        print(f"Lỗi hiển thị file: {e}")

def display_emoji(content_hex, sender, avatar_hex=None, is_self=None, save_history=True):
    try:
        if is_self is None:
            is_self = is_sender_self(sender)
        timestamp = current_time()
        if save_history:
            save_chat_history(f"[{timestamp}] {sender}: [Emoji]")

        image_bytes = bytes.fromhex(content_hex)
        image = Image.open(io.BytesIO(image_bytes))
        image.thumbnail((40, 40))
        photo = ImageTk.PhotoImage(image)
        image_refs.append(photo)
        container = tk.Frame(chat_display, bg="#f2f2f2")
        main_frame = tk.Frame(container, bg="#f2f2f2")
        main_frame.pack(fill=tk.BOTH, expand=True)
        avatar_photo = get_avatar(sender, avatar_hex)
        avatar_label = tk.Label(main_frame, image=avatar_photo, bg="#f2f2f2")
        emoji_label = tk.Label(main_frame, image=photo, bg="#f2f2f2")
        emoji_label.image = photo

        if is_self:
            avatar_label.pack(side=tk.RIGHT, padx=(5, 10))
            emoji_label.pack(side=tk.RIGHT)
            main_frame.pack(anchor="e")
        else:
            avatar_label.pack(side=tk.LEFT, padx=(10, 5))
            emoji_label.pack(side=tk.LEFT)
            main_frame.pack(anchor="w")

        chat_display.config(state='normal')
        chat_display.insert(tk.END, "\n")
        chat_display.window_create(tk.END, window=container)
        chat_display.tag_add("align_right" if is_self else "align_left", "end-2c")
        chat_display.insert(tk.END, f"\n{timestamp}", "right_time" if is_self else "left_time")
        chat_display.insert(tk.END, "\n")
        chat_display.config(state='disabled')
        chat_display.see(tk.END)
    except Exception as e:
        print(f"Lỗi hiển thị emoji: {e}")

def on_typing(event):
    global last_typing_time
    now = time.time()
    if now - last_typing_time > 1.5:
        data = {
            "type": "typing",
            "from": username
        }
        try:
            send_data(client, data)
            last_typing_time = now
        except:
            pass

def display_typing(username_typing):
    global typing_timer_id
    typing_label.config(text=f"{username_typing} đang nhập...")

    if typing_timer_id:
        window.after_cancel(typing_timer_id)
    typing_timer_id = window.after(3000, clear_typing_label)  # Sau 3 giây tự xoá

def clear_typing_label():
    typing_label.config(text="")
    
# ===== SEND FUNCTIONS =====
def send_message():
    msg = entry_msg.get().strip()

    if not msg:
        return

    formatted_msg_send = f"[{current_time()}] {username}: {msg}"

    data = {
        "type": "text",
        "msg": formatted_msg_send,
        "from": username,
        "avatar": avatar_hex
    }

    try:
        send_data(client, data)

        # HIỂN THỊ NGAY TẠI CLIENT
        display_text(
            formatted_msg_send,
            sender=username,
            avatar_hex=avatar_hex,
            save_history=False
        )

    except Exception as e:
        messagebox.showerror(
            "Lỗi",
            f"Không gửi được:\n{e}"
        )
        return

    entry_msg.delete(0, tk.END)

    clear_typing_label()
    
def send_file(is_image=False):
    filetypes = [("Ảnh", "*.png *.jpg *.jpeg *.gif")] if is_image else [("Tất cả files", "*.*")]
    path = filedialog.askopenfilename(filetypes=filetypes)
    if not path:
        return
    MAX_FILE_SIZE = 5 * 1024 * 1024

    if os.path.getsize(path) > MAX_FILE_SIZE:
        messagebox.showwarning(
            "File quá lớn",
            "Chỉ cho phép file dưới 5MB."
        )
        return

    filename = os.path.basename(path)
    
    # ===== ẢNH =====
    if is_image:
        try:
            image = Image.open(path)
            if image.mode == "RGBA":
                image = image.convert("RGB")
        except Exception:
            messagebox.showerror(
                "Lỗi ảnh",
                "Không đọc được file ảnh."
            )
            return
        image.thumbnail((1280, 1280))
        img_bytes = io.BytesIO()
        image.save(
            img_bytes,
            format="JPEG",
            quality=70,
            optimize=True
        )
        content = img_bytes.getvalue().hex()
        filename = os.path.splitext(filename)[0] + ".jpg"

        # HIỂN THỊ 1 LẦN DUY NHẤT
        data = {
            "type": "image",
            "from": username,
            "filename": filename,
            "content": content
        }
    # ===== FILE =====
    else:
        with open(path, "rb") as f:
            content = f.read().hex()
        data = {
            "type": "file",
            "from": username,
            "filename": filename,
            "content": content
        }

    # ===== GỬI =====
    try:
        send_data(client, data)

        # ===== HIỂN THỊ LOCAL =====
        if is_image:
            display_image(
                content,
                username,
                filename=filename,
                avatar_hex=avatar_hex,
                is_self=True,
                save_history=False
            )

        else:
            display_file(
                username,
                filename,
                avatar_hex=avatar_hex,
                filepath=path,
                is_self=True,
                save_history=False
            )

    except Exception as e:
        messagebox.showerror(
            "Lỗi gửi file",
            f"Không gửi được file:\n{e}"
        )
        
def send_emoji_image(image_path):
    try:
        with open(image_path, "rb") as f:
            image_data = f.read()

        hex_data = image_data.hex()

        message = {
            "type": "emoji",
            "from": username,
            "content": hex_data,
            "avatar": avatar_hex
        }

        send_data(client, message)

        # ===== HIỂN THỊ LOCAL =====
        display_emoji(
            hex_data,
            username,
            avatar_hex=avatar_hex,
            is_self=True,
            save_history=False
        )

    except Exception as e:
        display_text(f"❌ Không gửi được emoji: {e}", "System")
        
def open_emoji_window():
    emoji_win = tk.Toplevel(window)
    emoji_win.title("Emoji")
    emoji_win.geometry("300x200")

    canvas = tk.Canvas(emoji_win)
    scrollbar = tk.Scrollbar(emoji_win, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas)

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )
    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)
    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    emoji_dir = "emoji"
    if not os.path.exists(emoji_dir):
        os.makedirs(emoji_dir)
        display_text(f"ℹ️ Đã tạo thư mục emoji: {os.path.abspath(emoji_dir)}", "info")

    row, col = 0, 0
    for fname in os.listdir(emoji_dir):
        if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
            path = os.path.join(emoji_dir, fname)
            try:
                img = Image.open(path)
                img.thumbnail((32, 32))
                photo = ImageTk.PhotoImage(img)
                image_refs.append(photo)
                btn = tk.Button(scrollable_frame, image=photo, command=lambda p=path: send_emoji_image(p))
                btn.grid(row=row, column=col, padx=5, pady=5)
                col += 1
                if col > 4:
                    col = 0
                    row += 1
            except:
                continue
            
# ===== UPDATE ONLINE LIST =====
def update_online_list(users):
    online_listbox.delete(0, tk.END)
    for user in users:
        if user == username:
            online_listbox.insert(tk.END, f"🟢 {user} (Bạn)")
        else:
            online_listbox.insert(tk.END, f"🟢 {user}")
    
    # Cập nhật số lượng hiển thị trên nhãn
    online_count_label.config(text=f"{len(users)} người online")
    
# ===== RECEIVE FUNCTION =====
def receive():
    while True:
        try:
            data = receive_data(client)
            if not data:
                raise Exception("Mất kết nối với server.")

            msg_type = data.get('type')
            sender = data.get("from")
            # Lấy avatar_hex từ gói tin (server cần forward dữ liệu này)
            av_hex = data.get("avatar") 
            is_self = is_sender_self(sender)

            if msg_type == 'request_username':
                send_data(client, {"username": username})

            elif msg_type == 'text':

            # KHÔNG HIỂN THỊ LẠI TIN NHẮN CỦA CHÍNH MÌNH
                if not is_self:
                    window.after(0, lambda: display_text(
                    data['msg'],
                    sender=sender,
                    avatar_hex=av_hex
                ))

                window.after(0, clear_typing_label)

            elif msg_type == 'image':

                # KHÔNG HIỂN THỊ LẠI ẢNH CỦA CHÍNH MÌNH
                if not is_self:
                    window.after(0, lambda: display_image(
                        data['content'],
                        sender,
                        filename=data.get('filename'),
                        avatar_hex=av_hex,
                        is_self=is_self
                ))

                window.after(0, clear_typing_label)

            elif msg_type == 'file':

                # KHÔNG HIỂN THỊ LẠI FILE CỦA CHÍNH MÌNH
                if not is_self:

                # Tạo thư mục received nếu chưa có
                    if not os.path.exists("received"):
                        os.makedirs("received")

                    timestamp = int(time.time())
                    filepath = f"received/{timestamp}_{data['filename']}"

                    with open(filepath, "wb") as f:
                        f.write(bytes.fromhex(data['content']))

                    window.after(0, lambda: display_file(
                        sender,
                        data['filename'],
                        avatar_hex=av_hex,
                        filepath=filepath,
                        is_self=is_self
                    ))

                window.after(0, clear_typing_label)

            elif msg_type == 'emoji':

                # KHÔNG HIỂN THỊ LẠI EMOJI CỦA CHÍNH MÌNH
                if not is_self:
                    window.after(0, lambda: display_emoji(
                        data['content'],
                        sender,
                        avatar_hex=av_hex,
                        is_self=is_self
                    ))

                window.after(0, clear_typing_label)

            elif msg_type == 'typing':
                if not is_self:
                    window.after(0, lambda: display_typing(sender))

            elif msg_type == 'online':
                users = data.get('users', [])
                window.after(0, lambda: update_online_list(users))
                
        except Exception as e:
            window.after(0, lambda err=str(e): display_text(f"❌ Lỗi: {err}", sender="System"))
            break
# ===== GUI SETUP =====
window = tk.Tk()
window.title("Client Chat")
window.geometry("700x600")

# ===== MAIN LAYOUT =====
main_frame = tk.Frame(window, bg="#e9eef5")
main_frame.pack(fill=tk.BOTH, expand=True)

# ===== LEFT CHAT AREA =====
chat_frame = tk.Frame(main_frame, bg="#ffffff")
chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10, pady=10)

# ===== RIGHT SIDEBAR =====
sidebar = tk.Frame(main_frame, width=200, bg="#dbe9ff")
sidebar.pack(side=tk.RIGHT, fill=tk.Y)

sidebar.pack_propagate(False)

# ===== SIDEBAR TITLE =====
online_title = tk.Label(
    sidebar,
    text="🟢 ONLINE USERS",
    font=("Arial", 12, "bold"),
    bg="#dbe9ff",
    fg="#003366"
)
online_title.pack(pady=10)
online_count_label = tk.Label(
    sidebar,
    text="0 người online",
    font=("Arial", 10),
    bg="#dbe9ff",
    fg="gray"
)
online_count_label.pack()
# ===== ONLINE LIST =====
online_listbox = tk.Listbox(
    sidebar,
    font=("Arial", 11),
    bg="white",
    fg="black",
    relief="flat"
)
online_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

# ===== CHAT DISPLAY =====
chat_display = scrolledtext.ScrolledText(
    chat_frame,
    wrap=tk.WORD,
    font=("Arial", 12),
    bg="#f2f2f2",
    bd=0
)
chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
chat_display.config(state='disabled')

# ===== TYPING LABEL =====
typing_label = tk.Label(
    chat_frame,
    text="",
    font=("Arial", 10),
    fg="gray",
    bg="#ffffff"
)
typing_label.pack(anchor='w', padx=5)

# ===== BOTTOM FRAME =====
bottom_frame = tk.Frame(chat_frame, bg="#ffffff")
bottom_frame.pack(fill=tk.X)

# ===== ENTRY =====
entry_msg = tk.Entry(
    bottom_frame,
    font=("Arial", 12),
    relief="flat",
    bg="#ffffff"
)

entry_msg.bind("<Key>", on_typing)
entry_msg.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=8, padx=(0, 5))
entry_msg.bind("<Return>", lambda e: send_message())

# ===== SEND BUTTON =====
btn_send = tk.Button(
    bottom_frame,
    text="Gửi",
    font=("Arial", 11, "bold"),
    command=send_message,
    bg="#007bff",
    fg="white",
    relief="flat",
    padx=15
)
btn_send.pack(side=tk.LEFT, padx=(5, 0))

# ===== IMAGE BUTTON =====
btn_image = tk.Button(
    bottom_frame,
    text="🖼",
    font=("Arial", 12),
    command=lambda: send_file(True),
    bg="#cfe2ff",
    relief="flat"
)
btn_image.pack(side=tk.LEFT, padx=(5, 0))

# ===== FILE BUTTON =====
btn_file = tk.Button(
    bottom_frame,
    text="📄",
    font=("Arial", 12),
    command=lambda: send_file(False),
    bg="#ffe4b5",
    relief="flat"
)
btn_file.pack(side=tk.LEFT, padx=(5, 0))

# ===== EMOJI BUTTON =====
btn_emoji = tk.Button(
    bottom_frame,
    text="😃",
    font=("Arial", 12),
    command=open_emoji_window,
    bg="#d8f3c3",
    relief="flat"
)
btn_emoji.pack(side=tk.LEFT, padx=(5, 0))
# ===== LOGIN =====
while True:
    username = simpledialog.askstring(
        "Tên đăng nhập",
        "Nhập tên của bạn:"
    )
    if not username or not username.strip():
        messagebox.showwarning(
            "Cảnh báo",
            "Bạn cần nhập tên để tiếp tục."
        )
        continue
    if " " in username:
        messagebox.showwarning(
            "Tên không hợp lệ",
            "Tên không được chứa khoảng trắng."
        )
        continue
    choose_avatar = messagebox.askyesno(
        "Avatar",
        "Bạn có muốn chọn avatar không?"
    )
    if choose_avatar:
        avatar_path = filedialog.askopenfilename(
            filetypes=[("Ảnh", "*.png *.jpg *.jpeg")]
        )
        if avatar_path:
            with open(avatar_path, "rb") as f:
                avatar_hex = f.read().hex()

    send_data(client, {
        "username": username,
        "avatar": avatar_hex
    })

    # Chờ phản hồi từ server
    data = receive_data(client)

    if data.get("type") == "username_taken":
        messagebox.showerror(
            "Tên đã tồn tại",
            "Tên này đã được người khác sử dụng. Vui lòng nhập tên khác."
        )
        continue
    elif data.get("type") == "invalid_username":
        messagebox.showerror(
            "Tên không hợp lệ",
            "Tên không được chứa khoảng trắng hoặc rỗng."
        )
        continue
    else:
        window.title(f"Client Chat - {username}")
        break
# ===== START CLIENT =====
threading.Thread(target=receive, daemon=True).start()
load_chat_history()

def on_close():
    try:
        client.close()
    except:
        pass
    window.destroy()

window.protocol("WM_DELETE_WINDOW", on_close)
window.mainloop()