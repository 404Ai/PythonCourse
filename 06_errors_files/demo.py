"""
模块 06 · 异常与文件 IO —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. **猜一下这段代码会输出什么**，尤其是 demo_order() 那一节
    3. 再跑，看是否和你想的一样

本文件所有文件操作都在 tempfile.TemporaryDirectory() 里完成，
运行结束后不会在项目目录留下任何残留文件。
"""

from __future__ import annotations

import csv
import json
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

# 把课程根目录加进模块搜索路径，方便以后 import 根目录下的东西
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# 6.1 异常层次结构
# ======================================================================
def demo_hierarchy() -> None:
    section("6.1 异常层次：为什么不要捕获 BaseException")

    print("  BaseException 的直接子类：")
    for cls in BaseException.__subclasses__():
        print(f"     {cls.__module__}.{cls.__name__}")
    print()

    print("  Exception 的直接子类（部分）：")
    names = [c.__name__ for c in Exception.__subclasses__()]
    for i in range(0, len(names), 4):
        print("     " + "  ".join(f"{n:<24}" for n in names[i:i + 4]))
    print()

    print("  -- 关键：KeyboardInterrupt / SystemExit 不是 Exception 的子类 --")
    print(f"     issubclass(KeyboardInterrupt, Exception)     -> {issubclass(KeyboardInterrupt, Exception)}")
    print(f"     issubclass(KeyboardInterrupt, BaseException) -> {issubclass(KeyboardInterrupt, BaseException)}")
    print(f"     issubclass(SystemExit, Exception)            -> {issubclass(SystemExit, Exception)}")
    print(f"     issubclass(OSError, Exception)               -> {issubclass(OSError, Exception)}")
    print()

    print("  -- 演示：except Exception 抓不住 KeyboardInterrupt --")

    def try_catch(exc_type: type[BaseException], handler: type[BaseException]) -> str:
        try:
            try:
                raise exc_type("模拟")
            except handler:
                return f"被 {handler.__name__} 抓住了"
        except BaseException as escaped:  # noqa: BLE001 - 这里就是要观察「逃逸」
            return f"逃逸了（{type(escaped).__name__}）"

    for exc_type, handler in [
        (ValueError, Exception),
        (KeyboardInterrupt, Exception),          # 抓不住！
        (KeyboardInterrupt, BaseException),      # 抓得住
        (SystemExit, Exception),                 # 抓不住！
    ]:
        print(f"     raise {exc_type.__name__:<18} except {handler.__name__:<14} -> "
              f"{try_catch(exc_type, handler)}")

    print()
    print("  结论：except Exception 天然放过 Ctrl+C 和 sys.exit，这正是你要的。")
    print("        except BaseException 会把它们一起吞掉，用户按 Ctrl+C 就停不下来。")


# ======================================================================
# 6.2 try / except / else / finally 的执行顺序
# ======================================================================
def demo_order() -> None:
    section("6.2 try / except / else / finally 的精确执行顺序")

    trace: list[str] = []

    def reset():
        trace.clear()

    def show(label: str) -> None:
        print(f"     {label:<28} 执行顺序: {' -> '.join(trace)}")

    def case(flag: bool) -> None:
        try:
            trace.append("try")
            if flag:
                raise ValueError("出错了")
        except ValueError:
            trace.append("except")
        else:
            trace.append("else")
        finally:
            trace.append("finally")

    print("  -- 正常路径：try -> else -> finally --")
    reset()
    case(False)
    show("没有异常")

    print("  -- 异常路径：try -> except -> finally（else 被跳过）--")
    reset()
    case(True)
    show("抛出 ValueError")

    print()

    print("  -- else 存在的唯一理由：它的异常不会被同一个 try 的 except 吃掉 --")

    def without_else():
        try:
            raise ValueError("来自 try 块")
        except ValueError as exc:
            return f"except 抓到了: {exc}"

    def with_else():
        try:
            pass                       # try 块本身没问题
        except ValueError:
            return "except 抓到了"
        else:
            raise ValueError("来自 else 块")   # 这个会往上抛

    print(f"     without_else() 返回: {without_else()!r}")

    def call_with_else():
        try:
            with_else()
        except ValueError as exc:
            return f"外层抓到: {exc}"

    print(f"     with_else() 的结果 : {call_with_else()!r}   <- 异常穿透了这一层")
    print()

    print("  -- return 和 finally 的交互：finally 在 return 之前跑 --")

    def return_with_finally():
        try:
            trace.append("try-return")
            return "返回值来自 try"
        finally:
            trace.append("finally")      # 注意：此时返回值已经算好了

    reset()
    result = return_with_finally()
    print(f"     返回值 = {result!r}")
    show("return 之前")

    print()

    print("  -- 危险：finally 里的 return 会静默覆盖 try 的 return --")
    print("     Python 3.13 起这会触发 SyntaxWarning，未来的版本会变成 SyntaxError。")
    print("     所以下面这段**不能直接写在源码里**（会污染本文件的编译），")
    print("     改用 exec 在运行时编译，让你看到它真实的行为：")

    bad_src = (
        "def f():\n"
        "    try:\n"
        "        return 1\n"
        "    finally:\n"
        "        return 2\n"
    )
    import warnings

    ns: dict = {}
    with warnings.catch_warnings():
        # 演示用，故意让警告静音，不然会刷屏
        warnings.simplefilter("ignore", SyntaxWarning)
        exec(compile(bad_src, "<finally 反例>", "exec"), ns)
    print(f"     exec 编译出的 f() 返回 -> {ns['f']()}   <- 不是 1！")
    print("     try 里算出来的返回值被 finally 的 return 直接丢弃，而且不报任何错。")
    print()

    print("  -- 同样危险：finally 里抛新异常会盖掉原始异常 --")

    def cleanup_fails():
        try:
            raise ValueError("原始错误")
        finally:
            raise RuntimeError("清理时又炸了")     # 原始异常被降级成 __context__

    try:
        cleanup_fails()
    except RuntimeError as exc:
        print(f"     调用方看到的是 {type(exc).__name__}: {exc}")
        print(f"     真正的根因被藏在 __context__ 里: "
              f"{type(exc.__context__).__name__}: {exc.__context__}")
    print("     这就是为什么 finally 里只该写「不会失败」的清理代码。")
    print()

    print("  -- finally 在异常传播路径上也一定执行 --")

    def propagates():
        try:
            try:
                trace.append("inner-try")
                raise ValueError("穿透")
            finally:
                trace.append("inner-finally")
        except ValueError:
            trace.append("outer-except")

    reset()
    propagates()
    show("异常穿透")


