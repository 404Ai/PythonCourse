"""
模块 02 · 数据结构精讲 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**
"""

from __future__ import annotations

import copy
import sys
from collections import Counter, defaultdict, deque
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker

_PUNCT = ".,!?;:\"'()[]{}-"


# ======================================================================
# q1 —— 词频统计
# ======================================================================
def q1_word_count(text: str) -> Counter:
    """切成词 -> 去标点 -> 丢掉空串 -> 丢给 Counter。"""
    # str.split() 不带参数时按「任意连续空白」切分，并且自动丢掉首尾空白，
    # 所以不用先 strip()——这是 split() 和 split(" ") 的关键区别：
    #     "a  b".split()    -> ['a', 'b']
    #     "a  b".split(" ") -> ['a', '', 'b']   <- 连续空格会切出空串
    words = (w.strip(_PUNCT) for w in text.lower().split())
    return Counter(w for w in words if w)


# 常见错误：
#   1. text.split(" ")          —— 连续空格切出空串
#   2. 忘记过滤空串              —— "---" 会被统计成一个空字符串的键
#   3. 用 re.split(r"\W+", ...)  —— 能跑通，但本题不需要正则，杀鸡用牛刀
#
# strip(_PUNCT) 的参数是「字符集合」不是子串（模块 01 讲过），
# 所以它会去掉首尾所有属于这个集合的字符，"hello!!!," 会变成 "hello"。


# ======================================================================
# q2 —— 分组
# ======================================================================
def q2_group_by(records: list[dict], key_field: str) -> dict:
    """defaultdict(list) 的教科书用法。"""
    groups = defaultdict(list)
    for rec in records:
        groups[rec[key_field]].append(rec)
    return groups


# 为什么用 defaultdict 而不是普通 dict：
#     普通 dict 要写     groups.setdefault(k, []).append(rec)
#     或者              if k not in groups: groups[k] = []
#                       groups[k].append(rec)
#   defaultdict 把「key 不存在就创建一个空列表」这件事交给容器本身做，
#   循环体里就只剩下一行业务逻辑。
#
# 返回 defaultdict 而不是 dict 也没问题——defaultdict 是 dict 的子类，
# 比较、遍历、序列化行为完全一致。想做类型收窄可以包一层 dict(...)。
#
# 调用方注意：如果拿到的是 defaultdict，读一个不存在的 key 会往里插数据。
# 这是 defaultdict 最容易咬人的地方，模块 README 2.9 节讲过。


# ======================================================================
# q3 —— Top-K
# ======================================================================
def q3_top_k(items: list[str], k: int) -> list[tuple[str, int]]:
    """Counter 计数 + 自己排序处理并列。"""
    counts = Counter(items)
    # key 是 (-次数, 元素)：
    #   次数降序 -> 取负
    #   元素升序 -> 原样
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:k]


# 为什么不能直接用 most_common(k)：
#   Counter.most_common 用的是 heapq.nlargest，并列时按「插入顺序」返回，
#   也就是取决于元素第一次出现的先后。这是**确定但不直观**的行为，
#   题目要求字典序，所以必须自己排序。
#
# 想要 Top-K 更快的话，可以只取前 k 个而不全排序：
#     heapq.nsmallest(k, counts.items(), key=lambda kv: (-kv[1], kv[0]))
#   O(n log k) 而不是 O(n log n)。n 很大而 k 很小时值得换。
#   本题数据量小，sorted 更直观。


# ======================================================================
# q4 —— 递归展平
# ======================================================================
def q4_flatten(nested: list) -> list:
    """递归下降，遇到 list/tuple 就进去，否则当成叶子。"""
    out = []
    for item in nested:
        if isinstance(item, (list, tuple)):
            out.extend(q4_flatten(item))
        else:
            out.append(item)
    return out


