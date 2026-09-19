"""What the AI can detect today, and which module produces it.

The Kategoriler page and the "N kategoriden M'i değerlendirildi" line show
only these, so update this list in the same change that makes a module
produce a new code (or stop producing one).

Kept here, outside the modules, on purpose: a module declares what fields it
provides, not which content codes its current implementation emits, and module
code belongs to its owner.

Checked against the code on 2026-09-19 (after m2 and m6 landed, audit/m1-m6):
  * m1_lexicon 0.2.1 ROUTES each matched root to the code whose contract meaning
    fits (protocols/m1_runtime_routing_protocol.md, M1-ROUTE-1): the 17 family-A
    roots on the A1 carrier, ordinary insults on B1, threats on B2, curses and
    exclusion on B3. Topic vocabulary is a match with no content code.
  * A2 and A3 are the SAME m1 score after the decision layer re-codes the A1
    carrier from m6's target (ADR-005, thresholds.yaml `family_a.by_target`:
    individual -> A2, group -> A3). The score, span and evidence are m1's, so
    m1_lexicon is named as their module; without m6 they would stay A1.
  * m6_target 0.1.0 emits B4 (doxing: phone, national ID, IBAN, plate, address,
    e-mail, profile link) with the exact span, and publishes the target itself
    (Axis 3) - a target is not a category, so it is not listed here.
  * m3_encoder 0.2.0 emits no content code from the frozen BINARY checkpoint; it
    publishes raw_score / norm_score, which the decision layer turns into
    signals.decision.binary_offensive. With a multi-head artifact installed
    (NSOSYAL_M3_ARTIFACT) it also emits its trained heads' codes - add them here
    in the change that installs one.
  * m0_charsafe and m2_deobf produce Axis 2 form patterns, never a content code:
    obfuscation is never a category (CLAUDE.md, Axes).
  * A4 and the HOMONYM guard are not built (m1 spec.md §4.3, §8). C1-C5 wait for
    m3's C head (m4 is not a stub but has nothing to score). m5_sarcasm is the
    one remaining stub, so D1 is not produced.
"""
from __future__ import annotations

# "binary_offensive" is not a ContentCode: it is the decision layer's
# channel-level offensive score (decision/thresholds.yaml `binary_offensive`).
BINARY_OFFENSIVE = "binary_offensive"

CAPABILITIES: tuple[dict[str, str], ...] = (
    {"code": "A1", "module": "m1_lexicon"},
    {"code": "A2", "module": "m1_lexicon"},
    {"code": "A3", "module": "m1_lexicon"},
    {"code": "B1", "module": "m1_lexicon"},
    {"code": "B2", "module": "m1_lexicon"},
    {"code": "B3", "module": "m1_lexicon"},
    {"code": "B4", "module": "m6_target"},
    {"code": BINARY_OFFENSIVE, "module": "m3_encoder"},
)
