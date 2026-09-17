# 模块 04 · 面向对象与数据模型

> **目标**：你已经会用 Java / C++ 写 OOP 了，所以这个模块**不教你什么是类**。
> 它只讲一件事：Python 的对象模型和 Java / C++ 有哪些**根本性差异**，
> 以及这些差异会怎样让你写出「能跑但很别扭」的代码。
>
> 一句话预告：**Python 里没有私有成员，没有接口，没有虚函数表，
> 方法就是普通函数，「面向对象」只是「一堆函数共享第一个参数」的语法糖。**

---

## 4.1 `self` 的本质：方法是普通函数

### 先看结论

```python
class Counter:
    def __init__(self, n: int = 0) -> None:
        self.n = n

    def bump(self) -> int:
        self.n += 1
        return self.n
```

在 Java 里，`bump` 是「属于 Counter 类的一个方法」，`this` 是隐式注入的。
在 Python 里，真实情况是：

```python
Counter.bump          # <function Counter.bump at 0x...>   就是个普通函数
c = Counter()
c.bump                # <bound method Counter.bump of <Counter object at 0x...>>
```

`c.bump` 是一个**绑定方法（bound method）**对象，它同时记住了两样东西：

```python
c.bump.__func__      # 原来的那个函数 <function Counter.bump>
c.bump.__self__      # 绑定到的实例 c
```

所以：

```python
c.bump()             # 等价于 Counter.bump(c)
Counter.bump(c)      # 完全一样，你可以自己写
```

**`self` 不是关键字**，它只是一个约定俗成的形参名。下面这段代码完全合法：

```python
class Weird:
    def method(banana):      # 合法，但会被同事打
        return banana
```

### 方法、函数、绑定方法的关系

```
 类字典里的东西                     访问方式               得到什么
 ─────────────────────────────────────────────────────────────────
 def f(self)           ──►   Cls.f            ──►   普通函数（要自己传 self）
 def f(self)           ──►   Cls().f          ──►   绑定方法（self 已经绑好）
 @classmethod def f    ──►   Cls.f / Cls().f  ──►   绑定到「类」的方法
 @staticmethod def f   ──►   Cls.f / Cls().f  ──►   就是普通函数，不绑定
```

**这就是描述符协议（descriptor protocol）**：函数对象实现了 `__get__`，
所以当它作为类属性被访问时，会「变形」成绑定方法。第 6 节会看到
`property` 用的也是同一套机制。

### 为什么 `self` 要显式写

因为 Python 的哲学是「显式优于隐式」。代价是多打几个字，
好处是你**永远能一眼看出**：这个方法会不会改对象状态？它拿到的到底是谁？

顺带一提，C++ 里你也能写 `obj.method()` 和 `Cls::method(obj)`，
Python 只是把后者变成了日常写法。

> **一个实用的副产品**：因为 `a.f()` 就是 `Cls.f(a)`，
> 所以把一个方法当成回调传出去时，**绑定的 `self` 会一起带走**：
>
> ```python
> button.on_click(counter.bump)    # 不需要 lambda，self 已经绑好了
> ```

---

## 4.2 类属性 vs 实例属性：共享陷阱

### 查找顺序

读 `obj.attr` 时，Python 按这个顺序找：

```
   1. 类型(obj).__mro__ 里每个类的 __dict__（含 data descriptor，如 property）
   2. obj.__dict__  （实例自己的属性）
   3. 类型的 __mro__ 里的非 data descriptor（普通函数、classmethod）
   4. 找不到 -> __getattr__（如果定义了）
   5. 还找不到 -> AttributeError
```

（第 1 步优先于第 2 步是给 `property` 这类「数据描述符」让路，
细节见《流畅的 Python》第 20 章。）

**写** `obj.attr = x` 时，规则简单得多：**永远写进 `obj.__dict__`**，
除非这个属性在类上是个 data descriptor（比如带 setter 的 `property`）。

### 陷阱：类属性是可变对象时

```python
class Team:
    members = []           # 类属性，整个类共享同一个列表！

    def add(self, name):
        self.members.append(name)     # 注意：这是「改内容」，不是「赋值」
```

```python
a = Team()
b = Team()
a.add("张三")
print(b.members)          # ['张三']  ← b 也中招了
print(a.members is b.members)   # True
```

**为什么**：`self.members.append(...)` 先做**查找**，找到的是类属性那个列表，
然后就地修改它。没有任何一步创建了 `self.members` 这个实例属性。

