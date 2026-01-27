from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from theme_manager import theme_manager
from language import tr
from models import list_attempts, get_exam_title
from PySide6.QtGui import QColor


class UserHistoryModule(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        history_v = QVBoxLayout()
        self.attempts_table = QTableWidget(0, 5)
        self.attempts_table.setHorizontalHeaderLabels([tr('attempts.uuid'), tr('attempts.exam_title'), tr('attempts.started'), tr('attempts.submitted'), tr('attempts.score_total_status')])
        self.attempts_table.setColumnWidth(0, 280)
        self.attempts_table.setColumnWidth(1, 250)
        self.attempts_table.setColumnWidth(2, 200)
        self.attempts_table.setColumnWidth(3, 200)
        self.attempts_table.horizontalHeader().setStretchLastSection(True)
        self.attempts_table.setAlternatingRowColors(True)
        self.attempts_table.setShowGrid(False)
        self.refresh_attempts()
        history_v.addWidget(self.attempts_table)
        self.setLayout(history_v)
    def refresh_attempts(self):
        self.attempts_table.setRowCount(0)
        for a in list_attempts(self.user['id'], self.user['username']):
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
