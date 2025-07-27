# 侧边栏基础功能实现
from PySide6.QtWidgets import QVBoxLayout, QLabel, QWidget, QGraphicsOpacityEffect
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, Signal, QParallelAnimationGroup, QEvent
from utils.icon_utils import create_colored_pixmap

class SideBarButton(QWidget):
    clicked = Signal()
    def __init__(self, icon_path: str, text: str, parent: QWidget = None):
        super().__init__(parent)
        self._text = text
        # 状态标记
        self._is_active = False
        self._is_hover = False
        # 设置大小
        self.collapsed_height = 70
        self.expanded_height = 80
        self.icon_size_normal = QSize(32, 32)
        self.icon_size_hover = QSize(38, 38)
        # 设置颜色
        self.normal_color = "#BEBEBE"
        self.active_color = "#FFFFFF"
        self.indicator_color = QColor("#007ACC")
        # 预先创建好样式和图标
        self.style_text_normal = f"color: {self.normal_color}; font-weight: bold;"
        self.style_text_active = f"color: {self.active_color}; font-weight: bold;"
        self.normal_pixmap = create_colored_pixmap(icon_path, self.normal_color, self.icon_size_normal)
        self.hover_pixmap = create_colored_pixmap(icon_path, self.active_color, self.icon_size_hover)
        self.active_pixmap = create_colored_pixmap(icon_path, self.active_color, self.icon_size_hover)
        # 布局设置
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 10, 0, 0)
        self.main_layout.setSpacing(5)
        self.icon_label = QLabel()
        self.text_label = QLabel(self._text)
        self.text_label.setObjectName("SideBarButtonText")
        # 初始样式设置
        self.text_label.setStyleSheet(self.style_text_normal)
        self.main_layout.addWidget(self.icon_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addWidget(self.text_label, 0, Qt.AlignmentFlag.AlignHCenter)
        self.main_layout.addStretch()
        # 创建文字透明度效果和动画
        self.opacity_effect = QGraphicsOpacityEffect(self.text_label)
        self.text_label.setGraphicsEffect(self.opacity_effect)
        # 创建高度动画和透明度动画
        self.height_animation = QPropertyAnimation(self, b"maximumHeight")
        self.height_animation.setDuration(200)
        self.height_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.fade_animation = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_animation.setDuration(150) # 文字渐隐稍快一些
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        # 并行动画组同步两个动画
        self.animation_group = QParallelAnimationGroup(self)
        self.animation_group.addAnimation(self.height_animation)
        self.animation_group.addAnimation(self.fade_animation)
        self.animation_group.finished.connect(self._on_animation_finished)
        # 初始化状态
        self.text_label.hide()
        self.icon_label.setPixmap(self.normal_pixmap)
        self.setMinimumHeight(self.collapsed_height)
        self.setMaximumHeight(self.collapsed_height)
        self.setFixedWidth(80)

    def set_active(self, is_active: bool):
        """设置按钮的激活状态，由外部调用"""
        self.animation_group.stop()
        self._is_active = is_active
        if is_active:
            # 激活时立刻变为最终状态
            self.icon_label.setPixmap(self.active_pixmap)
            self.text_label.setStyleSheet(self.style_text_active)
            self.opacity_effect.setOpacity(1.0)
            self.text_label.show()
            self.setMaximumHeight(self.expanded_height)
        else:
            # 取消激活时执行收起和渐隐动画
            if not self._is_hover:
                self._animate_to_normal()
        self.update() # 触发paintEvent重绘指示器

    def enterEvent(self, event: QEvent):
        """鼠标进入事件"""
        self._is_hover = True
        if self._is_active:
            return
        self.animation_group.stop()
        # 立刻显示白色文字和悬停图标
        self.icon_label.setPixmap(self.hover_pixmap)
        self.text_label.setStyleSheet(self.style_text_active)
        self.opacity_effect.setOpacity(1.0)
        self.text_label.show()
        # 只执行高度扩展动画
        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(self.expanded_height)
        self.height_animation.start()
        super().enterEvent(event)

    def leaveEvent(self, event: QEvent):
        """鼠标离开事件"""
        self._is_hover = False
        if self._is_active:
            return  
        self._animate_to_normal()
        super().leaveEvent(event)

    def _animate_to_normal(self):
        """执行到 Normal 状态的转换"""
        self.animation_group.stop()
        # 动画开始前立刻将文字和图标颜色变为 normal
        self.text_label.setStyleSheet(self.style_text_normal)
        self.icon_label.setPixmap(self.normal_pixmap)
        # 设置高度收缩动画
        self.height_animation.setStartValue(self.height())
        self.height_animation.setEndValue(self.collapsed_height)
        # 设置文字渐隐动画
        self.fade_animation.setStartValue(self.opacity_effect.opacity())
        self.fade_animation.setEndValue(0.0)
        # 启动并行动画组
        self.animation_group.start()
        
    def _on_animation_finished(self):
        """动画组完成后的回调"""
        # 只有在完全收起的状态下才隐藏文字标签
        if not self._is_active and not self._is_hover:
            self.text_label.hide()

    def mouseReleaseEvent(self, event):
        """捕获鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mouseReleaseEvent(event)

    def paintEvent(self, event):
        """绘制蓝条"""
        if self._is_active:
            painter = QPainter(self)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(self.indicator_color)
            painter.drawRect(0, 0, 3, self.height())