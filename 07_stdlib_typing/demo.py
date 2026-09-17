"""
模块 07 · 标准库与类型注解 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. 猜一下这段代码会输出什么
    3. 再跑，看是否和你想的一样

本文件所有文件操作都在 tempfile.TemporaryDirectory() 里完成，
运行结束后不会在项目目录留下任何残留文件。
"""

from __future__ import annotations

import io
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# 7.1 类型注解在运行时发生了什么
# ======================================================================
def demo_annotations() -> None:
    section("7.1 类型注解在运行时到底发生了什么")

    import typing

    print("  -- 变量注解：解释器什么都不做 --")
    x: int = "我其实是个字符串"
    print(f"     x: int = '我其实是个字符串'")
    print(f"     type(x) = {type(x).__name__}   值是 {x!r}")
    printed: dict[str, int] = "注解完全不检查"
    print(f"     printed: dict[str, int] = '注解完全不检查'")
    print(f"     type(printed) = {type(printed).__name__}")
    print("     ^ 没有报错、没有转换、没有检查。注解只是给工具看的元信息。")
    print()

    print("  -- 函数注解会被存下来 --")

    def greet(name: str, times: int = 1) -> str:
        return f"你好，{name} " * times

    print(f"     greet.__annotations__ = {greet.__annotations__}")
    print(f"     全是字符串？ {all(isinstance(v, str) for v in greet.__annotations__.values())}")
    print("     ^ 因为我们文件开头有 `from __future__ import annotations`，")
    print("       所有注解都被存成了源码里的字符串，从来没有被求值过。")
    print()

    print("  -- 用 get_type_hints 把它们变成真实类型 --")
    hints = typing.get_type_hints(greet)
    print(f"     typing.get_type_hints(greet) = {hints}")
    print(f"     hints['name'] is str    -> {hints['name'] is str}"
          f"   <- 这才是真正的类型对象")
    print("     ^ 这就是框架（pydantic / FastAPI / dataclass 校验）读取注解的方式：")
    print("       先 get_type_hints 解析成真实类型，再据此做事。")
    print()

    print("  -- __annotate__：3.14 的新机制（PEP 649）--")
    print(f"     hasattr(greet, '__annotate__') = {hasattr(greet, '__annotate__')}")
    print("     每个带注解的函数/类现在都有一个 __annotate__ 属性，")
    print("     它是一段「算注解的代码」，默认到第一次读注解时才被调用。")
    print()

    print("     在**有** future import 的文件里，三种格式拿到的都是字符串：")
    try:
        import annotationlib

        for fmt_name in ("VALUE", "FORWARDREF", "STRING"):
            fmt = getattr(annotationlib.Format, fmt_name)
            got = annotationlib.get_annotations(greet, format=fmt)
            print(f"        Format.{fmt_name:<10} -> {got}")
        print("     ^ 因为 future import 把注解本体改成了「求值结果就是字符串」，")
        print("       三种格式自然一样。要看真实差别，得在没有 future import 的地方跑：")
        print()

        plain_src = (
            "def sample(a: int, b: UndefinedName) -> str:\n"   # noqa: F821
            "    return ''\n"
        )
        plain_ns: dict = {}
        # 关键：compile 默认会**继承调用处的 future 标志**，
        # 所以必须显式写 dont_inherit=True，才能真正模拟一个没有
        # `from __future__ import annotations` 的普通模块。
        plain_code = compile(plain_src, "<没有 future import 的模块>", "exec",
                             dont_inherit=True)
        exec(plain_code, plain_ns)
        sample = plain_ns["sample"]
        for fmt_name in ("VALUE", "FORWARDREF", "STRING"):
            fmt = getattr(annotationlib.Format, fmt_name)
            try:
                got = annotationlib.get_annotations(sample, format=fmt)
                print(f"        Format.{fmt_name:<10} -> {got}")
            except NameError as exc:
                print(f"        Format.{fmt_name:<10} -> NameError: {exc}")
        print()
        print("        VALUE      -> 立刻求值，名字不存在就 NameError")
        print("        FORWARDREF -> 不求值，未定义的名字包成 ForwardRef 占位符")
        print("        STRING     -> 原样返回源码字符串，最安全也最没用")
        print("     ^ 默认值是 VALUE，但框架为了兼容前向引用通常会用 FORWARDREF。")
        print("     annotationlib 是 3.14 才有的模块；")
        print("     3.13 及以前读注解只能靠 inspect.get_annotations 这类土办法。")
    except ImportError:
        print("     （这台机器上没有 annotationlib，跳过）")
    print()

    print("  -- 前向引用：不用写引号了 --")

    class Node:
        # 在 3.13 及以前，这里的 Node 必须写成字符串 "Node"，
        # 因为类还没定义完，名字还不存在。
        # 有了延迟求值（或 future import），直接写 Node 就行。
        def __init__(self, value: int, next_: Node | None = None) -> None:
            self.value = value
            self.next = next_

    n = Node(1, Node(2))
    print(f"     Node.__init__.__annotations__ = {Node.__init__.__annotations__}")
    print(f"     n.next.value = {n.next.value}")
    print()

    print("  -- 泛型别名在运行时是什么 --")
    print(f"     list[int]        = {list[int]!r}     type = {type(list[int]).__name__}")
    print(f"     dict[str, int]   = {dict[str, int]!r}")
    print("     ^ 它是一个 types.GenericAlias 对象，运行时不检查任何东西，")
    print("       只是给 mypy/pyright 看的标记。")
    print()

    print("  -- 注解不隔离名字：一个反例 --")

    def broken(v: NotDefinedAnywhere) -> None:   # noqa: F821
        return None

    print("     def broken(v: NotDefinedAnywhere) -> None: ...  定义成功，没报错")
    try:
        broken.__annotations__
    except NameError as exc:
        print(f"     但访问 broken.__annotations__ -> NameError: {exc}")
    print("     ^ 延迟求值的意思是「需要时才求值」，不是「永不求值」。")
    print("       名字拼错了，mypy 会立刻告诉你；运行时则要等到你读注解才炸。")


