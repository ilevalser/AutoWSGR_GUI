from PySide6.QtWidgets import (
    QWidget, QGridLayout, QLineEdit, QPushButton, QLabel,
    QHBoxLayout, QVBoxLayout, QFileDialog
)
from PySide6.QtCore import Qt, Signal
from ruamel.yaml.comments import CommentedSeq
import re
from pathlib import Path

from tabs.components.check_box import CustomCheckBox
from tabs.components.spin_box import CustomSpinBox
from tabs.components.combo_box import CustomComboBox
from utils.ui_utils import create_form_layout, create_group
from utils.config_utils import (
    update_config_value, save_config, validate_and_save_line_edit,
    validate_and_save_text_input
)
from constants import (
    SHIP_DISPLAY_ORDER, CATEGORY_DISPLAY_ORDER,
    SHIP_TYPE_CATEGORIES_LOGIC, LOG_LEVEL, SHIP_NAME_FILE
)

class SettingsTab(QWidget):
    """全局设置选项卡"""
    plan_root_changed = Signal()

    def __init__(self, settings_data, settings_path, configs_data, configs_path, yaml_manager, parent=None):
        super().__init__(parent)
        self.settings_data = settings_data
        self.settings_path = settings_path
        self.configs_data = configs_data
        self.configs_path = configs_path
        self.yaml_manager = yaml_manager
        self.selected_ships = set()
        self._setup_ui()
        self._connect_signals()
        self._load_data_to_ui()

        # 更新船名文件路径
        update_config_value(self.settings_data, 'ship_name_file', SHIP_NAME_FILE.as_posix())
        save_config(self.yaml_manager, self.settings_data, self.settings_path)
        
    def _setup_ui(self):
        """UI构建函数"""
        self.setObjectName("SettingsTab")
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 提前创建所有控件
        self.check_update_cb = CustomCheckBox("自动更新")
        self.debug_cb = CustomCheckBox("启用Debug模式")
        self.log_level_label = QLabel("日志级别:")
        self.log_level_combo = CustomComboBox()
        self.log_level_combo.addItems(LOG_LEVEL)
        self.delay_label = QLabel("延迟时间:")
        self.delay_input = QLineEdit()
        self.delay_input.setPlaceholderText("只能输入正浮点数")
        self.bathroom_feature_label = QLabel("浴室数量:")
        self.bathroom_feature_count_spin = CustomSpinBox()
        self.bathroom_feature_count_spin.setRange(1, 3)
        self.bathroom_count_label = QLabel("修理位总数:")
        self.bathroom_count_spin = CustomSpinBox()
        self.bathroom_count_spin.setRange(1, 12)
        self.emulator_type_label = QLabel("模拟器类型:")
        self.emulator_type_input = QLineEdit()
        self.emulator_name_label = QLabel("模拟器监听地址:")
        self.emulator_name_input = QLineEdit()
        self.emulator_name_input.setPlaceholderText("默认不填")
        self.plan_root_input = QLineEdit()
        self.plan_root_input.setReadOnly(True)
        self.plan_root_button = QPushButton("选择文件夹")
        self.plan_root_button.setObjectName("plans_button")
        self.dock_full_destroy_cb = CustomCheckBox("船坞满时解装")
        self.destroy_ship_work_mode_label = QLabel("解装模式:")
        self.destroy_ship_work_mode_combo = CustomComboBox()
        self.destroy_mode_items = [("不启用", 0), ("黑名单", 1), ("白名单", 2)]
        self.destroy_ship_work_mode_combo.addItems([item[0] for item in self.destroy_mode_items])

        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        group1_content = create_form_layout([
            (self.check_update_cb, "启动任务前自动更新AutoWSGR"),
            (self.debug_cb, "启用后会输出更详细的日志信息"),
            ((self.log_level_label, self.log_level_combo), "推荐使用INFO"),
            ((self.delay_label, self.delay_input), "脚本延迟时间(s)，若模拟器卡顿可调高<br>默认为1.5s")
        ])
        group2_content = create_form_layout([
            ((self.bathroom_feature_label, self.bathroom_feature_count_spin), "共3个：罗马浴室、和风温泉和曲径通幽"),
            ((self.bathroom_count_label, self.bathroom_count_spin), "购买浴室会送1个，3个浴室共12个")
        ])
        group3_content = create_form_layout([
            ((self.emulator_type_label, self.emulator_type_input), "填写名称，类型有：<br>雷电、蓝叠、MuMu、云手机和其他"),
            ((self.emulator_name_label, self.emulator_name_input), "模拟器使用多开功能时填写")
        ])

        left_layout.addWidget(create_group("AutoWSGR设置", group1_content))
        left_layout.addWidget(create_group("修理设置", group2_content))
        left_layout.addWidget(create_group("模拟器设置", group3_content))

        # 右侧面板
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(5, 5, 5, 5)
        right_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        plan_settings_layout = QHBoxLayout()
        plan_settings_layout.setContentsMargins(0, 0, 0, 0)
        plan_settings_layout.addWidget(self.plan_root_input, 1)
        plan_settings_layout.addWidget(self.plan_root_button)
        right_layout.addWidget(create_group("方案路径设置", plan_settings_layout, (15, 15, 15, 10)))
        destroy_content = create_form_layout([
            (self.dock_full_destroy_cb, "船坞满后自动根据下方黑/白名单设置进行解装"),
            ((self.destroy_ship_work_mode_label, self.destroy_ship_work_mode_combo),
             "选择解装时使用的策略<br>黑名单：解装选中的船<br>白名单：保留选中的船")
        ])
        right_layout.addWidget(create_group("解装设置", destroy_content))

        unified_content_layout = QVBoxLayout()
        unified_content_layout.setContentsMargins(0, 0, 0, 0)
        unified_content_layout.addSpacing(5)

        self.all_ships_button = QPushButton("全部")
        self.all_ships_button.setCheckable(True)
        self.all_ships_button.setProperty("class", "TallButton")
        unified_content_layout.addWidget(self.all_ships_button)
        unified_content_layout.addSpacing(10)

        ship_grid_layout = QGridLayout()
        ship_grid_layout.setSpacing(8)
        self.ship_type_buttons = {}

        for i, ship_name in enumerate(SHIP_DISPLAY_ORDER):
            button = QPushButton(ship_name)
            button.setCheckable(True)
            button.setProperty("class", "TallButton")
            self.ship_type_buttons[ship_name] = button
            row, col = divmod(i, 5)
            ship_grid_layout.addWidget(button, row, col)
        unified_content_layout.addLayout(ship_grid_layout)
        unified_content_layout.addSpacing(10)

        category_grid_layout = QGridLayout()
        category_grid_layout.setSpacing(8)
        self.category_buttons = {}
        for i, category_name in enumerate(CATEGORY_DISPLAY_ORDER):
            button = QPushButton(category_name)
            button.setCheckable(True)
            button.setProperty("class", "TallButton")
            self.category_buttons[category_name] = button
            category_grid_layout.addWidget(button, 0, i)
        unified_content_layout.addLayout(category_grid_layout)

        unified_group_frame = create_group("编辑黑/白名单", unified_content_layout)
        right_layout.addWidget(unified_group_frame)
        right_layout.addStretch(1)

        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(right_panel, 1)

    def _connect_signals(self):
        """将此选项卡内的所有信号连接到其处理方法"""
        self.check_update_cb.toggled.connect(lambda v: self._handle_value_change('check_update_gui', v))
        self.debug_cb.toggled.connect(lambda v: self._handle_value_change('debug', v))
        self.log_level_combo.currentTextChanged.connect(lambda v: self._handle_value_change('log_level', v))
        self.delay_input.editingFinished.connect(self._save_delay)
        self.bathroom_feature_count_spin.valueChanged.connect(lambda v: self._handle_value_change('bathroom_feature_count', v))
        self.bathroom_count_spin.valueChanged.connect(lambda v: self._handle_value_change('bathroom_count', v))
        self.emulator_type_input.textChanged.connect(self._on_emulator_type_changed)
        self.emulator_name_input.editingFinished.connect(self._validate_and_save_emulator_name)
        self.plan_root_button.clicked.connect(self._on_select_plan_root_clicked)
        self.dock_full_destroy_cb.toggled.connect(lambda v: self._handle_value_change('dock_full_destroy', v))
        self.destroy_ship_work_mode_combo.currentIndexChanged.connect(self._on_destroy_mode_changed)
        self.all_ships_button.clicked.connect(self._on_all_ships_clicked)
        for name, button in self.ship_type_buttons.items():
            button.clicked.connect(lambda _, n=name: self._on_individual_ship_clicked(n))
        for name, button in self.category_buttons.items():
            button.clicked.connect(lambda _, n=name: self._on_category_clicked(n))

    def _load_data_to_ui(self):
        """从配置数据加载初始值到UI控件。"""
        self.check_update_cb.setChecked(self.configs_data.get('check_update_gui', False))
        self.debug_cb.setChecked(self.settings_data.get('debug', False))
        self.log_level_combo.setCurrentText(self.settings_data.get('log_level', 'DEBUG'))
        self.delay_input.setText(str(self.settings_data.get('delay', 1.5)))
        self.bathroom_feature_count_spin.setValue(self.settings_data.get('bathroom_feature_count', 3))
        self.bathroom_count_spin.setValue(self.settings_data.get('bathroom_count', 8))
        emulator_type_text = self.settings_data.get('emulator_type', '')
        self.emulator_type_input.setText(emulator_type_text)
        self._on_emulator_type_changed(emulator_type_text)  # 确保初始状态正确
        emulator_name_text = self.settings_data.get('emulator_name', '')
        self.emulator_name_input.setText(emulator_name_text or "") # 确保 None 值不会错误地传递
        self._validate_and_save_emulator_name()  # 确保初始状态正确
        plan_root_path = self.settings_data.get('plan_root', '')
        self.plan_root_input.setText(plan_root_path or "")
        self._validate_and_save_plan_root(plan_root_path, initial_load=True)
        self.dock_full_destroy_cb.setChecked(self.settings_data.get('dock_full_destroy', False))
        work_mode_val = self.settings_data.get('destroy_ship_work_mode', 0)
        mode_index = next(
            (i for i, item in enumerate(self.destroy_mode_items) if item[1] == work_mode_val), 0
        )
        self.destroy_ship_work_mode_combo.setCurrentIndex(mode_index)
        ship_types = self.settings_data.get('destroy_ship_types')
        self.selected_ships = set(ship_types or [])
        self._update_ui_from_selection()

    def _handle_value_change(self, path, value):
        """统一处理配置值的更新和保存，并处理可能发生的错误"""
        try:
            if path == 'check_update_gui':
                update_config_value(self.configs_data, path, value)
                save_config(self.yaml_manager, self.configs_data, self.configs_path)
            else:
                update_config_value(self.settings_data, path, value)
                save_config(self.yaml_manager, self.settings_data, self.settings_path)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

    def _save_delay(self):
        """验证并保存延迟时间"""
        validate_and_save_line_edit(
            line_edit=self.delay_input,
            config_path="delay",
            settings_data=self.settings_data,
            settings_path=self.settings_path,
            yaml_manager=self.yaml_manager,
            default_value=1.5,
            target_type=float,
            clamp_range=(0.1, 60.0)
        )

    def _on_emulator_type_changed(self, text):
        """当模拟器类型文本变化时，规范MuMu大小写"""
        is_mumu = bool(re.fullmatch(r"mumu", text.strip(), re.IGNORECASE))

        if is_mumu:
            value_to_save = "MuMu"
            if self.emulator_type_input.text() != value_to_save:
                self.emulator_type_input.blockSignals(True)
                self.emulator_type_input.setText(value_to_save)
                self.emulator_type_input.blockSignals(False)
        else:
            value_to_save = text

        self._handle_value_change('emulator_type', value_to_save)

    def _validate_and_save_emulator_name(self):
        """验证并保存模拟器地址"""
        pattern = r"^(localhost|(\d{1,3}(\.\d{1,3}){3})):\d{1,5}$"
        validate_and_save_text_input(
            line_edit=self.emulator_name_input,
            config_path="emulator_name",
            settings_data=self.settings_data,
            settings_path=self.settings_path,
            yaml_manager=self.yaml_manager,
            validation_func=lambda text: not text or bool(re.match(pattern, text))
        )

    def _on_select_plan_root_clicked(self):
        """打开文件夹对话框以选择方案根目录"""
        current_path = self.plan_root_input.text()
        directory = QFileDialog.getExistingDirectory(self, "选择方案根文件夹", current_path)
        if directory:
            self.plan_root_input.setText(directory)
            self._validate_and_save_plan_root(directory)
    
    def _validate_and_save_plan_root(self, directory, initial_load=False):
        """验证方案路径的正确性，更新UI，如果有效则保存并发出信号。"""
        is_valid = False
        if directory:
            p = Path(directory)
            if p.is_dir() and p.name == 'plans':
                if (p / 'normal_fight').is_dir() and (p / 'event').is_dir():
                    is_valid = True
        
        if is_valid:
            self.plan_root_input.setProperty("state", "valid")
            if not initial_load:
                self._handle_value_change('plan_root', directory)
                self.plan_root_changed.emit() # 发出信号通知其他Tab
        else:
            # 只有在有输入时才标记为无效，空路径不标记
            state = "invalid" if directory else "neutral"
            self.plan_root_input.setProperty("state", state)
            # 如果是用户主动选择的无效路径，则不写入文件
            # 但允许配置文件中初始加载一个空路径
            if not initial_load and not directory:
                 self._handle_value_change('plan_root', '')


        # 刷新输入框样式
        self.plan_root_input.style().unpolish(self.plan_root_input)
        self.plan_root_input.style().polish(self.plan_root_input)

    def _on_destroy_mode_changed(self, index):
        """处理解装模式下拉菜单的变化"""
        value = self.destroy_mode_items[index][1]
        self._handle_value_change('destroy_ship_work_mode', value)

    def _on_individual_ship_clicked(self, ship_name):
        """响应单个舰种按钮点击"""
        if ship_name in self.selected_ships:
            self.selected_ships.discard(ship_name)
        else:
            self.selected_ships.add(ship_name)
        self._update_ui_and_save()

    def _on_all_ships_clicked(self):
        """响应“全部”按钮点击"""
        if len(self.selected_ships) == len(SHIP_DISPLAY_ORDER):
            self.selected_ships.clear()
        else:
            self.selected_ships = set(SHIP_DISPLAY_ORDER)
        self._update_ui_and_save()

    def _on_category_clicked(self, category_name):
        """响应类别按钮点击"""
        ships_in_category = set(SHIP_TYPE_CATEGORIES_LOGIC.get(category_name, []))
        if self.selected_ships == ships_in_category:
            self.selected_ships.clear()
        else:
            self.selected_ships = ships_in_category
        self._update_ui_and_save()

    def _update_ui_and_save(self):
        """封装“刷新UI”和“保存配置”两个动作"""
        self._update_ui_from_selection()
        if self.selected_ships:
            sorted_ships = sorted(
                list(self.selected_ships),
                key=lambda x: SHIP_DISPLAY_ORDER.index(x) if x in SHIP_DISPLAY_ORDER else 999
            )
            self.settings_data['destroy_ship_types'] = CommentedSeq(sorted_ships)
        else:
            # 确保即使集合为空，配置项也是一个空列表而不是被删除
            self.settings_data['destroy_ship_types'] = []
            
        try:
            save_config(self.yaml_manager, self.settings_data, self.settings_path)
        except Exception as e:
            print(f"配置文件保存失败: {e}")

    def _update_ui_from_selection(self):
        """根据 self.selected_ships 的当前状态，更新所有相关按钮的UI"""
        for name, button in self.ship_type_buttons.items():
            button.blockSignals(True)
            button.setChecked(name in self.selected_ships)
            button.blockSignals(False)
        self.all_ships_button.blockSignals(True)
        is_all_preset_active = self.selected_ships == set(SHIP_DISPLAY_ORDER)
        self.all_ships_button.setChecked(is_all_preset_active)
        self.all_ships_button.blockSignals(False)
        for name, button in self.category_buttons.items():
            button.blockSignals(True)
            category_ships = set(SHIP_TYPE_CATEGORIES_LOGIC.get(name, []))
            is_category_preset_active = (self.selected_ships == category_ships)
            button.setChecked(is_category_preset_active)
            button.blockSignals(False)