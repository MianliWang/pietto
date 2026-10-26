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
        "type Age = Int\n"
        "enum Status:\n"
        "    ACTIVE\n"
        "    PAUSED\n"
        "shape User:\n"
        "    id: Int\n"
        "constraint usable(value: Text) -> Bool:\n"
        "    return value is not None\n",
    )
    _write(
        root,
        "models/b.pietto",
        "derive normalize(value: Text) -> Text:\n"
        "    return lower(value)\n"
        'source users: User = postgres.table("users")\n'
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
        end_column=15,
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
        "derive Shared(value: Text) -> Text:\n"
        "    return value\n"
        'source Shared: Shared = postgres.table("shared")\n',
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
        "derive normalize(value: Text) -> Text:\n"
        "    return value\n",
    )
    _write(
        root,
        "models/b.pietto",
        "enum Shared:\n"
        "    ACTIVE\n"
        "constraint normalize(value: Text) -> Bool:\n"
        "    return value is not None\n"
        'source rows: Shared = postgres.table("rows")\n',
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
        'source raw: Raw = postgres.table("raw")\n'
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
    "    id: Int\n"
    "    n: Int | None\n"
    "    text: Text\n"
    "    row_key = unique(id)\n"
    "shape Other:\n"
    "    id: Int\n"
    "    row_id: Int\n"
    "    label: Text | None\n"
    'source rows: Row = postgres.table("rows")\n'
    'source others: Other = postgres.table("others")\n'
    "def pos(x: Int) -> Bool | None: return x > 0\n"
    "def idi(x: Int) -> Int: return x\n"
    "def idt(x: Text) -> Text: return x\n"
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
    exported = DEF_HEAD + "export (\n    source rows,\n    table pos)\n"
    caller = (
        'from "a.pietto" import (\n    source rows)\n'
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


def _uncallable(path: str, line: int, column: int, name: str, kind: str):
    return (
        "PIE-S2103",
        path,
        line,
        column,
        f"Unknown function: {name}; {name} is a {kind}, which cannot be called; "
        "write a `def` instead",
    )


def test_a_call_of_a_modules_own_constraint_or_derive_says_it_cannot_be_called(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    declared = DEF_HEAD + (
        "constraint valid(x: Text) -> Bool:\n"
        '    return x like "%a%"\n'
        "derive normalized(x: Text) -> Text:\n"
        "    return lower(x)\n"
        "export (\n    source rows)\n"
        "query q:\n    from rows\n    where valid(text)\n    select:\n        id\n"
        "        m = normalized(text)\n"
    )
    # Another module does not declare the name, so it is only unknown there.
    caller = (
        'from "a.pietto" import (\n    source rows)\n'
        "query t:\n    from rows\n    where valid(text)\n    select:\n        id\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": declared, "b.pietto": caller}) == [
        _uncallable("a.pietto", DEF_LINE + 8, 11, "valid", "constraint"),
        _uncallable("a.pietto", DEF_LINE + 11, 13, "normalized", "derive"),
        ("PIE-S2103", "b.pietto", 5, 11, "Unknown function: valid"),
    ]


def test_a_def_body_call_of_a_derive_says_it_cannot_be_called(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = DEF_HEAD + (
        "derive normalized(x: Text) -> Text:\n"
        "    return lower(x)\n"
        "def f(x: Text) -> Text: return normalized(x)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _uncallable("a.pietto", DEF_LINE + 2, 32, "normalized", "derive")
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
        "query q(k: Int, m: Int | None):\n    from rows\n"
        "    where pos(k) and pos(m)\n    select:\n        id\n"
        "        bare = idi(n)\n"
        "query c:\n    let l:\n        capture rows\n        from others\n"
        "        where pos(rows.n)\n        select:\n            id\n"
        "    from rows\n    where exists l\n    select:\n        id\n"
        "query j:\n    from rows\n    let o = others\n"
        "    inner join o on o.row_id == rows.id\n    select:\n        a = rows.id\n"
        "        p = idt(o.label)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("pos", DEF_LINE + 2, 22, "Int", "Int | None"),
        _mismatch("idi", DEF_LINE + 5, 16, "Int", "Int | None"),
        _mismatch("pos", DEF_LINE + 10, 15, "Int", "Int | None"),
        _mismatch("idt", DEF_LINE + 23, 13, "Text", "Text | None"),
    ]


def test_a_project_def_reads_local_aliases_and_null_comparisons_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A local alias is its base type in a signature; a comparison with the
    null literal is PIE-S2105 once, in an argument or made by a null
    argument, and a null argument that does not fit is only PIE-S2395, also
    where the body casts it."""
    source = DEF_HEAD + (
        "type Money = Int\n"
        "def bump(x: Money | None) -> Money | None: return x + 1\n"
        "def flag(b: Bool) -> Bool | None: return b or b\n"
        "def low(x: Int | None) -> Bool | None: return x < 3\n"
        "def fl(x: Int) -> Float | None: return Float(x)\n"
        "query q:\n    from rows\n"
        "    where flag(n == None) and low(None) and pos(None)\n"
        "    select:\n        id\n        v = bump(id)\n        w = fl(None)\n"
    )
    never = "comparison with null is never true"
    line = DEF_LINE + 7
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        (
            "PIE-S2105",
            "a.pietto",
            line,
            16,
            f"Invalid operands for operator ==: {never}; write `is None` instead",
        ),
        (
            "PIE-S2105",
            "a.pietto",
            line,
            31,
            f"Invalid operands for operator <: {never}",
        ),
        _mismatch("pos", line, 45, "Int", "null"),
        _mismatch("fl", line + 4, 13, "Int", "null"),
    ]


def test_a_project_keeps_the_typed_twin_diagnostic_of_a_null_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A NULL number beside numbers of other types, which a single file types
    as the database does, keeps its typed twin's diagnostic at the expression
    in a project, whose relations do not complete with it."""
    source = (
        "shape Row:\n    id: Int\n    n: Int | None\n    d: Decimal(9, 2)\n"
        '    fl: Float\nsource rows: Row = postgres.table("rows")\n'
        "def fn(x: Float | None) -> Float | None: return x\n"
        "query q:\n    from rows\n    select:\n        id\n"
        "        a = (None + d) + 1.5\n        b = coalesce(None + fl, 1)\n"
        "        c = fn(None + n)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        (
            "PIE-S2105",
            "a.pietto",
            12,
            13,
            "Invalid operands for operator +: expected numeric operands",
        ),
        (
            "PIE-S2104",
            "a.pietto",
            13,
            13,
            "Invalid argument types for function coalesce: expected same "
            "canonical type",
        ),
        _mismatch("fn", 14, 13, "Float | None", "Int | None"),
    ]


def test_a_legacy_flat_project_keeps_the_typed_twin_diagnostic_of_a_null_number(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    root = tmp_path / "project"
    _write(
        root,
        "pietto.toml",
        'schema_version = 1\n[sources]\ninclude = ["*.pietto"]\n',
    )
    _write(
        root,
        "a.pietto",
        "shape Row:\n    id: Int\n    n: Int | None\n    d: Decimal(9, 2)\n"
        '    fl: Float\nsource rows: Row = postgres.table("rows")\n'
        "query q:\n    from rows\n    select:\n        id\n"
        "        a = (None + d) + 1.5\n"
        "        b = coalesce(None + fl, 1)\n",
    )

    assert cli.main(["check", "--project", str(root), "--format", "json"]) == 1
    diagnostics = json.loads(capsys.readouterr().out)["diagnostics"]
    assert [
        (item["code"], item["location"]["line"], item["location"]["column"])
        for item in diagnostics
    ] == [
        ("PIE-S2105", 11, 13),
        ("PIE-S2104", 12, 13),
    ]


def test_a_project_def_reads_a_let_bound_to_null_as_null(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `let:` name bound to null, also through other lets, is a null
    argument as in a single file: PIE-S2395 alone, also where the body casts
    it, and the relation then needs no PIE-S2333."""
    source = DEF_HEAD + (
        "def fl(x: Int) -> Float | None: return Float(x)\n"
        "query q:\n    from rows\n    let k = None\n    let k2 = k\n"
        "    let k3 = k2\n    select:\n        id\n        a = idi(k)\n"
        "        b = idt(k2)\n        c = idi(k3)\n        d = fl(k)\n"
    )
    line = DEF_LINE + 8
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idi", line, 13, "Int", "null"),
        _mismatch("idt", line + 1, 13, "Text", "null"),
        _mismatch("idi", line + 2, 13, "Int", "null"),
        _mismatch("fl", line + 3, 13, "Int", "null"),
    ]


def test_a_project_def_reads_a_let_that_stands_for_null_as_written(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An argument reading a `let:` name bound to null is checked as written
    out, the literal taking its type from where it stands; a name bound to
    another always-null value is null, as in a single file."""
    source = DEF_HEAD + (
        "query q:\n    from rows\n    let k = None\n    let m = id + None\n"
        "    select:\n        id\n        a = idt(lower(k))\n"
        "        b = idi(coalesce(k, n))\n        c = idi(m)\n        d = idi(m + 1)\n"
    )
    line = DEF_LINE + 6
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idt", line, 13, "Text", "Text | None"),
        _mismatch("idi", line + 1, 13, "Int", "Int | None"),
        _mismatch("idi", line + 2, 13, "Int", "null"),
        _mismatch("idi", line + 3, 13, "Int", "null"),
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
        "    from rows\n    let p = others\n"
        "    inner join p on p.row_id == rows.id\n"
        "    let m = p.id + None > 1\n    let m2 = m\n"
    )
    source = DEF_HEAD + (
        "def bb(x: Bool) -> Bool: return x is None\n"
        "query w:\n    from rows\n    let b2 = id + None > 1\n"
        "    where bb(b2)\n    select:\n        id\n"
        "query s:\n    from rows\n    let nill = None\n"
        "    let j = coalesce(nill, n)\n    select:\n        id\n        a = idi(j)\n"
        f"query jl:\n{joined}    let c = bb(m2)\n    select:\n        k = rows.id\n"
        f"query jw:\n{joined}    where bb(m)\n    select:\n        k = rows.id\n"
        f"query js:\n{joined}    select:\n        k = rows.id\n        a = bb(m2)\n"
        f"query jo:\n{joined}    select:\n        k = rows.id\n    order by bb(not m)\n"
        f"query jt:\n{joined}    select:\n        k = rows.id\n"
        "        a = bb(p.id + None > 1)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("bb", DEF_LINE + 4, 11, "Bool", "null"),
        _mismatch("idi", DEF_LINE + 13, 13, "Int", "Int | None"),
        _mismatch("bb", DEF_LINE + 20, 13, "Bool", "null"),
        _mismatch("bb", DEF_LINE + 29, 11, "Bool", "null"),
        _mismatch("bb", DEF_LINE + 40, 13, "Bool", "null"),
        _mismatch("bb", DEF_LINE + 49, 14, "Bool", "null"),
        _mismatch("bb", DEF_LINE + 58, 13, "Bool", "null"),
    ]


@pytest.mark.parametrize(
    "spelling",
    [
        {"I1": "i1", "I2": "i2", "I8": "i8"},
        {
            "I1": "coalesce(None, 1)",
            "I2": "upper(None) + 1",
            "I8": "lower(coalesce(None, 1))",
        },
    ],
    ids=["let_names", "values_written_in"],
)
def test_a_project_let_value_ill_typed_once_the_null_it_reads_has_a_type_is_an_error(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], spelling: dict[str, str]
) -> None:
    """As in a single file, a `let:` value ill-typed once the null it reads
    takes its type reports its error in its binding, and a def argument that
    reads it, in a let or in a select, adds nothing; the value written by
    hand reports it where it is written, also as the whole argument, and its
    parameter adds nothing."""
    source = DEF_HEAD + (
        "query q:\n    from rows\n    let nill = None\n"
        "    let i1 = coalesce(nill, 1)\n    let i2 = upper(nill) + 1\n"
        "    let i8 = lower(i1)\n    let z = pos({I2})\n    select:\n        id\n"
        "        a = idt(lower({I1}))\n        b = pos({I2})\n        c = idt({I8})\n"
    ).format(**spelling)
    lower_of_int = (
        "Invalid argument type for function lower at position 1: expected Text, got Int"
    )
    not_numeric = (
        "Invalid operands for operator +: expected numeric operands; "
        "string concatenation is not supported yet"
    )
    written_in = spelling["I1"] != "i1"
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        ("PIE-S2105", "a.pietto", DEF_LINE + 4, 14, not_numeric),
        ("PIE-S2104", "a.pietto", DEF_LINE + 5, 14, lower_of_int),
        *(
            [("PIE-S2105", "a.pietto", DEF_LINE + 6, 17, not_numeric)]
            if written_in
            else []
        ),
        ("PIE-S2104", "a.pietto", DEF_LINE + 9, 17, lower_of_int),
        *(
            [
                ("PIE-S2105", "a.pietto", DEF_LINE + 10, 17, not_numeric),
                ("PIE-S2104", "a.pietto", DEF_LINE + 11, 17, lower_of_int),
            ]
            if written_in
            else []
        ),
    ]


@pytest.mark.parametrize(
    "spelling",
    [
        {"H": "h", "G": "g", "W": "w", "NILL": "nill"},
        {
            "H": "coalesce(None, id)",
            "G": "text if True else None",
            "W": "lower(coalesce(None, 1)) is None",
            "NILL": "None",
        },
    ],
    ids=["let_names", "values_written_in"],
)
def test_a_project_def_argument_reports_what_its_written_form_reports(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], spelling: dict[str, str]
) -> None:
    """As in a single file, an argument is checked with the types its `let:`
    values have written in, as the values written by hand are: a `let:` name
    the values read is never an unknown field, also when the relation's
    `let:` types are not all known (`nill`); a value ill-typed once the null
    it reads takes its type reports that in its binding (`e`) and keeps the
    type it still has (`w`); and an argument with an error of its own is not
    checked against its parameter."""
    source = DEF_HEAD + (
        "query q:\n    from rows\n    let nill = None\n    let f = id\n"
        "    let h = coalesce(nill, f)\n    let tt = True\n"
        "    let g = text if tt else nill\n    let j = coalesce(nill, 1)\n"
        "    let e = lower(j)\n    let w = e is None\n    select:\n        id\n"
        "        a = idi(len({H}))\n        b = pos(len({G}))\n        c = idi({W})\n"
        "        d = idi({NILL} + zz)\n"
    ).format(**spelling)
    line = DEF_LINE + 12
    lower_of_int = (
        "Invalid argument type for function lower at position 1: expected Text, got Int"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        ("PIE-S2104", "a.pietto", line - 4, 13, lower_of_int),
        (
            "PIE-S2104",
            "a.pietto",
            line,
            17,
            "Invalid argument type for function len at position 1: "
            "expected Text, got Int",
        ),
        _mismatch("pos", line + 1, 13, "Int", "Int | None"),
        *(
            [("PIE-S2104", "a.pietto", line + 2, 17, lower_of_int)]
            if spelling["W"] != "w"
            else []
        ),
        _mismatch("idi", line + 2, 13, "Int", "Bool"),
        ("PIE-S2102", "a.pietto", line + 3, 24, "Unknown field: zz"),
    ]


