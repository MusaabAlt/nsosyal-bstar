"""Functional / demo scenario runner for the FROZEN NSosyal pipeline. EVALUATION ONLY.

What it does
  * builds the REAL pipeline (pipeline.run.Pipeline, registry order m0 -> m2 -> m6 -> m1 -> m3 -> m4 -> m5,
    decision/thresholds.yaml as committed) - no mock, no alternative config, no threshold of its own;
  * identifies the M3 artifact actually loaded (path + weights sha256) BEFORE any scenario and says
    whether it is the Rule-v4 artifact; M3-dependent scenarios are BLOCKED when it is not;
  * runs every scenario of demo_scenarios.jsonl through Pipeline.analyze and evaluates its checks;
  * writes demo_scenario_report.json, demo_scenario_report.md and demo_scenario_traces.txt under
    AI/eval/results/.

Observation, not modification: to show each module's own output (charsafe / normalized text, m1's
private `_matches`), `pipeline.run.safe_process` is wrapped by a pass-through recorder that calls the
original function and returns ITS ModuleOutput object unchanged; the result judged is exactly what
Pipeline.analyze returns.

Checks (keys of a scenario's `expected`, `expected_module_signals` and `ideal`):
  rule_fired_exact / _include / _any / _exclude  codes that FIRED (after thresholds, guards, family-A
      assignment) among the channel scores of the deterministic rule modules m1_lexicon and m6_target
      (signals.decision.channel_scores). "A" / "B" / "C" / "D" expand to the family. Independent of the
      M3 artifact: m3's own scores are judged only by the `m3` block.
  rule_suppressed_include   a rule-module code that was scored but did not fire (suppressed)
  guards_active_include     guard codes the decision layer made active
  guard_suppressed          [[guard, code], ...] - that guard suppressed that code
  verdict_min               the verdict is at least this severe (block > escalate > review > nudge > clean)
  fired_any                 some fused content code of ANY module fired (used for ideals: C1-C5, D1)
  allow_degraded            a module other than the declared m5 stub may degrade (malformed input)
  m0 / m2                   charsafe_text / normalized_text equality, form codes the module EMITTED
  m6                        published target type
  m1                        roots / routes / family-A roots of m1's matches, collision guard, lexicon_hit
  m3_truncated              m3 noted a truncation (tokenizer fact, artifact independent)
  m4                        c_family_note, binary_consistent (stage-1 mechanics of binary_offensive)
  m5                        stub_degraded (m5 declared stub, emits nothing, degrades the result)
  m3                        binary_offensive_fired, a_head_fired - M3-DEPENDENT: evaluated only when the
                            exact Rule-v4 artifact is loaded, otherwise reported as BLOCKED

Result classes: PASS, FAIL, KNOWN_LIMITATION, NOT_IMPLEMENTED, BLOCKED, EXPECTATION_INVALID. A FAIL is
classified after inspection in failure_review.json (never by changing an expectation); a FAIL whose
review says EXPECTATION_WRONG is reported as EXPECTATION_INVALID with the original expectation kept.
PASS / total is a FUNCTIONAL SCENARIO PASS RATE, not model accuracy.

Usage (from AI/, with AI/.venv):
  python eval/scenarios/run_demo_scenarios.py [--unittest-log PATH] [--warm-repeats N] [--verbose]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import statistics
import subprocess
import sys
import time
import traceback
import unicodedata
from importlib import metadata
from pathlib import Path
from typing import Any

AI_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

HERE = Path(__file__).resolve().parent
RESULTS = AI_ROOT / "eval" / "results"
SCENARIOS = HERE / "demo_scenarios.jsonl"
REVIEW = HERE / "failure_review.json"
ANALYSIS = HERE / "report_analysis.md"

# The frozen Rule-v4 run the task names (docs/training/m3_rule_v4_handoff.md §4 naming).
RULE_V4_RUN_ID = "rule-v4-20260918-163728"
RULE_V4_ARTIFACT_ID = "m3-berturk-multihead-a-rule-v4-20260918-163728"
RULE_V4_WEIGHTS_SHA256 = "dc7fe3062b33938ccbb78b632947bf254ad72e60104e163c64830bb95f0d0b76"
RULE_V4_DRIVE_DIR = (f"/content/drive/MyDrive/nsosyal-train/runs/m3_multihead/{RULE_V4_RUN_ID}/artifact/"
                     f"{RULE_V4_ARTIFACT_ID}/")

RULE_MODULES = ("m1_lexicon", "m6_target")
FAMILIES = {"A": ("A1", "A2", "A3", "A4"), "B": ("B1", "B2", "B3", "B4", "B5"),
            "C": ("C1", "C2", "C3", "C4", "C5"), "D": ("D1",)}
RESULT_CLASSES = ("PASS", "FAIL", "KNOWN_LIMITATION", "NOT_IMPLEMENTED", "BLOCKED", "EXPECTATION_INVALID")
FAIL_CLASSES = ("PRODUCTION_BUG", "EXPECTATION_WRONG", "KNOWN_LIMITATION", "DEMO_BLOCKER",
                "ARTIFACT/CONFIGURATION_PROBLEM", "UNCLEAR_NEEDS_REVIEW")


# ------------------------------------------------------------------------------------------------
# small helpers
# ------------------------------------------------------------------------------------------------
_INVISIBLE = set("\u115f\u1160\u3164\uffa0\u2800")


def _escape(ch: str) -> str:
    units = ch.encode("utf-16-le", "surrogatepass")
    return "".join("\\u%04x" % int.from_bytes(units[k:k + 2], "little") for k in range(0, len(units), 2))


def visible(text: str) -> str:
    """Text with invisible / control / combining / surrogate characters written as \\u escapes."""
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        if ch == "\n":
            out.append("\\n")
        elif ch == "\t":
            out.append("\\t")
        elif cat in ("Cc", "Cf", "Cs", "Co", "Cn", "Mn", "Me", "Zl", "Zp") or (cat == "Zs" and ch != " ") \
                or ch in _INVISIBLE:
            out.append(_escape(ch))
        else:
            out.append(ch)
    return "".join(out)


def safe_json(obj: Any, indent: int | None = None) -> str:
    """JSON text that is always UTF-8 encodable (lone surrogates escaped)."""
    raw = json.dumps(obj, ensure_ascii=False, indent=indent, default=str)
    return "".join(_escape(ch) if unicodedata.category(ch) == "Cs" else ch for ch in raw)


def short(text: str, limit: int) -> str:
    text = visible(text)
    return text if len(text) <= limit else text[:limit] + f"... [{len(text)} chars]"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=AI_ROOT, capture_output=True, text=True, encoding="utf-8",
                              check=False).stdout.strip()
    except OSError as exc:
        return f"<git unavailable: {exc}>"


def version_of(dist: str) -> str:
    try:
        return metadata.version(dist)
    except metadata.PackageNotFoundError:
        return "not installed"


def expand(codes: list[str]) -> set[str]:
    out: set[str] = set()
    for code in codes:
        out.update(FAMILIES.get(code, (code,)))
    return out


def percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(round(q * (len(ordered) - 1))))]


def ms_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"n": 0}
    return {"n": len(values), "mean": round(statistics.fmean(values), 1), "p50": round(percentile(values, 0.5), 1),
            "p95": round(percentile(values, 0.95), 1), "max": round(max(values), 1), "min": round(min(values), 1)}


# ------------------------------------------------------------------------------------------------
# recording wrapper (pass-through)
# ------------------------------------------------------------------------------------------------
class Recorder:
    def __init__(self, prun: Any) -> None:
        from contracts.schema import to_jsonable
        self._to_jsonable = to_jsonable
        self.outputs: dict[str, dict[str, Any]] = {}
        self._original = prun.safe_process
        recorder = self

        def recording_safe_process(module: Any, ctx: Any) -> Any:
            out = recorder._original(module, ctx)
            recorder.outputs[module.name.value] = recorder.snapshot(out)
            return out          # the very object the pipeline would have received

        prun.safe_process = recording_safe_process

    def snapshot(self, out: Any) -> dict[str, Any]:
        signals = out.signals if isinstance(out.signals, dict) else {}
        kept = {k: v for k, v in signals.items() if k != "_offsets"}
        return {
            "ok": out.ok, "version": out.version, "latency_ms": out.latency_ms, "notes": list(out.notes),
            "charsafe_text": out.charsafe_text, "normalized_text": out.normalized_text,
            "form": [self._to_jsonable(p) for p in (out.form.patterns if out.form is not None else [])],
            "content": [self._to_jsonable(s) for s in out.content],
            "guards": [self._to_jsonable(g) for g in out.guards],
            "target": self._to_jsonable(out.target) if out.target is not None else None,
            "signals": self._to_jsonable(kept),
        }


# ------------------------------------------------------------------------------------------------
# M3 artifact identification
# ------------------------------------------------------------------------------------------------
def identify_m3(pipeline: Any) -> dict[str, Any]:
    import modules.m3_encoder.module as m3mod
    module = next((m for m in pipeline.modules if m.name.value == "m3_encoder"), None)
    info: dict[str, Any] = {
        "env": {k: os.environ.get(k) for k in (m3mod.MULTIHEAD_ENV, m3mod.CHECKPOINT_ENV, m3mod.TOKENIZER_ENV)},
        "module_class": type(module).__name__ if module is not None else None,
        "load_error": getattr(module, "_load_error", None) or getattr(module, "error", None),
    }
    multihead = m3mod.multihead_dir()
    if module is None or info["load_error"]:
        info.update({"loaded": False, "artifact_id": None, "kind": None, "weights_path": None, "weights_sha256": None})
    elif multihead is not None:
        weights = multihead / "weights.pt"
        heads = getattr(module, "_heads", None) or {}
        info.update({"loaded": True, "kind": "multi-head", "artifact_id": getattr(module, "_artifact_id", None),
                     "artifact_dir": str(multihead), "weights_path": str(weights),
                     "weights_sha256": sha256_file(weights) if weights.is_file() else None,
                     "trained_heads": {k: v.get("trained") for k, v in (heads.get("heads") or {}).items()}})
    else:
        checkpoint, tokenizer = m3mod.artifact_paths()
        info.update({"loaded": True, "kind": "binary-only baseline checkpoint",
                     "artifact_id": getattr(module, "_artifact_id", None), "weights_path": str(checkpoint.resolve()),
                     "tokenizer_dir": str(tokenizer.resolve()),
                     "weights_sha256": sha256_file(checkpoint) if checkpoint.is_file() else None,
                     "trained_heads": {"binary": True, "a": False, "b": False, "c": False}})
    info["is_rule_v4"] = bool(info.get("loaded") and info.get("artifact_id") == RULE_V4_ARTIFACT_ID
                              and info.get("weights_sha256") == RULE_V4_WEIGHTS_SHA256)
    info["rule_v4_expected"] = {
        "artifact_id": RULE_V4_ARTIFACT_ID, "weights_sha256": RULE_V4_WEIGHTS_SHA256, "run_id": RULE_V4_RUN_ID,
        "how_the_runtime_loads_it": f"environment variable {m3mod.MULTIHEAD_ENV}=<artifact directory> "
                                    "(modules/m3_encoder/module.py::multihead_dir); the directory must hold "
                                    "weights.pt, heads.json, config.json, tokenizer.json, tokenizer_config.json and "
                                    "sha256.txt (every listed file is sha256-verified before use)",
        "where_it_was_written": RULE_V4_DRIVE_DIR,
        "default_without_env": str(m3mod.DEFAULT_CHECKPOINT) + " (binary-only baseline " + m3mod.ARTIFACT_ID + ")",
    }
    return info


# ------------------------------------------------------------------------------------------------
# evaluation of one scenario
# ------------------------------------------------------------------------------------------------
class Facts:
    """Everything the checks read, extracted once from the result and the recorded module outputs."""

    def __init__(self, result: Any, outputs: dict[str, dict[str, Any]], cfg: dict[str, Any]) -> None:
        from decision import actions, fusion
        self.result = result
        self.outputs = outputs
        decision = result.signals.get("decision", {}) or {}
        self.channel_scores = decision.get("channel_scores") or []
        rule = [c for c in self.channel_scores if fusion.module_of(c["source"]) in RULE_MODULES]
        self.rule_fired = sorted({c["code"] for c in rule if c.get("fired")})
        self.rule_scored = sorted({c["code"] for c in rule})
        m3 = [c for c in self.channel_scores if fusion.module_of(c["source"]) == "m3_encoder"]
        self.m3_fired = sorted({c["code"] for c in m3 if c.get("fired")})
        self.all_fired = sorted({s.code.value for s in result.fired()})
        self.guards_active = sorted({g.code.value for g in result.guards if g.active})
        self.guard_suppression = sorted({(g.code.value, c.value) for g in result.guards for c in g.suppressed})
        self.binary = decision.get("binary_offensive") or {}
        self.verdict = result.verdict.value if result.verdict is not None else None
        try:
            _, driver = actions.resolve(result, cfg)
            self.driver = driver.code.value if hasattr(driver, "code") else driver
        except Exception as exc:        # a trace must still be written
            self.driver = f"<resolve failed: {exc}>"
        self.degraded = result.signals.get("pipeline", {}).get("degraded") or []
        m1 = outputs.get("m1_lexicon", {})
        self.m1_matches = (m1.get("signals") or {}).get("_matches") or []
        self.m6_target = (result.signals.get("m6_target") or {}).get("target_type")
        self.notes = list(result.notes)


def severity_index(action: str) -> int:
    from contracts.codes import ACTION_PRECEDENCE, Action
    return ACTION_PRECEDENCE.index(Action(action))


def check_block(block: dict[str, Any], facts: Facts, cfg: dict[str, Any]) -> list[tuple[str, bool, str]]:
    """Evaluate one expectation block. Returns (check name, passed, detail). `m3` is not handled here."""
    out: list[tuple[str, bool, str]] = []
    rf = set(facts.rule_fired)
    for key, want in block.items():
        if key == "rule_fired_exact":
            out.append((key, rf == set(want), f"rule fired {sorted(rf)} vs expected exactly {sorted(want)}"))
        elif key == "rule_fired_include":
            out.append((key, set(want) <= rf, f"rule fired {sorted(rf)} must include {sorted(want)}"))
        elif key == "rule_fired_any":
            out.append((key, bool(set(want) & rf), f"rule fired {sorted(rf)} must include one of {sorted(want)}"))
        elif key == "rule_fired_exclude":
            bad = expand(want) & rf
            out.append((key, not bad, f"rule fired {sorted(rf)} must exclude {sorted(want)}"))
        elif key == "rule_suppressed_include":
            ok = all(c in facts.rule_scored and c not in rf for c in want)
            out.append((key, ok, f"scored {facts.rule_scored}, fired {sorted(rf)}: {want} must be scored but suppressed"))
        elif key == "guards_active_include":
            out.append((key, set(want) <= set(facts.guards_active), f"active guards {facts.guards_active}"))
        elif key == "guard_suppressed":
            pairs = {tuple(p) for p in want}
            out.append((key, pairs <= set(facts.guard_suppression),
                        f"guard suppressions {sorted(facts.guard_suppression)} must include {sorted(pairs)}"))
        elif key == "verdict_min":
            ok = facts.verdict is not None and severity_index(facts.verdict) <= severity_index(want)
            out.append((key, ok, f"verdict {facts.verdict} must be at least {want}"))
        elif key == "verdict_in":
            out.append((key, facts.verdict in want, f"verdict {facts.verdict} in {want}"))
        elif key == "fired_any":
            out.append((key, bool(set(want) & set(facts.all_fired)), f"all fired {facts.all_fired} vs any of {want}"))
        elif key in ("no_crash", "allow_degraded"):
            continue
        elif key == "m0":
            out += module_text_checks("m0", facts.outputs.get("m0_charsafe", {}), want, "charsafe_text")
        elif key == "m2":
            out += module_text_checks("m2", facts.outputs.get("m2_deobf", {}), want, "normalized_text")
        elif key == "m6":
            got = facts.m6_target
            if "target_type" in want:
                out.append(("m6.target_type", got == want["target_type"], f"target {got} vs {want['target_type']}"))
        elif key == "m1":
            out += m1_checks(want, facts)
        elif key == "m3_truncated":
            got = any(n.startswith("[m3_encoder] truncated") for n in facts.notes)
            out.append((key, got == want, f"m3 truncation note present: {got}"))
        elif key == "m4":
            out += m4_checks(want, facts, cfg)
        elif key == "m5":
            m5 = [d for d in facts.degraded if d.get("module") == "m5_sarcasm"]
            ok = bool(m5) and m5[0].get("kinds") == ["stub"] and not facts.outputs.get("m5_sarcasm", {}).get("content")
            out.append(("m5.stub_degraded", ok == want.get("stub_degraded", True), f"m5 degraded entry {m5}"))
        elif key == "m3":
            continue
        else:
            out.append((key, False, f"unknown check key {key!r} (runner vocabulary)"))
    return out


def module_text_checks(name: str, out: dict[str, Any], want: dict[str, Any], text_key: str) -> list[tuple[str, bool, str]]:
    checks = []
    forms = [p["code"] for p in out.get("form", [])]
    for key, value in want.items():
        if key in ("charsafe_text", "normalized_text"):
            got = out.get(text_key)
            checks.append((f"{name}.{key}", got == value, f"{key} {visible(str(got))!r} vs {visible(value)!r}"))
        elif key == "form_include":
            checks.append((f"{name}.form_include", set(value) <= set(forms), f"{name} forms {forms} must include {value}"))
        elif key == "form_exclude":
            checks.append((f"{name}.form_exclude", not (set(value) & set(forms)), f"{name} forms {forms} must exclude {value}"))
        elif key in ("changed", "charsafe_changed"):
            got = (out.get("signals") or {}).get(key)
            checks.append((f"{name}.{key}", got == value, f"{key} {got}"))
        else:
            checks.append((f"{name}.{key}", False, f"unknown {name} check {key!r}"))
    return checks


def m1_checks(want: dict[str, Any], facts: Facts) -> list[tuple[str, bool, str]]:
    roots = sorted({m["root"] for m in facts.m1_matches})
    routes = sorted({m["route"] for m in facts.m1_matches})
    fam_a = sorted({m["root"] for m in facts.m1_matches if m["route"] == "A"})
    route_set = set(routes) | ({"A1", "A2", "A3"} if "A" in routes else set())
    checks = []
    for key, value in want.items():
        if key == "roots_include":
            checks.append(("m1.roots_include", set(value) <= set(roots), f"m1 roots {roots} must include {value}"))
        elif key == "roots_exclude":
            checks.append(("m1.roots_exclude", not (set(value) & set(roots)), f"m1 roots {roots} must exclude {value}"))
        elif key == "routes_include":
            checks.append(("m1.routes_include", set(value) <= set(routes), f"m1 routes {routes} must include {value}"))
        elif key == "routes_exclude":
            checks.append(("m1.routes_exclude", not (set(value) & route_set), f"m1 routes {routes} must exclude {value}"))
        elif key == "family_a_roots_exact":
            checks.append(("m1.family_a_roots_exact", fam_a == sorted(value), f"m1 family-A roots {fam_a} vs {value}"))
        elif key == "family_a_roots_include":
            checks.append(("m1.family_a_roots_include", set(value) <= set(fam_a),
                           f"m1 family-A roots {fam_a} must include {value}"))
        elif key == "collision":
            got = any(g.code.value == "SUBSTRING_COLLISION" and g.source.startswith("m1_lexicon")
                      for g in facts.result.guards)
            checks.append(("m1.collision", got == value, f"SUBSTRING_COLLISION present: {got}"))
        elif key == "lexicon_hit":
            got = (facts.result.signals.get("m1_lexicon") or {}).get("lexicon_hit")
            checks.append(("m1.lexicon_hit", got == value, f"lexicon_hit {got}"))
        else:
            checks.append((f"m1.{key}", False, f"unknown m1 check {key!r}"))
    return checks


def m4_checks(want: dict[str, Any], facts: Facts, cfg: dict[str, Any]) -> list[tuple[str, bool, str]]:
    checks = []
    if "c_family_note" in want:
        got = any(n.startswith("[m4_implicit] C1") for n in facts.notes)
        checks.append(("m4.c_family_note", got == want["c_family_note"], "m4 note 'C1-C5 not implemented yet' present"))
    if want.get("binary_consistent"):
        b, entry = facts.binary, cfg.get("binary_offensive") or {}
        raw = (b.get("channels") or {}).get("raw") or {}
        score = (facts.result.signals.get("m3_encoder") or {}).get("raw_score")
        configured = float(entry.get("threshold")) if entry else None
        problems = []
        if b.get("threshold") != configured:
            problems.append(f"threshold {b.get('threshold')} != configured {configured}")
        if b.get("branch") != "scalar":
            problems.append(f"branch {b.get('branch')} (stage 1 is the scalar global threshold)")
        if set((b.get("channels") or {})) != {"raw"}:
            problems.append(f"channels {sorted(b.get('channels') or {})} (stage 1 is raw-only)")
        if raw.get("score") != score:
            problems.append(f"raw score {raw.get('score')} != m3 raw_score {score}")
        if score is not None and configured is not None and raw.get("fired") != (score > configured):
            problems.append("fired != (score > threshold)")
        if b.get("fired") != raw.get("fired"):
            problems.append("post-level fired != raw channel fired")
        if b.get("action") != entry.get("action"):
            problems.append(f"action {b.get('action')} != configured {entry.get('action')}")
        checks.append(("m4.binary_consistent", not problems, "; ".join(problems) or
                       f"score {score} threshold {configured} fired {b.get('fired')} action {b.get('action')}"))
    return checks


def m3_checks(want: dict[str, Any], facts: Facts) -> list[tuple[str, bool, str]]:
    checks = []
    if "binary_offensive_fired" in want:
        got = facts.binary.get("fired")
        checks.append(("m3.binary_offensive_fired", got == want["binary_offensive_fired"], f"binary_offensive fired {got}"))
    if "a_head_fired" in want:
        got = bool(set(facts.m3_fired) & set(FAMILIES["A"]))
        checks.append(("m3.a_head_fired", got == want["a_head_fired"], f"m3 fired codes {facts.m3_fired}"))
    return checks


def health_checks(scenario: dict[str, Any], facts: Facts) -> list[tuple[str, bool, str]]:
    checks = [("health.verdict_present", facts.verdict is not None, f"verdict {facts.verdict}")]
    allow = scenario["expected"].get("allow_degraded", False)
    degraded = [(d.get("module"), tuple(d.get("kinds") or [])) for d in facts.degraded]
    if not allow:
        checks.append(("health.only_declared_stub_degraded", degraded == [("m5_sarcasm", ("stub",))],
                       f"degraded {degraded}"))
    try:
        json.dumps(facts.result.to_dict(), ensure_ascii=True)
        checks.append(("health.serialisable", True, "to_dict() is JSON-serialisable"))
    except Exception as exc:
        checks.append(("health.serialisable", False, f"{type(exc).__name__}: {exc}"))
    return checks


def evaluate(scenario: dict[str, Any], facts: Facts | None, crash: str | None, cfg: dict[str, Any],
             rule_v4: bool) -> dict[str, Any]:
    status = scenario["supported_status"]
    if crash is not None:
        return {"result": "FAIL", "raw_result": "FAIL", "checks": [["crash", False, crash]], "m3_checks": [],
                "m3_status": "not evaluated", "ideal_met": None, "documented_met": None, "blocked_reason": None}
    assert facts is not None
    health = health_checks(scenario, facts)
    main = check_block(scenario["expected"], facts, cfg) + check_block(
        {k: v for k, v in scenario["expected_module_signals"].items() if k != "m3"}, facts, cfg)
    m3_want = scenario["expected_module_signals"].get("m3") or {}
    m3 = m3_checks(m3_want, facts) if (rule_v4 and m3_want) else []
    m3_status = ("evaluated" if m3 else "no expectation") if (rule_v4 or not m3_want) else "BLOCKED_ARTIFACT_NOT_LOCAL"
    ideal = check_block(scenario["ideal"], facts, cfg) if scenario["ideal"] else []
    ideal_met = all(ok for _, ok, _ in ideal) if ideal else None
    health_ok = all(ok for _, ok, _ in health)
    main_ok = all(ok for _, ok, _ in main)
    blocked_reason = None
    if not health_ok:
        result = "FAIL"
    elif status == "SUPPORTED":
        result = "PASS" if main_ok and all(ok for _, ok, _ in m3) else "FAIL"
    elif status == "LIMITATION":
        result = "KNOWN_LIMITATION"
    elif status == "NOT_IMPLEMENTED":
        result = "NOT_IMPLEMENTED"
    elif status == "M3_DEPENDENT":
        if rule_v4:
            result = "PASS" if all(ok for _, ok, _ in m3 + main) else "FAIL"
        else:
            result, blocked_reason = "BLOCKED", "BLOCKED_ARTIFACT_NOT_LOCAL"
    else:
        result = "FAIL"
    checks = health + main
    documented_met = (main_ok if status in ("LIMITATION", "NOT_IMPLEMENTED") and main else None)
    return {"result": result, "raw_result": result, "checks": [list(c) for c in checks], "m3_checks": [list(c) for c in m3],
            "m3_status": m3_status, "ideal_checks": [list(c) for c in ideal], "ideal_met": ideal_met,
            "documented_met": documented_met, "blocked_reason": blocked_reason}


# ------------------------------------------------------------------------------------------------
# trace
# ------------------------------------------------------------------------------------------------
def build_trace(scenario: dict[str, Any], facts: Facts | None, m3info: dict[str, Any], latency: float | None) -> dict[str, Any]:
    if facts is None:
        return {}
    o = facts.outputs
    m0, m2, m6, m1, m3, m4, m5 = (o.get(k, {}) for k in ("m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon",
                                                         "m3_encoder", "m4_implicit", "m5_sarcasm"))
    text = facts.result.text
    target = facts.result.target
    m3sig = facts.result.signals.get("m3_encoder") or {}
    return {
        "M0": {"charsafe_text": m0.get("charsafe_text"), "forms": [(p["code"], p["confidence"], p["evidence"]) for p in m0.get("form", [])],
               "signals": {k: v for k, v in (m0.get("signals") or {}).items() if not k.startswith("_")}, "ok": m0.get("ok")},
        "M2": {"normalized_text": m2.get("normalized_text"),
               "forms": [(p["code"], p["confidence"], p["evidence"]) for p in m2.get("form", [])],
               "repairs": (m2.get("signals") or {}).get("_repairs"), "tier2_enabled": (m2.get("signals") or {}).get("tier2_enabled"),
               "notes": m2.get("notes"), "ok": m2.get("ok")},
        "M6": {"target": None if target is None else {"type": target.type.value, "confidence": target.confidence,
                                                      "evidence": target.evidence, "span": target.span},
               "how": ((facts.result.signals.get("m6_target") or {}).get("target_evidence") or {}).get("how"),
               "b4": [(s["code"], s["score"], text[s["span"][0]:s["span"][1]]) for s in m6.get("content", [])],
               "ok": m6.get("ok")},
        "M1": {"matches": [(m["root"], m["route"], m["channel"], text[m["span"][0]:m["span"][1]]) for m in facts.m1_matches],
               "content": [(s["code"], s["source"], s["span"]) for s in m1.get("content", [])],
               "guards": [(g["code"], g["evidence"], g["span"]) for g in m1.get("guards", [])],
               "lexicon_hit": (facts.result.signals.get("m1_lexicon") or {}).get("lexicon_hit"), "ok": m1.get("ok")},
        "M3": {"artifact": m3sig.get("artifact"),
               "artifact_note": ("Rule-v4 (" + RULE_V4_ARTIFACT_ID + ")") if m3info.get("is_rule_v4") else
               "NOT Rule-v4: " + str(m3info.get("artifact_id")) + " (" + str(m3info.get("kind")) + ") - scores informational only",
               "binary_probability_raw": m3sig.get("raw_score"), "binary_probability_normalized": m3sig.get("norm_score"),
               "a_probability": [(s["code"], s["score"], s["source"]) for s in m3.get("content", []) if s["code"] in FAMILIES["A"]] or
               ("n/a: the loaded artifact has no trained A head" if not m3info.get("trained_heads", {}).get("a") else []),
               "other_head_scores": [(s["code"], s["score"], s["source"]) for s in m3.get("content", []) if s["code"] not in FAMILIES["A"]],
               "notes": m3.get("notes"), "ok": m3.get("ok")},
        "M4": {"notes": m4.get("notes"), "content": m4.get("content"),
               "stage": "stage 1 only: binary_offensive threshold applied by the decision layer; stage 2 (C1-C5) not built"},
        "M5": {"status": "NOT_IMPLEMENTED (declared stub)", "notes": m5.get("notes"), "content": m5.get("content")},
        "DECISION": {"verdict": facts.verdict, "driver": facts.driver, "fired_codes_all_modules": facts.all_fired,
                     "rule_fired": facts.rule_fired, "m3_fired": facts.m3_fired,
                     "channel_scores": [(c["code"], c["source"], round(c["score"], 4), c.get("fired")) for c in facts.channel_scores],
                     "guards_active": facts.guards_active, "guard_suppressions": facts.guard_suppression,
                     "binary_offensive": {"score": ((facts.binary.get("channels") or {}).get("raw") or {}).get("score"),
                                          "threshold": facts.binary.get("threshold"), "fired": facts.binary.get("fired"),
                                          "action": facts.binary.get("action")},
                     "family_a": (facts.result.signals.get("decision") or {}).get("family_a"),
                     "degraded": [(d.get("module"), d.get("kinds")) for d in facts.degraded],
                     "explanation": facts.result.explanation, "latency_ms": None if latency is None else round(latency, 1)},
    }


def trace_text(row: dict[str, Any]) -> str:
    t, ev = row["trace"], row["evaluation"]
    lines = [f"CASE_ID: {row['case_id']}", f"CATEGORY: {row['category']} / {row['subcategory']}",
             f"STATUS: {row['supported_status']}", f"INPUT: {short(row['text'], 400)!r}",
             f"EXPECTED: {safe_json(row['expected'])}  MODULE: {safe_json(row['expected_module_signals'])}"]
    if row.get("ideal"):
        lines.append(f"IDEAL (limitation/not-implemented): {safe_json(row['ideal'])}")
    if not t:
        lines.append("ACTUAL: <no result - see RESULT>")
    else:
        lines.append("ACTUAL:")
        lines.append(f"  M0: charsafe={short(str(t['M0']['charsafe_text']), 160)!r} forms={t['M0']['forms']} {t['M0']['signals']}")
        lines.append(f"  M2: normalized={short(str(t['M2']['normalized_text']), 160)!r} forms={t['M2']['forms']} "
                     f"repairs={t['M2']['repairs']}")
        lines.append(f"  M6: target={t['M6']['target']} how={t['M6']['how']} B4={t['M6']['b4']}")
        lines.append(f"  M1: matches={t['M1']['matches']} content={t['M1']['content']}")
        lines.append(f"      guards={t['M1']['guards']}")
        lines.append(f"  M3: {t['M3']['artifact_note']}; binary p(raw)={t['M3']['binary_probability_raw']} "
                     f"p(norm)={t['M3']['binary_probability_normalized']}; A={t['M3']['a_probability']} notes={t['M3']['notes']}")
        lines.append(f"  M4: {t['M4']['notes']} ({t['M4']['stage']})")
        lines.append(f"  M5: {t['M5']['status']} notes={t['M5']['notes']}")
        d = t["DECISION"]
        lines.append(f"DECISION: verdict={d['verdict']} driver={d['driver']} rule_fired={d['rule_fired']} "
                     f"all_fired={d['fired_codes_all_modules']} guards_active={d['guards_active']} "
                     f"suppressions={d['guard_suppressions']}")
        lines.append(f"  binary_offensive={d['binary_offensive']} degraded={d['degraded']} latency_ms={d['latency_ms']}")
        lines.append(f"  explanation: {d['explanation']}")
    lines.append(f"RESULT: {ev['result']}" + (f" ({ev['blocked_reason']})" if ev.get("blocked_reason") else "")
                 + (f" [raw {ev['raw_result']}; review: {ev.get('review_classification')}]" if ev.get("review_classification") else ""))
    failed = [c for c in ev["checks"] if not c[1]]
    if failed:
        lines.append("FAILED CHECKS: " + " | ".join(f"{c[0]}: {c[2]}" for c in failed))
    if ev.get("ideal_met") is not None:
        lines.append(f"IDEAL MET: {ev['ideal_met']}  DOCUMENTED BEHAVIOUR MET: {ev.get('documented_met')}")
    if ev.get("m3_status") not in (None, "no expectation"):
        lines.append(f"M3 CHECKS: {ev['m3_status']} {ev.get('m3_checks') or ''}")
    lines.append(f"NOTES: {row['notes']}")
    return "\n".join(lines)


# ------------------------------------------------------------------------------------------------
# main
# ------------------------------------------------------------------------------------------------
def parse_unittest_log(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file():
        return {"available": False}
    text = path.read_text(encoding="utf-8", errors="replace")
    import re
    ran = re.search(r"^Ran (\d+) tests? in ([\d.]+)s", text, re.M)
    status = re.search(r"^(OK|FAILED)(?: \((.*)\))?\s*$", text, re.M)
    details = dict(kv.split("=") for kv in (status.group(2) or "").split(", ") if "=" in kv) if status else {}
    total = int(ran.group(1)) if ran else None
    failures, errors, skipped = (int(details.get(k, 0)) for k in ("failures", "errors", "skipped"))
    return {"available": True, "log": str(path), "ran": total, "seconds": float(ran.group(2)) if ran else None,
            "status": status.group(1) if status else None, "failures": failures, "errors": errors, "skipped": skipped,
            "passed": None if total is None else total - failures - errors - skipped}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--scenarios", type=Path, default=SCENARIOS)
    parser.add_argument("--unittest-log", type=Path, default=None)
    parser.add_argument("--warm-repeats", type=int, default=5)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--render-only", action="store_true",
                        help="rewrite demo_scenario_report.md from the existing JSON report (no inference)")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    if args.render_only:
        report = json.loads((RESULTS / "demo_scenario_report.json").read_text(encoding="utf-8"))
        rows = report["cases"]
        fails = [r for r in rows if r["evaluation"]["raw_result"] == "FAIL"]
        demo_rows = [r for r in rows if r.get("demo_critical")]
        (RESULTS / "demo_scenario_report.md").write_text(render_md(report, rows, fails, demo_rows), encoding="utf-8")
        print(f"[out] {RESULTS / 'demo_scenario_report.md'} re-rendered from the JSON report")
        return 0

    env = {"python": sys.version.split()[0], "executable": sys.executable, "platform": platform.platform(),
           "processor": platform.processor(), "cpu_count": os.cpu_count(),
           "is_AI_venv": Path(sys.executable).resolve().is_relative_to((AI_ROOT / ".venv").resolve()),
           "packages": {d: version_of(d) for d in ("torch", "transformers", "terlik", "zeyrek", "PyYAML", "numpy")},
           "git_head": git("rev-parse", "HEAD"), "git_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
           "git_status_porcelain": git("status", "--porcelain").splitlines()}
    print(f"[env] python {env['python']} at {env['executable']} (AI/.venv: {env['is_AI_venv']})")
    print(f"[env] git {env['git_branch']} @ {env['git_head']}")

    # -- cold start: import + construction of the real pipeline ---------------------------------
    t0 = time.perf_counter()
    import pipeline.run as prun
    from decision import fusion
    pipeline = prun.Pipeline()
    cold_start_s = time.perf_counter() - t0
    cfg = pipeline.config
    print(f"[perf] cold start (import + Pipeline() incl. model load): {cold_start_s:.1f} s")
    print("[modules] " + ", ".join(f"{m.name.value} {m.version}" + (" (STUB)" if getattr(m, "stub", False) else "")
                                   for m in pipeline.modules))

    # -- M3 artifact identity BEFORE any scenario ------------------------------------------------
    m3info = identify_m3(pipeline)
    print("=" * 100)
    print(f"[M3 ARTIFACT] loaded: {m3info.get('artifact_id')}  ({m3info.get('kind')})")
    print(f"[M3 ARTIFACT] weights path:   {m3info.get('weights_path')}")
    print(f"[M3 ARTIFACT] weights sha256: {m3info.get('weights_sha256')}")
    print(f"[M3 ARTIFACT] {'NSOSYAL_M3_ARTIFACT'} = {m3info['env'].get('NSOSYAL_M3_ARTIFACT')!r}")
    if m3info["is_rule_v4"]:
        print(f"[M3 ARTIFACT] RULE-V4 CONFIRMED ({RULE_V4_ARTIFACT_ID}, sha256 {RULE_V4_WEIGHTS_SHA256})")
    else:
        print("[M3 ARTIFACT] !!! THIS IS NOT THE RULE-V4 ARTIFACT !!!")
        print(f"[M3 ARTIFACT] expected {RULE_V4_ARTIFACT_ID} with weights sha256 {RULE_V4_WEIGHTS_SHA256}")
        print(f"[M3 ARTIFACT] the runtime loads it only via {m3info['rule_v4_expected']['how_the_runtime_loads_it']}")
        print("[M3 ARTIFACT] M3-dependent scenarios will be BLOCKED (BLOCKED_ARTIFACT_NOT_LOCAL); no substitution, "
              "no download, no training, no configuration change.")
    print("=" * 100)

    recorder = Recorder(prun)

    # -- first inference ------------------------------------------------------------------------------
    t1 = time.perf_counter()
    pipeline.analyze("Merhaba, bugün nasılsın?")
    first_inference_ms = (time.perf_counter() - t1) * 1000.0
    print(f"[perf] first inference: {first_inference_ms:.0f} ms")

    # -- scenarios -------------------------------------------------------------------------------------
    scenarios = [json.loads(line) for line in args.scenarios.read_text(encoding="utf-8").splitlines() if line.strip()]
    ids = [s["case_id"] for s in scenarios]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate case_id in the scenario file")
    rows: list[dict[str, Any]] = []
    latencies: list[float] = []
    for scenario in scenarios:
        recorder.outputs = {}
        crash, facts, latency = None, None, None
        start = time.perf_counter()
        try:
            result = pipeline.analyze(scenario["text"], trace_id=scenario["case_id"])
            latency = (time.perf_counter() - start) * 1000.0
            latencies.append(latency)
            facts = Facts(result, recorder.outputs, cfg)
        except Exception as exc:
            crash = f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}"
        evaluation = evaluate(scenario, facts, crash, cfg, m3info["is_rule_v4"])
        row = {**scenario, "evaluation": evaluation, "trace": build_trace(scenario, facts, m3info, latency)}
        rows.append(row)
        if args.verbose:
            print(trace_text(row) + "\n" + "-" * 100)
        elif evaluation["result"] == "FAIL":
            print(f"  FAIL {scenario['case_id']}: {short(scenario['text'], 60)!r} -> "
                  + "; ".join(c[2] for c in evaluation["checks"] if not c[1])[:300])
    print(f"[run] {len(rows)} scenarios analysed")

    # -- review overlay ----------------------------------------------------------------------------------
    review = json.loads(REVIEW.read_text(encoding="utf-8")) if REVIEW.is_file() else {}
    for row in rows:
        ev = row["evaluation"]
        if ev["raw_result"] != "FAIL":
            continue
        entry = review.get(row["case_id"])
        if entry is None:
            ev["review_classification"] = "UNREVIEWED"
            continue
        if entry["classification"] not in FAIL_CLASSES:
            raise SystemExit(f"{row['case_id']}: unknown review classification {entry['classification']}")
        ev["review_classification"] = entry["classification"]
        ev["review_evidence"] = entry.get("evidence", "")
        ev["demo_blocker"] = bool(entry.get("demo_blocker")) or entry["classification"] == "DEMO_BLOCKER"
        if entry["classification"] == "EXPECTATION_WRONG":
            ev["result"] = "EXPECTATION_INVALID"
    stale = sorted({k for k in review if not k.startswith("_")}
                   - {r["case_id"] for r in rows if r["evaluation"]["raw_result"] == "FAIL"})

    # -- warm latency on the demo-critical texts -------------------------------------------------------
    demo_texts = [s["text"] for s in scenarios if s.get("demo_critical")]
    warm: list[float] = []
    per_module: dict[str, list[float]] = {}
    for _ in range(args.warm_repeats):
        for text in demo_texts:
            s = time.perf_counter()
            r = pipeline.analyze(text)
            warm.append((time.perf_counter() - s) * 1000.0)
            for name, ms in r.per_module_ms.items():
                per_module.setdefault(name, []).append(ms)
    prun.safe_process = recorder._original          # restore

    # -- taxonomy coverage ---------------------------------------------------------------------------------
    from modules.m1_lexicon import module as m1mod
    routes = {"A": m1mod.ROUTE_A, "B1": m1mod.ROUTE_B1, "B2": m1mod.ROUTE_B2, "B3": m1mod.ROUTE_B3, "NONE": m1mod.ROUTE_NONE}
    coverage: dict[str, Any] = {}
    for route, roots in routes.items():
        tagged = {r["taxonomy"]["root"] for r in rows if r.get("taxonomy", {}).get("route") == route}
        matched = {r["taxonomy"]["root"] for r in rows if r.get("taxonomy", {}).get("route") == route and r["trace"]
                   and any(m[0] == r["taxonomy"]["root"] for m in r["trace"]["M1"]["matches"])}
        all_pass = {root for root in roots if all(r["evaluation"]["result"] == "PASS" for r in rows
                                                  if r.get("taxonomy", {}).get("root") == root)
                    and root in tagged}
        coverage[route] = {"total": len(roots), "covered": len(tagged & set(roots)),
                           "uncovered": sorted(set(roots) - tagged),
                           "matched_by_m1_in_own_scenarios": len(matched & set(roots)),
                           "never_matched": sorted((set(roots) & tagged) - matched),
                           "all_own_scenarios_pass": len(all_pass),
                           "roots_with_a_non_pass": sorted((set(roots) & tagged) - all_pass)}

    # -- summaries ---------------------------------------------------------------------------------------------
    def count(rows_: list[dict[str, Any]], key: str = "result") -> dict[str, int]:
        c = {k: 0 for k in RESULT_CLASSES}
        for r in rows_:
            c[r["evaluation"][key]] = c.get(r["evaluation"][key], 0) + 1
        return c

    categories = sorted({r["category"] for r in rows})
    by_category = {cat: count([r for r in rows if r["category"] == cat]) for cat in categories}
    totals = count(rows)
    raw_totals = count(rows, "raw_result")
    crashes = [r["case_id"] for r in rows if any(c[0] == "crash" for c in r["evaluation"]["checks"])]
    degraded_other = [r["case_id"] for r in rows if r["trace"] and
                      [d for d in r["trace"]["DECISION"]["degraded"] if d[0] != "m5_sarcasm"]]
    fails = [r for r in rows if r["evaluation"]["raw_result"] == "FAIL"]
    demo_rows = [r for r in rows if r.get("demo_critical")]
    evaluated = [r for r in rows if r["evaluation"]["result"] in ("PASS", "FAIL", "EXPECTATION_INVALID")]
    pass_rate = (totals["PASS"] / len(evaluated)) if evaluated else None

    report = {
        "title": "NSosyal functional / demo scenario regression (frozen system) - NOT an accuracy benchmark",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "environment": env, "m3_artifact": m3info,
        "decision_config": {"artifact": cfg.get("artifact"), "binary_offensive": {k: cfg["binary_offensive"][k]
                                                                                  for k in ("threshold", "action")},
                            "categories_A": {k: cfg["categories"][k] for k in ("A1", "A2", "A3")},
                            "form_min_confidence": cfg["form"]["min_confidence"]},
        "modules": [{"name": m.name.value, "version": m.version, "stub": bool(getattr(m, "stub", False))}
                    for m in pipeline.modules],
        "pipeline_artifact_hash": pipeline.artifact_hash,
        "performance": {"cold_start_s": round(cold_start_s, 2), "first_inference_ms": round(first_inference_ms, 1),
                        "warm_demo_texts_ms": ms_stats(warm), "warm_repeats": args.warm_repeats,
                        "warm_per_module_mean_ms": {k: round(statistics.fmean(v), 2) for k, v in per_module.items()},
                        "scenario_run_ms": ms_stats(latencies)},
        "existing_tests": parse_unittest_log(args.unittest_log),
        "totals": totals, "raw_totals_before_review": raw_totals, "total_scenarios": len(rows),
        "functional_scenario_pass_rate": {"pass": totals["PASS"], "evaluated_pass_fail_invalid": len(evaluated),
                                          "rate": None if pass_rate is None else round(pass_rate, 4),
                                          "note": "PASS / (PASS + FAIL + EXPECTATION_INVALID); limitations, "
                                                  "not-implemented and blocked cases excluded. NOT model accuracy."},
        "by_category": by_category, "taxonomy_coverage": coverage,
        "crashes": crashes, "unexpected_degradation": degraded_other,
        "review_entries_without_a_fail": stale,
        "cases": rows,
    }
    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "demo_scenario_report.json").write_text(safe_json(report, indent=1), encoding="utf-8")
    (RESULTS / "demo_scenario_traces.txt").write_text(
        "\n\n".join(trace_text(r) for r in rows) + "\n", encoding="utf-8")
    (RESULTS / "demo_scenario_report.md").write_text(render_md(report, rows, fails, demo_rows), encoding="utf-8")

    print("=" * 100)
    print(f"[result] {len(rows)} scenarios: " + ", ".join(f"{k} {v}" for k, v in totals.items()))
    print(f"[result] raw before review: " + ", ".join(f"{k} {v}" for k, v in raw_totals.items()))
    print(f"[result] crashes {len(crashes)}; unexpected degradation {len(degraded_other)}; "
          f"unreviewed FAILs {sum(1 for r in fails if r['evaluation'].get('review_classification') == 'UNREVIEWED')}")
    if stale:
        print(f"[result] review entries without a FAIL: {stale}")
    for route, c in coverage.items():
        print(f"[coverage] {route}: {c['covered']}/{c['total']} covered, matched {c['matched_by_m1_in_own_scenarios']}, "
              f"uncovered {c['uncovered']}")
    print(f"[perf] warm demo texts: {ms_stats(warm)}")
    print(f"[out] {RESULTS / 'demo_scenario_report.json'}\n[out] {RESULTS / 'demo_scenario_report.md'}\n"
          f"[out] {RESULTS / 'demo_scenario_traces.txt'}")
    return 0


# ------------------------------------------------------------------------------------------------
# markdown
# ------------------------------------------------------------------------------------------------
def md_cell(text: Any, limit: int = 90) -> str:
    return short(str(text), limit).replace("|", "\\|")


def render_md(report: dict[str, Any], rows: list[dict[str, Any]], fails: list[dict[str, Any]],
              demo_rows: list[dict[str, Any]]) -> str:
    env, m3, perf, tot = report["environment"], report["m3_artifact"], report["performance"], report["totals"]
    L: list[str] = []
    add = L.append
    add("# NSosyal - functional / demo scenario report (frozen system)\n")
    add("> **This is a functional scenario regression, not an accuracy benchmark.** The scenarios are hand-written "
        "and template-generated to exercise documented behaviour; PASS / total is a *functional scenario pass rate*. "
        "The 500-row AI-assisted, human-adjudicated reference remains the model-quality reference for the A head.\n")
    add(f"Generated {report['generated_at']} by `AI/eval/scenarios/run_demo_scenarios.py` from "
        f"`AI/eval/scenarios/demo_scenarios.jsonl`. Full per-case traces: `AI/eval/results/demo_scenario_traces.txt`; "
        "machine-readable: `AI/eval/results/demo_scenario_report.json`.\n")
    add("## 1-3. Environment, git, interpreter\n")
    add("| item | value |\n|---|---|")
    add(f"| interpreter | `{env['executable']}` (Python {env['python']}; AI/.venv: **{env['is_AI_venv']}**) |")
    add(f"| platform | {env['platform']} ({env['cpu_count']} logical CPUs) |")
    add("| packages | " + ", ".join(f"{k} {v}" for k, v in env["packages"].items()) + " |")
    add(f"| git | branch `{env['git_branch']}`, HEAD `{env['git_head']}` |")
    add(f"| working tree | {len(env['git_status_porcelain'])} porcelain lines: " +
        "; ".join(f"`{md_cell(x, 60)}`" for x in env["git_status_porcelain"]) + " |")
    add(f"| pipeline artifact_hash | `{report['pipeline_artifact_hash']}` |")
    add("| modules | " + ", ".join(f"{m['name']} {m['version']}{' (STUB)' if m['stub'] else ''}" for m in report["modules"]) + " |")
    add(f"| decision config | `{report['decision_config']['artifact']}`; binary_offensive threshold "
        f"{report['decision_config']['binary_offensive']['threshold']} (action {report['decision_config']['binary_offensive']['action']}); "
        f"A1/A2/A3 thresholds " + ", ".join(f"{k} {v['threshold']}->{v['action']}" for k, v in report['decision_config']['categories_A'].items()) + " |\n")
    add("## 4-5. M3 artifact actually loaded\n")
    flag = "**YES - Rule-v4**" if m3["is_rule_v4"] else "**NO - THIS IS NOT THE RULE-V4 ARTIFACT**"
    add("| item | value |\n|---|---|")
    add(f"| Rule-v4 loaded? | {flag} |")
    add(f"| loaded artifact id | `{m3.get('artifact_id')}` ({m3.get('kind')}) |")
    add(f"| weights path | `{m3.get('weights_path')}` |")
    add(f"| weights sha256 | `{m3.get('weights_sha256')}` |")
    add(f"| trained heads in loaded artifact | {m3.get('trained_heads')} |")
    add(f"| NSOSYAL_M3_ARTIFACT | `{m3['env'].get('NSOSYAL_M3_ARTIFACT')}` |")
    add(f"| expected Rule-v4 | `{m3['rule_v4_expected']['artifact_id']}`, sha256 `{m3['rule_v4_expected']['weights_sha256']}` |")
    add(f"| how the runtime would load Rule-v4 | {m3['rule_v4_expected']['how_the_runtime_loads_it']} |")
    add(f"| where the run wrote it | `{m3['rule_v4_expected']['where_it_was_written']}` |\n")
    add("## 6-13. Totals\n")
    add(f"Total scenarios: **{report['total_scenarios']}**\n")
    add("| result | count | before failure review |\n|---|---|---|")
    for k in RESULT_CLASSES:
        add(f"| {k} | {tot[k]} | {report['raw_totals_before_review'][k]} |")
    fr = report["functional_scenario_pass_rate"]
    add(f"\nFunctional scenario pass rate: {fr['pass']} / {fr['evaluated_pass_fail_invalid']} = "
        f"{fr['rate']} ({fr['note']})\n")
    add("### Count by category\n")
    add("| category | total | " + " | ".join(RESULT_CLASSES) + " |\n|---|---|" + "---|" * len(RESULT_CLASSES))
    for cat, c in report["by_category"].items():
        add(f"| {cat} | {sum(c.values())} | " + " | ".join(str(c[k]) for k in RESULT_CLASSES) + " |")
    add("\n## 14. Taxonomy coverage (introspected from `modules/m1_lexicon/module.py` ROUTE_*)\n")
    add("| route | roots covered / total | roots m1 matched in their own scenarios | roots whose every own scenario PASSes | uncovered | never matched | roots with a non-PASS scenario |\n|---|---|---|---|---|---|---|")
    for route, c in report["taxonomy_coverage"].items():
        add(f"| {route} | {c['covered']} / {c['total']} | {c['matched_by_m1_in_own_scenarios']} | {c['all_own_scenarios_pass']} | "
            f"{', '.join(c['uncovered']) or '-'} | {', '.join(c['never_matched']) or '-'} | {', '.join(c['roots_with_a_non_pass']) or '-'} |")
    add("\n## 15. Crashes / exceptions\n")
    add(f"Crashes: {len(report['crashes'])} {report['crashes'] or ''}. Unexpected module degradation (other than the "
        f"declared m5 stub): {len(report['unexpected_degradation'])} {report['unexpected_degradation'] or ''}.\n")
    add("## 16. Every failing case (raw FAIL before review), with its classification\n")
    if not fails:
        add("None.\n")
    else:
        add("| case | category | input | failed checks | final result | classification | evidence |\n|---|---|---|---|---|---|---|")
        for r in fails:
            ev = r["evaluation"]
            failed = "; ".join(f"{c[0]}: {c[2]}" for c in ev["checks"] + ev.get("m3_checks", []) if not c[1])
            add(f"| {r['case_id']} | {r['category']} | `{md_cell(r['text'], 60)}` | {md_cell(failed, 220)} | {ev['result']} | "
                f"{ev.get('review_classification')} | {md_cell(ev.get('review_evidence', ''), 400)} |")
    add("\n## 17. Demo-blocker cases\n")
    blockers = [r for r in rows if r["evaluation"].get("demo_blocker")]
    add("\n".join(f"- {r['case_id']} `{md_cell(r['text'], 80)}`: {md_cell(r['evaluation'].get('review_evidence', ''), 300)}"
                  for r in blockers) or "None classified as DEMO_BLOCKER.")
    add("\n### DEMO_CRITICAL cases\n")
    add("| case | purpose | input | status | result | verdict | rule fired | guards suppressed | binary (loaded artifact) |\n|---|---|---|---|---|---|---|---|---|")
    for r in demo_rows:
        d = r["trace"].get("DECISION", {}) if r["trace"] else {}
        b = d.get("binary_offensive", {})
        add(f"| {r['case_id']} | {r['subcategory']} | `{md_cell(r['text'], 70)}` | {r['supported_status']} | "
            f"{r['evaluation']['result']} | {d.get('verdict')} ({d.get('driver')}) | {d.get('rule_fired')} | "
            f"{d.get('guard_suppressions')} | {b.get('score') if b.get('score') is None else round(b.get('score'), 3)} "
            f"fired={b.get('fired')} |")
    add("\n## 18. Known limitations (every KNOWN_LIMITATION case)\n")
    lim = [r for r in rows if r["evaluation"]["result"] == "KNOWN_LIMITATION"]
    add(f"{len(lim)} cases. `ideal met` = the behaviour a user would want happened anyway (not claimed by the architecture).\n")
    add("| case | category / sub | input | ideal met | rule fired | why it is a limitation |\n|---|---|---|---|---|---|")
    for r in lim:
        d = r["trace"].get("DECISION", {}) if r["trace"] else {}
        add(f"| {r['case_id']} | {r['category']} / {r['subcategory']} | `{md_cell(r['text'], 60)}` | {r['evaluation']['ideal_met']} | "
            f"{d.get('rule_fired')} | {md_cell(r['notes'], 200)} |")
    add("\n## 19. M5 sarcasm - NOT_IMPLEMENTED\n")
    add("`m5_sarcasm` 0.0.0 is a declared stub (`stub = True`): it emits nothing, every result is DEGRADED because of it, "
        "and the decision layer therefore never returns `clean` (fail closed: a would-be-clean verdict becomes `review`). "
        "Every M5 scenario is NOT_IMPLEMENTED. Sarcasm detection must not be claimed.\n")
    ni = [r for r in rows if r["evaluation"]["result"] == "NOT_IMPLEMENTED"]
    add("\n".join(f"- {r['case_id']} `{md_cell(r['text'], 80)}` (rule fired {r['trace']['DECISION']['rule_fired'] if r['trace'] else None})" for r in ni))
    add("\n## 20. M4 - stage 1 only\n")
    add("`m4_implicit` emits no content score: it publishes its stage-1 signals (read from m3's scores) and the note "
        "'C1–C5 not implemented yet'. Stage 1 is the single global `binary_offensive` "
        f"threshold ({report['decision_config']['binary_offensive']['threshold']}) applied by the decision layer to m3's raw-channel "
        "score. Stage 2 (C1-C5, slice repair, influence hardening) is not built: C1-C5 scenarios are KNOWN_LIMITATION. "
        "The binary threshold was derived for `m3-berturk-pytorch-fp32-epoch1` only.\n")
    add("## M3-dependent scenarios\n")
    blocked = [r for r in rows if r["evaluation"]["result"] == "BLOCKED"]
    add(f"{len(blocked)} BLOCKED ({'BLOCKED_ARTIFACT_NOT_LOCAL' if blocked else '-'}). Scores of the artifact actually loaded are "
        "recorded in the traces for information only and are not judged.\n")
    add("| case | input | expectation (for Rule-v4) | loaded artifact binary p(raw) | fired at configured threshold |\n|---|---|---|---|---|")
    for r in blocked:
        d = r["trace"]["DECISION"] if r["trace"] else {}
        b = d.get("binary_offensive", {})
        add(f"| {r['case_id']} | `{md_cell(r['text'], 60)}` | {r['expected_module_signals'].get('m3')} | "
            f"{None if b.get('score') is None else round(b['score'], 3)} | {b.get('fired')} |")
    sub_blocked = sum(1 for r in rows if r["evaluation"].get("m3_status") == "BLOCKED_ARTIFACT_NOT_LOCAL"
                      and r["supported_status"] != "M3_DEPENDENT")
    add(f"\nAdditionally {sub_blocked} otherwise-evaluated scenarios carry an M3 sub-check (`a_head_fired: false` on clean text) "
        "that is reported as BLOCKED and did not influence their result.\n")
    add("## Existing automated test suite (separate from the scenarios)\n")
    ut = report["existing_tests"]
    if ut.get("available"):
        add(f"`python -m unittest discover -p \"test_*.py\"` with AI/.venv: ran {ut['ran']} in {ut['seconds']} s -> "
            f"**{ut['status']}**: passed {ut['passed']}, failed {ut['failures']}, errors {ut['errors']}, skipped {ut['skipped']} "
            "(the declared m5 skip `test_friendly_irony_is_not_d1`).\n")
    else:
        add("Not provided to this run.\n")
    add("## Performance (this machine, CPU)\n")
    add(f"- cold start (import + `Pipeline()` incl. BERTurk load, terlik, zeyrek): **{perf['cold_start_s']} s**")
    add(f"- first inference: **{perf['first_inference_ms']} ms**")
    add(f"- warm, {perf['warm_repeats']} x the {len(demo_rows)} DEMO_CRITICAL texts: {perf['warm_demo_texts_ms']}")
    add(f"- warm per-module mean ms: {perf['warm_per_module_mean_ms']}")
    add(f"- whole scenario run, per request: {perf['scenario_run_ms']}\n")
    if ANALYSIS.is_file():
        add(ANALYSIS.read_text(encoding="utf-8"))
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    raise SystemExit(main())
