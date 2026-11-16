from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

import pietto.cli as cli

REPO_ROOT = Path(__file__).resolve().parents[1]
OFFICIAL_SOURCE_SUFFIX = ".pietto"
FORMER_SOURCE_SUFFIX = "." + "p" + "i" + "e"
TEXT_SUFFIXES = {
    ".g4",
    ".json",
    ".md",
    ".pietto",
    ".py",
    ".toml",
    ".txt",
}
CODE_SUFFIXES = {".g4", ".md", ".pietto", ".py", ".txt"}


def test_pyright_gate_targets_handwritten_production_source() -> None:
    config_text = _read("pyrightconfig.json")
    config = json.loads(re.sub(r",(\s*[}\]])", r"\1", config_text))

    assert config == {
        "include": ["src/pietto"],
        "exclude": ["src/pietto/generated"],
        "ignore": ["src/pietto/generated"],
        "extraPaths": ["src"],
        "venvPath": ".",
        "venv": ".venv",
        "pythonVersion": "3.12",
        "typeCheckingMode": "standard",
    }
    assert "tests" not in config["include"]


def test_pylance_ignores_only_generated_antlr_diagnostics() -> None:
    settings = json.loads(_read(".vscode/settings.json"))

    assert settings == {
        "python.analysis.exclude": ["src/pietto/generated/**"],
        "python.analysis.ignore": ["src/pietto/generated/**"],
    }
    assert "python.analysis.typeCheckingMode" not in settings
    assert "python.analysis.diagnosticSeverityOverrides" not in settings


def test_official_examples_and_source_fixtures_use_pietto_suffix() -> None:
    examples = tuple(
        path for path in (REPO_ROOT / "examples").rglob("*") if path.is_file()
    )
    postgres_fixtures = tuple(
        path
        for path in (REPO_ROOT / "tests" / "fixtures" / "postgres").rglob("*")
        if path.is_file()
    )

    assert examples
    assert len(postgres_fixtures) == 4
    assert all(path.suffix == OFFICIAL_SOURCE_SUFFIX for path in examples)
    assert all(path.suffix == OFFICIAL_SOURCE_SUFFIX for path in postgres_fixtures)


def test_repository_contains_no_former_source_suffix_or_bare_diagnostic_codes() -> None:
    legacy_paths = tuple(
        path.relative_to(REPO_ROOT)
        for path in REPO_ROOT.rglob(f"*{FORMER_SOURCE_SUFFIX}")
        if ".git" not in path.parts and "__pycache__" not in path.parts
    )
    assert legacy_paths == ()

    legacy_reference = re.compile(re.escape(FORMER_SOURCE_SUFFIX) + r"(?=\b|\")")
    # Every diagnostic code is written with its PIE- prefix.
    bare_code = re.compile(r"(?<!PIE-)\b[PSIB][0-9]{4}\b")
    matches: list[Path] = []
    bare_codes: list[tuple[Path, str]] = []
    roots = (
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / ".vscode",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "pyrightconfig.json",
        REPO_ROOT / "docs",
        REPO_ROOT / "examples",
        REPO_ROOT / "grammar",
        REPO_ROOT / "src",
        REPO_ROOT / "tests",
    )
    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if (
                not path.is_file()
                or "__pycache__" in path.parts
                or path.suffix not in TEXT_SUFFIXES
            ):
                continue
            text = path.read_text(encoding="utf-8")
            if legacy_reference.search(text):
                matches.append(path.relative_to(REPO_ROOT))
            if path.suffix in CODE_SUFFIXES:
                bare_codes.extend(
                    (path.relative_to(REPO_ROOT), match.group())
                    for match in bare_code.finditer(text)
                )
    assert matches == []
    assert bare_codes == []


def test_current_user_facing_commands_use_pietto_suffix() -> None:
    readme = _read("README.md")

    readme_commands = {
        line.removeprefix("uv run ")
        for block in re.findall(r"```bash\n(.*?)\n```", readme, flags=re.DOTALL)
        for line in block.splitlines()
    }

    assert "pietto check shop.pietto" in readme_commands
    assert "pietto emit-sql shop.pietto --dialect postgres" in readme_commands


