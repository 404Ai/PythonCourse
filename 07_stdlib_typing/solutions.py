"""
模块 07 · 标准库与类型注解 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每道题下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。

本模块全部是内存操作，不碰磁盘，跑完不会有任何残留文件。
"""

from __future__ import annotations

import argparse
import io
import json
import logging
import math
import re
import sys
from collections import Counter, defaultdict, deque
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Generic, Literal, Protocol, TypedDict, TypeVar, runtime_checkable

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
    """必填字段的基线类。

    单独抽一层出来，是为了让下面 `Task` 里的 `total=False` 只作用于
    **Task 自己新声明的**键，而不影响继承来的 id / title。
    """

    id: int
    title: str


class Task(_TaskRequired, total=False):
    """一条任务记录（运行时就是普通 dict）。

    为什么不用 `NotRequired[str]`？
        本文件有 `from __future__ import annotations`，所有注解在运行时
        都是**字符串**，`NotRequired[...]` 这层包装根本没被解析，
        结果 `__required_keys__` 会把 rating 之类的可选字段也算成必填。
        这是 3.14.7 上实测到的行为，不是我的猜测。
        想用 NotRequired 就得去掉 future import；两者不能共存。
    """

    priority: str
    tags: list[str]
    done: bool


def q1_validate_task(raw: dict) -> Task:
    """逐项校验，第一个不满足的就抛异常。

    为什么用「抛异常」而不是「返回 (ok, msg)」：
        返回码可以被调用方**忘记检查**，异常不会。
        校验逻辑一多，返回码就要一层层手动往上传，异常是自动传播的。
    """

    # 先挡住「根本不是 dict」的情况。这是编程错误（调用方用错了 API），
    # 不是用户输入错误，所以用 TypeError 而不是 ValueError。
    if not isinstance(raw, dict):
        raise TypeError(f"需要一个 dict，收到 {type(raw).__name__}")

    # ---- id ----
    if "id" not in raw:
        raise ValueError("缺少必填字段: id")
    task_id = raw["id"]
    # bool 必须单独拦：`isinstance(True, int)` 是 True。
    # 不先判 bool，{"id": True} 就会变成编号为 1 的任务。
    if isinstance(task_id, bool) or not isinstance(task_id, int):
        raise ValueError(f"id 必须是 int，收到 {type(task_id).__name__}")
    if task_id <= 0:
        raise ValueError(f"id 必须是正整数，收到 {task_id}")

    # ---- title ----
    if "title" not in raw:
        raise ValueError("缺少必填字段: title")
    title = raw["title"]
    if not isinstance(title, str):
        raise ValueError(f"title 必须是 str，收到 {type(title).__name__}")
    title = title.strip()
    if not title:
        raise ValueError("title 不能为空")

    # ---- priority（可选）----
    # 用 .get(key, default) 而不是 `if key in raw`：
    # 少一层缩进，而且「默认值」和「校验」写在一行里，读起来是一件事。
    priority = raw.get("priority", "medium")
    if priority not in ("low", "medium", "high"):
        raise ValueError(f"priority 必须是 low/medium/high，收到 {priority!r}")

    # ---- tags（可选）----
    tags = raw.get("tags", [])
    if not isinstance(tags, list):
        raise ValueError(f"tags 必须是 list，收到 {type(tags).__name__}")
    for index, tag in enumerate(tags):
        if not isinstance(tag, str):
            raise ValueError(
                f"tags[{index}] 必须是 str，收到 {type(tag).__name__}"
            )

    # ---- done（可选）----
    done = raw.get("done", False)
    if not isinstance(done, bool):
        raise ValueError(f"done 必须是 bool，收到 {type(done).__name__}")

    # 返回**新建**的 dict：
    #   - list(tags) 复制一份，否则调用方之后改自己那个 list，
    #     会「隔空」改掉我们返回值的内容 —— 这类 bug 极难排查。
    #   - 不给调用方留下原始 dict 的引用，返回值就是一份干净的快照。
    return {
        "id": task_id,
        "title": title,
        "priority": priority,
        "tags": list(tags),
        "done": done,
    }


# 常见错误写法：
#
#   1) 用 assert 做输入校验
#         assert isinstance(task_id, int), "id 必须是 int"
#      `python -O` 会把所有 assert 整个删掉，校验直接消失。
#      assert 只用来表达「这里不可能发生」的内部不变量；
#      凡是外部输入（用户、文件、网络）一律显式 raise。
#
#   2) 用 `isinstance(task_id, int)` 判 int 却不判 bool
#      True 会被当成合法的 1，测试里 {"id": True} 那一行马上就挂。
#      规则很简单：**只要校验 int，就先写 `isinstance(x, bool)` 把 bool 挡掉**。
#
#   3) 所有错误都抛同一个异常、消息里不带字段名
#         raise ValueError("校验失败")
#     前端拿到这五个字，不知道该把红框画在哪个输入框上。
#       mypy/pydantic 这类工具的价值，一半就在「错误定位到字段」。
#
#   4) 校验通过后直接返回 raw（或 raw 的一部分）
#         return {"id": raw["id"], "tags": raw["tags"], ...}
#     调用方改一下自己传进来的 list，你返回值里的 tags 也跟着变。
#     返回值必须和输入**没有共享的可变对象**（本模块的测试专门查这个）。
#
#   5) 顺序写反：先做格式检查再判「键存不存在」
#         if not isinstance(raw["title"], str):   # KeyError!
#     缺键时抛的是 KeyError 而不是「缺少必填字段: title」，
#       API 调用方拿到的错误信息毫无指导意义。
#
#   6) 用 NotRequired 声明可选字段
#      `from __future__ import annotations` 在场时它就是不好使，
#      __required_keys__ 会算错。要么用 total=False 继承，
#      要么去掉 future import —— 二选一。


