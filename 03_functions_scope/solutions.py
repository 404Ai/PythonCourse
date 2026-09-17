"""
模块 03 · 函数与作用域 —— 参考答案

**先自己做完 exercises.py 再看这个文件。**

每个答案下面都写了「为什么这么写」和「常见错误写法错在哪」。
答案不是唯一的，如果你的实现通过了全部断言而且更清晰，那就是更好的答案。
"""

from __future__ import annotations

import functools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from course_kit import Checker


# ======================================================================
# q1 —— 修复可变默认参数陷阱
# ======================================================================
def q1_add_tag(tag: str, tags: list[str] | None = None) -> list[str]:
    """用 None 当哨兵，在函数体里新建列表。"""
    if tags is None:
        tags = []                    # 每次调用都新建，不跨调用共享
    return [*tags, tag]              # 解包成新列表，不碰原来的 tags


# 为什么这么写：
#   1. `tags=None` 的默认值是**不可变**的 None，所有调用共享它完全安全。
#      真正会被共享的可变对象，在函数体里每次调用时现造一个。
#   2. `[*tags, tag]` 一次性构造新列表，等价于 new = list(tags); new.append(tag)。
#      也可以写 tags + [tag]，效果一样。
#   3. 题目要求「不能修改传进来的 tags」，所以不能用 tags.append(tag) 再返回 tags。
#
# 常见错误写法一：直接写默认值 []
#     def q1_add_tag(tag, tags=[]):
#         tags.append(tag)
#         return tags
#   错在哪：默认值在 def 执行时求值**一次**，那个列表被塞进 q1_add_tag.__defaults__，
#   之后每次不传 tags 都拿到同一个列表，于是 q1_add_tag("a") 之后
#   q1_add_tag("b") 会返回 ['a', 'b']。调试时求值 q1_add_tag.__defaults__ 能直接看到它。
#
# 常见错误写法二：在函数里判空用 if not tags
#     if not tags:
#         tags = []
#   错在哪：调用方传了一个空列表 [] 时，`not []` 是 True，会被换成另一个新列表，
#   「返回值必须是新列表」这条仍然满足，但如果调用方期望「我传进去的那个空列表会被填上」，
#   语义就变了。判 None 一定要用 `is None`。
#
# 常见错误写法三：在函数体里 copy，但返回值还是原对象
#     tags = tags or []
#     return tags + [tag]
#   这个其实是对的，但 `tags or []` 和 if not tags 有同样的语义问题。
#   而且调用方传 None 时能工作、传别的假值（比如自定义对象）时会出错。
#   判断「有没有传」永远用 is None，不要用真值判断。
#
# 顺带一提：这个陷阱还有个「高级版」——
#     def f(x, seen=set()): ...          # 跨调用累积的缓存，很多人以为是「免费的缓存」
#   想真的做缓存就用 functools.lru_cache（见 q7），它至少是显式的、可清理的。


# ======================================================================
# q2 —— positional-only 与 keyword-only
# ======================================================================
def q2_make_url(
    host: str,
    path: str,
    /,
    *,
    scheme: str = "https",
    port: int | None = None,
) -> str:
    """按规则拼 URL，重点是签名本身。"""
    # 每个 scheme 的默认端口：等于默认端口就不显示，让 URL 干净一点
    default_ports = {"http": 80, "https": 443}

    if not path.startswith("/"):
        path = "/" + path            # 补上斜杠，函数内部随便改（path 是局部名字）

    if port is None or port == default_ports.get(scheme):
        return f"{scheme}://{host}{path}"
    return f"{scheme}://{host}:{port}{path}"


# 为什么签名要写成 (host, path, /, *, scheme="https", port=None)：
#
#   1. `/` 让 host / path 变成 positional-only。
#      这样别人写不出 q2_make_url(host="...", path="...")，
#      将来你想把参数名改成 hostname / url_path 就不会破坏任何调用方。
#      标准库的 len(obj) 之所以不能写成 len(obj=[])，就是这个原因。
#
#   2. `*` 让 scheme / port 变成 keyword-only。
#      scheme="http" 和 port=8080 都是「有含义的配置值」，
#      如果允许按位置传，q2_make_url("h", "/p", "http", 8080) 这种调用
#      读代码的人必须去翻定义才知道那两个值是什么。
#      布尔参数更是重灾区：create_user("张三", True, False) 完全没法读。
#
#   3. 组合起来，调用方能传的东西是：
#          q2_make_url("example.com", "/a")                   全部用默认值
#          q2_make_url("example.com", "/a", scheme="http")    只改一个
#      而 q2_make_url("example.com", "/a", "http") 会 TypeError，
#      这正是我们要的：参数含义永远写在调用点上。
#
# 常见错误写法一：写成 def q2_make_url(host, path, scheme="https", port=None)
#   错在哪：能跑，但 scheme/port 可以被位置传，上面说的可读性优势全没了。
#
# 常见错误写法二：只写了 * 没写 /
#   在很多标准库风格里 positional-only 也是要加的：
#   可以按关键字传的参数，就多了一种「参数名也是 API」的约束，
#   改名就变成破坏性变更。
#
# 常见错误写法三：在函数里用 if not port 判断
#   错在哪：port=0 是合法端口（虽然不常用），而 `not 0` 是 True，
#   会被误判成「没传端口」。判断 None 永远用 `is None`。
#
# 常见错误写法四：把 default_ports 字典写在函数体里
#   每次调用都要重建一个字典。虽然 CPython 对常量字典有优化，
#   但写成模块级常量更清楚，也更好改。


