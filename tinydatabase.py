import re

from datetime import datetime

from tinydb import TinyDB, Query, where


class TinyDatabase:
    _instance = None

    def __new__(cls, db_file='tiny_data.json'):
        if cls._instance is None:
            cls._instance = super(TinyDatabase, cls).__new__(cls)
            cls._instance._initialize(db_file)
        return cls._instance

    def _initialize(self, db_file):
        """
        初始化数据库
        """
        self.db = TinyDB(db_file)
        self.query = Query()
        self.windows = self.db.table('windows')
        self.records = self.db.table('records')
        self.all_tags = self.db.table('all_tags')
        # 初始化标签列表，如果不存在
        if len(self.all_tags.all()) == 0:
            self.all_tags.insert({'all_tags': [
                '#日总结', '#月总结', '#日活动', '#系统日总结', '#系统月总结',
                '#学习', '#笔记', '#作业', '#考试', '#复习', '#课程',
                '#阅读', '#研究', '#项目', '#实验', '#工作', '#任务', '#会议', '#报告', '#项目管理', '#客户', '#同事',
                '#进度', '#文档', '#演示', '#目标', '#技能', '#培训', '#自我提升', '#健康', '#锻炼', '#饮食', '#睡眠',
                '#习惯', '#心情', '#日程', '#计划', '#提醒', '#待办', '#重要', '#紧急', '#长远目标', '#短期目标',
                '#高优先级', '#购物', '#旅行', '#娱乐', '#家庭', '#朋友', '#生日', '#纪念日', '#节日', '#财务', '#编程',
                '#代码', '#开发', '#调试', '#技术文档', '#工具', '#框架', '#库', '#算法', '#数据', '#创意', '#灵感',
                '#设计', '#艺术', '#音乐', '#摄影', '#写作', '#绘画', '#手工', '#项目构思', '#社交', '#网络', '#联系',
                '#邮件', '#电话', '#会议', '#活动', '#聚会', '#社交媒体', '#社区', '#收入', '#支出', '#投资', '#储蓄',
                '#预算', '#账单', '#税务', '#理财', '#保险', '#参考', '#资源', '#链接', '#文件', '#图片', '#总结',
                '#询问记录', '#中优先级', '#低优先级', '#读书笔记', '#待办', '#进行中', '#已完成', '#暂停', '#取消',
                '#待处理', '#草稿', '#愉快', '#有挑战', '#灵感', '#反思', '#图书', '#论文', '#文章', '#视频',
                '#网站', '#截止日期', '#会议日期', '#纪念日', '#计划日期', '#python'
            ]})

    def add_record(self, time, tags, content, tags2=None):  # time支持datetime类型和str类型
        """
        添加一个新记录到数据库  {timestamp: 240528150701 ,tags:#测试标签 #记录  content:这是一条测试记录}
        """
        if isinstance(time, datetime):
            formatted_time = time.strftime("%y%m%d%H%M%S")
        else:
            formatted_time = str(time)
            if len(formatted_time) != 12:
                raise ValueError("时间格式错误，请使用220101123456格式")
        tags_list = re.findall(r"#\S+", tags)
        tags_str = ' '.join(tags_list)
        print("tags_str:", tags_str)
        if tags2:
            tags_list2 = re.findall(r"#\S+", tags2)
            print("tags_list2:", tags_list2)
            combined_tags_set = set(tags_list) | set(tags_list2)  # 使用集合的并集操作符
            tags_str = ' '.join(combined_tags_set)

        print("准备保存笔记tags_str:", tags_str, "content:", content)
        # 检查是否存在相同的记录
        existing_record = self.records.get(self.query.timestamp == formatted_time)
        if existing_record:
            # 更新现有记录
            self.records.update({'tags': tags_str, 'content': content}, doc_ids=[existing_record.doc_id])
            print("更新记录:", existing_record.doc_id)
            doc_id = existing_record.doc_id
        else:
            # 插入新记录
            doc_id = self.records.insert({'timestamp': formatted_time, 'tags': tags_str, 'content': content})
            print("插入新记录:", doc_id)
            for tag in tags_list:
                self.add_tag(tag)
        return doc_id

    def update_record(self, records_list):

        """
        更新一个或多个记录
        """
        for record in records_list:
            self.records.update({'tags': record['tags'], 'content': record['content']}, doc_ids=[record['doc_id']])
            print("更新记录:", record['doc_id'])

    def get_records_by_tag(self, tag):
        return self.records.search(self.query.tags.matches(f'.*{tag}.*'))

    def get_records_by_tags(self, tags):  # 查询返回任意符合标签的记录
        tags_list = re.findall(r"#\S+", tags)
        # 构建正则表达式，匹配列表中的任意一个标签
        regex_pattern = '|'.join([f'{tag}' for tag in tags_list])
        print("regex_pattern:", regex_pattern)
        # 使用正则表达式搜索匹配的记录
        matching_records = self.records.search(self.query.tags.matches(regex_pattern))
        return matching_records

    def get_records_by_date(self, start_time, end_time):    # 查询240528163452到240528163452之间的数据
        if isinstance(start_time, datetime):
            formatted_time_start = start_time.strftime("%y%m%d%H%M%S")
        else:
            formatted_time_start = str(start_time)
        if isinstance(end_time, datetime):
            formatted_time_end = end_time.strftime("%y%m%d%H%M%S")
        else:
            formatted_time_end = str(end_time)
        print("formatted_time_start:", formatted_time_start)
        print("formatted_time_end:", formatted_time_end)
        return self.records.search((self.query.timestamp >= formatted_time_start) &
                                   (self.query.timestamp <= formatted_time_end))

    def delete_record(self, time):
        if isinstance(time, datetime):
            formatted_time = time.strftime("%y%m%d%H%M%S")
        else:
            formatted_time = str(time)
        return self.records.remove((self.query.timestamp == formatted_time))

    def add_tag(self, tag):
        """
        向标签列表中添加一个新标签，如果它尚不存在 {labels:['#标签1', '#标签2']}
        """
        # 获取当前的标签列表
        labels_record = self.all_tags.all()[0]  # 假设只有一个标签记录
        labels_list = labels_record['all_tags']
        # 如果标签不在列表中，则添加它
        if tag.startswith('#'):
            if tag not in labels_list:
                labels_list.append(tag)
                self.all_tags.update({'all_tags': labels_list}, doc_ids=[labels_record.doc_id])
                print("add_tag:", tag)

    def get_all_tags(self):
        labels_record = self.all_tags.all()[0]  # 假设只有一个标签记录
        return labels_record['all_tags']

    def save_window_data(self, window_data):
        self.windows.insert(window_data)

    def update_window_data(self, window_id, new_data):
        self.windows.update(new_data, self.query.window_id == window_id)

    def delete_window_data(self, window_id):
        self.windows.remove(self.query.window_id == window_id)

    def get_window_data_by_id(self, window_id):
        result = self.windows.search(self.query.window_id == window_id)
        print("get_window_data_by_id", window_id)
        if result:
            return result[0]
        return None

    def get_window_data_by_time_range(self, start_time_str, end_time_str):
        # 将时间字符串转换为datetime对象
        start_time_int = int(start_time_str)
        end_time_int = int(end_time_str)
        print("start_time:", start_time_int)
        print("end_time:", end_time_int)
        # 筛选出符合时间范围的数据

        results = self.windows.search(
            where('window_id').test(lambda x: start_time_int <= int(x[:12]) <= end_time_int)
            # and print("time:", int(x[:12]),start_time_int <= int(x[:12]) <= end_time_int)
        )
        print("get_window_data_by_time_range results:", results)

        # 返回结果
        return results

    def get_last_summary_date(self):
        summaries = self.get_records_by_tag('#系统日总结')
        if summaries:
            # 假设 summaries 按日期排序，取最后一个
            last_summary = sorted(summaries, key=lambda x : x['timestamp'], reverse=True)[0]
            print("查找到最近的日总结日期:", last_summary['timestamp'])
            return last_summary['timestamp']
        return None

    def get_first_record_date(self):
        first_record = self.records.get(doc_id=1)
        if first_record :
            print("查找到第一条记录日期:", first_record['timestamp'])
            return first_record['timestamp']
        return None



