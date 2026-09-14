# tr-moderation

Turkish offensive-content moderation system. Modular: every category of
offensive speech gets its own engine, its own threshold and its own action.
Runs fully offline on CPU. No platform API, no network call at inference.

## Non-negotiable rules

1. `contracts/` is FROZEN. Never edit it without an explicit instruction.
2. A module NEVER imports another module. Only `pipeline/run.py` knows order.
3. A module NEVER mutates the original text.
4. A module NEVER applies a threshold and NEVER decides an action.
   Thresholds live only in `decision/thresholds.yaml`.
5. A module returns only its own part of the contract, as a `ModuleOutput`.
6. Standard library only in the core. Heavy deps (torch, transformers) belong
   to a single module and go in that module's own requirements file.
7. Every module must be runnable, testable and measurable ALONE.

Rule 2 covers imports between modules. Shared infrastructure - `contracts/`
and `eval.harness` - is outside its scope: any module may import contracts, and
a module's `eval.py` may import `eval.harness` and its own `module.py`, nothing
else. The exact allow-lists live as data in `tests/test_architecture.py`.

## Axes (see contracts/codes.py)

- Axis 1 Content: A1-A4 profanity, B1-B5 non-lexical abuse, C1-C5 implicit,
  D1 degrading sarcasm, CLEAN. One gold label per item.
- Axis 2 Form: obfuscation patterns. Multi-valued, sits ON TOP of any content
  code. Obfuscation is NEVER a content category.
- Axis 3 Target: individual / group / non_human / none.
- Axis 4 Level: post vs thread. Repetition lives here only.
- Guards: negative controls that SUPPRESS a positive decision.

## Modules

| id | type | purpose |
|---|---|---|
| m0_charsafe | representation | invisible chars, homoglyphs, Turkish I casing |
| m1_lexicon  | signal         | morpheme-boundary profanity match, never substring |
| m2_deobf    | representation | PARALLEL de-obfuscation channel, never replaces text |
| m3_encoder  | detection      | one BERTurk encoder, two heads (A, B), runs on both channels |
| m4_implicit | detection      | C1-C5, threshold repair + influence hardening |
| m5_sarcasm  | detection      | D1, own model (ADR-003), sequential transfer from a sarcasm corpus |
| m6_target   | signal         | target resolution + doxing patterns |

Entry points: `modules/registry.py::PIPELINE_ORDER` is the single ordered list
of modules. Each entry names the module CLASS by dotted path
(`modules.<name>.module:<ClassName>`); modules do not expose a module-level
instance. The pipeline constructs them, so a failing constructor degrades one
module instead of breaking import.

## Style

- Python 3.11+, type hints everywhere, dataclasses over dicts.
- Docstrings state what the module catches AND what it deliberately does not.
- No silent failures: a module catches its own exceptions and reports in notes.
- Comments explain WHY, especially where a rule exists to avoid a known
  failure (e.g. blind normalization lowered F1 on Turkish - hence the
  parallel channel).

## Commands

- run:    `python -m pipeline.run "metin"`
- tests:  `python -m unittest discover -p "test_*.py"`
- eval:   `python -m modules.<name>.eval`