# ======================================================================
# 7.2 typing 常用类型
# ======================================================================
def demo_typing_basics() -> None:
    section("7.2 typing 常用类型：把「能接受什么」写清楚")

    from typing import Any, Final, Literal, TypedDict, get_type_hints

    print("  -- 参数类型写「最宽的」，返回类型写「最具体的」--")

    from collections.abc import Iterable, Iterator, Sequence

    def total_wide(values: Iterable[int]) -> int:
        """只要能被迭代就行。"""
        return sum(values)

    def total_narrow(values: list[int]) -> int:
        """只接受 list —— 调用方被这个签名限制了。"""
        return sum(values)

    samples = [[1, 2, 3], (1, 2, 3), range(1, 4), {1, 2, 3}, (n for n in (1, 2, 3))]
    for sample in samples:
        name = type(sample).__name__
        wide = total_wide(sample)
        narrow = "可以" if isinstance(sample, list) else "不行（类型不符）"
        print(f"     {name:<10} total_wide -> {wide}    total_narrow -> {narrow}")
    print("     ^ 参数写 Iterable 而不是 list，调用方能少做很多无意义的转换。")
    print()

    print("  -- Any 会「污染」它接触到的一切 --")

    def leaky(data: Any) -> Any:
        return data

    print(f"     Any + int 的类型还是 Any —— 静态检查器从这里开始就放弃了。")
    print(f"     能用具体类型就别用 Any；非用不可时把范围缩到最小。")
    print()

    print("  -- Literal：把魔法字符串变成可检查的常量 --")

    def open_file(path: str, mode: Literal["r", "w", "a"]) -> str:
        return f"用 {mode} 模式打开 {path}"

    print(f"     open_file('a.txt', 'r') -> {open_file('a.txt', 'r')!r}")
    print("     open_file('a.txt', 'x') -> mypy 会报错（运行时不会）")
    print("     ^ IDE 能给你补全 r/w/a，写错了立刻标红。比裸 str 强太多。")
    print()

    print("  -- Final：常量 --")
    MAX_RETRY: Final = 3
    print(f"     MAX_RETRY: Final = {MAX_RETRY}")
    print("     运行时不阻止你改它，但 mypy 会。这是「意图声明」，不是运行时保护。")
    print()

    print("  -- TypedDict：给固定键名的 dict 加类型 --")

    class _MovieRequired(TypedDict):
        title: str
        year: int

    # total=False 表示「这个类里新加的键都是可选的」。
    # 用继承而不是 NotRequired[]，是因为本文件有
    # `from __future__ import annotations`，而字符串模式下
    # NotRequired 识别不出来 —— 见 README 7.1。
    class Movie(_MovieRequired, total=False):
        rating: float
        tags: list[str]

    print(f"     Movie.__required_keys__ = {Movie.__required_keys__}")
    print(f"     Movie.__optional_keys__ = {Movie.__optional_keys__}")
    print(f"     注意运行时它就是 dict：type({{...}}) = {type({'title': 'x', 'year': 1}).__name__}")

    m: Movie = {"title": "让子弹飞", "year": 2010, "rating": 9.1}
    print(f"     m = {m}")
    print(f"     m['titel'] 拼错了 -> mypy 报错，运行时不报（就是 KeyError）")
    print()

    print("     get_type_hints 能把 ForwardRef 解析成真实类型：")
    for name, hint in get_type_hints(Movie).items():
        print(f"        {name:<8} -> {hint}")

    print()
    print("  -- TypedDict 和 NotRequired 的坑（3.14 实测）--")

    from typing import NotRequired

    class WithNotRequired(TypedDict):
        title: str
        rating: NotRequired[float]

    print(f"     带 future import 时：")
    print(f"        __required_keys__ = {WithNotRequired.__required_keys__}")
    print(f"        ^ rating 本该是可选的，但因为注解被存成字符串，")
    print(f"          NotRequired 包装没被识别出来。")
    print("     结论：要么去掉 future import，要么用 total=False 继承。")


