"""Data for m3's multi-head fine-tune: the frozen split through the study's own reader,
one label table per head, and the leakage guards - inherited, not re-implemented.

Heads and their label sources (docs/blockers/m3_head_labels.md, owner decisions 2026-09-18):
  binary  OFF / NOT from the corpus itself - always available
  A       "profanity present" on the A1 carrier. TRAINING supervision: the terlik-derived
          pseudo-labels of the frozen TRAIN split (eval/derived/m1_lexicon_train_seed42.json,
          `a_label`, protocols/m1_lexicon_train_labels_protocol.md). EVALUATION: a declared DEV
          reference under docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md whose provenance kind is
          stated on the command line (`--labels-a-human` for a fully human-labelled set,
          `--labels-a-reference` + `--labels-a-reference-kind` otherwise; provenance.py). Its rows are
          `a_reference` here and in every published key. Pseudo-labels on dev rows are only ever
          reported as AGREEMENT, never as accuracy.
  B       B1 / B2 / B3 / B5, multi-label - from a label file (no corpus exists yet)
  C       C1 .. C5, single label - from a label file (slice being labelled)
A head without a label file is trained on nothing: its loss is masked on every row and the
exported artifact records `trained: false` for it, so the module never publishes its scores.

Every path comes from the caller or the environment (NSOSYAL_DATA), never from a constant.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from training.m3_encoder.provenance import REFERENCE_KEY

AI_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ROOT.parent
DIAGNOSIS = REPO_ROOT / "diagnosis"
FROZEN_SPLIT = DIAGNOSIS / "data" / "splits" / "split_seed42.json"
# Recorded in the study (docs/team/abdullah/RESOURCES.md); get_split refuses a different corpus.
TRAIN_SHA256 = "8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa"
DEV_FINGERPRINT = "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4"

# m3 spec §5: banned outright. Refused by name before any file is opened.
BANNED_DATASETS = ("Toygar/turkish-offensive-language-detection", "Overfit-GM/turkish-toxic-language")

BINARY_LABELS = ("NOT", "OFF")
A_CODES = ("A1",)                       # the carrier (ADR-005): one "profanity present" score
B_CODES = ("B1", "B2", "B3", "B5")      # B4 is m6's (spec §3)
C_CODES = ("C1", "C2", "C3", "C4", "C5")
MISSING = -100                          # PyTorch ignore_index; also the mask value for A / B


class LeakageError(RuntimeError):
    """A banned dataset, the spent test set, or a split that is not the frozen one."""


def refuse_banned(*names: str) -> None:
    hits = [n for n in names for b in BANNED_DATASETS if b.lower() in str(n).lower()]
    if hits:
        raise LeakageError(f"banned dataset named in the training path (m3 spec §5): {hits}")


def _diagnosis_on_path() -> None:
    if str(DIAGNOSIS) not in sys.path:
        sys.path.insert(0, str(DIAGNOSIS))


@dataclass(frozen=True)
class Row:
    row_id: str
    text: str
    binary: int                          # 0 NOT / 1 OFF
    a: int = MISSING                     # 0 / 1 / MISSING - pseudo-label (training supervision)
    b: tuple[int, ...] = (MISSING,) * len(B_CODES)   # per code 0 / 1 / MISSING
    c: int = MISSING                     # index into C_CODES / MISSING
    a_reference: int = MISSING           # 0 / 1 / MISSING - evaluation-reference label (never trained on)


@dataclass
class Split:
    train: list[Row]
    dev: list[Row]
    meta: dict[str, Any] = field(default_factory=dict)
    label_coverage: dict[str, dict[str, int]] = field(default_factory=dict)
    label_sources: dict[str, list[dict[str, str]]] = field(default_factory=dict)   # head -> [{file, sha256, kind}]


def load_frozen_split(corpus_path: str | Path | None = None) -> tuple[list[dict], list[dict], dict]:
    """The frozen split, verified: corpus hash, ids present, no overlap, dev fingerprint.
    Raises LeakageError if the split had to be created (it must exist)."""
    _diagnosis_on_path()
    from src import data_io  # the study's reader: no pandas, tab-safe (RESOURCES.md)

    if corpus_path is not None:
        refuse_banned(corpus_path)
    rows = data_io.load_coltekin_train(corpus_path)
    if not FROZEN_SPLIT.exists():
        raise LeakageError(f"frozen split missing: {FROZEN_SPLIT}; never create a split (RESOURCES.md)")
    train, dev, meta = data_io.get_split(rows, FROZEN_SPLIT, TRAIN_SHA256)
    if not meta.get("reused_existing_file"):
        raise LeakageError("a split was created instead of loading the frozen one - stop")
    if meta.get("dev_fingerprint") != DEV_FINGERPRINT:
        raise LeakageError(f"dev fingerprint {meta.get('dev_fingerprint')} is not the frozen {DEV_FINGERPRINT}")
    return train, dev, meta


# -- label tables --------------------------------------------------------------------------
def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                yield json.loads(line)


def sha256_of(path: str | Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_a_labels(path: str | Path) -> dict[str, int]:
    """row_id -> 0/1. Accepts (a) a jsonl of {"row_id", "label"} (the human oracle's export or
    any hand-made file) or (b) a derived-labels file written by eval/m1_lexicon_labels.py
    (`.json`, rows with `a_label` - the pseudo-label rule of the train protocol §5; a pre-2.0
    file without `a_label` falls back to `lexicon_hit`). The pseudo-label is a keyword label:
    it supervises, it never evaluates (evaluate.py keeps the two apart)."""
    path = Path(path)
    if path.suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        # rule v2: a_label null = REVIEW-class-only post, deliberately unlabelled -> left MISSING (masked)
        return {str(r["row_id"]): int(r["a_label"] if "a_label" in r else bool(r["lexicon_hit"]))
                for r in data["rows"] if not ("a_label" in r and r["a_label"] is None)}
    table = {}
    for r in _read_jsonl(path):
        label = int(r["label"])
        if label not in (0, 1):
            raise ValueError(f"row {r['row_id']}: A label {r['label']!r} is not 0/1")
        table[str(r["row_id"])] = label
    return table


def load_a_label_files(paths: Iterable[str | Path]) -> tuple[dict[str, int], list[dict[str, str]]]:
    """Several A label files merged (train + dev pseudo-labels are separate files by protocol).
    A row labelled differently by two files is an error, never a silent overwrite."""
    merged: dict[str, int] = {}
    sources: list[dict[str, str]] = []
    for path in paths:
        table = load_a_labels(path)
        for rid, label in table.items():
            if merged.get(rid, label) != label:
                raise ValueError(f"row {rid}: conflicting A labels across files ({path})")
            merged[rid] = label
        sources.append({"file": Path(path).name, "sha256": sha256_of(path),
                        "kind": "derived-pseudo-label" if Path(path).suffix == ".json" else "jsonl"})
    return merged, sources


def load_b_labels(path: str | Path) -> dict[str, tuple[int, ...]]:
    """row_id -> per-code 0/1 over B_CODES; jsonl of {"row_id", "codes": [...]}. Multi-label:
    a row may carry several codes (spec §2). Unknown codes are an error, not silently dropped."""
    table: dict[str, tuple[int, ...]] = {}
    for r in _read_jsonl(Path(path)):
        codes = set(r["codes"])
        unknown = codes - set(B_CODES)
        if unknown:
            raise ValueError(f"row {r['row_id']}: B codes outside {B_CODES}: {sorted(unknown)}")
        table[str(r["row_id"])] = tuple(int(c in codes) for c in B_CODES)
    return table


def load_c_labels(path: str | Path) -> dict[str, int]:
    """row_id -> index into C_CODES; jsonl of {"row_id", "code"}; "CLEAN" or null means
    'labelled, none of C1-C5' and is stored as the extra class index len(C_CODES)."""
    table: dict[str, int] = {}
    for r in _read_jsonl(Path(path)):
        code = r.get("code")
        if code in (None, "CLEAN", "NONE"):
            table[str(r["row_id"])] = len(C_CODES)
        elif code in C_CODES:
            table[str(r["row_id"])] = C_CODES.index(code)
        else:
            raise ValueError(f"row {r['row_id']}: C code outside {C_CODES}: {code!r}")
    return table


def _as_paths(value: Any) -> list[Path]:
    if value is None:
        return []
    if isinstance(value, (str, Path)):
        return [Path(value)]
    return [Path(v) for v in value]


def build_split(corpus_path: str | Path | None = None, labels_a: Any = None,
                labels_b: str | Path | None = None, labels_c: str | Path | None = None,
                labels_a_reference: str | Path | None = None) -> Split:
    """Rows of the frozen split with every head's label attached (MISSING where a head has no
    label for the row). `labels_a` is one path or several (pseudo-labels: train supervision, and
    on dev rows only agreement reporting); `labels_a_reference` is the A evaluation reference (dev
    rows), never used for training - its provenance KIND is resolved by the caller
    (evaluate.resolve_a_reference), not here. `label_coverage` records, per head and split, how many
    rows are labelled - the number every metric must be read against."""
    a_paths = _as_paths(labels_a)
    for p in (corpus_path, *a_paths, labels_b, labels_c, labels_a_reference):
        if p is not None:
            refuse_banned(p)
    train_raw, dev_raw, meta = load_frozen_split(corpus_path)
    a, a_sources = load_a_label_files(a_paths)
    a_ref, a_ref_sources = load_a_label_files([labels_a_reference]) if labels_a_reference else ({}, [])
    b = load_b_labels(labels_b) if labels_b else {}
    c = load_c_labels(labels_c) if labels_c else {}

    def convert(rows: list[dict]) -> list[Row]:
        out = []
        for r in rows:
            rid = str(r["id"])
            out.append(Row(row_id=rid, text=r["text"], binary=int(r["label"] == "OFF"),
                           a=a.get(rid, MISSING), b=b.get(rid, (MISSING,) * len(B_CODES)),
                           c=c.get(rid, MISSING), a_reference=a_ref.get(rid, MISSING)))
        return out

    train, dev = convert(train_raw), convert(dev_raw)
    reference_on_train = sum(r.a_reference != MISSING for r in train)
    if reference_on_train:
        # The evaluation reference is a dev subset by design (guideline §1): a reference label on a
        # train row would let an evaluation number be read on rows the encoder was fitted on.
        raise ValueError(f"{reference_on_train} evaluation-reference A labels fall on TRAIN rows; "
                         "the reference must be a dev subset")
    coverage = {}
    for name, rows in (("train", train), ("dev", dev)):
        coverage[name] = {"rows": len(rows), "binary": len(rows),
                          "a": sum(r.a != MISSING for r in rows),
                          REFERENCE_KEY: sum(r.a_reference != MISSING for r in rows),
                          "b": sum(r.b[0] != MISSING for r in rows),
                          "c": sum(r.c != MISSING for r in rows)}
    return Split(train=train, dev=dev, meta={k: v for k, v in meta.items() if k not in ("train_ids", "dev_ids",
                                                                                          "train_indices", "dev_indices")},
                 label_coverage=coverage,
                 label_sources={"a": a_sources, REFERENCE_KEY: a_ref_sources,
                                "b": [{"file": Path(labels_b).name, "sha256": sha256_of(labels_b), "kind": "jsonl"}] if labels_b else [],
                                "c": [{"file": Path(labels_c).name, "sha256": sha256_of(labels_c), "kind": "jsonl"}] if labels_c else []})


def corpus_path_from_env() -> Path | None:
    """NSOSYAL_DATA/coltekin/offenseval-tr-training-v1.tsv when NSOSYAL_DATA is set, else None
    (the study's config resolves the default under diagnosis/data)."""
    root = os.environ.get("NSOSYAL_DATA")
    return Path(root) / "coltekin" / "offenseval-tr-training-v1.tsv" if root else None
