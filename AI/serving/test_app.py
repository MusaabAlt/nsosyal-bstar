"""Tests for the inference service. Skipped when FastAPI is not installed."""
from __future__ import annotations

import unittest

try:
    from fastapi.testclient import TestClient
except ImportError:  # the service's dependencies are optional for module owners
    TestClient = None  # type: ignore[assignment,misc]


class FakeResult:
    def __init__(self, text: str, trace_id: str) -> None:
        self.text, self.trace_id = text, trace_id

    def to_dict(self) -> dict:
        if self.text == "boom":
            raise RuntimeError("model crashed")
        return {
            "text": self.text,
            "trace_id": self.trace_id,
            "verdict": "review",
            "signals": {"pipeline": {"degraded": [{"module": "m2_deobf", "kinds": ["stub"], "reasons": []}]}},
        }


class FakePipeline:
    artifact_hash = "fake-hash"

    def analyze(self, text: str, trace_id: str | None = None) -> FakeResult:
        return FakeResult(text, trace_id or "")


@unittest.skipIf(TestClient is None, "fastapi not installed (pip install -r serving/requirements.txt)")
class ServingTest(unittest.TestCase):
    def make(self, loaded: bool = True):
        from serving.app import State, create_app

        state = State()
        if loaded:
            state.load(FakePipeline)
        return state, TestClient(create_app(state, load_in_background=False))

    def test_health_reports_degraded_modules_and_capabilities(self) -> None:
        _, client = self.make()
        body = client.get("/health").json()
        self.assertEqual(body["status"], "ok")
        self.assertEqual(body["artifact_hash"], "fake-hash")
        self.assertEqual(body["degraded_modules"], ["m2_deobf"])
        self.assertFalse(body["representative"])
        codes = [c["code"] for c in body["capabilities"]]
        self.assertEqual(codes, ["A1", "A2", "A3", "B1", "B2", "B3", "B4", "binary_offensive"])
        # Every capability names the module that produces it, so the panel can
        # mark it "Modül hazır değil" from /health's degraded_modules.
        self.assertTrue(all(c["module"] for c in body["capabilities"]))

    def test_loading_answers_503(self) -> None:
        _, client = self.make(loaded=False)
        self.assertEqual(client.get("/health").json()["status"], "loading")
        response = client.post("/predict_batch", json={"items": [{"id": "a", "text": "x"}]})
        self.assertEqual(response.status_code, 503)

    def test_batch_returns_results_by_id_and_text_unchanged(self) -> None:
        _, client = self.make()
        response = client.post("/predict_batch", json={"items": [
            {"id": "a", "text": "  S4l4K  "},
            {"id": "b", "text": "amcam geldi"},
        ]})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["artifact_hash"], "fake-hash")
        by_id = {r["id"]: r for r in body["results"]}
        self.assertTrue(by_id["a"]["ok"])
        self.assertEqual(by_id["a"]["result"]["text"], "  S4l4K  ")  # never trimmed or normalized
        self.assertEqual(by_id["a"]["result"]["trace_id"], "a")

    def test_one_failing_item_does_not_fail_the_batch(self) -> None:
        _, client = self.make()
        body = client.post("/predict_batch", json={"items": [
            {"id": "a", "text": "boom"},
            {"id": "b", "text": "fine"},
        ]}).json()
        results = {r["id"]: r for r in body["results"]}
        self.assertFalse(results["a"]["ok"])
        self.assertEqual(results["a"]["error"], "internal error: RuntimeError")
        self.assertTrue(results["b"]["ok"])

    def test_load_failure_is_reported_not_raised(self) -> None:
        from serving.app import State, create_app

        def broken():
            raise OSError("checkpoint missing")

        state = State()
        state.load(broken)
        body = TestClient(create_app(state, load_in_background=False)).get("/health").json()
        self.assertEqual(body["status"], "error")
        self.assertIn("checkpoint missing", body["error"])

    def test_oversized_text_is_rejected(self) -> None:
        _, client = self.make()
        response = client.post("/predict_batch", json={"items": [{"id": "a", "text": "x" * 5001}]})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
