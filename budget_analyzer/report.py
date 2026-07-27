"""단일 HTML 보고서 생성.

외부 CSS/JS/폰트를 전혀 참조하지 않는다. 파일 하나만 있으면 인터넷이
끊긴 PC 에서도 열리고, 그대로 인쇄하거나 메일로 넘길 수 있다.
"""

from __future__ import annotations

import datetime as _dt

from . import charts
from .analysis import AnalysisResult
from .table import Table, format_number, format_percent, to_number

__all__ = ["render_report", "write_report"]


# dataviz 기준 팔레트(검증 통과분). 라이트/다크 각각 별도 단계.
_STYLE = """
:root {
  color-scheme: light;
  --surface-0: #f4f4f1;
  --surface-1: #fcfcfb;
  --surface-2: #edece8;
  --border:    #dcdbd5;
  --grid:      #e5e4de;
  --text-1:    #0b0b0b;
  --text-2:    #52514e;
  --text-3:    #77756e;
  --series-1:  #2a78d6;
  --series-2:  #eb6834;
  --good:      #0ca30c;
  --warning:   #fab219;
  --critical:  #d03b3b;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    color-scheme: dark;
    --surface-0: #121211;
    --surface-1: #1a1a19;
    --surface-2: #232322;
    --border:    #383835;
    --grid:      #2f2f2d;
    --text-1:    #ffffff;
    --text-2:    #c3c2b7;
    --text-3:    #94938a;
    --series-1:  #3987e5;
    --series-2:  #d95926;
    --good:      #0ca30c;
    --warning:   #fab219;
    --critical:  #d03b3b;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0;
  padding: 28px 20px 64px;
  background: var(--surface-0);
  color: var(--text-1);
  font-family: "맑은 고딕", "Malgun Gothic", "Apple SD Gothic Neo", "Noto Sans KR",
               system-ui, -apple-system, sans-serif;
  font-size: 14px;
  line-height: 1.55;
  -webkit-font-smoothing: antialiased;
}
.wrap { max-width: 1080px; margin: 0 auto; }
header.doc { margin-bottom: 22px; }
header.doc h1 { margin: 0 0 6px; font-size: 22px; letter-spacing: -0.01em; }
.meta { color: var(--text-3); font-size: 12.5px; }
.meta code {
  background: var(--surface-2); padding: 1px 6px; border-radius: 4px;
  font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 12px;
}
section.card {
  background: var(--surface-1);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 20px 22px;
  margin-bottom: 18px;
}
section.card > h2 {
  margin: 0 0 2px; font-size: 15.5px; font-weight: 650; letter-spacing: -0.01em;
}
section.card > p.sub { margin: 0 0 16px; color: var(--text-3); font-size: 12.5px; }

.tiles {
  display: grid; gap: 12px; margin-bottom: 18px;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
}
.tile {
  background: var(--surface-1); border: 1px solid var(--border);
  border-radius: 10px; padding: 14px 16px;
}
.tile .label { color: var(--text-3); font-size: 12px; margin-bottom: 4px; }
.tile .figure {
  font-size: 23px; font-weight: 640; letter-spacing: -0.02em;
  font-variant-numeric: tabular-nums; line-height: 1.25; white-space: nowrap;
}
.tile .note { color: var(--text-3); font-size: 12px; margin-top: 3px; }

.legend { display: flex; flex-wrap: wrap; gap: 14px; margin: 0 0 10px; }
.legend span { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; color: var(--text-2); }
.legend i { width: 14px; height: 3px; border-radius: 2px; display: inline-block; }
.legend i.s1 { background: var(--series-1); }
.legend i.s2 { background: var(--series-2); }

.chart-scroll { overflow-x: auto; }
svg.chart { display: block; min-width: 520px; }
svg.chart .grid { stroke: var(--grid); stroke-width: 1; }
svg.chart .grid.target { stroke: var(--text-3); stroke-dasharray: none; }
svg.chart .axis { fill: var(--text-3); font-size: 11.5px; }
svg.chart .cat-label { fill: var(--text-2); font-size: 12.5px; }
svg.chart .value-label { fill: var(--text-1); font-size: 12px; font-variant-numeric: tabular-nums; }
svg.chart .series-name { fill: var(--text-2); font-size: 11.5px; }
svg.chart .status-word { fill: var(--text-3); font-size: 11px; }
svg.chart .chart-empty { fill: var(--text-3); font-size: 13px; }
svg.chart .bar { fill: var(--series-1); }
svg.chart .bar.status-normal { fill: var(--good); }
svg.chart .bar.status-under { fill: var(--warning); }
svg.chart .bar.status-over { fill: var(--critical); }
svg.chart .bar.status-unknown { fill: var(--text-3); }
svg.chart .status-mark.status-normal { fill: var(--good); }
svg.chart .status-mark.status-under { fill: var(--warning); }
svg.chart .status-mark.status-over { fill: var(--critical); }
svg.chart .status-mark.status-unknown { fill: var(--text-3); }
svg.chart .line { fill: none; stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
svg.chart .line.series-1 { stroke: var(--series-1); }
svg.chart .line.series-2 { stroke: var(--series-2); }
svg.chart .marker { stroke: var(--surface-1); stroke-width: 2; }
svg.chart .marker.series-1 { fill: var(--series-1); }
svg.chart .marker.series-2 { fill: var(--series-2); }
svg.chart .hit { fill: transparent; }
svg.chart .hit:hover { fill: var(--text-1); fill-opacity: 0.04; }
svg.chart .bar-row:hover .bar { fill-opacity: 0.82; }

table { border-collapse: collapse; width: 100%; font-size: 13px; }
.table-scroll { overflow-x: auto; margin-top: 6px; }
th, td {
  padding: 7px 10px; text-align: left; white-space: nowrap;
  border-bottom: 1px solid var(--border);
}
th { color: var(--text-3); font-weight: 600; font-size: 12px; background: var(--surface-2); }
thead th:first-child { border-top-left-radius: 6px; }
thead th:last-child { border-top-right-radius: 6px; }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
tbody tr:hover td { background: var(--surface-2); }
tbody tr.total-row td { font-weight: 650; border-top: 2px solid var(--border); }
.pill {
  display: inline-block; padding: 1px 8px; border-radius: 99px;
  font-size: 11.5px; font-weight: 600; border: 1px solid;
}
.pill.normal { color: var(--good); border-color: var(--good); }
.pill.under { color: var(--warning); border-color: var(--warning); }
.pill.over { color: var(--critical); border-color: var(--critical); }
.pill.unknown { color: var(--text-3); border-color: var(--border); }

ul.notes { margin: 0; padding-left: 18px; color: var(--text-2); font-size: 13px; }
ul.notes li { margin-bottom: 4px; }
footer.doc { color: var(--text-3); font-size: 12px; text-align: center; margin-top: 26px; }

@media print {
  body { background: #fff; padding: 0; }
  section.card, .tile { border-color: #ccc; break-inside: avoid; }
  svg.chart { min-width: 0; }
}
"""

