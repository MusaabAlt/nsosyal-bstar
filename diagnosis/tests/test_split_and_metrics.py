"""Local, GPU-free checks for the phase 01 machinery.

The split and the metrics are the two things that, if silently wrong, produce a
plausible-looking number that nobody can catch by reading the output. Both are
pure stdlib on purpose, so they can be verified in the local Python 3.14 venv
before any Colab time is spent.
"""

import json
import sys

import pytest

from src import data_io, evaluate


def _corpus(n_off=40, n_not=160):
    rows = [{"id": str(i), "text": f"metin {i}", "label": "OFF"} for i in range(n_off)]
    rows += [{"id": str(1000 + i), "text": f"metin {i}", "label": "NOT"} for i in range(n_not)]
    return rows


# --------------------------------------------------------------------------
# split
# --------------------------------------------------------------------------


def test_split_is_stratified_and_exhaustive():
    rows = _corpus()
    train, dev = data_io.stratified_split(rows, dev_fraction=0.15, seed=42)

    assert len(train) + len(dev) == len(rows)
    assert not ({r["id"] for r in train} & {r["id"] for r in dev}), "train/dev overlap"
    # 15% of each class, rounded: 6 OFF, 24 NOT
    assert sum(1 for r in dev if r["label"] == "OFF") == 6
    assert sum(1 for r in dev if r["label"] == "NOT") == 24


def test_split_is_deterministic_and_independent_of_row_order():
    """A reader change that reorders rows must not move examples between train
    and dev -- otherwise 'the same dev set' silently stops being the same."""
    rows = _corpus()
    shuffled = list(reversed(rows))

    _, dev_a = data_io.stratified_split(rows, 0.15, 42)
    _, dev_b = data_io.stratified_split(rows, 0.15, 42)
    _, dev_c = data_io.stratified_split(shuffled, 0.15, 42)

    assert data_io.dev_fingerprint(dev_a) == data_io.dev_fingerprint(dev_b)
    assert data_io.dev_fingerprint(dev_a) == data_io.dev_fingerprint(dev_c)


def test_a_different_seed_gives_a_different_dev_set():
    rows = _corpus()
    _, dev_42 = data_io.stratified_split(rows, 0.15, 42)
    _, dev_7 = data_io.stratified_split(rows, 0.15, 7)
    assert data_io.dev_fingerprint(dev_42) != data_io.dev_fingerprint(dev_7)


def test_dev_fingerprint_rejects_duplicate_ids():
    dup = [{"id": "1", "label": "OFF", "text": "a"}, {"id": "1", "label": "OFF", "text": "b"}]
    with pytest.raises(ValueError, match="Duplicate ids"):
        data_io.dev_fingerprint(dup)


def test_split_file_round_trips(tmp_path):
    rows = _corpus()
    path = tmp_path / "split_seed42.json"

    train_a, dev_a, meta_a = data_io.get_split(rows, path, "deadbeef", seed=42, dev_fraction=0.15)
    assert meta_a["reused_existing_file"] is False
    assert path.exists()

    train_b, dev_b, meta_b = data_io.get_split(rows, path, "deadbeef", seed=42, dev_fraction=0.15)
    assert meta_b["reused_existing_file"] is True
    assert meta_b["matches_regeneration"] is True
    assert [r["id"] for r in dev_a] == [r["id"] for r in dev_b]
    assert [r["id"] for r in train_a] == [r["id"] for r in train_b]


def test_split_file_refuses_a_different_corpus(tmp_path):
    """The guard that stops a result claiming a dev set it was not measured on."""
    rows = _corpus()
    path = tmp_path / "split_seed42.json"
    data_io.get_split(rows, path, "deadbeef", seed=42, dev_fraction=0.15)

    with pytest.raises(ValueError, match="different corpus"):
        data_io.get_split(rows, path, "0ther5ha", seed=42, dev_fraction=0.15)


def test_split_file_refuses_train_dev_leakage(tmp_path):
    rows = _corpus()
    path = tmp_path / "split_seed42.json"
    data_io.get_split(rows, path, "deadbeef", seed=42, dev_fraction=0.15)

    meta = json.loads(path.read_text(encoding="utf-8"))
    meta["train_ids"].append(meta["dev_ids"][0])  # a leaked example
    path.write_text(json.dumps(meta), encoding="utf-8")

    with pytest.raises(ValueError, match="leaks"):
        data_io.load_split(path, rows, "deadbeef")


# --------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------

# tp=1 fn=1 fp=0 tn=2  ->  F1_off = 2/3, F1_not = 0.8, macro = 0.7333...
Y_TRUE = ["OFF", "OFF", "NOT", "NOT"]
Y_PRED = ["OFF", "NOT", "NOT", "NOT"]


