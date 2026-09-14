from __future__ import annotations

import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from api.main import make_handler
from pipeline.run import Pipeline


class _ExplodingPipeline:
    artifact_hash = "x"

    def analyze(self, text: str, trace_id: str | None = None):
        raise RuntimeError("boom")


class ApiTest(unittest.TestCase):
    def serve(self, pipeline) -> http.client.HTTPConnection:
        server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(pipeline))
        server.RequestHandlerClass.log_message = lambda *args: None  # keep test output quiet
        server.RequestHandlerClass.log_error = lambda *args: None
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        return http.client.HTTPConnection("127.0.0.1", server.server_address[1], timeout=5)

    def post(self, conn: http.client.HTTPConnection, body: bytes, headers: dict | None = None) -> tuple[int, dict]:
        conn.request("POST", "/analyze", body=body, headers=headers or {"Content-Type": "application/json"})
        response = conn.getresponse()
        return response.status, json.loads(response.read().decode("utf-8"))

    def test_analyze_returns_contract(self) -> None:
        status, data = self.post(self.serve(Pipeline()), json.dumps({"text": "Bu bir test"}).encode())
        self.assertEqual(status, 200)
        self.assertIn("verdict", data)

    def test_bad_requests_get_400_not_a_crash(self) -> None:
        conn = self.serve(Pipeline())
        for body in (b"not json", b"[1, 2]", json.dumps({"text": 5}).encode(), json.dumps({"txt": "x"}).encode(),
                     json.dumps({"text": "x", "trace_id": 7}).encode(), b"\xff\xfe"):
            with self.subTest(body=body):
                status, data = self.post(conn, body)
                self.assertEqual(status, 400)
                self.assertIn("error", data)

    def test_invalid_content_length_gets_400(self) -> None:
        conn = self.serve(Pipeline())
        conn.putrequest("POST", "/analyze")
        conn.putheader("Content-Length", "abc")
        conn.endheaders()
        response = conn.getresponse()
        self.assertEqual(response.status, 400)
        self.assertIn("Content-Length", json.loads(response.read())["error"])

    def test_pipeline_failure_gets_500_json(self) -> None:
        status, data = self.post(self.serve(_ExplodingPipeline()), json.dumps({"text": "x"}).encode())
        self.assertEqual(status, 500)
        self.assertEqual(data["error"], "internal error: RuntimeError")


if __name__ == "__main__":
    unittest.main()
