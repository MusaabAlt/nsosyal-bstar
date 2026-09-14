"""m1_lexicon - morpheme-boundary profanity lexicon. STUB: contract only, no detection logic yet.

Catches (once implemented):
  * Lexicon roots followed by a valid Turkish suffix chain (vowel harmony, consonant alternation, buffer letters) -> A1-A4 scores.
  * A4 via entries tagged sacred; A3 via entries tagged as group slurs; A2 only from the morphology of the matched word itself (e.g. 2nd person agreement on the profane form); otherwise A1.
  * SUBSTRING_COLLISION guard when a root occurs inside a known clean word (amca, sikke, psikoloji).
  * HOMONYM guard when a surface form has both a profane and a clean reading; DUAL_REGISTER guard for entries tagged as friendly in informal register.

Deliberately does NOT:
  * Obfuscated spellings on the raw channel: m1 reads m2's normalized channel instead of doing fuzzy matching itself.
  * Implicit abuse (C), sarcasm (D), threats or degradation without a lexicon word (B).
  * Target resolution beyond the matched word's own morphology (m6 / m3 target head).

See spec.md for approach, named tools and forbidden shortcuts.
"""
from __future__ import annotations

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput


class LexiconModule(BaseModule):
    name = ModuleName.M1_LEXICON
    version = "0.0.0"
    # Not part of the contract: tells the pipeline this module has no detection logic yet,
    # so its silence must not be read as evidence (remove when implemented).
    stub = True
    provides = frozenset({"content", "guards"})

    def _load(self) -> None:
        # TODO(load): load the versioned lexicon + suffix automaton tables from artifacts/ and verify the sha256 listed in artifacts/MANIFEST.md.
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): tokenize charsafe (raw) and normalized channels separately; parse each token as root + valid suffix chain with the morphotactic automaton; emit one ContentScore per hit tagged m1_lexicon@<channel>.
        # TODO(approach): when a root is a prefix of a known clean word, emit SUBSTRING_COLLISION guard evidence instead of a score.
        # TODO(forbidden): `root in text`, `startswith`, `\b`-only regex, str.lower(), stemming, fuzzy matching, threshold/fired.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
