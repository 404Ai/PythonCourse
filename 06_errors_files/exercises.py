"""
模块 06 · 异常与文件 IO —— 练习

做法：
    1. 把每个函数里的 `raise NotImplementedError` 换成你的实现
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

**所有涉及文件的题目都必须在 tempfile.TemporaryDirectory() 里完成。**
跑完之后项目目录里不应该多出任何文件 —— 这是本模块的硬性要求，
也是真实项目里写测试的基本素养。

提示：报错的那一行可以下断点，按 F5 用调试器看中间变量。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 自定义异常层次 + 校验函数
# ======================================================================
class AppError(Exception):
    """本应用所有异常的根。

    调用方写 `except AppError` 就能把「业务的错」和「Python 的错」区分开。
    """


class ValidationError(AppError):
    """校验失败的基类。"""

    def __init__(self, field: str, message: str) -> None:
        # TODO: 调用父类构造，让 str(exc) 有意义；并保存 field / message
        raise NotImplementedError


class MissingFieldError(ValidationError):
    """必填字段缺失。"""

    def __init__(self, field: str) -> None:
        # TODO: message 用 "缺少必填字段"
        raise NotImplementedError


class TypeMismatchError(ValidationError):
    """类型不对。"""

    def __init__(self, field: str, expected: type, got: object) -> None:
        # TODO: message 里要包含期望类型和实际类型；
        #       还要把 expected / got 存成属性
        raise NotImplementedError


class OutOfRangeError(ValidationError):
    """数值超出范围。"""

    def __init__(self, field: str, value: int, low: int, high: int) -> None:
        # TODO: 保存 value / low / high
        raise NotImplementedError


def q1_validate_user(record: dict) -> dict:
    """校验一条用户记录，返回规范化后的 dict：

        {"name": str, "age": int, "email": str}

    规则（按顺序检查，第一个不通过的就抛异常）：
        1. "name" 不在 record 里（或值是空字符串） -> MissingFieldError("name")
        2. "name" 不是 str                        -> TypeMismatchError("name", str, 实际值)
        3. "age"  不在 record 里                  -> MissingFieldError("age")
        4. "age"  不是 int                        -> TypeMismatchError("age", int, 实际值)
           **注意：bool 是 int 的子类，True/False 必须算类型错误！**
        5. "age"  不在 0~150 之间                 -> OutOfRangeError("age", age, 0, 150)
        6. "email" 不在 record 里                 -> MissingFieldError("email")
        7. "email" 不是 str                       -> TypeMismatchError("email", str, 实际值)
        8. "email" 里没有 "@"                     -> ValidationError("email", "格式不正确")

    返回值：{"name": name.strip(), "age": age, "email": email.strip()}

    提示：
        - 每个异常类都是 ValidationError 的子类，
          所以 `except ValidationError` 能一次性兜住全部。
        - 检查 isinstance 时，bool 要先判。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— pathlib：遍历目录、筛选扩展名、统计文件大小
# ======================================================================
def q2_scan_directory(root: Path, extensions: tuple[str, ...] = (".py",)) -> dict:
    """递归扫描 root，统计指定扩展名的文件。

    返回一个 dict：
        {
            "count":  匹配到的文件个数（int）,
            "total_size": 这些文件的字节数总和（int）,
            "largest": 最大的那个文件的**相对路径字符串**（没有匹配则为 None）,
            "files":  排序后的相对路径字符串列表,
                     排序规则：先按文件大小降序，大小相同再按路径字典序升序,
        }

    要求：
        - 用 pathlib 的 glob / rglob，不要用 os.walk
        - 相对路径用 `path.relative_to(root)` 再 `str()`，
          并且把 Windows 的反斜杠统一换成 "/"（这样测试跨平台稳定）
        - 空目录 -> {"count": 0, "total_size": 0, "largest": None, "files": []}

    提示：
        - extensions 是元组，比如 (".py", ".txt")，要为每个后缀各 glob 一次
          （glob 一次只认一个模式；也可以自己过滤 suffix）
        - 别把目录也算进去，用 is_file() 筛
    """
    raise NotImplementedError


