import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox
from theme_manager import theme_manager
from icon_manager import get_icon
from exam_interface import ModernTimer, ModernProgressBar
from models import list_questions, start_attempt, save_answer, submit_attempt, list_exams
from PySide6.QtWidgets import QMessageBox

class ExamWindow(QMainWindow):
    instance = None
    def __init__(self, user, exam_id, parent=None):
        super().__init__(parent)
        if ExamWindow.instance is not None and ExamWindow.instance.isVisible():
            QMessageBox.information(self, '提示', '已有考试正在进行')
            try:
                ExamWindow.instance.raise_()
                ExamWindow.instance.activateWindow()
            except Exception:
                pass
            self.close()
            return
        ExamWindow.instance = self
        self._submitted = False
        self.resize(900, 600)
        self.user = user
        self.exam_id = exam_id
        questions = list_questions(exam_id)
        questions_len = len(questions)
        self.questions = []
        self.total_score = 0
        for _ in range(questions_len):
            rand_q = random.choice(questions)
            self.questions.append(rand_q)
            self.total_score += rand_q["score"]
            questions.remove(rand_q)
        self.attempt_uuid = start_attempt(user['id'], exam_id)
        self.current_index = 0
        self.setWindowTitle(f'考试进行中, 总分: {self.total_score}')
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, True)
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        colors = theme_manager.get_theme_colors()
        bkg = 'background' + '-color'
        col = 'co' + 'lor'
        bd = 'bor' + 'der'
        pd = 'pad' + 'ding'
        fs = 'font' + '-size'
        br = 'border' + '-radius'
        ss_exam = (
            f"QMainWindow {{ {bkg}:{colors['background']}; }}\n"
            f"QLabel {{ {fs}:16px; {col}:{colors['text_primary']}; }}\n"
            f"QPushButton {{ {bkg}:{colors['button_primary']}; {col}:{colors['text_inverse']}; {pd}:8px 16px; border:none; {br}:8px; {fs}:14px; }}\n"
            f"QPushButton:hover {{ {bkg}:{colors['button_primary_hover']}; }}\n"
            f"QPushButton:disabled {{ {bkg}:{colors['border_light']}; {col}:{colors['text_inverse']}; }}\n"
            f"QListWidget {{ {bd}:1px solid {colors['border']}; {br}:8px; {pd}:4px; {bkg}:{colors['card_background']}; {col}:{colors['text_primary']}; }}\n"
            f"QListWidget::item {{ {pd}:6px; }}\n"
            f"QListWidget::item:selected {{ {bkg}:{colors['primary']}; {col}:{colors['text_inverse']}; }}\n"
        )
        self.setStyleSheet(ss_exam)
        central = QWidget()
        lay = QVBoxLayout()
        self.timer_widget = ModernTimer()
        lay.addWidget(self.timer_widget)
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setRange(0, max(1, len(self.questions)))
        self.progress_bar.setValue(1)
        lay.addWidget(self.progress_bar)
        gb = QGroupBox()
        gb.setStyleSheet(f"QGroupBox {{ border:1px solid {colors['border']}; border-radius:8px; padding:12px; }}")
        vb = QVBoxLayout()
        self.q_title = QLabel('')
        self.q_title.setWordWrap(True)
        self.q_title.setStyleSheet("font-size:16px; margin-bottom:8px;")
        self.opts_container = QWidget()
        self.opts_layout = QVBoxLayout()
        self.opts_layout.setSpacing(8)
        self.opts_container.setLayout(self.opts_layout)
        vb.addWidget(self.q_title)
        vb.addWidget(self.opts_container)
        gb.setLayout(vb)
        lay.addWidget(gb)
        hb = QHBoxLayout()
        self.prev_btn = QPushButton('上一题')
        self.next_btn = QPushButton('下一题')
        self.submit_btn = QPushButton('提交')
        self.submit_btn.setIcon(get_icon('submit'))
        self.next_btn.setDefault(True)
        self.submit_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_q)
        self.next_btn.clicked.connect(self.next_q)
        self.submit_btn.clicked.connect(self.submit)
        hb.addWidget(self.prev_btn)
        hb.addWidget(self.next_btn)
        hb.addStretch()
        hb.addWidget(self.submit_btn)
        lay.addLayout(hb)
        central.setLayout(lay)
        self.setCentralWidget(central)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.answers = {}
        tl = 0
        for e in list_exams(include_expired=True):
            if e[0] == exam_id:
                tl = int(e[4])
                break
        self.remaining = tl * 60
        self.timer.start(1000)
        self.timer_widget.start_timer(self.remaining)
        self.render_q()
    def all_answered(self):
        for q in self.questions:
            sel = self.answers.get(q['id'])
            if q['type'] in ('single', 'truefalse'):
                if not sel or len(sel) != 1:
                    return False
            elif q['type'] == 'multiple':
                if not sel or len(sel) == 0:
                    return False
            else:
                if not sel:
                    return False
        return True
    def update_buttons_state(self):
        self.prev_btn.setEnabled(self.current_index > 0)
        self.next_btn.setEnabled(self.current_index < len(self.questions) - 1)
        self.submit_btn.setEnabled(self.all_answered())
    def tick(self):
        self.remaining -= 1
        if self.remaining <= 0:
            self.submit()
            return
        self.progress_bar.setValue(min(len(self.questions), self.current_index + 1))
    def render_q(self):
        if self.current_index < 0:
            self.current_index = 0
        if self.current_index >= len(self.questions):
            self.current_index = len(self.questions) - 1
        q = self.questions[self.current_index]
        self.q_title.setText(f'{self.current_index+1}/{len(self.questions)} {q["text"]} ({q["type"]} 分值:{q["score"]})')
        # 清空旧选项
        while self.opts_layout.count():
            child = self.opts_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        self.opt_buttons = []
        # 构建选项按钮
        colors = theme_manager.get_theme_colors()
        btn_style = (
            f"QPushButton {{ background-color:{colors['card_background']}; color:{colors['text_primary']}; "
            f"border:1px solid {colors['input_border']}; border-radius:12px; padding:12px 16px; font-size:16px; text-align:left; min-height:44px; }}\n"
            f"QPushButton:hover {{ background-color:{colors['border_light']}; }}\n"
            f"QPushButton:checked {{ background-color:{colors['primary']}; color:{colors['text_inverse']}; border-color:{colors['primary']}; }}"
        )
        if q['type'] == 'truefalse':
            for label, val in [('正确', True), ('错误', False)]:
                btn = QPushButton(label)
                btn.setCheckable(True)
                btn.setStyleSheet(btn_style)
                btn.setProperty('tf_value', val)
                btn.clicked.connect(lambda checked, b=btn: self.on_option_clicked(b))
                self.opts_layout.addWidget(btn)
                self.opt_buttons.append(btn)
        else:
            for opt in q['options']:
                text = f"{opt.get('key')}. {opt.get('text')}"
                btn = QPushButton(text)
                btn.setCheckable(True)
                btn.setStyleSheet(btn_style)
                btn.setProperty('key', opt.get('key'))
                btn.clicked.connect(lambda checked, b=btn: self.on_option_clicked(b))
                self.opts_layout.addWidget(btn)
                self.opt_buttons.append(btn)
        # 回填已选择
        sel = self.answers.get(q['id'])
        if sel:
            if q['type'] == 'truefalse' and len(sel) == 1:
                for b in self.opt_buttons:
                    val = b.property('tf_value')
                    b.setChecked(bool(val) is bool(sel[0]) and val == sel[0])
            else:
                sset = set(sel)
                for b in self.opt_buttons:
                    key = b.property('key')
                    b.setChecked(key in sset if key is not None else False)
        self.update_buttons_state()
        self.progress_bar.setValue(self.current_index + 1)
    def collect_selected(self):
        q = self.questions[self.current_index]
        selected = []
        for b in getattr(self, 'opt_buttons', []):
            if b.isChecked():
                if q['type'] == 'truefalse':
                    selected = [bool(b.property('tf_value'))]
                else:
                    selected.append(str(b.property('key')))
        if q['type'] == 'single':
            selected = selected[:1]
        return selected
    def save_current(self):
        q = self.questions[self.current_index]
        sel = self.collect_selected()
        if q['type'] == 'truefalse':
            save_answer(self.attempt_uuid, q['id'], sel)
        elif q['type'] == 'single':
            save_answer(self.attempt_uuid, q['id'], sel)
        else:
            save_answer(self.attempt_uuid, q['id'], sel)
        self.answers[q['id']] = sel
        self.update_buttons_state()
    def on_option_clicked(self, button):
        q = self.questions[self.current_index]
        if button.isChecked() and q['type'] in ('single', 'truefalse'):
            for b in getattr(self, 'opt_buttons', []):
                if b is not button:
                    b.setChecked(False)
        sel = self.collect_selected()
        self.answers[q['id']] = sel
        self.update_buttons_state()
    def next_q(self):
        self.save_current()
        self.current_index += 1
        if self.current_index >= len(self.questions):
            self.current_index = len(self.questions) - 1
        self.render_q()
    def prev_q(self):
        self.save_current()
        self.current_index -= 1
        if self.current_index < 0:
            self.current_index = 0
        self.render_q()
    def submit(self):
        self.save_current()
        self.timer.stop()
        score, passed = submit_attempt(self.attempt_uuid)
        QMessageBox.information(self, '结果', f'得分:{score} {"通过" if passed==1 else "未通过"}')
        p = self.parent()
        if p is not None and hasattr(p, 'refresh_attempts'):
            p.refresh_attempts()
        self._submitted = True
        self.close()

    def closeEvent(self, event):
        if getattr(self, '_submitted', False):
            ExamWindow.instance = None
            event.accept()
            return
        reply = QMessageBox.question(self, '确认', '确定要退出考试吗？未作答的题目按0分，其他题目正常记分', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.save_current()
                self.timer.stop()
            except Exception:
                pass
            score, passed = submit_attempt(self.attempt_uuid)
            QMessageBox.information(self, '结果', f'已退出考试，得分:{score} {"通过" if passed==1 else "未通过"}（未作答按0分）')
            p = self.parent()
            if p is not None and hasattr(p, 'refresh_attempts'):
                p.refresh_attempts()
            self._submitted = True
            ExamWindow.instance = None
            event.accept()
        else:
            event.ignore()
