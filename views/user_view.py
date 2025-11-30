from PySide6.QtGui import QColor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QMessageBox, QTabWidget, QAbstractItemView
from icon_manager import get_icon
from theme_manager import theme_manager
from language import tr
from models import list_exams, list_attempts, get_exam_title, get_exam_stats, list_questions
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
        # 考试页面
        exams_tab = QWidget()
        exams_v = QVBoxLayout()
        exams_toolbar = QHBoxLayout()
        start_btn = QPushButton(tr('user.start_exam'))
        start_btn.setIcon(get_icon('exam_start'))
        start_btn.clicked.connect(lambda: self.start_exam(None))
        refresh_exams_btn = QPushButton(tr('common.refresh'))
        refresh_exams_btn.clicked.connect(self.refresh_exams)
        exams_toolbar.addWidget(start_btn)
        exams_toolbar.addWidget(refresh_exams_btn)
        exams_toolbar.addStretch()
        exams_v.addLayout(exams_toolbar)
        self.exams_table_user = QTableWidget(0, 9)
        self.exams_table_user.setHorizontalHeaderLabels([tr('exams.id'), tr('exams.title'), tr('exams.desc'), tr('exams.time_limit'), tr('exams.deadline'), tr('exams.pass_ratio'), tr('exams.q_count'), tr('exams.total'), tr('exams.best')])
        self.exams_table_user.setColumnWidth(0, 50)
        self.exams_table_user.setColumnWidth(1, 250)
        self.exams_table_user.setColumnWidth(2, 480)
        self.exams_table_user.setColumnWidth(3, 80)
        self.exams_table_user.setColumnWidth(4, 200)
        self.exams_table_user.setColumnWidth(5, 75)
        self.exams_table_user.setColumnWidth(6, 75)
        self.exams_table_user.setColumnWidth(7, 75)
        self.exams_table_user.setColumnWidth(8, 50)
        self.exams_table_user.horizontalHeader().setStretchLastSection(True)
        self.exams_table_user.setAlternatingRowColors(True)
        self.exams_table_user.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.exams_table_user.setSelectionMode(QAbstractItemView.SingleSelection)
        self.refresh_exams()
        exams_v.addWidget(self.exams_table_user)
        exams_tab.setLayout(exams_v)
        self.tabs.addTab(exams_tab, tr('user.exams_tab'))
        self.tabs.setTabIcon(0, get_icon('exam'))
        # 历史成绩页面
        history_tab = QWidget()
        history_v = QVBoxLayout()
        history_toolbar = QHBoxLayout()
        refresh_attempts_btn = QPushButton(tr('common.refresh'))
        refresh_attempts_btn.clicked.connect(self.refresh_attempts)
        history_toolbar.addWidget(refresh_attempts_btn)
        history_toolbar.addStretch()
        history_v.addLayout(history_toolbar)
        self.attempts_table = QTableWidget(0, 5)
        self.attempts_table.setHorizontalHeaderLabels([tr('attempts.uuid'), tr('attempts.exam_title'), tr('attempts.started'), tr('attempts.submitted'), tr('attempts.score_total_pass')])
        self.attempts_table.setColumnWidth(0, 280)
        self.attempts_table.setColumnWidth(1, 250)
        self.attempts_table.setColumnWidth(2, 200)
        self.attempts_table.setColumnWidth(3, 200)
        self.attempts_table.horizontalHeader().setStretchLastSection(True)
        self.attempts_table.setAlternatingRowColors(True)
        self.refresh_attempts()
        history_v.addWidget(self.attempts_table)
        history_tab.setLayout(history_v)
        self.tabs.addTab(history_tab, tr('user.history_tab'))
        self.tabs.setTabIcon(1, get_icon('score'))
        layout.addWidget(self.tabs)
        self.setLayout(layout)
    def refresh_exams(self):
        tbl = getattr(self, 'exams_table_user', None)
        if tbl is None:
            return
        tbl.setRowCount(0)
        colors = theme_manager.get_theme_colors()
        passed_ids = set()
        best_scores = {}
        for a in list_attempts(self.user['id']):
            if a[6] == 1 and a[4]:
                try:
                    passed_ids.add(int(a[2]))
                except Exception:
                    pass
            try:
                eid = int(a[2]) if a[2] is not None else None
            except Exception:
                eid = None
            if eid is not None and a[4]:
                bs = best_scores.get(eid)
                if bs is None or float(a[5] or 0.0) > bs:
                    best_scores[eid] = float(a[5] or 0.0)
        exams = list_exams(include_expired=False)
        exams_sorted = sorted(exams, key=lambda e: (0 if e[5] is None else 1, -int(e[0]) if e[0] is not None else 0))
        for e in exams_sorted:
            r = tbl.rowCount()
            tbl.insertRow(r)
            tbl.setItem(r, 0, QTableWidgetItem(str(e[0])))
            tbl.setItem(r, 1, QTableWidgetItem(e[1] or ''))
            tbl.setItem(r, 2, QTableWidgetItem(e[2] or ''))
            tbl.setItem(r, 3, QTableWidgetItem(str(e[4])))
            stats = get_exam_stats(int(e[0]))
            tbl.setItem(r, 4, QTableWidgetItem(e[5] if e[5] else tr('common.permanent')))
            tbl.setItem(r, 5, QTableWidgetItem(f"{int(float(e[3])*100)}%"))
            tbl.setItem(r, 6, QTableWidgetItem(str(stats['count']) if stats else '0'))
            tbl.setItem(r, 7, QTableWidgetItem(str(int(stats['total_score'])) if stats else '0'))
            best = int(best_scores.get(int(e[0]), 0))
            tbl.setItem(r, 8, QTableWidgetItem(str(best)))
            if int(e[0]) in passed_ids:
                for c in range(0, 9):
                    it = tbl.item(r, c)
                    if it:
                        it.setForeground(QColor('#2E7D32'))
            if e[5] is None:
                for c in range(0, 9):
                    it = tbl.item(r, c)
                    if it:
                        it.setBackground(QColor(colors['info_light']))
        try:
            for r in range(tbl.rowCount()):
                for c in range(tbl.columnCount()):
                    it = tbl.item(r, c)
                    if it:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
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
            passed_text = tr('attempts.data_invalid') if (len(a) > 8 and a[8] == 0) else (tr('attempts.pass') if a[6]==1 else tr('attempts.fail'))
            total = int(a[7] or 0)
            ucell = QTableWidgetItem(f'{a[5]} / {total} / {passed_text}')
            if len(a) > 8 and a[8] == 0:
                ucell.setBackground(QColor('#fff3cd'))
                ucell.setForeground(QColor('#8a6d3b'))
            else:
                if a[6] == 1:
                    ucell.setBackground(QColor("#6bc041"))
                else:
                    ucell.setBackground(QColor("#e75c5c"))
            self.attempts_table.setItem(r, 4, ucell)
        try:
            for r in range(self.attempts_table.rowCount()):
                for c in range(self.attempts_table.columnCount()):
                    it = self.attempts_table.item(r, c)
                    if it:
                        it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        except Exception:
            pass
    def start_exam(self, exam_id=None):
        if exam_id is None:
            tbl = getattr(self, 'exams_table_user', None)
            if tbl is None:
                QMessageBox.warning(self, tr('common.error'), tr('error.select_exam'))
                return
            sm = tbl.selectionModel()
            if sm is None:
                QMessageBox.warning(self, tr('common.error'), tr('error.select_exam'))
                return
            rows = sm.selectedRows()
            if len(rows) == 0:
                QMessageBox.warning(self, tr('common.error'), tr('error.select_exam'))
                return
            if len(rows) > 1:
                QMessageBox.warning(self, tr('common.error'), tr('error.select_exam_single'))
                return
            r = rows[0].row()
            it = tbl.item(r, 0)
            exam_id = int(it.text()) if it and it.text() else None
        if not exam_id:
            QMessageBox.warning(self, tr('common.error'), tr('error.select_exam'))
            return
        qs = list_questions(int(exam_id))
        if not qs:
            QMessageBox.warning(self, tr('common.error'), tr('error.no_questions'))
            return
        ExamWindow(self.user, exam_id, self).show()
    def handle_logout(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'logout'):
            p = p.parent()
        if p is not None:
            p.logout()