def test_cli_remains_path_based_for_nonstandard_suffix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "source.txt"
    path.write_text(
        """
shape User:
    id: Int

source users: User = postgres.table("users")

table all_users:
    from users
    select:
        id
""".lstrip(),
        encoding="utf-8",
    )

    assert cli.main(["check", str(path)]) == 0
    checked = capsys.readouterr()
    assert checked.out == f"OK: {path}\n"
    assert checked.err == ""

    assert cli.main(["emit-sql", str(path), "--dialect", "postgres"]) == 0
    emitted = capsys.readouterr()
    assert emitted.err == ""
    assert emitted.out == '-- all_users\nSELECT\n    "id" AS "id"\nFROM "users";\n'


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        (None, 0),
        (0, 0),
        (2, 2),
        ("message", 1),
    ],
)
def test_system_exit_codes_are_normalized(code: object, expected: int) -> None:
    assert cli._system_exit_code(SystemExit(code)) == expected


# AD78.03: each third dialect has its own adapter, and the PostgreSQL/MySQL
# pipeline never receives its family.
ADAPTER_FAMILIES = ("duckdb", "sqlite")
PIPELINE_FAMILIES = {"postgres", "mysql"}
# Each adapter family's own source connector.
_CONNECTORS = {"duckdb": "duckdb.arrow", "sqlite": "sqlite.table"}
_FIREWALL_MODULE = """shape Order:
    id: Int
    amount: Int

source orders: Order = CONNECTOR("orders")
source rows: Order = postgres.table("orders")

query own_rows:
    from orders
    select:
        id

query table_rows:
    from rows
    select:
        id
"""
# A single file of a source it knows, so its emission reaches the emitter.
_FIREWALL_FILE = """shape Order:
    id: Int
    amount: Int

source rows: Order = postgres.table("orders")

query table_rows:
    from rows
    select:
        id
"""


def _firewall_contract(family: str) -> str:
    """A contract of `family` for the source of that family's own spelling."""

    postgres = family == "postgres"
    domain = {"kind": "int_range", "min": "-1", "max": "1"}
    storage, namespace = {
        "postgres": ("pg_int8", "public"),
        "duckdb": ("arrow_int64", "arrow"),
        "sqlite": ("sqlite_integer", "main"),
    }[family]
    representation = {
        "storage": {"kind": storage},
        "nullable": False,
        "domain": domain,
    }
    encoding = "UTF-8" if family == "sqlite" else "UTF8"
    environment = [{"key": "client_encoding", "scope": "statement", "value": encoding}]
    if postgres:
        environment.append(
            {"key": "identifier_case", "scope": "statement", "value": "quoted_exact"}
        )
    source = {
        "selector": {
            "module": "main.pietto",
            "kind": "source",
            "name": "rows" if postgres else "orders",
        },
        "relation": {"namespace": namespace, "name": "orders"},
        "scan": "arrow_registration" if family == "duckdb" else "relation_rows",
        "fields": [
            {
                "ordinal": i,
                "name": name,
                "column": name,
                "representation": representation,
            }
            for i, name in enumerate(("id", "amount"))
        ],
        "premises": [
            {"key": key, "scope": "source", "value": True}
            for key in ("row_domain_matches", "read_only_object")
        ],
    }
    releases = {"postgres": "18.6", "duckdb": "2.0.0", "sqlite": "3.53.1"}
    return json.dumps(
        {
            "format": "pietto.emission-contract.v1",
            "target": {"family": family, "release": releases[family]},
            "sources": [source],
            "environment": environment,
        }
    )


