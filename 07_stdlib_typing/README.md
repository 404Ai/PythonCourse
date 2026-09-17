# 模块 07 · 标准库与类型注解

> **目标**：把「能跑的脚本」变成「别人敢接手的工具」。
>
> 这个模块讲三件事：
> 1. **类型注解**——让 IDE 和 mypy 帮你在运行前发现 bug
> 2. **日志与命令行**——让程序能被人使用、被自己排查
> 3. **正则与时间**——两个你迟早要打交道、而且极易写错的领域

---

## 7.1 类型注解基础

### 语法：注解是给谁看的

```python
# 变量注解
name: str = "张三"
count: int = 0
items: list[str] = []
table: dict[str, int] = {}

# 函数参数与返回值
def greet(name: str, times: int = 1) -> str:
    return f"你好，{name}" * times
```

**最重要的认知：上面这些注解，CPython 在运行时几乎什么都不做。**

```python
x: int = "这其实是个字符串"      # 完全合法，不报错，不转换
```

`x: int = "..."` 不会：

- 检查类型
- 转换类型
- 影响性能（运行时几乎没有额外开销）
- 阻止你把 `str` 赋给一个标注为 `int` 的名字

它就是一个**可以被工具读到的结构化注释**。类型检查是 `mypy` / `pyright` /
IDE 静态分析器做的事，不是解释器做的事。

> 唯一的例外是**函数签名的注解会被存下来**（`__annotations__`），
> 所以可以用 `typing.get_type_hints()` 在运行时读到它们。
> 各种 Web 框架（FastAPI、pydantic）的参数校验就是这么实现的。

### 为什么还要写

| 收益 | 说明 |
|------|------|
| IDE 补全 | 知道 `items` 是 `list[str]` 才敢在你打 `.` 的时候提示 `append` |
| 静态检查 | `mypy` 能在**运行前**发现「你把 `None` 传给了要 `str` 的函数」 |
| 文档 | `def load(path: str, strict: bool = False) -> dict` 一眼看懂用法 |
| 重构安全 | 改一个函数的返回值，mypy 会告诉你哪 20 个调用点需要跟进 |
| 内省 | `dataclasses`、`pydantic`、`argparse` 的某些用法能直接从注解生成代码 |

**代价**：多写一些字，以及需要维护。所以注解应该写在**边界**上——
公开函数的签名、模块级的数据结构、跨模块传递的对象。
一个 5 行的内部辅助函数标满注解是噪音。

### 注解在运行时到底发生了什么（PEP 649）

这块在 Python 3.14 有个**重大变化**，值得单独讲。

**3.14 之前**：函数定义的瞬间，注解表达式就会被求值。

```python
def f(x: Undefined) -> None:    # 3.13: 定义时就 NameError
    ...
```

**3.14 起（PEP 649 / PEP 749）**：注解改成**延迟求值**，
只有在你真的去读 `__annotations__` 时才计算。

```python
def f(x: Undefined) -> None:    # 3.14: 定义时不报错
    ...

f.__annotations__               # 现在才 NameError
f.__annotate__                  # 这是实际存储的求值函数
```

还有 `annotationlib` 这个新模块，能让你用三种不同策略取注解
（求值 / 保留字符串 / 保留前向引用）。日常写业务代码用不到，
但你要知道它是存在的，不然看到 `__annotate__` 会一头雾水。

### `from __future__ import annotations` 与它的区别

本课程每个文件开头都有这一行。它和 PEP 649 是**两件不同的事**：

| | `from __future__ import annotations` | PEP 649（3.14 默认） |
|---|---|---|
| 效果 | 注解**永远**是字符串，不保存求值函数 | 注解**延迟求值**，但最终是真实对象 |
| `__annotate__` | 返回 `None` | 返回求值函数 |
| 读取方式 | `get_type_hints()` 求值，或 `annotationlib` 的 `FORWARDREF` 格式 | `__annotations__` 直接可用 |
| 主要用途 | 兼容 3.9~3.13，历史习惯 | 3.14+ 的正式机制 |

**共同点**：都解决了「定义时不需要名字已经存在」的问题。

```python
class Node:
    # 没有这两种机制时，这里必须写字符串 "Node | None"
    def __init__(self, value: int, next_: Node | None = None) -> None:
        ...
```

**实践建议**：项目里**选一种，全项目统一**。
本课程用 `from __future__ import annotations`，因为它向后兼容到 3.7，
而且没有 `__annotate__` 那套心智负担。

> **一个真实的坑**：`from __future__ import annotations` 会让注解变成字符串，
> 而有些库**靠读取真实类型对象工作**。比如 `TypedDict` 的
> `NotRequired[T]`，在字符串模式下**识别不出来**：
>
> ```python
> from __future__ import annotations
> from typing import TypedDict, NotRequired
>
> class Movie(TypedDict):
>     title: str
>     rating: NotRequired[float]
>
> Movie.__required_keys__      # frozenset({'title', 'rating'})  <- rating 被当成必填了！
> ```
>
> 这是本课程在 Python 3.14 上实测的结果。
> 想让它正常工作，要么去掉 future import，要么改用
> `class Movie(_Base, total=False)` 的继承写法（7.2 节会讲）。
> **这就是「注解不影响运行时」这句话的边界——它影响，只是影响的是元编程。**

---

## 7.2 `typing` 常用类型速查

### 现代写法：内置泛型

```python
# 3.9 之后推荐（PEP 585）
xs: list[int] = []
d: dict[str, int] = {}
t: tuple[int, str] = (1, "a")
s: set[str] = set()
fro: frozenset[int]

# 3.9 之前的写法，现在不要用了
from typing import List, Dict, Tuple, Set
xs: List[int] = []
```

**为什么 `list[int]` 能工作**：这些内置类型实现了 `__class_getitem__`，
所以 `list[int]` 在运行时是合法的表达式（返回一个 `types.GenericAlias` 对象）。
**运行时它不做任何检查**，纯粹是给静态工具看的。

### `Optional` / `X | None` / `Union`

```python
from typing import Optional, Union

def find(name: str) -> Optional[str]: ...      # 老写法
def find(name: str) -> str | None: ...         # 3.10+，推荐
def parse(v: int | str | None) -> str: ...     # 多处联合
```

`Optional[str]` 和 `str | None` **完全等价**。
`Optional` 这个名字有误导性——它不表示「可选参数」，
而是「这个值可能是 `None`」。**新代码一律用 `|`。**

### 容器类型的变体

| 类型 | 含义 | 你能做什么 |
|------|------|-----------|
| `Iterable[T]` | 可迭代 | 只能 `for` 它 |
| `Iterator[T]` | 迭代器 | `for` + `next()` |
| `Sequence[T]` | 有序序列 | `for` + 索引 + `len` |
| `Mapping[K, V]` | 只读映射 | `for` + `d[k]` + `len` |
| `MutableMapping[K, V]` | 可变映射 | 上面 + `d[k] = v` |
| `Collection[T]` | 可迭代 + 有 `len` | `for` + `len` + `in` |

**参数类型该用哪个，是最能体现水平的地方**：

```python
# 差的写法：要求调用方必须传 list
def total(values: list[int]) -> int:
    return sum(values)

# 好的写法：只要能被迭代就行
def total(values: Iterable[int]) -> int:
    return sum(values)

total([1, 2, 3])          # 列表，可以
total((1, 2, 3))          # 元组，可以
total(range(3))           # range，可以
total(n for n in [1, 2])  # 生成器，也可以
```

