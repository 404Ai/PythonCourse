# 项目 C · 并发抓取器

> 目标：用 `asyncio` 并发抓一批 URL，带**限流**、**超时**、**重试**，结果落盘。
>
> ```powershell
> python solution.py crawl --offline                      # 离线模式，不需要网络
> python solution.py crawl --offline --concurrency 3
> python solution.py crawl --urls urls.txt --concurrency 10 --out results.json
> python solution.py test
> ```
>
> **默认就是离线模式。** 内置的假 fetcher 会模拟延迟、偶发失败、
> 永久失败的地址，让你在没有任何网络依赖的情况下把并发逻辑测干净。

---

## 一、为什么值得做这个

并发是「知道概念」和「写得对」之间差距最大的地方。这几个词你大概都听过：

- **限流**：不能一次发一万个请求
- **超时**：不能有一个请求卡住就永远等下去
- **重试**：网络抖动是常态，失败两次第三次可能就成功了
- **部分失败**：10 个 URL 里挂了 3 个，剩下 7 个的结果不能丢

每个词背后都是一段容易写错的代码。**而这个项目会逼你把四个全写一遍。**

还有一个更重要的设计问题：**可测试性**。

真实的爬虫依赖网络，而网络是不可控的——对方挂了、你断网了、数据变了，
测试就会红。所以这个项目的核心设计是：

```
    crawl(urls, fetcher)          <- 只依赖一个抽象的 fetcher
                  │
      ┌───────────┴───────────┐
      ▼                       ▼
  MockFetcher            HttpFetcher
  （离线、确定性）        （真实网络）
```

`crawl` 完全不知道 fetcher 背后是网络还是假数据。
于是并发逻辑可以用假 fetcher 测得很彻底，真实 fetcher 只需要保证
「拿到 HTTP 响应并返回 (状态码, 正文)」这一件事对就行。

**这就是依赖注入的威力**——不是为了好看，是为了让最难测的那部分能测。

---

## 二、核心数据结构

```python
@dataclass
class FetchResult:
    url: str
    ok: bool                       # 最终成功了没有
    status: int | None             # HTTP 状态码
    body: str | None               # 正文（失败时为 None）
    attempts: int                  # 一共尝试了几次
    elapsed: float                 # 总耗时（秒）
    error: str | None              # 失败原因（成功时为 None）
```

**注意 `attempts` 和 `error` 字段**——它们让「重试有没有发生」「为什么失败」
变成了可断言的数据，而不是只能靠看日志猜。

---

## 三、要实现的 fetcher

### 抽象约定

一个 fetcher 就是一个可调用对象：

```python
async def fetch(url: str) -> tuple[int, str]:
    """返回 (状态码, 正文)。失败时抛异常。"""
```

不需要继承什么基类——**Python 里协议比继承更常用**（模块 04 讲过）。
想写类型注解的话可以用 `Protocol`。

### `MockFetcher`：离线假 fetcher

行为要求（这些规则是给你测试用的，请严格实现）：

| URL 里包含 | 行为 |
|-----------|------|
| `dead` | 永远失败，抛 `ConnectionError` |
| `flaky` | 前 2 次失败，第 3 次成功 |
| `slow` | 延迟是普通请求的 3 倍 |
| `error500` | 返回状态码 500（**注意：这是成功返回，不是抛异常**） |
| 其他 | 延迟一段时间后返回 `(200, "内容: <url>")` |

另外要记录两个统计量，供测试断言：

- `max_concurrent`：观测到的最大并发数
- `call_count`：总共被调用了几次

**「抛异常」和「返回 500」是两回事**，这一点很重要：

- 抛异常 = 连接层面的失败（DNS 解析不了、连不上、读超时）→ **应该重试**
- 返回 500 = 服务器明确告诉你它出错了 → **通常也该重试**，但和连接失败是不同类别
- 返回 404 = 服务器明确告诉你「没有这个东西」→ **绝对不该重试**，重试一万次也是 404

你的 `crawl` 至少要能区分「连接失败」和「4xx」。

### `HttpFetcher`：真实网络

不引入第三方库也行，用 `asyncio.to_thread` 包住 `urllib.request`：

```python
async def fetch(self, url):
    return await asyncio.to_thread(self._blocking_get, url)
```

`to_thread` 把阻塞调用丢到线程池里跑，这样它不会卡住事件循环——
**这是把同步库接进 asyncio 的标准做法**（模块 08 讲过为什么直接调会卡死）。

---

## 四、`crawl` 的四个要点

```python
async def crawl(
    urls: list[str],
    fetcher,
    *,
    concurrency: int = 5,
    retries: int = 3,
    timeout: float = 5.0,
    backoff: float = 0.05,
) -> list[FetchResult]:
```

### 1. 限流 —— `Semaphore`

```python
sem = asyncio.Semaphore(concurrency)

async def one(url):
    async with sem:          # 超过 concurrency 个就在这里排队
        ...
```

