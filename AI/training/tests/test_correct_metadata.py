"""training/m3_encoder/correct_metadata.py: metadata-only correction of an exported artifact.

Runs on a synthetic legacy artifact (random bytes stand in for weights.pt; no torch needed): the
exact files an exporter before 2026-09-18 (third pass) wrote, with the generic "human dev oracle"
sentence and the `a_human` keys. The committed rule-v3 correction is checked for reproducibility
in CommittedRuleV3CorrectionTest (mandatory: the record is a repository file).
"""
from __future__ import annotations

import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from training.m3_encoder import correct_metadata as C
from training.m3_encoder import provenance as P

AI_ROOT = Path(__file__).resolve().parents[2]
# The committed correction of the rule-v3 candidate (docs/training/runs/...): exported originals, the
# corrected metadata and the tool's record, produced on a scratch copy of the Drive artifact.
RULE_V3 = AI_ROOT / "docs" / "training" / "runs" / "m3-berturk-multihead-a-rule-v3-20260918-074806.metadata"
RULE_V3_WEIGHTS = "41d98d7fa2599907f4b3f4c22b24bdd2990b90ffecae4563d09e16fabf91e145"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def legacy_artifact(root: Path, kind: str | None = "ai-assisted-human-adjudicated", name: str = "legacy") -> Path:
    d = root / name
    d.mkdir()
    coverage = {"train": {"rows": 10, "binary": 10, "a": 10, "a_human": 0, "b": 0, "c": 0},
                "dev": {"rows": 5, "binary": 5, "a": 5, "a_human": 3 if kind else 0, "b": 0, "c": 0}}
    sources = {"a": [{"file": "m1_lexicon_train_seed42.json", "sha256": "7" * 64, "kind": "derived-pseudo-label"}],
               "a_human": [{"file": "ref.jsonl", "sha256": "9" * 64, "kind": "jsonl"}] if kind else [], "b": [], "c": []}
    files = {
        "weights.pt": os.urandom(8192),
        "config.json": b'{\n  "model_type": "bert"\n}\n',
        "tokenizer.json": b'{"version": "1.0"}\n',
        "tokenizer_config.json": b'{\n  "do_lower_case": false\n}\n',
    }
    heads = {"artifact_id": "m3-test", "format": "multi-head-encoder-v1",
             "heads": {"a": {"size": 1, "labels": ["A1"], "trained": True, "activation": "sigmoid"}}, "off_index": 1,
             "best_epoch": 0, "hyperparams": {"lr": 2e-05, "seed": 42}, "a_evaluation_reference_kind": kind,
             "label_coverage": coverage, "label_sources": sources, "a_head_supervision": C.LEGACY_SUPERVISION,
             "history": [{"epoch": 0, "dev_binary_macro_f1": 0.8247056083562243}]}
    files["heads.json"] = C.dump(heads)
    digests = {n: sha(b) for n, b in sorted(files.items())}
    a_block = ({"oracle": kind, "labelled_rows": 3, "A1": {"support": 1, "tp": 1, "fp": 0, "fn": 0, "tn": 2,
                                                           "precision": {"value": 1.0, "ci_low": 1.0, "ci_high": 1.0}}}
               if kind else {"oracle": None, "labelled_rows": 0, "note": P.LEGACY_NO_REFERENCE_NOTE})
    dev_eval = {"n_rows": 5, "decision_point_for_reporting": 0.5, "binary": {"macro_f1": {"value": 0.8247056083562243}},
                "a": a_block, "a_pseudo_label_agreement": {"labelled_rows": 5, "note": P.PSEUDO_LABEL_AGREEMENT_NOTE},
                "artifact_id": "m3-test", "digests": digests, "label_coverage": coverage, "label_sources": sources,
                "smoke": False}
    for n, b in files.items():
        (d / n).write_bytes(b)
    (d / "sha256.txt").write_text("".join(f"{h}  {n}\n" for n, h in digests.items()), encoding="utf-8")
    (d / "MANIFEST_ROW.md").write_text("| m3-test | ... |\n", encoding="utf-8")
    (d / "dev_eval.json").write_bytes(C.dump(dev_eval))
    return d


def tree_digests(directory: Path) -> dict[str, str]:
    return {str(p.relative_to(directory)): sha(p.read_bytes()) for p in sorted(directory.rglob("*")) if p.is_file()}


class CorrectMetadataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.src = legacy_artifact(self.root)
        self.weights = sha((self.src / "weights.pt").read_bytes())
        self.dst = self.root / "corrected"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_source_is_never_written_and_weights_are_byte_identical(self) -> None:
        before = tree_digests(self.src)
        record = C.correct(self.src, self.dst, self.weights)
        self.assertEqual(tree_digests(self.src), before)
        self.assertEqual((self.dst / "weights.pt").read_bytes(), (self.src / "weights.pt").read_bytes())
        self.assertEqual(set(record["weights_sha256"].values()), {self.weights})
        self.assertEqual(C.verify(self.dst, self.weights), [])

    def test_only_the_provenance_fields_change(self) -> None:
        C.correct(self.src, self.dst, self.weights)
        old_h, new_h = (json.loads((d / "heads.json").read_text(encoding="utf-8")) for d in (self.src, self.dst))
        self.assertEqual(new_h["a_head_supervision"], P.a_head_supervision("ai-assisted-human-adjudicated"))
        self.assertIn("NOT a human oracle", new_h["a_head_supervision"])
        self.assertEqual(new_h["label_coverage"]["dev"]["a_reference"], 3)
        self.assertEqual([s["file"] for s in new_h["label_sources"]["a_reference"]], ["ref.jsonl"])
        for doc in (new_h, json.loads((self.dst / "dev_eval.json").read_text(encoding="utf-8"))):
            self.assertNotIn("a_human", json.dumps(doc))
            self.assertNotIn("human dev oracle", json.dumps(doc))
        for key in set(old_h) - {"a_head_supervision", "label_coverage", "label_sources"}:
            with self.subTest(heads=key):
                self.assertEqual(new_h[key], old_h[key])
        old_d, new_d = (json.loads((d / "dev_eval.json").read_text(encoding="utf-8")) for d in (self.src, self.dst))
        for key in ("binary", "a", "a_pseudo_label_agreement", "digests", "n_rows", "decision_point_for_reporting"):
            with self.subTest(dev_eval=key):
                self.assertEqual(new_d[key], old_d[key])                  # metrics and export-time digests unchanged
        self.assertEqual(new_d["metadata_corrections"][0]["id"], C.CORRECTION_ID)
        self.assertEqual(new_h["metadata_corrections"][0]["original_sha256"], sha((self.src / "heads.json").read_bytes()))

    def test_sha256_txt_keeps_its_files_and_updates_only_changed_digests(self) -> None:
        C.correct(self.src, self.dst, self.weights)
        old, new = (C.read_digests(d / "sha256.txt") for d in (self.src, self.dst))
        self.assertEqual([n for _, n in old], [n for _, n in new])
        changed = {n for (a, n), (b, _) in zip(old, new) if a != b}
        self.assertEqual(changed, {"heads.json"})
        self.assertEqual(dict((n, d) for d, n in new)["weights.pt"], self.weights)
        for name in ("heads.json", "dev_eval.json", "sha256.txt"):
            self.assertEqual((self.dst / C.ORIGINALS / name).read_bytes(), (self.src / name).read_bytes())

    def test_refusals_leave_nothing_behind(self) -> None:
        with self.assertRaisesRegex(C.CorrectionError, "expected"):
            C.correct(self.src, self.dst, "0" * 64)
        self.assertFalse(self.dst.exists())
        with self.assertRaisesRegex(C.CorrectionError, "separate"):
            C.correct(self.src, self.src / "inside", self.weights)
        self.dst.mkdir()
        with self.assertRaisesRegex(C.CorrectionError, "exists"):
            C.correct(self.src, self.dst, self.weights)
        tampered = legacy_artifact(self.root, name="tampered")
        (tampered / "config.json").write_text("{}", encoding="utf-8")
        with self.assertRaisesRegex(C.CorrectionError, "does not verify"):
            C.correct(tampered, self.root / "t_out", sha((tampered / "weights.pt").read_bytes()))
        self.assertFalse((self.root / "t_out").exists())

    def test_an_artifact_without_a_recorded_kind_is_not_guessed(self) -> None:
        src = legacy_artifact(self.root, name="nokindkey")
        heads = json.loads((src / "heads.json").read_text(encoding="utf-8"))
        del heads["a_evaluation_reference_kind"]
        (src / "heads.json").write_bytes(C.dump(heads))
        (src / "sha256.txt").write_text("".join(f"{sha((src / n).read_bytes())}  {n}\n" for _, n in
                                                C.read_digests(src / "sha256.txt")), encoding="utf-8")
        with self.assertRaisesRegex(C.CorrectionError, "cannot be inferred"):
            C.correct(src, self.root / "nk_out", sha((src / "weights.pt").read_bytes()))

    def test_no_reference_artifact_gets_the_no_claim_wording(self) -> None:
        src = legacy_artifact(self.root, kind=None, name="noref")
        out = self.root / "noref_out"
        C.correct(src, out, sha((src / "weights.pt").read_bytes()))
        heads = json.loads((out / "heads.json").read_text(encoding="utf-8"))
        dev_eval = json.loads((out / "dev_eval.json").read_text(encoding="utf-8"))
        self.assertIn("NO A-head quality claim", heads["a_head_supervision"])
        self.assertEqual(dev_eval["a"]["note"], P.NO_REFERENCE_NOTE)

    def test_corrected_once_and_verify_catches_an_edit(self) -> None:
        C.correct(self.src, self.dst, self.weights)
        with self.assertRaises(C.CorrectionError):
            C.correct(self.dst, self.root / "twice", self.weights)       # subdirectory + metadata_corrections
        heads = json.loads((self.dst / "heads.json").read_text(encoding="utf-8"))
        heads["a_head_supervision"] = "quality claims only against the human dev oracle"
        (self.dst / "heads.json").write_bytes(C.dump(heads))
        problems = C.verify(self.dst, self.weights)
        self.assertTrue(any("heads.json" in p for p in problems), problems)
        self.assertNotEqual(C.verify(self.dst, "0" * 64), [])

    def test_cli(self) -> None:
        self.assertEqual(C.main(["correct", "--artifact", str(self.src), "--out", str(self.dst),
                                 "--expect-weights-sha256", self.weights]), 0)
        self.assertEqual(C.main(["verify", "--artifact", str(self.dst), "--expect-weights-sha256", self.weights]), 0)
        self.assertEqual(C.main(["verify", "--artifact", str(self.dst), "--expect-weights-sha256", "0" * 64]), 1)


