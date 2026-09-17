"""
模块 09 · 工程化实践 —— 练习

这一模块的练习题都围绕「工程化的日常动作」：
版本号处理、动态导入、mock 外部依赖、读配置、抓日志、跑子进程。

全部只用标准库，不需要 pytest 也能跑。
（`tests/` 目录下的那套 pytest 测试是另一条线，两个都做。）
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 解析版本号
# ======================================================================
def q1_parse_version(text: str) -> tuple[int, int, int]:
    """把版本号字符串解析成 (主版本, 次版本, 修订号) 三元组。

    规则：
        1. 允许可选的前缀 'v' 或 'V'（'v1.2.3'）
        2. 按 '.' 切分，**不足三段补 0**（'1.2' -> (1, 2, 0)，'3' -> (3, 0, 0)）
        3. 超过三段抛 ValueError
        4. 切分后有空段（'1..2'）或不是数字，抛 ValueError

    >>> q1_parse_version("1.4.2")
    (1, 4, 2)
    >>> q1_parse_version("1.2")
    (1, 2, 0)
    >>> q1_parse_version("v2.0")
    (2, 0, 0)

    提示：'1.2' 这种省略末段的写法在 PEP 440 里是合法的，
         所以不能直接 `a, b, c = text.split('.')`——它会炸。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— 版本约束匹配
# ======================================================================
def q2_satisfies(version: str, spec: str) -> bool:
    """判断 version 是否满足 spec。

    spec 形如 ">=1.2,<2.0"，逗号分隔的多个条件必须**全部**满足。
    支持五种运算符：>=  <=  >  <  ==

    >>> q2_satisfies("1.4.2", ">=1.2,<2.0")
    True
    >>> q2_satisfies("2.0.0", ">=1.2,<2.0")
    False
    >>> q2_satisfies("1.0.0", "==1.0")
    True
    >>> q2_satisfies("3.1.0", "")
    True

    空字符串（或只有空白）表示无约束，返回 True。
    无法识别的运算符抛 ValueError。

    提示：用 q1_parse_version 把两边都变成三元组再比。
         元组比较是逐位比较的，所以 (1, 9, 9) < (2, 0, 0) 天然成立，
         不需要手动对齐位数。
    """
    raise NotImplementedError


# ======================================================================
# q3 —— 搭项目骨架
# ======================================================================
def q3_scaffold(root: Path, package: str = "mypkg") -> list[str]:
    """在 root 目录下创建一个 src layout 的项目骨架，返回**创建的文件**的相对路径列表。

    要创建这些文件（内容随意，但不能是空文件）：
        pyproject.toml
        README.md
        src/<package>/__init__.py
        tests/test_smoke.py

    返回的路径用正斜杠 '/' 分隔，按字典序排好。

    >>> q3_scaffold(Path(tmp), "demo")
    ['README.md', 'pyproject.toml', 'src/demo/__init__.py', 'tests/test_smoke.py']

    要求：
        - 父目录不存在要自动创建（用 mkdir(parents=True, exist_ok=True)）
        - 所有文件用 UTF-8 写

    提示：pathlib 的 relative_to() 配合 .as_posix() 可以把绝对路径
         转成用 '/' 分隔的相对路径——这样在 Windows 上跑出来的结果
         和 Linux 一致，测试才不会因为平台不同而挂。
    """
    raise NotImplementedError


# ======================================================================
# q4 —— mock 外部依赖
# ======================================================================
def _fetch(url: str) -> dict:
    """真实的 fetch 会发网络请求。测试里绝不能被真的调用。"""
    raise RuntimeError(f"不应该真的发起请求：{url}")


