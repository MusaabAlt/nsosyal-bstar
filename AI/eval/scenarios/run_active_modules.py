"""Active-module scenario suite: proves, through the REAL pipeline, that every runtime module M0-M6
executes and what each one contributes to a real analysis result.

    cd AI && python eval/scenarios/run_active_modules.py

Writes eval/results/active_modules_report.md and eval/results/active_modules_traces.txt: harness
output, not committed (eval/README.md). The scenarios are defined below, each with the oracle its
expectation comes from (a spec, a protocol, the annotation guideline or an existing test), never
from a run.

Checks (a scenario states only the ones its oracle supports):
  m0        exact m0 signal values              form      exact set of form codes (m0 + m2)
  m2_codes  exact set of m2's codes             m1_roots  exact set of matched roots
  m1_norm   m1 also scored m2's normalized channel (a m1_lexicon@normalized score reached the decision)
  target    m6's target type                    fired     exact set of fired content codes (after guards)
  suppressed  {guard: codes it suppressed}      binary    binary_offensive fired (model-dependent)
  m3_norm   m3 scored the normalized channel separately (norm_score present and different from raw_score)
  m3_a      m3's A head published an A-family score ({emitted}) and whether one fired ({fired})
  m4        exact m4 signal values              m4_gap    m4's norm_minus_raw is positive
  d1        m5 emitted D1 (BLOCKED if m5 is ever degraded: a degraded module's silence is not evidence)
  m5_rules  exact set of m5 rules satisfied     m5_excluded  m5 exclusion reasons that must appear
  degraded  exact list of degraded modules
and always the verdict, computed from decision/thresholds.yaml with actions.severity: the actions of
the expected fired codes, the binary action when the binary score is expected (or, for a scenario
that states no binary expectation, observed) to fire, and the fail-closed action when nothing fires
on a degraded result.

Result: FAIL when any check fails (tagged KNOWN_LIMITATION when the repository already documents
the gap); otherwise BLOCKED when a check cannot run on this system (never a pass); otherwise PASS.
Exit status 1 when an untagged FAIL exists. m3's probabilities belong to the loaded artifact
(CURRENT_ARTIFACT_OBSERVATION); the report names it.
"""
from __future__ import annotations

import json
import platform
import subprocess
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

AI_ROOT = Path(__file__).resolve().parents[2]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from contracts.codes import Action  # noqa: E402
from contracts.schema import AnalysisResult  # noqa: E402
from decision import actions  # noqa: E402
from pipeline.run import Pipeline  # noqa: E402

RESULTS = AI_ROOT / "eval" / "results"
MODULES = ("m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon", "m3_encoder", "m4_implicit", "m5_sarcasm")
ZWSP, CYRILLIC_A = chr(0x200B), chr(0x0430)
NONE: list[str] = []            # no module is a stub or degraded in a valid run (m5 Stage 1 since 2026-09-19)
QUOTE_GAP = ("no module produces QUOTE_COUNTERSPEECH (contracts/codes.py) and thresholds.yaml configures no such "
             "guard (HANDOVER decision #17): m1 matches mentioned words like used ones")
M5_MARKER_GAP = ("m5 Stage 1 fires only on an explicit marker of the inversion (protocols/m5_stage1_deterministic_protocol.md "
                 "§3): without one, sarcastic and sincere praise are the same sentence")
STAGE1_RECALL_GAP = ("stage 1 is one threshold on m3's raw binary score; veiled C-type text without hostile vocabulary "
                     "scores low (m4 spec §2: lexicon-free recall is the project's open problem; C1-C5 not trained)")
STAGE1_SIGNALS = {"stage": 1, "stage1_input_present": True, "stage1_artifact_match": True}


@dataclass(frozen=True)
class Scenario:
    id: str
    group: str
    title: str
    text: str
    oracle: str
    expect: dict[str, Any] = field(default_factory=dict)
    known_limitation: str | None = None


