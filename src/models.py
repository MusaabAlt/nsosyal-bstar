"""Fine-tuning + inference for the Turkish transformer baselines.

Fulfils phase 01 S4: `dbmdz/bert-base-turkish-cased`, max_len 128, seed 42,
fp16, lr 2e-5, batch 32, 3 epochs, 10% linear warmup, checkpoint every epoch.
Single configuration -- no hyperparameter search (phase 01 says a sweep costs a
day and earns nothing on a rubric that rewards the diagnosis).

Why a plain PyTorch loop and not `transformers.Trainer`
-------------------------------------------------------
Trainer's argument names have churned across releases (`evaluation_strategy` ->
`eval_strategy`, tokenizer -> processing_class, ...). A Colab session that
resolves a slightly different transformers version would fail at minute 0 or,
worse, silently ignore an argument. The loop below is ~80 lines, depends only on
stable torch APIs, and makes the seeding, the checkpointing and the resume path
explicit -- all three are things the master brief requires us to be able to
state exactly.

Deliberately NOT done here
--------------------------
* No class weighting and no threshold tuning. The corpus is ~19.3% OFF, so a
  weighted loss would raise OFF-recall -- which is precisely the quantity phase
  01 measures. Tilting it before the measurement would mean the diagnosis
  describes our intervention rather than the model. argmax at 0.5 throughout.
* No early stopping on the pivotal metric. Epoch selection uses dev macro-F1
  only; dev is the design set (briefing S7.2), the test set is untouched.

Torch/transformers are imported INSIDE functions, so `import src.models` stays
free in the local Python 3.14 venv where neither is installed.
"""

import json
import os
import random
import time
from pathlib import Path

LABELS = ("NOT", "OFF")
LABEL2ID = {"NOT": 0, "OFF": 1}
ID2LABEL = {0: "NOT", 1: "OFF"}


# --------------------------------------------------------------------------
# reproducibility
# --------------------------------------------------------------------------


def set_seed(seed):
    """Seed every generator that can move a number in this project."""
    import numpy as np
    import torch

    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    return seed


def environment_info():
    """Versions + device, recorded in run_config.json. A result that cannot be
    traced to the stack that produced it is not reproducible."""
    info = {}
    try:
        import torch

        info["torch"] = torch.__version__
        info["cuda_available"] = torch.cuda.is_available()
        info["device_name"] = torch.cuda.get_device_name(0) if torch.cuda.is_available() else None
    except ImportError:
        info["torch"] = None
    try:
        import transformers

        info["transformers"] = transformers.__version__
    except ImportError:
        info["transformers"] = None
    try:
        import sklearn

        info["scikit_learn"] = sklearn.__version__
    except ImportError:
        info["scikit_learn"] = None
    return info


# --------------------------------------------------------------------------
# data plumbing
# --------------------------------------------------------------------------


def encode(rows, tokenizer, max_len, with_labels=True):
    """Tokenise WITHOUT padding -- padding happens per batch in the collator, so
    a batch of short tweets does not pay for a 128-token pad."""
    enc = tokenizer(
        [r["text"] for r in rows],
        truncation=True,
        max_length=max_len,
        padding=False,
    )
    items = []
    for i in range(len(rows)):
        item = {k: enc[k][i] for k in enc}
        if with_labels:
            item["labels"] = LABEL2ID[rows[i]["label"]]
        items.append(item)
    return items


def _make_loader(items, tokenizer, batch_size, shuffle, seed):
    import torch
    from torch.utils.data import DataLoader

    def collate(batch):
        # NB: copy, never pop. DataLoader hands over the dataset's own dicts, so
        # popping "labels" here would strip the labels out of the dataset itself
        # and epoch 2 would train on nothing.
        labels = [b["labels"] for b in batch] if "labels" in batch[0] else None
        features = [{k: v for k, v in b.items() if k != "labels"} for b in batch]
        out = tokenizer.pad(features, padding=True, return_tensors="pt")
        if labels is not None:
            out["labels"] = torch.tensor(labels, dtype=torch.long)
        return out

    generator = None
    if shuffle:
        generator = torch.Generator()
        generator.manual_seed(seed)
    return DataLoader(
        items,
        batch_size=batch_size,
        shuffle=shuffle,
        collate_fn=collate,
        generator=generator,
        num_workers=0,  # deterministic ordering; the job is GPU-bound anyway
    )


