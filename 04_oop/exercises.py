"""
模块 04 · 面向对象与数据模型 —— 练习

做法：
    1. 把每个 `raise NotImplementedError` 换成你的实现
       （类里的方法也一样，把方法体的 `raise NotImplementedError` 换掉）
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

提示：报错的那一行可以下断点，按 F5 用调试器看中间变量，
      这是本课程最推荐的排错方式。
"""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from pathlib import Path

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 手写一个完整的不可变值对象
# ======================================================================
class Point:
    """二维点，一个不可变的值对象（value object）。

    要求：
        - 属性 x / y 只读：p.x = 99 必须抛 AttributeError
          （提示：把真实数据存在 _x / _y 上，再用只读 property 暴露）
        - __repr__ 输出 Point(x=1, y=2)（用 !r 格式化字段）
        - __eq__：两个 Point 的 x 和 y 都相等才算相等；
          和无关类型比较时返回 NotImplemented（不是 False！）
        - __hash__：和 __eq__ 保持一致的契约
        - __add__：支持 Point + Point，返回新的 Point；
          遇到别的类型返回 NotImplemented

    注意：原值原样保存，不要做 float 转换（Point(1, 2) 的 x 就是整数 1）。
    """

    def __init__(self, x: float, y: float) -> None:
        raise NotImplementedError

    @property
    def x(self) -> float:
        raise NotImplementedError

    @property
    def y(self) -> float:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError

    def __add__(self, other: "Point") -> "Point":
        raise NotImplementedError


# ======================================================================
# q2 —— 用 @dataclass 重写 q1
# ======================================================================
def q2_build_point_dataclass() -> type:
    """用 `@dataclass(frozen=True)` 定义并**返回**一个类，要求：

        - 类名必须叫 FrozenPoint
        - 字段顺序是 x, y
        - 行为和 q1 的 Point 等价：== 按值比较、可哈希、不可变
        - 实例被赋值时抛异常（frozen=True 会自动做到）

    提示：函数里也能用装饰器定义类，最后 `return FrozenPoint` 就行。

    做完对比一下：q1 手写了 7 个方法，这里只需要几行？
    """
    raise NotImplementedError


# ======================================================================
# q3 —— @property 带校验
# ======================================================================
class Temperature:
    """温度。真实数据存在 _celsius，对外暴露 celsius / fahrenheit 两个属性。

    要求：
        - celsius 可读可写，写入时校验：
            * 不是 int / float（bool 也不算）-> TypeError
            * 低于绝对零度 -273.15 -> ValueError
            * 合法时统一转成 float 存起来
        - fahrenheit 是**只读**的计算属性（没有 setter），
          公式：celsius * 9 / 5 + 32
        - 构造函数接收摄氏温度，并且必须走 setter（这样校验才生效）
    """

    def __init__(self, celsius: float = 0.0) -> None:
        raise NotImplementedError

    @property
    def celsius(self) -> float:
        raise NotImplementedError

    @celsius.setter
    def celsius(self, value: float) -> None:
        raise NotImplementedError

    @property
    def fahrenheit(self) -> float:
        raise NotImplementedError


# ======================================================================
# q4 —— 魔术方法：二维向量
# ======================================================================
class Vector2D:
    """二维向量。原值原样保存，不要做 float 转换。

    要求实现：
        __repr__    -> "Vector2D(1, 2)"（用 !r 格式化字段）
        __eq__      -> 两个分量都相等才相等；无关类型返回 NotImplemented
        __add__     -> 向量 + 向量；别的类型返回 NotImplemented
        __mul__     -> 向量 * 标量（int / float）；别的类型返回 NotImplemented
        __rmul__    -> 标量 * 向量，复用 __mul__ 的实现即可
        __neg__     -> -向量，返回新向量
        __abs__     -> 模长 sqrt(x² + y²)，返回 float
        __bool__    -> 零向量为 False，其余为 True

    重点：所有运算都必须返回**新对象**，不能就地修改 self。
    """

    def __init__(self, x: float, y: float) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __add__(self, other: "Vector2D") -> "Vector2D":
        raise NotImplementedError

    def __mul__(self, scalar: float) -> "Vector2D":
        raise NotImplementedError

    def __rmul__(self, scalar: float) -> "Vector2D":
        raise NotImplementedError

    def __neg__(self) -> "Vector2D":
        raise NotImplementedError

    def __abs__(self) -> float:
        raise NotImplementedError

    def __bool__(self) -> bool:
        raise NotImplementedError


