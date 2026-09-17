# 模块 02 · 数据结构精讲

> **目标**：从「会用 list 和 dict」升级到「知道它们底层是什么、什么时候会变慢」。
>
> 有算法基础的人最容易犯的错，是把 C 里的数据结构直觉直接搬到 Python：
> 用 `list` 当链表使、用 `list` 当哈希表使、用 `list` 当队列使。
> 这三种用法在 Python 里分别是 O(n)、O(n)、O(n)，性能差好几个数量级。
>
> 选对容器，比优化算法常数重要得多。

---

## 2.1 `list` 是动态数组，不是链表

CPython 的 `list` 底层就是一个**连续的指针数组**（`PyObject **ob_item`），
和 C++ 的 `std::vector`、Java 的 `ArrayList` 是同一个东西。

```
list 对象
+----------------+
| ob_refcnt      |
| ob_type        |
| ob_size   = 3  |  <- 逻辑长度 len()
| ob_item  ------|--+
+----------------+  |
                    v
              +-----+-----+-----+-----+-----+
              | ptr | ptr | ptr |  空  |  空 |   <- 已分配的槽位
              +--+--+--+--+--+--+-----+-----+
                 |     |     |
                 v     v     v
                 3     1     4      （各自是独立的 PyObject）
```

**关键点：存的是指针，不是值本身。**

这解释了两件事：

```python
a = [1, 2, 3]
b = a[0]          # b 指向 1 这个对象
a[0] = 99         # 只是把槽位里的指针换掉，原来的 1 不受影响

# 也解释了嵌套列表为什么是「共享」的
m = [[0] * 3] * 3
m[0][0] = 1
print(m)          # [[1, 0, 0], [1, 0, 0], [1, 0, 0]]  ← 三行是同一个列表！
```

### 扩容策略：为什么 `append` 是 O(1)

数组满了要扩容，CPython 不是「加一个扩一个」，而是**超量分配**。
下面是我在你机器上跑 `demo.py` 测出来的真实槽位数（每个槽位 8 字节，
列表头部固定 56 字节，`(sizeof - 56) // 8` 就是已分配的槽位数）：

| 追加到第几个元素时触发扩容 | 扩容后的槽位数 |
|:---:|:---:|
| 1 | 4 |
| 5 | 8 |
| 9 | 16 |
| 17 | 24 |
| 25 | 32 |
| 33 | 40 |
| 41 | 52 |
| 53 | 64 |
| 65 | 76 |

（对应 `listobject.c` 里的 `list_resize`，大致是
`newsize = size + size // 8 + 常数`，再向下取整到 4 的倍数。
**这个公式是实现细节，不要记它**，你只要知道「按比例多要一点」就够了。）

因为每次按**比例**增长，n 次 `append` 触发的总拷贝量是一个几何级数，
总和仍是 **O(n)**。摊到每次 `append` 就是 **O(1) 均摊**。

> **这就是为什么 `append` 快而 `insert(0, x)` 慢**：
> `append` 平均只写 1 个槽位；`insert(0, x)` 每次都要把后面
> 所有元素整体右移一格，是 **O(n)**。

### 队列的正确做法：`collections.deque`

```python
# 错：从头部弹出是 O(n)，n 次就是 O(n²)
queue = [1, 2, 3]
queue.pop(0)

# 对：deque 是双向链表 + 分块数组，两端操作都是 O(1)
from collections import deque
queue = deque([1, 2, 3])
queue.popleft()
```

`deque` 支持 `append`/`appendleft`/`pop`/`popleft`/`rotate` 全部 O(1)，
而且 `maxlen` 参数可以自动丢弃旧元素（做滑动窗口特别好用）。

### `list` 复杂度表

| 操作 | 复杂度 | 说明 |
|------|--------|------|
| `a[i]` / `a[i] = x` | O(1) | 下标直接寻址 |
| `a.append(x)` | O(1) 均摊 | 偶尔触发扩容 |
| `a.pop()` | O(1) | 从尾部弹 |
| `len(a)` | O(1) | 长度存在对象头里，不是数出来的 |
| `a.insert(0, x)` | **O(n)** | 整体右移 |
| `a.pop(0)` | **O(n)** | 整体左移 |
| `x in a` | **O(n)** | 线性扫描，除非有序才能二分 |
| `a.index(x)` | O(n) | 同上 |
| `a[i:j]` | O(j-i) | 要复制 |
| `a + b` | O(n+m) | 新建列表 |
| `a.sort()` | O(n log n) | Timsort |
| `a.reverse()` | O(n) | 就地反转 |
| `a.remove(x)` | O(n) | 先找再移 |

