"""CLI 的测试。

CLI 是出了名的难测，因为它天然依赖三样东西：命令行参数、标准输出、退出码。
本项目在设计时就把这三样都做成了**可注入的**：

    main(argv=None, out=None) -> int

于是测试只需要：传一个 argv 列表、传一个 io.StringIO、断言返回的整数。
不用 subprocess、不用重定向 sys.stdout、不用捕获异常。
**可测试性是设计出来的，不是测出来的。**
"""

from __future__ import annotations

import io
from pathlib import Path

import pytest

from taskkit.cli import build_parser, format_task, main
from taskkit.models import Priority, Task


@pytest.fixture
def run(db_path: Path):
    """包一个小工具，让每条测试只需写 `code, text = run("add", "写代码")`。"""

    def _run(*argv: str) -> tuple[int, str]:
        buffer = io.StringIO()
        code = main(["--db", str(db_path), *argv], out=buffer)
        return code, buffer.getvalue()

    return _run


# ----------------------------------------------------------------------
# 纯函数优先测
# ----------------------------------------------------------------------
def test_format_task_纯函数() -> None:
    """format_task 是纯函数，测它零成本——不碰文件、不碰标准输出。

    一个函数只要能从副作用里拆出来，就应该拆出来。
    """
    line = format_task(Task("写报告", priority=Priority.HIGH, id=1))
    assert line.startswith("[ ] !!! #1   写报告")


def test_format_task_显示逾期标记() -> None:
    from datetime import date, timedelta

    line = format_task(Task("过期任务", due=date.today() - timedelta(days=1)))
    assert "已逾期" in line


# ----------------------------------------------------------------------
# 通过 main() 测端到端
# ----------------------------------------------------------------------
def test_add_再_list(run) -> None:
    code, out = run("add", "写实验报告", "-p", "high")
    assert code == 0
    assert "已添加 #1" in out

    code, out = run("list")
    assert code == 0
    assert "写实验报告" in out


def test_done_改变_list_的输出(run) -> None:
    run("add", "写实验报告")
    assert "写实验报告" in run("list")[1]

    assert run("done", "1")[0] == 0
    assert "写实验报告" not in run("list")[1], "已完成的任务默认不显示"
    assert "写实验报告" in run("list", "--all")[1]


def test_rm_删除任务(run) -> None:
    run("add", "写实验报告")
    code, out = run("rm", "1")
    assert code == 0
    assert "已删除" in out
    assert "没有符合条件" in run("list")[1]


def test_stats(run) -> None:
    run("add", "甲", "-p", "high")
    run("add", "乙")
    code, out = run("stats")
    assert code == 0
    assert "总计 2" in out
    assert "HIGH" in out and "NORMAL" in out


# ----------------------------------------------------------------------
# 错误路径：这才是最容易出 bug 的地方
# ----------------------------------------------------------------------
def test_操作不存在的_id_返回退出码_1_而不是崩溃(run) -> None:
    """错误路径必须测。

    正经的 CLI 在用户输错时应该给一行提示 + 非零退出码，
    而不是甩一个 traceback。测试要守住这个契约。
    """
    code, out = run("done", "999")
    assert code == 1
    assert out == "", "错误信息应该走 stderr，不该混进 stdout"


def test_非法日期返回退出码_2(run) -> None:
    code, _ = run("add", "写代码", "-d", "2026/10/01")  # 格式错了
    assert code == 2


def test_非法优先级由_argparse_拦下(run) -> None:
    """choices= 让 argparse 在解析阶段就拒绝非法值，直接 SystemExit(2)。"""
    with pytest.raises(SystemExit) as exc_info:
        run("add", "写代码", "-p", "urgent")
    assert exc_info.value.code == 2


# ----------------------------------------------------------------------
# parser 本身
# ----------------------------------------------------------------------
def test_没给子命令会报错() -> None:
    """`required=True` 让漏写子命令直接失败，而不是静默什么都不做。"""
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_tag_参数可以重复出现() -> None:
    """action="append" 让同一个参数能出现多次，收集成列表。"""
    args = build_parser().parse_args(["add", "写代码", "--tag", "学校", "--tag", "紧急"])
    assert args.tag == ["学校", "紧急"]


def test_默认_db_路径可以被覆盖() -> None:
    args = build_parser().parse_args(["--db", "custom.json", "list"])
    assert args.db == Path("custom.json")
