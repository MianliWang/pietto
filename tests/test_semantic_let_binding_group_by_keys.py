from __future__ import annotations

import json
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

import pytest

import pietto.cli as cli
from pietto._project.check import check_project_parse_only
from pietto._project.model import (
    ProjectCompilationMode,
    ProjectRelationRowSchemaStatus,
    build_empty_project_semantic_result,
)
from pietto._project.project_completed_semantics import (
    build_project_completed_semantic_result,
)
from pietto.ast_nodes import QueryDef, TableDef
from pietto.errors import Severity
from pietto.ir import FieldRefIR, RelationIR, ScriptIR, build_ir
from pietto.parser_api import parse_source
from pietto.semantic import EffectiveNullability, RowField, SemanticResult, analyze
from pietto.sql import SqlArtifactKind, emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

SOURCE_PREFIX = (
    "shape Order:\n"
    "    id: Int\n"
    "    amount: Int\n"
    "    tax: Int\n"
    "    status: Text\n"
    "    region: Text | None\n"
    "    active: Bool\n"
    'source orders: Order = postgres.table("orders")\n'
)
MYSQL_SOURCE_PREFIX = SOURCE_PREFIX.replace("postgres.table", "mysql.table")


def test_group_by_direct_field_row_let_is_semantically_accepted() -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["status", "total"]
    _assert_field(schema.fields["status"], "Text", EffectiveNullability.NON_NULL)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_group_by_qualified_and_chained_field_row_lets_are_semantically_accepted() -> (
    None
):
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let region_key = orders.region\n"
        "    let bucket = region_key\n"
        "    group by:\n"
        "        bucket\n"
        "    select:\n"
        "        region = orders.region\n"
        "        total = count()\n"
    )
    relation = _relation_ast(semantic)
    schema = semantic.model.relation_row_schemas[relation]

    assert _errors(semantic) == []
    assert list(schema.fields) == ["region", "total"]
    _assert_field(schema.fields["region"], "Text", EffectiveNullability.NULLABLE)
    _assert_field(schema.fields["total"], "Int", EffectiveNullability.NON_NULL)


def test_ir_group_keys_inline_expand_row_let_names_to_field_refs() -> None:
    relation = _relation_ir(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let status_key = status\n"
        "    let region_key = orders.region\n"
        "    let bucket = region_key\n"
        "    group by:\n"
        "        status_key\n"
        "        bucket\n"
        "    select:\n"
        "        status\n"
        "        region = orders.region\n"
        "        total = count()\n"
    )

    assert [(key.name, key.qualifier) for key in relation.group_keys] == [
        ("status", ()),
        ("region", ("orders",)),
    ]
    assert not _field_refs_named(relation, {"status_key", "region_key", "bucket"})


@pytest.mark.parametrize(
    ("prefix", "dialect", "expected_fragments", "forbidden"),
    [
        (
            SOURCE_PREFIX,
            "postgres",
            (
                'GROUP BY\n    "status"',
                'COUNT(*) AS "total"',
            ),
            ('"key"', "WITH ", "FROM (SELECT"),
        ),
        (
            MYSQL_SOURCE_PREFIX,
            "mysql",
            (
                "GROUP BY\n    `status`",
                "COUNT(*) AS `total`",
            ),
            ("`key`", "WITH ", "FROM (SELECT"),
        ),
    ],
)
def test_sql_inlines_group_by_row_let_without_hidden_layers(
    prefix: str,
    dialect: str,
    expected_fragments: tuple[str, str],
    forbidden: tuple[str, ...],
) -> None:
    sql = _sql_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
        prefix=prefix,
        dialect=dialect,
    )

    for fragment in expected_fragments:
        assert fragment in sql
    for fragment in forbidden:
        if fragment.endswith(" "):
            assert fragment not in sql.upper()
        else:
            assert fragment not in sql


