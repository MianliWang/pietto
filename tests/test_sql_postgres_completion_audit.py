from __future__ import annotations

import inspect
import re
from dataclasses import replace
from pathlib import Path

import pytest

import pietto.ir as ir_api
import pietto.parser_api as parser_api
import pietto.semantic as semantic_api
import pietto.sql as sql_api
from pietto.errors import Diagnostic, Severity
from pietto.ir import CallIR, RelationIR, ScriptIR, SourceIR, build_ir
from pietto.parser_api import parse_file, parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, SqlResult, emit_postgres_sql

EXAMPLE_PATHS = tuple(sorted(Path("examples").rglob("*.pietto")))
assert len(EXAMPLE_PATHS) == 10

PIPELINE_SOURCE = (
    "type Email = Text not null\n"
    "enum Status:\n"
    "    active\n"
    "constraint valid_email(email: Text not null) -> Bool not null:\n"
    "    email is not null\n"
    "derive normalize_email(email: Text not null) -> Text not null:\n"
    "    lower(trim(email))\n"
    "shape User:\n"
    "    id: UUID not null\n"
    "    email: Text not null\n"
    "    active: Bool not null\n"
    'source users: User is postgres.table("users")\n'
    "table active_users:\n"
    "    from users\n"
    "    where active == true\n"
    "    select:\n"
    "        id\n"
    "        normalized_email = lower(trim(email))\n"
    "query active_user_emails:\n"
    "    from active_users\n"
    '    where matches(normalized_email, "@")\n'
    "    select:\n"
    "        normalized_email\n"
)


def test_public_sql_api_is_complete_and_internal_helpers_stay_private() -> None:
    assert sql_api.__all__ == [
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    ]
    assert all(hasattr(sql_api, name) for name in sql_api.__all__)
    for internal in (
        "quote_identifier",
        "render_expression_sql",
        "render_relation_sql",
        "_unsupported_definition_diagnostic",
    ):
        assert not hasattr(sql_api, internal)
    assert not hasattr(ir_api, "compile_to_ir")