# ======================================================================
# q5 —— 菱形继承与协作式 super()
# ======================================================================
class Root:
    """协作继承链的终点站。

    只做一件事：建出 self.log。
    注意它**不再调用 super().__init__()**，让链条在这里结束。
    （object.__init__ 不接受多余的关键字参数，调了反而会炸。）
    """

    def __init__(self, **kwargs) -> None:
        raise NotImplementedError


class Named(Root):
    """给对象加一个 name 属性，并在 log 里记一笔 "Named(<name>)"。"""

    def __init__(self, name: str = "?", **kwargs) -> None:
        raise NotImplementedError


class Aged(Root):
    """给对象加一个 age 属性，并在 log 里记一笔 "Aged(<age>)"。"""

    def __init__(self, age: int = 0, **kwargs) -> None:
        raise NotImplementedError


class Person(Named, Aged):
    """同时拿到 name 和 age，最后在 log 里记一笔 "Person"。

    实现完成后确认：
        Person(name="张三", age=20).log -> ["Aged(20)", "Named(张三)", "Person"]

    顺序是反的 —— 因为每个类都先 super().__init__() 再 append，
    最内层的 Root 最先跑完。
    另外：每个类的 __init__ 只能跑**一次**，这也是协作继承的意义。
    """

    def __init__(self, **kwargs) -> None:
        raise NotImplementedError


# ======================================================================
# q6 —— __eq__ 与 __hash__ 的契约
# ======================================================================
class Student:
    """学生。以**学号 sid** 作为身份标识。

    要求：
        - __repr__ -> "Student(sid=1, name='张三')"（用 !r 格式化字段）
        - __eq__ 按 sid 比较：学号相同就算同一个学生（名字不同也算）
        - __hash__ 必须和 __eq__ 一致
        - 和无关类型比较返回 NotImplemented

    这道题的重点是：你**必须**写 __hash__。
    只写 __eq__ 的话，Python 会把 Student.__hash__ 设成 None，
    实例就再也放不进 set、也不能当字典键了。
    """

    def __init__(self, sid: int, name: str) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def __hash__(self) -> int:
        raise NotImplementedError


# ======================================================================
# q7 —— classmethod / staticmethod
# ======================================================================
class Date:
    """一个日期类。

    要求：
        - __init__(year, month, day) 做合法性校验，非法就抛 ValueError
          （月份 1~12；天数 1~当月天数，闰年的 2 月有 29 天）
        - __repr__ -> "Date(2024, 2, 29)"
        - __eq__ 按三个字段比较，无关类型返回 NotImplemented
        - isoformat() -> "2024-02-29"（补零到 4/2/2 位）
        - from_iso(text) 是 **@classmethod** 备用构造器：
          解析 "2024-02-29"，返回 cls(...) 的实例
          **必须用 cls，不能写死 Date**
        - is_leap(year) 是 **@staticmethod**：
          判断闰年（能被 4 整除，但整百年必须能被 400 整除）
    """

    def __init__(self, year: int, month: int, day: int) -> None:
        raise NotImplementedError

    def __repr__(self) -> str:
        raise NotImplementedError

    def __eq__(self, other: object) -> bool:
        raise NotImplementedError

    def isoformat(self) -> str:
        raise NotImplementedError

    @classmethod
    def from_iso(cls, text: str) -> "Date":
        raise NotImplementedError

    @staticmethod
    def is_leap(year: int) -> bool:
        raise NotImplementedError


