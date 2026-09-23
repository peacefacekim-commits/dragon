"""
장애/실행오류를 이메일로 알린다 (2026-08-26 추가).

크래시(프로그램이 죽는 경우)와 "매수 신호는 떴는데 실제 체결이 안 된 경우"
두 가지를 사용자가 알림 받고 싶어해서 만듦. "조건에 안 맞아서 관망"처럼
정상적인 hold는 알림 안 보낸다 - 시장에 기회가 없는 건 어쩔 수 없는 거라서.

Gmail SMTP(앱 비밀번호)를 쓴다. .env 에 아래 세 값이 있어야 실제로 발송된다:
  NOTIFY_EMAIL_FROM         보내는 사람 Gmail 주소
  NOTIFY_EMAIL_APP_PASSWORD Gmail 앱 비밀번호(일반 로그인 비밀번호 아님, 16자리)
  NOTIFY_EMAIL_TO           받는 사람 이메일 주소 (본인한테 보내도 됨)

셋 중 하나라도 없으면 발송을 조용히 건너뛴다(예외 안 던짐) - 알림 기능
자체가 매매 실행을 막으면 안 되므로. 무슨 이유로든 이메일 발송이 실패해도
마찬가지로 조용히 넘어간다.

(2026-08-26 버그수정) .env 를 이 파일이 직접 안 읽고 common.py 가 먼저
import 돼서 .env 를 읽어주길 기대하고 있었다. 평소 실행(main.py/daemon.py
등)은 다 common 을 먼저 import 하니 문제가 안 드러났는데, "python -c
'import notify; ...'" 처럼 notify 만 단독으로 실행하면 .env 자체가 전혀
안 읽혀서 무조건 실패했다 (실제 계좌에서 확인됨 - 설정을 다 넣었는데도
계속 False 만 나왔음). load_dotenv() 를 이 파일에서 직접도 불러서, 어떤
순서로 import 되든 항상 .env 를 읽게 한다."""
import os
import smtplib
from email.mime.text import MIMEText

from dotenv import load_dotenv

from common import BASE_DIR

load_dotenv(BASE_DIR / ".env")

_SMTP_TIMEOUT_SEC = 15


def send_email(subject: str, body: str) -> bool:
    """알림 이메일을 보낸다. 설정이 없거나 발송 실패해도 예외를 던지지 않고
    False 를 돌려준다 - 알림 실패가 매매 프로세스를 멈추면 안 되므로."""
    sender = os.environ.get("NOTIFY_EMAIL_FROM", "")
    app_password = os.environ.get("NOTIFY_EMAIL_APP_PASSWORD", "")
    recipient = os.environ.get("NOTIFY_EMAIL_TO", "")
    if not sender or not app_password or not recipient:
        return False

    try:
        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = subject
        msg["From"] = sender
        msg["To"] = recipient

        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=_SMTP_TIMEOUT_SEC) as server:
            server.login(sender, app_password)
            server.sendmail(sender, [recipient], msg.as_string())
        return True
    except Exception as e:
        print(f"[알림] 이메일 발송 실패 (무시하고 계속 진행): {e}")
        return False


def notify_crash(context: str, error: Exception) -> None:
    """프로그램이 죽었을 때 보내는 알림. main.py 최상위 예외 처리에서 부른다."""
    send_email(
        subject=f"[자동매매] 오류로 중단됨 - {context}",
        body=f"{context} 실행 중 다음 오류로 중단됐습니다:\n\n{error}\n\n"
             f"KIS 앱에서 계좌 상태를 직접 확인해주세요.",
    )


def notify_buy_signal_not_executed(code: str, name: str, reason: str) -> None:
    """매수 신호(조건 충족)는 떴는데 실제 체결이 안 됐을 때 보내는 알림.
    (2026-09-04) 실전투자를 접으면서 이 함수를 부르던 trader.py의 매수 로직
    자체가 없어져 지금은 호출하는 곳이 없다 - 새 전략이 실제 주문을 다시 내게
    되면 재사용할 인프라로 남겨둔다. 조건 자체를 못 채워 관망(hold)한 정상적인
    경우는 이 알림 대상이 아니다."""
    send_email(
        subject=f"[자동매매] 매수 신호는 떴지만 체결 안 됨 - {name}",
        body=f"{name}({code}) 에서 매수 조건은 충족됐는데 실제 매수는 안 됐습니다.\n\n"
             f"사유: {reason}\n\n"
             f"콘솔 로그(run_console.log)에서 자세한 내용을 확인해주세요.",
    )
