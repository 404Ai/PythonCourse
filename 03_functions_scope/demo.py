"""
模块 03 · 函数与作用域 —— 可运行示例

在 VS Code 中打开本文件，按 F5 调试运行（或 Ctrl+F5 直接运行）。

建议读法：
    1. 先看 README 对应小节
    2. **先猜这段代码会输出什么**，再往下跑
    3. 猜错的地方就是你的知识盲区

强烈推荐用调试器走一遍 demo_mutable_default()：
    在 box.append(item) 那一行打上断点，按 F5 启动调试，
    在「监视」面板里加入 box，再加入 add_item.__defaults__[0]，
    看它们是不是同一个对象。亲眼看到一次，这个坑就再也不会踩。
"""

from __future__ import annotations

import functools
import inspect
import time


def section(title: str) -> None:
    """打印一个分节标题。"""
    print()
    print("=" * 70)
    print(title)
    print("=" * 70)


def show_call(func, *args, **kwargs) -> None:
    """调用 func 并把结果打到屏幕上；出异常时只打印异常类型和消息。

    这样 demo 里就能放心地演示「这样写会报错」，而不会真的崩掉。
    """
    try:
        result = func(*args, **kwargs)
    except Exception as exc:
        print(f"     {func.__name__}{args} -> {type(exc).__name__}: {exc}")
    else:
        print(f"     {func.__name__}{args} -> {result!r}")


# ======================================================================
# 3.1 参数机制全景
# ======================================================================
def demo_parameter_zoo() -> None:
    section("3.1 参数机制全景：位置 / 关键字 / 默认值 / *args / **kwargs")

    print("  -- 位置参数与关键字参数 --")

    def connect(host, port, timeout=30):
        return f"{host}:{port} timeout={timeout}"

    print(f"     connect('localhost', 8080)            -> {connect('localhost', 8080)}")
    print(f"     connect(host='localhost', port=8080)  -> {connect(host='localhost', port=8080)}")
    print(f"     connect('localhost', port=8080, timeout=60) -> "
          f"{connect('localhost', port=8080, timeout=60)}")
    print("     规则：一旦用了关键字形式，后面的实参也必须用关键字形式。")
    print("     connect(host='localhost', 8080) 是 SyntaxError（编译期就拦住了）。")
    print()

    print("  -- 默认值只在 def 执行时求值一次 --")
    stamp = time.time()

    def with_default(ts=stamp):
        return ts

    print(f"     定义时的 stamp       = {stamp}")
    print(f"     一秒后调用 with_default() = {with_default()}")
    time.sleep(0.01)
    print(f"     再调用一次           = {with_default()}")
    print(f"     两次相同吗 -> {with_default() == with_default()}")
    print("     晚一秒定义的新函数才会拿到新的时间戳：")

    def with_default_2(ts=time.time()):
        return ts

    print(f"     with_default_2()     = {with_default_2()}   <- 变新了，因为重新 def 了一次")
    print()

    print("  -- *args 收集成 tuple，**kwargs 收集成 dict --")

    def collect(*args, **kwargs):
        return f"args={args!r} ({type(args).__name__}), kwargs={kwargs!r} ({type(kwargs).__name__})"

    print(f"     collect(1, 2, x=3)   -> {collect(1, 2, x=3)}")
    print(f"     collect()            -> {collect()}")
    print()

    print("  -- 调用时的 * 和 ** 是解包 --")
    nums = [1, 2, 3]
    config = {"host": "db.local", "port": 5432}
    print(f"     connect(**{config}) -> {connect(**config)}")
    print(f"     print(*{nums}) 等价于 print(1, 2, 3)：", end="")
    print(*nums)
    print()

    print("  -- keyword-only 参数：裸 * 之后只能按关键字传 --")

    def create_user(name, *, is_admin=False, send_mail=True):
        return f"name={name} is_admin={is_admin} send_mail={send_mail}"

    print(f"     create_user('张三', is_admin=True) -> {create_user('张三', is_admin=True)}")
    show_call(create_user, "张三", True)
    print("     ^ 位置传第二个参数直接 TypeError。布尔参数是最该用 keyword-only 的场景：")
    print("       create_user('张三', True, False) 读代码的人根本不知道那两个布尔是什么。")
    print()

    print("  -- positional-only 参数：/ 之前不能按关键字传 --")

    def greet(name, /, greeting="你好"):
        return f"{greeting}, {name}"

    print(f"     greet('张三')          -> {greet('张三')}")
    print(f"     greet('张三', '早上好') -> {greet('张三', '早上好')}")
    show_call(greet, name="张三")
    print("     标准库的 len(obj) 也是 positional-only，所以 len(obj=[]) 会报错。")
    print()

    print("  -- 完整签名：从 / 到 **kwargs 的一条龙 --")

    def everything(a, b, /, c, d=4, *args, e, f=6, **kwargs):
        return (f"a={a} b={b} c={c} d={d} args={args} e={e} f={f} kwargs={kwargs}")

    print(f"     everything(1, 2, 3, 4, 5, 6, e=7, f=8, g=9)")
    print(f"       -> {everything(1, 2, 3, 4, 5, 6, e=7, f=8, g=9)}")
    print(f"     签名: {inspect.signature(everything)}")
    print()

    print("  -- functools.partial：把一部分参数冻住 --")

    def power(base, exp):
        return base ** exp

    square = functools.partial(power, exp=2)
    cube = functools.partial(power, exp=3)
    print(f"     square = partial(power, exp=2)  square(5) -> {square(5)}")
    print(f"     cube   = partial(power, exp=3)  cube(2)   -> {cube(2)}")
    print(f"     type(square) = {type(square).__name__}，但它可以直接当函数调用")
    print(f"     square.func.__name__ = {square.func.__name__}   <- lambda 做不到这一点")
    print(f"     square.keywords = {square.keywords}")


