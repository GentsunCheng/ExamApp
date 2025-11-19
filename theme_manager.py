from PySide6.QtGui import QColor
import sys
import subprocess


class ThemeManager:
    def __init__(self):
        self.mode = 'light'
        try:
            self.auto_detect_mode()
        except Exception:
            pass

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
                'text_inverse': '#ffffff',
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

    def auto_detect_mode(self):
        if sys.platform != 'darwin':
            return
        try:
            r = subprocess.run(['defaults', 'read', '-g', 'AppleInterfaceStyle'], capture_output=True, text=True)
            if r.returncode == 0:
                v = (r.stdout or '').strip().lower()
                self.mode = 'dark' if v == 'dark' else 'light'
            else:
                self.mode = 'light'
        except Exception:
            self.mode = 'light'


theme_manager = ThemeManager()