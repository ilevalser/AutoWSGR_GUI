from PySide6.QtWidgets import QListWidget, QAbstractItemView
from PySide6.QtCore import Qt

class ListBox(QListWidget):
    """基础舰船列表控件，支持拖拽、选择、查找等功能。"""
    def __init__(self, parent=None):
        """初始化控件，设置拖拽和选择模式。"""
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._drag_start_on_item = False

    def contextMenuEvent(self, event):
        """禁用右键菜单。"""
        pass

    def mousePressEvent(self, event):
        """记录拖拽起点是否在项目上。"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_on_item = self.itemAt(event.pos()) is not None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """禁用空白区域框选。"""
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_start_on_item:
            return
        super().mouseMoveEvent(event)

    def find_items(self, text):
        """精确查找项目。"""
        return self.findItems(text, Qt.MatchFlag.MatchExactly)

    def startDrag(self, supportedActions):
        """拖拽操作，支持信号连接。"""
        drag = super().startDrag(supportedActions)
        if drag:
            drag.finished.connect(self._on_drag_finished)
        return drag

    def _on_drag_finished(self, action):
        """拖拽取消时恢复项目。"""
        if action == Qt.DropAction.IgnoreAction:
            selected = self.selectedItems()
            if selected:
                for item in selected:
                    if not self.find_items(item.text()):
                        self.addItem(item.text())
                for item in selected:
                    items = self.find_items(item.text())
                    if items:
                        items[0].setSelected(True)