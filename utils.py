import os
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
