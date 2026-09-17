# 模块 05 · 迭代器、生成器、上下文管理器

> **目标**：这个模块讲的是 Python 最有辨识度的三件套。
> 它们不是语法糖，而是**同一套东西的三个面**——
> 「惰性求值」在数据流上的表现叫迭代器，
> 在函数上的表现叫生成器，
> 在资源管理上的表现叫上下文管理器。
>
> 学完你应该能把一个「先造一个大列表再处理」的循环，
> 改写成「一边算一边吐」的流水线。

---

## 5.1 可迭代对象 vs 迭代器

### 两个协议，一个区别

```
   可迭代对象 (Iterable)          迭代器 (Iterator)
   ─────────────────────          ─────────────────
   实现了 __iter__                 实现了 __iter__ 和 __next__
   每次 iter() 返回一个迭代器       __iter__ 返回 self
   能反复遍历                      一次性的，走过就没了
   例：list / str / dict / range   例：文件对象 / 生成器 / map / zip
```

**`iter(x)` 做两件事**：

1. 调用 `x.__iter__()`，拿到一个迭代器
2. 如果 `x` 没有 `__iter__`，退而求其次看 `x.__getitem__`（旧式序列协议），
   现场包一个迭代器出来

```python
it = iter([1, 2, 3])     # 拿到一个 list_iterator
next(it)                 # 1
next(it)                 # 2
next(it)                 # 3
next(it)                 # StopIteration
```

### `for` 循环的完整展开

```python
for x in obj:
    handle(x)
```

等价于：

```python
_iterator = iter(obj)          # 1. 拿迭代器，只做一次
while True:
    try:
        x = next(_iterator)    # 2. 每次取一个
    except StopIteration:      # 3. 取完了就退出
        break
    handle(x)
```

**两个关键推论**：

- **`StopIteration` 是正常控制流，不是错误。** `for` 靠捕获它来结束循环。
  （也正因如此，**生成器内部绝对不能抛 `StopIteration`**——它会
  被误认为「迭代结束」，Python 3.7+ 会把它转成 `RuntimeError` 提醒你。）
- `iter(obj)` 在循环开始前只调用一次。所以「可迭代对象」和「迭代器」
  在这个位置被统一对待了——**这就是 `for` 能同时吃下列表和生成器的原因**。

### 手写一个迭代器

```python
class Countdown:
    """从 n 倒数到 1。"""

    def __init__(self, n: int) -> None:
        self.n = n

    def __iter__(self):
        return self                    # 迭代器必须返回自己

    def __next__(self):
        if self.n <= 0:
            raise StopIteration        # 结束信号
        self.n -= 1
        return self.n + 1
```

```python
list(Countdown(3))       # [3, 2, 1]
list(Countdown(3))       # []   <- 注意！同一个对象已经耗尽了
```

### 为什么 `__iter__` 返回 `self` 是个常见 bug 源

因为它把「可迭代对象」和「迭代器」合并成了一个东西，于是**只能遍历一次**。
想反复遍历就得分开：

```python
class Countdown:
    def __init__(self, n: int) -> None:
        self.n = n

    def __iter__(self):
        return CountdownIterator(self.n)    # 每次都造一个新的迭代器
```

**判断标准**：你要的是一个「数据源」还是一个「游标」？
数据源（列表、range、你的容器类）应该每次 `iter()` 都返回**新的**迭代器；
游标（文件、网络流）本身就是一次性的，返回 `self` 才对。

---

## 5.2 生成器函数

### `yield` = 暂停，不是返回

```python
def gen():
    print("A")
    yield 1
    print("B")
    yield 2
    print("C")

g = gen()          # 什么都没打印！函数体一行都没执行
print("拿到生成器了")

next(g)            # 打印 "A"，返回 1
next(g)            # 打印 "B"，返回 2
next(g)            # 打印 "C"，抛 StopIteration
```

