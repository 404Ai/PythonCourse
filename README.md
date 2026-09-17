# Python 系统进阶课

[![License: CC BY-NC-SA 4.0](https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by-nc-sa/4.0/)

> 一套面向**已有编程与算法基础**的计算机系学生的 Python 课程。
> 不讲「什么是变量」，讲的是「Python 的变量为什么和 C 的变量不是一回事」。

---

## 一、这套课和你见过的教程有什么不同

网上大多数 Python 教程是「语法字典」：把 `if`、`for`、`def` 挨个讲一遍。
对已经会 C / C++ / Java 的人来说，那是在浪费时间——控制流、函数、类你都懂。

这套课的假设是：

- 你已经会写循环、递归、排序、链表，懂时间复杂度；
- 你需要的是 **Python 独有的那套东西**：名字绑定、可变对象、迭代协议、
  描述符、GIL、装饰器、上下文管理器、类型注解、打包与测试；
- 你最终要能用 Python **写出别人愿意维护的工程代码**，而不只是能跑通的脚本。

所以每个模块的结构是固定的四件套：

```
README.md      讲解：概念、原理、与 C/Java 的对照、常见坑
demo.py        可运行示例：边读边跑，看真实输出
exercises.py   练习：函数签名 + 断言自测，做不出来会提示 SKIP
solutions.py   参考答案：写完再对照，里面有「为什么这么写」的注释
```

---

## 二、本机环境

| 项目 | 值 |
|------|-----|
| Python | 3.14.7 |
| 系统解释器 | `C:\Users\24170\AppData\Local\Programs\Python\Python314\python.exe` |
| 课程虚拟环境 | `C:\Users\24170\Desktop\PythonCourse\.venv\Scripts\python.exe` |
| 编辑器 | VS Code（已装 Python / Pylance / debugpy 扩展） |
| 课程根目录 | `C:\Users\24170\Desktop\PythonCourse` |

> 课程代码全部在 **Python 3.14** 上实际运行验证过。
> 如果你的机器上 Python 版本是 3.9 及以下，部分语法（如 `match`、
> `X | Y` 类型联合、`dict` 合并运算符）会报错，建议升级。

---

## 三、课程地图

| # | 模块 | 核心内容 | 学完你应该能做到 |
|---|------|---------|-----------------|
| 01 | `01_language_core` | 执行模型、名字绑定、对象三要素、类型系统、int/float 精度、字符串格式化 | 看代码时脑子里有正确的内存图景 |
| 02 | `02_data_structures` | list/dict/set 的底层实现与复杂度、切片、解包、推导式、`collections` | 选对容器，写出 O(n) 而不是 O(n²) |
| 03 | `03_functions_scope` | 参数机制、LEGB、闭包、装饰器、`functools`、lambda 的边界 | 会写装饰器和工厂函数 |
| 04 | `04_oop` | 类与实例、MRO、魔术方法、`dataclass`、`property`、`__slots__` | 设计出符合 Python 习惯的类 |
| 05 | `05_pythonic` | 迭代器协议、生成器、上下文管理器、`itertools`、海象运算符 | 用 Python 的方式思考，而不是 C 的方式 |
| 06 | `06_errors_files` | 异常层次、EAFP vs LBYL、`pathlib`、文本编码、JSON/CSV | 写出健壮的 IO 与错误处理 |
| 07 | `07_stdlib_typing` | `typing`/泛型、`dataclasses`、`logging`、`argparse`、`re`、`datetime` | 会写带类型注解的 CLI 工具 |
| 08 | `08_concurrency_perf` | GIL 真相、`threading`/`multiprocessing`/`asyncio`、`cProfile`、复杂度实测 | 知道该用哪种并发，会定位性能瓶颈 |
| 09 | `09_engineering` | `pytest`、ruff/mypy、项目结构、`venv`、打包、Git 钩子 | 把脚本变成可发布的项目 |
| 10 | `10_projects` | 四个综合项目：表达式解释器 / 日志分析 CLI / 并发抓取器 / 算法可视化 | 独立完成一个完整程序 |

### 建议节奏

- **第 1~2 周**：模块 01–03（打地基，最容易「以为会了其实没有」）
- **第 3~4 周**：模块 04–06（面向对象与 Pythonic 风格，是分水岭）
- **第 5~6 周**：模块 07–08（标准库 + 并发，工程能力成型）
- **第 7~8 周**：模块 09–10（工程化 + 项目实战）

每个模块大约需要 3~5 小时。**不要跳过 exercises.py**，那才是真正学到东西的地方。

---

## 四、用 VS Code 打开并运行

### 1. 打开项目

VS Code 里 `File → Open Folder`，选择：

```
C:\Users\24170\Desktop\PythonCourse
```

或者在终端里：

```powershell
cd C:\Users\24170\Desktop\PythonCourse
code .
```

> **一定要打开「文件夹」，不要只打开单个 .py 文件。**
> VS Code 是围绕文件夹组织项目的。只打开一个文件的话，
> `.vscode/` 里的调试配置和任务全都不会生效，`F5` 也调不起来。

### 2. 确认解释器（一般不用管）

课程根目录下已经建好了一个虚拟环境 `.venv`，里面装好了
`pytest` / `pytest-cov` / `ruff` / `mypy`（模块 09 要用）。
`.vscode/settings.json` 已经把它设成默认解释器，**打开即用**。

只有换了新机器才需要手动确认一次：

1. 按 `Ctrl+Shift+P` 打开命令面板
2. 输入 `Python: Select Interpreter` 并回车
3. 选 `C:\Users\24170\Desktop\PythonCourse\.venv\Scripts\python.exe`

**怎么知道选对了**：看 VS Code **左下角状态栏**，显示的应该是 `.venv`，
而不是某个全局 Python。

> **模块 01~08 用哪个解释器都行**（只用标准库）。
> **模块 09 必须用 `.venv`**，因为它要跑 pytest / ruff / mypy。
>
> 想用系统解释器也行，先装依赖：
> `pip install -r requirements.txt`

### 3. 运行任意示例

打开任意 `demo.py` / `exercises.py` / `solutions.py`，然后任选一种：

| 方式 | 操作 |
|------|------|
| 右上角 ▷ 按钮 | 点一下，运行当前文件 |
| 快捷键 | `Ctrl+F5`（运行，不调试） |
| 集成终端 | `` Ctrl+` `` 打开，敲 `python 01_language_core/demo.py` |

### 4. 调试（本课程重点推荐的学法）

- 在**行号左侧**点一下 → 出现红点，就是断点（再点一下取消）
- 按 `F5` 以调试模式启动
  第一次会弹出让你选配置，选 **「调试当前文件（课程主推）」**，
  以后就不用再选了
- 常用按键：

| 按键 | 作用 |
|------|------|
| `F10` | 单步跳过（Step Over） |
| `F11` | 单步进入（Step Into） |
| `Shift + F11` | 跳出（Step Out） |
| `F5` | 继续运行到下一个断点 |
| `Shift + F5` | 停止调试 |

调试时左侧边栏会出现这些面板，本课程最常用的是前三个：

| 面板 | 用途 |
|------|------|
| 变量 VARIABLES | 看当前作用域里所有名字绑定的对象 |
| 监视 WATCH | 加入你自己关心的表达式，如 `id(a)`、`add_item.__defaults__[0]` |
| 调用堆栈 CALL STACK | 看函数是怎么一层层被调进来的 |
| 调试控制台 | 手动敲表达式求值 |

> **强烈建议**：模块 01 的 `demo_binding()` 一定要开调试器单步走一遍，
> 在「监视」面板里看 `id(a)` 和 `id(b)`，你会对「名字绑定」有肌肉记忆。
> 这比读十遍文档都管用。

### 5. 练习怎么做

```
1. 打开 moduleXX/exercises.py
2. 找到 raise NotImplementedError，把函数体换成你的实现
3. 按 Ctrl+F5 运行，看自测结果：
     [PASS] 通过
     [FAIL] 断言失败，你的实现有 bug
     [SKIP] 还没实现
     [ERROR] 抛了别的异常（看错误信息）
4. 全绿之后再打开 solutions.py 对照
```

`solutions.py` 里每个函数上面都写了**为什么这么写**，
以及常见的错误写法错在哪。

### 6. `.vscode/` 里配好了什么

课程根目录下的 `.vscode/` 有三个文件，它们让「打开就能跑、按 F5 就能调」
成为默认行为。**顺便说，这三个文件本身就是模块 09「工程化」的活教材** ——
把「怎么运行这个项目」写进版本库，而不是靠口头交代。

| 文件 | 作用 |
|------|------|
| `settings.json` | 锁定 `.venv` 解释器；让编辑器在根目录解析 `course_kit` 的导入；集成终端强制 UTF-8 |
| `launch.json` | `F5` 的调试配置 |
| `tasks.json` | 模块 09 的 pytest / ruff / mypy 任务 |

**四处特意做的设置，都值得知道为什么：**

1. **强制 UTF-8（`PYTHONUTF8=1`），否则会崩。**
   Windows 控制台的默认编码是 GBK，而本课程的输出里有中文、`ß`、`⚠` 这些
   GBK 装不下的字符。不设这个变量，模块 01 / 07 / 09 的 `demo.py` 会直接抛
   `UnicodeEncodeError` 退出 —— **不是显示成乱码，是跑不完**。

   选 `PYTHONUTF8` 而不是 `PYTHONIOENCODING`，是因为它会**被子进程继承**。
   模块 07 的 `subprocess` 演示就是子进程按 GBK 写、父进程按 UTF-8 读，
   结果读取线程直接死掉、`stdout` 变成 `None`。只改父进程的编码治不了这种问题
   —— 这正是模块 07 讲 `subprocess` 时要你记住的坑。

2. **调试输出走集成终端，而不是「调试控制台」。**
   调试控制台是纯文本视图，不接键盘输入、也不渲染 ANSI 转义序列。
   模块 10 的表达式解释器要你敲 `input()`、算法可视化要靠 ANSI 清屏做动画，
   在调试控制台里一个都跑不起来。所以 `launch.json` 里写死了
   `"console": "integratedTerminal"`。

3. **`justMyCode: false`，允许单步进入标准库。**
   默认情况下 VS Code 会跳过非你写的代码。本课程故意关掉它 ——
   你可以按 `F11` 一路钻进 `course_kit.py` 的 `Checker`、甚至标准库内部，
   亲眼看看 `list.append` 到底做了什么。这是本课程鼓励的学法。

4. **工作目录 = 脚本所在目录。**
   VS Code 默认把工作目录设成**项目根目录**，而脚本的默认行为
   （以及模块 06 讲的 `Path.cwd()` 那个坑）是按**脚本所在目录**理解。
   配置里显式写了 `"cwd": "${fileDirname}"`，
   这样在什么位置按 F5，结果都和你 `cd` 过去再运行一致。

**模块 09 的任务**（`Ctrl+Shift+P` → `Run Task` 挑一个，或按 `Ctrl+Shift+B` 直接跑测试）：

| 任务 | 等价命令 |
|------|---------|
| 09 · pytest（默认任务） | `pytest` |
| 09 · pytest + 覆盖率 | `pytest --cov=taskkit --cov-report=term-missing` |
| 09 · ruff 检查 | `ruff check .` |
| 09 · ruff 格式化 | `ruff format .` |
| 09 · mypy 类型检查 | `mypy src` |

这些任务直接调用 `.venv\Scripts\` 下的可执行文件，
所以**不依赖任何 VS Code 扩展**，也不要求你先手动激活虚拟环境。

---

## 五、环境准备

课程绝大部分内容只用标准库。模块 07–10 需要少量第三方库：

```powershell
# 在 VS Code 的集成终端里执行（Ctrl + 反引号 打开，会自动激活 .venv）
pip install pytest ruff mypy requests rich
```

对应的 `requirements.txt` 已经放在项目根目录，也可以直接：

```powershell
pip install -r requirements.txt
```

---

## 六、学习进度

打开 [`学习进度.md`](学习进度.md)，做完一个模块就勾掉一项。
进度表里还有每个模块的「自查问题」——**能不看笔记答出来**，才算真的过了。

---

## 七、目录结构

```
PythonCourse/
├── README.md              你正在看的文件
├── 学习进度.md             进度追踪 + 自查清单
├── requirements.txt       第三方依赖
├── course_kit.py          通用自测工具（所有模块共用）
├── .vscode/               VS Code 配置：解释器 / F5 调试 / pytest 任务
│   ├── settings.json      锁定 .venv、终端 UTF-8、导入路径
│   ├── launch.json        F5 的调试配置
│   └── tasks.json         pytest / ruff / mypy 任务
├── 01_language_core/      语言核心：对象模型与类型系统
│   ├── README.md
│   ├── demo.py
│   ├── exercises.py
│   └── solutions.py
├── 02_data_structures/    内置容器与 collections
├── 03_functions_scope/    函数、作用域、闭包、装饰器
├── 04_oop/                面向对象与数据模型
├── 05_pythonic/           迭代器、生成器、上下文管理器
├── 06_errors_files/       异常、文件 IO、序列化
├── 07_stdlib_typing/      标准库与类型注解
├── 08_concurrency_perf/   并发、并行与性能剖析
├── 09_engineering/        工程化：一个真实可运行的完整项目
│   ├── pyproject.toml     项目配置（PEP 621）
│   ├── src/taskkit/       库代码：模型 / 存储 / CLI
│   ├── tests/             45 条 pytest 测试
│   └── README.md          讲解 + demo.py + 练习
└── 10_projects/           四个综合项目
    ├── expr_interpreter/  表达式解释器（词法/语法/求值）
    ├── log_analyzer/      日志分析 CLI（解析/聚合/呈现）
    ├── async_crawler/     asyncio 并发抓取（限流/超时/重试）
    └── algo_visualizer/   终端 ASCII 算法动画
```

模块 01~08 是四件套（README / demo / exercises / solutions）。
模块 09 和 10 是**可运行的真实项目**，每个都带自测入口：

```powershell
cd 09_engineering        && pytest && python demo.py
cd 10_projects\expr_interpreter  && python solution.py --test
cd 10_projects\log_analyzer      && python solution.py test
cd 10_projects\async_crawler     && python solution.py test
cd 10_projects\algo_visualizer   && python solution.py test
```

---

## 八、一句忠告

> Python 最大的陷阱不是语法难，而是**它太容易写出能跑的错代码**。
>
> 一个 C 程序员写 Python，写出来的通常是「用 Python 语法写的 C」——
> 满屏的 `for i in range(len(arr))`、手写 getter/setter、到处 `try/except: pass`。
>
> 这套课的真正目标，是让你写出**像 Python 的 Python**。

---

## 九、授权协议

本项目采用 **[CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/deed.zh-hans)**
（署名 — 非商业性使用 — 相同方式共享）许可协议。

| | |
|---|---|
| **可以** | 自由学习、运行代码、做练习、修改改造、分享给同学 |
| **必须** | 注明原作者，并标明是否作出修改 |
| **不可以** | 用于商业目的（卖钱、放进付费课程、商业产品） |
| **衍生作品** | 必须沿用同样的非商业协议分发 |

一句话：**拿来学、随便改、可以传，但别拿去卖，也别改头换面说成自己的。**

完整法律条款见 [LICENSE](LICENSE)。
