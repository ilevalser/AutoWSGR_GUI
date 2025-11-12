from ruamel.yaml.comments import CommentedSeq
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QApplication,
    QPushButton, QTableWidgetItem
)
from PySide6.QtCore import Qt, QEvent
from utils.ui_utils import create_ok_cancel_buttons
from tabs.components.combo_box import CustomComboBox
from tabs.components.managed_list_widget import ManagedListWidget
from constants import ACTION_ITEMS, FORMATION_ITEMS

class FormationEditorContentWidget(QWidget):
    def __init__(self, initial_rules, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._load_rules(initial_rules or [])
        self._validate_inputs()

    def _setup_ui(self):
        root_layout = QHBoxLayout(self)
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        root_layout.addWidget(left_panel, 14)
        root_layout.addWidget(right_panel, 20)

    def _create_left_panel(self):
        """左侧包含阵型选择、动作选择和添加按钮"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        layout.addWidget(QLabel("如果敌方阵型是:"))
        self.formation_combo = CustomComboBox()
        for internal_value, display_text in FORMATION_ITEMS.items():
            self.formation_combo.addItem(display_text, userData=internal_value)
        layout.addWidget(self.formation_combo)
        
        layout.addWidget(QLabel("则:"))
        self.action_combo = CustomComboBox()
        for internal_value_str, display_text in ACTION_ITEMS.items():
            data_to_store = None
            try:
                data_to_store = int(internal_value_str)
            except ValueError:
                data_to_store = internal_value_str
            self.action_combo.addItem(display_text, userData=data_to_store)
            
        layout.addWidget(self.action_combo)
        
        explain = QLabel("根据敌方阵型指定最优先行为<br>例：敌方为单纵阵时撤退")
        explain.setObjectName("DescriptionLabel")
        layout.addWidget(explain)
        
        self.add_rule_button = QPushButton("添加至右侧")
        self.add_rule_button.setProperty("class", "TallButton")
        layout.addWidget(self.add_rule_button)
        
        layout.addStretch()
        return panel

    def _create_right_panel(self):
        """右侧包含规则表格和控制按钮"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("已添加的规则 (从上到下执行):"))
        self.list_manager = ManagedListWidget(["规则: [阵型, 操作]"])
        layout.addWidget(self.list_manager, 1)
        return panel

    def _connect_signals(self):
        """连接信号"""
        # 左侧面板的信号
        self.formation_combo.currentTextChanged.connect(self._validate_inputs)
        self.action_combo.currentTextChanged.connect(self._validate_inputs)
        self.add_rule_button.clicked.connect(self._on_add_rule)

    def _load_rules(self, rules: list):
        """加载初始规则到表格中"""
        items_list = []
        for rule_list in rules:
            if isinstance(rule_list, list) and len(rule_list) == 2:
                formation_internal, action_value = rule_list
                # 右侧表格显示内部值
                rule_display_text = f"[{formation_internal}, {action_value}]"
                # 创建 QTableWidgetItem
                item = QTableWidgetItem(rule_display_text)
                item.setData(Qt.UserRole, [formation_internal, action_value])
                # 添加到行列表
                items_list.append([item]) # 作为一个新行
        # 一次性设置所有数据
        self.list_manager.set_table_data(items_list)

    def _validate_inputs(self):
        """验证输入是否有效"""
        formation_text = self.formation_combo.currentText()
        action_text = self.action_combo.currentText()
        
        is_valid = bool(formation_text and action_text)
        self.add_rule_button.setEnabled(is_valid)
        
        return is_valid

    def _on_add_rule(self):
        """处理添加规则按钮点击事件"""
        if not self._validate_inputs(): return
        formation_internal = self.formation_combo.currentData()
        action_value = self.action_combo.currentData()
        rule_display_text = f"[{formation_internal}, {action_value}]"
        self._add_rule_to_table(rule_display_text, formation_internal, action_value)

    def _add_rule_to_table(self, rule_display_text: str, formation_internal: str, action_value: str):
        """在表格中添加规则"""
        item = QTableWidgetItem(rule_display_text)
        item.setData(Qt.UserRole, [formation_internal, action_value])
        # 使用 list_manager 的 API 添加单行
        self.list_manager.add_table_row([item])

    def get_rules(self) -> list:
        """从表格收集所有规则并返回"""
        rules = []
        for row in range(self.list_manager.get_row_count()):
            item = self.list_manager.get_item(row, 0)
            if item:
                rule_data = item.data(Qt.UserRole)
                if isinstance(rule_data, list) and len(rule_data) == 2:
                    flow_rule = CommentedSeq(rule_data)
                    flow_rule.fa.set_flow_style()
                    rules.append(flow_rule)
        return rules

    def process_app_event(self, watched, event: QEvent):
        """将事件传递给 list_manager 以重置其删除按钮状态"""
        if hasattr(self, 'list_manager'):
            self.list_manager.process_global_event(event)
        return False

class EnemyFormationRulesDialog(QDialog):
    """敌方阵型规则对话框"""
    def __init__(self, initial_rules: list, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName('Dialog')
        self.setWindowTitle("敌方阵型规则")
        self.setMinimumSize(600, 400)
        self.content_widget = FormationEditorContentWidget(initial_rules, self)
        self._setup_shell_ui()

    def get_rules(self):
        return self.content_widget.get_rules()

    def _setup_shell_ui(self):
        shell_layout = QVBoxLayout(self)
        shell_layout.addWidget(self.content_widget)
        confirm_button, cancel_button = create_ok_cancel_buttons()
        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(cancel_button)
        button_layout.addWidget(confirm_button)
        shell_layout.addLayout(button_layout)

    def exec(self):
        QApplication.instance().installEventFilter(self)
        result = super().exec()
        QApplication.instance().removeEventFilter(self)
        return result

    def eventFilter(self, watched, event: QEvent):
        """将事件传递给内容控件"""
        if self.isActiveWindow():
            return self.content_widget.process_app_event(watched, event)
        return False