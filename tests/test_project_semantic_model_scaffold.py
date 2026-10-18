from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass
import json
from pathlib import Path
from types import MappingProxyType

import pytest

import pietto.cli as cli
import pietto.semantic as semantic_api
from pietto._project.check import check_project_parse_only
from pietto._project.json_v2 import project_check_result_to_json_dict
from pietto._project.model import (
    ProjectConfigPath,
    ProjectParsedInput,
    ProjectParseCheckResult,
    ProjectRoot,
    ProjectSemanticCatalog,
    ProjectSemanticModel,
    ProjectSemanticResult,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    build_empty_project_semantic_result,
)
from pietto.ast_nodes import DeriveDef, ShapeDef, SourceDef, TableDef, TypeDef, Script
from pietto.errors import Diagnostic, Severity, SourceLocation

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_project_semantic_scaffold_types_are_frozen_slots_dataclasses() -> None:
    for model_type in (
        ProjectSemanticCatalog,
        ProjectSemanticModel,
        ProjectSemanticResult,
    ):
        assert is_dataclass(model_type)
        assert hasattr(model_type, "__slots__")

    result = ProjectSemanticResult(root=None, config_path=None, model=None)
    assert not hasattr(result, "__dict__")
    with pytest.raises(FrozenInstanceError):
        setattr(result, "diagnostics", ())


def test_project_semantic_catalog_has_readonly_namespace_maps() -> None:
    catalog = ProjectSemanticCatalog()

    assert tuple(field.name for field in fields(ProjectSemanticCatalog)) == (
        "type_symbols",
        "relation_symbols",
        "callable_symbols",
    )
    assert not hasattr(catalog, "__dict__")
    assert isinstance(catalog.type_symbols, MappingProxyType)
    assert isinstance(catalog.relation_symbols, MappingProxyType)
    assert isinstance(catalog.callable_symbols, MappingProxyType)
    assert catalog.type_symbols == {}
    assert catalog.relation_symbols == {}
    assert catalog.callable_symbols == {}


