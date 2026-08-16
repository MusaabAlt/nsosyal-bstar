"""Tests for the single-use accounting on the official Çöltekin test set.

The guard is the only thing standing between "touched exactly once" and a
promise kept by memory. These tests pin its three properties:

  * it refuses without the explicit flag;
  * it refuses outright once the SPEND record exists, flag or not;
  * the OPEN log is written BEFORE the bytes are read, so a crashed run still
    leaves evidence that the resource was seen.
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
from src import data_io


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Redirect the accounting files so tests never touch the real records."""
    monkeypatch.setattr(config, "TEST_OPEN_LOG", tmp_path / "opened.json")
    monkeypatch.setattr(config, "TEST_SPEND_RECORD", tmp_path / "spent.json")
    monkeypatch.setattr(config, "COLTEKIN_TEST", tmp_path / "missing_test.tsv")
    monkeypatch.setattr(config, "COLTEKIN_GOLD", tmp_path / "missing_gold.tsv")
    return tmp_path


def test_refuses_without_the_explicit_flag(sandbox):
    with pytest.raises(PermissionError, match="Refusing to load"):
        data_io.load_coltekin_test()
    assert not config.TEST_OPEN_LOG.exists(), "a refused call must not count as an open"


def test_refuses_once_spent_even_with_the_flag(sandbox):
    config.TEST_SPEND_RECORD.write_text(json.dumps({
        "spent_at": "2026-08-16T12:00:00", "run_id": "05_final_test",
        "git_sha": "deadbeef", "results_dir": "results/05_final_test"}),
        encoding="utf-8")
    with pytest.raises(PermissionError, match="already been SPENT"):
        data_io.load_coltekin_test(run_final_test=True)
    assert not config.TEST_OPEN_LOG.exists(), "a refused call must not count as an open"


def test_spent_message_names_the_run_and_the_record(sandbox):
    config.TEST_SPEND_RECORD.write_text(json.dumps({
        "spent_at": "2026-08-16T12:00:00", "run_id": "05_final_test",
        "git_sha": "abc1234", "results_dir": "results/05_final_test"}),
        encoding="utf-8")
    with pytest.raises(PermissionError) as e:
        data_io.load_coltekin_test(run_final_test=True)
    msg = str(e.value)
    for expected in ("2026-08-16T12:00:00", "abc1234", "05_final_test",
                     "project-lead decision"):
        assert expected in msg


def test_open_log_is_written_before_the_read(sandbox):
    """The corpus file does not exist, so the read fails -- but the log must
    already be on disk. That ordering is what makes a crashed run auditable."""
    with pytest.raises(Exception) as e:
        data_io.load_coltekin_test(run_final_test=True)
    assert not isinstance(e.value, PermissionError), "should have got past the guards"
    assert config.TEST_OPEN_LOG.exists(), "open log must precede the read"
    log = json.loads(config.TEST_OPEN_LOG.read_text(encoding="utf-8"))
    assert len(log) == 1 and "opened_at" in log[0]


def test_open_log_appends_rather_than_overwrites(sandbox):
    for _ in range(3):
        with pytest.raises(Exception):
            data_io.load_coltekin_test(run_final_test=True)
    log = json.loads(config.TEST_OPEN_LOG.read_text(encoding="utf-8"))
    assert len(log) == 3, "every open must be recorded, not just the last one"


def test_accounting_paths_are_root_relative(sandbox, monkeypatch):
    """Both records must live under ROOT so they are committed and travel with a
    clone -- the same reasoning as the split file. A RESULTS_DIR-relative path
    would let a fresh Colab clone believe the test set was never spent."""
    import importlib

    monkeypatch.setenv("NSOSYAL_RESULTS", str(sandbox / "elsewhere"))
    fresh = importlib.reload(config)
    try:
        assert fresh.ROOT in fresh.TEST_SPEND_RECORD.parents
        assert fresh.ROOT in fresh.TEST_OPEN_LOG.parents
    finally:
        monkeypatch.delenv("NSOSYAL_RESULTS", raising=False)
        importlib.reload(config)
