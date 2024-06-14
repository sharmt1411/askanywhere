import os
import json
from datetime import datetime, timedelta

from tinydatabase import RecordSearcher

# 定义复习间隔
REVIEW_INTERVALS = [1, 3, 7, 15, 30, 180]

# 存储复习记录的文件路径
RECORD_FILE = 'review_records.json'

def initialize_records():
    """初始化复习记录"""
    if os.path.exists(RECORD_FILE):
        records = load_records()
        if records :
            print("记录文件review_records.json已存在内容")
            last_record_date = max(records.keys())
            last_record_date = datetime.strptime(last_record_date, '%y%m%d')
            current_date = last_record_date + timedelta(days=1)
            end_date = datetime.now() - timedelta(days=1)
            while current_date <= end_date :
                record_id = current_date.strftime('%y%m%d')
                records[record_id] = {
                    'last_review_date' : record_id,
                    'current_interval' : 1
                }
                current_date += timedelta(days=1)
            save_records(records)
            return
    else:
        print("不存在记录文件，创建记录文件review_records.json")
    records = {}
    start_date = datetime.strptime('240601', '%y%m%d')
    end_date = datetime.now() - timedelta(days=1)
    current_date = start_date
    while current_date <= end_date:
        record_id = current_date.strftime('%y%m%d')
        records[record_id] = {
            'last_review_date': record_id,
            'current_interval': 1
        }
        current_date += timedelta(days=1)
    save_records(records)


def load_records():
    """加载复习记录"""
    if os.path.getsize(RECORD_FILE) == 0 :
        print(f"File {RECORD_FILE} is empty")

        return {}  # 返回一个空的字典或其他默认值
    with open(RECORD_FILE, 'r') as file:
        return json.load(file)

def save_records(records):
    """保存复习记录"""
    with open(RECORD_FILE, 'w') as file:
        json.dump(records, file, indent=4)
    print("saving records success")

def get_notes_by_date(date):
    """根据日期获取笔记（模拟接口）"""
    # 这里应该调用实际的获取笔记的接口
    records =[]
    start_time = date+"000000"
    end_time = date+"235959"
    searcher = RecordSearcher()
    params = {
        "tags" : ["读书笔记", "学习笔记", "笔记", "学习记录", "学习"],
        "combine_tags" : "OR",
        "start_time" : start_time,
        "end_time" : end_time,
        "keywords" : [],
        "combine_keywords" : "OR"
    }
    results = searcher.search_records(params)
    for result in results:
        records.append(result.get("content"))
    print("review.get_notes_by_date",date, "results:", results)
    # print("review.get_notes_by_date",date, "records:", records)
    # 这里只是模拟返回一些笔记内容
    return records

def review():
    """执行复习操作"""
    records = load_records()
    print("load records success")
    today = datetime.now().strftime('%y%m%d')
    review_dates = []
    notes_list = []
    for interval in REVIEW_INTERVALS:
        found_record = False
        review_date = (datetime.now() - timedelta(days=interval)).strftime('%y%m%d')  # 当前间隔起始查询日期
        print(f"Reviewing notes for {review_date} with interval {interval}")
        # 每一个间隔时间的复习日期，比如240601，240603，240607，240614，240629，240718，260117
        while review_date in records:              # 如果记录中有该日期的记录，否则说明超期
            record = records[review_date]       # 获取该日期的记录，以便后续更新
            if record['current_interval'] == interval and record['last_review_date'] != today:
                # 如果当前间隔与记录中的间隔相同并且上次复习日期不等于当前日期，则复习，否则陷入死循环，
                # 更新比较远的1天后，在3天间隔仍会重复，7天间隔则不会重复

                notes = get_notes_by_date(review_date)
                if notes:
                    string_notes = "\n\n".join(notes)
                    notes_list.append(f"###间隔{interval}天的复习记录\n###{review_date}\n"+string_notes+"\n")
                    found_record = True
                    # print(f"get Reviewing notes for {review_date}: {notes}")
                    record['last_review_date'] = today
                    # 计算下次复习日期
                    next_interval_index = REVIEW_INTERVALS.index(record['current_interval']) + 1  # 判断下次间隔是否超出范围
                    if next_interval_index < len(REVIEW_INTERVALS):
                        record['current_interval'] = REVIEW_INTERVALS[next_interval_index]
                    else:
                        record['current_interval'] = 0

                    break

                else:  # 没有学习记录，则置为-1
                    record['current_interval'] = -1   # 置为-1表示没有学习记录，跳过该日期，继续下一个日期
                    initial_date = datetime.strptime(review_date, "%y%m%d") - timedelta(days=1)
                    review_date = initial_date.strftime("%y%m%d")
                    print(f"no notes found for {review_date}, interval {interval}, skipping.new date{review_date}")

            else:
                initial_date = datetime.strptime(review_date, "%y%m%d") - timedelta(days=1)
                review_date = initial_date.strftime("%y%m%d")
                print(f"interval not match {review_date}, skipping.new date{review_date}")

        if not found_record:
            notes_list.append(f"####{interval}天周期的复习，无记录")
            print(f"当前间隔{interval}，无记录.准备下一个间隔")

    save_records(records)
    return notes_list


def auto_review():
    initialize_records()
    notes_list = review()
    return notes_list

if __name__ == "__main__":
    initialize_records()
    notes_list = review()
    print(notes_list)