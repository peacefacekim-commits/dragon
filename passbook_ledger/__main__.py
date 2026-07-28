import argparse
import shutil
import threading
import webbrowser

from .server import run


def main():
    parser = argparse.ArgumentParser(
        prog="python -m passbook_ledger",
        description="통장 스캔 -> 거래 내역 표 정리 도구 (오프라인)",
    )
    parser.add_argument("--port", type=int, default=8877, help="로컬 서버 포트 (기본 8877)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저를 자동으로 열지 않음")
    args = parser.parse_args()

    if not shutil.which("tesseract"):
        print(
            "[안내] tesseract 실행 파일을 찾지 못했습니다. OCR 자동 인식은 동작하지 않고,\n"
            "       표를 직접 입력하는 기능은 그대로 쓸 수 있습니다.\n"
            "       OCR을 쓰려면 Tesseract OCR(한국어 데이터 포함)을 설치하세요."
        )

    if not args.no_browser:
        url = f"http://127.0.0.1:{args.port}/"
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()

    run(port=args.port)


if __name__ == "__main__":
    main()
