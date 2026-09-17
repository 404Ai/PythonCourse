"""
模块 08 · 并发与性能 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

**这个文件里的数字全部是你机器上现场测出来的。**
不要相信任何文章里写的「多线程能加速 4 倍」，
自己跑一遍就知道在 CPU 密集场景下它连 1 倍都没有。

注意：Windows 上 multiprocessing 用 spawn 启动子进程，
会重新导入本模块，所以 `if __name__ == "__main__"` 保护是**必须的**。
"""

from __future__ import annotations

import asyncio
import cProfile
import pstats
import sys
import threading
import time
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed

# 演示竞态条件用的全局计数器（会在 demo_threading_lock 里被并发修改）
_unsafe_counter = 0

# ======================================================================
# 工作函数必须定义在模块顶层 —— 进程池要 pickle 它们，
# 定义在函数内部的闭包是 pickle 不了的。
# ======================================================================


def cpu_burn(n: int) -> int:
    """纯 Python 计算，典型的 CPU 密集任务。"""
    total = 0
    for i in range(n):
        total += i * i
    return total


def io_task(delay: float) -> float:
    """模拟一次网络请求：大部分时间在等。"""
    time.sleep(delay)
    return delay


def _identity(x):
    """只用来在「读」和「写」之间制造一个函数调用点。"""
    return x


def report(label: str, elapsed: float, baseline: float) -> None:
    speedup = baseline / elapsed
    print(f"  {label:<28} {elapsed:>7.3f} s   加速比 {speedup:>5.2f}x")


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# 8.1 + 8.2  CPU 密集：多线程毫无帮助
# ======================================================================
def demo_cpu_bound() -> None:
    section("8.1/8.2 CPU 密集：多线程为什么没用")

    n = 3_000_000
    print(f"  任务：cpu_burn({n:,}) 跑 2 次（纯 Python 计算）")
    print()

    t0 = time.perf_counter()
    cpu_burn(n)
    cpu_burn(n)
    t_serial = time.perf_counter() - t0
    report("串行 2 次", t_serial, t_serial)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(cpu_burn, [n, n]))
    t_thread = time.perf_counter() - t0
    report("2 个线程并发", t_thread, t_serial)

    t0 = time.perf_counter()
    with ProcessPoolExecutor(max_workers=2) as pool:
        list(pool.map(cpu_burn, [n, n]))
    t_proc = time.perf_counter() - t0
    report("2 个进程并发（含启动开销）", t_proc, t_serial)

    print()
    print("  结论：")
    print("    线程版本基本没有加速，甚至更慢 —— 两个线程抢同一把 GIL，")
    print("    同一时刻只有一个能在跑，还要额外付出线程切换的开销。")
    print("    进程版本有加速，但被 Windows 的 spawn 启动开销吃掉了一部分。")
    print("    任务再大一些（跑十几秒），进程的优势会更明显。")
    print()
    print(f"  本机 CPU 逻辑核心数：{__import__('os').cpu_count()}")


# ======================================================================
# 8.2  IO 密集：多线程真的有用
# ======================================================================
def demo_io_bound() -> None:
    section("8.2 IO 密集：多线程和协程才发挥作用")

    delay, count = 0.25, 4
    print(f"  任务：io_task(0.25s) 跑 {count} 次（模拟网络请求）")
    print()

    t0 = time.perf_counter()
    for _ in range(count):
        io_task(delay)
    t_serial = time.perf_counter() - t0
    report("串行", t_serial, t_serial)

    t0 = time.perf_counter()
    with ThreadPoolExecutor(max_workers=count) as pool:
        list(pool.map(io_task, [delay] * count))
    t_thread = time.perf_counter() - t0
    report(f"{count} 个线程", t_thread, t_serial)

    async def async_io(d: float) -> float:
        await asyncio.sleep(d)          # 注意是 asyncio.sleep，不是 time.sleep
        return d

    async def run_all():
        return await asyncio.gather(*(async_io(delay) for _ in range(count)))

    t0 = time.perf_counter()
    asyncio.run(run_all())
    t_async = time.perf_counter() - t0
    report(f"{count} 个协程（asyncio）", t_async, t_serial)

    print()
    print("  结论：")
    print("    三种方式里，串行是 1 秒，并发都是 0.25 秒左右。")
    print("    原因：time.sleep / IO 等待时会主动释放 GIL，别的线程能继续跑。")
    print()
    print("  !! 反面教材 !!  如果把 async_io 里的 await asyncio.sleep 换成 time.sleep，")
    print("     整个事件循环会被阻塞，协程版本会退化成串行（甚至更慢）。")
    print("     同理，在 async 函数里调用 requests.get() 也是灾难。")


