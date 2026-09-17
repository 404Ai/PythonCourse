"""
模块 02 · 数据结构精讲 —— 练习

做完整模块 01 的流程应该已经熟了：
    改函数体 -> Ctrl+F5 运行 -> 全 PASS -> 对照 solutions.py

这一模块的重点是**选对容器**。写实现之前先问自己：
    这题用 list / dict / set / Counter / defaultdict / deque 哪个最合适？
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 词频统计
# ======================================================================
_PUNCT = ".,!?;:\"'()[]{}-"


def q1_word_count(text: str) -> "Counter":
    """统计单词出现次数，返回 collections.Counter。

    规则：
        1. 先整体转小写
        2. 用 str.split() 按空白切分（它能自动处理连续空格和换行）
        3. 去掉每个词首尾的标点（标点集合见上面的 _PUNCT）
        4. 忽略去掉标点后变成空串的词

    >>> q1_word_count("Hello, hello! World.")
    Counter({'hello': 2, 'world': 1})

    提示：Counter 可以直接用可迭代对象构造：
         Counter(word for word in words if word)
    """
    raise NotImplementedError


# ======================================================================
# q2 —— 分组
# ======================================================================
def q2_group_by(records: list[dict], key_field: str) -> dict:
    """按 records 里每条记录的 key_field 字段分组，返回 {组名: [整条记录, ...]}。

    输入：
        [{"dept": "A", "name": "x"},
         {"dept": "B", "name": "y"},
         {"dept": "A", "name": "z"}]
    输出：
        {"A": [{"dept": "A", "name": "x"}, {"dept": "A", "name": "z"}],
         "B": [{"dept": "B", "name": "y"}]}

    要求：用 collections.defaultdict(list)，不要写 `if k not in d` 那种判断。

    注意：返回的字典要保持「组名首次出现的顺序」——
    defaultdict 天然保序，直接用就行。
    """
    raise NotImplementedError


# ======================================================================
# q3 —— Top-K
# ======================================================================
def q3_top_k(items: list[str], k: int) -> list[tuple[str, int]]:
    """统计 items 里各元素的出现次数，返回出现最多的前 k 个。

    返回 [(元素, 次数), ...]，排序规则：
        次数降序；次数相同时按元素字典序升序。

    >>> q3_top_k(["b", "a", "b", "a", "c"], 3)
    [('a', 2), ('b', 2), ('c', 1)]

    注意上面这个例子：a 和 b 都是 2 次，a 排在前面是因为字典序。

    提示：Counter.most_common() 在次数相同时按插入顺序返回，
         不保证字典序，所以不能直接用，得自己 sorted。
    """
    raise NotImplementedError


# ======================================================================
# q4 —— 递归展平
# ======================================================================
def q4_flatten(nested: list) -> list:
    """把任意深度的嵌套列表/元组展平成一维列表。

    >>> q4_flatten([1, [2, [3, [4]], 5], 6])
    [1, 2, 3, 4, 5, 6]
    >>> q4_flatten([])
    []
    >>> q4_flatten(["ab", ["cd"]])
    ['ab', 'cd']

    注意最后那个例子：**字符串也是可迭代对象，但不要展开它**。
    只展平 list 和 tuple。

    提示：`isinstance(item, (list, tuple))` 来判断要不要递归。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 分块
# ======================================================================
def q5_chunk(seq: list, size: int) -> list[list]:
    """把 seq 按 size 个一组切分，最后一组可能不足 size 个。

    >>> q5_chunk([1, 2, 3, 4, 5], 2)
    [[1, 2], [3, 4], [5]]
    >>> q5_chunk([1, 2, 3], 5)
    [[1, 2, 3]]
    >>> q5_chunk([], 3)
    []

    如果 size <= 0，抛 ValueError。

    提示：range(0, len(seq), size) 配合切片。
         切片越界不报错，所以最后一组不需要特殊处理。
    """
    raise NotImplementedError


