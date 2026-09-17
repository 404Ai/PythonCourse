# 模块 09 · 工程化实践

> **目标**：把「能跑的脚本」变成「别人敢改、敢用的项目」。
>
> 前八个模块教你写 Python。这个模块教你**交付** Python。
> 分水岭在这里：一个人写的代码和一支队伍写的代码，
> 差别不在语法水平，而在测试、依赖管理、代码质量和构建流程上。

这个模块和前八个不一样——它包含一个**真实可运行的完整项目**：

```
09_engineering/
├── pyproject.toml          项目的单一配置入口
├── src/taskkit/            库代码
│   ├── __init__.py
│   ├── errors.py           异常层次
│   ├── models.py           Task / Priority
│   ├── store.py            JSON 持久化
│   └── cli.py              命令行入口
└── tests/                  pytest 测试
    ├── conftest.py         共享 fixture
    ├── test_models.py
    ├── test_store.py
    └── test_cli.py
```

**先把它跑起来，再回来读文档：**

```powershell
cd C:\Users\24170\Desktop\PythonCourse\09_engineering
pytest
```

---

## 9.1 虚拟环境：为什么每个项目都要一个

### 问题

```
项目 A 需要 requests 2.25（老版本 API）
项目 B 需要 requests 2.32（新版本改了行为）
```

如果都装在系统 Python 里，**必然有一个项目跑不起来**。
这就是所谓的「依赖地狱」。

### 解决：每个项目一个独立环境

```powershell
# 创建一个虚拟环境（就是一个包含独立 Python 和 site-packages 的目录）
python -m venv .venv

# 激活它
.venv\Scripts\Activate.ps1        # Windows PowerShell
source .venv/bin/activate         # macOS / Linux

# 激活后 pip install 装的东西只进这个目录
pip install requests

# 退出
deactivate
```

虚拟环境的本质很简单：**就是一个目录**，里面有
`python.exe` 的副本（或符号链接）、独立的 `Lib/site-packages/`、
以及一个 `pyvenv.cfg` 标记文件。激活的核心作用是把 `.venv\Scripts`
加到 `PATH` 最前面，让 `python` 和 `pip` 指向这个副本。

**`.venv/` 必须写进 `.gitignore`。** 它是本地产物，不该进版本库。

### VS Code 里怎么用

按 `Ctrl+Shift+P` 打开命令面板，输入 `Python: Select Interpreter`，
选课程根目录下的 `.venv\Scripts\python.exe`。

本课程已经把这个路径写进了 `.vscode/settings.json`，正常情况下
**你什么都不用做** —— 打开项目就是对的。只有在一台新机器上重装了
`.venv` 时才需要手动选一次。

选好解释器之后，VS Code 的集成终端会自动激活这个虚拟环境，
所以终端里的 `python` / `pytest` / `ruff` 都直接指向 `.venv`，
**不需要手动敲 `Activate.ps1`**。这还顺带绕开了一个 Windows 上的常见坑：
PowerShell 默认的执行策略会拦截激活脚本，报
「无法加载文件 Activate.ps1，因为在此系统上禁止运行脚本」。

本课程已经为你建好了这个 `.venv`（在课程根目录），里面装好了
`pytest` / `pytest-cov` / `ruff` / `mypy`。

### `requirements.txt` 的正确用法

```
# 不好：完全钉死，依赖的依赖还是没锁
requests==2.32.3

# 好：说明可兼容的范围
requests>=2.32,<3.0
```

```powershell
pip install -r requirements.txt      # 按文件装
pip freeze > requirements.txt        # ❌ 别这么干
```

**`pip freeze` 的坑**：它会把**所有**已安装的包都写出来，
包括你只是顺手试了一下装进来的那些，以及依赖的依赖。
生成出来的文件臃肿且不可维护。

正确做法是分开维护两个文件：

- `requirements.txt` / `pyproject.toml` 的 `dependencies`：**你直接依赖的**，写版本范围
- `requirements.lock` / `uv.lock` / `poetry.lock`：**完整锁定**，由工具自动生成，用于可复现构建

---

## 9.2 项目目录结构

### 两种布局

```
# flat layout：包直接放在项目根目录
myproject/
├── mypackage/
│   └── __init__.py
├── tests/
└── pyproject.toml

# src layout：包放在 src/ 下面（推荐）
myproject/
├── src/
│   └── mypackage/
│       └── __init__.py
├── tests/
└── pyproject.toml
```

