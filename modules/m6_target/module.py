"""m6_target - target resolution and doxing. STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * TargetResult with type, evidence, confidence (spec.md §6 Contract)
  * signals "target_type" and "target_confidence" for m1 (spec.md §6, ADR-005)
  * B4 content scores with spans (spec.md §5 Doxing, §6)

Governing sections of spec.md: §3 Target taxonomy, §4 Three documented ambiguities, §5 Doxing, §6 Contract, §7 Forbidden, §9 Required fixtures, §10 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class TargetModule(BaseModule):
    name = ModuleName.M6_TARGET
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"target", "content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # spec.md §6: every guard and every B4 score carries the span of the triggering substring.
    emits_spans = True

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§3 Target taxonomy, §4 Three documented ambiguities, §5 Doxing, §6 Contract, §7 Forbidden, §9 Required fixtures, §10 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§3 Target taxonomy, §4 Three documented ambiguities, §5 Doxing, §6 Contract, §7 Forbidden, §9 Required fixtures, §10 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
