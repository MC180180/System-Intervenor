"""
SVG 图标渲染工具
将 SVG 字符串转换为高清 QPixmap（综合 DPI 方案）
"""
from PyQt6.QtCore import Qt, QByteArray, QRect
from PyQt6.QtGui import QPixmap, QPainter
from PyQt6.QtSvg import QSvgRenderer
from PyQt6.QtWidgets import QApplication


def get_dpr() -> float:
    """获取屏幕设备像素比"""
    screen = QApplication.primaryScreen()
    return screen.devicePixelRatio() if screen else 1.0


def create_svg_icon(svg_str: str, size: int = 22, color: str = "#8b949e") -> QPixmap:
    """从 SVG 字符串创建高清 QPixmap

    4x 超采样渲染后缩放到物理像素尺寸，设置 DPR 标记。
    调用方使用 draw_icon() 绘制以确保尺寸正确。

    Args:
        svg_str: SVG 格式的图标字符串
        size: 图标目标逻辑尺寸（正方形）
        color: 替换 currentColor 的目标颜色

    Returns:
        高分辨率 QPixmap，已设置 devicePixelRatio
    """
    svg_str = svg_str.replace('currentColor', color)
    renderer = QSvgRenderer(QByteArray(svg_str.encode()))

    dpr = get_dpr()
    physical_size = max(int(size * dpr), size)

    # 以 4 倍分辨率渲染 SVG
    render_size = size * 4
    large_pixmap = QPixmap(render_size, render_size)
    large_pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(large_pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    renderer.render(painter)
    painter.end()

    # 缩放到物理像素尺寸，保留高清细节
    result = large_pixmap.scaled(
        physical_size, physical_size,
        Qt.AspectRatioMode.KeepAspectRatio,
        Qt.TransformationMode.SmoothTransformation
    )
    result.setDevicePixelRatio(dpr)
    return result


def draw_icon(painter: QPainter, x: int, y: int, pixmap: QPixmap, logical_size: int):
    """在 QPainter 上绘制图标，确保大小精确

    Args:
        painter: 目标 QPainter
        x: 逻辑 X 坐标
        y: 逻辑 Y 坐标
        pixmap: create_svg_icon 返回的 QPixmap
        logical_size: 期望的逻辑绘制尺寸
    """
    painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
    painter.drawPixmap(QRect(x, y, logical_size, logical_size), pixmap)