**这是和普通函数最根本的区别**：
调用生成器函数**不执行函数体**，只是造出一个生成器对象。
真正的执行发生在第一次 `next()` 时。

**执行的状态（局部变量、指令指针、求值栈）全部保存在生成器对象的帧里**，
所以暂停之后还能接着跑。这也解释了生成器为什么占内存——
它得把整个执行上下文留着。

### 生成器表达式的惰性

```python
squares_list = [x * x for x in range(5)]     # 立刻算完，5 个 int 都在内存里
squares_gen  = (x * x for x in range(5))     # 什么都没算
```

```python
print(squares_list)      # [0, 1, 4, 9, 16]
print(squares_gen)       # <generator object <genexpr> at 0x...>
```

> **注意**：`(x for x in ...)` 只有一个参数时，**圆括号里那对才是生成器表达式**。
> `sum(x for x in ...)` 可以省一层括号，因为函数调用本身的括号就够了；
> 但 `sum((x for x in ...))` 和 `sum([x for x in ...])` 是**不同**的东西。

### `send` / `throw` / `close`（知道有这回事就行）

```python
def echo():
    received = None
    while True:
        received = yield received      # yield 表达式的值 = send 进来的值
        print(f"收到 {received}")

g = echo()
next(g)                # 必须先「预热」一次，跑到第一个 yield
g.send("hello")        # 收到 hello
g.send("world")        # 收到 world
g.close()              # 内部抛 GeneratorExit，生成器结束
```

- **`send(v)`**：把值送进生成器，成为 `yield` 表达式的返回值。第一次必须先 `next()`。
- **`throw(exc)`**：在暂停处抛一个异常进去，生成器内部可以 `try/except` 接住。
- **`close()`**：让生成器在暂停处收到 `GeneratorExit`，用来做清理。

这套东西是 `asyncio` 协程的底层（`async def` + `await` 本质上就是
「可以挂起的生成器」）。**日常写业务代码几乎用不到 `send`**，
但知道它存在，读别人的框架代码时才不会懵。

### `yield from`：把子生成器接上来

```python
def flat():
    yield from [1, 2, 3]
    yield from range(4, 6)

list(flat())     # [1, 2, 3, 4, 5]
```

`yield from` 不只是省一个 `for`：
它会把 `send` / `throw` / `close` **原样转发**给子生成器，
返回值也能拿到（`result = yield from sub()`）。要写生成器驱动的协程就得用它。

---

## 5.3 为什么生成器只能遍历一次

**因为迭代器是有状态的，而生成器就是迭代器。**

生成器对象内部保存着「我执行到哪儿了」。第一次遍历把它推到了末尾，
第二次 `for` 拿到的是**同一个已经耗尽的生成器**，于是循环体一次都不执行。

```python
g = (x for x in range(3))
list(g)      # [0, 1, 2]
list(g)      # []          <- 不报错，只是空的
```

**这个坑最要命的地方在于它不报错。** 你看到的是一个空列表，
然后开始怀疑数据源、怀疑过滤条件，就是不怀疑「生成器被用过了」。

### 对比：为什么 `list` 可以反复遍历

```python
lst = [1, 2, 3]
list(lst)    # [1, 2, 3]
list(lst)    # [1, 2, 3]     <- 照样跑

it = iter(lst)
print(list(it))   # [1, 2, 3]
print(list(it))   # []        <- 迭代器本身也只能用一次
```

**`list` 是可迭代对象，不是迭代器。** 每次 `iter(lst)` 都造一个**新的**
`list_iterator`，新旧互不干扰。

> 一句话总结：
> **能被反复遍历的不是「迭代器」，是「能生产迭代器的东西」。**

### 什么时候必须小心

```python
def process(items):
    if not any(x > 10 for x in items):
        return
    for x in items:              # 如果 items 是生成器，这里已经是空的
        handle(x)
```

修法有三种：

```python
items = list(items)              # 1. 物化（数据量大就别用）
items, peek = itertools.tee(items)   # 2. 分流（有缓存代价，见 5.5）
# 3. 把两次遍历合并成一次（通常是最好的做法）
```

