# 模块 03 · 函数与作用域

> **目标**：你在 C / Java 里已经会写函数了，所以这个模块**不讲「什么是函数」**。
> 它讲的是 Python 函数身上那些 C / Java 没有的东西：
> 参数的七种玩法、可变默认参数这个经典灾难、名字查找的 LEGB 规则、
> 函数是对象这件事带来的闭包与装饰器。
>
> 一句话概括本模块的价值：
> **装饰器、闭包、`functools` 这三样东西，是区分「会写 Python」和「会写 Python 库」的分水岭。**

---

## 3.1 参数机制全景

Python 的参数机制比 C / Java 复杂得多。先把全景图摆出来，再逐条拆。

```python
def f(a, b, /, c, d=4, *args, e, f_=6, **kwargs):
    ...
```

从左到右的每一段，规则都不一样：

| 位置 | 名字 | 调用方必须怎么传 |
|------|------|-----------------|
| `a, b` | positional-only（`/` 之前） | **只能**按位置传 |
| `c` | 普通参数 | 按位置或按关键字都行 |
| `d=4` | 带默认值 | 可以不传 |
| `*args` | 可变位置参数 | 多余的**位置**实参收集成 `tuple` |
| `e` | keyword-only（`*` 之后） | **只能**按关键字传 |
| `f_=6` | 带默认值的 keyword-only | 可以不传 |
| `**kwargs` | 可变关键字参数 | 多余的**关键字**实参收集成 `dict` |

记忆锚点：**`/` 左边的只能靠位置，`*` 右边的只能靠关键字。**
两个符号就像两堵墙，把参数分成三段。

### 位置参数与关键字参数

```python
def connect(host, port, timeout=30):
    return f"{host}:{port} timeout={timeout}"

connect("localhost", 8080)                       # 全位置
connect(host="localhost", port=8080)             # 全关键字
connect("localhost", port=8080)                  # 混用：位置必须在关键字前面
connect("localhost", 8080, timeout=60)
```

**规则：一旦用了关键字形式，后面的实参也必须用关键字形式。**

```python
connect(host="localhost", 8080)
# SyntaxError: positional argument follows keyword argument
```

注意这是**语法错误**，不是运行时错误——Python 在编译阶段就拦住了。

### 默认值：只在定义时求值一次

这是本模块第一节就要刻进脑子的一句话：

> **默认值表达式在 `def` 语句执行的那一刻求值一次，之后所有调用共享同一个对象。**

```python
import time

def log(msg, ts=time.time()):     # 灾难：ts 永远是「函数被定义的那一刻」
    print(ts, msg)

time.sleep(1)
log("a")     # 打印的是 1 秒前的时间戳
log("b")     # 和上面一模一样
```

如果你想要「每次调用时的当前时间」，正确写法是：

```python
def log(msg, ts=None):
    if ts is None:
        ts = time.time()          # 在函数体里求值 -> 每次调用都重新算
    print(ts, msg)
```

**用 `None` 当占位符，把真正的求值推迟到函数体内**，这是 Python 里最常用的一个模式。
下一节讲的「可变默认参数陷阱」是同一个原因导致的更严重的版本。

### `*args`：收集多余的位置实参

```python
def total(*args):
    print(type(args).__name__, args)     # tuple (1, 2, 3)
    return sum(args)

total(1, 2, 3)
total()              # 空元组，合法
```

`args` 这个名字是**约定**不是语法，写 `*numbers` 完全一样。
`*` 的作用是把「任意多个位置实参」打包成一个 `tuple`。

反过来，调用时用 `*` 是**解包**：

```python
nums = [1, 2, 3]
total(*nums)         # 等价于 total(1, 2, 3)
print(*nums)         # 等价于 print(1, 2, 3)
```

> **对比 C 的 `printf` / Java 的 `...`**：C 的可变参数没有类型信息也没有个数信息，
> 必须靠格式串自己推；Java 的 `Object...` 会装箱成数组。
> Python 的 `*args` 拿到的是一个真正的 `tuple`，`len()` 一下就知道有几个。

### `**kwargs`：收集多余的关键字实参

```python
def build(**kwargs):
    print(type(kwargs).__name__, kwargs)   # dict {'a': 1, 'b': 2}

build(a=1, b=2)
```

`kwargs` 是 `dict`，所以**键必须是字符串**（Python 的关键字只能是标识符）。

解包同样存在，但用的是 `**`：

```python
config = {"host": "localhost", "port": 8080}
connect(**config)        # 等价于 connect(host="localhost", port=8080)
```

`*` 和 `**` 同时出现在调用里是「转发参数」的标准写法：

```python
def wrapper(*args, **kwargs):
    return original(*args, **kwargs)     # 原样透传，一个都不丢
```

这段代码是**所有装饰器的骨架**，3.7 节会反复出现。

> **注意**：`*args` 和 `**kwargs` 会吃掉拼写错误的参数名。
> `connect(**{"hots": "localhost"})` 不会报错，只会让 `host` 用默认值——
> 如果你希望拼错就报错，就别用 `**kwargs`。

### keyword-only 参数（`*` 单独出现）

```python
def create_user(name, *, is_admin=False, send_mail=True):
    ...

create_user("张三", is_admin=True)     # 对
create_user("张三", True)              # TypeError！
```

**为什么需要它**：布尔参数是最典型的「传错了也能跑」的坑。

```python
def render(text, True, False)      # 哪个是哪个？读代码的人必须去翻定义
def render(text, wrap=True, escape=False)   # 一眼就懂，也传不错
```

这是 Python 的 API 设计哲学：**对自己好一点，别省那点打字量**。
标准库大量使用这个技巧，比如 `sorted(iterable, *, key=None, reverse=False)`。

一个裸的 `*` 后面如果**不写任何有默认值的参数**，那就是「强制关键字」：

```python
def f(a, *, b):     # b 必须用关键字传
    return a + b

f(1, b=2)           # 对
f(1, 2)             # TypeError: f() takes 1 positional argument but 2 were given
```

### positional-only 参数（`/`，Python 3.8+）

`/` 之前的参数**不允许**用关键字传：

```python
def greet(name, /, greeting="你好"):
    return f"{greeting}, {name}"

greet("张三")                  # 对
greet("张三", "早上好")         # 对
greet(name="张三")             # TypeError: got some positional-only arguments passed as keyword arguments
```

**为什么需要它**：库作者改参数名时不会破坏调用方。

```python
# 假设标准库第一版是：
def isclose(a, b, *, rel_tol=1e-9): ...

# 有人这样调用（能跑）：
isclose(a=1, b=2)

# 现在作者想把参数名改成 x, y（更清楚），如果参数不是 positional-only，
# 所有写成 isclose(a=..., b=...) 的代码全部炸掉。
# 加上 / 之后：
def isclose(x, y, /, *, rel_tol=1e-9): ...
# 参数名随便改，因为调用方根本无法用名字传。
```

`len(obj=...)` 报错就是这个原因——`len` 的参数是 positional-only 的。
你自己写业务代码时基本用不上 `/`，但读标准库时要知道它是什么意思。

