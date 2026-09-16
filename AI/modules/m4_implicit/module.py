"""m4_implicit - C1-C5 thresholds and the lexicon-free slice repair. Emits one note only.

NOT a stub (owner decision, ADR-006 amendment). C1-C5 scores come from m3's C
head; m4's deliverables are the C1-C5 and binary_offensive rows of
decision/thresholds.yaml and the slice repair (spec.md §4 What it must do,
§5 Contract). At inference it has nothing to score, so it returns no scores and
one plain note, NOTE_C_FAMILY, so a reader of the result sees that C1-C5 are not
covered. That is an answer, not a missing one: it is not a stub and does not
degrade the result (ADR-006 amendment), so the fail-closed behaviour of the
remaining stubs stays visible instead of being hidden behind this module.

Stage 1b (the lexicon-conditioned binary_offensive threshold) was measured against
stage 1 under protocols/m4_stage1b_protocol.md and not adopted; stage 1 stays.

Deliberately does NOT: score content (m3's C head does), read anything but what
m3 publishes in ctx.signals, or apply a threshold (decision/thresholds.yaml).
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput

# Plain information, not a failure: m4 is not a stub and this note degrades nothing.
NOTE_C_FAMILY = "C1–C5 not implemented yet"


class ImplicitModule(BaseModule):
    name = ModuleName.M4_IMPLICIT
    version = "0.1.0"
    # Kept as declared (owner decision): m4 emits no content scores today (ADR-006).
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # implicit abuse is scored on the whole post, not a substring.
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(notes=[NOTE_C_FAMILY])
