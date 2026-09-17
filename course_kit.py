"""
课程通用自测工具。

所有模块的 exercises.py / solutions.py 都用它来跑断言，
这样你在 VS Code 里只要按 Ctrl+F5 运行一次，就能看到每一题的判定结果。

    [PASS]  断言通过
    [FAIL]  断言失败 —— 你的实现有 bug，看后面的说明
    [SKIP]  函数抛了 NotImplementedError —— 说明你还没做
    [ERROR] 代码抛了别的异常 —— 通常是类型错误或拼写错误

用法（模块里的写法）：

    from course_kit import Checker
    from solutions_helpers import ...

    c = Checker("模块 01 · 语言核心 练习")
    c.add("q1 格式化报表", t_q1)
    c.add("q2 精确金额",   t_q2)
    c.run()          # 打印结果；若有 FAIL / ERROR 则以退出码 1 结束
"""

from __future__ import annotations

import sys
import traceback
from typing import Callable

__all__ = ["Checker"]

# 四种状态的显示宽度一致，方便对齐
_STATUS_ORDER = ("FAIL", "ERROR", "SKIP", "PASS")


def display_width(text: str) -> int:
    """估算字符串在等宽终端里占的列数。

    中日韩字符（CJK）占 2 列，其余占 1 列。这里只做粗略判断，
    真正的实现要看 unicode 的 East_Asian_Width 属性（wcwidth 库做的事）。

    模块 01 里提到过「中文字符宽度陷阱」，这个函数就是那个问题的
    一个最小化实现 —— 不然下面打印报表时中文标题会把表格撑歪。
    """
    return sum(2 if ord(ch) > 0x2E7F else 1 for ch in text)


class Checker:
    """收集一组「无参、靠 assert 判定」的测试函数并统一执行。"""

    def __init__(self, title: str) -> None:
        self.title = title
        self._cases: list[tuple[str, Callable[[], object]]] = []

    def add(self, name: str, fn: Callable[[], object]) -> "Checker":
        """注册一个测试用例。返回 self，因此可以链式调用。"""
        self._cases.append((name, fn))
        return self

    # ------------------------------------------------------------------
    # 内部实现
    # ------------------------------------------------------------------
    @staticmethod
    def _run_one(fn: Callable[[], object]) -> tuple[str, str]:
        """执行单个用例，返回 (状态, 说明)。

        注意这里刻意把 NotImplementedError 排在 AssertionError 之前判断：
        它俩没有继承关系，但语义上「没做」和「做错了」必须分开报。
        """
        try:
            fn()
        except NotImplementedError:
            return "SKIP", "尚未实现（找到 raise NotImplementedError 并替换它）"
        except AssertionError as exc:
            return "FAIL", str(exc) or "断言失败（没有附带说明）"
        except Exception as exc:  # noqa: BLE001 - 这里是测试运行器，必须兜住一切
            # 只取最后一行，避免把整个调用栈糊到屏幕上
            detail = traceback.format_exception_only(type(exc), exc)[-1].strip()
            return "ERROR", detail
        return "PASS", ""

    # ------------------------------------------------------------------
    # 对外接口
    # ------------------------------------------------------------------
    def run(self) -> None:
        """跑完全部用例，打印报告，并在有 FAIL/ERROR 时以退出码 1 结束。"""
        if not self._cases:
            print(f"{self.title}: 没有任何测试用例。")
            return

        name_width = max(display_width(name) for name, _ in self._cases)
        counts = dict.fromkeys(_STATUS_ORDER, 0)

        print()
        print("=" * 72)
        print(self.title)
        print("=" * 72)

        for name, fn in self._cases:
            status, detail = self._run_one(fn)
            counts[status] += 1
            # 用显示宽度补空格，中英文混排时表格才不会歪
            pad = " " * (name_width - display_width(name))
            print(f"[{status}] {name}{pad}  {detail}".rstrip())

        total = len(self._cases)
        ok = counts["PASS"]
        print("-" * 72)
        print(
            f"合计 {total} 题   通过 {ok}   失败 {counts['FAIL']}   "
            f"异常 {counts['ERROR']}   未做 {counts['SKIP']}"
        )

        if counts["FAIL"] or counts["ERROR"]:
            print("还有没解决的问题，先看上面带 FAIL / ERROR 的行。")
            print("提示：可以在报错那一行下断点，按 F5 调试看中间变量。")
            sys.exit(1)

        if counts["SKIP"]:
            print(f"通过的都对了，还剩 {counts['SKIP']} 题没做。")
            return

        print("全部通过。做完之后打开 solutions.py 对照一下写法。")

    # 让 Checker 实例可以直接当函数调用，写起来更短
    __call__ = run
