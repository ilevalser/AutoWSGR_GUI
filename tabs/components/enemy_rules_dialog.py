from ruamel.yaml.comments import CommentedSeq
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QApplication,
    QPushButton, QTableWidgetItem, QButtonGroup, QGridLayout
)
from PySide6.QtCore import Qt, Signal, QEvent, QSize
from utils.ui_utils import create_ok_cancel_buttons
from tabs.components.list_box import BaseSourceList, BaseTargetList
from tabs.components.combo_box import CustomComboBox
from tabs.components.managed_list_widget import ManagedListWidget
from constants import ENEMY_SHIP_TYPES, SYMBOLS, QUANTITIES, LOGIC_OPS, ACTION_ITEMS, PARENS

SYMBOLS_TEXT_TO_VALUE = {v: k for k, v in SYMBOLS.items()}
LOGIC_OPS_TEXT_TO_VALUE = {v: k for k, v in LOGIC_OPS.items()}
ENEMY_SHIP_TYPES_TEXT_TO_VALUE = {v: k for k, v in ENEMY_SHIP_TYPES.items()}

LOGIC_OPS_VALUES = set(LOGIC_OPS.keys())
SYMBOLS_VALUES = set(SYMBOLS.keys())
ENEMY_SHIP_TYPES_VALUES = set(ENEMY_SHIP_TYPES.keys())

sorted_quantities = sorted(list(QUANTITIES), key=lambda x: int(x))
sorted_ship_types = sorted(
    list(ENEMY_SHIP_TYPES.values()),
    key=lambda x: ENEMY_SHIP_TYPES_TEXT_TO_VALUE[x]
)

BLOCK_TYPES = {
    "舰船类型": sorted_ship_types,
    "比较": list(SYMBOLS.values()),
    "数量": sorted_quantities,
    "逻辑": list(LOGIC_OPS.values()) + list(PARENS)
}

ALL_BLOCKS = (
    sorted_ship_types + 
    list(SYMBOLS.values()) + 
    sorted_quantities + 
    list(LOGIC_OPS.values()) + 
    list(PARENS)
)

class RulesSourceList(BaseSourceList):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("SourceShipsList")

class RulesTargetList(BaseTargetList):
    syntax_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent, 
                        max_items=0,
                        allow_internal_move=True,
                        allow_same_type_exchange=False,
                        unique_in_same_type=False,
                        enable_smart_swap=False)
        self.setObjectName("FleetList")
        self.setMaximumHeight(80)
        self.setWrapping(True)
        self.setSpacing(3)
        self.contentChanged.connect(self.syntax_changed)

    def _update_item_sizes(self):
        fm = self.fontMetrics()
        horizontal_padding = 22
        fixed_height = 22
        for i in range(self.count()):
            item = self.item(i)
            text_width = fm.boundingRect(item.text()).width()
            item.setSizeHint(QSize(text_width + horizontal_padding, fixed_height))
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

