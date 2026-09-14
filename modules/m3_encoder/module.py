"""m3_encoder - one BERTurk encoder, three heads. STUB: contract only, no detection logic yet.

Catches (once implemented, see spec.md):
  * head_explicit    -> A1-A4 (single-label)
  * head_nonlexical  -> B1-B5 (multi-label)
  * head_sarcasm     -> D1
  * channel-level binary offensive probability in signals raw_score / norm_score

Deliberately does NOT:
  * resolve the target (m6_target owns Axis 3)
  * fuse the raw and normalized channels (decision layer)
  * set threshold or fired

See spec.md for base model, allowed/banned datasets and forbidden shortcuts.
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
    provides = frozenset({"content", "guards"})

    def _load(self) -> None:
        # TODO(load): load the fine-tuned dbmdz/bert-base-turkish-cased artifact from artifacts/ (local files only),
        # verify its sha256 against artifacts/MANIFEST.md; the artifact carries its own thresholds file.
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): encode ctx.text and ctx.normalized_text; three heads; one ContentScore per code and
        # channel with source m3_encoder@raw / m3_encoder@normalized; signals raw_score, norm_score, artifact.
        # TODO(forbidden): setting threshold/fired, fusing channels, banned datasets, quantized/exported
        # artifacts with another artifact's thresholds.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
