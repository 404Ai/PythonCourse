"""
项目 B · 日志分析 CLI —— 骨架

要填的地方标了 TODO。运行方式：

    python starter.py sample > access.log     生成示例日志（已实现）
    python starter.py test                    看进度
    python starter.py summary access.log

详细提示见 README.md，参考答案见 solution.py。

建议顺序：LogEntry -> parse_line -> load -> 各聚合函数 -> 渲染 -> CLI。
**先把 parse_line 做对再做别的**，后面的所有东西都建立在它上面。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

# ======================================================================
# 一、数据模型
# ======================================================================
@dataclass(frozen=True)
class LogEntry:
    """一条访问记录。

    frozen=True 让它不可变，顺带获得 __hash__（能放进 set / 当 dict 的键）。
    timestamp 必须是 **aware** datetime，不能是 naive 的。
    """

    timestamp: datetime
    ip: str
    method: str
    path: str
    status: int
    duration_ms: int

    @property
    def is_error(self) -> bool:
        """TODO 1：4xx 和 5xx 都算错误。

        ▸ 一行代码：return self.status >= 400
        ▸ 注意 3xx 重定向**不算**错误。
        """
        raise NotImplementedError("TODO 1: LogEntry.is_error")

    def to_dict(self) -> dict[str, object]:
        """已实现。注意 datetime 要转成字符串，否则 json.dumps 认不了。"""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        return data


# ======================================================================
# 二、解析
# ======================================================================
def parse_line(line: str) -> LogEntry | None:
    """TODO 2：解析一行日志，坏行返回 None。

    日志格式（空格分隔，六段）：
        2026-09-16T10:23:45Z 203.0.113.7 GET /api/users 200 1234

    步骤：
        1. parts = line.split()
        2. len(parts) != 6 -> return None
        3. 解包成 raw_ts, ip, method, path, raw_status, raw_duration
        4. try 块里做三件事：
               timestamp = datetime.fromisoformat(raw_ts)
               status = int(raw_status)
               duration_ms = int(raw_duration)
           任何 ValueError -> return None
        5. 状态码不在 100~599 之间 -> return None
        6. 返回 LogEntry(...)

    ▸ **返回 None 而不是抛异常**：日志分析的正确行为是跳过坏行继续，
      一行脏数据不该让整次分析失败。
    ▸ 3.11+ 的 fromisoformat 能直接解析结尾的 'Z'。拿到了 aware datetime。
    ▸ 只捕获 ValueError。其他异常是真 bug，应该带着 traceback 崩掉。
    """
    raise NotImplementedError("TODO 2: parse_line")


def load(path: Path) -> tuple[list[LogEntry], int]:
    """TODO 3：读文件，返回 (成功解析的条目, 无法解析的行数)。

        1. 两个累加器：entries 和 bad
        2. with path.open(encoding="utf-8") as fh: 逐行读
        3. line.strip() 之后为空 -> continue（空行不算坏行）
        4. parse_line(line) 返回 None -> bad += 1
           否则 append 到 entries
        5. 返回 (entries, bad)

    ▸ **encoding="utf-8" 必须写**。不写的话 Windows 上默认 GBK，
      日志里有中文就乱码或直接抛 UnicodeDecodeError。
    ▸ 坏行数一定要返回给调用方并报给用户。静默丢数据是真正的坑。
    """
    raise NotImplementedError("TODO 3: load")


# ======================================================================
# 三、聚合 —— 全部写成纯函数
# ======================================================================
def top_ips(entries: list[LogEntry], n: int = 10) -> list[tuple[str, int]]:
    """TODO 4：请求数最多的 N 个 IP，返回 [(ip, 次数), ...]。

        1. counts = Counter(e.ip for e in entries)
        2. 按 (-次数, ip) 排序后取前 n 个

    ▸ 不要直接用 Counter.most_common —— 它在计数相同时按**插入顺序**返回，
      结果不确定，测试会随机挂。
      用 (-次数, ip) 这个 key 排序，并列时按 IP 字典序，输出才是确定的。
    """
    raise NotImplementedError("TODO 4: top_ips")


def status_distribution(entries: list[LogEntry]) -> dict[int, int]:
    """TODO 5：状态码分布，按状态码升序返回 {状态码: 次数}。

        Counter 之后用 dict(sorted(...)) 排一下序。
    """
    raise NotImplementedError("TODO 5: status_distribution")


def slowest(entries: list[LogEntry], n: int = 10) -> list[LogEntry]:
    """TODO 6：最慢的 N 条请求。

        按 (-e.duration_ms, e.timestamp) 排序取前 n 条。
        并列时用时间戳兜底，保证结果稳定。
    """
    raise NotImplementedError("TODO 6: slowest")


def error_rate(entries: list[LogEntry]) -> float:
    """TODO 7：错误率 = 错误条数 / 总条数。

        ▸ 空列表要返回 0.0，不能除零。
    """
    raise NotImplementedError("TODO 7: error_rate")


def error_breakdown(entries: list[LogEntry]) -> dict[int, int]:
    """TODO 8：只统计错误状态码的分布，按状态码升序。"""
    raise NotImplementedError("TODO 8: error_breakdown")


def error_paths(entries: list[LogEntry], n: int = 10) -> list[tuple[str, int]]:
    """TODO 9：出错最多的路径，并列时按路径字典序。"""
    raise NotImplementedError("TODO 9: error_paths")


def hourly_histogram(entries: list[LogEntry]) -> list[tuple[int, int]]:
    """TODO 10：按小时统计，返回 [(小时, 次数), ...]，只列出有数据的小时。

        ▸ 用 e.timestamp.hour 拿小时。时间戳是 UTC 的，所以这是 UTC 小时。
          不要转本地时间 —— 那会让结果依赖「你的机器在哪个时区」，不可复现。
    """
    raise NotImplementedError("TODO 10: hourly_histogram")


def summarize(entries: list[LogEntry]) -> dict[str, object]:
    """TODO 11：汇总，返回普通 dict（方便直接 json.dumps）。

    要包含这些键：
        total            总条数
        unique_ips       独立 IP 数（提示：len({e.ip for e in entries})）
        error_rate       错误率，round(..., 4)
        avg_duration_ms  平均耗时，round(..., 1)
        max_duration_ms  最大耗时
        start / end      最早/最晚时间戳的 isoformat()

    ▸ 空列表要单独处理，返回全 0、start/end 为 None 的字典，别让它炸。
    """
    raise NotImplementedError("TODO 11: summarize")


# ======================================================================
# 四、呈现
# ======================================================================
def bar(value: int, maximum: int, width: int = 30) -> str:
    """已实现。按比例画条，用 # 而不是方块字符，避免控制台编码问题。"""
    if maximum <= 0:
        return ""
    filled = round(value / maximum * width)
    return "#" * max(filled, 1 if value else 0)