# ======================================================================
# q3 —— *args 配合 key 函数
# ======================================================================
def q3_top_scorer(key, *items, default=None):
    """直接委托给内置 max，把「空输入」这一个边界处理掉。"""
    if not items:
        return default
    return max(items, key=key)


# 为什么这么写：
#   1. `*items` 把任意多个位置实参收成一个 tuple，所以 len(items) / 切片 /
#      传给 max 全都直接可用，不需要自己写 for 循环。
#   2. `max(iterable, key=...)` 的语义正好是题目要的：
#      - key 对每个元素**各调用一次**（O(n) 次，不是 O(n log n) 次）
#      - 分数相同时返回最先出现的那个（CPython 的 max 用严格大于号推进）
#      - 元素本身是 tuple 时比较的是元素，不受 key 返回值影响
#   3. 空 tuple 不能直接丢给 max：max([]) 会 ValueError。
#      所以空的时候必须提前返回 default。
#
# 常见错误写法一：不处理空输入
#     return max(items, key=key)
#   错在哪：q3_top_scorer(len) 会抛 ValueError: max() arg is an empty sequence。
#   题目明确要求返回 default。这类「边界输入」是练习里最常被忽略的地方。
#
# 常见错误写法二：自己写循环
#     best = default
#     for item in items:
#         if best is default or key(item) > key(best):
#             best = item
#     return best
#   错在哪：累赘，而且有个隐蔽 bug —— key 被调用了 2n 次而不是 n 次。
#   如果 key 是个有代价的函数（比如访问数据库、算哈希），性能差一倍。
#   内置的 max 保证每个元素只算一次 key。
#
# 常见错误写法三：用 sorted 再取第一个
#     return sorted(items, key=key)[-1] if items else default
#   错在哪：没必要地做了 O(n log n) 的完整排序，max 是 O(n)。
#   而且 sorted 是稳定的，同分时会保留原顺序 —— 所以「最后一个同分元素」
#   和 max 的「第一个同分元素」结果不一样，q3 的 tie 用例会挂。
#
# 常见错误写法四：default 写成可变对象
#     def q3_top_scorer(key, *items, default={}):
#   错在哪：回到 3.2 节的陷阱。虽然这里 default 只是被返回、不会被修改，
#   但一旦将来有人加了「往 default 里塞东西」的逻辑，就立刻变成跨调用污染。
#   习惯性地用 None 当默认值，比每次去分析「这个可变默认值安不安全」要省心。
#
# 关于 max 的 key 和「比较函数」的区别（3.5 节）：
#   C 的 qsort 收的是一个 比较两个元素 的函数，会被调用 O(n log n) 次。
#   Python 的 key 收的是一个 给单个元素打分 的函数，只调用 O(n) 次。
#   后者是 William Schwartz 在 Perl 里提出的「Schwartzian transform」思想，
#   现在已经是脚本语言的共识（sort_by / sort key）。
#   真需要「只有 cmp 思维」的算法时，用 functools.cmp_to_key 转换，但新代码别这么写。


# ======================================================================
# q4 —— 手写装饰器：调用计数
# ======================================================================
def q4_count_calls(func):
    """三层结构：收函数 -> 定义 wrapper -> 返回 wrapper。"""
    calls = 0                        # 住在外层作用域，被 wrapper 的闭包捕获

    @functools.wraps(func)           # 少写这一行，__name__ / __doc__ / 签名全丢
    def wrapper(*args, **kwargs):
        nonlocal calls               # 不加 nonlocal 就是 UnboundLocalError
        calls += 1
        wrapper.calls = calls        # 顺便挂到函数对象上，调用方能读到
        return func(*args, **kwargs)  # 必须 return，否则返回值变成 None

    wrapper.calls = 0                # 初始值，这样调用前读 add.calls 也是 0
    return wrapper


# 为什么这么写：
#   1. `*args, **kwargs` 让 wrapper 能透传任意签名。少了它们，
#      被装饰的函数一旦有参数就会 TypeError。
#   2. `return func(*args, **kwargs)` 是装饰器最常见的 bug 来源 ——
#      忘了 return，被装饰函数就永远返回 None，而且**不报错**。
#   3. `nonlocal calls` 是必须的：wrapper 里有 `calls += 1`，
#      没有 nonlocal 的话 Python 会认为 calls 是 wrapper 的局部变量，
#      于是 UnboundLocalError（详见 3.4 / 3.6 节）。
#   4. 计数器放在**外层函数**的局部作用域，而不是模块级变量：
#      每次调用 q4_count_calls 都会创建一个新的 calls，
#      所以不同的被装饰函数各有各的计数器，不会互相干扰。
#      写成模块级的 `_calls = 0` 就会让所有函数共用一个计数器。
#   5. `wrapper.calls = 0` 放在 return 之前，是为了让「还没调用过」时
#      add.calls 也是 0 而不是 AttributeError。函数是对象，可以随便挂属性。
#
# 另一种等价实现（不用 nonlocal，直接用函数属性）：
#     @functools.wraps(func)
#     def wrapper(*args, **kwargs):
#         wrapper.calls += 1
#         return func(*args, **kwargs)
#     wrapper.calls = 0
#     return wrapper
#   这也对，而且更短。缺点是 wrapper 内部对 wrapper 这个名字有依赖
#   （如果之后有人把返回值赋给别的名字，语义会有点绕）。
#   两种写法都见过，选一种你读起来顺的。
#
# 常见错误写法一：忘了 functools.wraps
#     def wrapper(*args, **kwargs): ...
#   错在哪：add.__name__ 变成 'wrapper'，add.__doc__ 变成 None，
#   inspect.signature(add) 变成 (*args, **kwargs)，IDE 不再提示参数，
#   没有 __wrapped__ 所以拿不到原函数。日志里全是 wrapper，等于没记。
#   生产代码里 wraps 是标配，没有例外。
#
# 常见错误写法二：wrapper 写成固定签名
#     def wrapper(a, b): return func(a, b)
#   错在哪：被装饰的函数必须是 (a, b) 两个参数，q4 测试里的 varied() 会直接失败。
#   装饰器必须对「任意签名」都成立。
#
# 常见错误写法三：把函数对象本身当返回值，忘了调用
#     return func                  # 而不是 func(*args, **kwargs)
#   错在哪：调用 add(1, 2) 得到的是「调用 func() 且不传参数」的结果，
#   会 TypeError: missing 2 required positional arguments。
#
# 常见错误写法四：只支持位置参数
#     def wrapper(*args): return func(*args)
#   错在哪：add(1, 2, c=10) 会 TypeError。**kwargs 不能省。
#
# 常见错误写法五：计数器用全局变量
#     _calls = 0
#     def wrapper(*args, **kwargs):
#         global _calls
#         _calls += 1
#   错在哪：所有被 q4_count_calls 装饰的函数共用同一个计数器。
#   这正是 3.4 节说的「global 让状态难以隔离」的实例。


