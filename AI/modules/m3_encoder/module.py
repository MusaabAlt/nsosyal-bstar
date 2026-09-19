"""m3_encoder - shared encoder. PARTIAL: the deployed artifact is the rule-v4 multi-head encoder
(binary + A heads trained; B and C heads NOT trained), owner decision 2026-09-19.

Artifact selection (no silent fallback, ever):
  * NSOSYAL_M3_ARTIFACT unset -> the DEPLOYED artifact DEPLOYED_ID in artifacts/m3_encoder/<id>/
    (git-ignored; copied from Drive, artifacts/MANIFEST.md). Its heads.json must name DEPLOYED_ID and
    its weights.pt must hash to DEPLOYED_WEIGHTS_SHA256; missing or different -> the module fails
    closed and the result is degraded. It never falls back to another artifact.
  * NSOSYAL_M3_ARTIFACT=m3-berturk-pytorch-fp32-epoch1 -> the frozen binary baseline, on explicit
    request only (NSOSYAL_M3_CHECKPOINT / NSOSYAL_M3_TOKENIZER locate its files).
  * NSOSYAL_M3_ARTIFACT=<directory> -> that multi-head artifact, an explicit override (Colab, tests),
    every file verified against its sha256.txt; one that claims a pinned id must carry the pinned
    weights.

Catches:
  * a binary offensive probability per channel: `signals["raw_score"]` on `ctx.text` and
    `signals["norm_score"]` on `ctx.normalized_text` (spec §4: the encoder runs twice per request;
    when the normalized channel is absent there is no norm_score, when it equals the raw text the
    raw score is reused - the same input cannot score differently and the second pass is skipped)
  * `signals["artifact"]`: the artifact id that produced the scores (artifacts/MANIFEST.md)
  * a note whenever a channel is longer than MAX_LEN tokens and was truncated, and
    `signals["truncated_differently"]` when the two channels did not truncate at the same token count
    (spec §5); the token counts themselves are internal (`_truncation`)
  * with a MULTI-HEAD artifact (a directory written by training/m3_encoder/model.py::export_artifact,
    every file sha256-verified against its sha256.txt): one ContentScore per TRAINED head code and
    channel - the A head on the A1 carrier
    (ADR-005), B1/B2/B3/B5 from the multi-label B head, C1..C5 from the C head - with
    source "m3_encoder@raw" / "@normalized". Untrained heads are never published.

Deliberately does NOT:
  * emit content scores from the frozen binary checkpoint: OFF is not "profanity present"
    (owner decision 2026-09-15); content appears only from a multi-head artifact's trained heads
  * read `ctx.charsafe_text`: BERTurk is cased and m0 lowercases; the binary threshold was fitted
    on scores of the original text, so the raw channel is the original text (OPEN_QUESTIONS Q3 is
    the owner's; this module keeps the fitted behaviour)
  * calibrate, threshold or fuse anything (spec §3, §6); the two channels are reported separately
  * publish embeddings or hidden states (ADR-003)
  * touch the network: every file is local and verified by sha256 before use; a missing or
    different file fails the module closed

Inference on the frozen checkpoint reproduces the study exactly (diagnosis/src/models.py `encode`
and `predict`, copied, not imported): max_len 128, first tokens kept, no padding for a single
post, eval mode, FP32 on CPU, softmax index 1 = OFF.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

from contracts.codes import ContentCode, ModuleName
from contracts.module_api import NORMALIZED, RAW, BaseModule, Context, ModuleOutput
from contracts.schema import ContentScore

ARTIFACTS = Path(__file__).resolve().parents[2] / "artifacts" / "m3_encoder"
# The artifact the runtime deploys (owner decision 2026-09-19); decision/thresholds.yaml holds ITS
# binary_offensive threshold (protocols/threshold_derivation_binary_offensive_stage1_rule_v4.md).
DEPLOYED_ID = "m3-berturk-multihead-a-rule-v4-20260918-163728"
DEPLOYED_WEIGHTS_SHA256 = "dc7fe3062b33938ccbb78b632947bf254ad72e60104e163c64830bb95f0d0b76"
DEPLOYED_DIR = ARTIFACTS / DEPLOYED_ID
ARTIFACT_ID = DEPLOYED_ID
# Weights every multi-head artifact must carry under its id, wherever it is loaded from.
PINNED_WEIGHTS = {DEPLOYED_ID: DEPLOYED_WEIGHTS_SHA256}
# The frozen epoch-1 binary checkpoint: loaded only when NSOSYAL_M3_ARTIFACT names it.
BASELINE_ID = "m3-berturk-pytorch-fp32-epoch1"
# Environment overrides, so a Colab or demo machine can point at Drive or another disk.
CHECKPOINT_ENV = "NSOSYAL_M3_CHECKPOINT"
TOKENIZER_ENV = "NSOSYAL_M3_TOKENIZER"
# A multi-head artifact directory (heads.json + weights.pt + tokenizer files + sha256.txt), or BASELINE_ID.
MULTIHEAD_ENV = "NSOSYAL_M3_ARTIFACT"
DEFAULT_CHECKPOINT = ARTIFACTS / "berturk_epoch1.pt"
DEFAULT_TOKENIZER = ARTIFACTS / "tokenizer"
SOURCE = ModuleName.M3_ENCODER.value

# sha256 of every file loaded (artifacts/MANIFEST.md). The checkpoint is the phase-01 best.pt
# (epoch 1), recorded in diagnosis/docs/RESULTS_LOG.md.
CHECKPOINT_SHA256 = "43a20d5525aff0a57c0bda2be559a5acdf84848cf7cbed844f0c8f5f3024d4ca"
TOKENIZER_SHA256 = {
    "config.json": "980b01ddb94ee8cc2533e064bdca97584b96bbf9755601217ae3d13460c58f48",
    "tokenizer.json": "d424e0bceb7f017dfced77157d14647505b28b41bfc8d9bffd5631f1b1fe61e5",
    "tokenizer_config.json": "d50873edfa649e9950fbfb196da01d0b2b4470a25e2ac711cf5c7022761b0a04",
}

# The study's truncation policy (m3 spec.md §5): 128 tokens, first tokens kept.
MAX_LEN = 128
OFF_INDEX = 1  # id2label {0: NOT, 1: OFF}
# Head layout of a multi-head artifact (training/m3_encoder/model.py): code lists per head.
HEAD_CODES = {"a": ("A1",), "b": ("B1", "B2", "B3", "B5"), "c": ("C1", "C2", "C3", "C4", "C5")}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def artifact_paths() -> tuple[Path, Path]:
    return (Path(os.environ.get(CHECKPOINT_ENV, DEFAULT_CHECKPOINT)),
            Path(os.environ.get(TOKENIZER_ENV, DEFAULT_TOKENIZER)))


def multihead_dir() -> Path | None:
    """The multi-head artifact directory the runtime will load, or None for the explicit baseline."""
    value = os.environ.get(MULTIHEAD_ENV)
    if value == BASELINE_ID:
        return None
    return Path(value) if value else DEPLOYED_DIR


class EncoderModule(BaseModule):
    name = ModuleName.M3_ENCODER
    version = "0.3.0"
    provides = frozenset({"content"})
    # ADR-001 runtime enforcement: whether content scores / guards carry spans.
    # encoder heads score the whole post, not a substring.
    emits_spans = False

    # -- load ------------------------------------------------------------------------------
    def _load(self) -> None:
        import torch

        self._torch = torch
        self._heads: dict[str, Any] | None = None       # multi-head artifact layout, or None (binary only)
        target = multihead_dir()
        if target is None:
            self._load_binary()
        else:
            self._load_multihead(target, deployed=not os.environ.get(MULTIHEAD_ENV))

    def _load_binary(self) -> None:
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
        from transformers import AutoConfig, AutoModelForSequenceClassification, AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(tokenizer_dir, local_files_only=True)
        config = AutoConfig.from_pretrained(tokenizer_dir, local_files_only=True)
        model = AutoModelForSequenceClassification.from_config(config)
        state = self._torch.load(checkpoint, map_location="cpu", weights_only=True)
        model.load_state_dict(state["model"], strict=True)
        self._model = model.float().to("cpu").eval()
        self._artifact_id = BASELINE_ID

    def _load_multihead(self, directory: Path, deployed: bool) -> None:
        """A class-free artifact: AutoModel encoder weights + head tensors + heads.json, every file
        listed in sha256.txt verified before use (spec §8); a pinned id must carry its pinned weights."""
        digests_file = directory / "sha256.txt"
        if not digests_file.is_file():
            where = (f"deployed artifact {DEPLOYED_ID} not installed at {directory} (copy it from Drive, "
                     f"artifacts/MANIFEST.md); no fallback to another artifact" if deployed
                     else f"{MULTIHEAD_ENV}={directory}")
            raise FileNotFoundError(f"{where}: no sha256.txt; refusing an unverifiable artifact")
        wrong, missing, digests = [], [], {}
        for line in digests_file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            want, name = line.split(None, 1)
            name = name.strip()
            path = directory / name
            if not path.is_file():
                missing.append(name)
                continue
            digests[name] = sha256(path)
            if digests[name] != want:
                wrong.append(name)
        if missing or wrong:
            raise ValueError(f"multi-head artifact {directory}: missing {missing}, sha256 mismatch {wrong}")
        if "weights.pt" not in digests or "heads.json" not in digests:
            raise ValueError(f"multi-head artifact {directory}: sha256.txt does not cover weights.pt and heads.json")
        from transformers import AutoConfig, AutoModel, AutoTokenizer

        heads = json.loads((directory / "heads.json").read_text(encoding="utf-8"))
        artifact_id = str(heads.get("artifact_id"))
        if deployed and artifact_id != DEPLOYED_ID:
            raise ValueError(f"{directory} holds {artifact_id!r}, not the deployed {DEPLOYED_ID}; refusing it")
        pinned = PINNED_WEIGHTS.get(artifact_id)
        if pinned is not None and digests["weights.pt"] != pinned:
            raise ValueError(f"{artifact_id}: weights.pt sha256 {digests['weights.pt']} is not the pinned "
                             f"{pinned}; refusing it")
        self._tokenizer = AutoTokenizer.from_pretrained(directory, local_files_only=True)
        config = AutoConfig.from_pretrained(directory, local_files_only=True)
        encoder = AutoModel.from_config(config)
        state = self._torch.load(directory / "weights.pt", map_location="cpu", weights_only=True)
        encoder.load_state_dict(state["encoder"], strict=True)
        self._model = encoder.float().to("cpu").eval()
        self._head_tensors = {name: (t["weight"].float(), t["bias"].float()) for name, t in state["heads"].items()}
        self._heads = heads
        self._artifact_id = artifact_id

    # -- scoring ---------------------------------------------------------------------------
    def _token_count(self, text: str) -> int:
        return len(self._tokenizer(text, add_special_tokens=True, verbose=False)["input_ids"])

    def _score(self, text: str) -> dict[str, Any]:
        """Per-head probabilities for one text: {"binary": p_off, "a": [p], "b": [...], "c": [...]}
        (only "binary" for the frozen checkpoint)."""
        torch = self._torch
        encoded = self._tokenizer([text], truncation=True, max_length=MAX_LEN, padding=False, return_tensors="pt")
        with torch.no_grad():
            if self._heads is None:
                logits = self._model(**encoded).logits.float()
                return {"binary": float(torch.softmax(logits, dim=-1)[0, OFF_INDEX])}
            out = self._model(**encoded)
            pooled = out.pooler_output if getattr(out, "pooler_output", None) is not None else out.last_hidden_state[:, 0]
            probs: dict[str, Any] = {}
            for name, (weight, bias) in self._head_tensors.items():
                logits = torch.nn.functional.linear(pooled.float(), weight, bias)
                if name in ("binary", "c"):
                    values = torch.softmax(logits, dim=-1)[0]
                    probs[name] = float(values[int(self._heads.get("off_index", OFF_INDEX))]) if name == "binary" else values.tolist()
                else:
                    probs[name] = torch.sigmoid(logits)[0].tolist()
            return probs

    def _head_content(self, channel: str, probs: dict[str, Any]) -> list[ContentScore]:
        """Content scores from TRAINED heads only (heads.json `trained` flags)."""
        if self._heads is None:
            return []
        scores: list[ContentScore] = []
        for head, codes in HEAD_CODES.items():
            layout = self._heads["heads"].get(head, {})
            if not layout.get("trained") or head not in probs:
                continue
            for code, p in zip(codes, probs[head]):        # the C head's extra NONE class is not a code
                scores.append(ContentScore(code=ContentCode(code), score=float(p), source=f"{SOURCE}@{channel}"))
        return scores

    # -- run -------------------------------------------------------------------------------
    def _run(self, ctx: Context) -> ModuleOutput:
        notes: list[str] = []
        texts = {RAW: ctx.text}
        if ctx.normalized_text is not None:
            texts[NORMALIZED] = ctx.normalized_text
        counts = {channel: self._token_count(text) for channel, text in texts.items()}
        for channel, n in counts.items():
            if n > MAX_LEN:
                notes.append(f"truncated ({channel}): {n} tokens, scored the first {MAX_LEN}")
        probs = {RAW: self._score(ctx.text)}
        if NORMALIZED in texts:
            # Identical text scores identically: reuse rather than pay a second encoder pass.
            probs[NORMALIZED] = probs[RAW] if texts[NORMALIZED] == ctx.text else self._score(texts[NORMALIZED])
        content = [s for channel in probs for s in self._head_content(channel, probs[channel])]
        signals: dict[str, Any] = {"raw_score": probs[RAW]["binary"], "artifact": self._artifact_id,
                                   "truncated_differently": (NORMALIZED in counts and
                                                             (counts[RAW] > MAX_LEN) != (counts[NORMALIZED] > MAX_LEN)),
                                   "_truncation": counts}
        if NORMALIZED in probs:
            signals["norm_score"] = probs[NORMALIZED]["binary"]
        return ModuleOutput(content=content, signals=signals, notes=notes)
