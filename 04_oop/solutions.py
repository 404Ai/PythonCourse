"""
模块 04 · 面向对象与数据模型 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每个答案下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。
"""

from __future__ import annotations

import math
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 手写不可变值对象
# ======================================================================
class Point:
    """真实数据放在 _x / _y，对外只暴露只读 property。

    这是「手写不可变」的标准手法：property 没有 setter，
    对 p.x 赋值就会抛 AttributeError。
    """

    def __init__(self, x: float, y: float) -> None:
        self._x = x
        self._y = y

    @property
    def x(self) -> float:
        return self._x

    @property
    def y(self) -> float:
        return self._y

    def __repr__(self) -> str:
        # !r 让字符串字段带上引号，目标是 eval(repr(obj)) == obj
        return f"Point(x={self._x!r}, y={self._y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Point):
            # 关键：返回 NotImplemented 而不是 False。
            # NotImplemented 的意思是「我不懂这种比较」，Python 会接着去问对方，
            # 双方都不懂才退回身份比较。返回 False 就直接剥夺了对方的发言权。
            return NotImplemented
        return (self._x, self._y) == (other._x, other._y)

    def __hash__(self) -> int:
        # 用到的字段必须和 __eq__ 用到的完全一致
        return hash((self._x, self._y))

    def __add__(self, other: "Point") -> "Point":
        if not isinstance(other, Point):
            return NotImplemented
        return Point(self._x + other._x, self._y + other._y)


# 常见错误写法：
#
# 1) 用 __slots__ 或者覆写 __setattr__ 来做不可变
#       def __setattr__(self, name, value):
#           raise AttributeError("不可变")
#    这在 __init__ 里也拦住了自己，得再加一个开关变量，代码反而更长。
#    只读 property 更简单，而且语义清楚：能读，不能写。
#
# 2) __eq__ 里直接 `return False`
#       if not isinstance(other, Point):
#           return False            # 错
#    后果：任何需要「让对方的 __eq__ 说了算」的场景全部失效。
#    比如以后有个子类想和 Point 比较，就永远没机会了。
#
# 3) __hash__ 里塞了 __eq__ 没用的字段
#       return hash((self._x, self._y, id(self)))     # 错
#    id 每次都不一样，于是 a == b 但 hash(a) != hash(b)，
#    契约被打破 —— 对象放进 set 就再也找不回来了。
#
# 4) 忘记 __hash__
#    只要类里定义了 __eq__，Python 就把 __hash__ 置成 None，
#    实例直接变成不可哈希，`{p}` 会抛 TypeError。
#    （原因见模块 README 的 4.5 节。）
#
# 5) 只写 __str__ 不写 __repr__
#    调试器里、列表里看到的还是 <Point object at 0x...>，一点用都没有。


# ======================================================================
# q2 —— @dataclass(frozen=True)
# ======================================================================
def q2_build_point_dataclass() -> type:
    """三行顶 q1 的二十行。

    frozen=True 一次性给了我们：
        - 生成 __init__
        - 生成 __repr__
        - 生成 __eq__（按字段元组比较，遇到别的类型返回 NotImplemented）
        - 生成 __hash__（因为 frozen 了，对象不可变，哈希才是安全的）
        - 生成 __setattr__ / __delattr__ 抛 FrozenInstanceError
    """

    @dataclass(frozen=True)
    class FrozenPoint:
        x: float
        y: float

    return FrozenPoint


# 常见错误写法：
#
# 1) `@dataclass` 不加 frozen
#    那就变成可变对象了，p.x = 99 能通过，而且 __hash__ 仍然是 None
#    （dataclass 的默认 eq=True 会把 __hash__ 置 None）。
#
# 2) 还想手写 __eq__ / __hash__
#    dataclass 默认 eq=True 已经生成了 __eq__，你再写一个会覆盖它，
#    但 __hash__ 是被 eq=True 置成 None 之后再生成的，
#    顺序上很容易出现「写了 __eq__，__hash__ 又变 None」。
#    要么完全交给 dataclass，要么 eq=False 全部手写，别混着来。
#
# 3) 以为 frozen=True 就是深不可变
#    frozen 只拦「给字段赋值」。如果字段本身是个 list，
#    obj.items.append(x) 照样能改。要真的不可变，字段也得选不可变类型
#    （tuple / frozenset / str），或者自己在 __post_init__ 里拷贝一份。

