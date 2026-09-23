"""
거래 기록(trades.csv, decisions.csv, daily_summary.log)을 GitHub 에도 자동으로
커밋+푸시해서 백업한다 (2026-08-24 추가).

지금까지 logs/ 전체가 .gitignore 에 걸려서 이 기록들이 사용자 PC 안에만
있었다 - PC가 고장나거나 폴더를 실수로 지우면 복구할 방법이 없었다. 사용자가
"백업할 수 있게 해줘"라고 요청해서 추가함.

주의 1: git push 는 네트워크/인증이 필요한 동작이라 실패할 수 있다. 실패해도
매매 로직 자체가 멈추면 절대 안 되므로, 여기서 나는 예외는 전부 삼켜서
로그만 남기고 절대 밖으로 던지지 않는다.

주의 2: 인증 정보(토큰/비밀번호)가 저장 안 돼 있으면 git push 가 터미널에
로그인 정보를 물어보려고 하는데, 자동 실행 중에 그러면 그 자리에서 영원히
멈춘다 - 예전 REAL 확인 watchdog 사고와 같은 종류의 문제다. 그래서
GIT_TERMINAL_PROMPT=0 으로 그런 프롬프트 자체를 막고, 모든 git 호출에
타임아웃을 짧게 걸어서, 인증이 안 돼 있으면 그냥 몇 초 안에 실패로
끝나게 한다.

이 백업이 실제로 GitHub 까지 올라가려면, 이 컴퓨터에서 최소 한 번은
`git push` 가 로그인 창 없이 성공한 적이 있어야 한다 (Windows 자격 증명
관리자에 토큰이 저장돼 있어야 함). 안 돼 있으면 커밋까지는 되지만 push는
계속 실패하고, 실패 이유를 콘솔에 남긴다.
"""
import os
import subprocess
from datetime import datetime

from common import (
    BASE_DIR,
    CANDIDATE_SNAPSHOT_LOG_PATH,
    CANDIDATE_VOLATILITY_LOG_PATH,
    DECISION_LOG_PATH,
    INVESTOR_LOG_PATH,
    LOG_DIR,
    MARKET_LOG_PATH,
    TRADE_LOG_PATH,
    UPLOW_LOG_PATH,
    VIRTUAL_TRADE_LOG_PATH,
)

DAILY_SUMMARY_PATH = LOG_DIR / "daily_summary.log"
# (2026-08-27) market_history.csv(일별 코스피 기록) 추가 - 코스피-전략 상관관계
# 분석용 데이터도 다른 거래 기록과 동일하게 매 회차마다 자동 백업한다.
# (2026-08-31) investor_history.csv/uplow_history.csv(코스닥 개인순매수, 상한가/
# 하한가 종목수) 도 같은 이유로 추가.
# (2026-09-01) candidate_volatility.csv(후보 종목별 변동성, 사토시룰) 도 같은 이유로 추가.
# (2026-09-03) virtual_trades.csv(코스닥룰로 줄어든 슬롯의 가상매수 기록) 도 같은 이유로 추가.
# (2026-09-03) candidate_snapshot.csv(종목별 외국인순매수/프로그램매매 등 보조지표) 도 같은 이유로 추가.
BACKUP_PATHS = [
    TRADE_LOG_PATH,
    DECISION_LOG_PATH,
    DAILY_SUMMARY_PATH,
    MARKET_LOG_PATH,
    INVESTOR_LOG_PATH,
    UPLOW_LOG_PATH,
    CANDIDATE_VOLATILITY_LOG_PATH,
    VIRTUAL_TRADE_LOG_PATH,
    CANDIDATE_SNAPSHOT_LOG_PATH,
]

# (2026-09-13) 새 구조의 본체인 일봉 패널(data/panel_YYYY.csv)과 고정 유니버스
# (universe.json). 패널은 해가 바뀔 때마다 파일이 늘어나서 목록을 미리 못
# 박으므로, 백업할 때마다 실제로 존재하는 파일을 찾아서 넣는다.
DATA_DIR = BASE_DIR / "data"
UNIVERSE_PATH = BASE_DIR / "universe.json"


