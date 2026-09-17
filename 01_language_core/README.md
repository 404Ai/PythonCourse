# 模块 01 · 语言核心：对象模型与类型系统

> **目标**：如果你的母语是 C / C++ / Java，那么读 Python 代码时你脑子里
> 默认的内存图景是**错的**。这个模块的唯一任务，就是把那张图纠正过来。
>
> 这个模块看起来「简单」，但它是后面 9 个模块的地基。
> 学完请务必打开调试器，亲手验证每一个结论。

---

## 1.1 从源码到运行：Python 是怎么执行你的代码的

很多人说「Python 是解释型语言」，这句话只对了一半。

实际的流程是：

```
  hello.py               编译期（import 时发生一次）
     │
     │  ↓ 词法分析 → 语法分析 → 生成 AST → 编译
     │
  hello.pyc  ──────────►  CPython 字节码（bytecode）
     │  存在 __pycache__/         │
     │                            │  运行期（每次执行）
     │                            ▼
     └──────────────────►  Python 虚拟机（PVM）逐条执行
```

关键结论：

1. **Python 有编译阶段**，只是编译目标不是机器码，而是字节码。
2. 字节码缓存（`.pyc`）存在于 `__pycache__/` 目录，它省掉的是**每次启动时的
   解析与编译开销**，不是执行开销。所以它不会让程序跑得更快。
3. 真正执行字节码的是一个 `for` 循环 + 巨大的 `switch`（CPython 里是
   `ceval.c` 的 `_PyEval_EvalFrameDefault`）。**每一条字节码都是一次解释**，
   这就是 Python 纯计算比 C 慢几十倍的根本原因。

> 这也解释了一件事：**为什么把热循环交给 NumPy / C 扩展能快 100 倍**。
> 不是因为 NumPy 的算法更聪明，而是因为它把「逐条解释」变成了「一次性 C 循环」。

**动手**：跑 `demo.py` 的第一节，你会看到 `a + b` 被编译成了 5 条字节码指令。
再想想 C 里 `a + b` 是什么——是一条 `add` 指令。差距就在这儿。

### `if __name__ == "__main__"` 到底是什么意思

```python
# mymodule.py
print(f"__name__ = {__name__}")

if __name__ == "__main__":
    print("被直接运行")
```

- `python mymodule.py` → `__name__` 是 `"__main__"`
- `import mymodule` → `__name__` 是 `"mymodule"`

它不是「语法仪式」，而是一个真实的判断：**我是被当作程序启动的，还是被当作库导入的？**
只有前者才该执行副作用（比如启动服务器）。

---

## 1.2 变量不是盒子：名字绑定模型（本模块最重要的一节）

### C 的心智模型

```c
int a = 10;      // 分配一块内存，起名叫 a，把 10 放进去
int b = a;       // 再分配一块内存 b，把 a 的内容拷过去
b = 20;          // 改 b 那块内存，a 不受影响
```

在 C 里，**变量就是内存块**（a box）。

### Python 的心智模型

```python
a = 10       # 1. 创建一个 int 对象 10
             # 2. 把名字 a 绑定到这个对象上
b = a        # 把名字 b 也绑定到同一个对象上
b = 20       # 创建 int 对象 20，把名字 b 重新绑定到它
             # a 仍然绑定在 10 上
```

在 Python 里，**变量是贴在对象上的标签（a name tag），不是盒子**。
对象住在堆上，名字住在命名空间（namespace）里，两者靠绑定关系连起来。

一句话总结：

> **Python 的赋值语句从来不复制数据，它只改变「名字 → 对象」的指向。**

### 为什么这很重要：可变 vs 不可变

因为 `10`、`"abc"`、`(1, 2)` 是**不可变对象**，你没办法「修改」它们，
所以 `b = 20` 只能重新绑定，看起来和 C 一样。

但列表是**可变对象**：

```python
a = [1, 2, 3]
b = a            # b 和 a 是同一个列表的两个名字
b.append(4)      # 就地修改这个列表
print(a)         # [1, 2, 3, 4]  ← a 也变了！
```

这是初学者 90% 的「幽灵 bug」的来源。

### 想复制，怎么办

```python
a = [1, 2, 3]

b = a[:]                 # 浅拷贝：新列表，但元素还是共享的
b = list(a)              # 同上
b = a.copy()             # 同上（推荐，语义最清楚）

import copy
c = copy.deepcopy(a)     # 深拷贝：递归复制所有嵌套对象
```

