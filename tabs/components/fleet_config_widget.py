from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QLabel, QPushButton, QLineEdit, QListView,
    QButtonGroup, QAbstractItemView, QApplication
)
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from constants import ALL_SS_NAME
from tabs.components.list_box import ListBox
from utils.ui_utils import ConfirmButtonManager, natural_sort_key

# =========================
# 可用舰船列表
# =========================
class SourceShipList(ListBox):
    """可用舰船列表控件，支持拖拽到舰队列表和自定义筛选。"""
    contentChanged = Signal()

    def __init__(self, parent=None):
        """初始化控件，设置显示模式和拖拽模式。"""
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(True)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setGridSize(QSize(116, 30))
        self.setDropIndicatorShown(False)
        self._press_pos = None
        self._item_pressed = None
        self._was_selected_on_press = False

    def mousePressEvent(self, event):
        """重写鼠标按下事件，在 mouseReleaseEvent 中判断是单击还是拖拽。"""
        # 记录下可能被操作的项和位置
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_pos = event.pos()
            self._item_pressed = self.itemAt(self._press_pos)
            
            if self._item_pressed:
                self._was_selected_on_press = self._item_pressed.isSelected()
            else:
                self._was_selected_on_press = False
    
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """
        重写鼠标抬起事件，通过判断鼠标移动距离来区分单击和拖拽。"""
        # 仅当按下和抬起都是左键，且确实按到了一个项目上时才处理
        if (self._item_pressed and self._press_pos and
                event.button() == Qt.MouseButton.LeftButton):
            distance = (event.pos() - self._press_pos).manhattanLength()

            # 如果移动距离小于阈值
            if distance < QApplication.startDragDistance():
                item_at_release = self.itemAt(event.pos())
                # 确保抬起时仍然在该项目上，并且该项目是选中的
                if item_at_release == self._item_pressed and self._was_selected_on_press:
                    item_at_release.setSelected(False)

        super().mouseReleaseEvent(event)
        self._press_pos = None
        self._item_pressed = None
        self._was_selected_on_press = False

    def dragEnterEvent(self, event):
        """仅接受舰队列表拖入。"""
        if isinstance(event.source(), FleetShipList):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def startDrag(self, supportedActions):
        """拖拽为复制操作。"""
        return super().startDrag(Qt.DropAction.CopyAction)

    def dropEvent(self, event):
        """处理舰队列表拖回。"""
        source = event.source()
        if isinstance(source, FleetShipList):
            item_texts = [item.text() for item in source.selectedItems()]
            for text in item_texts:
                if items_to_remove := source.find_items(text):
                    row = source.row(items_to_remove[0])
                    source.takeItem(row)
            source.contentChanged.emit()
            event.accept()
        else:
            event.ignore()

# =========================
# 舰队列表
# =========================
class FleetShipList(ListBox):
    """舰队列表控件，支持与可用舰船列表和其他舰队列表的拖拽交互。"""
    contentChanged = Signal()

    def __init__(self, parent_widget, list_type, parent=None):
        """初始化控件，设置显示和拖拽模式。"""
        super().__init__(parent)
        self.parent_widget = parent_widget
        self.list_type = list_type
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setUniformItemSizes(False)
        self.setSpacing(3)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._is_first_show = True

    def showEvent(self, event):
        """首次显示时更新项目尺寸。"""
        super().showEvent(event)
        if self._is_first_show:
            self._update_item_sizes()
            self._is_first_show = False

    def _update_item_sizes(self):
        """根据内容自适应项目尺寸。"""
        fm = self.fontMetrics()
        horizontal_padding = 22
        fixed_height = 22
        for i in range(self.count()):
            item = self.item(i)
            text_width = fm.boundingRect(item.text()).width()
            item.setSizeHint(QSize(text_width + horizontal_padding, fixed_height))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def startDrag(self, supportedActions):
        """拖拽为复制操作。"""
        return super().startDrag(Qt.DropAction.CopyAction)

    def dragEnterEvent(self, event):
        """拖拽进入规则，支持源列表和同类型舰队间拖拽。"""
        source = event.source()
        if isinstance(source, SourceShipList):
            event.acceptProposedAction()
            return
        if isinstance(source, FleetShipList):
            if source == self:
                event.acceptProposedAction()
                return
            if self.list_type == 'main_fleet' and source.list_type == 'main_fleet':
                event.acceptProposedAction()
                return
        event.ignore()

    def dropEvent(self, event):
        """拖拽释放规则，处理不同来源的拖拽。"""
        source = event.source()
        # 从源列表复制
        if isinstance(source, SourceShipList):
            item_texts = [item.text() for item in source.selectedItems()]
            for text in item_texts:
                if self.find_items(text):
                    event.ignore()
                    return
            for text in item_texts:
                if not self.find_items(text):
                    self.addItem(text)
            if self.list_type == 'main_fleet':
                for text in item_texts:
                    self.parent_widget.ensure_main_fleet_uniqueness(text, self)
            event.accept()
            self._update_item_sizes()
            self.contentChanged.emit()
        # 舰队间移动
        elif (isinstance(source, FleetShipList) and source != self and
              self.list_type == 'main_fleet' and source.list_type == 'main_fleet'):
            item_texts = [item.text() for item in source.selectedItems()]
            for text in item_texts:
                if self.find_items(text):
                    event.ignore()
                    return
            for text in item_texts:
                if items := source.find_items(text):
                    row = source.row(items[0])
                    item = source.takeItem(row)
                    self.addItem(item.text())
            if self.list_type == 'main_fleet':
                for text in item_texts:
                    self.parent_widget.ensure_main_fleet_uniqueness(text, self)
            event.accept()
            self._update_item_sizes()
            if isinstance(source, FleetShipList):
                source.contentChanged.emit()
            self.contentChanged.emit()
        # 内部排序
        elif source == self:
            self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
            super().dropEvent(event)
            self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)
            self._update_item_sizes()
            self.contentChanged.emit()
        else:
            event.ignore()

