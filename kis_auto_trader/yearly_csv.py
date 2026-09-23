"""날짜 기준으로 계속 불어나는 표를 연도별 CSV 파일에 나눠 담는 저장소.

(2026-09-14 신설) panel.py(일봉)와 fundamentals.py(PER/PBR 등 일별 재무지표)가
똑같은 저장 방식을 쓰는데, 그 코드를 양쪽에 복사해두면 한쪽만 고치는 실수가
난다. 예전에 virtual_trades.csv 에서 컬럼을 가운데 끼워넣었다가 기존 행 16개가
조용히 밀려 읽히는 사고가 있었어서, 이런 중복은 아예 안 만드는 쪽이 낫다.

연도별로 나누는 이유: 한 파일에 다 넣으면 매일 수십 MB짜리 파일이 통째로
다시 커밋돼서 저장소가 금방 불어난다. 나누면 매일 바뀌는 건 올해 파일 하나뿐이고
지난 연도는 그대로 멈춰 있다.

컬럼을 추가할 때 규칙: 반드시 FIELDNAMES 의 '맨 끝'에 붙인다. 파일을 다시 쓸 때
헤더도 같이 새로 쓰기 때문에 순서가 바뀌면 기존 파일과 어긋난다 - 아래
check_header 가 그걸 발견해서 알려준다.
"""
import csv


def paths(data_dir, prefix: str) -> list:
    if not data_dir.exists():
        return []
    return sorted(data_dir.glob(f"{prefix}_*.csv"))


