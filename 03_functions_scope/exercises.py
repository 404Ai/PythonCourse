"""
模块 03 · 函数与作用域 —— 练习

做法：
    1. 把每个函数里的 `raise NotImplementedError` 换成你的实现
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

提示：报错的那一行可以下断点，按 F5 用调试器看中间变量，
      这是本课程最推荐的排错方式。

注意：本文件的函数签名**不要改**（尤其是 q2 的 `/` 和 `*`），
      测试就是冲着这些签名来的。
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 修复可变默认参数陷阱
# ======================================================================
def q1_add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    """返回一个「在 tags 基础上追加了 tag」的**新列表**。

    要求：
        1. 不传 tags 时，每次调用都从一个空列表开始，不能互相污染
        2. 不允许修改传进来的 tags（调用方的数据要原封不动）
        3. 返回值必须是一个新列表，不是传进来的那个

    >>> q1_add_tag("a")
    ['a']
    >>> q1_add_tag("b")
    ['b']
    >>> q1_add_tag("y", ["x"])
    ['x', 'y']

    提示：默认值不要写 []。想想 3.2 节讲的「默认值只在定义时求值一次」。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— positional-only 与 keyword-only
# ======================================================================
def q2_make_url(
    host: str,
    path: str,
    /,
    *,
    scheme: str = "https",
    port: int | None = None,
) -> str:
    """拼出一个 URL 字符串。

    规则：
        - path 不以 "/" 开头时，自动补上
        - port 是 None 时不出现在结果里
        - port 等于该 scheme 的默认端口（http 是 80，https 是 443）时也不出现

    >>> q2_make_url("example.com", "a/b")
    'https://example.com/a/b'
    >>> q2_make_url("example.com", "/a", scheme="http", port=8080)
    'http://example.com:8080/a'
    >>> q2_make_url("example.com", "/a", port=443)
    'https://example.com/a'

    注意签名里的 `/` 和 `*` 不要动：
        host / path 只能按位置传，scheme / port 只能按关键字传。
    """
    raise NotImplementedError


# ======================================================================
# q3 —— *args 配合 key 函数
# ======================================================================
def q3_top_scorer(key, *items, default=None):
    """返回 items 中 key(item) 最大的那个元素。

    要求：
        - key 是「打分函数」，用 max(..., key=...) 的语义实现
        - 分数相同时返回**最先出现**的那个元素
        - items 为空时返回 default
        - 用内置 max 完成，不要手写 for 循环比较

    >>> q3_top_scorer(len, "a", "bbb", "cc")
    'bbb'
    >>> q3_top_scorer(abs, -5, 3, -2)
    -5
    >>> q3_top_scorer(len) is None
    True

    提示：`*items` 收集成 tuple。空的时候不能直接调 max，会 ValueError。
    """
    raise NotImplementedError


