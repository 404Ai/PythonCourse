"""
项目 C · 并发抓取器 —— 骨架

要填的地方标了 TODO。运行方式：

    python starter.py test                       看进度
    python starter.py crawl --offline            离线模式跑一遍
    python starter.py sample-urls

详细提示见 README.md，参考答案见 solution.py。

建议顺序：
    FetchResult -> MockFetcher -> fetch_one（先不管重试）
    -> 加重试 -> crawl（加并发和限流）-> CLI 和落盘

⚠ 三条铁律，写的时候时刻记着：
    1. 永远不要在这个文件里出现 time.sleep —— 用 await asyncio.sleep
    2. 每个请求都要有超时
    3. fetch_one 不许把异常抛出去，失败也要返回 FetchResult
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
# 一、结果模型 —— 已给好
# ======================================================================
@dataclass
class FetchResult:
    """一次抓取的最终结果。

    attempts / error 这两个字段别省，它们让「重试发生过没有」
    「为什么失败」变成可断言的数据，而不是只能看日志猜。
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
    """结构化的协议：只要形状对得上就算 fetcher，不需要继承任何东西。

    ▸ 这就是「鸭子类型」的类型注解写法。
      MockFetcher 和 HttpFetcher 之间没有任何继承关系，
      但类型检查器知道它俩都能传给 crawl。
    """

    async def fetch(self, url: str) -> tuple[int, str]:
        """返回 (状态码, 正文)。连接层面失败时抛异常。"""
        ...


# 哪些异常算「可以重试的临时故障」—— 注意这是**连接层面**的错误。
RETRYABLE_EXCEPTIONS = (ConnectionError, TimeoutError, OSError, urllib.error.URLError)


def _should_retry_status(status: int) -> bool:
    """TODO 1：返回这个状态码值不值得重试。

        ▸ 5xx 值得（服务器临时故障），4xx 不值得（你的请求本身有问题）。
        ▸ 一行代码。
        ▸ 想想 404 重试一万次会是什么结果 —— 答案还是 404。
    """
    raise NotImplementedError("TODO 1: _should_retry_status")


# ======================================================================
# 二、MockFetcher —— 离线假 fetcher
# ======================================================================
@dataclass
class MockFetcher:
    """确定性的假 fetcher。行为完全由 URL 里的关键词决定：

        dead      永远失败（抛 ConnectionError）
        flaky     前 2 次失败，第 3 次成功
        slow      延迟 3 倍
        error500  返回 500（**成功返回**，不是抛异常）
        其他      延迟后返回 200
    """

    latency: float = 0.04
    _attempts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    _current: int = 0
    max_concurrent: int = 0
    call_count: int = 0

    async def fetch(self, url: str) -> tuple[int, str]:
        """TODO 2：实现上面描述的行为。

        步骤：
            1. self._attempts[url] += 1；self.call_count += 1
            2. attempt = self._attempts[url]
            3. self._current += 1
               self.max_concurrent = max(self.max_concurrent, self._current)
               然后用 try/finally 保证退出时 self._current -= 1
               （并发计数就是靠这个测出来的，别忘了 finally）
            4. delay = self.latency * (3 if "slow" in url else 1)
               await asyncio.sleep(delay)
            5. 按关键词分派：
                 "dead"      -> raise ConnectionError("模拟：连接被拒绝")
                 "flaky" 且 attempt < 3 -> raise ConnectionError(f"模拟：第 {attempt} 次抖动")
                 "error500"  -> return 500, "Internal Server Error"
                 其他        -> return 200, f"<html>内容: {url}</html>"

        ▸ **必须用 await asyncio.sleep**，用 time.sleep 会卡死整个事件循环。
        ▸ 注意 "error500" 是 return 而不是 raise ——
          「连接失败」和「服务器返回错误」是两回事，
          虽然都可能触发重试，但走的是不同的判断分支。
        """
        raise NotImplementedError("TODO 2: MockFetcher.fetch")

    def attempts_for(self, url: str) -> int:
        return self._attempts[url]


# ======================================================================
# 三、HttpFetcher —— 真实网络（已给好）
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
            # HTTPError 也是「拿到了响应」，只是状态码是 4xx/5xx。
            # 不该当连接失败往上抛，否则 404 会被误判成网络故障。
            return exc.code, exc.read().decode("utf-8", errors="replace")

    async def fetch(self, url: str) -> tuple[int, str]:
        """把阻塞的 urlopen 丢到线程池。

        ▸ 直接在协程里调 urlopen 会阻塞整个事件循环，所有并发一起卡住，
          退化成串行。asyncio.to_thread 是把同步库接进 asyncio 的标准做法。
        """
        return await asyncio.to_thread(self._blocking_get, url)


