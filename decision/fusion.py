"""Decision layer: the only code allowed to compare a score with a threshold.

Steps, in order:
  1. fuse raw/normalized channels per content code (strategy from config)
  2. set threshold + fired on every fused score
  3. mark active form codes
  4. apply guards as SUPPRESSORS, in guards_order
  5. apply the thread rule (Axis 4)
  6. resolve verdict + explanation (decision/actions.py)

Every number comes from decision/thresholds.yaml. A category missing from the
config never fires and is reported in notes - it does not silently pass.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from contracts.codes import FAMILY, Action, ContentCode, GuardCode, ModuleName
from contracts.schema import AnalysisResult, ContentScore, FormResult, GuardResult, ThreadSignal
from decision import actions

DEFAULT_CONFIG_PATH = Path(__file__).with_name("thresholds.yaml")
_STRATEGIES = ("max",)


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path) if path is not None else DEFAULT_CONFIG_PATH
    with config_path.open("r", encoding="utf-8") as fh:
        cfg = yaml.safe_load(fh)
    validate_config(cfg)
    return cfg


def validate_config(cfg: dict[str, Any]) -> None:
    """Fail loudly at load time rather than mis-deciding at inference time."""
    for key in ("artifact", "fusion", "form", "categories", "fast_path", "guards",
                "guards_order", "budgets", "thread"):
        if key not in cfg:
            raise ValueError(f"thresholds config missing section: {key}")
    if cfg["fusion"]["strategy"] not in _STRATEGIES:
        raise ValueError(f"unknown fusion strategy: {cfg['fusion']['strategy']!r}")
    for code, entry in cfg["categories"].items():
        ContentCode(code)
        Action(entry["action"])
        float(entry["threshold"])
    for code in cfg["guards_order"]:
        GuardCode(code)
        if code not in cfg["guards"]:
            raise ValueError(f"guards_order names {code} but guards has no entry for it")
    valid_targets = {c.value for c in ContentCode} | {f.value for f in FAMILY.values()}
    for code, entry in cfg["guards"].items():
        GuardCode(code)
        float(entry["threshold"])
        unknown = set(entry["suppresses"]) - valid_targets
        if unknown:
            raise ValueError(f"guard {code} suppresses unknown codes: {sorted(unknown)}")
    for name in cfg["fast_path"]["requires"]:
        ModuleName(name)
    Action(cfg["thread"]["action"])


# -- 1. channel fusion ------------------------------------------------------
def fuse_channels(scores: list[ContentScore], cfg: dict[str, Any]) -> list[ContentScore]:
    """One score per content code. With `max`, the winning source is kept so
    an audit can tell whether the normalized channel was decisive."""
    best: dict[ContentCode, ContentScore] = {}
    for score in scores:
        if score.code is ContentCode.CLEAN:
            continue
        current = best.get(score.code)
        if current is None or score.score > current.score:
            best[score.code] = ContentScore(code=score.code, score=score.score, source=score.source)
    return list(best.values())


# -- 2. thresholds ----------------------------------------------------------
def apply_thresholds(scores: list[ContentScore], cfg: dict[str, Any], notes: list[str]) -> None:
    for score in scores:
        entry = cfg["categories"].get(score.code.value)
        if entry is None:
            score.threshold, score.fired = None, False
            notes.append(f"[decision] no threshold configured for {score.code.value}; not fired")
            continue
        score.threshold = float(entry["threshold"])
        score.fired = score.score >= score.threshold


# -- 3. form ----------------------------------------------------------------
def apply_form(form: FormResult, cfg: dict[str, Any]) -> None:
    min_confidence = float(cfg["form"]["min_confidence"])
    form.active = list(dict.fromkeys(p.code for p in form.patterns if p.confidence >= min_confidence))


# -- 4. guards --------------------------------------------------------------
def _covers(entry: str, code: ContentCode) -> bool:
    return entry == code.value or entry == FAMILY[code].value


def guard_is_active(guard: GuardResult, cfg: dict[str, Any]) -> bool:
    entry = cfg["guards"].get(guard.code.value)
    return entry is not None and guard.score >= float(entry["threshold"])


def apply_guards(content: list[ContentScore], guards: list[GuardResult],
                 cfg: dict[str, Any], notes: list[str]) -> None:
    by_code: dict[GuardCode, list[GuardResult]] = {}
    for guard in guards:
        entry = cfg["guards"].get(guard.code.value)
        if entry is None:
            guard.active = False
            notes.append(f"[decision] no config for guard {guard.code.value}; inactive")
            continue
        guard.threshold = float(entry["threshold"])
        guard.active = guard_is_active(guard, cfg)
        by_code.setdefault(guard.code, []).append(guard)

    for code_name in cfg["guards_order"]:
        active = [g for g in by_code.get(GuardCode(code_name), []) if g.active]
        if not active:
            continue
        credited = max(active, key=lambda g: g.score)
        for score in content:
            if score.fired and any(_covers(e, score.code) for e in cfg["guards"][code_name]["suppresses"]):
                score.fired = False
                credited.suppressed.append(score.code)
                notes.append(f"[decision] {score.code.value} suppressed by guard {code_name} "
                             f"({credited.source})")


# -- 5. thread --------------------------------------------------------------
def apply_thread(thread: ThreadSignal | None, cfg: dict[str, Any]) -> None:
    if thread is None:
        return
    rule = cfg["thread"]
    thread.threshold = int(rule["min_repeats"])
    target_ok = thread.same_target is True or not rule["same_target_required"]
    thread.fired = bool(rule["enabled"]) and thread.repeat_count >= thread.threshold and target_ok


# -- fast path ----------------------------------------------------------------
def fast_path_hit(content: list[ContentScore], guards: list[GuardResult], cfg: dict[str, Any]) -> bool:
    """True when the evidence so far is decisive enough to skip the remaining
    modules. The pipeline checks that `fast_path.requires` have run."""
    fast = cfg["fast_path"]
    if not fast["enabled"]:
        return False
    if any(guard_is_active(g, cfg) for g in guards):
        return False
    margin = float(fast["margin"])
    for score in fuse_channels(content, cfg):
        entry = cfg["categories"].get(score.code.value)
        if entry is not None and score.score >= float(entry["threshold"]) + margin:
            return True
    return False


# -- entry point --------------------------------------------------------------
def decide(result: AnalysisResult, cfg: dict[str, Any]) -> AnalysisResult:
    """Fill every decision-owned field of `result` in place and return it."""
    raw_scores = list(result.content)
    result.signals.setdefault("decision", {})["channel_scores"] = [
        {"code": s.code.value, "score": s.score, "source": s.source} for s in raw_scores
    ]
    result.content = fuse_channels(raw_scores, cfg)
    apply_thresholds(result.content, cfg, result.notes)
    apply_form(result.form, cfg)
    apply_guards(result.content, result.guards, cfg, result.notes)
    apply_thread(result.thread, cfg)
    verdict, driver = actions.resolve(result, cfg)
    result.verdict = verdict
    result.explanation = actions.explain(result, verdict, driver)
    return result