def load_rows(data_dir, prefix: str, key_fields=("date", "code")) -> dict:
    """저장된 전부를 {(키...): row} 로 읽는다."""
    out: dict[tuple, dict] = {}
    for path in paths(data_dir, prefix):
        with open(path, encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if all(r.get(k) for k in key_fields):
                    out[tuple(r[k] for k in key_fields)] = r
    return out


def check_header(data_dir, prefix: str, fieldnames: list) -> list:
    """기존 파일 헤더가 지금 코드의 컬럼 순서와 다르면 그 파일 목록을 돌려준다."""
    bad = []
    for path in paths(data_dir, prefix):
        try:
            with open(path, encoding="utf-8-sig", newline="") as f:
                header = next(csv.reader(f), None)
        except Exception:
            continue
        if header is not None and header != fieldnames:
            bad.append(path.name)
    return bad


def write_years(data_dir, prefix: str, fieldnames: list, all_rows: dict,
                touched_years: set) -> None:
    """바뀐 연도 파일만 다시 쓴다. 임시파일에 쓰고 바꿔치기해서, 쓰는 도중
    프로그램이 죽어도 기존 파일이 깨지지 않게 한다."""
    data_dir.mkdir(exist_ok=True)
    by_year: dict[str, list[dict]] = {}
    for row in all_rows.values():
        year = row["date"][:4]
        if year in touched_years:
            by_year.setdefault(year, []).append(row)

    for year, rows in by_year.items():
        rows.sort(key=lambda r: (r["date"], r.get("code", "")))
        path = data_dir / f"{prefix}_{year}.csv"
        tmp = path.with_suffix(".csv.tmp")
        with open(tmp, "w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in fieldnames})
        tmp.replace(path)


def append(data_dir, prefix: str, fieldnames: list, new_rows: list,
           key_fields=("date", "code")) -> int:
    """행들을 저장소에 합친다. 키가 같으면 새 값으로 덮어쓴다.

    덮어쓰는 이유: 장중에 조회한 오늘 행은 그 시점까지의 값이라 미완성이다.
    다음 날 다시 받아서 덮어써야 제대로 된 값이 된다.

    반환값은 '새로 생긴 행 수'(덮어쓴 건 세지 않음).
    """
    if not new_rows:
        return 0
    bad = check_header(data_dir, prefix, fieldnames)
    if bad:
        print(f"[!!!] {bad} 의 컬럼 순서가 지금 코드({fieldnames})와 다릅니다. "
              f"컬럼을 가운데 끼워넣으면 기존 데이터가 밀려 읽힙니다 - "
              f"새 컬럼은 항상 맨 끝에 붙이고, 기존 파일은 따로 변환해야 합니다.")
    existing = load_rows(data_dir, prefix, key_fields)
    before = len(existing)
    touched = set()
    for r in new_rows:
        existing[tuple(r[k] for k in key_fields)] = r
        touched.add(r["date"][:4])
    write_years(data_dir, prefix, fieldnames, existing, touched)
    return len(existing) - before


class StreamWriter:
    """대량 수집 전용: 연도별 파일에 그냥 이어 쓴다 (전체 로드 없이).

    (2026-09-15 추가) append() 는 쓸 때마다 저장된 전체를 dict 으로 읽어서 합친
    뒤 다시 쓴다. 하루치 몇백 행이면 괜찮지만, KRX 과거 수집처럼 226만 행을
    넣을 때는 이게 O(n^2)이 되어 사실상 안 끝난다 (후반엔 한 번에 1GB 가까이
    메모리에 올린다). 그래서 대량 수집은 이 클래스로 흘려보낸다.

    중복 제거를 안 하므로, 같은 (날짜,종목)을 두 번 쓰지 않는 쪽에서 보장해야
    한다. 종목마다 한 번씩만 받아오는 수집에는 그 조건이 자연히 성립한다.
    정렬도 안 한다 - 읽는 쪽(backtest.Panel)이 종목별로 날짜순 정렬을 하므로
    파일 순서는 상관없다.
    """

    def __init__(self, data_dir, prefix: str, fieldnames: list):
        self.data_dir = data_dir
        self.prefix = prefix
        self.fieldnames = fieldnames
        self._writers: dict = {}
        self._files: dict = {}
        data_dir.mkdir(exist_ok=True)

    def _writer_for(self, year: str):
        if year not in self._writers:
            path = self.data_dir / f"{self.prefix}_{year}.csv"
            is_new = not path.exists() or path.stat().st_size == 0
            f = open(path, "a", encoding="utf-8-sig", newline="")
            w = csv.DictWriter(f, fieldnames=self.fieldnames)
            if is_new:
                w.writeheader()
            self._files[year] = f
            self._writers[year] = w
        return self._writers[year]

    def write_rows(self, rows: list) -> int:
        for r in rows:
            w = self._writer_for(r["date"][:4])
            w.writerow({k: r.get(k, "") for k in self.fieldnames})
        return len(rows)

    def flush(self):
        for f in self._files.values():
            f.flush()

    def close(self):
        for f in self._files.values():
            f.close()
        self._writers.clear()
        self._files.clear()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()


def codes_in(data_dir, prefix: str) -> set:
    """저장된 종목코드 집합만 빠르게 읽는다 (행 전체를 dict 으로 안 올림).

    coverage() 는 모든 행을 메모리에 올리므로 226만 행에서는 못 쓴다.
    '이 종목 이미 받았나'만 알면 되는 경우를 위한 가벼운 버전.
    """
    out = set()
    for path in paths(data_dir, prefix):
        with open(path, encoding="utf-8-sig", newline="") as f:
            r = csv.reader(f)
            header = next(r, None)
            if not header or "code" not in header:
                continue
            ci = header.index("code")
            for row in r:
                if len(row) > ci:
                    out.add(row[ci])
    return out


def coverage(data_dir, prefix: str) -> dict:
    """{code: (첫날, 마지막날, 행수)}"""
    acc: dict[str, list] = {}
    for (date, code) in load_rows(data_dir, prefix):
        cur = acc.get(code)
        if cur is None:
            acc[code] = [date, date, 1]
        else:
            cur[0] = min(cur[0], date)
            cur[1] = max(cur[1], date)
            cur[2] += 1
    return {c: tuple(v) for c, v in acc.items()}
