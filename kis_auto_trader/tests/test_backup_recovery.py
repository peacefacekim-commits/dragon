"""backup.py의 push 실패 자동 회복을 진짜 git 저장소로 검증하는 테스트.

(2026-09-12 추가) 9/4~9/8 사이 "원격이 앞서 있어서 push 거부 -> 그 뒤 모든
회차가 같은 이유로 계속 실패 -> 하루치 관찰 데이터 32커밋이 GitHub에 하나도
안 올라감" 사고를 겪고 만든 자동 회복 로직(_recover_and_retry_push)을 검증한다.

가짜 스텁이 아니라 임시 폴더에 실제 git 저장소(로컬 + bare 원격)를 만들어서
진짜 divergence를 재현한다 - git 동작 자체가 핵심이라 흉내로는 의미가 없다.

실행:
  python tests/test_backup_recovery.py
"""
import subprocess
import sys
import tempfile
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

results = []


def check(label, cond, detail=""):
    ok = bool(cond)
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail else ""))
    return ok


def git(cwd, *args, check_ok=True):
    r = subprocess.run(["git", *args], cwd=str(cwd), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if check_ok and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} 실패: {r.stderr}")
    return r


def make_repos():
    """bare 원격 + 로컬 클론 2개(사용자 PC 역할, 다른 곳에서 푸시하는 역할)를 만든다."""
    base = pathlib.Path(tempfile.mkdtemp())
    remote = base / "remote.git"
    git(base, "init", "--bare", "-b", "main", str(remote))

    local = base / "local"
    git(base, "clone", str(remote), str(local))
    git(local, "config", "user.email", "test@test")
    git(local, "config", "user.name", "test")
    (local / "logs").mkdir()
    (local / "logs" / "trades.csv").write_text("timestamp\n", encoding="utf-8")
    git(local, "add", "-A")
    git(local, "commit", "-m", "초기")
    git(local, "push", "-u", "origin", "main")

    other = base / "other"
    git(base, "clone", str(remote), str(other))
    git(other, "config", "user.email", "test2@test")
    git(other, "config", "user.name", "test2")
    return base, remote, local, other


def load_backup_for(local_path):
    """backup 모듈을 local_path 기준으로 다시 로드한다 (BASE_DIR/경로가 모듈
    로드 시점에 고정되므로 매 시나리오마다 새로 읽어야 한다)."""
    for mod in ["backup", "common"]:
        sys.modules.pop(mod, None)
    import common
    common.BASE_DIR = local_path
    common.LOG_DIR = local_path / "logs"
    common.TRADE_LOG_PATH = local_path / "logs" / "trades.csv"
    import backup
    backup.BASE_DIR = local_path
    backup.BACKUP_PATHS = [local_path / "logs" / "trades.csv"]
    return backup


# =====================================================================
# 1) 원격이 앞서 있을 때(충돌 없음): 자동으로 pull 후 push 성공해야 함
# =====================================================================
base, remote, local, other = make_repos()

# 다른 곳에서 원격에 코드 파일을 먼저 푸시 -> 원격이 앞서게 만든다
(other / "somecode.py").write_text("print('hi')\n", encoding="utf-8")
git(other, "add", "-A")
git(other, "commit", "-m", "다른 곳에서 코드 추가")
git(other, "push")

# 로컬(데몬)은 그것도 모르고 자기 로그만 바꿔서 백업 시도
(local / "logs" / "trades.csv").write_text("timestamp\nrow1\n", encoding="utf-8")
backup = load_backup_for(local)
ok = backup.backup_trade_data()
check("1) 원격이 앞서 있어도 자동 회복해서 백업 성공", ok is True)

remote_log = git(local, "log", "--oneline", "origin/main").stdout
check("1b) 로컬 커밋이 실제로 원격에 반영됨",
      "거래 기록 자동 백업" in git(local, "log", "--oneline", "-5", "origin/main").stdout,
      remote_log.splitlines()[0] if remote_log else "")
check("1c) 다른 곳에서 올린 코드도 로컬에 받아져 있음", (local / "somecode.py").exists())

# =====================================================================
# 2) 같은 파일이 양쪽에서 바뀐 경우(충돌): 병합을 되돌리고 실패 보고해야 함
#    - 중요: 저장소가 '병합하다 만 상태'로 남으면 안 된다
# =====================================================================
base2, remote2, local2, other2 = make_repos()

# 양쪽에서 같은 파일(trades.csv)의 같은 줄을 다르게 수정 -> 충돌 유발
(other2 / "logs" / "trades.csv").write_text("timestamp\n원격에서쓴줄\n", encoding="utf-8")
git(other2, "add", "-A")
git(other2, "commit", "-m", "원격에서 로그 수정")
git(other2, "push")

(local2 / "logs" / "trades.csv").write_text("timestamp\n로컬에서쓴줄\n", encoding="utf-8")
backup2 = load_backup_for(local2)
ok2 = backup2.backup_trade_data()
check("2) 충돌 시 백업은 실패로 보고됨", ok2 is False)

status = git(local2, "status", "--porcelain").stdout
merge_head = (local2 / ".git" / "MERGE_HEAD").exists()
check("2b) 병합하다 만 상태로 남지 않음 (MERGE_HEAD 없음)", not merge_head,
      f"status={status.strip()!r}")

local_log = git(local2, "log", "--oneline", "-3").stdout
check("2c) 로컬 커밋(데이터)은 그대로 남아있음 - 데이터 유실 없음",
      "거래 기록 자동 백업" in local_log, local_log.splitlines()[0] if local_log else "")

print()
if all(results):
    print(f"전체 통과: {len(results)}/{len(results)}")
else:
    print(f"실패 있음: {sum(results)}/{len(results)}")
    sys.exit(1)