def load_model(model_name, num_labels=2):
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(
        model_name,
        num_labels=num_labels,
        id2label=ID2LABEL,
        label2id=LABEL2ID,
    )
    return tokenizer, model


# --------------------------------------------------------------------------
# inference
# --------------------------------------------------------------------------


def predict(model, tokenizer, rows, batch_size=64, max_len=128, device=None):
    """Returns (pred_labels, p_off) -- softmax probability of the OFF class.

    Confidences are produced here even though calibration is a later phase: the
    failure analysis and the risk-coverage curve both read them, and recovering
    them later would mean retraining (phase 01 S5).
    """
    import torch

    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    model.eval().to(device)
    items = encode(rows, tokenizer, max_len, with_labels=False)
    loader = _make_loader(items, tokenizer, batch_size, shuffle=False, seed=0)

    probs = []
    with torch.no_grad():
        for batch in loader:
            batch = {k: v.to(device) for k, v in batch.items()}
            logits = model(**batch).logits.float()
            probs.extend(torch.softmax(logits, dim=-1)[:, LABEL2ID["OFF"]].tolist())

    preds = ["OFF" if p >= 0.5 else "NOT" for p in probs]
    return preds, probs


# --------------------------------------------------------------------------
# training
# --------------------------------------------------------------------------