**浅拷贝的坑**：

```python
matrix = [[1, 2], [3, 4]]
shallow = matrix[:]          # 外层是新列表，内层还是同一批子列表！
shallow[0].append(99)
print(matrix)                # [[1, 2, 99], [3, 4]]  ← 原数据被改了

deep = copy.deepcopy(matrix) # 这才是真正独立的副本
```

### 参数传递：Python 只有一种传递方式

C 里要区分「值传递」和「引用传递」。Python 两者都不是，它叫
**call by object reference**（传对象引用），或者说 **call by sharing**：

```python
def f(lst):
    lst.append(1)     # 修改对象内容 → 调用方看得见

def g(lst):
    lst = [9, 9]      # 只是把局部名字 lst 重新绑定 → 调用方看不见
```

**规律**：函数内**改内容**会影响调用方，**重新绑定名字**不会。
记住这条，你就不需要背「可变对象按引用、不可变对象按值」那种模糊口诀了。

---

## 1.3 对象三要素：`id` / `type` / `value`

Python 里**一切皆对象**——函数、类、模块、甚至 `None` 都是对象。
每个对象有三个不可变的基本属性：

| 属性 | 获取方式 | 含义 |
|------|---------|------|
| 身份 identity | `id(obj)` | 在 CPython 里就是内存地址（`id() // 16` 大约是十六进制地址） |
| 类型 type | `type(obj)` | 对象是什么类的实例 |
| 值 value | `obj == other` | 对象代表的数据 |

### `is` 与 `==` 的区别

- `a == b` → 调用 `a.__eq__(b)`，比较**值**
- `a is b` → 比较 `id(a) == id(b)`，比较**身份**

```python
a = [1, 2, 3]
b = [1, 2, 3]
a == b     # True  —— 值相同
a is b     # False —— 是两个不同的列表对象
```

### `is` 什么时候用

**只有三种情况应该用 `is`**：

```python
x is None        # 判断 None（PEP 8 明确规定）
x is True        # 判断单例布尔值
x is NotImplemented   # 极少见
```

**绝对不要**用 `is` 比较数字和字符串：

```python
if x is 1000:    # 危险！CPython 只缓存 -5~256 的小整数
                 # 大于 256 时行为取决于实现细节，PyPy 上必然出错
```

### 反直觉的 CPython 实现细节（面试常考）

**① 小整数缓存**：CPython 启动时预先创建了 `-5` 到 `256` 的 `int` 对象并永久复用。

```python
a = 256
b = 256
a is b        # True

a = 257
b = 257       # 注意：这里能是 True 是因为*编译期常量合并*，不是缓存！
a is b        # True（同一段代码里的两个 257 字面量指向同一个常量对象）

a = int("257")
b = int("257")
a is b        # False —— 运行时构造，各是各的对象
```

**② 字符串驻留（string interning）**：看起来像标识符的短字符串会被缓存复用。

```python
a = "hello"
b = "hello"
a is b        # True

a = "hello world!"     # 含空格和感叹号，不是合法标识符，不驻留
b = "hello world!"
a is b        # 可能是 False（取决于版本和编译期优化）
```

**③ 空容器**：

```python
[] is []      # False —— 每次字面量都新建
() is ()      # True  —— 空元组是单例（因为它不可变，没必要建两个）
'' is ''      # True  —— 空字符串也是单例
```

**这一节的实践结论**：这些细节**不该出现在你的业务代码里**。
`is` 只用于 `None` 和 `True`/`False`，其余一律用 `==`。

---

## 1.4 类型系统：动态 + 强类型 + 鸭子类型

### 动态类型（dynamic typing）

类型信息属于**对象**，不属于**变量**：

```python
x = 42          # 名字 x 暂时指向一个 int
x = "hello"     # 同一个名字，现在指向 str —— 完全合法
```

对比：

- **静态类型**（C/Java/Go）：类型检查在编译期，变量有固定类型
- **动态类型**（Python/Ruby/JS）：类型检查在运行期，名字可以指向任何类型

### 强类型（strong typing）

Python 是**强类型**的——它**不会替你隐式转换**：

```python
"3" + 5      # TypeError: can only concatenate str (not "int") to str
```

