"""
状态指示器系统
提供加载动画、状态指示器和进度显示功能
"""

from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, Signal
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QFontMetrics
from PySide6.QtWidgets import (
    QWidget, QLabel, QProgressBar, QFrame, QVBoxLayout, QHBoxLayout,
    QPushButton, QApplication, QSizePolicy
)
from theme_manager import theme_manager
from icon_manager import icon_manager

class LoadingIndicator(QWidget):
    """加载动画指示器"""
    
    def __init__(self, parent=None, size=40):
        super().__init__(parent)
        self.size = size
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.fps = 20  # 20 FPS
        self.timer.start(1000 // self.fps)
        
        # 设置组件大小
        self.setFixedSize(size, size)
        
    def paintEvent(self, event):
        """绘制加载动画"""
        colors = theme_manager.get_theme_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 移动到中心点
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        # 绘制圆环
        pen = QPen(QColor(colors['primary']), 3, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # 绘制圆环
        radius = self.size // 2 - 6
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0, 270 * 16)  # 3/4圆环
        
        self.angle = (self.angle + 360 // self.fps) % 360
        
    def start(self):
        """开始动画"""
        self.timer.start(1000 // self.fps)
        self.show()
        
    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.hide()

class SpinnerIndicator(QWidget):
    """旋转指示器"""
    
    def __init__(self, parent=None, size=32, color=None):
        super().__init__(parent)
        self.size = size
        self.color = color or theme_manager.get_theme_colors()['primary']
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.fps = 30
        
        # 设置组件大小
        self.setFixedSize(size, size)
        
    def paintEvent(self, event):
        """绘制旋转指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 移动到中心点
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self.angle)
        
        # 绘制弧形
        pen = QPen(QColor(self.color), 3, Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        
        # 绘制弧形
        radius = self.size // 2 - 6
        painter.drawArc(-radius, -radius, radius * 2, radius * 2, 0, 120 * 16)
        
        self.angle = (self.angle + 360 // self.fps) % 360
        
    def start(self):
        """开始动画"""
        self.timer.start(1000 // self.fps)
        self.show()
        
    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.hide()

class PulseIndicator(QWidget):
    """脉冲指示器"""
    
    def __init__(self, parent=None, size=24, color=None):
        super().__init__(parent)
        self.size = size
        self.color = color or theme_manager.get_theme_colors()['success']
        self.scale = 1.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.fps = 15
        
        # 设置组件大小
        self.setFixedSize(size, size)
        
        # 动画
        self.animation = QPropertyAnimation(self, b"scale")
        self.animation.setDuration(1000)
        self.animation.setEasingCurve(QEasingCurve.InOutSine)
        self.animation.setLoopCount(-1)  # 无限循环
        self.animation.setKeyValueAt(0, 1.0)
        self.animation.setKeyValueAt(0.5, 1.5)
        self.animation.setKeyValueAt(1.0, 1.0)
        
    def paintEvent(self, event):
        """绘制脉冲效果"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 移动到中心点
        painter.translate(self.width() / 2, self.height() / 2)
        painter.scale(self.scale, self.scale)
        
        # 绘制圆点
        radius = self.size // 4
        painter.setBrush(QBrush(QColor(self.color)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(-radius, -radius, radius * 2, radius * 2)
        
    def start(self):
        """开始动画"""
        self.animation.start()
        self.timer.start(1000 // self.fps)
        self.show()
        
    def stop(self):
        """停止动画"""
        self.animation.stop()
        self.timer.stop()
        self.scale = 1.0
        self.hide()

class WaveIndicator(QWidget):
    """波浪效果指示器"""
    
    def __init__(self, parent=None, height=40):
        super().__init__(parent)
        self.height = height
        self.width = 120
        self.phase = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.fps = 30
        
        # 设置组件大小
        self.setFixedSize(self.width, height)
        
    def paintEvent(self, event):
        """绘制波浪效果"""
        colors = theme_manager.get_theme_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 绘制波浪线
        points = []
        for x in range(0, self.width, 2):
            y = self.height // 2 + int(8 * (1 + self.phase) * (x / self.width) * (1 - x / self.width))
            points.append((x, y))
            
        # 绘制波浪线
        pen = QPen(QColor(colors['primary']), 2, Qt.SolidLine)
        painter.setPen(pen)
        
        for i in range(len(points) - 1):
            painter.drawLine(points[i][0], points[i][1], points[i+1][0], points[i+1][1])
            
        self.phase += 0.1
        if self.phase > 2 * 3.14159:
            self.phase = 0
            
    def start(self):
        """开始动画"""
        self.timer.start(1000 // self.fps)
        self.show()
        
    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.hide()

class DotsIndicator(QWidget):
    """点状指示器"""
    
    def __init__(self, parent=None, dot_count=3):
        super().__init__(parent)
        self.dot_count = dot_count
        self.phase = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.update)
        self.fps = 20
        
        # 设置组件大小
        self.setFixedSize(60, 20)
        
    def paintEvent(self, event):
        """绘制点状效果"""
        colors = theme_manager.get_theme_colors()
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        dot_radius = 4
        spacing = 20
        
        for i in range(self.dot_count):
            # 计算透明度
            alpha = int(255 * (1 - (self.phase + i * 0.3) % 1.0))
            color = QColor(colors['primary'])
            color.setAlpha(alpha)
            
            # 绘制点
            x = 10 + i * spacing
            y = self.height() // 2
            
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(x - dot_radius, y - dot_radius, 
                            dot_radius * 2, dot_radius * 2)
            
        self.phase += 0.1
        if self.phase > 1.0:
            self.phase = 0.0
            
    def start(self):
        """开始动画"""
        self.timer.start(1000 // self.fps)
        self.show()
        
    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.hide()

class StatusIndicator(QWidget):
    """状态指示器组件"""
    
    # 信号定义
    clicked = Signal(str)  # 点击信号
    
    def __init__(self, status="info", text="", parent=None):
        super().__init__(parent)
        self.status = status
        self.text = text
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4,8,4)
        layout.setSpacing(6)
        
        # 状态图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(16, 16)
        
        # 状态文本
        self.text_label = QLabel(self.text)
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        
        self.setLayout(layout)
        
        # 设置点击事件
        self.setCursor(Qt.PointingHandCursor)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        # 获取状态样式
        style_config = self._get_status_config()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {style_config['background']};
                border: 1px solid {style_config['border']};
                border-radius: 6px;
                padding: 4px 8px;
                min-height: 24px;
            }}
            
            QWidget:hover {{
                background: {style_config['hover_background']};
            }}
            
            QLabel {{
                color: {style_config['text_color']};
                font-size: 12px;
                font-weight: 500;
            }}
        """)
        
    def _get_status_config(self):
        """获取状态配置"""
        colors = theme_manager.get_theme_colors()
        
        config_map = {
            'success': {
                'icon': '✅',
                'background': colors['success_light'],
                'border': colors['success'],
                'text_color': colors['success'],
                'hover_background': colors['success']
            },
            'error': {
                'icon': '❌',
                'background': colors['error_light'],
                'border': colors['error'],
                'text_color': colors['error'],
                'hover_background': colors['error']
            },
            'warning': {
                'icon': '⚠️',
                'background': colors['warning_light'],
                'border': colors['warning'],
                'text_color': colors['warning'],
                'hover_background': colors['warning']
            },
            'info': {
                'icon': 'ℹ️',
                'background': colors['info_light'],
                'border': colors['info'],
                'text_color': colors['info'],
                'hover_background': colors['info']
            },
            'loading': {
                'icon': '⏳',
                'background': colors['info_light'],
                'border': colors['info'],
                'text_color': colors['info'],
                'hover_background': colors['info']
            },
            'online': {
                'icon': '🟢',
                'background': colors['success_light'],
                'border': colors['success'],
                'text_color': colors['success'],
                'hover_background': colors['success']
            },
            'offline': {
                'icon': '🔴',
                'background': colors['error_light'],
                'border': colors['error'],
                'text_color': colors['error'],
                'hover_background': colors['error']
            }
        }
        
        return config_map.get(self.status, config_map['info'])
        
    def set_status(self, status, text=None):
        """设置状态"""
        self.status = status
        if text is not None:
            self.text = text
            
        config = self._get_status_config()
        self.icon_label.setText(config['icon'])
        self.text_label.setText(self.text)
        
        self.update_style()
        
    def mousePressEvent(self, event):
        """鼠标点击事件"""
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.status)
        super().mousePressEvent(event)

class StatusBar(QWidget):
    """状态栏组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.indicators = []
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # 状态文本
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        layout.addWidget(self.status_label)
        layout.addStretch()
        
        # 状态指示器
        self.indicators_layout = QHBoxLayout()
        self.indicators_layout.setContentsMargins(0, 0, 0, 0)
        self.indicators_layout.setSpacing(4)
        
        layout.addLayout(self.indicators_layout)
        
        self.setLayout(layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['background_secondary']};
                border-top: 1px solid {colors['border']};
                min-height: 28px;
            }}
            
            QLabel {{
                color: {colors['text_secondary']};
                font-size: 12px;
            }}
        """)
        
    def set_status(self, text):
        """设置状态文本"""
        self.status_label.setText(text)
        
    def add_indicator(self, status, text="", indicator_type="dots"):
        """添加状态指示器"""
        if indicator_type == "dots":
            indicator = DotsIndicator()
        elif indicator_type == "spinner":
            indicator = SpinnerIndicator()
        elif indicator_type == "pulse":
            indicator = PulseIndicator()
        elif indicator_type == "wave":
            indicator = WaveIndicator()
        else:
            indicator = DotsIndicator()
            
        # 设置指示器样式
        indicator.setStyleSheet(f"""
            QWidget {{
                background: transparent;
                border: none;
            }}
        """)
        
        self.indicators_layout.addWidget(indicator)
        self.indicators.append({
            'widget': indicator,
            'status': status,
            'text': text,
            'type': indicator_type
        })
        
        return indicator
        
    def remove_indicator(self, indicator):
        """移除指示器"""
        if indicator in self.indicators:
            self.indicators_layout.removeWidget(indicator)
            indicator.hide()
            indicator.deleteLater()
            
    def start_loading(self, text="加载中..."):
        """开始加载"""
        self.set_status(text)
        
        # 添加加载指示器
        indicator = self.add_indicator("loading", text, "dots")
        indicator.start()
        
        return indicator
        
    def stop_loading(self, indicator):
        """停止加载"""
        if indicator:
            indicator.stop()
            self.remove_indicator(indicator)
            self.set_status("就绪")

class ProgressIndicator(QWidget):
    """进度指示器组件"""
    
    def __init__(self, parent=None, show_percentage=True):
        super().__init__(parent)
        self.value = 0
        self.maximum = 100
        self.show_percentage = show_percentage
        self.setup_ui()
        self.update_style()
        
    def setup_ui(self):
        """设置UI"""
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(self.show_percentage)
        
        layout.addWidget(self.progress_bar)
        
        # 进度文本
        if self.show_percentage:
            self.progress_label = QLabel("0%")
            self.progress_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(self.progress_label)
            
        self.setLayout(layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {colors['border']};
                border-radius: 4px;
                background: {colors['progress_background']};
                text-align: center;
                font-size: 11px;
                font-weight: 500;
                color: {colors['text_secondary']};
                height: 16px;
            }}
            
            QProgressBar::chunk {{
                background: {colors['primary']};
                border-radius: 4px;
                margin: 1px;
            }}
        """)
        
    def set_value(self, value):
        """设置进度值"""
        self.value = value
        self.progress_bar.setValue(value)
        
        if self.show_percentage:
            percentage = int((value / self.maximum) * 100)
            self.progress_label.setText(f"{percentage}%")
            
    def set_maximum(self, maximum):
        """设置最大值"""
        self.maximum = maximum
        self.progress_bar.setMaximum(maximum)
        
    def set_text(self, text):
        """设置进度文本"""
        if hasattr(self, 'progress_label'):
            self.progress_label.setText(text)
            
    def start_indeterminate(self):
        """启动不确定进度"""
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_indeterminate)
        self.value = 0
        self.timer.start(50)  # 20 FPS
        
    def _update_indeterminate(self):
        """更新不确定进度"""
        self.value = (self.value + 2) % 100
        self.progress_bar.setValue(self.value)
        
    def stop_indeterminate(self):
        """停止不确定进度"""
        if hasattr(self, 'timer'):
            self.timer.stop()

