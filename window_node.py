
from tinydatabase import TinyDatabase


class WindowNode:
    def __init__(self, window_id, parent_window_id, select, question, context, children_windows=None):

        self.window_id = window_id
        self.parent_window_id = parent_window_id
        self.select = select
        self.question = question
        self.context = context
        self.children_windows = children_windows or []

    def to_dict(self):
        return {
            "window_id": self.window_id,
            "parent_window": self.parent_window_id,
            "select": self.select,
            "question": self.question,
            "context": self.context,
            "children_windows": self.children_windows
        }
    # 一般只有context会变化，更新不要更新chilidren_windows，只更新context，因为子节点保存会自动更新父节点的children_windows列表

    @classmethod
    def from_dict(cls, window_data):
        window_id = window_data["window_id"]
        parent_window = window_data.get("parent_window", "")
        select = window_data.get("select", "")
        question = window_data.get("question", "")
        context = window_data.get("context", "")
        children_windows = window_data.get("children_windows", [])
        # children_windows = [cls.from_dict(child_data) for child_data in children_data]
        return cls(window_id, parent_window, select, question, context, children_windows)

    def save_window_node(self):
        print("准备保存窗口Node数据:", self.window_id)
        old = WindowNode.get_window_node_by_id(self.window_id)
        if old is not None:   # 窗口ID已存在，更新窗口数据
            print("窗口ID已存在，尝试更新窗口数据:", self.window_id)
            self.update_window_node({"context": self.context})
            return True
        else:
            if self.parent_window_id:             # 如果父窗口存在，需要更新父窗口的children_windows列表
                if self.parent_window_id == "root" or self.parent_window_id == "none":
                    print("准备保存root窗口")
                elif self.parent_window_id == "daywindow":
                    print("准备保存daywindow窗口")
                else:
                    print("存在父窗口，准备更新父窗口的children_windows列表")
                    new_parent_node = self.get_window_node_by_id(self.parent_window_id)
                    if new_parent_node:
                        if self.window_id in new_parent_node.children_windows:
                            print("新父窗口子窗口已存在，更新窗口数据")
                        else:
                            new_parent_node.children_windows.append(self.window_id)
                            new_parent_node.update_window_node({"children_windows": new_parent_node.children_windows})
                            print("新增父窗口，更新父窗口的子窗口")
                    else:
                        print("保存的父窗口无记录，请检查数据，未保存")
                        return False
            tinydb = TinyDatabase()
            tinydb.save_window_data(self.to_dict())
            print("保存窗口数据成功：", self.window_id)
            return True

    def update_window_node(self, data_dict):    # 更新窗口数据，如果父窗口发生变化，需要更新父窗口的children_windows列表,删除旧的父窗口子窗口记录
        print("准备更新窗口Node数据,首先检测更新是否正确，父窗口是否变更，id:", self.window_id)  #本程序中默认只允许变更子节点，和内容
        old_child = WindowNode.get_window_node_by_id(self.window_id)
        print("旧的子窗口记录", old_child.children_windows)
        if self.parent_window_id == old_child.parent_window_id:  # 父窗口未发生变化，更新父窗口的子窗口数据
            tinydb = TinyDatabase()
            tinydb.update_window_data(self.window_id, data_dict)
            print("更新窗口数据成功：", self.window_id, "，更新内容：", data_dict.keys())
            return True
        else:  # 父窗口发生变化，新增新父窗口的children_windows列表，删除旧的父窗口子窗口记录，,
            new_parent_node = self.get_window_node_by_id(self.parent_window_id)
            if new_parent_node:
                new_parent_node.children_windows.append(self.window_id)
                new_parent_node.update_window_node({"children_windows": new_parent_node.children_windows})
                print("父窗口变化，增加新父窗口子窗口")
            else:
                print("新纪录的父窗口无记录，请检查数据，本次无法保存")
                return False
            old_parent_node = self.get_window_node_by_id(old_child.parent_window_id)  # 找到旧父窗口的记录，并删除子窗口
            if old_parent_node:
                print("旧父节点,及其子窗口记录", old_parent_node.window_id, old_parent_node.children_windows)
                old_parent_node.children_windows.remove(self.window_id)
                old_parent_node.update_window_node({"children_windows": old_parent_node.children_windows})
            else:
                print("旧时的父窗口无记录，无法删除原有子节点，请检查数据，但新窗口的父窗口已继续更新")
        tinydb = TinyDatabase()
        tinydb.update_window_data(self.window_id, self.to_dict())
        return True

    def delete_window_node(self):
        tinydb = TinyDatabase()
        tinydb.delete_window_data(self.window_id)

    @staticmethod
    def get_window_node_by_id(window_id):
        tinydb = TinyDatabase()
        result = tinydb.get_window_data_by_id(window_id)
        if result:
            return WindowNode.from_dict(result)
        return None


    @staticmethod
    def get_window_nodes_by_parent_id(parent_id):
        nodes = []
        tinydb = TinyDatabase()
        result_data = tinydb.get_window_data_by_id(parent_id)
        if result_data:
            result_node = WindowNode.from_dict(result_data)
            nodes.append(result_node)
            if result_node.children_windows:
                for child_id in result_node.children_windows:
                    child_node = WindowNode.get_window_nodes_by_parent_id(child_id)
                    nodes.extend(child_node)
        return nodes

    @staticmethod
    def find_window_node_by_time_range(start_time_str, end_time_str):  # 240517121011
        tinydb = TinyDatabase()
        result_data = tinydb.get_window_data_by_time_range(start_time_str, end_time_str)
        result_node = []
        for window_data in result_data:
            result_node.append(WindowNode.from_dict(window_data))
        return result_node


