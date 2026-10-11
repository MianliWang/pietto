from __future__ import annotations

from pathlib import Path
import re


TESTS_ROOT = Path(__file__).resolve().parent
LATER_PHASE = re.compile(r"phase(69|[7-9]\d|\d{3,})")


def test_new_test_files_are_not_named_after_a_later_phase_or_a_slice() -> None:
    names = sorted(path.name for path in TESTS_ROOT.glob("test_*.py"))
    assert names
    assert [
        name
        for name in names
        if LATER_PHASE.search(name) or name.startswith("test_slice")
    ] == []