def test_metrics_match_hand_computation():
    s = evaluate.score(Y_TRUE, Y_PRED, with_ci=False)
    assert s["confusion"] == {"tp": 1, "fn": 1, "fp": 0, "tn": 2}
    assert s["off_recall"] == pytest.approx(0.5)
    assert s["off_precision"] == pytest.approx(1.0)
    assert s["off_f1"] == pytest.approx(2 / 3)
    assert s["not_f1"] == pytest.approx(0.8)
    assert s["macro_f1"] == pytest.approx((2 / 3 + 0.8) / 2)
    assert s["accuracy"] == pytest.approx(0.75)


def test_labels_outside_the_binary_set_raise():
    with pytest.raises(ValueError, match="labels outside"):
        evaluate.score(["OFF", "HATE"], ["OFF", "OFF"], with_ci=False)


def test_undefined_off_recall_is_none_not_zero():
    """No OFF examples in a slice means recall is undefined. Reporting 0.0 there
    would read as 'the model caught nothing' -- a false finding."""
    s = evaluate.score(["NOT", "NOT"], ["NOT", "OFF"], with_ci=False)
    assert s["off_recall"] is None


def test_bootstrap_is_reproducible_and_brackets_the_point_estimate():
    y_true = ["OFF"] * 50 + ["NOT"] * 50
    y_pred = ["OFF"] * 40 + ["NOT"] * 10 + ["NOT"] * 50  # OFF-recall = 0.8

    a = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=42)
    b = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=42)
    c = evaluate.bootstrap_ci(y_true, y_pred, "off_recall", n_boot=200, seed=1)

    assert (a["ci_low"], a["ci_high"]) == (b["ci_low"], b["ci_high"]), "not reproducible from the seed"
    assert (a["ci_low"], a["ci_high"]) != (c["ci_low"], c["ci_high"]), "seed had no effect"
    assert a["ci_low"] <= 0.8 <= a["ci_high"]


def test_recall_gap_ci_excludes_zero_when_the_gap_is_real():
    hit_true, hit_pred = ["OFF"] * 60, ["OFF"] * 60            # recall 1.0
    free_true = ["OFF"] * 60
    free_pred = ["NOT"] * 60                                    # recall 0.0

    gap = evaluate.bootstrap_gap_ci(hit_true, hit_pred, free_true, free_pred,
                                    metric="off_recall", n_boot=200, seed=42)
    assert gap["delta"] == pytest.approx(1.0)
    assert gap["excludes_zero"] is True


def test_recall_gap_ci_includes_zero_when_the_slices_behave_alike():
    true_a = ["OFF"] * 40 + ["NOT"] * 40
    pred_a = ["OFF"] * 30 + ["NOT"] * 10 + ["NOT"] * 40
    gap = evaluate.bootstrap_gap_ci(true_a, pred_a, list(true_a), list(pred_a),
                                    metric="off_recall", n_boot=300, seed=42)
    assert gap["delta"] == pytest.approx(0.0)
    assert gap["ci_low"] <= 0 <= gap["ci_high"]
    assert gap["excludes_zero"] is False


# --------------------------------------------------------------------------
# slice tagging must go through the frozen matcher
# --------------------------------------------------------------------------


def test_tag_slices_uses_the_frozen_root_matcher(tmp_path):
    from src import lexicon

    lex_file = tmp_path / "lex.txt"
    lex_file.write_text("aptal\n", encoding="utf-8")
    lex = lexicon.load_lexicon(lex_file)

    rows = [{"text": "aptalsın sen"}, {"text": "tamamen masum bir cumle"}]
    assert evaluate.tag_slices(rows, lex) == ["lexicon_hit", "lexicon_free"]


# --------------------------------------------------------------------------
# the runtime gate: a CPU-only build must fail at minute 0, not at minute 90
# --------------------------------------------------------------------------


def _stub_torch(version, cuda_available, device="NVIDIA L4"):
    """Minimal stand-in for torch, so the gate's logic is testable on a machine
    that has no torch at all."""
    import types

    mod = types.ModuleType("torch")
    mod.__version__ = version
    mod.cuda = types.SimpleNamespace(
        is_available=lambda: cuda_available,
        get_device_name=lambda i: device,
    )
    return mod


def test_runtime_gate_passes_on_a_cuda_build_with_a_gpu(monkeypatch):
    import phase01_baseline as drv

    monkeypatch.setitem(sys.modules, "torch", _stub_torch("2.11.0+cu124", True))
    info = drv.assert_trainable_runtime()
    assert info["cuda_available"] is True
    assert info["device_name"] == "NVIDIA L4"


def test_runtime_gate_aborts_when_no_gpu_is_visible(monkeypatch):
    import phase01_baseline as drv

    monkeypatch.setitem(sys.modules, "torch", _stub_torch("2.11.0+cu124", False))
    with pytest.raises(SystemExit, match="no CUDA device is visible"):
        drv.assert_trainable_runtime()


