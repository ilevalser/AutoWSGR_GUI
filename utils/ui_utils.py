from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel, QGridLayout, QWidget, QLayout, QPushButton
from PySide6.QtCore import Qt, QObject, Signal
import re

def create_group(title=None, content=None, margins=(15,15,15,0)):
    """
    用于创建带标准样式、边距、可选标题和分割线的设置组框架的辅助函数
    :param title: 组的标题，如果为 None，则不创建标题和分割线
    :param content: 一个 QLayout 或 QWidget 对象
    :return: 一个配置完成的 QFrame 控件
    """
    # 创建最外层的框架，并设置对象名以便应用QSS样式
    frame = QFrame()
    frame.setObjectName("SettingsGroupFrame")
    # 创建框架的垂直布局
    group_layout = QVBoxLayout(frame)
    group_layout.setContentsMargins(*margins)
    group_layout.setSpacing(10)
    # 如果提供了标题，则添加标题和分割线
    if title:
        title_label = QLabel(title)
        title_label.setObjectName("SettingsGroupTitle")
        group_layout.addWidget(title_label)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("SeparatorLine")
        group_layout.addWidget(line)
    # 如果提供了内容布局，则将其添加到框架中
    if content:
        if isinstance(content, QLayout):
            group_layout.addLayout(content)
        elif isinstance(content, QWidget):
            # 如果是控件，则直接添加该控件
            group_layout.addWidget(content)
    return frame

def create_form_layout(items_info, column_stretches=(4, 2, 3), track_widgets=False):
    """
    创建标准表单（左标签、右控件、可选的下方描述）的网格布局的辅助函数。
    此版本只接受字典格式的输入。

    :param items_info: 描述表单项的字典列表。
    :param column_stretches: (tuple) 每列的拉伸因子
    :param track_widgets: (bool) 如果为True，则额外返回一个包含所有已创建控件引用的字典
    :return: QGridLayout 或 (QGridLayout, dict)
    """
    content_grid = QGridLayout()
    content_grid.setContentsMargins(0, 5, 0, 5)
    content_grid.setVerticalSpacing(5)
    content_grid.setHorizontalSpacing(0)

    # 如果需要跟踪，则初始化字典
    widget_rows = {} if track_widgets else None

    num_columns = len(column_stretches)
    for i, stretch in enumerate(column_stretches):
        content_grid.setColumnStretch(i, stretch)

    current_row = 0
    for item in items_info:
        widget_info = item.get('widget')
        description = item.get('description')
        extra_widget = item.get('extra_widget')
        key = item.get('key')  # 获取用于跟踪的键

        # 初始化当前行的控件列表（如果需要跟踪）
        current_row_widgets = [] if track_widgets else None

        # 根据列数决定布局模式
        if num_columns == 2:
            # 两列布局
            if isinstance(widget_info, tuple):
                label, control = widget_info
                label.setObjectName("FormLabel")
                content_grid.addWidget(label, current_row, 0, Qt.AlignmentFlag.AlignLeft)
                content_grid.addWidget(control, current_row, 1)
                if track_widgets: current_row_widgets.extend([label, control])
            else: # 假设是 CustomCheckBox
                checkbox = widget_info
                # 标签是在函数内部创建的
                label = QLabel(checkbox.text())
                label.setObjectName("FormLabel")
                content_grid.addWidget(label, current_row, 0, Qt.AlignmentFlag.AlignLeft)
                content_grid.addWidget(checkbox, current_row, 1, Qt.AlignmentFlag.AlignCenter)
                if track_widgets: current_row_widgets.extend([label, checkbox])
        else: # 默认三列布局
            # (三列布局逻辑保持不变，同样增加跟踪)
            if isinstance(widget_info, tuple):
                label, control = widget_info
                label.setObjectName("FormLabel")
                content_grid.addWidget(label, current_row, 0, Qt.AlignmentFlag.AlignLeft)
                content_grid.addWidget(control, current_row, 2)
                if track_widgets: current_row_widgets.extend([label, control])
            else:
                checkbox = widget_info
                label = QLabel(checkbox.text())
                label.setObjectName("FormLabel")
                content_grid.addWidget(label, current_row, 0, Qt.AlignmentFlag.AlignLeft)
                content_grid.addWidget(checkbox, current_row, 2, Qt.AlignmentFlag.AlignCenter)
                if track_widgets: current_row_widgets.extend([label, checkbox])
        
        next_row_offset = 1

        if extra_widget:
            content_grid.addWidget(extra_widget, current_row + next_row_offset, 0, 1, num_columns)
            if track_widgets: current_row_widgets.append(extra_widget)
            next_row_offset += 1
            
        if description:
            desc_label = QLabel(description)
            desc_label.setObjectName("DescriptionLabel")
            desc_label.setWordWrap(True)
            content_grid.addWidget(desc_label, current_row + next_row_offset, 0, 1, num_columns)
            if track_widgets: current_row_widgets.append(desc_label)
            next_row_offset += 1

        if track_widgets and key:
            widget_rows[key] = current_row_widgets

        current_row += next_row_offset

    if track_widgets:
        return content_grid, widget_rows
    else:
        return content_grid

def natural_sort_key(text):
    """为字符串生成一个自然排序的键。"""
    def try_int(s):
        try:
            return int(s)
        except (TypeError, ValueError):
            return s
            
    return [try_int(c) for c in re.split('([0-9]+)', str(text))]


def create_ok_cancel_buttons():
    """
    创建一组标准的“确认”和“取消”按钮。

    :return: 一个包含 (confirm_button, cancel_button) 的元组。
    """
    confirm_button = QPushButton("确认")
    confirm_button.setProperty("class", "OkCancelButton")
    cancel_button = QPushButton("取消")
    cancel_button.setProperty("class", "OkCancelButton")

    return confirm_button, cancel_button

class ConfirmButtonManager(QObject):
    """为一个QPushButton提供二次点击确认功能。"""
    confirmed_click = Signal()

    def __init__(self, button: QPushButton, confirm_text: str = "再次点击", 
                 pre_condition_check: callable = None, parent: QObject = None):
        super().__init__(parent)
        
        self.button = button
        self.confirm_text = confirm_text
        self.pre_condition_check = pre_condition_check
        self._original_text = self.button.text()
        
        self.button.clicked.connect(self._handle_click)

    def _handle_click(self):
        """处理按钮的点击事件。"""
        # 如果按钮已经处于二次确认状态，则直接发射信号
        if self.is_confirming():
            self.confirmed_click.emit()
            self.reset_state()
            return

        if self.pre_condition_check and not self.pre_condition_check():
            # 如果检查函数存在且返回False，则中止操作，不进入二次确认
            return
            
        self.button.setProperty("confirming", True)
        self._original_text = self.button.text()
        self.button.setText(self.confirm_text)
        self._force_style_update()

    def reset_state(self):
        """将按钮恢复到正常状态。"""
        if self.is_confirming():
            self.button.setProperty("confirming", False)
            self.button.setText(self._original_text)
            self._force_style_update()

    def is_confirming(self):
        """检查按钮是否处于确认状态。"""
        return self.button.property("confirming") == True

    def _force_style_update(self):
        """强制按钮刷新其视觉样式以响应属性变化。"""
        self.button.style().unpolish(self.button)
        self.button.style().polish(self.button)