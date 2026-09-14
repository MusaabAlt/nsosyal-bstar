"""Checks for the counterfactual augmentation operators (phase 03 component 1).

Every rule here was added because the review pass caught a real bad row -- these
are regression tests against augmentation defects, not coverage theatre.
"""

import random

import pytest

from src import augment, lexicon


@pytest.fixture
def lex(tmp_path):
    """A miniature frozen lexicon: two real profanities, two demonstrated
    false-match roots."""
    p = tmp_path / "lex.txt"
    p.write_text("salak\naptal\nmal\nallah\namk\norospu\n", encoding="utf-8")
    return lexicon.load_lexicon(p)


# --------------------------------------------------------------------------
# 1a -- constraint C2: never leave a non-offensive residual labelled OFF
# --------------------------------------------------------------------------


def test_suspect_root_only_row_is_not_treated_as_profanity(lex):
    """`malsef` (a typo for maalesef) matched root 'mal' in review and was masked,
    corrupting an ordinary word."""
    ok, why = augment.qualifies_for_masking("sen bunu düşünmüyor malsef arkadaşım gerçekten", lex)
    assert not ok and why == "no_profanity_token"


def test_filler_only_row_is_rejected(lex):
    """Masking a filler leaves a benign row labelled OFF -- caught in review as
    `kalp dayanmaz [MASK] şu çocuğun arabasına bi bakın`."""
    ok, why = augment.qualifies_for_masking("bak motorda sorun olmasin kalp dayanmaz amk sen bak", lex)
    assert not ok and why == "profanity_is_only_a_filler"


def test_insult_head_construction_is_rejected(lex):
    """`Orospu çocukları` -> `[MASK] çocukları` keeps the frame and loses the offense."""
    ok, why = augment.qualifies_for_masking(
        "birde tam puan veriyorsunuz siz orospu çocukları hepiniz", lex)
    assert not ok and why == "profanity_is_the_insult_head"


def test_repeated_profanity_is_rejected(lex):
    ok, why = augment.qualifies_for_masking("sen salak mısın gerçekten aptal mısın nesin", lex)
    assert not ok and why == "multiple_profanity_tokens"


def test_row_without_second_person_is_rejected(lex):
    ok, why = augment.qualifies_for_masking("bu adamlar gerçekten salak olmuş yine bugün", lex)
    assert not ok and why == "no_second_person_address"


def test_a_clean_row_qualifies_and_masks_only_the_profanity(lex):
    text = "sen bunu bilmeyecek kadar aptal olamazsın gerçekten çok merak ediyorum"
    ok, why = augment.qualifies_for_masking(text, lex)
    assert ok and why == "ok"
    out = augment.mask_profanity(text, lex)
    assert augment.MASK in out
    assert "aptal" not in out
    assert "bilmeyecek" in out, "only the profanity may be replaced"


def test_masking_leaves_suspect_roots_alone(lex):
    """A religious phrase must not be mangled just because 'allah' is a lexicon entry."""
    out = augment.mask_profanity("sen allahın izniyle bunu yaparsın aptal olamazsın", lex)
    assert "allahın" in out and augment.MASK in out


# --------------------------------------------------------------------------
# 1b -- grammatical insertion, no positional shortcut
# --------------------------------------------------------------------------


def test_splice_never_breaks_a_clause():
    """Review caught `Neden gelecek kişilere mâni burada salak olan yok oldunuz?`
    -- insertion at an arbitrary word boundary. Only clause boundaries are legal."""
    text = "Neden gelecek kişilere mâni oldunuz? Ben başkan olsam yapardım."
    rng = random.Random(0)
    for _ in range(50):
        out = augment._splice(text, "kimse salak değil", rng)
        assert "mâni kimse salak değil oldunuz" not in out.lower()
        # the fragment must sit at the start, at the end, or after punctuation
        idx = out.lower().index("kimse salak değil")
        assert idx == 0 or out[:idx].rstrip()[-1] in ".!?,;:" or out.rstrip().endswith("kimse salak değil")


def test_splice_uses_more_than_one_position():
    """All-append would teach `profanity at the end = NOT`, a new shortcut."""
    rng = random.Random(1)
    text = "Bir cümle. İkinci cümle."
    placements = {augment._splice(text, "amk", rng).index("mk") for _ in range(40)}
    assert len(placements) > 1


def test_1b_sources_are_short_enough_to_survive_truncation():
    long_row = {"id": "1", "text": " ".join(["kelime"] * 80), "label": "NOT"}
    short_row = {"id": "2", "text": "kısa bir cümle bu", "label": "NOT"}
    out, pool = augment.build_1b([long_row, short_row], n=5, seed=42)
    assert pool == 1, "the 80-word row must be excluded as a source"
    assert all(o["source_id"] == "2" for o in out)


def test_1b_labels_stay_NOT_and_patterns_are_tagged():
    rows = [{"id": str(i), "text": "kısa bir cümle bu", "label": "NOT"} for i in range(20)]
    out, _ = augment.build_1b(rows, n=14, seed=42)
    assert all(o["label"] == "NOT" for o in out)
    assert {o["op"].split("_", 1)[1] for o in out} == {n for n, _ in augment.INSERTION_PATTERNS}
