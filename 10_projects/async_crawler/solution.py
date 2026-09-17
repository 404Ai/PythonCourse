"""
项目 C · 并发抓取器 —— 参考实现

运行方式：
    python solution.py crawl --offline                     离线模式跑一遍
    python solution.py crawl --offline --concurrency 3
    python solution.py crawl --offline --out results.json
    python solution.py crawl --urls urls.txt --concurrency 10   （真实网络）
    python solution.py sample-urls                         打印一批示例 URL
    python solution.py test                                跑自测

设计要点：
    crawl() 只依赖一个抽象的 fetcher，不知道背后是网络还是假数据。
    于是并发/限流/超时/重试这些最难的逻辑，可以完全用 MockFetcher
    确定性地测干净 —— 这就是依赖注入的价值。
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
import urllib.error
import urllib.request
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Protocol

# ======================================================================
# 一、结果模型
# ======================================================================
@dataclass
class FetchResult:
    """一次抓取的最终结果。

    attempts 和 error 是刻意加的：它们让「重试发生了没有」「为什么失败」
    变成可断言的数据，而不是只能看日志猜。
    """

    url: str
    ok: bool
    status: int | None = None
    body: str | None = None
    attempts: int = 0
    elapsed: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


class Fetcher(Protocol):
    """一个 fetcher 只需要满足这个形状，不需要继承任何东西。

    这就是「结构化子类型」——Python 里协议比继承更常用（模块 04 讲过）。
    有了它，类型检查器能验证 MockFetcher 和 HttpFetcher 都能传给 crawl，
    而两个类之间没有任何继承关系。
    """

    async def fetch(self, url: str) -> tuple[int, str]:
        """返回 (状态码, 正文)。连接层面失败时抛异常。"""
        ...


# 哪些异常算「可以重试的临时故障」。
# 注意这是**连接层面**的错误：连不上、超时、DNS 挂了。
# HTTP 层面的 4xx/5xx 不在这里，它们在下面的 _should_retry_status 处理。
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError, urllib.error.URLError)


def _should_retry_status(status: int) -> bool:
    """5xx 值得重试（服务器临时故障），4xx 不值得。

    404 重试一万次还是 404，401 重试一万次还是没权限。
    把它们和 5xx 一视同仁地重试，是在浪费时间和带宽，
    还可能让对方把你当成攻击者。
    """
    return status >= 500


# ======================================================================
# 二、MockFetcher —— 离线假 fetcher
# ======================================================================
@dataclass
class MockFetcher:
    """确定性的假 fetcher。行为完全由 URL 里的关键词决定。

        dead      永远失败
        flaky     前 2 次失败，第 3 次成功
        slow      延迟 3 倍
        error500  返回 500（注意：这是**成功返回**，不是抛异常）
        其他      延迟后返回 200

    另外还统计 max_concurrent 和 call_count，供测试断言限流是否生效。
    """

    latency: float = 0.04
    _attempts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _current: int = 0
    max_concurrent: int = 0
    call_count: int = 0

    async def fetch(self, url: str) -> tuple[int, str]:
        self._attempts[url] += 1
        self.call_count += 1
        attempt = self._attempts[url]

        # 统计并发度：进来 +1，出去 -1，全程记录峰值。
        # 这是验证 Semaphore 有没有生效的唯一手段。
        self._current += 1
        self.max_concurrent = max(self.max_concurrent, self._current)
        try:
            delay = self.latency * (3 if "slow" in url else 1)
            await asyncio.sleep(delay)

            if "dead" in url:
                raise ConnectionError("模拟：连接被拒绝")
            if "flaky" in url and attempt < 3:
                raise ConnectionError(f"模拟：第 {attempt} 次抖动")
            if "error500" in url:
                # 注意这里**没有抛异常**，是正常返回一个 500 状态码。
                # 「连接失败」和「服务器返回错误」是两回事，
                # 虽然都可能触发重试，但走的是不同的判断分支。
                return 500, "Internal Server Error"
            return 200, f"<html>内容: {url}</html>"
        finally:
            self._current -= 1

    def attempts_for(self, url: str) -> int:
        return self._attempts[url]


# ======================================================================
# 三、HttpFetcher —— 真实网络
# ======================================================================
class HttpFetcher:
    """真实的 HTTP fetcher，只用标准库。"""

    def __init__(self, user_agent: str = "PythonCourseCrawler/0.1") -> None:
        self.user_agent = user_agent

    def _blocking_get(self, url: str) -> tuple[int, str]:
        request = urllib.request.Request(url, headers={"User-Agent": self.user_agent})
        try:
            with urllib.request.urlopen(request) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                return response.status, response.read().decode(charset, errors="replace")
        except urllib.error.HTTPError as exc:
            # HTTPError 也是「拿到了响应」，只不过状态码是 4xx/5xx。
            # 它不应该被当成连接失败往上抛，否则 404 会被误判成网络故障。
            return exc.code, exc.read().decode("utf-8", errors="replace")

    async def fetch(self, url: str) -> tuple[int, str]:
        """把阻塞的 urlopen 丢到线程池里。

        ⚠ 直接在协程里调 urllib.request.urlopen 会**阻塞整个事件循环**，
          所有并发一起卡住，退化成串行（模块 08 讲过这个坑）。
          asyncio.to_thread 是官方推荐的「把同步库接进 asyncio」的写法。
        """
        return await asyncio.to_thread(self._blocking_get, url)


# ======================================================================
# 四、单个 URL 的抓取（含重试）
# ======================================================================
async def fetch_one(
    url: str,
    fetcher: Fetcher,
    *,
    retries: int = 3,
    timeout: float = 5.0,
    backoff: float = 0.05,
) -> FetchResult:
    """抓一个 URL，内部处理重试。**永远不抛异常**，失败也返回 FetchResult。

    「永远不抛异常」是刻意的设计：这样 crawl 里的 gather 收不到异常，
    一个 URL 挂掉不会影响其他 URL —— 这正是爬虫要的语义。
    """
    started = time.perf_counter()
    attempts = 0
    last_error = "未知错误"

    for attempts in range(1, retries + 1):
        try:
            # asyncio.timeout 是 3.11+ 的可组合超时。
            # 不用 asyncio.wait_for，因为它在嵌套场景下会把代码写得很乱。
            async with asyncio.timeout(timeout):
                status, body = await fetcher.fetch(url)

            if _should_retry_status(status) and attempts < retries:
                last_error = f"HTTP {status}"
                await asyncio.sleep(backoff * 2 ** (attempts - 1))
                continue

            return FetchResult(
                url=url,
                ok=status < 400,
                status=status,
                body=body,
                attempts=attempts,
                elapsed=time.perf_counter() - started,
                error=None if status < 400 else f"HTTP {status}",
            )

        except RETRYABLE_EXCEPTIONS as exc:
            last_error = f"{type(exc).__name__}: {exc}"
            if attempts < retries:
                # 指数退避：0.05 -> 0.1 -> 0.2 ...
                # 对方刚出问题就立刻重试只会雪上加霜，给它一点喘息时间。
                await asyncio.sleep(backoff * 2 ** (attempts - 1))

    return FetchResult(
        url=url,
        ok=False,
        attempts=attempts,
        elapsed=time.perf_counter() - started,
        error=last_error,
    )


# ======================================================================
# 五、并发抓取
# ======================================================================
async def crawl(
    urls: list[str],
    fetcher: Fetcher,
    *,
    concurrency: int = 5,
    retries: int = 3,
    timeout: float = 5.0,
    backoff: float = 0.05,
    on_done=None,
) -> list[FetchResult]:
    """并发抓取。返回结果的**顺序和 urls 一致**。

    on_done 是个可选回调，每完成一个就调一次，用来做进度显示。
    """
    if concurrency < 1:
        raise ValueError(f"concurrency 必须 >= 1，收到 {concurrency}")

    sem = asyncio.Semaphore(concurrency)
    done = 0
    total = len(urls)

    async def worker(url: str) -> FetchResult:
        nonlocal done
        # 没有这一行，一万个 URL 会同时发出去。
        # Semaphore 就是那个闸门，超过 concurrency 个协程在这里排队。
        async with sem:
            result = await fetch_one(
                url, fetcher, retries=retries, timeout=timeout, backoff=backoff
            )
        done += 1
        if on_done is not None:
            on_done(done, total, result)
        return result

    # gather 保序：返回的列表顺序 == 传入的 awaitable 顺序，
    # 和谁先跑完无关。
    #
    # 这里能放心用 gather（而不是 TaskGroup）的前提是：
    # fetch_one 保证不抛异常。否则一个任务失败会立刻向上传播，
    # 而其余任务不会被取消，留下 "Task exception was never retrieved" 警告。
    return list(await asyncio.gather(*(worker(url) for url in urls)))


# ======================================================================
# 六、落盘与统计
# ======================================================================
def save_results(results: list[FetchResult], path: Path) -> None:
    """写成 JSON。ensure_ascii=False 让中文可读。"""
    payload = {
        "total": len(results),
        "ok": sum(1 for r in results if r.ok),
        "failed": sum(1 for r in results if not r.ok),
        "results": [r.to_dict() for r in results],
    }
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def summarize(results: list[FetchResult]) -> dict[str, object]:
    ok = [r for r in results if r.ok]
    failed = [r for r in results if not r.ok]
    total_elapsed = sum(r.elapsed for r in results)
    wall = max((r.elapsed for r in results), default=0.0)
    return {
        "total": len(results),
        "ok": len(ok),
        "failed": len(failed),
        "retried": sum(1 for r in results if r.attempts > 1),
        "sum_elapsed": round(total_elapsed, 3),
        "max_elapsed": round(wall, 3),
    }


# ======================================================================
# 七、示例 URL
# ======================================================================
SAMPLE_URLS = [
    "https://example.com/index.html",
    "https://example.com/about",
    "https://example.com/flaky-api",     # 前两次失败，第三次成功
    "https://example.com/docs/a",
    "https://example.com/docs/b",
    "https://example.com/slow-report",   # 慢
    "https://example.com/dead-endpoint", # 永远失败
    "https://example.com/error500-page", # 返回 500
    "https://example.com/api/users",
    "https://example.com/static/app.js",
]


# ======================================================================
# 八、CLI
# ======================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crawler", description="一个极简的并发抓取器。")
    sub = parser.add_subparsers(dest="command", required=True)

    p_crawl = sub.add_parser("crawl", help="抓取一批 URL")
    p_crawl.add_argument("--urls", type=Path, help="每行一个 URL 的文件；不给就用内置示例")
    p_crawl.add_argument("--offline", action="store_true",
                         help="用内置的假 fetcher，不真的发请求")
    p_crawl.add_argument("--concurrency", type=int, default=5, help="最大并发数（默认 5）")
    p_crawl.add_argument("--retries", type=int, default=3, help="每个 URL 最多试几次")
    p_crawl.add_argument("--timeout", type=float, default=5.0, help="单次请求超时秒数")
    p_crawl.add_argument("--out", type=Path, help="把结果写到 JSON 文件")

    p_sample = sub.add_parser("sample-urls", help="打印内置示例 URL")
    p_sample.add_argument("--out", type=Path, help="写到文件而不是 stdout")

    sub.add_parser("test", help="跑自测")
    return parser


def run_crawl(args: argparse.Namespace) -> int:
    if args.urls is not None:
        if not args.urls.is_file():
            print(f"错误：找不到文件 {args.urls}", file=sys.stderr)
            return 1
        urls = [
            line.strip()
            for line in args.urls.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    else:
        urls = SAMPLE_URLS

    if not urls:
        print("错误：没有可抓取的 URL。", file=sys.stderr)
        return 1

    fetcher: Fetcher
    if args.offline:
        fetcher = MockFetcher()
        print(f"离线模式：{len(urls)} 个 URL，并发 {args.concurrency}，最多重试 {args.retries} 次")
    else:
        fetcher = HttpFetcher()
        print(f"真实网络模式：{len(urls)} 个 URL，并发 {args.concurrency}")

    def on_done(done: int, total: int, result: FetchResult) -> None:
        mark = "200 " if result.ok else "失败"
        extra = f"（重试 {result.attempts} 次）" if result.attempts > 1 else ""
        print(f"  [{done:>{len(str(total))}}/{total}] {mark} {result.url} "
              f"({result.elapsed:.2f}s){extra}")

    started = time.perf_counter()
    results = asyncio.run(
        crawl(
            urls,
            fetcher,
            concurrency=args.concurrency,
            retries=args.retries,
            timeout=args.timeout,
            on_done=on_done,
        )
    )
    wall = time.perf_counter() - started

    stats = summarize(results)
    print()
    print(f"总耗时      {wall:.2f}s")
    print(f"成功 / 失败 {stats['ok']} / {stats['failed']}")
    print(f"发生过重试  {stats['retried']} 个")
    print(f"串行累加耗时 {stats['sum_elapsed']}s   <- 和总耗时对比能看出并发的效果")

    if isinstance(fetcher, MockFetcher):
        print(f"观测到的最大并发数 {fetcher.max_concurrent}（上限 {args.concurrency}）")

    failures = [r for r in results if not r.ok]
    if failures:
        print()
        print("失败的 URL：")
        for r in failures:
            print(f"  {r.url}  ({r.error})")

    if args.out is not None:
        save_results(results, args.out)
        print(f"\n结果已写入 {args.out}")

    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "test":
        return run_tests()

    if args.command == "sample-urls":
        text = "\n".join(SAMPLE_URLS) + "\n"
        if args.out is not None:
            args.out.write_text(text, encoding="utf-8")
            print(f"已写入 {args.out}")
        else:
            sys.stdout.write(text)
        return 0

    return run_crawl(args)


# ======================================================================
# 九、自测
# ======================================================================
def run_tests() -> int:
    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}  {detail}")
            failures += 1

    # ---------------------------------------------------------------- #
    print("=" * 66)
    print("MockFetcher 本身")
    print("=" * 66)

    async def mock_semantics() -> None:
        fetcher = MockFetcher(latency=0.001)

        status, body = await fetcher.fetch("https://x.com/normal")
        check("普通 URL 返回 200", status == 200 and "normal" in body, f"{status} {body}")

        status, _ = await fetcher.fetch("https://x.com/error500")
        check("error500 返回 500 而不是抛异常", status == 500, str(status))

        for attempt in (1, 2):
            try:
                await fetcher.fetch("https://x.com/flaky")
                check(f"flaky 第 {attempt} 次应该失败", False)
            except ConnectionError:
                pass
        status, _ = await fetcher.fetch("https://x.com/flaky")
        check("flaky 第 3 次成功", status == 200)

        try:
            await fetcher.fetch("https://x.com/dead")
            check("dead 应该永远失败", False)
        except ConnectionError:
            pass
        else:
            pass
        check("dead 确实抛 ConnectionError", True)

    asyncio.run(mock_semantics())

    # ---------------------------------------------------------------- #
    print()
    print("=" * 66)
    print("fetch_one：重试逻辑")
    print("=" * 66)

    async def retry_logic() -> None:
        fetcher = MockFetcher(latency=0.001)

        r = await fetch_one("https://x.com/flaky", fetcher, retries=3, backoff=0.001)
        check("flaky 最终成功", r.ok is True, str(r))
        check("flaky 尝试了 3 次", r.attempts == 3, f"attempts={r.attempts}")
        check("成功时 error 为 None", r.error is None, str(r.error))

        r = await fetch_one("https://x.com/dead", fetcher, retries=3, backoff=0.001)
        check("dead 最终失败", r.ok is False)
        check("dead 尝试了 3 次", r.attempts == 3, f"attempts={r.attempts}")
        check("失败时带 error 说明", bool(r.error), str(r.error))
        check("失败时 status 为 None", r.status is None)

        # 4xx 不该重试
        class NotFoundFetcher:
            def __init__(self) -> None:
                self.calls = 0

            async def fetch(self, url: str) -> tuple[int, str]:
                self.calls += 1
                return 404, "not found"

        nf = NotFoundFetcher()
        r = await fetch_one("https://x.com/missing", nf, retries=3, backoff=0.001)
        check("404 只请求 1 次", nf.calls == 1, f"请求了 {nf.calls} 次")
        check("404 结果 ok=False", r.ok is False)

        # 5xx 应该重试
        class BadServerFetcher:
            def __init__(self) -> None:
                self.calls = 0

            async def fetch(self, url: str) -> tuple[int, str]:
                self.calls += 1
                return 503, "unavailable"

        bs = BadServerFetcher()
        r = await fetch_one("https://x.com/x", bs, retries=3, backoff=0.001)
        check("503 重试满 3 次", bs.calls == 3, f"请求了 {bs.calls} 次")
        check("503 最终 ok=False", r.ok is False)

    asyncio.run(retry_logic())

    # ---------------------------------------------------------------- #
    print()
    print("=" * 66)
    print("crawl：并发与限流")
    print("=" * 66)

    async def concurrency_checks() -> None:
        urls = [f"https://x.com/page{i}" for i in range(12)]

        fetcher = MockFetcher(latency=0.02)
        started = time.perf_counter()
        results = await crawl(urls, fetcher, concurrency=4, retries=1, backoff=0.001)
        elapsed = time.perf_counter() - started

        check("结果数量一致", len(results) == len(urls), f"{len(results)} vs {len(urls)}")
        check("结果顺序与输入一致", [r.url for r in results] == urls)
        check("全部成功", all(r.ok for r in results))
        check("限流生效（峰值 <= 4）", fetcher.max_concurrent <= 4,
              f"峰值 {fetcher.max_concurrent}")
        check("确实并发起来了（峰值 >= 2）", fetcher.max_concurrent >= 2,
              f"峰值 {fetcher.max_concurrent}")

        # 12 个 0.02s 的请求，并发 4 -> 约 3 轮 0.06s；
        # 串行会是 0.24s。给足余量判 0.18s。
        check(f"并发总耗时 {elapsed:.3f}s 明显小于串行", elapsed < 0.18, f"{elapsed:.3f}s")

    asyncio.run(concurrency_checks())

    # ---------------------------------------------------------------- #
    print()
    print("=" * 66)
    print("crawl：混合场景（部分失败不影响其他）")
    print("=" * 66)

    async def mixed() -> None:
        urls = [
            "https://x.com/ok1",
            "https://x.com/dead",
            "https://x.com/ok2",
            "https://x.com/flaky",
        ]
        fetcher = MockFetcher(latency=0.005)
        results = await crawl(urls, fetcher, concurrency=4, retries=3, backoff=0.001)

        by_url = {r.url: r for r in results}
        check("ok1 成功", by_url["https://x.com/ok1"].ok is True)
        check("ok2 成功", by_url["https://x.com/ok2"].ok is True)
        check("dead 失败但没影响别人", by_url["https://x.com/dead"].ok is False)
        check("flaky 重试后成功", by_url["https://x.com/flaky"].ok is True)
        check("flaky 尝试 3 次", by_url["https://x.com/flaky"].attempts == 3)
        check("没有异常导致整体中断", len(results) == 4)

        stats = summarize(results)
        check("统计正确", stats["ok"] == 3 and stats["failed"] == 1, str(stats))
        # 重试过的有**两个**：flaky（前两次失败）和 dead（重试满 3 次才放弃）。
        # 第一次写这条断言时只想到 flaky，跑出 2 才发现 dead 也算 ——
        # 「尝试次数 > 1」这个判据本身就同时覆盖了「重试成功」和「重试后仍失败」。
        check("统计出 2 个重试过的", stats["retried"] == 2, str(stats))
        check("重试的正是 flaky 和 dead",
              sorted(r.url.rsplit("/", 1)[-1] for r in results if r.attempts > 1)
              == ["dead", "flaky"],
              str([r.url for r in results if r.attempts > 1]))

    asyncio.run(mixed())

    # ---------------------------------------------------------------- #
    print()
    print("=" * 66)
    print("边界与落盘")
    print("=" * 66)

    async def edges() -> None:
        check("空列表返回空", await crawl([], MockFetcher()) == [])
        check("并发 1 也能跑", len(await crawl(["https://x.com/a"], MockFetcher(latency=0.001),
                                              concurrency=1, retries=1)) == 1)
        try:
            await crawl(["https://x.com/a"], MockFetcher(), concurrency=0)
        except ValueError:
            check("concurrency=0 抛 ValueError", True)
        else:
            check("concurrency=0 抛 ValueError", False, "竟然没报错")

    asyncio.run(edges())

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "results.json"
        sample = [
            FetchResult(url="https://x.com/a", ok=True, status=200, body="<html>中文</html>",
                        attempts=1, elapsed=0.1),
            FetchResult(url="https://x.com/dead", ok=False, attempts=3, elapsed=0.3,
                        error="ConnectionError: 拒绝"),
        ]
        save_results(sample, out)
        raw = out.read_text(encoding="utf-8")
        payload = json.loads(raw)
        check("落盘是合法 JSON", payload["total"] == 2)
        check("落盘统计正确", payload["ok"] == 1 and payload["failed"] == 1)
        check("中文没被转义", "\\u" not in raw and "中文" in raw)
        check("失败原因被保留", "拒绝" in json.dumps(payload, ensure_ascii=False))

    print()
    print("=" * 66)
    if failures:
        print(f"{failures} 项未通过")
    else:
        print("全部通过。")
    print("=" * 66)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
