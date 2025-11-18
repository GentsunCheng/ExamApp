import random
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem, QGroupBox
from theme_manager import theme_manager
from icon_manager import get_icon
from exam_interface import ModernTimer, ModernProgressBar
from models import list_questions, start_attempt, save_answer, submit_attempt, list_exams
from PySide6.QtWidgets import QMessageBox

class ExamWindow(QMainWindow):
    def __init__(self, user, exam_id, parent=None):
        super().__init__(parent)
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
        self.q_opts = QListWidget()
        self.q_opts.itemChanged.connect(self.on_option_changed)
        vb.addWidget(self.q_title)
        vb.addWidget(self.q_opts)
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
        self.q_opts.blockSignals(True)
        self.q_opts.clear()
        if q['type'] == 'truefalse':
            for opt in ['True', 'False']:
                item = QListWidgetItem(opt)
                item.setCheckState(Qt.Unchecked)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.q_opts.addItem(item)
        else:
            for opt in q['options']:
                item = QListWidgetItem(f'{opt.get("key")}. {opt.get("text")}')
                item.setCheckState(Qt.Unchecked)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.q_opts.addItem(item)
        sel = self.answers.get(q['id'])
        if sel:
            if q['type'] == 'truefalse' and len(sel) == 1:
                for i in range(self.q_opts.count()):
                    it = self.q_opts.item(i)
                    if it.text() == 'True':
                        it.setCheckState(Qt.Checked if sel[0] is True else Qt.Unchecked)
                    elif it.text() == 'False':
                        it.setCheckState(Qt.Checked if sel[0] is False else Qt.Unchecked)
            else:
                sset = set(sel)
                for i in range(self.q_opts.count()):
                    it = self.q_opts.item(i)
                    key = it.text().split('.', 1)[0]
                    it.setCheckState(Qt.Checked if key in sset else Qt.Unchecked)
        self.q_opts.blockSignals(False)
        self.update_buttons_state()
        self.progress_bar.setValue(self.current_index + 1)
    def collect_selected(self):
        q = self.questions[self.current_index]
        selected = []
        for i in range(self.q_opts.count()):
            it = self.q_opts.item(i)
            if it.checkState() == Qt.Checked:
                txt = it.text()
                if q['type'] == 'truefalse':
                    selected = [txt == 'True']
                else:
                    key = txt.split('.', 1)[0]
                    selected.append(key)
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
    def on_option_changed(self, item):
        q = self.questions[self.current_index]
        if item.checkState() == Qt.Checked and q['type'] in ('single', 'truefalse'):
            self.q_opts.blockSignals(True)
            for i in range(self.q_opts.count()):
                it = self.q_opts.item(i)
                if it is not item:
                    it.setCheckState(Qt.Unchecked)
            self.q_opts.blockSignals(False)
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
        self.close()
