import os
import sys
from datetime import datetime

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QSystemTrayIcon, QMenu, QAction, QWidget, QLabel, QVBoxLayout
from PyQt5.QtGui import QIcon, QPixmap, QFont

from notification import NotificationWindow
from config import load_config
import config
from workthread import WorkThread, auto_summary
from window_ask_ai_gui_qt_v2 import ChatApp
from selectthecontent_qt import SelectTheContentWidget
from chatcommand import ChatCommandTool


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class MainWindow(ChatApp):      # 主窗口
    def __init__(self):
        self.select_the_content_widget = None
        self.pause_trigger_flag = False
        now = datetime.now()
        formatted_date = now.strftime("%y年%#m月%#d日")
        formatted_id = now.strftime("%y%m%d") + "000000"
        self.window_id = f"{formatted_id}:000:000"
        print("今日总窗口id", self.window_id)
        # 打开主界面
        super().__init__(parent="daywindow", window_id=self.window_id, window_x=0, window_y=0,
                                select=None, question="今日日期："+formatted_date, context="none", window_width=1300, window_height=1000)

        icon_path = resource_path("icon/Depth_8,_Frame_0explore-角标.png")

        # 创建系统托盘图标
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon(icon_path))  # 设置图标

        # 创建托盘菜单
        tray_menu = QMenu()
        tray_menu.setStyleSheet("QMenu {background-color: #222; color: white;}")

        show_action = QAction("展示主界面", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)

        hide_action = QAction("隐藏主界面", self)
        hide_action.triggered.connect(self.hide)
        tray_menu.addAction(hide_action)

        pause_action = QAction("暂停触发", self)
        pause_action.triggered.connect(self.pause_trigger)
        tray_menu.addAction(pause_action)

        start_action = QAction("开始触发", self)
        start_action.triggered.connect(self.start_trigger)
        tray_menu.addAction(start_action)


        exit_action = QAction("退出", self)
        exit_action.triggered.connect(self.exit_app)
        tray_menu.addAction(exit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.on_tray_icon_activated)
        self.tray_icon.show()

        print("主窗口初始化完成")

    def start_chat(self):
        # 初始化聊天记录
        if self.is_restored:
            print("restored,开始恢复窗口信息")
            self.load_chat_history()
        else:
            print("not restored,开始初始化窗口信息")
            self.save_window()  # 保存窗口信息,否则后续以此新建的父窗口都无法保存并更新父窗口的子窗口信息。
        # 总结线程
            # //////////线程总结昨日，同步显示总结今天
        self.worker_summary = WorkThread(auto_summary)
        self.worker_summary.update_signal.connect(lambda x : NotificationWindow.show_success(x))
        print("关闭窗口，启动总结线程,time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        self.worker_summary.start()

    def start_listening(self):
        self.select_the_content_widget = SelectTheContentWidget()

    def send_message(self):
        user_message = self.input_field.toPlainText()
        if user_message:
            # 消息首个非空格字符是 '#'，则提取标签和内容
            if user_message.lstrip().startswith('#'):
                super().send_message()

            elif user_message.lstrip().startswith('~'):
                tool = ChatCommandTool()
                self.input_field.clear()
                self.add_message('user', user_message, align_right=True)
                QTimer.singleShot(50, self.scroll_to_bottom)
                response = tool.parse_command(user_message)
                self.add_message('system', response, align_right=False)
                QTimer.singleShot(50, self.scroll_to_bottom)

            else:
                # self.sleep1()
                print(f"send_message: user: {user_message}")
                self.add_message('user', user_message, align_right=True)     # 对话已保存到context中
                self.input_field.clear()
                QTimer.singleShot(50, self.scroll_to_bottom)

                self.call_stream_llm_and_update_ui(self.select, self.context, self.question, main_window=True)
    def pause_trigger(self):
        self.pause_trigger_flag = True
        NotificationWindow.show_notification("暂停划词功能", "Trigger paused")
        self.select_the_content_widget.stop_listening("mouse")

    def start_trigger(self):
        self.pause_trigger_flag = False
        NotificationWindow.show_notification("启动划词功能", "Trigger started")
        self.select_the_content_widget.start_listening("mouse")

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.save_window()
        NotificationWindow.show_notification("最小化到托盘", "Application was minimized to tray")

    def exit_app(self):
        self.save_window()
        print("退出触发，保存窗口信息")
        QApplication.instance().quit()
    def on_tray_icon_activated(self, reason):      # 双击托盘图标打开或者关闭
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()

    # def show_notification(self, title, message):
    #     # 获取当前脚本所在的目录
    #     current_dir = os.path.dirname(__file__)
    #     # 构建相对路径
    #     icon_path = os.path.join(current_dir, "../src/icon/Depth_8,_Frame_0explore-角标.png")
    #
    #     self.notification = NotificationWindow(title, message, icon_path)
    #     self.notification.show()

if __name__ == "__main__":

    load_config()
    app = QApplication(sys.argv)
    window = MainWindow()
    window.start_chat()
    window.show()
    window.start_listening()
    # print("config.API_KEY", config.API_KEY)
    if config.API_KEY == 'default_api_key' or config.API_KEY == 'your_api_key_here':
        print("请在配置文件中填写API_KEY")
        window.add_message("system", "请在配置文件config.txt中填写API_KEY后使用，如果已经保存，忽略本条消息", align_right=True)
    sys.exit(app.exec_())