def test_a_project_def_checks_a_let_that_an_aggregate_reads(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A `let:` name passed to a def and read directly by an aggregate, also
    in `satisfying`, must fit the parameter as the value written out must:
    PIE-S2333 at the relation, as for `count(idi(n))`, grouped or not, and
    PIE-S2395 at the call in a JOIN relation, which reports its own errors."""
    source = DEF_HEAD + (
        "query g:\n    from rows\n    let f = n\n    group by id\n"
        "    select:\n        id\n        c = count(idi(f))\n"
        "query a:\n    from rows\n    let f = n\n    select:\n"
        "        s = sum(idi(f))\n"
        "query m:\n    from rows\n    let g = id\n    group by id\n"
        "    select:\n        id\n        x = max(idt(g))\n"
        "query s:\n    from rows\n    let f = n\n    group by id\n"
        "    select:\n        id\n        c = count(f)\n"
        "    having count(idi(f)) > 0\n"
        "query j:\n    from rows\n    let o = others\n"
        "    inner join o on o.row_id == rows.id\n    let f = o.label\n"
        "    group by rows.id\n    select:\n        k = rows.id\n        c = count(f)\n"
        "    having count(idt(f)) > 0\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        (
            "PIE-S2333",
            "a.pietto",
            DEF_LINE + line,
            1,
            f"Project relation semantic completion is unavailable: {name}",
        )
        for name, line in (("g", 0), ("a", 7), ("m", 12), ("s", 19))
    ] + [_mismatch("idt", DEF_LINE + 36, 18, "Text", "Text | None")]


def test_a_project_def_checks_an_aggregate_or_group_key_passed_to_it(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An aggregate passed to a def is its result, and a group key passed to
    one is that key, which must fit the parameter as in a single file:
    PIE-S2395 at the call, grouped or not, with JOIN inputs or without, while
    a `count` fits a parameter of a bare type, which is never None."""
    joined = (
        "    from others\n    let r = rows\n    inner join r on r.id == others.row_id\n"
    )
    source = DEF_HEAD + (
        "query g:\n    from rows\n    group by id\n    select:\n        id\n"
        "        a = idt(max(n))\n        b = idi(count(n))\n"
        "query a:\n    from rows\n    select:\n        a = idi(max(n))\n"
        f"query jg:\n{joined}    group by others.id\n    select:\n"
        "        k = others.id\n        a = idi(max(r.n))\n        b = idi(count(r.n))\n"
        f"query jk:\n{joined}    group by r.n\n    select:\n        k = idi(r.n)\n"
        "        c = count()\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idt", DEF_LINE + 5, 13, "Text", "Int | None"),
        _mismatch("idi", DEF_LINE + 10, 13, "Int", "Int | None"),
        _mismatch("idi", DEF_LINE + 18, 13, "Int", "Int | None"),
        _mismatch("idi", DEF_LINE + 26, 13, "Int", "Int | None"),
    ]


