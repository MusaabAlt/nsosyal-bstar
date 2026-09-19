"""Unit tests for m3_encoder: contract tests, behaviour tests of the DEPLOYED artifact (rule-v4
multi-head: binary + A heads; B and C not trained) and of the explicitly selected binary baseline.

Tests that run a model need its git-ignored files (artifacts/MANIFEST.md) and torch/transformers;
without them they are skipped with the reason here, and tests/test_implementation_status.py FAILS
the suite with a named precondition, so a skip can never pass for green. The fail-closed tests
always run."""
from __future__ import annotations

import copy
import json
import os
import socket
import tempfile
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest import mock

from contracts.codes import ContentCode, ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m3_encoder import module as m3
from modules.m3_encoder.module import (ARTIFACT_ID, BASELINE_ID, CHECKPOINT_ENV, DEPLOYED_DIR, DEPLOYED_ID,
                                       DEPLOYED_WEIGHTS_SHA256, MAX_LEN, MULTIHEAD_ENV, TOKENIZER_ENV,
                                       EncoderModule, artifact_paths)


def _torch() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return True


def artifact_available() -> bool:
    """The DEPLOYED artifact (what the runtime loads by default) and torch/transformers are present."""
    return _torch() and all((DEPLOYED_DIR / n).is_file() for n in ("sha256.txt", "weights.pt", "heads.json"))


def baseline_available() -> bool:
    checkpoint, tokenizer_dir = artifact_paths()
    return _torch() and checkpoint.is_file() and tokenizer_dir.is_dir()


NEEDS_ARTIFACT = unittest.skipUnless(artifact_available(), f"deployed m3 artifact {DEPLOYED_ID} or torch missing")
NEEDS_BASELINE = unittest.skipUnless(baseline_available(), f"m3 baseline {BASELINE_ID} files or torch missing")
SHARED: dict[str, EncoderModule] = {}


def shared_module() -> EncoderModule:
    """One loaded model for the whole file: loading hashes 440 MB and builds BERT."""
    if "module" not in SHARED:
        SHARED["module"] = EncoderModule()
    return SHARED["module"]


def baseline_module() -> EncoderModule:
    """The frozen binary checkpoint, selected explicitly (it is never a fallback)."""
    if "baseline" not in SHARED:
        module = EncoderModule()
        with mock.patch.dict(os.environ, {MULTIHEAD_ENV: BASELINE_ID}):
            module.load()
        SHARED["baseline"] = module
    return SHARED["baseline"]


class EncoderModuleContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = shared_module()

    def test_name_matches_folder(self) -> None:
        self.assertIs(self.module.name, ModuleName("m3_encoder"))

    def test_provides_are_contract_fields(self) -> None:
        self.assertTrue(self.module.provides)
        self.assertLessEqual(set(self.module.provides), PROVIDABLE_FIELDS)

    @NEEDS_ARTIFACT
    def test_process_returns_ok_module_output(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.module, "m3_encoder")

    def test_output_stays_within_provides(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))

    def test_never_sets_decision_fields(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        for score in out.content:
            self.assertIsNone(score.threshold)
            self.assertIsNone(score.fired)
        for guard in out.guards:
            self.assertIsNone(guard.active)

    # -- baseline: contract shape / input not mutated / never raises --------------
    HOSTILE_INPUTS = ("", " ", "\t\n ", "a" * 5000, "Bu bir test cumlesi", "SIKINTI",
                      "ap​tal", "аptal", "\U0001F468‍\U0001F469", "\x00\x1b")

    def test_contract_shape(self) -> None:
        out = self.module.process(Context(text="Bu bir test cumlesi"))
        self.assertIsInstance(out, ModuleOutput)
        self.assertEqual(out.module, self.module.name.value)
        self.assertEqual(out.version, self.module.version)
        self.assertIsInstance(out.latency_ms, float)
        self.assertIsInstance(out.signals, dict)
        self.assertIsInstance(out.notes, list)
        self.assertLessEqual(out.populated_fields(), set(self.module.provides))
        for score in out.content:
            self.assertIsInstance(score, ContentScore)
            self.assertIsNone(score.threshold)
            self.assertIsNone(score.fired)
        for guard in out.guards:
            self.assertIsInstance(guard, GuardResult)
            self.assertIsNone(guard.threshold)
            self.assertIsNone(guard.active)
            self.assertEqual(guard.suppressed, [])

    def test_input_not_mutated(self) -> None:
        upstream = {"m0_charsafe": {"offsets": [0, 1, 2], "invisible_removed": 0}}
        snapshot = copy.deepcopy(upstream)
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                ctx = Context(text=text, charsafe_text=text.lower(), normalized_text=text,
                              signals=MappingProxyType(upstream))
                self.module.process(ctx)
                self.assertEqual(ctx.text, text)
                self.assertEqual(ctx.charsafe_text, text.lower())
                self.assertEqual(ctx.normalized_text, text)
        self.assertEqual(upstream, snapshot)

    @NEEDS_ARTIFACT
    def test_never_raises(self) -> None:
        for text in self.HOSTILE_INPUTS:
            with self.subTest(text=text[:20]):
                out = self.module.process(Context(text=text))
                self.assertIsInstance(out, ModuleOutput)
                self.assertTrue(out.ok, out.notes)


class EncoderModuleBehaviourTest(unittest.TestCase):
    def setUp(self) -> None:
        self.module = shared_module()

    def score(self, **kwargs) -> ModuleOutput:
        out = self.module.process(Context(**kwargs))
        self.assertTrue(out.ok, out.notes)
        return out

    def test_missing_artifact_fails_closed(self) -> None:
        with mock.patch.dict(os.environ, {MULTIHEAD_ENV: BASELINE_ID, CHECKPOINT_ENV: "does-not-exist.pt",
                                          TOKENIZER_ENV: "does-not-exist"}):
            out = EncoderModule().process(Context(text="Bu bir test cumlesi"))
        self.assertFalse(out.ok)
        self.assertIn("missing", out.notes[0])
        self.assertEqual(out.signals, {})

    def test_missing_deployed_artifact_fails_closed_without_fallback(self) -> None:
        # The runtime never substitutes another artifact for the deployed one (owner decision 2026-09-19).
        with tempfile.TemporaryDirectory() as empty, mock.patch.object(m3, "DEPLOYED_DIR", Path(empty)), \
                mock.patch.dict(os.environ, {MULTIHEAD_ENV: ""}):
            out = EncoderModule().process(Context(text="Bu bir test cumlesi"))
        self.assertFalse(out.ok)
        self.assertIn(f"deployed artifact {DEPLOYED_ID} not installed", out.notes[0])
        self.assertIn("no fallback to another artifact", out.notes[0])
        self.assertEqual(out.signals, {})

    @NEEDS_ARTIFACT
    def test_no_network_at_load(self) -> None:
        def refuse(*args, **kwargs):
            raise OSError("network access attempted during m3 load")
        with mock.patch.object(socket.socket, "connect", refuse):
            out = EncoderModule().process(Context(text="Bu bir test cumlesi"))
        self.assertTrue(out.ok, out.notes)

    @NEEDS_ARTIFACT
    def test_publishes_a_score_per_channel_the_artifact_and_the_trained_a_head(self) -> None:
        # spec §4: raw_score on ctx.text, norm_score on ctx.normalized_text, both reported, never fused.
        # The deployed rule-v4 artifact trained its binary and A heads only: A1 (the family-A carrier,
        # ADR-005) per channel, and no B or C code - those heads are not trained and never published.
        out = self.score(text="Sen çok aptal birisin.", normalized_text="sen cok aptal birisin.")
        self.assertEqual(set(out.signals), {"raw_score", "norm_score", "artifact", "truncated_differently", "_truncation"})
        self.assertEqual(out.signals["artifact"], DEPLOYED_ID)
        self.assertEqual(ARTIFACT_ID, DEPLOYED_ID)
        for key in ("raw_score", "norm_score"):
            self.assertIsInstance(out.signals[key], float)
            self.assertTrue(0 <= out.signals[key] <= 1)
        self.assertNotEqual(out.signals["raw_score"], out.signals["norm_score"])   # different text, own pass
        self.assertEqual(sorted((s.code, s.source) for s in out.content),
                         [(ContentCode.A1, "m3_encoder@normalized"), (ContentCode.A1, "m3_encoder@raw")])
        for score in out.content:
            self.assertTrue(0 <= score.score <= 1)
            self.assertIsNone(score.span)
        self.assertFalse(out.signals["truncated_differently"])

    @NEEDS_BASELINE
    def test_explicit_baseline_publishes_scores_and_no_content(self) -> None:
        # The frozen binary checkpoint publishes no content (OFF is not "profanity present").
        out = baseline_module().process(Context(text="Sen çok aptal birisin.", normalized_text="sen cok aptal birisin."))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.signals["artifact"], BASELINE_ID)
        self.assertEqual(out.content, [])

    @NEEDS_ARTIFACT
    def test_no_normalized_channel_means_no_norm_score(self) -> None:
        out = self.score(text="Sen çok aptal birisin.")
        self.assertEqual(set(out.signals), {"raw_score", "artifact", "truncated_differently", "_truncation"})
        same = self.score(text="Sen çok aptal birisin.", normalized_text="Sen çok aptal birisin.")
        self.assertEqual(same.signals["norm_score"], same.signals["raw_score"])   # identical text, one pass

    @NEEDS_ARTIFACT
    def test_norm_score_is_the_score_of_the_normalized_text(self) -> None:
        normalized = "sen cok aptal birisin."
        direct = self.score(text=normalized).signals["raw_score"]
        via_channel = self.score(text="Sen ÇOK 4ptal birisin.", normalized_text=normalized).signals["norm_score"]
        self.assertEqual(direct, via_channel)

    @NEEDS_ARTIFACT
    def test_public_signals_are_fixed_size(self) -> None:
        # decision #21: token counts live under the internal "_truncation" key only.
        short = self.score(text="Bugün hava çok güzel").signals
        long = self.score(text="Bugün hava çok güzel " * 100).signals
        public = lambda s: {k: type(v) for k, v in s.items() if not k.startswith("_")}
        self.assertEqual(public(short), public(long))

    @NEEDS_ARTIFACT
    def test_channels_truncating_differently_is_flagged(self) -> None:
        long_text = " ".join(f"kelime{i}" for i in range(MAX_LEN * 2))
        out = self.score(text=long_text, normalized_text="kısa metin")
        self.assertTrue(out.signals["truncated_differently"])
        self.assertTrue(any(n.startswith("truncated (raw)") for n in out.notes))

    @NEEDS_ARTIFACT
    def test_scores_original_text_not_charsafe_or_normalized(self) -> None:
        text = "Sen ÇOK Aptal Birisin."
        plain = self.score(text=text).signals["raw_score"]
        with_channels = self.score(text=text, charsafe_text=text.lower(), normalized_text="xxx").signals["raw_score"]
        self.assertEqual(plain, with_channels)

    @NEEDS_ARTIFACT
    def test_truncation_is_noted(self) -> None:
        long_text = " ".join(f"kelime{i}" for i in range(MAX_LEN * 2))
        self.assertTrue(any(n.startswith("truncated") for n in self.score(text=long_text).notes))
        self.assertEqual(self.score(text="Bugün hava çok güzel").notes, [])

    @NEEDS_ARTIFACT
    def test_deterministic(self) -> None:
        text = "Bugün hava çok güzel, parkta yürüyüş yaptık."
        self.assertEqual(self.score(text=text).signals["raw_score"], self.score(text=text).signals["raw_score"])


