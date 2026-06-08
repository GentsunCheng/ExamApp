from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTableWidget,
    QTableWidgetItem, QAbstractItemView, QFileDialog, QDialog,
    QLineEdit, QComboBox, QLabel, QFormLayout, QDialogButtonBox, QHeaderView
)
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QMessageBox
from icon_manager import IconManager
from theme_manager import theme_manager
from language import tr
from utils import show_info, show_warn, ask_yes_no
from file_viewer import open_file_in_viewer
from models import (
    save_knowledge_file,
    list_knowledge_files,
    list_knowledge_categories,
    list_knowledge_uploaders,
    delete_knowledge_file,
    get_knowledge_file_path,
)
import os


class UploadKnowledgeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('knowledge.upload_title'))
        self.setFixedSize(400, 220)
        layout = QFormLayout()
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.setPlaceholderText(tr('knowledge.category_ph'))
        self.category_combo.currentTextChanged.connect(self.on_category_changed)
        layout.addRow(tr('knowledge.category'), self.category_combo)

        self.keywords_edit = QLineEdit()
        self.keywords_edit.setPlaceholderText(tr('knowledge.input_keywords'))
        layout.addRow(tr('knowledge.keywords'), self.keywords_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)
        self.setLayout(layout)
        self.selected_path = None
        self._refresh_categories()

    def _refresh_categories(self):
        self.category_combo.clear()
        self.category_combo.addItem('')
        for c in list_knowledge_categories():
            self.category_combo.addItem(c)

    def on_category_changed(self, text):
        pass

    def get_category(self):
        return self.category_combo.currentText().strip()

    def get_keywords(self):
        return self.keywords_edit.text().strip()