# ======================================================================
# 3.2 可变默认参数陷阱
# ======================================================================
def demo_mutable_default() -> None:
    section("3.2 可变默认参数陷阱：def f(lst=[]) 为什么是灾难")

    print("  -- 灾难现场：默认值是列表 --")

    def add_item(item, box=[]):
        box.append(item)
        return box

    print(f"     add_item('a') -> {add_item('a')}")
    print(f"     add_item('b') -> {add_item('b')}     <- 上一次的 'a' 还在！")
    print(f"     add_item('c') -> {add_item('c')}")
    print()
    print("     证据在这里 —— 默认值存在函数对象里，只有一个：")
    print(f"     add_item.__defaults__ = {add_item.__defaults__!r}")
    print(f"     id(add_item.__defaults__[0]) = {id(add_item.__defaults__[0])}")
    print("     ^ 三次调用里的 box 都是这同一个列表。")
    print()

    print("  -- 同一份代码，传了参数就没事 --")
    fresh = []
    print(f"     add_item('x', []) -> {add_item('x', [])}   每次都新建，互不影响")
    print(f"     用显式传入的 {fresh!r} 也一样")
    print()

    print("  -- 正解：None 当哨兵 --")

    def add_item_ok(item, box=None):
        if box is None:
            box = []          # 每次调用都新建，不再共享
        box.append(item)
        return box

    print(f"     add_item_ok('a') -> {add_item_ok('a')}")
    print(f"     add_item_ok('b') -> {add_item_ok('b')}")
    print(f"     add_item_ok('c') -> {add_item_ok('c')}")
    print(f"     add_item_ok.__defaults__ = {add_item_ok.__defaults__!r}   <- 不可变的 None，安全")
    print()

    print("  -- 同样的坑：默认值写成了函数调用 --")
    print("     def log(msg, ts=time.time()): ...")
    print("     ts 会永远停在「函数被定义的那一刻」，因为默认值只求值一次。")
    print()

    print("  -- 变体：写在类里（模块 04 会细讲）--")

    class Basket:
        def __init__(self, items=[]):        # 所有实例共享同一个列表！
            self.items = items

    b1, b2 = Basket(), Basket()
    b1.items.append("苹果")
    print(f"     b1.items = {b1.items}   b2.items = {b2.items}")
    print(f"     b1.items is b2.items -> {b1.items is b2.items}   <- 是同一个列表")
    print()

    print("  -- 对照：partial 固化的是不可变值，所以安全 --")
    print("     partial(send, retries=3) 里的 3 永远不会变成 4，共享它没有任何风险。")
    print("     一句话规则：只要默认值是可变对象，就写 None 再在函数体里判空新建。")