不限流的爬虫会把目标站点打挂，也会把自己本地的文件描述符耗尽。

### 2. 超时 —— `asyncio.timeout`

```python
async with asyncio.timeout(timeout):
    status, body = await fetcher.fetch(url)
```

超时抛的是内置的 `TimeoutError`。**必须要有超时**：
一个卡住的连接会让整个 `gather` 永远等下去。

⚠ 别用 `asyncio.wait_for` 了，`asyncio.timeout`（3.11+）是可组合的上下文管理器，
写嵌套逻辑时不会像 `wait_for` 那样越包越乱。

### 3. 重试 —— 指数退避

```python
for attempt in range(1, retries + 1):
    try:
        ...
        return FetchResult(ok=True, ...)
    except (ConnectionError, TimeoutError, OSError) as exc:
        last_error = exc
        if attempt < retries:
            await asyncio.sleep(backoff * 2 ** (attempt - 1))   # 0.05, 0.1, 0.2...
```

**为什么要退避**：对方刚出问题你就立刻重试，通常只会让它更惨。
每次等待翻倍，给对方喘息时间。

**什么该重试**：连接错误、超时、5xx。
**什么不该重试**：4xx（你的请求本身有问题，重试多少次都一样）。

### 4. 部分失败不能丢

一个 URL 重试完还是失败，**不能抛异常中断整个 crawler**。
要返回一个 `ok=False` 的 `FetchResult`，让调用方决定怎么处理。

如果你用 `asyncio.gather(..., return_exceptions=True)` 或者 `TaskGroup`，
注意默认行为：**`gather` 默认一个任务抛异常会立刻向上传播**，
而其他任务不会被取消（会留下 "Task exception was never retrieved" 警告）。
`TaskGroup`（3.11+）遇到异常会取消其余任务——对爬虫来说这通常**不是**
你想要的（一个 URL 挂了不该取消其他 9 个）。

所以本题推荐：**在每个任务内部把异常处理干净，让 `gather` 永远收不到异常。**

---

## 五、分阶段提示

### 第 1 步：`FetchResult` + `MockFetcher`（1 小时）

先把假 fetcher 写对，包括并发计数。它不难，但它是后面一切测试的基础。

**自测**：直接 `await` 它几次，确认 `flaky` 第三次才成功、`dead` 每次都抛。

### 第 2 步：单 URL、无重试（1 小时）

```python
async def fetch_one(url, fetcher, *, timeout) -> FetchResult
```

只做「调用 + 计时 + 包装成 FetchResult」，把异常都接住变成 `ok=False`。

**自测**：`dead` 返回 `ok=False`，其他返回 `ok=True`。

### 第 3 步：加 retries（1 小时）

重点验证 `flaky` 的 `attempts == 3`、`dead` 的 `attempts == retries`。

### 第 4 步：加并发 + 限流（1 小时）

用 `Semaphore` + `asyncio.gather`。验证：

- 结果顺序和输入顺序一致（gather 保序）
- `fetcher.max_concurrent <= concurrency`
- 总耗时接近「最慢的那个」而不是「所有之和」

### 第 5 步：CLI + 落盘（1 小时）

`argparse` 子命令 + `json.dump`。注意 `ensure_ascii=False`。

### 第 6 步（进阶）：加进度显示和统计

```
[1/10] 200  https://example.com/a   (0.05s)
[2/10] 失败 https://example.com/dead (重试 3 次)
...
成功 8  失败 2  总耗时 0.31s  平均 0.06s
```

---

## 六、常见坑

| 坑 | 后果 |
|----|------|
| `time.sleep` 而不是 `await asyncio.sleep` | 整个事件循环卡死，退化成串行 |
| 在 async 函数里直接用 `requests` | 同上。用 `asyncio.to_thread` 包住 |
| 不限流 | 目标站点封 IP / 本地 fd 耗尽 |
| 不设超时 | 一个卡住的连接让程序永远不返回 |
| 4xx 也重试 | 浪费时间，还可能被当成攻击 |
| 一个失败就整体抛异常 | 其余成功的结果全丢 |
| `gather` 里任务抛异常 | 其他任务不被取消，留下警告和资源泄漏 |
| 重试没有退避 | 对方刚崩你就猛敲，雪上加霜 |
| 进度直接 `print` 但没 `flush` | 输出卡在缓冲区里看不到 |

---

## 七、验收标准

- [ ] 离线模式能完整跑通，`--concurrency` 可调
- [ ] `fetcher.max_concurrent <= concurrency`（限流真的生效）
- [ ] `flaky` 的 `attempts == 3`
- [ ] `dead` 的 `ok is False` 且 `attempts == retries`
- [ ] 4xx 不重试
- [ ] 返回结果数量和顺序与输入一致
- [ ] 并发总耗时显著小于串行（自测里会验）
- [ ] 结果能落成合法 JSON，中文不转义
- [ ] 全程没有 `time.sleep`，没有阻塞调用直接进事件循环
