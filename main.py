import os
import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QKeySequence, QShortcut, QPalette
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QRect, QParallelAnimationGroup
from database import ensure_db
from db_iter import iter_loop
from models import create_admin_if_absent
from utils import load_binary
from theme_manager import theme_manager
from views.login_view import LoginView
from views.admin_view import AdminView
from views.user_view import UserView

from language import set_language, get_system_language_codes, tr

__language__ = get_system_language_codes()
set_language(__language__)

__versionfile__ = load_binary(filename="version", no_raise=True)
__version__ = "dev"

if __versionfile__:
    if os.path.exists(__versionfile__):
        with open(__versionfile__, "r") as f:
            __version__ = f.read().strip()

iter_loop()


def is_dark_mode(app):
    palette = app.palette()
    color = palette.color(QPalette.Window)
    return color.lightness() < 128

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._zoom_anim = None
        self.user_view = None
        self.admin_view = None
        ensure_db()
        create_admin_if_absent()
        self.setWindowTitle(f"{tr('app.title')} - {__version__}")
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(int(screen.width() / 2), int(screen.height() / 2))
        self.resize(int(screen.width() * 0.75), int(screen.height() * 0.75))
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)

        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.close)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        self.setStyleSheet(f"QMainWindow {{ {bkg}:{colors['background']}; }}")
        self.stack = QStackedWidget()
        self.login = LoginView(self.on_login)
        self.stack.addWidget(self.login)
        self.setCentralWidget(self.stack)
        app = QApplication.instance()
        app.paletteChanged.connect(self.on_palette_changed)

    def on_palette_changed(self):
        self.setStyleSheet(theme_manager.get_scrollbar_style())
        theme_manager.install_smooth_scroll(self)

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
        self._zoom_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._zoom_anim.start()

    def _create_opacity_anim(self, widget, start, end):
        if widget is None:
            return None
        effect = widget.graphicsEffect()
        if not isinstance(effect, QGraphicsOpacityEffect):
            effect = QGraphicsOpacityEffect(widget)
            widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(220)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        return anim

    def _switch_with_fade(self, target_widget, cleanup=None):
        if target_widget is None:
            return
        current = self.stack.currentWidget()
        if current is target_widget:
            if cleanup:
                cleanup()
            return
        if self.stack.indexOf(target_widget) == -1:
            self.stack.addWidget(target_widget)
        target_widget.setVisible(True)
        self.stack.setCurrentWidget(target_widget)
        fade_in = self._create_opacity_anim(target_widget, 0.0, 1.0)
        fade_out = self._create_opacity_anim(current, 1.0, 0.0) if current is not None else None
        group = QParallelAnimationGroup(self)
        if fade_out is not None:
            group.addAnimation(fade_out)
        if fade_in is not None:
            group.addAnimation(fade_in)

        def on_finished():
            if cleanup:
                cleanup()
            if current is not None:
                eff = current.graphicsEffect()
                if isinstance(eff, QGraphicsOpacityEffect):
                    current.setGraphicsEffect(None)
            eff_t = target_widget.graphicsEffect()
            if isinstance(eff_t, QGraphicsOpacityEffect):
                eff_t.setOpacity(1.0)

        group.finished.connect(on_finished)
        self._fade_group = group
        group.start()

    def closeEvent(self, event):
        self.logout()
        event.accept()

    def on_login(self, user, role='auto'):
        if role == 'auto':
            role = user['role']
        if role == 'admin':
            self.admin_view = AdminView(self)
            self._switch_with_fade(self.admin_view)
        else:
            self.user_view = UserView(user, self)
            self._switch_with_fade(self.user_view)
            
    def logout(self):
        def cleanup():
            for i in range(1, self.stack.count()):
                w = self.stack.widget(i)
                self.stack.removeWidget(w)
                w.deleteLater()
        self._switch_with_fade(self.login, cleanup=cleanup)


if __name__ == '__main__':
    app = QApplication([])
    app.setStyle('Fusion')
    app.setStyleSheet(theme_manager.get_scrollbar_style())
    theme_manager.install_smooth_scroll(app)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