**为什么推荐 src layout？**

它逼着你**先安装再导入**。用 flat layout 时，你在项目根目录下敲
`python`，`import mypackage` 会直接找到源码目录——即使你的
`pyproject.toml` 配置是错的，或者漏了某个文件，你也发现不了。
等打包发布出去，用户装完 import 失败，你才追悔莫及。

src layout 让「本地能跑」和「装完能跑」是同一回事。

### `__init__.py` 还需要吗

Python 3.3 引入了 **PEP 420 命名空间包**：一个目录没有 `__init__.py`
也可以被当作包导入。

那还要不要写？**要写。** 理由：

1. 没有 `__init__.py` 的目录是「命名空间包」，多个同名的会**合并**。
   如果你不小心在别处也有一个 `taskkit` 目录，两者会被缝在一起，
   出现非常诡异的导入行为。
2. `__init__.py` 是放包级文档字符串、版本号、公开 API（`__all__`）的地方。
3. 打包工具（setuptools / hatchling）默认只收录含 `__init__.py` 的目录。

**例外**：如果你确实想做插件系统、想把多个独立发布的包挂到同一个
命名空间下（比如 `mycompany.plugin_a`、`mycompany.plugin_b` 分开发布），
那才用命名空间包。

### 什么该进版本库

```
✅ 该进                          ❌ 不该进
源码（src/, tests/）             .venv/
pyproject.toml                   __pycache__/
README.md                        .pytest_cache/ .mypy_cache/ .ruff_cache/
.gitignore                       构建产物 dist/ build/
CI 配置                          .idea/
```

---

## 9.3 `pyproject.toml`：单一配置入口

以前一个 Python 项目会有一堆配置文件：`setup.py`、`setup.cfg`、
`.flake8`、`mypy.ini`、`pytest.ini`、`isort.cfg`… 每个工具一套格式。

`pyproject.toml`（PEP 518 / PEP 621）把它们统一成一个 TOML 文件：

```toml
[build-system]                 # 用什么工具构建
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]                      # 项目元数据（取代 setup.py 的 setup(...)）
name = "taskkit"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = []

[project.optional-dependencies]   # 可选依赖组
dev = ["pytest>=8.3", "ruff>=0.8"]

[project.scripts]              # 命令行入口
taskkit = "taskkit.cli:main"

[tool.pytest.ini_options]      # 各工具的配置都挂在 [tool.*] 下
[tool.ruff]
[tool.mypy]
```

### `[project.scripts]` 是怎么工作的

```toml
[project.scripts]
taskkit = "taskkit.cli:main"
```

`pip install` 时，构建工具会生成一个名为 `taskkit` 的可执行脚本，
内容是「导入 `taskkit.cli` 模块，调用它的 `main` 函数」。
所以**入口函数的返回值会被当成退出码**——这就是 `main()` 返回 `int`
而不是调用 `sys.exit()` 的原因。

### 三种安装方式

```powershell
pip install .              # 普通安装：复制到 site-packages
pip install -e .           # 可编辑安装：只建个链接，改代码立刻生效
pip install -e ".[dev]"    # 可编辑安装 + 开发依赖
```

**开发时一律用 `-e`**，否则每改一行代码都要重装一次。

> 本课程的 `pyproject.toml` 用了更省事的办法：pytest 的
> `pythonpath = ["src"]` 配置。它等价于把 `src` 加进 `sys.path`，
> 连 `pip install -e .` 都省了。适合教学和小项目；
> 真要发布的话还是应该正经安装一遍验证。

---

## 9.4 `pytest` 基础

### 为什么不用 `unittest`

```python
# unittest：要继承 TestCase，要用 self.assertEqual
import unittest

class TestMath(unittest.TestCase):
    def test_add(self):
        self.assertEqual(1 + 1, 2)

# pytest：就是普通函数 + 普通 assert
def test_add():
    assert 1 + 1 == 2
```

pytest 赢在**没有样板代码**。而且它会**重写 assert 语句**，
失败时能告诉你具体的值：

```
E       assert 3 == 4
E        +  where 3 = add(1, 2)
```

这是 `assert` 被 pytest 改写后的效果——普通 Python 的 assert
只会说「AssertionError」，什么信息都没有。

