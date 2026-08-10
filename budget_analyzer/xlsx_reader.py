"""표준 라이브러리만으로 .xlsx / .csv 를 읽는다.

xlsx 는 결국 XML 이 들어있는 zip 이라, openpyxl 없이 zipfile +
xml.etree 로 충분히 읽을 수 있다. 폐쇄망에 패키지를 설치할 필요를
없애기 위한 선택이다.

한계: .xls (BIFF 바이너리) 는 지원하지 않는다. 엑셀에서 .xlsx 로 저장 후 사용.
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import re
import zipfile
from xml.etree import ElementTree

from .table import Table

__all__ = ["read_workbook", "read_table", "sheet_names", "SpreadsheetError"]


class SpreadsheetError(Exception):
    """파일을 읽을 수 없을 때."""


# 엑셀 1900 날짜 체계의 기준일. 1900 윤년 버그 때문에 12/30 이 기준이 된다.
_EXCEL_EPOCH = _dt.datetime(1899, 12, 30)
_EXCEL_EPOCH_1904 = _dt.datetime(1904, 1, 1)

# 엑셀 내장 서식 중 날짜/시간에 해당하는 numFmtId.
_BUILTIN_DATE_FORMATS = set(range(14, 23)) | set(range(45, 48))
_DATE_FORMAT_HINT = re.compile(r"(?<!\\)[ymdhs]")
_KOREAN_ENCODINGS = ("utf-8-sig", "cp949", "euc-kr", "utf-16", "latin-1")


def _local(tag: str) -> str:
    """``{namespace}tag`` -> ``tag``."""
    return tag.rpartition("}")[2]


def _column_index(cell_ref: str) -> int:
    """``"BC12"`` -> 54 (0-based)."""
    index = 0
    for char in cell_ref:
        if not char.isalpha():
            break
        index = index * 26 + (ord(char.upper()) - 64)
    return index - 1


def _serial_to_datetime(serial: float, epoch: _dt.datetime) -> _dt.datetime:
    days = int(serial)
    fraction = serial - days
    return epoch + _dt.timedelta(days=days, seconds=round(fraction * 86400))


class _Workbook:
    """xlsx zip 을 열어 시트별 셀을 꺼내주는 내부 헬퍼."""

    def __init__(self, path: str) -> None:
        try:
            self.zip = zipfile.ZipFile(path)
        except zipfile.BadZipFile:
            raise SpreadsheetError(
                f"'{path}' 는 올바른 xlsx 파일이 아닙니다. "
                "구형 .xls 파일이면 엑셀에서 .xlsx 로 다시 저장해 주세요."
            ) from None
        self.epoch = _EXCEL_EPOCH
        self.shared_strings = self._read_shared_strings()
        self.date_styles = self._read_date_styles()
        self.sheets = self._read_sheet_index()

    def close(self) -> None:
        self.zip.close()

    def _parse(self, name: str) -> ElementTree.Element | None:
        try:
            with self.zip.open(name) as handle:
                return ElementTree.parse(handle).getroot()
        except KeyError:
            return None

    def _read_shared_strings(self) -> list[str]:
        root = self._parse("xl/sharedStrings.xml")
        if root is None:
            return []
        strings: list[str] = []
        for item in root:
            # <si> 안의 모든 <t> 를 이어붙인다. 서식이 섞이면 <r><t> 로 쪼개진다.
            parts = [node.text or "" for node in item.iter() if _local(node.tag) == "t"]
            strings.append("".join(parts))
        return strings

    def _read_date_styles(self) -> set[int]:
        """날짜 서식이 적용된 cellXfs 인덱스 집합."""
        root = self._parse("xl/styles.xml")
        if root is None:
            return set()

        custom_date_formats: set[int] = set()
        for node in root.iter():
            if _local(node.tag) != "numFmt":
                continue
            code = node.get("formatCode", "")
            # 따옴표로 감싼 리터럴은 서식 판별에서 제외한다.
            stripped = re.sub(r'"[^"]*"', "", code)
            if _DATE_FORMAT_HINT.search(stripped):
                custom_date_formats.add(int(node.get("numFmtId", "-1")))

        date_styles: set[int] = set()
        for parent in root.iter():
            if _local(parent.tag) != "cellXfs":
                continue
            for position, xf in enumerate(parent):
                fmt_id = int(xf.get("numFmtId", "0"))
                if fmt_id in _BUILTIN_DATE_FORMATS or fmt_id in custom_date_formats:
                    date_styles.add(position)
        return date_styles

    def _read_sheet_index(self) -> list[tuple[str, str]]:
        """[(시트명, zip 내부 경로)] 를 워크북 순서대로."""
        root = self._parse("xl/workbook.xml")
        if root is None:
            raise SpreadsheetError("xl/workbook.xml 이 없습니다. 손상된 파일로 보입니다.")

        for node in root.iter():
            if _local(node.tag) == "workbookPr" and node.get("date1904") in ("1", "true"):
                self.epoch = _EXCEL_EPOCH_1904

        rels: dict[str, str] = {}
        rels_root = self._parse("xl/_rels/workbook.xml.rels")
        if rels_root is not None:
            for node in rels_root:
                rel_id, target = node.get("Id"), node.get("Target", "")
                if not rel_id:
                    continue
                target = target.lstrip("/")
                if not target.startswith("xl/"):
                    target = "xl/" + target
                rels[rel_id] = target

        names = set(self.zip.namelist())
        sheets: list[tuple[str, str]] = []
        for node in root.iter():
            if _local(node.tag) != "sheet":
                continue
            name = node.get("name") or f"Sheet{len(sheets) + 1}"
            rel_id = next(
                (v for k, v in node.attrib.items() if _local(k) == "id"), None
            )
            path = rels.get(rel_id or "")
            if path and path in names:
                sheets.append((name, path))

        if not sheets:  # 관계 파일이 깨진 경우의 대비책.
            sheets = [
                (n.rsplit("/", 1)[-1].removesuffix(".xml"), n)
                for n in sorted(names)
                if n.startswith("xl/worksheets/") and n.endswith(".xml")
            ]
        if not sheets:
            raise SpreadsheetError("워크시트를 찾지 못했습니다.")
        return sheets

    def cells(self, sheet_path: str) -> list[list[object]]:
        """시트를 행 리스트로 읽는다. 빈 셀은 None."""
        with self.zip.open(sheet_path) as handle:
            grid: list[list[object]] = []
            for _, element in ElementTree.iterparse(handle, events=("end",)):
                if _local(element.tag) != "row":
                    continue
                values: list[object] = []
                for cell in element:
                    if _local(cell.tag) != "c":
                        continue
                    position = _column_index(cell.get("r", "")) if cell.get("r") else len(values)
                    if position < 0:
                        position = len(values)
                    while len(values) < position:
                        values.append(None)
                    values.append(self._cell_value(cell))
                grid.append(values)
                element.clear()
        return grid

    def _cell_value(self, cell: ElementTree.Element) -> object:
        cell_type = cell.get("t")

        if cell_type == "inlineStr":
            parts = [n.text or "" for n in cell.iter() if _local(n.tag) == "t"]
            return "".join(parts) or None

        raw = None
        for child in cell:
            if _local(child.tag) == "v":
                raw = child.text
                break
        if raw is None:
            return None

        if cell_type == "s":
            try:
                return self.shared_strings[int(raw)]
            except (ValueError, IndexError):
                return raw
        if cell_type in ("str", "e"):
            return raw
        if cell_type == "b":
            return raw == "1"

        try:
            number = float(raw)
        except ValueError:
            return raw

        style = cell.get("s")
        if style is not None and int(style) in self.date_styles and 0 < number < 2958466:
            # 상한은 엑셀 날짜 체계의 최댓값(9999-12-31). 날짜 서식이 걸린 셀이라도
            # 실제 값이 금액처럼 그 범위를 벗어나면 날짜가 아니라 숫자로 취급한다.
            try:
                moment = _serial_to_datetime(number, self.epoch)
            except (OverflowError, OSError, ValueError):
                pass
            else:
                return moment.date() if moment.time() == _dt.time(0, 0) else moment

        return int(number) if number.is_integer() else number


def sheet_names(path: str) -> list[str]:
    """엑셀 파일의 시트 이름 목록. csv 는 ``["(csv)"]``."""
    if path.lower().endswith((".csv", ".tsv", ".txt")):
        return ["(csv)"]
    workbook = _Workbook(path)
    try:
        return [name for name, _ in workbook.sheets]
    finally:
        workbook.close()


def read_workbook(path: str) -> dict[str, list[list[object]]]:
    """모든 시트를 ``{시트명: 행 리스트}`` 로 읽는다."""
    workbook = _Workbook(path)
    try:
        return {name: workbook.cells(sheet_path) for name, sheet_path in workbook.sheets}
    finally:
        workbook.close()


def _read_csv(path: str) -> list[list[object]]:
    """한글 엑셀이 흔히 뱉는 cp949 까지 순서대로 시도한다."""
    last_error: Exception | None = None
    for encoding in _KOREAN_ENCODINGS:
        try:
            with open(path, "r", encoding=encoding, newline="") as handle:
                text = handle.read()
            break
        except (UnicodeDecodeError, LookupError) as error:
            last_error = error
    else:
        raise SpreadsheetError(f"'{path}' 인코딩을 인식하지 못했습니다: {last_error}")

    sample = text[:8192]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",\t;|")
        delimiter = dialect.delimiter
    except csv.Error:
        delimiter = "\t" if path.lower().endswith(".tsv") else ","

    return [list(row) for row in csv.reader(io.StringIO(text), delimiter=delimiter)]


def _find_header_row(grid: list[list[object]], scan_depth: int = 25) -> int:
    """제목/공백 줄을 건너뛰고 실제 머리글 행을 고른다.

    머리글은 대체로 (1) 문자열 셀이 많고 (2) 아래 행에 숫자가 많다.
    두 조건을 점수화해 가장 높은 행을 고른다.
    """
    best_row, best_score = 0, float("-inf")
    limit = min(scan_depth, len(grid))

    for index in range(limit):
        row = grid[index]
        labels = [c for c in row if isinstance(c, str) and c.strip()]
        if len(labels) < 2:
            continue
        filled = sum(1 for c in row if c is not None and str(c).strip())
        numeric_here = sum(1 for c in row if isinstance(c, (int, float)) and not isinstance(c, bool))

        below = grid[index + 1 : index + 6]
        numeric_below = sum(
            1
            for line in below
            for cell in line
            if isinstance(cell, (int, float)) and not isinstance(cell, bool)
        )
        width_below = max((len(line) for line in below), default=0)

        # 머리글 자신은 숫자가 없어야 하고, 아래는 숫자가 많고 폭이 비슷해야 한다.
        score = (
            len(labels) * 2.0
            + min(numeric_below, 30) * 0.8
            + (2.0 if width_below and abs(width_below - filled) <= 1 else 0.0)
            - numeric_here * 1.5
            - index * 0.4
        )
        if score > best_score:
            best_row, best_score = index, score

    return best_row


def _clean_headers(raw: list[object]) -> list[str]:
    """빈 머리글과 중복 머리글을 살려 쓸 수 있는 이름으로 바꾼다."""
    headers: list[str] = []
    seen: dict[str, int] = {}
    for position, cell in enumerate(raw):
        name = "" if cell is None else re.sub(r"\s+", " ", str(cell)).strip()
        if not name:
            name = f"컬럼{position + 1}"
        if name in seen:
            seen[name] += 1
            name = f"{name}_{seen[name]}"
        else:
            seen[name] = 0
        headers.append(name)
    return headers


def read_table(
    path: str,
    sheet: str | None = None,
    header_row: int | None = None,
) -> Table:
    """엑셀/CSV 한 시트를 :class:`Table` 로 읽는다.

    ``header_row`` 를 주지 않으면 머리글 위치를 자동으로 찾는다 (0-based).
    """
    if path.lower().endswith((".csv", ".tsv", ".txt")):
        grid = _read_csv(path)
        name = sheet or "(csv)"
    else:
        sheets = read_workbook(path)
        if sheet is None:
            # 내용이 가장 많은 시트를 기본으로 (표지 시트를 피하기 위해).
            name = max(sheets, key=lambda key: sum(len(r) for r in sheets[key]))
        elif sheet in sheets:
            name = sheet
        else:
            raise SpreadsheetError(
                f"'{sheet}' 시트가 없습니다. 사용 가능: {list(sheets)}"
            )
        grid = sheets[name]

    grid = [row for row in grid if any(c is not None and str(c).strip() for c in row)]
    if not grid:
        raise SpreadsheetError(f"'{path}' 에서 읽을 데이터가 없습니다.")

    if header_row is None:
        header_row = _find_header_row(grid)
    header_row = max(0, min(header_row, len(grid) - 1))

    width = max(len(row) for row in grid[header_row:])
    raw_headers = list(grid[header_row]) + [None] * (width - len(grid[header_row]))
    headers = _clean_headers(raw_headers)

    table = Table(headers, grid[header_row + 1 :], name=name)
    return table.drop_empty_rows()