SCENARIOS: tuple[Scenario, ...] = (
    # -- M0: character safety --------------------------------------------------------------------
    Scenario("M0-01", "M0", "zero-width space inside an insult", "ap" + ZWSP + "tal herif",
             "m0 spec (invisible characters); tests/test_end_to_end.py zero-width case; M1-ROUTE-1 (aptal -> B1)",
             {"m0": {"invisible_removed": 1, "charsafe_changed": True}, "form": ["ZERO_WIDTH"], "m1_roots": ["aptal"],
              "fired": ["B1"], "degraded": NONE}),
    Scenario("M0-02", "M0", "Cyrillic homoglyph inside an insult", CYRILLIC_A + "ptal herif",
             "m0 spec (confusables -> HOMOGLYPH); m0 test_unit homoglyph cases; M1-ROUTE-1",
             {"m0": {"homoglyphs_mapped": 1, "charsafe_changed": True}, "form": ["HOMOGLYPH"], "m1_roots": ["aptal"],
              "fired": ["B1"], "degraded": NONE}),
    Scenario("M0-03", "M0", "Turkish uppercase I never yields the profane root", "SIKINTI YOK",
             "m0 test_unit test_sikinti_never_yields_profane_root; m1 trap list",
             {"m0": {"charsafe_changed": True}, "m1_roots": [], "fired": [], "degraded": NONE}),
    # -- M1: lexicon routes -----------------------------------------------------------------------
    Scenario("M1-A", "M1", "profane root, no target -> A1", "siktir git",
             "M1-ROUTE-1 (sik in ROUTE_A); ADR-005 (target none -> A1)",
             {"m1_roots": ["sik"], "target": "none", "fired": ["A1"], "degraded": NONE}),
    Scenario("M1-B1", "M1", "ordinary insult -> B1", "salak herif",
             "M1-ROUTE-1 (salak in ROUTE_B1)", {"m1_roots": ["salak"], "fired": ["B1"], "degraded": NONE}),
    Scenario("M1-B2", "M1", "threat -> B2", "öldürücem seni",
             "M1-ROUTE-1 (ROUTE_B2); tests/test_end_to_end.py routes case",
             {"m1_roots": ["öldürücem"], "fired": ["B2"], "degraded": NONE}),
    Scenario("M1-B3", "M1", "curse -> B3", "geber",
             "M1-ROUTE-1 (ROUTE_B3); tests/test_end_to_end.py routes case",
             {"m1_roots": ["geber"], "fired": ["B3"], "degraded": NONE}),
    # -- M2: de-obfuscation, parallel channel ----------------------------------------------------------
    Scenario("M2-LEET", "M2", "leet digits", "sal4k",
             "m2 README tier 1 (LEET); m1 spec §3 (both channels)",
             {"m2_codes": ["LEET"], "form": ["LEET"], "m1_roots": ["salak"], "m1_norm": True, "fired": ["B1"],
              "degraded": NONE}),
    Scenario("M2-SPACED", "M2", "letters spaced out", "g e b e r",
             "m2 README tier 1 (SPACED)",
             {"m2_codes": ["SPACED"], "form": ["SPACED"], "m1_roots": ["geber"], "m1_norm": True, "fired": ["B3"],
              "degraded": NONE}),
    Scenario("M2-PUNCT", "M2", "letters split by punctuation", "d.e.f.o.l",
             "m2 README tier 1 (PUNCT_SPLIT)",
             {"m2_codes": ["PUNCT_SPLIT"], "form": ["PUNCT_SPLIT"], "m1_roots": ["defol"], "m1_norm": True,
              "fired": ["B3"], "degraded": NONE}),
    Scenario("M2-REPEAT", "M2", "repeated letter", "ahmakkkk",
             "m2 README tier 1 (REPEAT)",
             {"m2_codes": ["REPEAT"], "form": ["REPEAT"], "m1_roots": ["ahmak"], "m1_norm": True, "fired": ["B1"],
              "degraded": NONE}),
    # -- M3: the rule-v4 encoder (binary + A heads) -----------------------------------------------------
    Scenario("M3-BIN", "M3", "group attack with no profane root: binary head", "Bu Suriyeliler ülkeyi mahvetti",
             "m4 spec §1-§3 (lexicon-free slice: offensive with no profane root; hostility generalised to a group)",
             {"m1_roots": [], "fired": [], "binary": True, "m3_a": {"emitted": True, "fired": False}, "degraded": NONE}),
    Scenario("M3-A", "M3", "explicit profanity: the A head fires with m1", "Siktir git buradan",
             "docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md (explicit obscene root = 1); ADR-005 A1 carrier",
             {"m1_roots": ["sik"], "fired": ["A1"], "m3_a": {"emitted": True, "fired": True}, "degraded": NONE}),
    Scenario("M3-HARDNEG", "M3", "clean hard negative for both heads", "amacı ne",
             "M1-PREC-1 clean list (tests/test_end_to_end.py); A-head guideline (no obscene root = 0)",
             {"m1_roots": [], "fired": [], "binary": False, "m3_a": {"emitted": True, "fired": False}, "degraded": NONE}),
    # -- M4: stage 1 -------------------------------------------------------------------------------
    Scenario("M4-01", "M4", "the spec's own C1 example (veiled stereotype)", "Onlardan başka ne beklenir",
             "m4 spec §3 (`Onlardan başka ne beklenir` is C1); stage 1 = binary_offensive on m3's raw score (ADR-006)",
             {"m1_roots": [], "fired": [], "binary": True, "m4": STAGE1_SIGNALS, "degraded": NONE},
             known_limitation=STAGE1_RECALL_GAP),
    Scenario("M4-02", "M4", "obfuscation hides the insult from the raw channel", "5erefsiz",
             "m4 spec §4 (channel disagreement); thresholds.yaml binary_offensive (raw channel only, owner decision)",
             {"m2_codes": ["LEET", "DEASCII"], "m1_roots": ["şerefsiz"], "fired": ["B1"], "m3_norm": True,
              "m4_gap": True, "m4": STAGE1_SIGNALS, "degraded": NONE}),
    # -- M5: Stage-1 deterministic D1 ---------------------------------------------------------------
    Scenario("M5-R1", "M5", "scare-quoted praise at the addressee", "Bu kadar 'derin' bir yorum yapman etkileyici.",
             "m5 spec §1 (second D1 example); M5-S1 R1",
             {"d1": True, "m5_rules": ["R1_SCARE_QUOTE"], "m1_roots": [], "fired": ["D1"], "degraded": NONE}),
    Scenario("M5-R3", "M5", "congratulated failure", "Aferin sana, yine her şeyi berbat ettin.",
             "m5 spec §5 (praise + contradicting result = polarity inversion); M5-S1 R3",
             {"d1": True, "m5_rules": ["R3_CONGRATULATED_FAILURE"], "m1_roots": [], "fired": ["D1"], "degraded": NONE}),
    Scenario("M5-R2", "M5", "praise closed by an ironic tabii", "Çok zekisin tabii.",
             "m5 spec §11 (raw marker `tabii`); M5-S1 R2",
             {"d1": True, "m5_rules": ["R2_CLAUSE_FINAL_TABII"], "m1_roots": [], "fired": ["D1"], "degraded": NONE}),
    Scenario("M5-SPEC1", "M5", "the spec's first D1 example has no explicit marker",
             "Zekânı hayranlıkla izliyorum, gerçekten.", "m5 spec §1 (first D1 example)",
             {"d1": True, "m1_roots": [], "degraded": NONE}, known_limitation=M5_MARKER_GAP),
    Scenario("M5-NEG-SINCERE", "M5", "sincere praise", "Aferin sana, sınavı geçtin.",
             "m5 spec §3, §11 (sincere praise is a hard negative)",
             {"d1": False, "fired": [], "binary": False, "degraded": NONE}),
    Scenario("M5-NEG-BENIGN", "M5", "benign irony at an object", "Harika, otobüs yine gelmedi.",
             "m5 spec §8 (critical negative control)",
             {"d1": False, "fired": [], "binary": False, "degraded": NONE}),
    Scenario("M5-NEG-INSULT", "M5", "direct insult, no sarcastic structure", "Sen tam bir salaksın",
             "m5 spec §3 (direct abuse is not D1; B1 via m1)",
             {"d1": False, "fired": ["B1"], "degraded": NONE}),
    Scenario("M5-NEG-REPORTED", "M5", "reported sarcasm", "'Aferin sana, yine her şeyi berbat ettin.' dedi hocam.",
             "m5 spec §11 (quoting sarcasm is not producing it)",
             {"d1": False, "m5_excluded": ["X_REPORTED"], "fired": [], "degraded": NONE}),
    # -- M6: target ---------------------------------------------------------------------------------
    Scenario("M6-IND", "M6", "second person -> individual", "Sen tam bir aptalsın",
             "protocols/m6_target_guideline.md (second person); M1-ROUTE-1",
             {"target": "individual", "m1_roots": ["aptal"], "fired": ["B1"], "degraded": NONE}),
    Scenario("M6-GRP", "M6", "group stem -> group -> A3", "Suriyeliler orospu çocuğu",
             "m6 guideline + gazetteer groups_tr.txt; ADR-005 (group -> A3)",
             {"target": "group", "m1_roots": ["orospu"], "fired": ["A3"], "degraded": NONE}),
    Scenario("M6-NH", "M6", "insult at a program -> non_human, guard suppresses", "Bu program tam bir aptal",
             "tests/test_end_to_end.py non-human guard case; thresholds.yaml NON_HUMAN_TARGET suppresses B1",
             {"target": "non_human", "m1_roots": ["aptal"], "fired": [], "suppressed": {"NON_HUMAN_TARGET": ["B1"]},
              "degraded": NONE}),
    Scenario("M6-B4", "M6", "phone number published to harass -> B4 doxing", "Onun numarası 0532 123 45 67, herkes arasın.",
             "protocols/m6_target_guideline.md (Turkish mobile number -> B4); placeholder number",
             {"m1_roots": [], "fired": ["B4"], "degraded": NONE}),
    # -- combinations ------------------------------------------------------------------------------
    Scenario("X-M2M1", "M2+M1", "leet + ASCII-flattened insult, matched on both channels", "ger1zekal1",
             "m2 README (LEET, DEASCII); m1 spec §3",
             {"m2_codes": ["LEET", "DEASCII"], "m1_roots": ["gerizekalı"], "m1_norm": True, "fired": ["B1"],
              "degraded": NONE}),
    Scenario("X-M2M3", "M2+M3", "m3 scores m2's channel separately", "s a l a k",
             "m3 spec §4 (both channels); m2 spec (parallel channel exists because obfuscation hides offence)",
             {"m2_codes": ["SPACED"], "m3_norm": True, "m4_gap": True, "fired": ["B1"], "degraded": NONE}),
    Scenario("X-M1M6", "M1+M6", "profane root at the addressee -> A2", "Sen tam bir orospu çocuğusun",
             "ADR-005 (individual -> A2)",
             {"target": "individual", "m1_roots": ["orospu"], "fired": ["A2"], "degraded": NONE}),
    Scenario("X-M3M4", "M3+M4", "lexicon-free attack caught by stage 1", "Senin gibi insanlar yüzünden bu ülke batıyor",
             "m4 spec §1-§4 (lexicon-free slice, stage 1); ADR-006",
             {"m1_roots": [], "fired": [], "binary": True, "m4": STAGE1_SIGNALS, "degraded": NONE}),
    Scenario("X-M3M5", "M3+M5", "D1 beside the encoder's scores", "Çok akıllısın (!)",
             "M5-S1 R4 (TDK irony mark); m3 spec §4",
             {"d1": True, "m5_rules": ["R4_IRONY_MARK"], "m1_roots": [], "fired": ["D1"],
              "m3_a": {"emitted": True, "fired": False}, "degraded": NONE}),
    Scenario("X-CONFLICT", "multi-signal", "profanity + threat: the most severe action wins",
             "Siktir git yoksa öldürücem seni",
             "contracts ACTION_PRECEDENCE; decision/actions.py resolve; ADR-005",
             {"target": "individual", "m1_roots": ["sik", "öldürücem"], "fired": ["A2", "B2"], "degraded": NONE}),
    Scenario("X-HARDNEG-01", "hard negative", "'sık' is not 'sik'", "canım sıkıldı",
             "M1-PREC-1 (protocols/m1_positive_matching_precision_protocol.md); tests/test_end_to_end.py clean list",
             {"m1_roots": [], "fired": [], "binary": False, "degraded": NONE}),
    Scenario("X-HARDNEG-02", "hard negative", "party name 'AK' is not 'amk'", "AK Parti kazandı",
             "M1-PREC-1; tests/test_end_to_end.py clean list",
             {"m1_roots": [], "fired": [], "binary": False, "degraded": NONE}),
    Scenario("X-CLEAN", "clean", "ordinary sentence -> clean", "Bu şarkı çok güzel",
             "decision/actions.py: nothing fired and nothing degraded -> clean",
             {"m1_roots": [], "fired": [], "binary": False, "d1": False, "degraded": NONE}),
    Scenario("X-QUOTE", "quoted/reported", "profanity quoted to report it", 'Adam bana "siktir git" demiş, ayıp',
             "docs/annotation/A_HEAD_PROFANITY_GUIDELINE.md §9 (this sentence is labelled 0: mentioned, not used)",
             {"fired": [], "degraded": NONE}, known_limitation=QUOTE_GAP),
)


