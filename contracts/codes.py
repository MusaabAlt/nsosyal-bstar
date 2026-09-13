"""Code books for every axis of the moderation contract.

These enums are the vocabulary shared by modules, the decision layer, the
evaluation harness and the UI. Values are stable strings because they are
written to gold files, eval results and API responses.

Axis 1 (content) has exactly one gold label per item. Axis 2 (form) is
multi-valued and sits on top of any content code: obfuscation is NEVER a
content category. Guards are negative controls that suppress a positive
decision; they are not labels.
"""
from __future__ import annotations

from enum import Enum


class ContentCode(str, Enum):
    """Axis 1 - what is being said."""

    # A: lexical profanity
    A1 = "A1"  # untargeted profanity
    A2 = "A2"  # profanity aimed at an individual
    A3 = "A3"  # profanity aimed at a group
    A4 = "A4"  # profanity against the sacred
    # B: non-lexical abuse (no swear word required)
    B1 = "B1"  # degradation
    B2 = "B2"  # threat
    B3 = "B3"  # curse / exclusion ("allah belani versin", "gitsinler")
    B4 = "B4"  # doxing
    B5 = "B5"  # sexual aggression
    # C: implicit
    C1 = "C1"  # stereotype
    C2 = "C2"  # inferiority attribution
    C3 = "C3"  # coded language
    C4 = "C4"  # incitement
    C5 = "C5"  # defamation
    # D: degrading sarcasm
    D1 = "D1"
    CLEAN = "CLEAN"


class FormCode(str, Enum):
    """Axis 2 - how it is written. Multi-valued, never a content category."""

    LEET = "LEET"
    SPACED = "SPACED"
    PUNCT_SPLIT = "PUNCT_SPLIT"
    REPEAT = "REPEAT"
    CHAR_DROP = "CHAR_DROP"
    WORD_MERGE = "WORD_MERGE"
    ABBREV = "ABBREV"
    DEASCII = "DEASCII"
    DOTLESS_I = "DOTLESS_I"
    VOWEL_DROP = "VOWEL_DROP"
    SUFFIX_ON_MASKED = "SUFFIX_ON_MASKED"
    DIALECT = "DIALECT"
    HOMOGLYPH = "HOMOGLYPH"
    ZERO_WIDTH = "ZERO_WIDTH"
    EMOJI_SUB = "EMOJI_SUB"
    PHONETIC = "PHONETIC"


class GuardCode(str, Enum):
    """Negative controls. An active guard SUPPRESSES a positive decision."""

    SUBSTRING_COLLISION = "SUBSTRING_COLLISION"
    NEGATION = "NEGATION"
    QUOTE_COUNTERSPEECH = "QUOTE_COUNTERSPEECH"
    METADISCUSSION = "METADISCUSSION"
    SELF_DIRECTED = "SELF_DIRECTED"
    FRIENDLY_BANTER = "FRIENDLY_BANTER"
    DUAL_REGISTER = "DUAL_REGISTER"
    HOMONYM = "HOMONYM"
    NON_HUMAN_TARGET = "NON_HUMAN_TARGET"


class TargetType(str, Enum):
    """Axis 3 - who is being hit."""

    INDIVIDUAL = "individual"
    GROUP = "group"
    NON_HUMAN = "non_human"
    NONE = "none"


class Level(str, Enum):
    """Axis 4 - unit of analysis. Repetition lives at thread level only."""

    POST = "post"
    THREAD = "thread"


class Action(str, Enum):
    BLOCK = "block"
    ESCALATE = "escalate"
    REVIEW = "review"
    NUDGE = "nudge"
    CLEAN = "clean"


# Most severe first. When several actions apply, the earliest one wins.
ACTION_PRECEDENCE: tuple[Action, ...] = (
    Action.BLOCK,
    Action.ESCALATE,
    Action.REVIEW,
    Action.NUDGE,
    Action.CLEAN,
)


class ModuleName(str, Enum):
    M0_CHARSAFE = "m0_charsafe"
    M1_LEXICON = "m1_lexicon"
    M2_DEOBF = "m2_deobf"
    M3_ENCODER = "m3_encoder"
    M4_IMPLICIT = "m4_implicit"
    M5_SARCASM = "m5_sarcasm"
    M6_TARGET = "m6_target"