def _dynamic_backup_paths() -> list:
    paths = []
    if UNIVERSE_PATH.exists():
        paths.append(UNIVERSE_PATH)
    if DATA_DIR.exists():
        paths.extend(sorted(DATA_DIR.glob("panel_*.csv")))
        # (2026-09-14) 일별 PER/PBR 등 - fundamentals.py 참고. 과거치를 받아올 수
        # 없는 값이라 하루만 빠져도 영구히 비므로, 백업 대상에서 빠지면 안 된다.
        paths.extend(sorted(DATA_DIR.glob("fundamentals_*.csv")))
        # (2026-09-16) 장 시작 전 지표 + 그날 결과 - market_indicators.py 참고.
        # "나쁜 날을 피하는 필터"를 앞검증할 유일한 재료라, 하루라도 빠지면
        # 그날은 영구히 채점할 수 없다.
        paths.extend(sorted(DATA_DIR.glob("market_indicators_*.csv")))
        # (2026-09-22) 10분봉 - fetch_intraday.py 참고. 이 목록에서 제일
        # 급한 것이다. KIS 당일분봉 API(FHKST03010200)는 **오늘 것만** 준다.
        # 과거를 받아올 방법이 아예 없으므로, 수집한 PC 에서 올라오지 않으면
        # 그날 장중은 영구히 비고 분석도 못 한다. 위의 패널처럼 '다시 받는
        # 데 시간이 걸린다' 가 아니라 **다시 받을 데가 없다.**
        paths.extend(sorted(DATA_DIR.glob("krx_min10_*.csv")))
        # KRX 에서 한 번 받아온 과거 데이터. 매일 바뀌지는 않지만, 빠지면
        # 다시 받는 데 한두 시간이 걸리므로 백업 대상에 넣는다.
        # (2026-09-22) 업종분류 - fetch_krx_sector.py 참고. 시점별로 받은
        # 것이라 지금 다시 받으면 '오늘의 분류' 밖에 안 나온다. 과거 분기
        # 것은 KRX 가 날짜를 받아주는 동안만 복구 가능하다.
        for pre in ("krx_panel", "krx_flow", "krx_fund", "krx_cap",
                    "krx_sector", "us_market", "us_futures"):
            paths.extend(sorted(DATA_DIR.glob(f"{pre}_*.csv")))
        uh = DATA_DIR / "krx_universe_history.csv"
        if uh.exists():
            paths.append(uh)
    return paths


_GIT_TIMEOUT_SEC = 20


def _run_git(*args) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["GIT_TERMINAL_PROMPT"] = "0"
    return subprocess.run(
        ["git", *args],
        cwd=str(BASE_DIR),
        capture_output=True,
        text=True,
        # (2026-08-25 버그수정) text=True 인데 encoding 을 안 주면, Windows에서
        # 시스템 기본 코드페이지(한글 Windows는 cp949)로 디코딩을 시도한다.
        # git 커밋 메시지("거래 기록 자동 백업 (...)")는 한글이라 UTF-8로 나오는데,
        # cp949로는 못 읽어서 subprocess 내부 리더 스레드가 UnicodeDecodeError로
        # 죽고, 그 결과 stdout/stderr 가 None으로 남아 이 함수를 호출하는 쪽에서
        # None.strip() 호출로 다시 한번 죽었다 (실제 계좌에서 확인됨: 2026-08-25
        # evening_screen.py 실행 중 "Exception in thread Thread-4 (_readerthread)"
        # + "'NoneType' object has no attribute 'strip'"). daemon.py 가 자식
        # 파이썬 프로세스에 PYTHONIOENCODING=utf-8 을 넣어 이미 같은 종류의
        # 문제를 겪었던 것과 동일한 원인 - 여기서도 인코딩을 명시한다.
        encoding="utf-8",
        errors="replace",
        timeout=_GIT_TIMEOUT_SEC,
        env=env,
    )


