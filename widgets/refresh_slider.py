"""
通用刷新频率滑条控件 - 嵌入各大卡片右上角
"""
from PyQt6.QtWidgets import QWidget, QSlider, QLabel, QHBoxLayout
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QColor

from core.card_config import RATE_PRESETS, get_card_rate_index, set_card_rate_index


class RefreshRateSlider(QWidget):
    """紧凑型刷新频率滑条"""
    
    def __init__(self, card_key, on_change_callback, parent=None):
        super().__init__(parent)
        self.card_key = card_key
        self.on_change = on_change_callback
        
        self.setFixedHeight(22)
        self.setMaximumWidth(200)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 0, 4, 0)
        layout.setSpacing(4)
        
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(len(RATE_PRESETS) - 1)
        self.slider.setTickPosition(QSlider.TickPosition.NoTicks)
        self.slider.setFixedWidth(80)
        self.slider.setFixedHeight(16)
        
        self.label = QLabel("")
        self.label.setFont(QFont("Segoe UI", 7))
        self.label.setFixedWidth(42)
        self.label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # 样式
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                background: rgba(255,255,255,0.08);
                height: 4px;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: rgba(255,255,255,0.5);
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }
            QSlider::handle:horizontal:hover {
                background: rgba(255,255,255,0.85);
            }
        """)
        self.label.setStyleSheet("color: rgba(255,255,255,0.4); font-size: 11px;")
        
        layout.addWidget(self.label)
        layout.addWidget(self.slider)
        
        # 载入持久化的值
        idx = get_card_rate_index(self.card_key)
        self.slider.setValue(idx)
        self._update_label(idx)
        
        self.slider.valueChanged.connect(self._on_slider_changed)
    
    def _update_label(self, idx):
        label_text, _ = RATE_PRESETS[idx]
        self.label.setText(label_text)
    
    def _on_slider_changed(self, idx):
        self._update_label(idx)
        _, interval_ms = RATE_PRESETS[idx]
        set_card_rate_index(self.card_key, idx)
        if self.on_change:
            self.on_change(interval_ms)
    
    def get_interval_ms(self):
        idx = self.slider.value()
        return RATE_PRESETS[idx][1]