# ======================================================================
# q3 —— 读写 UTF-8 文本文件（含中文）
# ======================================================================
def q3_roundtrip_text(directory: Path, lines: list[str]) -> tuple[str, int, str]:
    """把 lines 逐行写进 directory/"notes.txt"，再读回来。

    返回 (读回的完整文本, 文件字节数, 非空行数)：
        - 用 utf-8 编码
        - 每行末尾写一个 "\\n"
        - 读回来的文本应该是 "行1\\n行2\\n" 这样

    注意：
        - 必须显式写 encoding="utf-8"，且最后一行也要带 "\\n"
        - 「非空行数」的定义是：去掉行尾换行符之后，字符串**不等于空串**的行数。
          所以一行全是空格的 "   " 算**非空**（它只是内容为空格，不是没内容）。
          在这里不要用 strip()，那会把有意义的空白吃掉；
          去掉行尾换行符请用 `line.rstrip("\\n")` 或 `line[:-1]`。

    提示：写入时用 "w" 模式，读取时用 open(...) 逐行迭代，
          或者直接 read_text。两种都行，但都要写 encoding。
    """
    raise NotImplementedError


def q3_read_with_fallback(path: Path) -> str:
    """按 utf-8 读 path；如果解码失败，改用 gbk 再读一次。

    两次都失败就抛 UnicodeDecodeError（让调用方看到）。

    场景：你收到一堆历史遗留文件，有的是 UTF-8 存的，有的是 GBK 存的，
    没有别的线索，只能试。

    要求：
        - 只捕获 UnicodeDecodeError，不要写 `except Exception`
        - 第二次失败时，异常应该**原样抛出**（用裸 raise 或让它自然传播）
        - 读的时候要处理文件不存在的情况吗？不需要——让 FileNotFoundError
          自然抛出去，调用方需要知道文件不在

    提示：`path.read_text(encoding="utf-8")` 失败会抛 UnicodeDecodeError。
    """
    raise NotImplementedError


# ======================================================================
# q4 —— JSON 读写（ensure_ascii=False 保存中文）
# ======================================================================
def q4_save_and_load_json(path: Path, data: dict) -> tuple[dict, str]:
    """把 data 以 JSON 存到 path，再读回来。

    返回 (读回来的对象, 文件原始文本)。

    要求：
        - ensure_ascii=False（中文必须原样写进文件，不能变成码点转义）
        - indent=2（缩进美化）
        - 编码 utf-8
        - 文件里必须能找到中文字符本身（测试会检查这个）

    提示：
        - `json.dump(data, f, ensure_ascii=False, indent=2)` 不会自动加末尾换行，
          这不影响测试，但你可以在写完手动写一个 "\\n"。
        - 写的时候用 `open(path, "w", encoding="utf-8")`。
    """
    raise NotImplementedError