# -- helpers -----------------------------------------------------------------------------------
def visible(text: str) -> str:
    """Escape invisible and cross-script characters so a report shows what the input really is."""
    out = []
    for ch in text:
        hidden = unicodedata.category(ch) in ("Cf", "Cc", "Mn") or "CYRILLIC" in unicodedata.name(ch, "")
        out.append(f"\\u{ord(ch):04x}" if hidden else ch)
    return "".join(out)


def cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=AI_ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        return f"<git {' '.join(args)} failed: {exc}>"


def expected_verdict(expect: dict[str, Any], result: AnalysisResult, cfg: dict[str, Any]) -> tuple[Action, str]:
    candidates = [Action(cfg["categories"][code]["action"]) for code in expect.get("fired", [])]
    observed_binary = bool((result.signals["decision"].get("binary_offensive") or {}).get("fired"))
    binary = expect.get("binary", observed_binary)
    if binary:
        candidates.append(Action(cfg["binary_offensive"]["action"]))
    verdict = min(candidates, key=actions.severity) if candidates else Action.CLEAN
    degraded = expect.get("degraded", [d["module"] for d in actions.degraded_modules(result)])
    if verdict is Action.CLEAN and degraded:
        verdict = actions.DEGRADED_ACTION
    basis = "binary expected" if "binary" in expect else "binary observed (not judged)"
    return verdict, basis


