"""m3_encoder - shared BERTurk encoder with three heads. STUB: contract only, no detection logic yet.

Catches (once implemented):
  * Content head: A1-A4 and B1-B5 multi-label scores, including abuse without lexicon words.
  * Target head: individual / group / non_human / none.
  * Guard head: NEGATION, QUOTE_COUNTERSPEECH, METADISCUSSION scores.

Deliberately does NOT:
  * C1-C5 (m4) and D1 (m5) - they consume this module's embeddings from signals.
  * Obfuscation description (m0/m2).
  * Thresholds on any head.

See spec.md for approach, named tools and forbidden shortcuts.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class EncoderModule(BaseModule):
    name = ModuleName.M3_ENCODER
    version = "0.0.0"
    provides = frozenset({"content", "target", "guards"})

    def _load(self) -> None:
        # TODO(load): load the quantized ONNX model + tokenizer from artifacts/ (local files only, HF_HUB_OFFLINE=1), verify sha256 against artifacts/MANIFEST.md.
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): encode raw channel (and normalized if different) once each; content/target/guard heads on the shared pooled output; tag sources @raw/@normalized; publish embeddings in signals for m4/m5.
        # TODO(forbidden): per-head encoders, hub downloads, lowercasing, in-module thresholds, silent truncation.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
