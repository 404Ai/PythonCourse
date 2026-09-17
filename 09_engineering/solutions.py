"""
模块 09 · 工程化实践 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**
"""

from __future__ import annotations

import importlib.util
import logging
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 解析版本号
# ======================================================================
def q1_parse_version(text: str) -> tuple[int, int, int]:
    """去掉前缀 -> 切分 -> 校验 -> 补齐。"""
    cleaned = text.strip()
    if cleaned[:1] in ("v", "V"):
        cleaned = cleaned[1:]

    parts = cleaned.split(".")
    if len(parts) > 3:
        raise ValueError(f"版本号最多三段，收到 {text!r}")

    values: list[int] = []
    for part in parts:
        # 用 isdigit() 而不是 try/except int()：
        # 这里的意图是「校验」，用异常做流程控制反而不清晰。
        # 注意 isdigit() 对空字符串返回 False，所以 '1..2' 会被拦下。
        if not part.isdigit():
            raise ValueError(f"版本号的每一段都必须是数字，收到 {text!r}")
        values.append(int(part))

    while len(values) < 3:
        values.append(0)

    return values[0], values[1], values[2]


# 常见错误：
#   1. `major, minor, patch = text.split(".")` —— '1.2' 只有两段，直接炸
#   2. 忘了处理 'v' 前缀 —— 实际项目里 git tag 几乎都带 v
#   3. 用 int() 包住 split 的结果但不校验段数 —— '1.2.3.4' 会被静默接受
#
# 顺带一提：真实项目**不要自己写版本比较**。
#   用 packaging 库的 packaging.version.Version，它按 PEP 440 处理了
#   预发布版（1.0a1）、开发版（1.0.dev1）、本地版本（1.0+ubuntu1）
#   这些你想都想不到的边角情况。这里手写只是为了理解原理。


# ======================================================================
# q2 —— 版本约束匹配
# ======================================================================
_OPERATORS = (">=", "<=", "==", ">", "<")


def q2_satisfies(version: str, spec: str) -> bool:
    """把两边都解析成三元组再逐条比较。"""
    current = q1_parse_version(version)
    spec = spec.strip()
    if not spec:
        return True

    for clause in spec.split(","):
        clause = clause.strip()
        if not clause:
            continue
        for op in _OPERATORS:
            if clause.startswith(op):
                target = q1_parse_version(clause[len(op):].strip())
                matched = {
                    ">=": current >= target,
                    "<=": current <= target,
                    "==": current == target,
                    ">": current > target,
                    "<": current < target,
                }[op]
                if not matched:
                    return False
                break
        else:
            raise ValueError(f"看不懂的版本约束：{clause!r}")

    return True


# 三个关键点：
#
# 1. **运算符的匹配顺序不能乱。**
#    _OPERATORS 里 ">=" 必须排在 ">" 前面。
#    否则 ">=1.2" 会被 ">" 匹配到，剩下的 "=1.2" 拿去做版本解析，直接炸。
#    这是「前缀匹配」的经典坑——永远先试长的。
#
# 2. **for/else 的用法。**
#    for 循环正常跑完（没 break）会执行 else 分支。这里用它表示
#    「所有运算符都试过了，一个都没匹配上」-> 抛 ValueError。
#    比再加一个标志变量干净。
#
# 3. **元组比较天然按位比较。**
#    (1, 9, 9) < (2, 0, 0) 成立，不需要先补零对齐长度。
#    这正是把版本号解析成定长元组的价值——比较逻辑白送。
#
# 真实项目同样应该用 packaging：
#     from packaging.specifiers import SpecifierSet
#     "1.4.2" in SpecifierSet(">=1.2,<2.0")
# 它还支持 ~=、===、以及预发布版的特殊规则。


