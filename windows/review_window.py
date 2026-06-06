from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QSplitter,
    QTextEdit, QDoubleSpinBox, QWidget, QMessageBox, QFrame,
    QApplication
)
from theme_manager import theme_manager
from language import tr
from models import (
    get_unreviewed_essays, save_manual_review, recalculate_attempt_score,
    get_exam_title, get_user_name
)


class ReviewWindow(QDialog):
    def __init__(self, user, parent=None):
        super().__init__(parent)
        self.user = user
        self.items = []
        self.current_index = -1
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(int(screen.width() * 0.8), int(screen.height() * 0.7))
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        self.setWindowTitle(tr('admin.review.title'))
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.close)
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        colors = theme_manager.get_theme_colors()
        self.setStyleSheet(f"""
            QDialog {{ background-color:{colors['background']}; }}
            QLabel {{ font-size:14px; color:{colors['text_primary']}; }}
            QPushButton {{ 
                background-color:{colors['button_primary']}; 
                color:{colors['text_inverse']}; 
                padding:8px 16px; border:none; border-radius:8px; font-size:14px;
            }}
            QPushButton:hover {{ background-color:{colors['button_primary_hover']}; }}
            QPushButton:disabled {{ background-color:{colors['border_light']}; }}
            QTextEdit {{ 
                background-color:{colors['card_background']}; 
                color:{colors['text_primary']}; 
                border:1px solid {colors['border']}; 
                border-radius:8px; 
                padding:8px; 
                font-size:14px;
            }}
            QDoubleSpinBox {{ 
                background-color:{colors['input_background']}; 
                color:{colors['text_primary']}; 
                border:1px solid {colors['input_border']}; 
                border-radius:8px; 
                padding:6px; 
                font-size:14px;
                min-height:30px;
            }}
        """)

        main_layout = QHBoxLayout(self)

        # Left: table of pending items
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)

        self.count_label = QLabel()
        self.count_label.setStyleSheet(
            f"font-size:15px; font-weight:bold; color:{colors['primary']}; padding:4px 0;"
        )
        left_layout.addWidget(self.count_label)

        self.table = QTableWidget(0, 4)
        self.table.setAlternatingRowColors(True)
        self.table.setHorizontalHeaderLabels([
            tr('attempts.uuid'), tr('scores.headers.username'),
            tr('attempts.exam_title'), tr('common.question')
        ])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(2, 140)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.on_selection_changed)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color:{colors['card_background']};
                color:{colors['text_primary']};
                border:1px solid {colors['border']};
                border-radius:8px;
                font-size:13px;
                gridline-color: {colors['border_light']};
                outline: none;
            }}
            QTableWidget::item {{
                padding:8px 10px;
                border-bottom: 1px solid {colors['border_light']};
            }}
            QTableWidget::item:hover {{
                background-color: {colors['border_light']};
            }}
            QTableWidget::item:selected {{
                background-color: {colors['primary']};
                color: {colors['text_inverse']};
            }}
            QHeaderView::section {{
                background-color: {colors['background']};
                color: {colors['text_primary']};
                border: none;
                border-bottom: 2px solid {colors['primary']};
                padding: 10px 10px;
                font-weight: bold;
                font-size: 13px;
            }}
        """)
        left_layout.addWidget(self.table)

        self.refresh_btn = QPushButton(tr('common.refresh'))
        self.refresh_btn.clicked.connect(self.load_data)
        left_layout.addWidget(self.refresh_btn)

        # Right: detail panel
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        detail_frame = QFrame()
        detail_frame.setStyleSheet(f"QFrame {{ background-color:{colors['card_background']}; border:1px solid {colors['border']}; border-radius:8px; }}")
        detail_layout = QVBoxLayout(detail_frame)

        exam_title_font = f"font-size:16px; font-weight:bold; color:{colors['primary']};"
        self.detail_exam = QLabel()
        self.detail_exam.setStyleSheet(exam_title_font)
        detail_layout.addWidget(self.detail_exam)

        self.detail_question = QLabel()
        self.detail_question.setWordWrap(True)
        self.detail_question.setStyleSheet("font-size:15px; padding:4px 0;")
        detail_layout.addWidget(self.detail_question)

        self.detail_answer = QTextEdit()
        self.detail_answer.setReadOnly(True)
        self.detail_answer.setMinimumHeight(100)
        self.detail_answer.setStyleSheet(
            f"QTextEdit {{ background-color:{colors['background']}; "
            f"color:{colors['text_primary']}; border:1px solid {colors['primary']}; "
            f"border-radius:8px; padding:10px; font-size:15px; }}"
        )
        detail_layout.addWidget(QLabel(tr('exam.essay_answer') + ':'))
        detail_layout.addWidget(self.detail_answer)

        # Score input
        score_layout = QHBoxLayout()
        score_layout.addWidget(QLabel(tr('exam.review_score') + ':'))
        self.score_input = QDoubleSpinBox()
        self.score_input.setRange(0, 999)
        self.score_input.setDecimals(1)
        self.score_input.setSingleStep(0.5)
        self.score_input.setMinimumWidth(120)
        score_layout.addWidget(self.score_input)
        self.score_max_label = QLabel()
        score_layout.addWidget(self.score_max_label)
        score_layout.addStretch()
        detail_layout.addLayout(score_layout)

        # Comment input
        detail_layout.addWidget(QLabel(tr('exam.review_comment') + ':'))
        self.comment_input = QTextEdit()
        self.comment_input.setMaximumHeight(80)
        self.comment_input.setPlaceholderText(tr('exam.review_comment'))
        detail_layout.addWidget(self.comment_input)

        # Save button
        self.save_btn = QPushButton(tr('admin.review.save'))
        self.save_btn.clicked.connect(self.save_review)
        detail_layout.addWidget(self.save_btn)

        # Status label
        self.status_label = QLabel()
        self.status_label.setStyleSheet("font-size:13px; padding:4px 0;")
        detail_layout.addWidget(self.status_label)

        right_layout.addWidget(detail_frame)
        right_layout.addStretch()

        # Use splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        main_layout.addWidget(splitter)

    def load_data(self):
        self.items = get_unreviewed_essays()
        self.table.setRowCount(0)

        for item in self.items:
            r = self.table.rowCount()
            self.table.insertRow(r)
            self.table.setRowHeight(r, 36)
            uuid_item = QTableWidgetItem(item['attempt_uuid'][:8] + '...')
            uuid_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 0, uuid_item)
            username = get_user_name(item.get('user_id'))
            name_item = QTableWidgetItem(username)
            name_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(r, 1, name_item)
            exam_title = get_exam_title(int(item['exam_id'])) if item.get('exam_id') else ''
            self.table.setItem(r, 2, QTableWidgetItem(exam_title or ''))
            q = item.get('question') or {}
            q_text = q.get('text', '')[:50] + ('...' if len(q.get('text', '')) > 50 else '')
            self.table.setItem(r, 3, QTableWidgetItem(q_text))

        self.count_label.setText(f"{tr('admin.review.title')}: {len(self.items)} 条待批阅")
        self.clear_detail()

    def on_selection_changed(self):
        rows = self.table.selectedItems()
        if not rows:
            self.clear_detail()
            return
        row = rows[0].row()
        if row < 0 or row >= len(self.items):
            self.clear_detail()
            return
        self.current_index = row
        item = self.items[row]
        q = item.get('question') or {}
        exam_title = get_exam_title(int(item['exam_id'])) if item.get('exam_id') else ''

        self.detail_exam.setText(exam_title)
        self.detail_question.setText(q.get('text', ''))
        user_text = str(item['selected'][0]) if item.get('selected') and len(item['selected']) > 0 else ''
        self.detail_answer.setPlainText(user_text)
        self.score_input.setValue(0.0)
        self.score_input.setMaximum(float(q.get('score', 1)))
        self.score_max_label.setText(f"/ {q.get('score', 1)}")
        self.comment_input.clear()
        self.status_label.setText('')
        self.save_btn.setEnabled(True)

    def clear_detail(self):
        self.current_index = -1
        self.detail_exam.setText('')
        self.detail_question.setText('')
        self.detail_answer.setPlainText('')
        self.score_input.setValue(0.0)
        self.score_max_label.setText('')
        self.comment_input.clear()
        self.status_label.setText('')
        self.save_btn.setEnabled(False)

    def save_review(self):
        if self.current_index < 0 or self.current_index >= len(self.items):
            return
        item = self.items[self.current_index]
        score = self.score_input.value()
        comment = self.comment_input.toPlainText().strip()

        save_manual_review(
            attempt_uuid=item['attempt_uuid'],
            question_id=item['question_id'],
            reviewed_by=self.user['id'],
            manual_score=score,
            review_comment=comment if comment else None,
        )

        total, passed = recalculate_attempt_score(item['attempt_uuid'])
        colors = theme_manager.get_theme_colors()
        self.status_label.setStyleSheet(f"font-size:14px; color:{colors['success']}; padding:4px 0; font-weight:bold;")
        self.status_label.setText(
            f"{tr('admin.review.saved')}. {tr('admin.review.recalculated')} ({tr('attempts.score_label')}: {total})"
        )

        # Refresh: remove this item from the list (block signals to prevent auto-selection)
        self.table.blockSignals(True)
        del self.items[self.current_index]
        self.table.removeRow(self.current_index)
        self.table.clearSelection()
        self.table.blockSignals(False)
        self.count_label.setText(f"{tr('admin.review.title')}: {len(self.items)}")
        self.clear_detail()

        if len(self.items) == 0:
            QMessageBox.information(self, tr('common.success'), tr('admin.review.empty'))