# ======================================================================
# q2 —— Protocol：结构化子类型
# ======================================================================
@runtime_checkable
class Shape(Protocol):
    """任何「有 name() 和 area()」的东西都算 Shape —— 不需要继承。

    和 abc.ABC 的区别：
        ABC 是**名义**子类型 —— 必须显式 `class Circle(Shape)`。
        Protocol 是**结构**子类型 —— 有你要求的方法就算数。

    为什么 Protocol 更适合这种场景：
        Circle / Square 可能来自第三方库，你改不了它们的基类；
        也可能它们已经继承了别的东西，Python 没有多继承的语法负担但
        加一层纯为了类型检查的基类仍然很别扭。Protocol 把这些都省了。

    @runtime_checkable 的代价（务必记住）：
        运行时只能检查**属性名是否存在**，检查不了签名。
        `def run(self, totally, wrong, signature)` 也会被判定为满足
        `def run(self, x: int) -> int`。所以别拿 isinstance 当参数校验，
        真正的检查交给 mypy。
    """

    def name(self) -> str:
        """形状的名字。"""
        ...

    def area(self) -> float:
        """面积。"""
        ...


class Circle:
    """圆形。

    注意类体里**一个字都没提 Shape** —— 这是重点。
    """

    def __init__(self, radius: float) -> None:
        if radius <= 0:
            raise ValueError("半径必须为正")
        self.radius = radius

    def name(self) -> str:
        return "circle"

    def area(self) -> float:
        return math.pi * self.radius ** 2


class Square:
    """正方形。同样不提 Shape。"""

    def __init__(self, side: float) -> None:
        if side <= 0:
            raise ValueError("边长必须为正")
        self.side = side

    def name(self) -> str:
        return "square"

    def area(self) -> float:
        return self.side ** 2


def q2_total_area(shapes: Sequence[Shape]) -> float:
    """参数写 Sequence[Shape]，但传 Circle / Square 都行。"""
    return sum(shape.area() for shape in shapes)


def q2_describe_all(shapes: Sequence[Shape]) -> list[str]:
    """面积降序；面积相同按名字升序。

    为什么排序键写成元组 `(-area, name)`：
        负号用来「反转」数值方向的排序，这是 sorted 的常用技巧。
        写成 `key=lambda s: s.area(), reverse=True` 的话，
        并列时名字也会跟着被反转成降序 —— 通常不是你要的。
    """
    ordered = sorted(shapes, key=lambda shape: (-shape.area(), shape.name()))
    return [f"{shape.name()}={shape.area():.4f}" for shape in ordered]


def q2_is_shape(obj: object) -> bool:
    """运行时判断。依赖 @runtime_checkable，且只看方法名不看签名。"""
    return isinstance(obj, Shape)


# 常见错误写法：
#
#   1) 让 Circle / Square 继承 Shape
#         class Circle(Shape):
#     能跑，但这就退化成名义子类型了 —— Protocol 的好处全没了。
#       Protocol 只用来**声明契约**，不要拿它当基类（除非你确实需要一个默认实现）。
#
#   2) 忘了 @runtime_checkable 就用 isinstance
#         isinstance(obj, Shape)
#     不加装饰器会直接 TypeError: Instance and class checks can only be
#      used with @runtime_checkable protocols。报错信息很直白，但第一次遇到
#       容易懵。记住：**要 isinstance 就必须加装饰器**。
#
#   3) 以为 runtime_checkable 会检查签名
#        (见上面 Shape 的 docstring) 它只看名字。
#       所以 `isinstance(x, Shape)` 为 True 之后，代码里千万别假设
#         `x.area()` 的参数一定是对的 —— 静态检查器才是那道防线。
#
#   4) 用 abc.ABC 硬套
#         class Shape(ABC): @abstractmethod def area(self): ...
#      在「我要给第三方类写类型」这个场景下 ABC 是做不到的：
#      你没法让别人的类去继承你的 ABC。Protocol 才行。
#
#   5) 参数类型写成 `list[Shape]` 而不是 `Sequence[Shape]`
#      调用方手里是 tuple 或其它序列时会被静态检查器挡住，
#      逼着他做一次无意义的 list() 转换。
#      **参数类型尽量宽（Iterable/Sequence），返回类型尽量具体（list）。**
#
#   6) 排序键写成 `key=lambda s: s.area(), reverse=True`
#      并列时的名字顺序会被一起反转，和「名字升序」的要求正好相反。


# ======================================================================
# q3 —— argparse：把参数解析拆成可测试的两半
# ======================================================================
def q3_build_parser() -> argparse.ArgumentParser:
    """只负责「构造 parser」，不负责解析 —— 这是能被测试的关键。

    为什么要把构造和 parse_args 分开：
        如果函数内部直接 `parser.parse_args()`，测试就只能去改
        sys.argv（污染整个进程，测试之间互相干扰）。
        拆开之后，测试直接 `q3_parse(["add", "x"])` 就行。
        真实项目里 CLI 的 90% 都能这么测。
    """
    parser = argparse.ArgumentParser(
        prog="todo",
        description="一个任务管理小工具。",
        epilog="示例: todo add 写作业 --priority high",
    )

    # dest="command" 让结果里有一个 "command" 键；
    # required=True 让「一个子命令都不给」变成错误 —— 否则会返回一个
    # 空 Namespace，调用方拿到手才发现什么都没有，报错点离真正的错误很远。
    sub = parser.add_subparsers(dest="command", required=True)

    p_add = sub.add_parser("add", help="添加任务")
    p_add.add_argument("title", help="任务标题")
    # choices= 让 argparse 帮你做白名单校验，并且自动写进 -h 的用法行里。
    p_add.add_argument(
        "--priority",
        choices=("low", "medium", "high"),
        default="medium",
        help="优先级（默认 medium）",
    )
    # action="append" 让同一个选项可以出现多次，攒成一个列表。
    # argparse 内部会对 default 做一次拷贝，所以这里的 [] 不会在多次
    # parse_args 之间被污染（但自己写代码时不要在函数默认参数里放 []）。
    p_add.add_argument("--tag", action="append", default=[],
                       help="标签，可以重复出现")
    # store_true：出现就是 True，不出现就是 False，不需要跟值。
    p_add.add_argument("-v", "--verbose", action="store_true",
                       help="输出详细信息")

    p_list = sub.add_parser("list", help="列出任务")
    # type= 传的是**函数**，不只是类型名。它会拿原始字符串去调用，
    # 抛 ValueError/TypeError 时 argparse 会转成友好的报错退出。
    p_list.add_argument("--limit", type=int, default=10, help="最多显示几条")
    p_list.add_argument("--all", action="store_true", help="显示全部")
    p_list.add_argument("--sort", choices=("id", "priority"), default="id",
                        help="排序字段")

    p_done = sub.add_parser("done", help="标记任务完成")
    # nargs="+" 表示「一个或多个」，结果一定是 list；不加的话只有一个值时
    # 会得到裸值而不是 list，调用方就得写 `if isinstance(ids, int)` —— 很脏。
    p_done.add_argument("ids", type=int, nargs="+", help="任务编号，至少一个")

    p_rm = sub.add_parser("rm", help="删除任务")
    p_rm.add_argument("-n", "--count", type=int, default=1, help="删除几条")
    p_rm.add_argument("--force", action="store_true", help="不确认直接删")

    return parser


