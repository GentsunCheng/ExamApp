import os
import sys
import hashlib
import base64
import secrets
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt

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

def show_info(parent, title, text):
    m = QMessageBox(parent)
    m.setIcon(QMessageBox.Icon.Information)
    m.setWindowTitle(title)
    m.setText(text)
    m.setStandardButtons(QMessageBox.StandardButton.Ok)
    m.setDefaultButton(QMessageBox.StandardButton.Ok)
    try:
        m.setWindowFlags(m.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    except Exception:
        pass
    return m.exec()

def show_warn(parent, title, text):
    m = QMessageBox(parent)
    m.setIcon(QMessageBox.Icon.Warning)
    m.setWindowTitle(title)
    m.setText(text)
    m.setStandardButtons(QMessageBox.StandardButton.Ok)
    m.setDefaultButton(QMessageBox.StandardButton.Ok)
    try:
        m.setWindowFlags(m.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    except Exception:
        pass
    return m.exec()

def ask_yes_no(parent, title, text, default_yes=False):
    m = QMessageBox(parent)
    m.setIcon(QMessageBox.Icon.Question)
    m.setWindowTitle(title)
    m.setText(text)
    m.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    m.setDefaultButton(QMessageBox.StandardButton.Yes if default_yes else QMessageBox.StandardButton.No)
    try:
        m.setWindowFlags(m.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
    except Exception:
        pass
    return m.exec()

def get_resource_base():
    """
    返回资源目录的实际路径
    - 开发环境: ./resources
    - PyInstaller: sys._MEIPASS/resources
    - Nuitka macOS app bundle: main.app/Contents/MacOS/resources
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, "resources")
    print(sys.executable)
    exe_dir = os.path.dirname(sys.executable)
    resources_dir = os.path.join(exe_dir, "resources")
    if os.path.exists(resources_dir):
        return resources_dir

    return os.path.abspath("resources")

def load_binary(filename, no_raise=False):
    """
    返回 sshpass 二进制文件路径，并设置可执行权限
    """
    base = get_resource_base()
    bin_path = os.path.join(base, filename)
    if not os.path.exists(bin_path):
        if no_raise:
            return None
        raise FileNotFoundError(f"Cannot find binary: {bin_path}")
    os.chmod(bin_path, 0o755)
    return bin_path
