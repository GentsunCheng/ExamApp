from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QScrollArea, QLabel, QGroupBox, QHBoxLayout
from PySide6.QtGui import QKeySequence, QShortcut

from theme_manager import theme_manager
from models import PROGRESS_STATUS_IN_PROGRESS, PROGRESS_STATUS_COMPLETED


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
            row = QHBoxLayout()
            row.setSpacing(8)
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
                row.addWidget(box)
            row.addStretch()
            gb_lay.addLayout(row)
            gb.setLayout(gb_lay)
            v.addWidget(gb)

        v.addStretch()
        content.setLayout(v)
        scroll.setWidget(content)
        lay.addWidget(scroll)

        central.setLayout(lay)
        self.setCentralWidget(central)