def q3_parse(argv: list[str]) -> dict:
    """解析 argv 列表。

    vars(namespace) 把 Namespace 变成普通 dict，
    这样测试里可以直接写 `== {"command": "add", ...}`，比
    `ns.command == "add" and ns.title == ...` 干净得多。
    """
    return vars(q3_build_parser().parse_args(argv))


# 常见错误写法：
#
#   1) 在函数里直接 `parser.parse_args()`（读 sys.argv）
#      这样就没法测了 —— 要么改 sys.argv（污染全局），要么开子进程。
#      传 argv 参数、默认 None、`parse_args(argv)`（None 时 argparse 自己
#      会去读 sys.argv），是既好测又好用的写法。
#
#   2) 不用 subparsers，用一堆互斥的 flag 自己分派
#         parser.add_argument("--add"); parser.add_argument("--list")
#     结果是 `--add x --list` 这种组合能同时成立，状态空间爆炸。
#       add_subparsers 天然互斥，-h 也会分节显示，可读性高一个数量级。
#
#   3) 子命令不加 required=True
#      `todo` 不带任何参数时返回空 Namespace，程序安静地什么都不做。
#      用户会以为命令成功了。宁可报错。
#
#   4) 用 `type=str` 然后自己 int() 转换
#         args = parser.parse_args(); count = int(args.count)   # 可能 ValueError
#     这个 ValueError 会带着一坨 traceback 甩给用户。
#      `type=int` 让 argparse 直接给出 "invalid int value: 'abc'"，
#      还会以退出码 2 结束 —— 这就是命令行工具该有的样子。
#
#   5) 把默认值写进 help 文本却忘了 default=
#         help="最多显示几条（默认 10）"   # 但没写 default=10
#     帮助说 10，实际是 None，之后 `if args.limit > 0` 直接 TypeError。
#       argparse 的 formatter 其实可以自动带默认值
#       （ArgumentDefaultsHelpFormatter），但最简单的是别撒谎。
#
#   6) 在函数默认参数里放可变对象
#         def f(tags=[]): ...
#     这是 Python 的经典坑（本模块 demo 演示过）。
#     本模块用 argparse 的 action="append" 绕开了这个问题，
#      因为 argparse 自己对 default 做了拷贝 —— 但别指望别处也这样。
#
#   7) 用 `-h` 之外还自己加 `--help`
#      argparse 已经自动加了 -h/--help，重复添加会
#      "conflicting option string" 报错。想要中文帮助就改
#      description/help= 的文案，不要自己造 help 选项。


# ======================================================================
# q4 —— re：解析日志行
# ======================================================================
# 命名分组 (?P<name>...) 是这一节的核心：
#   用 group(1)/group(2) 的时候，任何人往正则里插一个新分组，
#   所有下标全部错位 —— 而且不会报错，只会静默取到错的值。
#   命名分组不可能错位。
#
# 开头的 ^ 和 re.match 是双重保险：match 本身就从行首开始，
# 写个 ^ 是给读代码的人看的。
LOG_LINE = "2024-03-01 12:00:05 INFO  处理任务 42"

LOG_RE = re.compile(
    r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
    r"(?P<level>[A-Z]+)\s+"
    r"(?P<message>.*)$"
)

#: 键名大小写不敏感：(?i) 写在**模式最前面**才有效。
#: 值用 [^\s;]* —— 匹配到空白或分号为止，空值也允许。
SECRET_RE = re.compile(r"(?i)(?P<key>password|token|secret)=[^\s;]*")


def q4_parse_line(line: str) -> dict[str, str] | None:
    """解析一行，失败返回 None。

    为什么失败返回 None 而不是抛异常：
        「这一行不合格式」在日志解析里是**预期内**的情况
        （日志里混着堆栈、分隔线、别的程序输出），
        每遇到一行就抛一次异常，异常的开销和调用方的处理代码都会失控。
        真正意外的情况（文件打不开）才交给异常。
    """
    match = LOG_RE.match(line)
    if match is None:
        return None
    # groupdict() 直接给出 {名字: 值}，不用手写 4 次 group()
    return match.groupdict()


def q4_parse_lines(text: str) -> tuple[list[dict[str, str]], int]:
    """整段解析。空行跳过，其余解析不了的行计数。"""
    parsed: list[dict[str, str]] = []
    invalid = 0

    # splitlines() 会把 "\r\n" / "\n" / "\r" 都处理掉，
    # 不用自己 rstrip("\n")（那样在 Windows 上会留下 \r）。
    for line in text.splitlines():
        if not line.strip():
            continue                    # 空行不是错误，直接跳过
        record = q4_parse_line(line)
        if record is None:
            invalid += 1
        else:
            parsed.append(record)

    return parsed, invalid


def q4_filter_messages(text: str, level: str) -> list[str]:
    """挑出指定级别的消息。级别比较是**大小写敏感**的 —— 和解析规则一致。"""
    records, _ = q4_parse_lines(text)
    return [record["message"] for record in records if record["level"] == level]


def q4_mask_secrets(text: str) -> str:
    """把 password= / token= / secret= 的值换成 ***。

    re.sub 的替换串里 `\\g<key>` 是「命名分组的反向引用」：
    把匹配到的键名原样放回去，所以 PASSWORD 不会被改成小写。
    用 `\\1` 也行，但只要正则里一加分组的顺序就会错位 —— 命名更稳。
    """
    return SECRET_RE.sub(r"\g<key>=***", text)


