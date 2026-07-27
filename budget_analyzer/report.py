"""단일 HTML 보고서 생성.

양식이 만들어 낸 블록 목록을 그대로 그린다. 어떤 분석인지는 알지 못하고,
블록의 서식·차트 지정만 보고 렌더링한다.

외부 CSS/JS/폰트를 전혀 참조하지 않는다. 파일 하나만 있으면 인터넷이
끊긴 PC 에서도 열리고, 그대로 인쇄하거나 메일로 넘길 수 있다.
"""

from __future__ import annotations

from . import charts
from .engine import BlockResult, Report
from .table import format_number, format_percent, to_number

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
ul.notes.block { margin-top: 14px; }
footer.doc { color: var(--text-3); font-size: 12px; text-align: center; margin-top: 26px; }

@media print {
  body { background: #fff; padding: 0; }
  section.card, .tile { border-color: #ccc; break-inside: avoid; }
  svg.chart { min-width: 0; }
}
"""

# 상태 문구를 색으로 옮기는 규칙. 양식마다 문구가 다르므로 키워드로 판단한다.
_STATUS_KEYWORDS = (
    (("초과", "위험", "심각", "미납", "오류"), "over"),
    (("부진", "주의", "지연", "미달", "경고"), "under"),
    (("정상", "양호", "완료", "적정"), "normal"),
)


def _escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def status_class(value: object) -> str:
    """상태 문구에 맞는 CSS 클래스. 색만으로 뜻을 전하지 않도록 문구는 항상 함께 쓴다."""
    text = str(value)
    for keywords, css in _STATUS_KEYWORDS:
        if any(keyword in text for keyword in keywords):
            return css
    return "unknown"


def _looks_like_percent(column: str) -> bool:
    return any(token in column for token in ("구성비", "집행률", "증감", "비율", "율", "률", "%"))


def format_value(value: object, kind: str = "자동", column: str = "") -> tuple[str, bool]:
    """(표시 문자열, 우측정렬 여부). ``kind`` 는 양식이 지정한 서식."""
    if kind == "문자":
        return _escape("" if value is None else value), False
    if kind == "상태":
        return f'<span class="pill {status_class(value)}">{_escape(value)}</span>', False

    number = to_number(value)
    if number is None:
        return _escape("" if value is None else value), False

    if kind == "비율":
        return _escape(format_percent(number)), True
    if kind == "금액" or kind == "정수":
        return _escape(format_number(number)), True
    if kind == "소수":
        return _escape(format_number(number, 2)), True

    # 자동: 컬럼 이름이 비율처럼 생겼으면 퍼센트로, 아니면 자릿수를 보고 정한다.
    if _looks_like_percent(column):
        return _escape(format_percent(number)), True
    decimals = 0 if abs(number - round(number)) < 1e-9 else 2
    return _escape(format_number(number, decimals)), True


def _render_table(block: BlockResult, limit: int = 200) -> str:
    """블록의 표를 HTML 로. 차트가 못 보여주는 값은 여기서 전부 확인할 수 있다."""
    table = block.표
    if not len(table):
        return ""

    rows = table.rows[:limit]
    head = "".join(f"<th>{_escape(c)}</th>" for c in table.columns)

    body_parts = []
    for row in rows:
        cells = []
        for column, value in zip(table.columns, row):
            text, numeric = format_value(value, block.서식.get(column, "자동"), column)
            cells.append(f'<td class="num">{text}</td>' if numeric else f"<td>{text}</td>")
        body_parts.append("<tr>" + "".join(cells) + "</tr>")

    if block.합계표시:
        body_parts.append(_total_row(block))

    note = ""
    if len(table) > limit:
        note = (
            f'<p class="sub">전체 {len(table):,}행 중 상위 {limit:,}행만 표시 '
            "(전체는 엑셀 내보내기 참조)</p>"
        )

    return (
        '<div class="table-scroll"><table>'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body_parts)}</tbody>"
        f"</table></div>{note}"
    )


def _total_row(block: BlockResult) -> str:
    """합산이 말이 되는 컬럼만 더한다.

    평균·비율·상태를 세로로 더하면 뜻이 없으므로, 양식이 합계·건수로 집계한
    측정값과 금액·정수 계산 컬럼만 더한다.
    """
    table = block.표
    cells = []
    for index, column in enumerate(table.columns):
        if index == 0:
            cells.append("<td>합계</td>")
            continue

        if column not in block.합산가능:
            cells.append("<td></td>")
            continue

        numbers = [to_number(row[index]) for row in table.rows]
        if all(n is None for n in numbers):
            cells.append("<td></td>")
            continue
        total = sum(n for n in numbers if n is not None)
        cells.append(f'<td class="num">{_escape(format_number(total))}</td>')
    return '<tr class="total-row">' + "".join(cells) + "</tr>"


def _tiles(report: Report) -> str:
    if not report.tiles:
        return ""

    parts = []
    for tile in report.tiles:
        text, _ = format_value(tile.값, tile.서식, tile.이름)
        # 단위는 숫자 옆이 아니라 라벨에 붙인다. 억 단위 금액은 숫자만으로도
        # 줄을 꽉 채워서, 단위를 옆에 두면 혼자 다음 줄로 넘어간다.
        note = tile.설명
        heading = tile.이름
        if note and len(note) <= 3:  # "원", "건", "개" 같은 단위
            heading, note = f"{tile.이름} ({note})", ""
        note_html = f'<div class="note">{_escape(note)}</div>' if note else ""
        parts.append(
            f'<div class="tile"><div class="label">{_escape(heading)}</div>'
            f'<div class="figure">{text}</div>{note_html}</div>'
        )
    return f'<div class="tiles">{"".join(parts)}</div>'


# ── 차트 선택 ──────────────────────────────────────────────────────


def _column_of_format(block: BlockResult, kind: str) -> str | None:
    for column in block.표.columns:
        if block.서식.get(column) == kind:
            return column
    return None


def _label_column(block: BlockResult) -> str:
    """막대 차트의 세로축이 무엇인지 나타내는 이름."""
    return " · ".join(block.기준이름) or (block.표.columns[0] if block.표.columns else "")


def _bar_labels(block: BlockResult) -> list[str]:
    """기준 컬럼이 여러 개면 값을 이어 붙여 한 줄 라벨로 만든다."""
    key_count = max(1, len(block.기준이름))
    return [
        " · ".join(str(cell) for cell in row[:key_count] if str(cell).strip())
        for row in block.표.rows
    ]


def _render_chart(block: BlockResult) -> str:
    table = block.표
    if block.차트 == "없음" or not len(table):
        return ""

    if block.차트 == "선":
        return _render_line_chart(block)
    return _render_bar_chart(block)


def _render_bar_chart(block: BlockResult) -> str:
    table = block.표
    value_column = block.차트값 or (block.측정값이름[0] if block.측정값이름 else "")
    if value_column not in table.columns:
        numeric = [c for c in table.columns[1:] if any(to_number(v) is not None for v in table.column(c))]
        if not numeric:
            return charts.empty_chart("그래프로 그릴 숫자 컬럼이 없습니다.")
        value_column = numeric[0]

    labels = _bar_labels(block)
    top = 15
    labels, rows = labels[:top], table.rows[:top]
    values_index = table.index_of(value_column)

    # 비율 컬럼을 상태 컬럼과 함께 그리면 집행률 형태의 그래프가 된다.
    status_column = _column_of_format(block, "상태")
    is_ratio = block.서식.get(value_column) == "비율" or _looks_like_percent(value_column)
    if status_column and is_ratio:
        status_index = table.index_of(status_column)
        return charts.execution_chart(
            labels,
            [to_number(row[values_index]) for row in rows],
            [str(row[status_index]) for row in rows],
            status_class=status_class,
        )

    share_column = next(
        (c for c in table.columns if block.서식.get(c) == "비율" or "구성비" in c), None
    )
    shares = None
    if share_column and share_column != value_column:
        share_index = table.index_of(share_column)
        shares = [to_number(row[share_index]) for row in rows]

    return charts.bar_chart(
        labels,
        [to_number(row[values_index]) or 0.0 for row in rows],
        title=f"{_label_column(block)}별 {value_column}",
        shares=shares,
    )


def _line_series(block: BlockResult) -> list[tuple[str, list[float | None]]]:
    table = block.표
    if block.차트값 and block.차트값 in table.columns:
        names = [block.차트값]
    else:
        names = [n for n in block.측정값이름 if n in table.columns][:2]
    if not names:
        names = [
            c
            for c in table.columns[1:]
            if c != "건수" and any(to_number(v) is not None for v in table.column(c))
        ][:1]

    series = [(name, [to_number(v) for v in table.column(name)]) for name in names]

    # 예산액을 연초에 한 번만 계상하는 양식이면 기간별 예산 계열은 대부분 0 이라
    # 그래프가 '예산이 급감한 것처럼' 읽힌다. 그런 계열은 표에만 남긴다.
    if len(series) > 1:
        meaningful = [
            (name, values)
            for name, values in series
            if sum(1 for v in values if v) >= max(2, len(table.rows) * 0.6)
        ]
        if meaningful:
            series = meaningful
    return series


def _render_line_chart(block: BlockResult) -> str:
    table = block.표
    periods = [str(row[0]) for row in table.rows]
    series = _line_series(block)
    if not series:
        return charts.empty_chart("그래프로 그릴 숫자 컬럼이 없습니다.")

    legend = ""
    if len(series) >= 2:
        legend = (
            '<div class="legend">'
            f'<span><i class="s1"></i>{_escape(series[0][0])}</span>'
            f'<span><i class="s2"></i>{_escape(series[1][0])}</span>'
            "</div>"
        )
    return legend + charts.line_chart(periods, series)


# ── 섹션 ───────────────────────────────────────────────────────────


def _render_block(block: BlockResult, number: int) -> str:
    chart = _render_chart(block)
    chart_html = f'<div class="chart-scroll">{chart}</div>' if chart.startswith("<svg") else chart
    subtitle = f'<p class="sub">{_escape(block.설명)}</p>' if block.설명 else ""

    body = _render_table(block)
    if not len(block.표):
        body = '<p class="sub">표시할 데이터가 없습니다.</p>'

    notes = ""
    if block.경고:
        items = "".join(f"<li>{_escape(w)}</li>" for w in block.경고)
        notes = f'<ul class="notes block">{items}</ul>'

    return (
        f'<section class="card"><h2>{number}. {_escape(block.이름)}</h2>'
        f"{subtitle}{chart_html}{body}{notes}</section>"
    )


def _notes_section(report: Report) -> str:
    if not report.warnings:
        return ""
    items = "".join(f"<li>{_escape(w)}</li>" for w in report.warnings)
    return f'<section class="card"><h2>확인이 필요한 사항</h2><ul class="notes">{items}</ul></section>'


def render_report(report: Report, title: str = "") -> str:
    """실행 결과를 자기완결형 HTML 문자열로 만든다."""
    template = report.template
    title = title or f"{template.이름} 보고서"
    generated = report.generated_at.strftime("%Y-%m-%d %H:%M")
    source = report.source or "(직접 입력)"

    scope = f"{report.row_count:,}행"
    if report.analyzed_count != report.row_count:
        scope = f"{report.row_count:,}행 중 {report.analyzed_count:,}행 분석"

    description = f"<br>{_escape(template.설명)}" if template.설명 else ""
    blocks = "\n".join(
        _render_block(block, number) for number, block in enumerate(report.blocks, start=1)
    )

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
    원본 <code>{_escape(source)}</code> · 시트 <code>{_escape(report.sheet)}</code>
    · {scope} · 생성 {generated}
    <br>적용 양식: <code>{_escape(template.이름)}</code>{description}
  </div>
</header>
{_tiles(report)}
{blocks}
{_notes_section(report)}
<footer class="doc">
  이 파일은 외부 인터넷 연결 없이 열람·인쇄할 수 있습니다. ·
  {_escape(report.generated_at.year)} 예산 분석기
</footer>
</div>
</body>
</html>
"""


def write_report(path: str, report: Report, title: str = "") -> str:
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(render_report(report, title))
    return path
