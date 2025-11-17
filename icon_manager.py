"""
图标管理器
为考试系统提供统一的图标和视觉指示器
"""

from PySide6.QtGui import QIcon, QPixmap, QPainter, QColor, QFont
from PySide6.QtCore import QSize, Qt
from PySide6.QtWidgets import QApplication
import os

class IconManager:
    """图标管理器"""
    
    def __init__(self):
        self.icons = {}
        self.icon_cache = {}
        self._create_icons()
        
    def _create_icons(self):
        """创建所有图标"""
        # 用户相关图标
        self.icons['user'] = "👤"
        self.icons['user_admin'] = "👨‍💼"
        self.icons['user_student'] = "👨‍🎓"
        self.icons['user_add'] = "➕"
        self.icons['user_delete'] = "🗑️"
        self.icons['user_edit'] = "✏️"
        self.icons['user_active'] = "🟢"
        self.icons['user_inactive'] = "🔴"
        
        # 考试相关图标
        self.icons['exam'] = "📝"
        self.icons['exam_add'] = "➕"
        self.icons['exam_delete'] = "🗑️"
        self.icons['exam_edit'] = "✏️"
        self.icons['exam_import'] = "📥"
        self.icons['exam_export'] = "📤"
        self.icons['exam_start'] = "🚀"
        self.icons['exam_time'] = "⏰"
        self.icons['exam_pass'] = "✅"
        self.icons['exam_fail'] = "❌"
        
        # 题目相关图标
        self.icons['question'] = "❓"
        self.icons['question_single'] = "🔘"
        self.icons['question_multiple'] = "☑️"
        self.icons['question_truefalse'] = "⚖️"
        self.icons['question_score'] = "🎯"
        
        # 成绩相关图标
        self.icons['score'] = "🏆"
        self.icons['score_pass'] = "🎉"
        self.icons['score_fail'] = "😔"
        self.icons['score_sync'] = "🔄"
        self.icons['score_download'] = "📥"
        self.icons['score_upload'] = "📤"
        
        # 同步相关图标
        self.icons['sync'] = "🔄"
        self.icons['sync_push'] = "📤"
        self.icons['sync_pull'] = "📥"
        self.icons['device'] = "💻"
        self.icons['network'] = "🌐"
        self.icons['connection'] = "🔗"
        
        # 系统相关图标
        self.icons['settings'] = "⚙️"
        self.icons['help'] = "❓"
        self.icons['info'] = "ℹ️"
        self.icons['warning'] = "⚠️"
        self.icons['error'] = "❌"
        self.icons['success'] = "✅"
        self.icons['loading'] = "⏳"
        
        # 导航相关图标
        self.icons['home'] = "🏠"
        self.icons['back'] = "⬅️"
        self.icons['forward'] = "➡️"
        self.icons['refresh'] = "🔄"
        self.icons['search'] = "🔍"
        self.icons['filter'] = "🔽"
        
        # 文件相关图标
        self.icons['file'] = "📄"
        self.icons['folder'] = "📁"
        self.icons['database'] = "🗄️"
        self.icons['backup'] = "💾"
        
        # 状态指示器
        self.icons['online'] = "🟢"
        self.icons['offline'] = "🔴"
        self.icons['busy'] = "🟡"
        self.icons['new'] = "🆕"
        self.icons['hot'] = "🔥"
        self.icons['star'] = "⭐"
        
        # 动作图标
        self.icons['play'] = "▶️"
        self.icons['pause'] = "⏸️"
        self.icons['stop'] = "⏹️"
        self.icons['submit'] = "📤"
        self.icons['save'] = "💾"
        self.icons['cancel'] = "❌"
        self.icons['confirm'] = "✅"
        
    def get_icon(self, icon_name, size=16):
        """获取图标"""
        if icon_name not in self.icons:
            return QIcon()
            
        # 检查缓存
        cache_key = f"{icon_name}_{size}"
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]
            
        # 创建新图标
        icon_text = self.icons[icon_name]
        icon = self._create_text_icon(icon_text, size)
        
        # 缓存图标
        self.icon_cache[cache_key] = icon
        
        return icon
        
    def _create_text_icon(self, text, size):
        """创建文字图标"""
        # 创建透明背景的图标
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 设置字体
        font = QFont()
        font.setPointSize(size * 0.8)
        painter.setFont(font)
        
        # 绘制文字
        painter.drawText(0, 0, size, size, Qt.AlignCenter, text)
        painter.end()
        
        return QIcon(pixmap)
        
    def get_status_indicator(self, status, size=12):
        """获取状态指示器"""
        status_map = {
            'online': '🟢',
            'offline': '🔴', 
            'busy': '🟡',
            'new': '🆕',
            'hot': '🔥',
            'star': '⭐',
            'pass': '✅',
            'fail': '❌',
            'active': '🟢',
            'inactive': '🔴'
        }
        
        indicator_text = status_map.get(status, '⚪')
        return self.get_icon_text(indicator_text, size)
        
    def get_icon_text(self, icon_name, size=16):
        """获取图标文字"""
        return self.icons.get(icon_name, '⚪')
        
    def get_priority_indicator(self, priority):
        """获取优先级指示器"""
        priority_map = {
            'high': '🔴',
            'medium': '🟡', 
            'low': '🟢',
            'urgent': '🚨'
        }
        
        return priority_map.get(priority, '⚪')
        
    def get_type_indicator(self, item_type):
        """获取类型指示器"""
        type_map = {
            'admin': '👨‍💼',
            'user': '👤',
            'exam': '📝',
            'question': '❓',
            'score': '🏆',
            'device': '💻',
            'sync': '🔄'
        }
        
        return type_map.get(item_type, '⚪')
        
    def get_action_indicator(self, action):
        """获取动作指示器"""
        action_map = {
            'add': '➕',
            'delete': '🗑️',
            'edit': '✏️',
            'import': '📥',
            'export': '📤',
            'sync': '🔄',
            'push': '📤',
            'pull': '📥',
            'submit': '📤',
            'save': '💾',
            'refresh': '🔄'
        }
        
        return action_map.get(action, '⚪')
        
    def get_score_color_indicator(self, score, pass_threshold=0.6):
        """获取成绩颜色指示器"""
        if score >= pass_threshold:
            return '🟢'  # 绿色表示通过
        elif score >= pass_threshold * 0.8:
            return '🟡'  # 黄色表示接近通过
        else:
            return '🔴'  # 红色表示未通过
            
    def get_time_indicator(self, time_remaining):
        """获取时间指示器"""
        if time_remaining > 300:  # 5分钟以上
            return '🟢'  # 绿色
        elif time_remaining > 60:  # 1分钟以上
            return '🟡'  # 黄色
        else:
            return '🔴'  # 红色
            
    def get_sync_status_indicator(self, status):
        """获取同步状态指示器"""
        status_map = {
            'success': '✅',
            'error': '❌', 
            'progress': '⏳',
            'waiting': '⏸️'
        }
        
        return status_map.get(status, '⚪')
        
    def get_connection_status_indicator(self, is_connected):
        """获取连接状态指示器"""
        if is_connected:
            return '🟢'
        else:
            return '🔴'
            
    def get_file_type_indicator(self, file_path):
        """获取文件类型指示器"""
        if not file_path:
            return '📄'
            
        ext = os.path.splitext(file_path)[1].lower()
        
        type_map = {
            '.json': '📋',
            '.yaml': '📝',
            '.yml': '📝', 
            '.toml': '📄',
            '.db': '🗄️',
            '.backup': '💾'
        }
        
        return type_map.get(ext, '📄')
        
    def get_notification_indicator(self, notification_type):
        """获取通知类型指示器"""
        type_map = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'hot': '🔥',
            'new': '🆕'
        }
        
        return type_map.get(notification_type, '📢')

# 全局图标管理器实例
icon_manager = IconManager()

# 便捷函数
def get_icon(icon_name, size=16):
    """获取图标的便捷函数"""
    return icon_manager.get_icon(icon_name, size)
    
def get_icon_text(icon_name):
    """获取图标文字的便捷函数"""
    return icon_manager.get_icon_text(icon_name)
    
def get_status_indicator(status, size=12):
    """获取状态指示器的便捷函数"""
    return icon_manager.get_status_indicator(status, size)
    
def get_action_indicator(action):
    """获取动作指示器的便捷函数"""
    return icon_manager.get_action_indicator(action)
    
def get_type_indicator(item_type):
    """获取类型指示器的便捷函数"""
    return icon_manager.get_type_indicator(item_type)