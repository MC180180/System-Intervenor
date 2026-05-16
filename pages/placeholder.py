"""
占位页面
用于尚未实现的功能模块
"""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon


class PlaceholderPage(QWidget):
    """占位页面"""

    def __init__(self, icon_key: str, title: str, desc: str, parent=None):
        super().__init__(parent)
        self.theme = DARK_THEME
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        self.title_label = QLabel(title)
        self.title_label.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        layout.addWidget(self.title_label)

        self.desc_label = QLabel(desc)
        self.desc_label.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.desc_label)

        # 大图标
        self.icon_key = icon_key
        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addStretch()
        layout.addWidget(self.icon_label)

        self.hint_label = QLabel("功能开发中...")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setFont(QFont("Segoe UI", 12))
        layout.addWidget(self.hint_label)
        layout.addStretch()

    def get_anim_targets(self):
        return [self.title_label, self.desc_label, self.icon_label, self.hint_label]

    def apply_theme(self, theme):
        self.theme = theme
        self.title_label.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        self.desc_label.setStyleSheet(f"color: {theme['text_secondary']}; background: transparent;")
        self.hint_label.setStyleSheet(f"color: {theme['text_muted']}; background: transparent;")
        pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 64, theme["text_muted"])
        self.icon_label.setPixmap(pixmap)
