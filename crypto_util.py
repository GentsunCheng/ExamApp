import base64
import os
import hashlib
from io import BytesIO
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

def _load_key():
    try:
        from conf.serect_key import AES_KEY as _k
        return base64.b64decode(_k)
    except ImportError:
        try:
            key = None
            with open(".env", encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('AES_KEY='):
                        key = line[len('AES_KEY='):]
                    elif line.startswith('AES_KEY_B64='):
                        key = line[len('AES_KEY_B64='):]
            if key is None:
                key = os.urandom(32)
            with open('conf/serect_key.py','w') as f:
                f.write('AES_KEY = ' + repr(base64.b64encode(key).decode('ascii')) + '\n')
            return key
        except Exception:
            k = get_random_bytes(32)
            return k

_KEY = _load_key()

def encrypt_text(text):
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    nonce = get_random_bytes(12)
    cipher = AES.new(_KEY, AES.MODE_GCM, nonce=nonce)
    ct, tag = cipher.encrypt_and_digest(text.encode('utf-8'))
    payload = base64.b64encode(nonce + tag + ct).decode('ascii')
    return 'enc:' + payload

def decrypt_text(text):
    if text is None:
        return None
    if isinstance(text, bytes):
        try:
            text = text.decode('utf-8')
        except Exception:
            return text
    if not isinstance(text, str):
        return text
    if not text.startswith('enc:'):
        return text
    b = base64.b64decode(text[4:])
    nonce = b[:12]
    tag = b[12:28]
    ct = b[28:]
    cipher = AES.new(_KEY, AES.MODE_GCM, nonce=nonce)
    pt = cipher.decrypt_and_verify(ct, tag)
    return pt.decode('utf-8')

def encrypt_json(obj):
    import json
    s = json.dumps(obj, ensure_ascii=False)
    return encrypt_text(s)

def decrypt_json(text):
    import json
    if text is None:
        return None
    try:
        if isinstance(text, (str, bytes)) and str(text).startswith('enc:'):
            s = decrypt_text(text)
            return json.loads(s) if s else None
        return json.loads(text)
    except Exception:
        return None

def key_fingerprint():
    return hashlib.sha256(_KEY).hexdigest()

def encrypt_probe():
    return encrypt_text('EXAMAPP_KEY_PROBE')

def verify_probe(enc):
    try:
        return decrypt_text(enc) == 'EXAMAPP_KEY_PROBE'
    except Exception:
        return False


def aes_bytesio(data_io: BytesIO, secret_key: str, operation: str) -> BytesIO:
    """
    对 BytesIO 对象进行 AES-CBC 加密或解密，secret_key 为字符串。

    参数:
        data_io: BytesIO 对象
        secret_key: str
        operation: "encrypt" 或 "decrypt"

    返回:
        BytesIO 对象
    """
    data_io.seek(0)
    data = data_io.read()

    # 将字符串 key 转为 bytes，并调整长度为 32 字节（AES-256）
    key_bytes = secret_key.encode('utf-8')
    if len(key_bytes) < 32:
        key_bytes = key_bytes.ljust(32, b'\0')  # 不够 32 字节补 0
    else:
        key_bytes = key_bytes[:32]  # 超过截断

    if operation == "encrypt":
        iv = get_random_bytes(16)
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        encrypted_data = cipher.encrypt(pad(data, AES.block_size))
        return BytesIO(iv + encrypted_data)

    elif operation == "decrypt":
        if len(data) < 16:
            raise ValueError("Data too short to contain IV")
        iv = data[:16]
        encrypted_data = data[16:]
        cipher = AES.new(key_bytes, AES.MODE_CBC, iv)
        decrypted_data = unpad(cipher.decrypt(encrypted_data), AES.block_size)
        return BytesIO(decrypted_data)

    else:
        raise ValueError("Operation must be 'encrypt' or 'decrypt'")
