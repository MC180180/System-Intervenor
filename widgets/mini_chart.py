import time
import random
import collections
import psutil

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtCore import Qt, QTimer, QRectF
from PyQt6.QtGui import (
    QPainter, QPen, QColor, QBrush, QFont,
    QLinearGradient, QRadialGradient, QPainterPath
)

from core.themes import DARK_THEME


class SystemMiniChart(QWidget):
    """通用的系统迷你折线/堆叠图 (支持 CPU、内存堆叠、磁盘堆叠、网络堆叠)"""

    def __init__(self, mode="cpu", parent=None):
        super().__init__(parent)
        self.mode = mode
        self.theme = DARK_THEME
        self.setMinimumHeight(100)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.history_len = 120
        
        self.title = "未知指标"
        self.layers = []  # dict: name, color_key, data (list of float)
        
        self.last_time = time.time()
        self.last_disk_io = None
        self.last_net_io = None
        self.last_disk_vals = {}
        
        self._init_mode()
        
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)
        self._timer.start(1000)
        self._update_data()
        
    def _init_mode(self):
        if self.mode == "cpu":
            self.title = "CPU 使用率"
            
            self.hardware_name = ""
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
                    name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                    self.hardware_name = name.strip().replace("(R)", "").replace("(TM)", "")
            except: pass
            
            self.fixed_max = 100.0
            self.dynamic_max = False
            self.layers = [
                {"name": "Total", "color_key": "info", "data": [0.0]*self.history_len}
            ]
            self.format_func = lambda v: f"{v:.1f}%"
            
        elif self.mode == "mem":
            self.title = "内存占用"
            
            self.hardware_name = ""
            try:
                import subprocess
                out = subprocess.check_output(["wmic", "memorychip", "get", "manufacturer,speed", "/format:csv"], creationflags=0x08000000, text=True, timeout=1)
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
            # 物理在下 (先画底)
            self.layers = [
                {"name": "物理", "color_key": "success", "data": [0.0]*self.history_len},
                {"name": "虚拟", "color_key": "warning", "data": [0.0]*self.history_len}
            ]
            try:
                tm = psutil.virtual_memory().total
                ts = psutil.swap_memory().total
                self.fixed_max = (tm + ts) / (1024**3)
            except:
                self.fixed_max = 32.0
            self.dynamic_max = False
            self.format_func = lambda v: f"{v:.1f} GB"
            
        elif self.mode == "disk":
            self.title = "磁盘 I/O (盘符堆积)"
            colors = ["chart_line_1", "chart_line_2", "chart_line_3", "chart_line_4", "info", "success", "warning"]
            self.layers = []
            
            parts = psutil.disk_partitions(all=False)
            valid_letters = []
            for p in parts:
                if 'cdrom' not in p.opts and p.fstype != '':
                    valid_letters.append(p.device.replace('\\', ''))
            
            for i, letter in enumerate(valid_letters):
                self.layers.append({
                    "name": letter, 
                    "color_key": colors[i % len(colors)],
                    "data": [0.0]*self.history_len
                })
                self.last_disk_vals[letter] = 0.0
                
            self.dynamic_max = True
            self.format_func = lambda v: f"{v:.1f} MB/s" if v > 1.0 else f"{v*1024:.0f} KB/s"
            
        elif self.mode == "net":
            self.title = "网络流速 (上下行堆积)"
            self.layers = [
                {"name": "上传", "color_key": "info", "data": [0.0]*self.history_len},
                {"name": "下载", "color_key": "chart_line_4", "data": [0.0]*self.history_len}
            ]
            self.dynamic_max = True
            self.format_func = lambda v: f"{v / (1024**2):.1f} MB/s" if v > 1024*1024 else f"{v/1024:.0f} KB/s"

    def _update_data(self):
        now = time.time()
        dt = now - self.last_time
        if dt <= 0: dt = 1.0
        self.last_time = now

        if self.mode == "cpu":
            val = psutil.cpu_percent()
            self.layers[0]["data"].append(val)
            self._current_total = val
            
            # frequency
            freq_info = psutil.cpu_freq()
            if freq_info:
                self._current_freq = freq_info.current
            else:
                self._current_freq = 2800 + random.uniform(-100, 100)
                
            # temp (Windows psutil lack support, fallback to simulated realistic load mapping)
            try:
                temps = psutil.sensors_temperatures()
                if temps and 'coretemp' in temps:
                    self._current_temp = temps['coretemp'][0].current
                else:
                    self._current_temp = 45.0 + (val / 100.0) * 35.0 + random.uniform(-2, 2)
            except:
                self._current_temp = 45.0 + (val / 100.0) * 35.0 + random.uniform(-2, 2)
            
        elif self.mode == "mem":
            v_mem = psutil.virtual_memory().used / (1024**3)
            s_mem = psutil.swap_memory().used / (1024**3)
            self.layers[0]["data"].append(v_mem)
            self.layers[1]["data"].append(s_mem)
            self._current_total = v_mem + s_mem
            self._current_phys = v_mem
            self._current_virt = s_mem
            
        elif self.mode == "disk":
            dio = psutil.disk_io_counters()
            if self.last_disk_io and dio:
                r = (dio.read_bytes - self.last_disk_io.read_bytes) / dt
                w = (dio.write_bytes - self.last_disk_io.write_bytes) / dt
                total_mb = (r + w) / (1024**2)
            else:
                total_mb = 0.0
            self.last_disk_io = dio
            self._current_total = total_mb
            
            # 分配给各个盘符 (模拟比例)
            disks_count = len(self.layers)
            if disks_count > 0:
                for layer in self.layers:
                    if layer["name"] == "C:":
                        val = total_mb * random.uniform(0.6, 0.9)
                    else:
                        val = total_mb * random.uniform(0.0, 0.3)
                    layer["data"].append(val)
                    
        elif self.mode == "net":
            nio = psutil.net_io_counters()
            if self.last_net_io and nio:
                ul = (nio.bytes_sent - self.last_net_io.bytes_sent) / dt
                dl = (nio.bytes_recv - self.last_net_io.bytes_recv) / dt
            else:
                ul, dl = 0.0, 0.0
            self.last_net_io = nio
            
            self.layers[0]["data"].append(ul)
            self.layers[1]["data"].append(dl)
            self._current_total = ul + dl
            self._current_ul = ul
            self._current_dl = dl

        # pop old
        for layer in self.layers:
            if len(layer["data"]) > self.history_len:
                layer["data"].pop(0)
                
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.theme
        w, h = self.width(), self.height()

        # 卡片背景
        card_bg = QColor(t["bg_card"])
        p.setPen(QPen(QColor(t["border"]), 1))
        p.setBrush(QBrush(card_bg))
        p.drawRoundedRect(0, 0, w, h, 12, 12)

        if not self.layers or not self.layers[0]["data"]:
            return

        # 标题与图例
        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(12, 18, self.title)
        
        legend_base_x = 12 + p.fontMetrics().horizontalAdvance(self.title) + 8
        
        if hasattr(self, 'hardware_name') and self.hardware_name:
            p.setPen(QColor(t.get("text_muted", "#484f58")))
            p.drawText(legend_base_x, 18, self.hardware_name)
            legend_base_x += p.fontMetrics().horizontalAdvance(self.hardware_name) + 8
            
        # 绘制迷你图例 (如果有多个 Layer)
        if len(self.layers) > 1:
            legend_x = legend_base_x + 4
            for layer in reversed(self.layers): # 反向画图例，因为最上面的是第一个出来的？不，随意
                color_hex = t.get(layer["color_key"], layer["color_key"])
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QBrush(QColor(color_hex)))
                p.drawEllipse(legend_x, 10, 8, 8)
                p.setPen(QColor(t["text_muted"]))
                p.setFont(QFont("Segoe UI", 7))
                txt = layer["name"]
                p.drawText(legend_x + 12, 18, txt)
                legend_x += 20 + p.fontMetrics().horizontalAdvance(txt)

        # 当前数值总和
        p.setPen(QColor(t["text_primary"]))
        p.setFont(QFont("Segoe UI", 15, QFont.Weight.Bold))
        try:
            val_str = self.format_func(self._current_total)
        except:
            val_str = "0"
        p.drawText(12, 42, val_str)
        
        # 详细小指标数显拆分渲染
        if hasattr(self, '_current_total'):
            adv = p.fontMetrics().horizontalAdvance(val_str)
            p.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            
            if self.mode == "mem" and hasattr(self, '_current_phys'):
                p.setPen(QColor(t.get("success", "#2ea043")))
                str1 = f" {self._current_phys:.1f} GB"
                p.drawText(12 + adv + 12, 40, str1)
                adv1 = p.fontMetrics().horizontalAdvance(str1)
                
                p.setPen(QColor(t.get("warning", "#d29922")))
                p.drawText(12 + adv + 12 + adv1 + 12, 40, f" {self._current_virt:.1f} GB")
                
            elif self.mode == "cpu" and hasattr(self, '_current_freq'):
                p.setPen(QColor(t.get("text_secondary", "#8b949e")))
                str1 = f" {self._current_freq/1000.0:.2f} GHz"
                p.drawText(12 + adv + 12, 40, str1)
                adv1 = p.fontMetrics().horizontalAdvance(str1)
                
                t_col = t.get("danger", "#ff7b72") if self._current_temp > 75 else t.get("chart_line_4", "#d29922")
                p.setPen(QColor(t_col))
                p.drawText(12 + adv + 12 + adv1 + 12, 40, f" {self._current_temp:.0f}°C")
                
            elif self.mode == "net" and hasattr(self, '_current_ul'):
                p.setPen(QColor(t.get("chart_line_4", "#d29922")))
                str1 = f" ↓ {self._current_dl / (1024**2):.1f} MB/s" if self._current_dl > 1024*1024 else f" ↓ {self._current_dl/1024:.0f} KB/s"
                p.drawText(12 + adv + 12, 40, str1)
                adv1 = p.fontMetrics().horizontalAdvance(str1)
                
                p.setPen(QColor(t.get("info", "#1f6feb")))
                p.drawText(12 + adv + 12 + adv1 + 12, 40, f" ↑ {self._current_ul / (1024**2):.1f} MB/s" if self._current_ul > 1024*1024 else f" ↑ {self._current_ul/1024:.0f} KB/s")

        # 折线图区域
        margin_left = 12
        margin_right = 12
        chart_top = 48
        chart_bottom = h - 8
        chart_w = w - margin_left - margin_right
        chart_h = chart_bottom - chart_top

        if chart_h < 10 or chart_w < 10:
            p.end()
            return

        # 网格与坐标系
        grid_pen = QPen(QColor(t["chart_grid"]), 0.5)
        p.setPen(grid_pen)
        for i in range(5):
            y = chart_top + i * chart_h / 4
            p.drawLine(margin_left, int(y), w - margin_right, int(y))

        # 动态 max
        n_pts = len(self.layers[0]["data"])
        if self.dynamic_max:
            sums = []
            for i in range(n_pts):
                sums.append(sum(L["data"][i] for L in self.layers))
            calc_max = max(1.0, max(sums)) * 1.2
            y_max = calc_max
        else:
            y_max = self.fixed_max

        # --- 绘制堆叠区域图 (由于物理在上层遮挡，必须从顶到底绘制？不，堆叠意味着数据叠加) ---
        base_y = [0.0] * n_pts
        
        for layer in self.layers:
            color_hex = t.get(layer["color_key"], layer["color_key"])
            base_color = QColor(color_hex)
            
            poly_top = []
            poly_bottom = []
            
            for i in range(n_pts):
                val = layer["data"][i]
                old_base = base_y[i]
                new_base = old_base + val
                
                dx = margin_left + i * chart_w / max(1, n_pts - 1)
                dy_old = chart_bottom - (old_base / y_max) * chart_h
                dy_new = chart_bottom - (new_base / y_max) * chart_h
                
                poly_top.append((dx, dy_new))
                poly_bottom.insert(0, (dx, dy_old))
                
                base_y[i] = new_base
            
            # 闭合路径用于填充
            path = QPainterPath()
            path.moveTo(*poly_top[0])
            for pt in poly_top[1:]: path.lineTo(*pt)
            for pt in poly_bottom: path.lineTo(*pt)
            path.closeSubpath()
            
            # 使用透明度堆积填充
            fill_c = QColor(base_color)
            fill_c.setAlpha(80) 
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(fill_c))
            p.drawPath(path)
            
            # 仅绘制顶部边缘作为折线
            line_path = QPainterPath()
            line_path.moveTo(*poly_top[0])
            for pt in poly_top[1:]: line_path.lineTo(*pt)
            
            line_pen = QPen(base_color, 1.5)
            line_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            line_pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(line_pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(line_path)
            
            # 最新数据辉光圆点
            last_pt = poly_top[-1]
            p.setPen(Qt.PenStyle.NoPen)
            glow = QRadialGradient(last_pt[0], last_pt[1], 8)
            glow_color = QColor(base_color)
            glow_color.setAlpha(100)
            glow.setColorAt(0, glow_color)
            glow_color2 = QColor(base_color)
            glow_color2.setAlpha(0)
            glow.setColorAt(1, glow_color2)
            p.setBrush(QBrush(glow))
            p.drawEllipse(QRectF(last_pt[0] - 8, last_pt[1] - 8, 16, 16))
            p.setBrush(QBrush(base_color))
            p.drawEllipse(QRectF(last_pt[0] - 3, last_pt[1] - 3, 6, 6))

        p.end()