class CommittedRuleV3CorrectionTest(unittest.TestCase):
    """The committed correction of m3-berturk-multihead-a-rule-v3-20260918-074806 is exactly what the
    tool derives from the exported originals, and it never touched weights.pt."""

    def test_corrected_files_are_derived_from_the_originals(self) -> None:
        originals = {p.name: p.read_bytes() for p in (RULE_V3 / "original").iterdir()
                     if p.name in ("heads.json", "dev_eval.json", "sha256.txt")}
        derived, _ = C.derive(originals)
        for name, data in derived.items():
            with self.subTest(file=name):
                self.assertEqual((RULE_V3 / "corrected" / name).read_bytes(), data)
        old, new = (C.read_digests(RULE_V3 / d / "sha256.txt") for d in ("original", "corrected"))
        self.assertEqual(dict((n, d) for d, n in old)["weights.pt"], RULE_V3_WEIGHTS)
        self.assertEqual(dict((n, d) for d, n in new)["weights.pt"], RULE_V3_WEIGHTS)
        self.assertEqual({n for (a, n), (b, _) in zip(old, new) if a != b}, {"heads.json"})

    def test_record_proves_the_weights_were_not_changed(self) -> None:
        record = json.loads((RULE_V3 / "corrected" / C.RECORD).read_text(encoding="utf-8"))
        self.assertEqual(record["artifact_id"], "m3-berturk-multihead-a-rule-v3-20260918-074806")
        self.assertEqual(set(record["weights_sha256"].values()), {RULE_V3_WEIGHTS})
        self.assertEqual(record["files"]["weights.pt"],
                         {"original_sha256": RULE_V3_WEIGHTS, "corrected_sha256": RULE_V3_WEIGHTS, "changed": False})
        for name, info in record["files"].items():
            for folder, key in (("original", "original_sha256"), ("corrected", "corrected_sha256")):
                path = RULE_V3 / folder / name
                if path.is_file():
                    with self.subTest(file=f"{folder}/{name}"):
                        self.assertEqual(sha(path.read_bytes()), info[key])
        self.assertEqual({n for n, i in record["files"].items() if i["changed"]},
                         {"heads.json", "dev_eval.json", "sha256.txt"})
        heads = json.loads((RULE_V3 / "corrected" / "heads.json").read_text(encoding="utf-8"))
        self.assertEqual(heads["a_evaluation_reference_kind"], "ai-assisted-human-adjudicated")
        self.assertIn("NOT a human oracle", heads["a_head_supervision"])


if __name__ == "__main__":
    unittest.main()
