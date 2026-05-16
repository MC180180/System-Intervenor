"""
系统干预器 - 主程序入口
Python 3.12.4 + PyQt6
模块化架构
"""
import sys

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFrame, QStackedWidget, QToolTip
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIcon

from core.themes import DARK_THEME, LIGHT_THEME
from resources.icons import SVG_ICONS
from utils.svg_helper import create_svg_icon
from widgets.theme_toggle import ThemeToggle
from widgets.sidebar_button import SidebarButton
from widgets.mini_chart import SystemMiniChart
from pages.dashboard import DashboardPage
from pages.process import ProcessPage
from pages.network import NetworkPage
from pages.placeholder import PlaceholderPage


class MainWindow(QMainWindow):
    """系统干预器主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("系统干预器")
        self.resize(1500, 1000)
        self.setMinimumSize(1200, 800)

        self._current_theme = DARK_THEME
        self._sidebar_buttons: list[SidebarButton] = []
        self._current_sidebar_index = 0

        self._build_ui()
        self._apply_theme(DARK_THEME)

    def _build_ui(self):
        # 中央容器
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ── 顶部栏 ──
        self.topbar = QFrame()
        self.topbar.setFixedHeight(52)
        topbar_layout = QHBoxLayout(self.topbar)
        topbar_layout.setContentsMargins(16, 0, 16, 0)
        topbar_layout.setSpacing(12)

        # 应用标题
        self.app_title = QLabel("⚡ 系统干预器")
        self.app_title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        topbar_layout.addWidget(self.app_title)

        # 面包屑
        self.breadcrumb = QLabel("仪表盘")
        self.breadcrumb.setFont(QFont("Segoe UI", 10))
        topbar_layout.addWidget(self.breadcrumb)

        topbar_layout.addStretch()

        # 搜索框
        self.search_frame = QFrame()
        self.search_frame.setFixedSize(240, 32)
        search_layout = QHBoxLayout(self.search_frame)
        search_layout.setContentsMargins(10, 0, 10, 0)
        search_layout.setSpacing(6)

        self.search_icon = QLabel()
        self.search_icon.setFixedSize(16, 16)
        search_layout.addWidget(self.search_icon)

        self.search_label = QLabel("搜索功能... Ctrl+K")
        self.search_label.setFont(QFont("Segoe UI", 9))
        search_layout.addWidget(self.search_label)

        topbar_layout.addWidget(self.search_frame)

        # 通知按钮
        self.bell_btn = QPushButton()
        self.bell_btn.setFixedSize(32, 32)
        self.bell_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.bell_btn.setToolTip("通知")
        topbar_layout.addWidget(self.bell_btn)

        # 主题切换
        self.theme_toggle = ThemeToggle()
        topbar_layout.addWidget(self.theme_toggle)

        main_layout.addWidget(self.topbar)

        # 顶部分隔线
        self.top_sep = QFrame()
        self.top_sep.setFixedHeight(1)
        main_layout.addWidget(self.top_sep)

        # ── 中间区域（侧栏 + 内容）──
        mid_widget = QWidget()
        mid_layout = QHBoxLayout(mid_widget)
        mid_layout.setContentsMargins(0, 0, 0, 0)
        mid_layout.setSpacing(0)

        # 侧栏
        self.sidebar = QFrame()
        self.sidebar.setFixedWidth(60)
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(6, 12, 6, 12)
        sidebar_layout.setSpacing(4)

        sidebar_items = [
            ("dashboard", "仪表盘"),
            ("process", "进程管理"),
            ("network", "网络监控"),
            ("security", "安全防护"),
            ("storage", "存储管理"),
            ("terminal", "终端"),
        ]
        for icon_key, label in sidebar_items:
            btn = SidebarButton(icon_key, label)
            btn.clicked.connect(lambda checked, ik=icon_key: self._on_sidebar_click(ik))
            btn.right_clicked.connect(self._on_sidebar_right_click)
            sidebar_layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignHCenter)
            self._sidebar_buttons.append(btn)

        sidebar_layout.addStretch()

        # 底部设置
        settings_btn = SidebarButton("settings", "设置")
        settings_btn.clicked.connect(lambda: self._on_sidebar_click("settings"))
        settings_btn.right_clicked.connect(self._on_sidebar_right_click)
        sidebar_layout.addWidget(settings_btn, alignment=Qt.AlignmentFlag.AlignHCenter)
        self._sidebar_buttons.append(settings_btn)

        mid_layout.addWidget(self.sidebar)

        # 侧栏分隔线
        self.side_sep = QFrame()
        self.side_sep.setFixedWidth(1)
        mid_layout.addWidget(self.side_sep)

        # 内容区域
        self.content_stack = QStackedWidget()

        # 仪表盘
        self.dashboard_page = DashboardPage()
        self.content_stack.addWidget(self.dashboard_page)

        # 进程页面
        self.process_page = ProcessPage()
        self.content_stack.addWidget(self.process_page)

        # 网络监控页面
        self.network_page = NetworkPage()
        self.content_stack.addWidget(self.network_page)

        # 剩余占位页面
        pages_data = [
            ("security", "安全防护", "系统安全策略与威胁检测"),
            ("storage", "存储管理", "磁盘分区与存储优化"),
            ("terminal", "终端", "集成命令行终端"),
            ("settings", "设置", "系统干预器偏好设置"),
        ]
        self._pages = {"dashboard": 0, "process": 1, "network": 2}
        for i, (icon, title, desc) in enumerate(pages_data):
            page = PlaceholderPage(icon, title, desc)
            self.content_stack.addWidget(page)
            self._pages[icon] = i + 3

        mid_layout.addWidget(self.content_stack)
        main_layout.addWidget(mid_widget, 1)

        # ── 底部分隔线 ──
        self.bot_sep = QFrame()
        self.bot_sep.setFixedHeight(1)
        main_layout.addWidget(self.bot_sep)

        # ── 底部数据可视化栏 ──
        self.bottom_bar = QFrame()
        self.bottom_bar.setFixedHeight(130)
        bottom_layout = QHBoxLayout(self.bottom_bar)
        bottom_layout.setContentsMargins(12, 8, 12, 8)
        bottom_layout.setSpacing(8)

        self.mini_charts = []
        
        # 依次加载 CPU, 内存, 磁盘和网络 的堆叠组件
        for mode in ["cpu", "mem", "disk", "net"]:
            chart = SystemMiniChart(mode)
            bottom_layout.addWidget(chart)
            self.mini_charts.append(chart)

        main_layout.addWidget(self.bottom_bar)

        # 初始选中
        self._sidebar_buttons[0].set_active(True)

        # 恢复状态并应用
        from PyQt6.QtCore import QSettings
        settings = QSettings("SystemIntervener", "SidebarState")
        for btn in self._sidebar_buttons:
            is_disabled = settings.value(btn.icon_key, False, type=bool)
            if is_disabled:
                btn.set_disabled_state(True)
                self._apply_module_state(btn.icon_key, False)

    def _on_sidebar_click(self, icon_key: str):
        idx = self._pages.get(icon_key, 0)
        if hasattr(self, 'content_stack') and self.content_stack.currentIndex() == idx:
            return
            
        page_names = {
            "dashboard": "仪表盘",
            "process": "进程管理",
            "network": "网络监控",
            "security": "安全防护",
            "storage": "存储管理",
            "terminal": "终端",
            "settings": "设置",
        }
        self.breadcrumb.setText(page_names.get(icon_key, ""))

        for btn in self._sidebar_buttons:
            btn.set_active(btn.icon_key == icon_key)
            
        self._fade_transition(idx)

    def _fade_transition(self, new_idx):
        if getattr(self, '_is_transitioning', False):
            return
            
        old_page = self.content_stack.currentWidget()
        new_page = self.content_stack.widget(new_idx)
        
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
        
        def get_targets(page):
            if hasattr(page, 'get_anim_targets'):
                return page.get_anim_targets()
            return [page]
            
        old_targets = get_targets(old_page)
        self._new_targets_cache = get_targets(new_page)
        self._new_idx_cache = new_idx
        
        self._fade_states = []
        out_duration = 150
        
        self._is_transitioning = True
        
        for w in old_targets:
            eff = QGraphicsOpacityEffect(w)
            w.setGraphicsEffect(eff)
            
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(out_duration)
            anim.setStartValue(1.0)
            anim.setEndValue(0.0)
            self._fade_states.append((w, eff, anim))
            anim.start()
            
        for btn in self._sidebar_buttons:
            btn.setEnabled(False)
            
        QTimer.singleShot(out_duration + 5, self._on_fade_out_finished)

    def _on_fade_out_finished(self):
        for w, eff, anim in self._fade_states:
            w.setGraphicsEffect(None)
            
        self._fade_states = []
        self.content_stack.setCurrentIndex(self._new_idx_cache)
        
        from PyQt6.QtWidgets import QGraphicsOpacityEffect
        from PyQt6.QtCore import QPropertyAnimation, QEasingCurve, QTimer
        
        in_duration = 300
        
        for i, w in enumerate(self._new_targets_cache):
            eff = QGraphicsOpacityEffect(w)
            eff.setOpacity(0.0)
            w.setGraphicsEffect(eff)
            
            anim = QPropertyAnimation(eff, b"opacity")
            anim.setDuration(in_duration)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            self._fade_states.append((w, eff, anim))
            QTimer.singleShot(i * 60, anim.start)
            
        total_time = in_duration + len(self._new_targets_cache) * 60
        QTimer.singleShot(total_time + 10, self._on_fade_in_finished)

    def _on_fade_in_finished(self):
        for w, eff, anim in self._fade_states:
            w.setGraphicsEffect(None)
            
        self._fade_states = []
        self._is_transitioning = False
        for btn in self._sidebar_buttons:
            btn.setEnabled(True)

    def _on_sidebar_right_click(self, icon_key: str):
        from PyQt6.QtCore import QSettings
        settings = QSettings("SystemIntervener", "SidebarState")
        is_disabled = settings.value(icon_key, False, type=bool)
        new_disabled = not is_disabled
        settings.setValue(icon_key, new_disabled)
        
        for btn in self._sidebar_buttons:
            if btn.icon_key == icon_key:
                btn.set_disabled_state(new_disabled)
                break
                
        self._apply_module_state(icon_key, not new_disabled)

    def _apply_module_state(self, icon_key: str, enabled: bool):
        idx = self._pages.get(icon_key, -1)
        if idx != -1:
            page = self.content_stack.widget(idx)
            if hasattr(page, 'set_module_enabled'):
                page.set_module_enabled(enabled)

    def toggle_theme(self):
        if self._current_theme["name"] == "dark":
            self._apply_theme(LIGHT_THEME)
        else:
            self._apply_theme(DARK_THEME)

    def _apply_theme(self, theme: dict):
        self._current_theme = theme

        # 窗口背景
        self.centralWidget().setStyleSheet(f"background-color: {theme['bg_primary']};")

        # 顶栏
        self.topbar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['topbar_bg']};
                border: none;
            }}
        """)
        self.app_title.setStyleSheet(f"color: {theme['text_primary']}; background: transparent;")
        self.breadcrumb.setStyleSheet(f"color: {theme['text_muted']}; background: transparent;")

        # 搜索框
        self.search_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['bg_tertiary']};
                border: 1px solid {theme['border']};
                border-radius: 8px;
            }}
        """)
        search_pixmap = create_svg_icon(SVG_ICONS["search"], 14, theme["text_muted"])
        self.search_icon.setPixmap(search_pixmap)
        self.search_label.setStyleSheet(f"color: {theme['text_muted']}; background: transparent; border: none;")

        # 通知按钮
        bell_pixmap = create_svg_icon(SVG_ICONS["bell"], 18, theme["text_secondary"])
        self.bell_btn.setIcon(QIcon(bell_pixmap))
        self.bell_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                border: none;
                border-radius: 6px;
            }}
            QPushButton:hover {{
                background-color: {theme['bg_hover']};
            }}
        """)

        # 分隔线
        sep_style = f"background-color: {theme['border']};"
        self.top_sep.setStyleSheet(sep_style)
        self.side_sep.setStyleSheet(sep_style)
        self.bot_sep.setStyleSheet(sep_style)

        # 侧栏
        self.sidebar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['sidebar_bg']};
                border: none;
            }}
        """)
        for btn in self._sidebar_buttons:
            btn.theme = theme
            btn.update()

        # 内容区域
        self.content_stack.setStyleSheet(f"background-color: {theme['bg_primary']};")

        # 页面
        self.dashboard_page.apply_theme(theme)
        for i in range(1, self.content_stack.count()):
            page = self.content_stack.widget(i)
            if hasattr(page, 'apply_theme'):
                page.apply_theme(theme)

        # 底部栏
        self.bottom_bar.setStyleSheet(f"""
            QFrame {{
                background-color: {theme['bottom_bg']};
                border: none;
            }}
        """)

        # 更新图表颜色
        for chart in self.mini_charts:
            chart.theme = theme
            chart.update()

        # 主题切换按钮
        self.theme_toggle.theme = theme
        self.theme_toggle.update()

        # 工具提示
        QToolTip.setFont(QFont("Segoe UI", 9))


def main():
    app = QApplication(sys.argv)

    # 全局字体
    app.setFont(QFont("Segoe UI", 10))

    # 全局工具提示样式
    app.setStyleSheet("""
        QToolTip {
            background-color: #21262d;
            color: #e6edf3;
            border: 1px solid #30363d;
            padding: 6px 10px;
            border-radius: 6px;
            font-size: 12px;
        }
    """)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