# ======================================================================
# 7.3 Protocol 与结构化子类型
# ======================================================================
def demo_protocol() -> None:
    section("7.3 Protocol：鸭子类型的类型化表达")

    from abc import ABC, abstractmethod
    from typing import Protocol, runtime_checkable

    print("  -- 名义子类型（ABC）：必须显式继承 --")

    class NominalSink(ABC):
        @abstractmethod
        def send(self, msg: str) -> None:
            """抽象方法，子类必须实现。"""

    class MyNominalSink(NominalSink):
        def send(self, msg: str) -> None:
            print(f"        [ABC 版] {msg}")

    print("     class MyNominalSink(NominalSink)  <- 不写 (NominalSink) 就不算数")
    MyNominalSink().send("hello")
    print()

    print("  -- 结构化子类型（Protocol）：有这个方法就算 --")

    @runtime_checkable
    class Sink(Protocol):
        def send(self, msg: str) -> None: ...

    # 注意：下面两个类和 Sink 没有任何继承关系
    class ListSink:
        def __init__(self) -> None:
            self.items: list[str] = []

        def send(self, msg: str) -> None:
            self.items.append(msg)

    class ConsoleSink:
        def __init__(self) -> None:
            self.output: list[str] = []

        def send(self, msg: str) -> None:
            self.output.append(f"<控制台> {msg}")

    class NotASink:
        def totally_different(self) -> None:
            pass

    def broadcast(sinks: list[Sink], msg: str) -> None:
        """只要求「有 send 方法」，不管对方是什么类。"""
        for s in sinks:
            s.send(msg)

    a, b = ListSink(), ConsoleSink()
    broadcast([a, b], "广播消息")
    print(f"     ListSink 收到    -> {a.items}")
    print(f"     ConsoleSink 收到 -> {b.output}")
    print("     ^ 两个类都不知道 Sink 的存在，但都能传进去。")
    print()

    print("  -- runtime_checkable：运行时 isinstance --")
    print(f"     isinstance(ListSink(), Sink)    = {isinstance(ListSink(), Sink)}")
    print(f"     isinstance(ConsoleSink(), Sink) = {isinstance(ConsoleSink(), Sink)}")
    print(f"     isinstance(NotASink(), Sink)    = {isinstance(NotASink(), Sink)}")
    print(f"     isinstance(MyNominalSink(), Sink)= {isinstance(MyNominalSink(), Sink)}"
          f"   <- ABC 的实例也满足 Protocol")
    print()

    print("  -- runtime_checkable 的重要限制：只查方法名，不查签名 --")

    @runtime_checkable
    class Callable1(Protocol):
        def run(self, x: int) -> int: ...

    class WrongSignature:
        def run(self, totally, wrong, signature):   # 签名完全不对
            return None

    class RightSignature:
        def run(self, x: int) -> int:
            return x

    print(f"     isinstance(WrongSignature(), Callable1) = {isinstance(WrongSignature(), Callable1)}")
    print(f"     isinstance(RightSignature(), Callable1) = {isinstance(RightSignature(), Callable1)}")
    print("     ^ 签名不对也照样 True！运行时只能看属性名是否存在。")
    print("       所以 **别拿 runtime_checkable 的 isinstance 当参数校验**，")
    print("       它的合理用途是分发/路由。真正的检查交给 mypy。")
    print()

    print("  -- 内置的 Protocol：Python 标准库里已经有一堆 --")
    from typing import SupportsAbs, SupportsFloat, SupportsIndex, SupportsInt

    print(f"     typing.SupportsInt / SupportsFloat / SupportsIndex / SupportsAbs ...")
    print("     它们都是 Protocol，所以任何实现了 __int__ / __float__ 的类都算数。")
    print(f"     int(3.9) 走的就是 __int__ 协议 -> {int(3.9)}")
    print(f"     float(3) 走 __float__          -> {float(3)}")
    print(f"     abs(-3)  走 __abs__            -> {abs(-3)}")
    print(f"     isinstance(3, SupportsInt)     -> {isinstance(3, SupportsInt)}")
    print(f"     isinstance(3, SupportsIndex)   -> {isinstance(3, SupportsIndex)}")
    print(f"     isinstance(3, SupportsAbs)     -> {isinstance(3, SupportsAbs)}")
    print(f"     isinstance(3.5, SupportsInt)   -> {isinstance(3.5, SupportsInt)}"
          f"   <- float 也有 __int__")
    print("     ^ 这些 Supports* 全是 @runtime_checkable 的 Protocol，")
    print("       所以 abs()/int()/len() 这些内置函数的输入要求能用类型表达出来。")


# ======================================================================
# 7.4 mypy（本模块不 import 它，只演示怎么用）
# ======================================================================
def demo_mypy_note() -> None:
    """这一节没有可运行的代码，只有命令和使用姿势。

    为什么要单独占一节：
        「注解不影响运行时」这件事，光靠读代码是体会不到的 ——
        你必须亲眼看到「同一段代码，mypy 报错、Python 却跑得好好的」，
        才会真正接受「注解是给工具看的」这个定位。
    """
    section("7.4 mypy：注解是给工具看的（这一节只有命令）")

    print("  第一步：装（这是本课程唯一需要装的东西，而且只在命令行用）")
    print("      pip install mypy")
    print()
    print("  第二步：拿本模块的答案去体检")
    print("      mypy 07_stdlib_typing/solutions.py --ignore-missing-imports")
    print("      ^ --ignore-missing-imports 是因为 solutions.py 会 import 根目录的")
    print("        course_kit，mypy 找不到它的类型信息时会唠叨。")
    print()
    print("  第三步：亲眼看看「mypy 报错、Python 不报」是什么样子")
    print("      新建一个 tmp_check.py，内容如下：")
    print()
    print("          from __future__ import annotations")
    print()
    print("          def double(x: int) -> int:")
    print("              return x * 2")
    print()
    print("          print(double('abc'))          # 运行时会打印 abcabc")
    print("          bad: int = 'not an int'       # 运行时什么都不发生")
    print()
    print("      跑 `python tmp_check.py`  -> 正常输出 abcabc，退出码 0")
    print("      跑 `mypy tmp_check.py`    -> 两行 error，退出码 1")
    print()
    print("  这就是「注解不影响运行时」的全部含义：")
    print("      解释器读完注解就扔（或者存起来），从不据此做任何检查；")
    print("      检查是 mypy / pyright / IDE 在**另一个时间点**做的事。")
    print()
    print("  几个实用姿势：")
    print("      mypy --strict your_module.py      # 新项目建议直接上 strict")
    print("      mypy --install-types              # 自动补装第三方库的 stub")
    print("      # type: ignore[error-code]        # 精确地只忽略某一条")
    print("      reveal_type(obj)                  # 让 mypy 打印它推断出的类型")
    print()
    print("  本模块的代码**一个都不 import mypy**，注解全部只用标准库的 typing。")
    print("  mypy 是外挂工具，不是依赖 —— 装不装都不影响这些代码运行。")


