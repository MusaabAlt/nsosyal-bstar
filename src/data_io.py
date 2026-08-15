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
import random
from collections import Counter, defaultdict
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
# train / dev split  (briefing S5: 85/15 stratified, error analysis on dev only)
# --------------------------------------------------------------------------


def stratified_split(rows, dev_fraction=None, seed=None):
    """Deterministic label-stratified split of the Çöltekin training corpus.

    Returns (train_rows, dev_rows).

    Two properties matter more than the split itself:

    * **Order independence.** Rows are sorted by id inside each label bucket
      before shuffling, so the split does not depend on the order the file
      happened to be read in. A future reader change cannot silently move
      examples between train and dev.
    * **Reproducibility across steps.** BERTurk, ConvBERTurk, the defense and
      the calibration layer must all be measured on the *same* dev set, or the
      comparison matrix (briefing S8) compares systems on different data. The
      seed is fixed and `dev_fingerprint()` lets every result file prove which
      dev set it used.

    Per-class dev size is round(n_class * dev_fraction), so the OFF rate of the
    dev set matches the corpus to within one example per class.
    """
    import config

    dev_fraction = config.DEV_FRACTION if dev_fraction is None else dev_fraction
    seed = config.SEED if seed is None else seed
    if not 0.0 < dev_fraction < 1.0:
        raise ValueError(f"dev_fraction must be in (0, 1), got {dev_fraction!r}")

    buckets = defaultdict(list)
    for r in rows:
        buckets[r["label"]].append(r)

    rng = random.Random(seed)
    train_rows, dev_rows = [], []
    for label in sorted(buckets):  # sorted -> label iteration order is fixed
        bucket = sorted(buckets[label], key=lambda r: str(r["id"]))
        rng.shuffle(bucket)
        n_dev = int(round(len(bucket) * dev_fraction))
        dev_rows.extend(bucket[:n_dev])
        train_rows.extend(bucket[n_dev:])

    return train_rows, dev_rows


def stratified_kfold(rows, k=5, seed=None):
    """Deterministic label-stratified k-fold partition. Returns a list of k lists.

    Used to obtain OUT-OF-FOLD predictions inside the training split (phase 03 C1):
    insertion patterns for the defense must be derived from training-split errors,
    never from dev, or the reported error reduction partly measures the template
    rather than the model. Out-of-fold predictions are made on rows the model did
    not train on, which is the condition dev is evaluated under.

    Same ordering discipline as stratified_split: sort by id inside each label
    bucket before shuffling, so the partition does not depend on read order.
    """
    import config

    seed = config.SEED if seed is None else seed
    if k < 2:
        raise ValueError(f"k must be >= 2, got {k}")

    buckets = defaultdict(list)
    for r in rows:
        buckets[r["label"]].append(r)

    rng = random.Random(seed)
    folds = [[] for _ in range(k)]
    for label in sorted(buckets):
        bucket = sorted(buckets[label], key=lambda r: str(r["id"]))
        rng.shuffle(bucket)
        for i, row in enumerate(bucket):  # deal round-robin -> even, stratified folds
            folds[i % k].append(row)
    return folds


def dev_fingerprint(dev_rows):
    """sha256 over the sorted dev ids -- the identity of a dev set.

    Recorded in every result file. If two result files disagree, this says
    immediately whether they were even measured on the same examples.
    """
    ids = sorted(str(r["id"]) for r in dev_rows)
    if len(set(ids)) != len(ids):
        raise ValueError(
            "Duplicate ids in the dev split -- the corpus has non-unique ids, so a "
            "fingerprint cannot identify the split. Investigate before trusting any "
            "number measured on it."
        )
    return hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# the split as a FILE: generated once, then loaded and verified forever after
# --------------------------------------------------------------------------
#
# Phase 1 S1: "The dev set must be byte-identical across all four rows of the
# Section 8 comparison matrix -- regenerating it per run is how a matrix quietly
# stops comparing like with like."
#
# So the file on disk is authoritative, not the algorithm. `stratified_split()`
# is only ever used to CREATE it. On every later run the file is loaded and
# checked against the corpus fingerprint, and we additionally record whether a
# fresh deterministic split would still reproduce it -- a drift detector, not an
# override: a mismatch is reported, never silently corrected.


