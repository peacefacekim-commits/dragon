"""종목 뉴스 수집 + 호재/악재 판단.

뉴스는 네이버 금융의 종목별 뉴스 목록 페이지를 그대로 긁어온다 (로그인/키 불필요, 무료).
그 제목들을 모아서 Claude API 에 보내 종합적으로 호재/악재/중립을 판단하게 한다.
이 판단 호출은 유료(Anthropic API 과금)라서, .env 의 ANTHROPIC_API_KEY 가 있어야 동작한다.
"""
import html
import json
import os
import re

import anthropic
import requests

_TITLE_PATTERN = re.compile(
    r'<td class="title">\s*<a[^>]*>(?P<title>.*?)</a>\s*</td>\s*'
    r'<td class="info">(?P<press>.*?)</td>\s*'
    r'<td class="date">\s*(?P<date>.*?)\s*</td>',
    re.S,
)
_TAG_PATTERN = re.compile(r"<[^>]+>")

_client = None


def fetch_recent_news(code: str, max_items: int = 10) -> list[dict]:
    """네이버 금융 종목뉴스 페이지에서 최근 뉴스 제목/언론사/날짜를 가져온다."""
    res = requests.get(
        "https://finance.naver.com/item/news_news.naver",
        params={"code": code, "page": "", "clusterId": ""},
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": f"https://finance.naver.com/item/news.naver?code={code}",
        },
        timeout=10,
    )
    res.encoding = "euc-kr"

    items = []
    for m in _TITLE_PATTERN.finditer(res.text):
        title = html.unescape(_TAG_PATTERN.sub("", m.group("title"))).strip()
        # 네이버 페이지 구조가 종종 셀 안에 "관련기사 N건" 배지 등을 더 넣어놔서
        # 줄바꿈 섞인 문자열이 나올 때가 있다 - 한 줄로 뭉치고 길이를 제한해둔다.
        title = re.sub(r"\s+", " ", title).strip()[:120]
        if not title:
            continue
        items.append({
            "title": title,
            "press": m.group("press").strip(),
            "date": m.group("date").strip(),
        })
        if len(items) >= max_items:
            break
    return items


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            raise RuntimeError(
                ".env 에 ANTHROPIC_API_KEY 가 없습니다. console.anthropic.com 에서 발급받아 추가하세요."
            )
        _client = anthropic.Anthropic(api_key=api_key)
    return _client


def judge_sentiment(name: str, news_items: list[dict]) -> dict:
    """뉴스 제목들을 보고 이 종목에 대해 종합적으로 호재/악재/중립 중 하나로 판단한다.
    반환: {"verdict": "호재"|"악재"|"중립", "reason": str}"""
    if not news_items:
        return {"verdict": "중립", "reason": "최근 뉴스 없음"}

    headlines = "\n".join(f"- ({n['date']}, {n['press']}) {n['title']}" for n in news_items)
    prompt = (
        f"다음은 '{name}' 종목의 최근 뉴스 제목 목록이다. 이 뉴스들이 이 종목 주가에 "
        f"전반적으로 호재인지 악재인지 중립인지 판단하라. 제목만으로 확신이 서지 않으면 "
        f"중립으로 답하라. 과장하지 말고 보수적으로 판단하라.\n\n"
        f"{headlines}\n\n"
        f'다음 JSON 형식으로만 답하라(다른 텍스트 없이): '
        f'{{"verdict": "호재 또는 악재 또는 중립", "reason": "한 문장 이유"}}'
    )

    client = _get_client()
    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=200,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()

    # 모델이 ```json ... ``` 코드블록으로 감싸는 경우 대비
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        verdict = data.get("verdict", "중립")
        if verdict not in ("호재", "악재", "중립"):
            verdict = "중립"
        return {"verdict": verdict, "reason": str(data.get("reason", ""))}
    except Exception:
        return {"verdict": "중립", "reason": f"판단 응답 파싱 실패: {text[:100]}"}
