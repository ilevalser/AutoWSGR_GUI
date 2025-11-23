from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QDialog
from PySide6.QtCore import Signal
from ruamel.yaml.comments import CommentedSeq
from tabs.components.check_box import CustomCheckBox
from tabs.components.combo_box import CustomComboBox
from tabs.components.enemy_rules_dialog import EnemyRulesDialog
from tabs.components.enemy_formation_rules_dialog import EnemyFormationRulesDialog
from utils.ui_utils import create_form_layout
from constants import PARAM_DEFAULTS, SPOT_FAILS_FORMATION_ITEMS, PROCEED_ITEMS

class NodeParameterWidget(QWidget):
    """
    一个通用的节点参数设置控件，包含所有可能的参数项。
    可通过配置决定显示哪些参数。
    """
    parameters_changed = Signal()

    def __init__(self, visible_params: set, parent=None):
        super().__init__(parent)
        self._ui_rows = {}
        self._uncontrolled_data = {} # 防止两个规则被过滤
        self.current_defaults = PARAM_DEFAULTS.copy()
        self._setup_ui()
        self._connect_signals()
        self.update_visibility(visible_params)

    def _setup_ui(self):
        """创建所有UI控件和布局"""
        # --- 创建所有参数的UI控件 ---
        self.long_missile_support_check = CustomCheckBox("启用远程支援")
        self.detour_check = CustomCheckBox("启用迂回")
        self.enemy_rules_button = QPushButton("点击配置") # 占位符按钮
        self.enemy_rules_button.setProperty("class", "TallButton")
        self.enemy_formation_rules_button = QPushButton("点击配置") # 占位符按钮
        self.enemy_formation_rules_button.setProperty("class", "TallButton")
        self.sl_spot_fails_check = CustomCheckBox("索敌失败时SL")
        self.sl_detour_fails_check = CustomCheckBox("迂回失败时SL")
        self.sl_enter_fight_check = CustomCheckBox("进入战斗后SL")
        self.formation_combo = CustomComboBox()
        self.formation_combo.addItems(SPOT_FAILS_FORMATION_ITEMS[1:])
        self.formation_spot_fails_combo = CustomComboBox()
        self.formation_spot_fails_combo.addItems(SPOT_FAILS_FORMATION_ITEMS)
        self.night_check = CustomCheckBox("夜战")
        self.proceed_check = CustomCheckBox("继续前进")
        self.proceed_stop_combo, self.proceed_stop_buttons_container = self._create_proceed_stop_parts()

        items_info = [
            {'widget': self.long_missile_support_check, 'key': 'long_missile_support', 'description': "是否开启远程导弹支援<br>⚠<b><i>不携带导巡、导潜时启用会导致报错！<b><i>"},
            {'widget': self.detour_check, 'key': 'detour', 'description': "是否尝试迂回"},
            {'widget': (QLabel("敌方编队规则:"), self.enemy_rules_button), 'key': 'enemy_rules', 'description': "根据敌方编队情况指定最优先行为"},
            {'widget': (QLabel("敌方阵型规则:"), self.enemy_formation_rules_button), 'key': 'enemy_formation_rules', 'description': "根据敌方阵型情况指定最优先行为（覆盖敌方编队规则）"},
            {'widget': self.sl_spot_fails_check, 'key': 'SL_when_spot_enemy_fails', 'description': "在索敌阶段如果索敌失败则SL"},
            {'widget': self.sl_detour_fails_check, 'key': 'SL_when_detour_fails', 'description': "在迂回阶段如果迂回失败则SL"},
            {'widget': self.sl_enter_fight_check, 'key': 'SL_when_enter_fight', 'description': "在进入战斗时立即SL，用于快速刷战术经验"},
            {'widget': (QLabel("阵型选择:"), self.formation_combo), 'key': 'formation', 'description': "选择战斗的阵型"},
            {'widget': (QLabel("索敌失败阵型:"), self.formation_spot_fails_combo), 'key': 'formation_when_spot_enemy_fails', 'description': "索敌失败时使用的阵型"},
            {'widget': self.night_check, 'key': 'night', 'description': "是否进入夜战"},
            {'widget': self.proceed_check, 'key': 'proceed', 'description': "是否继续战斗"},
            {'widget': (QLabel("中止前进策略:"), self.proceed_stop_combo), 'extra_widget': self.proceed_stop_buttons_container, 'key': 'proceed_stop', 'description': "根据我方血量状态决定是否中止前进，逻辑同修理模式"},
        ]

        self.main_layout, self._ui_rows = create_form_layout(
            items_info, 
            column_stretches=(1, 1),
            track_widgets=True
        )
        
        self.setLayout(self.main_layout)
    
    def _create_proceed_stop_parts(self):
        """创建“中止前进策略”所需的组合框和一组按钮"""
        combo = CustomComboBox()
        combo.addItems(PROCEED_ITEMS)
        
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
        
        buttons_container.setProperty("buttons", buttons)
        return combo, buttons_container

    def _connect_signals(self):
        """将所有可交互控件的“值改变”信号连接到 parameters_changed 信号上。"""

        self.long_missile_support_check.toggled.connect(self.parameters_changed)
        self.detour_check.toggled.connect(self.parameters_changed)
        self.sl_spot_fails_check.toggled.connect(self.parameters_changed)
        self.sl_detour_fails_check.toggled.connect(self.parameters_changed)
        self.sl_enter_fight_check.toggled.connect(self.parameters_changed)
        self.night_check.toggled.connect(self.parameters_changed)
        self.proceed_check.toggled.connect(self.parameters_changed)

        self.formation_combo.currentIndexChanged.connect(self.parameters_changed)
        self.formation_spot_fails_combo.currentIndexChanged.connect(self.parameters_changed)

        self.proceed_stop_combo.currentIndexChanged.connect(self._on_proceed_stop_combo_changed)
        for btn in self.proceed_stop_buttons_container.property("buttons"):
            btn.toggled.connect(self.parameters_changed)

        self.enemy_rules_button.clicked.connect(self._on_edit_enemy_rules)
        self.enemy_formation_rules_button.clicked.connect(self._on_edit_enemy_formation_rules)

    def set_defaults(self, defaults_dict: dict):
        """公共接口：允许父控件设置此控件当前应使用的默认值"""
        self.current_defaults = defaults_dict.copy()

    def _apply_visibility(self):
        """根据初始化时传入的 visible_params，显示或隐藏对应的参数行"""
        for key, row_widgets in self._ui_rows.items():
            is_visible = key in self.visible_params
            for widget in row_widgets:
                if widget:
                    widget.setVisible(is_visible)
    
    def update_visibility(self, visible_params: set):
        """根据传入的参数名集合，更新UI上可见的参数项。"""
        self.visible_params = visible_params
        self._apply_visibility()

    def load_data(self, data: dict):
        """根据传入的数据字典，设置UI控件的状态"""
        self.blockSignals(True)
        
        data = data or {}
        # 暂存不能控制的参数
        self._uncontrolled_data = {}
        for key, value in data.items():
            if key not in PARAM_DEFAULTS:
                self._uncontrolled_data[key] = value

        self.long_missile_support_check.setChecked(data.get('long_missile_support', self.current_defaults['long_missile_support']))
        self.detour_check.setChecked(data.get('detour', self.current_defaults['detour']))
        self.sl_spot_fails_check.setChecked(data.get('SL_when_spot_enemy_fails', self.current_defaults['SL_when_spot_enemy_fails']))
        self.sl_detour_fails_check.setChecked(data.get('SL_when_detour_fails', self.current_defaults['SL_when_detour_fails']))
        self.sl_enter_fight_check.setChecked(data.get('SL_when_enter_fight', self.current_defaults['SL_when_enter_fight']))
        formation_val = data.get('formation', self.current_defaults['formation'])
        self.formation_combo.setCurrentIndex(formation_val - 1)
        spot_fails_val = data.get('formation_when_spot_enemy_fails', self.current_defaults['formation_when_spot_enemy_fails'])
        self.formation_spot_fails_combo.setCurrentIndex(spot_fails_val)
        self.night_check.setChecked(data.get('night', self.current_defaults['night']))
        self.proceed_check.setChecked(data.get('proceed', self.current_defaults['proceed']))
        
        self._load_proceed_stop_data(data.get('proceed_stop', self.current_defaults['proceed_stop']))

        self.blockSignals(False)

    def get_data(self) -> dict:
        """
        从UI控件读取数据，根据精细化逻辑返回待保存的字典。
        - 如果一个键在加载时就存在，则总是保存它。
        - 如果一个键是加载时缺失的，只有当它的值被用户修改为非默认值时才开始保存它。
        - 值为None的键永不保存。
        """
        data_to_save = {}
        
        # 先获取所有UI控件的当前值
        current_ui_values = {
            'long_missile_support': self.long_missile_support_check.isChecked(),
            'detour': self.detour_check.isChecked(),
            'SL_when_spot_enemy_fails': self.sl_spot_fails_check.isChecked(),
            'SL_when_detour_fails': self.sl_detour_fails_check.isChecked(),
            'SL_when_enter_fight': self.sl_enter_fight_check.isChecked(),
            'formation': self.formation_combo.currentIndex() + 1,
            'formation_when_spot_enemy_fails': self.formation_spot_fails_combo.currentIndex(),
            'night': self.night_check.isChecked(),
            'proceed': self.proceed_check.isChecked(),
        }
        # 单独处理 proceed_stop
        combo_index = self.proceed_stop_combo.currentIndex()
        if combo_index == 0:
            buttons = self.proceed_stop_buttons_container.property("buttons")
            value = CommentedSeq([2 if btn.isChecked() else 1 for btn in buttons])
            value.fa.set_flow_style()
            current_ui_values['proceed_stop'] = value
        else:
            current_ui_values['proceed_stop'] = combo_index

        # 根据新逻辑决定哪些值需要被保存
        for key, value in current_ui_values.items():
            if key not in self.visible_params or value is None:
                continue
            
            is_modified_from_default = value != self.current_defaults.get(key)

            if is_modified_from_default:
                data_to_save[key] = value

        # 将两个规则合并回去
        for key, value in self._uncontrolled_data.items():
            if key in self.visible_params:
                data_to_save[key] = value
 
        return data_to_save

    def _load_proceed_stop_data(self, value):
        """加载数据到“中止前进策略”的UI控件"""
        combo = self.proceed_stop_combo
        buttons_container = self.proceed_stop_buttons_container
        buttons = buttons_container.property("buttons")
        
        combo.blockSignals(True)
        for btn in buttons: btn.blockSignals(True)
        
        if isinstance(value, list) and len(value) == 6:
            combo.setCurrentIndex(0) # 逐位自定义
            buttons_container.setEnabled(True)
            for i, btn in enumerate(buttons):
                btn.setChecked(value[i] == 2) # 2代表大破
        else:
            index = int(value) if str(value).isdigit() and int(value) in [1, 2] else 2
            combo.setCurrentIndex(index)
            buttons_container.setEnabled(False)
            
        combo.blockSignals(False)
        for btn in buttons: btn.blockSignals(False)
    
    def _on_edit_enemy_rules(self):
        """打开敌方编队规则编辑器"""
        # 从未控制数据中获取当前规则并执行对话框
        current_rules = self._uncontrolled_data.get('enemy_rules', [])
        dialog = EnemyRulesDialog(current_rules, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_rules = dialog.get_rules()
            # 检查规则是否真的改变了
            if new_rules == current_rules:
                return
            # 将新规则存回未控制数据
            self._uncontrolled_data['enemy_rules'] = new_rules
            # 发出信号，通知父级数据已更改
            self.parameters_changed.emit()
    
    def _on_edit_enemy_formation_rules(self):
        """打开敌方阵型规则编辑器"""
        current_rules = self._uncontrolled_data.get('enemy_formation_rules', [])
        dialog = EnemyFormationRulesDialog(current_rules, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_rules = dialog.get_rules()
            if new_rules == current_rules: return
            self._uncontrolled_data['enemy_formation_rules'] = new_rules
            self.parameters_changed.emit()
    
    def _on_proceed_stop_combo_changed(self, index):
        """当“中止前进策略”下拉框变化时，控制按钮组的启用状态"""
        is_custom = (index == 0)
        self.proceed_stop_buttons_container.setEnabled(is_custom)
        self.parameters_changed.emit()