"""
模块 06 · 异常与文件 IO —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每道题下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。
"""

from __future__ import annotations

import csv
import json
import sys
import tempfile
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 自定义异常层次 + 校验函数
# ======================================================================
class AppError(Exception):
    """本应用所有异常的根。

    存在的意义只有一个：给调用方一个「只捕获我的错」的抓手。
    没有它，调用方只能写 `except Exception`，那就会连 Python 内置的
    编程错误（TypeError、AttributeError）一起吞掉。
    """


class ValidationError(AppError):
    """校验失败的基类。

    中间层的作用：让调用方能选择粒度。
    想精确处理就 catch 叶子类，想一把兜住就 catch 这个。
    """

    def __init__(self, field: str, message: str) -> None:
        # super().__init__(message) 不能省：
        # Exception.__str__ 返回的是 self.args[0]，不调用父类构造，
        # str(exc) 就是空字符串，日志里什么都看不到。
        super().__init__(f"字段 {field!r}: {message}")
        self.field = field
        self.message = message


class MissingFieldError(ValidationError):
    """必填字段缺失。"""

    def __init__(self, field: str) -> None:
        super().__init__(field, "缺少必填字段")


class TypeMismatchError(ValidationError):
    """类型不对。"""

    def __init__(self, field: str, expected: type, got: object) -> None:
        # 消息里放 type(got).__name__ 而不是 repr(got)：
        # 用户输入可能很长/很敏感，类型名才是排查时真正需要的。
        super().__init__(field, f"应该是 {expected.__name__}，收到 {type(got).__name__}")
        self.expected = expected
        self.got = got


class OutOfRangeError(ValidationError):
    """数值超出范围。"""

    def __init__(self, field: str, value: int, low: int, high: int) -> None:
        super().__init__(field, f"必须在 [{low}, {high}] 之间，收到 {value}")
        self.value = value
        self.low = low
        self.high = high


def q1_validate_user(record: dict) -> dict:
    """按规则逐项检查，第一个不通过的就抛异常。"""

    # ---- name ----
    if not record.get("name"):          # 兼顾「键不存在」和「值是空字符串」
        raise MissingFieldError("name")
    name = record["name"]
    if not isinstance(name, str):
        raise TypeMismatchError("name", str, name)

    # ---- age ----
    if "age" not in record:
        raise MissingFieldError("age")
    age = record["age"]
    # bool 必须单独拦：`isinstance(True, int)` 是 True，
    # 不先判 bool 的话 True 会被当成合法的 1 岁。
    if isinstance(age, bool) or not isinstance(age, int):
        raise TypeMismatchError("age", int, age)
    if not 0 <= age <= 150:
        raise OutOfRangeError("age", age, 0, 150)

    # ---- email ----
    if "email" not in record:
        raise MissingFieldError("email")
    email = record["email"]
    if not isinstance(email, str):
        raise TypeMismatchError("email", str, email)
    if "@" not in email:
        raise ValidationError("email", "格式不正确")

    # 规范化放在最后：只有全部校验通过才返回值，
    # 半成品的结果绝不能交出去。
    return {"name": name.strip(), "age": age, "email": email.strip()}


# 常见错误写法：
#
#   1) 用 assert 做校验
#         assert isinstance(age, int), "age 必须是 int"
#      assert 会在 `python -O` 下被整个删掉（CPython 优化模式），
#      校验逻辑直接消失。**assert 只用于「不可能发生」的内部不变量**，
#      用户输入校验一律用显式 raise。
#
#   2) 返回 (bool, 错误信息) 而不是抛异常
#         ok, msg = validate(record)
#      调用方**可以忘记检查 ok**，而且嵌套调用时要一层层手动往上传递错误。
#      异常不会被忽略，这就是它比返回码强的地方。
#
#   3) 所有错误都抛同一个 ValidationError，不带字段名
#      -> 前端拿到 "校验失败" 四个字，不知道该把红框画在哪个输入框上。
#         结构化数据（field/expected/got）才是自定义异常的价值所在。
#
#   4) 忘了判 bool
#         if not isinstance(age, int): raise TypeMismatchError(...)
#     于是 {"age": True} 通过校验，变成 1 岁。
#
#   5) 自定义异常继承 BaseException
#      -> 别人的 `except Exception` 抓不到，程序直接被你的异常干掉。


