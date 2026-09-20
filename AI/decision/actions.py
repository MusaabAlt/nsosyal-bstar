"""Verdict resolution and the one-sentence Turkish explanation.

The verdict is the most severe action among (a) the configured actions of
every fired content code, (b) the binary offensive score and (c) the thread
rule, using ACTION_PRECEDENCE from the contracts. Nothing here reads a
threshold; `fired` flags arrive already set by decision/fusion.py.

FAIL CLOSED (policy decided by the project owner, Phase 9): when the pipeline
reports any degraded module (stub, failure, unavailable, invalid output), the
system cannot judge. A verdict that would be clean becomes DEGRADED_ACTION;
more severe verdicts stand. The explanation always says the judgement is
incomplete and why.
"""
from __future__ import annotations

from typing import Any

from contracts.codes import ACTION_PRECEDENCE, Action, tr_label
from contracts.schema import AnalysisResult, ContentScore

# Policy, not a tunable: an incomplete judgement may never be clean.
DEGRADED_ACTION = Action.REVIEW

# The actions that put a comment in front of a moderator. Only these are
# banded: a channel configured to block or to nudge already decides alone.
ASKS_FOR_PERSON = frozenset({Action.REVIEW, Action.ESCALATE})

_VERB_TR: dict[Action, str] = {
    Action.BLOCK: "engellendi",
    Action.ESCALATE: "üst incelemeye iletildi",
    Action.REVIEW: "incelemeye alındı",
    Action.NUDGE: "kullanıcı uyarılarak yayımlandı",
}

_KIND_TR: dict[str, str] = {
    "stub": "henüz uygulanmadı",
    "failed": "hata verdi",
    "invalid_output": "geçersiz çıktı üretti",
}


def severity(action: Action) -> int:
    """Lower is more severe."""
    return ACTION_PRECEDENCE.index(action)


def action_for(score: ContentScore, cfg: dict[str, Any]) -> Action:
    return Action(cfg["categories"][score.code.value]["action"])


def _fired_score(binary: dict[str, Any]) -> float | None:
    """The strongest channel score that crossed the threshold, or None."""
    scores = [c["score"] for c in binary.get("channels", {}).values()
              if c.get("fired") and isinstance(c.get("score"), (int, float))]
    return max(scores) if scores else None


def binary_action(binary: dict[str, Any], cfg: dict[str, Any]) -> Action:
    """The binary offensive channel's action for THIS score.

    thresholds.yaml `binary_offensive.action` is what the channel asks for
    while the score is uncertain. `binary_offensive.review_band` narrows that
    to a range: above it the score is decisive and the content is acted on
    without a person, below it the same. Nothing is decided here that the
    config does not name - the band, its edges and both replacement actions
    all come from the file, and without a band the configured action stands
    exactly as before.
    """
    configured = Action(binary["action"])
    band = (cfg.get("binary_offensive") or {}).get("review_band")
    if not band or configured not in ASKS_FOR_PERSON:
        return configured
    score = _fired_score(binary)
    if score is None:
        return configured
    if score > float(band["high"]):
        return Action(band["above_action"])
    if score < float(band["low"]):
        return Action(band["below_action"])
    return configured


def degraded_modules(result: AnalysisResult) -> list[dict[str, Any]]:
    return list(result.signals.get("pipeline", {}).get("degraded") or [])


def resolve(result: AnalysisResult, cfg: dict[str, Any]) -> tuple[Action, ContentScore | str | None]:
    """Return the verdict and what drove it: a ContentScore, "thread",
    "binary_offensive", "degraded", or None when the verdict is clean."""
    driver: ContentScore | str | None = None
    verdict = Action.CLEAN
    for score in result.fired():  # highest score first, so ties keep the stronger score
        action = action_for(score, cfg)
        if severity(action) < severity(verdict):
            verdict, driver = action, score
    binary = result.signals.get("decision", {}).get("binary_offensive")
    if binary and binary.get("fired"):
        action = binary_action(binary, cfg)
        if severity(action) < severity(verdict):
            verdict, driver = action, "binary_offensive"
    if result.thread is not None and result.thread.fired:
        thread_action = Action(cfg["thread"]["action"])
        if severity(thread_action) < severity(verdict):
            verdict, driver = thread_action, "thread"
    if verdict is Action.CLEAN and degraded_modules(result):
        verdict, driver = DEGRADED_ACTION, "degraded"
    return verdict, driver


def _incomplete_clause(degraded: list[dict[str, Any]]) -> str:
    parts = [f"{d['module']} {' ve '.join(_KIND_TR.get(k, k) for k in d.get('kinds', []))}" for d in degraded]
    return f"değerlendirme eksik çünkü {', '.join(parts)}"


def _base_sentence(result: AnalysisResult, verdict: Action, driver: ContentScore | str | None) -> str:
    """The explanation without its final period."""
    if verdict is Action.CLEAN:
        for guard in result.guards:
            if guard.suppressed:
                code = guard.suppressed[0]
                return (f"'{tr_label(code)}' ({code.value}) sinyali '{tr_label(guard.code)}' "
                        f"koruması nedeniyle bastırıldı, içerik temiz kabul edildi")
        return "İçerikte eşiği aşan saldırgan bir kategori bulunmadı"
    if driver == "thread" and result.thread is not None:
        # Counted per sender and target across threads (ADR-004), so no "aynı başlıkta".
        return (f"Aynı gönderenin aynı hedefe yönelik {result.thread.repeat_count} saldırgan mesajı "
                f"nedeniyle içerik {_VERB_TR[verdict]}")
    if driver == "binary_offensive":
        return f"İçerik genel saldırganlık skoru eşiği aştığı için {_VERB_TR[verdict]}"
    assert isinstance(driver, ContentScore)
    return f"İçerik '{tr_label(driver.code)}' ({driver.code.value}) nedeniyle {_VERB_TR[verdict]}"


def explain(result: AnalysisResult, verdict: Action, driver: ContentScore | str | None) -> str:
    """Exactly one Turkish sentence for the end user / moderator UI."""
    degraded = degraded_modules(result)
    if driver == "degraded":
        return (f"Karar verilemedi, içerik temiz sayılmadı ve {_VERB_TR[verdict]}: "
                f"{_incomplete_clause(degraded)}.")
    base = _base_sentence(result, verdict, driver)
    if degraded:
        return f"{base}; ancak {_incomplete_clause(degraded)}."
    return f"{base}."
