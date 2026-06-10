from __future__ import annotations

from dataclasses import dataclass, replace

from pietto.errors import Severity
from pietto.ir import (
    DefinitionIR,
    RelationIR,
    ScriptIR,
    SourceIR,
    SourceSpan,
    build_ir,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.sql import SqlArtifactKind, SqlResult, emit_postgres_sql

METADATA_SOURCE = (
    "type Email = Text not null\n"
    "enum Status:\n"
    "    active\n"
    "constraint valid_email(email: Text not null) -> Bool not null:\n"
    "    email is not null\n"
    "derive normalize_email(email: Text not null) -> Text not null:\n"
    "    trim(email)\n"
    "shape User:\n"
    "    email: Email not null\n"
    'source users: User is postgres.table("users")\n'
)


@dataclass(frozen=True, slots=True)
class FutureDefinitionIR(DefinitionIR):
    """Test-only future backend target with the standard definition metadata."""

    name: str
    span: SourceSpan


def test_metadata_only_script_returns_empty_success() -> None:
    result = emit_postgres_sql(_compile_ir(METADATA_SOURCE))

    assert result == SqlResult(artifacts=(), diagnostics=())


def test_all_current_metadata_kinds_are_non_emitting() -> None:
    script_ir = _compile_ir(METADATA_SOURCE)

    result = emit_postgres_sql(script_ir)

    assert [type(definition).__name__ for definition in script_ir.definitions] == [
        "TypeIR",
        "EnumIR",
        "ConstraintIR",
        "DeriveIR",
        "ShapeIR",
        "SourceIR",
    ]
    assert result.artifacts == ()
    assert result.diagnostics == ()


def test_metadata_order_does_not_affect_noop_behavior() -> None:
    script_ir = _compile_ir(METADATA_SOURCE)
    reversed_ir = ScriptIR(definitions=tuple(reversed(script_ir.definitions)))

    assert emit_postgres_sql(script_ir) == SqlResult((), ())
    assert emit_postgres_sql(reversed_ir) == SqlResult((), ())


def test_source_and_table_emit_only_the_relation_without_metadata_diagnostics() -> None:
    result = emit_postgres_sql(
        _compile_ir(
            METADATA_SOURCE + "table user_emails:\n"
            "    from users\n"
            "    select:\n"
            "        email\n"
        )
    )

    assert [(artifact.name, artifact.kind) for artifact in result.artifacts] == [
        ("user_emails", SqlArtifactKind.RELATION)
    ]
    assert result.diagnostics == ()


def test_bad_connector_is_ignored_until_a_relation_uses_the_source() -> None:
    metadata_ir = _compile_ir(METADATA_SOURCE)
    invalid_metadata_ir = _replace_source_connector(metadata_ir)

    assert emit_postgres_sql(invalid_metadata_ir) == SqlResult((), ())

    relation_ir = _compile_ir(
        METADATA_SOURCE + "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )
    invalid_relation_ir = _replace_source_connector(relation_ir)

    result = emit_postgres_sql(invalid_relation_ir)

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-B1000"
    assert diagnostic.severity is Severity.ERROR
    assert "postgres.table(Text)" in diagnostic.message


def test_unsupported_relation_still_produces_pie_b1000() -> None:
    script_ir = _compile_ir(
        METADATA_SOURCE + "table user_emails:\n"
        "    from users\n"
        "    select:\n"
        "        email\n"
    )
    relation = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, RelationIR)
    )
    unsupported = replace(relation, projections=())
    definitions = tuple(
        unsupported if definition is relation else definition
        for definition in script_ir.definitions
    )

    result = emit_postgres_sql(ScriptIR(definitions=definitions))

    assert result.artifacts == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-B1000"]


def test_unknown_future_definition_reports_pie_b1000_at_its_span() -> None:
    definition = FutureDefinitionIR(
        name="future_target",
        span=SourceSpan(
            path="future.pie",
            line=7,
            column=3,
            end_line=7,
            end_column=16,
        ),
    )

    result = emit_postgres_sql(ScriptIR(definitions=(definition,)))

    assert result.artifacts == ()
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-B1000"
    assert diagnostic.severity is Severity.ERROR
    assert "FutureDefinitionIR" in diagnostic.message
    assert "future_target" in diagnostic.message
    assert (
        diagnostic.location.path,
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == ("future.pie", 7, 3, 7, 16)


def _compile_ir(source: str) -> ScriptIR:
    parse_result = parse_source(source, path="postgres-metadata.pie")
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


def _replace_source_connector(script_ir: ScriptIR) -> ScriptIR:
    source = next(
        definition
        for definition in script_ir.definitions
        if isinstance(definition, SourceIR)
    )
    invalid = replace(
        source,
        connector=replace(source.connector, name="unsupported.table"),
    )
    return ScriptIR(
        definitions=tuple(
            invalid if definition is source else definition
            for definition in script_ir.definitions
        )
    )
