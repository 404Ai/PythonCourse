"""
模块 02 · 数据结构精讲 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

这个文件里最重要的部分是**性能实测**（2.2 和 2.7 节）。
自己机器上跑出来的数字，比任何文档都有说服力。
"""

from __future__ import annotations

import copy
import sys
import time
from collections import Counter, ChainMap, defaultdict, deque, namedtuple


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def bench(label: str, fn, repeat: int = 1) -> float:
    """跑 fn 若干次，返回平均耗时（毫秒）。"""
    fn()                                   # 预热，避免第一次的额外开销影响结果
    t0 = time.perf_counter()
    for _ in range(repeat):
        fn()
    ms = (time.perf_counter() - t0) / repeat * 1000
    print(f"  {label:<44} {ms:>9.2f} ms")
    return ms


# ======================================================================
# 2.1 list 的底层：动态数组与超量分配
# ======================================================================
def demo_list_internals() -> None:
    section("2.1 list 的底层：动态数组与超量分配")

    print("  观察 list 扩容（一个槽位 8 字节，头部固定开销 56 字节）：")
    base = sys.getsizeof([])
    lst = []
    last_cap = 0
    print(f"     {'len':>4}  {'sizeof':>7}  {'已分配槽位':>10}")
    print(f"     {0:>4}  {base:>7}  {0:>10}   <- 空列表")
    for i in range(70):
        lst.append(i)
        cur = sys.getsizeof(lst)
        cap = (cur - base) // 8
        if cap != last_cap:
            print(f"     {len(lst):>4}  {cur:>7}  {cap:>10}   <- 扩容")
            last_cap = cap
    print()
    print("  槽位数的增长序列是 4, 8, 16, 24, 32, 40, 52, 64, 76 ...，")
    print("  不是 1, 2, 3, 4 这样一个个加，而是大约按当前容量的 1/8 多要一点。")
    print("  因为每次按**比例**增长，n 次 append 触发的总拷贝量是几何级数，")
    print("  总和仍是 O(n) —— 这就是『append 均摊 O(1)』的含义。")
    print()

    print("  list 里存的是指针，不是值本身：")
    inner = [1, 2]
    m = [inner] * 3
    print(f"     inner = {inner};  m = [inner] * 3  ->  {m}")
    print(f"     m[0] is m[1] -> {m[0] is m[1]}   <- 三个位置指向同一个列表")
    inner.append(99)
    print(f"     inner.append(99) 之后 m = {m}")
    print("     正确写法：[[1, 2] for _ in range(3)]")


# ======================================================================
# 2.2 复杂度实测
# ======================================================================
def demo_complexity() -> None:
    section("2.2 复杂度实测：为什么选对容器比优化算法更重要")

    n = 20_000
    print(f"  -- 尾部追加 vs 头部插入，n = {n} --")

    def append_loop():
        out = []
        for i in range(n):
            out.append(i)
        return out

    def insert_loop():
        out = []
        for i in range(n):
            out.insert(0, i)          # O(n) 每次
        return out

    t_append = bench("list.append   (均摊 O(1))", append_loop)
    t_insert = bench("list.insert(0)  (O(n) 每次)", insert_loop)
    print(f"     -> insert(0) 慢了约 {t_insert / t_append:.0f} 倍")
    print()

    print("  -- 用 deque 从头部插入 --")

    def deque_loop():
        out = deque()
        for i in range(n):
            out.appendleft(i)         # O(1)
        return out

    t_deque = bench("deque.appendleft  (O(1))", deque_loop)
    print(f"     -> deque 比 list.insert(0) 快约 {t_insert / t_deque:.0f} 倍")
    print()

    print("  -- 成员判断：list vs set，各做 1000 次查询 --")
    big_n = 200_000
    data_list = list(range(big_n))
    data_set = set(data_list)
    probes = list(range(big_n, big_n + 1000))

    def probe_list():
        return [p in data_list for p in probes]

    def probe_set():
        return [p in data_set for p in probes]

    t_list = bench(f"x in list   (n={big_n}, 1000 次)", probe_list)
    t_set = bench(f"x in set    (n={big_n}, 1000 次)", probe_set)
    print(f"     -> set 快约 {t_list / t_set:.0f} 倍")
    print()
    print("  结论：循环里反复做成员判断时，先把容器转成 set。")
    print("        这是 Python 里性价比最高的一处优化。")


