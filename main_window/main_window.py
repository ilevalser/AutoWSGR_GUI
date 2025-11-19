import sys
from PySide6.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, 
                               QStackedWidget, QSystemTrayIcon, QMenu, QApplication)
from PySide6.QtCore import Qt, QPoint, QEvent, QTimer, QObject, QProcess, Slot
from PySide6.QtGui import QAction, QPixmap, QIcon
from main_window.title_bar import CustomTitleBar
from main_window.side_bar import SideBar
from utils.icon_utils import get_icon_path
from constants import LOGO_FILE, SETTINGS_FILE, UI_CONFIGS_FILE
from ruamel.yaml import YAML, YAMLError
# 各选项卡
from tabs.settings_tab import SettingsTab
from tabs.daily_tab import DailyTab
from tabs.logs_tab import LogTab
from tabs.decisive_battle_tab import DecisiveBattleTab
from tabs.event_tab import EventTab
from tabs.plan_editor_tab import PlanEditorTab

class MainWindow(QMainWindow):
    # 定义不同边缘和角落的常量
    GRIP_SIZE = 5  # 边缘缩放热区的像素宽度
    POS_TOP = 1
    POS_BOTTOM = 2
    POS_LEFT = 4
    POS_RIGHT = 8
    POS_TOP_LEFT = POS_TOP | POS_LEFT
    POS_TOP_RIGHT = POS_TOP | POS_RIGHT
    POS_BOTTOM_LEFT = POS_BOTTOM | POS_LEFT
    POS_BOTTOM_RIGHT = POS_BOTTOM | POS_RIGHT
    SNAP_THRESHOLD = 10 # 窗口贴靠的像素阈值

    def __init__(self):
        super().__init__()
        # 创建实例
        self.setObjectName("MainWindow")
        self.resize(1200, 850)
        self.setMinimumSize(800, 600) # 设置最小尺寸，防止窗口过小

        # 任务栏样式
        app_title = "AutoWSGR"
        logo_pixmap = QPixmap(str(LOGO_FILE))
        self.setWindowTitle(app_title)
        self.setWindowIcon(QIcon(logo_pixmap))

        # 基础设置
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint |
                            Qt.WindowType.WindowMinimizeButtonHint |
                            Qt.WindowType.WindowSystemMenuHint) # 无边框和任务栏最小化
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground) # 背景透明
        self.setMouseTracking(True) # 鼠标跟踪

        # 状态变量
        self.normal_geometry = None # 存储几何信息
        self._drag_pos = QPoint() # 窗口拖动变量
        self._drag_pos_at_press = QPoint()
        self._is_restoring_drag = False # 是否在拖拽
        self._is_resizing = False   # 是否在缩放
        self.current_resize_pos = 0 # 当前正在缩放的边缘/角落
        self._initial_geometry = None # 缩放时的初始几何信息

        # 任务管理
        self.task_tabs = {}  # 用于存储所有任务选项卡的字典
        self.running_task_tab = None # 追踪当前正在运行任务的Tab实例

        # 更新管理
        self._is_updating = False
        self._task_to_run_after_update = None
        self.update_process = QProcess(self)
        
        # 鼠标光标更新节流定时器
        self._cursor_update_timer = QTimer(self)
        self._cursor_update_timer.setInterval(50) # 50ms 更新一次
        self._cursor_update_timer.setSingleShot(True) # 单次触发
        self._cursor_update_timer.timeout.connect(self._perform_cursor_update) # 连接槽函数
        self._last_mouse_pos = QPoint() # 存储最后一次鼠标位置，供定时器使用

        # 主框架
        self.main_frame = QFrame(self)
        self.main_frame.setObjectName("MainFrame")
        self.main_frame.setMouseTracking(True)
        # 根布局
        root_layout = QVBoxLayout(self.main_frame)
        root_layout.setContentsMargins(self.GRIP_SIZE, self.GRIP_SIZE, self.GRIP_SIZE, self.GRIP_SIZE)
        root_layout.setSpacing(0)
        self.setCentralWidget(self.main_frame)

        # 将标题栏添加到根布局的顶部
        self.title_bar = CustomTitleBar(title=app_title, logo_pixmap=logo_pixmap, parent=self)
        root_layout.addWidget(self.title_bar)
        # 内容区布局，用于安放左侧侧边栏和右侧页面堆栈
        content_area = QWidget()
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        # 创建页面堆栈实例，用于切换不同的页面
        self.side_bar = SideBar()
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setObjectName("MainContentArea")
        # 将侧边栏和页面堆栈添加到水平布局中
        content_layout.addWidget(self.side_bar)
        content_layout.addWidget(self.stacked_widget, 1) # 设置拉伸因子为1，让页面堆栈占据所有剩余空间
        root_layout.addWidget(content_area) # 添加到根布局中

        # 初始化YAML管理器
        self.yaml_manager = YAML()
        self.yaml_manager.preserve_quotes = True
        self.yaml_manager.default_flow_style = False
        self.yaml_manager.indent(mapping=2, sequence=4, offset=2)
        self.yaml_manager.boolean_representation = ['False', 'True']
        self.settings_data = self._load_yaml_file(SETTINGS_FILE)
        self.configs_data = self._load_yaml_file(UI_CONFIGS_FILE)

        # 初始化页面实例
        self.log_tab = LogTab(self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)
        self.settings_tab = SettingsTab(self.settings_data, SETTINGS_FILE, self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)
        self.daily_tab = DailyTab(self.settings_data, SETTINGS_FILE, self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)
        self.task_tabs["日常"] = self.daily_tab
        self.decisive_battle_tab = DecisiveBattleTab(self.settings_data, SETTINGS_FILE, self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)
        self.task_tabs["决战"] = self.decisive_battle_tab
        self.event_tab = EventTab(self.settings_data, SETTINGS_FILE, self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)
        self.task_tabs["活动"] = self.event_tab
        self.plan_editor_tab = PlanEditorTab(self.configs_data, UI_CONFIGS_FILE, self.yaml_manager, self)

        # 填充内容
        self.populate_content()
        self.init_tray_icon() # 初始化托盘图标

        # 选择管理器
        self.log_tab.task_selector_combo.addItems(self.task_tabs.keys())

        # 更新
        self.update_process.readyReadStandardOutput.connect(self._log_update_output)
        self.update_process.readyReadStandardError.connect(self._log_update_output)
        self.update_process.finished.connect(self._on_update_finished)

        # 连接窗口框架信号
        self.title_bar.minimize_requested.connect(self.showMinimized)
        self.title_bar.maximize_restore_requested.connect(self.maximize_restore)
        self.title_bar.close_requested.connect(self.close)
        self.title_bar.double_click_requested.connect(self.maximize_restore)
        self.title_bar.minimize_to_tray_requested.connect(self.minimize_to_tray)
        self.side_bar.index_changed.connect(self._on_sidebar_index_changed)

        # 将所有任务标签页的启动按钮和日志页的快捷启停信号连接到统一的处理器
        for task_name, tab_instance in self.task_tabs.items():
            button = tab_instance.get_start_button()
            button.clicked.connect(lambda checked=False, name=task_name: self._handle_task_toggle_request(name))

        # 连接日志页面的快捷启停信号
        self.log_tab.quick_start_request.connect(self._handle_task_toggle_request)
        self.log_tab.quick_stop_request.connect(self._handle_task_toggle_request)

        # 连接所有子任务页面的 "started" 和 "finished" 信号
        for tab_instance in self.task_tabs.values():
            tab_instance.task_started.connect(self._on_any_task_started)
            tab_instance.task_finished.connect(self._on_any_task_finished)
            tab_instance.log_message_signal.connect(self.log_tab.append_log_message)

        # 连接刷新下拉框
        self.settings_tab.plan_root_changed.connect(self.daily_tab.refresh_task_plans)
        self.settings_tab.plan_root_changed.connect(self.event_tab.refresh_task_plans)
        
        # 启用追踪
        QApplication.instance().installEventFilter(self)

    @Slot(int)
    def _on_sidebar_index_changed(self, new_index):
        """处理侧边栏切换请求"""
        current_index = self.stacked_widget.currentIndex()
        # 如果点击的是当前已激活的按钮，则不执行任何操作
        if new_index == current_index:
            return
        # 检查当前页面是否是 PlanEditorTab
        current_widget = self.stacked_widget.widget(current_index)
        if current_widget == self.plan_editor_tab:
            # 如果是，检查它是否处于未保存状态
            if not self.plan_editor_tab.can_safely_close_tab():
                # 阻止切换
                # 告诉 SideBar 恢复到上一个索引，保持 UI 同步
                self.side_bar.on_button_clicked(current_index)
                return
        # 允许切换
        self.stacked_widget.setCurrentIndex(new_index)

    def populate_content(self):
        """根据PAGES_CONFIG创建选项卡"""
        pages_config = [{"id": "overview", "title": "总览", "icon": "overview",
                         "page_factory": lambda: self.log_tab},
                        {"id": "settings", "title": "全局设置", "icon": "settings",
                         "page_factory": lambda: self.settings_tab},
                        {"id": "daily", "title": "日常", "icon": "daily",
                         "page_factory": lambda: self.daily_tab},
                        {"id": "decisive_battle", "title": "决战", "icon": "decisive_battle",
                         "page_factory": lambda: self.decisive_battle_tab},
                        {"id": "event", "title": "活动", "icon": "event",
                         "page_factory": lambda: self.event_tab},
                        {"id": "plan_editor", "title": "编辑计划", "icon": "edit",
                         "page_factory": lambda: self.plan_editor_tab}]
        
        for config in pages_config:
            page = config["page_factory"]() # 调用工厂函数创建实例
            if isinstance(page, QLabel):
                page.setAlignment(Qt.AlignmentFlag.AlignCenter) # 统一设置对齐
            self.side_bar.add_button(icon_path=get_icon_path(config["icon"]),text=config["title"]) # 向侧边栏添加按钮
            self.stacked_widget.addWidget(page) # 向页面堆栈添加页面

        if pages_config:
            self.side_bar.set_initial_checked(0)

    def init_tray_icon(self):
        """初始化托盘图标"""
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.windowIcon())
        self.tray_icon.setToolTip("AutoWSGR 仍在后台运行")

        # 为托盘图标创建右键菜单
        tray_menu = QMenu(self)
        restore_action = QAction("打开主界面", self)
        restore_action.triggered.connect(self.showNormal)
        quit_action = QAction("退出应用", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(restore_action)
        tray_menu.addAction(quit_action)
        self.tray_icon.setContextMenu(tray_menu)

        # 连接托盘图标的点击事件
        self.tray_icon.activated.connect(self.on_tray_icon_activated)

    def minimize_to_tray(self):
        """隐藏主窗口，并显示系统托盘图标"""
        self.hide()
        self.tray_icon.show()

    def on_tray_icon_activated(self, reason):
        """处理托盘图标点击的槽函数"""
        # 如果是单击或双击，则恢复窗口
        if reason == QSystemTrayIcon.ActivationReason.Trigger or reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.showNormal()
            self.activateWindow()
            self.tray_icon.hide()

    def maximize_restore(self):
        """根据是否已保存正常窗口几何信息最大化和还原窗口"""
        if self.normal_geometry is not None:
            # 如果有已保存的几何信息，则代表窗口是最大化的，现在需要还原
            self.showNormal()
            self.setGeometry(self.normal_geometry)
            self.normal_geometry = None  # 清除标志，表明窗口已恢复正常
            
        else:
            # 如果没有保存的几何信息，则代表窗口是正常的，现在需要最大化
            self.normal_geometry = self.geometry()  # 保存当前几何信息
            self.showMaximized()

        # 根据 self.normal_geometry 是否有值来决定图标的最终状态
        self.title_bar.update_restore_icon(self.normal_geometry is not None)

    def changeEvent(self, event):
        """在窗口状态改变时，根据状态标志更新图标"""
        if event.type() == QEvent.Type.WindowStateChange:
            # 无论窗口状态如何变化图标的状态都只取决于 normal_geometry 标志
            self.title_bar.update_restore_icon(self.normal_geometry is not None)
            
        super().changeEvent(event)

    def mousePressEvent(self, event):
        """鼠标按下事件，用于启动窗口拖动或边缘缩放"""
        # 处理左键点击
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return
        
        # 检查是否在缩放区域
        self.current_resize_pos = self._get_resize_position(event.position().toPoint())
        if self.current_resize_pos != 0 and not self.isMaximized():
            self._is_resizing = True
            self._drag_pos = event.globalPosition().toPoint()
            self._initial_geometry = self.geometry()
            event.accept()
            return
        
        # 检查是否在标题栏区域
        if self.title_bar.geometry().contains(event.position().toPoint()):
            if self.normal_geometry is not None:
                # 只要窗口不是常规尺寸，拖动时就应该先恢复
                self._is_restoring_drag = True
                self._drag_pos_at_press = event.position().toPoint()
            else:
                # 普通拖动
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            return
        
        # 取消焦点
        focused_widget = QApplication.instance().focusWidget()
        if focused_widget:
            focused_widget.clearFocus()

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件，处理窗口拖动和边缘缩放"""
        # 缩放逻辑
        if self._is_resizing:
            initial_rect = self._initial_geometry
            delta = event.globalPosition().toPoint() - self._drag_pos

            new_left = initial_rect.left()
            new_top = initial_rect.top()
            new_width = initial_rect.width()
            new_height = initial_rect.height()

            if self.current_resize_pos & self.POS_TOP:
                new_top = initial_rect.top() + delta.y()
                new_height = initial_rect.height() - delta.y()
            if self.current_resize_pos & self.POS_BOTTOM:
                new_height = initial_rect.height() + delta.y()
            if self.current_resize_pos & self.POS_LEFT:
                new_left = initial_rect.left() + delta.x()
                new_width = initial_rect.width() - delta.x()
            if self.current_resize_pos & self.POS_RIGHT:
                new_width = initial_rect.width() + delta.x()

            if new_width < self.minimumWidth():
                new_width = self.minimumWidth()
                if self.current_resize_pos & self.POS_LEFT:
                    new_left = initial_rect.right() - new_width
            if new_height < self.minimumHeight():
                new_height = self.minimumHeight()
                if self.current_resize_pos & self.POS_TOP:
                    new_top = initial_rect.bottom() - new_height

            self.setGeometry(new_left, new_top, new_width, new_height)
            return
        
        # 最大化状态开始拖动的逻辑
        if self._is_restoring_drag and event.buttons() == Qt.MouseButton.LeftButton:
            # 计算窗口应该恢复到的位置
            screen_geom = self.screen().availableGeometry() # 获取当前屏幕的几何信息
            if screen_geom.width() == 0: # 安全检查，防止除以零
                return
            
            mouse_x_on_screen = event.globalPosition().x() - screen_geom.x() # 计算鼠标相对于当前屏幕的X坐标
            ratio = max(0.0, min(1.0, mouse_x_on_screen / screen_geom.width())) # 计算正确的比例
            # 先获取正常的几何信息，再还原
            normal_geom = self.normal_geometry
            self.maximize_restore()
            new_width = normal_geom.width()
            new_x_offset = int(new_width * ratio)

            # 移动到光标下方的正确位置
            self.move(event.globalPosition().toPoint().x() - new_x_offset, event.globalPosition().toPoint().y() - self._drag_pos_at_press.y())
            # 切换为普通拖动模式
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_restoring_drag = False
            return
        
        # 普通拖动逻辑
        if event.buttons() == Qt.MouseButton.LeftButton and not self._drag_pos.isNull():
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            return
        
        # 光标形状更新
        self._last_mouse_pos = event.position().toPoint() # 存储当前鼠标位置
        if not self._cursor_update_timer.isActive(): # 如果定时器未激活，则启动
            self._cursor_update_timer.start() # 启动节流定时器

        super().mouseMoveEvent(event)


    def _get_resize_position(self, pos: QPoint):
        """根据鼠标位置返回当前所在的边缘或角落"""
        x, y = pos.x(), pos.y()
        w, h = self.width(), self.height()

        top_edge = y < self.GRIP_SIZE
        bottom_edge = h - self.GRIP_SIZE <= y < h
        left_edge = x < self.GRIP_SIZE
        right_edge = w - self.GRIP_SIZE <= x < w

        position = 0
        if top_edge: position |= self.POS_TOP
        if bottom_edge: position |= self.POS_BOTTOM
        if left_edge: position |= self.POS_LEFT
        if right_edge: position |= self.POS_RIGHT
        return position

    def _perform_cursor_update(self):
        """实际执行光标形状更新的槽函数，由定时器调用"""
        pos = self._last_mouse_pos
        if not self.isMaximized():
            resize_pos = self._get_resize_position(pos)
            if resize_pos != 0:
                if resize_pos == self.POS_TOP or resize_pos == self.POS_BOTTOM:
                    self.setCursor(Qt.CursorShape.SizeVerCursor)
                elif resize_pos == self.POS_LEFT or resize_pos == self.POS_RIGHT:
                    self.setCursor(Qt.CursorShape.SizeHorCursor)
                elif resize_pos == self.POS_TOP_LEFT or resize_pos == self.POS_BOTTOM_RIGHT:
                    self.setCursor(Qt.CursorShape.SizeFDiagCursor)
                elif resize_pos == self.POS_TOP_RIGHT or resize_pos == self.POS_BOTTOM_LEFT:
                    self.setCursor(Qt.CursorShape.SizeBDiagCursor)
            else:
                self.unsetCursor()
        else:
            self.unsetCursor()

    def leaveEvent(self, event: QEvent):
        """当鼠标离开窗口时，无条件重置光标形状"""
        self.unsetCursor()
        self._cursor_update_timer.stop() # 鼠标离开时停止定时器

        super().leaveEvent(event)

    def mouseReleaseEvent(self, event):
        """鼠标释放事件，用于停止拖动/缩放，并检查是否需要执行窗口贴靠"""
        # 检查鼠标左键是否释放
        if event.button() != Qt.MouseButton.LeftButton:
            return super().mouseReleaseEvent(event)
        
        # 记录是否在拖拽窗口
        was_dragging = not self._drag_pos.isNull()

        # 重置所有状态标志
        self._drag_pos = QPoint()
        self._is_resizing = False
        self._is_restoring_drag = False
        self.current_resize_pos = 0
        self.unsetCursor()
        event.accept()
        
        # 如果不在拖拽直接返回
        if not was_dragging:
            return
        
        # 窗口贴靠逻辑
        screen = self.screen().availableGeometry()
        global_pos = event.globalPosition().toPoint()
        # 贴靠到顶部 -> 最大化
        if global_pos.y() <= screen.y() + self.SNAP_THRESHOLD:
            # 只有在非最大化状态下才执行
            if not self.isMaximized():
                self.maximize_restore()
            return
        # 贴靠到左侧 -> 左半屏
        if global_pos.x() <= screen.x() + self.SNAP_THRESHOLD:
            if self.normal_geometry is None:
                self.normal_geometry = self.geometry()
            self.setGeometry(screen.x(), screen.y(), screen.width() // 2, screen.height())
            self.title_bar.update_restore_icon(True)
            return
        # 贴靠到右侧 -> 右半屏
        if global_pos.x() >= (screen.x() + screen.width() - self.SNAP_THRESHOLD):
            if self.normal_geometry is None:
                self.normal_geometry = self.geometry()
            self.setGeometry(screen.x() + screen.width() // 2, screen.y(), screen.width() // 2, screen.height())
            self.title_bar.update_restore_icon(True)
            return
        
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        """确保在关闭主窗口时，托盘图标也会被正确处理"""
        self.tray_icon.hide()
        super().closeEvent(event)

    def _load_yaml_file(self, file_path):
        """加载单个YAML文件并返回其数据"""
        config_data = {} # 默认返回空字典
        try:
            if file_path.exists():
                with open(file_path, 'r', encoding='utf-8') as f:
                    config_data = self.yaml_manager.load(f)
            else:
                print(f"提示: 配置文件 {file_path} 不存在，将使用默认值。")
        except YAMLError as e:
            print(f"错误: 加载 YAML 配置文件 {file_path} 时发生格式错误: {e}")
        except Exception as e:
            print(f"错误: 处理配置文件 {file_path} 时发生未知错误: {e}")
        return config_data

    def eventFilter(self, watched: 'QObject', event: 'QEvent') -> bool:
        """事件过滤器用于全局捕获鼠标移动事件"""
        if event.type() == QEvent.Type.MouseMove:
            # 检查鼠标是否在当前窗口的几何范围内
            if self.geometry().contains(event.globalPosition().toPoint()):
                # 将全局坐标转换为相对于本窗口的局部坐标
                local_pos = self.mapFromGlobal(event.globalPosition().toPoint())
                # 调用光标更新逻辑
                self._last_mouse_pos = local_pos
                if not self._cursor_update_timer.isActive():
                    self._cursor_update_timer.start()

        return super().eventFilter(watched, event)
    

# =================== 进程管理 ====================
    def _set_all_task_buttons_enabled(self, enabled: bool, tooltip: str = ""):
        """统一启用或禁用所有任务相关的按钮"""
        for tab in self.task_tabs.values():
            tab.set_button_enabled(enabled, tooltip)
        self.log_tab.set_quick_actions_enabled(enabled, tooltip)

    @Slot()
    def _log_update_output(self):
        """通用日志记录槽，用于捕获更新进程的输出"""
        stdout = self.update_process.readAllStandardOutput().data().decode(errors='ignore').strip()
        stderr = self.update_process.readAllStandardError().data().decode(errors='ignore').strip()
        if stdout:
            self.log_tab.append_log_message(stdout)
        if stderr:
            self.log_tab.append_log_message(stderr)

    @Slot(int, QProcess.ExitStatus)
    def _on_update_finished(self, exit_code, exit_status):
        """异步更新进程结束时调用的槽"""
        self._log_update_output()
        self.log_tab.append_log_message("--- 更新检查完成 ---\n")

        self._is_updating = False
        self._on_any_task_finished("")
        # 如果有一个等待执行的任务，现在就启动它
        if self._task_to_run_after_update:
            task_name = self._task_to_run_after_update
            self._task_to_run_after_update = None
            self._handle_task_toggle_request(task_name, force_run=True)
    
    @Slot(str)
    @Slot()
    def _handle_task_toggle_request(self, task_name: str = "", force_run: bool = False):
        """统一处理所有启动/停止请求。"""
        if self._is_updating:
            self.log_tab.append_log_message("提示：正在检查更新，请稍候...")
            return
        
        if self.running_task_tab:
            self.running_task_tab._on_task_toggle()
            return

        if task_name:
            # 只有在非强制模式下才检查更新
            if self.configs_data.get('check_update_gui', False) and not force_run:
                self._is_updating = True
                self._task_to_run_after_update = task_name

                self.log_tab.append_log_message("------------ 正在从清华镜像源检查更新 ------------")
                self._set_all_task_buttons_enabled(False, "正在检查更新...")
                
                command_args = [
                    "-m", "pip", "install", "--upgrade", "autowsgr",
                    "-i", "https://pypi.tuna.tsinghua.edu.cn/simple"
                ]
                self.update_process.start(sys.executable, command_args)
            else:
                # 直接启动任务（或在强制模式下启动）
                target_tab = self.task_tabs.get(task_name)
                if target_tab:
                    target_tab._on_task_toggle()

    @Slot(str)
    def _on_any_task_started(self, running_task_name: str):
        """当任何一个任务启动时，此槽函数被调用，负责更新全局UI状态"""
        self.running_task_tab = self.task_tabs.get(running_task_name)
        if not self.running_task_tab: return

        self.title_bar.start_task_animation(running_task_name)
        self.log_tab.update_for_task_state(True, running_task_name)

        for task_name, tab_instance in self.task_tabs.items():
            if tab_instance is not self.running_task_tab:
                tab_instance.set_button_enabled(False)

    @Slot(str)
    def _on_any_task_finished(self, finished_task_name: str):
        """当任何一个任务结束时，此槽函数被调用，负责重置全局UI状态"""
        self.running_task_tab = None

        self.title_bar.stop_task_animation()
        self.log_tab.update_for_task_state(False)

        self._set_all_task_buttons_enabled(True)