"""
模块 09 · 工程化实践 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

这个文件本身也是「工程化」的示范：
    - 需要用到 src/ 里的 taskkit 时，通过 sys.path 显式处理，不依赖运气
    - 调用外部工具（pytest / ruff / mypy）之前先检测它在不在
    - 所有外部命令的失败都被兜住，不会让 demo 崩掉
"""

from __future__ import annotations

import importlib
import importlib.util
import io
import json
import logging
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from unittest.mock import MagicMock, patch

HERE = Path(__file__).resolve().parent
SRC = HERE / "src"

# 把 src 加进模块搜索路径，等价于 pyproject.toml 里的 pythonpath = ["src"]。
# 生产代码当然应该正经 pip install，这里是为了让 demo 开箱即跑。
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


def section(title: str) -> None:
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def find_tool(name: str) -> str | None:
    """找一个可执行程序：先看当前解释器所在的目录，再查 PATH。

    为什么不能只用 shutil.which(name)：
        venv 里的 ruff.exe 只有在你**激活**了虚拟环境（Activate.ps1）时
        才会被加到 PATH 上。而在编辑器里直接按 F5 / Ctrl+F5 运行脚本时并没有激活，
        PATH 上找不到——但 `.venv\\Scripts\\ruff.exe` 明明就在那儿。

        所以正确的找法是：pip 装的命令行工具永远和 python.exe 在同一个目录
        （Windows 下是 Scripts\\，Linux 下是 bin\\）。先看那里，再退回到 PATH。
        这也顺便解释了另一个常见困惑：「我明明 pip install 了，为什么说找不到」——
        多半就是 python 和 PATH 指向了不同的环境。
    """
    suffix = ".exe" if sys.platform == "win32" else ""
    beside_python = Path(sys.executable).parent / f"{name}{suffix}"
    if beside_python.exists():
        return str(beside_python)
    return shutil.which(name)


def _real_print(msg: str) -> None:
    """demo_mock 里用来演示 patch 的靶子。

    必须是**模块级**的名字，因为 unittest.mock.patch 只能替换
    「某个模块命名空间里的属性」。函数内部的局部变量是 patch 不到的。
    """
    print(f"        [真的打印了] {msg}")


# ======================================================================
# 9.1 运行环境：你在哪个解释器里
# ======================================================================
def demo_environment() -> None:
    section("9.1 运行环境：怎么知道自己是不是在虚拟环境里")

    print(f"  sys.executable  = {sys.executable}")
    print(f"  sys.prefix      = {sys.prefix}")
    print(f"  sys.base_prefix = {sys.base_prefix}")
    print()

    in_venv = sys.prefix != sys.base_prefix
    print(f"  是否在虚拟环境中：{in_venv}")
    print("  判定方法就是比较 sys.prefix 和 sys.base_prefix：")
    print("     不在虚拟环境时两者相同；在虚拟环境里 prefix 指向 .venv 目录。")
    print()

    print("  模块搜索路径 sys.path（前 4 条）：")
    for entry in sys.path[:4]:
        print(f"     {entry or '(空字符串，表示当前目录)'}")
    print("  注意：sys.path[0] 在运行脚本时是脚本所在目录。")


# ======================================================================
# 9.2 项目结构
# ======================================================================
def demo_layout() -> None:
    section("9.2 项目结构：src layout")

    def walk(path: Path, prefix: str = "", depth: int = 0) -> None:
        if depth > 3:
            return
        skip = {
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".coverage",
            ".venv",
        }
        entries = sorted(
            (p for p in path.iterdir() if p.name not in skip),
            key=lambda p: (p.is_file(), p.name),
        )
        for index, entry in enumerate(entries):
            last = index == len(entries) - 1
            branch = "`-- " if last else "|-- "
            print(f"  {prefix}{branch}{entry.name}{'/' if entry.is_dir() else ''}")
            if entry.is_dir():
                walk(entry, prefix + ("    " if last else "|   "), depth + 1)

    walk(HERE)
    print()
    print("  几个要点：")
    print("     1. 包放在 src/ 下（src layout）—— 强迫你「先安装再导入」，")
    print("        避免本地能跑、装完却 import 失败的经典事故。")
    print("     2. 测试代码和产品代码分离，测试放在 tests/ 下。")
    print("     3. 配置只有一份：pyproject.toml，没有 setup.py / pytest.ini / mypy.ini。")
    print("     4. __pycache__ 之类的缓存目录已经在 .gitignore 里排除了。")