# ======================================================================
# 2.3 切片
# ======================================================================
def demo_slicing() -> None:
    section("2.3 切片：不会越界，永远返回新对象")

    s = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
    print(f"     s              = {s}")
    print(f"     s[2:5]         = {s[2:5]}")
    print(f"     s[:3]          = {s[:3]}")
    print(f"     s[7:]          = {s[7:]}")
    print(f"     s[::2]         = {s[::2]}")
    print(f"     s[::-1]        = {s[::-1]}   <- 反转的惯用法")
    print(f"     s[-3:]         = {s[-3:]}")
    print(f"     s[100:200]     = {s[100:200]}     <- 越界不报错，返回空")
    print(f"     s[5:2]         = {s[5:2]}     <- 起点在终点后面也是空")
    print()

    a = [0, 1, 2, 3, 4, 5]
    print(f"     切片赋值前 a = {a}")
    a[1:4] = [9]
    print(f"     a[1:4] = [9]        -> {a}   3 个换 1 个，长度变了")
    a[1:1] = [7, 7]
    print(f"     a[1:1] = [7, 7]     -> {a}   在位置 1 插入")
    del a[::2]
    print(f"     del a[::2]          -> {a}   删除所有偶数下标")
    print()

    print("  -- 切片是浅拷贝（本模块最容易踩的坑）--")
    matrix = [[1, 2], [3, 4]]
    rows = matrix[:]
    rows[0].append(99)
    print(f"     matrix = [[1, 2], [3, 4]];  rows = matrix[:]")
    print(f"     rows[0].append(99) 之后 matrix = {matrix}")
    print("     ^ 外层是新列表，但内层子列表还是共享的。")


# ======================================================================
# 2.4 解包
# ======================================================================
def demo_unpacking() -> None:
    section("2.4 解包：让代码短一半")

    x, y = 1, 2
    print(f"     x, y = 1, 2            -> x={x} y={y}")
    x, y = y, x
    print(f"     x, y = y, x            -> x={x} y={y}   （不需要临时变量）")

    first, *rest = [1, 2, 3, 4]
    print(f"     first, *rest           -> first={first}  rest={rest}")
    *init, last = [1, 2, 3, 4]
    print(f"     *init, last            -> init={init}  last={last}")
    a, *mid, b = [1, 2, 3, 4]
    print(f"     a, *mid, b             -> a={a}  mid={mid}  b={b}")
    print("     注意：rest/mid/init 永远是 list，哪怕只有一个或零个元素。")

    args = [1, 2, 3]
    print(f"     print(*[1, 2, 3])      -> ", end="")
    print(*args)
    print(f"     print(*args, sep=' | ') -> ", end="")
    print(*args, sep=" | ")
    print("     ^ 调用时的 * 是『把可迭代对象展开成位置参数』，")
    print("       和定义时的 def f(*args)（收集成元组）方向正好相反。")

    matrix = [[1, 2, 3], [4, 5, 6]]
    print(f"     矩阵转置 list(zip(*matrix)) = {list(zip(*matrix))}")


# ======================================================================
# 2.5 dict
# ======================================================================
def demo_dict() -> None:
    section("2.5 dict：哈希表、有序性与常用操作")

    d = {"a": 1, "b": 2}
    d["c"] = 3
    d["a"] = 99
    print(f"     d = {d}   <- 3.7 起保证按插入顺序遍历")
    print(f"     d.get('zzz')       -> {d.get('zzz')}     不存在返回 None")
    print(f"     d.get('zzz', 0)    -> {d.get('zzz', 0)}")
    print(f"     d.setdefault('a', 0) -> {d.setdefault('a', 0)}   已存在，原值不变")
    print(f"     d.setdefault('z', 0) -> {d.setdefault('z', 0)}   不存在，顺手插入")
    print(f"     之后 d = {d}")
    print()

    print("  -- 合并字典 --")
    e = {"x": 1}
    f = {"y": 2}
    print(f"     {{**e, **f}}   -> {dict(**e, **f)}   （3.5+）")
    print(f"     e | f          -> {e | f}   （3.9+，推荐）")
    g = dict(e)
    g |= f
    print(f"     g |= f         -> {g}   （就地合并）")
    print()

    print("  -- hash 与可哈希性 --")
    print(f"     hash(42)     = {hash(42)}")
    print(f"     hash('abc')  = {hash('abc')}   <- 每次启动进程都不一样（哈希随机化）")
    print(f"     hash((1, 2)) = {hash((1, 2))}")
    for bad in ([1, 2], {"k": 1}, {1, 2}):
        try:
            hash(bad)
        except TypeError as exc:
            print(f"     hash({bad}) -> TypeError: {exc}")
    print("     可哈希 = 不可变 + (a == b 时必有 hash(a) == hash(b))")
    print("     这就是 list 不能当 key、tuple 可以的原因。")
    print()

    print("  -- 视图对象会随字典变化 --")
    d2 = {"a": 1}
    keys = d2.keys()
    print(f"     keys = d2.keys()  -> {keys}")
    d2["b"] = 2
    print(f"     d2['b'] = 2 之后 keys -> {keys}   <- 是视图，不是快照")
    print()

    print("  -- 遍历时修改会炸 --")
    d3 = {"a": 1, "b": 2, "c": 3}
    try:
        for k in d3:
            del d3[k]
    except RuntimeError as exc:
        print(f"     直接删 -> RuntimeError: {exc}")
    d3 = {"a": 1, "b": 2, "c": 3}
    d3 = {k: v for k, v in d3.items() if k != "b"}
    print(f"     构造新字典 -> {d3}   <- 推荐写法")