def q4_use_fake_http(symbol: str) -> tuple[float, str]:
    """在不真的发请求的前提下，返回 (价格, 请求的 URL)。

    要求：
        1. 用 unittest.mock.patch 把本模块的 `_fetch` 替换成假的
        2. 假 _fetch 无论传什么 url，都返回 {"price": 100.0}
        3. 调用一次 _fetch，把 url 拼成 f"https://api.example.com/{symbol}"
        4. 返回 (价格, 那个 url)
        5. **patch 必须在 with 块里**，离开 with 之后 _fetch 要恢复原样

    >>> q4_use_fake_http("AAPL")
    (100.0, 'https://api.example.com/AAPL')

    提示：patch 的目标是「用它的地方」——这里就是本模块自己的命名空间。
         用 f"{__name__}._fetch" 拿到绝对名字最稳妥。
         想知道传进去的参数，可以用 mocked.call_args 取。
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 按路径动态导入
# ======================================================================
def q5_load_module_by_path(path: Path) -> object:
    """从文件路径加载一个 Python 模块并返回模块对象。

    给定一个 .py 文件，要求能拿到它里面定义的变量和函数，
    **不需要它在一个包里面，也不改 sys.path**。

    >>> mod = q5_load_module_by_path(Path("some.py"))
    >>> mod.SOME_CONSTANT
    42

    提示：importlib.util 的三步走：
        spec = importlib.util.spec_from_file_location(名字, 路径)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    模块名字随便起一个（不要和已有模块重名），比如用文件 stem。

    ⚠ spec 或 loader 可能是 None（路径不存在、后缀不对），
      那种情况要抛 ImportError。
    """
    raise NotImplementedError


# ======================================================================
# q6 —— 读 pyproject.toml
# ======================================================================
def q6_read_metadata(path: Path) -> dict:
    """读取 pyproject.toml，返回一个整理过的字典：

        {
            "name": str,
            "version": str,
            "requires_python": str,      # 对应 requires-python，缺失时 ">=3.9"
            "dev_dependencies": list,    # [project.optional-dependencies].dev，缺失时 []
            "scripts": dict,             # [project.scripts]，缺失时 {}
        }

    要求用标准库的 tomllib。

    提示：
        - tomllib.load() 收的是**二进制文件对象**（用 "rb" 打开），
          不是文本对象。或者用 tomllib.loads(路径.read_text(...))。
        - 嵌套表的取值路径形如 data["project"]["optional-dependencies"]["dev"]，
          但中间任何一层都可能不存在，注意给默认值。
    """
    raise NotImplementedError


# ======================================================================
# q7 —— 捕获日志
# ======================================================================
def q7_capture_logs(events: list[tuple[str, str]]) -> list[str]:
    """把 events 里的事件依次记到日志里，然后返回抓到的日志内容。

    events 是 [(级别名, 消息), ...]，级别名取 "debug"/"info"/"warning"/"error"。

    返回 ["级别名大写:消息", ...]，顺序和 events 一致。

    >>> q7_capture_logs([("info", "任务已创建"), ("warning", "文件缺失")])
    ['INFO:任务已创建', 'WARNING:文件缺失']

    ▸ 这道题的重点不是「能打印出来」，而是**日志内容能被程序读回来**——
      真实项目里断言日志就是这么做的，比去捕获 stderr 干净得多。

    提示：
        1. 写一个继承 logging.Handler 的类，在 emit(self, record) 里
           把 record.levelname 和 record.getMessage() 存进列表
        2. logging.getLogger("q7") 拿一个自己的 logger，
           addHandler 挂上去，setLevel(logging.DEBUG)
        3. **一定要设 logger.propagate = False**，否则日志会往根 logger
           冒泡，被默认的 lastResort handler 打到屏幕上，输出会变脏
        4. 级别是字符串，要用 getattr(logging, level.upper()) 拿到对应的整数
        5. 用完 removeHandler，别把 handler 留在 logger 上污染后面的调用
    """
    raise NotImplementedError


# ======================================================================
# q8 —— 校验项目元数据
# ======================================================================
_REQUIRED_FIELDS = ("name", "version", "description", "requires-python")


def q8_validate_metadata(data: dict) -> list[str]:
    """检查 [project] 表里的必需字段，返回**缺失或值为空**的字段名。

    返回顺序和 _REQUIRED_FIELDS 一致（不要用 set，顺序会乱）。

    >>> q8_validate_metadata({"name": "x", "version": "1.0"})
    ['description', 'requires-python']
    >>> q8_validate_metadata({"name": "x", "version": "1.0",
    ...                       "description": "d", "requires-python": ">=3.9"})
    []

    另外还要检查 name 的合法性：
        如果 name 含大写字母或下划线，把 "name" 也算进结果里
        （PyPI 要求项目名只能用小写字母、数字、连字符）

    >>> q8_validate_metadata({"name": "My_Pkg", "version": "1.0",
    ...                       "description": "d", "requires-python": ">=3.9"})
    ['name']

    注意：如果真的缺 name，只需要在结果里出现一次 "name"。
    """
    raise NotImplementedError


# ======================================================================
# q9 —— 跑子进程
# ======================================================================
def q9_run_command(args: list[str]) -> tuple[int, str]:
    """执行命令，返回 (退出码, 去掉首尾空白的 stdout)。

    >>> q9_run_command([sys.executable, "-c", "print('hi')"])
    (0, 'hi')
    >>> q9_run_command([sys.executable, "-c", "import sys; sys.exit(3)"])
    (3, '')

    要求：
        - 命令失败（非零退出码）时**不要抛异常**，正常返回退出码
        - stderr 不要混进返回值
        - stdout 要去掉首尾空白

    提示：subprocess.run 默认不捕获输出。需要传 capture_output=True（3.7+）
         和 text=True 让它返回字符串而不是 bytes。
         想让它不因非零退出码抛异常，记得处理 check 参数（默认就是 False，
         但要知道这件事——很多人栽在 shell=True 和 check=True 上）。

    ⚠ Windows 上编码是个坑：如果子进程输出中文，text=True 默认会用
      系统编码（GBK）解码，遇到 UTF-8 输出就乱码或抛 UnicodeDecodeError。
      稳妥做法是显式指定 encoding="utf-8", errors="replace"。
    """
    raise NotImplementedError


# ======================================================================
# 自测
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

    # 默认包名
    with tempfile.TemporaryDirectory() as tmp:
        created = q3_scaffold(Path(tmp))
        assert "src/mypkg/__init__.py" in created


def t_q4() -> None:
    price, url = q4_use_fake_http("AAPL")
    assert price == 100.0
    assert url == "https://api.example.com/AAPL"

    # 离开函数之后 _fetch 必须恢复原样（patch 是临时的）
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

        # 全都缺失的最小项目
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

    # 连跑两次结果要一致——不能因为 handler 没清干净而翻倍
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

    # 空字符串也算缺失
    assert q8_validate_metadata({**full, "version": "  "}) == ["version"]

    # 非法名字
    assert q8_validate_metadata({**full, "name": "My_Pkg"}) == ["name"]
    assert q8_validate_metadata({**full, "name": "MyPkg"}) == ["name"]

    # 缺 name 时只出现一次
    assert q8_validate_metadata({"version": "1.0", "description": "d",
                                 "requires-python": ">=3.9"}) == ["name"]

    # 合法名字不该被误判
    assert q8_validate_metadata({**full, "name": "my-pkg2"}) == []


def t_q9() -> None:
    code, out = q9_run_command([sys.executable, "-c", "print('hi')"])
    assert (code, out) == (0, "hi"), (code, out)

    code, out = q9_run_command([sys.executable, "-c", "import sys; sys.exit(3)"])
    assert (code, out) == (3, ""), (code, out)

    # 多行输出 + 首尾空白都要处理掉
    code, out = q9_run_command([sys.executable, "-c", "print('a'); print('b')"])
    assert code == 0
    assert out == "a\nb", repr(out)

    # 中文不能乱码
    code, out = q9_run_command([sys.executable, "-c", "print('中文测试')"])
    assert code == 0
    assert out == "中文测试", repr(out)

    # stderr 不能混进 stdout
    code, out = q9_run_command(
        [sys.executable, "-c", "import sys; print('out'); print('err', file=sys.stderr)"]
    )
    assert code == 0
    assert out == "out", repr(out)


def main() -> None:
    c = Checker("模块 09 · 工程化实践 练习")
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