# =========================
# 舰队配置主控件（控制器/工厂）
# =========================
class FleetConfigWidget(QWidget):
    """舰队配置主控件，负责管理所有舰队列表、可用舰船列表及自定义舰船的增删改查。"""
    # 信号定义
    level1_fleet_changed = Signal(list)
    level2_fleet_changed = Signal(list)
    flagship_priority_changed = Signal(list)
    custom_ships_changed = Signal(list)
    log_message_signal = Signal(str)

    def __init__(self, initial_custom_ships=None, parent=None):
        """初始化控件，创建UI和数据，连接信号。"""
        super().__init__(parent)
        # 数据初始化
        self.all_ships_data = ALL_SS_NAME
        self.custom_ships = initial_custom_ships if initial_custom_ships else []
        # UI控件创建
        self._create_widgets()
        self.remove_button_manager = ConfirmButtonManager(self.remove_custom_ship_button)

        # UI布局与信号连接
        self._layout = self._setup_ui()
        self._connect_signals()
        self.custom_ship_input.installEventFilter(self)
        self._update_source_list_filter()

    def get_layout(self):
        """返回主布局。"""
        return self._layout

    def process_app_event(self, watched, event):
        """处理由父控件转发来的全局事件。"""
        if not self.isVisible():
            return False

        # 点击输入框时自动切换筛选
        if watched == self.custom_ship_input and event.type() == QEvent.Type.FocusIn:
            for button in self.filter_button_group.buttons():
                if button.text() == "自定义" and not button.isChecked():
                    button.click()
                    break

        # 处理全局鼠标点击事件
        if event.type() == QEvent.Type.MouseButtonPress:
            clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())

            # 检查点击是否发生在删除按钮上
            is_click_on_delete_button = self.remove_custom_ship_button.isAncestorOf(clicked_widget) or clicked_widget == self.remove_custom_ship_button

            # 检查点击是否发生在源列表上
            is_click_on_source_list = self.source_ships_list.isAncestorOf(clicked_widget) or clicked_widget == self.source_ships_list

            # 全局单选逻辑：当点击发生在列表外部且不是删除按钮时，清空选择
            if self.source_ships_list.selectedItems() and not is_click_on_source_list and not is_click_on_delete_button:
                self.source_ships_list.clearSelection()

            # 二次确认按钮重置逻辑
            if self.remove_button_manager.is_confirming() and not is_click_on_delete_button:
                self.remove_button_manager.reset_state()

        return False

    def _create_widgets(self):
        """创建所有UI控件。"""
        self.level1_list = FleetShipList(self, 'main_fleet')
        self.level1_list.setObjectName("Level1FleetList")
        self.level1_list.setMaximumHeight(37)
        self.level2_list = FleetShipList(self, 'main_fleet')
        self.level2_list.setObjectName("Level2FleetList")
        self.level2_list.setMaximumHeight(37)
        self.flagship_priority_list = FleetShipList(self, 'flagship')
        self.flagship_priority_list.setObjectName("FlagshipPriorityList")
        self.flagship_priority_list.setMaximumHeight(37)

        self.filter_button_group = QButtonGroup(self)
        self.filter_button_group.setExclusive(True)
        self.all_ships_button = QPushButton("全部")

        self.source_ships_list = SourceShipList()
        self.source_ships_list.setObjectName("SourceShipsList")

        self.custom_ship_input = QLineEdit()
        self.add_custom_ship_button = QPushButton("添加")
        self.remove_custom_ship_button = QPushButton("删除选中")
        self.add_custom_ship_button.setProperty("class", "OkCancelButton")

        # 便于统一移除舰船
        self.fleet_lists = [
            self.level1_list,
            self.level2_list,
            self.flagship_priority_list
        ]

    def _setup_ui(self):
        """构建主界面布局。"""
        # 主布局
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 一级舰队
        level1_title = QLabel("一级舰队:")
        level1_title.setObjectName("FormLabel")
        level1_desc = QLabel("构建舰队时首先从此列表选取，越靠前的越先选择，与二级舰队互斥")
        level1_desc.setObjectName("DescriptionLabel")
        main_layout.addWidget(level1_title)
        main_layout.addSpacing(5)
        main_layout.addWidget(level1_desc)
        main_layout.addSpacing(5)
        main_layout.addWidget(self.level1_list)
        main_layout.addSpacing(5)

        # 二级舰队
        level2_title = QLabel("二级舰队:")
        level2_title.setObjectName("FormLabel")
        level2_desc = QLabel("一级舰队未能选满6艘时从此列表选取，优先级同上")
        level2_desc.setObjectName("DescriptionLabel")
        main_layout.addWidget(level2_title)
        main_layout.addSpacing(5)
        main_layout.addWidget(level2_desc)
        main_layout.addSpacing(5)
        main_layout.addWidget(self.level2_list)
        main_layout.addSpacing(5)

        # 旗舰优先级
        flagship_title = QLabel("旗舰优先级:")
        flagship_title.setObjectName("FormLabel")
        flagship_desc = QLabel("从此列表选取舰队旗舰，优先级同上")
        flagship_desc.setObjectName("DescriptionLabel")
        main_layout.addWidget(flagship_title)
        main_layout.addSpacing(5)
        main_layout.addWidget(flagship_desc)
        main_layout.addSpacing(5)
        main_layout.addWidget(self.flagship_priority_list)
        main_layout.addSpacing(5)

        # 可用舰船
        source_ships_title = QLabel("可用舰船:")
        source_ships_title.setObjectName("FormLabel")
        source_ships_desc = QLabel("拖拽到上方选取，拖回下方删除；一二级舰队舰船可交换")
        source_ships_desc.setObjectName("DescriptionLabel")
        main_layout.addWidget(source_ships_title)
        main_layout.addSpacing(5)
        main_layout.addWidget(source_ships_desc)
        main_layout.addSpacing(5)

        # 筛选按钮
        filter_buttons_layout = QGridLayout()
        filter_buttons_layout.setSpacing(5)
        self.all_ships_button.setCheckable(True)
        self.all_ships_button.setChecked(True)
        self.all_ships_button.setProperty("class", "ShortButton")
        self.filter_button_group.addButton(self.all_ships_button)
        filter_buttons_layout.addWidget(self.all_ships_button, 0, 0, 1, 5)
        other_buttons_data = list(self.all_ships_data.keys()) + ["自定义"]
        max_cols = 5
        for i, text in enumerate(other_buttons_data):
            button = QPushButton(text)
            button.setCheckable(True)
            button.setProperty("class", "ShortButton")
            self.filter_button_group.addButton(button)
            row, col = (i // max_cols) + 1, i % max_cols
            filter_buttons_layout.addWidget(button, row, col)
        main_layout.addLayout(filter_buttons_layout)
        main_layout.addSpacing(5)

        # 源舰船列表
        main_layout.addWidget(self.source_ships_list, 1)
        main_layout.addSpacing(5)

        # 自定义舰船输入区域
        custom_ship_layout = QHBoxLayout()
        custom_ship_layout.setSpacing(5)
        self.custom_ship_input.setPlaceholderText("输入自定义船名")
        self.add_custom_ship_button.setProperty("class", "OkCancelButton")
        self.remove_custom_ship_button.setProperty("class", "OkCancelButton")
        custom_ship_layout.addWidget(self.custom_ship_input)
        custom_ship_layout.addWidget(self.add_custom_ship_button)
        custom_ship_layout.addWidget(self.remove_custom_ship_button)
        main_layout.addLayout(custom_ship_layout)

        return main_layout

    def _connect_signals(self):
        """连接所有信号与槽函数。"""
        self.filter_button_group.buttonClicked.connect(self._update_source_list_filter)
        self.add_custom_ship_button.clicked.connect(self._on_add_custom_ship)
        self.remove_button_manager.confirmed_click.connect(self._on_remove_custom_ship)
        self.source_ships_list.itemSelectionChanged.connect(self._update_remove_button_state)
        self.level1_list.contentChanged.connect(
            lambda: self.level1_fleet_changed.emit(self.get_list_data(self.level1_list))
        )
        self.level2_list.contentChanged.connect(
            lambda: self.level2_fleet_changed.emit(self.get_list_data(self.level2_list))
        )
        self.flagship_priority_list.contentChanged.connect(
            lambda: self.flagship_priority_changed.emit(self.get_list_data(self.flagship_priority_list))
        )

    def _update_source_list_filter(self):
        """根据筛选按钮刷新可用舰船列表。"""
        self.source_ships_list.clear()
        checked_button = self.filter_button_group.checkedButton()
        if not checked_button:
            return
        filter_category = checked_button.text()

        is_custom_mode = (filter_category == "自定义")
        self.source_ships_list.setProperty("customMode", is_custom_mode)
        self.source_ships_list.style().unpolish(self.source_ships_list)
        self.source_ships_list.style().polish(self.source_ships_list)

        ships_to_display = []
        if filter_category == "全部":
            for country in self.all_ships_data.values():
                ships_to_display.extend(country)
            ships_to_display.extend(self.custom_ships)
        elif filter_category == "自定义":
            ships_to_display.extend(self.custom_ships)
        elif filter_category in self.all_ships_data:
            ships_to_display.extend(self.all_ships_data[filter_category])

        unique_ships = sorted(list(set(filter(None, ships_to_display))), key=natural_sort_key)
        self.source_ships_list.addItems(unique_ships)
        self._update_remove_button_state()

        grid_size = self.source_ships_list.gridSize()
        for i in range(self.source_ships_list.count()):
            item = self.source_ships_list.item(i)
            item.setSizeHint(grid_size)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def _on_add_custom_ship(self):
        """添加自定义舰船。"""
        ship_name = self.custom_ship_input.text().strip()
        if not ship_name:
            self.log_message_signal.emit("自定义舰船名不能为空。")
            return
        if ship_name in self.custom_ships:
            self.log_message_signal.emit(f"舰船“{ship_name}”已存在于自定义列表中。")
            return
        self.custom_ships.append(ship_name)
        self.custom_ships.sort()
        self.custom_ships_changed.emit(self.custom_ships)
        self.log_message_signal.emit(f"已添加自定义舰船：“{ship_name}”")
        self.custom_ship_input.clear()
        for button in self.filter_button_group.buttons():
            if button.text() == "自定义":
                button.setChecked(True)
                self._update_source_list_filter()
                break

    def _on_remove_custom_ship(self):
        """移除自定义舰船。"""
        selected_items = self.source_ships_list.selectedItems()
        if not selected_items:
            self.log_message_signal.emit("请先在左侧列表中选择一个自定义舰船再移除。")
            return
        ship_name = selected_items[0].text()
        if ship_name not in self.custom_ships:
            self.log_message_signal.emit(f"“{ship_name}”不是自定义舰船，无法移除。")
            return
        self.custom_ships.remove(ship_name)
        self.remove_ship_from_all_fleets(ship_name)
        self.custom_ships_changed.emit(self.custom_ships)
        self._update_source_list_filter()
        self.log_message_signal.emit(f"已移除自定义舰船：“{ship_name}”")

    def _update_remove_button_state(self):
        """根据当前筛选和列表选择，更新删除按钮的启用状态。"""
        # 当前筛选按钮是“自定义”
        checked_button = self.filter_button_group.checkedButton()
        is_custom_mode = checked_button and checked_button.text() == "自定义"
        
        # 源舰船列表中有项目被选中
        has_selection = bool(self.source_ships_list.selectedItems())
        
        # 只有两个条件同时满足时，按钮才可用
        self.remove_custom_ship_button.setEnabled(is_custom_mode and has_selection)

    def ensure_main_fleet_uniqueness(self, ship_name, list_to_ignore):
        """保证一级/二级舰队互斥，不重复出现同一舰船。"""
        for fleet_list in [self.level1_list, self.level2_list]:
            if fleet_list is not list_to_ignore:
                items_to_remove = fleet_list.find_items(ship_name)
                if items_to_remove:
                    for item in items_to_remove:
                        fleet_list.takeItem(fleet_list.row(item))
                    fleet_list.contentChanged.emit()

    def remove_ship_from_all_fleets(self, ship_name):
        """从所有舰队列表移除指定舰船。"""
        for fleet_list in self.fleet_lists:
            items_to_remove = fleet_list.find_items(ship_name)
            if items_to_remove:
                for item in items_to_remove:
                    fleet_list.takeItem(fleet_list.row(item))
                fleet_list.contentChanged.emit()

    def get_list_data(self, list_widget):
        """获取列表所有舰船名。"""
        return [list_widget.item(i).text() for i in range(list_widget.count())]

    def set_fleet_data(self, level1, level2, flagship):
        """批量设置舰队数据。"""
        self.level1_list.clear()
        self.level1_list.addItems(level1)
        self.level2_list.clear()
        self.level2_list.addItems(level2)
        self.flagship_priority_list.clear()
        self.flagship_priority_list.addItems(flagship)