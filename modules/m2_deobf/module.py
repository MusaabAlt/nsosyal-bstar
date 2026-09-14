"""m2_deobf - parallel de-obfuscation channel. STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * normalized_text, a parallel channel that never replaces the raw text (spec.md §4 Contract)
  * one FormPattern with evidence and span per transformation (spec.md §3 Patterns in scope, §4)

Governing sections of spec.md: §3 Patterns in scope, §4 Contract, §5 Forbidden, §7 Leakage rule, §8 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class DeobfModule(BaseModule):
    name = ModuleName.M2_DEOBF
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"normalized_text", "form"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # emits no content scores or guards.
    emits_spans = False

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§3 Patterns in scope, §4 Contract, §5 Forbidden, §7 Leakage rule, §8 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§3 Patterns in scope, §4 Contract, §5 Forbidden, §7 Leakage rule, §8 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