# ======================================================================
# 7.5 dataclasses 进阶
# ======================================================================
def demo_dataclasses() -> None:
    section("7.5 dataclasses 进阶：field / asdict / 校验")

    import json
    from dataclasses import asdict, astuple, dataclass, field

    @dataclass
    class Config:
        # 可变默认值必须用 default_factory，
        # dataclass 会直接拒绝你写 `tags: list = []`
        tags: list[str] = field(default_factory=list)

        # 不参与 repr 和比较（缓存类字段）
        cache: dict[str, int] = field(default_factory=dict, repr=False, compare=False)

        # 由 __post_init__ 填的派生字段，不允许调用方传
        tag_count: int = field(init=False, default=0)

        # metadata 是给框架/自己读的，dataclass 本身不解释它
        name: str = field(default="default", metadata={"help": "配置项名字"})

        def __post_init__(self) -> None:
            # 自动生成的 __init__ 最后会调用这里，此时所有字段都已就位
            self.tag_count = len(self.tags)

    c = Config(tags=["a", "b", "c"], name="演示")
    print("  -- field() 的四种用法 --")
    print(f"     repr(c)          = {c!r}        <- cache 没出现（repr=False）")
    print(f"     c.tag_count      = {c.tag_count}              <- 由 __post_init__ 算出来的")
    print(f"     c.cache          = {c.cache}")
    print(f"     字段元数据       = {Config.__dataclass_fields__['name'].metadata}")
    print()

    print("  -- 可变默认值的陷阱 --")

    @dataclass
    class WithFactory:
        items: list[int] = field(default_factory=list)

    @dataclass
    class AlsoFactory:
        items: list[int] = field(default_factory=list)

    w1, w2 = WithFactory(), WithFactory()
    w1.items.append(1)
    print(f"     WithFactory() 的 items 互相独立吗？ {w1.items} / {w2.items}   -> 独立")

    def bad_func(items: list = []):     # 函数默认参数的经典坑
        items.append(1)
        return items

    print(f"     对比函数默认参数：bad_func() = {bad_func()}，bad_func() = {bad_func()}"
          f"   <- 共享同一个列表！")
    print("     dataclass 直接禁止你在字段上写可变字面量，把这个坑堵死了。")
    print()

    print("  -- asdict / astuple：序列化 --")
    print(f"     asdict(c)  = {asdict(c)}")
    print(f"     astuple(c) = {astuple(c)}")
    print(f"     原对象没被影响？ c.tags = {c.tags}")

    d = asdict(c)
    d["tags"].append("被改了")
    print(f"     改动 asdict 的结果后，原对象的 tags = {c.tags}   <- 深拷贝，安全")
    print()

    print("  -- 和 json 配合 --")
    print(f"     json.dumps(asdict(c), ensure_ascii=False)")
    print(f"        -> {json.dumps(asdict(c), ensure_ascii=False)}")
    print()

    print("  -- asdict 不认非 dataclass 的嵌套对象 --")
    from datetime import datetime, timezone

    @dataclass
    class Event:
        name: str
        when: datetime

    e = Event("启动", datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc))
    print(f"     asdict(e) = {asdict(e)}")
    print("     ^ datetime 被原样保留，json.dumps 还是会炸：")
    try:
        json.dumps(asdict(e))
    except TypeError as exc:
        print(f"        TypeError: {exc}")
    print("     所以要配合 default= 钩子：")
    print(f"        -> {json.dumps(asdict(e), default=str)}")
    print()

    print("  -- frozen=True：不可变 + 可哈希 --")

    @dataclass(frozen=True)
    class Point:
        x: int
        y: int = 0

    p = Point(1, 2)
    print(f"     Point(1, 2) = {p}    hash = {hash(p)}")
    print(f"     p == Point(1, 2) -> {p == Point(1, 2)}")
    print(f"     放进 set -> { {Point(1, 2), Point(3, 4)} }")
    try:
        p.x = 99
    except Exception as exc:
        print(f"     p.x = 99 -> {type(exc).__name__}: {exc}")

    @dataclass
    class Mutable:
        x: int
        y: int = 0

    print(f"     非 frozen 的 dataclass 是不可哈希的：")
    try:
        hash(Mutable(1, 2))
    except TypeError as exc:
        print(f"        TypeError: {exc}")
    print("     ^ 因为 __eq__ 被自动生成，__hash__ 就被设成 None 了（模块 04 讲过）。")


