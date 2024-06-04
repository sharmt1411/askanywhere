# 这个文件是用来实现鼠标点击选中内容并复制到剪贴板的功能的。
import os
import time
import sys     # 系统模块,识别操作系统类型
from datetime import datetime

from PyQt5.QtWidgets import (QApplication,  QHBoxLayout, QWidget, QPushButton, QTextEdit, )
from PyQt5.QtGui import QIcon, QPixmap
from PyQt5.QtCore import QSize, Qt, QTimer

import logging  # 日志模块
from pynput import mouse     # 鼠标监听模块
from pynput import keyboard  # 键盘监听模块
import pyperclip    # 剪贴板模块
import pyautogui    # 自动化鼠标操作模块

from notification import NotificationWindow

from workthread import WorkThread, save_note
from window_ask_ai_gui_qt_v2 import ChatApp, AutoResizingTextEdit  # 自定义的文本编辑框

# 设定一个按键作为触发的按键，这里我们使用'x'键
TRIGGER_KEY = keyboard.Key.alt_l  # 触发的按键
SCALE_FACTOR = 1  # 对于150%缩放
CLICK_INTERVAL_THRESHOLD = 0.2  # 鼠标同一个按键事件点击间隔阈值，判断是否是单击还是选取
DOUBLE_CLICK_THRESHOLD = 0.25  # 定义双击的时间阈值（例如，0.25秒内的两次点击被视为双击）
# 记录上一次点击的时间和按钮
logging.basicConfig(level=logging.INFO, filename='app_paste.log', filemode='a',
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class SelectTheContentWidget(QWidget):

    def __init__(self):
        super().__init__()
        self.keyboard_listener = None
        self.mouse_listener = None
        self.window_x, self.window_y = 100, 100
        self.click_interval_last_time = 0
        self.double_click_last_time = 0
        self.last_alt_press_time = 0
        self.current_focus = None
        self.is_simulate_click = False      # 监测是否模拟点击
        # self.oldPos = self.pos()
        self.selected_text = ""
        self.context_text = ""
        self.clipboard_parent = "none"
        self.chatapp_windows = []
        self.ask_text_widget = None
        self._create_select_the_content_window()  # 创建按钮窗口
        self.start_listener()  # 启动监听器
        print("select_the_content全部初始化完成")

    def on_click(self, x, y, button, pressed):
        # print("鼠标点击,时间", x, y, button, pressed, time.time())
        global SCALE_FACTOR
        if button == mouse.Button.left:  # 左键点击、双击、选中、拖动
            if pressed:  # 松开后判断是否是单击还是双击
                # print("鼠标点击，更新点击位置", x, y,time.time())
                self.click_interval_last_time = time.time()  # 更新点击开始时间
            if not pressed:  # 当鼠标按钮释放时
                # 计算鼠标点击时间间隔
                self._handle_left_click(x, y)  # 处理鼠标点击事件
        else:  # 右键点击、双击
            self.hide()               # 隐藏按钮窗口
            # print("点击取消按钮")

    def _handle_left_click(self, x, y):
        if self.is_simulate_click:  # 忽略模拟点击
            return
        # 计算鼠标点击时间间隔
        current_time = time.time()
        click_interval = current_time - self.click_interval_last_time

        if click_interval > CLICK_INTERVAL_THRESHOLD:  # 鼠标点击持续间隔大于0.2秒，认为是选取
            self.update_current_focus()
            print("鼠标选中，更新按钮位置", x, y, time.time())
            self._show_send_button_window(x, y)
        else:  # 鼠标点击间隔小于0.2秒，认为是单击或者双击
            current_focus = QApplication.focusWidget()
            # 如果焦点不是按钮窗口，则认为是单击
            if current_focus is not self.ask_text_widget and current_focus is not self.send_button:
                self.hide()  # 隐藏按钮窗口  单击或者双击后隐藏按钮窗口
            # 双击显示窗口
            # double_click_interval = current_time - self.double_click_last_time
            # self.double_click_last_time = current_time  # 记录这一次松开的时间    两次按下或者松开的时间间隔小于0.25秒，认为是双击
            # if double_click_interval < DOUBLE_CLICK_THRESHOLD:  # 左键双击
                # self.update_current_focus()
                # print("self.ask_text_widget-handle_left_click2", self.ask_text_widget)
                # print("鼠标双击，更新按钮位置", x, y,  time.time())
                # self._show_send_button_window(x, y)    暂停双击触发，等待双击优化

    def on_key_press(self, key):
        # print("按下按键", key)
        if key == TRIGGER_KEY:
            print("按下触发键", key, self.isVisible())
            if self.isVisible():  # 如果按下触发键,如果当前copy按钮是可见的，执行点击操作
                # self.copy_text_and_hide()  # 焦点问题，输入文字后按下alt，窗口消失，原焦点也失焦，无法复制，但是点击按钮可以
                # self.send_button.click()  # 焦点问题，输入文字后按下alt，窗口消失，原焦点也失焦，无法复制，但是点击按钮可以
                self.is_simulate_click = True
                pyautogui.click(self.window_x+30, self.window_y+30)
                print("按下触发键，模拟点击", key)
                self.is_simulate_click = False
            else:       # 如果当前copy按钮不可见，显示按钮窗口
                current_time = time.time()
                print("按下触发键,不可见", key)
                if (current_time - self.last_alt_press_time) <= 0.5:
                    print("Alt key 双击，调出窗口")
                    self._show_send_button_window(x=500, y=500)
                self.last_alt_press_time = current_time

    # Call the base class method to handle other ke

    def _show_send_button_window(self, x, y):
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)  # 设置窗口始终置顶

        # 显示新询问窗口之前，判断点击位置是否在自己应用的范围内，如果在，更新上下文内容，本身已经具备选中或者双击条件了
        current_focus_widget = self.current_focus
        print("准备显示悬浮条，当前焦点", current_focus_widget)
        if isinstance(self.current_focus, AutoResizingTextEdit):
            self.selected_text = self.current_focus.textCursor().selectedText()
            self.context_text = self.current_focus.toPlainText()
            while current_focus_widget.parent():
                current_focus_widget = current_focus_widget.parent()
            self.clipboard_parent = current_focus_widget.window_id
            # print(f"Selected text: {self.selected_text}")
            # print(f"Full text: {self.context_text}")
            print(f"父窗口 id: {current_focus_widget.window_id}")
        else:
            print("选择非应用内文本，无父窗口id")
            self.selected_text = ""
            self.context_text = ""
            self.clipboard_parent = "none"

        # x, y是希望按钮出现的位置
        adjusted_x = int(x / SCALE_FACTOR)
        adjusted_y = int(y / SCALE_FACTOR)
        # 获取桌面分辨率
        screen = QApplication.primaryScreen()
        screen_geometry = screen.geometry()
        screen_width = screen_geometry.width()
        screen_height = screen_geometry.height()

        # 窗口大小
        window_width = 700
        window_height = 1100

        # 计算窗口的位置，确保不会超出桌面的右下角
        x_position = min(screen_width - window_width, adjusted_x)
        y_position = min(screen_height - window_height, adjusted_y)
        # print("桌面分辨率", screen_width, screen_height, "窗口位置", x_position, y_position, "窗口大小", window_width, window_height)

        self.window_x, self.window_y = x_position, y_position
        # 更新按钮位置
        # print("准备更新按钮位置", x_position, y_position, time.time())
        self.move(self.window_x, self.window_y)  #
        # print("已经更新按钮位置", self.window_x, self.window_y, time.time())
        # 显示按钮窗口
        # self.show()
        QTimer.singleShot(0, self.show)
        print("显示悬浮条", self.window_x, self.window_y, time.time())
        # print("当前焦点", self.current_focus)
        # if self.current_focus is not None:
        #     self.ask_text_widget.setFocus()   # 输入框获得焦点
        #     print("输入框获得焦点", self.window_x, self.window_y, time.time())
        # else:
        # self.is_simulate_click = True
        # pyautogui.click(x_position + 100, y_position+30)  # 点击一下，光标定位到文本框
        # self.is_simulate_click = False
        # print("模拟点击到输入框", x_position, y_position)
        # print("聚焦按钮窗口", self.window_x, self.window_y, time.time())

    def copy_text_and_hide(self):   # 按钮绑定点击后触发复制查询并隐藏按钮窗口
        # parent = "root"
        print("触发复制按钮")
        self.hide()
        if self.selected_text == "" and self.context_text == "":    # 双击选中更新focus,非应用内选中全部刷为空
            print("没有聚焦应用文本窗口，准备process_clipboard")
            QTimer.singleShot(50, self.process_clipboard)
        elif self.selected_text != "" or self.context_text != "":
            print("有聚焦应用文本窗口，无需复制")
            QTimer.singleShot(0, lambda: self.ask_ai(has_focus=True))

    def process_clipboard(self):
        # 检查剪贴板是否有内容
        clipboard_select = pyperclip.paste()
        if clipboard_select:
            logger.info(clipboard_select)
            print("之前内容是:", clipboard_select)
            pyperclip.copy('')  # 复制到剪贴板
        # 从剪贴板复制文本
        if sys.platform.startswith('darwin'):
            pyautogui.hotkey('command', 'c')
        else:
            pyautogui.hotkey('ctrl', 'c')  # 或者 pyautogui.hotkey('command', 'c')，取决于操作系统
            print("windows-ctrl+c,模拟复制，paste:", pyperclip.paste())
            # print("windows-ctrl+c,模拟复制2,paste:", pyperclip.paste(), "2")
        # if pyperclip.paste() == "":
        #     print("复制失败")
        #     return
        # else:
        #     clipboard_select = pyperclip.paste()
        QTimer.singleShot(100, lambda: self.ask_ai(has_focus=False))

    def ask_ai(self, has_focus=False):
        # 调用ai
        if not has_focus:
            clipboard_select = pyperclip.paste()
            clipboard_question = self.ask_text_widget.toPlainText()  # 获取输入框内容
            clipboard_context = ""  #

            now = datetime.now()
            formatted_date = now.strftime("%y年%#m月%#d日")
            formatted_id = now.strftime("%y%m%d") + "000000"
            clipboard_parent = f"{formatted_id}:000:000"
            # print("无焦点调用悬浮条，打开一级窗口")
            text = "无焦点调用悬浮条，打开一级窗口，你复制了: " + clipboard_select + "\n" + "你的意图是：" + clipboard_question
            if clipboard_select == "" and clipboard_question == "":
                print("没有内容，无选择，无意图，停止退出")
                return
        else:
            clipboard_select = self.selected_text
            clipboard_question = self.ask_text_widget.toPlainText()  # 获取输入框内容
            clipboard_context = self.context_text
            clipboard_parent = self.clipboard_parent  # 父窗口id
            # print("有焦点调用悬浮条")
            text = ("有焦点调用悬浮条,你选中了: " + clipboard_select + "\n" + "你的意图是：" + clipboard_question+"。\n" +
                    "parent_window_id:"+clipboard_parent)
            # "上下文内容是："+clipboard_context+
        print(text)  # 这里可以替换为其他处理剪贴板内容的逻辑

        if clipboard_question.lstrip().startswith('#'):   # 调用笔记保存功能/
            self.worker = WorkThread(save_note, clipboard_question, clipboard_select)
            self.worker.update_signal.connect(lambda x: NotificationWindow.show_success(x))
            print("开始保存笔记线程start")
            self.worker.start()
            print("开始保存笔记线程end")

        else:
            if clipboard_select is None and clipboard_question == "" and clipboard_context is None:
                print("没有内容，退出")
            else:
                # 调用ai//////////////////////////////////////////////////////////
                # print("创建chatapp聊天窗口，parent_window_id:", clipboard_parent, "window_x:", self.window_x, "window_y:", self.window_y,
                #       "select:", clipboard_select, "question:", clipboard_question, "context:", clipboard_context)
                print("创建chatapp聊天窗口，parent_window_id:", clipboard_parent, "window_x:", self.window_x,
                      "window_y:", self.window_y)
                chat_window = ChatApp(parent=clipboard_parent, window_id=0, window_x=self.window_x, window_y=self.window_y,
                                      select=clipboard_select, question=clipboard_question, context=clipboard_context)
                chat_window.closed_signal.connect(self.remove_chat_window)
                # print("创建对话窗口完毕")
                chat_window.show()
                print("展示对话窗口")
                self.chatapp_windows.append(chat_window)    # 防止窗口引用消失后自动关闭
                # print("添加对话窗口到列表")
                chat_window.start_chat()
        # QTimer.singleShot(5000, self.ask_text_widget.clear())
        self.ask_text_widget.clear()  # 清空输入框内容
        # QTimer.singleShot(1000,lambda: print("等待1s"))
        # print("清空输入框内容,调用结束")
        # 调用ask_ai_gui

    def _create_select_the_content_window(self):
        # 创建一个无边框的窗口
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)  # 无边框窗口置顶
        self.setGeometry(100, 100, 550, 50)  # 设置窗口的位置和大小
        self.setStyleSheet("QWidget { background-color: #F5F5F5; border-radius: 20px;border: 2px solid #D1D1D1; }")
        self.setAttribute(Qt.WA_TranslucentBackground)  # 设置窗口背景透明
        # 创建布局
        layout = QHBoxLayout()
        # 创建一个按钮
        send_button = QPushButton()
        send_button.setIcon(QIcon(QPixmap(resource_path("icon/Depth_8,_Frame_0chat.png"))))
        send_button.setFixedHeight(50)
        send_button.setFixedWidth(50)
        send_button.clicked.connect(self.copy_text_and_hide)
        send_button.setStyleSheet("QPushButton { background-color: #F5F5F5; border-radius: 10px; "
                                  "border: none; padding: 4px; text-align: middle; }"
                                  "QPushButton:hover { background-color: #E1E1E1; }")
        send_button.setIconSize(QSize(48, 48))  # Adjust icon size
        self.send_button = send_button
        # self.ask_text_widget = QLineEdit()
        self.ask_text_widget = ExpandingTextEdit(self)

        layout.addWidget(send_button)
        layout.addWidget(self.ask_text_widget)
        self.setLayout(layout)
        # QTimer.singleShot(0, self.show)
        # self.show()
        self.hide()
        print("crate_select_the_content_window 初始化完成")

    def start_listener(self):
        # 监听鼠标事件
        self.mouse_listener = mouse.Listener(on_click=self.on_click)
        self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
        self.mouse_listener.start()
        self.keyboard_listener.start()

    def stop_listening(self, chose):
        if chose == "mouse" and self.mouse_listener is not None:
            self.mouse_listener.stop()
        elif chose == "keyboard" and self.keyboard_listener is not None:
            self.keyboard_listener.stop()

    def start_listening(self, chose):
        print("开始监听", chose)
        print(self.mouse_listener, self.keyboard_listener)
        if chose == "mouse" and (self.mouse_listener is None or not self.mouse_listener.is_alive()):
            self.mouse_listener = mouse.Listener(on_click=self.on_click)
            self.mouse_listener.start()
            print("开始监听鼠标事件")
        elif chose == "keyboard" and (self.keyboard_listener is None or not self.keyboard_listener.is_alive()):
            self.keyboard_listener = keyboard.Listener(on_press=self.on_key_press)
            self.keyboard_listener.start()

    def update_current_focus(self):   # 选中文本时更新当前focus
        current_focus = QApplication.focusWidget()
        print(f"更新Current focus: {current_focus}")
        self.current_focus = current_focus  # 主窗口循环

    def remove_chat_window(self, chat_window):
        # 从列表中删除 C 窗口的引用
        if chat_window in self.chatapp_windows:
            self.chatapp_windows.remove(chat_window)
            print(f"窗口关闭。删除 reference to Window ChatApp with id {id(chat_window)}")