**实践准则**：函数签名里收到的参数，如果是「要被遍历两次」的，
就**在函数开头 `list()` 物化一次**，并在文档里写清楚。
或者干脆约定「本函数只遍历一次」，让调用方自己决定。

### 怎么判断一个东西是不是迭代器

```python
it = iter([1, 2, 3])
iter(it) is it           # True   -> 是迭代器（iter 返回自己）
lst = [1, 2, 3]
iter(lst) is lst         # False  -> 不是迭代器
```

**`iter(x) is x` 就是那条判断准则。**

---

## 5.4 生成器的内存优势：实测

### `sys.getsizeof` 在这里会骗你

```python
import sys
sys.getsizeof([x for x in range(100000)])   # 800984 字节（约 800 KB）
sys.getsizeof(x for x in range(100000))     # 大约 200 字节
```

**注意**：生成器的 `getsizeof` 是个**固定值**，跟它能产出多少项**无关**。
它量的是「生成器对象自己占多少」，不包括它将要产出的数据。
所以你没法用 `getsizeof` 比较「产出同样多项」的内存。

### 正确的量法：`tracemalloc` 看峰值

要比较「处理同样多的数据，内存峰值差多少」，得测**实际分配的峰值**：

```python
import tracemalloc

def peak_of(iterator_factory, n):
    tracemalloc.start()
    tracemalloc.reset_peak()
    total = 0
    for x in iterator_factory(n):        # 一边产一边消费，不攒着
        total += x
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak, total

peak_of(lambda n: [i for i in range(n)], 200000)      # 列表版，峰值很高
peak_of(lambda n: (i for i in range(n)), 200000)      # 生成器版，峰值很低
```

**结论的量级**：列表版峰值正比于 n（几十 MB），生成器版基本是常数（几 KB）。
具体数字看 `demo.py` 的实测输出。

> **别背数字，记住结论**：
> **列表的内存 = O(数据量)，生成器的内存 = O(1)。**
> 差一个数量级的复杂度，这才是「惰性」真正的价值。

### 最典型的场景：读大文件

```python
# 坏：整个文件读进内存
lines = open("huge.log", encoding="utf-8").readlines()
for line in lines:
    ...

# 好：一次一行
with open("huge.log", encoding="utf-8") as f:
    for line in f:                 # 文件对象本身就是个迭代器
        ...
```

**文件对象是 Python 里最经典的迭代器**：它实现了 `__iter__` 返回 `self`，
所以一个文件只能从头读到尾一次。

### 代价：惰性不是免费的

- **每次 `next()` 都有开销**，纯计算场景下生成器比列表推导慢（大约 1.2~2 倍）
- **无法 `len()`、无法切片、无法回退**（要长度就得全部走一遍）
- **调试更麻烦**：出问题时你不知道它「走到哪一步了」
- **异常会延迟到遍历时才爆发**，而不是定义时

**选择标准**：

| 场景 | 用什么 |
|------|--------|
| 数据小、要多次访问、要随机访问 | `list` |
| 数据大 / 无限流 / 只需要顺序过一遍 | 生成器 |
| 要 `len()` / 索引 | `list` |
| 管道式处理（几道工序串起来） | 生成器 |

---

## 5.5 `itertools` 精华

`itertools` 是标准库里性价比最高的一节。以下这些**读一遍就要记住**。

### 无限迭代器（必须配 `islice` 或 `break`）

```python
import itertools as it

it.count(10, 2)               # 10, 12, 14, ...       可以当 range 的无限版
it.cycle("ABC")               # A, B, C, A, B, C, ... 循环
it.repeat("x", 3)             # x, x, x               固定值重复 3 次
```

### 拼接与切片

