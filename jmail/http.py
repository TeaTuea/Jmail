from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Callable
from wsgiref.util import setup_testing_defaults


@dataclass(slots=True)
class Request:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes

    def json(self) -> dict[str, Any]:
        if not self.body:
            return {}
        return json.loads(self.body.decode("utf-8"))


@dataclass(slots=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


def json_response(payload: dict[str, Any], status: int = 200) -> Response:
    return Response(status=status, headers={"Content-Type": "application/json"}, body=json.dumps(payload).encode("utf-8"))


def build_request(environ: dict[str, Any]) -> Request:
    setup_testing_defaults(environ)
    method = environ.get("REQUEST_METHOD", "GET")
    path = environ.get("PATH_INFO", "/")
    headers = {
        key[5:].replace("_", "-").title(): value
        for key, value in environ.items()
        if key.startswith("HTTP_")
    }
    if "CONTENT_TYPE" in environ:
        headers["Content-Type"] = environ["CONTENT_TYPE"]
    length = int(environ.get("CONTENT_LENGTH") or 0)
    body = environ["wsgi.input"].read(length) if length else b""
    return Request(method=method, path=path, headers=headers, body=body)


def to_wsgi(response: Response) -> tuple[str, list[tuple[str, str]], bytes]:
    status_text = {
        200: "200 OK",
        201: "201 Created",
        204: "204 No Content",
        400: "400 Bad Request",
        401: "401 Unauthorized",
        404: "404 Not Found",
        409: "409 Conflict",
        500: "500 Internal Server Error",
    }.get(response.status, f"{response.status} Unknown")
    headers = [(key, value) for key, value in response.headers.items()]
    if "Content-Length" not in response.headers:
        headers.append(("Content-Length", str(len(response.body))))
    return status_text, headers, response.body


WSGIApp = Callable[[dict[str, Any], Callable[[str, list[tuple[str, str]]], Callable[[bytes], None]]], list[bytes]]