def render_summary(entries: list[LogEntry], bad: int, out) -> None:
    """TODO 12：打印总览。

    用 summarize() 拿到数据，然后逐行打印。
    别忘了 bad > 0 时打印「无法解析的行 N 行（已跳过）」——
    用户有权知道结论是建立在残缺数据上的。
    """
    raise NotImplementedError("TODO 12: render_summary")


def render_top(entries: list[LogEntry], n: int, out) -> None:
    """TODO 13：打印 Top N IP，每行带次数、占比和 bar()。"""
    raise NotImplementedError("TODO 13: render_top")


def render_slow(entries: list[LogEntry], n: int, out) -> None:
    """TODO 14：打印最慢的 N 条，带耗时、状态码、方法、路径、时间。"""
    raise NotImplementedError("TODO 14: render_slow")


def render_errors(entries: list[LogEntry], n: int, out) -> None:
    """TODO 15：打印错误分析：状态码分布 + 出错最多的路径。

    ▸ 没有错误时打印「没有错误请求。」然后返回，别继续往下算 max()。
    """
    raise NotImplementedError("TODO 15: render_errors")


def render_hourly(entries: list[LogEntry], out) -> None:
    """TODO 16：打印按小时分布，格式 `09 时  ####  412`。"""
    raise NotImplementedError("TODO 16: render_hourly")


def to_json(entries: list[LogEntry], bad: int) -> str:
    """TODO 17：把所有统计结果序列化成 JSON 字符串。

    结构随意，但要包含 summary / unparsed_lines / top_ips /
    status_distribution / error_breakdown / slowest / hourly。

    ▸ json.dumps(..., ensure_ascii=False, indent=2)
      ensure_ascii 默认是 True，中文会变成 \\uXXXX，文件没法读。
    """
    raise NotImplementedError("TODO 17: to_json")


