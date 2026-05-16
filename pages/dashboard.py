from PyQt6.QtWidgets import QWidget, QVBoxLayout, QGridLayout, QScrollArea, QSplitter
from PyQt6.QtGui import QFont
from PyQt6.QtCore import Qt, QSettings

from core.themes import DARK_THEME
from widgets.cpu_card import CpuDetailCard
from widgets.mem_card import MemoryDetailCard
from widgets.disk_card import DiskDetailCard
from widgets.net_card import NetworkDetailCard
from widgets.gpu_card import GpuDetailCard


class DashboardPage(QWidget):
    """仪表盘页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme = DARK_THEME
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        self.content_widget = QWidget()
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(16)

        # 构建支持用户自由拖动阻尼分配的极客大分割器
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setHandleWidth(10)
        
        # 💡 --- 上层主板/核心阵列容器 ---
        top_widget = QWidget()
        top_layout = QGridLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(12)

        self.cpu_card = CpuDetailCard()
        top_layout.addWidget(self.cpu_card, 0, 0)
        
        self.mem_card = MemoryDetailCard()
        top_layout.addWidget(self.mem_card, 0, 1)
        
        self.disk_card = DiskDetailCard()
        top_layout.addWidget(self.disk_card, 0, 2)
        
        self.net_card = NetworkDetailCard()
        top_layout.addWidget(self.net_card, 0, 3)

        top_layout.setColumnStretch(0, 20)
        top_layout.setColumnStretch(1, 15)
        top_layout.setColumnStretch(2, 37)
        top_layout.setColumnStretch(3, 18)

        # 💡 --- 下层 GPU 集群容器 (动态捕获本机真实 GPU) ---
        bottom_widget = QWidget()
        bottom_layout = QGridLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(12)
        
        import subprocess
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "Get-CimInstance win32_VideoController | Select-Object -ExpandProperty Name"],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            gpus = [line.strip() for line in res.stdout.split('\n') if line.strip() and not line.startswith("----") and "Name" not in line]
        except Exception:
            gpus = []
            
        if not gpus:
            gpus = ["NVIDIA GeForce RTX 4090", "Intel(R) UHD Graphics"]
            
        self.gpu_cards = []
        col = 0
        for i, gpu_name in enumerate(gpus):
            is_nvidia = "NVIDIA" in gpu_name.upper()
            gpu_type = "discrete" if is_nvidia else "integrated"
            card = GpuDetailCard(gpu_name=gpu_name, gpu_type=gpu_type)
            # Nvidia显卡赋予跨倍率列宽展现
            span = 2 if is_nvidia else 1
            if col + span > 4:
                col = 0
            bottom_layout.addWidget(card, 0, col, 1, span)
            self.gpu_cards.append(card)
            bottom_layout.setColumnStretch(col, 20 * span)
            col += span

        self.splitter.addWidget(top_widget)
        self.splitter.addWidget(bottom_widget)
        
        # 尝试恢复先前的动态拖动记忆，如果没有则给初始的 3:2 推荐值
        self.settings = QSettings("SystemIntervener", "Dashboard")
        saved_state = self.settings.value("splitter_state")
        if saved_state:
            self.splitter.restoreState(saved_state)
        else:
            self.splitter.setSizes([600, 400])

        # 监听拖动并存留到注册表/INI
        self.splitter.splitterMoved.connect(self._save_layout)

        layout.addWidget(self.splitter)
        
        self.scroll.setWidget(self.content_widget)
        main_layout.addWidget(self.scroll)

    def set_module_enabled(self, enabled: bool):
        cards = [self.cpu_card, self.mem_card, self.disk_card, self.net_card] + self.gpu_cards
        for card in cards:
            if hasattr(card, '_timer'):
                if enabled:
                    card._timer.start()
                else:
                    card._timer.stop()

    def get_anim_targets(self):
        return [self.cpu_card, self.mem_card, self.disk_card, self.net_card] + self.gpu_cards

    def _save_layout(self):
        self.settings.setValue("splitter_state", self.splitter.saveState())

    def apply_theme(self, theme):
        self.theme = theme
        self.scroll.setStyleSheet("background-color: transparent;")
        self.content_widget.setStyleSheet("background-color: transparent;")
        
        # 为分割条加入融合主题科技感
        self.splitter.setStyleSheet(f"""
            QSplitter::handle {{
                background: {theme.get('border', '#333333')};
                border-radius: 4px;
                margin: 4px 0;
            }}
            QSplitter::handle:hover {{
                background: {theme.get('text_secondary', '#666666')};
            }}
        """)
        
        self.cpu_card.theme = theme
        self.cpu_card.update()
        
        self.mem_card.theme = theme
        self.mem_card.update()
        
        self.disk_card.theme = theme
        self.disk_card.update()
        
        self.net_card.theme = theme
        self.net_card.update()
        
        for gpu in self.gpu_cards:
            gpu.theme = theme
            gpu.update()