# 常见错误写法：
#
#   1) 用 group(1)/group(2) 按下标取字段
#      往正则里加一个新分组就全错位，而且**不报错**，只是静默取错值。
#      命名分组是这一节最该带走的东西。
#
#   2) 用 re.search 而不是 re.match
#         re.search(r"\d{4}-\d{2}-\d{2}", line)
#     行中间出现的日期也会被当成本行的时间戳。
#     测试里「行首有空格」那一条就是这个问题的照妖镜。
#
#   3) 级别写成 `[A-Za-z]+` 或 `\w+`
#      大小写混着的 "info" 也会通过，后面按级别统计时多出一堆
#      看着像又看着不像的键。**用字符类把格式钉死**，别用 \w 图省事。
#
#   4) 正则里忘了写 r 前缀
#         re.compile("\\d{4}-\\d{2}-\\d{2}")     # 这个还行
#         re.compile("\b2024")                   # \b 变成了退格符！
#      含 \d \s \w \b 的模式一律用 r"..."，能省掉一整类神秘 bug。
#
#   5) 每解析一行就 re.compile 一次
#         def parse(line):
#             return re.match(r"...", line)      # 每次都重新查缓存
#     循环里应该把模式提到模块级 `LOG_RE = re.compile(...)`。
#     比性能更重要的一点是：**给正则起个名字**，
#     调用处 `LOG_RE.match(line)` 一眼就知道在干什么。
#
#   6) `.*` 在 message 里吃掉不该吃的东西
#      `.` 不匹配换行，所以单行没问题；但如果模式里没写 $ 也没写 \Z，
#      行尾多余的内容会被静默忽略。要求「整行匹配到底」就把 $ 写上。
#
#   7) `[^\s;]+` 写成 `.+`
#         r"password=.+"
#     贪婪的 `.+` 会一路吃到行尾，同一行的 token=xxx 就被吞掉了。
#       **写脱敏正则时，「值的边界」是最需要想清楚的一件事。**
#
#   8) 替换串里忘了用 raw string
#         SECRET_RE.sub("\g<key>=***", text)     # \g 被当成转义序列
#      会报 "bad escape \g" 或者行为诡异。替换串里有反斜杠就用 r""。


# ======================================================================
# q5 —— datetime：时区、格式化、时间差
# ======================================================================
UTC = timezone.utc
#: 东八区。注意这是**固定偏移**，不处理历史上的夏令时
#: （中国 1986-1991 年实行过夏令时）。要处理真实时区规则得用
#: zoneinfo.ZoneInfo("Asia/Shanghai")，那属于标准库的另一个模块。
CST = timezone(timedelta(hours=8))


