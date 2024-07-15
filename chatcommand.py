import re

from markdown2 import markdown

from tinydatabase import RecordSearcher, TinyDatabase


class ChatCommandTool:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ChatCommandTool, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.commands = {
            "help": self.help,
            "query": self.query,
            "q": self.query,
            "d": self.delete_record,
            "delete":self.delete_record,

        }
        self.delete_id_list = []
        self._initialized = True

    def parse_command(self, user_input):
        if not user_input.startswith("~"):
            return "请以~开头输入命令."

        command_line = user_input[1:].strip()  # 移除开头的 ~ 和 空格
        command_parts = command_line.split()  # 分割命令和参数
        command = command_parts[0]
        args = command_parts[1:]

        if command in self.commands:
            return self.commands[command](args)
        else:
            return f"未知命令: {command}. 输入 ~help 获取命令列表及参数."

    def help(self, args):
        help_text = """
        目前支持的指令如下:
        ~help               Show this help message
        ~query #标签1 #标签2 AND/OR 关键字1 关键字2 关键字3... AND/OR 240611-240615  (参数可选)
               查询某段日期下，带有标签或含有关键字的记录。
        ~q  用法同上
        ~delete doc_id,doc_id,doc_id...   删除记录，需要重复确认，doc_id用逗号分隔。为查询出来的记录的doc_id。
        ~d doc_id  用法同上
        ~unfinished     240611-240615
        ~其他              ...待补充...
        
        功能说明：
        -划词查询：本质新开对话与AI沟通，支持在弹出的窗口进一步划词查询，建议最后关闭最早打开的窗口，因为目前总结为第一次划词打开的窗口为根窗口，以此为依据进行AI总结。
        -主界面：指令输入，笔记，根据笔记沟通，复习，综合来讲就是主要功能展示
        -笔记保存： 输入#自定义标签 内容，即可保存为笔记，支持命令行查询，以及调用AI查询（目前精度有限）
        -复习： 使用艾宾浩斯遗忘曲线原理，周期复习当天#学习笔记 标签的内容，以及AI总结出来当天的学习知识点。
        -总结：每天首次启动软件，会在后台执行之前未完成的日总结任务及日学习记录总结，由于AI速率有限，一般需要1-2分钟执行1天的总结
        -命令行功能：当前界面，直接操作函数，目前实现上述查询删除功能，在ai能力有限的情况下，实现精确功能的替代方案，后续会增加更多功能。 
        -数据存储： 目前存储在本地，包含tiny_data.json,存储笔记及行为记录。review_record.json,存储复习进度。config配置AI-接口apikey等信息。
        
        API接口：目前支持openai及deepseek，后续会增加更多接口。建议使用deepseek，成本低。
        """
        return help_text

    def query(self, args) :
        tags, keywords, date_range = [], [], None
        combine_tags, combine_keywords = "OR", "OR"

        if isinstance(args, list) :
            args = ' '.join(args)

        # Extract tags
        tag_pattern = re.compile(r'#\w+')
        tags = tag_pattern.findall(args)
        args = tag_pattern.sub('', args).strip()

        # Extract date range
        date_pattern = re.compile(r'\d{6}-\d{6}')
        date_match = date_pattern.search(args)
        if date_match :
            date_range = date_match.group()
            args = date_pattern.sub('', args).strip()

        # Split remaining args by spaces
        parts = args.split()

        # Determine combine_tags if tags exist
        if tags :
            if "AND" in parts :
                combine_tags = "AND"
                parts.remove("AND")
            elif "OR" in parts :
                combine_tags = "OR"
                parts.remove("OR")

        # Determine combine_keywords
        if "AND" in parts :
            combine_keywords = "AND"
        elif "OR" in parts :
            combine_keywords = "OR"

        # Remove the first occurrence of AND/OR for keywords if it exists
        if combine_keywords in parts :
            parts.remove(combine_keywords)

        keywords = parts

        # Process date range
        start_time, end_time = "240601000000", "990101235959"
        if date_range :
            start_date, end_date = date_range.split('-')
            start_time = f"{start_date}000000"
            end_time = f"{end_date}235959"

        query_dict = {
            "tags" : tags,
            "combine_tags" : combine_tags,
            "start_time" : start_time,
            "end_time" : end_time,
            "keywords" : keywords,
            "combine_keywords" : combine_keywords
        }
        searcher = RecordSearcher()
        result = searcher.search_records(query_dict)
        if result :
            content = ""
            for record in result :
                # print(record)
                record_content = record.get('content')
                # 处理无法转换makedown的异常内容
                if record_content :
                    try :
                        html_note = markdown(record_content, extras=["fenced-code-blocks", "code-friendly", "mathjax",
                                                           "tables", "strike", "task_list", "cuddled-lists"])
                    except Exception as e :
                        replacements = {
                            '`' : '',  # 替换反引号
                            '*' : '',  # 替换星号
                            '_' : '',  # 替换下划线
                            '-' : '',  # 替换连字符
                            '~' : '',  # 替换波浪号
                            '>' : 'gt',  # 替换大于号
                            '<' : 'lt',  # 替换小于号
                            '&' : 'and',  # 替换和号
                        }
                        # '#': '',  # 替换井号
                        # '[': '',  # 替换左方括号
                        # ']': '',  # 替换右方括号
                        # '(': '',  # 替换左圆括号
                        # ')': '',  # 替换右圆括号
                        for key, value in replacements.items() :
                            record_content = record_content.replace(key, value)
                        print("chatcommand查询记录无法转换md格式", e)

                content += f"doc_id:{record.doc_id}  {record.get('timestamp')} {record.get('tags')}  {record_content}\n\n"
            # print(content)
        else :
            content = "未找到相关记录."

        return content

    def delete_record(self, args) :
        if isinstance(args, list) :
            args_str = ' '.join(args)
        else :
            args_str = args
        to_delete_list = []
        if not args_str :
            return "请输入要删除的记录的doc_id."
        # print("args-string", args)
        try :
            args_str = args_str.replace('，', ',')
            # print("args", args)

            args_list = args_str.split(',')

            print("args-list", args_list)

            for doc_id in args_list:
                # print("doc_id", doc_id)
                if doc_id.strip().isdigit() :
                    to_delete_list.append(int(doc_id.strip()))

            print("to_delete_list", to_delete_list)
        except ValueError :
            print(ValueError)
            return "输入包含无效的doc_id，请输入有效的doc_id."

        if not to_delete_list :
            return "无效的doc_id，请输入有效的doc_id."

        tinydb = TinyDatabase()
        deleted_id = []

        if self.delete_id_list :
            print("self.delete_id_list", self.delete_id_list)
            for doc_id in to_delete_list:
                if doc_id in self.delete_id_list:
                    removed = tinydb.delete_record_by_id(doc_id)
                    if removed :
                        deleted_id.append(doc_id)
            self.delete_id_list = []
            return f"已删除记录: {deleted_id}."
        else:
            self.delete_id_list = to_delete_list
            return f"请确认要删除的记录的doc_id: {to_delete_list}，再次执行删除以确认。"


# Example usage
if __name__ == "__main__":
    tool = ChatCommandTool()
    while True:
        user_input = input("You: #")
        # print(f"User: {user_input}")
        response = tool.parse_command(user_input)
        print(f"Bot: {response}")