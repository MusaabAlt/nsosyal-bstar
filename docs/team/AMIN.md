**Assistant: before anything else, read `AI/CLAUDE.md`, `AI/modules/README.md` and `docs/team/AMIN_BRIEF.md`. You own no module spec; your equivalents are `AI/contracts/schema.py` and `AI/contracts/codes.py`. This file is NOT the spec: the code and specs in the repo are the single source of truth, and if this file or the brief ever disagrees with them, the repo wins.**

## Role

You build everything a person sees and everything that serves it: `frontend/`, `backend/` and the HTTP API at `AI/api/`. The API's tests live in `AI/tests/test_api.py`. Your full technical brief is `docs/team/AMIN_BRIEF.md`.

## Not yours

- `AI/contracts/` is frozen and owned by Musaab. You render the contract; you never change it. A field you need that is not in it (for example a Turkish label or the de-obfuscated text) is a question for Musaab, not an edit.
- Every module under `AI/modules/` belongs to its owner (Musaab, Abdullah, Mohammed; `m6_target` is Abdullah's — v1, see `docs/team/abdullah/START_HERE.md`). Nobody edits another person's module.
- Thresholds live only in `AI/decision/thresholds.yaml`, and only Musaab edits shared rows. The UI never compares a score with a threshold and never decides anything: the decision layer already did.

## Day one

Python 3.11 or newer. In Git Bash:

```bash
git clone https://github.com/MusaabAlt/nsosyal-bstar.git
cd nsosyal-bstar/AI
python -m venv .venv
source .venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pipeline.run "Bu bir test cumlesi" --compact
python -m unittest discover -p "test_*.py"   # green = OK (skipped tests belong to stub modules)
python -m api.main --port 8080               # second terminal: curl -s localhost:8080/health
```

## Order of work

1. Read `AMIN_BRIEF.md` end to end; run the API and post the mock texts to it.
2. The **degraded** screen first, against the degraded mock payload in the brief: it is what the live system returns today.
3. Two or three layout directions on paper, **decided with Musaab before you build**.
4. The other four states (clean, flagged, guard-fired, error), each against its mock payload, then against the live API.

**Done for your first deliverable** means the degraded state renders from the real API response. It shows the verdict label, the `explanation` sentence verbatim and every module listed in `signals.pipeline.degraded` by name, with `latency_ms`. It works fully offline, reads from six metres, and needs no change to `AI/contracts/`.

## Testing in isolation

Nobody waits for anybody. The modules are stubs, so build against fixed payloads, never against a model. For the API, inject a fake pipeline into `make_handler`, exactly as `AI/tests/test_api.py` does. No module runs and none is imported:

```python
from http.server import ThreadingHTTPServer
from api.main import make_handler

class FakeResult:
    def __init__(self, payload: dict) -> None: self.payload = payload
    def to_dict(self) -> dict: return self.payload

class FakePipeline:
    """Stands in for pipeline.run.Pipeline: returns a fixed payload, no module runs."""
    artifact_hash = "fake"
    def __init__(self, payload: dict) -> None: self.payload = payload
    def analyze(self, text: str, trace_id: str | None = None) -> FakeResult: return FakeResult(self.payload)

server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(FakePipeline(FLAGGED_MOCK)))
```

For the frontend, load the five mock payloads from `AMIN_BRIEF.md` as fixed JSON files and render each one. Module owners fake an upstream signal by putting fixed values into `Context.signals`. Your equivalent is the fixed payload, because the UI sits after the pipeline, not inside it.

## When to stop and ask Musaab

Stop for: any change to a spec; any change to `AI/contracts/` or a field the response does not carry; any threshold; a policy decision (what a state means, what a judge may see); the layout direction; or anything the brief and the code do not cover, such as how `backend/` relates to `AI/api/`.

## Before every commit

```bash
cd AI
python -m unittest discover -p "test_*.py"
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```
