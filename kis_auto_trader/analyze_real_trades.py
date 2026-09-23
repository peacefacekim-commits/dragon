"""실제 체결 기록 88건 - 왜 졌는지 정확히 갈라본다.

(2026-09-22 신설) 사용자: "내가 지금까지 한 투자들도 10분 데이터들인데
그건 활용 할 수 있지?"

쓸 수 있다. 다만 **시세 데이터가 아니라 체결 기록**이라서 답하는 질문이
다르다. 10분봉으로는 "어떤 조건이면 승률이 오르나"를 묻고, 체결 기록으로는
**"실제로 왜 졌나"**를 묻는다. 뒤쪽이 먼저 답해야 하는 질문이다.

자료: logs/trades.csv, 2026-07-29 ~ 2026-09-04, 172건(매수 93 / 매도 79).
FIFO 로 짝지어 완결 거래 88건. 미청산 11건은 제외했다.
전부 mode=real, 즉 실제 돈이다.

===========================================================================
0 - 먼저 바로잡은 것: 10분 매매가 아니었다
===========================================================================
  보유 시간   하위25% 24.9분 / **중앙 140.3분(2.3시간)** / 상위25% 350분
  10분 이내 13건, 1시간 이내 31건, 당일 마감 이내 75건 (전체 88건)

'10분씩 짧게' 라고 기억하고 있었지만 실제 중앙값은 2.3시간이다. 이게
중요한 이유: 10분봉을 모으는 목적이 '10분 매매를 채점하는 것' 이었는데,
실제로 하던 것은 **당일 내 매매**였다. 10분봉은 여전히 필요하지만
(2.3시간도 일봉으로는 못 본다) 목표 보유시간이 다르다.

===========================================================================
1 - 처음 본 것과 그게 왜 틀렸나
===========================================================================
보유 시간으로 가르니 이렇게 나왔다.

  구간         건수  승률    기대값%    실현손익
  10분 이내     12   8.3%   -2.044   -93,350
  10~60분      19  42.1%   -1.021   -38,906
  1시간~당일     44  54.5%   +0.252    -7,390
  하루 이상      13  53.8%   +0.167   +31,096

"짧게 들면 진다"로 읽고 싶어진다. **틀렸다.** 10분 이내 12건의 청산
이유를 하나하나 보니 **손절 11건 + 익절 1건**이었다. note 에 그대로
적혀 있다.

  -4.76%  10.0분  모아라이프플러스  손절
  -4.55%   9.8분  사토시홀딩스      손절
  -4.33%  10.0분  이건산업          손절
  ... (11건 전부 손절)
  +6.68%   9.7분  헝셩그룹          익절

즉 **짧게 들어서 진 게 아니라, 손절이 걸리면 짧게 끝나고 그건 정의상
손실이다.** 보유 시간은 원인이 아니라 결과다. 인과가 거꾸로였다.

===========================================================================
2 - 청산 이유로 갈라야 한다
===========================================================================
  청산 이유   건수  승률    평균이익%  평균손실%  기대값%   실현손익   보유중앙
  손절         30   0.0%   +0.000   -4.018   -4.018  -392,728    25분
  익절         25  96.0%   +4.164   -2.397   +3.902  +293,618   130분
  일일 정리     33  48.5%   +1.799   -2.145   -0.233    -9,441   311분
  전체         88  45.5%   +3.218   -3.321   -0.349  -108,551   140분

손절과 익절은 **규칙이 결과를 정해버린다.** 손절의 승률이 0%인 것은
발견이 아니라 정의다. 그래서 이 둘로는 '내 판단이 맞았나'를 못 본다.

**'일일 정리' 33건만이 편향 없는 표본이다.** 규칙이 아니라 시간이 되어
청산한 것이라, 그 종목을 고른 판단이 맞았는지가 그대로 나온다.

===========================================================================
3 - 답: 종목 선정이 정확히 0이었다
===========================================================================
편향 없는 표본 33건:

    승률 48.5% (16승 17패)
    **수수료 전 평균 -0.023%**   <- 사실상 0
    수수료 후 평균 -0.233%
    실현손익 -9,441원

**종목 선정에 엣지도, 반대 엣지도 없었다.** 동전 던지기였고, 수수료만큼
졌다. 이게 "며칠 계속 손해를 봤다"의 정체다.

그럼 -108,551원은 어디서 왔나. 산수가 정확히 맞는다.

    손절 30건 x (-4.018%) = -120.5%p
    익절 25건 x (+3.902%) =  +97.5%p
    ------------------------------------
    합계                    -23.0%p

(익절 25건의 평균이 +3.902% 인 것은 그 안에 손실 1건이 섞여 있어서다.
이긴 것만 고르면 +4.164% 인데, 합계를 낼 때는 무리 전체 평균을 써야
한다. 이긴 것만 평균하면 진 건을 빼고 세는 셈이 된다.)

손절과 익절의 크기는 거의 같은데(-4.018 vs +3.902) **횟수가 손절 쪽이
많았다(30 vs 25).** 그래서 졌다.

필요 승률을 계산하면
    4.018 / (4.018 + 3.902) = **50.7%**
실제 익절 비율
    25 / (25 + 30) = **45.5%**

**5.3%p 부족했다.** 그리고 편향 없는 표본의 승률이 48.5% 였으므로,
애초에 50.7% 를 넘길 구조가 아니었다.

===========================================================================
4 - 이게 일봉 분석과 맞아떨어진다
===========================================================================
이 저장소는 일봉으로 익절/손절을 여러 번 쟀고 전부 졌다.
  손절 6가지 - 타이트할수록 나쁘다, 낙폭도 안 준다     [analyze_stops]
  익절 5가지 - +20% 가 좋아 보였으나 반띵에서 뒤집힘   [analyze_stops]
  좋은 선정 위에 올려도 12/12 짐                     [analyze_original]

**같은 결론이 실제 돈으로 확인됐다.** 백테스트가 맞았다는 뜻이고, 동시에
이 손실이 운이 나빴던 게 아니라 구조였다는 뜻이다.

===========================================================================
5 - 그래서 10분봉으로 무엇을 물어야 하나 (달라졌다)
===========================================================================
처음 계획은 "10분 매매의 승률을 올리는 조건 찾기" 였다. 위 결과가 그
계획을 두 군데 고친다.

  (1) 목표 보유시간이 10분이 아니라 **2~5시간**이다 (실제 중앙 2.3시간,
      '일일 정리' 중앙 311분). analyze_min10.py 의 보유시간 칸을
      10/20/30/60분에서 **60/120/180/300분** 까지 늘려야 한다.
  (2) **승률을 묻기 전에 손익 비대칭을 먼저 물어야 한다.** 승률 48.5%
      는 이미 거의 반반이다. 문제는 승률이 아니라 '이길 때와 질 때의
      크기가 같다' 는 것이었다. 크기를 벌릴 수 있는지가 진짜 질문이다.

한계
  1) 88건은 적다. 편향 없는 표본은 33건뿐이다. 승률 48.5% 의 신뢰구간은
     대략 32~65% 로 아주 넓다. "정확히 0" 은 점추정이지 확정이 아니다.
  2) 2026-07-29 ~ 09-04, 약 5주다. 시기 하나다.
  3) 종목 선정 기준이 그때그때 달랐을 수 있다. 이 기록만으로는 어떤
     기준으로 골랐는지 복원할 수 없다.
  4) 주문가와 체결가가 따로 없어서 **슬리피지는 못 뺀다.** 체결가만
     있으므로 '실제 슬리피지가 얼마였나' 는 여전히 모른다
     (analyze_knobs --fast 의 0.08% 교차점이 미해결로 남는다).

실행:
  python analyze_real_trades.py
"""
import collections
import csv
import pathlib
import statistics as st
import sys
from datetime import datetime