**正解**：在 `__init__` 里创建实例自己的副本：

```python
class Team:
    def __init__(self) -> None:
        self.members: list[str] = []      # 每个实例一份
```

### 对比：`self.x = ...` 会创建实例属性

```python
class Team:
    count = 0

    def __init__(self) -> None:
        self.count += 1        # 展开是 self.count = self.count + 1
                               # 右值读的是类属性 0，左值写的是实例属性
```

```python
a, b = Team(), Team()
print(Team.count)     # 0     类属性从没被改过
print(a.count)        # 1
print(b.count)        # 1
```

**这是从 Java 转过来的人最容易踩的坑**：Java 里 `count++` 改的是静态字段
（除非用 `this.count`），Python 里 `self.count += 1` 第一次执行必然创建实例属性。

要真的改类属性，得写 `type(self).count += 1` 或 `Team.count += 1`。

### 判断某个属性是不是类属性

```python
vars(Team)                        # 类的 __dict__，看得到 'members' / 'count'
"members" in vars(Team)           # True  -> 是类属性
"members" in vars(a)              # False -> 实例字典里没有，说明是共享的
```

养成习惯：**看到 `self.x.方法()` 就要警觉**——你确定 `x` 是实例自己的吗？

---

## 4.3 继承、`super()` 与 MRO

### 基本继承

```python
class Animal:
    def __init__(self, name: str) -> None:
        self.name = name

    def speak(self) -> str:
        return "..."

class Dog(Animal):
    def __init__(self, name: str, breed: str) -> None:
        super().__init__(name)     # 显式调用父类构造器
        self.breed = breed

    def speak(self) -> str:
        return f"{self.name} 汪"
```

和 Java 的差别：

1. **没有 `@Override`**，也没有编译期检查。写错方法名 = 静默多了一个新方法。
2. **所有方法都是虚方法**，都走动态分派，不需要 `virtual` 关键字。
   想「禁止重写」做不到（只能靠约定加注释）。
3. **`super()` 不写参数**（Python 3 的语法糖），等价于 `super(Dog, self)`。

### `super()` 到底做了什么

这是最关键的一点：

> **`super()` 返回的不是「父类」，而是「MRO 链上，当前类之后的那一段」。**

`super().speak()` 的含义是：「从 MRO 里我后面那个类开始，找第一个有 `speak` 的」。

### MRO 与 C3 线性化

`Cls.__mro__` 是一个元组，把方法查找顺序**拉平成一维**。

```python
class A: pass
class B(A): pass
class C(A): pass
class D(B, C): pass

print([c.__name__ for c in D.__mro__])
# ['D', 'B', 'C', 'A', 'object']
```

**C3 线性化的三条规则**（记住直觉就够了）：

1. 子类永远排在父类前面
2. 多个父类按声明顺序排（`class D(B, C)` 里 B 在 C 前面）
3. 单调性：如果 X 在某个线性化里排在 Y 前，那在所有合并结果里 X 都在 Y 前

Python 用 C3 而不是「深度优先」是因为深度优先在菱形继承下会破坏第 3 条。
如果两个类的声明顺序**无法**同时满足这三条，Python 直接拒绝定义类：

```python
class X: pass
class Y: pass
class Z(X, Y): pass
class W(Y, X): pass
class Bad(Z, W): pass     # TypeError: Cannot create a consistent MRO
```

> **为什么用 C3 而不是保留 Java 的 `A extends B`？**
> 因为 Python 允许多重继承，而多重继承必须有办法解决菱形问题。
> Java 选择禁止多继承 + 用接口绕开，Python 选择用 MRO 正面解决。
> 代价是 MRO 得自己想清楚，收益是 Mixin 这种模式特别好用。

### 协作式继承（cooperative inheritance）

菱形继承下，如果每个类都用 `super()` 而不是硬写 `Parent.method(self)`，
整条链上的方法**只会被调用一次**：

```python
class A:
    def who(self): return "A"
    def trace(self): return f"A({self.who()})"

class B(A):
    def who(self): return "B"
    def trace(self): return "B->" + super().trace()

class C(A):
    def who(self): return "C"
    def trace(self): return "C->" + super().trace()

class D(B, C):
    def who(self): return "D"
    def trace(self): return "D->" + super().trace()

print(D().trace())    # D->B->C->A(D)
```

