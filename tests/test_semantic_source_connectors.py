from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path

import pytest
from antlr4 import ParserRuleContext
from antlr4.Token import Token

from pietto.ast_nodes import CallExpr, Script, ShapeDef, SourceDef
from pietto.errors import Diagnostic, Severity
from pietto.parser_api import parse_source
from pietto.semantic import CheckMode, SemanticResult, ValueTypeKind, analyze

SHAPE = "shape UserRow:\n    id: UUID not null\n    email: Text not null\n"


@pytest.mark.parametrize(
    ("connector", "codes"),
    [
        ('postgres.table("public.users")', ()),
        ('mysql.table("app.users")', ()),
        ('postgres.table("")', ()),
        ('postgres.table("   ")', ()),
        ('mysql.table("   ")', ()),
        ('postgres.table(trim("users"))', ()),
        ("postgres.table(123)", ("PIE-S2306",)),
        ('mysql.table("")', ("PIE-S2306",)),
        ('unknown.table("rows")', ("PIE-S2306",)),
        ("postgres.table()", ("PIE-S2306",)),
        ('postgres.table("users", "extra")', ("PIE-S2306",)),
        ("mysql.table()", ("PIE-S2306",)),
        ('mysql.table("users", "extra")', ("PIE-S2306",)),
        ('mysql.table(trim("users"))', ("PIE-S2306",)),
        ('mysql.Table("users")', ("PIE-S2306",)),
        ("42", ("PIE-S2306",)),
        ("postgres.table(missing)", ("PIE-S2102",)),
        ("mysql.table(missing)", ("PIE-S2102",)),
        ("unknown.table(missing)", ("PIE-S2102",)),
    ],
)
def test_completed_source_rules_preserve_single_file_diagnostics(
    tmp_path: Path, connector: str, codes: tuple[str, ...]
) -> None:
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _completed,
    )

    text = SHAPE + f"source users: UserRow is {connector}\n"
    expected = analyze(_parse(text, path="main.pietto")).diagnostics
    completed = _completed(tmp_path, text)
    assert tuple(d.code for d in expected) == codes
    assert completed.diagnostics == expected
    assert completed.ok is (not codes)
    assert all(d.severity is Severity.ERROR for d in completed.diagnostics)


def test_completed_checks_defining_modules_once_and_reuses_diagnostics(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pietto._project import project_completed_semantics as boundary
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _completed,
        _source as joined_source,
    )
    from test_phase64_slice7_single_match_direction_unit_scoped_proof_obligation_warning_diagnostics import (
        _request,
    )

    (tmp_path / "a.pietto").write_text(
        SHAPE + 'source users: UserRow is mysql.table("")\nexport:\n    source users\n'
    )
    (tmp_path / "b.pietto").write_text(
        'import "a.pietto":\n    source users as Public\nexport:\n    source Public\n'
    )
    (tmp_path / "c.pietto").write_text(
        'import "a.pietto":\n    source users as Again\n'
        + SHAPE
        + "source users: UserRow is postgres.table(missing)\n"
        + 'source second: UserRow is mysql.table("")\n'
    )
    typed_scripts: list[Script] = []
    checked_scripts: list[Script] = []
    emitted: list[Diagnostic] = []
    type_arguments = boundary.type_source_connector_arguments
    check_connectors = boundary.check_source_connectors

    def capture_types(script):
        typed_scripts.append(script)
        types, diagnostics = type_arguments(script)
        emitted.extend(diagnostics)
        return types, diagnostics

    def capture_checks(script, types):
        checked_scripts.append(script)
        diagnostics = check_connectors(script, types)
        emitted.extend(diagnostics)
        return diagnostics

    monkeypatch.setattr(boundary, "type_source_connector_arguments", capture_types)
    monkeypatch.setattr(boundary, "check_source_connectors", capture_checks)
    completed = _completed(
        tmp_path,
        'import "b.pietto":\n    source Public as Imported\n' + joined_source("true"),
    )
    modules = completed.semantic_result.modules
    scripts = tuple(
        m.parsed_input.script for m in modules if m.parsed_input is not None
    )
    assert len(scripts) == len(modules) == 4
    assert len(typed_scripts) == len(checked_scripts) == len(scripts)
    assert all(
        a is b is c
        for a, b, c in zip(scripts, typed_scripts, checked_scripts, strict=True)
    )
    assert [(d.code, d.location.path) for d in completed.diagnostics] == [
        ("PIE-S2306", "a.pietto"),
        ("PIE-S2102", "c.pietto"),
        ("PIE-S2306", "c.pietto"),
    ]
    assert len(completed.diagnostics) == len(emitted)
    assert all(a is b for a, b in zip(completed.diagnostics, emitted, strict=True))
    request = _request(completed)
    for requests in ((), (request,), (request,)):
        wrapped = boundary.with_project_single_match_requests(completed, requests)
        assert wrapped.roots is completed.roots and not wrapped.ok
        assert all(
            a is b for a, b in zip(wrapped.diagnostics[:3], emitted, strict=True)
        )
        assert len(typed_scripts) == len(checked_scripts) == 4
        if requests:
            assert wrapped.diagnostics[-1].code == "PIE-S2337"


