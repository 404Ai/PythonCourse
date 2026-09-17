# 模块 06 · 异常与文件 IO

> **目标**：写出「出错时行为可预测」的代码，以及「换台机器也不会乱码」的文件读写。
>
> 这个模块不教你 `try` 的语法——你在 C++ / Java 里早就写腻了。
> 它讲的是 Python 的异常**体系设计**、**执行顺序的精确语义**，
> 以及为什么别人 review 你的代码时看到 `except Exception: pass` 会直接打回。

---

## 6.1 异常层次结构：为什么不要捕获 `BaseException`

### 完整的树（精简版）

```
BaseException
├── SystemExit              sys.exit() 抛的东西
├── KeyboardInterrupt       Ctrl+C 抛的东西
├── GeneratorExit           生成器被 close() 时抛的东西
├── Exception               ← 你写的所有代码都应该在这棵子树下
│   ├── ArithmeticError
│   │   ├── ZeroDivisionError
│   │   ├── OverflowError
│   │   └── FloatingPointError
│   ├── LookupError
│   │   ├── IndexError
│   │   └── KeyError
│   ├── OSError             （IOError / WindowsError 都是它的别名）
│   │   ├── FileNotFoundError
│   │   ├── PermissionError
│   │   ├── FileExistsError
│   │   ├── IsADirectoryError
│   │   └── TimeoutError
│   ├── ValueError
│   │   └── UnicodeError
│   │       ├── UnicodeDecodeError
│   │       └── UnicodeEncodeError
│   ├── TypeError
│   ├── AttributeError
│   ├── ImportError
│   │   └── ModuleNotFoundError
│   ├── RuntimeError
│   │   └── RecursionError
│   ├── StopIteration
│   ├── AssertionError
│   └── ...
└── BaseExceptionGroup      3.11+，except* 用
```

两个必须记住的事实：

**① `Exception` 和 `SystemExit` / `KeyboardInterrupt` 是兄弟，不是父子。**

```python
issubclass(KeyboardInterrupt, Exception)   # False
issubclass(KeyboardInterrupt, BaseException)  # True
```

**② 这就是为什么 `except BaseException:` 是灾难。**

```python
try:
    while True:
        do_work()
except BaseException:      # 灾难写法
    pass
```

用户按了 Ctrl+C，`KeyboardInterrupt` 被吞掉，循环**停不下来**，
只能去任务管理器杀进程。

同样的写法还会吞掉 `SystemExit`——如果这段代码在一个库函数里，
调用方的 `sys.exit(1)` 会被你吃掉，进程带着「成功」的状态码退出，
CI 里表现为「测试明明失败了却报绿」。

**规则**：

| 你想干什么 | 写什么 |
|-----------|--------|
| 处理业务错误 | `except SomeError:` |
| 兜底所有「正常」错误 | `except Exception:` |
| 清理资源后继续往上抛 | `finally:` 或 `except BaseException: ... raise` |
| 真的想连 Ctrl+C 都吞 | 几乎不存在这种需求 |

> 唯一合理地写 `except BaseException` 的地方是**清理 + 重抛**：
> ```python
> try:
>     ...
> finally:
>     cleanup()
> ```
> 用 `finally` 就够了，不需要 `except`。

### 别用异常做流程控制之外的用途

```python
# 反例：用异常判断字典有没有键
try:
    value = d["key"]
except KeyError:
    value = default

# 正例：dict 自己提供了这个 API
value = d.get("key", default)
```

`d[key]` 和 `d.get(key)` 在 CPython 里都是**一次哈希查找**，
用异常版本不会更快，只会更难读。

---

## 6.2 `try / except / else / finally` 的精确执行顺序

### 四块各自负责什么

| 块 | 什么时候执行 | 用途 |
|----|-------------|------|
| `try` | 总是先执行 | 放「可能出错的代码」 |
| `except X` | `try` 里抛出 X（或子类）时执行 | 处理错误 |
| `else` | `try` **没有**抛异常时执行 | 放「只有成功后才该做的事」 |
| `finally` | **无论如何**都执行 | 释放资源、清理状态 |

**关键点一：`else` 里的异常不会被同一个 `try` 的 `except` 捕获。**

这是 `else` 存在的**唯一理由**。对比一下：

```python
# 错的：process() 抛的 ValueError 会被当成 read() 的错误处理掉
try:
    data = read()
    process(data)          # 这个也可能抛 ValueError
except ValueError:
    print("读取失败")       # 结果把它误报成读取失败

# 对的：
try:
    data = read()
except ValueError:
    print("读取失败")       # 只处理 read 的错误
else:
    process(data)          # 这里的异常会正常往上抛
```

**关键点二：`finally` 在 `return` 之前执行。**

```python
def f():
    try:
        return "try 里的返回值"
    finally:
        print("finally 先跑")
```

调用 `f()` 会先打印 `finally 先跑`，然后返回 `"try 里的返回值"`。
流程是：算出返回值 → 暂存 → 跑 `finally` → 真正返回。

**推论：`finally` 里的 `return` 会覆盖 `try` 里的 `return`。**

```python
def bad():
    try:
        return 1
    finally:
        return 2       # 永远返回 2

bad()   # 2，不是 1
```

这是 Python 里最阴险的 bug 之一：它**不报错**，只是行为和你写的完全不一样。

> **Python 3.13 起，这段代码会触发 `SyntaxWarning: 'return' in a 'finally' block`，
> 官方明确表示未来会升级成 `SyntaxError`。** `break` 和 `continue` 同理。
> 也就是说这个语言设计错误正在被逐步封死——
> 但你的代码库里如果还有 3.13 之前写的东西，赶紧用
> `python -W error::SyntaxWarning` 扫一遍。
> 本模块的 `demo.py` 里那段反例是用 `exec` 在运行时编译的，
> 就是为了不污染文件的编译结果。