def run_checks(s: Scenario, result: AnalysisResult) -> list[tuple[str, str, str]]:
    """(check, PASS | FAIL | BLOCKED, detail) for every check the scenario states."""
    sig, exp, out = result.signals, s.expect, []

    def add(name: str, ok: bool, detail: str) -> None:
        out.append((name, "PASS" if ok else "FAIL", detail))

    for key, want in exp.get("m0", {}).items():
        add(f"m0.{key}", sig["m0_charsafe"].get(key) == want, f"{sig['m0_charsafe'].get(key)!r} (want {want!r})")
    if "form" in exp:
        got = sorted({p.code.value for p in result.form.patterns})
        add("form", got == sorted(exp["form"]), f"{got} (want {sorted(exp['form'])})")
    if "m2_codes" in exp:
        got = sorted(sig["m2_deobf"].get("codes") or [])
        add("m2.codes", got == sorted(exp["m2_codes"]), f"{got} (want {sorted(exp['m2_codes'])})")
    if "m1_roots" in exp:
        got = sorted(sig["m1_lexicon"].get("matched_roots") or [])
        add("m1.roots", got == sorted(exp["m1_roots"]), f"{got} (want {sorted(exp['m1_roots'])})")
    if exp.get("m1_norm"):
        sources = {c["source"] for c in sig["decision"].get("channel_scores") or []}
        add("m1.normalized_channel", "m1_lexicon@normalized" in sources, f"sources {sorted(sources)}")
    if "target" in exp:
        got = sig["m6_target"].get("target_type")
        add("m6.target", got == exp["target"], f"{got!r} (want {exp['target']!r})")
    if "fired" in exp:
        got = sorted(c.code.value for c in result.fired())
        add("fired", got == sorted(exp["fired"]), f"{got} (want {sorted(exp['fired'])})")
    for guard, codes in exp.get("suppressed", {}).items():
        got = sorted({c.value for g in result.guards if g.code.value == guard and g.active for c in g.suppressed})
        add(f"guard.{guard}", got == sorted(codes), f"suppressed {got} (want {sorted(codes)})")
    if "binary" in exp:
        got = (sig["decision"].get("binary_offensive") or {}).get("fired")
        add("binary_offensive", got is exp["binary"], f"{got!r} (want {exp['binary']!r}; CURRENT_ARTIFACT_OBSERVATION)")
    if exp.get("m3_norm"):
        m3 = sig["m3_encoder"]
        ok = "norm_score" in m3 and m3["norm_score"] != m3["raw_score"]
        add("m3.normalized_channel", ok, f"raw {m3.get('raw_score')!r} norm {m3.get('norm_score')!r}")
    for key, want in exp.get("m4", {}).items():
        got = sig["m4_implicit"].get(key)
        add(f"m4.{key}", got == want and type(got) is type(want), f"{got!r} (want {want!r})")
    if exp.get("m4_gap"):
        gap = sig["m4_implicit"].get("norm_minus_raw")
        add("m4.norm_minus_raw>0", isinstance(gap, float) and gap > 0, f"{gap!r}")
    if "m3_a" in exp:
        m3a = [c for c in sig["decision"].get("channel_scores") or []
               if c["source"].startswith("m3_encoder") and c["code"] in ("A1", "A2", "A3")]
        want = exp["m3_a"]
        add("m3.a_head_emitted", bool(m3a) is want["emitted"], f"{[(c['source'], round(c['score'], 4)) for c in m3a]}")
        if "fired" in want:
            got = any(c["fired"] for c in m3a)
            add("m3.a_head_fired", got is want["fired"],
                f"{got!r} (want {want['fired']!r}; CURRENT_ARTIFACT_OBSERVATION, A threshold placeholder)")
    if "m5_rules" in exp:
        got = sorted(sig["m5_sarcasm"].get("matched_rules") or [])
        add("m5.matched_rules", got == sorted(exp["m5_rules"]), f"{got} (want {sorted(exp['m5_rules'])})")
    if "m5_excluded" in exp:
        got = sorted({e["reason"] for e in sig["m5_sarcasm"].get("excluded") or []})
        add("m5.excluded", set(exp["m5_excluded"]) <= set(got), f"{got} (want {sorted(exp['m5_excluded'])})")
    if "d1" in exp:
        d1 = [c for c in result.content if c.code.value == "D1" and c.source.startswith("m5_sarcasm")]
        if any(d["module"] == "m5_sarcasm" for d in actions.degraded_modules(result)):
            out.append(("m5.d1", "BLOCKED", f"m5_sarcasm is a stub; D1 {'expected' if exp['d1'] else 'must not fire'}, "
                                            f"cannot be evaluated"))
        else:
            add("m5.d1", bool(d1) is exp["d1"], f"D1 scores {[(c.score, c.source) for c in d1]}")
    if "degraded" in exp:
        got = [d["module"] for d in actions.degraded_modules(result)]
        add("degraded", got == exp["degraded"], f"{got} (want {exp['degraded']})")
    return out


