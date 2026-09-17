"""m1 lexicon labels on one half of the frozen split (seed 42) - runs
protocols/m1_lexicon_dev_labels_protocol.md (--split dev) or
protocols/m1_lexicon_train_labels_protocol.md (--split train).

Writes, for every row of the chosen split, what m1_lexicon publishes at runtime through the
current m0 -> m2 -> m6 -> m1 path: the three hit flags, the channel, the matched roots, the span
of every match, every substring collision, every HOMONYM guard, and the A-head pseudo-label
`a_label` (train protocol §5: raw hit OR a normalized hit with a valid span).

Deliberately does NOT:
  * define the evaluation slice (m4's slice is eval/frozen/study_slice_dev.json, frozen)
  * write gold: join on row_id; gold is read only for the integrity counts
  * call private m1 functions: everything comes from m1's published signals, scores, guards
  * mix the halves: one split per file, and the train run never labels a dev row
  * open the official test set: only the training corpus and the committed split are read, no
    path containing "testset" or "labela" is accepted, every row id is a corpus id
  * report metrics: recall / precision / FPR are computed from these files elsewhere

    python -m eval.m1_lexicon_labels --split train --out eval/derived/m1_lexicon_train_seed42.json
    python -m eval.m1_lexicon_labels --split dev   --out eval/derived/m1_lexicon_dev_seed42.json
    python -m eval.m1_lexicon_labels --check eval/derived/m1_lexicon_train_seed42.json   # stale?
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from contracts.codes import GuardCode
from contracts.module_api import NORMALIZED, RAW
from modules import registry
from pipeline.run import Pipeline

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
SOURCE = "m1_lexicon"
GENERATOR = "AI/eval/m1_lexicon_labels.py"
# Bump on any change to the row schema, the a_label rule, or what the header records.
GENERATOR_VERSION = "2.0.0"

PROTOCOLS = {
    "dev": "protocols/m1_lexicon_dev_labels_protocol.md",
    "train": "protocols/m1_lexicon_train_labels_protocol.md",
}
CORPUS_SHA256 = "8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa"
SPLIT_SHA256 = "73a323b9e5750faecd557470bb53e27fe26b7fdf7a1ad9da1d365f224dc6d7f2"
FROZEN_SLICE_SHA256 = "94754632fb66d543b7c1e84bc4e396b65585f8adba90a4f2fc87aca8f2acbed8"

# Names that identify the official test set and its gold (RESOURCES.md: LOCKED, never touched).
# No input path may contain them; the generator never constructs such a path.
FORBIDDEN_INPUT_NAMES = ("testset", "labela")

LEXICON_MODULES = ("m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon")
WATCHED_PATHS = ("modules/m0_charsafe", "modules/m1_lexicon", "modules/m2_deobf", "modules/m6_target",
                 "modules/registry.py", "pipeline", "contracts", "eval/m1_lexicon_labels.py")

ROW_FIELDS = ["row_id", "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "channel", "a_label", "roots",
              "matches[channel,start,end,surface]", "collisions[start,end,surface,evidence]",
              "homonyms[start,end,surface,evidence]"]

README = {
    "dev": (
        "REGENERABLE, not frozen. What m1_lexicon (terlik balanced) publishes on every row of the frozen "
        "DEV split (seed 42), in dev_ids order, through the implemented m0 -> m2 -> m6 -> m1 path, plus the "
        "A-head pseudo-label a_label (protocols/m1_lexicon_train_labels_protocol.md §5). Purposes: "
        "pseudo-label AGREEMENT for m3's A head (never its evaluation: the oracle is the human-labelled dev "
        "subset, docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md) and comparison against "
        "eval/frozen/study_slice_dev.json. This file is NOT the evaluation slice: m4's lexicon_hit / "
        "lexicon_free slice stays eval/frozen/study_slice_dev.json (karaliste), and the two files are never "
        "merged. Regenerate with protocols/m1_lexicon_dev_labels_protocol.md §7; never edit by hand."
    ),
    "train": (
        "REGENERABLE, not frozen. What m1_lexicon (terlik balanced) publishes on every row of the frozen "
        "TRAIN split (seed 42), in train_ids order, through the implemented m0 -> m2 -> m6 -> m1 path, plus "
        "the A-head pseudo-label a_label (protocols/m1_lexicon_train_labels_protocol.md §5). Purpose: "
        "training supervision for m3's A head - a KEYWORD pseudo-label, never an evaluation oracle (the "
        "oracle is the human-labelled dev subset, docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md). No dev "
        "row is in this file. Regenerate with the train protocol §9; never edit by hand."
    ),
}

LIMITS = [
    "Gold is binary OFF/NOT: any rate computed from this file measures lexicon hits against OFF, never "
    "'profanity present' against a human judgement (the corpus has no A codes).",
    "a_label is a keyword pseudo-label (terlik balanced, both channels): an A head trained on it learns "
    "terlik's coverage; its quality is known only against the human-labelled dev subset.",
    "The raw channel is m0's charsafe text, not the untouched original; spans are original offsets.",
    "The normalized channel is m2's parallel channel (tier 1 + zeyrek-validated tier 2) mapped through "
    "m2's _offsets (ADR-008); a normalized-only hit without a valid span is labelled 0 and counted.",
    "roots is m1's matched_roots for the whole post (both channels); m1 publishes no root per span.",
    "terlik is not karaliste: a difference against the frozen study slice is a word-list difference; a "
    "difference against the study's 36.5% (karaliste, full corpus) also mixes in a population difference.",
    "No A4 (sacred-concept) coverage (m1 spec §4.3); HOMONYM guards are recorded, not applied to a_label.",
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


def fingerprint(ids: list[str]) -> str:
    """The study's split fingerprint: sha256 over the sorted ids joined with newlines."""
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(AI_ROOT), *args], capture_output=True, text=True)


