"""
环形进度图组件
带平滑过渡动画的圆环图
"""
import random

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush, QFont

from core.themes import DARK_THEME


class DonutChart(QWidget):
    """环形进度图"""

    def __init__(self, title: str, value: float, color: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.value = value
        self.target_value = value
        self.ring_color = color
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.theme = DARK_THEME

        # smooth animation
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(2000)
        self._step_timer = None

    def _animate(self):
        self.target_value = random.uniform(25, 85)
        if self._step_timer is not None:
            self._step_timer.stop()
        self._step_timer = QTimer(self)
        self._step_timer.timeout.connect(self._step)
        self._step_timer.start(16)

    def _step(self):
        diff = self.target_value - self.value
        if abs(diff) < 0.3:
            self.value = self.target_value
            if self._step_timer:
                self._step_timer.stop()
        else:
            self.value += diff * 0.08
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()

        # 卡片背景
        p.setPen(QPen(QColor(t["border"]), 1))
        p.setBrush(QBrush(QColor(t["bg_card"])))
        p.drawRoundedRect(0, 0, w, h, 12, 12)

        # 标题
        p.setPen(QColor(t["text_secondary"]))
        font = QFont("Segoe UI", 9)
        p.setFont(font)
        p.drawText(14, 22, self.title)

        # 绘制圆环
        cx = w // 2
        cy = (h + 20) // 2
        radius = min(w, h - 30) // 2 - 14
        pen_width = 8

        # 背景环
        bg_pen = QPen(QColor(t["chart_grid"]), pen_width)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(bg_pen)
        p.drawArc(cx - radius, cy - radius, 2 * radius, 2 * radius, 0, 360 * 16)

        # 值环
        ring_pen = QPen(QColor(self.ring_color), pen_width)
        ring_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(ring_pen)
        span = int(self.value / 100 * 360 * 16)
        p.drawArc(cx - radius, cy - radius, 2 * radius, 2 * radius, 90 * 16, -span)

        # 中心数值
        p.setPen(QColor(t["text_primary"]))
        font_big = QFont("Segoe UI", 14, QFont.Weight.Bold)
        p.setFont(font_big)
        text = f"{self.value:.0f}%"
        p.drawText(QRectF(cx - 30, cy - 12, 60, 24), Qt.AlignmentFlag.AlignCenter, text)

        p.end()