def test_postgres_mysql_tables_admit_no_adapter_family() -> None:
    from pietto import sql as sql_api
    from pietto._project import project_sql_emission_contract as contract
    from pietto._project import project_sql_emission_portable_schema as schema
    from pietto.sql import mysql as mysql_backend

    # The contract reader, the emitter and the artifact verifier admit a family
    # by these tables, and their family branches assume one of the two.
    for table in (contract.RELEASES, schema.FAMILIES, schema.QUOTES, schema.PHYSICAL):
        assert not set(table) & set(ADAPTER_FAMILIES)
    pipeline = {sql_api.emit_postgres_sql, mysql_backend.emit_mysql_sql}
    for family in ADAPTER_FAMILIES:
        assert cli._select_sql_emitter(family) not in pipeline


def _error_kinds(value: object) -> set[str]:
    """Every `cli_errors` kind in a project emission or batch document."""

    if isinstance(value, dict):
        kinds = {error["kind"] for error in value.get("cli_errors", ())}
        return kinds.union(*map(_error_kinds, value.values()))
    if isinstance(value, list):
        return set().union(*map(_error_kinds, value))
    return set()


@pytest.mark.parametrize("family", ADAPTER_FAMILIES)
def test_no_adapter_family_reaches_the_postgres_mysql_pipeline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, family: str
) -> None:
    from pietto import compiler, execution
    from pietto import sql as sql_api
    from pietto._project import project_execution_template as template
    from pietto._project import project_sql_emission_cli as emission_cli
    from pietto.sql import mysql as mysql_backend

    serving: list[str] = []  # the dialect of the request being driven
    calls: list[tuple[str, str]] = []  # (serving dialect, entry) per entry call
    families: list[object] = []

    def family_of(item: object) -> object:
        return getattr(getattr(item, "request", item), "family", None)

    def spy(owner: object, name: str) -> None:
        original = getattr(owner, name)

        def recorded(*arguments: Any, **keywords: Any) -> Any:
            calls.append((serving[-1], name))
            result = original(*arguments, **keywords)
            families.extend(
                family_of(item) for item in (*arguments, *keywords.values(), result)
            )
            return result

        monkeypatch.setattr(owner, name, recorded)

    # The entries of the project pipeline, and the single-file emitters that
    # `cli._select_sql_emitter` returns.
    entries = (
        (emission_cli, "prepare_project_sql_emission"),
        (emission_cli, "realize_project_sql"),
        (template, "prepare_live_template"),
        (sql_api, "emit_postgres_sql"),
        (mysql_backend, "emit_mysql_sql"),
    )
    for owner, name in entries:
        spy(owner, name)
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (root / "main.pietto").write_text(
        _FIREWALL_MODULE.replace("CONNECTOR", _CONNECTORS[family]), encoding="utf-8"
    )
    (root / "own.json").write_text(_firewall_contract(family), encoding="utf-8")
    (root / "postgres.json").write_text(
        _firewall_contract("postgres"), encoding="utf-8"
    )
    single = tmp_path / "single.pietto"
    single.write_text(_FIREWALL_FILE, encoding="utf-8")
    documents: dict[str, list[object]] = {family: [], "postgres": []}
    refusals: dict[str, list[tuple[str, str | None]]] = {family: [], "postgres": []}
    for dialect in (family, "postgres"):
        serving.append(dialect)
        for contract in ("own.json", "postgres.json"):
            for name in ("own_rows", "table_rows"):
                selected = {"module": "main.pietto", "kind": "query", "name": name}
                for output in ("json", "text"):
                    result = emission_cli.run_project_emit_sql(
                        [f"--project={root}"]
                        + [f"--{key}={value}" for key, value in selected.items()]
                        + [f"--dialect={dialect}", f"--emission-contract={contract}"]
                        + [f"--format={output}"]
                    )
                    if output == "json":
                        documents[dialect].append(json.loads(result.stdout))
                emission = compiler.compile_sql(
                    root, **selected, dialect=dialect, emission_contract=contract
                )
                documents[dialect].append(json.loads(emission.document))
                try:
                    execution.compile_query(
                        root,
                        **selected,
                        dialect=dialect,
                        emission_contract=contract,
                    )
                except execution.CompileRejected:
                    pass
                except execution.RequestRejected as refused:
                    refusals[dialect].append((refused.code, refused.detail))
            emission = compiler.compile_all_sql(
                root, dialect=dialect, emission_contract=contract
            )
            documents[dialect].append(json.loads(emission.document))
    for dialect in (family, "postgres", "mysql"):
        serving.append(dialect)
        for output in ("json", "text"):
            cli.main(
                ["emit-sql", str(single), f"--dialect={dialect}", f"--format={output}"]
            )
    # Every entry ran for the control dialects, so each spy is live.
    assert {name for dialect, name in calls if dialect in PIPELINE_FAMILIES} == {
        name for _, name in entries
    }
    # No entry ran for the adapter family's requests, and no pipeline object
    # carries its family: a postgres request whose contract names it is
    # refused by the contract reader, and the family goes no further.
    assert [call for call in calls if call[0] == family] == []
    assert set(families) - {None} <= PIPELINE_FAMILIES
    # AD78.03 admits `duckdb` and PL.47 `sqlite` as project dialects, so
    # their requests passed the argument checks and their own adapters
    # verified them, `compile_query` included.
    assert "usage" not in _error_kinds(documents["postgres"])
    assert refusals["postgres"] == []
    assert "usage" not in _error_kinds(documents[family])
    statuses = {d["status"] for d in documents[family] if isinstance(d, dict)}
    assert "VERIFIED" in statuses
    assert refusals[family] == []


