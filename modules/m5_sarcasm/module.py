"""m5_sarcasm - degrading sarcasm (D1). STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * D1 content scores (spec.md §6 Contract) - GATED: spec.md §2 Entry gate comes first

Governing sections of spec.md: §2 Entry gate, §4 Labelling rule, §5 Approach, §6 Contract, §7 Negative control, §8 Forbidden, §10 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
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
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # degrading sarcasm is scored on the whole post, not a substring.
    emits_spans = False

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§2 Entry gate, §4 Labelling rule, §5 Approach, §6 Contract, §7 Negative control, §8 Forbidden, §10 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§2 Entry gate, §4 Labelling rule, §5 Approach, §6 Contract, §7 Negative control, §8 Forbidden, §10 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