# ======================================================================
# q3 —— 搭项目骨架
# ======================================================================
def q3_scaffold(root: Path, package: str = "mypkg") -> list[str]:
    """把「相对路径 -> 内容」写成字典，一次性铺出去。"""
    root = Path(root)
    files = {
        "pyproject.toml": (
            "[build-system]\n"
            'requires = ["hatchling"]\n'
            'build-backend = "hatchling.build"\n'
            "\n"
            "[project]\n"
            f'name = "{package}"\n'
            'version = "0.1.0"\n'
            'requires-python = ">=3.11"\n'
        ),
        "README.md": f"# {package}\n\n这是 `q3_scaffold` 生成的骨架。\n",
        f"src/{package}/__init__.py": f'"""{package} 包。"""\n\n__version__ = "0.1.0"\n',
        "tests/test_smoke.py": (
            '"""最小的冒烟测试：先确认能 import，再谈别的。"""\n'
            "\n"
            f"from {package} import __version__\n"
            "\n"
            "\n"
            "def test_version() -> None:\n"
            '    assert __version__ == "0.1.0"\n'
        ),
    }

    created: list[str] = []
    for relative, content in files.items():
        path = root / relative
        # parents=True 会一路把缺的父目录建出来（src/demo/ 这种）
        # exist_ok=True 让「已经存在」不算错——脚本要能重复执行
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        created.append(path.relative_to(root).as_posix())

    return sorted(created)


# 为什么返回 as_posix() 而不是 str(path)：
#   Windows 上 relative_to 的结果是 'src\\demo\\__init__.py'，
#   Linux 上是 'src/demo/__init__.py'。测试里写死哪一种都会在
#   另一个平台上挂。as_posix() 统一成正斜杠，跨平台一致。
#
#   **「路径要不要参与比较」是个常见陷阱**：
#   如果只是拿去读文件，用原生 Path 就行；
#   一旦要写进日志、存进数据库、做断言，就该先规范化。
#
# 为什么用字典而不是四个 write_text 调用：
#   数据驱动。以后要加一个文件（比如 .gitignore、LICENSE），
#   只在字典里加一行，循环逻辑一行都不用改。


# ======================================================================
# q4 —— mock 外部依赖
# ======================================================================
def _fetch(url: str) -> dict:
    """真实的 fetch 会发网络请求。测试里绝不能被真的调用。"""
    raise RuntimeError(f"不应该真的发起请求：{url}")


def q4_use_fake_http(symbol: str) -> tuple[float, str]:
    """patch 本模块的 _fetch，用完自动还原。"""
    url = f"https://api.example.com/{symbol}"
    # patch 的目标写成 f"{__name__}._fetch"：
    #   __name__ 在直接运行本文件时是 "__main__"，被 import 时是 "solutions"。
    #   不管哪种情况，这个绝对名字都指向「当前模块里的 _fetch」。
    #   写死 "solutions._fetch" 的话，直接 Run 就会失败。
    with patch(f"{__name__}._fetch", return_value={"price": 100.0}) as mocked:
        price = _fetch(url)["price"]
        # call_args 是 unittest.mock 的调用记录：
        #   call_args[0]   位置参数元组
        #   call_args[1]   关键字参数字典
        # 想断言「有没有被调用、用什么参数调用」时用它。
        called_url = mocked.call_args[0][0]
        return price, called_url


# 三个要点：
#
# 1. **patch 的是「使用它的地方」，不是「定义它的地方」。**
#    本模块 `import` 时把 `_fetch` 这个名字绑定进了自己的命名空间，
#    所以要 patch `本模块._fetch`。
#    如果 _fetch 是从别的模块 import 来的（比如 from net import fetch），
#    那要 patch 的仍然是「本模块里的 fetch」，不是 net.fetch。
#
# 2. **patch 只在 with 块内有效。**
#    出块自动还原。测试最后那条断言就是守这个——
#    万一有人改成 patch 装饰器又改错了作用域，这条会立刻变红。
#
# 3. **能不用 mock 就不用。**
#    这道题真正更干净的做法是**依赖注入**：
#        def use_http(symbol, fetch=_fetch): ...
#    测试时传一个假函数进去，连 patch 都不需要，
#    而且调用方一眼能看出「这个依赖是可替换的」。
#    mock 是给「改不动的第三方代码」准备的最后手段。


