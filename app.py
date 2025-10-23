from __future__ import annotations

from wsgiref.simple_server import make_server

from jmail import create_app

app = create_app()


if __name__ == "__main__":
    with make_server("0.0.0.0", 8000, app) as server:
        print("Serving on http://0.0.0.0:8000")
        server.serve_forever()