# ======================================================================
# 6.3 EAFP vs LBYL
# ======================================================================
def demo_eafp() -> None:
    section("6.3 EAFP vs LBYL，以及「异常不是免费的」")

    data = {"name": "张三", "age": "30"}

    print("  -- LBYL: Look Before You Leap（先检查，再动手）--")

    if "name" in data:
        name = data["name"]
    else:
        name = None
    print(f"     if 'name' in data: ...       -> {name!r}")

    print("  -- EAFP: Easier to Ask Forgiveness than Permission（先做，错了再处理）--")
    try:
        name = data["name"]
    except KeyError:
        name = None
    print(f"     try: data['name'] ...        -> {name!r}")

    print("  -- 但上面两种都不如第三种：容器自己提供的 API --")
    print(f"     data.get('name')             -> {data.get('name')!r}   一次哈希查找，零异常")

    print()

    print("  -- 什么时候必须用 EAFP：操作本身才是检查（没有 TOCTOU 窗口）--")

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "exists.txt"
        p.write_text("内容", encoding="utf-8")

        # LBYL 版本：检查和使用之间有一个窗口，另一个进程可能刚好删掉文件
        if p.exists():
            print(f"     LBYL: p.exists() -> {p.exists()}，然后 read_text()")

        # EAFP 版本：没有窗口
        try:
            text = p.read_text(encoding="utf-8")
            print(f"     EAFP: 直接读 -> {text!r}")
        except FileNotFoundError:
            print("     EAFP: 文件不在，走 except 分支")

        missing = Path(d) / "不存在.txt"
        try:
            missing.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            print(f"     读不存在的文件 -> FileNotFoundError: {exc.strerror}")

    print()

    print("  -- 异常的代价：失败率高的地方用异常做流程控制会明显变慢 --")

    import timeit

    dict_hit = {i: i for i in range(100)}

    def via_exception() -> int:
        try:
            return dict_hit[9999]
        except KeyError:
            return -1

    def via_get() -> int:
        return dict_hit.get(9999, -1)

    t_exc = timeit.timeit(via_exception, number=200_000)
    t_get = timeit.timeit(via_get, number=200_000)

    print(f"     每次都 miss，20 万次：")
    print(f"        try/except KeyError : {t_exc:.4f} 秒")
    print(f"        dict.get(..., -1)   : {t_get:.4f} 秒")
    print(f"        慢了约 {t_exc / t_get:.1f} 倍")
    print()
    print("     注意：这里 100% 都失败，是最坏情况。")
    print("     如果失败率只有 1%，EAFP 和 LBYL 的差距会小到测不出来。")
    print("     判据是「失败是不是常态」，不是「哪个更 Pythonic」。")