# ======================================================================
# q5 —— 按路径动态导入
# ======================================================================
def q5_load_module_by_path(path: Path) -> object:
    """importlib.util 三步走。"""
    path = Path(path)
    # 必须先自己检查存在性！
    # spec_from_file_location **不会**验证文件是否存在，
    # 它会照样返回一个带 loader 的 spec，直到 exec_module 才炸出
    # FileNotFoundError —— 那不是我们想暴露给调用方的异常类型。
    if not path.is_file():
        raise ImportError(f"文件不存在：{path}")

    # 模块名用 path.stem（不含后缀的文件名）。它只是个标识，
    # 但要注意别和已导入的模块重名，否则可能拿到缓存里的旧模块。
    spec = importlib.util.spec_from_file_location(path.stem, path)
    if spec is None or spec.loader is None:
        # 后缀不是 .py（比如 .so 但平台不匹配）时会是 None
        raise ImportError(f"无法从 {path} 构造模块 spec")

    module = importlib.util.module_from_spec(spec)
    # exec_module 才真正执行模块代码。
    # 注意：这里**没有**把 module 放进 sys.modules，
    # 所以它不会污染全局导入缓存，重复加载也不会返回旧对象。
    # 想让它像正常 import 一样被缓存，就手动 sys.modules[spec.name] = module。
    spec.loader.exec_module(module)
    return module


# 什么时候需要这个：
#   - 插件系统：扫描插件目录，按路径加载每个 .py
#   - 配置文件指向某个脚本，运行时才决定加载哪个
#   - 测试里加载一个临时生成的模块
#
# 更规范的插件做法是用 importlib.metadata.entry_points()，
# 让插件通过 pyproject.toml 注册自己，而不是靠扫描目录——
# 扫描目录在打包安装后往往会失效（文件在 site-packages 里，不在你预期的位置）。


# ======================================================================
# q6 —— 读 pyproject.toml
# ======================================================================
def q6_read_metadata(path: Path) -> dict:
    """用 tomllib 读，然后一路 .get() 带默认值。"""
    data = tomllib.loads(Path(path).read_text(encoding="utf-8"))
    project = data.get("project", {})
    optional = project.get("optional-dependencies", {})

    return {
        "name": project.get("name", ""),
        "version": project.get("version", ""),
        # TOML 里的键是 "requires-python"（连字符），
        # Python 里习惯用下划线，在这里做一次转换，别让它漏到调用方。
        "requires_python": project.get("requires-python", ">=3.9"),
        "dev_dependencies": list(optional.get("dev", [])),
        "scripts": dict(project.get("scripts", {})),
    }


# 两个细节：
#
# 1. **tomllib.load 收的是二进制文件对象。**
#       with open("pyproject.toml", "rb") as f:
#           data = tomllib.load(f)
#    传文本对象会抛 TypeError。或者像我这样用 loads() 配 read_text()，
#    自己控制编码（TOML 规范要求必须是 UTF-8）。
#
# 2. **tomllib 只能读，不能写。**
#    这是故意的——它进标准库的目标就是「解析」，写 TOML 的需求少得多，
#    而且涉及格式保留等复杂问题。要写就装 tomli-w 或 tomlkit。
#
# 3. list(optional.get("dev", [])) 里那个 list() 不是多余的：
#    它保证返回的是**副本**，调用方改了不会影响原始数据。
#    同理 dict(project.get("scripts", {}))。防御性复制在返回
#    可变对象时是好习惯。


# ======================================================================
# q7 —— 捕获日志
# ======================================================================
class _RecordingHandler(logging.Handler):
    """把日志记录收集进列表的 Handler。

    自定义 Handler 只需要实现 emit(self, record)。
    record 上有 levelname / levelno / name / pathname / lineno /
    funcName / created 等一堆字段，还有 getMessage() 拿到格式化后的消息。
    """

    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(f"{record.levelname}:{record.getMessage()}")