### `functools.partial`：把参数「冻」住一部分

```python
import functools

def power(base, exp):
    return base ** exp

square = functools.partial(power, exp=2)
cube   = functools.partial(power, exp=3)

square(5)      # 25
cube(2)        # 8
```

它返回的不是函数，而是一个 `functools.partial` 对象，但**可以直接当函数调用**
（实现了 `__call__`，模块 04 会讲这是什么）。

**和 lambda 的分工**：

```python
square = functools.partial(power, exp=2)      # 想固定参数 -> partial
square = lambda x: power(x, exp=2)            # 想改造参数 -> lambda
```

`partial` 的优势在于：它能**保留原函数的元信息**（`__doc__` 之类可以通过
`square.func` 拿到原函数），而且可以直接用 `partial` 的 `.keywords` / `.args`
检查它固定了什么；lambda 是一团黑盒，调试器里只能看到一个 `<function <lambda>>`。

### 转成「看起来像函数」的调用方式

| 写法 | 实参形态 | 形参收到 |
|------|---------|---------|
| `f(1, 2)` | 位置 | 按顺序对号入座 |
| `f(a=1, b=2)` | 关键字 | 按名字对号入座 |
| `f(*seq)` | 解包序列 | 展开成多个位置实参 |
| `f(**d)` | 解包字典 | 展开成多个关键字实参 |
| `f(*seq, **d)` | 混合解包 | 转发场景的标准写法 |

> **一个常见的误解**：`*` 不是「指针」，`**` 也不是「字典指针」。
> 它们在**定义**处表示「收集」，在**调用**处表示「解包」。同一个符号，两个方向。

---

## 3.2 可变默认参数陷阱（本模块最重要的一节）

### 现象

```python
def add_item(item, box=[]):
    box.append(item)
    return box

print(add_item("a"))     # ['a']
print(add_item("b"))     # ['a', 'b']   <- 见鬼了
print(add_item("c"))     # ['a', 'b', 'c']
```

没有传入 `box` 的时候，三次调用**操作的是同一个列表对象**。

### 原因

回到 3.1 节那句话：**默认值在 `def` 执行时求值一次，结果保存在函数对象里。**

```python
def add_item(item, box=[]):
    box.append(item)
    return box

add_item.__defaults__        # (['a', 'b', 'c'],)  <- 可以直接看到！
add_item.__defaults__[0] is add_item.__defaults__[0]   # True，一直是同一个列表
```

`def` 语句执行时，Python 创建了一个空列表，把它的**引用**塞进
`add_item.__defaults__`。之后每次调用没给 `box` 时，形参 `box` 就被绑定到
这**同一个**列表上。你在函数里 `append` 的正是它。

这不是 bug，是**默认值只在定义时求值一次**这条规则的必然推论。
不可变的默认值（数字、字符串、`None`）没事，因为「改」它们只会产生新对象；
可变的（`list` / `dict` / `set` / 自定义实例）就全完了。

**`__defaults__` 是个好东西**：怀疑某个函数有默认值问题时，
在调试器里求值一下 `f.__defaults__` / `f.__kwdefaults__`，一眼就能看到那个
被共享的对象。`__kwdefaults__` 是 keyword-only 参数的默认值。

### 正解：用 `None` 当哨兵

```python
def add_item(item, box=None):
    if box is None:
        box = []             # 每次调用都新建一个
    box.append(item)
    return box
```

**为什么用 `None` 而不是 `[]`**：`None` 是单例（模块 01 讲过），
不可能被调用方「当成一个真实的空列表」传进来混淆；而且
`if box is None` 用 `is` 比较，O(1) 且不受 `__eq__` 干扰。

有一种更漂亮但不常用的写法，用默认参数来**固化循环变量**
（3.6 节会看到），以及用 `functools.partial` 来固化参数：

```python
from functools import partial

send_mail = partial(send, retries=3)    # 这是「固化」，不是「共享可变状态」
```

区别在于：`partial` 固化的是**不可变的值**（3 永远不会变成 4），
而 `box=[]` 共享的是一个**可以被改的对象**。共享不可变对象永远安全。

### 陷阱的变体

**变体一：默认值是函数调用的结果**

```python
def f(x, cache={}):      # 等价于上面的问题，换了个容器而已
    ...
```

**变体二：写在类里（模块 04 会详细讲）**

```python
class Basket:
    def __init__(self, items=[]):     # 所有实例共享同一个列表！
        self.items = items

a, b = Basket(), Basket()
a.items.append("苹果")
print(b.items)      # ['苹果']  <- b 也跟着变了
```

**变体三：你以为别人不会传可变对象进去**

```python
def process(data, seen=set()):
    ...
```

哪怕函数体里只「读」这个 `seen`，只要它会被写，就会跨调用累积。

### 一条可以直接背下来的规则

> **只要默认值是可变对象，就写成 `None`，然后在函数体开头判空并新建。**
> 没有例外。

---

## 3.3 参数传递：call by object reference

模块 01 提过一句，这里把它讲透，因为它是理解「为什么我的列表被改了」的钥匙。

### 先排除两个错误答案

C 程序员会说「Python 是引用传递」，Java 程序员会说「对象是引用传递，基本类型是值传递」。
**两种说法都不对**，或者说都不完整。

Python 只有一种传递方式，官方叫法有几个：

- **call by object reference**（传对象引用）
- **call by sharing**（共享传参，这个说法最准确）
- 也有人叫 **call by assignment**（传参就是一次赋值）

### 准确的说法：传参就是一次赋值

```python
def f(x):
    ...

f(data)
```

这次调用做了什么？**等价于 `x = data`**——仅此而已。
就是模块 01 讲的「名字绑定」：把形参这个名字，绑定到实参所指的那个对象上。

于是所有结论都能推出来了：

```python
def mutate(lst):
    lst.append(99)       # 改对象内容 -> 调用方看得见

def rebind(lst):
    lst = [99]           # 重新绑定局部名字 -> 调用方看不见

data = [1, 2]
mutate(data)
print(data)              # [1, 2, 99]

data = [1, 2]
rebind(data)
print(data)              # [1, 2]  <- 没变
```

**规律一句话**：函数内**改内容**会影响调用方，**重新绑定名字**不会。

### 为什么「不可变对象按值、可变对象按引用」这个口诀是错的

```python
def f(t):
    t += (3,)           # 元组不可变
    return t

tup = (1, 2)
f(tup)
print(tup)              # (1, 2)  <- 没变

def g(lst):
    lst += [3]          # 列表可变
    return lst

lst = [1, 2]
g(lst)
print(lst)              # [1, 2, 3]  <- 变了
```

看起来符合口诀。但下面这个例子会把它打穿：

```python
def f(t):
    t += [3]            # 对元组里的列表做 +=
    ...
```

再看一个真正的反例——**把不可变对象传进去，一样可以「改变」调用方的世界**：

```python
def f(s):
    s = s + "!"          # 重新绑定，调用方看不见
    return s

def g(lst):
    lst = lst + [3]      # 重新绑定，调用方看不见（注意是 + 不是 +=）
    return lst
```

