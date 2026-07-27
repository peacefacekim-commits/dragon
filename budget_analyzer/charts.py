"""SVG 차트 생성기.

matplotlib 을 설치할 수 없는 환경이므로 SVG 를 직접 그린다. 색은 하드코딩
대신 CSS 변수(``var(--series-1)`` 등)로 내보내, 보고서의 라이트/다크 테마가
한 곳에서 전환되도록 한다.
"""

from __future__ import annotations

import math
from typing import Callable, Sequence

from .table import format_number, format_percent

__all__ = ["bar_chart", "execution_chart", "line_chart", "empty_chart"]


# 마크 규격 (dataviz 가이드 준수).
_BAR_THICKNESS = 20  # ≤ 24px
_BAR_RADIUS = 4  # 데이터 끝단만 둥글게
_LINE_WIDTH = 2
_MARKER_RADIUS = 4  # 지름 8px
_SURFACE_GAP = 2


def _escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _text_width(text: str, font_size: float) -> float:
    """한글은 전각, 영문·숫자는 반각으로 보고 렌더 폭을 어림한다.

    라벨을 자를지 밖으로 뺄지 판단하려면 그리기 전에 폭을 알아야 한다.
    """
    width = 0.0
    for char in str(text):
        if ord(char) > 0x2E80:  # CJK 및 전각 기호
            width += 1.0
        elif char.isupper():
            width += 0.62
        elif char in "iljt.,'’ ":
            width += 0.32
        else:
            width += 0.55
    return width * font_size


def _truncate(text: str, font_size: float, max_width: float) -> str:
    text = str(text)
    if _text_width(text, font_size) <= max_width:
        return text
    ellipsis = "…"
    budget = max_width - _text_width(ellipsis, font_size)
    kept = ""
    for char in text:
        if _text_width(kept + char, font_size) > budget:
            break
        kept += char
    return (kept or text[:1]) + ellipsis


def _nice_ticks(maximum: float, min_steps: int = 3, max_steps: int = 6) -> list[float]:
    """0 부터 ``maximum`` 이상까지를 1/2/2.5/5 계열의 깔끔한 눈금으로 나눈다.

    눈금 개수가 3~6 칸에 들어오는 가장 촘촘한 간격을 고른다. 간격이 너무 성기면
    축 오른쪽에 빈 공간이 크게 남고, 너무 촘촘하면 눈금이 어지럽다.
    """
    if maximum <= 0:
        return [0.0]

    magnitude = 10 ** math.floor(math.log10(maximum))
    step = magnitude
    for multiple in (0.1, 0.2, 0.25, 0.5, 1, 2, 2.5, 5, 10):
        candidate = magnitude * multiple
        steps = math.ceil(maximum / candidate)
        if min_steps <= steps <= max_steps:
            step = candidate
            break

    # 마지막 눈금이 최대값 이상이어야 데이터가 축 밖으로 삐져나가지 않는다.
    return [step * i for i in range(math.ceil(maximum / step) + 1)]


def _compact(value: float) -> str:
    """축 눈금용 축약 표기. 1,200,000 -> ``120만``."""
    absolute = abs(value)
    if absolute >= 1_0000_0000:
        return f"{value / 1_0000_0000:,.4g}억"
    if absolute >= 1_0000:
        return f"{value / 1_0000:,.4g}만"
    return format_number(value)


def _bar_path(x: float, y: float, width: float, height: float, radius: float) -> str:
    """왼쪽(기준선)은 각지고 오른쪽(데이터 끝)만 둥근 가로 막대."""
    radius = max(0.0, min(radius, width / 2, height / 2))
    if radius <= 0.5:
        return f"M{x:.1f},{y:.1f} h{width:.1f} v{height:.1f} h{-width:.1f} Z"
    return (
        f"M{x:.1f},{y:.1f} "
        f"h{width - radius:.1f} a{radius},{radius} 0 0 1 {radius},{radius} "
        f"v{height - 2 * radius:.1f} a{radius},{radius} 0 0 1 {-radius},{radius} "
        f"h{-(width - radius):.1f} Z"
    )


