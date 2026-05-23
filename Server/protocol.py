import json
import struct
from cryptography.fernet import Fernet

# Dán chuỗi  vừa tạo để mã hóa
SHARED_SECRET_KEY = b"S0Y5Iw3qZOht8Fef-67sReiszN0rN_lpF6BEbzH-sVs=" 
cipher = Fernet(SHARED_SECRET_KEY)

def send_data(sock, data):
    json_data = json.dumps(data).encode('utf-8')

    # MÃ HÓA
    encrypted = cipher.encrypt(json_data)

    header = struct.pack('>I', len(encrypted))
    sock.sendall(header + encrypted)

def receive_data(sock):
    try:
        header = b''
        while len(header) < 4:
            chunk = sock.recv(4 - len(header))
            if not chunk:
                return None
            header += chunk

        msg_len = struct.unpack('>I', header)[0]

        chunks = []
        bytes_recd = 0

        while bytes_recd < msg_len:
            chunk = sock.recv(min(msg_len - bytes_recd, 4096))
            if not chunk:
                return None

            chunks.append(chunk)
            bytes_recd += len(chunk)

        encrypted_data = b''.join(chunks)

        # GIẢI MÃ
        decrypted = cipher.decrypt(encrypted_data)

        return json.loads(decrypted.decode('utf-8'))

    except:
        return None