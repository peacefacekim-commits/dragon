"""컬럼 역할 자동 인식.

부서마다 엑셀 양식이 달라도 매번 코드를 고치지 않도록, 머리글 이름과
실제 값의 생김새를 함께 보고 어떤 컬럼이 예산액인지 집행액인지 추정한다.
추정이 틀리면 GUI 에서 바꾸거나 매핑 프로파일(JSON)로 고정할 수 있다.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .table import Table, to_date, to_number

__all__ = ["ColumnMapping", "guess_mapping", "load_profile", "save_profile"]


# 역할별 머리글 키워드. 앞쪽일수록 확신이 강한 표현.
_BUDGET_TOKENS = (
    ("예산현액", 10), ("예산액", 10), ("당초예산", 9), ("본예산", 9),
    ("계상액", 8), ("편성액", 8), ("예산", 7), ("계획", 5), ("budget", 8),
)
_ACTUAL_TOKENS = (
    ("집행액", 10), ("지출액", 10), ("執行", 9), ("사용액", 9), ("결산액", 9),
    ("집행", 8), ("지출", 8), ("실적", 7), ("사용", 6), ("actual", 8), ("spent", 8),
)
_AMOUNT_TOKENS = (
    ("금액", 9), ("합계", 7), ("총액", 8), ("소계", 6), ("amount", 8), ("total", 6),
)
_CATEGORY_TOKENS = (
    ("계정과목", 10), ("세부사업", 10), ("사업명", 10), ("예산과목", 9),
    ("부서명", 9), ("항목", 8), ("과목", 8), ("부서", 8), ("사업", 7),
    ("구분", 6), ("분류", 6), ("실국", 8), ("본부", 6), ("팀", 5), ("명칭", 5),
)
_DATE_TOKENS = (
    ("집행일자", 10), ("지출일자", 10), ("일자", 9), ("날짜", 9), ("기간", 7),
    ("월", 6), ("분기", 7), ("연월", 8), ("date", 8), ("month", 7),
)
# 코드/식별자 컬럼은 숫자여도 금액이 아니다.
_EXCLUDE_TOKENS = ("코드", "번호", "no", "순번", "id", "연번", "비고")


def _score_header(header: str, tokens: tuple[tuple[str, int], ...]) -> int:
    lowered = header.lower().replace(" ", "")
    return max((weight for token, weight in tokens if token.lower() in lowered), default=0)


def _is_excluded(header: str) -> bool:
    lowered = header.lower().replace(" ", "")
    return any(token in lowered for token in _EXCLUDE_TOKENS)


def _profile_column(table: Table, column: str, sample_size: int = 300) -> dict[str, float]:
    """컬럼 값의 성격(숫자 비율, 날짜 비율, 고유값 수)을 잰다."""
    values = table.column(column)[:sample_size]
    filled = [v for v in values if v is not None and str(v).strip() != ""]
    if not filled:
        return {"numeric": 0.0, "date": 0.0, "unique": 0.0, "filled": 0.0, "magnitude": 0.0}

    numbers = [to_number(v) for v in filled]
    numeric = [n for n in numbers if n is not None]
    dates = [v for v in filled if to_date(v) is not None]
    magnitude = max((abs(n) for n in numeric), default=0.0)

    return {
        "numeric": len(numeric) / len(filled),
        "date": len(dates) / len(filled),
        "unique": len({str(v).strip() for v in filled}) / len(filled),
        "filled": len(filled) / max(len(values), 1),
        "magnitude": magnitude,
    }


@dataclass
class ColumnMapping:
    """어떤 컬럼이 어떤 역할인지에 대한 결론."""

    category: str | None = None
    budget: str | None = None
    actual: str | None = None
    amount: str | None = None
    date: str | None = None
    extra_categories: list[str] = field(default_factory=list)

    @property
    def value_column(self) -> str | None:
        """구성비 분석의 기준이 되는 금액 컬럼."""
        return self.actual or self.amount or self.budget

    def describe(self) -> str:
        pairs = [
            ("분류", self.category),
            ("예산액", self.budget),
            ("집행액", self.actual),
            ("금액", self.amount),
            ("일자", self.date),
        ]
        found = [f"{label}={name}" for label, name in pairs if name]
        return ", ".join(found) if found else "인식된 컬럼 없음"

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)


def guess_mapping(table: Table) -> ColumnMapping:
    """표에서 각 역할에 가장 어울리는 컬럼을 고른다."""
    profiles = {column: _profile_column(table, column) for column in table.columns}
    mapping = ColumnMapping()

    def numeric_candidates(tokens: tuple[tuple[str, int], ...]) -> list[tuple[float, str]]:
        scored = []
        for column in table.columns:
            profile = profiles[column]
            if profile["numeric"] < 0.6 or profile["filled"] < 0.1:
                continue
            if _is_excluded(column):
                continue
            header_score = _score_header(column, tokens)
            if header_score == 0:
                continue
            # 같은 점수면 값이 큰 쪽(단가보다 총액)을 선호한다.
            scored.append((header_score + min(profile["magnitude"], 1e12) / 1e13, column))
        scored.sort(reverse=True)
        return scored

    budget_candidates = numeric_candidates(_BUDGET_TOKENS)
    actual_candidates = numeric_candidates(_ACTUAL_TOKENS)
    if budget_candidates:
        mapping.budget = budget_candidates[0][1]
    if actual_candidates:
        mapping.actual = next(
            (name for _, name in actual_candidates if name != mapping.budget), None
        )

    amount_candidates = [
        (score, name)
        for score, name in numeric_candidates(_AMOUNT_TOKENS)
        if name not in (mapping.budget, mapping.actual)
    ]
    if amount_candidates:
        mapping.amount = amount_candidates[0][1]
    elif not mapping.budget and not mapping.actual:
        # 이름으로는 못 찾았으니 값이 가장 큰 숫자 컬럼을 금액으로 본다.
        fallback = [
            (profiles[c]["magnitude"], c)
            for c in table.columns
            if profiles[c]["numeric"] >= 0.7 and not _is_excluded(c)
        ]
        if fallback:
            mapping.amount = max(fallback)[1]

    date_scored: list[tuple[float, str]] = []
    for column in table.columns:
        profile = profiles[column]
        score = _score_header(column, _DATE_TOKENS) + profile["date"] * 6
        if profile["date"] >= 0.5 or (score >= 6 and profile["numeric"] < 0.95):
            date_scored.append((score, column))
    if date_scored:
        mapping.date = max(date_scored)[1]

    numeric_roles = {mapping.budget, mapping.actual, mapping.amount, mapping.date}
    category_scored: list[tuple[float, str]] = []
    for column in table.columns:
        if column in numeric_roles:
            continue
        profile = profiles[column]
        if profile["numeric"] >= 0.8:
            continue
        # 값이 너무 잘게 쪼개져 있으면(거의 전부 고유값) 묶어봐야 의미가 없다.
        repetition = 1.0 - profile["unique"]
        score = _score_header(column, _CATEGORY_TOKENS) + repetition * 5 + profile["filled"] * 2
        if _is_excluded(column):
            score -= 6
        category_scored.append((score, column))

    category_scored.sort(reverse=True)
    if category_scored:
        mapping.category = category_scored[0][1]
        mapping.extra_categories = [name for _, name in category_scored[1:4]]

    return mapping


def save_profile(path: str, mapping: ColumnMapping) -> str:
    """매핑을 JSON 으로 저장해 다음 실행 때 재사용한다."""
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(mapping.to_json())
    return path


def load_profile(path: str) -> ColumnMapping:
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    known = {f for f in ColumnMapping.__dataclass_fields__}
    return ColumnMapping(**{k: v for k, v in data.items() if k in known})
