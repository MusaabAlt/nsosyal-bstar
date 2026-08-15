"""Reading corpora off disk, with the known format traps guarded in code.

Fulfils briefing S5 (data role separation), S6 (reading warnings) and S7.2
(the official test set is for the final number only).

Ported from the verified `day1_gate_en.py` -- the parsing behaviour here is
byte-for-byte the behaviour that produced `results/day1_report.json`. Do not
"improve" it into pandas.read_csv; see the trap notes below.

Traps this module exists to prevent
-----------------------------------
1. Çöltekin training/test TSV has NO quoting and NO escapes. Newlines inside
   the original tweets were replaced with three spaces. Default csv/pandas
   parsing silently corrupts rows. -> read line-by-line, split on \\t manually.
2. The gold label file is named `.tsv` but its content is COMMA-separated and
   has no header row.
3. Mayda/Beyhan use 3-way labels; the collapse to binary is a documented
   decision (LABEL_MAP_3TO2), not an inline judgement call in a script.
"""

import hashlib
from collections import Counter
from pathlib import Path

# --------------------------------------------------------------------------
# integrity
# --------------------------------------------------------------------------


def sha256(path):
    """Content fingerprint -- recorded in every result file so a rerun can
    prove it read the same bytes."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------
# TRAP 1: unquoted TSV, embedded newlines replaced by three spaces
# --------------------------------------------------------------------------


def read_offenseval_tsv(path, has_labels=True):
    """Read an OffensEval-TR TSV correctly.

    Returns (header, rows) where rows are dicts with keys id/text[/label].

    A tweet that itself contains a literal tab would split into more than the
    expected number of fields. Rather than dropping it, the middle fields are
    joined back together with tabs -- the label is always the LAST field, the
    id always the first.
    """
    rows = []
    with open(path, encoding="utf-8") as f:
        header = f.readline().rstrip("\n").split("\t")
        for ln, line in enumerate(f, start=2):
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            if has_labels:
                if len(parts) < 3:
                    print(f"  [warn] line {ln}: only {len(parts)} field(s) -- skipped")
                    continue
                rows.append(
                    {
                        "id": parts[0],
                        "text": "\t".join(parts[1:-1]),
                        "label": parts[-1].strip(),
                    }
                )
            else:
                if len(parts) < 2:
                    print(f"  [warn] line {ln}: only {len(parts)} field(s) -- skipped")
                    continue
                rows.append({"id": parts[0], "text": "\t".join(parts[1:])})
    return header, rows


# --------------------------------------------------------------------------
# TRAP 2: gold labels are comma-separated despite the .tsv extension
# --------------------------------------------------------------------------


def read_gold_labels(path):
    """Read `offenseval-tr-labela-v1.tsv`. Content is `id,LABEL` per line,
    no header. Returns {id: label}."""
    gold = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) >= 2:
                gold[parts[0].strip()] = parts[1].strip()
    return gold


# --------------------------------------------------------------------------
# label sanity
# --------------------------------------------------------------------------

VALID_BINARY_LABELS = {"OFF", "NOT"}

# Briefing S6: Mayda / Beyhan are 3-way. This collapse is a documented
# limitation of the cross-corpus comparison and must be cited as such in the
# report -- it is deliberately a named constant so it cannot drift between
# scripts.
LABEL_MAP_3TO2 = {
    "hate": "OFF",
    "offensive": "OFF",
    "none": "NOT",
}


def map_3way_to_binary(label, mapping=LABEL_MAP_3TO2):
    """Collapse a 3-way label to OFF/NOT. Raises on anything unmapped rather
    than guessing -- an unseen label value means the source file was not what
    we assumed, and that must fail loudly."""
    key = str(label).strip().lower()
    if key not in mapping:
        raise ValueError(
            f"Unmapped 3-way label {label!r}. Inspect the source file and extend "
            f"LABEL_MAP_3TO2 deliberately -- do not guess. Known: {sorted(mapping)}"
        )
    return mapping[key]


def assert_binary_labels(rows):
    """Fail loudly if parsing produced labels outside {OFF, NOT}.

    Unexpected label values are the signature of a broken TSV read, so this is
    a parsing check disguised as a label check. Returns the distribution.
    """
    dist = Counter(r["label"] for r in rows)
    unexpected = set(dist) - VALID_BINARY_LABELS
    if unexpected:
        raise ValueError(
            f"Unexpected labels {sorted(unexpected)} -- parsing is broken. "
            "Stop and fix before continuing; do not filter these rows away."
        )
    return dict(dist)


# --------------------------------------------------------------------------
# convenience loaders (paths come from config, never from a caller's literal)
# --------------------------------------------------------------------------


def load_coltekin_train(path=None):
    """Training corpus. Free to use for train/dev splitting and error analysis."""
    import config

    path = Path(path or config.COLTEKIN_TRAIN)
    header, rows = read_offenseval_tsv(path, has_labels=True)
    assert_binary_labels(rows)
    return rows


def load_coltekin_test(run_final_test=False, path=None, gold_path=None):
    """Official Çöltekin test set + gold labels. THE FINAL NUMBER ONLY.

    Anti-circularity guard (briefing S7.2): this is the single-use resource
    that produces the reported result. Reading it during development -- even
    "just to look" -- contaminates every number in the report, because any
    subsequent design decision is then informed by it.

    Callers must pass run_final_test=True explicitly, which in practice means
    a script exposing `--run_final_test 1` that defaults to off.
    """
    if not run_final_test:
        raise PermissionError(
            "Refusing to load the official Çöltekin test set.\n"
            "This resource is touched exactly once, at the end of the project "
            "(briefing S7.2). Pass run_final_test=True only from a script "
            "invoked with an explicit --run_final_test 1 flag, and preserve "
            "that run's output unmodified."
        )
    import config

    path = Path(path or config.COLTEKIN_TEST)
    gold_path = Path(gold_path or config.COLTEKIN_GOLD)

    _, rows = read_offenseval_tsv(path, has_labels=False)
    gold = read_gold_labels(gold_path)

    missing = [r["id"] for r in rows if r["id"] not in gold]
    if missing:
        raise ValueError(
            f"{len(missing)} test rows have no gold label (first: {missing[:5]}). "
            "Check that both files come from the same release."
        )
    for r in rows:
        r["label"] = gold[r["id"]]
    assert_binary_labels(rows)
    return rows
