from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable

from .auth import authenticate_user, decode_token, register_user, row_to_dict, validate_email
from .config import AppConfig, load_config
from .database import Database
from .email_service import EmailConfigurationError, send_email
from .http import Request, Response, build_request, json_response, to_wsgi


class HTTPError(Exception):
    def __init__(self, message: str, status: int) -> None:
        super().__init__(message)
        self.status = status


class UnauthorizedError(HTTPError):
    def __init__(self, message: str = "Unauthorized") -> None:
        super().__init__(message, 401)


class BadRequestError(HTTPError):
    def __init__(self, message: str = "Bad request") -> None:
        super().__init__(message, 400)


class ConflictError(HTTPError):
    def __init__(self, message: str = "Conflict") -> None:
        super().__init__(message, 409)


@dataclass(slots=True)
class JmailApplication:
    config: AppConfig
    db: Database

    def __call__(
        self,
        environ: dict[str, Any],
        start_response: Callable[[str, list[tuple[str, str]]], Callable[[bytes], None]] | Callable[[str, list[tuple[str, str]]], None],
    ):
        request = build_request(environ)
        try:
            response = self.dispatch(request)
        except HTTPError as error:
            response = json_response({"error": str(error)}, status=error.status)
        except EmailConfigurationError as error:
            response = json_response({"error": str(error)}, status=500)
        except Exception:  # pragma: no cover
            response = json_response({"error": "Internal server error"}, status=500)
        status, headers, body = to_wsgi(response)
        start_response(status, headers)
        return [body]

    def dispatch(self, request: Request) -> Response:
        if request.path == "/api/health" and request.method == "GET":
            return json_response({"status": "ok"})
        if request.path == "/api/register" and request.method == "POST":
            return self.handle_register(request)
        if request.path == "/api/login" and request.method == "POST":
            return self.handle_login(request)
        if request.path == "/api/profile" and request.method == "GET":
            return self.handle_profile(request)
        if request.path == "/api/send" and request.method == "POST":
            return self.handle_send(request)
        return json_response({"error": "Not found"}, status=404)

    def _parse_json(self, request: Request) -> dict[str, Any]:
        try:
            return request.json()
        except json.JSONDecodeError as exc:
            raise BadRequestError("Invalid JSON payload") from exc

    def handle_register(self, request: Request) -> Response:
        payload = self._parse_json(request)
        email = payload.get("email", "").strip().lower()
        password = payload.get("password", "")
        display_name = payload.get("display_name")

        if not email or not password:
            raise BadRequestError("Email and password are required")
        try:
            validate_email(email)
            result = register_user(self.db, email, password, display_name, self.config)
        except ValueError as exc:
            message = str(exc)
            if "already" in message:
                raise ConflictError(message) from exc
            raise BadRequestError(message) from exc

        return json_response({"token": result.token, "user": result.user})

    def handle_login(self, request: Request) -> Response:
        payload = self._parse_json(request)
        email = payload.get("email", "").strip().lower()
        password = payload.get("password", "")

        if not email or not password:
            raise BadRequestError("Email and password are required")
        try:
            result = authenticate_user(self.db, email, password, self.config)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc

        return json_response({"token": result.token, "user": result.user})

    def _require_user(self, request: Request) -> dict[str, Any]:
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            raise UnauthorizedError("Missing Authorization header")
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token, config=self.config)
        except ValueError as exc:
            raise UnauthorizedError(str(exc)) from exc
        user_id = payload.get("sub")
        if user_id is None:
            raise UnauthorizedError("Token missing subject")
        row = self.db.get_user_by_id(int(user_id))
        if row is None:
            raise UnauthorizedError("User not found")
        return row_to_dict(row)

    def handle_profile(self, request: Request) -> Response:
        user = self._require_user(request)
        return json_response({"user": user})

    def handle_send(self, request: Request) -> Response:
        self._require_user(request)
        payload = self._parse_json(request)
        recipient = payload.get("to", "").strip()
        subject = payload.get("subject", "").strip()
        body = payload.get("body", "").strip()
        reply_to = payload.get("reply_to")

        if not recipient or not subject or not body:
            raise BadRequestError("Recipient, subject, and body are required")
        try:
            validate_email(recipient)
            if reply_to:
                validate_email(reply_to)
        except ValueError as exc:
            raise BadRequestError(str(exc)) from exc

        send_email(config=self.config, recipient=recipient, subject=subject, body=body, reply_to=reply_to)
        return json_response({"status": "sent"})


def create_app(config: AppConfig | None = None) -> JmailApplication:
    app_config = config or load_config()
    database = Database(app_config.database_path)
    return JmailApplication(config=app_config, db=database)


__all__ = ["create_app", "AppConfig", "JmailApplication"]