def q4_load_json_with_default(path: Path) -> dict:
    """读 JSON 文件；如果文件里出现了不能直接反序列化的东西就返回 {}。

    只处理这两种情况：
        - 文件不存在（FileNotFoundError）-> 返回 {}
        - 内容不是合法 JSON（json.JSONDecodeError）-> 返回 {}

    其他异常（比如 PermissionError）**必须原样传播**——
    没权限和文件不存在是完全不同的问题，不能混为一谈。

    要求：捕获要精确到具体的异常类型，不要用 `except Exception`。

    提示：json.JSONDecodeError 是 ValueError 的子类，
          所以 `except ValueError` 也能抓到它，但那样会连别的 ValueError 一起兜住。
          写精确的那个。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— CSV 解析（DictReader + 类型转换 + 缺列处理）
# ======================================================================
def q5_parse_csv(path: Path) -> list[dict]:
    """解析 CSV 文件，返回规范化后的记录列表。

    输入格式（第一行是表头，一定有 name / score 两列，city 列可能缺失）：
        name,score,city
        张三,95,北京
        李四,,上海
        王五,abc,
        赵六,88

    输出：每条记录一个 dict，字段固定为 name / score / city：
        - name：字符串，strip 过；如果是空串就跳过这一行（不放进结果）
        - score：**int 或 None**。空串、非数字、超出 0~100 都算 None
        - city：字符串，strip 过；缺列时用 ""（不能用 None）

    要求：
        - 用 csv.DictReader
        - 打开文件时必须 `encoding="utf-8"` 且 `newline=""`
        - 用 restval="" 让缺列变成空串，这样 city 缺列时不会变成 None
        - score 的转换用 try/except ValueError（EAFP），不要用正则先校验

    提示：
        - `row["score"]` 一定是 str（CSV 没有类型系统）
        - 最后一行 "赵六,88" 缺了 city 列
    """
    raise NotImplementedError


# ======================================================================
# q6 —— 不要吞异常：把 except: pass 改成正确写法
# ======================================================================
def q6_safe_read_int(path: Path, default: int) -> tuple[int, str]:
    """读一个内容应该是整数的文件，返回 (值, 说明)。

    这是「不要吞异常」的练习。**要求返回里带上说明字符串**，
    这样调用方至少知道发生了什么，而不是拿到一个默认值却不知道原因。

    规则：
        1. 文件不存在       -> 返回 (default, "文件不存在")
        2. 文件读不出来     -> 返回 (default, "无法读取")        # OSError 但不是上面那种
        3. 内容不是整数     -> 返回 (default, "内容不是整数")
        4. 文件里是空内容   -> 返回 (default, "内容为空")
        5. 正常             -> 返回 (值, "读取成功")

    要求：
        - **绝对不允许出现 `except: pass` 或 `except Exception: pass`**
        - 每种失败都要有独立的、具体的 except 分支
        - 捕获的异常类型要尽量精确（FileNotFoundError 和 PermissionError
          都是 OSError 的子类，注意分支顺序）
        - 路径可能是个目录，open() 会抛 IsADirectoryError（也是 OSError 的子类）
          这种也应该归到 "无法读取"

    提示：
        - `int("  42  ")` 是合法的，会自动去空白
        - 空文件读出来是 ""，int("") 会抛 ValueError，
          但题目要求单独归为 "内容为空"，所以要先判空串
    """
    raise NotImplementedError


# ======================================================================
# q7 —— 异常链：包装底层异常
# ======================================================================
class ConfigError(AppError):
    """配置文件相关错误。"""


class ConfigNotFoundError(ConfigError):
    """配置文件不存在。"""


class ConfigFormatError(ConfigError):
    """配置文件格式非法。"""


def q7_load_config(path: Path) -> dict:
    """加载 JSON 配置文件，把底层异常包装成语义更清楚的配置异常。

    规则：
        - 文件不存在 -> 抛 ConfigNotFoundError，消息里要有路径，
          并且 `__cause__` 必须是原始的 FileNotFoundError（用 `raise ... from`）
        - JSON 解析失败 -> 抛 ConfigFormatError，消息里要有路径，
          并且 `__cause__` 必须是原始的 json.JSONDecodeError
        - 顶层不是 dict（比如是个 list 或者数字）->
          抛 ConfigFormatError，但这一条**没有 cause**（它是业务规则，不是底层异常）
        - 成功 -> 返回解析出来的 dict

    要求：
        - **必须用 `raise ... from exc`**，测试会检查 `__cause__`
        - 消息格式不重要，但必须包含 path 的字符串形式
        - 注意捕获顺序和类型精确度

    提示：
        - `json.load(f)` 抛的是 json.JSONDecodeError
        - 判断顶层类型用 `isinstance(data, dict)`
    """
    raise NotImplementedError


# ======================================================================
# q8 —— 大文件：逐行迭代，不要 readlines
# ======================================================================
def q8_stream_stats(path: Path) -> dict:
    """流式统计一个文本日志文件，不要把它整个读进内存。

    日志格式（每行）：
        2024-03-01 12:00:05 INFO  处理任务 42
        2024-03-01 12:00:06 ERROR 任务 43 失败

    即：日期 时间 级别 空格 消息

    返回：
        {
            "lines":     总行数（int，空行也算）,
            "levels":    {"INFO": 12, "ERROR": 3, ...}，各级别行数,
            "first_msg": 第一行里 "级别" 之后的消息部分（strip 过），
                         文件为空时为 None,
            "max_line":  最长那一行的长度（含结尾换行符），文件为空时为 0,
        }

    要求：
        - 用 `for line in f` 逐行迭代，**不许用 readlines() / read().splitlines()**
          （测试不会检查这一点，但你要自觉；1GB 的日志文件靠这个活命）
        - `with open(path, encoding="utf-8") as f:`
        - 解析级别：用 `line.split(maxsplit=3)`，
          拆不出来（少于 3 段）的行算作 "UNKNOWN" 级别
        - first_msg 是第一行 split(maxsplit=3) 之后的第 4 段（strip 过），
          如果第一行拆不出 4 段，则 first_msg 是 None

    提示：
        - `"a b c d".split(maxsplit=3)` -> ['a', 'b', 'c', 'd']
        - 别用 strip() 去掉整行再算长度，因为题目要的是**含换行符**的长度
    """
    raise NotImplementedError


# ======================================================================
# q9 —— try/except/else/finally 的执行顺序
# ======================================================================
def q9_execution_trace(scenario: str, trace: list[str]) -> list[str]:
    """按 scenario 执行一段 try/except/else/finally，把轨迹记进 trace。

    请**真的写出 try/except/else/finally 结构**，每一步往 trace 里 append 标记，
    而不是直接 return 一个写死的列表。

    scenario 取值：
        "ok"        正常结束              -> ["try", "else", "finally"]
        "handled"   抛 ValueError 并被捕获 -> ["try", "except", "finally"]
        "unhandled" 抛 KeyError，没被捕获  -> ["try", "finally", "escaped"]

    其中 "escaped" 表示异常最终穿透出了这个函数。

    为什么要把 trace 当参数传进来，而不是直接 return？
        因为 "unhandled" 场景下函数会抛异常，**根本走不到 return**。
        调用方只有通过自己传进去的那个列表，才能看到异常发生前的轨迹。
        这也是「异常路径下的副作用必须由调用方持有」的一个小例子。

    要求：
        - 三种场景的异常都必须**真的抛出**（能捕获的捕获，不能捕获的传播出去）
        - "unhandled" 场景里，KeyError 必须用裸 raise 重抛，不能吞掉，也不能
          改成别的异常类型
        - finally 里不要写 return

    提示：
        - 用一个 dict 把 scenario 映射到「要不要抛、抛什么」，会比 if/elif 干净
        - 别忘了在函数最后 `return trace`
    """
    raise NotImplementedError


# ======================================================================
# 自测
#
# 约定：所有测试都在临时目录里跑，跑完自动清理，不留残留文件。
# ======================================================================
def _make_tree(root: Path) -> None:
    """在 root 下造一棵固定的目录树，给 q2 用。

    这里显式写 newline="\\n" 是为了让「字符数 == 字节数」在所有平台上都成立。
    write_text 默认会把 "\\n" 翻译成 os.linesep（Windows 上是 "\\r\\n"），
    那样每个换行都会多出一个字节，测试里手算的期望值就对不上了。
    **写测试夹具时，能确定的字节数就别留给平台去决定。**
    """

    def put(path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8", newline="\n")

    (root / "src").mkdir(parents=True, exist_ok=True)
    put(root / "src" / "main.py", "print(1)\n")       # 9 字节
    put(root / "src" / "util.py", "x = 1\ny = 2\n")   # 12 字节
    (root / "src" / "deep").mkdir(exist_ok=True)
    put(root / "src" / "deep" / "big.py", "a" * 64 + "\n")   # 65 字节，最大的 .py
    put(root / "README.md", "# 标题\n")
    put(root / "notes.txt", "你好\n")


def t_q1() -> None:
    ok = q1_validate_user({"name": "张三", "age": 30, "email": " a@b.com "})
    assert ok == {"name": "张三", "age": 30, "email": "a@b.com"}, ok

    # bool 是 int 子类，必须先判
    try:
        q1_validate_user({"name": "张三", "age": True, "email": "a@b.com"})
    except TypeMismatchError as exc:
        assert exc.field == "age", exc.field
        assert exc.expected is int, exc.expected
        assert exc.got is True, exc.got
        assert "bool" in str(exc), f"消息里应该有实际类型名: {exc}"
    else:
        raise AssertionError("age=True 应该抛 TypeMismatchError")

    try:
        q1_validate_user({"age": 30, "email": "a@b.com"})
    except MissingFieldError as exc:
        assert exc.field == "name", exc.field
        assert isinstance(exc, ValidationError), "MissingFieldError 应该是 ValidationError 的子类"
    else:
        raise AssertionError("缺 name 应该抛 MissingFieldError")

    try:
        q1_validate_user({"name": "张三", "age": 200, "email": "a@b.com"})
    except OutOfRangeError as exc:
        assert (exc.value, exc.low, exc.high) == (200, 0, 150), vars(exc)
    else:
        raise AssertionError("age=200 应该抛 OutOfRangeError")

    try:
        q1_validate_user({"name": "张三", "age": 30, "email": "nope"})
    except ValidationError as exc:
        assert exc.field == "email", exc.field
    else:
        raise AssertionError("email 里没有 @ 应该抛 ValidationError")

    # 所有具体异常都必须能用一个 except ValidationError 兜住
    for bad in (
        {"age": 30, "email": "a@b.com"},
        {"name": 1, "age": 30, "email": "a@b.com"},
        {"name": "张三", "age": "30", "email": "a@b.com"},
        {"name": "张三", "age": -1, "email": "a@b.com"},
        {"name": "张三", "age": 30},
        {"name": "张三", "age": 30, "email": 5},
    ):
        try:
            q1_validate_user(bad)
        except ValidationError:
            pass
        else:
            raise AssertionError(f"{bad} 应该抛 ValidationError 的子类")


def t_q2() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _make_tree(root)

        result = q2_scan_directory(root, (".py",))
        assert result["count"] == 3, result
        assert result["total_size"] == 9 + 12 + 65, result
        assert result["largest"] == "src/deep/big.py", result
        assert result["files"] == [
            "src/deep/big.py",   # 65 字节
            "src/util.py",       # 12 字节
            "src/main.py",       # 9 字节
        ], result["files"]

        # 多后缀
        multi = q2_scan_directory(root, (".py", ".md"))
        assert multi["count"] == 4, multi
        assert multi["largest"] == "src/deep/big.py", multi

        # 没有匹配
        none = q2_scan_directory(root, (".rs",))
        assert none == {"count": 0, "total_size": 0, "largest": None, "files": []}, none

        # 空目录
        empty_dir = root / "empty"
        empty_dir.mkdir()
        assert q2_scan_directory(empty_dir, (".py",))["count"] == 0

        # 不能把目录算进去
        only_dirs = root / "onlydirs"
        (only_dirs / "a.py").mkdir(parents=True)
        assert q2_scan_directory(only_dirs, (".py",))["count"] == 0


def t_q3() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        text, size, nonempty = q3_roundtrip_text(root, ["第一行中文", "第二行", "第三行"])
        assert text == "第一行中文\n第二行\n第三行\n", repr(text)
        assert nonempty == 3, nonempty

        # 字节数必须和磁盘上的真实字节数一致。
        # 注意不能直接断言 `size == len(text.encode("utf-8"))`：
        # 文本模式写入时 "\n" 会被翻译成 os.linesep，Windows 上会多出 \r。
        # 这是**平台行为**，不是实现错误，所以两种都接受；
        # 但 GBK 编码出来的字节两种都不是 —— 那条才是我们要抓的 bug。
        raw = (root / "notes.txt").read_bytes()
        assert size == len(raw), (size, len(raw))
        assert raw in (text.encode("utf-8"),
                       text.replace("\n", "\r\n").encode("utf-8")), raw

        # 空串不算非空；只含空格的 "   " 算非空
        text2, _, nonempty2 = q3_roundtrip_text(root, ["有内容", "", "   ", "又一行"])
        assert text2 == "有内容\n\n   \n又一行\n", repr(text2)
        assert nonempty2 == 3, nonempty2

        # 文件里必须真的是 UTF-8 字节，不是 GBK。
        # 判据：「有内容」这三个字的 UTF-8 字节序列必须原样出现在文件里；
        # 如果实现里没写 encoding，Windows 上写出的是 GBK 字节，这里就挂。
        raw = (root / "notes.txt").read_bytes()
        assert "有内容".encode("utf-8") in raw, raw
        assert "有内容".encode("gbk") not in raw, "写成 GBK 了，说明没指定 encoding='utf-8'"

        # 空列表
        text3, size3, nonempty3 = q3_roundtrip_text(root, [])
        assert (text3, size3, nonempty3) == ("", 0, 0), (text3, size3, nonempty3)

        # ---- 编码回退 ----
        u8 = root / "u8.txt"
        u8.write_text("中文内容", encoding="utf-8")
        assert q3_read_with_fallback(u8) == "中文内容"

        gbk = root / "gbk.txt"
        gbk.write_bytes("中文内容".encode("gbk"))
        assert q3_read_with_fallback(gbk) == "中文内容", "GBK 文件应该能靠回退读出来"

        # 两种编码都解不开的字节序列 -> 必须抛 UnicodeDecodeError
        broken = root / "broken.txt"
        broken.write_bytes(b"\xff\xfe\x00\xff\xfe\x00")
        try:
            q3_read_with_fallback(broken)
        except UnicodeDecodeError:
            pass
        else:
            raise AssertionError("两种编码都失败时应该抛 UnicodeDecodeError")

        # 文件不存在 -> FileNotFoundError 必须传播出去
        try:
            q3_read_with_fallback(root / "nope.txt")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("文件不存在应该抛 FileNotFoundError")


def t_q4() -> None:
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "cfg.json"

        data = {"应用名": "示例", "版本": "1.0", "嵌套": {"键": [1, 2, 3]}}
        loaded, raw = q4_save_and_load_json(p, data)
        assert loaded == data, loaded

        # 中文必须原样出现在文件里，不能是码点转义
        assert "应用名" in raw, raw
        assert "\\u" not in raw, f"用了 ensure_ascii=True？文件内容: {raw}"

        # 缩进美化：应该有换行
        assert "\n" in raw, "indent=2 应该产生多行输出"

        # 再独立读一遍，确认是合法 JSON
        with open(p, encoding="utf-8") as f:
            assert json.load(f) == data

        # ---- 容错的读取 ----
        assert q4_load_json_with_default(root / "not_there.json") == {}

        bad = root / "bad.json"
        bad.write_text("{不是合法 json}", encoding="utf-8")
        assert q4_load_json_with_default(bad) == {}

        good = root / "good.json"
        good.write_text('{"a": 1}', encoding="utf-8")
        assert q4_load_json_with_default(good) == {"a": 1}


def t_q5() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "scores.csv"
        p.write_text(
            "name,score,city\n"
            "张三,95,北京\n"
            "李四,,上海\n"
            "王五,abc,\n"
            "赵六,88\n"
            ",70,广州\n"
            "钱七,-5,深圳\n"
            "孙八,120,杭州\n"
            "周九, 60 ,成都\n",
            encoding="utf-8",
        )

        rows = q5_parse_csv(p)
        got = [(r["name"], r["score"], r["city"]) for r in rows]
        expected = [
            ("张三", 95, "北京"),
            ("李四", None, "上海"),
            ("王五", None, ""),
            ("赵六", 88, ""),
            ("钱七", None, "深圳"),
            ("孙八", None, "杭州"),
            ("周九", 60, "成都"),
        ]
        assert got == expected, f"\n期望 {expected}\n实际 {got}"

        # name 为空的行要被跳过
        assert all(r["name"] for r in rows), "name 为空的行不该出现在结果里"
        assert len(rows) == 7, len(rows)

        # city 缺列时必须是 ""，不能是 None
        assert all(isinstance(r["city"], str) for r in rows), "city 必须是 str"

        # 文件只有表头
        empty = root / "empty.csv"
        empty.write_text("name,score,city\n", encoding="utf-8")
        assert q5_parse_csv(empty) == []


def t_q6() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        good = root / "good.txt"
        good.write_text("  42  \n", encoding="utf-8")
        assert q6_safe_read_int(good, -1) == (42, "读取成功")

        negative = root / "neg.txt"
        negative.write_text("-7", encoding="utf-8")
        assert q6_safe_read_int(negative, -1) == (-7, "读取成功")

        empty = root / "empty.txt"
        empty.write_text("", encoding="utf-8")
        assert q6_safe_read_int(empty, -1) == (-1, "内容为空")

        blank = root / "blank.txt"
        blank.write_text("   \n", encoding="utf-8")
        assert q6_safe_read_int(blank, -1) == (-1, "内容为空"), "全是空白也算内容为空"

        bad = root / "bad.txt"
        bad.write_text("3.14", encoding="utf-8")
        assert q6_safe_read_int(bad, -1) == (-1, "内容不是整数")

        assert q6_safe_read_int(root / "nope.txt", 0) == (0, "文件不存在")

        # 目录 -> OSError 家族 -> "无法读取"
        target_dir = root / "adir"
        target_dir.mkdir()
        assert q6_safe_read_int(target_dir, 0) == (0, "无法读取")

        # 关键：函数不能把异常吞成静默的默认值——它必须给出「说明」
        value, reason = q6_safe_read_int(bad, 99)
        assert reason != "", "必须返回说明，不能只是静默返回默认值"


def t_q7() -> None:
    import json
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        good = root / "ok.json"
        good.write_text('{"debug": true}', encoding="utf-8")
        assert q7_load_config(good) == {"debug": True}

        # 文件不存在
        try:
            q7_load_config(root / "missing.json")
        except ConfigNotFoundError as exc:
            assert isinstance(exc.__cause__, FileNotFoundError), \
                f"__cause__ 应该是 FileNotFoundError，实际 {exc.__cause__!r}"
            assert "missing.json" in str(exc), f"消息里要有路径: {exc}"
        else:
            raise AssertionError("文件不存在应该抛 ConfigNotFoundError")

        # 格式错误
        bad = root / "bad.json"
        bad.write_text("{不是 json}", encoding="utf-8")
        try:
            q7_load_config(bad)
        except ConfigFormatError as exc:
            assert isinstance(exc.__cause__, json.JSONDecodeError), \
                f"__cause__ 应该是 JSONDecodeError，实际 {exc.__cause__!r}"
            assert "bad.json" in str(exc), f"消息里要有路径: {exc}"
        else:
            raise AssertionError("非法 JSON 应该抛 ConfigFormatError")

        # 顶层不是 dict：这是业务规则，不该有 cause
        listy = root / "list.json"
        listy.write_text("[1, 2, 3]", encoding="utf-8")
        try:
            q7_load_config(listy)
        except ConfigFormatError as exc:
            assert exc.__cause__ is None, f"这条不该有 __cause__，实际 {exc.__cause__!r}"
            assert "list.json" in str(exc), f"消息里要有路径: {exc}"
        else:
            raise AssertionError("顶层不是 dict 应该抛 ConfigFormatError")

        # 三种异常都是 ConfigError / AppError 的后代，调用方能按粒度捕获
        for path, expected in (
            (root / "missing.json", ConfigNotFoundError),
            (bad, ConfigFormatError),
            (listy, ConfigFormatError),
        ):
            try:
                q7_load_config(path)
            except ConfigError as exc:
                assert isinstance(exc, expected), f"{path.name}: {type(exc).__name__}"
                assert isinstance(exc, AppError)


def t_q8() -> None:
    import tempfile

    log_text = (
        "2024-03-01 12:00:05 INFO  处理任务 42\n"
        "2024-03-01 12:00:06 ERROR 任务 43 失败\n"
        "2024-03-01 12:00:07 INFO  处理任务 44\n"
        "\n"
        "这行格式不对\n"
        "2024-03-01 12:00:08 WARNING 磁盘快满了\n"
    )

    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "app.log"
        p.write_text(log_text, encoding="utf-8")

        stats = q8_stream_stats(p)
        assert stats["lines"] == 6, stats
        assert stats["levels"] == {
            "INFO": 2, "ERROR": 1, "WARNING": 1, "UNKNOWN": 2,
        }, stats["levels"]
        assert stats["first_msg"] == "处理任务 42", stats["first_msg"]
        # 最长的是 "2024-03-01 12:00:08 WARNING 磁盘快满了\n"
        longest = max(len(line) for line in log_text.splitlines(keepends=True))
        assert stats["max_line"] == longest, (stats["max_line"], longest)

        # 空文件
        empty = root / "empty.log"
        empty.write_text("", encoding="utf-8")
        empty_stats = q8_stream_stats(empty)
        assert empty_stats["lines"] == 0, empty_stats
        assert empty_stats["levels"] == {}, empty_stats
        assert empty_stats["first_msg"] is None, empty_stats
        assert empty_stats["max_line"] == 0, empty_stats

        # 第一行拆不出 4 段
        weird = root / "weird.log"
        weird.write_text("只有一段\n", encoding="utf-8")
        weird_stats = q8_stream_stats(weird)
        assert weird_stats["first_msg"] is None, weird_stats
        assert weird_stats["levels"] == {"UNKNOWN": 1}, weird_stats


def t_q9() -> None:
    assert q9_execution_trace("ok", []) == ["try", "else", "finally"], \
        q9_execution_trace("ok", [])

    t_handled: list[str] = []
    assert q9_execution_trace("handled", t_handled) == ["try", "except", "finally"], \
        t_handled

    t_unhandled: list[str] = []
    try:
        q9_execution_trace("unhandled", t_unhandled)
    except KeyError:
        pass
    else:
        raise AssertionError("unhandled 场景必须把 KeyError 抛出去")
    assert t_unhandled == ["try", "finally", "escaped"], t_unhandled


def main() -> None:
    c = Checker("模块 06 · 异常与文件 IO 练习")
    c.add("q1  自定义异常层次 + 校验", t_q1)
    c.add("q2  pathlib 目录扫描统计", t_q2)
    c.add("q3  UTF-8 文本读写与编码回退", t_q3)
    c.add("q4  JSON 读写（中文不转义）", t_q4)
    c.add("q5  CSV 解析与类型转换", t_q5)
    c.add("q6  不要吞异常：安全读取整数", t_q6)
    c.add("q7  异常链：raise ... from", t_q7)
    c.add("q8  流式统计日志（不 readlines）", t_q8)
    c.add("q9  try/except/else/finally 轨迹", t_q9)
    c.run()


if __name__ == "__main__":
    main()
