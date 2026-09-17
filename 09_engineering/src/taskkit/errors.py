"""异常层次。

设计原则（模块 06 讲过）：
    1. 库应该有**自己的**顶层异常基类，这样调用方可以
       `except taskkit.TaskKitError` 一次兜住所有本库的异常，
       而不会误捕到别的库或者标准库抛的异常。
    2. 所有自定义异常都继承 Exception，不要继承 BaseException。
    3. 层次不要太深，两三层就够。过深的继承树没人记得住。
"""

from __future__ import annotations


class TaskKitError(Exception):
    """本库所有异常的基类。调用方只需要记住这一个名字。"""


class TaskNotFound(TaskKitError):
    """找不到指定 id 的任务。

    注意这里**没有**去继承 KeyError。
    虽然语义上像「键不存在」，但 KeyError 的 str() 会加一层引号
    （KeyError("x") 打印出来是 "'x'"），而且会让调用方误以为
    这真的是个字典查找失败。异常类型应该表达语义，不是复用实现。
    """

    def __init__(self, task_id: int) -> None:
        super().__init__(f"找不到 id 为 {task_id} 的任务")
        self.task_id = task_id  # 把结构化信息留给调用方，别只给字符串


class DuplicateTask(TaskKitError):
    """同一个标题的任务已经存在。"""

    def __init__(self, title: str) -> None:
        super().__init__(f"任务已存在：{title}")
        self.title = title


class StoreCorrupted(TaskKitError):
    """存储文件损坏，无法解析。

    实际项目里这类异常应该把底层异常用 `raise ... from exc` 串起来，
    这样 traceback 里能同时看到「文件坏了」和「JSON 解析在哪一行失败」。
    见 store.py 里的用法。
    """
