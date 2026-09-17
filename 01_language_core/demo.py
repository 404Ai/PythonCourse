"""
模块 01 · 语言核心 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. 猜一下这段代码会输出什么
    3. 再跑，看是否和你想的一样

强烈推荐用调试器走一遍 demo_binding()：
    在 b = a 那一行左侧点一下打上断点，按 F5 启动调试，
    在「监视」面板里加入 id(a) 和 id(b)，看它们是否相同。
"""

from __future__ import annotations


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


# ======================================================================
# 1.1 执行模型
# ======================================================================
def demo_execution_model() -> None:
    section("1.1 执行模型：源码 -> 字节码 -> 虚拟机")

    import dis
    import sys

    print(f"  解释器实现: {sys.implementation.name}")
    print(f"  版本      : {sys.version.split()[0]}")
    print(f"  缓存前缀  : {sys.pycache_prefix or '(默认，即源码旁边的 __pycache__/)'}")
    print()

    def add(a, b):
        return a + b

    print("  函数 add(a, b) -> a + b 编译后的字节码：")
    print()
    dis.dis(add)

    print(f"  add.__code__.co_varnames = {add.__code__.co_varnames}")
    print(f"  add.__code__.co_consts   = {add.__code__.co_consts}")
    print()
    print("  C 里 a + b 是一条机器指令；Python 里得走好几条字节码，每条都要过一遍")
    print("  解释循环。这就是纯 Python 计算慢的根源，也是 NumPy 存在的理由。")


# ======================================================================
# 1.2 名字绑定
# ======================================================================
def demo_binding() -> None:
    section("1.2 变量不是盒子：名字绑定（name binding）")

    print("  -- 两个名字指向同一个对象 --")
    a = [1, 2, 3]
    b = a
    print(f"     a = {a}    id(a) = {id(a)}")
    print(f"     b = a 之后  b = {b}    id(b) = {id(b)}")
    print(f"     a is b -> {a is b}")
    b.append(4)
    print(f"     b.append(4) 之后  a = {a}    b = {b}")
    print("     ^ a 也变了！a 和 b 只是同一个列表的两个名字。")
    print()

    print("  -- 切片产生新对象 --")
    c = a[:]
    c.append(5)
    print(f"     c = a[:] 之后  a = {a}    id(a) = {id(a)}")
    print(f"                    c = {c}    id(c) = {id(c)}")
    print(f"     a is c -> {a is c}")
    print()

    print("  -- 不可变对象看起来『像 C』，其实是重新绑定 --")
    x = 10
    y = x
    print(f"     x = 10; y = x  ->  id(x) = {id(x)}    id(y) = {id(y)}")
    y += 1
    print(f"     y += 1 之后     x = {x} id(x) = {id(x)}")
    print(f"                     y = {y} id(y) = {id(y)}")
    print("     ^ int 不可变，y += 1 实际是新建对象 11 并把 y 绑过去，x 不受影响。")
    print()

    print("  -- 函数参数：改内容会影响调用方，重新绑定不会 --")

    def mutate(lst):
        lst.append("新元素")     # 修改对象内容

    def rebind(lst):
        lst = ["完全不同的列表"]  # 只是把局部名字重新绑定

    data = [1, 2]
    mutate(data)
    print(f"     传入 {[1, 2]} 调用 mutate() 后  data = {data}   <- 被改了")

    data = [1, 2]
    rebind(data)
    print(f"     传入 {[1, 2]} 调用 rebind() 后  data = {data}   <- 没变")


