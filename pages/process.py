import os
import psutil
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QPushButton,
    QGridLayout, QMessageBox, QFileIconProvider, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QFileInfo, QPropertyAnimation
from PyQt6.QtGui import QColor, QFont, QIcon, QBrush

from core.themes import DARK_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon

class ProcessWorker(QThread):
    data_ready = pyqtSignal(list)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = True
        self.paused = False
        
    def run(self):
        # 建立持久化迭代器
        proc_iter = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe', 'username'])
        while self.running:
            if getattr(self, 'paused', False):
                time.sleep(1.0)
                continue
            processes = []
            for _ in range(10):  # 严格每秒仅抓取 10 个
                try:
                    proc = next(proc_iter)
                    info = proc.info
                    
                    pid = info.get('pid', 0)
                    if pid == 0: continue
                    
                    cpu = info.get('cpu_percent', 0.0) or 0.0
                    mem_info = info.get('memory_info')
                    mem_rss = mem_info.rss if mem_info else 0
                    mem = mem_rss / (1024 * 1024)
                    
                    processes.append({
                        'pid': pid,
                        'name': info.get('name', '') or '',
                        'cpu': cpu,
                        'mem': mem,
                        'user': info.get('username', '') or '',
                        'exe': info.get('exe', '') or ''
                    })
                except StopIteration:
                    # 循环回卷
                    proc_iter = psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info', 'exe', 'username'])
                    break
                except Exception:
                    pass
            
            if processes:
                self.data_ready.emit(processes)
                
            # 每秒休息
            time.sleep(1.0)
            
    def stop(self):
        self.running = False
        self.wait()

class ProcessCard(QWidget):
    kill_requested = pyqtSignal(int, str) # PID, 名字
    
    def __init__(self, pid, theme=DARK_THEME, parent=None):
        super().__init__(parent)
        self.pid = pid
        self.theme = theme
        self.exe_path = ""
        self.name = ""
        self.mem = 0.0
        self.is_selected = False
        self.setFixedSize(210, 52)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(8, 6, 8, 6)
        main_layout.setSpacing(8)
        
        self.lbl_icon = QLabel()
        self.lbl_icon.setFixedSize(24, 24)
        main_layout.addWidget(self.lbl_icon)
        
        vbox = QVBoxLayout()
        vbox.setSpacing(1)
        self.lbl_name_pid = QLabel(f"PID: {pid}")
        self.lbl_name_pid.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self.lbl_name_pid.setStyleSheet(f"color: {theme['text_primary']};")
        
        self.lbl_res = QLabel("CPU: 0% | Mem: 0MB")
        self.lbl_res.setFont(QFont("Segoe UI", 7))
        self.lbl_res.setStyleSheet(f"color: {theme['text_secondary']};")
        
        vbox.addWidget(self.lbl_name_pid)
        vbox.addWidget(self.lbl_res)
        main_layout.addLayout(vbox)
        main_layout.addStretch()
        
        self._update_style(0.0, 0.0)

    def set_selected(self, selected):
        self.is_selected = selected
        self._update_style(getattr(self, 'cpu', 0.0), getattr(self, 'mem', 0.0))

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.kill_requested.emit(self.pid, self.name)
        super().mousePressEvent(event)

    def _update_style(self, cpu, mem):
        if self.is_selected:
            self.setStyleSheet(f"""
                ProcessCard {{
                    background-color: {self.theme.get('accent_light', 'rgba(88, 166, 255, 0.15)')};
                    border: 2px solid {self.theme.get('accent', '#58a6ff')};
                    border-radius: 6px;
                }}
            """)
            self.lbl_res.setStyleSheet(f"color: {self.theme.get('text_primary', '#fff')};")
        elif cpu > 10.0 or mem > 1024.0:
            self.setStyleSheet(f"""
                ProcessCard {{
                    background-color: {self.theme.get('accent_light', 'rgba(88, 166, 255, 0.1)')};
                    border: 1px solid {self.theme.get('accent', '#58a6ff')};
                    border-radius: 6px;
                }}
            """)
            self.lbl_res.setStyleSheet(f"color: {self.theme.get('warning', '#d29922')}; font-weight: bold;")
        else:
            self.setStyleSheet(f"""
                ProcessCard {{
                    background-color: {self.theme['bg_card']};
                    border: 1px solid {self.theme['border']};
                    border-radius: 6px;
                }}
                ProcessCard:hover {{
                    border: 1px solid {self.theme.get('accent', '#58a6ff')};
                    background-color: {self.theme.get('bg_hover', '#2d333b')};
                }}
            """)
            self.lbl_res.setStyleSheet(f"color: {self.theme['text_secondary']};")

    def update_data(self, info):
        name = info['name']
        cpu = info['cpu']
        mem = info['mem']
        self.exe_path = info['exe']
        self.name = name
        self.mem = mem
        self.cpu = cpu
        
        self.lbl_name_pid.setText(f"{name} ({self.pid})")
        self.lbl_res.setText(f"CPU: {cpu:.1f}% | Mem: {mem:.1f} MB")
        self._update_style(cpu, mem)

    def set_icon(self, icon):
        self.lbl_icon.setPixmap(icon.pixmap(24, 24))


