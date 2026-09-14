"""Minimal offline HTTP API over the pipeline. Standard library only.

    python -m api.main [--host 127.0.0.1] [--port 8080]

    GET  /health            -> {"status": "ok", "artifact_hash": ...}
    POST /analyze {"text"}  -> full AnalysisResult contract JSON

Every request gets a JSON response: 400 for a bad request, 413 for an
oversized body, 500 (with the exception type, never a dropped connection) if
anything unexpected fails. No auth, no TLS: meant to sit behind the
platform's own gateway.
"""
from __future__ import annotations

import argparse
import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from pipeline.run import Pipeline

MAX_BODY_BYTES = 64 * 1024


class BadRequest(Exception):
    def __init__(self, status: HTTPStatus, message: str) -> None:
        super().__init__(message)
        self.status = status


def _parse_request(headers: Any, rfile: Any) -> tuple[str, str | None]:
    raw_length = headers.get("Content-Length")
    try:
        length = int(raw_length or 0)
    except ValueError:
        raise BadRequest(HTTPStatus.BAD_REQUEST, f"invalid Content-Length: {raw_length!r}") from None
    if length < 0:
        raise BadRequest(HTTPStatus.BAD_REQUEST, "negative Content-Length")
    if length > MAX_BODY_BYTES:
        raise BadRequest(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "body too large")
    try:
        payload = json.loads(rfile.read(length).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BadRequest(HTTPStatus.BAD_REQUEST, f"body is not UTF-8 JSON: {exc}") from None
    if not isinstance(payload, dict):
        raise BadRequest(HTTPStatus.BAD_REQUEST, "body must be a JSON object")
    text = payload.get("text")
    if not isinstance(text, str):
        raise BadRequest(HTTPStatus.BAD_REQUEST, "text must be a string")
    trace_id = payload.get("trace_id")
    if trace_id is not None and not isinstance(trace_id, str):
        raise BadRequest(HTTPStatus.BAD_REQUEST, "trace_id must be a string")
    return text, trace_id


def make_handler(pipeline: Pipeline) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _guarded(self, handle: Any) -> None:
            try:
                handle()
            except BadRequest as exc:
                self._send(exc.status, {"error": str(exc)})
            except Exception as exc:  # never drop the connection without an answer
                self.log_error("unhandled %s: %s", type(exc).__name__, exc)
                self._send(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": f"internal error: {type(exc).__name__}"})

        def do_GET(self) -> None:  # noqa: N802 - http.server naming
            def handle() -> None:
                if self.path == "/health":
                    self._send(HTTPStatus.OK, {"status": "ok", "artifact_hash": pipeline.artifact_hash})
                else:
                    self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})

            self._guarded(handle)

        def do_POST(self) -> None:  # noqa: N802
            def handle() -> None:
                if self.path != "/analyze":
                    self._send(HTTPStatus.NOT_FOUND, {"error": "not found"})
                    return
                text, trace_id = _parse_request(self.headers, self.rfile)
                self._send(HTTPStatus.OK, pipeline.analyze(text, trace_id=trace_id).to_dict())

            self._guarded(handle)

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