所以——**永远不要在 `finally` 里写 `return` / `break` / `continue`**。

**关键点三：`finally` 里 `raise` 会吞掉原始异常。**

```python
def worse():
    try:
        raise ValueError("原始错误")
    finally:
        raise RuntimeError("清理时又炸了")
```

调用方只会看到 `RuntimeError`，`ValueError` 变成了 `__context__`（见 6.4）。
排查问题时这个原始错误往往才是关键，被藏起来会让你多花两小时。

### 完整流程图

```
                ┌──────────────┐
                │  执行 try 块  │
                └──────┬───────┘
                       │
          ┌────────────┴────────────┐
          │                         │
      抛异常了                   正常结束
          │                         │
          ▼                         ▼
   ┌─────────────┐           ┌─────────────┐
   │ except 匹配？│            │  执行 else  │
   └──┬───────┬──┘           └──────┬──────┘
      │是     │否                   │
      ▼       │                     │
 ┌─────────┐  │                     │
 │执行 except│ │                    │
 └────┬────┘  │                     │
      │       │ 异常继续传播（但不执行 else）│
      └───────┴──────────┬──────────┘
                         ▼
                  ┌─────────────┐
                  │  执行 finally │   ← 一定执行
                  └──────┬──────┘
                         ▼
                     继续传播 / 返回
```

> 注意：如果 `except` 块里又抛了新异常，或者异常没被匹配上，
> `finally` 仍然会执行，然后新异常继续往上传播。

---

## 6.3 EAFP vs LBYL：以及「异常不是免费的」

### 两种哲学

**LBYL**（Look Before You Leap，先检查再动手）—— 这是 C / Java 的习惯：

```c
if (fopen_s(&fp, "data.txt", "r") == 0) {
    // 再读
}
```

```python
# Python 里的 LBYL 写法
import os

if os.path.exists(path) and os.access(path, os.R_OK):
    with open(path) as f:
        data = f.read()
else:
    data = ""
```

**EAFP**（Easier to Ask Forgiveness than Permission，先做错了再道歉）——
这是 Python 的习惯：

```python
try:
    with open(path, encoding="utf-8") as f:
        data = f.read()
except OSError:
    data = ""
```

### 为什么 Python 推荐 EAFP

**① LBYL 有 TOCTOU 竞态（Time-Of-Check to Time-Of-Use）。**

你的 `os.path.exists()` 返回 `True`，但到你真正 `open()` 之间，
另一个进程可能已经把文件删了。检查和使用之间永远有一个窗口。

EAFP 没有这个窗口：**操作本身就是检查**。

**② LBYL 要求你知道所有失败模式。**

```python
# LBYL 版要检查多少东西？
if os.path.exists(path):                     # 存在？
    if os.access(path, os.R_OK):             # 可读？
        if os.path.isfile(path):             # 是个文件不是目录？
            if not os.path.islink(path):     # 不是坏软链？
                ...
```

而实际失败原因可能是：文件被占用（Windows）、编码不对、
路径长度超限、网络盘断开、权限被 ACL 拒绝……
**你不可能枚举完**，漏掉一个就是未捕获的异常。EAFP 把它们全交给 `except`。

**③ 检查本身可能比操作还贵。**

```python
# 要先扫一遍整个文件，再读一遍
if text.count(",") > 0: ...
```

### 但：「异常不是免费的」

这是 EAFP 被滥用最厉害的地方。**在 CPython 上，抛出并捕获一个异常的代价
大约是几十到上百纳秒，比一次普通的属性访问贵 100 倍以上。**
（准确数字随版本变化，但数量级是这样的。）

```python
# 常见错误：把异常当 if 用，而且在热循环里
total = 0
for token in tokens:          # tokens 里有 90% 是合法数字
    try:
        total += int(token)
    except ValueError:        # 90% 都走正常的快路径？不，10% 走慢路径，还好
        pass
```

什么时候 EAFP 会真的伤性能？**当「异常路径」变成常态时：**

```python
# 反例：这个循环里 99% 的迭代都会抛异常
for key in keys:
    try:
        result.append(table[key])
    except KeyError:
        result.append(None)

# 正例：用 get() 或 defaultdict，没有任何异常开销
for key in keys:
    result.append(table.get(key))
```

**决策规则**：

| 场景 | 选择 |
|------|------|
| 失败是**罕见**的例外情况 | EAFP（`try/except`） |
| 失败是**常态**（> 10% 左右） | LBYL 或换 API（`get` / `defaultdict` / `setdefault`） |
| 存在 TOCTOU 风险（文件、网络、并发） | EAFP，没有第二个选择 |
| 只是想给个默认值 | 用容器自带的 API，别用异常 |

一句话：**EAFP 是「出错时该怎么办」的哲学，不是「用异常替代 if」的许可证。**

---

## 6.4 异常链：`raise ... from ...` / `__cause__` / `__context__`

### 问题：包装异常时原始信息去哪了

```python
def load_config(path):
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        raise ConfigError("配置加载失败")     # 原始错误没了！
```

调用方只看到 `ConfigError: 配置加载失败`。
到底是文件不存在、没权限、还是网络盘断了？**看不到。**
排查时你只知道「加载失败了」，这几乎等于没有信息。

### 两种链

Python 有**两条**链，别搞混：

