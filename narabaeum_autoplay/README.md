# 나라배움터 다음 강의 자동 열기

한 과목 안에 여러 강의가 있을 때, 지금 듣는 강의가 끝나면(수강완료로 표시되면)
같은 과목의 다음 강의를 자동으로 열어주는 도구입니다.

## 이 도구가 하는 일 / 하지 않는 일

- ✅ 화면에서 "수강완료" 같은 완료 표시를 감지하면, 미리 지정해둔 "다음 강의" 버튼을
  자동으로 클릭합니다.
- ✅ 로그인은 사람이 직접 합니다. 한 번 로그인해두면 `chrome_profile` 폴더에 세션이
  저장되어 다음 실행부터는 자동으로 로그인 상태가 유지됩니다.
- ❌ **본인확인 팝업, 캡차, 그 밖의 "사람인지 확인"하는 장치는 절대 자동으로 누르지
  않습니다.** 그런 화면이 뜨면 "다음 강의" 버튼을 못 찾게 되어 자동화가 그냥
  멈추고, 콘솔에 확인해달라는 메시지만 남깁니다. 사람이 직접 대응한 뒤 다시
  실행하면 됩니다. 이건 우연이 아니라 이 도구가 갖고 있는 유일한 안전장치라서,
  코드를 고쳐서 이 부분을 우회하는 용도로 쓰지 마세요.

## 준비 (Windows, 더블클릭으로)

1. **`설치.bat`** 을 더블클릭합니다. (처음 한 번만) 필요한 패키지와 브라우저를
   설치하고, `config.json` 이 없으면 `config.example.json` 을 복사해 만들어줍니다.
2. 메모장으로 `config.json` 을 열어 `next_lecture_selector` 등 값을 채웁니다.
   (아래 [셀렉터 찾는 법](#셀렉터-찾는-법-next_lecture_selector-등) 참고)
3. **`실행.bat`** 을 더블클릭하면 시작합니다.

파이썬이 없다면 [python.org] 에서 설치하고, 설치 시
**"Add python.exe to PATH"** 를 꼭 체크하세요.

## 준비 (명령줄로 직접)

```bash
pip install -r requirements.txt
python -m playwright install chromium
```

`config.example.json` 을 `config.json` 으로 복사한 뒤 값을 채웁니다.

```json
{
  "start_url": "https://www.nlc.go.kr/",
  "profile_dir": "./chrome_profile",
  "poll_seconds": 1800,
  "completion_texts": ["수강완료", "학습완료", "이수완료"],
  "completion_selectors": [],
  "next_lecture_selector": "여기에 CSS 셀렉터",
  "play_after_next_selector": "",
  "wait_after_click_seconds": 3
}
```

| 항목 | 설명 |
|---|---|
| `start_url` | 실행 시 처음 열 주소 (로그인 페이지나 과목 목록 페이지) |
| `poll_seconds` | 완료 여부를 몇 초마다 확인할지 (기본값 1800 = 시작하자마자 한 번, 이후 30분마다) |
| `completion_texts` | 이 중 하나라도 화면 텍스트에 있으면 "완료"로 판단 |
| `completion_selectors` | (선택) 완료 시 나타나는 특정 요소의 CSS 셀렉터 |
| `next_lecture_selector` | **필수.** "다음 강의" 버튼/링크의 CSS 셀렉터 |
| `play_after_next_selector` | (선택) 다음 강의 페이지에서 재생 버튼을 한 번 더 눌러야 한다면 그 셀렉터 |

## 셀렉터 찾는 법 (`next_lecture_selector` 등)

나라배움터는 로그인이 필요해서, 실제 화면 구조(버튼 이름·클래스)는 직접 로그인한
상태에서만 확인할 수 있습니다. 아래 순서로 찾으면 됩니다.

1. 크롬에서 나라배움터에 로그인하고, 강의 목록이 있는 과목 페이지로 이동합니다.
2. "다음 강의" 버튼(또는 강의 목록에서 다음 차시 링크) 위에서 마우스 오른쪽 클릭 →
   **검사(Inspect)** 를 누릅니다.
3. 개발자도구에서 해당 요소를 오른쪽 클릭 → **Copy → Copy selector** 를 누르면
   CSS 셀렉터가 복사됩니다. 이 값을 `next_lecture_selector` 에 붙여넣습니다.
4. "수강완료"처럼 완료 시 나타나는 문구가 있다면 그대로 `completion_texts` 에 문자열로
   넣으면 되고, 별도 배지/아이콘으로만 표시된다면 그 요소도 같은 방식으로
   `completion_selectors` 에 셀렉터를 추가합니다.

## 실행

`실행.bat` 을 더블클릭하거나(Windows), 명령줄에서 직접 실행합니다.

```bash
python autoplay.py
```

브라우저가 뜨면 나라배움터에 로그인하고 강의 재생 화면으로 이동한 뒤, 터미널에서
Enter 를 누르면 모니터링이 시작됩니다. 강의가 끝날 때마다 콘솔에 진행 상황이
출력되고, 다음 강의로 자동 이동합니다. `Ctrl+C` 로 언제든 멈출 수 있습니다.

[python.org]: https://www.python.org/downloads/windows/

## 시연할 때 참고

- 처음 실행할 때 `next_lecture_selector` 가 실제 화면과 맞는지 짧은 강의 하나로
  먼저 확인해보는 걸 추천합니다.
- 시연 중 본인확인 팝업이 뜨면 "여기서 자동화가 멈추는 걸 보여주는 것"도
  이 도구의 설계 의도를 보여주는 좋은 지점입니다 — 의도적으로 안 만든 부분이니까요.