# ======================================================================
# q2 —— pathlib 目录扫描
# ======================================================================
def q2_scan_directory(root: Path, extensions: tuple[str, ...] = (".py",)) -> dict:
    """用 rglob 逐个后缀收集，再排序。"""

    matches: list[Path] = []
    for ext in extensions:
        # rglob 一次只认一个模式，所以后缀要循环。
        # 另一条路是 rglob("*") 然后在 Python 里过滤 suffix，
        # 但那样会把目录树里所有文件都枚举一遍，后缀多的时候更慢。
        matches.extend(p for p in root.rglob(f"*{ext}") if p.is_file())

    # 去重：extensions 里如果写了 (".py", ".py")，或者有两个后缀互相包含
    # 的情况（比如 (".gz", ".tar.gz")），同一个文件会被收两次。
    # 用 dict.fromkeys 而不是 set，是为了保持稳定顺序方便调试。
    unique = list(dict.fromkeys(matches))

    # 排序键：(大小降序, 路径升序)
    # 用元组做 key，(…) 里第一个元素取负号实现降序，
    # 第二个元素保持升序 —— 这是 Python 里排多关键字的标准写法。
    files = sorted(unique, key=lambda p: (-p.stat().st_size, str(p.relative_to(root))))

    # Windows 上是反斜杠，统一换成 "/" 让结果跨平台稳定
    rel = [p.relative_to(root).as_posix() for p in files]
    total = sum(p.stat().st_size for p in files)

    return {
        "count": len(rel),
        "total_size": total,
        "largest": rel[0] if rel else None,     # files 已按大小降序，第一个就是最大
        "files": rel,
    }


# 常见错误写法：
#
#   1) os.walk + os.path.join 手工拼路径
#      能跑，但拼出来的是字符串，Windows 上是 "src\\deep\\big.py"，
#      测试断言写成 "src/deep/big.py" 就挂了。as_posix() 一行解决。
#
#   2) 忘了 is_file()，把目录也算进去
#      目录名恰好叫 "a.py" 时（真实项目里少见，但 __pycache__ 之类不少见），
#      stat().st_size 会拿到目录项的大小，通常是 0 或 4096，统计就错了。
#
#   3) 逐个文件调用两次 stat()
#         for p in files:
#             size = p.stat().st_size      # 第一次
#         total = sum(p.stat().st_size for p in files)   # 第二次
#      每次 stat() 都是一次系统调用。文件多的时候（几万个）差别很明显。
#      需要多处用到就先把 (path, size) 存下来。
#
#   4) 用 `p.name.endswith(ext)` 而不是 `p.suffix == ext`
#      "my.tar.gz".endswith(".gz") 是 True（碰巧对），
#      但找 ".gz" 时 "a.bz2" 不会被误判 —— 真正的问题是
#      endswith 会匹配到文件名中间部分之外的整个尾部，
#      而 suffix 是 pathlib 解析出来的、语义明确的那一个后缀。
#
#   5) 用 glob("**/*.py") 时不加 recursive 参数
#      那是 os 模块遗留风格。pathlib 的 rglob 已经隐含递归，别混着用。


# ======================================================================
# q3 —— UTF-8 文本读写
# ======================================================================
def q3_roundtrip_text(directory: Path, lines: list[str]) -> tuple[str, int, str]:
    """写进去再读回来，全程显式 utf-8。"""

    path = directory / "notes.txt"

    # "w" 会先清空文件；这里每次都从头写全部行，语义正确。
    # 如果是「追加」场景要用 "a"，别不小心写成 "w" 把历史数据清了。
    with open(path, "w", encoding="utf-8") as f:
        for line in lines:
            f.write(line + "\n")

    with open(path, encoding="utf-8") as f:
        text = f.read()

    size = path.stat().st_size

    # 用 rstrip("\n") 而不是 strip()：
    # 「   」这种全是空格的行应该算非空（它只是内容为空格），
    # strip() 会把它误判成空行。
    # 注意这里只削行尾的换行，不碰内容本身的空白。
    nonempty = sum(1 for line in text.splitlines() if line != "")

    return text, size, nonempty


# 常见错误写法：
#
#   1) 不写 encoding
#         with open(path, "w") as f: ...
#      简体中文 Windows 上是 cp936(GBK)，
#      本机写出来的是 GBK 字节，测试断言 "第一行中文".encode("utf-8") in raw 直接挂。
#      更糟的是：本机跑得通，部署到 Linux 上因为文件是 GBK 而炸掉 ——
#      这就是「跨平台 bug」的诞生过程。
#
#   2) 忘了给最后一行加 "\n"
#         text = "\n".join(lines)
#      结果 "行1\n行2"，最后一行没有换行符。
#      POSIX 标准里「文本文件每一行都应以换行结尾」，
#      很多命令行工具（wc -l、grep -c）会把缺尾换行的最后一行漏掉。
#
#   3) 用 strip() 统计非空行
#         nonempty = sum(1 for line in lines if line.strip())
#      把 "   " 这种行漏掉了。题目要的是「字符串非空」，
#      而 strip() 回答的是「去掉空白后非空」，是两个问题。
#
#   4) 用 readlines() 再逐行处理
#      小文件无所谓，但这是坏习惯。见 q8。
#
#   5) size 用 len(text)
#         len(text) 是**字符数**，不是字节数。
#      "中文" 的 len 是 2，字节数是 6。要字节数必须 path.stat().st_size
#      或者 len(text.encode("utf-8"))。


