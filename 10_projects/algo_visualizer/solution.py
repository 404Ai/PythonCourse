"""
项目 D · 算法可视化 —— 参考实现

运行方式：
    python solution.py sort --algo bubble --size 15
    python solution.py sort --algo quick --size 15 --delay 0.02
    python solution.py sort --algo insertion --no-animate
    python solution.py bst --values 5,3,8,1,4,7,9
    python solution.py bst --values 5,3,8 --no-animate
    python solution.py test

核心设计：
    算法是**生成器**，每次 yield 一帧（数组快照 + 高亮下标 + 说明）。
    渲染器消费帧。两者通过 Frame 解耦，谁也不知道对方的存在。

    好处：测试只需要断言「最后一帧是排好序的」，不用跑动画、不用 sleep。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass

# ======================================================================
# 一、帧
# ======================================================================
@dataclass
class Frame:
    """一帧画面。

    values 必须是**快照**（复制过的），不能是算法内部那个列表的引用。
    否则所有帧会共享同一个列表对象，你最后看到的永远是最终状态 —— 这是
    做动画最常见的 bug。
    """

    values: list[int]
    highlight: tuple[int, ...] = ()
    note: str = ""
    # 已经排好、不再参与比较的区域，渲染时用不同样式区分
    settled: tuple[int, ...] = ()


# ======================================================================
# 二、排序算法（生成器）
# ======================================================================
def bubble_sort(data: list[int]) -> Iterator[Frame]:
    """冒泡排序。

    每轮把当前未排序部分的最大值「冒」到末尾。
    每完成一轮，末尾就多一个元素的位置被永久确定（settled）。
    """
    values = list(data)                      # 不改传入的列表
    n = len(values)
    settled: list[int] = []

    yield Frame(values[:], (), "开始：冒泡排序")

    for i in range(n - 1):
        swapped = False
        for j in range(n - 1 - i):
            yield Frame(
                values[:], (j, j + 1),
                f"比较 {values[j]} 和 {values[j + 1]}",
                tuple(settled),
            )
            if values[j] > values[j + 1]:
                values[j], values[j + 1] = values[j + 1], values[j]
                swapped = True
                yield Frame(
                    values[:], (j, j + 1),
                    f"交换 -> {values[j]} 和 {values[j + 1]}",
                    tuple(settled),
                )

        settled.insert(0, n - 1 - i)
        yield Frame(values[:], (), f"第 {i + 1} 轮结束，位置 {n - 1 - i} 已确定",
                    tuple(settled))

        # 优化：这一轮一次都没交换，说明已经有序了，可以直接收工。
        # 最好的情况（输入本来就有序）因此变成 O(n)。
        if not swapped:
            settled[:] = list(range(n))
            yield Frame(values[:], (), "这一轮没有发生交换，已经有序，提前结束",
                        tuple(settled))
            break

    yield Frame(values[:], (), "排序完成", tuple(range(n)))


def insertion_sort(data: list[int]) -> Iterator[Frame]:
    """插入排序。

    维护一个「已排好序的前缀」，每次把下一个元素往左挪到正确位置。
    想象你整理手里的扑克牌。
    """
    values = list(data)
    n = len(values)

    yield Frame(values[:], (), "开始：插入排序")

    for i in range(1, n):
        key = values[i]
        yield Frame(values[:], (i,), f"取出 {key}，准备插入前面的有序区")

        j = i - 1
        while j >= 0 and values[j] > key:
            values[j + 1] = values[j]
            yield Frame(values[:], (j, j + 1), f"{values[j]} 比 {key} 大，往右挪一位")
            j -= 1

        values[j + 1] = key
        yield Frame(values[:], (j + 1,), f"把 {key} 放在位置 {j + 1}")

    yield Frame(values[:], (), "排序完成", tuple(range(n)))


def quick_sort(data: list[int]) -> Iterator[Frame]:
    """快速排序。

    递归生成器：子问题的帧通过 `yield from` 直接冒泡到顶层，
    调用方看到的仍然是一条平坦的帧流。

    ▸ 如果写成 `for f in quick_sort(...): yield f` 效果一样，
      但 `yield from` 更短、更快，也更清楚地表达「委托」的意图。
    """
    values = list(data)

    yield Frame(values[:], (), "开始：快速排序")

    def sort_range(lo: int, hi: int) -> Iterator[Frame]:
        if lo >= hi:
            return
        pivot_index = yield from partition(lo, hi)
        yield from sort_range(lo, pivot_index - 1)
        yield from sort_range(pivot_index + 1, hi)

    def partition(lo: int, hi: int) -> Iterator[Frame]:
        """Lomuto 分区：以最右元素为基准，把比它小的都挪到左边。

        返回基准最终落到的位置。
        """
        pivot = values[hi]
        yield Frame(values[:], (hi,), f"选 {pivot} 作为基准（下标 {hi}）")

        store = lo
        for i in range(lo, hi):
            yield Frame(values[:], (i, hi), f"比较 {values[i]} 和基准 {pivot}",
                        tuple(settled))
            if values[i] < pivot:
                values[store], values[i] = values[i], values[store]
                if store != i:
                    yield Frame(values[:], (store, i),
                                f"{values[store]} < {pivot}，换到左区",
                                tuple(settled))
                store += 1

        values[store], values[hi] = values[hi], values[store]
        settled.add(store)
        yield Frame(values[:], (store,), f"基准 {pivot} 归位到下标 {store}",
                    tuple(sorted(settled)))
        return store

    settled: set[int] = set()
    yield from sort_range(0, len(values) - 1)

    yield Frame(values[:], (), "排序完成", tuple(range(len(values))))


SORT_ALGORITHMS = {
    "bubble": bubble_sort,
    "insertion": insertion_sort,
    "quick": quick_sort,
}


# ======================================================================
# 三、排序的渲染
# ======================================================================
BAR_CHARS = 44          # 柱子的最大宽度


def render_sort_frame(frame: Frame, max_value: int) -> str:
    """把一帧渲染成多行文本。

    用 `#` 和空格，不用方块字符 —— Windows 控制台默认 GBK，
    方块字符可能显示成乱码。本课程所有模块都遵守这条。
    """
    lines: list[str] = []
    width = max(1, max_value)

    for index, value in enumerate(frame.values):
        bar_len = max(1, round(value / width * BAR_CHARS))
        if index in frame.highlight:
            bar = "#" * bar_len
            mark = ">"
        elif index in frame.settled:
            bar = "=" * bar_len
            mark = " "
        else:
            bar = "#" * bar_len
            mark = " "
        lines.append(f"  {mark}{index:>3} |{bar:<{BAR_CHARS}}| {value:>4}")

    lines.append("")
    lines.append(f"  {frame.note}")
    return "\n".join(lines)


# ======================================================================
# 四、二叉搜索树
# ======================================================================
@dataclass
class Node:
    value: int
    left: "Node | None" = None
    right: "Node | None" = None

    def __repr__(self) -> str:
        return f"Node({self.value})"


def insert(root: Node | None, value: int) -> Node:
    """标准 BST 插入。返回值是新的根。"""
    if root is None:
        return Node(value)
    if value < root.value:
        root.left = insert(root.left, value)
    elif value > root.value:
        root.right = insert(root.right, value)
    # 相等就不插入：BST 里通常不允许重复键
    return root


def inorder(root: Node | None) -> list[int]:
    """中序遍历 —— 结果是升序的，这正是 BST 的定义。"""
    if root is None:
        return []
    return inorder(root.left) + [root.value] + inorder(root.right)


def bst_insert(values: list[int]) -> Iterator[tuple[Node | None, int, str]]:
    """逐值插入的生成器。

    每次 yield 一帧 (当前根, 刚插入的值, 说明)。
    这里没有复用 Frame，因为树帧的「值」是一棵树而不是一个列表 ——
    硬塞进同一个数据结构反而更别扭。**不要为了统一而强行统一。**
    """
    root: Node | None = None
    yield root, 0, "开始：空树"
    for value in values:
        if _contains(root, value):
            yield root, value, f"{value} 已经存在，跳过"
            continue
        root = insert(root, value)
        yield root, value, f"插入 {value}"


def _contains(root: Node | None, value: int) -> bool:
    if root is None:
        return False
    if value == root.value:
        return True
    return _contains(root.left if value < root.value else root.right, value)


def render_tree(root: Node | None) -> str:
    """横向渲染二叉树。

    算法：
        1. 中序遍历分配列号：节点从左到右的顺序 == 中序遍历的顺序，
           因为 BST 中序是升序，而图上从左到右也是升序。
        2. 横坐标 = 列号 * 4，纵坐标 = 深度 * 2（中间空一行放连接线）。
        3. 连接线：父在 row，子在 row+2，中间那行画 '/' 和 '\\'。

    空树返回 "(空树)"。
    """
    if root is None:
        return "  (空树)"

    centers: dict[int, int] = {}      # id(node) -> 横坐标（中心）
    depths: dict[int, int] = {}       # id(node) -> 深度
    counter = 0

    def assign(node: Node | None, depth: int) -> None:
        nonlocal counter
        if node is None:
            return
        assign(node.left, depth + 1)
        centers[id(node)] = counter * 4 + 2
        depths[id(node)] = depth
        counter += 1
        assign(node.right, depth + 1)

    assign(root, 0)

    height = (max(depths.values()) + 1) * 2 - 1
    width = counter * 4 + 4
    grid = [[" "] * width for _ in range(height)]

    def put(row: int, col: int, text: str) -> None:
        for offset, char in enumerate(text):
            if 0 <= col + offset < width:
                grid[row][col + offset] = char

    def draw(node: Node | None) -> None:
        if node is None:
            return
        row = depths[id(node)] * 2
        col = centers[id(node)]
        label = str(node.value)
        put(row, col - len(label) // 2, label)

        left, right = node.left, node.right
        if left is not None and right is not None:
            # 两个孩子：左孩子上方画 '/'，右孩子上方画 '\'，
            # 中间用 '-' 连起来，看起来才像一棵树而不是两个孤立的分支。
            connector_row = row + 1
            left_col = centers[id(left)]
            right_col = centers[id(right)]
            put(connector_row, left_col, "/")
            put(connector_row, right_col, "\\")
            for x in range(left_col + 1, right_col):
                if grid[connector_row][x] == " ":
                    grid[connector_row][x] = "-"

        elif left is not None or right is not None:
            # 只有一个孩子：在父与子的中点画一条斜线，
            # 比画一条横跨半张图的横线好看得多。
            child = left if left is not None else right
            assert child is not None
            child_col = centers[id(child)]
            mid = (col + child_col) // 2
            put(row + 1, mid, "/" if child_col < col else "\\")

        draw(node.left)
        draw(node.right)

    draw(root)

    # 去掉每行尾部的空格，避免输出一堆看不见的空白
    return "\n".join("".join(row).rstrip() for row in grid)


# ======================================================================
# 五、动画
# ======================================================================
CLEAR = "\x1b[H\x1b[J"      # 光标回左上角 + 清除到屏幕末尾


def animate(frames: Iterator[str], delay: float, out, enabled: bool = True) -> str:
    """播放帧序列，返回最后一帧的内容。

    ⚠ 两个必须防的坑：

      1. **非交互环境要降级**。把输出重定向到文件时，ANSI 转义序列
         会变成乱码写进文件。所以 enabled=False 时只写最后一帧。

      2. **每帧都要 flush()**。不 flush 的话输出卡在缓冲区，
         动画要等程序结束才一次性显示 —— “动画不动”十有八九是这个原因。
    """
    last = ""
    for text in frames:
        last = text
        if not enabled:
            continue
        out.write(CLEAR)
        out.write(text)
        out.flush()                 # 少了这行动画就不会动
        time.sleep(delay)

    if not enabled and last:
        out.write(last)
        out.write("\n")
        out.flush()
    return last


# ======================================================================
# 六、CLI
# ======================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="visualizer", description="终端里的算法可视化。")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sort = sub.add_parser("sort", help="排序动画")
    p_sort.add_argument("--algo", choices=sorted(SORT_ALGORITHMS), default="bubble")
    p_sort.add_argument("--size", type=int, default=15, help="数据规模（默认 15）")
    p_sort.add_argument("--delay", type=float, default=0.05, help="每帧间隔秒数")
    p_sort.add_argument("--seed", type=int, default=20260916, help="随机种子")
    p_sort.add_argument("--reverse", action="store_true", help="用完全逆序的数据")
    p_sort.add_argument("--no-animate", action="store_true", help="不放动画，只出最终结果")

    p_bst = sub.add_parser("bst", help="二叉搜索树")
    p_bst.add_argument("--values", default="5,3,8,1,4,7,9", help="逗号分隔的整数")
    p_bst.add_argument("--delay", type=float, default=0.35)
    p_bst.add_argument("--no-animate", action="store_true")

    sub.add_parser("test", help="跑自测")
    return parser


def make_data(size: int, seed: int, reverse: bool) -> list[int]:
    """生成数据。固定种子 -> 结果可复现。"""
    import random

    rng = random.Random(seed)
    values = [rng.randint(1, 99) for _ in range(size)]
    if reverse:
        values.sort(reverse=True)
    return values


def run_sort(args: argparse.Namespace) -> int:
    if args.size < 1:
        print("错误：--size 必须大于 0。", file=sys.stderr)
        return 2

    data = make_data(args.size, args.seed, args.reverse)
    algorithm = SORT_ALGORITHMS[args.algo]
    max_value = max(data) if data else 1

    # isatty() 为 False 说明输出被重定向了，这时候不该放动画
    enabled = not args.no_animate and sys.stdout.isatty()

    # 先一次性把帧算出来存好，再交给渲染器。
    # 这样最后一帧的值可以直接从列表里取，不用把生成器再跑一遍。
    raw_frames = list(algorithm(data))
    rendered = (render_sort_frame(f, max_value) for f in raw_frames)

    started = time.perf_counter()
    animate(rendered, args.delay, sys.stdout, enabled=enabled)
    elapsed = time.perf_counter() - started

    if enabled:
        print()
    print(f"算法 {args.algo}   数据 {data}")
    print(f"结果 {sorted(data)}   耗时 {elapsed:.2f}s")

    # 验收项：最后一帧必须真的是排好序的
    ok = raw_frames[-1].values == sorted(data)
    print(f"最后一帧是否已排序：{'是' if ok else '否 —— 有问题！'}")
    return 0 if ok else 1


def run_bst(args: argparse.Namespace) -> int:
    try:
        values = [int(v.strip()) for v in args.values.split(",") if v.strip()]
    except ValueError:
        print(f"错误：--values 必须是逗号分隔的整数，收到 {args.values!r}", file=sys.stderr)
        return 2

    if not values:
        print("错误：至少要给一个值。", file=sys.stderr)
        return 2

    enabled = not args.no_animate and sys.stdout.isatty()
    frames = (
        f"{render_tree(root)}\n\n  {note}"
        for root, _value, note in bst_insert(values)
    )
    animate(frames, args.delay, sys.stdout, enabled=enabled)
    if enabled:
        print()

    root: Node | None = None
    for value in values:
        if not _contains(root, value):
            root = insert(root, value)

    ordered = inorder(root)
    print(f"插入顺序 {values}")
    print(f"中序遍历 {ordered}")
    print(f"是否升序：{'是' if ordered == sorted(set(values)) else '否 —— 有问题！'}")
    return 0 if ordered == sorted(set(values)) else 1


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "test":
        return run_tests()
    if args.command == "sort":
        return run_sort(args)
    return run_bst(args)


# ======================================================================
# 七、自测
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

    # ------------------------------------------------------------------ #
    print("=" * 66)
    print("排序算法：正确性")
    print("=" * 66)

    SAMPLE_CASES: list[list[int]] = [
        [],
        [1],
        [2, 1],
        [1, 2, 3, 4, 5],
        [5, 4, 3, 2, 1],
        [3, 1, 4, 1, 5, 9, 2, 6],
        [7, 7, 7],
    ]

    for name, algorithm in SORT_ALGORITHMS.items():
        for data in SAMPLE_CASES:
            frames = list(algorithm(data))
            final = frames[-1].values
            check(f"{name} 排序 {data}", final == sorted(data), f"得到 {final}")

    print()
    print("=" * 66)
    print("排序算法：不修改入参")
    print("=" * 66)

    for name, algorithm in SORT_ALGORITHMS.items():
        original = [3, 1, 4, 1, 5]
        snapshot = list(original)
        list(algorithm(original))
        check(f"{name} 没有改动传入的列表", original == snapshot, f"变成了 {original}")

    print()
    print("=" * 66)
    print("帧的合法性")
    print("=" * 66)

    for name, algorithm in SORT_ALGORITHMS.items():
        data = [5, 3, 8, 1, 9, 2]
        frames = list(algorithm(data))
        n = len(data)
        check(f"{name} 至少产出一帧", len(frames) >= 1, f"{len(frames)} 帧")
        check(f"{name} 首帧等于原数据", frames[0].values == data)
        check(f"{name} 末帧已排序", frames[-1].values == sorted(data))
        check(
            f"{name} highlight 下标都合法",
            all(0 <= i < n for f in frames for i in f.highlight),
            str([f.highlight for f in frames if any(i >= n or i < 0 for i in f.highlight)]),
        )
        check(
            f"{name} 每帧长度不变",
            all(len(f.values) == n for f in frames),
            "有帧的长度不对",
        )
        # 每帧都应该是独立的列表对象，不能共享引用
        check(
            f"{name} 每帧是独立快照",
            len({id(f.values) for f in frames}) == len(frames),
            "有帧共享了同一个列表对象（快照没复制）",
        )

    print()
    print("=" * 66)
    print("渲染")
    print("=" * 66)

    frames = list(bubble_sort([3, 1, 2]))
    text = render_sort_frame(frames[0], max_value=3)
    check("渲染结果非空", bool(text.strip()))
    check("渲染结果不含 ANSI 转义", "\x1b" not in text, "渲染函数本身不该输出转义序列")
    check("渲染结果里数值都出现了", all(str(v) in text for v in (1, 2, 3)))

    # 数据全为 0 时不能除零
    zero_frame = Frame([0, 0], (), "全零")
    check("全零数据不崩", bool(render_sort_frame(zero_frame, max_value=0).strip()))

    print()
    print("=" * 66)
    print("二叉搜索树")
    print("=" * 66)

    root: Node | None = None
    for value in [5, 3, 8, 1, 4, 7, 9]:
        root = insert(root, value)

    check("中序遍历是升序", inorder(root) == [1, 3, 4, 5, 7, 8, 9], str(inorder(root)))

    rendered = render_tree(root)
    check("树渲染非空", bool(rendered.strip()))
    check("树里有 5", "5" in rendered and "8" in rendered)
    check("渲染不含 ANSI 转义", "\x1b" not in rendered)

    # 关键验收：从左到右读就是升序
    # 做法：找出每个数字第一次出现的列号，然后检查列号顺序 == 升序
    positions: list[tuple[int, int]] = []
    for line in rendered.splitlines():
        for col, char in enumerate(line):
            if char.isdigit():
                positions.append((col, int(char)))
    # 数字都是一位数，所以 (列号, 值) 按列号排序后，值应该是升序
    sorted_by_col = [v for _, v in sorted(set(positions))]
    check("从左到右读是升序", sorted_by_col == sorted(sorted_by_col), str(sorted_by_col))

    check("空树能渲染", render_tree(None) == "  (空树)")

    # 重复值不该被插入两次
    root2: Node | None = None
    for value in [5, 5, 5]:
        root2 = insert(root2, value)
    check("重复值只插入一次", inorder(root2) == [5], str(inorder(root2)))

    # 生成器版本
    frames_bst = list(bst_insert([5, 3, 8, 3]))
    check("bst_insert 产出帧", len(frames_bst) >= 1)
    check("bst_insert 跳过重复值",
          any("已经存在" in note for _, _, note in frames_bst),
          str([note for _, _, note in frames_bst]))

    # 极端输入
    degenerate: Node | None = None
    for value in range(1, 8):
        degenerate = insert(degenerate, value)
    check("退化成链也能渲染", bool(render_tree(degenerate).strip()))
    check("链的中序仍是升序", inorder(degenerate) == list(range(1, 8)))

    print()
    print("=" * 66)
    print("动画")
    print("=" * 66)

    import io

    def collect(enabled: bool) -> str:
        buffer = io.StringIO()
        animate(iter(["第一帧", "第二帧", "第三帧"]), 0.0, buffer, enabled=enabled)
        return buffer.getvalue()

    animated = collect(enabled=True)
    check("开启动画时每帧都清屏", animated.count(CLEAR) == 3, str(animated.count(CLEAR)))

    plain = collect(enabled=False)
    check("关闭动画时不输出 ANSI 转义", "\x1b" not in plain, repr(plain))
    check("关闭动画时只输出最后一帧", plain.strip() == "第三帧", repr(plain))

    print()
    print("=" * 66)
    print("CLI")
    print("=" * 66)

    check("未知算法被 argparse 拦下", _expect_system_exit(["sort", "--algo", "nope"]))
    check("--size 0 返回退出码 2", main(["sort", "--algo", "bubble", "--size", "0"]) == 2)
    check("bad --values 返回退出码 2", main(["bst", "--values", "a,b"]) == 2)
    check("空 --values 返回退出码 2", main(["bst", "--values", ""]) == 2)

    # 跑一遍真实的 --no-animate 路径（stdout 被重定向，自动降级）
    check("--no-animate 排序退出码 0",
          main(["sort", "--algo", "quick", "--size", "8", "--no-animate"]) == 0)
    check("--no-animate BST 退出码 0",
          main(["bst", "--values", "5,3,8", "--no-animate"]) == 0)

    print()
    print("=" * 66)
    if failures:
        print(f"{failures} 项未通过")
    else:
        print("全部通过。")
    print("=" * 66)
    return 1 if failures else 0


def _expect_system_exit(argv: list[str]) -> bool:
    try:
        main(argv)
    except SystemExit as exc:
        return exc.code == 2
    return False


if __name__ == "__main__":
    sys.exit(main())