# ======================================================================
# q5 —— 闭包：计数器工厂
# ======================================================================
def q5_make_counter(start: int = 0, step: int = 1):
    """状态变量定义在外层函数里，两个内层函数共享同一个 cell。"""
    count = start                    # 这就是被闭包捕获的「状态」

    def bump():
        nonlocal count               # 必须声明，否则 count 变成 bump 的局部变量
        count += step                # step 是只读的，不需要 nonlocal
        return count

    def reset():
        nonlocal count               # 和 bump 共享同一个 cell
        count = start                # start 也是只读的
        return count

    return bump, reset


# 为什么这么写：
#   1. `count` 是 make_counter 的局部变量，bump / reset 是它的内层函数，
#      所以 count 是这两个函数的**自由变量**（co_freevars 里能看到它），
#      被存进 cell 里，跟着函数对象一起活到 make_counter 返回之后。
#   2. **只有写的时候才需要 nonlocal**。step 和 start 在内层函数里只是读，
#      读自由变量不需要任何声明。判断规则：
#          只读 -> 不写
#          有 x = ... / x += ... / del x 这种绑定行为 -> 必须写
#   3. bump 和 reset 必须共享同一个 cell，所以只能有一个 `count` 变量。
#      如果每个函数各自定义一份状态，reset 就影响不到 bump 了 ——
#      这正是「cell 是共享的存储位置，不是值的副本」的意义。
#   4. 用 `return bump, reset` 返回一个元组，调用方可以 `b, r = make_counter()`。
#      不写成返回字典或类的原因：两个函数就是最简单的接口。
#
# 为什么状态用闭包而不是全局变量 / 类：
#   - 全局变量：所有计数器共用一个状态，且 q5 测试里的「互相独立」会失败
#   - 类：完全可以（这就是 3.6 节说的「只读一次那个对比」），
#     但只有两个方法、一点状态的时候，闭包更短
#   - 闭包：每次调用 make_counter 都创建一套全新的 cell，天然隔离
#
# 常见错误写法一：忘了 nonlocal
#     def bump():
#         count += 1
#   错在哪：UnboundLocalError: cannot access local variable 'count'
#   —— 编译 bump 时看到 `count = ...` 就认定 count 是局部的，
#   和有没有全局的同名变量无关。这是 3.4 节那条规则的直接结果。
#
# 常见错误写法二：用可变对象绕过 nonlocal
#     def make_counter(start=0, step=1):
#         state = [start]              # 用列表装状态
#         def bump():
#             state[0] += step         # 改内容，不需要 nonlocal
#             return state[0]
#         return bump, ...
#   能跑通，也是很多老代码的写法（因为 nonlocal 是 Python 3 才有的）。
#   但现在没必要了 —— 这种写法可读性更差，而且和 3.2 节的陷阱形态很像。
#   nonlocal 存在于就是为了干这件事。
#
# 常见错误写法三：把 count 定义在模块级再 return 内层函数
#   错在哪：所有 make_counter 的返回值共享同一个 count，
#   q5 的「bump3() 应该是 1」这条会失败。
#
# 常见错误写法四：返回 count 的值而不是函数
#     return count + step          # 忘了定义内层函数
#   错在哪：调用方拿到的是数字，不是可调用对象，bump() 会 TypeError。
#
# 常见错误写法五：用默认参数假装是闭包
#     def bump(_count=[start]):
#         _count[0] += step
#         return _count[0]
#   错在哪：这个 _count 列表在 def 执行时创建一次，
#   如果 make_counter 被调用多次，每次都是新的列表，看起来没问题；
#   但 reset 要改 start 的时候就写不出来了，而且这是 3.2 节陷阱的变体，
#   读代码的人要花时间确认它到底安不安全。


# ======================================================================
# q6 —— 延迟绑定陷阱的修复
# ======================================================================
def q6_make_multipliers(factors: list[int]) -> list:
    """修复方式二：工厂函数。每次调用产生一个新的作用域。"""
    return [_make_one(f) for f in factors]