def _recover_and_retry_push(first_error: str) -> bool:
    """push 가 거부됐을 때 원격 변경을 받아 합친 뒤 한 번 더 시도한다.
    성공하면 True.

    (2026-09-12 추가) 원래는 push 가 실패하면 "인증 문제인 것 같으니 사람이
    직접 git push 해보라"는 메시지만 찍고 포기했다. 그런데 실제로 훨씬 흔한
    원인은 인증이 아니라 "원격이 앞서 있음"(내가 이 세션에서 코드를 푸시해둔
    경우)이었고, 한 번 그 상태가 되면 그 뒤 모든 회차의 push 가 같은 이유로
    계속 실패하면서 로컬에만 커밋이 쌓였다 - 9/4~9/8 사이 32개 커밋(하루치
    관찰 데이터 전부)이 GitHub 에 하나도 안 올라간 채 방치됐던 사고가 실제로
    있었다. 그래서 이 경우를 자동으로 회복한다.

    중요: 이 함수는 사람이 안 보는 동안(데몬 자동 실행 중) 돌기 때문에,
    저장소를 '병합하다 만 상태'로 남기면 절대 안 된다. 충돌이 나면 즉시
    merge --abort 로 되돌리고 사람에게 알린다 - 반쯤 병합된 채로 방치되면
    그 다음부터 데몬의 커밋조차 실패하게 되고, 사람이 수동으로 풀어줘야 하는
    상황이 된다(9/7 에 실제로 겪음)."""
    print(f"[백업] push 거부됨 - 원격 변경을 받아 합친 뒤 재시도합니다. (원인: {first_error})")

    pull_result = _run_git("pull", "--no-rebase", "--no-edit")
    if pull_result.returncode != 0:
        abort_result = _run_git("merge", "--abort")
        print(
            "[백업] 원격과 자동 병합이 실패해서 원래 상태로 되돌렸습니다"
            f"{' (되돌리기도 실패 - 저장소 상태를 직접 확인하세요)' if abort_result.returncode != 0 else ''}. "
            "로컬 커밋은 그대로 남아있으니 데이터가 사라지지는 않았지만, GitHub 반영은 "
            f"사람이 직접 확인해야 합니다. (오류: {pull_result.stderr.strip()})"
        )
        return False

    retry_result = _run_git("push")
    if retry_result.returncode != 0:
        print(
            "[백업] 원격 변경을 합친 뒤에도 push 가 실패했습니다 (이 경우는 인증 문제일 "
            "가능성이 큽니다). 터미널에서 직접 'git push' 를 한 번 실행해 로그인/토큰 "
            f"입력을 완료해주세요. (오류: {retry_result.stderr.strip()})"
        )
        return False

    print("[백업] 원격 변경을 합쳐서 push 에 성공했습니다.")
    return True


def backup_trade_data() -> bool:
    """거래 기록 파일들을 커밋+푸시한다. 뭐든 실패해도 예외를 던지지 않고
    False 를 돌려준다 - 백업 실패가 매매 프로세스를 멈추면 안 되므로."""
    try:
        existing = [str(p) for p in BACKUP_PATHS if p.exists()]
        existing += [str(p) for p in _dynamic_backup_paths()]
        if not existing:
            return False

        status_result = _run_git("status", "--porcelain", "--", *existing)
        if status_result.returncode != 0:
            # (2026-08-25) 원래 returncode 를 안 보고 stdout 만 봤는데, git 자체가
            # 실패하면(예: BASE_DIR이 더 이상 git 저장소가 아님) stdout 도 비어있어서
            # "바뀐 게 없다"로 잘못 해석해 조용히 아무 것도 안 하고 성공한 척 넘어갔다
            # (매 거래마다 백업하도록 바꾸면서 sim20 테스트 중 실제로 발견됨 - 임시
            # 폴더는 git 저장소가 아니라서 이 경로를 탔다). 이제 실패를 실패로 보고한다.
            print(f"[백업] git status 실패: {status_result.stderr.strip()}")
            return False
        if not status_result.stdout.strip():
            return True  # 어제와 비교해 바뀐 게 없음 - 백업할 새 내용이 없을 뿐 정상

        # (2026-08-25 버그수정) "commit -- <path>" 만으로 충분한 줄 알았는데,
        # 그건 git이 이미 알고 있는(과거에 한 번이라도 커밋된) 파일에만 통한다.
        # logs/trades.csv 등은 이 저장소에 한 번도 커밋된 적이 없는 완전히 새
        # 파일이라, git이 "known to git" 이 아니라며 commit 자체를 거부했다
        # (실제 계좌에서 확인됨: "pathspec ... did not match any file(s) known
        # to git"). git add 로 먼저 이 3개 파일만 스테이징해야 git이 존재를
        # 인지한다. add 도 이 3개 경로로만 한정하므로, 사용자가 다른 파일을
        # 미리 git add 해뒀어도 그건 안 건드림 - 그 아래 commit 에도 여전히
        # 같은 pathspec 을 넘겨서, 혹시 모를 다른 스테이징 내용이 이 커밋에
        # 같이 묶여 들어가는 것도 이중으로 막는다.
        add_result = _run_git("add", "--", *existing)
        if add_result.returncode != 0:
            print(f"[백업] git add 실패: {add_result.stderr.strip()}")
            return False

        today = datetime.now().strftime("%Y-%m-%d")
        commit_result = _run_git("commit", "-m", f"거래 기록 자동 백업 ({today})", "--", *existing)
        if commit_result.returncode != 0:
            print(f"[백업] git commit 실패: {commit_result.stderr.strip()}")
            return False

        push_result = _run_git("push")
        if push_result.returncode != 0:
            if not _recover_and_retry_push(push_result.stderr.strip()):
                return False

        print("[백업] 거래 기록을 GitHub 에 백업했습니다.")
        return True
    except Exception as e:
        print(f"[백업] 예외로 건너뜁니다 (매매에는 영향 없음): {e}")
        return False