对比 JavaScript 会给出 `"35"`。Python 选择报错，这是好事：**错误在离它产生的地方越近越好**。

但注意 Python **有**一些隐式转换：

```python
1 + 2.5      # 3.5   int 自动提升为 float
True + 1     # 2     bool 是 int 的子类
int(3.9)     # 3     显式转换是截断，不是四舍五入！要四舍五入用 round()
```

> **`int()` 是截断不是四舍五入**，这是从 C 转过来的同学最容易踩的坑之一：
> C 里 `(int)3.9` 也是截断，但很多人写 Python 时以为 `int()` 会「取整」。

### 鸭子类型（duck typing）

> "If it walks like a duck and quacks like a duck, then it must be a duck."

Python 不关心对象**是什么类**，只关心它**能做什么**：

```python
def total(iterable):
    return sum(iterable)

total([1, 2, 3])            # 列表
total((1, 2, 3))            # 元组
total({1, 2, 3})            # 集合
total(n for n in range(4))  # 生成器
```

`total` 完全不知道也不关心参数的类型，它只要对方能被迭代。这就是为什么
Python 的很多库函数能同时处理几十种输入——**靠协议（protocol），不靠继承**。

这也是为什么 Python 程序员写文档时经常说「传一个 file-like object」——
意思是"传一个实现了 `read()` 的对象就行"，不要求它继承 `io.IOBase`。

### `type()` vs `isinstance()`

```python
type(True) is int            # False —— type() 不看继承
isinstance(True, int)        # True  —— isinstance() 看继承链
```

**永远优先用 `isinstance()`**，因为：

```python
class MyList(list):
    pass

type(MyList()) is list            # False —— 子类被拒绝了，这通常不是你想要的
isinstance(MyList(), list)        # True
```

而 `bool` 是 `int` 的子类这件事，会导致一个真实 bug：

```python
def add_item(item):
    if isinstance(item, int):
        ...          # True 也会走到这里！
```

要区分，必须先判 `bool`：

```python
if isinstance(v, bool):
    ...
elif isinstance(v, int):
    ...
```

### `type()` 的正确用途

`type()` 几乎只在一个场景用：**动态创建类**。

```python
Point = type("Point", (), {"x": 0, "y": 0})   # 等价于 class Point: x = 0; y = 0
```

---

## 1.5 数字：`int` 任意精度与 `float` 的陷阱

### `int` 是任意精度的

Python 的 `int` 没有 32/64 位限制，它**自动扩容**：

```python
2 ** 100        # 1267650600228229401496703205376
(2 ** 100).bit_length()   # 101
```

实现上，CPython 用一个 `30 位一组的数组`来存大整数（`ob_digit`），
运算时按组做竖式运算。所以：

- 小整数的加减**很快**（就是一次 C 的 `long` 运算）
- 超出 30 位后开始变慢，但**永远不会溢出**

对比 Java 的 `int` 会溢出，Python 不会——代价是大整数运算更慢。

### `float` 是 IEEE-754 双精度

```python
0.1 + 0.2                # 0.30000000000000004
0.1 + 0.2 == 0.3         # False ！
```

**这不是 Python 的 bug，是所有使用 IEEE-754 的语言的共同行为**
（C、Java、JS 都一样）。`0.1` 在二进制里是无限循环小数，只能近似存储。

```python
from decimal import Decimal
Decimal("0.1") + Decimal("0.2")     # Decimal('0.3')  ← 精确

from fractions import Fraction
Fraction(1, 3) + Fraction(1, 6)     # Fraction(1, 2) ← 精确
```

**浮点数三条军规**：

1. **永远不要用 `==` 比较浮点数**，用 `math.isclose(a, b)`
2. **涉及金额一律用 `Decimal`**（或者干脆用「分」为单位的整数）
3. 打印浮点数时用格式化控制精度：`f"{x:.2f}"`

```python
import math
math.isclose(0.1 + 0.2, 0.3)              # True
math.isclose(1e-10, 0, abs_tol=1e-9)      # True，和 0 比较要用绝对容差
```

### 其他数字类型速查

| 类型 | 说明 | 什么时候用 |
|------|------|-----------|
| `int` | 任意精度整数 | 默认 |
| `float` | 双精度浮点 | 科学计算 |
| `complex` | 复数，`3+4j` | 信号处理、数学 |
| `Decimal` | 十进制浮点，精确 | **金额、财务** |
| `Fraction` | 有理数 | 精确分数运算 |
| `bool` | `True`/`False`，是 `int` 子类 | 逻辑判断 |