# ======================================================================
# 3.3 参数传递：call by object reference
# ======================================================================
def demo_argument_passing() -> None:
    section("3.3 参数传递：call by object reference（传参就是一次赋值）")

    print("  -- 改内容 vs 重新绑定 --")

    def mutate(lst):
        lst.append(99)          # 改对象内容

    def rebind(lst):
        lst = [99]              # 重新绑定局部名字

    data = [1, 2]
    mutate(data)
    print(f"     data = [1, 2]; mutate(data)  -> data = {data}     <- 变了")

    data = [1, 2]
    rebind(data)
    print(f"     data = [1, 2]; rebind(data)  -> data = {data}       <- 没变")
    print()

    print("  -- 不可变对象只能「重新绑定」，所以看起来像值传递 --")

    def bump(n):
        n += 1                  # int 不可变，这其实是 n = n + 1
        return n

    n = 10
    bump(n)
    print(f"     n = 10; bump(n) 之后 n = {n}   bump 内部拿到的是新建的 11")
    print()

    print("  -- 所以「可变对象按引用、不可变按值」这个口诀是错的 --")

    def plus_assign_tuple(t):
        t += (3,)               # 元组不可变 -> 新建对象 -> 重新绑定

    tup = (1, 2)
    plus_assign_tuple(tup)
    print(f"     tup = (1, 2); t += (3,) 之后  tup = {tup}")

    def plus_assign_list(lst):
        lst += [3]              # 列表有 __iadd__ -> 就地扩展

    lst = [1, 2]
    plus_assign_list(lst)
    print(f"     lst = [1, 2]; lst += [3] 之后 lst = {lst}")
    print("     决定「调用方看不看得见」的不是对象的可变性，")
    print("     而是函数里做的是『改内容』还是『重新绑定』。")
    print()

    print("  -- 想改又不想影响调用方：进函数先复制 --")

    def normalize(data):
        data = list(data)       # 复制一份，后面随便改
        data.sort()
        return data

    src = [3, 1, 2]
    out = normalize(src)
    print(f"     normalize([3, 1, 2]) -> {out}   原列表 src 还是 {src}")
    print("     标准库也遵守这个约定：list.sort() 就地改并返回 None，")
    print("                            sorted() 返回新列表且不动原列表。")


# ======================================================================
# 3.4 LEGB 与 global / nonlocal
# ======================================================================
_GLOBAL_COUNTER = 0
_GLOBAL_READONLY = "我是模块级变量"


