from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QPushButton, QHeaderView, QTableWidgetItem, QApplication
)
from PySide6.QtCore import Qt, Signal, QEvent, Slot
from utils.ui_utils import ConfirmButtonManager

class ManagedListWidget(QWidget):
    """
    一个可管理的列表组件，封装了 QTableWidget、上移、下移和删除按钮
    及其相关的通用逻辑。
    
    通过 eventFilter 实现了以下特性:
    1. 点击空白处不取消选中。
    2. 点击已选中的行可以取消选中。
    3. 点击未选中的行可以选中。
    4. 删除后自动取消选中。
    """
    
    item_moved = Signal(int, int) 
    item_removed = Signal(int)
    selection_changed = Signal(int)

    def __init__(self, column_labels: list, parent=None):
        """
        初始化
        :param column_labels: 表格的列标题列表
        """
        super().__init__(parent)
        self.currently_selected_row = -1
        self._setup_ui(column_labels)
        self._connect_signals()
        self._update_buttons_state()

    def _setup_ui(self, column_labels: list):
        """构建UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(len(column_labels))
        self.table.setHorizontalHeaderLabels(column_labels)
        
        if len(column_labels) == 1:
            self.table.horizontalHeader().setStretchLastSection(True)
        else:
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
            
        self.table.verticalHeader().setVisible(True)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.table.setShowGrid(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionsClickable(False)
        self.table.verticalHeader().setSectionsClickable(False)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setHighlightSections(False)
        self.table.setCornerButtonEnabled(False)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)

        def ignore_drag_selection(event):
            if event.buttons() & Qt.MouseButton.LeftButton:
                return
            QTableWidget.mouseMoveEvent(self.table, event)
        self.table.mouseMoveEvent = ignore_drag_selection

        # 安装事件过滤器以实现所有点击逻辑
        self.table.viewport().installEventFilter(self)
        layout.addWidget(self.table)
        
        # 按钮
        self.move_up_btn = QPushButton("上移一行")
        self.move_down_btn = QPushButton("下移一行")
        self.remove_btn = QPushButton("删除选中")
        self.move_up_btn.setProperty("class", "ShortButton")
        self.move_down_btn.setProperty("class", "ShortButton")
        self.remove_btn.setProperty("class", "ShortButton")

        # 删除确认管理器
        self.confirm_delete_manager = ConfirmButtonManager(
            self.remove_btn, "确认删除",
            lambda: self.currently_selected_row >= 0
        )
        
        # 按钮布局
        self.button_layout = QHBoxLayout()
        self.button_layout.addWidget(self.move_up_btn)
        self.button_layout.addWidget(self.move_down_btn)
        self.button_layout.addWidget(self.remove_btn)
        
        layout.addLayout(self.button_layout)

    def _connect_signals(self):
        """连接信号"""
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.confirm_delete_manager.confirmed_click.connect(self._on_remove_row)
        self.move_up_btn.clicked.connect(lambda: self._on_move_row(-1))
        self.move_down_btn.clicked.connect(lambda: self._on_move_row(1))

    def eventFilter(self, watched, event: QEvent):
        """事件过滤器，处理所有点击逻辑"""
        if watched == self.table.viewport() and event.type() == QEvent.Type.MouseButtonPress:
            # 获取点击位置的索引
            index = self.table.indexAt(event.pos())
            if not index.isValid(): return True # 点击在空白处拦截事件
                
            clicked_row = index.row()
            if clicked_row == self.currently_selected_row:
                self.table.clearSelection() # 点击在已选中的行手动取消选中
                return True
            # 点击在未选中的行放行事件
            return False 
        return super().eventFilter(watched, event)

    def process_global_event(self, event: QEvent):
        """由父窗口的 eventFilter 调用，用于处理全局点击事件"""
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.confirm_delete_manager.is_confirming():
                clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())
                is_on_remove_button = clicked_widget and (self.remove_btn == clicked_widget or self.remove_btn.isAncestorOf(clicked_widget))
                if not is_on_remove_button:
                    self.confirm_delete_manager.reset_state()
    
    # --- 内部槽函数 ---
    def _on_selection_changed(self):
        """处理表格选择变化"""
        selected_rows = self.table.selectionModel().selectedRows()
        new_row = -1
        if selected_rows:
            new_row = selected_rows[0].row()
        # 仅在选择真正改变时才发出信号和更新
        if new_row != self.currently_selected_row:
            self.currently_selected_row = new_row
            self.selection_changed.emit(self.currently_selected_row)
            self._update_buttons_state()

    @Slot()
    def _on_remove_row(self):
        """处理删除按钮点击"""
        row = self.currently_selected_row
        if row >= 0:
            self.table.removeRow(row)
            self.item_removed.emit(row)
            # 删除后取消所有选中
            self.table.clearSelection() 

    def _on_move_row(self, direction: int):
        """处理上移或下移"""
        current_row = self.currently_selected_row
        new_row = current_row + direction
        
        if not (0 <= current_row < self.table.rowCount() and \
                0 <= new_row < self.table.rowCount()):
            return

        items = []
        for col in range(self.table.columnCount()):
            items.append(self.table.takeItem(current_row, col))
        self.table.removeRow(current_row)
        self.table.insertRow(new_row)
        
        for col, item in enumerate(items):
            self.table.setItem(new_row, col, item)
        # 保持选中
        self.table.setCurrentCell(new_row, 0)
        self.item_moved.emit(current_row, new_row)
        self._update_buttons_state() # 立即更新按钮（到了顶部/底部）
        self.table.setFocus()

    def _update_buttons_state(self):
        """根据选择状态更新按钮可用性"""
        has_selection = self.currently_selected_row >= 0
        row_count = self.table.rowCount()

        self.remove_btn.setEnabled(has_selection)
        self.move_up_btn.setEnabled(has_selection and self.currently_selected_row > 0)
        self.move_down_btn.setEnabled(has_selection and self.currently_selected_row < row_count - 1)

    # --- 公共API方法 ---

    def set_table_data(self, data: list[list[QTableWidgetItem]]):
        self.table.clearSelection() 
        self.table.setRowCount(0) 
        for row_items in data:
            self.add_table_row(row_items)
        
        if self.currently_selected_row != -1:
            self.currently_selected_row = -1
            self.selection_changed.emit(-1)
            self._update_buttons_state()

    def add_table_row(self, items: list[QTableWidgetItem]):
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)
        for col, item in enumerate(items):
            self.table.setItem(row_count, col, item)

    def edit_table_row(self, row: int, items: list[QTableWidgetItem]):
        if not (0 <= row < self.table.rowCount()):
            return
        for col, item in enumerate(items):
            self.table.setItem(row, col, item)

    def get_current_row(self) -> int:
        return self.currently_selected_row

    def get_row_count(self) -> int:
        return self.table.rowCount()

    def get_item(self, row, col) -> QTableWidgetItem | None:
        return self.table.item(row, col)

    def get_item_data(self, row, col, role=Qt.ItemDataRole.UserRole):
        item = self.get.item(row, col)
        return item.data(role) if item else None

    def clear_selection(self):
        self.table.clearSelection()