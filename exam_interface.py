"""
考试界面组件
提供现代化的计时器、进度显示和考试管理功能
"""

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Signal
from PySide6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QButtonGroup,
    QTextEdit, QGroupBox, QLineEdit
)
from theme_manager import theme_manager


def seconds_to_time(seconds):
    """将秒数转换为时间格式"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"


class ModernTimer(QLabel):
    """现代化计时器组件"""
    
    time_changed = Signal(str)  # 时间变化信号
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.time_remaining = 0  # 剩余时间（秒）
        self.total_time = 0  # 总时间（秒）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_timer)
        
        # 动画效果
        self.pulse_animation = QPropertyAnimation(self, b"pulse_scale")
        self.pulse_animation.setDuration(1000)
        self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
        self.pulse_scale = 1.0
        
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(60)
        self.setMaximumHeight(60)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QLabel {{
                background: {colors['card_background']};
                border: 2px solid {colors['border']};
                border-radius: 12px;
                color: {colors['text_primary']};
                font-size: 24px;
                font-weight: 700;
                font-family: 'Consolas', 'Monaco', monospace;
                padding: 12px;
                text-align: center;
            }}
        """)
        
    def start_timer(self, total_seconds):
        """开始计时器"""
        self.time_remaining = total_seconds
        self.total_time = total_seconds
        self.update_timer()
        self.timer.start(1000)  # 每秒更新
        
    def stop_timer(self):
        """停止计时器"""
        self.timer.stop()
        
    def update_timer(self):
        """更新计时器显示"""
        if self.time_remaining <= 0:
            self.timer.stop()
            self.time_remaining = 0
            self.update_display()
            self.time_changed.emit("00:00:00")
            return
            
        self.time_remaining -= 1
        self.update_display()
        
        # 发送时间变化信号
        time_str = seconds_to_time(self.time_remaining)
        self.time_changed.emit(time_str)
        
    def update_display(self):
        """更新显示"""
        time_str = seconds_to_time(self.time_remaining)
        self.setText(time_str)
        
        # 根据剩余时间设置颜色
        self._update_timer_color()
        
    def _update_timer_color(self):
        """根据剩余时间更新颜色"""
        colors = theme_manager.get_theme_colors()
        
        if self.time_remaining <= 60:  # 1分钟内
            # 红色警告
            self.setStyleSheet(f"""
                QLabel {{
                    background: {colors['error_light']};
                    border: 2px solid {colors['error']};
                    border-radius: 12px;
                    color: {colors['error']};
                    font-size: 24px;
                    font-weight: 700;
                    text-align: center;
                }}
            """)
            self._start_pulse_animation()
        elif self.time_remaining <= 300:  # 5分钟内
            # 橙色警告
            self.setStyleSheet(f"""
                QLabel {{
                    background: {colors['warning_light']};
                    border: 2px solid {colors['warning']};
                    border-radius: 12px;
                    color: {colors['warning']};
                    font-size: 24px;
                    font-weight: 700;
                    text-align: center;
                }}
            """)
        else:
            # 正常状态
            self.setStyleSheet(f"""
                QLabel {{
                    background: {colors['card_background']};
                    border: 2px solid {colors['border']};
                    border-radius: 12px;
                    color: {colors['text_primary']};
                    font-size: 24px;
                    font-weight: 700;
                    text-align: center;
                }}
            """)
            
    def _start_pulse_animation(self):
        """启动脉冲动画"""
        if not self.pulse_animation:
            self.pulse_animation = QPropertyAnimation(self, b"pulse_scale")
            self.pulse_animation.setDuration(1000)
            self.pulse_animation.setEasingCurve(QEasingCurve.Type.InOutSine)
            
        self.pulse_animation.start()

    def get_time_remaining(self):
        """获取剩余时间"""
        return self.time_remaining
        
    def set_time_remaining(self, seconds):
        """设置剩余时间"""
        self.time_remaining = seconds
        self.update_display()

class ModernProgressBar(QProgressBar):
    """现代化进度条组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        self.setMinimumHeight(20)
        self.setMaximumHeight(20)
        self.setTextVisible(True)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QProgressBar {{
                border: none;
                border-radius: 10px;
                background: {colors['progress_background']};
                text-align: center;
                font-size: 12px;
                font-weight: 600;
                color: {colors['text_primary']};
            }}
            
            QProgressBar::chunk {{
                background: {self._get_progress_color()};
                border-radius: 10px;
                margin: 1px;
            }}
        """)
        
    def _get_progress_color(self):
        """获取进度条颜色"""
        colors = theme_manager.get_theme_colors()
        value = self.value()
        maximum = self.maximum()
        
        if maximum > 0:
            percentage = value / maximum
            if percentage >= 0.8:
                return colors['success']
            elif percentage >= 0.5:
                return colors['warning']
            else:
                return colors['primary']
        return colors['primary']

