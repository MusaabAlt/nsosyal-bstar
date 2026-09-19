"""ModuleEvaluator: measure ONE module alone (CLAUDE.md rule 7).

Fixture format (jsonl, one item per line):
  {"id": "...", "text": "...",
   "expected": ["A2", "ZERO_WIDTH", "NEGATION", "target:individual"],
   "context": {"charsafe_text": "...", "normalized_text": "...", "signals": {}},  # optional
   "expect": {"charsafe_text": "..."},                                            # optional
   "expect_clean": true,                                                           # optional
   ("expect_patterns" is accepted as the spec.md name for "expected")
   "placeholder": false}                                                           # optional

`context` lets a downstream module be measured without running upstream
modules. Items with "placeholder": true are counted but not scored.

Predicted codes come from the decision layer applied to the module's output
alone, so the thresholds measured are exactly the ones in thresholds.yaml.

Reporting rules (modules/README.md):
  * per code, never pooled - an average hides the case that fails;
  * every rate carries a percentile-bootstrap CI over items;
  * the code list is FIXED by what the module provides (not gold ∪ predictions),
    so a code's FPR denominator never moves with what happened to be predicted;
  * representation modules also report capture rate per pattern and damage rate
    on clean text;
  * fixture-run and trap-run latency are reported separately;
  * latency is TIMED REPEATEDLY: every fixture and trap item runs
    `latency_repeats` extra times after its scored run, and p50/p95 are taken
    over all those timings. One run per item reported as "p95" is not a p95.
    The repeat count is recorded in the results next to the numbers;
  * latency budgets apply to CLEAN input (owner decision). Adversarial input is
    measured and reported alongside in its own column, with the same bands; an
    overrun there is a published finding (`adversarial_over_budget`), never
    hidden and never folded into `within_budget`.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import platform
import random
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from contracts.codes import ContentCode, FormCode, GuardCode, ModuleName, TargetType
from contracts.module_api import Context, ModuleOutput
from contracts.schema import AnalysisResult, ContentScore
from decision import actions, fusion
from modules import registry
from pipeline.run import (DEGRADED_FAILED, DEGRADED_INVALID, DEGRADED_STUB, Pipeline, artifact_hash,
                          build_modules_safely, deep_freeze, safe_process, span_declarations)

ROOT = Path(__file__).resolve().parent.parent
TRAPS_PATH = ROOT / "eval" / "traps" / "traps.jsonl"
RESULTS_DIR = ROOT / "eval" / "results"
REPRESENTATION_FIELDS = ("charsafe_text", "normalized_text")
# Declared per-module implementation status (STUB / PARTIAL / IMPLEMENTED), owner-maintained.
IMPLEMENTATION_STATUS_PATH = ROOT / "eval" / "implementation_status.json"
IMPLEMENTATION_STATUSES = ("IMPLEMENTED", "PARTIAL", "STUB")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for lineno, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"{path}:{lineno}: invalid json: {exc}") from exc
    return items


def percentile(values: list[float], q: float) -> float | None:
    """Nearest-rank percentile, q in [0, 100]."""
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(q / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _ratio(num: float, den: float) -> float | None:
    return num / den if den else None


def code_space(module: Any) -> list[str]:
    """Fixed list of codes a module can be scored on, derived from `provides`."""
    provides = set(module.provides)
    codes: list[str] = []
    if "content" in provides:
        codes += [c.value for c in ContentCode if c is not ContentCode.CLEAN]
    if "form" in provides:
        codes += [c.value for c in FormCode]
    if "guards" in provides:
        codes += [c.value for c in GuardCode]
    if "target" in provides:
        codes += [f"target:{t.value}" for t in TargetType if t is not TargetType.NONE]
    return codes


def latency_budget(latencies: list[float], lengths: list[int], budget: Any,
                   items: list[int] | None = None) -> dict[str, Any]:
    """Compare fixture latency with a scalar budget, or with per-length bands
    {max_chars: p95_ms}: each timing counts in the smallest band that holds its
    item. `n` counts timings; `n_items` (when `items` is given) counts items."""
    if budget is None or not isinstance(budget, dict):
        p95 = percentile(latencies, 95)
        return {"budget_p95_ms": budget,
                "within_budget": None if budget is None or p95 is None else p95 <= budget}
    bands, lower = [], -1
    for max_chars in sorted(budget):
        in_band = [k for k, n in enumerate(lengths) if lower < n <= max_chars]
        sample = [latencies[k] for k in in_band]
        p95 = percentile(sample, 95)
        band = {"max_chars": max_chars, "n": len(sample), "p95_ms": p95, "budget_p95_ms": budget[max_chars],
                "within_budget": None if p95 is None else p95 <= budget[max_chars]}
        if items is not None:
            band["n_items"] = len({items[k] for k in in_band})
        bands.append(band)
        lower = max_chars
    checked = [b["within_budget"] for b in bands if b["within_budget"] is not None]
    return {"budget_bands": bands, "unbudgeted_n": sum(1 for n in lengths if n > lower),
            "within_budget": all(checked) if checked else None}


# Timings per item. High enough for a stable p95 per band even when a band holds a
# single item; override with --latency-repeats (or LATENCY_REPEATS in scripts/check.sh).
# A measurement setting like --n-boot, not decision config: it lives here rather than
# in decision/thresholds.yaml so changing it never changes artifact_hash.
DEFAULT_LATENCY_REPEATS = 200


def _checked_repeats(repeats: int) -> int:
    if isinstance(repeats, bool) or not isinstance(repeats, int) or not range(repeats):
        raise ValueError(f"latency repeats must be a positive integer, got {repeats!r}")
    return repeats


# How a fixture item is classed for latency. Clean is what the budget covers.
LATENCY_CLASSES = {
    "clean": "expect_clean is true; or, when an item has no expect_clean, it has no gold codes",
    "adversarial": "every other scored fixture item (gold codes present, or expect_clean false)",
}


def latency_class(item: dict[str, Any]) -> str:
    if "expect_clean" in item:
        return "clean" if item["expect_clean"] else "adversarial"
    gold = item.get("expected", item.get("expect_patterns", []))
    return "adversarial" if gold else "clean"


def latency_report(latencies: list[float], lengths: list[int], classes: list[str], budget: Any,
                   items: list[int] | None = None) -> dict[str, Any]:
    """Fixture latency split into clean and adversarial columns, each with the
    budget bands. Only the clean column decides `within_budget`. `items` gives the
    item index of every timing, so each column and band reports `n_items` next to
    `n` (timings)."""
    items = items if items is not None else list(range(len(latencies)))
    columns: dict[str, Any] = {}
    for name in LATENCY_CLASSES:
        sample = [(ms, n, i) for ms, n, c, i in zip(latencies, lengths, classes, items) if c == name]
        ms_list = [ms for ms, _, _ in sample]
        columns[name] = {"n_items": len({i for _, _, i in sample}), "n": len(sample),
                         "p50_ms": percentile(ms_list, 50), "p95_ms": percentile(ms_list, 95),
                         **latency_budget(ms_list, [n for _, n, _ in sample], budget, [i for _, _, i in sample])}
    adversarial_within = columns["adversarial"]["within_budget"]
    return {
        "budget_applies_to": "clean",
        "classes": LATENCY_CLASSES,
        **columns,
        "within_budget": columns["clean"]["within_budget"],
        "adversarial_over_budget": None if adversarial_within is None else not adversarial_within,
    }


def _band_text(band: dict[str, Any]) -> str:
    p95 = "n/a" if band["p95_ms"] is None else f"{band['p95_ms']:.3f}ms"
    return f"<={band['max_chars']}:items={band.get('n_items', '?')},timings={band['n']},p95={p95}"


def tr_fold(text: str) -> str:
    """Turkish-aware case fold, used only to decide whether a word changed.
    NFC first: canonical composition ("s" + U+0327 -> "ş") is not damage."""
    return unicodedata.normalize("NFC", text).replace("I", "ı").replace("İ", "i").lower()


# -- observability (Gate 1) -----------------------------------------------------------
# Three things a result file used to hide: that the module was a stub or failed
# (the harness never degraded), what the binary offensive score did (only content
# codes were scored), and which bytes produced the number (no provenance).

def degradation_record(module: Any, out: ModuleOutput, problems: list[str]) -> dict[str, Any] | None:
    """The `signals.pipeline.degraded` entry Pipeline.analyze would write for this
    module's output: stub, ok=False, or items dropped by Pipeline._merge - same
    kinds, same reasons, same order. tests/test_harness_gate1.py checks the two
    agree, so the harness cannot drift into calling a stub healthy."""
    kinds: list[str] = []
    reasons: list[str] = []
    if getattr(module, "stub", False):
        kinds.append(DEGRADED_STUB)
        reasons.append("stub: no detection logic yet")
    if not out.ok:
        kinds.append(DEGRADED_FAILED)
        reasons.append("; ".join(map(str, out.notes)) or "ok=False")
    if problems:
        kinds.append(DEGRADED_INVALID)
        reasons.extend(problems)
    if not kinds:
        return None
    return {"module": module.name.value, "kinds": kinds, "reasons": reasons}


def observe(result: AnalysisResult, cfg: dict[str, Any]) -> dict[str, Any]:
    """What one decided result says, as SEPARATE facts - never one boolean:
    content that fired, the binary score's state, form / guard effects,
    degradation, and the verdict with what drove it (actions.resolve is pure, so
    re-asking it here changes nothing)."""
    decision = result.signals.get("decision", {})
    binary = decision.get("binary_offensive")
    verdict, driver = actions.resolve(result, cfg)
    return {
        "content_fired": sorted(s.code.value for s in result.fired()),
        "content_scored": sorted(f"{s.code.value}<-{s.source}" for s in result.content
                                 if s.code is not ContentCode.CLEAN),
        "binary": None if binary is None else {"fired": binary["fired"], "threshold": binary["threshold"],
                                                "channels": binary["channels"], "action": binary["action"]},
        "form_active": [c.value for c in result.form.active],
        "guards_active": sorted(g.code.value for g in result.guards if g.active),
        "guards_suppressed": {g.code.value: [c.value for c in g.suppressed] for g in result.guards if g.suppressed},
        "degraded": [d["module"] for d in actions.degraded_modules(result)],
        "post_offensive": decision.get("post_offensive"),
        "verdict": None if verdict is None else verdict.value,
        "driver": f"content:{driver.code.value}" if isinstance(driver, ContentScore) else driver,
    }


def binary_fired(result: AnalysisResult) -> bool:
    binary = result.signals.get("decision", {}).get("binary_offensive") or {}
    return bool(binary.get("fired"))


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


def file_digest(path: Path) -> str | None:
    try:
        return hashlib.sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return None


def provenance(inputs: dict[str, Path], **extra: Any) -> dict[str, Any]:
    """Where a number came from: the commit, whether tracked files under AI/ were
    dirty, and the digest of every data file read. A result without this block
    cannot be tied to a commit (HISTORICAL_RESULT); one with it is a
    CURRENT_REPRODUCIBLE_RESULT only while `git_dirty` is false and the digests
    match that commit."""
    status = _git("status", "--porcelain", "--", ".")
    lines = [line for line in (status or "").splitlines() if line]
    return {
        "git_head": _git("rev-parse", "HEAD"),
        "git_dirty": None if status is None else any(not line.startswith("??") for line in lines),
        "git_untracked_under_ai": None if status is None else sum(1 for line in lines if line.startswith("??")),
        "python": platform.python_version(),
        "inputs": {name: {"path": (str(Path(p).relative_to(ROOT)) if Path(p).is_relative_to(ROOT) else str(p)),
                          "sha256": file_digest(Path(p))} for name, p in inputs.items()},
        **extra,
    }


def implementation_status(module: Any) -> dict[str, Any]:
    """Declared status (eval/implementation_status.json) cross-checked with the
    module's `stub` flag. The report says in words what its numbers cover: a
    stub's numbers cover nothing, a PARTIAL module's numbers never cover its
    `not_built` list."""
    declared = json.loads(IMPLEMENTATION_STATUS_PATH.read_text(encoding="utf-8"))["modules"].get(module.name.value)
    is_stub = bool(getattr(module, "stub", False))
    status = "UNDECLARED" if declared is None else str(declared.get("status"))
    consistent = declared is not None and status in IMPLEMENTATION_STATUSES and (status == "STUB") == is_stub
    if not consistent:
        # A wrong declaration is a data error to fix before any number is read.
        scope = f"INCONSISTENT: declared {status!r} but stub={is_stub}; fix eval/implementation_status.json"
    elif is_stub:
        scope = "NOT VERIFIED: stub - traps, per-code metrics and latency describe an empty module"
    else:
        scope = (f"MEASURED ({status}); items in not_built are outside this measurement"
                 if status == "PARTIAL" else f"MEASURED ({status})")
    return {"stub": is_stub, "declared_status": status, "consistent": consistent,
            "not_built": list((declared or {}).get("not_built", [])),
            "preconditions": list((declared or {}).get("preconditions", [])),
            "behaviour_measurable": consistent and not is_stub, "scope": scope}


@dataclass
class Cells:
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0

    def add(self, other: "Cells") -> None:
        self.tp += other.tp
        self.fp += other.fp
        self.fn += other.fn
        self.tn += other.tn

    def metrics(self) -> dict[str, float | None]:
        recall = _ratio(self.tp, self.tp + self.fn)
        precision = _ratio(self.tp, self.tp + self.fp)
        f1 = (None if recall is None or precision is None
              else _ratio(2 * precision * recall, precision + recall) or 0.0)
        return {"recall": recall, "precision": precision, "f1": f1, "fpr": _ratio(self.fp, self.fp + self.tn)}


class ModuleEvaluator:
    def __init__(self, module: Any, fixture_path: Path, traps_path: Path = TRAPS_PATH,
                 config: dict[str, Any] | None = None, results_dir: Path = RESULTS_DIR,
                 n_boot: int = 1000, ci: float = 0.95, seed: int = 20240901,
                 latency_repeats: int = DEFAULT_LATENCY_REPEATS) -> None:
        self.module = module
        self.fixture_path = Path(fixture_path)
        self.traps_path = Path(traps_path)
        self.config = config if config is not None else fusion.load_config()
        self.results_dir = Path(results_dir)
        self.n_boot = n_boot
        self.ci = ci
        self.seed = seed
        self.fixture_latencies: list[float] = []
        self.fixture_lengths: list[int] = []
        self.fixture_classes: list[str] = []
        self.fixture_items: list[int] = []
        self.trap_latencies: list[float] = []
        self.trap_items: list[int] = []
        self.latency_repeats = _checked_repeats(latency_repeats)
        self.module.load()

    # -- running ----------------------------------------------------------------
    def run_item(self, item: dict[str, Any], latencies: list[float] | None = None
                 ) -> tuple[ModuleOutput, AnalysisResult, set[str]]:
        extra = item.get("context", {})
        ctx = Context(
            text=item["text"],
            charsafe_text=extra.get("charsafe_text"),
            normalized_text=extra.get("normalized_text"),
            signals=deep_freeze(extra.get("signals", {})),
            trace_id=str(item.get("id", "")),
        )
        out = safe_process(self.module, ctx)
        # The scored run above doubles as a warm-up; only the repeats are timed.
        timings = [safe_process(self.module, ctx).latency_ms for _ in range(self.latency_repeats)]
        if latencies is None:
            index = len(set(self.fixture_items))
            self.fixture_latencies += timings
            self.fixture_lengths += [len(item["text"])] * len(timings)
            self.fixture_classes += [latency_class(item)] * len(timings)
            self.fixture_items += [index] * len(timings)
        else:
            index = len(set(self.trap_items))
            latencies += timings
            self.trap_items += [index] * len(timings)
        result = AnalysisResult(text=item["text"])
        problems = list(Pipeline._merge(result, out, self.module))
        # Same signal view the pipeline gives the decision layer, so signal-
        # conditioned thresholds resolve identically in eval and at inference -
        # including DEGRADATION: a stub, a failure or dropped output is degraded
        # here exactly as in Pipeline.analyze, so a result file can never show a
        # clean verdict for a module that did not run (Gate 1).
        result.signals.update(extra.get("signals", {}))
        result.signals[self.module.name.value] = out.signals
        degraded = degradation_record(self.module, out, problems)
        result.signals["pipeline"] = {"degraded": [degraded] if degraded else [],
                                      "emits_spans": span_declarations([self.module])}
        fusion.decide(result, self.config)
        predicted = {s.code.value for s in result.fired()}
        predicted |= {c.value for c in result.form.active}
        predicted |= {g.code.value for g in result.guards if g.active}
        if result.target is not None and result.target.type is not TargetType.NONE:
            predicted.add(f"target:{result.target.type.value}")
        return out, result, predicted

    @staticmethod
    def _expect_failures(item: dict[str, Any], out: ModuleOutput) -> list[str]:
        failures = []
        for field_name, wanted in item.get("expect", {}).items():
            got = getattr(out, field_name, None)
            if got is not None and got != wanted:
                failures.append(f"{field_name}: expected {wanted!r}, got {got!r}")
        return failures

    # -- statistics -----------------------------------------------------------------
    def _resamples(self, n: int) -> list[list[int]]:
        rng = random.Random(self.seed)
        return [[rng.randrange(n) for _ in range(n)] for _ in range(self.n_boot if n else 0)]

    def _interval(self, point: float | None, samples: list[float]) -> dict[str, Any]:
        tail = (1 - self.ci) / 2 * 100
        return {"value": point, "ci_low": percentile(samples, tail), "ci_high": percentile(samples, 100 - tail),
                "n_boot_defined": len(samples)}

    def per_code_metrics(self, rows: list[tuple[set[str], set[str]]], codes: list[str]) -> dict[str, Any]:
        """One entry per code in the fixed code list; the same item resamples are
        used for every code so their CIs are comparable."""
        resamples = self._resamples(len(rows))
        report: dict[str, Any] = {}
        for code in codes:
            cells = [Cells(tp=int(code in g and code in p), fp=int(code not in g and code in p),
                           fn=int(code in g and code not in p), tn=int(code not in g and code not in p))
                     for g, p in rows]
            total = Cells()
            for c in cells:
                total.add(c)
            point = total.metrics()
            samples: dict[str, list[float]] = {k: [] for k in point}
            for idx in resamples:
                agg = Cells()
                for i in idx:
                    agg.add(cells[i])
                for key, value in agg.metrics().items():
                    if value is not None:
                        samples[key].append(value)
            report[code] = {
                "support": total.tp + total.fn, "negatives": total.fp + total.tn,
                "tp": total.tp, "fp": total.fp, "fn": total.fn, "tn": total.tn,
                **{key: self._interval(point[key], samples[key]) for key in point},
            }
        return report

    def damage_rate(self, clean_rows: list[tuple[str, str, str | None]]) -> dict[str, Any]:
        """Share of clean items whose words changed beyond Turkish-aware case folding."""
        measurable = [(item_id, text, produced) for item_id, text, produced in clean_rows if produced is not None]
        flags = [int(tr_fold(produced).split() != tr_fold(text).split()) for _, text, produced in measurable]
        samples = [sum(flags[i] for i in idx) / len(idx) for idx in self._resamples(len(flags))]
        return {
            **self._interval(_ratio(sum(flags), len(flags)), samples),
            "n_clean": len(clean_rows), "n_measurable": len(measurable),
            "damaged_ids": [row[0] for row, flag in zip(measurable, flags) if flag],
            "note": None if clean_rows else "no fixture item has expect_clean: true",
        }

    # -- evaluation -------------------------------------------------------------------
    def evaluate(self) -> dict[str, Any]:
        items = load_jsonl(self.fixture_path)
        scored = [it for it in items if not it.get("placeholder")]
        codes = code_space(self.module)
        rows: list[tuple[set[str], set[str]]] = []
        expect_total, expect_failures, module_errors, out_of_space = 0, [], [], []
        representation_field = next((f for f in REPRESENTATION_FIELDS if f in self.module.provides), None)
        clean_rows: list[tuple[str, str, str | None]] = []
        degraded_items: list[dict[str, Any]] = []
        for item in scored:
            out, result, predicted = self.run_item(item)
            if not out.ok:
                module_errors.append({"id": item.get("id"), "notes": out.notes})
            for entry in result.signals["pipeline"]["degraded"]:
                degraded_items.append({"id": item.get("id"), "kinds": entry["kinds"]})
            gold = set(item.get("expected", item.get("expect_patterns", [])))
            unknown = sorted(gold - set(codes))
            if unknown:
                out_of_space.append({"id": item.get("id"), "codes": unknown})
            rows.append((gold, predicted))
            if item.get("expect"):
                expect_total += 1
                failures = self._expect_failures(item, out)
                if failures:
                    expect_failures.append({"id": item.get("id"), "failures": failures})
            if representation_field and item.get("expect_clean"):
                clean_rows.append((str(item.get("id")), item["text"], getattr(out, representation_field)))

        per_code = self.per_code_metrics(rows, codes)
        representation = None
        if representation_field:
            representation = {
                "field": representation_field,
                "capture_rate_per_pattern": {
                    code: {"support": per_code[code]["support"], **per_code[code]["recall"]}
                    for code in codes if code in FormCode.__members__
                },
                "damage_rate_on_clean": self.damage_rate(clean_rows),
            }

        traps = self.check_traps()
        budget = self.config["budgets"]["module_latency_p95_ms"].get(self.module.name.value)
        fixture_p95 = percentile(self.fixture_latencies, 95)
        status = implementation_status(self.module)
        return {
            "module": self.module.name.value,
            "version": self.module.version,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            # Gate 1: what this report's numbers cover, and which bytes produced them.
            "implementation": status,
            "degraded_items": {"n": len(degraded_items), "n_scored": len(scored), "items": degraded_items,
                               "note": "an item is degraded for the same reasons Pipeline.analyze degrades it; "
                                       "a stub degrades every item, so its per-code numbers verify nothing"},
            "provenance": provenance({"fixture": self.fixture_path, "traps": self.traps_path,
                                      "thresholds": fusion.DEFAULT_CONFIG_PATH,
                                      "implementation_status": IMPLEMENTATION_STATUS_PATH},
                                     traps_n=traps["n"], latency_repeats=self.latency_repeats,
                                     n_boot=self.n_boot),
            "fixture": (str(self.fixture_path.relative_to(ROOT)) if self.fixture_path.is_relative_to(ROOT)
                        else str(self.fixture_path)),
            "thresholds_artifact": self.config["artifact"]["id"],
            "thresholds_status": self.config["artifact"]["status"],
            # Same definition as the pipeline: config in use + the modules measured (here, one).
            "artifact_hash": artifact_hash(self.config, [self.module]),
            "n_items": len(items),
            "n_scored": len(scored),
            "n_placeholder": len(items) - len(scored),
            "codes": codes,
            "gold_codes_outside_code_space": out_of_space,
            "bootstrap": {"n_boot": self.n_boot, "ci": self.ci, "seed": self.seed, "unit": "item"},
            "per_code": per_code,
            "representation": representation,
            "expect": {"n": expect_total, "exact_match": _ratio(expect_total - len(expect_failures), expect_total),
                       "failures": expect_failures},
            "traps": traps,
            "latency": {
                "repeats": self.latency_repeats,
                "unit": "ms per timing; each item timed `repeats` times after its scored run",
                "fixture": {"n_items": len(set(self.fixture_items)), "n": len(self.fixture_latencies),
                            "p50_ms": percentile(self.fixture_latencies, 50), "p95_ms": fixture_p95},
                "traps": {"n_items": len(set(self.trap_items)), "n": len(self.trap_latencies),
                          "p50_ms": percentile(self.trap_latencies, 50),
                          "p95_ms": percentile(self.trap_latencies, 95)},
                **latency_report(self.fixture_latencies, self.fixture_lengths, self.fixture_classes, budget,
                                 self.fixture_items),
            },
            "module_errors": module_errors,
        }

    def check_traps(self) -> dict[str, Any]:
        """Traps assert what a module must and must not do on collision-prone text.

        Trap fields (eval/README.md):
          must_not_fire  content codes that must never FIRE, "*" = any (every module)
          expect         output fields that must match exactly, when produced
          form / guards  {"modules": [...], "must": [...], "must_not": [...]} on the
                         codes a listed module EMITS (before thresholds), "*" = any

        A "must" that a stub cannot meet yet is reported as pending, not as a
        regression; a stub still has to respect every "must_not".

        Gate 1 additions:
          binary         {"modules": [...], "must_not_fire": true} - the binary
                         offensive score (signals.decision.binary_offensive) must
                         not fire for a listed module; a listed module that
                         publishes no numeric score fails the rule outright.
          observations   one record per trap with the SEPARATE facts: content
                         fired, binary state, form / guard effects, degradation,
                         verdict and driver - so "0 regressions" can be read next
                         to "binary fired on N traps".
          binary_fired   ids of every trap whose binary score fired, whether or
                         not a rule asked about it. Which traps may carry a
                         `binary` rule is not decided (OPEN_QUESTIONS Q2, Q18),
                         so no committed trap has one yet; the list is the
                         observable fact the rule would assert on.
        """
        if not self.traps_path.exists():
            return {"n": 0, "regressions": 0, "failures": [], "pending": [], "binary_fired": [],
                    "binary_observable": False, "observations": [], "note": "traps file missing"}
        traps = load_jsonl(self.traps_path)
        name = self.module.name.value
        is_stub = bool(getattr(self.module, "stub", False))
        failures, pending, observations, fired_binary = [], [], [], []
        for trap in traps:
            out, result, _ = self.run_item(trap, latencies=self.trap_latencies)
            observed = observe(result, self.config)
            observations.append({"id": trap.get("id"), **observed})
            banned = set(trap.get("must_not_fire", ["*"]))
            fired = set(observed["content_fired"])
            hit = fired if "*" in banned else fired & banned
            problems = [f"fired {sorted(hit)}"] if hit else []
            problems += self._expect_failures(trap, out)
            emitted = {"form": {p.code.value for p in result.form.patterns},
                       "guards": {g.code.value for g in result.guards}}
            waiting = []
            for field_name, emitted_codes in emitted.items():
                rule = trap.get(field_name)
                if not rule or name not in rule.get("modules", []):
                    continue
                missing = sorted(set(rule.get("must", [])) - emitted_codes)
                if missing:
                    (waiting if is_stub else problems).append(f"{field_name}: expected {missing}")
                forbidden = set(rule.get("must_not", []))
                unwanted = sorted(emitted_codes if "*" in forbidden else emitted_codes & forbidden)
                if unwanted:
                    problems.append(f"{field_name}: must not emit {unwanted}")
            binary = observed["binary"]
            if binary is not None and binary["fired"]:
                fired_binary.append(trap.get("id"))
            rule = trap.get("binary")
            if rule and name in rule.get("modules", []):
                if binary is None or binary["fired"] is None:
                    problems.append("binary: no numeric score observed on any configured channel")
                elif rule.get("must_not_fire") and binary["fired"]:
                    problems.append(f"binary: fired {binary['channels']} at threshold {binary['threshold']}")
            if problems:
                failures.append({"id": trap.get("id"), "text": trap["text"], "problems": problems})
            if waiting:
                pending.append({"id": trap.get("id"), "text": trap["text"], "pending": waiting})
        return {"n": len(traps), "regressions": len(failures), "failures": failures, "pending": pending,
                "binary_fired": fired_binary,
                "binary_observable": any(o["binary"] is not None and o["binary"]["fired"] is not None
                                         for o in observations),
                "observations": observations,
                "checks": "content codes (must_not_fire), expect fields, emitted form patterns and guards, "
                          "binary rule where a trap names this module; binary_fired is reported for every trap"}

    def write(self, report: dict[str, Any]) -> Path:
        self.results_dir.mkdir(parents=True, exist_ok=True)
        path = self.results_dir / f"{report['module']}.json"
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return path


def _fmt(m: dict[str, Any]) -> str:
    if m["value"] is None:
        return "n/a"
    if m["ci_low"] is None:
        return f"{m['value']:.3f}"
    return f"{m['value']:.3f} [{m['ci_low']:.3f}, {m['ci_high']:.3f}]"


def summarize(report: dict[str, Any]) -> str:
    """Human summary: one line per code with support or predictions - never an average."""
    lat = report["latency"]
    p95 = "n/a" if lat["fixture"]["p95_ms"] is None else f"{lat['fixture']['p95_ms']:.3f}ms"
    status = report.get("implementation", {})
    traps = report["traps"]
    lines = [f"{report['module']} [{status.get('declared_status', '?')}]: scored={report['n_scored']} "
             f"placeholder={report['n_placeholder']} degraded_items={report.get('degraded_items', {}).get('n', '?')} "
             f"traps={traps['regressions']}/{traps['n']} pending={len(traps.get('pending', []))} "
             f"binary_fired={len(traps.get('binary_fired', []))}/{traps['n']}"
             f"{'' if traps.get('binary_observable') else ' (binary not observable for this module)'} "
             f"fixture_p95={p95} x{lat['repeats']} "
             f"within_budget(clean)={lat['within_budget']} adversarial_over_budget={lat['adversarial_over_budget']}"]
    if status and not status.get("behaviour_measurable", True):
        lines.append(f"  ** {status['scope']} **")
    elif status.get("not_built"):
        lines.append(f"  not_built (outside this measurement): {'; '.join(status['not_built'])}")
    for name in LATENCY_CLASSES:
        bands = " ".join(_band_text(b) for b in lat[name].get("budget_bands", []))
        if bands:
            lines.append(f"  latency[{name}] {bands}")
    for code, m in report["per_code"].items():
        if m["support"] or m["fp"]:
            lines.append(f"  {code:<22} support={m['support']:<3} recall={_fmt(m['recall'])} "
                         f"precision={_fmt(m['precision'])} f1={_fmt(m['f1'])} fpr={_fmt(m['fpr'])}")
    if len(lines) == 1:
        lines.append("  (no code has gold support or predictions on this fixture)")
    rep = report.get("representation")
    if rep:
        dmg = rep["damage_rate_on_clean"]
        lines.append(f"  damage_rate_on_clean({rep['field']})={_fmt(dmg)} n_clean={dmg['n_clean']}")
    return "\n".join(lines)


class NoNormalizedChannel:
    """Stands in for m2_deobf to measure what the normalized channel adds."""

    def __init__(self) -> None:
        self.name = ModuleName.M2_DEOBF
        self.version = "disabled-for-measurement"
        self.provides: frozenset[str] = frozenset()
        self.emits_spans = False

    def load(self) -> None:
        return None

    def process(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput()


def pipeline_budget_report(config: dict[str, Any] | None = None, traps_path: Path = TRAPS_PATH,
                           modules: list[Any] | None = None, texts: list[str] | None = None,
                           runs: int = DEFAULT_LATENCY_REPEATS) -> dict[str, Any]:
    """Pipeline-level budgets from thresholds.yaml.

    clean_to_dirty_flip_rate (m2 spec.md §8): share of traps with no fired content
    code when the normalized channel is disabled but a fired code when it is on.
    latency_p95_ms: whole-pipeline p95 over the trap texts and every module fixture.
    """
    cfg = config if config is not None else fusion.load_config()
    modules = modules if modules is not None else build_modules_safely()
    with_channel = Pipeline(modules=modules, config=cfg)
    without_channel = Pipeline(modules=[NoNormalizedChannel() if m.name is ModuleName.M2_DEOBF else m
                                        for m in modules], config=cfg)
    traps = load_jsonl(traps_path)
    with_runs = [(t, with_channel.analyze(t["text"])) for t in traps]
    without_runs = [without_channel.analyze(t["text"]) for t in traps]
    flips = [t.get("id") for (t, on), off in zip(with_runs, without_runs) if not off.fired() and on.fired()]
    flip_budget = cfg["budgets"]["clean_to_dirty_flip_rate"]
    flip_rate = _ratio(len(flips), len(traps))
    # Gate 1: the binary offensive score is verdict-relevant but not a content code,
    # so the budget above never sees it. Reported next to it, not folded in: the
    # budget's definition (m2 spec.md §8) is content codes, and whether a binary flip
    # counts is undecided (OPEN_QUESTIONS Q18).
    binary_flips = [t.get("id") for (t, on), off in zip(with_runs, without_runs)
                    if not binary_fired(off) and binary_fired(on)]
    trap_observations = [{"id": t.get("id"), **observe(on, cfg)} for t, on in with_runs]

    if texts is None:
        texts = [t["text"] for t in traps]
        for entry in registry.PIPELINE_ORDER:
            fixture = default_fixture(entry.name.value)
            if fixture.exists():
                texts += [i["text"] for i in load_jsonl(fixture) if not i.get("placeholder")]
    latencies = [with_channel.analyze(text).latency_ms for _ in range(_checked_repeats(runs)) for text in texts]
    latency_budget = cfg["budgets"]["latency_p95_ms"]
    p95 = percentile(latencies, 95)
    return {
        "clean_to_dirty_flip_rate": {
            "value": flip_rate, "flipped_trap_ids": flips, "n_traps": len(traps), "budget": flip_budget,
            "within_budget": None if flip_rate is None else flip_rate <= flip_budget,
        },
        "binary_offensive_on_traps": {
            "fired_with_channel_trap_ids": [o["id"] for o in trap_observations if o["binary"] and o["binary"]["fired"]],
            "flipped_by_channel_trap_ids": binary_flips,
            "n_traps": len(traps),
            "budgeted": False,
            "note": "reported, not budgeted: clean_to_dirty_flip_rate is defined on content codes (m2 spec §8)",
        },
        "trap_observations": trap_observations,
        "pipeline_latency": {
            "repeats": runs, "n_texts": len(texts),
            "n": len(latencies), "p50_ms": percentile(latencies, 50), "p95_ms": p95, "budget_p95_ms": latency_budget,
            "within_budget": None if p95 is None else p95 <= latency_budget,
        },
        "degraded_modules": sorted({d["module"] for _, on in with_runs for d in actions.degraded_modules(on)}),
        "provenance": provenance({"traps": Path(traps_path), "thresholds": fusion.DEFAULT_CONFIG_PATH,
                                  **{f"fixture:{entry.name.value}": default_fixture(entry.name.value)
                                     for entry in registry.PIPELINE_ORDER
                                     if default_fixture(entry.name.value).exists()}},
                                 traps_n=len(traps), latency_repeats=runs,
                                 modules=[f"{m.name.value}:{getattr(m, 'version', '')}" for m in modules]),
    }


def default_fixture(module_name: str) -> Path:
    # One name for every module (CONTRIBUTING.md, the specs): fixtures/cases.jsonl.
    return ROOT / "modules" / module_name / "fixtures" / "cases.jsonl"


def main_for(module_name: str, argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog=f"python -m modules.{module_name}.eval")
    parser.add_argument("--fixture", default=str(default_fixture(module_name)))
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--latency-repeats", type=int, default=DEFAULT_LATENCY_REPEATS,
                        help="timings per item for latency p50/p95 (recorded in the results)")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    evaluator = ModuleEvaluator(registry.build(module_name), Path(args.fixture), n_boot=args.n_boot,
                                latency_repeats=args.latency_repeats)
    report = evaluator.evaluate()
    print(summarize(report))
    if not args.no_write:
        print(f"wrote {evaluator.write(report).relative_to(ROOT)} (git-ignored; see eval/README.md)")
    return 1 if report["traps"]["regressions"] else 0
