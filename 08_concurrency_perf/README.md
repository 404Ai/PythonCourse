# 模块 08 · 并发与性能

> **目标**：搞清楚 Python 里「并发」到底能做什么、不能做什么，
> 以及**在什么场景该用哪种方案**。
>
> 这一模块的知识点网上错误信息极多，尤其是关于 GIL 的。
> 我们直接跑代码验证，不信传言。

---

## 8.1 GIL：全局解释器锁

### 一句话定义

**GIL（Global Interpreter Lock）是 CPython 解释器里的一把互斥锁，
任何时刻只允许一个线程执行 Python 字节码。**

注意三件事：

1. **它属于 CPython 实现，不属于 Python 语言**。PyPy 有 GIL，Jython 和
   IronPython 没有。Python 3.13 起有官方的 free-threaded 构建（无 GIL），
   3.14 起这个构建被正式支持（PEP 779），但默认构建**仍然有 GIL**。
2. **它保护的是解释器内部状态**，不是你的数据。
   `list`、`dict` 的内部结构在 GIL 下不会被并发破坏——
   但这也意味着**你的业务逻辑正确性，GIL 一点忙都帮不上**。
3. **它只锁字节码执行**。执行到 IO 操作（读文件、网络请求、`time.sleep`）时，
   线程会**主动释放 GIL**，让别的线程跑。

### 直接看后果

```python
# CPU 密集：多线程完全无效，甚至更慢
import threading, time

def burn():
    total = 0
    for i in range(5_000_000):
        total += i * i
    return total

# 串行两次
t0 = time.perf_counter()
burn(); burn()
print(f"串行:   {time.perf_counter() - t0:.2f}s")

# 两个线程各跑一次
t0 = time.perf_counter()
ts = [threading.Thread(target=burn) for _ in range(2)]
for t in ts: t.start()
for t in ts: t.join()
print(f"多线程: {time.perf_counter() - t0:.2f}s")   # 基本一样，甚至更慢
```

原因：两个线程要抢同一把 GIL，抢到了才能执行字节码。
再加上线程切换的开销，多线程版本通常**比串行还慢一点**。

但换成 IO 就完全不同：

```python
def fetch():
    time.sleep(0.3)      # 模拟网络请求 —— sleep 会释放 GIL

# 串行三次 ≈ 0.9s
# 三个线程 ≈ 0.3s      <- 真的并发了
```

**所以**：

| 任务类型 | 多线程有用吗 | 原因 |
|---------|------------|------|
| CPU 密集（纯计算） | **没用** | 抢 GIL，等于串行 |
| IO 密集（网络、磁盘） | **有用** | IO 等待时释放 GIL |
| 调用 C 扩展且该扩展释放 GIL（NumPy、`hashlib`、`zlib`） | **有用** | 计算发生在 GIL 之外 |

### 一个反直觉的细节：到底什么时候会丢更新

「多线程不加锁会丢更新」这句话是对的，但**不是在所有情况下都能复现**。
在 CPython 3.12+ 上跑 `demo.py` 你会看到：

| 循环体 | 丢失的更新 |
|--------|-----------|
| `counter += 1`（紧凑，中间没有调用） | **0 次** |
| `v = counter; counter = f(v) + 1`（读和写之间有一次函数调用） | **约 48 万次 / 80 万次** |
| 加锁版本 | 0 次 |

第一行是不是很意外？原因是：**解释器并不是每条字节码之后都检查要不要切线程**。
检查点只放在「循环回跳」「函数调用」「返回」这些位置，
而紧凑的 `counter += 1` 中间一个检查点都没有，所以它被「顺带保护」了。

**但这是实现细节，不是语言保证。** 换 PyPy、换 free-threaded 构建、
换一个 CPython 版本，结论都可能变。而且现实代码里读和写之间**永远**隔着点什么——
读缓存、查数据库、打日志、发请求。窗口一旦出现，更新就会丢。

所以正确的结论是：

- ❌「Python 有 GIL，所以不用加锁」
- ❌「`+= 1` 一定会丢更新」
- ✅ **「共享可变状态必须用锁保护，或者干脆不要共享」**

> 顺带一提：`sys.setswitchinterval()` 控制的就是这个检查的间隔（默认 5 毫秒）。
> demo 里把它调成 10 微秒，就是为了把本来就存在的窗口暴露出来，
> 否则这段代码几毫秒就跑完了，根本来不及切换几次。