# 경로를 박아두지 않는다 (사용자 PC 는 윈도우다).
_ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ROOT))

LOG_PATH = _ROOT / "logs" / "trades.csv"
FEE_ROUND_TRIP = 0.21
# 청산 이유. 앞의 둘은 규칙이 결과를 정하므로 판단 평가에 못 쓴다.
RULE_EXITS = ("손절", "익절")
UNBIASED_EXIT = "일일 정리"


def load_trades(path=LOG_PATH):
    """체결 기록을 시간순으로. 숫자를 못 읽는 줄은 버린다."""
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            try:
                out.append({
                    "t": datetime.fromisoformat(r["timestamp"]),
                    "mode": r.get("mode", ""),
                    "code": r["code"], "name": r.get("name", ""),
                    "side": r["side"], "qty": int(float(r["qty"])),
                    "price": float(r["price"]), "note": r.get("note", ""),
                })
            except (KeyError, TypeError, ValueError):
                continue
    out.sort(key=lambda r: r["t"])
    return out


def pair_fifo(rows, fee=FEE_ROUND_TRIP):
    """매수-매도를 FIFO 로 짝지어 완결 거래 목록을 만든다.

    왜 FIFO 인가: 같은 종목을 여러 번 나눠 사고 팔았으므로 어떤 매수와
    어떤 매도를 묶을지 정해야 한다. 먼저 산 것을 먼저 팔았다고 본다.
    다른 규칙을 쓰면 개별 수익률이 달라지지만 합계는 같다.

    미청산(아직 안 판 매수)은 빼고 돌려준다 - 결과를 모르는 거래다.
    """
    book, done = collections.defaultdict(list), []
    for r in rows:
        if r["side"] == "buy":
            book[r["code"]].append([r["t"], r["price"], r["qty"]])
            continue
        need = r["qty"]
        while need > 0 and book[r["code"]]:
            bt, bp, bq = book[r["code"]][0]
            use = min(need, bq)
            gross = (r["price"] / bp - 1) * 100 if bp else 0.0
            done.append({
                "code": r["code"], "name": r["name"], "qty": use,
                "buy": bp, "sell": r["price"], "buy_t": bt, "sell_t": r["t"],
                "mins": (r["t"] - bt).total_seconds() / 60,
                "note": r["note"], "gross": gross, "net": gross - fee,
                "won": (r["price"] - bp) * use
                       - (r["price"] + bp) * use * fee / 200,
            })
            bq -= use
            need -= use
            if bq == 0:
                book[r["code"]].pop(0)
            else:
                book[r["code"]][0][2] = bq
    open_left = sum(len(v) for v in book.values())
    return done, open_left