结论：**决定「调用方看不看得见」的，不是对象可不可变，
而是函数内部做的是「改内容」还是「重新绑定」。**

口诀之所以「看起来对」，只是因为可变对象**能够**被改内容，
不可变对象**只能**被重新绑定而已——是巧合，不是因果。

### 实战检查表

| 你想做的 | 会不会影响调用方 | 说明 |
|---------|----------------|------|
| `lst.append(x)` | 会 | 改内容 |
| `lst[0] = x` | 会 | 改内容 |
| `lst += [x]`（list） | 会 | 就地修改 |
| `lst = lst + [x]` | 不会 | 新建对象后重新绑定 |
| `lst = []` | 不会 | 重新绑定 |
| `d.update(...)` | 会 | 改内容 |
| `n += 1`（int） | 不会 | int 不可变，只能重新绑定 |

**如果函数不应该修改调用方的数据**，就在函数开头复制一份：

```python
def normalize(data):
    data = list(data)        # 复制，后面随便改
    data.sort()
    return data
```

或者用更 Python 的表达：干脆不改，直接返回新的（这也是 `sorted()` 和
`list.sort()` 的区别——前者返回新列表，后者就地改并返回 `None`）。

> **顺带记住**：一个函数如果**就地修改**，就应该返回 `None`；
> 如果**返回新对象**，就不要顺手改原对象。
> 标准库严格遵守这条（`list.sort()` 返回 `None`、`sorted()` 不改原列表），
> 你的代码也照做，调用方就不会猜错。

---

## 3.4 作用域：LEGB 规则与 `global` / `nonlocal`

### 名字查找的四个圈

Python 在函数里遇到一个名字时，按固定的顺序去找：

```
L  Local        当前函数内部
E  Enclosing    外层函数（嵌套定义时）
G  Global       当前模块
B  Builtins     内置命名空间（len、print 之类）
```

**从内往外，找到就停**，找不到就 `NameError`。

```python
x = "global"

def outer():
    x = "enclosing"

    def inner():
        x = "local"
        print(x)       # local   <- L 命中，后面的圈根本不去看

    inner()

outer()
```

把 `inner` 里那行 `x = "local"` 删掉，打印的就是 `enclosing`（E 命中）；
再把 `outer` 里的 `x = "enclosing"` 也删掉，打印的才是 `global`。

### 关键：作用域是**编译期**决定的，不是运行期

这一点和 C / Java 完全不同，也是所有反直觉行为的根源。

```python
G = 1

def f():
    print(G)      # 这里会报错
    G = 2

f()
# UnboundLocalError: cannot access local variable 'G' where it is not associated with a value
```

**函数里明明有全局的 `G`，为什么读不到？**

因为 Python 编译 `f` 的函数体时，看到 `G = 2` 这条赋值语句，就**决定**
`G` 是这个函数的**局部名字**（写进了 `co_varnames`，用的字节码是 `STORE_FAST`）。
这个决定在编译期就做完了，跟运行时有没有执行到那行无关。

于是运行时 `print(G)` 执行的时候，Python 认为「你要的是局部变量 `G`」，
而局部 `G` 还没被赋值，所以报 `UnboundLocalError`
（注意：不是 `NameError`，这个区别本身就是「它认为这是局部变量」的证据）。

**Python 没有变量声明语法**——`x = 1` 这一条语句同时完成了「声明」和「赋值」。
这就是为什么「函数内不能直接改全局变量」：不是不允许，
而是**只要你对它赋值，它就变成局部的了**，和全局那个已经不是同一个名字。

> 对比 C：C 里 `int x; x = 2;` 声明和赋值是分开的，所以不会出现这种歧义。
> Java 里局部变量遮蔽字段要靠 `this.x` 区分。Python 用「赋值即声明」换来了简洁，
> 代价就是这个 `UnboundLocalError` 坑。

### `global`：明确声明「我要的是模块级的那个」

```python
counter = 0

def bump():
    global counter      # 声明：接下来的 counter 指模块级那个
    counter += 1        # 没有这行 global 就是 UnboundLocalError
```

`global` 只是**声明**，不创建变量。

**但绝大多数情况下你不该用 `global`。** 它的问题：

1. 函数不再是纯的：同样的输入可能得到不同结果，测试和并发都变难
2. 调试困难：谁改了这个变量？得全文件搜 `global`
3. 单测没法隔离：跑一次测试就污染了全局状态

**更好的做法**是用返回值、传参、或者干脆用一个类来装状态：

```python
# 不好
total = 0
def add(n):
    global total
    total += n

# 好
def add(total, n):
    return total + n

# 也好（状态多了以后）
class Counter:
    def __init__(self):
        self.total = 0
    def add(self, n):
        self.total += n
```

**唯一合理的 `global` 场景**：模块级的常量缓存 / 开关，而且必须写得很显眼。
真正需要可变全局状态时，优先用 `functools.lru_cache`（3.8 节）或者类。

### `nonlocal`：改外层函数的名字

`global` 管的是「模块级」，`nonlocal` 管的是「外层函数」：

```python
def make_counter():
    count = 0

    def bump():
        nonlocal count      # 声明：count 是外层函数的，不是我的局部变量
        count += 1
        return count

    return bump
```

去掉 `nonlocal count`，`count += 1` 会让 `count` 变成 `bump` 的局部变量，
于是又会 `UnboundLocalError`——和 `global` 是同一个道理。

**三个关键字对比**：

| 关键字 | 作用 | 什么时候必须写 |
|--------|------|--------------|
| 不写 | 只读外层/全局 -> 能读 | 只读时 |
| `global x` | 写模块级的 `x` | 在函数里给模块级变量**赋值**时 |
| `nonlocal x` | 写外层函数的 `x` | 在嵌套函数里给外层函数变量**赋值**时 |

`nonlocal` 只能用在**嵌套函数**里；在模块顶层用会直接 `SyntaxError`。
如果外层函数根本没有这个名字，也会 `SyntaxError`（编译期就报）。

### 一个容易搞混的点：`for` / `if` 不产生作用域

```python
for i in range(3):
    pass
print(i)          # 2  <- 循环变量泄漏到外面了！

if True:
    y = 1
print(y)          # 1  <- 一样
```

Python 的**代码块**（`if` / `for` / `while` / `try`）不构成作用域，
只有**函数**、**类**、**模块**、**推导式**才构成。

```python
squares = [x * x for x in range(5)]
print(x)          # NameError  <- 推导式里的 x 不外泄
```

> 对比 Java：Java 的 `for (int i = ...)` 里 `i` 只活在循环里。
> 从 Java 转过来的人会觉得 Python 这个设计很脏——确实有点，
> 所以「短函数 + 变量名写清楚」在 Python 里格外重要。
> 另外 `if`/`for` 不产生作用域意味着**没有块级作用域**，
> 也就没有 Java 那种「内层块遮蔽外层同名变量」的问题。

---

## 3.5 一等函数：函数是对象

### 一等公民是什么意思

在 Python 里，函数是**对象**，和 `42`、`"abc"` 没有任何地位差别：