> **三个「一眼看出是 O(n²)」的 Python 反模式**：
> `for x in items: result.insert(0, x)`、`if x in big_list`（循环里）、
> `list.pop(0)`（循环里）。见到就换 `deque` / `set`。

---

## 2.2 `tuple`：不可变带来的三个好处

```python
t = (1, 2, 3)
t[0] = 9        # TypeError
```

什么时候该用 `tuple` 而不是 `list`：

1. **语义上是「记录」而不是「序列」**——比如坐标 `(x, y)`、数据库一行。
   长度固定，每个位置含义固定。
2. **可哈希**——只有不可变的 `tuple` 能当 `dict` 的键或放进 `set`（前提是元素也都可哈希）。
3. **稍微省内存**——`tuple` 不用预留扩容空间。

```python
import sys
sys.getsizeof([1, 2, 3])    # 88
sys.getsizeof((1, 2, 3))    # 64
```

**注意**：`tuple` 的不可变是**浅层**的。如果里面装着列表，列表本身还能改：

```python
t = (1, [2, 3])
t[1].append(4)      # 合法！t 变成 (1, [2, 3, 4])
t[1] = [9]          # TypeError，这才是 tuple 禁止的
```

`namedtuple` 是带字段名的 `tuple`，用来替代「返回多个值但看不清顺序」的写法：

```python
from collections import namedtuple
Point = namedtuple("Point", ["x", "y"])
p = Point(3, 4)
p.x, p[0], tuple(p)     # 3, 3, (3, 4)  —— 既能按名字访问，又完全兼容 tuple
```

> 更现代的替代品是 `typing.NamedTuple`（带类型注解）和
> `@dataclass(frozen=True)`（模块 04 讲）。新项目优先用后者。

---

## 2.3 切片：比你想象的强得多

```python
s = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

s[2:5]          # [2, 3, 4]          左闭右开
s[:3]           # [0, 1, 2]          省略起点 = 从头
s[7:]           # [7, 8, 9]          省略终点 = 到结尾
s[::2]          # [0, 2, 4, 6, 8]    步长 2
s[::-1]         # [9, 8, ..., 0]     反转（最常用的技巧）
s[-3:]          # [7, 8, 9]          最后三个
s[1:-1]         # 掐头去尾
```

**切片永远不会越界**，这是和 C 数组最大的区别：

```python
s[100:200]      # []      不报错，返回空
s[:1000]        # 整个列表
s[5:2]          # []      起点在终点后面也是空
s[100]          # IndexError  ← 单下标会报错
```

### 切片赋值：长度可以不同

```python
a = [0, 1, 2, 3, 4, 5]
a[1:4] = [9]              # [0, 9, 4, 5]        3 个换 1 个
a[1:1] = [7, 7]           # 在位置 1 插入（不删除任何东西）
del a[::2]                # 删除所有偶数下标位置
a[::-1] = a               # 原地反转
```

### 切片创建的是浅拷贝

```python
matrix = [[1, 2], [3, 4]]
copy_rows = matrix[:]        # 新列表，但子列表还是共享的
copy_rows[0].append(99)
print(matrix)                # [[1, 2, 99], [3, 4]]  ← 原数据被改了
```

---

## 2.4 解包：让代码短一半

```python
# 基础
x, y = 1, 2
x, y = y, x                  # 交换，不需要临时变量

# 星号收集（可以出现在任意位置）
first, *rest = [1, 2, 3, 4]      # first=1, rest=[2, 3, 4]
*init, last = [1, 2, 3, 4]       # init=[1, 2, 3], last=4
first, *mid, last = [1, 2, 3, 4] # first=1, mid=[2, 3], last=4
```

**注意 `rest` 永远是 `list`，哪怕只有一个元素或没有元素**——这是设计决定，不是 bug。

