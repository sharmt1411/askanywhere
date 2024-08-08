import base64
import sys
import os

from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QFileDialog, QMessageBox, QVBoxLayout, QMainWindow, \
    QRubberBand, QLabel
from PyQt5.QtGui import QIcon, QPixmap
from openai import OpenAI

import config


def resource_path(relative_path):
    """获取资源文件的绝对路径"""
    try:
        # PyInstaller 创建临时文件夹，并将路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class FileUploader(QMainWindow):
    """
    只支持部分图片和音频格式的上传，返回文件路径
    """
    info_signal = pyqtSignal(str, str)

    def __init__(self):
        super().__init__()
        self.info_label = None
        self.rubber_band = None
        self.end_point = None
        self.start_point = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('文件功能')
        self.setWindowIcon(QIcon(QPixmap(resource_path("icon/Depth_8,_Frame_0explore-角标.png"))))
        self.setFixedSize(200, 250)
        # 设置窗口居中
        self.move(QApplication.desktop().screen().rect().center() - self.rect().center())
        # 设置窗口标志，去掉最小化和最大化按钮
        self.setWindowFlags(Qt.Window | Qt.WindowTitleHint | Qt.WindowCloseButtonHint)

        # 置顶显示

        self.setWindowFlags(self.windowFlags() | Qt.WindowStaysOnTopHint)

        # 创建一个中央窗口部件
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # 创建布局
        layout = QVBoxLayout(central_widget)

        # 创建按钮
        upload_button = QPushButton('选择文件', self)
        screenshot_button = QPushButton('截图上传', self)
        # 增加text文本显示
        self.info_label = QLabel(self)
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setText('尽量在小窗中选择文件\n单次解析\n主窗口有上下文记忆\n会持续消耗token')

        # clipboard_button = QPushButton('剪贴板', self)

        # 将按钮添加到布局
        layout.addWidget(upload_button)
        layout.addWidget(screenshot_button)
        layout.addWidget(self.info_label)
        # layout.addWidget(clipboard_button)

        # 设置按钮的大小
        upload_button.setFixedSize(150, 50)
        screenshot_button.setFixedSize(150, 50)

        # clipboard_button.setFixedSize(150, 50)

        # 按钮连接功能
        upload_button.clicked.connect(self.upload_file)
        screenshot_button.clicked.connect(self.start_screenshot)
        # clipboard_button.clicked.connect(self.clipboard_upload)

        # 设置布局为居中
        layout.setAlignment(upload_button, Qt.AlignCenter)
        layout.setAlignment(screenshot_button, Qt.AlignCenter)
        # layout.setAlignment(clipboard_button, Qt.AlignCenter)

    def start_screenshot(self):
        self.start_point = None
        self.end_point = None
        self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
        # 让窗口变得透明
        self.setWindowOpacity(0.1)
        self.showFullScreen()
        QApplication.setOverrideCursor(Qt.CrossCursor)

    def mousePressEvent(self, event):
        if self.isFullScreen() and event.button() == Qt.LeftButton:
            self.start_point = event.pos()
            self.end_point = self.start_point
            self.rubber_band.setGeometry(QRect(self.start_point, self.end_point))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if self.isFullScreen() and self.rubber_band:
            self.end_point = event.pos()
            self.rubber_band.setGeometry(QRect(self.start_point, self.end_point))

    def mouseReleaseEvent(self, event):
        if self.isFullScreen() and event.button() == Qt.LeftButton and self.rubber_band:
            self.end_point = event.pos()
            self.rubber_band.hide()
            self.take_screenshot()

    def take_screenshot(self):
        # 计算截图区域
        x = min(self.start_point.x(), self.end_point.x())
        y = min(self.start_point.y(), self.end_point.y())
        width = abs(self.start_point.x() - self.end_point.x())
        height = abs(self.start_point.y() - self.end_point.y())
        rect = QRect(x, y, width, height)

        # 截取指定区域
        screen = QApplication.primaryScreen()
        screenshot = screen.grabWindow(0, x, y, width, height)
        if not os.path.exists("./cache") :
            os.makedirs("./cache")  # 创建文件夹
        screenshot.save('./cache/screenshot-cache.png', 'png')
        print('截图成功')
        # 恢复界面状态
        self.setWindowOpacity(1.0)
        print('恢复界面状态')
        self.showNormal()
        print('恢复界面')
        QApplication.restoreOverrideCursor()

        # 处理截图
        self.process_image('./cache/screenshot-cache.png')

    # def is_audio_content(self, mime_data):
    #     # 判断剪切板内容是否为音频
    #     return (mime_data.hasFormat("audio/wav") or mime_data.hasFormat("audio/mpeg") or mime_data.hasFormat("audio/ogg")
    #             or mime_data.hasFormat("audio/mp3") or mime_data.hasFormat("audio/m4a") or mime_data.hasFormat("audio/webm")
    #             or mime_data.hasFormat("audio/mp4"))

    # 剪切板读取文件失败
    # def clipboard_upload(self):
    #     clipboard = QApplication.clipboard()
    #     mime_data = clipboard.mimeData()
    #     print("Available clipboard formats:", mime_data.formats())
    #
    #     if mime_data.hasFormat('file'):
    #         file_urls = mime_data.urls()
    #         if len(file_urls) == 1:
    #             file_format = file_urls[0].fileName().split('.')[-1]  # 获取文件扩展名作为格式
    #             print("单个文件格式:", file_format)
    #         else:
    #             print("剪贴板中的文件不是单个文件")
    #             QMessageBox.information(self, '暂不支持多文件', f'剪贴板中有多个文件，重新选择文件')
    #             return
    #     else:
    #         print("剪贴板中没有文件")
    #         QMessageBox.information(self, '错误', f'剪贴板中没有文件，请选择文件')
    #         return
    #
    #     # 判断剪切板内容是否为图像
    #     if mime_data.hasImage():
    #         image = clipboard.image()
    #         print("剪切板内容是图像。")
    #         # 保存图片
    #         image.save('./cache/screenshot-cache.png', 'png')
    #         self.process_image('./cache/screenshot-cache.png')
    #
    #     elif self.is_audio_content(mime_data):
    #         print("剪切板内容是音频。")
    #         # 保存到本地
    #         with open('./cache/audio-cache.mp3', 'wb') as f:
    #             f.write(mime_data.data("audio/mp3"))
    #
    #
    #         self.process_audio(mime_data)
    #     else:
    #         print("剪切板内容既不是图像也不是音频。")

    def upload_file(self):
        # 弹出文件选择对话框
        selected_file, _ = QFileDialog.getOpenFileName(self, '选择文件,支持部分图片，音频格式', '',
                                                       'Images (*.png *.jpg *.jpeg *.webp);;'
                                                       'Audio (*.mp3 *.wav *.oog *.m4a *.mpeg *.webm *.mp4)')
        if selected_file:
            self.analyze_file(selected_file)

    def analyze_file(self, selected_file_name):
        # 获取文件后缀
        print("分析文件格式",selected_file_name)
        file_name, file_extension = os.path.splitext(selected_file_name)
        file_extension = file_extension.lower()  # 转换为小写以便比较

        # 定义支持的图片和音频格式
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp'}
        audio_extensions = {'.mp3', '.wav', '.ogg', '.m4a', '.mpeg', '.webm', '.mp4'}

        # 判断文件类型
        if file_extension in image_extensions:
            # 调用处理图片的函数
            self.process_image(selected_file_name)
        elif file_extension in audio_extensions:
            # 调用处理音频的函数
            self.process_audio(selected_file_name)
        else:
            # 不支持的文件类型
            QMessageBox.information(self, '文件格式不支持', f'重新选择文件: {selected_file_name}')

    def process_image(self, image_file):
        # 处理图片文件的代码
        print(f"正在处理图片: {image_file}")
        try:
            self.info_signal.emit(image_file, "pic")
        except Exception as e:
            print(e)

        # 关闭窗口
        self.close()

        # 测试API接口
        # try:
        #     with open(image_file, "rb") as image_file :
        #         base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        #     print(base64_image)
        #     client = OpenAI(api_key="", base_url= "https://api.gptsapi.net/v1")
        #     response = client.chat.completions.create(
        #         model= "gpt-4o-mini",
        #         messages=[
        #             {"role" : "system",
        #              "content" : "You are a helpful assistant that responds in Markdown. Help me with my math homework!"},
        #             {"role" : "user", "content" : [
        #                 {"type" : "text", "text" : "这是用户上传的图片"},
        #                 {"type" : "image_url", "image_url" : {
        #                     "url" : f"data:image/png;base64,{base64_image}"}
        #                  }
        #             ]},
        #             {"role" : "user", "content" : "这张图表达了啥"}
        #         ],
        #         temperature=0.0,
        #     )
        #     print(response.choices[0].message.content)
        # except Exception as e:
        #     print(e)

    def process_audio(self, audio_file):
        text = None
        error = None
        # 处理音频文件的代码
        print(f"正在处理音频: {audio_file}", "audio")
        QMessageBox.information(self, '音频处理中', f'音频处理时间随输入增加，请关闭本窗口后，耐心等待音频处理结束，但不要关闭文件功能小窗口！！')
        try:
            # client = OpenAI(api_key="sk-", base_url="https://api.gptsapi.net/v1")
            client = OpenAI(api_key=config.API_KEY, base_url=config.BASE_URL)
            transcription = client.audio.transcriptions.create(
                model="whisper-1",
                file=open(audio_file, "rb"),
            )
            QMessageBox.information(self, '音频处理完成', f'音频处理完成，请查看输出结果')
            text = transcription.text
            print(text)
        except Exception as e:
            error = e
            print(e)
        if text:
            self.info_signal.emit(text, "audio")
        else:
            QMessageBox.information(self, '音频处理失败', f'错误信息：{error}')
        self.close()
        # content = "音频内容:" + audio_file


if __name__ == "__main__":
    app = QApplication(sys.argv)
    uploader = FileUploader()
    uploader.show()
    sys.exit(app.exec_())