class ExamInfoPanel(QWidget):
    """考试信息面板"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.progress_bar = None
        self.timer_label = None
        self.timer_frame = None
        self.pass_score_label = None
        self.questions_label = None
        self.duration_label = None
        self.title_label = None
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 考试标题
        self.title_label = QLabel("考试标题")
        self.title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 700;
                color: #303133;
                margin-bottom: 8px;
            }
        """)
        layout.addWidget(self.title_label)
        
        # 考试信息
        info_layout = QHBoxLayout()
        
        # 考试时长
        self.duration_label = QLabel()
        info_layout.addWidget(self.duration_label)
        
        # 题目数量
        self.questions_label = QLabel()
        info_layout.addWidget(self.questions_label)
        
        # 及格分数
        self.pass_score_label = QLabel()
        info_layout.addWidget(self.pass_score_label)
        
        layout.addLayout(info_layout)
        
        # 计时器
        self.timer_frame = QFrame()
        timer_layout = QVBoxLayout()
        
        self.timer_label = ModernTimer()
        timer_layout.addWidget(self.timer_label)
        
        self.timer_frame.setLayout(timer_layout)
        layout.addWidget(self.timer_frame)
        
        # 进度条
        self.progress_bar = ModernProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.setLayout(layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['card_background']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 16px;
            }}
            
            QLabel {{
                color: {colors['text_secondary']};
                font-size: 14px;
                margin: 4px 0;
            }}
            
            QPushButton#optionButton {{
                background: {colors['card_background']};
                border: 1px solid {colors['input_border']};
                border-radius: 12px;
                color: {colors['text_primary']};
                padding: 12px 16px;
                font-size: 16px;
                min-height: 44px;
                text-align: left;
            }}
            QPushButton#optionButton:hover {{
                background: {colors['border_light']};
            }}
            QPushButton#optionButton:checked {{
                background: {colors['primary']};
                color: {colors['text_inverse']};
                border-color: {colors['primary']};
            }}
        """)
        
    def set_exam_info(self, title, duration, total_questions, pass_score):
        """设置考试信息"""
        self.title_label.setText(title)
        self.duration_label.setText(f"考试时长: {duration} 分钟")
        self.questions_label.setText(f"题目数量: {total_questions} 题")
        self.pass_score_label.setText(f"及格分数: {pass_score} 分")
        
        # 设置进度条
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
    def update_progress(self, current_question, total_questions):
        """更新进度"""
        percentage = (current_question - 1) / total_questions * 100
        self.progress_bar.setValue(int(percentage))
        
    def start_timer(self, duration_seconds):
        """开始计时器"""
        self.timer_label.time_remaining = duration_seconds
        self.timer_label.total_time = duration_seconds
        self.timer_label.start_timer(duration_seconds)

class QuestionNavigation(QWidget):
    """题目导航组件"""
    
    question_selected = Signal(int)  # 题目选择信号
    
    def __init__(self, total_questions, parent=None):
        super().__init__(parent)
        self.question_buttons = None
        self.button_group = None
        self.total_questions = total_questions
        self.answered_questions = set()
        self.current_question = 1
        
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("题目导航")
        title_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                font-weight: 600;
                color: #303133;
                margin-bottom: 12px;
            }
        """)
        layout.addWidget(title_label)
        
        # 题目按钮组
        self.button_group = QButtonGroup()
        self.button_group.setExclusive(True)
        
        # 创建题目按钮
        self.question_buttons = []
        for i in range(1, self.total_questions + 1):
            button = QPushButton(f"{i}")
            button.setCheckable(True)
            button.setChecked(i == 1)  # 默认选中第一题
            button.clicked.connect(lambda checked, q=i: self.on_question_selected(q))
            
            self.button_group.addButton(button, i)
            self.question_buttons.append(button)
            layout.addWidget(button)
            
        layout.addStretch()
        self.setLayout(layout)
        
    def mark_question_answered(self, question_num):
        """标记题目为已答"""
        self.answered_questions.add(question_num)
        self.update_button_styles()
        
    def mark_question_unanswered(self, question_num):
        """标记题目为未答"""
        if question_num in self.answered_questions:
            self.answered_questions.remove(question_num)
        self.update_button_styles()
        
    def set_current_question(self, question_num):
        """设置当前题目"""
        self.current_question = question_num
        self.update_button_styles()
        
    def update_button_styles(self):
        """更新按钮样式"""
        colors = theme_manager.get_theme_colors()
        
        for i, button in enumerate(self.question_buttons, 1):
            button_style = f"""
                QPushButton {{
                    background: {colors['card_background']};
                    border: 2px solid {colors['border']};
                    border-radius: 6px;
                    color: {colors['text_primary']};
                    font-size: 14px;
                    font-weight: 600;
                    padding: 8px;
                    min-width: 40px;
                    min-height: 40px;
                }}
            """
            
            if i == self.current_question:
                # 当前题目
                button_style += f"""
                    QPushButton {{
                        background: {colors['primary']};
                        border-color: {colors['primary']};
                        color: {colors['text_inverse']};
                    }}
                """
            elif i in self.answered_questions:
                # 已答题目
                button_style += f"""
                    QPushButton {{
                        background: {colors['success_light']};
                        border-color: {colors['success']};
                        color: {colors['success']};
                    }}
                """
            else:
                # 未答题目
                button_style += f"""
                    QPushButton:hover {{
                        background: {colors['border_light']};
                    }}
                """
                
            button.setStyleSheet(button_style)
            
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['card_background']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 16px;
            }}
        """)
        
    def on_question_selected(self, question_num):
        """题目选择回调"""
        self.current_question = question_num
        self.update_button_styles()
        self.question_selected.emit(question_num)

class QuestionDisplay(QWidget):
    """题目显示组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.submit_button = None
        self.next_button = None
        self.prev_button = None
        self.options_layout = None
        self.content_text = None
        self.score_label = None
        self.question_type_label = None
        self.question_num_label = None
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        
        # 题目信息
        info_layout = QHBoxLayout()
        
        self.question_num_label = QLabel()
        self.question_type_label = QLabel()
        self.score_label = QLabel()
        
        info_layout.addWidget(self.question_num_label)
        info_layout.addWidget(self.question_type_label)
        info_layout.addStretch()
        info_layout.addWidget(self.score_label)
        
        layout.addLayout(info_layout)
        
        # 题目内容
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        layout.addWidget(self.content_text)
        
        # 答案选项
        self.options_layout = QVBoxLayout()
        layout.addLayout(self.options_layout)
        
        # 导航按钮
        nav_layout = QHBoxLayout()
        
        self.prev_button = QPushButton("上一题")
        self.next_button = QPushButton("下一题")
        self.submit_button = QPushButton("提交考试")
        
        nav_layout.addWidget(self.prev_button)
        nav_layout.addWidget(self.next_button)
        nav_layout.addStretch()
        nav_layout.addWidget(self.submit_button)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['card_background']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 16px;
                margin: 8px;
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 8px;
            }}
            
            QTextEdit {{
                background: {colors['input_background']};
                border: 1px solid {colors['input_border']};
                border-radius: 6px;
                padding: 12px;
                font-size: 14px;
                color: {colors['text_primary']};
                margin-bottom: 16px;
            }}
            
            QPushButton {{
                background: {colors['button_primary']};
                color: {colors['text_inverse']};
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                font-weight: 500;
                min-height: 20px;
            }}
            
            QPushButton:hover {{
                background: {colors['button_primary_hover']};
            }}
            
            QPushButton:disabled {{
                background: {colors['border_light']};
                color: {colors['text_tertiary']};
            }}
        """)
        
    def display_question(self, question_data):
        """显示题目"""
        # 更新题目信息
        self.question_num_label.setText(f"第 {question_data['number']} 题")
        self.question_type_label.setText(f"类型: {question_data['type']}")
        self.score_label.setText(f"分值: {question_data['score']}")
        
        # 显示题目内容
        self.content_text.setHtml(question_data['content'])
        
        # 清除之前的选项
        for i in reversed(range(self.options_layout.count())):
            child = self.options_layout.takeAt(i)
            if child.widget():
                child.widget().deleteLater()
                
        # 显示选项
        if question_data['type'] == 'single':
            self._display_single_choice(question_data)
        elif question_data['type'] == 'multiple':
            self._display_multiple_choice(question_data)
        elif question_data['type'] == 'truefalse':
            self._display_truefalse_choice(question_data)
        elif question_data['type'] == 'fill':
            self._display_fill_blank(question_data)
            
    def _display_single_choice(self, question_data):
        """显示单选题"""
        for option in question_data['options']:
            button = QPushButton(option['text'])
            button.setObjectName('optionButton')
            button.setCheckable(True)
            self.options_layout.addWidget(button)
            
    def _display_multiple_choice(self, question_data):
        """显示多选题"""
        for option in question_data['options']:
            button = QPushButton(option['text'])
            button.setObjectName('optionButton')
            button.setCheckable(True)
            self.options_layout.addWidget(button)
            
    def _display_truefalse_choice(self, question_data):
        """显示判断题"""
        true_button = QPushButton("正确")
        false_button = QPushButton("错误")
        true_button.setObjectName('optionButton')
        false_button.setObjectName('optionButton')
        
        true_button.setCheckable(True)
        false_button.setCheckable(True)
        
        # 创建按钮组
        button_group = QButtonGroup()
        button_group.addButton(true_button, 0)
        button_group.addButton(false_button, 1)
        
        self.options_layout.addWidget(true_button)
        self.options_layout.addWidget(false_button)
        return question_data
        
    def _display_fill_blank(self, question_data):
        """显示填空题"""
        input_field = QLineEdit()
        input_field.setPlaceholderText("请输入答案")
        self.options_layout.addWidget(input_field)
        return question_data

class ModernExamInterface(QWidget):
    """现代化考试界面"""
    
    # 信号定义
    question_changed = Signal(int)  # 题目切换信号
    time_up = Signal()  # 时间到信号
    exam_submitted = Signal()  # 考试提交信号
    
    def __init__(self, exam_data, parent=None):
        super().__init__(parent)
        self.auto_save_label = None
        self.remaining_label = None
        self.answered_label = None
        self.question_display = None
        self.info_panel = None
        self.navigation = None
        self.exam_data = exam_data
        self.current_question_index = 0
        self.answers = {}  # 答案存储
        
        self.setup_ui()
        self.update_style()
        self.load_question()
        
    def setup_ui(self):
        """设置UI"""
        main_layout = QHBoxLayout()
        
        # 左侧：题目导航
        self.navigation = QuestionNavigation(
            len(self.exam_data['questions'])
        )
        self.navigation.question_selected.connect(self.go_to_question)
        main_layout.addWidget(self.navigation)
        
        # 中间：题目显示区域
        center_layout = QVBoxLayout()
        
        # 考试信息面板
        self.info_panel = ExamInfoPanel()
        center_layout.addWidget(self.info_panel)
        
        # 题目显示
        self.question_display = QuestionDisplay()
        center_layout.addWidget(self.question_display)
        
        main_layout.addLayout(center_layout)
        
        # 右侧：考试信息
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        
        # 考试统计
        stats_group = QGroupBox("考试统计")
        stats_layout = QVBoxLayout()
        
        self.answered_label = QLabel("已答: 0")
        self.remaining_label = QLabel("剩余: 0")
        self.auto_save_label = QLabel("自动保存: 开启")
        
        stats_layout.addWidget(self.answered_label)
        stats_layout.addWidget(self.remaining_label)
        stats_layout.addWidget(self.auto_save_label)
        
        stats_group.setLayout(stats_layout)
        right_layout.addWidget(stats_group)
        
        # 快捷操作
        operations_group = QGroupBox("快捷操作")
        operations_layout = QVBoxLayout()
        
        save_button = QPushButton("保存答案")
        save_button.clicked.connect(self.save_current_answer)
        
        clear_button = QPushButton("清除当前答案")
        clear_button.clicked.connect(self.clear_current_answer)
        
        submit_button = QPushButton("提交考试")
        submit_button.setStyleSheet("""
            QPushButton {
                background: #F56C6C;
                color: white;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #F78989;
            }
        """)
        submit_button.clicked.connect(self.submit_exam)
        
        operations_layout.addWidget(save_button)
        operations_layout.addWidget(clear_button)
        operations_layout.addWidget(submit_button)
        
        operations_group.setLayout(operations_layout)
        right_layout.addWidget(operations_group)
        
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['background']};
            }}
        """)
        
    def load_question(self):
        """加载题目"""
        if self.current_question_index < len(self.exam_data['questions']):
            question = self.exam_data['questions'][self.current_question_index]
            self.question_display.display_question(question)
            
            # 更新导航状态
            self.navigation.set_current_question(
                self.current_question_index + 1
            )
            
            # 更新进度
            self.info_panel.update_progress(
                self.current_question_index + 1,
                len(self.exam_data['questions'])
            )
            
    def go_to_question(self, question_index):
        """跳转到指定题目"""
        if 0 <= question_index < len(self.exam_data['questions']):
            self.current_question_index = question_index
            self.load_question()
            
    def save_current_answer(self):
        """保存当前答案"""
        # 实现答案保存逻辑
        pass
        
    def clear_current_answer(self):
        """清除当前答案"""
        # 实现清除逻辑
        pass
        
    def submit_exam(self):
        """提交考试"""
        # 实现考试提交逻辑
        self.exam_submitted.emit()
        
    def get_exam_data(self):
        """获取考试数据"""
        return self.exam_data
        
    def get_current_answers(self):
        """获取当前答案"""
        return self.answers