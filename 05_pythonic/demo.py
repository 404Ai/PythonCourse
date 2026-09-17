"""
模块 05 · 迭代器、生成器、上下文管理器 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. 猜一下这段代码会输出什么
    3. 再跑，看是否和你想的一样

这个文件的三个主题其实是同一件事的三个面：
    惰性求值  在数据流上 = 迭代器
             在函数上   = 生成器
             在资源上   = 上下文管理器
"""

from __future__ import annotations

import itertools as it
import os
import sys
import time
import tracemalloc
from contextlib import contextmanager, suppress


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ======================================================================
# 5.1 可迭代对象 vs 迭代器
# ======================================================================
def demo_iter_protocol() -> None:
    section("5.1 可迭代对象 vs 迭代器：__iter__ / __next__ / StopIteration")

    print("  iter() 拿到迭代器，next() 一个个取，取完抛 StopIteration：")
    iterator = iter([1, 2, 3])
    print(f"     type(iter([1,2,3]))  -> {type(iterator).__name__}")
    while True:
        try:
            item = next(iterator)
        except StopIteration:
            print("     取完了 -> StopIteration（这是正常控制流，不是错误）")
            break
        print(f"     next() -> {item}")
    print()

    print("  判断一个东西是不是『迭代器』，只需看 iter(x) is x：")
    for name, obj in (("list", [1, 2, 3]), ("str", "abc"), ("range", range(3)),
                      ("dict", {"a": 1}), ("file-like", iter([1]))):
        print(f"     {name:<10} iter(obj) is obj -> {iter(obj) is obj}")
    print("     列表/字符串/range 都是『可迭代对象』，不是迭代器 ——")
    print("     它们每次 iter() 都造一个新的迭代器出来，所以能反复遍历。")
    print()

    print("  for 循环的完整展开：")
    print("     _it = iter(obj)                <- 只做一次")
    print("     while True:")
    print("         try: x = next(_it)")
    print("         except StopIteration: break")
    print("         handle(x)")
    print()

    print("  手写一个迭代器：")

    class Countdown:
        def __init__(self, n: int) -> None:
            self.n = n

        def __iter__(self):
            return self              # 迭代器必须返回自己

        def __next__(self):
            if self.n <= 0:
                raise StopIteration
            self.n -= 1
            return self.n + 1

    c = Countdown(3)
    print(f"     list(Countdown(3))   -> {list(Countdown(3))}")
    print(f"     list(c)              -> {list(c)}")
    print(f"     list(c) 再来一次      -> {list(c)}     <- 同一个对象已经耗尽了")
    print()

    print("  想反复遍历，就把『数据源』和『游标』分开：")

    class Countdown2:
        def __init__(self, n: int) -> None:
            self.n = n

        def __iter__(self):
            return Countdown(self.n)      # 每次都造一个新的迭代器

    d = Countdown2(3)
    print(f"     list(d)              -> {list(d)}")
    print(f"     list(d) 再来一次      -> {list(d)}     <- 这次有数据了")
    print()

    print("  反面教材：__iter__ 里写 return iter(self)")

    class BadIter:
        def __iter__(self):
            return iter(self)          # 会无限递归

    try:
        iter(BadIter())
    except RecursionError as exc:
        print(f"     iter(BadIter())      -> RecursionError: {exc}")


