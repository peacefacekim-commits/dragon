"""관찰 대상 종목 집합(유니버스)을 한 번 정해서 파일에 고정해두고 계속 쓴다.

(2026-09-13 신설) 왜 필요한가:

지금까지 관찰 종목은 screener 가 "그날 상승률 상위 + 하락률 상위"에서 매일
새로 뽑았다. 그래서 실제로 쌓인 candidate_snapshot.csv 를 열어보면 4거래일
동안 등장한 101종목 중 4일 모두 나온 종목이 6개뿐이다. 매일 다른 종목을
보고 있었으니 "같은 종목을 계속 추적한 기록"이 사실상 없고, 그 상태로는
"이 신호가 한 달 뒤 수익으로 이어지는가" 같은 질문에 답할 수가 없다.
게다가 "오늘 많이 움직인 종목"만 뽑히니 표본 자체에 편향이 걸린다.

그래서 유니버스를 한 번 만들어 universe.json 에 얼려두고, 그 뒤로는 매일
같은 종목들을 본다. 종목이 바뀌지 않아야 패널 데이터(panel.py)가 쌓인다.

무엇으로 채우는가 (2026-09-14 변경 - 중요):

원래는 screener._base_candidates, 즉 "그날 등락률 상위/하위"로 채웠다. 그런데
실제 데이터를 보니 그게 바로 문제의 출처였다. 9/4·9/8·9/9·9/14 네 거래일의
10분 간격 장중 가격(92 종목-일)으로 확인한 결과, 그렇게 뽑힌 종목들은
09:30부터 장 마감까지 평균 -1.03% 흘렀고, 코스닥이 오른 날에도 지수 대비
1~2%p 뒤쳐졌다. "오늘 크게 튄 종목"은 튄 뒤에 되밀리기 때문이다.

유니버스는 한 번 차면 다시 안 바뀌므로, 그 편향이 박제된다. 그래서 채우는
출처를 거래대금/거래량 상위로 바꿨다. 등락률과 달리 "오늘 얼마나 움직였나"가
아니라 "얼마나 크고 활발하게 거래되나"로 뽑히므로, 급등락주 쏠림이 훨씬 덜하다.

  1순위: 거래대금/거래량 상위 (_liquid_candidates)
  2순위: 등락률 상위/하위 (screener._base_candidates) - 1순위가 실패할 때만

종목마다 어느 출처에서 들어왔는지 universe.json 에 같이 적는다. 나중에
"이 유니버스가 편향된 출처로 채워졌나"를 결과와 대조할 수 있어야 하기 때문이다.

한계 (결과를 볼 때 같이 생각해야 하는 것):

- 거래대금 상위도 편향이 없는 건 아니다. "2026년 9월에 크고 활발했던 종목"이
  들어가므로, 그때까지 살아남은 종목만 뽑힌다(생존 편향). 이 유니버스로 돌린
  과거 백테스트 성적은 실제보다 좋게 나오는 쪽으로 치우친다.
- 순위 API가 한 번에 주는 종목 수가 목표치보다 적어서, 목표 개수를 채울
  때까지는 실행할 때마다 새 종목을 더한다(add-only). 한 번 들어온 종목은
  빠지지 않고, 목표 개수를 채우면 그 뒤로는 건드리지 않는다.

사용법:
  python universe.py            # 현재 상태 출력 (출처별 집계 포함)
  python universe.py --build    # 목표 개수까지 종목을 더 채운다 (여러 번 실행 가능)
  python universe.py --reset    # 처음부터 다시 채운다 (잘못 채워졌을 때)
"""
import json
from datetime import datetime

import blocklist
from auth import get_access_token
from common import BASE_DIR, Config, load_config

UNIVERSE_PATH = BASE_DIR / "universe.json"

# 유니버스에 넣지 않을 종목 (파생/레버리지 상품 등)
EXCLUDE_KEYWORDS = ["레버리지", "인버스", "곱버스", "2X", "3X", "ETN", "선물"]

