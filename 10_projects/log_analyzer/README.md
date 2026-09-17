# 项目 B · 日志分析 CLI

> 目标：读一个访问日志，输出 Top IP、状态码分布、最慢的请求、错误率。
>
> ```powershell
> python solution.py sample > access.log       # 生成一份示例日志
> python solution.py summary access.log
> python solution.py top access.log --top 5
> python solution.py slow access.log --top 5
> python solution.py errors access.log
> python solution.py hourly access.log
> ```

---

## 一、为什么值得做这个

数据类工作的标准形态就三步：

```
   原始文本  ──解析──►  结构化数据  ──聚合──►  结论
   access.log          [LogEntry,...]        Top IP / 错误率
```

这个套路你做多少次都不嫌多——把「日志」换成 CSV、数据库、API 返回的 JSON，
骨架一模一样。**真正花时间的从来不是聚合，是解析**：

- 真实日志里总有几行对不上格式（被截断、是别的程序写的、编码错了）
- 时间戳格式五花八门，时区处理一不小心就错
- 字段里可能有引号和空格，简单 `split()` 会散架

这个项目的重点因此是：**让你的程序在脏数据面前活下来**。

---

## 二、日志格式

每行一条，空格分隔，六个字段：

```
2026-09-16T10:23:45Z 203.0.113.7 GET /api/users 200 1234
└────────┬─────────┘ └────┬────┘ └┬┘ └────┬────┘ └┬┘ └─┬─┘
      时间戳(UTC)       客户端IP  方法    路径    状态码 耗时(毫秒)
```

### 你要写的解析器还要负责

| 情况 | 处理 |
|------|------|
| 空行 | 跳过，不算错误 |
| 字段数量不对 | 计入「无法解析」的计数 |
| 状态码不是数字 | 计入「无法解析」 |
| 时间戳格式不对 | 计入「无法解析」 |
| 路径里有查询串 `?a=1` | 保留原样（统计时再决定要不要剥掉） |

**关键设计**：`parse_line` 遇到坏行返回 `None`，而不是抛异常。
因为「跳过坏行继续处理」才是日志分析的正确行为——
一行坏了不该让整个文件分析失败。但**坏行数必须被记录下来并报给用户**，
否则就是「静默丢数据」，那才是真正的坑。

---

## 三、要实现的聚合

| 名字 | 输出 |
|------|------|
| `summary` | 总请求数 / 独立 IP 数 / 错误率 / 平均耗时 / 时间范围 |
| `top --top N` | 请求数最多的 N 个 IP，带占比 |
| `slow --top N` | 最慢的 N 条请求（路径、耗时、状态码） |
| `errors` | 4xx / 5xx 按状态码分组计数，以及错误最多的路径 |

---

## 四、分阶段提示

### 第 1 步：数据模型和解析（1 小时）

```python
@dataclass(frozen=True)
class LogEntry:
    timestamp: datetime      # 必须是 aware（带时区）的，见下
    ip: str
    method: str
    path: str
    status: int
    duration_ms: int
```

```python
def parse_line(line: str) -> LogEntry | None: ...
```

**关于时间戳**：格式是 `2026-09-16T10:23:45Z`，末尾的 `Z` 表示 UTC。
Python 3.11+ 的 `datetime.fromisoformat` **能直接解析结尾的 Z**，
拿到的是 aware datetime。如果你在更老的版本上，要手动把 `Z` 换成 `+00:00`。

**一定要用 aware datetime**（模块 07 讲过原因）：naive 的 datetime
在比较、排序、跨时区换算时行为是错的，而且错得很隐蔽。

### 第 2 步：读文件并统计坏行（30 分钟）

```python
def load(path: Path) -> tuple[list[LogEntry], int]:
    """返回 (成功解析的条目, 无法解析的行数)"""
```

用 `path.open(encoding="utf-8")` 逐行读。**必须显式写 encoding**——
Windows 上默认是 GBK，日志里有中文就乱码。

顺便处理：文件不存在时给出友好提示而不是 traceback。

### 第 3 步：聚合函数（1 小时）

```python
def top_ips(entries, n) -> list[tuple[str, int]]: ...
def status_distribution(entries) -> dict[int, int]: ...
def slowest(entries, n) -> list[LogEntry]: ...
def error_rate(entries) -> float: ...
```

**这几个函数都应该是纯函数**——输入 `list[LogEntry]`，输出结果，
不碰文件、不 print。这样它们能被单独测试（模块 09 的核心思想）。

### 第 4 步：拼成 CLI（1 小时）

用 `argparse` 的子命令（模块 07）：

```
loganalyzer summary <文件> [--json]
loganalyzer top     <文件> [--top N] [--json]
loganalyzer slow    <文件> [--top N] [--json]
loganalyzer errors  <文件> [--top N] [--json]
loganalyzer hourly  <文件> [--json]
loganalyzer sample  [--count N]        生成示例日志到 stdout
loganalyzer test                       跑自测
```

**注意这里所有功能都是子命令，文件路径跟在子命令后面。**

一开始很容易写成 `loganalyzer <文件> <子命令>` 那种形式（文件用
`nargs="?"` 的可选位置参数）。那样在 argparse 上会踩一个老坑：

```
loganalyzer access.log summary          能跑
loganalyzer access.log summary --json   报错 unrecognized arguments: --json
loganalyzer access.log --json           报错，把文件名当成了子命令名
```

第二行为什么反直觉——子命令吃掉 `summary` 之后，剩下的 `--json`
被交给了**子解析器**，而子解析器不认识这个参数。

改成「全子命令」结构之后，每种写法都只有一个确定的结果，
用户不需要记任何特例。**少写一个子命令不值得用「行为不可预测」来换。**

### 第 5 步（进阶）：时间维度（1 小时）

- `hourly`：按小时统计请求量，用 `Counter` + 时间戳的 `strftime("%H")`
- 用 `■` 字符画一个简单的直方图

```
  09 时  ████████████████ 412
  10 时  ██████████████████████████ 673
  11 时  ████████ 208
```

---

## 五、常见坑

| 坑 | 后果 |
|----|------|
| 打开文件不写 `encoding="utf-8"` | Windows 上中文乱码 / UnicodeDecodeError |
| 用 naive datetime | 排序和比较结果错，且不易察觉 |
| 坏行直接抛异常 | 一个脏行毁掉整个分析 |
| 坏行静默丢弃 | 用户不知道数据少了，结论不可信 |
| 用 `split()` 切字段却不校验数量 | `IndexError` |
| 聚合函数里直接 `print` | 没法测试，也没法输出 JSON |

---

## 六、验收标准

- [ ] 能处理**含坏行**的日志，并报告坏行数
- [ ] 文件不存在时给友好提示，退出码非 0
- [ ] `summary` 输出的错误率正确（4xx + 5xx 除以总数）
- [ ] 时间戳是 aware datetime
- [ ] 所有聚合函数是纯函数，可单独调用
- [ ] `--json` 输出能被 `json.loads` 解析
- [ ] 文件用 `encoding="utf-8"` 打开