def demo_scope_legb() -> None:
    section("3.4 作用域：LEGB、global、nonlocal")

    print("  LEGB 查找顺序：Local -> Enclosing -> Global -> Builtins")
    print()

    x = "global"

    def outer():
        x = "enclosing"

        def inner():
            x = "local"
            return x

        return inner(), x

    got_inner, got_outer = outer()
    print(f"     inner 里写了 x = 'local'  -> inner 返回 {got_inner!r}")
    print(f"     outer 里写了 x = 'enclosing' -> outer 返回 {got_outer!r}")
    print("     每一层都命中自己的 L，外面的圈根本不去看。")
    print()

    print("  -- 只读的话，会往上找 --")

    def read_global():
        return _GLOBAL_READONLY       # 本地没有 -> E 没有 -> G 命中

    print(f"     read_global() -> {read_global()!r}")
    print()

    print("  -- 但只要函数里有赋值，这个名字就变成局部的了（编译期决定）--")

    def broken():
        print(f"      broken 里 print(G) 之前，G 的值是 ...")
        print(G)                       # 这一行会炸

    G_BAD = 1
    print(f"     模块级 G_BAD = {G_BAD}")
    print("     def broken():")
    print("         print(G_BAD)     <- UnboundLocalError！")
    print("         G_BAD = 2")
    try:
        broken()
    except UnboundLocalError as exc:
        print(f"     实际报错：UnboundLocalError: {exc}")
    except NameError as exc:
        print(f"     实际报错：NameError: {exc}")
    print("     原因：编译 broken 时看到 G_BAD = 2，就认定 G_BAD 是局部变量。")
    print("     Python 没有变量声明语法，赋值语句同时完成了『声明』和『赋值』。")
    print("     ^ 注意这个函数故意没被执行成功，它只是用来演示报错信息的。")
    print()

    print("  -- global：明确声明要改模块级那个 --")

    def bump_global():
        global _GLOBAL_COUNTER
        _GLOBAL_COUNTER += 1
        return _GLOBAL_COUNTER

    print(f"     调用前 _GLOBAL_COUNTER = {_GLOBAL_COUNTER}")
    bump_global()
    bump_global()
    print(f"     调用两次后 _GLOBAL_COUNTER = {_GLOBAL_COUNTER}")
    print("     global 只是声明，不创建变量。而且多数情况下不该用它：")
    print("     函数变得不纯、测试互相污染、并发不安全。")
    print("     更好的是：用返回值、用参数、或者用类把状态装起来。")
    print()

    print("  -- nonlocal：改外层函数的名字 --")

    def make_counter():
        count = 0

        def counter():
            nonlocal count        # 没有这行就是 UnboundLocalError
            count += 1
            return count

        return counter

    c1 = make_counter()
    c2 = make_counter()
    print(f"     c1() 三次 -> {c1()} {c1()} {c1()}")
    print(f"     c2() 一次 -> {c2()}      <- 每个闭包实例有自己独立的状态")
    print()

    print("  -- 只有函数 / 类 / 模块 / 推导式产生作用域，if 和 for 不产生 --")
    for i in range(3):
        pass
    print(f"     for 循环结束后 i = {i}      <- 循环变量泄漏到外面了")
    squares = [k * k for k in range(4)]
    print(f"     推导式 [k * k for k in range(4)] = {squares}")
    try:
        print(k)
    except NameError:
        print("     但推导式结束后 k 是 NameError —— 推导式有自己的作用域")


# ======================================================================
# 3.5 一等函数
# ======================================================================
def demo_first_class() -> None:
    section("3.5 一等函数：函数是对象，可以传参、可以返回")

    def shout(text):
        return text.upper() + "!"

    yell = shout                 # 注意：没有括号，这是绑定名字不是调用
    print(f"     yell = shout         type(shout) = {type(shout).__name__}")
    print(f"     yell is shout        -> {yell is shout}")
    print(f"     shout.__name__       = {shout.__name__!r}")
    print(f"     yell('hi')           = {yell('hi')!r}")
    print()

    print("  -- 函数可以放进容器里 --")

    def add(a, b):
        return a + b

    def sub(a, b):
        return a - b

    ops = {"+": add, "-": sub}
    print(f"     ops['+'](7, 2) = {ops['+'](7, 2)}    ops['-'](7, 2) = {ops['-'](7, 2)}")
    print("     这就是「用字典代替 if/elif 长链」的标准做法。")
    print()

    print("  -- 函数可以有属性（装饰器记状态就靠这个）--")
    add.calls = 0
    add.calls += 1
    print(f"     add.calls = {add.calls}   <- 函数是对象，随便挂属性")
    print()

    print("  -- map / filter 返回的是迭代器，不是列表 --")
    nums = [1, 2, 3, 4]
    print(f"     list(map(str, {nums}))            = {list(map(str, nums))}")
    print(f"     list(map(lambda n: n * 2, {nums})) = {list(map(lambda n: n * 2, nums))}")
    print(f"     list(filter(lambda n: n % 2 == 0, {nums})) = "
          f"{list(filter(lambda n: n % 2 == 0, nums))}")
    print(f"     list(filter(None, [0, 1, '', 'x', None])) = "
          f"{list(filter(None, [0, 1, '', 'x', None]))}   <- None 表示按真值过滤")

    once = map(lambda n: n * n, nums)
    print(f"     第一次 list(once) = {list(once)}")
    print(f"     第二次 list(once) = {list(once)}     <- 迭代器只能用一次")
    print()

    print("  -- sorted(key=) 的 key 是『打分函数』，不是『比较函数』 --")
    words = ["banana", "Apple", "cherry", "fig"]
    print(f"     sorted({words})")
    print(f"       -> {sorted(words)}")
    print(f"     sorted(words, key=str.lower) -> {sorted(words, key=str.lower)}")
    print(f"     sorted(words, key=len)       -> {sorted(words, key=len)}")
    print(f"     sorted(words, key=len, reverse=True) -> {sorted(words, key=len, reverse=True)}")
    print("     key 只对每个元素调用一次（O(n) 次），比 C 的 qsort 比较函数高效得多。")
    print()

    students = [("张三", 85), ("李四", 92), ("王五", 85)]
    print(f"     students = {students}")
    print(f"     先按分数降序、同分按名字升序：")
    print(f"       key=lambda t: (-t[1], t[0])")
    print(f"       -> {sorted(students, key=lambda t: (-t[1], t[0]))}")
    print("     ^ 负号把降序变成升序，因为元组是从左到右比较的。")
    print()

    print("  -- lambda 的边界 --")
    print(f"     (lambda a, b=2: a + b)(1) = {(lambda a, b=2: a + b)(1)}")
    print(f"     lambda 有 __name__ 但没有 __doc__: "
          f"{(lambda x: x).__name__!r}, {(lambda x: x).__doc__!r}")
    print("     不能写语句：lambda x: return x 是 SyntaxError，lambda x: y = x 也是。")
    print("     不能有注解：lambda x: int 不是注解，是语法错误。")
    print("     不能有文档字符串，调试器里名字永远是 <lambda>。")
    print("     结论：短的、一次性的回调用 lambda，其余一律用 def。")