# 一句话总结：**先想清楚「我要的是值语义还是引用语义」，
# 再决定 @dataclass 的参数。** 值对象就 frozen=True。


# ======================================================================
# q3 —— @property 带校验
# ======================================================================
class Temperature:
    def __init__(self, celsius: float = 0.0) -> None:
        # 故意写 self.celsius 而不是 self._celsius：
        # 这样校验逻辑只有一份，构造函数和外部赋值走的是同一条路。
        self.celsius = celsius

    @property
    def celsius(self) -> float:
        return self._celsius

    @celsius.setter
    def celsius(self, value: float) -> None:
        # bool 是 int 的子类，不先拦掉的话 True 会被当成 1 度
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise TypeError(f"温度必须是数字，收到 {type(value).__name__}")
        if value < -273.15:
            raise ValueError(f"低于绝对零度：{value}")
        self._celsius = float(value)     # 统一成 float，后面读出来类型稳定

    @property
    def fahrenheit(self) -> float:
        # 没有 setter -> 只读。计算属性不需要存储，每次现算
        return self._celsius * 9 / 5 + 32


# 常见错误写法：
#
# 1) 构造函数里写 self._celsius = celsius，绕过了 setter
#    -> Temperature(-300) 构造成功，校验形同虚设。
#    这是本题最容易踩的坑：**校验的价值在「所有入口都走它」**。
#
# 2) 用 get_celsius() / set_celsius() 这种 Java 风格的方法名
#    Python 的惯例是「统一访问原则」：读的时候不要写括号。
#    一开始就写公开属性 self.celsius，需要校验时再升级成 property，
#    调用方一行都不用改。
#
# 3) 只抛 ValueError 不抛 TypeError
#    「值不合法」和「类型不对」是两类错误，调用方的处理方式完全不同。
#    TypeError 表示程序写错了，ValueError 表示数据有问题。
#
# 4) 忘了拦 bool
#    t.celsius = True 会变成 1 度，静默的错数据。
#
# 5) 以为 self._celsius 真的是私有
#    外部照样能 t._celsius = -9999。Python 靠约定，不靠强制。


# ======================================================================
# q4 —— 魔术方法 Vector2D
# ======================================================================
class Vector2D:
    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"Vector2D({self.x!r}, {self.y!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Vector2D):
            return NotImplemented
        return (self.x, self.y) == (other.x, other.y)

    def __add__(self, other: "Vector2D") -> "Vector2D":
        if not isinstance(other, Vector2D):
            return NotImplemented
        return Vector2D(self.x + other.x, self.y + other.y)

    def __mul__(self, scalar: float) -> "Vector2D":
        # bool 也是 int，这里不拦也无所谓（True 就当 1 用），
        # 但如果是业务上不允许的情况，还是显式拦掉更好
        if not isinstance(scalar, (int, float)):
            return NotImplemented
        return Vector2D(self.x * scalar, self.y * scalar)

    def __rmul__(self, scalar: float) -> "Vector2D":
        # 3 * v 时，int.__mul__(v) 不认识 Vector2D，返回 NotImplemented，
        # Python 才会回头调用 v.__rmul__(3)。复用 __mul__ 就行。
        return self.__mul__(scalar)

    def __neg__(self) -> "Vector2D":
        return Vector2D(-self.x, -self.y)

    def __abs__(self) -> float:
        # math.hypot 比自己写 sqrt(x*x + y*y) 数值上更稳（不会中间溢出）
        return math.hypot(self.x, self.y)

    def __bool__(self) -> bool:
        # 必须返回真正的 bool。返回 self.x or self.y 的话，
        # 分量是 0.0 时会返回 0.0（float），虽然真值判断等价但不规范。
        return bool(self.x or self.y)


