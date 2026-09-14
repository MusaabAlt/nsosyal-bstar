"""Pipeline: runs modules in registry order, merges their partial outputs into
one AnalysisResult, honours the fast path, then hands off to the decision layer.

The pipeline enforces the module contract at runtime:
  * fields a module did not declare in `provides` are dropped (rule 5)
  * threshold / fired / active set by a module are cleared (rule 4)
  * a failing module degrades the result with a note, it never aborts it

CLI:  python -m pipeline.run "metin" [--compact] [--trace-id ID]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
import uuid
from types import MappingProxyType
from typing import Any

from contracts.module_api import Context, ModuleOutput
from contracts.schema import AnalysisResult, ThreadSignal
from decision import fusion
from modules import registry


def artifact_hash(cfg_path: Any, modules: list[Any]) -> str:
    """sha256 over the thresholds file and every module name:version, so a
    stored result names exactly which decision config and code produced it."""
    digest = hashlib.sha256()
    with open(cfg_path, "rb") as fh:
        digest.update(fh.read())
    for module in modules:
        digest.update(f"{module.name.value}:{module.version}".encode())
    return digest.hexdigest()


class Pipeline:
    def __init__(self, modules: list[Any] | None = None, config: dict[str, Any] | None = None,
                 config_path: str | None = None) -> None:
        path = config_path if config_path is not None else fusion.DEFAULT_CONFIG_PATH
        self.config = config if config is not None else fusion.load_config(path)
        self.modules = modules if modules is not None else registry.build_all()
        self.artifact_hash = artifact_hash(path, self.modules)
        for module in self.modules:
            module.load()

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
        required = set(self.config["fast_path"]["requires"])

        for index, module in enumerate(self.modules):
            ctx = Context(
                text=text,
                charsafe_text=charsafe_text,
                normalized_text=normalized_text,
                signals=MappingProxyType(dict(signals)),
                trace_id=result.trace_id,
            )
            out = module.process(ctx)
            self._merge(result, out, module)
            if "charsafe_text" in module.provides and out.charsafe_text is not None:
                charsafe_text = out.charsafe_text
            if "normalized_text" in module.provides and out.normalized_text is not None:
                normalized_text = out.normalized_text
            signals[module.name.value] = out.signals
            ran.add(module.name.value)

            remaining = self.modules[index + 1:]
            if remaining and required <= ran and fusion.fast_path_hit(result.content, result.guards, self.config, signals):
                result.fast_path = True
                skipped = ", ".join(m.name.value for m in remaining)
                result.notes.append(f"[pipeline] fast path after {module.name.value}; skipped: {skipped}")
                break

        result.signals.update(signals)
        result.signals["channels"] = {"charsafe_text": charsafe_text, "normalized_text": normalized_text}
        fusion.decide(result, self.config)
        result.latency_ms = (time.perf_counter() - start) * 1000.0
        return result

    @staticmethod
    def _merge(result: AnalysisResult, out: ModuleOutput, module: Any) -> None:
        name = module.name.value
        result.per_module_ms[name] = out.latency_ms
        result.notes.extend(f"[{name}] {note}" for note in out.notes)
        if not out.ok:
            result.notes.append(f"[pipeline] {name} failed; result is degraded")

        undeclared = out.populated_fields() - set(module.provides)
        if undeclared:
            result.notes.append(f"[pipeline] {name} returned undeclared fields {sorted(undeclared)}; dropped")

        def allowed(field_name: str) -> bool:
            return field_name in module.provides and field_name not in undeclared

        if allowed("form") and out.form is not None:
            for pattern in out.form.patterns:
                pattern.source = pattern.source or name
            result.form.patterns.extend(out.form.patterns)
            if out.form.active:
                result.notes.append(f"[pipeline] {name} set form.active (decision-owned); cleared")
        if allowed("content"):
            for score in out.content:
                if score.threshold is not None or score.fired is not None:
                    result.notes.append(f"[pipeline] {name} set threshold/fired on {score.code.value} "
                                        f"(decision-owned); cleared")
                    score.threshold, score.fired = None, None
                result.content.append(score)
        if allowed("guards"):
            for guard in out.guards:
                if guard.threshold is not None or guard.active is not None or guard.suppressed:
                    result.notes.append(f"[pipeline] {name} set decision fields on guard "
                                        f"{guard.code.value}; cleared")
                    guard.threshold, guard.active, guard.suppressed = None, None, []
                result.guards.append(guard)
        if allowed("target") and out.target is not None:
            if result.target is not None:
                result.notes.append(f"[pipeline] {name} overrides target from {result.target.source}")
            result.target = out.target
        if allowed("thread") and out.thread is not None:
            out.thread.threshold, out.thread.fired = None, None
            result.thread = out.thread


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
