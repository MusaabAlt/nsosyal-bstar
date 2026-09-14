"""m4_implicit - implicit abuse (C1-C5). STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * C1-C5 content scores (spec.md §4 Contract)

Governing sections of spec.md: §2 The measured starting point, §3 What it must do, §4 Contract, §5 Forbidden, §8 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class ImplicitModule(BaseModule):
    name = ModuleName.M4_IMPLICIT
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # implicit abuse is scored on the whole post, not a substring.
    emits_spans = False

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§2 The measured starting point, §3 What it must do, §4 Contract, §5 Forbidden, §8 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§2 The measured starting point, §3 What it must do, §4 Contract, §5 Forbidden, §8 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