def q5_to_cst(dt: datetime) -> datetime:
    """naive 当 UTC 处理，aware 按绝对时刻转换。

    为什么 naive 要显式 `.replace(tzinfo=UTC)`：
        对 naive 时间直接调 `.astimezone(CST)`，Python 会**按本地时区**
        解释它。同一条代码在 UTC 机器和东八区机器上跑出不一样的结果，
        而且不会报错 —— 这是最难查的一类 bug。
        显式 replace 之后，行为和你所在的机器完全无关。
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.astimezone(CST)


def q5_parse(stamp: str) -> datetime:
    """解析 ISO 8601 时间戳，必须是 aware。"""
    try:
        dt = datetime.fromisoformat(stamp)
    except ValueError as exc:
        # raise ... from exc 保留原始异常作为 __cause__：
        # 调用方按 ValueError 捕获，但 traceback 里能看到「原来是
        # fromisoformat 报的错」，排查时不会丢失线索。
        raise ValueError(f"无法解析时间戳: {stamp!r}") from exc

    if dt.tzinfo is None:
        # 缺时区的时间戳是**歧义**的：12:00 到底是哪里的 12:00？
        # 与其猜一个，不如让调用方说清楚。这就是「naive 不要用」的原因。
        raise ValueError(f"时间戳缺少时区信息: {stamp!r}")

    return dt


def q5_to_iso(dt: datetime) -> str:
    """序列化。naive 一律拒绝。"""
    if dt.tzinfo is None:
        raise ValueError(f"naive 时间没有时区信息，无法安全序列化: {dt!r}")
    return dt.isoformat()


def q5_days_between(d1: date, d2: date) -> int:
    """绝对天数差。

    为什么用 abs 而不是 `if d1 > d2: d1, d2 = d2, d1`：
        一行和四行的区别。date 相减得到 timedelta，`.days` 是整数天。
        注意 date 相减不会有 int 截断问题（timedelta 的 days 就是整天数）。
    """
    return abs((d2 - d1).days)


def q5_humanize_delta(td: timedelta) -> str:
    """把时间差转成「N 天 N 小时 N 分」。

    实现里最关键的一步是 `abs(td)`：
        timedelta 内部是 (days, seconds, microseconds)，
        负数会被规范成 days=-1, seconds=86340 这种「向负无穷取整」的形式。
        所以 `td.days == -1` 但 `td.seconds == 86340`（= 23:59:00），
        直接拿这两个数拼字符串会得到「-1 天 23 小时 59 分」这种鬼东西。
        先取绝对值，一切都变回直觉中的样子。
    """
    negative = td < timedelta(0)
    td = abs(td)

    days = td.days
    hours = td.seconds // 3600
    minutes = (td.seconds % 3600) // 60

    parts = []
    if days:
        parts.append(f"{days} 天")
    if hours:
        parts.append(f"{hours} 小时")
    if minutes:
        parts.append(f"{minutes} 分")
    if not parts:
        parts.append("0 分")        # 全零时至少给个「0 分」，别返回空串

    text = " ".join(parts)
    return f"-{text}" if negative else text


def q5_now_utc() -> datetime:
    """当前 UTC 时间，**带时区**。

    `datetime.utcnow()` 已经废弃（3.12 起）：
    它返回的是 naive 时间，用的时候还得自己提醒自己「这是 UTC 哦」，
    一旦混进 aware 时间做运算就炸。`datetime.now(timezone.utc)` 一步到位。
    """
    return datetime.now(timezone.utc)


# 常见错误写法：
#
#   1) 用 datetime.utcnow() / datetime.now()
#      utcnow() 返回 naive，3.12 起已废弃；now() 返回本地时区的 naive 时间。
#      两者长得一模一样，混在一起就是灾难。统一用 datetime.now(timezone.utc)。
#
#   2) naive 和 aware 混着比大小 / 相减
#      naive 和 aware 相减会 TypeError（这是好事，Python 在拦你）；
#      但 `naive < aware` 在旧版本里行为诡异，别去赌。
#
#   3) 用本地时区做换算的参照
#         datetime.fromtimestamp(0)          # 本机是 UTC+8 就得 08:00
#         datetime.fromtimestamp(0, tz=UTC)  # 永远是 00:00
#      不带 tz 参数的 fromtimestamp/timestamp 全部依赖机器设置，
#      代码一换环境结果就变。
#
#   4) 自己拼 strptime 的格式串
#         datetime.strptime(s, "%Y-%m-%dT%H:%M:%S%z")
#      这个格式**丢微秒**（没有 %f），往返一次精度就没了；
#      而且 %z 只认 "+0800" 不认 "+08:00"。
#      能 fromisoformat 就 fromisoformat：无损、能认 Z 后缀、还快 30 倍。
#
#   5) 拿 timedelta.days 去算「还剩几小时」
#         timedelta(hours=23).days == 0     # 对
#         (-timedelta(hours=1)).days == -1  # 也是「对」，但反直觉
#      负数 timedelta 的 .days/.seconds 是**规范化**过的，
#      不是「-0 天 -1 小时」。想拆成分量，先 abs。
#
#   6) 用 `datetime.now() - datetime.now()` 测耗时
#      本地时钟可能因为 NTP 校时往回跳，测出负的耗时。
#      计时用 time.perf_counter()（单调时钟），别用墙上时钟。
#
#   7) 以为 timezone(timedelta(hours=8)) 等于「中国时区」
#      它只是一个**固定偏移**。要处理历史时区规则（夏令时、时区边界变更）
#      得用 zoneinfo.ZoneInfo。固定偏移适合「存库」，不适合「展示历史时间」。
#
#   8) 把本地时间直接存进数据库
#      同一列里混着不同时区的数字，之后没人能还原。**存 aware UTC，
#      展示时再 astimezone 到目标时区**，这是唯一不会后悔的做法。


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
    """造一个独立、可预测的 logger。

    四个要素在这一段里全都出现了：
        Logger    -> logging.getLogger(name)，按名字全局唯一
        Handler   -> StreamHandler(stream)，决定「写到哪里」
        Formatter -> Formatter(LOG_FORMAT)，决定「长什么样」
        Level     -> logger.setLevel + handler.setLevel，两级过滤

    为什么要先 removeHandler 把旧的摘掉：
        getLogger(name) 对同一个名字返回**同一个对象**（logging 的全局
        注册表）。第二次调用时如果不清理，就会挂上第二个 handler，
        每条日志被输出两遍 —— 这是 logging 最常见的「灵异现象」。
        摘的时候顺手 close() 一下，StreamHandler 会 flush 掉缓冲。
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    # propagate=False：不往根 logger 冒泡。
    # 不设置的话，你精心格式化的日志会被根 logger 的 handler 再输出一遍
    # （格式还是另一套），而且测试输出里会混入别的东西。
    logger.propagate = False

    for old_handler in list(logger.handlers):    # list() 复制：边遍历边改会出问题
        logger.removeHandler(old_handler)
        old_handler.close()

    handler = logging.StreamHandler(stream)
    # handler_level 默认 NOTSET(0)，意味着「handler 这一层不过滤」。
    handler.setLevel(handler_level)
    handler.setFormatter(logging.Formatter(LOG_FORMAT))
    logger.addHandler(handler)

    return logger


def q6_safe_divide(logger: logging.Logger, a: float, b: float) -> float:
    """带日志的除法。

    两处刻意的写法：

    1) `logger.debug("计算 %s / %s = %s", a, b, result)`
       而不是 `logger.debug(f"计算 {a} / {b} = {result}")`。
       差别不是「好看」：日志被过滤掉时（比如生产环境是 INFO 级），
       %s 版本**连字符串都不会拼**，f-string 版本已经拼完了才交给
       logging 丢掉。日志级别调低之后，海量 DEBUG 日志的格式化开销
       是真实存在的性能问题，而且 f-string 里的表达式（比如
       `f"{obj!r}"` 调了很贵的 __repr__）也一样会执行。
       唯一的例外：日志"一定"会输出时（比如已经确认级别够），
       f-string 也行。**默认用 %s，有理由才用 f-string。**

    2) `logger.exception(...)` 而不是 `logger.error(f"...: {exc}")`
       exception() 会自动把当前 exc_info 的完整调用栈写进日志。
       只写一行消息的话，你在日志里看到「任务 43 失败」，
       却完全不知道是哪个文件哪一行失败的 —— 排查时等于瞎了一半。
       注意 exception() 只能在 except 块里用，级别固定 ERROR。
    """
    try:
        result = a / b
    except ZeroDivisionError:
        logger.exception("计算 %s / %s 失败", a, b)
        return 0.0
    logger.debug("计算 %s / %s = %s", a, b, result)
    return result


