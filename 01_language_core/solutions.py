"""
模块 01 · 语言核心 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每个答案下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。
"""

from __future__ import annotations

import math
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— f-string 定宽报表
# ======================================================================
def q1_format_table(rows: list[tuple[str, int, float]]) -> str:
    """一行一个 f-string，三个格式说明符直接拼接。"""
    # 格式说明符拆解：
    #   {name:<8}      -> 左对齐，最小宽度 8
    #   {count:>6}     -> 右对齐，最小宽度 6
    #   {amount:>10.2f}-> 右对齐，宽 10，定点表示保留 2 位小数
    #
    # 注意：宽度是「最小」宽度，内容更长时会自动撑开，不会截断。
    lines = [f"{name:<8}{count:>6}{amount:>10.2f}" for name, count, amount in rows]
    return "\n".join(lines)


# 常见错误写法：
#   f"{name:<8} {count:>6} {amount:>10.2f}"   —— 多加了分隔空格，列宽就不是 8/6/10 了
#   name.ljust(8) + str(count).rjust(6)       —— 能跑通，但啰嗦，且金额还得自己 format
#   f"{name:<8}{count:>6}{amount:>10.2}"      —— .2 是「有效数字」不是「小数位」，
#                                                12.5 会变成 "      1.2e+01"


# ======================================================================
# q2 —— Decimal 精确求和
# ======================================================================
def q2_money_sum(amounts: list[str]) -> str:
    """用 Decimal 累加，最后格式化回两位小数字符串。

    这里用 math.fsum 也可以，但 Decimal 才是财务场景的正解：
    fsum 只是把舍入误差降到最低，Decimal 是彻底没有二进制表示误差。
    """
    total = sum((Decimal(a) for a in amounts), start=Decimal(0))
    return f"{total:.2f}"


# 关键点：
#   1. Decimal("0.1") 是精确的十分之一；Decimal(0.1) 会先把 float 0.1
#      变成它那个不精确的二进制近似值再转，精度问题原封不动带进来。
#      **永远用字符串构造 Decimal**。
#   2. sum() 的 start 参数默认是整数 0，Decimal + int 是合法的，
#      但显式写 Decimal(0) 更明确。
#   3. f"{Decimal('3.005'):.2f}" -> '3.00'，因为 Decimal 默认用
#      ROUND_HALF_EVEN。要传统四舍五入得 quantize(..., rounding=ROUND_HALF_UP)。
#      本题的 1.005 + 2.005 = 3.010 恰好不需要进位，所以没暴露这个细节。


# ======================================================================
# q3 —— 对象身份关系
# ======================================================================
def q3_object_identity(a, b) -> str:
    """先判 is（更严格），再判 ==（更宽松）。"""
    if a is b:
        return "identical"
    if a == b:
        return "equal"
    return "different"


# 为什么要先判 is：
#   is 为真时 == 必然为真（同一个对象当然等于自己，除非 __eq__ 被写成
#   返回 NotImplemented 的奇葩），所以先判更严格的那个能保证语义正确。
#   反过来的话，"identical" 这个分支永远不会被走到。


# ======================================================================
# q4 —— 整数的进制视角
# ======================================================================
def q4_describe_int(n: int) -> tuple[int, str, str, str]:
    """bit_length() 和 bin/oct/hex 都是内置函数。"""
    return n.bit_length(), bin(n), oct(n), hex(n)


# 说明：
#   n.bit_length() 返回表示 n 所需的最少二进制位数。
#   0 的 bit_length() 是 0（不是 1），这是很多人会猜错的边界。
#   负数返回的是绝对值的位数：(-255).bit_length() == 8。
#
#   bin/oct/hex 都带前缀且字母小写，正好符合题目要求。
#   想要不带前缀用格式化：f"{n:b}" f"{n:o}" f"{n:x}"。


