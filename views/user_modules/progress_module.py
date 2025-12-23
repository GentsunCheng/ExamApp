from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QPushButton

from icon_manager import get_icon
from theme_manager import theme_manager
from language import tr
from models import (
    PROGRESS_STATUS_NOT_STARTED,
    PROGRESS_STATUS_IN_PROGRESS,
    PROGRESS_STATUS_COMPLETED,
    get_user_progress_tree,
)

from windows.progress_overview_window import ProgressOverviewWindow


class UserProgressModule(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        lay = QVBoxLayout()

        header = QGroupBox()
        hb = QHBoxLayout()
        hb.addStretch()
        btn_overview = QPushButton(tr('progress.overview'))
        btn_overview.setIcon(get_icon('score'))
        btn_overview.clicked.connect(self.open_overview)
        hb.addWidget(btn_overview)
        header.setLayout(hb)
        lay.addWidget(header)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout()
        self.content_widget.setLayout(self.content_layout)
        self.scroll.setWidget(self.content_widget)
        lay.addWidget(self.scroll)

        lay.addStretch()
        self.setLayout(lay)
        self.refresh_progress()

        self.overview_window = None

    def refresh_progress(self):
        self._clear_layout(self.content_layout)
        user_id = int(self.user.get('id') or 0)
        if user_id <= 0:
            return
        tree = get_user_progress_tree(user_id)
        for md in tree:
            gb = QGroupBox(md.get('module_name') or '')
            vb = QVBoxLayout()
            tbl = QTableWidget(0, 4)
            tbl.setHorizontalHeaderLabels([
                tr('progress.headers.task_title'),
                tr('progress.headers.description'),
                tr('progress.headers.order'),
                tr('progress.headers.status'),
            ])
            tbl.setColumnWidth(0, 240)
            tbl.setColumnWidth(1, 520)
            tbl.setColumnWidth(2, 80)
            tbl.setColumnWidth(3, 120)
            tbl.horizontalHeader().setStretchLastSection(True)
            tbl.setAlternatingRowColors(True)
            tbl.setShowGrid(False)
            tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
            tbl.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
            tbl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            tbl.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)

            tasks = md.get('tasks') or []
            tbl.setRowCount(len(tasks))
            for r, t in enumerate(tasks):
                it_title = QTableWidgetItem(t.get('title') or '')
                it_title.setFlags(Qt.ItemFlag.ItemIsEnabled)
                tbl.setItem(r, 0, it_title)

                it_desc = QTableWidgetItem(t.get('description') or '')
                it_desc.setFlags(Qt.ItemFlag.ItemIsEnabled)
                tbl.setItem(r, 1, it_desc)

                it_order = QTableWidgetItem(str(int(t.get('sort_order') or 0)))
                it_order.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_order.setFlags(Qt.ItemFlag.ItemIsEnabled)
                tbl.setItem(r, 2, it_order)

                status = int(t.get('status') or 0)
                it_status = QTableWidgetItem(self._status_text(status))
                it_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                it_status.setFlags(Qt.ItemFlag.ItemIsEnabled)
                self._apply_status_style(it_status, status)
                tbl.setItem(r, 3, it_status)

            vb.addWidget(tbl)
            gb.setLayout(vb)
            self.content_layout.addWidget(gb)
        self.content_layout.addStretch()

    @staticmethod
    def _apply_status_style(item, status):
        colors = theme_manager.get_theme_colors()
        if int(status) == PROGRESS_STATUS_COMPLETED:
            bg = '#67c23a'
            fg = '#ffffff'
        elif int(status) == PROGRESS_STATUS_IN_PROGRESS:
            bg = colors.get('primary') or '#409eff'
            fg = '#ffffff'
        else:
            bg = '#909399'
            fg = '#ffffff'
        item.setBackground(QColor(bg))
        item.setForeground(QColor(fg))

    @staticmethod
    def _status_text(status):
        if int(status) == PROGRESS_STATUS_COMPLETED:
            return tr('progress.status.completed')
        if int(status) == PROGRESS_STATUS_IN_PROGRESS:
            return tr('progress.status.in_progress')
        return tr('progress.status.not_started')

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

    def open_overview(self):
        try:
            user_id = int(self.user.get('id') or 0)
        except Exception:
            user_id = 0
        if user_id <= 0:
            return
        tree = get_user_progress_tree(user_id)
        username = self.user.get('username') or ''
        title = tr('progress.overview.title', user=username)
        self.overview_window = ProgressOverviewWindow(title, tree, self)
        self.overview_window.show()
        try:
            self.overview_window.raise_()
            self.overview_window.activateWindow()
        except Exception:
            pass
