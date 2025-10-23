from __future__ import annotations

import io
import json
import os
import sys
import tempfile
from collections import deque
from pathlib import Path
from typing import Any, Callable

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import jmail
from jmail import AppConfig, create_app


class WSGIResponse:
    def __init__(self, status: str, headers: list[tuple[str, str]], body: bytes) -> None:
        self.status = status
        self.headers = headers
        self.body = body

    @property
    def status_code(self) -> int:
        return int(self.status.split(" ", 1)[0])

    def json(self) -> dict[str, Any]:
        return json.loads(self.body.decode("utf-8"))


def call_wsgi(app: Callable, method: str, path: str, *, json_payload: dict[str, Any] | None = None, headers: dict[str, str] | None = None) -> WSGIResponse:
    headers = headers or {}
    body_bytes = b""
    environ: dict[str, Any] = {
        "REQUEST_METHOD": method,
        "PATH_INFO": path,
        "SERVER_NAME": "localhost",
        "SERVER_PORT": "80",
        "wsgi.version": (1, 0),
        "wsgi.url_scheme": "http",
        "wsgi.input": io.BytesIO(),
    }
    if json_payload is not None:
        body_bytes = json.dumps(json_payload).encode("utf-8")
        environ["wsgi.input"] = io.BytesIO(body_bytes)
        environ["CONTENT_LENGTH"] = str(len(body_bytes))
        environ["CONTENT_TYPE"] = "application/json"
    for key, value in headers.items():
        environ[f"HTTP_{key.upper().replace('-', '_')}"] = value

    status_holder: dict[str, Any] = {}
    header_holder: dict[str, Any] = {}

    def start_response(status: str, response_headers: list[tuple[str, str]]):
        status_holder["status"] = status
        header_holder["headers"] = response_headers

    result = app(environ, start_response)
    body = b"".join(result)
    return WSGIResponse(status_holder["status"], header_holder["headers"], body)


@pytest.fixture()
def test_app():
    with tempfile.TemporaryDirectory() as tmpdir:
        config = AppConfig(
            database_path=Path(tmpdir) / "test.db",
            jwt_secret="test-secret",
            token_exp_seconds=3600,
            smtp_host="smtp.test",
            smtp_port=587,
            smtp_username="sender@example.com",
            smtp_password="password",
            smtp_use_tls=True,
            smtp_from_email="sender@example.com",
            smtp_from_name="Jmail",
        )
        app = create_app(config)
        yield app


def test_register_and_login_flow(monkeypatch, test_app):
    sent_messages = deque()

    monkeypatch.setattr(jmail, "send_email", lambda **kwargs: sent_messages.append(kwargs))

    register_resp = call_wsgi(
        test_app,
        "POST",
        "/api/register",
        json_payload={"email": "alice@example.com", "password": "password123", "display_name": "Alice"},
    )
    assert register_resp.status_code == 200
    token = register_resp.json()["token"]
    assert token

    profile_resp = call_wsgi(
        test_app,
        "GET",
        "/api/profile",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert profile_resp.status_code == 200
    assert profile_resp.json()["user"]["email"] == "alice@example.com"

    login_resp = call_wsgi(
        test_app,
        "POST",
        "/api/login",
        json_payload={"email": "alice@example.com", "password": "password123"},
    )
    assert login_resp.status_code == 200
    assert login_resp.json()["user"]["display_name"] == "Alice"

    send_resp = call_wsgi(
        test_app,
        "POST",
        "/api/send",
        json_payload={
            "to": "friend@example.com",
            "subject": "Hello",
            "body": "Hi there",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert send_resp.status_code == 200
    assert sent_messages


def test_send_email_requires_auth(test_app):
    resp = call_wsgi(
        test_app,
        "POST",
        "/api/send",
        json_payload={"to": "friend@example.com", "subject": "Hello", "body": "Hi"},
    )
    assert resp.status_code == 401


def test_invalid_email_registration(test_app):
    resp = call_wsgi(
        test_app,
        "POST",
        "/api/register",
        json_payload={"email": "invalid", "password": "password123"},
    )
    assert resp.status_code == 400