# ======================================================================
# q6 —— 保序去重
# ======================================================================
def q6_dedupe(items: list) -> list:
    """去掉重复元素，**保持首次出现的顺序**。

    >>> q6_dedupe([3, 1, 3, 2, 1])
    [3, 1, 2]
    >>> q6_dedupe(["b", "a", "b"])
    ['b', 'a']

    提示：不要用 set，set 会打乱顺序。
         dict 在 3.7+ 保证按插入顺序遍历，而 dict 的 key 天然唯一——
         所以 `dict.fromkeys(items)` 拿到的是「保序去重的 key」。
    """
    raise NotImplementedError


# ======================================================================
# q7 —— 多键排序
# ======================================================================
def q7_sort_records(records: list[dict]) -> list[dict]:
    """按 score 降序排列；score 相同时按 name 升序。

    >>> recs = [{"name": "bob", "score": 90},
    ...         {"name": "alice", "score": 90},
    ...         {"name": "carl", "score": 85}]
    >>> [r["name"] for r in q7_sort_records(recs)]
    ['alice', 'bob', 'carl']

    要求：**一次** sorted 调用搞定，不要排两趟。
    提示：让 key 返回一个元组，数值取负来实现降序。
         注意不能对整个元组用 reverse=True，因为那样 name 也会变成降序。
    """
    raise NotImplementedError


# ======================================================================
# q8 —— 矩阵转置
# ======================================================================
def q8_transpose(matrix: list[list]) -> list[list]:
    """转置矩阵（行列互换）。

    >>> q8_transpose([[1, 2, 3], [4, 5, 6]])
    [[1, 4], [2, 5], [3, 6]]
    >>> q8_transpose([])
    []

    要求：用 zip(*matrix) 一行搞定，不要写双重循环。
    注意 zip 返回的是元组，题目要的是 list，所以要转换一下。

    提示：`zip(*[])` 会得到空迭代器，所以空矩阵自然返回 []，不用特判。
    """
    raise NotImplementedError


# ======================================================================
# q9 —— 浅拷贝陷阱
# ======================================================================
def q9_copy_trap() -> tuple[bool, list, list]:
    """按下面的步骤执行，返回 (浅拷贝是否影响了原数据, 浅拷贝后的原数据, 深拷贝追加后的结果)。

    步骤：
        original = [[1, 2], [3, 4]]
        shallow  = original[:]        # 浅拷贝
        shallow[0].append(99)
        deep     = copy.deepcopy(original)
        deep[1].append(88)

    期望返回：
        (True, [[1, 2, 99], [3, 4]], [[1, 2, 99], [3, 4, 88]])

    做完这题你就彻底理解「浅拷贝只复制一层」了。
    """
    raise NotImplementedError


