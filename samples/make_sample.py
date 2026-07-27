"""테스트·시연용 예산 엑셀 샘플을 만든다.

실무 파일에서 흔한 특징을 일부러 섞어 넣었다:
  · 맨 위 제목 줄 + 빈 줄 (머리글이 1행이 아님)
  · 문자열로 들어간 금액("1,200,000")
  · 날짜 셀과 문자열 날짜 혼재
  · 예산 없이 집행만 있는 항목

    python samples/make_sample.py            # samples/예산_샘플.xlsx 생성
"""

from __future__ import annotations

import datetime as _dt
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from budget_analyzer.table import Table  # noqa: E402
from budget_analyzer.xlsx_writer import write_xlsx  # noqa: E402

DEPARTMENTS = {
    "기획조정실": ["정책연구용역", "성과평가", "법무자문"],
    "총무과": ["청사관리", "차량운영", "사무용품"],
    "정보화담당관": ["전산장비 임차", "보안관제", "홈페이지 유지보수"],
    "복지정책과": ["취약계층 지원", "경로당 운영", "돌봄서비스"],
    "도시안전과": ["도로보수", "CCTV 확충", "재난대비 물자"],
    "문화체육과": ["시민축제", "도서관 운영", "생활체육 지원"],
}
ACCOUNTS = ["일반운영비", "여비", "업무추진비", "자산취득비", "민간이전", "시설비"]


def build_rows(seed: int = 20260727) -> list[list[object]]:
    random.seed(seed)
    rows: list[list[object]] = []
    serial = 1

    for department, projects in DEPARTMENTS.items():
        for project in projects:
            account = random.choice(ACCOUNTS)
            budget = random.randrange(8, 320) * 1_000_000

            # 집행률은 항목마다 다르게 — 부진/정상/초과가 모두 나오도록.
            ratio = random.choice([0.32, 0.55, 0.68, 0.81, 0.9, 0.97, 1.0, 1.08, 1.21])
            remaining = int(budget * ratio)

            months = sorted(random.sample(range(1, 13), random.randint(3, 7)))
            for position, month in enumerate(months):
                last = position == len(months) - 1
                spent = remaining if last else int(remaining / (len(months) - position) * random.uniform(0.6, 1.4))
                spent = max(0, min(spent, remaining))
                remaining -= spent

                day = random.randint(1, 28)
                date: object = _dt.date(2026, month, day)
                if serial % 7 == 0:  # 일부러 문자열 날짜를 섞는다.
                    date = f"2026-{month:02d}-{day:02d}"

                amount: object = spent
                if serial % 5 == 0:  # 일부러 문자열 금액을 섞는다.
                    amount = f"{spent:,}"

                rows.append(
                    [
                        serial,
                        department,
                        project,
                        account,
                        budget if position == 0 else 0,
                        amount,
                        date,
                        "정기" if month % 2 else "수시",
                    ]
                )
                serial += 1

    # 예산 없이 집행만 있는 항목 (실무에서 자주 문제가 되는 케이스).
    for month in (5, 9):
        rows.append(
            [
                serial,
                "총무과",
                "예비비 집행",
                "일반운영비",
                0,
                random.randrange(3, 20) * 1_000_000,
                _dt.date(2026, month, 15),
                "수시",
            ]
        )
        serial += 1

    return rows


def main() -> None:
    columns = ["연번", "부서", "세부사업", "계정과목", "예산액", "집행액", "집행일자", "구분"]
    data = build_rows()

    # writer 는 첫 행을 머리글로 쓰므로, 그 자리에 제목 줄을 넣어
    # "머리글이 3행에 있는" 실제 양식을 재현한다.
    title = ["2026년도 부서별 예산 집행 현황"] + [""] * (len(columns) - 1)
    body = [[None] * len(columns), columns] + data

    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "예산_샘플.xlsx")
    write_xlsx(path, [Table(title, body, "집행내역")])
    print(f"샘플 생성: {path}  ({len(data):,}행)")


if __name__ == "__main__":
    main()
