"""
项目 B · 日志分析 CLI —— 参考实现

运行方式（子命令在前，日志文件路径在后）：
    python solution.py sample > access.log      生成一份示例日志
    python solution.py summary access.log
    python solution.py top access.log --top 5
    python solution.py slow access.log --top 5
    python solution.py errors access.log
    python solution.py hourly access.log
    python solution.py test                     跑自测

设计要点：
    解析 -> 聚合 -> 呈现，三段分离。
    聚合函数全是纯函数（输入 list[LogEntry]，输出结果），
    不碰文件也不 print，所以能单独测试、也能同时喂给文本和 JSON 两种输出。
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

# ======================================================================
# 一、数据模型
# ======================================================================
@dataclass(frozen=True)
class LogEntry:
    """一条访问记录。

    frozen=True 让它变成不可变的值对象，顺带获得 __hash__ ——
    这样它既能放进 set 去重，也能当 dict 的键。
    对「日志行」这种天然不变的东西，冻结是合适的。

    timestamp 用 aware datetime（带时区）。日志里的 Z 表示 UTC，
    解析后 tzinfo 是 timezone.utc。naive datetime 在比较和换算时
    行为是错的，而且错得很隐蔽——模块 07 讲过这一点。
    """

    timestamp: datetime
    ip: str
    method: str
    path: str
    status: int
    duration_ms: int

    @property
    def is_error(self) -> bool:
        """4xx 和 5xx 都算错误（客户端错 + 服务端错）。"""
        return self.status >= 400

    def to_dict(self) -> dict[str, object]:
        data = asdict(self)
        # asdict 会把 datetime 原样留着，json.dumps 认不了，得转成字符串
        data["timestamp"] = self.timestamp.isoformat()
        return data


# ======================================================================
# 二、解析
# ======================================================================
def parse_line(line: str) -> LogEntry | None:
    """解析一行日志。坏行返回 None，不抛异常。

    为什么不抛异常：
        日志分析的正确行为是「跳过坏行继续」，一行脏数据不该让
        整次分析失败。但坏行数必须被统计并报给用户，
        否则就成了静默丢数据。
    """
    parts = line.split()
    if len(parts) != 6:
        return None

    raw_ts, ip, method, path, raw_status, raw_duration = parts

    try:
        # 3.11+ 的 fromisoformat 能直接吃结尾的 'Z'。
        # 老版本要手动替换：raw_ts.replace("Z", "+00:00")
        timestamp = datetime.fromisoformat(raw_ts)
        status = int(raw_status)
        duration_ms = int(raw_duration)
    except ValueError:
        # 时间戳/状态码/耗时任何一个格式不对，整行判为坏行。
        # 只捕获 ValueError：其他异常（比如 TypeError）属于真 bug，
        # 应该让它带着 traceback 崩掉，而不是被当成「数据问题」吞掉。
        return None

    if not 100 <= status <= 599:
        return None

    return LogEntry(
        timestamp=timestamp,
        ip=ip,
        method=method,
        path=path,
        status=status,
        duration_ms=duration_ms,
    )


def load(path: Path) -> tuple[list[LogEntry], int]:
    """读文件，返回 (成功解析的条目, 无法解析的行数)。

    encoding="utf-8" 是必须的。不写的话 Windows 上用系统默认的 GBK，
    日志里有中文（用户代理、错误信息）就会乱码或直接抛 UnicodeDecodeError。
    """
    entries: list[LogEntry] = []
    bad = 0

    with path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue  # 空行跳过，不算坏行
            entry = parse_line(line)
            if entry is None:
                bad += 1
            else:
                entries.append(entry)

    return entries, bad


# ======================================================================
# 三、聚合 —— 全是纯函数
# ======================================================================
def top_ips(entries: list[LogEntry], n: int = 10) -> list[tuple[str, int]]:
    """请求数最多的 N 个 IP。

    Counter.most_common 在计数相同时按插入顺序返回，结果不确定。
    这里自己排序，并列时按 IP 字典序 —— 输出稳定才好做测试。
    """
    counts = Counter(entry.ip for entry in entries)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def status_distribution(entries: list[LogEntry]) -> dict[int, int]:
    """状态码分布，按状态码升序。"""
    counts = Counter(entry.status for entry in entries)
    return dict(sorted(counts.items()))


def slowest(entries: list[LogEntry], n: int = 10) -> list[LogEntry]:
    """最慢的 N 条请求。并列时按时间先后排，保证结果稳定。"""
    return sorted(entries, key=lambda e: (-e.duration_ms, e.timestamp))[:n]


def error_rate(entries: list[LogEntry]) -> float:
    """错误率：4xx + 5xx 占总数的比例。空列表返回 0.0。"""
    if not entries:
        return 0.0
    return sum(1 for e in entries if e.is_error) / len(entries)


def error_breakdown(entries: list[LogEntry]) -> dict[int, int]:
    """只统计错误状态码的分布。"""
    counts = Counter(e.status for e in entries if e.is_error)
    return dict(sorted(counts.items()))


def error_paths(entries: list[LogEntry], n: int = 10) -> list[tuple[str, int]]:
    """出错最多的路径。"""
    counts = Counter(e.path for e in entries if e.is_error)
    return sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:n]


def hourly_histogram(entries: list[LogEntry]) -> list[tuple[int, int]]:
    """按小时统计请求量，返回 [(小时, 次数), ...]，小时从 0 到 23 只列出有数据的。

    时间戳是 UTC 的，所以这里统计的是 UTC 小时。
    要转本地时间得先 .astimezone()，那会引入「你的机器在哪个时区」
    这个变量，结果就不可复现了 —— 分析工具应该保持确定性。
    """
    counts = Counter(e.timestamp.hour for e in entries)
    return sorted(counts.items())


def summarize(entries: list[LogEntry]) -> dict[str, object]:
    """汇总统计。返回普通 dict，方便直接 json.dumps。"""
    if not entries:
        return {
            "total": 0,
            "unique_ips": 0,
            "error_rate": 0.0,
            "avg_duration_ms": 0.0,
            "max_duration_ms": 0,
            "start": None,
            "end": None,
        }

    timestamps = [e.timestamp for e in entries]
    durations = [e.duration_ms for e in entries]
    return {
        "total": len(entries),
        "unique_ips": len({e.ip for e in entries}),
        "error_rate": round(error_rate(entries), 4),
        "avg_duration_ms": round(sum(durations) / len(durations), 1),
        "max_duration_ms": max(durations),
        "start": min(timestamps).isoformat(),
        "end": max(timestamps).isoformat(),
    }


# ======================================================================
# 四、呈现
# ======================================================================
def bar(value: int, maximum: int, width: int = 30) -> str:
    """按比例画一个条。用 # 而不是方块字符，避免控制台编码问题。"""
    if maximum <= 0:
        return ""
    filled = round(value / maximum * width)
    return "#" * max(filled, 1 if value else 0)


