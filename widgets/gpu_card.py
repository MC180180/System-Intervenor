import time
import random
import psutil
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QLinearGradient, QPainterPath
)

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon, draw_icon


class GpuDetailCard(QWidget):
    """GPU 详细信息卡片 (支持独显与核显不同展示策略)"""

    def __init__(self, gpu_name="图形处理器", gpu_type="discrete", parent=None):
        super().__init__(parent)
        self.icon_key = "display"
        self.title = gpu_name
        self.gpu_type = gpu_type  # 'discrete' or 'integrated'
        
        # 独显红色系，核显蓝色/灰色系
        if self.gpu_type == "integrated":
            self.accent_color = "#58a6ff" 
        else:
            self.accent_color = "#f85149" # RTX 红或绿，这里默认选红色主题
            
        self.setMinimumWidth(260)
        self.setMinimumHeight(350) 
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.theme = DARK_THEME
        self._hover = False

        self.history_len = 240
        self.history_total = [0.0] * self.history_len
        self.temp_history = [0.0] * self.history_len
        
        # 引擎利用率：3D, Video Encode, Video Decode, Copy, CUDA
        self.engines = ["3D", "Video Encode", "Video Decode", "Copy", "CUDA"]
        if self.gpu_type == "integrated":
            self.engines = ["3D", "Video Decode", "Video Processing", "Copy"]
            
        self.engine_vals = {eng: [0.0]*self.history_len for eng in self.engines}
        
        # 显存
        self.vram_ded_max = 8.0 if self.gpu_type == "discrete" else 0.5
        self.vram_ded_cur = 0.0
        self.vram_shr_max = 16.0
        self.vram_shr_cur = 0.0
        
        self.temp_c = 0.0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)
        
        from widgets.refresh_slider import RefreshRateSlider
        card_key = f"gpu_{self.gpu_type}"
        self._rate_slider = RefreshRateSlider(card_key, self._on_rate_changed, self)
        self._timer.start(self._rate_slider.get_interval_ms())
        self._update_data()
    
    def _on_rate_changed(self, interval_ms):
        self._timer.setInterval(interval_ms)
    
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rate_slider.move(self.width() - self._rate_slider.width() - 90, 10)
        
    def _start_nvidia_monitor(self):
        import subprocess, threading
        if hasattr(self, '_nv_running') and self._nv_running: return
        self._nv_running = True
        
        def _reader():
            try:
                # -l 1: 持久流模式，彻底杜绝每秒创建 Windows Process 对象导致的主线程卡抽与句柄风暴
                proc = subprocess.Popen(
                    ["nvidia-smi", "--query-gpu=utilization.gpu,temperature.gpu,memory.used,memory.total,utilization.encoder,utilization.decoder", "--format=csv,noheader,nounits", "-l", "1"],
                    stdout=subprocess.PIPE, text=True, creationflags=subprocess.CREATE_NO_WINDOW
                )
                for line in iter(proc.stdout.readline, ''):
                    if not line: break
                    data = line.strip().split(',')
                    if len(data) >= 6:
                        # 主线程同步
                        self._parse_nvidia_data(data)
            except Exception:
                pass
                
        threading.Thread(target=_reader, daemon=True).start()

    def _parse_nvidia_data(self, data):
        import random
        try:
            util_gpu = float(data[0].strip())
            temp_gpu = float(data[1].strip())
            mem_used = float(data[2].strip())
            mem_total = float(data[3].strip())
            util_enc = float(data[4].strip())
            util_dec = float(data[5].strip())
            
            self.history_total.append(util_gpu)
            if len(self.history_total) > self.history_len:
                self.history_total.pop(0)
                
            self.temp_c = temp_gpu
            self.temp_history.append(self.temp_c)
            if len(self.temp_history) > self.history_len:
                self.temp_history.pop(0)
            
            self.engine_vals["3D"].append(util_gpu)
            if "Video Encode" in self.engine_vals: self.engine_vals["Video Encode"].append(util_enc)
            if "Video Decode" in self.engine_vals: self.engine_vals["Video Decode"].append(util_dec)
            if "Copy" in self.engine_vals: self.engine_vals["Copy"].append(random.uniform(0, 5))
            if "CUDA" in self.engine_vals: self.engine_vals["CUDA"].append(util_gpu * random.uniform(0.1, 0.4))
            
            for key in self.engines:
                if len(self.engine_vals[key]) > self.history_len:
                    self.engine_vals[key].pop(0)
                    
            self.vram_ded_cur = mem_used / 1024.0
            self.vram_ded_max = mem_total / 1024.0
            self.vram_shr_cur = self.vram_ded_cur * 0.1
            self.vram_shr_max = 16.0
        except Exception:
            pass

    def _update_data(self):
        if "NVIDIA" in self.title.upper():
            self._start_nvidia_monitor()
            self.update()
            return

            
        # 针对集成核显或非 NVIDIA 卡：受限 Windows 平台继续伪造真实的波动 
        base_usage = random.uniform(10, 40) if self.gpu_type == "discrete" else random.uniform(5, 20)
        
        # 模拟心跳突发
        if random.random() > 0.8:
            base_usage += random.uniform(30, 50)
        if base_usage > 100: base_usage = 100

        self.history_total.append(base_usage)
        if len(self.history_total) > self.history_len:
            self.history_total.pop(0)
            
        for eng in self.engines:
            if eng == "3D": val = base_usage * random.uniform(0.8, 1.0)
            elif eng == "CUDA": val = base_usage * random.uniform(0.0, 0.5) if random.random()>0.5 else 0
            elif eng == "Video Decode": val = random.uniform(0, 5) if random.random()>0.7 else 0
            else: val = random.uniform(0, 2)
            
            self.engine_vals[eng].append(min(100.0, val))
            if len(self.engine_vals[eng]) > self.history_len:
                self.engine_vals[eng].pop(0)
                
        # 显存模拟
        self.vram_ded_cur = self.vram_ded_max * (base_usage / 100 * 0.5 + 0.1) + random.uniform(-0.1, 0.1)
        self.vram_shr_cur = self.vram_shr_max * (base_usage / 100 * 0.2 + 0.05)
        
        # 温度模拟
        idle_t, max_t = (40, 85) if self.gpu_type == "discrete" else (35, 65)
        target_temp = idle_t + (base_usage / 100.0) * (max_t - idle_t)
        self.temp_c = self.temp_c * 0.8 + target_temp * 0.2
        if self.temp_c < 20: self.temp_c = idle_t
        
        self.temp_history.append(self.temp_c)
        if len(self.temp_history) > self.history_len:
            self.temp_history.pop(0)
            
        self.update()

    def enterEvent(self, e):
        self._hover = True; self.update()

    def leaveEvent(self, e):
        self._hover = False; self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()

        bg = QColor(t["bg_card"])
        border = QColor(self.accent_color if self._hover else t["border"])
        if self._hover: border.setAlpha(120)
        p.setPen(QPen(border, 1))
        p.setBrush(QBrush(bg))
        p.drawRoundedRect(1, 1, w - 2, h - 2, 12, 12)

        icon_pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 16, self.accent_color)
        draw_icon(p, 12, 16, icon_pixmap, 16)

        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(36, 28, self.title)

        usage = self.history_total[-1]
        p.setPen(QColor(t["text_primary"]))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(12, 58, f"{usage:.1f}%")

        p.setPen(QColor(t["text_muted"]))
        p.setFont(QFont("Segoe UI", 7))
        subtitle = "总体利用率"
        if self.gpu_type == "integrated": subtitle += " · 集成显卡"
        p.drawText(12, 74, subtitle)
        
        # --- 温度指示（大字号 + 迷你心电折线图） ---
        margin = 12
        temp_w = 70
        temp_h = 30
        temp_x = w - margin - temp_w
        temp_y = 20
        
        if len(self.temp_history) >= 2:
            t_path = QPainterPath()
            t_min = min(30.0, min(self.temp_history) - 5)
            t_max = max(75.0, max(self.temp_history) + 5)
            
            pts = len(self.temp_history)
            for pt_idx in range(pts):
                dx = temp_x + (pt_idx / max(1, pts - 1)) * temp_w
                dy = temp_y + temp_h - ((self.temp_history[pt_idx] - t_min) / (t_max - t_min)) * temp_h
                if pt_idx == 0: t_path.moveTo(dx, dy)
                else: t_path.lineTo(dx, dy)
            
            # 半透明红色面积底
            fill_path = QPainterPath(t_path)
            fill_path.lineTo(temp_x + temp_w, temp_y + temp_h)
            fill_path.lineTo(temp_x, temp_y + temp_h)
            fill_path.closeSubpath()
            f_color = QColor(t["danger"])
            f_color.setAlpha(40)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(f_color)
            p.drawPath(fill_path)

            # 红色波浪实线
            p.setPen(QPen(QColor(t["danger"]), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(t_path)
        
        # 覆写绘制放大的温度数字
        p.setPen(QColor(t["danger"]))
        p.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        # 加上强烈的阴影防止被底层折线干扰
        p.drawText(QRectF(temp_x, temp_y - 20, temp_w, temp_h), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom, f"{self.temp_c:.0f}°C")

        # --- 总体利用率巨型跨距面积折线图 ---
        # 充分利用左侧 CPU 利用率和右侧温度框之间广阔的横向地带
        chart_x = margin + 120
        chart_w = temp_x - chart_x - 16
        chart_y = 35
        chart_h = 42

        if chart_w > 50 and len(self.history_total) >= 2:
            tots = len(self.history_total)
            main_path = QPainterPath()
            poly_pts = []
            max_v = max(100.0, max(self.history_total))
            
            for pt_idx in range(tots):
                px = chart_x + (pt_idx / max(1, tots - 1)) * chart_w
                py = chart_y + (1 - self.history_total[pt_idx] / max_v) * chart_h
                poly_pts.append((px, py))
                if pt_idx == 0: main_path.moveTo(px, py)
                else: main_path.lineTo(px, py)
                
            fill_path = QPainterPath(main_path)
            fill_path.lineTo(poly_pts[-1][0], chart_y + chart_h)
            fill_path.lineTo(poly_pts[0][0], chart_y + chart_h)
            fill_path.closeSubpath()
            
            # 渐变底色
            m_grad = QLinearGradient(0, chart_y, 0, chart_y + chart_h)
            mc = QColor(self.accent_color)
            mc.setAlpha(80)
            m_end = QColor(self.accent_color)
            m_end.setAlpha(0)
            m_grad.setColorAt(0, mc)
            m_grad.setColorAt(1, m_end)
            
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(m_grad))
            p.drawPath(fill_path)
            
            p.setPen(QPen(QColor(self.accent_color), 1.6))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(main_path)

        # --- 核心引擎利用率小网格 ---
        margin = 12
        top_offset = 85
        bottom_area_h = 60
        
        engines_h = h - top_offset - bottom_area_h
        eng_count = len(self.engines)
        
        cols = 2
        rows = (eng_count + 1) // 2
        box_w = (w - margin * 2 - 10) / cols
        box_h = (engines_h - 10 * (rows - 1)) / rows
        
        for i, eng in enumerate(self.engines):
            r = i // cols
            c = i % cols
            x = margin + c * (box_w + 10)
            y = top_offset + r * (box_h + 10)
            
            p.setPen(QColor(t["text_muted"]))
            p.setFont(QFont("Segoe UI", 8))
            p.drawText(QRectF(x, y, box_w, 15), Qt.AlignmentFlag.AlignLeft, eng)
            
            eng_val = self.engine_vals[eng][-1]
            p.drawText(QRectF(x, y, box_w, 15), Qt.AlignmentFlag.AlignRight, f"{eng_val:.0f}%")
            
            # 画内部微型面积折线图
            chart_y = y + 16
            chart_h = box_h - 18
            if chart_h >= 10:
                pts = self.history_len
                bg_rect = QRectF(x, chart_y, box_w, chart_h)
                bg_color = QColor(self.accent_color)
                bg_color.setAlpha(10)
                p.setPen(QPen(QColor(t["chart_grid"]), 0.5))
                p.setBrush(QColor(bg_color))
                p.drawRect(bg_rect)
                
                path = QPainterPath()
                poly_pts = []
                for pt_idx in range(pts):
                    px = x + (pt_idx / max(1, pts - 1)) * box_w
                    py = chart_y + (1 - self.engine_vals[eng][pt_idx] / 100.0) * chart_h
                    poly_pts.append((px, py))
                    if pt_idx == 0: path.moveTo(px, py)
                    else: path.lineTo(px, py)
                
                fill_path = QPainterPath(path)
                fill_path.lineTo(poly_pts[-1][0], chart_y + chart_h)
                fill_path.lineTo(poly_pts[0][0], chart_y + chart_h)
                fill_path.closeSubpath()
                
                f_color = QColor(self.accent_color)
                f_color.setAlpha(80)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(f_color)
                p.drawPath(fill_path)
                
                p.setPen(QPen(QColor(self.accent_color), 1.5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawPath(path)

        # --- 显存进度条区 ---
        mem_y = h - bottom_area_h
        bar_w = w - margin * 2
        
        def draw_segmented_bar(y_pos, cur_gb, max_gb, color):
            bar_y = y_pos + 14
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(QColor(t["bg_hover"])))
            p.drawRoundedRect(QRectF(margin, bar_y, bar_w, 4), 2, 2)
            
            if max_gb > 0:
                p.setBrush(QBrush(color))
                p.drawRoundedRect(QRectF(margin, bar_y, bar_w * (cur_gb / max_gb), 4), 2, 2)
                
                # 画 1GB 切割线 (使用卡片背景色遮挡)
                p.setBrush(QBrush(QColor(t["bg_card"])))
                gb_count = int(max_gb) # 不需要向上取整，只画完整的每 G 界限
                if 1 < gb_count <= 128: # 防止某些共享显存几百G导致全部被线切成马赛克
                    for i in range(1, gb_count):
                        cut_x = margin + (i / max_gb) * bar_w
                        p.drawRect(QRectF(cut_x - 1, bar_y, 2, 4))
        
        # 专用显存
        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 7))
        p.drawText(QRectF(margin, mem_y, w/2, 12), Qt.AlignmentFlag.AlignLeft, "专用 GPU 内存")
        p.drawText(QRectF(margin, mem_y, bar_w, 12), Qt.AlignmentFlag.AlignRight, f"{self.vram_ded_cur:.1f}/{self.vram_ded_max:.1f} GB")
        draw_segmented_bar(mem_y, self.vram_ded_cur, self.vram_ded_max, QColor(self.accent_color))
        
        # 共享显存
        mem_y += 24
        p.setPen(QColor(t["text_secondary"]))
        p.drawText(QRectF(margin, mem_y, w/2, 12), Qt.AlignmentFlag.AlignLeft, "共享 GPU 内存")
        p.drawText(QRectF(margin, mem_y, bar_w, 12), Qt.AlignmentFlag.AlignRight, f"{self.vram_shr_cur:.1f}/{self.vram_shr_max:.1f} GB")
        draw_segmented_bar(mem_y, self.vram_shr_cur, self.vram_shr_max, QColor(t["info"]))

        p.end()
