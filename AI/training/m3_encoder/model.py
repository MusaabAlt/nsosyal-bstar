"""The multi-head encoder m3 trains: one BERTurk encoder, four linear heads.

    binary  2 logits, softmax, OFF = index 1     (the score `binary_offensive` thresholds)
    a       1 logit, sigmoid                     ("profanity present", A1 carrier, ADR-005)
    b       4 logits, sigmoid each, multi-label  (B1 B2 B3 B5; B4 is m6's)
    c       6 logits, softmax                    (C1..C5 + "none of C")

Export format (`export_artifact`) is deliberately class-free so that modules/m3_encoder can
load it without importing this package (rule 2): `encoder.safetensors`-style state dict for the
bare `AutoModel`, plus each head's weight / bias tensors under `heads.<name>.weight|bias`, and
`heads.json` describing layout, label names and which heads were actually trained.
"""
from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from training.m3_encoder.data import A_CODES, B_CODES, BINARY_LABELS, C_CODES, MISSING

HEAD_SIZES = {"binary": len(BINARY_LABELS), "a": len(A_CODES), "b": len(B_CODES), "c": len(C_CODES) + 1}
HEAD_LABELS = {"binary": list(BINARY_LABELS), "a": list(A_CODES), "b": list(B_CODES), "c": [*C_CODES, "NONE"]}


def build_model(base_model_or_dir: str | Path, dropout: float = 0.1):
    """AutoModel encoder + four heads. Imports torch lazily: this file is importable on a
    machine without torch (the data code and the docs do not need it)."""
    import torch
    from torch import nn
    from transformers import AutoConfig, AutoModel

    config = AutoConfig.from_pretrained(base_model_or_dir)
    base = Path(str(base_model_or_dir))
    # A local directory holding only config + tokenizer (the m3 tokenizer dir) has no weights:
    # the smoke test builds a RANDOMLY initialised encoder from it. Never a usable artifact.
    weightless_dir = base.is_dir() and not any((base / n).exists() for n in
                                               ("model.safetensors", "pytorch_model.bin"))

    class MultiHeadEncoder(nn.Module):
        random_init = weightless_dir

        def __init__(self) -> None:
            super().__init__()
            self.encoder = (AutoModel.from_config(config) if weightless_dir
                            else AutoModel.from_pretrained(base_model_or_dir, config=config))
            self.dropout = nn.Dropout(dropout)
            hidden = config.hidden_size
            self.heads = nn.ModuleDict({name: nn.Linear(hidden, size) for name, size in HEAD_SIZES.items()})

        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
            pooled = out.pooler_output if getattr(out, "pooler_output", None) is not None else out.last_hidden_state[:, 0]
            pooled = self.dropout(pooled)
            return {name: head(pooled) for name, head in self.heads.items()}

    return MultiHeadEncoder(), config


def multitask_loss(logits: dict[str, Any], batch: dict[str, Any], weights: dict[str, float] | None = None):
    """Sum of per-head losses, each masked to the rows that carry a label for that head.
    A head with no labelled row in the batch contributes zero (not NaN)."""
    import torch
    import torch.nn.functional as F

    weights = weights or {}
    zero = logits["binary"].sum() * 0.0
    total = zero
    parts: dict[str, float] = {}

    loss_bin = F.cross_entropy(logits["binary"], batch["binary"])
    total = total + weights.get("binary", 1.0) * loss_bin
    parts["binary"] = float(loss_bin)

    a_mask = batch["a"] != MISSING
    if a_mask.any():
        loss_a = F.binary_cross_entropy_with_logits(logits["a"][a_mask].squeeze(-1), batch["a"][a_mask].float())
        total = total + weights.get("a", 1.0) * loss_a
        parts["a"] = float(loss_a)

    b_mask = batch["b"][:, 0] != MISSING
    if b_mask.any():
        loss_b = F.binary_cross_entropy_with_logits(logits["b"][b_mask], batch["b"][b_mask].float())
        total = total + weights.get("b", 1.0) * loss_b
        parts["b"] = float(loss_b)

    c_mask = batch["c"] != MISSING
    if c_mask.any():
        loss_c = F.cross_entropy(logits["c"], batch["c"], ignore_index=MISSING)
        total = total + weights.get("c", 1.0) * loss_c
        parts["c"] = float(loss_c)
    return total, parts


def probabilities(logits: dict[str, Any]) -> dict[str, Any]:
    """Per-head probabilities as plain lists: binary p(OFF), a p, b per code, c per code (+NONE)."""
    import torch

    return {
        "binary": torch.softmax(logits["binary"].float(), dim=-1)[:, 1].tolist(),
        "a": torch.sigmoid(logits["a"].float()).squeeze(-1).tolist(),
        "b": torch.sigmoid(logits["b"].float()).tolist(),
        "c": torch.softmax(logits["c"].float(), dim=-1).tolist(),
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def export_artifact(model, tokenizer_dir: str | Path, out_dir: str | Path, artifact_id: str,
                    trained_heads: dict[str, bool], meta: dict[str, Any]) -> dict[str, Any]:
    """Write a class-free artifact directory:
        weights.pt      {"encoder": state_dict of AutoModel, "heads": {name: {"weight", "bias"}}}
        config.json, tokenizer.json, tokenizer_config.json   copied from tokenizer_dir
        heads.json      layout, labels, trained flags, base model, training meta
        sha256.txt      one line per file: "<digest>  <name>"
        MANIFEST_ROW.md the row to paste into artifacts/MANIFEST.md
    Returns the digests. The module verifies every digest before loading (m3 spec §8)."""
    import torch

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    state = {"encoder": {k: v.detach().cpu() for k, v in model.encoder.state_dict().items()},
             "heads": {name: {"weight": head.weight.detach().cpu(), "bias": head.bias.detach().cpu()}
                       for name, head in model.heads.items()}}
    torch.save(state, out / "weights.pt")
    for name in ("config.json", "tokenizer.json", "tokenizer_config.json"):
        src = Path(tokenizer_dir) / name
        if src.exists():
            shutil.copyfile(src, out / name)
    heads = {"artifact_id": artifact_id, "format": "multi-head-encoder-v1", "heads": {
        name: {"size": size, "labels": HEAD_LABELS[name], "trained": bool(trained_heads.get(name, False)),
               "activation": "softmax" if name in ("binary", "c") else "sigmoid"}
        for name, size in HEAD_SIZES.items()}, "off_index": 1, **meta}
    (out / "heads.json").write_text(json.dumps(heads, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    digests = {p.name: sha256_file(p) for p in sorted(out.iterdir()) if p.name not in ("sha256.txt", "MANIFEST_ROW.md")}
    (out / "sha256.txt").write_text("".join(f"{d}  {n}\n" for n, d in digests.items()), encoding="utf-8")
    (out / "MANIFEST_ROW.md").write_text(
        f"| {artifact_id} | multi-head-encoder-v1, `artifacts/m3_encoder/{out.name}/` | `{digests['weights.pt']}` "
        f"(weights.pt; full list in sha256.txt) | TBD: derive on dev for THIS artifact before use | frozen dev split "
        f"`{meta.get('dev_fingerprint', '')[:8]}…` | {meta.get('date', '')} | m3_encoder | "
        f"base `{meta.get('base_model', '')}`; trained on the Çöltekin training split only |\n", encoding="utf-8")
    return digests