# ======================================================================
# q4 —— 手写装饰器：调用计数
# ======================================================================
def q4_count_calls(func):
    """装饰器：记录被装饰函数被调用了多少次。

    要求：
        1. 包装函数上有一个 `calls` 属性，表示「到目前为止被调用了几次」
        2. 原函数的返回值必须原样返回
        3. 原函数的参数必须能原样传进去（任意签名都要支持）
        4. 用 functools.wraps 保留原函数的元信息

    >>> @q4_count_calls
    ... def add(a, b):
    ...     "两数相加。"
    ...     return a + b
    >>> add(1, 2)
    3
    >>> add.calls
    1

    提示：结构是「接收函数 -> 定义 wrapper -> 返回 wrapper」，
          计数变量可以放在外层函数的局部作用域里，用 nonlocal 累加，
          也可以直接挂在 wrapper 上（函数是对象，可以挂属性）。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 闭包：计数器工厂
# ======================================================================
def q5_make_counter(start: int = 0, step: int = 1):
    """返回一对函数 `(bump, reset)`。

        bump()  先把当前值加上 step，再返回新值
        reset() 把当前值恢复成 start，并返回它

    要求：
        1. bump 和 reset 共享同一份状态
        2. 每次调用 q5_make_counter 得到的状态互相独立
        3. 用 nonlocal 实现，不要用类、不要用 global

    >>> bump, reset = q5_make_counter(10, 5)
    >>> bump()
    15
    >>> bump()
    20
    >>> reset()
    10

    提示：状态变量定义在 make_counter 的函数体里，
          内层函数要改它就必须声明 nonlocal。
    """
    raise NotImplementedError


# ======================================================================
# q6 —— 延迟绑定陷阱的修复
# ======================================================================
def q6_make_multipliers(factors: list[int]) -> list:
    """为 factors 里的每个因子各返回一个函数。

    返回的列表里第 i 个函数 f(x) 的结果是 x * factors[i]。

    >>> fns = q6_make_multipliers([1, 2, 3])
    >>> [f(10) for f in fns]
    [10, 20, 30]
    >>> q6_make_multipliers([])
    []

    警告：下面这种写法是**错的**，返回的每个函数都会用同一个因子：

        return [lambda x: x * f for f in factors]      # 全都是最后一个 f

    提示：3.6 节讲了三种修复方式（默认参数固化 / 工厂函数 / functools.partial），
          任选一种。
    """
    raise NotImplementedError


# ======================================================================
# q7 —— lru_cache 记忆化
# ======================================================================
def q7_fib(n: int) -> int:
    """返回第 n 个斐波那契数，fib(0) = 0，fib(1) = 1，fib(n) = fib(n-1) + fib(n-2)。

    要求：
        1. 用递归写法（一行 return，不要改成循环）
        2. 必须加上 functools.lru_cache 或 functools.cache 装饰器，
           否则 q7_fib(30) 会慢到肉眼可见

    >>> q7_fib(10)
    55
    >>> q7_fib(30)
    832040

    提示：装饰器写在 def 上面，和 @q4_count_calls 的用法一样。
          注意测试里会访问 q7_fib.cache_info()，所以装饰器必须真的用上。
    """
    raise NotImplementedError


# ======================================================================
# q8 —— functools 工具箱：partial 与 reduce
# ======================================================================
def q8_make_formatter(prefix: str, width: int, precision: int = 2):
    """返回一个「格式化函数」f(value)，效果等于 f"{prefix}{value:>{width}.{precision}f}"。

    要求：返回值必须是 functools.partial 对象，不是 lambda、也不是内部 def 的函数。
          也就是要**用一个模块级的辅助函数 + partial 冻住参数**来实现。

    >>> fmt = q8_make_formatter("金额: ", 8)
    >>> fmt(3.14159)
    '金额:     3.14'

    提示：先写一个把 (prefix, width, precision, value) 全收下的函数，
          再用 functools.partial 把前三个冻住。
    """
    raise NotImplementedError


def q8_fold(operation: str, values: list[float], initial: float) -> float:
    """用 functools.reduce 实现三种折叠：

        "sum"   累加（从 initial 开始）
        "prod"  累乘（从 initial 开始）
        "max"   取最大值（initial 也参与比较）

    未知的 operation 抛 ValueError，消息里带上这个值。

    >>> q8_fold("sum", [1, 2, 3, 4], 0)
    10
    >>> q8_fold("prod", [1, 2, 3, 4], 1)
    24
    >>> q8_fold("sum", [], 100)
    100

    提示：准备一个 {"sum": 二元函数, ...} 的字典，
          然后 functools.reduce(那个函数, values, initial)。
          空列表会走 initial，所以不需要特判。
    """
    raise NotImplementedError


# ======================================================================
# q9 —— 带参数的装饰器：重试
# ======================================================================
def q9_retry(times: int, exceptions: tuple = (Exception,)):
    """装饰器工厂：让被装饰的函数失败时自动重试。

    语义：
        - 一共最多尝试 times 次
        - 只捕获 exceptions 里列出的异常类型；其它异常立刻向上抛
        - 全部尝试都失败时，把**最后一次**的异常抛出去（不能吞掉）
        - 有一次成功就立刻返回那个返回值
        - 用 functools.wraps 保留原函数的元信息

    用法示意（真正的测试在 t_q9 里）：

        @q9_retry(3)
        def flaky():
            ...

        @q9_retry(2, (ConnectionError, TimeoutError))
        def fetch():
            ...

    提示：这是「三层嵌套」结构 ——
          最外层 retry 收配置，中间层 decorator 收 func，最内层 wrapper 收实参。
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    # 两次独立调用不能互相污染（这就是可变默认参数陷阱的检测点）
    assert q1_add_tag("a") == ["a"], f"实际 {q1_add_tag('a')!r}"
    assert q1_add_tag("b") == ["b"], "第二次调用把上一次的结果带出来了，默认值是可变对象"
    assert q1_add_tag("c") == ["c"]

    base = ["x"]
    got = q1_add_tag("y", base)
    assert got == ["x", "y"], f"实际 {got!r}"
    assert got is not base, "必须返回新列表，而不是把传进来的列表直接返回"
    assert base == ["x"], "不能修改调用方传进来的列表"


