"""m4_implicit - implicit abuse (C1-C5). STUB: contract only, no detection logic yet.

Catches (once implemented):
  * C1 stereotype, C2 inferiority attribution, C3 coded language, C4 incitement, C5 defamation.

Deliberately does NOT:
  * Explicit profanity or overt threats (m1, m3).
  * Mere mention of a group, or counter-speech about a stereotype (guards suppress; the model must not learn identity terms as signal).
  * Degrading sarcasm (m5).

See spec.md for approach, named tools and forbidden shortcuts.
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

    def _load(self) -> None:
        # TODO(load): load head weights and per-class calibrators from artifacts/ (hash-checked).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): read ctx.signals['m3_encoder']['embedding'][channel]; if absent, add a note and return nothing; else head -> calibrator -> C1-C5 ContentScore per channel.
        # TODO(forbidden): identity keyword lists, calibration on test, writing thresholds, importing m3, silent clean on missing signals.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
