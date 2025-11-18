from PySide6.QtCore import Qt, QRegularExpression
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLineEdit, QPushButton, QLabel, QMessageBox
from PySide6.QtGui import QRegularExpressionValidator
from models import authenticate
from theme_manager import theme_manager

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
        main.setAlignment(Qt.AlignCenter)
        card = QGroupBox()
        card.setFixedWidth(320)
        card.setStyleSheet(f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:12px; padding:24px; background-color:{colors['card_background']}; }}")
        lay = QVBoxLayout()
        title = QLabel('📝 登录')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-size:20px; font-weight:bold; margin-bottom:16px;")
        self.user = QLineEdit()
        self.user.setPlaceholderText('用户名')
        self.user.setInputMethodHints(Qt.ImhNoPredictiveText | Qt.ImhNoAutoUppercase | Qt.ImhPreferLowercase)
        user_validator = QRegularExpressionValidator(QRegularExpression(r"^[A-Za-z0-9_@.\-]+$"))
        self.user.setValidator(user_validator)
        self.pwd = QLineEdit()
        self.pwd.setEchoMode(QLineEdit.Password)
        self.pwd.setPlaceholderText('密码')
        self.pwd.setInputMethodHints(Qt.ImhHiddenText | Qt.ImhNoPredictiveText | Qt.ImhSensitiveData)
        pwd_validator = QRegularExpressionValidator(QRegularExpression(r"^[\x20-\x7E]+$"))
        self.pwd.setValidator(pwd_validator)
        btn = QPushButton('登录')
        btn.setDefault(True)
        btn.clicked.connect(self.handle_login)
        lay.addWidget(title)
        lay.addWidget(self.user)
        lay.addWidget(self.pwd)
        lay.addWidget(btn)
        lay.setSpacing(12)
        card.setLayout(lay)
        main.addWidget(card)
        self.setLayout(main)
    def handle_login(self):
        u = authenticate(self.user.text().strip(), self.pwd.text())
        if not u:
            QMessageBox.warning(self, '错误', '用户名或密码错误')
            return
        self.on_login(u)