```python
it.chain([1, 2], "ab", (3,))          # 1, 2, 'a', 'b', 3   把多个可迭代对象串起来
it.chain.from_iterable([[1, 2], [3]]) # 1, 2, 3             展平一层（惰性）
it.islice(it.count(), 5)              # 0, 1, 2, 3, 4       只支持正索引，不支持负数
it.islice(range(100), 10, 20, 2)      # 10, 12, ..., 18     等价于 [10:20:2]
```

### 组合数学（这三兄弟一定要记）

```python
list(it.product("AB", [1, 2]))          # 笛卡尔积，有顺序，共 4 项
# [('A', 1), ('A', 2), ('B', 1), ('B', 2)]

list(it.permutations("ABC", 2))         # 排列，有顺序，共 6 项
# [('A','B'), ('A','C'), ('B','A'), ('B','C'), ('C','A'), ('C','B')]

list(it.combinations("ABC", 2))         # 组合，无顺序，共 3 项
# [('A','B'), ('A','C'), ('B','C')]

list(it.combinations_with_replacement("AB", 2))
# [('A','A'), ('A','B'), ('B','B')]     允许重复拿同一个元素
```

> **排列 vs 组合**：`permutations` 认为 `(A,B)` 和 `(B,A)` 是两回事，
> `combinations` 认为是一回事。
> 「从 N 个里挑 K 个，顺序重要吗？」——回答这个就能选对。

### `groupby`：**必须先排序**

```python
data = [("水果", "苹果"), ("蔬菜", "白菜"), ("水果", "香蕉")]

for key, group in it.groupby(data, key=lambda p: p[0]):
    print(key, list(group))
# 水果 [('水果', '苹果')]
# 蔬菜 [('蔬菜', '白菜')]
# 水果 [('水果', '香蕉')]     <- 水果被分成了两组！
```

**`groupby` 只合并「相邻」的相同 key**，它不会替你把整个序列看完再分组
（那样就不惰性了）。所以标准写法永远是：

```python
sorted_data = sorted(data, key=lambda p: p[0])
for key, group in it.groupby(sorted_data, key=lambda p: p[0]):
    ...
```

**两个额外的坑**：

1. **`group` 是共享的迭代器**：一旦你推进到下一组，上一组的 group 就失效了。
   要保存就立刻 `list(group)`。

   ```python
   for key, group in it.groupby(sorted_data, key=...):
       groups[key] = group          # 错！全是空的/错的
       groups[key] = list(group)    # 对
   ```

2. **key 为 `None` 时**，`groupby` 用元素自身做 key。

### 累加与相邻

```python
list(it.accumulate([1, 2, 3, 4]))          # [1, 3, 6, 10]      累加
list(it.accumulate([1, 2, 3, 4], max))     # [1, 2, 3, 4]       累积最大值
list(it.accumulate([1, 2, 3, 4], initial=0))   # [0, 1, 3, 6, 10]（3.8+）

list(it.pairwise([1, 2, 3, 4]))            # [(1,2), (2,3), (3,4)]（3.10+，超好用）
list(it.batched(range(7), 3))              # [(0,1,2), (3,4,5), (6,)]（3.12+，分批）
```

### `tee`：分流，但有代价

```python
a, b = it.tee(source, 2)
```

`tee` 看起来像「复制一份」，实际上是**共享一个底层迭代器 + 各自缓存**：
谁落后就得把数据留着，**落后越多，内存越大**。
除非两个消费者速度差不多，否则不如直接 `list(source)`。

### 什么时候自己写而不是用 itertools

`itertools` 的函数都是**短小的组合件**，用在流水线里威力最大：

```python
# 读日志，取最近 100 条 ERROR，提取时间戳
with open("app.log", encoding="utf-8") as f:
    errors = (line for line in f if " ERROR " in line)
    recent = it.islice(errors, 100)
    stamps = (line.split(" ", 1)[0] for line in recent)
    for ts in stamps:
        ...
```

**整个链条里没有任何一个中间列表**——这就是「惰性管道」。

---

## 5.6 上下文管理器

### `with` 的完整展开

