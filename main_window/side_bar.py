# 侧边栏控件
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Signal
from main_window.side_bar_button import SideBarButton

class SideBar(QWidget):
    index_changed = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SideBar")
        self.setFixedWidth(80) # 侧边栏宽度
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 15, 0, 0)
        self.main_layout.setSpacing(1) # 按钮间的垂直间距
        self._buttons = []
        # 在所有未来按钮的下方，预先放置一个弹簧
        self.main_layout.addStretch()

    def add_button(self, icon_path: str, text: str):
        """向侧边栏添加一个新按钮"""
        button = SideBarButton(icon_path, text, self)
        index = len(self._buttons)
        button.clicked.connect(lambda: self.on_button_clicked(index))
        # 将按钮插入到弹簧的前面
        self.main_layout.insertWidget(self.main_layout.count() - 1, button)
        self._buttons.append(button)

    def on_button_clicked(self, index: int):
        """处理按钮点击事件"""
        # 遍历所有按钮
        for i, btn in enumerate(self._buttons):
            # 判断当前遍历的按钮是否是刚刚被点击的按钮
            is_active = (i == index)
            btn.set_active(is_active)
        # 发送被点击按钮的索引信号
        self.index_changed.emit(index)

    def set_initial_checked(self, index: int):
        """设置初始选中的按钮"""
        if 0 <= index < len(self._buttons):
            # 直接调用点击处理函数来设置初始状态
            self.on_button_clicked(index)