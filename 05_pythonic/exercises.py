"""
模块 05 · 迭代器、生成器、上下文管理器 —— 练习

做法：
    1. 把每个 `raise NotImplementedError` 换成你的实现
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

提示：报错的那一行可以下断点，按 F5 用调试器看中间变量，
      这是本课程最推荐的排错方式。
"""

from __future__ import annotations

import sys
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 手写一个迭代器类
# ======================================================================
class Fibonacci:
    """斐波那契数列迭代器：1, 1, 2, 3, 5, 8, ...

    要求：
        - 产出所有**不超过** limit 的斐波那契数
        - 前两个数都是 1
        - __iter__ 返回 self（它本身就是迭代器，只跑一次）
        - __next__ 返回下一个数；没有更多时抛 StopIteration

    Fibonacci(10) 应该产出 1, 1, 2, 3, 5, 8  （13 > 10，停）
    Fibonacci(0)  应该什么都不产出
    """

    def __init__(self, limit: int) -> None:
        raise NotImplementedError

    def __iter__(self) -> "Fibonacci":
        raise NotImplementedError

    def __next__(self) -> int:
        raise NotImplementedError


# ======================================================================
# q2 —— 生成器：滑动窗口
# ======================================================================
def sliding_window(iterable: Iterable, n: int) -> Iterator[tuple]:
    """把序列切成一个个长度为 n 的连续窗口。

        sliding_window([1, 2, 3, 4], 2) -> (1, 2), (2, 3), (3, 4)
        sliding_window([1, 2], 3)       -> 什么都不产出

    要求：
        - 用 yield 写成生成器（不是返回 list）
        - 只遍历 iterable **一次**，不能先 list() 再切片
          （提示：collections.deque(maxlen=n) 天然适合做这个）
        - n <= 0 时抛 ValueError
    """
    raise NotImplementedError


# ======================================================================
# q3 —— 生成器：惰性读取文件
# ======================================================================
def read_clean_lines(path: str | Path) -> Iterator[str]:
    """惰性读取文本文件，逐行产出「洗干净」的行。

    规则：
        - 每行 strip() 之后，空行不产出
        - 以 # 开头的行（注释）不产出
        - 一次只从文件读一行，不能 readlines()

    要求：
        - 用 with 打开文件，保证异常时也会关闭
        - 用 encoding="utf-8"（不写的话 Windows 上会按 GBK 解码）
    """
    raise NotImplementedError


