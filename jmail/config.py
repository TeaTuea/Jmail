from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _env_bool(name: str, default: bool = True) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.lower() not in {"false", "0", "no"}


@dataclass(slots=True)
class AppConfig:
    database_path: Path
    jwt_secret: str
    token_exp_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_from_email: str
    smtp_from_name: str


def load_config() -> AppConfig:
    smtp_username = os.getenv("SMTP_USERNAME", "")
    return AppConfig(
        database_path=Path(os.getenv("DATABASE_PATH", "jmail.db")),
        jwt_secret=os.getenv("JWT_SECRET", "change-me"),
        token_exp_seconds=int(os.getenv("TOKEN_EXP_SECONDS", "3600")),
        smtp_host=os.getenv("SMTP_HOST", ""),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_username=smtp_username,
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        smtp_use_tls=_env_bool("SMTP_USE_TLS", True),
        smtp_from_email=os.getenv("SMTP_FROM_EMAIL", smtp_username),
        smtp_from_name=os.getenv("SMTP_FROM_NAME", "Jmail"),
    )


__all__ = ["AppConfig", "load_config"]
