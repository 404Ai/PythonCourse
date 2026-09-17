"""
项目 D · 算法可视化 —— 骨架

要填的地方标了 TODO。运行方式：

    python starter.py test                              看进度
    python starter.py sort --algo bubble --size 15
    python starter.py sort --algo quick --no-animate
    python starter.py bst --values 5,3,8,1,4,7,9

详细提示见 README.md，参考答案见 solution.py。

核心思路：**算法是生成器，每次 yield 一帧。**
渲染器和算法互不认识，只通过 Frame 这个数据结构打交道。
想清楚这一点，剩下的都是体力活。
"""

from __future__ import annotations

import argparse
import shutil
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass

# ======================================================================
# 一、帧 —— 已给好
# ======================================================================
@dataclass
class Frame:
    """一帧画面。

    ⚠ values 必须是**快照**（复制过的），不能是算法内部那个列表的引用。
      否则所有帧共享同一个列表对象，你最后看到的永远是最终状态 ——
      这是做动画最常见的 bug，而且症状很迷惑（「动画直接跳到结尾」）。
    """

    values: list[int]
    highlight: tuple[int, ...] = ()
    note: str = ""
    settled: tuple[int, ...] = ()


# ======================================================================
# 二、排序算法
# ======================================================================
def bubble_sort(data: list[int]) -> Iterator[Frame]:
    """TODO 1：冒泡排序，产出每一帧。

    步骤：
        values = list(data)          # 不许改传入的列表
        n = len(values)
        settled: list[int] = []
        yield Frame(values[:], (), "开始：冒泡排序")

        for i in range(n - 1):
            swapped = False
            for j in range(n - 1 - i):
                yield Frame(values[:], (j, j + 1),
                            f"比较 {values[j]} 和 {values[j+1]}", tuple(settled))
                if values[j] > values[j + 1]:
                    交换
                    swapped = True
                    yield Frame(values[:], (j, j+1), "交换 -> ...", tuple(settled))
            settled.insert(0, n - 1 - i)
            yield Frame(values[:], (), f"第 {i+1} 轮结束...", tuple(settled))
            # 优化：一次都没交换说明已经有序，提前收工
            if not swapped:
                yield Frame(values[:], (), "已经有序，提前结束", tuple(range(n)))
                break

        yield Frame(values[:], (), "排序完成", tuple(range(n)))

    ▸ 注意 yield 出来的是 values[:]（切片复制），不是 values。
    ▸ settled 记录「已经排好、不再参与比较」的下标，渲染时会有不同样式。
    """
    raise NotImplementedError("TODO 1: bubble_sort")


def insertion_sort(data: list[int]) -> Iterator[Frame]:
    """TODO 2：插入排序。

    维护一个已排序的前缀。每轮取出 values[i]，往左挪到正确位置。

        for i in range(1, n):
            key = values[i]
            yield Frame(values[:], (i,), f"取出 {key}...")
            j = i - 1
            while j >= 0 and values[j] > key:
                values[j+1] = values[j]        # 往右挪一格
                yield Frame(values[:], (j, j+1), "...")
                j -= 1
            values[j+1] = key
            yield Frame(values[:], (j+1,), f"把 {key} 放在位置 {j+1}")

    ▸ 注意最后是 values[j+1] = key，不是 values[j]。j 已经多减了一次。
    """
    raise NotImplementedError("TODO 2: insertion_sort")


def quick_sort(data: list[int]) -> Iterator[Frame]:
    """TODO 3：快速排序（递归生成器）。

    外面包一层，里面用两个嵌套生成器函数：

        def sort_range(lo, hi):
            if lo >= hi: return
            pivot_index = yield from partition(lo, hi)
            yield from sort_range(lo, pivot_index - 1)
            yield from sort_range(pivot_index + 1, hi)

        def partition(lo, hi):
            # Lomuto 分区：以 values[hi] 为基准
            # 把比它小的都换到左区，最后把基准换到分界点上
            返回基准最终的下标

        yield from sort_range(0, len(values) - 1)

    ▸ **`yield from` 是关键**：它让子生成器产出的帧直接冒泡到顶层，
      调用方看到的是一条平坦的帧流，不需要自己递归展开。
    ▸ partition 里每次交换都要 yield 一帧，这样动画才看得出分区过程。
    """
    raise NotImplementedError("TODO 3: quick_sort")


SORT_ALGORITHMS = {
    "bubble": bubble_sort,
    "insertion": insertion_sort,
    "quick": quick_sort,
}


