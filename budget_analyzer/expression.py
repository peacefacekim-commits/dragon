"""사용자가 쓴 수식을 안전하게 계산한다.

양식(템플릿)의 핵심. 사용자가 ``[집행액] / [예산액]`` 같은 식을 문자열로
적으면 여기서 해석해 계산한다. ``eval`` 을 쓰지 않고 ``ast`` 로 파싱한 뒤
허용한 노드만 직접 처리하므로, 수식에 무엇이 적혀도 파일·네트워크·임의
코드에 접근할 수 없다.

문법
----
컬럼 참조   ``[집행액]``            (대괄호 안은 엑셀 머리글 그대로)
사칙연산    ``+ - * / % **``
비교        ``== != < <= > >=``
논리        ``and or not`` 또는 ``& | !``
문자열      ``"정기"``
함수        아래 표 참고

계산은 열 단위로 이뤄진다. ``[집행액] / [예산액]`` 은 모든 행에 대해
한 번에 계산되고, ``합계([집행액])`` 처럼 하나의 값이 되는 함수는 필요한
자리에서 자동으로 모든 행에 퍼진다. 그래서 ``[집행액] / 합계([집행액])``
같은 식이 그대로 구성비가 된다.
"""

from __future__ import annotations

import ast
import re
import statistics
from dataclasses import dataclass
from typing import Any, Callable, Sequence

from .table import Table, to_number

__all__ = [
    "AGGREGATORS",
    "ExpressionError",
    "FUNCTION_HELP",
    "check",
    "evaluate",
    "evaluate_scalar",
    "truthy",
]


class ExpressionError(ValueError):
    """수식이 잘못됐을 때. 메시지는 사용자에게 그대로 보여줄 수 있다."""


@dataclass(frozen=True)
class _Scalar:
    """모든 행에 같은 값이 들어가는 결과. 필요할 때 열로 퍼진다."""

    value: Any


_COLUMN_REF = re.compile(r"\[([^\[\]]+)\]")
_PLACEHOLDER = "_컬럼참조_{}_"


# ── 값 도우미 ──────────────────────────────────────────────────────


def _number(value: Any) -> float | None:
    return to_number(value)


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def _text(value: Any) -> str:
    return "" if value is None else str(value)


def truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if value is True:
        return True
    number = to_number(value)
    if number is not None:
        return number != 0
    return bool(_text(value).strip())


# ── 함수 구현 ──────────────────────────────────────────────────────


def _numbers(values: Sequence[Any]) -> list[float]:
    return [n for n in (to_number(v) for v in values) if n is not None]


def _sum(values: Sequence[Any]) -> float:
    return sum(_numbers(values))


def _avg(values: Sequence[Any]) -> float | None:
    numbers = _numbers(values)
    return sum(numbers) / len(numbers) if numbers else None


def _median(values: Sequence[Any]) -> float | None:
    numbers = _numbers(values)
    return statistics.median(numbers) if numbers else None


def _count(values: Sequence[Any]) -> int:
    return sum(1 for v in values if not _is_blank(v))


def _distinct(values: Sequence[Any]) -> int:
    return len({_text(v).strip() for v in values if not _is_blank(v)})


def _max(values: Sequence[Any]) -> float | None:
    numbers = _numbers(values)
    return max(numbers) if numbers else None


def _min(values: Sequence[Any]) -> float | None:
    numbers = _numbers(values)
    return min(numbers) if numbers else None


def _cumulative(values: Sequence[Any]) -> list[float]:
    running, out = 0.0, []
    for value in values:
        running += to_number(value) or 0.0
        out.append(running)
    return out


def _share(values: Sequence[Any]) -> list[float | None]:
    total = _sum(values)
    if not total:
        return [None] * len(values)
    return [None if to_number(v) is None else to_number(v) / total for v in values]