# ======================================================================
# 1.3 对象三要素与 is / ==
# ======================================================================
def demo_identity() -> None:
    section("1.3 对象三要素 id / type / value，以及 is 与 ==")

    print("  id()   身份，CPython 里就是内存地址")
    print("  type() 类型")
    print("  ==     比较值（调用 __eq__）")
    print()

    print("  -- 小整数缓存：CPython 预先建好 -5 ~ 256 的 int 并永久复用 --")
    for n in (256, 257):
        m = int(str(n))          # 故意绕开编译期常量合并，强制运行时构造
        print(f"     int(str({n})) : {n} is m -> {str(n is m):<5} {n} == m -> {n == m}")
    print()

    print("  -- 字符串驻留（interning）--")
    s1 = "hello"
    s2 = "hel" + "lo"                  # 编译期就能算出来，合并成同一个常量
    parts = ["hel", "lo"]
    s3 = "".join(parts)                # 运行时构造，不在驻留表里
    print(f"     s1 is s2 -> {s1 is s2}    （编译期常量折叠）")
    print(f"     s1 is s3 -> {s1 is s3}    （运行时 join 出来的是新对象）")
    print(f"     s1 == s3 -> {s1 == s3}")
    print()

    print("  -- 空容器：字面量每次都新建，但不可变的空对象有单例 --")
    # 注意：不能直接写 `() is ()`，Python 会对这种「is 接字面量」的写法
    # 抛 SyntaxWarning。所以这里用运行时构造的对象来比较。
    tup_a, tup_b = tuple(), tuple()
    str_a, str_b = "abc"[:0], "hello"[:0]
    print(f"     [] is []             -> {[] is []}     每次字面量都创建新 list")
    print(f"     tuple() is tuple()   -> {tup_a is tup_b}     空元组是单例（不可变，建两个没意义）")
    print(f"     'abc'[:0] is 'x'[:0] -> {str_a is str_b}     空字符串也是单例")
    print()

    print("  实践结论：")
    print("     is    只用于 None / True / False")
    print("     ==    用于其余一切值比较")


# ======================================================================
# 1.4 类型系统
# ======================================================================
def demo_types() -> None:
    section("1.4 类型系统：动态 + 强类型 + 鸭子类型")

    print("  -- 动态：类型属于对象，不属于名字 --")
    x = 42
    print(f"     x = 42         type(x) = {type(x).__name__}")
    x = "现在是字符串"
    print(f"     x = '...'      type(x) = {type(x).__name__}   同一个名字换了对象")
    print()

    print("  -- 强类型：不会偷偷替你转换 --")
    try:
        "3" + 5
    except TypeError as exc:
        print(f"     '3' + 5  ->  TypeError: {exc}")
    print(f"     '3' * 5  ->  {'3' * 5}   （str 对 * 有定义，表示重复）")
    print(f"     '3' + str(5) -> {'3' + str(5)}   显式转换才是正解")
    print()

    print("  -- 鸭子类型：关心能做什么，不关心是什么 --")
    for obj in ([3, 1, 2], (3, 1, 2), "312", {1, 2, 3}, range(3)):
        print(f"     {str(obj):<14} len={len(obj)}  sorted={sorted(obj)}")
    print("     这些对象没有共同基类，但都实现了 __len__ 和 __iter__，")
    print("     所以 len() 和 sorted() 都能用。这就是『协议』。")
    print()

    print("  -- isinstance 看继承链，type() 不看 --")
    print(f"     type(True) is int         -> {type(True) is int}")
    print(f"     isinstance(True, int)     -> {isinstance(True, int)}   (bool 是 int 子类)")

    def classify(v):
        if isinstance(v, bool):      # 必须最先判 bool！
            return "bool"
        if isinstance(v, int):
            return "int"
        return "other"

    print(f"     classify(True) -> {classify(True)!r}    classify(1) -> {classify(1)!r}")
    print("     ^ 顺序反了就会把 True 归成 int，这是真实项目里的常见 bug。")


