"""
한국투자증권(KIS) OAuth 접근토큰 발급/캐싱.

토큰은 발급 후 약 24시간 유효합니다. 매번 새로 발급받으면 API 서버가
너무 잦은 발급 요청으로 보고 거부할 수 있어서, 로컬 파일에 캐싱해두고
만료 임박 시에만 새로 발급받습니다.
"""
import json
import time

import requests

from common import Config, TOKEN_CACHE_PATH

# 토큰을 실제 만료시간보다 여유 있게 미리 갱신한다.
REFRESH_MARGIN_SEC = 60 * 30


def _load_cache() -> dict:
    if TOKEN_CACHE_PATH.exists():
        try:
            return json.loads(TOKEN_CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_cache(data: dict) -> None:
    TOKEN_CACHE_PATH.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def get_access_token(cfg: Config) -> str:
    cache = _load_cache()
    entry = cache.get(cfg.mode)
    now = time.time()

    if entry and entry.get("expires_at", 0) - REFRESH_MARGIN_SEC > now:
        return entry["access_token"]

    res = requests.post(
        f"{cfg.base_url}/oauth2/tokenP",
        json={
            "grant_type": "client_credentials",
            "appkey": cfg.app_key,
            "appsecret": cfg.app_secret,
        },
        timeout=10,
    )
    res.raise_for_status()
    body = res.json()

    token = body["access_token"]
    expires_in = int(body.get("expires_in", 60 * 60 * 24))

    cache[cfg.mode] = {"access_token": token, "expires_at": now + expires_in}
    _save_cache(cache)
    return token


def get_hashkey(cfg: Config, body: dict) -> str:
    """주문 등 일부 POST 요청에 필요한 요청 본문 해시값."""
    res = requests.post(
        f"{cfg.base_url}/uapi/hashkey",
        headers={
            "content-type": "application/json",
            "appkey": cfg.app_key,
            "appsecret": cfg.app_secret,
        },
        json=body,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()["HASH"]
