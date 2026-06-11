from pathlib import Path

import pytest

from pietto.parser_api import parse_file


EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
assert EXAMPLE_PATHS, "Expected at least one committed Pietto example."


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_committed_example_parses(path: Path) -> None:
    result = parse_file(path)

    assert result.diagnostics == ()
    assert result.ast is not None
