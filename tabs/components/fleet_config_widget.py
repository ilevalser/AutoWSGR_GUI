from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout, QWidget,
    QLabel, QPushButton, QLineEdit,QButtonGroup, QApplication
)
from PySide6.QtCore import Signal, QEvent
from tabs.components.list_box import BaseSourceList, BaseTargetList
from utils.ui_utils import ConfirmButtonManager, natural_sort_key
from utils.ship_data_utils import load_ship_data

class ConfigSourceList(BaseSourceList):
    """配置界面的源列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SourceShipsList")


class ConfigTargetList(BaseTargetList):
    """配置界面的目标列表"""
    def __init__(self, parent_widget, list_type, parent=None):
        super().__init__(parent, 
                        max_items=0,  # 多元素
                        allow_internal_move=True,
                        allow_same_type_exchange=True,
                        unique_in_same_type=True,
                        enable_smart_swap=True)  # 启用智能交换
        
        self.parent_widget = parent_widget  # 保存对父组件的引用
        self.list_type = list_type
        self.setObjectName("FleetList")
        self.setMaximumHeight(37)
        
    def dragEnterEvent(self, event):
        """限制不同list_type之间的拖拽。"""
        source = event.source()
        
        # 拒绝不同list_type之间的拖拽
        if (isinstance(source, ConfigTargetList) and 
            source != self and
            source.list_type != self.list_type):
            event.ignore()
            return
            
        super().dragEnterEvent(event)
        
    def _get_same_type_lists(self):
        """获取所有同类列表（用于智能交换）"""
        same_type_lists = []
        if hasattr(self.parent_widget, 'fleet_lists'):
            for fleet_list in self.parent_widget.fleet_lists:
                if (fleet_list != self and 
                    hasattr(fleet_list, 'list_type') and 
                    fleet_list.list_type == self.list_type):
                    same_type_lists.append(fleet_list)
        return same_type_lists

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
        submarine_types = ['潜艇', '炮潜', '导潜']
        self.all_ships_data = load_ship_data(target_types=submarine_types, group_by_type=False)
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
        self.level1_list = ConfigTargetList(self, 'main_fleet')
        self.level2_list = ConfigTargetList(self, 'main_fleet')
        self.flagship_priority_list = ConfigTargetList(self, 'flagship')
        
        self.flagship_priority_list.allow_same_type_exchange = False
        self.flagship_priority_list.unique_in_same_type = False

        self.filter_button_group = QButtonGroup(self)
        self.filter_button_group.setExclusive(True)
        self.all_ships_button = QPushButton("全部")

        self.source_ships_list = ConfigSourceList()

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
            for country_ships in self.all_ships_data.values(): # --- 修改: 迭代字典的值 ---
                ships_to_display.extend(country_ships)
            ships_to_display.extend(self.custom_ships)
        elif filter_category == "自定义":
            ships_to_display.extend(self.custom_ships)
        elif filter_category in self.all_ships_data:
            ships_to_display.extend(self.all_ships_data[filter_category])

        unique_ships = sorted(list(set(filter(None, ships_to_display))), key=natural_sort_key)
        self.source_ships_list.addItems(unique_ships)
        self._update_remove_button_state()

    def _on_add_custom_ship(self):
        """添加自定义舰船。"""
        ship_name = self.custom_ship_input.text().strip()
        if not ship_name:
            return
        if ship_name in self.custom_ships:
            return
        self.custom_ships.append(ship_name)
        self.custom_ships.sort()
        self.custom_ships_changed.emit(self.custom_ships)
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
            return
        ship_name = selected_items[0].text()
        if ship_name not in self.custom_ships:
            return
        self.custom_ships.remove(ship_name)
        self.remove_ship_from_all_fleets(ship_name)
        self.custom_ships_changed.emit(self.custom_ships)
        self._update_source_list_filter()

    def _update_remove_button_state(self):
        """根据当前筛选和列表选择，更新删除按钮的启用状态。"""
        # 当前筛选按钮是“自定义”
        checked_button = self.filter_button_group.checkedButton()
        is_custom_mode = checked_button and checked_button.text() == "自定义"
        # 源舰船列表中有项目被选中
        has_selection = bool(self.source_ships_list.selectedItems())

        self.remove_custom_ship_button.setEnabled(is_custom_mode and has_selection)

    def ensure_uniqueness_across_lists(self, ship_name, list_to_ignore):
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