注意最后是 `A(D)` 而不是 `A(C)`：`self` 从头到尾都是那个 `D` 实例，
所以 `self.who()` 走的是完整的 MRO，命中的是 `D.who`。
**`super()` 只影响「从哪继续找」，不影响 `self` 是谁。**

如果把 `super().trace()` 换成 `A.trace(self)`，`C` 的 `trace` 就被跳过了——
**这就是协作继承的整个要点**。

### Mixin 模式

多重继承在 Python 里最常见的正当用法是 Mixin：一个只提供**一小块横切能力**
的类，不参与 `is-a` 关系。

```python
class JsonMixin:
    def to_json(self) -> str:
        import json
        return json.dumps(vars(self), ensure_ascii=False)

class User(JsonMixin):        # 读作「User 有 JSON 能力」，不是「User 是一种 JsonMixin」
    def __init__(self, name: str) -> None:
        self.name = name
```

约定：Mixin 类名以 `Mixin` 结尾，`__init__` 一律用 `*args, **kwargs` 透传。

---

## 4.4 魔术方法（dunder methods）

「魔术方法」是 Python 数据模型的钩子：**你实现它们，语法就为你服务**。

| 语法 | 背后的调用 | 备注 |
|------|-----------|------|
| `obj()` | `type(obj).__call__(obj)` | 让实例像函数一样可调用 |
| `len(obj)` | `obj.__len__()` | 返回值必须是 `int` 且 `>= 0`，否则 `TypeError` |
| `obj[k]` | `obj.__getitem__(k)` | 顺带让对象可迭代（旧协议） |
| `obj[k] = v` | `obj.__setitem__(k, v)` | |
| `k in obj` | `obj.__contains__(k)` | 没实现时退化成遍历 `__iter__` |
| `repr(obj)` | `obj.__repr__()` | **给开发者看**，调试器的显示 |
| `str(obj)` | `obj.__str__()` | **给用户看**，`print` 的输出 |
| `obj == other` | `obj.__eq__(other)` | 返回 `NotImplemented` 表示「我不懂」 |
| `hash(obj)` | `obj.__hash__()` | 必须和 `__eq__` 一致 |
| `obj + other` | `obj.__add__(other)` | 反向版本 `__radd__` |
| `obj * 3` | `obj.__mul__(3)` | `3 * obj` 走 `__rmul__` |
| `abs(obj)` | `obj.__abs__()` | |
| `bool(obj)` | `obj.__bool__()` | 没实现则退回 `__len__` |
| `with obj:` | `obj.__enter__()` / `__exit__()` | 模块 05 细讲 |
| `for x in obj` | `obj.__iter__()` | 模块 05 细讲 |

### `__repr__` 和 `__str__` 的分工

```python
class Money:
    def __init__(self, amount, currency="CNY"):
        self.amount = amount
        self.currency = currency

    def __repr__(self) -> str:
        # 目标：eval(repr(obj)) == obj —— 至少让人看出怎么造一个出来
        return f"Money({self.amount!r}, {self.currency!r})"

    def __str__(self) -> str:
        return f"{self.amount:.2f} {self.currency}"
```

```python
m = Money(3.5)
print(repr(m))    # Money(3.5, 'CNY')   给开发者
print(str(m))     # 3.50 CNY            给用户
print(m)          # 3.50 CNY            print 走 __str__
print([m])        # [Money(3.5, 'CNY')]  容器里的元素走 __repr__！
```

**规则**：
- 只实现一个的话，实现 `__repr__`（`__str__` 会自动回退到它，反之不会）
- 列表/字典打印元素时用的是 `__repr__`——这就是为什么调试时 `__repr__` 更重要
- 如果实在写不出 `eval` 得回去的 `__repr__`，退而求其次写 `<Money 3.5 CNY>` 这种

**默认的 `__repr__` 是灾难**：

```python
<__main__.Money object at 0x7f8b1c2d3e40>     # 完全没用，地址每次都不一样
```

### `__eq__` 必须处理「不是同类」的情况

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, Money):
        return NotImplemented        # 注意：不是 False！
    return (self.amount, self.currency) == (other.amount, other.currency)
```

**为什么是 `NotImplemented` 而不是 `False`**：

`a == b` 的真实流程是：

```
   1. 尝试 a.__eq__(b)
   2. 如果返回 NotImplemented，尝试 b.__eq__(a)（反射）
   3. 都返回 NotImplemented -> 退回身份比较 a is b  -> False