# ======================================================================
# 6.4 异常链
# ======================================================================
def demo_chain() -> None:
    section("6.4 异常链：__cause__ / __context__ / 裸 raise")

    print("  -- 隐式链：在 except 块里 raise，Python 自动设置 __context__ --")
    try:
        try:
            int("abc")
        except ValueError:
            raise RuntimeError("转换失败")
    except RuntimeError as exc:
        print(f"     __cause__   = {exc.__cause__!r}      （没有，因为没写 from）")
        print(f"     __context__ = {type(exc.__context__).__name__}: {exc.__context__}")
    print()

    print("  -- 显式链：raise ... from exc，两者都指向原始异常 --")
    try:
        try:
            int("abc")
        except ValueError as original:
            raise RuntimeError("转换失败") from original
    except RuntimeError as exc:
        print(f"     __cause__   = {type(exc.__cause__).__name__}: {exc.__cause__}")
        print(f"     __context__ = {type(exc.__context__).__name__}")
        print("     语义：『我因为这个错误才抛新错误』")
    print()

    print("  -- 断链：raise ... from None 把底层异常藏起来 --")
    try:
        try:
            int("abc")
        except ValueError:
            raise RuntimeError("对外只暴露这个") from None
    except RuntimeError as exc:
        print(f"     __cause__           = {exc.__cause__!r}")
        print(f"     __suppress_context__ = {exc.__suppress_context__}   <- traceback 不会显示原因了")
    print()

    print("  -- 裸 raise（重抛当前异常）vs raise exc（多出一帧）--")

    def reraise_bare() -> str:
        try:
            int("abc")
        except ValueError:
            raise                    # 正确：原始 traceback 完整保留

    def reraise_named() -> str:
        try:
            int("abc")
        except ValueError as exc:
            raise exc                # 错误：traceback 的起点变成这一行

    import traceback

    for fn, label in ((reraise_bare, "裸 raise "), (reraise_named, "raise exc")):
        try:
            fn()
        except ValueError as exc:
            frames = traceback.extract_tb(exc.__traceback__)
            print(f"     {label} -> traceback 有 {len(frames)} 帧")
            for fr in frames:
                print(f"        {Path(fr.filename).name}:{fr.lineno:<4} "
                      f"in {fr.name:<16} {fr.line}")
    print()
    print("     裸 raise 只有 2 帧，栈底那帧直接指向真正出错的 int('abc')。")
    print("     raise exc 多出 1 帧，栈底变成了 raise 语句本身。")
    print("     异常没有被重置（__traceback__ 会累积），但多出来的这帧会")
    print("     让「最深一帧就是出错点」这个直觉失效，排查时白白多跳一次。")
    print("     规则：在 except 里重新抛出，一律写裸 raise。")


# ======================================================================
# 6.5 自定义异常
# ======================================================================
def demo_custom() -> None:
    section("6.5 自定义异常：层次设计与结构化数据")

    class AppError(Exception):
        """本应用所有异常的根。调用方靠它区分「业务的错」和「Python 的错」。"""

    class ValidationError(AppError):
        """校验失败。携带结构化信息，方便调用方精确处理。"""

        def __init__(self, field: str, message: str) -> None:
            super().__init__(f"字段 {field!r}: {message}")   # 不写这句 str(exc) 会是空串
            self.field = field
            self.message = message

    class RangeError(ValidationError):
        """值超出范围。继承自 ValidationError，所以 except ValidationError 也能抓到它。"""

        def __init__(self, field: str, value, low, high) -> None:
            super().__init__(field, f"必须在 [{low}, {high}] 之间，收到 {value!r}")
            self.value, self.low, self.high = value, low, high

    def validate_age(record: dict) -> int:
        if "age" not in record:
            raise ValidationError("age", "缺少必填字段")
        age = record["age"]
        if not isinstance(age, int) or isinstance(age, bool):
            raise ValidationError("age", f"必须是 int，收到 {type(age).__name__}")
        if not 0 <= age <= 150:
            raise RangeError("age", age, 0, 150)
        return age

    def report(record: dict) -> str:
        """调用方：按粒度不同，可以选择不同的 except。"""
        try:
            age = validate_age(record)
        except RangeError as exc:
            # 最具体的一层：能拿到结构化的上/下限
            return f"RangeError  -> {exc}   (low={exc.low}, high={exc.high})"
        except ValidationError as exc:
            # 中间层：任何校验失败都能兜住，还能拿到字段名
            return f"ValidationError -> {exc}   (field={exc.field!r})"
        except AppError as exc:
            # 根异常：理论上到不了这里，但它是和外界的契约
            return f"AppError -> {exc}"
        return f"通过，age = {age}"

    for rec in (
        {"age": 30},
        {"age": True},          # bool 是 int 子类，必须单独拦住
        {"age": "30"},
        {"age": 200},
        {"name": "张三"},        # 缺字段
    ):
        print(f"     {str(rec):<22} {report(rec)}")

    print()
    print("  -- 异常层次的意义：except 的粒度和 raise 的粒度匹配 --")
    print(f"     RangeError 是 ValidationError 的子类 -> "
          f"{issubclass(RangeError, ValidationError)}")
    print(f"     ValidationError 是 AppError 的子类   -> "
          f"{issubclass(ValidationError, AppError)}")
    print(f"     AppError 是 Exception 的子类         -> "
          f"{issubclass(AppError, Exception)}")
    print(f"     AppError 是 BaseException 的直接子类？ -> "
          f"{BaseException in AppError.__bases__}")
    print()
    print("     自定义异常必须继承 Exception，不能继承 BaseException。")
    print("     否则别人写 except Exception 兜底时抓不到你，程序会被你直接干掉。")