# PL.47: from the PostgreSQL/MySQL emission modules the SQLite adapter imports
# only these names, the ones the DuckDB adapter imported when PL.47 was
# answered; those modules branch on the family, so it never passes one.
_SQLITE_PIPELINE_NAMES = {
    "pietto._project.project_sql_emission_contract": {
        *("MAX_DEPTH", "MAX_FIELDS", "MAX_INPUT_BYTES", "MAX_SOURCES"),
        *("MAX_ARTIFACT_BYTES", "MAX_NODES", "MAX_PARAMETERS", "MAX_SQL_BYTES"),
        *("CODES", "InputError", "Premise", "Blocker", "canonical", "unique_pairs"),
        *("_domain", "_error", "_finite", "_integer", "_nonfinite", "_object"),
        *("_selector", "_text", "validate_resolved_premise"),
    },
    "pietto._project.project_sql_emission_scopes": {"reference_source_ports"},
    "pietto._project.project_sql_emission_suggestions": {"blocker_suggestion"},
}


def test_the_sqlite_adapter_imports_only_its_pipeline_whitelist() -> None:
    import ast
    import importlib.util

    package = REPO_ROOT / "src/pietto/_project"
    paths = sorted(package.glob("project_sqlite_*.py"))
    assert package / "project_sqlite_emission.py" in paths
    imported: dict[str, set[str]] = {}
    calls = []
    for path in paths:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
                assert not [n for n in names if "project_sql_emission" in n], path
            elif isinstance(node, ast.ImportFrom):
                # A relative import is checked as the absolute name it reads.
                module = importlib.util.resolve_name(
                    "." * node.level + (node.module or ""), "pietto._project"
                )
                names = [alias.name for alias in node.names]
                assert not [n for n in names if n.startswith("project_sql_emission")]
                if module.startswith("pietto._project.project_sql_emission"):
                    imported.setdefault(module, set()).update(names)
                for read in (module, *(f"{module}.{n}" for n in names)):
                    assert not read.startswith("pietto.sql"), (path, read)
                    assert "duckdb" not in read, (path, read)
            elif (
                isinstance(node, ast.Call)
                and getattr(node.func, "id", None) == "blocker_suggestion"
            ):
                calls.append(node)
    for module, names in imported.items():
        assert names <= _SQLITE_PIPELINE_NAMES.get(module, set()), module
    # Every suggestion is asked for with no family.
    assert calls and all(
        len(call.args) == 3
        and isinstance(call.args[2], ast.Constant)
        and call.args[2].value is None
        for call in calls
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")