def _svg_open(width: float, height: float, title: str) -> list[str]:
    return [
        f'<svg class="chart" viewBox="0 0 {width:.0f} {height:.0f}" width="100%" '
        f'height="{height:.0f}" role="img" xmlns="http://www.w3.org/2000/svg" '
        f'aria-label="{_escape(title)}" preserveAspectRatio="xMinYMin meet">'
    ]


def empty_chart(message: str) -> str:
    """데이터가 없을 때 자리를 지키는 안내 그래픽."""
    return (
        '<svg class="chart" viewBox="0 0 720 90" width="100%" height="90" '
        'xmlns="http://www.w3.org/2000/svg" role="img" '
        f'aria-label="{_escape(message)}">'
        f'<text x="360" y="50" text-anchor="middle" class="chart-empty">{_escape(message)}</text>'
        "</svg>"
    )


def bar_chart(
    labels: Sequence[str],
    values: Sequence[float],
    title: str = "",
    shares: Sequence[float | None] | None = None,
    width: float = 720,
) -> str:
    """단일 계열 가로 막대. 항목별 금액 비교용.

    계열이 하나라 범례를 두지 않는다(제목이 무엇을 그렸는지 말해준다).
    값은 막대 끝에 직접 붙인다.
    """
    labels = [str(label) for label in labels]
    values = [float(v or 0) for v in values]
    if not labels:
        return empty_chart("표시할 항목이 없습니다.")

    row_height = 30
    top, bottom = 10, 26
    font_size = 12.5

    label_width = min(max((_text_width(l, font_size) for l in labels), default=60) + 12, 210)
    label_width = max(label_width, 70)
    value_width = 92
    plot_left = label_width + 10
    plot_width = max(width - plot_left - value_width - 12, 80)
    height = top + row_height * len(labels) + bottom

    maximum = max((abs(v) for v in values), default=0.0) or 1.0
    ticks = _nice_ticks(maximum)
    scale_max = ticks[-1] or 1.0

    parts = _svg_open(width, height, title or "항목별 막대 그래프")

    # 눈금선 먼저 (데이터 뒤로 물러나게).
    plot_bottom = top + row_height * len(labels)
    for tick in ticks:
        x = plot_left + plot_width * (tick / scale_max)
        parts.append(
            f'<line class="grid" x1="{x:.1f}" y1="{top - 4:.1f}" x2="{x:.1f}" y2="{plot_bottom:.1f}"/>'
        )
        parts.append(
            f'<text class="axis" x="{x:.1f}" y="{plot_bottom + 16:.1f}" text-anchor="middle">'
            f"{_escape(_compact(tick))}</text>"
        )

    for index, (label, value) in enumerate(zip(labels, values)):
        y = top + index * row_height + (row_height - _BAR_THICKNESS) / 2
        bar_width = max(plot_width * (abs(value) / scale_max), 1.5)
        share_text = ""
        if shares is not None and index < len(shares) and shares[index] is not None:
            share_text = f" · {format_percent(shares[index])}"

        parts.append(f'<g class="bar-row"><title>{_escape(label)}: {format_number(value)}{share_text}</title>')
        parts.append(
            f'<text class="cat-label" x="{label_width:.1f}" y="{y + _BAR_THICKNESS / 2 + 4.5:.1f}" '
            f'text-anchor="end">{_escape(_truncate(label, font_size, label_width - 8))}</text>'
        )
        parts.append(
            f'<path class="bar" d="{_bar_path(plot_left, y, bar_width, _BAR_THICKNESS, _BAR_RADIUS)}"/>'
        )
        parts.append(
            f'<text class="value-label" x="{plot_left + bar_width + 8:.1f}" '
            f'y="{y + _BAR_THICKNESS / 2 + 4.5:.1f}">{_escape(_compact(value))}</text>'
        )
        parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