# ======================================================================
# 1.5 数值
# ======================================================================
def demo_numeric() -> None:
    section("1.5 数值：int 任意精度与 float 的坑")

    print("  -- int 是任意精度，永不溢出 --")
    big = 2 ** 100
    print(f"     2 ** 100            = {big}")
    print(f"     bit_length()        = {big.bit_length()}")
    print(f"     2 ** 100 * 2 ** 100 = {2 ** 100 * 2 ** 100}")
    print()

    print("  -- float 是 IEEE-754 双精度，只有约 15~17 位有效数字 --")
    print(f"     0.1 + 0.2           = {0.1 + 0.2}")
    print(f"     0.1 + 0.2 == 0.3    -> {0.1 + 0.2 == 0.3}")
    print(f"     1e16 + 1 == 1e16    -> {1e16 + 1 == 1e16}   （精度不够，1 被吃掉了）")
    print()

    import math

    print(f"     math.isclose(0.1+0.2, 0.3) -> {math.isclose(0.1 + 0.2, 0.3)}   <- 正确做法")
    print()

    print("  -- 要精确就用 Decimal / Fraction --")
    from decimal import Decimal
    from fractions import Fraction

    print(f"     Decimal('0.1') + Decimal('0.2') = {Decimal('0.1') + Decimal('0.2')}")
    print(f"     Fraction(1, 3) + Fraction(1, 6) = {Fraction(1, 3) + Fraction(1, 6)}")
    print()

    print("  -- 除法与取整 --")
    print(f"     7 / 2   = {7 / 2}     真除法，永远是 float")
    print(f"     7 // 2  = {7 // 2}      向下取整")
    print(f"     -7 // 2 = {-7 // 2}     ^ 是 -4 不是 -3！Python 的 // 是 floor")
    print(f"     -7 % 2  = {-7 % 2}      模的符号跟除数走")
    print(f"     divmod(7, 2) = {divmod(7, 2)}")
    print()

    print("  -- round 是银行家舍入，不是四舍五入 --")
    print(f"     round(2.5) = {round(2.5)}      <- 不是 3")
    print(f"     round(3.5) = {round(3.5)}")
    print(f"     int(3.9)   = {int(3.9)}     <- int() 是向零截断，不是取整")
    print(f"     int(-3.9)  = {int(-3.9)}")
    print()

    print("  -- bool 是 int 的子类 --")
    print(f"     True + True = {True + True}")
    print(f"     sum([True, False, True]) = {sum([True, False, True])}   （统计通过数就靠这个）")


# ======================================================================
# 1.6 字符串与格式化
# ======================================================================
def demo_strings() -> None:
    section("1.6 字符串与格式化")

    print("  -- f-string 常用格式 --")
    name, score = "张三", 0.8765
    print(f"     f'{{score:.2%}}'      -> {score:.2%}")
    print(f"     f'{{1234567:,}}'      -> {1234567:,}")
    print(f"     f'{{1234567:_}}'      -> {1234567:_}")
    print(f"     f'{{255:#x}}'         -> {255:#x}")
    print(f"     f'{{255:08b}}'        -> {255:08b}")
    print(f"     f'{{3.14159:.2f}}'    -> {3.14159:.2f}")
    print(f"     f'{{3.14159:+.3e}}'   -> {3.14159:+.3e}")
    print(f"     f'{{42:>10}}|'        -> {42:>10}|")
    print(f"     f'{{42:<10}}|'        -> {42:<10}|")
    print(f"     f'{{42:^10}}|'        -> {42:^10}|")
    print(f"     f'{{42:*^9}}'         -> {42:*^9}")
    x = 42
    print(f"     f'{{x = }}'           -> {x = }     <- 3.8+ 调试神器")
    print()

    print("  -- 中文字符宽度陷阱 --")
    print(f"     |{'苹果':<8}|{'banana':<8}|")
    print(f"     |{'香蕉':<8}|{'cherry':<8}|")
    print("     ^ 字符数都是 8，但终端里中文占 2 列，所以看起来是歪的。")
    print("       真实项目做表格要用 wcwidth 库算显示宽度。")
    print()

    print("  -- 不可变 + join --")
    s = "Python"
    print(f"     s.upper() = {s.upper()!r}，但 s 还是 {s!r}")
    print(f"     s[::-1] = {s[::-1]}     s[1:4] = {s[1:4]}     s[::2] = {s[::2]}")
    print(f"     ''.join(['a','b','c']) -> {'abc'}")
    print()

    print("  -- strip 的参数是『字符集合』不是子串 --")
    print(f"     'www.example.com'.strip('wcom.') -> {'www.example.com'.strip('wcom.')!r}")
    print(f"     'www.example.com'.removeprefix('www.') -> {'www.example.com'.removeprefix('www.')!r}")
    print()

    print("  -- 大小写无关比较要用 casefold --")
    print(f"     'Straße'.lower()     -> {'Straße'.lower()!r}")
    print(f"     'Straße'.casefold()  -> {'Straße'.casefold()!r}   （ß 被展开成 ss，才是正确的折叠）")
    print(f"     'Straße'.casefold() == 'STRASSE'.casefold() -> "
          f"{'Straße'.casefold() == 'STRASSE'.casefold()}")


