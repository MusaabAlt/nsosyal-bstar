"""Rule-v3 -> rule-v4 A-label flip report (protocols/m1_positive_matching_precision_protocol.md §8).

Compares, row by row, the A-head pseudo-labels the rule-v3 artifact was trained on (git `7f5e003`,
byte-exact, digests pinned below) with the committed rule-v4 files, and lists every row whose
`a_label` changed: the rule-v3 family-A evidence (every rule-v3 match the rule-v4 file no longer
holds), the rule-v4 outcome read from m1's own collision evidence ("rule-v4 R<n>: <reason>"), and
the rule-v4 POSITIVE roots. It also checks that every row's EXCLUDED roots equal the last rule-v3
regeneration (`dd6a855`): rule v4 changes POSITIVE-root matching only.

Two outputs:
  * committed - eval/derived/m1_lexicon_rule_v4_flips.{json,md}: NO corpus text, NO gold, exactly like
    the derived files (row ids, match spans and matched surfaces only)
  * private   - eval/derived/private/ (git-ignored): the same rows with the original text and the corpus
    OFF/NOT label, CONTEXT ONLY - the label is never an input to any rule or to this comparison

Deliberately does NOT: open the official test set (only the training corpus, sha256-pinned, is read,
and only with --private); read the 500-row evaluation reference or any candidate prediction; re-run m1
(the committed files are the evidence).

    python -m eval.m1_lexicon_rule_v4_flips                 # committed report
    python -m eval.m1_lexicon_rule_v4_flips --private       # + the private full report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from eval import m1_lexicon_labels as G

SCRIPT = "AI/eval/m1_lexicon_rule_v4_flips.py"
VERSION = "1.0.0"
DERIVED = G.AI_ROOT / "eval" / "derived"
OUT_JSON = DERIVED / "m1_lexicon_rule_v4_flips.json"
OUT_MD = DERIVED / "m1_lexicon_rule_v4_flips.md"
PRIVATE = DERIVED / "private"
SPLITS = ("train", "dev")

# The rule-v3 artifact's training labels (its heads.json label_sources.a) and the last rule-v3 files.
RULE_V3_TRAINING = {"train": ("7f5e003", "78d845a5fed8dd38441d9ef23f416b85ed8d2ba747d94f5943509550d9fc50c8"),
                    "dev": ("7f5e003", "8f4dcdfeec707bd8cb9b52744ff6b72a675cdb94790b64d167b87c12fd603ee7")}
RULE_V3_LAST = {"train": ("dd6a855", "ce3ef280f6dd4ebcbfdc0cc2045d61aa8dc59ef2f1c3c222e9192e1ba785f5f5"),
                "dev": ("dd6a855", "79afe7b9e0a5fa999c4fa64b3c844064e0b7b851601d88305cfd94d6ed69a468")}
RULE = re.compile(r"rule-v4 (R\d)")
# R7 also extends m1's prayer clean word to "amîn": clean words were already applied under rule v3, so a
# rule-v3 match that is now a "clean word amin" collision can only come from that extension.
PRAYER = re.compile(r"\(clean word amin\)$")
RULE_NAMES = {"R1": "no letter", "R2": "edge digit", "R3": "edge punctuation / not a word of the root",
              "R4": "apostrophe or mask inside a word", "R5": "cross-word", "R6": "Turkish-letter spelling",
              "R7": "am morphology (and the prayer word amîn)", "R8": "stable clean form", "R9": "masked-root alignment"}


def historical(commit: str, split: str, digest: str) -> dict[str, Any]:
    shown = subprocess.run(["git", "-C", str(G.AI_ROOT), "show", f"{commit}:AI/eval/derived/m1_lexicon_{split}_seed42.json"],
                           capture_output=True, timeout=300)
    G.require(shown.returncode == 0, f"git show {commit} {split}: {shown.stderr[-300:]!r}")
    G.require(hashlib.sha256(shown.stdout).hexdigest() == digest, f"{commit} {split} file is not the pinned bytes")
    return json.loads(shown.stdout)


def current(split: str) -> tuple[dict[str, Any], str]:
    path = DERIVED / f"m1_lexicon_{split}_seed42.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    G.require(data["a_label_rule"]["version"] == G.A_LABEL_RULE_VERSION, f"{path.name} is not a rule-v4 file")
    return data, G.sha256_file(path)


def split_report(split: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    old = historical(RULE_V3_TRAINING[split][0], split, RULE_V3_TRAINING[split][1])
    last = historical(RULE_V3_LAST[split][0], split, RULE_V3_LAST[split][1])
    new, new_sha = current(split)
    ids = [r["row_id"] for r in new["rows"]]
    G.require(ids == [r["row_id"] for r in old["rows"]] == [r["row_id"] for r in last["rows"]], f"{split}: row ids differ")
    flips = []
    excluded_changed = []
    for o, l, n in zip(old["rows"], last["rows"], new["rows"]):
        if l["root_classes"]["excluded"] != n["root_classes"]["excluded"]:
            excluded_changed.append(n["row_id"])
        if o["a_label"] == n["a_label"]:
            continue
        evidence = {(c["start"], c["end"]): c["evidence"] for c in n["collisions"]}
        now = {(m["channel"], m["start"], m["end"]) for m in n["matches"]}
        before = {(m["channel"], m["start"], m["end"]) for m in o["matches"]}
        lost = []
        for m in o["matches"]:
            if (m["channel"], m["start"], m["end"]) in now:
                continue
            text = evidence.get((m["start"], m["end"]), "")
            rule = RULE.search(text)
            code = rule.group(1) if rule else ("R7" if PRAYER.search(text) else None)
            lost.append({"channel": m["channel"], "start": m["start"], "end": m["end"], "surface": m["surface"],
                         "rule": code, "evidence": text.split(": ", 1)[-1] or None})
        added = [dict(m) for m in n["matches"] if (m["channel"], m["start"], m["end"]) not in before]
        rules = sorted({m["rule"] for m in lost if m["rule"]})
        if n["a_label"] == 1 and not rules:
            rules = ["R9"]
        flips.append({"split": split, "row_id": n["row_id"], "a_label_rule_v3": o["a_label"],
                      "a_label_rule_v4": n["a_label"], "rule_v3_positive_roots": o["root_classes"]["positive"],
                      "rule_v4_positive_roots": n["root_classes"]["positive"], "rules": rules,
                      "rule_v3_matches_not_kept": lost, "rule_v4_matches_added": added})
    by_rule = Counter(r for f in flips for r in f["rules"])
    by_set = Counter("+".join(f["rules"]) or "unattributed" for f in flips)
    summary = {
        "rows": len(ids),
        "rule_v3_positives": sum(r["a_label"] == 1 for r in old["rows"]),
        "rule_v4_positives": sum(r["a_label"] == 1 for r in new["rows"]),
        "positive_to_negative": sum(f["a_label_rule_v3"] == 1 and f["a_label_rule_v4"] == 0 for f in flips),
        "negative_to_positive": sum(f["a_label_rule_v3"] == 0 and f["a_label_rule_v4"] == 1 for f in flips),
        "flipped_rows_by_rule": dict(sorted(by_rule.items())),
        "flipped_rows_by_rule_set": dict(sorted(by_set.items())),
        "unattributed_flips": [f["row_id"] for f in flips if not f["rules"]],
        "rows_whose_excluded_roots_differ_from_dd6a855": excluded_changed,
        "sources": {
            "rule_v3_training": {"commit": RULE_V3_TRAINING[split][0], "sha256": RULE_V3_TRAINING[split][1]},
            "rule_v3_last_regeneration": {"commit": RULE_V3_LAST[split][0], "sha256": RULE_V3_LAST[split][1]},
            "rule_v4": {"file": f"AI/eval/derived/m1_lexicon_{split}_seed42.json", "sha256": new_sha,
                        "generator_git_head": new["generator"]["git_head"],
                        "m1_lexicon": new["engine"]["module_versions"]["m1_lexicon"]},
        },
    }
    return summary, flips


def build() -> dict[str, Any]:
    splits, rows = {}, []
    for split in SPLITS:
        splits[split], flips = split_report(split)
        rows += flips
    return {
        "_README": ("Every row whose A-head pseudo-label differs between the rule-v3 training labels (git 7f5e003) "
                    "and the rule-v4 files (protocols/m1_positive_matching_precision_protocol.md, M1-PREC-1). "
                    "No corpus text and no gold: row ids, spans and matched surfaces only, as in the derived files. "
                    "Rule codes: " + "; ".join(f"{k} {v}" for k, v in RULE_NAMES.items()) + "."),
        "script": SCRIPT, "version": VERSION,
        "matching_protocol": {"id": G.MATCHING_PROTOCOL["id"], "file": f"AI/{G.MATCHING_PROTOCOL['file']}",
                              "sha256": G.sha256_file(G.AI_ROOT / G.MATCHING_PROTOCOL["file"])},
        "splits": splits,
        "rows": rows,
    }


def render_md(report: dict[str, Any], private: dict[str, tuple[str, str]] | None = None) -> str:
    lines = ["# Rule-v3 → rule-v4 A-label flips (M1-PREC-1)", "",
             "Generated by `AI/eval/m1_lexicon_rule_v4_flips.py`; the JSON next to this file is the "
             "machine-readable version. " + ("PRIVATE: holds corpus text and the corpus OFF/NOT label (context "
                                            "only). Never commit." if private else
                                            "No corpus text and no gold (row ids, spans, matched surfaces only)."),
             "", "| split | rows | rule-v3 positives | rule-v4 positives | 1 → 0 | 0 → 1 | EXCLUDED roots changed |",
             "|---|---|---|---|---|---|---|"]
    for split, s in report["splits"].items():
        lines.append(f"| {split} | {s['rows']} | {s['rule_v3_positives']} | {s['rule_v4_positives']} | "
                     f"{s['positive_to_negative']} | {s['negative_to_positive']} | "
                     f"{len(s['rows_whose_excluded_roots_differ_from_dd6a855'])} |")
    lines += ["", "Flipped rows by rule (a row counts under every rule that rejected one of its rule-v3 "
              "family-A matches):", "", "| rule | meaning | train | dev |", "|---|---|---|---|"]
    for code, name in RULE_NAMES.items():
        counts = [report["splits"][s]["flipped_rows_by_rule"].get(code, 0) for s in SPLITS]
        if any(counts):
            lines.append(f"| {code} | {name} | {counts[0]} | {counts[1]} |")
    for split in SPLITS:
        rows = [r for r in report["rows"] if r["split"] == split]
        lines += ["", f"## {split.upper()} ({len(rows)} rows)", ""]
        header = "| row | v3 → v4 | rule | rule-v3 family-A evidence → rule-v4 outcome | rule-v4 positive roots |"
        if private:
            header += " corpus label | text |"
        lines += [header, "|" + "---|" * (header.count("|") - 1)]
        for r in rows:
            seen, parts = set(), []
            for m in r["rule_v3_matches_not_kept"]:
                key = (m["start"], m["end"])
                if key in seen:
                    continue
                seen.add(key)
                parts.append(f"`{m['surface']}` → {m['evidence'] or 'not kept'}")
            parts += [f"added `{m['surface']}` ({m['channel']})" for m in r["rule_v4_matches_added"]]
            cells = [r["row_id"], f"{r['a_label_rule_v3']} → {r['a_label_rule_v4']}", "+".join(r["rules"]) or "—",
                     "; ".join(parts).replace("|", "\\|"), ", ".join(r["rule_v4_positive_roots"]) or "—"]
            if private:
                text, label = private[r["row_id"]]
                cells += [label, text.replace("|", "\\|").replace("\n", " ")]
            lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines) + "\n"


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--private", action="store_true", help="also write the full report with text and gold "
                                                                "to the git-ignored eval/derived/private/")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    try:
        report = build()
    except G.ProtocolStop as exc:
        print(f"PROTOCOL STOP: {exc}", file=sys.stderr)
        return 2
    write(OUT_JSON, json.dumps(report, ensure_ascii=False, indent=1) + "\n")
    write(OUT_MD, render_md(report))
    print(f"wrote {G._display(OUT_JSON)} and {G._display(OUT_MD)}")
    for split, s in report["splits"].items():
        print(f"  {split}: 1->0 {s['positive_to_negative']}, 0->1 {s['negative_to_positive']}, positives "
              f"{s['rule_v3_positives']} -> {s['rule_v4_positives']}, by rule {s['flipped_rows_by_rule']}, "
              f"EXCLUDED-root rows changed {len(s['rows_whose_excluded_roots_differ_from_dd6a855'])}")
    if args.private:
        spec = G.Spec(split="train")
        G.refuse_test_set(spec.corpus)
        G.require(G.sha256_file(spec.corpus) == spec.corpus_sha256, "corpus sha256 is not the pinned one")
        corpus = G.read_corpus(spec.corpus)
        private = {r["row_id"]: corpus[r["row_id"]] for r in report["rows"]}
        full = {**report, "_README": report["_README"].replace("No corpus text and no gold", "PRIVATE, never commit: "
                "with the original text and the corpus OFF/NOT label as CONTEXT ONLY"),
                "rows": [{**r, "text": private[r["row_id"]][0], "corpus_label_context_only": private[r["row_id"]][1]}
                         for r in report["rows"]]}
        write(PRIVATE / "m1_lexicon_rule_v4_flips_full.json", json.dumps(full, ensure_ascii=False, indent=1) + "\n")
        write(PRIVATE / "m1_lexicon_rule_v4_flips_full.md", render_md(report, private))
        print(f"wrote the private full report to {G._display(PRIVATE)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
