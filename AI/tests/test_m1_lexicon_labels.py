"""eval/m1_lexicon_labels.py - the derived-label generator behind the dev and train protocols.

Synthetic corpus + synthetic split in a temp dir, real m0 / m6 / m1 (terlik) and either the real
m2 (zeyrek) or an injected m2 that publishes a chosen normalized channel, so every branch of the
a_label rule (train protocol §5) is exercised deterministically:
  * train/dev separation, no test-set rows, refusal of test-set paths
  * determinism, provenance, split digest
  * raw-only, normalized-only (mapped and unmapped), both; lexicon_hit == raw OR norm
  * every recorded span is the exact original substring
  * stale-file detection (--check) on a fresh file, on doctored headers, and on the COMMITTED files

Preconditions FAIL with a named reason (never skip): terlik and zeyrek must be importable, which
means the project interpreter AI/.venv (CONTRIBUTING.md "Interpreter").
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import tempfile
import unittest
from pathlib import Path
from typing import Any

from contracts.codes import ModuleName
from contracts.module_api import BaseModule, Context, ModuleOutput
from eval import m1_lexicon_labels as G
from modules.m0_charsafe.module import CharSafeModule
from modules.m1_lexicon.module import LexiconModule
from modules.m2_deobf.module import DeobfModule
from modules.m6_target.module import TargetModule

DERIVED = G.AI_ROOT / "eval" / "derived"
SPLIT = G.REPO_ROOT / "diagnosis" / "data" / "splits" / "split_seed42.json"


def require_engines(test: unittest.TestCase) -> None:
    missing = [d for d in ("terlik", "zeyrek") if importlib.util.find_spec(d) is None]
    if missing:
        test.fail(f"PRECONDITION: {missing} not importable - run the suite with AI/.venv "
                  "(CONTRIBUTING.md 'Interpreter'); the root .venv is not the project interpreter")


class FakeDeobf(BaseModule):
    """An m2 that publishes exactly the normalized channel a test wants (ADR-008 signals)."""
    name = ModuleName.M2_DEOBF
    version = "test"
    provides = frozenset({"normalized_text"})

    def __init__(self, table: dict[str, tuple[str, list[int] | None]]) -> None:
        super().__init__()
        self.table = table
        self.tier2_enabled = True

    def _run(self, ctx: Context) -> ModuleOutput:
        source = ctx.charsafe_text if ctx.charsafe_text is not None else ctx.text
        normalized, offsets = self.table.get(ctx.text, (source, list(range(len(source)))))
        signals: dict[str, Any] = {}
        if offsets is not None:
            signals["_offsets"] = offsets
            signals["offsets_identity"] = normalized == ctx.text and offsets == list(range(len(ctx.text)))
        return ModuleOutput(normalized_text=normalized, signals=signals)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class SyntheticData:
    """A corpus TSV, a split file and a decoy test-set file, written to `root`."""

    # rule v3 classes (train protocol): siktir / bok / am / orospu are POSITIVE; aptal (ordinary insult) and
    # kahpe (gendered insult, owner decision) are EXCLUDED
    TRAIN = [("1", "siktir git", "OFF"), ("2", "sen xbok", "OFF"), ("3", "psikoloji dersi", "NOT"),
             ("4", "saat 10 am", "NOT"), ("5", "Bu bir test cumlesi", "NOT"), ("6", "amca geldi", "NOT"),
             ("11", "aptal herif", "OFF"), ("12", "orospu", "OFF"), ("13", "kahpe", "OFF")]
    DEV = [("7", "aptal", "OFF"), ("8", "merhaba", "NOT")]
    TEST = [("9", "salak", "OFF"), ("10", "iyi", "NOT")]

    def __init__(self, root: Path) -> None:
        self.root = root
        (root / "coltekin").mkdir()
        (root / "splits").mkdir()
        self.corpus = root / "coltekin" / "offenseval-tr-training-v1.tsv"
        self.test_set = root / "coltekin" / "offenseval-tr-testset-v1.tsv"
        self.split = root / "splits" / "split_seed42.json"
        self._write_tsv(self.corpus, self.TRAIN + self.DEV)
        self._write_tsv(self.test_set, self.TEST)
        train_ids = [r[0] for r in self.TRAIN]
        dev_ids = [r[0] for r in self.DEV]
        self.split.write_text(json.dumps({
            "seed": 42, "train_ids": train_ids, "dev_ids": dev_ids, "dev_fingerprint": G.fingerprint(dev_ids),
            "counts": {"train": self._counts(self.TRAIN), "dev": self._counts(self.DEV)}}), encoding="utf-8")
        self.expected = {
            "train": {"n": len(train_ids), **self._counts(self.TRAIN), "fingerprint": G.fingerprint(train_ids)},
            "dev": {"n": len(dev_ids), **self._counts(self.DEV), "fingerprint": G.fingerprint(dev_ids)},
        }

    @staticmethod
    def _write_tsv(path: Path, rows: list[tuple[str, str, str]]) -> None:
        path.write_text("id\ttweet\tsubtask_a\n" + "".join(f"{i}\t{t}\t{l}\n" for i, t, l in rows), encoding="utf-8")

    @staticmethod
    def _counts(rows: list[tuple[str, str, str]]) -> dict[str, int]:
        return {"OFF": sum(r[2] == "OFF" for r in rows), "NOT": sum(r[2] == "NOT" for r in rows)}

    def spec(self, split: str) -> G.Spec:
        return G.Spec(split=split, corpus=self.corpus, corpus_sha256=G.sha256_file(self.corpus),
                      split_file=self.split, split_sha256=G.sha256_file(self.split),
                      frozen_slice=None, frozen_slice_sha256=None, expected=self.expected)


class GeneratorTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.tmp = tempfile.TemporaryDirectory()
        cls.data = SyntheticData(Path(cls.tmp.name))
        # "sen xbok": the raw channel sees "bok" inside "xbok" (a collision); the injected m2
        # drops the "x" and maps the repaired token back to original indices 5..7 (ADR-008 §5).
        cls.mapped = ("sen bok", [0, 1, 2, 3, 5, 6, 7])
        cls.pipeline = G.build_pipeline([CharSafeModule(), FakeDeobf({"sen xbok": cls.mapped}), TargetModule(),
                                         LexiconModule()])

    @classmethod
    def tearDownClass(cls) -> None:
        cls.tmp.cleanup()

    def setUp(self) -> None:
        require_engines(self)

    def rows_for(self, split: str, pipeline=None) -> tuple[Path, dict[str, Any]]:
        out = Path(self.tmp.name) / f"{split}.json"
        rc = G.generate(self.data.spec(split), out, pipeline=pipeline or self.pipeline, spot_check=0)
        self.assertEqual(rc, 0)
        return out, json.loads(out.read_text(encoding="utf-8"))

    # -- split discipline -------------------------------------------------------------
    def test_train_and_dev_files_hold_exactly_their_split_and_never_a_test_row(self) -> None:
        _, train = self.rows_for("train")
        _, dev = self.rows_for("dev")
        train_ids = [r["row_id"] for r in train["rows"]]
        dev_ids = [r["row_id"] for r in dev["rows"]]
        self.assertEqual(train_ids, [r[0] for r in SyntheticData.TRAIN])
        self.assertEqual(dev_ids, [r[0] for r in SyntheticData.DEV])
        self.assertFalse(set(train_ids) & set(dev_ids))
        for test_id in (r[0] for r in SyntheticData.TEST):
            self.assertNotIn(test_id, train_ids + dev_ids)
        self.assertEqual(train["split"]["name"], "train")
        self.assertEqual(dev["split"]["name"], "dev")

    def test_test_set_paths_are_refused_before_anything_is_read(self) -> None:
        for bad in (self.data.test_set, Path("x/offenseval-tr-labela-v1.tsv")):
            with self.assertRaises(G.ProtocolStop):
                G.refuse_test_set(bad)
        spec = G.Spec(split="train", corpus=self.data.test_set, corpus_sha256="", split_file=self.data.split,
                      split_sha256=G.sha256_file(self.data.split), frozen_slice=None, expected=self.data.expected)
        with self.assertRaises(G.ProtocolStop):
            G.load_inputs(spec)

    def test_split_overlap_and_wrong_digest_stop_the_run(self) -> None:
        root = Path(self.tmp.name) / "bad"
        root.mkdir()
        bad = SyntheticData(root)
        split = json.loads(bad.split.read_text(encoding="utf-8"))
        split["train_ids"].append(split["dev_ids"][0])
        bad.split.write_text(json.dumps(split), encoding="utf-8")
        spec = bad.spec("train")
        with self.assertRaises(G.ProtocolStop):
            G.load_inputs(spec)                              # sha256 of the split changed
        expected = {**bad.expected, "train": {**bad.expected["train"], "n": bad.expected["train"]["n"] + 1}}
        spec = G.Spec(split="train", corpus=bad.corpus, corpus_sha256=G.sha256_file(bad.corpus), split_file=bad.split,
                      split_sha256=G.sha256_file(bad.split), frozen_slice=None, expected=expected)
        with self.assertRaisesRegex(G.ProtocolStop, "overlap|fingerprint"):
            G.load_inputs(spec)

    # -- determinism / provenance ------------------------------------------------------
    def test_generation_is_deterministic(self) -> None:
        ids, corpus, _ = G.load_inputs(self.data.spec("train"))
        block1, rows1 = G.build_rows(ids, corpus, self.pipeline)
        block2, rows2 = G.build_rows(ids, corpus, self.pipeline)
        self.assertEqual(block1, block2)
        self.assertEqual(rows1, rows2)

    def test_header_records_provenance(self) -> None:
        _, data = self.rows_for("train")
        self.assertRegex(data["generator"]["git_head"], r"^[0-9a-f]{40}$")
        self.assertIsInstance(data["generator"]["uncommitted_changes"], list)
        self.assertEqual(data["generator"]["version"], G.GENERATOR_VERSION)
        self.assertEqual(data["generator"]["script"], G.GENERATOR)
        self.assertEqual(data["protocol"]["file"], "AI/protocols/m1_lexicon_train_labels_protocol.md")
        self.assertEqual(data["protocol"]["sha256"], G.sha256_file(G.AI_ROOT / G.PROTOCOLS["train"]))
        self.assertEqual(data["inputs"]["split"]["sha256"], G.sha256_file(self.data.split))
        self.assertEqual(data["inputs"]["corpus"]["sha256"], G.sha256_file(self.data.corpus))
        self.assertEqual(data["split"]["fingerprint"], self.data.expected["train"]["fingerprint"])
        self.assertEqual(data["engine"]["module_versions"],
                         {"m0_charsafe": CharSafeModule.version, "m2_deobf": "test", "m6_target": TargetModule.version,
                          "m1_lexicon": LexiconModule.version})
        self.assertEqual(data["engine"]["modules_in_order"], ["m0_charsafe", "m2_deobf", "m6_target", "m1_lexicon"])
        self.assertIsNotNone(data["engine"]["terlik"])
        self.assertEqual(data["row_fields"], G.ROW_FIELDS)
        self.assertEqual(data["rows_sha256"], hashlib.sha256(G.serialise_rows(data["rows"]).encode("utf-8")).hexdigest())

    # -- the a_label rule --------------------------------------------------------------
    def test_channels_and_a_label(self) -> None:
        _, data = self.rows_for("train")
        rows = {r["row_id"]: r for r in data["rows"]}
        with self.subTest(case="both channels"):
            self.assertEqual(rows["1"]["channel"], "both")
            self.assertEqual(rows["1"]["a_label"], 1)
            self.assertEqual({m["channel"] for m in rows["1"]["matches"]}, {"raw", "normalized"})
        with self.subTest(case="normalized-only, mapped"):
            self.assertEqual(rows["2"]["channel"], "normalized")
            self.assertFalse(rows["2"]["lexicon_hit_raw"])
            self.assertTrue(rows["2"]["lexicon_hit_norm"])
            self.assertEqual(rows["2"]["a_label"], 1)
            self.assertEqual(rows["2"]["matches"], [{"channel": "normalized", "start": 5, "end": 8, "surface": "bok"}])
            self.assertTrue(any("bok in xbok" in c["evidence"] for c in rows["2"]["collisions"]))
        with self.subTest(case="collision only"):
            self.assertEqual(rows["3"]["channel"], "none")
            self.assertEqual(rows["3"]["a_label"], 0)
            self.assertTrue(rows["3"]["collisions"])
            self.assertEqual(rows["6"]["a_label"], 0)
        with self.subTest(case="homonym recorded, not applied"):
            self.assertEqual(rows["4"]["a_label"], 1)
            self.assertEqual([h["surface"] for h in rows["4"]["homonyms"]], ["am"])
        with self.subTest(case="clean"):
            self.assertEqual(rows["5"]["a_label"], 0)
            self.assertEqual(rows["5"]["matches"], [])
        with self.subTest(case="rule v3: ordinary insult is a hit but NOT a positive"):
            self.assertTrue(rows["11"]["lexicon_hit"])
            self.assertEqual((rows["11"]["a_label_v1"], rows["11"]["a_label"]), (1, 0))
            self.assertEqual(rows["11"]["root_classes"], {"positive": [], "excluded": ["aptal"], "review": []})
        with self.subTest(case="rule v3: orospu is an explicit profane root"):
            self.assertEqual((rows["12"]["a_label_v1"], rows["12"]["a_label"]), (1, 1))
            self.assertEqual(rows["12"]["root_classes"], {"positive": ["orospu"], "excluded": [], "review": []})
        with self.subTest(case="rule v3: owner decision - kahpe is a gendered insult, EXCLUDED"):
            self.assertTrue(rows["13"]["lexicon_hit"])
            self.assertEqual((rows["13"]["a_label_v1"], rows["13"]["a_label"]), (1, 0))
            self.assertEqual(rows["13"]["root_classes"], {"positive": [], "excluded": ["kahpe"], "review": []})
        with self.subTest(case="rule v3: no row is masked"):
            self.assertTrue(all(r["a_label"] in (0, 1) for r in data["rows"]))
        with self.subTest(case="rule v3: positive class"):
            self.assertEqual(rows["1"]["root_classes"]["positive"], ["sik"])
            self.assertEqual(rows["4"]["root_classes"]["positive"], ["am"])
        for r in data["rows"]:
            self.assertEqual(r["lexicon_hit"], r["lexicon_hit_raw"] or r["lexicon_hit_norm"])
        self.assertEqual(data["counts"]["a_label"], 4)            # rows 1, 2, 4, 12
        self.assertEqual(data["counts"]["a_label_null"], 0)
        self.assertEqual(data["counts"]["a_label_v1"], 6)         # rows 1, 2, 4, 11, 12, 13
        self.assertEqual(data["counts"]["v1_positive_now_zero"], 2)   # rows 11, 13
        self.assertEqual(data["counts"]["v1_positive_now_null"], 0)
        self.assertEqual(data["counts"]["v1_zero_now_positive"], 0)
        self.assertEqual(data["counts"]["normalized_only"], 1)
        self.assertEqual(data["counts"]["both"], 5)   # rows 1, 4, 11, 12, 13
        self.assertEqual(data["counts"]["raw_only"], 0)
        self.assertEqual(data["counts"]["norm_hit_unmapped"], 0)
        self.assertEqual(data["counts"]["rows_all_matches_homonym"], 1)
        self.assertEqual(data["a_label_rule"]["version"], 3)
        self.assertEqual(data["a_label_rule"]["terlik_tr_dictionary_sha256"], G.TERLIK_TR_DICTIONARY_SHA256)
        self.assertEqual(data["a_label_rule"]["class_sizes"], {"positive": 17, "excluded": 130, "review": 0})
        self.assertEqual(data["a_label_rule"]["taxonomy_sha256"], G.taxonomy_sha256())
        self.assertEqual(data["a_label_rule"]["positive_roots"], sorted(G.POSITIVE_ROOTS))

    def test_raw_only_positive_and_unmapped_normalized_hit(self) -> None:
        # raw-only: the injected m2 loses the profane word; unmapped: it repairs "xaptal" but publishes no
        # offsets and a different length, so m1 can only flag the normalized hit (Q9) -> a_label 0.
        pipeline = G.build_pipeline([CharSafeModule(), FakeDeobf({"siktir git": ("hello git", list(range(9))),
                                                                  "sen xbok": ("sen bok", None)}),
                                     TargetModule(), LexiconModule()])
        _, data = self.rows_for("train", pipeline=pipeline)
        rows = {r["row_id"]: r for r in data["rows"]}
        self.assertEqual(rows["1"]["channel"], "raw")
        self.assertEqual(rows["1"]["a_label"], 1)
        self.assertEqual([m["channel"] for m in rows["1"]["matches"]], ["raw"])
        self.assertEqual(rows["2"]["channel"], "normalized")
        self.assertTrue(rows["2"]["lexicon_hit"])
        self.assertEqual(rows["2"]["matches"], [])
        self.assertEqual(rows["2"]["a_label"], 0)
        self.assertEqual(data["counts"]["norm_hit_unmapped"], 1)
        self.assertEqual(data["counts"]["raw_only"], 1)

    def test_every_span_is_the_exact_original_substring(self) -> None:
        _, data = self.rows_for("train")
        corpus = {r[0]: r[1] for r in SyntheticData.TRAIN}
        for r in data["rows"]:
            text = corpus[r["row_id"]]
            for item in r["matches"] + r["collisions"] + r["homonyms"]:
                self.assertLess(item["start"], item["end"])
                self.assertLessEqual(item["end"], len(text))
                self.assertEqual(text[item["start"]:item["end"]], item["surface"])

    def test_real_m2_path_on_the_synthetic_rows(self) -> None:
        pipeline = G.build_pipeline([CharSafeModule(), DeobfModule(), TargetModule(), LexiconModule()])
        _, data = self.rows_for("train", pipeline=pipeline)
        rows = {r["row_id"]: r for r in data["rows"]}
        self.assertTrue(data["engine"]["m2_tier2_enabled"])
        self.assertTrue(data["channels"]["normalized"]["available"])
        self.assertEqual(rows["1"]["channel"], "both")
        self.assertEqual(rows["3"]["a_label"], 0)
        self.assertEqual(data["engine"]["module_versions"]["m2_deobf"], DeobfModule.version)

    # -- rule v2: the lexical classes and the evaluation-leakage firewall ----------------
    def test_lexical_classes_follow_the_protocol_table(self) -> None:
        """Rule v3: A = an explicit obscene / profane lexical root; every dictionary root decided."""
        classes = G.lexical_classes()
        self.assertEqual(len(classes), 147)
        self.assertEqual({r for r, c in classes.items() if c == G.POSITIVE},
                         {"am", "amcı", "amk", "bok", "gavat", "göt", "hassiktir", "oç", "orospu", "pezevenk", "piç",
                          "sakso", "sg", "sik", "sktrgt", "taşak", "yarrak"})
        self.assertEqual([r for r, c in classes.items() if c == G.REVIEW], [])
        for root, why in (("aptal", "ordinary insult"), ("salak", "ordinary insult"), ("eşek", "ordinary insult"),
                          ("rezil", "derogatory"), ("ibne", "identity slur"), ("puşt", "identity slur"),
                          ("meme", "sexual-topic vocabulary"), ("döl", "sexual-topic vocabulary"),
                          ("fuhuş", "sexual-topic vocabulary"), ("kerhane", "sexual-topic vocabulary"),
                          ("kahpe", "gendered insult, owner"), ("sürtük", "gendered insult, owner"),
                          ("kaltak", "gendered insult, owner"), ("kancık", "gendered insult, owner"),
                          ("kevaşe", "gendered insult, owner"), ("kaşar", "gendered insult"),
                          ("aşifte", "gendered insult"), ("fahişe", "formal term"), ("geber", "threat"),
                          ("allahbelanıversin", "sacred concept")):
            self.assertEqual(classes[root], G.EXCLUDED, f"{root}: {why}")

    def test_protocol_lists_are_the_generator_sets(self) -> None:
        """The rule the protocol freezes is the rule the generator runs: the three RULE_V3_* lines of
        the train protocol equal POSITIVE_ROOTS / EXCLUDED_ROOTS / REVIEW_ROOTS."""
        text = (G.AI_ROOT / G.PROTOCOLS["train"]).read_text(encoding="utf-8")
        parsed = {}
        for name in ("POSITIVE", "EXCLUDED", "REVIEW"):
            m = re.search(rf"^RULE_V3_{name} \((\d+)\):(.*)$", text, re.M)
            self.assertIsNotNone(m, name)
            items = [x.strip() for x in m.group(2).split(",") if x.strip()]
            self.assertEqual(len(items), int(m.group(1)), name)
            parsed[name] = frozenset(items)
        self.assertEqual(parsed["POSITIVE"], G.POSITIVE_ROOTS)
        self.assertEqual(parsed["EXCLUDED"], G.EXCLUDED_ROOTS)
        self.assertEqual(parsed["REVIEW"], G.REVIEW_ROOTS)

    def test_unexpected_dictionary_conditions_stop(self) -> None:
        roots = sorted(G.POSITIVE_ROOTS | G.EXCLUDED_ROOTS)
        self.assertEqual(len(G.classify(roots)), 147)
        with self.assertRaisesRegex(G.ProtocolStop, "no rule-v3 class"):
            G.classify(roots + ["yenikelime"])
        with self.assertRaisesRegex(G.ProtocolStop, "does not hold"):
            G.classify([r for r in roots if r != "sik"])

    def test_masking_mechanism_is_kept_for_a_future_review_class(self) -> None:
        self.assertIsNone(G.a_label_of(1, {"positive": [], "excluded": [], "review": ["x"]}))
        self.assertEqual(G.a_label_of(1, {"positive": ["sik"], "excluded": [], "review": ["x"]}), 1)
        self.assertEqual(G.a_label_of(1, {"positive": [], "excluded": ["aptal"], "review": []}), 0)
        self.assertEqual(G.a_label_of(0, {"positive": [], "excluded": [], "review": []}), 0)

    def test_another_terlik_dictionary_stops_the_run(self) -> None:
        other = Path(self.tmp.name) / "dictionary.json"
        other.write_text(json.dumps({"entries": [{"root": "x", "category": "sexual", "severity": "high"}]}), encoding="utf-8")
        with self.assertRaisesRegex(G.ProtocolStop, "pinned"):
            G.lexical_classes(other)

    def test_generator_cannot_reach_the_dev_evaluation_reference(self) -> None:
        """The 500-row AI-assisted, human-adjudicated reference is an EVALUATION set. The generator
        has no path to it: it names no file under eval/annotation/private, imports nothing from the
        sampler, and its class rule names no corpus row id."""
        source = (G.AI_ROOT / "eval" / "m1_lexicon_labels.py").read_text(encoding="utf-8")
        for forbidden in ("annotation/private", "a_dev_ai_assisted", "a_dev_human", ".adjudication", "a_head_dev_sample",
                          "a_head_eval", "sample_seed42"):
            self.assertNotIn(forbidden, source, forbidden)
        rule = (source.split("def classify")[1].split("\ndef ")[0]
                + source.split("def lexical_classes")[1].split("\ndef ")[0])
        self.assertIsNone(re.search(r"\d{5}", rule), "a corpus row id inside the class rule")
        self.assertFalse(any(ch.isdigit() for r in G.POSITIVE_ROOTS | G.EXCLUDED_ROOTS for ch in r),
                         "a digit inside the explicit taxonomy")
        for forbidden in ("sample_scores", "dev_eval", "dev_predictions", "a_head_eval", "runs/m3_multihead"):
            self.assertNotIn(forbidden, source, forbidden)

    # -- staleness ---------------------------------------------------------------------
    def test_check_passes_on_a_fresh_file_and_flags_doctored_ones(self) -> None:
        out, data = self.rows_for("train")
        spec = self.data.spec("train")
        problems = G.check_file(out, spec)
        self.assertEqual([p for p in problems if "m2_deobf" not in p], [])   # only the injected m2 version differs
        cases = {
            "module version": lambda d: d["engine"]["module_versions"].__setitem__("m1_lexicon", "0.0.0"),
            "generator version": lambda d: d["generator"].__setitem__("version", "1.0.0"),
            "protocol digest": lambda d: d["protocol"].__setitem__("sha256", "0" * 64),
            "rows edited": lambda d: d["rows"][0].__setitem__("a_label", 1 - d["rows"][0]["a_label"]),
            "row dropped": lambda d: d["rows"].pop(),
            "terlik version": lambda d: d["engine"].__setitem__("terlik", "0.0.0"),
            "taxonomy digest": lambda d: d["a_label_rule"].__setitem__("taxonomy_sha256", "0" * 64),
        }
        for name, doctor in cases.items():
            with self.subTest(case=name):
                doctored = json.loads(json.dumps(data))
                doctor(doctored)
                path = Path(self.tmp.name) / "doctored.json"
                path.write_text(json.dumps(doctored, ensure_ascii=False), encoding="utf-8")
                self.assertTrue(G.check_file(path, spec), name)

    def test_generation_stops_without_tier_2(self) -> None:
        fake = FakeDeobf({})
        fake.tier2_enabled = False
        pipeline = G.build_pipeline([CharSafeModule(), fake, TargetModule(), LexiconModule()])
        out = Path(self.tmp.name) / "no_tier2.json"
        self.assertEqual(G.generate(self.data.spec("train"), out, pipeline=pipeline, spot_check=0), 2)
        self.assertFalse(out.exists())


class CommittedFilesTest(unittest.TestCase):
    """The committed derived files are current at HEAD (protocol §7 staleness) and hold exactly
    their split: the train file never contains a dev row and vice versa."""

    FILES = {"train": DERIVED / "m1_lexicon_train_seed42.json", "dev": DERIVED / "m1_lexicon_dev_seed42.json"}

    def setUp(self) -> None:
        require_engines(self)

    def test_committed_files_are_not_stale(self) -> None:
        for split, path in self.FILES.items():
            with self.subTest(split=split):
                self.assertTrue(path.is_file(), f"{path} missing - generate it per its protocol")
                self.assertEqual(G.check_file(path), [])

    def test_committed_files_hold_disjoint_halves_of_the_frozen_split(self) -> None:
        split = json.loads(SPLIT.read_text(encoding="utf-8"))
        ids = {}
        for name, path in self.FILES.items():
            data = json.loads(path.read_text(encoding="utf-8"))
            ids[name] = [r["row_id"] for r in data["rows"]]
            self.assertEqual(ids[name], [str(i) for i in split[f"{name}_ids"]])
            self.assertEqual(data["split"]["name"], name)
            self.assertTrue(data["protocol"]["committed_and_unchanged"], f"{name}: generated against an uncommitted protocol")
            self.assertEqual(data["generator"]["uncommitted_changes"], [], f"{name}: generated from a dirty tree")
            self.assertEqual(data["counts"]["norm_hit_unmapped"], 0)
        self.assertFalse(set(ids["train"]) & set(ids["dev"]))
        self.assertEqual(len(ids["train"]) + len(ids["dev"]), split["n_rows"])

    def test_generator_and_sampler_never_name_the_test_set_files(self) -> None:
        """The locked files are `offenseval-tr-testset-v1.tsv` and `offenseval-tr-labela-v1.tsv`
        (RESOURCES.md). Neither file name may appear in the generator or the sampler: the only
        mention of the test set is the refusal list of name fragments."""
        for script in ("m1_lexicon_labels.py", "a_head_dev_sample.py"):
            source = (G.AI_ROOT / "eval" / script).read_text(encoding="utf-8")
            self.assertIsNone(re.search(r"offenseval-tr-(testset|labela)", source), script)
            self.assertNotIn("load_coltekin_test", source, script)
        self.assertEqual(G.FORBIDDEN_INPUT_NAMES, ("testset", "labela"))


if __name__ == "__main__":
    unittest.main()