def test_cli_json_and_explain_shapes_remain_compatible(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_path = _write_source(
        tmp_path,
        "group_by_let.pietto",
        "query grouped_orders:\n"
        "    from orders\n"
        "    let key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        status\n"
        "        total = count()\n",
    )

    assert cli.main(["check", str(source_path)]) == 0
    check_output = capsys.readouterr()
    assert check_output.err == ""
    assert f"OK: {source_path}" in check_output.out

    assert (
        cli.main(
            [
                "emit-sql",
                str(source_path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        )
        == 0
    )
    emit_document = _read_json(capsys)
    assert emit_document["ok"] is True
    assert emit_document["diagnostics"] == []
    assert len(cast(list[object], emit_document["artifacts"])) == 1
    assert "let_scopes" not in json.dumps(emit_document)

    assert cli.main(["explain", str(source_path), "--format", "json"]) == 0
    explain_document = _read_json(capsys)
    assert explain_document["ok"] is True
    assert explain_document["artifact"] == "Semantic Metadata Artifact v1"
    assert "metadata" in explain_document
    assert "let_scopes" not in json.dumps(explain_document)


@pytest.mark.parametrize(
    ("body", "expected_code"),
    [
        (
            "    from orders\n"
            "    let gross = amount + tax\n"
            "    group by:\n"
            "        gross\n"
            "    select:\n"
            "        amount\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let normalized = lower(trim(status))\n"
            "    group by:\n"
            "        normalized\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let one = 1\n"
            "    group by:\n"
            "        one\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n"
            "    having:\n"
            "        key > 0\n",
            "PIE-S2324",
        ),
        (
            "    from orders\n"
            "    let key = status\n"
            "    select:\n"
            "        amount\n"
            "    limit key\n",
            "PIE-S2307",
        ),
        (
            "    from orders\n"
            "    let gross = status\n"
            "    group by:\n"
            "        orders.gross\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2102",
        ),
        (
            "    from orders\n"
            "    let key = status\n"
            "    group by:\n"
            "        key\n"
            "    select:\n"
            "        key\n"
            "        total = count()\n",
            "PIE-S2329",
        ),
        (
            "    from orders\n"
            "    let key = status\n"
            "    select:\n"
            "        smallest = min(key)\n",
            "PIE-S2314",
        ),
        (
            "    from orders\n"
            "    let key = status\n"
            "    select:\n"
            "        largest = max(key)\n",
            "PIE-S2314",
        ),
    ],
)
def test_non_slice4_group_by_let_consumers_remain_rejected(
    body: str,
    expected_code: str,
) -> None:
    semantic = _semantic_for("query grouped_orders:\n" + body)

    assert expected_code in _error_codes(semantic)


def test_a_refused_let_group_key_reports_only_the_refusal() -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n"
        "    from orders\n"
        "    let key = status\n"
        "    group by:\n"
        "        key\n"
        "    select:\n"
        "        key\n"
        "        total = count()\n"
    )

    # The GROUP BY key and SELECT reads of the refused name report nothing more.
    assert _errors(semantic) == [
        (
            "PIE-S2329",
            "Let binding conflicts with projection output name: key; a query with "
            "GROUP BY cannot select a `let` name here yet: write status in place of key",
        )
    ]


COMPUTED_KEY_RELATION = (
    "query grouped_orders:\n"
    "    from orders\n"
    "    let gross = amount + tax\n"
    "    group by:\n"
    "        gross\n"
    "    select:\n"
    "        gross\n"
    "        largest = max(gross)\n"
    "        total = count()\n"
)


@pytest.mark.parametrize(
    ("schema_version", "mode"),
    (
        (1, ProjectCompilationMode.LEGACY_FLAT),
        (2, ProjectCompilationMode.EXPLICIT_MODULES),
    ),
)
def test_computed_let_keys_and_let_extrema_follow_their_mode_law(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    schema_version: int,
    mode: ProjectCompilationMode,
) -> None:
    """EXPLICIT_MODULES completes the relation; the other laws keep refusing it."""

    # Reads of the refused binding name add no Unknown field diagnostics; the
    # refusal says where the relation is accepted.
    assert _errors(_semantic_for(COMPUTED_KEY_RELATION)) == [
        (
            "PIE-S2329",
            "Let binding conflicts with projection output name: gross; a query with "
            "GROUP BY cannot select a computed `let` value here yet: group by it and "
            "select it in an EXPLICIT_MODULES project (schema version 2)",
        ),
    ]

    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (root / "main.pietto").write_text(
        SOURCE_PREFIX + COMPUTED_KEY_RELATION, encoding="utf-8"
    )
    assert cli.main(["check", "--project", str(root)]) == 0
    captured = capsys.readouterr()
    assert captured.out.startswith("Project check OK: .\n") and captured.err == ""

    semantic_result = build_empty_project_semantic_result(
        check_project_parse_only(root)
    )
    assert semantic_result.compilation_mode is mode
    if mode is ProjectCompilationMode.LEGACY_FLAT:
        assert semantic_result.model is not None
        (state,) = semantic_result.model.relation_row_schema_states.values()
        assert state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        return
    completed = build_project_completed_semantic_result(semantic_result)
    assert completed.ok and completed.diagnostics == ()


UNAVAILABLE = (
    "PIE-S2333",
    "Project relation semantic completion is unavailable: grouped_orders",
)


@pytest.mark.parametrize(
    ("let_lines", "tail", "expected"),
    (
        (
            "",
            "    group by:\n        bucket\n    select:\n        bucket\n"
            "        total = count()\n"
            "        r = row_number() window(order by bucket asc)\n",
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window order expression must be a direct field",
            ),
        ),
        (
            "",
            "    group by:\n        bucket\n    select:\n        bucket\n"
            "        total = count()\n"
            "        r = row_number() window(partition by bucket order by total asc)\n",
            (
                "PIE-S2103",
                "Unsupported window computation for function row_number: "
                "window partition expression must be a direct field",
            ),
        ),
        (
            "    let alias = bucket\n",
            "    group by:\n        alias\n    select:\n        total = count()\n",
            UNAVAILABLE,
        ),
        (
            "",
            "    group by:\n        orders.bucket\n    select:\n"
            "        total = count()\n",
            UNAVAILABLE,
        ),
        (
            "",
            "    group by:\n        bucket\n        bucket\n    select:\n"
            "        total = count()\n",
            UNAVAILABLE,
        ),
        (
            "",
            "    group by:\n        bucket\n    select:\n        b = bucket\n"
            "        total = count()\n    having:\n        b > 0\n",
            UNAVAILABLE,
        ),
    ),
    ids=(
        "window_order",
        "window_partition",
        "alias",
        "qualified",
        "duplicate",
        "satisfying",
    ),
)
def test_explicit_module_computed_keys_keep_their_documented_refusals(
    tmp_path: Path,
    let_lines: str,
    tail: str,
    expected: tuple[str, str],
) -> None:
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        SOURCE_PREFIX
        + "query grouped_orders:\n    from orders\n    let bucket = amount * 2\n"
        + let_lines
        + tail,
        encoding="utf-8",
    )
    completed = build_project_completed_semantic_result(
        build_empty_project_semantic_result(check_project_parse_only(tmp_path))
    )

    assert not completed.ok
    assert [(d.code, d.message) for d in completed.diagnostics] == [expected]


