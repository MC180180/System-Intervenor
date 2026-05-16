import psutil
import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QLinearGradient, QPainterPath
)

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon, draw_icon


class MemoryDetailCard(QWidget):
    """内存详细信息大卡片，分块展示物理内存和虚拟内存（每块8GB或自定义）"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_key = "memory"
        self.title = "内存使用"
        self.accent_color = "#a371f7"  # 紫色主题
        
        self.setMinimumWidth(260)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.theme = DARK_THEME
        self._hover = False
        
        # 提取硬件名称
        self.hardware_name = ""
        try:
            import subprocess
            # 使用 CREATE_NO_WINDOW 让 Windows 隐式读取 WMI 防弹窗
            out = subprocess.check_output(["wmic", "memorychip", "get", "manufacturer,speed", "/format:csv"], creationflags=0x08000000, text=True, timeout=2)
            for line in out.split('\n'):
                if ',' in line and 'Node' not in line and 'Manufacturer' not in line:
                    parts = line.split(',')
                    speed = parts[-1].strip()
                    man = parts[-2].strip()
                    if speed and speed.isdigit():
                        if not man or man.lower() == "unknown": man = "Physical Memory"
                        self.hardware_name = f"{man} {speed} MHz"
                        break
        except: pass

        # 以多少 GB 为一行进行切分
        self.chunk_size_gb = 8.0
        
        # 初始默认值
        self.phys_total_gb = 16.0
        self.phys_used_gb = 0.0
        self.swap_total_gb = 16.0
        self.swap_used_gb = 0.0
        
        self.subtitle = ""

        # 定时器刷新数据
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)
        
        from widgets.refresh_slider import RefreshRateSlider
        self._rate_slider = RefreshRateSlider("mem", self._on_rate_changed, self)
        self._timer.start(self._rate_slider.get_interval_ms())
        self._update_data()
    
    def _on_rate_changed(self, interval_ms):
        self._timer.setInterval(interval_ms)
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rate_slider.move(self.width() - self._rate_slider.width() - 8, 40)

    def _update_data(self):
        # 物理内存
        mem = psutil.virtual_memory()
        self.phys_total_gb = mem.total / (1024 ** 3)
        self.phys_used_gb = mem.used / (1024 ** 3)
        # Windows上，psutil.virtual_memory().used 的计算有时不一定刚好匹配系统显示，但这里正常用
        
        # 交换/虚拟内存
        swap = psutil.swap_memory()
        self.swap_total_gb = swap.total / (1024 ** 3)
        self.swap_used_gb = swap.used / (1024 ** 3)
        
        self.subtitle = f"物理 {self.phys_total_gb:.1f} GB | 虚拟 {self.swap_total_gb:.1f} GB"
        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def _draw_memory_bars(self, p, x, y, w, h, total_gb, used_gb, color_rgb, title):
        """绘制内存分块条"""
        t = self.theme
        
        # 标题
        p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        p.setPen(QColor(t["text_secondary"]))
        p.drawText(int(x), int(y + 12), title)
        
        usage_text = f"{used_gb:.1f} GB / {total_gb:.1f} GB"
        p.drawText(QRectF(x, y, w, 15), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, usage_text)
        
        # 计算行数 (每行8GB)
        # 向上取整，不足8G的单独成一行
        rows = math.ceil(total_gb / self.chunk_size_gb)
        if rows <= 0:
            return y + 20
            
        bar_area_y = y + 24
        bar_area_h = h - 24
        spacing = 6
        
        # 如果超出高度限制，压缩行高
        row_h = (bar_area_h - spacing * (rows - 1)) / rows
        # 限制每行最大高度，防止看着太胖
        row_h = min(row_h, 24)
        
        font_small = QFont("Segoe UI", 8)
        p.setFont(font_small)

        # 逐行绘制
        remaining_used = used_gb
        
        for i in range(rows):
            # 这行代表的最大容量（正常是chunk_size_gb，最后一行可能是余数）
            if i == rows - 1 and (total_gb % self.chunk_size_gb) != 0:
                row_cap = total_gb % self.chunk_size_gb
            else:
                row_cap = self.chunk_size_gb
                
            # 这行的实际使用量
            row_used = min(remaining_used, row_cap)
            remaining_used -= row_used
            if remaining_used < 0:
                remaining_used = 0
                
            y_i = bar_area_y + i * (row_h + spacing)
            
            # 画背景条
            bg_rect = QRectF(x, y_i, w, row_h)
            p.setPen(Qt.PenStyle.NoPen)
            bg_color = QColor(color_rgb)
            bg_color.setAlpha(20) # 极浅的背景
            p.setBrush(QBrush(bg_color))
            p.drawRoundedRect(bg_rect, 4, 4)
            
            # 画已用比例条
            if row_used > 0:
                ratio = row_used / row_cap
                fill_w = w * ratio
                fill_rect = QRectF(x, y_i, fill_w, row_h)
                
                # 设置填充颜色
                fill_color = QColor(color_rgb)
                # 根据该条块的饱满程度改变颜色的明暗
                fill_color.setAlpha(int(100 + ratio * 155))
                p.setBrush(QBrush(fill_color))
                
                # 如果没满，保持右侧为直角或者小圆角以显示裁切
                if fill_w >= w - 1:
                    p.drawRoundedRect(fill_rect, 4, 4)
                else:
                    path = QPainterPath()
                    path.moveTo(x + fill_w, y_i)
                    path.lineTo(x + fill_w, y_i + row_h)
                    path.lineTo(x + 4, y_i + row_h)
                    path.arcTo(x, y_i + row_h - 8, 8, 8, -90, -90)
                    path.lineTo(x, y_i + 4)
                    path.arcTo(x, y_i, 8, 8, 180, -90)
                    path.closeSubpath()
                    p.drawPath(path)
            
            # 绘制边框（任务管理器风）
            p.setPen(QPen(QColor(t["chart_grid"]), 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(bg_rect, 4, 4)
            
            # 文字（比如 8GB）
            p.setPen(QColor(t["text_primary"]) if row_used > row_cap * 0.6 else QColor(t["text_secondary"]))
            p.drawText(bg_rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{row_cap:.1f}G")
            if row_used > 0.01:
                p.setPen(QColor(t["bg_primary"]) if row_used > row_cap * 0.3 else QColor(t["text_primary"]))
                p.drawText(bg_rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"{row_used:.1f}G")

        return bar_area_y + rows * (row_h + spacing)

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



        # 头部：图标/标题
        icon_pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 16, self.accent_color)
        draw_icon(p, 12, 16, icon_pixmap, 16)

        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(36, 28, self.title)
        
        if self.hardware_name:
            title_adv = p.fontMetrics().horizontalAdvance(self.title)
            p.setPen(QColor(t.get("text_muted", "#484f58")))
            p.drawText(36 + title_adv + 8, 28, self.hardware_name)

        # 物理内存总使用数值显示
        p.setPen(QColor(t["text_primary"]))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(12, 58, f"{self.phys_used_gb:.1f} GB")

        p.setPen(QColor(t["text_muted"]))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(12, 74, self.subtitle)

        # --- 绘制内存分块面板 ---
        margin = 12
        top_offset = 85
        bottom_padding = 16
        
        avail_h = h - top_offset - bottom_padding
        if avail_h > 40:
            # 上下两部分等分高度（视实际情况微调，物理内存行可能更多）
            phys_rows = math.ceil(self.phys_total_gb / self.chunk_size_gb)
            virt_rows = math.ceil(self.swap_total_gb / self.chunk_size_gb)
            
            # 按行数权重分配高度，同时给中间留间距
            mid_spacing = 20
            total_rows = phys_rows + virt_rows
            if total_rows > 0:
                phys_h = (avail_h - mid_spacing) * (phys_rows / total_rows)
                virt_h = (avail_h - mid_spacing) * (virt_rows / total_rows)
            else:
                phys_h = virt_h = (avail_h - mid_spacing) / 2
                
            # 物理内存
            phys_color = self.accent_color
            end_y = self._draw_memory_bars(
                p, margin, top_offset, w - margin * 2, phys_h,
                self.phys_total_gb, self.phys_used_gb, phys_color,
                "物理内存分配"
            )
            
            # 虚拟内存 (更浅/透的同色系，或者稍微偏蓝)
            virt_color = "#8b949e" # theme 中偏向 text_secondary，或者提取 t["accent_hover"]
            if "name" in t and t["name"] == "dark":
                virt_color = "#4c5561" # 深色下用灰紫
            
            self._draw_memory_bars(
                p, margin, top_offset + phys_h + mid_spacing, w - margin * 2, virt_h,
                self.swap_total_gb, self.swap_used_gb, virt_color,
                "虚拟内存 (Swap)"
            )

        p.end()
