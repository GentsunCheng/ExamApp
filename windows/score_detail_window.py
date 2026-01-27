from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QWidget,
    QFrame, QPushButton, QGroupBox, QGridLayout, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QKeySequence, QShortcut
from theme_manager import theme_manager
from language import tr
from models import get_attempt, get_attempt_answers, list_questions, get_exam_title, grade_question, get_pic
import json
from datetime import datetime


class ScoreDetailWindow(QDialog):
    def __init__(self, attempt_uuid, parent=None):
        super().__init__(parent)
        self.attempt_uuid = attempt_uuid
        self.questions = []
        self.user_answers = {}
        self.current_index = 0
        self.nav_buttons = []
        screen = QApplication.primaryScreen().availableGeometry()
        self.setMinimumSize(int(screen.width() / 2), int(screen.height() / 2))
        self.resize(int(screen.width() * 0.6), int(screen.height() * 0.6))
        size = self.geometry()
        self.move((screen.width() - size.width()) // 2, (screen.height() - size.height()) // 2)
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.close)
        self.shortcut_next_q = QShortcut(Qt.Key.Key_PageDown, self)
        self.shortcut_next_q.activated.connect(self.next_q)
        self.shortcut_prev_q = QShortcut(Qt.Key.Key_PageUp, self)
        self.shortcut_prev_q.activated.connect(self.prev_q)
        
        screen = QApplication.primaryScreen().availableGeometry()
        self.pic_width = min(screen.width(), screen.height()) / 2
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        colors = theme_manager.get_theme_colors()
        
        # Exact same base style as ExamWindow
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        br = 'border' + '-radius'
        
        self.setStyleSheet(f"""
            QDialog {{ {bkg}:{colors['background']}; }}
            QLabel {{ {fs}:16px; {col}:{colors['text_primary']}; }}
            QPushButton {{ 
                {bkg}:{colors['button_primary']}; 
                {col}:{colors['text_inverse']}; 
                {pd}:8px 16px; 
                border:none; 
                {br}:8px; 
                {fs}:14px; 
            }}
            QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}
            QPushButton:disabled {{ {bkg}:{colors['border_light']}; {col}:{colors['text_inverse']}; }}
        """)

        self.main_layout = QHBoxLayout(self)
        self.main_layout.setContentsMargins(12, 12, 12, 12)
        self.main_layout.setSpacing(12)

        # Left: Navigation Panel (Exactly like ExamWindow)
        self.nav_box = QGroupBox(tr('exam.nav_title'))
        self.nav_layout = QGridLayout()
        self.nav_box.setStyleSheet(
            f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:8px; padding:8px; font-size:13px; color:{colors['text_primary']}; }}"
        )
        self.nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self.nav_box.setLayout(self.nav_layout)
        
        # Wrap nav_box in a layout to match ExamWindow's structure
        left_container = QVBoxLayout()
        left_container.addWidget(self.nav_box)
        left_container.addStretch()
        self.main_layout.addLayout(left_container)

        # Right Panel
        self.right_panel = QVBoxLayout()
        
        # Header Info (Replacement for Timer/Progress Bar area)
        self.info_container = QFrame()
        self.info_container.setStyleSheet(f"QFrame {{ background-color:{colors['card_background']}; border:1px solid {colors['border']}; border-radius:8px; }}")
        info_layout = QHBoxLayout(self.info_container)
        info_layout.setContentsMargins(15, 10, 15, 10)
        
        self.exam_title_label = QLabel()
        self.exam_title_label.setStyleSheet(f"font-weight: bold; color: {colors['primary']}; font-size: 18px;")
        
        # Right info container (Score and Time)
        right_info_layout = QVBoxLayout()
        right_info_layout.setSpacing(2)
        
        self.score_label = QLabel()
        self.score_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.time_label = QLabel()
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.time_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 13px;")
        
        right_info_layout.addWidget(self.score_label)
        right_info_layout.addWidget(self.time_label)
        
        info_layout.addWidget(self.exam_title_label)
        info_layout.addStretch()
        info_layout.addLayout(right_info_layout)
        self.right_panel.addWidget(self.info_container)

        # Question Content Scroll Area (Exactly like ExamWindow)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"QScrollArea {{ border:1px solid {colors['border']}; border-radius:8px; background-color: transparent; }}")
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        self.vb = QVBoxLayout(scroll_content)
        self.vb.setContentsMargins(12, 12, 12, 12)
        self.vb.setSpacing(15)
        
        self.q_title = QLabel('')
        self.q_title.setWordWrap(True)
        self.q_title.setStyleSheet("font-size:16px; margin-bottom:8px;")
        
        self.q_picture_layout = QGridLayout()
        self.q_picture_layout.setSpacing(10)
        
        self.opts_container = QWidget()
        self.opts_layout = QVBoxLayout()
        self.opts_layout.setSpacing(8)
        self.opts_layout.setContentsMargins(0, 0, 0, 0)
        self.opts_container.setLayout(self.opts_layout)
        
        self.vb.addWidget(self.q_title)
        self.vb.addLayout(self.q_picture_layout)
        self.vb.addWidget(self.opts_container)
        self.vb.addStretch()
        
        self.scroll_area.setWidget(scroll_content)
        self.right_panel.addWidget(self.scroll_area)

        # Bottom Buttons (Exactly like ExamWindow)
        hb = QHBoxLayout()
        self.prev_btn = QPushButton(tr('exam.prev'))
        self.next_btn = QPushButton(tr('exam.next'))
        self.close_btn = QPushButton(tr('common.confirm'))
        
        # Use same button logic as ExamWindow
        self.prev_btn.clicked.connect(self.prev_q)
        self.next_btn.clicked.connect(self.next_q)
        self.close_btn.clicked.connect(self.accept)
        
        hb.addWidget(self.prev_btn)
        hb.addWidget(self.next_btn)
        hb.addStretch()
        hb.addWidget(self.close_btn)
        self.right_panel.addLayout(hb)

        self.main_layout.addLayout(self.right_panel, 1)

    def load_data(self):
        attempt = get_attempt(self.attempt_uuid)
        if not attempt:
            return

        exam_title = get_exam_title(attempt['exam_id'])
        self.exam_title_label.setText(exam_title or tr('attempts.detail_title'))
        self.setWindowTitle(f"{tr('attempts.detail_title')} - {exam_title}")
        
        status_text = tr('attempts.pass') if attempt['passed'] else tr('attempts.fail')
        score_info = f"{tr('attempts.score_label')}: {attempt['score']} / {attempt['total_score']} ({status_text})"
        
        # Set score label color based on pass status
        colors = theme_manager.get_theme_colors()
        score_color = colors['success'] if attempt['passed'] else colors['error']
        self.score_label.setStyleSheet(f"font-weight: bold; color: {score_color}; font-size: 16px;")

        # Time details
        time_info = ""
        try:
            start_dt = datetime.fromisoformat(attempt['started_at'].replace('Z', '+00:00'))
            start_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')
            time_info += f"{tr('attempts.started')}: {start_str}"
            
            if attempt['submitted_at']:
                end_dt = datetime.fromisoformat(attempt['submitted_at'].replace('Z', '+00:00'))
                end_str = end_dt.strftime('%Y-%m-%d %H:%M:%S')
                duration = end_dt - start_dt
                
                # Format duration: HH:MM:SS
                total_seconds = int(duration.total_seconds())
                h = total_seconds // 3600
                m = (total_seconds % 3600) // 60
                s = total_seconds % 60
                dur_str = f"{h:02d}:{m:02d}:{s:02d}"
                
                time_info += f"  |  {tr('attempts.submitted')}: {end_str}  |  {tr('attempts.duration')}: {dur_str}"
        except Exception:
            pass
            
        self.score_label.setText(score_info)
        self.time_label.setText(time_info)

        self.questions = list_questions(attempt['exam_id'])
        self.user_answers = get_attempt_answers(self.attempt_uuid)
        
        # Setup navigation buttons (3 columns like ExamWindow)
        colors = theme_manager.get_theme_colors()
        for i in range(len(self.questions)):
            row = i // 3
            col = i % 3
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            
            # Color based on correctness
            ans_data = self.user_answers.get(self.questions[i]['id'])
            user_ans = ans_data['selected'] if ans_data else None
            is_correct = grade_question(self.questions[i], user_ans)
            is_cheat = ans_data['cheat'] if ans_data else False
            
            if is_cheat:
                bg = colors['warning_light']
                fg = colors['warning']
            elif is_correct:
                bg = colors['success_light']
                fg = colors['success']
            else:
                bg = colors['error_light']
                fg = colors['error']
                
            btn.setStyleSheet(
                f"QPushButton {{ background-color:{bg}; color:{fg}; border-radius:8px; padding:6px 10px; min-width:32px; border:1px solid transparent; font-weight:bold; }}\n"
                f"QPushButton:hover {{ border-color:{colors['primary']}; }}\n"
                f"QPushButton:checked {{ border-color:{colors['text_primary']}; border-width:2px; }}"
            )
            
            btn.clicked.connect(lambda checked, idx=i: self.goto_question(idx))
            self.nav_layout.addWidget(btn, row, col)
            self.nav_buttons.append(btn)

        self.goto_question(0)

    def goto_question(self, index):
        self.current_index = index
        for i, btn in enumerate(self.nav_buttons):
            btn.setChecked(i == index)
        self.render_question()
        self.update_nav_buttons_state()

    def prev_q(self):
        if self.current_index > 0:
            self.goto_question(self.current_index - 1)

    def next_q(self):
        if self.current_index < len(self.questions) - 1:
            self.goto_question(self.current_index + 1)

    def update_nav_buttons_state(self):
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.questions) - 1)

    def render_question(self):
        if not self.questions:
            return
            
        q = self.questions[self.current_index]
        ans_data = self.user_answers.get(q['id'])
        user_ans = ans_data['selected'] if ans_data else None
        
        colors = theme_manager.get_theme_colors()
        
        # 1. Title
        tlabel = tr('exam.type.' + str(q.get('type')))
        self.q_title.setText(tr('exam.question_title', index=self.current_index+1, total=len(self.questions), text=q["text"], type=tlabel, score=q["score"]))
        
        # 2. Pictures
        while self.q_picture_layout.count():
            item = self.q_picture_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        pic_hashes = []
        try:
            if q.get('pictures'):
                pic_hashes = json.loads(q['pictures'])
        except Exception:
            pass
            
        for i, ph in enumerate(pic_hashes):
            q_img = get_pic(ph, max_dim=int(self.pic_width)) 
            if q_img:
                img_label = QLabel()
                img_label.setPixmap(QPixmap.fromImage(q_img))
                img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                img_label.setStyleSheet(f"border: 1px solid {colors['border']}; border-radius: 8px;")
                self.q_picture_layout.addWidget(img_label, 0, i)

        # 3. Options (Exactly like ExamWindow)
        while self.opts_layout.count():
            item = self.opts_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        is_q_correct = grade_question(q, user_ans)

        if q['type'] == 'truefalse':
            options = [(tr('exam.true'), True), (tr('exam.false'), False)]
            for label, val in options:
                btn = QPushButton(label)
                btn.setStyleSheet(self.get_option_style(q, val, user_ans))
                self.opts_layout.addWidget(btn)
        else:
            raw_opts = q['options'] or []
            for i, opt in enumerate(raw_opts):
                if isinstance(opt, dict):
                    key = opt.get('key')
                    text = opt.get('text') or str(key)
                else:
                    key = opt
                    text = str(opt)
                
                label = chr(65 + i) if i < 26 else str(i + 1)
                btn = QPushButton(f"{label}. {text}")
                btn.setStyleSheet(self.get_option_style(q, key, user_ans))
                self.opts_layout.addWidget(btn)

    def get_option_style(self, q, current_val, user_ans):
        colors = theme_manager.get_theme_colors()
        
        # Determine if this option is selected by user
        is_selected = False
        if user_ans is not None:
            if isinstance(user_ans, list):
                is_selected = current_val in user_ans
            else:
                is_selected = current_val == user_ans
            
        # Determine if this option is correct
        correct_ans = q['correct']
        is_correct = False
        if isinstance(correct_ans, list):
            is_correct = current_val in correct_ans
        else:
            is_correct = current_val == correct_ans
            
        bg = colors['card_background']
        border = colors['input_border']
        text_color = colors['text_primary']
        
        if is_correct:
            # Always show correct answers in green
            bg = colors['success_light']
            border = colors['success']
            text_color = colors['success']
        elif is_selected:
            # If selected but not correct, show in red
            bg = colors['error_light']
            border = colors['error']
            text_color = colors['error']
        
        return f"""
            QPushButton {{
                background-color: {bg};
                color: {text_color};
                border: 1px solid {border};
                border-radius: 12px;
                padding: 12px 16px;
                font-size: 16px;
                text-align: left;
                min-height: 44px;
            }}
        """

