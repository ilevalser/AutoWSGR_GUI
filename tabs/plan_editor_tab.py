import os
import yaml
from ruamel.yaml.comments import CommentedSeq
import re
from pathlib import Path
import io
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTextEdit, QSizePolicy, QScrollArea, QApplication
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, Signal, QRect, QEvent
from tabs.components.check_box import CustomCheckBox 
from tabs.components.combo_box import CustomComboBox
from tabs.components.plan_settings_widget import PlanSettingsWidget
from tabs.components.node_settings_editor_widget import NodeSettingsEditorWidget
from tabs.components.new_plan_dialog import NewPlanDialog
from constants import SETTINGS_FILE, MAP_PICS_DIR, NORMAL_MAP_CONFIGS_FILE, EVENT_MAP_CONFIGS_FILE, KEY_ORDER_MAP
from utils.config_utils import save_config, update_config_value
from utils.ui_utils import create_ok_cancel_buttons, ConfirmButtonManager

class MapDisplayWidget(QWidget):
    """
    一个显示地图图片并在其上叠加交互式节点（复选框）的控件。
    节点根据相对坐标定位，并且地图是可缩放的。
    """
    selection_changed = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_pixmap = QPixmap()
        self._node_data = {}
        self._node_checkboxes = {}
        self._last_emitted_selection = set()

        self.map_label = QLabel(self)
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setObjectName("MapPlaceholder")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.map_label)
        
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)

    def clear(self):
        """清除地图和所有节点复选框。"""
        self.map_label.clear()
        self._original_pixmap = QPixmap()
        for checkbox in self._node_checkboxes.values():
            checkbox.deleteLater()
        self._node_checkboxes.clear()
        self._node_data = {}

    def set_text(self, text):
        """显示文本信息而不是地图。"""
        self.clear()
        self.map_label.setText(text)

    def set_map_and_nodes(self, pixmap, nodes_data, selected_nodes=None):
        """设置地图图片并为给定的节点数据创建复选框。"""
        self.clear()
        
        if pixmap.isNull():
            self.set_text("地图无法加载。")
            return

        self._original_pixmap = pixmap
        self._node_data = nodes_data or {}
        self._last_emitted_selection = set(selected_nodes or [])
        
        for name in self._node_data.keys():
            checkbox = CustomCheckBox(parent=self)
            checkbox.toggled.connect(self._on_checkbox_state_changed)
            self._node_checkboxes[name] = checkbox

        if selected_nodes:
            self._set_selected_nodes_quietly(selected_nodes)

        self._validate_and_update_all_nodes()
        self._update_display()
        
    def _set_selected_nodes_quietly(self, selected_nodes):
        """静默设置节点的选中状态，不发射信号。"""
        for name, checkbox in self._node_checkboxes.items():
            checkbox.blockSignals(True)
            checkbox.setChecked(name in selected_nodes)
            checkbox.blockSignals(False)

    def get_selected_nodes(self):
        """返回所有被选中的节点名称列表。"""
        return [name for name, checkbox in self._node_checkboxes.items() if checkbox.isChecked()]

    def _on_checkbox_state_changed(self):
        """当复选框状态改变时，触发完整的验证和更新流程。"""
        self._validate_and_update_all_nodes()

    def resizeEvent(self, event):
        """通过更新图片和节点位置来处理控件大小调整事件。"""
        super().resizeEvent(event)
        self._update_display()

    def _get_pixmap_geometry(self):
        """计算缩放后的图片在标签内的实际屏幕几何区域。"""
        if self._original_pixmap.isNull() or self.map_label.width() == 0 or self.map_label.height() == 0:
            return QRect()

        label_size = self.map_label.size()
        scaled_pixmap = self._original_pixmap.scaled(label_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        x_offset = (label_size.width() - scaled_pixmap.width()) / 2
        y_offset = (label_size.height() - scaled_pixmap.height()) / 2
        
        return QRect(x_offset, y_offset, scaled_pixmap.width(), scaled_pixmap.height())

    def _update_display(self):
        """更新缩放后的图片并重新定位所有节点复选框。"""
        if self._original_pixmap.isNull():
            return

        scaled_pixmap = self._original_pixmap.scaled(
            self.map_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.map_label.setPixmap(scaled_pixmap)
        
        pixmap_rect = self._get_pixmap_geometry()

        for name, checkbox in self._node_checkboxes.items():
            node_info = self._node_data.get(name, {})
            pos_data = node_info.get('pos')

            if not pos_data or len(pos_data) != 2:
                checkbox.hide()
                continue

            rel_x, rel_y = pos_data
            abs_x = pixmap_rect.x() + rel_x * pixmap_rect.width()
            abs_y = pixmap_rect.y() + rel_y * pixmap_rect.height()
            
            chk_x = abs_x - checkbox.width() / 2
            chk_y = abs_y - checkbox.height() / 2
            
            checkbox.move(int(chk_x), int(chk_y))
            checkbox.show()

    def _validate_and_update_all_nodes(self):
        """
        验证节点选择的有效性，自动取消孤立节点，并更新所有节点的可用状态。
        """
        for checkbox in self._node_checkboxes.values():
            checkbox.blockSignals(True)

        currently_checked_set = set(self.get_selected_nodes())
        validly_selected = set()
        
        queue = [name for name, info in self._node_data.items() if info.get('is_start') and name in currently_checked_set]
        visited = set(queue)

        while queue:
            node_name = queue.pop(0)
            validly_selected.add(node_name)
            
            node_info = self._node_data.get(node_name, {})
            connections = node_info.get('connections', [])
            
            if connections:
                for conn_name in connections:
                    if conn_name in currently_checked_set and conn_name not in visited:
                        visited.add(conn_name)
                        queue.append(conn_name)

        orphaned_nodes = currently_checked_set - validly_selected
        if orphaned_nodes:
            for name in orphaned_nodes:
                self._node_checkboxes[name].setChecked(False)

        nodes_to_enable = set()
        
        for name, info in self._node_data.items():
            if info.get('is_start'):
                nodes_to_enable.add(name)

        nodes_to_enable.update(validly_selected)
        for name in validly_selected:
            node_info = self._node_data.get(name, {})
            connections = node_info.get('connections', [])
            if connections:
                nodes_to_enable.update(connections)

        for name, checkbox in self._node_checkboxes.items():
            checkbox.setEnabled(name in nodes_to_enable)
            checkbox.blockSignals(False)

        new_selection_set = set(validly_selected)
        if new_selection_set != self._last_emitted_selection:
            self._last_emitted_selection = new_selection_set
            self.selection_changed.emit(list(validly_selected))

class PlanEditorTab(QWidget):
    """用于编辑任务计划的标签页"""

    def __init__(self, ui_configs_data, ui_configs_path, yaml_manager, parent=None):
        super().__init__(parent)
        self.current_plan_path_dir = ""
        self.plan_root_path = self._get_plan_root_path()
        self.yaml_manager = yaml_manager
        self.ui_configs_data = ui_configs_data
        self.ui_configs_path = ui_configs_path
        self.normal_map_configs = self._load_normal_map_configs()
        self.event_map_configs = self._load_event_map_configs()
        self.current_plan_data = None
        self.is_dirty = False 
        self._current_plan_file_path = None
        self._last_root_text = ""
        self._last_event_text = ""
        self._last_plan_text = ""
        self._setup_ui()
        self._connect_signals()
        self._populate_root_combo()
        QApplication.instance().installEventFilter(self)

    def _load_normal_map_configs(self):
        """加载普通地图的节点配置"""
        try:
            with open(NORMAL_MAP_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}
    
    def _load_event_map_configs(self):
        """加载活动地图的节点配置"""
        try:
            with open(EVENT_MAP_CONFIGS_FILE, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def _get_plan_root_path(self):
        """读取 plan_root 路径"""
        try:
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = yaml.safe_load(f)
                return settings.get('plan_root')
        except (FileNotFoundError, Exception):
            return None

    def _setup_ui(self):
        """构建UI界面。"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        # 左侧面板
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(10, 0, 0, 0)

        top_section_widget = QWidget()
        top_section_layout = QHBoxLayout(top_section_widget)
        top_section_layout.setContentsMargins(0, 0, 0, 0)

        file_selector_widget = QFrame()
        file_selector_layout = QVBoxLayout(file_selector_widget)

        self.root_combo = CustomComboBox()
        self.event_combo = CustomComboBox()
        self.event_combo.setEnabled(False)
        self.plan_combo = CustomComboBox()
        self.new_plan_button = QPushButton("新建计划")
        self.new_plan_button.setProperty('class', 'TallButton')
        self.new_plan_description = QLabel("点击新建时，新建的计划会保存在<br>“计划类型”或“活动”文件夹内")
        self.new_plan_description.setObjectName('DescriptionLabel')
        self.delete_plan_button = QPushButton("删除当前计划")
        self.delete_plan_button.setProperty('class', 'TallButton')
        self.delete_button_manager = ConfirmButtonManager(
            self.delete_plan_button, "确认删除",
            pre_condition_check=lambda: self.delete_plan_button.isEnabled()
        )

        file_selector_layout.addWidget(QLabel("计划类型:"))
        file_selector_layout.addWidget(self.root_combo)
        file_selector_layout.addSpacing(10)
        file_selector_layout.addWidget(QLabel("选择活动:"))
        file_selector_layout.addWidget(self.event_combo)
        file_selector_layout.addSpacing(10)
        file_selector_layout.addWidget(QLabel("计划文件:"))
        file_selector_layout.addWidget(self.plan_combo)
        file_selector_layout.addSpacing(10)
        file_selector_layout.addWidget(self.new_plan_button)
        file_selector_layout.addSpacing(10)
        file_selector_layout.addWidget(self.delete_plan_button)
        file_selector_layout.addWidget(self.new_plan_description)
        file_selector_layout.addStretch()

        plan_summary_widget = QFrame()
        plan_summary_layout = QVBoxLayout(plan_summary_widget)
        self.plan_summary_text = QTextEdit()
        self.plan_summary_text.setReadOnly(True)
        plan_summary_layout.addWidget(self.plan_summary_text)

        top_section_layout.addWidget(file_selector_widget, 1)
        top_section_layout.addWidget(plan_summary_widget, 2)

        map_container_widget = QWidget()
        map_container_layout = QVBoxLayout(map_container_widget)
        map_container_layout.setContentsMargins(9, 0, 9, 0)
        
        self.map_display_widget = MapDisplayWidget(self)
        self.map_display_widget.set_text("请选择一个计划文件以显示地图")
        
        map_container_layout.addWidget(self.map_display_widget)
        left_layout.addWidget(top_section_widget, 7)
        left_layout.addWidget(map_container_widget, 8)
        # 右侧面板
        right_panel_container = QWidget()
        right_panel_layout = QVBoxLayout(right_panel_container)
        right_panel_layout.setContentsMargins(0, 0, 0, 0)

        # 创建保存取消按钮
        self.save_button, self.cancel_button = create_ok_cancel_buttons()
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 0, 10)
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        # 滚动区域
        self.settings_panel = PlanSettingsWidget(self.yaml_manager, self.ui_configs_data, self.ui_configs_path)
        self.node_settings_panel = NodeSettingsEditorWidget()
        

        right_scroll_area = QScrollArea()
        right_scroll_area.setWidgetResizable(True)  # 允许内部控件随滚动区域大小变化而调整
        right_scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        right_content_container = QWidget()
        right_content_container.setObjectName("ScrollAreaContentContainer")
        right_layout = QVBoxLayout(right_content_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.settings_panel)
        right_layout.addWidget(self.node_settings_panel)
        right_layout.addStretch()
        right_scroll_area.setWidget(right_content_container)
        # 集成
        right_panel_layout.addLayout(button_layout)
        right_panel_layout.addWidget(right_scroll_area)
        main_layout.addWidget(left_panel, 2)
        main_layout.addWidget(right_panel_container, 1)
        # 初始禁用
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def _connect_signals(self):
        """连接所有UI控件的信号到其处理函数。"""
        self.root_combo.currentTextChanged.connect(self._on_root_changed)
        self.event_combo.currentTextChanged.connect(self._on_event_changed)
        self.plan_combo.currentTextChanged.connect(self._on_plan_selected)
        self.new_plan_button.clicked.connect(self._on_new_plan_clicked)
        self.delete_button_manager.confirmed_click.connect(self._on_delete_plan_clicked)
        self.save_button.clicked.connect(self._on_save_clicked)
        self.cancel_button.clicked.connect(self._on_cancel_clicked)
        self.settings_panel.plan_data_changed.connect(self._on_plan_settings_changed)
        self.map_display_widget.selection_changed.connect(self._on_node_selection_changed)
        self.settings_panel.custom_ships_updated.connect(self._on_custom_ships_updated)
        self.node_settings_panel.settings_changed.connect(lambda: self._set_dirty(True))
    
    # --- 状态管理 ---
    def _update_file_action_buttons_state(self):
        """更新文件操作按钮的启用状态。"""
        # 检查是否有一个有效的、真实存在的文件被选中
        is_plan_selected = (self._current_plan_file_path is not None and 
                            self._current_plan_file_path.exists())
        self.delete_plan_button.setEnabled(is_plan_selected and not self.is_dirty)
        # 重置删除按钮的确认状态
        if hasattr(self, 'delete_button_manager'):
             self.delete_button_manager.reset_state()

    def _set_dirty(self, is_dirty):
        """设置UI的未保存状态，并集中管理所有相关控件的启用/禁用。"""
        self.is_dirty = is_dirty
        # 保存/取消 按钮
        self.save_button.setEnabled(is_dirty)
        self.cancel_button.setEnabled(is_dirty)
        # 导航/文件操作 按钮
        is_nav_enabled = not self.is_dirty
        self.root_combo.setEnabled(is_nav_enabled)
        # 只有在导航启用 且 根目录是 'event' 时才启用
        is_event_root = (self.root_combo.currentText().lower() == 'event')
        self.event_combo.setEnabled(is_nav_enabled and is_event_root)
        # 只有在导航启用 且 计划列表有内容时 才启用
        is_plan_list_valid = (self.plan_combo.count() > 0 and not self.plan_combo.currentText().startswith('['))
        self.plan_combo.setEnabled(is_nav_enabled and is_plan_list_valid)
        # 只有在导航启用 且 存在有效保存路径时 才启用
        has_valid_path = (self.current_plan_path_dir != "" and os.path.isdir(self.current_plan_path_dir))
        self.new_plan_button.setEnabled(is_nav_enabled and has_valid_path)
        # 只有在导航启用 且 选中了一个真实文件时 才启用
        is_plan_selected = (self._current_plan_file_path is not None and 
                            self._current_plan_file_path.exists())
        self.delete_plan_button.setEnabled(is_nav_enabled and is_plan_selected)
        # 重置删除按钮的确认状态
        if hasattr(self, 'delete_button_manager'):
            self.delete_button_manager.reset_state()
        # 更新预览
        if is_dirty and self.current_plan_data:
            self._update_plan_summary_from_memory()
        # 重置保存按钮的 "warning" 状态
        self.save_button.setProperty("warning", "")
        self.save_button.style().unpolish(self.save_button)
        self.save_button.style().polish(self.save_button)

    def _on_save_clicked(self):
        """保存按钮：将内存保存到文件"""
        self._save_current_plan()
        self._set_dirty(False)
        # 刷新只读预览
        self._update_plan_summary(self._current_plan_file_path)

    def _on_cancel_clicked(self):
        """取消按钮：从文件重新加载，丢弃内存更改"""
        self._set_dirty(False)
        # 重新加载当前选定的文件，这会覆盖所有内存更改
        self._on_plan_selected(self.plan_combo.currentText())

    # --- combox守卫 ---
    def _populate_root_combo(self):
        """填充第一层下拉框（计划类型）。"""
        self.root_combo.clear()
        if not self.plan_root_path or not os.path.isdir(self.plan_root_path):
            self.root_combo.addItem("[计划文件夹未找到]")
            self.root_combo.setEnabled(False)
            return
        try:
            dirs = [d for d in os.listdir(self.plan_root_path) if os.path.isdir(os.path.join(self.plan_root_path, d))]
            if dirs:
                self.root_combo.addItems(sorted(dirs))
                self._last_root_text = self.root_combo.currentText()
            else:
                self.root_combo.addItem("[无内容]")
                self.root_combo.setEnabled(False)
        except Exception:
            self.root_combo.addItem("[读取错误]")
            self.root_combo.setEnabled(False)

    def _on_root_changed(self, selected_dir):
        """当第一层下拉框变化时的处理函数。"""
        self._clear_displays()
        if not selected_dir or selected_dir.startswith('['):
            self.plan_combo.clear()
            self.event_combo.hide()
            return
        if selected_dir.lower() == 'event':
            self.event_combo.setEnabled(True)
            self._populate_event_combo(selected_dir)
        else:
            self.event_combo.setEnabled(False)
            self.event_combo.clear()
            self.current_plan_path_dir = os.path.join(self.plan_root_path, selected_dir)
            self._populate_plan_combo(self.current_plan_path_dir)

    def _populate_event_combo(self, root_dir):
        """填充第二层下拉框（活动文件夹）。"""
        self.event_combo.clear()
        event_path = os.path.join(self.plan_root_path, root_dir)
        try:
            dirs = [d for d in os.listdir(event_path) if os.path.isdir(os.path.join(event_path, d))]
            if dirs:
                self.event_combo.addItems(sorted(dirs))
                self._last_event_text = self.event_combo.currentText()
                self.event_combo.setEnabled(True)
            else:
                self.event_combo.addItem("[无内容]")
                self.event_combo.setEnabled(False)
        except Exception:
            self.event_combo.addItem("[路径错误]")
            self.event_combo.setEnabled(False)

    def _on_event_changed(self, selected_event_dir):
        """当第二层下拉框变化时的处理函数。"""
        self._clear_displays()
        root_dir = self.root_combo.currentText()
        if not selected_event_dir or selected_event_dir.startswith('[') or not root_dir:
            self.plan_combo.clear()
            return
        self.current_plan_path_dir = os.path.join(self.plan_root_path, root_dir, selected_event_dir)
        self._populate_plan_combo(self.current_plan_path_dir)

    def _populate_plan_combo(self, full_path):
        """填充第三层下拉框。"""
        self.plan_combo.clear()
        try:
            files = [f for f in os.listdir(full_path) if f.endswith('.yaml') and os.path.isfile(os.path.join(full_path, f))]
            if files:
                self.plan_combo.addItems(sorted(files))
                self._last_plan_text = self.plan_combo.currentText()
                self.plan_combo.setEnabled(True)
            else:
                self.plan_combo.addItem("[无计划文件]")
                self.plan_combo.setEnabled(False)
        except Exception:
            self.plan_combo.addItem("[路径错误]")
            self.plan_combo.setEnabled(False)

    def _on_plan_file_updated(self):
        """当接收到计划文件已更新的信号时，重新从文件读取内容以刷新显示。"""
        plan_filename = self.plan_combo.currentText()
        if not plan_filename or plan_filename.startswith('[') or not self.current_plan_path_dir:
            return

        file_path = Path(self.current_plan_path_dir) / plan_filename
        if file_path.exists():
            self._on_plan_selected(plan_filename)

    def _refresh_displays_from_memory(self):
        """根据内存中的 self.current_plan_data 刷新地图和节点设置。"""
        if self.current_plan_data is None:
            # 如果没有数据，确保清除
            self._clear_displays()
            return

        # 刷新地图
        nodes_data, map_path_or_flag = self._get_nodes_data_and_map_path()
        self._update_map_display(nodes_data, map_path_or_flag)
        
        # 刷新节点设置
        plan_type = self.root_combo.currentText()
        selected_nodes = self.current_plan_data.get('selected_nodes') or []
        self.node_settings_panel.load_plan(
            plan_type, 
            self.current_plan_data,
            selected_nodes,
            nodes_data
        )

    def _update_plan_summary_from_memory(self):
        """从内存中的 self.current_plan_data 刷新预览"""
        if not self.current_plan_data:
            self.plan_summary_text.clear()
            return
            
        try:
            # 使用 YAML管理器 将内存数据转储到字符串流
            stream = io.StringIO()
            self.yaml_manager.dump(self.current_plan_data, stream)
            full_text = stream.getvalue()

            lines = full_text.splitlines()
            clean_lines = []
            for line in lines:
                line_no_comment = re.sub(r'\s*#.*$', '', line).rstrip()
                if line_no_comment:
                    clean_lines.append(line_no_comment)
            self.plan_summary_text.setText("\n".join(clean_lines))
        except Exception as e:
            self.plan_summary_text.setText(f"渲染预览时出错:\n{e}")

    def _update_plan_summary(self, file_path):
        """读取文件，去除注释和空行，并显示在文本框中。"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            clean_lines = []
            for line in lines:
                line_no_comment = re.sub(r'\s*#.*$', '', line).rstrip()
                if line_no_comment:
                    clean_lines.append(line_no_comment)
            self.plan_summary_text.setText("\n".join(clean_lines))
        except Exception as e:
            self.plan_summary_text.setText(f"读取文件时出错:\n{e}")

    def _get_nodes_data_and_map_path(self):
        """
        根据当前计划数据，获取节点配置和地图图像路径。
        返回 (nodes_data, map_image_path_or_flag)
        """
        if not self.current_plan_data:
            return None, None

        plan_type = self.root_combo.currentText().lower()
        if plan_type in ['exercise', 'battle']:
            return None, "no_map"

        chapter = self.current_plan_data.get('chapter')
        map_num = self.current_plan_data.get('map')
        if chapter is None or map_num is None:
            return None, "missing_keys"

        map_image_name = f"{chapter}-{map_num}.jpg"
        map_image_path = ""
        nodes_data = None

        if plan_type in ['normal_fight', 'week', 'special_ap_task']:
            map_image_path = os.path.join(MAP_PICS_DIR, 'normal_fight', map_image_name)
            chapter_key = f"chapter{chapter}"
            map_key = f"{chapter}-{map_num}"
            nodes_data = self.normal_map_configs.get(chapter_key, {}).get(map_key, {}).get('nodes')
        elif plan_type == 'event':
            specific_event_folder = self.event_combo.currentText()
            if not specific_event_folder:
                return None, "no_event_folder"
            map_image_path = os.path.join(MAP_PICS_DIR, 'event', specific_event_folder, map_image_name)
            map_key = f"{chapter}-{map_num}"
            nodes_data = self.event_map_configs.get(specific_event_folder, {}).get(map_key, {}).get('nodes')

        return nodes_data, map_image_path
    
    def _update_map_display(self, nodes_data, map_image_path):
        """根据传入的数据更新地图显示。"""
        if map_image_path == "no_map":
            self.map_display_widget.set_text("演习/战役无地图")
            return
        if map_image_path == "missing_keys":
            self.map_display_widget.set_text("计划文件中缺少\n'chapter' 或 'map' 键")
            return
        if map_image_path == "no_event_folder":
            self.map_display_widget.set_text("请先选择一个具体活动")
            return

        if map_image_path and os.path.exists(map_image_path):
            pixmap = QPixmap(map_image_path)
            selected_nodes = self.current_plan_data.get('selected_nodes') or []
            self.map_display_widget.set_map_and_nodes(pixmap, nodes_data, selected_nodes)
        elif map_image_path:
            relative_path = os.path.join(os.path.basename(MAP_PICS_DIR), os.path.relpath(map_image_path, MAP_PICS_DIR))
            self.map_display_widget.set_text(f"地图图片未找到:\n...\\{relative_path}")
        else:
            plan_type = self.root_combo.currentText().lower()
            self.map_display_widget.set_text(f"不支持的计划类型 '{plan_type}'")

    def _clear_displays(self):
        """清空计划概要、地图显示和内存数据。"""
        self.current_plan_data = None
        self.plan_summary_text.clear()
        self.map_display_widget.set_text("请选择一个计划文件以显示地图")

        if hasattr(self, 'settings_panel'):
            self.settings_panel.clear_and_hide()

        self._set_dirty(False)
        self.save_button.setEnabled(False)
        self.cancel_button.setEnabled(False)
        self._current_plan_file_path = None

        if hasattr(self, 'node_settings_panel'):
            self.node_settings_panel.hide()

    def _on_plan_selected(self, index_or_text):
        """当最终的计划文件被选择时，加载数据并更新UI。"""
        plan_filename = ""
        if isinstance(index_or_text, int): # 来自用户点击
            plan_filename = self.plan_combo.itemText(index_or_text)
        elif isinstance(index_or_text, str): # 来自代码调用
            plan_filename = index_or_text
            
        self.current_plan_data = None
        if not plan_filename or plan_filename.startswith('['):
            self._clear_displays()
            return

        file_path = Path(self.current_plan_path_dir) / plan_filename
        self._current_plan_file_path = file_path

        if file_path.exists():
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    self.current_plan_data = self.yaml_manager.load(f) or {}
            except Exception as e:
                print(f"加载计划 {plan_filename} 失败: {e}")
                self.current_plan_data = {}

            # 重置脏状态
            self._set_dirty(False)
            self.save_button.setEnabled(False)
            self.cancel_button.setEnabled(False)
            # 获取节点和地图数据
            nodes_data, map_path_or_flag = self._get_nodes_data_and_map_path()
            selected_nodes = self.current_plan_data.get('selected_nodes') or []
            # 更新计划概和地图显示
            self._update_plan_summary(file_path)
            self._update_map_display(nodes_data, map_path_or_flag)
            # 加载设置面板
            plan_type = self.root_combo.currentText()
            self.settings_panel.load_plan(plan_type, self.current_plan_data)
            self.node_settings_panel.load_plan(
                plan_type, 
                self.current_plan_data,  # 传入整个数据字典
                selected_nodes,          # 传入节点列表
                nodes_data               # 传入节点配置
            )
        else:
            self._clear_displays()
        self._update_file_action_buttons_state()

    def _save_current_plan(self):
        """
        中央保存函数。保存内存中的当前状态。
        """
        if self.current_plan_data is None or self._current_plan_file_path is None:
            return

        plan_type = self.root_combo.currentText().lower()
        key_order = KEY_ORDER_MAP.get(plan_type)

        data_to_save = self.current_plan_data
        try:
            save_config(self.yaml_manager, data_to_save, self._current_plan_file_path, key_order=key_order)
        except Exception as e:
            print(f"保存计划失败: {e}")
            
    def _on_node_selection_changed(self, selected_nodes):
        """当用户在地图上勾选节点时，使用工具函数更新配置并设置为脏。"""
        # 当地图选择变化时，立即更新节点设置下拉框的内容
        if hasattr(self, 'node_settings_panel'):
            self.node_settings_panel.update_node_list(selected_nodes)
        if self.current_plan_data is None:
            return
        # 删除已取消勾选的节点的 node_args
        plan_type = self.root_combo.currentText().lower()
        # 仅在地图型计划中执行此操作
        if 'node_args' in self.current_plan_data and plan_type in ['normal_fight', 'week', 'special_ap_task', 'event']:
            node_args_dict = self.current_plan_data.get('node_args') or {}
            selected_nodes_set = set(selected_nodes)
            # 找出所有在内存中但不在新选择列表中的节点
            nodes_to_delete = set(node_args_dict.keys()) - selected_nodes_set
            for node in nodes_to_delete:
                del self.current_plan_data['node_args'][node]
            if not self.current_plan_data['node_args']:
                del self.current_plan_data['node_args']
        # 更新内存中的 selected_nodes
        flow_style_nodes = CommentedSeq(selected_nodes)
        flow_style_nodes.fa.set_flow_style()
        update_config_value(self.current_plan_data, 'selected_nodes', flow_style_nodes)
        # 设置为脏
        self._set_dirty(True)

    def _on_node_settings_changed(self):
        """当节点设置(默认或单独)变化时，更新内存中的数据并设置为脏。"""
        if self.current_plan_data is None:
            return
        self._set_dirty(True)

    def _on_custom_ships_updated(self, custom_ships: list):
        """当自定义舰船列表更新时，保存到 user_configs.yaml 文件。"""
        if not self.ui_configs_path:
            return
        update_config_value(self.ui_configs_data, 'custom_names', CommentedSeq(custom_ships))
        try:
            save_config(self.yaml_manager, self.ui_configs_data, self.ui_configs_path)
        except Exception as e:
            print(f"Error saving custom ships to {self.ui_configs_path}: {e}")
    
    def _on_plan_settings_changed(self):
        """当 PlanSettingsWidget 中的数据发生变化时调用。"""
        self._set_dirty(True)
        self._refresh_displays_from_memory()
    
    def can_safely_close_tab(self) -> bool:
        """
        公共API，供主窗口在切换Tab前调用。
        返回 False 表示应阻止切换。
        """
        if self._check_if_dirty_and_block():
            return False
        return True
    
    def _on_new_plan_clicked(self):
        """处理“新建计划”按钮点击事件。"""
        plan_type = self.root_combo.currentText()
        dialog = NewPlanDialog(parent=self, save_dir_path=self.current_plan_path_dir)
        if not dialog.exec():return

        full_file_path = dialog.get_confirmed_path()
        default_data = self._get_default_plan_data(plan_type)
        key_order = KEY_ORDER_MAP.get(plan_type.lower())
        save_config(self.yaml_manager, default_data, full_file_path, key_order=key_order)
        self._populate_plan_combo(self.current_plan_path_dir)
        self.plan_combo.setCurrentText(full_file_path.name)

    def _get_default_plan_data(self, plan_type: str) -> dict:
        """根据 plan_type 推断并返回一个包含默认设置的字典。"""
        plan_type = plan_type.lower()
        if plan_type in ['normal_fight', 'week', 'special_ap_task']:
            return {'chapter': 1, 'map': 1, 'repair_mode': 2, 'fleet_id': 1}  
        elif plan_type == 'battle':
            return {'map': 1, 'repair_mode': 2}
        elif plan_type == 'event':
            return {'chapter': 'H', 'map': 1, 'repair_mode': 2, 'fleet_id': 0, 'from_alpha': True}
        elif plan_type == 'exercise':
            return {'exercise_times': 4, 'robot': True, 'fleet_id': 2, 'max_refresh_times': 2}
        else:
            return {}

    def _on_delete_plan_clicked(self):
        """处理“确认删除”按钮的点击事件。""" 
        file_to_delete = self._current_plan_file_path
        try:
            file_to_delete.unlink()
            self._clear_displays()
            self._populate_plan_combo(self.current_plan_path_dir)
        except Exception: return
    
    def _check_if_dirty_and_block(self) -> bool:
        """检查是否有未保存的更改。"""
        if not self.is_dirty:
            return False # 不脏
        # 应用 "warning" 样式以闪烁按钮
        self.save_button.setProperty("warning", "true")
        self.save_button.style().unpolish(self.save_button)
        self.save_button.style().polish(self.save_button)
        return True # 很脏，阻止
    
    def eventFilter(self, watched, event: QEvent):
        """全局事件过滤器，用于处理点击空白处取消二次确认的逻辑。"""
        # 仅在当前标签页可见时才处理事件
        if not self.isVisible():
            return super().eventFilter(watched, event)
        # 检查事件类型
        if event.type() == QEvent.Type.MouseButtonPress:
            if hasattr(self, 'delete_button_manager') and self.delete_button_manager.is_confirming():
                clicked_widget = QApplication.widgetAt(event.globalPosition().toPoint())
                is_on_delete_button = clicked_widget and (
                    self.delete_plan_button == clicked_widget or 
                    self.delete_plan_button.isAncestorOf(clicked_widget)
                )
                # 如果点击的不是删除按钮，则重置它
                if not is_on_delete_button:
                    self.delete_button_manager.reset_state()
        return super().eventFilter(watched, event)