def render_summary(entries: list[LogEntry], bad: int, out) -> None:
    s = summarize(entries)
    print("=" * 60, file=out)
    print("总览", file=out)
    print("=" * 60, file=out)
    print(f"  总请求数      {s['total']}", file=out)
    print(f"  独立 IP 数    {s['unique_ips']}", file=out)
    print(f"  错误率        {s['error_rate']:.2%}", file=out)
    print(f"  平均耗时      {s['avg_duration_ms']} ms", file=out)
    print(f"  最慢请求      {s['max_duration_ms']} ms", file=out)
    print(f"  时间范围      {s['start']}  ~  {s['end']}", file=out)
    if bad:
        # 坏行数必须报出来。不报的话用户不知道结论是建立在残缺数据上的。
        print(f"  无法解析的行  {bad} 行（已跳过）", file=out)
    print(file=out)


def render_top(entries: list[LogEntry], n: int, out) -> None:
    rows = top_ips(entries, n)
    total = len(entries) or 1
    maximum = rows[0][1] if rows else 0

    print("=" * 60, file=out)
    print(f"Top {n} IP", file=out)
    print("=" * 60, file=out)
    for ip, count in rows:
        share = count / total
        print(f"  {ip:<16} {count:>6}  {share:>6.2%}  {bar(count, maximum)}", file=out)
    print(file=out)