**规则：参数类型尽量写「最宽的能接受」的那个，返回类型写「最具体的那个」。**
这就是所谓的「参数逆变、返回协变」的直觉版本。

```python
# 返回：如果调用方拿到的是 dict，他就能用 dict 的方法，别只承诺 Mapping
def load_config() -> dict[str, str]: ...
```

### `Callable`

```python
from typing import Callable

def apply(fn: Callable[[int, int], int], a: int, b: int) -> int:
    return fn(a, b)

apply(lambda x, y: x + y, 1, 2)
```

`Callable[[参数类型...], 返回类型]`。参数列表写成 `...` 表示
「参数不重要」（`Callable[..., int]`），**不要滥用**——它就是放弃检查。

### `Any`

```python
from typing import Any

def log_json(data: Any) -> None: ...
```

`Any` 表示「别检查我」。它和 `object` 完全不是一回事：

```python
def f(x: object) -> None:
    x.anything()      # mypy: 报错，object 上没有 anything

def g(x: Any) -> None:
    x.anything()      # mypy: 通过，Any 上什么都有
```

`Any` 会**污染**它接触到的一切（`Any + int` 还是 `Any`），
一个 `Any` 能顺着调用链把类型检查全废掉。
**它的正确用途**：第三方库没有类型标注时的桥接、
真正异构的容器（JSON 解析结果）、`*args/**kwargs` 的转发。

### `TypeVar` 与 `Generic`

```python
from typing import TypeVar

T = TypeVar("T")

def first(items: list[T]) -> T:
    return items[0]

reveal_a = first([1, 2, 3])        # mypy 推出 int
reveal_b = first(["a", "b"])       # mypy 推出 str
```

`TypeVar` 的作用是**保持类型之间的关联**。对比一下：

```python
def bad_first(items: list) -> object:      # 丢掉了信息，调用方拿回 object
    return items[0]

def good_first(items: list[T]) -> T:       # 输入是 list[int]，输出就是 int
    return items[0]
```

写泛型类：

```python
from typing import Generic, TypeVar

T = TypeVar("T")

class Stack(Generic[T]):
    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        return self._items.pop()
```

**3.12+ 的新语法**（本课程按 PEP 695）：

```python
# 不用再显式声明 TypeVar
def first[T](items: list[T]) -> T:
    return items[0]

class Stack[T]:
    ...
```

课程代码里用哪种都行，但**别在同一个文件里混用**。

### `Literal` 与 `Final`

```python
from typing import Final, Literal

Mode = Literal["r", "w", "a"]        # 只能是这三个字符串之一

def open_file(path: str, mode: Mode) -> None:
    ...

open_file("a.txt", "r")     # OK
open_file("a.txt", "x")     # mypy 报错，但运行时不报

MAX_RETRY: Final = 3        # mypy 会阻止你重新赋值
PI: Final[float] = 3.14159
```

`Literal` 的价值在于：**把「魔法字符串」变成可检查的枚举**，
而且 IDE 能给你补全。它比 `str` 精确得多，又比 `Enum` 轻。

`Final` 是给**常量**用的。注意它**只在静态检查层面生效**：

```python
MAX_RETRY: Final = 3
MAX_RETRY = 5        # 运行时完全合法，mypy 会报错
```

### `TypeAlias`

```python
from typing import TypeAlias

# 3.10+ 的显式写法
Vector: TypeAlias = list[float]
Matrix: TypeAlias = list[Vector]
UserRecord: TypeAlias = dict[str, str | int | None]

# 3.12+ 用 type 语句更清晰
type Vector = list[float]
type Matrix = list[Vector]
```

不写 `TypeAlias` 也能用（就是个普通赋值），
但显式写出来能让 mypy 知道「这是别名，不是变量」，报错信息也更好看。

### `TypedDict`

给「固定键名的 dict」加类型：

```python
from typing import TypedDict

class Movie(TypedDict):
    title: str
    year: int
    rating: float
```

**运行时它就是一个 `dict`**：

```python
m: Movie = {"title": "让子弹飞", "year": 2010, "rating": 9.1}
type(m)          # dict，不是 Movie！
```

它带来的是：`m["titel"]` 会被 mypy 抓出来（拼写错误），
而普通 `dict[str, Any]` 完全看不出来。

**可选键的两种写法**：

```python
# 写法一：total=False 继承（推荐，兼容性最好）
class _MovieRequired(TypedDict):
    title: str
    year: int

class Movie(_MovieRequired, total=False):
    rating: float
    tags: list[str]

Movie.__required_keys__    # frozenset({'title', 'year'})
Movie.__optional_keys__    # frozenset({'rating', 'tags'})
```

```python
# 写法二：NotRequired（更简洁，但和 from __future__ import annotations 冲突）
class Movie(TypedDict):
    title: str
    year: int
    rating: NotRequired[float]
```

**本课程用写法一**，原因见 7.1 的那个坑。

> `TypedDict` 是**纯粹的静态工具**，运行时**完全不校验**。
> 想让「数据进来时真的被检查」，得自己写校验函数
> （练习 q1 就是这个），或者上 pydantic。
> `TypedDict.__required_keys__` 是你在运行时唯一能拿到的元信息。

### `@overload`

给「同一个函数，不同参数类型对应不同返回类型」的情况加精确签名：

```python
from typing import overload

@overload
def parse(value: str) -> str: ...
@overload
def parse(value: int) -> int: ...
@overload
def parse(value: None) -> None: ...

def parse(value):                    # 真正的实现，不带 @overload
    if value is None:
        return None
    return str(value) if isinstance(value, str) else value
```

**运行时**：三个 `@overload` 定义会被后面的真实实现**覆盖掉**，
调用 `parse` 执行的是最后一个。`@overload` 只是给静态检查器看的声明。

**注意**：`@overload` 系列必须紧挨着真实实现写，
中间插一个别的函数 mypy 就找不到了。

---

## 7.3 `Protocol` 与结构化子类型

### 问题：名义子类型不够用

`abc.ABC` 是**名义子类型**（nominal subtyping）：
一个类必须**显式继承** `ABC` 才算数。

```python
from abc import ABC, abstractmethod

class Sink(ABC):
    @abstractmethod
    def send(self, msg: str) -> None: ...

class ListSink(Sink):          # 必须写 (Sink)
    def send(self, msg: str) -> None: ...
```

问题来了：如果 `ListSink` 是**别人的库**里的类，
或者是一个你不想改动的老类呢？你只能：

- 写一个适配器包一层（多一层间接）
- 或者放弃类型检查，参数写成 `Any`

### `Protocol` 解决这个问题

```python
from typing import Protocol

class Sink(Protocol):
    def send(self, msg: str) -> None:
        ...                     # 方法体是 ... ，这里不写实现

def broadcast(sinks: list[Sink], msg: str) -> None:
    for s in sinks:
        s.send(msg)
```

**任何有 `send(self, msg: str) -> None` 方法的类，都自动满足 `Sink`**——
不管它有没有继承 `Sink`：

```python
class MyOwnSink:                    # 完全不知道 Sink 的存在
    def send(self, msg: str) -> None:
        print(msg)

class ThirdPartySink:               # 别人的库里的
    def send(self, msg: str) -> None:
        ...

broadcast([MyOwnSink(), ThirdPartySink()], "hello")   # mypy 全部通过
```