```python
# 1. 隐式链：在 except 块里 raise，Python 自动设置 __context__
try:
    int("abc")
except ValueError:
    raise RuntimeError("转换失败")

# exc.__context__  -> ValueError("invalid literal for int()...")
# exc.__cause__    -> None
```

```python
# 2. 显式链：用 from 指定因果，设置 __cause__
try:
    int("abc")
except ValueError as exc:
    raise RuntimeError("转换失败") from exc

# exc.__cause__    -> ValueError(...)
# exc.__context__  -> ValueError(...)   两者都是它
```

**区别在显示和语义**：

| | `__cause__`（`from exc`） | `__context__`（隐式） |
|---|---|---|
| 谁设置的 | 你，显式 | Python，自动 |
| 语义 | 「我**因为**这个错误才抛新错误」 | 「我是在处理这个错误时**顺便**抛了新错误」 |
| traceback 措辞 | `The above exception was the direct cause of ...` | `During handling of the above exception, another exception occurred` |

**实践规则：包装底层异常时一律写 `from exc`。**
它让 traceback 明确地说「这是因果」，而不是含糊的「处理过程中又出事了」。

### 断链：`raise ... from None`

有时候底层异常对调用方是**实现细节**，暴露出来只会造成困惑：

```python
class Config:
    def __getitem__(self, key):
        try:
            return self._data[key]
        except KeyError:
            raise ConfigKeyError(key) from None    # 藏掉 KeyError
```

`from None` 会把 `__suppress_context__` 设为 `True`，traceback 里
不再显示 `KeyError`。**慎用**——大多数时候你还是想看到根因。

### 裸 `raise`：重抛当前异常

在 `except` 块里写 `raise`（后面什么都不跟），表示**把当前异常原样重抛**：

```python
def process(item):
    try:
        do_something(item)
    except ValueError:
        log.warning("处理 %s 失败", item)
        raise            # 正确：保留原始 traceback
```

**对比 `raise exc`（错）**：

```python
    except ValueError as exc:
        log.warning(...)
        raise exc        # 错误！多出一帧指向这一行
```

实测的差别（`traceback.extract_tb` 的帧数）：

| 写法 | traceback 帧数 | 栈底那一帧 |
|------|---------------|-----------|
| `raise` | 2 | 真正出错的 `int("abc")` |
| `raise exc` | 3 | `raise exc` 这一行本身 |

原始帧并没有被删掉，但**多出来的这一帧会让「栈底就是出错点」这个直觉失效**——
你每次排查都要多跳一层，而且 IDE 的「跳转到出错行」会定位到你的 `raise exc`，
而不是真正的故障点。日志里也会多一条没有意义的位置信息。

> 唯一的例外：你确实想改异常的类型或参数，
> 那就老老实实 `raise NewError(...) from exc`。

---

## 6.5 自定义异常：设计与实践

### 为什么继承 `Exception` 而不是 `BaseException`

只有一条理由，但它足够硬：**`except Exception` 是所有人兜底的写法。**

```python
class MyError(BaseException):   # 灾难设计
    pass
```

这样写，任何用 `except Exception` 兜底的代码都**抓不到你的异常**，
它会一路穿透到最顶层，把程序干掉。你相当于给自己造了一个
`KeyboardInterrupt` 级别的东西。

### 命名与层次设计

```python
class AppError(Exception):
    """本应用所有异常的基类。

    存在的意义：调用方可以只写 `except AppError` 就把
    「业务逻辑抛的错」和「Python 内置的错」区分开。
    """


class ConfigError(AppError):
    """配置相关错误的基类。"""


class ConfigNotFoundError(ConfigError):
    """配置文件不存在。"""


class ConfigFormatError(ConfigError):
    """配置格式非法（YAML 语法错、JSON 解析失败……）。"""


class NetworkError(AppError):
    """网络相关错误的基类。"""
```

**设计要点**：

1. **一定要有一个「根异常」**（`AppError`）。它是你这个库和外界之间的契约。
2. **中间层要抽象**（`ConfigError`），叶子要具体且携带数据。
3. **别把层次做太深**。三层（根 / 分类 / 具体）在 95% 的项目里够用了。
4. **抛异常的粒度和 except 的粒度要匹配**：你能写 `except ConfigNotFoundError`
   的地方，才有必要定义这个类。定义一堆没人 catch 的异常是在做无用功。

### 携带结构化数据

```python
class ValidationError(AppError):
    def __init__(self, field: str, message: str) -> None:
        super().__init__(f"字段 {field!r}: {message}")   # 让 str(exc) 有意义
        self.field = field          # 调用方能拿到结构化的信息
        self.message = message
```

`super().__init__(...)` 这一步**不能省**：`str(exc)` 取的是 `args[0]`，
不调用父类构造，`str(exc)` 会是空字符串，日志里什么都看不到。

### `raise ... from` 在自定义异常里的用法

```python
try:
    raw = json.loads(text)
except json.JSONDecodeError as exc:
    raise ConfigFormatError(f"配置不是合法 JSON: {exc}") from exc
```

---

## 6.6 反模式清单

### 反模式一：`except Exception: pass`

```python
# 灾难
try:
    send_report()
except Exception:
    pass
```

这段代码做了什么？**没有任何人能回答。** 它做了这些事：

- 网络断了 → 静默
- 报告里有个 `KeyError`（你的 bug）→ 静默
- 磁盘满了 → 静默
- 编码错误 → 静默
- 有人重构时打错了函数名 → 静默

然后三个月后，老板问「为什么上周的报告都没发出去」，
你打开日志，**日志里什么都没有**。

`except ...: pass` 的本质是**主动销毁证据**。

**正确写法**：

