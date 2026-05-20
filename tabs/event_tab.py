import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QLineEdit
)
from PySide6.QtCore import Qt, Signal, Slot
from pathlib import Path
from tabs.components.check_box import CustomCheckBox
from tabs.components.spin_box import CustomSpinBox
from tabs.components.combo_box import CustomComboBox
from tabs.components.base_task_tab import BaseTaskTab
from utils.ui_utils import create_form_layout, create_group
from utils.config_utils import update_config_value, save_config, validate_and_save_line_edit
from utils.plan_utils import get_backend_plans_dir, list_directory, merge_lists

class EventTab(BaseTaskTab):
    """活动挂机选项卡"""

    log_message_signal = Signal(str)

    def __init__(self, settings_data, settings_path, configs_data, configs_path, yaml_manager, parent=None):
        """初始化活动选项卡"""
        super().__init__(parent)
        self.settings_data = settings_data
        self.settings_path = settings_path
        self.configs_data = configs_data
        self.configs_path = configs_path
        self.yaml_manager = yaml_manager
        self.event_plans_dir = None
        self.backend_event_plans_dir = None

        # 默认参数和范围
        self.BATTLE_COUNT_RANGE = (1, 999)
        self.BONUS_INTERVAL_RANGE = (300, 99999)
        self.BATTLE_COUNT_DEFAULT_SAVE = 100
        self.BATTLE_COUNT_DEFAULT_ARG = "100"
        self.BONUS_INTERVAL_DEFAULT_SAVE = 1800
        self.BONUS_INTERVAL_DEFAULT_ARG = "1800"

        self._setup_ui()
        self._connect_signals()
        self._load_data_to_ui()

    def _setup_ui(self):
        """构建UI界面，包括所有设置项和启动按钮"""
        # 主布局
        self.setObjectName("EventTab")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 启动按钮
        self.event_button = QPushButton("启动活动")
        self.event_button.setProperty("class", "StartStopButton")
        self.event_button.setProperty("running", False)
        self.event_button.setObjectName("活动")
        button_layout = QVBoxLayout()
        button_layout.addWidget(self.event_button)
        button_group = create_group(title=None, content=button_layout, margins=(15, 0, 15, 0))
        left_layout.addWidget(button_group)
        left_layout.addSpacing(10)

        # 活动设置控件
        self.event_folder_combo = CustomComboBox()
        self.event_task_combo = CustomComboBox()
        self.fleet_id_spin = CustomSpinBox()
        self.fleet_id_spin.setRange(1, 4)

        self.battle_count_input = QLineEdit()
        self.battle_count_input.setPlaceholderText("100")

        self.reuse_daily_settings_cb = CustomCheckBox("复用部分日常设置")

        self.bonus_check_interval_input = QLineEdit()
        self.bonus_check_interval_input.setPlaceholderText("1800")

        # 活动设置布局
        event_settings_layout = create_form_layout([
            {'widget': (QLabel("选择活动:"), self.event_folder_combo), 'description': "选择具体活动，以日期区分"},
            {'widget': (QLabel("选择任务:"), self.event_task_combo), 'description': "选择具体的任务计划"},
            {'widget': (QLabel("出征舰队:"), self.fleet_id_spin), 'description': "选择出征的舰队编号"},
            {'widget': (QLabel("战斗次数:"), self.battle_count_input), 'description': "执行任务计划的战斗次数<br>默认100，范围[1, 999]"},
            {'widget': self.reuse_daily_settings_cb, 'description': "复用日常中的自动开启战役支援和500船上限设置"},
            {'widget': (QLabel("检查远征间隔:"), self.bonus_check_interval_input), 'description': "远征的检查间隔时间(s)<br>默认1800，范围[300, 99999]"},
        ])
        left_layout.addWidget(create_group("活动设置", event_settings_layout))
        left_layout.addStretch()

        # 右侧面板
        right_panel = QWidget()
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        """连接所有UI控件的信号到对应的处理函数"""
        # 下拉框、复选框、数值调节框信号连接
        self.event_folder_combo.currentTextChanged.connect(self._on_event_folder_changed)
        self.event_task_combo.currentTextChanged.connect(
            lambda text: self._handle_value_change("event_automation.plan_name", text) if text and "未找到" not in text else None
        )
        self.fleet_id_spin.valueChanged.connect(
            lambda val: self._handle_value_change("event_automation.fleet_id", val)
        )
        self.reuse_daily_settings_cb.toggled.connect(
            lambda checked: self._handle_value_change("event_automation.reuse_daily_settings", checked)
        )

        # 输入框在失去焦点时进行验证和保存
        self.battle_count_input.editingFinished.connect(self._save_battle_count)
        self.bonus_check_interval_input.editingFinished.connect(self._save_bonus_interval)

    def _save_battle_count(self):
        """验证并保存战斗次数"""
        validate_and_save_line_edit(
            line_edit=self.battle_count_input,
            config_path="event_automation.battle_count",
            settings_data=self.configs_data,
            settings_path=self.configs_path,
            yaml_manager=self.yaml_manager,
            default_value=self.BATTLE_COUNT_DEFAULT_SAVE,
            clamp_range=self.BATTLE_COUNT_RANGE,
            log_signal=self.log_message_signal
        )

    def _save_bonus_interval(self):
        """验证并保存检查远征间隔"""
        validate_and_save_line_edit(
            line_edit=self.bonus_check_interval_input,
            config_path="event_automation.bonus_check_interval",
            settings_data=self.configs_data,
            settings_path=self.configs_path,
            yaml_manager=self.yaml_manager,
            default_value=self.BONUS_INTERVAL_DEFAULT_SAVE,
            clamp_range=self.BONUS_INTERVAL_RANGE,
            log_signal=self.log_message_signal
        )

    def _load_data_to_ui(self):
        """从 'user_configs.yaml' 加载初始值到UI控件"""
        self.event_folder_combo.blockSignals(True)
        self.event_task_combo.blockSignals(True)

        event = self.configs_data.get('event_automation', {})
        saved_folder = event.get('event_folder')
        saved_plan = event.get('plan_name')

        self._populate_event_folders_combo()
        if saved_folder and self.event_folder_combo.findText(saved_folder) != -1:
            self.event_folder_combo.setCurrentText(saved_folder)
        
        self._on_event_folder_changed(self.event_folder_combo.currentText())

        if saved_plan and self.event_task_combo.findText(saved_plan) != -1:
            self.event_task_combo.setCurrentText(saved_plan)
        elif self.event_task_combo.count() > 0:
            self.event_task_combo.setCurrentIndex(0)
            self._handle_value_change("event_automation.plan_name", self.event_task_combo.currentText())

        self.fleet_id_spin.setValue(event.get('fleet_id', 1))
        self.battle_count_input.setText(str(event.get('battle_count', self.BATTLE_COUNT_DEFAULT_SAVE)))
        self.reuse_daily_settings_cb.setChecked(event.get('reuse_daily_settings', False))
        self.bonus_check_interval_input.setText(str(event.get('bonus_check_interval', self.BONUS_INTERVAL_DEFAULT_SAVE)))
        
        self.event_folder_combo.blockSignals(False)
        self.event_task_combo.blockSignals(False)

    def _handle_value_change(self, path, value):
        """统一处理配置值的更新和保存"""
        try:
            update_config_value(self.configs_data, path, value)
            save_config(self.yaml_manager, self.configs_data, self.configs_path)
        except Exception as e:
            self.log_message_signal.emit(str(e))

    def _populate_event_folders_combo(self):
        """从用户方案目录和后端内置方案目录加载活动文件夹名称到下拉框中"""
        plan_root = self.settings_data.get('plan_root', '')
        self.event_plans_dir = Path(plan_root) / 'event' if plan_root else None
        backend_plans = get_backend_plans_dir()
        self.backend_event_plans_dir = Path(backend_plans) / 'event' if backend_plans else None

        self.event_folder_combo.clear()
        self.event_folder_combo.setEnabled(True)

        # 从用户方案目录读取活动文件夹
        user_folders = []
        if self.event_plans_dir and self.event_plans_dir.is_dir():
            try:
                user_folders = [d.name for d in self.event_plans_dir.iterdir() if d.is_dir()]
            except Exception as e:
                self.log_message_signal.emit(f"错误: 读取用户活动文件夹时出错: {e}")

        # 从后端内置方案目录读取活动文件夹
        backend_folders = list_directory(self.backend_event_plans_dir, filter_func=lambda p: os.path.isdir(p))

        # 合并去重，用户目录优先级更高
        all_folders = merge_lists(user_folders, backend_folders)

        if not all_folders:
            self.event_folder_combo.addItem("没有可用的活动")
            self.event_folder_combo.setEnabled(False)
        else:
            self.event_folder_combo.addItems(sorted(all_folders, reverse=True))

    def _populate_event_tasks_combo(self, folder_name):
        """根据文件夹名称，填充任务计划下拉菜单（优先用户目录，其次后端内置目录）"""
        self.event_task_combo.clear()
        if not folder_name or "未找到" in folder_name or "没有可用" in folder_name:
            self.event_task_combo.setEnabled(False)
            return

        # 从用户方案目录查找任务文件
        user_files = []
        if self.event_plans_dir:
            user_task_dir = os.path.join(self.event_plans_dir, folder_name)
            if os.path.isdir(user_task_dir):
                try:
                    user_files = [f for f in os.listdir(user_task_dir) if f.endswith(('.yml', '.yaml'))]
                except Exception as e:
                    self.log_message_signal.emit(f"错误: 读取用户任务文件时出错: {e}")

        # 从后端内置方案目录查找任务文件
        backend_files = []
        if self.backend_event_plans_dir:
            backend_task_dir = os.path.join(self.backend_event_plans_dir, folder_name)
            if os.path.isdir(backend_task_dir):
                try:
                    backend_files = [f for f in os.listdir(backend_task_dir) if f.endswith(('.yml', '.yaml'))]
                except Exception as e:
                    self.log_message_signal.emit(f"错误: 读取后端任务文件时出错: {e}")

        # 合并去重，用户文件优先级更高
        all_files = merge_lists(user_files, backend_files)

        if not all_files:
            self.event_task_combo.addItem("无效的文件夹")
            self.event_task_combo.setEnabled(False)
            return

        plan_names = sorted([os.path.splitext(f)[0] for f in all_files])
        self.event_task_combo.addItems(plan_names)
        self.event_task_combo.setEnabled(True)

    def _on_event_folder_changed(self, folder_name):
        """当活动文件夹选择变化时，保存新文件夹并级联更新和保存任务"""
        self._populate_event_tasks_combo(folder_name)
        
        # 只有在有效文件夹名时才保存
        if folder_name and "未找到" not in folder_name and "没有可用" not in folder_name and "无效" not in folder_name:
            self._handle_value_change("event_automation.event_folder", folder_name)

        if self.event_task_combo.count() > 0 and self.event_task_combo.isEnabled():
            self.event_task_combo.blockSignals(True)
            self.event_task_combo.setCurrentIndex(0)
            self.event_task_combo.blockSignals(False)
            new_plan_name = self.event_task_combo.currentText()
            self._handle_value_change("event_automation.plan_name", new_plan_name)
        else:
            self._handle_value_change("event_automation.plan_name", None)

    @Slot()
    def refresh_task_plans(self):
        """刷新活动文件夹和任务计划的下拉列表"""
        self._populate_event_folders_combo()
        current_folder = self.event_folder_combo.currentText()
        self._on_event_folder_changed(current_folder)

    def get_script_args(self):
        """从UI控件收集并返回要传递给脚本的参数列表"""
        event_folder = self.event_folder_combo.currentText()
        event_identifier = f"{event_folder[:4]}_{event_folder[4:]}"
        plan_name = self.event_task_combo.currentText()

        # 查找方案文件的绝对路径（优先用户目录，其次后端内置目录）
        plan_abs_path = None
        for ext in ('.yml', '.yaml'):
            if self.event_plans_dir:
                candidate = os.path.join(self.event_plans_dir, event_folder, plan_name + ext)
                if os.path.isfile(candidate):
                    plan_abs_path = candidate
                    break
            if plan_abs_path is None and self.backend_event_plans_dir:
                candidate = os.path.join(self.backend_event_plans_dir, event_folder, plan_name + ext)
                if os.path.isfile(candidate):
                    plan_abs_path = candidate
                    break

        fleet_id = str(self.fleet_id_spin.value())
        battle_count_text = self.battle_count_input.text()
        battle_count_arg = self.BATTLE_COUNT_DEFAULT_ARG if not battle_count_text else battle_count_text
        reuse_daily_settings = str(self.reuse_daily_settings_cb.isChecked())
        bonus_interval_text = self.bonus_check_interval_input.text()
        bonus_interval_arg = self.BONUS_INTERVAL_DEFAULT_ARG if not bonus_interval_text else bonus_interval_text

        return [
            event_identifier,
            plan_abs_path or plan_name,
            fleet_id,
            battle_count_arg,
            reuse_daily_settings,
            bonus_interval_arg
        ]


    def get_start_button(self):
        """返回启动按钮控件，供主窗口连接信号"""
        return self.event_button

    def get_script_module_path(self):
        """返回此选项卡要运行的脚本的模块路径"""
        return "scripts.event"