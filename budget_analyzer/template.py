"""분석 양식(템플릿).

"무엇을 어떻게 분석할지" 를 코드가 아니라 데이터로 적어 둔 것. JSON 파일
하나가 곧 하나의 분석 양식이고, 프로그램은 그 양식을 실행만 한다. 새로운
분석이 필요하면 코드를 고치는 대신 양식을 만들거나 고치면 된다.

양식의 구조
-----------
::

    양식
    ├─ 시트 / 머리글행        어떤 시트의 몇 행부터 읽을지
    ├─ 전체필터              분석에서 제외할 행 (수식)
    ├─ 파생컬럼[]            원본 행 단위로 새로 만드는 컬럼 (수식)
    ├─ 요약[]                맨 위 숫자 타일 (수식)
    └─ 블록[]                본문 섹션 하나하나
       ├─ 유형              집계 | 추이 | 목록
       ├─ 필터              이 블록에만 적용할 조건
       ├─ 기준[]            묶는 기준 컬럼 (집계) / 날짜 컬럼 (추이)
       ├─ 측정값[]          합계·평균·건수 … 를 낼 컬럼
       ├─ 계산[]            집계 결과 위에서 다시 계산할 컬럼 (수식)
       ├─ 정렬 / 상위 / 차트
       └─ 규칙[]            조건에 걸리면 경고를 띄우는 규칙 (수식)
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from .mapping import ColumnMapping

__all__ = [
    "Template",
    "Block",
    "Measure",
    "Computed",
    "Summary",
    "Rule",
    "TemplateError",
    "load_template",
    "save_template",
    "builtin_templates",
    "template_from_mapping",
    "AGGREGATIONS",
    "FORMATS",
]


class TemplateError(ValueError):
    """양식이 잘못됐을 때."""


AGGREGATIONS = ("합계", "평균", "건수", "고유건수", "최대", "최소", "중앙값")
FORMATS = ("자동", "금액", "비율", "정수", "소수", "문자", "상태")
BLOCK_KINDS = ("집계", "추이", "목록")
CHART_KINDS = ("자동", "막대", "선", "없음")
GRAINS = ("월", "분기", "연도")


def _clean(value: Any) -> Any:
    """dataclass -> JSON 으로 내보내기 전에 빈 값을 걷어낸다."""
    if isinstance(value, dict):
        return {k: _clean(v) for k, v in value.items() if v not in ("", [], None)}
    if isinstance(value, list):
        return [_clean(v) for v in value]
    return value


@dataclass
class Measure:
    """집계할 값 하나. ``합계(집행액)`` 처럼 읽는다."""

    컬럼: str
    함수: str = "합계"
    이름: str = ""
    서식: str = "자동"

    @property
    def 결과이름(self) -> str:
        if self.이름:
            return self.이름
        return self.컬럼 if self.함수 == "합계" else f"{self.컬럼} {self.함수}"


@dataclass
class Computed:
    """수식으로 만드는 컬럼."""

    이름: str
    식: str
    서식: str = "자동"


@dataclass
class Summary:
    """보고서 맨 위에 큰 숫자로 뜨는 타일."""

    이름: str
    식: str
    서식: str = "자동"
    설명: str = ""


@dataclass
class Rule:
    """조건에 걸린 행이 있으면 경고 문구를 만든다.

    메시지에 ``{건수}`` 와 ``{항목}`` 을 쓰면 각각 걸린 행 수와 첫 항목
    이름으로 바뀐다.
    """

    조건: str
    메시지: str
    수준: str = "경고"


@dataclass
class Block:
    """보고서 본문의 한 섹션."""

    이름: str
    유형: str = "집계"
    설명: str = ""
    필터: str = ""
    기준: list[str] = field(default_factory=list)
    단위: str = "월"
    측정값: list[Measure] = field(default_factory=list)
    계산: list[Computed] = field(default_factory=list)
    정렬: str = ""
    내림차순: bool = True
    상위: int = 0
    기타로묶기: bool = True
    차트: str = "자동"
    차트값: str = ""
    규칙: list[Rule] = field(default_factory=list)


@dataclass
class Template:
    """분석 양식 하나."""

    이름: str = "새 양식"
    설명: str = ""
    시트: str = ""
    머리글행: int = 0  # 0 = 자동
    전체필터: str = ""
    파생컬럼: list[Computed] = field(default_factory=list)
    요약: list[Summary] = field(default_factory=list)
    블록: list[Block] = field(default_factory=list)

    # ── 직렬화 ──────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        return _clean(asdict(self))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Template":
        if not isinstance(data, dict):
            raise TemplateError("양식 파일의 최상위는 객체(JSON object)여야 합니다.")

        def build(kind: type, items: Any, where: str) -> list[Any]:
            if items is None:
                return []
            if not isinstance(items, list):
                raise TemplateError(f"'{where}' 는 목록이어야 합니다.")
            known = set(kind.__dataclass_fields__)
            out = []
            for item in items:
                if not isinstance(item, dict):
                    raise TemplateError(f"'{where}' 의 항목은 객체여야 합니다.")
                out.append(kind(**{k: v for k, v in item.items() if k in known}))
            return out

        blocks: list[Block] = []
        for raw in data.get("블록") or []:
            if not isinstance(raw, dict):
                raise TemplateError("'블록' 의 항목은 객체여야 합니다.")
            known = set(Block.__dataclass_fields__)
            fields = {k: v for k, v in raw.items() if k in known}
            fields["측정값"] = build(Measure, raw.get("측정값"), "측정값")
            fields["계산"] = build(Computed, raw.get("계산"), "계산")
            fields["규칙"] = build(Rule, raw.get("규칙"), "규칙")
            if "이름" not in fields:
                raise TemplateError("모든 블록에는 '이름' 이 필요합니다.")
            blocks.append(Block(**fields))

        known = set(cls.__dataclass_fields__)
        fields = {k: v for k, v in data.items() if k in known}
        fields["파생컬럼"] = build(Computed, data.get("파생컬럼"), "파생컬럼")
        fields["요약"] = build(Summary, data.get("요약"), "요약")
        fields["블록"] = blocks
        return cls(**fields)

    # ── 검증 ────────────────────────────────────────────────────

    def validate(self, columns: list[str] | None = None) -> list[str]:
        """양식 자체의 문제를 목록으로 돌려준다. 비어 있으면 정상.

        ``columns`` 를 주면 실제 엑셀 컬럼과 맞는지까지 확인한다.
        """
        from . import expression  # 순환 참조를 피하려고 여기서 불러온다.

        problems: list[str] = []
        available = list(columns) if columns else None

        def check_expression(text: str, where: str, extra: list[str] | None = None) -> None:
            if not text or available is None:
                return
            message = expression.check(text, available + (extra or []))
            if message:
                problems.append(f"{where}: {message}")

        if not self.블록:
            problems.append("블록이 하나도 없습니다. 분석할 내용을 추가하세요.")

        check_expression(self.전체필터, "전체필터")

        derived = [c.이름 for c in self.파생컬럼]
        for computed in self.파생컬럼:
            if not computed.이름:
                problems.append("파생컬럼에 이름이 없습니다.")
            check_expression(computed.식, f"파생컬럼 '{computed.이름}'", derived)

        for summary in self.요약:
            check_expression(summary.식, f"요약 '{summary.이름}'", derived)

        seen: set[str] = set()
        for block in self.블록:
            where = f"블록 '{block.이름}'"
            if block.이름 in seen:
                problems.append(f"{where}: 이름이 중복됩니다.")
            seen.add(block.이름)

            if block.유형 not in BLOCK_KINDS:
                problems.append(f"{where}: 유형은 {', '.join(BLOCK_KINDS)} 중 하나여야 합니다.")
            if block.차트 not in CHART_KINDS:
                problems.append(f"{where}: 차트는 {', '.join(CHART_KINDS)} 중 하나여야 합니다.")

            if block.유형 == "추이":
                if not block.기준:
                    problems.append(f"{where}: 추이 블록에는 날짜/기간 컬럼이 필요합니다.")
                if block.단위 not in GRAINS:
                    problems.append(f"{where}: 단위는 {', '.join(GRAINS)} 중 하나여야 합니다.")
            elif block.유형 == "집계" and not block.기준:
                problems.append(f"{where}: 묶을 기준 컬럼이 필요합니다.")

            if available is not None:
                for column in block.기준:
                    if column not in available and column not in derived:
                        problems.append(f"{where}: '{column}' 컬럼이 파일에 없습니다.")

            if block.유형 != "목록" and not block.측정값:
                problems.append(f"{where}: 집계할 측정값이 하나 이상 필요합니다.")

            for measure in block.측정값:
                if measure.함수 not in AGGREGATIONS:
                    problems.append(
                        f"{where}: '{measure.함수}' 는 없는 집계 함수입니다. "
                        f"({', '.join(AGGREGATIONS)})"
                    )
                if available is not None and measure.컬럼 not in available + derived:
                    problems.append(f"{where}: '{measure.컬럼}' 컬럼이 파일에 없습니다.")

            check_expression(block.필터, f"{where} 필터", derived)

            # 계산·규칙은 집계가 끝난 표 위에서 돌아가므로 결과 컬럼을 기준으로 본다.
            result_columns = list(block.기준) + [m.결과이름 for m in block.측정값] + ["건수"]
            for computed in block.계산:
                if not computed.이름:
                    problems.append(f"{where}: 계산 컬럼에 이름이 없습니다.")
                message = expression.check(computed.식, result_columns)
                if message:
                    problems.append(f"{where} 계산 '{computed.이름}': {message}")
                result_columns.append(computed.이름)

            for rule in block.규칙:
                message = expression.check(rule.조건, result_columns)
                if message:
                    problems.append(f"{where} 규칙: {message}")

        return problems


# ── 저장 / 불러오기 ────────────────────────────────────────────────


def save_template(path: str, template: Template) -> str:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(template.to_json())
    return path


def load_template(path: str) -> Template:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as error:
        raise TemplateError(f"양식 파일을 읽을 수 없습니다 ({path}): {error}") from None
    return Template.from_dict(data)


# ── 기본 제공 양식 ─────────────────────────────────────────────────


def _standard_template(mapping: ColumnMapping) -> Template:
    """예산액·집행액이 모두 있을 때의 표준 3종 분석."""
    category = mapping.category or "항목"
    budget, actual = mapping.budget or "예산액", mapping.actual or "집행액"

    blocks = [
        Block(
            이름="항목별 집계 · 구성비",
            설명=f"{category} 기준 {actual} 합계와 전체 대비 비중",
            기준=[category],
            측정값=[Measure(컬럼=actual, 함수="합계", 서식="금액")],
            계산=[
                Computed(이름="구성비", 식=f"비율([{actual}])", 서식="비율"),
                Computed(이름="누적구성비", 식=f"누적비율([{actual}])", 서식="비율"),
            ],
            정렬=actual,
            상위=15,
            차트="막대",
        ),
        Block(
            이름="예산 대비 집행률",
            설명="예산액·집행액·잔액과 집행률 판정",
            기준=[category],
            측정값=[
                Measure(컬럼=budget, 함수="합계", 서식="금액"),
                Measure(컬럼=actual, 함수="합계", 서식="금액"),
            ],
            계산=[
                Computed(이름="잔액", 식=f"[{budget}] - [{actual}]", 서식="금액"),
                Computed(이름="집행률", 식=f"[{actual}] / [{budget}]", 서식="비율"),
                Computed(
                    이름="상태",
                    식=(
                        '조건(비어있음([집행률]), "예산없음", '
                        '조건([집행률] > 1, "초과", '
                        '조건([집행률] < 0.7, "부진", "정상")))'
                    ),
                    서식="상태",
                ),
            ],
            정렬=budget,
            상위=15,
            차트="막대",
            차트값="집행률",
            규칙=[
                Rule(조건='[상태] == "초과"', 메시지="예산을 초과한 항목이 {건수}개 있습니다. (예: {항목})"),
                Rule(조건='[상태] == "부진"', 메시지="집행률 70% 미만인 부진 항목이 {건수}개 있습니다."),
                Rule(조건='[상태] == "예산없음"', 메시지="예산 없이 집행만 있는 항목이 {건수}개 있습니다."),
            ],
        ),
    ]

    if mapping.date:
        blocks.append(
            Block(
                이름="기간별 추이",
                유형="추이",
                설명="기간 순 집행액과 누적, 직전 기간 대비 증감률",
                기준=[mapping.date],
                단위="월",
                측정값=[Measure(컬럼=actual, 함수="합계", 서식="금액")],
                계산=[
                    Computed(이름=f"누적{actual}", 식=f"누적([{actual}])", 서식="금액"),
                    Computed(이름="전기대비", 식=f"증감률([{actual}])", 서식="비율"),
                ],
                차트="선",
            )
        )

    return Template(
        이름="표준 예산분석",
        설명="항목별 집계·구성비, 예산 대비 집행률, 기간별 추이 3종",
        요약=[
            Summary(이름="총 예산액", 식=f"합계([{budget}])", 서식="금액", 설명="원"),
            Summary(이름="총 집행액", 식=f"합계([{actual}])", 서식="금액", 설명="원"),
            Summary(
                이름="잔액",
                식=f"합계([{budget}]) - 합계([{actual}])",
                서식="금액",
                설명="원",
            ),
            Summary(
                이름="전체 집행률",
                식=f"합계([{actual}]) / 합계([{budget}])",
                서식="비율",
                설명="예산 대비 집행액",
            ),
        ],
        블록=blocks,
    )


def _simple_template(mapping: ColumnMapping) -> Template:
    """금액 컬럼 하나만 있을 때의 기본 분석."""
    category = mapping.category or "항목"
    amount = mapping.value_column or "금액"

    blocks = [
        Block(
            이름="항목별 집계 · 구성비",
            설명=f"{category} 기준 {amount} 합계와 전체 대비 비중",
            기준=[category],
            측정값=[Measure(컬럼=amount, 함수="합계", 서식="금액")],
            계산=[
                Computed(이름="구성비", 식=f"비율([{amount}])", 서식="비율"),
                Computed(이름="누적구성비", 식=f"누적비율([{amount}])", 서식="비율"),
            ],
            정렬=amount,
            상위=15,
            차트="막대",
        )
    ]
    if mapping.date:
        blocks.append(
            Block(
                이름="기간별 추이",
                유형="추이",
                기준=[mapping.date],
                단위="월",
                측정값=[Measure(컬럼=amount, 함수="합계", 서식="금액")],
                계산=[
                    Computed(이름=f"누적{amount}", 식=f"누적([{amount}])", 서식="금액"),
                    Computed(이름="전기대비", 식=f"증감률([{amount}])", 서식="비율"),
                ],
                차트="선",
            )
        )

    return Template(
        이름="단순 집계",
        설명="금액 컬럼 하나로 항목별 집계와 추이를 낸다",
        요약=[
            Summary(이름=f"총 {amount}", 식=f"합계([{amount}])", 서식="금액", 설명="원"),
            Summary(이름="항목 수", 식=f"고유건수([{category}])", 서식="정수", 설명="개"),
        ],
        블록=blocks,
    )


def template_from_mapping(mapping: ColumnMapping) -> Template:
    """자동 인식된 컬럼으로 시작 양식을 만든다.

    양식 없이 실행했을 때의 기본 동작이자, 사용자가 자기 양식을 만들 때의
    출발점이기도 하다 (``--save-template`` 으로 저장해 고쳐 쓰면 된다).
    """
    if mapping.budget and mapping.actual:
        return _standard_template(mapping)
    return _simple_template(mapping)


def builtin_templates(mapping: ColumnMapping) -> list[Template]:
    """자동 인식 결과에 맞춰 만들어 둔 예시 양식들."""
    templates = [template_from_mapping(mapping)]

    category = mapping.category or "항목"
    amount = mapping.value_column or "금액"
    if mapping.budget and mapping.actual:
        templates.append(_simple_template(mapping))

    extra = [c for c in mapping.extra_categories if c != category]
    if extra:
        second = extra[0]
        templates.append(
            Template(
                이름=f"{second}별 교차 분석",
                설명=f"{category} 대신 {second} 기준으로 다시 묶어 본다",
                블록=[
                    Block(
                        이름=f"{second}별 집계",
                        기준=[second],
                        측정값=[
                            Measure(컬럼=amount, 함수="합계", 서식="금액"),
                            Measure(컬럼=amount, 함수="평균", 이름="건당 평균", 서식="금액"),
                        ],
                        계산=[Computed(이름="구성비", 식=f"비율([{amount}])", 서식="비율")],
                        정렬=amount,
                        차트="막대",
                    ),
                    Block(
                        이름=f"{second} × {category}",
                        기준=[second, category],
                        측정값=[Measure(컬럼=amount, 함수="합계", 서식="금액")],
                        계산=[Computed(이름="구성비", 식=f"비율([{amount}])", 서식="비율")],
                        정렬=amount,
                        상위=30,
                        차트="없음",
                    ),
                ],
            )
        )
    return templates
