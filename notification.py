import os
import sys

from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import QTimer, Qt


class NotificationWindow(QWidget):    # 自定义通知窗口,用于发通知
    current_notification = None

    def __init__(self, title, message, icon_path):
        super().__init__()
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        # self.setStyleSheet("background-color: rgba(30, 30, 30, 200); border-radius: 10px;")

        # 创建一个容器小部件
        container = QWidget()
        container.setStyleSheet("background-color: rgba(30, 30, 30, 200); border-radius: 10px;")

        layout = QVBoxLayout(container)

        icon_label = QLabel()
        pixmap = QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pixmap)

        # icon_label.setFixedSize(64, 64)
        icon_label.setStyleSheet("margin-top: 10px;background-color: transparent;")
        icon_label.setAlignment(Qt.AlignCenter)

        title_label = QLabel(title)
        title_label.setFont(QFont("Arial", 14, QFont.Bold))
        title_label.setStyleSheet("color: white;background-color: transparent;")
        title_label.setAlignment(Qt.AlignCenter)

        # message_label = QLabel(message)
        # message_label.setFont(QFont("Arial", 12))
        # message_label.setStyleSheet("color: white;")
        # message_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        # layout.addWidget(message_label)

        main_layout = QVBoxLayout(self)
        main_layout.addWidget(container)
        self.setLayout(main_layout)
        self.adjustSize()   # 调整窗口大小
        # 自动关闭窗口
        QTimer.singleShot(2000, self.close)

    @classmethod
    def show_notification(cls, title, message):
        try :
            # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
            base_path = sys._MEIPASS
        except Exception :
            base_path = os.path.abspath(".")
        relative_path = "icon/Depth_8,_Frame_0explore-角标.png"
        icon_path = os.path.join(base_path, relative_path)
        # icon_path = "icon/Depth_8,_Frame_0explore-角标.png"
        if cls.current_notification is not None :
            cls.current_notification.close()
            cls.current_notification = None
            # 创建新的通知实例并显示
        cls.current_notification = NotificationWindow(title, message, icon_path)
        cls.current_notification.show()

    @classmethod
    def show_success(cls, doc_id):
        if doc_id:
            cls.show_notification("保存成功,id:"+str(doc_id), "Trigger paused")
        else:
            cls.show_notification("保存失败", "Trigger paused")


