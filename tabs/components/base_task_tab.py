import sys
import locale
from PySide6.QtWidgets import QWidget, QPushButton
from PySide6.QtCore import Signal, QProcess
from constants import BASE_DIR

class BaseTaskTab(QWidget):
    """包含后台进程管理通用逻辑的标签页基类"""
    # log信号
    log_message_signal = Signal(str)
    # 任务启动时发出，并附带任务名
    task_started = Signal(str)
    # 任务结束时发出，并附带任务名
    task_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_process = QProcess(self)
        self.log_encoding = locale.getpreferredencoding()

        # 连接通用的信号
        self.task_process.readyReadStandardOutput.connect(
            lambda: self._process_output_and_log(is_error=False))
        self.task_process.readyReadStandardError.connect(
            lambda: self._process_output_and_log(is_error=True))
        self.task_process.finished.connect(self._on_task_finished)
        self.task_process.started.connect(self._on_task_started)

    def set_button_enabled(self, enabled: bool, tooltip: str = ""):
        """由外部调用，用于控制按钮的可用状态和提示文本"""
        button = self.get_start_button()
        button.setEnabled(enabled)

    def get_start_button(self) -> QPushButton:
        """子类需要返回其用于启动/停止的按钮实例"""
        raise NotImplementedError

    def get_script_module_path(self) -> str:
        """子类需要返回其要运行的脚本模块路径，例如 'scripts.auto_daily'"""
        raise NotImplementedError

    def get_script_args(self) -> list:
        """子类可以重写此方法以提供脚本参数"""
        return []

    # 通用逻辑方法

    def _on_task_toggle(self):
        """启动或中止后台脚本"""
        if self.task_process.state() == QProcess.ProcessState.Running:
            self.task_process.kill()
        else:
            self.task_process.setWorkingDirectory(str(BASE_DIR))
            module_path = self.get_script_module_path()
            args = self.get_script_args()
            if args is None: # 如果获取参数失败，则不启动
                return
            self.log_message_signal.emit(f"--- 准备启动脚本: {module_path} ---")
            self.task_process.start(sys.executable, ['-um', module_path, *args])
            
    def _on_task_started(self):
        """后台脚本启动时的通用UI更新"""
        button = self.get_start_button()
        task_name = button.objectName()
        button.setText(f"中止{task_name}")
        button.setProperty("running", True)
        button.style().polish(button)
        self.log_message_signal.emit(f"\n--- {task_name}任务已启动 ---\n")
        self.task_started.emit(task_name)

    def _on_task_finished(self):
        """后台脚本结束时的通用UI更新"""
        button = self.get_start_button()
        task_name = button.objectName()
        button.setText(f"启动{task_name}")
        button.setProperty("running", False)
        button.style().polish(button)
        self.log_message_signal.emit(f"\n--- {task_name}任务已结束 ---\n")
        self.task_finished.emit(task_name)
        
    def _process_output_and_log(self, is_error=False):
        """读取并记录后台脚本的输出"""
        if is_error:
            output_bytes = self.task_process.readAllStandardError()
        else:
            output_bytes = self.task_process.readAllStandardOutput()
        
        output_text = output_bytes.data().decode(self.log_encoding, errors='ignore').strip()
        if output_text:
            self.log_message_signal.emit(output_text)