# ======================================================================
# 五、示例数据 —— 已实现
# ======================================================================
SAMPLE_PATHS = [
    ("GET", "/api/users"),
    ("GET", "/api/users/42"),
    ("POST", "/api/login"),
    ("GET", "/api/orders?page=2"),
    ("POST", "/api/orders"),
    ("GET", "/static/app.js"),
    ("GET", "/health"),
    ("DELETE", "/api/users/7"),
]
SAMPLE_IPS = [
    "203.0.113.7",
    "198.51.100.4",
    "192.0.2.55",
    "203.0.113.91",
    "198.51.100.23",
]


def generate_sample(count: int = 500, seed: int = 20260916) -> str:
    """生成示例日志。固定 seed，所以每次内容完全一样 —— 可复现的数据才能写测试。"""
    rng = random.Random(seed)
    start = datetime(2026, 9, 16, 9, 0, 0)
    lines: list[str] = []

    for _ in range(count):
        ts = start + timedelta(seconds=rng.randint(0, 3 * 3600))
        ip = rng.choice(SAMPLE_IPS)
        method, path = rng.choice(SAMPLE_PATHS)
        roll = rng.random()
        if roll < 0.88:
            status = 200
        elif roll < 0.95:
            status = rng.choice([401, 403, 404])
        else:
            status = rng.choice([500, 502, 503])
        duration = max(1, int(rng.lognormvariate(4.5, 1.0)))
        lines.append(f"{ts.isoformat()}Z {ip} {method} {path} {status} {duration}")

    # 故意掺两行脏数据
    lines.insert(count // 3, "这行是坏的 不是合法日志")
    lines.insert(count // 2, "2026-09-16T10:00:00Z 1.2.3.4 GET /x abc 100")

    return "\n".join(lines) + "\n"


# ======================================================================
# 六、CLI —— 骨架已给好，你只需要实现上面那些函数
# ======================================================================
def _add_input_options(p: argparse.ArgumentParser) -> None:
    p.add_argument("logfile", type=Path, help="日志文件路径")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")


def build_parser() -> argparse.ArgumentParser:
    """已实现。注意所有功能都是子命令，文件路径跟在子命令后面 ——
    这是为了绕开 argparse 「可选位置参数 + 子解析器」那个坑。
    """
    parser = argparse.ArgumentParser(prog="loganalyzer", description="访问日志分析器。")
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("summary", "hourly"):
        _add_input_options(sub.add_parser(name))
    for name in ("top", "slow", "errors"):
        p = sub.add_parser(name)
        _add_input_options(p)
        p.add_argument("--top", type=int, default=10, help="显示多少条（默认 10）")

    p_sample = sub.add_parser("sample")
    p_sample.add_argument("--count", type=int, default=500)
    sub.add_parser("test")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "test":
        return run_tests()
    if args.command == "sample":
        sys.stdout.write(generate_sample(args.count))
        return 0

    if not args.logfile.is_file():
        print(f"错误：找不到文件 {args.logfile}", file=sys.stderr)
        return 1

    entries, bad = load(args.logfile)

    if args.json:
        print(to_json(entries, bad))
        return 0

    top = getattr(args, "top", 10)
    renderers = {
        "summary": lambda: render_summary(entries, bad, sys.stdout),
        "top": lambda: render_top(entries, top, sys.stdout),
        "slow": lambda: render_slow(entries, top, sys.stdout),
        "errors": lambda: render_errors(entries, top, sys.stdout),
        "hourly": lambda: render_hourly(entries, sys.stdout),
    }
    renderers[args.command]()
    return 0


# ======================================================================
# 七、自测
# ======================================================================
GOOD_LINES = [
    "2026-09-16T10:00:00Z 203.0.113.7 GET /api/users 200 120",
    "2026-09-16T10:00:01Z 203.0.113.7 GET /api/users/42 404 15",
    "2026-09-16T10:05:00Z 198.51.100.4 POST /api/login 200 340",
    "2026-09-16T11:00:00Z 198.51.100.4 GET /health 200 5",
    "2026-09-16T11:30:00Z 192.0.2.55 GET /api/orders 500 2500",
]

BAD_LINES = [
    "",
    "只有 两个",
    "2026-09-16T10:00:00Z 1.2.3.4 GET /x abc 100",
    "2026-09-16T10:00:00Z 1.2.3.4 GET /x 200 abc",
    "不是时间戳 1.2.3.4 GET /x 200 100",
    "2026-09-16T10:00:00Z 1.2.3.4 GET /x 999 100",
    "a b c d e f g",
]


def run_tests() -> int:
    failures = 0
    skipped = 0

    def report(label: str, fn) -> None:
        nonlocal failures, skipped
        try:
            fn()
        except NotImplementedError as exc:
            print(f"  [SKIP] {label:<34} {exc}")
            skipped += 1
        except AssertionError as exc:
            print(f"  [FAIL] {label:<34} {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001 - 自测运行器兜住一切
            print(f"  [ERROR] {label:<34} {type(exc).__name__}: {exc}")
            failures += 1
        else:
            print(f"  [PASS] {label}")

    print("=" * 66)
    print("解析")
    print("=" * 66)

    def check_parse() -> None:
        entry = parse_line(GOOD_LINES[0])
        assert entry is not None, "正常行竟然返回了 None"
        assert (entry.ip, entry.method, entry.path, entry.status, entry.duration_ms) == (
            "203.0.113.7", "GET", "/api/users", 200, 120
        ), "字段解析错误"
        assert entry.timestamp.tzinfo is not None, "时间戳是 naive 的，必须用 aware"
        assert entry.timestamp.utcoffset() == timedelta(0), "时间戳不是 UTC"

    report("正常行解析", check_parse)
    for bad in BAD_LINES:
        report(f"坏行返回 None: {bad[:24]!r}", lambda bad=bad: _assert_none(bad))

    print()
    print("=" * 66)
    print("聚合")
    print("=" * 66)

    def entries() -> list[LogEntry]:
        return [e for e in (parse_line(line) for line in GOOD_LINES) if e is not None]

    report("全部解析成功", lambda: _assert(len(entries()) == 5, "条数不对"))
    report(
        "top_ips 并列按字典序",
        lambda: _assert(
            top_ips(entries(), 3)
            == [("198.51.100.4", 2), ("203.0.113.7", 2), ("192.0.2.55", 1)],
            str(top_ips(entries(), 3)),
        ),
    )
    report(
        "状态码分布",
        lambda: _assert(status_distribution(entries()) == {200: 3, 404: 1, 500: 1},
                        str(status_distribution(entries()))),
    )
    report(
        "错误率 2/5",
        lambda: _assert(abs(error_rate(entries()) - 0.4) < 1e-9, str(error_rate(entries()))),
    )
    report(
        "错误状态码分布",
        lambda: _assert(error_breakdown(entries()) == {404: 1, 500: 1},
                        str(error_breakdown(entries()))),
    )
    report(
        "最慢的是 2500ms",
        lambda: _assert(slowest(entries(), 1)[0].duration_ms == 2500, "排序不对"),
    )
    report(
        "按小时分组",
        lambda: _assert(hourly_histogram(entries()) == [(10, 3), (11, 2)],
                        str(hourly_histogram(entries()))),
    )
    report(
        "空列表不炸",
        lambda: _assert(summarize([])["total"] == 0 and error_rate([]) == 0.0, "空输入炸了"),
    )

    print()
    print("=" * 66)
    print("端到端")
    print("=" * 66)

    import tempfile

    def end_to_end() -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "access.log"
            path.write_text(generate_sample(200), encoding="utf-8")
            loaded, bad = load(path)
            assert len(loaded) > 150, f"只解析出 {len(loaded)} 条"
            assert bad == 2, f"坏行数 {bad}，期望 2"
            payload = json.loads(to_json(loaded, bad))
            assert payload["summary"]["total"] == len(loaded)
            assert "\\u" not in to_json(loaded, bad), "中文被转义了"
            assert main(["summary", str(path)]) == 0

    report("生成->解析->统计->JSON", end_to_end)

    print()
    print("=" * 66)
    total = 1 + len(BAD_LINES) + 8 + 1      # 正常行 + 7 条坏行 + 8 项聚合 + 端到端
    print(f"合计约 {total} 项   失败 {failures}   未做 {skipped}")
    if failures:
        print("还有失败项，先看上面带 FAIL / ERROR 的行。")
    elif skipped:
        print("通过的都对了，继续做剩下的 TODO。")
    else:
        print("全部通过。对照 solution.py 看看它的代码组织方式。")
    print("=" * 66)
    return 1 if failures else 0


def _assert(condition: bool, detail: str = "") -> None:
    assert condition, detail


def _assert_none(line: str) -> None:
    assert parse_line(line) is None, f"{line!r} 应该被判为坏行"


if __name__ == "__main__":
    sys.exit(main())