# ======================================================================
# 5.2 生成器函数
# ======================================================================
def demo_generator_basics() -> None:
    section("5.2 生成器函数：yield 是暂停点，不是 return")

    def gen():
        print("       [函数体开始执行]")
        yield 1
        print("       [从暂停处恢复]")
        yield 2
        print("       [再恢复]")
        return "我是返回值"          # 会变成 StopIteration 的 value

    print("  调用生成器函数，函数体一行都不会执行：")
    g = gen()
    print(f"     g = gen()            -> {g}")
    print("     （上面没有打印任何 [函数体...] 的日志）")
    print()

    print("  真正的执行发生在第一次 next()：")
    print(f"     next(g)              -> {next(g)}")
    print(f"     next(g)              -> {next(g)}")
    try:
        next(g)
    except StopIteration as exc:
        print(f"     next(g)              -> StopIteration(value={exc.value!r})")
    print()

    print("  生成器表达式是惰性的：")
    list_comp = [x * x for x in range(5)]
    gen_exp = (x * x for x in range(5))
    print(f"     [x*x for x in range(5)] -> {list_comp}")
    print(f"     (x*x for x in range(5)) -> {gen_exp}")
    print("     ^ 一个是列表，一个是生成器对象 —— 后者什么都还没算")
    print(f"     list(gen_exp)           -> {list(gen_exp)}   （现在才算）")
    print()

    print("  yield from：把子生成器接上来，并且会转发 send/throw/close：")

    def flat():
        yield from [1, 2, 3]
        yield from range(4, 6)

    print(f"     list(flat())         -> {list(flat())}")
    print()

    print("  send / throw / close（知道有这回事就行，asyncio 就是靠这套）：")

    def echo():
        received = None
        while True:
            received = yield received        # yield 表达式的值 = send 进来的值
            print(f"       [生成器收到 {received!r}]")

    e = echo()
    next(e)                      # 必须先预热，跑到第一个 yield
    print(f"     e.send('hello')      -> {e.send('hello')}")
    print(f"     e.send('world')      -> {e.send('world')}")
    e.close()
    print("     e.close()            -> 生成器在暂停处收到 GeneratorExit，正常收尾")
    print()

    print("  这条规矩必须记住：生成器里不能抛 StopIteration 当结束信号：")

    def bad():
        yield 1
        raise StopIteration("我想结束")      # 错！

    b = bad()
    next(b)
    try:
        next(b)
    except RuntimeError as exc:
        print(f"     RuntimeError: {exc}")
    print("     ^ PEP 479：StopIteration 从生成器里冒出来会被转成 RuntimeError，")
    print("       因为 for 会把它误认为『迭代正常结束』。要结束就用 return。")


# ======================================================================
# 5.3 为什么生成器只能遍历一次
# ======================================================================
def demo_single_use() -> None:
    section("5.3 为什么生成器只能遍历一次：迭代器是有状态的")

    print("  生成器对象内部保存着『我执行到哪儿了』：")
    g = (x for x in range(3))
    print(f"     g = (x for x in range(3))")
    print(f"     list(g)              -> {list(g)}")
    print(f"     list(g)              -> {list(g)}     <- 空了，但不报错！")
    print()
    print("  这是最坑的地方：**它不报错**。你看到空结果，然后开始怀疑数据源、")
    print("  怀疑过滤条件，就是不怀疑『生成器已经被用过了』。")
    print()

    print("  对比列表：它是『可迭代对象』，每次 iter() 都造新的迭代器")
    lst = [1, 2, 3]
    print(f"     list(lst)            -> {list(lst)}")
    print(f"     list(lst)            -> {list(lst)}     <- 反复可用")
    print()

    print("  但迭代器本身也只能用一次，哪怕它来自列表：")
    # 注意变量名别叫 it —— 本文件顶部 `import itertools as it`，
    # 局部名会把它遮住。这也是个真实存在的坑。
    one_shot = iter(lst)
    print(f"     one_shot = iter([1,2,3])")
    print(f"     list(one_shot)       -> {list(one_shot)}")
    print(f"     list(one_shot)       -> {list(one_shot)}     <- 同一个迭代器，也会空")
    print()

    print("  真实场景：一个函数把参数遍历了两遍")

    def bad_process(items):
        if not any(x > 10 for x in items):     # 第一遍：把生成器耗尽了
            return "没有大数"
        return f"大数个数 = {sum(1 for x in items)}"   # 第二遍：空的

    def good_process(items):
        items = list(items)                    # 物化一次，之后随便遍历
        if not any(x > 10 for x in items):
            return "没有大数"
        return f"大数个数 = {sum(1 for x in items)}"

    numbers = [1, 2, 30, 4]
    print(f"     传列表给 bad_process    -> {bad_process(numbers)}")
    print(f"     传生成器给 bad_process  -> {bad_process(x for x in numbers)}    <- 错！")
    print(f"     传生成器给 good_process -> {good_process(x for x in numbers)}")
    print()
    print("  itertools.tee 也能分流，但它靠缓存实现：落后越多占内存越多，")
    print("  除非两个消费者速度差不多，否则不如直接 list()。")