这就是**结构化子类型**（structural subtyping），也就是模块 01 讲的
**鸭子类型**在类型系统里的正式表达。

### `runtime_checkable`：运行时的 `isinstance`

`Protocol` 默认只在静态检查层面生效，`isinstance` 用不了：

```python
isinstance(x, Sink)      # TypeError: Instance and class checks can only be used with @runtime_checkable protocols
```

加上装饰器就可以了：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Sink(Protocol):
    def send(self, msg: str) -> None: ...

isinstance(MyOwnSink(), Sink)     # True
isinstance(object(), Sink)        # False
```

**但有一个重要的限制**：`runtime_checkable` 只检查**方法名存不存在**，
**不检查签名**。

```python
class Fake:
    def send(self, totally, wrong, signature) -> None: ...

isinstance(Fake(), Sink)      # True ！签名完全不匹配也照样通过
```

所以 `runtime_checkable` 的 `isinstance` 是很弱的检查，
**别拿它当参数校验用**。它的合理用途是分发/路由（比如
「这个对象是不是一个 file-like object，是就按文件处理」）。

### `Protocol` vs `ABC` 怎么选

| | `Protocol` | `abc.ABC` |
|---|---|---|
| 关系 | 结构（看有没有方法） | 名义（看有没有继承） |
| 要求对方改代码 | 不用 | 必须继承 |
| 支持第三方类 | 是 | 只能包适配器 |
| `isinstance` | 需要 `@runtime_checkable`，且只查方法名 | 直接可用，且准确 |
| 能提供默认实现 | 可以（但静态检查不管） | 可以（`super()` 调用） |
| 能当注册表用 | 不行 | `ABC.register()` |
| 适合 | 描述「接口长什么样」 | 提供「共享的实现」 |

**实践规则**：

- 你**拥有**整条继承链，需要共享代码 -> `ABC`
- 你只是想说「只要长这样就能用」-> `Protocol`
- 库的公开 API 想接受用户自定义类型 -> `Protocol`（否则逼用户继承你的类）

---

## 7.4 `mypy` 与「注解不影响运行时」

### 静态检查器的定位

```powershell
pip install mypy
mypy your_module.py
```

mypy 做的事：把注解当**断言**，沿数据流检查是否自洽。

```python
def double(x: int) -> int:
    return x * 2

double("abc")        # mypy: error: Argument 1 has incompatible type "str"
                     # 运行时：'abcabc'，完全合法，没有任何报错
```

**它能抓的**：拼写错误的属性名、`None` 没判就调用、
参数个数/类型不对、`TypedDict` 键名写错、返回值类型不匹配。

**它抓不到的**：逻辑错误、运行时的数据问题（用户输入就是脏的）、
`Any` 传播之后的一切、动态生成的代码。

### `mypy` 的工作模式

mypy 是**渐进式**的，你可以从零开始慢慢加：

```ini
# mypy.ini / pyproject.toml
[mypy]
# 默认：只检查有注解的部分。没注解的函数体完全不看
# --disallow-untyped-defs：所有函数都必须有注解
# --strict：打开所有严格选项，新项目建议直接上
strict = true
```

**没写注解的函数，mypy 默认不检查它的函数体**（把参数和返回值都当 `Any`）。
这是设计上的妥协：让大项目可以逐步迁移，而不是一次性面对几千个错误。

### 为什么注解不是强制的

1. **脚本和一次性代码**不需要。10 行的数据处理脚本标满注解是浪费时间。
2. **动态特性的表达力**：元编程、`__getattr__` 转发、
   运行时代理——这些场景里类型系统只能靠 `Any` 和 `# type: ignore` 绕过。
3. **渐进式是有意的设计**。PEP 484 明确说 Python 会一直是动态类型语言，
   注解是「可选的、外挂的一层」。GvR 的原话大意是：
   **不要为了类型系统牺牲语言的灵活性。**
4. 生态里大量老库没有注解（虽然现在标准库和主流库都补齐了）。

**那什么时候必须写**：团队协作的代码、公开的库 API、
跨模块传的数据结构。判断标准是**这段代码会被别人读/改吗**。

> **`mypy` 只需要在 README 里知道就够了。** 本模块的代码全部只用标准库，
> 不会 import `mypy`。想试的话自己在命令行跑，
> 把 `07_stdlib_typing/solutions.py` 丢给它，看看有什么报错。

---

## 7.5 `dataclasses` 进阶

模块 04 讲了基础，这里补进阶用法。

### `field()`：需要更精细控制时

```python
from dataclasses import dataclass, field

@dataclass
class Config:
    # 1. default_factory：可变默认值必须用它
    tags: list[str] = field(default_factory=list)

    # 2. 默认值 + 不在 repr 里 + 不参与比较
    cache: dict = field(default_factory=dict, repr=False, compare=False)

    # 3. 初始化时不可见，但之后可以访问（由 __post_init__ 填）
    total: int = field(init=False, default=0)

    # 4. 元数据，给自己或框架读
    name: str = field(default="", metadata={"help": "配置名"})
```

**为什么可变默认值必须用 `default_factory`**：

```python
@dataclass
class Bad:
    items: list = []          # TypeError: mutable default <class 'list'> ... not allowed
```

dataclass 会**直接报错**（不像函数默认参数那样只是静默地共享同一个列表）。
这是 dataclass 做得比函数参数好的地方——它把这个经典坑堵死了。

`default_factory` 接收的是一个**可调用对象**（不是值），
每次实例化时会调用它生成新对象。`list` / `dict` / `set` 本身就是可调用对象，
所以直接写 `default_factory=list`。

### `__post_init__`：派生字段与校验

```python
@dataclass
class Order:
    items: list[tuple[str, int]] = field(default_factory=list)
    total: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # 1. 派生字段
        self.total = sum(price * qty for _, price, qty in ...)
        # 2. 校验
        if self.total < 0:
            raise ValueError("总额不能为负")
```

`__post_init__` 在自动生成的 `__init__` **最后**被调用，
此时所有字段都已赋值。派生字段配合 `field(init=False)` 用，
表示「这个字段不该由调用方传」。

### `asdict` / `astuple`：序列化

```python
from dataclasses import asdict, astuple

@dataclass
class Point:
    x: int
    y: int = 0

p = Point(1, 2)
asdict(p)      # {'x': 1, 'y': 2}          （递归：嵌套的 dataclass 也会转）
astuple(p)     # (1, 2)
```

**关键点：`asdict` 是深拷贝式的递归转换。**

```python
d = asdict(p)
d["x"] = 999
p.x            # 1，原对象不受影响
```

这正好解决了 JSON 序列化的问题：

```python
import json
json.dumps(asdict(p))                     # 直接能序列化
json.dumps(p, default=lambda o: asdict(o))  # 或者用 default 钩子，更省事
```

**注意 `asdict` 不认非 dataclass 的嵌套对象**：

```python
@dataclass
class Wrapper:
    when: datetime            # datetime 不是 dataclass

asdict(Wrapper(datetime.now()))
# {'when': datetime.datetime(...)}  <- 原样返回，json.dumps 还是会炸
# 你的 default 函数要处理它
```

### `frozen` 与不可变性

```python
@dataclass(frozen=True)
class Point:
    x: int
    y: int

p = Point(1, 2)
p.x = 3        # FrozenInstanceError
hash(p)        # 可哈希了（前提是所有字段都可哈希）
```