class Family(str, Enum):
    A = "A"
    B = "B"
    C = "C"
    D = "D"
    CLEAN = "CLEAN"


FAMILY: dict[ContentCode, Family] = {
    code: (Family.CLEAN if code is ContentCode.CLEAN else Family(code.value[0]))
    for code in ContentCode
}


def codes_in_family(family: Family) -> list[ContentCode]:
    return [code for code, fam in FAMILY.items() if fam is family]


# Turkish labels for the UI. Every enum member must have an entry
# (enforced by tests/test_contracts.py).
TR_LABELS: dict[Enum, str] = {
    ContentCode.A1: "Hedefsiz küfür",
    ContentCode.A2: "Bireye yönelik küfür",
    ContentCode.A3: "Gruba yönelik küfür",
    ContentCode.A4: "Kutsal değerlere yönelik küfür",
    ContentCode.B1: "Aşağılama",
    ContentCode.B2: "Tehdit",
    ContentCode.B3: "Lanetleme / dışlama",
    ContentCode.B4: "Kişisel bilgi ifşası (doxing)",
    ContentCode.B5: "Cinsel saldırganlık",
    ContentCode.C1: "Kalıp yargı",
    ContentCode.C2: "Aşağılık atfetme",
    ContentCode.C3: "Kodlu dil",
    ContentCode.C4: "Kışkırtma",
    ContentCode.C5: "Karalama / iftira",
    ContentCode.D1: "Aşağılayıcı alay",
    ContentCode.CLEAN: "Temiz",
    Family.A: "Açık küfür",
    Family.B: "Sözcük dışı saldırganlık",
    Family.C: "Örtük saldırganlık",
    Family.D: "Aşağılayıcı ironi",
    Family.CLEAN: "Temiz",
    FormCode.LEET: "Rakam/sembol ikamesi",
    FormCode.SPACED: "Harf arası boşluk",
    FormCode.PUNCT_SPLIT: "Noktalama ile bölme",
    FormCode.REPEAT: "Harf tekrarı",
    FormCode.CHAR_DROP: "Harf düşürme",
    FormCode.WORD_MERGE: "Sözcük birleştirme",
    FormCode.ABBREV: "Kısaltma",
    FormCode.DEASCII: "Türkçe karaktersiz yazım",
    FormCode.DOTLESS_I: "Noktalı/noktasız i oyunu",
    FormCode.VOWEL_DROP: "Ünlü düşürme",
    FormCode.SUFFIX_ON_MASKED: "Maskelenmiş köke ek",
    FormCode.DIALECT: "Ağız / yöresel yazım",
    FormCode.HOMOGLYPH: "Benzer görünümlü karakter",
    FormCode.ZERO_WIDTH: "Görünmez karakter",
    FormCode.EMOJI_SUB: "Emoji ikamesi",
    FormCode.PHONETIC: "Sesletime dayalı yazım",
    GuardCode.SUBSTRING_COLLISION: "Alt dizi çakışması",
    GuardCode.NEGATION: "Olumsuzlama",
    GuardCode.QUOTE_COUNTERSPEECH: "Alıntı / karşı söylem",
    GuardCode.METADISCUSSION: "Dil üzerine tartışma",
    GuardCode.SELF_DIRECTED: "Kendine yönelik",
    GuardCode.FRIENDLY_BANTER: "Dostça takılma",
    GuardCode.DUAL_REGISTER: "Çift anlamlı kullanım",
    GuardCode.HOMONYM: "Eş sesli sözcük",
    GuardCode.NON_HUMAN_TARGET: "İnsan dışı hedef",
    TargetType.INDIVIDUAL: "Birey",
    TargetType.GROUP: "Grup",
    TargetType.NON_HUMAN: "İnsan dışı",
    TargetType.NONE: "Hedef yok",
    Action.BLOCK: "Engelle",
    Action.ESCALATE: "Üst incelemeye ilet",
    Action.REVIEW: "İncelemeye al",
    Action.NUDGE: "Uyar",
    Action.CLEAN: "Temiz",
}


def tr_label(code: Enum) -> str:
    return TR_LABELS.get(code, str(getattr(code, "value", code)))