### 常用数字操作

```python
7 / 2        # 3.5   真除法，结果永远是 float
7 // 2       # 3     向下取整除法（注意：-7 // 2 是 -4，不是 -3！）
7 % 2        # 1     取模（Python 的模结果符号永远跟除数走）
divmod(7, 2) # (3, 1)  同时拿到商和余数，比算两次快
abs(-3)      # 3
round(2.5)   # 2     ← 银行家舍入（round half to even），不是四舍五入！
```

> **`round(2.5)` 是 `2` 不是 `3`**。Python 3 用的是「四舍六入五成双」，
> 因为这样在大量统计时不会累积偏差。要传统四舍五入得用
> `Decimal("2.5").quantize(Decimal("1"), rounding=ROUND_HALF_UP)`。

> **`-7 // 2 == -4`**：Python 的 `//` 是「向下取整」而不是「向零截断」。
> 这是为了让 `a == (a // b) * b + a % b` 这个恒等式成立。

---

## 1.6 字符串与格式化

### 字符串是不可变的

```python
s = "hello"
s.upper()      # 返回新字符串 "HELLO"
print(s)       # "hello" —— 原串没变
s[0] = "H"     # TypeError！不支持项赋值
```

**不可变带来的好处**：字符串可以安全地做字典键、可以被驻留、可以多线程共享。
**代价**：循环里拼接字符串是 O(n²)：

```python
# 慢：每次 += 都新建一个字符串并复制全部内容
result = ""
for word in words:
    result += word        # O(n²)

# 快：join 先算出总长度，一次性分配
result = "".join(words)   # O(n)
```

### f-string（Python 3.6+，最推荐）

```python
name, score = "张三", 0.8765

f"{name} 的得分率 {score:.2%}"      # "张三 的得分率 87.65%"
f"{1234567:,}"                      # "1,234,567"
f"{255:#x}"                         # "0xff"
f"{255:08b}"                        # "11111111"
f"{3.14159:.2f}"                    # "3.14"
f"{42:>10}"                         # "        42"   右对齐
f"{42:<10}|"                        # "42        |"  左对齐
f"{42:^10}|"                        # "    42    |"  居中
f"{'a':*^9}"                        # "****a****"    填充字符
f"{x = }"                           # "x = 42"       3.8+ 调试神器
```

**`f"{x = }"` 值得单独记一下**——调试时不用再写 `print("x =", x)`。

> ⚠️ **中文字符宽度陷阱**：`f"{'苹果':<8}"` 补到 8 个**字符**，
> 但终端里中文占 2 个**显示列**，所以看起来还是歪的。
> 真正的表格对齐需要用 `wcwidth` 库或者手动算显示宽度。

### 三种格式化方式的历史

```python
"%s: %d" % (name, 42)              # 1. C 风格（老代码里还有）
"{}: {}".format(name, 42)          # 2. str.format（3.6 前的标准）
f"{name}: {42}"                    # 3. f-string（现在一律用这个）
```

`str.format` 在一种场景下还有用：**模板需要复用**时。

```python
TPL = "{name} 考了 {score} 分"
TPL.format(name="张三", score=90)
TPL.format(name="李四", score=85)
```

### 常用字符串方法

```python
s.strip() / s.lstrip() / s.rstrip()       # 去空白（注意：去掉所有指定字符，不是前缀！）
s.split(",")       / s.rsplit(",", 1)     # 切分
s.replace(a, b)                           # 替换（返回新串）
s.startswith(x) / s.endswith(x)           # 判断前后缀（可以传元组）
s.find(x)  / s.index(x)                   # 找位置（find 返回 -1，index 抛异常）
s.upper() / s.lower() / s.title() / s.casefold()   # casefold 才是正确的大小写无关比较
s.zfill(5)                                # 补零
s.isdigit() / s.isalpha() / s.isspace()
",".join(iterable)                        # 拼接（元素必须都是 str）
```

> `s.strip()` 的参数是**字符集合**，不是子串：
> `"www.example.com".strip("wcom.")` 得到 `"example"`（把首尾所有 w/c/o/m/. 字符都削掉）。

---

## 1.7 真值、`None` 与条件表达式

### 什么是「假」

只有这些是假值：