- 可以赋值给变量
- 可以放进列表 / 字典 / 集合
- 可以作为参数传给别人
- 可以作为返回值
- 可以有属性（`f.attr = 1` 是合法的！）

```python
def shout(text):
    return text.upper() + "!"

yell = shout            # 注意：没有括号，这是「另一个名字」，不是调用
yell("hi")              # 'HI!'
type(shout)             # <class 'function'>
shout.__name__          # 'shout'
shout.__doc__           # 函数的文档字符串
shout.__code__          # 字节码对象，模块 01 的 dis 用过
```

**在 C 里**，只有函数指针能这么干，而且不能带状态、不能有属性、不能有闭包。
**在 Java 里**，3.8 之前得写匿名内部类；之后有方法引用和 lambda，
但底层仍然是「函数式接口的实例」，不能像普通对象那样随意操作。

### 把函数当参数：高阶函数

```python
def apply_twice(func, value):
    return func(func(value))

apply_twice(str.upper, "ab")             # 'AB'
apply_twice(lambda n: n + 1, 5)          # 7
```

内置的 `map` / `filter` / `sorted` 全都是这么工作的。

### `map` / `filter`

```python
nums = [1, 2, 3, 4]

list(map(str, nums))               # ['1', '2', '3', '4']
list(map(lambda n: n * 2, nums))   # [2, 4, 6, 8]

list(filter(lambda n: n % 2 == 0, nums))   # [2, 4]
list(filter(None, [0, 1, "", "x", None]))  # [1, 'x']   None 表示「用真值判断」
```

**`map` / `filter` 返回的是迭代器，不是列表**——这是模块 05 的主题，
现在只要记住「想看内容得 `list()` 一下」就行。而且迭代器只能用一次：

```python
squares = map(lambda n: n * n, nums)
list(squares)     # [1, 4, 9, 16]
list(squares)     # []          <- 已经用完了
```

> **实践建议**：在 Python 里 `map` / `filter` 通常**不如推导式好读**。
> 上面这几行更 Python 的写法是：
> ```python
> [str(n) for n in nums]
> [n * 2 for n in nums]
> [n for n in nums if n % 2 == 0]
> ```
> 但**有一个场景 `map` 更好**：函数已经存在，不需要包装。
> `list(map(str.strip, lines))` 比 `[line.strip() for line in lines]` 更短，
> 而且省掉了一个 lambda。

### `sorted(key=)`：本模块最有用的一个参数

```python
words = ["banana", "Apple", "cherry"]

sorted(words)                          # ['Apple', 'banana', 'cherry']  按码点，大写在前
sorted(words, key=str.lower)           # ['Apple', 'banana', 'cherry']  忽略大小写
sorted(words, key=len)                 # ['Apple', 'banana', 'cherry']  按长度
sorted(words, key=len, reverse=True)   # ['banana', 'cherry', 'Apple']
```

**`key` 是一个「打分函数」**：`sorted` 对它拿到的每个元素调用一次 `key(element)`，
拿到一个分数，然后**按分数排序**，最后返回**原始元素**。

```python
students = [("张三", 85), ("李四", 92), ("王五", 85)]

sorted(students, key=lambda t: t[1])              # 按分数升序
sorted(students, key=lambda t: t[1], reverse=True)
```

**为什么是 `key` 而不是 C 的 `cmp`（比较函数）**：

C 的 `qsort` 收的是一个「比较两个元素」的函数，所以排序过程中比较函数
会被调用 O(n log n) 次。`key` 只需要对每个元素调用**一次**（O(n) 次），
之后排序比较的是现成的分数。

```python
# key 版本：len(x) 只算 n 次
sorted(words, key=len)

# 如果只有 cmp，就得这样，len(x) 要算 n log n 次
sorted(words, key=functools.cmp_to_key(lambda a, b: len(a) - len(b)))
```

`functools.cmp_to_key` 就是给「只有 cmp 思维」的场景准备的逃生舱，
但**新代码一律用 `key`**。

**多级排序**：让 `key` 返回一个元组，元组按元素顺序比较。

```python
# 先按分数降序，分数相同再按名字升序
sorted(students, key=lambda t: (-t[1], t[0]))
```

**负号是常用技巧**：`-t[1]` 把「降序」变成「升序」，因为元组比较是从左到右的。
（数字能取负，字符串不能，字符串要降序只能排序两次或者自己包一层。）

**排序是稳定的**（Timsort）：分数相同的元素保持原有相对顺序。
所以「先按次要键排一次，再按主要键排一次」也能实现多级排序，
利用的正是稳定性。

### `lambda` 的边界

`lambda` 是「能写成一个表达式的匿名函数」。

```python
lambda a, b: a + b
```

它和 `def` 唯一的区别是**只能放一个表达式**，所以：

**不能写语句**：

```python
lambda x: print(x)                    # 合法！print 是表达式（函数调用）
lambda x: if x > 0: return x          # SyntaxError
lambda x: return x                    # SyntaxError: return 只能在语句里
lambda x: y = x                       # SyntaxError: 赋值是语句
lambda x: (y := x)                    # 合法（海象运算符是表达式），但可读性差
```

**不能有注解**：

```python
lambda x: int: x                       # SyntaxError
f = lambda x: x                        # 无法给参数或返回值写类型注解
```

**不能有文档字符串**：

```python
def f(x):
    """把 x 转成字符串。"""      # __doc__ 有内容
    return str(x)

g = lambda x: str(x)               # g.__doc__ 是 None
```

**所以 lambda 的适用边界就一句话**：

> **短的、一次性的、不需要名字的回调用 lambda；其余一律用 `def`。**

需要多行、需要注解、需要文档、需要被调试器认出来——都老老实实写 `def`。
一个 `lambda` 如果长到要折行，它就该变成 `def`。

> **一个额外事实**：`lambda` 在调试器里的名字是 `<lambda>`，
> 在 traceback 里也一样。生产代码里给 key 函数起个名字，
> 出问题时调用栈会直接告诉你「哦，是 `by_score` 挂了」。

### 函数可以有属性

因为函数是对象，你可以随便往上挂东西：

```python
def fetch(url):
    ...

fetch.calls = 0          # 完全合法
fetch.calls += 1
```

**这是装饰器不用额外容器就能记录状态的原因**（3.7 节会用到）。

---

## 3.6 闭包

### 定义

闭包 = **函数** + **它定义时所在的那个环境**。

```python
def make_multiplier(factor):
    def multiply(x):
        return x * factor        # factor 不是 multiply 的参数，也不是它的局部变量
    return multiply

double = make_multiplier(2)
triple = make_multiplier(3)

double(5)     # 10
triple(5)     # 15
```

`make_multiplier(2)` 已经**返回**了，它的栈帧理论上应该没了。
但 `multiply` 之后还能读到 `factor`——因为 `factor` 被
**存进了 `multiply` 的闭包里**，跟着函数对象一起活着。

### 看得见的闭包：`__closure__`

```python
double = make_multiplier(2)

double.__closure__            # (<cell at 0x...: int object at 0x...>,)
double.__closure__[0].cell_contents    # 2
double.__code__.co_freevars   # ('factor',)   <- co_freevars 里的就是自由变量
```

