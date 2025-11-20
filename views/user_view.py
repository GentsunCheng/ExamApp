from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QTabWidget
from icon_manager import get_icon
from theme_manager import theme_manager
from models import list_exams, list_attempts, get_exam_title, get_exam_stats
from windows.exam_window import ExamWindow

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
            f"QHeaderView::section {{ {bkg}:{colors['border_light']}; {col}:{colors['text_secondary']}; font-weight:600; {pd}:6px 8px; {bd}:none; {bd}-right:1px solid {colors['border']}; }}\n"
        )
        self.setStyleSheet(ss_user)
        self.user = user
        layout = QVBoxLayout()
        topbar = QHBoxLayout()
        title = QLabel('用户中心')
        title.setStyleSheet("font-size:18px; font-weight:bold;")
        topbar.addWidget(title)
        topbar.addStretch()
        name_display = user.get('full_name')
        user_label = QLabel(f'当前用户: {user["username"]}' + (f'（{name_display}）' if name_display else ''))
        topbar.addWidget(user_label)
        logout_btn = QPushButton('退出登录')
        logout_btn.setIcon(get_icon('confirm'))
        logout_btn.clicked.connect(self.handle_logout)
        topbar.addWidget(logout_btn)
        layout.addLayout(topbar)
        self.tabs = QTabWidget()
        # 考试页面
        exams_tab = QWidget()
        exams_v = QVBoxLayout()
        exams_toolbar = QHBoxLayout()
        start_btn = QPushButton('开始考试')
        start_btn.setIcon(get_icon('exam_start'))
        start_btn.clicked.connect(lambda: self.start_exam(None))
        refresh_exams_btn = QPushButton('刷新')
        refresh_exams_btn.clicked.connect(self.refresh_exams)
        exams_toolbar.addWidget(start_btn)
        exams_toolbar.addWidget(refresh_exams_btn)
        exams_toolbar.addStretch()
        exams_v.addLayout(exams_toolbar)
        self.exams_table_user = QTableWidget(0, 7)
        self.exams_table_user.setHorizontalHeaderLabels(['ID', '标题', '限时(分钟)', '总分', '及格比例%', '题目数量', '截止'])
        self.exams_table_user.setColumnWidth(0, 50)
        self.exams_table_user.setColumnWidth(1, 250)
        self.exams_table_user.setColumnWidth(2, 80)
        self.exams_table_user.setColumnWidth(3, 80)
        self.exams_table_user.setColumnWidth(4, 80)
        self.exams_table_user.setColumnWidth(5, 80)
        self.exams_table_user.setColumnWidth(6, 180)
        self.exams_table_user.horizontalHeader().setStretchLastSection(True)
        self.exams_table_user.setAlternatingRowColors(True)
        self.refresh_exams()
        exams_v.addWidget(self.exams_table_user)
        exams_tab.setLayout(exams_v)
        self.tabs.addTab(exams_tab, '试题列表')
        self.tabs.setTabIcon(0, get_icon('exam'))
        # 历史成绩页面
        history_tab = QWidget()
        history_v = QVBoxLayout()
        history_toolbar = QHBoxLayout()
        refresh_attempts_btn = QPushButton('刷新')
        refresh_attempts_btn.clicked.connect(self.refresh_attempts)
        history_toolbar.addWidget(refresh_attempts_btn)
        history_toolbar.addStretch()
        history_v.addLayout(history_toolbar)
        self.attempts_table = QTableWidget(0, 5)
        self.attempts_table.setHorizontalHeaderLabels(['UUID记录', '试题', '开始', '提交', '分数/通过'])
        self.attempts_table.setColumnWidth(0, 280)
        self.attempts_table.setColumnWidth(1, 250)
        self.attempts_table.setColumnWidth(2, 200)
        self.attempts_table.setColumnWidth(3, 200)
        self.attempts_table.horizontalHeader().setStretchLastSection(True)
        self.attempts_table.setAlternatingRowColors(True)
        self.refresh_attempts()
        history_v.addWidget(self.attempts_table)
        history_tab.setLayout(history_v)
        self.tabs.addTab(history_tab, '历史成绩')
        self.tabs.setTabIcon(1, get_icon('score'))
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    def refresh_exams(self):
        tbl = getattr(self, 'exams_table_user', None)
        if tbl is None:
            return
        tbl.setRowCount(0)
        for e in list_exams(include_expired=False):
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(str(e[0])))
            tbl.setItem(r, 1, QTableWidgetItem(e[1] or ''))
            tbl.setItem(r, 2, QTableWidgetItem(str(e[4])))
            stats = get_exam_stats(int(e[0]))
            tbl.setItem(r, 3, QTableWidgetItem(str(int(stats['total_score'])) if stats else '0'))
            tbl.setItem(r, 4, QTableWidgetItem(f"{int(float(e[3])*100)}%"))
            tbl.setItem(r, 5, QTableWidgetItem(str(stats['count']) if stats else '0'))
            tbl.setItem(r, 6, QTableWidgetItem(e[5] if e[5] else '永久'))
    def refresh_attempts(self):
        self.attempts_table.setRowCount(0)
        for a in list_attempts(self.user['id']):
            r = self.attempts_table.rowCount()
            self.attempts_table.insertRow(r)
            self.attempts_table.setItem(r, 0, QTableWidgetItem(a[0]))
            title = get_exam_title(int(a[2])) if a[2] is not None else ''
            self.attempts_table.setItem(r, 1, QTableWidgetItem(title or ''))
            self.attempts_table.setItem(r, 2, QTableWidgetItem(a[3] or ''))
            self.attempts_table.setItem(r, 3, QTableWidgetItem(a[4] or ''))
            ucell = QTableWidgetItem(f'{a[5]} / {"通过" if a[6]==1 else "未通过"}')
            if a[6] == 1:
                ucell.setBackground(QColor("#6bc041"))
            else:
                ucell.setBackground(QColor("#e75c5c"))
            self.attempts_table.setItem(r, 4, ucell)
    def start_exam(self, exam_id=None):
        if exam_id is None:
            tbl = getattr(self, 'exams_table_user', None)
            if tbl is None:
                QMessageBox.warning(self, '错误', '请选择试题')
                return
            r = tbl.currentRow()
            if r < 0:
                QMessageBox.warning(self, '错误', '请选择试题')
                return
            it = tbl.item(r, 0)
            exam_id = int(it.text()) if it and it.text() else None
        if not exam_id:
            QMessageBox.warning(self, '错误', '请选择试题')
            return
        ExamWindow(self.user, exam_id, self).show()
    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()