# ======================================================================
# q5 —— 浮点数安全比较
# ======================================================================
def q5_floats_close(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    """直接透传给 math.isclose。

    math.isclose 的判定是 |a-b| <= max(rel_tol * max(|a|,|b|), abs_tol)。

    rel_tol（相对容差）适合比较两个「量级相当」的数；
    要和 0 比较必须给 abs_tol，因为相对容差乘 0 永远是 0。
        math.isclose(1e-10, 0)                # False ！
        math.isclose(1e-10, 0, abs_tol=1e-9)  # True
    """
    return math.isclose(a, b, rel_tol=rel_tol)


# 错误写法：
#   abs(a - b) < 1e-9
#   对于 a=1e10, b=1e10+1 这种大数，绝对误差 1 早就超过 1e-9，
#   但这两个数在双精度下根本就是同一个，应该判为相等。
#   rel_tol 就是为解决这个问题设计的。


# ======================================================================
# q6 —— 类型判别
# ======================================================================
def q6_classify(value) -> str:
    """bool 必须排在 int 前面，因为 True 也是 int 的实例。

    这里用元组一次性判断，也可以用 if isinstance(value, bool) 单独判。
    """
    if value is None:
        return "none"
    # 顺序即优先级：bool -> int -> float -> complex -> str
    for cls, name in ((bool, "bool"), (int, "int"), (float, "float"),
                      (complex, "complex"), (str, "str")):
        if isinstance(value, cls):
            return name
    return "other"


# 为什么 None 要单独判：
#   None 不是上面任何类型的实例，isinstance(None, ...) 全为 False，
#   放最后也可以。但用 `is None` 更符合 Python 惯例，也更直观。
#
# 最容易写错的版本：
#   if isinstance(value, int): return "int"     # True 会被误判成 int
#   elif isinstance(value, bool): return "bool" # 永远到不了


# ======================================================================
# q7 —— 增强赋值
# ======================================================================
def q7_augmented() -> tuple[list, bool, list, bool]:
    """+= 在 list 上是就地修改，+ 是新建对象。"""
    a = [1]
    b = a
    b += [2]          # 等价于 b.__iadd__([2])，就地扩展 b 指向的那个列表

    c = [1]
    d = c
    d = d + [2]       # d.__add__([2]) 返回新列表，然后重新绑定名字 d

    return a, a is b, c, c is d


# 底层原因：
#   list 实现了 __iadd__（就地相加），执行后返回 self。
#   所以 `b += x` 对 list 来说不产生新对象，只是原地长大。
#
#   而 tuple、str、int 没有 __iadd__，Python 会退化成
#   `b = b + x`，即「新建对象 → 重新绑定」。
#
#   这就是为什么 「可变对象用 += 要小心别名」：
#       a = [1]; b = a; b += [2]     # a 也变了
#       a = (1,); b = a; b += (2,)   # a 不变


# ======================================================================
# q8 —— 链式比较 + 异常
# ======================================================================
def q8_grade(score: int) -> str:
    """链式比较 + 边界检查。"""
    if not 0 <= score <= 100:
        raise ValueError(f"分数必须在 0~100 之间，收到 {score}")

    # 从高到低依次判断，命中即返回，避免写一长串 and
    if 90 <= score <= 100:
        return "A"
    if 80 <= score <= 89:
        return "B"
    if 70 <= score <= 79:
        return "C"
    if 60 <= score <= 69:
        return "D"
    return "F"


# 为什么链式比较更好：
#   0 <= score <= 100  比  score >= 0 and score <= 100  少写一遍变量名，
#   而且 score 只会被求值一次。当 score 是个函数调用时这点很重要：
#       0 <= compute() <= 100      # compute() 只调用一次
#       compute() >= 0 and compute() <= 100   # 调用两次，且两次结果可能不同
#
# 为什么抛 ValueError 而不是返回 "F"：
#   输入 101 不是「不及格」，而是「非法输入」。把非法输入和合法但差的结果
#   混在一起（都返回 F），会让调用方无法区分，是 bug 的温床。
#   异常类型选择：值不合法用 ValueError，类型不对用 TypeError。


# ======================================================================
# q9 —— 健壮的整数解析（EAFP）
# ======================================================================
def q9_parse_int(text: str, default: int = 0) -> int:
    """EAFP: Easier to Ask Forgiveness than Permission（先做，错了再处理）。

    int() 的行为正好符合题目要求：
        - 自动忽略首尾空白（包括全角空格）
        - 接受 +/-
        - 浮点、字母、空串一律 ValueError
    """
    try:
        return int(text)
    except (TypeError, ValueError):
        return default


# 对比 LBYL（Look Before You Leap，先检查再动手）的写法：
#
#     t = text.strip()
#     if t and (t.lstrip("+-").isdigit()):
#         return int(t)
#     return default
#
# 这种写法有两个问题：
#   1. 要自己处理所有边界（"+", "-", "", " 12 ", "１２３"全角数字……），容易漏
#   2. 检查完到真正转换之间，状态可能已经变了（并发场景）
#
# Python 的官方风格是 EAFP：直接做，用 try/except 处理失败。
# 但注意：**异常处理不是免费的**，在热循环里用异常做流程控制会明显变慢。
# 如果你预期失败率很高（比如 50% 的输入都是垃圾），LBYL 反而更快。
#
# 额外细节：int() 接受 Unicode 数字！
#     int("١٢٣")  ->  123     阿拉伯-印度数字
#     int("１２３") -> 123     全角数字
# 真要做严格校验，得用 str.isascii() + str.isdigit() 自己把关。
# 本题的测试用例里没有这两类，所以 EAFP 版本足够。


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def t_q1() -> None:
    got = q1_format_table([("apple", 3, 12.5), ("banana", 10, 3.25)])
    expected = "apple        3     12.50\nbanana      10      3.25"
    assert got == expected, f"期望:\n{expected!r}\n实际:\n{got!r}"

    assert q1_format_table([]) == "", "空列表应该返回空字符串"
    assert q1_format_table([("x", 0, 0.0)]) == "x            0      0.00"


def t_q2() -> None:
    assert q2_money_sum(["0.1", "0.2"]) == "0.30", q2_money_sum(["0.1", "0.2"])
    assert q2_money_sum(["1.005", "2.005"]) == "3.01", q2_money_sum(["1.005", "2.005"])
    assert q2_money_sum([]) == "0.00"

    naive = sum(float(x) for x in ["0.1", "0.2"])
    assert naive != 0.3, "这一条用来证明 float 版本确实是错的"


def t_q3() -> None:
    x = [1, 2]
    assert q3_object_identity(x, x) == "identical"
    assert q3_object_identity(x, [1, 2]) == "equal"
    assert q3_object_identity(x, [3]) == "different"
    assert q3_object_identity(1, True) == "equal", "1 == True 在 Python 里成立"


def t_q4() -> None:
    assert q4_describe_int(255) == (8, "0b11111111", "0o377", "0xff")
    assert q4_describe_int(0) == (0, "0b0", "0o0", "0x0")
    assert q4_describe_int(1) == (1, "0b1", "0o1", "0x1")
    assert q4_describe_int(2 ** 64)[0] == 65


def t_q5() -> None:
    assert q5_floats_close(0.1 + 0.2, 0.3) is True
    assert q5_floats_close(1.0, 1.1) is False
    assert q5_floats_close(100.0, 101.0, rel_tol=0.02) is True
    assert (0.1 + 0.2 == 0.3) is False, "这一条提醒你 == 对 float 不可靠"


def t_q6() -> None:
    assert q6_classify(True) == "bool"
    assert q6_classify(False) == "bool"
    assert q6_classify(1) == "int"
    assert q6_classify(1.5) == "float"
    assert q6_classify(1 + 2j) == "complex"
    assert q6_classify("1") == "str"
    assert q6_classify(None) == "none"
    assert q6_classify([1]) == "other"


def t_q7() -> None:
    a, a_is_b, c, c_is_d = q7_augmented()
    assert a == [1, 2], f"a 应该是 [1, 2]，实际 {a}"
    assert a_is_b is True, "b += [2] 是就地修改，b 和 a 还是同一个对象"
    assert c == [1], f"c 不应该变，实际 {c}"
    assert c_is_d is False, "d = d + [2] 让 d 重新绑定了新对象"


def t_q8() -> None:
    assert q8_grade(100) == "A"
    assert q8_grade(90) == "A"
    assert q8_grade(89) == "B"
    assert q8_grade(80) == "B"
    assert q8_grade(79) == "C"
    assert q8_grade(70) == "C"
    assert q8_grade(69) == "D"
    assert q8_grade(60) == "D"
    assert q8_grade(59) == "F"
    assert q8_grade(0) == "F"

    for bad in (-1, 101, 1000):
        try:
            q8_grade(bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"q8_grade({bad}) 应该抛 ValueError")


def t_q9() -> None:
    assert q9_parse_int("42") == 42
    assert q9_parse_int("  -7  ") == -7
    assert q9_parse_int("+13") == 13
    assert q9_parse_int("0") == 0
    assert q9_parse_int("3.14") == 0
    assert q9_parse_int("abc", -1) == -1
    assert q9_parse_int("", 99) == 99
    assert q9_parse_int("12abc", 5) == 5


def main() -> None:
    c = Checker("模块 01 · 语言核心 参考答案")
    c.add("q1  f-string 定宽报表", t_q1)
    c.add("q2  Decimal 精确求和", t_q2)
    c.add("q3  对象身份关系判定", t_q3)
    c.add("q4  整数的进制视角", t_q4)
    c.add("q5  浮点数安全比较", t_q5)
    c.add("q6  类型判别（bool 陷阱）", t_q6)
    c.add("q7  增强赋值的行为", t_q7)
    c.add("q8  链式比较 + ValueError", t_q8)
    c.add("q9  健壮的整数解析", t_q9)
    c.run()


if __name__ == "__main__":
    main()