# ======================================================================
# 9.3 pyproject.toml
# ======================================================================
def demo_pyproject() -> None:
    section("9.3 pyproject.toml：配置只此一份")

    # tomllib 是 3.11 起进标准库的 TOML 解析器，只读不写（写要用第三方库）
    data = tomllib.loads((HERE / "pyproject.toml").read_text(encoding="utf-8"))

    print("  [project] 里的元数据：")
    project = data["project"]
    for key in ("name", "version", "description", "requires-python"):
        print(f"     {key:<16} = {project.get(key)!r}")

    print()
    print("  直接依赖（dependencies）：", project.get("dependencies") or "（无）")
    print("  开发依赖（optional-dependencies.dev）：")
    for dep in project["optional-dependencies"]["dev"]:
        print(f"     {dep}")
    print()
    print("  命令行入口（project.scripts）：")
    for name, target in project["scripts"].items():
        print(f"     {name}  ->  {target}")
    print("     装完之后终端里就有 taskkit 这个命令，它会调用 cli.main()。")
    print()

    print("  工具配置都挂在 [tool.*] 下面：")
    for tool in data.get("tool", {}):
        print(f"     [tool.{tool}]")
    print()
    print(f"  pytest 的 testpaths = {data['tool']['pytest']['ini_options']['testpaths']}")
    print(f"  pytest 的 pythonpath = {data['tool']['pytest']['ini_options']['pythonpath']}")
    print("     有了 pythonpath，就不用手动 pip install -e . 也能 import taskkit。")
    print()

    print("  用 TOML 写配置的好处：")
    print("     - 结构化（有真正的数组和嵌套表），不像 ini 只能拍平")
    print("     - 有标准规范（TOML v1.0.0），各语言解析器行为一致")
    print("     - 一个文件搞定所有工具，不用在根目录堆十个配置文件")


# ======================================================================
# 9.4 语义化版本
# ======================================================================
def demo_semver() -> None:
    section("9.4 语义化版本：>=1.2,<2.0 到底是什么意思")

    def parse(text: str) -> tuple[int, int, int]:
        """把 '1.4.2' 解析成 (1, 4, 2)。

        注意还要处理 '1.2' 这种省略了末段的写法——按 PEP 440，
        '1.2' 等价于 '1.2.0'。直接 `a, b, c = text.split(".")`
        在这里会炸掉（上次跑这个 demo 就是这么挂的）。
        """
        parts = [int(p) for p in text.split(".")]
        while len(parts) < 3:  # '1.2' -> [1, 2] -> [1, 2, 0]
            parts.append(0)
        major, minor, patch = parts[:3]
        return major, minor, patch

    def satisfies(version: str, spec: str) -> bool:
        """检查 version 是否满足 spec，支持逗号分隔的多个约束。"""
        current = parse(version)
        for clause in spec.split(","):
            clause = clause.strip()
            for op in (">=", "<=", "==", ">", "<"):
                if clause.startswith(op):
                    target = parse(clause[len(op) :])
                    ok = {
                        ">=": current >= target,
                        "<=": current <= target,
                        ">": current > target,
                        "<": current < target,
                        "==": current == target,
                    }[op]
                    if not ok:
                        return False
                    break
            else:
                raise ValueError(f"看不懂的版本约束：{clause}")
        return True

    versions = ["1.2.0", "1.4.2", "1.9.9", "2.0.0"]
    spec = ">=1.2,<2.0"
    print(f"  约束 {spec}")
    for v in versions:
        mark = "满足" if satisfies(v, spec) else "不满足"
        print(f"     {v:<8} {mark}")
    print()

    print("  三段数字的含义：")
    print("     主版本 MAJOR  有破坏性变更（1.x -> 2.x，你的代码可能要改）")
    print("     次版本 MINOR  加了新功能，向后兼容（1.2 -> 1.3，放心升）")
    print("     修订 PATCH    修 bug，向后兼容（1.4.1 -> 1.4.2，放心升）")
    print()
    print("  所以 `>=1.2,<2.0` 的意思是：1.2 以上随便升，但别跨到 2.0。")
    print()
    print("  注意元组比较是逐位比较的，所以 (1, 9, 9) < (2, 0, 0) 成立，")
    print("  不需要先补零对齐——这是 Python 元组比较天然适合干这个的原因。")