_STATUS_SYMBOL = {"over": "▲", "under": "▼", "normal": "●", "unknown": "◆"}


def execution_chart(
    labels: Sequence[str],
    rates: Sequence[float | None],
    statuses: Sequence[str],
    width: float = 720,
    status_class: Callable[[str], str] | None = None,
) -> str:
    """비율 막대에 상태색을 입힌다. 상태 문구는 어떤 양식이냐에 따라 달라지므로
    문구 -> 색 매핑은 호출한 쪽이 넘긴다. 색만으로 뜻을 전하지 않도록 기호와
    문구를 항상 함께 그린다.
    """
    labels = [str(label) for label in labels]
    if not labels:
        return empty_chart("표시할 항목이 없습니다.")

    to_class = status_class or (lambda _status: "unknown")
    row_height = 30
    top, bottom = 10, 26
    font_size = 12.5

    label_width = min(max((_text_width(l, font_size) for l in labels), default=60) + 12, 200)
    label_width = max(label_width, 70)
    right_width = 108
    plot_left = label_width + 10
    plot_width = max(width - plot_left - right_width - 12, 80)
    height = top + row_height * len(labels) + bottom

    numeric_rates = [r for r in rates if r is not None]
    scale_max = max(1.0, max(numeric_rates, default=1.0))
    ticks = [t for t in (0.0, 0.5, 0.7, 1.0) if t <= scale_max]
    if scale_max > 1.0:
        ticks.append(round(scale_max, 2))

    parts = _svg_open(width, height, "예산 대비 집행률")
    plot_bottom = top + row_height * len(labels)

    for tick in ticks:
        x = plot_left + plot_width * (tick / scale_max)
        emphasis = " target" if abs(tick - 1.0) < 1e-9 else ""
        parts.append(
            f'<line class="grid{emphasis}" x1="{x:.1f}" y1="{top - 4:.1f}" '
            f'x2="{x:.1f}" y2="{plot_bottom:.1f}"/>'
        )
        parts.append(
            f'<text class="axis" x="{x:.1f}" y="{plot_bottom + 16:.1f}" text-anchor="middle">'
            f"{tick * 100:.0f}%</text>"
        )

    for index, label in enumerate(labels):
        rate = rates[index] if index < len(rates) else None
        status = statuses[index] if index < len(statuses) else "-"
        y = top + index * row_height + (row_height - _BAR_THICKNESS) / 2
        css = to_class(status)
        symbol = _STATUS_SYMBOL.get(css, "·")
        rate_text = "-" if rate is None else format_percent(rate)

        parts.append(
            f'<g class="bar-row"><title>{_escape(label)}: 집행률 {rate_text} ({_escape(status)})</title>'
        )
        parts.append(
            f'<text class="cat-label" x="{label_width:.1f}" y="{y + _BAR_THICKNESS / 2 + 4.5:.1f}" '
            f'text-anchor="end">{_escape(_truncate(label, font_size, label_width - 8))}</text>'
        )
        if rate is not None:
            bar_width = max(plot_width * (rate / scale_max), 1.5)
            parts.append(
                f'<path class="bar status-{css}" '
                f'd="{_bar_path(plot_left, y, bar_width, _BAR_THICKNESS, _BAR_RADIUS)}"/>'
            )
            text_x = plot_left + bar_width + 8
        else:
            text_x = plot_left + 4
        parts.append(
            f'<text class="value-label" x="{text_x:.1f}" y="{y + _BAR_THICKNESS / 2 + 4.5:.1f}">'
            f'{_escape(rate_text)} <tspan class="status-mark status-{css}">{symbol}</tspan> '
            f'<tspan class="status-word">{_escape(status)}</tspan></text>'
        )
        parts.append("</g>")

    parts.append("</svg>")
    return "".join(parts)