def _cumulative_share(values: Sequence[Any]) -> list[float | None]:
    total = _sum(values)
    if not total:
        return [None] * len(values)
    return [running / total for running in _cumulative(values)]


def _growth(values: Sequence[Any]) -> list[float | None]:
    """직전 행 대비 증감률. 첫 행과 직전이 0 인 경우는 None."""
    out: list[float | None] = []
    previous: float | None = None
    for value in values:
        current = to_number(value)
        if previous is None or not previous or current is None:
            out.append(None)
        else:
            out.append((current - previous) / previous)
        previous = current
    return out


def _rank(values: Sequence[Any]) -> list[int | None]:
    """큰 값이 1위. 값이 없으면 None."""
    numbered = [(to_number(v), i) for i, v in enumerate(values)]
    ordered = sorted(
        (pair for pair in numbered if pair[0] is not None),
        key=lambda pair: pair[0],
        reverse=True,
    )
    out: list[int | None] = [None] * len(values)
    for position, (_, index) in enumerate(ordered, start=1):
        out[index] = position
    return out


# 이름 -> (구현, 종류). 종류: elementwise | aggregate | window
_FUNCTIONS: dict[str, tuple[Callable[..., Any], str]] = {
    # 행마다 계산
    "조건": (lambda c, a, b: a if truthy(c) else b, "elementwise"),
    "IF": (lambda c, a, b: a if truthy(c) else b, "elementwise"),
    "절대값": (lambda x: None if _number(x) is None else abs(_number(x)), "elementwise"),
    "ABS": (lambda x: None if _number(x) is None else abs(_number(x)), "elementwise"),
    "반올림": (
        lambda x, n=0: None if _number(x) is None else round(_number(x), int(_number(n) or 0)),
        "elementwise",
    ),
    "ROUND": (
        lambda x, n=0: None if _number(x) is None else round(_number(x), int(_number(n) or 0)),
        "elementwise",
    ),
    "포함": (lambda x, part: _text(part) in _text(x), "elementwise"),
    "CONTAINS": (lambda x, part: _text(part) in _text(x), "elementwise"),
    "비어있음": (_is_blank, "elementwise"),
    "숫자": (_number, "elementwise"),
    "문자": (_text, "elementwise"),
    # 열 전체 -> 값 하나
    "합계": (_sum, "aggregate"),
    "SUM": (_sum, "aggregate"),
    "평균": (_avg, "aggregate"),
    "AVG": (_avg, "aggregate"),
    "중앙값": (_median, "aggregate"),
    "MEDIAN": (_median, "aggregate"),
    "건수": (_count, "aggregate"),
    "COUNT": (_count, "aggregate"),
    "고유건수": (_distinct, "aggregate"),
    "DISTINCT": (_distinct, "aggregate"),
    "최대": (_max, "aggregate"),
    "MAX": (_max, "aggregate"),
    "최소": (_min, "aggregate"),
    "MIN": (_min, "aggregate"),
    # 열 전체 -> 열 전체
    "누적": (_cumulative, "window"),
    "CUMSUM": (_cumulative, "window"),
    "비율": (_share, "window"),
    "SHARE": (_share, "window"),
    "누적비율": (_cumulative_share, "window"),
    "CUMSHARE": (_cumulative_share, "window"),
    "증감률": (_growth, "window"),
    "GROWTH": (_growth, "window"),
    "순위": (_rank, "window"),
    "RANK": (_rank, "window"),
}

# 양식의 '측정값' 이 쓰는 집계 함수. 수식의 같은 이름 함수와 동작이 같다.
AGGREGATORS: dict[str, Callable[[Sequence[Any]], Any]] = {
    "합계": _sum,
    "평균": _avg,
    "건수": _count,
    "고유건수": _distinct,
    "최대": _max,
    "최소": _min,
    "중앙값": _median,
}