```python
# 嵌套解包
(a, b), c = (1, 2), 3

# 函数返回值
def min_max(nums):
    return min(nums), max(nums)      # 实际返回的是一个 tuple
lo, hi = min_max([3, 1, 4, 1, 5])

# 带星号的函数调用：把序列拆成位置参数
args = [1, 2, 3]
print(*args)                         # 等价于 print(1, 2, 3)

kwargs = {"sep": " | ", "end": "!\n"}
print(*args, **kwargs)

# 转置矩阵（本模块练习题会用到）
matrix = [[1, 2, 3], [4, 5, 6]]
list(zip(*matrix))                   # [(1, 4), (2, 5), (3, 6)]
```

> `print(*args)` 是 `print(args[0], args[1], ...)` 的缩写。
> `*` 的作用是**在函数调用时把可迭代对象展开成位置参数**，
> 和函数定义时的 `*args`（把位置参数收集成元组）方向正好相反。

---

## 2.5 `dict`：Python 最核心的数据结构

Python 里几乎所有东西都建立在 `dict` 之上——模块命名空间、类属性、
实例属性、关键字参数、`globals()`、`locals()` 全是字典。

### 底层：哈希表 + 开放寻址

CPython 3.6 之后用的是**紧凑字典**（compact dict），结构是：

```
indices:  [ -, -, 1, -, -, 0, -, 2 ]      稀疏的索引表（只存序号）
entries:  [ [hash, key, value],          稠密的实体表（按插入顺序排列）
            [hash, key, value],
            [hash, key, value] ]
```

两个直接结果：

1. **3.7 起 `dict` 保证按插入顺序遍历**（官方语言规范，不再是实现细节）
2. 内存比老版本省 20%~25%

### 平均 O(1)，最坏 O(n)

哈希表的查找是「算哈希 → 定位槽位 → 比较 key」。
只要哈希函数分布均匀且不冲突，就是 O(1)。

**最坏情况 O(n)** 什么时候发生？所有 key 的哈希值都相同。
这在实践中主要有两个来源：

1. **攻击**：Web 框架里拿用户输入当 key，攻击者可以构造大量哈希冲突的字符串来
   拖垮服务器（HashDoS）。CPython 从 3.3 起默认开启 **哈希随机化**
   （`PYTHONHASHSEED`），就是为了防这个。
2. **自己写坏的 `__hash__`**：`def __hash__(self): return 1` 会让所有实例
   挤在同一个槽位，字典退化成链表。

### 可哈希 = 不可变 + `__eq__`

`dict` 的 key 和 `set` 的元素必须**可哈希**（hashable）：

```python
hash(42)          # 42
hash("abc")       # 某个数
hash((1, 2))      # 可以
hash([1, 2])      # TypeError: unhashable type: 'list'
hash({1: 2})      # TypeError: unhashable type: 'dict'
```

规则：一个对象可哈希，当且仅当它的哈希值在其生命周期内不变，且
`a == b` 时必有 `hash(a) == hash(b)`。

**这就是为什么列表不能当 key 而元组可以**——如果列表可哈希，
你往字典里存了 `[1,2]` 当 key，之后 `append(3)`，它的哈希就变了，
字典再也找不到这个条目。

### 常用操作

```python
d = {"a": 1, "b": 2}

d["c"] = 3                      # 增 / 改
d.get("z")                      # None  —— 不存在不报错（最常用）
d.get("z", 0)                   # 0     —— 带默认值
d.setdefault("a", 99)           # 1     —— 存在就返回已有的，不存在才写入
d.setdefault("z", 99)           # 99    —— 顺手插入了 {"z": 99}

del d["a"]                      # KeyError 风险
d.pop("a", None)                # 安全删除
d.popitem()                     # 弹出最后一个（LIFO，3.7+）

d.keys() / d.values() / d.items()   # 视图对象，不是列表；会随字典变化
"a" in d                        # O(1)

d | {"x": 1}                    # 3.9+ 合并，返回新字典
d |= {"x": 1}                   # 3.9+ 就地合并
{**d, "x": 1}                   # 老写法（3.5+）

d.update(other)                 # 就地更新

sorted(d.items(), key=lambda kv: kv[1])   # 按值排序
```

