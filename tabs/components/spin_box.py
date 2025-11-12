from PySide6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from utils.icon_utils import get_icon_path, create_colored_pixmap
class CustomSpinBox(QWidget):
    """自定义SpinBox"""
    valueChanged = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self._min = 0
        self._max = 99999
        self._step = 1
        self._color_normal = "#BEBEBE"
        self._color_hover = "#FFFFFF"
        self._icon_size_normal = QSize(14, 14)
        self._icon_size_hover = QSize(18, 18)
        # 预创建Pixmap
        minus_icon_path = get_icon_path('arrow_left')
        plus_icon_path = get_icon_path('arrow_right')
        self.minus_pixmap_normal = create_colored_pixmap(minus_icon_path, self._color_normal, self._icon_size_normal)
        self.minus_pixmap_hover = create_colored_pixmap(minus_icon_path, self._color_hover, self._icon_size_hover)
        self.plus_pixmap_normal = create_colored_pixmap(plus_icon_path, self._color_normal, self._icon_size_normal)
        self.plus_pixmap_hover = create_colored_pixmap(plus_icon_path, self._color_hover, self._icon_size_hover)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setMouseTracking(True)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.setSpacing(0)
        # 为按钮设置不同的对象名以便QSS能区分它们
        self.decr_button = QPushButton()
        self.decr_button.setObjectName("SpinBoxDecrButton")
        self.incr_button = QPushButton()
        self.incr_button.setObjectName("SpinBoxIncrButton")
        self.line_edit = QLineEdit(str(self._value))
        self.line_edit.setReadOnly(True)
        for btn in [self.decr_button, self.incr_button]:
            btn.setFixedWidth(28)
            btn.setMouseTracking(True)
        self.line_edit.setObjectName("SpinBoxLineEdit")
        self.line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.line_edit.setMouseTracking(True)
        # 图标
        self.decr_button.setIcon(QIcon(self.minus_pixmap_normal))
        self.incr_button.setIcon(QIcon(self.plus_pixmap_normal))
        self.decr_button.setIconSize(self._icon_size_hover)
        self.incr_button.setIconSize(self._icon_size_hover)
        # 添加到布局
        layout.addWidget(self.decr_button)
        layout.addWidget(self.line_edit, 1)
        layout.addWidget(self.incr_button)
        # 连接信号
        self.decr_button.clicked.connect(self._decrement)
        self.incr_button.clicked.connect(self._increment)
        # 为所有三个子控件安装事件过滤器
        self.decr_button.installEventFilter(self)
        self.incr_button.installEventFilter(self)
        self.line_edit.installEventFilter(self)

    def _update_hover_state(self, state):
        """统一更新悬浮状态并刷新样式"""
        if self.property("hoverState") != state:
            self.setProperty("hoverState", state)
            # 刷新自身及所有子控件的样式
            self.style().unpolish(self)
            self.style().polish(self)
            for child in self.findChildren(QWidget):
                 self.style().unpolish(child)
                 self.style().polish(child)

    def eventFilter(self, obj, event):
        """事件过滤器，用于控制整个控件的悬浮状态"""
        # 悬浮只作用于按钮
        if obj is self.decr_button or obj is self.incr_button:
            shape = 'minus' if obj is self.decr_button else 'plus'
            pixmap_normal = self.minus_pixmap_normal if shape == 'minus' else self.plus_pixmap_normal
            pixmap_hover = self.minus_pixmap_hover if shape == 'minus' else self.plus_pixmap_hover
            if event.type() == QEvent.Type.Enter:
                obj.setIcon(QIcon(pixmap_hover))
                hover_state = "left" if obj is self.decr_button else "right"
                self._update_hover_state(hover_state) # 设置父容器的渐变
                self.line_edit.setProperty("parentButtonHovered", True)
                self.line_edit.style().polish(self.line_edit)
                return True
            elif event.type() == QEvent.Type.Leave:
                obj.setIcon(QIcon(pixmap_normal))
                # 注意：离开按钮时，由父控件的leaveEvent统一处理状态清除
                return True
        # 输入框事件
        if obj is self.line_edit:
            # 当鼠标进入输入框区域时，立即取消渐变效果
            if event.type() == QEvent.Type.Enter:
                self._update_hover_state("none")
                self.line_edit.setProperty("parentButtonHovered", False)
                self.line_edit.style().polish(self.line_edit)
            # 处理焦点事件
            if event.type() == QEvent.Type.FocusIn:
                self.setProperty("hasFocus", True)
                self.style().polish(self)
            elif event.type() == QEvent.Type.FocusOut:
                self.setProperty("hasFocus", False)
                self.style().polish(self)
        return super().eventFilter(obj, event)

    def leaveEvent(self, event):
        """当鼠标离开整个控件时，清除所有悬浮效果"""
        self.decr_button.setIcon(QIcon(self.minus_pixmap_normal))
        self.incr_button.setIcon(QIcon(self.plus_pixmap_normal))
        self._update_hover_state("none")
        self.line_edit.setProperty("parentButtonHovered", False)
        self.line_edit.style().polish(self.line_edit)
        super().leaveEvent(event)
    
    def _decrement(self):
        self.line_edit.setFocus() # 点击按钮时让输入框获得焦点
        self.setValue(self._value - self._step)

    def _increment(self):
        self.line_edit.setFocus() # 点击按钮时让输入框获得焦点
        self.setValue(self.value() + self._step)

    # 返回值的辅助函数
    def value(self): return self._value
    # 更新值
    def setValue(self, value):
        new_value = max(self._min, min(value, self._max))
        if self._value == new_value and self.line_edit.text() == str(new_value): return
        self._value = new_value
        self.line_edit.setText(str(self._value))
        self.valueChanged.emit(self._value)
    # 设置最大最小值
    def setRange(self, min_val, max_val):
        self._min, self._max = min_val, max_val
        self.setValue(self.value())
    # 设置步长
    def setSingleStep(self, step): self._step = step