# ======================================================================
# 5.4 内存优势实测
# ======================================================================
def demo_memory() -> None:
    section("5.4 生成器的内存优势：实测 list vs generator")

    n = 200_000

    print("  先看 sys.getsizeof —— 注意它在生成器上会『骗你』：")
    print(f"     sys.getsizeof([x for x in range({n})])  -> "
          f"{sys.getsizeof([x for x in range(n)]):>10,} 字节")
    print(f"     sys.getsizeof((x for x in range({n})))  -> "
          f"{sys.getsizeof((x for x in range(n))):>10,} 字节")
    print("     ^ 生成器是个固定大小，跟它能产出多少项**无关** ——")
    print("       它量的是生成器对象自己，不包括将要产出的数据。")
    print()

    print("  正确量法：用 tracemalloc 看处理同样多数据时的**峰值内存**：")

    def peak_list(n: int) -> tuple[int, int]:
        tracemalloc.start()
        tracemalloc.reset_peak()
        data = [i for i in range(n)]          # 一次性全造出来
        total = 0
        for x in data:
            total += x
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak, total

    def peak_gen(n: int) -> tuple[int, int]:
        tracemalloc.start()
        tracemalloc.reset_peak()
        data = (i for i in range(n))          # 一边产一边消费
        total = 0
        for x in data:
            total += x
        _, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        return peak, total

    p_list, t1 = peak_list(n)
    p_gen, t2 = peak_gen(n)

    print(f"     列表版   峰值 {p_list:>12,} 字节   总和 {t1:,}")
    print(f"     生成器版 峰值 {p_gen:>12,} 字节   总和 {t2:,}")
    print(f"     结果一致：{t1 == t2}")
    print(f"     峰值相差约 {p_list / max(p_gen, 1):.0f} 倍")
    print()
    print("  记住这个复杂度，别背数字：")
    print("     列表的内存 = O(数据量)")
    print("     生成器的内存 = O(1)")
    print()

    print("  最典型的场景 —— 读大文件：")
    print("     坏：  lines = open('huge.log').readlines()   # 全进内存")
    print("     好：  with open('huge.log') as f:")
    print("               for line in f:                    # 一次一行")
    print("   文件对象本身就是最经典的迭代器：__iter__ 返回 self。")
    print()

    print("  代价也不是没有：生成器无法 len()、无法切片、无法回退，")
    print("  而且每次 next() 都有开销 —— 纯计算场景比列表推导慢 1.2~2 倍。")


