"""m4_implicit - C1-C5 thresholds and the lexicon-free slice repair. Emits nothing yet.

NOT a stub (owner decision, ADR-006 amendment). C1-C5 scores come from m3's C
head; m4's deliverables are the C1-C5 and binary_offensive rows of
decision/thresholds.yaml and the slice repair (spec.md §4 What it must do,
§5 Contract). At inference it has nothing to add, so it returns an empty output.
That is an answer, not a missing one: it does not degrade the result, so the
fail-closed behaviour of the remaining stubs stays visible instead of being
hidden behind this module.

Deliberately does NOT: score content (m3's C head does), read anything but what
m3 publishes in ctx.signals, or apply a threshold (decision/thresholds.yaml).
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class ImplicitModule(BaseModule):
    name = ModuleName.M4_IMPLICIT
    version = "0.1.0"
    # Kept as declared (owner decision): m4 emits no content scores today (ADR-006).
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # implicit abuse is scored on the whole post, not a substring.
    emits_spans = False

    def _run(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput()
