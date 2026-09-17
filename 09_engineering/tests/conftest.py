"""pytest 的共享夹具（fixture）集中在这里。

conftest.py 是 pytest 的特殊文件：**这个目录及其子目录里的测试文件
都能直接用里面定义的 fixture，不需要 import。**

什么时候该把 fixture 放进 conftest.py：
    被两个以上测试文件用到 -> 放 conftest.py
    只在一个文件里用       -> 就写在那个文件里，别污染全局
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest

from taskkit.models import Priority
from taskkit.store import TaskStore


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """一个位于临时目录里的数据库路径。

    tmp_path 是 pytest 内置的 fixture，每次测试都给你一个**全新的**空目录
    （形如 C:\\Users\\...\\pytest-123\\test_xxx0\\），测试结束后 pytest 会自动清理。

    这就是为什么测试里不该手动写 `open("test.json", "w")`：
    那样的文件会留在项目目录里，两次运行的残留还会互相干扰。
    tmp_path 让每个测试都在干净的沙箱里跑。
    """
    return tmp_path / "tasks.json"


@pytest.fixture
def store(db_path: Path) -> TaskStore:
    """一个空的任务库。"""
    return TaskStore(db_path)


@pytest.fixture
def filled_store(store: TaskStore) -> TaskStore:
    """装了三条任务的任务库，覆盖三种优先级和三种截止日期状态。

    注意这个 fixture **依赖** `store` fixture —— fixture 可以层层依赖，
    pytest 会自动按依赖顺序构造，同一个 fixture 在一次测试里只构造一次。
    """
    today = date.today()
    store.add("写实验报告", priority=Priority.HIGH, due=today - timedelta(days=1), tags=["学校"])
    store.add("买牛奶", priority=Priority.LOW, due=today + timedelta(days=3))
    store.add("复习期末", priority=Priority.NORMAL, tags=["学校", "重要"])
    return store
