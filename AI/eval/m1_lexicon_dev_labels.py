"""m1 lexicon labels on the frozen dev split - runs protocols/m1_lexicon_dev_labels_protocol.md.

Writes, for every dev row, what m1_lexicon publishes at runtime: the three hit flags,
the channel, the matched roots, the span of every match and every substring collision.

Deliberately does NOT:
  * define the evaluation slice. m4's slice is eval/frozen/study_slice_dev.json (karaliste,
    frozen); this file is regenerable data for m3's A head and for comparison (protocol §1)
  * write gold. Join on row_id; gold is read only for the integrity count
  * call private m1 functions. Everything comes from m1's published signals, scores, guards
  * report metrics. Recall / precision / FPR are computed from this file, elsewhere
  * open the official test set

    python -m eval.m1_lexicon_dev_labels --out eval/derived/m1_lexicon_dev_seed42.json
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.codes import GuardCode
from contracts.module_api import NORMALIZED, RAW
from modules import registry
from pipeline.run import Pipeline

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
PROTOCOL = "protocols/m1_lexicon_dev_labels_protocol.md"
SOURCE = "m1_lexicon"

INPUTS = {
    "corpus": (REPO_ROOT / "diagnosis/data/coltekin/offenseval-tr-training-v1.tsv",
               "8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa"),
    "dev_split": (REPO_ROOT / "diagnosis/data/splits/split_seed42.json",
                  "73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2"),
    "frozen_slice": (AI_ROOT / "eval/frozen/study_slice_dev.json",
                     "94754632fb66d543b7c1e84bc4e396b65585f8adba90a4f2fc87aca8f2acbed8"),
}

# Integrity checks, protocol §3.
EXPECTED: dict[str, Any] = {
    "seed": 42, "n_dev": 4764, "off": 920, "not": 3844,
    "dev_fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4",
}

LEXICON_MODULES = ("m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon")
WATCHED_PATHS = ("modules/m0_charsafe", "modules/m1_lexicon", "modules/m2_deobf", "modules/m6_target",
                 "modules/registry.py", "pipeline", "eval/m1_lexicon_dev_labels.py")

README = (
    "REGENERABLE, not frozen. What m1_lexicon (terlik balanced) publishes on every row of the frozen "
    "dev split (seed 42), in dev_ids order. Purposes: training labels for m3's A head, and comparison "
    "against eval/frozen/study_slice_dev.json. This file is NOT the evaluation slice: m4's "
    "lexicon_hit / lexicon_free slice stays eval/frozen/study_slice_dev.json (karaliste), and the two "
    "files are never merged. Normalized channel: m2 is a stub and publishes no normalized text, so m1 "
    "does not scan that channel; lexicon_hit_norm is false by absence, not by measurement. "
    "Regenerate with protocols/m1_lexicon_dev_labels_protocol.md §7; never edit by hand."
)

LIMITS = [
    "Gold is binary OFF/NOT: any rate computed from this file measures lexicon hits against OFF, "
    "never per content code (the corpus has no A codes).",
    "The raw channel is m0's charsafe text, not the untouched original; spans are original offsets.",
    "The normalized channel is absent while m2 is a stub; no metric may be reported for it.",
    "roots is m1's matched_roots for the whole post (both channels); m1 publishes no root per span.",
    "terlik is not karaliste: a difference against the frozen study slice is a word-list difference; a "
    "difference against the study's 36.5% (karaliste, full corpus) also mixes in a population difference.",
    "No A4 (sacred-concept) coverage and no HOMONYM guard yet (m1 spec §4.3, §8).",
]


class ProtocolStop(Exception):
    """An integrity check failed: the protocol says stop, write nothing."""


def require(ok: bool, what: str) -> None:
    if not ok:
        raise ProtocolStop(what)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(AI_ROOT), *args], capture_output=True, text=True)


# -- data -------------------------------------------------------------------
def read_corpus(path: Path) -> dict[str, tuple[str, str]]:
    """id -> (text, label), parsed as diagnosis/src/data_io.py does: id first, label last,
    the middle fields joined with tabs."""
    rows: dict[str, tuple[str, str]] = {}
    with open(path, encoding="utf-8") as f:
        f.readline()
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            parts = line.split("\t")
            require(len(parts) >= 3, f"corpus line with {len(parts)} field(s): {line[:60]!r}")
            require(parts[0] not in rows, f"duplicate corpus id {parts[0]}")
            rows[parts[0]] = ("\t".join(parts[1:-1]), parts[-1].strip())
    return rows


def load_inputs() -> tuple[list[str], dict[str, tuple[str, str]], dict[str, Any]]:
    hashes = {}
    for key, (path, want) in INPUTS.items():
        got = sha256_file(path)
        require(got == want, f"sha256 mismatch for {path}: {got}")
        hashes[key] = {"file": path.relative_to(REPO_ROOT).as_posix(), "sha256": got}

    split = json.loads(INPUTS["dev_split"][0].read_text(encoding="utf-8"))
    dev_ids = [str(i) for i in split["dev_ids"]]
    require(split["seed"] == EXPECTED["seed"], f"split seed {split['seed']}")
    require(len(dev_ids) == EXPECTED["n_dev"] and len(set(dev_ids)) == len(dev_ids), "dev_ids count / unique")
    fingerprint = hashlib.sha256("\n".join(sorted(dev_ids)).encode("utf-8")).hexdigest()
    require(fingerprint == EXPECTED["dev_fingerprint"] == split["dev_fingerprint"], "dev fingerprint")

    corpus = read_corpus(INPUTS["corpus"][0])
    missing = [i for i in dev_ids if i not in corpus]
    require(not missing, f"{len(missing)} dev ids not in the corpus")
    labels = [corpus[i][1] for i in dev_ids]
    require(labels.count("OFF") == EXPECTED["off"] and labels.count("NOT") == EXPECTED["not"],
            "dev OFF/NOT counts")

    frozen = json.loads(INPUTS["frozen_slice"][0].read_text(encoding="utf-8"))
    require(frozen["split"]["dev_fingerprint"] == EXPECTED["dev_fingerprint"], "frozen slice fingerprint")
    require({row[0] for row in frozen["rows"]} == set(dev_ids), "frozen slice row ids == dev ids")
    return dev_ids, corpus, hashes


# -- labelling ----------------------------------------------------------------
def channel_of(raw: bool, norm: bool) -> str:
    return {(True, True): "both", (True, False): RAW, (False, True): NORMALIZED, (False, False): "none"}[(raw, norm)]


def label_row(pipeline: Pipeline, row_id: str, text: str) -> dict[str, Any]:
    result = pipeline.analyze(text)
    degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
    require(SOURCE not in degraded, f"row {row_id}: m1_lexicon degraded: {degraded.get(SOURCE)}")
    signals = result.signals.get(SOURCE, {})
    flags = {key: signals.get(key) for key in ("lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm")}
    require(all(isinstance(v, bool) for v in flags.values()), f"row {row_id}: non-bool flag {flags}")
    require(flags["lexicon_hit"] == (flags["lexicon_hit_raw"] or flags["lexicon_hit_norm"]),
            f"row {row_id}: lexicon_hit is not raw OR norm {flags}")

    matches = []
    for score in result.content:
        if not score.source.startswith(f"{SOURCE}@"):
            continue
        channel = score.source.split("@", 1)[1]
        require(channel in (RAW, NORMALIZED), f"row {row_id}: unknown channel in {score.source}")
        require(score.span is not None, f"row {row_id}: m1 score without span")
        start, end = score.span
        matches.append({"channel": channel, "start": start, "end": end, "surface": text[start:end]})
    matches.sort(key=lambda m: (m["start"], m["end"], m["channel"]))

    m1_notes = [n for n in result.notes if n.startswith(f"[{SOURCE}] ")]
    for channel, key in ((RAW, "lexicon_hit_raw"), (NORMALIZED, "lexicon_hit_norm")):
        scored = any(m["channel"] == channel for m in matches)
        spanless = any(n.startswith(f"[{SOURCE}] {channel}: ") for n in m1_notes)
        require(flags[key] == (scored or spanless), f"row {row_id}: {key}={flags[key]} but scores/notes disagree")

    collisions = []
    for guard in result.guards:
        if guard.code is GuardCode.SUBSTRING_COLLISION and guard.source == SOURCE:
            require(guard.span is not None, f"row {row_id}: collision guard without span")
            start, end = guard.span
            collisions.append({"start": start, "end": end, "surface": text[start:end], "evidence": guard.evidence})
    collisions.sort(key=lambda c: (c["start"], c["end"]))

    return {
        "row_id": row_id,
        **flags,
        "channel": channel_of(flags["lexicon_hit_raw"], flags["lexicon_hit_norm"]),
        "roots": sorted(signals.get("matched_roots", [])),
        "matches": matches,
        "collisions": collisions,
    }


def serialise_rows(rows: list[dict[str, Any]]) -> str:
    return ",\n".join("    " + json.dumps(row, ensure_ascii=False, sort_keys=False) for row in rows)


def build_rows(dev_ids: list[str], corpus: dict[str, tuple[str, str]]) -> tuple[str, list[dict[str, Any]], dict]:
    names = [e.name.value for e in registry.PIPELINE_ORDER if e.name.value in LEXICON_MODULES]
    pipeline = Pipeline(modules=[registry.build(n) for n in names])
    versions = {m.name.value: m.version for m in pipeline.modules}
    rows = [label_row(pipeline, row_id, corpus[row_id][0]) for row_id in dev_ids]
    engine = pipeline.analyze("").signals[SOURCE]["engine"]
    return serialise_rows(rows), rows, {"modules_in_order": names, "versions": versions, "engine": engine}


# -- provenance ---------------------------------------------------------------
def provenance() -> dict[str, Any]:
    protocol_path = AI_ROOT / PROTOCOL
    require(protocol_path.exists(), f"{PROTOCOL} does not exist - the protocol comes before the file")
    commit = git("log", "-1", "--format=%H", "--", PROTOCOL).stdout.strip() or None
    protocol_clean = commit is not None and git("diff", "--quiet", "HEAD", "--", PROTOCOL).returncode == 0
    dirty = git("status", "--porcelain", "--", *WATCHED_PATHS).stdout.splitlines()
    return {
        "protocol": {"file": f"AI/{PROTOCOL}", "sha256": sha256_file(protocol_path),
                     "commit": commit, "committed_and_unchanged": protocol_clean},
        "generator": {"script": "AI/eval/m1_lexicon_dev_labels.py",
                      "git_head": git("rev-parse", "HEAD").stdout.strip() or None,
                      "uncommitted_changes": [line[3:] for line in dirty]},
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--spot-check", type=int, default=20, help="hits and collisions printed for review")
    args = parser.parse_args(argv)
    # The spot-check prints Turkish surfaces; a cp1252 console (Windows default) would
    # raise after the file is written and mask a successful run as a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    try:
        meta = provenance()
        dev_ids, corpus, hashes = load_inputs()
        block, rows, run = build_rows(dev_ids, corpus)
        second, _, _ = build_rows(dev_ids, corpus)
        require(block == second, "two generations of the rows differ - not deterministic")
    except ProtocolStop as exc:
        print(f"PROTOCOL STOP: {exc}", file=sys.stderr)
        return 2

    n_hit = sum(r["lexicon_hit"] for r in rows)
    header = {
        "_README": README,
        **meta,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": {
            "m1_engine_signal": run["engine"],
            "terlik": importlib.metadata.version("terlik"),
            "modules_in_order": run["modules_in_order"],
            "module_versions": run["versions"],
        },
        "inputs": hashes,
        "split": {"seed": EXPECTED["seed"], "dev_fingerprint": EXPECTED["dev_fingerprint"], "n": len(rows)},
        "channels": {
            RAW: {"available": True, "text": "m0_charsafe charsafe_text (original if m0 publishes none)"},
            NORMALIZED: {"available": False,
                         "text": "m2_deobf normalized_text; m2 is a stub and publishes none, so m1 does not scan "
                                 "this channel and lexicon_hit_norm is false by absence"},
        },
        "counts": {
            "n": len(rows), "lexicon_hit": n_hit, "lexicon_free": len(rows) - n_hit,
            "lexicon_hit_raw": sum(r["lexicon_hit_raw"] for r in rows),
            "lexicon_hit_norm": sum(r["lexicon_hit_norm"] for r in rows),
            "rows_with_collision": sum(bool(r["collisions"]) for r in rows),
        },
        "rows_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
        "limits": LIMITS,
        "row_fields": ["row_id", "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "channel", "roots",
                       "matches[channel,start,end,surface]", "collisions[start,end,surface,evidence]"],
    }
    head = json.dumps(header, ensure_ascii=False, indent=2)
    text = head[:-2] + ',\n  "rows": [\n' + block + "\n  ]\n}\n"
    if json.loads(text)["rows"] != rows:
        print("PROTOCOL STOP: serialised file does not round-trip", file=sys.stderr)
        return 2

    out = args.out if args.out.is_absolute() else AI_ROOT / args.out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    print(f"wrote {out.relative_to(AI_ROOT).as_posix()}  rows={len(rows)}  rows_sha256={header['rows_sha256']}")
    print(f"counts {json.dumps(header['counts'])}")
    if not meta["protocol"]["committed_and_unchanged"]:
        print("NOTE: protocol not committed (or changed since): commit it before committing this file")
    if meta["generator"]["uncommitted_changes"]:
        print(f"NOTE: uncommitted changes in watched paths: {meta['generator']['uncommitted_changes']}")
    hits = [r for r in rows if r["lexicon_hit"]][:args.spot_check]
    cols = [r for r in rows if r["collisions"]][:args.spot_check]
    print(f"\nspot-check: first {len(hits)} hits (row_id | roots | surfaces)")
    for r in hits:
        print(f"  {r['row_id']:>6} | {','.join(r['roots'])} | {' / '.join(m['surface'] for m in r['matches'])}")
    print(f"\nspot-check: first {len(cols)} collisions (row_id | surface | evidence)")
    for r in cols:
        for c in r["collisions"]:
            print(f"  {r['row_id']:>6} | {c['surface']} | {c['evidence']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