# 自定义可扩展的输入框
class ExpandingTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.document().contentsChanged.connect(self.size_change)
        self.setPlaceholderText("输入#标签保存笔记 或者 输入你的问题")
        self.setStyleSheet("""
            QTextEdit { 
                background-color: white; 
                border: 1px solid #D1D1D1; 
                border-radius: 10px; 
                padding: 8px; 
                font-size: 22px; /* 设置字体大小 */
                text-align: center; /* 设置文本居中 */
            }""")

        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.parent = parent
        self.size_change()

    def size_change(self):
        doc = self.document()
        doc_height = doc.size().height()
        # print(f"doc_height: {doc_height}")
        # 设置最小高度以防止过小
        min_height = 50
        # 设置最大高度以限制扩展
        max_height = 600
        # 计算新的高度
        new_height = max(min_height, min(doc_height + 5, max_height))
        self.setFixedHeight(int(new_height))  # 10 for padding
        self.parent.setFixedHeight(int(new_height) + 30)  # 10 for padding


if __name__ == '__main__':
    # def start_select_the_content():
    # 创建Tkinter root窗口
    app = QApplication(sys.argv)
    try:
        sec = SelectTheContentWidget()
    except Exception as e:
        print(e)
    exit_code = app.exec_()
    print(f"Application exited with code {exit_code}")
    sys.exit(exit_code)