_STATUS_CLASS = {"초과": "over", "부진": "under", "정상": "normal"}


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _is_percent_column(name: str) -> bool:
    return any(token in name for token in ("구성비", "집행률", "전기대비", "비율", "%"))


def _format_cell(column: str, value: object) -> tuple[str, bool]:
    """(표시 문자열, 우측정렬 여부)."""
    if column == "상태":
        css = _STATUS_CLASS.get(str(value), "unknown")
        return f'<span class="pill {css}">{_escape(value)}</span>', False

    number = to_number(value)
    if number is None:
        return _escape("" if value is None else value), False
    if _is_percent_column(column):
        return _escape(format_percent(number)), True
    decimals = 0 if abs(number - round(number)) < 1e-9 else 2
    return _escape(format_number(number, decimals)), True


def _render_table(table: Table, limit: int = 200, with_total: bool = True) -> str:
    """표를 HTML 로. 차트가 못 보여주는 값은 여기서 전부 확인할 수 있다."""
    rows = table.rows[:limit]
    head = "".join(f"<th>{_escape(c)}</th>" for c in table.columns)

    body_parts = []
    for row in rows:
        cells = []
        for column, value in zip(table.columns, row):
            text, numeric = _format_cell(column, value)
            cells.append(f'<td class="num">{text}</td>' if numeric else f"<td>{text}</td>")
        body_parts.append("<tr>" + "".join(cells) + "</tr>")

    if with_total and len(table):
        total_cells = []
        for index, column in enumerate(table.columns):
            if index == 0:
                total_cells.append("<td>합계</td>")
                continue
            if column in ("상태",) or _is_percent_column(column):
                total_cells.append("<td></td>")
                continue
            numbers = [to_number(row[index]) for row in table.rows]
            if all(n is None for n in numbers):
                total_cells.append("<td></td>")
                continue
            total = sum(n for n in numbers if n is not None)
            total_cells.append(f'<td class="num">{_escape(format_number(total))}</td>')
        body_parts.append('<tr class="total-row">' + "".join(total_cells) + "</tr>")

    note = ""
    if len(table) > limit:
        note = f'<p class="sub">전체 {len(table):,}행 중 상위 {limit:,}행만 표시 (전체는 엑셀 파일 참조)</p>'

    return (
        '<div class="table-scroll"><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_parts)}</tbody>"
        f"</table></div>{note}"
    )