FUNCTION_HELP: list[tuple[str, str, str]] = [
    ("조건(조건식, 참값, 거짓값)", "행", '조건(([집행률] > 1), "초과", "정상")'),
    ("절대값(값)", "행", "절대값([잔액])"),
    ("반올림(값, 자릿수)", "행", "반올림([집행률], 3)"),
    ("포함(값, 문자)", "행", '포함([사업명], "지원")'),
    ("비어있음(값)", "행", "비어있음([부서])"),
    ("합계(열)", "전체", "합계([집행액])"),
    ("평균(열)", "전체", "평균([집행액])"),
    ("중앙값(열)", "전체", "중앙값([집행액])"),
    ("건수(열)", "전체", "건수([부서])"),
    ("고유건수(열)", "전체", "고유건수([부서])"),
    ("최대(열) / 최소(열)", "전체", "최대([집행액])"),
    ("누적(열)", "누적", "누적([집행액])"),
    ("비율(열)", "누적", "비율([집행액])"),
    ("누적비율(열)", "누적", "누적비율([집행액])"),
    ("증감률(열)", "누적", "증감률([집행액])"),
    ("순위(열)", "누적", "순위([집행액])"),
]


# ── 파서 ───────────────────────────────────────────────────────────


class _Evaluator:
    def __init__(self, columns: dict[str, list[Any]], length: int) -> None:
        self.columns = columns
        self.length = length

    # 값 표현: _Scalar 또는 길이 length 의 list.

    def _spread(self, value: Any) -> list[Any]:
        if isinstance(value, _Scalar):
            return [value.value] * self.length
        return value

    def _elementwise(self, function: Callable[..., Any], args: list[Any]) -> Any:
        if all(isinstance(a, _Scalar) for a in args):
            return _Scalar(function(*[a.value for a in args]))
        spread = [self._spread(a) for a in args]
        return [function(*values) for values in zip(*spread)]

    def evaluate(self, node: ast.AST) -> Any:
        method = getattr(self, "_on_" + type(node).__name__, None)
        if method is None:
            raise ExpressionError(f"수식에서 쓸 수 없는 표현입니다: {type(node).__name__}")
        return method(node)

    # -- 리터럴과 이름 --

    def _on_Expression(self, node: ast.Expression) -> Any:
        return self.evaluate(node.body)

    def _on_Constant(self, node: ast.Constant) -> Any:
        if isinstance(node.value, (int, float, str, bool)) or node.value is None:
            return _Scalar(node.value)
        raise ExpressionError(f"쓸 수 없는 값입니다: {node.value!r}")

    def _on_Name(self, node: ast.Name) -> Any:
        if node.id in self.columns:
            return list(self.columns[node.id])
        if node.id in ("참", "True"):
            return _Scalar(True)
        if node.id in ("거짓", "False"):
            return _Scalar(False)
        if node.id in ("없음", "None"):
            return _Scalar(None)
        raise ExpressionError(
            f"'{node.id}' 을(를) 알 수 없습니다. 컬럼은 [컬럼명] 처럼 대괄호로 감싸주세요."
        )

    # -- 연산 --

    _ARITHMETIC = {
        ast.Add: lambda a, b: a + b,
        ast.Sub: lambda a, b: a - b,
        ast.Mult: lambda a, b: a * b,
        ast.Div: lambda a, b: None if b == 0 else a / b,
        ast.FloorDiv: lambda a, b: None if b == 0 else a // b,
        ast.Mod: lambda a, b: None if b == 0 else a % b,
        ast.Pow: lambda a, b: a**b,
    }

    def _on_BinOp(self, node: ast.BinOp) -> Any:
        left, right = self.evaluate(node.left), self.evaluate(node.right)
        operator = type(node.op)

        # & 와 | 는 논리 연산으로 받아준다 (필터에서 쓰기 편하도록).
        if operator is ast.BitAnd:
            return self._elementwise(lambda a, b: truthy(a) and truthy(b), [left, right])
        if operator is ast.BitOr:
            return self._elementwise(lambda a, b: truthy(a) or truthy(b), [left, right])

        # 문자열끼리의 + 는 이어붙이기.
        if operator is ast.Add:
            def add(a: Any, b: Any) -> Any:
                if isinstance(a, str) or isinstance(b, str):
                    if to_number(a) is None or to_number(b) is None:
                        return _text(a) + _text(b)
                return self._arith(ast.Add, a, b)

            return self._elementwise(add, [left, right])

        if operator not in self._ARITHMETIC:
            raise ExpressionError(f"쓸 수 없는 연산자입니다: {operator.__name__}")
        return self._elementwise(lambda a, b: self._arith(operator, a, b), [left, right])

    def _arith(self, operator: type, a: Any, b: Any) -> Any:
        left, right = to_number(a), to_number(b)
        if left is None or right is None:
            return None
        try:
            return self._ARITHMETIC[operator](left, right)
        except (ZeroDivisionError, OverflowError, ValueError):
            return None

    def _on_UnaryOp(self, node: ast.UnaryOp) -> Any:
        operand = self.evaluate(node.operand)
        if isinstance(node.op, ast.USub):
            return self._elementwise(
                lambda x: None if to_number(x) is None else -to_number(x), [operand]
            )
        if isinstance(node.op, ast.UAdd):
            return operand
        if isinstance(node.op, (ast.Not, ast.Invert)):
            return self._elementwise(lambda x: not truthy(x), [operand])
        raise ExpressionError("쓸 수 없는 단항 연산자입니다.")

    def _on_BoolOp(self, node: ast.BoolOp) -> Any:
        values = [self.evaluate(v) for v in node.values]
        combine = all if isinstance(node.op, ast.And) else any
        return self._elementwise(lambda *args: combine(truthy(a) for a in args), values)

    _COMPARISONS = {
        ast.Eq: lambda a, b: a == b,
        ast.NotEq: lambda a, b: a != b,
        ast.Lt: lambda a, b: a < b,
        ast.LtE: lambda a, b: a <= b,
        ast.Gt: lambda a, b: a > b,
        ast.GtE: lambda a, b: a >= b,
    }

    def _on_Compare(self, node: ast.Compare) -> Any:
        values = [self.evaluate(node.left)] + [self.evaluate(c) for c in node.comparators]
        operators = node.ops

        def compare(*args: Any) -> bool:
            for index, operator in enumerate(operators):
                if not self._compare_pair(operator, args[index], args[index + 1]):
                    return False
            return True

        return self._elementwise(compare, values)

    def _compare_pair(self, operator: ast.cmpop, a: Any, b: Any) -> bool:
        if isinstance(operator, ast.In):
            return _text(a) in _text(b)
        if isinstance(operator, ast.NotIn):
            return _text(a) not in _text(b)

        function = self._COMPARISONS.get(type(operator))
        if function is None:
            raise ExpressionError("쓸 수 없는 비교 연산자입니다.")

        left, right = to_number(a), to_number(b)
        if left is None or right is None:
            # 한쪽이라도 숫자가 아니면 문자열로 비교한다.
            if isinstance(operator, (ast.Eq, ast.NotEq)):
                return function(_text(a).strip(), _text(b).strip())
            if _is_blank(a) or _is_blank(b):
                return False
            return function(_text(a), _text(b))
        return function(left, right)

    def _on_IfExp(self, node: ast.IfExp) -> Any:
        condition = self.evaluate(node.test)
        body, orelse = self.evaluate(node.body), self.evaluate(node.orelse)
        return self._elementwise(lambda c, a, b: a if truthy(c) else b, [condition, body, orelse])

    # -- 함수 --

    def _on_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise ExpressionError("함수 이름이 올바르지 않습니다.")
        name = node.func.id
        entry = _FUNCTIONS.get(name)
        if entry is None:
            raise ExpressionError(
                f"'{name}' 함수는 없습니다. 쓸 수 있는 함수: "
                + ", ".join(sorted({n.split("(")[0] for n, _, _ in FUNCTION_HELP}))
            )
        if node.keywords:
            raise ExpressionError("함수에 이름표(키워드) 인자는 쓸 수 없습니다.")

        function, kind = entry
        args = [self.evaluate(a) for a in node.args]

        try:
            if kind == "elementwise":
                return self._elementwise(function, args)
            if not args:
                raise ExpressionError(f"'{name}' 함수에는 인자가 하나 필요합니다.")
            series = self._spread(args[0])
            if kind == "aggregate":
                return _Scalar(function(series))
            return list(function(series))  # window
        except ExpressionError:
            raise
        except TypeError as error:
            raise ExpressionError(f"'{name}' 함수의 인자가 맞지 않습니다: {error}") from None