def test_a_project_relation_selecting_an_unfit_def_argument_has_no_known_columns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A field or `let:` name passed to a def it does not fit is unknown, as
    in a single file: a relation that selects it, also as a relation let or
    from another module, has no known columns for the relations that read
    it, which report PIE-S2333 as when a computed output has an error, never
    the field's or the let's type. One that fits keeps the field's type."""
    source = DEF_HEAD + (
        "query q1:\n    from rows\n    let u = True\n    select:\n"
        "        id\n        f = idi(n)\n        t = idi(text)\n        b = idi(u)\n"
        "query q2:\n    from q1\n    select:\n        id\n        x = lower(f)\n"
        "        y = t + 1\n        z = not b\n"
        "query q3:\n    let base:\n        from rows\n        select:\n"
        "            id\n            w = idt(n)\n    from base\n    select:\n"
        "        id\n"
        "query fit:\n    from rows\n    select:\n        o = idi(id)\n"
        "query reader:\n    from fit\n    select:\n        x = lower(o)\n"
        "export (\n    query q1)\n"
    )
    files = {
        "a.pietto": source,
        "b.pietto": 'from "a.pietto" import (\n    query q1)\n'
        "query q4:\n    from q1\n    select:\n        id\n",
    }
    assert _def_check(tmp_path, capsys, files) == [
        _mismatch("idi", DEF_LINE + 5, 13, "Int", "Int | None"),
        _mismatch("idi", DEF_LINE + 6, 13, "Int", "Text"),
        _mismatch("idi", DEF_LINE + 7, 13, "Int", "Bool"),
        (
            "PIE-S2333",
            "a.pietto",
            DEF_LINE + 8,
            1,
            "Project relation semantic completion is unavailable: q2",
        ),
        _mismatch("idt", DEF_LINE + 20, 17, "Text", "Int | None"),
        (
            "PIE-S2333",
            "a.pietto",
            DEF_LINE + 15,
            1,
            "Project relation semantic completion is unavailable: q3",
        ),
        (
            "PIE-S2104",
            "a.pietto",
            DEF_LINE + 31,
            13,
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        ),
        (
            "PIE-S2333",
            "b.pietto",
            3,
            1,
            "Project relation semantic completion is unavailable: q4",
        ),
    ]


