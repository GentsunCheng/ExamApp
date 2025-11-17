import os
import hashlib
import base64
import secrets

def hash_password(password):
    salt = base64.b64encode(secrets.token_bytes(16)).decode('utf-8')
    h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
    return f'{salt}${h}'

def verify_password(password, stored):
    try:
        salt, h = stored.split('$', 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + password).encode('utf-8')).hexdigest() == h

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)