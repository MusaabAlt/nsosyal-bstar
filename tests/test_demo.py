"""Tests for the offline demo's input handling and rendering.

The model half needs an 885 MB asset bundle and is exercised by
`python demo/app.py --selftest`. Everything here runs without it, because the
failure mode that actually matters in a live demo is a hostile paste, not a
wrong prediction: empty box, a pasted novel, emoji, English, control characters.
None of those may raise.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo import app


HOSTILE = [
    "", "   ", "\n\n\t", None, 12345,
    "🔥🔥🔥😀🙃", "!!!???...", "a", "İIıi ŞĞÜÖÇ",
    "This is a perfectly ordinary English sentence.",
    "çok uzun bir metin " * 900,
    "merhaba\x00\x07\x1b dünya",
    "<script>alert(1)</script>",
    "'; DROP TABLE rows; --",
    "​​​",
]


@pytest.mark.parametrize("raw", HOSTILE)
def test_clean_input_never_raises(raw):
    text, notes = app.clean_input(raw)
    assert isinstance(text, str)
    assert isinstance(notes, list)


def test_empty_variants_are_reported_not_crashed():
    for raw in ("", "   ", "\n\t ", None):
        text, notes = app.clean_input(raw)
        assert text == ""
        assert any("empty" in n for n in notes)


def test_long_input_is_truncated_and_says_so():
    text, notes = app.clean_input("a" * 99_999)
    assert len(text) == app.MAX_CHARS
    assert any("truncated" in n for n in notes)


def test_control_characters_are_stripped():
    text, notes = app.clean_input("merhaba\x00\x07 dünya")
    assert "\x00" not in text and "\x07" not in text
    assert "merhaba" in text and "dünya" in text
    assert any("control" in n for n in notes)


def test_newlines_and_tabs_survive():
    text, _ = app.clean_input("bir\niki\tüç")
    assert "\n" in text and "\t" in text


def test_emoji_only_is_accepted_but_flagged():
    text, notes = app.clean_input("🔥🔥😀")
    assert text, "emoji-only input should still be classified"
    assert any("no alphanumeric" in n for n in notes)


def test_turkish_characters_are_preserved():
    s = "İstanbul'da ışık çok güzeldi ŞĞÜÖÇ"
    text, _ = app.clean_input(s)
    assert text == s


def test_non_string_input_is_coerced():
    text, _ = app.clean_input(42)
    assert text == "42"


def test_keyword_decision_delegates_to_the_frozen_matcher():
    """The decision must equal lexicon.hit_root on the same string -- if these
    ever disagree, the demo is showing a different filter than every reported
    number was measured with."""
    from src import lexicon

    lex = lexicon.load_lexicon()
    for s in ("bugün hava çok güzel", "İstanbul'da yağmur var",
              "merhaba dünya", "🔥", "a"):
        decision, _ = app.keyword_decision(s, lex)
        assert decision == ("OFF" if lexicon.hit_root(s, lex) else "NOT"), s


def test_render_result_escapes_html():
    res = {"ok": True, "text": "<b>x</b>", "notes": [], "n_chars": 8, "n_tokens": 5,
           "systems": {
               "keyword": {"decision": "NOT", "confidence": None,
                           "detail": "<script>alert(1)</script>"},
               "raw": {"decision": "OFF", "confidence": 0.9, "detail": "P(OFF) = 0.9"},
               "1a1b_d": {"decision": "OFF", "confidence": 0.8, "detail": "P(OFF) = 0.8"}},
           "selective": {"confidence": 0.9, "threshold": 0.6632,
                         "route": "AUTO-RESOLVE", "decision": "OFF", "margin": 0.2368}}
    out = app.render_result(res)
    assert "<script>" not in out
    assert "&lt;script&gt;" in out


def test_render_result_handles_the_rejected_case():
    out = app.render_result({"ok": False, "notes": ["empty input"], "text": ""})
    assert "empty input" in out


def test_examples_file_is_valid_and_covers_both_directions():
    path = Path(__file__).resolve().parents[1] / "demo" / "examples.json"
    ex = json.loads(path.read_text(encoding="utf-8"))
    assert len(ex) >= 8
    fams = {e["family"] for e in ex}
    assert "implicit offense, no profanity token" in fams
    assert "profanity token present, no offensive act" in fams
    for e in ex:
        for k in ("id", "text", "gold", "slice", "family", "phase02_tag", "note"):
            assert k in e, f"example {e.get('id')} missing {k}"
        assert e["gold"] in ("OFF", "NOT")
        assert e["text"].strip()


def test_examples_are_consistent_with_their_slice_tag():
    """An example labelled lexicon_hit must actually hit the frozen lexicon."""
    from src import lexicon

    lex = lexicon.load_lexicon()
    path = Path(__file__).resolve().parents[1] / "demo" / "examples.json"
    for e in json.loads(path.read_text(encoding="utf-8")):
        hit = lexicon.hit_root(e["text"], lex)
        assert hit == (e["slice"] == "lexicon_hit"), \
            f"example {e['id']} is tagged {e['slice']} but hit_root says {hit}"
