**Assistant: before anything else, read `AI/CLAUDE.md`, `AI/modules/README.md`, `AI/modules/m1_lexicon/spec.md` and `AI/modules/m4_implicit/spec.md`. This file is NOT the spec: the specs in the repo are the single source of truth, and if this file and a spec ever disagree, the spec wins.**

## Role

Captain: you own the contract, the decision layer and the final review of every number the team produces. Your modules: `m1_lexicon` and `m4_implicit`, plus `m0_charsafe`, the reference implementation.

You also own `AI/contracts/`, `AI/decision/` (including every shared row in `AI/decision/thresholds.yaml`: A1–A3, C1–C5, `binary_offensive`), `m6_target` owner: Abdullah (v1, see `abdullah/START_HERE.md`).

## Not yours

- `m2_deobf` is Mohammed's. `m3_encoder` and `m5_sarcasm` are Abdullah's. `frontend/`, `backend/` and `AI/api/` are Amin's. Nobody edits another person's module, you included: you review and approve, the owner writes.
- A module owner's own category rows in `thresholds.yaml` are theirs to propose (derived on dev, separate reviewed change, `AI/CONTRIBUTING.md` step 7). You review them. Nobody else edits shared rows.
- `AI/contracts/` is frozen even for you: a change needs an ADR in `AI/protocols/` first, and the contract is re-frozen straight after.

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
```

## Order of work

1. **`m1_lexicon` first.** Its `lexicon_hit` signal defines the `lexicon_free` slice that m4's whole result rests on, and m4 stage 1 cannot be verified until that split exists.
2. `m4_implicit` stage 1: re-verify the single global `binary_offensive` threshold on the frozen dev set (m4 spec §4, §10).
3. Stage 1b against stage 1 at equal coverage, only if proposed. Then stage 2, with its precision budget committed in `AI/protocols/` **before** the first stage-2 number.

**Done for your first deliverable** means m1 meets its spec §8 Acceptance criteria and §10 Definition of done: zero positives on the full trap list, the two-tier list in place, both channels reported, a span on every score and guard, `lexicon_hit`, `lexicon_hit_raw` and `lexicon_hit_norm` present and boolean on every input, and the licence of every list recorded.

## Testing in isolation

Nobody waits for anybody. m1 reads `ctx.signals["m6_target"]`, and m6 does not exist yet. Do not import `modules.m6_target`: rule 2 forbids it and `tests/test_architecture.py` fails the build. Write a fake producer in your own `test_unit.py` that returns fixed values, and inject it into `Context.signals`:

```python
import unittest
from types import MappingProxyType
from contracts.codes import GuardCode
from contracts.module_api import Context
from modules.m1_lexicon.module import LexiconModule

FAMILY_A_FIXTURE_TEXT = "..."   # a family-A item from your fixtures/cases.jsonl

def fake_m6_target(target_type: str, target_confidence: float) -> MappingProxyType:
    """Stands in for m6_target with fixed values. modules.m6_target is never imported."""
    return MappingProxyType({"m6_target": MappingProxyType(
        {"target_type": target_type, "target_confidence": target_confidence})})

class NonHumanTargetTest(unittest.TestCase):
    def test_guard_raised_from_fake_m6_signal(self) -> None:
        ctx = Context(text=FAMILY_A_FIXTURE_TEXT, signals=fake_m6_target("non_human", 0.9))
        guards = [g for g in LexiconModule().process(ctx).guards if g.code is GuardCode.NON_HUMAN_TARGET]
        self.assertTrue(guards)
        self.assertEqual({g.score for g in guards}, {0.9})   # score = m6's target_confidence (spec §3)
```

Use `assertEqual` on fixed values. Rule 4's scan rejects numeric literals in comparisons and ordering asserts inside `test_unit.py`. For m4, the fixtures carry fixed `m3_encoder` and `m1_lexicon` signals under `context.signals` in `fixtures/cases.jsonl` (m4 spec §9); `eval/harness.py` injects them the same way.

## When to stop

You are the person the others stop for. Hold yourself to the same line: a contract change gets an ADR before the edit; a policy decision is written down (ADR or `AI/docs/HANDOVER.md`) before code; the open questions in HANDOVER §5 and in the specs stay open until you decide them in writing.

## Before every commit

```bash
cd AI
python -m unittest discover -p "test_*.py"
python -m modules.m1_lexicon.eval          # and python -m modules.m4_implicit.eval
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```
