from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QApplication
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QEvent
from ruamel.yaml.comments import CommentedSeq
from ruamel.yaml.scalarstring import DoubleQuotedScalarString

from tabs.components.base_task_tab import BaseTaskTab
from tabs.components.fleet_config_widget import FleetConfigWidget
from tabs.components.check_box import CustomCheckBox
from tabs.components.spin_box import CustomSpinBox
from tabs.components.combo_box import CustomComboBox
from utils.ui_utils import create_form_layout, create_group
from utils.config_utils import update_config_value, save_config

class DecisiveBattleTab(BaseTaskTab):
    """决战设置选项卡"""
    log_message_signal = Signal(str)

    def __init__(
        self, settings_data, settings_path,
        ui_configs_data, ui_configs_path,
        yaml_manager, parent=None
    ):
        """初始化决战设置选项卡"""
        super().__init__(parent)
        self.settings_data = settings_data
        self.ui_configs_data = ui_configs_data
        self.yaml_manager = yaml_manager
        self.settings_path = settings_path
        self.ui_configs_path = ui_configs_path

        self._setup_ui()
        self._connect_signals()
        self._load_data_to_ui()
        QApplication.instance().installEventFilter(self)

    def _setup_ui(self):
        """构建UI界面"""
        # 主布局
        self.setObjectName("DecisiveBattleTab")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 左侧面板（参数与按钮）
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 启动按钮与警告标签
        self.start_button = QPushButton("启动决战")
        self.start_button.setProperty("class", "StartStopButton")
        self.start_button.setProperty("running", False)
        self.start_button.setObjectName("决战")

        self.fleet_warning_label = QLabel("❌ 编组舰船过少，出战舰队无法满编")
        self.fleet_warning_label.setObjectName("WarningLabel")
        self.fleet_warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.fleet_warning_label.setMaximumHeight(0)  # 初始隐藏

        combined_control_layout = QVBoxLayout()
        combined_control_layout.setContentsMargins(0, 0, 0, 0)
        combined_control_layout.addWidget(self.start_button)

        warning_layout = QHBoxLayout()
        warning_layout.addWidget(self.fleet_warning_label)
        combined_control_layout.addLayout(warning_layout)
        control_group = create_group(content=combined_control_layout, margins=(15, 0, 15, 0))
        left_layout.addWidget(control_group)

        # 决战参数设置
        self.sortie_count_spin = CustomSpinBox()  # 出击次数
        self.sortie_count_spin.setRange(1, 12)
        self.chapter_spin = CustomSpinBox()       # 决战章节
        self.chapter_spin.setRange(4, 6)
        self.repair_level_combo = CustomComboBox()  # 维修策略
        self.repair_level_combo.addItems(["中破修", "大破修"])

        params_layout = create_form_layout([
            {'widget': (QLabel("出击次数:"), self.sortie_count_spin), 'description': "设置决战的出击次数"},
            {'widget': (QLabel("决战章节:"), self.chapter_spin), 'description': "选择要进行的决战章节，仅支持4、5和6"},
            {'widget': (QLabel("维修策略:"), self.repair_level_combo), 'description': "选择舰船在何种状态下进行维修，自动使用快修"}
        ])
        left_layout.addWidget(create_group("决战任务设置", params_layout))

        # 其他设置
        self.full_destroy_cb = CustomCheckBox("船坞满时解装")
        self.useful_skill_cb = CustomCheckBox("充分利用教官技能")
        self.useful_skill_strict_cb = CustomCheckBox("严格利用教官技能")
        self.no_quick_repair_cb = CustomCheckBox("不使用快速修理")

        other_settings_layout = create_form_layout([
            {
                'widget': self.full_destroy_cb,
                'description': "此设置独立于“全局设置”中的“船坞满时解装”,仅在决战生效<br>解装模式及黑白名单依旧生效"
            },
            {
                'widget': self.useful_skill_cb,
                'description': "开启后在第1小关时，随机到的必须为一二级舰队中的船<br>其余地图至少一半的船为一级舰队中的船"
            },
            {
                'widget': self.useful_skill_strict_cb,
                'description': "只能在“充分利用教官技能”启用时勾选<br>开启后在第1小关时，教官技能不能获取+1强化的船"
            },
            {
                'widget': self.no_quick_repair_cb,
                'description': "只使用澡堂，自然等待修理完成（利用task功能）"
            }
        ])
        left_layout.addWidget(create_group("其他设置", other_settings_layout))
        left_layout.addStretch()

        # 右侧面板（舰队配置）
        custom_ships = self.ui_configs_data.get('custom_names', [])
        initial_custom_ships = [str(item) for item in custom_ships] if isinstance(custom_ships, (list, CommentedSeq)) else []
        self.fleet_config_controller = FleetConfigWidget(initial_custom_ships, self)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        fleet_config_layout = self.fleet_config_controller.get_layout()
        fleet_config_group = create_group("决战舰队编组", fleet_config_layout)
        right_layout.addWidget(fleet_config_group)
        right_layout.addStretch(1)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        """连接所有UI控件的信号到其处理函数"""
        # 参数控件信号
        self.sortie_count_spin.valueChanged.connect(
            lambda val: self._handle_value_change(
                self.ui_configs_data, self.ui_configs_path, "sortie_times", val
            )
        )
        self.chapter_spin.valueChanged.connect(
            lambda val: self._handle_value_change(
                self.settings_data, self.settings_path, "decisive_battle.chapter", val
            )
        )
        self.repair_level_combo.currentIndexChanged.connect(
            lambda index: self._handle_value_change(
                self.settings_data, self.settings_path, "decisive_battle.repair_level", index + 1
            )
        )
        self.full_destroy_cb.toggled.connect(
            lambda checked: self._handle_value_change(
                self.settings_data, self.settings_path, "decisive_battle.full_destroy", checked
            )
        )
        self.useful_skill_cb.toggled.connect(self._on_useful_skill_toggled)
        self.useful_skill_strict_cb.toggled.connect(
            lambda checked: self._handle_value_change(
                self.settings_data, self.settings_path, "decisive_battle.useful_skill_strict", checked
            )
        )
        self.no_quick_repair_cb.toggled.connect(
            lambda checked: self._handle_value_change(
                self.ui_configs_data, self.ui_configs_path, "use_quick_repair", not checked
            )
        )
        # 舰队配置信号
        self.fleet_config_controller.level1_fleet_changed.connect(
            lambda data: self._save_list_to_config(self.settings_data, self.settings_path, "decisive_battle.level1", data, style='flow')
        )
        self.fleet_config_controller.level2_fleet_changed.connect(
            lambda data: self._save_list_to_config(self.settings_data, self.settings_path, "decisive_battle.level2", data, style='flow')
        )
        self.fleet_config_controller.flagship_priority_changed.connect(
            lambda data: self._save_list_to_config(self.settings_data, self.settings_path, "decisive_battle.flagship_priority", data, style='flow')
        )
        self.fleet_config_controller.custom_ships_changed.connect(
            lambda data: self._save_list_to_config(self.ui_configs_data, self.ui_configs_path, "custom_names", data, style='block')
        )
        self.fleet_config_controller.log_message_signal.connect(self.log_message_signal.emit)

    def eventFilter(self, watched, event):
        """事件过滤器，用于处理全局点击事件。"""
        # 警告标签处理
        if self.fleet_warning_label.maximumHeight() > 0 and event.type() == QEvent.Type.MouseButtonPress:
            global_pos = event.globalPosition().toPoint()
            if self.rect().contains(self.mapFromGlobal(global_pos)):
                clicked_widget = QApplication.widgetAt(global_pos)
                is_start_button_click = False
                widget_iterator = clicked_widget
                while widget_iterator is not None:
                    if widget_iterator == self.start_button:
                        is_start_button_click = True
                        break
                    widget_iterator = widget_iterator.parent()
                if not is_start_button_click:
                    self._toggle_warning_label(show=False)
                    return True
        # 转发事件给舰队配置面板
        self.fleet_config_controller.process_app_event(watched, event)
        return False

    def hideEvent(self, event):
        """切换标签页时自动收起警告信息"""
        super().hideEvent(event)
        self._toggle_warning_label(show=False)

    def _load_data_to_ui(self):
        """从配置数据加载初始值到UI控件"""
        self.sortie_count_spin.setValue(self.ui_configs_data.get('sortie_times', 1))
        use_quick_repair = self.ui_configs_data.get('use_quick_repair', True)
        self.no_quick_repair_cb.setChecked(not use_quick_repair)
        decisive = self.settings_data.get('decisive_battle', {})
        self.chapter_spin.setValue(decisive.get('chapter', 6))
        self.repair_level_combo.setCurrentIndex(decisive.get('repair_level', 2) - 1)
        self.full_destroy_cb.setChecked(decisive.get('full_destroy', False))
        is_useful_skill_enabled = decisive.get('useful_skill', False)
        self.useful_skill_cb.setChecked(is_useful_skill_enabled)
        self.useful_skill_strict_cb.setChecked(decisive.get('useful_skill_strict', False))
        self.useful_skill_strict_cb.setEnabled(is_useful_skill_enabled)
        level1 = decisive.get('level1', [])
        level2 = decisive.get('level2', [])
        flagship = decisive.get('flagship_priority', [])
        self.fleet_config_controller.set_fleet_data(level1, level2, flagship)

    def _handle_value_change(self, config_data, file_path, path, value):
        """处理普通值的更新和保存"""
        try:
            update_config_value(config_data, path, value)
            save_config(self.yaml_manager, config_data, file_path)
        except Exception as e:
            self.log_message_signal.emit(str(e))

    def _save_list_to_config(self, config_data, file_path, path, items_list: list, style: str = 'flow'):
        """处理列表值的更新和保存"""
        cs = CommentedSeq([DoubleQuotedScalarString(item) for item in items_list])
        if style == 'flow':
            cs.fa.set_flow_style()
        self._handle_value_change(config_data, file_path, path, cs)

    def _on_useful_skill_toggled(self, checked):
        """教官技能复选框状态改变时的处理"""
        self._handle_value_change(
            self.settings_data, self.settings_path, "decisive_battle.useful_skill", checked
        )
        self.useful_skill_strict_cb.setEnabled(checked)
        if not checked:
            self.useful_skill_strict_cb.setChecked(False)

    def _on_task_toggle(self):
        """重写任务启动/停止的槽函数，在启动前进行检查"""
        if not self._is_fleet_size_valid():
            self._toggle_warning_label(show=True)
            self.log_message_signal.emit(f"\n决战配置错误：舰队数量不满足章节要求！\n已阻止决战启动，请调整舰队编组后重试。\n")
            return
        self._toggle_warning_label(show=False)
        super()._on_task_toggle()

    def _is_fleet_size_valid(self) -> bool:
        """检查舰队数量是否满足章节要求"""
        requirements = {4: 8, 5: 10, 6: 10}
        current_chapter = self.chapter_spin.value()
        required_ships = requirements.get(current_chapter, 10)
        level1_count = self.fleet_config_controller.level1_list.count()
        level2_count = self.fleet_config_controller.level2_list.count()
        total_ships = level1_count + level2_count
        return total_ships >= required_ships

    def _toggle_warning_label(self, show: bool):
        """使用动画显示或隐藏警告标签"""
        target_height = self.fleet_warning_label.sizeHint().height()
        current_height = self.fleet_warning_label.maximumHeight()
        if (show and current_height == target_height) or (not show and current_height == 0):
            return
        self.animation = QPropertyAnimation(self.fleet_warning_label, b"maximumHeight")
        self.animation.setDuration(300)
        self.animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        start_value = self.fleet_warning_label.height()
        end_value = target_height if show else 0
        self.animation.setStartValue(start_value)
        self.animation.setEndValue(end_value)
        self.animation.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)

    def get_start_button(self) -> QPushButton:
        """返回启动按钮控件"""
        return self.start_button

    def get_script_module_path(self) -> str:
        """返回脚本的模块路径"""
        return "scripts.decisive_battle"

    def get_script_args(self) -> list:
        """返回需要传递给脚本的参数列表"""
        sortie_count = str(self.sortie_count_spin.value())
        args = [sortie_count]
        if self.no_quick_repair_cb.isChecked():
            args.append('--use-task-runner')
        return args