"""eval/a_head_dev_sample.py - the A-head human annotation package on a synthetic corpus/split.

Pins: the draw is deterministic and dev-only; the annotator template reveals row_id and text and
nothing else (no gold, no prediction, no lexicon field); check / adjudicate / export enforce the
guideline's file contract; the exported oracle is exactly what the trainer's loader reads.
No terlik or zeyrek needed: nothing here runs a module.
"""
from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from eval import a_head_dev_sample as S
from eval import m1_lexicon_labels as G
from tests.test_m1_lexicon_labels import SyntheticData


class DevSampleTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.data = SyntheticData(self.root / "data")
        self.spec = self.data.spec("dev")
        self.out = self.root / "annotation"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def draw(self, n: int = 2, seed: int = 42, annotators=("ann1", "ann2")):
        return S.draw(self.spec, n, seed, list(annotators), self.out)

    def test_draw_is_deterministic_dev_only_and_blind(self) -> None:
        ids_file, files = self.draw()
        design = json.loads(ids_file.read_text(encoding="utf-8"))
        dev_ids = {r[0] for r in SyntheticData.DEV}
        self.assertEqual(set(design["ids_in_presentation_order"]), dev_ids)
        self.assertEqual(design["design"], {"population": "frozen dev split, seed 42", "n_population": 2, "n": 2,
                                            "seed": 42, "method": design["design"]["method"], "weights": "none (uniform)"})
        again, _ = S.draw(self.spec, 2, 42, ["ann1", "ann2"], self.root / "again")
        self.assertEqual(json.loads(again.read_text(encoding="utf-8"))["ids_in_presentation_order"],
                         design["ids_in_presentation_order"])
        self.assertEqual(S.draw_ids([str(i) for i in range(100)], 10, 7), S.draw_ids([str(i) for i in range(100)], 10, 7))
        self.assertNotEqual(S.draw_ids([str(i) for i in range(100)], 10, 7), S.draw_ids([str(i) for i in range(100)], 10, 8))
        for path in files:
            self.assertTrue(path.parent.name == "private")
            for row in S._read_jsonl(path):
                self.assertEqual(tuple(row), S.TEMPLATE_FIELDS)
                self.assertIsNone(row["label"])
                self.assertFalse(row["uncertain"])
                self.assertEqual(row["notes"], "")
                self.assertIn(row["row_id"], dev_ids)
        for train_id in (r[0] for r in SyntheticData.TRAIN):
            self.assertNotIn(train_id, design["ids_in_presentation_order"])
        self.assertRegex(design["sampler"]["git_head"], r"^[0-9a-f]{40}$")
        self.assertEqual(design["inputs"]["split"]["sha256"], G.sha256_file(self.data.split))

    def test_draw_refuses_test_set_and_bad_sizes(self) -> None:
        bad = G.Spec(split="dev", corpus=self.data.test_set, corpus_sha256="", split_file=self.data.split,
                     split_sha256=G.sha256_file(self.data.split), frozen_slice=None, expected=self.data.expected)
        with self.assertRaises(G.ProtocolStop):
            S.load_dev(bad)
        with self.assertRaises(S.SampleError):
            S.draw_ids(["1", "2"], 3, 42)

    def fill(self, path: Path, labels: dict[str, int], uncertain: set[str] = frozenset()) -> Path:
        rows = S._read_jsonl(path)
        for row in rows:
            row["label"] = labels[row["row_id"]]
            row["uncertain"] = row["row_id"] in uncertain
            row["notes"] = "x" if row["row_id"] in uncertain else ""
        S._write_jsonl(path, rows)
        return path

    def test_check_accepts_a_complete_file_and_rejects_broken_ones(self) -> None:
        ids_file, (ann1, _) = self.draw()
        with self.assertRaisesRegex(S.SampleError, "label is null"):
            S.check_file(ann1, ids_file)
        self.assertEqual(S.check_file(ann1, ids_file, allow_incomplete=True)["unlabelled"], 2)
        self.fill(ann1, {"7": 1, "8": 0}, uncertain={"8"})
        self.assertEqual(S.check_file(ann1, ids_file), {"n": 2, "labelled": 2, "unlabelled": 0, "positives": 1,
                                                          "negatives": 1, "uncertain": 1})
        rows = S._read_jsonl(ann1)
        rows[0]["label"] = 2
        S._write_jsonl(ann1, rows)
        with self.assertRaisesRegex(S.SampleError, "not 0/1"):
            S.check_file(ann1, ids_file)
        rows[0]["label"] = True
        S._write_jsonl(ann1, rows)
        with self.assertRaisesRegex(S.SampleError, "not 0/1"):
            S.check_file(ann1, ids_file)
        rows[0]["label"] = 1
        S._write_jsonl(ann1, rows[:1])
        with self.assertRaisesRegex(S.SampleError, "ids differ"):
            S.check_file(ann1, ids_file)
        rows[0]["extra"] = "prediction"
        S._write_jsonl(ann1, rows)
        with self.assertRaisesRegex(S.SampleError, "unexpected fields"):
            S.check_file(ann1, ids_file)

    def test_adjudicate_and_export(self) -> None:
        ids_file, (ann1, ann2) = self.draw()
        self.fill(ann1, {"7": 1, "8": 0})
        self.fill(ann2, {"7": 1, "8": 1})
        stats, rows = S.adjudicate([ann1, ann2], ids_file)
        self.assertEqual((stats["agreed"], stats["disagreed"]), (1, 1))
        self.assertEqual(stats["pairwise"]["ann1|ann2"]["percent_agreement"], 0.5)
        self.assertEqual(stats["positives_per_annotator"], {"ann1": 1, "ann2": 2})
        by_id = {r["row_id"]: r for r in rows}
        self.assertEqual(by_id["7"]["final"], 1)
        self.assertIsNone(by_id["8"]["final"])
        adjudication = self.out / "private" / "adj.jsonl"
        S._write_jsonl(adjudication, rows)
        with self.assertRaisesRegex(S.SampleError, "without a final"):
            S.export(adjudication, ids_file, self.out / "private" / "oracle.jsonl")
        by_id["8"]["final"] = 0
        S._write_jsonl(adjudication, rows)
        oracle = self.out / "private" / "oracle.jsonl"
        prov = S.export(adjudication, ids_file, oracle)
        self.assertEqual((prov["kind"], prov["n"], prov["positives"]), ("adjudication", 2, 1))
        self.assertTrue(oracle.with_suffix(".provenance.json").is_file())
        # The exported lines are exactly the trainer's jsonl contract ({"row_id","label"} per line,
        # training/m3_encoder/data.py::load_a_labels); tests/ must not import the training package.
        lines = [json.loads(line) for line in oracle.read_text(encoding="utf-8").splitlines()]
        self.assertTrue(all(set(r) == {"row_id", "label"} for r in lines))
        self.assertEqual({r["row_id"]: r["label"] for r in lines}, {"7": 1, "8": 0})
        single = S.export(ann1, ids_file, self.out / "private" / "single.jsonl")
        self.assertEqual(single["kind"], "single-annotator")

    def test_cohen_kappa(self) -> None:
        self.assertEqual(S.cohen_kappa([1, 0, 1, 0], [1, 0, 1, 0]), 1.0)
        self.assertAlmostEqual(S.cohen_kappa([1, 1, 0, 0], [1, 0, 1, 0]), 0.0)
        self.assertIsNone(S.cohen_kappa([], []))

    def test_sampler_never_reads_predictions_or_derived_labels(self) -> None:
        source = (G.AI_ROOT / "eval" / "a_head_dev_sample.py").read_text(encoding="utf-8")
        for forbidden in ("dev_predictions", "study_slice", "m1_lexicon_dev_seed42", "m1_lexicon_train_seed42",
                          "thresholds.yaml", "raw_score", "lexicon_hit", "load_config", "decision"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
