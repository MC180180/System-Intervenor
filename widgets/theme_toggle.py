"""
主题切换开关组件
圆润的深色/浅色主题滑动开关，带太阳/月亮图标
"""
import math

from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QPainterPath

from core.themes import DARK_THEME


class ThemeToggle(QWidget):
    """圆润的深色/浅色主题切换开关"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(62, 30)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._is_dark = True
        self._knob_x = 4.0  # 初始位置（深色模式，月亮在左）
        self._anim = QPropertyAnimation(self, b"knobX")
        self._anim.setDuration(280)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.theme = DARK_THEME

    def get_knob_x(self):
        return self._knob_x

    def set_knob_x(self, val):
        self._knob_x = val
        self.update()

    knobX = pyqtProperty(float, get_knob_x, set_knob_x)

    def mousePressEvent(self, e):
        self._is_dark = not self._is_dark
        self._anim.stop()
        if self._is_dark:
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(4.0)
        else:
            self._anim.setStartValue(self._knob_x)
            self._anim.setEndValue(32.0)
        self._anim.start()
        # 通知父窗口切换主题
        main_win = self.window()
        if hasattr(main_win, 'toggle_theme'):
            main_win.toggle_theme()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 背景胶囊
        bg_color = QColor(self.theme["toggle_bg"])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(bg_color))
        p.drawRoundedRect(0, 0, 62, 30, 15, 15)

        # 滑块
        knob_color = QColor(self.theme["toggle_knob"])
        p.setBrush(QBrush(knob_color))
        shadow = QColor(0, 0, 0, 40)
        p.setPen(QPen(shadow, 0.5))
        p.drawEllipse(int(self._knob_x), 3, 24, 24)
        p.setPen(Qt.PenStyle.NoPen)

        # 太阳图标（右侧）
        sun_color = QColor(self.theme["toggle_icon_sun"])
        p.setPen(QPen(sun_color, 1.5))
        sun_cx, sun_cy = 44, 15
        p.drawEllipse(sun_cx - 4, sun_cy - 4, 8, 8)
        for angle in range(0, 360, 45):
            rad = math.radians(angle)
            x1 = sun_cx + 6 * math.cos(rad)
            y1 = sun_cy + 6 * math.sin(rad)
            x2 = sun_cx + 8 * math.cos(rad)
            y2 = sun_cy + 8 * math.sin(rad)
            p.drawLine(int(x1), int(y1), int(x2), int(y2))

        # 月亮图标（左侧）
        moon_color = QColor(self.theme["toggle_icon_moon"])
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(moon_color))
        moon_cx, moon_cy = 18, 15
        moon_path = QPainterPath()
        moon_path.addEllipse(moon_cx - 5, moon_cy - 5, 10, 10)
        cutout = QPainterPath()
        cutout.addEllipse(moon_cx - 2, moon_cy - 7, 10, 10)
        moon_path = moon_path.subtracted(cutout)
        p.drawPath(moon_path)

        p.end()