# ======================================================================
# 6.6 反模式
# ======================================================================
def demo_antipatterns() -> None:
    section("6.6 反模式：为什么 except Exception: pass 是灾难")

    print("  -- 演示：一个 bug 被 except: pass 吃掉之后的样子 --")

    def buggy_parse(text: str) -> int:
        # 假设这里有个拼写错误，本该是 int(text)
        return int(texxt)  # noqa: F821  —— 故意的，演示用

    def swallow_all(text: str) -> str:
        try:
            return f"解析结果 {buggy_parse(text)}"
        except Exception:
            pass                      # 灾难：什么都没留下
        return "解析失败"

    def log_and_narrow(text: str) -> str:
        try:
            return f"解析结果 {buggy_parse(text)}"
        except ValueError as exc:
            # 只捕 ValueError（能预期的那些），并且留痕
            print(f"       [日志] ValueError: {exc}")
        except Exception as exc:      # noqa: BLE001 - 兜底，但一定要记日志 + 重抛或降级
            print(f"       [日志] 未预期的 {type(exc).__name__}: {exc}")
            print("       [日志] 这是 bug，不是用户输入问题，应该报警")
        return "解析失败"

    print("     调用 swallow_all('42'):")
    print(f"       -> {swallow_all('42')!r}")
    print("       程序看起来「正常工作」，但你永远不知道 NameError 发生过。")
    print()
    print("    调用 log_and_narrow('42'):")
    print(f"       -> {log_and_narrow('42')!r}")
    print("       至少日志里有痕迹，你能在 5 分钟内定位到拼写错误。")
    print()

    print("  -- 演示：裸 except 吞掉 KeyboardInterrupt --")

    def loop_with_bare_except() -> str:
        acks = []
        for i in range(5):
            try:
                if i == 2:
                    # 模拟用户按下 Ctrl+C
                    raise KeyboardInterrupt
                acks.append(f"第{i}轮正常")
            except:                    # noqa: E722 - 故意的反例
                acks.append(f"第{i}轮被吃掉了")
        return " | ".join(acks)

    print(f"     裸 except:  {loop_with_bare_except()}")

    def loop_with_exception() -> str:
        acks = []
        for i in range(5):
            try:
                if i == 2:
                    raise KeyboardInterrupt
                acks.append(f"第{i}轮正常")
            except Exception as exc:   # noqa: BLE001
                acks.append(f"第{i}轮被 {type(exc).__name__} 吃掉")
        return " | ".join(acks)

    try:
        print(f"     except Exception: {loop_with_exception()}")
    except KeyboardInterrupt:
        print("     except Exception: KeyboardInterrupt 正常穿透出来了 -> 循环能停下来了")
    print()

    print("  -- 演示：把精确错误变成模糊错误 --")
    try:
        data = json.loads("{不是合法 json}")
    except json.JSONDecodeError as exc:
        print(f"     直接让 json 抛 -> JSONDecodeError: {exc.msg} (line {exc.lineno} col {exc.colno})")
    print("     如果你把这个异常转成 data = {}，后面访问 data['key'] 才炸，")
    print("     报错位置离真正的错误已经隔了几十行。")


# ======================================================================
# 6.7 pathlib
# ======================================================================
def demo_pathlib() -> None:
    section("6.7 pathlib.Path 全面替代 os.path")

    p = Path("data") / "2024" / "report.tar.gz"
    print("  -- 拼接与拆解 --")
    print(f"     Path('data') / '2024' / 'report.tar.gz' -> {p}")
    print(f"     .name       = {p.name!r}      文件名（含全部后缀）")
    print(f"     .stem       = {p.stem!r}")
    print(f"     .suffix     = {p.suffix!r}        最后一个后缀")
    print(f"     .suffixes   = {p.suffixes}")
    print(f"     .parent     = {p.parent}")
    print(f"     .parts      = {p.parts}")
    print(f"     .with_suffix('.csv') = {p.with_suffix('.csv')}   <- 只换最后一个后缀！")
    print(f"     .with_stem('new')    = {p.with_stem('new')}")
    print()

    print("  -- Path 能直接传给 open() / os.path / shutil，不用 str() --")

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        print(f"     临时目录: {root}")
        print()

        print("  -- mkdir(parents=True, exist_ok=True) 是幂等的 --")
        (root / "a" / "b" / "c").mkdir(parents=True, exist_ok=True)
        (root / "a" / "b" / "c").mkdir(parents=True, exist_ok=True)   # 再调一次也不报错
        print(f"     (root/'a'/'b'/'c').mkdir(parents=True, exist_ok=True) 调两次都没报错")
        print()

        print("  -- 造几个文件，然后遍历 --")
        files = {
            "readme.md": "# 标题\n",
            "main.py": "print('hello')\n",
            "util.py": "def f():\n    return 1\n",
            "data.csv": "a,b\n1,2\n",
        }
        for name, content in files.items():
            (root / name).write_text(content, encoding="utf-8")
        # 再放一个子目录里的文件，用来演示 rglob
        (root / "sub").mkdir(exist_ok=True)
        (root / "sub" / "deep.py").write_text("x = 1\n", encoding="utf-8")

        print("     iterdir() 直接子项（文件 + 目录都算）：")
        for child in sorted(root.iterdir()):
            kind = "目录" if child.is_dir() else "文件"
            print(f"        [{kind}] {child.name}")
        print()

        print("     glob('*.py') 只看当前层：")
        for f in sorted(root.glob("*.py")):
            print(f"        {f.name}")
        print()

        print("     rglob('*.py') 递归所有子目录：")
        for f in sorted(root.rglob("*.py")):
            print(f"        {f.relative_to(root)}")
        print()

        print("     glob('**/*.py') 等价于 rglob('*.py')：")
        print(f"        结果相同 -> "
              f"{sorted(f for f in root.glob('**/*.py')) == sorted(root.rglob('*.py'))}")
        print()

        print("  -- 筛选扩展名 + 统计文件大小 --")
        py_files = sorted(root.rglob("*.py"))
        total = sum(f.stat().st_size for f in py_files)
        print(f"        共 {len(py_files)} 个 .py 文件，合计 {total} 字节")
        for f in py_files:
            print(f"        {str(f.relative_to(root)):<16} {f.stat().st_size:>4} 字节")
        print()

        print("  -- 筛选扩展名的两种写法 --")
        print(f"        [f for f in root.iterdir() if f.suffix == '.py']  -> "
              f"{[f.name for f in sorted(root.iterdir()) if f.suffix == '.py']}")
        print(f"        直接 root.glob('*.py')                            -> "
              f"{[f.name for f in sorted(root.glob('*.py'))]}")
        print("        两者等价，但 glob 是在文件系统层面过滤，通常更快也更清晰。")
        print()

        print("  -- resolve() / relative_to() / exists() --")
        target = root / "main.py"
        print(f"     (root/'main.py').resolve()          = {target.resolve()}")
        print(f"     (root/'main.py').relative_to(root)  = {target.relative_to(root)}")
        print(f"     (root/'nope').exists()              = {(root / 'nope').exists()}")
        print(f"     (root/'nope').is_file()             = {(root / 'nope').is_file()}")
        print()

        print("  -- 用 with_suffix 生成配对文件 --")
        for src in sorted(root.glob("*.csv")):
            print(f"     {src.name} 的 .json 版本会是 {src.with_suffix('.json').name}")


