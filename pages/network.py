import time
import psutil
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QSizePolicy, QScroller
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QPoint, QEasingCurve
from PyQt6.QtGui import QFont, QColor

from core.themes import DARK_THEME

class NetWorker(QThread):
    data_ready = pyqtSignal(dict, list) # 网卡速率，连接列表
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused = False
        self.last_io = psutil.net_io_counters(pernic=True)
        self.last_proc_io = {}
        self.last_time = time.time()
        self.proc_cache = {}
        self.proc_obj_cache = {}

    def run(self):
        while self.running:
            if getattr(self, 'paused', False):
                time.sleep(1.0)
                self.last_time = time.time()
                continue
            
            try:
                curr_time = time.time()
                curr_io = psutil.net_io_counters(pernic=True)
                dt = curr_time - self.last_time
                if dt <= 0: dt = 1.0
                
                io_speeds = {}
                for nic, counters in curr_io.items():
                    if nic in self.last_io:
                        sent_speed = (counters.bytes_sent - self.last_io[nic].bytes_sent) / dt
                        recv_speed = (counters.bytes_recv - self.last_io[nic].bytes_recv) / dt
                        if sent_speed > 0 or recv_speed > 0:
                            # 过滤掉几乎不跑流量的虚拟网卡
                            if sent_speed > 100 or recv_speed > 100:
                                io_speeds[nic] = {'sent': sent_speed, 'recv': recv_speed}
                
                self.last_io = curr_io
                self.last_time = curr_time
                
                # 抓取活跃连接列表 (需要 Admin 提权才能扫全系统级)
                conns = psutil.net_connections(kind='inet')
                curr_proc_io = {}
                proc_speeds = {}
                # 预先去重PID，防止同一进程(如Chrome)开启几百个端口导致重复发起几百次底层进程查询，这是巨卡的根源！
                unique_pids = {c.pid for c in conns if c.pid}
                for pid in unique_pids:
                    try:
                        if pid not in self.proc_obj_cache:
                            self.proc_obj_cache[pid] = psutil.Process(pid)
                        pio = self.proc_obj_cache[pid].io_counters()
                        curr_proc_io[pid] = pio
                    except psutil.NoSuchProcess:
                        self.proc_obj_cache.pop(pid, None)
                    except:
                        pass
                        
                for pid, io in curr_proc_io.items():
                    if pid in self.last_proc_io:
                        old_io = self.last_proc_io[pid]
                        recv_s = (io.read_bytes - old_io.read_bytes) / dt
                        sent_s = (io.write_bytes - old_io.write_bytes) / dt
                        proc_speeds[pid] = {'recv': recv_s, 'sent': sent_s}
                    else:
                        proc_speeds[pid] = {'recv': 0.0, 'sent': 0.0}
                        
                self.last_proc_io = curr_proc_io
                
                conn_list = []
                # 过滤大量冗余的 TIME_WAIT 和 CLOSE_WAIT 或者本地环回 127.0.0.1 产生的视觉噪音
                filtered_conns = []
                for c in conns:
                    if not c.laddr: continue
                    if c.status in ('TIME_WAIT', 'CLOSE_WAIT', 'FIN_WAIT1', 'FIN_WAIT2') and not proc_speeds.get(c.pid, {}).get('recv', 0):
                        continue
                    if c.laddr.ip == '127.0.0.1' and getattr(c.raddr, 'ip', '') == '127.0.0.1':
                        if proc_speeds.get(c.pid, {}).get('recv', 0) < 1000:
                            continue # 收发全在本地环回并且没大流量的过滤
                    filtered_conns.append(c)
                
                # 全量提取待合并IO特征
                for c in filtered_conns:
                    laddr = f"{c.laddr.ip}:{c.laddr.port}"
                    raddr = f"{c.raddr.ip}:{c.raddr.port}" if c.raddr else "*:*"
                    pid = c.pid
                    name = "System"
                    
                    if pid:
                        if pid not in self.proc_cache:
                            try:
                                if pid not in self.proc_obj_cache:
                                    self.proc_obj_cache[pid] = psutil.Process(pid)
                                name = self.proc_obj_cache[pid].name()
                                self.proc_cache[pid] = name
                            except:
                                name = "Access Denied"
                        else:
                            name = self.proc_cache[pid]
                    else:
                        name = "System/Unknown"
                    
                    speed = proc_speeds.get(pid, {'recv': 0.0, 'sent': 0.0})
                    
                    conn_list.append({
                        'proto': "TCP" if c.type == 1 else ("UDP" if c.type == 2 else "RAW"),
                        'laddr': laddr,
                        'raddr': raddr,
                        'status': c.status if hasattr(c, 'status') else "NONE",
                        'pid': pid or 0,
                        'name': name,
                        'recv_speed': speed['recv'],
                        'sent_speed': speed['sent']
                    })
                
                # 提取完毕后按总流量大小全局降序排序
                conn_list.sort(key=lambda x: x['recv_speed'] + x['sent_speed'], reverse=True)
                
                # 最后仅抛出首屏和次屏约 150 个占用核心网际资源的连接到表单防卡顿
                self.data_ready.emit(io_speeds, conn_list[:150])
            except Exception as e:
                print(f"NET WORKER ERROR: {str(e)}")
                import traceback
                traceback.print_exc()
            
            time.sleep(1.5)