def q7_capture_logs(events: list[tuple[str, str]]) -> list[str]:
    """挂一个内存 Handler，记完日志再摘掉。"""
    logger = logging.getLogger("course.q7")
    handler = _RecordingHandler()
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    # 这一行是关键：不设的话日志会往根 logger 冒泡，
    # 被默认的 lastResort handler 打到 stderr 上，污染测试输出。
    logger.propagate = False

    try:
        for level, message in events:
            # getattr(logging, "INFO") 拿到的是整数 20。
            # logger.log(级别, 消息) 是万能入口，
            # 比写一堆 if level == "info": logger.info(...) 干净。
            logger.log(getattr(logging, level.upper()), message)
        return list(handler.messages)
    finally:
        # 一定要摘掉。否则同一个 logger 被调用多次，
        # handler 越挂越多，日志会成倍重复——
        # 这是测试里非常常见的一种「越跑越慢、输出越跑越多」的 bug。
        logger.removeHandler(handler)


# 为什么不在库里调用 logging.basicConfig()：
#   那会动到**根 logger**，改变整个应用的日志行为。
#   一个库偷偷改了全局配置，是很难排查的问题。
#   库只应该 getLogger(__name__) 然后往外发，配不配、配到哪，
#   是使用它的**应用**该决定的事。


# ======================================================================
# q8 —— 校验项目元数据
# ======================================================================
_REQUIRED_FIELDS = ("name", "version", "description", "requires-python")


def q8_validate_metadata(data: dict) -> list[str]:
    """先收集问题，最后按固定顺序输出。"""
    problems: set[str] = set()

    for field in _REQUIRED_FIELDS:
        value = data.get(field)
        if value is None:
            problems.add(field)
        elif isinstance(value, str) and not value.strip():
            # 空字符串和纯空白都算缺失。
            # 只写 `if not value` 会把 0 和 False 也判成缺失，
            # 虽然这几个字段本来就该是字符串，但显式一点不容易出错。
            problems.add(field)

    name = data.get("name")
    if isinstance(name, str):
        stripped = name.strip()
        # PyPI 的规范：项目名只能用小写字母、数字、连字符和点。
        # 这里简化成「不能有大写、不能有下划线」。
        if stripped and (stripped != stripped.lower() or "_" in stripped):
            problems.add("name")

    # 最后按 _REQUIRED_FIELDS 的顺序输出，而不是按 set 的迭代顺序——
    # set 的顺序取决于哈希值，每次运行都可能不一样。
    # **返回给用户看的列表，顺序必须是确定的。**
    return [field for field in _REQUIRED_FIELDS if field in problems]


# 为什么中间用 set：
#   name 既可能因为「缺失」被加进来，也可能因为「不合法」被加进来，
#   用 set 天然去重，不用写 `if "name" not in problems`。
#
# 为什么最后又要按固定顺序过滤一遍：
#   set 的迭代顺序不保证，直接 list(set) 会让同一个输入在不同进程里
#   返回不同顺序的结果。测试会随机挂，用户也会觉得莫名其妙。
#   「内部用 set 去重，出口用有序结构排列」是个很实用的套路。


# ======================================================================
# q9 —— 跑子进程
# ======================================================================
def q9_run_command(args: list[str]) -> tuple[int, str]:
    """subprocess.run + capture_output。"""
    proc = subprocess.run(
        args,
        capture_output=True,  # 等价于 stdout=PIPE, stderr=PIPE
        text=True,  # 返回 str 而不是 bytes
        encoding="utf-8",  # 显式指定编码，别用系统默认
        errors="replace",  # 遇到解不开的字节用替代字符，别抛异常
        check=False,  # 非零退出码不抛异常（这也是默认值，写出来更明确）
    )
    return proc.returncode, (proc.stdout or "").strip()