def render_slow(entries: list[LogEntry], n: int, out) -> None:
    print("=" * 60, file=out)
    print(f"最慢的 {n} 条请求", file=out)
    print("=" * 60, file=out)
    for e in slowest(entries, n):
        ts = e.timestamp.strftime("%m-%d %H:%M:%S")
        print(
            f"  {e.duration_ms:>6} ms  {e.status}  {e.method:<4} {e.path}  [{ts}]",
            file=out,
        )
    print(file=out)


def render_errors(entries: list[LogEntry], n: int, out) -> None:
    breakdown = error_breakdown(entries)
    total_errors = sum(breakdown.values())

    print("=" * 60, file=out)
    print("错误分析", file=out)
    print("=" * 60, file=out)
    if not breakdown:
        print("  没有错误请求。", file=out)
        print(file=out)
        return

    maximum = max(breakdown.values())
    for status, count in breakdown.items():
        print(f"  {status}  {count:>6}  {bar(count, maximum)}", file=out)
    print(f"  合计 {total_errors} 条错误请求", file=out)
    print(file=out)

    print(f"  出错最多的路径（Top {n}）：", file=out)
    for path, count in error_paths(entries, n):
        print(f"    {count:>5}  {path}", file=out)
    print(file=out)


def render_hourly(entries: list[LogEntry], out) -> None:
    rows = hourly_histogram(entries)
    print("=" * 60, file=out)
    print("按小时分布（UTC）", file=out)
    print("=" * 60, file=out)
    maximum = max((c for _, c in rows), default=0)
    for hour, count in rows:
        print(f"  {hour:02d} 时  {bar(count, maximum, 34):<34} {count}", file=out)
    print(file=out)


