import os
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedSeq
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QDialog, QListWidget, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal, QSize
from tabs.components.fleet_editor_dialog import FleetEditorDialog
from tabs.components.spin_box import CustomSpinBox
from tabs.components.check_box import CustomCheckBox
from tabs.components.combo_box import CustomComboBox
from constants import BATTLE_TYPES, REPAIR_ITEMS, FIGHT_CONDITION_ITEMS
from utils.ui_utils import create_group, create_form_layout

class FleetDisplayBox(QListWidget):
    """一个不可交互的、水平单行显示的列表框，用于展示舰队成员。"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlow(QListWidget.Flow.LeftToRight)  # 水平流动
        self.setWrapping(False)  # 禁止换行
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded) # 按需显示水平滚动条
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff) # 从不显示垂直滚动条
        self.setSpacing(3)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection) # 禁止选中
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus) # 禁止获取焦点
        self.setDragDropMode(QAbstractItemView.DragDropMode.NoDragDrop) # 禁止拖拽

    def _update_item_sizes(self):
        """根据内容自适应项目尺寸"""
        fm = self.fontMetrics()
        horizontal_padding = 22  # 水平内边距
        fixed_height = 22      # 固定高度
        for i in range(self.count()):
            item = self.item(i)
            text_width = fm.boundingRect(item.text()).width()
            item.setSizeHint(QSize(text_width + horizontal_padding, fixed_height))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_fleet_data(self, ships: list):
        """外部调用的接口，用于设置舰队数据并更新显示。"""
        self.clear()
        if ships:
            self.addItems(ships)
        self._update_item_sizes()

class PlanSettingsWidget(QWidget):
    """
    用于编辑所选计划文件参数的控件。
    其UI会根据不同的计划类型（如常规战斗、活动、演习等）动态变化。
    """
    log_message_signal = Signal(str)
    plan_data_changed = Signal()
    custom_ships_updated = Signal(list)

    def __init__(self, yaml_manager: YAML, ui_configs_data: dict, ui_configs_path: str, parent=None):
        """初始化控件。"""
        super().__init__(parent)
        self.yaml_manager = yaml_manager
        self.current_plan_path = None
        self.plan_data = {}
        self.plan_type = None
        self.ui_configs_data = ui_configs_data
        self.ui_configs_path = ui_configs_path

        self._setup_ui()
        self._connect_signals()
        self.clear_and_hide()

    # --- 公共方法 ---
    def load_plan(self, plan_type, plan_data: dict):
        """加载指定的计划文件，并根据其类型显示对应的设置界面。"""
        self._block_all_signals(True) # 加载数据前阻塞所有信号，防止误触发保存操作
        self.clear_and_hide()
        self.plan_type = plan_type.lower()

        self.plan_data = plan_data
        if not isinstance(self.plan_data, dict):
             self.plan_data = {}

        # 根据计划类型，加载数据并显示对应的UI容器
        if self.plan_type in ['normal_fight', 'week', 'special_ap_task']:
            self._load_normal_fight_data()
            self.normal_fight_settings_container.show()
        elif self.plan_type == 'battle':
            self._load_battle_data()
            self.battle_settings_container.show()
        elif self.plan_type == 'event':
            self._load_event_data()
            self.event_settings_container.show()
        elif self.plan_type == 'exercise':
            self._load_exercise_data()
            self.exercise_settings_container.show()
        
        self.show()
        self._block_all_signals(False) # 处理完毕后恢复信号

    def clear_and_hide(self):
        """清空当前数据并隐藏所有设置面板。"""
        self.normal_fight_settings_container.hide()
        self.battle_settings_container.hide()
        self.event_settings_container.hide()
        self.exercise_settings_container.hide()
        self.plan_data = {}
        self.plan_type = None
        self.hide()

    # --- UI 初始化 ---
    def _setup_ui(self):
        """创建所有计划类型可能用到的UI元素和布局容器。"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 5, 10, 5)
        self.main_layout.setSpacing(15)

        # 预先创建所有类型的控件
        self._create_all_widgets()

        # 创建并添加所有设置组容器
        self.normal_fight_settings_container = self._create_normal_fight_settings()
        self.main_layout.addWidget(self.normal_fight_settings_container)
        self.battle_settings_container = self._create_battle_settings()
        self.main_layout.addWidget(self.battle_settings_container)
        self.event_settings_container = self._create_event_settings()
        self.main_layout.addWidget(self.event_settings_container)
        self.exercise_settings_container = self._create_exercise_settings()
        self.main_layout.addWidget(self.exercise_settings_container)

        self.main_layout.addStretch()
        
    def _create_all_widgets(self):
        """统一创建所有界面控件实例，便于管理。"""
        # 常规战斗
        self.nf_chapter_spin = CustomSpinBox()
        self.nf_chapter_spin.setRange(1, 9)
        self.nf_map_spin = CustomSpinBox()
        self.nf_map_spin.setRange(1, 6)
        self.nf_repair_combo, self.nf_repair_buttons_container = self._create_repair_mode_parts()
        self.nf_fight_cond_combo = CustomComboBox()
        self.nf_fight_cond_combo.addItems(FIGHT_CONDITION_ITEMS)
        self.nf_fleet_id_spin = CustomSpinBox()
        self.nf_fleet_id_spin.setRange(1, 4)
        self.nf_edit_fleet_button = QPushButton("选择/编辑")
        self.nf_edit_fleet_button.setProperty('class', 'TallButton')
        self.nf_edit_fleet_button, self.nf_fleet_display_label = self._create_fleet_parts()
        # 决战
        self.b_map_combo = CustomComboBox()
        self.b_map_combo.addItems(BATTLE_TYPES)
        self.b_repair_combo, self.b_repair_buttons_container = self._create_repair_mode_parts()
        # 活动
        self.e_difficulty_button = QPushButton()
        self.e_difficulty_button.setProperty("class", "TallButton")
        self.e_difficulty_button.setCheckable(True)
        self.e_map_spin = CustomSpinBox()
        self.e_map_spin.setRange(1, 6)
        self.e_repair_combo, self.e_repair_buttons_container = self._create_repair_mode_parts()
        self.e_fleet_id_spin = CustomSpinBox()
        self.e_fleet_id_spin.setRange(0, 4)
        self.e_from_alpha_check = CustomCheckBox("从A入口进入")
        self.e_edit_fleet_button = QPushButton("选择/编辑")
        self.e_edit_fleet_button.setProperty('class', 'TallButton')
        self.e_edit_fleet_button, self.e_fleet_display_label = self._create_fleet_parts()
        # 演习
        self.ex_times_spin = CustomSpinBox()
        self.ex_times_spin.setRange(1, 10)
        self.ex_robot_check = CustomCheckBox("是否打bot")
        self.ex_fleet_id_spin = CustomSpinBox()
        self.ex_fleet_id_spin.setRange(1, 4)
        self.ex_refresh_spin = CustomSpinBox()
        self.ex_refresh_spin.setRange(1, 10)

    def _create_normal_fight_settings(self):
        """创建“常规战斗”设置的表单布局和分组框。"""
        items = [
            {'widget': (QLabel("章节:"), self.nf_chapter_spin), 'description': "选择主线章节"},
            {'widget': (QLabel("地图:"), self.nf_map_spin), 'description': "选择主线地图"},
            {'widget': (QLabel("修理模式:"), self.nf_repair_combo), 'extra_widget': self.nf_repair_buttons_container, 'description': "需要逐位自定义时，在上方选择<br>不选中的位置中破修，选中的位置大破修"},
            {'widget': (QLabel("战况选择:"), self.nf_fight_cond_combo), 'description': "地图无战况时最好选无战况"},
            {'widget': (QLabel("出征舰队:"), self.nf_fleet_id_spin), 'description': "选择出征舰队，第1舰队无法进行编成替换"},
            {'widget': (QLabel("舰队编成:"), self.nf_edit_fleet_button), 'extra_widget': self.nf_fleet_display_label, 'description': "点击右侧按钮进行编队，第1舰队无法进行编成替换"}
        ]
        layout = create_form_layout(items, column_stretches=(1, 1))
        return create_group("常规战斗设置", layout, margins=(10, 0, 10, 0))

    def _create_battle_settings(self):
        """创建“战役”设置的表单布局和分组框。"""
        items = [
            {'widget': (QLabel("选择战役:"), self.b_map_combo), 'description': "选择战役的类型"},
            {'widget': (QLabel("修理模式:"), self.b_repair_combo), 'extra_widget': self.b_repair_buttons_container, 'description': "需要逐位自定义时，在上方选择<br>不选中的位置中破修，选中的位置大破修"}
        ]
        layout = create_form_layout(items, column_stretches=(1, 1))
        return create_group("战役设置", layout, margins=(10, 0, 10, 0))

    def _create_event_settings(self):
        """创建“活动”设置的表单布局和分组框。"""
        items = [
            {'widget': (QLabel("难度:"), self.e_difficulty_button), 'description': "选择普通图还是困难图"},
            {'widget': (QLabel("地图:"), self.e_map_spin), 'description': "选择活动地图"},
            {'widget': (QLabel("修理模式:"), self.e_repair_combo), 'extra_widget': self.e_repair_buttons_container, 'description': "需要逐位自定义时，在上方选择<br>不选中的位置中破修，选中的位置大破修"},
            {'widget': (QLabel("出征舰队:"), self.e_fleet_id_spin), 'description': "舰队问答等拥有活动专用舰队的活动选择0"},
            {'widget': self.e_from_alpha_check, 'description': "舰队问答活动选择入口，不选则为B入口进入"},
            {'widget': (QLabel("舰队编成:"), self.e_edit_fleet_button), 'extra_widget': self.e_fleet_display_label, 'description': "点击右侧按钮进行编队，第1舰队无法进行编成替换"}
        ]
        layout = create_form_layout(items, column_stretches=(1, 1))
        return create_group("活动设置", layout, margins=(10, 0, 10, 0))

    def _create_exercise_settings(self):
        """创建“演习”设置的表单布局和分组框。"""
        items = [
            {'widget': (QLabel("最大玩家演习次数:"), self.ex_times_spin), 'description': "打几个玩家，选4全打"},
            {'widget': self.ex_robot_check, 'description': "是否打排在演习第一位的bot"},
            {'widget': (QLabel("出征舰队:"), self.ex_fleet_id_spin), 'description': "选择出征舰队，第1舰队无法进行编成替换"},
            {'widget': (QLabel("最大刷新次数:"), self.ex_refresh_spin), 'description': "单个演习对象最多刷新几次"}
        ]
        layout = create_form_layout(items, column_stretches=(1, 1))
        return create_group("演习设置", layout, margins=(10, 0, 10, 0))

    def _create_repair_mode_parts(self):
        """创建“修理模式”所需的组合框和一组按钮，返回元组 (combo, button_container)。"""
        combo = CustomComboBox()
        combo.addItems(REPAIR_ITEMS)
        buttons_container = QWidget()
        buttons_layout = QHBoxLayout(buttons_container)
        buttons_layout.setContentsMargins(0,0,0,0)
        buttons_layout.setSpacing(3)
        buttons = []
        for i in range(6):
            btn = QPushButton(f"{i+1}号位")
            btn.setCheckable(True)
            btn.setProperty("class", "TallButton")
            buttons_layout.addWidget(btn)
            buttons.append(btn)
        buttons_container.setProperty("buttons", buttons) # 将按钮列表存入属性，方便后续访问
        return combo, buttons_container

    def _create_fleet_parts(self):
        """创建“舰队编成”所需的编辑按钮和显示区域。"""
        edit_button = QPushButton("选择/编辑")
        edit_button.setProperty('class', 'TallButton')
        display_widget = FleetDisplayBox()
        display_widget.setObjectName('fleet_display')

        return edit_button, display_widget
    
    # --- 信号连接 ---
    def _connect_signals(self):
        """集中连接所有控件的信号。"""
        # 常规战斗
        self.nf_chapter_spin.valueChanged.connect(lambda v: self._update_value_in_memory('chapter', v))
        self.nf_map_spin.valueChanged.connect(lambda v: self._update_value_in_memory('map', v))
        self._connect_repair_mode_widget(self.nf_repair_combo, self.nf_repair_buttons_container, 'repair_mode')
        self.nf_fight_cond_combo.currentIndexChanged.connect(lambda i: self._update_value_in_memory('fight_condition', i, delete_if=0))
        self.nf_fleet_id_spin.valueChanged.connect(self._on_nf_fleet_id_changed)
        self.nf_edit_fleet_button.clicked.connect(lambda: self._open_fleet_editor(self.nf_fleet_display_label))
        # 决战
        self.b_map_combo.currentIndexChanged.connect(lambda i: self._update_value_in_memory('map', i + 1))
        self._connect_repair_mode_widget(self.b_repair_combo, self.b_repair_buttons_container, 'repair_mode')
        # 活动
        self.e_difficulty_button.toggled.connect(self._on_difficulty_toggled)
        self.e_map_spin.valueChanged.connect(lambda v: self._update_value_in_memory('map', v))
        self._connect_repair_mode_widget(self.e_repair_combo, self.e_repair_buttons_container, 'repair_mode')
        self.e_fleet_id_spin.valueChanged.connect(self._on_e_fleet_id_changed)
        self.e_from_alpha_check.toggled.connect(lambda v: self._update_value_in_memory('from_alpha', v))
        self.e_edit_fleet_button.clicked.connect(lambda: self._open_fleet_editor(self.e_fleet_display_label))
        # 演习
        self.ex_times_spin.valueChanged.connect(lambda v: self._update_value_in_memory('exercise_times', v))
        self.ex_robot_check.toggled.connect(lambda v: self._update_value_in_memory('robot', v))
        self.ex_fleet_id_spin.valueChanged.connect(lambda v: self._update_value_in_memory('fleet_id', v))
        self.ex_refresh_spin.valueChanged.connect(lambda v: self._update_value_in_memory('max_refresh_times', v))
        
    def _connect_repair_mode_widget(self, combo, buttons_container, config_key):
        """为“修理模式”相关控件设置联动信号。"""
        buttons = buttons_container.property("buttons")
        
        def on_combo_changed(index):
            is_custom_mode = (index == 0) # 逐位自定义
            buttons_container.setEnabled(is_custom_mode)
            # 切换到逐位自定义
            if is_custom_mode:
                current_values = [2 if btn.isChecked() else 1 for btn in buttons]
                value_to_save = CommentedSeq(current_values)
                value_to_save.fa.set_flow_style()
                self._update_value_in_memory(config_key, value_to_save)
            # 切换到其他模式
            else:
                self._update_value_in_memory(config_key, index)

        def on_button_toggled():
            # 仅在逐位自定义模式下，按钮点击才触发保存
            if combo.currentIndex() == 0:
                current_values = [2 if btn.isChecked() else 1 for btn in buttons]
                flow_list = CommentedSeq(current_values)
                flow_list.fa.set_flow_style()
                self._update_value_in_memory(config_key, flow_list)

        combo.currentIndexChanged.connect(on_combo_changed)
        for btn in buttons:
            btn.toggled.connect(on_button_toggled)

    # --- 事件处理器 ---
    def _on_nf_fleet_id_changed(self, value):
        """处理常规战斗舰队ID变化，并更新舰队编辑器状态。"""
        is_disabled = (value == 1)
        self.nf_edit_fleet_button.setEnabled(not is_disabled)

        fields_to_manage = ['fleet']
        if is_disabled:
            for key in fields_to_manage:
                if key in self.plan_data:
                    del self.plan_data[key]

        self.plan_data['fleet_id'] = value
        self.plan_data_changed.emit()

        # 刷新UI时，调用修理模式的加载函数
        self._load_fleet_data(self.nf_fleet_display_label)
        self._load_repair_mode_data(self.nf_repair_combo, self.nf_repair_buttons_container, self.plan_data.get('repair_mode', 2))

    def _on_e_fleet_id_changed(self, value):
        """处理活动舰队ID变化，并更新相关UI状态。"""
        is_button_disabled = (value in [0, 1])
        self.e_edit_fleet_button.setEnabled(not is_button_disabled)
        self.e_from_alpha_check.setEnabled(value == 0)
        should_clear_data = (value == 0)

        fields_to_manage = ['fleet']
        if should_clear_data:
            for key in fields_to_manage:
                if key in self.plan_data:
                    del self.plan_data[key]

        is_fleet_id_zero = (value == 0)
        if is_fleet_id_zero:
            self.plan_data['from_alpha'] = self.e_from_alpha_check.isChecked()
        elif 'from_alpha' in self.plan_data:
            del self.plan_data['from_alpha']
        
        if value == 0:
            if 'fleet_id' in self.plan_data: del self.plan_data['fleet_id']
        else:
            self.plan_data['fleet_id'] = value

        self.plan_data_changed.emit()

        # 刷新UI时，调用修理模式的加载函数
        self._load_fleet_data(self.e_fleet_display_label)
        self._load_repair_mode_data(self.e_repair_combo, self.e_repair_buttons_container, self.plan_data.get('repair_mode', 2))

    def _on_difficulty_toggled(self, is_checked):
        """处理活动难度按钮点击事件。"""
        text_to_show = "困难" if is_checked else "简单"
        value_to_save = "H" if is_checked else "E"
        self.e_difficulty_button.setText(text_to_show)
        self._update_value_in_memory('chapter', value_to_save)

    def _open_fleet_editor(self, display_label):
        """打开舰队编辑器对话框，并在完成后保存和更新UI。"""
        current_fleet = self.plan_data.get('fleet', [])
        custom_ships = self.ui_configs_data.get('custom_names', [])
        
        dialog = FleetEditorDialog(current_fleet, custom_ships, self.window())
        dialog.custom_ships_changed.connect(self._on_custom_ships_changed)

        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_fleet = dialog.get_fleet()
            self._update_fleet_in_memory(new_fleet)
            self._load_fleet_data(display_label)

    def _on_custom_ships_changed(self, new_custom_ships: list):
        """接收来自对话框的信号，更新内存中的数据副本，并向父组件发射信号。"""
        self.ui_configs_data['custom_names'] = new_custom_ships
        self.custom_ships_updated.emit(new_custom_ships)

    # --- 数据加载与保存 ---
    def _load_normal_fight_data(self):
        """加载常规战斗类型的配置到UI。"""
        self.nf_chapter_spin.setValue(self.plan_data.get('chapter', 1))
        self.nf_map_spin.setValue(self.plan_data.get('map', 1))
        self._load_repair_mode_data(self.nf_repair_combo, self.nf_repair_buttons_container, self.plan_data.get('repair_mode', 2))
        self.nf_fight_cond_combo.setCurrentIndex(self.plan_data.get('fight_condition', 0))
        fleet_id = self.plan_data.get('fleet_id', 1)
        self.nf_fleet_id_spin.setValue(fleet_id)
        is_disabled = (fleet_id == 1)
        self.nf_edit_fleet_button.setEnabled(not is_disabled)
        self._load_fleet_data(self.nf_fleet_display_label)
        
    def _load_battle_data(self):
        """加载战役类型的配置到UI。"""
        self.b_map_combo.setCurrentIndex(self.plan_data.get('map', 1) - 1)
        self._load_repair_mode_data(self.b_repair_combo, self.b_repair_buttons_container, self.plan_data.get('repair_mode', 2))
        
    def _load_event_data(self):
        """加载活动类型的配置到UI。"""
        is_hard = (self.plan_data.get('chapter', 'H') == 'H')
        self.e_difficulty_button.setChecked(is_hard)
        self.e_difficulty_button.setText("困难" if is_hard else "简单")
        self.e_map_spin.setValue(self.plan_data.get('map', 1))
        self._load_repair_mode_data(self.e_repair_combo, self.e_repair_buttons_container, self.plan_data.get('repair_mode', 2))
        fleet_id = self.plan_data.get('fleet_id', 0)
        self.e_fleet_id_spin.setValue(fleet_id)
        is_button_disabled = (fleet_id in [0, 1])
        self.e_edit_fleet_button.setEnabled(not is_button_disabled)
        from_alpha_value = self.plan_data.get('from_alpha')
        is_checked = from_alpha_value if from_alpha_value is not None else True
        self.e_from_alpha_check.setChecked(is_checked)
        self.e_from_alpha_check.setEnabled(fleet_id == 0)
        self._load_fleet_data(self.e_fleet_display_label)

    def _load_exercise_data(self):
        """加载演习类型的配置到UI。"""
        self.ex_times_spin.setValue(self.plan_data.get('exercise_times', 4))
        self.ex_robot_check.setChecked(self.plan_data.get('robot', True))
        self.ex_fleet_id_spin.setValue(self.plan_data.get('fleet_id', 2))
        self.ex_refresh_spin.setValue(self.plan_data.get('max_refresh_times', 2))

    def _load_repair_mode_data(self, combo, buttons_container, value):
        """加载数据到“修理模式”的UI控件。"""
        buttons = buttons_container.property("buttons")
        # 临时阻塞信号
        combo.blockSignals(True)
        for btn in buttons: btn.blockSignals(True)
        
        try:
            if isinstance(value, list) and len(value) == 6: # 逐位自定义
                combo.setCurrentIndex(0)
                buttons_container.setEnabled(True)
                for i, btn in enumerate(buttons):
                    btn.setChecked(value[i] == 2) # 2代表大破修
            else: # 中破或大破修
                index = int(value) if str(value).isdigit() and int(value) in [1, 2] else 2
                combo.setCurrentIndex(index)
                buttons_container.setEnabled(False)
                for btn in buttons:
                    btn.setChecked(False)
        finally:
            # 恢复信号
            combo.blockSignals(False)
            for btn in buttons: btn.blockSignals(False)

    def _load_fleet_data(self, fleet_display_widget):
        """
        从plan_data加载舰队数据显示到UI。
        - 如果无舰队数据，则显示空白。
        - 如果有舰队数据，则补齐至6位显示。
        """
        # 演习和战役模式不需要显示舰队，直接清空并返回
        if self.plan_type in ['exercise', 'battle']:
            fleet_display_widget.set_fleet_data([])
            return

        fleet_list = self.plan_data.get('fleet')
        if fleet_list and isinstance(fleet_list, list) and len(fleet_list) > 1:
            ships_data = fleet_list[1:]
            padded_data = (ships_data + [None] * 6)[:6]
            display_ships = [str(ship) if ship else "-" for ship in padded_data]
            
            fleet_display_widget.set_fleet_data(display_ships)
        else:
            fleet_display_widget.set_fleet_data([])
            
    def _update_value_in_memory(self, key, value, delete_if=None):
        """保存单个键值对到内存中"""
        if delete_if is not None and value == delete_if:
            if key in self.plan_data:
                del self.plan_data[key]
        else:
            self.plan_data[key] = value

        self.plan_data_changed.emit()

    def _update_fleet_in_memory(self, new_fleet_list):
        """将舰队列表保存到内存中"""
        if all(not ship for ship in new_fleet_list):
            if 'fleet' in self.plan_data:
                del self.plan_data['fleet']
        else:
            final_list = [""] + new_fleet_list
            flow_list = CommentedSeq(final_list)
            flow_list.fa.set_flow_style()
            self.plan_data['fleet'] = flow_list

        self.plan_data_changed.emit()

    def _block_all_signals(self, block):
        """阻塞或恢复当前控件下所有子控件的信号。"""
        # 查找所有需要阻塞信号的控件类型
        widgets_to_block = []
        widget_types = (CustomSpinBox, CustomCheckBox, QPushButton, CustomComboBox)
        for widget_type in widget_types:
            widgets_to_block.extend(self.findChildren(widget_type))
        
        for widget in widgets_to_block:
            widget.blockSignals(block)