```python
try:
    send_report()
except OSError as exc:              # 1. 收窄捕获范围
    log.warning("报告发送失败，稍后重试: %s", exc)   # 2. 至少留痕
    retry_later()                    # 3. 有恢复策略
```

### 反模式二：裸 `except:`

```python
try:
    risky()
except:                # 等价于 except BaseException:
    pass
```

它连 `KeyboardInterrupt` 和 `SystemExit` 都吞。见 6.1。
**即使你要兜底，也写 `except Exception:`。**

### 反模式三：捕获了不处理也不重抛

```python
try:
    data = json.loads(text)
except json.JSONDecodeError:
    data = {}          # 然后后面用 data["key"] 时 KeyError
```

比 `pass` 好一点，但仍然是错的：**你把一个精确的错误（第 3 行 JSON 语法错）
转换成了一个模糊的错误（第 40 行 KeyError）**。

错误应该**在离它产生的地方最近处被处理**。如果你不知道该怎么处理，
就别捕获——让它往上抛，交给知道怎么处理的那一层。

### 反模式四：用异常做正常流程控制

```python
# 反例
try:
    return cache[key]
except KeyError:
    value = compute()
    cache[key] = value
    return value
```

```python
# 正例（Python 3.8+ 的 setdefault 不够用，用下面这个）
if (value := cache.get(key)) is None:
    value = compute()
    cache[key] = value
return value
```

或者干脆用 `functools.lru_cache` / `collections.defaultdict`。

### 反模式五：`finally` 里的 `return`

见 6.2。它会静默吞掉异常和返回值。

### 反模式六：异常信息写成「出错了」

```python
raise ValueError("参数错误")                    # 调用方：哪个参数？为什么错？
raise ValueError(f"age 必须是 0~150 的整数，收到 {age!r}")   # 好得多
```

异常消息是**写给未来半夜三点被叫起来排查问题的自己看的**。

---

## 6.7 `pathlib.Path`：全面替代 `os.path`

### 为什么

```python
# os.path 版：路径是字符串，靠一堆函数拼
import os

base = "data"
sub = "2024"
full = os.path.join(base, sub, "report.csv")
name = os.path.splitext(os.path.basename(full))[0]
exists = os.path.isfile(full)
```

```python
# pathlib 版：路径是对象，操作用方法/运算符
from pathlib import Path

full = Path("data") / "2024" / "report.csv"    # / 运算符拼接
name = full.stem                                # "report"
exists = full.is_file()
```

差别不只是「更短」：

1. **`/` 运算符处理了所有平台的差异**。Windows 上 `Path("a") / "b"` 给你 `a\b`，
   Linux 上给你 `a/b`，你不用管。
2. **路径是对象，可以 `.parent` / `.suffix` / `.stem`**，不用记
   `dirname` / `basename` / `splitext` 的组合方式。
3. **方法名统一且自解释**：`is_file()` 比 `os.path.isfile()` 少一次类型转换。
4. `Path` 重载了 `/`，**从字符串拼路径的一切手写代码都是未来的 bug**。

> `c:\a` + `\b` 的手工拼接在 Windows 上看起来没事，
> 但 `"data/" + "/abs"` 会得到 `data//abs`，
> 而 `Path("data") / "/abs"` 会得到 `/abs`（后者是绝对路径，直接覆盖前者）。
> 这个语义差别正是 `os.path.join` 的行为，`pathlib` 忠实地保留了它。

### 构造路径

```python
from pathlib import Path

Path("data/report.csv")                 # 相对路径
Path("data") / "2024" / "report.csv"    # 用 / 拼
Path.home()                             # C:\Users\24170
Path.cwd()                              # 当前工作目录（注意：不是你脚本所在目录！）
Path(__file__).resolve().parent         # 脚本所在目录 —— 这个才是你要的
```

> **`Path.cwd()` 的坑**：它返回的是**进程的当前工作目录**，
> 取决于你从哪里启动的程序，而不是脚本在哪。
> 在 VS Code 里按 `F5` / `Ctrl+F5` 运行（工作目录 = 脚本所在目录），
> 和在别的目录用命令行运行，结果可能完全不同。
> **要引用和脚本一起分发的文件，一律用 `Path(__file__).parent`。**

### 读写文件（最常用的两个方法）

```python
p = Path("notes.txt")

text = p.read_text(encoding="utf-8")            # 一次性读全部
p.write_text("你好\n", encoding="utf-8")         # 一次性写（覆盖）

data = p.read_bytes()                           # 二进制
p.write_bytes(b"\x00\x01")
```

**注意 `encoding=` 一定要写**，理由见 6.8。

### 遍历目录

```python
p = Path(".")

p.iterdir()                    # 直接子项（文件 + 目录），返回迭代器
p.glob("*.py")                 # 当前层的 *.py
p.rglob("*.py")                # 递归所有子目录的 *.py
p.glob("**/*.py")              # 等价于 rglob("*.py")

# 常用筛选
[f for f in p.iterdir() if f.is_file()]
[f for f in p.iterdir() if f.suffix == ".py"]
sorted(p.glob("*.py"), key=lambda f: f.stat().st_size, reverse=True)
```

> **`glob("*.py")` 和 `glob("**/*.py")` 的区别**：
> 前者只看当前目录，后者递归。`rglob` 是 `**/` 前缀的语法糖。
>
> 另外 `p.rglob("*")` 会**进入** `__pycache__`、`.git` 这些目录，
> 真实项目里记得过滤掉。

### 创建与删除

```python
p.mkdir(parents=True, exist_ok=True)     # 递归创建，已存在也不报错
```