# 常见错误写法：
#
# 1) __add__ 里直接算，不判断类型
#       return Vector2D(self.x + other.x, self.y + other.y)
#    对 v + 3 会抛 AttributeError: 'int' object has no attribute 'x'，
#    而不是干净的 TypeError: unsupported operand type(s)。
#    返回 NotImplemented 才能让 Python 生成标准错误信息，
#    也才给对方的 __radd__ 留了机会。
#
# 2) 忘记 __rmul__
#    v * 3 能跑，3 * v 报 TypeError。这两个在数学上是一回事，
#    用户不会记得哪个行哪个不行。
#
# 3) 就地修改 self 而不是返回新对象
#       def __add__(self, other):
#           self.x += other.x
#           return self
#    那么 a = b + c 会把 b 也改掉。**除非你显式在实现 __iadd__，
#    否则所有运算符都应该返回新对象。**
#
# 4) __bool__ 里写 `return self.x + self.y`
#    分量都是 0 时返回 int 0，Python 会把它当真值判断（能工作），
#    但别人读到这行会犹豫。显式 bool() 一下更清楚。
#
# 5) 定义了 __eq__ 却没定义 __hash__
#    这个类会变成不可哈希。本题没要求哈希，所以不写也行，
#    但要意识到「这是个不可哈希的类」，别放进 set。


# ======================================================================
# q5 —— 菱形继承与协作式 super()
# ======================================================================
class Root:
    def __init__(self, **kwargs) -> None:
        # 终点站：**不调用 super().__init__()**。
        # 因为 object.__init__ 不接受关键字参数，
        # 多传一个就会 TypeError: object.__init__() takes exactly one argument。
        # 协作链必须在某处停下来，这里就是那个地方。
        self.log: list[str] = []


class Named(Root):
    def __init__(self, name: str = "?", **kwargs) -> None:
        # 先让链上后面的人初始化完，自己再收尾。
        # 顺序反过来的话，Root 那句 self.log = [] 会把前面的记录清空。
        super().__init__(**kwargs)
        self.name = name
        self.log.append(f"Named({name})")


class Aged(Root):
    def __init__(self, age: int = 0, **kwargs) -> None:
        super().__init__(**kwargs)
        self.age = age
        self.log.append(f"Aged({age})")


class Person(Named, Aged):
    def __init__(self, **kwargs) -> None:
        # Person 自己不消费任何参数，只负责把整包 kwargs 往下传。
        # 这是 Mixin 风格的固定写法：*args, **kwargs 一律透传。
        super().__init__(**kwargs)
        self.log.append("Person")


# 完整走一遍 Person(name="张三", age=20)：
#
#   Person.__init__(name="张三", age=20)
#     -> super() 从 MRO 里找，下一站是 Named
#   Named.__init__(name="张三", age=20)   吃掉 name，剩下 age
#     -> super() 下一站 Aged
#   Aged.__init__(age=20)                吃掉 age，剩下空
#     -> super() 下一站 Root
#   Root.__init__()                      建出 self.log，链条结束
#     <- Aged 追加 "Aged(20)"
#     <- Named 追加 "Named(张三)"
#     <- Person 追加 "Person"
#
#   log == ["Aged(20)", "Named(张三)", "Person"]
#
# 注意每一层都在**同一个 self** 上工作 —— self 从头到尾都是那个 Person 实例。
# super() 只是「从 MRO 的哪个位置继续找」，不改变 self 是谁。

