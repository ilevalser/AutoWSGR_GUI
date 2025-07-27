# 自定义实用函数
from PySide6.QtCore import QSize, QByteArray
from PySide6.QtGui import QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtCore import Qt
from constants import ICONS_DIR

def create_colored_pixmap(svg_path: str, color: str, size: QSize) -> QPixmap:
    """从SVG文件创建并返回一个着色后的、指定尺寸的QPixmap"""
    with open(svg_path, 'r', encoding='utf-8') as f:
        svg_data = f.read()
    colored_svg_data = svg_data.replace('currentColor', color, -1)
    renderer = QSvgRenderer(QByteArray(colored_svg_data.encode('utf-8')))
    # 直接创建目标尺寸的Pixmap
    pixmap = QPixmap(size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    renderer.render(painter)
    painter.end()
    return pixmap

def get_icon_path(icon_name: str) -> str:
    """根据图标名称获取完整的SVG文件路径"""
    return str(ICONS_DIR / f'{icon_name}.svg')