# ======================================================================
# 3.6 闭包
# ======================================================================
def demo_closure() -> None:
    section("3.6 闭包：函数 + 它定义时的环境")

    def make_multiplier(factor):
        def multiply(x):
            return x * factor        # factor 既不是参数也不是局部变量
        return multiply

    double = make_multiplier(2)
    triple = make_multiplier(3)
    print(f"     double = make_multiplier(2)   double(5) = {double(5)}")
    print(f"     triple = make_multiplier(3)   triple(5) = {triple(5)}")
    print("     make_multiplier 早就返回了，factor 却还活着 —— 它住在闭包里。")
    print()

    print("  -- 闭包是看得见的：__closure__ / co_freevars --")
    print(f"     double.__code__.co_freevars      = {double.__code__.co_freevars}")
    print(f"     make_multiplier.__code__.co_cellvars = {make_multiplier.__code__.co_cellvars}")
    print(f"     len(double.__closure__)          = {len(double.__closure__)}")
    print(f"     double.__closure__[0].cell_contents = {double.__closure__[0].cell_contents}")
    print(f"     triple.__closure__[0].cell_contents = {triple.__closure__[0].cell_contents}")
    print("     ^ 同一个 co_freevars 名字，两个函数对象各有各的 cell，互不影响。")
    print()

    print("  -- 延迟绑定陷阱：循环里创建 lambda --")
    funcs = [lambda x: x * i for i in range(4)]
    print(f"     funcs = [lambda x: x * i for i in range(4)]")
    print(f"     [f(10) for f in funcs] = {[f(10) for f in funcs]}")
    print("     ^ 期望 [0, 10, 20, 30]，实际全是 30 —— 四个 lambda 共享同一个 i 的 cell。")
    print("     闭包捕获的是『变量本身』，不是『变量当时的值』；")
    print("     名字在『调用时』才解析，那时循环早已结束，i 停在 3。")
    print()

    print("  -- 修复一：默认参数固化（默认值在定义时求值一次）--")
    funcs_default = [lambda x, i=i: x * i for i in range(4)]
    print(f"     [lambda x, i=i: x * i for i in range(4)]")
    print(f"     [f(10) for f in funcs_default] = {[f(10) for f in funcs_default]}")
    print("     ^ 用的是 3.2 节那个『陷阱』的同一个机制 —— 区别在于 i 是不可变的 int，")
    print("       共享不可变对象永远安全，共享可变对象才是灾难。")
    print()

    print("  -- 修复二：工厂函数（每次调用产生一个新的作用域）--")

    def make_mul(i):
        return lambda x: x * i

    funcs_factory = [make_mul(i) for i in range(4)]
    print(f"     funcs = [make_mul(i) for i in range(4)]")
    print(f"     [f(10) for f in funcs] = {[f(10) for f in funcs_factory]}")
    print()

    print("  -- 修复三：functools.partial --")

    def mul(i, x):
        return x * i

    funcs_partial = [functools.partial(mul, i) for i in range(4)]
    print(f"     [partial(mul, i) for i in range(4)]")
    print(f"     [f(10) for f in funcs_partial] = {[f(10) for f in funcs_partial]}")
    print()

    print("  -- nonlocal 让闭包能『改』外层变量 --")

    def make_counter(start=0, step=1):
        count = start

        def counter():
            nonlocal count
            count += step
            return count

        def reset():
            nonlocal count
            count = start
            return count

        return counter, reset

    counter, reset = make_counter(100, 5)
    print(f"     counter() 两次 -> {counter()} {counter()}")
    print(f"     reset()        -> {reset()}")
    print(f"     counter()      -> {counter()}")
    print("     ^ counter 和 reset 共享同一个 count cell —— 所以 cell 里存的必须是")
    print("       『存储位置』而不是『值的副本』，否则 reset 改了 counter 也看不到。")
    print()

    print("  -- 闭包持有引用：会拖住内存 --")
    print("     只要闭包活着，它捕获的整个对象就活着。")
    print("     回调里捕获了大对象、回调又被注册到全局，是真实项目里内存泄漏的常见来源。")