# ======================================================================
# 5.5 itertools
# ======================================================================
def demo_itertools() -> None:
    section("5.5 itertools 精华")

    print("  -- 无限迭代器（必须配 islice 或 break）--")
    print(f"     islice(count(10, 2), 5)          -> {list(it.islice(it.count(10, 2), 5))}")
    print(f"     islice(cycle('ABC'), 7)          -> {list(it.islice(it.cycle('ABC'), 7))}")
    print(f"     repeat('x', 3)                   -> {list(it.repeat('x', 3))}")
    print()

    print("  -- 拼接与切片 --")
    print(f"     chain([1,2], 'ab', (3,))         -> {list(it.chain([1, 2], 'ab', (3,)))}")
    print(f"     chain.from_iterable([[1,2],[3]]) -> {list(it.chain.from_iterable([[1, 2], [3]]))}")
    print(f"     islice(range(100), 10, 20, 2)    -> {list(it.islice(range(100), 10, 20, 2))}")
    print("     注意 islice 只支持正索引，不支持负数，也不能 len()")
    print()

    print("  -- 组合数学三兄弟 --")
    print(f"     product('AB', [1, 2])            -> {list(it.product('AB', [1, 2]))}")
    print(f"     permutations('ABC', 2)           -> {list(it.permutations('ABC', 2))}")
    print(f"     combinations('ABC', 2)           -> {list(it.combinations('ABC', 2))}")
    print(f"     combinations_with_replacement('AB', 2) -> "
          f"{list(it.combinations_with_replacement('AB', 2))}")
    print("     ^ 排列认为 (A,B) 和 (B,A) 不同，组合认为是同一个。")
    print()

    print("  -- groupby：必须先排序，否则同一个 key 会被分成好几组 --")
    data = [("水果", "苹果"), ("蔬菜", "白菜"), ("水果", "香蕉"), ("蔬菜", "萝卜")]

    print("     不排序：")
    for key, group in it.groupby(data, key=lambda p: p[0]):
        print(f"       {key} -> {list(group)}")
    print("     排序后：")
    for key, group in it.groupby(sorted(data, key=lambda p: p[0]), key=lambda p: p[0]):
        print(f"       {key} -> {list(group)}")
    print()
    print("     groupby 只合并**相邻**的相同 key —— 它不会替你把整个序列看完，")
    print("     那样就不惰性了。所以标准写法永远是 sorted(...) + groupby。")
    print()

    print("     第二个坑：group 是共享的迭代器，推进到下一组它就失效了：")
    grouped_bad = {}
    for key, group in it.groupby(sorted(data, key=lambda p: p[0]), key=lambda p: p[0]):
        grouped_bad[key] = group                 # 错：存的是迭代器
    print(f"       （存迭代器）{ {k: list(v) for k, v in grouped_bad.items()} }")
    grouped_ok = {}
    for key, group in it.groupby(sorted(data, key=lambda p: p[0]), key=lambda p: p[0]):
        grouped_ok[key] = list(group)            # 对：立刻物化
    print(f"       （立刻物化）{grouped_ok}")
    print()

    print("  -- 累加与相邻 --")
    print(f"     accumulate([1,2,3,4])            -> {list(it.accumulate([1, 2, 3, 4]))}")
    print(f"     accumulate([1,2,3,4], max)       -> {list(it.accumulate([1, 2, 3, 4], max))}")
    print(f"     accumulate([1,2,3,4], initial=0) -> {list(it.accumulate([1, 2, 3, 4], initial=0))}")
    print(f"     pairwise([1,2,3,4])              -> {list(it.pairwise([1, 2, 3, 4]))}   （3.10+）")
    print(f"     batched(range(7), 3)             -> {list(it.batched(range(7), 3))}   （3.12+）")
    print()

    print("  -- tee：分流，但有缓存代价 --")
    a, b = it.tee(iter(range(5)), 2)
    print(f"     a, b = tee(iter(range(5)), 2)")
    print(f"     list(a)                          -> {list(a)}")
    print(f"     list(b)                          -> {list(b)}")
    print("     看起来像『复制了一份』，实际是共享底层迭代器 + 各自缓存：")
    print("     谁落后就得把数据留着，落后越多内存越大。")
    print()

    print("  -- 实战：全部串成一条惰性管道，中间没有任何列表 --")

    def fake_log():
        for i in range(30):
            level = "ERROR" if i % 7 == 0 else "INFO"
            yield f"2026-09-16 10:00:{i:02d} {level} 消息 {i}"

    errors = (line for line in fake_log() if " ERROR " in line)
    recent = it.islice(errors, 3)
    stamps = (line.split(" ", 1)[0] for line in recent)
    print(f"     最近 3 条 ERROR 的日期 -> {list(stamps)}")
    print("     整条链上一次只处理一行，数据量再大也不爆内存。")


# ======================================================================
# 5.6 上下文管理器：with 的展开
# ======================================================================
class DemoResource:
    """用类实现一个上下文管理器，把每个钩子都打印出来。"""

    def __init__(self, name: str, swallow: bool = False) -> None:
        self.name = name
        self.swallow = swallow

    def __enter__(self) -> str:
        print(f"       __enter__({self.name}) 被调用")
        return f"<{self.name} 的句柄>"      # 这个值绑给 as 后面的名字

    def __exit__(self, exc_type, exc, tb) -> bool:
        if exc_type is None:
            print(f"       __exit__(None, None, None) —— 正常结束")
        else:
            print(f"       __exit__ 收到异常 {exc_type.__name__}: {exc}")
        return self.swallow                # True = 吞掉异常