### 发现规则（按这个命名，pytest 才找得到）

| 项目 | 默认规则 |
|------|---------|
| 文件 | `test_*.py` 或 `*_test.py` |
| 类 | `Test*`（**不能有 `__init__`**） |
| 函数 | `test_*` |
| 目录 | 会递归进入，但**跳过** `node_modules`、`.venv` 等 |

### 常用断言写法

```python
assert x == y
assert x in container
assert isinstance(x, str)
assert not items

# 浮点数：永远不要用 ==
assert value == pytest.approx(0.3)

# 异常
with pytest.raises(ValueError, match="不能为空"):
    Task("")

# 警告
with pytest.warns(DeprecationWarning):
    old_function()
```

### `parametrize`：一份逻辑测多组数据

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("high", Priority.HIGH), ("HIGH", Priority.HIGH), ("  High  ", Priority.HIGH)],
)
def test_parse(raw, expected):
    assert Priority.from_str(raw) is expected
```

一条测试展开成三条，失败时 pytest 会告诉你**具体是哪组参数**挂了。
比在函数体内写 for 循环好得多——循环里第一条失败后面的就不跑了。

### 常用命令行参数

```powershell
pytest                       # 跑全部
pytest -v                    # 每条用例一行
pytest -x                    # 第一条失败就停
pytest -k "priority"         # 只跑名字含 priority 的
pytest tests/test_store.py   # 只跑一个文件
pytest -m "not slow"         # 按 marker 过滤
pytest --lf                  # 只重跑上次失败的
pytest --pdb                 # 失败时进调试器
```

> `--lf`（last failed）是日常开发中最省时间的参数：
> 改一处代码，只重跑受影响的失败用例，几秒钟就得到反馈。

---

## 9.5 `fixture`：测试的资源管理

### 问题

```python
def test_a():
    store = TaskStore(tmp_path / "db.json")   # 每个测试都要重复这几行
    store.add("甲")
    ...

def test_b():
    store = TaskStore(tmp_path / "db.json")   # 又写一遍
    ...
```

### 解决：fixture

```python
@pytest.fixture
def store(db_path):
    return TaskStore(db_path)

def test_a(store):        # 写个参数名，pytest 就把对象注入进来
    store.add("甲")
```

**fixture 的三种威力**：

1. **依赖注入**：fixture 可以依赖别的 fixture（`filled_store` 依赖 `store`），
   pytest 自动按依赖顺序构造，同一个测试里只构造一次。
2. **作用域**：`scope="function"`（默认）/ `"class"` / `"module"` / `"session"`。
   贵重的资源（数据库连接）用 `session` 只建一次。
3. **setup/teardown**：`yield` 之前是准备，之后是清理。

```python
@pytest.fixture
def db_connection():
    conn = connect()
    yield conn                # 测试在这里跑
    conn.close()              # 无论测试成功还是失败，都会执行
