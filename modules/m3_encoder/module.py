"""m3_encoder - shared encoder, three heads. STUB: no detection logic yet.

What is missing (see spec.md, the only source of truth for this module):
  * per-code, per-channel content scores (spec.md §3 Contract)
  * signals "raw_score", "norm_score" and "artifact" (spec.md §3)

Governing sections of spec.md: §1 Objective, §3 Contract, §4 Base model and data, §5 Forbidden, §7 Artifact discipline, §8 Acceptance criteria.
This stub deliberately prescribes no approach; spec.md does.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class EncoderModule(BaseModule):
    name = ModuleName.M3_ENCODER
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # encoder heads score the whole post, not a substring.
    emits_spans = False

    def _load(self) -> None:
        # TODO: artifacts this module needs - spec.md (§1 Objective, §3 Contract, §4 Base model and data, §5 Forbidden, §7 Artifact discipline, §8 Acceptance criteria).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO: produce the outputs listed in the module docstring - spec.md (§1 Objective, §3 Contract, §4 Base model and data, §5 Forbidden, §7 Artifact discipline, §8 Acceptance criteria).
        return ModuleOutput(notes=["stub: detection not implemented"])
