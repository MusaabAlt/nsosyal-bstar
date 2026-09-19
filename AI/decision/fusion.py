"""Decision layer: the only code allowed to compare a score with a threshold.

Steps, in order:
  0. reset decision-owned fields; assign the final family-A code (A1/A2/A3)
     from m6's target (ADR-005) - modules report profanity, never its target
  1. set threshold + fired on every per-module, per-channel score
  2. apply guards as SUPPRESSORS, in guards_order, scoped per ADR-001
     (same module; overlapping spans when both carry one)
  3. fuse channels/sources per content code (strategy from config)
  4. mark active form codes
  5. apply the thread rule (Axis 4)
  6. resolve verdict + explanation (decision/actions.py)

Guards run BEFORE fusion on purpose: fusion keeps one score per code, so a
guard applied after it could erase an independent score from another module -
cross-module suppression by the back door (ADR-001).

Every number comes from decision/thresholds.yaml. A category missing from the
config never fires and is reported in notes - it does not silently pass.
"""
from __future__ import annotations

import math
from pathlib import Path
from typing import Any, Mapping

import yaml

from contracts.codes import FAMILY, Action, ContentCode, GuardCode, ModuleName, TargetType
from contracts.schema import AnalysisResult, ContentScore, FormResult, GuardResult, TargetResult, ThreadSignal
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
    for key in ("artifact", "fusion", "form", "family_a", "categories", "fast_path", "guards",
                "guards_order", "budgets", "thread"):
        if key not in cfg:
            raise ValueError(f"thresholds config missing section: {key}")
    status, derived_on = cfg["artifact"].get("status"), cfg["artifact"].get("derived_on")
    if status not in ("placeholder", "derived"):
        raise ValueError(f"artifact.status must be placeholder or derived, got {status!r}")
    if (status == "derived") != (derived_on is not None):
        # A derived file must say where it was derived; a placeholder must not pretend to be.
        raise ValueError(f"artifact.derived_on is {derived_on!r} but status is {status!r}")
    if cfg["fusion"]["strategy"] not in _STRATEGIES:
        raise ValueError(f"unknown fusion strategy: {cfg['fusion']['strategy']!r}")
    for code, entry in cfg["categories"].items():
        ContentCode(code)
        Action(entry["action"])
        _validate_threshold_entry(f"categories.{code}", entry)
    binary = cfg.get("binary_offensive")
    if binary is not None:
        Action(binary["action"])
        _validate_threshold_entry("binary_offensive", binary)
        for channel, path in binary["channels"].items():
            if channel not in cfg["fusion"]["channels"]:
                raise ValueError(f"binary_offensive.channels: unknown channel {channel!r}")
            _split_signal_path(path)
    for code in cfg["guards_order"]:
        GuardCode(code)
        if code not in cfg["guards"]:
            raise ValueError(f"guards_order names {code} but guards has no entry for it")
    unordered = set(cfg["guards"]) - set(cfg["guards_order"])
    if unordered:
        # A configured guard missing from guards_order would never be applied - silently.
        raise ValueError(f"guards configured but not in guards_order: {sorted(unordered)}")
    valid_targets = {c.value for c in ContentCode} | {f.value for f in FAMILY.values()}
    for code, entry in cfg["guards"].items():
        GuardCode(code)
        float(entry["threshold"])
        unknown = set(entry["suppresses"]) - valid_targets
        if unknown:
            raise ValueError(f"guard {code} suppresses unknown codes: {sorted(unknown)}")
    for name in cfg["fast_path"]["requires"]:
        ModuleName(name)
    for name, budget in cfg["budgets"]["module_latency_p95_ms"].items():
        ModuleName(name)
        bands = budget if isinstance(budget, dict) else {None: budget}
        for max_chars, ms in bands.items():
            if max_chars is not None and (not isinstance(max_chars, int) or isinstance(max_chars, bool)):
                raise ValueError(f"latency budget for {name}: band key {max_chars!r} must be a max character count")
            float(ms)
    family_a = cfg["family_a"]
    float(family_a["target_min_confidence"])
    by_target = family_a["by_target"]
    if set(by_target) != {t.value for t in TargetType}:
        raise ValueError(f"family_a.by_target must map every target type, got {sorted(by_target)}")
    for target, code in by_target.items():
        if ContentCode(code) not in TARGETED_A:
            raise ValueError(f"family_a.by_target.{target} must be A1, A2 or A3, got {code!r}")
    Action(cfg["thread"]["action"])
    window = cfg["thread"].get("window_seconds")
    if isinstance(window, bool) or not isinstance(window, (int, float)) or not math.isfinite(window) or window <= 0:
        raise ValueError(f"thread.window_seconds must be a positive number of seconds, got {window!r}")