def _tiles(result: AnalysisResult) -> str:
    tiles: list[str] = []

    def tile(label: str, figure: str, note: str = "", unit: str = "") -> str:
        # 단위는 숫자 옆이 아니라 라벨에 붙인다. 억 단위 금액은 숫자만으로도
        # 줄을 꽉 채워서, 단위를 옆에 두면 혼자 다음 줄로 넘어간다.
        heading = f"{label} ({unit})" if unit else label
        note_html = f'<div class="note">{_escape(note)}</div>' if note else ""
        return (
            f'<div class="tile"><div class="label">{_escape(heading)}</div>'
            f'<div class="figure">{_escape(figure)}</div>{note_html}</div>'
        )

    budget = result.totals.get("예산액")
    actual = result.totals.get("집행액")
    amount = result.totals.get("금액")

    if budget is not None:
        tiles.append(tile("총 예산액", format_number(budget), unit="원"))
    if actual is not None:
        tiles.append(tile("총 집행액", format_number(actual), unit="원"))
    if budget is not None and actual is not None:
        remaining = budget - actual
        rate = result.execution_rate
        tiles.append(
            tile(
                "잔액",
                format_number(remaining),
                note="예산 초과" if remaining < 0 else "미집행 잔액",
                unit="원",
            )
        )
        tiles.append(
            tile(
                "전체 집행률",
                format_percent(rate) if rate is not None else "-",
                note="예산 대비 집행액",
            )
        )
    elif amount is not None:
        tiles.append(tile("총 금액", format_number(amount), unit="원"))

    tiles.append(tile("분석 행 수", f"{result.row_count:,}", note=f"시트: {result.sheet}", unit="건"))
    return f'<div class="tiles">{"".join(tiles)}</div>'


def _breakdown_section(result: AnalysisResult) -> str:
    table = result.breakdown
    category = result.mapping.category or "항목"
    value_column = result.mapping.value_column or ""

    if table is None or not len(table):
        chart = charts.empty_chart("항목별 집계를 만들 수 없습니다.")
        body = ""
    else:
        top = Table(table.columns, table.rows[:15], table.name)
        chart = charts.bar_chart(
            [str(row[0]) for row in top.rows],
            [to_number(row[top.index_of(value_column)]) or 0.0 for row in top.rows],
            title=f"{category}별 {value_column}",
            shares=[to_number(row[top.index_of("구성비")]) for row in top.rows],
        )
        body = _render_table(table)

    return (
        '<section class="card"><h2>1. 항목별 집계 · 구성비</h2>'
        f'<p class="sub">{_escape(category)} 기준 {_escape(value_column)} 합계와 전체 대비 비중 '
        "(금액 큰 순, 상위 15개 그래프)</p>"
        f'<div class="chart-scroll">{chart}</div>{body}</section>'
    )


def _execution_section(result: AnalysisResult) -> str:
    table = result.execution
    if table is None or not len(table):
        reason = "예산액·집행액 컬럼이 모두 있어야 계산할 수 있습니다."
        return (
            '<section class="card"><h2>2. 예산 대비 집행률</h2>'
            f'<p class="sub">{_escape(reason)}</p>'
            f'<div class="chart-scroll">{charts.empty_chart(reason)}</div></section>'
        )

    top = Table(table.columns, table.rows[:15], table.name)
    chart = charts.execution_chart(
        [str(row[0]) for row in top.rows],
        [to_number(row[top.index_of("집행률")]) for row in top.rows],
        [str(row[top.index_of("상태")]) for row in top.rows],
    )
    legend = (
        '<div class="legend">'
        f'<span><span class="pill normal">정상</span> 집행률 70% 이상 100% 이하</span>'
        f'<span><span class="pill under">부진</span> 70% 미만</span>'
        f'<span><span class="pill over">초과</span> 100% 초과</span>'
        "</div>"
    )
    return (
        '<section class="card"><h2>2. 예산 대비 집행률</h2>'
        '<p class="sub">예산액 큰 순 상위 15개. 100% 눈금이 목표선입니다.</p>'
        f"{legend}<div class=\"chart-scroll\">{chart}</div>{_render_table(table)}</section>"
    )


