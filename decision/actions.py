"""Verdict resolution and the one-sentence Turkish explanation.

The verdict is the most severe action among (a) the configured actions of
every fired content code and (b) the thread rule, using ACTION_PRECEDENCE from
the contracts. Nothing here reads a threshold; `fired` flags arrive already
set by decision/fusion.py.
"""
from __future__ import annotations

from typing import Any, Iterable

from contracts.codes import ACTION_PRECEDENCE, Action, tr_label
from contracts.schema import AnalysisResult, ContentScore

_VERB_TR: dict[Action, str] = {
    Action.BLOCK: "engellendi",
    Action.ESCALATE: "üst incelemeye iletildi",
    Action.REVIEW: "incelemeye alındı",
    Action.NUDGE: "kullanıcı uyarılarak yayımlandı",
}


def severity(action: Action) -> int:
    """Lower is more severe."""
    return ACTION_PRECEDENCE.index(action)


def most_severe(actions: Iterable[Action]) -> Action:
    return min(actions, key=severity, default=Action.CLEAN)


def action_for(score: ContentScore, cfg: dict[str, Any]) -> Action:
    return Action(cfg["categories"][score.code.value]["action"])


def resolve(result: AnalysisResult, cfg: dict[str, Any]) -> tuple[Action, ContentScore | str | None]:
    """Return the verdict and what drove it: a ContentScore, "thread",
    "binary_offensive", or None when the verdict is clean."""
    driver: ContentScore | str | None = None
    verdict = Action.CLEAN
    for score in result.fired():  # highest score first, so ties keep the stronger score
        action = action_for(score, cfg)
        if severity(action) < severity(verdict):
            verdict, driver = action, score
    binary = result.signals.get("decision", {}).get("binary_offensive")
    if binary and binary.get("fired"):
        binary_action = Action(binary["action"])
        if severity(binary_action) < severity(verdict):
            verdict, driver = binary_action, "binary_offensive"
    if result.thread is not None and result.thread.fired:
        thread_action = Action(cfg["thread"]["action"])
        if severity(thread_action) < severity(verdict):
            verdict, driver = thread_action, "thread"
    return verdict, driver


def explain(result: AnalysisResult, verdict: Action, driver: ContentScore | str | None) -> str:
    """Exactly one Turkish sentence for the end user / moderator UI."""
    if verdict is Action.CLEAN:
        stubs = result.signals.get("pipeline", {}).get("stub_modules") or []
        if stubs:
            return (f"Kesin sonuç değil: {', '.join(stubs)} henüz uygulanmadığı için içerik yalnızca kısmen "
                    f"denetlendi ve eşiği aşan bir kategori bulunmaması içeriğin temiz olduğu anlamına gelmez.")
        for guard in result.guards:
            if guard.suppressed:
                code = guard.suppressed[0]
                return (f"'{tr_label(code)}' ({code.value}) sinyali '{tr_label(guard.code)}' "
                        f"koruması nedeniyle bastırıldı, içerik temiz kabul edildi.")
        return "İçerikte eşiği aşan saldırgan bir kategori bulunmadı."
    if driver == "thread" and result.thread is not None:
        return (f"Aynı başlıkta {result.thread.repeat_count} tekrar tespit edildiği için "
                f"içerik {_VERB_TR[verdict]}.")
    if driver == "binary_offensive":
        return f"İçerik genel saldırganlık skoru eşiği aştığı için {_VERB_TR[verdict]}."
    assert isinstance(driver, ContentScore)
    return f"İçerik '{tr_label(driver.code)}' ({driver.code.value}) nedeniyle {_VERB_TR[verdict]}."