def save_split(path, all_rows, train_rows, dev_rows, train_sha256, seed, dev_fraction):
    """Persist a split as ids (authoritative) + positional indices (convenience)."""
    import json
    from datetime import datetime

    index_of = {str(r["id"]): i for i, r in enumerate(all_rows)}
    payload = {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "seed": seed,
        "dev_fraction": dev_fraction,
        "train_sha256": train_sha256,
        "n_rows": len(all_rows),
        "dev_fingerprint": dev_fingerprint(dev_rows),
        "counts": {
            "train": dict(Counter(r["label"] for r in train_rows)),
            "dev": dict(Counter(r["label"] for r in dev_rows)),
        },
        "train_ids": [str(r["id"]) for r in train_rows],
        "dev_ids": [str(r["id"]) for r in dev_rows],
        "train_indices": [index_of[str(r["id"])] for r in train_rows],
        "dev_indices": [index_of[str(r["id"])] for r in dev_rows],
    }
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    return payload


def load_split(path, all_rows, train_sha256=None):
    """Load a saved split and verify it still describes THIS corpus.

    Raises if the corpus fingerprint changed, if any saved id is missing, or if
    train/dev overlap. Returns (train_rows, dev_rows, meta).
    """
    import json

    meta = json.loads(Path(path).read_text(encoding="utf-8"))
    if train_sha256 is not None and meta.get("train_sha256") != train_sha256:
        raise ValueError(
            f"Split file {path} was built from a different corpus.\n"
            f"  split file : {meta.get('train_sha256')}\n"
            f"  corpus now : {train_sha256}\n"
            "Every number measured against this split would be measured on different "
            "data than the one it claims. Regenerate deliberately, do not ignore."
        )

    by_id = {str(r["id"]): r for r in all_rows}
    missing = [i for i in meta["train_ids"] + meta["dev_ids"] if i not in by_id]
    if missing:
        raise ValueError(
            f"{len(missing)} ids in {path} are not in the corpus (first: {missing[:5]})."
        )
    overlap = set(meta["train_ids"]) & set(meta["dev_ids"])
    if overlap:
        raise ValueError(
            f"Split file leaks {len(overlap)} ids into both train and dev "
            f"(first: {sorted(overlap)[:5]}). Every dev number would be train accuracy."
        )

    train_rows = [by_id[i] for i in meta["train_ids"]]
    dev_rows = [by_id[i] for i in meta["dev_ids"]]
    return train_rows, dev_rows, meta


def get_split(all_rows, path, train_sha256, seed=None, dev_fraction=None):
    """The only split entry point callers should use.

    Creates the split file on first use, loads and verifies it thereafter.
    Returns (train_rows, dev_rows, meta) where meta["reused_existing_file"] and
    meta["matches_regeneration"] record how the split was obtained -- both go
    into the result file so a reader can tell.
    """
    import config

    seed = config.SEED if seed is None else seed
    dev_fraction = config.DEV_FRACTION if dev_fraction is None else dev_fraction
    path = Path(path)

    if not path.exists():
        train_rows, dev_rows = stratified_split(all_rows, dev_fraction, seed)
        meta = save_split(path, all_rows, train_rows, dev_rows, train_sha256, seed, dev_fraction)
        meta["reused_existing_file"] = False
        meta["matches_regeneration"] = True
        return train_rows, dev_rows, meta

    train_rows, dev_rows, meta = load_split(path, all_rows, train_sha256)
    _, fresh_dev = stratified_split(all_rows, meta["dev_fraction"], meta["seed"])
    meta["reused_existing_file"] = True
    meta["matches_regeneration"] = dev_fingerprint(fresh_dev) == meta["dev_fingerprint"]
    return train_rows, dev_rows, meta


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
