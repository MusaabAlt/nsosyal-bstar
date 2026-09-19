"""A-head human annotation package - draws the DEV sample the annotators label under
docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md, checks filled files, adjudicates between
annotators and exports the oracle the trainer reads (`--labels-a-human`).

    python -m eval.a_head_dev_sample draw --n 500 --seed 42 --annotator ann1 [--annotator ann2]
    python -m eval.a_head_dev_sample check eval/annotation/private/<file>.jsonl
    python -m eval.a_head_dev_sample adjudicate <ann1 file> <ann2 file> --out <adjudication file>
    python -m eval.a_head_dev_sample export <checked annotator file | adjudication file> --out <labels jsonl>

What the annotator sees: row_id and the ORIGINAL text, in a seeded random order. Nothing else -
no OFF/NOT gold, no lexicon flag, no model score, no derived-file field. The ids file that is
committed (eval/annotation/) holds the design and the ids; the files holding corpus text live in
eval/annotation/private/ (git-ignored: the corpus is never committed).

Deliberately does NOT:
  * read any prediction, the derived label files, the frozen slice or thresholds
  * touch the train split or the official test set (only dev_ids of the frozen split; test-set
    paths are refused as in eval/m1_lexicon_labels.py)
  * fill a label: labels are null until a human writes 0 or 1
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from eval.m1_lexicon_labels import AI_ROOT, GENERATOR_VERSION as _LABELS_VERSION, Spec, fingerprint, git, read_corpus, \
    refuse_test_set, sha256_file

SAMPLER_VERSION = "1.0.0"
GUIDELINE = "docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md"
ANNOTATION_DIR = AI_ROOT / "eval" / "annotation"
PRIVATE_DIR = ANNOTATION_DIR / "private"
TEMPLATE_FIELDS = ("row_id", "text", "label", "uncertain", "notes")
LABELS = (0, 1)

del _LABELS_VERSION  # imported only to fail loudly if the generator module moves


class SampleError(Exception):
    pass


def require(ok: bool, what: str) -> None:
    if not ok:
        raise SampleError(what)


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for n, line in enumerate(fh, start=1):
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError as exc:
                    raise SampleError(f"{path.name}:{n}: not JSON ({exc})") from exc
    return rows


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")


# -- draw ---------------------------------------------------------------------
def load_dev(spec: Spec) -> tuple[list[str], dict[str, tuple[str, str]], dict[str, Any]]:
    """dev ids (split order), corpus, input digests - the split/corpus checks of the label
    generator, restricted to what a sample needs (no gold count is written anywhere)."""
    refuse_test_set(spec.corpus, spec.split_file)
    hashes = {}
    for key, path, want in (("corpus", spec.corpus, spec.corpus_sha256), ("split", spec.split_file, spec.split_sha256)):
        require(path.is_file(), f"missing input {path}")
        got = sha256_file(path)
        require(got == want, f"sha256 mismatch for {path}: {got}")
        hashes[key] = {"file": path.name, "sha256": got}
    split = json.loads(spec.split_file.read_text(encoding="utf-8"))
    require(split.get("seed") == spec.seed, f"split seed {split.get('seed')}")
    dev_ids = [str(i) for i in split["dev_ids"]]
    require(fingerprint(dev_ids) == spec.expected["dev"]["fingerprint"], "dev fingerprint")
    require(not set(dev_ids) & {str(i) for i in split["train_ids"]}, "train/dev overlap")
    corpus = read_corpus(spec.corpus)
    require(all(i in corpus for i in dev_ids), "dev ids missing from the corpus")
    return dev_ids, corpus, hashes


def draw_ids(dev_ids: list[str], n: int, seed: int) -> list[str]:
    """Simple random sample without replacement from the dev split, in a seeded random order.
    Uniform: the sample estimates the dev distribution without weights (guideline §6)."""
    require(0 < n <= len(dev_ids), f"n must be in 1..{len(dev_ids)}")
    rng = random.Random(seed)
    chosen = rng.sample(sorted(dev_ids), n)
    rng.shuffle(chosen)
    return chosen


def draw(spec: Spec, n: int, seed: int, annotators: list[str], out_dir: Path) -> tuple[Path, list[Path]]:
    dev_ids, corpus, hashes = load_dev(spec)
    ids = draw_ids(dev_ids, n, seed)
    stem = f"a_head_dev_sample_seed{seed}_n{n}"
    ids_file = out_dir / f"{stem}.ids.json"
    design = {
        "_README": "A-head human annotation sample: a uniform random sample of the frozen DEV split (seed 42), "
                   "labelled under docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md. The evaluation oracle for m3's "
                   "A head. Texts live in eval/annotation/private/ (never committed). Labels are written by humans "
                   "only; nothing here is a prediction.",
        "sampler": {"script": "AI/eval/a_head_dev_sample.py", "version": SAMPLER_VERSION,
                    "git_head": git("rev-parse", "HEAD").stdout.strip() or None,
                    "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds")},
        "guideline": {"file": f"AI/{GUIDELINE}",
                      "sha256": sha256_file(AI_ROOT / GUIDELINE) if (AI_ROOT / GUIDELINE).is_file() else None},
        "design": {"population": "frozen dev split, seed 42", "n_population": len(dev_ids), "n": n, "seed": seed,
                   "method": "simple random sample without replacement (random.Random(seed).sample over sorted ids), "
                             "then a seeded shuffle for presentation order", "weights": "none (uniform)"},
        "inputs": hashes,
        "dev_fingerprint": spec.expected["dev"]["fingerprint"],
        "annotators": annotators,
        "ids_in_presentation_order": ids,
        "ids_sha256": hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest(),
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    ids_file.write_text(json.dumps(design, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    files = []
    for annotator in annotators:
        path = out_dir / "private" / f"{stem}.{annotator}.jsonl"
        _write_jsonl(path, [{"row_id": i, "text": corpus[i][0], "label": None, "uncertain": False, "notes": ""}
                            for i in ids])
        files.append(path)
    return ids_file, files


# -- check --------------------------------------------------------------------
def check_file(path: Path, ids_file: Path, allow_incomplete: bool = False) -> dict[str, Any]:
    """A filled annotator file: exactly the sample's ids, once each, label 0/1 (null only when
    allowed), uncertain a bool, notes a string. Returns the counts."""
    design = json.loads(ids_file.read_text(encoding="utf-8"))
    expected = design["ids_in_presentation_order"]
    rows = _read_jsonl(path)
    problems = []
    ids = [str(r.get("row_id")) for r in rows]
    if Counter(ids) != Counter(expected):
        missing = sorted(set(expected) - set(ids))
        extra = sorted(set(ids) - set(expected))
        dupes = sorted(i for i, c in Counter(ids).items() if c > 1)
        problems.append(f"ids differ from the sample: missing {len(missing)}, extra {len(extra)}, duplicated {len(dupes)}")
    unlabelled = 0
    for r in rows:
        label = r.get("label")
        if label is None:
            unlabelled += 1
            if not allow_incomplete:
                problems.append(f"row {r.get('row_id')}: label is null")
        elif label not in LABELS or isinstance(label, bool):
            problems.append(f"row {r.get('row_id')}: label {label!r} is not 0/1")
        if not isinstance(r.get("uncertain", False), bool):
            problems.append(f"row {r.get('row_id')}: uncertain is not a bool")
        if not isinstance(r.get("notes", ""), str):
            problems.append(f"row {r.get('row_id')}: notes is not a string")
        if set(r) - set(TEMPLATE_FIELDS):
            problems.append(f"row {r.get('row_id')}: unexpected fields {sorted(set(r) - set(TEMPLATE_FIELDS))}")
    if problems:
        raise SampleError("; ".join(problems[:10]) + (f"; +{len(problems) - 10} more" if len(problems) > 10 else ""))
    labels = [r["label"] for r in rows if r.get("label") is not None]
    return {"n": len(rows), "labelled": len(labels), "unlabelled": unlabelled, "positives": sum(labels),
            "negatives": len(labels) - sum(labels), "uncertain": sum(bool(r.get("uncertain")) for r in rows)}


# -- adjudicate ----------------------------------------------------------------
def cohen_kappa(a: list[int], b: list[int]) -> float | None:
    n = len(a)
    if n == 0:
        return None
    observed = sum(x == y for x, y in zip(a, b)) / n
    pa1, pb1 = sum(a) / n, sum(b) / n
    expected = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return None if expected == 1 else (observed - expected) / (1 - expected)


def adjudicate(files: list[Path], ids_file: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Agreement between complete annotator files and the adjudication template: rows every
    annotator labelled alike get `final` filled with that label; disagreements get `final: null`
    for the adjudicator (guideline §7)."""
    require(len(files) >= 2, "adjudication needs at least two annotator files")
    tables = {}
    for path in files:
        check_file(path, ids_file)
        tables[path.stem.rsplit(".", 1)[-1]] = {str(r["row_id"]): r for r in _read_jsonl(path)}
    names = list(tables)
    require(len(set(names)) == len(names), "annotator names (file suffix) must differ")
    ids = json.loads(ids_file.read_text(encoding="utf-8"))["ids_in_presentation_order"]
    rows = []
    for rid in ids:
        labels = {name: tables[name][rid]["label"] for name in names}
        agreed = len(set(labels.values())) == 1
        rows.append({"row_id": rid, "labels": labels,
                     "uncertain": {name: bool(tables[name][rid].get("uncertain")) for name in names},
                     "notes": {name: tables[name][rid].get("notes", "") for name in names},
                     "final": next(iter(labels.values())) if agreed else None,
                     "adjudicator_notes": ""})
    pairwise = {}
    for i, x in enumerate(names):
        for y in names[i + 1:]:
            a = [tables[x][r]["label"] for r in ids]
            b = [tables[y][r]["label"] for r in ids]
            pairwise[f"{x}|{y}"] = {"percent_agreement": sum(p == q for p, q in zip(a, b)) / len(ids),
                                    "cohen_kappa": cohen_kappa(a, b)}
    stats = {"n": len(ids), "annotators": names, "agreed": sum(r["final"] is not None for r in rows),
             "disagreed": sum(r["final"] is None for r in rows), "pairwise": pairwise,
             "positives_per_annotator": {name: sum(tables[name][r]["label"] for r in ids) for name in names}}
    return stats, rows