def installed_version(dist: str) -> str | None:
    try:
        return importlib.metadata.version(dist)
    except importlib.metadata.PackageNotFoundError:
        return None


# -- inputs -------------------------------------------------------------------
@dataclass(frozen=True)
class Spec:
    """What one run reads and expects. The defaults are the project's; tests build their own."""
    split: str
    corpus: Path = REPO_ROOT / "diagnosis/data/coltekin/offenseval-tr-training-v1.tsv"
    corpus_sha256: str = CORPUS_SHA256
    split_file: Path = REPO_ROOT / "diagnosis/data/splits/split_seed42.json"
    split_sha256: str = SPLIT_SHA256
    frozen_slice: Path | None = AI_ROOT / "eval/frozen/study_slice_dev.json"      # dev cross-check only
    frozen_slice_sha256: str | None = FROZEN_SLICE_SHA256
    seed: int = 42
    # Per split: row count, gold counts and the pinned fingerprint (protocol §3).
    expected: dict[str, dict[str, Any]] = field(default_factory=lambda: {
        "dev": {"n": 4764, "OFF": 920, "NOT": 3844,
                "fingerprint": "034415af3a23b388cb2bfbb13fc5eda37e43f71a3542e9ea925de72e06a133b4"},
        "train": {"n": 26992, "OFF": 5211, "NOT": 21781,
                  "fingerprint": "29a2ea8bdc9730bf7a16f6c7e21d69dd3f33648b923f2829e8e2797876bbe931"},
    })

    def protocol(self) -> str:
        return PROTOCOLS[self.split]


def refuse_test_set(*paths: Path | None) -> None:
    for path in paths:
        if path is None:
            continue
        low = str(path).lower()
        require(not any(name in low for name in FORBIDDEN_INPUT_NAMES),
                f"refusing input {path}: the official test set / gold is locked and never read")


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


