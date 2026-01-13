import sys

from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect
from database import ensure_db
from models import create_admin_if_absent
from theme_manager import theme_manager
from views.login_view import LoginView
from views.admin_view import AdminView
from views.user_view import UserView

from language import set_language, get_system_language_codes

__language__ = get_system_language_codes()
set_language(__language__)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.user_view = None
        self.admin = None
        ensure_db()
        create_admin_if_absent()
        self.setWindowTitle('ExamApp By Gentsun')
        self.setMinimumSize(900, 600)
        self.resize(1440, 960)
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.close)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        self.setStyleSheet(f"QMainWindow {{ {bkg}:{colors['background']}; }}")
        self.stack = QStackedWidget()
        self.login = LoginView(self.on_login)
        self.stack.addWidget(self.login)
        self.setCentralWidget(self.stack)

    def showEvent(self, event):
        super().showEvent(event)
        self.start_zoom_in_animation()

    def start_zoom_in_animation(self):
        rect = self.geometry()
        if not rect.isValid():
            return
        scale = 0.9
        w = max(1, int(rect.width() * scale))
        h = max(1, int(rect.height() * scale))
        start_rect = QRect(
            rect.center().x() - w // 2,
            rect.center().y() - h // 2,
            w,
            h,
        )
        self._zoom_anim = QPropertyAnimation(self, b"geometry")
        self._zoom_anim.setDuration(180)
        self._zoom_anim.setStartValue(start_rect)
        self._zoom_anim.setEndValue(rect)
        self._zoom_anim.setEasingCurve(QEasingCurve.OutCubic)
        self._zoom_anim.start()

    def closeEvent(self, event):
        self.logout()
        event.accept()

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
    app.setStyleSheet(theme_manager.get_scrollbar_style())
    theme_manager.install_smooth_scroll(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
