"""
模块 05 · 迭代器、生成器、上下文管理器 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每个答案下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。
"""

from __future__ import annotations

import itertools
import os
import sys
import time
from collections import deque
from collections.abc import Iterable, Iterator
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 手写迭代器类
# ======================================================================
class Fibonacci:
    """用两个变量滚动推进，不需要保存整个数列。

    _a 是「下一个要产出的数」，_b 是它后面那个。
    每次产出 _a，然后把 (_a, _b) 更新成 (_b, _a + _b)。
    """

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self._a = 1
        self._b = 1

    def __iter__(self) -> "Fibonacci":
        return self          # 迭代器协议要求返回自己

    def __next__(self) -> int:
        if self._a > self.limit:
            raise StopIteration      # 结束信号，不是错误
        value = self._a
        self._a, self._b = self._b, self._a + self._b
        return value


# 常见错误写法：
#
# 1) __iter__ 里写 `return iter(self)`
#    这会无限递归：iter(self) 又去调 self.__iter__()…… 最后 RecursionError。
#    迭代器的 __iter__ 就该老老实实 `return self`。
#
# 2) 在 __next__ 里 `return None` 表示结束
#    None 是个合法的值（如果序列里本来就有 None，语义就乱了）。
#    结束只有一种方式：抛 StopIteration。
#
# 3) 把整个数列预先算好存进 list，__next__ 里 pop(0)
#    pop(0) 是 O(n)，而且失去了「惰性」的意义。
#    迭代器的价值就在于「不把所有数据都放在内存里」。
#
# 4) 用 self.n 当计数器但从 0 开始
#    斐波那契前两项都是 1，边界很容易差一。写之前先手算 limit=0/1/2 三个用例。
#
# 5) 忘了「迭代器是一次性的」
#    这个类的 __iter__ 返回 self，所以 list(f) 之后再 list(f) 就是空的。
#    这是**正确**的行为（和文件对象一致），但要在文档里说清楚。
#    要反复遍历就得把「数据源」和「游标」拆成两个类。


# ======================================================================
# q2 —— 生成器：滑动窗口
# ======================================================================
def sliding_window(iterable: Iterable, n: int) -> Iterator[tuple]:
    """deque(maxlen=n) 是为这个场景量身定做的：

    往右端 append，超过 maxlen 时左端自动弹出，
    所以窗口里永远只有最近 n 个元素，内存是 O(n) 而不是 O(len(iterable))。
    """
    if n <= 0:
        raise ValueError(f"窗口大小必须为正数，收到 {n}")

    window: deque = deque(maxlen=n)
    for item in iterable:
        window.append(item)
        if len(window) == n:      # 还没攒够 n 个时不产出
            yield tuple(window)   # 转成 tuple：deque 会变，产出必须是快照


# 常见错误写法：
#
# 1) 先物化再切片
#       data = list(iterable)
#       for i in range(len(data) - n + 1):
#           yield tuple(data[i:i + n])
#    能跑，但：内存 O(全部数据)，而且输入必须是可重复遍历的序列 ——
#    传进来一个生成器就直接废了。**迭代器的题目里出现 list(iterable) 就要警觉。**
#
# 2) yield window 而不是 yield tuple(window)
#    deque 是同一个对象，之后每次 append 都会改到它。
#    调用方收集起来会得到一堆内容相同的窗口（全是最后一个）。
#    这是「可变对象别名」的经典变体。
#
# 3) 用 list 当窗口然后 pop(0)
#    pop(0) 是 O(n)，整个算法退化成 O(n*m)。deque 的 popleft 才是 O(1)。
#
# 4) 忘了 n <= 0 的检查
#    deque(maxlen=0) 永远不 append 任何东西，于是静默产出空序列 ——
#    静默的错误比 ValueError 难查得多。
#
# 5) 把参数校验写在生成器外面
#    注意：生成器函数体在**第一次 next() 时**才开始执行，
#    所以这里 `if n <= 0: raise` 也是延迟到遍历时才触发的。
#    想立刻报错就得拆成「普通函数做校验 + 内部生成器干活」两层。
#    这是惰性的代价之一，知道有这回事就行。