> **`.keys()` / `.values()` / `.items()` 返回的是视图（view），不是列表**。
> 它不复制数据，而且会**实时反映**字典的变化。所以不能在遍历时改字典大小：
> ```python
> for k in list(d.keys()):     # 先转成 list 快照
>     if cond(k):
>         del d[k]
> ```

### 遍历时修改字典会炸

```python
for k in d:
    del d[k]        # RuntimeError: dictionary changed size during iteration
```

正确做法：先收集要删的 key，或者构造新字典。

```python
d = {k: v for k, v in d.items() if not should_remove(k)}   # 最 Pythonic
```

---

## 2.6 `set` 与 `frozenset`

`set` 就是**只有 key 没有 value 的字典**，底层同样是哈希表。

```python
s = {1, 2, 3}
s = set()                # 注意：{} 是空字典，不是空集合！

s.add(4)                 # O(1)
s.discard(99)            # 不存在也不报错（推荐）
s.remove(99)             # 不存在会 KeyError

a | b      # 并集 union
a & b      # 交集 intersection
a - b      # 差集 difference
a ^ b      # 对称差 symmetric_difference
a <= b     # 子集
a.isdisjoint(b)          # 无交集？
```

### `set` 最大的价值：把 O(n) 变成 O(1)

```python
# 慢：O(n) 每次，循环里就是 O(n²)
if word in big_list:

# 快：O(1) 每次
if word in big_set:
```

**这是 Python 里性价比最高的一处优化。** 只要你在循环里反复做成员判断，
而且数据不变，就把它转成 `set`。

```python
# 去重的两种写法
list(set(items))                    # 不保序
list(dict.fromkeys(items))          # 保序（推荐）
```

`frozenset` 是不可变的 `set`，因此**可哈希**，可以当字典的键或者放进另一个 `set`。

---

## 2.7 推导式

```python
[x * 2 for x in range(5)]                       # 列表推导
{x * 2 for x in range(5)}                       # 集合推导
{x: x * 2 for x in range(5)}                    # 字典推导
(x * 2 for x in range(5))                       # 生成器表达式（惰性，模块 05 细讲）

[x for x in nums if x % 2 == 0]                 # 带过滤
[x if x > 0 else -x for x in nums]              # 注意 if 的位置不同，含义完全不同
[x + y for x in "ab" for y in "12"]             # 多重循环（等价于嵌套 for）
''.join(c for c in s if c.isalpha())            # 生成器表达式省一个中间列表
```

**列表推导 vs 生成器表达式**：

| | 列表推导 `[...]` | 生成器表达式 `(...)` |
|---|---|---|
| 求值时机 | 立即 | 惰性，用到才算 |
| 内存 | O(n) 全存下 | O(1) |
| 可重复遍历 | 可以 | **只能一次** |

### 什么时候不该用推导式

```python
# 坏：逻辑已经复杂到看不懂了
result = [x.strip().lower() for x in lines if x.strip() and not x.startswith("#") and len(x.strip()) > 3]

# 好：退回普通循环
result = []
for line in lines:
    stripped = line.strip().lower()
    if not stripped or stripped.startswith("#"):
        continue
    if len(stripped) <= 3:
        continue
    result.append(stripped)
```

判据：**推导式超过一行，或者需要 `if/else` 嵌套时，就退回 for 循环。**

### 性能：推导式为什么快

```python
# 列表推导
[x * 2 for x in range(1000)]

# 等价的 for 循环
out = []
for x in range(1000):
    out.append(x * 2)
```

差别在于：推导式在字节码层面用的是 `LIST_APPEND` 这个专用指令，
不需要每轮都 `LOAD_FAST out` + `LOAD_METHOD append` + `CALL`。
实测通常快 30%~50%。这也是为什么 `for` 循环里 `result.append(...)`
可以换成推导式就换成推导式。

> 想要更快还可以用 `map`/`filter` 配合内置函数（C 实现），
> 但当变换逻辑是 lambda 时，lambda 的调用开销会吃掉这个优势。
> **实践建议：能用推导式就用推导式，够清楚了。**

---

## 2.8 排序