# ======================================================================
# 三、排序渲染
# ======================================================================
BAR_CHARS = 44


def render_sort_frame(frame: Frame, max_value: int) -> str:
    """TODO 4：把一帧渲染成多行文本。

    每一行形如：
        "   1 |####################                        |   42"

    格式：两个空格，标记位（高亮时是 '>'，否则空格），
         下标右对齐占 3 位，" |"，柱子，"| "，数值右对齐占 4 位。

    柱子长度：
        bar_len = max(1, round(value / width * BAR_CHARS))
        width = max(1, max_value)     # 防 max_value 为 0 时除零

    柱子样式：
        下标在 highlight 里  -> 用 '#'
        下标在 settled 里    -> 用 '='
        其他                 -> 用 '#'

    最后追加一个空行和 frame.note。

    ▸ **用 '#' 和 '='，不要用 █ 之类的方块字符** ——
      Windows 控制台默认 GBK，方块字符会显示成乱码。
    ▸ 这个函数是纯函数（输入 Frame 输出 str），所以测试它不需要动画、
      也不需要 sleep。这就是把渲染和动画分开的价值。
    """
    raise NotImplementedError("TODO 4: render_sort_frame")


# ======================================================================
# 四、二叉搜索树
# ======================================================================
@dataclass
class Node:
    value: int
    left: "Node | None" = None
    right: "Node | None" = None


def insert(root: Node | None, value: int) -> Node:
    """TODO 5：标准 BST 插入，返回新的根。

        root is None            -> return Node(value)
        value < root.value      -> root.left = insert(root.left, value)
        value > root.value      -> root.right = insert(root.right, value)
        相等                    -> 不插入（BST 里通常不允许重复键）
        return root

    ▸ 递归写法只有四行。注意最后一定要 return root，
      而且左右分支的返回值要**赋回去**（root.left = ...），
      否则新节点接不上。
    """
    raise NotImplementedError("TODO 5: insert")


def inorder(root: Node | None) -> list[int]:
    """TODO 6：中序遍历，返回升序列表。

        if root is None: return []
        return inorder(root.left) + [root.value] + inorder(root.right)

    ▸ 三行。但它是理解「为什么横向渲染能用中序定横坐标」的关键：
      中序顺序 == 从左到右的顺序 == 升序顺序，三者是同一件事。
    """
    raise NotImplementedError("TODO 6: inorder")


def bst_insert(values: list[int]) -> Iterator[tuple[Node | None, int, str]]:
    """TODO 7：逐值插入的生成器，每帧 yield (当前根, 插入的值, 说明)。

        root = None
        yield root, 0, "开始：空树"
        for value in values:
            if 已经存在:
                yield root, value, f"{value} 已经存在，跳过"
                continue
            root = insert(root, value)
            yield root, value, f"插入 {value}"

    ▸ 「已经存在」要自己写个递归查找（见 solution.py 的 _contains），
      或者用 inorder(root) 取出所有值再判断 —— 后者简单但慢，
      树很大时是 O(n) 而不是 O(log n)。
    """
    raise NotImplementedError("TODO 7: bst_insert")


def render_tree(root: Node | None) -> str:
    """TODO 8：横向渲染二叉树。

    目标效果：
                      5
              /-------------------\\
              3                   8
      /-----------\\           /-------\\
      1           4           7       9

    算法（三步）：
        1. 中序遍历，给每个节点分配一个递增的列号
           centers[id(node)] = 列号 * 4 + 2
           depths[id(node)] = 深度
        2. 建一个二维字符网格，高度 = (最大深度+1)*2 - 1，
           宽度 = 节点数*4 + 4。标签画在 row = 深度*2 那一行。
        3. 画连接线（在 row+1 那一行）：
             两个孩子 -> 左孩子列画 '/'，右孩子列画 '\\'，
                          中间用 '-' 填满
             只有一个孩子 -> 在父子列号的中点画一条斜线
        最后把每行 rstrip() 掉尾部空格。

    ▸ 空树返回 "  (空树)"。
    ▸ 用 id(node) 当字典键，因为 Node 是 dataclass 但没有 frozen，
      默认不可哈希。
    ▸ **先做一个能跑的纵向缩进版本也行**（每层加前缀），
      那个二十行就写完，而且绝对不会错。先做对再做好看。
    """
    raise NotImplementedError("TODO 8: render_tree")


# ======================================================================
# 五、动画
# ======================================================================
CLEAR = "\x1b[H\x1b[J"      # 光标回左上角 + 清除到屏幕末尾


