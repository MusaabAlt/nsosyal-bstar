"""Unit tests for m3_encoder: contract tests and behaviour tests of the baseline wrapper.

Tests that run the model need the git-ignored artifact files (artifacts/MANIFEST.md)
and torch/transformers; without them they are skipped with the reason, and the
fail-closed test still runs."""
from __future__ import annotations

import copy
import os
import socket
import unittest
from types import MappingProxyType
from unittest import mock

from contracts.codes import ModuleName
from contracts.module_api import PROVIDABLE_FIELDS, Context, ModuleOutput
from contracts.schema import ContentScore, GuardResult
from modules.m3_encoder.module import (ARTIFACT_ID, CHECKPOINT_ENV, MAX_LEN, TOKENIZER_ENV, EncoderModule,
                                       artifact_paths)


def artifact_available() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    checkpoint, tokenizer_dir = artifact_paths()
    return checkpoint.is_file() and tokenizer_dir.is_dir()


NEEDS_ARTIFACT = unittest.skipUnless(artifact_available(), "m3 artifact files or torch/transformers not installed")
SHARED: dict[str, EncoderModule] = {}


def shared_module() -> EncoderModule:
    """One loaded model for the whole file: loading hashes 440 MB and builds BERT."""
    if "module" not in SHARED:
        SHARED["module"] = EncoderModule()
    return SHARED["module"]


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
        with mock.patch.dict(os.environ, {CHECKPOINT_ENV: "does-not-exist.pt", TOKENIZER_ENV: "does-not-exist"}):
            out = EncoderModule().process(Context(text="Bu bir test cumlesi"))
        self.assertFalse(out.ok)
        self.assertIn("missing", out.notes[0])
        self.assertEqual(out.signals, {})

    @NEEDS_ARTIFACT
    def test_no_network_at_load(self) -> None:
        def refuse(*args, **kwargs):
            raise OSError("network access attempted during m3 load")
        with mock.patch.object(socket.socket, "connect", refuse):
            out = EncoderModule().process(Context(text="Bu bir test cumlesi"))
        self.assertTrue(out.ok, out.notes)

    @NEEDS_ARTIFACT
    def test_publishes_raw_score_and_artifact_only(self) -> None:
        out = self.score(text="Sen çok aptal birisin.", normalized_text="sen cok aptal birisin.")
        self.assertEqual(set(out.signals), {"raw_score", "artifact"})
        self.assertEqual(out.signals["artifact"], ARTIFACT_ID)
        self.assertIsInstance(out.signals["raw_score"], float)
        self.assertTrue(0 <= out.signals["raw_score"] <= 1)
        self.assertEqual(out.content, [])

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