```python
nums.sort()                          # 就地排序，返回 None（不是返回排好的列表！）
sorted(nums)                         # 返回新列表，原列表不变

sorted(words, key=len)               # 按长度排
sorted(words, key=str.lower)         # 忽略大小写
sorted(people, key=lambda p: p.age)  # 按属性排
sorted(d.items(), key=lambda kv: kv[1], reverse=True)   # 按字典的值降序

import operator
sorted(people, key=operator.attrgetter("age"))          # 比 lambda 快一点
sorted(d.items(), key=operator.itemgetter(1))

import heapq
heapq.nlargest(3, nums)              # Top-K，不需要全排序，O(n log k)
heapq.nsmallest(3, nums)
```

### 排序是稳定的

Python 的 Timsort 是**稳定排序**：相等的元素保持原有相对顺序。这带来一个很有用的技巧：

```python
# 需求：先按分数降序，分数相同的按姓名升序
# 技巧：分两趟排，先排次要键，再排主要键（利用了稳定性）
records.sort(key=lambda r: r["name"])                 # 次要键，升序
records.sort(key=lambda r: r["score"], reverse=True)  # 主要键，降序

# 更直接的写法：让 key 返回一个元组，用负号实现「降序」
records.sort(key=lambda r: (-r["score"], r["name"]))
```

第二种写法更紧凑，但**有局限**：只有数值才能用负号取反。
字符串想降序必须用 `reverse=True`，而 `reverse` 会影响整个 key，
所以「数值降序 + 字符串升序」必须用元组那一招（数值取负，字符串不动）。

### `sort()` 返回 `None`

```python
nums = [3, 1, 2]
nums = nums.sort()          # nums 变成 None！经典 bug
nums = sorted(nums)         # 正确
```

这是 Python 的一个**刻意的设计约定**：就地修改的方法一律返回 `None`，
用来提醒你「这个操作是就地做的」。`list.append`、`list.reverse`、
`dict.update` 都是这样。

---

## 2.9 `collections`：标准库里的四件宝

### `Counter`：计数

```python
from collections import Counter

c = Counter("abracadabra")
# Counter({'a': 5, 'b': 2, 'r': 2, 'c': 1, 'd': 1})

c.most_common(2)            # [('a', 5), ('b', 2)]
c["不存在的键"]              # 0     ← 注意：不报 KeyError，返回 0
c.total()                   # 3.10+ 所有计数值之和
c + other                   # Counter 支持加法
```

`Counter` 的一个大坑：**访问不存在的 key 返回 0 且不会插入**，
所以 `if c[k] == 0` 无法区分「不存在」和「计数为 0」。要区分用 `k in c`。

### `defaultdict`：带默认值的字典

```python
from collections import defaultdict

groups = defaultdict(list)          # 默认值是 list()
for k, v in data:
    groups[k].append(v)             # 不用先判断 key 是否存在

counts = defaultdict(int)           # 默认值是 0
for ch in text:
    counts[ch] += 1

# 经典用法：构建邻接表
graph = defaultdict(list)
for u, v in edges:
    graph[u].append(v)
    graph[v].append(u)
```

`defaultdict` 的陷阱：**访问一个不存在的 key 会顺手把它插进去**。

```python
d = defaultdict(list)
if d["missing"]:        # 这一句就把 "missing" 加进去了，值是 []
    ...
len(d)                  # 1  ← 你只是想判断，却改了数据
```

要纯判断用 `k in d` 或 `d.get(k)`。

默认值必须是**可调用对象**：`defaultdict(list)` 而不是 `defaultdict([])`。
后者会抛 `TypeError: first argument must be callable or None`
（如果真允许传 `[]`，所有 key 会共享同一个列表——这正是可变默认参数陷阱的翻版）。

### `deque`：双端队列

```python
from collections import deque

dq = deque([1, 2, 3])
dq.append(4)            # 右进
dq.appendleft(0)        # 左进
dq.pop()                # 右出
dq.popleft()            # 左出
dq.rotate(1)            # 右旋 1 位：[3, 1, 2]（负数左旋）
dq.rotate(-1)           # 左旋

dq = deque(maxlen=3)    # 定长：满了以后自动从另一端丢弃
for i in range(5):
    dq.append(i)
# deque([2, 3, 4], maxlen=3)   ← 天然的滑动窗口
```