```python
with EXPR as VAR:
    BODY
```

等价于：

```python
mgr = EXPR                                  # 1. 求值，拿到管理器对象
VAR = mgr.__enter__()                       # 2. 返回值绑给 as 后面的名字
try:
    BODY
except BaseException as exc:                # 3. 出任何异常都交给 __exit__
    if not mgr.__exit__(type(exc), exc, exc.__traceback__):
        raise                               #    返回假值 -> 异常继续往外传
else:
    mgr.__exit__(None, None, None)          # 4. 正常结束
```

**三个必须记住的点**：

1. **`as` 绑的是 `__enter__` 的返回值，不是 `EXPR` 本身。**
   这就是为什么 `with open(...) as f` 拿到的是文件对象——
   因为 `file.__enter__` 返回 `self`。而 `with lock:` 里 lock 的
   `__enter__` 可以返回别的东西。
2. **`__exit__` 三个参数是 `(异常类型, 异常实例, traceback)`**，
   没异常时全是 `None`。
3. **`__exit__` 返回真值 = 吞掉异常**；返回 `None` / `False` = 放行。
   `return None` 是隐式的，所以**不打算吞异常就别写 `return True`**。

### 手写一个（类实现）

```python
class Timer:
    def __init__(self) -> None:
        self.elapsed = 0.0

    def __enter__(self) -> "Timer":
        self._start = time.perf_counter()
        return self                     # 关键：返回 self，才能 `as t`

    def __exit__(self, exc_type, exc, tb) -> None:
        self.elapsed = time.perf_counter() - self._start
        return None                     # 明确不吞异常（写出来更清楚）
```

```python
with Timer() as t:
    do_something()
print(f"耗时 {t.elapsed:.4f} 秒")
```

### `@contextmanager`：用生成器写，短很多

```python
from contextlib import contextmanager

@contextmanager
def timer():
    start = time.perf_counter()
    try:
        yield                       # yield 之前 = __enter__
    finally:
        elapsed.append(time.perf_counter() - start)   # yield 之后 = __exit__
```

**规则**：

- `yield` **之前**的代码 = `__enter__`
- `yield` **的值** = `as` 后面拿到的东西
- `yield` **之后**的代码 = `__exit__`
- **必须用 `try/finally` 包住 `yield`**，否则 `with` 块内抛异常时，
  清理代码**根本不会执行**——这是最常见的错误
- 想吞异常就在 `yield` 外面套 `try/except`（而不是 `finally`），
  然后正常返回即可

```python
@contextmanager
def suppress_value_error():
    try:
        yield
    except ValueError:
        pass                # 吞掉 ValueError —— 相当于 __exit__ 返回 True
```

**选择标准**：

| | 类实现 | `@contextmanager` |
|---|---|---|
| 代码量 | 多 | 少 |
| 需要被继承 / 复用 | 合适 | 不合适 |
| 需要保存状态给外部用 | 合适（`return self`） | 只能靠闭包变量 |
| 一次性的小工具 | 啰嗦 | **首选** |

### `__exit__` 吞异常的演示

```python
class Swallow:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb):
        print(f"看到了 {exc_type.__name__ if exc_type else '没有异常'}")
        return True          # 吞掉

with Swallow():
    raise ValueError("你抓不到我")
print("程序继续跑")
```

输出：

```
看到了 ValueError
程序继续跑
```

**这是 `with` 最容易用错的地方**：随手写个 `return True` 会让
`with` 块里的所有异常人间蒸发。**除非你在写 `suppress` 那样的工具，
否则不要吞异常。**

### `contextlib` 的三个实用工具