# ======================================================================
# 7.6 logging
# ======================================================================
def demo_logging() -> None:
    section("7.6 logging：四个要素与两级过滤")

    import logging

    print("  -- 级别数值 --")
    for name in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        print(f"     {name:<9} = {getattr(logging, name)}")
    print()

    print("  -- 最小可用配置：basicConfig 给根 logger 装 handler --")
    logging.basicConfig(
        level=logging.WARNING,
        format="%(levelname)-8s %(name)s: %(message)s",
        force=True,          # 3.8+：把已有的 handler 清掉重来，演示用
    )
    root = logging.getLogger()
    print(f"     根 logger 的 level = {logging.getLevelName(root.level)}")
    print(f"     根 logger 的 handlers = {root.handlers}")
    print("     下面 5 条日志里，只有 WARNING 及以上会出现：")
    logging.debug("这条 DEBUG 被过滤掉了")
    logging.info("这条 INFO 也被过滤掉了")
    logging.warning("这条 WARNING 会出现")
    logging.error("这条 ERROR 会出现")
    logging.critical("这条 CRITICAL 会出现")
    print()

    print("  -- 两级过滤：logger.level 和 handler.level 都要过 --")
    logger = logging.getLogger("demo.two_level")
    logger.propagate = False
    logger.setLevel(logging.DEBUG)

    buf = io.StringIO()
    handler = logging.StreamHandler(buf)
    handler.setLevel(logging.INFO)          # handler 门槛更高
    handler.setFormatter(logging.Formatter("%(levelname)s|%(message)s"))
    logger.addHandler(handler)

    logger.debug("DEBUG: logger 通过，但 handler 拦住了")
    logger.info("INFO: 两级都通过")
    print(f"     缓冲区内容 = {buf.getvalue()!r}")
    print("     ^ DEBUG 记录产生了，但被 handler 的 level 挡住，没写出来。")
    print("       「日志怎么不见了」90% 是这个原因。")
    logger.removeHandler(handler)
    print()

    print("  -- %s 延迟格式化：被过滤掉的日志几乎零成本 --")

    import timeit

    quiet = logging.getLogger("demo.quiet")
    quiet.propagate = False
    quiet.setLevel(logging.WARNING)         # DEBUG 会被过滤掉
    quiet.addHandler(logging.NullHandler())

    class Expensive:
        def __repr__(self) -> str:
            # 假装这是个很贵的 __repr__
            sum(range(200))
            return "<Expensive>"

    obj = Expensive()

    def lazy_style() -> None:
        quiet.debug("值 = %s", obj)          # 不格式化

    def eager_style() -> None:
        quiet.debug(f"值 = {obj}")           # 一定格式化

    t_lazy = timeit.timeit(lazy_style, number=20000)
    t_eager = timeit.timeit(eager_style, number=20000)
    print(f"     20000 次被过滤的 DEBUG 日志：")
    print(f"        延迟格式化 logger.debug('%s', obj) : {t_lazy:.4f} 秒")
    print(f"        f-string     logger.debug(f'{{obj}}') : {t_eager:.4f} 秒")
    print(f"        慢 {t_eager / t_lazy:.1f} 倍（而且这条日志根本没输出！）")
    print()

    print("  -- 为什么不要用 logging.warning() --")
    print(f"     logging.getLogger().name        = {logging.getLogger().name!r}   <- 根 logger")
    print(f"     logging.getLogger(__name__).name = {logging.getLogger(__name__).name!r}")
    print()
    print("     往根 logger 挂一个 handler，同时用两种方式打日志：")
    b2 = io.StringIO()
    h2 = logging.StreamHandler(b2)
    h2.setFormatter(logging.Formatter("%(name)-12s|%(levelname)-8s|%(message)s"))
    root = logging.getLogger()
    root.addHandler(h2)
    try:
        logging.warning("模块级 logging.warning() 打的")
        logging.getLogger("course.m07").warning("自家 logger 打的")
    finally:
        # 演示完一定要摘掉，否则会影响后面的输出
        root.removeHandler(h2)
    for line in b2.getvalue().splitlines():
        print(f"        {line}")
    print("     ^ 模块级函数的 %(name)s 永远是 'root'，于是：")
    print("       1) 没法单独调高/调低某个业务模块的级别")
    print("       2) 没法把某个模块的日志单独导到文件")
    print("       3) 第三方库的日志和你自己的混在一起，分不开")
    print("       所以每个模块开头写 logger = logging.getLogger(__name__)，")
    print("       它的名字就是模块的完整导入路径，过滤和分发都靠它。")
    print()

    print("  -- logger.exception：把 traceback 一起打进去 --")

    def divide(a: int, b: int) -> float:
        try:
            return a / b
        except ZeroDivisionError:
            logger.exception("除法失败: %s / %s", a, b)
            return 0.0

    logger.handlers.clear()
    log_buf = io.StringIO()
    log_handler = logging.StreamHandler(log_buf)
    log_handler.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    logger.addHandler(log_handler)

    divide(1, 0)
    captured = log_buf.getvalue()
    print(f"     日志行数 = {len(captured.splitlines())}")
    print("     内容（截取前 4 行）：")
    for line in captured.splitlines()[:4]:
        print(f"        {line}")
    print("     ^ 自动带上了完整的调用栈。手写 logger.error(f'...: {exc}') 只有一行消息，")
    print("       排查时等于瞎了一半。")
    logger.removeHandler(log_handler)


# ======================================================================
# 7.7 argparse
# ======================================================================
def demo_argparse() -> None:
    section("7.7 argparse：把函数变成命令行工具")

    import argparse

    def build_parser() -> argparse.ArgumentParser:
        """只负责构造 parser —— 拆出来才能被测试单独调用。"""
        parser = argparse.ArgumentParser(
            prog="tasks",
            description="一个任务管理小工具。",
            epilog="示例: tasks add 写作业 --priority high",
        )
        sub = parser.add_subparsers(dest="command", required=True)

        p_add = sub.add_parser("add", help="添加一个任务")
        p_add.add_argument("title", help="任务标题")
        p_add.add_argument(
            "--priority",
            choices=["low", "medium", "high"],
            default="medium",
            help="优先级（默认 medium）",
        )
        p_add.add_argument("--tag", action="append", default=[],
                           help="标签，可以重复出现")
        p_add.add_argument("-v", "--verbose", action="store_true",
                           help="输出详细信息")

        p_list = sub.add_parser("list", help="列出任务")
        p_list.add_argument("--limit", type=int, default=10, help="最多显示几条")
        p_list.add_argument("--all", action="store_true", help="显示全部")

        p_done = sub.add_parser("done", help="标记任务完成")
        p_done.add_argument("ids", type=int, nargs="+", help="任务编号，至少一个")

        return parser

    parser = build_parser()

    print("  -- parse_args 可以直接接收 argv 列表（测试的关键）--")
    cases = [
        ["add", "写作业"],
        ["add", "写作业", "--priority", "high", "--tag", "a", "--tag", "b", "-v"],
        ["list"],
        ["list", "--limit", "3", "--all"],
        ["done", "1", "2", "3"],
    ]
    for argv in cases:
        ns = parser.parse_args(argv)
        print(f"     {str(argv):<58} -> {vars(ns)}")
    print()

    print("  -- type= 是「函数」，不只是类型 --")

    def parse_size(text: str) -> int:
        """支持 10K / 3M 这种写法。抛 ValueError 时 argparse 会友好报错。"""
        suffix = text[-1].upper()
        if suffix in "KMG":
            return int(text[:-1]) * {"K": 1024, "M": 1024 ** 2, "G": 1024 ** 3}[suffix]
        return int(text)

    p2 = argparse.ArgumentParser(prog="demo2", add_help=False)
    p2.add_argument("--size", type=parse_size, default=0)
    for value in ("1024", "10K", "3M"):
        print(f"     --size {value:<6} -> {p2.parse_args(['--size', value]).size}")
    try:
        p2.parse_args(["--size", "abc"])
    except SystemExit as exc:
        print(f"     --size abc    -> argparse 报了错并 SystemExit({exc.code})")
    print()

    print("  -- 自动生成的 -h --")
    print("     parser.format_help() 的前几行：")
    for line in parser.format_help().splitlines()[:6]:
        print(f"        {line}")
    print("     ^ 每个参数都写了 help=，所以 -h 是有用的。")
    print()

    print("  -- 子命令的帮助是独立的 --")
    sub_action = next(a for a in parser._actions if isinstance(a, argparse._SubParsersAction))
    add_parser = sub_action.choices["add"]
    print("     `tasks add -h` 会显示：")
    for line in add_parser.format_help().splitlines():
        print(f"        {line}")


