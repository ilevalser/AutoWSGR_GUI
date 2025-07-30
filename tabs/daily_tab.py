import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QApplication,
    QTableWidgetItem, QHeaderView, QPushButton, QLabel, QSizePolicy, QLineEdit
)
from PySide6.QtCore import Qt, Signal, QEvent, Slot
from PySide6.QtGui import QIntValidator
from ruamel.yaml.comments import CommentedSeq

from tabs.components.check_box import CustomCheckBox
from tabs.components.spin_box import CustomSpinBox
from tabs.components.combo_box import CustomComboBox
from tabs.components.base_task_tab import BaseTaskTab
from utils.ui_utils import create_form_layout, create_group, ConfirmButtonManager
from utils.config_utils import update_config_value, save_config
from constants import BATTLE_TYPES

class DailyTab(BaseTaskTab):
    """日常挂机设置选项卡"""

    log_message_signal = Signal(str)  # 日志信号，用于输出错误或提示信息

    def __init__(self, settings_data, settings_path, yaml_manager, parent=None):
        """初始化 DailyTab 选项卡"""
        super().__init__(parent)
        self.settings_data = settings_data
        self.settings_path = settings_path
        self.yaml_manager = yaml_manager
        plan_root = self.settings_data.get('plan_root')
        self.normal_plans_dir = plan_root + '/normal_fight' if plan_root else None

        # 状态变量
        self.normal_plans_dir = None
        self.currently_selected_row = -1
        self.edit_mode = None
        self.editing_row_index = -1

        self._setup_ui()
        self.remove_button_manager = ConfirmButtonManager(self.remove_task_btn)
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

        # 左侧设置表单布局
        daily_settings_layout = create_form_layout([
            (self.auto_expedition_cb, "定时检查远征并自动收取"),
            (self.auto_gain_bonus_cb, "有任务奖励时自动领取"),
            (self.auto_bath_repair_cb, "在无其他任务时自动修理破损舰船"),
            (self.auto_set_support_cb, "出征前自动设置战役支援"),
            (self.auto_battle_cb, "根据战役类型自动进行每日战役"),
            ((QLabel("战役选择:"), self.battle_type_combo), "选择每日战役的类型"),
            (self.auto_exercise_cb, "自动进行演习"),
            ((QLabel("演习出征舰队:"), self.exercise_fleet_id_spin), "选择用于演习的舰队编号"),
            (self.auto_normal_fight_cb, "根据右侧任务列表自动出征"),
            ((QLabel("快修消耗上限:"), self.quick_repair_limit_input), "设置自动使用快速修理的最大数量，0为无上限"),
            (self.stop_max_ship_cb, "当捞取达到每日舰船掉落上限时停止挂机"),
            (self.stop_max_loot_cb, "当捞取达到每日胖次掉落上限时停止挂机")
        ])
        left_layout.addWidget(create_group("日常挂机设置", daily_settings_layout))
        left_layout.addStretch()

        # 右侧面板：任务列表与编辑
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 任务列表表格
        self.tasks_table = QTableWidget()
        self.tasks_table.setColumnCount(3)
        self.tasks_table.setHorizontalHeaderLabels(["任务", "出征舰队", "出征次数"])
        self.tasks_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.tasks_table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.tasks_table.verticalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self.tasks_table.setShowGrid(False)
        self.tasks_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.tasks_table.horizontalHeader().setSectionsClickable(False)
        self.tasks_table.verticalHeader().setSectionsClickable(False)
        self.tasks_table.horizontalHeader().setHighlightSections(False)
        self.tasks_table.verticalHeader().setHighlightSections(False)
        self.tasks_table.setCornerButtonEnabled(False)
        self.tasks_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tasks_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.tasks_table.setFixedHeight(260)

        # 禁止拖动改变选择
        def ignore_drag_selection(event):
            if event.buttons() & Qt.MouseButton.LeftButton:
                return
            QTableWidget.mouseMoveEvent(self.tasks_table, event)
        self.tasks_table.mouseMoveEvent = ignore_drag_selection

        # 任务列表操作按钮
        tasks_buttons_layout = QHBoxLayout()
        self.add_task_btn = QPushButton("添加任务")
        self.add_task_btn.setCheckable(True)
        self.add_task_btn.setProperty("class", "ShortButton")
        self.edit_task_btn = QPushButton("编辑选中")
        self.edit_task_btn.setCheckable(True)
        self.edit_task_btn.setProperty("class", "ShortButton")
        self.remove_task_btn = QPushButton("删除选中")
        self.remove_task_btn.setProperty("class", "ShortButton")
        self.move_up_btn = QPushButton("上移一行")
        self.move_up_btn.setProperty("class", "ShortButton")
        self.move_down_btn = QPushButton("下移一行")
        self.move_down_btn.setProperty("class", "ShortButton")

        # 添加所有按钮到布局
        button_list = [
            self.add_task_btn, self.edit_task_btn,
            self.move_up_btn, self.move_down_btn, self.remove_task_btn
        ]
        for btn in button_list:
            btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            tasks_buttons_layout.addWidget(btn)

        # 任务列表组装
        task_list_content_layout = QVBoxLayout()
        task_list_content_layout.setContentsMargins(0, 0, 0, 0)
        task_list_content_layout.addWidget(self.tasks_table)
        task_list_content_layout.addLayout(tasks_buttons_layout)
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
            ((QLabel("任务:"), self.task_file_combo), None),
            ((QLabel("出征舰队:"), self.fleet_spinbox), None),
            ((QLabel("出征次数:"), self.count_input), None)
        ]
        form_layout = create_form_layout(editor_items_info, column_stretches=(1, 1))

        # 编辑模块按钮
        edit_module_content_layout = QVBoxLayout()
        edit_module_content_layout.setContentsMargins(0, 0, 0, 0)
        module_buttons_layout = QHBoxLayout()
        module_buttons_layout.addStretch()
        self.ok_button = QPushButton("确定")
        self.ok_button.setProperty("class", "OkCancelButton")
        self.cancel_button = QPushButton("取消")
        self.cancel_button.setProperty("class", "OkCancelButton")
        module_buttons_layout.addWidget(self.ok_button)
        module_buttons_layout.addWidget(self.cancel_button)
        edit_module_content_layout.addLayout(form_layout)
        edit_module_content_layout.addLayout(module_buttons_layout)

        # 编辑模块组装
        self.edit_task_module = create_group(
            "任务编辑", edit_module_content_layout, margins=(5, 15, 5, 15)
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
            lambda checked: self._handle_value_change("daily_automation.auto_expedition", checked)
        )
        self.auto_gain_bonus_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_gain_bonus", checked)
        )
        self.auto_bath_repair_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_bath_repair", checked)
        )
        self.auto_set_support_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_set_support", checked)
        )
        self.auto_battle_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_battle", checked)
        )
        self.battle_type_combo.currentTextChanged.connect(
            lambda text: self._handle_value_change('daily_automation.battle_type', text)
        )
        self.auto_exercise_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_exercise", checked)
        )
        self.exercise_fleet_id_spin.valueChanged.connect(
            lambda val: self._handle_value_change("daily_automation.exercise_fleet_id", val)
        )
        self.auto_normal_fight_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.auto_normal_fight", checked)
        )
        self.quick_repair_limit_input.editingFinished.connect(self._save_quick_repair_limit)
        self.stop_max_ship_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.stop_max_ship", checked)
        )
        self.stop_max_loot_cb.toggled.connect(
            lambda checked: self._handle_value_change("daily_automation.stop_max_loot", checked)
        )

        # 任务管理按钮信号
        self.add_task_btn.clicked.connect(self._on_add_task_clicked)
        self.edit_task_btn.clicked.connect(self._on_edit_task_clicked)
        self.move_up_btn.clicked.connect(self._on_move_task_up)
        self.move_down_btn.clicked.connect(self._on_move_task_down)
        self.remove_button_manager.confirmed_click.connect(self._remove_task_row)

        # 表格交互信号
        self.tasks_table.cellClicked.connect(self._handle_cell_click)
        self.tasks_table.itemSelectionChanged.connect(self._on_selection_changed)

        # 编辑模块按钮信号
        self.ok_button.clicked.connect(self._on_accept_edit)
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
        self._update_task_buttons_state()

    def populate_tasks_table(self, tasks):
        """将任务列表数据填充到表格中"""
        self.tasks_table.setRowCount(len(tasks))
        for row, task in enumerate(tasks or []):
            for col, item_data in enumerate(task):
                item = QTableWidgetItem(str(item_data))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.tasks_table.setItem(row, col, item)

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
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.remove_button_manager.is_confirming():
                clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())
                if clicked_widget != self.remove_task_btn:
                    self.remove_button_manager.reset_state()
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

        if not current_tasks:
            return

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
            self._update_task_buttons_state()

    # =========================
    # 任务列表核心交互逻辑
    # =========================

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

    def _handle_cell_click(self, row, column):
        """处理表格单击，实现选中/取消选中切换"""
        if row == self.currently_selected_row:
            self.tasks_table.blockSignals(True)
            self.tasks_table.clearSelection()
            self.tasks_table.blockSignals(False)
            self.currently_selected_row = -1
            self._reset_to_view_mode()
            self._update_task_buttons_state()
        else:
            self.currently_selected_row = row

    def _on_selection_changed(self):
        """响应表格选择变化，更新 UI 状态"""
        selected_rows = self.tasks_table.selectionModel().selectedRows()
        if not selected_rows:
            self.currently_selected_row = -1
            self._reset_to_view_mode()
        else:
            current_row = selected_rows[0].row()
            if self.edit_mode == 'add':
                self._reset_to_view_mode()
            elif self.edit_task_module.isVisible() and self.edit_mode == 'edit':
                self._load_task_data_to_editor(current_row)
        self._update_task_buttons_state()

    def _update_task_buttons_state(self):
        """根据是否有行被选中，更新按钮的可用性"""
        is_item_selected = bool(self.tasks_table.selectedItems())
        self.edit_task_btn.setEnabled(is_item_selected)
        self.remove_task_btn.setEnabled(is_item_selected)
        self.move_up_btn.setEnabled(is_item_selected)
        self.move_down_btn.setEnabled(is_item_selected)

    def _on_add_task_clicked(self):
        """处理“添加任务”按钮点击，进入“添加”模式"""
        if self.edit_task_module.isVisible() and self.edit_mode == 'add':
            self._reset_to_view_mode()
            return
        self.tasks_table.clearSelection()
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
        current_row = self.tasks_table.currentRow()
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
        if not task_name or "未找到" in task_name:
            self.log_message_signal.emit("错误：未选择有效的任务计划。")
            return
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

    def _remove_task_row(self):
        """处理“删除选中”按钮点击，包含二次确认"""
        current_row = self.tasks_table.currentRow()
        if current_row < 0:
            return
        current_tasks = self.settings_data['daily_automation']['normal_fight_tasks']
        del current_tasks[current_row]
        new_value = current_tasks if current_tasks else []
        self._handle_value_change('daily_automation.normal_fight_tasks', new_value)
        self.populate_tasks_table(current_tasks)
        self.tasks_table.clearSelection()

    def _on_move_task_up(self):
        """处理“上移一行”按钮点击"""
        current_row = self.tasks_table.currentRow()
        if current_row > 0:
            current_tasks = self.settings_data['daily_automation']['normal_fight_tasks']
            current_tasks.insert(current_row - 1, current_tasks.pop(current_row))
            self._handle_value_change('daily_automation.normal_fight_tasks', current_tasks)
            self.populate_tasks_table(current_tasks)
            new_row_index = current_row - 1
            self.tasks_table.setCurrentCell(new_row_index, 0)
            self.currently_selected_row = new_row_index

    def _on_move_task_down(self):
        """处理“下移一行”按钮点击"""
        current_row = self.tasks_table.currentRow()
        if 0 <= current_row < self.tasks_table.rowCount() - 1:
            current_tasks = self.settings_data['daily_automation']['normal_fight_tasks']
            current_tasks.insert(current_row + 1, current_tasks.pop(current_row))
            self._handle_value_change('daily_automation.normal_fight_tasks', current_tasks)
            self.populate_tasks_table(current_tasks)
            new_row_index = current_row + 1
            self.tasks_table.setCurrentCell(new_row_index, 0)
            self.currently_selected_row = new_row_index

    def get_start_button(self):
        """返回启动按钮控件"""
        return self.daily_task_button

    def get_script_module_path(self):
        """返回脚本的模块路径"""
        return "scripts.auto_daily"