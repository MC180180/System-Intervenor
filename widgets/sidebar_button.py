"""
侧边栏按钮组件
带 SVG 图标、活跃状态指示条和 hover 效果
"""
from PyQt6.QtWidgets import QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QColor, QBrush

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon, draw_icon


class SidebarButton(QPushButton):
    """带图标和工具提示的侧边栏按钮"""
    right_clicked = pyqtSignal(str)

    def __init__(self, icon_key: str, label: str, parent=None):
        super().__init__(parent)
        self.icon_key = icon_key
        self.label_text = label
        self.setFixedSize(48, 48)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip(label)
        self._is_active = False
        self._hover = False
        self._is_disabled = False
        self.theme = DARK_THEME

    def set_disabled_state(self, disabled: bool):
        self._is_disabled = disabled
        self.update()

    def set_active(self, active: bool):
        self._is_active = active
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.RightButton:
            self.right_clicked.emit(self.icon_key)
        else:
            if not getattr(self, '_is_disabled', False):
                super().mousePressEvent(e)

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

        # 背景
        if getattr(self, '_is_disabled', False):
            pass
        elif self._is_active:
            bg = QColor(t["accent"])
            bg.setAlpha(25)
            p.setBrush(QBrush(bg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(4, 4, 40, 40, 10, 10)
            # 左侧指示条
            accent = QColor(t["accent"])
            p.setBrush(QBrush(accent))
            p.drawRoundedRect(0, 12, 3, 24, 1.5, 1.5)
        elif self._hover:
            bg = QColor(t["bg_hover"])
            p.setBrush(QBrush(bg))
            p.setPen(Qt.PenStyle.NoPen)
            p.drawRoundedRect(4, 4, 40, 40, 10, 10)

        # 图标
        if getattr(self, '_is_disabled', False):
            color = t.get("text_muted", "#484f58")
        else:
            color = t["sidebar_icon_active"] if self._is_active else (
                t["text_primary"] if self._hover else t["sidebar_icon_inactive"]
            )
        pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 22, color)
        draw_icon(p, 13, 13, pixmap, 22)
        p.end()
