# 标签栏控件
from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Qt, QSize, Signal, QEvent, QTimer
from PySide6.QtGui import QIcon, QPixmap
from utils.icon_utils import create_colored_pixmap, get_icon_path

class HoverButton(QPushButton):
    """鼠标悬浮控件"""
    def __init__(self, normal_icon: QIcon, hover_icon: QIcon, parent=None):
        super().__init__(normal_icon, "", parent)
        self._normal_icon = normal_icon
        self._hover_icon = hover_icon
        self.normal_size = QSize(25, 25)
        self.hover_size = QSize(30, 30)
        self.setIconSize(self.normal_size)

    def enterEvent(self, event: QEvent):
        """鼠标进入事件"""
        self.setIcon(self._hover_icon)
        self.setIconSize(self.hover_size)
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """鼠标离开事件"""
        self.setIcon(self._normal_icon)
        self.setIconSize(self.normal_size)
        super().leaveEvent(event)

class CustomTitleBar(QWidget):
    """自定义标题栏控件"""
    # 按钮
    minimize_to_tray_requested = Signal()
    minimize_requested = Signal()
    maximize_restore_requested = Signal()
    close_requested = Signal()
    # 双击标题栏
    double_click_requested = Signal()
    
    def __init__(self, title: str, logo_pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setObjectName("CustomTitleBar")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        # Logo和标题
        self.logo_label = QLabel(self)
        self.logo_label.setPixmap(logo_pixmap.scaled(45, 45, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        layout.addWidget(self.logo_label)
        self.title_label = QLabel(title, self)
        layout.addWidget(self.title_label)
        # 运行指示
        self.status_label = QLabel(self)
        self.status_label.setObjectName("StatusLabel")
        self.status_label.setVisible(False) # 默认隐藏
        layout.addWidget(self.status_label)
        self._animation_timer = QTimer(self)
        self._animation_timer.setInterval(500) # 每500毫秒更新一次
        self._animation_timer.timeout.connect(self._animate_status)
        self._dot_count = 0
        self._base_status_text = ""
        layout.addStretch() #弹簧
        # 设置按钮大小
        normal_icon_size = QSize(25, 25)
        hover_icon_size_restore_max = QSize(27, 27)
        hover_icon_size_tray_min = QSize(28, 28)
        hover_icon_size_close = QSize(29, 29)
        # 定义颜色
        normal_color = "#BEBEBE"
        hover_color_white = "#FFFFFF"
        close_hover_color_red = "#E81123"
        # 生成图标
        self.tray_icon_normal = QIcon(create_colored_pixmap(get_icon_path('tray'), normal_color, normal_icon_size))
        self.tray_icon_hover = QIcon(create_colored_pixmap(get_icon_path('tray'), hover_color_white, hover_icon_size_tray_min))
        self.min_icon_normal = QIcon(create_colored_pixmap(get_icon_path('min'), normal_color, normal_icon_size))
        self.min_icon_hover = QIcon(create_colored_pixmap(get_icon_path('min'), hover_color_white, hover_icon_size_tray_min))
        self.max_icon_normal = QIcon(create_colored_pixmap(get_icon_path('max'), normal_color, normal_icon_size))
        self.max_icon_hover = QIcon(create_colored_pixmap(get_icon_path('max'), hover_color_white, hover_icon_size_restore_max))
        self.restore_icon_normal = QIcon(create_colored_pixmap(get_icon_path('restore'), normal_color, normal_icon_size))
        self.restore_icon_hover = QIcon(create_colored_pixmap(get_icon_path('restore'), hover_color_white, hover_icon_size_restore_max))
        self.close_icon_normal = QIcon(create_colored_pixmap(get_icon_path('close'), normal_color, normal_icon_size))
        self.close_icon_hover = QIcon(create_colored_pixmap(get_icon_path('close'), close_hover_color_red, hover_icon_size_close))
        # 实例化
        self.tray_button = HoverButton(self.tray_icon_normal, self.tray_icon_hover, self)
        self.minimize_button = HoverButton(self.min_icon_normal, self.min_icon_hover, self)
        self.maximize_button = HoverButton(self.max_icon_normal, self.max_icon_hover, self)
        self.close_button = HoverButton(self.close_icon_normal, self.close_icon_hover, self)
        # 为按钮命名
        self.tray_button.setObjectName("trayButton")
        self.minimize_button.setObjectName("minimizeButton")
        self.maximize_button.setObjectName("maximizeButton")
        self.close_button.setObjectName("closeButton")
        # 连接信号
        self.tray_button.clicked.connect(self.minimize_to_tray_requested.emit)
        self.minimize_button.clicked.connect(self.minimize_requested.emit)
        self.maximize_button.clicked.connect(self.maximize_restore_requested.emit)
        self.close_button.clicked.connect(self.close_requested.emit)
        # 显示
        layout.addWidget(self.tray_button)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)

    def mouseDoubleClickEvent(self, event: QEvent):
        """处理鼠标双击事件，用于最大化/恢复窗口"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_click_requested.emit()
        super().mouseDoubleClickEvent(event)

    def update_restore_icon(self, is_maximized):
        """当窗口状态改变时，更新最大化/还原按钮的图标"""
        if is_maximized:
            self.maximize_button._normal_icon = self.restore_icon_normal
            self.maximize_button._hover_icon = self.restore_icon_hover
        else:
            self.maximize_button._normal_icon = self.max_icon_normal
            self.maximize_button._hover_icon = self.max_icon_hover
        self.maximize_button.setIcon(self.maximize_button._normal_icon)

    def start_task_animation(self, task_name: str):
        """开始任务运行动画"""
        self._base_status_text = f"{task_name} 运行中"
        self._dot_count = 0
        self.status_label.setText(self._base_status_text)
        self.status_label.setVisible(True)
        self._animation_timer.start()

    def stop_task_animation(self):
        """停止任务运行动画"""
        self._animation_timer.stop()
        self.status_label.setVisible(False)
        self._base_status_text = ""

    def _animate_status(self):
        """定时器调用的槽函数，用于更新点的数量"""
        self._dot_count = (self._dot_count + 1) % 4
        dots = "." * self._dot_count
        self.status_label.setText(f"{self._base_status_text}{dots}")