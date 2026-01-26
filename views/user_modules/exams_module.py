from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem, QAbstractItemView
from PySide6.QtGui import QColor
from icon_manager import IconManager
from theme_manager import theme_manager
from language import tr
from models import list_exams, list_attempts, get_exam_stats


class UserExamsModule(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.icon_manager = IconManager()
        self.user = user
        exams_v = QVBoxLayout()
        exams_toolbar = QHBoxLayout()
        start_btn = QPushButton(tr('user.start_exam'))
        start_btn.setIcon(self.icon_manager.get_icon('exam_start'))
        start_btn.clicked.connect(self.on_start_button_clicked)
        try:
            import sys
            print("[DEBUG] exams_module start button connected", file=sys.stderr)
        except Exception:
            pass
        exams_toolbar.addWidget(start_btn)
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
        self.exams_table_user.setShowGrid(False)
        self.exams_table_user.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.exams_table_user.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        try:
            self.exams_table_user.itemDoubleClicked.connect(lambda *_: self._start_via_parent())
        except Exception:
            pass
        self.refresh_exams()
        exams_v.addWidget(self.exams_table_user)
        self.setLayout(exams_v)
    def _start_via_parent(self):
        p = self.parent()
        while p is not None and not hasattr(p, 'start_exam'):
            p = p.parent()
        if p is not None:
            p.start_exam(None)
        else:
            try:
                import sys
                print("[DEBUG] no ancestor provides start_exam", file=sys.stderr)
            except Exception:
                pass
    def on_start_button_clicked(self):
        try:
            import sys
            print("[DEBUG] start button clicked", file=sys.stderr)
        except Exception:
            pass
        self._start_via_parent()
    def get_selected_exam_id(self):
        tbl = getattr(self, 'exams_table_user', None)
        if tbl is None:
            return None
        sm = tbl.selectionModel()
        if sm is None:
            return None
        rows = sm.selectedRows()
        if len(rows) != 1:
            return None
        r = rows[0].row()
        it = tbl.item(r, 0)
        return int(it.text()) if it and it.text() else None
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
        try:
            if tbl.rowCount() > 0 and tbl.currentRow() < 0:
                tbl.selectRow(0)
        except Exception:
            pass
