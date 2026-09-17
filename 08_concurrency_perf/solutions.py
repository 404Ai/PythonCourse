"""
模块 08 · 并发与性能 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**
"""

from __future__ import annotations

import asyncio
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 线程池并行映射
# ======================================================================
def q1_parallel_map(fn, items: list, max_workers: int = 4) -> list:
    """ThreadPoolExecutor.map 就是保序的，一行搞定。"""
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(fn, items))


# 为什么用 `with`：
#   ThreadPoolExecutor 的 __exit__ 会调用 shutdown(wait=True)，
#   等所有任务跑完并回收线程。不写 with 的话，程序退出时可能卡住，
#   或者任务还没跑完解释器就开始拆环境了。
#
# 为什么 map 保序：
#   pool.map 返回的迭代器内部按提交顺序持有 Future，
#   取值时逐个 .result() 阻塞等待，所以先提交的一定排在前面，
#   哪怕它最后才算完。这正是 t_q1 里 sleepy 那个测试验证的行为。
#
# 为什么不用 submit + as_completed：
#   as_completed 是「谁先完成先给你谁」，顺序不确定。
#   要保序又想要灵活控制（比如单独处理异常）就得自己收集 Future 再按序取。
#
# 错误写法：
#   `for x in items: pool.submit(fn, x)` 然后不用 with ——
#   任务提交了但没人等，主线程可能先退出。


# ======================================================================
# q2 —— 进程池
# ======================================================================
def q2_process_squares(nums: list[int], max_workers: int = 2) -> list[int]:
    """把 ThreadPoolExecutor 换成 ProcessPoolExecutor，就这一处区别。"""
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        return list(pool.map(_square, nums))


def _square(n: int) -> int:
    """进程池的工作函数（必须放在模块顶层才能被 pickle）。"""
    return n * n


# Windows 上的三个坑，一个都不能踩：
#
# 1. 工作函数必须是模块顶层定义的可 pickle 对象。
#    写成函数内部的闭包或 lambda 会抛：
#        AttributeError: Can't pickle local object 'q2.<locals>.<lambda>'
#    因为子进程是全新的解释器，函数得序列化过去重建。
#    这也意味着工作函数的参数和返回值都必须是可 pickle 的。
#
# 2. 主模块必须有 `if __name__ == "__main__":` 保护。
#    Windows 没有 fork，只能用 spawn：新进程会重新 import 主模块。
#    没有保护的话，import 时又执行一遍创建进程池的代码 -> 无限递归。
#
# 3. 进程间不共享内存。每次 map 的输入输出都要序列化传输。
#    传一个 100MB 的 DataFrame 进去，光序列化就能比计算还慢。
#    数据大就用 multiprocessing.shared_memory 或者干脆别用多进程。
#
# 进程池的启动成本：Windows 上 spawn 一个进程大约 0.1~0.5 秒，
# 所以「每个任务 1 毫秒」的场景用进程池是纯亏。


# ======================================================================
# q3 —— asyncio 并发
# ======================================================================
def q3_async_gather(delays: list[float]) -> list[int]:
    """gather 并发跑，结果保序。"""

    async def worker(index: int, delay: float) -> int:
        # 必须是 await asyncio.sleep，不能用 time.sleep：
        # time.sleep 会阻塞整个事件循环，所有协程一起卡住，退化成串行。
        await asyncio.sleep(delay)
        return index

    async def run() -> list[int]:
        return list(await asyncio.gather(*(worker(i, d) for i, d in enumerate(delays))))

    return asyncio.run(run())


# 关键点拆解：
#
# 1. `asyncio.run(coro)` 是同步世界进入异步世界的入口。
#    它会新建一个事件循环、跑完这个协程、关掉循环。
#    一个线程里只能有一个正在运行的事件循环，所以在协程内部
#    不能再调 asyncio.run（会抛 RuntimeError）。
#
# 2. `await coro` 和 `gather(coro1, coro2)` 的区别是本题的核心：
#        await a; await b        -> 串行，总耗时 = a + b
#        await gather(a, b)      -> 并发，总耗时 ≈ max(a, b)
#    很多人第一次写异步代码，满屏 await 却一个都没并发起来，
#    就是因为每处都是顺序 await。
#
# 3. gather 保序：返回的列表顺序 == 传入协程的顺序，
#    和完成先后无关。想要「谁先完成先处理」用 asyncio.as_completed。
#
# 4. 3.11+ 推荐用 TaskGroup 替代 gather：
#        async with asyncio.TaskGroup() as tg:
#            tg.create_task(a())
#            tg.create_task(b())
#    gather 的缺陷是：其中一个任务抛异常时，其余任务不会被取消，
#    会出现 "Task exception was never retrieved" 的告警和资源泄漏。