# -- 0b. family A by target (ADR-005) ----------------------------------------
# A1/A2/A3 differ only by target. Modules report "profanity present" on the A1
# carrier; the final code is assigned here from m6's target, never by a module.
# A4 is concept-based (m1) and is not touched.
TARGETED_A = frozenset({ContentCode.A1, ContentCode.A2, ContentCode.A3})


def family_a_code(target: TargetResult | None, cfg: dict[str, Any]) -> tuple[ContentCode, dict[str, Any]]:
    """The A code every A1-A3 score takes for this post, and its audit record.
    A target below family_a.target_min_confidence, or no target at all, counts as none."""
    rule = cfg["family_a"]
    min_confidence = float(rule["target_min_confidence"])
    seen = target.type if target is not None else TargetType.NONE
    used = seen if target is not None and target.confidence >= min_confidence else TargetType.NONE
    code = ContentCode(rule["by_target"][used.value])
    return code, {"target": seen.value, "confidence": None if target is None else target.confidence,
                  "min_confidence": min_confidence, "resolved_as": used.value, "code": code.value}


def resolve_family_a(scores: list[ContentScore], target: TargetResult | None, cfg: dict[str, Any],
                     notes: list[str]) -> dict[str, Any] | None:
    if not any(s.code in TARGETED_A for s in scores):
        return None
    code, record = family_a_code(target, cfg)
    for score in scores:
        if score.code in TARGETED_A:
            if score.code is not ContentCode.A1:
                notes.append(f"[decision] {score.source} emitted {score.code.value}; family A codes are "
                             f"assigned from the target (ADR-005), recoded to {code.value}")
            score.code = code
    return record


# -- 1. channel fusion ------------------------------------------------------
def fuse_channels(scores: list[ContentScore], cfg: dict[str, Any]) -> list[ContentScore]:
    """One score per content code. With `max`, the winning source and span are
    kept so an audit can tell which module/channel was decisive.

    On already-decided scores the representative is the highest score that is
    still fired (unsuppressed); only if none fired is it the highest overall.
    A suppressed score therefore never hides a fired one for the same code.
    """
    groups: dict[ContentCode, list[ContentScore]] = {}
    for score in scores:
        if score.code is not ContentCode.CLEAN:
            groups.setdefault(score.code, []).append(score)
    fused: list[ContentScore] = []
    for code, group in groups.items():
        fired = [s for s in group if s.fired]
        best = max(fired or group, key=lambda s: s.score)
        fused.append(ContentScore(code=code, score=best.score, source=best.source, span=best.span,
                                  threshold=best.threshold,
                                  fired=bool(fired) if best.fired is not None else None))
    return fused


# -- signal-conditioned thresholds -------------------------------------------
def _split_signal_path(path: str) -> tuple[str, str]:
    module, sep, key = str(path).partition(".")
    if not sep or not module or not key:
        raise ValueError(f"signal path must be '<module>.<key>', got {path!r}")
    ModuleName(module)
    return module, key


def _branch_value(when: dict[Any, Any], branch: bool) -> Any:
    # YAML 1.1 parses unquoted `true:` / `false:` keys as booleans; accept both forms.
    if branch in when:
        return when[branch]
    return when[str(branch).lower()]


