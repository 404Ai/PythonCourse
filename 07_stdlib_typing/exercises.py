"""
模块 07 · 标准库与类型注解 —— 练习

做法：
    1. 把每个函数里的 `raise NotImplementedError` 换成你的实现
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

本模块的题目**不需要写文件**，所有测试都在内存里跑（StringIO / 纯数据），
所以你不用担心留下残留文件。

提示：
    - 所有注解都不影响运行时。注解写错了 Python 也不会拦你，
      真正拦你的是测试断言。所以「想清楚契约」比「注解好看」重要得多。
    - 报错的那一行可以下断点，按 F5 用调试器看中间变量。
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import re
import sys
from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generic, Literal, Protocol, TypedDict, TypeVar, runtime_checkable

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker

#: 优先级只允许这三个值。写成 Literal 之后，mypy 会把 "urgent" 这种拼写错误
#: 当场标红，IDE 也能给你补全 —— 比裸 str 强很多。
#: 注意：运行时它就是个普通的类型别名，什么都不检查。
Priority = Literal["low", "medium", "high"]


# ======================================================================
# q1 —— TypedDict + 校验函数
# ======================================================================
class _TaskRequired(TypedDict):
    """必填字段。单独抽一个基线类，是为了绕开下面这个坑。"""

    id: int
    title: str


class Task(_TaskRequired, total=False):
    """一条任务记录。

    `total=False` 的作用范围是**这个类里新声明的**键，
    所以继承来的 id / title 仍然是必填的，priority / tags / done 变成可选。

    为什么不用 `NotRequired[str]`？
        本文件开头有 `from __future__ import annotations`，
        所有注解都被存成**字符串**，`NotRequired[...]` 这层包装
        在运行时不会被解析出来，结果 `__required_keys__` 会算错。
        （这是 3.14.7 实测行为。）
    """

    priority: str
    tags: list[str]
    done: bool


def q1_validate_task(raw: dict) -> Task:
    """把任意 dict 校验并规范化成一条 Task。

    规则（**按顺序**检查，第一个不满足的就抛异常）：

        0. raw 不是 dict                        -> TypeError（消息里要有 "dict"）
        1. "id" 不在 raw 里                      -> ValueError，消息含 "id"
        2. "id" 不是 int                         -> ValueError，消息含 "id"
           **bool 是 int 的子类，True/False 必须被拒绝**
        3. "id" <= 0                             -> ValueError，消息含 "id"
        4. "title" 不在 raw 里，或去掉首尾空白后为空 -> ValueError，消息含 "title"
        5. "title" 不是 str                       -> ValueError，消息含 "title"
        6. "priority"（可选，默认 "medium"）
           不在 ("low", "medium", "high") 里      -> ValueError，消息含 "priority"
        7. "tags"（可选，默认 []）
           不是 list，或里面有元素不是 str         -> ValueError，消息含 "tags"
        8. "done"（可选，默认 False）
           不是 bool                             -> ValueError，消息含 "done"

    返回值（**正好**这 5 个键，顺序无所谓）：
        {
            "id": int,              # 原样
            "title": str,           # 去掉首尾空白
            "priority": str,
            "tags": list[str],      # 必须是**新列表**，不能和输入共用同一个对象
            "done": bool,
        }

    提示：
        - 校验 bool 时 `isinstance(x, int)` 会放行 True，先判 `isinstance(x, bool)`。
        - 抛出的异常里带上字段名，调用方（和用户）才知道是哪一项出了问题。
        - `raw.get("priority", "medium")` 比 `if "priority" in raw` 简洁。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— Protocol：结构化子类型
# ======================================================================
@runtime_checkable
class Shape(Protocol):
    """任何「有 name() 和 area()」的东西都算 Shape —— 不需要继承。"""

    def name(self) -> str:
        """形状的名字。"""
        ...

    def area(self) -> float:
        """面积。"""
        ...


class Circle:
    """圆形。**不要**继承 Shape，也不要在类体里提到 Shape。"""

    def __init__(self, radius: float) -> None:
        # TODO: 保存半径；半径 <= 0 抛 ValueError("半径必须为正")
        raise NotImplementedError

    def name(self) -> str:
        # TODO: 返回 "circle"
        raise NotImplementedError

    def area(self) -> float:
        # TODO: 返回 math.pi * r ** 2
        raise NotImplementedError


class Square:
    """正方形。同样不继承 Shape。"""

    def __init__(self, side: float) -> None:
        # TODO: 保存边长；边长 <= 0 抛 ValueError("边长必须为正")
        raise NotImplementedError

    def name(self) -> str:
        # TODO: 返回 "square"
        raise NotImplementedError

    def area(self) -> float:
        # TODO: 返回 side ** 2
        raise NotImplementedError


def q2_total_area(shapes: Sequence[Shape]) -> float:
    """把所有形状的面积加起来。

    注意参数类型是 Sequence[Shape]，但 Circle / Square 都不继承 Shape ——
    这正是 Protocol 的意义：只要**结构上**对得上就行。
    """
    raise NotImplementedError


def q2_describe_all(shapes: Sequence[Shape]) -> list[str]:
    """返回描述字符串列表，每项形如 "circle=3.1416"（面积保留 4 位小数）。

    排序规则：先按面积降序，面积相同按名字字典序升序。
    空列表 -> []
    """
    raise NotImplementedError


def q2_is_shape(obj: object) -> bool:
    """运行时判断 obj 是不是 Shape。

    用 `isinstance(obj, Shape)` —— 它要求 Shape 被 @runtime_checkable 装饰过。
    提醒：这个检查**只看有没有同名方法**，不看签名，所以别拿它当参数校验。
    """
    raise NotImplementedError


# ======================================================================
# q3 —— argparse：把参数解析拆成可测试的两半
# ======================================================================
def q3_build_parser() -> argparse.ArgumentParser:
    """构造一个 `prog="todo"` 的命令行解析器。

    结构：

        todo add <title> [--priority {low,medium,high}] [--tag TAG]... [-v]
        todo list [--limit N] [--all] [--sort {id,priority}]
        todo done <ids> [<ids> ...]
        todo rm [-n N] [--force]

    要求：
        - 子命令用 add_subparsers(dest="command", required=True)
          —— 一个子命令都不给时要报错退出，而不是返回一个空 Namespace
        - add：title 是位置参数；--priority 用 choices，默认 "medium"；
          --tag 用 action="append"（可重复，默认空列表）；
          -v/--verbose 用 action="store_true"
        - list：--limit 用 type=int，默认 10；--all 用 action="store_true"；
          --sort 用 choices=("id", "priority")，默认 "id"
        - done：ids 是位置参数，type=int，nargs="+"（至少一个）
        - rm：-n/--count 用 type=int，默认 1；--force 用 action="store_true"
        - 每个参数都写 help=，这样自动生成的 -h 才有用

    提示：把 parser 的构造和 parse_args 分开，测试才能直接喂 argv 列表，
          不用去改 sys.argv（那会污染整个进程）。
    """
    raise NotImplementedError


