"""training/m3_encoder smoke test on CPU, and the multi-head artifact path of modules/m3_encoder.

Trains a RANDOMLY initialised encoder (built from the local BERTurk config, no weights, no
network) on a handful of frozen-split rows for two steps, exports the class-free artifact, then
loads it through EncoderModule with NSOSYAL_M3_ARTIFACT and checks: sha256 verification, the
binary score per channel, content scores only for TRAINED heads, and fail-closed on a tampered
file. The artifact is a `smoke-` artifact and proves the code path only; it never scores anything
for real (docs/training/m3_encoder.md).

Preconditions are machine data, not module behaviour, so they SKIP with a reason (unlike the
module suites, which fail): the corpus under diagnosis/data and the m3 tokenizer directory.
"""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from contracts.codes import ContentCode
from contracts.module_api import Context

AI_ROOT = Path(__file__).resolve().parents[2]
TOKENIZER_DIR = AI_ROOT / "artifacts" / "m3_encoder" / "tokenizer"
CORPUS = AI_ROOT.parent / "diagnosis" / "data" / "coltekin" / "offenseval-tr-training-v1.tsv"


def can_run() -> bool:
    try:
        import torch  # noqa: F401
        import transformers  # noqa: F401
    except ImportError:
        return False
    return TOKENIZER_DIR.is_dir() and CORPUS.is_file()


@unittest.skipUnless(can_run(), "training smoke test needs torch/transformers, the m3 tokenizer dir and the local corpus")
class TrainingSmokeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from training.m3_encoder import train as T

        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name) / "run"
        # A labels for a few rows so the A head counts as TRAINED; B and C stay untrained.
        from training.m3_encoder import data as D
        train_rows, _, _ = D.load_frozen_split()
        labels = Path(cls.tmp.name) / "a.jsonl"
        with open(labels, "w", encoding="utf-8") as fh:
            for r in train_rows[:64]:
                fh.write(json.dumps({"row_id": r["id"], "label": int(r["label"] == "OFF")}) + "\n")
        rc = T.main(["--out", str(out), "--smoke", "16", "--base", str(TOKENIZER_DIR), "--labels-a", str(labels),
                     "--batch-size", "8", "--eval-batch-size", "8"])
        assert rc == 0
        cls.artifact = next((out / "artifact").iterdir())

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def test_export_is_complete_and_self_describing(self) -> None:
        names = {p.name for p in self.artifact.iterdir()}
        self.assertTrue({"weights.pt", "heads.json", "config.json", "tokenizer.json", "sha256.txt", "dev_eval.json",
                         "MANIFEST_ROW.md"} <= names, names)
        heads = json.loads((self.artifact / "heads.json").read_text(encoding="utf-8"))
        self.assertTrue(heads["artifact_id"].startswith("smoke-"))
        self.assertTrue(heads["smoke"] and heads["random_init"])
        self.assertEqual({k: v["trained"] for k, v in heads["heads"].items()},
                         {"binary": True, "a": True, "b": False, "c": False})
        self.assertEqual(heads["heads"]["b"]["labels"], ["B1", "B2", "B3", "B5"])
        self.assertEqual(heads["heads"]["c"]["labels"], ["C1", "C2", "C3", "C4", "C5", "NONE"])

    def test_module_loads_the_artifact_and_publishes_trained_heads_only(self) -> None:
        from modules.m3_encoder.module import EncoderModule

        with mock.patch.dict(os.environ, {"NSOSYAL_M3_ARTIFACT": str(self.artifact)}):
            module = EncoderModule()
            out = module.process(Context(text="Sen çok aptal birisin.", normalized_text="sen cok aptal birisin."))
        self.assertTrue(out.ok, out.notes)
        self.assertTrue(out.signals["artifact"].startswith("smoke-"))
        for key in ("raw_score", "norm_score"):
            self.assertTrue(0.0 <= out.signals[key] <= 1.0)
        sources = {(s.code, s.source) for s in out.content}
        self.assertEqual(sources, {(ContentCode.A1, "m3_encoder@raw"), (ContentCode.A1, "m3_encoder@normalized")})
        self.assertTrue(all(s.threshold is None and s.fired is None for s in out.content))

    def test_tampered_artifact_fails_closed(self) -> None:
        from modules.m3_encoder.module import EncoderModule

        tampered = Path(self.tmp.name) / "tampered"
        import shutil
        shutil.copytree(self.artifact, tampered)
        (tampered / "heads.json").write_text("{}", encoding="utf-8")
        with mock.patch.dict(os.environ, {"NSOSYAL_M3_ARTIFACT": str(tampered)}):
            out = EncoderModule().process(Context(text="x"))
        self.assertFalse(out.ok)
        self.assertIn("sha256 mismatch", out.notes[0])
        self.assertEqual(out.signals, {})

    def test_evaluate_loads_the_exported_artifact_without_the_training_class(self) -> None:
        from training.m3_encoder import evaluate as E

        model, tokenizer, heads = E.load_exported(self.artifact)
        self.assertEqual(heads["artifact_id"], json.loads((self.artifact / "heads.json").read_text(encoding="utf-8"))["artifact_id"])
        report = json.loads((self.artifact / "dev_eval.json").read_text(encoding="utf-8"))
        self.assertIn("macro_f1", report["binary"])
        self.assertEqual(report["b"]["labelled_rows"], 0)


if __name__ == "__main__":
    unittest.main()