def test_runtime_gate_aborts_on_a_cpu_wheel_even_if_a_gpu_is_attached(monkeypatch):
    """The dangerous case: a GPU is present, so nothing looks wrong, but the
    wheel has no CUDA compiled in and every step silently runs on CPU."""
    import phase01_baseline as drv

    monkeypatch.setitem(sys.modules, "torch", _stub_torch("2.11.0+cpu", True))
    with pytest.raises(SystemExit, match=r"CPU-only build"):
        drv.assert_trainable_runtime()


def test_runtime_gate_can_be_overridden_deliberately(monkeypatch):
    import phase01_baseline as drv

    monkeypatch.setitem(sys.modules, "torch", _stub_torch("2.11.0+cpu", False))
    info = drv.assert_trainable_runtime(allow_cpu=True)
    assert info["cpu_override"] is True


# --------------------------------------------------------------------------
# the Drive mirror: a completed run only, never mock or partial output
# --------------------------------------------------------------------------


def _fake_run_dir(tmp_path, name="run", mock=False):
    d = tmp_path / name
    d.mkdir()
    payload = {"run_id": "01_baseline_berturk", "berturk": {}}
    if mock:
        payload = {"MOCK_RUN": "fabricated", **payload}
    (d / "metrics.json").write_text(json.dumps(payload), encoding="utf-8")
    (d / "classification_report.txt").write_text("report body", encoding="utf-8")
    (d / "results_log_row.md").write_text("| row |\n", encoding="utf-8")
    (d / "run_config.json").write_text('{"run_id": "01_baseline_berturk"}', encoding="utf-8")
    (d / "dev_predictions.csv").write_text("row_id,text,gold,pred,confidence,slice\n1,a,OFF,OFF,0.9,lexicon_hit\n",
                                           encoding="utf-8")
    return d


def test_mirror_copies_every_file_and_verifies_it(tmp_path):
    import phase01_baseline as drv

    src = _fake_run_dir(tmp_path)
    dst = tmp_path / "drive" / "01_baseline_berturk"

    copied = drv.mirror_outputs(src, dst)

    assert {n for n, _ in copied} == {"metrics.json", "classification_report.txt",
                                      "results_log_row.md", "run_config.json",
                                      "dev_predictions.csv"}
    for name, size in copied:
        assert (dst / name).exists()
        assert (dst / name).stat().st_size == size == (src / name).stat().st_size


def test_mirror_refuses_mock_output(tmp_path):
    """Mock numbers reaching Drive would look exactly like results."""
    import phase01_baseline as drv

    src = _fake_run_dir(tmp_path, mock=True)
    with pytest.raises(SystemExit, match="MOCK"):
        drv.mirror_outputs(src, tmp_path / "drive")
    assert not (tmp_path / "drive").exists(), "nothing may be written before the check"


@pytest.mark.parametrize("state", ["missing", "empty"])
def test_mirror_refuses_when_dev_predictions_is_lost(tmp_path, state):
    """The mirror is the ONLY surviving copy of dev_predictions.csv: it is
    gitignored and /content is wiped at session end. Reporting a successful
    mirror without it would cost a retrain to notice."""
    import phase01_baseline as drv

    src = _fake_run_dir(tmp_path, name=f"run_{state}")
    csv_file = src / "dev_predictions.csv"
    if state == "missing":
        csv_file.unlink()
    else:
        csv_file.write_text("", encoding="utf-8")

    with pytest.raises(SystemExit, match="dev_predictions.csv"):
        drv.mirror_outputs(src, tmp_path / f"drive_{state}")
    assert not (tmp_path / f"drive_{state}").exists()


def test_mirror_refuses_an_incomplete_run(tmp_path):
    import phase01_baseline as drv

    src = tmp_path / "partial"
    src.mkdir()
    (src / "classification_report.txt").write_text("half a run", encoding="utf-8")

    with pytest.raises(SystemExit, match="did not complete"):
        drv.mirror_outputs(src, tmp_path / "drive")


def test_score_by_slice_partitions_the_rows():
    y_true = ["OFF", "OFF", "NOT", "NOT"]
    y_pred = ["OFF", "NOT", "NOT", "NOT"]
    tags = ["lexicon_hit", "lexicon_free", "lexicon_hit", "lexicon_free"]

    out = evaluate.score_by_slice(y_true, y_pred, tags, n_boot=0)
    assert out["lexicon_hit"]["n"] + out["lexicon_free"]["n"] == 4
    assert out["lexicon_hit"]["off_recall"] == pytest.approx(1.0)
    assert out["lexicon_free"]["off_recall"] == pytest.approx(0.0)