def q3_read_with_fallback(path: Path) -> str:
    """先试 utf-8，不行再试 gbk。

    这是 EAFP 的教科书场景：你没有别的线索判断文件是什么编码，
    **唯一的办法就是试着解码，失败了再换一种**。
    用 LBYL 写不出来 —— 没有任何 API 能「预先检查一个文件是不是 UTF-8」。
    """
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        # 只捕 UnicodeDecodeError。FileNotFoundError、PermissionError
        # 会自然往上抛 —— 那些不是「编码猜错了」，重试没有意义。
        return path.read_text(encoding="gbk")


# 常见错误写法：
#
#   1) except Exception
#      FileNotFoundError 也被吞掉，然后再用 gbk 读一次，又抛一次
#      FileNotFoundError —— 除了白白多做一次 IO，行为上没区别，
#      但你把「文件不存在」这个信息在第一次就被掩盖了，
#      以后加日志/加埋点时会发现根本分不清是哪一步失败的。
#
#   2) except UnicodeDecodeError: 后接第二个 try，且第二次也包了 except
#         try:
#             return path.read_text(encoding="utf-8")
#         except UnicodeDecodeError:
#             try:
#                 return path.read_text(encoding="gbk")
#             except UnicodeDecodeError:
#                 return ""        # 灾难：把不可恢复的编码错误降级成空字符串
#      两种编码都失败说明这个文件**不是文本**（可能是图片、加密数据），
#      返回空字符串会让调用方以为「文件是空的」，从而做出错误的业务决策。
#      正确做法是让异常抛出去。这也呼应 q6：不要吞异常。
#
#   3) 用 errors="replace" 掩盖问题
#         path.read_text(encoding="utf-8", errors="replace")
#     它不抛异常，但把解不开的字节替换成 U+FFFD（?），
#      数据被静默损坏。除非你在做「尽力而为的展示」，
#      否则不要用 errors="replace"。
#
#   4) 猜编码顺序反了
#      先试 gbk 再试 utf-8 是危险的：GBK 的解码器对很多字节序列都很宽容，
#      一个 UTF-8 文件很可能被 GBK「成功」解成乱码（不报错！）。
#      **一定要先试 UTF-8**，因为它对非法序列的检查严格得多。


# ======================================================================
# q4 —— JSON 读写
# ======================================================================
def q4_save_and_load_json(path: Path, data: dict) -> tuple[dict, str]:
    """ensure_ascii=False + indent=2，中文原样落盘。"""

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.write("\n")           # 文件末尾补一个换行，符合 POSIX 文本文件惯例

    raw = path.read_text(encoding="utf-8")

    with open(path, encoding="utf-8") as f:
        loaded = json.load(f)

    return loaded, raw


# 常见错误写法：
#
#   1) 忘了 ensure_ascii=False
#         json.dump(data, f, indent=2)
#      中文全部变成码点转义序列。文件仍然**是合法 JSON**，
#      反序列化后完全一样，所以测试不检查这个的话你根本发现不了 ——
#      直到某天有人打开配置文件，看到的是一堆看不懂的转义。
#      文件体积还会大好几倍（每个汉字 6 个 ASCII 字符）。
#
#   2) 认为 ensure_ascii=False 是「不转义所有字符」
#      它只管非 ASCII 字符。引号、反斜杠、换行这些**该转义的还是会转义**，
#      否则就不是合法 JSON 了。
#
#   3) 用 path.write_text(json.dumps(...)) 代替 json.dump
#         path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
#      能跑，但等于先把整个 JSON 在内存里拼成一个巨型字符串再写。
#      数据大的时候（几十 MB）内存翻倍。json.dump 是流式写出的。
#
#   4) 忘了写 encoding
#      同样是 GBK 陷阱。json.dump 默认会写 UnicodeEncodeError 或者乱码。
#
#   5) 用 repr(data) 或者 str(data) 当 JSON 存
#      Python 的 repr 用单引号，JSON 只认双引号；True/None 也不一样。
#      存出来的东西 json.load 读不回来。


def q4_load_json_with_default(path: Path) -> dict:
    """只兜住「文件不在」和「不是合法 JSON」两种，其他让它抛。"""

    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        # 精确捕 FileNotFoundError，而不是 IOError/OSError：
        # PermissionError 也继承自 OSError，但它代表「文件在那儿，你没资格读」，
        # 这是配置/部署问题，必须让调用方看见。
        return {}
    except json.JSONDecodeError:
        # 不用 `except ValueError`，虽然 JSONDecodeError 是它的子类：
        # 那样写会把别的 ValueError 也一起兜住，语义就不精确了。
        # **except 写多窄，就代表你的意图有多明确。**
        return {}


