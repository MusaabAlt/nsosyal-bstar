"""m1 lexicon labels on one half of the frozen split (seed 42) - runs
protocols/m1_lexicon_dev_labels_protocol.md (--split dev) or
protocols/m1_lexicon_train_labels_protocol.md (--split train).

Writes, for every row of the chosen split, what m1_lexicon publishes at runtime through the
current m0 -> m2 -> m6 -> m1 path: the three hit flags, the channel, the matched roots, the span
of every match, every substring collision, every HOMONYM guard, and the A-head pseudo-label
`a_label` (train protocol, rule v4: a valid hit on a root of the explicit POSITIVE set -> 1, otherwise
0; the set is the frozen rule-v3 A-head taxonomy - explicit obscene / profane lexical roots - recorded
in the protocol and never derived from any evaluation set; rule v4 is that formula and taxonomy with
m1's POSITIVE-root matching made precise, protocols/m1_positive_matching_precision_protocol.md).

Deliberately does NOT:
  * define the evaluation slice (m4's slice is eval/frozen/study_slice_dev.json, frozen)
  * write gold: join on row_id; gold is read only for the integrity counts
  * call private m1 functions: everything comes from m1's published signals, scores, guards
  * mix the halves: one split per file, and the train run never labels a dev row
  * open the official test set: only the training corpus and the committed split are read, no
    path containing "testset" or "labela" is accepted, every row id is a corpus id
  * report metrics: recall / precision / FPR are computed from these files elsewhere
  * read the 500-row AI-assisted, human-adjudicated dev reference (eval/annotation/): it is an
    EVALUATION set only and no path of this script reaches it

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
from contracts.module_api import NORMALIZED, RAW, Context, ModuleOutput
from modules import registry
from pipeline.run import Pipeline

AI_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ROOT.parent
SOURCE = "m1_lexicon"
GENERATOR = "AI/eval/m1_lexicon_labels.py"
# Bump on any change to the row schema, the a_label rule, or what the header records.
GENERATOR_VERSION = "6.0.0"

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

ROW_FIELDS = ["row_id", "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "channel", "a_label", "a_label_v1",
              "roots", "root_classes{positive,excluded,review}", "matches[channel,start,end,surface]",
              "collisions[start,end,surface,evidence]", "homonyms[start,end,surface,evidence]"]

# -- pseudo-label rule v4 = the rule-v3 formula and taxonomy (train protocol, amendments (b), (d)) -----
# The A head is explicit profanity: an obscene / profane lexical root. The taxonomy is an EXPLICIT,
# versioned list over every root of the pinned terlik dictionary, frozen in the protocol before any
# v3 label existed; tests require the protocol's lists to equal these sets. Never move a root because
# of how a dev row was labelled or scored: that is evaluation leakage. Any change is a rule-version
# bump recorded in the protocol first.
# Rule v4 (amendment (d)) keeps the taxonomy - TAXONOMY_VERSION stays 3 and so does its digest - and
# changes only how m1 accepts a POSITIVE-root match (M1-PREC-1). The generator reads matches as before.
A_LABEL_RULE_VERSION = 4
TAXONOMY_VERSION = 3
MATCHING_PROTOCOL = {"id": "M1-PREC-1", "file": "protocols/m1_positive_matching_precision_protocol.md"}
TERLIK_TR_DICTIONARY_SHA256 = "e83a97b38c553227cd20c2b5688939fda6037fb30b4964e9fd063a125a9a641c"
POSITIVE, EXCLUDED, REVIEW = "positive", "excluded", "review"
POSITIVE_ROOTS = frozenset({
    "am", "amcı", "amk", "bok", "gavat", "göt", "hassiktir", "orospu", "oç", "pezevenk", "piç", "sakso",
    "sg", "sik", "sktrgt", "taşak", "yarrak"
})
EXCLUDED_ROOTS = frozenset({
    "ahlaksız", "ahmak", "akılsız", "allahbelanıversin", "alçak", "alık", "andaval", "aptal", "arsız",
    "asılası", "avanak", "ağzıbozuk", "aşağılık", "aşifte", "baldırıçıplak", "belanıbulurum", "beyinamip",
    "beyinsiz", "boğazınıkeserim", "budala", "canınıalırım", "cehenneme", "dalkavuk", "dallama", "dangalak",
    "dangoz", "defol", "densiz", "denyo", "dingil", "dolandırıcı", "domuz", "döl", "dümenci", "dürzü",
    "edepsiz", "embesil", "enayi", "ensenibulurum", "ezik", "eşek", "eşoğlueşek", "fahişe", "fuhuş",
    "fırıldak", "geber", "gerizekalı", "gerzek", "glk", "gömerler", "gömülesi", "görgüsüz", "hapiyedin",
    "hayasız", "haysiyetsiz", "hergele", "hödük", "hımbıl", "hınzır", "ibne", "ikiyüzlü", "kafanıkırarım",
    "kafasız", "kahpe", "kalleş", "kalpazan", "kaltak", "kalınkafalı", "kancık", "kansız", "karaktersiz",
    "kaybol", "kaşar", "kepaze", "kerhane", "kesilesi", "kevaşe", "kötüniyetli", "küstah", "kıro",
    "kıtakıllı", "madrabaz", "maganda", "magat", "mal", "mankafa", "manyak", "maymun", "meme",
    "mezarınıkazarım", "müptezel", "namussuz", "nankör", "onursuz", "oğlancı", "pislik", "puşt", "rezil",
    "sahtekar", "salak", "saloz", "sersem", "serseri", "soysuz", "sürtük", "tabanvansen", "terbiyesiz",
    "tokmakçı", "ukala", "utanmaz", "vefasız", "yakılası", "yalaka", "yarımakıllı", "yavşak", "yobaz",
    "yüzkarası", "yüzsüz", "yıkık", "zonta", "zugar", "zukkafa", "çomar", "çüş", "öküz", "öldürücem",
    "üçkağıtçı", "şapşal", "şarlatan", "şerefsiz"
})
REVIEW_ROOTS: frozenset[str] = frozenset()    # empty in v3: every root is decided


def taxonomy_record() -> dict[str, Any]:
    """The frozen taxonomy as a canonical record: what the header stores and the digest covers."""
    return {"version": TAXONOMY_VERSION, POSITIVE: sorted(POSITIVE_ROOTS), EXCLUDED: sorted(EXCLUDED_ROOTS),
            REVIEW: sorted(REVIEW_ROOTS)}


def taxonomy_sha256() -> str:
    canonical = json.dumps(taxonomy_record(), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def terlik_tr_dictionary() -> Path:
    """Located without importing terlik: eval/ is core (stdlib + pyyaml only); the dictionary is data."""
    import importlib.util
    spec = importlib.util.find_spec("terlik")
    require(spec is not None and spec.origin is not None, "terlik is not installed: its dictionary defines the classes")
    return Path(spec.origin).resolve().parent / "lang" / "tr" / "dictionary.json"


def classify(roots: list[str]) -> dict[str, str]:
    """root -> POSITIVE / EXCLUDED / REVIEW from the explicit rule-v3 sets. Stops on any unexpected
    dictionary condition: a root in no set or in two sets, or a set root the dictionary lacks."""
    sets = {POSITIVE: POSITIVE_ROOTS, EXCLUDED: EXCLUDED_ROOTS, REVIEW: REVIEW_ROOTS}
    overlap = (POSITIVE_ROOTS & EXCLUDED_ROOTS) | (POSITIVE_ROOTS & REVIEW_ROOTS) | (EXCLUDED_ROOTS & REVIEW_ROOTS)
    require(not overlap, f"roots in two rule-v3 classes: {sorted(overlap)}")
    unclassified = [r for r in roots if not any(r in members for members in sets.values())]
    require(not unclassified, f"dictionary roots in no rule-v3 class: {unclassified}")
    absent = sorted((POSITIVE_ROOTS | EXCLUDED_ROOTS | REVIEW_ROOTS) - set(roots))
    require(not absent, f"rule-v3 roots the dictionary does not hold: {absent}")
    return {r: next(c for c, members in sets.items() if r in members) for r in roots}


def lexical_classes(dictionary: Path | None = None) -> dict[str, str]:
    """The rule-v3 class of every root of the pinned terlik dictionary (protocol amendment (b))."""
    path = dictionary or terlik_tr_dictionary()
    require(path.is_file(), f"terlik dictionary missing: {path}")
    got = sha256_file(path)
    require(got == TERLIK_TR_DICTIONARY_SHA256, f"terlik dictionary sha256 {got} is not the pinned one: the "
                                                 "taxonomy was frozen on other bytes")
    return classify([e["root"] for e in json.loads(path.read_text(encoding="utf-8"))["entries"]])

README = {
    "dev": (
        "REGENERABLE, not frozen. What m1_lexicon (terlik balanced) publishes on every row of the frozen "
        "DEV split (seed 42), in dev_ids order, through the implemented m0 -> m2 -> m6 -> m1 path, plus the "
        "A-head pseudo-label a_label (protocols/m1_lexicon_train_labels_protocol.md §5). Purposes: "
        "pseudo-label AGREEMENT for m3's A head (never its evaluation: A-head quality is measured only "
        "against an independent evaluation reference - currently the 500-row AI-assisted, human-adjudicated "
        "dev reference under docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md, evaluation only and not a human "
        "oracle) and comparison against "
        "eval/frozen/study_slice_dev.json. This file is NOT the evaluation slice: m4's lexicon_hit / "
        "lexicon_free slice stays eval/frozen/study_slice_dev.json (karaliste), and the two files are never "
        "merged. Regenerate with protocols/m1_lexicon_dev_labels_protocol.md §7; never edit by hand."
    ),
    "train": (
        "REGENERABLE, not frozen. What m1_lexicon (terlik balanced) publishes on every row of the frozen "
        "TRAIN split (seed 42), in train_ids order, through the implemented m0 -> m2 -> m6 -> m1 path, plus "
        "the A-head pseudo-label a_label (protocols/m1_lexicon_train_labels_protocol.md §5). Purpose: "
        "training supervision for m3's A head - a KEYWORD pseudo-label, never an evaluation reference "
        "(A-head quality is measured only against an independent evaluation reference - currently the "
        "500-row AI-assisted, human-adjudicated dev reference under "
        "docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md, evaluation only and not a human oracle). No dev "
        "row is in this file. Regenerate with the train protocol §9; never edit by hand."
    ),
}

LIMITS = [
    "Gold is binary OFF/NOT: any rate computed from this file measures lexicon hits against OFF, never "
    "'profanity present' against a human judgement (the corpus has no A codes).",
    "a_label is a keyword pseudo-label (rule v4: terlik matches restricted to the explicit POSITIVE set of "
    "obscene / profane roots, each accepted only as a real word of its root under M1-PREC-1): an A head trained "
    "on it learns that set's coverage, not what terlik misses. Its quality is known only against an independent "
    "evaluation reference.",
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


def a_label_v1_of(raw: bool, norm: bool, matches: list[dict[str, Any]]) -> int:
    """Rule v1 ("valid hit"): raw hit, or a normalized hit that m1 mapped back to the original text.
    Superseded as the label; kept as the first condition of v2 and for the old/new comparison."""
    spanned_norm = any(m["channel"] == NORMALIZED for m in matches)
    return int(raw or (norm and spanned_norm))


def a_label_of(valid_hit: int, root_classes: dict[str, list[str]]) -> int | None:
    """Rules v3 and v4 (one formula; v4 differs only in m1's POSITIVE-root matching, M1-PREC-1): 1 on a
    root of the explicit POSITIVE set; 0 otherwise. None (masked, no supervision) only when REVIEW roots
    alone matched - the REVIEW class is empty, so it never happens; the mechanism is kept for a future
    version."""
    if not valid_hit:
        return 0
    if root_classes[POSITIVE]:
        return 1
    return None if root_classes[REVIEW] else 0


class M1MatchTap:
    """m1's private `_matches` for the post being analysed (generator 5.0.0, train protocol
    amendment (c)). Under M1-ROUTE-1 a dictionary match may emit no content score at all, so the
    matches can no longer be read from content scores. The pipeline keeps "_" signal keys out of
    the response (pipeline.run.public_signals), so the generator reads them where m1 returns them:
    m1's own ModuleOutput, recorded by wrapping that module instance's process(). Only `root`,
    `channel` and `span` are read - never the runtime route: a_label has no path to it."""

    def __init__(self, module: Any) -> None:
        self.matches: Any = None
        original = module.process

        def process(ctx: Context) -> ModuleOutput:
            out = original(ctx)
            self.matches = out.signals.get("_matches") if out.ok else None
            return out

        module.process = process


def m1_tap(pipeline: Pipeline) -> M1MatchTap:
    tap = getattr(pipeline, "_m1_match_tap", None)
    if tap is None:
        m1 = next((m for m in pipeline.modules if m.name.value == SOURCE), None)
        require(m1 is not None, "the lexicon pipeline holds no m1_lexicon module")
        tap = M1MatchTap(m1)
        pipeline._m1_match_tap = tap  # type: ignore[attr-defined]
    return tap


def label_row(pipeline: Pipeline, row_id: str, text: str, classes: dict[str, str]) -> dict[str, Any]:
    tap = m1_tap(pipeline)
    tap.matches = None
    result = pipeline.analyze(text)
    degraded = {d["module"]: d for d in result.signals["pipeline"]["degraded"]}
    require(SOURCE not in degraded, f"row {row_id}: m1_lexicon degraded: {degraded.get(SOURCE)}")
    signals = result.signals.get(SOURCE, {})
    flags = {key: signals.get(key) for key in ("lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm")}
    require(all(isinstance(v, bool) for v in flags.values()), f"row {row_id}: non-bool flag {flags}")
    require(flags["lexicon_hit"] == (flags["lexicon_hit_raw"] or flags["lexicon_hit_norm"]),
            f"row {row_id}: lexicon_hit is not raw OR norm {flags}")

    # Every match, whatever its runtime route, from m1's private `_matches` (M1MatchTap): one per
    # channel and original span, as the content scores were before M1-ROUTE-1.
    require(isinstance(tap.matches, (list, tuple)), f"row {row_id}: m1 published no _matches signal")
    matches = []
    for item in tap.matches:
        channel = item.get("channel")
        require(channel in (RAW, NORMALIZED), f"row {row_id}: unknown channel {channel!r} in _matches")
        require(item.get("span") is not None, f"row {row_id}: m1 match without span")
        start, end = (int(v) for v in item["span"])
        require(0 <= start < end <= len(text), f"row {row_id}: span {item['span']} outside the text")
        match = {"channel": channel, "start": start, "end": end, "surface": text[start:end]}
        if match not in matches:
            matches.append(match)
    matches.sort(key=lambda m: (m["start"], m["end"], m["channel"]))
    # Integrity: every m1 content score (decision layer's pre-fusion record) sits on a published match.
    for score in result.signals.get("decision", {}).get("channel_scores", []):
        source = str(score.get("source", ""))
        if source.startswith(f"{SOURCE}@") and score.get("span") is not None:
            key = (source.split("@", 1)[1], int(score["span"][0]), int(score["span"][1]))
            require(any((m["channel"], m["start"], m["end"]) == key for m in matches),
                    f"row {row_id}: m1 content score {key} has no match in _matches")

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
                if item not in items:      # m1 raises one guard per channel match; the same span once
                    items.append(item)
        return sorted(items, key=lambda c: (c["start"], c["end"]))

    roots = sorted(signals.get("matched_roots", []))
    unknown = [r for r in roots if r not in classes]
    require(not unknown, f"row {row_id}: matched roots outside the terlik dictionary classes: {unknown}")
    root_classes = {c: [r for r in roots if classes[r] == c] for c in (POSITIVE, EXCLUDED, REVIEW)}
    v1 = a_label_v1_of(flags["lexicon_hit_raw"], flags["lexicon_hit_norm"], matches)
    return {
        "row_id": row_id,
        **flags,
        "channel": channel_of(flags["lexicon_hit_raw"], flags["lexicon_hit_norm"]),
        "a_label": a_label_of(v1, root_classes),
        "a_label_v1": v1,
        "roots": roots,
        "root_classes": root_classes,
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


def build_rows(ids: list[str], corpus: dict[str, tuple[str, str]], pipeline: Pipeline,
               classes: dict[str, str] | None = None) -> tuple[str, list[dict[str, Any]]]:
    classes = classes if classes is not None else lexical_classes()
    rows = [label_row(pipeline, row_id, corpus[row_id][0], classes) for row_id in ids]
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
        "a_label": sum(1 for r in rows if r["a_label"] == 1),
        "a_label_null": sum(1 for r in rows if r["a_label"] is None),
        "a_label_zero": sum(1 for r in rows if r["a_label"] == 0),
        "a_label_v1": sum(r["a_label_v1"] for r in rows),
        "v1_positive_now_zero": sum(1 for r in rows if r["a_label_v1"] == 1 and r["a_label"] == 0),
        "v1_positive_now_null": sum(1 for r in rows if r["a_label_v1"] == 1 and r["a_label"] is None),
        "v1_zero_now_positive": sum(1 for r in rows if r["a_label_v1"] == 0 and r["a_label"] == 1),
        "rows_with_positive_root": sum(bool(r["root_classes"][POSITIVE]) for r in rows),
        "rows_with_excluded_root": sum(bool(r["root_classes"][EXCLUDED]) for r in rows),
        "rows_with_review_root": sum(bool(r["root_classes"][REVIEW]) for r in rows),
        "norm_hit_unmapped": sum(1 for r in rows if r["lexicon_hit_norm"]
                                 and not any(m["channel"] == NORMALIZED for m in r["matches"])),
        "rows_with_collision": sum(bool(r["collisions"]) for r in rows),
        "rows_with_homonym": sum(bool(r["homonyms"]) for r in rows),
        "rows_all_matches_homonym": sum(
            1 for r in rows if r["matches"]
            and all(any(h["start"] <= m["start"] and m["end"] <= h["end"] for h in r["homonyms"]) for m in r["matches"])),
    }


# -- provenance ---------------------------------------------------------------
def matching_protocol_record() -> dict[str, Any]:
    """The M1-PREC-1 protocol the file's POSITIVE-root matches were accepted under (rule v4)."""
    rel = MATCHING_PROTOCOL["file"]
    path = AI_ROOT / rel
    require(path.exists(), f"{rel} does not exist - rule v4 needs its matching protocol")
    commit = git("log", "-1", "--format=%H", "--", rel).stdout.strip() or None
    clean = commit is not None and git("diff", "--quiet", "HEAD", "--", rel).returncode == 0
    return {"id": MATCHING_PROTOCOL["id"], "file": f"AI/{rel}", "sha256": sha256_file(path), "commit": commit,
            "committed_and_unchanged": clean}


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
                 rows: list[dict[str, Any]], block: str, classes: dict[str, str]) -> dict[str, Any]:
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
        "a_label_rule": {
            "version": A_LABEL_RULE_VERSION,
            "text": "valid hit := lexicon_hit_raw OR (lexicon_hit_norm AND a normalized-channel match with a valid "
                    "span). a_label = 1 if valid hit and a matched root is in the explicit POSITIVE set; null only if "
                    "REVIEW roots alone matched (the REVIEW class is empty); 0 otherwise - "
                    "protocols/m1_lexicon_train_labels_protocol.md, amendments 2026-09-18 (b) and (d) (rule v4: the "
                    "rule-v3 taxonomy, A = explicit obscene / profane lexical root; a POSITIVE-root match counts only "
                    "when m1 accepts it as a real word of its root under M1-PREC-1)",
            "taxonomy_version": TAXONOMY_VERSION,
            "matching_protocol": matching_protocol_record(),
            "terlik_tr_dictionary_sha256": TERLIK_TR_DICTIONARY_SHA256,
            "taxonomy_sha256": taxonomy_sha256(),
            "positive_roots": sorted(POSITIVE_ROOTS),
            "excluded_roots": sorted(EXCLUDED_ROOTS),
            "review_roots": sorted(REVIEW_ROOTS),
            "class_sizes": {c: sum(1 for v in classes.values() if v == c) for c in (POSITIVE, EXCLUDED, REVIEW)},
        },
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
    expected_fields = {"row_id", "lexicon_hit", "lexicon_hit_raw", "lexicon_hit_norm", "channel", "a_label",
                       "a_label_v1", "roots", "root_classes", "matches", "collisions", "homonyms"}
    rule = data.get("a_label_rule") if isinstance(data.get("a_label_rule"), dict) else {}
    if rule.get("version") != A_LABEL_RULE_VERSION:
        problems.append(f"a_label rule version {rule.get('version')} != {A_LABEL_RULE_VERSION}")
    if rule.get("terlik_tr_dictionary_sha256") != TERLIK_TR_DICTIONARY_SHA256:
        problems.append("a_label rule was applied with another terlik dictionary")
    if rule.get("taxonomy_sha256") != taxonomy_sha256():
        problems.append("a_label taxonomy differs from the generator's frozen rule-v3 sets")
    if rule.get("taxonomy_version") != TAXONOMY_VERSION:
        problems.append(f"taxonomy version {rule.get('taxonomy_version')} != {TAXONOMY_VERSION}")
    matching = rule.get("matching_protocol") if isinstance(rule.get("matching_protocol"), dict) else {}
    matching_path = AI_ROOT / MATCHING_PROTOCOL["file"]
    if matching.get("id") != MATCHING_PROTOCOL["id"] or not matching_path.exists() \
            or matching.get("sha256") != sha256_file(matching_path):
        problems.append("matching protocol (M1-PREC-1) differs from the protocol on disk")
    try:
        if sha256_file(terlik_tr_dictionary()) != TERLIK_TR_DICTIONARY_SHA256:
            problems.append("installed terlik dictionary differs from the pinned sha256")
    except Exception as exc:                                     # terlik not importable on this machine
        problems.append(f"terlik dictionary not checkable: {type(exc).__name__}")
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
        classes = lexical_classes()
        block, rows = build_rows(ids, corpus, pipeline, classes)
        second, _ = build_rows(ids, corpus, pipeline, classes)
        require(block == second, "two generations of the rows differ - not deterministic")
        header = build_header(spec, meta, engine, hashes, rows, block, classes)
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