# 常见错误写法：
#
# 1) 硬写父类构造器
#       Named.__init__(self, name)
#    Person 的 MRO 是 Person -> Named -> Aged -> Root，
#    Named.__init__ 里硬写 Root.__init__(self) 的话，Aged.__init__ 永远不会被调用，
#    于是 p.age 根本不存在（AttributeError）。
#    更糟的是 Root 可能被调用两次，把 log 清空。
#
# 2) 每层都写 self.log = []
#    那就不是「记一笔」而是「清空重来」了。
#    要区分「初始化」和「追加」：Root 负责初始化，其余只 append。
#
# 3) 子类里写死参数名
#       class Person(Named, Aged):
#           def __init__(self, name="?", age=0):
#               Named.__init__(self, name)
#               Aged.__init__(self, age)
#    这样虽然能跑，但 Root 会被初始化两次（log 被清空一次），
#    而且以后再加一个 Mixin 就得改 Person 的签名。**透传才是可扩展的写法。**
#
# 4) 忘了 Root 那个「不调 super()」的终点
#    Root.__init__ 里如果也写 super().__init__(**kwargs)，
#    有 kwargs 时就会炸在 object 上。
#
# 5) 用 `super(Person, self)` 这种老写法
#    Python 3 的零参 super() 靠 __class__ 闭包单元自动取当前类，
#    改名、重构都不会出错，永远优先用它。


# ======================================================================
# q6 —— __eq__ 与 __hash__ 的契约
# ======================================================================
class Student:
    def __init__(self, sid: int, name: str) -> None:
        self.sid = sid
        self.name = name

    def __repr__(self) -> str:
        return f"Student(sid={self.sid!r}, name={self.name!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Student):
            return NotImplemented
        # 只比 sid：学号才是身份标识，名字可能改（比如改名、录入错误）
        return self.sid == other.sid

    def __hash__(self) -> int:
        # 必须只哈希 sid —— 和 __eq__ 用到的字段保持完全一致。
        # 多哈希一个 name 就会破坏契约：
        #   Student(1, "张三") == Student(1, "李四")  为 True
        #   但两者 hash 不同 -> 放进 set 里会变成两个元素，
        #   用其中一个去查另一个也查不到（KeyError）。
        # 这就是所谓的「哈希与相等必须一致」。
        return hash(self.sid)


# 常见错误写法：
#
# 1) 只写 __eq__，完全不写 __hash__
#    Python 在类创建时检测到「定义了 __eq__ 但没有 __hash__」，
#    会把 __hash__ 显式设为 None，于是：
#       hash(Student(1, "张三"))   -> TypeError: unhashable type: 'Student'
#       {Student(1, "张三")}       -> TypeError
#    这是 Python 故意设计成「快速失败」的：
#    默认的 __hash__ 是按 id 算的，一旦你改了 __eq__ 却留着它，
#    a == b 但 hash(a) != hash(b)，字典查找会静默失败 ——
#    静默的错数据比崩溃可怕得多，所以干脆不让你用。
#
# 2) __hash__ 里哈希了多余的字段
#       return hash((self.sid, self.name))     # 错
#    set 会去重失败、dict 会查不到。这个 bug 非常隐蔽：
#    单独测 hash 和单独测 == 都正常，合在一起才出问题。
#
# 3) __hash__ 里哈希了可变字段
#       return hash((self.sid, self.tags))     # tags 是个 list -> TypeError
#   就算 tags 是 tuple，只要它之后会被重新赋值，
#    对象进了 set 之后就会「找不到自己」。
#    **能当字典键的东西必须不可变。**
#
# 4) __eq__ 返回 False 而不是 NotImplemented
#       if not isinstance(other, Student): return False
#    后果：Student(1, "a") == 某个想和它比较的自定义对象 永远为 False，
#    对方连解释的机会都没有。
#
# 5) 想「只按值比较、不要哈希」时，显式写 `__hash__ = None`
#    比留着一个错误的 __hash__ 好得多 —— 至少调用方会立刻拿到 TypeError。


# ======================================================================
# q7 —— classmethod / staticmethod
# ======================================================================
_DAYS_IN_MONTH = (31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)


