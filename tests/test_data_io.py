"""Sanity checks for the confirmed data-format traps.

These are regression tests against real bugs, not coverage theatre. Each one
corresponds to a documented trap in docs/phase_briefing.md S6. If one of these
fails, the corpus is being silently corrupted and every downstream number is
worthless -- which is exactly the failure mode they exist to catch.
"""

import pytest

from src import data_io, lexicon, obfuscation


# --------------------------------------------------------------------------
# TRAP 1: unquoted TSV, embedded newlines replaced by three spaces
# --------------------------------------------------------------------------


def test_unquoted_tsv_with_quotes_and_triple_space_newlines(tmp_path):
    """A tweet containing a bare double quote must NOT be treated as a quoting
    character, and the three-space newline substitution must survive intact.

    A default csv/pandas read would swallow the quote and merge rows here.
    """
    p = tmp_path / "train.tsv"
    p.write_text(
        "id\ttweet\tsubtask_a\n"
        '1\tbu "adam" ne diyor   ikinci satir\tOFF\n'
        "2\tnormal bir tweet\tNOT\n",
        encoding="utf-8",
    )

    header, rows = data_io.read_offenseval_tsv(p, has_labels=True)

    assert header == ["id", "tweet", "subtask_a"]
    assert len(rows) == 2, "quoting was applied -- rows got merged"
    assert rows[0]["text"] == 'bu "adam" ne diyor   ikinci satir'
    assert "   " in rows[0]["text"], "the triple-space newline marker was destroyed"
    assert rows[0]["label"] == "OFF"
    assert rows[1]["label"] == "NOT"


def test_tweet_containing_a_tab_keeps_its_label(tmp_path):
    """Extra tab-splits get merged back into the text; the label is the LAST
    field, never a fragment of the tweet."""
    p = tmp_path / "train.tsv"
    p.write_text("id\ttweet\tsubtask_a\n3\tiki\tparcali metin\tOFF\n", encoding="utf-8")

    _, rows = data_io.read_offenseval_tsv(p, has_labels=True)

    assert rows[0]["text"] == "iki\tparcali metin"
    assert rows[0]["label"] == "OFF"


def test_unlabeled_read_keeps_full_text(tmp_path):
    """The test set has no label column -- nothing may be shaved off the end."""
    p = tmp_path / "test.tsv"
    p.write_text("id\ttweet\n7\tson kelime onemli\n", encoding="utf-8")

    _, rows = data_io.read_offenseval_tsv(p, has_labels=False)

    assert rows[0] == {"id": "7", "text": "son kelime onemli"}


def test_broken_parse_raises_instead_of_being_filtered(tmp_path):
    """A label outside {OFF, NOT} means the read is broken. It must raise, not
    quietly drop rows and report a plausible-looking number."""
    p = tmp_path / "train.tsv"
    p.write_text("id\ttweet\tsubtask_a\n1\tmetin\tMAYBE\n", encoding="utf-8")

    _, rows = data_io.read_offenseval_tsv(p, has_labels=True)
    with pytest.raises(ValueError, match="parsing is broken"):
        data_io.assert_binary_labels(rows)


# --------------------------------------------------------------------------
# TRAP 2: gold label file is comma-separated despite the .tsv extension
# --------------------------------------------------------------------------


def test_gold_file_is_comma_separated_despite_tsv_extension(tmp_path):
    p = tmp_path / "offenseval-tr-labela-v1.tsv"
    p.write_text("41993,NOT\n23000,NOT\n42478,OFF\n", encoding="utf-8")

    gold = data_io.read_gold_labels(p)

    assert gold == {"41993": "NOT", "23000": "NOT", "42478": "OFF"}


def test_gold_file_has_no_header_row(tmp_path):
    """There is no header to skip -- skipping the first line would silently
    lose a real test item."""
    p = tmp_path / "gold.tsv"
    p.write_text("41993,NOT\n23000,OFF\n", encoding="utf-8")

    assert len(data_io.read_gold_labels(p)) == 2