```python
False, None, 0, 0.0, 0j, Decimal(0), Fraction(0, 1),
"", [], (), {}, set(), range(0)
```

其余一切都是真，**包括**：

```python
bool("0")     # True  ← 非空字符串
bool([0])     # True  ← 非空列表（哪怕内容是 0）
bool("False") # True  ← 非空字符串
```

所以**判空不要用 `if x == ""`，也不要依赖 `if x`** 去判断一个可能是 `"0"` 的字符串。

```python
if not items:              # 判空，推荐
    ...

if x is None:              # 判 None，必须用 is
    ...
```

### `None`

- `None` 是**单例**，整个进程里只有一个
- 函数没有 `return` 时，隐式返回 `None`
- **不要**把 `None` 和「空字符串」「0」混为一谈——它们的语义完全不同：
  - `None` = 「没有值」
  - `""` = 「值是空串」
  - `0` = 「值是零」

### 条件表达式（三目）

```python
label = "偶数" if x % 2 == 0 else "奇数"
```

注意它**不是** C 的 `?:` 的语法糖顺序，Python 的顺序是 `值 if 条件 else 值`，
读作「如果条件成立就取前面的值，否则取后面的值」。

### 链式比较

```python
0 <= x < 100        # Python 写法
```

这是**真的链式**，等价于 `0 <= x and x < 100`，而且 `x` 只会求值一次：

```python
def f():
    print("f 被调用")
    return 5

0 < f() < 10        # "f 被调用" 只打印一次
```

而 C 里 `0 <= x < 100` 会被解析成 `(0 <= x) < 100`，即 `0或1 < 100`，恒为真——
**这是个经典的 C 陷阱，Python 专门修掉了它**。

### `:=` 海象运算符（3.8+）

在表达式里赋值，避免写两遍：

```python
# 之前
data = get_data()
if data:
    process(data)

# 现在
if data := get_data():
    process(data)
```

```python
while chunk := file.read(8192):
    handle(chunk)
```

---

## 1.8 常见坑速查

| 坑 | 症状 | 正解 |
|----|------|------|
| `b = a` 以为是复制 | 改 `b` 把 `a` 也改了 | `b = a.copy()` 或 `copy.deepcopy(a)` |
| `x is 1000` | 换解释器就出错 | 用 `==` |
| `0.1 + 0.2 == 0.3` | 恒为 `False` | `math.isclose()` |
| `round(2.5)` | 得到 2 | 用 `Decimal` + `ROUND_HALF_UP` |
| `int(-3.9)` | 得到 -3（向零截断） | 明确你要的是截断还是取整 |
| `-7 // 2` | 得到 -4 | 记住 `//` 是向下取整 |
| `s.strip("ab")` | 把中间的字符也削了 | 参数是字符集合，用 `removeprefix`/`removesuffix`(3.9+) |
| 循环里 `s += x` | 慢 | `"".join(list)` |
| `isinstance(True, int)` | 实现意外的分支 | 先判 `bool` |
| `bool("False")` | 是 `True` | 显式解析 |
| 中文列对齐 | 表格歪掉 | 用 `wcwidth` 算显示宽度 |

---

## 1.9 本模块文件

| 文件 | 内容 |
|------|------|
| `demo.py` | 8 节可运行示例，覆盖 1.1~1.8 全部结论 |
| `exercises.py` | 8 道练习，含自动断言 |
| `solutions.py` | 参考答案 + 为什么这么写 |

### 强烈建议的学法

1. 先跑 `demo.py` 看输出，**先猜结果再看**，猜错的地方就是你的知识盲区
2. 打开 `demo_binding()`，在第 3 行左侧点一下打上断点，按 `F5` 启动调试
3. 在左侧「监视」面板里加入 `id(a)` 和 `id(b)`，看它们是否相同
4. 然后做 `exercises.py`

---

## 1.10 延伸阅读

- [Python 官方教程第 3~5 章](https://docs.python.org/zh-cn/3/tutorial/index.html)
- [PEP 8 代码风格指南](https://peps.python.org/pep-0008/) —— 模块 09 会细讲
- 《流畅的 Python》第 1 章、第 6 章 —— **本书是 Python 进阶的圣经，强烈建议入手**
- [Python 3.14 新特性](https://docs.python.org/3/whatsnew/3.14.html) —— 你机器上装的就是这个版本
