import os
import sys
from datetime import datetime
import time
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QTextEdit, QMainWindow, QVBoxLayout,
                             QHBoxLayout, QLabel, QScrollArea, QFrame,
                             QSizePolicy, QGraphicsDropShadowEffect,QTextBrowser)
from PyQt5.QtGui import QFont, QIcon, QPixmap,QDesktopServices
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtCore import QSize, Qt, QTimer
from markdown2 import markdown

from notification import NotificationWindow
from workthread import WorkThread, save_note, window_summary
from window_node import WindowNode
from api_llm import ApiLLM

def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

class ChatApp(QMainWindow):
    closed_signal = pyqtSignal(object)  # 定义一个信号，在窗口关闭时发出


    def __init__(self, parent="root", window_id=None, window_x=0, window_y=0,
                 select=None, question=None, context="none", window_width=700, window_height=1000):
        super().__init__()

        self.message_temp = None
        self.worker_summary = None
        self.worker_thread = None
        self.message_label = None
        if window_id is None or window_id == 0:
            # //////////新建窗口,生成window_id
            timestamp = time.time()
            dt = datetime.fromtimestamp(timestamp)
            formatted_time = dt.strftime("%y%m%d%H%M%S")
            self.window_id = f"{formatted_time}:{window_x}:{window_y}"
            self.is_restored = False
            print("创建，window_id:", self.window_id)
        else:
            self.window_id = window_id
            self.is_restored = True
        if context == "none":
            context = []
        # print("parent_window_id:", parent)
        if parent == "root" or parent == "none":
            now = datetime.now()
            formatted_date = now.strftime("%y年%#m月%#d日")
            formatted_id = now.strftime("%y%m%d") + "000000"
            self.parent_window_id = f"{formatted_id}:000:000"
        else:
            self.parent_window_id = parent
        print("parent_window_id:", self.parent_window_id)
        self.window_x = window_x
        self.window_y = window_y
        self.select = select
        self.question = question
        self.context = context     # 如果初次带上下文，，context注意处理掉，不然add_message会和元组（sender, message）冲突
        max_length = 20  # 截取字符串到最大长度
        truncated_select = ""
        if select is not None:  # 如果字符串被截断了，尝试在最后一个空格处截断
            truncated_select = select
            if len(select) > max_length:
                truncated_select = select[:max_length]
                last_space_index = truncated_select.rfind(' ')
                if last_space_index != -1:
                    truncated_select = truncated_select[:last_space_index]

        self.setWindowTitle("Jarvis")
        self.setWindowIcon(QIcon(QPixmap(resource_path("icon/Depth_8,_Frame_0explore-角标.png"))))
        # self.setFixedSize(QSize(window_width, window_height))
        self.setWindowFlags(Qt.FramelessWindowHint)
        if window_x == 0 and window_y == 0:
            # print("位置信息为空，使用中间位置")
            self.setFixedSize(QSize(window_width, window_height))
        else:
            # self.setGeometry(window_x, window_y, window_width, 700)  # Set window size
            # 设置位置x，y
            self.setFixedWidth(700)
            self.setMinimumHeight(700)
            self.move(window_x, window_y)

        self.setAttribute(Qt.WA_TranslucentBackground)

        # 圆角窗口
        round_wind = QFrame()
        round_wind.setObjectName("round_Wind")
        round_wind.setStyleSheet("#round_Wind {background-color: #F5F5F5; border: 1px  solid #F0F0F0;"
                                 " border-radius: 20px; padding: 10px;}")
        round_wind.setFrameShadow(QFrame.Raised)  # 阴影
        # round_wind.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=10, xOffset=0.5, yOffset=0.5))

        # Main layout  包括toplayout，chatlayout，inputlayout
        main_layout = QVBoxLayout()  # 垂直布局主窗口
        main_layout.setSpacing(10)   # 设定内部组件间间距
        main_layout.setContentsMargins(0, 0, 0, 0)

        # top_layout 包括上方标签以及关闭窗口按钮
        top_layout = QHBoxLayout()
        top_layout.setAlignment(Qt.AlignTop)
        top_layout.setSpacing(0)
        top_layout.setContentsMargins(0, 0, 10, 0)    # 设定内部组件间间距
        top_label = QLabel("JARVIS")
        top_label.setFont(QFont("Arial", 16, weight=QFont.Bold))
        top_label.setStyleSheet("color: #0078D7;")
        top_layout.addWidget(top_label)
        close_button = QPushButton()
        close_button.setIcon(QIcon(QPixmap(resource_path("icon/Depth_8,_Frame_0explore-角标.png"))))
        close_button.setFixedSize(QSize(50, 50))
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #E1E1E1;
            }
            QPushButton:pressed {
                background-color: #D1D1D1;
            }
        """)
        close_button.setIconSize(QSize(40, 40))
        # close_button.align = Qt.AlignTop | Qt.AlignRight
        close_button.clicked.connect(self.close)
        top_layout.addWidget(close_button, alignment=Qt.AlignRight)

        # 聊天窗口 chat_layout包括标签 滚动区域
        chat_layout = QVBoxLayout()
        chat_layout.setSpacing(20)    # 设定内部组件间间距
        chat_layout.setContentsMargins(10, 0, 10, 5)    # 设定内部组件间间距
        if self.question is not None:
            chat_label = QLabel(str(question))
        elif truncated_select:
            chat_label = QLabel(str(truncated_select))
        else:
            chat_label = QLabel("……")

        chat_label.setAlignment(Qt.AlignCenter)
        chat_label.setFixedHeight(50)
        chat_label.setFont(QFont("Arial", 14, weight=QFont.Bold))
        chat_label.setStyleSheet("border: none; color: #0078D7; padding: 10px;")
        chat_layout.addWidget(chat_label)
        # Chat area
        self.chat_area_layout = QVBoxLayout()
        self.chat_area_layout.setAlignment(Qt.AlignTop)
        self.chat_scroll = QScrollArea()
        self.chat_scroll.setStyleSheet("border: none; background-color: #F5F5F5; padding: 0px;")
        self.chat_scroll.setWidgetResizable(True)    # 可自动调整大小
        self.chat_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏垂直滚动条
        # self.chat_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        self.chat_scroll_vertical_bar = self.chat_scroll.verticalScrollBar()
        # self.chat_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)  # 自动扩展
        # self.chat_scroll.setFixedSize(QSize(700, 900))  # 设置固定大小
        chat_sroll_widget = QWidget()
        # chat_sroll_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 自动扩展
        # chat_sroll_widget.setFixedHeight(300)
        # chat_sroll_widget.setFixedWidth(600)

        #chat_sroll_widget.setStyleSheet("border: none; background-color: #F5F5F5; padding: 10px;")
        chat_sroll_widget.setLayout(self.chat_area_layout)
        self.chat_scroll.setWidget(chat_sroll_widget)
        chat_layout.addWidget(self.chat_scroll)

        # Input frame
        self.input_frame = QFrame()
        self.input_frame.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: none; 
                border-radius: 30px;
            }
        """)
        self.input_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum) # 自动扩展, 最小高度
        self.input_frame.setFixedHeight(83)
        input_layout = QHBoxLayout()
        input_layout.setSpacing(20)
        input_layout.setContentsMargins(30, 0, 30, 0)

        # Attachment button
        attachment_button = QPushButton()
        attachment_button.setIcon(QIcon(QPixmap(resource_path("icon/Depth_9,_Frame_0notes.png"))))
        attachment_button.setIconSize(QSize(50, 50))
        attachment_button.setFixedSize(QSize(50, 50))
        attachment_button.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #E1E1E1;
            }
            QPushButton:pressed {
                background-color: #D1D1D1;
            }
        """)
        input_layout.addWidget(attachment_button)

        # Input field
        self.input_field = AutoResizingInputTextEdit()
        self.input_field.textChanged.connect(self.adjust_input_frame_height)
        # 连接信号和槽
        self.input_field.sendMessageSignal.connect(self.send_message)
        input_layout.addWidget(self.input_field)
        # print("input_field初始化完成")

        # Send button
        self.send_button = QPushButton()
        self.send_button.setIcon(QIcon(QPixmap(resource_path("icon/Depth_8,_Frame_0chat.png"))))
        self.send_button.setIconSize(QSize(50, 50))
        self.send_button.setFixedSize(QSize(50, 50))
        self.send_button.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: none;
                border-radius: 10px;
            }
            QPushButton:hover {
                background-color: #E1E1E1;
            }
            QPushButton:pressed {
                background-color: #D1D1D1;
            }
        """)
        self.send_button.clicked.connect(self.send_message)  # 发送按钮
        input_layout.addWidget(self.send_button)

        self.input_frame.setLayout(input_layout)

        # shortcut = QShortcut(QKeySequence(Qt.Key_Alt), self)  # 绑定回车按键
        # shortcut.activated.connect(self.send_message)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(chat_layout)   # 聊天窗口
        main_layout.addWidget(self.input_frame)
        # main_layout.addLayout(input_layout)   # 输入框和发送按钮
        round_wind.setLayout(main_layout)
        self.setCentralWidget(round_wind)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        print("chat界面初始化完成")
        # self.start_chat()    不能在初始化启动，会减慢窗口刷新出来的速度

    def send_message(self):
        user_message = self.input_field.toPlainText()
        if user_message:
            # 消息首个非空格字符是 '#'，则提取标签和内容
            if user_message.lstrip().startswith('#'):

                self.worker1 = WorkThread(save_note, user_message)
                self.worker1.update_signal.connect(lambda x: NotificationWindow.show_success(x))
                self.worker1.start()
                self.add_message('user', user_message, align_right=True)  # 对话已保存到context中
                self.input_field.clear()
                QTimer.singleShot(50, self.scroll_to_bottom)

            else:
                # self.sleep1()
                print(f"send_message: user: {user_message}")
                self.add_message('user', user_message, align_right=True)     # 对话已保存到context中
                self.input_field.clear()
                QTimer.singleShot(50, self.scroll_to_bottom)
                self.call_stream_llm_and_update_ui(self.select, self.context, self.question)


    def add_message(self, sender, message, align_right=False):
        message_widget = self.get_message_widget(sender=sender, message=message)
        self.chat_area_layout.addWidget(message_widget)
        self.context.append((sender, message))                 # 注意restore时,避免重复存储
        # print("add_message：", sender)

    def scroll_to_bottom(self):
        scrollbar = self.chat_scroll_vertical_bar
        scrollbar.setValue(scrollbar.maximum())
        # print("scroll_to_bottom, scrollbar.value: ", scrollbar.maximum())

    def start_chat(self):
        # 初始化聊天记录
        self.save_window()
        if self.is_restored:
            print("有window_id初始化，restored,开始尝试恢复窗口信息")
            self.load_chat_history()
        elif self.select.strip() != "" or self.question is not None:      # 如果有选取内容，则显示选取内容
            if self.context == "none" or self.context == [] or self.context == "" or self.context is None:
                self.context = []    # 防止其他内容，无法add元组报错
                print("context:none,开始新划词对话")
                # self.add_system_message("准备调用ai，等待ai回答...")
                # 调用api接口获取ai回复
                # ai_reply = ApiLLM.get_response_deepseek(self.select, "none", question=self.question)
                # self.add_assistant_message(ai_reply)1
                self.call_stream_llm_and_update_ui(self.select, "none", self.question, new_window=True)
            else:
                print("有context,开始新划词对话")
                # self.add_system_message("等待ai回答...")
                # 调用api接口获取ai回复
                # ai_reply = ApiLLM.get_response_deepseek(self.select, self.context, question=self.question)
                # self.add_assistant_message(ai_reply)
                context = self.context
                self.context = []  # 不然add assistant message会和元组（sender, message）冲突
                self.call_stream_llm_and_update_ui(self.select, context, self.question, new_window=True)
        else:
            print("Warning Please enter a message.")

    def call_stream_llm_and_update_ui(self, select=None, context=None, question="none", new_window=False,main_window=False):
        # 如果新建窗口，可能存在select，question，context参数 如果继续聊天，则没有select，question，只需context
        # select 和question 属于窗口属性，context属于对话属性
        # 调用api接口获取ai回复
        # print("开始调用api接口获取ai回复select:", select, "context:", context, "question:", question)
        self.worker_thread = GetAIResponseThread(select, context, question, new_window, main_window)
        self.worker_thread.chunk_received_signal.connect(self.call_back_stream_llm_and_update_ui)
        print("worker_thread启动连接")
        self.worker_thread.start()

    def call_back_stream_llm_and_update_ui(self, chunk_message):
        self.add_assistant_message_stream(chunk_message)

    def add_assistant_message_stream(self, message):
        if message is not None:
            if message == "stream_start":
                if self.message_label is not None and self.message_label.toPlainText() == "分析查找记忆中……":  # 如果调用记忆分析，需要清空提示，防止重复插入
                    self.message_label.clear()

                else:
                    message_widget = self.get_message_widget(sender="assistant", message="")
                    self.chat_area_layout.addWidget(message_widget)
                self.message_temp = ""
                # print("add_assistant_message_stream_widget")
            elif message == "stream_end":
                if self.message_label is not None:
                    # self.message_temp += "<>"
                    # self.message_label.setMarkdown(self.message_temp)
                    # self.message_label.append("<>")
                    # self.message_label.adjuestSize()   # 触发resize事件，使得文本框自动适应内容,不注释就卡死
                    print("add_assistant_message_stream_end")
                # self.context.append(("assistant", self.message_label.toMarkdown()))     # 注意restore时,避免重复存储
                self.context.append(("assistant", self.message_temp))
                # self.message_label.resizeEvent(None)   # 触发resize事件，使得文本框自动适应内容,不注释就卡死
            elif message == "function_call":
                self.message_label.setPlainText("分析查找记忆中……")
                self.adjust_output_frame_height(self.message_label)

            else:
                if self.message_label is not None:
                    # print("message:", message)
                    self.message_temp += message
                    # self.message_label.setMarkdown(self.message_temp)
                    # html_content = self.message_temp
                    html_content = markdown(self.message_temp, extras=["fenced-code-blocks", "code-friendly", "mathjax",
                                                                       "tables", "strike", "task_list", "cuddled-lists"])
                    styled_html_content = f"""
                                               <html>
                                               <head>
                                               <style>
                                                 body {{
                                                    font-family: Arial, sans-serif;
                                                    line-height: 1.3;  /* 设置行高 */
                                                }}
                                                p {{
                                                    margin: 0;
                                                    padding: 0;
                                                }}
                                                pre, code {{
                                                    margin: 0;
                                                    padding: 0;
                                                    background-color: #f5f5f5;
                                                    border: none;
                                                    line-height: 1.0;  /* 设置行高 */
                                                }}
                                                pre {{
                                                    background-color: #f5f5f5;
                                                    padding: 0px;
                                                    border-radius: 5px;
                                                    margin: 0;
                                                }}
                                                code {{
                                                    background-color: #f5f5f5;
                                                    padding: 0px 0px;
                                                    border-radius: 3px;
                                                    margin: 0;
                                                }}
                                                .code-container {{
                                                    margin: 0;
                                                    padding: 0;
                                                }}
                                                table {{
                                                    width: 100%;
                                                    border-collapse: collapse;
                                                }}
                                                th, td {{
                                                    border: 1px solid #ddd;
                                                    padding: 8px;
                                                }}
                                                th {{
                                                    background-color: #f2f2f2;
                                                    text-align: left;
                                                }}
                                               </style>
                                               </head>
                                               <body>
                                               {html_content}
                                               </body>
                                               </html>
                                               """
                    self.message_label.setHtml(styled_html_content)
                    self.adjust_output_frame_height(self.message_label)
                    # self.message_label.resizeEvent(None)   # 触发resize事件，使得文本框自动适应内容,不注释就卡死

                    # print("插入", message)
        QTimer.singleShot(50, self.scroll_to_bottom)

    def get_message_widget(self, sender="", message=""):             # message 格式在此处定义修改
        message_widget = QWidget()
        message_widget.setObjectName("message_widget")
        message_widget.setStyleSheet(
            "#message_widget {background-color: white; border: 0px solid #E0E0E0;"
            "border-radius: 20px; padding: 0px;}")
        # 为部件添加shadow效果
        message_widget.setGraphicsEffect(QGraphicsDropShadowEffect(blurRadius=10, xOffset=3, yOffset=0.5))
        message_box = QVBoxLayout()
        message_box.setSpacing(5)
        message_box.setContentsMargins(10, 10, 10, 10)
        sender_label = QLabel(sender)
        sender_label.setStyleSheet(" background-color: white; padding: 5px; border-radius: 5px; font-size: 23px; "
                                   "font-weight: bold;")
        if sender == "assistant" or sender == "system" or sender == "review":
            message_label = AutoResizingTextEdit()
            html_content = markdown(message, extras=["fenced-code-blocks", "code-friendly", "mathjax",
                                                     "tables", "strike", "task_list", "cuddled-lists"])
            styled_html_content = f"""
                                               <html>
                                               <head>
                                               <style>
                                                 body {{
                                                    font-family: Arial, sans-serif;
                                                    line-height: 1.3;  /* 设置行高 */
                                                }}
                                                p {{
                                                    margin: 0;
                                                    padding: 0;
                                                }}
                                                pre, code {{
                                                    margin: 0;
                                                    padding: 0;
                                                    background-color: #f5f5f5;
                                                    border: none;
                                                    line-height: 1.0;  /* 设置行高 */
                                                }}
                                                pre {{
                                                    background-color: #f5f5f5;
                                                    padding: 0px;
                                                    border-radius: 5px;
                                                    margin: 0;
                                                    border: 1px solid #E0E0E0;
                                                }}
                                                code {{
                                                    background-color: #f5f5f5;
                                                    padding: 0px 0px;
                                                    border-radius: 3px;
                                                    margin: 0;
                                                }}
                                                .code-container {{
                                                    margin: 0;
                                                    padding: 0;
                                                }}
                                                table {{
                                                    width: 100%;
                                                    border-collapse: collapse;
                                                }}
                                                th, td {{
                                                    border: 1px solid #ddd;
                                                    padding: 8px;
                                                }}
                                                th {{
                                                    background-color: #f2f2f2;
                                                    text-align: left;
                                                }}
                                               </style>
                                               </head>
                                               <body>
                                               {html_content}
                                               </body>
                                               </html>
                                               """
            message_label.setHtml(styled_html_content)
            self.message_label = message_label
        else:
            message_label = AutoResizingTextEdit()
            message_label.insertPlainText(message)

        message_label.setStyleSheet(
            "background-color: white; padding: 5px; border-radius: 5px;font-size: 20px;")
        message_box.addWidget(sender_label)
        message_box.addWidget(message_label)
        message_widget.setLayout(message_box)
        QTimer.singleShot(20, lambda: self.adjust_output_frame_height(message_label))
        return message_widget

    def load_chat_history(self):    # 如果有window_id，则从数据库中恢复窗口信息
        print("load_chat_history")
        window_node = WindowNode.get_window_node_by_id(self.window_id)
        if window_node is not None:
            chat_history = window_node.context
            if chat_history is None:
                return
            for sender, message in chat_history:
                self.add_message(sender, message)
        QTimer.singleShot(800, self.scroll_to_bottom)

    def closeEvent(self, event):
        print("closeEvent")
        # ///////////////////////////////如果是顶层窗口，父窗口是240530000000：000：000，全部触发总结
        self.save_window()
        print("关闭窗口,窗口id:", self.window_id, "父窗口id：", self.parent_window_id)
        if self.parent_window_id[-12:] == '0000:000:000':
            # print("关闭窗口，启动总结线程")
            self.worker_summary = WorkThread(window_summary, self.window_id)
            self.worker_summary.update_signal.connect(lambda x : NotificationWindow.show_success(x))
            print("关闭窗口，启动总结线程")
            self.worker_summary.start()

            # QTimer.singleShot(10000, self.closed_signal.emit(self))
            # print("隐藏删除索引")
            # event.accept()
            self.hide()
            QTimer.singleShot(10000, lambda: self.closed_signal.emit(self))
            print("隐藏删除索引")
            event.ignore()

        else:
            self.closed_signal.emit(self) # 发出信号，传递自身引用
            print("直接关闭")
            event.accept()

    @staticmethod
    def from_window_node(window_node):
        window_id = window_node.window_id
        position = window_id.split(':')
        window_x = position[1]
        window_y = position[2]
        chat_window = ChatApp(window_node.parent_window_id, window_id=window_id, window_x=window_x,
                              window_y=window_y, select=window_node.select, question=window_node.question,
                              context=window_node.context)
        return chat_window

    def to_window_node(self):
        window_node = WindowNode(self.window_id, self.parent_window_id, self.select, self.question,
                                 self.context)
        return window_node

    def save_window(self):
        self.window_x, self.window_y = self.x(), self.y()  # 更新窗口位置信息
        print("save_window(),window_id:", self.window_id, "parent_window_id:", self.parent_window_id)
        self.to_window_node().save_window_node()

    @staticmethod                     # 静态方法，可直接调用恢复窗口
    def restore_window_by_id(window_id):
        window_node = WindowNode.get_window_node_by_id(window_id)
        if window_node is not None:
            ChatApp.from_window_node(window_node)
        else:
            print("没有找到对应的窗口记录")

    def adjust_input_frame_height(self):   # 调整输入框高度以适应内容,此处输入框限制最大高度为300
        doc_height = self.input_field.document().size().height()
        # print(f"输入框doc_height: {doc_height}")
        # 设置最小高度以防止过小
        min_height = 83
        # 设置最大高度以限制扩展
        max_height = 300
        # 计算新的高度
        new_height = max(min_height, min(doc_height + 52, max_height))
        # new_height = max(min_height, doc_height+52)
        # print(f"输入框new_height: {new_height}")
        self.input_field.setFixedHeight(int(new_height))  # 10 for padding
        self.input_frame.setFixedHeight(int(new_height) + 10)  # 10 for padding  同步更新外框高度

    def adjust_output_frame_height(self, widget):   # 调整输入框高度以适应内容,此处输入框限制最大高度为300
        doc_height = widget.document().size().height()
        # print(f"输出doc_height: {doc_height}")
        # 设置最小高度以防止过小
        min_height = 45
        # 设置最大高度以限制扩展
        max_height = 800
        # 计算新的高度
        new_height = max(min_height, min(doc_height + 12, max_height))
        # print(f"输出框new_height: {new_height}")
        widget.setFixedHeight(int(new_height))  # 10 for padding