def demo_context_manager() -> None:
    section("5.6 上下文管理器：with 的展开与 __exit__ 吞异常")

    print("  with 的完整展开：")
    print("     mgr = EXPR")
    print("     VAR = mgr.__enter__()          <- as 绑的是 __enter__ 的返回值")
    print("     try:")
    print("         BODY")
    print("     except BaseException as exc:")
    print("         if not mgr.__exit__(type(exc), exc, exc.__traceback__):")
    print("             raise                  <- __exit__ 返回假值就继续往外抛")
    print("     else:")
    print("         mgr.__exit__(None, None, None)")
    print()

    print("  正常路径：")
    with DemoResource("A") as handle:
        print(f"       with 块内，handle = {handle}")
    print()

    print("  异常路径：__exit__ 返回 None（假值）-> 异常继续传播")
    try:
        with DemoResource("B"):
            raise ValueError("我出错了")
    except ValueError as exc:
        print(f"       外面接到了：{exc}")
    print()

    print("  异常路径：__exit__ 返回 True -> 异常被吞掉，外面毫无察觉")
    with DemoResource("C", swallow=True):
        raise ValueError("你抓不到我")
    print("       程序继续往下跑 —— 这就是『吞异常』")
    print("       除非你在写 suppress 那样的工具，否则不要这么干。")
    print()

    print("  不是所有 __enter__ 都返回 self。它想返回什么就返回什么：")

    class ReturnsNumber:
        def __enter__(self) -> int:
            return 42

        def __exit__(self, *exc_info) -> None:
            return None

    with ReturnsNumber() as value:
        print(f"       with ReturnsNumber() as value -> value = {value}  (type={type(value).__name__})")
    print("       这就是为什么 `with open(...) as f` 拿到的是文件对象：")
    print("       因为 file.__enter__ 返回 self。")

    print()
    print("  @contextmanager：用生成器写，短得多")
    print("     yield 之前   = __enter__")
    print("     yield 的值   = as 后面拿到的东西")
    print("     yield 之后   = __exit__")
    print()

    journal: list[str] = []

    @contextmanager
    def tracked(name: str):
        journal.append(f"进入 {name}")
        try:
            yield name.upper()
        finally:
            journal.append(f"离开 {name}")     # 必须放在 finally 里！

    with tracked("db") as upper:
        journal.append(f"使用 {upper}")
    print(f"     with tracked('db') as upper -> upper = {upper!r}")
    print(f"     journal = {journal}")
    print()

    print("  忘了 try/finally 会怎样 —— 用一个对比版本：")

    @contextmanager
    def fragile(name: str):
        journal2.append(f"进入 {name}")
        yield name
        journal2.append(f"离开 {name}")        # 没有 try/finally 包住

    journal2: list[str] = []
    try:
        with fragile("db"):
            raise RuntimeError("块内炸了")
    except RuntimeError:
        pass
    print(f"     journal2 = {journal2}")
    print("     ^ 『离开 db』没被记录 —— 异常让 yield 之后的代码直接跳过了。")
    print("       **@contextmanager 里的 yield 必须包在 try/finally 里。**")