### GIL 的历史包袱

GIL 让 CPython 的实现简单了很多：引用计数不需要原子操作、内存管理不用加锁、
C 扩展写起来不用考虑线程安全。代价就是多核时代的多线程形同虚设。

**为什么到现在还没去掉？** 因为去掉会让单线程性能下降 30%~40%，
而且会打破大量 C 扩展的假设。Python 3.13+ 的 free-threaded 构建是官方答案，
但它需要第三方库逐步适配，短期内不会成为默认。

### `sys.setswitchinterval()`

GIL 的切换不是每个字节码都发生。CPython 用「执行多少个字节码指令后检查一次」
的策略，默认阈值是 5 毫秒（`sys.getswitchinterval()`）。
调小会让线程切换更频繁（IO 响应更快，但整体吞吐下降）。

---

## 8.2 三种并发方案

### 方案一：`threading` —— 线程

适合：**IO 密集，且用的是不支持 asyncio 的库**（比如 `requests`、老式 SDK）。

```python
import threading

results = []

def worker(x):
    results.append(x * 2)

threads = [threading.Thread(target=worker, args=(i,)) for i in range(5)]
for t in threads:
    t.start()
for t in threads:
    t.join()          # 等所有线程结束
```

问题：

- 要自己管理 `start`/`join`
- 异常发生在子线程里**不会传播到主线程**，会静默消失
- 共享数据的同步要自己加锁

### 方案二：`multiprocessing` —— 进程

适合：**CPU 密集**。每个进程有自己的解释器和自己的 GIL，能真正用满多核。

代价：

- 进程启动开销大（Windows 上尤其大）
- 数据要在进程间**序列化（pickle）**传输，大对象很慢
- 不能共享普通对象（要用 `multiprocessing.Queue` / `Value` / `Manager`）

**Windows 上的大坑**：Windows 没有 `fork`，只能 `spawn`——
新进程会**重新导入你的主模块**。所以：

```python
# 这样写会在 Windows 上无限递归创建进程，直接崩掉！
from multiprocessing import Pool

def work(x):
    return x * 2

p = Pool(4)
print(p.map(work, range(10)))
```

```python
# 必须加这个保护
from multiprocessing import Pool

def work(x):
    return x * 2

if __name__ == "__main__":        # <- 少了这行，Windows 上必炸
    p = Pool(4)
    print(p.map(work, range(10)))
```

原因：子进程被 spawn 时会重新 import 主模块，于是又执行了一遍 `Pool(4)`…

**这不是可选的风格问题，是硬性要求。**

### 方案三：`asyncio` —— 协程

适合：**超高并发的 IO**（几千个网络连接）。

核心思想：**单线程内的事件循环**。协程遇到 IO 时主动 `await`，
把控制权交回事件循环，循环去跑别的协程。

```python
import asyncio

async def fetch(name, delay):
    await asyncio.sleep(delay)        # 这里会「让出」控制权
    return name

async def main():
    # 三个协程并发跑，总耗时约 0.3s 而不是 0.9s
    return await asyncio.gather(
        fetch("a", 0.3), fetch("b", 0.2), fetch("c", 0.1)
    )

result = asyncio.run(main())
```

关键区别：

| | `threading` | `asyncio` |
|---|---|---|
| 调度者 | 操作系统 | 事件循环（你在的程序里） |
| 切换时机 | 抢占式（随时可能被切） | 协作式（只在 `await` 处切） |
| 竞态条件 | 随时可能出现 | **只在 `await` 处可能** |
| 并发量级 | 几百个线程就吃力 | 上万个协程没问题 |
| 生态 | 所有同步库都能用 | 必须要 `async` 版本的库 |

**协作式调度的好处**：你不用到处加锁。只要记得
「两个 `await` 之间的代码是原子的」，推理难度大幅下降。

### 什么时候用哪个：决策树

```
任务是什么？
│
├─ CPU 密集（纯计算、图像处理、加解密）
│   └─> multiprocessing / ProcessPoolExecutor
│       （或者：换 NumPy 之类的 C 扩展，让它替你在 GIL 外算）
│
└─ IO 密集
    ├─ 任务量小（几十个）、用的是同步库
    │   └─> 直接串行，别折腾
    │
    ├─ 用的是同步库（requests、pymysql、open）
    │   └─> threading / ThreadPoolExecutor
    │
    └─ 量大（几百上千）、有 async 版本的库（aiohttp、asyncpg）
        └─> asyncio
```