# ======================================================================
# q4 —— Semaphore 限制并发度
# ======================================================================
def q4_limited_concurrency(n_tasks: int, limit: int) -> int:
    """Semaphore 当闸门，计数器观测峰值。"""
    sem = asyncio.Semaphore(limit)
    current = 0
    max_seen = 0

    async def worker() -> None:
        nonlocal current, max_seen
        async with sem:                 # 拿不到就在这排队
            current += 1
            max_seen = max(max_seen, current)
            await asyncio.sleep(0.01)   # 模拟一次网络请求
            current -= 1

    async def run() -> None:
        await asyncio.gather(*(worker() for _ in range(n_tasks)))

    asyncio.run(run())
    return max_seen


# 为什么这里不用加锁？
#   因为整个事件循环跑在**一个线程**里，`current += 1` 到 `await` 之间
#   不会有别的协程插进来。协程是协作式调度，只在你写 await 的地方让出。
#   这就是 asyncio 相比 threading 最大的好处：**并发推理难度低得多**。
#
#   但要注意：这意味着**任何一处 await 都可能被插入别的任务**。
#   如果你在 `current += 1` 和 `await ...` 之间读了一个共享状态、
#   又指望它在 await 之后没变，那就错了。这是 asyncio 里唯一的竞态来源。
#
# Semaphore 的典型用途：
#   - 爬虫限流（每个域名最多 10 个并发，别把人家服务器打挂）
#   - 数据库连接池上限
#   - 本地文件描述符数量限制
#
# 相比 ThreadPoolExecutor(max_workers=N)：
#   线程池是「硬上限」——最多 N 个线程；协程 + Semaphore 可以在
#   上万个协程里只放 10 个真正在跑，内存占用小得多。