```python
from contextlib import suppress, closing, nullcontext, ExitStack

# 1. suppress：明确地忽略指定异常（比 try/except/pass 短，而且意图清楚）
with suppress(FileNotFoundError):
    os.remove("可能不存在的文件.txt")

# 2. closing：给「有 close() 但没有 __enter__」的对象补一个
with closing(urllib.request.urlopen(url)) as resp:
    data = resp.read()

# 3. nullcontext：什么都不做的上下文管理器
#    典型用途：让「可选资源」的两个分支写法统一
ctx = open(path) if path else nullcontext(sys.stdin)
with ctx as f:
    ...

# 4. ExitStack：动态管理「数量不确定」的资源
with ExitStack() as stack:
    files = [stack.enter_context(open(p, encoding="utf-8")) for p in paths]
    # 退出时按相反顺序全部关闭，中途出错也一样
```

`ExitStack` 值得单独记一笔：**它是「手动 `try/finally` 管理 N 个资源」
的唯一优雅解法**，在需要动态打开资源的地方无可替代。

---

## 5.7 上下文管理器的实际用途

### 1. 文件（最基础）

```python
with open("a.txt", encoding="utf-8") as f:
    text = f.read()
# 离开缩进块时无论正常还是异常，f 一定被关掉
```

**永远写 `encoding="utf-8"`**。不写就用系统默认编码——
Windows 上是 GBK，于是别人的机器上能跑的程序在你的机器上
`UnicodeDecodeError`。这是跨平台丢数据的第一大来源。

### 2. 锁

```python
import threading

lock = threading.Lock()

with lock:                    # 等价于 lock.acquire() / try / finally: lock.release()
    shared_state += 1
```

用 `with` 而不是手动 `acquire`/`release`，是因为
**中间抛异常时手写版本会死锁**。

### 3. 计时（性能分析）

```python
@contextmanager
def timed(label):
    start = time.perf_counter()
    try:
        yield
    finally:
        print(f"{label}: {time.perf_counter() - start:.4f}s")
```

### 4. 临时改环境变量

```python
@contextmanager
def temp_env(**overrides):
    old = {k: os.environ.get(k) for k in overrides}
    os.environ.update(overrides)
    try:
        yield
    finally:
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)     # 本来没有 -> 删掉
            else:
                os.environ[k] = v           # 本来有 -> 还原
```

**「本来不存在的键要删掉而不是设成空字符串」**是这类工具最容易漏的细节。
测试里改配置、临时切换 API 地址都靠它。

### 5. 数据库事务

```python
@contextmanager
def transaction(conn):
    try:
        yield conn
    except Exception:
        conn.rollback()          # 出任何错就回滚
        raise                    # 但异常要继续往上抛，别悄悄吞掉
    else:
        conn.commit()            # 只有正常走完才提交
```

**这个模式值得背下来**：`except` 里回滚 + `raise`，
`else` 里提交。顺序反了或者忘了 `raise` 都会造成
「事务失败了但程序以为成功了」。

### 6. 临时改工作目录 / 临时打补丁

```python
@contextmanager
def chdir(path):
    old = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(old)
```

### 共同点

**上下文管理器管的是「配对的操作」**：开/关、加锁/解锁、开始/结束、
提交/回滚。只要你在代码里写下 `X` 之后**必须**有 `Y`，就该想想
能不能包成一个 `with`。

而且注意上面每一个例子，清理逻辑都写在 **`finally`** 里——
**异常路径才是上下文管理器存在的理由**。正常路径上你自己
多写一行也能对；异常路径上你多半会忘。

---

## 5.8 其他 Pythonic 惯用法

### `enumerate` 带起始值

```python
for i, name in enumerate(names):          # 从 0 开始
for i, name in enumerate(names, start=1): # 从 1 开始（报表行号）
```

别写 `for i in range(len(names)): name = names[i]`——又慢又容易越界。

### `zip` 与 `strict=True`

```python
names = ["张三", "李四", "王五"]
scores = [90, 85]

list(zip(names, scores))                  # [('张三', 90), ('李四', 85)]  静默截断！
list(zip(names, scores, strict=True))     # ValueError: zip() argument 2 is shorter
```

