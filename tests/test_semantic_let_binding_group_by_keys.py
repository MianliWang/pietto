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

    status_key, region_key = relation.group_keys
    assert isinstance(status_key, FieldRefIR)
    assert isinstance(region_key, FieldRefIR)
    assert (status_key.name, status_key.qualifier) == ("status", ())
    assert (region_key.name, region_key.qualifier) == ("region", ("orders",))
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
            "PIE-S2318",
        ),
        (
            "    from orders\n"
            "    let normalized = lower(trim(status))\n"
            "    group by:\n"
            "        normalized\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2318",
        ),
        (
            "    from orders\n"
            "    let one = 1\n"
            "    group by:\n"
            "        one\n"
            "    select:\n"
            "        status\n"
            "        total = count()\n",
            "PIE-S2318",
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
        "    let base = lower(status)\n"
        "    let key = base\n"
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
            "GROUP BY cannot select a computed `let` value here yet: select key in "
            "one query, then group by key in another that reads it with `from`",
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
    """A single file and EXPLICIT_MODULES accept the relation; LEGACY_FLAT
    passes its check without a CONCRETE row schema."""

    # Grouping opens, and a single file takes `max` of the numeric `let` key
    # as a project does (PL.48 (3)).
    assert _errors(_semantic_for(COMPUTED_KEY_RELATION)) == []

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
            (
                "PIE-S2102",
                "Unknown field: alias; a query cannot group by a computed `let` "
                "value here yet: select alias in one query, then group by alias "
                "in another that reads it with `from`",
            ),
        ),
        (
            # A let name is no field of its input, as in a single file.
            "",
            "    group by:\n        orders.bucket\n    select:\n"
            "        total = count()\n",
            ("PIE-S2102", "Unknown field: orders.bucket"),
        ),
        (
            "",
            "    group by:\n        bucket\n        bucket\n    select:\n"
            "        total = count()\n",
            ("PIE-S2317", "Duplicate GROUP BY key: bucket"),
        ),
        (
            "",
            "    group by:\n        bucket\n    select:\n        b = bucket\n"
            "        total = count()\n    having:\n        b > 0\n",
            (
                "PIE-S2326",
                "Having output is not a group-key or direct aggregate projection: b",
            ),
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
    """Each refusal is the diagnostic a single file reports."""
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
_TWO_QUERIES = (
    "select key in one query, then group by key in another that reads it with `from`"
)
_COMPUTED_SELECT = (
    "a query with GROUP BY cannot select a computed `let` value here yet: "
    + _TWO_QUERIES
)
_COMPUTED_KEY = (
    "a query cannot group by a computed `let` value here yet: " + _TWO_QUERIES
)
_CONFLICT = "Let binding conflicts with projection output name: key; "


@pytest.mark.parametrize(
    ("value", "key", "items", "expected"),
    (
        (
            "lower(status)",
            "key",
            "        key\n",
            [],
        ),
        (
            "lower(status)",
            "key",
            "",
            [],
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
        ("status", "key", "        k = status\n", []),
    ),
    ids=(
        "self_computed",
        "key_computed",
        "select_computed_not_key",
        "select_field_not_key",
        "self_field_not_key",
        "select_key_field",
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


# H3 (4): a `let` that renames a field that GROUP BY groups by, written as
# the field or as such a name, reads that key wherever the field would.
_RENAMED_KEY_FORMS = {
    "self": ("status", "key", "        key\n", ""),
    "projected": ("status", "key", "        k = key\n", ""),
    "field_key": ("status", "status", "        key\n", ""),
    "field_key_projected": ("status", "orders.status", "        k = key\n", ""),
    "qualified": ("orders.status", "key", "        key\n", ""),
    "ordered": ("status", "key", "        k = key\n", "    order by key\n"),
    "having": ("status", "key", "        k = key\n", '    having k == "open"\n'),
    "having_field_key": (
        "status",
        "status",
        "        key\n",
        '    having key == "open"\n',
    ),
    # Under a `let` key, `having` also reads the selected field.
    "having_key_field": (
        "status",
        "key",
        "        status\n",
        '    having status == "open"\n',
    ),
}


@pytest.mark.parametrize("dialect", ("postgres", "mysql"))
@pytest.mark.parametrize("form", sorted(_RENAMED_KEY_FORMS))
def test_a_single_file_selects_a_let_that_renames_a_key_field(
    form: str, dialect: str
) -> None:
    value, key, items, tail = _RENAMED_KEY_FORMS[form]
    source = _GROUPED_LET.format(value=value, key=key, items=items) + tail
    if dialect == "mysql":
        source = source.replace("postgres.table", "mysql.table")
    parsed = parse_source(source)
    assert parsed.ast is not None and parsed.diagnostics == ()
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    output = items.split("=")[0].strip()
    (relation,) = semantic.model.relation_row_schemas.values()
    assert list(relation.fields) == [output, "n"]
    _assert_field(relation.fields[output], "Text", EffectiveNullability.NON_NULL)
    assert semantic.script is not None
    ir = build_ir(semantic.script, semantic.model)
    assert ir.diagnostics == () and ir.ir is not None
    result = (emit_mysql_sql if dialect == "mysql" else emit_postgres_sql)(ir.ir)
    assert result.diagnostics == ()
    q = "`" if dialect == "mysql" else '"'
    bare, qualified = f"{q}status{q}", f"{q}orders{q}.{q}status{q}"
    # Each read keeps its own spelling, as reads of the field itself do.
    selected = qualified if "." in value else bare
    grouped = qualified if "." in value + key else bare
    expected = (
        f"SELECT\n    {selected} AS {q}{output}{q},\n    COUNT(*) AS {q}n{q}\n"
        f"FROM {q}orders{q}"
        + (f" AS {q}orders{q}" if "." in value + key else "")
        + f"\nGROUP BY\n    {grouped}"
        + (f"\nHAVING\n    {grouped} = 'open'" if "having" in tail else "")
        + (f"\nORDER BY\n    {grouped} ASC" if "order by" in tail else "")
    )
    assert [artifact.sql for artifact in result.artifacts] == [expected]


@pytest.mark.parametrize("key", ("key", "status"))
@pytest.mark.parametrize("items", ("        key\n", "        k = key\n"))
def test_a_let_that_renames_a_key_field_is_selected_over_an_unknown_row(
    key: str, items: str
) -> None:
    """H3 (4): over a source without a shape a single file selects such a
    `let`, by its name or as another output's value, as it selects the field.
    Before: PIE-S2329 for `key`, PIE-S2102 with a hint for `k = key`."""
    source = _GROUPED_LET.format(value="status", key=key, items=items)
    parsed = parse_source(
        'source orders = postgres.table("orders")\n'
        + source[source.index("query q:") :]
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert [(d.code, d.severity) for d in analyze(parsed.ast).diagnostics] == [
        ("PIE-S2303", Severity.WARNING)
    ]


_SCALAR_OF_KEY = """shape Order:
    id: Int
    status: Text
source orders: Order = postgres.table("orders")
query q:
    from orders
    let key = status
    group by {key}
    select:
        {selected}
        next = {read}
"""


@pytest.mark.parametrize("read", ("lower({})", "{} + 1"))
@pytest.mark.parametrize("selected", ("key", "status"))
@pytest.mark.parametrize("key", ("key", "status"))
def test_a_grouped_scalar_reads_a_let_that_renames_a_key_field_as_the_field(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    key: str,
    selected: str,
    read: str,
) -> None:
    """H3 (4): a grouped scalar projection without aggregates that reads such
    a `let` reports what it reports reading the field, PIE-S2319 beside its
    own errors, in a single file and in an explicit-module project. Before:
    a single file also reported PIE-S2102 for the name."""
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n', encoding="utf-8"
    )
    path = tmp_path / "main.pietto"
    found = []
    for name in ("key", "status"):
        path.write_text(
            _SCALAR_OF_KEY.format(key=key, selected=selected, read=read.format(name)),
            encoding="utf-8",
        )
        for arguments in (["check", str(path)], ["check", "--project", str(tmp_path)]):
            assert cli.main([*arguments, "--format", "json"]) == 1
            diagnostics = cast(
                list[dict[str, dict[str, object]]], _read_json(capsys)["diagnostics"]
            )
            found.append(
                [
                    (
                        d["code"],
                        d["message"],
                        d["location"]["line"],
                        d["location"]["column"],
                    )
                    for d in diagnostics
                ]
            )
    assert found[1:] == found[:1] * 3
    assert [row[0] for row in found[0]] == (
        ["PIE-S2105", "PIE-S2319"] if "+" in read else ["PIE-S2319"]
    )


@pytest.mark.parametrize("schema_version", (None, 2))
def test_a_let_key_beside_its_field_is_a_duplicate_group_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], schema_version: int | None
) -> None:
    """`group by key, status` after `let key = status` groups by `status`
    twice, as `group by status, status` does, in a single file and in a
    project. Before: PIE-S2329 in a single file, PIE-S2333 in a project."""
    source = _GROUPED_LET.format(
        value="status", key="key, status", items="        key\n"
    )
    path = tmp_path / "main.pietto"
    path.write_text(source, encoding="utf-8")
    if schema_version is None:
        arguments = ["check", str(path), "--format", "json"]
    else:
        (tmp_path / "pietto.toml").write_text(
            f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
            encoding="utf-8",
        )
        arguments = ["check", "--project", str(tmp_path), "--format", "json"]
    assert cli.main(arguments) == 1
    diagnostics = cast(list[dict[str, object]], _read_json(capsys)["diagnostics"])
    assert [(d["code"], d["message"]) for d in diagnostics] == [
        ("PIE-S2317", "Duplicate GROUP BY key: status")
    ]


_JOINED_LET = """shape Row:
    id: Int
    key: Int | None
    row_key = unique(id)
source lhs: Row = postgres.table("lhs")
source rhs: Row = postgres.table("rhs")
query q:
    from lhs
    let r = rhs
    inner join r on lhs.id == r.id
{lets}    group by {key}
    select:
        {items}
        n = count()
    having {output} > 1
"""


@pytest.mark.parametrize(
    ("key", "items", "output"),
    (("k", "x = k", "x"), ("r.key", "x = k", "x"), ("k", "k", "k")),
)
def test_having_reads_a_joined_let_that_renames_a_key_field_in_both_modes(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    key: str,
    items: str,
    output: str,
) -> None:
    """H3 (4): over JOIN inputs `having` reads an output that is such a
    `let` in a single file, with the SQL of the field-spelled query, as a
    project does. Before: PIE-S2326 in a single file."""
    source = _JOINED_LET.format(
        lets="    let k = r.key\n", key=key, items=items, output=output
    )
    control = _JOINED_LET.format(
        lets="", key="r.key", items=f"{output} = r.key", output=output
    )
    assert _sql_for(source, prefix="", dialect="postgres") == _sql_for(
        control, prefix="", dialect="postgres"
    )
    (tmp_path / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (tmp_path / "main.pietto").write_text(source, encoding="utf-8")
    code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    assert (code, _read_json(capsys)["diagnostics"]) == (0, [])


def test_the_two_query_route_the_computed_key_hint_names_is_accepted() -> None:
    parsed = parse_source(
        "shape Order:\n    id: Int\n    status: Text\n"
        'source orders: Order = postgres.table("orders")\n'
        "query keyed:\n    from orders\n    let key = lower(status)\n"
        "    select id, key\n"
        "query q:\n    from keyed\n    group by key\n    select key, n = count()\n"
    )
    assert parsed.ast is not None and parsed.diagnostics == ()
    assert analyze(parsed.ast).diagnostics == ()


@pytest.mark.parametrize(
    ("value", "key", "items", "tail"),
    (
        ("lower(status)", "key", "        key\n", ""),
        *(_RENAMED_KEY_FORMS[form] for form in sorted(_RENAMED_KEY_FORMS)),
    ),
    ids=("computed", *sorted(_RENAMED_KEY_FORMS)),
)
@pytest.mark.parametrize("schema_version", (1, 2))
def test_an_explicit_module_project_groups_by_and_selects_a_let_key(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    schema_version: int,
    value: str,
    key: str,
    items: str,
    tail: str,
) -> None:
    """What the computed hints say to write, and a `let` that renames a key's
    field (H3 (4)), are accepted in a project, LEGACY_FLAT checks included."""

    (tmp_path / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    (tmp_path / "main.pietto").write_text(
        _GROUPED_LET.format(value=value, key=key, items=items) + tail,
        encoding="utf-8",
    )
    code = cli.main(["check", "--project", str(tmp_path), "--format", "json"])
    assert (code, _read_json(capsys)["diagnostics"]) == (0, [])
    if schema_version == 2:
        completed = build_project_completed_semantic_result(
            build_empty_project_semantic_result(check_project_parse_only(tmp_path))
        )
        assert completed.ok and completed.diagnostics == ()


@pytest.mark.parametrize(
    "value, expected_type, nullable",
    [
        ("amount + tax", "Int", EffectiveNullability.UNKNOWN),
        ("lower(region)", "Text", EffectiveNullability.NULLABLE),
        ("lower(trim(status))", "Text", EffectiveNullability.NON_NULL),
        ("1", "Int", EffectiveNullability.NON_NULL),
    ],
)
def test_computed_group_key_preserves_its_type_and_nullable_row(
    value: str,
    expected_type: str,
    nullable: EffectiveNullability,
) -> None:
    semantic = _semantic_for(
        f"query grouped_orders:\n    from orders\n    let bucket = {value}\n"
        "    group by bucket\n    select bucket, n = count()\n"
    )
    assert _errors(semantic) == []
    schema = semantic.model.relation_row_schemas[_relation_ast(semantic)]
    assert tuple(schema.fields) == ("bucket", "n")
    _assert_field(schema.fields["bucket"], expected_type, nullable)


@pytest.mark.parametrize(
    "tail, code",
    [
        ("    group by bucket, bucket\n    select n = count()\n", "PIE-S2317"),
        (
            "    let alias = bucket\n    group by alias\n    select n = count()\n",
            "PIE-S2102",
        ),
        ("    group by orders.bucket\n    select n = count()\n", "PIE-S2102"),
        (
            "    group by bucket\n    select n = sum(amount) if True else 0\n",
            "PIE-S2310",
        ),
    ],
)
def test_computed_group_key_keeps_identity_and_composition_boundaries(
    tail: str, code: str
) -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n    from orders\n    let bucket = amount + tax\n" + tail
    )
    assert code in _error_codes(semantic)


def test_computed_group_key_does_not_expose_other_inputs_to_qualify() -> None:
    semantic = _semantic_for(
        "query grouped_orders:\n    from orders\n    let bucket = amount + tax\n"
        "    group by bucket\n    select bucket, n = count()\n"
        "    qualify id > 0\n"
    )
    assert ("PIE-S2102", "Unknown field: id") in _errors(semantic)


def test_computed_grouping_requires_a_known_input_row() -> None:
    parsed = parse_source(
        'source rows = postgres.table("rows")\n'
        "query q:\n    from rows\n    let k = 1\n"
        "    group by k\n    select k, n = count()\n"
    )
    assert parsed.ast is not None
    assert "PIE-S2102" in _error_codes(analyze(parsed.ast))
