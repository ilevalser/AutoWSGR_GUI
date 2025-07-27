import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont
from main_window.main_window import MainWindow
from constants import STYLE_FILE

if __name__ == '__main__':
    app = QApplication(sys.argv)
    # 从外部文件加载并应用样式表
    font = QFont()
    font.setStyleStrategy(QFont.StyleStrategy.NoSubpixelAntialias)
    app.setFont(font)
    try:
        with open(STYLE_FILE, 'r', encoding='utf-8') as f:
            style_sheet = f.read()
            app.setStyleSheet(style_sheet)
    except FileNotFoundError:
        # 如果找不到样式文件，打印警告，程序仍可运行
        print("警告: 'style.qss' 文件未找到，将使用默认样式运行。")

    window = MainWindow()
    window.show()
    sys.exit(app.exec())