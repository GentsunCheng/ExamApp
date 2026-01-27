from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLineEdit, QPushButton, QLabel
from PySide6.QtGui import QRegularExpressionValidator
from models import authenticate, verify_encryption_ok
from utils import show_warn
from language import tr
from theme_manager import theme_manager


# noinspection PyTypeChecker
class LoginView(QWidget):
    def __init__(self, on_login):
        super().__init__()
        self.on_login = on_login
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        ff = 'font' + '-family'
        br = 'border' + '-radius'
        ss = (
            f"QWidget {{ {bkg}:{colors['background']}; {ff}:\"PingFang SC\",sans-serif; }}\n"
            f"QLabel {{ {fs}:16px; {col}:{colors['text_primary']}; }}\n"
            f"QLineEdit {{ {pd}:8px; {bd}:1px solid {colors['input_border']}; {br}:8px; {fs}:14px; {bkg}:{colors['input_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QLineEdit:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:8px 16px; border:none; {br}:8px; {fs}:14px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QPushButton:pressed {{ {bkg}:{colors['primary']}; }}\n"
        )
        self.setStyleSheet(ss)
        main = QVBoxLayout()
        main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card = QGroupBox()
        card.setFixedWidth(320)
        card.setStyleSheet(f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:12px; padding:24px; background-color:{colors['card_background']}; }}")
        lay = QVBoxLayout()
        title = QLabel(tr('login.title'))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            f"font-size:20px; font-weight:bold; margin-bottom:16px; padding:6px 12px; border-radius:12px; "
            f"background-color:{colors['border_light']}; color:{colors['text_primary']}; border:1px solid {colors['border']};"
        )
        self.user_role = 'auto'
        self.user = QLineEdit()
        self.user.setPlaceholderText(tr('login.username'))
        self.user.setInputMethodHints(Qt.InputMethodHint.ImhNoPredictiveText | Qt.InputMethodHint.ImhNoAutoUppercase | Qt.InputMethodHint.ImhPreferLowercase)
        user_validator = QRegularExpressionValidator(QRegularExpression(r"^[A-Za-z0-9_@.\-]+$"))
        self.user.setValidator(user_validator)
        self.user.returnPressed.connect(lambda: self.pwd.setFocus())
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.EchoMode.Password)
        self.pwd.setPlaceholderText(tr('login.password'))
        self.pwd.setInputMethodHints(Qt.InputMethodHint.ImhHiddenText | Qt.InputMethodHint.ImhNoPredictiveText | Qt.InputMethodHint.ImhSensitiveData)
        pwd_validator = QRegularExpressionValidator(QRegularExpression(r"^[\x20-\x7E]+$"))
        self.pwd.setValidator(pwd_validator)
        self.pwd.returnPressed.connect(self.handle_login)
        btn = QPushButton(tr('login.button'))
        btn.setDefault(True)
        btn.clicked.connect(self.handle_login)
        self.login_btn = btn
        lay.addWidget(title)
        lay.addWidget(self.user)
        lay.addWidget(self.pwd)
        lay.addWidget(btn)
        lay.setSpacing(12)
        card.setLayout(lay)
        main.addWidget(card)
        self.setLayout(main)
        try:
            ok = verify_encryption_ok()
            self._encryption_ok = ok
            if not ok:
                self.user.setEnabled(False)
                self.pwd.setEnabled(False)
                self.login_btn.setEnabled(False)
                msg = QLabel(tr('login.decrypt_failed'))
                msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
                colors2 = theme_manager.get_theme_colors()
                msg.setStyleSheet(f"font-size:13px; color:{colors2['error']}; padding:6px; border:1px solid {colors2['error']}; border-radius:8px; background-color:{colors2['error_light']};")
                lay.addWidget(msg)
        except Exception:
            self._encryption_ok = True
    def handle_login(self):
        if hasattr(self, '_encryption_ok') and not self._encryption_ok:
            return
        u = authenticate(self.user.text().strip(), self.pwd.text())
        if not u:
            show_warn(self, tr('common.error'), tr('error.bad_credentials'))
            return
        self.on_login(u, self.user_role)