# -- export -------------------------------------------------------------------
def export(source: Path, ids_file: Path, out: Path) -> dict[str, Any]:
    """The oracle file the trainer reads: {"row_id","label"} per line, from one checked annotator
    file or an adjudication file whose every `final` is filled. Refuses an unlabelled row."""
    rows = _read_jsonl(source)
    if rows and "final" in rows[0]:
        labels = {str(r["row_id"]): r["final"] for r in rows}
        kind = "adjudication"
    else:
        check_file(source, ids_file)
        labels = {str(r["row_id"]): r["label"] for r in rows}
        kind = "single-annotator"
    design = json.loads(ids_file.read_text(encoding="utf-8"))
    expected = design["ids_in_presentation_order"]
    require(set(labels) == set(expected), "labels do not cover exactly the sample ids")
    missing = [rid for rid, label in labels.items() if label not in LABELS or isinstance(label, bool)]
    require(not missing, f"{len(missing)} rows without a final 0/1 label (first: {missing[:5]})")
    _write_jsonl(out, [{"row_id": rid, "label": int(labels[rid])} for rid in expected])
    provenance = {"kind": kind, "source": source.name, "source_sha256": sha256_file(source),
                  "ids_file": ids_file.name, "ids_sha256": design["ids_sha256"], "guideline": design.get("guideline"),
                  "n": len(expected), "positives": sum(int(labels[r]) for r in expected),
                  "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                  "labels_sha256": sha256_file(out)}
    out.with_suffix(".provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8", newline="\n")
    return provenance


# -- cli ----------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m eval.a_head_dev_sample", description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("draw", help="draw the dev sample and write one template per annotator")
    d.add_argument("--n", type=int, default=500)
    d.add_argument("--seed", type=int, default=42)
    d.add_argument("--annotator", action="append", required=True, help="repeatable; one template per name")
    d.add_argument("--out-dir", type=Path, default=ANNOTATION_DIR)
    c = sub.add_parser("check", help="validate a filled annotator file")
    c.add_argument("file", type=Path)
    c.add_argument("--ids", type=Path, required=True)
    c.add_argument("--allow-incomplete", action="store_true")
    a = sub.add_parser("adjudicate", help="agreement between annotators + adjudication template")
    a.add_argument("files", type=Path, nargs="+")
    a.add_argument("--ids", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("export", help="write the {row_id,label} oracle the trainer reads")
    e.add_argument("source", type=Path)
    e.add_argument("--ids", type=Path, required=True)
    e.add_argument("--out", type=Path, required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        if args.cmd == "draw":
            ids_file, files = draw(Spec(split="dev"), args.n, args.seed, args.annotator, args.out_dir)
            print(f"wrote {ids_file} (commit this) and {len(files)} private template(s):")
            for f in files:
                print(f"  {f}  (git-ignored: holds corpus text)")
        elif args.cmd == "check":
            print(json.dumps(check_file(args.file, args.ids, args.allow_incomplete)))
        elif args.cmd == "adjudicate":
            stats, rows = adjudicate(args.files, args.ids)
            _write_jsonl(args.out, rows)
            print(json.dumps(stats, indent=2))
            print(f"wrote {args.out}: fill `final` on the {stats['disagreed']} disagreement row(s)")
        elif args.cmd == "export":
            print(json.dumps(export(args.source, args.ids, args.out), indent=2))
    except SampleError as exc:
        print(f"STOP: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