# 常见错误写法：
#
#   1) except Exception: return {}
#      硬盘坏了、权限不够、文件被别的进程独占 —— 全部变成「配置是空的」，
#      程序带着默认配置默默跑起来，产出错误的结果。
#      配置读取失败是最应该**大声报错**的场景之一。
#
#   2) 读出来是 list 或 str 也照单全收
#      调用方期待 dict，你返回 [] 或者 "abc"，
#      错误就推迟到了 `data["key"]` 那一行，离根因很远。
#      在边界处（读文件的地方）就把类型检查做掉。
#
#   3) 把 json.JSONDecodeError 的原始信息丢掉
#      JSONDecodeError 上有 .lineno / .colno / .pos / .msg，
#      是定位问题的金矿。你要吞掉它，至少把 msg 打进日志。
#
#   4) 忘了 encoding="utf-8"
#      Windows 上按 GBK 读 UTF-8 的 JSON 文件 -> UnicodeDecodeError，
#      然后被你的 except Exception 吞掉，返回 {}。
#      两个 bug 叠加，排查难度指数上升。


# ======================================================================
# q5 —— CSV 解析
# ======================================================================
def q5_parse_csv(path: Path) -> list[dict]:
    """DictReader + EAFP 的类型转换。"""

    result: list[dict] = []

    # newline="" 是 csv 模块的硬性要求：csv 自己会写 \r\n 作行终止符，
    # 如果文本层再做一次 universal-newline 翻译，就会变成 \r\r\n。
    # 读的时候不加也能跑，但写的时候不加必然出问题 —— 养成习惯两个都加。
    with open(path, encoding="utf-8", newline="") as f:
        # restval="" 让缺失的列变成空字符串而不是 None。
        # 这样调用方拿到的 city 永远是 str，不用到处写 `or ""`。
        reader = csv.DictReader(f, restval="")
        for row in reader:
            name = (row.get("name") or "").strip()
            if not name:
                # 整行没名字就跳过。注意 row.get("name") 也可能返回
                # None（列名压根不在表头里），所以先 `or ""` 再 strip。
                continue

            result.append({
                "name": name,
                "score": _parse_score(row.get("score")),
                "city": (row.get("city") or "").strip(),
            })

    return result


def _parse_score(raw: object) -> int | None:
    """把 CSV 里的分数字符串转成 int，任何不合理的情况都返回 None。

    EAFP 版本：直接 int()，失败再处理。
    LBYL 版本要先判空串、判 isdigit、判负号、判空白……
    而 CSV 是**外部数据**，失败率不低但也没到「常态」，
    所以 try/except 是合适的；同时这段不在热循环里，性能完全不是问题。
    """
    text = (raw if isinstance(raw, str) else "").strip()
    if not text:
        return None                    # 空单元格 -> None，不是 0
    try:
        value = int(text)
    except ValueError:
        return None                    # "abc"、"3.14"、"1e3" 都到这里
    if not 0 <= value <= 100:
        return None                    # 范围外也当无效
    return value


# 常见错误写法：
#
#   1) 不加 newline=""
#      读的时候在 Windows 上会因为 \r\n 被翻译一次而侥幸没事，
#      但写的时候必然产生空行。习惯要一次养成：csv + open 永远 newline=""。
#
#   2) 不加 encoding="utf-8"
#      Windows 上是 GBK，中文列直接炸或者乱码。
#
#   3) 不做类型转换，直接把 row 交出去
#         return list(reader)
#      调用方拿到 {"score": "95"}，某天字符串比较 "95" < "100" 是 True
#      这种 bug 会在离这里一千行的地方爆炸。
#      **在系统边界处完成类型转换**是数据处理的铁律。
#
#   4) 用 `row["score"]` 而不是 `row.get("score")`
#      如果 CSV 的表头里根本没有 score 这一列（上游改了格式），
#      DictReader 生成的 dict 里就没有这个键，直接 KeyError。
#      对**外部数据**要用 .get()，对自己构造的 dict 才用 []。
#
#   5) 空字符串被 int() 抛异常后连行都丢了
#         try: score = int(row["score"])
#         except ValueError: continue      # 整行被跳过
#      空分数和非法分数都是「这一行的分数无效」，
#      不代表「这一行没有意义」。丢弃整行会丢数据。
#
#   6) 用 csv.reader 然后 row[1] 取列
#      列顺序一变就全错，而且代码里到处是魔法数字。
#      DictReader 至少让列名参与进来。
#
#   7) 手工 line.split(",")
#      引号里的逗号、字段内的换行、BOM 全都会把你打穿。
#      **永远不要手写 CSV 解析器**，csv 模块就是标准库给你的答案。