def to_json(entries: list[LogEntry], bad: int) -> str:
    """把所有统计结果序列化成 JSON。

    ensure_ascii=False 让中文原样输出（模块 06 讲过）。
    """
    payload = {
        "summary": summarize(entries),
        "unparsed_lines": bad,
        "top_ips": [{"ip": ip, "count": c} for ip, c in top_ips(entries, 10)],
        "status_distribution": status_distribution(entries),
        "error_breakdown": error_breakdown(entries),
        "slowest": [e.to_dict() for e in slowest(entries, 10)],
        "hourly": [{"hour": h, "count": c} for h, c in hourly_histogram(entries)],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


# ======================================================================
# 五、示例数据生成
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
    """生成一份示例日志。

    用固定的 seed，所以每次生成的**内容完全一样**——
    可复现的测试数据是能写测试的前提。用 time.time() 当种子的话，
    今天跑通明天挂掉，你会怀疑人生。
    """
    rng = random.Random(seed)
    start = datetime(2026, 9, 16, 9, 0, 0)
    lines: list[str] = []

    for _ in range(count):
        ts = start + timedelta(seconds=rng.randint(0, 3 * 3600))
        ip = rng.choice(SAMPLE_IPS)
        method, path = rng.choice(SAMPLE_PATHS)
        # 大部分是 200，偶尔 4xx，偶尔 5xx
        roll = rng.random()
        if roll < 0.88:
            status = 200
        elif roll < 0.95:
            status = rng.choice([401, 403, 404])
        else:
            status = rng.choice([500, 502, 503])
        duration = max(1, int(rng.lognormvariate(4.5, 1.0)))
        lines.append(
            f"{ts.isoformat()}Z {ip} {method} {path} {status} {duration}"
        )

    # 故意掺两行脏数据，逼着使用者处理坏行
    lines.insert(count // 3, "这行是坏的 不是合法日志")
    lines.insert(count // 2, "2026-09-16T10:00:00Z 1.2.3.4 GET /x abc 100")

    return "\n".join(lines) + "\n"


# ======================================================================
# 六、CLI
# ======================================================================
def _add_input_options(p: argparse.ArgumentParser) -> None:
    """给分析类子命令加上「输入文件 + 输出格式」这两个公共参数。

    抽成函数而不是复制粘贴：以后加一个子命令，只要调一次这个函数，
    参数定义不会漏、也不会写歪。
    """
    p.add_argument("logfile", type=Path, help="日志文件路径")
    p.add_argument("--json", action="store_true", help="以 JSON 输出")


def build_parser() -> argparse.ArgumentParser:
    """构造解析器。

    ── 为什么是「全子命令」结构，而不是 `loganalyzer <文件> <子命令>` ──

    最初写的是后者：一个可选的位置参数 logfile 放在子命令前面。
    结果 argparse 在这个组合上行为很怪（这是它的老毛病，
    可选位置参数和子解析器放一起就会互相打架）：

        loganalyzer access.log summary            能跑
        loganalyzer access.log summary --json     报错：unrecognized arguments: --json
        loganalyzer access.log --json             报错：把文件名当成了子命令名

    第二条尤其反直觉 —— 子命令吃掉 summary 之后，剩下的 --json
    被丢给**子解析器**，而子解析器不认识它。

    改成「所有功能都是子命令、文件路径在子命令后面」之后，
    每种写法都只有一个确定的结果，不需要记特例：

        loganalyzer summary access.log
        loganalyzer summary access.log --json
        loganalyzer top access.log --top 5

    ▸ 教训：**CLI 设计要优先考虑「所有合法写法都符合直觉」**，
      而不是「我能少写一个子命令」。
      一个需要用户去记特例的命令行工具，不如多敲几个字。
    """
    parser = argparse.ArgumentParser(
        prog="loganalyzer",
        description="一个极简的访问日志分析器。",
        epilog="示例：python solution.py top access.log --top 5",
    )
    # required=True 让漏写子命令时直接报错，而不是静默什么都不做
    sub = parser.add_subparsers(dest="command", required=True)

    for name in ("summary", "hourly"):
        _add_input_options(sub.add_parser(name))

    # top / slow / errors 都需要 --top，用循环加而不是复制三遍
    for name in ("top", "slow", "errors"):
        p = sub.add_parser(name)
        _add_input_options(p)
        p.add_argument("--top", type=int, default=10, help="显示多少条（默认 10）")

    p_sample = sub.add_parser("sample", help="生成示例日志到 stdout")
    p_sample.add_argument("--count", type=int, default=500, help="生成多少行")

    sub.add_parser("test", help="跑自测")

    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "test":
        return run_tests()

    if args.command == "sample":
        sys.stdout.write(generate_sample(args.count))
        return 0

    if not args.logfile.is_file():
        # 友好提示 + 非零退出码。别甩 traceback。
        print(f"错误：找不到文件 {args.logfile}", file=sys.stderr)
        return 1

    entries, bad = load(args.logfile)

    if args.json:
        print(to_json(entries, bad))
        return 0

    # 这几个渲染函数签名不完全一样（有的要 bad，有的要 top），
    # 用闭包包一层，主流程就只剩「按名字取一个来执行」。
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


def run_tests() -> int:
    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"  [PASS] {label}")
        else:
            print(f"  [FAIL] {label}  {detail}")
            failures += 1

    print("=" * 60)
    print("解析")
    print("=" * 60)

    entry = parse_line(GOOD_LINES[0])
    check("正常行能解析", entry is not None)
    assert entry is not None
    check("字段正确",
          (entry.ip, entry.method, entry.path, entry.status, entry.duration_ms)
          == ("203.0.113.7", "GET", "/api/users", 200, 120))
    check("时间戳是 aware 的", entry.timestamp.tzinfo is not None)
    check("时间戳是 UTC", entry.timestamp.utcoffset() == timedelta(0))

    for bad_line in [
        "",
        "只有 两个",
        "2026-09-16T10:00:00Z 1.2.3.4 GET /x abc 100",     # 状态码不是数字
        "2026-09-16T10:00:00Z 1.2.3.4 GET /x 200 abc",     # 耗时不是数字
        "不是时间戳 1.2.3.4 GET /x 200 100",               # 时间戳不对
        "2026-09-16T10:00:00Z 1.2.3.4 GET /x 999 100",     # 状态码越界
        "a b c d e f g",                                   # 字段数量不对
    ]:
        check(f"坏行返回 None: {bad_line[:28]!r}", parse_line(bad_line) is None)

    print()
    print("=" * 60)
    print("聚合")
    print("=" * 60)

    entries = [e for e in (parse_line(line) for line in GOOD_LINES) if e is not None]
    check("全部解析成功", len(entries) == 5)

    # 两个 IP 都是 2 次，并列时按 IP 字典序：'1' < '2'，
    # 所以 198.51.100.4 排在 203.0.113.7 前面。
    # （第一次写这条断言时我按「先出现的排前面」写的，跑挂了 ——
    #   并列时的顺序必须由规则决定，不能靠 Counter 的插入顺序。）
    check("top_ips 排序正确",
          top_ips(entries, 3) == [("198.51.100.4", 2), ("203.0.113.7", 2), ("192.0.2.55", 1)],
          str(top_ips(entries, 3)))

    check("状态码分布", status_distribution(entries) == {200: 3, 404: 1, 500: 1},
          str(status_distribution(entries)))
    check("错误率 = 2/5", abs(error_rate(entries) - 0.4) < 1e-9, str(error_rate(entries)))
    check("错误分布", error_breakdown(entries) == {404: 1, 500: 1},
          str(error_breakdown(entries)))
    check("最慢的是 2500ms", slowest(entries, 1)[0].duration_ms == 2500)
    check("按小时分组",
          hourly_histogram(entries) == [(10, 3), (11, 2)],
          str(hourly_histogram(entries)))
    check("空列表不炸", summarize([])["total"] == 0 and error_rate([]) == 0.0)

    print()
    print("=" * 60)
    print("端到端：生成的示例日志能被自己解析")
    print("=" * 60)

    import io
    import tempfile

    text = generate_sample(200)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "access.log"
        path.write_text(text, encoding="utf-8")
        loaded, bad = load(path)
        check("解析出条目", len(loaded) > 150, f"只解析出 {len(loaded)} 条")
        check("坏行被统计到", bad == 2, f"坏行数 {bad}，期望 2")

        # --json 输出必须能被解析回来
        payload = json.loads(to_json(loaded, bad))
        check("JSON 可解析", payload["summary"]["total"] == len(loaded))
        check("JSON 里中文不转义", "\\u" not in to_json(loaded, bad))

        # 各种子命令和参数组合都要能跑通
        for argv in (
            ["summary", str(path)],
            ["summary", str(path), "--json"],
            ["top", str(path), "--top", "3"],
            ["top", str(path), "--top", "3", "--json"],
            ["slow", str(path)],
            ["errors", str(path), "--top", "3"],
            ["hourly", str(path)],
        ):
            buffer = io.StringIO()
            old = sys.stdout
            sys.stdout = buffer
            try:
                code = main(argv)
            finally:
                sys.stdout = old
            check(f"main({' '.join(argv)}) 退出码 0", code == 0)

        # --json 的输出必须是合法 JSON
        buffer = io.StringIO()
        old = sys.stdout
        sys.stdout = buffer
        try:
            main(["summary", str(path), "--json"])
        finally:
            sys.stdout = old
        check("--json 输出可被 json.loads", isinstance(json.loads(buffer.getvalue()), dict))

    check("文件不存在返回 1", main(["summary", "不存在的文件.log"]) == 1)

    # 漏写子命令：argparse 直接 SystemExit(2)，这是预期行为
    try:
        main([])
    except SystemExit as exc:
        check("漏写子命令退出码为 2", exc.code == 2, f"拿到 {exc.code}")
    else:
        check("漏写子命令退出码为 2", False, "竟然没报错")

    print()
    print("=" * 60)
    if failures:
        print(f"{failures} 项未通过")
    else:
        print("全部通过。")
    print("=" * 60)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
