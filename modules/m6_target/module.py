"""m6_target - target resolution and doxing patterns. STUB: contract only, no detection logic yet.

Catches (once implemented):
  * Individual target: 2nd person agreement (-sın/-sin/-sun/-sün, -sınız), sen/siz/sana/seni, vocatives, @mentions.
  * Group target: group noun gazetteer (nationality, religion, ethnicity, party, profession) with plural/collective forms.
  * SELF_DIRECTED: 1st person copula on the insult ("ne salağım").
  * NON_HUMAN_TARGET: object is a non-human gazetteer noun (film, maç, hava, trafik, bilgisayar).
  * B4 doxing: TC kimlik no (checksum-validated), +90 5xx mobile numbers, TR IBAN (mod-97), address markers (Mah., Cad., Sok., No:), plates.

Deliberately does NOT:
  * Whether the post is abusive at all.
  * Coreference across a thread.
  * Named-entity recognition with a model.

See spec.md for approach, named tools and forbidden shortcuts.
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
    provides = frozenset({"target", "content", "guards"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # spec.md: every guard and every B4 score carries the span of the triggering substring.
    emits_spans = True

    def _load(self) -> None:
        # TODO(load): load group / non-human gazetteers from artifacts/ (hash-checked).
        return None

    def _run(self, ctx: Context) -> ModuleOutput:
        # TODO(approach): suffix/pronoun/vocative rules -> TargetResult; gazetteers -> group / NON_HUMAN_TARGET; 1st person copula -> SELF_DIRECTED; validated identifier patterns -> B4 score with masked evidence.
        # TODO(forbidden): unchecked 11-digit TC matches, raw PII in output, 'sen' as proof of target.
        # The stub says so explicitly instead of returning a silent empty result.
        return ModuleOutput(notes=["stub: detection not implemented"])
