"""m5_sarcasm - degrading sarcasm (D1). STUB: contract only, no detection logic yet.

Catches (once implemented):
  * D1 degrading sarcasm.
  * FRIENDLY_BANTER guard: ironic but non-degrading exchanges.

Deliberately does NOT:
  * Sarcasm that degrades no one: sarcasm is not D1.
  * Explicit abuse (A/B) and implicit stereotypes (C).

See spec.md for approach, named tools and forbidden shortcuts.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class SarcasmModule(BaseModule):
    name = ModuleName.M5_SARCASM
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"content", "guards"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # degrading sarcasm is scored on the whole post, not a substring.
    emits_spans = False

    def _load(self) -> None:
        # TODO(load): load stage-2 head weights from artifacts/ (hash-checked).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): read m3 embedding per channel from ctx.signals; if absent, note and return nothing; else sequential-transfer head -> D1 score + FRIENDLY_BANTER guard score.
        # TODO(forbidden): sarcasm == D1, emoji/punctuation heuristics, skipping stage 1, importing m3.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