class KnowledgeBaseModule(QWidget):
    def __init__(self, user, is_admin=False, parent=None):
        super().__init__(parent)
        self.user = user
        self.is_admin = is_admin
        self.icon_manager = IconManager()
        lay = QVBoxLayout()

        toolbar_h = QHBoxLayout()
        share_btn = QPushButton(tr('knowledge.share'))
        share_btn.setIcon(self.icon_manager.get_icon('file'))
        share_btn.clicked.connect(self.share_file)
        toolbar_h.addWidget(share_btn)

        refresh_btn = QPushButton(tr('knowledge.refresh'))
        refresh_btn.setIcon(self.icon_manager.get_icon('refresh'))
        refresh_btn.clicked.connect(self.refresh_knowledge)
        toolbar_h.addWidget(refresh_btn)

        toolbar_h.addStretch()
        lay.addLayout(toolbar_h)

        filter_h = QHBoxLayout()
        self.keyword_edit = QLineEdit()
        self.keyword_edit.setPlaceholderText(tr('knowledge.filter_keyword'))
        self.keyword_edit.setClearButtonEnabled(True)
        filter_h.addWidget(self.keyword_edit)

        self.category_combo = QComboBox()
        self.category_combo.setPlaceholderText(tr('knowledge.filter_category'))
        self.category_combo.addItem(tr('knowledge.all'), '')
        self._refresh_filter_categories()
        filter_h.addWidget(self.category_combo)

        self.uploader_combo = QComboBox()
        self.uploader_combo.setPlaceholderText(tr('knowledge.filter_uploader'))
        self.uploader_combo.addItem(tr('knowledge.all'), '')
        self._refresh_filter_uploaders()
        filter_h.addWidget(self.uploader_combo)

        search_btn = QPushButton(tr('knowledge.search'))
        search_btn.setIcon(self.icon_manager.get_icon('search'))
        search_btn.clicked.connect(self.refresh_knowledge)
        filter_h.addWidget(search_btn)
        lay.addLayout(filter_h)

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            tr('knowledge.filename'), tr('knowledge.uploader'),
            tr('knowledge.category'), tr('knowledge.keywords'),
            tr('knowledge.uploaded_at'), ''
        ])
        self.table.setColumnWidth(0, 250)
        self.table.setColumnWidth(1, 100)
        self.table.setColumnWidth(2, 120)
        self.table.setColumnWidth(3, 200)
        self.table.setColumnWidth(4, 160)
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setShowGrid(False)
        self.table.itemDoubleClicked.connect(self.open_selected_file)
        lay.addWidget(self.table)

        self.setLayout(lay)
        self.refresh_knowledge()

    def _refresh_filter_categories(self):
        current = self.category_combo.currentData()
        self.category_combo.blockSignals(True)
        while self.category_combo.count() > 1:
            self.category_combo.removeItem(1)
        for c in list_knowledge_categories():
            self.category_combo.addItem(c, c)
        idx = self.category_combo.findData(current)
        if idx >= 0:
            self.category_combo.setCurrentIndex(idx)
        self.category_combo.blockSignals(False)

    def _refresh_filter_uploaders(self):
        current = self.uploader_combo.currentData()
        self.uploader_combo.blockSignals(True)
        while self.uploader_combo.count() > 1:
            self.uploader_combo.removeItem(1)
        for u in list_knowledge_uploaders():
            self.uploader_combo.addItem(u, u)
        idx = self.uploader_combo.findData(current)
        if idx >= 0:
            self.uploader_combo.setCurrentIndex(idx)
        self.uploader_combo.blockSignals(False)

    def refresh_knowledge(self):
        keyword = self.keyword_edit.text().strip() or None
        category = self.category_combo.currentData() or None
        uploader = self.uploader_combo.currentData() or None
        files = list_knowledge_files(keyword=keyword, category=category, uploader=uploader)
        colors = theme_manager.get_theme_colors()
        self.table.setRowCount(0)
        for f in files:
            r = self.table.rowCount()
            self.table.insertRow(r)

            it_name = QTableWidgetItem(f['filename'])
            it_name.setData(Qt.ItemDataRole.UserRole, f['id'])
            it_name.setData(Qt.ItemDataRole.UserRole + 1, f['sha1'])
            self.table.setItem(r, 0, it_name)
            self.table.setItem(r, 1, QTableWidgetItem(f['username']))
            self.table.setItem(r, 2, QTableWidgetItem(f['category']))
            self.table.setItem(r, 3, QTableWidgetItem(f['keywords']))
            self.table.setItem(r, 4, QTableWidgetItem(f['uploaded_at']))

            is_owner = (f['user_id'] == self.user['id'])
            del_btn = QPushButton(tr('common.delete'))
            del_btn.setStyleSheet(f"QPushButton {{ background-color:{colors.get('error','#f56c6c')}; color:#fff; padding:4px 8px; font-size:12px; border-radius:6px; }}")
            del_btn.clicked.connect(lambda checked, kb_id=f['id']: self._delete_file(kb_id))
            self.table.setCellWidget(r, 5, del_btn)

        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount() - 1):
                it = self.table.item(r, c)
                if it:
                    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def share_file(self):
        file_filter = "所有文件 (*);;文档文件 (*.doc *.docx *.xls *.xlsx *.ppt *.pptx *.pdf *.txt *.md)"
        paths, _ = QFileDialog.getOpenFileNames(self, tr('knowledge.share'), '', file_filter)
        if not paths:
            return
        dlg = UploadKnowledgeDialog(self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return
        category = dlg.get_category()
        keywords = dlg.get_keywords()
        ok_count = 0
        for path in paths:
            result = save_knowledge_file(path, self.user['id'], self.user['username'], category, keywords)
            if result:
                ok_count += 1
        if ok_count > 0:
            show_info(self, tr('common.success'), tr('knowledge.file_shared'))
            self.refresh_knowledge()

    def open_selected_file(self, item):
        row = item.row()
        it = self.table.item(row, 0)
        if not it:
            return
        sha1 = it.data(Qt.ItemDataRole.UserRole + 1)
        if not sha1:
            return
        path = get_knowledge_file_path(sha1)
        if path:
            open_file_in_viewer(path, self, original_name=it.text())

    def _delete_file(self, kb_id):
        reply = ask_yes_no(self, tr('common.confirm'), tr('knowledge.delete_confirm'), default_yes=False)
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            if delete_knowledge_file(kb_id, user_id=self.user['id'], is_admin=self.is_admin):
                show_info(self, tr('common.success'), tr('knowledge.file_deleted'))
                self.refresh_knowledge()
            else:
                show_warn(self, tr('common.error'), tr('knowledge.no_permission'))
        except Exception as e:
            show_warn(self, tr('common.error'), str(e))