**`parents=True` 相当于 `mkdir -p`，`exist_ok=True` 相当于「别抛 FileExistsError」。**
两个都写上才是幂等的：可以安全地在程序启动时调用一百次。

```python
p.rmdir()            # 只能删空目录
p.unlink()           # 删文件（或符号链接）
p.unlink(missing_ok=True)   # 3.8+，不存在也不报错

import shutil
shutil.rmtree(p)     # 递归删除整个目录树（危险！）
```

### 路径操作

```python
p = Path("data/report.tar.gz")

p.name          # 'report.tar.gz'     文件名（含全部后缀）
p.stem          # 'report.tar'        去最后一个后缀
p.suffix        # '.gz'               最后一个后缀
p.suffixes      # ['.tar', '.gz']     全部后缀
p.parent        # Path('data')        父目录
p.parts         # ('data', 'report.tar.gz')

p.with_suffix(".csv")       # Path('data/report.tar.csv')  ← 只换最后一个后缀
p.with_name("other.txt")    # Path('data/other.txt')
p.with_stem("new")          # Path('data/new.tar.gz')      3.9+

p.resolve()                 # 绝对路径 + 解析 .. 和软链
p.is_absolute()
p.relative_to("data")       # Path('report.tar.gz')，不是子路径会抛 ValueError

p.stat().st_size            # 字节数
p.stat().st_mtime           # 修改时间（时间戳）
p.exists() / p.is_file() / p.is_dir()
```

> `with_suffix` 的坑：`Path("archive.tar.gz").with_suffix(".zip")`
> 得到的是 `archive.tar.zip`——它**只替换最后一个**后缀。
> 想去掉所有后缀要自己用 `p.name.split(".")[0]` 或者循环。

### `Path` 和字符串的互转

```python
str(p)          # 转字符串（给只接受 str 的老 API 用）
Path("a/b")     # 字符串转 Path
f"{p}"          # f-string 里直接用，会调用 __format__ -> str
```

`Path` 对象**可以直接传给 `open()`、`os.path.*`、`shutil.*`**，
它们都接受 path-like object，不需要手动 `str()`。

---

## 6.8 文件打开模式与文本编码

### 打开模式

| 模式 | 含义 | 文件不存在时 | 文件存在时 |
|------|------|-------------|-----------|
| `"r"` | 只读文本（默认） | `FileNotFoundError` | 从头读 |
| `"w"` | 只写文本 | 创建 | **清空！** |
| `"a"` | 追加文本 | 创建 | 从末尾写 |
| `"x"` | 独占创建 | 创建 | **`FileExistsError`** |
| `"r+"` | 读写 | `FileNotFoundError` | 从头读写 |
| `"rb"` / `"wb"` | 二进制 | 同上 | 同上 |

**加 `"t"` 是显式的文本模式**（`"rt"` 等价 `"r"`），
**加 `"b"` 是二进制模式**（`"rb"`）。**两者不能同时用**。

> **`"w"` 会静默清空文件**，这是新手最常见的「我的数据不见了」。
> 如果你只是想写文件但不想意外覆盖，用 `"x"`，
> 或者先 `if not p.exists():` 判断。

### 文本编码：本模块最重要的实践

**在 Windows 中文环境下，`open()` 不指定 `encoding` 时用的是 GBK（cp936）。**

在本课程的机器上验证过：

```python
>>> import locale
>>> locale.getencoding()
'cp936'
```

对比 Linux / macOS：它们的 locale 通常是 UTF-8，所以**同一个程序，
在你的 Windows 上跑没事，部署到 Linux 服务器上就炸**——或者反过来。

**具体的爆炸方式**（真实场景，不是理论）：

```python
# 你的代码
with open("data.txt") as f:        # Windows 上默认 GBK
    text = f.read()

# data.txt 是别人用 UTF-8 存的，里面有「中文」
# -> UnicodeDecodeError: 'gbk' codec can't decode byte 0xad in position 3
```

或者更隐蔽的：**不报错，但内容全是乱码**。

```python
Path("out.txt").write_text("中文", encoding="utf-8")
Path("out.txt").read_text()        # Windows 上按 GBK 解，得到 '涓枃' 之类的乱码
```

**规则（没有例外）：**

> **所有文本 IO 一律显式写 `encoding="utf-8"`。**

```python
with open("data.txt", encoding="utf-8") as f:
    text = f.read()

Path("data.txt").write_text(text, encoding="utf-8")
```

为什么选 UTF-8 而不是「让它跟随系统」：

1. UTF-8 能表示所有 Unicode 字符，GBK 表示不了 emoji 和很多生僻字
2. UTF-8 是跨平台的事实标准，你的文件可以安全地发给任何人
3. 显式写出来，读代码的人不用去猜

> **唯一不需要管 `encoding` 的地方**：`json` 模块。
> `json.dump` / `json.load` 的 `ensure_ascii` 让输出是纯 ASCII，
> 但**如果你用 `open()` 包了一层，编码还是得自己写**。
> 所以还是老实写。

### `newline` 参数：换行的三套标准

- Windows 文本文件里换行是 `\r\n`
- Unix 是 `\n`
- 老 Mac（OS 9）是 `\r`

Python 的文本模式默认开启 **universal newlines**：

```python
with open(p, encoding="utf-8") as f:
    f.read()      # 所有 \r\n 和 \r 都被翻译成 \n
```

**写**的时候，`\n` 会被翻译成 `os.linesep`（Windows 上是 `\r\n`）。

这个自动翻译大部分时候是好事，但有两个场景必须关掉：