**术语对照**：

| 名字 | 含义 |
|------|------|
| **自由变量**（free variable） | 函数里用到、但既不是参数也不是局部变量的名字 |
| **cell** | 存放自由变量的容器，一个变量一个 cell |
| `co_freevars` | 这个函数有哪些自由变量 |
| `__closure__` | 与 `co_freevars` 一一对应的 cell 元组 |
| `co_cellvars` | **外层**函数里「被内层用到」的变量（在外层看来它们是 cell） |

```python
make_multiplier.__code__.co_cellvars    # ('factor',)  <- 在 make_multiplier 眼里，factor 是 cell
```

**为什么要用 cell 而不是直接复制值**？

```python
def make_counter():
    count = 0
    def bump():
        nonlocal count        # 如果有多个内层函数，它们必须共享同一个 count
        count += 1
        return count
    def reset():
        nonlocal count
        count = 0
    return bump, reset
```

如果内层每个函数各拿一份 `count` 的副本，`bump` 加完 `reset` 就重置不了。
**cell 是共享的存储位置**，内层函数和外层函数看到的是同一个格子。
这也解释了为什么 `nonlocal` 是必要的——它告诉编译器「这个名字是 cell，
走 `LOAD_DEREF` 而不是 `LOAD_FAST`」。

### 反直觉的地方：`count += 1` 为什么不能自动生效

```python
def make_counter():
    count = 0
    def bump():
        count += 1        # UnboundLocalError！
        return count
    return bump
```

原因和 3.4 节讲 `global` 时**一模一样**：编译 `bump` 时看到 `count = ...`，
就认定 `count` 是 `bump` 的局部变量。要打破这个判断，必须显式写 `nonlocal`。

注意：**只读**外层变量是不需要 `nonlocal` 的。

```python
def make_adder(n):
    def add(x):
        return x + n       # 只读 n，不需要 nonlocal
    return add
```

**判断规则**：内层函数里**只读**外层变量 -> 不用写；
一旦有 `x = ...` / `x += ...` 这种**绑定**行为 -> 必须 `nonlocal`。

### 陷阱：循环里的 lambda（延迟绑定 / late binding）

这是闭包最著名的坑：

```python
funcs = [lambda x: x * i for i in range(4)]
[f(10) for f in funcs]      # [30, 30, 30, 30]   <- 全都是 3，不是 [0, 10, 20, 30]
```

**为什么**：闭包捕获的是**变量本身（那个 cell）**，不是**变量当时的值**。
四个 lambda 共享同一个 cell，循环结束后这个 cell 里的 `i` 是 `3`。
调用的时候才去 cell 里取值，取到的自然全是 3。

这叫**延迟绑定**：名字的解析发生在**函数被调用**时，而不是被定义时。

**修复方法一：用默认参数固化**（最常用）

```python
funcs = [lambda x, i=i: x * i for i in range(4)]
[f(10) for f in funcs]      # [0, 10, 20, 30]
```

**为什么这个能行**：默认值在 `def`（这里是 `lambda`）**定义时**求值一次，
那时 `i` 正好是当次循环的值，于是被固化进了 `__defaults__`。
注意这**利用了 3.2 节那个「陷阱」的同一个机制**——同样的规则，
用在不可变的 int 上就成了救星，用在可变的 list 上就成了灾难。
区别还是那句话：**共享不可变对象是安全的，共享可变对象不是。**

**修复方法二：再包一层函数（工厂）**

```python
def make_mul(i):
    return lambda x: x * i

funcs = [make_mul(i) for i in range(4)]
[f(10) for f in funcs]      # [0, 10, 20, 30]
```

每次调用 `make_mul` 都会创建一个**新的作用域**，`i` 是那个作用域的**参数**，
所以每个 lambda 的 cell 是独立的。

**方法三：`functools.partial`**

```python
from functools import partial

def mul(i, x):
    return x * i

funcs = [partial(mul, i) for i in range(4)]
[f(10) for f in funcs]      # [0, 10, 20, 30]
```

**哪种最好**：方法二最清楚（还顺便给函数起了名字），方法一最短，
方法三在需要复用已有函数时最自然。**不要**用方法一去写带可变默认值的函数，
那会退回 3.2 节的陷阱。

### 闭包的状态是「每个闭包实例一份」

```python
c1 = make_counter()
c2 = make_counter()
c1()     # 1
c1()     # 2
c2()     # 1   <- 独立的，不受 c1 影响
```

**这一点让闭包可以替代「只有一个方法的类」**。实际上，下面两段代码等价：

```python
def make_counter():
    count = 0
    def bump():
        nonlocal count
        count += 1
        return count
    return bump

class Counter:
    def __init__(self):
        self.count = 0
    def bump(self):
        self.count += 1
        return self.count
```

闭包版本更短，类版本可以被继承、被检查 `isinstance`、能被序列化。
**状态只有一个、方法也只有一个的时候用闭包，其余用类**（模块 04 会讲
`__call__`，那时两者就彻底统一了）。

### 闭包的内存代价

```python
def leak():
    big = [0] * 10_000_000        # 80MB
    def peek():
        return big[0]
    return peek                   # big 不会因为 leak() 返回而被回收
```

**只要闭包活着，它捕获的整个对象就活着**。这是真实项目里内存泄漏的常见来源，
尤其是「回调函数捕获了大对象，而回调被注册到全局事件循环里」这种模式。

想验证的话，用 `sys.getrefcount` 或者 `gc` 模块；想避免的话，
在返回闭包前先算好需要的值，只捕获那个小值。

---

## 3.7 装饰器

### 装饰器就是「接收函数、返回函数」的高阶函数

先看清楚 `@` 只是语法糖：

```python
@my_decorator
def target():
    ...

# 完全等价于：
def target():
    ...
target = my_decorator(target)
```

**记住这一点，装饰器就没有魔法了**：它和 3.5 节讲的「把函数当参数」是同一件事。

### 手写一个 `@timer`

```python
import functools
import time

def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)        # 原样转发，返回值不能丢
        finally:
            elapsed = time.perf_counter() - start
            print(f"{func.__name__} 耗时 {elapsed:.4f}s")
    return wrapper


@timer
def slow_sum(n):
    """累加 0..n-1。"""
    return sum(range(n))

slow_sum(1_000_000)

print(slow_sum.__name__)      # slow_sum        <- 靠 functools.wraps
print(slow_sum.__doc__)       # 累加 0..n-1。
```

几个必须注意的点：

**① `*args, **kwargs` 是不可省的。** 不写它们，被装饰的函数就只能收固定参数了：

```python
def wrapper():                # 坏
    return func()
```

**② 必须 `return` 原函数的返回值。** 忘了 `return` 的话，
`slow_sum(10)` 会返回 `None`，而且不报错——这是最常见的装饰器 bug。

**③ `try/finally` 保证异常时也能计时**，而且异常会正常向上传播
（`finally` 里不写 `return` 就不会吞掉异常）。

