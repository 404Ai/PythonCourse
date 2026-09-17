"""
模块 04 · 面向对象与数据模型 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. 猜一下这段代码会输出什么
    3. 再跑，看是否和你想的一样

本模块假设你已经会用 Java / C++ 写 OOP，所以不讲「什么是类」，
只讲 Python 的对象模型和它们「不一样的地方」。
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import FrozenInstanceError, dataclass, field


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 74)
    print(title)
    print("=" * 74)


# ======================================================================
# 4.1 self 的本质
# ======================================================================
def demo_self() -> None:
    section("4.1 self 的本质：方法就是普通函数，self 只是第一个参数")

    class Counter:
        def __init__(self, n: int = 0) -> None:
            self.n = n

        def bump(self) -> int:
            self.n += 1
            return self.n

    c = Counter()

    print("  类字典里存的是一个普通函数：")
    print(f"     Counter.bump          -> {Counter.bump}")
    print(f"     type(Counter.bump)    -> {type(Counter.bump).__name__}")
    print()
    print("  通过实例访问，函数会『变形』成绑定方法（bound method）：")
    print(f"     c.bump                -> {c.bump}")
    print(f"     type(c.bump)          -> {type(c.bump).__name__}")
    print(f"     c.bump.__func__       -> {c.bump.__func__}")
    print(f"     c.bump.__self__ is c  -> {c.bump.__self__ is c}")
    print()
    print("  所以这两种写法完全等价：")
    print(f"     c.bump()              -> {c.bump()}")
    print(f"     Counter.bump(c)       -> {Counter.bump(c)}     <- 手动传 self")
    print()
    print("  self 不是关键字，只是个约定名。下面这个类完全合法：")

    class Weird:
        def method(banana):  # noqa: N805 - 故意的，用来证明 self 只是形参名
            return f"我收到了 {banana!r}"

    w = Weird()
    print(f"     Weird().method()      -> {w.method()!r}   （banana 就是 w 自己）")
    print()
    print("  副产品：把绑定方法当回调传出去时，self 会跟着走，不需要 lambda：")

    def run_twice(fn):
        return [fn(), fn()]

    c2 = Counter(10)
    print(f"     run_twice(c2.bump)    -> {run_twice(c2.bump)}")


# ======================================================================
# 4.2 类属性 vs 实例属性
# ======================================================================
def demo_class_attr() -> None:
    section("4.2 类属性 vs 实例属性：可变类属性的共享陷阱")

    class Team:
        members = []      # 类属性！整个类共用一个列表
        count = 0         # 类属性，不可变，看起来没问题

        def add(self, name: str) -> None:
            self.members.append(name)   # 这是『改内容』，不是『赋值』
            self.count += 1             # 这是『赋值』，会创建实例属性

    a = Team()
    b = Team()
    a.add("张三")

    print("  a.add('张三') 之后：")
    print(f"     a.members             -> {a.members}")
    print(f"     b.members             -> {b.members}      <- b 也中招了！")
    print(f"     a.members is b.members -> {a.members is b.members}")
    print()
    print("  原因：self.members.append(...) 分两步 ——")
    print("     1. 查找 self.members  -> 没找到实例属性，命中类属性那个列表")
    print("     2. 就地修改那个列表     -> 没有任何一步创建了实例属性")
    print()

    print("  再看 self.count += 1：它展开是 self.count = self.count + 1")
    print(f"     Team.count            -> {Team.count}          <- 类属性从没被改过")
    print(f"     a.count               -> {a.count}")
    print(f"     b.count               -> {b.count}")
    print(f"     'count' in vars(a)    -> {'count' in vars(a)}      <- 实例字典里有了")
    print(f"     'members' in vars(a)  -> {'members' in vars(a)}      <- 实例字典里没有")
    print()
    print("  对照：Java 里 count++ 改的是静态字段，Python 里 self.count += 1")
    print("  第一次执行必然创建一个同名的实例属性，把类属性遮住。")
    print()
    print("  正解：可变状态一律在 __init__ 里建实例自己的副本。")

    class FixedTeam:
        def __init__(self) -> None:
            self.members: list[str] = []

    x, y = FixedTeam(), FixedTeam()
    x.members.append("张三")
    print(f"     FixedTeam 版：x.members = {x.members}   y.members = {y.members}")


# ======================================================================
# 4.3 继承 / super() / MRO
# ======================================================================
def demo_mro() -> None:
    section("4.3 继承、super() 与 MRO（C3 线性化）")

    class A:
        def who(self) -> str:
            return "A"

        def trace(self) -> str:
            return f"A({self.who()})"

    class B(A):
        def who(self) -> str:
            return "B"

        def trace(self) -> str:
            return "B->" + super().trace()

    class C(A):
        def who(self) -> str:
            return "C"

        def trace(self) -> str:
            return "C->" + super().trace()

    class D(B, C):
        def who(self) -> str:
            return "D"

        def trace(self) -> str:
            return "D->" + super().trace()

    print("  菱形继承：A 是 B 和 C 的父类，D 同时继承 B 和 C")
    print()
    print("     class D(B, C)  的 MRO（方法解析顺序）：")
    for i, cls in enumerate(D.__mro__):
        print(f"        {i}. {cls.__name__:<8}  {cls}")
    print()
    print(f"     D().trace() -> {D().trace()}")
    print()
    print("  注意最后是 A(D) 而不是 A(C)：")
    print("     super() 只影响『从 MRO 的哪个位置继续找』，")
    print("     不影响 self 是谁 —— self 从头到尾都是那个 D 实例，")
    print("     所以 self.who() 命中的始终是 D.who。")
    print()
    print("  注意：光把『最外层』写死是没用的。比如让 D2(D 的变体) 硬写 B.trace：")

    class D2(B, C):
        def who(self) -> str:
            return "D"

        def trace(self) -> str:
            return "D->" + B.trace(self)      # 硬写中间层

    print(f"     D2().trace() -> {D2().trace()}")
    print("     结果和 D 一样 —— 因为 B.trace 内部用的还是 super().trace()，")
    print("     它会顺着 MRO 继续走到 C。**跳过只发生在『硬写的那一环』。**")
    print()

    print("  真正会丢方法的是中间层硬写父类：")

    class B2(A):
        def who(self) -> str:
            return "B"

        def trace(self) -> str:
            return "B->" + A.trace(self)      # 硬写祖父类，绕过 MRO 上排在后面的 C

    class D3(B2, C):
        def who(self) -> str:
            return "D"

        def trace(self) -> str:
            return "D->" + super().trace()

    print(f"     协作版 D().trace()  -> {D().trace()}")
    print(f"     硬写版 D3().trace() -> {D3().trace()}      <- C.trace 真的没了")
    print(f"     D3 的 MRO           -> {[k.__name__ for k in D3.__mro__]}")
    print("     ^ C 明明在 MRO 里，却因为 B2 直接跳到 A 而永远轮不到它。")
    print("       这就是为什么协作式继承里『一律用 super()』是硬规矩。")
    print()

    print("  C3 线性化无法满足时会直接拒绝定义类：")
    try:
        class X:
            pass

        class Y:
            pass

        class Z(X, Y):
            pass

        class W(Y, X):
            pass

        class Bad(Z, W):     # X 要在 Y 前，又要在 Y 后，矛盾
            pass
    except TypeError as exc:
        print(f"     TypeError: {exc}")
    print()

    print("  协作式继承的 __init__ 写法（每个类都用 **kwargs 透传）：")

    class Root:
        def __init__(self, **kwargs) -> None:
            self.log: list[str] = []      # 链的终点，不再往上走

    class Named(Root):
        def __init__(self, name: str = "?", **kwargs) -> None:
            super().__init__(**kwargs)    # 先让链后面的人初始化
            self.name = name
            self.log.append(f"Named({name})")

    class Aged(Root):
        def __init__(self, age: int = 0, **kwargs) -> None:
            super().__init__(**kwargs)
            self.age = age
            self.log.append(f"Aged({age})")

    class Person(Named, Aged):
        def __init__(self, **kwargs) -> None:
            super().__init__(**kwargs)
            self.log.append("Person")

    p = Person(name="李四", age=30)
    print(f"     Person(name='李四', age=30).log -> {p.log}")
    print("     顺序是反的：因为每个类都先 super().__init__() 再 append，")
    print("     最内层的 Root 最先跑完，最外层的 Person 最后跑完。")


# ======================================================================
# 4.4 魔术方法
# ======================================================================
def demo_magic_methods() -> None:
    section("4.4 魔术方法：让语法为你服务")

    class Playlist:
        """一个最小可用的容器类，演示常见魔术方法。"""

        def __init__(self, songs: list[str] | None = None) -> None:
            self._songs: list[str] = list(songs or [])

        # repr 给开发者看，目标是 eval(repr(obj)) == obj
        def __repr__(self) -> str:
            return f"Playlist({self._songs!r})"

        # str 给用户看，不实现的话会自动回退到 __repr__
        def __str__(self) -> str:
            return "、".join(self._songs) if self._songs else "(空播放列表)"

        def __len__(self) -> int:
            return len(self._songs)

        def __getitem__(self, index):
            # 支持 p[0] / p[1:2]，切片会传进来一个 slice 对象
            return self._songs[index]

        def __contains__(self, item: str) -> bool:
            return item in self._songs

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Playlist):
                return NotImplemented
            return self._songs == other._songs

        def __hash__(self) -> int:
            return hash(tuple(self._songs))   # 内部是 list，转成 tuple 才能哈希

        def __add__(self, other: "Playlist") -> "Playlist":
            if not isinstance(other, Playlist):
                return NotImplemented
            return Playlist(self._songs + other._songs)

        def __call__(self, n: int) -> list[str]:
            # 实现 __call__ 后，实例本身就像函数一样可以加括号调用
            return self._songs[:n]

    p = Playlist(["晴天", "七里香"])
    q = Playlist(["稻香"])

    print(f"     repr(p)          -> {p!r}")
    print(f"     str(p)           -> {p}")
    print(f"     print(p)         -> ", end="")
    print(p)
    print(f"     len(p)           -> {len(p)}")
    print(f"     p[0]             -> {p[0]!r}")
    print(f"     p[0:2]           -> {p[0:2]!r}")
    print(f"     '晴天' in p      -> {'晴天' in p}")
    print(f"     p == Playlist(['晴天', '七里香']) -> {p == Playlist(['晴天', '七里香'])}")
    print(f"     p + q            -> {p + q!r}")
    print(f"     p(1)             -> {p(1)!r}    <- __call__，实例被当成函数调用")
    print(f"     bool(Playlist()) -> {bool(Playlist())}    <- 没实现 __bool__，回退到 __len__")
    print()

    print("  repr 和 str 的分工，最直观的例子是容器：")
    print(f"     print(p)         -> {p}          （走 __str__）")
    print(f"     print([p, q])    -> {[p, q]}    （容器里走 __repr__）")
    print()

    print("  __eq__ 遇到不认识的类型，应该返回 NotImplemented 而不是 False：")

    class OnlyOne:
        def __eq__(self, other):
            return NotImplemented   # 交给对方的 __eq__ 去决定

    print(f"     OnlyOne() == 1   -> {OnlyOne() == 1}   （双方都放弃，退回身份比较）")
    print(f"     NotImplemented 是单例：{NotImplemented!r}")

    print()
    print("  Python 允许你实现 __add__ 却让 + 报错，因为返回了 NotImplemented：")
    try:
        p + 3
    except TypeError as exc:
        print(f"     p + 3            -> TypeError: {exc}")


# ======================================================================
# 4.5 __eq__ 与 __hash__
# ======================================================================
def demo_eq_hash() -> None:
    section("4.5 __eq__ 与 __hash__ 必须成对修改")

    class EqOnly:
        """只定义了 __eq__，没定义 __hash__。"""

        def __init__(self, x: int) -> None:
            self.x = x

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, EqOnly):
                return NotImplemented
            return self.x == other.x

    print("  Python 在类创建时做了一件事：")
    print(f"     EqOnly.__hash__      -> {EqOnly.__hash__}")
    print("     ^ 定义了 __eq__ 却没定义 __hash__，__hash__ 会被显式置为 None。")
    print()
    try:
        hash(EqOnly(1))
    except TypeError as exc:
        print(f"     hash(EqOnly(1))      -> TypeError: {exc}")
    try:
        {EqOnly(1)}
    except TypeError as exc:
        print(f"     {{EqOnly(1)}}          -> TypeError: {exc}")
    print()

    print("  为什么必须这样？先看看『如果放着不管』会发生什么坏事：")

    class Broken:
        def __init__(self, x: int) -> None:
            self.x = x

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Broken):
                return NotImplemented
            return self.x == other.x

        __hash__ = object.__hash__      # 强行保留『按身份算哈希』

    b1, b2 = Broken(1), Broken(1)
    print(f"     b1 == b2             -> {b1 == b2}    （我们定义的规则：按值相等）")
    print(f"     hash(b1) == hash(b2) -> {hash(b1) == hash(b2)}    （按身份算，必然不同）")
    print("     契约『a == b 则 hash(a) == hash(b)』被打破了，后果是：")
    d = {b1: "找到了"}
    print(f"     d = {{b1: '找到了'}}; d[b2] -> ", end="")
    try:
        d[b2]
    except KeyError as exc:
        print(f"KeyError: {exc}")
    print("     明明 b1 == b2，却查不到。这种『静默的错数据』比崩溃可怕得多，")
    print("     所以 Python 干脆让类变成不可哈希 —— 快速失败。")
    print()

    print("  正确写法：")
    print("     1. __hash__ 用到的字段要和 __eq__ 用到的一致")
    print("     2. 这些字段必须不可变，否则对象进了 set 之后会『找不到自己』")

    class Point:
        def __init__(self, x: int, y: int) -> None:
            self.x, self.y = x, y

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Point):
                return NotImplemented
            return (self.x, self.y) == (other.x, other.y)

        def __hash__(self) -> int:
            return hash((self.x, self.y))

        def __repr__(self) -> str:
            return f"Point({self.x}, {self.y})"

    s = {Point(1, 2), Point(1, 2), Point(3, 4)}
    print(f"     {{Point(1,2), Point(1,2), Point(3,4)}} -> {s}   （去重成功）")
    print()

    print("  字段可变会怎样：")
    p = Point(1, 2)
    bag = {p}
    p.x = 99
    print(f"     p = Point(1,2); bag = {{p}}; p.x = 99")
    print(f"     p in bag             -> {p in bag}    <- False！对象还在里面，但找不到了")
    print(f"     bag                  -> {bag}    （它的哈希是按 x=1 算的）")
    print()
    print(f"  另一个例子：hash((1, 2)) = {hash((1, 2))}，但元组里装了列表就不行：")
    try:
        hash((1, [2]))
    except TypeError as exc:
        print(f"     hash((1, [2]))       -> TypeError: {exc}")


# ======================================================================
# 4.6 property
# ======================================================================
def demo_property() -> None:
    section("4.6 @property：计算属性，而不是 getter/setter")

    class Temperature:
        def __init__(self, celsius: float = 0.0) -> None:
            # 注意这里走的是 setter，所以校验自动生效
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

    t = Temperature(25)
    print(f"     t.celsius            -> {t.celsius}      （当属性读，不写括号）")
    print(f"     t.fahrenheit         -> {t.fahrenheit}      （算出来的）")
    t.celsius = 30
    print(f"     t.celsius = 30 之后 t.fahrenheit -> {t.fahrenheit}")
    print()

    print("  只读的计算属性不能赋值：")
    try:
        t.fahrenheit = 100
    except AttributeError as exc:
        print(f"     t.fahrenheit = 100   -> AttributeError: {exc}")
    print()

    print("  校验在 setter 里：")
    for bad in (-300, "热"):
        try:
            t.celsius = bad
        except (ValueError, TypeError) as exc:
            print(f"     t.celsius = {bad!r:<6} -> {type(exc).__name__}: {exc}")
    print()

    print("  property 背后是数据描述符，真实数据住在实例字典里：")
    print(f"     t.__dict__           -> {t.__dict__}")
    print(f"     type(t).celsius      -> {type(t).celsius}")
    print()
    print("  但 _celsius 只是个约定，不是私有 —— Python 没有强制访问控制：")
    t._celsius = -9999
    print(f"     t._celsius = -9999; t.celsius -> {t.celsius}")
    t.celsius = 25
    print()

    print("  双下划线（name mangling）也只是改个名：")

    class Secret:
        def __init__(self) -> None:
            self.__token = "abc123"

    s = Secret()
    print(f"     vars(s)              -> {vars(s)}")
    print(f"     s._Secret__token     -> {s._Secret__token}")
    print("     它防的是『子类不小心撞名』，不是防你访问。")


# ======================================================================
# 4.7 dataclass
# ======================================================================
class DemoPointDC:
    """手写版值对象：为了和下面的 dataclass 版本对比。"""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"DemoPointDC(x={self.x!r}, y={self.y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DemoPointDC):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __hash__(self) -> int:
        return hash((self.x, self.y))


@dataclass(frozen=True)
class DemoPointFrozen:
    """同样的东西，dataclass 版本。"""

    x: float
    y: float


@dataclass(order=True)
class DemoVersion:
    major: int
    minor: int = 0
    tag: str = field(default="", compare=False)   # 不参与比较


@dataclass
class DemoStudent:
    name: str
    scores: list[int] = field(default_factory=list)      # 可变默认值必须这样写
    average: float = field(init=False, default=0.0)      # 不出现在 __init__ 参数里

    def __post_init__(self) -> None:
        self.average = sum(self.scores) / len(self.scores) if self.scores else 0.0


def demo_dataclass() -> None:
    section("4.7 @dataclass：把样板代码交给解释器")

    print("  手写版 vs dataclass 版，行为完全一致：")
    a = DemoPointDC(1, 2)
    b = DemoPointFrozen(1, 2)
    print(f"     手写      : {a!r}")
    print(f"     dataclass : {b!r}")
    print(f"     相等性    : {a == DemoPointDC(1, 2)} / {b == DemoPointFrozen(1, 2)}")
    print(f"     可哈希    : {hash(a) == hash(DemoPointDC(1, 2))} / {hash(b) == hash(DemoPointFrozen(1, 2))}")
    print()

    print(f"     DemoPointDC 的源码行数（含 __init__/__repr__/__eq__/__hash__）约 20 行")
    print(f"     DemoPointFrozen 只需 3 行。")
    print()

    print("  frozen=True 让实例彻底不可变：")
    try:
        b.x = 99
    except FrozenInstanceError as exc:
        print(f"     b.x = 99             -> FrozenInstanceError: {exc}")
    print(f"     （FrozenInstanceError 是 AttributeError 的子类，")
    print(f"      所以 except AttributeError 也能抓到：{issubclass(FrozenInstanceError, AttributeError)}）")
    print()

    print("  frozen=True 顺带自动生成了 __hash__：")
    print(f"     {{DemoPointFrozen(1, 2), DemoPointFrozen(1, 2)}} -> "
          f"{ {DemoPointFrozen(1, 2), DemoPointFrozen(1, 2)} }")
    print()

    print("  order=True：比较的是『参与比较的字段组成的元组』，字典序")
    v1, v2 = DemoVersion(1, 9), DemoVersion(2, 0)
    print(f"     DemoVersion(1, 9) < DemoVersion(2, 0) -> {v1 < v2}")
    print(f"     tag 字段 compare=False，不参与比较：")
    print(f"       DemoVersion(1, 0, 'zzz') < DemoVersion(1, 0, 'aaa') -> "
          f"{DemoVersion(1, 0, 'zzz') < DemoVersion(1, 0, 'aaa')}")
    print()

    print("  default_factory 解决『可变默认值共享』的问题：")
    s1, s2 = DemoStudent("张三", [90, 80]), DemoStudent("李四")
    s1.scores.append(100)
    print(f"     s1 = DemoStudent('张三', [90, 80]); s1.scores.append(100)")
    print(f"     s1.scores            -> {s1.scores}")
    print(f"     s2.scores            -> {s2.scores}      <- 没有被污染")
    print(f"     s1.average           -> {s1.average}      （__post_init__ 算出来的）")
    print(f"     s2.average           -> {s2.average}")
    print()
    print("     如果写成 scores: list[int] = []，dataclasses 会直接拦住：")
    try:
        @dataclass
        class Bad:
            items: list = []
    except ValueError as exc:
        print(f"       ValueError: {exc}")
    print()
    print("     但它只认得出 list/dict/set 这类内置类型，自定义可变对象照样踩坑，")
    print("     所以养成『可变默认值一律 default_factory』的习惯最安全。")
    print()

    print("  init=False 的字段不出现在构造参数里：")
    import inspect
    print(f"     inspect.signature(DemoStudent) -> {inspect.signature(DemoStudent)}")


# ======================================================================
# 4.8 classmethod / staticmethod
# ======================================================================
def demo_method_kinds() -> None:
    section("4.8 @classmethod / @staticmethod / 实例方法")

    class Date:
        def __init__(self, y: int, m: int, d: int) -> None:
            self.y, self.m, self.d = y, m, d

        def __repr__(self) -> str:
            return f"Date({self.y}, {self.m}, {self.d})"

        def __eq__(self, other: object) -> bool:
            if not isinstance(other, Date):
                return NotImplemented
            return (self.y, self.m, self.d) == (other.y, other.m, other.d)

        # 实例方法：第一个参数是实例
        def isoformat(self) -> str:
            return f"{self.y:04d}-{self.m:02d}-{self.d:02d}"

        # 类方法：第一个参数是『类』。典型用途是备用构造器
        @classmethod
        def from_iso(cls, text: str) -> "Date":
            y, m, d = (int(part) for part in text.split("-"))
            return cls(y, m, d)       # 注意是 cls，不是写死的 Date

        # 静态方法：谁都不绑，就是借个命名空间放的普通函数
        @staticmethod
        def is_leap(year: int) -> bool:
            return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)

    d = Date.from_iso("2024-02-29")
    print(f"     Date.from_iso('2024-02-29') -> {d!r}")
    print(f"     d.isoformat()               -> {d.isoformat()!r}")
    print(f"     Date.is_leap(2024)          -> {Date.is_leap(2024)}")
    print(f"     Date.is_leap(1900)          -> {Date.is_leap(1900)}   （整百年要能被 400 整除）")
    print(f"     Date.is_leap(2000)          -> {Date.is_leap(2000)}")
    print()

    print("  三者到底是什么东西，看类字典最清楚：")
    for name in ("isoformat", "from_iso", "is_leap"):
        raw = Date.__dict__[name]
        print(f"     Date.__dict__['{name}']{' ' * (11 - len(name))}-> {raw!r}")
    print()

    print("  关键：classmethod 的第一个参数是 cls，所以子类调用会拿到子类：")

    class DateTime(Date):
        pass

    print(f"     type(Date.from_iso('2024-01-01'))     -> {type(Date.from_iso('2024-01-01')).__name__}")
    print(f"     type(DateTime.from_iso('2024-01-01')) -> {type(DateTime.from_iso('2024-01-01')).__name__}")
    print("     ^ 如果 from_iso 里写死 return Date(...)，这里就会错成 Date。")
    print()
    print("  所以：需要 cls 就用 @classmethod，纯工具函数才用 @staticmethod。")
    print("  如果一个函数既不需要 self 也不需要 cls，先想想它该不该是模块级函数。")


# ======================================================================
# 4.9 __slots__
# ======================================================================
def demo_slots() -> None:
    section("4.9 __slots__：省内存的原理与代价")

    class WithDict:
        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    class WithSlots:
        __slots__ = ("x", "y")

        def __init__(self, x: int, y: int) -> None:
            self.x = x
            self.y = y

    a, b = WithDict(1, 2), WithSlots(1, 2)

    print("  普通类的每个实例都揣着一个 __dict__（稀疏哈希表）：")
    print(f"     a.__dict__                     -> {a.__dict__}")
    print(f"     sys.getsizeof(a)               -> {sys.getsizeof(a)} 字节（只有对象头）")
    print(f"     sys.getsizeof(a.__dict__)      -> {sys.getsizeof(a.__dict__)} 字节（那个字典本身）")
    print(f"     合计                           -> {sys.getsizeof(a) + sys.getsizeof(a.__dict__)} 字节")
    print()
    print("  __slots__ 把属性存储换成『描述符 + 实例内存块里的固定偏移』：")
    try:
        b.__dict__
    except AttributeError as exc:
        print(f"     b.__dict__                     -> AttributeError: {exc}")
    print(f"     sys.getsizeof(b)               -> {sys.getsizeof(b)} 字节（没有额外字典）")
    print()

    print("  用 tracemalloc 精确测量创建 20000 个实例的净增量：")

    import tracemalloc

    def measure(cls) -> int:
        tracemalloc.start()
        before = tracemalloc.take_snapshot()
        objs = [cls(i, i) for i in range(20000)]
        after = tracemalloc.take_snapshot()
        tracemalloc.stop()
        total = sum(stat.size_diff for stat in after.compare_to(before, "lineno"))
        assert len(objs) == 20000
        return total

    n_dict = measure(WithDict)
    n_slots = measure(WithSlots)
    print(f"     普通类  : {n_dict:>9,} 字节  （平均 {n_dict / 20000:.1f} 字节/实例）")
    print(f"     slots 类: {n_slots:>9,} 字节  （平均 {n_slots / 20000:.1f} 字节/实例）")
    print(f"     省了约 {(1 - n_slots / n_dict) * 100:.0f}%")
    print("     （具体数字随版本变化，看量级就好，不要背）")
    print()

    print("  代价一：不能再动态加属性")
    try:
        b.z = 3
    except AttributeError as exc:
        print(f"     b.z = 3              -> AttributeError: {exc}")
    print()
    print("  代价二：__slots__ 挡不住『修改 slot 里那个可变对象的内容』")
    print("          所以它不等于不可变，要不可变请用 @dataclass(frozen=True)")
    print()
    print("  代价三：不能多继承两个『互不相关、且都有非空 __slots__』的类")
    try:
        class SlotsA:
            __slots__ = ("x",)

        class SlotsB:
            __slots__ = ("y",)

        class Both(SlotsA, SlotsB):    # 两套实例内存布局没法合并
            pass
    except TypeError as exc:
        print(f"     TypeError: {exc}")
    print("     （如果两个父类有继承关系，布局能合并，就不会报错 —— ")
    print("       所以这个限制只在『真·多继承两个 slots 类』时才踩到。）")
    print()
    print("  还可以用 @dataclass(slots=True) 一行搞定（3.10+）：")

    @dataclass(slots=True)
    class AutoSlots:
        x: int
        y: int

    print(f"     '__slots__' in vars(AutoSlots) -> {'__slots__' in vars(AutoSlots)}")
    print(f"     AutoSlots(1, 2).__dict__ 会抛 AttributeError -> ", end="")
    try:
        AutoSlots(1, 2).__dict__
        print("没有抛（意外）")
    except AttributeError:
        print("确实抛了")
    print("     注意 slots=True 会让 dataclass 重新创建一个类对象，")
    print("     __class__ 相关的小技巧（比如零参 super() 的闭包）在这个类上要小心。")


# ======================================================================
# 4.10 abc 与 Protocol
# ======================================================================
def demo_abc_protocol() -> None:
    section("4.10 抽象基类 abc.ABC 与结构化类型 Protocol")

    class Shape(ABC):
        @abstractmethod
        def area(self) -> float:
            """子类必须实现。"""

        @abstractmethod
        def perimeter(self) -> float:
            ...

        # 具体方法可以调用抽象方法 —— 这就是模板方法模式
        def describe(self) -> str:
            return f"{type(self).__name__}: 面积={self.area():.2f} 周长={self.perimeter():.2f}"

    class Circle(Shape):
        def __init__(self, r: float) -> None:
            self.r = r

        def area(self) -> float:
            import math
            return math.pi * self.r ** 2

        def perimeter(self) -> float:
            import math
            return 2 * math.pi * self.r

    import math

    c = Circle(1.0)
    print(f"     Circle(1).describe()   -> {c.describe()}")
    print()
    print("  抽象基类不能被实例化：")
    try:
        Shape()
    except TypeError as exc:
        print(f"     Shape()                -> TypeError: {exc}")
    print()
    print("  只实现一半的子类也一样：")

    class HalfShape(Shape):
        def area(self) -> float:
            return 1.0

    try:
        HalfShape()
    except TypeError as exc:
        print(f"     HalfShape()            -> TypeError: {exc}")
    print()
    print("  注意 abstractmethod 只检查『有没有覆盖』，不检查签名、不检查真的实现了：")

    class Liar(Shape):
        area = 42                  # 不是方法，只是个属性，照样算『已覆盖』

        def perimeter(self) -> float:
            return 0.0

    print(f"     Liar() 竟然能创建 -> {Liar()!r}，但 c.describe() 会炸")
    print()

    print("  abc 还支持『虚拟子类』——不继承也算数：")

    class Duck:                    # 完全独立的一个类，跟 Shape 没有任何继承关系
        def area(self) -> float:
            return 0.0

        def perimeter(self) -> float:
            return 0.0

    Shape.register(Duck)
    print(f"     isinstance(Duck(), Shape) -> {isinstance(Duck(), Shape)}   （注册出来的）")
    print(f"     Duck.__mro__            -> {[k.__name__ for k in Duck.__mro__]}")
    print("     标准库也这么干：isinstance([], collections.abc.Sequence) 为真，")
    print("     但 list 的 MRO 里根本没有 Sequence。")
    print()

    print("  但 Python 更推荐『鸭子类型 + Protocol』：")

    from typing import Protocol, runtime_checkable

    @runtime_checkable
    class HasLen(Protocol):
        def __len__(self) -> int: ...

    def show(obj: HasLen) -> str:
        return f"len = {len(obj)}"

    print(f"     show([1, 2, 3])   -> {show([1, 2, 3])}   （list 没有任何继承关系）")
    print(f"     show('abcd')      -> {show('abcd')}")
    print(f"     isinstance([1], HasLen) -> {isinstance([1], HasLen)}")
    print()
    print("  两者怎么选：")
    print("     Protocol  -> 只想描述『能做什么』，用类型注解让 mypy 检查")
    print("     abc.ABC   -> 想提供默认实现 / 强制某个继承体系 / 需要运行期检查")
    print("     Python 的默认答案是：先写鸭子类型，真需要强约束再上 ABC。")


# ======================================================================
def main() -> None:
    demo_self()
    demo_class_attr()
    demo_mro()
    demo_magic_methods()
    demo_eq_hash()
    demo_property()
    demo_dataclass()
    demo_method_kinds()
    demo_slots()
    demo_abc_protocol()
    print()
    print("=" * 74)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 74)


if __name__ == "__main__":
    main()