`frozen=True` 会同时生成 `__setattr__` 的拦截和 `__hash__`。
**默认的 dataclass 是不可哈希的**（`__hash__ = None`），
所以不能放进 `set` 或当 dict 的键——`frozen=True` 才能解决这个问题。

### 和 `attrs` / `pydantic` 的关系

| | 标准库 `dataclasses` | `attrs` | `pydantic` |
|---|---|---|---|
| 来源 | 标准库，零依赖 | 第三方，dataclass 的前身 | 第三方，为数据校验而生 |
| 核心卖点 | 够用、无依赖 | 功能更多（`slots`、`validator`、`converter`） | **运行时数据校验 + 类型转换** |
| 运行时校验 | 不做 | 可选 | **默认做** |
| 类型转换 | 不做 | 可选 | 默认做（`"42"` -> `42`） |
| 性能 | 快 | 快 | v2 用 Rust 重写，很快 |
| 适合 | 内部数据结构 | 需要更多控制的数据类 | API 入参、配置文件、外部数据 |

**一句话选择**：

- 内部传递的结构化数据 -> `dataclasses`（标准库，够用）
- 从外部（API / 用户输入 / 文件）来的数据 -> `pydantic`（一定要校验）
- 需要 `attrs` 特有能力（如 `__slots__` + 继承 + 转换器）-> `attrs`

`dataclasses` 的 `__init_subclass__`/`field` 这些设计直接借鉴了 `attrs`，
PEP 557 的作者就是 `attrs` 的作者。**不理解 attrs 的动机，就理解不了
dataclass 为什么长这样。**

---

## 7.6 `logging`

### 为什么不用 `print`

```python
print("用户登录失败")
```

问题：

1. **没法关掉。** 生产环境要 100 万条日志？还是 0 条？`print` 只会一直打。
2. **没法分级。** 「用户登录失败」和「磁盘写满了」都用 `print`，你没法过滤。
3. **没有上下文。** 哪一行？哪个模块？什么时候？`print` 给不了。
4. **控制不了输出目标。** 要写到文件、要发到 syslog、要发给监控？`print` 只能到 stdout。
5. **`print` 是 stdout。** 程序输出（stdout）应该给用户，诊断信息（stderr）应该给日志。

**一句话**：`print` 是给用户看的，`logging` 是给自己看的。

### 四个要素

```
        ┌──────────┐
        │  Logger  │  你调用的入口：logger.info(...)
        └────┬─────┘  决定「这条日志要不要发出去」（按 level 过滤）
             │
             ▼
        ┌──────────┐
        │ Handler  │  决定「发到哪里」：控制台 / 文件 / 网络 / 邮件
        └────┬─────┘  也决定「哪些级别」：handler.setLevel(...)
             │
             ▼
        ┌──────────┐
        │Formatter │  决定「长什么样」：%(asctime)s %(levelname)s %(message)s
        └────┬─────┘
             │
             ▼
        ┌──────────┐
        │  Level   │  过滤门槛：DEBUG < INFO < WARNING < ERROR < CRITICAL
        └──────────┘
```

**过滤是两级串联的**：一条日志要发出去，
必须 `logger.level <= 记录级别` **且** `handler.level <= 记录级别`。
任何一级没通过，它就消失了。这是「我的日志怎么不见了」的头号原因。

### 级别怎么选

| 级别 | 数值 | 什么时候用 | 生产环境 |
|------|------|-----------|---------|
| `DEBUG` | 10 | 排查细节：变量的值、分支走向 | 关 |
| `INFO` | 20 | 正常但重要的事件：启动、请求完成、任务结束 | 开 |
| `WARNING` | 30 | **能继续跑，但不正常**：重试了、降级了、配置缺失用了默认值 | 开 |
| `ERROR` | 40 | 这次操作失败了，但程序还活着 | 开 |
| `CRITICAL` | 50 | 整个程序要挂了 | 开 |

**判据**：问自己「这条日志需要有人在半夜被叫起来处理吗？」
是 -> `ERROR` 以上；否，但生产环境要看 -> `INFO`；
只在排查具体问题时才需要 -> `DEBUG`。

**最常见的错误是把 `WARNING` 当 `INFO` 用**，
最后满屏黄色警告，真正的警告被淹没。

### 标准用法

```python
import logging

# 每个模块都这么写。__name__ 就是模块名（如 "myapp.db"），
# 日志里能直接看出是哪个模块打的，而且 logger 名天然形成层级。
logger = logging.getLogger(__name__)

def process(item):
    logger.info("开始处理 %s", item)
    try:
        ...
    except ValueError:
        logger.exception("处理 %s 失败", item)   # 自动带上 traceback
        raise
```

**入口处配置一次**：

```python
def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    ...
```

`basicConfig()` 给**根 logger** 装一个 `StreamHandler`（输出到 stderr）。
**它只在根 logger 还没有 handler 时生效**，所以在库代码里调用它
可能完全没有效果（宿主程序已经配过了）。

### 两条铁律

**① 用 `%s` 延迟格式化，不要用 f-string**

```python
# 好：只在真的要输出时才做字符串格式化
logger.debug("处理 %s，耗时 %.2f 秒", item, elapsed)

# 坏：无论日志级别多高，f-string 都会被执行
logger.debug(f"处理 {item}，耗时 {elapsed:.2f} 秒")
```

**为什么这个区别重要**：被过滤掉的日志，第一版的开销是「一次函数调用 + 几个参数」，
第二版的开销是「完整的字符串格式化 + 可能很贵的 `__repr__`」。
在一个每秒几十万次的热函数里，第二版能让 `DEBUG` 级别的日志
把程序拖慢一倍——**哪怕你根本没开 DEBUG**。

**例外**：`logger.error(f"...")` 这种错误处理器里的日志，
性能无所谓，用 f-string 更可读也没问题。**热路径上才需要在意。**

**② 不要用 `logging.warning()` / `logging.info()` 这些模块级函数**

```python
# 坏：用的是根 logger，name 是 "root"，而且会和你自己配的 handler 打架
logging.warning("磁盘快满了")

# 好：用自己的 logger
logger = logging.getLogger(__name__)
logger.warning("磁盘快满了")
```

模块级函数操作的是**根 logger**。在多模块的程序里，
你没法按模块过滤、没法按模块设级别，而且第三方库
调用 `basicConfig()` 时会打乱你的配置。

**唯一的例外**：`logging.basicConfig()` 和一次性脚本的入口，
用根 logger 是合理的。

### 异常日志：`logger.exception`

```python
try:
    do_something()
except Exception:
    logger.exception("操作失败")     # 等价于 logger.error(..., exc_info=True)
    raise
```

它会**自动把当前异常的 traceback 打进日志**。
手写 `logger.error(f"...: {exc}")` 只会给你一行错误消息，
**没有调用栈**，排查时等于瞎了一半。

### 配置的三种方式

```python
# 1. basicConfig —— 最简单，适合脚本
logging.basicConfig(level=logging.INFO)

# 2. dictConfig —— 结构化，适合应用
import logging.config
logging.config.dictConfig({
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"std": {"format": "%(levelname)s %(name)s %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler",
                             "formatter": "std", "level": "INFO"}},
    "root": {"handlers": ["console"], "level": "DEBUG"},
})

# 3. 手工 addHandler —— 测试里最常用（练习 q6 就是这么做的）
logger = logging.getLogger("x")
handler = logging.StreamHandler(io.StringIO())
handler.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))
logger.addHandler(handler)
```