```

如果第 1 步就返回 `False`，你就**剥夺了对方类型解释这次比较的机会**。
`1 == True` 能成立、`Decimal("1") == 1` 能成立，靠的都是这套协商机制。

`NotImplemented` 是个**内置单例**（不是 `NotImplementedError`，那个是异常）。

### 运算符重载的完整套路

以「向量 + 标量乘」为例：

```python
class Vec:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __add__(self, other):                    # v + other
        if not isinstance(other, Vec):
            return NotImplemented
        return Vec(self.x + other.x, self.y + other.y)

    def __radd__(self, other):                   # other + v（other 没处理时）
        return self.__add__(other)

    def __mul__(self, k):                        # v * 3
        if not isinstance(k, (int, float)):
            return NotImplemented
        return Vec(self.x * k, self.y * k)

    def __rmul__(self, k):                       # 3 * v
        return self.__mul__(k)

    def __iadd__(self, other):                   # v += other
        self.x += other.x                        # 就地改，返回 self
        self.y += other.y
        return self
```

**`__iadd__` 的坑**：返回 `self` 就是就地修改（`+=` 会改到别名指向的对象），
返回新对象就是「重新绑定」。模块 01 里 `list` 和 `tuple` 的 `+=` 行为差异，
根源就在这里。**不要为了炫技给不可变对象实现 `__iadd__`。**

**`__hash__` 一旦有了 `__eq__` 就会消失**——下一节细讲。

---

## 4.5 `__eq__` 与 `__hash__` 必须成对修改

### 现象

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other):                 # 只定义了 __eq__
        return isinstance(other, Point) and (self.x, self.y) == (other.x, other.y)

p = Point(1, 2)
{p}                     # TypeError: unhashable type: 'Point'
hash(p)                 # TypeError: unhashable type: 'Point'
```

### 原因

Python 在**类创建时**做了一件事：

> 如果你的类定义了 `__eq__` 却没有定义 `__hash__`，
> 解释器会把 `__hash__` **显式设为 `None`**。

```python
Point.__hash__          # None
```

**为什么这么设计**：哈希和相等的契约是

> **`a == b` 为真 必须推出 `hash(a) == hash(b)`**

默认的 `__hash__` 用的是 `id()`（身份）。如果你改了 `__eq__` 让它按值相等，
却留着按身份算的 `__hash__`，那么两个「相等」的对象会有不同的哈希值——
它们会被放进 dict 的**不同桶**里，于是：

```python
d = {Point(1, 2): "找到了"}
d[Point(1, 2)]        # KeyError！明明相等却查不到
```

**静默的错数据比崩溃可怕得多**，所以 Python 干脆让类变成不可哈希，
强制你显式表态。这是「快速失败」的典范。

### 正确写法

```python
class Point:
    def __init__(self, x, y):
        self.x, self.y = x, y

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self) -> int:
        # 把「参与 __eq__ 的字段」组成元组再哈希，是标准做法
        return hash((self.x, self.y))
```

### 三个必须记住的点

1. **`__eq__` 用到的字段，`__hash__` 也要用到**（且只能用到这些）。
2. **`__hash__` 用到的字段必须不可变**。如果 `x` 事后被改了，
   对象在 set 里就「找不到了」——因为它被放进的桶是按旧哈希算的：

   ```python
   p = Point(1, 2)
   s = {p}
   p.x = 99
   p in s        # False！对象还在 set 里，但按新哈希找不到它了
   ```

   **实践准则：想做字典键 / set 元素，就把它做成不可变的。**
   这就是 `@dataclass(frozen=True)` 和 `tuple` 存在的意义。

3. **不想管哈希就写 `__hash__ = None`**（显式声明「我不可哈希」），
   比留着一个错误的 `__hash__` 好得多。

### 一个真实世界的例子

`list` 是可变的，所以 `__hash__ = None`，不能当字典键。
`tuple` 是不可变的，可以。但**元组里装了列表就又不能哈希了**：

```python
hash((1, 2))            # ok
hash((1, [2]))          # TypeError: unhashable type: 'list'  ← 递归地看元素
```

---

## 4.6 `@property`：计算属性，而不是 getter/setter

### 先看 Python 的立场

Java 的写法：

```java
private double celsius;
public double getCelsius() { return celsius; }
public void setCelsius(double c) { this.celsius = c; }
```