class GetAIResponseThread(QThread):
    chunk_received_signal = pyqtSignal(str)

    def __init__(self, select, context, question, new_window=False, main_window=False):
        super().__init__()
        self.select = select
        self.context = context
        self.question = question
        self.new_window = new_window
        self.main_window = main_window
        print("GetAIResponseThread初始化")

    def run(self):
        if self.main_window:   # 主窗口，需要判断是否读取记忆,如果需要读取到记忆再处理回复
            print("主窗口，需要判断是否读取记忆线程start")
            # print("select:", self.select, "question:", self.question, "context:", self.context)
            ApiLLM.handle_user_query(self.select, self.context, self.question, self.chunk_received_signal.emit)    #主窗口question是日期

        else:
            print("getAIResponseThread启动线程start")
            ApiLLM.get_stream_response_deepseek(self.select, self.context, self.question, self.chunk_received_signal.emit,
                                                self.new_window)


class AutoResizingInputTextEdit(QTextEdit):                  # 可扩展消息输入文本框
    # 定义一个信号，当需要发送消息时发出
    sendMessageSignal = pyqtSignal()
    def __init__(self,parent=None):
        super().__init__(parent)
        self.setPlaceholderText('聊聊吧，可再次划词…… #标签 保存笔记， ~help 详细了解~')
        self.setStyleSheet("""
                    QTextEdit {
                        background-color: transparent;
                        border: 1px solid #E0E0E0;
                        padding: 25px;
                        font-size: 20px;
                    }
                """)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.setFixedHeight(83)

    def keyPressEvent(self, event) :
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter :
            if event.modifiers() == Qt.ShiftModifier or event.modifiers() == Qt.ControlModifier :
                # Shift+Enter 或 Ctrl+Enter 换行
                self.insertPlainText("\n")
            else :
                # Enter 发送内容
                self.sendMessageSignal.emit()
        else :
            super().keyPressEvent(event)