def trace(s: Scenario, result: AnalysisResult, checks: list[tuple[str, str, str]], want: Action, basis: str,
          driver: Any) -> str:
    sig = result.signals
    lines = [f"ID: {s.id}  [{s.group}] {s.title}", f"INPUT: {visible(s.text)!r}", f"ORACLE: {s.oracle}",
             f"EXPECT: {json.dumps(s.expect, ensure_ascii=False)}"]
    for name in MODULES:
        public = sig.get(name)
        lines.append(f"  {name}: signals={json.dumps(public, ensure_ascii=False, default=str)}")
    lines.append(f"  content: {[(c.code.value, round(c.score, 4), c.source, c.span, c.fired) for c in result.content]}")
    lines.append(f"  guards: {[(g.code.value, g.source, g.span, g.active, [x.value for x in g.suppressed]) for g in result.guards]}")
    lines.append(f"  target: {None if result.target is None else (result.target.type.value, result.target.confidence, result.target.evidence)}")
    lines.append(f"  form: {[(p.code.value, p.source, p.span) for p in result.form.patterns]}")
    lines.append(f"  decision.binary_offensive: {sig['decision'].get('binary_offensive')}")
    lines.append(f"  decision.family_a: {sig['decision'].get('family_a')}")
    lines.append(f"  degraded: {actions.degraded_modules(result)}")
    lines.append(f"  module notes: {[n for n in result.notes if n.startswith(('[m4', '[m5', '[m3'))]}")
    lines.append(f"VERDICT: {result.verdict.value if result.verdict else None} (driver {getattr(driver, 'code', driver)}); "
                 f"expected {want.value} ({basis})")
    lines.append(f"EXPLANATION: {result.explanation}")
    lines += [f"  CHECK {status:7} {name}: {detail}" for name, status, detail in checks]
    return "\n".join(lines)