Python 的立场是：**如果你只是转发，就不要写**。

```python
class Temperature:
    def __init__(self, celsius: float) -> None:
        self.celsius = celsius          # 普通公开属性，就这样
```

需要校验、需要计算、需要只读时，**再**升级成 property——
而且**调用方代码一行都不用改**（`t.celsius` 还是 `t.celsius`，不是 `t.celsius()`）。

> 这条「先公开属性，需要时再升级成 property」的路径，就是 Python 没有
> getter/setter 文化的原因：**统一访问原则（uniform access principle）**。
> Java 里你必须提前写 getter，因为字段改方法签名是破坏性变更。

### 语法

```python
class Temperature:
    def __init__(self, celsius: float = 0.0) -> None:
        # 注意：这里走 setter，所以校验自动生效（不要写 self._celsius = celsius）
        self.celsius = celsius

    @property
    def celsius(self) -> float:
        """读：t.celsius"""
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        """写：t.celsius = 30"""
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"温度必须是数字，收到 {type(value).__name__}")
        if value < -273.15:
            raise ValueError(f"低于绝对零度：{value}")
        self._celsius = float(value)

    @property
    def fahrenheit(self) -> float:
        """计算属性：没有 setter，所以是只读的。"""
        return self._celsius * 9 / 5 + 32
```

```python
t = Temperature(25)
t.fahrenheit        # 77.0   直接当属性读，不用写 ()
t.fahrenheit = 100  # AttributeError: property 'fahrenheit' ... has no setter
t.celsius = -300    # ValueError
t.celsius = "hi"    # TypeError
```

### property 背后是描述符

`property` 是一个实现了 `__get__` / `__set__` 的类（data descriptor）。
第 4.2 节说的「data descriptor 优先于实例字典」在这里体现为：

```python
t.__dict__          # {'_celsius': 25.0}   真实数据住在这儿
t.celsius           # 走 property.__get__ 算出来的
```

**所以 `_celsius` 只是个约定（单下划线 = 内部使用），不是私有。**
Python 没有强制访问控制，`t._celsius = -9999` 照样能写进去。
「我们都是在成年人之间约定」——这是 Python 的一贯态度。

### 双下划线（name mangling）也不是私有

```python
class A:
    def __init__(self):
        self.__secret = 1        # 被改写成 self._A__secret

a = A()
a.__secret           # AttributeError
a._A__secret         # 1  ← 只是改了个名，防的是「子类不小心撞名」，不是防访问
```

### `@cached_property`（3.8+）

算一次很贵、之后不该变的属性：

```python
from functools import cached_property

class DataSet:
    def __init__(self, rows):
        self.rows = rows

    @cached_property
    def summary(self):              # 第一次访问才计算，之后存在实例 __dict__ 里
        print("只在第一次算")
        return expensive(self.rows)
```

注意它**需要实例有 `__dict__`**，所以和 `__slots__` 冲突。

---

## 4.7 `@dataclass`：把样板代码交给解释器

### 手写一个值对象有多啰嗦

```python
class Point:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Point(x={self.x!r}, y={self.y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self) -> int:
        return hash((self.x, self.y))
```

### 等价写法

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

一行顶二十行。而且 `frozen=True` 还额外给了你 `__setattr__` 的拦截，
比手写的只读 property 更彻底（连 `p._x = 1` 都不行）。

### 常用参数速查

| 参数 | 效果 |
|------|------|
| `eq=True`（默认） | 生成 `__eq__`（按字段元组比较） |
| `frozen=True` | 生成 `__setattr__`/`__delattr__`，实例不可变；**并自动生成 `__hash__`** |
| `order=True` | 生成 `<` `<=` `>` `>=`（按字段元组，字典序） |
| `slots=True`（3.10+） | 生成 `__slots__`，**注意它会新建一个类对象** |
| `kw_only=True`（3.10+） | 所有字段变成关键字参数 |
| `repr=False` | 不生成 `__repr__`（密码之类的字段） |
| `unsafe_hash=True` | 可变类也强行生成 `__hash__`（想清楚再用） |

### `field()` 的常见用法

```python
from dataclasses import dataclass, field

@dataclass
class Student:
    name: str
    scores: list[int] = field(default_factory=list)     # 可变默认值必须这样做
    #              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ 不要写 = []
    total: int = field(init=False, default=0)           # 不出现在 __init__ 里
    _cache: dict = field(default_factory=dict, repr=False)   # 不参与 repr
```

