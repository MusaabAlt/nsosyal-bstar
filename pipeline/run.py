"""Pipeline: runs modules in registry order, merges their partial outputs into
one AnalysisResult, honours the fast path, then hands off to the decision layer.

The pipeline enforces the module contract at runtime:
  * fields a module did not declare in `provides` are dropped (rule 5)
  * threshold / fired / active set by a module are cleared (rule 4)
  * malformed output items (wrong types, NaN/inf scores, invalid spans, a
    `source` naming another module) are dropped with a note - a NaN score is
    an error, never an implicit "clean"
  * each module sees a deep read-only copy of earlier modules' signals;
    "_"-prefixed signal keys are internal and never reach the response
  * nothing a module does - failing to construct, load, run, or returning
    garbage - crashes the request
  * SPANS (ADR-001): a module declaring `emits_spans = True` - or declaring
    nothing - must put a span on every content score and guard; one without a
    span is dropped, never applied. The no-span guard fallback exists only for
    modules that explicitly declare `emits_spans = False`.
  * FAIL CLOSED: a stub, a failed or unavailable module, or a module whose
    output had to be dropped makes the result DEGRADED. Every degraded module
    is listed in signals.pipeline.degraded with its reasons, and the decision
    layer never returns clean for a degraded result (policy, Phase 9).

CLI:  python -m pipeline.run "metin" [--compact] [--trace-id ID]
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import sys
import time
import uuid
from types import MappingProxyType
from typing import Any, Mapping

from contracts.codes import ContentCode, FormCode, GuardCode, ModuleName, TargetType
from contracts.module_api import Context, ModuleOutput
from contracts.schema import (AnalysisResult, ContentScore, FormPattern, FormResult, GuardResult, TargetResult,
                              ThreadSignal)
from decision import fusion
from modules import registry

_IMMUTABLE_SCALARS = (str, int, float, bool, bytes, type(None))


def _canonical(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_canonical(v) for v in value]
    return value


def artifact_hash(config: Mapping[str, Any], modules: list[Any]) -> str:
    """sha256 over the decision config actually in use (in-memory, canonical
    JSON) and every module name:version. The harness uses this same function,
    so a stored result names exactly which decision config and code produced it."""
    digest = hashlib.sha256()
    digest.update(json.dumps(_canonical(config), sort_keys=True, separators=(",", ":"),
                             ensure_ascii=False, default=str).encode("utf-8"))
    for module in modules:
        digest.update(f"|{module.name.value}:{module.version}".encode("utf-8"))
    return digest.hexdigest()


def deep_freeze(value: Any) -> Any:
    """Read-only deep copy: mappings become MappingProxyType, sequences tuples.
    A module can therefore neither mutate another module's signal payload nor
    see later mutations by the producer."""
    if isinstance(value, Mapping):
        return MappingProxyType({k: deep_freeze(v) for k, v in value.items()})
    if isinstance(value, (list, tuple)):
        return tuple(deep_freeze(v) for v in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(deep_freeze(v) for v in value)
    if isinstance(value, _IMMUTABLE_SCALARS) or isinstance(value, (ModuleName, ContentCode, FormCode, GuardCode)):
        return value
    return copy.deepcopy(value)


class UnavailableModule:
    """Stands in for a module that could not be constructed or loaded, so the
    failure is reported on every request instead of crashing the service."""

    def __init__(self, name: ModuleName, error: str) -> None:
        self.name = name
        self.version = "unavailable"
        self.provides: frozenset[str] = frozenset()
        self.error = error

    def load(self) -> None:
        return None

    def process(self, ctx: Context) -> ModuleOutput:
        return ModuleOutput(ok=False, notes=[self.error])


def build_modules_safely(entries: tuple[registry.RegistryEntry, ...] = registry.PIPELINE_ORDER) -> list[Any]:
    modules: list[Any] = []
    for entry in entries:
        if not entry.enabled:
            continue
        try:
            module = registry.load_class(entry)()
        except Exception as exc:
            modules.append(UnavailableModule(entry.name, f"construction failed: {type(exc).__name__}: {exc}"))
            continue
        try:
            module.load()
        except Exception as exc:
            modules.append(UnavailableModule(entry.name, f"load failed: {type(exc).__name__}: {exc}"))
            continue
        modules.append(module)
    return modules


def safe_process(module: Any, ctx: Context) -> ModuleOutput:
    """Call module.process without letting anything escape. BaseModule already
    catches its own exceptions; this also covers Protocol-only modules."""
    start = time.perf_counter()
    try:
        out = module.process(ctx)
        if not isinstance(out, ModuleOutput):
            out = ModuleOutput(ok=False, notes=[f"process returned {type(out).__name__}, expected ModuleOutput"])
    except Exception as exc:
        out = ModuleOutput(ok=False, notes=[f"process raised {type(exc).__name__}: {exc}"])
    out.module = module.name.value
    out.version = getattr(module, "version", "")
    out.latency_ms = (time.perf_counter() - start) * 1000.0
    return out


def _finite(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _score_problem(value: Any) -> str | None:
    """Scores and confidences are probabilities: finite and within [0, 1].
    NaN, None or out-of-range is an error of the producing module, never a silent zero."""
    if not _finite(value):
        return f"score {value!r} is not a finite number (treated as degradation, not as clean)"
    if not 0 <= value <= 1:
        return f"score {value!r} is outside [0, 1] (treated as degradation, not as clean)"
    return None


DEGRADED_STUB = "stub"
DEGRADED_FAILED = "failed"
DEGRADED_INVALID = "invalid_output"


def _span_problem(span: Any, text: str) -> str | None:
    if span is None:
        return None
    if (not isinstance(span, (tuple, list)) or len(span) != 2
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in span)):
        return f"span {span!r} is not a (start, end) pair of ints"
    if not 0 <= span[0] <= span[1] <= len(text):
        return f"span {tuple(span)} is outside the original text (length {len(text)})"
    return None


def _source_problem(source: Any, name: str, required: bool) -> str | None:
    if not isinstance(source, str):
        return f"source {source!r} is not a string"
    if not source:
        return "source is empty" if required else None
    if fusion.module_of(source) != name:
        # A module may not speak for another: guard scoping (ADR-001) trusts `source`.
        return f"source {source!r} names a different module"
    return None


def public_signals(payload: Any) -> Any:
    """A module's signal payload without its internal ("_"-prefixed) keys."""
    if isinstance(payload, dict):
        return {k: v for k, v in payload.items() if not str(k).startswith("_")}
    return payload


