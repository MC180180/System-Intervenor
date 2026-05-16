import codecs

path = r"c:\Users\Administrator\Desktop\系统干预器\pages\network.py"
with codecs.open(path, 'r', 'utf-8') as f:
    content = f.read()

# 1. Update imports
content = content.replace(
    '''from PyQt6.QtCore import Qt, QThread, pyqtSignal''',
    '''from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPropertyAnimation, QPoint, QEasingCurve'''
)

# 2. Extract up to NetworkPage update_data function and rewrite the rest
idx = content.find("class NetworkPage(QWidget):")
idx2 = content.find("    def update_data(self, io_speeds, conns):", idx)

if idx == -1 or idx2 == -1:
    print("Cannot find points.")
    import sys; sys.exit(1)

# Now we also need to rewrite init to remove groups_layout
init_part = content[idx:idx2]
init_part = init_part.replace(
'''        self.groups_layout = QVBoxLayout(self.groups_container)
        self.groups_layout.setContentsMargins(0, 0, 0, 0)
        self.groups_layout.setSpacing(12)
        self.groups_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        self.scroll.setWidget(self.groups_container)
        layout.addWidget(self.scroll)
        
        self.process_groups = {}''',
'''        self.scroll.setWidget(self.groups_container)
        layout.addWidget(self.scroll)
        
        self.process_groups = {}
        self.group_animations = {}
        self.speed_history = {}
        self.sorted_pids = []
        self.last_sort_time = 0'''
)

new_update_data = '''    def update_data(self, io_speeds, conns):
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
        
        # 计算每个 PID 的 10 秒平均流量和当前总流量
        for pid, group in groups.items():
            total_speed = sum(c['recv_speed'] + c['sent_speed'] for c in group['conns'])
            if pid not in self.speed_history:
                self.speed_history[pid] = []
            self.speed_history[pid].append((current_time, total_speed))
            
            # 清理过了 10 秒的历史数据
            self.speed_history[pid] = [(t, s) for t, s in self.speed_history[pid] if current_time - t <= 10.0]
            
            # 计算平滑的均值作为排序权重
            avg_speed = sum(s for t, s in self.speed_history[pid]) / len(self.speed_history[pid])
            group['avg_speed'] = avg_speed
            
        # 频率节流：仅每隔 2.0 秒重组一次顺序
        if getattr(self, 'last_sort_time', 0) == 0 or current_time - self.last_sort_time >= 2.0:
            self.sorted_pids = sorted(groups.keys(), key=lambda p: groups[p]['avg_speed'], reverse=True)
            self.last_sort_time = current_time
            
        # 追加新出现的 pid（如果在这 2 秒内诞生了）到末尾，防止消失或报错
        for pid in groups.keys():
            if pid not in self.sorted_pids:
                self.sorted_pids.append(pid)
        # 清除已经消失的进程
        self.sorted_pids = [pid for pid in self.sorted_pids if pid in groups]

        # 同步卡片内容和容器创建
        for pid in self.sorted_pids:
            if pid not in self.process_groups:
                pg = ProcessNetGroup(pid, groups[pid]['name'], self.theme, parent=self.groups_container)
                pg.show()
                self.process_groups[pid] = pg
            self.process_groups[pid].update_connections(groups[pid]['conns'])

        # 清除不存在的组
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

        # 对排列在组内的卡片执行平滑的位移动画
        y = 0
        spacing = 12
        item_w = self.scroll.viewport().width() - 8
        if item_w < 100: item_w = 100
        
        for pid in self.sorted_pids:
            pg = self.process_groups[pid]
            # ProcessNetGroup 的高度固定为所需大小，此处预估 108 px
            item_h = 108
            
            # 立即调整正确的宽度（不参与动画直接展开）
            if pg.width() != item_w:
                pg.resize(item_w, item_h)
            
            target_pos = QPoint(0, y)
            
            if pg.pos() != target_pos:
                if pid not in self.group_animations:
                    # 如果初次出现直接闪现到对应位置，防止从 0,0 飞过来
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
            
        # 修正外层可滚动的边界
        self.groups_container.setMinimumHeight(y)
        
    def resizeEvent(self, e):
        super().resizeEvent(e)
        w = self.scroll.viewport().width() - 8
        if w > 0:
            for pg in self.process_groups.values():
                pg.resize(w, pg.height())
'''

with codecs.open(path, 'w', 'utf-8') as f:
    f.write(content[:idx] + init_part + new_update_data)
print("done")