# ======================================================================
# 9.5 importlib：动态导入
# ======================================================================
def demo_importlib() -> None:
    section("9.5 importlib：按名字拿到模块")

    print("  -- 按模块名导入（import_module）--")
    models = importlib.import_module("taskkit.models")
    print(f"     importlib.import_module('taskkit.models') -> {models.__name__}")

    # 反射：拿名字当字符串用
    # noqa 是给 ruff 看的「我知道这条规则，这里是有意为之」。
    # ruff 的 B009 建议「属性名是常量字符串时别用 getattr」——一般情况下它是对的，
    # 但这一节就是在演示反射本身，所以显式豁免。**不要滥用 noqa**：
    # 每条 noqa 都应该是「我理解这条规则，且这里确实需要破例」。
    Priority = getattr(models, "Priority")  # noqa: B009
    print(f"     getattr(models, 'Priority') -> {Priority}")
    for name in ("LOW", "NORMAL", "HIGH"):
        member = getattr(Priority, name)
        print(f"     Priority.{name:<7} = {member.value}")
    print()

    print("  -- 按文件路径导入（spec_from_file_location）--")
    errors_path = SRC / "taskkit" / "errors.py"
    spec = importlib.util.spec_from_file_location("taskkit_errors_by_path", errors_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    print(f"     直接从 {errors_path.name} 加载 -> 拿到 {module.TaskKitError.__name__}")
    print()

    print("  -- 检查「能不能导入」而不真的导入（find_spec）--")
    for name in ("json", "tomllib", "pytest", "numpy"):
        try:
            found = importlib.util.find_spec(name) is not None
        except (ImportError, ValueError):
            # 模块存在但导入时报错（缺 C 依赖之类）也会走到这里
            found = False
        print(f"     import {name:<10} {'可以' if found else '不行'}")

    print()
    print("  -- 检查「命令行工具在不在」--")
    print("     注意这两件事不一样：ruff 和 mypy 是**可执行程序**，不是可导入的模块。")
    for name in ("pytest", "ruff", "mypy"):
        print(f"     {name:<10} {find_tool(name) or '找不到'}")
    print()
    print("     shutil.which 只查 PATH；而 venv 里的工具只有激活环境后才在 PATH 上。")
    print("     pip 装的命令行工具总是和 python.exe 同目录，先看那里最可靠：")
    print(f"        {Path(sys.executable).parent}")
    print()
    print("     插件系统、配置驱动的加载、可选依赖的探测，都靠这类 API。")


# ======================================================================
# 9.6 unittest.mock
# ======================================================================
def demo_mock() -> None:
    section("9.6 unittest.mock：把外部世界替换成假的")

    print("  -- 场景：一个会真发网络请求的函数 --")

    def fetch_price(symbol: str, http) -> float:
        """http 从外面传进来 —— 这叫依赖注入，可测试性的关键。"""
        response = http.get(f"https://api.example.com/{symbol}")
        return response.json()["price"]

    # 真调用会走网络。用 mock 替掉。
    fake_http = MagicMock()
    fake_http.get.return_value.json.return_value = {"price": 187.5}

    price = fetch_price("AAPL", http=fake_http)
    print(f"     fetch_price('AAPL', http=fake_http) -> {price}")
    print(f"     请求过的 URL：{fake_http.get.call_args[0][0]}")
    print(f"     http.get 被调用次数：{fake_http.get.call_count}")
    print()
    print("     MagicMock 会自动补全任意属性链：")
    print("        fake_http.get(...)          -> 另一个 MagicMock")
    print("        .json()                     -> 又一个 MagicMock")
    print("        但我们手动指定了 return_value，所以拿到的是真值。")
    print()

    print("  -- patch：临时替换掉某个名字 --")

    def noisy(msg: str) -> str:
        _real_print(msg)  # 注意：它去模块命名空间里找 _real_print
        return msg.upper()

    with patch(f"{__name__}._real_print", return_value=None) as mocked:
        result = noisy("hello")
        print(
            f"     patch 生效时 noisy('hello') 返回 {result!r}，"
            f"_real_print 被调用 {mocked.call_count} 次（真身没执行）"
        )

    print("     with 块结束后自动还原：")
    noisy("hello")
    print()
    print("  ⚠ 最容易错的一点：patch 的是**使用它的地方**，不是定义它的地方。")
    print("     错： @patch('requests.get')")
    print("     对： @patch('mymodule.requests.get')")
    print("     因为 mymodule 在 import 时就把 requests.get 绑定进自己的命名空间了。")
    print()
    print("  ⚠ 更重要的一点：**如果为了测一个函数要 mock 五六个东西，")
    print("     那问题在产品代码的耦合上，不在测试上。**")


# ======================================================================
# 9.7 logging
# ======================================================================
def demo_logging() -> None:
    section("9.7 logging：比 print 强在哪")

    logger = logging.getLogger("demo.taskkit")

    print("  -- 用一个内存 Handler 把日志抓下来 --")

    class MemoryHandler(logging.Handler):
        """把日志记录收集到列表里，而不是打到屏幕。

        写测试时就这么干——断言「有没有记日志、记了什么级别」，
        比去捕获 stderr 干净得多。
        """

        def __init__(self) -> None:
            super().__init__()
            self.records: list[logging.LogRecord] = []

        def emit(self, record: logging.LogRecord) -> None:
            self.records.append(record)

    handler = MemoryHandler()
    handler.setFormatter(logging.Formatter("%(levelname)-8s %(name)s: %(message)s"))
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False  # 别往根 logger 冒泡，免得重复输出

    logger.debug("这条只有 DEBUG 级别才看得到")
    logger.info("任务 %s 已创建", 42)
    logger.warning("存储文件缺失，已按空库处理")
    try:
        _ = 1 / 0  # 故意炸一下，演示 logger.exception
    except ZeroDivisionError:
        logger.exception("除法炸了")  # exception 会自动附上 traceback

    print(f"     抓到了 {len(handler.records)} 条记录：")
    for record in handler.records:
        print(f"        {record.levelname:<8} {record.getMessage()}")
    print()

    print("  -- 为什么不用 print --")
    print("     1. 有级别：可以整体调高调低，不用改代码")
    print("     2. 有来源：%(name)s 自动带上 logger 名字（惯例是 __name__）")
    print("     3. 有目标：同一份日志能同时进文件、进 stderr、进网络")
    print("     4. 有格式：时间戳、进程号、线程号这些都是免费的")
    print()
    print("  -- 延迟格式化 --")
    logger.info("任务 %s 已创建", 42)  # 推荐
    print("     推荐 logger.info('任务 %s 已创建', 42)，不要 logger.info(f'任务 {42} 已创建')")
    print("     前者在日志级别不够时**根本不做字符串拼接**，后者每次都要拼。")
    print("     热路径上这个差别很可观。")
    print()
    print("  -- 两个常见的错误 --")
    print("     1. 用 logging.info()（根 logger）—— 应该 getLogger(__name__)")
    print("     2. 在库里调 basicConfig() —— 那是**应用**该做的事，")
    print("        库只负责 getLogger 并往上报。")

    logger.removeHandler(handler)


# ======================================================================
# 9.8 真的跑一遍工具
# ======================================================================
def demo_tools() -> None:
    section("9.8 真的跑一遍 pytest / ruff / mypy")

    def run_tool(*args: str, timeout: int = 120) -> None:
        name = args[0]
        # 第一个参数是解释器路径或工具名。解释器直接可用；工具要先找到绝对路径。
        if Path(name).is_file():
            command = [name, *args[1:]]
        else:
            found = find_tool(name)
            if found is None:
                print(f"  [{name}] 没装。装了之后再看这一节：pip install {name}")
                return
            command = [found, *args[1:]]
        print(f"  $ {name} {' '.join(args[1:])}")
        proc = subprocess.run(
            command,
            cwd=HERE,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        output = (proc.stdout or "") + (proc.stderr or "")
        lines = [ln for ln in output.splitlines() if ln.strip()]
        for line in lines[-12:]:
            print(f"     {line}")
        print(f"     -> 退出码 {proc.returncode}")
        print()

    # sys.executable 保证用的是**当前这个**解释器，而不是 PATH 里碰巧排前面的那个
    run_tool(
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "--no-header",
        "--cov=taskkit",
        "--cov-report=term-missing",
    )
    run_tool("ruff", "check", ".")
    run_tool("ruff", "format", "--check", ".")
    run_tool("mypy", "src")

    print("  注意 `python -m pytest` 和直接敲 `pytest` 的区别：")
    print("     前者用的是 sys.executable 这个解释器，能保证和你代码跑在同一个环境里。")
    print("     VS Code 里按 F5 运行用的也是当前项目的解释器。")
    print("     混用不同环境的 pytest 是「明明装了却说找不到」的头号原因。")


# ======================================================================
# 9.9 跑一遍 CLI
# ======================================================================
def demo_cli() -> None:
    section("9.9 调用真实的 CLI")

    db = HERE / "_demo_tasks.json"
    if db.exists():
        db.unlink()

    from taskkit.cli import main

    def invoke(*argv: str) -> None:
        buffer = io.StringIO()
        code = main(["--db", str(db), *argv], out=buffer)
        for line in buffer.getvalue().splitlines():
            print(f"     {line}")
        if code != 0:
            print(f"     (退出码 {code})")

    print("  $ taskkit add '写实验报告' -p high -d 2026-12-31 --tag 学校")
    invoke("add", "写实验报告", "-p", "high", "-d", "2026-12-31", "--tag", "学校")
    print()
    print("  $ taskkit add '买牛奶' -p low")
    invoke("add", "买牛奶", "-p", "low")
    print()
    print("  $ taskkit list")
    invoke("list")
    print()
    print("  $ taskkit stats")
    invoke("stats")
    print()
    print("  $ taskkit done 2  然后  taskkit list")
    invoke("done", "2")
    invoke("list")
    print()
    print("  $ taskkit done 999   （错误路径）")
    invoke("done", "999")
    print()

    print(f"  数据文件写在这里：{db.name}")
    print("  内容：")
    payload = json.loads(db.read_text(encoding="utf-8"))
    for line in json.dumps(payload, ensure_ascii=False, indent=2).splitlines()[:12]:
        print(f"     {line}")
    print()
    print("  注意几点：")
    print("     1. main() 返回退出码而不是 sys.exit()，所以这里可以直接接住。")
    print("     2. out 参数可注入，所以输出能被 StringIO 抓住，测试同理。")
    print("     3. 出错时返回 1 并往 stderr 打一行友好提示，不甩 traceback。")
    db.unlink(missing_ok=True)


# ======================================================================
def main() -> None:
    demo_environment()
    demo_layout()
    demo_pyproject()
    demo_semver()
    demo_importlib()
    demo_mock()
    demo_logging()
    demo_tools()
    demo_cli()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