> **测试时的两个必须动作**：
> `logger.propagate = False`（不然日志会同时往根 logger 传一份），
> 和测完 `logger.removeHandler(handler)`（不然 handler 会累积，
> 第二次跑测试就出现重复日志）。

---

## 7.7 `argparse`

### 最小可用版本

```python
import argparse

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="greet",
        description="向指定的人问好。",
        epilog="示例: greet 张三 --times 3",
    )
    parser.add_argument("name", help="要问候的名字")
    parser.add_argument("--times", type=int, default=1, help="重复次数（默认 1）")
    args = parser.parse_args()

    for _ in range(args.times):
        print(f"你好，{args.name}")

if __name__ == "__main__":
    main()
```

`argparse` 自动给你三样东西：

- `-h` / `--help`（**不写 `help=` 也有**，但写上才有人能看懂）
- 参数错误时的用法提示和退出码 2
- 前缀自动补全（写 `--tim` 会被补成 `--times`）

### `add_argument` 常用参数

| 参数 | 作用 | 示例 |
|------|------|------|
| `type=` | 把字符串转成目标类型 | `type=int`、`type=float`、`type=Path` |
| `default=` | 没给时的默认值 | `default=10` |
| `choices=` | 限定取值范围，越界自动报错 | `choices=["r", "w", "a"]` |
| `action="store_true"` | 布尔开关 | `--verbose` |
| `action="store_false"` | 反向布尔 | `--no-color` |
| `action="append"` | 重复出现时收集成列表 | `--tag a --tag b` -> `["a", "b"]` |
| `action="count"` | 出现次数 | `-vvv` -> `3` |
| `nargs=N` / `"?"` / `"*"` / `"+"` | 接收多个值 | `nargs="+"` 至少一个 |
| `required=True` | 让可选参数必填（少用） | 见下 |
| `metavar=` | 帮助里的显示名 | `metavar="FILE"` |
| `help=` | 帮助文本 | **能写就写** |

**参数名就是属性名**：

```python
parser.add_argument("--dry-run", action="store_true")
args = parser.parse_args([])
args.dry_run        # True/False —— 连字符会变成下划线
```

**`type=` 是函数，不只是类型**：

```python
parser.add_argument("--size", type=parse_size)     # 你自己写的函数
def parse_size(text: str) -> int:
    if text.endswith("K"):
        return int(text[:-1]) * 1024
    return int(text)
```

`type=` 抛出 `ValueError` / `TypeError` 时，argparse 会捕获它，
打印「invalid parse_size value」并退出（退出码 2）。
**这是 argparse 最实用的扩展点。**

### 位置参数 vs 可选参数

```python
parser.add_argument("input")                 # 位置参数，必填
parser.add_argument("output", nargs="?")     # 位置参数，可省略（得到 None）
parser.add_argument("--verbose", action="store_true")   # 可选参数
```

**`required=True` 用在可选参数上是反模式**：

```python
parser.add_argument("--name", required=True)   # 形式上可选，实际上必填
```

用户看到 `[--name NAME]` 以为可以不给，结果不给就报错。
**如果一个参数真的必填，就把它写成位置参数。**

### 子命令

```python
parser = argparse.ArgumentParser(prog="tasks")
subparsers = parser.add_subparsers(dest="command", required=True)

add_parser = subparsers.add_parser("add", help="添加任务")
add_parser.add_argument("title")
add_parser.add_argument("--priority", choices=["low", "medium", "high"],
                        default="medium")

list_parser = subparsers.add_parser("list", help="列出任务")
list_parser.add_argument("--limit", type=int, default=10)
list_parser.add_argument("--all", action="store_true")

args = parser.parse_args(["add", "写作业", "--priority", "high"])
args.command      # 'add'
args.title        # '写作业'
args.priority     # 'high'
```

- **`dest="command"` 必须写**，否则你没法知道用户用了哪个子命令
- **`required=True` 推荐写**，否则用户不写子命令时 `args.command` 是 `None`，
  你要在代码里手动判空
- 每个子命令的 `-h` 是独立的：`tasks add -h` 只显示 `add` 的参数

### 测试 CLI 的关键技巧

**把 `main()` 拆成两部分**：

```python
def build_parser() -> argparse.ArgumentParser:
    """只负责构造 parser —— 可以被测试单独调用。"""
    ...

def main() -> None:
    args = build_parser().parse_args()      # 不传参数才读 sys.argv
    ...
```

**`parse_args()` 可以接收一个列表**，这样测试时不用去改 `sys.argv`：

```python
args = build_parser().parse_args(["add", "写作业"])
```

这是本模块练习 q3 的做法：**构造 parser 的函数和解析 argv 的函数分开**，
测试直接喂一个 argv 列表进去。

---

## 7.8 `re` 正则表达式

### 原始字符串：`r"..."`

```python
"\d"      # 这是字符串 '\d'？不，\d 不是合法转义，Python 3.12+ 会警告
r"\d"     # 明确的「反斜杠 + d」两个字符
```

**写正则一律用 `r"..."`**。理由：

- `"\b"` 是**退格符**，`r"\b"` 才是「词边界」——这是一个非常经典的 bug
- `"\n"` 是换行，`r"\n"` 才是「正则里的换行符」（虽然等价，但语义不同）
- 不用记「哪些转义序列 Python 已经占用了」

### 常用元字符速查

| 模式 | 含义 | 注意 |
|------|------|------|
| `.` | 任意字符（**默认不含换行**） | 要含换行加 `re.DOTALL` |
| `\d` `\D` | 数字 / 非数字 | `\d` 匹配 Unicode 数字（含全角） |
| `\w` `\W` | 单词字符 / 非单词字符 | 含下划线，**含中文** |
| `\s` `\S` | 空白 / 非空白 | 含 `\t\n\r\f\v` 和全角空格 |
| `[abc]` `[^abc]` | 字符集 / 补集 | `[a-z]` 范围 |
| `^` `$` | 行首 / 行尾 | 多行模式加 `re.MULTILINE` |
| `*` `+` `?` | 0+ / 1+ / 0或1 | 默认贪婪 |
| `{n}` `{n,}` `{n,m}` | 精确次数 | |
| `*?` `+?` `??` `{n,m}?` | **非贪婪**版本 | 见下 |
| `(...)` | 捕获分组 | 会出现在 `groups()` 里 |
| `(?:...)` | 非捕获分组 | 只分组不捕获，更快 |
| `(?P<name>...)` | **命名分组** | 用 `group("name")` 取 |
| `(?=...)` `(?!...)` | 前瞻（不消耗字符） | |
| `\|` | 或 | |
| `\b` | 词边界 | 必须用 `r"\b"` |

### 五个核心函数

```python
import re

text = "2024-03-01 ERROR 磁盘满了"

re.match(r"\d+", text)        # 从**开头**匹配，失败返回 None
re.search(r"\d+", text)       # 在**任意位置**找第一个匹配
re.fullmatch(r"\d+", text)    # 整个字符串必须完全匹配
re.findall(r"\d+", text)      # 找出**所有**匹配，返回字符串列表
re.finditer(r"\d+", text)     # 同上，但返回 Match 对象的迭代器
```

**`match` vs `search` 是最容易搞混的一对**：

```python
re.match(r"ERROR", text)      # None！因为 text 不是以 ERROR 开头
re.search(r"ERROR", text)     # <Match>，找到了
```

