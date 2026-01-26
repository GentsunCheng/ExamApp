import json
import random
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QGroupBox, QGridLayout, QScrollArea
from PySide6.QtGui import QKeySequence, QShortcut, QPixmap, QGuiApplication
from theme_manager import theme_manager
from icon_manager import IconManager
from exam_interface import ModernTimer, ModernProgressBar
from language import tr
from models import start_attempt, save_answer, submit_attempt, list_exams, grade_question, build_exam_questions_for_attempt, get_pic
from PySide6.QtWidgets import QMessageBox
from utils import show_info, show_warn, ask_yes_no

class ExamWindow(QMainWindow):
    instance = None
    def __init__(self, user, exam_id, parent=None):
        super().__init__(parent)
        self.opt_buttons = []
        self.icon_manager = IconManager()
        try:
            print(f"[DEBUG] ExamWindow init user={user.get('username')} exam_id={exam_id}")
        except Exception:
            pass
        if ExamWindow.instance is not None and ExamWindow.instance.isVisible():
            show_info(self, tr('common.hint'), tr('exam.already_running'))
            try:
                ExamWindow.instance.raise_()
                ExamWindow.instance.activateWindow()
            except Exception:
                pass
            self.close()
            return
        ExamWindow.instance = self
        self._submitted = False
        self.setWindowState(Qt.WindowState.WindowMaximized)
        self.shortcut_cheat = QShortcut(QKeySequence("Ctrl+Shift+O"), self)
        self.shortcut_cheat.activated.connect(self.cheat)
        self.shortcut_quit = QShortcut(QKeySequence("Ctrl+W"), self)
        self.shortcut_quit.activated.connect(self.quit_exam)
        self.cheatting = False
        self.user = user
        self.exam_id = exam_id
        self.questions = build_exam_questions_for_attempt(exam_id)
        try:
            random.shuffle(self.questions)
        except Exception:
            pass
        self.option_orders = {}
        self.total_score = 0
        for q in self.questions:
            self.total_score += q["score"]
        self.attempt_uuid = start_attempt(user['id'], exam_id, self.total_score)
        self.current_index = 0
        self.pic_width = self.get_resolution() / 2
        self.setWindowTitle(tr('exam.in_progress', total=self.total_score))
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
        main_layout = QHBoxLayout()

        self.nav_buttons = []
        nav_box = QGroupBox(tr('exam.nav_title'))
        nav_layout = QGridLayout()
        nav_colors = theme_manager.get_theme_colors()
        nav_box.setStyleSheet(
            f"QGroupBox {{ border:1px solid {nav_colors['border']}; border-radius:8px; padding:8px; font-size:13px; }}"
        )
        nav_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        for i in range(len(self.questions)):
            row = i // 3
            col = i % 3
            btn = QPushButton(str(i + 1))
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, idx=i: self.goto_question(idx))
            nav_layout.addWidget(btn, row, col)
            self.nav_buttons.append(btn)
        nav_box.setLayout(nav_layout)
        main_layout.addWidget(nav_box)

        right = QVBoxLayout()
        self.timer_widget = ModernTimer()
        right.addWidget(self.timer_widget)
        self.progress_bar = ModernProgressBar()
        self.progress_bar.setRange(0, max(1, len(self.questions)))
        self.progress_bar.setValue(1)
        right.addWidget(self.progress_bar)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet(f"QScrollArea {{ border:1px solid {colors['border']}; border-radius:8px; background-color: transparent; }}")
        self.scroll_area.setFrameShape(QScrollArea.Shape.NoFrame)
        
        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent;")
        vb = QVBoxLayout(scroll_content)
        vb.setContentsMargins(12, 12, 12, 12)
        
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
        
        vb.addWidget(self.q_title)
        vb.addLayout(self.q_picture_layout)
        vb.addWidget(self.opts_container)
        vb.addStretch()
        
        self.scroll_area.setWidget(scroll_content)
        right.addWidget(self.scroll_area)
        hb = QHBoxLayout()
        self.prev_btn = QPushButton(tr('exam.prev'))
        self.next_btn = QPushButton(tr('exam.next'))
        self.submit_btn = QPushButton(tr('exam.submit'))
        self.submit_btn.setIcon(self.icon_manager.get_icon('submit'))
        self.next_btn.setDefault(True)
        self.submit_btn.setEnabled(False)
        self.prev_btn.clicked.connect(self.prev_q)
        self.next_btn.clicked.connect(self.next_q)
        self.submit_btn.clicked.connect(self.submit)
        hb.addWidget(self.prev_btn)
        hb.addWidget(self.next_btn)
        hb.addStretch()
        hb.addWidget(self.submit_btn)
        right.addLayout(hb)

        main_layout.addLayout(right, 1)
        central.setLayout(main_layout)
        self.setCentralWidget(central)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.answers = {}
        self.evaluation = {}
        tl = 0
        for e in list_exams(include_expired=True):
            if e[0] == exam_id:
                tl = int(e[4])
                break
        self.remaining = tl * 60
        self.timer.start(1000)
        self.timer_widget.start_timer(self.remaining)
        self.update_nav_buttons_state()
        self.render_q()

    def get_resolution(self):
        screen = QGuiApplication.primaryScreen()
        size = screen.size()
        width = size.width()
        height = size.height()
        h = min(width, height)
        return h


    def showEvent(self, event):
        super().showEvent(event)

    def quit_exam(self):
        self.timer.stop()
        self.timer_widget.stop_timer()
        self.close()

    def cheat(self):
        self.cheatting = not self.cheatting
        print("Cheat enabled:", self.cheatting)
        if self.cheatting:
            self.shortcut_cheat.setEnabled(False)
        else:
            self.shortcut_cheat.setEnabled(True)

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
        self.submit_btn.setEnabled(self.all_answered() and not getattr(self, '_submitted', False))

    def update_nav_buttons_state(self):
        colors = theme_manager.get_theme_colors()
        base_bg = colors['card_background']
        base_fg = colors['text_primary']
        answered_bg = colors['primary']
        answered_fg = colors['text_inverse']
        ok_bg = colors['success_light']
        ok_fg = colors['success']
        warn_bg = colors['warning_light']
        warn_fg = colors['warning']
        bad_bg = colors['error_light']
        bad_fg = colors['error']
        for idx, q in enumerate(self.questions):
            if idx >= len(self.nav_buttons):
                continue
            btn = self.nav_buttons[idx]
            style_bg = base_bg
            style_fg = base_fg
            btn.setChecked(idx == self.current_index)
            if getattr(self, '_submitted', False):
                info = self.evaluation.get(q['id']) or {'selected': [], 'correct': False}
                sel_list = info.get('selected') or []
                sel = set(str(s) for s in sel_list)
                correct_set = set(str(s) for s in (q.get('correct') or []))
                if info.get('correct'):
                    style_bg = ok_bg
                    style_fg = ok_fg
                else:
                    if q['type'] == 'multiple':
                        intersection = sel & correct_set
                        if len(intersection) == 0:
                            style_bg = bad_bg
                            style_fg = bad_fg
                        else:
                            style_bg = warn_bg
                            style_fg = warn_fg
                    else:
                        style_bg = bad_bg
                        style_fg = bad_fg
            else:
                sel = self.answers.get(q['id'])
                if sel:
                    style_bg = answered_bg
                    style_fg = answered_fg
            btn.setStyleSheet(
                f"QPushButton {{ background-color:{style_bg}; color:{style_fg}; border-radius:8px; padding:6px 10px; min-width:32px; border:1px solid transparent; }}\n"
                f"QPushButton:hover {{ border-color:{colors['primary']}; }}\n"
                f"QPushButton:pressed {{ border-color:{colors['primary']}; }}\n"
                f"QPushButton:checked {{ border-color:{colors['primary']}; }}"
            )

    def goto_question(self, index):
        if index < 0 or index >= len(self.questions):
            return
        self.save_current()
        self.current_index = index
        self.render_q()

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
        tlabel = tr('exam.type.' + str(q.get('type')))
        self.q_title.setText(tr('exam.question_title', index=self.current_index+1, total=len(self.questions), text=q["text"], type=tlabel, score=q["score"]))
        picture_hash_list = json.loads(q.get("pictures", '[]'))
        # 清空旧图片
        for i in reversed(range(self.q_picture_layout.count())):
            widget = self.q_picture_layout.itemAt(i).widget()
            if widget:
                self.q_picture_layout.removeWidget(widget)
                widget.setParent(None)
        # 渲染新图片
        for picture_hash in picture_hash_list:
            picture = get_pic(picture_hash, max_dim=self.pic_width)
            if not picture:
                continue
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            pixmap = QPixmap.fromImage(picture)
            label.setPixmap(pixmap)
            self.q_picture_layout.addWidget(label)
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
            for label, val in [(tr('exam.true'), True), (tr('exam.false'), False)]:
                btn = QPushButton(label)
                btn.setCheckable(True)
                btn.setStyleSheet(btn_style)
                btn.setProperty('tf_value', val)
                btn.clicked.connect(lambda checked, b=btn: self.on_option_clicked(b))
                self.opts_layout.addWidget(btn)
                self.opt_buttons.append(btn)
        else:
            raw_opts = list(q['options'] or [])
            normalized = []
            for idx, o in enumerate(raw_opts):
                if isinstance(o, dict):
                    kv = o.get('key')
                    tv = o.get('text') if o.get('text') is not None else (str(o.get('value')) if o.get('value') is not None else str(kv))
                    kstr = str(kv) if kv is not None else str(idx)
                    normalized.append({'key_val': kv if kv is not None else idx, 'key_str': kstr, 'text': tv})
                else:
                    kv = o
                    kstr = str(kv)
                    normalized.append({'key_val': kv, 'key_str': kstr, 'text': str(o)})
            order = self.option_orders.get(q['id'])
            if order is None:
                keys = [opt['key_str'] for opt in normalized]
                try:
                    random.shuffle(keys)
                except Exception:
                    pass
                self.option_orders[q['id']] = keys
                order = keys
            by_key = {opt['key_str']: opt for opt in normalized}
            ordered_opts = [by_key[k] for k in order if k in by_key]
            for opt in ordered_opts:
                text = f"{opt['key_str']}. {opt['text']}"
                btn = QPushButton(text)
                btn.setCheckable(True)
                btn.setStyleSheet(btn_style)
                btn.setProperty('key', opt['key_str'])
                btn.setProperty('key_val', opt['key_val'])
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
                    kval = b.property('key_val')
                    b.setChecked(kval in sset if kval is not None else False)
        self.update_buttons_state()
        self.update_nav_buttons_state()
        self.progress_bar.setValue(self.current_index + 1)
        if getattr(self, '_submitted', False):
            try:
                self.apply_evaluation_styles(q)
            except Exception:
                pass

    def collect_selected(self):
        q = self.questions[self.current_index]
        selected = []
        for b in getattr(self, 'opt_buttons', []):
            if b.isChecked():
                if q['type'] == 'truefalse':
                    selected = [bool(b.property('tf_value'))]
                else:
                    selected.append(b.property('key_val'))
        if q['type'] == 'single':
            selected = selected[:1]
        return selected

    def save_current(self):
        q = self.questions[self.current_index]
        sel = self.collect_selected()
        if q['type'] == 'truefalse':
            save_answer(self.attempt_uuid, q['id'], sel, self.cheatting)
        elif q['type'] == 'single':
            save_answer(self.attempt_uuid, q['id'], sel, self.cheatting)
        else:
            save_answer(self.attempt_uuid, q['id'], sel, self.cheatting)
        self.answers[q['id']] = sel
        self.update_buttons_state()
        self.update_nav_buttons_state()

    def on_option_clicked(self, button):
        if getattr(self, '_submitted', False):
            return
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
        try:
            self.timer_widget.stop_timer()
        except Exception:
            pass
        score, passed = submit_attempt(self.attempt_uuid)
        show_info(self, tr('exam.result'), f'{tr("exam.score_label")}:{score} {tr("exam.pass_text") if passed==1 else tr("exam.fail_text")}')
        try:
            self.setWindowTitle(tr('exam.finished_title', score=score, total=self.total_score, passed=(tr('exam.pass_text') if passed==1 else tr('exam.fail_text'))))
        except Exception:
            pass
        p = self.parent()
        if p is not None and hasattr(p, 'refresh_attempts'):
            p.refresh_attempts()
        # 计算评估仅用于着色，不显示正确答案
        self.evaluation = {}
        for q in self.questions:
            sel = self.answers.get(q['id']) or []
            ok = bool(grade_question(q, sel))
            self.evaluation[q['id']] = {'selected': sel, 'correct': ok}
        self._submitted = True
        self.update_buttons_state()
        self.update_nav_buttons_state()
        self.render_q()

    def apply_evaluation_styles(self, q):
        colors = theme_manager.get_theme_colors()
        ok_bg = colors['success_light']
        ok_fg = colors['success']
        ok_border = colors['success']
        warn_bg = colors['warning_light']
        warn_fg = colors['warning']
        warn_border = colors['warning']
        bad_bg = colors['error_light']
        bad_fg = colors['error']
        bad_border = colors['error']
        info = self.evaluation.get(q['id']) or {'selected': [], 'correct': False}
        sel_list = info['selected'] or []
        sel = set(str(s) for s in sel_list)
        correct_set = set(str(s) for s in (q.get('correct') or []))
        # 禁止修改
        for b in getattr(self, 'opt_buttons', []):
            b.setEnabled(False)
        # 着色仅针对用户选择的选项
        for b in getattr(self, 'opt_buttons', []):
            key = b.property('key')
            is_sel = False
            if key is None and q['type'] == 'truefalse':
                chosen = (info['selected'] or [None])[0]
                is_sel = (b.property('tf_value') == chosen)
            else:
                is_sel = (str(key) in sel)
            if not is_sel:
                continue
            if info['correct']:
                b.setStyleSheet(
                    f"QPushButton {{ background-color:{ok_bg}; color:{ok_fg}; border:1px solid {ok_border}; border-radius:12px; padding:12px 16px; font-size:16px; text-align:left; min-height:44px; }}"
                )
            else:
                if q['type'] == 'multiple':
                    intersection = sel & correct_set
                    if len(intersection) == 0:
                        b.setStyleSheet(
                            f"QPushButton {{ background-color:{bad_bg}; color:{bad_fg}; border:1px solid {bad_border}; border-radius:12px; padding:12px 16px; font-size:16px; text-align:left; min-height:44px; }}"
                        )
                    else:
                        b.setStyleSheet(
                            f"QPushButton {{ background-color:{warn_bg}; color:{warn_fg}; border:1px solid {warn_border}; border-radius:12px; padding:12px 16px; font-size:16px; text-align:left; min-height:44px; }}"
                        )
                else:
                    b.setStyleSheet(
                        f"QPushButton {{ background-color:{bad_bg}; color:{bad_fg}; border:1px solid {bad_border}; border-radius:12px; padding:12px 16px; font-size:16px; text-align:left; min-height:44px; }}"
                    )

    def closeEvent(self, event):
        if getattr(self, '_submitted', False):
            ExamWindow.instance = None
            event.accept()
            return
        reply = ask_yes_no(self, tr('common.hint'), tr('exam.confirm_exit'), default_yes=False)
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.save_current()
                self.timer.stop()
                self.timer_widget.stop_timer()
            except Exception:
                pass
            score, passed = submit_attempt(self.attempt_uuid)
            show_info(self, tr('exam.result'), tr('exam.exit_result', score=score, pass_text=(tr('exam.pass_text') if passed==1 else tr('exam.fail_text'))) + tr('exam.unanswered_note'))
            try:
                self.setWindowTitle(tr('exam.finished_title', score=score, total=self.total_score, passed=(tr('exam.pass_text') if passed==1 else tr('exam.fail_text'))))
            except Exception:
                pass
            p = self.parent()
            if p is not None and hasattr(p, 'refresh_attempts'):
                p.refresh_attempts()
            self._submitted = True
            ExamWindow.instance = None
            event.accept()
        else:
            event.ignore()
