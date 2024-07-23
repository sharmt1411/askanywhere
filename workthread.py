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
from review import auto_review


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
            print(self.task.__name__, "返回result", flush=True)
            self.update_signal.emit(str(result))
        except Exception as e:
            print(f"Exception in thread: {e}")


def save_note(user_message, user_select=None):
    print("开始保存note线程：user_message长度:", len(user_message), "user_select:",
          user_select, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), flush=True)
    timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    # 分离出前三行
    lines = user_message.split('\n')
    first_lines = lines[0:2]
    remaining_lines = lines[2:]
    # 使用正则表达式提取标签
    tags_list = []
    for line in first_lines :
        tags_list.extend(re.findall(r'#(?!#)\S+', line))
    # tags_list = re.findall(r'#(?!#)\S+', first_lines[1])
    tags_str1 = ' '.join(tags_list)

    # 提取笔记内容，即去除所有标签后的部分
    first_lines_no_tags = [re.sub(r'#(?!#)\S+', '', line).strip() for line in first_lines]
    content_no_tags = '\n'.join(first_lines_no_tags + remaining_lines)
    # content = re.sub(r'#(?!#)\S+', '', user_message).strip()
    if user_select:
        content = user_select + ":" + content_no_tags
    # 保存笔记（这里需要实现保存逻辑，比如插入数据库）
    db = TinyDatabase()
    tags = db.get_all_tags()
    # print(tags)
    tags_ai = ApiLLM().get_record_tags_deepseek(content_no_tags, tags)
    tags_list2 = re.findall(r'#\S+', tags_ai)
    if len(tags_list2)>5:
        tags_list2 = []          # 多于5个标签，系统可能出错
    tags_str2 = ' '.join(tags_list2)

    doc_id = db.add_record(timestamp, tags_str1, content_no_tags, tags_str2)
    print("结束保存note线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    print("tags:", tags_str1, "tags2:", tags_str2, "contentlenth:", len(content_no_tags), "doc_id:", doc_id, flush=True)
    return doc_id


def window_summary(window_id):
    print("开始获取窗口内容总结线程：window_id:", window_id, time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()), flush=True)
    finish_timestamp = datetime.now().strftime("%y%m%d%H%M%S")
    nodes = WindowNode.get_window_nodes_by_parent_id(window_id)
    window_history = ""
    for node in nodes:
        time_str = f"#时间：{int(node.window_id[6:8])}点{int(node.window_id[8:10])}分\n"
        title_str = f"#User选取：{node.select if node.select else '无'},User疑问：{node.question if node.question else '无'}\n"
        content_str = f"#交流内容：{node.context if node.context else '无'}\n"
        window_str = "\n$窗口<" + time_str + title_str + content_str + "/>"
        window_history += window_str

    db = TinyDatabase()
    content = ApiLLM().get_window_summary_deepseek(window_history)
    if content != "":
        if "万有引力" in content:
            # 创建txt，将内容写入笔记本
            file_path = "wanyouyinli.txt"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write("windowid:"+window_id+"\n\n")
                f.write(window_history)
                f.write("\n\n")
                f.write("content"+content)
        doc_id = db.add_record(finish_timestamp, "#日活动", content)
        print("结束窗口内容总结线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    # print("content:", content, "doc_id:", doc_id, flush=True)
    else:
        print("窗口内容总结为空，不保存", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        doc_id = 0
    return doc_id


def auto_summary():
    print("开始周期总结线程：",time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
          flush=True)

    db = TinyDatabase()
    current_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    current_month_date = current_date.replace(day=1, hour=0, minute=0, second=1, microsecond=0)
    last_summary_date = db.get_last_summary_date()
    last_summary_month_date = db.get_last_summary_date(month=True)
    start_date = None
    start_month_date = None
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
    return_str = ""

    if last_summary_month_date:
        print("有最近的系统月总结日期", last_summary_month_date)
        last_month_date = str_to_date(last_summary_month_date)
        start_month_date = last_month_date + timedelta(days=1)
        print("从新日期开始月总结", start_month_date)
    else:
        first_record_month_date = db.get_first_record_date()
        if first_record_month_date:
            start_month_date = str_to_date(first_record_month_date)
            print("没有最近的系统月总结日期，使用第一个记录日期", start_month_date)

    if start_date:
        # 时间定为当天0点
        date = start_date
        current_date = current_date.replace(hour=0, minute=0, second=1, microsecond=0)  # 今天的结束时间定为当天23点59分59秒，防止今天上午总结今天
        while date < current_date:
            doc_id = auto_summarize_day(date)
            if doc_id:
                return_str += f"{doc_id},"
            # Check if it's the last day of the month
            # if date.day == 1:
            #     month_date = date - timedelta(days=1)
            #     doc_id = auto_summarize_month(month_date)
            #     if doc_id:
            #         return_str += f"{doc_id},"
            date += timedelta(days=1)

    if start_month_date:
        month_date = start_month_date  # 应该开始总结日期 可能是某月1日，或者无初始化的某月任何一天
        month_date = month_date.replace(day=1)  # 统一日期1日开始，用于转化为月底
        month_date = month_date + timedelta(days=32)  # 统一日期为月底 ，转换为下月，1号加30天都不会跨2个月
        month_date = month_date.replace(day=1) - timedelta(days=1)  # 统一日期为月底
        print("start_month_date:", month_date)
        while month_date < current_month_date:    # 应总结月月底小于当前时间，说明需要月总结
            print("current_month_date:", current_month_date)
            doc_id = auto_summarize_month(month_date)
            if doc_id:
                return_str += f"{doc_id},"
            month_date = month_date + timedelta(days=1)  # 日期为月底，转换为下月1号开始
            month_date = month_date + timedelta(days=32)  # 处理变为新月份的月底
            month_date = month_date.replace(day=1) - timedelta(days=1)  # 统一日期为月底
            print("新的month_date:", month_date)
        print("循环结束，周期总结线程", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    if return_str == "":
        return_str = "没有重新总结的记录"
    return return_str


def auto_review_thread(callback=None):
    print("--------------------------------------------------------\n开始auto_review线程：", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
          flush=True)
    note_list = auto_review()
    if note_list:
        string_notes = "\n\n---\n\n".join(note_list)
    else:
        string_notes = "没有需要复习的记录"
    if callback:
        callback(string_notes)
    return string_notes


def str_to_date(date_str) :
    return datetime.strptime(date_str, "%y%m%d%H%M%S")


def date_to_str(date_obj) :
    return date_obj.strftime("%y%m%d%H%M%S")


def auto_summarize_day(date) :  # 日总结，日学习记录总结
    # 这里实现每日总结逻辑
    print(f"auto_summarize_day: 运行 {date_to_str(date)} 的每日总结")
    content = ApiLLM().get_records_summary_deepseek(date)
    db = TinyDatabase()
    date_str_day_summarize = date.strftime("%y%m%d") + "235958"
    date_str_day_review = date.strftime("%y%m%d") + "235957"    # ！！！！注意系统按照timestamp区分，重复会覆盖！！！
    if content != "":
        doc_id = db.add_record(date_str_day_summarize, "#系统日总结", content)
    else:
        doc_id = "无记录"
        # 无活动的不做总结记录
        # doc_id = db.add_record(date_str_day_summarize, "#系统日总结", f"{date_to_str(date)} 无活动记录")
    print(f"auto_summarize_day: 结束 {date_str_day_summarize} 的每日总结，doc_id: {doc_id}")
    review_content = ApiLLM().get_records_review_deepseek(date)
    if review_content != "":
        doc_id_review = db.add_record(date_str_day_review, "#学习记录", review_content)
    else:
        doc_id_review = "无复习"
    print(f"auto_summarize_day: 结束 {date_str_day_review} 的每日学习总结，doc_id_review: {doc_id_review}")
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