def _validate_threshold_entry(where: str, entry: dict[str, Any]) -> None:
    float(entry["threshold"])
    when = entry.get("threshold_when")
    if when is None:
        return
    _split_signal_path(when["signal"])
    for branch in (True, False):
        try:
            float(_branch_value(when, branch))
        except KeyError as exc:
            raise ValueError(f"{where}.threshold_when is missing the {str(branch).lower()} branch") from exc


def lookup_signal(signals: Mapping[str, Any] | None, path: str) -> Any:
    """Value at "<module>.<key>" in published module signals, or None if absent."""
    module, key = _split_signal_path(path)
    payload = (signals or {}).get(module)
    return payload.get(key) if isinstance(payload, Mapping) else None


def resolve_threshold(entry: dict[str, Any], signals: Mapping[str, Any] | None) -> tuple[float, dict[str, Any]]:
    """Scalar threshold, or the threshold_when branch selected by a boolean
    signal. Returns (threshold, audit record)."""
    when = entry.get("threshold_when")
    if when is None:
        return float(entry["threshold"]), {"branch": "scalar", "signal": None, "signal_value": None}
    value = lookup_signal(signals, when["signal"])
    if isinstance(value, bool):
        return (float(_branch_value(when, value)),
                {"branch": str(value).lower(), "signal": when["signal"], "signal_value": value})
    return float(entry["threshold"]), {"branch": "fallback", "signal": when["signal"], "signal_value": value}


