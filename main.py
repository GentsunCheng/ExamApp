import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from database import ensure_db
from models import create_admin_if_absent
from theme_manager import theme_manager
from views.login_view import LoginView
from views.admin_view import AdminView
from views.user_view import UserView


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_view = None
        self.admin = None
        ensure_db()
        create_admin_if_absent()
        self.setWindowTitle('本地考试系统')
        self.setMinimumSize(900, 600)
        self.resize(1440, 960)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        self.setStyleSheet(f"QMainWindow {{ {bkg}:{colors['background']}; }}")
        self.stack = QStackedWidget()
        self.login = LoginView(self.on_login)
        self.stack.addWidget(self.login)
        self.setCentralWidget(self.stack)
    def on_login(self, user):
        if user['role'] == 'admin':
            self.admin = AdminView(self)
            self.stack.addWidget(self.admin)
            self.stack.setCurrentWidget(self.admin)
        else:
            self.user_view = UserView(user, self)
            self.stack.addWidget(self.user_view)
            self.stack.setCurrentWidget(self.user_view)
    def logout(self):
        for i in range(1, self.stack.count()):
            w = self.stack.widget(i)
            self.stack.removeWidget(w)
            w.deleteLater()
        self.stack.setCurrentWidget(self.login)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('Fusion')
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