```python
# 1. 读写 CSV —— csv 模块自己指定了 \r\n 作为行终止符，
#    再叠加一层翻译就会变成 \r\r\n
with open("data.csv", encoding="utf-8", newline="") as f:
    reader = csv.reader(f)

# 2. 你就是在处理原始换行（比如做二进制安全的文本处理、算行数）
with open("data.txt", encoding="utf-8", newline="") as f:
```

> **`csv` 模块的文档明确要求用 `newline=""`。**
> 不写的话，Windows 上写出来的 CSV 会多出 `\r`，
> Excel 打开可能没问题，但别的解析器会读出空行。

### 二进制模式

```python
with open("image.png", "rb") as f:
    magic = f.read(8)         # 读前 8 字节，检查文件头

with open("out.bin", "wb") as f:
    f.write(b"\x89PNG\r\n\x1a\n")
```

二进制模式下：

- 读写的是 `bytes`，不是 `str`，**不做任何编码转换**
- **不能指定 `encoding`**（会抛 `ValueError`）
- 没有 universal newlines 翻译

什么时候用：图片、压缩包、任何非文本文件；或者你要自己控制编码/分块。

---

## 6.9 `with` 与处理大文件

### 为什么必须用 `with`

```python
# 不要这样写
f = open("data.txt", encoding="utf-8")
text = f.read()
f.close()          # 如果 read() 抛异常，这一行永远不执行
```

```python
# 正确
with open("data.txt", encoding="utf-8") as f:
    text = f.read()
```

`with` 保证**即使块内抛异常，`f.close()` 也会执行**
（准确地说，是 `f.__exit__` 被调用，它内部会 `close()`）。

在 Windows 上这点尤其要命：**文件句柄没关，你就删不掉这个文件**
（`PermissionError`），因为 Windows 不允许删除被占用的文件。
Linux 允许，所以「在我机器上没问题」。

```python
# 反例：在 Windows 上会 PermissionError
f = open("t.txt", "w", encoding="utf-8")
f.write("x")
Path("t.txt").unlink()      # PermissionError: [WinError 32] 另一个程序正在使用此文件
```

### 一次开多个文件

```python
with (
    open("in.txt", encoding="utf-8") as fin,
    open("out.txt", "w", encoding="utf-8") as fout,
):
    for line in fin:
        fout.write(line.upper())
```

3.10 开始支持括号形式（之前的写法是 `with open(a) as x, open(b) as y:` 一行到底，
太长不好看）。

### 大文件：逐行迭代，不要 `readlines()`

```python
# 差：把整个文件读进内存，构造一个巨大的 list
lines = Path("huge.log").read_text(encoding="utf-8").splitlines()
for line in lines:
    process(line)

# 差：readlines() 同样是把整个文件变成 list
for line in open("huge.log", encoding="utf-8").readlines():
    process(line)

# 好：文件对象本身就是可迭代的，每次只读一行（内部有缓冲区，不会真的每次 syscall）
with open("huge.log", encoding="utf-8") as f:
    for line in f:
        process(line)
```

**为什么文件对象可以直接 `for`**：

`open()` 返回的 `TextIOWrapper` 实现了迭代器协议，
它内部维护一个读缓冲区（默认 8KB），每次 `__next__()` 从缓冲区里
切出一行，缓冲用完了才做一次系统调用。

所以逐行迭代**既省内存，也不比 `readlines()` 慢**——
`readlines()` 还得额外分配一个巨大的 list 并把所有字符串塞进去。

**内存对比**（一个 1GB 的日志文件）：

| 写法 | 峰值内存 |
|------|---------|
| `read()` | 1GB+（一个巨型 str） |
| `readlines()` | 1GB+（一个巨型 list + 所有行对象，实际更多） |
| `for line in f` | 约 8KB |

**逐行迭代的例外**：你需要随机访问某一行、或者要多次遍历，
那就老实读进内存。但如果你要多次遍历一个大文件，
更好的做法是先处理成结构化数据写回去。

> **`for line in f` 保留行尾的 `\n`**。
> 不想带就用 `line.rstrip("\n")`（**不要用 `line.strip()`**，
> 它会连行首的缩进一起削掉——解析缩进敏感格式时这是灾难）。

### 分块读写二进制

```python
with open("big.bin", "rb") as fin, open("copy.bin", "wb") as fout:
    while chunk := fin.read(64 * 1024):      # 海象运算符，模块 01 见过
        fout.write(chunk)
```

注意 `while chunk := fin.read(...)` 能正确终止是因为**读到最后返回 `b""`**，
空 bytes 是假值。这在文本模式下也成立（返回 `""`）。

---

## 6.10 JSON 与 CSV

### JSON：结构化数据

```python
import json

data = {"name": "张三", "scores": [90, 85], "active": True}

# 写
with open("cfg.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

# 读
with open("cfg.json", encoding="utf-8") as f:
    loaded = json.load(f)
```

**三个参数必须记住**：

| 参数 | 作用 | 什么时候用 |
|------|------|-----------|
| `ensure_ascii=False` | 中文直接写出「中文」而不是 `\u4e2d\u6587` | **几乎总是**（否则文件没法看） |
| `indent=2` | 缩进美化，方便人读和 git diff | 配置文件、要人看的文件 |
| `default=fn` | 遇到不能序列化的对象时调用 `fn(obj)` | 自定义类、`datetime`、`Decimal` |

**`ensure_ascii` 的对比**：

```python
>>> json.dumps({"a": "中"}, ensure_ascii=True)     # 默认
# 输出里「中」被替换成了它对应的 Unicode 码点转义序列（六个 ASCII 字符）
>>> json.dumps({"a": "中"}, ensure_ascii=False)
'{"a": "中"}'
```

