import re
import sys
from datetime import datetime, timedelta
import time

from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QApplication

from api_llm import ApiLLM
from notification import NotificationWindow
from tinydatabase import TinyDatabase
from window_node import WindowNode


class WorkThread(QThread):
    update_signal = pyqtSignal(str)

    def __init__(self, task, *args, **kwargs):
        super().__init__()
        self.task = task
        self.args = args
        self.kwargs = kwargs
        print("wokerthread-task:", task, "args:", args, "kwargs:", kwargs)

    def run(self):
        try:
            print("worker.run()", flush=True)
            result = self.task(*self.args, **self.kwargs)
            print("result:", result, flush=True)
            self.update_signal.emit(str(result))
        except Exception as e:
            print(f"Exception in thread: {e}")


def save_note(user_message, user_select=None):
    print("开始保存note线程：user_message:", user_message, "user_select:",
          user_select, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), flush=True)
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    tags_list = re.findall(r'#\S+', user_message)
    tags_str1 = ' '.join(tags_list)
    # 提取笔记内容，即去除所有标签后的部分
    content = re.sub(r'#\S+', '', user_message).strip()
    if user_select:
        content = user_select + ":" + content
    # 保存笔记（这里需要实现保存逻辑，比如插入数据库）
    db = TinyDatabase()
    tags = db.get_all_tags()
    # print(tags)
    tags_ai = ApiLLM().get_record_tags_deepseek(content, tags)
    tags_list2 = re.findall(r'#\S+', tags_ai)
    tags_str2 = ' '.join(tags_list2)

    doc_id = db.add_record(timestamp, tags_str1, content, tags_str2)
    print("结束保存note线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    print("tags:", tags_str1, "tags2:", tags_str2, "content:", content, "doc_id:", doc_id, flush=True)
    return doc_id


def window_summary(window_id):
    print("开始获取窗口内容总结线程：window_id:", window_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), flush=True)
    finish_timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    nodes = WindowNode.get_window_nodes_by_parent_id(window_id)
    window_history = ""
    for node in nodes:
        time_str = f"#时间：{int(node.window_id[6:8])}点{int(node.window_id[8:10])}分\n"
        title_str = f"#User选取：{node.select if node.select else '无'},User疑问：{node.question if node.question else '无'}\n"
        content_str = f"#交流内容：{node.context if node.context else "无"}\n"
        window_str = "\n$窗口<" + time_str + title_str + content_str + "/>"
        window_history += window_str

    db = TinyDatabase()
    content = ApiLLM().get_window_summary_deepseek(window_history)

    doc_id = db.add_record(finish_timestamp, "#日活动", content)
    print("结束窗口内容总结线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    # print("content:", content, "doc_id:", doc_id, flush=True)
    return doc_id


def auto_summary():
    print("开始周期总结线程：",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
          flush=True)

    db = TinyDatabase()
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    last_summary_date = db.get_last_summary_date()
    start_date = None
    # 检查是否有最近的日总结日期
    if last_summary_date:
        print("有最近的系统日总结日期", last_summary_date)
        last_date = str_to_date(last_summary_date)
        start_date = last_date + timedelta(days=1)
        print("从新日期开始", start_date)
    else:
        first_record_date = db.get_first_record_date()
        if first_record_date:
            start_date = str_to_date(first_record_date)
            print("没有最近的系统日总结日期，使用第一个记录日期", start_date)

    if start_date:

        date = start_date
        while date < current_date:
            auto_summarize_day(date)
            # Check if it's the last day of the month
            if date.day == 1:
                month_date = date - timedelta(days=1)
                auto_summarize_month(month_date)
            date += timedelta(days=1)
        print("循环结束，周期总结线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))


def str_to_date(date_str) :
    return datetime.strptime(date_str, "%y%m%d%H%M%S")


def date_to_str(date_obj) :
    return date_obj.strftime("%y%m%d%H%M%S")


def auto_summarize_day(date) :
    # 这里实现每日总结逻辑
    print(f"运行 {date_to_str(date)} 的每日总结")
    content = ApiLLM().get_records_summary_deepseek(date)
    db = TinyDatabase()
    date_str = date.strftime("%y%m%d") + "235958"
    doc_id = db.add_record(date_str, "#系统日总结", content)
    print(f"结束 {date_str} 的每日总结，doc_id: {doc_id}")
    return doc_id


def auto_summarize_month(date) :
    # 这里实现当月总结逻辑
    print(f"运行 {date.year} 年 {date.month} 月的月总结")
    content = ApiLLM().get_records_summary_month_deepseek(date)
    db = TinyDatabase()
    date_str = date.strftime("%y%m%d")+"235959"
    doc_id = db.add_record(date_str, "#系统月总结", content)
    print(f"结束 {date_to_str(date)} 的每月总结，doc_id: {doc_id}")
    return doc_id




if __name__ == '__main__':
    # 你的线程创建和启动代码
    # app = QApplication(sys.argv)
    # worker1 = WorkThread(save_note, "#读书 我顺着剥落的高墙走路，踏着松的灰土。另外有几个人，各自走路。微风起来，露在墙头的高树的枝条带着还未干枯的叶子在我头上摇动。")
    # worker1.update_signal.connect(lambda x: NotificationWindow.show_success(x))
    # print("start worker1")
    # worker1.start()
    # print("end worker1")
    # sys.exit(app.exec_())

    app = QApplication(sys.argv)
    worker1 = WorkThread(window_summary, "240531000000:000:000")
    worker1.update_signal.connect(lambda x: NotificationWindow.show_success(x))
    print("start worker1")
    worker1.start()
    print("end worker1")
    sys.exit(app.exec_())  # 你的线程创建和启动代码