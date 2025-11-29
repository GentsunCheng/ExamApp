import base64
import os
import hashlib
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes

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