# ======================================================================
# q5 —— 用锁保护共享状态
# ======================================================================
def q5_locked_counter(n_threads: int, per_thread: int) -> int:
    """with lock: 包住整个「读-改-写」。"""
    lock = threading.Lock()
    counter = 0

    def worker() -> None:
        nonlocal counter
        for _ in range(per_thread):
            with lock:
                counter += 1

    threads = [threading.Thread(target=worker) for _ in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()                        # 必须 join，否则主线程不等就返回了

    return counter


# 为什么必须加锁：
#   `counter += 1` 会被编译成 4 条字节码：
#       LOAD_FAST counter / LOAD_CONST 1 / BINARY_OP += / STORE_FAST counter
#   两个线程可能都执行到 LOAD_FAST 拿到 5，各自加一，都写回 6，
#   实际加了 2 次却只涨了 1。这就是「丢失更新」。
#
#   注意 GIL **不能**防止这件事：GIL 只保证单条字节码是原子的，
#   而 += 是 4 条字节码，中间随时可能被切走。
#   网上「Python 有 GIL 所以不用加锁」的说法是**错的**，
#   它只在「操作本身就是单条字节码」时成立（比如 list.append）。
#
# 锁的粒度：这里把整个循环体都锁住了，实际上每次迭代都要抢一次锁，
#   开销不小（几百万次迭代会明显变慢）。
#   优化办法是「攒够一批再提交」：
#       local = 0
#       for _ in range(per_thread):
#           local += 1
#       with lock:
#           counter += local
#   这样每个线程只抢一次锁。批量提交是并发编程的通用优化思路。
#
# 更现代的替代：threading.Lock 换成 queue.Queue。
#   让每个线程把结果放进队列，主线程统一汇总，
#   完全不需要共享可变状态，也就不需要锁。
#   **「不要共享，要传递」是并发编程的第一原则。**


# ======================================================================
# q6 —— lru_cache 记忆化
# ======================================================================
def q6_fib(n: int) -> int:
    """@lru_cache 把 O(2^n) 变成 O(n)。"""
    import functools

    @functools.lru_cache(maxsize=None)
    def _fib(k: int) -> int:
        if k < 2:
            return k
        return _fib(k - 1) + _fib(k - 2)

    return _fib(n)


# 上面把缓存函数套在里面是为了让它「自包含」（每次调用 q6_fib 都是新缓存）。
# 生产代码通常直接写成模块级：
#
#     @functools.lru_cache(maxsize=None)
#     def fib(n):
#         return n if n < 2 else fib(n - 1) + fib(n - 2)
#
# maxsize=None 和 maxsize=None 的区别：
#   functools.cache 就是 lru_cache(maxsize=None) 的简写，3.9+ 可用。
#   maxsize=None 表示「不淘汰，无限增长」——
#   对本题这种参数范围有限的函数没问题，
#   但如果参数是任意字符串，缓存会无限膨胀，必须给个上限（比如 maxsize=128）。
#
# **lru_cache 只能用在纯函数上**：
#   同样的输入必须永远返回同样的输出，且不能有副作用。
#   缓存一个「读文件」或「发请求」的函数会返回过期数据。
#   缓存一个「依赖当前时间」的函数会返回错误结果。
#
# 另外：参数必须可哈希（要做 dict 的 key）。传 list 会直接报 TypeError。
#
# 想看缓存效果，用 fib.cache_info()：
#     CacheInfo(hits=..., misses=..., maxsize=None, currsize=...)


# ======================================================================
# q7 —— 选型判断
# ======================================================================
_RECOMMEND_TABLE = {
    "cpu_heavy": "multiprocessing",
    "io_sync_lib": "threading",
    "io_async_lib": "asyncio",
    "io_disk": "threading",
    "tiny_task": "serial",
    "unknown": "serial",
}


def q7_recommend(scenario: str) -> str:
    """查表，默认值是 "serial"。"""
    return _RECOMMEND_TABLE.get(scenario, "serial")


# 背后的判断逻辑（这才是要记住的东西）：
#
#   CPU 密集  -> 只能多进程。多线程抢 GIL，等于白干。
#                更好的选择：用 NumPy / C 扩展，让计算发生在 GIL 之外。
#
#   IO 密集   -> 多线程或协程都行，看用的是哪个库。
#                同步库（requests/pymysql/open）只能用线程池；
#                有异步库（aiohttp/asyncpg）且并发量大就上 asyncio。
#
#   任务太小  -> 串行。线程切换、序列化、任务调度的开销比任务本身还大。
#                经验法则：单个任务耗时 < 1ms 就别并发了。
#
# 用查表而不是 if/elif 链：以后加场景只改数据不改代码，
# 而且表本身一眼就能看完，比读 20 行 if 快得多。


# ======================================================================
# q8 —— 用 cProfile 找热点
# ======================================================================
def q8_hotspot(func) -> str:
    """按 tottime 取最大值。"""
    import cProfile
    import pstats

    pr = cProfile.Profile()
    pr.enable()
    func()
    pr.disable()

    stats = pstats.Stats(pr)
    # stats.stats 的每一项是：
    #   (文件名, 行号, 函数名) -> (cc, nc, tt, ct, callers)
    #   cc = 调用次数（不含递归），nc = 总调用次数，
    #   tt = tottime（自身耗时），ct = cumtime（含子调用）
    # max 的 key 返回 (tt, 函数名)，第二项是为了在耗时相同时有确定的结果
    key, _ = max(stats.stats.items(), key=lambda kv: (kv[1][2], kv[0][2]))
    return key[2]


def _slow_helper() -> int:
    total = 0
    for i in range(30_000):
        total += i
    return total


def _the_workload() -> int:
    return _slow_helper() + _slow_helper()


# 为什么用 tottime 而不是 cumtime：
#   cumtime 是「含所有子调用」的耗时，那么最外层的包装函数永远是第一名
#   （因为所有时间都算在它头上）。按 cumtime 排序只能看出「谁调用了慢东西」，
#   找不出「慢在哪一行」。
#   tottime 剔除子调用，剩下的就是函数自己烧掉的时间 —— 这才是真正的热点。
#
# 实战里两个都要看：
#   1. 先按 tottime 排序 -> 找到最烧时间的那个函数
#   2. 再按 cumtime 排序 -> 看它是被谁调用的（调用链）
#
# cProfile 本身有开销（通常让程序慢 2~3 倍），而且会干扰多线程的时间统计。
# 它给的是**相对**的热点排序，不是精确耗时。
# 生产环境排查用 py-spy（采样式，开销极低，可以挂在运行中的进程上）：
#     py-spy top --pid 12345
#     py-spy record -o profile.svg -- python app.py


# ======================================================================
# q9 —— timeit 微基准
# ======================================================================
def q9_timeit_faster(fn_a, fn_b, number: int = 200) -> str:
    """各跑 number 次，谁快返回谁。"""
    import timeit

    t_a = timeit.timeit(fn_a, number=number)
    t_b = timeit.timeit(fn_b, number=number)
    return "a" if t_a <= t_b else "b"


# timeit 相比手写 time.perf_counter 的好处：
#   1. 自动重复多次（number 参数），抹平单次抖动
#   2. 测量期间临时关闭垃圾回收（gc.disable），避免 GC 暂停污染结果
#   3. 用最精确的计时器（Windows 上是 QueryPerformanceCounter）
#
# 注意 timeit 在 Windows 上的计时器精度：默认是 perf_counter，
# 分辨率大约 100 纳秒级别。测微秒级的操作时，务必要把 number 调大
# （比如 number=100000），否则测出来的主要是噪声。
#
# 什么时候不该用 timeit：
#   它只适合测「微秒到毫秒级」的代码片段。
#   要测整个程序的性能瓶颈，用 cProfile；
#   要测一个函数在不同数据规模下的表现，自己写 time.perf_counter 更灵活。
#
# 最重要的一条：**微基准的结果经常不能直接外推到真实程序**。
#   比如 timeit 测出推导式比 for 循环快 30%，但如果这 30% 的代码
#   只占程序总耗时的 1%，那优化它等于没优化。
#   先 profile 找到瓶颈，再微基准优化瓶颈。


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def t_q1() -> None:
    assert q1_parallel_map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6]
    assert q1_parallel_map(lambda x: x * 2, []) == []
    assert q1_parallel_map(str, [1, 2, 3, 4]) == ["1", "2", "3", "4"]

    def sleepy(x):
        time.sleep(0.05 if x == 0 else 0.01)
        return x

    assert q1_parallel_map(sleepy, [0, 1, 2, 3], max_workers=4) == [0, 1, 2, 3]

    t0 = time.perf_counter()
    q1_parallel_map(lambda _: time.sleep(0.05), list(range(8)), max_workers=4)
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.28, f"没跑起来并发？8 个 0.05s 的任务花了 {elapsed:.2f}s"