def get_traffic_style(volume, is_dark, default_bg, default_border):
    if volume < 10 * 1024: return default_bg, default_border
    if volume < 100 * 1024:       c = (90, 40, 150) if is_dark else (210, 180, 240)
    elif volume < 1024 * 1024:    c = (20, 60, 140) if is_dark else (160, 200, 250)
    elif volume < 10 * 1024 * 1024: c = (40, 100, 220) if is_dark else (100, 160, 255)
    elif volume < 100 * 1024 * 1024: c = (20, 160, 180) if is_dark else (120, 220, 230)
    elif volume < 1024 * 1024 * 1024: c = (200, 150, 20) if is_dark else (220, 180, 20)
    else:                         c = (220, 40, 40) if is_dark else (220, 80, 80)
    return f"rgba({c[0]}, {c[1]}, {c[2]}, 0.2)", f"rgb({c[0]}, {c[1]}, {c[2]})"


class TrafficChart(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.points_rx = []
        self.points_tx = []
        self.color_rx = QColor("#3fb950")
        self.color_tx = QColor("#58a6ff")
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def set_data(self, rx_list, tx_list, limit=0):
        if limit > 0:
            rx, tx = list(rx_list), list(tx_list)
            self.points_rx = ([0] * max(0, limit - len(rx))) + rx[-limit:]
            self.points_tx = ([0] * max(0, limit - len(tx))) + tx[-limit:]
        else:
            self.points_rx = rx_list
            self.points_tx = tx_list
        self.update()

    def paintEvent(self, e):
        from PyQt6.QtGui import QPainter, QPen, QPainterPath
        from PyQt6.QtCore import Qt
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        w = self.width()
        h = self.height()
        
        # 预留上下 2 px 避免被截断
        draw_h = h - 4
        if draw_h < 1: return
        
        if not self.points_rx and not self.points_tx: return
        
        max_val = max(max(self.points_rx or [0]), max(self.points_tx or [0]), 1024)
        
        def draw_line(points, color):
            if len(points) < 2: return
            path = QPainterPath()
            step = w / (len(points) - 1)
            for i, val in enumerate(points):
                x = i * step
                y = h - 2 - (val / max_val) * draw_h
                y = max(2, min(h - 2, y))
                if i == 0: path.moveTo(x, y)
                else: path.lineTo(x, y)
            pen = QPen(color, 2)
            pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
            p.setPen(pen)
            p.drawPath(path)
            
        draw_line(self.points_rx, self.color_rx)
        draw_line(self.points_tx, self.color_tx)


class ConnCard(QWidget):
    def __init__(self, theme=None, parent=None):
        super().__init__(parent)
        if theme is None:
            from core.themes import DARK_THEME
            theme = DARK_THEME
        self.theme = theme
        self.setFixedSize(210, 108)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(4)
        
        top_lyt = QHBoxLayout()
        self.lbl_proto = QLabel()
        self.lbl_proto.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_status = QLabel()
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        top_lyt.addWidget(self.lbl_proto)
        top_lyt.addStretch()
        top_lyt.addWidget(self.lbl_status)
        layout.addLayout(top_lyt)
        
        self.lbl_addrs = QLabel()
        self.lbl_addrs.setFont(QFont("Consolas", 8))
        layout.addWidget(self.lbl_addrs)
        
        lyt_speeds = QHBoxLayout()
        self.lbl_speed_rx = QLabel()
        self.lbl_speed_rx.setFont(QFont("Consolas", 8))
        self.lbl_speed_tx = QLabel()
        self.lbl_speed_tx.setFont(QFont("Consolas", 8))
        lyt_speeds.addWidget(self.lbl_speed_rx)
        lyt_speeds.addWidget(self.lbl_speed_tx)
        layout.addLayout(lyt_speeds)
        
        # 底部小图表
        self.chart = TrafficChart()
        layout.addWidget(self.chart, 1)
        
    def update_data(self, conn, current_theme):
        self.theme = current_theme
        self.lbl_proto.setText(conn['proto'])
        status = conn['status']
        self.lbl_status.setText(status if status != 'NONE' else '')
        
        cColor_sec = self.theme.get('text_secondary', '#8b949e')
        cColor_est = self.theme.get('success', '#3fb950')
        cColor_lst = self.theme.get('accent', '#58a6ff')
        cColor_wrn = self.theme.get('warning', '#d29922')
        
        c_color = cColor_sec
        if status == 'ESTABLISHED': c_color = cColor_est
        elif status == 'LISTEN': c_color = cColor_lst
        elif status != 'NONE': c_color = cColor_wrn
        self.lbl_status.setStyleSheet(f"color: {c_color};")
        self.lbl_proto.setStyleSheet(f"color: {cColor_sec};")
        
        raddr = conn['raddr'] if conn['raddr'] != '*:*' else 'ANY'
        self.lbl_addrs.setText(f"{conn['laddr']}\n➜ {raddr}")
        self.lbl_addrs.setStyleSheet(f"color: {self.theme['text_primary']};")
        
        recv = conn['recv_speed']
        sent = conn['sent_speed']
        
        def format_speed(speed):
            if speed >= 1024 * 1024: return f"{speed / (1024**2):.1f} MB/s"
            if speed >= 1024: return f"{speed / 1024:.0f} KB/s"
            return f"{speed:.0f} B/s"
            
        self.lbl_speed_rx.setText(f"↓ {format_speed(recv)}")
        self.lbl_speed_tx.setText(f"↑ {format_speed(sent)}")
        self.lbl_speed_rx.setStyleSheet(f"color: {self.theme.get('success', '#3fb950')};")
        self.lbl_speed_tx.setStyleSheet(f"color: {self.theme.get('accent', '#58a6ff')};")
        
        # 色盘计算
        is_dark = self.theme.get('name', 'dark') == 'dark'
        bg, border = get_traffic_style(conn.get('vol_5s', 0), is_dark, self.theme['bg_card'], self.theme['border'])
        
        self.setStyleSheet(f"""
            ConnCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 6px;
            }}
        """)
        
        rx_pts = conn.get('rx_points', [])
        tx_pts = conn.get('tx_points', [])
        self.chart.set_data(rx_pts, tx_pts, limit=30)


class ProcessNetGroup(QFrame):
    def __init__(self, pid, name, theme=None, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.name = name
        if theme is None:
            from core.themes import DARK_THEME
            theme = DARK_THEME
        self.theme = theme
        self.cards = []
        
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        info_vbox = QVBoxLayout()
        self.lbl_name = QLabel(f"{name}")
        self.lbl_name.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.lbl_name.setStyleSheet(f"color: {self.theme['text_primary']};")
        
        self.lbl_pid = QLabel(f"PID: {pid}")
        self.lbl_pid.setFont(QFont("Segoe UI", 9))
        self.lbl_pid.setStyleSheet(f"color: {self.theme['text_secondary']};")
        
        self.lbl_total_speed = QLabel()
        self.lbl_total_speed.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_total_speed.setStyleSheet(f"color: {self.theme.get('accent', '#58a6ff')};")
        
        self.chart = TrafficChart()
        self.chart.setFixedHeight(30)
        
        info_vbox.addWidget(self.lbl_name)
        info_vbox.addWidget(self.lbl_pid)
        info_vbox.addWidget(self.lbl_total_speed)
        info_vbox.addWidget(self.chart)
        info_vbox.addStretch()
        
        info_widget = QWidget()
        info_widget.setLayout(info_vbox)
        info_widget.setFixedWidth(160)
        layout.addWidget(info_widget)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.cards_container)
        self.scroll.setFixedHeight(116)
        
        layout.addWidget(self.scroll)
        
    def update_connections(self, group, current_theme):
        self.theme = current_theme
        conns = group['conns']
        total_recv = sum(c['recv_speed'] for c in conns)
        total_sent = sum(c['sent_speed'] for c in conns)
        
        def format_speed(speed):
            if speed >= 1024 * 1024: return f"{speed / (1024**2):.1f} MB/s"
            if speed >= 1024: return f"{speed / 1024:.0f} KB/s"
            return f"{speed:.0f} B/s"
            
        if total_recv > 50 or total_sent > 50:
            self.lbl_total_speed.setText(f"↓ {format_speed(total_recv)}\n↑ {format_speed(total_sent)}")
        else:
            self.lbl_total_speed.setText("")
            
        is_dark = self.theme.get('name', 'dark') == 'dark'
        vol_120s = group.get('vol_120s', 0)
        bg, border = get_traffic_style(vol_120s, is_dark, self.theme['bg_tertiary'], self.theme['border'])
        
        self.setStyleSheet(f"""
            ProcessNetGroup {{
                background-color: {bg};
                border: 1px solid {border};
                border-radius: 8px;
            }}
        """)
        
        self.chart.set_data(group.get('rx_points', []), group.get('tx_points', []), limit=60)
        
        while len(self.cards) < len(conns):
            card = ConnCard(self.theme)
            self.cards.append(card)
            self.cards_layout.addWidget(card)
            
        for i, card in enumerate(self.cards):
            if i < len(conns):
                card.show()
                card.update_data(conns[i], self.theme)
            else:
                card.hide()
        
        self.cards_container.setMinimumWidth(len(conns) * 218)

class NetworkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.themes import DARK_THEME
        self.theme = DARK_THEME
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel("网络监控")
        self.lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.subtitle = QLabel("全量接口流转及活体连接监听")
        self.subtitle.setFont(QFont("Segoe UI", 11))
        
        title_vbox = QVBoxLayout()
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.subtitle)
        top_layout.addLayout(title_vbox)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        self.io_lbl = QLabel("正在收集底层网卡拓扑与信标汇率...")
        self.io_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.io_lbl)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        QScroller.grabGesture(self.scroll.viewport(), QScroller.ScrollerGestureType.LeftMouseButtonGesture)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.groups_container = QWidget()
        self.groups_container.setStyleSheet("background: transparent;")
        self.scroll.setWidget(self.groups_container)
        layout.addWidget(self.scroll)
        
        self.process_groups = {}
        self.group_animations = {}
        self.speed_history = {}
        self.conn_history = {}
        self.sorted_pids = []
        self.last_sort_time = 0
        
        self.worker = NetWorker()
        self.worker.data_ready.connect(self.update_data)
        self.worker.start()
        
        self._apply_theme_to_widgets()
        
    def get_anim_targets(self):
        return [self.lbl_title, self.subtitle, self.io_lbl, self.scroll]

    def set_module_enabled(self, enabled: bool):
        self.worker.paused = not enabled

    def apply_theme(self, theme):
        self.theme = theme
        self._apply_theme_to_widgets()
        for pg in self.process_groups.values():
            pg.lbl_name.setStyleSheet(f"color: {theme['text_primary']};")
            pg.lbl_pid.setStyleSheet(f"color: {theme['text_secondary']};")
            pg.lbl_total_speed.setStyleSheet(f"color: {theme.get('accent', '#58a6ff')};")
            for card in pg.cards:
                card.lbl_addrs.setStyleSheet(f"color: {theme['text_primary']};")
        
    def _apply_theme_to_widgets(self):
        self.lbl_title.setStyleSheet(f"color: {self.theme['text_primary']};")
        self.subtitle.setStyleSheet(f"color: {self.theme['text_secondary']};")
        self.io_lbl.setStyleSheet(f"color: {self.theme.get('accent', '#58a6ff')};")
        self.scroll.verticalScrollBar().setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0px 0px 0px 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {self.theme['border']};
                min-height: 20px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {self.theme.get('text_muted', '#8b949e')};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)
        
    def format_speed(self, speed):
        if speed >= 1024 * 1024 * 1024:
            return f"{speed / (1024**3):.1f} GB/s"
        elif speed >= 1024 * 1024:
            return f"{speed / (1024**2):.1f} MB/s"
        elif speed >= 1024:
            return f"{speed / 1024:.0f} KB/s"
        return f"{speed:.0f} B/s"
        
    def update_data(self, io_speeds, conns):
        io_texts = []
        for nic, speeds in io_speeds.items():
            if speeds['recv'] > 50 or speeds['sent'] > 50:
                io_texts.append(f"📡 {nic}: [↓ {self.format_speed(speeds['recv'])} | ↑ {self.format_speed(speeds['sent'])}]")
        
        self.io_lbl.setText("  ".join(io_texts) if io_texts else "无可测量的网际网络活动 / 未检索到数据流交换")
        
        groups = {}
        for c in conns:
            pid = c['pid']
            if pid not in groups:
                groups[pid] = {'name': c['name'], 'conns': []}
            groups[pid]['conns'].append(c)
            
        current_time = time.time()
        
        # 处理连接的 5 秒均值
        active_cids = set()
        for pid, group in groups.items():
            for c in group['conns']:
                cid = (pid, c['laddr'], c['raddr'])
                active_cids.add(cid)
                if cid not in self.conn_history: self.conn_history[cid] = []
                # 记录 (time, rx, tx)
                self.conn_history[cid].append((current_time, c['recv_speed'], c['sent_speed']))
                self.conn_history[cid] = [x for x in self.conn_history[cid] if current_time - x[0] <= 5.0]
                
                vol = sum((x[1] + x[2]) * 1.5 for x in self.conn_history[cid])
                c['vol_5s'] = vol
                c['rx_points'] = [x[1] for x in self.conn_history[cid]]
                c['tx_points'] = [x[2] for x in self.conn_history[cid]]
                
        # 清理 5 秒之前的僵尸连接历史
        for cid in list(self.conn_history.keys()):
            if cid not in active_cids:
                # 给它 5 秒保留时间
                self.conn_history[cid] = [x for x in self.conn_history[cid] if current_time - x[0] <= 5.0]
                if not self.conn_history[cid]:
                    del self.conn_history[cid]
        
        # 处理进程的 120 秒均值
        for pid, group in groups.items():
            total_rx = sum(c['recv_speed'] for c in group['conns'])
            total_tx = sum(c['sent_speed'] for c in group['conns'])
            total_speed = total_rx + total_tx
            
            if pid not in self.speed_history:
                self.speed_history[pid] = []
            self.speed_history[pid].append((current_time, total_rx, total_tx))
            
            # 120秒 -> 获取所有符合历史的
            self.speed_history[pid] = [x for x in self.speed_history[pid] if current_time - x[0] <= 120.0]
            
            # 由于可能出现卡顿导致记录点不够，我们按照时长乘积计算预估总量
            vol = sum((x[1]+x[2])*1.5 for x in self.speed_history[pid])
            group['vol_120s'] = vol
            
            # 我们按照当前10秒滑动平均来进行动态排序
            recent_10s = [x for x in self.speed_history[pid] if current_time - x[0] <= 10.0]
            avg_sort = sum(x[1]+x[2] for x in recent_10s) / max(1, len(recent_10s))
            group['avg_speed'] = avg_sort
            
            # 用于折线图
            group['rx_points'] = [x[1] for x in self.speed_history[pid]]
            group['tx_points'] = [x[2] for x in self.speed_history[pid]]
            
        if getattr(self, 'last_sort_time', 0) == 0 or current_time - self.last_sort_time >= 2.0:
            self.sorted_pids = sorted(groups.keys(), key=lambda p: groups[p]['avg_speed'], reverse=True)
            self.last_sort_time = current_time
            
        for pid in groups.keys():
            if pid not in self.sorted_pids:
                self.sorted_pids.append(pid)
                
        self.sorted_pids = [pid for pid in self.sorted_pids if pid in groups]

        # 更新内容
        for pid in self.sorted_pids:
            if pid not in self.process_groups:
                pg = ProcessNetGroup(pid, groups[pid]['name'], self.theme, parent=self.groups_container)
                pg.show()
                self.process_groups[pid] = pg
            self.process_groups[pid].update_connections(groups[pid], self.theme)

        active_pids = set(self.sorted_pids)
        for pid, pg in list(self.process_groups.items()):
            if pid not in active_pids:
                pg.hide()
                pg.deleteLater()
                if pid in self.group_animations:
                    self.group_animations[pid].stop()
                    del self.group_animations[pid]
                del self.process_groups[pid]
                if pid in self.speed_history:
                    del self.speed_history[pid]

        y = 0
        spacing = 12
        item_w = self.scroll.viewport().width() - 8
        if item_w < 100: item_w = 100
        
        for pid in self.sorted_pids:
            pg = self.process_groups[pid]
            # Height of group: increase to 160 to prevent text clipping
            item_h = 160
            
            if pg.width() != item_w or pg.height() != item_h:
                pg.resize(item_w, item_h)
            
            target_pos = QPoint(0, y)
            
            if pg.pos() != target_pos:
                if pid not in self.group_animations:
                    if pg.pos() == QPoint(0, 0) and y > 0:
                        pg.move(target_pos)
                    else:
                        anim = QPropertyAnimation(pg, b"pos", self)
                        anim.setDuration(450)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                        anim.setEndValue(target_pos)
                        self.group_animations[pid] = anim
                        anim.start()
                else:
                    anim = self.group_animations[pid]
                    if anim.endValue() != target_pos:
                        anim.stop()
                        anim.setEndValue(target_pos)
                        anim.start()
                    
            y += item_h + spacing
            
        self.groups_container.setMinimumHeight(y)
        
    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.scroll.viewport().width() - 8
        if w > 0:
            for pg in self.process_groups.values():
                pg.resize(w, pg.height())