# ======================================================================
# q4 —— 用 itertools 解决组合问题
# ======================================================================
def two_sum_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """找出所有下标对 (i, j)，i < j，使得 nums[i] + nums[j] == target。

        two_sum_pairs([1, 2, 3, 4, 5], 6) -> [(0, 4), (1, 3)]

    要求：
        - 用 itertools.combinations 枚举下标对，**不要写双重 for 循环**
        - 返回顺序就是 combinations 的产出顺序（下标升序）
        - 没有解时返回空列表

    提示：combinations(range(len(nums)), 2) 正好枚举所有 i < j 的下标对。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 上下文管理器：类实现
# ======================================================================
class Timer:
    """用类实现的计时上下文管理器。

        with Timer() as t:
            do_something()
        print(t.elapsed)

    要求：
        - __enter__ 记录开始时间，并返回 self（这样才能 `as t`）
        - __exit__ 把耗时（秒，float）存进 self.elapsed
        - **不要吞异常**：块内抛异常时，异常必须继续往外传，
          但 elapsed 仍然要被设置好（提示：__exit__ 一定会被调用）
    """

    def __init__(self) -> None:
        raise NotImplementedError

    def __enter__(self) -> "Timer":
        raise NotImplementedError

    def __exit__(self, exc_type, exc, tb) -> None:
        raise NotImplementedError


# ======================================================================
# q6 —— 上下文管理器：@contextmanager 实现
# ======================================================================
@contextmanager
def temp_env(name: str, value: str) -> Iterator[None]:
    """临时把环境变量 name 设成 value，退出时恢复原状。

        with temp_env("API_URL", "https://test.example.com"):
            ...   # 块内 os.environ["API_URL"] 是新的值

    要求：
        - 用 contextlib.contextmanager 实现（yield 之前 = 进入，之后 = 退出）
        - 退出时如果这个变量**原本不存在**，必须把它**删掉**，
          而不是设成空字符串
        - 块内抛异常也要正确恢复（提示：yield 必须包在 try/finally 里）
    """
    raise NotImplementedError


# ======================================================================
# q7 —— groupby 分组（注意那个必须先排序的坑）
# ======================================================================
def group_by_key(records: list[tuple[str, int]]) -> dict[str, list[tuple[str, int]]]:
    """按每条记录的第 0 个元素分组。

        [("水果", 1), ("蔬菜", 2), ("水果", 3)]
        -> {"水果": [("水果", 1), ("水果", 3)], "蔬菜": [("蔬菜", 2)]}

    要求：
        - 必须用 itertools.groupby，不要用 defaultdict
        - groupby 只合并**相邻**的相同 key，所以先按同一个 key 排序
        - group 是共享的迭代器，必须**立刻** list() 物化
          （直接存 group 的话，下一轮它就空了）
        - 返回 dict 的键顺序不作要求

    最常见的错误就是忘了排序：那样 "水果" 会被分成两组甚至更多组。
    """
    raise NotImplementedError


# ======================================================================
# q8 —— itertools 综合运用
# ======================================================================
def running_max(numbers: list[int]) -> list[int]:
    """累积最大值：[3, 1, 4, 1, 5] -> [3, 3, 4, 4, 5]。

    要求：用 itertools.accumulate。
    """
    raise NotImplementedError


def first_n(iterable: Iterable, n: int) -> list:
    """取前 n 个元素。

        first_n(itertools.count(), 4) -> [0, 1, 2, 3]
        first_n([1, 2, 3], 10)        -> [1, 2, 3]

    要求：用 itertools.islice。
    注意输入可能是生成器或无限迭代器，所以不能 len()、不能切片。
    """
    raise NotImplementedError


def successive_diffs(numbers: list[int]) -> list[int]:
    """相邻两项之差：[1, 4, 9] -> [3, 5]。

    要求：用 itertools.pairwise（3.10+）。
    """
    raise NotImplementedError


def flatten(nested: list[list[int]]) -> list[int]:
    """展平一层：[[1, 2], [3], [4, 5]] -> [1, 2, 3, 4, 5]。

    要求：用 itertools.chain.from_iterable。
    """
    raise NotImplementedError


# ======================================================================
# q9 —— __missing__、字典合并、zip(strict=True)
# ======================================================================
class CountDict(dict):
    """一个「读不存在的键返回 0」的字典。

        c = CountDict()
        c["apple"] += 1        # 不应该抛 KeyError
        c["apple"] += 1
        print(c)               # {'apple': 2}

    要求：用 __missing__ 实现，并且访问后这个键要真的出现在字典里。
    注意 __missing__ 只对 d[key] 生效，不影响 get() / in。
    """

    def __missing__(self, key):
        raise NotImplementedError


def merge_configs(*configs: dict) -> dict:
    """把多个配置字典合并成一个，**后面的覆盖前面的**。

        merge_configs({"a": 1, "b": 2}, {"b": 99, "c": 3})
        -> {"a": 1, "b": 99, "c": 3}

    要求：
        - 用字典合并运算符 `|`，不要写 for 循环逐个 update
        - 不能就地修改任何输入字典
        - 一个都不传时返回空字典
    """
    raise NotImplementedError


def all_positive_pairs(names: list[str], scores: list[int]) -> bool:
    """判断「名字和分数一一对应，且每个分数都大于 0」。

    要求：
        - 两列表长度必须相同，不同就抛 ValueError
          （提示：zip(..., strict=True) 会替你抛，别自己写 if len(...) != len(...)）
        - 用 all(...) 判断。空输入返回 True
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    assert list(Fibonacci(10)) == [1, 1, 2, 3, 5, 8], f"实际 {list(Fibonacci(10))}"
    assert list(Fibonacci(1)) == [1, 1], "两个 1 都不超过 1，所以都要产出"
    assert list(Fibonacci(2)) == [1, 1, 2], "2 不超过 2，也要产出"
    assert list(Fibonacci(0)) == [], "limit 为 0 时什么都不该产出"
    assert list(Fibonacci(100)) == [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]

    f = Fibonacci(10)
    assert iter(f) is f, "__iter__ 必须返回 self（它本身就是迭代器）"

    assert list(f) == [1, 1, 2, 3, 5, 8]
    assert list(f) == [], "同一个迭代器只能用一次，第二次应该是空的"

    exhausted = Fibonacci(1)
    assert list(exhausted) == [1, 1], "先把 limit=1 的迭代器跑干净"
    for _ in range(3):
        try:
            next(exhausted)
        except StopIteration:
            pass
        else:
            raise AssertionError("耗尽的迭代器再 next() 必须继续抛 StopIteration")

    assert [n for n in Fibonacci(7)] == [1, 1, 2, 3, 5], "for 循环也应该能遍历"