> **记忆法**：`match` 只在**开头**试一次，`search` 会**扫描全串**。
> 想知道「是不是整串都匹配」用 `fullmatch`。

**`findall` 在有分组时会变行为**：

```python
re.findall(r"\d+", "a1b22")                  # ['1', '22']
re.findall(r"(\d)(\d)", "a12b34")            # [('1','2'), ('3','4')]  多个分组 -> 元组列表
re.findall(r"(\d)\d", "a12b34")              # ['1', '3']  一个分组 -> 只返回分组内容！
```

**一个分组时 `findall` 只返回分组里的内容，不是整个匹配**。
这是无数 bug 的来源。需要整个匹配就用 `finditer` + `m.group(0)`。

### 替换与切分

```python
re.sub(r"\d+", "#", "a1b22c333")             # 'a#b#c#'
re.sub(r"\d+", "#", "a1b22c333", count=1)    # 'a#b22c333'
re.sub(r"(\w+)@(\w+)", r"\2@\1", "a@b")      # 'b@a'  用 \1 \2 反向引用

re.split(r"[,;]\s*", "a, b;c")               # ['a', 'b', 'c']
re.split(r"\s+", "a   b  c")                 # ['a', 'b', 'c']
```

**`re.sub` 的替换串里 `\1` / `\g<name>` 是反向引用**。
如果替换串是用户提供的、可能含反斜杠，用**函数**代替字符串：

```python
re.sub(r"\d+", lambda m: str(int(m.group()) * 2), "a1b2")   # 'a2b4'
```

### 命名分组

```python
LOG_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>[A-Z]+)\s+"
    r"(?P<msg>.*)$"
)

m = LOG_RE.match("2024-03-01 12:00:05 ERROR 任务 43 失败")
m.group("level")     # 'ERROR'
m.groupdict()        # {'date': ..., 'time': ..., 'level': ..., 'msg': ...}
m.group(3)           # 'ERROR'（也能按序号取）
```

**命名分组在超过 2 个字段时必须用**。`m.group(7)` 这种代码，
三个月后连你自己都不知道是哪个字段。

`groupdict()` 直接给你一个 dict，这是解析日志/配置行的标准做法。

### 贪婪 vs 非贪婪

```python
re.match(r"<.*>",  "<a><b>").group()     # '<a><b>'   贪婪：吃到最后一个 >
re.match(r"<.*?>", "<a><b>").group()     # '<a>'      非贪婪：吃到第一个 >
re.match(r"<.+?>", "<a><b>").group()     # '<a>'
```

**贪婪是默认，而且是正确的默认**。规则：

- `*` `+` `?` `{n,m}` 默认**尽可能多**地吃
- 加 `?` 变成**尽可能少**地吃
- 但正则引擎仍然会**为了整体匹配成功而回溯**

```python
re.match(r"<.*>", "<a> <b>").group()    # '<a> <b>'   不是 '<a>'
```

**性能警告：嵌套量词会指数爆炸。**

```python
re.match(r"(a+)+b", "a" * 30)      # 灾难性的回溯，可能要跑几分钟
```

真实项目里解析**用户可控的字符串**时，这种正则就是 DoS 攻击面（ReDoS）。
防御手段：

- 避免嵌套的量词 `(x+)+`
- 用 `(?:...)` 减少不必要的分组
- 能不用正则就不用（`str.split` 通常够）
- 给正则加长度上限（先 `if len(text) > 10000: reject`）

### `re.compile` 预编译

```python
# 慢：每次调用都要重新编译（re 模块内部有缓存，但缓存容量只有 512 个）
for line in huge_log:
    m = re.match(r"(\d+)-(\d+)", line)

# 快：编译一次，反复使用
PATTERN = re.compile(r"(\d+)-(\d+)")
for line in huge_log:
    m = PATTERN.match(line)
```

**规则**：

- 正则出现在**循环里**或**被调用多次** -> 模块级 `re.compile` 一次
- 正则只用一次 -> 直接用 `re.search(...)`，别为编译单开一行

`re` 模块内部对最近用过的 512 个模式有缓存，
所以「忘了编译」在简单场景下不会明显变慢。
但显式编译还能**给正则起个名字**（`EMAIL_RE` 比一行天书可读得多），
这才是更大的收益。

---

## 7.9 `datetime`

### 四个类型

```python
from datetime import date, datetime, time, timedelta

date(2024, 3, 1)                        # 2024-03-01     只有日期
time(12, 30, 45)                        # 12:30:45       只有时间
datetime(2024, 3, 1, 12, 30, 45)        # 两者都有
timedelta(days=1, hours=2, minutes=30)  # 一个时长
```

它们都是**不可变**的，所有运算返回新对象。

```python
datetime.now()          # 当前本地时间（naive）
datetime.now(timezone.utc)   # 当前 UTC 时间（aware）
date.today()            # 今天
time.time()             # 不是这里的东西！那是 time 模块的 Unix 时间戳
```

> `datetime.time` 和 `time` 模块是两个完全无关的东西。
> 你在 `import datetime` 之后写 `time()` 会拿到 `datetime.time`。
> **别名导入能避免这个坑**：`from datetime import datetime as dt`。

### naive vs aware：本模块最重要的一节

- **naive（幼稚）**：`tzinfo is None`，不知道自己是哪个时区的时间
- **aware（有意识）**：`tzinfo` 不为 `None`，知道自己带偏移量

```python
naive = datetime(2024, 3, 1, 12, 0)                    # tzinfo=None
aware = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)

naive.tzinfo        # None
aware.tzinfo        # datetime.timezone.utc
aware.utcoffset()   # timedelta(0)
```

**为什么推荐 aware**：

**① naive 的运算结果取决于你的想象，而程序没有想象力。**

```python
naive + timedelta(days=1)     # 加 24 小时？还是加一个「日历天」？
```

夏令时切换的那一天，一个「日历天」可能是 23 或 25 小时。
naive 永远按 24 小时算，于是在有 DST 的地区就会错一小时。

**② naive 和 aware 不能直接相减。**

```python
naive - aware
# TypeError: can't subtract offset-naive and offset-aware datetimes
```

这是个**好事**——Python 逼你明确说出「这两个时间是不是同一个参照系」。
很多语言的日期库会让你算出一个静默错误的结果。

**③ 跨时区比较必须 aware。**

```python
# 同一个时刻，两种表示
utc_time = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)
beijing = utc_time.astimezone(timezone(timedelta(hours=8)))    # 20:00+08:00

utc_time == beijing          # True！同一时刻，aware 的比较看的是绝对时间
```

如果两个都是 naive，Python 只会比较字面数字，`12:00` 和 `20:00` 就是不等——
**但它们在物理上是同一时刻**。

**实践规则**：

> **程序内部一律用 aware 的 UTC 时间，只在展示给用户时才转成本地时区。**

```python
from datetime import datetime, timedelta, timezone

CST = timezone(timedelta(hours=8))          # 中国标准时间，无夏令时

def now_utc() -> datetime:
    return datetime.now(timezone.utc)

def to_local(dt: datetime) -> datetime:
    return dt.astimezone(CST)

def to_iso(dt: datetime) -> str:
    return dt.isoformat()                   # '2024-03-01T12:00:00+00:00'
```

