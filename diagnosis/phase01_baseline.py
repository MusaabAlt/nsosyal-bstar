#!/usr/bin/env python3
"""NSosyal B* -- Phase 01: baseline diagnosis (BERTurk vs the lexicon-free slice).

Implements phases/01_baseline_diagnosis.md end to end.

The one question this run answers
---------------------------------
Day 1 proved 3,892 / 6,131 OFF tweets (63%) evade the frozen keyword filter under
root matching. That is a fact about the FILTER. This run establishes whether it
is also a fact about a TRANSFORMER: is BERTurk's OFF-recall on the lexicon-free
slice of dev materially below its OFF-recall on the lexicon-hit slice, with a
bootstrap CI on the difference that excludes zero?

Two stages, run in this order:

    python phase01_baseline.py --stage preflight
        Preconditions + split + slice tagging + the 3,892/6,131 sanity gate +
        the keyword-filter matrix row. No torch, no GPU, seconds. This is a
        gate: if the sanity check fails, the tagger in use is not the one that
        produced the frozen record and NO training should be started.

    python phase01_baseline.py --stage train
        Everything above (cheap, re-verified) + fine-tune BERTurk + evaluate +
        write the four output-contract files.

Gate: this script NEVER touches the official Çöltekin test set. It calls
`load_coltekin_train()` only; `load_coltekin_test()`'s PermissionError guard
stays armed and unused (briefing S7.2).

Inputs  : config.COLTEKIN_TRAIN, config.LEXICON_PATH
Outputs : <RESULTS_DIR>/01_baseline_berturk/{metrics.json,
          classification_report.txt, dev_predictions.csv, run_config.json,
          results_log_row.md} -- five files. results_log_row.md is a
          ready-to-paste RESULTS_LOG row with the two judgement columns left
          as TODO; the driver deliberately does not append to the log itself.
          With --mirror_dir, those files are copied to Drive after a
          successful run. The repo copy stays canonical.
"""

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))

import config
from src import data_io, evaluate, lexicon

RUN_ID = "01_baseline_berturk"

# --- frozen expectations (results/day1_report.json). These are not tuning
# --- targets; they are what the sanity gate asserts against.
EXPECTED_TRAIN_SHA = "8509c01c4bf387d9e387c4637829585431cc045adaf7d0413c0022bf2bcd4baa"
EXPECTED_LEXICON_SHA = "0f5a05f52c414e07be8d67b1010979a901a974f573c7d47430f3cb5d3eace20b"
EXPECTED_LEXICON_FREE_OFF = 3892
EXPECTED_TOTAL_OFF = 6131