# ======================================================================
# 5.7 contextlib 与实战用途
# ======================================================================
def demo_contextlib() -> None:
    section("5.7 contextlib 工具箱与上下文管理器的实际用途")

    from contextlib import ExitStack, closing, nullcontext

    print("  -- suppress：明确地忽略指定异常 --")
    with suppress(FileNotFoundError):
        os.remove("这个文件肯定不存在.txt")
    print("     with suppress(FileNotFoundError): os.remove(...)  -> 安静通过")
    print("     比 try/except/pass 短，而且『故意忽略』的意图一目了然。")
    print()

    print("  -- closing：给『有 close() 但没有 __enter__』的对象补一个 --")

    class Conn:
        def close(self):
            print("       Conn.close() 被调用")

    with closing(Conn()):
        print("       使用 Conn")
    print()

    print("  -- nullcontext：什么都不做，用来统一两个分支的写法 --")

    import tempfile

    def show(text: str, path: str | None = None) -> None:
        # path 给定时写文件，否则写标准输出。
        # 用 nullcontext 包一下，两个分支的 `with` 写法就完全一致了，
        # 不需要写 if/else 两套代码。
        ctx = open(path, "w", encoding="utf-8") if path else nullcontext(sys.stdout)
        with ctx as out:
            out.write(text + "\n")

    show("       写到标准输出")
    with tempfile.TemporaryDirectory() as tmp:
        target = os.path.join(tmp, "out.txt")
        show("写到文件", target)
        with open(target, encoding="utf-8") as handle:
            print(f"       文件内容 -> {handle.read().strip()!r}")
    print()

    print("  -- ExitStack：动态管理数量不确定的资源 --")
    events: list[str] = []

    @contextmanager
    def resource(name: str):
        events.append(f"打开 {name}")
        try:
            yield name
        finally:
            events.append(f"关闭 {name}")

    with ExitStack() as stack:
        handles = [stack.enter_context(resource(f"r{i}")) for i in range(3)]
        events.append(f"正在使用 {handles}")
    print(f"     {events}")
    print("     退出时按**相反顺序**全部关闭，中途出错也一样 ——")
    print("     这是『手动 try/finally 管 N 个资源』的唯一优雅解法。")
    print()

    print("  -- 实战 1：计时 --")

    @contextmanager
    def timed(label: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            print(f"       {label} 耗时 {time.perf_counter() - start:.4f}s")

    with timed("空转 10 万次"):
        sum(range(100_000))
    print()

    print("  -- 实战 2：临时改环境变量 --")

    @contextmanager
    def temp_env(**overrides):
        # 记住旧值；本来不存在的记成 None
        old = {k: os.environ.get(k) for k in overrides}
        os.environ.update(overrides)
        try:
            yield
        finally:
            for key, value in old.items():
                if value is None:
                    os.environ.pop(key, None)     # 本来没有 -> 删掉
                else:
                    os.environ[key] = value       # 本来有 -> 还原

    print(f"     进入前 API_URL in os.environ -> {'API_URL' in os.environ}")
    with temp_env(API_URL="https://test.example.com", DEBUG="1"):
        print(f"     块内 API_URL = {os.environ['API_URL']}")
        print(f"     块内 DEBUG   = {os.environ['DEBUG']}")
    print(f"     退出后 API_URL in os.environ -> {'API_URL' in os.environ}")
    print("     ^ 『本来不存在的键要删掉而不是设成空字符串』")
    print("       —— 这是这类工具最容易漏的细节。")
    print()

    print("  -- 实战 3：数据库事务（伪代码形状，值得背下来）--")
    print("     @contextmanager")
    print("     def transaction(conn):")
    print("         try:")
    print("             yield conn")
    print("         except Exception:")
    print("             conn.rollback()        # 出错回滚")
    print("             raise                  # 但异常要继续往上抛")
    print("         else:")
    print("             conn.commit()          # 只有正常走完才提交")
    print()
    print("     注意 except 里必须 raise。忘了它，事务失败了程序却以为成功了。")


# ======================================================================
# 5.8 其他 Pythonic 惯用法
# ======================================================================
def demo_pythonic_idioms() -> None:
    section("5.8 其他 Pythonic 惯用法")

    print("  -- enumerate 带起始值 --")
    names = ["张三", "李四", "王五"]
    print(f"     enumerate(names)          -> {list(enumerate(names))}")
    print(f"     enumerate(names, start=1) -> {list(enumerate(names, start=1))}")
    print()

    print("  -- zip 与 strict=True（3.10+）--")
    names2 = ["张三", "李四", "王五"]
    scores = [90, 85]
    print(f"     zip(names, scores)                -> {list(zip(names2, scores))}")
    print("     ^ 静默截断！少了一行，而且不报错")
    try:
        list(zip(names2, scores, strict=True))
    except ValueError as exc:
        print(f"     zip(..., strict=True)             -> ValueError: {exc}")
    print("     『两个列表应该一样长』是绝大多数场景的隐含假设，")
    print("     一旦不成立，你要的是一个错误，不是一个少了一行的结果。")
    print()

    print("  -- 解包 --")
    a, b = 1, 2
    a, b = b, a
    print(f"     交换 a, b = b, a          -> a={a}, b={b}")
    first, *rest = [1, 2, 3, 4]
    print(f"     first, *rest = [1,2,3,4]  -> first={first}, rest={rest}")
    head, *mid, tail = [1, 2, 3, 4, 5]
    print(f"     head, *mid, tail          -> head={head}, mid={mid}, tail={tail}")
    unpacked = {**{"x": 1, "y": 2}, "z": 3}
    print(f"     {{**{{'x': 1, 'y': 2}}, 'z': 3}} -> {unpacked}")
    print("     ^ 注意 f-string 里想写字面量花括号要写两遍，否则会被当成格式说明符")
    print()

    print("  -- any / all 是短路的 --")
    print(f"     any([False, True, ...])   -> 遇到第一个真值就停")
    print(f"     all([])                   -> {all([])}      <- 空真，容易记错")
    print(f"     any([])                   -> {any([])}")
    print()

    calls: list[int] = []

    def check(n: int) -> bool:
        calls.append(n)
        return n > 2

    result = any(check(n) for n in [1, 2, 3, 4, 5])
    print(f"     any(check(n) for n in 1..5) -> {result}，check 实际被调用了 {len(calls)} 次")
    print(f"     （传生成器才有短路效果；写成 any([...]) 会先把所有元素算完）")
    print()

    print("  -- dict.__missing__：给缺失的键一个默认值 --")

    class CountDict(dict):
        def __missing__(self, key):
            # 只在 d[key] 找不到时调用，不影响 get() / in
            self[key] = 0            # 顺手写回去，下次就是真命中
            return 0

    counter = CountDict()
    for word in "apple apple banana".split():
        counter[word] += 1
    print(f"     counter = {counter}")

    from collections import defaultdict
    dd = defaultdict(list)
    dd["水果"].append("苹果")
    print(f"     defaultdict(list) 读不存在的键也会建条目：dd['蔬菜'] -> {dd['蔬菜']}")
    print(f"     ^ 之后 '蔬菜' 就真的在 dd 里了：{'蔬菜' in dd}")
    print("     defaultdict 的工厂函数拿不到 key；__missing__ 能拿到，")
    print("     所以『默认值需要按 key 算』的场景要用 __missing__。")
    print()

    print("  -- 字典合并 |（3.9+）--")
    x = {"a": 1, "b": 2}
    y = {"b": 99, "c": 3}
    print(f"     x | y     -> {x | y}     <- 右边优先，返回新字典")
    z = dict(x)
    z |= y
    print(f"     z = dict(x); z |= y -> {z}")
    print(f"     x 没被改动 -> {x}")
    print("     `|` 新建，`|=` 就地改 —— 和模块 01 的 `+` / `+=` 是同一回事。")
    print()

    print("  -- match 语句（3.10+）：结构模式匹配，不是 C 的 switch --")

    def handle(command: str) -> str:
        match command.split():
            case ["go", direction]:
                return f"往 {direction} 走"
            case ["look"]:
                return "环顾四周"
            case ["take", item, *rest]:
                return f"拿起 {item}，剩下的 {rest} 先不管"
            case _:
                return "不懂这个命令"

    for cmd in ("go north", "look", "take sword shield", "dance"):
        print(f"     {cmd!r:<22} -> {handle(cmd)}")
    print()

    print("  类模式对 dataclass 特别好用：")

    from dataclasses import dataclass

    @dataclass
    class Point:
        x: int
        y: int

    def locate(p: Point) -> str:
        match p:
            case Point(x=0, y=0):
                return "原点"
            case Point(x=0, y=y):
                return f"在 y 轴上，y={y}"
            case Point(x=x, y=y) if x == y:
                return "在对角线上"
            case Point():
                return "普通点"

    for point in (Point(0, 0), Point(0, 5), Point(3, 3), Point(1, 7)):
        print(f"     {point!r:<18} -> {locate(point)}")
    print()
    print("  两个容易踩的点：")
    print("     case 1    会匹配 1、1.0、True（因为 1 == 1.0 == True）")
    print("     case NAME 里的 NAME 是**捕获变量**，永远匹配成功；")
    print("               想匹配常量必须写成带点的 case Color.RED")


# ======================================================================
def main() -> None:
    demo_iter_protocol()
    demo_generator_basics()
    demo_single_use()
    demo_memory()
    demo_itertools()
    demo_context_manager()
    demo_contextlib()
    demo_pythonic_idioms()
    print()
    print("=" * 74)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 74)


if __name__ == "__main__":
    main()