**默认的静默截断是 bug 温床**。「两个列表应该一样长」是绝大多数
业务场景的隐含假设，一旦不成立，你得到的是**少了一行的结果**，
而不是一个错误。**3.10+ 请一律写 `strict=True`。**

### 解包

```python
a, b = b, a                     # 交换，不用临时变量
first, *rest = [1, 2, 3, 4]     # first=1, rest=[2, 3, 4]
*init, last = [1, 2, 3, 4]      # init=[1, 2, 3], last=4
head, *mid, tail = [1, 2, 3]    # head=1, mid=[2], tail=3

def f(*args, **kwargs): ...     # 收集
f(*[1, 2], **{"a": 1})          # 展开

d = {"x": 1, "y": 2}
{**d, "z": 3}                   # 字典解包
```

**`_` 是「我不关心」的约定**：

```python
for _ in range(3):              # 只要循环三次，不要下标
    do()

_, score = ("张三", 90)          # 只要分数
```

### `any` / `all` 是短路的

```python
any([False, True, ...])     # 遇到第一个真值就停，后面的不看了
all([True, True, ...])      # 遇到第一个假值就停
any([])                     # False   <- 空集合的 any 是 False
all([])                     # True    <- 空集合的 all 是 True（空真，容易记错）
```

**短路意味着生成器可以放心交给它们**：

```python
if any(line.startswith("ERROR") for line in huge_file):
    ...        # 找到第一条就停，不会读完整个文件
```

写成 `any([...])`（列表推导）就把整个文件读进内存了，短路白费。

### `dict.__missing__`：给缺失的键一个默认值

```python
class CountDict(dict):
    def __missing__(self, key):
        # 只在 d[key] 找不到时调用（不影响 get / in）
        self[key] = 0            # 顺手写回去，下次就是真的命中
        return 0

c = CountDict()
c["apple"] += 1
c["apple"] += 1
c["banana"] += 1
print(c)        # {'apple': 2, 'banana': 1}
```

**和 `defaultdict` 的区别**：
`defaultdict(list)` 每次访问都会**新建**一个 `list`；
`__missing__` 可以写更复杂的逻辑（比如计数从 0 开始、
或者从数据库查一次再缓存）。另外 `defaultdict` 的工厂函数
**不能**知道自己对应的 key，`__missing__ 能**。

> 用 `Counter` 计数、`defaultdict(list)` 分组是更常见的做法；
> `__missing__` 留给「默认值需要按 key 算」的场景。

### 字典合并 `|`（3.9+）

```python
a = {"x": 1, "y": 2}
b = {"y": 99, "z": 3}

a | b            # {'x': 1, 'y': 99, 'z': 3}   右边优先，返回新字典
a |= b           # 就地更新 a
{**a, **b}       # 老写法，效果一样
```

**注意 `|` 和 `|=` 的区别，跟模块 01 讲的 `+` / `+=` 是同一回事**：
`|` 新建，`|=` 就地改。

### `match` 语句（3.10+，简介）

`match` **不是** C 的 `switch`。它是**结构模式匹配**——能解构、能绑定变量、
能加守卫条件。

```python
match command.split():
    case ["go", direction]:                  # 列表结构 + 捕获变量
        move(direction)
    case ["look"]:                           # 精确匹配
        look()
    case ["take", item, *rest]:              # 星号收集剩余
        take(item, rest)
    case _:                                  # 兜底（_ 是通配符，不绑定）
        print("不懂这个命令")
```

**类模式**（对 dataclass 特别好用）：

```python
from dataclasses import dataclass

@dataclass
class Point:
    x: int
    y: int

match shape:
    case Point(x=0, y=0):
        print("原点")
    case Point(x=0, y=y):                    # 按属性解构 + 捕获 y
        print(f"在 y 轴上，y={y}")
    case Point(x=x, y=y) if x == y:          # 加守卫条件
        print("在对角线上")
    case Point():
        print("普通点")