# ======================================================================
# q10 —— 循环右移
# ======================================================================
def q10_rotate(seq: list, n: int) -> list:
    """把序列循环右移 n 位。

    >>> q10_rotate([1, 2, 3, 4, 5], 2)
    [4, 5, 1, 2, 3]
    >>> q10_rotate([1, 2, 3, 4, 5], 0)
    [1, 2, 3, 4, 5]
    >>> q10_rotate([1, 2, 3, 4, 5], 7)
    [4, 5, 1, 2, 3]

    n 可以比长度大（取模即可），也可以是负数（表示左移）。

    提示：collections.deque 的 rotate() 正好干这个，而且比切片拼接更直观。
         注意 rotate 是**就地**修改，返回值是 None。
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    from collections import Counter

    assert q1_word_count("Hello, hello! World.") == Counter({"hello": 2, "world": 1})
    assert q1_word_count("") == Counter()
    assert q1_word_count("a  \n b\tb") == Counter({"a": 1, "b": 2})
    # 去掉标点后变成空串的词要被忽略
    assert q1_word_count("hi --- there") == Counter({"hi": 1, "there": 1})


def t_q2() -> None:
    recs = [
        {"dept": "A", "name": "x"},
        {"dept": "B", "name": "y"},
        {"dept": "A", "name": "z"},
    ]
    got = q2_group_by(recs, "dept")
    assert dict(got) == {
        "A": [{"dept": "A", "name": "x"}, {"dept": "A", "name": "z"}],
        "B": [{"dept": "B", "name": "y"}],
    }
    assert list(got.keys()) == ["A", "B"], "组的顺序要保持首次出现的顺序"
    assert q2_group_by([], "dept") == {}


def t_q3() -> None:
    assert q3_top_k(["b", "a", "b", "a", "c"], 3) == [("a", 2), ("b", 2), ("c", 1)]
    assert q3_top_k(["x", "x", "x"], 1) == [("x", 3)]
    assert q3_top_k(["a", "b"], 5) == [("a", 1), ("b", 1)], "k 超过种类数时返回全部"
    assert q3_top_k([], 3) == []


def t_q4() -> None:
    assert q4_flatten([1, [2, [3, [4]], 5], 6]) == [1, 2, 3, 4, 5, 6]
    assert q4_flatten([]) == []
    assert q4_flatten(["ab", ["cd"]]) == ["ab", "cd"], "字符串不要展开"
    assert q4_flatten([(1, 2), [3]]) == [1, 2, 3], "元组也要展开"
    assert q4_flatten([[], [[]], 1]) == [1]


def t_q5() -> None:
    assert q5_chunk([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert q5_chunk([1, 2, 3], 5) == [[1, 2, 3]]
    assert q5_chunk([], 3) == []
    assert q5_chunk([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]

    for bad in (0, -1):
        try:
            q5_chunk([1], bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"size={bad} 应该抛 ValueError")


def t_q6() -> None:
    assert q6_dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert q6_dedupe(["b", "a", "b"]) == ["b", "a"]
    assert q6_dedupe([]) == []
    assert q6_dedupe([1, 1, 1]) == [1]


def t_q7() -> None:
    recs = [
        {"name": "bob", "score": 90},
        {"name": "alice", "score": 90},
        {"name": "carl", "score": 85},
        {"name": "dave", "score": 95},
    ]
    got = [r["name"] for r in q7_sort_records(recs)]
    assert got == ["dave", "alice", "bob", "carl"], got

    # 原列表不应该被修改（sorted 返回新列表）
    assert [r["name"] for r in recs][0] == "bob", "不要用就地 sort 改掉入参"


def t_q8() -> None:
    assert q8_transpose([[1, 2, 3], [4, 5, 6]]) == [[1, 4], [2, 5], [3, 6]]
    assert q8_transpose([[1], [2]]) == [[1, 2]]
    assert q8_transpose([]) == []
    result = q8_transpose([[1, 2], [3, 4]])
    assert isinstance(result[0], list), "要返回 list 而不是 tuple"


def t_q9() -> None:
    affected, original_after, deep_after = q9_copy_trap()
    assert affected is True, "浅拷贝应该影响到了原数据"
    assert original_after == [[1, 2, 99], [3, 4]], original_after
    assert deep_after == [[1, 2, 99], [3, 4, 88]], deep_after


def t_q10() -> None:
    assert q10_rotate([1, 2, 3, 4, 5], 2) == [4, 5, 1, 2, 3]
    assert q10_rotate([1, 2, 3, 4, 5], 0) == [1, 2, 3, 4, 5]
    assert q10_rotate([1, 2, 3, 4, 5], 5) == [1, 2, 3, 4, 5]
    assert q10_rotate([1, 2, 3, 4, 5], 7) == [4, 5, 1, 2, 3]
    assert q10_rotate([1, 2, 3, 4, 5], -1) == [2, 3, 4, 5, 1]
    assert q10_rotate([], 3) == []

    src = [1, 2, 3]
    q10_rotate(src, 1)
    assert src == [1, 2, 3], "不要就地修改传入的列表"


def main() -> None:
    c = Checker("模块 02 · 数据结构精讲 练习")
    c.add("q1  Counter 词频统计", t_q1)
    c.add("q2  defaultdict 分组", t_q2)
    c.add("q3  Top-K 与并列排序", t_q3)
    c.add("q4  递归展平嵌套列表", t_q4)
    c.add("q5  分块 chunk", t_q5)
    c.add("q6  保序去重", t_q6)
    c.add("q7  多键排序", t_q7)
    c.add("q8  矩阵转置", t_q8)
    c.add("q9  浅拷贝陷阱", t_q9)
    c.add("q10 deque 循环移位", t_q10)
    c.run()


if __name__ == "__main__":
    main()