def load_inputs(spec: Spec) -> tuple[list[str], dict[str, tuple[str, str]], dict[str, Any]]:
    """The ids of the chosen split (in split order), the corpus, and the input digests.
    Every protocol §3 check that does not need the pipeline runs here."""
    require(spec.split in PROTOCOLS, f"unknown split {spec.split!r}")
    refuse_test_set(spec.corpus, spec.split_file, spec.frozen_slice)
    hashes: dict[str, Any] = {}
    for key, path, want in (("corpus", spec.corpus, spec.corpus_sha256), ("split", spec.split_file, spec.split_sha256)):
        require(path.is_file(), f"missing input {path}")
        got = sha256_file(path)
        require(got == want, f"sha256 mismatch for {path}: {got}")
        hashes[key] = {"file": _display(path), "sha256": got}

    split = json.loads(spec.split_file.read_text(encoding="utf-8"))
    require(split.get("seed") == spec.seed, f"split seed {split.get('seed')}")
    train_ids = [str(i) for i in split["train_ids"]]
    dev_ids = [str(i) for i in split["dev_ids"]]
    exp = spec.expected
    require(len(train_ids) == exp["train"]["n"] and len(set(train_ids)) == len(train_ids), "train_ids count / unique")
    require(len(dev_ids) == exp["dev"]["n"] and len(set(dev_ids)) == len(dev_ids), "dev_ids count / unique")
    require(not set(train_ids) & set(dev_ids), "train_ids and dev_ids overlap")
    require(fingerprint(dev_ids) == exp["dev"]["fingerprint"] == split.get("dev_fingerprint"), "dev fingerprint")
    require(fingerprint(train_ids) == exp["train"]["fingerprint"], "train fingerprint")
    ids = train_ids if spec.split == "train" else dev_ids

    corpus = read_corpus(spec.corpus)
    missing = [i for i in ids if i not in corpus]
    require(not missing, f"{len(missing)} {spec.split} ids not in the corpus")
    labels = [corpus[i][1] for i in ids]
    require(labels.count("OFF") == exp[spec.split]["OFF"] and labels.count("NOT") == exp[spec.split]["NOT"],
            f"{spec.split} OFF/NOT counts")

    if spec.split == "dev" and spec.frozen_slice is not None:
        require(spec.frozen_slice.is_file(), f"missing frozen slice {spec.frozen_slice}")
        got = sha256_file(spec.frozen_slice)
        require(got == spec.frozen_slice_sha256, f"sha256 mismatch for {spec.frozen_slice}: {got}")
        hashes["frozen_slice"] = {"file": _display(spec.frozen_slice), "sha256": got}
        frozen = json.loads(spec.frozen_slice.read_text(encoding="utf-8"))
        require(frozen["split"]["dev_fingerprint"] == exp["dev"]["fingerprint"], "frozen slice fingerprint")
        require({str(row[0]) for row in frozen["rows"]} == set(ids), "frozen slice row ids == dev ids")
    return ids, corpus, hashes


