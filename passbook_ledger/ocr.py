"""통장 스캔 이미지 → 거래 내역 표 추출.

tesseract(설치돼 있어야 함) 의 TSV 출력(단어 단위 좌표)만으로 표 구조를 복원한다.
외부 파이썬 패키지(pytesseract 등)에 기대지 않고 표준 라이브러리 + tesseract 실행 파일만 쓴다.

정확도를 100% 보장하지 않는다. 낮은 신뢰도이거나 애매한 값은 빈 칸으로 남겨
사람이 스캔본을 보고 채우도록 한다 (자동 인식 실패를 조용히 틀린 값으로 채우지 않는다).
"""
from __future__ import annotations

import csv
import difflib
import io
import re
import shutil
import subprocess
from dataclasses import dataclass, field

# 표준 컬럼 순서와, 헤더 행에서 이 컬럼을 찾기 위한 키워드들.
COLUMN_KEYWORDS = [
    ("거래일자", ["거래일자", "거래일시", "거래일", "일자", "날짜"]),
    ("적요", ["적요", "거래내용", "내용", "거래구분"]),
    ("출금", ["찾으신금액", "출금액", "출금", "지급금액", "인출"]),
    ("입금", ["맡기신금액", "입금액", "입금", "수입금액"]),
    ("잔액", ["거래후잔액", "잔액", "거래후잔고", "잔고"]),
    ("메모", ["취급점", "메모", "비고", "거래점"]),
]

# 통장에 자주 나오는 적요 표현. OCR이 라틴+한글 혼용(CD 등)에서 자주 깨지므로,
# 비슷한 문자열이면 표준 표현으로 보정한다. 사전에 없으면 원문 그대로 두고
# 확인이 필요하다고만 표시한다(임의로 다른 뜻으로 바꾸지 않는다).
KNOWN_DESCRIPTIONS = [
    "당행CD입금", "당행CD지급", "타행CD입금", "타행CD지급",
    "외환카드대금", "카드대금", "결산이자", "이자", "대체",
    "자동이체", "급여", "수수료", "ATM출금", "ATM입금", "인터넷뱅킹",
]

NOISE_RE = re.compile(r"^[\s|.\-_~`'\"]+$")
DATE_RE = re.compile(r"\d{2,4}[-./년]\s?\d{1,2}[-./월]\s?\d{1,2}일?")
AMOUNT_RE = re.compile(r"[0-9][0-9,]*")

LOW_CONF = 60.0  # 이 미만 신뢰도의 칸은 빈 칸으로 남긴다.


@dataclass
class Word:
    block: int
    par: int
    line: int
    left: int
    top: int
    width: int
    height: int
    conf: float
    text: str

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height


@dataclass
class Cluster:
    left: int
    right: int
    top: int
    bottom: int
    text: str
    conf: float

    @property
    def center(self) -> float:
        return (self.left + self.right) / 2


def parse_tsv(tsv_text: str) -> list[Word]:
    """tesseract --tsv 출력에서 단어(level=5) 토큰만 뽑아 잡음을 제거한다."""
    reader = csv.reader(io.StringIO(tsv_text), delimiter="\t")
    header = next(reader, None)
    if not header:
        return []
    words: list[Word] = []
    for row in reader:
        if len(row) < 12:
            continue
        level = row[0]
        if level != "5":
            continue
        text = row[11]
        if not text or NOISE_RE.match(text):
            continue
        try:
            conf = float(row[10])
        except ValueError:
            conf = -1.0
        words.append(
            Word(
                block=int(row[2]),
                par=int(row[3]),
                line=int(row[4]),
                left=int(row[6]),
                top=int(row[7]),
                width=int(row[8]),
                height=int(row[9]),
                conf=conf,
                text=text,
            )
        )
    return words


def _group_lines(words: list[Word]) -> list[list[Word]]:
    groups: dict[tuple[int, int, int], list[Word]] = {}
    for w in words:
        groups.setdefault((w.block, w.par, w.line), []).append(w)
    lines = list(groups.values())
    for line in lines:
        line.sort(key=lambda w: w.left)
    lines.sort(key=lambda line: sum(w.top for w in line) / len(line))
    return lines


