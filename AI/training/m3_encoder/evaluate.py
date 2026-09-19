"""Dev evaluation of a multi-head artifact: per-code metrics with bootstrap CIs, per head,
only over the rows that carry a label for that head (the coverage is reported next to every
number). Also usable on an exported artifact directory without the training package's model
class (`load_exported`), which is how the Colab handoff verifies a returned artifact.

    python -m training.m3_encoder.evaluate --artifact <dir> [--corpus PATH] [--labels-a ...]
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any

from training.m3_encoder import data as D
from training.m3_encoder import model as M
from training.m3_encoder import provenance as P


def _percentile(values: list[float], q: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    rank = max(1, round(q / 100 * len(ordered)))
    return ordered[min(rank, len(ordered)) - 1]


def _prf(tp: int, fp: int, fn: int, tn: int) -> dict[str, float | None]:
    recall = tp / (tp + fn) if tp + fn else None
    precision = tp / (tp + fp) if tp + fp else None
    f1 = (2 * precision * recall / (precision + recall) if precision is not None and recall is not None
          and precision + recall else (0.0 if precision is not None and recall is not None else None))
    fpr = fp / (fp + tn) if fp + tn else None
    return {"recall": recall, "precision": precision, "f1": f1, "fpr": fpr}


def binary_metrics(gold: list[int], pred: list[int], n_boot: int, seed: int) -> dict[str, Any]:
    """Macro-F1 and OFF recall/precision with percentile-bootstrap CIs, resampled over rows."""
    rng = random.Random(seed)
    n = len(gold)

    def cells(idx):
        tp = sum(1 for i in idx if gold[i] and pred[i]); fp = sum(1 for i in idx if not gold[i] and pred[i])
        fn = sum(1 for i in idx if gold[i] and not pred[i]); tn = sum(1 for i in idx if not gold[i] and not pred[i])
        return tp, fp, fn, tn

    def macro(tp, fp, fn, tn):
        pos = _prf(tp, fp, fn, tn)["f1"] or 0.0
        neg = _prf(tn, fn, fp, tp)["f1"] or 0.0
        return (pos + neg) / 2

    tp, fp, fn, tn = cells(range(n))
    point = {"macro_f1": macro(tp, fp, fn, tn), **_prf(tp, fp, fn, tn)}
    samples: dict[str, list[float]] = {k: [] for k in point}
    for _ in range(n_boot if n else 0):
        idx = [rng.randrange(n) for _ in range(n)]
        c = cells(idx)
        s = {"macro_f1": macro(*c), **_prf(*c)}
        for k, v in s.items():
            if v is not None:
                samples[k].append(v)
    return {k: {"value": v, "ci_low": _percentile(samples[k], 2.5), "ci_high": _percentile(samples[k], 97.5)}
            for k, v in point.items()} | {"n": n, "confusion": {"tp": tp, "fp": fp, "fn": fn, "tn": tn}}


def per_code_metrics(gold: list[list[int]], pred: list[list[int]], codes: list[str], n_boot: int,
                     seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    n = len(gold)
    report = {}
    for j, code in enumerate(codes):
        def cells(idx):
            tp = sum(1 for i in idx if gold[i][j] and pred[i][j]); fp = sum(1 for i in idx if not gold[i][j] and pred[i][j])
            fn = sum(1 for i in idx if gold[i][j] and not pred[i][j]); tn = sum(1 for i in idx if not gold[i][j] and not pred[i][j])
            return tp, fp, fn, tn
        tp, fp, fn, tn = cells(range(n))
        point = _prf(tp, fp, fn, tn)
        samples: dict[str, list[float]] = {k: [] for k in point}
        for _ in range(n_boot if n else 0):
            s = _prf(*cells([rng.randrange(n) for _ in range(n)]))
            for k, v in s.items():
                if v is not None:
                    samples[k].append(v)
        support = tp + fn
        report[code] = {"support": support, "tp": tp, "fp": fp, "fn": fn, "tn": tn,
                        "insufficient_sample": support < 20,   # m3 spec §9: fewer than 20 positives is not a metric
                        **{k: {"value": v, "ci_low": _percentile(samples[k], 2.5), "ci_high": _percentile(samples[k], 97.5)}
                           for k, v in point.items()}}
    return report


def predict_rows(model, tokenizer, rows: list[D.Row], max_len: int, batch_size: int, device: str) -> dict[str, list]:
    import torch

    model.eval().to(device)
    probs: dict[str, list] = {"binary": [], "a": [], "b": [], "c": []}
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            chunk = rows[start:start + batch_size]
            enc = tokenizer([r.text for r in chunk], truncation=True, max_length=max_len, padding=True,
                            return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            out = M.probabilities(model(**enc))
            for k in probs:
                probs[k].extend(out[k])
    return probs


REFERENCE_KINDS = P.REFERENCE_KINDS


def evaluate_rows(model, tokenizer, rows: list[D.Row], max_len: int, batch_size: int, device: str,
                  n_boot: int = 1000, seed: int = 42, decision: float = 0.5,
                  oracle_kind: str | None = None) -> dict[str, Any]:
    """`decision` is the study's argmax point (0.5) used ONLY to report comparable training-time
    numbers; the deployed threshold is derived separately on this same dev split (m3 spec §8)."""
    probs = predict_rows(model, tokenizer, rows, max_len, batch_size, device)
    report: dict[str, Any] = {"n_rows": len(rows), "decision_point_for_reporting": decision, "n_boot": n_boot,
                              "seed": seed}
    gold_bin = [r.binary for r in rows]
    pred_bin = [int(p >= decision) for p in probs["binary"]]
    report["binary"] = binary_metrics(gold_bin, pred_bin, n_boot, seed)

    # A head, two SEPARATE blocks (owner decision 2026-09-18, HYBRID strategy):
    #   "a"                        against the DECLARED evaluation reference only - the only A-head
    #                              quality claim; its provenance kind is stamped in "oracle"
    #   "a_pseudo_label_agreement" against terlik pseudo-labels on the same rows - agreement, never accuracy
    ref_idx = [i for i, r in enumerate(rows) if r.a_reference != D.MISSING]
    if ref_idx and oracle_kind is None:
        # No default kind: a reference evaluated without its kind would otherwise be stamped by omission.
        raise ValueError("evaluation-reference rows present but no oracle_kind: state the reference's provenance")
    if oracle_kind is not None and oracle_kind not in REFERENCE_KINDS:
        raise ValueError(f"oracle_kind {oracle_kind!r} is not one of {REFERENCE_KINDS}")
    # `oracle` states the reference's TRUE provenance. "human" only for human-labelled rows; an
    # AI-annotated, human-adjudicated reference is stamped as such and is never a human oracle.
    report["a"] = ({"oracle": oracle_kind, "labelled_rows": len(ref_idx),
                    **per_code_metrics([[rows[i].a_reference] for i in ref_idx],
                                       [[int(probs["a"][i] >= decision)] for i in ref_idx],
                                       list(D.A_CODES), n_boot, seed)}
                   if ref_idx else {"oracle": None, "labelled_rows": 0, "note": P.NO_REFERENCE_NOTE})
    a_idx = [i for i, r in enumerate(rows) if r.a != D.MISSING]
    report["a_pseudo_label_agreement"] = (
        {"labelled_rows": len(a_idx),
         "note": P.PSEUDO_LABEL_AGREEMENT_NOTE,
         **per_code_metrics([[rows[i].a] for i in a_idx], [[int(probs["a"][i] >= decision)] for i in a_idx],
                            list(D.A_CODES), n_boot, seed)}
        if a_idx else {"labelled_rows": 0, "note": "no pseudo-labels on the evaluated rows"})
    b_idx = [i for i, r in enumerate(rows) if r.b[0] != D.MISSING]
    report["b"] = ({"labelled_rows": len(b_idx), **per_code_metrics([list(rows[i].b) for i in b_idx],
                                                                     [[int(p >= decision) for p in probs["b"][i]] for i in b_idx],
                                                                     list(D.B_CODES), n_boot, seed)}
                   if b_idx else {"labelled_rows": 0, "note": "no B labels: head not evaluated"})
    c_idx = [i for i, r in enumerate(rows) if r.c != D.MISSING]
    if c_idx:
        n_c = len(D.C_CODES)
        gold_c = [[int(rows[i].c == j) for j in range(n_c)] for i in c_idx]
        pred_c = [[int(max(range(n_c + 1), key=lambda j: probs["c"][i][j]) == j) for j in range(n_c)] for i in c_idx]
        report["c"] = {"labelled_rows": len(c_idx), **per_code_metrics(gold_c, pred_c, list(D.C_CODES), n_boot, seed)}
    else:
        report["c"] = {"labelled_rows": 0, "note": "no C labels: head not evaluated"}
    return report


def resolve_a_reference(parser, args) -> tuple[Path | None, str]:
    """The A evaluation labels and their provenance kind. A reference that is not fully
    human-labelled must say what it is: there is no way to pass it as a human oracle by omission."""
    if args.labels_a_human and args.labels_a_reference:
        parser.error("--labels-a-human and --labels-a-reference are mutually exclusive")
    if args.labels_a_reference:
        if not args.labels_a_reference_kind:
            parser.error("--labels-a-reference needs --labels-a-reference-kind")
        return args.labels_a_reference, args.labels_a_reference_kind
    if args.labels_a_reference_kind:
        parser.error("--labels-a-reference-kind given without --labels-a-reference")
    # No reference at all -> no kind: nothing is stamped "human" unless human labels were given.
    return args.labels_a_human, ("human" if args.labels_a_human else None)


def load_exported(artifact_dir: str | Path):
    """Rebuild a class-free artifact (model.export_artifact) for evaluation: AutoModel + head
    tensors applied with torch.nn.functional.linear. Mirrors what modules/m3_encoder does."""
    import torch
    from torch import nn
    from transformers import AutoConfig, AutoModel, AutoTokenizer

    d = Path(artifact_dir)
    heads = json.loads((d / "heads.json").read_text(encoding="utf-8"))
    config = AutoConfig.from_pretrained(d, local_files_only=True)
    encoder = AutoModel.from_config(config)
    state = torch.load(d / "weights.pt", map_location="cpu", weights_only=True)
    encoder.load_state_dict(state["encoder"], strict=True)

    class Exported(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.encoder = encoder
            self.head_tensors = {k: (v["weight"], v["bias"]) for k, v in state["heads"].items()}

        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
            pooled = out.pooler_output if getattr(out, "pooler_output", None) is not None else out.last_hidden_state[:, 0]
            return {name: torch.nn.functional.linear(pooled, w.to(pooled.device), b.to(pooled.device))
                    for name, (w, b) in self.head_tensors.items()}

    return Exported(), AutoTokenizer.from_pretrained(d, local_files_only=True), heads


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m training.m3_encoder.evaluate")
    parser.add_argument("--artifact", required=True, type=Path)
    parser.add_argument("--corpus", type=Path, default=D.corpus_path_from_env())
    parser.add_argument("--labels-a", type=Path, action="append",
                        help="pseudo-label file(s); on dev rows reported as agreement only (repeatable)")
    parser.add_argument("--labels-a-human", type=Path, help="HUMAN-labelled oracle jsonl (dev rows): the A-head metric")
    parser.add_argument("--labels-a-reference", type=Path,
                        help="evaluation reference jsonl that is NOT fully human-labelled (dev rows); needs "
                             "--labels-a-reference-kind; mutually exclusive with --labels-a-human")
    parser.add_argument("--labels-a-reference-kind", choices=[k for k in REFERENCE_KINDS if k != "human"],
                        help="the reference's true provenance, stamped into the report as `a.oracle`")
    parser.add_argument("--labels-b", type=Path)
    parser.add_argument("--labels-c", type=Path)
    parser.add_argument("--max-len", type=int, default=128)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import torch

    eval_labels, oracle_kind = resolve_a_reference(parser, args)
    split = D.build_split(args.corpus, args.labels_a, args.labels_b, args.labels_c, labels_a_reference=eval_labels)
    model, tokenizer, heads = load_exported(args.artifact)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    report = evaluate_rows(model, tokenizer, split.dev, args.max_len, args.batch_size, device, n_boot=args.n_boot,
                           oracle_kind=oracle_kind)
    report["artifact_id"] = heads["artifact_id"]
    report["label_coverage"] = split.label_coverage
    report["label_sources"] = split.label_sources
    text = json.dumps(report, indent=2, ensure_ascii=False)
    print(text if len(text) < 4000 else text[:4000] + "\n...")
    if args.out:
        args.out.write_text(text + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