# ======================================================================
# 2.6 set
# ======================================================================
def demo_set() -> None:
    section("2.6 set：把 O(n) 变成 O(1)")

    a = {1, 2, 3, 4}
    b = {3, 4, 5, 6}
    print(f"     a = {a}   b = {b}")
    print(f"     a | b  (并集)     = {a | b}")
    print(f"     a & b  (交集)     = {a & b}")
    print(f"     a - b  (差集)     = {a - b}")
    print(f"     a ^ b  (对称差)   = {a ^ b}")
    print(f"     a <= b (子集)     = {a <= b}")
    print(f"     a.isdisjoint(b)   = {a.isdisjoint(b)}")
    print()

    print(f"     set() 才是空集合，{{}} 是空字典：type(set()) = {type(set()).__name__}, "
          f"type({{}}) = {type({}).__name__}")
    print()

    items = [3, 1, 3, 2, 1]
    print(f"     原列表 {items}")
    print(f"     list(set(items))          -> {list(set(items))}   不保序")
    print(f"     list(dict.fromkeys(items)) -> {list(dict.fromkeys(items))}   保序（推荐）")


# ======================================================================
# 2.7 推导式
# ======================================================================
def demo_comprehension() -> None:
    section("2.7 推导式：更快，但不一定更可读")

    squares = {x * 2 for x in range(5)}
    dbl_map = {x: x * 2 for x in range(3)}
    print(f"     [x*2 for x in range(5)]              -> {[x * 2 for x in range(5)]}")
    print(f"     {{x*2 for x in range(5)}}              -> {squares}   （集合，无序）")
    print(f"     {{x: x*2 for x in range(3)}}           -> {dbl_map}   （字典推导）")
    print(f"     [x for x in range(10) if x % 2 == 0] -> {[x for x in range(10) if x % 2 == 0]}")
    print(f"     [x if x > 0 else -x for x in [-2, 3]] -> {[x if x > 0 else -x for x in [-2, 3]]}")
    print(f"     [x+y for x in 'ab' for y in '12']    -> {[x + y for x in 'ab' for y in '12']}")
    print("     ^ 注意 if 在 for 之后是『过滤』，在 for 之前是『三目表达式』，含义完全不同。")
    print()

    print("  -- 性能对比：100 万次乘 2 --")
    N = 1_000_000

    def with_loop():
        out = []
        for i in range(N):
            out.append(i * 2)
        return out

    def with_comprehension():
        return [i * 2 for i in range(N)]

    def with_generator_sum():
        return sum(i * 2 for i in range(N))

    t_loop = bench("for 循环 + append", with_loop)
    t_comp = bench("列表推导式 [i*2 for i in range(N)]", with_comprehension)
    t_gen = bench("sum(i*2 for i in range(N))  惰性，省内存", with_generator_sum)
    print(f"     -> 推导式比 for + append 快约 {(t_loop / t_comp - 1) * 100:.0f}%")
    print("     原因：推导式在字节码层面用 LIST_APPEND 专用指令，")
    print("           省掉了每轮 LOAD_FAST out / LOAD_METHOD append / CALL 的开销。")
    print()

    print("  -- 但可读性优先：这种就该退回 for 循环 --")
    print("     [x.strip().lower() for x in lines if x.strip()")
    print("      and not x.startswith('#') and len(x.strip()) > 3]   <- 太挤了")


# ======================================================================
# 2.8 排序
# ======================================================================
def demo_sorting() -> None:
    section("2.8 排序：稳定性与多键排序")

    words = ["banana", "Apple", "cherry", "date"]
    print(f"     sorted(words, key=len)      -> {sorted(words, key=len)}")
    print(f"     sorted(words, key=str.lower) -> {sorted(words, key=str.lower)}")
    print()

    nums = [3, 1, 2]
    result = nums.sort()
    print(f"     nums.sort() 的返回值是 {result}   <- 返回 None！")
    print(f"     但 nums 本身已经变成 {nums}")
    print("     这是 Python 的约定：就地修改的方法一律返回 None，提醒你是原地操作。")
    print()

    records = [
        {"name": "bob", "score": 90},
        {"name": "alice", "score": 90},
        {"name": "carl", "score": 85},
        {"name": "dave", "score": 95},
    ]
    print("  -- 需求：分数降序，分数相同的按姓名升序 --")
    one_pass = sorted(records, key=lambda r: (-r["score"], r["name"]))
    print("     一次排序（数值取负实现降序）：")
    for r in one_pass:
        print(f"        {r['name']:<6} {r['score']}")

    two_pass = sorted(records, key=lambda r: r["name"])
    two_pass.sort(key=lambda r: r["score"], reverse=True)
    print("     两趟排序（利用 Timsort 的稳定性，先排次要键再排主要键）：")
    for r in two_pass:
        print(f"        {r['name']:<6} {r['score']}")
    print()
    print("     注意：reverse=True 会影响整个 key，所以『数值降序 + 字符串升序』")
    print("           只能用元组那一招（数值取负，字符串不动）。")

    import heapq

    big = [5, 1, 9, 3, 7, 2, 8]
    print()
    print(f"     heapq.nlargest(3, {big}) -> {heapq.nlargest(3, big)}   （O(n log k)，不必全排序）")


