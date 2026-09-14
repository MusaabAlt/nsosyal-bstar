"""m2_deobf - parallel de-obfuscation channel. STUB: contract only, no detection logic yet.

Catches (once implemented):
  * LEET, SPACED, PUNCT_SPLIT, REPEAT, CHAR_DROP, WORD_MERGE, ABBREV, DEASCII, VOWEL_DROP, SUFFIX_ON_MASKED, DIALECT, EMOJI_SUB, PHONETIC.

Deliberately does NOT:
  * ZERO_WIDTH, HOMOGLYPH, DOTLESS_I (m0).
  * Whether the de-obfuscated text is offensive: no content scores, ever. Obfuscation is never a content category.

See spec.md for approach, named tools and forbidden shortcuts.
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

    def _load(self) -> None:
        # TODO(load): load leet table, unigram frequency list, dictionary and deasciifier pattern tables from artifacts/ (hash-checked).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): candidate generation per token -> frequency/dictionary ranking -> normalized_text + alignment + alternatives in signals; FormPattern per rewrite, spans mapped to original via ctx.signals['m0_charsafe']['offsets'].
        # TODO(forbidden): replacing text/charsafe_text, collapse-to-one repeats, unconditional deasciification, correcting toward the profanity lexicon, content scores.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