# ======================================================================
# 3.7 装饰器
# ======================================================================
def demo_decorators() -> None:
    section("3.7 装饰器：接收函数、返回函数")

    print("  @ 只是语法糖：")
    print("     @my_decorator")
    print("     def f(): ...        <=>   f = my_decorator(f)")
    print()

    print("  -- 手写 @timer --")

    def timer(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                elapsed = time.perf_counter() - start
                print(f"       [{func.__name__}] 耗时 {elapsed:.6f}s")

        return wrapper

    @timer
    def slow_sum(n):
        """累加 0..n-1。"""
        return sum(range(n))

    print("     调用 slow_sum(1_000_000)：")
    result = slow_sum(1_000_000)
    print(f"     返回值 = {result}")
    print(f"     slow_sum.__name__ = {slow_sum.__name__!r}   <- 靠 functools.wraps 保住的")
    print(f"     slow_sum.__doc__  = {slow_sum.__doc__!r}")
    print()

    print("  -- functools.wraps 不写会丢什么 --")

    def naive_timer(func):
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        return wrapper

    @naive_timer
    def documented(x: int) -> int:
        """原始文档字符串。"""
        return x

    print(f"     documented.__name__     = {documented.__name__!r}    <- 名字没了")
    print(f"     documented.__doc__      = {documented.__doc__!r}     <- 文档没了")
    print(f"     documented.__qualname__ = {documented.__qualname__!r}")
    print(f"     inspect.signature(documented) = {inspect.signature(documented)}")
    print(f"     hasattr(documented, '__wrapped__') = {hasattr(documented, '__wrapped__')}")
    print()
    print("     加上 @functools.wraps(func) 之后：")
    print(f"     slow_sum.__name__     = {slow_sum.__name__!r}")
    print(f"     inspect.signature(slow_sum) = {inspect.signature(slow_sum)}")
    print(f"     slow_sum.__wrapped__.__name__ = {slow_sum.__wrapped__.__name__!r}"
          f"   <- 可以直接拿到没被包装的原函数")
    print("     ^ 日志、pytest 的测试发现、Flask 路由、IDE 的参数提示，")
    print("       全都依赖 __name__ 和 __wrapped__。所以 wraps 是标配，没有例外。")
    print()

    print("  -- 装饰器在『定义时』就执行了 --")

    def trace(func):
        print(f"     [trace] 正在装饰 {func.__name__}（这一行在定义时打印）")

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            print(f"     [trace] 调用 {func.__name__}（这一行在调用时打印）")
            return func(*args, **kwargs)

        return wrapper

    @trace
    def hello():
        return "hi"

    print("     （上面那行是定义装饰器后立刻打印的，还没调用 hello）")
    print(f"     hello() -> {hello()!r}")
    print()

    print("  -- 带参数的装饰器：三层嵌套 --")

    def retry(times, exceptions=(ValueError,)):
        def decorator(func):                       # 第二层：真正的装饰器
            @functools.wraps(func)
            def wrapper(*args, **kwargs):          # 第三层：包装函数
                last = None
                for attempt in range(1, times + 1):
                    try:
                        return func(*args, **kwargs)
                    except exceptions as exc:
                        last = exc
                        print(f"       第 {attempt} 次失败：{exc}")
                raise last                          # 重试用完还是失败，必须抛出去
            return wrapper
        return decorator

    attempts = {"n": 0}

    @retry(3)
    def flaky():
        attempts["n"] += 1
        if attempts["n"] < 3:
            raise ValueError(f"第 {attempts['n']} 次故意失败")
        return "第三次成功了"

    print(f"     flaky() -> {flaky()!r}")
    print(f"     实际被调用了 {attempts['n']} 次")
    print("     如果不写最后的 raise，重试全失败时会静默返回 None —— 比不重试更糟。")
    print()

    print("  -- 装饰器顺序：从下往上包 --")
    print("     @a")
    print("     @b")
    print("     def f(): ...    <=>   f = a(b(f))")
    print("     @b 先包装 f，@a 再包装 b 的产物；调用时顺序相反。")
    print("     常见讲究：@lru_cache 写在最外层，这样 @timer 计的是『没命中缓存』那次。")


# ======================================================================
# 3.8 functools 四件套
# ======================================================================
def demo_functools() -> None:
    section("3.8 functools：lru_cache / cache / partial / reduce")

    print("  -- lru_cache：自动记忆化 --")
    calls = {"n": 0}

    @functools.lru_cache(maxsize=None)
    def fib(n):
        calls["n"] += 1
        return n if n < 2 else fib(n - 1) + fib(n - 2)

    print(f"     fib(100) = {fib(100)}")
    print(f"     函数体真正被执行的次数 = {calls['n']}   <- 没有缓存的话是天文数字")
    print(f"     fib.cache_info() = {fib.cache_info()}")
    fib.cache_clear()
    print(f"     cache_clear() 之后 fib.cache_info() = {fib.cache_info()}")
    print()

    print("  -- 限制一：参数必须可哈希 --")

    @functools.cache
    def take_list(x):
        return x

    show_call(take_list, [1, 2])
    print("     缓存底层是 dict，键是实参元组，所以 list/dict/set 不能直接传。")
    print()

    print("  -- 限制二：函数必须是纯的 --")
    log_count = {"n": 0}

    @functools.cache
    def log_and_get(n):
        log_count["n"] += 1
        return n * 2

    log_and_get(5)
    log_and_get(5)
    log_and_get(5)
    print(f"     调用 log_and_get(5) 三次，副作用只发生了 {log_count['n']} 次")
    print("     有副作用（打印 / 写文件 / 发请求 / 读全局）的函数被缓存后，")
    print("     副作用只会发生一次。这不是 bug，但通常不是你要的。")
    print()

    print("  -- 限制三：缓存是全局状态，测试之间会互相污染 --")
    print("     跑单测时记得在 setUp 里 cache_clear()，否则上一个用例的结果会被复用。")
    print("     另外 lru_cache 会持有参数的强引用 —— 缓存实例方法时 self 会进键，")
    print("     对象永远回收不掉。要缓存就缓存模块级的纯函数。")
    print()

    print("  -- functools.cache 就是 maxsize=None 的 lru_cache（3.9+）--")
    print("     参数空间有限就 cache，参数空间大（用户 ID 之类）就 lru_cache(maxsize=128)。")
    print()

    print("  -- partial：把参数冻住一部分 --")

    def power(base, exp):
        return base ** exp

    square = functools.partial(power, exp=2)
    print(f"     partial(power, exp=2)(5)  = {square(5)}")
    print(f"     partial(power, exp=2)(5, exp=3) = {square(5, exp=3)}   <- 调用时能覆盖")
    print()

    print("  -- reduce：折叠 --")
    nums = [1, 2, 3, 4]
    print(f"     reduce(lambda a, b: a + b, {nums}) = "
          f"{functools.reduce(lambda a, b: a + b, nums)}")
    print(f"     reduce(lambda a, b: a * b, {nums}) = "
          f"{functools.reduce(lambda a, b: a * b, nums)}")
    print(f"     reduce(lambda a, b: a if a > b else b, [3, 9, 2]) = "
          f"{functools.reduce(lambda a, b: a if a > b else b, [3, 9, 2])}")
    print("     执行过程：reduce(f, [1,2,3,4]) 就是 f(f(f(1,2),3),4)")
    show_call(functools.reduce, lambda a, b: a + b, [])
    print("     ^ 空序列必须给 initial：")
    print(f"     reduce(lambda a, b: a + b, [], 0) = "
          f"{functools.reduce(lambda a, b: a + b, [], 0)}")
    print()
    print("     风格警告：reduce 在 Python 里名声不好，求和用 sum()、求积用 math.prod()、")
    print("     求最值用 max()。只有『折叠操作本身是个变量』时 reduce 才真的赢：")

    OPS = {
        "sum": lambda a, b: a + b,
        "prod": lambda a, b: a * b,
        "max": lambda a, b: a if a > b else b,
    }

    def fold(name, values, initial):
        return functools.reduce(OPS[name], values, initial)

    print(f"     fold('sum', [1,2,3,4], 0)  = {fold('sum', [1, 2, 3, 4], 0)}")
    print(f"     fold('prod', [1,2,3,4], 1) = {fold('prod', [1, 2, 3, 4], 1)}")
    print()

    print("  -- singledispatch：按第一个参数的类型派发 --")

    @functools.singledispatch
    def render(value):
        raise TypeError(f"不支持的类型：{type(value).__name__}")

    @render.register
    def _(value: int):
        return f"整数 {value}"

    @render.register
    def _(value: list):
        return "列表：" + ", ".join(map(str, value))

    print(f"     render(42)    -> {render(42)!r}")
    print(f"     render([1, 2]) -> {render([1, 2])!r}")
    show_call(render, "x")
    print("     比 C++ 重载更明确：运行期派发，而且能给『没注册的类型』一个统一兜底。")


# ======================================================================
# 3.9 函数签名里的类型注解
# ======================================================================
def demo_annotations() -> None:
    section("3.9 函数签名里的类型注解（模块 07 细讲）")

    def greet(name: str, times: int = 1) -> str:
        return f"你好，{name}" * times

    print(f"     greet('张三', 2) = {greet('张三', 2)!r}")
    print(f"     inspect.signature(greet) = {inspect.signature(greet)}")
    print(f"     greet.__annotations__ = {greet.__annotations__}")
    print()

    print("  -- 最重要的一句话：注解不影响运行，解释器一个都不检查 --")
    print(f"     greet(123, 2) = {greet(123, 2)!r}    <- name 声明是 str，传 int 照样跑")
    print(f"     greet('张三', True) = {greet('张三', True)!r}    <- True 当 1 用，也没人管")
    print("     注解只是给人和工具看的元数据，解释器一个都不检查。")
    print("     真正做事的是 mypy / pyright / IDE（模块 09 会讲怎么跑）。")
    print()

    print("  -- 本文件开头写了 from __future__ import annotations --")
    print("     它让所有注解变成字符串，定义时不再求值：")
    print("       - 可以写前向引用（注解里引用还没定义的类）")
    print("       - 省掉求值开销，模块导入更快")
    print("     代价：运行时想拿真实类型对象，得用 typing.get_type_hints()。")
    print()

    print("  -- Python 3.14 起（PEP 649）：注解默认就是惰性求值的 --")
    print("     3.14 之前注解在『定义时』求值，写了个不存在的类型名，import 就炸；")
    print("     现在推迟到『访问 __annotations__ 时』才求值。")
    print("     课程代码统一写 from __future__ import annotations，保证行为一致。")
    print()

    print("  -- 常用注解速查 --")
    samples = [
        "name: str",
        "tags: list[str] | None = None",
        "*args: float",
        "count: int = 0            # keyword-only",
        "**kwargs: object",
        "-> dict[str, int]",
        "func: Callable[[int], str]",
        "items: Iterable[int]",
    ]
    for s in samples:
        print(f"     {s}")


# ======================================================================
def main() -> None:
    demo_parameter_zoo()
    demo_mutable_default()
    demo_argument_passing()
    demo_scope_legb()
    demo_first_class()
    demo_closure()
    demo_decorators()
    demo_functools()
    demo_annotations()
    print()
    print("=" * 70)
    print("全部示例结束。现在打开 exercises.py 开始练习。")
    print("=" * 70)


if __name__ == "__main__":
    main()