def _display(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    except ValueError:
        return path.name


# -- labelling ----------------------------------------------------------------
def channel_of(raw: bool, norm: bool) -> str:
    return {(True, True): "both", (True, False): RAW, (False, True): NORMALIZED, (False, False): "none"}[(raw, norm)]


def a_label_of(raw: bool, norm: bool, matches: list[dict[str, Any]]) -> int:
    """Train protocol §5: raw hit, or a normalized hit that m1 mapped back to the original text."""
    spanned_norm = any(m["channel"] == NORMALIZED for m in matches)
    return int(raw or (norm and spanned_norm))


def label_row(pipeline: Pipeline, row_id: str, text: str) -> dict[str, Any]:
    result = pipeline.analyze(text)
    degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
    require(SOURCE not in degraded, f"row {row_id}: m1_lexicon degraded: {degraded.get(SOURCE)}")
    signals = result.signals.get(SOURCE, {})
    flags = {key: signals.get(key) for key in ("lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm")}
    require(all(isinstance(v, bool) for v in flags.values()), f"row {row_id}: non-bool flag {flags}")
    require(flags["lexicon_hit"] == (flags["lexicon_hit_raw"] or flags["lexicon_hit_norm"]),
            f"row {row_id}: lexicon_hit is not raw OR norm {flags}")

    # Per-channel scores are read from the decision layer's PRE-FUSION record: `result.content`
    # is fused (one entry per code and span, max over channels), so an identical normalized
    # channel would vanish from it while `channel_scores` keeps every source.
    matches = []
    for score in result.signals.get("decision", {}).get("channel_scores", []):
        source = str(score.get("source", ""))
        if not source.startswith(f"{SOURCE}@"):
            continue
        channel = source.split("@", 1)[1]
        require(channel in (RAW, NORMALIZED), f"row {row_id}: unknown channel in {source}")
        require(score.get("span") is not None, f"row {row_id}: m1 score without span")
        start, end = (int(v) for v in score["span"])
        require(0 <= start < end <= len(text), f"row {row_id}: span {score['span']} outside the text")
        matches.append({"channel": channel, "start": start, "end": end, "surface": text[start:end]})
    matches.sort(key=lambda m: (m["start"], m["end"], m["channel"]))

    m1_notes = [n for n in result.notes if n.startswith(f"[{SOURCE}] ")]
    for channel, key in ((RAW, "lexicon_hit_raw"), (NORMALIZED, "lexicon_hit_norm")):
        scored = any(m["channel"] == channel for m in matches)
        spanless = any(n.startswith(f"[{SOURCE}] {channel}: ") for n in m1_notes)
        require(flags[key] == (scored or spanless), f"row {row_id}: {key}={flags[key]} but scores/notes disagree")

    def spanned(code: GuardCode) -> list[dict[str, Any]]:
        items = []
        for guard in result.guards:
            if guard.code is code and guard.source == SOURCE:
                require(guard.span is not None, f"row {row_id}: {code.value} guard without span")
                start, end = guard.span
                require(0 <= start < end <= len(text), f"row {row_id}: guard span {guard.span} outside the text")
                item = {"start": start, "end": end, "surface": text[start:end], "evidence": guard.evidence}
                if item not in items:      # m1 raises one guard per channel score; the same span once
                    items.append(item)
        return sorted(items, key=lambda c: (c["start"], c["end"]))

    return {
        "row_id": row_id,
        **flags,
        "channel": channel_of(flags["lexicon_hit_raw"], flags["lexicon_hit_norm"]),
        "a_label": a_label_of(flags["lexicon_hit_raw"], flags["lexicon_hit_norm"], matches),
        "roots": sorted(signals.get("matched_roots", [])),
        "matches": matches,
        "collisions": spanned(GuardCode.SUBSTRING_COLLISION),
        "homonyms": spanned(GuardCode.HOMONYM),
    }


def serialise_rows(rows: list[dict[str, Any]]) -> str:
    return ",\n".join("    " + json.dumps(row, ensure_ascii=False, sort_keys=False) for row in rows)


def build_pipeline(modules: list[Any] | None = None) -> Pipeline:
    """The runtime path of the lexicon signal: the registry's order restricted to the lexicon
    modules. Tests may inject their own module instances (same order)."""
    if modules is None:
        names = [e.name.value for e in registry.PIPELINE_ORDER if e.name.value in LEXICON_MODULES]
        modules = [registry.build(n) for n in names]
    return Pipeline(modules=modules)


def engine_record(pipeline: Pipeline) -> dict[str, Any]:
    m2 = next((m for m in pipeline.modules if m.name.value == "m2_deobf"), None)
    tier2 = bool(getattr(m2, "tier2_enabled", False))
    return {
        "m1_engine_signal": pipeline.analyze("").signals[SOURCE]["engine"],
        "terlik": installed_version("terlik"),
        "zeyrek": installed_version("zeyrek"),
        "m2_tier2_enabled": tier2,
        "modules_in_order": [m.name.value for m in pipeline.modules],
        "module_versions": {m.name.value: m.version for m in pipeline.modules},
    }


def build_rows(ids: list[str], corpus: dict[str, tuple[str, str]], pipeline: Pipeline) -> tuple[str, list[dict[str, Any]]]:
    rows = [label_row(pipeline, row_id, corpus[row_id][0]) for row_id in ids]
    return serialise_rows(rows), rows


def counts_of(rows: list[dict[str, Any]]) -> dict[str, int]:
    n_hit = sum(r["lexicon_hit"] for r in rows)
    return {
        "n": len(rows), "lexicon_hit": n_hit, "lexicon_free": len(rows) - n_hit,
        "lexicon_hit_raw": sum(r["lexicon_hit_raw"] for r in rows),
        "lexicon_hit_norm": sum(r["lexicon_hit_norm"] for r in rows),
        "raw_only": sum(r["channel"] == RAW for r in rows),
        "normalized_only": sum(r["channel"] == NORMALIZED for r in rows),
        "both": sum(r["channel"] == "both" for r in rows),
        "a_label": sum(r["a_label"] for r in rows),
        "norm_hit_unmapped": sum(1 for r in rows if r["lexicon_hit_norm"]
                                 and not any(m["channel"] == NORMALIZED for m in r["matches"])),
        "rows_with_collision": sum(bool(r["collisions"]) for r in rows),
        "rows_with_homonym": sum(bool(r["homonyms"]) for r in rows),
        "rows_all_matches_homonym": sum(
            1 for r in rows if r["matches"]
            and all(any(h["start"] <= m["start"] and m["end"] <= h["end"] for h in r["homonyms"]) for m in r["matches"])),
    }


# -- provenance ---------------------------------------------------------------
def provenance(spec: Spec) -> dict[str, Any]:
    protocol_rel = spec.protocol()
    protocol_path = AI_ROOT / protocol_rel
    require(protocol_path.exists(), f"{protocol_rel} does not exist - the protocol comes before the file")
    commit = git("log", "-1", "--format=%H", "--", protocol_rel).stdout.strip() or None
    protocol_clean = commit is not None and git("diff", "--quiet", "HEAD", "--", protocol_rel).returncode == 0
    dirty = git("status", "--porcelain", "--", *WATCHED_PATHS).stdout.splitlines()
    return {
        "protocol": {"file": f"AI/{protocol_rel}", "sha256": sha256_file(protocol_path),
                     "commit": commit, "committed_and_unchanged": protocol_clean},
        "generator": {"script": GENERATOR, "version": GENERATOR_VERSION,
                      "git_head": git("rev-parse", "HEAD").stdout.strip() or None,
                      "uncommitted_changes": [line[3:] for line in dirty],
                      "python": platform.python_version()},
    }


def build_header(spec: Spec, meta: dict[str, Any], engine: dict[str, Any], hashes: dict[str, Any],
                 rows: list[dict[str, Any]], block: str) -> dict[str, Any]:
    return {
        "_README": README[spec.split],
        **meta,
        "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "engine": engine,
        "inputs": hashes,
        "split": {"name": spec.split, "seed": spec.seed, "n": len(rows),
                  "fingerprint": spec.expected[spec.split]["fingerprint"],
                  "dev_fingerprint": spec.expected["dev"]["fingerprint"]},
        "channels": {
            RAW: {"available": True, "text": "m0_charsafe charsafe_text (original if m0 publishes none)"},
            NORMALIZED: {"available": engine["m2_tier2_enabled"],
                         "text": "m2_deobf normalized_text (tier 1 + zeyrek-validated tier 2), spans mapped "
                                 "through m2's _offsets (ADR-008)"},
        },
        "a_label_rule": "lexicon_hit_raw OR (lexicon_hit_norm AND a normalized-channel match with a valid span) "
                        "- protocols/m1_lexicon_train_labels_protocol.md §5 (owner decision 2026-09-18)",
        "counts": counts_of(rows),
        "rows_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
        "limits": LIMITS,
        "row_fields": ROW_FIELDS,
    }


def render(header: dict[str, Any], block: str) -> str:
    head = json.dumps(header, ensure_ascii=False, indent=2)
    return head[:-2] + ',\n  "rows": [\n' + block + "\n  ]\n}\n"


# -- staleness ----------------------------------------------------------------
def check_file(path: Path, spec: Spec | None = None) -> list[str]:
    """Everything that can be verified WITHOUT the corpus: protocol digest, generator version,
    installed engine versions, module versions of the registry classes, the split's ids and
    digest, the rows digest. Returns the problems (empty = current). The corpus digest is checked
    only when the corpus is on the machine."""
    problems: list[str] = []
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    split_name = data.get("split", {}).get("name")
    if split_name not in PROTOCOLS:
        return [f"header split.name {split_name!r} is not dev/train (pre-2.0 file?)"]
    spec = spec or Spec(split=split_name)
    if spec.split != split_name:
        problems.append(f"file is a {split_name} file, checked against a {spec.split} spec")

    protocol_path = AI_ROOT / spec.protocol()
    if not protocol_path.exists():
        problems.append(f"protocol missing: {spec.protocol()}")
    elif data.get("protocol", {}).get("sha256") != sha256_file(protocol_path):
        problems.append("protocol sha256 differs from the protocol on disk")
    if data.get("generator", {}).get("version") != GENERATOR_VERSION:
        problems.append(f"generator version {data.get('generator', {}).get('version')} != {GENERATOR_VERSION}")

    engine = data.get("engine", {})
    for dist in ("terlik", "zeyrek"):
        if engine.get(dist) != installed_version(dist):
            problems.append(f"{dist} {engine.get(dist)} in file, {installed_version(dist)} installed")
    current_versions = {e.name.value: registry.load_class(e).version for e in registry.PIPELINE_ORDER
                        if e.name.value in LEXICON_MODULES}
    if engine.get("module_versions") != current_versions:
        problems.append(f"module versions {engine.get('module_versions')} != current {current_versions}")
    if engine.get("modules_in_order") != list(current_versions):
        problems.append(f"module order {engine.get('modules_in_order')} != registry {list(current_versions)}")

    inputs = data.get("inputs", {})
    for key, file, want in (("corpus", spec.corpus, spec.corpus_sha256), ("split", spec.split_file, spec.split_sha256)):
        recorded = inputs.get(key, {}).get("sha256")
        if recorded != want:
            problems.append(f"input {key} sha256 {recorded} != pinned {want}")
        if file.is_file() and sha256_file(file) != want:
            problems.append(f"input {key} on disk differs from the pinned sha256")

    rows = data.get("rows", [])
    if hashlib.sha256(serialise_rows(rows).encode("utf-8")).hexdigest() != data.get("rows_sha256"):
        problems.append("rows_sha256 does not match the rows")
    if spec.split_file.is_file():
        split = json.loads(spec.split_file.read_text(encoding="utf-8"))
        ids = [str(i) for i in split[f"{split_name}_ids"]]
        if [r.get("row_id") for r in rows] != ids:
            problems.append(f"row ids are not the split's {split_name}_ids in order")
    expected_fields = {"row_id", "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "channel", "a_label", "roots",
                       "matches", "collisions", "homonyms"}
    if rows and set(rows[0]) != expected_fields:
        problems.append(f"row fields {sorted(rows[0])} != {sorted(expected_fields)}")
    if data.get("counts") != counts_of(rows):
        problems.append("header counts do not match the rows")
    return problems


# -- entry point --------------------------------------------------------------
def generate(spec: Spec, out: Path, pipeline: Pipeline | None = None, spot_check: int = 20) -> int:
    try:
        meta = provenance(spec)
        ids, corpus, hashes = load_inputs(spec)
        pipeline = pipeline or build_pipeline()
        engine = engine_record(pipeline)
        require(engine["m2_tier2_enabled"], "m2 tier 2 (zeyrek) unavailable: the normalized channel would be "
                                            "silently different; install modules/m2_deobf/requirements.txt")
        block, rows = build_rows(ids, corpus, pipeline)
        second, _ = build_rows(ids, corpus, pipeline)
        require(block == second, "two generations of the rows differ - not deterministic")
        header = build_header(spec, meta, engine, hashes, rows, block)
        text = render(header, block)
        require(json.loads(text)["rows"] == rows, "serialised file does not round-trip")
    except ProtocolStop as exc:
        print(f"PROTOCOL STOP: {exc}", file=sys.stderr)
        return 2

    out = out if out.is_absolute() else AI_ROOT / out
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)

    print(f"wrote {_display(out)}  split={spec.split}  rows={len(rows)}  rows_sha256={header['rows_sha256']}")
    print(f"counts {json.dumps(header['counts'])}")
    if not meta["protocol"]["committed_and_unchanged"]:
        print("NOTE: protocol not committed (or changed since): commit it before committing this file")
    if meta["generator"]["uncommitted_changes"]:
        print(f"NOTE: uncommitted changes in watched paths: {meta['generator']['uncommitted_changes']}")
    hits = [r for r in rows if r["lexicon_hit"]][:spot_check]
    norm_only = [r for r in rows if r["channel"] == NORMALIZED][:spot_check]
    print(f"\nspot-check: first {len(hits)} hits (row_id | channel | roots | surfaces)")
    for r in hits:
        print(f"  {r['row_id']:>6} | {r['channel']:<10} | {','.join(r['roots'])} | "
              f"{' / '.join(m['surface'] for m in r['matches'])}")
    print(f"\nspot-check: first {len(norm_only)} normalized-only hits (row_id | roots | surfaces)")
    for r in norm_only:
        print(f"  {r['row_id']:>6} | {','.join(r['roots'])} | {' / '.join(m['surface'] for m in r['matches'])}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--split", choices=sorted(PROTOCOLS))
    parser.add_argument("--out", type=Path)
    parser.add_argument("--check", type=Path, help="report whether an existing derived file is stale (exit 1)")
    parser.add_argument("--spot-check", type=int, default=20, help="hits printed for review")
    args = parser.parse_args(argv)
    # Spot-checks print Turkish surfaces; a cp1252 console (Windows default) would raise after
    # the file is written and mask a successful run as a failure.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    if args.check:
        path = args.check if args.check.is_absolute() else AI_ROOT / args.check
        problems = check_file(path)
        print(f"{_display(path)}: {'CURRENT' if not problems else 'STALE'}")
        for p in problems:
            print(f"  - {p}")
        return 1 if problems else 0
    if not (args.split and args.out):
        parser.error("--split and --out are required unless --check is given")
    return generate(Spec(split=args.split), args.out, spot_check=args.spot_check)


if __name__ == "__main__":
    sys.exit(main())