# 常见错误写法：
#
#   1) 用 print 代替 logging
#      print 没法按级别过滤、没法关掉、没法带时间戳和模块名、
#      没法导到文件/网络，而且和真正的日志混在 stdout 里分不开。
#      「调试时加 print，上线前再删」这种流程迟早会漏掉几个。
#
#   2) 用 logging.warning() 这类**模块级函数**
#      它们写的是根 logger，%(name)s 永远是 "root"。
#      于是你没法单独调高某个模块的级别、没法把某个模块的日志导到单独文件、
#      第三方库的日志和你自己的混在一起。每个模块顶部一行
#      `logger = logging.getLogger(__name__)` 就解决了。
#
#   3) 在这段函数里做了两次 `logger.addHandler(h)`
#      输出翻倍。这是 logging 最常见的 bug，而且因为「日志多了」看起来
#      不像 bug，很多人查半天。**配置 logger 的地方要么只跑一次，
#      要么先把旧 handler 摘干净。**
#
#   4) 忘了 `logger.propagate = False`
#      日志既被自己的 handler 处理，又被根 logger 的 handler 处理，
#      两套格式各输出一遍。测试里断言 `== "..."` 就会挂。
#
#   5) handler 的级别设得比 logger 还高却没意识到
#         logger.setLevel(DEBUG); handler.setLevel(WARNING)
#      明明调了 setLevel(DEBUG)，DEBUG 日志就是不出来。
#      **日志要输出必须同时通过 logger 和 handler 两道关卡**，
#      级别高的那道说了算。
#
#   6) 把异常信息塞进消息字符串就完事
#         logger.error(f"失败了: {exc}")
#      只有一行字，没有调用栈。用 logger.exception()。
#
#   7) 在 except 块外面用 logger.exception()
#      此时 sys.exc_info() 是空的，traceback 打出来是 "NoneType: None"，
#      比不用还糟。exception() 只该出现在 except 块里。
#
#   8) 用 root logger 的 basicConfig 去配置库代码
#      库（被 import 的模块）**永远不要**调 basicConfig ——
#      它会篡改使用者的日志配置，而且 basicConfig 只在
#      根 logger 没有 handler 时生效，行为随 import 顺序变化。
#      库只 `logger = getLogger(__name__)`，配置交给应用入口。


# ======================================================================
# q7 —— dataclasses 进阶
# ======================================================================
@dataclass
class LineItem:
    """订单行。total 是派生字段，由 __post_init__ 算出来。"""

    name: str
    price: float
    qty: int = 1
    # init=False：不出现在自动生成的 __init__ 参数里。
    # 为什么要默认值 0.0：dataclass 的字段顺序不能乱，
    # 而且 __post_init__ 里会覆盖它。给个默认值让「没走 __post_init__」
    # 也不会爆出 AttributeError。
    total: float = field(init=False, default=0.0)

    def __post_init__(self) -> None:
        """自动生成的 __init__ 最后会调用它。

        为什么校验放在这里而不是 __init__ 里：
            @dataclass 会**覆盖**你手写的 __init__，写了也白写。
            __post_init__ 是官方给的钩子，此时所有字段都已赋值。
        """
        # 先归一化再做校验：这样 "   " 和 "" 走同一条路，
        # 不用写两个分支。而且把结果写回 self.name，
        # 保证「字段值」和「校验过的值」永远是同一个。
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name 不能为空")
        if self.price <= 0:
            raise ValueError(f"price 必须为正数，收到 {self.price}")
        if self.qty < 0:
            raise ValueError(f"qty 不能为负数，收到 {self.qty}")

        self.total = self.price * self.qty


@dataclass
class Order:
    """一张订单。

    三个字段各演示了 field() 的一种用法：
        items      -> default_factory=list（可变默认值）
        note       -> repr=False（太长，不塞进 repr）
        item_count -> init=False（派生字段，不给调用方传）
    """

    order_id: str
    # 关键：可变默认值必须用 default_factory。
    # 直接写 `= []` 会被 dataclass 当场拒绝
    # （ValueError: mutable default for field items is not allowed），
    # 因为它知道这会重蹈「函数默认参数共享」的覆辙 —— 所有 Order
    # 实例会共用同一个 list。
    # default_factory=list 的意思是「每个实例调用一次 list()」。
    items: list[LineItem] = field(default_factory=list)
    # repr=False：note 可能很长（用户输入），出现在 repr 里会把
    # 日志刷得没法看。compare=True（默认）保持不变，它仍然参与 ==。
    note: str = field(default="", repr=False)
    item_count: int = field(init=False, default=0)

    def __post_init__(self) -> None:
        self.order_id = self.order_id.strip()
        if not self.order_id:
            raise ValueError("order_id 不能为空")
        self.item_count = len(self.items)


def q7_order_total(order: Order) -> float:
    """总金额。空订单返回 0.0（sum 的空序列默认值）。"""
    return sum(item.total for item in order.items)


def q7_order_to_json(order: Order) -> str:
    """序列化成 JSON。

    ensure_ascii=False：
        默认 True 会把中文转成 \\uXXXX 码点转义 —— 合法但没法读，
        而且体积膨胀 6 倍。给中国人看的配置文件/接口一律 False。
    indent=2：给人看的输出要缩进；机器之间传的 JSON 反而不缩进（省流量）。
    """
    return json.dumps(asdict(order), ensure_ascii=False, indent=2)


def q7_order_from_json(text: str) -> Order:
    """从 JSON 还原。

    关键：只把 name / price / qty 传给 LineItem，**不传 total**。
        total 是 init=False 的派生字段，传了会 TypeError；
        而且就算能传也不该传 —— 派生值应该由 __post_init__ 重算，
        否则 JSON 里那个可能被改过的 total 就成了「真相」，
        和 price * qty 对不上，账就烂了。
    """
    payload = json.loads(text)
    items = [
        LineItem(name=raw["name"], price=raw["price"], qty=raw["qty"])
        for raw in payload["items"]
    ]
    return Order(
        order_id=payload["order_id"],
        items=items,
        note=payload.get("note", ""),
    )