两个都是**合法的 JSON**，反序列化后完全一样。
但前者对人的可读性是零，而且文件体积大 6 倍。

**`default=` 处理自定义类型**：

```python
from dataclasses import dataclass, asdict

@dataclass
class Point:
    x: int
    y: int

json.dumps(Point(1, 2))                       # TypeError: not JSON serializable
json.dumps(Point(1, 2), default=asdict)       # '{"x": 1, "y": 2}'  ← dataclass 直接转 dict
```

`default` 只对**无法序列化的对象**调用，且**必须是返回可序列化对象的函数**。
通用的写法：

```python
def json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return str(obj)          # 别用 float(obj)，那会丢精度
    if isinstance(obj, Path):
        return str(obj)
    if is_dataclass(obj):
        return asdict(obj)
    raise TypeError(f"不支持的类型: {type(obj).__name__}")
```

**JSON 的类型映射**（记住这张表，反序列化时你会需要）：

| Python | JSON | 反向会得到 |
|--------|------|-----------|
| `dict` | object | `dict`，**键永远是 `str`** |
| `list` / `tuple` | array | `list`（**tuple 变成 list！**） |
| `str` | string | `str` |
| `int` / `float` | number | `int` 或 `float` |
| `True` / `False` | true / false | `bool` |
| `None` | null | `None` |

**两个必须知道的坑**：

1. **JSON 的键永远是字符串。** `json.dumps({1: "a"})` 得到 `'{"1": "a"}'`，
   读回来键是 `"1"` 不是 `1`。用整数当键要自己转换。
2. **`tuple` 会变成 `list`。** 往返一圈 `(1, 2)` 变成 `[1, 2]`。
   如果你的代码依赖它是 tuple（比如要当 dict 的键），会 `TypeError: unhashable`。

**什么时候用 JSON**：配置文件、API 请求/响应、嵌套结构、
需要保留类型信息（数字 vs 字符串）的场景。

### CSV：表格数据

```python
import csv

# 读：用 DictReader，每行变成 dict
with open("users.csv", encoding="utf-8", newline="") as f:
    reader = csv.DictReader(f)
    print(reader.fieldnames)          # ['name', 'age']  第一行的表头
    for row in reader:
        print(row["name"], row["age"])   # 值全是 str！
```

**`DictReader` 的两个关键行为**：

1. **所有值都是字符串**，包括数字。要 `int(row["age"])` 自己转。
2. **缺列时填 `None`**（`restval` 默认是 `None`），
   **多出来的列会塞进一个 list**，键是 `restkey`（默认 `None`）。

```python
# 给缺列一个默认值
reader = csv.DictReader(f, restval="")     # 缺的列变成 ""
```

```python
# 写：DictWriter
with open("out.csv", "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["name", "age"])
    writer.writeheader()                 # 写表头，别忘
    writer.writerow({"name": "张三", "age": 30})
    writer.writerows(rows)               # 批量写
```

**CSV 用的时候必须注意**：

1. **`newline=""`**（见 6.8），否则 Windows 上会多出空行。
2. **`encoding="utf-8"`**，否则中文炸。
   （`utf-8-sig` 这个变体用于「给 Excel 打开」的场景，
   它会在文件开头加 BOM，Excel 才认得 UTF-8。）
3. `DictWriter.writerow` 传的 dict **缺键会抛 `ValueError`**，
   多键也会抛。要允许缺键就传 `extrasaction="ignore"` 和
   `restval=""`。
4. CSV **没有任何类型系统**——它只是一堆逗号分隔的字符串。
   空单元格和 `"0"` 在解析后是 `""` 和 `"0"`，你得自己决定空是什么意思。

### JSON vs CSV 怎么选

| | JSON | CSV |
|---|------|-----|
| 结构 | 任意嵌套 | 扁平表格（行 × 列） |
| 类型 | 有（数字/布尔/null 区分） | 全是字符串，要自己转 |
| 体积 | 大（键名每行重复） | 小 |
| 人能读 | 缩进后可以 | 可以（但列多时不行） |
| Excel 能开 | 不能直观打开 | 双击就开 |
| 适合 | 配置、API、嵌套对象 | 表格数据、日志导出、Excel 交换 |

**简单判据**：数据是「一张表」就用 CSV；数据是「一棵树」就用 JSON。

---

## 6.11 `tempfile` / `shutil` 速查

### `tempfile`

```python
import tempfile
from pathlib import Path

# 1. 临时目录：with 块结束时自动递归删除
with tempfile.TemporaryDirectory() as d:
    p = Path(d) / "test.txt"
    p.write_text("临时内容", encoding="utf-8")
    ...
# 到这里 d 已经不存在了

# 2. 临时文件：返回 (文件对象, 路径)
with tempfile.NamedTemporaryFile(mode="w", suffix=".txt",
                                 encoding="utf-8", delete=True) as f:
    f.write("内容")
    f.flush()             # 不 flush 的话别的进程读不到
    ...

# 3. 只要一个不重复的路径（文件不创建，你要自己创建）
path = Path(tempfile.mkdtemp()) / "x.txt"

# 4. 系统临时目录
tempfile.gettempdir()
```

**为什么测试里要用 `TemporaryDirectory`**：

- 测试产生的文件**不会污染项目目录**（这是本课程练习的硬性要求）
- 不依赖「上一次运行留下的文件」
- 不需要在测试末尾写清理代码——`with` 块退出时自动删，**异常退出也删**
- 可以并行跑测试而不互相踩

### `shutil`（shell utilities）

