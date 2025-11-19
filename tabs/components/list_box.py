from PySide6.QtWidgets import QListWidget, QAbstractItemView, QListView
from PySide6.QtCore import Qt, Signal, QSize

class ListBox(QListWidget):
    """基础舰船列表控件，支持拖拽、选择、查找等功能"""
    def __init__(self, parent=None):
        """初始化控件，设置拖拽和选择模式"""
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._drag_start_on_item = False

    def contextMenuEvent(self, event):
        """禁用右键菜单"""
        pass

    def mousePressEvent(self, event):
        """记录拖拽起点是否在项目上"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_on_item = self.itemAt(event.pos()) is not None
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """禁用空白区域框选"""
        if event.buttons() & Qt.MouseButton.LeftButton and not self._drag_start_on_item:
            return
        super().mouseMoveEvent(event)

    def find_items(self, text):
        """精确查找项目"""
        return self.findItems(text, Qt.MatchFlag.MatchExactly)

    def startDrag(self, supportedActions):
        """拖拽操作，支持信号连接"""
        drag = super().startDrag(supportedActions)
        if drag:
            drag.finished.connect(self._on_drag_finished)
        return drag

    def _on_drag_finished(self, action):
        """拖拽取消时恢复项目"""
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


class BaseSourceList(ListBox):
    """所有源列表的基类，提供统一的拖拽和样式管理"""
    contentChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)  # 允许拖回删除
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setGridSize(QSize(116, 30))

    def _update_all_item_sizes(self):
        """统一的项目尺寸更新逻辑"""
        grid_size = self.gridSize()
        for i in range(self.count()):
            item = self.item(i)
            item.setSizeHint(grid_size)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def addItem(self, item):
        """重写 addItem，在添加单个项目后更新尺寸"""
        super().addItem(item)
        self._update_all_item_sizes()

    def addItems(self, labels):
        """重写 addItems，在添加多个项目后更新尺寸"""
        super().addItems(labels)
        self._update_all_item_sizes()

    def startDrag(self, supportedActions):
        """拖拽为复制操作"""
        return super().startDrag(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        """接受来自目标列表的拖回删除"""
        from_target_list = hasattr(event.source(), '_is_target_list')
        if from_target_list:
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理从目标列表拖回删除"""
        source = event.source()
        if hasattr(source, '_is_target_list'):
            # 从目标列表拖回，删除源列表中的对应项目
            item_texts = [item.text() for item in source.selectedItems()]
            for text in item_texts:
                if items_to_remove := source.find_items(text):
                    row = source.row(items_to_remove[0])
                    source.takeItem(row)
            if hasattr(source, 'contentChanged'):
                source.contentChanged.emit()
            event.accept()
        else:
            event.ignore()