def test_project_semantic_result_preserves_successful_parse_inputs(
    tmp_path: Path,
) -> None:
    root = _project_root(
        tmp_path,
        include=("models/*.pietto", "*.pietto"),
        exclude=("models/tmp/*.pietto",),
    )
    _write(root, "root.pietto", "shape Root:\n    id: Int\n")
    _write(root, "models/z.pietto", "shape Zed:\n    id: Int\n")
    _write(root, "models/a.pietto", "shape Alpha:\n    id: Int\n")
    _write(root, "models/tmp/skip.pietto", "shape Skip:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.root == parse_result.root
    assert semantic_result.config_path == parse_result.config_path
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert semantic_result.model.root == parse_result.root
    assert semantic_result.model.config_path == parse_result.config_path
    assert semantic_result.model.inputs is parse_result.parsed_inputs
    assert tuple(item.path for item in semantic_result.model.inputs) == (
        "models/a.pietto",
        "models/z.pietto",
        "root.pietto",
    )
    for parsed_input in semantic_result.model.inputs:
        assert isinstance(parsed_input, ProjectParsedInput)
        assert not Path(parsed_input.path).is_absolute()
        assert isinstance(parsed_input.script, Script)
        assert parsed_input.script.span.path == parsed_input.path


def test_project_semantic_catalog_populates_symbols_in_deterministic_order(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a.pietto",
        "type Age = Int not null\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "    PAUSED\n"
        "shape User:\n"
        "    id: Int\n"
        "constraint usable(value: Text not null) -> Bool not null:\n"
        "    value is not null\n",
    )
    _write(
        root,
        "models/b.pietto",
        "derive normalize(value: Text not null) -> Text not null:\n"
        "    lower(value)\n"
        'source users: User is postgres.table("users")\n'
        "table active_users:\n"
        "    from users\n"
        "    select:\n"
        "        id\n"
        "query user_ids:\n"
        "    from active_users\n"
        "    select:\n"
        "        id\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.model is not None
    catalog = semantic_result.model.catalog
    assert tuple(catalog.type_symbols) == ("Age", "Status", "User")
    assert tuple(catalog.callable_symbols) == ("usable", "normalize")
    assert tuple(catalog.relation_symbols) == ("users", "active_users", "user_ids")

    age = catalog.type_symbols["Age"]
    assert age.namespace is ProjectSymbolNamespace.TYPE
    assert age.kind is ProjectSymbolKind.TYPE_ALIAS
    assert age.name == "Age"
    assert age.path == "models/a.pietto"
    assert age.location == SourceLocation(
        path="models/a.pietto",
        line=1,
        column=1,
        end_line=1,
        end_column=24,
    )
    assert isinstance(age.definition, TypeDef)
    assert age.definition.name == "Age"

    assert catalog.type_symbols["Status"].kind is ProjectSymbolKind.ENUM
    assert catalog.type_symbols["User"].kind is ProjectSymbolKind.SHAPE
    assert catalog.callable_symbols["usable"].kind is ProjectSymbolKind.CONSTRAINT
    assert catalog.callable_symbols["normalize"].kind is ProjectSymbolKind.DERIVE
    assert catalog.relation_symbols["users"].kind is ProjectSymbolKind.SOURCE
    assert catalog.relation_symbols["active_users"].kind is ProjectSymbolKind.TABLE
    assert catalog.relation_symbols["user_ids"].kind is ProjectSymbolKind.QUERY
    assert isinstance(catalog.type_symbols["User"].definition, ShapeDef)
    assert isinstance(catalog.relation_symbols["users"].definition, SourceDef)
    assert isinstance(catalog.relation_symbols["active_users"].definition, TableDef)
    assert isinstance(catalog.callable_symbols["normalize"].definition, DeriveDef)


def test_project_semantic_catalog_can_still_be_empty() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )

    assert model.catalog == ProjectSemanticCatalog()
    assert model.catalog.type_symbols == {}
    assert model.catalog.relation_symbols == {}
    assert model.catalog.callable_symbols == {}


def test_same_name_across_project_namespaces_is_allowed(tmp_path: Path) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "shared.pietto",
        "shape Shared:\n"
        "    id: Int\n"
        "derive Shared(value: Text not null) -> Text not null:\n"
        "    value\n"
        'source Shared: Shared is postgres.table("shared")\n',
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    catalog = semantic_result.model.catalog
    assert set(catalog.type_symbols) == {"Shared"}
    assert set(catalog.callable_symbols) == {"Shared"}
    assert set(catalog.relation_symbols) == {"Shared"}


def test_project_duplicate_symbols_fail_closed_and_keep_first_symbol(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("models/*.pietto",))
    _write(
        root,
        "models/a.pietto",
        "shape Shared:\n"
        "    id: Int\n"
        "derive normalize(value: Text not null) -> Text not null:\n"
        "    value\n",
    )
    _write(
        root,
        "models/b.pietto",
        "enum Shared:\n"
        "    ACTIVE\n"
        "constraint normalize(value: Text not null) -> Bool not null:\n"
        "    value is not null\n"
        'source rows: Shared is postgres.table("rows")\n',
    )
    _write(
        root,
        "models/c.pietto",
        "table rows:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "query rows:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert not semantic_result.ok
    assert semantic_result.model is not None
    assert [
        (diagnostic.code, diagnostic.severity, diagnostic.message)
        for diagnostic in semantic_result.diagnostics
    ] == [
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in type namespace: Shared",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in callable namespace: normalize",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in relation namespace: rows",
        ),
        (
            "PIE-S2001",
            Severity.ERROR,
            "Duplicate symbol name in relation namespace: rows",
        ),
    ]
    assert [
        (diagnostic.location.path, diagnostic.location.line, diagnostic.location.column)
        for diagnostic in semantic_result.diagnostics
    ] == [
        ("models/b.pietto", 1, 1),
        ("models/b.pietto", 3, 1),
        ("models/c.pietto", 1, 1),
        ("models/c.pietto", 5, 1),
    ]

    catalog = semantic_result.model.catalog
    assert catalog.type_symbols["Shared"].path == "models/a.pietto"
    assert catalog.type_symbols["Shared"].kind is ProjectSymbolKind.SHAPE
    assert catalog.callable_symbols["normalize"].path == "models/a.pietto"
    assert catalog.callable_symbols["normalize"].kind is ProjectSymbolKind.DERIVE
    assert catalog.relation_symbols["rows"].path == "models/b.pietto"
    assert catalog.relation_symbols["rows"].kind is ProjectSymbolKind.SOURCE


def test_relation_body_semantics_remain_deferred_after_resolution(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(
        root,
        "body_deferred.pietto",
        "shape Raw:\n"
        "    id: Int\n"
        'source raw: Raw is postgres.table("raw")\n'
        "table projected:\n"
        "    from raw\n"
        "    select:\n"
        "        total = missing_field + 1\n",
    )

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.ok
    assert semantic_result.diagnostics == ()
    assert semantic_result.model is not None
    assert tuple(semantic_result.model.catalog.relation_symbols) == ("raw", "projected")
    projected = semantic_result.model.catalog.relation_symbols["projected"].definition
    assert isinstance(projected, TableDef)
    assert (
        semantic_result.model.relation_resolutions[projected.from_clause].name == "raw"
    )


def test_project_semantic_result_defaults_and_ok_behavior() -> None:
    model = ProjectSemanticModel(
        root=ProjectRoot(path="."),
        config_path=ProjectConfigPath(path="pietto.toml"),
        inputs=(),
        catalog=ProjectSemanticCatalog(),
    )
    error_diagnostic = Diagnostic(
        code="PIE-S9999",
        severity=Severity.ERROR,
        message="Synthetic project semantic error.",
        location=SourceLocation(path="models/a.pietto", line=1, column=1),
    )
    warning_diagnostic = Diagnostic(
        code="PIE-S9998",
        severity=Severity.WARNING,
        message="Synthetic project semantic warning.",
        location=SourceLocation(path="models/a.pietto", line=1, column=1),
    )

    assert (
        ProjectSemanticResult(root=None, config_path=None, model=None).diagnostics == ()
    )
    assert not ProjectSemanticResult(root=None, config_path=None, model=None).ok
    assert ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
    ).ok
    assert ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
        diagnostics=(warning_diagnostic,),
    ).ok
    assert not ProjectSemanticResult(
        root=model.root,
        config_path=model.config_path,
        model=model,
        diagnostics=(error_diagnostic,),
    ).ok