> **`timezone.utc` 和 `ZoneInfo("Asia/Shanghai")` 的区别**：
> `timezone(timedelta(hours=8))` 是一个**固定偏移**，永远 +8。
> `zoneinfo.ZoneInfo("Asia/Shanghai")` 带**完整的时区规则历史**，
> 能正确处理「1986 年中国实行过夏令时」这种历史事件。
> 只做当前时间的换算，固定偏移够用；要做历史日期计算，用 `zoneinfo`。

### 格式化：`strftime` 和 `strptime`

```python
dt = datetime(2024, 3, 1, 12, 30, 45, tzinfo=timezone.utc)

# datetime -> str
dt.strftime("%Y-%m-%d %H:%M:%S")        # '2024-03-01 12:30:45'
dt.strftime("%Y-%m-%dT%H:%M:%S%z")      # '2024-03-01T12:30:45+0000'
dt.isoformat()                          # '2024-03-01T12:30:45+00:00'  <- 首选

# str -> datetime
datetime.strptime("2024-03-01 12:30:45", "%Y-%m-%d %H:%M:%S")
datetime.strptime("2024-03-01T12:30:45+0000", "%Y-%m-%dT%H:%M:%S%z")
```

**`strftime` / `strptime` 记忆法**：
**f** = format（格式化输出），**p** = parse（解析输入）。
两个函数用的是**同一套格式代码**。

常用格式代码：

| 代码 | 含义 | 示例 |
|------|------|------|
| `%Y` | 四位年 | 2024 |
| `%m` | 两位月 | 03 |
| `%d` | 两位日 | 01 |
| `%H` `%M` `%S` | 时 分 秒（24 小时制） | 12 30 45 |
| `%j` | 一年中的第几天 | 061 |
| `%A` `%a` | 星期几全称/缩写 | Friday / Fri |
| `%B` `%b` | 月份全称/缩写 | March / Mar |
| `%z` | UTC 偏移 | +0800 |
| `%Z` | 时区名 | UTC / CST |
| `%%` | 字面量 % | % |

> **`%Y-%m-%d` 里的 `-` 是字面量**，`%` 才是转义起始符。
> `"%Y年%m月%d日"` 也能正常工作，中文不需要转义。

**`strptime` 的两个坑**：

1. **它很慢。** 内部是纯 Python 的逐字符扫描。
   解析几十万行日志时，`datetime.strptime` 会成为瓶颈。
   固定格式用 `datetime.fromisoformat()`（3.11+ 支持大部分 ISO 8601），
   它是 C 实现的，快得多。
2. **它不会替你猜。** 格式串必须和输入**逐字符对应**，
   多一个空格都会 `ValueError`。

**往返一致性**：

```python
dt = datetime.now(timezone.utc)
dt == datetime.strptime(dt.isoformat(), "%Y-%m-%dT%H:%M:%S%z")
# 不一定为 True！isoformat 会输出微秒（如果非零），
# strptime 的格式里没有 %f，微秒就丢了。
```

**要完整往返，用 `%Y-%m-%dT%H:%M:%S.%f%z`，或者两边都用 `isoformat()` / `fromisoformat()`。**
对于「存下来再读回来」的场景，**首选 ISO 格式**，
它是标准、可排序、可读、且无歧义。

### 时间戳转换

```python
# datetime -> 时间戳（Unix epoch，秒，float）
aware.timestamp()                     # 1709294400.0
datetime.now(timezone.utc).timestamp()

# 时间戳 -> datetime
datetime.fromtimestamp(1709294400.0, tz=timezone.utc)   # 推荐
datetime.fromtimestamp(1709294400.0)                    # 本地时区的 naive

# 只有 date 的时候
date(2024, 3, 1).toordinal()          # 从公元 1 年 1 月 1 日算起的天数
```

> **`timestamp()` 对 naive datetime 的行为**：按**本地时区**解释。
> 也就是说，同一段代码在北京和纽约会得到不同的时间戳。
> **这就是为什么所有时间戳转换都应该用 aware datetime。**
>
> `fromtimestamp()` 同理：不传 `tz=` 得到的是本地时区的 naive 时间。

### 时间差

```python
d1 = date(2024, 3, 1)
d2 = date(2024, 3, 10)
(d2 - d1).days          # 9
(d2 - d1).total_seconds()   # 777600.0

dt2 - dt1               # timedelta 对象
dt2 > dt1               # 可以直接比较

timedelta(days=30, hours=6) / timedelta(days=1)    # 30.25  用除法算天数
```

**注意 `date` 相减得到的是 `timedelta`，不是整数**。
想直接拿天数用 `.days`。

---

## 7.10 `collections` 补充 + `os` / `sys` / `subprocess`

### `collections` 再补三件套

模块 02 讲过 `Counter` / `defaultdict` / `deque`，这里只补充易忘的点。

```python
from collections import Counter, defaultdict, deque, OrderedDict, namedtuple

# Counter：计数 + 取前 N + 加减
words = Counter("abracadabra")
words.most_common(2)             # [('a', 5), ('b', 2)]
words.total()                    # 11                     3.10+
words - Counter("ab")            # 支持集合运算（负数和 0 会被丢掉）

# defaultdict：分组的标准工具
groups = defaultdict(list)
for name, dept in records:
    groups[dept].append(name)    # 不用先判 key 存在

# 注意：访问不存在的键会**创建**它！
groups["不存在"]                 # 不报错，插入 []，len(groups) 变了
# 只想取值不想插入，用普通 dict 或 groups.get(k, [])

# deque：双端队列，两端 O(1)；maxlen 实现「只保留最近 N 条」
recent = deque(maxlen=5)
for i in range(10):
    recent.append(i)             # 满了会自动从左边挤掉旧的
list(recent)                     # [5, 6, 7, 8, 9]
```

**`defaultdict` 的 `default_factory` 必须是可调用对象**，
写 `defaultdict([])` 会 `TypeError`，要写 `defaultdict(list)`。
理由和 `dataclasses.field(default_factory=...)` 一样：**可变默认值必须每次新建**。

### `os`：环境与进程

```python
import os

os.environ["MY_VAR"]             # 读环境变量，不存在会 KeyError
os.environ.get("MY_VAR", "默认")  # 推荐：给默认值
os.getenv("MY_VAR", "默认")       # 等价，更短

os.getpid()                      # 当前进程 ID
os.cpu_count()                   # CPU 核数（决定开几个进程）
os.linesep                       # 平台换行符
os.name                          # 'nt' / 'posix'
os.sep                           # '\\' / '/'

os.rename(src, dst)              # 重命名/移动（同磁盘）
os.replace(src, dst)             # 覆盖式重命名
os.remove(path)                  # 删文件
os.makedirs(path, exist_ok=True) # 递归建目录（但 pathlib 更好用）
```

> **路径操作一律用 `pathlib`（模块 06），`os` 只用来读环境变量和进程信息。**
> `os.path` 那套 API 是历史包袱，新代码不要用。

### `sys`：解释器相关

```python
import sys

sys.argv                 # 命令行参数列表，argv[0] 是脚本名
sys.executable           # 当前 Python 解释器的完整路径
sys.version_info         # (3, 14, 7, 'final', 0)，比较用 >= (3, 11)
sys.platform             # 'win32' / 'linux' / 'darwin'
sys.path                 # 模块搜索路径（可以 append 来加自己的目录）
sys.stdout / sys.stderr  # 标准输出/错误流（可以替换，比如重定向到文件）
sys.getrecursionlimit()  # 递归深度上限，默认 1000
sys.maxsize              # 平台指针能表示的最大整数
sys.exit(1)              # 退出，1 表示失败（raise SystemExit(1) 的语法糖）
```

