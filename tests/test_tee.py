"""Tests for the phase-05 stdout tee.

Written after the real failure: transformers calls `sys.stdout.isatty()` while
reporting checkpoint loading, and the first Tee implemented only write/flush.
The AttributeError landed AFTER the official test set had been opened, which is
the most expensive place in the project to discover a missing method.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from phase05_final_test import Tee


def test_writes_to_both_stream_and_file(tmp_path, capsys):
    p = tmp_path / "out.txt"
    t = Tee(sys.stdout, p)
    t.write("hello\n")
    t.flush()
    t.close()
    assert p.read_text(encoding="utf-8") == "hello\n"
    assert "hello" in capsys.readouterr().out


def test_isatty_is_false_so_colour_codes_never_reach_the_file(tmp_path):
    t = Tee(sys.stdout, tmp_path / "o.txt")
    try:
        assert t.isatty() is False
    finally:
        t.close()


def test_unknown_attributes_delegate_to_the_real_stream(tmp_path):
    """The regression: any attribute a library asks for must resolve."""
    t = Tee(sys.stdout, tmp_path / "o.txt")
    try:
        for attr in ("encoding", "errors", "writable", "readable", "seekable"):
            assert hasattr(t, attr), f"Tee does not expose {attr}"
        assert callable(t.writable)
    finally:
        t.close()


def test_write_returns_character_count(tmp_path):
    t = Tee(sys.stdout, tmp_path / "o.txt")
    try:
        assert t.write("abcd") == 4
    finally:
        t.close()
