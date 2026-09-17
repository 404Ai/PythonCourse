"""
项目 A · 表达式解释器 —— 参考实现

运行方式：
    python solution.py              进入交互式 REPL
    python solution.py "1 + 2 * 3"  直接算一个表达式
    python solution.py --test       跑自测

三个阶段：Lexer（词法）-> Parser（语法）-> Evaluator（求值）。
每一层只依赖上一层的数据结构，可以单独导入、单独测试：

    >>> from solution import Lexer, Parser, Evaluator, evaluate
    >>> [t.kind for t in Lexer("1+2").tokenize()]
    ['NUMBER', 'OP', 'NUMBER', 'EOF']
    >>> evaluate("1 + 2 * 3")
    7.0
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Any

# ======================================================================
# 一、异常
# ======================================================================
class CalcError(Exception):
    """所有解释器错误的基类。

    带上 pos 是为了能画出那个 `^` 指示符 —— 这是「好用的报错」
    和「能跑的代码」之间的区别。
    """

    kind = "错误"

    def __init__(self, message: str, pos: int) -> None:
        super().__init__(message)
        self.message = message
        self.pos = pos


class LexError(CalcError):
    kind = "词法错误"


class ParseError(CalcError):
    kind = "语法错误"


class EvalError(CalcError):
    kind = "求值错误"


def format_error(exc: CalcError, text: str) -> str:
    """把异常渲染成带列号和 ^ 指示符的三行文本。

    这个函数是纯函数（输入异常和原文，输出字符串），
    所以它可以被单独测试，不需要真的制造一个错误。
    """
    return (
        f"{exc.kind}：第 {exc.pos + 1} 列：{exc.message}\n"
        f"  {text}\n"
        f"  {' ' * exc.pos}^"
    )


# ======================================================================
# 二、词法分析
# ======================================================================
# Token 类型用字符串常量而不是 Enum：这里类型只有 7 种，
# 用字符串打印出来更直观，调试时一眼能看懂。
NUMBER = "NUMBER"
IDENT = "IDENT"
OP = "OP"
LPAREN = "LPAREN"
RPAREN = "RPAREN"
COMMA = "COMMA"
EOF = "EOF"

OPERATORS = "+-*/%^"


@dataclass
class Token:
    """一个词法单元。

    pos 是它在原字符串里的起始下标，错误定位全靠它。
    """

    kind: str
    value: str
    pos: int

    def __repr__(self) -> str:
        return f"Token({self.kind}, {self.value!r}, {self.pos})"


class Lexer:
    """把字符串切成 Token 列表。"""

    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    # -- 游标操作 ----------------------------------------------------
    def _peek(self, offset: int = 0) -> str:
        """看当前字符，但不移动游标。越界返回空字符串。"""
        index = self.pos + offset
        return self.text[index] if index < len(self.text) else ""

    def _advance(self) -> str:
        """吃掉当前字符并返回它。"""
        char = self._peek()
        self.pos += 1
        return char

    def _skip_spaces(self) -> None:
        while self._peek() and self._peek().isspace():
            self._advance()

    # -- 主循环 ------------------------------------------------------
    def tokenize(self) -> list[Token]:
        tokens: list[Token] = []
        while True:
            self._skip_spaces()
            if not self._peek():
                # 末尾一定要放一个 EOF 哨兵：
                # 语法分析器需要「向前看一个 Token」，
                # 有哨兵就不用到处判越界。
                tokens.append(Token(EOF, "", self.pos))
                return tokens
            tokens.append(self._next_token())

    def _next_token(self) -> Token:
        start = self.pos
        char = self._peek()

        if char.isdigit() or char == ".":
            return self._read_number()

        if char.isalpha() or char == "_":
            # 标识符：字母或下划线开头，后面跟字母数字下划线
            while self._peek() and (self._peek().isalnum() or self._peek() == "_"):
                self._advance()
            return Token(IDENT, self.text[start:self.pos], start)

        if char in OPERATORS:
            self._advance()
            return Token(OP, char, start)

        if char == "(":
            self._advance()
            return Token(LPAREN, char, start)
        if char == ")":
            self._advance()
            return Token(RPAREN, char, start)
        if char == ",":
            self._advance()
            return Token(COMMA, char, start)

        # 不认识的字符立刻报错。**不要跳过**——
        # 跳过去的话错误会跑到很远的地方才暴露，定位就失去意义了。
        raise LexError(f"无法识别的字符 {char!r}", start)

    def _read_number(self) -> Token:
        """读一个数字。

        要处理的形态：42 / 3.14 / .5 / 1. / 1e3 / 1.5e-3
        单独一个 '.' 不是合法数字。
        """
        start = self.pos
        digits_seen = 0

        while self._peek().isdigit():
            self._advance()
            digits_seen += 1

        if self._peek() == ".":
            self._advance()
            while self._peek().isdigit():
                self._advance()
                digits_seen += 1

        if digits_seen == 0:
            raise LexError("单独的小数点不是合法数字", start)

        # 科学计数法：e / E 后面可以跟正负号
        if self._peek() in ("e", "E"):
            save = self.pos
            self._advance()
            if self._peek() in ("+", "-"):
                self._advance()
            if not self._peek().isdigit():
                # 'e' 后面没跟数字 —— 回退，把它当成标识符的一部分。
                # 这样 '1e' 会报「语法错误」而不是「词法错误」，
                # 报错位置更贴近用户真正写错的地方。
                self.pos = save
            else:
                while self._peek().isdigit():
                    self._advance()

        return Token(NUMBER, self.text[start:self.pos], start)


# ======================================================================
# 三、AST 节点
# ======================================================================
# 用 dataclass 而不是元组：字段有名字，调试和报错时可读性好太多。
# 每个节点都带 pos，求值阶段报错时才有位置可用。
@dataclass
class Number:
    value: float
    pos: int


@dataclass
class Variable:
    name: str
    pos: int


@dataclass
class UnaryOp:
    op: str
    operand: Any
    pos: int


@dataclass
class BinOp:
    op: str
    left: Any
    right: Any
    pos: int


@dataclass
class Call:
    name: str
    args: list[Any]
    pos: int


# ======================================================================
# 四、语法分析
# ======================================================================
class Parser:
    """递归下降语法分析器。

    文法（从低优先级到高优先级）：

        expr    := term (('+' | '-') term)*
        term    := unary (('*' | '/' | '%') unary)*
        unary   := ('+' | '-') unary | power
        power   := primary ('^' unary)?
        primary := NUMBER
                 | IDENT '(' arglist? ')'
                 | IDENT
                 | '(' expr ')'
        arglist := expr (',' expr)*
    """

    def __init__(self, tokens: list[Token], text: str) -> None:
        self.tokens = tokens
        self.text = text      # 只为了在报错里能引用原文
        self.index = 0

    # -- Token 游标 --------------------------------------------------
    @property
    def current(self) -> Token:
        return self.tokens[self.index]

    def _advance(self) -> Token:
        token = self.current
        if token.kind != EOF:
            self.index += 1
        return token

    def _check(self, kind: str, value: str | None = None) -> bool:
        token = self.current
        return token.kind == kind and (value is None or token.value == value)

    def _match(self, kind: str, value: str | None = None) -> Token | None:
        """当前 Token 匹配就吃掉并返回它，否则返回 None。"""
        if self._check(kind, value):
            return self._advance()
        return None

    def _expect(self, kind: str, value: str | None = None, what: str = "") -> Token:
        token = self._match(kind, value)
        if token is None:
            expected = value or kind
            got = self.current.value or "表达式结束"
            raise ParseError(f"这里应该是 {expected}{what}，实际是 {got!r}", self.current.pos)
        return token

    # -- 文法规则 ----------------------------------------------------
    def parse(self) -> Any:
        node = self.expr()
        if self.current.kind != EOF:
            raise ParseError(f"多余的内容 {self.current.value!r}", self.current.pos)
        return node

    def expr(self) -> Any:
        """加减：左结合，用循环累积。"""
        node = self.term()
        while self._check(OP, "+") or self._check(OP, "-"):
            op = self._advance()
            right = self.term()
            node = BinOp(op.value, node, right, op.pos)
        return node

    def term(self) -> Any:
        """乘除模：优先级比加减高，所以被 expr 调用。"""
        node = self.unary()
        while (
            self._check(OP, "*") or self._check(OP, "/") or self._check(OP, "%")
        ):
            op = self._advance()
            right = self.unary()
            node = BinOp(op.value, node, right, op.pos)
        return node

    def unary(self) -> Any:
        """一元正负号。

        注意它在 power **上面**——这一层的位置决定了 `-2 ^ 2 == -4`：
        power 先算出 2^2=4，unary 再取负。
        """
        if self._check(OP, "-") or self._check(OP, "+"):
            op = self._advance()
            operand = self.unary()          # 递归，支持 --x
            return UnaryOp(op.value, operand, op.pos)
        return self.power()

    def power(self) -> Any:
        """幂运算：**右结合**。

        `2 ^ 3 ^ 2` 要解析成 `2 ^ (3 ^ 2)` 而不是 `(2 ^ 3) ^ 2`。
        实现上的区别就一个字：递归而不是循环。
        """
        base = self.primary()
        if self._check(OP, "^"):
            op = self._advance()
            exponent = self.unary()         # 递归 -> 右结合；并且允许 2 ^ -3
            return BinOp("^", base, exponent, op.pos)
        return base

    def primary(self) -> Any:
        """最基本的单元，也是递归的出口。"""
        token = self.current

        if token.kind == NUMBER:
            self._advance()
            return Number(float(token.value), token.pos)

        if token.kind == LPAREN:
            self._advance()
            node = self.expr()
            self._expect(RPAREN, what="（括号没闭合）")
            return node

        if token.kind == IDENT:
            self._advance()
            if self._check(LPAREN):
                self._advance()
                args: list[Any] = []
                if not self._check(RPAREN):
                    args.append(self.expr())
                    while self._match(COMMA):
                        args.append(self.expr())
                self._expect(RPAREN, what="（函数调用的括号没闭合）")
                return Call(token.value, args, token.pos)
            return Variable(token.value, token.pos)

        if token.kind == EOF:
            raise ParseError("表达式在这里意外结束了", token.pos)

        if token.kind == OP:
            raise ParseError(f"{token.value!r} 前面缺少操作数", token.pos)

        raise ParseError(f"这里不应该出现 {token.value!r}", token.pos)


# ======================================================================
# 五、求值
# ======================================================================
DEFAULT_FUNCTIONS: dict[str, Any] = {
    "sqrt": math.sqrt,
    "abs": abs,
    "min": min,
    "max": max,
    "round": round,
    "pow": math.pow,
    "floor": math.floor,
    "ceil": math.ceil,
    "trunc": math.trunc,
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "exp": math.exp,
    "log": math.log,
    "log10": math.log10,
}

# ⚠ 已知限制：`round(3.567, 1)` 会报「参数不对」。
#
#   原因不是 round 写错了，而是本解释器**只有一种数字类型：float**。
#   `round(x, ndigits)` 要求 ndigits 是 int，而我们传过去的是 3.567 之外的
#   另一个 float。`pow(2, 3)` 同理——math.pow 只吃两个参数且都当浮点算，
#   和 Python 内置的 `2 ** 3` 返回 int 不是一回事。
#
#   这是解释器设计里非常经典的一个坎：**要不要区分整数和浮点**。
#   真要解决，得给 AST 加一个 Int 节点、让词法分析器看有没有小数点来决定
#   类型，然后所有运算符都要处理「两个 int 的结果还是 int」这种提升规则。
#   工作量不小，但这就是 CPython 里 int/float 两套类型的由来。
#
#   本项目选择「全部按浮点算」换取简洁——大多数计算器场景够用。
#   想练手的话，加 int 类型是绝佳的进阶练习（见 README 第七节）。


class Evaluator:
    """在 AST 上递归求值。"""

    def __init__(
        self,
        env: dict[str, float] | None = None,
        functions: dict[str, Any] | None = None,
    ) -> None:
        self.env: dict[str, float] = dict(env or {})
        self.functions = dict(DEFAULT_FUNCTIONS)
        if functions:
            self.functions.update(functions)

    def eval(self, node: Any) -> float:
        # 用「类型 -> 处理函数」的字典分派，而不是一长串 isinstance。
        # 好处：加一种节点只在表里加一行，主流程一行都不用改。
        # （Python 3.10+ 也可以直接用 match 语句，效果类似。）
        handler = self._handlers.get(type(node))
        if handler is None:
            raise EvalError(f"不认识的节点类型：{type(node).__name__}", 0)
        return handler(self, node)

    # -- 每种节点一个处理函数 ---------------------------------------
    def _eval_number(self, node: Number) -> float:
        return node.value

    def _eval_variable(self, node: Variable) -> float:
        if node.name not in self.env:
            raise EvalError(f"未定义的变量：{node.name}", node.pos)
        return self.env[node.name]

    def _eval_unary(self, node: UnaryOp) -> float:
        value = self.eval(node.operand)
        return -value if node.op == "-" else value

    def _eval_binop(self, node: BinOp) -> float:
        left = self.eval(node.left)
        right = self.eval(node.right)

        if node.op == "+":
            return left + right
        if node.op == "-":
            return left - right
        if node.op == "*":
            return left * right
        if node.op == "/":
            if right == 0:
                # 把 ZeroDivisionError 换成我们自己的异常类型，
                # 顺便给它一个位置——原始异常是没有位置的。
                raise EvalError("除以零", node.pos)
            return left / right
        if node.op == "%":
            if right == 0:
                raise EvalError("对零取模", node.pos)
            return math.fmod(left, right)
        if node.op == "^":
            try:
                return float(left**right)
            except (OverflowError, ValueError) as exc:
                raise EvalError(f"幂运算失败：{exc}", node.pos) from exc

        raise EvalError(f"不支持的运算符：{node.op}", node.pos)

    def _eval_call(self, node: Call) -> float:
        if node.name not in self.functions:
            raise EvalError(f"未定义的函数：{node.name}", node.pos)

        # 参数先全部求值，再一次性传进去 —— min/max 支持任意个参数，
        # 所以这里必须用 *args 而不是写死两个参数。
        args = [self.eval(arg) for arg in node.args]
        try:
            return float(self.functions[node.name](*args))
        except TypeError as exc:
            raise EvalError(f"调用 {node.name} 的参数不对：{exc}", node.pos) from exc
        except ValueError as exc:
            # 比如 sqrt(-1)
            raise EvalError(f"{node.name} 的参数超出定义域：{exc}", node.pos) from exc

    _handlers = {
        Number: _eval_number,
        Variable: _eval_variable,
        UnaryOp: _eval_unary,
        BinOp: _eval_binop,
        Call: _eval_call,
    }


# ======================================================================
# 六、门面：把三个阶段串起来
# ======================================================================
def parse(text: str) -> Any:
    """字符串 -> AST。"""
    tokens = Lexer(text).tokenize()
    return Parser(tokens, text).parse()


def evaluate(text: str, env: dict[str, float] | None = None) -> float:
    """字符串 -> 数值。这是最常用的入口。"""
    return Evaluator(env).eval(parse(text))


# ======================================================================
# 七、REPL
# ======================================================================
HELP = """\
可用：
  1 + 2 * 3          直接算表达式
  sqrt(16) + abs(-3) 调用内置函数
  x = 5              定义变量
  :vars              查看所有变量
  :help / :quit
