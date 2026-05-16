import sys
import codecs

path = r"c:\Users\Administrator\Desktop\系统干预器\pages\network.py"
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# Replace Imports
content = content.replace(
    '''from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QAbstractItemView
)''',
    '''from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame, QSizePolicy
)'''
)

idx = content.find("class NetworkPage(QWidget):")
if idx == -1:
    print("Failed!")
    sys.exit(1)

new_code = '''class ConnCard(QWidget):
    def __init__(self, theme=None, parent=None):
        super().__init__(parent)
        if theme is None:
            from core.themes import DARK_THEME
            theme = DARK_THEME
        self.theme = theme
        self.setFixedSize(180, 80)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 6, 8, 8)
        layout.setSpacing(4)
        
        # 协议 和 状态
        top_lyt = QHBoxLayout()
        self.lbl_proto = QLabel()
        self.lbl_proto.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        self.lbl_status = QLabel()
        self.lbl_status.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        top_lyt.addWidget(self.lbl_proto)
        top_lyt.addStretch()
        top_lyt.addWidget(self.lbl_status)
        layout.addLayout(top_lyt)
        
        # 本地 -> 远程
        self.lbl_addrs = QLabel()
        self.lbl_addrs.setFont(QFont("Consolas", 8))
        layout.addWidget(self.lbl_addrs)
        
        # 速率
        self.lbl_speed = QLabel()
        self.lbl_speed.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
        layout.addWidget(self.lbl_speed)
        
    def update_data(self, conn):
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
            
        self.lbl_speed.setText(f"↓ {format_speed(recv)}  ↑ {format_speed(sent)}")
        
        self.setStyleSheet(f"""
            ConnCard {{
                background-color: {self.theme['bg_card']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
            }}
        """)


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
        self.setStyleSheet(f"""
            ProcessNetGroup {{
                background-color: {self.theme['bg_tertiary']};
                border: 1px solid {self.theme['border']};
                border-radius: 8px;
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)
        
        # 左侧进程信息
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
        
        info_vbox.addWidget(self.lbl_name)
        info_vbox.addWidget(self.lbl_pid)
        info_vbox.addWidget(self.lbl_total_speed)
        info_vbox.addStretch()
        
        info_widget = QWidget()
        info_widget.setLayout(info_vbox)
        info_widget.setFixedWidth(140)
        layout.addWidget(info_widget)
        
        # 右侧连接卡片水平滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        # 隐藏水平滚动条，但开启可滚动支持
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QHBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.cards_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.cards_container)
        self.scroll.setFixedHeight(84)
        
        layout.addWidget(self.scroll)
        
    def update_connections(self, conns):
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
            
        # 复用卡片
        while len(self.cards) < len(conns):
            card = ConnCard(self.theme)
            self.cards.append(card)
            self.cards_layout.addWidget(card)
            
        for i, card in enumerate(self.cards):
            if i < len(conns):
                card.show()
                card.update_data(conns[i])
            else:
                card.hide()
        
        # 手动修正容器宽度避免遮挡
        self.cards_container.setMinimumWidth(len(conns) * 188)

class NetworkPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        from core.themes import DARK_THEME
        self.theme = DARK_THEME
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # 头部
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel("网络监控")
        self.lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.subtitle = QLabel("全量接口流转及活体连接监听 (卡片流态)")
        self.subtitle.setFont(QFont("Segoe UI", 11))
        
        title_vbox = QVBoxLayout()
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.subtitle)
        top_layout.addLayout(title_vbox)
        top_layout.addStretch()
        layout.addLayout(top_layout)
        
        # IO速率横幅
        self.io_lbl = QLabel("正在收集底层网卡拓扑与信标汇率...")
        self.io_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.io_lbl)
        
        # 垂直滚动卡片区
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.groups_container = QWidget()
        self.groups_container.setStyleSheet("background: transparent;")
        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.setSpacing(12)
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.groups_container)
        layout.addWidget(self.scroll)
        
        self.process_groups = {}
        
        self.worker = NetWorker()
        self.worker.data_ready.connect(self.update_data)
        self.worker.start()
        
        self._apply_theme_to_widgets()
        
    def apply_theme(self, theme):
        self.theme = theme
        self._apply_theme_to_widgets()
        for pg in self.process_groups.values():
            pg.theme = theme
            pg.setStyleSheet(f"""
                ProcessNetGroup {{
                    background-color: {pg.theme['bg_tertiary']};
                    border: 1px solid {pg.theme['border']};
                    border-radius: 8px;
                }}
            """)
            pg.lbl_name.setStyleSheet(f"color: {theme['text_primary']};")
            pg.lbl_pid.setStyleSheet(f"color: {theme['text_secondary']};")
            pg.lbl_total_speed.setStyleSheet(f"color: {theme.get('accent', '#58a6ff')};")
            for card in pg.cards:
                card.theme = theme
                card.setStyleSheet(f"""
                    ConnCard {{
                        background-color: {theme['bg_card']};
                        border: 1px solid {theme['border']};
                        border-radius: 6px;
                    }}
                """)
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
            
        active_pids = set(groups.keys())
        for pid, group_widget in list(self.process_groups.items()):
            if pid not in active_pids:
                self.groups_layout.removeWidget(group_widget)
                group_widget.deleteLater()
                del self.process_groups[pid]
                
        for pid, group in groups.items():
            total_speed = sum(c['recv_speed'] + c['sent_speed'] for c in group['conns'])
            group['total_speed'] = total_speed
            
        sorted_pids = sorted(groups.keys(), key=lambda p: groups[p]['total_speed'], reverse=True)
        
        sorted_widgets = []
        for pid in sorted_pids:
            if pid not in self.process_groups:
                pg = ProcessNetGroup(pid, groups[pid]['name'], self.theme)
                self.process_groups[pid] = pg
            sorted_widgets.append(self.process_groups[pid])
            self.process_groups[pid].update_connections(groups[pid]['conns'])
            
        current_count = self.groups_layout.count()
        current_widgets = [self.groups_layout.itemAt(i).widget() for i in range(current_count) if self.groups_layout.itemAt(i).widget()]
        
        if sorted_widgets != current_widgets:
            # Reorder silently
            for i in reversed(range(current_count)):
                item = self.groups_layout.takeAt(i)
            # Re-insert in correct order
            for w in sorted_widgets:
                self.groups_layout.addWidget(w)
'''

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content[:idx] + new_code)
print("OK")
