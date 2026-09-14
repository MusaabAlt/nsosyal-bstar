"""m1_lexicon - lexicon signal. STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * family-A content scores (A1 carrier, ADR-005) and A4, on both channels (spec.md §3 Contract)
  * signals "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm" (spec.md §3, §8)
  * SUBSTRING_COLLISION, HOMONYM and NON_HUMAN_TARGET guards with spans (spec.md §3, §8)

Governing sections of spec.md: §3 Contract, §4 Approach, §5 Forbidden, §7 Required fixtures, §8 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class LexiconModule(BaseModule):
    name = ModuleName.M1_LEXICON
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"content", "guards"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # spec.md §3: every match and every guard carries the span of the triggering substring.
    emits_spans = True

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§3 Contract, §4 Approach, §5 Forbidden, §7 Required fixtures, §8 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§3 Contract, §4 Approach, §5 Forbidden, §7 Required fixtures, §8 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