# ======================================================================
# 8.4 threading：锁与竞态
# ======================================================================
def demo_threading_lock() -> None:
    section("8.4 threading：共享状态必须加锁")

    rounds = 4
    per_round = 200_000
    expected = rounds * per_round

    def tight_worker():
        """读和写之间没有任何函数调用。"""
        global _unsafe_counter
        for _ in range(per_round):
            _unsafe_counter += 1

    def realworld_worker():
        """读和写之间隔着一次函数调用 —— 这才是真实代码的样子。"""
        global _unsafe_counter
        for _ in range(per_round):
            v = _unsafe_counter
            _unsafe_counter = _identity(v) + 1

    def run_threads(target, workers=rounds):
        threads = [threading.Thread(target=target) for _ in range(workers)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

    global _unsafe_counter             # 少了这行，下面的赋值只会创建一个局部变量

    print(f"  4 个线程，每个线程把同一个全局计数器加 {per_round:,} 次")
    print(f"  期望结果：{expected:,}")
    print()

    _unsafe_counter = 0
    run_threads(tight_worker)
    lost_tight = expected - _unsafe_counter
    print(f"  A. 紧凑的 `counter += 1`（读和写之间没有调用）")
    print(f"     实际 {_unsafe_counter:,}，丢了 {lost_tight:,} 次")
    print()

    # 默认的线程切换间隔是 5 毫秒（sys.getswitchinterval()）。
    # 这个循环跑得太快，几毫秒内就结束了，来不及发生几次切换。
    # 调成 10 微秒是为了把「切换点」变密，让本来就存在的窗口露出来。
    old_interval = sys.getswitchinterval()
    sys.setswitchinterval(1e-5)
    try:
        _unsafe_counter = 0
        run_threads(realworld_worker)
        lost_real = expected - _unsafe_counter
    finally:
        sys.setswitchinterval(old_interval)

    print(f"  B. 读 -> 调用一次函数 -> 写（模拟「读出来算一下再存回去」）")
    print(f"     实际 {_unsafe_counter:,}，丢了 {lost_real:,} 次")
    print()

    lock = threading.Lock()
    safe_counter = 0

    def safe_worker():
        nonlocal safe_counter
        for _ in range(per_round):
            with lock:                 # 拿不到锁就在这里等
                safe_counter += 1

    run_threads(safe_worker)
    print(f"  C. 加锁保护（读-改-写整体在锁内）")
    print(f"     实际 {safe_counter:,}，丢了 {expected - safe_counter:,} 次")
    print()

    print("  A 的结果是不是很反直觉？这在 CPython 3.12+ 上是**正常**的：")
    print("     解释器只在『循环回跳』『函数调用』『返回』这些位置才检查要不要切线程，")
    print("     而紧凑的 += 1 中间没有这些位置，所以它实际上被『顺带保护』了。")
    print("     这是实现细节，不是语言保证 —— 换 PyPy、换 free-threaded 构建，")
    print("     或者换一行 CPython 版本，结论都可能变。")
    print()
    print("  B 才是真实世界的样子：读和写之间永远隔着点什么 ——")
    print("     读缓存 / 查数据库 / 打日志 / 发请求。窗口一旦出现，更新就会丢。")
    print("     这类 bug 的特点是**大部分时候是对的**，只在压力大时偶发，极难复现。")
    print()
    print("  用 GIL 不能救你 —— GIL 保护的是解释器内部结构，不是你的业务变量。")
    print("  真正可靠的做法是 C：用锁，或者干脆别共享（见 q5 答案里的 queue 方案）。")


# ======================================================================
# 8.3 concurrent.futures
# ======================================================================
def demo_futures() -> None:
    section("8.3 concurrent.futures：日常首选")

    print("  -- map：结果顺序和输入一致，不管谁先算完 --")
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(io_task, [0.20, 0.05, 0.15, 0.01]))
    print(f"     输入 [0.20, 0.05, 0.15, 0.01]")
    print(f"     输出 {results}   <- 严格保序")
    print()

    print("  -- as_completed：谁先完成先处理谁 --")
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(io_task, d): d for d in [0.20, 0.05, 0.15, 0.01]}
        order = [fut.result() for fut in as_completed(futures)]
    print(f"     完成顺序 {order}   <- 按实际耗时排的")
    print()

    print("  -- 异常会被完整地传递回主线程 --")

    def risky(x):
        if x == 2:
            raise ValueError(f"我不喜欢 {x}")
        return x * 10

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [(i, pool.submit(risky, i)) for i in range(4)]
        for i, fut in futures:
            try:
                print(f"     submit(risky, {i}) -> {fut.result()}")
            except ValueError as exc:
                print(f"     submit(risky, {i}) 抛出 -> {type(exc).__name__}: {exc}")
    print("     ^ 裸 threading 里子线程的异常只会往 stderr 打一行，很容易漏掉。")