```python
import shutil

shutil.copy(src, dst)           # 复制文件（保留权限，不保留元数据）
shutil.copy2(src, dst)          # 复制文件（连修改时间一起保留，推荐）
shutil.copytree(src, dst)       # 递归复制目录
shutil.rmtree(path)             # 递归删除目录树（危险，没有回收站）
shutil.move(src, dst)           # 移动 / 重命名（跨磁盘也能用）
shutil.disk_usage(path)         # (total, used, free) 字节数
shutil.which("python")          # 在 PATH 里找可执行文件，等价于 Linux 的 which
shutil.make_archive("out", "zip", "mydir")   # 打包成 zip / tar
shutil.get_terminal_size()      # 终端宽度，做进度条/表格用
```

> **`shutil.rmtree` 是不可恢复的。** 写之前先用
> `print` 把路径打出来看一眼，一个变量拼错就是整个目录没了。
> 在代码里至少加个断言：
> ```python
> assert target.is_dir() and target != Path("/"), f"拒绝删除 {target}"
> shutil.rmtree(target)
> ```

### 三个库的分工

| 库 | 管什么 |
|----|--------|
| `pathlib` | **路径**：拼、拆、判断、遍历、简单读写 |
| `os` | 环境：`os.environ`、`os.getpid()`、`os.rename()` |
| `shutil` | **高级文件操作**：复制、移动、删除目录树、打包 |

日常代码里 **90% 的路径操作应该用 `pathlib`**，
只在 `os.environ` 和少数没有 `pathlib` 对应物的 API 上才用 `os`。

---

## 6.12 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| `except Exception: pass` | 出错了但什么都没发生，无法排查 | 至少记日志；收窄异常类型 |
| 裸 `except:` | Ctrl+C 停不下来 | 写 `except Exception:` |
| `except BaseException` | `sys.exit()` 被吞，CI 误报绿 | 只捕 `Exception` |
| `finally` 里 `return` | 静默吞掉返回值/异常（3.13+ 有 SyntaxWarning） | `finally` 只做清理 |
| `except X as e: raise e` | traceback 多出一帧，定位失真 | 用裸 `raise` |
| 包装异常不用 `from` | 看不到根因 | `raise New(...) from exc` |
| `open()` 不写 `encoding` | Windows 上用 GBK，跨平台乱码 | 永远写 `encoding="utf-8"` |
| `csv` 不加 `newline=""` | 输出多出空行 | `open(..., newline="")` |
| `readlines()` 读大文件 | 内存爆掉 | `for line in f` |
| `line.strip()` 去换行 | 把行首缩进也削了 | `line.rstrip("\n")` |
| `Path.cwd()` 当脚本目录 | 换个启动目录就找不到文件 | `Path(__file__).parent` |
| `with_suffix` 换 `.tar.gz` | 得到 `x.tar.zip` | 只换最后一个后缀，注意 |
| `json.dumps` 中文变 `\uXXXX` | 文件没法读 | `ensure_ascii=False` |
| `json` 往返后 tuple 变 list | `TypeError: unhashable` | 读回来手动 `tuple()` |
| `json` 往返后 int 键变 str | `d[1]` KeyError | 手动 `int(k)` |
| 忘了关文件 | Windows 上删不掉文件 | 一律用 `with` |
| 用异常做正常流程 | 热循环里慢几十倍 | 用 `get` / `setdefault` |

---

## 6.13 本模块文件

| 文件 | 内容 |
|------|------|
| `README.md` | 你正在看的文件 |
| `demo.py` | 12 节可运行示例，覆盖 6.1~6.11 |
| `exercises.py` | 9 道练习，全部在临时目录里跑，不留残留文件 |
| `solutions.py` | 参考答案 + 「常见错误写法错在哪」 |

### 强烈建议的学法

1. 先跑 `demo.py`。**重点是 `demo_order()` 和 `demo_encoding()` 两节**，
   前者的输出顺序你应该先猜一遍再看。
2. 在 `demo_order()` 的 `finally` 那一行下断点，按 `F5` 启动调试后单步走
   （`F10` 跳过 / `F11` 进入），在左侧「调用堆栈」面板观察它是怎么一层层展开的。
3. 做 `exercises.py`。**q6 和 q7 是重点**，它们直接对应
   「不要吞异常」和「异常链」这两个真实项目里最常被写错的点。
4. 对照 `solutions.py`，特别是每道题下面「常见错误写法」那几段。

---

## 6.14 延伸阅读

- [Python 官方教程第 8 章 · 错误和异常](https://docs.python.org/zh-cn/3/tutorial/errors.html)
- [Python 官方教程第 7 章 · 输入和输出](https://docs.python.org/zh-cn/3/tutorial/inputoutput.html) —— 文件读写
- [PEP 3134 · Exception Chaining and Embedded Tracebacks](https://peps.python.org/pep-3134/) —— `__cause__` / `__context__` 的设计动机
- [PEP 3151 · Reworking the OS and IO exception hierarchy](https://peps.python.org/pep-3151/) —— `OSError` 家族为什么长这样
- [PEP 428 · The pathlib module](https://peps.python.org/pep-0428/) —— 为什么要有 `Path`
- [PEP 686 · Make UTF-8 mode default](https://peps.python.org/pep-0686/) —— 编码这个坑官方准备怎么收场
- 《流畅的 Python》第 4 章「文本和字节序列」——**编码问题讲得最透的一章**
- [The Python Standard Library · `pathlib`](https://docs.python.org/zh-cn/3/library/pathlib.html)
- [The Python Standard Library · `csv`](https://docs.python.org/zh-cn/3/library/csv.html) —— 注意开头的 `newline=""` 警告
