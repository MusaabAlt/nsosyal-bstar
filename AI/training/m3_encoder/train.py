"""Fine-tune the multi-head encoder on the frozen split.

    python -m training.m3_encoder.train --out <dir> [--corpus PATH] [--labels-a PATH ...]
        [--labels-a-human PATH] [--labels-b PATH] [--labels-c PATH] [--base dbmdz/bert-base-turkish-cased]
        [--epochs 3 --batch-size 32 --lr 2e-5 --max-len 128 --warmup-ratio 0.1
         --weight-decay 0.01 --seed 42 --grad-accum 1 --fp16] [--resume] [--smoke N]

Defaults reproduce the study's phase-01 hyperparameters (docs/team/abdullah/RESOURCES.md,
"Recorded hyperparameters"), so the binary head is comparable with the frozen baseline.
Checkpointing follows the study: <out>/latest.pt after every epoch (resume point), <out>/best.pt
for the best dev binary macro-F1. On completion the best weights are exported as a class-free
artifact under <out>/artifact/<artifact_id>/ (model.export_artifact) together with a dev
evaluation (evaluate.py) - both on the SAME frozen dev split.

`--smoke N` trains on N rows for 2 steps on whatever device exists: a CPU proof that the code
runs end to end. It never produces a usable artifact (the id is prefixed `smoke-`).
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from training.m3_encoder import data as D
from training.m3_encoder import evaluate as E
from training.m3_encoder import model as M

DEFAULT_BASE = "dbmdz/bert-base-turkish-cased"


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def encode(rows: list[D.Row], tokenizer, max_len: int) -> list[dict]:
    enc = tokenizer([r.text for r in rows], truncation=True, max_length=max_len, padding=False)
    items = []
    for i, r in enumerate(rows):
        item = {k: enc[k][i] for k in enc}
        item.update({"binary": r.binary, "a": r.a, "b": list(r.b), "c": r.c})
        items.append(item)
    return items


def make_loader(items: list[dict], tokenizer, batch_size: int, shuffle: bool, seed: int):
    import torch
    from torch.utils.data import DataLoader

    label_keys = ("binary", "a", "b", "c")

    def collate(batch):
        features = [{k: v for k, v in b.items() if k not in label_keys} for b in batch]
        out = tokenizer.pad(features, padding=True, return_tensors="pt")
        for key in label_keys:
            out[key] = torch.tensor([b[key] for b in batch], dtype=torch.long)
        return out

    generator = None
    if shuffle:
        generator = torch.Generator()
        generator.manual_seed(seed)
    return DataLoader(items, batch_size=batch_size, shuffle=shuffle, collate_fn=collate, generator=generator,
                      num_workers=0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m training.m3_encoder.train", description=__doc__.split("\n")[0])
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--corpus", type=Path, default=D.corpus_path_from_env())
    parser.add_argument("--labels-a", type=Path, action="append",
                        help="A pseudo-label file(s), repeatable: train rows supervise, dev rows report agreement only")
    parser.add_argument("--labels-a-human", type=Path,
                        help="human 'profanity present' jsonl on DEV rows: the A head's evaluation oracle, never trained on")
    parser.add_argument("--labels-a-reference", type=Path,
                        help="A evaluation reference on DEV rows that is NOT fully human-labelled; needs "
                             "--labels-a-reference-kind; never trained on")
    parser.add_argument("--labels-a-reference-kind", choices=[k for k in E.REFERENCE_KINDS if k != "human"],
                        help="the reference's true provenance, stamped into dev_eval.json as `a.oracle`")
    parser.add_argument("--labels-b", type=Path)
    parser.add_argument("--labels-c", type=Path)
    parser.add_argument("--base", default=DEFAULT_BASE)
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--eval-batch-size", type=int, default=64)
    parser.add_argument("--grad-accum", type=int, default=1)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-len", type=int, default=128)
    parser.add_argument("--warmup-ratio", type=float, default=0.1)
    parser.add_argument("--weight-decay", type=float, default=0.01)
    parser.add_argument("--max-grad-norm", type=float, default=1.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--artifact-id", default=None, help="default m3-berturk-multihead-<date>")
    parser.add_argument("--smoke", type=int, default=0, help="train on N rows for 2 steps (CPU proof), no real artifact")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    import torch
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import LambdaLR
    from transformers import AutoTokenizer

    eval_labels, oracle_kind = E.resolve_a_reference(parser, args)
    D.refuse_banned(args.base, *(str(p) for p in (args.corpus, *(args.labels_a or []), eval_labels,
                                                  args.labels_b, args.labels_c) if p))
    set_seed(args.seed)
    split = D.build_split(args.corpus, args.labels_a, args.labels_b, args.labels_c, labels_a_human=eval_labels)
    train_rows, dev_rows = split.train, split.dev
    if args.smoke:
        rng = random.Random(args.seed)
        train_rows = rng.sample(train_rows, min(args.smoke, len(train_rows)))
        dev_rows = dev_rows[:max(8, min(args.smoke, len(dev_rows)))]
    print(f"split: {split.label_coverage}  (smoke={args.smoke})")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = bool(args.fp16) and device == "cuda"
    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model, config = M.build_model(args.base)
    model.to(device)
    print(f"device={device} fp16={use_fp16} base={args.base} params={sum(p.numel() for p in model.parameters())}")

    train_items = encode(train_rows, tokenizer, args.max_len)
    loader = make_loader(train_items, tokenizer, args.batch_size, shuffle=True, seed=args.seed)
    steps_per_epoch = max(1, len(loader) // args.grad_accum)
    total_steps = steps_per_epoch * args.epochs if not args.smoke else 2
    warmup_steps = int(round(total_steps * args.warmup_ratio))

    decay, no_decay = [], []
    for name, p in model.named_parameters():
        (no_decay if (name.endswith("bias") or "LayerNorm" in name) else decay).append(p)
    optimizer = AdamW([{"params": decay, "weight_decay": args.weight_decay},
                       {"params": no_decay, "weight_decay": 0.0}], lr=args.lr)

    def lr_lambda(step: int) -> float:
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        return max(0.0, (total_steps - step) / max(1, total_steps - warmup_steps))

    scheduler = LambdaLR(optimizer, lr_lambda)
    scaler = torch.amp.GradScaler("cuda") if use_fp16 else None

    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    latest, best = out / "latest.pt", out / "best.pt"
    start_epoch, best_f1, history = 0, -1.0, []
    if args.resume:
        if not latest.exists():
            raise FileNotFoundError(f"--resume given but {latest} does not exist")
        state = torch.load(latest, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        if scaler is not None and state.get("scaler"):
            scaler.load_state_dict(state["scaler"])
        start_epoch, best_f1, history = state["epoch"] + 1, state["best_f1"], state["history"]
        print(f"resumed from {latest}: epochs 0..{state['epoch']} done, best dev macro-F1={best_f1:.4f}")

    global_step = 0
    for epoch in range(start_epoch, args.epochs):
        model.train()
        t0, running, parts_sum, n_batches = time.time(), 0.0, {}, 0
        optimizer.zero_grad(set_to_none=True)
        for step, batch in enumerate(loader, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            inputs = {k: batch[k] for k in ("input_ids", "attention_mask", "token_type_ids") if k in batch}
            if use_fp16:
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    loss, parts = M.multitask_loss(model(**inputs), batch)
                scaler.scale(loss / args.grad_accum).backward()
            else:
                loss, parts = M.multitask_loss(model(**inputs), batch)
                (loss / args.grad_accum).backward()
            running += float(loss)
            n_batches += 1
            for k, v in parts.items():
                parts_sum[k] = parts_sum.get(k, 0.0) + v
            if step % args.grad_accum == 0:
                if scaler is not None:
                    scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), args.max_grad_norm)
                if scaler is not None:
                    scaler.step(optimizer)
                    scaler.update()
                else:
                    optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
            if args.smoke and global_step >= 2:
                break
        dev_report = E.evaluate_rows(model, tokenizer, dev_rows, args.max_len, args.eval_batch_size, device,
                                     n_boot=50 if args.smoke else 1000, seed=args.seed, oracle_kind=oracle_kind)
        f1 = dev_report["binary"]["macro_f1"]["value"]
        record = {"epoch": epoch, "train_loss": running / max(1, n_batches),
                  "train_loss_parts": {k: v / max(1, n_batches) for k, v in parts_sum.items()},
                  "dev_binary_macro_f1": f1, "seconds": round(time.time() - t0, 1)}
        history.append(record)
        print(json.dumps(record))
        if f1 > best_f1:
            best_f1 = f1
            torch.save({"model": model.state_dict(), "epoch": epoch, "dev_macro_f1": f1}, best)
        torch.save({"model": model.state_dict(), "optimizer": optimizer.state_dict(),
                    "scheduler": scheduler.state_dict(), "scaler": scaler.state_dict() if scaler else None,
                    "epoch": epoch, "best_f1": best_f1, "history": history}, latest)
        if args.smoke:
            break

    # Export the BEST epoch (the study's rule), then evaluate it on dev.
    state = torch.load(best, map_location=device, weights_only=False)
    model.load_state_dict(state["model"])
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    artifact_id = args.artifact_id or f"{'smoke-' if args.smoke else ''}m3-berturk-multihead-{date}"
    trained = {"binary": True, "a": split.label_coverage["train"]["a"] > 0,
               "b": split.label_coverage["train"]["b"] > 0, "c": split.label_coverage["train"]["c"] > 0}
    tokenizer_dir = out / "tokenizer"
    tokenizer.save_pretrained(tokenizer_dir)
    config.save_pretrained(tokenizer_dir)
    meta = {"base_model": args.base, "date": date, "seed": args.seed, "epochs": args.epochs,
            "best_epoch": int(state["epoch"]), "hyperparams": {k: v for k, v in vars(args).items()
                                                               if k not in ("out", "corpus", "labels_a", "labels_a_human",
                                                                            "labels_a_reference", "labels_b", "labels_c")},
            "a_evaluation_reference_kind": oracle_kind if eval_labels else None,
            "split": split.meta, "label_coverage": split.label_coverage, "label_sources": split.label_sources,
            "a_head_supervision": "terlik-derived pseudo-labels (keyword); quality claims only against the human "
                                  "dev oracle (dev_eval.json 'a'), never against pseudo-label agreement",
            "dev_fingerprint": D.DEV_FINGERPRINT, "max_len": args.max_len, "truncation": "first tokens kept",
            "smoke": bool(args.smoke), "random_init": bool(getattr(model, "random_init", False)),
            "history": history}
    artifact_dir = out / "artifact" / artifact_id
    digests = M.export_artifact(model, tokenizer_dir, artifact_dir, artifact_id, trained, meta)
    report = E.evaluate_rows(model, tokenizer, dev_rows, args.max_len, args.eval_batch_size, device,
                             n_boot=50 if args.smoke else 1000, seed=args.seed, oracle_kind=oracle_kind)
    report.update({"artifact_id": artifact_id, "digests": digests, "label_coverage": split.label_coverage,
                   "label_sources": split.label_sources, "smoke": bool(args.smoke)})
    (artifact_dir / "dev_eval.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"exported {artifact_dir}  weights sha256 {digests['weights.pt']}")
    print(f"dev binary macro-F1 {report['binary']['macro_f1']['value']:.4f}  trained heads {trained}")
    a = report["a"]
    if a.get("oracle"):
        m = a["A1"]
        print(f"A head vs reference [{a['oracle']}] ({a['labelled_rows']} dev rows, support {m['support']}"
              f"{', INSUFFICIENT SAMPLE' if m['insufficient_sample'] else ''}): "
              f"P {m['precision']['value']} R {m['recall']['value']} F1 {m['f1']['value']}")
    else:
        print("A head: no human oracle given - no A-head quality claim (pseudo-label agreement is in dev_eval.json "
              "under a_pseudo_label_agreement and is NOT accuracy)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
