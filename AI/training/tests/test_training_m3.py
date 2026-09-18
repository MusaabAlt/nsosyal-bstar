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
        # The HYBRID A-head path in miniature (owner decision 2026-09-18): pseudo-labels in the
        # derived-file format (`a_label`) on TRAIN rows so the A head counts as TRAINED, pseudo-labels
        # on a few DEV rows (agreement only), and a HUMAN oracle jsonl on DEV rows (the metric).
        # The label VALUES here are arbitrary code-path fodder (OFF/NOT), never a claim about profanity.
        from training.m3_encoder import data as D
        train_rows, dev_rows, _ = D.load_frozen_split()
        cls.train_ids, cls.dev_ids = [r["id"] for r in train_rows], [r["id"] for r in dev_rows]
        cls.pseudo_train = Path(cls.tmp.name) / "m1_lexicon_train_seed42.json"
        cls.pseudo_train.write_text(json.dumps({"rows": [
            {"row_id": r["id"], "lexicon_hit": True, "a_label": int(r["label"] == "OFF")} for r in train_rows[:64]]}),
            encoding="utf-8")
        cls.pseudo_dev = Path(cls.tmp.name) / "a_dev_pseudo.jsonl"
        cls.pseudo_dev.write_text("".join(json.dumps({"row_id": r["id"], "label": int(r["label"] == "OFF")}) + "\n"
                                          for r in dev_rows[:8]), encoding="utf-8")
        cls.human_dev = Path(cls.tmp.name) / "a_dev_human.jsonl"
        cls.human_dev.write_text("".join(json.dumps({"row_id": r["id"], "label": int(r["label"] == "OFF")}) + "\n"
                                         for r in dev_rows[4:12]), encoding="utf-8")
        rc = T.main(["--out", str(out), "--smoke", "16", "--base", str(TOKENIZER_DIR),
                     "--labels-a", str(cls.pseudo_train), "--labels-a", str(cls.pseudo_dev),
                     "--labels-a-human", str(cls.human_dev), "--batch-size", "8", "--eval-batch-size", "8"])
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

    def test_human_oracle_and_pseudo_label_agreement_are_reported_apart(self) -> None:
        """HYBRID strategy: `a` is the human oracle (the only quality claim); pseudo-label agreement
        sits under its own key with a note saying it is not accuracy; the artifact records where
        every A label came from."""
        report = json.loads((self.artifact / "dev_eval.json").read_text(encoding="utf-8"))
        self.assertEqual(report["a"]["oracle"], "human")
        self.assertEqual(report["a"]["labelled_rows"], 8)
        self.assertTrue(report["a"]["A1"]["insufficient_sample"])          # 8 rows < 20 positives
        self.assertEqual(report["a_pseudo_label_agreement"]["labelled_rows"], 8)
        self.assertIn("NOT accuracy", report["a_pseudo_label_agreement"]["note"])
        self.assertEqual(report["label_coverage"]["train"]["a"], 64)
        self.assertEqual(report["label_coverage"]["train"]["a_human"], 0)
        self.assertEqual(report["label_coverage"]["dev"]["a_human"], 8)
        heads = json.loads((self.artifact / "heads.json").read_text(encoding="utf-8"))
        kinds = [s["kind"] for s in heads["label_sources"]["a"]]
        self.assertEqual(kinds, ["derived-pseudo-label", "jsonl"])
        self.assertEqual([s["file"] for s in heads["label_sources"]["a_human"]], ["a_dev_human.jsonl"])
        self.assertTrue(all(len(s["sha256"]) == 64 for s in heads["label_sources"]["a"]))
        self.assertIn("a_head_supervision", heads)

    def test_a_non_human_reference_must_state_its_provenance(self) -> None:
        """An AI-annotated, human-adjudicated reference is never stamped `oracle: human`: it goes in
        through --labels-a-reference, which refuses to run without its kind. (A handful of rows:
        evaluating the whole dev split on CPU is not a unit test.)"""
        import argparse
        from training.m3_encoder import data as D, evaluate as E

        def resolve(**kw):
            ns = argparse.Namespace(labels_a_human=None, labels_a_reference=None, labels_a_reference_kind=None)
            ns.__dict__.update(kw)
            return E.resolve_a_reference(argparse.ArgumentParser(), ns)

        self.assertEqual(resolve(labels_a_human=self.human_dev), (self.human_dev, "human"))
        self.assertEqual(resolve(labels_a_reference=self.human_dev,
                                 labels_a_reference_kind="ai-assisted-human-adjudicated"),
                         (self.human_dev, "ai-assisted-human-adjudicated"))
        self.assertEqual(resolve(), (None, "human"))
        for bad in ({"labels_a_reference": self.human_dev},                                          # kind missing
                    {"labels_a_reference_kind": "ai-assisted-human-adjudicated"},                   # file missing
                    {"labels_a_reference": self.human_dev, "labels_a_human": self.human_dev,
                     "labels_a_reference_kind": "ai-assisted-human-adjudicated"}):                  # both given
            with self.assertRaises(SystemExit):
                resolve(**bad)

        split = D.build_split(labels_a_human=self.human_dev)
        rows = [r for r in split.dev if r.a_human != D.MISSING]
        model, tokenizer, _ = E.load_exported(self.artifact)
        report = E.evaluate_rows(model, tokenizer, rows, 128, 8, "cpu", n_boot=20,
                                 oracle_kind="ai-assisted-human-adjudicated")
        self.assertEqual(report["a"]["oracle"], "ai-assisted-human-adjudicated")
        self.assertEqual(report["a"]["labelled_rows"], 8)
        with self.assertRaises(ValueError):
            E.evaluate_rows(model, tokenizer, rows, 128, 8, "cpu", n_boot=5, oracle_kind="two-human")

    def test_a_label_loading_rules(self) -> None:
        from training.m3_encoder import data as D

        derived = Path(self.tmp.name) / "derived.json"
        derived.write_text(json.dumps({"rows": [{"row_id": "1", "lexicon_hit": True, "a_label": 0},
                                                {"row_id": "2", "lexicon_hit": False}]}), encoding="utf-8")
        self.assertEqual(D.load_a_labels(derived), {"1": 0, "2": 0})     # a_label wins; pre-2.0 fallback
        masked = Path(self.tmp.name) / "masked.json"
        masked.write_text(json.dumps({"rows": [{"row_id": "1", "lexicon_hit": True, "a_label": None},
                                               {"row_id": "2", "lexicon_hit": True, "a_label": 1}]}), encoding="utf-8")
        self.assertEqual(D.load_a_labels(masked), {"2": 1})              # rule v2: null = no supervision, not 0
        conflict = Path(self.tmp.name) / "conflict.jsonl"
        conflict.write_text(json.dumps({"row_id": "1", "label": 1}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "conflicting"):
            D.load_a_label_files([derived, conflict])
        bad = Path(self.tmp.name) / "bad.jsonl"
        bad.write_text(json.dumps({"row_id": "1", "label": 2}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "not 0/1"):
            D.load_a_labels(bad)

    def test_human_labels_on_train_rows_are_refused(self) -> None:
        from training.m3_encoder import data as D

        on_train = Path(self.tmp.name) / "human_on_train.jsonl"
        on_train.write_text(json.dumps({"row_id": self.train_ids[0], "label": 1}) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "TRAIN rows"):
            D.build_split(labels_a_human=on_train)


if __name__ == "__main__":
    unittest.main()