def t_q2() -> None:
    import inspect

    assert list(sliding_window([1, 2, 3, 4], 2)) == [(1, 2), (2, 3), (3, 4)]
    assert list(sliding_window([1, 2, 3], 3)) == [(1, 2, 3)]
    assert list(sliding_window([1, 2], 3)) == [], "不足 n 个时一个都不产出"
    assert list(sliding_window([1], 1)) == [(1,)]
    assert list(sliding_window([], 2)) == []
    assert list(sliding_window("abcd", 2)) == [("a", "b"), ("b", "c"), ("c", "d")], "字符串也要能用"

    # 输入是迭代器（只能遍历一次）也要能工作
    assert list(sliding_window(iter([1, 2, 3, 4]), 2)) == [(1, 2), (2, 3), (3, 4)], (
        "输入是一次性迭代器时也必须正确 —— 说明你只遍历了它一次"
    )

    windowed = sliding_window([1, 2, 3, 4], 2)
    assert inspect.isgenerator(windowed), "必须用 yield 写成生成器，不能返回 list"
    assert next(windowed) == (1, 2), "生成器应该是惰性的"
    assert next(windowed) == (2, 3)

    for bad in (0, -1):
        try:
            list(sliding_window([1, 2, 3], bad))
        except ValueError:
            pass
        else:
            raise AssertionError(f"n={bad} 应该抛 ValueError")


def t_q3() -> None:
    import inspect
    import tempfile

    content = (
        "# 这是注释\n"
        "\n"
        "  apple  \n"
        "banana\n"
        "# 又一条注释\n"
        "   \n"
        "\tcherry\t\n"
        "中文行\n"
    )

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "data.txt"
        path.write_text(content, encoding="utf-8")

        gen = read_clean_lines(path)
        assert inspect.isgenerator(gen), "必须用 yield 写成生成器，不能 readlines() 一次性读完"
        assert next(gen) == "apple", "第一行应该是 strip 过的 apple"
        assert next(gen) == "banana"
        assert list(gen) == ["cherry", "中文行"], "剩下的行也要正确产出"

        assert list(read_clean_lines(path)) == ["apple", "banana", "cherry", "中文行"]

        empty = Path(tmp) / "empty.txt"
        empty.write_text("\n\n# only comments\n   \n", encoding="utf-8")
        assert list(read_clean_lines(empty)) == []

        # 传字符串路径也要能用
        assert list(read_clean_lines(str(path))) == ["apple", "banana", "cherry", "中文行"]


def t_q4() -> None:
    import inspect

    assert two_sum_pairs([1, 2, 3, 4, 5], 6) == [(0, 4), (1, 3)], (
        f"实际 {two_sum_pairs([1, 2, 3, 4, 5], 6)}"
    )
    assert two_sum_pairs([1, 2, 3], 100) == []
    assert two_sum_pairs([], 5) == []
    assert two_sum_pairs([5], 5) == [], "一个元素凑不出一对"
    assert two_sum_pairs([2, 2, 2], 4) == [(0, 1), (0, 2), (1, 2)], "重复元素也要分别算"
    assert two_sum_pairs([0, 0], 0) == [(0, 1)]
    assert two_sum_pairs([4, -2, 6, -4], 2) == [(0, 1), (2, 3)], (
        f"负数也要能处理，实际 {two_sum_pairs([4, -2, 6, -4], 2)}"
    )

    assert "combinations" in inspect.getsource(two_sum_pairs), (
        "要求用 itertools.combinations 枚举下标对"
    )


