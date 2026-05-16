"""
状态信息卡片组件
用于顶部区域展示关键指标，带图标、渐变装饰条和 hover 效果
"""
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QLinearGradient, QPainterPath
)

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon, draw_icon


class StatusCard(QWidget):
    """顶部状态信息卡片"""

    def __init__(self, icon_key: str, title: str, value: str, subtitle: str, color: str, parent=None):
        super().__init__(parent)
        self.icon_key = icon_key
        self.title = title
        self.value = value
        self.subtitle = subtitle
        self.accent_color = color
        self.setMinimumHeight(90)
        self.setMinimumWidth(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.theme = DARK_THEME
        self._hover = False

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()

        # 卡片背景
        bg = QColor(t["bg_card"])
        border = QColor(t["border"])
        if self._hover:
            border = QColor(self.accent_color)
            border.setAlpha(120)
        p.setPen(QPen(border, 1))
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        # 顶部渐变条
        grad = QLinearGradient(0, 0, w, 0)
        c1 = QColor(self.accent_color)
        c1.setAlpha(200)
        c2 = QColor(self.accent_color)
        c2.setAlpha(60)
        grad.setColorAt(0, c1)
        grad.setColorAt(1, c2)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(grad))
        path = QPainterPath()
        path.moveTo(12, 1)
        path.lineTo(w - 12, 1)
        path.arcTo(w - 14, 1, 12, 12, 90, -90)
        path.lineTo(w - 1, 4)
        path.lineTo(1, 4)
        path.lineTo(1, 12)
        path.arcTo(1, 1, 12, 12, 180, -90)
        p.drawPath(path)

        # 图标
        icon_pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 20, self.accent_color)
        draw_icon(p, 16, 20, icon_pixmap, 20)

        # 标题
        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 9))
        p.drawText(44, 32, self.title)

        # 数值
        p.setPen(QColor(t["text_primary"]))
        p.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        p.drawText(16, 68, self.value)

        # 副标题
        p.setPen(QColor(t["text_muted"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(16, 84, self.subtitle)

        p.end()
