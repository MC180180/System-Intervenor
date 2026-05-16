import codecs

path = r"c:\Users\Administrator\Desktop\系统干预器\pages\network.py"
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

idx1 = content.find("class ConnCard(QWidget):")
idx2 = content.find("class NetworkPage(QWidget):")

if idx1 == -1 or idx2 == -1:
    print("Cannot find points.")
    import sys; sys.exit(1)

new_code = '''class ConnCard(QWidget):
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
        self.lbl_speed_rx = QLabel()
        self.lbl_speed_rx.setFont(QFont("Consolas", 8))
        self.lbl_speed_tx = QLabel()
        self.lbl_speed_tx.setFont(QFont("Consolas", 8))
        layout.addWidget(self.lbl_speed_rx)
        layout.addWidget(self.lbl_speed_tx)
        
        layout.addStretch()
        
    def update_data(self, conn, max_recv, max_sent):
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
            if speed >= 1024 * 1024: return f"{speed / (1024**2):5.1f} MB/s"
            if speed >= 1024: return f"{speed / 1024:5.0f} KB/s"
            return f"{speed:5.0f}  B/s"
            
        def get_bar(speed, max_spd, length=10):
            val = speed / max_spd if max_spd > 0 else 0
            val = min(1.0, max(0.0, val))
            bars = int(val * length)
            return "█" * bars + "░" * (length - bars)
            
        rx_bar = get_bar(recv, max_recv)
        tx_bar = get_bar(sent, max_sent)
        
        self.lbl_speed_rx.setText(f"↓ [{rx_bar}] {format_speed(recv)}")
        self.lbl_speed_tx.setText(f"↑ [{tx_bar}] {format_speed(sent)}")
        
        self.lbl_speed_rx.setStyleSheet(f"color: {self.theme.get('success', '#3fb950')};")
        self.lbl_speed_tx.setStyleSheet(f"color: {self.theme.get('accent', '#58a6ff')};")
        
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
        self.scroll.setFixedHeight(116)
        
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
            
        max_recv = max((c['recv_speed'] for c in conns), default=1.0)
        max_sent = max((c['sent_speed'] for c in conns), default=1.0)
        if max_recv < 1024 * 10: max_recv = 1024 * 10 # 下限规避全满
        if max_sent < 1024 * 10: max_sent = 1024 * 10
            
        # 复用卡片
        while len(self.cards) < len(conns):
            card = ConnCard(self.theme)
            self.cards.append(card)
            self.cards_layout.addWidget(card)
            
        for i, card in enumerate(self.cards):
            if i < len(conns):
                card.show()
                card.update_data(conns[i], max_recv, max_sent)
            else:
                card.hide()
        
        # 手动修正容器宽度避免遮挡
        self.cards_container.setMinimumWidth(len(conns) * 218)

'''

# modify "item_h = 108" to "item_h = 140" inside NetworkPage update_data function over all code
main_code = content[idx2:]
main_code = main_code.replace("item_h = 108", "item_h = 140")

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content[:idx1] + new_code + main_code)
print("done")
