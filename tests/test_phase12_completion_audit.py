from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import re
import subprocess
import sys
import tomllib
from collections.abc import Iterable
from pathlib import Path
from types import ModuleType
from typing import Any, cast

from _phase54_active_gate2_manifest import (  # noqa: F401
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pietto.cli as cli
import pietto.cli_json as cli_json
import pietto.sql as sql_api
from pietto.ast_nodes import Script
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, build_ir
from pietto.ir.model import OrderDirectionIR
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = "docs/plan/phase-12-sql-feature-expansion-i.md"
CONTRACT_PATH = "docs/spec/order-limit-contract-v1.md"
GOLDEN_ROOT = REPO_ROOT / "tests/fixtures/golden"
POSTGRES_INPUT = Path("tests/fixtures/phase12/postgres_order_limit_composition.pietto")
MYSQL_INPUT = Path("tests/fixtures/phase12/mysql_order_limit_composition.pietto")
POSTGRES_GOLDEN = "emit_sql_order_limit_composition.sql"
MYSQL_GOLDEN = "emit_mysql_order_limit_composition.sql"
ALL_GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"
HISTORICAL_GOLDENS_HASH = (
    "11d4343245dc18fd574999cbef5bff7c316d90975b3856ed729e8d2c1d579cf0"
)
BOUNDARY_HASH = "34ed0ea23aa6d713137d746ab914ea75a43dc6d0c8322ce420f56192ab2daed0"
GENERATED_HASH = "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1"
EXPECTED_BLOBS = {
    "scripts/validate.py": "e1607a47da34ff868ca09a128c8897a6a0dbad21",
    "scripts/check_generated.py": "51081d5337e0659e73f8666ba639c0d4c3fe3a4b",
    "scripts/check_goldens.py": "4f49ddc0a8a6836b68a83a98cc9c05389d4519a3",
    "scripts/package_smoke.py": "f490e50aacd07132948fe2fd826eb5053b5e1c59",
}
EXPECTED_GATES = (
    ("lockfile", ("uv", "lock", "--check")),
    ("format", ("uv", "run", "ruff", "format", "--check", ".")),
    ("lint", ("uv", "run", "ruff", "check", ".")),
    ("production typing", ("uv", "run", "pyright")),
    (
        "test typing",
        ("uv", "run", "pyright", "--project", "pyrightconfig.tests.json"),
    ),
    ("tests", ("uv", "run", "pytest")),
)
HISTORICAL_GOLDENS = (
    "check_sources_users_warning.json",
    "check_types.json",
    "emit_mysql_compatibility_expressions.sql",
    "emit_mysql_compatibility_literals_identifiers.sql",
    "emit_mysql_compatibility_ordering_metadata.json",
    "emit_mysql_compatibility_ordering_metadata.sql",
    "emit_sql_active_user_emails.sql",
    "emit_sql_active_users.json",
    "emit_sql_active_users.sql",
    "emit_sql_compatibility_expressions.sql",
    "emit_sql_compatibility_literals_identifiers.sql",
    "emit_sql_compatibility_ordering_metadata.sql",
)
POSTGRES_PREFIX = (
    "shape User:\n"
    "    id: Int not null\n"
    "    created_at: Int not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
)


def _load_module(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


validate = cast(
    Any,
    _load_module(
        "pietto_phase12_completion_validate",
        REPO_ROOT / "scripts/validate.py",
    ),
)
goldens = cast(
    Any,
    _load_module(
        "pietto_phase12_completion_goldens",
        REPO_ROOT / "scripts/check_goldens.py",
    ),
)


def test_phase12_plan_and_status_documents_are_complete() -> None:
    plan = _read(PLAN_PATH)
    documents = {
        "AGENTS.md": _read("AGENTS.md"),
        "docs/spec/pietto-v0.9.md": _read("docs/spec/pietto-v0.9.md"),
    }
    slice_names = (
        "Master Plan And Baseline Audit",
        "ORDER BY / LIMIT Language Contract",
        "LIMIT Vertical Slice",
        "ORDER BY Vertical Slice",
        "Composition, CLI/JSON And Goldens",
        "Completion Audit And Documentation",
    )

    assert "**Phase 12 SQL Feature Expansion I is complete.**" in plan
    for number, name in enumerate(slice_names, start=1):
        assert f"**Slice {number}: {name} is complete.**" in plan
    assert "planned only" not in plan

    combined = " ".join("\n".join(documents.values()).split())
    assert "Phase 12 SQL Feature Expansion I is complete" in combined
    assert "Slices 1 through 6 are complete" in combined
    assert PLAN_PATH in combined
    for required in (
        "static `LIMIT`",
        "input-scope `ORDER BY`",
        "reviewed PostgreSQL and MySQL composition",
        "CLI text",
        "JSON v1",
        "not an actual package release",
        "package publication",
        "versioning",
        "signing",
        "upload",
    ):
        assert required in combined


def test_order_limit_contract_records_completed_behavior_and_deferred_scope() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "Phase 12 is complete",
        "Slice 3 static `LIMIT`",
        "Slice 4 input-scope `ORDER BY`",
        "Slice 5 composition and presentation coverage",
        "Projection aliases are not members of the `ORDER BY` name-resolution scope",
        "JSON schema version 1",
        "`pietto.sql.mysql.emit_mysql_sql` as a private emitter",
        "absence of a generic public `emit_sql(...)`",
    ):
        assert required in contract

    for deferred in (
        "projection-alias ordering",
        "output-schema ordering",
        "ordinal ordering",
        "`NULLS FIRST` or `NULLS LAST`",
        "collation",
        "`OFFSET`",
        "`FETCH`",
    ):
        assert deferred in contract


def test_grammar_and_parser_keep_the_exact_phase12_surface() -> None:
    grammar = _read("grammar/Pietto.g4")
    for token in (
        "LIMIT: 'limit';",
        "ORDER: 'order';",
        "BY: 'by';",
        "ASC: 'asc';",
        "DESC: 'desc';",
        "GROUP: 'group';",
        "WINDOW: 'window';",
        "PARTITION: 'partition';",
    ):
        assert grammar.count(token) == 1
    for token in (
        "OFFSET:",
        "FETCH:",
        "NULLS:",
        "COLLATE:",
        "JOIN:",
        "HAVING:",
        "INSERT:",
        "UPDATE:",
        "DELETE:",
        "CREATE:",
        "ALTER:",
        "DROP:",
    ):
        assert token not in grammar

    accepted = parse_source(
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        id\n"
        "    limit 10\n",
        path="phase12-complete.pietto",
    )
    assert accepted.diagnostics == ()
    assert accepted.ast is not None

    ordinal = parse_source(
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        1\n",
        path="phase12-ordinal.pietto",
    )
    assert ordinal.ast is None
    assert [item.code for item in ordinal.diagnostics] == ["PIE-P1000"]

    wrong_order = parse_source(
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "    limit 10\n"
        "    order by:\n"
        "        id\n",
        path="phase12-clause-order.pietto",
    )
    assert wrong_order.ast is None
    assert wrong_order.diagnostics
    assert all(item.code == "PIE-P1000" for item in wrong_order.diagnostics)


def test_semantic_limit_and_input_scope_ordering_contracts_are_complete() -> None:
    invalid_limit = analyze(_parse(POSTGRES_PREFIX + _relation_source(limit="missing")))
    limit_errors = [
        item for item in invalid_limit.diagnostics if item.severity is Severity.ERROR
    ]
    assert [(item.code, item.message) for item in limit_errors] == [
        (
            "PIE-S2307",
            "Limit must be a static integer from 0 to 9223372036854775807",
        )
    ]

    alias_only = analyze(
        _parse(
            POSTGRES_PREFIX
            + _relation_source(
                projections=("sort_key = lower(email)",),
                order_items=("sort_key",),
            )
        )
    )
    alias_errors = [
        item for item in alias_only.diagnostics if item.severity is Severity.ERROR
    ]
    assert [(item.code, item.message) for item in alias_errors] == [
        ("PIE-S2102", "Unknown field: sort_key")
    ]

    same_spelling = _relation_ir(
        _compile(
            POSTGRES_PREFIX
            + _relation_source(
                projections=("created_at = lower(email)",),
                order_items=("created_at",),
            )
        )
    )
    expression = same_spelling.order_by[0].expression
    assert isinstance(expression, FieldRefIR)
    assert expression.name == "created_at"
    assert expression.field is not None
    assert expression.field.owner == same_spelling.source.target


def test_ir_defaults_and_direction_normalization_are_stable() -> None:
    defaults = _relation_ir(_compile(POSTGRES_PREFIX + _relation_source()))
    ordered = _relation_ir(
        _compile(POSTGRES_PREFIX + _relation_source(order_items=("created_at",)))
    )

    assert defaults.order_by == ()
    assert defaults.limit is None
    assert len(ordered.order_by) == 1
    assert ordered.order_by[0].direction is OrderDirectionIR.ASC


def test_postgres_mysql_composition_and_golden_inventory_are_locked() -> None:
    postgres = sql_api.emit_postgres_sql(_compile_file(POSTGRES_INPUT))
    mysql = emit_mysql_sql(_compile_file(MYSQL_INPUT))

    assert postgres.diagnostics == ()
    assert mysql.diagnostics == ()
    assert (postgres.artifacts[0].sql + "\n").encode("utf-8") == (
        GOLDEN_ROOT / POSTGRES_GOLDEN
    ).read_bytes()
    assert (mysql.artifacts[0].sql + "\n").encode("utf-8") == (
        GOLDEN_ROOT / MYSQL_GOLDEN
    ).read_bytes()

    inventory = tuple(path for path in GOLDEN_ROOT.iterdir() if path.is_file())
    assert len(inventory) == 37
    assert _aggregate_hash(inventory) == ALL_GOLDENS_HASH
    assert (
        _aggregate_hash(tuple(GOLDEN_ROOT / name for name in HISTORICAL_GOLDENS))
        == HISTORICAL_GOLDENS_HASH
    )
    assert goldens.audit(REPO_ROOT) == ()


def test_golden_audit_has_no_automatic_update_workflow() -> None:
    source = _read("scripts/check_goldens.py").lower()

    for forbidden in (
        "update_" + "golden",
        "approve_" + "golden",
        "rewrite_" + "golden",
        "snapshot " + "update",
        "--" + "update",
        "write_" + "text",
        "write_" + "bytes",
        "subprocess",
    ):
        assert forbidden not in source


def test_generated_guard_verifies_tracked_files_byte_for_byte(tmp_path: Path) -> None:
    result = subprocess.run(
        (sys.executable, str(REPO_ROOT / "scripts/check_generated.py")),
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "verified 8 tracked files byte-for-byte" in result.stdout
    assert (
        _aggregate_hash(
            tuple(
                path
                for path in (REPO_ROOT / "src/pietto/generated").iterdir()
                if path.is_file()
            )
        )
        == GENERATED_HASH
    )


def test_public_api_json_cli_package_and_dependency_contracts_are_unchanged() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    signature = inspect.signature(sql_api.emit_postgres_sql)
    parser = cli._build_parser()
    check = parser.parse_args(["check", "file.pietto"])
    emit = parser.parse_args(
        [
            "emit-sql",
            "file.pietto",
            "--dialect",
            "mysql",
            "--format",
            "json",
            "--output",
            "out.sql",
        ]
    )
    subparsers = next(
        action
        for action in cast(list[argparse.Action], getattr(parser, "_actions"))
        if action.dest == "command"
    )

    assert set(cast(Any, subparsers).choices) == {"check", "emit-sql", "explain"}
    assert vars(check) == {
        "command": "check",
        "path": Path("file.pietto"),
        "project": None,
        "format": "text",
    }
    assert vars(emit) == {
        "command": "emit-sql",
        "path": Path("file.pietto"),
        "dialect": "mysql",
        "output": Path("out.sql"),
        "format": "json",
    }
    assert project["project"]["version"] == "0.1.0"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert "sqlglot" not in _read("uv.lock").lower()
    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert cli_json._SCHEMA_VERSION == 1


def test_phase11_authoritative_gates_and_ci_are_unchanged() -> None:
    for path, expected_hash in EXPECTED_BLOBS.items():
        assert _git_blob_hash(REPO_ROOT / path) == expected_hash
    assert validate.GATES == EXPECTED_GATES

    workflow = _read(".github/workflows/ci.yml")
    commands = tuple(
        re.findall(r"(?m)^        run: (uv run python scripts/.+)$", workflow)
    )
    assert commands == (
        "uv run python scripts/validate.py --timings --pytest-workers auto --pytest-dist loadfile --pytest-maxprocesses 4",
        "uv run python scripts/check_generated.py",
        "uv run python scripts/check_goldens.py",
        "uv run python scripts/package_smoke.py",
    )
    assert re.findall(r'(?m)^          - "(3\.\d+)"$', workflow) == [
        "3.12",
        "3.13",
    ]


def test_production_compiler_and_configuration_boundary_is_unchanged() -> None:
    paths = [
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar/Pietto.g4",
    ]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    )

    assert _aggregate_hash(paths) == BOUNDARY_HASH


def test_phase_level_non_goals_suffix_and_diagnostics_remain_locked() -> None:
    plan = _normalized(PLAN_PATH)
    runtime = _runtime_text().lower()
    repository = _repository_text()

    for required in (
        "projection-alias ordering",
        "ordinal ordering",
        "null-order controls",
        "collations",
        "offset",
        "fetch",
        "joins",
        "grouping",
        "aggregates",
        "windows",
        "CTEs",
        "subqueries",
        "DDL",
        "DML",
        "SQL execution",
        "database or connector connections",
        "schema introspection",
        "project or multi-file mode",
        "`pietto.toml`",
        "watch mode",
        "LSP/editor support",
        "Web UI",
        "online playground",
        "JSON v2",
        "SQLGlot",
        "package version bump",
    ):
        assert required in plan

    assert re.search(r"\." + "pie" + r"\b", repository) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository) is None
    assert "sqlglot" not in runtime
    assert not (REPO_ROOT / "pietto.toml").exists()
    for module_name in (
        "database.py",
        "executor.py",
        "lsp.py",
        "runtime.py",
        "server.py",
        "watch.py",
    ):
        assert not (REPO_ROOT / "src/pietto" / module_name).exists()


