"""Task 和 Priority 的单元测试。

命名约定：文件名 test_*.py，函数名 test_*，这样 pytest 才能发现它们。
（可以在 pyproject.toml 里改 python_files / python_functions，但没必要。）
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from taskkit.models import Priority, Task


# ----------------------------------------------------------------------
# 基本的 assert —— pytest 会重写它
# ----------------------------------------------------------------------
def test_默认优先级是_normal() -> None:
    """中文函数名也能跑，pytest 完全支持。

    不过团队协作时还是建议用英文——不是技术限制，是「谁都得能读」的问题。
    """
    assert Task("写代码").priority is Priority.NORMAL


def test_标题首尾空白会被去掉() -> None:
    assert Task("  写代码  ").title == "写代码"


def test_空标题抛_value_error() -> None:
    # pytest.raises 是上下文管理器：块内的代码必须抛出指定异常，否则测试失败
    with pytest.raises(ValueError, match="不能为空"):
        Task("   ")


# ----------------------------------------------------------------------
# 参数化：一份逻辑测多组数据
# ----------------------------------------------------------------------
@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("high", Priority.HIGH),
        ("HIGH", Priority.HIGH),
        ("  High  ", Priority.HIGH),
        ("normal", Priority.NORMAL),
        ("low", Priority.LOW),
    ],
)
def test_优先级字符串解析(raw: str, expected: Priority) -> None:
    """@pytest.mark.parametrize 会把一条测试展开成 5 条。

    失败时 pytest 会告诉你具体是哪一组参数挂的，比在函数里写循环好得多：
        test_优先级字符串解析[high-Priority.HIGH] PASSED
        test_优先级字符串解析[LOW-Priority.LOW]   PASSED
    """
    assert Priority.from_str(raw) is expected


def test_非法优先级字符串会给出可选值() -> None:
    with pytest.raises(ValueError, match="可选"):
        Priority.from_str("urgent")


# ----------------------------------------------------------------------
# 那条最容易踩的坑：可变默认值
# ----------------------------------------------------------------------
def test_两个实例的标签列表是独立的() -> None:
    """这条测试守的是 field(default_factory=list)。

    如果哪天有人把 `tags: list[str] = field(default_factory=list)`
    改成 `tags: list[str] = []`，这条测试会立刻变红。
    这就是「回归测试」的价值：把曾经的 bug 钉死在测试里。
    """
    a = Task("a")
    b = Task("b")
    a.tags.append("x")
    assert b.tags == [], "两个实例共享了同一个列表——可变默认值陷阱"


# ----------------------------------------------------------------------
# 边界：日期相关的派生属性
# ----------------------------------------------------------------------
def test_逾期判定() -> None:
    yesterday = date.today() - timedelta(days=1)
    tomorrow = date.today() + timedelta(days=1)

    assert Task("过期了", due=yesterday).is_overdue is True
    assert Task("还没到", due=tomorrow).is_overdue is False
    assert Task("没日期").is_overdue is False, "没有截止日期就不算逾期"
    assert Task("已完成的过期任务", due=yesterday, done=True).is_overdue is False, (
        "已完成的任务不该再算逾期"
    )


def test_排序键把重要且紧急的排在前面() -> None:
    today = date.today()
    tasks = [
        Task("低优先级", priority=Priority.LOW),
        Task("高优先级无日期", priority=Priority.HIGH),
        Task("高优先级明天", priority=Priority.HIGH, due=today + timedelta(days=1)),
    ]
    order = [t.title for t in sorted(tasks, key=lambda t: t.sort_key)]
    assert order == ["高优先级明天", "高优先级无日期", "低优先级"], order


# ----------------------------------------------------------------------
# 序列化往返
# ----------------------------------------------------------------------
def test_to_dict_再_from_dict_应该还原出相等的对象() -> None:
    """这类「往返测试」是序列化代码的基本功。

    只测 to_dict 的输出长什么样是不够的——那样改一个字段就要改测试。
    测「round trip 之后还相等」，既稳定又能发现真正的 bug。
    """
    original = Task(
        "写实验报告",
        priority=Priority.HIGH,
        due=date(2026, 10, 1),
        tags=["学校", "紧急"],
        id=7,
    )
    restored = Task.from_dict(original.to_dict())
    assert restored == original
    assert restored.due == date(2026, 10, 1)


def test_from_dict_能处理缺省字段() -> None:
    """外部数据总是可能缺字段——读取时要给默认值，不要假设格式完整。"""
    task = Task.from_dict({"title": "只有标题"})
    assert task.priority is Priority.NORMAL
    assert task.due is None
    assert task.done is False
    assert task.tags == []