def animate(frames: Iterator[str], delay: float, out, enabled: bool = True) -> str:
    """TODO 9：播放帧序列，返回最后一帧的内容。

        last = ""
        for text in frames:
            last = text
            if not enabled:
                continue
            out.write(CLEAR)
            out.write(text)
            out.flush()            # ！！！这行不能少
            time.sleep(delay)

        if not enabled and last:
            out.write(last)
            out.write("\\n")
            out.flush()
        return last

    ▸ **flush() 是动画能不能动的关键**。不 flush 的话输出卡在缓冲区，
      动画要等程序结束才一次性显示出来。「动画不动」十有八九是这个原因。
    ▸ enabled=False 时只输出最后一帧，一行 ANSI 都不写 ——
      输出被重定向到文件时，转义序列会变成乱码。
    """
    raise NotImplementedError("TODO 9: animate")


# ======================================================================
# 六、CLI —— 已给好
# ======================================================================
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="visualizer", description="终端里的算法可视化。")
    sub = parser.add_subparsers(dest="command", required=True)

    p_sort = sub.add_parser("sort", help="排序动画")
    p_sort.add_argument("--algo", choices=sorted(SORT_ALGORITHMS), default="bubble")
    p_sort.add_argument("--size", type=int, default=15)
    p_sort.add_argument("--delay", type=float, default=0.05)
    p_sort.add_argument("--seed", type=int, default=20260916)
    p_sort.add_argument("--reverse", action="store_true", help="用完全逆序的数据")
    p_sort.add_argument("--no-animate", action="store_true")

    p_bst = sub.add_parser("bst", help="二叉搜索树")
    p_bst.add_argument("--values", default="5,3,8,1,4,7,9")
    p_bst.add_argument("--delay", type=float, default=0.35)
    p_bst.add_argument("--no-animate", action="store_true")

    sub.add_parser("test")
    return parser


def make_data(size: int, seed: int, reverse: bool) -> list[int]:
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

    raw_frames = list(algorithm(data))
    rendered = (render_sort_frame(f, max_value) for f in raw_frames)

    started = time.perf_counter()
    animate(rendered, args.delay, sys.stdout, enabled=enabled)
    elapsed = time.perf_counter() - started

    if enabled:
        print()
    print(f"算法 {args.algo}   数据 {data}")
    print(f"结果 {sorted(data)}   耗时 {elapsed:.2f}s")
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
        root = insert(root, value)
    ordered = inorder(root)
    expected = sorted(set(values))
    print(f"插入顺序 {values}")
    print(f"中序遍历 {ordered}")
    ok = ordered == expected
    print(f"是否升序：{'是' if ok else '否 —— 有问题！'}")
    return 0 if ok else 1


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
SAMPLE_CASES: list[list[int]] = [
    [],
    [1],
    [2, 1],
    [1, 2, 3, 4, 5],
    [5, 4, 3, 2, 1],
    [3, 1, 4, 1, 5, 9, 2, 6],
    [7, 7, 7],
]