# ======================================================================
# 7.8 re 正则
# ======================================================================
def demo_re() -> None:
    section("7.8 re：解析、提取、替换")

    import re

    print("  -- 原始字符串：为什么必须写 r'...' --")
    plain = "\\d"        # 两个字符：反斜杠 + d
    print(f"     '\\d' 这个字面量有 {len(plain)} 个字符：反斜杠 + d")
    print(f"     不写 r 的时候，'\\b' 是退格符（0x08），r'\\b' 才是词边界断言")
    print(f"     re.search(r'\\bcat\\b', 'a cat here')  -> "
          f"{bool(re.search(r'\bcat\b', 'a cat here'))}")
    print(f"     re.search(r'\\bcat\\b', 'concatenate') -> "
          f"{bool(re.search(r'\bcat\b', 'concatenate'))}   <- 词边界的效果")
    print("     ^ 写 Windows 路径、写正则，都用 r'...'，能避免一整类神秘 bug。")
    print()

    print("  -- match / search / fullmatch 的区别 --")
    text = "2024-03-01 ERROR 磁盘满了"
    print(f"     text = {text!r}")
    print(f"     re.match(r'\\d+', text)      -> {re.match(r'\d+', text)}")
    print(f"     re.search(r'ERROR', text)   -> {re.search(r'ERROR', text)}")
    print(f"     re.match(r'ERROR', text)    -> {re.match(r'ERROR', text)}   <- 开头不是它")
    print(f"     re.fullmatch(r'\\d+', '123')  -> {re.fullmatch(r'\d+', '123')}")
    print(f"     re.fullmatch(r'\\d+', '12a')  -> {re.fullmatch(r'\d+', '12a')}")
    print()

    print("  -- findall 的陷阱：有一个分组时只返回分组内容 --")
    s = "a1b22c333"
    print(f"     re.findall(r'\\d+', {s!r})       -> {re.findall(r'\d+', s)}")
    print(f"     re.findall(r'(\\d)', {s!r})      -> {re.findall(r'(\d)', s)}   <- 只剩分组！")
    print(f"     re.findall(r'(\\d)(\\d)', 'a12b34') -> {re.findall(r'(\d)(\d)', 'a12b34')}")
    print(f"     re.findall(r'(?:\\d)+', {s!r})   -> {re.findall(r'(?:\d)+', s)}   <- 非捕获分组")
    print()

    print("  -- 命名分组：字段一多就必须用 --")
    LOG_RE = re.compile(
        r"^(?P<date>\d{4}-\d{2}-\d{2})\s+"
        r"(?P<time>\d{2}:\d{2}:\d{2})\s+"
        r"(?P<level>[A-Z]+)\s+"
        r"(?P<msg>.*)$"
    )
    lines = [
        "2024-03-01 12:00:05 INFO  处理任务 42",
        "2024-03-01 12:00:06 ERROR 任务 43 失败",
        "这行格式不对",
    ]
    for line in lines:
        m = LOG_RE.match(line)
        if m:
            d = m.groupdict()
            print(f"     {d['date']} {d['time']} [{d['level']:<7}] {d['msg']}")
        else:
            print(f"     （无法解析）{line}")
    print()

    print("  -- 贪婪 vs 非贪婪 --")
    for pattern in (r"<.*>", r"<.*?>", r"<.+?>"):
        got = re.match(pattern, "<a><b>")
        print(f"     re.match({pattern!r}, '<a><b>')  -> {got.group() if got else None}")
    print("     贪婪是默认：* + ? {n,m} 都尽可能多。加 ? 变成尽可能少。")
    print(f"     注意贪婪会为了整体匹配成功而回溯：")
    print(f"        re.match(r'<.*>', '<a> <b>').group() -> "
          f"{re.match(r'<.*>', '<a> <b>').group()!r}")
    print()

    print("  -- sub / split --")
    print(f"     re.sub(r'\\d+', '#', 'a1b22c333')        -> "
          f"{re.sub(r'\d+', '#', 'a1b22c333')!r}")
    print(f"     re.sub(r'\\d+', '#', 'a1b22c333', count=1) -> "
          f"{re.sub(r'\d+', '#', 'a1b22c333', count=1)!r}")
    print(f"     re.sub(r'(\\w+)@(\\w+)', r'\\2@\\1', 'a@b')  -> "
          f"{re.sub(r'(\w+)@(\w+)', r'\2@\1', 'a@b')!r}   <- 反向引用")
    print(f"     用函数做替换（结果里含反斜杠时更安全）：")
    print(f"        re.sub(r'\\d+', lambda m: str(int(m.group()) * 2), 'a1b2') -> "
          f"{re.sub(r'\d+', lambda m: str(int(m.group()) * 2), 'a1b2')!r}")
    print(f"     re.split(r'[,;]\\s*', 'a, b;c')          -> "
          f"{re.split(r'[,;]\s*', 'a, b;c')!r}")
    print()

    print("  -- re.compile：循环里必须预编译 --")
    import timeit

    sample = "2024-03-01 12:00:05 INFO 处理任务 42"
    pat = re.compile(r"(\d{4})-(\d{2})-(\d{2})")

    t_uncompiled = timeit.timeit(lambda: re.match(r"(\d{4})-(\d{2})-(\d{2})", sample),
                                 number=20000)
    t_compiled = timeit.timeit(lambda: pat.match(sample), number=20000)
    print(f"     20000 次匹配：")
    print(f"        每次传模式字符串 re.match(...) : {t_uncompiled:.4f} 秒")
    print(f"        预编译 pat.match(...)          : {t_compiled:.4f} 秒")
    print("     ^ re 模块内部有 512 个模式的缓存，所以差距不算夸张，")
    print("       但显式 compile 的真正价值是**给正则起个名字**。")
    print()

    print("  -- ReDoS：嵌套量词会指数回溯 --")
    evil = re.compile(r"(a+)+b")
    for n in (6, 10, 14, 18):
        elapsed = timeit.timeit(lambda n=n: evil.match("a" * n), number=1)
        print(f"     长度 {n:>2} 的 'aaa...' -> {elapsed:.4f} 秒")
    print("     ^ 长度每 +4 时间翻几倍。真实项目里解析用户输入的正则")
    print("       如果有嵌套量词，就是一个 DoS 攻击面（ReDoS）。")
    print("       防御：避免 (x+)+、用非捕获分组、能 split 就别用正则、先限长。")