def test_completed_preserves_prior_diagnostics_and_cli_semantic_caller(
    tmp_path: Path,
) -> None:
    from pietto import cli
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _completed,
    )

    completed = _completed(
        tmp_path,
        SHAPE
        + 'source users: UserRow is mysql.table("")\n'
        + "query broken:\n    from absent\n    select:\n        id\n",
    )
    semantic = completed.semantic_result
    prior = semantic.diagnostics
    assert prior and all(d.severity is Severity.ERROR for d in prior)
    assert all(
        a is b for a, b in zip(completed.diagnostics[: len(prior)], prior, strict=True)
    )
    assert completed.diagnostics[-1].code == "PIE-S2306"
    diagnostics, ok = cli._project_semantic_boundary(semantic)
    assert not ok
    assert all(a is b for a, b in zip(diagnostics[: len(prior)], prior, strict=True))
    assert diagnostics == completed.diagnostics


def test_completed_source_scan_rejects_missing_module_script(tmp_path: Path) -> None:
    from pietto._project.project_completed_semantics import (
        build_project_completed_semantic_result,
    )
    from test_phase64_slice3_generic_on_condition_semantics_authority_separation import (
        _completed,
    )

    completed = _completed(
        tmp_path, SHAPE + 'source users: UserRow is postgres.table("users")\n'
    )
    module = completed.semantic_result.modules[0]
    parsed = module.parsed_input
    # Deliberately corrupt one retained root; restore it before the test exits.
    object.__setattr__(module, "parsed_input", None)
    try:
        with pytest.raises(ValueError, match="every module script"):
            build_project_completed_semantic_result(completed.semantic_result)
    finally:
        object.__setattr__(module, "parsed_input", parsed)


@pytest.mark.parametrize("mode", ("legacy_flat", "package_root"))
def test_completed_nonpositive_modes_do_not_run_source_scan(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pietto._project import project_completed_semantics as boundary
    from pietto._project.model import ProjectSemanticResult
    from pietto._project.module_carrier import ProjectCompilationMode

    def forbidden(script):
        raise AssertionError("nonpositive modes must not enter source validation")

    monkeypatch.setattr(boundary, "type_source_connector_arguments", forbidden)
    semantic = ProjectSemanticResult(
        root=None,
        config_path=None,
        model=None,
        compilation_mode=ProjectCompilationMode(mode),
    )
    result = boundary.build_project_completed_semantic_result(semantic)
    assert isinstance(result, boundary.ProjectNonConcreteCompletedSemanticResult)
    assert result.diagnostics is semantic.diagnostics and not result.ok


def test_postgres_table_with_text_argument_passes() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    )

    assert result.diagnostics == ()


def test_mysql_table_with_nonempty_text_literal_passes() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is mysql.table("app.users")\n')
    )

    assert result.diagnostics == ()


@pytest.mark.parametrize(
    "connector",
    [
        "postgres.table()",
        'postgres.table("public.users", "extra")',
        "postgres.table(123)",
    ],
)
def test_invalid_postgres_table_arguments_report_pie_s2306(
    connector: str,
) -> None:
    result = analyze(_parse(SHAPE + f"source users: UserRow is {connector}\n"))

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2306",
            Severity.ERROR,
            "Invalid source connector arguments for postgres.table",
        )
    ]


@pytest.mark.parametrize(
    "connector",
    [
        "mysql.table()",
        'mysql.table("users", "extra")',
        "mysql.table(123)",
        'mysql.table(trim("users"))',
        'mysql.table("")',
    ],
)
def test_invalid_mysql_table_arguments_report_pie_s2306(
    connector: str,
) -> None:
    result = analyze(_parse(SHAPE + f"source users: UserRow is {connector}\n"))

    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in result.diagnostics
    ] == [
        (
            "PIE-S2306",
            Severity.ERROR,
            "Invalid source connector arguments for mysql.table",
        )
    ]