# ======================================================================
# 四、单个 URL 的抓取
# ======================================================================
async def fetch_one(
    url: str,
    fetcher: Fetcher,
    *,
    retries: int = 3,
    timeout: float = 5.0,
    backoff: float = 0.05,
) -> FetchResult:
    """TODO 3：抓一个 URL，内部处理重试。

    **永远不抛异常**，失败也返回 FetchResult（ok=False）。这一点是刻意的：
    这样 crawl 里的 gather 收不到异常，一个 URL 挂掉不会影响其他 URL。

    结构：
        started = time.perf_counter()
        attempts = 0
        last_error = "未知错误"

        for attempts in range(1, retries + 1):
            try:
                async with asyncio.timeout(timeout):
                    status, body = await fetcher.fetch(url)

                # 5xx 且还能重试 -> 记下错误、退避、continue
                if _should_retry_status(status) and attempts < retries:
                    last_error = f"HTTP {status}"
                    await asyncio.sleep(backoff * 2 ** (attempts - 1))
                    continue

                # 否则直接返回（ok 用 status < 400 判断）
                return FetchResult(url=url, ok=status < 400, status=status,
                                   body=body, attempts=attempts,
                                   elapsed=time.perf_counter() - started,
                                   error=None if status < 400 else f"HTTP {status}")

            except RETRYABLE_EXCEPTIONS as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                if attempts < retries:
                    await asyncio.sleep(backoff * 2 ** (attempts - 1))

        # 循环跑完还没 return，说明彻底失败了
        return FetchResult(url=url, ok=False, attempts=attempts,
                           elapsed=time.perf_counter() - started, error=last_error)

    ▸ asyncio.timeout 是 3.11+ 的，超时抛内置的 TimeoutError。
    ▸ 退避是指数增长：0.05 -> 0.1 -> 0.2。对方刚出问题就猛敲只会雪上加霜。
    ▸ 注意 except 里也要判断 attempts < retries 才 sleep，
      最后一次失败后再睡就是白白浪费时间。
    """
    raise NotImplementedError("TODO 3: fetch_one")


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
    """TODO 4：并发抓取，返回结果的顺序要和 urls 一致。

    步骤：
        1. concurrency < 1 -> raise ValueError
        2. sem = asyncio.Semaphore(concurrency)
        3. done = 0；total = len(urls)
        4. 定义内层 async def worker(url):
               nonlocal done
               async with sem:          # <- 限流的闸门就在这里
                   result = await fetch_one(url, fetcher, retries=retries,
                                            timeout=timeout, backoff=backoff)
               done += 1
               if on_done is not None:
                   on_done(done, total, result)
               return result
        5. return list(await asyncio.gather(*(worker(u) for u in urls)))

    ▸ `async with sem` 这一行就是限流。没有它，一万个请求会同时发出去。
    ▸ gather 保序：返回列表的顺序 == 传入的顺序，和谁先跑完无关。
    ▸ 这里能放心用 gather 而不是 TaskGroup，前提是 fetch_one 保证不抛异常。
      TaskGroup 遇到异常会取消其余任务 —— 对爬虫来说这是错的：
      一个 URL 挂了不该取消其他 9 个。
    """
    raise NotImplementedError("TODO 4: crawl")


# ======================================================================
# 六、落盘与统计
# ======================================================================
def save_results(results: list[FetchResult], path: Path) -> None:
    """TODO 5：写成 JSON。

    结构：{"total": ..., "ok": ..., "failed": ..., "results": [...]}
    用 json.dumps(..., ensure_ascii=False, indent=2)，
    再 path.write_text(..., encoding="utf-8")。

    ▸ ensure_ascii 默认 True，中文会变成 \\uXXXX，文件没法读也没法 diff。
    """
    raise NotImplementedError("TODO 5: save_results")


def summarize(results: list[FetchResult]) -> dict[str, object]:
    """TODO 6：返回统计字典：

        total         总条数
        ok            成功数
        failed        失败数
        retried       尝试次数 > 1 的条数
        sum_elapsed   所有耗时之和（round 3 位）—— 相当于串行会花多久
        max_elapsed   最大耗时（round 3 位）—— 并发理想情况下的墙钟时间

    ▸ sum_elapsed 和 max_elapsed 的对比，是展示并发效果最直观的一组数字。
    """
    raise NotImplementedError("TODO 6: summarize")