def t_q5() -> None:
    import time

    with Timer() as t:
        assert isinstance(t, Timer), "__enter__ 必须返回 self"
    assert isinstance(t.elapsed, float), f"elapsed 应该是 float，实际 {type(t.elapsed).__name__}"
    assert t.elapsed >= 0.0

    with Timer() as t2:
        time.sleep(0.02)
    assert t2.elapsed >= 0.01, f"应该量到 sleep 的耗时，实际只有 {t2.elapsed}"

    t3 = Timer()
    try:
        with t3:
            raise ValueError("块内炸了")
    except ValueError:
        pass
    else:
        raise AssertionError("Timer 的 __exit__ 不能吞掉异常，必须让它继续往外传")
    assert t3.elapsed >= 0.0, "即使块内抛异常，__exit__ 也应该把 elapsed 设好"

    for _ in range(2):
        with Timer() as fresh:
            pass
        assert fresh.elapsed >= 0.0, "同一个类应该能反复使用"


def t_q6() -> None:
    import os

    key = "PYCOURSE_TEST_VAR"
    os.environ.pop(key, None)
    try:
        assert key not in os.environ
        with temp_env(key, "hello"):
            assert os.environ[key] == "hello", f"块内应该是 hello，实际 {os.environ.get(key)!r}"
        assert key not in os.environ, (
            "这个变量原本不存在，退出时必须把它删掉，而不是设成空字符串"
        )

        os.environ[key] = "original"
        with temp_env(key, "changed"):
            assert os.environ[key] == "changed"
        assert os.environ[key] == "original", "退出后必须还原成原来的值"

        try:
            with temp_env(key, "changed2"):
                assert os.environ[key] == "changed2"
                raise RuntimeError("块内炸了")
        except RuntimeError:
            pass
        else:
            raise AssertionError("temp_env 不能吞掉异常")
        assert os.environ[key] == "original", "异常路径下也必须恢复原值"

        os.environ.pop(key, None)
        try:
            with temp_env(key, "x"):
                raise RuntimeError("块内炸了")
        except RuntimeError:
            pass
        assert key not in os.environ, "原本不存在的变量，异常路径下也必须被删掉"
    finally:
        os.environ.pop(key, None)


def t_q7() -> None:
    import inspect

    records = [
        ("水果", 1),
        ("蔬菜", 2),
        ("水果", 3),
        ("肉类", 4),
        ("蔬菜", 5),
        ("水果", 6),
    ]
    got = group_by_key(records)
    assert got == {
        "水果": [("水果", 1), ("水果", 3), ("水果", 6)],
        "蔬菜": [("蔬菜", 2), ("蔬菜", 5)],
        "肉类": [("肉类", 4)],
    }, f"实际 {got}"

    assert len(got["水果"]) == 3, (
        "同一组的记录掉了一些 —— 多半是把 group 迭代器直接存起来没 list()，"
        "或者忘了先排序导致同一组被拆开"
    )
    assert sum(len(v) for v in got.values()) == len(records), "一条记录都不能丢"

    assert group_by_key([]) == {}
    assert group_by_key([("a", 1)]) == {"a": [("a", 1)]}

    # 已经排好序的输入也要正确
    sorted_records = sorted(records, key=lambda r: r[0])
    assert group_by_key(sorted_records) == got

    assert "groupby" in inspect.getsource(group_by_key), "要求用 itertools.groupby"

    # 返回的 group 必须是 list，不能是迭代器
    for group in got.values():
        assert isinstance(group, list), f"每组必须是 list，实际是 {type(group).__name__}"


