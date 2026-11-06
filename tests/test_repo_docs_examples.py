"""Every Pietto example of the user documentation checks as the page shows it.

A ```pietto block is one complete file, checked as `pietto check --check-mode
strict` checks it. With nothing after `pietto` on its opening fence line it
reports no diagnostic; otherwise the words after `pietto` are the codes it
reports, in report order (an example that shows a diagnostic, or a form that a
single file refuses, such as a project-only one). See docs/style.md,
Documentation examples. Every block is also already formatted: `pietto fmt`
leaves it unchanged. The commands of docs/worked-example.md also run as the
page shows them, over the files it names.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import shlex

import pytest

from pietto.cli import main
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, analyze
from pietto.source_format import format_source

REPO_ROOT = Path(__file__).resolve().parents[1]
DOCUMENTS = ("README.md", "docs/language.md", "docs/style.md", "docs/worked-example.md")
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


EXAMPLES = _examples()


@pytest.mark.parametrize(("source", "codes"), EXAMPLES)
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


@pytest.mark.parametrize(("source", "codes"), EXAMPLES)
def test_documented_example_is_already_formatted(source: str, codes: list[str]) -> None:
    del codes  # the shared parametrization; the codes are checked above
    result = format_source(source)
    assert result.source == source, [d.message for d in result.diagnostics]


def _bikes_contract() -> str:
    """The `contract.json` the page puts in `bikes-project` (it links its values)."""
    whole = {"kind": "int_range", "min": "0", "max": "1000000"}
    text = {
        "kind": "text",
        "max_characters": 32,
        "encoding": "UTF8",
        "collation": "C",
        "padding": "NO PAD",
    }
    kinds = {
        "Int": {"storage": {"kind": "pg_int8"}, "nullable": False, "domain": whole},
        "Text": {"storage": {"kind": "pg_text"}, "nullable": True, "domain": text},
        "Date": {
            "storage": {"kind": "pg_date"},
            "nullable": False,
            "domain": {"kind": "date"},
        },
    }
    tables = {
        "members": {"id": "Int", "plan": "Text"},
        "rides": {
            "id": "Int",
            "member_id": "Int",
            "station_id": "Int",
            "started_on": "Date",
            "fee_cents": "Int",
        },
    }
    sources = [
        {
            "selector": {"module": "bikes.pietto", "kind": "source", "name": name},
            "relation": {"namespace": "bikes", "name": name},
            "scan": "relation_rows",
            "fields": [
                {
                    "ordinal": i,
                    "name": field,
                    "column": field,
                    "representation": kinds[kind],
                }
                for i, (field, kind) in enumerate(fields.items())
            ],
            "premises": [
                {"key": key, "scope": "source", "value": True}
                for key in ("row_domain_matches", "read_only_object")
            ],
        }
        for name, fields in tables.items()
    ]
    statement = {
        "client_encoding": "UTF8",
        "operator_environment": "builtin_only",
        "identifier_case": "quoted_exact",
        "parameter_protocol": "postgres_extended",
    }
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": "postgres", "release": "18.6"},
            "sources": sources,
            "environment": [
                {"key": key, "scope": "statement", "value": value}
                for key, value in statement.items()
            ],
        },
        indent=1,
    )


def test_worked_example_commands_run_as_the_page_shows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = (REPO_ROOT / "docs/worked-example.md").read_text(encoding="utf-8")
    rides, bikes = (block.group(2) for block in BLOCK.finditer(text))
    (toml,) = re.findall(r"^```toml\n(.*?)^```$", text, re.MULTILINE | re.DOTALL)
    commands = re.findall(r"^```bash\n(.*?)^```$", text, re.MULTILINE | re.DOTALL)
    project = tmp_path / "bikes-project"
    project.mkdir()
    (tmp_path / "rides.pietto").write_text(rides, encoding="utf-8")
    (project / "pietto.toml").write_text(toml, encoding="utf-8")
    (project / "bikes.pietto").write_text(bikes, encoding="utf-8")
    (project / "contract.json").write_text(_bikes_contract(), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    lines = "".join(commands).replace("\\\n", "").splitlines()
    assert lines
    for line in lines:
        program, *argv = shlex.split(line)
        assert program == "pietto"
        assert main(argv) == 0, (line, capsys.readouterr())
