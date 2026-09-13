"""Minimal offline HTTP API over the pipeline. Standard library only.

    python -m api.main [--host 127.0.0.1] [--port 8080]

    GET  /health            -> {"status": "ok", "artifact_hash": ...}
    POST /analyze {"text"}  -> full AnalysisResult contract JSON

No auth, no TLS: meant to sit behind the platform's own gateway.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from pipeline.run import Pipeline

MAX_BODY_BYTES = 64 * 1024


def make_handler(pipeline: Pipeline) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:  # noqa: N802 - http.server naming
            if self.path == "/health":
                self._send(HTTPStatus.OK, {"status": "ok", "artifact_hash": pipeline.artifact_hash})
            else:
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/analyze":
                self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
                return
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY_BYTES:
                self._send(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "body too large"})
                return
            try:
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                text = payload["text"]
                if not isinstance(text, str):
                    raise TypeError("text must be a string")
            except (ValueError, KeyError, TypeError) as exc:
                self._send(HTTPStatus.BAD_REQUEST, {"error": f"invalid request: {exc}"})
                return
            result = pipeline.analyze(text, trace_id=payload.get("trace_id"))
            self._send(HTTPStatus.OK, result.to_dict())

    return Handler


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m api.main")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8080)
    args = parser.parse_args(argv)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(Pipeline()))
    print(f"serving on http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
