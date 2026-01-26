from PySide6.QtCore import Qt, QPoint, QRect, QSize
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QGroupBox, QLayout
from PySide6.QtGui import QKeySequence, QShortcut

from theme_manager import theme_manager
from models import PROGRESS_STATUS_IN_PROGRESS, PROGRESS_STATUS_COMPLETED
from language import tr


class FlowLayout(QLayout):
    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        if margin != 0:
            self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing)
        self.itemList = []

    def __del__(self):
        item = self.takeAt(0)
        while item:
            item = self.takeAt(0)

    def addItem(self, item):
        self.itemList.append(item)

    def count(self):
        return len(self.itemList)

    def itemAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self.itemList):
            return self.itemList.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        height = self.doLayout(QRect(0, 0, width, 0), True)
        return height

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self.doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self.itemList:
            size = size.expandedTo(item.minimumSize())
        left, top, right, bottom = self.getContentsMargins()
        size += QSize(left + right, top + bottom)
        return size

    def doLayout(self, rect, testOnly):
        left, top, right, bottom = self.getContentsMargins()
        effectiveRect = rect.adjusted(+left, +top, -right, -bottom)
        x = effectiveRect.x()
        y = effectiveRect.y()
        lineHeight = 0

        for item in self.itemList:
            wid = item.widget()
            spaceX = self.spacing()
            if spaceX == -1:
                spaceX = wid.style().layoutSpacing(
                    wid.sizePolicy().controlType(),
                    wid.sizePolicy().controlType(),
                    Qt.Orientation.Horizontal
                )
            spaceY = self.spacing()
            if spaceY == -1:
                spaceY = wid.style().layoutSpacing(
                    wid.sizePolicy().controlType(),
                    wid.sizePolicy().controlType(),
                    Qt.Orientation.Vertical
                )
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > effectiveRect.right() and lineHeight > 0:
                x = effectiveRect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0

            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))

            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())

        return y + lineHeight - rect.y() + bottom


class ProgressOverviewWindow(QMainWindow):
    def __init__(self, title, tree, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or tr('progress.overview'))
        colors = theme_manager.get_theme_colors()
        self.resize(960, 720)
        central = QWidget()
        lay = QVBoxLayout()

        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.close)

        lbl = QLabel(title or tr('progress.overview'))
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setStyleSheet(f"QLabel {{ font-size:16px; color:{colors['text_primary']}; padding:8px 0; }}")
        lay.addWidget(lbl)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(
            f"QScrollArea {{ border:1px solid {colors['border']}; border-radius:8px; background-color:{colors['card_background']}; }}"
        )

        content = QWidget()
        v = QVBoxLayout()

        for md in tree or []:
            name = md.get('module_name') or ''
            tasks = md.get('tasks') or []
            if not tasks:
                continue
            gb = QGroupBox(name)
            gb_lay = QVBoxLayout()
            flow = FlowLayout()
            flow.setSpacing(8)
            sorted_tasks = sorted(tasks, key=lambda x: int(x.get('sort_order') or 0))
            for t in sorted_tasks:
                title_text = t.get('title') or ''
                status = int(t.get('status') or 0)
                if status == PROGRESS_STATUS_COMPLETED:
                    bg = '#e1f3d8'
                    fg = '#67c23a'
                elif status == PROGRESS_STATUS_IN_PROGRESS:
                    bg = '#d9ecff'
                    fg = colors.get('primary') or '#409eff'
                else:
                    bg = '#f4f4f5'
                    fg = colors.get('text_secondary') or '#909399'
                box = QLabel(title_text)
                box.setAlignment(Qt.AlignmentFlag.AlignCenter)
                box.setStyleSheet(
                    f"QLabel {{ background-color:{bg}; color:{fg}; border-radius:8px; padding:4px 10px; font-size:13px; }}"
                )
                flow.addWidget(box)
            gb_lay.addLayout(flow)
            gb.setLayout(gb_lay)
            v.addWidget(gb)

        v.addStretch()
        content.setLayout(v)
        scroll.setWidget(content)
        lay.addWidget(scroll)

        central.setLayout(lay)
        self.setCentralWidget(central)
