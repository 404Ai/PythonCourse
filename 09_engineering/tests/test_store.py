"""TaskStore 的测试：增删改查、持久化、异常。"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest

from taskkit.errors import DuplicateTask, StoreCorrupted, TaskNotFound
from taskkit.models import Priority, Task
from taskkit.store import TaskStore


# ----------------------------------------------------------------------
# 增
# ----------------------------------------------------------------------
def test_add_会分配递增的_id(store: TaskStore) -> None:
    first = store.add("甲")
    second = store.add("乙")
    assert (first.id, second.id) == (1, 2)
    assert len(store) == 2


def test_add_拒绝重复标题(filled_store: TaskStore) -> None:
    with pytest.raises(DuplicateTask):
        filled_store.add("买牛奶")


def test_add_的字符串优先级会被转成枚举(store: TaskStore) -> None:
    task = store.add("写代码", priority="high")
    assert task.priority is Priority.HIGH


# ----------------------------------------------------------------------
# 改 / 删
# ----------------------------------------------------------------------
def test_complete_标记完成(filled_store: TaskStore) -> None:
    task = filled_store.complete(2)
    assert task.done is True
    assert all(t.id != 2 for t in filled_store.list_tasks())


def test_操作不存在的_id_抛_task_not_found(store: TaskStore) -> None:
    for operation in (store.complete, store.remove, store.get):
        with pytest.raises(TaskNotFound, match="999"):
            operation(999)


def test_task_not_found_带着结构化的_id() -> None:
    """异常除了消息，还应该带上结构化数据，方便调用方程序化处理。"""
    exc = TaskNotFound(42)
    assert exc.task_id == 42


# ----------------------------------------------------------------------
# 查
# ----------------------------------------------------------------------
def test_list_默认不返回已完成的任务(filled_store: TaskStore) -> None:
    """注意 list_tasks() 返回的是**排好序**的，不是插入顺序。

    三条任务的优先级分别是 HIGH(1) / LOW(2) / NORMAL(3)，
    所以按 sort_key（优先级降序）排出来是 1, 3, 2。

    这条测试第一次写的时候我断言成了 [1, 2, 3]（插入顺序），跑挂了才想起来。
    这正好说明「测试失败不一定是代码错，也可能是测试写错了」——
    先搞清楚契约是什么，再决定改哪边。
    """
    filled_store.complete(2)
    assert [t.id for t in filled_store.list_tasks()] == [1, 3]
    assert [t.id for t in filled_store.list_tasks(include_done=True)] == [1, 3, 2]
    assert len(filled_store.list_tasks(include_done=True)) == 3


def test_list_按标签过滤(filled_store: TaskStore) -> None:
    assert [t.title for t in filled_store.list_tasks(tag="学校")] == ["写实验报告", "复习期末"]
    assert filled_store.list_tasks(tag="不存在") == []


def test_list_按截止日期过滤逾期(filled_store: TaskStore) -> None:
    overdue = filled_store.list_tasks(overdue_only=True)
    assert [t.title for t in overdue] == ["写实验报告"]


def test_list_排序是优先级优先(filled_store: TaskStore) -> None:
    titles = [t.title for t in filled_store.list_tasks()]
    assert titles == ["写实验报告", "复习期末", "买牛奶"], titles


def test_stats_汇总(filled_store: TaskStore) -> None:
    filled_store.complete(2)
    stats = filled_store.stats()
    assert stats["total"] == 3
    assert stats["done"] == 1
    assert stats["overdue"] == 1
    assert stats["by_priority"] == {"HIGH": 1, "NORMAL": 1, "LOW": 1}


# ----------------------------------------------------------------------
# 持久化
# ----------------------------------------------------------------------
def test_数据会写进文件并且能被新实例读回来(store: TaskStore, db_path: Path) -> None:
    """这是本项目里最重要的一条测试。

    它测的不是「save 被调用了」，而是**可观察的行为**：
    换一个实例重新打开，数据还在。
    测行为而不是测实现，代码重构时测试才不会碎。
    """
    store.add("写实验报告", priority=Priority.HIGH, due=date(2026, 10, 1), tags=["学校"])

    reopened = TaskStore(db_path)  # 全新的实例，只能从文件里读
    assert len(reopened) == 1
    task = reopened.get(1)
    assert task.title == "写实验报告"
    assert task.priority is Priority.HIGH
    assert task.due == date(2026, 10, 1)
    assert task.tags == ["学校"]


def test_重新打开后_id_不会重复(store: TaskStore, db_path: Path) -> None:
    store.add("甲")
    store.add("乙")

    reopened = TaskStore(db_path)
    third = reopened.add("丙")
    assert third.id == 3, "新实例应该接着已有的最大 id 往下发"


def test_中文不会被转义成_unicode_转义序列(store: TaskStore, db_path: Path) -> None:
    """json.dumps 默认 ensure_ascii=True，中文会变成 \\uXXXX。

    功能上没区别，但文件变得没法用肉眼读，也没法直接 diff。
    中文项目里应该一律 ensure_ascii=False。
    """
    store.add("写实验报告")
    raw = db_path.read_text(encoding="utf-8")
    assert "写实验报告" in raw
    assert "\\u" not in raw


def test_文件不存在时当作空库不报错(tmp_path: Path) -> None:
    assert len(TaskStore(tmp_path / "从来没存在过.json")) == 0


def test_文件损坏时抛_store_corrupted(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{ 这不是合法的 JSON", encoding="utf-8")
    with pytest.raises(StoreCorrupted):
        TaskStore(bad)


def test_结构不对时也抛_store_corrupted(tmp_path: Path) -> None:
    """JSON 合法但结构不对（缺 tasks 键）也要给出明确的异常，而不是 KeyError。"""
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps({"wrong": "shape"}), encoding="utf-8")
    with pytest.raises(StoreCorrupted):
        TaskStore(bad)


def test_写入是原子的_不会残留临时文件(store: TaskStore, db_path: Path) -> None:
    """save 用的是「写临时文件 + os.replace」。

    这个测试守两件事：
      1. 目录里不留下 *.tmp 垃圾
      2. 目标文件内容是完整合法的 JSON
    """
    store.add("甲")
    store.add("乙")

    leftovers = list(db_path.parent.glob("*.tmp"))
    assert leftovers == [], f"残留了临时文件：{leftovers}"

    payload = json.loads(db_path.read_text(encoding="utf-8"))
    assert payload["version"] == 1
    assert len(payload["tasks"]) == 2


# ----------------------------------------------------------------------
# monkeypatch：替换外部依赖
# ----------------------------------------------------------------------
def test_monkeypatch_可以固定_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """monkeypatch 是 pytest 内置 fixture，比 unittest.mock.patch 更好用。

    它会**在测试结束后自动还原**，不用自己写 try/finally。
    这里把「今天」钉死，逾期判断就变成了确定性的——
    否则一条「截止日期是今天」的测试会在不同日期跑出不同结果（flaky test）。
    """
    fake_today = date(2026, 6, 1)

    class _FakeDate(date):
        @classmethod
        def today(cls) -> date:
            return fake_today

    monkeypatch.setattr("taskkit.models.date", _FakeDate)

    assert Task("昨天到期", due=date(2026, 5, 31)).is_overdue is True
    assert Task("明天到期", due=date(2026, 6, 2)).is_overdue is False
