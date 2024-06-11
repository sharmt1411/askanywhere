import re
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
        Available commands:
        ~help               Show this help message
        ~query #标签1 #标签2 AND/OR 关键字1 关键字2 关键字3... AND/OR 240611-240615  (参数可选)
        ~q  用法同上
        ~delete doc_id,doc_id,doc_id...   删除记录，需要重复确认
        ~d doc_id  用法同上
        ~unfinished     240611-240615
        ~其他              ...待补充
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
                content += f"doc_id:{record.doc_id}  {record.get('tags')}  {record.get('content')}\n\n"
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