class Date:
    def __init__(self, year: int, month: int, day: int) -> None:
        if not 1 <= month <= 12:
            raise ValueError(f"月份必须在 1~12，收到 {month}")
        max_day = _DAYS_IN_MONTH[month - 1]
        # 用 type(self).is_leap 而不是 Date.is_leap：
        # 万一子类覆写了闰年规则，这里会自动跟着变
        if month == 2 and type(self).is_leap(year):
            max_day = 29
        if not 1 <= day <= max_day:
            raise ValueError(f"{year} 年 {month} 月没有 {day} 号")
        self.year, self.month, self.day = year, month, day

    def __repr__(self) -> str:
        return f"Date({self.year!r}, {self.month!r}, {self.day!r})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Date):
            return NotImplemented
        return (self.year, self.month, self.day) == (other.year, other.month, other.day)

    def isoformat(self) -> str:
        return f"{self.year:04d}-{self.month:02d}-{self.day:02d}"

    @classmethod
    def from_iso(cls, text: str) -> "Date":
        """备用构造器。注意 cls 而不是 Date。"""
        year, month, day = (int(part) for part in text.split("-"))
        # 校验全部交给 __init__，这里不重复实现
        return cls(year, month, day)

    @staticmethod
    def is_leap(year: int) -> bool:
        return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)


# 常见错误写法：
#
# 1) from_iso 里写死 return Date(year, month, day)
#    子类 DateTime.from_iso("2024-01-01") 会拿到一个 Date 实例，
#    而不是 DateTime —— 多态直接断了。
#    **@classmethod 存在的唯一理由就是那个 cls。**
#
# 2) 用 @staticmethod 写 from_iso
#    @staticmethod 拿不到 cls，只能写死类名，等于放弃多态。
#    判断标准很简单：**需要用 cls 就用 @classmethod。**
#
# 3) is_leap 写成模块级函数
#    能跑，但失去了「这是日期相关工具」的归属提示。
#    不过反过来，如果某个函数跟这个类八竿子打不着，
#    就**应该**放模块级，别硬塞进类里。
#
# 4) 在 __init__ 里不做校验，指望调用方自觉
#    这次 from_iso("2023-02-29") 就悄悄造出了一个不存在的日期。
#    校验放在 __init__ 里，所有构造入口（含将来的备用构造器）自动受益。
#
# 5) 闰年判断写成 year % 4 == 0
#    1900 年会错判成闰年。整百年必须能被 400 整除，这个坑考了三十年。
#
# 6) 日期比较用字符串比大小
#    isoformat() 的字典序恰好和日期序一致，但 `d.isoformat() > "2024-1-5"` 这种
#    混着不补零的输入就会出错。要比较就老老实实比元组，或者实现 __lt__。


# ======================================================================
# q8 —— 抽象基类
# ======================================================================
class Shape(ABC):
    @abstractmethod
    def area(self) -> float:
        """子类必须实现。"""

    @abstractmethod
    def perimeter(self) -> float:
        """子类必须实现。"""

    def describe(self) -> str:
        # 模板方法：父类定流程，子类填细节。
        # 注意用 type(self).__name__ 而不是写死类名 —— 子类也能用。
        return f"{type(self).__name__}: 面积={self.area():.2f} 周长={self.perimeter():.2f}"


class Circle(Shape):
    def __init__(self, r: float) -> None:
        self.r = r

    def area(self) -> float:
        return math.pi * self.r ** 2

    def perimeter(self) -> float:
        return 2 * math.pi * self.r


class Rectangle(Shape):
    def __init__(self, width: float, height: float) -> None:
        self.width = width
        self.height = height

    def area(self) -> float:
        return self.width * self.height

    def perimeter(self) -> float:
        # 记得加括号：width + height * 2 是另一个意思
        return 2 * (self.width + self.height)


