**Assistant: before anything else, read `AI/CLAUDE.md`, `AI/modules/README.md` and `AI/modules/m2_deobf/spec.md`. This file is NOT the spec: the spec in the repo is the single source of truth, and if this file and the spec ever disagree, the spec wins.**

## Role

You own one module and do it thoroughly: `m2_deobf`, the parallel de-obfuscation channel.

It is a full job on its own. It is the highest value-to-effort module in the project and the strongest live-demo moment: a judge types an obfuscated insult and the system catches it. Its headline number has never been published for Turkish: how far recall falls under each obfuscation pattern, and how much the parallel channel recovers.

## Not yours

- `AI/contracts/` is frozen and owned by Musaab. You never edit it.
- `m0_charsafe`, `m1_lexicon` and `m4_implicit` are Musaab's; `m3_encoder` and `m5_sarcasm` are Abdullah's. `m6_target` is Abdullah's (v1, see `docs/team/abdullah/START_HERE.md`). Nobody edits another person's module.
- Thresholds live only in `AI/decision/thresholds.yaml`, and only Musaab edits shared rows. `budgets.clean_to_dirty_flip_rate` is the budget your tier 2 is measured against; you do not set it.

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

1. The protection pass (URLs, mentions, hashtags, brands, proper nouns), then tier 1 conservative character rules (m2 spec §5).
2. Fixtures: per-pattern pairs, protection cases, ambiguity cases, traps, idempotency (spec §9). Commit the leakage rule's protocol file before any number (spec §10).
3. Tier 2 behind the over-correction budget; the real-obfuscation slice and the human spot-check; then the headline sentence in spec §8.

**Done for your first deliverable** means tier 1 and the protection pass work, and: `ctx.text` is provably unmodified (dedicated test); every transformation emits a `FormPattern` whose `text[start:end]` equals its `evidence`; `f(f(x)) == f(x)`; zero clean-to-dirty flips on the trap list; and `python -m modules.m2_deobf.eval` reports capture rate per tier-1 pattern with confidence intervals, plus damage rate on clean text.

## Testing in isolation

Nobody waits for anybody, and you do not wait for m3. Capture rate and damage rate need no model at all: the harness compares your `normalized_text` and patterns with the fixture. Where you need a detector's reading on both channels, use fixed fake scores, never a real model.

m2 reads `ctx.charsafe_text`, which comes from m0. Do not import `modules.m0_charsafe`: rule 2 forbids it and `tests/test_architecture.py` fails the build. Fake the upstream output with fixed values in your own `test_unit.py`:

```python
import unittest
from types import MappingProxyType
from contracts.module_api import Context
from modules.m2_deobf.module import DeobfModule

def fake_m0(text: str, charsafe_text: str, signals: dict | None = None) -> Context:
    """Stands in for m0 with fixed values. No other module is imported.
    Signals from another module go into ctx.signals the same way, keyed by module name."""
    return Context(text=text, charsafe_text=charsafe_text, signals=MappingProxyType(signals or {}))

class SpanTest(unittest.TestCase):
    def test_every_pattern_points_at_its_evidence(self) -> None:
        text = "Seni b1tireceğim"
        ctx = fake_m0(text, text)
        out = DeobfModule().process(ctx)
        self.assertEqual(ctx.text, text)
        for p in out.form.patterns:
            self.assertEqual(text[p.span[0]:p.span[1]], p.evidence)
```

Use `assertEqual` on fixed values. Rule 4's scan rejects numeric literals in comparisons and ordering asserts inside `test_unit.py`. For the eval, put the fixed upstream text under `context.charsafe_text` in `fixtures/cases.jsonl` (spec §9).

## When to stop and ask Musaab

Stop for: any change to the spec; any change to `AI/contracts/`; a threshold or budget; a policy decision; or anything the spec does not cover, including where the recall-recovery measurement lives. It needs a scorer on both channels plus the decision layer, and that code sits outside `AI/modules/m2_deobf/`.

## Before every commit

```bash
cd AI
python -m unittest discover -p "test_*.py"
python -m modules.m2_deobf.eval
BASE_REF=$(git merge-base HEAD master) bash scripts/check.sh
```
