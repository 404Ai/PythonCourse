"""
taskkit —— 课程演示用的小型任务管理库。

这个包是模块 09 的「标本」：它不大，但结构是完整的——
有模型、有持久化、有命令行入口、有测试。
所有工程化的知识点都落在它身上。

注意这里的 `__all__`：它定义了 `from taskkit import *` 会导出什么，
同时也是给类型检查器和文档工具看的「公开 API 清单」。
不在 `__all__` 里的名字（比如 `errors`）算实现细节。
"""

from __future__ import annotations

from taskkit.errors import TaskKitError, TaskNotFound
from taskkit.models import Priority, Task
from taskkit.store import TaskStore

__version__ = "0.1.0"

__all__ = [
    "Priority",
    "Task",
    "TaskKitError",
    "TaskNotFound",
    "TaskStore",
    "__version__",
]
