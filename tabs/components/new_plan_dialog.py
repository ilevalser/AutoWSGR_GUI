from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget
from PySide6.QtCore import Qt, QEvent

class NewPlanDialog(QDialog):
    """
    一个自定义的、无边框的对话框，用于创建新计划。
    它处理文件名输入、空值验证和文件存在性验证。
    """
    def __init__(self, parent: QWidget, save_dir_path: str):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("Dialog")
        self.setWindowTitle("新建计划")
        self.setMinimumSize(300, 150)

        self.save_dir_path = Path(save_dir_path)
        self.confirmed_path = None # 将在成功时设置
        self._setup_ui()
        self._connect_signals()
        self.line_edit.setFocus() # 打开时立即聚焦到输入框

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        self.label = QLabel("请输入文件名:")
        self.line_edit = QLineEdit()
        
        
        # 用于显示 "文件名不能为空" 或 "文件已存在" 等错误
        self.error_label = QLabel()
        self.error_label.setObjectName("DescriptionLabel") # 你可以在QSS中将其设置为红色
        self.error_label.setWordWrap(True)
        self.error_label.hide() # 默认隐藏

        self.ok_button = QPushButton("确认")
        self.cancel_button = QPushButton("取消")
        self.ok_button.setProperty("class", "OkCancelButton")
        self.cancel_button.setProperty("class", "OkCancelButton")

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        layout.addWidget(self.label)
        layout.addWidget(self.line_edit)
        layout.addStretch()
        layout.addWidget(self.error_label)
        layout.addLayout(button_layout)

        self.line_edit.installEventFilter(self)

    def _connect_signals(self):
        self.ok_button.clicked.connect(self.accept) 
        self.cancel_button.clicked.connect(self.reject)
        self.line_edit.returnPressed.connect(self.accept)

    def eventFilter(self, watched, event: QEvent):
        """事件过滤器，用于在 line_edit 获得焦点时清除错误状态。"""
        if watched == self.line_edit and event.type() == QEvent.Type.FocusIn:
            self._clear_error_state()
        return super().eventFilter(watched, event)

    def get_confirmed_path(self) -> Path | None:
        return self.confirmed_path

    def accept(self):
        """覆盖 accept() 槽，以执行所有验证。"""
        text = self.line_edit.text().strip()
        # 验证是否为空
        if not text:
            self.line_edit.setProperty("state", "invalid")
            self.line_edit.style().unpolish(self.line_edit)
            self.line_edit.style().polish(self.line_edit)
            self.error_label.setText("文件名不能为空。")
            self.error_label.show()
            return # 不关闭对话框
        # 格式化文件名
        file_name = text
        if not file_name.endswith('.yaml'):
            file_name += '.yaml'
        full_path = self.save_dir_path / file_name
        # 检查文件是否存在
        if full_path.exists():
            self.line_edit.setProperty("state", "invalid")
            self.line_edit.style().unpolish(self.line_edit)
            self.line_edit.style().polish(self.line_edit)
            self.error_label.setText(f"文件 '{file_name}' 已存在。请使用其他名称。")
            self.error_label.show()
            return # 不关闭对话框

        self.confirmed_path = full_path
        super().accept()
    
    def _clear_error_state(self):
        """清除错误标签和红色边框。"""
        self.error_label.hide()
        self.line_edit.setProperty("state", "valid")
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)