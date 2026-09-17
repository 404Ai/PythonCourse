"""命令行入口。

这个文件演示三件事：
    1. argparse 的子命令（subparsers）怎么写
    2. 为什么业务逻辑要放在库函数里、CLI 只做「解析参数 + 调用 + 打印」
    3. 怎么让 CLI 可测试：把 argv 做成参数、把输出打到可注入的流

`main(argv=None) -> int` 这个签名是刻意设计的：
    - 不调用 sys.exit()，而是**返回退出码**，方便测试直接断言返回值
    - argv 默认 None（表示读 sys.argv[1:]），测试时传列表进去
    - 真正的 sys.exit 只在 `if __name__ == "__main__"` 里做一次
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path
from typing import TextIO

from taskkit import __version__
from taskkit.errors import TaskKitError
from taskkit.models import Priority, Task
from taskkit.store import TaskStore

__all__ = ["build_parser", "format_task", "main"]

DEFAULT_DB = Path.home() / ".taskkit.json"


def build_parser() -> argparse.ArgumentParser:
    """构造解析器。

    单独抽成函数是为了让测试能直接拿到 parser——
    测试 `--help` 文案、测试参数校验，都不需要真的跑一遍 main。
    """
    parser = argparse.ArgumentParser(
        prog="taskkit",
        description="一个极简的命令行任务管理器。",
        epilog="示例：taskkit add '写实验报告' -p high -d 2026-10-01 --tag 学校",
    )
    parser.add_argument("--version", action="version", version=f"taskkit {__version__}")
    parser.add_argument(
        "--db",
        type=Path,
        default=DEFAULT_DB,
        help=f"数据文件路径（默认 {DEFAULT_DB}）",
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ---- add ----
    p_add = sub.add_parser("add", help="新增任务")
    p_add.add_argument("title", help="任务标题")
    p_add.add_argument(
        "-p",
        "--priority",
        choices=[m.name.lower() for m in Priority],
        default="normal",
        help="优先级（默认 normal）",
    )
    p_add.add_argument("-d", "--due", help="截止日期，格式 YYYY-MM-DD")
    p_add.add_argument("--tag", action="append", default=[], help="标签，可重复")

    # ---- list ----
    p_list = sub.add_parser("list", help="列出任务")
    p_list.add_argument("-a", "--all", action="store_true", help="包含已完成的任务")
    p_list.add_argument("--tag", help="只看某个标签")
    p_list.add_argument("--overdue", action="store_true", help="只看逾期的")

    # ---- done / rm ----
    for name, help_text in (("done", "标记任务完成"), ("rm", "删除任务")):
        p = sub.add_parser(name, help=help_text)
        p.add_argument("id", type=int, help="任务 id")

    # ---- stats ----
    sub.add_parser("stats", help="显示统计信息")

    return parser


def format_task(task: Task) -> str:
    """把一条任务渲染成一行文本。

    抽成独立的纯函数（输入 Task，输出 str），这样测试它不需要碰文件系统，
    也不需要捕获标准输出。**能写成纯函数的地方就写成纯函数**——
    这是可测试性最高的一类代码。
    """
    mark = "[x]" if task.done else "[ ]"
    prio = {Priority.HIGH: "!!!", Priority.NORMAL: "!", Priority.LOW: "."}[task.priority]
    due = f" 截止 {task.due.isoformat()}" if task.due else ""
    flag = " 已逾期" if task.is_overdue else ""
    tags = f"  #{' #'.join(task.tags)}" if task.tags else ""
    return f"{mark} {prio} #{task.id:<3} {task.title}{due}{tags}{flag}"


def _run(args: argparse.Namespace, store: TaskStore, out: TextIO) -> int:
    """执行具体命令。返回退出码。"""
    if args.command == "add":
        due = date.fromisoformat(args.due) if args.due else None
        task = store.add(args.title, priority=args.priority, due=due, tags=args.tag)
        print(f"已添加 #{task.id}：{task.title}", file=out)

    elif args.command == "list":
        tasks = store.list_tasks(include_done=args.all, tag=args.tag, overdue_only=args.overdue)
        if not tasks:
            print("（没有符合条件的任务）", file=out)
        for task in tasks:
            print(format_task(task), file=out)

    elif args.command == "done":
        task = store.complete(args.id)
        print(f"已完成 #{task.id}：{task.title}", file=out)

    elif args.command == "rm":
        task = store.remove(args.id)
        print(f"已删除 #{task.id}：{task.title}", file=out)

    elif args.command == "stats":
        s = store.stats()
        print(f"总计 {s['total']}  已完成 {s['done']}  逾期 {s['overdue']}", file=out)
        # 这里不需要 type: ignore —— stats() 返回的是 StoreStats（TypedDict），
        # mypy 知道 by_priority 就是 dict[str, int]
        for name, count in s["by_priority"].items():
            print(f"  {name:<7} {count}", file=out)

    return 0


def main(argv: list[str] | None = None, out: TextIO | None = None) -> int:
    """程序入口。返回退出码而不是直接 sys.exit。

    为什么把 `out` 也做成参数：
        测试想断言输出内容时，可以直接传一个 io.StringIO() 进来，
        不用去折腾 capsys 或者重定向 sys.stdout。
        生产代码里默认用 sys.stdout，行为和普通 print 一样。
    """
    out = out if out is not None else sys.stdout
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        # 建 store 也可能抛（文件损坏），所以一起放在 try 里
        store = TaskStore(args.db)
        return _run(args, store, out)
    except TaskKitError as exc:
        # 只捕获**本库的**异常。其他异常照常往上抛，
        # 因为那是 bug，应该带着完整 traceback 崩掉，而不是被吞成一行提示。
        print(f"错误：{exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        # 用户输入不合法（日期格式错、优先级拼错）属于「用错了」，
        # 给一行友好提示 + 退出码 1，比甩一个 traceback 友好得多。
        print(f"错误：{exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    # 整个项目里唯一一处 sys.exit
    sys.exit(main())