def span_declarations(modules: list[Any]) -> dict[str, bool]:
    """Module name -> whether its scores/guards must carry spans (undeclared = True)."""
    return {m.name.value: getattr(m, "emits_spans", None) is not False for m in modules}


class Pipeline:
    def __init__(self, modules: list[Any] | None = None, config: dict[str, Any] | None = None,
                 config_path: str | None = None) -> None:
        path = config_path if config_path is not None else fusion.DEFAULT_CONFIG_PATH
        # A broken decision config must stop the service at startup, loudly.
        self.config = config if config is not None else fusion.load_config(path)
        if modules is None:
            self.modules = build_modules_safely()
        else:
            self.modules = []
            for module in modules:
                try:
                    module.load()
                    self.modules.append(module)
                except Exception as exc:
                    self.modules.append(UnavailableModule(module.name, f"load failed: {type(exc).__name__}: {exc}"))
        self.artifact_hash = artifact_hash(self.config, self.modules)

    def analyze(self, text: str, thread: ThreadSignal | None = None,
                trace_id: str | None = None) -> AnalysisResult:
        start = time.perf_counter()
        result = AnalysisResult(
            text=text,
            thread=thread,
            trace_id=trace_id or uuid.uuid4().hex,
            artifact_hash=self.artifact_hash,
        )
        charsafe_text: str | None = None
        normalized_text: str | None = None
        signals: dict[str, Any] = {}
        ran: set[str] = set()
        degraded: dict[str, dict[str, Any]] = {}

        def degrade(name: str, kind: str, reason: str) -> None:
            entry = degraded.setdefault(name, {"module": name, "kinds": [], "reasons": []})
            if kind not in entry["kinds"]:
                entry["kinds"].append(kind)
            entry["reasons"].append(reason)

        for module in self.modules:
            if getattr(module, "stub", False):
                degrade(module.name.value, DEGRADED_STUB, "stub: no detection logic yet")
        required = set(self.config["fast_path"]["requires"])

        for index, module in enumerate(self.modules):
            ctx = Context(
                text=text,
                charsafe_text=charsafe_text,
                normalized_text=normalized_text,
                signals=deep_freeze(signals),
                trace_id=result.trace_id,
            )
            out = safe_process(module, ctx)
            if not out.ok:
                degrade(module.name.value, DEGRADED_FAILED, "; ".join(map(str, out.notes)) or "ok=False")
            for problem in self._merge(result, out, module):
                degrade(module.name.value, DEGRADED_INVALID, problem)
            if "charsafe_text" in module.provides and out.charsafe_text is not None:
                charsafe_text = out.charsafe_text
            if "normalized_text" in module.provides and out.normalized_text is not None:
                normalized_text = out.normalized_text
            signals[module.name.value] = out.signals
            ran.add(module.name.value)

            remaining = self.modules[index + 1:]
            if remaining and required <= ran and fusion.fast_path_hit(result.content, result.guards,
                                                                     self.config, signals):
                result.fast_path = True
                skipped = ", ".join(m.name.value for m in remaining)
                result.notes.append(f"[pipeline] fast path after {module.name.value}; skipped: {skipped}")
                break

        # Keys starting with "_" are internal: passed to later modules through
        # ctx.signals but kept out of the response, so its size does not grow
        # with the post (e.g. m0's per-character `_offsets`).
        result.signals.update({name: public_signals(payload) for name, payload in signals.items()})
        result.signals["channels"] = {"charsafe_text": charsafe_text, "normalized_text": normalized_text}
        result.signals["pipeline"] = {"degraded": list(degraded.values()),
                                      "emits_spans": span_declarations(self.modules)}
        if degraded:
            # A screenshot of a "clean" verdict must not pass for a real result.
            summary = ", ".join(f"{d['module']} ({'/'.join(d['kinds'])})" for d in degraded.values())
            result.notes.insert(0, f"[pipeline] DEGRADED - judgement incomplete, clean is not reachable: {summary}")
        try:
            fusion.decide(result, self.config)
        except Exception as exc:
            result.verdict = None
            result.explanation = "Karar verilemedi: karar katmanında bir hata oluştu, içerik değerlendirilmedi."
            result.notes.append(f"[pipeline] decision layer failed: {type(exc).__name__}: {exc}")
        result.latency_ms = (time.perf_counter() - start) * 1000.0
        return result

    @staticmethod
    def _merge(result: AnalysisResult, out: ModuleOutput, module: Any) -> list[str]:
        """Merge one module's output into `result`. Returns the problems found
        (dropped items, undeclared fields); each one degrades the module."""
        name = module.name.value
        result.per_module_ms[name] = out.latency_ms
        problems: list[str] = []
        # Undeclared counts as "spans required": the fallback must be opted into.
        spans_required = getattr(module, "emits_spans", None) is not False

        def drop(what: str, why: str) -> None:
            problems.append(f"dropped {what}: {why}")

        if not isinstance(out.notes, list):
            problems.append(f"notes was {type(out.notes).__name__}, expected list")
            out.notes = []
        result.notes.extend(f"[{name}] {note}" for note in out.notes)
        if not isinstance(out.signals, dict):
            problems.append(f"signals was {type(out.signals).__name__}; replaced by {{}}")
            out.signals = {}

        undeclared = out.populated_fields() - set(module.provides)
        if undeclared:
            problems.append(f"returned undeclared fields {sorted(undeclared)}; dropped")

        def allowed(field_name: str) -> bool:
            return field_name in module.provides and field_name not in undeclared

        for text_field in ("charsafe_text", "normalized_text"):
            value = getattr(out, text_field)
            if value is not None and not isinstance(value, str):
                drop(text_field, f"is {type(value).__name__}, expected str")
                setattr(out, text_field, None)

        if allowed("form") and out.form is not None:
            if not isinstance(out.form, FormResult):
                drop("form", f"is {type(out.form).__name__}, expected FormResult")
            else:
                for i, pattern in enumerate(out.form.patterns):
                    if not isinstance(pattern, FormPattern) or not isinstance(pattern.code, FormCode):
                        drop(f"form pattern #{i}", "not a FormPattern with a FormCode")
                    elif why := _score_problem(pattern.confidence):
                        drop(f"form pattern #{i} ({pattern.code.value})", why)
                    elif (why := _span_problem(pattern.span, result.text)
                          or _source_problem(pattern.source, name, required=False)):
                        drop(f"form pattern #{i} ({pattern.code.value})", why)
                    else:
                        pattern.source = pattern.source or name
                        result.form.patterns.append(pattern)
                if out.form.active:
                    result.notes.append(f"[pipeline] {name} set form.active (decision-owned); cleared")

        if allowed("content"):
            for i, score in enumerate(out.content):
                if not isinstance(score, ContentScore) or not isinstance(score.code, ContentCode):
                    drop(f"content item #{i}", "not a ContentScore with a ContentCode")
                    continue
                if why := _score_problem(score.score):
                    drop(f"content {score.code.value}", why)
                    continue
                why = _span_problem(score.span, result.text) or _source_problem(score.source, name, required=True)
                if not why and spans_required and score.span is None:
                    why = "no span although the module emits spans (ADR-001); not applied"
                if why:
                    drop(f"content {score.code.value}", why)
                    continue
                if score.threshold is not None or score.fired is not None:
                    result.notes.append(f"[pipeline] {name} set threshold/fired on {score.code.value} "
                                        f"(decision-owned); cleared")
                    score.threshold, score.fired = None, None
                result.content.append(score)

        if allowed("guards"):
            for i, guard in enumerate(out.guards):
                if not isinstance(guard, GuardResult) or not isinstance(guard.code, GuardCode):
                    drop(f"guard #{i}", "not a GuardResult with a GuardCode")
                    continue
                if why := _score_problem(guard.score):
                    drop(f"guard {guard.code.value}", why)
                    continue
                why = _span_problem(guard.span, result.text) or _source_problem(guard.source, name, required=False)
                if not why and spans_required and guard.span is None:
                    why = "no span although the module emits spans (ADR-001); not applied"
                if why:
                    drop(f"guard {guard.code.value}", why)
                    continue
                guard.source = guard.source or name
                if guard.threshold is not None or guard.active is not None or guard.suppressed:
                    result.notes.append(f"[pipeline] {name} set decision fields on guard "
                                        f"{guard.code.value}; cleared")
                    guard.threshold, guard.active, guard.suppressed = None, None, []
                result.guards.append(guard)

        if allowed("target") and out.target is not None:
            if not isinstance(out.target, TargetResult) or not isinstance(out.target.type, TargetType):
                drop("target", "not a TargetResult with a TargetType")
            elif why := _score_problem(out.target.confidence):
                drop("target", why)
            elif why := _span_problem(out.target.span, result.text):
                drop("target", why)
            else:
                if result.target is not None:
                    result.notes.append(f"[pipeline] {name} overrides target from {result.target.source}")
                result.target = out.target

        if allowed("thread") and out.thread is not None:
            if not isinstance(out.thread, ThreadSignal) or not isinstance(out.thread.repeat_count, int):
                drop("thread", "not a ThreadSignal with an int repeat_count")
            else:
                out.thread.threshold, out.thread.fired = None, None
                result.thread = out.thread

        result.notes.extend(f"[pipeline] {name}: {problem}" for problem in problems)
        if not out.ok or problems:
            result.notes.append(f"[pipeline] {name} failed or returned invalid output; result is degraded")
        return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m pipeline.run", description=__doc__.splitlines()[0])
    parser.add_argument("text", help="text to analyse")
    parser.add_argument("--compact", action="store_true", help="single-line JSON")
    parser.add_argument("--trace-id", default=None)
    args = parser.parse_args(argv)

    # Windows consoles default to a legacy code page that cannot print Turkish.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = Pipeline().analyze(args.text, trace_id=args.trace_id)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=None if args.compact else 2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
