from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QApplication,
                               QPushButton, QButtonGroup, QGridLayout, QLineEdit)
from PySide6.QtCore import Qt, Signal, QEvent
from utils.ship_data_utils import load_ship_data
from utils.ui_utils import natural_sort_key, create_ok_cancel_buttons, ConfirmButtonManager
from tabs.components.list_box import BaseSourceList, BaseTargetList

class EditorSourceList(BaseSourceList):
    """编辑器界面的源列表"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('SourceShipsList')


class EditorSlotList(BaseTargetList):
    """编辑器界面的槽位列表，单元素+允许同类交换"""
    itemChanged = Signal()

    def __init__(self, parent_dialog, parent=None):
        super().__init__(parent, 
                        max_items=1,  # 单元素
                        allow_internal_move=False,
                        allow_same_type_exchange=True,
                        unique_in_same_type=True,
                        enable_smart_swap=True)  # 启用智能交换
        
        self.parent_dialog = parent_dialog
        self.setMaximumHeight(35)
        self.setWrapping(True)
        self.setObjectName('FleetList')
        self.contentChanged.connect(self.itemChanged)

    def get_ship(self):
        """获取当前插槽的舰船名。"""
        return self.item(0).text() if self.count() > 0 else ""

    def set_ship(self, ship_name):
        """设置或更新当前插槽的舰船。"""
        if self.count() > 0: self.takeItem(0)
        if ship_name: self.addItem(ship_name)
        self._update_item_sizes()
        self.itemChanged.emit()
        
    def _get_same_type_lists(self):
        """获取所有同类列表（用于智能交换）"""
        same_type_lists = []
        if hasattr(self.parent_dialog, 'drop_zones'):
            for drop_zone in self.parent_dialog.drop_zones:
                if drop_zone != self:
                    same_type_lists.append(drop_zone)
        return same_type_lists
        
    def dropEvent(self, event):
        """重写拖放事件，实现槽位间交换和从源列表的智能交换。"""
        source = event.source()
        
        # 同类槽位间交换
        if (isinstance(source, EditorSlotList) and 
            source != self):
            source_ship = source.get_ship()
            target_ship = self.get_ship()
            
            # 执行交换
            self.set_ship(source_ship)
            source.set_ship(target_ship)
            
            event.accept()
            return
            
        # 从源列表拖拽到非空槽位 - 替换逻辑
        if isinstance(source, BaseSourceList):
            dropped_ship_name = source.selectedItems()[0].text()
            current_ship = self.get_ship()
            
            # 查找拖拽的舰船是否已存在于其他槽位
            duplicate_slot = None
            for slot in self.parent_dialog.drop_zones:
                if slot is not self and slot.get_ship() == dropped_ship_name:
                    duplicate_slot = slot
                    break
            
            # 设置当前槽位为新舰船
            self.set_ship(dropped_ship_name)
            
            # 如果存在重复，执行交换
            if duplicate_slot:
                duplicate_slot.set_ship(current_ship)
            # 如果不存在重复，且当前槽位有船，则当前槽位的船应该回到源列表

            event.accept()
            self.contentChanged.emit()
            return
                
        # 其他情况交给基类处理
        super().dropEvent(event)


class EditorContentWidget(QWidget):
    """
    舰队编辑器的主要内容控件，负责UI布局和逻辑处理
    """
    custom_ships_changed = Signal(list)

    def __init__(self, initial_custom_ships, parent=None):
        super().__init__(parent)
        self.all_ships_data = load_ship_data(group_by_type=True)
        self.custom_ships = initial_custom_ships if initial_custom_ships else []
        self._all_standard_ships = {ship for data in self.all_ships_data.values() for ships in data.values() for ship in ships}
        self.drop_zones = []
        self._setup_ui()
        self._connect_signals()
        self._update_source_list_filter()

    def process_app_event(self, watched, event: QEvent):
        """专门处理由父级对话框转发来的事件"""
        if event.type() == QEvent.Type.FocusIn and watched == self.custom_ship_input:
            custom_button = next((btn for btn in self.type_filter_group.buttons() if btn.text() == "自定义"), None)
            if custom_button and not custom_button.isChecked():
                custom_button.click()
            return False
        
        # 处理全局鼠标点击事件，以实现点击空白处取消选择和清除焦点的功能
        if event.type() == QEvent.Type.MouseButtonPress:
            clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())

            is_on_input = clicked_widget and (self.custom_ship_input == clicked_widget)
            # 如果输入框有焦点，但点击位置不在输入框上，则清除焦点
            if self.custom_ship_input.hasFocus() and not is_on_input:
                self.custom_ship_input.clearFocus()

            # 处理删除确认按钮和源列表的点击逻辑
            is_on_delete_btn = clicked_widget and (self.remove_custom_ship_button == clicked_widget or self.remove_custom_ship_button.isAncestorOf(clicked_widget))
            is_on_source_list = clicked_widget and (self.source_ships_list == clicked_widget or self.source_ships_list.isAncestorOf(clicked_widget))
            
            if self.remove_button_manager.is_confirming() and not is_on_delete_btn:
                self.remove_button_manager.reset_state()
            
            if self.source_ships_list.selectedItems() and not is_on_source_list and not is_on_delete_btn:
                self.source_ships_list.clearSelection()

            if is_on_source_list:
                item_at_click = self.source_ships_list.itemAt(self.source_ships_list.mapFromGlobal(event.globalPosition().toPoint()))
                if item_at_click is None:
                    self.source_ships_list.clearSelection()
                    self.custom_ship_input.clearFocus()
                    self.source_ships_list.setFocus()
                    return True
        return False

    def _setup_ui(self):
        root_layout = QHBoxLayout(self)
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        root_layout.addWidget(left_panel, 2)
        root_layout.addWidget(right_panel, 1)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        nations = ["全部"] + sorted(self.all_ships_data.keys())
        self.nation_filter_group = QButtonGroup(self)
        nation_buttons_layout = self._create_button_grid(nations, self.nation_filter_group, "全部")
        all_types = sorted(list(set(t for n in self.all_ships_data.values() for t in n.keys())))
        ship_types = ["全部"] + all_types + ["自定义"]
        self.type_filter_group = QButtonGroup(self)
        type_buttons_layout = self._create_button_grid(ship_types, self.type_filter_group, "全部")
        self.source_ships_list = EditorSourceList()
        layout.addWidget(QLabel("国籍:"))
        layout.addLayout(nation_buttons_layout)
        layout.addSpacing(10)
        layout.addWidget(QLabel("舰种:"))
        layout.addLayout(type_buttons_layout)
        layout.addSpacing(10)
        layout.addWidget(self.source_ships_list, 1)
        layout.addSpacing(5)
        self.custom_ship_input = QLineEdit()
        self.custom_ship_input.setPlaceholderText("输入自定义船名后按添加")
        self.add_custom_ship_button = QPushButton("添加")
        self.add_custom_ship_button.setProperty("class", "OkCancelButton")
        self.remove_custom_ship_button = QPushButton("删除选中")
        self.remove_custom_ship_button.setProperty("class", "OkCancelButton")
        self.remove_button_manager = ConfirmButtonManager(self.remove_custom_ship_button)
        custom_ship_layout = QHBoxLayout()
        custom_ship_layout.addWidget(self.custom_ship_input)
        custom_ship_layout.addWidget(self.add_custom_ship_button)
        custom_ship_layout.addWidget(self.remove_custom_ship_button)
        layout.addLayout(custom_ship_layout)
        return panel
    
    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addStretch()
        for i in range(6):
            row_layout = QHBoxLayout()
            row_layout.setSpacing(10)
            label = QLabel(f"{i+1}号位")
            label.setFixedWidth(45)
            label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            zone = EditorSlotList(self) 
            self.drop_zones.append(zone)
            row_layout.addWidget(label)
            row_layout.addWidget(zone)
            layout.addLayout(row_layout)
        clear_button = QPushButton("清空所有位置")
        clear_button.setProperty('class', 'TallButton')
        layout.addWidget(clear_button)
        clear_button.clicked.connect(self._clear_all_zones)
        return panel

    def _connect_signals(self):
        self.nation_filter_group.buttonClicked.connect(self._update_source_list_filter)
        self.type_filter_group.buttonClicked.connect(self._update_source_list_filter)
        self.add_custom_ship_button.clicked.connect(self._on_add_custom_ship)
        self.remove_button_manager.confirmed_click.connect(self._on_remove_custom_ship)
        self.source_ships_list.itemSelectionChanged.connect(self._update_remove_button_state)
        self.custom_ship_input.returnPressed.connect(self._on_add_custom_ship)

    def _on_add_custom_ship(self):
        ship_name = self.custom_ship_input.text().strip()
        if not ship_name: return
        if ship_name in self.custom_ships or ship_name in self._all_standard_ships: return
        self.custom_ships.append(ship_name)
        self.custom_ships.sort(key=natural_sort_key)
        self.custom_ships_changed.emit(self.custom_ships)
        self.custom_ship_input.clear()
        custom_button = next((btn for btn in self.type_filter_group.buttons() if btn.text() == "自定义"), None)
        if custom_button and not custom_button.isChecked(): custom_button.click()
        else: self._update_source_list_filter()

    def _update_remove_button_state(self):
        checked_button = self.type_filter_group.checkedButton()
        is_custom_filter_active = checked_button and checked_button.text() == "自定义"
        has_selection = bool(self.source_ships_list.selectedItems())
        self.remove_custom_ship_button.setEnabled(is_custom_filter_active and has_selection)
        if not has_selection and self.remove_button_manager.is_confirming():
            self.remove_button_manager.reset_state()

    def _create_button_grid(self, items, button_group, default_checked_text):
        layout = QGridLayout(); layout.setSpacing(5); max_cols = 6
        for i, text in enumerate(items):
            button = QPushButton(text); button.setCheckable(True); button.setProperty("class", "ShortButton")
            if text == default_checked_text: button.setChecked(True)
            button_group.addButton(button); row, col = i // max_cols, i % max_cols; layout.addWidget(button, row, col)
        return layout

    def _update_source_list_filter(self):
        self.source_ships_list.clear(); selected_nation = self.nation_filter_group.checkedButton().text(); selected_type = self.type_filter_group.checkedButton().text()
        is_custom_mode = selected_type == "自定义"; self.source_ships_list.setProperty("customMode", is_custom_mode); self.source_ships_list.style().unpolish(self.source_ships_list); self.source_ships_list.style().polish(self.source_ships_list)
        for btn in self.nation_filter_group.buttons(): btn.setEnabled(not is_custom_mode)
        ships_to_display = []
        if is_custom_mode: ships_to_display.extend(self.custom_ships)
        else:
            for nation, types_dict in self.all_ships_data.items():
                if selected_nation != "全部" and nation != selected_nation: continue
                for ship_type, ships in types_dict.items():
                    if selected_type != "全部" and ship_type != selected_type: continue
                    ships_to_display.extend(ships)
            if selected_nation == "全部" and selected_type == "全部": ships_to_display.extend(self.custom_ships)
        self.source_ships_list.addItems(sorted(list(set(ships_to_display)), key=natural_sort_key))
        for zone in self.drop_zones: zone._update_item_sizes()
        self._update_remove_button_state()

    def remove_ship_from_all_fleets(self, ship_name: str):
        for zone in self.drop_zones:
            if zone.get_ship() == ship_name: zone.set_ship(None)

    def _on_remove_custom_ship(self):
        selected_items = self.source_ships_list.selectedItems()
        if not selected_items: return
        ship_name = selected_items[0].text()
        if ship_name not in self.custom_ships: return
        self.custom_ships.remove(ship_name); self.remove_ship_from_all_fleets(ship_name); self.custom_ships_changed.emit(self.custom_ships); self._update_source_list_filter()

    def _clear_all_zones(self):
        for zone in self.drop_zones: zone.set_ship(None)


class FleetEditorDialog(QDialog):
    """
    舰队编成对话框。主要负责窗口管理和事件转发。
    """
    custom_ships_changed = Signal(list) # 外部连接到Dialog的信号

    def __init__(self, initial_fleet, initial_custom_ships, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName('Dialog')
        self.setWindowTitle("舰队编成")
        self.setMinimumSize(800, 640)

        # 创建内容控件
        self.content_widget = EditorContentWidget(initial_custom_ships, self)
        self.content_widget.set_fleet = lambda fleet: self.set_fleet(fleet) # 代理方法
        self.content_widget.get_fleet = lambda: self.get_fleet() # 代理方法

        # 2. 将内容的信号连接到壳的信号上向外传递
        self.content_widget.custom_ships_changed.connect(self.custom_ships_changed)

        self._setup_shell_ui()
        self.set_fleet(initial_fleet)

    def set_fleet(self, fleet_list):
        ships_to_set = fleet_list[1:] if fleet_list else []
        for i, zone in enumerate(self.content_widget.drop_zones):
            ship_name = ships_to_set[i] if i < len(ships_to_set) else None
            zone.set_ship(ship_name)

    def get_fleet(self):
        return [zone.get_ship() for zone in self.content_widget.drop_zones]

    def _setup_shell_ui(self):
        """设置壳的UI，它包含内容类和OK/Cancel按钮"""
        shell_layout = QVBoxLayout(self)
        shell_layout.addWidget(self.content_widget)
        confirm_button, cancel_button = create_ok_cancel_buttons()
        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(527, 0, 18, 0)
        button_layout.addWidget(confirm_button)
        button_layout.addWidget(cancel_button)
        shell_layout.addLayout(button_layout)

    def exec(self):
        QApplication.instance().installEventFilter(self)
        result = super().exec()
        QApplication.instance().removeEventFilter(self)
        return result

    def eventFilter(self, watched, event: QEvent):
        """壳的过滤器，只负责转发"""
        if self.isActiveWindow():
            # 将事件转发给内容类处理
            return self.content_widget.process_app_event(watched, event)
        return False