# ======================================================================
# q6 —— 不要吞异常
# ======================================================================
def q6_safe_read_int(path: Path, default: int) -> tuple[int, str]:
    """每种失败都有独立的、具体的分支，并且都带说明。

    注意这个函数**故意不抛异常**：它的契约是「尽力给一个值 + 一个说明」。
    这不是吞异常 —— 吞异常是「不抛也不说」，
    这里是「不抛，但把发生了什么明确地交给调用方」。
    """

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        # 最具体的放最前面。FileNotFoundError 是 OSError 的子类，
        # 顺序反了它就被下面的 OSError 分支吃掉，说明文字会变错。
        return default, "文件不存在"
    except OSError:
        # 剩下的 OSError 家族：PermissionError（没权限）、
        # IsADirectoryError（路径是目录）、磁盘错误、路径太长……
        # 对调用方来说它们的共同点是「这个路径读不了」。
        # 注意这里**没有**写 except Exception：编程错误（NameError、
        # AttributeError）必须原样抛出去，那是 bug 不是预期情况。
        return default, "无法读取"

    if not text.strip():
        return default, "内容为空"

    try:
        return int(text), "读取成功"
    except ValueError:
        # int("3.14") / int("abc") 都到这里。
        # 不把原始 ValueError 吞掉就完事，而是给出「内容不是整数」这个
        # 调用方能理解的说明 —— 错误信息要做的是**翻译**，不是删除。
        return default, "内容不是整数"


# 常见错误写法：
#
#   1) 你正在看的那一种：
#         try:
#             return int(Path(path).read_text()), "读取成功"
#         except:
#             pass
#         return default, ""
#      文件不存在、没权限、内容是 "abc" —— 全部塌缩成同一个结果，
#      调用方拿到的说明是空字符串，等于什么都没说。
#      线上出问题时，你连「是文件没了还是内容坏了」都分不清。
#
#   2) except Exception: return default, "读取失败"
#      比上一条好（至少有说明），但仍然把「程序 bug」和「预期内的失败」
#      混为一谈。哪天 path 传了个 None，你会得到 "读取失败"，
#      然后花两小时去查文件系统，实际上问题在调用方。
#
#   3) 先判 FileNotFoundError 再判 OSError —— 顺序反了
#         except OSError: ...          # FileNotFoundError 在这里就被截胡了
#         except FileNotFoundError: ...  # 永远到不了，而且这行代码看起来
#                                         还很合理，code review 时极易漏掉
#      Python 的 except 是**按书写顺序**匹配的，第一个匹配上的胜出。
#
#   4) 把所有 OSError 都改名成 "文件不存在"
#      用户看到「文件不存在」，去创建了一个同名文件，
#      然后发现还是不行 —— 因为真正的原因是没权限。
#      **错误信息比实际原因模糊，比没有错误信息更坏。**
#
#   5) 只捕获不记录
#      这个函数把说明返回给调用方，是**契约的一部分**。
#      如果你的函数不打算返回说明，那就应该 log 一行。
#      静默的 except 等于把证据销毁。


# ======================================================================
# q7 —— 异常链
# ======================================================================
class ConfigError(AppError):
    """配置文件相关错误。"""


class ConfigNotFoundError(ConfigError):
    """配置文件不存在。"""


class ConfigFormatError(ConfigError):
    """配置文件格式非法。"""


def q7_load_config(path: Path) -> dict:
    """用 raise ... from 把底层异常包装成有语义的配置异常。"""

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError as exc:
        # `from exc` 是这里的重点。没有它，traceback 只会说
        # "During handling of the above exception, another exception occurred"，
        # 有它才会明确地写 "The above exception was the direct cause of..."。
        # 语义差别是「我因为这个才抛」vs「我处理那个的时候顺便抛了」。
        raise ConfigNotFoundError(f"配置文件不存在: {path}") from exc
    except json.JSONDecodeError as exc:
        # 把 exc 的定位信息带进消息里。
        # json.JSONDecodeError 有 .lineno / .colno / .msg，
        # 这些是用户改配置时最需要的东西。
        raise ConfigFormatError(
            f"配置文件不是合法 JSON: {path}（第 {exc.lineno} 行第 {exc.colno} 列: {exc.msg}）"
        ) from exc

    if not isinstance(data, dict):
        # 这一条**不加 from**：顶层不是对象是**业务规则**，
        # 不是「底层抛了个异常我包一下」。
        # 给它硬塞一个 __cause__ 会让 traceback 读起来莫名其妙。
        raise ConfigFormatError(
            f"配置文件的顶层必须是 JSON 对象，实际是 {type(data).__name__}: {path}"
        )

    return data