# ======================================================================
# 2.9 collections
# ======================================================================
def demo_collections() -> None:
    section("2.9 collections：四件宝")

    c = Counter("abracadabra")
    print(f"     Counter('abracadabra')        = {dict(c)}")
    print(f"     c.most_common(3)              = {c.most_common(3)}")
    print(f"     c['不存在的键']                = {c['不存在的键']}   <- 不报错，返回 0")
    print(f"     '不存在的键' in c              = {'不存在的键' in c}   <- 要区分『没有』和『零』用这个")
    print()

    data = [("水果", "苹果"), ("蔬菜", "白菜"), ("水果", "香蕉"), ("蔬菜", "萝卜")]
    groups = defaultdict(list)
    for k, v in data:
        groups[k].append(v)
    print(f"     defaultdict(list) 分组        = {dict(groups)}")
    print()

    d = defaultdict(list)
    _ = d["随手一读"]                       # 只是想读，却改了数据
    print(f"     d = defaultdict(list); _ = d['随手一读']  -> len(d) = {len(d)}")
    print("     ^ 读取不存在的键会顺手插入！纯判断请用 `in` 或 `.get()`。")
    print()

    dq = deque([1, 2, 3])
    dq.appendleft(0)
    dq.append(4)
    print(f"     deque 两端操作都是 O(1)：{dq}")
    dq.rotate(2)
    print(f"     dq.rotate(2)                  -> {dq}")
    print()

    win = deque(maxlen=3)
    for i in range(6):
        win.append(i)
    print(f"     deque(maxlen=3) 喂 0~5        -> {win}   <- 天然的滑动窗口")
    print()

    Point = namedtuple("Point", ["x", "y"])
    p = Point(3, 4)
    print(f"     namedtuple: p = {p}   p.x = {p.x}   p[0] = {p[0]}   tuple(p) = {tuple(p)}")
    print()

    cfg = ChainMap({"color": "blue"}, {"color": "red", "size": "M"})
    print(f"     ChainMap 查找 color -> {cfg['color']!r}   查找 size -> {cfg['size']!r}")


# ======================================================================
# 2.10 拷贝
# ======================================================================
def demo_copy() -> None:
    section("2.10 浅拷贝 vs 深拷贝")

    original = [[1, 2], [3, 4]]
    shallow = original[:]
    shallow[0].append(99)
    print(f"     original = [[1, 2], [3, 4]]")
    print(f"     shallow = original[:]")
    print(f"     shallow[0].append(99)")
    print(f"     -> original = {original}   <- 被连累了")
    print(f"     -> shallow  = {shallow}")
    print()

    original = [[1, 2], [3, 4]]
    deep = copy.deepcopy(original)
    deep[0].append(99)
    print(f"     换成 copy.deepcopy：")
    print(f"     -> original = {original}   <- 安然无恙")
    print(f"     -> deep     = {deep}")
    print()

    print("     各种拷贝方式对照：")
    a = [[1], [2]]
    print(f"       a[:]           is a          -> {a[:] is a}   浅")
    print(f"       list(a)        is a          -> {list(a) is a}   浅")
    print(f"       a.copy()       is a          -> {a.copy() is a}   浅")
    print(f"       copy.copy(a)   is a          -> {copy.copy(a) is a}   浅")
    print(f"       deepcopy(a)    is a          -> {copy.deepcopy(a) is a}   深")
    print(f"       a[:][0]        is a[0]       -> {a[:][0] is a[0]}   <- 浅拷贝共享内层")
    print(f"       deepcopy(a)[0] is a[0]       -> {copy.deepcopy(a)[0] is a[0]}   <- 深拷贝不共享")


# ======================================================================
def main() -> None:
    demo_list_internals()
    demo_complexity()
    demo_slicing()
    demo_unpacking()
    demo_dict()
    demo_set()
    demo_comprehension()
    demo_sorting()
    demo_collections()
    demo_copy()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