def train(
    train_rows,
    dev_rows,
    model_name,
    ckpt_dir,
    epochs=3,
    batch_size=32,
    lr=2e-5,
    max_len=128,
    seed=42,
    warmup_ratio=0.1,
    weight_decay=0.01,
    max_grad_norm=1.0,
    fp16=True,
    resume=False,
    eval_batch_size=64,
    log=print,
):
    """Fine-tune and return (model, tokenizer, history).

    Checkpointing (a free Colab session can drop mid-run):
      <ckpt_dir>/latest.pt  full training state, rewritten after every epoch --
                            this is the resume point, `--resume` reads it
      <ckpt_dir>/best.pt    weights of the best epoch by dev macro-F1
    Result FILES are never overwritten (master brief S3); checkpoints rotate by
    design, which is what makes resume possible.

    On return the model holds the best epoch's weights, not the last epoch's.
    """
    import torch
    from torch.optim import AdamW
    from torch.optim.lr_scheduler import LambdaLR

    from src import evaluate

    set_seed(seed)
    ckpt_dir = Path(ckpt_dir)
    ckpt_dir.mkdir(parents=True, exist_ok=True)
    latest_path = ckpt_dir / "latest.pt"
    best_path = ckpt_dir / "best.pt"

    device = "cuda" if torch.cuda.is_available() else "cpu"
    use_fp16 = bool(fp16) and device == "cuda"
    log(f"device={device}  fp16={use_fp16}  model={model_name}")
    if device == "cpu":
        log("  [warn] no GPU visible -- this will take hours, not minutes.")

    tokenizer, model = load_model(model_name)
    model.to(device)

    train_items = encode(train_rows, tokenizer, max_len)
    train_loader = _make_loader(train_items, tokenizer, batch_size, shuffle=True, seed=seed)
    steps_per_epoch = len(train_loader)
    total_steps = steps_per_epoch * epochs
    warmup_steps = int(round(total_steps * warmup_ratio))

    decay, no_decay = [], []
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        (no_decay if (name.endswith("bias") or "LayerNorm" in name) else decay).append(p)
    optimizer = AdamW(
        [{"params": decay, "weight_decay": weight_decay},
         {"params": no_decay, "weight_decay": 0.0}],
        lr=lr,
    )

    def lr_lambda(step):
        if step < warmup_steps:
            return step / max(1, warmup_steps)
        remaining = total_steps - warmup_steps
        return max(0.0, (total_steps - step) / max(1, remaining))

    scheduler = LambdaLR(optimizer, lr_lambda)

    scaler = None
    if use_fp16:
        try:  # torch >= 2.4
            scaler = torch.amp.GradScaler("cuda")
        except (AttributeError, TypeError):  # older torch
            scaler = torch.cuda.amp.GradScaler()

    start_epoch = 0
    best_f1 = -1.0
    history = []
    if resume:
        if not latest_path.exists():
            raise FileNotFoundError(
                f"--resume was passed but {latest_path} does not exist. "
                "Start the run without --resume (nothing to resume from)."
            )
        state = torch.load(latest_path, map_location=device, weights_only=False)
        model.load_state_dict(state["model"])
        optimizer.load_state_dict(state["optimizer"])
        scheduler.load_state_dict(state["scheduler"])
        if scaler is not None and state.get("scaler"):
            scaler.load_state_dict(state["scaler"])
        random.setstate(state["py_rng"])
        torch.set_rng_state(state["torch_rng"])
        start_epoch = state["epoch"] + 1
        best_f1 = state["best_f1"]
        history = state["history"]
        log(f"resumed from {latest_path}: epochs 0..{state['epoch']} done, best dev macro-F1={best_f1:.4f}")

    for epoch in range(start_epoch, epochs):
        model.train()
        t0 = time.time()
        running = 0.0
        for step, batch in enumerate(train_loader, start=1):
            batch = {k: v.to(device) for k, v in batch.items()}
            optimizer.zero_grad(set_to_none=True)
            if use_fp16:
                with torch.amp.autocast(device_type="cuda", dtype=torch.float16):
                    loss = model(**batch).loss
                scaler.scale(loss).backward()
                scaler.unscale_(optimizer)
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                scaler.step(optimizer)
                scaler.update()
            else:
                loss = model(**batch).loss
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_grad_norm)
                optimizer.step()
            scheduler.step()
            running += loss.item()
            if step % 100 == 0 or step == steps_per_epoch:
                log(f"  epoch {epoch + 1}/{epochs}  step {step}/{steps_per_epoch}  "
                    f"loss={running / step:.4f}  lr={scheduler.get_last_lr()[0]:.2e}")

        # dev evaluation: macro-F1 only, no bootstrap -- this picks the epoch,
        # it is not a reported number.
        dev_preds, _ = predict(model, tokenizer, dev_rows, eval_batch_size, max_len, device)
        dev_gold = [r["label"] for r in dev_rows]
        f1 = evaluate.macro_f1(dev_gold, dev_preds)
        entry = {
            "epoch": epoch + 1,
            "train_loss": running / max(1, steps_per_epoch),
            "dev_macro_f1": f1,
            "seconds": round(time.time() - t0, 1),
        }
        history.append(entry)
        log(f"  epoch {epoch + 1} done: train_loss={entry['train_loss']:.4f}  "
            f"dev_macro_f1={f1:.4f}  ({entry['seconds']}s)")

        model.train()  # torch state back to training before the checkpoint
        torch.save(
            {
                "epoch": epoch,
                "model": model.state_dict(),
                "optimizer": optimizer.state_dict(),
                "scheduler": scheduler.state_dict(),
                "scaler": scaler.state_dict() if scaler is not None else None,
                "py_rng": random.getstate(),
                "torch_rng": torch.get_rng_state(),
                "best_f1": max(best_f1, f1),
                "history": history,
                "config": {"model_name": model_name, "lr": lr, "batch_size": batch_size,
                           "epochs": epochs, "max_len": max_len, "seed": seed},
            },
            latest_path,
        )
        if f1 > best_f1:
            best_f1 = f1
            torch.save({"epoch": epoch, "model": model.state_dict(), "dev_macro_f1": f1}, best_path)
            log(f"  new best epoch ({f1:.4f}) -> {best_path}")
        (ckpt_dir / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")

    if best_path.exists():
        best = torch.load(best_path, map_location=device, weights_only=False)
        model.load_state_dict(best["model"])
        log(f"loaded best epoch {best['epoch'] + 1} (dev macro-F1={best['dev_macro_f1']:.4f}) for final evaluation")

    return model, tokenizer, history