---

## 8.3 最实用的：`concurrent.futures`

`Thread` / `Process` 那套 API 太底层了。**日常写代码应该优先用
`concurrent.futures`**，它把线程池和进程池统一成了同一套接口。

```python
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor

def fetch(url):
    ...

urls = [...]
with ThreadPoolExecutor(max_workers=8) as pool:
    results = list(pool.map(fetch, urls))     # 结果顺序和输入一致
```

换成进程池，只要改一行：

```python
with ProcessPoolExecutor(max_workers=4) as pool:
    results = list(pool.map(fetch, urls))
```

### 三个常用方法

```python
executor.map(fn, items)
# 最简单。返回迭代器，结果顺序 == 输入顺序。
# 缺点：如果有任务抛异常，会在你迭代到它时才抛出。

executor.submit(fn, *args)
# 返回一个 Future 对象，可以拿到 .result() / .exception() / .done()。
# 提交后立刻返回，不阻塞。

# 谁先完成先处理谁 —— 适合「哪个请求先回来就先处理哪个」
from concurrent.futures import as_completed
futures = [executor.submit(fetch, u) for u in urls]
for fut in as_completed(futures):
    print(fut.result())
```

### 异常处理

`submit` 的异常会在 `.result()` 时重新抛出，**带上原始 traceback**：

```python
fut = pool.submit(risky, 1, 2)
try:
    fut.result()
except ZeroDivisionError:
    ...
```

这一点比裸 `threading` 强得多——裸线程里的异常默认只会往 stderr 打一行，很容易漏掉。

### 别忘了 `with`

`ThreadPoolExecutor` 没有 `with` 时不会自动关闭线程池，程序可能**卡在退出**。
用 `with` 保证 `shutdown()` 被调用。

---

## 8.4 `asyncio` 实战要点

### 三个必须记住的东西

```python
asyncio.run(main())              # 程序入口，创建事件循环并运行到结束
await asyncio.sleep(1)           # 异步的 sleep，不能用 time.sleep
await asyncio.gather(*coros)     # 并发跑多个协程，返回结果列表（保序）
```

### `time.sleep` 是 asyncio 的头号杀手

```python
async def bad():
    time.sleep(1)      # 阻塞整个事件循环！所有其他协程一起卡住

async def good():
    await asyncio.sleep(1)   # 让出控制权
```

同样地，`requests.get()` 会阻塞事件循环，必须换 `aiohttp` / `httpx`。
**这就是为什么 asyncio 生态是分裂的**——一个同步调用能毁掉整个事件循环。

### `gather` vs `TaskGroup`

```python
# 老写法：gather
results = await asyncio.gather(*coros)
# 问题：一个任务抛异常，其他的不会被取消，会以 "Task exception was never retrieved" 告警

# 3.11+ 推荐：TaskGroup
async with asyncio.TaskGroup() as tg:
    t1 = tg.create_task(fetch("a"))
    t2 = tg.create_task(fetch("b"))
# 退出 with 块时自动 await 全部完成；任何一个失败，其余自动取消
```

### 限制并发度：`Semaphore`

爬虫最容易犯的错是「一次发起一万个请求」，结果被对方封 IP 或者自己 OOM。

```python
sem = asyncio.Semaphore(10)      # 最多 10 个并发

async def fetch(url):
    async with sem:              # 超过 10 个就在这排队
        ...
```

### 加超时

```python
# 3.11+ 的写法
async with asyncio.timeout(5):
    await fetch(url)
```

---

## 8.5 性能剖析：别猜，去测

> **过早优化是万恶之源。** 而且人肉猜瓶颈的准确率极低——
> 我见过太多人花一天优化一个只占 2% 耗时的函数。

### 微观：`timeit`

```python
import timeit

# 比较两种写法
t1 = timeit.timeit('"-".join(str(n) for n in range(100))', number=10000)
t2 = timeit.timeit('"-".join(map(str, range(100)))', number=10000)
print(f"生成器: {t1:.4f}s   map: {t2:.4f}s")
```

