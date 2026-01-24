from PySide6.QtGui import QIcon, QPalette
from PySide6.QtCore import Qt
import qtawesome as qta
import os


class IconManager:
    """图标管理器（支持深色/浅色主题自动切换）"""

    def __init__(self, theme=None):
        """
        theme: None 表示自动跟随系统/应用主题
               'light' 或 'dark' 表示强制主题
        """
        self._forced_theme = theme
        self.icons = {}
        self.icon_cache = {}
        self._create_icons()

    # ----------------- 主题相关 -----------------

    def _detect_theme(self):
        """检测当前主题：'light' 或 'dark'"""
        if self._forced_theme in ('light', 'dark'):
            return self._forced_theme

        palette = qta.QtWidgets.QApplication.instance().palette()
        bg = palette.color(QPalette.ColorRole.Window)
        # 根据背景亮度判断主题
        return 'dark' if bg.lightness() < 128 else 'light'

    def set_theme(self, theme):
        """手动设置主题（None / 'light' / 'dark'）"""
        self._forced_theme = theme
        self.icon_cache.clear()

    def _icon_color(self):
        """根据主题返回合适的图标颜色"""
        theme = self._detect_theme()
        return '#AAAAAA' if theme == 'dark' else '#555555'

    # ----------------- 图标定义 -----------------

    def _create_icons(self):
        self.icons.update({
            # 用户
            'user': 'fa6s.user',
            'user_admin': 'fa6s.user-tie',
            'user_student': 'fa6s.user-graduate',
            'user_add': 'fa6s.user-plus',
            'user_delete': 'fa6s.user-xmark',
            'user_edit': 'fa6s.user-pen',
            'user_active': 'fa6s.circle-check',
            'user_inactive': 'fa6s.circle-xmark',

            # 考试
            'exam': 'fa6s.book',
            'exam_add': 'fa6s.plus',
            'exam_delete': 'fa6s.trash',
            'exam_edit': 'fa6s.pen',
            'exam_import': 'fa6s.file-import',
            'exam_export': 'fa6s.file-export',
            'exam_start': 'fa6s.play',
            'exam_time': 'fa6s.clock',
            'exam_pass': 'fa6s.circle-check',
            'exam_fail': 'fa6s.circle-xmark',

            # 题目
            'question': 'fa6s.circle-question',
            'question_single': 'fa6s.circle-dot',
            'question_multiple': 'fa6s.square-check',
            'question_truefalse': 'fa6s.scale-balanced',
            'question_score': 'fa6s.star',

            # 成绩
            'score': 'fa6s.trophy',
            'score_pass': 'fa6s.check',
            'score_fail': 'fa6s.xmark',
            'score_sync': 'fa6s.arrows-rotate',
            'score_download': 'fa6s.download',
            'score_upload': 'fa6s.upload',

            # 系统
            'settings': 'fa6s.gear',
            'help': 'fa6s.circle-question',
            'info': 'fa6s.circle-info',
            'warning': 'fa6s.triangle-exclamation',
            'error': 'fa6s.circle-xmark',
            'success': 'fa6s.circle-check',
            'loading': 'fa6s.spinner',

            # 导航
            'home': 'fa6s.house',
            'back': 'fa6s.arrow-left',
            'forward': 'fa6s.arrow-right',
            'refresh': 'fa6s.rotate',
            'search': 'fa6s.magnifying-glass',
            'filter': 'fa6s.filter',

            # 文件
            'file': 'fa6s.file',
            'folder': 'fa6s.folder',
            'database': 'fa6s.database',
            'backup': 'fa6s.floppy-disk',

            # 动作
            'play': 'fa6s.play',
            'pause': 'fa6s.pause',
            'stop': 'fa6s.stop',
            'submit': 'fa6s.paper-plane',
            'save': 'fa6s.floppy-disk',
            'delete': 'fa6s.trash',
            'cancel': 'fa6s.xmark',
            'confirm': 'fa6s.check',
            'push': 'fa6s.upload',
            'sync': 'fa6s.arrows-rotate',
        })

    # ----------------- 对外接口 -----------------

    def get_icon(self, icon_name, size=16, color=None):
        """获取图标（自动适配主题颜色）"""
        icon_id = self.icons.get(icon_name)
        if not icon_id:
            print(f"图标 {icon_name} 不存在")
            return QIcon()

        theme = self._detect_theme()
        color = color or self._icon_color()
        cache_key = f'{icon_id}_{size}_{color}_{theme}'
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        icon = qta.icon(icon_id, color=color)
        self.icon_cache[cache_key] = icon
        return icon

    # -------- 状态 / 类型 / 动作 --------

    def get_status_indicator(self, status, size=16):
        status_map = {
            'online': 'fa6s.circle-check',
            'offline': 'fa6s.circle-xmark',
            'busy': 'fa6s.spinner',
            'new': 'fa6s.plus',
            'hot': 'fa6s.fire',
            'pass': 'fa6s.check',
            'fail': 'fa6s.xmark',
            'active': 'fa6s.circle-check',
            'inactive': 'fa6s.circle-xmark',
        }
        return qta.icon(status_map.get(status, 'fa6s.circle-question'), color=self._icon_color())

    def get_action_indicator(self, action):
        action_map = {
            'add': 'fa6s.plus',
            'delete': 'fa6s.trash',
            'edit': 'fa6s.pen',
            'import': 'fa6s.upload',
            'export': 'fa6s.download',
            'sync': 'fa6s.arrows-rotate',
            'submit': 'fa6s.paper-plane',
            'save': 'fa6s.floppy-disk',
            'refresh': 'fa6s.rotate',
        }
        return qta.icon(action_map.get(action, 'fa6s.circle-question'), color=self._icon_color())

    def get_type_indicator(self, item_type):
        type_map = {
            'admin': 'fa6s.user-tie',
            'user': 'fa6s.user',
            'exam': 'fa6s.book',
            'question': 'fa6s.circle-question',
            'score': 'fa6s.trophy',
            'device': 'fa6s.laptop',
            'sync': 'fa6s.arrows-rotate',
        }
        return qta.icon(type_map.get(item_type, 'fa6s.circle-question'), color=self._icon_color())

    def get_file_type_indicator(self, file_path):
        if not file_path:
            return qta.icon('fa6s.file', color=self._icon_color())

        ext = os.path.splitext(file_path)[1].lower()
        ext_map = {
            '.json': 'fa6s.file-code',
            '.yaml': 'fa6s.file-code',
            '.yml': 'fa6s.file-code',
            '.toml': 'fa6s.file-code',
            '.db': 'fa6s.database',
            '.backup': 'fa6s.floppy-disk',
        }
        return qta.icon(ext_map.get(ext, 'fa6s.file'), color=self._icon_color())