**④ 用 `time.perf_counter()` 而不是 `time.time()`**：
前者是单调时钟，不受系统时间被调整的影响，专门用来测耗时。

### `functools.wraps` 到底保住了什么

不写 `@functools.wraps(func)` 会丢掉这些：

```python
def naive_timer(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)
    return wrapper

@naive_timer
def documented(x: int) -> int:
    """原始文档字符串。"""
    return x

documented.__name__       # 'wrapper'    <- 名字丢了，调试器里全是 wrapper
documented.__doc__        # None         <- 文档丢了，help() 是空的
documented.__qualname__   # 'naive_timer.<locals>.wrapper'
inspect.signature(documented)     # (*args, **kwargs)  <- 签名丢了，IDE 无法提示参数
hasattr(documented, '__wrapped__')  # False      <- 拿不到原函数了，无法「拆包装」
```

加上 `@functools.wraps(func)` 之后：

```python
documented.__name__                # 'documented'
documented.__doc__                 # '原始文档字符串。'
inspect.signature(documented)      # (x: int) -> int    <- IDE 和框架都能看到真实签名
documented.__wrapped__             # <function documented at 0x...>  原函数本体
documented.__wrapped__(5)          # 可以直接调用没被包装的版本
```

**`functools.wraps` 做的事情**：把 `func` 的 `__module__` / `__name__` /
`__qualname__` / `__doc__` / `__dict__` 拷到 `wrapper` 上，
更新 `wrapper.__dict__`，并设置 `wrapper.__wrapped__ = func`。

**为什么生产代码必须写**：

1. **日志和监控**：你记的是 `func.__name__`，不写 wraps 的话日志里全是
   `wrapper`，等于没记
2. **框架靠名字派发**：Flask 的路由、pytest 的测试发现，都靠 `__name__`
3. **IDE 提示**：VS Code / Pylance 靠 `__wrapped__` 还原签名，不写的话参数提示全没了
4. **`__wrapped__` 是「拆包装」的标准入口**，`inspect.signature` 就是靠它穿透装饰器的

**一句话：写装饰器，`@functools.wraps(func)` 是标配，没有例外。**

### 装饰器的执行时机

```python
def trace(func):
    print(f"装饰器作用于 {func.__name__}")     # 这一行在「定义时」执行
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        print(f"调用 {func.__name__}")         # 这一行在「调用时」执行
        return func(*args, **kwargs)
    return wrapper
```

运行上面的 `trace` 定义后**立刻**会打印「装饰器作用于 ...」——
因为 `@` 那一行是模块加载时执行的普通函数调用。
**装饰器只在定义时运行一次**，`wrapper` 内部才在每次调用时运行。

这解释了一些看起来很奇怪的报错：**装饰器写错了，程序连启动都启动不了**
（import 阶段就炸），而不是等到调用那个函数才炸。

### 带参数的装饰器：三层嵌套

`@retry(3)` 和 `@timer` 的区别在于——`@retry(3)` 是**先调用 `retry(3)`
拿到一个装饰器**，再用它去装饰：

```python
@retry(3)
def f(): ...

# 等价于：
def f(): ...
f = retry(3)(f)
```

所以 `retry` 必须返回一个装饰器，结构就变成了三层：

```python
def retry(times, exceptions=(Exception,)):
    def decorator(func):                        # 第二层：真正的装饰器
        @functools.wraps(func)
        def wrapper(*args, **kwargs):           # 第三层：包装函数
            last = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    last = exc
            raise last                          # 重试用完还是失败，抛出去
        return wrapper
    return decorator
```

**三层结构一定要记牢**：

| 层 | 参数 | 返回 | 什么时候执行 |
|----|------|------|------------|
| 最外层 `retry` | 装饰器的配置（`times`） | `decorator` | `@retry(3)` 求值时，一次 |
| 中间层 `decorator` | 被装饰的函数 `func` | `wrapper` | 装饰时，一次 |
| 最内层 `wrapper` | 调用时的实参 | 原函数的返回值 | 每次调用 |

**忘记 `raise` 的后果**：重试用完了却不抛异常，函数会「静默失败」返回 `None`。
这比不重试还糟糕，因为调用方拿不到任何错误信号。

### 一个实用的增强版 `@timer`：支持 `@timer` 和 `@timer("说明")` 两种用法

```python
def timer(func=None, *, label=None):
    """既能 @timer，也能 @timer(label="xxx")。"""
    if func is None:                      # 说明是带参数调用：@timer(label=...)
        return lambda f: timer(f, label=label)
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        ...
    return wrapper
```

**为什么需要这个技巧**：`@timer` 时第一个位置参数就是被装饰的函数，
`@timer(...)` 时它是一个配置值。用 `func is None` 就能区分——因为
「被装饰的函数」永远不可能是 `None`。

标准库里的 `dataclasses.dataclass`、`functools.lru_cache` 都支持这种双形态，
它们的实现也是这个套路。

### 装饰器的顺序：从下往上

```python
@a
@b
def f(): ...

# 等价于 f = a(b(f))
```

**离函数最近的先执行**。所以 `@b` 先包装 `f`，`@a` 再包装 `b` 的产物。
调用时顺序相反：`a` 的 wrapper 先跑，再进 `b` 的 wrapper，最后才是 `f`。

常见的固定搭配有讲究：

```python
@functools.lru_cache(maxsize=None)      # 缓存应该在「最外层」
@timer                                  # 这样计时的是未命中缓存那次
def fib(n): ...
```

反过来写的话，计时会把缓存命中也算进去，你就分不清到底慢在哪了。

---

## 3.8 `functools` 三件套

`functools` 是「给函数用的工具箱」。四个最常用的工具：

### `lru_cache` / `cache`：自动记忆化

```python
import functools

@functools.lru_cache(maxsize=None)
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)

fib(100)             # 瞬间返回，没有缓存的话这个数字要算到天荒地老
fib.cache_info()     # CacheInfo(hits=98, misses=101, maxsize=None, currsize=101)
fib.cache_clear()    # 清空缓存
```

`lru_cache` 用一个字典把「实参元组 -> 返回值」存起来，下次同样的参数直接返回。

**`maxsize` 的含义**：LRU = Least Recently Used，超出容量时淘汰最久未使用的条目。
`maxsize=None` 表示不淘汰、无限增长（等价于 `functools.cache`）。

```python
@functools.cache                     # 3.9+，等价于 maxsize=None
def fib(n): ...

@functools.lru_cache(maxsize=128)    # 默认值，有上限，不会把内存吃光
def query(uid): ...
```

**什么时候用哪个**：

| 场景 | 选择 |
|------|------|
| 参数空间有限、结果确定（纯函数） | `cache` / `maxsize=None` |
| 参数空间大（比如用户 ID 有几百万） | `lru_cache(maxsize=128)` 之类，限制内存 |
| 输入是不可信的外部数据 | 加 `maxsize`，防止被撑爆内存 |

**三个必须知道的限制**：

**① 参数必须可哈希。**

```python
@functools.cache
def take_list(x):
    return x

take_list([1, 2])
# TypeError: unhashable type: 'list'
```