class RecordSearcher:
    def __init__(self):
        self.tinydb = TinyDatabase()
        self.db = self.tinydb.db
        self.query = self.tinydb.query
        self.records = self.tinydb.records

    @staticmethod
    def records_to_text(matching_records):
        """
        将记录列表转换为文本，每条记录占一行。
        """
        return "\n".join(", ".join(f"{key}: {value}"
                                   for key, value in matching_record.items()) for matching_record in matching_records)

    def search_records(self, params):
        tags = params.get("tags", [])
        combine_tags = params.get("combine_tags", "OR")
        start_time = params.get("start_time", "")
        end_time = params.get("end_time", "")
        keywords = params.get("keywords", [])
        combine_keywords = params.get("combine_keywords", "OR")
        print(tags, combine_tags, start_time, end_time, keywords, combine_keywords)
        conditions = []

        if start_time == '':
            start_time = '240601000000'  # 240601000000 表示24年6月1日0点0分0秒
        if end_time == '':
            end_time = '991231235900'     # 991231235900 表示99年12月31日23时59分59秒
        time_condition = lambda record: start_time <= record['timestamp'] <= end_time
        conditions.append(time_condition)
        print(f"Time condition: {start_time} <= record['timestamp'] <= {end_time}")

        if tags:
            if combine_tags == "AND":
                tag_condition = lambda record: all(re.search(re.escape(tag) + r'\b', record['tags']) for tag in tags)
            elif combine_tags == "OR":
                tag_condition = lambda record: any(re.search(re.escape(tag) + r'\b', record['tags']) for tag in tags)
            else:
                tag_condition = None
            if tag_condition:
                conditions.append(tag_condition)
            print(f"Tag condition: {combine_tags} {tags}")

        if keywords:
            if combine_keywords == "AND":
                keyword_condition = lambda record: all(
                    re.search(keyword, record['content'], re.IGNORECASE) for keyword in keywords)
            elif combine_keywords == "OR":
                keyword_condition = lambda record: any(
                    re.search(keyword, record['content'], re.IGNORECASE) for keyword in keywords)
            conditions.append(keyword_condition)
            print(f"Keyword condition: {combine_keywords} {keywords}")

        def combined_condition(record):
            result = all(cond(record) for cond in conditions)
            # print(f"Evaluating record {record['timestamp']}: {result}")
            return result

        matching_records = [record for record in self.records.all() if combined_condition(record)]
        print("Matching records:", matching_records)

        return matching_records