# 거래대금 하한 (원). 너무 안 거래되는 종목은 체결 자체가 어렵다.
MIN_TRADE_VALUE = 3_000_000_000

# 거래량순위 API를 어떤 조합으로 부를지.
# (시장, 순위기준) - 한 번 호출로 오는 종목 수가 한정적이라, 코스피/코스닥을
# 나누고 거래량순/거래대금순을 각각 받아서 합쳐야 목표 개수를 채울 수 있다.
#   FID_INPUT_ISCD: 0000 전체 / 0001 코스피 / 1001 코스닥
#   FID_BLNG_CLS_CODE: 0 평균거래량 / 3 거래금액순
VOLUME_RANK_QUERIES = [
    ("0001", "3"),  # 코스피 거래금액순
    ("1001", "3"),  # 코스닥 거래금액순
    ("0001", "0"),  # 코스피 평균거래량
    ("1001", "0"),  # 코스닥 평균거래량
]


def _volume_rank(cfg: Config, market: str, blng: str) -> list[dict]:
    """거래량/거래대금 순위 조회.

    (2026-09-15) 이 TR(FHPST01710000)과 파라미터는 실전 계좌로 동작을 확인했다.
    한 번 실행에 54종목이 들어왔고, SK하이닉스/삼성전자/현대차/KB금융 같은
    대형주와 알테오젠/HPSP/심텍 같은 중소형주가 섞여 들어왔다 - 등락률 순위로
    뽑을 때 나오던 급등락 소형주 쏠림이 없어진 것을 눈으로 확인했다.

    그래도 실패 시 등락률 순위로 되돌아가는 경로는 남겨둔다 (장중이 아니거나
    거래소 일시 오류인 날에도 그날 수집이 통째로 비지 않게).
    """
    import requests

    res = requests.get(
        f"{cfg.base_url}/uapi/domestic-stock/v1/quotations/volume-rank",
        headers={
            "content-type": "application/json; charset=utf-8",
            "authorization": f"Bearer {get_access_token(cfg)}",
            "appkey": cfg.app_key,
            "appsecret": cfg.app_secret,
            "tr_id": "FHPST01710000",
            "custtype": "P",
        },
        params={
            "FID_COND_MRKT_DIV_CODE": "J",
            "FID_COND_SCR_DIV_CODE": "20171",
            "FID_INPUT_ISCD": market,
            "FID_DIV_CLS_CODE": "0",
            "FID_BLNG_CLS_CODE": blng,
            "FID_TRGT_CLS_CODE": "1111111111",
            "FID_TRGT_EXLS_CLS_CODE": "0000000000",
            "FID_INPUT_PRICE_1": "",
            "FID_INPUT_PRICE_2": "",
            "FID_VOL_CNT": "",
            "FID_INPUT_DATE_1": "",
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()
    if body.get("rt_cd") != "0":
        raise RuntimeError(f"거래량순위 조회 실패: {body.get('msg1')}")
    return body.get("output", [])


def _liquid_candidates(cfg: Config) -> tuple[list[dict], str]:
    """거래대금/거래량 상위 종목. 실패하면 등락률 순위로 되돌아간다.

    반환: (후보 목록, 실제로 쓴 출처 이름)
    """
    out, seen = [], set()
    errors = []
    for market, blng in VOLUME_RANK_QUERIES:
        try:
            rows = _volume_rank(cfg, market, blng)
        except Exception as e:
            errors.append(f"{market}/{blng}: {e}")
            continue
        for r in rows:
            # 응답의 종목코드 필드명이 순위 API마다 달라서 둘 다 받아준다.
            code = r.get("mksc_shrn_iscd") or r.get("stck_shrn_iscd")
            name = r.get("hts_kor_isnm")
            if not code or not name or code in seen:
                continue
            try:
                price = float(r["stck_prpr"])
                volume = int(r.get("acml_vol", 0))
            except (KeyError, ValueError, TypeError):
                continue
            if price <= 0 or price * volume < MIN_TRADE_VALUE:
                continue
            seen.add(code)
            out.append({"code": code, "name": name, "price": price,
                        "trade_value": price * volume})

    if out:
        # 거래대금 큰 순으로 - 목표 개수를 채울 때 큰 종목부터 들어가게
        out.sort(key=lambda c: -c["trade_value"])
        return out, "거래대금상위"

    print(f"[유니버스] 거래대금 순위 조회가 전부 실패해서 등락률 순위로 되돌아갑니다. "
          f"({'; '.join(errors[:2]) if errors else '응답이 비어 있음'})")
    print("[유니버스] 주의: 등락률 순위로 채운 종목은 '그날 크게 움직인 종목' 쪽으로 "
          "치우칩니다. 나중에 결과를 볼 때 이걸 감안해야 합니다.")
    import screener
    return screener._base_candidates(cfg), "등락률상위(대체)"


def _empty() -> dict:
    return {
        "built_at": None,
        "note": "고정 유니버스. 손으로 종목을 더하거나 빼도 된다 (code/name 만 맞으면 됨).",
        "stocks": [],
    }


# (2026-09-14) 출처 기록이 없는 종목에 붙이는 이름. 출처를 적기 시작한 건
# 2026-09-14 부터이고, 그 전 코드는 screener._base_candidates(= 등락률 상위/하위)
# 하나만 썼다. 그래서 "기록 없음"은 곧 등락률 출처라는 뜻이다 - 편향 여부를
# 따질 때 '모름'으로 남겨두면 안 되므로 명시적으로 이름을 붙인다.
LEGACY_SOURCE = "등락률상위(초기)"


def load() -> dict:
    if not UNIVERSE_PATH.exists():
        return _empty()
    with open(UNIVERSE_PATH, encoding="utf-8") as f:
        data = json.load(f)
    data.setdefault("stocks", [])
    for s in data["stocks"]:
        s.setdefault("source", LEGACY_SOURCE)
    return data


def codes(source: str | None = None) -> list[str]:
    """유니버스 종목코드. source 를 주면 그 출처로 들어온 종목만."""
    return [s["code"] for s in load()["stocks"]
            if source is None or s.get("source") == source]


def save(data: dict) -> None:
    data["built_at"] = datetime.now().isoformat(timespec="seconds")
    tmp = UNIVERSE_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(UNIVERSE_PATH)


def _acceptable(cand: dict, cfg: Config) -> bool:
    if blocklist.is_blocked(cand["code"]):
        return False
    if any(kw in cand["name"] for kw in EXCLUDE_KEYWORDS):
        return False
    if cfg.min_stock_price > 0 and cand.get("price", 0) < cfg.min_stock_price:
        return False
    return True


def top_up(cfg: Config, target: int | None = None, verbose: bool = True) -> dict:
    """목표 개수에 못 미치면 종목을 더 채운다. 이미 목표를 채웠으면 아무것도 안 한다.

    이미 들어있는 종목은 절대 빼지 않는다 - 유니버스가 흔들리면 패널 데이터를
    쌓는 의미 자체가 없어지기 때문이다.
    """
    target = target or cfg.universe_size
    data = load()
    have = {s["code"] for s in data["stocks"]}

    if len(have) >= target:
        if verbose:
            print(f"[유니버스] 이미 {len(have)}종목 (목표 {target}) - 그대로 둡니다.")
        return data

    try:
        candidates, source = _liquid_candidates(cfg)
    except Exception as e:
        print(f"[유니버스] 후보 조회 실패 - 이번에는 채우지 않고 넘어갑니다: {e}")
        return data

    added = 0
    for c in candidates:
        if len(have) >= target:
            break
        if c["code"] in have or not _acceptable(c, cfg):
            continue
        # 어느 출처에서 들어온 종목인지 같이 남긴다 - 나중에 편향된 출처로
        # 채워진 종목이 섞여 있는지 결과와 대조할 수 있어야 하므로.
        data["stocks"].append({
            "code": c["code"], "name": c["name"],
            "source": source,
            "added_at": datetime.now().strftime("%Y-%m-%d"),
        })
        have.add(c["code"])
        added += 1

    if added:
        save(data)

    if verbose:
        print(f"[유니버스] {added}종목 추가 (출처: {source}) -> 현재 {len(have)}종목 (목표 {target})")
        if len(have) < target:
            # (2026-09-19 정정) 원래 여기서 무조건 "며칠에 걸쳐 채워집니다" 라고
            # 안내했는데, 이번에 0종목 추가가 나오는 걸 보고 그게 틀렸다는 걸
            # 알았다. 순위 API 는 매일 거의 같은 이름을 돌려주므로, 후보를
            # 받았는데도 0종목이 추가됐다면 그건 "아직 덜 받았다" 가 아니라
            # "이 출처로는 여기까지" 라는 뜻이다. 기다려도 안 채워진다.
            print(f"[유니버스] 아직 {target - len(have)}종목 모자랍니다.")
            if added == 0 and candidates:
                print(f"[유니버스] 후보 {len(candidates)}개를 받았는데 새로 들어갈 종목이 "
                      f"없었습니다 - 순위 API 가 매일 거의 같은 이름을 주므로 "
                      f"{len(have)}종목에서 더 안 늘어납니다. 기다려도 채워지지 "
                      f"않으니, 목표를 낮추거나 universe.json 에 직접 추가해야 합니다.")
                print(f"[유니버스] 참고: 전략/백테스트는 이 목록이 아니라 "
                      f"krx_panel(전 종목)에서 종목을 다시 뽑으므로, 이 부족분이 "
                      f"전략에 영향을 주지는 않습니다.")
            else:
                print(f"[유니버스] 순위 API가 하루에 주는 종목 수가 한정적이라, "
                      f"며칠에 걸쳐 채워집니다 (매일 자동 실행 시 알아서 채움).")
    return data


def source_counts() -> dict:
    """출처별 종목 수. 편향된 대체 출처가 섞였는지 한눈에 보려고."""
    counts: dict[str, int] = {}
    for s in load()["stocks"]:
        key = s.get("source", "(출처 기록 없음)")
        counts[key] = counts.get(key, 0) + 1
    return counts


def main():
    import argparse
    parser = argparse.ArgumentParser(description="고정 유니버스 관리")
    parser.add_argument("--build", action="store_true", help="목표 개수까지 종목을 더 채운다")
    parser.add_argument("--size", type=int, default=None, help="목표 종목 수 (기본: config.yaml)")
    parser.add_argument("--reset", action="store_true",
                        help="유니버스를 비우고 처음부터 다시 채운다 (잘못 채워졌을 때)")
    args = parser.parse_args()

    cfg = load_config()
    if args.reset:
        n = len(load()["stocks"])
        save(_empty())
        print(f"[유니버스] {n}종목을 비웠습니다. --build 로 다시 채우세요.")
        print("[유니버스] 주의: 이미 받아둔 일봉(data/panel_*.csv)은 그대로 남습니다. "
              "빠진 종목의 일봉도 남아 있지만, 백테스트는 패널에 있는 종목을 다 쓰므로 "
              "섞이는 게 싫으면 data/ 를 비우고 다시 받으세요.")
        return
    if args.build:
        top_up(cfg, target=args.size)
    else:
        data = load()
        print(f"유니버스: {len(data['stocks'])}종목 (목표 {args.size or cfg.universe_size})")
        print(f"마지막 갱신: {data.get('built_at')}")
        for src, n in sorted(source_counts().items(), key=lambda x: -x[1]):
            print(f"  출처 {src}: {n}종목")
        print()
        for s in data["stocks"][:20]:
            print(f"  {s['code']} {s['name']}")
        if len(data["stocks"]) > 20:
            print(f"  ... 외 {len(data['stocks']) - 20}종목")


if __name__ == "__main__":
    main()