# ======================================================================
# 七、示例 URL 与 CLI —— 已给好
# ======================================================================
SAMPLE_URLS = [
    "https://example.com/index.html",
    "https://example.com/about",
    "https://example.com/flaky-api",
    "https://example.com/docs/a",
    "https://example.com/docs/b",
    "https://example.com/slow-report",
    "https://example.com/dead-endpoint",
    "https://example.com/error500-page",
    "https://example.com/api/users",
    "https://example.com/static/app.js",
]


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="crawler", description="一个极简的并发抓取器。")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("crawl", help="抓取一批 URL")
    p.add_argument("--urls", type=Path, help="每行一个 URL 的文件；不给就用内置示例")
    p.add_argument("--offline", action="store_true", help="用假 fetcher，不真的发请求")
    p.add_argument("--concurrency", type=int, default=5)
    p.add_argument("--retries", type=int, default=3)
    p.add_argument("--timeout", type=float, default=5.0)
    p.add_argument("--out", type=Path, help="把结果写到 JSON 文件")

    p2 = sub.add_parser("sample-urls")
    p2.add_argument("--out", type=Path)

    sub.add_parser("test")
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

    fetcher: Fetcher = MockFetcher() if args.offline else HttpFetcher()
    mode = "离线模式" if args.offline else "真实网络模式"
    print(f"{mode}：{len(urls)} 个 URL，并发 {args.concurrency}，最多重试 {args.retries} 次")

    def on_done(done: int, total: int, result: FetchResult) -> None:
        mark = "200 " if result.ok else "失败"
        extra = f"（重试 {result.attempts} 次）" if result.attempts > 1 else ""
        width = len(str(total))
        print(f"  [{done:>{width}}/{total}] {mark} {result.url} "
              f"({result.elapsed:.2f}s){extra}")

    started = time.perf_counter()
    results = asyncio.run(
        crawl(urls, fetcher, concurrency=args.concurrency, retries=args.retries,
              timeout=args.timeout, on_done=on_done)
    )
    wall = time.perf_counter() - started

    stats = summarize(results)
    print()
    print(f"总耗时       {wall:.2f}s")
    print(f"成功 / 失败  {stats['ok']} / {stats['failed']}")
    print(f"发生过重试   {stats['retried']} 个")
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
# 八、自测
# ======================================================================
def run_tests() -> int:
    failures = 0
    skipped = 0

    def report(label: str, fn) -> None:
        nonlocal failures, skipped
        try:
            fn()
        except NotImplementedError as exc:
            print(f"  [SKIP] {label:<32} {exc}")
            skipped += 1
        except AssertionError as exc:
            print(f"  [FAIL] {label:<32} {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] {label:<32} {type(exc).__name__}: {exc}")
            failures += 1
        else:
            print(f"  [PASS] {label}")

    def aio(coro_factory, label):
        def run() -> None:
            asyncio.run(coro_factory())
        report(label, run)

    def assert_that(condition: bool, detail: str = "") -> None:
        assert condition, detail

    # ------------------------------------------------------------------ #
    print("=" * 66)
    print("状态码重试策略")
    print("=" * 66)
    report("404 不重试", lambda: assert_that(_should_retry_status(404) is False))
    report("401 不重试", lambda: assert_that(_should_retry_status(401) is False))
    report("500 重试", lambda: assert_that(_should_retry_status(500) is True))
    report("503 重试", lambda: assert_that(_should_retry_status(503) is True))

    # ------------------------------------------------------------------ #
    print()
    print("=" * 66)
    print("MockFetcher")
    print("=" * 66)

    async def mock_semantics() -> None:
        f = MockFetcher(latency=0.001)
        status, body = await f.fetch("https://x.com/normal")
        assert_that(status == 200 and "normal" in body, f"{status} {body}")
        status, _ = await f.fetch("https://x.com/error500")
        assert_that(status == 500, "error500 应该返回 500 而不是抛异常")
        for _ in range(2):
            try:
                await f.fetch("https://x.com/flaky")
            except ConnectionError:
                pass
            else:
                raise AssertionError("flaky 前两次应该失败")
        status, _ = await f.fetch("https://x.com/flaky")
        assert_that(status == 200, "flaky 第三次应该成功")
        try:
            await f.fetch("https://x.com/dead")
        except ConnectionError:
            pass
        else:
            raise AssertionError("dead 应该抛 ConnectionError")

    aio(mock_semantics, "MockFetcher 的四种行为")

    # ------------------------------------------------------------------ #
    print()
    print("=" * 66)
    print("fetch_one 重试逻辑")
    print("=" * 66)

    async def retry_logic() -> None:
        f = MockFetcher(latency=0.001)
        r = await fetch_one("https://x.com/flaky", f, retries=3, backoff=0.001)
        assert_that(r.ok is True, str(r))
        assert_that(r.attempts == 3, f"attempts={r.attempts}")
        assert_that(r.error is None, str(r.error))

        r = await fetch_one("https://x.com/dead", f, retries=3, backoff=0.001)
        assert_that(r.ok is False and r.attempts == 3, str(r))
        assert_that(bool(r.error), "失败时应该有 error 说明")

        class NotFound:
            calls = 0

            async def fetch(self, url: str) -> tuple[int, str]:
                NotFound.calls += 1
                return 404, "nf"

        NotFound.calls = 0
        r = await fetch_one("https://x.com/m", NotFound(), retries=3, backoff=0.001)
        assert_that(NotFound.calls == 1, f"404 不该重试，实际请求 {NotFound.calls} 次")
        assert_that(r.ok is False, "404 应该 ok=False")

        class BadServer:
            calls = 0

            async def fetch(self, url: str) -> tuple[int, str]:
                BadServer.calls += 1
                return 503, "unavailable"

        r = await fetch_one("https://x.com/x", BadServer(), retries=3, backoff=0.001)
        assert_that(BadServer.calls == 3, f"503 应该重试满 3 次，实际 {BadServer.calls} 次")

    aio(retry_logic, "重试与退避")

    # ------------------------------------------------------------------ #
    print()
    print("=" * 66)
    print("crawl 并发与限流")
    print("=" * 66)

    async def concurrency_checks() -> None:
        urls = [f"https://x.com/page{i}" for i in range(12)]
        f = MockFetcher(latency=0.02)
        started = time.perf_counter()
        results = await crawl(urls, f, concurrency=4, retries=1, backoff=0.001)
        elapsed = time.perf_counter() - started

        assert_that(len(results) == len(urls), f"{len(results)} vs {len(urls)}")
        assert_that([r.url for r in results] == urls, "结果顺序和输入不一致")
        assert_that(all(r.ok for r in results), "不该有失败")
        assert_that(f.max_concurrent <= 4, f"限流没生效，峰值 {f.max_concurrent}")
        assert_that(f.max_concurrent >= 2, f"没并发起来，峰值 {f.max_concurrent}")
        assert_that(elapsed < 0.18, f"并发总耗时 {elapsed:.3f}s，太慢了")

    aio(concurrency_checks, "限流与保序")

    async def mixed() -> None:
        urls = ["https://x.com/ok1", "https://x.com/dead",
                "https://x.com/ok2", "https://x.com/flaky"]
        f = MockFetcher(latency=0.005)
        results = await crawl(urls, f, concurrency=4, retries=3, backoff=0.001)
        by_url = {r.url: r for r in results}
        assert_that(len(results) == 4, "一个失败不该让整体中断")
        assert_that(by_url["https://x.com/dead"].ok is False, "dead 应该失败")
        assert_that(by_url["https://x.com/flaky"].ok is True, "flaky 重试后应该成功")
        assert_that(by_url["https://x.com/flaky"].attempts == 3, "flaky 应该试 3 次")
        stats = summarize(results)
        assert_that(stats["ok"] == 3 and stats["failed"] == 1, str(stats))
        assert_that(stats["retried"] == 2, str(stats))

    aio(mixed, "部分失败不影响其他")

    async def edges() -> None:
        assert_that(await crawl([], MockFetcher()) == [], "空列表应该返回空")
        try:
            await crawl(["https://x.com/a"], MockFetcher(), concurrency=0)
        except ValueError:
            pass
        else:
            raise AssertionError("concurrency=0 应该抛 ValueError")

    aio(edges, "边界情况")

    # ------------------------------------------------------------------ #
    print()
    print("=" * 66)
    print("落盘")
    print("=" * 66)

    import tempfile

    def persistence() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "r.json"
            sample = [
                FetchResult(url="https://x.com/a", ok=True, status=200,
                            body="<html>中文</html>", attempts=1, elapsed=0.1),
                FetchResult(url="https://x.com/b", ok=False, attempts=3,
                            elapsed=0.3, error="ConnectionError: 拒绝"),
            ]
            save_results(sample, out)
            raw = out.read_text(encoding="utf-8")
            payload = json.loads(raw)
            assert_that(payload["total"] == 2, str(payload))
            assert_that(payload["ok"] == 1 and payload["failed"] == 1, str(payload))
            assert_that("\\u" not in raw and "中文" in raw, "中文被转义了")

    report("JSON 落盘（含中文）", persistence)

    print()
    print("=" * 66)
    total = 4 + 1 + 1 + 2 + 1 + 1     # 状态码4 + Mock1 + 重试1 + 并发2 + 边界1 + 落盘1
    print(f"合计约 {total} 项   失败 {failures}   未做 {skipped}")
    if failures:
        print("还有失败项，先看上面带 FAIL / ERROR 的行。")
    elif skipped:
        print("通过的都对了，继续做剩下的 TODO。")
    else:
        print("全部通过。对照 solution.py 看看它的代码组织方式。")
    print("=" * 66)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