# ======================================================================
# q8 —— 抽象基类
# ======================================================================
class Shape(ABC):
    """所有图形的抽象基类。

    要求：
        - area / perimeter 是 @abstractmethod（子类必须实现）
        - describe() 是具体方法，直接借用子类实现的 area / perimeter：
          返回 f"{type(self).__name__}: 面积={self.area():.2f} 周长={self.perimeter():.2f}"
          这就是「模板方法模式」：父类定流程，子类填细节。
    """

    @abstractmethod
    def area(self) -> float:
        """子类必须实现。"""

    @abstractmethod
    def perimeter(self) -> float:
        """子类必须实现。"""

    def describe(self) -> str:
        raise NotImplementedError


class Circle(Shape):
    """圆。area = pi * r²，perimeter = 2 * pi * r。"""

    def __init__(self, r: float) -> None:
        raise NotImplementedError

    def area(self) -> float:
        raise NotImplementedError

    def perimeter(self) -> float:
        raise NotImplementedError


class Rectangle(Shape):
    """矩形。area = w * h，perimeter = 2 * (w + h)。"""

    def __init__(self, width: float, height: float) -> None:
        raise NotImplementedError

    def area(self) -> float:
        raise NotImplementedError

    def perimeter(self) -> float:
        raise NotImplementedError


