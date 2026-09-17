"""领域模型。

这个文件是模块 04（面向对象）知识的落地：
IntEnum、dataclass、field(default_factory=...)、__post_init__、property、
以及「值对象」该有的 __eq__ / __hash__ / __repr__。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import IntEnum
from typing import Any

__all__ = ["Priority", "Task"]


class Priority(IntEnum):
    """优先级。用 IntEnum 而不是普通 Enum，是为了能直接比大小和排序。

    取值故意让 HIGH 最大，这样 `sorted(key=lambda t: t.priority, reverse=True)`
    就是「重要的排前面」，符合直觉。

    用 IntEnum 而不是裸整数，是为了防止把 `priority=99` 这种非法值塞进来——
    `Priority(99)` 会直接抛 ValueError。
    """

    LOW = 1
    NORMAL = 2
    HIGH = 3

    @classmethod
    def from_str(cls, text: str) -> Priority:
        """从 'high' / 'HIGH' / 'High' 这样的字符串构造。

        单独抽一个类方法而不是在别处写一堆 if，是因为
        「字符串 <-> 枚举」的映射应该紧挨着枚举定义，改的时候不会漏。
        """
        try:
            return cls[text.strip().upper()]
        except KeyError:
            valid = ", ".join(m.name.lower() for m in cls)
            raise ValueError(f"无效的优先级 {text!r}，可选：{valid}") from None


@dataclass
class Task:
    """一条任务。

    为什么用 @dataclass 而不是手写 __init__：
        手写版本要写 __init__ / __repr__ / __eq__ 三个方法，
        而且加一个字段就要改三处。@dataclass 由字段声明自动生成，
        字段只声明一次。

    为什么 tags 要用 field(default_factory=list) 而不是 tags: list[str] = []：
        后者是模块 03 讲过的可变默认参数陷阱——所有 Task 实例会共享
        同一个列表，往一条任务加标签，其他任务也会跟着变。
        default_factory 让每个实例都调用一次 list() 拿到新列表。
    """

    title: str
    priority: Priority = Priority.NORMAL
    due: date | None = None
    done: bool = False
    tags: list[str] = field(default_factory=list)
    id: int = 0

    def __post_init__(self) -> None:
        """dataclass 生成的 __init__ 末尾会调用它，用来做校验和归一化。

        为什么不用 @dataclass(frozen=True) 之类的约束：
        因为我们既要在构造时校验，又要允许后续修改（比如标记完成），
        所以做成普通可变对象，只是在边界上把关。
        """
        self.title = self.title.strip()
        if not self.title:
            raise ValueError("任务标题不能为空")
        if isinstance(self.priority, str):
            # 允许 Task("x", priority="high") 这种写法
            self.priority = Priority.from_str(self.priority)
        if self.id < 0:
            raise ValueError("id 不能为负数")

    # ------------------------------------------------------------------
    # 派生属性
    # ------------------------------------------------------------------
    @property
    def is_overdue(self) -> bool:
        """是否已逾期。未完成 + 有截止日期 + 日期已过。"""
        return not self.done and self.due is not None and self.due < date.today()

    @property
    def sort_key(self) -> tuple[int, date, str]:
        """排序键：优先级高的在前，同优先级按截止日期早的在前，再按标题。

        把排序规则做成模型自己的属性，而不是散落在各个调用点——
        以后排序规则改了，只改这一处。
        """
        # date 不能取负，所以用 date.max 兜住「没有截止日期」，让它排最后
        return (-int(self.priority), self.due or date.max, self.title)

    # ------------------------------------------------------------------
    # 序列化
    # ------------------------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        """转成能直接被 json.dump 处理的普通字典。

        注意 date 不能直接 JSON 序列化，必须转成 ISO 格式字符串。
        这一步放在模型里做，调用方就不需要知道这个细节了。
        """
        return {
            "id": self.id,
            "title": self.title,
            "priority": self.priority.name,
            "due": self.due.isoformat() if self.due else None,
            "done": self.done,
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Task:
        """从字典还原。和 to_dict 是一对，必须成对维护。"""
        due_raw = data.get("due")
        return cls(
            title=data["title"],
            priority=Priority.from_str(data.get("priority", "NORMAL")),
            due=date.fromisoformat(due_raw) if due_raw else None,
            done=bool(data.get("done", False)),
            tags=list(data.get("tags", [])),
            id=int(data.get("id", 0)),
        )


# 说明：@dataclass 默认生成的 __eq__ 比较所有字段，__repr__ 会打印所有字段，
# 对值对象来说这两件事都是想要的，所以不用自己写。
#
# 但有一点要注意：@dataclass 默认 eq=True 会把 __hash__ 设成 None，
# 于是 Task 实例**不能放进 set、也不能当 dict 的键**。
# 需要的话加 @dataclass(eq=True, frozen=True)（不可变 + 可哈希），
# 或者手动写 __hash__。模块 04 的练习里踩过这个坑。