# 常见错误写法：
#
#   1) 手写 __init__ 而不是用 __post_init__
#         @dataclass
#         class LineItem:
#             ...
#             def __init__(self, name, price):    # 被 @dataclass 覆盖了！
#     你写的 __init__ 会被自动生成的版本**静默替换掉**，
#      调用时参数对不上才发现。校验/派生逻辑放 __post_init__。
#
#   2) 可变默认值直接写字面量
#         items: list[LineItem] = []
#     dataclass 会当场报错（比默默共享一个 list 好得多）。
#      换成 `field(default_factory=list)`。（注意是 list 这个**函数**，
#      不是 list() —— 写 list() 的话所有实例又共用一个列表了。）
#
#   3) default_factory=list() 而不是 default_factory=list
#     写成 `list()` 是「求值一次，把结果当工厂」，所有实例共用同一个列表。
#      这是个很隐蔽的坑，记法：**工厂要的是函数，不是调用结果**。
#
#   4) 把派生字段也放进 __init__ 参数
#         class LineItem: total: float = 0.0     # 没写 field(init=False)
#      调用方可以传一个和 price*qty 对不上的 total 进来，
#      数据从此不自洽。派生字段一律 field(init=False)。
#
#   5) 用 asdict 之后直接改返回值，以为影响原对象
#         d = asdict(order); d["items"][0]["name"] = "x"
#     其实 asdict 是**深拷贝**（递归处理嵌套的 dataclass / list / dict），
#      原对象不会被改。反过来说：对象很大时 asdict 有一定的深拷贝成本，
#      热路径里别反复调。
#
#   6) 用 asdict 序列化含 datetime 的对象然后 json.dumps
#      asdict 不认识 datetime，会原样留着，json.dumps 直接
#      TypeError: Object of type datetime is not JSON serializable。
#      要么 json.dumps(..., default=str)，要么先自己转成字符串。
#
#   7) 以为 frozen=True 就是「完全不可变」
#      它只挡住 `obj.field = x` 这一个操作。字段本身如果是 list，
#      照样能 append。真正的不可变要连容器一起换（tuple / frozenset）。
#
#   8) 用 @dataclass 却不写类型注解
#         @dataclass
#         class P:
#             x = 0        # 这不是字段！只是类属性
#     没有注解的赋值语句**不会**变成 dataclass 字段，
#      __init__ 里没有它，asdict 里也没有它。字段必须有注解。


# ======================================================================
# q8 —— TypeVar 与 Generic
# ======================================================================
T = TypeVar("T")
K = TypeVar("K")


class Stack(Generic[T]):
    """泛型栈。

    运行时到底发生了什么：
        `Stack[int]` 是 typing 在运行时造出来的一个「泛型别名」对象，
        `Stack[int]()` 实际上是 `Stack()` 加一个类型标记，
        **没有任何检查、没有任何特化**。`type(Stack[int]()) is Stack`
        为 True，`Stack[int]` 和 `Stack[str]` 的实例是同一个类。
        类型参数只对静态检查器有意义。

    那为什么还写：
        1) 调用方（和 IDE）知道该 push 什么类型，补全和标红都到位
        2) 库的公开 API 写清楚类型，使用者不用读源码
        3) 它也是**文档**：Stack[str] 一眼就知道里面是字符串
    """

    def __init__(self) -> None:
        self._items: list[T] = []

    def push(self, item: T) -> None:
        self._items.append(item)

    def pop(self) -> T:
        if not self._items:
            # 为什么是 IndexError：这是**容器**该有的语义。
            # 让调用方可以写 `try: s.pop() except IndexError`，
            # 和 list.pop / deque.pop 保持一致。
            raise IndexError("空栈")
        return self._items.pop()

    def peek(self) -> T:
        if not self._items:
            raise IndexError("空栈")
        return self._items[-1]

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        # 定义了 __len__ 之后，bool() 本来就会走 __len__，
        # 显式写出来只是为了让「空栈为假」这件事更醒目。
        return bool(self._items)

    def __iter__(self):
        """从栈顶往栈底迭代。"""
        # reversed(list) 返回一个迭代器，不复制 list 的内容。
        return iter(reversed(self._items))

    def to_list(self) -> list[T]:
        return list(reversed(self._items))


def q8_chunked(items: Sequence[T], size: int) -> list[list[T]]:
    """按 size 切块。

    为什么参数是 Sequence 而不是 list：
        str、tuple、range 都能切片，调用方不用先转成 list。
        「参数尽量宽，返回尽量具体」的又一处应用。

    为什么每块要 list(...) 一下：
        `items[i:i+size]` 对 str 返回的是 str、对 range 返回的是 range，
        不统一。返回类型声明的是 list[list[T]]，那就老老实实转换。
    """
    if size <= 0:
        raise ValueError(f"size 必须是正整数，收到 {size}")
    return [list(items[i:i + size]) for i in range(0, len(items), size)]


def q8_unique(items: Iterable[T]) -> list[T]:
    """保序去重。

    dict.fromkeys(items) 一步到位：
        dict 的键唯一且保序（3.7+ 的语言保证），
        所以「去重 + 保序」= 取 dict 的键。
        比手写 `seen = set(); out = []` 短，而且这是 C 层面实现的，更快。
    """
    return list(dict.fromkeys(items))


def q8_group_by(items: Iterable[T], key: Callable[[T], K]) -> dict[K, list[T]]:
    """按 key 分组，组内保序。

    为什么最后要 dict(...) 转回普通 dict：
        defaultdict 在**访问不存在的键时会自动创建它**。
        如果把它返回给调用方，一句无心的 `groups["拼错的键"]`
        就会往结果里插一个空列表，而且不报错。
        内部用它方便，对外一定要转成普通 dict。
    """
    groups: defaultdict[K, list[T]] = defaultdict(list)
    for item in items:
        groups[key(item)].append(item)
    return dict(groups)


