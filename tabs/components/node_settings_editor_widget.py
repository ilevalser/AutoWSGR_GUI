from PySide6.QtWidgets import QWidget, QVBoxLayout,QLabel
from PySide6.QtCore import Signal
from tabs.components.node_parameter_widget import NodeParameterWidget
from tabs.components.combo_box import CustomComboBox
from utils.ui_utils import create_group, create_form_layout
from constants import VISIBLE_PARAMS_MAP, PARAM_DEFAULTS, KEY_ORDER_MAP

class NodeSettingsEditorWidget(QWidget):
    """
    管理“节点设置”的控件，包括“默认设置”和“单点设置”。
    它包含一个下拉框来选择编辑对象，以及一个 NodeParameterWidget 来编辑参数。
    """
    settings_changed = Signal()  # 当任何设置(默认或单独)被更改时发出

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_plan_type = None
        self.plan_data = {}  # 存储对整个计划数据的引用
        self.nodes_config_data = {}
        self.plan_defaults = {}
        self.selected_nodes_list = []
        self._setup_ui()
        self._connect_signals()
        self.hide()

    def _setup_ui(self):
        # 创建核心的参数编辑器
        self.param_widget = NodeParameterWidget(visible_params=set())
        
        # 创建下拉框选择器
        self.node_selector_combo = CustomComboBox()
        selector_items_info = [{'widget': (QLabel("编辑对象:"), self.node_selector_combo)}]
        selector_layout = create_form_layout(
            selector_items_info, 
            column_stretches=(1, 1)
        )
        self.selector_widget = QWidget()
        self.selector_widget.setLayout(selector_layout)

        # 创建主布局，将下拉框和参数编辑器组合
        editor_layout = QVBoxLayout()
        editor_layout.setContentsMargins(0, 0, 0, 0)
        editor_layout.addWidget(self.selector_widget) 
        editor_layout.addWidget(self.param_widget)

        # 创建带标题的UI分组
        group = create_group("节点设置", editor_layout, margins=(20, 0, 20 ,0))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(group)

    def _connect_signals(self):
        # 当参数被修改时，调用 _on_params_changed 来保存数据
        self.param_widget.parameters_changed.connect(self._on_params_changed)
        # 当下拉框切换时，调用 _on_node_selected 来加载新数据
        self.node_selector_combo.currentTextChanged.connect(self._on_node_selected)

    def _get_current_visible_params(self) -> set:
        """
        根据当前选择的节点，动态计算哪些参数应该可见。
        """
        # 从 MAP 获取基础可见参数
        base_params = VISIBLE_PARAMS_MAP.get(self.current_plan_type, set()).copy()
        # 如果 detour 根本不在基础设置里直接返回
        if 'detour' not in base_params:
            return base_params
        selected_node = self.node_selector_combo.currentText()
        
        # 默认设置总是显示启用迂回
        if selected_node == "默认设置" or not selected_node:
            # 检查任何已选节点是否可迂回
            can_any_selected_node_detour = False
            for node_name in self.selected_nodes_list:
                if self.nodes_config_data.get(node_name, {}).get('detourable', False):
                    can_any_selected_node_detour = True
                    break # 找到了一个就行
            if not can_any_selected_node_detour:
                base_params.remove('detour') # 默认也删除迂回
        else:
            # 检查特定节点是否可迂回
            node_config = self.nodes_config_data.get(selected_node, {})
            is_detourable = node_config.get('detourable', False)
            if not is_detourable:
                base_params.remove('detour')

        return base_params

    
    def load_plan(self, plan_type: str, plan_data: dict, selected_nodes_list: list, nodes_config_data: dict = None):
        """
        加载新计划的核心方法。
        传入计划类型、计划数据字典和可选的节点配置数据字典。
        根据计划类型调整UI，并加载相应的数据。
        """
        self.current_plan_type = plan_type.lower()
        self.plan_data = plan_data or {}
        self.nodes_config_data = nodes_config_data or {}
        self.selected_nodes_list = selected_nodes_list or []
        
        # 节点默认覆盖参数默认值
        self.plan_defaults = PARAM_DEFAULTS.copy()
        self.plan_defaults.update(self.plan_data.get('node_defaults') or {})

        # 先填充下拉框，这样 _get_current_visible_params 才能获取到默认设置
        self.node_selector_combo.blockSignals(True)
        self.node_selector_combo.clear()
        self.node_selector_combo.addItem("默认设置")

        if self.current_plan_type == 'battle':
            self.selector_widget.hide()
            self.node_selector_combo.setEnabled(False)
        elif self.current_plan_type == 'exercise':
            self.selector_widget.show()
            self.node_selector_combo.addItems(["player", "robot"])
            self.node_selector_combo.setEnabled(True)
        elif self.current_plan_type in ['normal_fight', 'week', 'special_ap_task', 'event']:
            self.selector_widget.show()
            if selected_nodes_list:
                self.node_selector_combo.addItems(sorted(selected_nodes_list))
            self.node_selector_combo.setEnabled(self.node_selector_combo.count() > 1)
        
        self.node_selector_combo.setCurrentIndex(0) # 确保选中默认设置
        self.node_selector_combo.blockSignals(False)
        
        # 获取默认设置对应的可见参数
        visible_params = self._get_current_visible_params()

        # 检查是否有可见参数
        if not visible_params:
            self.hide()
            return

        self._load_current_node_data()
        self.show()

    def update_node_list(self, nodes_list: list):
        """
        更新下拉框中的节点列表以匹配地图选择
        """
        if self.current_plan_type not in ['normal_fight', 'week', 'special_ap_task', 'event']:
            return
        
        self.selected_nodes_list = sorted(nodes_list or [])
        
        # 记住当前选中的是什么
        current_selection = self.node_selector_combo.currentText()
        
        # 重新填充下拉框
        self.node_selector_combo.blockSignals(True)
        self.node_selector_combo.clear()
        self.node_selector_combo.addItem("默认设置")
        
        if self.selected_nodes_list:
            self.node_selector_combo.addItems(self.selected_nodes_list)
        
        # 尝试恢复选择
        new_index = self.node_selector_combo.findText(current_selection)
        
        if new_index != -1: # 原来的选项还在
            self.node_selector_combo.setCurrentIndex(new_index)
        else: # 原来的选项不在了
            self.node_selector_combo.setCurrentIndex(0)
            # 如果选项被迫改变必须手动加载新选项的数据
            if current_selection != "默认设置":
                self._load_current_node_data()
                
        # 只有当有节点可选时才启用下拉框
        self.node_selector_combo.setEnabled(self.node_selector_combo.count() > 1)
        self.node_selector_combo.blockSignals(False)
        # 如果正在查看默认设置则刷新UI
        if self.node_selector_combo.currentText() == "默认设置":
            # 立即获取新的可见参数
            new_visible_params = self._get_current_visible_params()
            # 检查 detour 是否应该被隐藏
            if 'detour' not in new_visible_params:
                node_defaults = self.plan_data.get('node_defaults')
                # 如果应该隐藏并卡在内存里的话删掉它
                if node_defaults and 'detour' in node_defaults:
                    del node_defaults['detour']
                    # 如果删除后 node_defaults 变空也删除
                    if not node_defaults:
                        del self.plan_data['node_defaults']
                    # 保存
                    self.settings_changed.emit()
            # 刷新UI
            self._load_current_node_data()

    def _on_node_selected(self, node_name: str):
        """当用户从下拉框选择一个不同的节点时，加载该节点的数据。"""
        if node_name:
            self._load_current_node_data()

    def _load_current_node_data(self):
        """
        根据下拉框的当前选项，从 self.plan_data 中提取数据
        并加载到 self.param_widget 中。
        """
        data_to_load = {}
        
        # 首先获取当前节点应显示的参数并将可见性设置应用到子控件
        visible_params = self._get_current_visible_params()
        self.param_widget.update_visibility(visible_params)
        
        # 获取数据
        selected_node = self.node_selector_combo.currentText()
        
        if self.current_plan_type == 'battle':
            # 战役使用 plan_defaults
            self.param_widget.set_defaults(self.plan_defaults)
            data_to_load = self.plan_data.get('node_args') or {}
        elif selected_node == "默认设置" or not selected_node:
            # 默认设置使用 PARAM_DEFLOATS
            self.param_widget.set_defaults(PARAM_DEFAULTS)
            data_to_load = self.plan_data.get('node_defaults') or {}
        elif selected_node:
            # 单点必须使用合并后的 plan_defaults
            self.param_widget.set_defaults(self.plan_defaults)
            node_args_dict = self.plan_data.get('node_args') or {}
            data_to_load = (node_args_dict.get(selected_node) or {}).copy()

        # 检查 detour 是否刚被设为不可见
        if 'detour' not in visible_params and selected_node != "默认设置":
            # 如果包含一个无效的 detour
            if 'detour' in data_to_load:
                # 在加载到 param_widget 之前删除
                del data_to_load['detour']

        self.param_widget.load_data(data_to_load)

    def _on_params_changed(self):
        """当子控件参数变化时，获取新数据并将其保存回 self.plan_data。"""
        # 从参数编辑器获取数据
        new_data = self.param_widget.get_data()
        # 检查并处理空列表的情况
        if 'enemy_rules' in new_data and not new_data['enemy_rules']:
            del new_data['enemy_rules']

        # battle 保存到 node_args
        if self.current_plan_type == 'battle':
            if new_data:
                self.plan_data['node_args'] = new_data
            elif 'node_args' in self.plan_data:
                del self.plan_data['node_args']
                    
            self.settings_changed.emit()
            return
        
        # 确定要保存到哪里
        selected_node = self.node_selector_combo.currentText()
        
        if selected_node == "默认设置" or not selected_node:
            # 保存到 node_defaults
            if new_data:
                self.plan_data['node_defaults'] = new_data
            elif 'node_defaults' in self.plan_data:
                # 如果数据为空且键存在则删除
                del self.plan_data['node_defaults']
            # 重新计算 plan_defaults
            self.plan_defaults = PARAM_DEFAULTS.copy()
            self.plan_defaults.update(self.plan_data.get('node_defaults') or {})
                
        elif selected_node:
            # 保存到 node_args
            if 'node_args' not in self.plan_data:
                self.plan_data['node_args'] = {}
            
            if new_data:
                # 保存或更新该节点的数据
                self.plan_data['node_args'][selected_node] = new_data
            elif selected_node in self.plan_data['node_args']:
                # 如果数据为空且该节点键存在则删除
                del self.plan_data['node_args'][selected_node]
                
            # 如果 node_args 变空了也删除
            if not self.plan_data['node_args']:
                del self.plan_data['node_args']
        # 重新组织 plan_data 的键顺序
        self._reorder_plan_data_keys()
        # 发信号通知 PlanEditorTab 已更改
        self.settings_changed.emit()

    def _reorder_plan_data_keys(self):
        """
        根据 KEY_ORDER_MAP 重新组织 plan_data 的键顺序
        """
        if not self.plan_data:
            return
            
        plan_type = self.current_plan_type
        key_order = KEY_ORDER_MAP.get(plan_type)
        
        if not key_order:
            return
            
        # 创建新的有序字典
        ordered_data = {}
        
        # 按照 key_order 的顺序添加键
        for key in key_order:
            if key in self.plan_data:
                ordered_data[key] = self.plan_data[key]
        
        # 添加不在 key_order 中的其他键（如果有）
        for key in self.plan_data:
            if key not in key_order:
                ordered_data[key] = self.plan_data[key]
        
        # 清空原数据并更新为有序数据
        self.plan_data.clear()
        self.plan_data.update(ordered_data)