# -- 2. thresholds ----------------------------------------------------------
def apply_thresholds(scores: list[ContentScore], cfg: dict[str, Any], notes: list[str],
                     signals: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Set threshold + fired on each score. Returns one audit record per score
    naming the threshold branch taken."""
    audit: list[dict[str, Any]] = []
    for score in scores:
        entry = cfg["categories"].get(score.code.value)
        if entry is None:
            score.threshold, score.fired = None, False
            notes.append(f"[decision] no threshold configured for {score.code.value}; not fired")
            continue
        score.threshold, record = resolve_threshold(entry, signals)
        score.fired = score.score >= score.threshold
        if record["branch"] == "fallback":
            notes.append(f"[decision] {score.code.value}: signal {record['signal']} absent or not bool; "
                         f"scalar threshold used")
        audit.append({"code": score.code.value, "source": score.source, "threshold": score.threshold, **record})
    return audit


def apply_binary_offensive(cfg: dict[str, Any], signals: Mapping[str, Any] | None,
                           notes: list[str]) -> dict[str, Any] | None:
    """Threshold the channel-level binary offensive scores, if configured.

    Flags iff score > threshold: the rule the threshold was derived with
    (protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md §3, the study's C12-3), so a
    score exactly at the threshold - the fitted CAL row itself - is not flagged (owner decision
    2026-09-19; it replaces the 2026-09-15 decision to keep `>=` here). Content-code rows and guards
    keep `>=` in apply_thresholds / guard_is_active: no derivation defines them otherwise."""
    entry = cfg.get("binary_offensive")
    if entry is None:
        return None
    threshold, record = resolve_threshold(entry, signals)
    channels: dict[str, Any] = {}
    for channel, path in entry["channels"].items():
        value = lookup_signal(signals, path)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            channels[channel] = {"score": None, "fired": None}
            continue
        channels[channel] = {"score": float(value), "fired": float(value) > threshold}
    present = [c for c in channels.values() if c["fired"] is not None]
    if present and record["branch"] == "fallback":
        notes.append(f"[decision] binary_offensive: signal {record['signal']} absent or not bool; "
                     f"scalar threshold used")
    return {"threshold": threshold, **record, "channels": channels,
            "fired": any(c["fired"] for c in present) if present else None,
            "action": entry["action"]}


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


def module_of(source: str) -> str:
    """"m1_lexicon@raw" -> "m1_lexicon"."""
    return source.split("@", 1)[0]


def spans_overlap(a: tuple[int, int] | list[int], b: tuple[int, int] | list[int]) -> bool:
    return a[0] < b[1] and b[0] < a[1]


def guard_applies(guard: GuardResult, score: ContentScore, cfg: dict[str, Any],
                  emits_spans: Mapping[str, bool] | None = None) -> bool:
    """ADR-001 scoping rule.

    - never across modules: the guard's source module must have produced the score
    - both spans present: suppress only when they overlap
    - either span missing: same-module fallback ONLY for a module that declares
      `emits_spans = False`; for a span-emitting module a missing span never
      suppresses (the pipeline already drops such items - this is defence in depth)
    - still limited to the codes/families the guard's config lists
    """
    module = module_of(guard.source)
    if not guard.source or module != module_of(score.source):
        return False
    if not any(_covers(e, score.code) for e in cfg["guards"][guard.code.value]["suppresses"]):
        return False
    if guard.span is not None and score.span is not None:
        return spans_overlap(guard.span, score.span)
    return not (emits_spans or {}).get(module, False)


def apply_guards(content: list[ContentScore], guards: list[GuardResult],
                 cfg: dict[str, Any], notes: list[str], emits_spans: Mapping[str, bool] | None = None) -> None:
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
        active = sorted((g for g in by_code.get(GuardCode(code_name), []) if g.active),
                        key=lambda g: g.score, reverse=True)
        for score in content:
            if not score.fired:
                continue
            guard = next((g for g in active if guard_applies(g, score, cfg, emits_spans)), None)
            if guard is None:
                continue
            score.fired = False
            if score.code not in guard.suppressed:
                guard.suppressed.append(score.code)
            notes.append(f"[decision] {score.code.value} from {score.source} span={score.span} "
                         f"suppressed by guard {code_name} from {guard.source} span={guard.span}")


# -- 5. thread --------------------------------------------------------------
def apply_thread(thread: ThreadSignal | None, cfg: dict[str, Any], post_offensive: bool) -> None:
    """The thread rule fires only on an OFFENSIVE post (owner decision, ADR-004).

    Escalation is an action on THIS post. Repetition raises the severity of an
    offensive post; it never creates severity where the post itself has none,
    so a clean message is not escalated on the strength of earlier ones - that
    would be acting on the person rather than the content."""
    if thread is None:
        return
    rule = cfg["thread"]
    thread.threshold = int(rule["min_repeats"])
    target_ok = thread.same_target is True or not rule["same_target_required"]
    thread.fired = (bool(rule["enabled"]) and post_offensive
                    and thread.repeat_count >= thread.threshold and target_ok)


# -- fast path ----------------------------------------------------------------
def fast_path_hit(content: list[ContentScore], guards: list[GuardResult], cfg: dict[str, Any],
                  signals: Mapping[str, Any] | None = None, target: TargetResult | None = None) -> bool:
    """True when the evidence so far is decisive enough to skip the remaining
    modules. The pipeline checks that `fast_path.requires` have run."""
    fast = cfg["fast_path"]
    if not fast["enabled"]:
        return False
    if any(guard_is_active(g, cfg) for g in guards):
        return False
    margin = float(fast["margin"])
    # Nothing is decided yet, so decision-owned fields on these scores are
    # ignored: the best raw score per code is compared, whatever `fired` says.
    best: dict[ContentCode, float] = {}
    a_code = family_a_code(target, cfg)[0]
    for score in content:
        if score.code is not ContentCode.CLEAN:
            code = a_code if score.code in TARGETED_A else score.code  # same assignment as decide_post
            best[code] = max(score.score, best.get(code, score.score))
    for code, value in best.items():
        entry = cfg["categories"].get(code.value)
        if entry is not None and value >= resolve_threshold(entry, signals)[0] + margin:
            return True
    return False


# -- 0. reset ---------------------------------------------------------------
def reset_decision_fields(result: AnalysisResult) -> list[str]:
    """Clear every decision-owned field before deciding (CLAUDE.md rule 4).

    Whoever built `result` - the pipeline, the eval harness, a test, a direct
    caller - may have left values in fields only this file assigns. They are
    never trusted: each is reset here and recomputed below, so deciding twice
    gives the same answer. Returns one line per offending source, for notes.
    """
    found: dict[str, set[str]] = {}

    def saw(source: str, what: str) -> None:
        found.setdefault(source or "<unknown source>", set()).add(what)

    for score in result.content:
        if score.threshold is not None or score.fired is not None:
            saw(module_of(score.source), f"threshold/fired on {score.code.value}")
        score.threshold, score.fired = None, None
    for guard in result.guards:
        if guard.threshold is not None or guard.active is not None or guard.suppressed:
            saw(module_of(guard.source), f"threshold/active/suppressed on guard {guard.code.value}")
        guard.threshold, guard.active, guard.suppressed = None, None, []
    if result.form.active:
        saw("<form>", "form.active")
    result.form.active = []
    if result.thread is not None:
        if result.thread.threshold is not None or result.thread.fired is not None:
            saw(result.thread.source, "threshold/fired on thread")
        result.thread.threshold, result.thread.fired = None, None
    return [f"[decision] {source} set decision-owned {', '.join(sorted(whats))}; reset before deciding"
            for source, whats in found.items()]


# -- entry points -------------------------------------------------------------
def decide(result: AnalysisResult, cfg: dict[str, Any]) -> AnalysisResult:
    """Fill every decision-owned field of `result` in place and return it.

    Equivalent to `decide_post` then `conclude`. A caller that must act on the
    post-level decision before the thread rule (the repetition counter only
    counts offensive posts) calls the two stages itself."""
    decide_post(result, cfg)
    return conclude(result, cfg)


def post_is_offensive(result: AnalysisResult) -> bool:
    """After `decide_post`: did the post itself fire - a content code that
    survived the guards, or the binary offensive score? Form patterns never
    count (obfuscation is not content), and neither does degradation: an
    incomplete judgement is not a finding of abuse."""
    binary = result.signals.get("decision", {}).get("binary_offensive") or {}
    return bool(result.fired()) or bool(binary.get("fired"))


def decide_post(result: AnalysisResult, cfg: dict[str, Any]) -> AnalysisResult:
    """Stages 0-4: reset, family A by target, thresholds, binary score, guards, channel fusion, form."""
    result.notes.extend(reset_decision_fields(result))
    raw_scores = [s for s in result.content if s.code is not ContentCode.CLEAN]
    decision_signals = result.signals.setdefault("decision", {})
    decision_signals["family_a"] = resolve_family_a(raw_scores, result.target, cfg, result.notes)
    decision_signals["threshold_branches"] = apply_thresholds(raw_scores, cfg, result.notes, result.signals)
    decision_signals["binary_offensive"] = apply_binary_offensive(cfg, result.signals, result.notes)
    apply_guards(raw_scores, result.guards, cfg, result.notes,
                 result.signals.get("pipeline", {}).get("emits_spans"))
    decision_signals["channel_scores"] = [
        {"code": s.code.value, "score": s.score, "source": s.source,
         "span": list(s.span) if s.span is not None else None,
         "threshold": s.threshold, "fired": s.fired}
        for s in raw_scores
    ]
    result.content = fuse_channels(raw_scores, cfg)
    apply_form(result.form, cfg)
    decision_signals["post_offensive"] = post_is_offensive(result)
    return result


def conclude(result: AnalysisResult, cfg: dict[str, Any]) -> AnalysisResult:
    """Stage 5 and the verdict: thread rule, action, Turkish explanation."""
    if result.thread is not None:
        # The thread may have been attached after decide_post; it is reset here too.
        result.thread.threshold, result.thread.fired = None, None
    apply_thread(result.thread, cfg, post_is_offensive(result))
    verdict, driver = actions.resolve(result, cfg)
    result.verdict = verdict
    result.explanation = actions.explain(result, verdict, driver)
    return result