# 常见错误写法：
#
#   1) 以为泛型在运行时会检查类型
#         s = Stack[int](); s.push("字符串")    # 照样跑，不报错
#      类型参数全是给静态检查器看的。**要运行时保护就得自己写 isinstance
#      校验**（那是 q1 那种活），别指望注解。
#
#   2) 忘了 TypeVar 直接用 T
#         T = TypeVar("T")
#         def f(x: T) -> T: ...
#     这没问题；但 `def f(x: "T") -> "T"` 又忘了先定义 T、
#      或者把 TypeVar 当成普通类去实例化 `T()`，都会炸。
#      TypeVar 是**占位符**，不是类。
#
#   3) 用 `TypeVar("T", bound=...)` 之前不考虑需不需要约束
#         T = TypeVar("T")
#         def total(xs: list[T]) -> T: return sum(xs)    # mypy 会报错
#     因为 sum 需要 T 支持 +。要么 `TypeVar("T", bound=SupportsAdd)`
#      （没有这个，得自己定义 Protocol），要么直接写 `-> float`。
#      **能用具体类型写清楚的时候，不要用泛型。**
#
#   4) 用 `list` / `dict` 当返回类型注解却返回了 None
#         注解不检查，mypy 才检查。别把注解当成「写完就不用管」的东西，
#         跑一次 mypy 能免费抓出一堆这类问题。
#
#   5) 用 `list(set(items))` 去重
#      set 是**无序**的（哈希随机化、插入顺序都不保证），
#      输出的顺序每次跑都可能不一样。要么 dict.fromkeys（保序），
#      要么 sorted(set(...))（明确排序）。
#
#   6) 分组时返回 defaultdict
#      调用方一句 `groups["不存在的组"]` 就静默插入了新键，
#      而且是在**读取**的时候 —— 排查这种 bug 极其痛苦。
#      内部用 defaultdict，出函数前转普通 dict。
#
#   7) 空栈 pop 返回 None 而不是抛异常
#         if not self._items: return None
#      调用方 `x = s.pop()` 拿到 None，之后 `x + 1` 才炸，
#      报错点离错误源头十万八千里。**空容器上的非法操作要立刻报错。**
#
#   8) 用 index 下标遍历而不是迭代
#         for i in range(len(items)): use(items[i])
#      又慢又容易越界。直接 `for item in items`。
#      需要下标就用 `enumerate(items)`。


# ======================================================================
# q9 —— collections 实战
# ======================================================================
#: 「词」= 连续的字母或数字。中文汉字、标点、空白都是分隔符。
#: 用 [a-z0-9] 而不是 \w：\w 会把汉字和下划线也算进去，
#: 分词结果就不是我们想要的了。
WORD_RE = re.compile(r"[a-z0-9]+")


def q9_word_count(text: str) -> Counter[str]:
    """词频统计。

    两行的活：先转小写再 findall，Counter 直接吃 list。
    Counter 是 dict 的子类，所以 `counts["没见过的词"]` 返回 0
    而**不会** KeyError —— 这是 Counter 和 defaultdict 的关键区别
    （它不插入键，只是返回 0）。
    """
    return Counter(WORD_RE.findall(text.lower()))


def q9_top_n(counts: Counter[str], n: int) -> list[tuple[str, int]]:
    """取词频前 n。

    为什么不用 Counter.most_common(n)：
        most_common 用的是 heapq.nlargest，并列时的顺序取决于
        **插入顺序**（也就是文本里词出现的先后），不确定。
        要「并列按字典序」就必须自己 sorted。

    排序键 (-count, word) 的含义：
        负号 = 次数降序（Python 的 sorted 只能升序，用负号反转数值），
        第二项 = 词升序。元组按位比较，正好实现「先按次数、再按名字」。
    """
    if n <= 0:
        raise ValueError(f"n 必须是正整数，收到 {n}")
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def q9_group_records(records: Iterable[tuple[str, str]]) -> dict[str, list[str]]:
    """按第一个字段分组。"""
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for group, value in records:
        groups[group].append(value)
    # 转成普通 dict 再返回：见上面 q8_group_by 的说明。
    return dict(groups)


def q9_recent(items: Iterable[T], n: int) -> list[T]:
    """取最后 n 个。

    deque(maxlen=n) 的妙处：
        它是一个**有界**队列，追加超过 n 个时会自动从另一头挤掉最老的。
        内存占用永远是 n 个元素，不管输入是一万条还是一亿条。
        所以这个版本的记忆开销是 O(n)，而不是「先全读进 list 再切片」的 O(N)。

    注意：`deque(iterable, maxlen=n)` 仍然会**完整消费**这个迭代器
    （时间是 O(N)），只是内存是 O(n)。想连时间都省掉，
    得靠「是不是 Sequence」来判断能不能直接切片。
    """
    if n <= 0:
        raise ValueError(f"n 必须是正整数，收到 {n}")
    return list(deque(items, maxlen=n))


# 常见错误写法：
#
#   1) 用普通 dict 手写计数
#         counts = {}
#         for w in words:
#             counts[w] = counts.get(w, 0) + 1
#      能跑，但 `Counter(words)` 一行就完了，而且 Counter 还自带
#      most_common / 加减运算 / total()。**先翻 collections 文档再动手。**
#
#   2) 用 `sorted(counts.items(), key=lambda kv: kv[1], reverse=True)`
#      并列时的顺序不确定（Python 的排序是稳定的，但「原始顺序」
#      取决于 dict 的插入顺序，也就是文本里词出现的先后）。
#      要可复现就得把完整排序键写出来：`(-count, word)`。
#
#   3) 用 `counts.most_common(n)` 然后以为并列是有序的
#      同上。它在「次数不同」时是对的，并列时不行。
#      测试里那组 z/a/m 各出现两次的用例就是专门抓这个的。
#
#   4) 把 defaultdict 直接返回给调用方
#         return groups            # 类型是 defaultdict
#      调用方 `groups["拼错的组名"]` 会**静默创建**一个空列表，
#      不报错、不留痕。对外一律 `dict(groups)`。
#
#   5) 用 set 求「去重后的顺序」
#         list(set(items))
#     顺序每次跑都可能不同。要保序用 dict.fromkeys，
#      要确定顺序用 sorted(set(items))。
#
#   6) 用 list 当队列并从头部删除
#         queue.pop(0)
#     这是 O(n)：后面所有元素都要往前挪。数据一多就是性能灾难。
#      两端操作一律用 collections.deque，两端都是 O(1)。
#
#   7) 用 deque 却不用 maxlen
#         d = deque()
#         for x in stream: d.append(x)
#         return list(d)[-n:]
#      内存里存了**全部**元素，白瞎了 deque 的最大优势。
#      要「最近 n 条」就直接 `deque(stream, maxlen=n)`。
#
#   8) 用 `len(counts)` 求词的总出现次数
#      len 是**不同的词**的个数。总出现次数是 `sum(counts.values())`
#      或 3.10+ 的 `counts.total()`。这两个数经常被搞混，
#      在统计报表里是会出人命的错误。


# ======================================================================
# 自测（和 exercises.py 里的一模一样）
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
    c = Checker("模块 07 · 标准库与类型注解 参考答案")
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
