"""
模块 01 · 语言核心 —— 练习

做法：
    1. 把每个函数里的 `raise NotImplementedError` 换成你的实现
    2. 在 VS Code 里打开本文件，按 Ctrl+F5 运行
    3. 看自测结果，全 PASS 之后再打开 solutions.py 对照

    [PASS]  通过
    [FAIL]  断言失败 —— 实现有 bug
    [SKIP]  还没做
    [ERROR] 抛了别的异常

提示：报错的那一行可以下断点，按 F5 用调试器看中间变量，
      这是本课程最推荐的排错方式。
"""

from __future__ import annotations

import sys
from pathlib import Path

# 把课程根目录加进模块搜索路径，这样才能 import 到根目录的 course_kit.py。
# 运行脚本时 sys.path[0] 是脚本所在目录（01_language_core/），
# 所以需要手动把上一级目录插进去。这也是理解 Python 导入机制的好例子。
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— f-string 格式化：生成定宽报表
# ======================================================================
def q1_format_table(rows: list[tuple[str, int, float]]) -> str:
    """把 (名称, 数量, 金额) 列表格式化成定宽文本表格。

    格式要求（每一行，三列直接拼接，列之间不加额外空格）：
        第 1 列：名称，左对齐，宽 8
        第 2 列：数量，右对齐，宽 6
        第 3 列：金额，右对齐，宽 10，保留 2 位小数

    多行之间用 "\\n" 连接（结尾不要有换行符）。

    示例：
        >>> q1_format_table([("apple", 3, 12.5)])
        'apple        3     12.50'

    提示：全部在一个 f-string 里用格式说明符完成，
         不要用 ljust/rjust 手工补空格。
    """
    raise NotImplementedError


# ======================================================================
# q2 —— 用 Decimal 精确求和
# ======================================================================
def q2_money_sum(amounts: list[str]) -> str:
    """把字符串形式的金额精确相加，返回两位小数的字符串。

    >>> q2_money_sum(["0.1", "0.2"])
    '0.30'
    >>> q2_money_sum(["1.005", "2.005"])
    '3.01'

    要求：必须使用 decimal.Decimal，不能用 float。
    提示：Decimal 的构造参数直接传字符串，不要传 float。
    """
    raise NotImplementedError


# ======================================================================
# q3 —— 判断两个对象的关系
# ======================================================================
def q3_object_identity(a, b) -> str:
    """返回 a 和 b 的关系，三选一：

        "identical"  —— a is b（同一个对象）
        "equal"      —— a == b 但不是同一个对象
        "different"  —— a != b

    注意顺序：先判 is，再判 ==。

    >>> x = [1, 2]
    >>> q3_object_identity(x, x)
    'identical'
    >>> q3_object_identity(x, [1, 2])
    'equal'
    >>> q3_object_identity(x, [3])
    'different'
    """
    raise NotImplementedError


# ======================================================================
# q4 —— 整数的二进制视角
# ======================================================================
def q4_describe_int(n: int) -> tuple[int, str, str, str]:
    """返回整数 n 的四元组：

        (二进制位数, 二进制字符串, 八进制字符串, 十六进制字符串)

    后三个都带前缀（0b / 0o / 0x），前缀字母小写。

    >>> q4_describe_int(255)
    (8, '0b11111111', '0o377', '0xff')
    >>> q4_describe_int(0)
    (0, '0b0', '0o0', '0x0')
    """
    raise NotImplementedError


# ======================================================================
# q5 —— 浮点数安全比较
# ======================================================================
def q5_floats_close(a: float, b: float, rel_tol: float = 1e-9) -> bool:
    """判断两个浮点数是否「足够接近」，使用 math.isclose。

    要求：直接把参数透传给 math.isclose，不要自己写 abs(a-b) < eps。

    >>> q5_floats_close(0.1 + 0.2, 0.3)
    True
    >>> q5_floats_close(1.0, 1.1)
    False
    """
    raise NotImplementedError


# ======================================================================
# q6 —— 类型判别（bool 陷阱）
# ======================================================================
def q6_classify(value) -> str:
    """返回 value 的类别名，取值范围：

        "bool" / "int" / "float" / "complex" / "str" / "none" / "other"

    >>> q6_classify(True)
    'bool'
    >>> q6_classify(1)
    'int'
    >>> q6_classify(None)
    'none'

    注意：True 也是 int 的实例，所以判断顺序非常关键。
    提示：可以用 (bool, int, float, complex, str) 这样的元组配合 isinstance。
    """
    raise NotImplementedError


# ======================================================================
# q7 —— 增强赋值的两种行为
# ======================================================================
def q7_augmented() -> tuple[list, bool, list, bool]:
    """按下面的步骤操作，返回 (a, a is b, c, c is d)。

        1. a = [1]
        2. b = a
        3. b += [2]
        4. c = [1]
        5. d = c
        6. d = d + [2]

    期望返回：
        ([1, 2], True, [1], False)

    做完这道题你就明白 += 和 + 的区别了。
    """
    raise NotImplementedError


# ======================================================================
# q8 —— 链式比较 + 异常
# ======================================================================
def q8_grade(score: int) -> str:
    """按分数返回等级：

        90 ~ 100 -> "A"
        80 ~ 89  -> "B"
        70 ~ 79  -> "C"
        60 ~ 69  -> "D"
        0  ~ 59  -> "F"

    如果 score 不在 0~100 范围内，抛 ValueError。

    要求：用 Python 的链式比较（如 90 <= score <= 100），不要写
          `score >= 90 and score <= 100`。

    >>> q8_grade(90)
    'A'
    >>> q8_grade(89)
    'B'
    >>> q8_grade(60)
    'D'
    >>> q8_grade(101)
    Traceback (most recent call last):
    ValueError: 分数必须在 0~100 之间，收到 101
    """
    raise NotImplementedError


# ======================================================================
# q9 —— 健壮的整数解析（EAFP 初体验）
# ======================================================================
def q9_parse_int(text: str, default: int = 0) -> int:
    """把字符串解析成 int，解析失败时返回 default。

    >>> q9_parse_int("42")
    42
    >>> q9_parse_int("  -7  ")
    -7
    >>> q9_parse_int("+13")
    13
    >>> q9_parse_int("3.14")
    0
    >>> q9_parse_int("abc", -1)
    -1
    >>> q9_parse_int("")
    0

    提示：用 try/except ValueError 包住 int(text)。
         Python 的哲学是 EAFP（先做，出问题再处理），
         而不是先用正则校验一遍再转换。
         int() 会自动忽略首尾空白，也会接受正负号。
    """
    raise NotImplementedError


# ======================================================================
# 自测
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

    # 用 float 求和会得到 0.30000000000000004，这就是为什么必须用 Decimal
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
    c = Checker("模块 01 · 语言核心 练习")
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
