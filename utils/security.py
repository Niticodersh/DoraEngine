"""Password hashing and signed-token helpers."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time

from utils.config import get_secret


_TOKEN_EXPIRY_SECONDS = 60 * 60 * 24 * 7


def _secret_key() -> str:
    return get_secret("AUTH_SECRET_KEY", "change-me-in-production")


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    return f"{salt}${base64.urlsafe_b64encode(digest).decode('ascii')}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, expected = password_hash.split("$", 1)
    except ValueError:
        return False

    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120000)
    candidate = base64.urlsafe_b64encode(digest).decode("ascii")
    return hmac.compare_digest(candidate, expected)


def create_token(payload: dict, expires_in: int = _TOKEN_EXPIRY_SECONDS) -> str:
    token_payload = dict(payload)
    token_payload["exp"] = int(time.time()) + expires_in
    body = base64.urlsafe_b64encode(json.dumps(token_payload, separators=(",", ":")).encode("utf-8")).decode("ascii")
    signature = hmac.new(_secret_key().encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{body}.{signature}"


def decode_token(token: str) -> dict:
    try:
        body, signature = token.split(".", 1)
    except ValueError as exc:
        raise ValueError("Invalid token format") from exc

    expected = hmac.new(_secret_key().encode("utf-8"), body.encode("utf-8"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(signature, expected):
        raise ValueError("Invalid token signature")

    payload = json.loads(base64.urlsafe_b64decode(body.encode("ascii")).decode("utf-8"))
    if payload.get("exp", 0) < int(time.time()):
        raise ValueError("Token expired")
    return payload