def t_q2() -> None:
    assert q2_process_squares([1, 2, 3, 4]) == [1, 4, 9, 16]
    assert q2_process_squares([]) == []
    assert q2_process_squares([10]) == [100]


def t_q3() -> None:
    assert q3_async_gather([0.05, 0.05, 0.05]) == [0, 1, 2]
    assert q3_async_gather([]) == []

    t0 = time.perf_counter()
    assert q3_async_gather([0.05] * 4) == [0, 1, 2, 3]
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.15, f"没有并发？4 个 0.05s 的协程花了 {elapsed:.2f}s"


def t_q4() -> None:
    assert q4_limited_concurrency(10, 3) == 3
    assert q4_limited_concurrency(2, 5) == 2
    assert q4_limited_concurrency(1, 1) == 1
    assert q4_limited_concurrency(20, 4) == 4


def t_q5() -> None:
    assert q5_locked_counter(4, 1000) == 4000
    assert q5_locked_counter(1, 100) == 100
    assert q5_locked_counter(8, 500) == 4000


def t_q6() -> None:
    assert q6_fib(0) == 0
    assert q6_fib(1) == 1
    assert q6_fib(10) == 55
    assert q6_fib(30) == 832040

    def fib_iter(n):
        a, b = 0, 1
        for _ in range(n):
            a, b = b, a + b
        return a

    t0 = time.perf_counter()
    got = q6_fib(400)
    elapsed = time.perf_counter() - t0
    assert got == fib_iter(400), "大数结果不对"
    assert elapsed < 0.5, f"q6_fib(400) 花了 {elapsed:.2f}s —— 是不是忘了 @lru_cache？"

    t0 = time.perf_counter()
    q6_fib(400)
    assert time.perf_counter() - t0 < 0.01, "缓存没生效"


def t_q7() -> None:
    assert q7_recommend("cpu_heavy") == "multiprocessing"
    assert q7_recommend("io_sync_lib") == "threading"
    assert q7_recommend("io_async_lib") == "asyncio"
    assert q7_recommend("io_disk") == "threading"
    assert q7_recommend("tiny_task") == "serial"
    assert q7_recommend("unknown") == "serial"
    assert q7_recommend("乱写的") == "serial"


def t_q8() -> None:
    assert q8_hotspot(_the_workload) == "_slow_helper", q8_hotspot(_the_workload)
    assert q8_hotspot(_slow_helper) == "_slow_helper"


def t_q9() -> None:
    def loop_sum():
        total = 0
        for i in range(2000):
            total += i
        return total

    assert q9_timeit_faster(lambda: sum(range(2000)), loop_sum) == "a"
    assert q9_timeit_faster(loop_sum, lambda: sum(range(2000))) == "b"


def main() -> None:
    c = Checker("模块 08 · 并发与性能 参考答案")
    c.add("q1  ThreadPoolExecutor 并行映射", t_q1)
    c.add("q2  ProcessPoolExecutor 进程池", t_q2)
    c.add("q3  asyncio.gather 并发", t_q3)
    c.add("q4  Semaphore 限制并发度", t_q4)
    c.add("q5  Lock 保护共享计数器", t_q5)
    c.add("q6  lru_cache 记忆化", t_q6)
    c.add("q7  并发方案选型", t_q7)
    c.add("q8  cProfile 找热点", t_q8)
    c.add("q9  timeit 微基准", t_q9)
    c.run()


if __name__ == "__main__":          # Windows + 进程池的硬性要求
    main()