# ======================================================================
# 6.8 编码
# ======================================================================
def demo_encoding() -> None:
    section("6.8 文本编码：为什么 encoding='utf-8' 必须显式写")

    import locale

    print("  -- 这台机器上的默认编码 --")
    print(f"     locale.getencoding()        = {locale.getencoding()!r}   <- open() 不写 encoding 时用它")
    print(f"     sys.getdefaultencoding()    = {sys.getdefaultencoding()!r}   <- str <-> bytes 隐式转换用的，不是文件编码")
    print(f"     sys.getfilesystemencoding() = {sys.getfilesystemencoding()!r}")
    print(f"     UTF-8 模式开启？            = {bool(sys.flags.utf8_mode)}")
    print()
    print("     注意区别：sys.getdefaultencoding() 永远是 utf-8，")
    print("     但**文件 IO 的默认编码是 locale 编码**，简体中文 Windows 上是 cp936（GBK）。")
    print()

    chinese = "中文内容，含标点：测试"

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        print("  -- 用 UTF-8 写，用默认编码读（Windows 上就是踩坑现场）--")
        u8 = root / "utf8.txt"
        u8.write_text(chinese, encoding="utf-8")
        print(f"     写入 bytes: {u8.read_bytes()!r}")
        print(f"     字节数    : {len(u8.read_bytes())}")

        try:
            got = u8.read_text()          # 故意不写 encoding
            if got == chinese:
                print(f"     不写 encoding 读回 = {got!r}")
                print("     （这台机器的 locale 就是 UTF-8，所以侥幸没出错——")
                print("       换个 GBK 的 Windows 或者 Docker 里的 C locale 就炸）")
            else:
                print(f"     不写 encoding 读回 = {got!r}   <- 乱码！")
        except UnicodeDecodeError as exc:
            print(f"     不写 encoding 读回 -> UnicodeDecodeError: {exc.reason}")
            print(f"        出错位置: byte {exc.start}，这段字节是 {exc.object[exc.start:exc.end]!r}")
            print("        这就是跨平台 bug 的典型现场：本机没事，服务器上炸。")

        print()
        print("     写 encoding='utf-8' 读回 -> ", end="")
        print(f"{u8.read_text(encoding='utf-8')!r}")
        print()

        print("  -- 写的时候不指定编码，会写出 GBK 字节 --")
        gbk = root / "default.txt"
        gbk.write_text("中文", encoding="gbk")
        print(f"     encoding='gbk' 写 '中文'      -> {gbk.read_bytes()!r}")
        (root / "u8b.txt").write_text("中文", encoding="utf-8")
        print(f"     encoding='utf-8' 写 '中文'    -> {(root / 'u8b.txt').read_bytes()!r}")
        print("     GBK 用 2 字节存一个汉字，UTF-8 用 3 字节，字节序列完全不同。")
        print()

        print("  -- GBK 表示不了的字符 --")
        # 注意：这里**故意不把那个 emoji 本身打印出来**。
        # 如果这台机器的控制台是 GBK 编码，print 它会让整个程序
        # UnicodeEncodeError 崩掉 —— 而这段 demo 恰恰是在讲这件事。
        # 所以只用码位（U+XXXX）指代它。
        cases = (
            ("中", "汉字", "U+4E2D"),
            ("é", "带音标的拉丁字母", "U+00E9"),
            ("\U0001F40D", "emoji（蛇）", "U+1F40D"),
            ("Ω", "希腊字母 Omega", "U+03A9"),
        )
        for ch, name, code in cases:
            try:
                ch.encode("gbk")
                gbk_ok = "可编码"
            except UnicodeEncodeError:
                gbk_ok = "UnicodeEncodeError"
            try:
                ch.encode("utf-8")
                u8_ok = "可编码"
            except UnicodeEncodeError:
                u8_ok = "UnicodeEncodeError"
            print(f"     {name:<16}({code}) GBK: {gbk_ok:<20} UTF-8: {u8_ok}")
        print("     ^ emoji 在 GBK 里根本不存在，UTF-8 里则要 4 个字节。")
        print("       这也是为什么「编码」「解码」这两个动作必须成对出现：")
        print("       用 UTF-8 写、用 GBK 读，中文就变成一串乱码。")

        print()
        print("  -- 二进制模式：不做任何编码转换 --")
        png = root / "fake.png"
        png.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 4)
        with open(png, "rb") as f:
            magic = f.read(8)
        print(f"     文件头 8 字节 = {magic!r}")
        print(f"     是 PNG 吗？  = {magic == b'\x89PNG\r\n\x1a\n'}")
        print()
        print("     二进制模式下读出来是 bytes，不经过任何编码转换。")
        print("     想在二进制模式里指定 encoding？会抛 ValueError —— ")
        try:
            open(png, "rb", encoding="utf-8")
        except ValueError as exc:
            print(f"        ValueError: {exc}")