def _merge_line_into_clusters(line: list[Word]) -> list[Cluster]:
    """같은 줄에서 자간이 좁은 단어들을 하나의 칸(cell)으로 합친다.

    한글 음절이 tesseract에서 글자 단위로 쪼개져 인식되는 경우가 있어
    (예: '거래일자' -> '거','래','일','자'), 간격이 좁으면 이어 붙인다.
    """
    if not line:
        return []
    heights = [w.height for w in line]
    median_h = sorted(heights)[len(heights) // 2]
    gap_threshold = max(10, median_h * 0.9)

    clusters: list[Cluster] = []
    cur = Cluster(line[0].left, line[0].right, line[0].top, line[0].bottom, line[0].text, line[0].conf)
    confs = [line[0].conf]
    for w in line[1:]:
        gap = w.left - cur.right
        if gap <= gap_threshold:
            sep = " " if (cur.text[-1:].isascii() and cur.text[-1:].isalnum()
                          and w.text[:1].isascii() and w.text[:1].isalnum()) else ""
            cur.text += sep + w.text
            cur.right = max(cur.right, w.right)
            cur.top = min(cur.top, w.top)
            cur.bottom = max(cur.bottom, w.bottom)
            confs.append(w.conf)
        else:
            cur.conf = sum(c for c in confs if c >= 0) / max(1, len([c for c in confs if c >= 0]))
            clusters.append(cur)
            cur = Cluster(w.left, w.right, w.top, w.bottom, w.text, w.conf)
            confs = [w.conf]
    cur.conf = sum(c for c in confs if c >= 0) / max(1, len([c for c in confs if c >= 0]))
    clusters.append(cur)
    return clusters


def _normalize(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _keyword_score(cell_text: str, keywords: list[str]) -> float:
    norm = _normalize(cell_text)
    best = 0.0
    for kw in keywords:
        if kw == norm:
            return 1.0
        if kw in norm or norm in kw:
            best = max(best, 0.9)
        best = max(best, difflib.SequenceMatcher(None, norm, kw).ratio())
    return best


def _best_column_for_header_cell(cell_text: str) -> tuple[str, float]:
    scores = [(col_name, _keyword_score(cell_text, keywords)) for col_name, keywords in COLUMN_KEYWORDS]
    return max(scores, key=lambda s: s[1])


def _detect_header(
    lines: list[list[Cluster]],
) -> tuple[list[tuple[str, float, float]], int] | tuple[None, None]:
    """앞쪽 몇 줄 중 컬럼 제목이 3개 이상(서로 다른 컬럼으로) 매칭되는 줄을 헤더로 본다."""
    for idx, line in enumerate(lines[:4]):
        matched: dict[str, tuple[float, float, float]] = {}
        for cluster in line:
            col_name, score = _best_column_for_header_cell(cluster.text)
            if score < 0.75:
                continue
            prev = matched.get(col_name)
            if prev is None or score > prev[2]:
                matched[col_name] = (cluster.left, cluster.right, score)
        if len(matched) >= 3:
            result = [(name, left, right) for name, (left, right, _) in matched.items()]
            result.sort(key=lambda m: m[1])
            return result, idx
    return None, None


def _fallback_columns(lines: list[list[Cluster]], page_width: int) -> list[tuple[str, float, float]]:
    """헤더를 못 찾으면 전체 칸의 x좌표 간격이 큰 지점을 기준으로 등분한다."""
    centers = sorted(c.center for line in lines for c in line)
    n_cols = len(COLUMN_KEYWORDS)
    if len(centers) < n_cols:
        step = page_width / n_cols
        return [(name, i * step, (i + 1) * step) for i, (name, _) in enumerate(COLUMN_KEYWORDS)]
    gaps = [(centers[i + 1] - centers[i], i) for i in range(len(centers) - 1)]
    gaps.sort(reverse=True)
    splits = sorted(centers[i] + (centers[i + 1] - centers[i]) / 2 for _, i in gaps[: n_cols - 1])
    bounds = [0.0] + splits + [float(page_width)]
    return [(COLUMN_KEYWORDS[i][0], bounds[i], bounds[i + 1]) for i in range(n_cols)]


def _assign_columns(line: list[Cluster], columns: list[tuple[str, float, float]]) -> dict[str, list[Cluster]]:
    result: dict[str, list[Cluster]] = {name: [] for name, _, _ in columns}
    for cluster in line:
        best_name, best_overlap = None, -1.0
        for name, left, right in columns:
            overlap = min(cluster.right, right) - max(cluster.left, left)
            if overlap > best_overlap:
                best_overlap, best_name = overlap, name
        if best_name is not None:
            result[best_name].append(cluster)
    return result


def _cell_text(clusters: list[Cluster]) -> tuple[str, float]:
    if not clusters:
        return "", -1.0
    clusters = sorted(clusters, key=lambda c: c.left)
    text = "".join(c.text for c in clusters)
    confs = [c.conf for c in clusters if c.conf >= 0]
    conf = sum(confs) / len(confs) if confs else -1.0
    return text.strip(), conf


def _clean_amount(text: str) -> str:
    m = AMOUNT_RE.search(text.replace(" ", ""))
    return m.group(0) if m else ""


def _correct_description(text: str) -> tuple[str, bool]:
    """비슷한 표준 적요 표현이 있으면 보정하고, 없으면 원문을 그대로 둔다."""
    if not text:
        return "", False
    match = difflib.get_close_matches(text, KNOWN_DESCRIPTIONS, n=1, cutoff=0.55)
    if match:
        return match[0], match[0] != text
    return text, False


def page_width_from_tsv(tsv_text: str) -> int:
    for line in tsv_text.splitlines()[1:]:
        cols = line.split("\t")
        if len(cols) >= 9 and cols[0] == "1":
            try:
                return int(cols[8])
            except ValueError:
                break
    return 2000


def rows_from_tsv(tsv_text: str, page_width: int | None = None) -> list[dict]:
    """TSV 텍스트를 거래 행 목록(dict)으로 변환한다.

    각 행: 거래일자, 적요, 구분(수입/지급), 금액, 잔액, 메모, 확인필요(bool), 확인사유
    """
    if page_width is None:
        page_width = page_width_from_tsv(tsv_text)
    words = parse_tsv(tsv_text)
    if not words:
        return []
    lines = _group_lines(words)
    cluster_lines = [_merge_line_into_clusters(line) for line in lines]

    columns, header_line_index = _detect_header(cluster_lines)
    if columns is None:
        columns = _fallback_columns(cluster_lines, page_width)

    rows: list[dict] = []
    for idx, line in enumerate(cluster_lines):
        if idx == header_line_index:
            continue
        if not line:
            continue
        by_col = _assign_columns(line, columns)

        date_text, date_conf = _cell_text(by_col.get("거래일자", []))
        desc_text, desc_conf = _cell_text(by_col.get("적요", []))
        out_text, out_conf = _cell_text(by_col.get("출금", []))
        in_text, in_conf = _cell_text(by_col.get("입금", []))
        bal_text, bal_conf = _cell_text(by_col.get("잔액", []))
        memo_text, memo_conf = _cell_text(by_col.get("메모", []))

        if not any([date_text, desc_text, out_text, in_text, bal_text, memo_text]):
            continue

        needs_review: list[str] = []

        date_match = DATE_RE.search(date_text)
        date_value = date_match.group(0) if date_match else ""
        if not date_value or date_conf < LOW_CONF:
            needs_review.append("거래일자")
            if date_conf < LOW_CONF:
                date_value = ""

        desc_value, was_corrected = _correct_description(desc_text)
        if desc_conf < LOW_CONF or not desc_value:
            needs_review.append("적요")
        elif was_corrected:
            needs_review.append("적요(자동보정됨-확인)")

        out_amount = _clean_amount(out_text) if out_conf >= LOW_CONF else ""
        in_amount = _clean_amount(in_text) if in_conf >= LOW_CONF else ""

        if out_amount and in_amount:
            gubun, amount = "확인필요", ""
            needs_review.append("출금/입금 동시 인식")
        elif out_amount:
            gubun, amount = "지급", out_amount
        elif in_amount:
            gubun, amount = "수입", in_amount
        else:
            gubun, amount = "", ""
            needs_review.append("금액")

        balance = _clean_amount(bal_text) if bal_conf >= LOW_CONF else ""
        if not balance:
            needs_review.append("잔액")

        memo_value = memo_text if memo_conf >= LOW_CONF else ""

        rows.append(
            {
                "거래일자": date_value,
                "적요": desc_value,
                "구분": gubun,
                "금액": amount,
                "잔액": balance,
                "메모": memo_value,
                "확인필요": bool(needs_review),
                "확인사유": ", ".join(needs_review),
            }
        )
    return rows


def recognize_image(image_path: str, lang: str = "kor+eng") -> str:
    """tesseract 실행 파일을 호출해 TSV 텍스트를 얻는다. (외부 파이썬 패키지 불필요)"""
    tesseract = shutil.which("tesseract")
    if not tesseract:
        raise RuntimeError(
            "tesseract 실행 파일을 찾을 수 없습니다. Tesseract OCR(한국어 데이터 포함)을 "
            "먼저 설치해 주세요."
        )
    result = subprocess.run(
        [tesseract, image_path, "-", "--dpi", "300", "-l", lang, "tsv"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    return result.stdout