def _relation_source(
    *,
    projections: tuple[str, ...] = ("id",),
    order_items: tuple[str, ...] = (),
    limit: str | None = None,
) -> str:
    order_clause = ""
    if order_items:
        order_clause = "    order by:\n" + "".join(
            f"        {item}\n" for item in order_items
        )
    limit_clause = "" if limit is None else f"    limit {limit}\n"
    return (
        "query selected:\n"
        "    from users\n"
        "    select:\n"
        + "".join(f"        {projection}\n" for projection in projections)
        + order_clause
        + limit_clause
    )


def _parse(source: str) -> Script:
    result = parse_source(source, path="phase12-completion.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _compile(source: str) -> ScriptIR:
    script = _parse(source)
    semantic_result = analyze(script)
    assert not [
        item for item in semantic_result.diagnostics if item.severity is Severity.ERROR
    ]
    result = build_ir(script, semantic_result.model)
    assert result.diagnostics == ()
    assert result.ir is not None
    return result.ir


def _compile_file(relative_path: Path) -> ScriptIR:
    result = parse_file(REPO_ROOT / relative_path)
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic_result = analyze(result.ast)
    assert not [
        item for item in semantic_result.diagnostics if item.severity is Severity.ERROR
    ]
    ir_result = build_ir(result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _relation_ir(script_ir: ScriptIR) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


def _aggregate_hash(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        if not path.is_file():
            continue
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_blob_hash(path: Path) -> str:
    content = path.read_bytes()
    return hashlib.sha1(f"blob {len(content)}\0".encode() + content).hexdigest()


def _runtime_text() -> str:
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    )


def _repository_text() -> str:
    paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
    ]
    for directory in ("src", "tests", "docs", "examples", "grammar", ".github"):
        paths.extend(
            path
            for path in (REPO_ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix
            in {".py", ".md", ".pietto", ".json", ".sql", ".toml", ".g4", ".yml"}
        )
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(set(paths)))


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
