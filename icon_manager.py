from PySide6.QtGui import QIcon
import qtawesome as qta
import os


class IconManager:
    """图标管理器（QtAwesome 版本）"""

    def __init__(self):
        self.icons = {}
        self.icon_cache = {}
        self._create_icons()

    def _create_icons(self):
        """定义图标名称映射（不立即生成 QIcon）"""

        # 用户相关
        self.icons.update({
            'user': 'fa6s.user',
            'user_admin': 'fa6s.user-tie',
            'user_student': 'fa6s.user-graduate',
            'user_add': 'fa6s.user-plus',
            'user_delete': 'fa6s.user-xmark',
            'user_edit': 'fa6s.user-pen',
            'user_active': 'fa6s.circle-check',
            'user_inactive': 'fa6s.circle-xmark',
        })

        # 考试相关
        self.icons.update({
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
        })

        # 题目
        self.icons.update({
            'question': 'fa6s.circle-question',
            'question_single': 'fa6s.circle-dot',
            'question_multiple': 'fa6s.square-check',
            'question_truefalse': 'fa6s.scale-balanced',
            'question_score': 'fa6s.star',
        })

        # 成绩
        self.icons.update({
            'score': 'fa6s.trophy',
            'score_pass': 'fa6s.check',
            'score_fail': 'fa6s.xmark',
            'score_sync': 'fa6s.arrows-rotate',
            'score_download': 'fa6s.download',
            'score_upload': 'fa6s.upload',
        })

        # 系统
        self.icons.update({
            'settings': 'fa6s.gear',
            'help': 'fa6s.circle-question',
            'info': 'fa6s.circle-info',
            'warning': 'fa6s.triangle-exclamation',
            'error': 'fa6s.circle-xmark',
            'success': 'fa6s.circle-check',
            'loading': 'fa6s.spinner',
        })

        # 导航
        self.icons.update({
            'home': 'fa6s.house',
            'back': 'fa6s.arrow-left',
            'forward': 'fa6s.arrow-right',
            'refresh': 'fa6s.rotate',
            'search': 'fa6s.magnifying-glass',
            'filter': 'fa6s.filter',
        })

        # 文件
        self.icons.update({
            'file': 'fa6s.file',
            'folder': 'fa6s.folder',
            'database': 'fa6s.database',
            'backup': 'fa6s.floppy-disk',
        })

        # 动作
        self.icons.update({
            'play': 'fa6s.play',
            'pause': 'fa6s.pause',
            'stop': 'fa6s.stop',
            'submit': 'fa6s.paper-plane',
            'save': 'fa6s.floppy-disk',
            'cancel': 'fa6s.xmark',
            'confirm': 'fa6s.check',
        })

    def get_icon(self, icon_name: str, size: int = 16, color=None) -> QIcon:
        """获取 QIcon"""

        icon_id = self.icons.get(icon_name)
        if not icon_id:
            return QIcon()

        cache_key = f'{icon_id}_{size}_{color}'
        if cache_key in self.icon_cache:
            return self.icon_cache[cache_key]

        icon = qta.icon(
            icon_id,
            color=color,
            options=[{'scale_factor': 1.0}]
        )

        self.icon_cache[cache_key] = icon
        return icon

    # ---------- 状态 / 类型 / 动作 ----------

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
        return qta.icon(status_map.get(status, 'fa6s.circle-question'))

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
        return qta.icon(action_map.get(action, 'fa6s.circle-question'))

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
        return qta.icon(type_map.get(item_type, 'fa6s.circle-question'))

    def get_file_type_indicator(self, file_path):
        if not file_path:
            return qta.icon('fa6s.file')

        ext = os.path.splitext(file_path)[1].lower()
        ext_map = {
            '.json': 'fa6s.file-code',
            '.yaml': 'fa6s.file-code',
            '.yml': 'fa6s.file-code',
            '.toml': 'fa6s.file-code',
            '.db': 'fa6s.database',
            '.backup': 'fa6s.floppy-disk',
        }
        return qta.icon(ext_map.get(ext, 'fa6s.file'))