def run_tests() -> int:
    failures = 0
    skipped = 0

    def report(label: str, fn) -> None:
        nonlocal failures, skipped
        try:
            fn()
        except NotImplementedError as exc:
            print(f"  [SKIP] {label:<36} {exc}")
            skipped += 1
        except AssertionError as exc:
            print(f"  [FAIL] {label:<36} {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001
            print(f"  [ERROR] {label:<36} {type(exc).__name__}: {exc}")
            failures += 1
        else:
            print(f"  [PASS] {label}")

    def a(c: bool, d: str = "") -> None:
        assert c, d

    print("=" * 66)
    print("排序正确性")
    print("=" * 66)
    for name, algorithm in SORT_ALGORITHMS.items():
        for data in SAMPLE_CASES:
            def check(name=name, algorithm=algorithm, data=data) -> None:
                frames = list(algorithm(data))
                a(frames[-1].values == sorted(data), f"得到 {frames[-1].values}")

            report(f"{name} 排序 {data}", check)

    print()
    print("=" * 66)
    print("不改入参 / 帧的合法性")
    print("=" * 66)

    for name, algorithm in SORT_ALGORITHMS.items():
        def check_immutable(algorithm=algorithm) -> None:
            original = [3, 1, 4, 1, 5]
            snapshot = list(original)
            list(algorithm(original))
            a(original == snapshot, f"变成了 {original}")

        report(f"{name} 没改动传入的列表", check_immutable)

        def check_frames(algorithm=algorithm) -> None:
            data = [5, 3, 8, 1, 9, 2]
            frames = list(algorithm(data))
            n = len(data)
            a(len(frames) >= 1, "一帧都没有")
            a(frames[0].values == data, "首帧不等于原数据")
            a(frames[-1].values == sorted(data), "末帧没排好序")
            a(all(0 <= i < n for f in frames for i in f.highlight), "highlight 下标越界")
            a(all(len(f.values) == n for f in frames), "有帧长度不对")
            a(len({id(f.values) for f in frames}) == len(frames),
              "有帧共享了同一个列表对象（快照没复制）")

        report(f"{name} 帧合法性", check_frames)

    print()
    print("=" * 66)
    print("渲染")
    print("=" * 66)

    def check_render() -> None:
        frames = list(bubble_sort([3, 1, 2]))
        text = render_sort_frame(frames[0], max_value=3)
        a(bool(text.strip()), "渲染结果是空的")
        a("\x1b" not in text, "渲染函数不该输出 ANSI 转义序列")
        a(all(str(v) in text for v in (1, 2, 3)), "数值没出现在渲染结果里")

    report("排序帧渲染", check_render)

    def check_zero() -> None:
        a(bool(render_sort_frame(Frame([0, 0], (), "全零"), max_value=0).strip()),
          "max_value=0 时炸了")

    report("全零数据不崩", check_zero)

    print()
    print("=" * 66)
    print("二叉搜索树")
    print("=" * 66)

    def check_bst() -> None:
        root: Node | None = None
        for value in [5, 3, 8, 1, 4, 7, 9]:
            root = insert(root, value)
        a(inorder(root) == [1, 3, 4, 5, 7, 8, 9], str(inorder(root)))
        rendered = render_tree(root)
        a(bool(rendered.strip()), "渲染为空")
        a("\x1b" not in rendered, "渲染里不该有 ANSI 转义")

        # 关键验收：从左到右读就是升序
        positions = []
        for line in rendered.splitlines():
            for col, char in enumerate(line):
                if char.isdigit():
                    positions.append((col, int(char)))
        by_col = [v for _, v in sorted(set(positions))]
        a(by_col == sorted(by_col), f"从左到右不是升序：{by_col}")

    report("建树 + 中序 + 渲染", check_bst)

    def check_bst_edges() -> None:
        a(render_tree(None) == "  (空树)", "空树的渲染不对")
        root: Node | None = None
        for value in [5, 5, 5]:
            root = insert(root, value)
        a(inorder(root) == [5], f"重复值被插入了多次：{inorder(root)}")
        degenerate: Node | None = None
        for value in range(1, 8):
            degenerate = insert(degenerate, value)
        a(inorder(degenerate) == list(range(1, 8)), "退化成链时出错")
        a(bool(render_tree(degenerate).strip()), "链渲染为空")

    report("空树 / 重复值 / 退化链", check_bst_edges)

    def check_gen() -> None:
        frames = list(bst_insert([5, 3, 8, 3]))
        a(len(frames) >= 1, "没有产出帧")
        a(any("已经存在" in note for _, _, note in frames), "没有跳过重复值")

    report("bst_insert 生成器", check_gen)

    print()
    print("=" * 66)
    print("动画")
    print("=" * 66)

    import io

    def check_animate() -> None:
        buf = io.StringIO()
        animate(iter(["A", "B", "C"]), 0.0, buf, enabled=True)
        a(buf.getvalue().count(CLEAR) == 3, f"清屏次数不对：{buf.getvalue().count(CLEAR)}")

        buf2 = io.StringIO()
        animate(iter(["A", "B", "C"]), 0.0, buf2, enabled=False)
        a("\x1b" not in buf2.getvalue(), "关闭动画时不该有 ANSI 转义")
        a(buf2.getvalue().strip() == "C", f"应该只输出最后一帧：{buf2.getvalue()!r}")

    report("动画开关与降级", check_animate)

    print()
    print("=" * 66)
    print("CLI")
    print("=" * 66)
    report("--size 0 退出码 2", lambda: a(main(["sort", "--size", "0"]) == 2))
    report("--values 非法退出码 2", lambda: a(main(["bst", "--values", "a,b"]) == 2))
    report("--no-animate 排序",
           lambda: a(main(["sort", "--algo", "quick", "--size", "8", "--no-animate"]) == 0))
    report("--no-animate BST",
           lambda: a(main(["bst", "--values", "5,3,8", "--no-animate"]) == 0))

    print()
    print("=" * 66)
    total = len(SORT_ALGORITHMS) * len(SAMPLE_CASES) + len(SORT_ALGORITHMS) * 2 + 8
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
