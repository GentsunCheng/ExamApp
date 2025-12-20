from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem, QLabel

from theme_manager import theme_manager
from language import tr
from models import list_exams, list_exam_user_overview


class AdminScoresOverviewModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout()
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        colors_scroll = theme_manager.get_theme_colors()
        self.scroll.setStyleSheet(
            f"QScrollArea {{ border:1px solid {colors_scroll['border']}; border-radius:8px; background-color:{colors_scroll['card_background']}; }}"
        )
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        self.scroll.setWidget(self.content_widget)
        lay.addWidget(self.scroll)
        lay.addStretch()
        self.setLayout(lay)
        self.refresh_overview()

    def make_tag(self, text, bg, fg):
        lab = QLabel(text)
        lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lab.setStyleSheet(f"QLabel {{ background-color:{bg}; color:{fg}; border-radius:10px; padding:2px 8px; font-size:12px; }}")
        return lab

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.deleteLater()
                continue
            child_layout = item.layout()
            if child_layout is not None:
                self._clear_layout(child_layout)

    def refresh_overview(self):
        self._clear_layout(self.content_layout)
        exams = list_exams(include_expired=True)
        for e in exams:
            exam_id = int(e[0])
            exam_title = e[1] or ''
            gb = QGroupBox(exam_title or f'Exam {exam_id}')
            vb = QVBoxLayout()
            tbl = QTableWidget(0, 6)
            tbl.setHorizontalHeaderLabels([
                tr('admin.users.headers.id'),
                tr('admin.users.headers.username'),
                tr('admin.users.headers.full_name'),
                tr('scores.headers.submitted'),
                tr('exams.best'),
                tr('progress.headers.status'),
            ])
            tbl.setColumnWidth(0, 60)
            tbl.setColumnWidth(1, 120)
            tbl.setColumnWidth(2, 140)
            tbl.setColumnWidth(3, 200)
            tbl.setColumnWidth(4, 100)
            tbl.setColumnWidth(5, 140)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setAlternatingRowColors(True)
            tbl.setShowGrid(False)
            rows = list_exam_user_overview(exam_id)
            for row in rows:
                r = tbl.rowCount()
                tbl.insertRow(r)
                uid = row[0]
                uname = row[1] or ''
                full_name = row[2] or ''
                last_ts = row[3] or ''
                best_score = row[4] or 0.0
                passed = int(row[5] or 0)
                tbl.setItem(r, 0, QTableWidgetItem(str(uid)))
                tbl.setItem(r, 1, QTableWidgetItem(uname))
                tbl.setItem(r, 2, QTableWidgetItem(full_name))
                tbl.setItem(r, 3, QTableWidgetItem(last_ts))
                tbl.setItem(r, 4, QTableWidgetItem(str(best_score)))
                status_text = tr('attempts.pass') if passed == 1 else tr('attempts.fail')
                badge_bg = '#e1f3d8' if passed == 1 else '#fde2e2'
                badge_fg = '#67c23a' if passed == 1 else '#f56c6c'
                tbl.setCellWidget(r, 5, self.make_tag(status_text, badge_bg, badge_fg))
            try:
                for r in range(tbl.rowCount()):
                    for c in range(tbl.columnCount()):
                        it = tbl.item(r, c)
                        if it:
                            it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            except Exception:
                pass
            vb.addWidget(tbl)
            gb.setLayout(vb)
            self.content_layout.addWidget(gb)
        self.content_layout.addStretch()