def _make_one(factor: int):
    """给单个因子造一个乘法函数。"""
    def multiply(x):
        return x * factor            # factor 是这个作用域的参数，每个函数一份
    return multiply


# 为什么这么写：
#   错的版本长这样：
#       return [lambda x: x * f for f in factors]
#   四个 lambda 共享同一个 f 的 cell，循环结束后 f 停在最后一个元素，
#   所以 [f(10) for f in fns] 得到 [30, 30, 30, 30]。
#   叫「延迟绑定」是因为：名字的解析发生在**调用时**，不是定义时。
#
#   工厂函数把「捕获变量」变成「捕获函数参数」：每次调用 _make_one 都会
#   创建一个新的栈帧，factor 是这个帧的参数，所以每个 multiply 的
#   __closure__[0] 指向各自独立的 cell。
#
#   另外两种同样正确的写法：
#
#   写法二：默认参数固化（最短）
#       return [lambda x, f=f: x * f for f in factors]
#     f=f 的默认值在 lambda **定义时**求值一次，那时 f 正好是当次循环的值。
#     注意这用的是 3.2 节那个「陷阱」的同一个机制 —— 区别在于 f 是不可变的 int。
#     共享不可变对象永远安全，共享可变对象才是灾难。
#
#   写法三：functools.partial
#       def _mul(factor, x):
#           return x * factor
#       return [functools.partial(_mul, f) for f in factors]
#     最干净的一种，因为它完全不依赖闭包的细节 —— 参数早就被冻进
#     partial 对象的 .args 里了，跟 cell 一点关系都没有。
#
# 为什么推荐工厂函数（本答案的选择）：
#   1. 最好读：一眼看出「每个 f 造一个函数」
#   2. 顺便给函数起了名字 _make_one，调试器 / traceback 里能看到它，
#      而不是满屏的 <lambda>（模块 03 的 3.5 节提过这点）
#   3. 不依赖「默认参数在定义时求值」这个容易忘的规则
#
# 常见错误写法一：直接列表推导（原题警告的那个）
#   就是延迟绑定陷阱本身。
#
# 常见错误写法二：默认参数写成可变对象
#     [lambda x, f=[]: ... for f in factors]
#   错在哪：虽然这里每次循环都会新建一个字面量列表（因为字面量在定义时求值），
#   看起来没共享；但一旦写成 `cache=[]` 然后又 append，就退化成 3.2 节的陷阱。
#   用默认参数固化时，只固化不可变对象。
#
# 常见错误写法三：以为用 for 循环 append 就能避开
#     funcs = []
#     for f in factors:
#         funcs.append(lambda x: x * f)
#   错在哪：和列表推导完全一样的问题 —— 闭包捕获的是变量不是值，
#   循环结束后 f 还是最后一个元素。
#
# 这个陷阱在真实项目里的样子：
#     按钮/菜单项的回调注册、事件监听器、多线程任务提交……
#     凡是「在循环里创建回调」的地方都会遇到。
#     调试时的典型症状是「所有回调的行为都像最后一个」。


# ======================================================================
# q7 —— lru_cache 记忆化
# ======================================================================
@functools.lru_cache(maxsize=None)
def q7_fib(n: int) -> int:
    """递归 + 记忆化。装饰器让每层只算一次，O(n) 而不是 O(2^n)。"""
    return n if n < 2 else q7_fib(n - 1) + q7_fib(n - 2)


# 为什么这么写：
#   1. 朴素递归的 fib(30) 要算约 270 万次调用，fib(100) 要算到宇宙毁灭。
#      lru_cache 记住「n -> fib(n)」的结果，每个 n 只真正递归一次，
#      总调用次数降到 O(n)。
#   2. `maxsize=None` 表示不淘汰、无限增长，等价于 functools.cache（3.9+）。
#      fib 的参数空间是 0..n，很有限，所以不淘汰是安全的。
#   3. 加了装饰器之后，函数对象上多了这些方法：
#          q7_fib.cache_info()    -> CacheInfo(hits=8, misses=11, ...)
#          q7_fib.cache_clear()   -> 清空
#          q7_fib.__wrapped__(n)  -> 调用没被缓存的原始版本
#      cache_info 的 hits / misses 是排查缓存有没有生效的第一手证据。
#
# 常见错误写法一：装饰器写成 @functools.lru_cache() 或者忘了写
#     @functools.lru_cache
#     def q7_fib(n): ...
#   错在哪：`@lru_cache` 不带括号时，被装饰的函数被当成了 maxsize 参数传进去，
#   结果是 maxsize 等于这个函数对象 —— 类型错误，装饰器内部会报错。
#   记住规则：`@app.route` 这种不带括号的，装饰器本身就是最终形态；
#   `@lru_cache(...)` 这种带括号的，装饰器是「调用一次之后返回装饰器」的工厂。
#   判断方法看定义：`def lru_cache(maxsize=128, typed=False)` 第一个参数是配置，
#   `def wraps(f)` 第一个参数就是被装饰的函数。
#
# 常见错误写法二：改成循环为了「不依赖 lru_cache」
#     a, b = 0, 1
#     for _ in range(n): a, b = b, a + b
#     return a
#   这也算对（而且更快），但题目要求保留递归写法 —— 目的是练 lru_cache。
#   真实项目里当然是循环更好。
#
# 常见错误写法三：用 lru_cache 缓存有副作用的函数
#     @functools.cache
#     def log_and_get(n):
#         print(n)         # 只会打印一次
#         return n * 2
#   错在哪：不是 bug，但副作用只在第一次发生。日志、计数、写文件、
#   发请求，这些都不能放进缓存函数里。
#
# 常见错误写法四：缓存实例方法
#     class A:
#         @functools.lru_cache(maxsize=128)
#         def get(self, key): ...
#   错在哪：缓存键是 (self, key)，self 进了键 —— 于是每个实例都被 lru_cache
#   强引用着，对象永远回收不掉（内存泄漏），而且不同实例之间也不共享缓存。
#   正解是把纯函数提到模块级缓存，方法里调用它。
#
# 常见错误写法五：认为 lru_cache 能接收任何参数
#     @functools.cache
#     def f(items): ...
#     f([1, 2])            # TypeError: unhashable type: 'list'
#   错在哪：缓存底层是 dict，键是实参元组，所以参数必须可哈希。
#   要缓存列表就先转成 tuple / frozenset，或者用 str 做键。
#
# 还有一个和测试相关的点：缓存是**跨调用持续存在的全局状态**。
#   写单测时要在 setUp 里 cache_clear()，否则用例之间互相污染，
#   会出现「单独跑能过、一起跑就挂」的诡异现象。