# ======================================================================
# 8.4 asyncio
# ======================================================================
def demo_asyncio() -> None:
    section("8.4 asyncio：单线程事件循环")

    print("  -- 协程是协作式调度：只在 await 处让出控制权 --")

    async def step(name: str, delay: float):
        print(f"     [{name}] 开始")
        await asyncio.sleep(delay)
        print(f"     [{name}] 结束（等了 {delay}s）")
        return name

    async def serial_vs_concurrent():
        print("     串行 await：")
        t0 = time.perf_counter()
        await step("A", 0.10)
        await step("B", 0.10)
        print(f"     耗时 {time.perf_counter() - t0:.3f}s\n")

        print("     用 gather 并发：")
        t0 = time.perf_counter()
        await asyncio.gather(step("A", 0.10), step("B", 0.10))
        print(f"     耗时 {time.perf_counter() - t0:.3f}s")

    asyncio.run(serial_vs_concurrent())
    print()
    print("  ^ 关键：`await coro` 是「等它做完」，")
    print("           `gather(coro1, coro2)` 才是「同时跑两个」。")
    print()

    print("  -- Semaphore 限制并发度 --")

    sem = asyncio.Semaphore(3)
    max_seen = 0
    current = 0

    async def limited(i: int):
        nonlocal current, max_seen
        async with sem:
            current += 1
            max_seen = max(max_seen, current)
            await asyncio.sleep(0.02)
            current -= 1
            return i

    async def run_limited():
        return await asyncio.gather(*(limited(i) for i in range(20)))

    got = asyncio.run(run_limited())
    print(f"     20 个任务、Semaphore(3)：观测到的最大并发数 = {max_seen}")
    print(f"     返回值 {got[:5]}... （gather 保序）")
    print()
    print("     爬虫不限流的下场：目标站点封你 IP，或者本地文件描述符耗尽。")


# ======================================================================
# 8.5 性能剖析
# ======================================================================
def demo_profiling() -> None:
    section("8.5 性能剖析：别猜，去测")

    import timeit

    print("  -- timeit：比较两种等价的写法 --")
    t_gen = timeit.timeit('"-".join(str(n) for n in range(200))', number=5000)
    t_map = timeit.timeit('"-".join(map(str, range(200)))', number=5000)
    print(f"     生成器表达式  {t_gen:.4f}s")
    print(f"     map + 内置   {t_map:.4f}s   （快 {(t_gen / t_map - 1) * 100:.0f}%）")
    print("     map 更快是因为 str() 的调用发生在 C 层，不经过 Python 的求值循环。")
    print()

    print("  -- cProfile：找出真正的时间黑洞 --")

    def parse_row(row):
        return [x.strip() for x in row.split(",")]

    def validate(row):
        return all(f for f in row)

    def heavy_work():
        data = [f" a{i} , b{i} , c{i} " for i in range(4000)]
        total = 0
        for _ in range(30):
            rows = [parse_row(r) for r in data]
            total += sum(1 for r in rows if validate(r))
        return total

    pr = cProfile.Profile()
    pr.enable()
    heavy_work()
    pr.disable()

    print("     按 tottime（函数自身耗时）排序的前 5 名：")
    stats = pstats.Stats(pr)
    stats.sort_stats("tottime")
    stats.print_stats(5)

    print("  看 cProfile 输出的要点：")
    print("     tottime  = 函数自身耗时（不含子调用）-> 找热点看这个")
    print("     cumtime  = 含子调用的总耗时            -> 找调用链看这个")
    print("     ncalls   = 调用次数；次数多但 tottime 小 -> 单次很便宜，只是调得太频繁")
    print()
    print("  命令行等价用法：python -m cProfile -s tottime myscript.py")
    print("  想看运行中的进程：pip install py-spy; py-spy top -- python myscript.py")


# ======================================================================
def main() -> None:
    demo_cpu_bound()
    demo_io_bound()
    demo_threading_lock()
    demo_futures()
    demo_asyncio()
    demo_profiling()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":          # Windows + multiprocessing 的硬性要求
    main()