# 关键点：**只把 list/tuple 当容器**。
#   如果写成 `if hasattr(item, "__iter__")` 或者 `try: iter(item)`，
#   字符串就会被当成容器展开成一个个字符，["ab"] 会变成 ["a", "b"]。
#   字符串是「不可再分的原子值」还是「字符序列」，取决于你的业务语义——
#   这里显然应该是前者，所以要显式排除。
#
# extend 而不是 append：extend 把返回的列表逐个元素并进来，
#   append 会把整个列表当成一个元素塞进去，结果是嵌套没变浅。
#
# 递归深度：Python 默认递归上限是 1000 层（sys.getrecursionlimit()）。
#   数据嵌套超过 1000 层会 RecursionError。真实场景要改成显式栈的迭代版本：
#
#       def flatten_iter(nested):
#           stack = list(reversed(nested))
#           out = []
#           while stack:
#               item = stack.pop()
#               if isinstance(item, (list, tuple)):
#                   stack.extend(reversed(item))
#               else:
#                   out.append(item)
#           return out


# ======================================================================
# q5 —— 分块
# ======================================================================
def q5_chunk(seq: list, size: int) -> list[list]:
    """range + 切片，一句搞定。"""
    if size <= 0:
        raise ValueError(f"size 必须为正整数，收到 {size}")
    return [seq[i:i + size] for i in range(0, len(seq), size)]


# 为什么不需要处理最后一组：
#   切片越界不报错。"abcde"[4:6] 得到 ['e']，就这么简单。
#   如果用 C 的思路写成「先算有几组，再逐组循环」，就得处理余数，容易出 bug。
#
# 如果传入的不是序列而是生成器（没有 len、不能切片），得换成：
#     from itertools import islice
#     it = iter(iterable)
#     while chunk := list(islice(it, size)):
#         yield chunk
#   这是模块 05 的内容。


# ======================================================================
# q6 —— 保序去重
# ======================================================================
def q6_dedupe(items: list) -> list:
    """dict.fromkeys 一行搞定。"""
    return list(dict.fromkeys(items))


# dict.fromkeys(iterable) 会创建一个以 iterable 元素为 key、值为 None 的字典。
# 因为 dict 的 key 天然唯一，重复的自动被后写入的覆盖（值都是 None，无所谓）；
# 又因为 dict 在 3.7+ 保证按插入顺序遍历，所以「第一次出现」的顺序被保留下来。
#
# 等价的手写版本：
#     seen = set()
#     out = []
#     for x in items:
#         if x not in seen:
#             seen.add(x)
#             out.append(x)
#     return out
#   这个版本更啰嗦，但它揭示了两件事：
#     1. 需要额外的 set 来做 O(1) 的存在性判断
#     2. 元素必须可哈希（dict.fromkeys 也一样，因为要做 key）
#   如果 items 里有 list 或 dict，两个版本都会抛 TypeError。
#
# 不能用 list(set(items))：set 的迭代顺序由哈希值决定，不保序。


# ======================================================================
# q7 —— 多键排序
# ======================================================================
def q7_sort_records(records: list[dict]) -> list[dict]:
    """key 返回元组，数值取负实现降序。"""
    return sorted(records, key=lambda r: (-r["score"], r["name"]))


# 为什么不能写 sorted(records, key=lambda r: (r["score"], r["name"]), reverse=True)：
#   reverse=True 会把**整个元组**的比较结果反过来，
#   于是 name 也变成降序了 —— 结果会是 ['dave', 'bob', 'alice', 'carl']（错）。
#
# 为什么不能写 (-score, -name)：
#   取负只对数值有意义，字符串没法取负。
#   这就是「数值降序 + 字符串升序」必须用元组混合 key 的原因。
#
# 另一种正解是排两趟（利用 Timsort 的稳定性）：
#     records = sorted(records, key=lambda r: r["name"])          # 先排次要键
#     records = sorted(records, key=lambda r: r["score"], reverse=True)  # 再排主要键
#   多次排序时「先次要后主要」，最后一趟决定主序，稳定性保证前面的顺序不被打乱。
#   数据量大且主要键是字符串（没法取负）时，这个技巧很有用。
#
# 用 sorted 而不是 .sort()：题目要求不改动入参，而且 sorted 能直接接链式调用。


