"""Every Pietto example of the user documentation checks as the page shows it.

A ```pietto block is one complete file, checked as `pietto check --check-mode
strict` checks it. With nothing after `pietto` on its opening fence line it
reports no diagnostic; otherwise the words after `pietto` are the codes it
reports, in report order (an example that shows a diagnostic, or a form that a
single file refuses, such as a project-only one). See docs/style.md,
Documentation examples. Every block of README.md, docs/*.md and the
release-note fragments docs/release-notes.d/*.md is also already formatted:
`pietto fmt --check` accepts it. The commands of
docs/worked-example.md also run as the page shows them, over the files it
names, and its two modules compile to the SQL of the same declarations in one
module.
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
FORMATTED = (
    "README.md",
    *sorted(f"docs/{path.name}" for path in REPO_ROOT.glob("docs/*.md")),
    *sorted(
        f"docs/release-notes.d/{path.name}"
        for path in REPO_ROOT.glob("docs/release-notes.d/*.md")
    ),
)
BLOCK = re.compile(r"^```pietto([^\n]*)\n(.*?)^```$", re.MULTILINE | re.DOTALL)


def _examples(names: tuple[str, ...]) -> list[object]:
    examples: list[object] = []
    for name in names:
        text = (REPO_ROOT / name).read_text(encoding="utf-8")
        blocks = list(BLOCK.finditer(text))
        assert len(blocks) == text.count("```pietto"), f"{name}: unchecked fence"
        for block in blocks:
            where = f"{name}:{text.count(chr(10), 0, block.start()) + 1}"
            codes = block.group(1).split()
            examples.append(pytest.param(block.group(2), codes, id=where))
    return examples


@pytest.mark.parametrize(("source", "codes"), _examples(DOCUMENTS))
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


@pytest.mark.parametrize(("source", "codes"), _examples(FORMATTED))
def test_documented_example_is_already_formatted(source: str, codes: list[str]) -> None:
    del codes  # the shared parametrization; the codes are checked above
    result = format_source(source)
    assert result.source == source, [d.message for d in result.diagnostics]


BIKES_TABLES = {
    "members": {"id": "Int", "plan": "Text | None"},
    "rides": {
        "id": "Int",
        "member_id": "Int",
        "station_id": "Int",
        "started_on": "Date",
        "fee_cents": "Int",
    },
}
# The two-module part's tables, in `models.pietto`.
MODULE_TABLES = {
    "members": {"id": "Int", "name": "Text"},
    "rides": {"id": "Int", "member_id": "Int", "minutes": "Int"},
}


def _bikes_contract(
    module: str = "bikes.pietto",
    tables: dict[str, dict[str, str]] = BIKES_TABLES,
    family: str = "postgres",
) -> str:
    """A `contract.json` the page puts beside a project's `pietto.toml` (it
    links its values): ``tables`` of ``module``, by declared field type."""
    pg = family == "postgres"
    whole = {"kind": "int_range", "min": "0", "max": "1000000"}
    text = {
        "kind": "text",
        "max_characters": 32,
        "encoding": "UTF8" if pg else "utf8mb4",
        "collation": "C" if pg else "utf8mb4_0900_bin",
        "padding": "NO PAD",
    }
    texts = {"kind": "pg_text"} if pg else {"kind": "my_varchar", "length": 32}
    kinds = {
        "Int": {
            "storage": {"kind": "pg_int8" if pg else "my_bigint"},
            "nullable": False,
            "domain": whole,
        },
        "Text": {"storage": texts, "nullable": False, "domain": text},
        "Text | None": {"storage": texts, "nullable": True, "domain": text},
        "Date": {
            "storage": {"kind": "pg_date"},
            "nullable": False,
            "domain": {"kind": "date"},
        },
    }
    sources = [
        {
            "selector": {"module": module, "kind": "source", "name": name},
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
    statement = (
        {
            "client_encoding": "UTF8",
            "operator_environment": "builtin_only",
            "identifier_case": "quoted_exact",
            "parameter_protocol": "postgres_extended",
        }
        if pg
        else {
            "client_encoding": "utf8mb4",
            "operator_environment": "builtin_only",
            "identifier_case": "lower_case_table_names=0",
            "parameter_protocol": "mysql_prepared",
        }
    )
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": family, "release": "18.6" if pg else "8.4.12"},
            "sources": sources,
            "environment": [
                {"key": key, "scope": "statement", "value": value}
                for key, value in statement.items()
            ],
        },
        indent=1,
    )


def _project(root: Path, toml: str, modules: dict[str, str], contract: str) -> Path:
    root.mkdir()
    (root / "pietto.toml").write_text(toml, encoding="utf-8")
    for name, source in modules.items():
        (root / name).write_text(source, encoding="utf-8")
    (root / "contract.json").write_text(contract, encoding="utf-8")
    return root


def test_worked_example_commands_run_as_the_page_shows(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    text = (REPO_ROOT / "docs/worked-example.md").read_text(encoding="utf-8")
    rides, bikes, models, report = (block.group(2) for block in BLOCK.finditer(text))
    (toml,) = re.findall(r"^```toml\n(.*?)^```$", text, re.MULTILINE | re.DOTALL)
    commands = re.findall(r"^```bash\n(.*?)^```$", text, re.MULTILINE | re.DOTALL)
    (tmp_path / "rides.pietto").write_text(rides, encoding="utf-8")
    _project(
        tmp_path / "bikes-project", toml, {"bikes.pietto": bikes}, _bikes_contract()
    )
    _project(
        tmp_path / "bikes-modules",
        toml,
        {"models.pietto": models, "report.pietto": report},
        _bikes_contract("models.pietto", MODULE_TABLES),
    )
    monkeypatch.chdir(tmp_path)
    lines = "".join(commands).replace("\\\n", "").splitlines()
    assert lines
    for line in lines:
        program, *argv = shlex.split(line)
        assert program == "pietto"
        assert main(argv) == 0, (line, capsys.readouterr())


@pytest.mark.parametrize("family", ("postgres", "mysql"))
def test_the_two_module_example_has_the_sql_of_one_module(
    tmp_path: Path, family: str
) -> None:
    """Each query of the page's two modules compiles to the SQL of the same
    declarations in one module (the def and the relationship moved, the
    imports and exports dropped), on PostgreSQL and, with `mysql.table`
    sources, on MySQL; the live template and a bundle that export_bundle wrote
    and load_bundle read bind to that SQL."""
    from pietto import execution
    from pietto._project.project_execution_template import bind_values

    text = (REPO_ROOT / "docs/worked-example.md").read_text(encoding="utf-8")
    *_, models, report = (block.group(2) for block in BLOCK.finditer(text))
    (toml,) = re.findall(r"^```toml\n(.*?)^```$", text, re.MULTILINE | re.DOTALL)
    models = models.replace("postgres.table", f"{family}.table")
    one = models.partition(")\n\n")[2] + "\n" + report.partition(")\n\n")[2]
    projects = {
        "report.pietto": _project(
            tmp_path / "two",
            toml,
            {"models.pietto": models, "report.pietto": report},
            _bikes_contract("models.pietto", MODULE_TABLES, family),
        ),
        "one.pietto": _project(
            tmp_path / "one",
            toml,
            {"one.pietto": one},
            _bikes_contract("one.pietto", MODULE_TABLES, family),
        ),
    }
    names = re.findall(r"^query (\w+):", report, re.MULTILINE)
    assert names == ["ride_bands", "rides_per_member", "member_ride_counts"]
    for name in names:
        two, local = (
            execution.compile_query(
                root,
                module=module,
                kind="query",
                name=name,
                dialect=family,
                emission_contract="contract.json",
            )
            for module, root in projects.items()
        )
        assert two.emission is not None and local.emission is not None
        sql = json.loads(two.emission)["sql"]
        assert json.loads(local.emission)["sql"] == sql
        bundle = execution.export_bundle(two)
        loaded = execution.load_bundle(
            bundle.payload,
            expected_pin=bundle.pin,
            accepted_producer=bundle.producer,
            accepted_compatibility=bundle.compatibility,
        )
        for query in (two, loaded):
            bound = bind_values(query._template, ())
            assert bound.artifact.rendered.sql == sql.encode()