```

### 四个最该记住的内置 fixture

| fixture | 作用 |
|---------|------|
| `tmp_path` | 一个**每次测试都全新**的临时目录（`pathlib.Path`）。绝不要在测试里往项目目录写文件 |
| `monkeypatch` | 临时改属性/环境变量/`sys.path`，**测试结束自动还原** |
| `capsys` | 捕获 `print` 的输出 |
| `caplog` | 捕获 `logging` 的日志 |

```python
def test_env(monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")     # 跑完自动还原
    monkeypatch.setattr("mymodule.time.time", lambda: 1000.0)
```

**`monkeypatch` 比 `unittest.mock.patch` 更推荐**，因为它会
自动清理，不需要 `with` 或装饰器，也不会因为测试失败而漏掉还原。

### `conftest.py`

放在 `tests/` 下的 `conftest.py` 会自动被 pytest 加载，
**里面的 fixture 不需要 import 就能在同目录及子目录的测试里使用。**

> 规则：被两个以上测试文件用到的 fixture 放 `conftest.py`，
> 只在一个文件里用的就写在那个文件里。别把什么都塞进 conftest。

---

## 9.6 覆盖率：数字不是目标

```powershell
pytest --cov=taskkit --cov-report=term-missing
```

```
Name                     Stmts   Miss  Cover   Missing
------------------------------------------------------
src\taskkit\__init__.py      5      0   100%
src\taskkit\cli.py          62      3    95%   88-90
src\taskkit\errors.py       12      0   100%
src\taskkit\models.py       48      1    98%   71
src\taskkit\store.py        70      2    97%   102-103
------------------------------------------------------
TOTAL                      197      6    97%
```

**`Missing` 那一列才是重点**——它告诉你哪些行从来没被执行过。

### 覆盖率能告诉你什么，不能告诉你什么

```python
def divide(a, b):
    return a / b


def test_divide():
    assert divide(6, 2) == 3        # 100% 行覆盖
```

这条测试让 `divide` 达到 100% 行覆盖，但 `divide(1, 0)` 会崩——
**你一行代码都没测到边界**。

覆盖率衡量的是「哪些代码被执行过」，**不是**「哪些情况被验证过」。
它可以告诉你哪里**没测**，但不能告诉你哪里**测好了**。

**实践建议**：

- 覆盖率低于 60% 说明测试严重不足，这是真的信号
- 追求 100% 通常是浪费，最后 10% 的代价远超收益
- **别把覆盖率当 KPI**——它会立刻诱发「写一堆不 assert 的测试」
- 真正的判据是：**改坏一处逻辑，有没有测试变红？**

---

## 9.7 `unittest.mock`：隔离外部依赖

### 什么时候要 mock

代码依赖外部世界时，测试就没法确定性地跑：

```python
def get_price(symbol):
    resp = requests.get(f"https://api.example.com/{symbol}")   # 真发请求
    return resp.json()["price"]
```

问题：慢、要网络、对方挂了测试就挂、数据每天都在变。
解决办法：把 `requests.get` **替换成一个假的**。

### 三种写法

```python
from unittest.mock import patch, MagicMock

# 1. 装饰器
@patch("mymodule.requests.get")
def test_a(mock_get):
    mock_get.return_value.json.return_value = {"price": 100}
    assert get_price("AAPL") == 100

# 2. 上下文管理器
def test_b():
    with patch("mymodule.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"price": 100}
        assert get_price("AAPL") == 100

# 3. 手动 start/stop（少用，容易忘了 stop）
```

### 最重要的一个规则：patch 的位置

> **patch 的是「使用它的地方」，不是「定义它的地方」。**

```python
# mymodule.py
import requests
def get_price(): return requests.get(...)

# ✅ 对：patch 的是 mymodule 命名空间里的那个名字
@patch("mymodule.requests.get")

# ❌ 错：这会替换 requests 模块里的属性，
#      但 mymodule 早就把函数对象绑定到自己命名空间了，替换不到
@patch("requests.get")
```

（`mymodule.requests.get` 这个看起来别扭的路径，本质上 patch 的是
「`mymodule` 模块里 `requests` 这个名字指向的对象的 `get` 属性」。）

### `MagicMock` 的特性

`MagicMock` 会自动实现魔术方法，所以它能骗过 isinstance 检查、
支持 `len()`、迭代、下标访问、上下文管理器：

```python
m = MagicMock()
len(m)          # 0
m[0]            # 另一个 MagicMock
list(m)         # []
with m:         # 正常
    pass
```

不过**别滥用**。mock 太多通常是设计有问题的信号：

> **如果你发现要 mock 五六个东西才能测一个函数，
> 那说明这个函数耦合太紧了，该重构的是产品代码，不是测试。**

依赖注入（把 `client` 作为参数传进来）通常比 patch 更干净：

```python
# 难测：函数内部自己创建依赖
def get_price(symbol):
    return requests.get(...)

# 好测：依赖从外面传进来
def get_price(symbol, http=requests):
    return http.get(...)

def test_get_price():
    assert get_price("AAPL", http=FakeHttp()) == 100   # 连 mock 都不用
```

---

## 9.8 代码质量工具

### `ruff`：lint + format 二合一

`ruff` 用 Rust 写的，比 `flake8` + `isort` + `black` 加起来快几十倍，
现在基本是 Python 社区的默认选择。

```powershell
ruff check .            # 检查
ruff check --fix .      # 自动修复能修的
ruff format .           # 格式化（等价于 black）
ruff format --diff .    # 只看看会改什么，不实际改
```

配置里那些规则集的作用：

| 代码 | 作用 | 例子 |
|------|------|------|
| `E` | pycodestyle 错误 | 多余的空格 |
| `F` | pyflakes | 未使用的导入、用了未定义的变量 |
| `I` | isort | 导入顺序 |
| `UP` | pyupgrade | `"{}".format(x)` → `f"{x}"` |
| `B` | bugbear | `def f(x=[])` 这种已知陷阱 |
| `SIM` | simplify | 可以简化的写法 |

> **`F401: imported but unused` 是最有价值的一条**。
> 未使用的导入不只是脏，它还可能掩盖真正的错误：
> 你以为在用 `from a import thing`，实际用的是别处定义的另一个 `thing`。

### `mypy`：静态类型检查

```powershell
mypy src
```

它读你的类型注解，在**不运行代码**的情况下找类型错误。
这就是模块 07 那些注解的真正用途——注解本身不影响运行，
但 `mypy` 能拿它做事。

```python
def greet(name: str) -> str:
    return f"你好，{name}"

greet(123)      # mypy: Argument 1 to "greet" has incompatible type "int"; expected "str"
                # 运行时：完全正常，照跑不误
```

**渐进的用法**：不要一上来就开 `disallow_untyped_defs = true`。
先把最核心的模块加上注解，`mypy` 只检查那几个文件，
等习惯了再逐步扩大。

### `pre-commit`：把检查自动化

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.8.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.13.0
    hooks:
      - id: mypy
```

```powershell
pip install pre-commit
pre-commit install        # 装进 .git/hooks/pre-commit
```

之后每次 `git commit`，它都会自动跑一遍检查，不合格就拒绝提交。

> **不要用 `git commit --no-verify` 绕过它。**
> 钩子失败说明代码真有问题是大概率事件；绕过一次，
> 下次就会绕第二次，这个机制就废了。

---

## 9.9 打包与发布

```powershell
pip install build
python -m build
```

产物在 `dist/` 下：

| 文件 | 是什么 | 用途 |
|------|--------|------|
| `taskkit-0.1.0.tar.gz` | **sdist**，源码包 | 用户 `pip install` 时现场构建 |
| `taskkit-0.1.0-py3-none-any.whl` | **wheel**，预构建包 | 装了就不用再构建，快 |

wheel 文件名有讲究：`py3-none-any` 表示「Python 3、无 ABI 依赖、跨平台」。
如果含 C 扩展，就会变成 `cp314-cp314-win_amd64` 这种——必须为每个
Python 版本和平台各打一个包。

```powershell
pip install twine
twine check dist/*
twine upload dist/*          # 上传到 PyPI（需要账号，慎用）
```

> **`twine upload` 是不可撤销的。** PyPI 上的文件一旦发布就不能覆盖，
> 只能发新版本。发之前务必先 `pip install dist/xxx.whl` 到干净环境里试一遍。
>
> 练习阶段用 `--repository-url https://test.pypi.org/legacy/` 传到测试仓库。

### 语义化版本（SemVer）

```
    1  .  4  .  2
    │     │     └── PATCH：修 bug，向后兼容
    │     └──────── MINOR：加功能，向后兼容
    └────────────── MAJOR：破坏性变更
```

`>=1.2,<2.0` 表示「1.2 及以上，但不要 2.0」——因为 2.0 可能有破坏性变更。

---

## 9.10 CI：让机器替你检查

`.github/workflows/test.yml`：

```yaml
name: tests

on: [push, pull_request]           # 什么时候触发

jobs:
  test:
    runs-on: ${{ matrix.os }}      # 在哪些系统上跑
    strategy:
      fail-fast: false             # 一个挂了别取消其他的
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ["3.11", "3.12", "3.13"]

    steps:
      - uses: actions/checkout@v4              # 拉代码
      - uses: actions/setup-python@v5          # 装指定版本的 Python
        with:
          python-version: ${{ matrix.python-version }}
      - name: 安装依赖
        run: |
          python -m pip install --upgrade pip
          pip install -e ".[dev]"
      - name: 静态检查
        run: |
          ruff check .
          ruff format --check .
      - name: 类型检查
        run: mypy src
      - name: 测试
        run: pytest --cov=taskkit --cov-report=xml
```

**matrix 是 CI 最有价值的部分**：一次配置，9 种组合（3 系统 × 3 版本）
同时跑。你自己的机器只能测一个环境，CI 能测九个。

> **在 Windows 上开发，一定要把 CI 配上 Linux。**
> 路径分隔符、文件名大小写敏感、换行符、编码默认值——
> 这四个坑在 Windows 上永远测不出来。

---

## 9.11 常见坑速查

| 坑 | 后果 | 正解 |
|----|------|------|
| `.venv` 提交进了 git | 仓库爆炸、别人环境被污染 | 写进 `.gitignore` |
| `pip freeze > requirements.txt` | 混入无关依赖 | 手写直接依赖，用 lock 文件锁版本 |
| 用 flat layout 且不开 `-e` | 本地能跑、装完报找不到模块 | 用 src layout |
| 测试里往项目目录写文件 | 残留污染、互相干扰 | `tmp_path` fixture |
| 测试依赖 `date.today()` | 换一天就跑挂（flaky） | `monkeypatch` 固定时间 |
| `patch("requests.get")` | 不生效 | patch **使用处**：`patch("mymodule.requests.get")` |
| mock 了五六个依赖 | 测试比产品代码还长 | 重构产品代码，改成依赖注入 |
| 把覆盖率当 KPI | 一堆不 assert 的测试 | 看「改坏逻辑会不会变红」 |
| 测试了实现细节 | 重构一次碎一片 | 测可观察行为，不测内部调用 |
| `assert x == 0.3` | 浮点比较失败 | `pytest.approx` |
| 项目根目录直接 `import` 自己的包 | 掩盖了打包配置错误 | src layout |
| 忘了 `yield` 之后写清理 | 资源泄漏 | fixture 用 `yield` 而不是 `return` |

---

## 9.12 本模块文件

| 文件 | 内容 |
|------|------|
| `pyproject.toml` | 完整可用的项目配置，每段都有注释 |
| `src/taskkit/` | 一个结构完整的库（模型 / 持久化 / CLI） |
| `tests/` | 40+ 条 pytest 测试，覆盖正常路径和错误路径 |
| `demo.py` | 可运行示例：环境、配置解析、mock、日志、跑真实工具 |
| `exercises.py` | 9 道练习 |
| `solutions.py` | 参考答案 |

### 动手清单

```powershell
cd C:\Users\24170\Desktop\PythonCourse\09_engineering

pytest                                  # 全部测试
pytest -v                               # 看清楚每条用例的名字
pytest -k "store"                       # 只跑 store 相关的
pytest --cov=taskkit --cov-report=term-missing

ruff check .                            # 看看有没有问题
ruff format --diff .                    # 看格式化会改什么

mypy src                                # 类型检查

# 亲自试一下 CLI
python -m taskkit.cli --help
python -m taskkit.cli --db demo.json add "写实验报告" -p high -d 2026-12-31 --tag 学校
python -m taskkit.cli --db demo.json list
python -m taskkit.cli --db demo.json stats
```

> 跑完记得删掉 `demo.json`。

### 故意搞破坏（最有效的学习方式）

1. 把 `models.py` 里 `tags: list[str] = field(default_factory=list)`
   改成 `tags: list[str] = []`，跑 `pytest`，看哪条测试变红
2. 把 `store.py` 的 `self.save()` 注释掉一行，看哪几条测试变红
3. 把 `cli.py` 的 `main()` 里 `out = out if out is not None else sys.stdout`
   改成 `out = sys.stdout`，看 `test_cli.py` 怎么全崩
4. 把 `errors.py` 的 `TaskNotFound(TaskKitError)` 改成继承 `KeyError`，观察变化

**这四条比读十遍文档都管用**——你会亲眼看到测试是怎么替你守住契约的。

---

## 9.13 延伸阅读

- [Python 官方打包指南](https://packaging.python.org/zh-cn/latest/) —— 打包问题查这里最权威
- [pytest 官方文档](https://docs.pytest.org/) —— 「How to invoke pytest」和「Fixtures」两章必读
- [PEP 621: 项目元数据](https://peps.python.org/pep-0621/) —— `[project]` 表的规范
- [PEP 420: 隐式命名空间包](https://peps.python.org/pep-0420/)
- [ruff 规则列表](https://docs.astral.sh/ruff/rules/) —— 按规则查「为什么这条是坏的」
- [Semantic Versioning 2.0.0](https://semver.org/lang/zh-CN/)
- 《Python 工匠：案例、技巧与工程实践》—— 中文原创，工程视角很好
