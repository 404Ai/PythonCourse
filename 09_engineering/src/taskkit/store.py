"""持久化层：把任务存成 JSON 文件。

设计要点：
    1. **存储细节不泄漏给调用方**。上层只看到 add/complete/remove/list_tasks，
       不知道底下是 JSON 还是 SQLite。以后要换成数据库，改这一个文件就行。
    2. **写文件要原子**。直接 write_text 的话，写到一半断电/崩溃，
       原文件就被截断了，数据全丢。做法是先写临时文件再 os.replace。
    3. **异常要带上下文**。JSON 解析失败时用 `raise ... from exc` 串起原始异常。
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import TypedDict

from taskkit.errors import DuplicateTask, StoreCorrupted, TaskNotFound
from taskkit.models import Priority, Task

__all__ = ["StoreStats", "TaskStore"]


class StoreStats(TypedDict):
    """stats() 的返回结构。

    为什么要专门定义这个类型，而不是返回 dict[str, object]：
        dict[str, object] 等于放弃了类型信息 —— 调用方写
        `stats["by_priority"].items()` 时，mypy 只知道它是 object，
        会直接报错，逼得你写 `# type: ignore` 把类型检查关掉。

    用了 TypedDict 之后：
        - 每个键的名字和类型都是确定的，写错键名或类型立刻报错
        - 调用方不需要任何 type: ignore
        - 它仍然是**普通 dict**，零运行时开销，可以直接 json.dumps

    这就是「用类型把契约写下来」的价值：不是为了好看，
    是为了让工具能在你写错的那一瞬间就告诉你。
    """

    total: int
    done: int
    overdue: int
    by_priority: dict[str, int]


class TaskStore:
    """任务集合 + 文件持久化。"""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._tasks: dict[int, Task] = {}
        self._next_id = 1
        self.load()

    # ------------------------------------------------------------------
    # 读写
    # ------------------------------------------------------------------
    def load(self) -> None:
        """从磁盘读取。文件不存在就当成空库，不报错。

        「文件不存在」和「文件损坏」必须区分对待：
        前者是正常情况（第一次用），后者必须让用户知道，否则会静默丢数据。
        """
        if not self.path.exists():
            self._tasks = {}
            self._next_id = 1
            return

        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            # `from exc` 把原始异常挂在 __cause__ 上，
            # traceback 里会显示 "The above exception was the direct cause of..."
            # 不写 from 的话信息就断了，排查时只能看到 StoreCorrupted。
            raise StoreCorrupted(f"存储文件不是合法 JSON：{self.path}") from exc

        try:
            self._tasks = {int(item["id"]): Task.from_dict(item) for item in raw["tasks"]}
        except (KeyError, TypeError, ValueError) as exc:
            raise StoreCorrupted(f"存储文件结构不对：{self.path}") from exc

        self._next_id = max(self._tasks, default=0) + 1

    def save(self) -> None:
        """原子写入：先写临时文件，再整体替换。

        为什么不能直接 write_text：
            写入不是原子的。如果进程在写到一半时被杀掉（Ctrl+C、断电、OOM），
            原文件会变成半截 JSON —— 下次启动直接 StoreCorrupted，数据全丢。
            os.replace 在同一个文件系统内是原子操作，要么全换要么不换。

        Windows 注意：os.replace 可以覆盖已存在的目标文件（os.rename 不行）。
        """
        payload = {"version": 1, "tasks": [t.to_dict() for t in self._ordered()]}
        text = json.dumps(payload, ensure_ascii=False, indent=2)

        self.path.parent.mkdir(parents=True, exist_ok=True)
        # 临时文件必须和目标在同一个目录，否则跨文件系统的 replace 不是原子的
        fd, tmp_name = tempfile.mkstemp(dir=self.path.parent, suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(text)
            os.replace(tmp_name, self.path)
        except BaseException:
            # 中途出任何问题都要把临时文件清掉，别留垃圾
            Path(tmp_name).unlink(missing_ok=True)
            raise

    # ------------------------------------------------------------------
    # 增删改查
    # ------------------------------------------------------------------
    def add(
        self,
        title: str,
        *,
        priority: Priority | str = Priority.NORMAL,
        due: date | None = None,
        tags: list[str] | None = None,
    ) -> Task:
        """新增任务。标题重复时抛 DuplicateTask。

        注意 priority / due / tags 前面那个 `*`：它们全是 keyword-only。
        这个 API 里有三个可选参数，强制关键字传参能杜绝
        `add("写代码", True)` 这种「True 到底是什么」的调用。
        """
        task = Task(
            title=title,
            priority=Priority.from_str(priority) if isinstance(priority, str) else priority,
            due=due,
            tags=list(tags or []),
            id=self._next_id,
        )
        if any(t.title == task.title for t in self._tasks.values()):
            raise DuplicateTask(task.title)

        self._tasks[task.id] = task
        self._next_id += 1
        self.save()
        return task

    def complete(self, task_id: int) -> Task:
        """标记完成。找不到就抛 TaskNotFound。"""
        task = self._get(task_id)
        task.done = True
        self.save()
        return task

    def remove(self, task_id: int) -> Task:
        """删除并返回被删掉的那条。"""
        task = self._get(task_id)
        del self._tasks[task_id]
        self.save()
        return task

    def get(self, task_id: int) -> Task:
        return self._get(task_id)

    def list_tasks(
        self,
        *,
        include_done: bool = False,
        tag: str | None = None,
        overdue_only: bool = False,
    ) -> list[Task]:
        """按 sort_key 排好序返回。所有过滤参数都是 keyword-only。

        ── 为什么这个方法叫 list_tasks 而不是 list ──

        因为它一开始就叫 `list`，然后 mypy 报了三条错：

            error: Function "TaskStore.list" is not valid as a type
            error: "list?[Task]" has no attribute "__iter__"

        原因是：**类体内定义的方法名会遮蔽同名的内置函数。**
        在 class 的命名空间里，`list` 这个名字在 `def list(...)` 之后
        就指向那个方法了。于是本类里其他方法的 `-> list[Task]` 注解，
        被 mypy 解析成了「方法 list 用作类型」，直接报错。

        这是「用内置类型名给方法命名」的通病：
            store.list() / store.dict() / store.set() / store.type()
        都会踩到。运行时没事，但静态检查器会迷糊，
        而且读代码的人也要多想一秒「这个 list 是内置的还是你的」。

        两条出路：
            a. 换个名字（本例采用）—— 最省事，也最不容易让后来人踩坑
            b. 保留 list，把注解改成模块级别的类型别名

        选 a 是因为可读性优先：`store.list_tasks()` 一眼就知道是「列出任务」，
        `store.list()` 还得结合上下文才知道列的是什么。
        """
        result = [t for t in self._tasks.values() if include_done or not t.done]
        if tag is not None:
            result = [t for t in result if tag in t.tags]
        if overdue_only:
            result = [t for t in result if t.is_overdue]
        return sorted(result, key=lambda t: t.sort_key)

    def stats(self) -> StoreStats:
        """汇总统计，给 CLI 的 stats 子命令用。"""
        all_tasks = list(self._tasks.values())
        by_priority = Counter(t.priority.name for t in all_tasks)
        return {
            "total": len(all_tasks),
            "done": sum(1 for t in all_tasks if t.done),
            "overdue": sum(1 for t in all_tasks if t.is_overdue),
            "by_priority": {p.name: by_priority.get(p.name, 0) for p in Priority},
        }

    # ------------------------------------------------------------------
    # 内部
    # ------------------------------------------------------------------
    def _get(self, task_id: int) -> Task:
        try:
            return self._tasks[task_id]
        except KeyError:
            raise TaskNotFound(task_id) from None

    def _ordered(self) -> list[Task]:
        return sorted(self._tasks.values(), key=lambda t: t.id)

    def __len__(self) -> int:
        return len(self._tasks)

    def __contains__(self, task_id: object) -> bool:
        return task_id in self._tasks
