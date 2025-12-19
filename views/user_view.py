from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QTabWidget, QAbstractItemView
from icon_manager import get_icon
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn, ask_yes_no
from models import list_exams, list_attempts, get_exam_title, get_exam_stats, list_questions
from windows.exam_window import ExamWindow
from views.user_modules.exams_module import UserExamsModule
from views.user_modules.history_module import UserHistoryModule
from views.user_modules.progress_module import UserProgressModule

class UserView(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        br = 'border' + '-radius'
        ss_user = (
            f"QWidget {{ {bkg}:{colors['background']}; font-family:\"PingFang SC\",sans-serif; }}\n"
            f"QTabWidget::pane {{ {bd}:1px solid {colors['border']}; {bkg}:{colors['card_background']}; {br}:8px; }}\n"
            f"QTabBar::tab {{ {bkg}:{colors['border_light']}; {pd}:10px 16px; margin-right:2px; {br}:8px; }}\n"
            f"QTabBar::tab:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QGroupBox {{ font-weight:bold; {bd}:1px solid {colors['border']}; {br}:8px; margin-top:8px; padding-top:8px; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:6px 12px; border:none; {br}:8px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QPushButton:checked {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QTableWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {bkg}:{colors['card_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QTableWidget::item:hover {{ {bkg}:{colors['border_light']}; }}\n"
            f"QTableWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QHeaderView::section {{ {bkg}:{colors['border_light']}; {col}:{colors['text_secondary']}; font-weight:600; {pd}:6px 8px; {bd}:none; }}\n"
        )
        self.setStyleSheet(ss_user)
        self.user = user
        layout = QVBoxLayout()
        topbar = QHBoxLayout()
        title = QLabel(tr('user.center'))
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        topbar.addWidget(title)
        topbar.addStretch()
        name_display = user.get('full_name')
        user_label = QLabel(tr('user.current_user_prefix') + f'{user["username"]}' + (tr('user.full_name_suffix', name=name_display) if name_display else ''))
        topbar.addWidget(user_label)
        logout_btn = QPushButton(tr('common.logout'))
        logout_btn.setIcon(get_icon('confirm'))
        logout_btn.clicked.connect(self.handle_logout)
        topbar.addWidget(logout_btn)
        layout.addLayout(topbar)
        self.tabs = QTabWidget()
        self.exams_module = UserExamsModule(self.user, self)
        self.history_module = UserHistoryModule(self.user, self)
        self.progress_module = UserProgressModule(self.user, self)
        self.tabs.addTab(self.exams_module, tr('user.exams_tab'))
        self.tabs.setTabIcon(0, get_icon('exam'))
        self.tabs.addTab(self.history_module, tr('user.history_tab'))
        self.tabs.setTabIcon(1, get_icon('score'))
        self.tabs.addTab(self.progress_module, '学习进度')
        self.tabs.setTabIcon(2, get_icon('info'))
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    def refresh_exams(self):
        if hasattr(self, 'exams_module'):
            self.exams_module.refresh_exams()
    def refresh_attempts(self):
        if hasattr(self, 'history_module'):
            self.history_module.refresh_attempts()
    def refresh_progress(self):
        if hasattr(self, 'progress_module'):
            self.progress_module.refresh_progress()
    def on_tab_changed(self, idx):
        if idx == 2:
            self.refresh_progress()
    def start_exam(self, exam_id=None):
        try:
            print("[DEBUG] start_exam invoked")
        except Exception:
            pass
        if exam_id is None:
            exam_id = self.exams_module.get_selected_exam_id()
            if not exam_id:
                show_warn(self, tr('common.error'), tr('error.select_exam'))
                return
        try:
            print(f"[DEBUG] selected exam_id={exam_id}")
        except Exception:
            pass
        if not exam_id:
            show_warn(self, tr('common.error'), tr('error.select_exam'))
            return
        try:
            import sys
            print("[DEBUG] calling list_questions", file=sys.stderr)
        except Exception:
            pass
        qs = list_questions(int(exam_id))
        try:
            print(f"[DEBUG] questions_count={len(qs) if qs else 0}")
        except Exception:
            pass
        if not qs:
            show_warn(self, tr('common.error'), tr('error.no_questions'))
            return
        try:
            if not hasattr(self, '_exam_windows'):
                self._exam_windows = []
            win = ExamWindow(self.user, exam_id, self)
            self._exam_windows.append(win)
            win.show()
            try:
                print("[DEBUG] exam window shown")
            except Exception:
                pass
            try:
                win.raise_()
                win.activateWindow()
            except Exception:
                pass
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()
