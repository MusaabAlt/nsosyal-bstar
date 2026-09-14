"""Tests for the Phase 15 address flag, written before any Phase 15 count exists.

Every input is synthetic. Nothing here reads the prediction dump or the split.

The whole of what these tests defend is one word in the specification: **exact**.
`sen` matches the token `sen` and nothing else. If the flag ever slid to prefix
matching it would silently absorb `sene`, `senaryo`, `senato`, `sendika` and
`sizofren`, and the "address" cell would fill with rows carrying no address at
all. That is not hypothetical: it is exactly what `hit_root` prefix matching did
to the profanity slice -- phase 02 found 248 of 614 `lexicon_hit` rows matched
only via a suspect root (`allah`, `mal` -> `malatya`, `göt` -> `götürür`), and
that contamination is on the record as a known slice-definition defect. The same
mistake is not repeated in a slice defined here.

The second thing defended is Turkish casing. `src.lexicon.tr_lower` maps
`I` -> `ı` and `İ` -> `i` BEFORE `lower()`. So `SİZİN` lowercases to `sizin` and
flags, while `SIZIN` lowercases to `sızın` and does not -- `SIZIN` is the
uppercase of `sızın`, a different word. Python's `str.lower()` would map both to
`sizin` and manufacture a false hit. The asymmetry is the correct behaviour, not
a gap, so it is asserted in both directions.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src import lexicon
from src.phase15_deixis import TOKENS_PATH, address_flag, load_token_sets

SETS, DOC = load_token_sets()
PRIMARY = SETS["primary"]


# ==============================================================================
# the frozen file
# ==============================================================================

def test_the_primary_set_is_the_stage_4_seven():
    """Transcribed from phases/09_deeper_analysis.md Stage 4. Not extended, not
    reordered, not tuned."""
    assert DOC["primary_set"] == ["sen", "siz", "sizin", "senin", "sizi", "sana", "size"]
    assert len(PRIMARY) == 7


def test_the_sensitivity_sets_are_supersets_or_disjoint_as_declared():
    assert PRIMARY < SETS["extended"], "extended_set must contain the primary seven"
    assert len(SETS["extended"]) == 20
    assert not (PRIMARY & SETS["third_person_deictic"]), \
        "the third-person set must share no token with the second-person primary"
    assert SETS["third_person_deictic"] == {"lan", "bak", "adam", "bunlar", "onlar"}


def test_the_frozen_file_parses_and_declares_exact_matching():
    doc = json.loads(Path(TOKENS_PATH).read_text(encoding="utf-8"))
    assert "exact match" in doc["matching_rule"]
    assert "NOT hit_root" in doc["matching_rule"]
    assert "NOT prefix" in doc["matching_rule"]


# ==============================================================================
# exact match, NOT prefix -- the point of the whole file
# ==============================================================================

@pytest.mark.parametrize("text", ["sene", "senaryo", "senato", "sendika", "sizofren"])
def test_prefixes_of_an_address_token_do_not_flag(text):
    """`sen` is a prefix of the first four and `siz` of the last. Under prefix
    matching every one of these would be a false address hit."""
    assert address_flag(text, PRIMARY) is False


@pytest.mark.parametrize("text", ["sen", "siz", "sizin"])
def test_the_address_tokens_themselves_flag(text):
    assert address_flag(text, PRIMARY) is True


@pytest.mark.parametrize("token", sorted(PRIMARY))
def test_every_primary_token_flags_on_its_own(token):
    assert address_flag(token, PRIMARY) is True


@pytest.mark.parametrize("text", [
    "bugün sene başı",                    # `sene`, not `sen`
    "senaryo çok kötüydü",                # `senaryo`
    "senato toplandı",                    # `senato`
    "sendika kararı açıkladı",            # `sendika`
    "sizofren teşhisi",                   # `sizofren`
    "seninki gibi",                       # `seninki`, not `senin`
    "sizinle konuştum",                   # extended-set member, NOT primary
    "seni gördüm",                        # extended-set member, NOT primary
])
def test_near_misses_in_running_text_do_not_flag_the_primary_set(text):
    assert address_flag(text, PRIMARY) is False


@pytest.mark.parametrize("text", ["sizinle", "seni", "sizler", "sence"])
def test_those_same_near_misses_do_flag_the_extended_set(text):
    """The extended set is a pre-registered sensitivity precisely because these
    forms exist. That it catches them is what makes it a different denominator."""
    assert address_flag(text, SETS["extended"]) is True


def test_an_address_token_anywhere_in_the_text_flags():
    assert address_flag("ne yaptığını sen biliyorsun", PRIMARY) is True
    assert address_flag("bunu size söylemiştim", PRIMARY) is True


def test_a_text_with_no_address_token_does_not_flag():
    assert address_flag("bugün hava çok güzel", PRIMARY) is False
    assert address_flag("", PRIMARY) is False


# ==============================================================================
# Turkish casing, via tr_lower
# ==============================================================================

def test_turkish_casing_dotted_capital_i_flags():
    """`SEN` -> `sen`; `SİZİN` -> `sizin`. Both are address."""
    assert address_flag("SEN", PRIMARY) is True
    assert address_flag("SİZİN", PRIMARY) is True
    assert address_flag("SİZ", PRIMARY) is True
    assert address_flag("Sana", PRIMARY) is True


def test_turkish_casing_dotless_capital_i_does_not_flag():
    """`SIZIN` -> `sızın`, not `sizin`. It is the uppercase of a different word,
    so it must NOT flag. `str.lower()` would map it to `sizin` and be wrong."""
    assert lexicon.tr_lower("SIZIN") == "sızın"
    assert "SIZIN".lower() == "sizin", "the bug tr_lower exists to avoid"
    assert address_flag("SIZIN", PRIMARY) is False
    assert address_flag("SIZ", PRIMARY) is False


def test_the_flag_goes_through_the_frozen_tokeniser():
    """Not a reimplementation: whatever `lexicon.tokens` produces is what is
    matched, punctuation and Turkish casing included."""
    assert lexicon.tokens("Sen, gerçekten?") == ["sen", "gerçekten"]
    assert address_flag("Sen, gerçekten?", PRIMARY) is True
    assert address_flag("SEN!!!", PRIMARY) is True


# ==============================================================================
# the flag is a set membership test, and nothing more
# ==============================================================================

def test_an_empty_token_set_never_flags():
    assert address_flag("sen siz sizin", frozenset()) is False


def test_the_third_person_set_does_not_flag_second_person_address():
    assert address_flag("sen ne dedin", SETS["third_person_deictic"]) is False
    assert address_flag("lan ne dedin", SETS["third_person_deictic"]) is True


def test_the_flag_returns_a_bool_not_a_truthy_value():
    """Cells are counted by identity against True/False; a truthy token would
    still count but would make the counting code's `is` comparisons lie."""
    assert address_flag("sen", PRIMARY) is True
    assert address_flag("kedi", PRIMARY) is False