因为缓存底层是 dict，键是「实参元组」。所以 `list` / `dict` / `set` 都不能直接传。
（要缓存这种输入，得先转成 `tuple` / `frozenset`，或者用 `str` 做键。）

**② 参数的 `__hash__` 和 `__eq__` 必须靠谱。** 两个「看起来一样」的对象必须
真的 `hash` 相同且 `==` 为真，否则缓存永远不命中（或者更糟，命中错的结果）。

**③ 函数必须是纯的。** 有副作用（打印、写文件、发请求、读全局变量）的函数
被缓存后，副作用只会发生一次。这不是 bug，但通常不是你要的：

```python
@functools.cache
def log_and_get(n):
    print(f"真的计算了 {n}")       # 只会打印一次
    return n * 2
```

**还有两个容易忽略的点**：

- **缓存是全局的、跨调用持续存在的**，也就是 3.4 节说的「全局可变状态」。
  测试时要在 `setUp` 里 `cache_clear()`，否则用例之间互相污染。
- **`lru_cache` 会持有参数的强引用**，被缓存过的对象不会被 GC 回收。
  缓存实例方法时（`self` 会进缓存键！）尤其要小心，这是经典的「对象泄漏」来源：
  ```python
  class Service:
      @functools.lru_cache(maxsize=128)     # 危险：self 进了缓存键
      def get(self, key): ...
  ```
  正确做法是缓存一个模块级的纯函数，类方法里调用它。

**自测题**（`学习进度.md` 里的第 6 问）：`lru_cache` 对什么类型的函数不能用？
答案是：参数不可哈希的、有副作用的、结果依赖外部状态的（比如依赖当前时间、
依赖文件内容）。共同点都是「违反了纯函数假设」。

### `functools.partial`：见 3.1 节

再补一个真实用法——给回调函数「预先塞进」上下文：

```python
from functools import partial

def handle_event(user_id, event):
    ...

# 事件系统只传 event，那就把 user_id 冻进去
bus.subscribe("click", partial(handle_event, user_id=42))
```

**注意 `partial` 的一个坑**：它固定的是**参数**，不是「对象状态」；
而且关键字参数可以在调用时被覆盖：

```python
def f(a, b, c=3):
    return a, b, c

p = partial(f, 1, c=99)
p(2)              # (1, 2, 99)
p(2, c=0)         # (1, 2, 0)   <- 可以被覆盖
```

### `functools.reduce`：折叠

```python
import functools

functools.reduce(lambda a, b: a + b, [1, 2, 3, 4])       # 10
functools.reduce(lambda a, b: a * b, [1, 2, 3, 4])       # 24
functools.reduce(lambda a, b: a if a > b else b, [3, 9, 2])   # 9
```

**执行过程**（`reduce(func, [a, b, c])` -> `func(func(a, b), c)`）：

```
第一步: func(1, 2) = 3
第二步: func(3, 3) = 6
第三步: func(6, 4) = 10
```

**空序列会报错**：

```python
functools.reduce(lambda a, b: a + b, [])
# TypeError: reduce() of empty iterable with no initial value
```

要么给 `initial`，要么用 `sum()` 这类专用函数：

```python
functools.reduce(lambda a, b: a + b, [], 0)      # 0
sum([])                                          # 0
```

**什么时候用 `reduce`**：

| 任务 | 用什么 |
|------|-------|
| 求和 | `sum()` |
| 求积 | `math.prod()` |
| 求最值 | `max()` / `min()` |
| 拼接 | `"".join()` / `list.extend` |
| 以上都不是的折叠 | `reduce` |
| 带条件的复杂累积 | 老老实实写 `for` 循环 |

> **风格警告**：`reduce` 在 Python 里**名声不好**。Guido 当年差点把它从
> 标准库移到 `functools` 里就不再管了，理由就是「一个 `for` 循环更清楚」。
> `reduce(lambda a, b: a if a > b else b, xs)` 显然不如 `max(xs)`，
> 而复杂的累积用 `reduce` 写出来没人看得懂。
>
> **但有一个场景 `reduce` 确实赢**：折叠操作本身是一个**变量**的时候
> （比如从配置里读 `"sum"` / `"prod"` 然后选对应的折叠函数）。

```python
OPS = {
    "sum":  lambda a, b: a + b,
    "prod": lambda a, b: a * b,
    "max":  lambda a, b: a if a > b else b,
}

def fold(name, values, initial):
    return functools.reduce(OPS[name], values, initial)
```

### `functools` 里还有几个值得知道的

| 工具 | 作用 |
|------|------|
| `functools.wraps` | 装饰器必备，见 3.7 |
| `functools.singledispatch` | 单分派泛型函数：按第一个参数的类型选实现 |
| `functools.total_ordering` | 只写 `__eq__` 和 `__lt__`，自动补齐其余比较（模块 04） |
| `functools.cmp_to_key` | 老式比较函数转 `key` |
| `functools.partialmethod` | `partial` 的方法版 |

`singledispatch` 值得先看一眼，它能让「一个函数名 + 多套类型实现」变得很干净：

```python
@functools.singledispatch
def render(value):
    raise TypeError(f"不支持的类型：{type(value).__name__}")

@render.register
def _(value: int):
    return f"整数 {value}"

@render.register
def _(value: list):
    return "列表：" + ", ".join(map(str, value))

render(42)          # '整数 42'
render([1, 2])      # '列表：1, 2'
render("x")         # TypeError: 不支持的类型：str
```

**这比 C++ 的重载更明确**：它是运行期按类型派发，而且能给「没注册的类型」
一个统一的兜底实现（C++ 的重载是编译期决议，没匹配上直接编译失败）。

---

## 3.9 函数签名里的类型注解（简介）

> 模块 07 会细讲 `typing`。这里只讲**函数签名里怎么写**，以及**注解不会做任何事**。

### 基本写法

```python
def greet(name: str, times: int = 1) -> str:
    return f"你好，{name}" * times
```

语法就三处：

- 参数后面 `: 类型`
- 返回值在 `->` 之后
- 默认值在注解之后：`times: int = 1`

### 最重要的一句话：注解不影响运行

```python
def add(a: int, b: int) -> int:
    return a + b

add("abc", "def")     # 'abcdef'  <- 完全不报错
```

**Python 的类型注解只是给人和工具看的元数据，解释器一个都不检查。**
真正做事的是 `mypy` / `pyright` / IDE（模块 09 会讲怎么跑）。

对比 Java：Java 的泛型和类型是编译期强制的；Python 的选择是
「让运行时保持灵活，把检查交给可选的工具」。

### `from __future__ import annotations`：注解是字符串

课程所有文件都在开头写了这一行，它让**所有注解变成字符串**，不再求值：

```python
from __future__ import annotations

def f(x: SomeUndefinedClass) -> None:     # 名字不存在也照样能定义
    ...

f.__annotations__        # {'x': 'SomeUndefinedClass', 'return': 'None'}
```

**好处**：

1. **可以写「先有注解、后有类」的代码**（前向引用），不用把类型名写成字符串
2. 求值注解有开销（尤其是每次调用 `get_type_hints()`），变字符串后省掉了
3. 模块导入更快