class BaseTargetList(ListBox):
    """所有目标列表的基类"""
    contentChanged = Signal()
    
    def __init__(self, parent=None, max_items=0, allow_internal_move=True, 
                 allow_same_type_exchange=False, unique_in_same_type=False,
                 enable_smart_swap=False):
        super().__init__(parent)
        self._is_target_list = True  # 标记为目标列表
        self.max_items = max_items  # 0=无限制，1=单元素
        self.allow_internal_move = allow_internal_move
        self.allow_same_type_exchange = allow_same_type_exchange
        self.unique_in_same_type = unique_in_same_type
        self.enable_smart_swap = enable_smart_swap  # 智能交换开关
        
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setSpacing(3)
        
        if allow_internal_move:
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        else:
            self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)

    def _update_item_sizes(self):
        """统一的目标列表项目尺寸更新"""
        fm = self.fontMetrics()
        horizontal_padding = 22
        fixed_height = 22
        for i in range(self.count()):
            item = self.item(i)
            text_width = fm.boundingRect(item.text()).width()
            item.setSizeHint(QSize(text_width + horizontal_padding, fixed_height))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def addItem(self, item):
        """重写 addItem，在添加后更新尺寸"""
        super().addItem(item)
        self._update_item_sizes()
        
    def addItems(self, labels):
        """重写 addItems，在添加后更新尺寸"""
        super().addItems(labels)
        self._update_item_sizes()

    def dragEnterEvent(self, event):
        """统一的拖拽进入处理"""
        source = event.source()
        # 接受来自源列表的拖拽
        if isinstance(source, BaseSourceList):
            event.acceptProposedAction()
            return
        # 接受来自同类目标列表的交换（如果允许）
        if (self.allow_same_type_exchange and 
            isinstance(source, BaseTargetList) and 
            source != self):
            event.acceptProposedAction()
            return
        # 接受内部移动（如果允许）
        if self.allow_internal_move and source == self:
            event.acceptProposedAction()
            return
            
        event.ignore()

    def dropEvent(self, event):
        """统一的拖放处理"""
        source = event.source()
        # 从源列表复制
        if isinstance(source, BaseSourceList):
            if self._can_accept_from_source(source):
                self._handle_drop_from_source(source, event)
            else:
                event.ignore()   
        # 同类目标列表间交换
        elif (self.allow_same_type_exchange and 
              isinstance(source, BaseTargetList) and 
              source != self):
            self._handle_exchange_with_same_type(source, event)
        # 内部移动
        elif self.allow_internal_move and source == self:
            super().dropEvent(event)
            self.contentChanged.emit()
        else:
            event.ignore()

    def _can_accept_from_source(self, source):
        """检查是否可以从源列表接受项目"""
        if self.max_items == 1 and self.count() >= 1:
            return False
            
        item_texts = [item.text() for item in source.selectedItems()]
        
        # 检查唯一性约束
        if self.unique_in_same_type:
            # 查找同类型的其他列表并检查唯一性
            parent_widget = self.parent()
            if hasattr(parent_widget, 'fleet_lists'):
                for target_list in parent_widget.fleet_lists:
                    # 检查同类型且不是自己的列表
                    if (target_list != self and 
                        hasattr(target_list, 'list_type') and 
                        target_list.list_type == self.list_type):
                        for text in item_texts:
                            if target_list.find_items(text):
                                return False
                        
        return True

    def _handle_drop_from_source(self, source, event):
        """处理从源列表的拖放，支持智能交换"""
        if not self.enable_smart_swap:
            # 使用默认的拖拽复制逻辑
            item_texts = [item.text() for item in source.selectedItems()]
            # 单元素目标列表的特殊处理
            if self.max_items == 1:
                self.clear()

            for text in item_texts:
                self.addItem(text)

            event.accept()
            self.contentChanged.emit()
            return
        
        dropped_item_texts = [item.text() for item in source.selectedItems()]
        # 使用新的方法获取同类列表
        if hasattr(self, '_get_same_type_lists'):
            same_type_lists = self._get_same_type_lists()
        else:
            # 回退到原有逻辑
            parent_widget = self.parent()
            same_type_lists = []
            if hasattr(parent_widget, 'fleet_lists'):
                for target_list in parent_widget.fleet_lists:
                    if (hasattr(target_list, 'list_type') and 
                        target_list.list_type == self.list_type):
                        same_type_lists.append(target_list)
            elif hasattr(parent_widget, 'drop_zones'):
                same_type_lists = parent_widget.drop_zones
        # 对于每个拖拽的项目，检查是否已存在于同类列表中
        for dropped_text in dropped_item_texts:
            # 从所有同类列表中移除重复项
            for same_type_list in same_type_lists:
                if same_type_list != self:
                    items_to_remove = same_type_list.find_items(dropped_text)
                    for item in items_to_remove:
                        same_type_list.takeItem(same_type_list.row(item))
                    if items_to_remove:
                        same_type_list.contentChanged.emit()
            # 添加到当前列表（如果不存在）
            if not self.find_items(dropped_text):
                self.addItem(dropped_text)
        event.accept()
        self.contentChanged.emit()

    def _handle_exchange_with_same_type(self, source, event):
        """处理与同类目标列表的交换"""
        item_texts = [item.text() for item in source.selectedItems()]
        # 检查目标列表是否可以接受这些项目
        for text in item_texts:
            if self.find_items(text):  # 目标列表已存在该项目
                event.ignore()
                return
        # 执行交换：从源列表移除，添加到目标列表
        for text in item_texts:
            if items := source.find_items(text):
                row = source.row(items[0])
                item = source.takeItem(row)
                self.addItem(item.text())
        event.accept()
        source.contentChanged.emit()
        self.contentChanged.emit()
    
    def showEvent(self, event):
        """当控件显示时重新计算尺寸"""
        super().showEvent(event)
        if self.count() > 0:
            self._update_item_sizes()