# ======================================================================
# 7.9 datetime
# ======================================================================
def demo_datetime() -> None:
    section("7.9 datetime：naive vs aware")

    from datetime import date, datetime, time, timedelta, timezone

    print("  -- 四个类型 --")
    print(f"     date(2024, 3, 1)                   = {date(2024, 3, 1)}")
    print(f"     time(12, 30, 45)                   = {time(12, 30, 45)}")
    print(f"     datetime(2024, 3, 1, 12, 30, 45)   = {datetime(2024, 3, 1, 12, 30, 45)}")
    print(f"     timedelta(days=1, hours=2)         = {timedelta(days=1, hours=2)}")
    print()

    print("  -- naive vs aware --")
    naive = datetime(2024, 3, 1, 12, 0)
    aware = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)
    print(f"     naive = {naive}      tzinfo = {naive.tzinfo}")
    print(f"     aware = {aware}  tzinfo = {aware.tzinfo}")
    print(f"     aware.utcoffset() = {aware.utcoffset()}")
    print()

    print("  -- naive 和 aware 不能相减（这是好事）--")
    try:
        naive - aware
    except TypeError as exc:
        print(f"     naive - aware -> TypeError: {exc}")
    print("     ^ Python 逼你说清「这两个时间是不是同一个参照系」，")
    print("       而不是给你一个静默错误的结果。")
    print()

    print("  -- 跨时区换算 --")
    CST = timezone(timedelta(hours=8))
    utc_now = datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc)
    beijing = utc_now.astimezone(CST)
    new_york = utc_now.astimezone(timezone(timedelta(hours=-5)))
    print(f"     UTC      : {utc_now.isoformat()}   {utc_now.tzname()}")
    print(f"     北京     : {beijing.isoformat()}   {beijing.tzname()}")
    print(f"     纽约     : {new_york.isoformat()}   {new_york.tzname()}")
    print(f"     它们相等吗？ utc_now == beijing -> {utc_now == beijing}"
          f"   <- 同一时刻，aware 比较的是绝对时间")
    print()

    print("     对比 naive 版本（同一个物理时刻，字面数字却不一样）：")
    n1 = datetime(2024, 3, 1, 12, 0)
    n2 = datetime(2024, 3, 1, 20, 0)
    print(f"        {n1} == {n2} -> {n1 == n2}   <- 看起来不等，实际上是同一时刻")
    print()

    print("  -- timestamp 的行为取决于 aware 还是 naive --")
    print(f"     aware.timestamp()        = {utc_now.timestamp()}")
    print(f"     naive.timestamp()        = {naive.timestamp()}"
          f"   <- 按**本地时区**解释，换台机器就变")
    print(f"     fromtimestamp(0, tz=utc) = {datetime.fromtimestamp(0, tz=timezone.utc).isoformat()}")
    print(f"     fromtimestamp(0)         = {datetime.fromtimestamp(0)}"
          f"   <- 本地时区，同样是机器相关")
    print()

    print("  -- strftime / strptime --")
    dt = datetime(2024, 3, 1, 12, 30, 45, tzinfo=timezone.utc)
    print(f"     strftime('%Y-%m-%d %H:%M:%S')     -> {dt.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"     strftime('%Y-%m-%dT%H:%M:%S%z')   -> {dt.strftime('%Y-%m-%dT%H:%M:%S%z')}")
    print(f"     strftime('%Y年%m月%d日 %A')        -> {dt.strftime('%Y年%m月%d日 %A')}")
    print(f"     isoformat()                       -> {dt.isoformat()}   <- 首选")
    print(f"     strptime(...)                     -> "
          f"{datetime.strptime('2024-03-01T12:30:45+0000', '%Y-%m-%dT%H:%M:%S%z')}")
    print()

    print("     注意 %A / %B 是**英文**的，因为 Python 默认不调用 C 的 setlocale，")
    print("     想让它们是中文得自己调 locale.setlocale(locale.LC_TIME, 'zh_CN.UTF-8')，")
    print("     但那样代码就依赖运行环境的 locale 了 —— 所以展示层用中文自己映射更稳。")
    print()

    print("     往返一致性（注意微秒）：")
    with_us = dt.replace(microsecond=123456)
    back = datetime.strptime(with_us.strftime("%Y-%m-%dT%H:%M:%S%z"),
                             "%Y-%m-%dT%H:%M:%S%z")
    print(f"        原值              = {with_us.isoformat()}")
    print(f"        strptime 解析回来 = {back.isoformat()}")
    print(f"        相等吗？ {with_us == back}   <- 微秒丢了（格式里没有 %f）")
    print(f"        用 fromisoformat 解析就无损："
          f" {datetime.fromisoformat(with_us.isoformat()) == with_us}")
    print("     ^ 自己拼格式字符串很容易丢精度/丢时区，能用 ISO 格式就别自定义格式。")
    print()

    print("  -- strptime 很慢，大量解析用 fromisoformat --")
    import timeit

    stamp = "2024-03-01T12:30:45+00:00"
    t_strp = timeit.timeit(
        lambda: datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%S%z"), number=5000)
    t_iso = timeit.timeit(lambda: datetime.fromisoformat(stamp), number=5000)
    print(f"     5000 次解析：")
    print(f"        strptime      : {t_strp:.4f} 秒")
    print(f"        fromisoformat : {t_iso:.4f} 秒")
    print(f"        快了约 {t_strp / t_iso:.1f} 倍（fromisoformat 是 C 实现的）")
    print()

    print("  -- timedelta 运算 --")
    d1, d2 = date(2024, 3, 1), date(2024, 3, 10)
    print(f"     (date(2024,3,10) - date(2024,3,1)).days = {(d2 - d1).days}")
    print(f"     (d2 - d1).total_seconds()               = {(d2 - d1).total_seconds()}")
    print(f"     dt + timedelta(days=1)                  = {(dt + timedelta(days=1)).isoformat()}")
    print(f"     timedelta(days=30, hours=6) / timedelta(days=1) = "
          f"{timedelta(days=30, hours=6) / timedelta(days=1)}")
    print()

    print("  -- 推荐做法：内部一律存 aware UTC，展示时才转本地 --")
    print("     now_utc()  -> datetime.now(timezone.utc)")
    print("     to_local() -> dt.astimezone(CST)")
    print("     to_iso()   -> dt.isoformat()")
    print()
    print("     注意 timezone(timedelta(hours=8)) 是**固定偏移**，")
    print("     要处理历史时区规则（比如中国 1986-1991 实行过夏令时）")
    print("     得用 zoneinfo.ZoneInfo('Asia/Shanghai')。")


# ======================================================================
# 7.10 collections + os / sys / subprocess
# ======================================================================
def demo_collections_os_sys() -> None:
    section("7.10 collections 补充 + os / sys / subprocess")

    from collections import Counter, defaultdict, deque

    print("  -- Counter --")
    words = Counter("abracadabra")
    print(f"     Counter('abracadabra').most_common(3) = {words.most_common(3)}")
    print(f"     .total()                              = {words.total()}")
    print(f"     words - Counter('ab')                 = {words - Counter('ab')}")
    print()

    print("  -- defaultdict：分组的标准工具 --")
    records = [("张三", "研发"), ("李四", "市场"), ("王五", "研发")]
    groups: defaultdict[str, list[str]] = defaultdict(list)
    for name, dept in records:
        groups[dept].append(name)          # 不用先判键是否存在
    print(f"     {dict(groups)}")
    print(f"     注意：访问不存在的键会**创建**它")
    before = len(groups)
    groups["不存在的部门"]                  # 看起来只是读一下
    print(f"        len(groups) 从 {before} 变成 {len(groups)}   <- 被插入了空列表")
    print(f"     只想读不想插，用 groups.get('x', []) 或普通 dict")
    print()

    print("  -- deque：两端 O(1) + maxlen 实现「最近 N 条」--")
    recent: deque[int] = deque(maxlen=5)
    for i in range(10):
        recent.append(i)                   # 满了自动从左边挤掉
    print(f"     deque(maxlen=5) 追加 0..9 -> {list(recent)}")
    print(f"     deque 也可以当栈（append/pop）或队列（append/popleft）")
    print()

    print("  -- os：环境与进程 --")
    import os

    print(f"     os.name          = {os.name!r}")
    print(f"     os.linesep       = {os.linesep!r}")
    print(f"     os.sep           = {os.sep!r}")
    print(f"     os.getpid()      = {os.getpid()}")
    print(f"     os.cpu_count()   = {os.cpu_count()}")
    print(f"     'PATH' in os.environ -> {'PATH' in os.environ}")
    print(f"     os.environ.get('几乎肯定不存在的变量', '默认值') = "
          f"{os.environ.get('几乎肯定不存在的变量', '默认值')!r}")
    print("     ^ 读环境变量一律用 .get(名字, 默认值)，直接 [] 会 KeyError。")
    print()

    print("  -- sys：解释器相关 --")
    print(f"     sys.platform        = {sys.platform!r}")
    print(f"     sys.version_info    = {tuple(sys.version_info)}")
    print(f"     sys.executable      = {sys.executable}")
    print(f"     sys.getrecursionlimit() = {sys.getrecursionlimit()}")
    print(f"     sys.maxsize         = {sys.maxsize}")
    print(f"     sys.argv            = {sys.argv}")
    print("     ^ 调外部程序时用 sys.executable，不要硬编码 'python'，")
    print("       否则虚拟环境里会跑到另一个解释器上去。")
    print()

    print("  -- subprocess：调用外部程序 --")
    import subprocess

    print("     1) 参数传列表，不要用 shell=True")
    print("        subprocess.run(f'ls {user_input}', shell=True)  <- 命令注入漏洞")
    print("        subprocess.run(['ls', user_input])              <- 安全")
    print()
    print("     2) 实测跑一个子进程：")
    result = subprocess.run(
        [sys.executable, "-c", "import sys; print('子进程 Python', sys.version_info[:2])"],
        capture_output=True,
        text=True,
        encoding="utf-8",       # Windows 上不写会按 GBK 解码
        timeout=30,
        check=False,
    )
    print(f"        returncode = {result.returncode}")
    print(f"        stdout     = {result.stdout.strip()!r}")
    print(f"        stderr     = {result.stderr.strip()!r}")
    print()
    print("     3) 失败要检查 returncode（或 check=True 让它抛异常）：")
    failed = subprocess.run(
        [sys.executable, "-c", "import sys; sys.stderr.write('出错了'); sys.exit(3)"],
        capture_output=True, text=True, encoding="utf-8", timeout=30, check=False,
    )
    print(f"        returncode = {failed.returncode}   stderr = {failed.stderr.strip()!r}")
    if failed.returncode != 0:
        print("        ^ 非零退出码代表失败。静默忽略它 = 「脚本跑完了但什么都没做」。")
    print()
    print("     4) 超时保护：")
    try:
        subprocess.run([sys.executable, "-c", "import time; time.sleep(10)"],
                       capture_output=True, timeout=1, check=False)
    except subprocess.TimeoutExpired:
        print("        超时 -> subprocess.TimeoutExpired（没有 timeout= 的话你的程序会一起卡住）")


# ======================================================================
def main() -> None:
    demo_annotations()
    demo_typing_basics()
    demo_protocol()
    demo_mypy_note()
    demo_dataclasses()
    demo_logging()
    demo_argparse()
    demo_re()
    demo_datetime()
    demo_collections_os_sys()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