def main() -> int:
    started = time.time()
    pipeline = Pipeline()
    cfg = pipeline.config
    rows, traces = [], []
    for s in SCENARIOS:
        result = pipeline.analyze(s.text, trace_id=f"active-{s.id}")
        checks = run_checks(s, result)
        want, basis = expected_verdict(s.expect, result, cfg)
        got_verdict, driver = actions.resolve(result, cfg)
        checks.append(("verdict", "PASS" if result.verdict is want else "FAIL",
                       f"{result.verdict.value if result.verdict else None} (want {want.value}; {basis})"))
        failed = [c for c in checks if c[1] == "FAIL"]
        blocked = [c for c in checks if c[1] == "BLOCKED"]
        # A scenario whose own capability cannot be checked is BLOCKED, never PASS.
        outcome = "FAIL" if failed else "BLOCKED" if blocked else "PASS"
        if failed and s.known_limitation:
            outcome = "FAIL (KNOWN_LIMITATION)"
        label = driver.code.value if hasattr(driver, "code") else driver
        rows.append({"s": s, "outcome": outcome, "failed": failed, "blocked": blocked, "want": want,
                     "got": result.verdict, "driver": label, "result": result})
        traces.append(trace(s, result, checks, want, basis, driver))

    modules = {m.name.value: getattr(m, "version", "?") + (" (STUB)" if getattr(m, "stub", False) else "")
               for m in pipeline.modules}
    m3_artifact = rows[0]["result"].signals["m3_encoder"].get("artifact")
    from modules.m3_encoder import module as m3   # report only: which weights sha256 the loaded id stands for
    m3_sha = {m3.DEPLOYED_ID: m3.DEPLOYED_WEIGHTS_SHA256, m3.BASELINE_ID: m3.CHECKPOINT_SHA256}.get(
        m3_artifact, "see the artifact directory's sha256.txt")
    total = len(rows)
    counts = {k: sum(r["outcome"] == k for r in rows) for k in ("PASS", "FAIL", "FAIL (KNOWN_LIMITATION)", "BLOCKED")}
    ran = {name: sum(name in r["result"].per_module_ms for r in rows) for name in MODULES}
    degraded = {name: sum(any(d["module"] == name for d in actions.degraded_modules(r["result"])) for r in rows)
                for name in MODULES}

    md = ["# Active-module scenario report", "",
          "> Functional scenarios through the real pipeline. Expectations come from the named oracles, never from a "
          "run. PASS / total is a functional pass rate, not an accuracy benchmark.", "",
          f"Generated {time.strftime('%Y-%m-%dT%H:%M:%S%z')} by `eval/scenarios/run_active_modules.py` in "
          f"{time.time() - started:.1f} s.", "",
          "| item | value |", "|---|---|",
          f"| git | branch `{git('branch', '--show-current')}`, HEAD `{git('rev-parse', 'HEAD')}`, "
          f"{len(git('status', '--porcelain').splitlines())} porcelain lines |",
          f"| interpreter | `{sys.executable}` (Python {platform.python_version()}) |",
          f"| pipeline artifact_hash | `{pipeline.artifact_hash}` |",
          f"| m3 artifact loaded | `{m3_artifact}` (sha256 `{m3_sha}`) |",
          f"| modules | {', '.join(f'{name} {version}' for name, version in modules.items())} |",
          f"| binary_offensive | threshold {cfg['binary_offensive']['threshold']} (derived, {cfg['artifact']['derived_on']}), "
          f"action {cfg['binary_offensive']['action']} (placeholder policy) |", "",
          f"**Totals:** {total} scenarios: " + ", ".join(f"{n} {k}" for k, n in counts.items()) +
          ". BLOCKED = the scenario's own capability cannot be checked on this system (never a pass); the "
          "scenario's other checks still ran and are listed.", "",
          "| module | ran in | degraded in |", "|---|---|---|"]
    md += [f"| {name} | {ran[name]}/{total} | {degraded[name]}/{total} |" for name in MODULES]
    md += ["", "| id | group | input | expected | actual (driver) | result | failed / blocked checks |",
           "|---|---|---|---|---|---|---|"]
    for r in rows:
        s = r["s"]
        notes = "; ".join(f"{n}: {d}" for n, _, d in r["failed"] + r["blocked"]) or "-"
        md.append(f"| {s.id} | {s.group} | `{cell(visible(s.text))}` | {r['want'].value} | "
                  f"{r['got'].value if r['got'] else None} ({cell(r['driver'])}) | {r['outcome']} | {cell(notes)} |")
    limits = {s.known_limitation for s in SCENARIOS if s.known_limitation}
    md += ["", "Known limitations referenced above:", *[f"- {cell(k)}" for k in sorted(limits)], ""]

    RESULTS.mkdir(parents=True, exist_ok=True)
    (RESULTS / "active_modules_report.md").write_text("\n".join(md), encoding="utf-8", newline="\n")
    (RESULTS / "active_modules_traces.txt").write_text("\n\n".join(traces) + "\n", encoding="utf-8", newline="\n")
    print("\n".join(md))
    return 0 if counts["FAIL"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