class AutoResizingTextEdit(QTextBrowser):                  # 可扩展消息显示文本框
    def __init__(self, parent=None):
        super().__init__(parent)
        # 确保 QTextBrowser 不会尝试自己打开链接
        self.setOpenExternalLinks(False)
        # 连接 anchorClicked 信号到自定义的槽函数
        self.anchorClicked.connect(self.open_link_in_browser)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)  # 自动扩展宽度，最小高度
        self.setViewportMargins(0, 0, 0, 0)   # 去掉边框
        self.setContentsMargins(0, 0, 0, 0)
        # self.setVerticalScrollBarPolicy(Qt.ScrollBarAllwaysOff)  # 隐藏垂直滚动条
        # self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)  # 隐藏水平滚动条
        print("AutoResizingTextEdit 可扩展消息显示文本框初始化完成")
        # self.setStyleSheet("background: transparent; border: none;")
        # self.setMaximumHeight(100)  # 设置最大高度

    # def resizeEvent(self, event):
    #     if not self._resizing :
    #         self._resizing = True  # 设置标志为 True，表示正在调整大小
    #         self.document().adjustSize()
    #         self.init_height +=10
    #         document_height = self.document().size().height()
    #         print("document_height:", document_height,"组件可视高度", self.viewport().height())
    #         # self.setFixedHeight(int(document_height + 10))  # 加一些额外的空间以避免滚动条
    #         self.setFixedHeight(int(self.init_height))  # 加一些额外的空间以避免滚动条
    #         # super().resizeEvent(event)
    #     self._resizing = False  # 调整大小完成后，重置标志

    def open_link_in_browser(self, url):
        # 使用系统默认浏览器打开链接
        QDesktopServices.openUrl(url)

    def setSource(self, url) :
        # 重写 setSource 方法，防止 QTextBrowser 尝试改变内容
        # 可以在这里调用 open_link_in_browser，或者简单地忽略
        # self.open_link_in_browser(url)
        pass


    # def mouseReleaseEvent(self, event):
    #     super().mouseReleaseEvent(event)
    #     selected_text = self.textCursor().selectedText()
    #     full_text = self.toPlainText()
    #     if selected_text:
    #         self.text_selected.emit(self.window_id, selected_text, full_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatApp(parent="root", window_id=0, window_x=50, window_y=50, select="你好，我是Jarvis，你是谁？",
                     question="你好，我是Jarvis，你是谁？", context="none")
    # window.start_chat()
    window.show()
    window.start_chat()
    sys.exit(app.exec_())

    # def get_ai_response(self, message):   # 改为使用流式调用
    #     # Simulate an AI response (replace this with actual AI interaction code)
    #     self.call_stream_llm_and_update_ui(self.select, self.context, self.question)

    # def save_chat_history(self):
    #     self.context = self.chat_history.get(1.0, 'end')
    #     print("保存聊天记录:", self.context)
    # 在每一步新增消息时存储聊天记录
