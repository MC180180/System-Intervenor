import codecs

path = r"c:\Users\Administrator\Desktop\系统干预器\pages\network.py"
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

idx1 = content.find("class ConnCard(QWidget):")

if idx1 == -1:
    print("Cannot find ConnCard.")
    import sys; sys.exit(1)

new_code = '''def get_traffic_style(volume, is_dark, default_bg, default_border):
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

    def set_data(self, rx_list, tx_list):
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
        self.lbl_addrs.setText(f"{conn['laddr']}\\n➜ {raddr}")
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
        self.chart.set_data(rx_pts, tx_pts)


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
            self.lbl_total_speed.setText(f"↓ {format_speed(total_recv)}\\n↑ {format_speed(total_sent)}")
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
        
        self.chart.set_data(group.get('rx_points', []), group.get('tx_points', []))
        
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
        self.subtitle = QLabel("全量接口流转及活体连接监听 (流量图谱版)")
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
            # Height of group: fixed 140 is typical because card is 108 + layout margins
            # But let's let sizeHint do partially, or fix it to 140
            item_h = 140
            
            if pg.width() != item_w:
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
'''

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content[:idx1] + new_code)
print("done")