# ======================================================================
# q8 —— functools 工具箱：partial 与 reduce
# ======================================================================
def _format_value(prefix: str, width: int, precision: int, value: float) -> str:
    """把 (prefix, width, precision, value) 全收下的辅助函数。

    注意格式说明符里的 width / precision 是**嵌套替换字段**：
        f"{value:>{width}.{precision}f}"
    内层的 {width} / {precision} 会先被求值，再拼成完整的格式说明符。
    """
    return f"{prefix}{value:>{width}.{precision}f}"


def q8_make_formatter(prefix: str, width: int, precision: int = 2):
    """用 partial 把前三个参数冻住，剩下的 value 留给调用时传。"""
    return functools.partial(_format_value, prefix, width, precision)


# 为什么这么写：
#   1. `functools.partial(f, a, b)` 返回一个对象，调用它时相当于
#      `f(a, b, 你传的参数...)`。它实现了 __call__，所以能当函数用。
#   2. 题目特意要求返回 partial 而不是 lambda，原因是二者的分工：
#          partial  -> 固定一部分参数（参数个数变了，函数体没变）
#          lambda   -> 改造参数（参数个数可能没变，但表达式变了）
#      `lambda v: _format_value(prefix, width, precision, v)` 也能跑通，
#      但它对调试器是一团黑盒：类型是 function、名字是 <lambda>，
#      看不到它固定了哪些参数。partial 对象有 .func / .args / .keywords，
#      在调试器的「监视」面板里加一下就知道它是什么。
#   3. 辅助函数 _format_value 定义在模块级（而不是在 q8_make_formatter 内部），
#      这样 partial.func 是一个有名字、有文档的普通函数，更好调试。
#      定义在内部也能工作，但 traceback 里会多一层 <locals>。
#
# 常见错误写法一：用 lambda
#     return lambda value: f"{prefix}{value:>{width}.{precision}f}"
#   能跑通，但不符合题目要求，而且丢失了 partial 的可检查性。
#
# 常见错误写法二：忘了 precision 参数可以传位置
#     return functools.partial(_format_value, prefix=prefix, width=width)
#   这样写 precision 用的是默认值 2，q8_make_formatter("", 6, 1) 会得到 2 位小数，
#   测试会挂。partial 的位置参数和关键字参数是可以混的，但要想清楚哪个是哪个：
#       partial(f, a, b)          -> 固定前两个位置参数
#       partial(f, prefix="x")    -> 固定关键字参数，调用时还能被覆盖
#   本题的辅助函数签名是 (prefix, width, precision, value)，所以位置传最自然。
#
# 常见错误写法三：忘了 functools.partial 也可以接收调用时的额外参数
#     square = functools.partial(power, exp=2)
#     square(5, exp=3)          # 合法！调用时的关键字会覆盖 partial 冻住的
#   这不是错误，是个容易惊讶的点：partial 冻的是「默认值」，不是「不可改的常量」。
#   想真正锁死就用位置参数配合 positional-only，或者干脆写个新函数。
#
# 常见错误写法四：用嵌套函数而不是 partial
#     def q8_make_formatter(prefix, width, precision=2):
#         def format_value(value):
#             return f"{prefix}{value:>{width}.{precision}f}"
#         return format_value
#   完全能跑，也是合法的闭包用法（q6 就是这么干的）。
#   区别在于：闭包捕获的是**变量**，partial 固定的是**值**。
#   闭包的捕获是活的（外层变量变了内层也看到），partial 冻住的就是冻住了。
#   本题要求用 partial 是为了让你把两种工具都握在手里。

def q8_fold(operation: str, values: list[float], initial: float) -> float:
    """把「选哪个折叠」和「怎么折叠」拆开：字典选函数，reduce 干活。"""
    ops = {
        "sum": lambda a, b: a + b,
        "prod": lambda a, b: a * b,
        "max": lambda a, b: a if a > b else b,
    }
    if operation not in ops:
        raise ValueError(f"未知的折叠方式：{operation!r}，可选 {sorted(ops)}")
    return functools.reduce(ops[operation], values, initial)