"""


def repl() -> None:
    """交互式命令行。

    REPL = Read-Eval-Print Loop，读-求值-打印循环。
    这里把变量环境放在循环外面，所以跨行定义的变量能保留下来。
    """
    print("表达式解释器（输入 :help 看帮助，:quit 退出）")
    env: dict[str, float] = {}

    while True:
        try:
            line = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if not line:
            continue
        if line in (":quit", ":q", "exit"):
            return
        if line in (":help", ":h"):
            print(HELP)
            continue
        if line == ":vars":
            if env:
                for name, value in env.items():
                    print(f"  {name} = {value}")
            else:
                print("  （还没有变量）")
            continue

        # 赋值：要区分 '=' 和 '=='。这里只有 '=' 才当赋值处理。
        if "=" in line and "==" not in line:
            name, _, rhs = line.partition("=")
            name = name.strip()
            if not name.isidentifier():
                print(f"  变量名不合法：{name!r}")
                continue
            try:
                env[name] = evaluate(rhs, env)
                print(f"  {name} = {env[name]}")
            except CalcError as exc:
                print(format_error(exc, rhs.strip()))
            continue

        try:
            print(f"  {evaluate(line, env)}")
        except CalcError as exc:
            print(format_error(exc, line))


# ======================================================================
# 八、自测
# ======================================================================
CASES: list[tuple[str, float]] = [
    ("1 + 2 * 3", 7),
    ("(1 + 2) * 3", 9),
    ("1 - 2 - 3", -4),
    ("2 ^ 3 ^ 2", 512),
    ("-2 ^ 2", -4),
    ("(-2) ^ 2", 4),
    ("2 ^ -1", 0.5),
    ("10 % 3", 1),
    ("2 * (3 + 4) - 5", 9),
    ("1.5 + .5", 2.0),
    ("1e3", 1000.0),
    ("--3", 3.0),
    ("+4", 4.0),
    ("sqrt(16) + abs(-3)", 7.0),
    ("max(1, 2 * 3, 4)", 6.0),
    ("min(3, 1, 2)", 1.0),
    ("round(3.567)", 4.0),          # 两个参数版本见上面 DEFAULT_FUNCTIONS 的说明
    ("1 + 1 + 1 + 1", 4),
]


def run_tests() -> int:
    failures = 0

    print("=" * 60)
    print("表达式求值")
    print("=" * 60)
    for text, expected in CASES:
        try:
            got = evaluate(text)
        except CalcError as exc:
            print(f"  [FAIL] {text:<24} 抛了异常：{exc.kind}：{exc.message}")
            failures += 1
            continue
        ok = math.isclose(got, expected, rel_tol=1e-9, abs_tol=1e-12)
        print(f"  [{'PASS' if ok else 'FAIL'}] {text:<24} = {got!r:<12} 期望 {expected!r}")
        if not ok:
            failures += 1

    print()
    print("=" * 60)
    print("变量与函数")
    print("=" * 60)
    env = {"x": 3.0, "y": 3.0}
    got = evaluate("x * (y + 1)", env)
    ok = got == 12.0
    print(f"  [{'PASS' if ok else 'FAIL'}] x * (y + 1)  (x=3, y=3) = {got!r} 期望 12.0")
    failures += 0 if ok else 1

    print()
    print("=" * 60)
    print("错误处理")
    print("=" * 60)

    error_cases: list[tuple[str, type[CalcError], str]] = [
        ("1 + * 2", ParseError, "'*' 前面缺少操作数"),
        ("(1 + 2", ParseError, "括号没闭合"),
        ("1 + ", ParseError, "意外结束"),
        ("foo(1)", EvalError, "未定义的函数"),
        ("y + 1", EvalError, "未定义的变量"),
        ("1 / 0", EvalError, "除以零"),
        ("1 $ 2", LexError, "无法识别的字符"),
        ("1 2", ParseError, "多余的内容"),
        ("sqrt(1, 2)", EvalError, "参数不对"),
    ]

    for text, exc_type, keyword in error_cases:
        try:
            evaluate(text)
        except exc_type as exc:
            ok = keyword in exc.message
            print(f"  [{'PASS' if ok else 'FAIL'}] {text:<14} -> {exc.kind}：{exc.message}")
            if not ok:
                failures += 1
        except CalcError as exc:
            print(f"  [FAIL] {text:<14} -> 异常类型不对，拿到 {type(exc).__name__}")
            failures += 1
        else:
            print(f"  [FAIL] {text:<14} -> 竟然没报错")
            failures += 1

    print()
    print("=" * 60)
    print("报错渲染")
    print("=" * 60)
    try:
        evaluate("1 + * 2")
    except CalcError as exc:
        rendered = format_error(exc, "1 + * 2")
        print(rendered)
        assert "^" in rendered and rendered.count("\n") == 2

    print()
    print("=" * 60)
    if failures:
        print(f"{failures} 项未通过")
    else:
        print("全部通过。")
    print("=" * 60)
    return 1 if failures else 0


# ======================================================================
def main(argv: list[str]) -> int:
    if not argv:
        repl()
        return 0
    if argv[0] == "--test":
        return run_tests()

    text = " ".join(argv)
    try:
        print(evaluate(text))
    except CalcError as exc:
        print(format_error(exc, text), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
