"""
模块 08 · 并发与性能 —— 练习

这一模块的练习涉及真实的多线程/多进程/协程，所以测试会跑几秒钟，这是正常的。

注意：Windows 上 ProcessPoolExecutor 用 spawn 启动子进程，会重新导入本模块。
因此本文件末尾有 `if __name__ == "__main__":` 保护 —— 这不是风格问题，
少了他 q2 会无限递归创建进程，直接把机器拖死。
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 线程池并行映射
# ======================================================================
def q1_parallel_map(fn, items: list, max_workers: int = 4) -> list:
    """用 ThreadPoolExecutor 并行地对 items 的每一项调用 fn。

    返回结果列表，**顺序必须和 items 一致**。

    >>> q1_parallel_map(lambda x: x * 2, [1, 2, 3])
    [2, 4, 6]

    提示：queue 的 map 方法返回的就是保序的迭代器，
         转成 list 返回即可。别忘了用 `with` 语句管理线程池。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— 进程池
# ======================================================================
def q2_process_squares(nums: list[int], max_workers: int = 2) -> list[int]:
    """用 ProcessPoolExecutor 并行计算每个数的平方。

    >>> q2_process_squares([1, 2, 3, 4])
    [1, 4, 9, 16]

    注意：
        1. 传给进程池的函数（本文件里的 _square）必须是**模块顶层**定义的，
           不能是闭包或 lambda —— 它要被 pickle 序列化后送进子进程。
        2. 本文件末尾的 `if __name__ == "__main__":` 保护不能删。

    提示：和 q1 几乎一模一样，把 ThreadPoolExecutor 换成 ProcessPoolExecutor 就行。
         这正是 concurrent.futures 的设计目的。
    """
    raise NotImplementedError


def _square(n: int) -> int:
    """进程池的工作函数（必须放在模块顶层才能被 pickle）。"""
    return n * n


# ======================================================================
# q3 —— asyncio 并发
# ======================================================================
def q3_async_gather(delays: list[float]) -> list[int]:
    """并发等待一系列延时，返回每个任务的编号 [0, 1, 2, ...]。

    第 i 个任务等待 delays[i] 秒，然后返回 i。

    >>> q3_async_gather([0.05, 0.05, 0.05])
    [0, 1, 2]

    要求：总耗时应接近 max(delays)，而不是 sum(delays)。
         也就是说必须**并发**，不能写成循环里逐个 await。

    提示：
        - 用 asyncio.gather 并发跑
        - 用 asyncio.run 作为同步入口
        - sleep 必须是 `await asyncio.sleep(...)`，用 time.sleep 会阻塞整个事件循环
    """
    raise NotImplementedError