def t_q2() -> None:
    assert q2_make_url("example.com", "a/b") == "https://example.com/a/b"
    assert q2_make_url("example.com", "/a/b") == "https://example.com/a/b"
    assert q2_make_url("example.com", "/a", scheme="http") == "http://example.com/a"
    assert q2_make_url("example.com", "/a", port=8080) == "https://example.com:8080/a"
    # 默认端口不显示
    assert q2_make_url("example.com", "/a", scheme="http", port=80) == "http://example.com/a"
    assert q2_make_url("example.com", "/a", scheme="https", port=443) == "https://example.com/a"

    # host / path 是 positional-only，用关键字传必须 TypeError
    try:
        q2_make_url(host="example.com", path="/a")
    except TypeError:
        pass
    else:
        raise AssertionError("host / path 是 positional-only，用关键字传应该 TypeError")

    # scheme / port 是 keyword-only，用位置传必须 TypeError
    try:
        q2_make_url("example.com", "/a", "http")
    except TypeError:
        pass
    else:
        raise AssertionError("scheme / port 是 keyword-only，用位置传应该 TypeError")


def t_q3() -> None:
    assert q3_top_scorer(len, "a", "bbb", "cc") == "bbb"
    assert q3_top_scorer(len, "bbb", "cc", "a") == "bbb"
    assert q3_top_scorer(abs, -5, 3, -2) == -5
    assert q3_top_scorer(str.lower, "Apple", "banana") == "banana"

    # 分数相同时返回最先出现的那个
    tie = [("a", 9), ("b", 9), ("c", 1)]
    assert q3_top_scorer(lambda t: t[1], *tie) == ("a", 9)

    # 空输入
    assert q3_top_scorer(len) is None
    assert q3_top_scorer(len, default="") == ""

    # key 必须对每个元素各调用一次
    seen: list[int] = []

    def spy(x: int) -> int:
        seen.append(x)
        return x

    assert q3_top_scorer(spy, 3, 1, 2) == 3
    assert sorted(seen) == [1, 2, 3], f"key 应该对每个元素都调用一次，实际 {seen}"


def t_q4() -> None:
    @q4_count_calls
    def add(a, b):
        """两数相加。"""
        return a + b

    assert add(1, 2) == 3, "返回值必须原样透传"
    assert add.calls == 1, f"add.calls 应该是 1，实际 {getattr(add, 'calls', '没有这个属性')}"
    assert add(3, 4) == 7
    assert add.calls == 2, f"add.calls 应该是 2，实际 {add.calls}"

    # 元信息必须靠 functools.wraps 保留
    assert add.__name__ == "add", f"__name__ 应该是 'add'，实际 {add.__name__!r}"
    assert add.__doc__ == "两数相加。", f"__doc__ 丢了：{add.__doc__!r}"
    assert hasattr(add, "__wrapped__"), "wraps 会设置 __wrapped__，没有它说明没写 wraps"

    # 任意签名都要支持（靠 *args / **kwargs）
    @q4_count_calls
    def varied(a, b=2, *args, **kwargs):
        return (a, b, args, sorted(kwargs.items()))

    assert varied(1) == (1, 2, (), [])
    assert varied(1, 3, 5, x=9) == (1, 3, (5,), [("x", 9)])
    assert varied.calls == 2

    # 不同被装饰函数的计数器互相独立
    @q4_count_calls
    def other():
        return None

    other()
    assert other.calls == 1
    assert add.calls == 2, "计数器不能是全局共享的"


def t_q5() -> None:
    bump, reset = q5_make_counter()
    assert bump() == 1
    assert bump() == 2
    assert bump() == 3
    assert reset() == 0
    assert bump() == 1, "reset 之后应该从 start 重新开始"

    bump2, reset2 = q5_make_counter(10, 5)
    assert bump2() == 15
    assert bump2() == 20
    assert reset2() == 10
    assert bump2() == 15

    # 两个闭包实例的状态必须独立
    bump3, _ = q5_make_counter()
    assert bump3() == 1, "新的计数器不该受之前那个影响"
    assert bump2() == 20, "老计数器也不该被新计数器影响"


def t_q6() -> None:
    fns = q6_make_multipliers([1, 2, 3])
    got = [f(10) for f in fns]
    assert got == [10, 20, 30], f"期望 [10, 20, 30]，实际 {got}（大概是延迟绑定陷阱）"

    assert q6_make_multipliers([]) == []

    # 再取一次结果，确认每个函数是稳定的、不共享状态
    assert [f(2) for f in fns] == [2, 4, 6]
    assert fns[0](0) == 0

    fns2 = q6_make_multipliers([0, -1, 100])
    assert [f(5) for f in fns2] == [0, -5, 500]
    # 用 partial 实现也是允许的，所以这里只要求「可调用」，不要求必须是函数
    assert callable(fns2[0]), "返回的应该是可调用对象"