def _semantic_for(source: str) -> SemanticResult:
    result = parse_source(SOURCE_PREFIX + source, path="phase43-slice4.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    return analyze(result.ast)


def _relation_ast(semantic: SemanticResult) -> TableDef | QueryDef:
    for definition in semantic.model.relation_row_schemas:
        if definition.name == "grouped_orders":
            return definition
    raise AssertionError("grouped_orders relation not found")


def _relation_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> RelationIR:
    script_ir = _script_ir(source, prefix=prefix)
    relation = script_ir.definitions[-1]
    assert isinstance(relation, RelationIR)
    return relation


def _script_ir(source: str, *, prefix: str = SOURCE_PREFIX) -> ScriptIR:
    result = parse_source(prefix + source, path="phase43-slice4.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    semantic = analyze(result.ast)
    assert semantic.diagnostics == ()
    assert semantic.script is not None
    ir_result = build_ir(semantic.script, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return ir_result.ir


def _sql_for(source: str, *, prefix: str, dialect: str) -> str:
    script_ir = _script_ir(source, prefix=prefix)
    result = (
        emit_mysql_sql(script_ir)
        if dialect == "mysql"
        else emit_postgres_sql(script_ir)
    )
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    assert result.artifacts[0].kind is SqlArtifactKind.RELATION
    return result.artifacts[0].sql


def _assert_field(
    field: RowField,
    expected_type: str,
    expected_nullability: EffectiveNullability,
) -> None:
    assert field.resolved_type.name == expected_type
    assert field.nullability is expected_nullability


def _error_codes(semantic: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _errors(semantic: SemanticResult) -> list[tuple[str, str]]:
    return [
        (diagnostic.code, diagnostic.message)
        for diagnostic in semantic.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]


def _write_source(tmp_path: Path, filename: str, relation_source: str) -> Path:
    path = tmp_path / filename
    path.write_text(SOURCE_PREFIX + relation_source, encoding="utf-8")
    return path


def _read_json(capsys: pytest.CaptureFixture[str]) -> dict[str, object]:
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out.endswith("\n")
    return cast(dict[str, object], json.loads(captured.out))


def _field_refs_named(relation: RelationIR, names: set[str]) -> bool:
    return any(ref.name in names for ref in _field_refs(relation))


def _field_refs(value: object) -> tuple[FieldRefIR, ...]:
    refs: list[FieldRefIR] = []
    if isinstance(value, FieldRefIR):
        refs.append(value)
    if isinstance(value, tuple):
        for item in value:
            refs.extend(_field_refs(item))
    elif is_dataclass(value) and not isinstance(value, type):
        for field in fields(value):
            refs.extend(_field_refs(getattr(value, field.name)))
    return tuple(refs)


_GROUPED_LET = """shape Order:
    id: Int
    status: Text
source orders: Order = postgres.table("orders")
query q:
    from orders
    let key = {value}
    group by:
        {key}
    select:
{items}        n = count()
"""
_LET_FIELD = "a query with GROUP BY cannot select a `let` name here yet: write {} in place of key"
_COMPUTED_SELECT = (
    "a query with GROUP BY cannot select a computed `let` value here yet: group by "
    "it and select it in an EXPLICIT_MODULES project (schema version 2)"
)
_COMPUTED_KEY = (
    "a query cannot group by a computed `let` value here yet: group by it in an "
    "EXPLICIT_MODULES project (schema version 2)"
)
_CONFLICT = "Let binding conflicts with projection output name: key; "


@pytest.mark.parametrize(
    ("value", "key", "items", "expected"),
    (
        (
            "status",
            "key",
            "        k = key\n",
            [
                (
                    "PIE-S2102",
                    "Unknown field: key; " + _LET_FIELD.format("status"),
                    11,
                    13,
                )
            ],
        ),
        (
            "orders.status",
            "key",
            "        key\n",
            [("PIE-S2329", _CONFLICT + _LET_FIELD.format("orders.status"), 7, 5)],
        ),
        (
            "lower(status)",
            "key",
            "        key\n",
            [("PIE-S2329", _CONFLICT + _COMPUTED_SELECT, 7, 5)],
        ),
        (
            "lower(status)",
            "key",
            "",
            [("PIE-S2102", "Unknown field: key; " + _COMPUTED_KEY, 9, 9)],
        ),
        # A `let` that is no GROUP BY key is named so, computed or not.
        (
            "lower(status)",
            "status",
            "        status\n        k = key\n",
            [("PIE-S2102", "Unknown field: key; key is not a GROUP BY key", 12, 13)],
        ),
        (
            "status",
            "id",
            "        id\n        k = key\n",
            [("PIE-S2102", "Unknown field: key; key is not a GROUP BY key", 12, 13)],
        ),
        (
            "orders.status",
            "id",
            "        key\n",
            [("PIE-S2329", _CONFLICT + "key is not a GROUP BY key", 7, 5)],
        ),
        # A `let` of a field that a key groups by is that key.
        (
            "status",
            "orders.status",
            "        k = key\n",
            [
                (
                    "PIE-S2102",
                    "Unknown field: key; " + _LET_FIELD.format("status"),
                    11,
                    13,
                )
            ],
        ),
        # What the field hint says to write is accepted.
        ("status", "key", "        k = status\n", []),
    ),
    ids=(
        "select_field",
        "self_field",
        "self_computed",
        "key_computed",
        "select_computed_not_key",
        "select_field_not_key",
        "self_field_not_key",
        "select_field_of_key",
        "fixed",
    ),
)
def test_single_file_grouped_let_reads_say_what_to_write(
    value: str, key: str, items: str, expected: list[tuple[str, str, int, int]]
) -> None:
    parsed = parse_source(_GROUPED_LET.format(value=value, key=key, items=items))
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert [
        (d.code, d.message, d.location.line, d.location.column)
        for d in analyze(parsed.ast).diagnostics
    ] == expected


def test_an_explicit_module_project_groups_by_and_selects_a_computed_let(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """What the computed hints say to write is accepted in a project."""

    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    (tmp_path / "main.pietto").write_text(
        _GROUPED_LET.format(value="lower(status)", key="key", items="        key\n"),
        encoding="utf-8",
    )
    code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    assert (code, _read_json(capsys)["diagnostics"]) == (0, [])