def line_chart(
    periods: Sequence[str],
    series: Sequence[tuple[str, Sequence[float | None]]],
    width: float = 720,
    height: float = 300,
) -> str:
    """기간별 추이 꺾은선. 계열은 최대 2개(예산·집행)를 상정한다.

    축은 하나만 쓴다. 값 라벨은 마지막 점에만 붙이고 나머지는 축·툴팁이 맡는다.
    """
    periods = [str(p) for p in periods]
    series = [(name, list(values)) for name, values in series if any(v is not None for v in values)]
    if not periods or not series:
        return empty_chart("기간별 추이를 그릴 데이터가 없습니다.")

    left, right, top, bottom = 62, 76, 16, 42
    plot_width = max(width - left - right, 80)
    plot_height = max(height - top - bottom, 80)

    all_values = [v for _, values in series for v in values if v is not None]
    maximum = max(all_values + [0.0])
    ticks = _nice_ticks(maximum)
    scale_max = ticks[-1] or 1.0

    def x_at(index: int) -> float:
        if len(periods) == 1:
            return left + plot_width / 2
        return left + plot_width * index / (len(periods) - 1)

    def y_at(value: float) -> float:
        return top + plot_height * (1 - value / scale_max)

    parts = _svg_open(width, height, "기간별 추이")

    for tick in ticks:
        y = y_at(tick)
        parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}"/>')
        parts.append(
            f'<text class="axis" x="{left - 8}" y="{y + 4:.1f}" text-anchor="end">'
            f"{_escape(_compact(tick))}</text>"
        )

    # x 축 라벨은 서로 겹치지 않을 만큼만 남긴다. 마지막 눈금은 항상 표시하되,
    # 직전 라벨과 붙으면 그 직전 것을 대신 버린다.
    label_font = 11.5
    widest = max((_text_width(p, label_font) for p in periods), default=30)
    stride = max(1, math.ceil((widest + 10) / max(plot_width / max(len(periods) - 1, 1), 1)))
    shown = [i for i in range(len(periods)) if i % stride == 0]
    last = len(periods) - 1
    if last not in shown:
        if shown and x_at(last) - x_at(shown[-1]) < widest + 16:
            shown.pop()
        shown.append(last)
    for index in shown:
        parts.append(
            f'<text class="axis" x="{x_at(index):.1f}" y="{top + plot_height + 20:.1f}" '
            f'text-anchor="middle">{_escape(periods[index])}</text>'
        )

    for slot, (name, values) in enumerate(series[:2], start=1):
        points = [(x_at(i), y_at(v)) for i, v in enumerate(values) if v is not None]
        if not points:
            continue
        path = "M" + " L".join(f"{x:.1f},{y:.1f}" for x, y in points)
        parts.append(f'<path class="line series-{slot}" d="{path}"/>')
        for (x, y), value in zip(points, [v for v in values if v is not None]):
            parts.append(f'<circle class="marker series-{slot}" cx="{x:.1f}" cy="{y:.1f}" r="{_MARKER_RADIUS}"/>')

        last_x, last_y = points[-1]
        last_value = [v for v in values if v is not None][-1]
        parts.append(
            f'<text class="value-label" x="{last_x + 10:.1f}" y="{last_y + 4:.1f}">'
            f"{_escape(_compact(last_value))}</text>"
        )
        parts.append(
            f'<text class="series-name" x="{last_x + 10:.1f}" y="{last_y - 8:.1f}">{_escape(name)}</text>'
        )

    # 기간별 값 전체를 담은 투명 히트 영역 — 마크보다 넉넉한 호버 대상.
    band = plot_width / max(len(periods), 1)
    for index, period in enumerate(periods):
        readings = " / ".join(
            f"{name} {_compact(values[index])}"
            for name, values in series[:2]
            if index < len(values) and values[index] is not None
        )
        parts.append(
            f'<rect class="hit" x="{x_at(index) - band / 2:.1f}" y="{top}" '
            f'width="{band:.1f}" height="{plot_height:.1f}">'
            f"<title>{_escape(period)}: {_escape(readings)}</title></rect>"
        )

    parts.append("</svg>")
    return "".join(parts)