`timeit` 会自动重复多次取最优值，并把垃圾回收的影响降到最低。
**在 IPython / Jupyter 里用 `%timeit` 更方便。**

### 宏观：`cProfile`

```python
import cProfile, pstats

pr = cProfile.Profile()
pr.enable()
main()                     # 你要分析的那段代码
pr.disable()

pstats.Stats(pr).sort_stats("cumulative").print_stats(15)
```

两个关键指标：

- **`tottime`**：函数**自身**（不含子调用）消耗的时间 —— 找「热点代码」
- **`cumtime`**：函数**及其所有子调用**消耗的时间 —— 找「耗时的调用链」

**找瓶颈看 `tottime`**，否则你看到的永远是 `main()` 排第一。

命令行用法：

```powershell
python -m cProfile -s tottime myscript.py | more
```

可视化可以用 `snakeviz` / `py-spy`（`py-spy` 能直接看运行中的进程，非常好用）：

```powershell
pip install py-spy
py-spy top -- python myscript.py
```

### 逐行：`line_profiler`

```powershell
pip install line_profiler
```

```python
@profile          # 注意：不用 import，是 kernprof 注入的
def slow_function():
    ...
```

```powershell
kernprof -l -v myscript.py
```

---

## 8.6 优化手段速查（按性价比排序）

| 手段 | 提速幅度 | 说明 |
|------|---------|------|
| **换算法/数据结构** | 10~1000x | `list` 查找换 `set`，O(n²) 换 O(n log n) |
| **用 C 扩展（NumPy 等）** | 10~100x | 把循环交给 C |
| **换并发模型** | 2~20x | IO 密集上线程/协程；CPU 密集上进程 |
| **缓存（`lru_cache`）** | 取决于重复率 | 纯函数才安全 |
| **局部变量绑定** | 10~30% | `append = out.append` 这种，可读性换性能 |
| **用内置函数 / 推导式** | 20~50% | 模块 02 讲过 |
| **`__slots__`** | 内存省 40% | 类实例多时才有意义 |

**注意**：前两条是数量级差异，后面都是常数级。**永远先想前两条。**

---

## 8.7 常见坑速查

| 坑 | 后果 | 正解 |
|----|------|------|
| CPU 密集用多线程 | 完全没加速 | 换 `ProcessPoolExecutor` |
| Windows 上用 `multiprocessing` 不加 `if __name__ == "__main__"` | 进程爆炸 | 加保护 |
| `asyncio` 里调 `time.sleep` / `requests` | 整个事件循环卡住 | `await asyncio.sleep` / `aiohttp` |
| 线程里读写共享变量不加锁 | 数据丢失且难复现 | `threading.Lock` |
| 子线程里的异常 | 静默消失 | 用 `concurrent.futures`，异常会在 `.result()` 抛出 |
| `ThreadPoolExecutor` 不用 `with` | 程序退出时卡住 | 用 `with` |
| 一次发起几千个请求 | 被封 IP / OOM | `Semaphore` 限流 |
| `gather` 里某个任务失败 | 其他任务继续跑，资源泄漏 | 用 `asyncio.TaskGroup` |
| `lru_cache` 用在有副作用的函数上 | 结果错误 | 只缓存纯函数 |
| 传大对象给进程池 | 序列化开销比计算还大 | 传小数据，或者用共享内存 |

---

## 8.8 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | **实测**串行/线程/进程/协程在 CPU 密集和 IO 密集下的耗时对比 |
| `exercises.py` | 9 道练习 |
| `solutions.py` | 参考答案 |

**这一模块的 demo 一定要跑。** 「多线程对 CPU 密集任务毫无帮助」
这件事，看多少次文字都不如自己看一次计时结果震撼。

---

## 8.9 延伸阅读

- [Python 官方文档：concurrent.futures](https://docs.python.org/zh-cn/3/library/concurrent.futures.html) —— 最该先读的
- [Python 官方文档：asyncio](https://docs.python.org/zh-cn/3/library/asyncio.html)
- [PEP 703: Making the GIL Optional](https://peps.python.org/pep-0703/) —— 无 GIL 的官方设计文档
- [PEP 779: free-threaded 正式支持](https://peps.python.org/pep-0779/)
- 《流畅的 Python》第 19、20 章（并发模型）
- `py-spy` 项目主页 —— 生产环境排查性能问题的利器
