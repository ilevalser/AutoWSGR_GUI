from PySide6.QtWidgets import QPushButton, QListWidget, QListWidgetItem, QApplication, QAbstractItemView, QLabel, QHBoxLayout, QWidget
from PySide6.QtCore import Qt, Signal, QSize, QPoint, QEvent
from utils.icon_utils import get_icon_path, create_colored_pixmap

class CustomComboBox(QPushButton):
    currentIndexChanged = Signal(int)
    currentTextChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_index = -1
        self._popup_visible = False
        self.setObjectName("DisplayButton")
        button_layout = QHBoxLayout(self) # 布局直接设置在 self 上
        button_layout.setContentsMargins(5, 0, 5, 0)
        self.text_label = QLabel("---")
        self.text_label.setObjectName("DisplayText")
        # 让标签不捕获鼠标事件，确保父按钮能接收所有事件
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.icon_label = QLabel()
        self.icon_label.setFixedWidth(18)
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        button_layout.addWidget(self.text_label, 1)
        button_layout.addWidget(self.icon_label)
        # 弹出的列表控件
        self.list_widget = QListWidget(self)
        self.list_widget.setObjectName("PopupList")
        self.list_widget.setWindowFlags(Qt.WindowType.Popup)
        # 图标相关的代码
        color_normal = "#BEBEBE"
        color_hover = "#FFFFFF"
        arrow_icon_path = get_icon_path('arrow_down')
        self.arrow_pixmap_normal = create_colored_pixmap(arrow_icon_path, color_normal, QSize(14, 14))
        self.arrow_pixmap_hover = create_colored_pixmap(arrow_icon_path, color_hover, QSize(18, 18))
        self.icon_label.setPixmap(self.arrow_pixmap_normal)
        # 信号连接
        self.clicked.connect(self._show_popup)
        self.list_widget.itemClicked.connect(self._on_item_selected)
        # 全局事件过滤器，用于处理点击外部关闭弹窗的逻辑
        self.global_event_filter = GlobalEventFilter(self, self.list_widget, self._hide_popup)

    # enterEvent 和 leaveEvent 用于手动处理图标变化
    def enterEvent(self, event):
        super().enterEvent(event)
        self.icon_label.setPixmap(self.arrow_pixmap_hover)
    def leaveEvent(self, event):
        super().leaveEvent(event)
        # 只有在弹窗不可见时，离开才恢复正常图标
        if not self._popup_visible:
            self.icon_label.setPixmap(self.arrow_pixmap_normal)

    def _show_popup(self):
        if self._popup_visible:
            self._hide_popup() # 如果已打开，再次点击则关闭
            return
        self._popup_visible = True
        self.setProperty("state", "on") # 用于QSS，例如让边框持续高亮
        self.style().polish(self)
        self.icon_label.setPixmap(self.arrow_pixmap_hover) # 打开时图标保持高亮
        # 弹窗定位和显示逻辑
        item_height = self.list_widget.sizeHintForRow(0) if self.count() > 0 else 30
        visible_items = min(self.count(), 10)
        popup_height = item_height * visible_items + 2 * self.list_widget.frameWidth()
        self.list_widget.setFixedHeight(popup_height)
        global_pos = self.mapToGlobal(QPoint(0, self.height()))
        self.list_widget.move(global_pos)
        self.list_widget.setFixedWidth(self.width())
        self.list_widget.show()
        if self._current_index >= 0:
            self.list_widget.scrollToItem(self.list_widget.item(self._current_index), QAbstractItemView.ScrollHint.PositionAtCenter)
        # 安装全局事件过滤器
        QApplication.instance().installEventFilter(self.global_event_filter)

    def _hide_popup(self):
        if not self._popup_visible:
            return
        self._popup_visible = False
        self.list_widget.hide()
        self.setProperty("state", "off")
        self.style().polish(self)
        # 弹窗关闭后，如果鼠标不在按钮上，恢复图标
        if not self.underMouse():
            self.icon_label.setPixmap(self.arrow_pixmap_normal)
        # 移除全局事件过滤器
        QApplication.instance().removeEventFilter(self.global_event_filter)
        
    def _on_item_selected(self, item: QListWidgetItem):
        row = self.list_widget.row(item)
        self.setCurrentIndex(row)
        self._hide_popup()

    # 公共API
    def addItem(self, text, userData=None):
        item = QListWidgetItem(text)
        if userData is not None: item.setData(Qt.ItemDataRole.UserRole, userData)
        self.list_widget.addItem(item)
        if self._current_index == -1 and self.count() > 0: self.setCurrentIndex(0)
    def addItems(self, texts): [self.addItem(text) for text in texts]
    def count(self): return self.list_widget.count()
    def currentIndex(self): return self._current_index
    def currentText(self): return "" if self._current_index == -1 else self.text_label.text()
    def currentData(self): return None if self._current_index == -1 else self.list_widget.item(self._current_index).data(Qt.ItemDataRole.UserRole)
    def clear(self):
        self.list_widget.clear()
        self.text_label.setText("---")
        self._current_index = -1
    def setCurrentIndex(self, index):
        if not (0 <= index < self.count()): return
        self.list_widget.setCurrentRow(index)
        old_index, self._current_index = self._current_index, index
        item = self.list_widget.item(index)
        if old_index != index:
            self.text_label.setText(item.text())
            self.currentIndexChanged.emit(index)
            self.currentTextChanged.emit(item.text())
    def setCurrentText(self, text):
        for i in range(self.count()):
            if self.list_widget.item(i).text() == text:
                self.setCurrentIndex(i); return

    def findText(self, text, flags=Qt.MatchFlag.MatchExactly):
        """查找给定文本项的索引"""
        for i in range(self.count()):
            item_text = self.list_widget.item(i).text()
            if (flags & Qt.MatchFlag.MatchExactly and item_text == text) or \
               (flags & Qt.MatchFlag.MatchStartsWith and item_text.startswith(text)) or \
               (flags & Qt.MatchFlag.MatchEndsWith and item_text.endswith(text)) or \
               (flags & Qt.MatchFlag.MatchContains and text in item_text) or \
               (flags & Qt.MatchFlag.MatchCaseSensitive and item_text == text) or \
               (not (flags & Qt.MatchFlag.MatchCaseSensitive) and item_text.lower() == text.lower()):
                return i
        return -1
    # 用于居中文本
    def get_icon_width(self):
        return self.icon_label.width()

# 一个辅助类，用于处理点击外部关闭弹窗的逻辑
class GlobalEventFilter(QWidget):
    def __init__(self, button, popup, hide_callback):
        super().__init__()
        self.button = button
        self.popup = popup
        self.hide_callback = hide_callback
    
    def eventFilter(self, obj, event):
        # 只关心鼠标按键按下的事件
        if event.type() == QEvent.Type.MouseButtonPress:
            widget_at_pos = QApplication.widgetAt(event.globalPosition().toPoint())
            # 点击是否发生在内部
            parent = widget_at_pos
            while parent is not None:
                if parent == self.popup:
                    # 如果是则不处理，让列表自身响应点击
                    return False
                parent = parent.parent()
            # 点击是否发生在父按钮
            parent = widget_at_pos
            while parent is not None:
                if parent == self.button:
                    # 是，则关闭弹窗并消费事件(return True)，防止按钮再次打开弹窗
                    self.hide_callback()
                    return True
                parent = parent.parent()
            # 点击发生在控件外部，关闭弹窗
            self.hide_callback()
            # 不消费事件，让窗口其他部分能响应点击
            return False
        # 对于其他类型的事件不进行处理
        return False