if __name__ == '__main__':
    db = TinyDatabase()
    # timestamp = datetime.now()
    # print("timestamp:", timestamp)
    # db.add_record(timestamp, '#测试标签1 #记录 #内容', '这是一条测试记录')
    # db.add_tag('#测试标签2')
    #
    # time_str = "240528175552"
    #
    # # 将字符串转换为 datetime 对象
    # # %y 表示两位数的年份，%m 表示月份，%d 表示日，%H 表示小时，%M 表示分钟，%S 表示秒
    # time_obj = datetime.strptime(time_str, "%y%m%d%H%M%S")
    # db.add_record(time_str, '#测试标签2 #记录 #内容', '这是一条测试记录2')
    #
    # print("db.get_all_tags()", db.get_all_tags())
    # print("db.get_records_by_tag('#测试标签1')", db.get_records_by_tag('#测试标签1'))
    # # print("db.get_records_by_date", db.get_records_by_date(timestamp, time_str))
    # print("db.get_records_by_date", db.get_records_by_date(timestamp, "240528175552"))
    # print("db.get_records_by_tags('#测试标签1#测试标签2')", db.get_records_by_tags('#测试标签1 #测试标签2'))
    # db.delete_record(timestamp)
    # # print(db.get_all_tags())
    # print("db.get_records_by_date", db.get_records_by_date(timestamp, "240528175552"))

    # db.add_record("240529235801", '#测试标签 #记录', '这是一条测试记录')
    # db.add_record("240529235802", '#测试标签 #记录2', '这是一条测试记录2')
    # db.add_record("240529235803", '#测试 #记录2', '这是一条测试记录3')
    # db.add_record("240529235804", '#测试 #记录', '这是一条测试记录试验4')
    # print("db.get_records_by_time_range()", db.get_records_by_date('240528000000', '240529235905'))
    searcher = RecordSearcher()
    params = {
        "tags": ["读书笔记","阅读","笔记"],
        "combine_tags": "OR",
        "start_time": "240603000000",
        "end_time": "240606235959",
        "keywords": [],
        "combine_keywords": "OR"
    }
    results = searcher.search_records(params)
    params = {
            "tags" : ["#读书笔记", "#阅读", "#笔记"],
            "combine_tags" : "OR",
            "start_time" : "",
            "end_time" : "",
            "keywords" : [],
            "combine_keywords" : "OR"
        }

    results2 = searcher.search_records(params)

    print("Results:", results2)
    # print("Results:", results)
    # print("Results text:", searcher.records_to_text(results))
    # params = {
    #     "tags" : ["#测试标签", "#记录"],
    #     "combine_tags" : "OR",
    #     "start_time" : "240528000000",
    #     "end_time" : "240529235900",
    #     "keywords" : ["测试", "试验"],
    #     "combine_keywords" : "OR"
    # }
    # results = searcher.search_records(params)
    # # print("Results:", results)
    # params = {
    #     "tags" : ["#测试标签", "#记录"],
    #     "combine_tags" : "OR",
    #     "start_time" : "240528000000",
    #     "end_time" : "240528235900",
    #     "keywords" : ["测试", "试验"],
    #     "combine_keywords" : "OR"
    # }
    # results = searcher.search_records(params)
    #
    # params = {
    #     "tags" : ["#测试标签", "#记录2"],
    #     "combine_tags" : "OR",
    #     "start_time" : "240528000000",
    #     "end_time" : "240529235900",
    #     "keywords" : ["测试记录3", "试验"],
    #     "combine_keywords" : "OR"
    # }
    # results = searcher.search_records(params)
