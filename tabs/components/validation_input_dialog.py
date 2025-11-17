from pathlib import Path
from PySide6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget
from PySide6.QtCore import Qt, QEvent
from abc import ABC, abstractmethod

class BaseValidator(ABC):
    """
    校验器策略的抽象基类。
    validate 方法在成功时返回处理后的值，在失败时引发 ValueError。
    """
    @abstractmethod
    def validate(self, text: str):
        pass

class PlanValidator(BaseValidator):
    def __init__(self, save_dir_path: Path):
        self.save_dir_path = save_dir_path

    def validate(self, text: str):
        """校验文件名、添加后缀并检查是否存在"""
        if not self.save_dir_path or not self.save_dir_path.is_dir():
            raise ValueError(f"无效的保存目录:\n{self.save_dir_path}")

        if not text:
            raise ValueError("文件名不能为空。")
        
        file_name = text
        if not file_name.endswith('.yaml'):
            file_name += '.yaml'
        full_path = self.save_dir_path / file_name
        
        if full_path.exists():
            raise ValueError(f"文件 '{file_name}' 已存在。请使用其他名称。")
        
        return full_path
        

class PresetValidator(BaseValidator):
    """一个用于预设名称校验的具体策略类"""
    def __init__(self, existing_names: list[str]):
        self.existing_names = existing_names

    def validate(self, text: str):
        """校验名称是否为空以及是否已存在"""
        if not text:
            raise ValueError("预设名称不能为空。")
        
        if text in self.existing_names:
            raise ValueError(f"名称 '{text}' 已存在。请使用其他名称。")
        
        return text

class ValidationInputDialog(QDialog):
    """
    一个通用的、可配置的、无边框的输入对话框。
    它使用一个可注入的 "validator" 对象来处理特定的校验逻辑。
    """
    def __init__(self, parent: QWidget, title: str, prompt: str, validator: BaseValidator):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self.setObjectName("Dialog")
        self.setWindowTitle(title) # 使用传入的标题
        self.setMinimumSize(300, 150)

        self.prompt_text = prompt       # 使用传入的提示
        self.validator = validator      # 存储校验器
        self.confirmed_value = None     # 存储校验成功后的值
        
        self._setup_ui()
        self._connect_signals()
        self.line_edit.setFocus()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        self.label = QLabel(self.prompt_text) # 使用 self.prompt_text
        self.line_edit = QLineEdit()
        
        self.error_label = QLabel()
        self.error_label.setObjectName("DescriptionLabel")
        self.error_label.setWordWrap(True)
        self.error_label.hide()

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

    def get_confirmed_value(self):
        """获取已确认并处理过的值"""
        return self.confirmed_value

    def accept(self):
        """覆盖 accept() 槽，以执行所有验证。"""
        text = self.line_edit.text().strip()
        
        try:
            # 调用 validator 对象
            self.confirmed_value = self.validator.validate(text)
            super().accept()
            
        except ValueError as e:
            # 校验失败，显示来自 validator 的错误信息
            self._show_error(str(e))
            return

    def _show_error(self, message: str):
        """在一个地方处理显示错误的UI逻辑"""
        self.line_edit.setProperty("state", "invalid")
        self.error_label.setText(message)
        self.error_label.show()
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)
    
    def _clear_error_state(self):
        """清除错误标签和红色边框。"""
        self.error_label.hide()
        self.line_edit.setProperty("state", "valid")
        self.line_edit.style().unpolish(self.line_edit)
        self.line_edit.style().polish(self.line_edit)