**用 `sys.executable` 而不是硬编码 `"python"`**：

```python
import subprocess, sys

# 错：可能拿到另一个 Python 环境
subprocess.run(["python", "-c", "import sys; print(sys.version)"])

# 对：一定是当前正在运行的这个解释器（虚拟环境里尤其重要）
subprocess.run([sys.executable, "-c", "import sys; print(sys.version)"])
```

**`sys.exit()` 抛的是 `SystemExit`**，它继承 `BaseException` 而不是
`Exception`（模块 06 讲过）——所以 `except Exception` 拦不住它，这是故意的。

### `subprocess`：调用外部程序

```python
import subprocess

result = subprocess.run(
    ["git", "rev-parse", "HEAD"],   # 参数用列表！不要拼字符串
    capture_output=True,            # 抓 stdout / stderr
    text=True,                      # 返回 str 而不是 bytes
    encoding="utf-8",               # text=True 时的编码，Windows 上必须写
    check=False,                    # 不要因非零退出码抛异常
    timeout=10,                     # 超时保护
    cwd=None,                       # 工作目录
)
result.returncode     # 0 成功
result.stdout         # 标准输出（str）
result.stderr         # 标准错误（str）
```

**四条铁律**：

1. **参数用列表，不要用字符串 + `shell=True`。**
   ```python
   subprocess.run(f"ls {user_input}", shell=True)     # 命令注入漏洞！
   subprocess.run(["ls", user_input])                 # 安全
   ```
   `shell=True` 会把字符串交给系统 shell 解析，
   用户输入里的 `; rm -rf /` 会真的被执行。
   **只有在需要 shell 特性（管道、通配符、环境变量展开）时才用字符串形式**。
2. **Windows 上一定要 `encoding="utf-8"`**（或者 `errors="replace"`）。
   子进程的输出默认按 locale 解码，中文 Windows 上是 GBK，
   碰到 UTF-8 输出直接炸。
3. **加 `timeout=`**。外部程序卡住时，你的程序会一起卡住。
   超时会抛 `subprocess.TimeoutExpired`。
4. **`check=True` 或手工检查 `returncode`**。
   静默忽略失败返回码是「脚本跑完了但什么都没做」的经典原因。

---

## 7.11 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| 以为注解会校验 | `x: int = "abc"` 静默通过 | 用 mypy / pydantic |
| `List[int]` vs `list[int]` | 老代码风格不统一 | 新代码用 `list[int]` |
| 参数类型写 `list[T]` | 调用方被迫转成 list | 写 `Iterable[T]` / `Sequence[T]` |
| 滥用 `Any` | 类型检查全废 | 只在真正异构处用 |
| `Protocol` 加 `isinstance` | TypeError | 加 `@runtime_checkable` |
| 以为 `runtime_checkable` 查签名 | 签名不对也通过 | 只查方法名，别当校验用 |
| `NotRequired` + future annotations | 可选键被当成必填 | 改用 `total=False` 继承 |
| `dataclass` 可变默认值 | TypeError | `field(default_factory=list)` |
| `defaultdict([])` | TypeError | `defaultdict(list)` |
| 日志用 f-string | 热路径上拖慢程序 | `logger.info("%s", x)` |
| `logging.warning(...)` | 走根 logger，没法按模块过滤 | `getLogger(__name__)` |
| 只配 logger 不配 handler | 日志不输出 / 输出两次 | 两级 level 都要设 |
| 测试完不 removeHandler | 日志重复 | 测完摘掉 handler |
| `except` 里 `logger.error(str(e))` | 没有 traceback | `logger.exception(...)` |
| 可选参数写 `required=True` | 帮助里显示 `[--x]` 但必填 | 改成位置参数 |
| `dest` 忘了写给 subparsers | 不知道用了哪个子命令 | `add_subparsers(dest="cmd")` |
| 正则不用 `r""` | `\b` 变成退格 | 一律 `r"..."` |
| `re.match` 当 `search` 用 | 明明有却返回 None | `match` 只匹配开头 |
| `findall` 带一个分组 | 只返回分组内容 | 用 `finditer` + `group(0)` |
| 循环里 `re.match` | 每次重新编译 | `re.compile` 提到循环外 |
| `(a+)+` 嵌套量词 | ReDoS，指数回溯 | 改写正则 + 限长 |
| naive / aware 混算 | TypeError 或静默错 | 内部统一用 aware UTC |
| `timestamp()` 用在 naive 上 | 结果随机器时区变 | 永远用 aware |
| `strptime` 解析海量日志 | 慢 | `datetime.fromisoformat` |
| `subprocess` 用 `shell=True` | 命令注入 | 参数传列表 |
| `subprocess` 不写 encoding | Windows 上乱码 | `text=True, encoding="utf-8"` |

---

## 7.12 本模块文件

| 文件 | 内容 |
|------|------|
| `README.md` | 你正在看的文件 |
| `demo.py` | 10 节可运行示例，覆盖 7.1~7.10 |
| `exercises.py` | 9 道练习 |
| `solutions.py` | 参考答案 + 「常见错误写法错在哪」 |

### 强烈建议的学法

1. 跑 `demo.py`。**重点看 `demo_annotations()` 和 `demo_logging()`**，
   前者会让你第一次真正看清「注解在运行时是什么」。
2. 装个 mypy（`pip install mypy`），在 `07_stdlib_typing/` 目录下跑：
   ```powershell
   mypy solutions.py --ignore-missing-imports
   ```
   看它报什么错，然后再想想「为什么运行起来完全没问题」。
3. 做 `exercises.py`。**q2（Protocol）和 q6（logging）是重点**，
   它们对应的是「鸭子类型的类型化表达」和「可观测性」两个工程核心问题。
4. 对照 `solutions.py`。

---

## 7.13 延伸阅读

- [PEP 484 · Type Hints](https://peps.python.org/pep-0484/) —— 一切的起点
- [PEP 544 · Protocols: Structural subtyping](https://peps.python.org/pep-0544/) —— `Protocol` 的设计文档
- [PEP 585 · Type Hinting Generics In Standard Collections](https://peps.python.org/pep-0585/) —— 为什么是 `list[int]`
- [PEP 649 · Deferred Evaluation Of Annotations](https://peps.python.org/pep-0649/) —— **3.14 的核心变化，必读**
- [PEP 695 · Type Parameter Syntax](https://peps.python.org/pep-0695/) —— `def f[T](...)` 新语法
- [PEP 557 · Data Classes](https://peps.python.org/pep-0557/) —— 里面明确提到了 attrs 的影响
- [Python 官方文档 · `logging` 的做法与陷阱](https://docs.python.org/zh-cn/3/howto/logging.html)
- [Python 官方文档 · `re` 正则表达式语法](https://docs.python.org/zh-cn/3/library/re.html)
- [Python 官方文档 · `datetime`](https://docs.python.org/zh-cn/3/library/datetime.html) —— 开头「aware 和 naive 对象」那一段值得反复读
- [正则表达式 30 分钟入门教程](https://deerchao.cn/tutorials/regex/regex.htm) —— 中文里写得最清楚的一篇
- [mypy 官方文档](https://mypy.readthedocs.io/) —— 尤其看「Common Issues」那一章
