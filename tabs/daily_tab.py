import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QApplication,
    QTableWidgetItem, QPushButton, QLabel, QLineEdit, QDialog
)
from PySide6.QtCore import Qt, Signal, Slot, QEvent
from PySide6.QtGui import QIntValidator
from numpy import True_
from ruamel.yaml.comments import CommentedSeq, CommentedMap

from tabs.components.check_box import CustomCheckBox
from tabs.components.spin_box import CustomSpinBox
from tabs.components.combo_box import CustomComboBox
from tabs.components.base_task_tab import BaseTaskTab
from tabs.components.managed_list_widget import ManagedListWidget
from tabs.components.validation_input_dialog import ValidationInputDialog, PresetValidator
from utils.ui_utils import create_form_layout, create_group, create_ok_cancel_buttons, ConfirmButtonManager
from utils.config_utils import update_config_value, save_config
from constants import BATTLE_TYPES

class DailyTab(BaseTaskTab):
    """日常挂机设置选项卡"""

    log_message_signal = Signal(str)  # 日志信号，用于输出错误或提示信息

    def __init__(self, settings_data, settings_path, configs_data, configs_path, yaml_manager, parent=None):
        """初始化 DailyTab 选项卡"""
        super().__init__(parent)
        self.settings_data = settings_data
        self.settings_path = settings_path
        self.configs_data = configs_data
        self.configs_path = configs_path
        self.yaml_manager = yaml_manager
        plan_root = self.settings_data.get('plan_root')
        self.normal_plans_dir = plan_root + '/normal_fight' if plan_root else None

        # 状态变量
        self.normal_plans_dir = None
        self.edit_mode = None
        self.editing_row_index = -1
        self.delete_preset_confirm_manager = None

        self._setup_ui()
        self._connect_signals()
        self._load_data_to_ui()
        QApplication.instance().installEventFilter(self)

    def _setup_ui(self):
        """构建 UI 界面，包括左侧设置和右侧任务列表"""
        # 主布局
        self.setObjectName("DailyTab")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 左侧面板：挂机通用设置
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 启动挂机按钮
        self.daily_task_button = QPushButton("启动日常")
        self.daily_task_button.setProperty("class", "StartStopButton")
        self.daily_task_button.setProperty("running", False)
        self.daily_task_button.setObjectName("日常")
        button_layout = QVBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.addWidget(self.daily_task_button)
        button_group = create_group(title=None, content=button_layout, margins=(15, 0, 15, 0))
        left_layout.addWidget(button_group)
        left_layout.addSpacing(10)
        
        # 日常挂机相关设置项
        self.auto_expedition_cb = CustomCheckBox("自动重复远征")
        self.auto_gain_bonus_cb = CustomCheckBox("自动收取任务奖励")
        self.auto_bath_repair_cb = CustomCheckBox("空闲时自动修理")
        self.auto_set_support_cb = CustomCheckBox("自动开启战役支援")
        self.auto_battle_cb = CustomCheckBox("自动每日战役")
        self.battle_type_combo = CustomComboBox()
        self.battle_type_combo.addItems(BATTLE_TYPES)
        self.auto_exercise_cb = CustomCheckBox("自动演习")
        self.exercise_fleet_id_spin = CustomSpinBox()
        self.exercise_fleet_id_spin.setRange(1, 4)
        self.auto_normal_fight_cb = CustomCheckBox("按自定义任务进行日常出征")
        self.quick_repair_limit_input = QLineEdit()
        self.quick_repair_limit_input.setPlaceholderText("0")
        self.stop_max_ship_cb = CustomCheckBox("捞到每日最大掉落时停止")
        self.stop_max_loot_cb = CustomCheckBox("捞到每日最大胖次时停止")
        daily_settings_layout = create_form_layout([
            {'widget': self.auto_expedition_cb, 'description': "定时检查远征并自动收取"},
            {'widget': self.auto_gain_bonus_cb, 'description': "有任务奖励时自动领取"},
            {'widget': self.auto_bath_repair_cb, 'description': "在无其他任务时自动修理破损舰船"},
            {'widget': self.auto_set_support_cb, 'description': "出征前自动设置战役支援"},
            {'widget': self.auto_battle_cb, 'description': "根据战役类型自动进行每日战役"},
            {'widget': (QLabel("战役选择:"), self.battle_type_combo), 'description': "选择每日战役的类型"},
            {'widget': self.auto_exercise_cb, 'description': "自动进行演习"},
            {'widget': (QLabel("演习出征舰队:"), self.exercise_fleet_id_spin), 'description': "选择用于演习的舰队编号"},
            {'widget': self.auto_normal_fight_cb, 'description': "根据右侧任务列表自动出征"},
            {'widget': (QLabel("快修消耗上限:"), self.quick_repair_limit_input), 'description': "设置自动使用快速修理的最大数量，0为无上限"},
            {'widget': self.stop_max_ship_cb, 'description': "当捞取达到每日舰船掉落上限时停止挂机"},
            {'widget': self.stop_max_loot_cb, 'description': "当捞取达到每日胖次掉落上限时停止挂机"}
        ])
        left_layout.addWidget(create_group("日常挂机设置", daily_settings_layout))
        left_layout.addStretch()

        # 右侧面板：任务列表与编辑
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 预设管理
        self.preset_task_combo = CustomComboBox()
        self.apply_preset_btn = QPushButton("应用预设")
        self.save_preset_btn = QPushButton("保存为预设")
        self.delete_preset_btn = QPushButton("删除预设")
        self.delete_preset_confirm_manager = ConfirmButtonManager(
            self.delete_preset_btn,
            confirm_text="再次点击",
            pre_condition_check=self._delete_preset_pre_condition_check
        )
        self.apply_preset_btn.setProperty("class", "ShortButton")
        self.save_preset_btn.setProperty("class", "ShortButton")
        self.delete_preset_btn.setProperty("class", "ShortButton")
        preset_form_layout = create_form_layout([{'widget': (QLabel("选择任务:"), self.preset_task_combo), 'description': "点击应用后将覆盖当前任务列表"}])

        preset_buttons_layout = QHBoxLayout()
        preset_buttons_layout.addWidget(self.apply_preset_btn)
        preset_buttons_layout.addWidget(self.save_preset_btn)
        preset_buttons_layout.addWidget(self.delete_preset_btn)

        preset_layout = QVBoxLayout()
        preset_layout.setContentsMargins(0, 0, 0, 0)
        preset_layout.addLayout(preset_form_layout)
        preset_layout.addLayout(preset_buttons_layout)

        self.preset_group = create_group("任务预设", preset_layout)
        right_layout.addWidget(self.preset_group)

        # 任务列表表格
        self.list_manager = ManagedListWidget(["任务", "出征舰队", "出征次数"])
        self.tasks_table = self.list_manager.table
        self.tasks_table.setFixedHeight(240)
        self.remove_task_btn = self.list_manager.remove_btn

        # DailyTab 独有的按钮
        self.add_task_btn = QPushButton("添加任务")
        self.add_task_btn.setCheckable(True)
        self.add_task_btn.setProperty("class", "ShortButton")
        self.edit_task_btn = QPushButton("编辑选中")
        self.edit_task_btn.setCheckable(True)
        self.edit_task_btn.setProperty("class", "ShortButton")
        # 在最前面插入 Add 和 Edit 按钮
        self.list_manager.button_layout.insertWidget(0, self.add_task_btn)
        self.list_manager.button_layout.insertWidget(1, self.edit_task_btn)

        # 任务列表组装
        task_list_content_layout = QVBoxLayout()
        task_list_content_layout.setContentsMargins(0, 0, 0, 0)
        task_list_content_layout.addWidget(self.list_manager)
        self.task_list_group = create_group("自定义任务列表", task_list_content_layout)
        right_layout.addWidget(self.task_list_group)

        # 任务编辑控件
        self.task_file_combo = CustomComboBox()
        self._load_task_files_to_combo()
        self.fleet_spinbox = CustomSpinBox()
        self.fleet_spinbox.setRange(1, 4)
        self.count_input = QLineEdit()
        self.count_input.setPlaceholderText("只能输入正整数")
        self.count_validator = QIntValidator(1, 99999)
        self.count_input.setValidator(self.count_validator)
        editor_items_info = [
            {'widget': (QLabel("任务:"), self.task_file_combo)},
            {'widget': (QLabel("出征舰队:"), self.fleet_spinbox)},
            {'widget': (QLabel("出征次数:"), self.count_input)}
        ]
        form_layout = create_form_layout(editor_items_info, column_stretches=(1, 1))

        # 编辑模块按钮
        edit_module_content_layout = QVBoxLayout()
        edit_module_content_layout.setContentsMargins(0, 0, 0, 0)
        module_buttons_layout = QHBoxLayout()
        module_buttons_layout.addStretch()
        self.confirm_button, self.cancel_button = create_ok_cancel_buttons()
        module_buttons_layout.addWidget(self.confirm_button)
        module_buttons_layout.addWidget(self.cancel_button)
        edit_module_content_layout.addLayout(form_layout)
        edit_module_content_layout.addLayout(module_buttons_layout)

        # 编辑模块组装
        self.edit_task_module = create_group(
            "任务编辑", edit_module_content_layout, margins=(15, 15, 15, 0)
        )
        self.edit_task_module.setVisible(False)
        right_layout.addWidget(self.edit_task_module)
        right_layout.addStretch(1)

        # 组合左右面板
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        """连接所有 UI 控件的信号到对应的处理函数"""
        # 日常自动化设置信号
        self.auto_expedition_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_expedition", checked))
        self.auto_gain_bonus_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_gain_bonus", checked))
        self.auto_bath_repair_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_bath_repair", checked))
        self.auto_set_support_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_set_support", checked))
        self.auto_battle_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_battle", checked))
        self.battle_type_combo.currentTextChanged.connect(
            lambda text: self._handle_value_change('daily_automation.battle_type', text))
        self.auto_exercise_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_exercise", checked))
        self.exercise_fleet_id_spin.valueChanged.connect(
            lambda val: self._handle_value_change("daily_automation.exercise_fleet_id", val))
        self.auto_normal_fight_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_normal_fight", checked))
        self.quick_repair_limit_input.editingFinished.connect(self._save_quick_repair_limit)
        self.stop_max_ship_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.stop_max_ship", checked))
        self.stop_max_loot_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.stop_max_loot", checked))
        # 预设管理信号
        self.apply_preset_btn.clicked.connect(self._on_apply_preset_clicked)
        self.save_preset_btn.clicked.connect(self._on_save_preset_clicked)
        self.delete_preset_confirm_manager.confirmed_click.connect(self._on_delete_preset_clicked)
        self.preset_task_combo.currentTextChanged.connect(self._on_preset_selection_changed)
        # 任务管理按钮信号
        self.add_task_btn.clicked.connect(self._on_add_task_clicked)
        self.edit_task_btn.clicked.connect(self._on_edit_task_clicked)
        # 连接到 list_manager 的信号
        self.list_manager.item_moved.connect(self._on_task_moved)
        self.list_manager.item_removed.connect(self._on_task_removed)
        self.list_manager.selection_changed.connect(self._on_selection_changed)
        # 编辑模块按钮信号
        self.confirm_button.clicked.connect(self._on_accept_edit)
        self.cancel_button.clicked.connect(self._on_cancel_edit)

    def _load_task_files_to_combo(self):
        """加载任务文件夹下的任务文件到下拉菜单"""
        plan_root = self.settings_data.get('plan_root')
        if plan_root:
            self.normal_plans_dir = os.path.join(plan_root, 'normal_fight')
        else:
            self.normal_plans_dir = None
        
        self.task_file_combo.clear() # 确保每次加载前都清空
        self.task_file_combo.setEnabled(True) # 默认启用

        if not self.normal_plans_dir or not os.path.isdir(self.normal_plans_dir):
            self.task_file_combo.addItem("方案路径无效或未设置")
            self.task_file_combo.setEnabled(False)
            return
        try:
            files = [f for f in os.listdir(self.normal_plans_dir) if f.endswith(('.yml', '.yaml'))]
            if not files:
                self.task_file_combo.addItem("未找到日常作战方案")
                self.task_file_combo.setEnabled(False)
            else:
                plan_names = sorted([os.path.splitext(f)[0] for f in files])
                self.task_file_combo.addItems(plan_names)
        except Exception as e:
            self.log_message_signal.emit(f"错误: 读取任务文件时出错: {e}")

    def _load_data_to_ui(self):
        """从配置数据加载初始值到 UI 控件"""
        daily = self.settings_data.get('daily_automation', {})
        self.auto_expedition_cb.setChecked(daily.get('auto_expedition', False))
        self.auto_gain_bonus_cb.setChecked(daily.get('auto_gain_bonus', False))
        self.auto_bath_repair_cb.setChecked(daily.get('auto_bath_repair', False))
        self.auto_set_support_cb.setChecked(daily.get('auto_set_support', False))
        self.auto_battle_cb.setChecked(daily.get('auto_battle', False))
        self.auto_exercise_cb.setChecked(daily.get('auto_exercise', False))
        self.auto_normal_fight_cb.setChecked(daily.get('auto_normal_fight', False))
        self.stop_max_ship_cb.setChecked(daily.get('stop_max_ship', False))
        self.stop_max_loot_cb.setChecked(daily.get('stop_max_loot', False))
        self.battle_type_combo.setCurrentText(daily.get('battle_type', '困难战列'))
        self.exercise_fleet_id_spin.setValue(daily.get('exercise_fleet_id', 3))
        
        # 如果值为 None（无上限），则在UI上显示为 '0'
        quick_repair_limit_val = daily.get('quick_repair_limit')
        display_text = '0' if quick_repair_limit_val is None else str(quick_repair_limit_val)
        self.quick_repair_limit_input.setText(display_text)
        self._load_task_files_to_combo()
        self.populate_tasks_table(daily.get('normal_fight_tasks', []))

        # 预设按钮刷新
        self._load_presets_to_combo()
        self._update_task_buttons_state()

    def populate_tasks_table(self, tasks):
        """将任务列表数据填充到表格中"""
        items_list = []
        for row, task in enumerate(tasks or []):
            row_items = []
            for col, item_data in enumerate(task):
                item = QTableWidgetItem(str(item_data))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                row_items.append(item)
            items_list.append(row_items)
        self.list_manager.set_table_data(items_list)
        self._update_task_buttons_state()

    def _handle_value_change(self, path, value):
        """统一处理配置值的更新和保存，并处理可能发生的错误"""
        try:
            update_config_value(self.settings_data, path, value)
            save_config(self.yaml_manager, self.settings_data, self.settings_path)
        except Exception as e:
            self.log_message_signal.emit(str(e))

    def _save_quick_repair_limit(self):
        """验证并保存快速修理上限"""
        text = self.quick_repair_limit_input.text()
        value_to_save = None
        display_text = "0"
        if text and text != "0":
            try:
                num_value = int(text)
                value_to_save = max(1, min(num_value, 999)) 
                display_text = str(value_to_save)
            except (ValueError, TypeError):
                value_to_save = None
                display_text = "0"
        
        if self.quick_repair_limit_input.text() != display_text:
            self.quick_repair_limit_input.setText(display_text)
        self._handle_value_change("daily_automation.quick_repair_limit", value_to_save)


    def eventFilter(self, watched, event):
        """事件过滤器，重置删除按钮的二次确认状态"""
        if not self.isVisible():
            return super().eventFilter(watched, event)
        self.list_manager.process_global_event(event)

        if self.delete_preset_confirm_manager and event.type() == QEvent.Type.MouseButtonPress:
            if self.delete_preset_btn.isVisible() and self.delete_preset_confirm_manager.is_confirming():
                clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())
                is_on_delete_button = clicked_widget and (
                    self.delete_preset_btn == clicked_widget or 
                    self.delete_preset_btn.isAncestorOf(clicked_widget)
                )
                if not is_on_delete_button:
                    self.delete_preset_confirm_manager.reset_state()
        return super().eventFilter(watched, event)

    @Slot()
    def refresh_task_plans(self):
        """刷新自定义任务下拉列表的内容，并校验现有任务列表的有效性"""
        self._load_task_files_to_combo()

        # 校验现有任务列表
        available_plans = set()
        if self.normal_plans_dir and os.path.isdir(self.normal_plans_dir):
            available_plans = {os.path.splitext(f)[0] for f in os.listdir(self.normal_plans_dir) if f.endswith(('.yml', '.yaml'))}

        daily_automation = self.settings_data.get('daily_automation', {})
        current_tasks = daily_automation.get('normal_fight_tasks', [])
        if not current_tasks: return

        # 筛选出有效的任务
        validated_tasks = []
        removed_task_names = []
        for task in current_tasks:
            if task and task[0] in available_plans:
                validated_tasks.append(task)
            elif task:
                removed_task_names.append(str(task[0]))
        
        # 如果有任务被移除，则更新配置和UI
        if removed_task_names:
            new_task_list = CommentedSeq(validated_tasks)
            for task in new_task_list:
                task.fa.set_flow_style()

            self._handle_value_change('daily_automation.normal_fight_tasks', new_task_list)
            self.populate_tasks_table(new_task_list)

    # 任务列表核心交互逻辑
    def _reset_to_view_mode(self):
        """重置 UI 到默认的“仅查看”状态"""
        self.edit_task_module.setVisible(False)
        self.add_task_btn.setChecked(False)
        self.edit_task_btn.setChecked(False)
        self.edit_mode = None
        self.editing_row_index = -1

    def _load_task_data_to_editor(self, row):
        """加载指定行的数据到编辑模块"""
        title_label = self.edit_task_module.findChild(QLabel, "SettingsGroupTitle")
        task_name = self.tasks_table.item(row, 0).text()
        fleet_id = int(self.tasks_table.item(row, 1).text())
        count = int(self.tasks_table.item(row, 2).text())

        if title_label:
            title_label.setText(f"编辑任务{row + 1}：{task_name}")

        self.task_file_combo.setCurrentText(task_name)
        self.fleet_spinbox.setValue(fleet_id)
        self.count_input.setText(str(count))
        self.editing_row_index = row

    def _on_selection_changed(self, current_row: int):
        """响应表格选择变化，更新 UI 状态"""
        if current_row == -1:
            self._reset_to_view_mode()
        else:
            if self.edit_mode == 'add':
                self._reset_to_view_mode()
                # 让 list_manager 取消选择
                self.list_manager.clear_selection() 
                return # 避免重复逻辑
            elif self.edit_task_module.isVisible() and self.edit_mode == 'edit':
                self._load_task_data_to_editor(current_row)
        self._update_task_buttons_state()

    def _update_task_buttons_state(self):
        """更新所有任务相关按钮的可用性"""
        # 任务列表按钮逻辑
        is_item_selected = self.list_manager.get_current_row() >= 0
        self.edit_task_btn.setEnabled(is_item_selected)
        # 预设按钮逻辑
        has_preset_selected = self.preset_task_combo.currentIndex() != -1 and self.preset_task_combo.isEnabled()
        has_current_tasks = self.tasks_table.rowCount() > 0
        is_duplicate = self._is_current_task_list_a_duplicate()
        can_save = has_current_tasks and not is_duplicate

        self.apply_preset_btn.setEnabled(has_preset_selected)
        self.delete_preset_btn.setEnabled(has_preset_selected)
        self.save_preset_btn.setEnabled(can_save)

        if has_current_tasks and is_duplicate:
            self.save_preset_btn.setToolTip("当前任务列表与一个已保存的预设内容相同")
        elif not has_current_tasks:
            self.save_preset_btn.setToolTip("当前任务列表为空")
        else:
            self.save_preset_btn.setToolTip("")

    def _on_add_task_clicked(self):
        """处理“添加任务”按钮点击，进入“添加”模式"""
        if self.edit_task_module.isVisible() and self.edit_mode == 'add':
            self._reset_to_view_mode()
            return
        self.list_manager.clear_selection()
        self.edit_mode = 'add'
        self.add_task_btn.setChecked(True)
        self.edit_task_btn.setChecked(False)
        self.edit_task_module.setVisible(True)
        title_label = self.edit_task_module.findChild(QLabel, "SettingsGroupTitle")
        if title_label:
            title_label.setText("添加新任务")
        self.task_file_combo.setCurrentIndex(0)
        self.fleet_spinbox.setValue(1)
        self.count_input.setText("1")

    def _on_edit_task_clicked(self):
        """处理“编辑选中”按钮点击，进入“编辑”模式"""
        current_row = self.list_manager.get_current_row()
        if current_row < 0:
            return
        if self.edit_task_module.isVisible() and self.edit_mode == 'edit' and self.editing_row_index == current_row:
            self._reset_to_view_mode()
            return
        self.edit_mode = 'edit'
        self.add_task_btn.setChecked(False)
        self.edit_task_btn.setChecked(True)
        self.edit_task_module.setVisible(True)
        self._load_task_data_to_editor(current_row)

    def _on_accept_edit(self):
        """处理编辑模块中的“确定”按钮，保存更改"""
        task_name = self.task_file_combo.currentText()
        if not task_name or "未找到" in task_name: return
        count_text = self.count_input.text()
        count_value = int(count_text) if count_text.isdigit() and int(count_text) > 0 else 1
        new_task_data = CommentedSeq([task_name, self.fleet_spinbox.value(), count_value])
        new_task_data.fa.set_flow_style()
        daily_settings = self.settings_data.setdefault('daily_automation', {})
        current_tasks = daily_settings.get('normal_fight_tasks')
        if not isinstance(current_tasks, CommentedSeq):
            current_tasks = CommentedSeq(current_tasks or [])
            daily_settings['normal_fight_tasks'] = current_tasks
        if self.edit_mode == 'add':
            current_tasks.append(new_task_data)
        elif self.edit_mode == 'edit':
            if 0 <= self.editing_row_index < len(current_tasks):
                current_tasks[self.editing_row_index] = new_task_data
        try:
            save_config(self.yaml_manager, self.settings_data, self.settings_path)
        except Exception as e:
            self.log_message_signal.emit(str(e))
        self.populate_tasks_table(current_tasks)
        self._reset_to_view_mode()

    def _on_cancel_edit(self):
        """处理编辑模块中的“取消”按钮，放弃更改"""
        self._reset_to_view_mode()

    @Slot(int)
    def _on_task_removed(self, row: int):
        """响应 list_manager 的 item_removed 信号"""
        current_tasks = self.settings_data['daily_automation']['normal_fight_tasks']
        del current_tasks[row]
        new_value = current_tasks if current_tasks else []
        self._handle_value_change('daily_automation.normal_fight_tasks', new_value)
        self._update_task_buttons_state()
        # 此时选择已自动清除，需要重置编辑模块
        self._reset_to_view_mode()

    @Slot(int, int)
    def _on_task_moved(self, from_row: int, to_row: int):
        """响应 list_manager 的 item_moved 信号"""
        current_tasks = self.settings_data['daily_automation']['normal_fight_tasks']
        current_tasks.insert(to_row, current_tasks.pop(from_row))
        self._handle_value_change('daily_automation.normal_fight_tasks', current_tasks)
        self._update_task_buttons_state()
        # 如果处于编辑模式，更新正在编辑的行索引
        if self.edit_mode == 'edit':
            self.editing_row_index = to_row
            # 重新加载编辑器内容以防万一
            self._load_task_data_to_editor(to_row)

    # 任务预设交互逻辑
    def _is_current_task_list_a_duplicate(self):
        """检查当前的任务列表是否与任何已保存的预设内容相同"""
        current_tasks_data = self.settings_data.get('daily_automation', {}).get('normal_fight_tasks', [])
        # 处理 None 值的情况
        if current_tasks_data is None:
            current_tasks_list = []
        else:
            current_tasks_list = [list(task) for task in current_tasks_data]

        preset_map = self._get_preset_map()
        if not preset_map: return False

        for saved_task_data in preset_map.values():
            saved_task_list = [list(task) for task in saved_task_data]
            if current_tasks_list == saved_task_list: return True_
        return False
    
    def _save_configs(self):
        """保存 ui_configs.yaml"""
        try:
            save_config(self.yaml_manager, self.configs_data, self.configs_path)
        except Exception as e:
            self.log_message_signal.emit(f"保存预设失败: {e}")

    def _get_preset_map(self):
        """如果preset_task是'[]'或不存在，将其转换/创建为一个空的 CommentedMap"""
        preset_data = self.configs_data.get('preset_task')
        # 检查是否是 '[]' (来自) 或 None
        if not isinstance(preset_data, (dict, CommentedMap)):
            new_map = self.yaml_manager.map()
            self.configs_data['preset_task'] = new_map
            return new_map
        return preset_data

    def _load_presets_to_combo(self):
        """从 configs_data 加载预设到下拉框"""
        self.preset_task_combo.blockSignals(True)
        current_selection = self.preset_task_combo.currentText()
        self.preset_task_combo.clear()
        preset_map = self._get_preset_map()
        
        if not preset_map:
            self.preset_task_combo.addItem("无可用预设")
            self.preset_task_combo.setEnabled(False)
        else:
            self.preset_task_combo.setEnabled(True)
            preset_names = sorted(list(preset_map.keys()))
            self.preset_task_combo.addItems(preset_names)
            # 尝试恢复之前的选择
            index = self.preset_task_combo.findText(current_selection)
            if index != -1:
                self.preset_task_combo.setCurrentIndex(index)
            else:
                self.preset_task_combo.setCurrentIndex(-1) # 默认不选中
        
        self.preset_task_combo.blockSignals(False)
        self._on_preset_selection_changed(self.preset_task_combo.currentText())
        self._update_task_buttons_state() # 确保按钮状态在加载后更新

    def _get_preset_tasks(self, preset_name: str) -> list | None:
        """根据名称从 configs_data 获取预设任务列表的副本"""
        preset_map = self._get_preset_map()
        tasks = preset_map.get(preset_name)
        # 返回一个副本以避免意外修改
        return list(tasks) if tasks else None

    @Slot()
    def _on_preset_selection_changed(self, text: str):
        """预设下拉框选择变化时更新按钮状态和工具提示"""
        self._update_task_buttons_state()
        preset_name = text

        if not preset_name or not self.preset_task_combo.isEnabled() or "无可用" in preset_name:
            self.preset_task_combo.setToolTip("") # 清除
            return

        tasks = self._get_preset_tasks(preset_name)
        if not tasks:
            self.preset_task_combo.setToolTip(f"预设 '{preset_name}' 为空")
            return

        try:
            tooltip_lines = [f"预设「{preset_name}」内容:"]
            for task in tasks:
                task_str = f"{list(task)}" 
                tooltip_lines.append(task_str)
            tooltip_text = "\n".join(tooltip_lines)
            self.preset_task_combo.setToolTip(tooltip_text)
            
        except Exception:
            self.preset_task_combo.setToolTip(f"无法预览预设 '{preset_name}'")

    @Slot()
    def _on_apply_preset_clicked(self):
        """应用选中的预设到当前任务列表"""
        preset_name = self.preset_task_combo.currentText()
        if not preset_name or not self.preset_task_combo.isEnabled():
            return
            
        tasks_to_apply = self._get_preset_tasks(preset_name)
        if tasks_to_apply is None: return
        # 为 settings_data 创建 CommentedSeq
        new_task_list = CommentedSeq()
        for task in tasks_to_apply:
            new_task_item = CommentedSeq(task)
            new_task_item.fa.set_flow_style()
            new_task_list.append(new_task_item)

        self._handle_value_change('daily_automation.normal_fight_tasks', new_task_list)
        self.populate_tasks_table(new_task_list)

    @Slot()
    def _on_save_preset_clicked(self):
        """将当前任务列表保存为新预设"""
        current_tasks = self.settings_data.get('daily_automation', {}).get('normal_fight_tasks', [])
        if not current_tasks: return

        preset_map = self._get_preset_map()
        existing_names = list(preset_map.keys())

        validator = PresetValidator(existing_names)
        dialog = ValidationInputDialog(self, 
                                     title="新建预设", 
                                     prompt="请输入预设名称:", 
                                     validator=validator)
        if dialog.exec() == QDialog.Accepted:
            new_name = dialog.get_confirmed_value()
            if new_name:
                # 为 ui_configs.yaml 创建 CommentedSeq
                tasks_copy = self.yaml_manager.seq() # 使用 .seq() 创建 CommentedSeq
                for task in current_tasks:
                    inner_task = self.yaml_manager.seq(task) # 同样
                    inner_task.fa.set_flow_style()
                    tasks_copy.append(inner_task)
                
                preset_map[new_name] = tasks_copy
                self._save_configs()
                self._load_presets_to_combo()
                self.preset_task_combo.setCurrentText(new_name)
                self.log_message_signal.emit(f"已保存预设 '{new_name}'")

    @Slot()
    def _on_delete_preset_clicked(self):
        """删除选中的预设"""
        preset_name = self.preset_task_combo.currentText()
        if not preset_name or not self.preset_task_combo.isEnabled():
            return

        preset_map = self._get_preset_map()
        
        if preset_name in preset_map:
            del preset_map[preset_name]
            self._save_configs()
            self._load_presets_to_combo() # 会自动更新按钮状态

    def _delete_preset_pre_condition_check(self):
        """只有在选中了有效预设时才允许进入确认状态"""
        return self.preset_task_combo.currentIndex() != -1 and self.preset_task_combo.isEnabled()

    def get_start_button(self):
        """返回启动按钮控件"""
        return self.daily_task_button

    def get_script_module_path(self):
        """返回脚本的模块路径"""
        return "scripts.auto_daily"