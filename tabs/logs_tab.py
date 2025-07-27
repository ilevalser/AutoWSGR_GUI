from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QFrame, QLabel
)
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import Slot, Signal, Qt
from ansi2html import Ansi2HTMLConverter
from tabs.components.combo_box import CustomComboBox
from tabs.components.check_box import CustomCheckBox
from utils.ui_utils import create_form_layout, create_group
from utils.config_utils import update_config_value, save_config

class LogTab(QWidget):
    """专门的日志显示选项卡，带有快捷控制功能"""
    quick_start_request = Signal(str)
    quick_stop_request = Signal()

    def __init__(self, configs_data, configs_path, yaml_manager, parent=None):
        super().__init__(parent)
        self.configs_data = configs_data
        self.configs_path = configs_path
        self.yaml_manager = yaml_manager
        self.ansi_converter = Ansi2HTMLConverter(scheme='xterm', inline=True)
        self._setup_ui()
        self._connect_signals()
        self._load_initial_settings()

    def _setup_ui(self):
        """构建UI界面，采用左右布局"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 左侧控制面板
        left_panel = QFrame()
        left_panel.setObjectName("LogControlPanel")
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # 快捷启动
        self.quick_start_stop_button = QPushButton("快捷启动")
        self.quick_start_stop_button.setProperty("class", "StartStopButton")
        self.task_selector_combo = CustomComboBox()
        task_selector_layout = create_form_layout(
            [((QLabel("选择任务:"), self.task_selector_combo), "选择要快速启动的任务")],
            column_stretches=(1, 1)
        )
        quick_start_layout = QVBoxLayout()
        quick_start_layout.addWidget(self.quick_start_stop_button)
        quick_start_layout.addLayout(task_selector_layout)
        quick_start_group = create_group("快捷启动", quick_start_layout)
        left_layout.addWidget(quick_start_group)
        left_layout.addSpacing(10)

        # 日志设置
        self.clear_log_button = QPushButton("清空日志")
        self.clear_log_button.setProperty("class", "StartStopButton")
        self.auto_scroll_checkbox = CustomCheckBox("自动滚动日志")
        auto_scroll_layout = create_form_layout(
            [(self.auto_scroll_checkbox, None)],
            column_stretches=(1, 1)
        )
        log_settings_layout = QVBoxLayout()
        log_settings_layout.addWidget(self.clear_log_button)
        log_settings_layout.addLayout(auto_scroll_layout)
        auto_scroll_group = create_group("日志设置", log_settings_layout)
        left_layout.addWidget(auto_scroll_group)
        left_layout.addStretch()

        # 右侧日志显示区
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)

        # 添加到主布局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.log_display, 2)

    def _connect_signals(self):
        """连接内部控件的信号"""
        self.quick_start_stop_button.clicked.connect(self._on_quick_button_clicked)
        self.auto_scroll_checkbox.toggled.connect(self._on_auto_scroll_toggled)
        self.clear_log_button.clicked.connect(self._clear_log)

    def _on_quick_button_clicked(self):
        """根据按钮的当前状态，决定是发送启动还是中止信号"""
        is_running = self.quick_start_stop_button.property("running")
        if is_running:
            self.quick_stop_request.emit()
        else:
            task_name = self.task_selector_combo.currentText()
            if task_name:
                self.quick_start_request.emit(task_name)

    def _clear_log(self):
        """清空日志框内容"""
        self.log_display.clear()

    def _load_initial_settings(self):
        """从配置文件加载初始UI状态"""
        saved_auto_scroll = self.configs_data.get('auto_scroll', True)
        self.auto_scroll_enabled = saved_auto_scroll
        self.auto_scroll_checkbox.blockSignals(True)
        self.auto_scroll_checkbox.setChecked(saved_auto_scroll)
        self.auto_scroll_checkbox.blockSignals(False)
        self.auto_scroll_checkbox.update_icon()

    @Slot(bool)
    def _on_auto_scroll_toggled(self, checked):
        """更新自动滚动状态"""
        self.auto_scroll_enabled = checked
        update_config_value(self.configs_data, 'auto_scroll', checked)
        save_config(self.yaml_manager, self.configs_data, self.configs_path)

    @Slot(str)
    def append_log_message(self, message):
        """槽函数，用于接收并显示日志信息，并根据设置滚动"""
        message = message.rstrip()
        self.log_display.moveCursor(QTextCursor.MoveOperation.End)
        self.log_display.insertPlainText(message + "\n")
        if self.auto_scroll_enabled:
            self.log_display.verticalScrollBar().setValue(
                self.log_display.verticalScrollBar().maximum()
            )

    @Slot(bool, str)
    def update_for_task_state(self, is_running: bool, task_name: str = ""):
        """
        根据全局任务状态更新本页面的UI。
        此槽函数由 MainWindow 调用。

        :param is_running: 任务是否正在运行
        :param task_name: 如果在运行，当前运行的任务名
        """
        if is_running:
            self.quick_start_stop_button.setText(f"中止{task_name}")
            self.quick_start_stop_button.setProperty("running", True)
            self.task_selector_combo.setEnabled(False)
        else:
            self.quick_start_stop_button.setText("启动任务")
            self.quick_start_stop_button.setProperty("running", False)
            self.task_selector_combo.setEnabled(True)
        self.quick_start_stop_button.style().polish(self.quick_start_stop_button)

    @Slot(str)
    def append_log_message(self, message_chunk: str):
        """槽函数，用于接收并显示日志信息。"""
        lines = message_chunk.splitlines()

        # 遍历这个列表，对每一行独立进行处理
        for line in lines:
            if not line:
                continue

            processed_line = line.replace(" [36mautowsgr", "")
            html_line = self.ansi_converter.convert(processed_line, full=False)
            self.log_display.append(html_line)
        
        if self.auto_scroll_enabled and lines:
            self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())