# ======================================================================
# q8 —— 矩阵转置
# ======================================================================
def q8_transpose(matrix: list[list]) -> list[list]:
    """zip(*matrix) —— 星号解包在这里是精髓。"""
    return [list(row) for row in zip(*matrix)]


# zip(*matrix) 展开后是 zip(row0, row1, row2, ...)，
# zip 会把每行的第 i 个元素收成一个元组，正好就是转置后的第 i 行。
#
#     matrix = [[1, 2, 3],
#               [4, 5, 6]]
#     zip(*matrix) -> (1,4) (2,5) (3,6)
#
# 空矩阵：zip(*[]) 就是 zip()，返回空迭代器，所以结果是 []，不用特判。
#
# 返回 list 而不是 tuple：题目要求，而且列表可变更符合矩阵的语义。
#
# 行长度不一致时（锯齿矩阵），zip 会在最短的一行处截断——
# 想按最长的补齐可以用 itertools.zip_longest(matrix, fillvalue=None)。


# ======================================================================
# q9 —— 浅拷贝陷阱
# ======================================================================
def q9_copy_trap() -> tuple[bool, list, list]:
    """一步步照做，让浅拷贝的后果真实发生一次。"""
    original = [[1, 2], [3, 4]]
    shallow = original[:]           # 浅拷贝：只复制外层那个「指针数组」
    shallow[0].append(99)           # 改的是内层列表，两个列表共享的同一个对象
    affected = original != [[1, 2], [3, 4]]     # 原数据确实被改了
    original_after = copy.deepcopy(original)    # 存一份快照，免得后面被 deep 影响

    deep = copy.deepcopy(original)  # 深拷贝：递归复制，内层也是新的
    deep[1].append(88)              # 只影响 deep 自己

    return affected, original_after, deep


# 内存图：
#
#     original ──> [ ptr0, ptr1 ]        外层 list（新拷贝的是这一层）
#                     |      |
#     shallow  ──> [ ptr0, ptr1 ]        两个外层列表的槽位指向同一批子列表
#                     |      |
#                     v      v
#                  [1,2]  [3,4]          内层 list（浅拷贝没有复制这一层）
#
# 所以 shallow[0].append(99) 改的是 [1,2] 这个对象本身，original 自然看得见。
# 而 shallow[0] = [9, 9]（重新赋值而不是改内容）不会影响 original——
# 那只是换掉了 shallow 自己那个槽位里的指针。
#
# deepcopy 的开销：
#   它要递归遍历整个对象图，遇到循环引用还要靠 memo 字典去重。
#   一个 1000x1000 的嵌套列表 deepcopy 一次能跑几百毫秒。
#   能用不可变对象（tuple、frozenset）或者重新构造代替，就别 deepcopy。


# ======================================================================
# q10 —— 循环右移
# ======================================================================
def q10_rotate(seq: list, n: int) -> list:
    """deque.rotate 一行搞定。"""
    dq = deque(seq)
    dq.rotate(n)        # n > 0 右移，n < 0 左移，超出长度自动取模
    return list(dq)


# deque.rotate(k) 等价于「把右边 k 个元素搬到左边」，
# 内部实现是分三段做反转，复杂度 O(n)。
#
# 切片版本（不依赖 deque）：
#     if not seq:
#         return []
#     k = n % len(seq)
#     return seq[-k:] + seq[:-k] if k else list(seq)
#   注意 k == 0 时要特判，否则 seq[-0:] 等于 seq[0:] 就是整个列表，
#   再拼上 seq[:-0]（也是整个列表），结果会变成两倍长度 —— 这是经典 bug。
#   deque 版本没有这个坑，这也是推荐它的原因之一。
#
# 题目要求「不要就地修改入参」，所以先 deque(seq) 复制一份。
# 如果允许就地改，直接对原列表做反转三段法，空间 O(1)，是 LeetCode 189 的解法。


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def t_q1() -> None:
    assert q1_word_count("Hello, hello! World.") == Counter({"hello": 2, "world": 1})
    assert q1_word_count("") == Counter()
    assert q1_word_count("a  \n b\tb") == Counter({"a": 1, "b": 2})
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
    c = Checker("模块 02 · 数据结构精讲 参考答案")
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