def test_parse_failures_return_no_model_and_no_semantic_diagnostics(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto", "models/*.pietto"))
    _write(root, "bad.pietto", "shape Broken\n    id: Int\n")
    _write(root, "models/good.pietto", "shape Good:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)

    assert not parse_result.ok
    assert semantic_result.root == parse_result.root
    assert semantic_result.config_path == parse_result.config_path
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert not semantic_result.ok


def test_missing_root_or_config_returns_no_model() -> None:
    parse_result = ProjectParseCheckResult(
        root=None,
        config_path=None,
        inputs=(),
        errors=(),
        diagnostics=(),
    )

    semantic_result = build_empty_project_semantic_result(parse_result)

    assert parse_result.ok
    assert semantic_result.root is None
    assert semantic_result.config_path is None
    assert semantic_result.model is None
    assert semantic_result.diagnostics == ()
    assert not semantic_result.ok


def test_project_semantic_scaffold_does_not_call_single_file_semantics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_analyze(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project semantic scaffold must not analyze scripts")

    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    parse_result = check_project_parse_only(root)
    monkeypatch.setattr(semantic_api, "analyze", unexpected_analyze)

    assert build_empty_project_semantic_result(parse_result).ok


def test_project_semantic_scaffold_does_not_enter_output_pipelines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")
    parse_result = check_project_parse_only(root)

    assert build_empty_project_semantic_result(parse_result).ok


def test_project_json_v2_does_not_expose_project_semantic_scaffold(
    tmp_path: Path,
) -> None:
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    parse_result = check_project_parse_only(root)
    semantic_result = build_empty_project_semantic_result(parse_result)
    document = project_check_result_to_json_dict(parse_result)
    serialized = json.dumps(document)

    assert semantic_result.model is not None
    assert document["ok"] is True
    assert "ProjectSemantic" not in serialized
    assert "catalog" not in serialized
    assert "parsed_inputs" not in serialized
    assert "script" not in serialized


def test_project_text_output_remains_parse_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _forbid_project_compiler_pipeline(monkeypatch)
    root = _project_root(tmp_path, include=("*.pietto",))
    _write(root, "good.pietto", "shape Good:\n    id: Int\n")

    assert cli.main(["check", "--project", str(root)]) == 0

    captured = capsys.readouterr()
    assert captured.out == "Project check OK: .\nFiles checked: 1\n"
    assert captured.err == ""


DEF_HEAD = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    n: Int nullable\n"
    "    text: Text not null\n"
    "    unique row_key on id\n"
    "shape Other:\n"
    "    id: Int not null\n"
    "    row_id: Int not null\n"
    "    label: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
    'source others: Other is postgres.table("others")\n'
    "def pos(x: Int not null) -> Bool nullable: return x > 0\n"
    "def idi(x: Int not null) -> Int not null: return x\n"
    "def idt(x: Text not null) -> Text not null: return x\n"
)
# The first line written after DEF_HEAD.
DEF_LINE = 15


def _def_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], files: dict[str, str]
) -> list[tuple[str, str, int, int, str]]:
    root = tmp_path / "project"
    _write(
        root, "pietto.toml", 'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n'
    )
    for name, source in files.items():
        _write(root, name, source)
    code = cli.main(["check", "--project", str(root), "--format", "json"])
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    assert code == (1 if diagnostics else 0)
    return [
        (
            d["code"],
            d["location"]["path"],
            d["location"]["line"],
            d["location"]["column"],
            d["message"],
        )
        for d in diagnostics
    ]


def test_a_def_belongs_to_its_module(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    exported = DEF_HEAD + "export:\n    source rows\n    table pos\n"
    caller = (
        'import "a.pietto":\n    source rows\n'
        "table t:\n    from rows\n    where pos(id)\n    select:\n        id\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": exported, "b.pietto": caller}) == [
        (
            "PIE-S2704",
            "a.pietto",
            DEF_LINE + 2,
            11,
            "Unknown export binding: table pos",
        ),
        ("PIE-S2103", "b.pietto", 5, 11, "Unknown function: pos"),
    ]


def _mismatch(name: str, line: int, column: int, expected: str, got: str):
    return (
        "PIE-S2395",
        "a.pietto",
        line,
        column,
        f"Invalid argument for def {name} at position 1 (x): expected {expected}, "
        f"got {got}",
    )


def test_a_project_checks_def_arguments_in_its_typed_positions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = DEF_HEAD + (
        "query q(k: Int not null, m: Int nullable):\n    from rows\n"
        "    where pos(k) and pos(m)\n    select:\n        id\n"
        "        bare = idi(n)\n"
        "query c:\n    let l:\n        capture rows\n        from others\n"
        "        where pos(rows.n)\n        select:\n            id\n"
        "    from rows\n    where exists l\n    select:\n        id\n"
        "query j:\n    from rows\n    inner join others as o:\n        from rows\n"
        "        on o.row_id == rows.id\n    select:\n        a = rows.id\n"
        "        p = idt(o.label)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("pos", DEF_LINE + 2, 22, "Int not null", "Int nullable"),
        _mismatch("idi", DEF_LINE + 5, 16, "Int not null", "Int nullable"),
        _mismatch("pos", DEF_LINE + 10, 15, "Int not null", "Int nullable"),
        _mismatch("idt", DEF_LINE + 24, 13, "Text not null", "Text nullable"),
    ]


def test_a_project_def_reads_local_aliases_and_null_comparisons_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A local alias is its base type in a signature; a comparison with the
    null literal is PIE-S2105 once, in an argument or made by a null
    argument, and a null argument that does not fit is only PIE-S2395, also
    where the body casts it."""
    source = DEF_HEAD + (
        "type Money = Int not null\n"
        "def bump(x: Money nullable) -> Money nullable: return x + 1\n"
        "def flag(b: Bool not null) -> Bool nullable: return b or b\n"
        "def low(x: Int nullable) -> Bool nullable: return x < 3\n"
        "def fl(x: Int not null) -> Float nullable: return cast(x as Float)\n"
        "query q:\n    from rows\n"
        "    where flag(n == null) and low(null) and pos(null)\n"
        "    select:\n        id\n        v = bump(id)\n        w = fl(null)\n"
    )
    never = "comparison with null is never true"
    line = DEF_LINE + 7
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        (
            "PIE-S2105",
            "a.pietto",
            line,
            16,
            f"Invalid operands for operator ==: {never}; write `is null` instead",
        ),
        (
            "PIE-S2105",
            "a.pietto",
            line,
            31,
            f"Invalid operands for operator <: {never}",
        ),
        _mismatch("pos", line, 45, "Int not null", "null"),
        _mismatch("fl", line + 4, 13, "Int not null", "null"),
    ]


def test_a_project_def_reads_a_let_bound_to_null_as_null(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `let:` name bound to null, also through other lets, is a null
    argument as in a single file: PIE-S2395 alone, also where the body casts
    it, and the relation then needs no PIE-S2333."""
    source = DEF_HEAD + (
        "def fl(x: Int not null) -> Float nullable: return cast(x as Float)\n"
        "query q:\n    from rows\n    let:\n        k = null\n        k2 = k\n"
        "        k3 = k2\n    select:\n        id\n        a = idi(k)\n"
        "        b = idt(k2)\n        c = idi(k3)\n        d = fl(k)\n"
    )
    line = DEF_LINE + 9
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idi", line, 13, "Int not null", "null"),
        _mismatch("idt", line + 1, 13, "Text not null", "null"),
        _mismatch("idi", line + 2, 13, "Int not null", "null"),
        _mismatch("fl", line + 3, 13, "Int not null", "null"),
    ]


def test_a_project_def_reads_a_let_that_stands_for_null_as_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An argument reading a `let:` name bound to null is checked as written
    out, the literal taking its type from where it stands; a name bound to
    another always-null value is null, as in a single file."""
    source = DEF_HEAD + (
        "query q:\n    from rows\n    let:\n        k = null\n        m = id + null\n"
        "    select:\n        id\n        a = idt(lower(k))\n"
        "        b = idi(coalesce(k, n))\n        c = idi(m)\n        d = idi(m + 1)\n"
    )
    line = DEF_LINE + 7
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idt", line, 13, "Text not null", "Text nullable"),
        _mismatch("idi", line + 1, 13, "Int not null", "Int nullable"),
        _mismatch("idi", line + 2, 13, "Int not null", "null"),
        _mismatch("idi", line + 3, 13, "Int not null", "null"),
    ]


def test_a_project_def_checks_an_argument_with_its_let_values_written_in(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An argument is checked as emission writes it, with each `let:` value in
    place of its name, in a WHERE as in a select: a known Bool that is always
    null is null, and a value that reads a let bound to null is typed as the
    null literal written there would make it. A relation with JOIN inputs
    checks it so too, in its lets, WHERE, select and ORDER BY, as it checks
    the value written by hand."""
    joined = (
        "    from rows\n    inner join others as p:\n        from rows\n"
        "        on p.row_id == rows.id\n    let:\n        m = p.id + null > 1\n"
        "        m2 = m\n"
    )
    source = DEF_HEAD + (
        "def bb(x: Bool not null) -> Bool not null: return x is null\n"
        "query w:\n    from rows\n    let:\n        b2 = id + null > 1\n"
        "    where bb(b2)\n    select:\n        id\n"
        "query s:\n    from rows\n    let:\n        nill = null\n"
        "        j = coalesce(nill, n)\n    select:\n        id\n        a = idi(j)\n"
        f"query jl:\n{joined}        c = bb(m2)\n    select:\n        k = rows.id\n"
        f"query jw:\n{joined}    where bb(m)\n    select:\n        k = rows.id\n"
        f"query js:\n{joined}    select:\n        k = rows.id\n        a = bb(m2)\n"
        f"query jo:\n{joined}    select:\n        k = rows.id\n    order by: bb(not m)\n"
        f"query jt:\n{joined}    select:\n        k = rows.id\n"
        "        a = bb(p.id + null > 1)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("bb", DEF_LINE + 5, 11, "Bool not null", "null"),
        _mismatch("idi", DEF_LINE + 15, 13, "Int not null", "Int nullable"),
        _mismatch("bb", DEF_LINE + 24, 13, "Bool not null", "null"),
        _mismatch("bb", DEF_LINE + 35, 11, "Bool not null", "null"),
        _mismatch("bb", DEF_LINE + 48, 13, "Bool not null", "null"),
        _mismatch("bb", DEF_LINE + 59, 15, "Bool not null", "null"),
        _mismatch("bb", DEF_LINE + 70, 13, "Bool not null", "null"),
    ]


@pytest.mark.parametrize(
    "spelling",
    [
        {"I1": "i1", "I2": "i2", "I8": "i8"},
        {
            "I1": "coalesce(null, 1)",
            "I2": "upper(null) + 1",
            "I8": "lower(coalesce(null, 1))",
        },
    ],
    ids=["let_names", "values_written_in"],
)
def test_a_project_def_argument_ill_typed_once_its_lets_are_written_in_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], spelling: dict[str, str]
) -> None:
    """As in a single file, an argument whose `let:` values are ill-typed once
    the null they read is written in reports the error the values written by
    hand report, where they start, in a let and in a select, also as the
    whole argument, and its parameter adds nothing."""
    source = DEF_HEAD + (
        "query q:\n    from rows\n    let:\n        nill = null\n"
        "        i1 = coalesce(nill, 1)\n        i2 = upper(nill) + 1\n"
        "        i8 = lower(i1)\n        z = pos({I2})\n    select:\n        id\n"
        "        a = idt(lower({I1}))\n        b = pos({I2})\n        c = idt({I8})\n"
    ).format(**spelling)
    lower_of_int = (
        "Invalid argument type for function lower at position 1: expected Text, got Int"
    )
    not_numeric = "Invalid operands for operator +: expected numeric operands"
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        ("PIE-S2105", "a.pietto", DEF_LINE + 7, 17, not_numeric),
        ("PIE-S2104", "a.pietto", DEF_LINE + 10, 17, lower_of_int),
        ("PIE-S2105", "a.pietto", DEF_LINE + 11, 17, not_numeric),
        ("PIE-S2104", "a.pietto", DEF_LINE + 12, 17, lower_of_int),
    ]


def test_a_project_def_checks_a_let_that_an_aggregate_reads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `let:` name passed to a def and read directly by an aggregate, also
    in `satisfying`, must fit the parameter as the value written out must:
    PIE-S2333 at the relation, as for `count(idi(n))`, grouped or not, and
    PIE-S2395 at the call in a JOIN relation, which reports its own errors."""
    source = DEF_HEAD + (
        "query g:\n    from rows\n    let:\n        f = n\n    group by: id\n"
        "    select:\n        id\n        c = count(idi(f))\n"
        "query a:\n    from rows\n    let:\n        f = n\n    select:\n"
        "        s = sum(idi(f))\n"
        "query m:\n    from rows\n    let:\n        g = id\n    group by: id\n"
        "    select:\n        id\n        x = max(idt(g))\n"
        "query s:\n    from rows\n    let:\n        f = n\n    group by: id\n"
        "    select:\n        id\n        c = count(f)\n"
        "    satisfying: count(idi(f)) > 0\n"
        "query j:\n    from rows\n    inner join others as o:\n        from rows\n"
        "        on o.row_id == rows.id\n    let:\n        f = o.label\n"
        "    group by: rows.id\n    select:\n        k = rows.id\n        c = count(f)\n"
        "    satisfying: count(idt(f)) > 0\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        (
            "PIE-S2333",
            "a.pietto",
            DEF_LINE + line,
            1,
            f"Project relation semantic completion is unavailable: {name}",
        )
        for name, line in (("g", 0), ("a", 8), ("m", 14), ("s", 22))
    ] + [_mismatch("idt", DEF_LINE + 42, 23, "Text not null", "Text nullable")]


def test_a_project_def_checks_an_aggregate_or_group_key_passed_to_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An aggregate passed to a def is its result, and a group key passed to
    one is that key, which must fit the parameter as in a single file:
    PIE-S2395 at the call, grouped or not, with JOIN inputs or without, while
    a `count` fits a `not null` parameter."""
    joined = (
        "    from others\n    inner join rows as r:\n        from others\n"
        "        on r.id == others.row_id\n"
    )
    source = DEF_HEAD + (
        "query g:\n    from rows\n    group by: id\n    select:\n        id\n"
        "        a = idt(max(n))\n        b = idi(count(n))\n"
        "query a:\n    from rows\n    select:\n        a = idi(max(n))\n"
        f"query jg:\n{joined}    group by: others.id\n    select:\n"
        "        k = others.id\n        a = idi(max(r.n))\n        b = idi(count(r.n))\n"
        f"query jk:\n{joined}    group by: r.n\n    select:\n        k = idi(r.n)\n"
        "        c = count()\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idt", DEF_LINE + 5, 13, "Text not null", "Int nullable"),
        _mismatch("idi", DEF_LINE + 10, 13, "Int not null", "Int nullable"),
        _mismatch("idi", DEF_LINE + 19, 13, "Int not null", "Int nullable"),
        _mismatch("idi", DEF_LINE + 28, 13, "Int not null", "Int nullable"),
    ]


def test_a_project_def_refuses_an_imported_alias(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {
        "t.pietto": "type Cash = Int not null\nexport:\n    type Cash\n",
        "a.pietto": 'import "t.pietto":\n    type Cash\n'
        "def c(x: Cash nullable) -> Int nullable: return x\n",
    }
    assert _def_check(tmp_path, capsys, files) == [
        (
            "PIE-S2397",
            "a.pietto",
            3,
            10,
            "Def c parameter x has type Cash; a def parameter or result type is "
            "exactly Bool, Int, Float, Decimal, Text, Date, Timestamp or UUID, "
            "without arguments, or an alias of one declared in this file without "
            "arguments or `ensure`",
        )
    ]


REPEATED_DEFS = (
    "def blank(x: Text nullable) -> Bool nullable: return x is null or x == ''\n"
    "def same(x: Bool nullable) -> Bool nullable: return x\n"
    "def twice(x: Int not null) -> Bool nullable: return x <= 2 and x <= 3\n"
)
WINDOWED = (
    "(row_number() window:\n            order by:\n                {}\n        )\n"
)
JOINED = (
    "query j:\n    from rows\n    inner join others as o:\n        from rows\n"
    "        on o.row_id == rows.id\n"
)
REPEATED = {
    "qualify": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        blank" + WINDOWED.format("id"),
        [("blank", 6, 9, "Text nullable", "Int not null")],
    ),
    "qualify_whole": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        same" + WINDOWED.format("id"),
        [("same", 6, 9, "Bool nullable", "Int not null")],
    ),
    "joined_qualify": (
        JOINED + "    select:\n        a = rows.id\n    qualify:\n"
        "        blank" + WINDOWED.format("rows.id"),
        [("blank", 9, 9, "Text nullable", "Int not null")],
    ),
    "joined_select": (
        JOINED + "    select:\n        a = rows.id\n        p = blank(o.row_id)\n",
        [("blank", 8, 13, "Text nullable", "Int not null")],
    ),
    "where": (
        "query m:\n    from rows\n    where blank(n)\n    select:\n        id\n",
        [("blank", 3, 11, "Text nullable", "Int nullable")],
    ),
    "captured_whole": (
        "query c:\n    let l:\n        capture rows\n        from others\n"
        "        where same(rows.id)\n        select:\n            id\n"
        "    from rows\n    where exists l\n    select:\n        id\n",
        [("same", 5, 15, "Bool nullable", "Int not null")],
    ),
    "inner_call_in_where": (
        "query m:\n    from rows\n    where blank(idt(n))\n    select:\n        id\n",
        [("idt", 3, 17, "Text not null", "Int nullable")],
    ),
    "inner_call_in_qualify": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        blank(idt" + WINDOWED.format("id").rstrip("\n") + ")\n",
        [("idt", 6, 15, "Text not null", "Int not null")],
    ),
    "window_argument_used_twice": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        twice" + WINDOWED.format("id"),
        [],
    ),
}


@pytest.mark.parametrize(("relation", "errors"), REPEATED.values(), ids=REPEATED)
def test_a_project_reports_a_def_argument_mismatch_once(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    relation: str,
    errors: list[tuple[str, int, int, str, str]],
) -> None:
    """Each use of the argument, a typed read the project seeds among them,
    is Unknown to the body after the one report, and a window computation is
    copied for every use; nothing raises."""
    first = DEF_LINE + 3
    assert _def_check(
        tmp_path, capsys, {"a.pietto": DEF_HEAD + REPEATED_DEFS + relation}
    ) == [
        _mismatch(name, first + line - 1, column, expected, got)
        for name, line, column, expected, got in errors
    ]


IDENTITY_SELECTS = {
    "ungrouped": "query u:\n    from rows\n    select:\n        id\n        u = {}\n",
    "grouped": (
        "query u:\n    from rows\n    group by: id\n    select:\n        id\n"
        "        u = {}\n"
    ),
}


@pytest.mark.parametrize("relation", IDENTITY_SELECTS.values(), ids=IDENTITY_SELECTS)
def test_an_identity_def_over_an_unknown_field_reports_what_the_field_does(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], relation: str
) -> None:
    """The field's own error is reported once, as for the field written out."""
    reports = [
        [
            (code, path, line, message)
            for code, path, line, _, message in _def_check(
                tmp_path / name, capsys, {"a.pietto": DEF_HEAD + relation.format(text)}
            )
        ]
        for name, text in (("called", "idi(missing)"), ("written", "missing"))
    ]
    assert reports[0] == reports[1]
    assert [report[0] for report in reports[0]].count("PIE-S2102") == 1


def _forbid_project_compiler_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    def unexpected_call(*args: object, **kwargs: object) -> object:
        del args, kwargs
        raise AssertionError("project scaffold must not enter output pipelines")

    monkeypatch.setattr(cli.semantic_api, "analyze", unexpected_call)
    monkeypatch.setattr(cli.ir_api, "build_ir", unexpected_call)
    monkeypatch.setattr(cli.sql_api, "emit_postgres_sql", unexpected_call)
    monkeypatch.setattr(cli.mysql_backend, "emit_mysql_sql", unexpected_call)
    monkeypatch.setattr(cli, "build_semantic_metadata_artifact", unexpected_call)
    monkeypatch.setattr(cli, "semantic_metadata_artifact_to_json_dict", unexpected_call)
    monkeypatch.setattr(cli, "render_semantic_metadata_text", unexpected_call)


def _project_root(
    tmp_path: Path,
    *,
    include: tuple[str, ...],
    exclude: tuple[str, ...] = (),
) -> Path:
    root = tmp_path / "project"
    root.mkdir(parents=True)
    config_text = (
        "schema_version = 1\n\n"
        "[sources]\n"
        f"include = {_toml_array(include)}\n"
        f"exclude = {_toml_array(exclude)}\n"
    )
    (root / "pietto.toml").write_text(config_text, encoding="utf-8")
    return root


def _toml_array(values: tuple[str, ...]) -> str:
    return "[" + ", ".join(json.dumps(value) for value in values) + "]"


def _write(root: Path, relative_path: str, source: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path
