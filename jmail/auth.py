from __future__ import annotations

import base64
import hmac
import json
import os
import re
import time
from dataclasses import dataclass
from hashlib import pbkdf2_hmac, sha256
from typing import Any, Dict

from .config import AppConfig
from .database import Database

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass(slots=True)
class AuthResult:
    token: str
    user: Dict[str, Any]


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    hash_bytes = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{_b64encode(salt)}${_b64encode(hash_bytes)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt_b64, hash_b64 = stored.split("$")
    except ValueError:
        return False
    salt = _b64decode(salt_b64)
    expected = _b64decode(hash_b64)
    actual = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(expected, actual)


def generate_token(*, user_id: int, config: AppConfig) -> str:
    header = {"alg": "HS256", "typ": "JWT"}
    now = int(time.time())
    payload = {"sub": user_id, "iat": now, "exp": now + config.token_exp_seconds}
    signing_input = ".".join(
        _b64encode(json.dumps(part, separators=(",", ":")).encode("utf-8"))
        for part in (header, payload)
    )
    signature = hmac.new(config.jwt_secret.encode("utf-8"), signing_input.encode("utf-8"), sha256).digest()
    return f"{signing_input}.{_b64encode(signature)}"


def decode_token(token: str, *, config: AppConfig) -> Dict[str, Any]:
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise ValueError("Malformed token") from exc

    signing_input = f"{header_b64}.{payload_b64}"
    expected_sig = hmac.new(
        config.jwt_secret.encode("utf-8"), signing_input.encode("utf-8"), sha256
    ).digest()
    if not hmac.compare_digest(expected_sig, _b64decode(signature_b64)):
        raise ValueError("Invalid signature")

    payload = json.loads(_b64decode(payload_b64))
    if int(time.time()) >= int(payload.get("exp", 0)):
        raise ValueError("Token expired")
    return payload


def validate_email(address: str) -> str:
    if not EMAIL_REGEX.match(address):
        raise ValueError("Invalid email address")
    return address


def authenticate_user(db: Database, email: str, password: str, config: AppConfig) -> AuthResult:
    row = db.get_user_by_email(email)
    if row is None or not verify_password(password, row["password_hash"]):
        raise ValueError("Invalid email or password")

    token = generate_token(user_id=row["id"], config=config)
    return AuthResult(token=token, user=row_to_dict(row))


def register_user(db: Database, email: str, password: str, display_name: str | None, config: AppConfig) -> AuthResult:
    validate_email(email)
    if db.get_user_by_email(email) is not None:
        raise ValueError("Email already registered")

    password_hash = hash_password(password)
    user_id = db.create_user(email=email, password_hash=password_hash, display_name=display_name)
    row = db.get_user_by_id(user_id)
    token = generate_token(user_id=user_id, config=config)
    return AuthResult(token=token, user=row_to_dict(row))


def row_to_dict(row: Any) -> Dict[str, Any]:
    created_at = row["created_at"]
    if hasattr(created_at, "isoformat"):
        created_at_value = created_at.isoformat()
    else:
        created_at_value = str(created_at)
    return {
        "id": row["id"],
        "email": row["email"],
        "display_name": row["display_name"],
        "created_at": created_at_value,
    }


__all__ = [
    "AuthResult",
    "authenticate_user",
    "register_user",
    "decode_token",
    "validate_email",
    "row_to_dict",
]
