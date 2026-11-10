import base64
import binascii
import hashlib
import hmac
import json
import os
import threading
import time
from collections import defaultdict, deque

from .errors import ApiError

_requests: dict[str, deque[float]] = defaultdict(deque)
_lock = threading.Lock()


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def authenticate(authorization: str | None) -> dict:
    secret = os.getenv("JWT_SECRET", "")
    production = os.getenv("ENVIRONMENT", "development").lower() == "production"
    if not secret and not production:
        return {"sub": "local"}
    if not secret:
        raise ApiError(503, "음성 인증 설정이 완료되지 않았습니다.")
    if not authorization or not authorization.startswith("Bearer "):
        raise ApiError(401, "로그인이 필요합니다.")
    try:
        token = authorization.removeprefix("Bearer ").strip()
        header, payload, signature = token.split(".")
        expected = hmac.new(base64.b64decode(secret), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _decode(signature)):
            raise ValueError
        claims = json.loads(_decode(payload))
        if claims.get("type") != "access" or claims.get("role") not in {"CUSTOMER", "STAFF"}:
            raise ValueError
        if float(claims.get("exp", 0)) <= time.time():
            raise ValueError
        return claims
    except (ValueError, TypeError, KeyError, json.JSONDecodeError, binascii.Error):
        raise ApiError(401, "유효하지 않거나 만료된 인증 정보입니다.")


def enforce_rate_limit(subject: str) -> None:
    if not os.getenv("JWT_SECRET") and os.getenv("ENVIRONMENT", "development").lower() != "production":
        return
    limit = int(os.getenv("VOICE_REQUESTS_PER_MINUTE", "10"))
    now = time.monotonic()
    with _lock:
        bucket = _requests[subject]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            raise ApiError(429, "음성 요청이 너무 많습니다. 잠시 후 다시 시도해 주세요.")
        bucket.append(now)