if __name__ == "__main__":
    # Example usage:
    print(WindowNode.get_window_nodes_by_parent_id("240531000000:000:000"))
    # window_datas = [
    #     {
    #         "window_id": "240517145901:110:120",  # 窗口ID:x:y
    #         "parent_window": "",
    #         "select": "example_select3",
    #         "question": "example_question3",
    #         "context": "第一个窗口",
    #         "children_windows": [
    #             "240517154902:110:120", "240517155902:110:120"
    #         ]
    #     },
    #     {
    #         "window_id": "240517154902:110:120",
    #         "parent_window": "240517145901:110:120",
    #         "select": "example_select4",
    #         "question": "example_question4",
    #         "context": "第二个窗口，第一个子窗口",
    #         "children_windows": []
    #     },
    #     {
    #         "window_id": "240517155902:110:120",
    #         "parent_window": "240517145901:110:120",
    #         "select": "example_select5",
    #         "question": "example_question5",
    #         "context": "第三个窗口，第一个的第二个子窗口",
    #         "children_windows": []
    #     }
    # ]
    # for data in window_datas:
    #     window_node = WindowNode.from_dict(data)
    #     window_node.save_window_node()
    # print("导入数据完成")
    # # 测试新增节点带父节点
    # WindowNode.find_window_node_by_time_range("200101000000", "250101000000")
    # window_node = WindowNode("240517165901:110:120", "240517155902:110:120", "example_select3", "example_question3",
    #                          "第四个窗口，第三个的子窗口")
    # window_node.save_window_node()
    # print("新增子窗口测试完成")
    # WindowNode.find_window_node_by_time_range(200101000000, 250101000000)
    # print(WindowNode.get_window_node_by_id("240517165901:110:120"))
    #
    # # 测试错误父节点不保存
    # window_node = WindowNode("240517165901:110:120", "240517155903:110:120", "example_select3", "example_question3",
    #                          "测试父窗口出错")
    # window_node.save_window_node()
    #
    # # 测试父节点更改
    # window_node = WindowNode("240517165901:110:120", "240517145901:110:120", "example_select3", "example_question3",
    #                          "测试父窗口更改")
    # window_node.save_window_node()
    # print("父节点不一致处理测试完成")
    # WindowNode.find_window_node_by_time_range(200101000000, 250101000000)