def test_a_grouped_project_relation_selecting_an_unfit_def_key_has_no_known_columns(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A group key passed to a def it does not fit, a field, a `let:` key or
    an unaliased qualified name, is unknown as without GROUP BY: a relation
    that reads its relation reports PIE-S2333, as for a key passed to a def
    of another body, never the key's type (before: PIE-S2104 at `lower`). A
    key that fits keeps its type."""
    source = DEF_HEAD + (
        "query g1:\n    from rows\n    group by n\n    select:\n        k = idi(n)\n"
        "        c = count()\n"
        "query g2:\n    from rows\n    let w = n + 1\n    group by w\n"
        "    select:\n        k = idi(w)\n        c = count()\n"
        "query g3:\n    from rows\n    group by rows.n\n    select:\n"
        "        idi(rows.n)\n        c = count()\n"
        "query fit:\n    from rows\n    group by id\n    select:\n        k = idi(id)\n"
        "        c = count()\n"
        "query r1:\n    from g1\n    select:\n        x = lower(k)\n"
        "query r2:\n    from g2\n    select:\n        x = lower(k)\n"
        "query r3:\n    from g3\n    select:\n        x = lower(n)\n"
        "query r4:\n    from fit\n    select:\n        x = lower(k)\n"
    )
    assert _def_check(tmp_path, capsys, {"a.pietto": source}) == [
        _mismatch("idi", DEF_LINE + 4, 13, "Int", "Int | None"),
        _mismatch("idi", DEF_LINE + 11, 13, "Int", "Int of unknown nullability"),
        _mismatch("idi", DEF_LINE + 17, 9, "Int", "Int | None"),
        *(
            (
                "PIE-S2333",
                "a.pietto",
                DEF_LINE + line,
                1,
                f"Project relation semantic completion is unavailable: {name}",
            )
            for name, line in (("r1", 25), ("r2", 29), ("r3", 33))
        ),
        (
            "PIE-S2104",
            "a.pietto",
            DEF_LINE + 40,
            13,
            "Invalid argument type for function lower at position 1: "
            "expected Text, got Int",
        ),
    ]


def test_a_project_relation_builds_its_def_argument_check_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """A relation's row schema checks each select item that passes a def,
    with the input row and `let:` values built once for the relation, and
    builds nothing for a relation whose items pass no def, so its check grows
    with its size (before: both once per item that selects a field or a
    `let:` name, cubic in a relation with many `let:` names, def or not)."""
    from pietto._project import let_scope_facts, row_expression_type_facts

    calls: dict[str, int] = {}
    for module, name in (
        (let_scope_facts, "checked_let_values"),
        (row_expression_type_facts, "project_row_schema_to_semantic_row_schema"),
        (row_expression_type_facts, "reports_unfit_def_argument"),
    ):

        def counting(*args: object, _run=getattr(module, name), _name=name, **kw):
            calls[_name] = calls.get(_name, 0) + 1
            return _run(*args, **kw)

        monkeypatch.setattr(module, name, counting)

    def check(size: int, item: str) -> dict[str, int]:
        calls.clear()
        lets = "".join(f"    let j{index} = n + {index}\n" for index in range(size))
        items = "".join(
            f"        v{index} = {item.format(f'j{index}')}\n" for index in range(size)
        )
        source = (
            DEF_HEAD
            + "def idn(x: Int | None) -> Int | None: return x\n"
            + f"query q:\n    from rows\n{lets}    select:\n        id\n{items}"
        )
        root = tmp_path / f"{size}-{'def' if '(' in item else 'defless'}"
        assert _def_check(root, capsys, {"a.pietto": source}) == []
        return dict(calls)

    defless = check(4, "{}")
    assert "reports_unfit_def_argument" not in defless
    assert check(8, "{}") == defless
    with_def = check(4, "idn({})")
    assert with_def.pop("reports_unfit_def_argument") == 4
    assert with_def["checked_let_values"] == 1
    assert {
        name: count
        for name, count in check(8, "idn({})").items()
        if name != "reports_unfit_def_argument"
    } == with_def


def test_a_project_def_refuses_an_imported_alias(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    files = {
        "t.pietto": "type Cash = Int\nexport (\n    type Cash)\n",
        "a.pietto": 'from "t.pietto" import (\n    type Cash)\n'
        "def c(x: Cash | None) -> Int | None: return x\n",
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
    "def blank(x: Text | None) -> Bool | None: return x is None or x == ''\n"
    "def same(x: Bool | None) -> Bool | None: return x\n"
    "def twice(x: Int) -> Bool | None: return x <= 2 and x <= 3\n"
)
WINDOWED = "(row_number() window(order by {}))\n"
JOINED = (
    "query j:\n    from rows\n    let o = others\n"
    "    inner join o on o.row_id == rows.id\n"
)
REPEATED = {
    "qualify": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        blank" + WINDOWED.format("id"),
        [("blank", 6, 9, "Text | None", "Int")],
    ),
    "qualify_whole": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        same" + WINDOWED.format("id"),
        [("same", 6, 9, "Bool | None", "Int")],
    ),
    "joined_qualify": (
        JOINED + "    select:\n        a = rows.id\n    qualify:\n"
        "        blank" + WINDOWED.format("rows.id"),
        [("blank", 8, 9, "Text | None", "Int")],
    ),
    "joined_select": (
        JOINED + "    select:\n        a = rows.id\n        p = blank(o.row_id)\n",
        [("blank", 7, 13, "Text | None", "Int")],
    ),
    "where": (
        "query m:\n    from rows\n    where blank(n)\n    select:\n        id\n",
        [("blank", 3, 11, "Text | None", "Int | None")],
    ),
    "captured_whole": (
        "query c:\n    let l:\n        capture rows\n        from others\n"
        "        where same(rows.id)\n        select:\n            id\n"
        "    from rows\n    where exists l\n    select:\n        id\n",
        [("same", 5, 15, "Bool | None", "Int")],
    ),
    "inner_call_in_where": (
        "query m:\n    from rows\n    where blank(idt(n))\n    select:\n        id\n",
        [("idt", 3, 17, "Text", "Int | None")],
    ),
    "inner_call_in_qualify": (
        "query q:\n    from rows\n    select:\n        id\n    qualify:\n"
        "        blank(idt" + WINDOWED.format("id").rstrip("\n") + ")\n",
        [("idt", 6, 15, "Text", "Int")],
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
        "query u:\n    from rows\n    group by id\n    select:\n        id\n"
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