class ToastNotification(QWidget):
    """吐司通知组件"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
        self.update_style()
        self.fade_animation = QPropertyAnimation(self, b"opacity")
        self.fade_animation.setDuration(3000)  # 3秒显示时间
        self.fade_animation.setEasingCurve(QEasingCurve.InOutSine)
        self.opacity = 1.0
        
    def setup_ui(self):
        """设置UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(8)
        
        # 图标
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        self.icon_label.setFixedSize(20, 20)
        
        # 文本
        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        
        # 关闭按钮
        self.close_button = QPushButton("×")
        self.close_button.setFixedSize(20, 20)
        self.close_button.clicked.connect(self.hide)
        
        layout.addWidget(self.icon_label)
        layout.addWidget(self.text_label)
        layout.addStretch()
        layout.addWidget(self.close_button)
        
        self.setLayout(layout)
        
    def update_style(self):
        """更新样式"""
        colors = theme_manager.get_theme_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background: {colors['card_background']};
                border: 1px solid {colors['border']};
                border-radius: 8px;
                padding: 8px 12px;
                margin: 4px;
                min-width: 200px;
                max-width: 400px;
            }}
            
            QLabel {{
                color: {colors['text_primary']};
                font-size: 13px;
            }}
            
            QPushButton {{
                background: transparent;
                border: none;
                color: {colors['text_secondary']};
                font-size: 16px;
                font-weight: 300;
                min-width: 20px;
                max-width: 20px;
            }}
            
            QPushButton:hover {{
                color: {colors['text_primary']};
            }}
        """)
        
    def show_notification(self, text, type="info", duration=3000):
        """显示通知"""
        # 设置通知样式
        style_config = self._get_notification_config(type)
        
        self.icon_label.setText(style_config['icon'])
        self.text_label.setText(text)
        
        # 设置位置
        parent = self.parent()
        if parent:
            parent_rect = parent.rect()
            self.move(parent_rect.right() - 220, parent_rect.bottom() - 50)
            
        # 显示动画
        self.show()
        self.fade_animation.start()
        
        # 定时隐藏
        QTimer.singleShot(duration, self.hide)
        
    def _get_notification_config(self, type):
        """获取通知配置"""
        config_map = {
            'success': {
                'icon': '✅',
                'background': theme_manager.get_theme_colors()['success_light']
            },
            'error': {
                'icon': '❌',
                'background': theme_manager.get_theme_colors()['error_light']
            },
            'warning': {
                'icon': '⚠️',
                'background': theme_manager.get_theme_colors()['warning_light']
            },
            'info': {
                'icon': 'ℹ️',
                'background': theme_manager.get_theme_colors()['info_light']
            }
        }
        
        return config_map.get(type, config_map['info'])

# 便捷函数
def create_loading_indicator(parent=None, size=40):
    """创建加载指示器的便捷函数"""
    indicator = LoadingIndicator(parent, size)
    return indicator
    
def create_status_indicator(status, text="", parent=None):
    """创建状态指示器的便捷函数"""
    indicator = StatusIndicator(status, text, parent)
    return indicator
    
def create_progress_indicator(parent=None, show_percentage=True):
    """创建进度指示器的便捷函数"""
    indicator = ProgressIndicator(parent, show_percentage)
    return indicator
    
def show_toast_notification(parent, text, type="info", duration=3000):
    """显示吐司通知的便捷函数"""
    toast = ToastNotification(parent)
    toast.show_notification(text, type, duration)
    return toast