# ======================================================================
# 6.9 newline 与 with / 大文件
# ======================================================================
def demo_newline_and_with() -> None:
    section("6.9 newline 参数、with 语句、大文件逐行迭代")

    print("  -- newline 的默认行为：读的时候把换行统一成 \\n，写的时候把 \\n 翻成 os.linesep --")

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "crlf.txt"

        # 直接写原始字节，绕过一切翻译
        p.write_bytes("行1\r\n行2\r\n".encode("utf-8"))
        print(f"     磁盘上的原始字节: {p.read_bytes()!r}")

        with open(p, encoding="utf-8") as f:
            print(f"     newline 默认（universal）读: {f.read()!r}")
        with open(p, encoding="utf-8", newline="") as f:
            print(f"     newline='' 读:              {f.read()!r}")
        print()

        print("  -- 写的时候的翻译 --")
        w1 = root / "w_default.txt"
        with open(w1, "w", encoding="utf-8") as f:
            f.write("a\nb\n")
        print(f"     默认写 'a\\nb\\n'            -> {w1.read_bytes()!r}")

        w2 = root / "w_empty.txt"
        with open(w2, "w", encoding="utf-8", newline="") as f:
            f.write("a\nb\n")
        print(f"     newline='' 写 'a\\nb\\n'     -> {w2.read_bytes()!r}")
        print("     ^ 一个变成 \\r\\n，一个保持 \\n。跨平台交换文件时这个差别会要命。")
        print()

        print("  -- 为什么 csv 必须 newline='' --")
        rows = [{"name": "张三", "score": "95"}, {"name": "李四", "score": "88"}]

        bad = root / "bad.csv"
        with open(bad, "w", encoding="utf-8") as f:      # 忘了 newline=""
            writer = csv.DictWriter(f, fieldnames=["name", "score"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"     不加 newline='' -> {bad.read_bytes()!r}")

        good = root / "good.csv"
        with open(good, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "score"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"     加 newline=''   -> {good.read_bytes()!r}")
        print("     csv 模块自己写 \\r\\n，文本层的翻译又加了一层 \\r，变成 \\r\\r\\n。")
        print()

        print("  -- with 保证文件被关闭（Windows 上不关就删不掉）--")
        f = open(root / "held.txt", "w", encoding="utf-8")
        f.write("x")
        try:
            (root / "held.txt").unlink()
            print("       未关闭文件时 unlink 成功（Linux 行为）")
        except PermissionError as exc:
            print(f"       未关闭文件时 unlink -> PermissionError: {exc.strerror}")
            print("       ^ 这就是 Windows 上「文件明明没用却删不掉」的原因")
        f.close()                                        # 关了之后才能删
        (root / "held.txt").unlink()
        print("       close() 之后再 unlink -> 成功")
        print()

        print("  -- 一次性开多个文件（3.10+ 括号写法）--")
        with (
            open(root / "src.txt", "w", encoding="utf-8") as fout,
        ):
            fout.write("hello\nworld\n")
        with (
            open(root / "src.txt", encoding="utf-8") as fin,
            open(root / "dst.txt", "w", encoding="utf-8") as fout,
        ):
            for line in fin:
                fout.write(line.upper())
        print(f"     src: {(root / 'src.txt').read_text(encoding='utf-8')!r}")
        print(f"     dst: {(root / 'dst.txt').read_text(encoding='utf-8')!r}")
        print()

        print("  -- 大文件必须逐行迭代：对比内存峰值 --")
        big = root / "big.log"
        with open(big, "w", encoding="utf-8") as f:
            for i in range(20000):
                f.write(f"2024-03-01 12:00:{i % 60:02d} INFO 处理任务 {i}\n")
        size = big.stat().st_size
        print(f"     造了一个 {size} 字节的日志文件（{size / 1024:.1f} KB）")

        import tracemalloc

        def by_readlines() -> int:
            with open(big, encoding="utf-8") as f:
                lines = f.readlines()
            return sum(1 for line in lines if "INFO" in line)

        def by_iteration() -> int:
            with open(big, encoding="utf-8") as f:
                return sum(1 for line in f if "INFO" in line)

        for fn, label in ((by_readlines, "readlines()"), (by_iteration, "for line in f")):
            tracemalloc.start()
            fn()
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            print(f"     {label:<16} 峰值内存 {peak / 1024:>8.1f} KB")
        print()
        print("     文件对象本身就是迭代器，内部有 8KB 缓冲区，")
        print("     每次 __next__ 从缓冲区切一行，缓冲用完才做一次系统调用。")
        print("     所以逐行迭代**既省内存，也不会更慢**。")
        print()

        print("  -- rstrip('\\n') vs strip() --")
        line = "    缩进不能丢\n"
        print(f"     line.strip()          -> {line.strip()!r}")
        print(f"     line.rstrip('\\n')     -> {line.rstrip(chr(10))!r}   <- 缩进保住了")


# ======================================================================
# 6.10 JSON 与 CSV
# ======================================================================
def demo_json_csv() -> None:
    section("6.10 JSON 与 CSV")

    print("  -- JSON: ensure_ascii / indent / default --")
    data = {"名称": "张三", "分数": [90, 85], "在读": True, "备注": None}

    print("     ensure_ascii=True （默认）:")
    print(f"        {json.dumps(data, ensure_ascii=True)[:70]}...")
    print("     ensure_ascii=False:")
    print(f"        {json.dumps(data, ensure_ascii=False)}")
    print()
    print("     两种都是合法 JSON，反序列化结果完全一样。")
    print("     但 ensure_ascii=True 中文变码点转义，文件没法直接读，体积还大好几倍。")
    print()

    print("     indent=2 的效果:")
    print(json.dumps({"a": 1, "b": {"c": [1, 2]}}, ensure_ascii=False, indent=2))
    print()

    class Point:
        def __init__(self, x: float, y: float) -> None:
            self.x, self.y = x, y

    print("     自定义对象直接 dumps 会 TypeError:")
    try:
        json.dumps(Point(1, 2))
    except TypeError as exc:
        print(f"        TypeError: {exc}")
    print("     用 default= 告诉它怎么转:")
    print(f"        json.dumps(Point(1, 2), default=lambda o: {{'x': o.x, 'y': o.y}})")
    print(f"        -> {json.dumps(Point(1, 2), default=lambda o: {'x': o.x, 'y': o.y})}")

    def json_default(obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return str(obj)              # 不要 float()，那会丢精度
        if isinstance(obj, Path):
            return str(obj)
        raise TypeError(f"不支持的类型: {type(obj).__name__}")

    mixed = {
        "时间": datetime(2024, 3, 1, 12, 0, tzinfo=timezone.utc),
        "金额": Decimal("19.99"),
        "路径": Path("a/b.txt"),
    }
    print(f"     通用 default 函数 -> {json.dumps(mixed, ensure_ascii=False, default=json_default)}")
    print()

    print("  -- JSON 的两个数据丢失点 --")
    t = (1, 2, 3)
    roundtrip = json.loads(json.dumps(t))
    print(f"     tuple (1,2,3) 往返后 -> {roundtrip!r}  type = {type(roundtrip).__name__}   <- tuple 变 list")
    d = {1: "a", 2: "b"}
    roundtrip_d = json.loads(json.dumps(d))
    print(f"     dict {{1:'a'}} 往返后 -> {roundtrip_d!r}   键变成字符串了")
    print("     JSON 的 object 键永远是 string，这是规范决定的。")
    print()

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)

        print("  -- 写 JSON 文件并读回 --")
        cfg = {"应用名": "示例", "版本": "1.0", "超时": 30, "标签": ["a", "b"]}
        jf = root / "cfg.json"
        with open(jf, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        print(f"     文件内容（{jf.stat().st_size} 字节）:")
        print("\n".join("        " + line for line in jf.read_text(encoding="utf-8").splitlines()))

        with open(jf, encoding="utf-8") as f:
            loaded = json.load(f)
        print(f"     读回: {loaded}")
        print(f"     往返一致？ {loaded == cfg}")
        print()

        print("  -- CSV: DictReader 的列全变成 str --")
        csv_path = root / "users.csv"
        csv_path.write_text(
            "name,age,city\n张三,30,北京\n李四,,上海\n",
            encoding="utf-8",
        )
        with open(csv_path, encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            print(f"     fieldnames = {reader.fieldnames}")
            for row in reader:
                age = row["age"]
                print(f"        {row}   age 的类型是 {type(age).__name__!r}，值是 {age!r}")
        print("     空单元格读出来是空字符串，不是 None，也不是 0。")
        print()

        print("  -- DictReader 的缺列 / 多列行为 --")

        ragged = root / "ragged.csv"
        ragged.write_text("a,b,c\n1,2,3\n4,5\n6,7,8,9\n", encoding="utf-8")

        for kwargs, label in (({}, "默认"), ({"restval": ""}, "restval=''")):
            print(f"     {label}:")
            with open(ragged, encoding="utf-8", newline="") as f:
                for row in csv.DictReader(f, **kwargs):
                    print(f"        {row}")
        print("     缺列填 restval（默认 None），多出来的列会被塞进 restkey（默认 None）的 list。")
        print()

        print("  -- 带类型转换和缺列处理的解析 --")

        def parse_users(path: Path) -> list[dict]:
            out = []
            with open(path, encoding="utf-8", newline="") as f:
                for lineno, row in enumerate(csv.DictReader(f, restval=""), start=2):
                    raw_age = (row.get("age") or "").strip()
                    try:
                        age = int(raw_age) if raw_age else None
                    except ValueError:
                        age = None
                    out.append({
                        "name": row.get("name", "").strip(),
                        "age": age,
                        "city": row.get("city", "").strip(),
                        "_line": lineno,
                    })
            return out

        for rec in parse_users(csv_path):
            print(f"        {rec}")
        print()

        print("  -- DictWriter --")
        out_csv = root / "out.csv"
        rows = [{"name": "张三", "age": 30}, {"name": "李四", "age": 25}]
        with open(out_csv, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["name", "age"])
            writer.writeheader()
            writer.writerow({"name": "王五", "age": 40})
            writer.writerows(rows)
        print(f"     磁盘字节: {out_csv.read_bytes()!r}")
        print(f"     读回: {out_csv.read_text(encoding='utf-8')!r}")
        print()

        print("  -- utf-8-sig：让 Excel 正确识别中文 --")
        excel = root / "for_excel.csv"
        with open(excel, "w", encoding="utf-8-sig", newline="") as f:
            csv.writer(f).writerow(["姓名", "分数"])
            csv.writer(f).writerow(["张三", 90])
        print(f"     前 3 字节 = {excel.read_bytes()[:3]!r}   <- BOM")
        print("     Excel 靠这个 BOM 才知道这是 UTF-8；")
        print("     反过来，用 utf-8-sig 去读一个普通 UTF-8 文件也没问题。")
        print()

        print("  -- 什么时候用哪个 --")
        print("     数据是「一张表」-> CSV（小、Excel 能开）")
        print("     数据是「一棵树」-> JSON（有类型、能嵌套）")
        print("     CSV 没有任何类型系统，全靠你自己转。")


# ======================================================================
# 6.11 tempfile / shutil
# ======================================================================
def demo_tempfile_shutil() -> None:
    section("6.11 tempfile / shutil 速查")

    print("  -- 系统临时目录 --")
    print(f"     tempfile.gettempdir() = {tempfile.gettempdir()}")
    print()

    print("  -- TemporaryDirectory：with 块结束自动递归删除 --")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d)
        (p / "sub").mkdir()
        (p / "sub" / "a.txt").write_text("内容", encoding="utf-8")
        (p / "b.txt").write_text("内容", encoding="utf-8")
        print(f"     目录存在？ {p.exists()}   里面的内容: "
              f"{sorted(str(x.relative_to(p)) for x in p.rglob('*'))}")
        created = p
    print(f"     出了 with 块之后，还存在吗？ {created.exists()}")
    print("     即使块内抛异常，它也会被删掉——这就是测试里该用它而不是用项目目录的原因。")
    print()

    print("  -- NamedTemporaryFile --")
    with tempfile.NamedTemporaryFile(
        mode="w+", suffix=".txt", encoding="utf-8", delete=True
    ) as f:
        f.write("临时内容")
        f.flush()                       # 不 flush 的话缓冲区里的内容还没落到磁盘
        print(f"     路径 = {f.name}")
        # 注意：Windows 上不能趁它开着的时候用路径再打开一次（PermissionError）。
        # 官方文档明确写了这个跨平台差异。要读就 seek(0) 再读同一个句柄。
        f.seek(0)
        print(f"     内容 = {f.read()!r}")
    print("     （出了 with 块文件已被删除，delete=True 是默认值）")
    print()

    print("  -- shutil 常用操作 --")
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        src = root / "src"
        src.mkdir()
        (src / "a.txt").write_text("aaa", encoding="utf-8")
        (src / "b.txt").write_text("bbb", encoding="utf-8")

        shutil.copy(src / "a.txt", root / "a_copy.txt")
        print(f"     copy      -> 存在？ {(root / 'a_copy.txt').exists()}")

        shutil.copy2(src / "a.txt", root / "a_copy2.txt")
        print(f"     copy2     -> 保留修改时间 "
              f"{(root / 'a_copy2.txt').stat().st_mtime == (src / 'a.txt').stat().st_mtime}")

        shutil.copytree(src, root / "dst")
        print(f"     copytree  -> {(root / 'dst').is_dir()}，里面有 "
              f"{sorted(x.name for x in (root / 'dst').iterdir())}")

        shutil.move(root / "a_copy.txt", root / "moved.txt")
        print(f"     move      -> moved.txt 存在？ {(root / 'moved.txt').exists()}")

        usage = shutil.disk_usage(root)
        print(f"     disk_usage-> 总 {usage.total / 2**30:.1f} GiB，"
              f"已用 {usage.used / 2**30:.1f} GiB，可用 {usage.free / 2**30:.1f} GiB")

        which = shutil.which("python")
        print(f"     which('python') -> {which}")

        size = shutil.get_terminal_size()
        print(f"     get_terminal_size() -> {size.columns} 列 x {size.lines} 行")

        # rmtree 是不可恢复的，动手之前一定要断言
        target = root / "dst"
        assert target.is_dir() and target != Path("/"), f"拒绝删除 {target}"
        shutil.rmtree(target)
        print(f"     rmtree    -> dst 还存在？ {target.exists()}")
        print("     ^ rmtree 没有回收站。真实代码里删之前一定要断言路径。")
    print()

    print("  -- 三个库的分工 --")
    print("     pathlib  路径：拼、拆、判断、遍历、简单读写")
    print("     os       环境：os.environ / os.getpid / os.rename")
    print("     shutil   高级操作：复制、移动、删目录树、打包")


# ======================================================================
def main() -> None:
    demo_hierarchy()
    demo_order()
    demo_eafp()
    demo_chain()
    demo_custom()
    demo_antipatterns()
    demo_pathlib()
    demo_encoding()
    demo_newline_and_with()
    demo_json_csv()
    demo_tempfile_shutil()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