# ======================================================================
# q9 —— @dataclass 进阶
# ======================================================================
def q9_build_student_class() -> type:
    """用 `@dataclass` 定义并返回一个类，要求：

        - 类名 Student
        - 字段 name: str
        - 字段 scores: list[int]，默认是**空列表** —— 必须用
          field(default_factory=list)，不能写 = []
        - 字段 average: float，不出现在构造参数里（field(init=False)），
          由 __post_init__ 算成平均分（scores 为空时是 0.0）
        - 支持按字段排序（order=True）
        - 用 __slots__ 省内存（slots=True）

    验收时会检查 inspect.signature 只有 name 和 scores 两个参数、
    两个实例的 scores 不是同一个列表、以及实例没有 __dict__。
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    p = Point(1, 2)
    assert repr(p) == "Point(x=1, y=2)", f"repr 不对：{repr(p)}"
    assert (p.x, p.y) == (1, 2)

    assert p == Point(1, 2), "x 和 y 都相等就应该相等"
    assert p != Point(1, 3)
    assert p != Point(2, 2)
    assert (p == "Point(1, 2)") is False, "和无关类型比较不能抛异常，也不能返回 True"
    assert (p != "Point(1, 2)") is True

    assert hash(p) == hash(Point(1, 2)), "相等对象的哈希必须相同"
    assert len({Point(1, 2), Point(1, 2), Point(3, 4)}) == 2, "set 应该去重"

    assert Point(1, 2) + Point(3, 4) == Point(4, 6)
    assert p == Point(1, 2), "加法不能修改原对象"

    try:
        p.x = 99
    except AttributeError:
        pass
    else:
        raise AssertionError("Point 应该是不可变的：p.x = 99 必须抛 AttributeError")

    try:
        p + 3
    except TypeError:
        pass
    else:
        raise AssertionError("Point + int 应该抛 TypeError（__add__ 要返回 NotImplemented）")


def t_q2() -> None:
    import dataclasses

    FrozenPoint = q2_build_point_dataclass()
    assert FrozenPoint.__name__ == "FrozenPoint", f"类名应该是 FrozenPoint，实际 {FrozenPoint.__name__}"
    assert dataclasses.is_dataclass(FrozenPoint), "这个类应该是个 dataclass"

    p = FrozenPoint(1, 2)
    assert (p.x, p.y) == (1, 2)
    assert repr(p).endswith("FrozenPoint(x=1, y=2)"), f"repr 不对：{repr(p)}"

    assert p == FrozenPoint(1, 2)
    assert p != FrozenPoint(1, 3)
    assert (p == (1, 2)) is False, "和元组比较不应该相等"
    assert hash(p) == hash(FrozenPoint(1, 2)), "frozen=True 会自动生成 __hash__"
    assert len({p, FrozenPoint(1, 2), FrozenPoint(3, 4)}) == 2

    try:
        p.x = 99
    except AttributeError:
        pass
    else:
        raise AssertionError("frozen=True 的实例不该能被赋值")

    try:
        FrozenPoint(1)
    except TypeError:
        pass
    else:
        raise AssertionError("FrozenPoint(1) 少了一个参数，应该抛 TypeError")


def t_q3() -> None:
    t = Temperature(25)
    assert t.celsius == 25.0, f"celsius 不对：{t.celsius}"
    assert isinstance(t.celsius, float), "合法输入应该被统一转成 float"
    assert t.fahrenheit == 77.0, f"fahrenheit 不对：{t.fahrenheit}"

    t.celsius = 30
    assert t.celsius == 30.0
    assert t.fahrenheit == 86.0

    assert Temperature().celsius == 0.0, "默认值应该是 0 摄氏度"
    assert Temperature(-40).fahrenheit == -40.0, "摄氏 -40 度正好等于华氏 -40 度"
    assert Temperature(-273.15).celsius == -273.15, "绝对零度本身是合法的"

    try:
        t.fahrenheit = 100
    except AttributeError:
        pass
    else:
        raise AssertionError("fahrenheit 是只读的计算属性，赋值必须抛 AttributeError")

    for bad, exc_type in ((-300, ValueError), ("热", TypeError), (True, TypeError), (None, TypeError)):
        try:
            t.celsius = bad
        except exc_type:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                f"t.celsius = {bad!r} 应该抛 {exc_type.__name__}，实际抛了 {type(exc).__name__}"
            ) from exc
        else:
            raise AssertionError(f"t.celsius = {bad!r} 应该抛 {exc_type.__name__}")

    for bad, exc_type in ((-300, ValueError), ("热", TypeError)):
        try:
            Temperature(bad)
        except exc_type:
            pass
        except Exception as exc:  # noqa: BLE001
            raise AssertionError(
                f"Temperature({bad!r}) 应该抛 {exc_type.__name__}，实际抛了 {type(exc).__name__}"
            ) from exc
        else:
            raise AssertionError(f"Temperature({bad!r}) 应该抛 {exc_type.__name__}，构造函数也要走 setter")

    assert isinstance(type(t).celsius, property), "celsius 应该是个 property"
    assert isinstance(type(t).fahrenheit, property), "fahrenheit 应该是个 property"


def t_q4() -> None:
    v = Vector2D(1, 2)
    assert repr(v) == "Vector2D(1, 2)", f"repr 不对：{repr(v)}"

    assert v + Vector2D(3, 4) == Vector2D(4, 6)
    assert v * 3 == Vector2D(3, 6)
    assert 3 * v == Vector2D(3, 6), "3 * v 走的是 __rmul__，必须实现"
    assert -v == Vector2D(-1, -2)

    assert abs(Vector2D(3, 4)) == 5.0, "abs 是模长"
    assert isinstance(abs(Vector2D(3, 4)), float), "abs 应该返回 float"

    assert bool(Vector2D(0, 0)) is False, "零向量是假值"
    assert bool(Vector2D(0, 1)) is True
    assert bool(Vector2D(1, 0)) is True

    assert v != Vector2D(1, 3)
    assert (v == 3) is False, "和无关类型比较不能抛异常"

    for build in (lambda: v + 3, lambda: v * "x", lambda: v + (1, 2)):
        try:
            build()
        except TypeError:
            pass
        else:
            raise AssertionError("对不支持的类型做运算必须抛 TypeError（__add__/__mul__ 要返回 NotImplemented）")

    assert v == Vector2D(1, 2), "所有运算都必须返回新对象，不能就地改动 self"


def t_q5() -> None:
    assert [c.__name__ for c in Person.__mro__] == ["Person", "Named", "Aged", "Root", "object"], (
        f"MRO 不对：{[c.__name__ for c in Person.__mro__]}"
    )

    p = Person(name="张三", age=20)
    assert p.name == "张三", f"name 不对：{p.name!r}"
    assert p.age == 20, f"age 不对：{p.age!r}"
    assert p.log == ["Aged(20)", "Named(张三)", "Person"], f"log 不对：{p.log}"
    assert len(p.log) == 3, "每个类的 __init__ 只应该跑一次（协作继承的核心）"

    q = Person()
    assert (q.name, q.age) == ("?", 0), f"默认值不对：{q.name!r} {q.age!r}"
    assert q.log == ["Aged(0)", "Named(?)", "Person"], f"log 不对：{q.log}"

    r = Person(age=30, name="李四")
    assert (r.name, r.age) == ("李四", 30), "关键字参数的顺序不影响结果"

    assert isinstance(q, Named) and isinstance(q, Aged) and isinstance(q, Root)


def t_q6() -> None:
    assert Student.__hash__ is not None, (
        "只写了 __eq__ 没写 __hash__，Python 会把 __hash__ 设成 None，"
        "实例就再也放不进 set / 当不了字典键了"
    )

    a, b = Student(1, "张三"), Student(1, "李四")
    c = Student(2, "张三")

    assert repr(a) == "Student(sid=1, name='张三')", f"repr 不对：{repr(a)}"
    assert a == b, "学号相同就算同一个学生，名字不同也算"
    assert a != c, "学号不同就不是同一个学生，名字相同也不算"
    assert (a == "Student(1, '张三')") is False, "和无关类型比较不能抛异常"

    assert hash(a) == hash(b), "a == b 必须推出 hash(a) == hash(b)，这是硬契约"
    assert len({a, b, c}) == 2, "set 应该把 a 和 b 去重"

    d = {a: "一班"}
    assert d[b] == "一班", "用等价的另一个实例应该能查到同一个值"
    assert b in d
    assert c not in d


def t_q7() -> None:
    d = Date(2024, 2, 29)
    assert repr(d) == "Date(2024, 2, 29)", f"repr 不对：{repr(d)}"
    assert d.isoformat() == "2024-02-29", f"isoformat 不对：{d.isoformat()}"
    assert Date(2024, 1, 5).isoformat() == "2024-01-05", "月和日要补零到两位"

    assert d == Date(2024, 2, 29)
    assert d != Date(2024, 2, 28)
    assert (d == "2024-02-29") is False

    assert Date.from_iso("2024-02-29") == Date(2024, 2, 29)
    assert Date.is_leap(2024) is True
    assert Date.is_leap(1900) is False, "整百年必须能被 400 整除才是闰年"
    assert Date.is_leap(2000) is True
    assert Date.is_leap(2023) is False
    assert Date(2024, 1, 1).is_leap(2024) is True, "staticmethod 通过实例调用也应该能用"

    class DateTime(Date):
        """空的子类，只用来验证 from_iso 里的 cls 是不是多态的。"""

    assert type(Date.from_iso("2024-01-01")) is Date
    assert type(DateTime.from_iso("2024-01-01")) is DateTime, (
        "from_iso 里写死 return Date(...) 了 —— 必须用 cls(...)"
    )

    assert isinstance(Date.__dict__["from_iso"], classmethod), "from_iso 应该是 @classmethod"
    assert isinstance(Date.__dict__["is_leap"], staticmethod), "is_leap 应该是 @staticmethod"

    for bad in ((2023, 2, 29), (2024, 13, 1), (2024, 0, 1), (2024, 1, 32), (2024, 4, 31), (2024, 2, 0)):
        try:
            Date(*bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Date{bad} 是个非法日期，应该抛 ValueError")

    for bad_text in ("2023-02-29", "不是日期"):
        try:
            Date.from_iso(bad_text)
        except ValueError:
            pass
        else:
            raise AssertionError(f"Date.from_iso({bad_text!r}) 应该抛 ValueError")


def t_q8() -> None:
    import math

    try:
        Shape()
    except TypeError:
        pass
    else:
        raise AssertionError("抽象基类不能被实例化")

    assert Shape.__abstractmethods__ == frozenset({"area", "perimeter"}), (
        f"抽象方法集合不对：{Shape.__abstractmethods__}"
    )

    c = Circle(1.0)
    assert isinstance(c, Shape)
    assert c.area() == math.pi, f"圆面积不对：{c.area()}"
    assert c.perimeter() == 2 * math.pi, f"圆周长不对：{c.perimeter()}"
    assert c.describe() == "Circle: 面积=3.14 周长=6.28", f"describe 不对：{c.describe()}"

    r = Rectangle(3, 4)
    assert isinstance(r, Shape)
    assert r.area() == 12.0
    assert r.perimeter() == 14.0
    assert r.describe() == "Rectangle: 面积=12.00 周长=14.00", f"describe 不对：{r.describe()}"

    class Half(Shape):
        """只实现一半的子类。"""

        def area(self) -> float:
            return 1.0

    try:
        Half()
    except TypeError:
        pass
    else:
        raise AssertionError("没实现全部抽象方法的子类也不能被实例化")


def t_q9() -> None:
    import dataclasses
    import inspect

    Student = q9_build_student_class()
    assert Student.__name__ == "Student", f"类名应该是 Student，实际 {Student.__name__}"
    assert dataclasses.is_dataclass(Student), "这个类应该是个 dataclass"

    a = Student("张三", [90, 80, 70])
    assert a.scores == [90, 80, 70], f"scores 不对：{a.scores}"
    assert a.average == 80.0, f"average 应该由 __post_init__ 算出来，实际 {a.average}"

    b, c = Student("李四"), Student("王五")
    assert b.scores == [], f"默认值应该是空列表，实际 {b.scores}"
    assert b.average == 0.0, "空成绩的平均分应该是 0.0"
    b.scores.append(100)
    assert c.scores == [], "两个实例共享了同一个列表 —— default_factory 没写对"
    assert b.average == 0.0, "为什么改 scores 后 average 没变？想想 average 是什么时候算的"

    params = list(inspect.signature(Student).parameters)
    assert params == ["name", "scores"], f"average 不该出现在构造参数里，实际参数是 {params}"

    assert Student("A") < Student("B"), "order=True 应该生成比较运算符"
    assert sorted([Student("C"), Student("A"), Student("B")]) == [Student("A"), Student("B"), Student("C")]
    assert a == Student("张三", [90, 80, 70]), "dataclass 的 __eq__ 是按字段比较的"
    assert a != Student("李四", [90, 80, 70]), "name 不同就不相等"
    assert a != Student("张三", [90, 80]), "scores 不同 -> 算出来的 average 也不同 -> 不相等"

    assert "__slots__" in vars(Student), "slots=True 应该在类上生成 __slots__"
    assert not hasattr(a, "__dict__"), "slots=True 的实例不该有 __dict__"
    try:
        a.extra = 1
    except AttributeError:
        pass
    else:
        raise AssertionError("slots=True 的实例不能动态加属性")


def main() -> None:
    c = Checker("模块 04 · 面向对象与数据模型 练习")
    c.add("q1  手写不可变值对象 Point", t_q1)
    c.add("q2  @dataclass(frozen=True) 重写", t_q2)
    c.add("q3  @property 带校验", t_q3)
    c.add("q4  魔术方法 Vector2D", t_q4)
    c.add("q5  菱形继承与协作式 super()", t_q5)
    c.add("q6  __eq__ 与 __hash__ 契约", t_q6)
    c.add("q7  classmethod / staticmethod", t_q7)
    c.add("q8  抽象基类 ABC", t_q8)
    c.add("q9  @dataclass 进阶", t_q9)
    c.run()


if __name__ == "__main__":
    main()