# 常见错误写法：
#
#   1) 不用 from
#         except FileNotFoundError:
#             raise ConfigNotFoundError(f"配置文件不存在: {path}")
#      原始异常会变成 __context__，traceback 里措辞是
#      "During handling of the above exception..."，
#      而且如果中间还有别的异常穿插，链条会被替换掉。
#      **包装异常时一律写 from，这是无条件的习惯。**
#
#   2) 用 `raise ... from None` 断链
#      对配置文件这种「用户要自己排查」的场景，
#      藏掉底层错误等于让用户自己去猜。from None 只适合
#      「底层异常纯属实现细节，暴露出来只会误导」的库内部场景。
#
#   3) 消息里不带 path
#         raise ConfigNotFoundError("配置文件不存在")
#      一个程序可能读 5 个配置文件，用户拿到这句话完全不知道是哪个。
#      **异常消息里要带上定位问题所需的全部上下文。**
#
#   4) 捕获 Exception 而不是具体类型
#      那会把 KeyboardInterrupt 之外的一切都变成 ConfigFormatError，
#      包括你自己代码里的 TypeError —— 一个编程 bug 被伪装成「用户配置写错了」，
#      用户会去反复检查配置文件，永远找不到问题。
#
#   5) 顶层类型检查忘了做
#      配置文件内容是个 `[1, 2, 3]` 时，函数返回一个 list，
#      调用方 `cfg["debug"]` -> TypeError: list indices must be integers。
#      错误推迟到了很远的地方，而且错误类型（TypeError）完全没提示
#      「是你的配置文件写错了」。
#      **校验要发生在数据进入系统的边界处。**


# ======================================================================
# q8 —— 流式统计
# ======================================================================
def q8_stream_stats(path: Path) -> dict:
    """逐行迭代，内存恒定。"""

    lines = 0
    levels: Counter[str] = Counter()
    first_msg: str | None = None
    max_line = 0

    # `for line in f` 是文件对象的迭代协议：内部有约 8KB 的读缓冲，
    # 每次 __next__ 从缓冲区切一行，缓冲用完才做一次系统调用。
    # 所以它既省内存（峰值约 8KB，不随文件增长），也不比 readlines 慢。
    with open(path, encoding="utf-8") as f:
        for line in f:
            lines += 1

            # 注意：这里不能对整行做 strip 再算长度，
            # 题目要的是含换行符的原始长度。
            if len(line) > max_line:
                max_line = len(line)

            parts = line.split(maxsplit=3)
            # parts 长度：0（空行）/1/2 -> 都不是合法日志行
            if len(parts) >= 3:
                levels[parts[2]] += 1
            else:
                levels["UNKNOWN"] += 1

            # 只处理第一行
            if lines == 1:
                first_msg = parts[3].strip() if len(parts) >= 4 else None

    return {
        "lines": lines,
        "levels": dict(levels),
        "first_msg": first_msg,
        "max_line": max_line,
    }


# 常见错误写法：
#
#   1) readlines() / read().splitlines()
#         for line in path.read_text(encoding="utf-8").splitlines():
#      一个 1GB 的日志文件会瞬间占满 1GB+ 内存（str 对象本身，
#      还没算 splitlines 产生的几百万个字符串对象）。
#      本机测试用的小文件永远看不出问题，线上直接 OOM。
#
#   2) 先 strip() 再算 len
#      "abc\n".strip() 长度是 3 不是 4，max_line 全错。
#      strip 是很方便，但**它会同时削掉行首和行尾**，
#      任何时候需要「原始内容」都不能用它。
#
#   3) 用正则解析每一行
#         m = re.match(r"(\S+) (\S+) (\S+) (.*)", line)
#      正则引擎比 str.split 慢一个数量级，而这里根本不需要正则的
#      表达力（格式是「按空白切 4 段」）。
#      **热循环里能用 split 就别用 re。**
#
#   4) 忘了空行的 parts 长度是 0
#         level = parts[2]        # IndexError: list index out of range
#      日志文件里空行/半截行是常态（进程被杀时最后一行可能不完整），
#      边界一定要处理。
#
#   5) max_line 用 max(len(line) for line in f) 单独再遍历一次
#      文件读两遍，IO 成本翻倍。一次遍历里顺手统计，
#      这是流式处理的固定模式。
#
#   6) Counter 用普通 dict 手写
#         levels[level] = levels.get(level, 0) + 1
#      能跑，但 Counter 就是为这个场景设计的（模块 02 讲过），
#      而且 Counter 还自带 most_common()。
#
#   7) 觉得「文件才几 MB，一次性读完没事」
#      代码会一直在同一份数据上跑。今天 3MB 的日志，
#      明年就是 30GB。**流的接口天然比一次性读更耐增长。**