def stats(group):
    """(건수, 승률%, 평균이익%, 평균손실%, 기대값%, 실현손익원, 보유중앙분)."""
    if not group:
        return (0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    w = [t["net"] for t in group if t["net"] > 0]
    l = [t["net"] for t in group if t["net"] <= 0]
    wr = len(w) / len(group) * 100
    aw = st.mean(w) if w else 0.0
    al = st.mean(l) if l else 0.0
    return (len(group), wr, aw, al, wr / 100 * aw + (1 - wr / 100) * al,
            sum(t["won"] for t in group), st.median(t["mins"] for t in group))


def required_win_rate(avg_win, avg_loss):
    """이 손익 크기에서 본전이 되는 승률%.

    승률 x 이익 + (1-승률) x 손실 = 0  =>  승률 = |손실| / (이익 + |손실|)
    이게 이 파일의 핵심 산수다. 승률만 봐서는 이길지 알 수 없다.
    """
    a, b = abs(avg_win), abs(avg_loss)
    if a + b == 0:
        return float("inf")
    return b / (a + b) * 100


def by_note(done):
    """청산 이유별로 나눈다. 규칙 청산과 시간 청산을 섞으면 안 된다."""
    out = collections.OrderedDict()
    for key in RULE_EXITS + (UNBIASED_EXIT,):
        out[key] = [t for t in done if t["note"].startswith(key)]
    known = {id(t) for g in out.values() for t in g}
    rest = [t for t in done if id(t) not in known]
    if rest:
        out["그 외"] = rest
    return out


def unbiased(done):
    """규칙이 결과를 정하지 않은 거래만. '내 판단이 맞았나' 를 보는 표본."""
    return [t for t in done if t["note"].startswith(UNBIASED_EXIT)]


def main():
    rows = load_trades()
    if not rows:
        print(f"[!] {LOG_PATH} 가 없거나 읽을 수 없습니다.")
        return 1
    done, open_left = pair_fifo(rows)
    if not done:
        print("[!] 짝지어진 완결 거래가 없습니다.")
        return 1

    modes = collections.Counter(r["mode"] for r in rows)
    print(f"\n=== 실제 체결 기록 ===")
    print(f"  {rows[0]['t']:%Y-%m-%d} ~ {rows[-1]['t']:%Y-%m-%d}, "
          f"{len(rows)}건 (mode: {dict(modes)})")
    print(f"  완결 거래 {len(done)}건, 미청산 {open_left}건(제외)")

    m = sorted(t["mins"] for t in done)
    print(f"\n[0] 보유 시간 - '10분 매매' 가 아니었다")
    for q, lab in ((0.25, "하위25%"), (0.5, "중앙"), (0.75, "상위25%")):
        v = m[min(len(m) - 1, int(q * len(m)))]
        print(f"  {lab:<8}{v:>8.1f}분 ({v / 60:.1f}시간)")
    print(f"  10분 이내 {sum(1 for x in m if x <= 10)}건 / "
          f"1시간 이내 {sum(1 for x in m if x <= 60)}건 / "
          f"당일 이내 {sum(1 for x in m if x <= 390)}건 / 전체 {len(m)}건")

    print(f"\n[1] 청산 이유별 - 규칙 청산과 시간 청산을 섞으면 안 된다")
    print(f"{'청산 이유':<12}{'건수':>5}{'승률':>8}{'평균이익%':>10}"
          f"{'평균손실%':>10}{'기대값%':>10}{'실현손익':>12}{'보유중앙':>9}")
    for key, g in by_note(done).items():
        if not g:
            continue
        n, wr, aw, al, ev, won, mid = stats(g)
        print(f"{key:<12}{n:>5}{wr:>7.1f}%{aw:>+10.3f}{al:>+10.3f}"
              f"{ev:>+10.3f}{won:>+12,.0f}{mid:>8.0f}분")
    n, wr, aw, al, ev, won, mid = stats(done)
    print(f"{'전체':<12}{n:>5}{wr:>7.1f}%{aw:>+10.3f}{al:>+10.3f}"
          f"{ev:>+10.3f}{won:>+12,.0f}{mid:>8.0f}분")
    print("  손절의 승률 0% 는 발견이 아니라 정의다. 규칙이 결과를 정한다.")

    pure = unbiased(done)
    print(f"\n[2] 편향 없는 표본 ('{UNBIASED_EXIT}' {len(pure)}건)")
    if pure:
        pw = [t for t in pure if t["net"] > 0]
        print(f"  승률 {len(pw) / len(pure) * 100:.1f}% "
              f"({len(pw)}승 {len(pure) - len(pw)}패)")
        print(f"  수수료 전 평균 {st.mean(t['gross'] for t in pure):+.3f}%"
              f"  <- 종목 선정의 엣지")
        print(f"  수수료 후 평균 {st.mean(t['net'] for t in pure):+.3f}%")
        print(f"  실현손익 {sum(t['won'] for t in pure):+,.0f}원")

    print(f"\n[3] 왜 졌나 - 산수")
    cut = [t for t in done if t["note"].startswith("손절")]
    tp = [t for t in done if t["note"].startswith("익절")]
    if cut and tp:
        ac = st.mean(t["net"] for t in cut)
        at = st.mean(t["net"] for t in tp)
        print(f"  손절 {len(cut)}건 x ({ac:+.3f}%) = {len(cut) * ac:+.1f}%p")
        print(f"  익절 {len(tp)}건 x ({at:+.3f}%) = {len(tp) * at:+.1f}%p")
        print(f"  합계 {len(cut) * ac + len(tp) * at:+.1f}%p")
        need = required_win_rate(at, ac)
        got = len(tp) / (len(tp) + len(cut)) * 100
        print(f"\n  필요 승률 {need:.1f}%  /  실제 익절 비율 {got:.1f}%"
              f"  ->  {got - need:+.1f}%p")
        print(f"  손익 크기가 거의 같으면(-{abs(ac):.2f} vs +{at:.2f}) "
              f"승률 {need:.0f}% 를 넘어야 본전이다.")
    print("\n종목 선정은 거의 0 이었고, 손절이 손실을 확정했다.")
    print("승률이 문제가 아니라 '이길 때와 질 때의 크기가 같다' 가 문제였다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