def _prepare(expression: str, available: Sequence[str]) -> tuple[str, dict[str, list[Any]], list[str]]:
    """``[컬럼]`` 을 파이썬 식별자로 바꾸고, 참조된 컬럼 목록을 돌려준다."""
    referenced: list[str] = []
    mapping: dict[str, str] = {}

    def replace(match: re.Match[str]) -> str:
        name = match.group(1).strip()
        if name not in mapping:
            mapping[name] = _PLACEHOLDER.format(len(mapping))
            referenced.append(name)
        return mapping[name]

    rewritten = _COLUMN_REF.sub(replace, expression)

    unknown = [name for name in referenced if name not in available]
    if unknown:
        raise ExpressionError(
            f"[{unknown[0]}] 컬럼이 없습니다. 사용 가능: {', '.join(available)}"
        )
    return rewritten, mapping, referenced


def evaluate(expression: str, table: Table, extra: dict[str, list[Any]] | None = None) -> list[Any]:
    """표의 모든 행에 대해 수식을 계산해 값 목록을 돌려준다."""
    if not expression or not expression.strip():
        raise ExpressionError("수식이 비어 있습니다.")

    available = list(table.columns) + list(extra or {})
    rewritten, mapping, _ = _prepare(expression, available)

    columns: dict[str, list[Any]] = {}
    for name, placeholder in mapping.items():
        if extra and name in extra:
            columns[placeholder] = list(extra[name])
        else:
            columns[placeholder] = table.column(name)

    try:
        tree = ast.parse(rewritten, mode="eval")
    except SyntaxError as error:
        raise ExpressionError(f"수식 문법이 잘못됐습니다: {error.msg}") from None

    evaluator = _Evaluator(columns, len(table))
    result = evaluator.evaluate(tree)
    return evaluator._spread(result)