# 常见错误写法：
#
# 1) 只写 @abstractmethod 不继承 ABC
#    在 Python 3 里 `class Shape(metaclass=ABCMeta)` 或 `class Shape(ABC)` 都行，
#    但不写的话 abstractmethod 只是个普通装饰器，**一点强制力都没有**：
#    照样能 Shape()，而且不实现 area 的子类也能实例化。
#
# 2) 以为 abc 会检查签名
#    不会。子类写 `def area(self, extra)` 甚至 `area = 42` 都算「已覆盖」，
#    只检查名字在不在。**abc 拦的是「忘了实现」，不是「实现错了」。**
#    要检查签名得靠类型检查器（mypy / pyright）。
#
# 3) 抽象方法里写 raise NotImplementedError
#    没必要 —— 抽象类根本不能实例化，这个方法永远不会被调到。
#    函数体留 `...` 或者一段 docstring 就够了。
#    （不过作为一种「万一被绕过」的防御也不算错，只是啰嗦。）
#
# 4) 为了用抽象基类，让一堆无关的类都去继承它
#    abc 是**名义子类型**：必须显式继承。这意味着你的类要反向依赖别人的抽象基类。
#    Python 更推荐 Protocol（结构子类型）：只看「有没有这些方法」，
#    不需要继承关系。**想复用代码 / 提供默认实现才用 ABC；
#    只想描述接口形状，用 Protocol + 类型注解。**
#
# 5) 忘了 describe 是具体方法
#    它调用了抽象的 area()，这在 Python 里完全合法 ——
#    只要实例化时方法都已经存在，运行期就不会有问题。
#    这就是「模板方法模式」在 Python 里的样子。


# ======================================================================
# q9 —— @dataclass 进阶
# ======================================================================
def q9_build_student_class() -> type:
    @dataclass(order=True, slots=True)
    class Student:
        name: str
        # 可变默认值必须用 default_factory：
        # 写 = [] 的话那个列表在**类创建时**只造一次，所有实例共享。
        # （dataclasses 对 list/dict/set 会直接抛 ValueError 拦住你，
        #   但对自定义的可变对象它看不出来，所以养成习惯最保险。）
        scores: list[int] = field(default_factory=list)
        # init=False：不出现在构造参数里，由 __post_init__ 填
        average: float = field(init=False, default=0.0)

        def __post_init__(self) -> None:
            # __init__ 跑完之后被自动调用，用来算派生字段 / 做校验
            self.average = sum(self.scores) / len(self.scores) if self.scores else 0.0

    return Student


# 常见错误写法：
#
# 1) scores: list[int] = []
#    dataclasses 会直接抛：
#       ValueError: mutable default <class 'list'> for field scores is not allowed
#    如果换成自定义类的实例（比如 = Config()），它检测不出来，
#    于是所有 Student 共享同一个 Config —— 模块 01 里的类属性陷阱重演。
#
# 2) 用 = field(default=list) 代替 default_factory
#    default 传的是「值」不是「工厂」，传 list 这个类型对象本身，
#    结果 scores 默认变成 <class 'list'>，类型完全不对。
#
# 3) 把 average 算在 __init__ 里，同时又让 dataclass 生成 __init__
#    dataclass 生成的 __init__ 会覆盖你手写的那个，你的代码直接消失。
#    派生字段只有两个去处：__post_init__，或者 field(init=False) + property。
#
# 4) 期望改了 scores 之后 average 自动更新
#    average 是**快照**，不是计算属性。print(b.average) 仍然是 0.0。
#    要「永远最新」，就别存字段，用 @property 现算 ——
#    但那样它就不参与 __eq__ / order 了，需要自己权衡。
#
# 5) order=True 却把不重要的字段写在前面
#    比较的是「所有参与比较的字段组成的元组」，字典序。
#    想让 tag 不参与比较，要写 field(compare=False)。
#    另外注意：order=True **不会**生成 __hash__，
#    这个类默认仍然不可哈希（除非同时加 frozen=True）。
#
# 6) slots=True 之后还想给实例挂临时属性
#    会抛 AttributeError。另外 slots=True 会让 dataclass **重新创建一个类对象**，
#    所以 `isinstance` 里用的那个类引用要拿返回值，别拿装饰前的。
#
# 7) frozen=True + __post_init__ 里给字段赋值
#    会抛 FrozenInstanceError，得用 object.__setattr__(self, "name", value)。
#    这是 frozen 类里唯一合法的「写字段」方式，知道有这回事就行。


# ======================================================================
# 自测（和 exercises.py 保持一致）
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
    c = Checker("模块 04 · 面向对象与数据模型 参考答案")
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