def t_q8() -> None:
    import inspect
    import itertools

    assert running_max([3, 1, 4, 1, 5]) == [3, 3, 4, 4, 5], f"实际 {running_max([3, 1, 4, 1, 5])}"
    assert running_max([]) == []
    assert running_max([-1, -5, -3]) == [-1, -1, -1]

    assert first_n(itertools.count(), 4) == [0, 1, 2, 3], "无限迭代器也要能取"
    assert first_n([1, 2, 3], 10) == [1, 2, 3], "不足 n 个就全给"
    assert first_n([1, 2, 3], 0) == []
    assert first_n(iter([1, 2, 3]), 2) == [1, 2]

    assert successive_diffs([1, 4, 9]) == [3, 5], f"实际 {successive_diffs([1, 4, 9])}"
    assert successive_diffs([5]) == []
    assert successive_diffs([]) == []
    assert successive_diffs([1, 2]) == [1]

    assert flatten([[1, 2], [3], [], [4, 5]]) == [1, 2, 3, 4, 5]
    assert flatten([]) == []
    assert flatten([[], []]) == []

    src = {
        "accumulate": inspect.getsource(running_max),
        "islice": inspect.getsource(first_n),
        "pairwise": inspect.getsource(successive_diffs),
        "chain": inspect.getsource(flatten),
    }
    for name, text in src.items():
        assert name in text, f"要求用 itertools.{name} 实现"


def t_q9() -> None:
    import inspect

    c = CountDict()
    assert c["apple"] == 0, "访问不存在的键应该返回 0，而不是抛 KeyError"
    assert "apple" in c, "__missing__ 里要把键写回字典，不能只返回 0"
    c["apple"] += 1
    c["apple"] += 1
    c["banana"] += 1
    assert c == {"apple": 2, "banana": 1}, f"实际 {c}"

    assert c["nope"] == 0
    assert "nope" in c
    assert c.get("nope") == 0, "get() 不该受 __missing__ 影响（键已经被写回去了，所以是 0）"
    assert c.get("another") is None, "get() 不触发 __missing__，应该返回 None"

    assert merge_configs({"a": 1, "b": 2}, {"b": 99, "c": 3}) == {"a": 1, "b": 99, "c": 3}
    assert merge_configs({"a": 1}) == {"a": 1}
    assert merge_configs() == {}
    assert merge_configs({}, {"x": 1}) == {"x": 1}
    original = {"a": 1}
    merged = merge_configs(original, {"b": 2})
    assert original == {"a": 1}, "不能就地修改输入字典"
    assert merged == {"a": 1, "b": 2}
    assert "|" in inspect.getsource(merge_configs), "要求用 `|` 合并字典"

    assert all_positive_pairs(["张三", "李四"], [90, 85]) is True
    assert all_positive_pairs([], []) is True, "空输入返回 True（空真）"
    assert all_positive_pairs(["张三"], [0]) is False
    assert all_positive_pairs(["张三", "李四"], [90, -5]) is False

    try:
        all_positive_pairs(["张三", "李四"], [90])
    except ValueError:
        pass
    else:
        raise AssertionError("长度不一致必须抛 ValueError（提示：zip(..., strict=True)）")

    try:
        all_positive_pairs(["张三"], [90, 85])
    except ValueError:
        pass
    else:
        raise AssertionError("长度不一致必须抛 ValueError")

    assert "strict=True" in inspect.getsource(all_positive_pairs), (
        "要求用 zip(..., strict=True) 来发现长度不一致"
    )


def main() -> None:
    c = Checker("模块 05 · 迭代器、生成器、上下文管理器 练习")
    c.add("q1  手写迭代器类 Fibonacci", t_q1)
    c.add("q2  生成器：滑动窗口", t_q2)
    c.add("q3  生成器：惰性读文件", t_q3)
    c.add("q4  itertools：两数之和配对", t_q4)
    c.add("q5  上下文管理器（类实现）", t_q5)
    c.add("q6  上下文管理器（@contextmanager）", t_q6)
    c.add("q7  groupby 分组", t_q7)
    c.add("q8  itertools 综合运用", t_q8)
    c.add("q9  __missing__ / 字典合并 / zip strict", t_q9)
    c.run()


if __name__ == "__main__":
    main()