```

`match` 是**静态结构匹配**，不是「等于」比较：

- `case 1` 匹配 `1`、`1.0`、`True`（因为 `1 == 1.0 == True`）
- `case [x, y]` 匹配任何长度为 2 的序列（列表、元组都行）
- **`case CONST` 里的名字会被当成捕获变量，除非它是带点的（`case Color.RED`）**

**要不要用**：处理「结构化的输入」时（解析协议、AST、命令、配置）
非常香；简单的值分派用 `if/elif` 反而更清楚。
**不要为了用而用。**

---

## 5.9 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| 生成器遍历两次 | 第二次静默为空，不报错 | 物化 `list()` 或改写成一次遍历 |
| `__iter__` 返回 `self` | 对象只能遍历一次 | 返回一个新迭代器 |
| `__iter__` 里写 `return iter(self)` | 无限递归 `RecursionError` | 返回 `self` 或新迭代器 |
| 函数里收到可迭代对象遍历两遍 | 第二次是空的 | 开头 `list()` 物化 |
| 生成器函数里 `raise StopIteration` | `RuntimeError`（3.7+） | 用 `return` 结束 |
| `sum([x for x in ...])` 处理大数据 | 内存爆掉 | `sum(x for x in ...)` |
| `groupby` 不排序 | 同一个 key 分成好几组 | 先 `sorted(key=...)` |
| 保存 `groupby` 的 group | 拿到的是空的 | 立刻 `list(group)` |
| `zip` 长度不等 | 静默截断，少数据 | `zip(..., strict=True)` |
| `all([])` | 返回 `True`（记错成 False） | 空真：`all` 为真、`any` 为假 |
| `@contextmanager` 忘了 `try/finally` | 块内抛异常时清理不执行 | `yield` 必须包在 `try/finally` 里 |
| `__exit__` 写 `return True` | 静默吞掉所有异常 | 明确不吞就返回 `None` |
| `with open(...)` 不写 `encoding` | Windows 上按 GBK 解码 | 一律写 `encoding="utf-8"` |
| `defaultdict` 以为不会建键 | 读取也创建了条目 | 用 `__missing__` 或先 `in` 判断 |
| `match` 里 `case SOME_NAME` | 被当成捕获变量，永远匹配 | 常量要带点：`case Color.RED` |

---

## 5.10 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | 9 节可运行示例，覆盖 5.1~5.8 全部结论 |
| `exercises.py` | 9 道练习，含自动断言 |
| `solutions.py` | 参考答案 + 为什么这么写 |

### 强烈建议的学法

1. 先跑 `demo.py` 看输出，**先猜结果再看**
2. 在 `demo_generator_basics()` 的第一行下断点，用调试器单步走，
   看「调用生成器函数」和「第一次 `next()`」之间到底发生了什么
3. 打开 REPL，写 `g = (x for x in range(3))`，
   然后 `next(g)` / `list(g)` / `list(g)` 各来一次，亲眼看那个「第二次是空的」
4. 然后做 `exercises.py`

---

## 5.11 延伸阅读

- [官方教程：迭代器与生成器](https://docs.python.org/zh-cn/3/tutorial/classes.html#iterators)
- [`itertools` 官方文档](https://docs.python.org/zh-cn/3/library/itertools.html)
  —— **页面上那份「itertools 配方」别跳过**，里面有大量现成的高级组合
- [`contextlib` 官方文档](https://docs.python.org/zh-cn/3/library/contextlib.html)
- [PEP 255 - 简单生成器](https://peps.python.org/pep-0255/) /
  [PEP 342 - 增强型生成器](https://peps.python.org/pep-0342/)
  —— 想知道 `send`/`throw` 为什么存在，读这两篇
- [PEP 634 - 结构化模式匹配](https://peps.python.org/pep-0634/)
- 《流畅的 Python》（第 2 版）第 17、18、21 章
  —— 第 17 章把迭代器讲了 40 页，是全书最扎实的一章
- [Python 3.14 新特性](https://docs.python.org/3/whatsnew/3.14.html)
