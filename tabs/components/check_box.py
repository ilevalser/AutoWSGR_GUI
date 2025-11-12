from PySide6.QtWidgets import QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import QSize, QEvent
from utils.icon_utils import get_icon_path, create_colored_pixmap 

class CustomCheckBox(QPushButton):
    """自定义CheckBox"""
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setObjectName("CustomCheckBox")
        # 内部变量，用于存储文本
        self._text_storage = text
        # 定义图标
        check_color = "#FFFFFF"
        disabled_color = "#888888"
        icon_size = QSize(20, 20)
        check_pixmap = create_colored_pixmap(svg_path=get_icon_path('check'),color=check_color,size=icon_size)
        self.check_icon = QIcon(check_pixmap)
        disabled_pixmap = create_colored_pixmap(svg_path=get_icon_path('disabled'), color=disabled_color, size=icon_size)
        self.disabled_icon = QIcon(disabled_pixmap)
        # 设置按钮的图标大小
        self.setIconSize(icon_size)
        self.setFixedSize(20, 20)
        # 连接信号，当选中状态改变时，更新图标显示
        self.toggled.connect(self.update_icon)
        # 初始化一次图标
        self.update_icon(self.isChecked())

    def text(self) -> str:
        """供 create_form_layout 调用，以获取外部标签的文本"""
        return self._text_storage

    def setText(self, text: str):
        """供 create_form_layout 调用，以清空文本"""
        self._text_storage = text
        super().setText("")
    
    def setChecked(self, checked: bool):
        """重写setChecked，确保在设置状态后总是更新图标，无论信号是否被阻塞。"""
        super().setChecked(checked)
        self.update_icon()

    def update_icon(self, checked = None):
        """根据选中状态，显示或隐藏图标"""
        if not self.isEnabled():
            self.setIcon(self.disabled_icon)
        elif self.isChecked():
            self.setIcon(self.check_icon)
        else:
            self.setIcon(QIcon())

    def changeEvent(self, event):
        """重写changeEvent来响应状态变化"""
        super().changeEvent(event)
        # 当“启用/禁用”状态发生变化时
        if event.type() == QEvent.Type.EnabledChange:
            self.update_icon()