# 为什么这么写：
#   1. functools.reduce(f, values, initial) 的执行过程是
#          f(f(f(initial, v0), v1), v2) ...
#      给了 initial 之后，空列表会直接返回 initial，不需要特判 ——
#      这正是题目提示里说的「不需要特判空列表」。
#   2. 把「选哪个操作」做成字典查表，而不是 if/elif 长链。
#      这样加一个新的折叠方式只要往字典里加一行，不用改控制流。
#      （装饰器那题的 ops 字典、模块 3.5 节的 ops = {"+": add, "-": sub} 是同一个套路。）
#   3. 抛 ValueError 而不是返回 None / 0：非法输入必须和合法结果区分开。
#      消息里带上 operation 的值，这样日志里能直接看到是谁传错了。
#
# 常见错误写法一：不用 reduce，手写 for 循环
#     result = initial
#     for v in values:
#         result = ops[operation](result, v)
#     return result
#   能跑通，其实**在 Python 里这往往更好读**（3.8 节说过 reduce 名声不好）。
#   本题要求 reduce 是为了练这个 API。
#
# 常见错误写法二：忘了 initial
#     return functools.reduce(ops[operation], values)
#   错在哪：空列表会抛 TypeError: reduce() of empty iterable with no initial value。
#   就算列表不空，[1, 2, 3] 的 sum 也会变成 6 而不是 6 —— 咦，一样？
#   因为 initial=0 对加法没影响。但对 max 就完全不一样了：
#       reduce(max_func, [3, 9, 2])       -> 9
#       reduce(max_func, [3, 9, 2], 100)  -> 100
#   题目要求 initial 参与比较，所以必须传。
#
# 常见错误写法三：把 lambda 写成两行
#     "sum": lambda a, b: (
#         a + b
#     )
#   语法上合法（括号里可以换行），但 lambda 的边界就是「一个短表达式」。
#   一旦需要折行，就该老老实实写 def —— 这是 3.5 节讲的 lambda 边界。
#
# 常见错误写法四：用 sum() 代替 reduce 实现 "sum"
#   那是另一种「选对了工具」的答案，但题目要求练 reduce。
#   真实代码里确实应该用 sum()：内置函数更快，也更明确。
#
# 顺带说一句 reduce 的历史：
#   它本来是 Python 2 的内置函数，Guido 在 Python 3 里把它移到了 functools，
#   理由就是「一个 for 循环更清楚」。所以你在真实项目里看到 reduce，
#   通常意味着这段代码是 2008 年之前写的，或者作者是从函数式语言转过来的。
#   求和用 sum、求积用 math.prod、求最值用 max、拼接用 join —— 这些才是 Python 味。


