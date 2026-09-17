"""
项目 A · 表达式解释器 —— 骨架

要填的地方全部标了 TODO。运行方式：

    python starter.py --test     看进度（未实现的部分会显示 SKIP）
    python starter.py "1+2*3"    算一个表达式
    python starter.py            进入 REPL

**建议按 TODO 的编号顺序做**，每一步都能独立验证。
详细提示见同目录的 README.md，参考答案见 solution.py。

不要跳着做。这个项目的三个阶段是强耦合的：
词法不对，语法分析拿不到正确的 Token 流，你会以为是自己语法写错了，
白白浪费几个小时。
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from typing import Any

# ======================================================================
# 一、异常 —— 已给好，不用改
# ======================================================================
class CalcError(Exception):
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
    """渲染成带 ^ 指示符的报错。已给好。"""
    return (
        f"{exc.kind}：第 {exc.pos + 1} 列：{exc.message}\n"
        f"  {text}\n"
        f"  {' ' * exc.pos}^"
    )


# ======================================================================
# 二、词法分析
# ======================================================================
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
    kind: str
    value: str
    pos: int


class Lexer:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0

    def _peek(self, offset: int = 0) -> str:
        """看当前字符但不移动游标。越界返回空字符串。"""
        index = self.pos + offset
        return self.text[index] if index < len(self.text) else ""

    def _advance(self) -> str:
        char = self._peek()
        self.pos += 1
        return char

    def _skip_spaces(self) -> None:
        while self._peek() and self._peek().isspace():
            self._advance()

    def tokenize(self) -> list[Token]:
        """TODO 1：把 self.text 切成 Token 列表。

        流程：
            循环 {
                跳过空白
                如果到结尾：追加一个 Token(EOF, "", self.pos) 然后返回
                否则追加 self._next_token() 的结果
            }

        ▸ 末尾那个 EOF 哨兵不能省。语法分析器需要「向前看一个 Token」，
          没有哨兵就得到处判越界。
        """
        raise NotImplementedError("TODO 1: Lexer.tokenize")

    def _next_token(self) -> Token:
        """TODO 2：识别**一个** Token。

        按这个顺序判断当前字符：
            - 是数字或 '.'        -> self._read_number()
            - 是字母或 '_'        -> 一直吃字母数字下划线，返回 Token(IDENT, ...)
            - 在 OPERATORS 里     -> 返回 Token(OP, char, start)
            - '(' / ')' / ','     -> 返回对应的 LPAREN / RPAREN / COMMA
            - 其他                -> raise LexError(f"无法识别的字符 {char!r}", start)

        ▸ 每个分支都要记住 start（进入函数时的 self.pos），
          它是错误定位和取原文的依据。
        ▸ 不认识的字符要**立刻**报错，不要跳过。
        """
        raise NotImplementedError("TODO 2: Lexer._next_token")

    def _read_number(self) -> Token:
        """TODO 3：读一个数字。

        要支持的形态：42 / 3.14 / .5 / 1. / 1e3 / 1.5e-3
        单独一个 '.' 要抛 LexError。

        推荐做法：
            1. 一直吃数字，统计吃到了几位（digits_seen）
            2. 如果当前是 '.'，吃掉，再一直吃数字（同样累加 digits_seen）
            3. 如果 digits_seen == 0，说明只有一个小数点 -> 抛 LexError
            4. 处理科学计数法：当前是 'e'/'E' 时试探一下，
               后面跟可选正负号再跟数字才算数；如果不是，要**回退**，
               让 'e' 留给标识符处理
            5. 用 self.text[start:self.pos] 当 value 返回
        """
        raise NotImplementedError("TODO 3: Lexer._read_number")


# ======================================================================
# 三、AST 节点 —— 已给好，不用改
# ======================================================================
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
    """文法（优先级从低到高）：

        expr    := term (('+' | '-') term)*
        term    := unary (('*' | '/' | '%') unary)*
        unary   := ('+' | '-') unary | power
        power   := primary ('^' unary)?
        primary := NUMBER | IDENT '(' arglist? ')' | IDENT | '(' expr ')'
    """

    def __init__(self, tokens: list[Token], text: str) -> None:
        self.tokens = tokens
        self.text = text
        self.index = 0

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

    def parse(self) -> Any:
        """TODO 4：解析入口。

            1. node = self.expr()
            2. 如果当前不是 EOF，说明有多余内容 ->
               raise ParseError(f"多余的内容 {self.current.value!r}", self.current.pos)
            3. 返回 node
        """
        raise NotImplementedError("TODO 4: Parser.parse")

    def expr(self) -> Any:
        """TODO 5：加减，**左结合**。

            先 node = self.term()
            然后 while 当前是 '+' 或 '-':
                吃掉运算符
                right = self.term()
                node = BinOp(运算符文本, node, right, 运算符的 pos)
            返回 node

        ▸ 「左结合」体现在这里：每轮把**已经算出的结果**当左子树，
          所以 1 - 2 - 3 自然变成 (1-2)-3。换成递归就成右结合了。
        """
        raise NotImplementedError("TODO 5: Parser.expr")

    def term(self) -> Any:
        """TODO 6：乘除模，左结合。结构和 expr 一样，只是运算符换成 * / %，
        并且调用的下一层是 self.unary()。

        ▸ 优先级就是靠「谁调用谁」体现的：expr 调 term 调 unary。
          越靠下的规则结合得越紧。
        """
        raise NotImplementedError("TODO 6: Parser.term")

    def unary(self) -> Any:
        """TODO 7：一元正负号。

            如果当前是 '-' 或 '+':
                吃掉运算符
                operand = self.unary()      # 递归，这样 --3 也能解析
                return UnaryOp(运算符, operand, 运算符的 pos)
            否则:
                return self.power()

        ▸ 这一层放在 power **上面**，是 -2^2 == -4 的原因。
          先算 2^2=4，再取负。
        """
        raise NotImplementedError("TODO 7: Parser.unary")

    def power(self) -> Any:
        """TODO 8：幂运算，**右结合**。

            base = self.primary()
            如果当前是 '^':
                吃掉
                exponent = self.unary()     # 递归！不是循环
                return BinOp("^", base, exponent, pos)
            返回 base

        ▸ 这里是全项目最需要想清楚的一处。用循环会得到左结合
          （2^3^2 = 64），用递归才是右结合（2^3^2 = 512）。
          自己先在纸上推一遍两种写法的结果。
        ▸ 指数位置调 self.unary() 而不是 self.primary()，
          这样 2 ^ -3 也能解析。
        """
        raise NotImplementedError("TODO 8: Parser.power")

    def primary(self) -> Any:
        """TODO 9：最基本的单元，递归的出口。

            NUMBER  -> 吃掉，返回 Number(float(value), pos)
            LPAREN  -> 吃掉，node = self.expr()，
                       self._expect(RPAREN, what="（括号没闭合）")，返回 node
            IDENT   -> 吃掉；如果紧跟 LPAREN 就是函数调用：
                          吃掉 '('
                          如果当前不是 ')'：
                              先 self.expr() 收第一个参数
                              while self._match(COMMA): 再收一个
                          self._expect(RPAREN, what="（函数调用的括号没闭合）")
                          返回 Call(名字, 参数列表, 名字的 pos)
                       否则返回 Variable(名字, pos)
            EOF     -> raise ParseError("表达式在这里意外结束了", pos)
            OP      -> raise ParseError(f"{value!r} 前面缺少操作数", pos)
            其他    -> raise ParseError(f"这里不应该出现 {value!r}", pos)

        ▸ 最后那两条错误分支别偷懒不写。它们正是
          "1 + * 2" 能报出「'*' 前面缺少操作数」的原因。
        """
        raise NotImplementedError("TODO 9: Parser.primary")


# ======================================================================
# 五、求值
# ======================================================================
def _default_functions() -> dict[str, Any]:
    return {
        "sqrt": math.sqrt,
        "abs": abs,
        "min": min,
        "max": max,
        "round": round,
        "pow": math.pow,
        "floor": math.floor,
        "ceil": math.ceil,
        "sin": math.sin,
        "cos": math.cos,
        "log": math.log,
        "log10": math.log10,
        "exp": math.exp,
    }


class Evaluator:
    def __init__(
        self,
        env: dict[str, float] | None = None,
        functions: dict[str, Any] | None = None,
    ) -> None:
        self.env: dict[str, float] = dict(env or {})
        self.functions = _default_functions()
        if functions:
            self.functions.update(functions)

    def eval(self, node: Any) -> float:
        """TODO 10：根据节点类型分派。已给出骨架，你只需要补全下面的
        各个 _eval_xxx 方法。

        ▸ 用 isinstance 链或者「类型 -> 函数」字典都行。
          字典分派的好处是加节点类型时主流程不用改。
        """
        if isinstance(node, Number):
            return self._eval_number(node)
        if isinstance(node, Variable):
            return self._eval_variable(node)
        if isinstance(node, UnaryOp):
            return self._eval_unary(node)
        if isinstance(node, BinOp):
            return self._eval_binop(node)
        if isinstance(node, Call):
            return self._eval_call(node)
        raise EvalError(f"不认识的节点类型：{type(node).__name__}", 0)

    def _eval_number(self, node: Number) -> float:
        return node.value

    def _eval_variable(self, node: Variable) -> float:
        """TODO 11：查 self.env。

        不在环境里就 raise EvalError(f"未定义的变量：{node.name}", node.pos)
        """
        raise NotImplementedError("TODO 11: Evaluator._eval_variable")

    def _eval_unary(self, node: UnaryOp) -> float:
        """TODO 12：先 self.eval(node.operand)，
        '-' 就取负，否则原样返回。
        """
        raise NotImplementedError("TODO 12: Evaluator._eval_unary")

    def _eval_binop(self, node: BinOp) -> float:
        """TODO 13：先算出 left 和 right，再按 node.op 分派。

            +  -  *   直接算
            /          右操作数是 0 时 raise EvalError("除以零", node.pos)
            %          同样要防零，用 math.fmod
            ^          用 left ** right；可能抛 OverflowError / ValueError，
                       记得 raise ... from exc 包装成 EvalError
            其他       raise EvalError(f"不支持的运算符：{node.op}", node.pos)

        ▸ 除零一定要自己检查并换成 EvalError。直接让它抛
          ZeroDivisionError 的话，调用方就没法统一处理了，
          而且那个异常没有位置信息，报错画不出 ^。
        """
        raise NotImplementedError("TODO 13: Evaluator._eval_binop")

    def _eval_call(self, node: Call) -> float:
        """TODO 14：函数调用。

            1. node.name 不在 self.functions 里 ->
               raise EvalError(f"未定义的函数：{node.name}", node.pos)
            2. args = [self.eval(a) for a in node.args]
               （参数先全部求值，再用 *args 一次性传进去）
            3. 调用它，把结果 float() 一下返回
            4. 用 try/except 包住 TypeError 和 ValueError，
               包装成 EvalError 并带上 node.pos

        ▸ 必须用 *args。min / max 支持任意个参数，
          写死 fn(args[0], args[1]) 就废了。
        ▸ 第 4 步很重要：sqrt(-1) 抛的是 ValueError，
          直接漏出去调用方会一脸茫然。
        """
        raise NotImplementedError("TODO 14: Evaluator._eval_call")


# ======================================================================
# 六、门面 —— 已给好
# ======================================================================
def parse(text: str) -> Any:
    tokens = Lexer(text).tokenize()
    return Parser(tokens, text).parse()


def evaluate(text: str, env: dict[str, float] | None = None) -> float:
    return Evaluator(env).eval(parse(text))


# ======================================================================
# 七、自测
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
    ("sqrt(16) + abs(-3)", 7.0),
    ("max(1, 2 * 3, 4)", 6.0),
    ("min(3, 1, 2)", 1.0),
    ("round(3.567)", 4.0),
]

ERROR_CASES: list[tuple[str, type[CalcError], str]] = [
    ("1 + * 2", ParseError, "'*' 前面缺少操作数"),
    ("(1 + 2", ParseError, "括号没闭合"),
    ("1 + ", ParseError, "意外结束"),
    ("foo(1)", EvalError, "未定义的函数"),
    ("y + 1", EvalError, "未定义的变量"),
    ("1 / 0", EvalError, "除以零"),
    ("1 $ 2", LexError, "无法识别的字符"),
    ("1 2", ParseError, "多余的内容"),
]


def run_tests() -> int:
    failures = 0
    skipped = 0

    def report(label: str, fn) -> None:
        nonlocal failures, skipped
        try:
            fn()
        except NotImplementedError as exc:
            print(f"  [SKIP] {label:<26} {exc}")
            skipped += 1
        except AssertionError as exc:
            print(f"  [FAIL] {label:<26} {exc}")
            failures += 1
        except Exception as exc:  # noqa: BLE001 - 自测运行器要兜住一切
            print(f"  [ERROR] {label:<26} {type(exc).__name__}: {exc}")
            failures += 1
        else:
            print(f"  [PASS] {label}")

    print("=" * 66)
    print("表达式求值")
    print("=" * 66)
    for text, expected in CASES:
        def check(text=text, expected=expected) -> None:
            got = evaluate(text)
            assert math.isclose(got, expected, rel_tol=1e-9, abs_tol=1e-12), (
                f"{text} = {got!r}，期望 {expected!r}"
            )

        report(text, check)

    print()
    print("=" * 66)
    print("变量")
    print("=" * 66)

    def check_vars() -> None:
        got = evaluate("x * (y + 1)", {"x": 3.0, "y": 3.0})
        assert got == 12.0, f"得到 {got!r}"

    report("x * (y + 1)", check_vars)

    print()
    print("=" * 66)
    print("错误处理")
    print("=" * 66)
    for text, exc_type, keyword in ERROR_CASES:
        def check(text=text, exc_type=exc_type, keyword=keyword) -> None:
            try:
                evaluate(text)
            except exc_type as exc:
                assert keyword in exc.message, f"报错信息里没有 {keyword!r}：{exc.message}"
            else:
                raise AssertionError(f"{text} 竟然没报错")

        report(text, check)

    print()
    print("=" * 66)
    total = len(CASES) + 1 + len(ERROR_CASES)
    print(f"合计 {total} 项   通过 {total - failures - skipped}   失败 {failures}   未做 {skipped}")
    if failures:
        print("还有失败项，先看上面带 FAIL / ERROR 的行。")
    elif skipped:
        print("通过的都对了，继续做剩下的 TODO。")
    else:
        print("全部通过。对照 solution.py 看看它是怎么组织代码的。")
    print("=" * 66)
    return 1 if failures else 0


# ======================================================================
def repl() -> None:
    print("表达式解释器（骨架版，未实现的会抛 NotImplementedError）")
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
        if "=" in line and "==" not in line:
            name, _, rhs = line.partition("=")
            try:
                env[name.strip()] = evaluate(rhs, env)
                print(f"  {name.strip()} = {env[name.strip()]}")
            except CalcError as exc:
                print(format_error(exc, rhs.strip()))
            except NotImplementedError as exc:
                print(f"  还没做：{exc}")
            continue
        try:
            print(f"  {evaluate(line, env)}")
        except CalcError as exc:
            print(format_error(exc, line))
        except NotImplementedError as exc:
            print(f"  还没做：{exc}")


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
    except NotImplementedError as exc:
        print(f"还没实现：{exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