**为什么不能写 `scores: list = []`**：那个列表在**类定义时创建一次**，
之后所有实例共享（就是 4.2 节的类属性陷阱）。
`dataclasses` 对 `list` / `dict` / `set` 这类会**直接抛 `ValueError`** 拦住你，
但对自定义的可变对象它看不出来——所以养成「可变默认值一律 `default_factory`」的习惯。

```python
@dataclass
class Bad:
    items: list = []        # ValueError: mutable default <class 'list'> for field items
```

### `__post_init__`：字段到手后的加工

```python
@dataclass
class Student:
    name: str
    scores: list[int] = field(default_factory=list)
    average: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        # __init__ 之后被调用，用来做校验或算派生字段
        self.average = sum(self.scores) / len(self.scores) if self.scores else 0.0
```

用 `__post_init__` 做校验时，记得 `frozen=True` 要用 `object.__setattr__`：

```python
@dataclass(frozen=True)
class Range:
    lo: int
    hi: int

    def __post_init__(self) -> None:
        if self.lo > self.hi:
            raise ValueError(f"lo({self.lo}) > hi({self.hi})")
        # frozen 类里要写字段，只能绕过拦截：
        # object.__setattr__(self, "lo", max(self.lo, 0))
```

### `order=True` 的细节

```python
@dataclass(order=True)
class V:
    major: int
    minor: int = 0
    build: str = field(compare=False)     # 不参与比较
```

比较的是**参与比较的字段组成的元组**，字典序。所以要排序才有意义：
把最重要的字段写在最前面。

**注意 `order=True` 不生成 `__hash__`**，所以 `order=True` 的类默认仍然不可哈希
（除非同时 `frozen=True` 或 `eq=False`）。

### 什么时候**不要**用 dataclass

- 类里有大量逻辑、只有一两个字段 —— 手写更清楚
- 需要和 ORM / 框架的元类配合 —— 可能有坑
- 需要精细控制 `__init__` 的签名 —— 手写

---

## 4.8 `@classmethod` / `@staticmethod` / 实例方法

### 三者的区别只看「第一个参数是谁」

```python
class Date:
    def __init__(self, y: int, m: int, d: int) -> None:
        self.y, self.m, self.d = y, m, d

    # 实例方法：第一个参数是实例
    def isoformat(self) -> str:
        return f"{self.y:04d}-{self.m:02d}-{self.d:02d}"

    # 类方法：第一个参数是「类」，不是实例
    @classmethod
    def from_iso(cls, text: str) -> "Date":
        y, m, d = (int(p) for p in text.split("-"))
        return cls(y, m, d)          # 注意是 cls，不是写死的 Date

    # 静态方法：谁都不绑，就是借个命名空间放的普通函数
    @staticmethod
    def is_leap(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
```

### 使用场景

**`@classmethod` 的正经用途只有一个：备用构造器。**

```python
Date.from_iso("2024-01-01")
Date.from_timestamp(1704067200)
Date.today()
```

**关键在 `cls` 而不是 `Date`**：

```python
class DateTime(Date):
    pass

DateTime.from_iso("2024-01-01")     # 返回 DateTime 实例，不是 Date
```

写死 `Date(...)` 的话，子类调用会拿到父类实例——这是很常见的 bug。
**继承场景下 `cls` 才是「正确的多态」。**

**`@staticmethod` 的用途：一个逻辑上属于这个类、但不需要任何状态的小工具。**

```python
Date.is_leap(2024)         # 放在类里只是为了说明「这是日期相关的工具」
```

如果它压根不像这个类的事，**就写成模块级函数**——Python 不强制一切进类。

### 表格对比

| | 第一个参数 | 能访问类属性 | 能访问实例属性 | 典型用途 |
|---|---|---|---|---|
| 实例方法 | `self` | 能（`type(self).x`） | 能 | 绝大多数方法 |
| `@classmethod` | `cls` | 能（`cls.x`） | 不能 | 备用构造器、工厂 |
| `@staticmethod` | 无 | 不能 | 不能 | 归类放置的工具函数 |

### 一个选择上的建议

**默认写实例方法；需要「另一个构造入口」才用 classmethod；
`@staticmethod` 能少用就少用**——大部分情况下它应该是个模块级函数，
放进类里只是把命名空间弄乱了。

