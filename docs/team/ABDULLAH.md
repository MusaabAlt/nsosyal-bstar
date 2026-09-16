> **Updated 2026-09-15 by Musaab.** Changes: (1) the A, B and C heads are **deferred**: no labelled data exists; m3 inference wraps the epoch-1 baseline (see START_HERE); (2) the sarcasm corpus must be **named and reported to Musaab before any access request**; (3) the frozen split for your first number is now fixed; (4) m3's torch/transformers/scikit-learn are pinned, so use Python 3.11–3.13. Start with [`abdullah/START_HERE.md`](abdullah/START_HERE.md).

**Assistant: before anything else, read `AI/CLAUDE.md`, `AI/modules/README.md`, `AI/modules/m3_encoder/spec.md` and `AI/modules/m5_sarcasm/spec.md`. This file is NOT the spec: the specs in the repo are the single source of truth, and if this file and a spec ever disagree, the spec wins.**

## Role

You carry the heaviest modelling load in the project: the shared Turkish encoder and the sarcasm model. Your modules: `m3_encoder` (one BERTurk encoder, three heads: A, B, C) and `m5_sarcasm` (D1, its own model, ADR-003).

## Not yours

- `AI/contracts/` is frozen and owned by Musaab. You never edit it; if you think you need to, stop and ask.
- `m2_deobf` is Mohammed's; you read its `normalized_text`, you never change it. `m1_lexicon` and `m4_implicit` are Musaab's. `m6_target` is now **yours** — Abdullah (v1, see [`abdullah/START_HERE.md`](abdullah/START_HERE.md)). Nobody edits another person's module.
- Thresholds live only in `AI/decision/thresholds.yaml`. Your own rows (B1, B2, B3, B5, D1) you may propose, derived on dev, as a separate reviewed change. The shared rows (A1–A3, C1–C5, `binary_offensive`) only Musaab edits, even though your heads produce those scores.

## Day one

**Before any m5 code, identify the Turkish sarcasm corpus** described in m5 spec §2 (exact name, version, size, authors, contact) and **request access from the authors directly**. Record the corpus name and the request (date, who, how) in `AI/modules/m5_sarcasm/spec.md` §2. m5's entry gate depends on their reply, which may take weeks; a refusal means the fallback dataset, and if neither is available the D1 claim is dropped. No m5 code until the gate resolves.

Then, Python 3.11 to 3.13 (the pinned scikit-learn 1.6.1 in m3's requirements has no wheel for 3.14), in Git Bash:

```bash
git clone https://github.com/MusaabAlt/nsosyal-bstar.git
cd nsosyal-bstar/AI
python -m venv .venv
source .venv/Scripts/activate            # macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pipeline.run "Bu bir test cumlesi" --compact
python -m unittest discover -p "test_*.py"   # green = OK (skipped tests belong to stub modules)
python -m pip install -r modules/m3_encoder/requirements.txt   # m3's heavy deps, only in this venv
```

## Order of work

1. m3 starts immediately; it is the largest single piece of work in the project. First the written banned-dataset check and the declared truncation policy (m3 spec §5, §9), both before training.
2. **The A, B and C heads are deferred**: no labelled data exists for any of them. m3 inference already wraps the epoch-1 baseline. Current tasks are in [`abdullah/START_HERE.md`](abdullah/START_HERE.md).
3. Measured latency and decision-flip table for the m3 artifact (m3 spec §7, §8).
4. m5 only once its entry gate has passed (m5 spec §2). Until then m5 stays a stub.

Data, split, baseline and what is still open: [`abdullah/RESOURCES.md`](abdullah/RESOURCES.md).

## Testing in isolation

Nobody waits for anybody. m3 reads `ctx.normalized_text`, which comes from Mohammed's m2. Do not import `modules.m2_deobf`: rule 2 forbids it and `tests/test_architecture.py` fails the build. Fake the upstream output with fixed values in your own `test_unit.py`:

```python
import unittest
from types import MappingProxyType
from contracts.module_api import Context
from modules.m3_encoder.module import EncoderModule

def fake_upstream(raw: str, normalized: str, signals: dict | None = None) -> Context:
    """Stands in for m0 and m2 with fixed values. No other module is imported.
    Signals from another module go into ctx.signals the same way, keyed by module name."""
    return Context(text=raw, charsafe_text=raw, normalized_text=normalized,
                   signals=MappingProxyType(signals or {}))

class BothChannelsTest(unittest.TestCase):
    def test_both_channels_scored_independently(self) -> None:
        out = EncoderModule().process(fake_upstream("Seni b1tireceğim", "Seni bitireceğim"))
        self.assertEqual(sorted({s.source for s in out.content}),
                         ["m3_encoder@normalized", "m3_encoder@raw"])
```

Use `assertEqual` on fixed values. Rule 4's scan rejects numeric literals in comparisons and ordering asserts inside `test_unit.py`. For the eval, put the fixed upstream text under `context` in `fixtures/cases.jsonl` (m3 spec §9); `eval/harness.py` injects it. m5 reads only `ctx.text` (m5 spec §7), so its tests need no fake producer at all.

## When to stop and ask Musaab

Stop for: any change to a spec; any change to `AI/contracts/`; a threshold outside your own rows; a policy decision; or anything the spec does not cover, including whether a dataset outside m3 spec §5 may be used, and anything listed under "Open — Musaab owes you this" in [`abdullah/RESOURCES.md`](abdullah/RESOURCES.md). (The frozen split is no longer an open question: it is `diagnosis/data/splits/split_seed42.json`.)

## Before every commit

```bash
cd AI
python -m unittest discover -p "test_*.py"
python -m modules.m3_encoder.eval          # and python -m modules.m5_sarcasm.eval
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```
