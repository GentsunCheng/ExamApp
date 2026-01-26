from PySide6.QtGui import QColor
from PySide6.QtCore import QObject, QEvent
from PySide6.QtWidgets import QAbstractScrollArea, QAbstractItemView, QScroller, QScrollerProperties
import sys
import subprocess


class SmoothScrollFilter(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._configured = set()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            area = self._find_scroll_area(obj)
            if area is None:
                return False
            if isinstance(area, QAbstractItemView):
                try:
                    area.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                    area.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
                except Exception:
                    pass
            self._ensure_scroller(area)
        return False

    @staticmethod
    def _find_scroll_area(obj):
        w = obj
        while w is not None:
            if isinstance(w, QAbstractScrollArea):
                return w
            w = w.parent()
        return None

    def _ensure_scroller(self, area):
        key = id(area)
        if key in self._configured:
            return
        self._configured.add(key)
        scroller = QScroller.scroller(area)
        props = QScrollerProperties(scroller.scrollerProperties())
        try:
            props.setScrollMetric(QScrollerProperties.ScrollMetric.DecelerationFactor, 0.5)
            props.setScrollMetric(QScrollerProperties.ScrollMetric.MaximumVelocity, 1.5)
            props.setScrollMetric(QScrollerProperties.ScrollMetric.MinimumVelocity, 0.01)
            props.setScrollMetric(QScrollerProperties.ScrollMetric.FrameRate, QScrollerProperties.FrameRates.Fps60)
            props.setScrollMetric(QScrollerProperties.ScrollMetric.VerticalOvershootPolicy,
                                  QScrollerProperties.OvershootPolicy.OvershootWhenScrollable)
            props.setScrollMetric(QScrollerProperties.ScrollMetric.HorizontalOvershootPolicy,
                                  QScrollerProperties.OvershootPolicy.OvershootWhenScrollable)
        except Exception:
            pass
        scroller.setScrollerProperties(props)


class ThemeManager:
    def __init__(self):
        self.mode = 'light'
        self._smooth_scroll_filter = None
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

    def get_scrollbar_style(self):
        colors = self.get_theme_colors()
        bg_track = colors.get('border_light', '#eef2f6')
        bg_handle = colors.get('input_border', '#d1d9e6')
        bg_handle_hover = colors.get('primary', '#409eff')
        return f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 4px 2px 4px 0;
            }}
            QScrollBar::handle:vertical {{
                background: {bg_handle};
                min-height: 40px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {bg_handle_hover};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
                subcontrol-origin: margin;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: {bg_track};
                border-radius: 5px;
            }}
            QScrollBar:horizontal {{
                background: transparent;
                height: 10px;
                margin: 0 4px 2px 4px;
            }}
            QScrollBar::handle:horizontal {{
                background: {bg_handle};
                min-width: 40px;
                border-radius: 5px;
            }}
            QScrollBar::handle:horizontal:hover {{
                background: {bg_handle_hover};
            }}
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
                width: 0px;
                subcontrol-origin: margin;
            }}
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
                background: {bg_track};
                border-radius: 5px;
            }}
        """

    def install_smooth_scroll(self, app):
        if self._smooth_scroll_filter is None:
            self._smooth_scroll_filter = SmoothScrollFilter(app)
            app.installEventFilter(self._smooth_scroll_filter)

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
