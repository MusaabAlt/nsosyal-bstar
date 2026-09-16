"""m3_encoder - shared encoder. PARTIAL: wraps the frozen study baseline only.

Catches:
  * a binary offensive probability on the raw channel, `signals["raw_score"]`:
    p(OFF) from the frozen phase-01 BERTurk checkpoint (epoch 1), the model every
    study number and the stage-1 `binary_offensive` threshold was measured on
  * `signals["artifact"]`: the artifact id of that checkpoint (artifacts/MANIFEST.md)
  * a note whenever the input is longer than MAX_LEN tokens and was truncated

Deliberately does NOT (owner decisions, 2026-09-15):
  * emit content scores. The checkpoint is a binary OFF/NOT classifier; OFF is not
    "profanity present", so nothing is emitted on the A1 carrier, and the B and C
    heads do not exist yet (spec.md §1, §4, §12 remain open)
  * score the normalized channel. `norm_score` is not published: the threshold was
    derived on raw text only and no threshold applies to a normalized score
  * read `ctx.charsafe_text`. BERTurk is cased and m0 lowercases; the threshold was
    fitted on scores of the original text, so the original text is what is scored
  * calibrate, threshold or fuse anything (spec.md §3, §6)
  * touch the network: the checkpoint and tokenizer are local files, verified by
    sha256 before use; a missing or different file fails the module closed

Inference reproduces the study exactly (diagnosis/src/models.py `encode` and
`predict`, copied, not imported): max_len 128, first tokens kept, no padding for a
single post, eval mode, FP32 on CPU, softmax index 1 = OFF.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput

ARTIFACT_ID = "m3-berturk-pytorch-fp32-epoch1"
ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts" / "m3_encoder"
# Environment overrides, so a Colab or demo machine can point at Drive or another disk.
CHECKPOINT_ENV = "NSOSYAL_M3_CHECKPOINT"
TOKENIZER_ENV = "NSOSYAL_M3_TOKENIZER"
DEFAULT_CHECKPOINT = ARTIFACTS / "berturk_epoch1.pt"
DEFAULT_TOKENIZER = ARTIFACTS / "tokenizer"

# sha256 of every file loaded (artifacts/MANIFEST.md). The checkpoint is the phase-01
# best.pt (epoch 1), recorded in diagnosis/docs/RESULTS_LOG.md.
CHECKPOINT_SHA256 = "43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca"
TOKENIZER_SHA256 = {
    "config.json": "980b01ddb94ee8cc2533e064bdca97584b96bbf9755601217ae3d13460c58f48",
    "tokenizer.json": "d424e0bceb7f017dfced77157d14647505b28b41bfc8d9bffd5631f1b1fe61e5",
    "tokenizer_config.json": "d50873edfa649e9950fbfb196da01d0b2b4470a25e2ac711cf5c7022761b0a04",
}

# The study's truncation policy (m3 spec.md §5): 128 tokens, first tokens kept.
MAX_LEN = 128
OFF_INDEX = 1  # id2label {0: NOT, 1: OFF}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_paths() -> tuple[Path, Path]:
    return (Path(os.environ.get(CHECKPOINT_ENV, DEFAULT_CHECKPOINT)),
            Path(os.environ.get(TOKENIZER_ENV, DEFAULT_TOKENIZER)))


class EncoderModule(BaseModule):
    name = ModuleName.M3_ENCODER
    version = "0.1.0"
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # encoder heads score the whole post, not a substring.
    emits_spans = False

    def _load(self) -> None:
        checkpoint, tokenizer_dir = artifact_paths()
        missing = [str(p) for p in (checkpoint, *(tokenizer_dir / n for n in TOKENIZER_SHA256)) if not p.is_file()]
        if missing:
            raise FileNotFoundError(f"m3 artifact files missing (git-ignored; see artifacts/MANIFEST.md, "
                                    f"{CHECKPOINT_ENV} / {TOKENIZER_ENV}): {missing}")
        wrong = [f"{p.name}: {sha256(p)}" for p, want in
                 ((checkpoint, CHECKPOINT_SHA256), *((tokenizer_dir / n, h) for n, h in TOKENIZER_SHA256.items()))
                 if sha256(p) != want]
        if wrong:
            raise ValueError(f"m3 artifact sha256 mismatch, not the frozen files: {wrong}")

        import torch
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

        self._torch = torch
        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
        config = AutoConfig.from_pretrained(tokenizer_dir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_config(config)
        state = torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state["model"], strict=True)
        self._model = model.float().to("cpu").eval()

    def _run(self, ctx: Context) -> ModuleOutput:
        notes: list[str] = []
        n_tokens = len(self._tokenizer(ctx.text, add_special_tokens=True, verbose=False)["input_ids"])
        if n_tokens > MAX_LEN:
            notes.append(f"truncated: {n_tokens} tokens, scored the first {MAX_LEN}")
        encoded = self._tokenizer([ctx.text], truncation=True, max_length=MAX_LEN, padding=False,
                                  return_tensors="pt")
        with self._torch.no_grad():
            logits = self._model(**encoded).logits.float()
            p_off = float(self._torch.softmax(logits, dim=-1)[0, OFF_INDEX])
        return ModuleOutput(signals={"raw_score": p_off, "artifact": ARTIFACT_ID}, notes=notes)