def test_tab_separated_gold_would_fail_loudly(tmp_path):
    """If someone hands us a genuinely tab-separated gold file, the comma split
    yields one field per line and we get an empty mapping -- visible, not a
    subtly wrong accuracy score."""
    p = tmp_path / "gold.tsv"
    p.write_text("41993\tNOT\n23000\tOFF\n", encoding="utf-8")

    assert data_io.read_gold_labels(p) == {}


# --------------------------------------------------------------------------
# TRAP 3: Turkish casing
# --------------------------------------------------------------------------


def test_turkish_lowercasing_maps_dotted_and_dotless_i():
    assert lexicon.tr_lower("IĞDIR") == "ığdır"
    assert lexicon.tr_lower("İSTANBUL") == "istanbul"
    # the bug this prevents: str.lower() alone turns I into i
    assert "IPTAL".lower() != lexicon.tr_lower("IPTAL")


def test_matching_uses_turkish_casing(tmp_path):
    lex_file = tmp_path / "lex.txt"
    lex_file.write_text("# comment line\nsalak\n", encoding="utf-8")
    lex = lexicon.load_lexicon(lex_file)

    assert lex == ["salak"], "comment lines must be dropped"
    assert lexicon.hit_literal("SALAK herif", set(lex)), "uppercase must still match"
    assert not lexicon.hit_literal("salakca degil ama", set(lex)), "literal match is exact-word only"


def test_root_matching_catches_agglutinated_forms(tmp_path):
    lex_file = tmp_path / "lex.txt"
    lex_file.write_text("aptal\n", encoding="utf-8")
    lex = lexicon.load_lexicon(lex_file)

    assert not lexicon.hit_literal("aptalsın sen", set(lex)), "literal must miss inflected forms"
    assert lexicon.hit_root("aptalsın sen", lex), "root match must catch them"


def test_url_placeholder_is_dropped():
    """URL is a corpus artefact, not content."""
    assert "url" not in lexicon.tokens("@USER merhaba URL")


def test_user_placeholder_quirk_is_pinned():
    """Characterisation test, not an endorsement.

    `\\w+` strips the '@', so "@USER" tokenises to "user" and the "@user" entry
    in SKIP never fires. Verified harmless (no lexicon entry matches "user"),
    and results/day1_report.json was frozen with this behaviour. This test
    exists so that changing it becomes a deliberate re-freeze rather than an
    accidental drift in the Day 1 numbers.
    """
    assert lexicon.tokens("@USER merhaba URL") == ["user", "merhaba"]


# --------------------------------------------------------------------------
# TRAP 4: 3-way -> binary mapping must be explicit
# --------------------------------------------------------------------------


def test_three_way_label_map_is_explicit():
    assert data_io.map_3way_to_binary("hate") == "OFF"
    assert data_io.map_3way_to_binary("Offensive") == "OFF"
    assert data_io.map_3way_to_binary("none") == "NOT"


def test_unknown_three_way_label_raises_rather_than_guessing():
    with pytest.raises(ValueError, match="Unmapped 3-way label"):
        data_io.map_3way_to_binary("neutral")


# --------------------------------------------------------------------------
# Anti-circularity guards (briefing S7)
# --------------------------------------------------------------------------


def test_official_test_set_refuses_to_load_without_explicit_flag():
    with pytest.raises(PermissionError, match="touched exactly once"):
        data_io.load_coltekin_test()


def test_reusing_a_training_attack_family_for_evaluation_raises():
    with pytest.raises(ValueError, match="ANTI-CIRCULARITY VIOLATION"):
        obfuscation.assert_disjoint(train_families=["D"], eval_families=["D"])


def test_disjoint_attack_families_are_accepted():
    assert obfuscation.assert_disjoint(train_families=["D"], eval_families=["H"]) is True
