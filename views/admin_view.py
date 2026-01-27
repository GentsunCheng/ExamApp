from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTabWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QShortcut, QKeySequence
from PySide6.QtCore import QPropertyAnimation, QEasingCurve
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn, ask_yes_no
from icon_manager import IconManager
from views.admin_modules.users_module import AdminUsersModule
from views.admin_modules.exams_module import AdminExamsModule
from views.admin_modules.sync_module import AdminSyncModule
from views.admin_modules.scores_module import AdminScoresModule
from views.admin_modules.study_progress_module import AdminProgressModule
from views.admin_modules.exam_progress_module import AdminScoresOverviewModule


class AdminView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_manager = IconManager()
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        ff = 'font' + '-family'
        br = 'border' + '-radius'
        ss_admin = (
            f"QWidget {{ {bkg}:{colors['background']}; {ff}:\"PingFang SC\",sans-serif; }}\n"
            f"QTabWidget::pane {{ {bd}:1px solid {colors['border']}; {bkg}:{colors['card_background']}; {br}:8px; }}\n"
            f"QTabBar::tab {{ {bkg}:{colors['border_light']}; {pd}:10px 16px; margin-right:2px; {br}:8px; }}\n"
            f"QTabBar::tab:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QGroupBox {{ font-weight:bold; {bd}:1px solid {colors['border']}; {br}:8px; margin-top:8px; padding-top:8px; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:6px 12px; border:none; {br}:8px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QTableWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {bkg}:{colors['card_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QTableWidget::item:hover {{ {bkg}:{colors['border_light']}; }}\n"
            f"QTableWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
            f"QHeaderView::section {{ {bkg}:{colors['border_light']}; {col}:{colors['text_secondary']}; font-weight:600; {pd}:6px 8px; {bd}:none; }}\n"
            f"QLineEdit, QTextEdit, QSpinBox, QDateTimeEdit {{ {pd}:6px; {bd}:1px solid {colors['input_border']}; {br}:8px; {bkg}:{colors['input_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QLineEdit:focus, QTextEdit:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QComboBox {{ {pd}:6px 8px; {bd}:1px solid {colors['input_border']}; {br}:8px; {bkg}:{colors['input_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QComboBox:focus {{ {bd}-color:{colors['primary']}; }}\n"
            f"QComboBox::drop-down {{ width:24px; border:none; }}\n"
            f"QComboBox QAbstractItemView {{ {bkg}:{colors['card_background']}; {bd}:1px solid {colors['border']}; {pd}:4px; outline:0; }}\n"
        )
        self.setStyleSheet(ss_admin)
        self.tabs = QTabWidget()
        self.tabs.addTab(AdminUsersModule(self), tr('admin.users_tab'))
        self.tabs.addTab(AdminExamsModule(self), tr('admin.exams_tab'))
        self.tabs.addTab(AdminSyncModule(self), tr('admin.sync_tab'))
        self.tabs.addTab(AdminScoresModule(self), tr('admin.scores_tab'))
        self.tabs.addTab(AdminScoresOverviewModule(self), tr('admin.exam_progress_tab'))
        self.tabs.addTab(AdminProgressModule(self), tr('admin.study_progress_tab'))
        self.tabs.setTabIcon(0, self.icon_manager.get_icon('user'))
        self.tabs.setTabIcon(1, self.icon_manager.get_icon('exam'))
        self.tabs.setTabIcon(2, self.icon_manager.get_icon('sync'))
        self.tabs.setTabIcon(3, self.icon_manager.get_icon('score'))
        self.tabs.setTabIcon(4, self.icon_manager.get_icon('score'))
        self.tabs.setTabIcon(5, self.icon_manager.get_icon('score'))
        self.tabs.setTabVisible(2, False)
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout = QVBoxLayout()
        topbar = QHBoxLayout()
        title = QLabel(tr('admin.dashboard'))
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        topbar.addWidget(title)
        topbar.addStretch()
        logout_btn = QPushButton(tr('common.logout'))
        logout_btn.setIcon(self.icon_manager.get_icon('confirm'))
        logout_btn.clicked.connect(self.handle_logout)
        topbar.addWidget(logout_btn)
        layout.addLayout(topbar)
        layout.addWidget(self.tabs)
        self.setLayout(layout)
        self.sync_tab_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.sync_tab_shortcut.activated.connect(self.sync_view_change)
        self._last_tab_index = 0
        self._tab_anim = None
        self._tab_effect = None

    def _animate_tab_change(self, new_idx):
        if self._tab_anim is not None:
            try:
                self._tab_anim.stop()
            except Exception:
                pass
            self._tab_anim = None
        w = self.tabs.widget(new_idx) if 0 <= new_idx < self.tabs.count() else None
        if w is None:
            return
        if self._tab_effect is not None:
            last = self.tabs.widget(self._last_tab_index) if 0 <= self._last_tab_index < self.tabs.count() else None
            if last is not None and last.graphicsEffect() is self._tab_effect:
                last.setGraphicsEffect(None)
        effect = QGraphicsOpacityEffect(w)
        w.setGraphicsEffect(effect)
        effect.setOpacity(0.0)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(75)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.InOutCubic)

        def finished():
            effect.setOpacity(1.0)
            w.setGraphicsEffect(None)

        anim.finished.connect(finished)
        self._tab_anim = anim
        self._tab_effect = effect
        anim.start()

    def sync_view_change(self):
        if self.tabs.isTabVisible(2):
            self.tabs.setTabVisible(2, False)
        else:
            self.tabs.setTabVisible(2, True)

    def on_tab_changed(self, idx):
        old_idx = getattr(self, '_last_tab_index', 0)
        if old_idx != idx:
            self._animate_tab_change(idx)
        self._last_tab_index = idx
        w = self.tabs.widget(idx)
        if isinstance(w, AdminUsersModule):
            if hasattr(w, 'refresh_users'):
                w.refresh_users()
        elif isinstance(w, AdminExamsModule):
            if hasattr(w, 'refresh_exams'):
                w.refresh_exams()
        elif isinstance(w, AdminSyncModule):
            if hasattr(w, 'refresh_targets'):
                w.refresh_targets()
        elif isinstance(w, AdminScoresModule):
            if hasattr(w, 'refresh_scores'):
                w.refresh_scores()
        elif isinstance(w, AdminScoresOverviewModule):
            if hasattr(w, 'refresh_overview'):
                w.refresh_overview()
        elif isinstance(w, AdminProgressModule):
            if hasattr(w, 'refresh_users_and_view'):
                w.refresh_users_and_view()

    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()
            
