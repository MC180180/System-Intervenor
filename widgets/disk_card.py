import math
import random
import time
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


class DiskDetailCard(QWidget):
    """磁盘详细信息大卡片，包含多磁盘网格、读写图表与底层响应指标"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.icon_key = "disk"
        self.title = "磁盘 I/O"
        self.accent_color = "#3fb950"  # 绿色主题
        
        self.setMinimumWidth(280)
        self.setMinimumHeight(350)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.theme = DARK_THEME
        self._hover = False

        self.history_len = 48
        self.disks = []        # 存放每个盘符的静态属性
        self.disk_stats = {}   # 存放动态状态
        
        self.last_io = None
        self.last_time = time.time()
        
        self.total_read_speed = 0.0
        self.total_write_speed = 0.0

        self._init_disks()

        # 定时器刷新数据
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._update_data)
        
        from widgets.refresh_slider import RefreshRateSlider
        self._rate_slider = RefreshRateSlider("disk", self._on_rate_changed, self)
        self._timer.start(self._rate_slider.get_interval_ms())
        self._update_data()
    
    def _on_rate_changed(self, interval_ms):
        self._timer.setInterval(interval_ms)
        
    def _get_logical_io(self):
        """直接通过 WIndows 底层内核接口查询单个逻辑分区的精确 IO"""
        import ctypes
        from ctypes import wintypes
        
        class DISK_PERFORMANCE(ctypes.Structure):
            _fields_ = [
                ('BytesRead', ctypes.c_int64),
                ('BytesWritten', ctypes.c_int64),
                ('ReadTime', ctypes.c_int64),
                ('WriteTime', ctypes.c_int64),
                ('IdleTime', ctypes.c_int64),
                ('ReadCount', ctypes.c_uint32),
                ('WriteCount', ctypes.c_uint32),
                ('QueueDepth', ctypes.c_uint32),
                ('SplitCount', ctypes.c_uint32),
                ('QueryTime', ctypes.c_int64),
                ('StorageDeviceNumber', ctypes.c_uint32),
                ('StorageManagerName', ctypes.c_wchar * 8)
            ]
            
        k32 = ctypes.windll.kernel32
        res = {}
        for disk in self.disks:
            letter = disk["letter"]
            path = f'\\\\.\\{letter}'
            # INVALID_HANDLE_VALUE 是 -1 (或 4294967295)
            h = k32.CreateFileW(path, 0, 7, None, 3, 0, None)
            if h != -1 and h != 4294967295:
                perf = DISK_PERFORMANCE()
                ret = wintypes.DWORD()
                ok = k32.DeviceIoControl(h, 0x70020, None, 0, ctypes.byref(perf), ctypes.sizeof(perf), ctypes.byref(ret), None)
                if ok:
                    res[letter] = {
                        "read_bytes": perf.BytesRead,
                        "write_bytes": perf.BytesWritten,
                        "read_time": perf.ReadTime // 10000,  # 100ns -> ms
                        "write_time": perf.WriteTime // 10000 # 100ns -> ms
                    }
                k32.CloseHandle(h)
        return res

    def _init_disks(self):
        """初始化磁盘列表和静态信息"""
        import ctypes
        partitions = psutil.disk_partitions(all=False)
        
        for p in partitions:
            if 'cdrom' in p.opts or p.fstype == '':
                continue
                
            drive_letter = p.device.replace('\\', '')
            
            vol_name = ""
            try:
                buf = ctypes.create_unicode_buffer(1024)
                if ctypes.windll.kernel32.GetVolumeInformationW(
                    ctypes.c_wchar_p(drive_letter + "\\"), buf, ctypes.sizeof(buf), None, None, None, None, 0):
                    vol_name = buf.value
            except Exception:
                pass

            label_str = f"{drive_letter} {vol_name}".strip()
            
            try:
                usage = psutil.disk_usage(p.mountpoint)
                total_gb = usage.total / (1024**3)
            except:
                total_gb = 0
                
            self.disks.append({
                "mount": p.mountpoint,
                "letter": drive_letter,
                "label": label_str,
                "total_gb": total_gb,
            })
            
            self.disk_stats[drive_letter] = {
                "read_speed": 0.0,
                "write_speed": 0.0,
                "read_history": [0.0] * self.history_len,
                "write_history": [0.0] * self.history_len,
                "active_time": 0.0,
                "resp_time": 0.0,
                "last_read_bytes": 0,
                "last_write_bytes": 0,
                "last_read_time": 0,
                "last_write_time": 0,
                "initialized": False,
            }
        
        # 初始化基线 IO 计数器
        logical_ios = self._get_logical_io()
        for letter, io_data in logical_ios.items():
            if letter in self.disk_stats:
                st = self.disk_stats[letter]
                st["last_read_bytes"] = io_data["read_bytes"]
                st["last_write_bytes"] = io_data["write_bytes"]
                st["last_read_time"] = io_data["read_time"]
                st["last_write_time"] = io_data["write_time"]
                st["initialized"] = True
    
    def _update_data(self):
        current_time = time.time()
        dt = current_time - self.last_time
        if dt <= 0:
            dt = 1.0
            
        self.last_time = current_time
        
        try:
            counters = psutil.disk_io_counters(perdisk=True)
            total_io = psutil.disk_io_counters(perdisk=False)
        except:
            self.update()
            return
            
        # 更新全局速度
        if self.last_io and total_io:
            self.total_read_speed = (total_io.read_bytes - self.last_io.read_bytes) / dt
            self.total_write_speed = (total_io.write_bytes - self.last_io.write_bytes) / dt
        self.last_io = total_io
        
        self._adjust_min_height()

        # 调用底层精确计算每一个分区的IO
        logical_ios = self._get_logical_io()

        for disk in self.disks:
            letter = disk["letter"]
            stats = self.disk_stats[letter]
            
            matched = logical_ios.get(letter)
            
            if matched and stats["initialized"]:
                read_delta = max(0, matched["read_bytes"] - stats["last_read_bytes"])
                write_delta = max(0, matched["write_bytes"] - stats["last_write_bytes"])
                
                r_speed_mb = (read_delta / dt) / (1024 * 1024)
                w_speed_mb = (write_delta / dt) / (1024 * 1024)
                
                stats["read_speed"] = r_speed_mb
                stats["write_speed"] = w_speed_mb
                
                # 响应时间 (基于 IO 时间差分)
                rt_delta = max(0, matched["read_time"] - stats["last_read_time"])
                wt_delta = max(0, matched["write_time"] - stats["last_write_time"])
                io_count = max(1, (read_delta + write_delta) / (4096))  # 粗略估算IO次数
                stats["resp_time"] = (rt_delta + wt_delta) / io_count if (rt_delta + wt_delta) > 0 else 0.0
                stats["active_time"] = min(100.0, (r_speed_mb + w_speed_mb) * 2.0)
                
                stats["last_read_bytes"] = matched["read_bytes"]
                stats["last_write_bytes"] = matched["write_bytes"]
                stats["last_read_time"] = matched["read_time"]
                stats["last_write_time"] = matched["write_time"]
            else:
                stats["read_speed"] = 0.0
                stats["write_speed"] = 0.0
                if matched:
                    stats["last_read_bytes"] = matched["read_bytes"]
                    stats["last_write_bytes"] = matched["write_bytes"]
                    stats["last_read_time"] = matched["read_time"]
                    stats["last_write_time"] = matched["write_time"]
                    stats["initialized"] = True
            
            stats["read_history"].append(stats["read_speed"])
            stats["write_history"].append(stats["write_speed"])
            if len(stats["read_history"]) > self.history_len:
                stats["read_history"].pop(0)
                stats["write_history"].pop(0)

        # DEBUG: 打印物理映射和瞬时速度，方便排查数据一样的问题
        if getattr(self, "_debug_ticker", 0) <= 0:
            print(f"--- 磁盘 I/O 雷达扫描 (dt={dt:.2f}) ---")
            for disk in self.disks:
                l = disk['letter']
                st = self.disk_stats[l]
                print(f"[{l}] -> 读取: {st['read_speed']:>6.1f} MB/s | 写入: {st['write_speed']:>6.1f} MB/s")
            self._debug_ticker = 3  # 每 3 秒打印一次防止刷屏
        else:
            self._debug_ticker -= 1

        self.update()

    def enterEvent(self, e):
        self._hover = True
        self.update()

    def leaveEvent(self, e):
        self._hover = False
        self.update()

    def _adjust_min_height(self):
        w = self.width()
        margin = 12
        avail_w = w - margin * 2
        num_disks = len(self.disks)
        if num_disks > 0 and avail_w > 0:
            cols = max(1, int(avail_w // 150))
            if cols > num_disks: cols = num_disks
            rows = math.ceil(num_disks / cols)
            
            # 解除过度的防压扁限制，允许方块变扁以确保主布局比例（如2:2）生效
            min_box_h = 45
            spacing = 8
            
            req_h = 85 + rows * (min_box_h + spacing) + 12 # top_offset + ... + bottom
            
            # 使用精准的 max 函数允许其回缩，而不是只增不长
            self.setMinimumHeight(int(max(350, req_h)))
                
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._adjust_min_height()
        self._rate_slider.move(self.width() - self._rate_slider.width() - 8, 40)

    def _format_speed(self, bytes_per_sec):
        # bytes -> MB or KB
        if bytes_per_sec > 1024 * 1024:
            return f"{bytes_per_sec / (1024*1024):.1f} MB/s"
        else:
            return f"{bytes_per_sec / 1024:.0f} KB/s"

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

        # 头部
        icon_pixmap = create_svg_icon(SVG_ICONS.get(self.icon_key, ""), 16, self.accent_color)
        draw_icon(p, 12, 16, icon_pixmap, 16)

        p.setPen(QColor(t["text_secondary"]))
        p.setFont(QFont("Segoe UI", 8))
        p.drawText(36, 28, self.title)

        # 总体 I/O (读写最高者)
        top_speed = max(self.total_read_speed, self.total_write_speed)
        p.setPen(QColor(t["text_primary"]))
        p.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        p.drawText(12, 58, self._format_speed(top_speed))

        p.setPen(QColor(t["text_muted"]))
        p.setFont(QFont("Segoe UI", 7))
        subtitle_text = "总计 读取 / 写入速率"
        p.drawText(12, 74, subtitle_text)

        # --- 绘制磁盘网格 ---
        margin = 12
        top_offset = 85
        bottom_padding = 12
        avail_w = w - margin * 2
        avail_h = h - top_offset - bottom_padding

        num_disks = len(self.disks)
        if avail_h > 40 and num_disks > 0:
            # 动态决定列数：希望每个盘的方块宽度至少保持在 150px
            cols = max(1, int(avail_w // 150))
            if cols > num_disks:
                cols = num_disks
            
            rows = math.ceil(num_disks / cols)
            
            spacing = 8
            box_w = (avail_w - spacing * (cols - 1)) / cols
            box_h = (avail_h - spacing * (rows - 1)) / rows
            
            # 安全阈值：如果过扁则按极简模式绘制
            is_compact = box_h < 90
            
            for i, disk in enumerate(self.disks):
                r = i // cols
                c = i % cols
                x = margin + c * (box_w + spacing)
                y = top_offset + r * (box_h + spacing)
                
                stats = self.disk_stats[disk["letter"]]
                
                base_color_str = self.accent_color
                b_color = QColor(base_color_str)
                
                # --- 对数亮度随动映射: 0MB→0, 10MB→0.33, 100MB→0.66, 1000MB→1.0 ---
                cur_r = stats["read_speed"]
                cur_w = stats["write_speed"]
                total_mb = cur_r + cur_w
                import math as _math
                if total_mb <= 0.01:
                    intensity = 0.0
                else:
                    # log10(0.01)=-2, log10(10)=1, log10(100)=2, log10(1000)=3
                    intensity = max(0.0, min(1.0, (_math.log10(total_mb) + 2.0) / 5.0))
                
                # 底框光辉
                rect = QRectF(x, y, box_w, box_h)
                
                # 从主题色到白色的渐变
                # 适配浅色模式，如果是浅色模式，则向深黑沉淀
                is_light_mode = QColor(self.theme["bg_card"]).lightness() > 127
                target_rgb = 0 if is_light_mode else 255
                
                base_c = QColor(self.accent_color)
                color_intensity = intensity * 0.95
                r_c = base_c.red() + int((target_rgb - base_c.red()) * color_intensity)
                g_c = base_c.green() + int((target_rgb - base_c.green()) * color_intensity)
                b_c = base_c.blue() + int((target_rgb - base_c.blue()) * color_intensity)
                
                bg_color = QColor(r_c, g_c, b_c, int(8 + 60 * intensity))
                border_color = QColor(r_c, g_c, b_c, int(40 + 160 * intensity))
                
                p.setPen(QPen(border_color, 1))
                p.setBrush(bg_color)
                p.drawRoundedRect(rect, 6, 6)
                
                # 文字亮度也随 intensity 渐变
                text_color = QColor(r_c, g_c, b_c, int(180 + 75 * intensity))
                
                # 防止超长卷标覆盖容量文字 (省略号截断)
                cap_str = f"{int(disk['total_gb'])} GB"
                cap_font = QFont("Segoe UI", 8)
                p.setFont(cap_font)
                cap_w = p.fontMetrics().horizontalAdvance(cap_str)
                
                font_title = QFont("Segoe UI", 10, QFont.Weight.Bold)
                p.setFont(font_title)
                fm = p.fontMetrics()
                
                avail_title_w = box_w - 20 - 40 - 10 # 预留点空间
                elided_label = fm.elidedText(disk["label"], Qt.TextElideMode.ElideRight, int(max(20, avail_title_w)))
                
                # 小标题: 盘符与裁切后的名称
                p.setPen(text_color)
                p.drawText(QRectF(x + 10, y + 8, avail_title_w, 20), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, elided_label)
                
                p.setFont(cap_font)
                cap_color = QColor(b_color)
                cap_color.setAlpha(int(100 + 50 * intensity)) # 容量略暗
                p.setPen(cap_color)
                p.drawText(QRectF(x + 10, y + 8, box_w - 20, 20), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, cap_str)
                
                # 画微型读写双折线图
                top_h = 30
                bottom_h = 18 if is_compact else 55
                
                chart_y = y + top_h
                chart_h = max(10, box_h - top_h - bottom_h)
                
                if chart_h >= 10:
                    pts_count = self.history_len
                    max_val_r = max(1.0, max(stats["read_history"]))
                    max_val_w = max(1.0, max(stats["write_history"]))
                    global_max = max(max_val_r, max_val_w) * 1.2
                    
                    r_path = QPainterPath()
                    w_path = QPainterPath()
                    for pt_idx in range(pts_count):
                        pt_x = x + 10 + (pt_idx / max(1, pts_count - 1)) * (box_w - 20)
                        
                        ry = chart_y + chart_h - (stats["read_history"][pt_idx] / global_max) * chart_h
                        wy = chart_y + chart_h - (stats["write_history"][pt_idx] / global_max) * chart_h
                        
                        if pt_idx == 0:
                            r_path.moveTo(pt_x, ry)
                            w_path.moveTo(pt_x, wy)
                        else:
                            r_path.lineTo(pt_x, ry)
                            w_path.lineTo(pt_x, wy)
                            
                    r_color = QColor(t["info"])
                    p.setPen(QPen(r_color, 1.5))
                    p.drawPath(r_path)
                    
                    w_color = QColor(b_color)
                    p.setPen(QPen(w_color, 1.5))
                    p.drawPath(w_path)
                
                # 最底部的当前读写速度 (图表下沿)
                speed_y = y + box_h - bottom_h
                p.setFont(QFont("Segoe UI", 8))
                speed_str = f"读: {cur_r:.1f} M | 写: {cur_w:.1f} M"
                p.setPen(text_color)
                p.drawText(QRectF(x + 10, speed_y + 2, box_w - 20, 15), Qt.AlignmentFlag.AlignRight, speed_str)
                
                # 底部指标信息 (接口类型 / 延迟 / 活动) - 压缩模式下隐藏
                if not is_compact:
                    bot_y = speed_y + 20
                    p.setFont(QFont("Segoe UI", 7))
                    
                    col_w = (box_w - 20) / 2
                    
                    p.setPen(QColor(t["text_muted"]))
                    p.drawText(QRectF(x + 10, bot_y, col_w, 15), Qt.AlignmentFlag.AlignLeft, "响应")
                    p.drawText(QRectF(x + 10 + col_w, bot_y, col_w, 15), Qt.AlignmentFlag.AlignLeft, "活动")
                    
                    bot_val_y = bot_y + 15
                    p.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
                    
                    if stats["resp_time"] > 20:
                        p.setPen(QColor(t["danger"]))
                    elif stats["resp_time"] > 5:
                        p.setPen(QColor(t["warning"]))
                    else:
                        p.setPen(QColor(t["text_primary"]))
                        
                    p.drawText(QRectF(x + 10, bot_val_y, col_w, 15), Qt.AlignmentFlag.AlignLeft, f"{stats['resp_time']:.1f}ms")
                    
                    p.setPen(QColor(t["text_primary"]))
                    p.drawText(QRectF(x + 10 + col_w, bot_val_y, col_w, 15), Qt.AlignmentFlag.AlignLeft, f"{stats['active_time']:.0f}%")

        p.end()
