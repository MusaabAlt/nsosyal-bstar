"""FastAPI inference service: the one bridge between the Go backend and the pipeline.

    python -m uvicorn serving.app:create_app --factory --host 127.0.0.1 --port 8001   (from AI/)

Listens on localhost only; the Go backend is its only client and starts it
(backend config `python`). Contract: backend/docs/inference-contract.md.

    GET  /health         {"status": "loading" | "ok" | "error", "artifact_hash",
                          "degraded_modules", "capabilities", "representative": false}
    POST /predict_batch  {"items": [{"id", "text"}]}
                         -> {"artifact_hash", "results": [{"id", "ok", "result" | "error"}]}

What it does NOT do: decide anything, change the text, or touch the frozen
AnalysisResult. It runs `Pipeline.analyze` and returns `to_dict()` unchanged.

Model loading (BERTurk) takes a while, so the pipeline is built in a
background thread; until then /health says "loading" and /predict_batch
answers 503, which the Go backend treats as "retry when healthy".
"""
from __future__ import annotations

import logging
import threading
import time
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from serving.capabilities import CAPABILITIES

log = logging.getLogger("serving")

# The warm-up text: loads every module once and tells /health which modules
# are degraded (the pipeline reports that per analysis, not per module).
WARMUP_TEXT = "Bu bir test cumlesi"
MAX_ITEMS = 64


class Item(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    text: str = Field(max_length=5000)


class BatchRequest(BaseModel):
    items: list[Item] = Field(max_length=MAX_ITEMS)


class State:
    """The pipeline and what /health reports. Replaced in tests."""

    def __init__(self) -> None:
        self.pipeline: Any = None
        self.status = "loading"
        self.error: str | None = None
        self.degraded_modules: list[str] = []
        # Pipeline modules are not documented as thread-safe (m3 holds a torch
        # model): one analysis at a time. Go already bounds concurrency.
        self.lock = threading.Lock()

    def load(self, factory: Any = None) -> None:
        started = time.perf_counter()
        try:
            if factory is None:
                from pipeline.run import Pipeline  # imported here: loading is the slow part

                factory = Pipeline
            pipeline = factory()
            warm = pipeline.analyze(WARMUP_TEXT, trace_id="serving-warmup").to_dict()
            degraded = warm.get("signals", {}).get("pipeline", {}).get("degraded", [])
            self.degraded_modules = [d["module"] for d in degraded]
            self.pipeline = pipeline
            self.status = "ok"
            log.info("pipeline ready in %.1fs, degraded: %s", time.perf_counter() - started, self.degraded_modules)
        except Exception as exc:  # the service stays up and says why
            self.status = "error"
            self.error = f"{type(exc).__name__}: {exc}"
            log.exception("pipeline failed to load")


def create_app(state: State | None = None, load_in_background: bool = True) -> FastAPI:
    state = state or State()
    app = FastAPI(title="NSosyal inference", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.inference = state

    if load_in_background and state.pipeline is None and state.status == "loading":
        threading.Thread(target=state.load, name="pipeline-loader", daemon=True).start()

    @app.get("/health")
    def health() -> dict[str, Any]:
        body: dict[str, Any] = {
            "status": state.status,
            "artifact_hash": getattr(state.pipeline, "artifact_hash", ""),
            "degraded_modules": state.degraded_modules,
            "capabilities": list(CAPABILITIES),
            "representative": False,
        }
        if state.error:
            body["error"] = state.error
        return body

    @app.post("/predict_batch")
    def predict_batch(request: BatchRequest) -> Any:
        if state.status != "ok" or state.pipeline is None:
            return JSONResponse(status_code=503, content={"status": state.status})
        pipeline = state.pipeline
        results: list[dict[str, Any]] = []
        for item in request.items:
            try:
                with state.lock:
                    result = pipeline.analyze(item.text, trace_id=item.id).to_dict()
                # normalization: m2 is a stub; when it lands, add its text and changes here.
                results.append({"id": item.id, "ok": True, "result": result})
            except Exception as exc:  # one text failing never fails the batch
                log.exception("analysis failed for %s", item.id)
                results.append({"id": item.id, "ok": False, "error": f"internal error: {type(exc).__name__}"})
        return {"artifact_hash": pipeline.artifact_hash, "results": results}

    return app