class EditorContentWidget(QWidget):
    def __init__(self, initial_rules, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._connect_signals()
        self._load_rules(initial_rules or [])
        self._update_source_block_list()
        self._validate_staging_list()

    def _setup_ui(self):
        root_layout = QHBoxLayout(self)
        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()
        root_layout.addWidget(left_panel, 18)
        root_layout.addWidget(right_panel, 16)

    def _create_left_panel(self):
        """左侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        categories = ["全部"] + list(BLOCK_TYPES.keys())
        self.block_type_group = QButtonGroup(self)
        buttons_layout = self._create_button_grid(categories, self.block_type_group, "全部")
        layout.addLayout(buttons_layout)
        
        self.source_block_list = RulesSourceList()
        layout.addWidget(self.source_block_list, 1)
        layout.addWidget(QLabel("如果敌方编队中的："))
        explain = QLabel("单元内规则：舰种(+舰种) 比较 数量<br>单元间规则：允许并且、或者、()进行逻辑运算<br>例：“驱逐+轻巡≤1 并且 (( 轻母=1 并且 航母=0 ) 或者 轻母=0 )”")
        explain.setObjectName("DescriptionLabel")
        layout.addWidget(explain)
        
        self.staging_list = RulesTargetList()
        layout.addWidget(self.staging_list)
        layout.addWidget(QLabel("则："))

        self.action_combo = CustomComboBox()
        for internal_value_str, display_text in ACTION_ITEMS.items():
            data_to_store = None
            try:
                data_to_store = int(internal_value_str)
            except ValueError:
                data_to_store = internal_value_str
            self.action_combo.addItem(display_text, userData=data_to_store)
            
        layout.addWidget(self.action_combo)

        self.add_rule_button = QPushButton("添加至右侧")
        self.clear_stage_button = QPushButton("清空条件")
        self.clear_stage_button.setProperty("class", "TallButton")
        self.add_rule_button.setProperty("class", "TallButton")
        stage_button_layout = QHBoxLayout()
        stage_button_layout.addWidget(self.clear_stage_button)
        stage_button_layout.addWidget(self.add_rule_button)
        layout.addLayout(stage_button_layout)
        return panel

    def _create_button_grid(self, items, button_group, default_checked_text):
        """辅助函数：创建按钮网格"""
        layout = QGridLayout()
        layout.setSpacing(5); max_cols = 5
        for i, text in enumerate(items):
            button = QPushButton(text); button.setCheckable(True)
            button.setProperty("class", "ShortButton")
            if text == default_checked_text: button.setChecked(True)
            button_group.addButton(button); row, col = i // max_cols, i % max_cols
            layout.addWidget(button, row, col)
        return layout

    def _create_right_panel(self):
        """右侧面板"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("已添加的规则 (从上到下执行):"))
        self.list_manager = ManagedListWidget(["规则: [条件, 操作]"])
        layout.addWidget(self.list_manager, 1)
        
        return panel

    def _connect_signals(self):
        """连接信号"""
        self.block_type_group.buttonClicked.connect(self._update_source_block_list)
        self.staging_list.syntax_changed.connect(self._validate_staging_list)
        self.add_rule_button.clicked.connect(self._on_add_rule)
        self.clear_stage_button.clicked.connect(self.staging_list.clear)

    def _load_rules(self, rules: list):
        """加载初始规则到表格中"""
        items_list = []
        for rule_list in rules:
            if isinstance(rule_list, list) and len(rule_list) == 2:
                condition, action = rule_list
                rule_display_text = f"[{condition}, {str(action)}]"
                item = QTableWidgetItem(rule_display_text)
                item.setData(Qt.UserRole, [condition, str(action)])
                items_list.append([item]) # 作为一个新行
        # 一次性设置所有数据
        self.list_manager.set_table_data(items_list)

    def _update_source_block_list(self):
        """根据选中的块类型更新源块列表"""
        self.source_block_list.clear()
        checked_button = self.block_type_group.checkedButton()
        if not checked_button: return
        block_type = checked_button.text()
        
        items = []
        if block_type == "全部":
            items = ALL_BLOCKS
        else:
            items = BLOCK_TYPES.get(block_type, [])
        self.source_block_list.addItems(items)

    def _get_block_type(self, block_text):
        """根据显示文本获取块类型"""
        internal_value = block_text
        if block_text in ENEMY_SHIP_TYPES_TEXT_TO_VALUE:
            internal_value = ENEMY_SHIP_TYPES_TEXT_TO_VALUE[block_text]
        elif block_text in SYMBOLS_TEXT_TO_VALUE:
            internal_value = SYMBOLS_TEXT_TO_VALUE[block_text]
        elif block_text in LOGIC_OPS_TEXT_TO_VALUE:
            internal_value = LOGIC_OPS_TEXT_TO_VALUE[block_text]

        if internal_value in SYMBOLS_VALUES: return "SYMBOL"
        if internal_value in LOGIC_OPS_VALUES: return "LOGIC"
        if internal_value == "(": return "LPAREN"
        if internal_value == ")": return "RPAREN"
        if internal_value in QUANTITIES: return "QUANTITY"
        if internal_value in ENEMY_SHIP_TYPES_VALUES: return "TYPE"
        return "UNKNOWN"

    def _get_block_type_from_value(self, value):
        """根据内部值获取块类型"""
        if value in SYMBOLS_VALUES: return "SYMBOL"
        if value in LOGIC_OPS_VALUES: return "LOGIC"
        if value == "(": return "LPAREN"
        if value == ")": return "RPAREN"
        if value in QUANTITIES: return "QUANTITY"
        if value in ENEMY_SHIP_TYPES_VALUES: return "TYPE"
        return "UNKNOWN"
    
    def _is_valid_atomic(self, sub_tokens: list) -> bool:
        """检查一个原子条件 (e.g., "BB + CL > 1") 是否有效。使用内部值进行验证。"""     
        if not sub_tokens: return False
        symbol_index = -1
        symbol_count = 0
        for i, token in enumerate(sub_tokens):
            if token in SYMBOLS_VALUES:  # 使用内部值集合
                if symbol_index == -1:
                    symbol_index = i
                symbol_count += 1
        # 必须包含一个且只有一个比较符号
        if symbol_count != 1: return False
            
        lhs_tokens = sub_tokens[:symbol_index]
        rhs_tokens = sub_tokens[symbol_index + 1:]
        # 必须是 1 个 QUANTITY
        if not (len(rhs_tokens) == 1 and rhs_tokens[0] in QUANTITIES): return False
        # 必须是 (TYPE) 或 (TYPE + TYPE ...)
        if not lhs_tokens: return False
        # 检查左侧第一个元素是否为类型
        if lhs_tokens[0] not in ENEMY_SHIP_TYPES_VALUES: return False
        # 检查左侧最后一个元素是否为逻辑运算符
        if lhs_tokens[-1] in LOGIC_OPS_VALUES: return False
        # 检查 LHS 的交替模式 (TYPE, LOGIC, TYPE, LOGIC...)
        for i in range(1, len(lhs_tokens)):
            token = lhs_tokens[i]
            last_token = lhs_tokens[i-1]
            # 如果上一个元素是类型，当前元素必须是逻辑运算符
            if last_token in ENEMY_SHIP_TYPES_VALUES:
                if token not in LOGIC_OPS_VALUES:return False
            # 如果上一个元素是逻辑运算符，当前元素必须是类型
            elif last_token in LOGIC_OPS_VALUES:
                if token not in ENEMY_SHIP_TYPES_VALUES:return False
            else: return False
        return True
    
    def _compile_to_logical_tokens(self, items: list) -> (list | None):
        """
        将原始积木列表编译为逻辑标记列表
        """
        # 将显示文本转换为内部值
        internal_items = []
        for item in items:
            if item in ENEMY_SHIP_TYPES_TEXT_TO_VALUE:
                internal_items.append(ENEMY_SHIP_TYPES_TEXT_TO_VALUE[item])
            elif item in SYMBOLS_TEXT_TO_VALUE:
                internal_items.append(SYMBOLS_TEXT_TO_VALUE[item])
            elif item in LOGIC_OPS_TEXT_TO_VALUE:
                internal_items.append(LOGIC_OPS_TEXT_TO_VALUE[item])
            else:
                internal_items.append(item)
        
        # 使用内部值进行编译
        delimiters = (LOGIC_OPS_VALUES - {'+'}) | PARENS
        tokens = []
        current_atom = []
        
        for item in internal_items:
            if item in delimiters:
                # 遇到了分隔符，先处理之前积累的原子块
                if current_atom:
                    if not self._is_valid_atomic(current_atom): return None
                    tokens.append("ATOMIC")
                    current_atom = []
                # 添加分隔符本身
                tokens.append(item)
            else:
                # 非分隔符，说明是原子块的一部分
                current_atom.append(item)
        # 处理循环结束后的最后一个原子块
        if current_atom:
            if not self._is_valid_atomic(current_atom): return None
            tokens.append("ATOMIC")
        return tokens

    def _validate_logical_syntax(self, tokens: list) -> bool:
        """
        检查编译后的标记列表 ['(', 'ATOMIC', 'and', 'ATOMIC', ')']是否符合逻辑语法规则。
        """
        if not tokens: return False # 列表为空
        # 检查括号平衡
        paren_balance = 0
        for token in tokens:
            if token == "(": paren_balance += 1
            elif token == ")": paren_balance -= 1
            if paren_balance < 0: return False # e.g., ") ("
        if paren_balance != 0: return False # e.g., "( ( ..."
        # 检查标记的顺序是否合法
        logic_ops = LOGIC_OPS_VALUES  - {'+'} # 'and', 'or'
        last_token_type = "START"
        for token in tokens:
            current_token_type = "UNKNOWN"
            if token == "ATOMIC": current_token_type = "ATOMIC"
            elif token in logic_ops: current_token_type = "LOGIC"
            elif token == "(": current_token_type = "LPAREN"
            elif token == ")": current_token_type = "RPAREN"
            if last_token_type == "START":
                # 规则必须以 原子 或 ( 开头
                if current_token_type not in {"ATOMIC", "LPAREN"}: return False
            elif last_token_type == "ATOMIC":
                # 原子 后面必须跟 逻辑(and/or) 或 )
                if current_token_type not in {"LOGIC", "RPAREN"}: return False
            elif last_token_type == "LOGIC":
                # 逻辑(and/or) 后面必须跟 原子 或 (
                if current_token_type not in {"ATOMIC", "LPAREN"}: return False
            elif last_token_type == "LPAREN":
                # ( 后面必须跟 原子 或 (
                if current_token_type not in {"ATOMIC", "LPAREN"}: return False # 杜绝 "( )" 或 "( and ...)"
            elif last_token_type == "RPAREN":
                # ) 后面必须跟 逻辑(and/or) 或 )
                if current_token_type not in {"LOGIC", "RPAREN"}: return False
            last_token_type = current_token_type
        # 规则必须以 原子 或 ) 结尾
        if last_token_type not in {"ATOMIC", "RPAREN"}: return False
        return True

    def _validate_staging_list(self) -> bool:
        """
        1. 将积木列表转为逻辑标记，并验证所有原子规则。
        2. 验证逻辑标记的顺序。
        """
        items = [self.staging_list.item(i).text() for i in range(self.staging_list.count())]
        is_valid = False
        if items: # 仅在列表非空时验证
            # 验证所有原子
            logical_tokens = self._compile_to_logical_tokens(items)
            if logical_tokens is not None:
                # 验证逻辑结构
                is_valid = self._validate_logical_syntax(logical_tokens)
        # 设置 QSS
        if is_valid:
            self.staging_list.setProperty("class", "")
        else:
            self.staging_list.setProperty("class", "invalid")
        self.staging_list.style().unpolish(self.staging_list)
        self.staging_list.style().polish(self.staging_list)
        self.add_rule_button.setEnabled(is_valid)
        return is_valid

    def _on_add_rule(self):
        """处理添加至右侧"""
        
        if not self._validate_staging_list(): return
        
        items = [self.staging_list.item(i).text() for i in range(self.staging_list.count())]
        
        condition_items = []
        for item in items:
            if item in ENEMY_SHIP_TYPES_TEXT_TO_VALUE:
                condition_items.append(ENEMY_SHIP_TYPES_TEXT_TO_VALUE[item])
            elif item in SYMBOLS_TEXT_TO_VALUE:
                condition_items.append(SYMBOLS_TEXT_TO_VALUE[item])
            elif item in LOGIC_OPS_TEXT_TO_VALUE:
                condition_items.append(LOGIC_OPS_TEXT_TO_VALUE[item])
            else:
                condition_items.append(item)
        
        condition_str = " ".join(condition_items)
        
        # 直接从 userData 获取内部值
        action_value = self.action_combo.currentData()
        if not action_value: return
        self._add_rule_to_table(condition_str, action_value)
        self.staging_list.clear()

    def _add_rule_to_table(self, condition: str, action_value: str):
        """辅助函数：在表格末尾添加 1 列"""
        rule_text = f"[{condition}, {action_value}]"
        item = QTableWidgetItem(rule_text)
        item.setData(Qt.UserRole, [condition, action_value])
        self.list_manager.add_table_row([item])

    def get_rules(self) -> list:
        """从右侧表格收集所有规则并返回"""
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
        """
        处理全局鼠标点击事件。
        将事件传递给 list_manager 以重置其删除按钮状态。
        """
        if hasattr(self, 'list_manager'):
            self.list_manager.process_global_event(event)
        return False

class EnemyRulesDialog(QDialog):
    """敌方规则对话框的壳"""
    def __init__(self, initial_rules: list, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName('Dialog')
        self.setWindowTitle("敌方编队规则")
        self.setMinimumSize(800, 600)
        self.content_widget = EditorContentWidget(initial_rules, self)
        self._setup_shell_ui()

    def get_rules(self):
        return self.content_widget.get_rules()

    def _setup_shell_ui(self):
        shell_layout = QVBoxLayout(self)
        shell_layout.addWidget(self.content_widget)
        confirm_button, cancel_button = create_ok_cancel_buttons()
        confirm_button.clicked.connect(self.accept)
        cancel_button.clicked.connect(self.reject)
        button_layout = QHBoxLayout(); button_layout.addStretch()
        button_layout.addWidget(cancel_button); button_layout.addWidget(confirm_button)
        shell_layout.addLayout(button_layout)

    def exec(self):
        QApplication.instance().installEventFilter(self)
        result = super().exec()
        QApplication.instance().removeEventFilter(self)
        return result

    def eventFilter(self, watched, event: QEvent):
        if self.isActiveWindow():
            return self.content_widget.process_app_event(watched, event)
        return False