def evaluate_scalar(
    expression: str, table: Table, extra: dict[str, list[Any]] | None = None
) -> Any:
    """값 하나를 기대하는 자리(요약 타일 등)에서 쓴다."""
    values = evaluate(expression, table, extra)
    if not values:
        return None
    first = values[0]
    if all(v == first for v in values):
        return first
    return _sum(values)  # 행마다 다르면 합계로 본다.


def check(expression: str, columns: Sequence[str]) -> str | None:
    """양식 편집기용 문법 검사. 문제가 없으면 None, 있으면 메시지."""
    if not expression or not expression.strip():
        return None
    try:
        rewritten, mapping, _ = _prepare(expression, columns)
        tree = ast.parse(rewritten, mode="eval")
    except ExpressionError as error:
        return str(error)
    except SyntaxError as error:
        return f"수식 문법이 잘못됐습니다: {error.msg}"

    # 빈 열에 한 번 돌려 함수 이름과 인자 개수까지 확인한다.
    try:
        _Evaluator({placeholder: [] for placeholder in mapping.values()}, 0).evaluate(tree)
    except ExpressionError as error:
        return str(error)
    except Exception as error:  # 예상 못 한 형태도 사용자에게 그대로 알려준다.
        return f"계산할 수 없는 수식입니다: {error}"
    return None