# ======================================================================
# 1.7 真值、None、条件表达式
# ======================================================================
def demo_truthiness() -> None:
    section("1.7 真值、None 与条件表达式")

    from decimal import Decimal

    print("  -- 假值只有这些 --")
    falsy = [False, None, 0, 0.0, 0j, Decimal(0), "", [], (), {}, set(), range(0)]
    for v in falsy:
        print(f"     bool({v!r:<12}) = {bool(v)}")
    print()

    print("  -- 反直觉的真值 --")
    for v in ("0", "False", " ", [0], (None,), {0}):
        print(f"     bool({v!r:<10}) = {bool(v)}")
    print("     ^ 非空容器和非空字符串永远是真，不管内容是什么。")
    print()

    print("  -- 判空写法 --")
    items = []
    print(f"     推荐: if not items:      -> {not items}")
    print(f"     判 None 必须用 is: value is None")
    val = None
    print(f"     val is None -> {val is None}")
    print()

    print("  -- 条件表达式 --")
    for n in (3, 4):
        print(f"     {n} 是{'偶数' if n % 2 == 0 else '奇数'}")
    print()

    print("  -- 链式比较：Python 专门修掉了 C 的这个坑 --")

    call_count = 0

    def f():
        nonlocal call_count
        call_count += 1
        return 5

    print(f"     0 < f() < 10 -> {0 < f() < 10}")
    print(f"     f() 只被调用了 {call_count} 次（C 里会调用两次，且结果错误）")
    print()

    print("  -- 海象运算符 :=  --")
    data = [1, 2, 3]
    if (n := len(data)) > 2:
        print(f"     if (n := len(data)) > 2:  -> n = {n}，只算了一次 len")


# ======================================================================
# 1.8 增强赋值陷阱
# ======================================================================
def demo_augmented() -> None:
    section("1.8 增强赋值的陷阱：+= 是就地改还是重新绑定？")

    print("  -- list 的 += 是就地修改，等价于 extend --")
    a = [1]
    b = a
    b += [2]
    print(f"     b += [2] 之后   a = {a}   a is b -> {a is b}")
    print()

    print("  -- list 的 + 是新建对象 --")
    c = [1]
    d = c
    d = d + [2]
    print(f"     d = d + [2] 之后  c = {c}   c is d -> {c is d}")
    print()

    print("  -- 面试经典：元组里的列表 --")
    t = ([1], "固定")
    print(f"     初始 t = {t}")
    try:
        t[0] += [2]
    except TypeError as exc:
        print(f"     t[0] += [2]  抛出了 TypeError: {exc}")
    print(f"     但 t 已经变成 {t}")
    print()
    print("     为什么？拆开看 t[0] += [2] 其实是两步：")
    print("         1. temp = t[0].__iadd__([2])   -> 列表就地扩展，成功")
    print("         2. t[0] = temp                 -> 元组不支持赋值，TypeError")
    print("     第 1 步已经生效了，错误发生在第 2 步。所以是『报错了，但数据改了』。")


# ======================================================================
def main() -> None:
    demo_execution_model()
    demo_binding()
    demo_identity()
    demo_types()
    demo_numeric()
    demo_strings()
    demo_truthiness()
    demo_augmented()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
