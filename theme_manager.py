from PySide6.QtGui import QColor


class ThemeManager:
    def __init__(self):
        self.mode = 'light'

    def get_theme_colors(self):
        if self.mode == 'light':
            return {
                'background': '#f5f7fa',
                'card_background': '#ffffff',
                'border': '#e4e7ed',
                'border_light': '#eef2f6',
                'text_primary': '#303133',
                'text_secondary': '#606266',
                'text_tertiary': '#909399',
                'text_inverse': '#ffffff',
                'primary': '#409eff',
                'success': '#67c23a',
                'warning': '#e6a23c',
                'error': '#f56c6c',
                'info': '#909399',
                'success_light': '#e1f3d8',
                'warning_light': '#fdf6ec',
                'error_light': '#fde2e2',
                'info_light': '#edf2fc',
                'input_background': '#ffffff',
                'input_border': '#d1d9e6',
                'progress_background': '#eef2f6',
                'button_primary': '#409eff',
                'button_primary_hover': '#66b1ff'
            }
        else:
            return {
                'background': '#1f1f1f',
                'card_background': '#2a2a2a',
                'border': '#3a3a3a',
                'border_light': '#444444',
                'text_primary': '#eaeaea',
                'text_secondary': '#cfcfcf',
                'text_tertiary': '#b3b3b3',
                'text_inverse': '#000000',
                'primary': '#409eff',
                'success': '#67c23a',
                'warning': '#e6a23c',
                'error': '#f56c6c',
                'info': '#909399',
                'success_light': '#29412a',
                'warning_light': '#3d3324',
                'error_light': '#3a2626',
                'info_light': '#2b2e33',
                'input_background': '#2a2a2a',
                'input_border': '#3a3a3a',
                'progress_background': '#333333',
                'button_primary': '#409eff',
                'button_primary_hover': '#66b1ff'
            }

    def set_mode(self, mode):
        self.mode = mode if mode in ('light', 'dark') else 'light'


theme_manager = ThemeManager()