---

## 4.9 `__slots__`：省内存的原理与代价

### 默认情况下，每个实例都揣着一个字典

```python
class P:
    def __init__(self, x, y):
        self.x, self.y = x, y

p = P(1, 2)
p.__dict__        # {'x': 1, 'y': 2}
```

这个 `__dict__` 是**稀疏哈希表**——为了支持运行时任意增删属性，
它的内存开销远超「两个键值对」本身。

### `__slots__` 把它换成固定偏移

```python
class PSlots:
    __slots__ = ("x", "y")

    def __init__(self, x, y):
        self.x, self.y = x, y
```

```python
p = PSlots(1, 2)
p.__dict__        # AttributeError: 'PSlots' object has no attribute '__dict__'
p.z = 3           # AttributeError: 'PSlots' object has no attribute 'z'
```

**原理**：类里声明 `__slots__` 后，属性存储变成了
「描述符 + 实例内存块里的固定偏移」，跟 C 结构体成员一样。
省下的就是那个 `__dict__`。

**量级**：在 CPython 3.14 上，一个空实例从约 48 字节 + 一个 64 字节以上的
`__dict__`，变成约 48 字节。**属性少的类能省一半以上**，属性多了收益更明显。

（准确数字看 `demo.py` 的实测输出——不同版本会有差异，**不要背数字，要看量级**。）

### 代价

1. **不能再动态加属性**。`p.z = 3` 直接 `AttributeError`。
   如果你依赖这个（比如给实例挂临时状态），就不能用 slots。
2. **不能多继承有 `__slots__` 的类**（多个非空 slots 的父类会冲突报错）。
   只允许「一个非空 slots 的父类 + 若干无 slots 的父类」。
3. **和 `cached_property` 冲突**（后者需要 `__dict__`）。
4. **和 `@property` 共存要小心**：`__slots__` 里不能放和 property 同名的名字，
   真实数据要放到 `_x` 这种不同的名字上。

### 用 `__slots__` 时最常见的一个 bug

```python
class Bad:
    __slots__ = ("x", "y", "x")      # 重复名字 -> ValueError / 行为诡异
```

```python
class AlsoBad:
    __slots__ = ("values",)

    def __init__(self, values):
        self.values = values

    def add(self, v):
        self.values.append(v)        # ok，改内容没问题
        self.values = self.values + [v]   # ok，重新绑定到 slots 也行
```

**注意**：`__slots__` 挡的是「加新属性名」和「删属性」，
**挡不住修改 slot 里存的那个可变对象的内容**。
所以 `__slots__` 不等于不可变——要不可变请用 `@dataclass(frozen=True)`。

### 什么时候值得用

- 会创建**几十万以上**实例的小类（图形、事件、AST 节点）
- 想向读者表达「这个类的属性是固定的」
- `@dataclass(slots=True)` 是最省事的写法

**不要**为了「性能」到处加 `__slots__`。属性访问速度的收益很小，
真正的收益是内存。

---

## 4.10 抽象基类 `abc` 与 Protocol

### `abc.ABC`

```python
from abc import ABC, abstractmethod

class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        """子类必须实现。"""

    @abstractmethod
    def perimeter(self) -> float:
        ...

    # 具体方法：可以调用抽象方法——这是模板方法模式
    def describe(self) -> str:
        return f"{type(self).__name__}: 面积={self.area():.2f}"

class Circle(Shape):
    def __init__(self, r: float) -> None:
        self.r = r

    def area(self) -> float:
        import math
        return math.pi * self.r ** 2

    def perimeter(self) -> float:
        import math
        return 2 * math.pi * self.r
```

```python
Shape()        # TypeError: Can't instantiate abstract class Shape
               #             with abstract methods area, perimeter
```

**注意：只有「实例化」被拦住，`abstractmethod` 本身不检查签名、
也不检查子类是否真的「覆写」（随便写个同名方法就算数）。**
Python 只在 `__init__` 之前检查「抽象方法集合是否已经全部被覆盖」。

### 抽象基类还能做「虚拟子类」

```python
class MyThing:
    def area(self): ...

Shape.register(MyThing)        # 不继承也算「是 Shape」
isinstance(MyThing(), Shape)   # True
```

标准库里到处这么干：`collections.abc.Sequence.register(tuple)` 之类。
`isinstance([], Sequence)` 为真，但 `list` 的 MRO 里根本没有 `Sequence`。