# 逐个参数解释：
#
# capture_output=True
#     不写的话子进程的输出会直接打到你的终端上，程序拿不到。
#     很多人第一次写 subprocess 都会踩这个。
#
# text=True（老版本叫 universal_newlines=True）
#     不加就拿到 bytes，后面还得 decode。
#
# encoding="utf-8", errors="replace"
#     **Windows 上的必踩坑**。text=True 默认用 locale 编码，
#     中文 Windows 上是 GBK。如果子进程输出 UTF-8（Python 脚本默认就是），
#     轻则乱码，重则直接抛 UnicodeDecodeError。
#     errors="replace" 是兜底：真遇到解不开的字节，替换掉总比崩了强。
#
# check=False
#     这是默认值。但如果哪天有人把 check=True 加上，
#     非零退出码就会抛 CalledProcessError，这道题的测试会挂。
#     显式写出来是在说「我知道这个参数，我就是要关掉它」。
#
# strip()
#     print() 会在末尾加换行，不去掉的话每次比较都得写 "hi\n"。
#     但如果输出本身**有意义的前导空白**（比如格式化过的表格），
#     就不该 strip —— 这时候应该用 rstrip("\n") 只去尾部换行。
#     选哪个取决于你要拿这个字符串干什么。
#
# 安全提醒：**永远不要给 shell=True 拼用户输入**。
#     subprocess.run(f"ls {user_input}", shell=True)
#     用户输入 `; rm -rf /` 就完蛋了。用列表形式传参数，
#     不经过 shell，就不存在这个问题。


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def t_q1() -> None:
    assert q1_parse_version("1.4.2") == (1, 4, 2)
    assert q1_parse_version("1.2") == (1, 2, 0)
    assert q1_parse_version("3") == (3, 0, 0)
    assert q1_parse_version("v2.0.1") == (2, 0, 1)
    assert q1_parse_version("V1.0") == (1, 0, 0)
    assert q1_parse_version("10.20.30") == (10, 20, 30)

    for bad in ("1.2.3.4", "1..2", "abc", "", "1.a.3"):
        try:
            q1_parse_version(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"q1_parse_version({bad!r}) 应该抛 ValueError")


def t_q2() -> None:
    assert q2_satisfies("1.4.2", ">=1.2,<2.0") is True
    assert q2_satisfies("2.0.0", ">=1.2,<2.0") is False
    assert q2_satisfies("1.2.0", ">=1.2,<2.0") is True
    assert q2_satisfies("1.0.0", "==1.0") is True
    assert q2_satisfies("3.1.0", "") is True
    assert q2_satisfies("3.1.0", "   ") is True
    assert q2_satisfies("1.5.0", ">1.0") is True
    assert q2_satisfies("1.0.0", ">1.0") is False
    assert q2_satisfies("1.0.0", "<2.0,>=1.0") is True

    try:
        q2_satisfies("1.0.0", "~=1.0")
    except ValueError:
        pass
    else:
        raise AssertionError("不认识的运算符应该抛 ValueError")


def t_q3() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "proj"
        created = q3_scaffold(root, "demo")
        assert created == [
            "README.md",
            "pyproject.toml",
            "src/demo/__init__.py",
            "tests/test_smoke.py",
        ], created

        for rel in created:
            f = root / rel
            assert f.is_file(), f"{rel} 没有创建出来"
            assert f.read_text(encoding="utf-8").strip(), f"{rel} 是空文件"

        assert (root / "src" / "demo").is_dir()

    with tempfile.TemporaryDirectory() as tmp:
        created = q3_scaffold(Path(tmp))
        assert "src/mypkg/__init__.py" in created


def t_q4() -> None:
    price, url = q4_use_fake_http("AAPL")
    assert price == 100.0
    assert url == "https://api.example.com/AAPL"

    try:
        _fetch("https://example.com")
    except RuntimeError:
        pass
    else:
        raise AssertionError("_fetch 没有被还原，patch 泄漏了")