class ToastNotification(QWidget):
    def __init__(self, text, bg_color="#1f6feb", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(text)
        self.label.setStyleSheet(f"background-color: {bg_color}; color: white; padding: 8px 16px; border-radius: 6px; font-family: 'Segoe UI'; font-weight: bold;")
        layout.addWidget(self.label)
        self.adjustSize()
        self.eff = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.eff)
        self.eff.setOpacity(0)
        self.anim_in = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim_in.setDuration(200)
        self.anim_in.setEndValue(1.0)
        self.anim_out = QPropertyAnimation(self.eff, b"opacity", self)
        self.anim_out.setDuration(600)
        self.anim_out.setEndValue(0.0)
        self.anim_out.finished.connect(self.deleteLater)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.anim_out.start)
        
    def show_toast(self, parent_btn):
        pos = parent_btn.mapToGlobal(parent_btn.rect().bottomLeft())
        x = pos.x() + parent_btn.width() // 2 - self.width() // 2
        y = pos.y() + 5
        self.move(x, y)
        self.show()
        self.anim_in.start()
        self.timer.start(1000)

class ProcessGridContainer(QWidget):
    def __init__(self, theme, parent=None):
        super().__init__(parent)
        self.theme = theme
        self.groups = []

    def update_groups(self, group_pids, cards_dict):
        self.groups = []
        for pids in group_pids:
            widgets = [cards_dict[pid] for pid in pids if pid in cards_dict]
            if len(widgets) > 1:
                self.groups.append(widgets)
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
        from PyQt6.QtCore import QRectF, Qt
        
        if not self.groups:
            return
            
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        import hashlib
        
        # 预设一组对深色模式友好的高对比度赛博色卡
        palette = [
            QColor('#58a6ff'), # 科技蓝
            QColor('#3fb950'), # 矩阵绿
            QColor('#d29922'), # 警示黄
            QColor('#f85149'), # 拦截红
            QColor('#a371f7'), # 深层紫
            QColor('#ff7b72'), # 珊瑚粉
            QColor('#2f81f7'), # 纯正蓝
            QColor('#46bbf8'), # 青蓝
        ]
        
        for g_widgets in self.groups:
            # 提取进程名进行稳定哈希，确保同一个名字总是一样的分配色
            name = getattr(g_widgets[0], 'name', 'Unknown')
            h_val = int(hashlib.md5(name.encode('utf-8')).hexdigest(), 16)
            base_color = palette[h_val % len(palette)]
            
            fill_color = QColor(base_color)
            fill_color.setAlpha(12)
            pen_color = QColor(base_color)
            pen_color.setAlpha(180)
            
            p.setPen(QPen(pen_color, 2))
            p.setBrush(fill_color)
            
            path = QPainterPath()
            path.setFillRule(Qt.FillRule.WindingFill)
            for w in g_widgets:
                # 因为网格间隔是6，扩展 4 像素使得相邻的完全对接重叠（原必须为int防错）
                r = w.geometry().adjusted(-4, -4, 4, 4)
                path.addRoundedRect(QRectF(r), 6, 6)
                
            unified_path = path.simplified()
            p.drawPath(unified_path)


class ProcessPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = DARK_THEME
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        self.default_icon = QIcon(create_svg_icon(SVG_ICONS.get("process", ""), 24, "#8b949e"))
        self.icon_provider = QFileIconProvider()
        self.icon_cache = {}
        
        # 头部功能区
        top_layout = QHBoxLayout()
        self.lbl_title = QLabel("进程控制")
        self.lbl_title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.lbl_title.setStyleSheet(f"color: {self.theme['text_primary']};")
        self.subtitle = QLabel("超轻量卡片式资源接管")
        self.subtitle.setFont(QFont("Segoe UI", 11))
        self.subtitle.setStyleSheet(f"color: {self.theme['text_secondary']};")
        
        title_vbox = QVBoxLayout()
        title_vbox.addWidget(self.lbl_title)
        title_vbox.addWidget(self.subtitle)
        title_vbox.setSpacing(4)
        
        self.btn_mem_opt = QPushButton("强制剥离内存")
        self.btn_mem_opt.setMinimumHeight(36)
        self.btn_mem_opt.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_mem_opt.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_mem_opt.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme['text_primary']};
                background-color: {self.theme['bg_card']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('bg_hover', '#2d333b')};
                border: 1px solid {self.theme.get('accent', '#58a6ff')};
            }}
        """)
        self.btn_mem_opt.clicked.connect(self.optimize_memory)
        
        self.btn_kill = QPushButton("强制结束进程")
        self.btn_kill.setMinimumHeight(36)
        self.btn_kill.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.btn_kill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_kill.setEnabled(False) # 默认未选中时禁用
        self.btn_kill.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme['text_primary']};
                background-color: {self.theme['bg_card']};
                border: 1px solid {self.theme['danger']};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('danger', '#f85149')};
                border: 1px solid {self.theme.get('danger', '#f85149')};
            }}
            QPushButton:disabled {{
                color: rgba(255, 255, 255, 0.4);
                border: 1px solid rgba(255, 255, 255, 0.1);
            }}
        """)
        self.btn_kill.clicked.connect(self.kill_selected)

        top_layout.addLayout(title_vbox)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_kill)
        top_layout.addWidget(self.btn_mem_opt)
        layout.addLayout(top_layout)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.scroll.setStyleSheet("background: transparent;")
        
        self.grid_container = ProcessGridContainer(self.theme)
        self.grid_container.setStyleSheet("background: transparent;")
        self.grid = QGridLayout(self.grid_container)
        self.grid.setSpacing(6)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self.scroll.setWidget(self.grid_container)
        layout.addWidget(self.scroll)
        
        self.selected_pid = None
        self.selected_name = ""
        self.cards = {}
        self.ordered_pids = []
        self.current_groups = []
        
        self.worker = ProcessWorker()
        self.worker.data_ready.connect(self.update_data)
        self.worker.start()
        
    def get_anim_targets(self):
        return [self.lbl_title, self.subtitle, self.btn_kill, self.btn_mem_opt, self.scroll]

    def set_module_enabled(self, enabled: bool):
        self.worker.paused = not enabled

    def apply_theme(self, theme):
        self.theme = theme
        self.lbl_title.setStyleSheet(f"color: {self.theme['text_primary']};")
        self.subtitle.setStyleSheet(f"color: {self.theme['text_secondary']};")
        
        self.btn_mem_opt.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme['text_primary']};
                background-color: {self.theme['bg_card']};
                border: 1px solid {self.theme['border']};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('bg_hover', '#2d333b')};
                border: 1px solid {self.theme.get('accent', '#58a6ff')};
            }}
        """)
        
        self.btn_kill.setStyleSheet(f"""
            QPushButton {{
                color: {self.theme['text_primary']};
                background-color: {self.theme['bg_card']};
                border: 1px solid {self.theme['danger']};
                border-radius: 6px;
                padding: 0 16px;
            }}
            QPushButton:hover {{
                background-color: {self.theme.get('danger', '#f85149')};
                border: 1px solid {self.theme.get('danger', '#f85149')};
            }}
            QPushButton:disabled {{
                color: rgba(128, 128, 128, 0.4);
                border: 1px solid rgba(128, 128, 128, 0.1);
            }}
        """)
        
        self.grid_container.theme = theme
        self.grid_container.update()
        
        for card in self.cards.values():
            card.theme = theme
            card.lbl_name_pid.setStyleSheet(f"color: {theme['text_primary']};")
            card._update_style(getattr(card, 'cpu', 0.0), getattr(card, 'mem', 0.0))
        
    def get_icon(self, exe_path):
        if not exe_path: return self.default_icon
        if exe_path in self.icon_cache: return self.icon_cache[exe_path]
        try:
            qicon = self.icon_provider.icon(QFileInfo(exe_path))
            if not qicon.isNull():
                res = QIcon(qicon.pixmap(32, 32))
                self.icon_cache[exe_path] = res
                return res
        except: pass
        self.icon_cache[exe_path] = self.default_icon
        return self.default_icon
        
    def _rebuild_grid(self):
        cols = max(1, self.scroll.width() // 220)
        # 将现有的卡片按最新的顺序列出并重新布局
        for card in self.cards.values():
            self.grid.removeWidget(card)
                
        for i, pid in enumerate(self.ordered_pids):
            card = self.cards[pid]
            r = i // cols
            c = i % cols
            self.grid.addWidget(card, r, c)
            card.show()
            
        self.grid_container.update_groups(self.current_groups, self.cards)
            
    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._rebuild_grid()
        
    def update_data(self, processes):
        # 定期全量清理死亡进程太耗时，我们在这里简单对即将更新的这10个或者现存进行一次状态查询
        changed = False
        
        # 为了防止泄漏，每隔一段时间或者每次随机挑几个 pid 测试 exists
        todelete = []
        import random
        for pid in random.sample(self.ordered_pids, min(len(self.ordered_pids), 20)):
            if not psutil.pid_exists(pid):
                todelete.append(pid)
                
        for pid in todelete:
            card = self.cards.pop(pid)
            card.deleteLater()
            self.ordered_pids.remove(pid)
            
            if pid == self.selected_pid:
                self.selected_pid = None
                self.selected_name = ""
                self.btn_kill.setEnabled(False)
                self.btn_kill.setText("强制结束进程")
                
            changed = True
            
        for info in processes:
            pid = info['pid']
            if pid not in self.cards:
                if len(self.cards) > 2000: continue
                card = ProcessCard(pid, theme=self.theme)
                card.kill_requested.connect(self.select_card)
                self.cards[pid] = card
                self.ordered_pids.append(pid)
                changed = True
                
            card = self.cards[pid]
            card.update_data(info)
            card.set_icon(self.get_icon(info['exe']))
            
        old_order = list(self.ordered_pids)
        
        # 聚合分组并进行复合树状排序（同伴相聚 + 总量降序）
        groups = {}
        for pid in self.ordered_pids:
            card = self.cards[pid]
            # 这里按照名字分组最好（例如所有的 chrome.exe）
            group_key = card.name if card.name else 'System'
            if group_key not in groups:
                groups[group_key] = {'total_mem': 0, 'pids': []}
            groups[group_key]['total_mem'] += card.mem
            groups[group_key]['pids'].append(pid)
            
        # 根据聚合后总组内存降序
        sorted_groups = sorted(groups.values(), key=lambda g: g['total_mem'], reverse=True)
        
        new_order = []
        new_groups = []
        for g in sorted_groups:
            # 组内单进程按自身内存大小再降序
            sorted_pids = sorted(g['pids'], key=lambda pid: self.cards[pid].mem, reverse=True)
            new_order.extend(sorted_pids)
            new_groups.append(sorted_pids)
            
        self.ordered_pids = new_order
        self.current_groups = new_groups
        
        # 如果顺序发生了改变或卡片发生了增加/删减，触发重构
        if changed or old_order != self.ordered_pids:
            self._rebuild_grid()
        else:
            # 定时更新一下容器确保卡片有内部变动时框体同步
            self.grid_container.update()

    def select_card(self, pid, name):
        # 取消旧的选择
        if self.selected_pid in self.cards:
            self.cards[self.selected_pid].set_selected(False)
            
        self.selected_pid = pid
        self.selected_name = name
        
        # 激活新的选择
        if pid in self.cards:
            self.cards[pid].set_selected(True)
            self.btn_kill.setEnabled(True)
            self.btn_kill.setText(f"结束进程 ({name})")

    def kill_selected(self):
        if not self.selected_pid: return
        pid = self.selected_pid
        name = self.selected_name
        try:
            proc = psutil.Process(pid)
            proc.kill()
            t = ToastNotification(f"已强制终止: {name}", bg_color=self.theme.get('danger', '#f85149'))
            t.show_toast(self.btn_kill) # Anchor to nearby button
            
            # 手动移除以防在这一秒内还没扫到
            if pid in self.cards:
                card = self.cards.pop(pid)
                card.deleteLater()
                if pid in self.ordered_pids:
                    self.ordered_pids.remove(pid)
                self._rebuild_grid()
                
            self.selected_pid = None
            self.selected_name = ""
            self.btn_kill.setEnabled(False)
            self.btn_kill.setText("强制结束进程")
        except BaseException as e:
            QMessageBox.critical(self, "错误", f"无法结束进程 {pid}\n{str(e)}")

    def optimize_memory(self):
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.windll.kernel32
        PROCESS_SET_QUOTA = 0x0100
        EmptyWorkingSet = ctypes.windll.psapi.EmptyWorkingSet
        
        success_count = 0
        fail_count = 0
        
        for pid in self.ordered_pids:
            try:
                hProcess = kernel32.OpenProcess(PROCESS_SET_QUOTA, False, pid)
                if hProcess:
                    if EmptyWorkingSet(hProcess):
                        success_count += 1
                    else:
                        fail_count += 1
                    kernel32.CloseHandle(hProcess)
                else:
                    fail_count += 1
            except:
                fail_count += 1
                
        t = ToastNotification(f"成功剥离 {success_count} 个 | 跳过 {fail_count} 个", bg_color=self.theme.get('info', '#1f6feb'))
        t.show_toast(self.btn_mem_opt)