### 但 Python 更推荐鸭子类型 + `Protocol`

**`abc` 的问题**：要使用 `Shape` 这个抽象基类，你的类就必须**继承**它。
这意味着「我的类必须知道并依赖你的抽象基类」——反向依赖。

**`Protocol`（3.8+，PEP 544）解决的就是这个**：

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class Sized(Protocol):
    def __len__(self) -> int: ...

def show(obj: Sized) -> None:
    print(len(obj))

show([1, 2, 3])       # 静态检查器认为 list 满足 Sized，因为它有 __len__
show("abc")
```

**核心差异**：

| | `abc.ABC` | `Protocol` |
|---|---|---|
| 关系 | 名义子类型（nominal）：必须显式继承 | 结构子类型（structural）：有方法就算 |
| 所在位置 | 运行期 | 主要给类型检查器（mypy/pyright）看 |
| 检查时机 | `isinstance` / 实例化时 | 静态分析时 |
| 适合 | 想提供**默认实现**、想强制继承体系 | 只描述**接口形状** |

**实践建议**：

1. 想表达「这个类能做什么」-> 用 `Protocol` + 类型注解
2. 想复用代码 / 提供模板方法 / 强制某个继承体系 -> 用 `abc.ABC`
3. 单纯想「文档化一个接口」-> 写进文档字符串就够了，什么都不用加

**Python 的默认答案是：先写鸭子类型，等到真需要强约束再上 ABC。**
Java 的 `interface` 在 Python 里通常对应的是一份文档 + 类型注解。

---

## 4.11 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| 类属性是可变对象 | 所有实例共享数据 | 在 `__init__` 里建实例属性 |
| `self.count += 1` 想改类属性 | 类属性纹丝不动 | `type(self).count += 1` |
| 只定义 `__eq__` | `TypeError: unhashable type` | 同时定义 `__hash__` |
| `__hash__` 用到的字段可变 | 对象放进 set 后找不到了 | 键字段做成不可变 |
| `__eq__` 返回 `False` 而非 `NotImplemented` | 反射比较失效 | 类型不符时返回 `NotImplemented` |
| 只写 `__str__` | 列表里打印还是 `<obj at 0x...>` | 写 `__repr__` |
| 硬写 `Parent.method(self)` | 菱形继承下重复调用 | 一律用 `super()` |
| `@dataclass` 里 `x: list = []` | `ValueError` | `field(default_factory=list)` |
| `@staticmethod` 里想用 `cls` | `NameError` | 换成 `@classmethod` |
| 备用构造器里写死类名 | 子类调用拿到父类实例 | 用 `cls(...)` |
| `__slots__` 类想动态加属性 | `AttributeError` | 老老实实用 `__dict__` |
| 以为 `_x` / `__x` 是私有 | 外部照样能改 | Python 没有访问控制，靠约定 |

---

## 4.12 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | 10 节可运行示例，覆盖 4.1~4.10 全部结论 |
| `exercises.py` | 9 道练习，含自动断言 |
| `solutions.py` | 参考答案 + 常见错误写法错在哪 |

### 强烈建议的学法

1. 先跑 `demo.py` 看输出，**先猜结果再看**，猜错的地方就是你的知识盲区
2. 在 `demo_mro()` 里 `D.__mro__` 那一行下断点，用调试器展开看整个元组
3. 打开 REPL，写一个只定义 `__eq__` 的类，然后试试 `hash(实例)`，
   亲手看那个 `None` 是怎么变成 `TypeError` 的
4. 然后做 `exercises.py`

---

## 4.13 延伸阅读

- [Python 官方教程第 9 章：类](https://docs.python.org/zh-cn/3/tutorial/classes.html)
- [官方数据模型参考](https://docs.python.org/zh-cn/3/reference/datamodel.html)
  —— 相当于 Python 的「对象内存布局说明书」，遇到魔术方法就来查这里
- [`dataclasses` 文档](https://docs.python.org/zh-cn/3/library/dataclasses.html)
  和 [PEP 557](https://peps.python.org/pep-0557/)
- [PEP 544 - Protocol](https://peps.python.org/pep-0544/) —— 结构子类型
- 《流畅的 Python》（第 2 版）第 11~13 章、第 20 章
  —— 「一致性哈希」和「描述符」两节必读
- [Python 3.14 新特性](https://docs.python.org/3/whatsnew/3.14.html)