# ======================================================================
# q9 —— 带参数的装饰器：重试
# ======================================================================
def q9_retry(times: int, exceptions: tuple = (Exception,)):
    """三层嵌套：retry 收配置 -> decorator 收 func -> wrapper 收实参。"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last = None
            for attempt in range(1, times + 1):
                try:
                    return func(*args, **kwargs)     # 成功就立刻返回
                except exceptions as exc:
                    last = exc
            raise last                               # 全部失败，抛最后一次的异常
        return wrapper
    return decorator


# 为什么这么写：
#   1. 三层结构一定要刻进脑子。`@q9_retry(3)` 的求值顺序是：
#          q9_retry(3)        -> 返回 decorator            （一次）
#          decorator(flaky)   -> 返回 wrapper              （一次）
#          wrapper()          -> 真正执行 flaky            （每次调用）
#      对比不带参数的 `@timer`：只有两层，因为被装饰的函数本身就是那个参数。
#      区分方法：装饰器定义里第一个参数**是函数还是配置**。
#   2. `raise last` 是必须的。忘了它，重试全部失败时 wrapper 会返回 None ——
#      静默失败比直接报错糟糕得多，因为调用方拿到 None 之后可能再走几百行才炸，
#      而且 traceback 指向的是调用方而不是出错点。
#      如果想保留「第一次失败的现场」，可以用 `raise last from first_error`。
#   3. `except exceptions as exc` 里 exceptions 是元组，正好是 except 接受的类型。
#      默认值 (Exception,) 是**不可变**的元组，不存在 3.2 节的默认参数陷阱。
#      注意元组里必须留逗号：(Exception,) 是元组，(Exception) 只是打了括号的类。
#   4. `for attempt in range(1, times + 1)` 保证总共尝试 times 次。
#      attempt 变量这里没用上，但保留它能让「第几次」在调试时一眼可见，
#      也方便将来加退避 sleep：time.sleep(backoff ** attempt)。
#   5. functools.wraps 同样是标配。测试里断言 flaky.__name__ == "flaky"。
#
# 常见错误写法一：忘了 raise
#     for _ in range(times):
#         try:
#             return func(*args, **kwargs)
#         except exceptions:
#             pass
#     # 这里什么都不写
#   错在哪：全部失败时返回 None。这是本模块最危险的错误之一。
#
# 常见错误写法二：只捕获 Exception 而不接受参数
#     def q9_retry(times):
#         def decorator(func):
#             def wrapper(*args, **kwargs):
#                 try: ...
#                 except Exception:   # 忽略了 exceptions 参数
#   错在哪：题目要求「不在列表里的异常立刻抛出」，测试的 wrong_type 用例会挂。
#   而且真实场景里这很重要：ValueError 值得重试（可能是数据竞争），
#   TypeError 重试一万次也没用，只会浪费时间。
#
# 常见错误写法三：重试次数写成 range(times) 之外的东西
#     for _ in range(times + 1):     # 多试了一次
#   错在哪：语义变成「1 次首发 + times 次重试」。两种约定都有人用，
#   但**必须和文档写的一致**，否则调用方会按错误的次数预估超时时间。
#   本题的约定是「总共尝试 times 次」。
#
# 常见错误写法四：把 retry 和 decorator 合成一层
#     def q9_retry(times, exceptions=(Exception,), func=None):
#         ...
#   能实现（就是 3.7 节讲的 func=None 双形态技巧），但语句会绕很多。
#   三层嵌套虽然多缩进一级，但结构是最清楚的 —— 标准库和主流库都这么写。
#
# 常见错误写法五：在 wrapper 里 sleep 但不做退避
#     except exceptions:
#         time.sleep(1)
#   错在哪：固定 1 秒的立即重试在真实系统里是「重试风暴」的制造者 ——
#   上游刚挂，几万个客户端同时每秒锤它一次。生产代码要用指数退避 + 抖动：
#       time.sleep(min(60, 0.5 * 2 ** attempt) * (0.5 + random.random() / 2))
#   Python 3.14 的标准库还没有内置的重试工具，
#   实际项目一般用第三方库 tenacity，或者自己封装。
#
# 最后一个容易忽略的点：装饰器在**定义时**就执行了（3.7 节）。
#   所以 q9_retry(-1) 这种配置错误也是定义时就生效的（range 为空 -> 永远返回 None）。
#   认真的装饰器工厂应该在 retry 里就校验参数：
#       if times < 1:
#           raise ValueError("times 必须 >= 1")


# ======================================================================
# 自测（和 exercises.py 保持一致）
# ======================================================================
def t_q1() -> None:
    assert q1_add_tag("a") == ["a"], f"实际 {q1_add_tag('a')!r}"
    assert q1_add_tag("b") == ["b"], "第二次调用把上一次的结果带出来了，默认值是可变对象"
    assert q1_add_tag("c") == ["c"]

    base = ["x"]
    got = q1_add_tag("y", base)
    assert got == ["x", "y"], f"实际 {got!r}"
    assert got is not base, "必须返回新列表，而不是把传进来的列表直接返回"
    assert base == ["x"], "不能修改调用方传进来的列表"


def t_q2() -> None:
    assert q2_make_url("example.com", "a/b") == "https://example.com/a/b"
    assert q2_make_url("example.com", "/a/b") == "https://example.com/a/b"
    assert q2_make_url("example.com", "/a", scheme="http") == "http://example.com/a"
    assert q2_make_url("example.com", "/a", port=8080) == "https://example.com:8080/a"
    assert q2_make_url("example.com", "/a", scheme="http", port=80) == "http://example.com/a"
    assert q2_make_url("example.com", "/a", scheme="https", port=443) == "https://example.com/a"

    try:
        q2_make_url(host="example.com", path="/a")
    except TypeError:
        pass
    else:
        raise AssertionError("host / path 是 positional-only，用关键字传应该 TypeError")

    try:
        q2_make_url("example.com", "/a", "http")
    except TypeError:
        pass
    else:
        raise AssertionError("scheme / port 是 keyword-only，用位置传应该 TypeError")


def t_q3() -> None:
    assert q3_top_scorer(len, "a", "bbb", "cc") == "bbb"
    assert q3_top_scorer(len, "bbb", "cc", "a") == "bbb"
    assert q3_top_scorer(abs, -5, 3, -2) == -5
    assert q3_top_scorer(str.lower, "Apple", "banana") == "banana"

    tie = [("a", 9), ("b", 9), ("c", 1)]
    assert q3_top_scorer(lambda t: t[1], *tie) == ("a", 9)

    assert q3_top_scorer(len) is None
    assert q3_top_scorer(len, default="") == ""

    seen: list[int] = []

    def spy(x: int) -> int:
        seen.append(x)
        return x

    assert q3_top_scorer(spy, 3, 1, 2) == 3
    assert sorted(seen) == [1, 2, 3], f"key 应该对每个元素都调用一次，实际 {seen}"


def t_q4() -> None:
    @q4_count_calls
    def add(a, b):
        """两数相加。"""
        return a + b

    assert add(1, 2) == 3, "返回值必须原样透传"
    assert add.calls == 1, f"add.calls 应该是 1，实际 {getattr(add, 'calls', '没有这个属性')}"
    assert add(3, 4) == 7
    assert add.calls == 2, f"add.calls 应该是 2，实际 {add.calls}"

    assert add.__name__ == "add", f"__name__ 应该是 'add'，实际 {add.__name__!r}"
    assert add.__doc__ == "两数相加。", f"__doc__ 丢了：{add.__doc__!r}"
    assert hasattr(add, "__wrapped__"), "wraps 会设置 __wrapped__，没有它说明没写 wraps"

    @q4_count_calls
    def varied(a, b=2, *args, **kwargs):
        return (a, b, args, sorted(kwargs.items()))

    assert varied(1) == (1, 2, (), [])
    assert varied(1, 3, 5, x=9) == (1, 3, (5,), [("x", 9)])
    assert varied.calls == 2

    @q4_count_calls
    def other():
        return None

    other()
    assert other.calls == 1
    assert add.calls == 2, "计数器不能是全局共享的"


def t_q5() -> None:
    bump, reset = q5_make_counter()
    assert bump() == 1
    assert bump() == 2
    assert bump() == 3
    assert reset() == 0
    assert bump() == 1, "reset 之后应该从 start 重新开始"

    bump2, reset2 = q5_make_counter(10, 5)
    assert bump2() == 15
    assert bump2() == 20
    assert reset2() == 10
    assert bump2() == 15

    bump3, _ = q5_make_counter()
    assert bump3() == 1, "新的计数器不该受之前那个影响"
    assert bump2() == 20, "老计数器也不该被新计数器影响"


def t_q6() -> None:
    fns = q6_make_multipliers([1, 2, 3])
    got = [f(10) for f in fns]
    assert got == [10, 20, 30], f"期望 [10, 20, 30]，实际 {got}（大概是延迟绑定陷阱）"

    assert q6_make_multipliers([]) == []

    assert [f(2) for f in fns] == [2, 4, 6]
    assert fns[0](0) == 0

    fns2 = q6_make_multipliers([0, -1, 100])
    assert [f(5) for f in fns2] == [0, -5, 500]
    assert callable(fns2[0]), "返回的应该是可调用对象"


def t_q7() -> None:
    # 先调用一次：这样没做这道题时会得到 SKIP 而不是 FAIL。
    assert q7_fib(0) == 0
    assert q7_fib(1) == 1
    assert q7_fib(10) == 55
    assert q7_fib(30) == 832040

    assert hasattr(q7_fib, "cache_info"), \
        "q7_fib 必须用 functools.lru_cache 或 functools.cache 装饰"

    q7_fib.cache_clear()
    assert q7_fib(0) == 0
    assert q7_fib(1) == 1
    assert q7_fib(10) == 55
    assert q7_fib(30) == 832040

    q7_fib.cache_clear()
    assert q7_fib(30) == 832040
    first = q7_fib.cache_info()
    assert first.misses >= 1, f"第一次计算不应该全是命中：{first}"

    q7_fib(30)
    second = q7_fib.cache_info()
    assert second.hits == first.hits + 1, f"重复调用必须命中缓存：{first} -> {second}"
    assert second.misses == first.misses, f"重复调用不该产生新的未命中：{first} -> {second}"


def t_q8() -> None:
    money = q8_make_formatter("金额: ", 8)
    assert isinstance(money, functools.partial), \
        f"q8_make_formatter 必须返回 functools.partial 对象，实际是 {type(money).__name__}"
    assert money(3.14159) == "金额: " + f"{3.14159:>8.2f}"
    assert money(0.5) == "金额: " + f"{0.5:>8.2f}"

    pct = q8_make_formatter("", 6, 1)
    assert pct(0.25) == f"{0.25:>6.1f}"
    assert pct(1.0) == f"{1.0:>6.1f}"

    assert q8_fold("sum", [1, 2, 3, 4], 0) == 10
    assert q8_fold("sum", [], 100) == 100
    assert q8_fold("prod", [1, 2, 3, 4], 1) == 24
    assert q8_fold("prod", [2, 5], 1) == 10
    assert q8_fold("max", [3, 9, 2], 0) == 9
    assert q8_fold("max", [3, 9, 2], 100) == 100
    assert q8_fold("sum", [1.5, 2.5], 0.0) == 4.0

    try:
        q8_fold("average", [1, 2], 0)
    except ValueError as exc:
        assert "average" in str(exc), f"ValueError 的消息里应该带上那个值：{exc}"
    else:
        raise AssertionError("未知的 operation 应该抛 ValueError")


def t_q9() -> None:
    calls = {"n": 0}

    @q9_retry(3)
    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError(f"第 {calls['n']} 次故意失败")
        return "ok"

    assert flaky() == "ok", "第三次应该成功"
    assert calls["n"] == 3, f"应该尝试 3 次，实际 {calls['n']} 次"
    assert flaky.__name__ == "flaky", "必须用 functools.wraps 保留 __name__"

    always = {"n": 0}

    @q9_retry(2)
    def always_fail():
        always["n"] += 1
        raise RuntimeError("一直失败")

    try:
        always_fail()
    except RuntimeError:
        pass
    else:
        raise AssertionError("重试全部失败后必须把异常抛出去，不能吞掉返回 None")
    assert always["n"] == 2, f"应该尝试 2 次，实际 {always['n']} 次"

    typed = {"n": 0}

    @q9_retry(5, (ValueError,))
    def wrong_type():
        typed["n"] += 1
        raise TypeError("不该被重试")

    try:
        wrong_type()
    except TypeError:
        pass
    else:
        raise AssertionError("TypeError 不在 exceptions 里，应该原样抛出")
    assert typed["n"] == 1, f"不该重试，实际尝试了 {typed['n']} 次"

    @q9_retry(3)
    def add(a, b, c=0):
        return a + b + c

    assert add(1, 2) == 3
    assert add(1, 2, c=10) == 13


def main() -> None:
    c = Checker("模块 03 · 函数与作用域 参考答案")
    c.add("q1  修复可变默认参数陷阱", t_q1)
    c.add("q2  positional-only 与 keyword-only", t_q2)
    c.add("q3  *args 配合 key 函数", t_q3)
    c.add("q4  手写装饰器：调用计数", t_q4)
    c.add("q5  闭包：计数器工厂", t_q5)
    c.add("q6  延迟绑定陷阱的修复", t_q6)
    c.add("q7  lru_cache 记忆化", t_q7)
    c.add("q8  functools 工具箱：partial 与 reduce", t_q8)
    c.add("q9  带参数的装饰器：重试", t_q9)
    c.run()


if __name__ == "__main__":
    main()
