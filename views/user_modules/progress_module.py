from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QScrollArea, QTableWidget, QTableWidgetItem, QAbstractItemView, QHBoxLayout, QPushButton, QFileDialog, QDialog, QHeaderView, QLabel, QMessageBox

from icon_manager import IconManager
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn
from file_viewer import open_file_in_viewer
from models import (
    PROGRESS_STATUS_NOT_STARTED,
    PROGRESS_STATUS_IN_PROGRESS,
    PROGRESS_STATUS_COMPLETED,
    get_user_progress_tree,
    set_user_task_progress,
    save_task_file,
    delete_task_file,
    get_file_path,
)
from database import FILES_DIR

from windows.study_progress_overview_window import ProgressOverviewWindow

import os
import json


class UserProgressModule(QWidget):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.icon_manager = IconManager()
        self.user = user
        lay = QVBoxLayout()

        header = QGroupBox()
        hb = QHBoxLayout()
        hb.addStretch()
        btn_overview = QPushButton(tr('progress.overview'))
        btn_overview.setIcon(self.icon_manager.get_icon('score'))
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
            tbl = QTableWidget(0, 5)
            tbl.setHorizontalHeaderLabels([
                tr('progress.headers.task_title'),
                tr('progress.headers.description'),
                tr('progress.headers.order'),
                tr('progress.headers.status'),
                tr('progress.files'),
            ])
            tbl.setColumnWidth(0, 200)
            tbl.setColumnWidth(1, 400)
            tbl.setColumnWidth(2, 60)
            tbl.setColumnWidth(3, 100)
            tbl.setColumnWidth(4, 200)
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

                # Files column widget
                files_widget = QWidget()
                files_layout = QHBoxLayout()
                files_layout.setContentsMargins(4, 2, 4, 2)
                files_layout.setSpacing(4)

                task_files = t.get('files') or []
                task_id = int(t.get('task_id') or 0)

                # Upload button
                btn_upload = QPushButton(tr('progress.upload_file'))
                btn_upload.setStyleSheet("QPushButton { background-color:#409eff; color:#fff; padding:4px 8px; font-size:11px; border-radius:6px; }")
                btn_upload.clicked.connect(lambda checked, uid=user_id, tid=task_id: self.upload_file(uid, tid))
                files_layout.addWidget(btn_upload)

                if task_files:
                    # Show file count badge
                    lbl_count = QLabel(f"{len(task_files)}")
                    lbl_count.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    lbl_count.setStyleSheet("QLabel { background-color:#67c23a; color:#fff; border-radius:8px; padding:2px 6px; font-size:11px; font-weight:bold; }")
                    files_layout.addWidget(lbl_count)

                    btn_view = QPushButton(tr('progress.view_files'))
                    btn_view.setStyleSheet("QPushButton { background-color:#67c23a; color:#fff; padding:4px 8px; font-size:11px; border-radius:6px; }")
                    btn_view.clicked.connect(lambda checked, uid=user_id, tid=task_id: self.view_files(uid, tid))
                    files_layout.addWidget(btn_view)

                files_widget.setLayout(files_layout)
                tbl.setCellWidget(r, 4, files_widget)

            vb.addWidget(tbl)
            gb.setLayout(vb)
            self.content_layout.addWidget(gb)
        self.content_layout.addStretch()

    def upload_file(self, user_id, task_id):
        file_filter = "文档文件 (*.doc *.docx *.xls *.xlsx *.ppt *.pptx *.pdf *.png *.jpg *.jpeg *.gif *.bmp *.txt *.md *.csv *.json *.xml *.yaml *.yml *.log *.rtf);;所有文件 (*)"
        paths, _ = QFileDialog.getOpenFileNames(self, tr('progress.upload_file'), '', file_filter)
        if not paths:
            return
        # 获取当前进度记录
        tree = get_user_progress_tree(user_id)
        current_files = []
        current_status = PROGRESS_STATUS_NOT_STARTED
        for md in tree:
            for t in md.get('tasks') or []:
                if int(t.get('task_id') or 0) == task_id:
                    current_files = list(t.get('files') or [])
                    current_status = int(t.get('status') or PROGRESS_STATUS_NOT_STARTED)
                    break
        # 保存新文件
        for path in paths:
            meta = save_task_file(path)
            if meta:
                # 检查是否已存在相同sha1
                existing_shas = {f['sha1'] for f in current_files}
                if meta['sha1'] not in existing_shas:
                    current_files.append(meta)
        # 更新进度记录
        try:
            set_user_task_progress(user_id, task_id, current_status, updated_by='user', files=current_files)
            show_info(self, tr('common.success'), tr('progress.file_uploaded'))
            self.refresh_progress()
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    def view_files(self, user_id, task_id):
        tree = get_user_progress_tree(user_id)
        task_files = []
        task_title = ''
        for md in tree:
            for t in md.get('tasks') or []:
                if int(t.get('task_id') or 0) == task_id:
                    task_files = list(t.get('files') or [])
                    task_title = t.get('title') or ''
                    break
        if not task_files:
            show_info(self, tr('common.hint'), tr('progress.no_files'))
            return

        dlg = QDialog(self)
        dlg.setWindowTitle(tr('progress.file_list') + f' - {task_title}')
        dlg.resize(520, 380)
        colors = theme_manager.get_theme_colors()
        dlg.setStyleSheet(f"QDialog {{ background-color:{colors['card_background']}; }}")
        layout = QVBoxLayout()

        for fmeta in task_files:
            row = QHBoxLayout()
            lbl_name = QLabel(fmeta.get('original_name', ''))
            size_str = self._format_size(fmeta.get('size', 0))
            lbl_size = QLabel(f'({size_str})')
            lbl_size.setStyleSheet(f"color:{colors['text_secondary']}; font-size:12px;")

            btn_open = QPushButton('打开')
            btn_open.setStyleSheet("QPushButton { background-color:#409eff; color:#fff; padding:4px 12px; font-size:12px; border-radius:6px; }")
            sha1 = fmeta.get('sha1', '')
            btn_open.clicked.connect(lambda checked, s=sha1, oname=fmeta.get('original_name', ''): self.open_file(s, oname))

            btn_del = QPushButton('删除')
            btn_del.setStyleSheet("QPushButton { background-color:#f56c6c; color:#fff; padding:4px 12px; font-size:12px; border-radius:6px; }")
            btn_del.clicked.connect(lambda checked, uid=user_id, tid=task_id, sha1_val=sha1, d=dlg: self.delete_file_from_task(uid, tid, sha1_val, d))

            row.addWidget(lbl_name)
            row.addWidget(lbl_size)
            row.addStretch()
            row.addWidget(btn_open)
            row.addWidget(btn_del)
            layout.addLayout(row)

        close_btn = QPushButton(tr('common.close'))
        close_btn.setStyleSheet("QPushButton { background-color:#909399; color:#fff; padding:6px 16px; font-size:13px; border-radius:6px; }")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, 0, Qt.AlignmentFlag.AlignRight)

        dlg.setLayout(layout)
        dlg.exec()

    def open_file(self, sha1, original_name=''):
        path = get_file_path(sha1)
        if path and os.path.exists(path):
            open_file_in_viewer(path, self, original_name=original_name or None)

    def delete_file_from_task(self, user_id, task_id, sha1, dialog):
        reply = QMessageBox.question(self, tr('common.confirm'), tr('progress.confirm_delete_file'),
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        # 获取当前进度并移除文件
        tree = get_user_progress_tree(user_id)
        current_files = []
        current_status = PROGRESS_STATUS_NOT_STARTED
        for md in tree:
            for t in md.get('tasks') or []:
                if int(t.get('task_id') or 0) == task_id:
                    current_files = list(t.get('files') or [])
                    current_status = int(t.get('status') or PROGRESS_STATUS_NOT_STARTED)
                    break
        new_files = [f for f in current_files if f.get('sha1') != sha1]
        # 只删除文件（磁盘上的），不再检查引用
        delete_task_file(sha1)
        try:
            set_user_task_progress(user_id, task_id, current_status, updated_by='user', files=new_files)
            show_info(self, tr('common.success'), tr('progress.file_deleted'))
            dialog.accept()
            self.refresh_progress()
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))

    @staticmethod
    def _format_size(size_bytes):
        if size_bytes < 1024:
            return f'{size_bytes} B'
        elif size_bytes < 1024 * 1024:
            return f'{size_bytes / 1024:.1f} KB'
        else:
            return f'{size_bytes / (1024 * 1024):.1f} MB'

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