def test_unknown_source_connector_reports_pie_s2306() -> None:
    result = analyze(_parse(SHAPE + 'source users: UserRow is sqlite.table("users")\n'))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2306", "Unknown source connector: sqlite.table")]


def test_mysql_connector_name_matching_is_exact() -> None:
    result = analyze(_parse(SHAPE + 'source users: UserRow is mysql.Table("users")\n'))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2306", "Unknown source connector: mysql.Table")]


def test_non_call_source_connector_reports_pie_s2306() -> None:
    result = analyze(_parse(SHAPE + "source users: UserRow is 42\n"))

    assert [
        (diagnostic.code, diagnostic.message) for diagnostic in result.diagnostics
    ] == [("PIE-S2306", "Invalid source connector expression")]


@pytest.mark.parametrize("connector_name", ["postgres.table", "mysql.table"])
def test_unknown_argument_suppresses_connector_cascade(
    connector_name: str,
) -> None:
    result = analyze(
        _parse(SHAPE + f"source users: UserRow is {connector_name}(missing)\n")
    )
    source = _source(result)
    connector = source.connector
    assert isinstance(connector, CallExpr)

    assert [diagnostic.code for diagnostic in result.diagnostics] == ["PIE-S2102"]
    assert (
        result.model.expression_value_types[connector.arguments[0]].kind
        is ValueTypeKind.UNKNOWN
    )


@pytest.mark.parametrize(
    ("mode", "expected"),
    [
        (CheckMode.LOOSE, ()),
        (CheckMode.CHECKED, (("PIE-S2303", Severity.WARNING),)),
        (CheckMode.STRICT, (("PIE-S2303", Severity.ERROR),)),
    ],
)
def test_untyped_source_mode_policy_is_unchanged(
    mode: CheckMode,
    expected: tuple[tuple[str, Severity], ...],
) -> None:
    result = analyze(
        _parse('source users is postgres.table("public.users")\n'),
        mode_override=mode,
    )

    assert (
        tuple(
            (diagnostic.code, diagnostic.severity) for diagnostic in result.diagnostics
        )
        == expected
    )


@pytest.mark.parametrize("connector_name", ["postgres.table", "mysql.table"])
def test_typed_source_schema_still_comes_from_declared_shape(
    connector_name: str,
) -> None:
    result = analyze(
        _parse(SHAPE + f'source users: UserRow is {connector_name}("public.users")\n')
    )
    source = _source(result)
    shape = result.model.type_symbols["UserRow"]
    assert isinstance(shape, ShapeDef)
    schema = result.model.source_row_schemas[source]

    assert list(schema.fields) == ["id", "email"]
    assert schema.fields["id"].definition is shape.fields[0]
    assert schema.fields["email"].definition is shape.fields[1]


def test_connector_diagnostic_uses_connector_expression_span() -> None:
    script = _parse(
        SHAPE + "source users: UserRow is mysql.table(123)\n",
        path="source-connectors.pietto",
    )
    source = script.definitions[-1]
    assert isinstance(source, SourceDef)

    diagnostic = analyze(script).diagnostics[0]
    span = source.connector.span

    assert diagnostic.code == "PIE-S2306"
    assert diagnostic.location.path == span.path == "source-connectors.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (span.line, span.column, span.end_line, span.end_column)


def test_connector_validation_does_not_mutate_input_ast() -> None:
    script = _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    original = deepcopy(script)

    analyze(script)

    assert script == original


def test_connector_results_do_not_expose_antlr_nodes() -> None:
    result = analyze(
        _parse(SHAPE + 'source users: UserRow is postgres.table("public.users")\n')
    )

    _assert_no_antlr_nodes(result)


def _parse(source: str, *, path: str | None = None) -> Script:
    result = parse_source(source, path=path)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _source(result: SemanticResult) -> SourceDef:
    definition = result.model.relation_symbols["users"]
    assert isinstance(definition, SourceDef)
    return definition


def _assert_no_antlr_nodes(value: object) -> None:
    assert not isinstance(value, ParserRuleContext)
    assert not isinstance(value, Token)
    assert not type(value).__module__.startswith("pietto.generated")
    if is_dataclass(value):
        for field in fields(value):
            _assert_no_antlr_nodes(getattr(value, field.name))
    elif isinstance(value, Mapping):
        for key, item in value.items():
            _assert_no_antlr_nodes(key)
            _assert_no_antlr_nodes(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _assert_no_antlr_nodes(item)