if __name__ == "__main__":
    unittest.main()


class DeployedArtifactTest(unittest.TestCase):
    """The deployed artifact is exactly rule-v4 (owner decision 2026-09-19): pinned weights, trained
    binary and A heads, untrained B and C heads that are never published."""

    @NEEDS_ARTIFACT
    def test_the_installed_files_are_the_pinned_rule_v4_artifact(self) -> None:
        digests = dict(reversed(line.split(None, 1)) for line in
                       (DEPLOYED_DIR / "sha256.txt").read_text(encoding="utf-8").splitlines() if line.strip())
        self.assertEqual(digests["weights.pt"], DEPLOYED_WEIGHTS_SHA256)
        self.assertEqual(m3.sha256(DEPLOYED_DIR / "weights.pt"), DEPLOYED_WEIGHTS_SHA256)
        heads = json.loads((DEPLOYED_DIR / "heads.json").read_text(encoding="utf-8"))
        self.assertEqual(heads["artifact_id"], DEPLOYED_ID)
        self.assertEqual({name: layout["trained"] for name, layout in heads["heads"].items()},
                         {"binary": True, "a": True, "b": False, "c": False})

    @NEEDS_ARTIFACT
    def test_the_runtime_loads_it_by_default(self) -> None:
        with mock.patch.dict(os.environ, {MULTIHEAD_ENV: ""}):
            out = EncoderModule().process(Context(text="Bugün hava çok güzel"))
        self.assertTrue(out.ok, out.notes)
        self.assertEqual(out.signals["artifact"], DEPLOYED_ID)
        self.assertTrue({s.code for s in out.content} <= {ContentCode.A1})

    @NEEDS_ARTIFACT
    def test_no_b_or_c_code_is_ever_published(self) -> None:
        module = shared_module()
        for text in ("Seni öldüreceğim", "Onlardan başka ne beklenir", "Sen tam bir aptalsın", "Bugün hava çok güzel"):
            with self.subTest(text=text):
                out = module.process(Context(text=text, normalized_text=text.lower()))
                self.assertTrue(out.ok, out.notes)
                self.assertTrue({s.code for s in out.content} <= {ContentCode.A1}, out.content)