# ======================================================================
# q9 —— 执行轨迹
# ======================================================================
def q9_execution_trace(scenario: str, trace: list[str]) -> list[str]:
    """四种块的执行顺序，以及异常如何穿透。"""

    # 用 dict 把「场景 -> 异常类型」映射出来，
    # 比 if/elif 链更好读，加新场景只改一行数据。
    errors: dict[str, type[Exception]] = {
        "ok": None,
        "handled": ValueError,
        "unhandled": KeyError,
    }

    try:
        try:
            trace.append("try")
            error = errors[scenario]
            if error is not None:
                raise error(f"scenario={scenario}")

        except ValueError:
            # 只捕 ValueError。KeyError 会穿过这一层。
            trace.append("except")

        else:
            # else 只在 try 块**没有抛异常**时执行。
            # 注意它和 `try` 块的区别：把代码写在 else 里而不是 try 里，
            # 意味着「这一段抛的异常，不会被上面的 except 捕获」。
            trace.append("else")

        finally:
            # finally 在 return / 异常传播 / 正常结束三种路径上都会执行。
            # 这里**绝对不能写 return** —— 既会吞掉异常，
            # 也会在 Python 3.13+ 触发 SyntaxWarning。
            trace.append("finally")

    except KeyError:
        # 异常从内层传播出来之后，在 finally 已经跑完的那一刻才落到这里。
        # 所以轨迹顺序是 try -> finally -> escaped。
        trace.append("escaped")
        raise           # 裸 raise：原样重抛，保留完整 traceback

    return trace


