"""m5_sarcasm: sequential transfer for D1 (degrading sarcasm) on m5's OWN small model (ADR-003).

Stage 1  pre-train a sarcasm/irony classifier on the corpus the entry gate grants
         (jsonl {"text", "label"} with label 1 = sarcastic / ironic, 0 = not).
Stage 2  fine-tune the same encoder on the D1 task (jsonl {"text", "label", "inversion_span"};
         label 1 = D1, 0 = not D1; positives must carry an inversion_span, m5 spec §11).
         The benign-sarcasm control set and the sincere-praise negatives are part of the
         stage-2 negatives and are ALSO evaluated separately, because precision on the control
         set gates acceptance (spec §10, §12).

    python -m training.m5_sarcasm.train --out <dir> --base <small Turkish encoder>
        --stage1 <sarcasm.jsonl> --stage2-train <d1_train.jsonl> --stage2-dev <d1_dev.jsonl>
        --control <benign_sarcasm.jsonl> [--epochs1 3 --epochs2 5 --batch-size 32 --lr 2e-5
        --max-len 128 --seed 42 --fp16] [--smoke N]

Nothing here touches m3 or its artifact: m5 is a separate model with a separate artifact, its own
MANIFEST row and its own `D1` threshold row (spec §6).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import random
import shutil
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MISSING = -100


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def check_d1_rows(rows: list[dict[str, Any]], where: str) -> None:
    """m5 spec §11: a D1 positive with no marked inversion span fails the fixture check."""
    bad = [r for r in rows if int(r["label"]) == 1 and not r.get("inversion_span")]
    if bad:
        raise ValueError(f"{where}: {len(bad)} D1 positive(s) without inversion_span (polarity rule, spec §5); "
                         f"first: {bad[0].get('text', '')[:60]!r}")


def set_seed(seed: int) -> None:
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def build(base: str, dropout: float = 0.1):
    import torch
    from torch import nn
    from transformers import AutoConfig, AutoModel

    config = AutoConfig.from_pretrained(base)
    base_path = Path(base)
    weightless = base_path.is_dir() and not any((base_path / n).exists() for n in ("model.safetensors", "pytorch_model.bin"))

    class SarcasmModel(nn.Module):
        random_init = weightless

        def __init__(self) -> None:
            super().__init__()
            self.encoder = AutoModel.from_config(config) if weightless else AutoModel.from_pretrained(base, config=config)
            self.dropout = nn.Dropout(dropout)
            hidden = config.hidden_size
            self.heads = nn.ModuleDict({"sarcasm": nn.Linear(hidden, 1), "d1": nn.Linear(hidden, 1)})

        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            kwargs = {"input_ids": input_ids, "attention_mask": attention_mask}
            if token_type_ids is not None:
                kwargs["token_type_ids"] = token_type_ids
            out = self.encoder(**kwargs)
            pooled = out.pooler_output if getattr(out, "pooler_output", None) is not None else out.last_hidden_state[:, 0]
            pooled = self.dropout(pooled)
            return {name: head(pooled).squeeze(-1) for name, head in self.heads.items()}

    return SarcasmModel(), config


def loader_for(rows: list[dict[str, Any]], tokenizer, max_len: int, batch_size: int, shuffle: bool, seed: int):
    import torch
    from torch.utils.data import DataLoader

    enc = tokenizer([r["text"] for r in rows], truncation=True, max_length=max_len, padding=False)
    items = [{**{k: enc[k][i] for k in enc}, "label": int(rows[i]["label"])} for i in range(len(rows))]

    def collate(batch):
        features = [{k: v for k, v in b.items() if k != "label"} for b in batch]
        out = tokenizer.pad(features, padding=True, return_tensors="pt")
        out["label"] = torch.tensor([b["label"] for b in batch], dtype=torch.float)
        return out

    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(items, batch_size=batch_size, shuffle=shuffle, collate_fn=collate, generator=generator)


def run_stage(model, head: str, loader, epochs: int, lr: float, device: str, fp16: bool, seed: int,
              log, smoke: bool, eval_fn=None) -> list[dict[str, Any]]:
    import torch
    import torch.nn.functional as F
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import LambdaLR

    total_steps = max(1, len(loader) * epochs) if not smoke else 2
    warmup = int(round(total_steps * 0.1))
    optimizer = AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    scheduler = LambdaLR(optimizer, lambda s: s / max(1, warmup) if s < warmup else max(0.0, (total_steps - s) / max(1, total_steps - warmup)))
    scaler = torch.amp.GradScaler("cuda") if fp16 else None
    history, step = [], 0
    for epoch in range(epochs):
        model.train()
        t0, running, n = time.time(), 0.0, 0
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            inputs = {k: batch[k] for k in ("input_ids", "attention_mask", "token_type_ids") if k in batch}
            optimizer.zero_grad(set_to_none=True)
            if fp16:
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    loss = F.binary_cross_entropy_with_logits(model(**inputs)[head], batch["label"])
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss = F.binary_cross_entropy_with_logits(model(**inputs)[head], batch["label"])
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
            scheduler.step()
            running += float(loss)
            n += 1
            step += 1
            if smoke and step >= 2:
                break
        record = {"stage": head, "epoch": epoch, "train_loss": running / max(1, n), "seconds": round(time.time() - t0, 1)}
        if eval_fn is not None:
            record["dev"] = eval_fn()
        history.append(record)
        log(json.dumps(record, ensure_ascii=False))
        if smoke:
            break
    return history


def predict(model, head: str, rows, tokenizer, max_len: int, batch_size: int, device: str) -> list[float]:
    import torch

    model.eval()
    probs: list[float] = []
    with torch.no_grad():
        for start in range(0, len(rows), batch_size):
            chunk = rows[start:start + batch_size]
            enc = tokenizer([r["text"] for r in chunk], truncation=True, max_length=max_len, padding=True, return_tensors="pt")
            enc = {k: v.to(device) for k, v in enc.items()}
            probs.extend(torch.sigmoid(model(**enc)[head].float()).tolist())
    return probs


def prf(gold: list[int], pred: list[int]) -> dict[str, Any]:
    tp = sum(g and p for g, p in zip(gold, pred)); fp = sum((not g) and p for g, p in zip(gold, pred))
    fn = sum(g and (not p) for g, p in zip(gold, pred)); tn = sum((not g) and (not p) for g, p in zip(gold, pred))
    return {"tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": tp / (tp + fp) if tp + fp else None, "recall": tp / (tp + fn) if tp + fn else None,
            "fpr": fp / (fp + tn) if fp + tn else None}


def bootstrap(gold: list[int], pred: list[int], n_boot: int, seed: int) -> dict[str, Any]:
    rng = random.Random(seed)
    point = prf(gold, pred)
    samples: dict[str, list[float]] = {"precision": [], "recall": [], "fpr": []}
    n = len(gold)
    for _ in range(n_boot if n else 0):
        idx = [rng.randrange(n) for _ in range(n)]
        s = prf([gold[i] for i in idx], [pred[i] for i in idx])
        for k in samples:
            if s[k] is not None:
                samples[k].append(s[k])

    def pct(v, q):
        if not v:
            return None
        v = sorted(v)
        return v[min(len(v), max(1, round(q / 100 * len(v)))) - 1]
    return {**point, "n": n, **{f"{k}_ci": [pct(v, 2.5), pct(v, 97.5)] for k, v in samples.items()}}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m training.m5_sarcasm.train")
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--base", required=True, help="small / distilled Turkish encoder (m5 spec §6 constraint)")
    parser.add_argument("--stage1", type=Path, help="sarcasm corpus jsonl {text,label}; omit to skip pre-training")
    parser.add_argument("--stage2-train", type=Path, required=True)
    parser.add_argument("--stage2-dev", type=Path, required=True)
    parser.add_argument("--control", type=Path, help="benign-sarcasm control set jsonl {text,label=0}")
    parser.add_argument("--gate-record", type=Path, help="GATE_RECORD.md naming the dataset (spec §11); copied into the artifact")
    parser.add_argument("--epochs1", type=int, default=3)
    parser.add_argument("--epochs2", type=int, default=5)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max-len", type=int, default=128)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--fp16", action="store_true")
    parser.add_argument("--n-boot", type=int, default=1000)
    parser.add_argument("--artifact-id", default=None)
    parser.add_argument("--smoke", type=int, default=0)
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    import torch
    from transformers import AutoTokenizer

    set_seed(args.seed)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    fp16 = bool(args.fp16) and device == "cuda"
    tokenizer = AutoTokenizer.from_pretrained(args.base)
    model, config = build(args.base)
    model.to(device)

    s2_train, s2_dev = read_jsonl(args.stage2_train), read_jsonl(args.stage2_dev)
    check_d1_rows(s2_train, "stage2-train")
    check_d1_rows(s2_dev, "stage2-dev")
    control = read_jsonl(args.control) if args.control else []
    if args.smoke:
        s2_train, s2_dev, control = s2_train[:args.smoke], s2_dev[:max(4, args.smoke)], control[:args.smoke]
    history: list[dict[str, Any]] = []

    if args.stage1:
        s1 = read_jsonl(args.stage1)
        if args.smoke:
            s1 = s1[:args.smoke]
        history += run_stage(model, "sarcasm", loader_for(s1, tokenizer, args.max_len, args.batch_size, True, args.seed),
                             args.epochs1, args.lr, device, fp16, args.seed, print, bool(args.smoke))

    def dev_eval() -> dict[str, Any]:
        probs = predict(model, "d1", s2_dev, tokenizer, args.max_len, 64, device)
        gold = [int(r["label"]) for r in s2_dev]
        pred = [int(p >= 0.5) for p in probs]                      # reporting point only; the D1 row is derived on dev
        out = {"dev": bootstrap(gold, pred, 50 if args.smoke else args.n_boot, args.seed)}
        if control:
            cp = predict(model, "d1", control, tokenizer, args.max_len, 64, device)
            out["control_precision_gate"] = bootstrap([0] * len(control), [int(p >= 0.5) for p in cp],
                                                      50 if args.smoke else args.n_boot, args.seed)
        return out

    history += run_stage(model, "d1", loader_for(s2_train, tokenizer, args.max_len, args.batch_size, True, args.seed),
                         args.epochs2, args.lr, device, fp16, args.seed, print, bool(args.smoke), eval_fn=dev_eval)

    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    artifact_id = args.artifact_id or f"{'smoke-' if args.smoke else ''}m5-sarcasm-d1-{date}"
    out = args.out / "artifact" / artifact_id
    out.mkdir(parents=True, exist_ok=True)
    tok_dir = args.out / "tokenizer"
    tokenizer.save_pretrained(tok_dir)
    config.save_pretrained(tok_dir)
    torch.save({"encoder": model.encoder.state_dict(),
                "heads": {n: {"weight": h.weight.detach().cpu(), "bias": h.bias.detach().cpu()} for n, h in model.heads.items()}},
               out / "weights.pt")
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        if (tok_dir / name).exists():
            shutil.copyfile(tok_dir / name, out / name)
    if args.gate_record and args.gate_record.exists():
        shutil.copyfile(args.gate_record, out / "GATE_RECORD.md")
    meta = {"artifact_id": artifact_id, "format": "single-head-encoder-v1", "head": "d1", "activation": "sigmoid",
            "code": "D1", "base_model": args.base, "date": date, "seed": args.seed,
            "hyperparams": {k: v for k, v in vars(args).items() if not isinstance(v, Path)},
            "stage1_used": bool(args.stage1), "random_init": bool(getattr(model, "random_init", False)),
            "smoke": bool(args.smoke), "history": history, "final": dev_eval()}
    (out / "heads.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digests = {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.name != "sha256.txt"}
    (out / "sha256.txt").write_text("".join(f"{d}  {n}\n" for n, d in digests.items()), encoding="utf-8")
    print(f"exported {out}  weights sha256 {digests['weights.pt']}")
    print(json.dumps(meta["final"], ensure_ascii=False)[:800])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
