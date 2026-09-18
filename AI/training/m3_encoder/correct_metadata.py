"""Metadata-only correction of an exported multi-head artifact (model.export_artifact), WITHOUT
retraining and without touching a tensor.

    python -m training.m3_encoder.correct_metadata correct --artifact SRC --out DST --expect-weights-sha256 H
    python -m training.m3_encoder.correct_metadata verify  --artifact DST --expect-weights-sha256 H

Catches: provenance wording an older exporter published that is false for the artifact's OWN
declared evaluation reference, and rewrites it from the kind the artifact itself records
(heads.json `a_evaluation_reference_kind`, provenance.py):
  * heads.json `a_head_supervision` (the generic "human dev oracle" sentence);
  * the `a_human` key in label_coverage.{train,dev} and label_sources (heads.json, dev_eval.json),
    renamed `a_reference` - values unchanged;
  * dev_eval.json a.note, only where it is the legacy "no human A labels" wording.

Guarantees, each ASSERTED (the run stops with nothing written to SRC otherwise):
  * SRC is never opened for writing; the corrected artifact is a NEW directory DST;
  * every file listed in SRC/sha256.txt verifies before anything is written;
  * weights.pt is copied byte for byte and its sha256 equals the expected digest in SRC before,
    in SRC after, and in DST;
  * everything else in dev_eval.json (every metric block, the export-time `digests`) and in
    heads.json (heads, history, hyperparameters, split, every label digest) is equal as JSON;
  * the original bytes are kept in DST/original_metadata/, every digest before and after is in
    DST/metadata_correction.json, and sha256.txt lists the same files with their new digests;
  * `verify` re-derives the corrected files from the kept originals and compares BYTES.

Deliberately does NOT: re-evaluate, change a metric, infer a reference kind the artifact does not
record, add or remove a file from sha256.txt, overwrite an existing directory, or correct an
artifact twice.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from training.m3_encoder import provenance as P

TOOL_VERSION = "1.0.0"
CORRECTION_ID = "a-reference-provenance-wording-v1"
RECORD = "metadata_correction.json"
ORIGINALS = "original_metadata"
# Fields this correction may change; everything else must be equal as JSON.
HEADS_FIELDS = ("a_head_supervision", "label_coverage", "label_sources", "metadata_corrections")
DEV_EVAL_FIELDS = ("label_coverage", "label_sources", "a", "metadata_corrections")
LEGACY_SUPERVISION = ("terlik-derived pseudo-labels (keyword); quality claims only against the human "
                      "dev oracle (dev_eval.json 'a'), never against pseudo-label agreement")
_ABSENT = object()


class CorrectionError(RuntimeError):
    """The artifact cannot be corrected safely; nothing was written to its source."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def dump(obj: Any) -> bytes:
    """The exporter's own serialisation (train.py / model.export_artifact)."""
    return (json.dumps(obj, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def read_digests(path: Path) -> list[tuple[str, str]]:
    """sha256.txt as written by export_artifact: '<digest>  <name>' per line, order kept."""
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            digest, name = line.split("  ", 1)
            out.append((digest, name))
    return out


def write_digests(entries: list[tuple[str, str]]) -> bytes:
    return "".join(f"{d}  {n}\n" for d, n in entries).encode("utf-8")


def _rename(mapping: dict[str, Any], old: str, new: str) -> dict[str, Any]:
    """Same dict with key `old` renamed to `new` in place (key order kept)."""
    if old in mapping and new in mapping:
        raise CorrectionError(f"both {old!r} and {new!r} present: refusing to guess which is right")
    return {(new if k == old else k): v for k, v in mapping.items()}


def _rename_reference_keys(doc: dict[str, Any], changes: list[dict], file: str) -> dict[str, Any]:
    old, new = P.LEGACY_REFERENCE_KEY, P.REFERENCE_KEY
    out = dict(doc)
    coverage = doc.get("label_coverage")
    if isinstance(coverage, dict):
        out["label_coverage"] = {}
        for split, counts in coverage.items():
            if isinstance(counts, dict) and old in counts:
                changes.append({"file": file, "path": f"label_coverage.{split}", "rename": [old, new]})
                counts = _rename(counts, old, new)
            out["label_coverage"][split] = counts
    sources = doc.get("label_sources")
    if isinstance(sources, dict) and old in sources:
        changes.append({"file": file, "path": "label_sources", "rename": [old, new]})
        out["label_sources"] = _rename(sources, old, new)
    return out


def correct_heads(heads: dict[str, Any], original_sha256: str) -> tuple[dict[str, Any], list[dict]]:
    """Pure: the corrected heads.json value and the list of changes."""
    kind = heads.get("a_evaluation_reference_kind", _ABSENT)
    if kind is _ABSENT:
        raise CorrectionError("heads.json does not record a_evaluation_reference_kind: the reference's provenance "
                              "cannot be inferred, so the supervision sentence cannot be corrected truthfully")
    if "metadata_corrections" in heads:
        raise CorrectionError("heads.json already carries metadata_corrections: an artifact is corrected once")
    changes: list[dict] = []
    out = _rename_reference_keys(heads, changes, "heads.json")
    wanted = P.a_head_supervision(kind)
    if out.get("a_head_supervision") != wanted:
        changes.append({"file": "heads.json", "path": "a_head_supervision",
                        "before": out.get("a_head_supervision"), "after": wanted})
        out["a_head_supervision"] = wanted
    if not changes:
        raise CorrectionError("nothing to correct: heads.json already states its provenance truthfully")
    out["metadata_corrections"] = [{"id": CORRECTION_ID, "record": RECORD, "original_sha256": original_sha256,
                                    "fields": sorted({c["path"] for c in changes})}]
    return out, changes


def correct_dev_eval(dev_eval: dict[str, Any], original_sha256: str,
                     heads_before: str, heads_after: str) -> tuple[dict[str, Any], list[dict]]:
    """Pure: the corrected dev_eval.json value. Metric blocks are carried over untouched."""
    if "metadata_corrections" in dev_eval:
        raise CorrectionError("dev_eval.json already carries metadata_corrections: an artifact is corrected once")
    changes: list[dict] = []
    out = _rename_reference_keys(dev_eval, changes, "dev_eval.json")
    a = out.get("a")
    if isinstance(a, dict) and a.get("note") == P.LEGACY_NO_REFERENCE_NOTE:
        changes.append({"file": "dev_eval.json", "path": "a.note", "before": a["note"], "after": P.NO_REFERENCE_NOTE})
        out["a"] = {**a, "note": P.NO_REFERENCE_NOTE}
    out["metadata_corrections"] = [{
        "id": CORRECTION_ID, "record": RECORD, "original_sha256": original_sha256,
        "fields": sorted({c["path"] for c in changes}),
        "metrics": "unchanged: every metric block is the export-time evaluation of the unchanged weights",
        "digests": f"export-time digests; heads.json was {heads_before} when exported and is {heads_after} "
                   f"after this metadata-only correction (originals in {ORIGINALS}/)"}]
    return out, changes


def _equal_outside(original: dict, corrected: dict, allowed: tuple[str, ...]) -> list[str]:
    """Fields outside `allowed` that differ, plus reference-key renames whose VALUES changed."""
    bad = [k for k in set(original) | set(corrected) if k not in allowed and original.get(k) != corrected.get(k)]
    old, new = P.LEGACY_REFERENCE_KEY, P.REFERENCE_KEY
    back = lambda d: {(old if k == new else k): v for k, v in d.items()}
    for key in ("label_coverage",):
        o, c = original.get(key), corrected.get(key)
        if isinstance(o, dict) and isinstance(c, dict):
            if set(o) != set(c) or any(back(c[s]) != back(o[s]) for s in o):
                bad.append(key)
    for key in ("label_sources",):
        o, c = original.get(key), corrected.get(key)
        if isinstance(o, dict) and isinstance(c, dict) and back(c) != back(o):
            bad.append(key)
    if "a" in allowed and isinstance(original.get("a"), dict):
        o, c = original["a"], corrected.get("a", {})
        if {k: v for k, v in o.items() if k != "note"} != {k: v for k, v in c.items() if k != "note"}:
            bad.append("a")
    return sorted(bad)


def derive(originals: dict[str, bytes]) -> tuple[dict[str, bytes], list[dict]]:
    """Pure: corrected heads.json, dev_eval.json and sha256.txt from the ORIGINAL bytes."""
    heads_raw, dev_raw, sums_raw = originals["heads.json"], originals.get("dev_eval.json"), originals["sha256.txt"]
    heads_sha = sha256_bytes(heads_raw)
    heads, changes = correct_heads(json.loads(heads_raw), heads_sha)
    new_heads = dump(heads)
    out = {"heads.json": new_heads}
    if dev_raw is not None:
        dev_eval, dev_changes = correct_dev_eval(json.loads(dev_raw), sha256_bytes(dev_raw), heads_sha,
                                                 sha256_bytes(new_heads))
        changes += dev_changes
        out["dev_eval.json"] = dump(dev_eval)
        bad = _equal_outside(json.loads(dev_raw), dev_eval, DEV_EVAL_FIELDS)
        if bad:
            raise CorrectionError(f"dev_eval.json fields outside the correction changed: {bad}")
    bad = _equal_outside(json.loads(heads_raw), heads, HEADS_FIELDS)
    if bad:
        raise CorrectionError(f"heads.json fields outside the correction changed: {bad}")
    entries = read_digests_bytes(sums_raw)
    names = [n for _, n in entries]
    if "heads.json" not in names or "weights.pt" not in names:
        raise CorrectionError(f"sha256.txt does not list heads.json and weights.pt: {names}")
    out["sha256.txt"] = write_digests([(sha256_bytes(out[n]) if n in out else d, n) for d, n in entries])
    return out, changes


def read_digests_bytes(data: bytes) -> list[tuple[str, str]]:
    return [tuple(line.split("  ", 1)) for line in data.decode("utf-8").splitlines() if line.strip()]  # type: ignore[misc]


def _git_state() -> dict[str, Any]:
    repo = Path(__file__).resolve().parents[2]
    try:
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip() or None
        dirty = subprocess.run(["git", "-C", str(repo), "status", "--porcelain", "--", "training/m3_encoder"],
                               capture_output=True, text=True, timeout=30).stdout.split("\n")
        return {"tool_git_head": head, "tool_uncommitted_changes": [l for l in dirty if l.strip()]}
    except (OSError, subprocess.SubprocessError):
        return {"tool_git_head": None, "tool_uncommitted_changes": None}


def _verify_listed(directory: Path, entries: list[tuple[str, str]]) -> list[str]:
    return [f"{n}: missing" if not (directory / n).is_file() else f"{n}: {sha256_file(directory / n)} != {d}"
            for d, n in entries if not (directory / n).is_file() or sha256_file(directory / n) != d]


def correct(src: Path, dst: Path, expect_weights: str) -> dict[str, Any]:
    src, dst = src.resolve(), dst.resolve()
    if dst.exists():
        raise CorrectionError(f"{dst} exists: the corrected artifact is always a NEW directory")
    if dst == src or src in dst.parents or dst in src.parents:
        raise CorrectionError("source and output must be separate directories")
    if not (src / "sha256.txt").is_file() or not (src / "weights.pt").is_file():
        raise CorrectionError(f"{src} is not an exported artifact (sha256.txt and weights.pt required)")
    if any(p.is_dir() for p in src.iterdir()):
        raise CorrectionError(f"{src} has subdirectories: not a flat exported artifact (already corrected?)")
    entries = read_digests(src / "sha256.txt")
    listed_weights = dict((n, d) for d, n in entries).get("weights.pt")
    weights_before = sha256_file(src / "weights.pt")
    if not (weights_before == expect_weights == listed_weights):
        raise CorrectionError(f"weights.pt: expected {expect_weights}, file {weights_before}, sha256.txt {listed_weights}")
    bad = _verify_listed(src, entries)
    if bad:
        raise CorrectionError(f"source does not verify against its own sha256.txt: {bad}")

    originals = {p.name: p.read_bytes() for p in src.iterdir() if p.name != "weights.pt"}
    corrected, changes = derive(originals)

    dst.mkdir(parents=True)
    for p in sorted(src.iterdir()):
        shutil.copyfile(p, dst / p.name)                    # weights.pt byte for byte; SRC opened read-only
    (dst / ORIGINALS).mkdir()
    for name in corrected:
        (dst / ORIGINALS / name).write_bytes(originals[name])
        (dst / name).write_bytes(corrected[name])

    weights_src_after, weights_dst = sha256_file(src / "weights.pt"), sha256_file(dst / "weights.pt")
    if not (weights_src_after == weights_dst == expect_weights):
        raise CorrectionError(f"weights.pt changed: source after {weights_src_after}, output {weights_dst}")
    files = {}
    for p in sorted(src.iterdir()):
        before = sha256_bytes(originals[p.name]) if p.name in originals else weights_before
        after = sha256_file(dst / p.name)
        files[p.name] = {"original_sha256": before, "corrected_sha256": after, "changed": before != after}
    record = {
        "correction_id": CORRECTION_ID, "tool": "training/m3_encoder/correct_metadata.py", "tool_version": TOOL_VERSION,
        **_git_state(), "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "artifact_id": json.loads(originals["heads.json"]).get("artifact_id"),
        "reason": "published provenance wording was false for the artifact's own declared evaluation reference "
                  "(heads.json a_evaluation_reference_kind); metadata only, no retraining",
        "evaluation_reference_kind": json.loads(originals["heads.json"]).get("a_evaluation_reference_kind"),
        "weights_sha256": {"expected": expect_weights, "source_before": weights_before,
                           "source_after": weights_src_after, "output": weights_dst},
        "files": files, "changes": changes, "originals_kept_in": f"{ORIGINALS}/",
        "unchanged": ["weights.pt (every tensor)", "dev_eval.json metric blocks and export-time digests",
                      "heads.json heads, history, hyperparameters, split, label digests",
                      "training provenance: the weights were trained on the label files whose digests "
                      "label_sources.a records, at the code the run record names"],
    }
    (dst / RECORD).write_bytes(dump(record))
    problems = verify(dst, expect_weights)
    if problems:
        raise CorrectionError(f"corrected artifact does not verify: {problems}")
    return record


def verify(directory: Path, expect_weights: str) -> list[str]:
    """[] when `directory` is a corrected artifact whose files are exactly what `derive` makes from
    its kept originals, with weights.pt at the expected digest."""
    problems: list[str] = []
    record_path = directory / RECORD
    if not record_path.is_file():
        return [f"no {RECORD}"]
    record = json.loads(record_path.read_text(encoding="utf-8"))
    if sha256_file(directory / "weights.pt") != expect_weights:
        problems.append("weights.pt does not have the expected sha256")
    if set(record["weights_sha256"].values()) != {expect_weights}:
        problems.append(f"record weights digests {record['weights_sha256']} != {expect_weights}")
    problems += _verify_listed(directory, read_digests(directory / "sha256.txt"))
    originals = {p.name: p.read_bytes() for p in (directory / ORIGINALS).iterdir()}
    try:
        derived, _ = derive(originals)
    except CorrectionError as exc:
        return problems + [f"cannot re-derive from {ORIGINALS}/: {exc}"]
    for name, data in derived.items():
        if (directory / name).read_bytes() != data:
            problems.append(f"{name} is not what the correction derives from its original")
    for name, info in record["files"].items():
        kept = directory / ORIGINALS / name
        if kept.is_file() and sha256_file(kept) != info["original_sha256"]:
            problems.append(f"{ORIGINALS}/{name} does not match the recorded original digest")
        if sha256_file(directory / name) != info["corrected_sha256"]:
            problems.append(f"{name} does not match the recorded corrected digest")
        if not info["changed"] and info["original_sha256"] != info["corrected_sha256"]:
            problems.append(f"{name} marked unchanged but its digest changed")
    changed = {n for n, i in record["files"].items() if i["changed"]}
    if not changed <= {"heads.json", "dev_eval.json", "sha256.txt"}:
        problems.append(f"files outside the metadata changed: {sorted(changed)}")
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m training.m3_encoder.correct_metadata",
                                     description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    c = sub.add_parser("correct", help="write a corrected copy of an exported artifact")
    c.add_argument("--artifact", type=Path, required=True)
    c.add_argument("--out", type=Path, required=True)
    c.add_argument("--expect-weights-sha256", required=True)
    v = sub.add_parser("verify", help="check a corrected artifact against its kept originals")
    v.add_argument("--artifact", type=Path, required=True)
    v.add_argument("--expect-weights-sha256", required=True)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.command == "correct":
        try:
            record = correct(args.artifact, args.out, args.expect_weights_sha256)
        except CorrectionError as exc:
            print(f"REFUSED: {exc}")
            return 1
        print(f"corrected copy written to {args.out}")
        for name, info in record["files"].items():
            print(f"  {name:<24} {'CHANGED' if info['changed'] else 'same   '} "
                  f"{info['original_sha256'][:12]} -> {info['corrected_sha256'][:12]}")
        print(f"  weights.pt sha256 {record['weights_sha256']}")
        return 0
    problems = verify(args.artifact, args.expect_weights_sha256)
    print("VERIFIED" if not problems else "NOT VERIFIED")
    for p in problems:
        print(f"  - {p}")
    return 0 if not problems else 1


if __name__ == "__main__":
    raise SystemExit(main())