def q3_parse(argv: list[str]) -> dict:
    """解析 argv，返回 `vars(namespace)`（也就是一个普通 dict）。

    例：
        q3_parse(["add", "写作业"])
            -> {"command": "add", "title": "写作业",
                "priority": "medium", "tag": [], "verbose": False}
        q3_parse(["done", "1", "2"])
            -> {"command": "done", "ids": [1, 2]}

    注意：argv 里**不含**程序名（不传 sys.argv[0]）。
    参数非法时 argparse 会自己 SystemExit(2)，不用你处理。
    """
    raise NotImplementedError


# ======================================================================
# q4 —— re：解析日志行
# ======================================================================
LOG_LINE = "2024-03-01 12:00:05 INFO  处理任务 42"

#: 供参考的日志格式（字段之间可能有多个空格）：
#:     日期(YYYY-MM-DD) 空白 时间(HH:MM:SS) 空白 级别(大写字母) 空白 消息
#: 消息是这一行的剩余部分，可以包含空格。


def q4_parse_line(line: str) -> dict[str, str] | None:
    """解析一行日志，成功返回 dict，失败返回 None。

    成功时正好这 4 个键：
        {"date": "2024-03-01", "time": "12:00:05",
         "level": "INFO", "message": "处理任务 42"}

    要求：
        - 用**命名分组**取字段，别用下标（group(1)/group(2) 一改格式全崩）
        - 必须从行首开始匹配（用 re.match 或 ^ 锚点，不要用 search）
        - 级别只接受大写字母
        - message 前面的多个空格不能被带进结果里
        - 解析不出来（包括空行、格式不对）返回 None，**不要抛异常**

    示例：
        q4_parse_line("2024-03-01 12:00:05 INFO  处理任务 42")
            -> {"date": "2024-03-01", "time": "12:00:05",
                "level": "INFO", "message": "处理任务 42"}
        q4_parse_line("这行格式不对") -> None
        q4_parse_line("2024-03-01 12:00:05 info 小写级别") -> None
    """
    raise NotImplementedError


def q4_parse_lines(text: str) -> tuple[list[dict[str, str]], int]:
    """把整段文本按行解析。

    返回 (解析成功的记录列表, 无法解析的行数)。

    规则：
        - 空行 / 纯空白行直接**跳过**：既不加进结果，也不计入失败数
        - 其余无法解析的行计入失败数

    例：
        text = "2024-03-01 12:00:05 INFO ok\\n\\n坏行\\n"
        -> ([{...}], 1)
    """
    raise NotImplementedError


def q4_filter_messages(text: str, level: str) -> list[str]:
    """返回文本里所有指定级别的**消息**（按出现顺序）。

    例：q4_filter_messages(text, "ERROR") -> ["任务 43 失败", "任务 44 失败"]
    级别不存在 -> []
    """
    raise NotImplementedError


