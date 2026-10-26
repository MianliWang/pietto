"""Every Pietto example of the user documentation checks as the page shows it.

A ```pietto block is one complete file, checked as `pietto check --check-mode
strict` checks it. With nothing after `pietto` on its opening fence line it
reports no diagnostic; otherwise the words after `pietto` are the codes it
reports, in report order (an example that shows a diagnostic, or a form that a
single file refuses, such as a project-only one). See docs/development.md.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, analyze

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("README.md", "docs/language.md", "docs/style.md")
BLOCK = re.compile(r"^```pietto([^\n]*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def _examples() -> list[object]:
    examples: list[object] = []
    for name in DOCUMENTS:
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        blocks = list(BLOCK.finditer(text))
        assert len(blocks) == text.count("```pietto"), f"{name}: unchecked fence"
        for block in blocks:
            where = f"{name}:{text.count(chr(10), 0, block.start()) + 1}"
            codes = block.group(1).split()
            examples.append(pytest.param(block.group(2), codes, id=where))
    return examples


@pytest.mark.parametrize(("source", "codes"), _examples())
def test_documented_example_reports_exactly_its_marked_codes(
    source: str, codes: list[str]
) -> None:
    parsed = parse_source(source)
    diagnostics = list(parsed.diagnostics)
    errors = [d for d in diagnostics if d.severity is Severity.ERROR]
    if parsed.ast is not None and not errors:
        result = analyze(parsed.ast, mode_override=CheckMode.STRICT)
        diagnostics += result.diagnostics
    assert [d.code for d in diagnostics] == codes, [d.message for d in diagnostics]
