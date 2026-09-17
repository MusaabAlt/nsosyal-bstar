"""m6_target - target resolution and doxing patterns (spec.md; rules declared in
protocols/m6_target_guideline.md; gazetteers in gazetteers/ with sha256 rows in artifacts/MANIFEST.md).

Catches:
  * target type on Axis 3, with the evidence span, published as `out.target` and as
    signals["target_type"] / ["target_confidence"] for m1 (ADR-005):
      individual  an @mention, a second-person token from the project's frozen deictic set
                  (diagnosis/data/deixis/address_tokens.json, exact token match after Turkish
                  lowercasing, never a prefix), a vocative particle, or a second-person copula /
                  verb ending on a word of four or more letters
      group       a stem of gazetteers/groups_tr.txt with Turkish plural / possessive / case suffixes
      non_human   a stem of gazetteers/non_human_tr.txt with the same suffix awareness
      none        nothing above
    precedence individual > group > non_human (guideline §1)
  * B4 doxing, one ContentScore per validated pattern with the exact span (ADR-001):
    Turkish mobile and landline numbers, national ID numbers (both checksum digits), IBAN
    (TR, mod-97), licence plates with a valid province code, addresses with a personal cue and no
    public-place cue, e-mail addresses, social-profile links (guideline §3)

Deliberately does NOT:
  * decide the three documented ambiguities (siz, institution vs members, religion vs followers)
    or the sports-supporter question: v1 behaviour is declared in the guideline and marked
    PENDING OWNER DECISION (OPEN_QUESTIONS Q28)
  * identify, verify, enrich or store anyone: no lookup of any kind (spec §2, privacy boundary)
  * resolve a non-human stem as individual or group (spec §7)
  * use a person-name gazetteer or a transformer NER (ADR-007; no licensed name list in the repo)
  * read charsafe or normalized text: mentions, casing and formatting matter (spec §6)
  * set threshold or fired; judge offensiveness (target is resolved regardless, spec §2)
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from contracts.codes import ContentCode, ModuleName, TargetType
from contracts.module_api import BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore, Span, TargetResult

SOURCE = ModuleName.M6_TARGET.value
DATA = Path(__file__).resolve().parent / "gazetteers"

# Frozen second-person address set (diagnosis/data/deixis/address_tokens.json): primary seven
# plus the pre-registered extended forms. Exact token match; `sen` as a prefix would take
# `sene`, `senaryo`, `senato`, and `siz` would take `sizofren` (that file's matching rule).
SECOND_PERSON = frozenset("""sen siz sizin senin sizi sana size seni sende senden seninle sence sizde sizden
sizinle sizce sizler sizleri sizlere sizlerin""".split())
VOCATIVES = frozenset("lan ulan be oğlum kızım moruk kardeşim abi abla hacı".split())
# Second-person copula / verb endings, on words of >= MIN_COPULA_LETTERS letters (guideline §1 d).
COPULA_RE = re.compile(r"^[^\W\d_]{4,}(sın|sin|sun|sün|sınız|siniz|sunuz|sünüz|yorsun|yorsunuz|mısın|misin|musun|müsün)$",
                       re.UNICODE)
# Plural / possessive / case suffixes accepted after a gazetteer stem (guideline §1).
SUFFIX = (r"(?:lar|ler|ı|i|u|ü|a|e|ya|ye|yı|yi|yu|yü|da|de|ta|te|dan|den|tan|ten|ın|in|un|ün|nın|nin|nun|nün|"
          r"la|le|yla|yle|sı|si|su|sü|nda|nde|ndan|nden|ki|m|n|mız|miz|muz|müz|nız|niz|nuz|nüz)")
WORD_RE = re.compile(r"[^\W_]+(?:['’][^\W_]+)?", re.UNICODE)

CONF_MENTION = 0.95
CONF_SECOND_PERSON = 0.90
CONF_VOCATIVE = 0.75
CONF_COPULA = 0.60
CONF_GROUP_PLURAL = 0.85
CONF_GROUP_BARE = 0.70
CONF_NON_HUMAN = 0.80

# -- doxing patterns (guideline §3) ---------------------------------------------------------
MOBILE_RE = re.compile(r"(?<!\d)(?:\+90|0090|0)?[\s.\-]?\(?5\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}(?!\d)")
LANDLINE_RE = re.compile(r"(?<!\d)(?:\+90|0090|0)[\s.\-]?\(?[234]\d{2}\)?[\s.\-]?\d{3}[\s.\-]?\d{2}[\s.\-]?\d{2}(?!\d)")
TCKN_RE = re.compile(r"(?<!\d)[1-9]\d{10}(?!\d)")
IBAN_RE = re.compile(r"\bTR\d{2}(?:[\s]?\d{4}){5}[\s]?\d{2}\b", re.IGNORECASE)
PLATE_RE = re.compile(r"\b(0[1-9]|[1-7]\d|8[01])\s?[A-ZÇĞİÖŞÜ]{1,3}\s?\d{2,4}\b")
EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
PROFILE_RE = re.compile(r"https?://(?:www\.)?(instagram\.com|x\.com|twitter\.com|facebook\.com|tiktok\.com|t\.me)/@?[\w.\-]{2,}",
                        re.IGNORECASE)
ADDRESS_MARKERS = ("mah.", "mahallesi", "mahalle", "sok.", "sokak", "sokağı", "cad.", "caddesi", "cadde", "bulvarı",
                   "bulv.", "no:", "no.", "no ", "daire", "kat ", "kat:", "apt.", "apartmanı", "blok", "sitesi")
PERSONAL_CUES = ("evi", "evinin", "evine", "evinde", "adresi", "adresini", "oturuyor", "yaşıyor", "kalıyor", "ikamet")
PUBLIC_CUES = ("mağaza", "dükkan", "dükkân", "şube", "ofis", "etkinlik", "konser", "açılış", "restoran", "kafe",
               "okul", "hastane", "belediye", "müze", "stadyum")
CONF_MOBILE, CONF_LANDLINE, CONF_TCKN, CONF_IBAN, CONF_PLATE, CONF_ADDRESS, CONF_EMAIL, CONF_PROFILE = \
    0.95, 0.85, 0.97, 0.97, 0.70, 0.80, 0.60, 0.60


def tr_lower(text: str) -> str:
    """Turkish lowercase that keeps every index in place (one character in, one out)."""
    return "".join("ı" if c == "I" else "i" if c == "İ" else (c.lower() if len(c.lower()) == 1 else c) for c in text)


_HARMONY = {"a": "aı", "ı": "aı", "e": "ei", "i": "ei", "o": "au", "u": "au", "ö": "eü", "ü": "eü", "â": "aı", "î": "ei", "û": "au"}
_VOWELS = set(_HARMONY)


def _harmonic(stem: str, tail: str) -> bool:
    """A gazetteer stem plus a suffix tail is accepted when (a) Turkish vowel harmony holds - the
    tail's vowels belong to the class of the stem's last vowel, which keeps "türkiye" from matching
    "türk" + "iye" - and (b) the tail is not a `-ki` form ("belediyedekiler", those AT the
    municipality): that is the members reading of an institution, which v1 does not resolve
    (guideline §2, pending owner decision)."""
    if "ki" in tail:
        return False
    last = next((c for c in reversed(stem) if c in _VOWELS), None)
    if last is None or not tail:
        return True
    allowed = _HARMONY[last]
    return all(c in allowed for c in tail if c in _VOWELS)


def tckn_valid(digits: str) -> bool:
    """Turkish national ID checksum: d10 = ((d1+d3+d5+d7+d9)*7 - (d2+d4+d6+d8)) mod 10; d11 = sum(d1..d10) mod 10."""
    d = [int(c) for c in digits]
    if len(d) != 11 or d[0] == 0:
        return False
    tenth = ((d[0] + d[2] + d[4] + d[6] + d[8]) * 7 - (d[1] + d[3] + d[5] + d[7])) % 10
    eleventh = sum(d[:10]) % 10
    return d[9] == tenth and d[10] == eleventh


def iban_valid(iban: str) -> bool:
    """ISO 7064 mod-97 over the rearranged string; TR IBANs are 26 characters."""
    s = re.sub(r"\s", "", iban).upper()
    if len(s) != 26 or not s.startswith("TR"):
        return False
    moved = s[4:] + s[:4]
    number = "".join(str(ord(c) - 55) if c.isalpha() else c for c in moved)
    remainder = int(number) % 97
    return remainder == 1


def _load_stems(name: str) -> list[str]:
    stems = []
    for line in (DATA / name).read_text(encoding="utf-8").splitlines():
        line = line.split("#", 1)[0].strip()
        if line:
            stems.append(tr_lower(line))
    return sorted(set(stems), key=len, reverse=True)


@dataclass(frozen=True)
class Candidate:
    type: TargetType
    confidence: float
    span: Span
    evidence: str
    how: str


class TargetModule(BaseModule):
    name = ModuleName.M6_TARGET
    version = "0.1.0"
    provides = frozenset({"target", "content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # B4 scores carry the span of the identifying substring; the target result carries its evidence span.
    emits_spans = True

    def _load(self) -> None:
        self._groups = _load_stems("groups_tr.txt")
        self._non_human = _load_stems("non_human_tr.txt")
        self._group_re = re.compile(r"^(" + "|".join(re.escape(s) for s in self._groups) + r")" + SUFFIX + r"*$")
        self._non_human_re = re.compile(r"^(" + "|".join(re.escape(s) for s in self._non_human) + r")" + SUFFIX + r"*$")

    def _run(self, ctx: Context) -> ModuleOutput:
        text = ctx.text
        lowered = tr_lower(text)
        candidates = self._target_candidates(text, lowered)
        target, signals = None, {"target_type": TargetType.NONE.value, "target_confidence": 0.0, "target_evidence": None}
        if candidates:
            best = candidates[0]
            target = TargetResult(type=best.type, confidence=best.confidence, evidence=best.evidence, span=best.span,
                                  source=SOURCE)
            signals = {"target_type": best.type.value, "target_confidence": best.confidence,
                       "target_evidence": {"span": list(best.span), "how": best.how}}
        signals["target_candidates"] = [{"type": c.type.value, "confidence": c.confidence, "span": list(c.span), "how": c.how}
                                        for c in candidates[:8]]
        content = self._doxing(text, lowered)
        return ModuleOutput(target=target, content=content, signals=signals)

    # -- target resolution ---------------------------------------------------------------------
    def _target_candidates(self, text: str, lowered: str) -> list[Candidate]:
        found: list[Candidate] = []
        for m in re.finditer(r"(?<!\w)@\w{2,}", text):
            found.append(Candidate(TargetType.INDIVIDUAL, CONF_MENTION, m.span(), m.group(), "mention"))
        for m in WORD_RE.finditer(lowered):
            word = m.group()
            base = word.split("'")[0].split("’")[0]
            span = (m.start(), m.start() + len(base))
            surface = text[span[0]:span[1]]
            if base in SECOND_PERSON:
                found.append(Candidate(TargetType.INDIVIDUAL, CONF_SECOND_PERSON, span, surface, "second person"))
            elif base in VOCATIVES:
                found.append(Candidate(TargetType.INDIVIDUAL, CONF_VOCATIVE, span, surface, "vocative"))
            elif COPULA_RE.match(base) and base not in self._non_human_lookup(base):
                found.append(Candidate(TargetType.INDIVIDUAL, CONF_COPULA, span, surface, "second-person ending"))
            g = self._group_re.match(base)
            if g and _harmonic(g.group(1), base[len(g.group(1)):]):
                plural = base != g.group(1)
                found.append(Candidate(TargetType.GROUP, CONF_GROUP_PLURAL if plural else CONF_GROUP_BARE, span,
                                       surface, f"group stem '{g.group(1)}'"))
                continue
            n = self._non_human_re.match(base)
            if n and _harmonic(n.group(1), base[len(n.group(1)):]):
                found.append(Candidate(TargetType.NON_HUMAN, CONF_NON_HUMAN, span, surface, f"non-human stem '{n.group(1)}'"))
        order = {TargetType.INDIVIDUAL: 0, TargetType.GROUP: 1, TargetType.NON_HUMAN: 2}
        return sorted(found, key=lambda c: (order[c.type], -c.confidence, c.span[0]))

    def _non_human_lookup(self, base: str) -> set[str]:
        return {base} if self._non_human_re.match(base) else set()

    # -- doxing --------------------------------------------------------------------------------
    def _doxing(self, text: str, lowered: str) -> list[ContentScore]:
        scores: list[ContentScore] = []
        taken: list[Span] = []

        def add(span: Span, confidence: float) -> None:
            if any(a < span[1] and span[0] < b for a, b in taken):
                return
            taken.append(span)
            scores.append(ContentScore(code=ContentCode.B4, score=confidence, source=f"{SOURCE}@raw", span=span))

        for m in IBAN_RE.finditer(text):
            if iban_valid(m.group()):
                add(m.span(), CONF_IBAN)
        for m in TCKN_RE.finditer(text):
            if tckn_valid(m.group()):
                add(m.span(), CONF_TCKN)
        for m in MOBILE_RE.finditer(text):
            add((m.start() + (len(m.group()) - len(m.group().lstrip())), m.end()), CONF_MOBILE)
        for m in LANDLINE_RE.finditer(text):
            add((m.start() + (len(m.group()) - len(m.group().lstrip())), m.end()), CONF_LANDLINE)
        for m in PROFILE_RE.finditer(text):
            add(m.span(), CONF_PROFILE)
        for m in EMAIL_RE.finditer(text):
            add(m.span(), CONF_EMAIL)
        for m in PLATE_RE.finditer(text):
            add(m.span(), CONF_PLATE)
        address = self._address_span(text, lowered)
        if address is not None:
            add(address, CONF_ADDRESS)
        return sorted(scores, key=lambda s: s.span)

    @staticmethod
    def _address_span(text: str, lowered: str) -> Span | None:
        markers = [(m.start(), m.end()) for marker in ADDRESS_MARKERS for m in re.finditer(re.escape(marker), lowered)]
        if len(markers) < 2 or not re.search(r"\d", text):
            return None
        if any(cue in lowered for cue in PUBLIC_CUES):
            return None
        personal = any(cue in lowered for cue in PERSONAL_CUES) or any(w in SECOND_PERSON for w in re.findall(r"\w+", lowered)) \
            or re.search(r"(?<!\w)@\w{2,}", text) is not None
        if not personal:
            return None
        start = min(s for s, _ in markers)
        end = max(e for _, e in markers)
        # widen to the number that directly follows the last marker ("No: 12", "Daire 3")
        m = re.match(r"[ :.]{0,2}(\d[\d/ -]*\d|\d)", text[end:])
        if m:
            end += m.end()
        return (start, end)