def q4_mask_secrets(text: str) -> str:
    """把敏感字段的值替换成 ***。

    规则：
        - 键名是 password / token / secret 三者之一，**大小写不敏感**
        - 值的结束位置：空白字符、分号 `;` 或字符串结尾
        - 值可以是空的（`password=` 也要处理）
        - 替换后保留键名原本的大小写

    例：
        "user=alice password=hunter2 token=abc;ok"
            -> "user=alice password=*** token=***;ok"
        "PASSWORD=xyz" -> "PASSWORD=***"
        "password="    -> "password=***"
        "没有敏感字段"  -> 原样返回

    提示：用 re.sub + `\\g<name>` 反向引用，或者传一个函数做替换。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— datetime：时区、格式化、时间差
# ======================================================================
UTC = timezone.utc
#: 东八区。注意这是**固定偏移**，不处理历史上的夏令时。
CST = timezone(timedelta(hours=8))


def q5_to_cst(dt: datetime) -> datetime:
    """把 dt 转成 +08:00 时区的 aware datetime。

    - dt 是 naive（没有 tzinfo）时，**假定它表示 UTC 时间**
    - dt 是 aware 时，按绝对时刻转换

    例：
        q5_to_cst(datetime(2024, 3, 1, 12, 0))
            -> datetime(2024, 3, 1, 20, 0, tzinfo=CST)
        q5_to_cst(datetime(2024, 3, 1, 12, 0, tzinfo=UTC))
            -> datetime(2024, 3, 1, 20, 0, tzinfo=CST)

    提示：nanive 的要先 `.replace(tzinfo=UTC)` 再 `.astimezone(CST)`。
          直接 astimezone 在 naive 上会按**本地时区**解释 —— 换台机器结果就变。
    """
    raise NotImplementedError


def q5_parse(stamp: str) -> datetime:
    """解析 ISO 8601 时间戳，返回 **aware** datetime。

    - 用 `datetime.fromisoformat`（不要自己拼 strptime 格式串）
    - 解析结果没有时区信息时，抛 `ValueError`，消息里含 "时区"

    例：
        q5_parse("2024-03-01T20:00:00+08:00")
            -> datetime(2024, 3, 1, 20, 0, tzinfo=CST)
        q5_parse("2024-03-01 12:00:00") -> ValueError
        q5_parse("这不是时间")           -> ValueError
    """
    raise NotImplementedError


def q5_to_iso(dt: datetime) -> str:
    """把 aware datetime 转成 ISO 8601 字符串；naive 时抛 ValueError（消息含 "时区"）。"""
    raise NotImplementedError


def q5_days_between(d1: date, d2: date) -> int:
    """两个日期之间相差的**绝对**天数。

        q5_days_between(date(2024, 3, 1), date(2024, 3, 10)) -> 9
        q5_days_between(date(2024, 3, 10), date(2024, 3, 1)) -> 9
        q5_days_between(date(2024, 3, 1), date(2024, 3, 1))  -> 0
    """
    raise NotImplementedError


def q5_humanize_delta(td: timedelta) -> str:
    """把时间差转成人话，只显示 天 / 小时 / 分 三个单位。

    规则：
        - 负数：先取绝对值，结果前面加 "-"
        - 秒和微秒全部忽略（只到分钟）
        - 为零的单位**不显示**
        - 全为 0 时返回 "0 分"
        - 各部分用一个空格连接

    例：
        timedelta(days=2, hours=3, minutes=5) -> "2 天 3 小时 5 分"
        timedelta(hours=1)                    -> "1 小时"
        timedelta(minutes=90)                 -> "1 小时 30 分"
        timedelta(days=1, minutes=1) 取负      -> "-1 天 1 分"
        timedelta(seconds=30)                 -> "0 分"
        timedelta(0)                          -> "0 分"

    提示：td.days 是「整天」（负数时是向负无穷取整，很反直觉），
          td.seconds 是「去掉整天后的秒数」，永远是 0..86399。
          所以先用 abs(td) 处理负数最省事。
    """
    raise NotImplementedError


def q5_now_utc() -> datetime:
    """返回当前的 aware UTC 时间。

    这是本模块推荐的存库姿势：内部一律用 aware UTC，
    只在**展示**的时候转成本地时区。
    """
    raise NotImplementedError


# ======================================================================
# q6 —— logging：配置独立 logger 并用 StringIO 验证输出
# ======================================================================
LOG_FORMAT = "%(levelname)s|%(name)s|%(message)s"


def q6_make_logger(
    name: str,
    stream: io.StringIO,
    level: int = logging.DEBUG,
    handler_level: int = logging.NOTSET,
) -> logging.Logger:
    """造一个「干净」的 logger，满足：

        - 名字是 name
        - logger 自身的级别是 level
        - `propagate = False`（不往根 logger 冒泡，免得和别人的 handler 打架）
        - 挂**恰好一个** StreamHandler，输出到 stream
        - handler 的级别是 handler_level
        - formatter 用模块级常量 LOG_FORMAT
        - 如果这个 logger 之前已经被配置过，先把旧 handler 全摘掉再挂新的
          （否则同一个 logger 会被调用两次 `q6_make_logger` 后输出翻倍）

    返回这个 logger。

    提示：`logging.getLogger(name)` 对同一个名字返回的是**同一个对象**，
          这是 logging 的全局注册表机制，不是 bug。
    """
    raise NotImplementedError


def q6_safe_divide(logger: logging.Logger, a: float, b: float) -> float:
    """带日志的除法。

    - 成功：`logger.debug("计算 %s / %s = %s", a, b, result)`，返回结果
    - b == 0：用 `logger.exception(...)` 打日志（**要带上 traceback**），
      然后返回 0.0
    - 其它异常：不用管，让它传播

    要求：
        - 用 `%s` 占位符做**延迟格式化**，不要用 f-string 拼好再传进去
          （被过滤掉的日志就不用付出格式化的代价）
        - b == 0 的日志级别是 ERROR，消息里要有 a 和 b 的值
        - 消息内容不限，但捕获到的输出里必须能看到 "ZeroDivisionError"
          和 "Traceback" 字样
    """
    raise NotImplementedError


# ======================================================================
# q7 —— dataclasses 进阶
# ======================================================================
@dataclass
class LineItem:
    """订单行。

    - name: 商品名，去空白后不能为空，否则 ValueError（消息含 "name"）
    - price: 单价，必须 > 0，否则 ValueError（消息含 "price"）
    - qty: 数量，默认 1，必须 >= 0，否则 ValueError（消息含 "qty"）
    - total: **派生字段**，`field(init=False)`，由 __post_init__ 算出 price * qty
    """

    name: str
    price: float
    qty: int = 1
    total: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        # TODO:
        #   1. name 去空白后为空 -> raise ValueError("name 不能为空")
        #   2. price <= 0        -> raise ValueError("price 必须为正数")
        #   3. qty < 0           -> raise ValueError("qty 不能为负数")
        #   4. name 存成去空白后的形式（提示：赋值给 self.name）
        #   5. self.total = self.price * self.qty
        raise NotImplementedError


@dataclass
class Order:
    """一张订单。

    - order_id: 订单号，不能为空
    - items: 行列表，**必须**用 `field(default_factory=list)`
      —— 直接写 `items: list[LineItem] = []` 会被 dataclass 当场拒绝，
         而且就算不拒绝也会让所有订单共用同一个列表
    - note: 备注，默认 ""，`repr=False`（太长，别塞进 repr）
    - item_count: 派生字段，`field(init=False)`，由 __post_init__ 算出 len(items)
    """

    order_id: str
    items: list[LineItem] = field(default_factory=list)
    note: str = field(default="", repr=False)
    item_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        # TODO: order_id 去空白后为空 -> ValueError("order_id 不能为空")
        #       然后 self.item_count = len(self.items)
        raise NotImplementedError


def q7_order_total(order: Order) -> float:
    """订单总金额 = 所有行 total 之和。空订单 -> 0.0"""
    raise NotImplementedError


def q7_order_to_json(order: Order) -> str:
    """把订单序列化成 JSON 字符串。

    要求：
        - 先 `asdict(order)` 变成普通 dict
        - `ensure_ascii=False`：中文要**原样**出现在结果里
        - `indent=2`：要有换行，方便人看
        - 不要用 `default=str` 之类的逃避手段（这里全都是 JSON 原生类型）

    注意：`asdict` 是**深拷贝**，改它的返回值不会影响原对象。
    """
    raise NotImplementedError


def q7_order_from_json(text: str) -> Order:
    """把 q7_order_to_json 的输出还原成 Order。

    要求：
        - 每一行还原成 LineItem(name=..., price=..., qty=...)
          —— **不要**把 total 也传进去（它是 init=False 的派生字段，
             传了会 TypeError，而且交给 __post_init__ 重算才是对的）
        - 还原出来的对象应该满足 `asdict(还原结果) == asdict(原对象)`
    """
    raise NotImplementedError


# ======================================================================
# q8 —— TypeVar 与 Generic
# ======================================================================
T = TypeVar("T")
K = TypeVar("K")


class Stack(Generic[T]):
    """泛型栈（后进先出）。

    - `Stack[int]()` 在**运行时**只是 `Stack()` 加一个类型标记，不做任何检查
    - push(item)
    - pop() -> T：弹栈顶并返回；空栈抛 IndexError("空栈")
    - peek() -> T：只看不弹；空栈抛 IndexError("空栈")
    - __len__ / __bool__
    - __iter__：从栈顶往栈底迭代
    - to_list() -> list[T]：同样从栈顶往栈底
    """

    def __init__(self) -> None:
        # TODO: self._items: list[T] = []
        raise NotImplementedError

    def push(self, item: T) -> None:
        raise NotImplementedError

    def pop(self) -> T:
        raise NotImplementedError

    def peek(self) -> T:
        raise NotImplementedError

    def __len__(self) -> int:
        raise NotImplementedError

    def __bool__(self) -> bool:
        raise NotImplementedError

    def __iter__(self):
        # TODO: 从栈顶往栈底迭代（可以用 reversed 或倒序切片）
        raise NotImplementedError

    def to_list(self) -> list[T]:
        raise NotImplementedError


def q8_chunked(items: Sequence[T], size: int) -> list[list[T]]:
    """把序列按 size 切成若干段。

        q8_chunked([1, 2, 3, 4, 5], 2) -> [[1, 2], [3, 4], [5]]
        q8_chunked([], 3)              -> []
        q8_chunked([1], 3)             -> [[1]]

    size <= 0 抛 ValueError。
    """
    raise NotImplementedError


def q8_unique(items: Iterable[T]) -> list[T]:
    """去重，**保持首次出现的顺序**。

        q8_unique([3, 1, 3, 2, 1]) -> [3, 1, 2]
        q8_unique([])              -> []

    提示：`dict.fromkeys(items)` 一步到位 —— dict 保序，而且比手写
          `seen` 集合更短。别用 `list(set(items))`，那会打乱顺序。
    """
    raise NotImplementedError


def q8_group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """按 key(item) 分组，组内保持原顺序。

        q8_group_by(["apple", "avocado", "banana"], lambda s: s[0])
            -> {"a": ["apple", "avocado"], "b": ["banana"]}
        q8_group_by([], lambda x: x) -> {}

    返回值必须是**普通 dict**（不是 defaultdict），
    而且访问不存在的键不能把键插进去。
    """
    raise NotImplementedError


# ======================================================================
# q9 —— collections 实战
# ======================================================================
def q9_word_count(text: str) -> Counter[str]:
    """统计词频。

    规则：
        - 先把文本转小写
        - 「词」= 连续的字母或数字（正则 `[a-z0-9]+`），
          其它字符（空格、标点、汉字）都是分隔符
        - 返回 Counter，**不要**过滤任何词

    例：
        q9_word_count("Hello, hello! World")   -> Counter({"hello": 2, "world": 1})
        q9_word_count("")                      -> Counter()
    """
    raise NotImplementedError


def q9_top_n(counts: Counter[str], n: int) -> list[tuple[str, int]]:
    """取词频最高的 n 个，返回 [(词, 次数), ...]。

    排序规则：先按次数**降序**，次数相同按词**字典序升序**。
    （注意：`Counter.most_common` 在并列时的顺序是插入顺序，不确定，不能用。）

    n <= 0 抛 ValueError；n 大于总词数就返回全部。

    例：
        q9_top_n(Counter({"a": 2, "b": 2, "c": 1}), 2)
            -> [("a", 2), ("b", 2)]        # a 和 b 次数相同，按字典序
    """
    raise NotImplementedError


def q9_group_records(records: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    """把 (分组名, 值) 的序列聚成 {分组名: [值, ...]}。

        q9_group_records([("研发", "张三"), ("市场", "李四"), ("研发", "王五")])
            -> {"研发": ["张三", "王五"], "市场": ["李四"]}

    要求：
        - 组内保持输入顺序
        - 返回值是**普通 dict**
        - 空输入 -> {}

    提示：`defaultdict(list)` 写起来最舒服，但别忘了最后
          `dict(...)` 转回普通 dict —— 否则调用方 `result["不存在的键"]`
          会**静默地**插一个新键进去。
    """
    raise NotImplementedError


def q9_recent(items: Iterable[T], n: int) -> list[T]:
    """返回序列里**最后** n 个元素。

        q9_recent([1, 2, 3, 4, 5], 2) -> [4, 5]
        q9_recent([1, 2], 5)          -> [1, 2]
        q9_recent([], 3)              -> []

    n <= 0 抛 ValueError。
    提示：deque(maxlen=n) 会在追加时自动挤掉最老的元素 ——
          即使输入是上千万条，也只占 n 个位置。
    """
    raise NotImplementedError


# ======================================================================
# 自测
# ======================================================================
def t_q1() -> None:
    # 先把 TypedDict 声明本身检查掉
    assert Task.__required_keys__ == frozenset({"id", "title"}), (
        f"Task.__required_keys__ 应该是 {{'id', 'title'}}，实际 {Task.__required_keys__}。"
        f"本文件有 from __future__ import annotations，NotRequired 不会被识别，"
        f"请用 _TaskRequired + total=False 继承的写法。"
    )
    assert Task.__optional_keys__ == frozenset({"priority", "tags", "done"}), \
        Task.__optional_keys__

    # 最小合法输入
    assert q1_validate_task({"id": 1, "title": "  写作业  "}) == {
        "id": 1, "title": "写作业", "priority": "medium", "tags": [], "done": False,
    }, q1_validate_task({"id": 1, "title": "  写作业  "})

    # 全字段
    full = q1_validate_task({
        "id": 7, "title": "复习", "priority": "high",
        "tags": ["期末", "重要"], "done": True,
    })
    assert full == {"id": 7, "title": "复习", "priority": "high",
                    "tags": ["期末", "重要"], "done": True}, full
    assert type(full) is dict, "TypedDict 在运行时就是 dict"

    # tags 必须是新列表，不能和输入共用
    src_tags = ["a"]
    result = q1_validate_task({"id": 1, "title": "t", "tags": src_tags})
    result["tags"].append("b")
    assert src_tags == ["a"], "返回的 tags 必须是一个新列表，不能和输入的 list 共用"

    # 逐条错误
    def expect_error(payload, needle: str, exc_type=ValueError) -> None:
        try:
            q1_validate_task(payload)
        except exc_type as exc:
            assert needle in str(exc), f"{payload!r} 的报错消息里应该有 {needle!r}: {exc}"
        else:
            raise AssertionError(f"{payload!r} 应该抛 {exc_type.__name__}")

    expect_error("不是 dict", "dict", TypeError)
    expect_error([1, 2], "dict", TypeError)
    expect_error({"title": "t"}, "id")
    expect_error({"id": "1", "title": "t"}, "id")
    expect_error({"id": True, "title": "t"}, "id")
    expect_error({"id": 1.0, "title": "t"}, "id")
    expect_error({"id": 0, "title": "t"}, "id")
    expect_error({"id": -3, "title": "t"}, "id")
    expect_error({"id": 1}, "title")
    expect_error({"id": 1, "title": ""}, "title")
    expect_error({"id": 1, "title": "   "}, "title")
    expect_error({"id": 1, "title": 42}, "title")
    expect_error({"id": 1, "title": "t", "priority": "urgent"}, "priority")
    expect_error({"id": 1, "title": "t", "priority": "HIGH"}, "priority")
    expect_error({"id": 1, "title": "t", "tags": "a,b"}, "tags")
    expect_error({"id": 1, "title": "t", "tags": [1, 2]}, "tags")
    expect_error({"id": 1, "title": "t", "done": 1}, "done")
    expect_error({"id": 1, "title": "t", "done": "yes"}, "done")

    # done=False 是合法的（别把 falsy 当成「没提供」）
    assert q1_validate_task({"id": 1, "title": "t", "done": False})["done"] is False


def t_q2() -> None:
    import math

    c = Circle(1.0)
    s = Square(2.0)

    # 两个类都不继承 Shape
    assert Circle.__bases__ == (object,), Circle.__bases__
    assert Square.__bases__ == (object,), Square.__bases__
    assert c.name() == "circle", c.name()
    assert s.name() == "square", s.name()
    assert abs(c.area() - math.pi) < 1e-9, c.area()
    assert s.area() == 4.0, s.area()

    # 同一个函数接受两个毫无关系的类
    total = q2_total_area([c, s])
    assert abs(total - (math.pi + 4.0)) < 1e-9, total
    assert q2_total_area([]) == 0.0

    # 排序：面积降序；面积相同按名字字典序
    assert q2_describe_all([c, s]) == ["square=4.0000", "circle=3.1416"], \
        q2_describe_all([c, s])
    assert q2_describe_all([]) == []

    # runtime_checkable 的 isinstance
    assert q2_is_shape(c) is True
    assert q2_is_shape(s) is True
    assert q2_is_shape(object()) is False
    assert q2_is_shape(42) is False
    assert q2_is_shape("circle") is False

    # 非法参数
    for factory in (Circle, Square):
        try:
            factory(0)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{factory.__name__}(0) 应该抛 ValueError")
        try:
            factory(-1)
        except ValueError:
            pass
        else:
            raise AssertionError(f"{factory.__name__}(-1) 应该抛 ValueError")


def t_q3() -> None:
    assert q3_parse(["add", "写作业"]) == {
        "command": "add", "title": "写作业",
        "priority": "medium", "tag": [], "verbose": False,
    }, q3_parse(["add", "写作业"])

    assert q3_parse(["add", "写作业", "--priority", "high",
                     "--tag", "期末", "--tag", "重要", "-v"]) == {
        "command": "add", "title": "写作业", "priority": "high",
        "tag": ["期末", "重要"], "verbose": True,
    }, q3_parse(["add", "写作业", "--priority", "high", "--tag", "期末",
                 "--tag", "重要", "-v"])

    # 再解析一次同一套参数，确认 append 的默认列表没被上一次污染
    again = q3_parse(["add", "别的"])
    assert again["tag"] == [], f"默认值被污染了: {again['tag']}"

    assert q3_parse(["list"]) == {
        "command": "list", "limit": 10, "all": False, "sort": "id",
    }, q3_parse(["list"])
    assert q3_parse(["list", "--limit", "3", "--all", "--sort", "priority"]) == {
        "command": "list", "limit": 3, "all": True, "sort": "priority",
    }, q3_parse(["list", "--limit", "3", "--all", "--sort", "priority"])
    assert q3_parse(["list", "--limit", "0"])["limit"] == 0
    assert q3_parse(["list", "--limit", "-5"])["limit"] == -5

    assert q3_parse(["done", "1", "2", "3"]) == {
        "command": "done", "ids": [1, 2, 3],
    }, q3_parse(["done", "1", "2", "3"])
    assert q3_parse(["done", "9"])["ids"] == [9]

    assert q3_parse(["rm"]) == {"command": "rm", "count": 1, "force": False}, \
        q3_parse(["rm"])
    assert q3_parse(["rm", "-n", "2", "--force"]) == {
        "command": "rm", "count": 2, "force": True,
    }, q3_parse(["rm", "-n", "2", "--force"])

    # 非法输入：argparse 自己打印用法并 SystemExit(2)。
    # 它会往 stderr 写一堆 usage，测试期间用 redirect_stderr 静音掉。
    def expect_system_exit(argv: list[str]) -> None:
        import contextlib

        with contextlib.redirect_stderr(io.StringIO()):
            try:
                q3_parse(argv)
            except SystemExit as exc:
                assert exc.code == 2, f"{argv} 的退出码应该是 2，实际 {exc.code}"
            else:
                raise AssertionError(f"{argv} 应该让 argparse 报错退出")

    expect_system_exit([])                                       # 缺子命令
    expect_system_exit(["add"])                                  # 缺 title
    expect_system_exit(["add", "t", "--priority", "urgent"])     # 不在 choices 里
    expect_system_exit(["list", "--limit", "abc"])               # type=int 失败
    expect_system_exit(["list", "--sort", "name"])               # 不在 choices 里
    expect_system_exit(["done"])                                 # nargs="+" 至少要一个
    expect_system_exit(["done", "x"])                            # type=int 失败
    expect_system_exit(["不存在子命令"])

    # -h 能打印出来（自动生成的帮助没被搞坏）
    parser = q3_build_parser()
    help_text = parser.format_help()
    for token in ("add", "list", "done", "rm"):
        assert token in help_text, f"-h 里应该有子命令 {token}"


def t_q4() -> None:
    text = (
        "2024-03-01 12:00:05 INFO  处理任务 42\n"
        "\n"
        "    \n"
        "2024-03-01 12:00:06 ERROR 任务 43 失败\n"
        "这行格式不对\n"
        "2024-03-01 12:00:07 WARNING 磁盘快满了\n"
        "2024-03-01 12:00:08 ERROR 任务 44 失败\n"
    )

    assert q4_parse_line(LOG_LINE) == {
        "date": "2024-03-01", "time": "12:00:05",
        "level": "INFO", "message": "处理任务 42",
    }, q4_parse_line(LOG_LINE)

    # 消息里有空格也要完整保留
    spaced = q4_parse_line("2024-03-01 12:00:09 INFO  任务 45 又 失败 了")
    assert spaced is not None and spaced["message"] == "任务 45 又 失败 了", spaced

    # 字段之间多个空格照样能解析
    assert q4_parse_line("2024-03-01   12:00:05   INFO       消息")["level"] == "INFO"

    # 解析不了的
    assert q4_parse_line("这行格式不对") is None
    assert q4_parse_line("") is None
    assert q4_parse_line("   ") is None
    assert q4_parse_line("2024-03-01 12:00:05 info 小写级别") is None
    assert q4_parse_line("12:00:05 INFO 没有日期") is None
    assert q4_parse_line(" 2024-03-01 12:00:05 INFO 行首有空格") is None, \
        "必须从行首开始匹配，不能用 search"

    parsed, invalid = q4_parse_lines(text)
    assert invalid == 1, f"坏行只有「这行格式不对」一条，空行要跳过，实际 {invalid}"
    assert len(parsed) == 4, [p["message"] for p in parsed]
    assert [p["level"] for p in parsed] == ["INFO", "ERROR", "WARNING", "ERROR"], parsed
    assert parsed[0]["message"] == "处理任务 42", parsed[0]
    assert parsed[-1]["message"] == "任务 44 失败", parsed[-1]

    assert q4_parse_lines("") == ([], 0)
    assert q4_parse_lines("\n\n  \n") == ([], 0)

    assert q4_filter_messages(text, "ERROR") == ["任务 43 失败", "任务 44 失败"], \
        q4_filter_messages(text, "ERROR")
    assert q4_filter_messages(text, "WARNING") == ["磁盘快满了"]
    assert q4_filter_messages(text, "DEBUG") == []
    assert q4_filter_messages(text, "error") == []

    assert q4_mask_secrets("user=alice password=hunter2 token=abc;ok") == \
        "user=alice password=*** token=***;ok"
    assert q4_mask_secrets("PASSWORD=xyz") == "PASSWORD=***", \
        "键名大小写不敏感，但替换后要保留原样大小写"
    assert q4_mask_secrets("secret = spaced") == "secret = spaced", \
        "键名和 = 之间有空格不算（这是刻意的简化规则）"
    assert q4_mask_secrets("password=") == "password=***", "空值也要处理"
    assert q4_mask_secrets("没有敏感字段") == "没有敏感字段"
    assert q4_mask_secrets("token=abc\ntoken=def") == "token=***\ntoken=***", \
        "换行也是值的终止符"
    assert q4_mask_secrets("password=a,b;c") == "password=***;c", \
        "只替换「键名=值」这一段，后面的 ;c 必须原样保留"
    assert q4_mask_secrets("token=abc token=def") == "token=*** token=***"


def t_q5() -> None:
    naive = datetime(2024, 3, 1, 12, 0)
    from_utc = datetime(2024, 3, 1, 12, 0, tzinfo=UTC)

    converted = q5_to_cst(naive)
    assert converted == datetime(2024, 3, 1, 20, 0, tzinfo=CST), converted
    assert converted.utcoffset() == timedelta(hours=8), converted.utcoffset()
    assert q5_to_cst(from_utc) == converted, q5_to_cst(from_utc)

    # 已经是 CST 的，换算后不变
    already = datetime(2024, 3, 1, 20, 0, tzinfo=CST)
    assert q5_to_cst(already) == already

    # naive 输入被当成 UTC：本地时区不同也不影响结果
    assert q5_to_cst(datetime(2024, 1, 1, 0, 0)).hour == 8

    # ---- 解析 ----
    parsed = q5_parse("2024-03-01T20:00:00+08:00")
    assert parsed == datetime(2024, 3, 1, 20, 0, tzinfo=CST), parsed
    assert parsed.tzinfo is not None
    assert q5_parse("2024-03-01T12:00:00+00:00") == from_utc
    assert q5_parse("2024-03-01T12:00:00Z") == from_utc, \
        "Z 后缀是合法的 ISO 8601（fromisoformat 能认）"
    # 微秒不能丢
    assert q5_parse("2024-03-01T12:00:00.123456+00:00").microsecond == 123456

    # 缺时区的、根本不是时间的，一律 ValueError
    for bad in ("2024-03-01 12:00:00", "2024-03-01T12:00:00", "这不是时间", ""):
        try:
            q5_parse(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"q5_parse({bad!r}) 应该抛 ValueError")
    # 缺时区的那两条，消息里要说明是「时区」的问题
    for missing_tz in ("2024-03-01 12:00:00", "2024-03-01T12:00:00"):
        try:
            q5_parse(missing_tz)
        except ValueError as exc:
            assert "时区" in str(exc), f"{missing_tz!r} 的报错里应该有「时区」: {exc}"

    # ---- 序列化 ----
    assert q5_to_iso(converted) == "2024-03-01T20:00:00+08:00", q5_to_iso(converted)
    assert q5_to_iso(from_utc) == "2024-03-01T12:00:00+00:00", q5_to_iso(from_utc)
    assert q5_parse(q5_to_iso(converted)) == converted
    try:
        q5_to_iso(naive)
    except ValueError as exc:
        assert "时区" in str(exc), exc
    else:
        raise AssertionError("naive 时间序列化成 ISO 应该抛 ValueError")

    # ---- 天数差 ----
    assert q5_days_between(date(2024, 3, 1), date(2024, 3, 10)) == 9
    assert q5_days_between(date(2024, 3, 10), date(2024, 3, 1)) == 9
    assert q5_days_between(date(2024, 3, 1), date(2024, 3, 1)) == 0
    assert q5_days_between(date(2023, 12, 31), date(2024, 1, 1)) == 1

    # ---- 人话时间差 ----
    cases = [
        (timedelta(days=2, hours=3, minutes=5), "2 天 3 小时 5 分"),
        (timedelta(hours=1), "1 小时"),
        (timedelta(minutes=90), "1 小时 30 分"),
        (timedelta(days=1, minutes=1), "1 天 1 分"),
        (timedelta(seconds=30), "0 分"),
        (timedelta(0), "0 分"),
        (timedelta(days=1, hours=1, minutes=1, seconds=59), "1 天 1 小时 1 分"),
        (-timedelta(days=1, minutes=1), "-1 天 1 分"),
        (-timedelta(hours=2), "-2 小时"),
        (timedelta(weeks=1), "7 天"),
    ]
    for td, expected in cases:
        got = q5_humanize_delta(td)
        assert got == expected, f"q5_humanize_delta({td!r}) -> {got!r}，期望 {expected!r}"

    # ---- now ----
    now = q5_now_utc()
    assert now.tzinfo is not None, "必须是 aware"
    assert now.utcoffset() == timedelta(0), now.utcoffset()


def t_q6() -> None:
    buf = io.StringIO()
    log = q6_make_logger("course.m07.q6", buf)

    assert log.name == "course.m07.q6"
    assert log.level == logging.DEBUG
    assert log.propagate is False, "propagate 必须是 False，别往根 logger 冒泡"
    assert len(log.handlers) == 1, [type(h).__name__ for h in log.handlers]

    log.debug("d %s", 1)
    log.info("i %s", 2)
    log.warning("w")
    assert buf.getvalue() == (
        "DEBUG|course.m07.q6|d 1\n"
        "INFO|course.m07.q6|i 2\n"
        "WARNING|course.m07.q6|w\n"
    ), repr(buf.getvalue())

    # 同一个名字再配置一次，不能变成两个 handler（输出会翻倍）
    buf2 = io.StringIO()
    log2 = q6_make_logger("course.m07.q6", buf2)
    assert log2 is log, "getLogger 对同一个名字返回的是同一个对象"
    assert len(log.handlers) == 1, [type(h).__name__ for h in log.handlers]
    log.warning("once")
    assert buf2.getvalue() == "WARNING|course.m07.q6|once\n", repr(buf2.getvalue())

    # handler 级别的两级过滤
    buf3 = io.StringIO()
    strict = q6_make_logger("course.m07.q6.strict", buf3, level=logging.DEBUG,
                           handler_level=logging.WARNING)
    strict.debug("看不见")
    strict.info("也看不见")
    strict.warning("看得见")
    assert buf3.getvalue() == "WARNING|course.m07.q6.strict|看得见\n", \
        repr(buf3.getvalue())

    # 更高的 logger 级别也一样拦得住
    buf4 = io.StringIO()
    quiet = q6_make_logger("course.m07.q6.quiet", buf4, level=logging.ERROR)
    quiet.warning("被 logger 拦住")
    quiet.error("能过")
    assert buf4.getvalue() == "ERROR|course.m07.q6.quiet|能过\n", repr(buf4.getvalue())

    # ---- 带 traceback 的日志 ----
    buf5 = io.StringIO()
    err_log = q6_make_logger("course.m07.q6.divide", buf5)

    assert q6_safe_divide(err_log, 10, 4) == 2.5
    assert "DEBUG|course.m07.q6.divide|" in buf5.getvalue(), repr(buf5.getvalue())

    before = len(buf5.getvalue().splitlines())
    assert q6_safe_divide(err_log, 1, 0) == 0.0
    tail = buf5.getvalue().splitlines()[before:]
    assert tail[0].startswith("ERROR|course.m07.q6.divide|"), tail[0]
    assert "1" in tail[0] and "0" in tail[0], f"消息里要有 a 和 b 的值: {tail[0]}"
    joined = "\n".join(tail)
    assert "Traceback (most recent call last)" in joined, \
        f"logger.exception 必须把调用栈也打进去:\n{joined}"
    assert "ZeroDivisionError" in joined, joined
    assert "division by zero" in joined, joined

    # 非零错误不能把别的异常也吞掉
    try:
        q6_safe_divide(err_log, 1, "x")   # type: ignore[arg-type]
    except TypeError:
        pass
    else:
        raise AssertionError("除 0 以外的异常应该原样传播出去")


def t_q7() -> None:
    apple = LineItem("苹果", 3.5, 2)
    assert apple.total == 7.0, apple.total
    assert LineItem("苹果", 3.5).total == 3.5, "qty 默认 1"
    assert LineItem(" 苹果 ", 2.0).name == "苹果", "name 要去空白"
    assert LineItem("苹果", 2.0, 0).total == 0.0, "qty 可以是 0"

    # total 是 init=False：不能从构造函数传
    try:
        LineItem("苹果", 3.5, 2, 99.0)
    except TypeError:
        pass
    else:
        raise AssertionError("total 是 field(init=False)，不该能通过构造函数传入")

    # 逐条校验
    for kwargs, needle in (
        ({"name": "", "price": 1.0}, "name"),
        ({"name": "   ", "price": 1.0}, "name"),
        ({"name": "x", "price": 0}, "price"),
        ({"name": "x", "price": -1.0}, "price"),
        ({"name": "x", "price": 1.0, "qty": -1}, "qty"),
    ):
        try:
            LineItem(**kwargs)
        except ValueError as exc:
            assert needle in str(exc), f"{kwargs} 的报错里要有 {needle!r}: {exc}"
        else:
            raise AssertionError(f"LineItem({kwargs}) 应该抛 ValueError")

    # ---- Order ----
    order = Order("A-001", [apple, LineItem("香蕉", 2.0, 3)], note="周末送货")
    assert order.item_count == 2, order.item_count
    assert q7_order_total(order) == 7.0 + 6.0, q7_order_total(order)
    assert q7_order_total(Order("A-002")) == 0.0
    assert "周末送货" not in repr(order), f"note 是 repr=False:\n{order!r}"
    assert "item_count=2" in repr(order), repr(order)
    try:
        Order("A-003", [], note="x", item_count=9)
    except TypeError:
        pass
    else:
        raise AssertionError("item_count 是 field(init=False)，不该能传")

    try:
        Order("   ")
    except ValueError as exc:
        assert "order_id" in str(exc), exc
    else:
        raise AssertionError("空 order_id 应该抛 ValueError")

    # 两张订单不能共用同一个 items 列表
    o1, o2 = Order("A-004"), Order("A-005")
    o1.items.append(LineItem("橘子", 1.0))
    assert o2.items == [], f"items 必须是独立列表（field(default_factory=list)）: {o2.items}"
    # item_count 是在 __post_init__ 里算好的**快照**：
    # 之后再手动改 items，它不会自动跟着变。
    # 这正是「派生字段」的边界 —— 想让它准，就别绕过构造函数去改 items。
    assert o1.item_count == 0, "item_count 是构造时算的快照，事后改 items 不会更新"

    # ---- JSON 往返 ----
    text = q7_order_to_json(order)
    assert "苹果" in text and "香蕉" in text, f"中文必须原样出现:\n{text}"
    assert "\\u" not in text, f"用了 ensure_ascii=True？\n{text}"
    assert "\n" in text, "indent=2 应该产生多行输出"

    payload = json.loads(text)
    assert set(payload) == {"order_id", "items", "note", "item_count"}, payload
    assert payload["order_id"] == "A-001"
    assert len(payload["items"]) == 2
    assert payload["items"][0]["total"] == 7.0, payload["items"][0]

    back = q7_order_from_json(text)
    assert isinstance(back, Order), type(back)
    assert back.order_id == "A-001"
    assert back.note == "周末送货"
    assert asdict(back) == asdict(order), f"\n{asdict(back)}\n{asdict(order)}"
    assert q7_order_total(back) == q7_order_total(order)
    assert all(isinstance(item, LineItem) for item in back.items)
    assert back.item_count == 2

    # 空订单往返
    empty = Order("A-006")
    assert asdict(q7_order_from_json(q7_order_to_json(empty))) == asdict(empty)

    # asdict 是深拷贝
    d = asdict(order)
    d["items"][0]["name"] = "改过了"
    assert order.items[0].name == "苹果", "asdict 应该是深拷贝"


def t_q8() -> None:
    import typing

    # 泛型参数在运行时只是标记：Stack[int] 和 Stack[str] 造出来的实例
    # 是**同一个类**，类型参数根本不参与运行。
    assert typing.get_origin(Stack[int]) is Stack, typing.get_origin(Stack[int])
    assert typing.get_args(Stack[int]) == (int,), typing.get_args(Stack[int])
    assert type(Stack[int]()) is type(Stack[str]()), "泛型参数不影响实际的类"

    s = Stack[int]()
    assert len(s) == 0 and not s
    s.push(1)
    s.push(2)
    s.push(3)
    assert len(s) == 3 and s
    assert s.peek() == 3, s.peek()
    assert len(s) == 3, "peek 不能弹元素"
    assert s.to_list() == [3, 2, 1], s.to_list()
    assert list(s) == [3, 2, 1], list(s)
    assert s.pop() == 3
    assert s.pop() == 2
    assert s.to_list() == [1], s.to_list()
    assert s.pop() == 1
    assert not s

    for method in ("pop", "peek"):
        try:
            getattr(s, method)()
        except IndexError as exc:
            assert "空栈" in str(exc), f"{method}(): {exc}"
        else:
            raise AssertionError(f"空栈调用 {method}() 应该抛 IndexError")

    # 换个类型照样能用（运行时不检查，但写法上说明意图）
    words = Stack[str]()
    words.push("a")
    words.push("b")
    assert words.to_list() == ["b", "a"]
    assert isinstance(words, Stack)

    # ---- chunked ----
    assert q8_chunked([1, 2, 3, 4, 5], 2) == [[1, 2], [3, 4], [5]]
    assert q8_chunked([1, 2, 3, 4], 2) == [[1, 2], [3, 4]]
    assert q8_chunked([1], 3) == [[1]]
    assert q8_chunked([], 3) == []
    assert q8_chunked("abcdef", 4) == [["a", "b", "c", "d"], ["e", "f"]], \
        "Sequence 就行，不必是 list"
    assert q8_chunked(range(5), 5) == [[0, 1, 2, 3, 4]]
    for bad in (0, -1):
        try:
            q8_chunked([1, 2], bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"size={bad} 应该抛 ValueError")

    # ---- unique ----
    assert q8_unique([3, 1, 3, 2, 1]) == [3, 1, 2]
    assert q8_unique([]) == []
    assert q8_unique("abracadabra") == ["a", "b", "r", "c", "d"]
    assert q8_unique([(1, 2), (1, 2), (3,)]) == [(1, 2), (3,)]
    assert q8_unique(iter([1, 1, 2])) == [1, 2], "Iterable 就够，不用 Sequence"

    # ---- group_by ----
    got = q8_group_by(["apple", "avocado", "banana"], lambda w: w[0])
    assert got == {"a": ["apple", "avocado"], "b": ["banana"]}, got
    assert type(got) is dict, f"必须是普通 dict，实际 {type(got).__name__}"
    # 访问不存在的键不能插进去
    try:
        got["z"]
    except KeyError:
        pass
    else:
        raise AssertionError("普通 dict 访问不存在的键应该 KeyError")
    assert "z" not in got

    assert q8_group_by([], lambda x: x) == {}
    assert q8_group_by([1, 2, 3, 4, 5, 6], lambda n: n % 3) == {
        1: [1, 4], 2: [2, 5], 0: [3, 6],
    }, q8_group_by([1, 2, 3, 4, 5, 6], lambda n: n % 3)


def t_q9() -> None:
    counts = q9_word_count("Hello, hello! World")
    assert counts == Counter({"hello": 2, "world": 1}), counts
    assert isinstance(counts, Counter), type(counts)

    # 汉字和标点都是分隔符；数字算词
    mixed = q9_word_count("你好 python 3.14 真好玩，python3 python3")
    assert mixed == Counter({"python": 1, "3": 1, "14": 1, "python3": 2}), mixed
    assert q9_word_count("") == Counter()
    assert q9_word_count("!!! ???") == Counter()

    # ---- top_n ----
    c = Counter({"a": 2, "b": 2, "c": 1})
    assert q9_top_n(c, 2) == [("a", 2), ("b", 2)], q9_top_n(c, 2)
    assert q9_top_n(c, 10) == [("a", 2), ("b", 2), ("c", 1)], q9_top_n(c, 10)
    for bad in (0, -1):
        try:
            q9_top_n(c, bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"n={bad} 应该抛 ValueError")
    assert q9_top_n(Counter(), 3) == []

    # 并列时按字典序（Counter.most_common 在并列时用的是插入顺序，不能用）
    tied = Counter()
    for word in ("zebra", "apple", "mango", "apple", "zebra", "mango"):
        tied[word] += 1
    assert q9_top_n(tied, 3) == [("apple", 2), ("mango", 2), ("zebra", 2)], \
        q9_top_n(tied, 3)
    assert q9_top_n(q9_word_count("a b c a b a"), 2) == [("a", 3), ("b", 2)]

    # ---- group_records ----
    grouped = q9_group_records([("研发", "张三"), ("市场", "李四"), ("研发", "王五")])
    assert grouped == {"研发": ["张三", "王五"], "市场": ["李四"]}, grouped
    assert type(grouped) is dict, f"必须是普通 dict，实际 {type(grouped).__name__}"
    try:
        grouped["行政"]
    except KeyError:
        pass
    else:
        raise AssertionError("普通 dict 访问不存在的键应该 KeyError")
    assert "行政" not in grouped, "访问不存在的键不能把键插进去"
    assert q9_group_records([]) == {}

    # 组内顺序 = 输入顺序
    ordered = q9_group_records([("a", "3"), ("a", "1"), ("a", "2")])
    assert ordered == {"a": ["3", "1", "2"]}, ordered

    # ---- recent ----
    assert q9_recent([1, 2, 3, 4, 5], 2) == [4, 5]
    assert q9_recent([1, 2], 5) == [1, 2]
    assert q9_recent([], 3) == []
    assert q9_recent(range(10), 3) == [7, 8, 9]
    assert q9_recent("abcdef", 2) == ["e", "f"]
    assert q9_recent(iter([1, 2, 3]), 2) == [2, 3], "Iterable 就够，不用 Sequence"
    for bad in (0, -1):
        try:
            q9_recent([1, 2], bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"n={bad} 应该抛 ValueError")


def main() -> None:
    c = Checker("模块 07 · 标准库与类型注解 练习")
    c.add("q1  TypedDict + 校验函数", t_q1)
    c.add("q2  Protocol 结构化子类型", t_q2)
    c.add("q3  argparse 子命令解析", t_q3)
    c.add("q4  re 解析日志与脱敏", t_q4)
    c.add("q5  datetime 时区与格式化", t_q5)
    c.add("q6  logging 配置与输出验证", t_q6)
    c.add("q7  dataclasses 进阶与 JSON 往返", t_q7)
    c.add("q8  TypeVar / Generic 泛型工具", t_q8)
    c.add("q9  collections 实战", t_q9)
    c.run()


if __name__ == "__main__":
    main()