def t_q7() -> None:
    # 先调用一次：这样没做这道题时会得到 SKIP 而不是 FAIL。
    # （如果先断言 hasattr(cache_info)，未实现的桩函数会直接判成 FAIL，
    #   那学生就分不清「我不会」和「我做错了」。）
    assert q7_fib(0) == 0
    assert q7_fib(1) == 1
    assert q7_fib(10) == 55
    assert q7_fib(30) == 832040

    assert hasattr(q7_fib, "cache_info"), \
        "q7_fib 必须用 functools.lru_cache 或 functools.cache 装饰"

    q7_fib.cache_clear()
    assert q7_fib(0) == 0
    assert q7_fib(1) == 1
    assert q7_fib(10) == 55
    assert q7_fib(30) == 832040

    q7_fib.cache_clear()
    assert q7_fib(30) == 832040
    first = q7_fib.cache_info()
    assert first.misses >= 1, f"第一次计算不应该全是命中：{first}"

    q7_fib(30)
    second = q7_fib.cache_info()
    assert second.hits == first.hits + 1, f"重复调用必须命中缓存：{first} -> {second}"
    assert second.misses == first.misses, f"重复调用不该产生新的未命中：{first} -> {second}"


def t_q8() -> None:
    # ---- partial 部分 ----
    money = q8_make_formatter("金额: ", 8)
    assert isinstance(money, functools.partial), \
        f"q8_make_formatter 必须返回 functools.partial 对象，实际是 {type(money).__name__}"
    assert money(3.14159) == "金额: " + f"{3.14159:>8.2f}"
    assert money(0.5) == "金额: " + f"{0.5:>8.2f}"

    pct = q8_make_formatter("", 6, 1)
    assert pct(0.25) == f"{0.25:>6.1f}"
    assert pct(1.0) == f"{1.0:>6.1f}"

    # ---- reduce 部分 ----
    assert q8_fold("sum", [1, 2, 3, 4], 0) == 10
    assert q8_fold("sum", [], 100) == 100
    assert q8_fold("prod", [1, 2, 3, 4], 1) == 24
    assert q8_fold("prod", [2, 5], 1) == 10
    assert q8_fold("max", [3, 9, 2], 0) == 9
    assert q8_fold("max", [3, 9, 2], 100) == 100
    assert q8_fold("sum", [1.5, 2.5], 0.0) == 4.0

    try:
        q8_fold("average", [1, 2], 0)
    except ValueError as exc:
        assert "average" in str(exc), f"ValueError 的消息里应该带上那个值：{exc}"
    else:
        raise AssertionError("未知的 operation 应该抛 ValueError")


def t_q9() -> None:
    # 失败两次后成功
    calls = {"n": 0}

    @q9_retry(3)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError(f"第 {calls['n']} 次故意失败")
        return "ok"

    assert flaky() == "ok", "第三次应该成功"
    assert calls["n"] == 3, f"应该尝试 3 次，实际 {calls['n']} 次"
    assert flaky.__name__ == "flaky", "必须用 functools.wraps 保留 __name__"

    # 全部失败 -> 把最后一次异常抛出去
    always = {"n": 0}

    @q9_retry(2)
    def always_fail():
        always["n"] += 1
        raise RuntimeError("一直失败")

    try:
        always_fail()
    except RuntimeError:
        pass
    else:
        raise AssertionError("重试全部失败后必须把异常抛出去，不能吞掉返回 None")
    assert always["n"] == 2, f"应该尝试 2 次，实际 {always['n']} 次"

    # 不在 exceptions 列表里的异常要立刻抛出，不重试
    typed = {"n": 0}

    @q9_retry(5, (ValueError,))
    def wrong_type():
        typed["n"] += 1
        raise TypeError("不该被重试")

    try:
        wrong_type()
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError 不在 exceptions 里，应该原样抛出")
    assert typed["n"] == 1, f"不该重试，实际尝试了 {typed['n']} 次"

    # 成功时包装函数要有返回值，参数也要能传进去
    @q9_retry(3)
    def add(a, b, c=0):
        return a + b + c

    assert add(1, 2) == 3
    assert add(1, 2, c=10) == 13


def main() -> None:
    c = Checker("模块 03 · 函数与作用域 练习")
    c.add("q1  修复可变默认参数陷阱", t_q1)
    c.add("q2  positional-only 与 keyword-only", t_q2)
    c.add("q3  *args 配合 key 函数", t_q3)
    c.add("q4  手写装饰器：调用计数", t_q4)
    c.add("q5  闭包：计数器工厂", t_q5)
    c.add("q6  延迟绑定陷阱的修复", t_q6)
    c.add("q7  lru_cache 记忆化", t_q7)
    c.add("q8  functools 工具箱：partial 与 reduce", t_q8)
    c.add("q9  带参数的装饰器：重试", t_q9)
    c.run()


if __name__ == "__main__":
    main()