# ======================================================================
# q3 —— 生成器：惰性读取文件
# ======================================================================
def read_clean_lines(path: str | Path) -> Iterator[str]:
    """文件对象本身就是迭代器，`for line in f` 一次只读一行。

    with 保证无论正常结束、break 还是抛异常，文件都会被关闭。
    """
    with open(path, encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            yield stripped


# 常见错误写法：
#
# 1) lines = open(path).readlines() 然后再逐个 yield
#    这样整个文件已经进内存了，「惰性」完全是假的。
#    而且文件句柄在函数返回前不会关（如果不用 with 就更糟）。
#
# 2) 不用 with，手写 f = open(...) / f.close()
#    一旦循环体抛异常，close() 永远不会执行，句柄泄漏。
#    在 Windows 上还表现为「文件被占用，删不掉」。
#
# 3) 不写 encoding="utf-8"
#    Python 会用 locale 的默认编码。Windows 中文环境是 GBK，
#    于是同样的代码在 Linux 上跑得好好的，到你机器上就 UnicodeDecodeError。
#    **跨平台代码里 open() 不写 encoding 一律算 bug。**
#
# 4) 判断注释用 `line[0] == "#"`
#    行首可能有空格（缩进的注释），而且空行会让 line[0] 抛 IndexError。
#    先 strip() 再判断才对。
#
# 5) 用 line.strip() 去掉行尾的 '\n'
#    对大多数文本没问题，但如果要保留行内的有意义空白就得小心。
#    更精确的写法是 line.rstrip('\n')。


# ======================================================================
# q4 —— itertools：两数之和配对
# ======================================================================
def two_sum_pairs(nums: list[int], target: int) -> list[tuple[int, int]]:
    """combinations(range(len(nums)), 2) 正好枚举所有 i < j 的下标对。

    用列表推导而不是双重 for，是想说：**「枚举所有无序对」是个组合问题，
    标准库已经把它抽象好了**，没必要自己写两层循环加边界判断。
    """
    return [
        (i, j)
        for i, j in itertools.combinations(range(len(nums)), 2)
        if nums[i] + nums[j] == target
    ]


# 常见错误写法：
#
# 1) 用 permutations(range(len(nums)), 2)
#    会同时产出 (0, 1) 和 (1, 0)，结果里每对出现两次。
#    **顺序重要吗？** 重要用 permutations，不重要用 combinations。
#
# 2) 双重 for + 手动管理下标
#       for i in range(len(nums)):
#           for j in range(i + 1, len(nums)):
#   能跑，但 i + 1 这个边界、以及「忘写 +1 导致自己和自己配对」是高频 bug。
#
# 3) 用 product(range(len(nums)), repeat=2) 然后过滤 i < j
#    产出的元素数量是 n²，其中一半要被丢掉 —— 浪费。
#    combinations 直接产出 C(n,2) 个，不多不少。
#
# 4) 返回 [(nums[i], nums[j])] 而不是下标对
#    题目要的是下标对。**读清题目要什么再动手。**
#    而且返回数值的话，有重复元素时根本分不清是哪两个。
#
# 5) 只找一个解就 return
#    「所有配对」意味着要穷举，中途 return 会漏。


# ======================================================================
# q5 —— 上下文管理器（类实现）
# ======================================================================
class Timer:
    def __init__(self) -> None:
        self.elapsed = 0.0
        self._start = 0.0

    def __enter__(self) -> "Timer":
        # perf_counter 是单调时钟，专门用来测耗时；
        # time.time() 会被系统时间调整（NTP 同步、夏令时）影响，不能用来测耗时。
        self._start = time.perf_counter()
        return self          # 返回 self，调用方才能 `as t` 拿到这个对象

    def __exit__(self, exc_type, exc, tb) -> None:
        # 不管有没有异常，__exit__ 一定会被调用 —— 所以这里算出来的耗时是对的。
        self.elapsed = time.perf_counter() - self._start
        # 显式返回 None = 不吞异常。写出来是为了让人一眼看到「这里没吞」。
        return None


# 常见错误写法：
#
# 1) __enter__ 不 return（或 return None）
#    `with Timer() as t` 里 t 会变成 None，然后 t.elapsed 就 AttributeError。
#    记住：**as 绑的是 __enter__ 的返回值，不是 with 后面那个表达式。**
#
# 2) __exit__ 里写 `return True`
#    块内的所有异常都会人间蒸发。这种 bug 极难查：
#    程序不崩、不报错，只是后面的逻辑走错了分支。
#
# 3) 用 time.time() 计时
#    系统时间被 NTP 校准或者用户手动改时间时，你会得到负数或者荒谬的值。
#    **测耗时一律用 time.perf_counter()。**
#
# 4) 把耗时打印在 __exit__ 里而不是存起来
#    能用，但调用方就拿不到数据、没法做聚合分析了。
#    存到 self 上更灵活，打印是调用方的事。
#
# 5) 以为 __exit__ 只在正常情况下被调用
#    它**一定会**被调用（包括异常、break、return）。
#    这正是上下文管理器存在的意义 —— 正常路径你自己多写一行也行，
#    异常路径你多半会忘。


# ======================================================================
# q6 —— 上下文管理器（@contextmanager）
# ======================================================================
@contextmanager
def temp_env(name: str, value: str) -> Iterator[None]:
    """yield 之前 = __enter__，之后 = __exit__。

    「原本不存在就删掉」这一条是这类工具的灵魂：
    用 os.environ[name] = "" 恢复的话，程序看起来一切正常，
    但依赖 `"KEY" in os.environ` 判断的代码会走进完全不同的分支。
    """
    old = os.environ.get(name)        # 不存在时是 None
    os.environ[name] = value
    try:
        yield                          # 这里把控制权交给 with 块
    finally:
        # 必须放 finally：块内抛异常时也要恢复
        if old is None:
            os.environ.pop(name, None)   # 原本没有 -> 删掉
        else:
            os.environ[name] = old       # 原本有 -> 还原


# 常见错误写法：
#
# 1) yield 不包在 try/finally 里
#       @contextmanager
#       def temp_env(name, value):
#           old = os.environ.get(name)
#           os.environ[name] = value
#           yield
#           os.environ[name] = old        # 异常时这行不会执行！
#    这是本题最重要的一课。with 块内一旦抛异常，异常会从 yield 处抛出来，
#    直接穿过函数体，后面的清理代码全被跳过。
#    **验收标准很简单：把 with 块改成 raise，环境变量还恢复得了吗？**
#
# 2) 恢复时写 os.environ[name] = old，而 old 可能是 None
#    os.environ 只接受 str，赋 None 会 TypeError。
#    所以必须先判断「原本有没有」。
#
# 3) 用 `if name in os.environ` 判断之后再用 os.environ[name] 取值
#    能用，但多一次查找。`os.environ.get(name)` 一次搞定，
#    而且「None 表示不存在」在环境变量这个场景下是安全的
#    （环境变量的值永远是 str，不可能是 None）。
#
# 4) 用 pop(name) 而不是 pop(name, None)
#    并发场景下别人可能已经删掉了，pop 会 KeyError。
#    清理代码里一律用带默认值的 pop。
#
# 5) 忘记 os.environ 的修改是**进程级全局**的
#    这个工具不适合在多个线程里同时改同一个变量。
#    测试并发代码时要注意。


# ======================================================================
# q7 —— groupby 分组
# ======================================================================
def group_by_key(records: list[tuple[str, int]]) -> dict[str, list[tuple[str, int]]]:
    """先排序，再 groupby，最后立刻 list() 物化每一组。

    三步缺一不可：
        sorted   —— groupby 只合并相邻的相同 key
        groupby  —— 惰性地产出 (key, group_iterator)
        list     —— group 是共享迭代器，下一轮就失效
    """
    ordered = sorted(records, key=lambda record: record[0])
    return {
        key: list(group)                                   # 立刻物化，不能省
        for key, group in itertools.groupby(ordered, key=lambda record: record[0])
    }


# 常见错误写法：
#
# 1) 不排序直接用 groupby
#    输入 [("水果",1), ("蔬菜",2), ("水果",3)] 会产出三组：
#    水果 / 蔬菜 / 水果。**「同一个 key 出现多次」正是这个 bug 的症状。**
#    groupby 不排序是设计使然 —— 它要的是「流式处理」，
#    想一遍扫描就分组，就只能合并相邻的。
#    （真需要「不排序也能分组」就用 collections.defaultdict(list) 或 Counter。）
#
# 2) 直接存 group，不 list()
#       {key: group for key, group in groupby(...)}      # 错
#    存下来的是迭代器，等字典推导走到下一组时，上一组的迭代器已经被推进了，
#    读出来全是空列表或者错的内容。
#    **看到 groupby 的返回值，第一个念头就该是 `list(group)`。**
#
# 3) 用 sorted 排完序就以为万事大吉，但排序的 key 和 groupby 的 key 不一致
#       sorted(records, key=lambda r: r[1])
#       groupby(ordered, key=lambda r: r[0])             # 错
#    排序和分组必须用**同一个** key，否则等于没排序。
#
# 4) 手写双重循环 + set 去重
#    那就是把 itertools 已有的能力重造一遍，还容易写错。
#
# 5) 忘了 groupby 是「惰性」的，把整个 groupby 对象存起来以后再用
#    比如 `groups = groupby(...)` 然后过一会儿再遍历 —— 那时底层数据可能
#    已经被别的地方推进过了。**惰性对象要立刻消费掉。**


# ======================================================================
# q8 —— itertools 综合运用
# ======================================================================
def running_max(numbers: list[int]) -> list[int]:
    """accumulate 的第二个参数是「累积函数」，默认是加法。

    传 max 就得到前缀最大值，传 min 就是前缀最小值，
    传 operator.mul 就是前缀积 —— 一个函数顶一堆手写循环。
    """
    return list(itertools.accumulate(numbers, max))


def first_n(iterable: Iterable, n: int) -> list:
    """islice 的唯一正确用途：给无限/惰性序列「限量」。

    注意 islice 不支持负数索引、不支持 len()，因为它在流上工作，
    根本不知道总长度。
    """
    return list(itertools.islice(iterable, n))


def successive_diffs(numbers: list[int]) -> list[int]:
    """pairwise（3.10+）就是「相邻两项」。

    以前要写 zip(numbers, numbers[1:])，那个写法有两个毛病：
    对迭代器无效（不能切片），而且会多复制一份列表。
    """
    return [later - earlier for earlier, later in itertools.pairwise(numbers)]


def flatten(nested: list[list[int]]) -> list[int]:
    """chain.from_iterable 展平一层。

    注意是 `chain.from_iterable(nested)`，不是 `chain(nested)`：
    后者把 nested 当成一个可迭代对象，产出的是 [[1,2], [3]] 这种**子列表本身**。
    """
    return list(itertools.chain.from_iterable(nested))


# 常见错误写法：
#
# 1) flatten 写成 chain(*nested)
#    能跑，但 `*` 会把所有子列表**一次性展开成参数**。
#    子列表有十万个就直接 RecursionError / 内存爆掉。
#    chain.from_iterable 是惰性的，只一个个取。
#
# 2) first_n 里写 iterable[:n]
#    对列表能跑，对生成器直接 TypeError。
#    **看到切片就要想：这个参数一定是序列吗？**
#
# 3) successive_diffs 里写 zip(numbers, numbers[1:])
#    对 list 能跑，对生成器报错，而且 numbers[1:] 复制了一份。
#    pairwise 存在的意义就是把这两个问题一起解决。
#
# 4) running_max 里手写循环维护一个 best 变量
#    能用，但 accumulate 的意图更清楚，而且不用自己处理空序列。
#
# 5) 结果不包 list()
#    accumulate / islice / pairwise / chain 全都返回**迭代器**，
#    不包 list() 的话断言会拿到 <itertools.accumulate object>，
#    而且打印出来没法看。


# ======================================================================
# q9 —— __missing__ / 字典合并 / zip strict
# ======================================================================
class CountDict(dict):
    """__missing__ 只在 d[key] 找不到时被调用。

    和 defaultdict 的区别：
        - defaultdict 每次访问都新建默认值，工厂函数拿不到 key
        - __missing__ 能拿到 key，可以写「按 key 算默认值」的逻辑
          （比如按 key 去数据库查一次再缓存）
    """

    def __missing__(self, key):
        self[key] = 0        # 顺手写回去，下次就是真命中
        return 0


def merge_configs(*configs: dict) -> dict:
    """用 `|` 逐个合并，每次都是**新建**一个字典。

    这意味着输入字典不会被改动 —— 这点很重要：
    调用方传进来的可能是别人的配置对象，就地 update 会污染它。
    """
    result: dict = {}
    for config in configs:
        result = result | config      # 新建，不是 |=
    return result


def all_positive_pairs(names: list[str], scores: list[int]) -> bool:
    """先 zip 物化一次，再交给 all 判断。

    为什么要先 list()：如果直接把 `zip(..., strict=True)` 生成的迭代器
    丢给 all()，all 一遇到假值就短路，后面的元素根本不会被取，
    「长度不一致」这个检查就可能轮不到执行。
    先物化能保证长度检查一定发生 —— 这就是「惰性」和「短路」撞在一起的坑。
    """
    pairs = list(zip(names, scores, strict=True))
    return all(score > 0 for _, score in pairs)


# 常见错误写法：
#
# 1) __missing__ 里只 return 0，不写回字典
#       def __missing__(self, key):
#           return 0
#    功能上计数是对的，但 `"新键" in d` 永远是 False ——
#    后面依赖「键存在」的代码会走错分支。
#    （不过有些场景下「不写回」才是想要的，要看语义。这里题目明确要求写回。）
#
# 2) 以为 get() 也会触发 __missing__
#    不会。get() / in / setdefault 都绕过 __missing__。
#    所以 c.get("新键") 返回 None，而 c["新键"] 返回 0 —— 两者行为不同是正常的。
#
# 3) 用 defaultdict(int) 代替
#    效果类似（defaultdict 也会把键建出来），但 defaultdict 的工厂函数
#    拿不到 key。题目要求用 __missing__，是为了让你掌握「默认值依赖 key」的能力。
#
# 4) merge_configs 里用 dict.update 就地改
#       result = configs[0]
#       for cfg in configs[1:]:
#           result.update(cfg)        # 错：改到了 configs[0] 本身
#    调用方的字典被悄悄改了，这种 bug 在多个模块共享配置对象时极难查。
#
# 5) 自己写 if len(a) != len(b): raise ValueError
#    能做，但 zip(strict=True) 是标准库替你做的，
#    而且它报告的是「哪个参数更短」，信息更全。
#    **3.10+ 的代码里，只要两个序列「应该一样长」，就一律写 strict=True。**
#
# 6) 用 zip 的默认行为（静默截断）
#    最危险的写法：长度不匹配时不报错，只是少算了几条。
#    你会看到「结果对不上但也不报错」，然后开始怀疑人生。


# ======================================================================
# 自测（和 exercises.py 保持一致）
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
    import time as time_module

    with Timer() as t:
        assert isinstance(t, Timer), "__enter__ 必须返回 self"
    assert isinstance(t.elapsed, float), f"elapsed 应该是 float，实际 {type(t.elapsed).__name__}"
    assert t.elapsed >= 0.0

    with Timer() as t2:
        time_module.sleep(0.02)
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

    sorted_records = sorted(records, key=lambda r: r[0])
    assert group_by_key(sorted_records) == got

    assert "groupby" in inspect.getsource(group_by_key), "要求用 itertools.groupby"

    for group in got.values():
        assert isinstance(group, list), f"每组必须是 list，实际是 {type(group).__name__}"


def t_q8() -> None:
    import inspect
    import itertools as it_module

    assert running_max([3, 1, 4, 1, 5]) == [3, 3, 4, 4, 5], f"实际 {running_max([3, 1, 4, 1, 5])}"
    assert running_max([]) == []
    assert running_max([-1, -5, -3]) == [-1, -1, -1]

    assert first_n(it_module.count(), 4) == [0, 1, 2, 3], "无限迭代器也要能取"
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
    c = Checker("模块 05 · 迭代器、生成器、上下文管理器 参考答案")
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