### `namedtuple` / `ChainMap` / `OrderedDict`

```python
from collections import namedtuple, ChainMap, OrderedDict

Point = namedtuple("Point", ["x", "y"])

# ChainMap：把多个字典串起来查找，写操作只作用于第一个
defaults = {"color": "red", "size": "M"}
user = {"color": "blue"}
cfg = ChainMap(user, defaults)
cfg["color"]         # 'blue'（先查 user）
cfg["size"]          # 'M'（user 里没有，落到 defaults）

# OrderedDict：3.7 之后普通 dict 也有序了，它现在主要用于两个场景：
#   1. move_to_end()  （LRU 缓存实现）
#   2. 需要「顺序敏感的比较」时（OrderedDict 的 == 要求顺序也相同）
```

---

## 2.10 拷贝：浅与深

```
a = [[1, 2], [3, 4]]

浅拷贝 b = a[:]             深拷贝 c = copy.deepcopy(a)

   a        b                 a        c
   |        |                 |        |
   v        v                 v        v
 [ ptr0, ptr1 ]              [ ptr0', ptr1' ]     ← 外层是新列表
   |      |                    |      |
   +--+---+                    |      |
      |                        |      |
      v                        v      v
   [[1,2], [3,4]]           [[1,2], [3,4]]   ← 深拷贝时内层也是新的
   ↑ 两者共享同一批子列表
```

```python
import copy

b = a[:]                  # 浅
b = list(a)               # 浅
b = a.copy()              # 浅（最清晰）
b = copy.copy(a)          # 浅

c = copy.deepcopy(a)      # 深（递归复制一切）
```

**什么时候需要深拷贝？** 当你要对嵌套结构做「独立修改」时。
深拷贝的开销和嵌套深度成正比，而且遇到循环引用要靠 `memo` 处理——
`deepcopy` 比你想的慢得多，能不用就不用。

**更好的办法**：避免共享可变状态。比如用不可变的 `tuple` 做内层，
或者每次构造新对象而不是拷贝。

---

## 2.11 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| `[[0]*3]*3` | 三行是同一个列表 | `[[0]*3 for _ in range(3)]` |
| `list.pop(0)` 循环 | O(n²) | `deque.popleft()` |
| `insert(0, x)` 循环 | O(n²) | `append` + `reverse`，或 `deque.appendleft` |
| `if x in big_list` 循环 | O(n²) | 先转 `set` |
| `nums = nums.sort()` | 得到 `None` | `nums.sort()` 或 `sorted(nums)` |
| 遍历 dict 时删除 | `RuntimeError` | 构造新 dict 或先取 `list(keys)` |
| `{}` 当空集合 | 得到空字典 | `set()` |
| `c[k] == 0` 判断 Counter | 分不清「没有」和「零」 | `k in c` |
| `defaultdict` 的读访问 | 凭空多出条目 | 用 `in` 或 `get` |
| `t = ([1],)` 里改列表 | 数据被改了 | 用 `deepcopy` 或别放可变对象 |
| 用了浅拷贝改嵌套 | 原数据被改 | `copy.deepcopy` |
| `list` 当 dict 的 key | `TypeError` | 用 `tuple` |

---

## 2.12 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | 底层结构可视化 + **真实的性能实测数据** |
| `exercises.py` | 10 道练习 |
| `solutions.py` | 参考答案 |

**这一模块请务必跑一遍 `demo.py` 的性能测试**——自己机器上测出来的
「`in list` 比 `in set` 慢 5000 倍」比任何文字都有说服力。

---

## 2.13 延伸阅读

- [Python 官方文档 TimeComplexity 页面](https://wiki.python.org/moin/TimeComplexity) —— 每个操作的复杂度权威表
- [CPython 源码 `Objects/listobject.c`](https://github.com/python/cpython/blob/main/Objects/listobject.c) —— 看 `list_resize` 函数
- 《流畅的 Python》第 2、3 章（序列）与第 5 章（数据类）
- [`collections` 官方文档](https://docs.python.org/zh-cn/3/library/collections.html)