def git_sha():
    """HEAD sha, suffixed `-dirty` only if a TRACKED file was modified.

    Untracked files are deliberately excluded (`--untracked-files=no`). The
    first phase-01 run reported `837c351-dirty` purely because it had written
    its own four output files into results/, which are untracked until
    committed -- so every run marked itself dirty by succeeding, and the flag
    carried no information. It now means what it should: the code that produced
    the numbers differs from the commit.
    """
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True, text=True, timeout=10,
        )
        sha = out.stdout.strip()
        if out.returncode != 0 or not sha:
            return None
        dirty = subprocess.run(
            ["git", "status", "--porcelain", "--untracked-files=no"],
            cwd=Path(__file__).resolve().parent,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return sha + ("-dirty" if dirty else "")
    except Exception:
        return None


def check_preconditions(train_path, lex_path, strict=True):
    """Phase 01 preconditions 1, 2 and 4. Returns the check block; aborts on
    failure unless --allow_hash_mismatch was passed."""
    checks = {}

    train_sha = data_io.sha256(train_path)
    lex_sha = data_io.sha256(lex_path)
    checks["train_sha256"] = {"got": train_sha, "expected": EXPECTED_TRAIN_SHA,
                              "passed": train_sha == EXPECTED_TRAIN_SHA}
    checks["lexicon_sha256"] = {"got": lex_sha, "expected": EXPECTED_LEXICON_SHA,
                                "passed": lex_sha == EXPECTED_LEXICON_SHA}

    # Precondition 1: the Day 1 reproduction check needs a rerun record to
    # compare against; report its state rather than silently claiming it passed.
    rerun = config.RESULTS_DIR / "day1_report_rerun.json"
    checks["day1_reproduction_record"] = {
        "path": str(rerun),
        "present": rerun.exists(),
        "note": None if rerun.exists() else (
            "absent -- run `python day1_gate_en.py --out results/day1_report_rerun.json` "
            "then `python tests/_verify_day1_reproduction.py` before trusting this run"
        ),
    }

    # Precondition 4, asserted rather than assumed.
    checks["official_test_set_touched"] = False

    print("Preconditions")
    for name in ("train_sha256", "lexicon_sha256"):
        c = checks[name]
        print(f"  {name:<16}: {'OK' if c['passed'] else 'MISMATCH'}  {c['got'][:16]}...")
    r = checks["day1_reproduction_record"]
    print(f"  day1 rerun record: {'present' if r['present'] else 'ABSENT'}")
    if r["note"]:
        print(f"      -> {r['note']}")

    failed = [n for n in ("train_sha256", "lexicon_sha256") if not checks[n]["passed"]]
    if failed and strict:
        sys.exit(
            f"ABORT: {', '.join(failed)} does not match the frozen Day 1 record.\n"
            "The corpus or the lexicon changed under the project. Every number from "
            "Day 1 onwards would be measured on different bytes than it claims.\n"
            "Pass --allow_hash_mismatch only if you know exactly why it changed."
        )
    return checks, train_sha, lex_sha


def sanity_gate(all_rows, lex_list):
    """Phase 01 S2: the tagger must reproduce 3,892 lexicon-free OFF of 6,131 on
    the FULL training corpus. This is what proves the slice definition used here
    is the same one that produced the frozen record."""
    off_rows = [r for r in all_rows if r["label"] == "OFF"]
    tags = evaluate.tag_slices(off_rows, lex_list)
    free = sum(1 for t in tags if t == "lexicon_free")
    passed = (free == EXPECTED_LEXICON_FREE_OFF and len(off_rows) == EXPECTED_TOTAL_OFF)
    block = {
        "lexicon_free_off": free,
        "total_off": len(off_rows),
        "expected_lexicon_free_off": EXPECTED_LEXICON_FREE_OFF,
        "expected_total_off": EXPECTED_TOTAL_OFF,
        "passed": passed,
    }
    print("\nSanity gate (full training corpus, frozen tagger)")
    print(f"  lexicon-free OFF : {free:,}  (expected {EXPECTED_LEXICON_FREE_OFF:,})")
    print(f"  total OFF        : {len(off_rows):,}  (expected {EXPECTED_TOTAL_OFF:,})")
    if not passed:
        print(json.dumps(block, indent=2))
        sys.exit(
            "ABORT: the tagger does not reproduce the frozen Day 1 slice.\n"
            "src/lexicon.py has drifted from the code that produced "
            "results/day1_report.json. Report this -- do not proceed with the "
            "adjusted number (phase 01 S2)."
        )
    print("  [PASS] tagger matches the frozen record")
    return block


def assert_trainable_runtime(allow_cpu=False):
    """Fail at minute 0 if this runtime cannot actually train on a GPU.

    A CPU-only torch build on a GPU runtime trains silently at roughly 20x the
    wall-clock with no error of any kind -- the run just appears slow, and the
    discovery happens ninety minutes in, usually after the session has dropped.
    So this is a hard gate, not a warning.

    Two distinct failures are caught:
      * no CUDA device visible (CPU runtime, or GPU not attached yet)
      * a `+cpu` local-version torch wheel, which has no CUDA support compiled
        in at all and cannot use a GPU even when one is attached

    Where a +cpu build comes from: NOT from this repo. requirements.txt asks for
    a plain `torch>=2.2` (the default PyPI Linux wheel is CUDA-enabled), and the
    Colab runbook installs only transformers -- it never installs torch. A
    `+cpu` build therefore comes from the runtime image itself, i.e. the session
    was started on a CPU runtime. The fix is to change the runtime type and
    restart the session, not to reinstall torch blind.
    """
    try:
        import torch
    except ImportError:
        sys.exit("ABORT: torch is not installed in this environment, so training cannot start.\n"
                 "On Colab it ships with the runtime; locally, `pip install -r requirements.txt`.")

    version = torch.__version__
    cuda_ok = torch.cuda.is_available()
    device_name = torch.cuda.get_device_name(0) if cuda_ok else None
    cpu_wheel = "+cpu" in version

    print("\nRuntime gate")
    print(f"  torch          : {version}")
    print(f"  cuda available : {cuda_ok}")
    print(f"  device         : {device_name or 'NONE'}")

    if cuda_ok and not cpu_wheel:
        print("  [PASS] GPU present and torch is a CUDA build.")
        return {"torch": version, "cuda_available": True, "device_name": device_name}

    reason = ("torch is a CPU-only build (`+cpu`), which cannot use a GPU even if one "
              "is attached" if cpu_wheel else "no CUDA device is visible")
    message = (
        f"ABORT: this runtime cannot train on a GPU -- {reason}.\n\n"
        "BERT-base on ~27k examples for 3 epochs is minutes on an L4 and many hours on\n"
        "CPU. Training would start and appear to work; you would find out at minute 90.\n\n"
        "Fix:\n"
        "  1. Runtime -> Change runtime type -> L4 GPU (or T4), then Runtime -> Restart session.\n"
        "  2. Re-run the environment cell and check this gate prints [PASS].\n\n"
        "Note on where a `+cpu` wheel comes from: not from this repo. requirements.txt\n"
        "asks for a plain `torch>=2.2` (the default PyPI Linux wheel is CUDA-enabled) and\n"
        "the runbook installs only transformers -- it never installs torch. A `+cpu` build\n"
        "means the SESSION is a CPU runtime; changing the runtime type is the fix, not a\n"
        "blind reinstall.\n\n"
        "To train on CPU anyway (a deliberate slow smoke test, never a reported result),\n"
        "pass --allow_cpu."
    )
    if allow_cpu:
        print("  [WARN] gate overridden with --allow_cpu.")
        print("         Any number this run produces is a smoke test, not a result.")
        return {"torch": version, "cuda_available": cuda_ok, "device_name": device_name,
                "cpu_override": True}
    sys.exit(message)


PHASE01_CONTRACT = ("metrics.json", "classification_report.txt", "dev_predictions.csv",
                    "run_config.json", "results_log_row.md")


def mirror_outputs(out_dir, mirror_dir, required=None, marker="metrics.json"):
    """Copy a COMPLETED run's outputs to Drive.

    The repo copy stays canonical and is the one that gets committed; Drive is a
    durable mirror, because /content is wiped when the Colab session ends. Never
    the reverse -- nothing in this project reads results back from Drive.

    Called only after `evaluate_and_write` returns, so partial output cannot be
    mirrored, and it refuses anything stamped MOCK_RUN. (The dry-run harness
    calls `evaluate_and_write` directly and never reaches main(), so mock output
    has no path here at all; this check is the second lock on that door.)

    `required` is the output contract to enforce and defaults to phase 01's five
    files. Later phases pass their own list rather than getting a second copy of
    this function -- two mirrors would be free to drift apart on exactly the
    checks that make this one worth having.
    """
    out_dir, mirror_dir = Path(out_dir), Path(mirror_dir)
    required = tuple(required) if required else PHASE01_CONTRACT
    marker_file = out_dir / marker
    if not marker_file.exists():
        sys.exit(f"Refusing to mirror: {marker_file} does not exist, so the run did not complete.")
    if marker_file.suffix == ".json" and "MOCK_RUN" in json.loads(
            marker_file.read_text(encoding="utf-8")):
        sys.exit("Refusing to mirror MOCK output. Mock numbers are not results.")

    # dev_predictions.csv is gitignored (corpus text) and /content is wiped when
    # the session ends, so THE DRIVE MIRROR IS ITS ONLY SURVIVING COPY. Phase 2
    # reads it for the failure analysis and phase 4 reads its confidence column
    # for calibration; losing it means retraining to recover it. Reporting a
    # successful mirror without it would be the expensive kind of quiet failure.
    for name in required:
        f = out_dir / name
        if not f.exists() or f.stat().st_size == 0:
            state = "missing" if not f.exists() else "zero-length"
            extra = ""
            if name == "dev_predictions.csv":
                extra = ("\nThis file is the one that cannot be regenerated without retraining: "
                         "it is gitignored,\n/content is wiped at session end, and this mirror "
                         "would have been its only copy.\nPhase 2 (failure analysis) and phase 4 "
                         "(calibration confidences) both read it.")
            sys.exit(f"Refusing to mirror: {name} is {state} in {out_dir}. "
                     f"The run did not produce a complete output set.{extra}")

    mirror_dir.mkdir(parents=True, exist_ok=True)
    copied = []
    for src in sorted(p for p in out_dir.iterdir() if p.is_file()):
        dst = mirror_dir / src.name
        shutil.copy2(src, dst)
        if not dst.exists() or dst.stat().st_size != src.stat().st_size:
            sys.exit(f"Mirror verification FAILED for {src.name} -- sizes differ or file missing.")
        copied.append((src.name, dst.stat().st_size))

    print("\n" + "=" * 68)
    print(f"MIRRORED TO DRIVE -> {mirror_dir}")
    print("=" * 68)
    for name, size in copied:
        print(f"  {name:<28} {size:>12,} bytes")
    print(f"  {len(copied)} file(s), verified by size after copy.")
    print("  The repo copy remains canonical and is the one to commit; this is a mirror.")
    return copied


def evaluate_and_write(*, dev_rows, dev_gold, dev_slices, dev_pred, p_off,
                       kw, kw_pred, history, env, gate, checks, split_meta,
                       split_path, train_sha, lex_sha, out_dir, ckpt_dir,
                       args, started, mock_note=None):
    """Everything after `predict()`: scoring, the gap CI, and the four output
    files. Split out of main() so it can be exercised end to end with mock
    predictions on a machine with no GPU -- see tests/_dryrun_phase01_outputs.py.
    A KeyError in here should surface locally in seconds, not after a completed
    Colab training run.

    `mock_note` is set ONLY by the dry-run harness. It stamps every artifact as
    fake and refuses to write into the canonical run directory. The production
    CLI has no flag that reaches it: a fabrication path in the real driver is
    exactly the kind of second source of truth the master brief forbids.
    """
    out_dir = Path(out_dir)
    canonical = Path(config.RESULTS_DIR / RUN_ID).resolve()
    if mock_note and out_dir.resolve() == canonical:
        sys.exit(f"Refusing to write mock output into the canonical run directory {canonical}.")

    overall = evaluate.score(dev_gold, dev_pred, n_boot=args.n_boot, seed=args.seed)
    by_slice = evaluate.score_by_slice(dev_gold, dev_pred, dev_slices,
                                       n_boot=args.n_boot, seed=args.seed)

    hit_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_hit"]
    free_idx = [i for i, t in enumerate(dev_slices) if t == "lexicon_free"]
    gap = evaluate.bootstrap_gap_ci(
        [dev_gold[i] for i in hit_idx], [dev_pred[i] for i in hit_idx],
        [dev_gold[i] for i in free_idx], [dev_pred[i] for i in free_idx],
        metric="off_recall", n_boot=args.n_boot, seed=args.seed,
    )

    def fmt(v, spec=".4f"):
        """None means the metric is undefined on this slice -- print it as such
        rather than crashing or, worse, printing 0.0000."""
        return "undefined" if v is None else format(v, spec)

    print("\n" + "=" * 68)
    if mock_note:
        print(f"*** MOCK RUN -- {mock_note} -- NUMBERS BELOW ARE NOT RESULTS ***")
    print("RESULTS (dev split -- the official test set was NOT touched)")
    print("=" * 68)
    print(f"BERTurk overall : macro-F1 {fmt(overall['macro_f1'])}  "
          f"OFF-P {fmt(overall['off_precision'])}  OFF-R {fmt(overall['off_recall'])}")
    for tag in ("lexicon_hit", "lexicon_free"):
        s = by_slice[tag]
        ci = s["ci"]["off_recall"]
        c = s["confusion"]
        print(f"  {tag:<13}: n={s['n']:>5}  OFF n={s['support_off']:>4}  "
              f"base rate {s['support_off'] / s['n']:.3f}  "
              f"OFF-recall {fmt(s['off_recall'])} [{fmt(ci['ci_low'])}, {fmt(ci['ci_high'])}]")
        print(f"                 counts tp={c['tp']} fn={c['fn']} fp={c['fp']} tn={c['tn']}")
    print("  (Cross-slice comparison is OFF-recall only, by pre-registered constraint: the")
    print("   base rates differ sharply, so a per-slice macro-F1 difference would be driven")
    print("   by class balance. Raw counts are kept so later phases can recompute anything.)")
    print(f"\nRECALL GAP (hit - free) : {fmt(gap['delta'], '+.4f')}   "
          f"95% CI [{fmt(gap['ci_low'], '+.4f')}, {fmt(gap['ci_high'], '+.4f')}]   "
          f"excludes zero: {gap['excludes_zero']}")
    print("This is the pivotal number. Apply the pre-registered three-way decision rule in")
    print("phases/01_baseline_diagnosis.md to it -- out loud, before anything else is built.")

    # --- output contract ----------------------------------------------------
    out_dir.mkdir(parents=True, exist_ok=True)

    header = (
        "NOTE (pre-registered constraint, phases/01_baseline_diagnosis.md):\n"
        "The per-slice sections below are diagnostic, useful WITHIN a slice. Their F1 and\n"
        "accuracy columns are NOT comparable ACROSS slices -- base rates are 57.8% OFF in\n"
        "lexicon_hit vs 13.6% in lexicon_free, so a difference there reflects class balance,\n"
        "not model behaviour. The only cross-slice comparison this project makes is\n"
        "OFF-recall, which conditions on gold=OFF and is immune to base rate.\n"
    )
    if mock_note:
        header = f"*** MOCK RUN -- {mock_note} -- NOT A RESULT ***\n\n" + header
    report_lines = [
        header + "=" * 78,
        evaluate.sklearn_report(dev_gold, dev_pred, title="BERTurk -- dev, overall", strict=False),
    ]
    for tag in ("lexicon_hit", "lexicon_free"):
        idx = hit_idx if tag == "lexicon_hit" else free_idx
        report_lines.append(evaluate.sklearn_report(
            [dev_gold[i] for i in idx], [dev_pred[i] for i in idx],
            title=f"BERTurk -- dev, slice={tag} (n={len(idx)})", strict=False))
    report_lines.append(evaluate.sklearn_report(
        dev_gold, kw_pred, title="Keyword filter (frozen lexicon) -- dev, overall", strict=False))
    (out_dir / "classification_report.txt").write_text(
        "\n\n".join(report_lines), encoding="utf-8")

    with open(out_dir / "dev_predictions.csv", "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["row_id", "text", "gold", "pred", "confidence", "slice"])
        for r, g, p, c, s in zip(dev_rows, dev_gold, dev_pred, p_off, dev_slices):
            # confidence = softmax P(OFF); the failure analysis and the
            # risk-coverage curve both read this column.
            w.writerow([r["id"], r["text"], g, p, f"{c:.6f}", s])

    def slice_block(tag):
        """Per-slice block: OFF-recall (the only sanctioned cross-slice metric)
        plus RAW COUNTS. The counts are primitives, not a comparison -- phase 4
        needs false-positive behaviour inside lexicon_free to characterise the
        deferral queue, and any later phase can recompute a metric from them
        without re-running training."""
        s = by_slice[tag]
        return {
            "n": s["n"],
            "support_off": s["support_off"],
            "support_not": s["support_not"],
            "base_rate_off": s["support_off"] / s["n"] if s["n"] else None,
            "off_recall": s["off_recall"],
            "off_recall_ci": s["ci"]["off_recall"],
            "confusion": s["confusion"],  # {tn, fp, fn, tp} -- gold OFF = tp+fn
            "macro_f1": None,
            "macro_f1_note": (
                "omitted by pre-registered constraint -- not comparable across slices "
                "(base rates 57.8% vs 13.6%); recompute from `confusion` if ever needed "
                "WITHIN a slice"
            ),
        }

    metrics = {
        "run_id": RUN_ID,
        "git_sha": git_sha(),
        "sanity_gate": gate,
        "keyword_filter": {
            "macro_f1": kw["macro_f1"],
            "off_recall": kw["off_recall"],
            "off_precision": kw["off_precision"],
            "confusion": kw["confusion"],
            "ci": kw["ci"],
            "note": "slice recalls are tautological (1.0 / 0.0) and deliberately not reported",
        },
        "berturk": {
            "overall": {
                "macro_f1": overall["macro_f1"],
                "off_precision": overall["off_precision"],
                "off_recall": overall["off_recall"],
                "n": overall["n"],
                "support_off": overall["support_off"],
                "confusion": overall["confusion"],
                "ci": overall["ci"],
            },
            "lexicon_hit": slice_block("lexicon_hit"),
            "lexicon_free": slice_block("lexicon_free"),
            "recall_gap": {
                "delta": gap["delta"],
                "ci_low": gap["ci_low"],
                "ci_high": gap["ci_high"],
                "excludes_zero": gap["excludes_zero"],
                "method": gap["resampling"],
                "n_boot": gap["n_boot"],
            },
        },
        "training_history": history,
        "decision_rule_applied": None,  # filled by a human, from the log entry
    }
    if mock_note:
        metrics = {"MOCK_RUN": mock_note, **metrics}
    with open(out_dir / "metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, ensure_ascii=False, indent=2)

    run_config = {
        "run_id": RUN_ID,
        "git_sha": metrics["git_sha"],
        "started_at": started.isoformat(timespec="seconds"),
        "finished_at": datetime.now().isoformat(timespec="seconds"),
        "env": config.ENV,
        "paths": {"root": str(config.ROOT), "data": str(config.DATA_DIR),
                  "results": str(out_dir), "checkpoints": str(ckpt_dir),
                  "split_file": str(split_path)},
        "hashes": {"train_sha256": train_sha, "lexicon_sha256": lex_sha,
                   "dev_fingerprint": split_meta["dev_fingerprint"]},
        "preconditions": checks,
        "split": {k: split_meta[k] for k in
                  ("seed", "dev_fraction", "counts", "reused_existing_file", "matches_regeneration")},
        "model": args.model,
        "hyperparams": {"epochs": args.epochs, "batch_size": args.batch_size, "lr": args.lr,
                        "max_len": args.max_len, "seed": args.seed, "warmup_ratio": 0.1,
                        "weight_decay": 0.01, "fp16": not args.no_fp16,
                        "class_weighting": None, "threshold": 0.5},
        "bootstrap": {"n_boot": args.n_boot, "alpha": 0.05, "seed": args.seed},
        "environment": env,
        "official_test_set_touched": False,
    }
    if mock_note:
        run_config = {"MOCK_RUN": mock_note, **run_config}
    with open(out_dir / "run_config.json", "w", encoding="utf-8") as f:
        json.dump(run_config, f, ensure_ascii=False, indent=2)

    # A ready-to-paste RESULTS_LOG row. The driver does NOT append to
    # docs/RESULTS_LOG.md itself: two of that table's columns are Interpretation
    # and Decision, and a script cannot honestly fill them. An auto-appended row
    # with placeholder text in the project's engineering log is worse than no
    # row -- so the numbers are pre-filled here and a human writes the judgement.
    log_row = (
        f"| {datetime.now().date().isoformat()} | Phase 01 {'MOCK' if mock_note else 'BERTurk baseline'} | "
        f"`phase01_baseline.py --stage train` ({args.model}, seed {args.seed}, "
        f"{args.epochs} epochs) | BERTurk dev macro-F1 {fmt(overall['macro_f1'])}, "
        f"OFF-recall {fmt(overall['off_recall'])}. Slice OFF-recall: lexicon_hit "
        f"{fmt(by_slice['lexicon_hit']['off_recall'])} (n OFF "
        f"{by_slice['lexicon_hit']['support_off']}), lexicon_free "
        f"{fmt(by_slice['lexicon_free']['off_recall'])} (n OFF "
        f"{by_slice['lexicon_free']['support_off']}). **Gap {fmt(gap['delta'], '+.4f')} "
        f"95% CI [{fmt(gap['ci_low'], '+.4f')}, {fmt(gap['ci_high'], '+.4f')}]**, "
        f"excludes zero: {gap['excludes_zero']}. | _interpretation: TO BE WRITTEN BY A HUMAN_ "
        f"| _decision: apply the three-way pre-registered rule_ |\n"
    )
    if mock_note:
        log_row = f"<!-- MOCK RUN ({mock_note}) -- DO NOT PASTE INTO RESULTS_LOG.md -->\n" + log_row
    (out_dir / "results_log_row.md").write_text(log_row, encoding="utf-8")

    print(f"\nWritten -> {out_dir}")
    for name in ("metrics.json", "classification_report.txt", "dev_predictions.csv",
                 "run_config.json", "results_log_row.md"):
        print(f"  {name}")
    if mock_note:
        print("\nMOCK RUN complete -- the code path executed; the numbers mean nothing.")
    else:
        print("\nNext: paste this output back, and paste results_log_row.md into")
        print("docs/RESULTS_LOG.md once the interpretation and decision are written.")
    return metrics


def build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["preflight", "train"], default="preflight",
                    help="preflight = no GPU, gates only; train = full run")
    ap.add_argument("--model", default=config.MODEL_BASELINE)
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch_size", type=int, default=32)
    ap.add_argument("--lr", type=float, default=2e-5)
    ap.add_argument("--max_len", type=int, default=config.MAX_LEN)
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n_boot", type=int, default=1000)
    ap.add_argument("--no_fp16", action="store_true")
    ap.add_argument("--resume", action="store_true", help="continue from checkpoints/<run>/latest.pt")
    ap.add_argument("--out_dir", default=None)
    ap.add_argument("--ckpt_dir", default=None)
    ap.add_argument("--force", action="store_true", help="allow overwriting existing result files")
    ap.add_argument("--allow_hash_mismatch", action="store_true")
    ap.add_argument("--allow_cpu", action="store_true",
                    help="override the GPU gate and train on CPU anyway (~20x slower). "
                         "A smoke test only -- never a reported result.")
    ap.add_argument("--mirror_dir", default=None,
                    help="after a SUCCESSFUL run, copy the output files here "
                         "(e.g. the mounted Drive path). The repo copy stays canonical.")
    return ap


def prepare(args):
    """Everything both stages need: preconditions, corpus, sanity gate, split,
    slice tags, keyword baseline. Returns a context dict.

    Shared with the dry-run harness on purpose -- if the harness reimplemented
    this setup it would be exercising a different pipeline than the real one.
    """
    train_path = Path(config.COLTEKIN_TRAIN)
    lex_path = Path(config.LEXICON_PATH)

    if not train_path.exists():
        sys.exit(f"Training file not found: {train_path}\n"
                 "Raw data is gitignored -- mount/copy it, or set NSOSYAL_DATA.")

    # --- preconditions -----------------------------------------------------
    checks, train_sha, lex_sha = check_preconditions(
        train_path, lex_path, strict=not args.allow_hash_mismatch
    )

    # --- corpus + lexicon --------------------------------------------------
    all_rows = data_io.load_coltekin_train(train_path)
    lex_list = lexicon.load_lexicon(lex_path)
    print(f"\nCorpus: {len(all_rows):,} rows   lexicon: {len(lex_list):,} entries")

    gate = sanity_gate(all_rows, lex_list)

    # --- S1: deterministic split, written once and reused thereafter --------
    split_path = config.SPLITS_DIR / f"split_seed{args.seed}.json"
    train_rows, dev_rows, split_meta = data_io.get_split(
        all_rows, split_path, train_sha, seed=args.seed, dev_fraction=config.DEV_FRACTION
    )
    print(f"\nSplit ({'loaded from' if split_meta['reused_existing_file'] else 'created'} {split_path})")
    print(f"  train : {len(train_rows):,}  {split_meta['counts']['train']}")
    print(f"  dev   : {len(dev_rows):,}  {split_meta['counts']['dev']}")
    print(f"  dev fingerprint : {split_meta['dev_fingerprint'][:16]}...")
    if not split_meta["matches_regeneration"]:
        print("  [warn] the saved split is NOT what a fresh seed-42 split would produce.")
        print("         The file wins (it is the identity of the dev set), but say so in")
        print("         the results log -- something changed the split algorithm.")

    # --- S2: slice tags on dev --------------------------------------------
    dev_gold = [r["label"] for r in dev_rows]
    dev_slices = evaluate.tag_slices(dev_rows, lex_list)
    n_hit = sum(1 for t in dev_slices if t == "lexicon_hit")
    off_hit = sum(1 for t, g in zip(dev_slices, dev_gold) if t == "lexicon_hit" and g == "OFF")
    off_free = sum(1 for t, g in zip(dev_slices, dev_gold) if t == "lexicon_free" and g == "OFF")
    print("\nDev slices")
    print(f"  lexicon_hit  : {n_hit:,} rows  ({off_hit:,} OFF)")
    print(f"  lexicon_free : {len(dev_rows) - n_hit:,} rows  ({off_free:,} OFF)")

    # --- S3: keyword-filter baseline, same split, same scoring code ---------
    kw_pred = ["OFF" if t == "lexicon_hit" else "NOT" for t in dev_slices]
    kw = evaluate.score(dev_gold, kw_pred, n_boot=args.n_boot, seed=args.seed)
    print("\nKeyword filter (frozen lexicon, root matching) on dev -- matrix row 1")
    print(f"  macro-F1   : {kw['macro_f1']:.4f}  "
          f"[{kw['ci']['macro_f1']['ci_low']:.4f}, {kw['ci']['macro_f1']['ci_high']:.4f}]")
    print(f"  OFF-recall : {kw['off_recall']:.4f}  "
          f"[{kw['ci']['off_recall']['ci_low']:.4f}, {kw['ci']['off_recall']['ci_high']:.4f}]")
    print(f"  OFF-prec.  : {kw['off_precision']:.4f}")
    print("  (Per-slice keyword numbers are omitted on purpose: the filter predicts OFF on")
    print("   lexicon_hit and NOT on lexicon_free BY DEFINITION, so its slice recalls are")
    print("   1.0 and 0.0 tautologically. Only the model's slice recalls carry information.)")

    return {
        "checks": checks, "train_sha": train_sha, "lex_sha": lex_sha,
        "all_rows": all_rows, "lex_list": lex_list, "gate": gate,
        "split_path": split_path, "split_meta": split_meta,
        "train_rows": train_rows, "dev_rows": dev_rows,
        "dev_gold": dev_gold, "dev_slices": dev_slices,
        "kw": kw, "kw_pred": kw_pred,
    }


def main():
    args = build_parser().parse_args()

    started = datetime.now()
    out_dir = Path(args.out_dir or config.RESULTS_DIR / RUN_ID)
    ckpt_dir = Path(args.ckpt_dir or config.CKPT_DIR / RUN_ID)

    print(f"NSosyal B* -- phase 01 ({args.stage})")
    print(f"env={config.ENV}  root={config.ROOT}")
    print(f"data={config.DATA_DIR}\nout={out_dir}\nckpt={ckpt_dir}\n")

    metrics_path = out_dir / "metrics.json"
    if args.stage == "train" and metrics_path.exists() and not args.force:
        sys.exit(f"Refusing to overwrite an existing result: {metrics_path}\n"
                 "Use --out_dir for a new run, or --force if you really mean to replace it.")

    ctx = prepare(args)

    if args.stage == "preflight":
        print("\nPreflight complete. Gates passed, split fixed, matrix row 1 measured.")
        print("Nothing was written except the split file. Next: --stage train on the GPU box.")
        return

    # --- S4: fine-tune BERTurk ---------------------------------------------
    from src import models  # imported here so preflight needs no torch

    print("\n" + "=" * 68)
    print("TRAINING")
    print("=" * 68)
    env = models.environment_info()
    print(f"  torch={env['torch']}  transformers={env['transformers']}  "
          f"sklearn={env['scikit_learn']}  device={env['device_name']}")

    # Hard gate BEFORE the corpus is tokenised or a single step is taken.
    assert_trainable_runtime(allow_cpu=args.allow_cpu)

    model, tokenizer, history = models.train(
        ctx["train_rows"], ctx["dev_rows"], args.model, ckpt_dir,
        epochs=args.epochs, batch_size=args.batch_size, lr=args.lr,
        max_len=args.max_len, seed=args.seed, fp16=not args.no_fp16, resume=args.resume,
    )

    # --- S5: evaluate -------------------------------------------------------
    dev_pred, p_off = models.predict(model, tokenizer, ctx["dev_rows"], max_len=args.max_len)

    evaluate_and_write(
        dev_rows=ctx["dev_rows"], dev_gold=ctx["dev_gold"], dev_slices=ctx["dev_slices"],
        dev_pred=dev_pred, p_off=p_off, kw=ctx["kw"], kw_pred=ctx["kw_pred"],
        history=history, env=env, gate=ctx["gate"], checks=ctx["checks"],
        split_meta=ctx["split_meta"], split_path=ctx["split_path"],
        train_sha=ctx["train_sha"], lex_sha=ctx["lex_sha"],
        out_dir=out_dir, ckpt_dir=ckpt_dir, args=args, started=started,
    )

    # Only reached if the whole run above succeeded -- partial output never
    # gets mirrored.
    if args.mirror_dir:
        mirror_outputs(out_dir, Path(args.mirror_dir))


if __name__ == "__main__":
    main()