# ======================================================================
# q4 —— 用 Semaphore 限制并发度
# ======================================================================
def q4_limited_concurrency(n_tasks: int, limit: int) -> int:
    """启动 n_tasks 个协程，用 Semaphore 把并发度限制在 limit 以内。

    返回**实际观测到的最大并发数**（同时处于「进行中」状态的任务数的峰值）。

    并发数达到 limit 之后，剩下的任务应该排队等待。

    >>> q4_limited_concurrency(10, 3)
    3
    >>> q4_limited_concurrency(2, 5)
    2

    提示：用一个计数变量记录「当前有几个任务在跑」，
         进入临界区 +1 并更新最大值，退出前 -1。
         每个任务在临界区里 `await asyncio.sleep(0.01)`。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 用锁保护共享状态
# ======================================================================
def q5_locked_counter(n_threads: int, per_thread: int) -> int:
    """启动 n_threads 个线程，每个线程把同一个共享计数器加 per_thread 次。

    必须用 threading.Lock 保护，返回值必须**精确等于** n_threads * per_thread。

    >>> q5_locked_counter(4, 1000)
    4000

    说明：如果去掉锁，这个值通常会小于 4000（`x += 1` 不是原子操作）。
         但「通常」意味着偶尔也会刚好等于 —— 这种偶发性正是竞态条件最难查的地方。
    返回精确值，说明你的加锁是对的。
    """
    raise NotImplementedError


# ======================================================================
# q6 —— lru_cache 记忆化
# ======================================================================
def q6_fib(n: int) -> int:
    """用递归 + functools.lru_cache 计算第 n 个斐波那契数。

    定义：fib(0) = 0, fib(1) = 1, fib(n) = fib(n-1) + fib(n-2)

    >>> q6_fib(10)
    55
    >>> q6_fib(0)
    0

    !! 警告 !!  必须加 @functools.lru_cache 装饰器。
    朴素的递归版本是 O(2^n)，算 q6_fib(100) 需要几百年。
    加了缓存之后是 O(n)，瞬间返回。

    提示：装饰器写在函数定义上面：
        @functools.lru_cache(maxsize=None)
        def q6_fib(n): ...
    """
    raise NotImplementedError


# ======================================================================
# q7 —— 选型判断
# ======================================================================
def q7_recommend(scenario: str) -> str:
    """根据场景返回推荐的并发方案，取值只有四种：

        "serial"          不需要并发，串行就行
        "threading"       线程池
        "multiprocessing" 进程池
        "asyncio"         协程

    场景对照表（输入 -> 输出）：
        "cpu_heavy"     CPU 密集型计算（图像处理、加解密、纯 Python 循环）
                        -> "multiprocessing"
        "io_sync_lib"   几十个网络请求，只能用同步库（requests）
                        -> "threading"
        "io_async_lib"  上万个网络请求，有异步库（aiohttp / httpx）
                        -> "asyncio"
        "io_disk"       本地文件读写，量不大
                        -> "threading"
        "tiny_task"     任务本身只要几微秒，有十万个
                        -> "serial"
        "unknown"       看不懂的场景
                        -> "serial"

    其他任何输入都返回 "serial"。

    提示：用一个 dict 做映射，最后用 .get(scenario, "serial")。
         这类「查表」逻辑不要写成一长串 if/elif。
    """
    raise NotImplementedError


# ======================================================================
# q8 —— 用 cProfile 找热点
# ======================================================================
def q8_hotspot(func) -> str:
    """用 cProfile 分析 func() 的执行，返回**自身耗时（tottime）最长**的函数名。

    只返回函数名（如 "parse"），不带模块名和文件名。

    提示：
        import cProfile, pstats
        pr = cProfile.Profile()
        pr.enable(); func(); pr.disable()
        stats = pstats.Stats(pr)
        # stats.stats 的结构是：
        #   {(文件名, 行号, 函数名): (调用次数, 递归调用次数, tottime, cumtime, ...)}
        # 取 tottime（下标 2）最大的那个，返回函数名（下标的 2 号元素）
        #   即 (文件名, 行号, 函数名) 这个元组的 [2]

    注意：要按 tottime 排序，不是 cumtime。
         按 cumtime 排的话排第一的永远是最外层的包装函数。
    """
    raise NotImplementedError


def _slow_helper() -> int:
    total = 0
    for i in range(30_000):
        total += i
    return total


def _the_workload() -> int:
    return _slow_helper() + _slow_helper()


# ======================================================================
# q9 —— timeit 微基准
# ======================================================================
def q9_timeit_faster(fn_a, fn_b, number: int = 200) -> str:
    """用 timeit 分别测 fn_a 和 fn_b 各跑 number 次的总耗时，
    返回更快的那个的标识："a" 或 "b"。

    >>> def loop_sum():
    ...     total = 0
    ...     for i in range(1000):
    ...         total += i
    ...     return total
    >>> q9_timeit_faster(lambda: sum(range(1000)), loop_sum)
    'a'

    提示：timeit.timeit(stmt, number=...) 的 stmt 可以直接传可调用对象。
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    assert q1_parallel_map(lambda x: x * 2, [1, 2, 3]) == [2, 4, 6]
    assert q1_parallel_map(lambda x: x * 2, []) == []
    assert q1_parallel_map(str, [1, 2, 3, 4]) == ["1", "2", "3", "4"]

    # 顺序必须和输入一致，即使后面的任务先算完
    def sleepy(x):
        time.sleep(0.05 if x == 0 else 0.01)
        return x

    assert q1_parallel_map(sleepy, [0, 1, 2, 3], max_workers=4) == [0, 1, 2, 3]

    # 8 个 0.05s 的任务，4 个线程：串行要 0.4s，并发约 0.1s
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

    # 4 个 0.05s：串行要 0.2s，并发约 0.05s
    t0 = time.perf_counter()
    assert q3_async_gather([0.05] * 4) == [0, 1, 2, 3]
    elapsed = time.perf_counter() - t0
    assert elapsed < 0.15, f"没有并发？4 个 0.05s 的协程花了 {elapsed:.2f}s"


def t_q4() -> None:
    assert q4_limited_concurrency(10, 3) == 3
    assert q4_limited_concurrency(2, 5) == 2
    assert q4_limited_concurrency(1, 1) == 1
    # 20 个任务限流 4，峰值应该正好是 4
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

    # 迭代版本作为参照，验证大数也对
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

    # 缓存真的生效了：第二次调用应该几乎不花时间
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
    c = Checker("模块 08 · 并发与性能 练习")
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