# 常见错误写法：
#
#   1) 直接 return 写死的列表
#         if scenario == "ok": return ["try", "else", "finally"]
#      题目正是要你亲手写出这四块，才能记住顺序。
#      能通过测试不代表学到了东西 —— 这是本课程里唯一一道
#      「测试无法验证你是否真的理解」的题，靠自觉。
#
#   2) 在 finally 里 return
#         finally:
#             trace.append("finally")
#             return trace        # 灾难
#      这会让 KeyError 被静默吞掉，测试里那个 `except KeyError` 永远不触发，
#      而且 Python 3.13+ 会给你一个 SyntaxWarning。
#
#   3) 把 "escaped" 也写在 finally 里
#         finally:
#             trace.append("finally")
#             trace.append("escaped")   # 错：正常路径也会被标成 escaped
#      finally 无法区分「接下来是正常返回还是异常传播」。
#      要判断逃逸，只能在外层用 except 接住。
#
#   4) 外层用 `except BaseException` 接
#      那会连 KeyboardInterrupt 一起吞，虽然本题测试能过，
#      但在真实代码里这是明确的坏味道。
#      **接什么异常，就写什么类型。**
#
#   5) `raise KeyError(...)` 而不是裸 `raise`
#      功能上测试也能过，但会多出一帧 traceback，
#      而且异常的 args 会变成空的……（实际上 raise 裸抛保留原 args）。
#      总之：在 except 里重新抛出，永远用裸 raise。
#
#   6) 忘了 `return trace`
#      异常没发生时会返回 None，测试直接断言失败。


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def _make_tree(root: Path) -> None:
    """在 root 下造一棵固定的目录树，给 q2 用。

    newline="\\n" 让「字符数 == 字节数」在所有平台上都成立，
    write_text 默认会把 "\\n" 翻成 os.linesep，那样期望值就不可移植了。
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
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        _make_tree(root)

        result = q2_scan_directory(root, (".py",))
        assert result["count"] == 3, result
        assert result["total_size"] == 9 + 12 + 65, result
        assert result["largest"] == "src/deep/big.py", result
        assert result["files"] == [
            "src/deep/big.py",
            "src/util.py",
            "src/main.py",
        ], result["files"]

        multi = q2_scan_directory(root, (".py", ".md"))
        assert multi["count"] == 4, multi
        assert multi["largest"] == "src/deep/big.py", multi

        none = q2_scan_directory(root, (".rs",))
        assert none == {"count": 0, "total_size": 0, "largest": None, "files": []}, none

        empty_dir = root / "empty"
        empty_dir.mkdir()
        assert q2_scan_directory(empty_dir, (".py",))["count"] == 0

        only_dirs = root / "onlydirs"
        (only_dirs / "a.py").mkdir(parents=True)
        assert q2_scan_directory(only_dirs, (".py",))["count"] == 0


def t_q3() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        text, size, nonempty = q3_roundtrip_text(root, ["第一行中文", "第二行", "第三行"])
        assert text == "第一行中文\n第二行\n第三行\n", repr(text)
        assert nonempty == 3, nonempty

        # 文本模式写入时 "\n" 会被翻译成 os.linesep（Windows 上是 \r\n），
        # 这是平台行为不是实现错误，所以两种字节序列都接受。
        # 但 GBK 编码出来的字节两种都不是 —— 那条才是要抓的 bug。
        raw = (root / "notes.txt").read_bytes()
        assert size == len(raw), (size, len(raw))
        assert raw in (text.encode("utf-8"),
                       text.replace("\n", "\r\n").encode("utf-8")), raw

        text2, _, nonempty2 = q3_roundtrip_text(root, ["有内容", "", "   ", "又一行"])
        assert text2 == "有内容\n\n   \n又一行\n", repr(text2)
        assert nonempty2 == 3, nonempty2

        raw = (root / "notes.txt").read_bytes()
        assert "有内容".encode("utf-8") in raw, raw
        assert "有内容".encode("gbk") not in raw, "写成 GBK 了，说明没指定 encoding='utf-8'"

        text3, size3, nonempty3 = q3_roundtrip_text(root, [])
        assert (text3, size3, nonempty3) == ("", 0, 0), (text3, size3, nonempty3)

        u8 = root / "u8.txt"
        u8.write_text("中文内容", encoding="utf-8")
        assert q3_read_with_fallback(u8) == "中文内容"

        gbk = root / "gbk.txt"
        gbk.write_bytes("中文内容".encode("gbk"))
        assert q3_read_with_fallback(gbk) == "中文内容", "GBK 文件应该能靠回退读出来"

        broken = root / "broken.txt"
        broken.write_bytes(b"\xff\xfe\x00\xff\xfe\x00")
        try:
            q3_read_with_fallback(broken)
        except UnicodeDecodeError:
            pass
        else:
            raise AssertionError("两种编码都失败时应该抛 UnicodeDecodeError")

        try:
            q3_read_with_fallback(root / "nope.txt")
        except FileNotFoundError:
            pass
        else:
            raise AssertionError("文件不存在应该抛 FileNotFoundError")


def t_q4() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)
        p = root / "cfg.json"

        data = {"应用名": "示例", "版本": "1.0", "嵌套": {"键": [1, 2, 3]}}
        loaded, raw = q4_save_and_load_json(p, data)
        assert loaded == data, loaded

        assert "应用名" in raw, raw
        assert "\\u" not in raw, f"用了 ensure_ascii=True？文件内容: {raw}"
        assert "\n" in raw, "indent=2 应该产生多行输出"

        with open(p, encoding="utf-8") as f:
            assert json.load(f) == data

        assert q4_load_json_with_default(root / "not_there.json") == {}

        bad = root / "bad.json"
        bad.write_text("{不是合法 json}", encoding="utf-8")
        assert q4_load_json_with_default(bad) == {}

        good = root / "good.json"
        good.write_text('{"a": 1}', encoding="utf-8")
        assert q4_load_json_with_default(good) == {"a": 1}


def t_q5() -> None:
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

        assert all(r["name"] for r in rows), "name 为空的行不该出现在结果里"
        assert len(rows) == 7, len(rows)
        assert all(isinstance(r["city"], str) for r in rows), "city 必须是 str"

        empty = root / "empty.csv"
        empty.write_text("name,score,city\n", encoding="utf-8")
        assert q5_parse_csv(empty) == []


def t_q6() -> None:
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

        target_dir = root / "adir"
        target_dir.mkdir()
        assert q6_safe_read_int(target_dir, 0) == (0, "无法读取")

        value, reason = q6_safe_read_int(bad, 99)
        assert reason != "", "必须返回说明，不能只是静默返回默认值"


def t_q7() -> None:
    with tempfile.TemporaryDirectory() as d:
        root = Path(d)

        good = root / "ok.json"
        good.write_text('{"debug": true}', encoding="utf-8")
        assert q7_load_config(good) == {"debug": True}

        try:
            q7_load_config(root / "missing.json")
        except ConfigNotFoundError as exc:
            assert isinstance(exc.__cause__, FileNotFoundError), \
                f"__cause__ 应该是 FileNotFoundError，实际 {exc.__cause__!r}"
            assert "missing.json" in str(exc), f"消息里要有路径: {exc}"
        else:
            raise AssertionError("文件不存在应该抛 ConfigNotFoundError")

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

        listy = root / "list.json"
        listy.write_text("[1, 2, 3]", encoding="utf-8")
        try:
            q7_load_config(listy)
        except ConfigFormatError as exc:
            assert exc.__cause__ is None, f"这条不该有 __cause__，实际 {exc.__cause__!r}"
            assert "list.json" in str(exc), f"消息里要有路径: {exc}"
        else:
            raise AssertionError("顶层不是 dict 应该抛 ConfigFormatError")

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
        longest = max(len(line) for line in log_text.splitlines(keepends=True))
        assert stats["max_line"] == longest, (stats["max_line"], longest)

        empty = root / "empty.log"
        empty.write_text("", encoding="utf-8")
        empty_stats = q8_stream_stats(empty)
        assert empty_stats["lines"] == 0, empty_stats
        assert empty_stats["levels"] == {}, empty_stats
        assert empty_stats["first_msg"] is None, empty_stats
        assert empty_stats["max_line"] == 0, empty_stats

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
    c = Checker("模块 06 · 异常与文件 IO 参考答案")
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
