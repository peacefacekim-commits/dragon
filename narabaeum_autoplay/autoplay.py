"""나라배움터: 강의가 끝나면 같은 과목의 다음 강의를 자동으로 열어주는 도구.

본인확인 등 사람 확인이 필요한 팝업/버튼은 절대 자동으로 누르지 않는다.
설정된 "다음 강의" 요소를 못 찾거나 누를 수 없으면 그냥 멈추고 사람에게 확인을
요청한다 — 이게 이 도구의 핵심 안전장치이므로 다른 동작을 추가하지 말 것.
"""

import argparse
import json
import sys
import time
from pathlib import Path

from playwright.sync_api import Locator, Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

DEFAULT_CONFIG = {
    "start_url": "",
    "profile_dir": "./chrome_profile",
    "poll_seconds": 1800,
    "completion_texts": [],
    "completion_selectors": [],
    "next_lecture_selector": "",
    "play_after_next_selector": "",
    "wait_after_click_seconds": 3,
    "headless": False,
}


def load_config(path: Path) -> dict:
    if not path.exists():
        sys.exit(
            f"[오류] 설정 파일이 없습니다: {path}\n"
            f"config.example.json 을 {path.name} 으로 복사한 뒤 값을 채워주세요."
        )
    user_cfg = json.loads(path.read_text(encoding="utf-8"))
    cfg = {**DEFAULT_CONFIG, **user_cfg}

    if not cfg["next_lecture_selector"]:
        print(
            "[경고] next_lecture_selector 가 비어 있어요. "
            "강의 완료를 감지해도 다음 강의를 열 수 없습니다.\n"
            "       README의 '셀렉터 찾는 법'을 참고해 채워주세요."
        )
    return cfg


def is_visible(locator: Locator) -> bool:
    return locator.count() > 0 and locator.first.is_visible()


def detect_completion(page: Page, cfg: dict) -> bool:
    for selector in cfg["completion_selectors"]:
        if is_visible(page.locator(selector)):
            return True

    if cfg["completion_texts"]:
        body_text = page.locator("body").inner_text()
        if any(text in body_text for text in cfg["completion_texts"]):
            return True

    return False


def advance_to_next_lecture(page: Page, cfg: dict) -> bool:
    if not cfg["next_lecture_selector"]:
        return False

    next_button = page.locator(cfg["next_lecture_selector"]).first
    try:
        next_button.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeoutError:
        print(
            "[확인 필요] 다음 강의 버튼을 찾지 못했습니다. "
            "본인확인 팝업 등이 떠 있을 수 있어요 — 직접 확인해주세요."
        )
        return False

    if not next_button.is_enabled():
        print("[대기] 다음 강의 버튼이 아직 비활성 상태예요. 잠시 후 다시 확인합니다.")
        return False

    next_button.click()
    print(f"[진행] 다음 강의로 이동했습니다: {page.url}")

    play_selector = cfg["play_after_next_selector"]
    if play_selector:
        page.wait_for_timeout(cfg["wait_after_click_seconds"] * 1000)
        play_button = page.locator(play_selector).first
        if is_visible(play_button):
            play_button.click()
            print("[진행] 재생을 시작했습니다.")

    return True


def watch(page: Page, cfg: dict) -> None:
    handled_urls = set()
    interval_min = cfg["poll_seconds"] / 60
    print(
        f"모니터링을 시작합니다 — 지금 바로 한 번 확인하고, "
        f"이후 {interval_min:g}분마다 확인합니다. 종료하려면 Ctrl+C 를 누르세요.\n"
    )

    while True:
        try:
            url = page.url
            if url not in handled_urls and detect_completion(page, cfg):
                print(f"[감지] 강의 완료: {url}")
                if advance_to_next_lecture(page, cfg):
                    handled_urls.add(url)
            time.sleep(cfg["poll_seconds"])
        except KeyboardInterrupt:
            print("\n종료합니다.")
            return
        except Exception as exc:  # noqa: BLE001 - 모니터링 루프는 계속 살아있어야 함
            print(f"[오류] {exc} — 계속 모니터링합니다.")
            time.sleep(cfg["poll_seconds"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", default="config.json", help="설정 파일 경로")
    parser.add_argument(
        "--start-file",
        help="start_url 대신 사용할 로컬 HTML 파일 경로 (시연용 모의 강의 등)",
    )
    args = parser.parse_args()

    cfg = load_config(Path(args.config))
    if args.start_file:
        cfg["start_url"] = Path(args.start_file).resolve().as_uri()
    if not cfg["start_url"]:
        sys.exit("[오류] start_url 이 비어 있습니다. config.json 을 채우거나 --start-file 을 넘겨주세요.")

    profile_dir = Path(cfg["profile_dir"]).resolve()
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            str(profile_dir), headless=cfg["headless"], viewport=None
        )
        page = context.pages[0] if context.pages else context.new_page()
        page.goto(cfg["start_url"])

        print("브라우저가 열렸습니다. (실제 사이트라면 로그인 후 강의 화면으로 이동하세요)")
        print("(로그인 정보는 이 폴더의 chrome_profile 에 저장되어 다음 실행부터는 유지됩니다.)")
        input("준비되면 이 창에서 Enter 를 눌러 모니터링을 시작합니다...")

        watch(page, cfg)
        context.close()


if __name__ == "__main__":
    main()