**代价**：运行时想拿到真实类型对象，得手动求值：

```python
import typing
typing.get_type_hints(f)      # {'x': <class 'SomeUndefinedClass'>, 'return': NoneType}
inspect.signature(f, eval_str=True)
```

### 3.14 的新变化（PEP 649）

Python 3.14 起，**注解默认就是惰性求值的**（PEP 649 的「延迟注解」），
`from __future__ import annotations` 的效果已经变成了默认行为。

```python
def f(x: Undefined) -> None: ...
f.__annotations__      # NameError: name 'Undefined' is not defined
```

区别在于：3.14 之前，注解在**定义时**求值（所以上面这行会立刻炸）；
现在推迟到**访问 `__annotations__` 时**才求值，而且访问到的可能是真实类型对象
而不是字符串，取决于你有没有写 `from __future__ import annotations`。

**实践建议**：课程代码统一写 `from __future__ import annotations`
（兼容 3.9 及以前的写法，也保证行为一致），业务代码跟着项目的约定走。

### 常用注解速查

```python
def f(
    name: str,
    tags: list[str] | None = None,          # 3.10+ 的联合类型写法
    *args: float,
    count: int = 0,                          # keyword-only
    **kwargs: object,
) -> dict[str, int]:
    ...
```

| 想要表达 | 写法 |
|---------|------|
| 任意类型 | `object`（别用 `Any`，除非真没办法） |
| 可空 | `str | None` |
| 容器 | `list[int]` / `dict[str, int]` / `set[str]` / `tuple[int, ...]` |
| 固定长度元组 | `tuple[int, str]` |
| 任意可调用 | `Callable[[int], str]`（模块 07） |
| 只要是可迭代 | `Iterable[int]`（模块 07） |
| 可以是字典或列表 | `dict | list` |

**函数类型注解尤其值得写**，因为它同时是文档：

```python
def apply_twice(func: Callable[[int], int], value: int) -> int:
    ...
```

读完签名就知道：`func` 收一个 int 返回一个 int，`value` 是 int，整体返回 int。

---

## 3.10 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| `def f(lst=[])` | 多次调用共享同一个列表 | `lst=None` + 函数体内判空新建 |
| `def f(ts=time.time())` | 时间戳永远是定义那一刻 | 同上，把求值推迟到函数体 |
| 装饰器忘了 `return func(...)` | 被装饰函数返回 `None` | 一定 `return` |
| 装饰器没写 `@functools.wraps` | 日志里全是 `wrapper`，IDE 无提示 | 标配 `@functools.wraps(func)` |
| `wrapper()` 没写 `*args, **kwargs` | 被装饰函数一收参数就报错 | 原样透传 |
| `@retry(3)` 忘了 `raise` | 重试失败后静默返回 `None` | 循环外 `raise last` |
| 循环里 `lambda: i` | 全都返回最后一个值 | `lambda i=i:` 或工厂函数 |
| 函数里 `count += 1` 改外层 | `UnboundLocalError` | 加 `nonlocal` / `global` |
| `print(G)` 后又有 `G = 2` | `UnboundLocalError` | 赋值让 `G` 变成了局部变量 |
| `f(a=1, 2)` | `SyntaxError` | 位置实参必须写在关键字实参前面 |
| `f(*args)` 传太多 | `TypeError` | 检查形参和 `*args` 的边界 |
| `lru_cache` 缓存列表参数 | `TypeError: unhashable type` | 先转成 `tuple` |
| 用 `lru_cache` 缓存实例方法 | 对象无法回收 | 缓存模块级纯函数 |
| `map` 结果用第二次 | 空的 | 迭代器只能用一次，先 `list()` |
| `sorted(..., key=cmp_func)` | 结果莫名其妙 | `key` 收的是「打分函数」不是「比较函数」 |
| `reduce` 传空序列 | `TypeError` | 给 `initial` 或用 `sum()` |
| `global` 满天飞 | 状态难追踪、测试互相污染 | 用返回值 / 参数 / 类封装 |
| 闭包捕获大对象 | 内存不释放 | 只捕获需要的小值 |

---

## 3.11 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | 9 节可运行示例，覆盖 3.1~3.9 全部结论 |
| `exercises.py` | 9 道练习，含自动断言 |
| `solutions.py` | 参考答案 + 为什么这么写 + 常见错误写法错在哪 |

### 强烈建议的学法

1. 先跑 `demo.py`，**每一节都先猜输出再看结果**。猜错的地方就是你的盲区。
2. 在 `demo_mutable_default()` 里，把断点下在 `box.append(item)` 那一行，
   按 `F5` 启动调试，在「监视」面板里加入 `box` 和 `add_item.__defaults__[0]`，
   看它们是不是同一个对象——**亲眼看到一次，这个坑你就再也不会踩**。
3. 在 `demo_closure()` 里用「监视」面板加入 `double.__closure__[0].cell_contents`，
   理解「闭包保存的是 cell」。
4. 然后做 `exercises.py`，全 PASS 之后再看 `solutions.py`。

### 三个「必须能徒手写出来」的东西

学完这个模块，下面三样东西应该能在不看资料的情况下写对：

```python
# 1. 一个完整的装饰器（含 wraps 和异常安全）
def timer(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            return func(*args, **kwargs)
        finally:
            print(f"{func.__name__}: {time.perf_counter() - start:.4f}s")
    return wrapper

# 2. 一个闭包工厂（含 nonlocal）
def make_counter(start=0, step=1):
    count = start
    def counter():
        nonlocal count
        count += step
        return count
    return counter

# 3. 一个带参数的装饰器（三层结构）
def retry(times):
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            for _ in range(times):
                try:
                    return func(*args, **kwargs)
                except Exception:
                    pass
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

如果哪一样还需要翻书，就回去把对应的小节再读一遍。

---

## 3.12 延伸阅读

- [Python 官方教程 4.8 函数定义](https://docs.python.org/zh-cn/3/tutorial/controlflow.html#defining-functions)
  —— 参数机制的权威描述，值得逐行读一遍
- [PEP 3102 – Keyword-Only Arguments](https://peps.python.org/pep-3102/) —— `*` 的设计动机
- [PEP 570 – Python Positional-Only Parameters](https://peps.python.org/pep-0570/) —— `/` 的设计动机
- [PEP 318 – Decorators for Functions and Methods](https://peps.python.org/pep-0318/) —— `@` 语法是怎么来的，为什么是 `@`
- [PEP 649 – Deferred Evaluation of Annotations](https://peps.python.org/pep-0649/) —— 3.14 注解行为变化的来源
- [functools 官方文档](https://docs.python.org/zh-cn/3/library/functools.html) —— 每个工具都有可运行示例
- [Real Python: Primer on Python Decorators](https://realpython.com/primer-on-python-decorators/) —— 装饰器讲得最透的一篇长文
- 《流畅的 Python》第 5 章（一等函数）、第 7 章（函数装饰器和闭包）、第 9 章（装饰器与闭包进阶）
  —— **这三章是本模块的最佳扩展阅读**