def test_sql_entry_point_accepts_script_ir_without_running_earlier_stages(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script_ir = _compile_ir(PIPELINE_SOURCE)

    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("SQL emission must consume ScriptIR directly")

    monkeypatch.setattr(parser_api, "parse_source", unexpected_call)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(ir_api, "build_ir", unexpected_call)

    result = emit_postgres_sql(script_ir)

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert result.diagnostics == ()


def test_empty_and_metadata_only_ir_are_successful_noops() -> None:
    full_ir = _compile_ir(PIPELINE_SOURCE)
    users = _source(full_ir, "users")
    invalid_users = replace(
        users,
        connector=replace(users.connector, name="unsupported.table"),
    )
    metadata_ir = ScriptIR(
        definitions=tuple(
            invalid_users if definition is users else definition
            for definition in full_ir.definitions
            if not isinstance(definition, RelationIR)
        )
    )

    assert emit_postgres_sql(ScriptIR(definitions=())) == SqlResult((), ())
    assert emit_postgres_sql(metadata_ir) == SqlResult((), ())


def test_current_mvp_pipeline_emits_stable_ordered_relation_sql() -> None:
    result = emit_postgres_sql(_compile_ir(PIPELINE_SOURCE))

    assert [
        (artifact.name, artifact.kind, artifact.sql) for artifact in result.artifacts
    ] == [
        (
            "active_users",
            SqlArtifactKind.RELATION,
            "SELECT\n"
            '    "id" AS "id",\n'
            '    lower(trim("email")) AS "normalized_email"\n'
            'FROM "users"\n'
            'WHERE "active" = TRUE',
        ),
        (
            "active_user_emails",
            SqlArtifactKind.RELATION,
            "SELECT\n"
            '    "normalized_email" AS "normalized_email"\n'
            'FROM "active_users"\n'
            "WHERE \"normalized_email\" ~ '@'",
        ),
    ]
    assert result.diagnostics == ()


def test_supported_artifacts_and_ordered_backend_diagnostics_can_coexist() -> None:
    script_ir = _compile_ir(
        PIPELINE_SOURCE + 'source backup: User is postgres.table("backup")\n'
        "table bad_connector:\n"
        "    from backup\n"
        "    select:\n"
        "        email\n"
        "query bad_expression:\n"
        "    from active_users\n"
        "    select:\n"
        "        normalized = lower(normalized_email)\n"
    )
    backup = _source(script_ir, "backup")
    bad_expression = _relation(script_ir, "bad_expression")
    projection = bad_expression.projections[0]
    assert isinstance(projection.expression, CallIR)

    invalid_backup = replace(
        backup,
        connector=replace(backup.connector, name="unsupported.table"),
    )
    invalid_expression = replace(
        bad_expression,
        projections=(
            replace(
                projection,
                expression=replace(projection.expression, callee="unsupported"),
            ),
        ),
    )
    definitions = tuple(
        invalid_backup
        if definition is backup
        else invalid_expression
        if definition is bad_expression
        else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert [artifact.name for artifact in result.artifacts] == [
        "active_users",
        "active_user_emails",
    ]
    assert [
        (diagnostic.code, _diagnostic_definition_name(diagnostic))
        for diagnostic in result.diagnostics
    ] == [
        ("PIE-B1000", "bad_connector"),
        ("PIE-B1000", "bad_expression"),
    ]


@pytest.mark.parametrize("path", EXAMPLE_PATHS, ids=str)
def test_all_committed_examples_complete_the_sql_pipeline(path: Path) -> None:
    parse_result = parse_file(path)
    assert parse_result.diagnostics == (), _format_diagnostics(
        path,
        "parser",
        parse_result.diagnostics,
    )
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    semantic_errors = tuple(
        diagnostic
        for diagnostic in semantic_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert semantic_errors == (), _format_diagnostics(
        path,
        "semantic",
        semantic_errors,
    )

    ir_result = build_ir(parse_result.ast, semantic_result.model)
    ir_errors = tuple(
        diagnostic
        for diagnostic in ir_result.diagnostics
        if diagnostic.severity is Severity.ERROR
    )
    assert ir_errors == (), _format_diagnostics(path, "IR", ir_errors)
    assert ir_result.ir is not None

    sql_result = emit_postgres_sql(ir_result.ir)

    assert sql_result.diagnostics == (), _format_diagnostics(
        path,
        "PostgreSQL",
        sql_result.diagnostics,
    )
    assert all(
        artifact.kind is SqlArtifactKind.RELATION for artifact in sql_result.artifacts
    )


def test_implemented_backend_diagnostics_match_documented_codes() -> None:
    implemented: set[str] = set()
    for path in Path("src/pietto/sql").rglob("*.py"):
        implemented.update(
            re.findall(
                r'["\'](PIE-B[0-9]{4})["\']',
                path.read_text(encoding="utf-8"),
            )
        )
    documented = set(
        re.findall(
            r"`(PIE-B[0-9]{4})`",
            Path("docs/spec/diagnostics.md").read_text(encoding="utf-8"),
        )
    )

    assert implemented == documented == {"PIE-B1000"}


def test_repository_contains_no_legacy_diagnostic_codes() -> None:
    roots = (
        Path("src"),
        Path("tests"),
        Path("docs"),
        Path("README.md"),
        Path("AGENTS.md"),
    )
    legacy_codes: list[tuple[Path, str]] = []

    for root in roots:
        paths = root.rglob("*") if root.is_dir() else (root,)
        for path in paths:
            if not path.is_file() or path.suffix not in {
                ".md",
                ".pietto",
                ".py",
                ".txt",
            }:
                continue
            for match in re.finditer(
                r"(?<!PIE-)\bP[0-9]{4}\b",
                path.read_text(encoding="utf-8"),
            ):
                legacy_codes.append((path, match.group()))

    assert legacy_codes == []


def test_sql_backend_has_no_forbidden_integration_or_runtime_features() -> None:
    source = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("src/pietto/sql").rglob("*.py")
    )

    assert "sqlglot" not in source
    assert "compile_to_ir" not in source
    assert "parse_source" not in source
    assert "analyze(" not in source
    assert "build_ir(" not in source
    for sql_keyword in (
        "CREATE TABLE",
        "CREATE VIEW",
        "JOIN ",
        "WINDOW ",
        "UNION ",
    ):
        assert sql_keyword not in source


def test_sql_public_entry_point_type_contract_uses_script_ir() -> None:
    signature = inspect.signature(emit_postgres_sql)

    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.parameters["script_ir"].annotation == "ScriptIR"
    assert signature.return_annotation == "SqlResult"


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="sql-completion-audit.pietto")
    assert parse_result.diagnostics == ()
    assert parse_result.ast is not None

    semantic_result = analyze(parse_result.ast)
    assert all(
        diagnostic.severity is not Severity.ERROR
        for diagnostic in semantic_result.diagnostics
    )
    ir_result = build_ir(parse_result.ast, semantic_result.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _source(script_ir: ScriptIR, name: str) -> SourceIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR) and definition.name == name
    )


def _relation(script_ir: ScriptIR, name: str) -> RelationIR:
    return next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR) and definition.name == name
    )


def _diagnostic_definition_name(diagnostic: Diagnostic) -> str:
    head = diagnostic.message.split(".", maxsplit=1)[0]
    return head.rsplit(": ", maxsplit=1)[-1]


def _format_diagnostics(
    path: Path,
    stage: str,
    diagnostics: tuple[Diagnostic, ...],
) -> str:
    details = "\n".join(
        (
            f"{diagnostic.severity.value} {diagnostic.code} "
            f"{diagnostic.location.line}:{diagnostic.location.column} "
            f"{diagnostic.message}"
        )
        for diagnostic in diagnostics
    )
    return f"{path} produced {stage} diagnostics:\n{details}"