def t_q5() -> None:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        f = Path(tmp) / "my_plugin.py"
        f.write_text(
            "SOME_CONSTANT = 42\n\ndef double(x):\n    return x * 2\n",
            encoding="utf-8",
        )
        mod = q5_load_module_by_path(f)
        assert mod.SOME_CONSTANT == 42
        assert mod.double(21) == 42

    try:
        q5_load_module_by_path(Path("这个文件不存在.py"))
    except ImportError:
        pass
    else:
        raise AssertionError("路径不存在时应该抛 ImportError")


def t_q6() -> None:
    import tempfile

    toml_text = """
[project]
name = "demo"
version = "1.2.3"

[project.optional-dependencies]
dev = ["pytest>=8.3", "ruff>=0.8"]

[project.scripts]
demo = "demo.cli:main"
"""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "pyproject.toml"
        p.write_text(toml_text, encoding="utf-8")
        got = q6_read_metadata(p)
        assert got["name"] == "demo"
        assert got["version"] == "1.2.3"
        assert got["requires_python"] == ">=3.9", "缺失时应该给默认值"
        assert got["dev_dependencies"] == ["pytest>=8.3", "ruff>=0.8"]
        assert got["scripts"] == {"demo": "demo.cli:main"}

        p2 = Path(tmp) / "minimal.toml"
        p2.write_text('[project]\nname = "x"\n', encoding="utf-8")
        got2 = q6_read_metadata(p2)
        assert got2["dev_dependencies"] == []
        assert got2["scripts"] == {}


def t_q7() -> None:
    got = q7_capture_logs([("info", "任务已创建"), ("warning", "文件缺失")])
    assert got == ["INFO:任务已创建", "WARNING:文件缺失"], got

    assert q7_capture_logs([]) == []
    assert q7_capture_logs([("debug", "d"), ("error", "e")]) == ["DEBUG:d", "ERROR:e"]

    assert q7_capture_logs([("info", "x")]) == ["INFO:x"]


def t_q8() -> None:
    assert q8_validate_metadata({"name": "x", "version": "1.0"}) == [
        "description",
        "requires-python",
    ]
    full = {
        "name": "x",
        "version": "1.0",
        "description": "d",
        "requires-python": ">=3.9",
    }
    assert q8_validate_metadata(full) == []

    assert q8_validate_metadata({**full, "version": "  "}) == ["version"]

    assert q8_validate_metadata({**full, "name": "My_Pkg"}) == ["name"]
    assert q8_validate_metadata({**full, "name": "MyPkg"}) == ["name"]

    assert q8_validate_metadata(
        {"version": "1.0", "description": "d", "requires-python": ">=3.9"}
    ) == ["name"]

    assert q8_validate_metadata({**full, "name": "my-pkg2"}) == []


def t_q9() -> None:
    code, out = q9_run_command([sys.executable, "-c", "print('hi')"])
    assert (code, out) == (0, "hi"), (code, out)

    code, out = q9_run_command([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert (code, out) == (3, ""), (code, out)

    code, out = q9_run_command([sys.executable, "-c", "print('a'); print('b')"])
    assert code == 0
    assert out == "a\nb", repr(out)

    code, out = q9_run_command([sys.executable, "-c", "print('中文测试')"])
    assert code == 0
    assert out == "中文测试", repr(out)

    code, out = q9_run_command(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"]
    )
    assert code == 0
    assert out == "out", repr(out)


def main() -> None:
    c = Checker("模块 09 · 工程化实践 参考答案")
    c.add("q1  解析语义化版本号", t_q1)
    c.add("q2  版本约束匹配", t_q2)
    c.add("q3  搭建 src layout 骨架", t_q3)
    c.add("q4  mock 外部依赖", t_q4)
    c.add("q5  按路径动态导入模块", t_q5)
    c.add("q6  读 pyproject.toml", t_q6)
    c.add("q7  捕获日志", t_q7)
    c.add("q8  校验项目元数据", t_q8)
    c.add("q9  跑子进程并捕获输出", t_q9)
    c.run()


if __name__ == "__main__":
    main()