def _trend_section(result: AnalysisResult) -> str:
    table = result.trend
    grain_label = {"month": "월별", "quarter": "분기별", "year": "연도별"}.get(result.grain, "기간별")

    if table is None or not len(table):
        reason = "일자/기간 컬럼을 찾지 못해 추이를 그릴 수 없습니다."
        return (
            f'<section class="card"><h2>3. {_escape(grain_label)} 추이</h2>'
            f'<p class="sub">{_escape(reason)}</p>'
            f'<div class="chart-scroll">{charts.empty_chart(reason)}</div></section>'
        )

    periods = [str(row[0]) for row in table.rows]
    measures = [
        column
        for column in table.columns[1:]
        if column not in ("건수", "전기대비") and not column.startswith("누적")
    ]
    series = [
        (column, [to_number(row[table.index_of(column)]) for row in table.rows])
        for column in measures[:2]
    ]
    # 예산액을 연초에 한 번만 계상하는 양식이면 기간별 예산 계열은 대부분 0 이라
    # 그래프가 '예산이 급감한 것처럼' 읽힌다. 그런 계열은 표에만 남긴다.
    if len(series) > 1:
        meaningful = [
            (name, values)
            for name, values in series
            if sum(1 for v in values if v) >= max(2, len(periods) * 0.6)
        ]
        if meaningful:
            series = meaningful

    chart = charts.line_chart(periods, series)

    legend = ""
    if len(series) >= 2:
        legend = (
            '<div class="legend">'
            f'<span><i class="s1"></i>{_escape(series[0][0])}</span>'
            f'<span><i class="s2"></i>{_escape(series[1][0])}</span>'
            "</div>"
        )

    plotted = " · ".join(name for name, _ in series)
    return (
        f'<section class="card"><h2>3. {_escape(grain_label)} 추이</h2>'
        f'<p class="sub">그래프: {_escape(plotted)} · 표에는 누적액과 직전 기간 대비 증감률까지</p>'
        f"{legend}<div class=\"chart-scroll\">{chart}</div>"
        f"{_render_table(table, with_total=False)}</section>"
    )


def _notes_section(result: AnalysisResult) -> str:
    if not result.warnings:
        return ""
    items = "".join(f"<li>{_escape(w)}</li>" for w in result.warnings)
    return (
        '<section class="card"><h2>확인이 필요한 사항</h2>'
        f'<ul class="notes">{items}</ul></section>'
    )


def render_report(result: AnalysisResult, title: str = "예산 분석 보고서") -> str:
    """분석 결과를 자기완결형 HTML 문자열로 만든다."""
    generated = result.generated_at.strftime("%Y-%m-%d %H:%M")
    source = result.source or "(직접 입력)"

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_escape(title)}</title>
<style>{_STYLE}</style>
</head>
<body>
<div class="wrap">
<header class="doc">
  <h1>{_escape(title)}</h1>
  <div class="meta">
    원본 <code>{_escape(source)}</code> · 시트 <code>{_escape(result.sheet)}</code>
    · {result.row_count:,}행 · 생성 {generated}
    <br>인식된 컬럼: {_escape(result.mapping.describe())}
  </div>
</header>
{_tiles(result)}
{_breakdown_section(result)}
{_execution_section(result)}
{_trend_section(result)}
{_notes_section(result)}
<footer class="doc">
  이 파일은 외부 인터넷 연결 없이 열람·인쇄할 수 있습니다. ·
  {_escape(_dt.datetime.now().year)} 예산 분석기
</footer>
</div>
</body>
</html>
"""


def write_report(path: str, result: AnalysisResult, title: str = "예산 분석 보고서") -> str:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_report(result, title))
    return path
