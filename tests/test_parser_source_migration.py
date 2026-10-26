from __future__ import annotations

from pathlib import Path

import pytest

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    ExportStatement,
    ImportStatement,
    LiteralExpr,
    NameExpr,
    QueryDef,
    ShapeDef,
    TypeDef,
)
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.source_migration import migrate_file, migrate_source


@pytest.mark.parametrize(
    ("before", "after"),
    [
        (
            'source users is postgres.table("users")\n',
            'source users = postgres.table("users")\n',
        ),
        ("shape S:\n    maybe: Int nullable\n", "shape S:\n    maybe: Int | None\n"),
        (
            "shape S:\n    id: Int not null\n    note: Text\n",
            "shape S:\n    id: Int\n    note: Text | None\n",
        ),
        ("type Score = Decimal(12, 2) not null\n", "type Score = Decimal(12, 2)\n"),
        (
            "type T = Bool ensure self is not null\n",
            "type T = Bool ensure self is not None\n",
        ),
        ("enum Status active, inactive\n", "enum Status: active, inactive\n"),
        (
            "constraint positive(x: Int not null) -> Bool not null:\n    x > 0\n",
            "constraint positive(x: Int) -> Bool:\n    return x > 0\n",
        ),
        (
            "derive successor(x: Int) -> Int not null:\n    x + 1\n",
            "derive successor(x: Int | None) -> Int:\n    return x + 1\n",
        ),
    ],
)
def test_migrate_mechanical_spelling(before: str, after: str) -> None:
    result = migrate_source(before)

    assert result.diagnostics == ()
    assert result.source == after
    assert migrate_source(after).source == after


def test_comments_strings_bom_and_line_endings_are_preserved() -> None:
    source = (
        "\ufeff# null true True False None nullable is cast: 保留\r\n"
        'source users is postgres.table("null true True False None nullable is cast: 保留") # false\r\n'
        "type T = Text not null\r\n"
    )
    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source.replace("source users is", "source users =").replace(
        "Text not null", "Text"
    )


def test_clause_keywords_used_as_field_names_are_preserved() -> None:
    source = (
        "shape Fields:\n"
        "    source: Int not null\n"
        "    satisfying: Int not null\n"
        "    cast: Int not null\n"
        'source data: Fields is postgres.table("data")\n'
        "query q:\n"
        "    from data\n"
        "    select: satisfying = data.satisfying, source = data.source, cast = data.cast\n"
    )
    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source.replace("Fields is", "Fields =").replace(
        "select:", "select"
    ).replace(" not null", "")


def test_between_and_nested_cast_keep_operand_structure_and_comments() -> None:
    result = migrate_source(
        "type T = Bool ensure (cast(\n"
        "    value # preserve operand comment\n"
        "    as Float) between (1 + 2) and 10)\n"
    )

    assert result.diagnostics == ()
    assert result.source is not None
    assert result.source == (
        "type T = Bool ensure ((1 + 2) <= Float(\n"
        "    value # preserve operand comment\n"
        "     ) <= 10)\n"
    )
    parsed = parse_source(result.source)
    assert parsed.ast is not None
    definition = parsed.ast.definitions[0]
    assert isinstance(definition, TypeDef)
    expression = definition.ensures[0].expression
    assert isinstance(expression, BetweenExpr)
    assert isinstance(expression.value, CallExpr)
    assert isinstance(expression.value.callee, NameExpr)
    assert expression.value.callee.name == "Float"
    assert len(expression.value.arguments) == 1
    argument = expression.value.arguments[0]
    assert isinstance(argument, NameExpr)
    assert argument.name == "value"
    assert isinstance(expression.lower, BinaryExpr)
    assert expression.lower.operator == "+"
    assert isinstance(expression.lower.left, LiteralExpr)
    assert expression.lower.left.value == 1
    assert isinstance(expression.lower.right, LiteralExpr)
    assert expression.lower.right.value == 2
    assert isinstance(expression.upper, LiteralExpr)
    assert expression.upper.value == 10


def test_shape_calls_keep_names_field_order_and_predicates() -> None:
    result = migrate_source(
        "shape Data:\n"
        "    id: Int not null\n"
        "    other: Int nullable\n"
        "    unique key on other, id # preserve key\n"
        "    index lookup on id, other when id > 0\n"
        "    check valid:\n"
        "        id > 0 # first predicate\n"
        "        other is null or other > 0\n"
    )

    assert result.diagnostics == ()
    assert result.source is not None
    assert "# preserve key\n" in result.source
    assert "# first predicate\n" in result.source
    parsed = parse_source(result.source)
    assert parsed.ast is not None
    shape = parsed.ast.definitions[0]
    assert isinstance(shape, ShapeDef)
    assert [(item.name, item.field_names) for item in shape.uniques] == [
        ("key", ("other", "id"))
    ]
    assert [(item.name, item.field_names) for item in shape.indexes] == [
        ("lookup", ("id", "other"))
    ]
    assert shape.indexes[0].predicate is not None
    assert [item.name for item in shape.checks] == ["valid"]
    predicate = shape.checks[0].expression
    assert isinstance(predicate, BinaryExpr)
    assert predicate.operator == "and"
    assert isinstance(predicate.right, BinaryExpr)
    assert predicate.right.operator == "or"


def test_modules_keep_target_literals_aliases_kinds_and_comments() -> None:
    result = migrate_source(
        'import "./null-and-true.pietto": # import comment\n'
        "    type Id as UserId # alias comment\n"
        "    shape User\n"
        "export: # export comment\n"
        "    type UserId\n"
        "    shape User # final comment\n"
    )

    assert result.diagnostics == ()
    assert result.source is not None
    assert '"./null-and-true.pietto"' in result.source
    for comment in (
        "# import comment",
        "# alias comment",
        "# export comment",
        "# final comment",
    ):
        assert comment in result.source
    parsed = parse_source(result.source)
    assert parsed.ast is not None
    imported, exported = parsed.ast.module_statements
    assert isinstance(imported, ImportStatement)
    assert isinstance(exported, ExportStatement)
    assert imported.target == "./null-and-true.pietto"
    assert [(item.exported_name, item.local_name) for item in imported.items] == [
        ("Id", "UserId"),
        ("User", None),
    ]
    assert [item.local_name for item in exported.items] == ["UserId", "User"]


def test_window_conversion_keeps_frame_between_and_named_inheritance() -> None:
    result = migrate_source(
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        n = row_number() window w\n"
        "    window base:\n"
        "        partition by:\n"
        "            rows.account\n"
        "            rows.region # partition comment\n"
        "        order by: rows.id\n"
        "    window w = base:\n"
        "        rows between 1 preceding and current row\n"
    )

    assert result.diagnostics == ()
    assert result.source is not None
    assert "let base = window(" in result.source
    assert "let w = window base(" in result.source
    assert "rows between 1 preceding and current row" in result.source
    assert "# partition comment" in result.source
    assert migrate_source(result.source).source == result.source


@pytest.mark.parametrize("ending", ["\n", "\r\n", "\r"])
def test_let_bindings_split_without_rebinding_or_extra_indentation(ending: str) -> None:
    source = ending.join(
        [
            "query q:",
            "    from rows",
            "    let:",
            "        first = rows.id, second = first + 1 # keep comment",
            "        third = second + 1",
            "    select: first, second, third",
            "",
        ]
    )
    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source is not None
    assert (
        f"    let first = rows.id{ending}    let second = first + 1 # keep comment"
        in result.source
    )
    assert f"{ending}    let third = second + 1{ending}" in result.source
    assert migrate_source(result.source).source == result.source


def test_unsupported_relationships_and_joins_report_all_locations_without_output() -> (
    None
):
    result = migrate_source(
        'source orders is postgres.table("orders")\n'
        "relationship owner:\n"
        "    endpoint order: orders\n"
        "    endpoint customer: customers\n"
        "    on order.customer_id == customer.id\n"
        "query q:\n"
        "    from orders\n"
        "    left join customers as buyer: on orders.customer_id == buyer.id\n"
        "    select: orders.id\n",
        path="old.pietto",
    )

    assert result.source is None
    assert [
        (item.code, item.location.line, item.location.column)
        for item in result.diagnostics
    ] == [
        ("PIE-P1011", 2, 1),
        ("PIE-P1011", 8, 5),
    ]
    assert "proof provenance" in result.diagnostics[0].message
    assert all(item.location.path == "old.pietto" for item in result.diagnostics)


def test_unsupported_cast_does_not_expand_conversion_capability() -> None:
    result = migrate_source('type T = Int ensure cast(self as Text) == "1"\n')

    assert result.source is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-P1011"
    assert "Float" in result.diagnostics[0].message


def test_invalid_input_produces_original_parser_diagnostic() -> None:
    result = migrate_source("shape User {\n", path="bad.pietto")

    assert result.source is None
    assert result.diagnostics[0].code == "PIE-P1005"
    assert result.diagnostics[0].location.path == "bad.pietto"


def test_modern_input_is_byte_identical_and_header_stays_metadata() -> None:
    source = (
        "pietto 3.7\n"
        "# already migrated\n"
        "shape Maybe:\n"
        "    value: Int | None\n"
        'source data = postgres.table("data")\n'
        "query q:\n"
        "    from data\n"
        "    select amount = 1_000, missing = None, valid = True, invalid = False\n"
    )

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source


def test_inline_colons_without_spaces_keep_keyword_boundaries() -> None:
    result = migrate_source(
        "query q:\n"
        "    from data\n"
        "    let:first=1,second=2\n"
        "    where:first < second\n"
        "    select:first,second\n"
    )

    assert result.diagnostics == ()
    assert result.source is not None
    assert "    let first=1\n    let second=2\n" in result.source
    assert "    where first < second\n" in result.source
    assert "    select first,second\n" in result.source


@pytest.mark.parametrize(
    ("source", "locations"),
    [
        (
            "def Float(x: Int not null) -> Float not null:\n"
            "    return cast(x as Float)\n"
            "def use(x: Int not null) -> Float not null:\n"
            "    return Float(x) + cast(x as Float)\n",
            [(2, 12, 2, 28), (4, 23, 4, 39)],
        ),
        (
            "shape Row:\n    id: Int not null\n"
            "relationship Float(left: Row, right: Row):\n"
            "    left.id == right.id\n"
            "derive convert(x: Int not null) -> Float not null:\n"
            "    return cast(x as Float)\n",
            [(6, 12, 6, 28)],
        ),
    ],
)
def test_float_callable_collision_refuses_every_cast_without_changing_input(
    source: str,
    locations: list[tuple[int, int, int, int]],
    tmp_path: Path,
) -> None:
    path = tmp_path / "float_collision.pietto"
    path.write_bytes(source.encode("utf-8"))

    result = migrate_file(path)

    assert result.source is None
    assert path.read_bytes() == source.encode("utf-8")
    assert [
        (
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == locations
    assert all(item.code == "PIE-P1011" for item in result.diagnostics)
    assert all(item.location.path == str(path) for item in result.diagnostics)
    assert all("change call resolution" in item.message for item in result.diagnostics)

    for modern in (
        "def Float(x: Int) -> Int: return x\ndef use(x: Int) -> Int: return Float(x)\n",
        "shape Row:\n    id: Int\n"
        "relationship Float(left: Row, right: Row):\n"
        "    left.id == right.id\n",
    ):
        unchanged = migrate_source(modern)
        assert unchanged.source == modern
        assert unchanged.diagnostics == ()


@pytest.mark.parametrize("name", ["True", "False", "None"])
def test_legacy_literal_keyword_references_refuse_every_location_without_output(
    name: str, tmp_path: Path
) -> None:
    source = (
        'source rows is postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        f"        value = {name}\n"
        f"        dotted = rows.{name}\n"
        f"        call = {name}(rows.id)\n"
        f"    qualify rows.{name}\n"
        f"    order by: {name}\n"
    )
    path = tmp_path / "literal_keyword.pietto"
    path.write_bytes(source.encode("utf-8"))

    result = migrate_file(path)

    assert result.source is None
    assert path.read_bytes() == source.encode("utf-8")
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-P1011", line, column, line, column + len(name))
        for line, column in [(5, 17), (6, 23), (7, 16), (8, 18), (9, 15)]
    ]
    assert all(item.location.path == str(path) for item in result.diagnostics)
    assert all(
        f"Legacy identifier '{name}'" in item.message for item in result.diagnostics
    )


@pytest.mark.parametrize("name", ["True", "False", "None"])
def test_legacy_literal_keyword_declarations_and_identity_references_are_refused(
    name: str,
) -> None:
    result = migrate_source(
        f"shape {name}:\n"
        f"    {name}: {name} not null\n"
        f'source {name}: {name} is postgres.table("{name}")\n'
        "query q:\n"
        f"    from {name}\n"
        "    select:\n"
        f"        {name} = rows.id\n"
    )

    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-P1011", line, column, line, column + len(name))
        for line, column in [
            (1, 7),
            (2, 5),
            (2, len(name) + 7),
            (3, 8),
            (3, len(name) + 10),
            (5, 10),
            (7, 9),
        ]
    ]


@pytest.mark.parametrize("name", ["having", "any", "for"])
def test_new_contextual_keywords_retain_name_and_call_meaning(name: str) -> None:
    source = (
        f'source {name} is postgres.table("{name}")\n'
        "query q:\n"
        f"    from {name}\n"
        "    select:\n"
        f"        bare = {name}\n"
        f"        dotted = rows.{name}\n"
        f"        called = {name}(1)\n"
    )

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source is not None
    assert result.source == source.replace(f"source {name} is", f"source {name} =")
    parsed = parse_source(result.source)
    assert parsed.ast is not None
    query = parsed.ast.definitions[-1]
    assert isinstance(query, QueryDef)
    bare, dotted, called = (item.expression for item in query.select_items)
    assert isinstance(bare, NameExpr) and bare.name == name
    assert isinstance(dotted, DottedNameExpr) and dotted.parts == ("rows", name)
    assert isinstance(called, CallExpr)
    assert isinstance(called.callee, NameExpr) and called.callee.name == name


def test_migrated_literals_require_manual_confirmation_when_reinterpreted() -> None:
    source = "type T = Bool ensure self == true or self == false or self == null\n"
    expected = "type T = Bool ensure self == True or self == False or self == None\n"

    migrated = migrate_source(source)

    assert migrated.diagnostics == ()
    assert migrated.source == expected
    repeated = migrate_source(expected)
    assert repeated.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in repeated.diagnostics
    ] == [
        ("PIE-P1011", 1, 30, 1, 34),
        ("PIE-P1011", 1, 46, 1, 51),
        ("PIE-P1011", 1, 63, 1, 67),
    ]
    assert all(
        "Confirm the intended meaning" in item.message for item in repeated.diagnostics
    )


@pytest.mark.parametrize(("operator",), [("==",), ("!=",)])
def test_migrate_keeps_legacy_null_equality_as_a_mechanical_literal_rewrite(
    operator: str,
) -> None:
    source = f"type T = Bool ensure self {operator} null\n"

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source.replace("null", "None")


@pytest.mark.parametrize("header", ["", "pietto 3.7\n"])
def test_shared_syntax_literal_ambiguity_refuses_all_spans_and_preserves_input(
    header: str, tmp_path: Path
) -> None:
    source = (
        header + "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        truth = True\n"
        "        falsehood = False\n"
        "        missing = None\n"
    )
    path = tmp_path / "ambiguous.pietto"
    path.write_bytes(source.encode("utf-8"))

    result = migrate_file(path)

    assert result.source is None
    assert path.read_bytes() == source.encode("utf-8")
    offset = 1 if header else 0
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-P1011", 4 + offset, 17, 4 + offset, 21),
        ("PIE-P1011", 5 + offset, 21, 5 + offset, 26),
        ("PIE-P1011", 6 + offset, 19, 6 + offset, 23),
    ]
    assert all(item.location.path == str(path) for item in result.diagnostics)


@pytest.mark.parametrize(
    "source",
    [
        "type T = Int\n",
        "type T = Bool ensure self is None or True\n",
        "query q:\n"
        "    from rows\n"
        "    where any(row.id == 1 for row in rows)\n"
        "    select valid = True\n",
    ],
)
def test_unambiguous_modern_input_remains_byte_identical(source: str) -> None:
    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source


@pytest.mark.parametrize(
    "modern_only",
    [
        pytest.param('source rows = postgres.table("rows")\n', id="source_assignment"),
        pytest.param('from "types.pietto" import type Id\n', id="import"),
        pytest.param("export type Collision\n", id="export"),
        pytest.param(
            "shape Row:\n    id: Int\n"
            "relationship same(left: Row, right: Row):\n"
            "    left.id == right.id\n",
            id="relationship_template",
        ),
        pytest.param(
            "constraint c(x: Int) -> Bool:\n    return x > 0\n",
            id="constraint_return",
        ),
        pytest.param(
            "derive d(x: Int) -> Int:\n    return x + 1\n",
            id="derive_return",
        ),
        pytest.param(
            "shape Row:\n    id: Int\n    positive = check(id > 0)\n",
            id="shape_check",
        ),
        pytest.param(
            "shape Row:\n    id: Int\n    key = unique(id)\n",
            id="shape_unique",
        ),
        pytest.param(
            "shape Row:\n    id: Int\n    lookup = index(id)\n",
            id="shape_index",
        ),
        pytest.param(
            "query q:\n    let rows = other\n    from rows\n    select:\n        id\n",
            id="query_let",
        ),
        pytest.param(
            "query q:\n    from rows\n    inner join other on rows.id == other.id\n"
            "    select:\n        rows.id\n",
            id="join",
        ),
        pytest.param("query q:\n    union left, right\n", id="inline_set"),
        pytest.param(
            "constraint c(x: Int) -> Bool: return x > 0\n",
            id="one_line_constraint",
        ),
        pytest.param(
            "derive d(x: Int) -> Int: return x + 1\n",
            id="one_line_derive",
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n        rows.id\n"
            "    qualify:\n        rows.id > 0\n        rows.id < 9\n",
            id="qualify_block_lines",
        ),
        pytest.param(
            "query q:\n    from rows\n    group by rows.id\n"
            "    select:\n        rows.id\n",
            id="inline_group",
        ),
        pytest.param(
            "query q:\n    from rows\n    select rows.id\n", id="inline_select"
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n        rows.id\n"
            "    order by rows.id\n",
            id="inline_order",
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n        rows.id\n"
            "    qualify rows.id > 0\n",
            id="inline_qualify",
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n"
            "        n = row_number() window(partition by rows.id order by rows.id)\n",
            id="compact_window",
        ),
        pytest.param(
            "query q:\n    from rows\n"
            "    select n = row_number() window(order by rows.id)\n",
            id="inline_window_item",
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n        rows.id\n"
            "    qualify:\n        row_number() window(order by rows.id) == 1\n",
            id="compact_qualify_window",
        ),
        pytest.param(
            "query q:\n    from rows\n    let w = window(order by rows.id)\n"
            "    select:\n        n = row_number() window w\n",
            id="named_window",
        ),
        pytest.param(
            "query q:\n    from rows\n    let w = window base\n"
            "    select:\n        n = row_number() window w\n",
            id="inherited_window",
        ),
        pytest.param(
            "type Range = Bool ensure 0 <= self <= 10\n", id="comparison_chain"
        ),
        pytest.param(
            "query q:\n    from rows\n    select:\n        rows.id\n"
            "    qualify:\n        0 <= rows.id <= 10\n",
            id="qualify_comparison_chain",
        ),
        pytest.param("type Sized = Decimal(1_0, 2)\n", id="number_separator"),
        pytest.param("shape Maybe:\n    value: Int | None\n", id="nullability"),
        pytest.param("type Missing = Bool ensure self is None\n", id="null_predicate"),
        pytest.param(
            "query q:\n    from rows\n    select:\n        total = count()\n"
            "    having total > 0\n",
            id="having",
        ),
        pytest.param(
            "query q:\n    from rows\n    where any(row.id == 1 for row in rows)\n"
            "    select:\n        rows.id\n",
            id="any",
        ),
        pytest.param(
            "query q:\n    from rows\n    where any(row.id == 1 for row in rows)\n"
            "    inner join other on rows.id == other.id\n"
            "    select:\n        rows.id\n",
            id="join_prefix_filter",
        ),
    ],
)
def test_modern_only_syntax_anywhere_excludes_legacy_interpretation(
    modern_only: str,
) -> None:
    source = "type Collision = Bool ensure True or False or None\n" + modern_only

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source


@pytest.mark.parametrize("kind", ["constraint", "derive"])
@pytest.mark.parametrize(
    "body",
    [
        "return (x)",
        "return +x",
        "return -x",
        "return in(x)",
        "return in()",
        "return in((x + 1), 2)",
        "return not in(x)",
        "return in(x) and flag",
        "return in(x) if flag else fallback",
    ],
)
def test_return_identifier_overlap_requires_manual_confirmation(
    kind: str, body: str
) -> None:
    source = f"{kind} c(x: Int not null) -> Bool not null:\n    {body}\n"

    result = migrate_source(source, path="return_overlap.pietto")

    assert result.source is None
    assert len(result.diagnostics) == 1
    diagnostic = result.diagnostics[0]
    assert diagnostic.code == "PIE-P1011"
    assert "identifier 'return'" in diagnostic.message
    assert diagnostic.location.path == "return_overlap.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == (2, 5, 2, 5 + len(body))


@pytest.mark.parametrize(
    "body",
    [
        "return in(True) + False",
        "return in(True) == False",
        "return not in(True) < False",
        "return not (True)",
        "return notin(True)",
    ],
)
def test_return_modern_only_expression_does_not_invent_legacy_membership(
    body: str,
) -> None:
    source = f"constraint c() -> Bool:\n    {body}\n"

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source


def test_return_and_literal_ambiguities_are_reported_together_in_source_order() -> None:
    result = migrate_source(
        "constraint c() -> Bool not null:\n    return (True) or False\n"
    )

    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        ("PIE-P1011", 2, 5, 2, 27),
        ("PIE-P1011", 2, 13, 2, 17),
        ("PIE-P1011", 2, 22, 2, 27),
    ]


def test_named_windows_after_select_move_whole_lines_before_where() -> None:
    result = migrate_source(
        "query ranked:\n"
        "    from rows\n"
        "    let net = value - 1\n"
        "    where net > 0\n"
        "    select:\n"
        "        id\n"
        "        position = row_number() window ordered\n"
        "        rank_in_account = row_number() window by_account\n"
        "    # the windows\n"
        "    let ordered = window(order by id)  # by id\n"
        "    let by_account = window(\n"
        "        partition by account_id\n"
        "        order by value desc)\n"
        "    order by:\n"
        "        id\n"
    )

    assert result.diagnostics == ()
    assert result.source == (
        "query ranked:\n"
        "    from rows\n"
        "    let net = value - 1\n"
        "    let ordered = window(order by id)  # by id\n"
        "    let by_account = window(\n"
        "        partition by account_id\n"
        "        order by value desc)\n"
        "    where net > 0\n"
        "    select:\n"
        "        id\n"
        "        position = row_number() window ordered\n"
        "        rank_in_account = row_number() window by_account\n"
        "    # the windows\n"
        "    order by:\n"
        "        id\n"
    )
    assert migrate_source(result.source).source == result.source


def test_a_legacy_window_moves_before_group_by_keeping_crlf_and_no_final_newline() -> (
    None
):
    result = migrate_source(
        "query grouped:\r\n"
        "    from rows\r\n"
        "    group by:\r\n"
        "        category\r\n"
        "    select:\r\n"
        "        category\r\n"
        "        n = row_number() window ordered\r\n"
        "    window ordered:\r\n"
        "        order by: category"
    )

    assert result.diagnostics == ()
    assert result.source == (
        "query grouped:\r\n"
        "    from rows\r\n"
        "    let ordered = window(\r\n"
        "        order by category)\r\n"
        "    group by:\r\n"
        "        category\r\n"
        "    select:\r\n"
        "        category\r\n"
        "        n = row_number() window ordered"
    )


def test_a_window_in_a_relation_let_moves_within_that_body() -> None:
    result = migrate_source(
        "query q:\n"
        "    let recent:\n"
        "        from rows\n"
        "        select:\n"
        "            id\n"
        "            n = row_number() window w\n"
        "        let w = window(order by id)\n"
        "    from recent\n"
        "    select:\n"
        "        id\n"
    )

    assert result.diagnostics == ()
    assert result.source == (
        "query q:\n"
        "    let recent:\n"
        "        from rows\n"
        "        let w = window(order by id)\n"
        "        select:\n"
        "            id\n"
        "            n = row_number() window w\n"
        "    from recent\n"
        "    select:\n"
        "        id\n"
    )


@pytest.mark.parametrize(
    ("source", "name", "line", "column"),
    [
        pytest.param(
            "query clash:\n"
            "    from rows\n"
            "    let ordered = value * 2\n"
            "    select:\n"
            "        id\n"
            "        doubled = ordered\n"
            "        position = row_number() window ordered\n"
            "    let ordered = window(order by id)\n",
            "ordered",
            8,
            9,
            id="value_let",
        ),
        pytest.param(
            "query clash:\n"
            "    let ordered = rows\n"
            "    from ordered\n"
            "    select:\n"
            "        id\n"
            "        n = row_number() window ordered\n"
            "    let ordered = window(order by id)\n",
            "ordered",
            7,
            9,
            id="input_alias",
        ),
        pytest.param(
            "query clash:\n"
            "    from rows\n"
            "    let:\n"
            "        ordered = value * 2\n"
            "    select:\n"
            "        id\n"
            "    window ordered:\n"
            "        order by id\n",
            "ordered",
            7,
            12,
            id="legacy_let_binding",
        ),
        pytest.param(
            "query q:\n"
            "    let recent:\n"
            "        from rows\n"
            "        select:\n"
            "            id\n"
            "    from recent\n"
            "    select:\n"
            "        id\n"
            "        n = row_number() window recent\n"
            "    let recent = window(order by id)\n",
            "recent",
            10,
            9,
            id="relation_let",
        ),
    ],
)
def test_a_window_named_like_a_let_of_its_query_needs_manual_migration(
    source: str, name: str, line: int, column: int
) -> None:
    result = migrate_source(source, path="clash.pietto")

    assert result.source is None
    assert [
        (
            item.code,
            item.message,
            item.location.path,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
            item.suggestion,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            f"The named window {name} has the name of a let of its query, and "
            "windows now share the let namespace; rename one of them explicitly. "
            "No migrated source was emitted.",
            "clash.pietto",
            line,
            5,
            line,
            column + len(name),
            "Rewrite this declaration explicitly, preserving its identities and "
            "metadata.",
        )
    ]


MIGRATED_INPUTS = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    value: Int nullable\n"
    "shape Account:\n"
    "    id: Int not null\n"
    "    region: Text not null\n"
    'source rows: Row is postgres.table("rows")\n'
    'source accounts: Account is postgres.table("accounts")\n'
    "table ranked:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        score = id\n"
)
MIGRATED_JOIN = "    from rows\n    inner join accounts on rows.id == accounts.id\n"


@pytest.mark.parametrize(
    ("inputs", "name", "kind"),
    [
        pytest.param("    from rows\n", "rows", "an input relation", id="from"),
        pytest.param("    from rows\n", "value", "an input field", id="field"),
        pytest.param("    from ranked\n", "score", "an input field", id="output"),
        pytest.param(MIGRATED_JOIN, "accounts", "an input relation", id="join"),
        pytest.param(MIGRATED_JOIN, "region", "an input field", id="joined_field"),
    ],
)
def test_a_window_named_like_an_input_of_its_query_needs_manual_migration(
    inputs: str, name: str, kind: str
) -> None:
    head = MIGRATED_INPUTS + "query q:\n" + inputs + "    select:\n        id\n"
    line = head.count("\n") + 2
    result = migrate_source(
        head + f"        n = row_number() window {name}\n"
        f"    window {name}:\n        order by id\n",
        path="clash.pietto",
    )

    assert result.source is None
    assert [
        (
            item.code,
            item.message,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            f"The named window {name} has the name of {kind} of its query, which a "
            "window, like a let, cannot take now; rename the window explicitly. No "
            "migrated source was emitted.",
            line,
            5,
            line,
            12 + len(name),
        )
    ]


def test_order_key_that_an_output_shadows_keeps_reading_what_it_read() -> None:
    legacy = (
        "shape Row:\n"
        "    id: Int nullable\n"
        "    amount: Int nullable\n"
        "    tag: Text nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        'source raw is postgres.table("raw")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "        label = tag\n"
        "    order by:\n"
        "        amount desc\n"
        "        label\n"
        "        id\n"
        "query w:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = row_number() window:\n"
        "            order by: id\n"
        "    order by: amount\n"
        "query l:\n"
        "    from rows\n"
        "    let:\n"
        "        total = amount + 1\n"
        "    select:\n"
        "        id\n"
        "        line = total\n"
        "    order by: total\n"
        "query u:\n"
        "    from raw\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "    order by: amount\n"
    )

    result = migrate_source(legacy)

    # Over the shape of `rows` a bare `amount` key read the input field, which
    # a modern bare key would read as the output (ambiguous): it is qualified,
    # also beside a selected window result. A name the shape lacks (`label`),
    # the same field (`id`) and a `let` name keep their spelling, and so does
    # the key over `raw`, whose unknown row SQL reads by the output name.
    assert result.diagnostics == ()
    assert result.source == (
        "shape Row:\n"
        "    id: Int | None\n"
        "    amount: Int | None\n"
        "    tag: Text | None\n"
        'source rows: Row = postgres.table("rows")\n'
        'source raw = postgres.table("raw")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "        label = tag\n"
        "    order by:\n"
        "        rows.amount desc\n"
        "        label\n"
        "        id\n"
        "query w:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = row_number() window(\n"
        "            order by id)\n"
        "    order by rows.amount\n"
        "query l:\n"
        "    from rows\n"
        "    \n"
        "    let total = amount + 1\n"
        "    select:\n"
        "        id\n"
        "        line = total\n"
        "    order by total\n"
        "query u:\n"
        "    from raw\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "    order by amount\n"
    )
    assert migrate_source(result.source).source == result.source


def test_a_shadowed_order_key_and_a_late_window_migrate_in_one_body() -> None:
    result = migrate_source(
        "shape Row:\n"
        "    id: Int nullable\n"
        "    amount: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    where id > 0\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "        n = row_number() window ordered\n"
        "    window ordered:\n"
        "        order by: id\n"
        "    order by:\n"
        "        amount desc\n"
    )

    assert result.diagnostics == ()
    assert result.source == (
        "shape Row:\n"
        "    id: Int | None\n"
        "    amount: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    let ordered = window(\n"
        "        order by id)\n"
        "    where id > 0\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "        n = row_number() window ordered\n"
        "    order by:\n"
        "        rows.amount desc\n"
    )
    assert migrate_source(result.source).source == result.source


def test_order_key_of_a_source_in_both_spellings_keeps_its_spelling() -> None:
    mixed = (
        "shape Row:\n"
        "    id: Int | None\n"
        "    amount: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "    order by: amount desc\n"
    )

    result = migrate_source(mixed)

    # The old reader cannot read `Int | None`, so the key has no old reading
    # to keep: it stays as written, and `check` reports it as ambiguous.
    assert result.diagnostics == ()
    assert result.source == (
        "shape Row:\n"
        "    id: Int | None\n"
        "    amount: Int | None\n"
        'source rows: Row = postgres.table("rows")\n'
        "query q:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        amount = amount * 2\n"
        "    order by amount desc\n"
    )


def test_shadowed_order_key_needs_manual_migration_without_a_syntactic_row() -> None:
    source = (
        'source orders is postgres.table("orders")\n'
        'source customers is postgres.table("customers")\n'
        "query q:\n"
        "    from orders\n"
        "    inner join customers on orders.customer_id == customers.id\n"
        "    select:\n"
        "        id = orders.id\n"
        "        name = lower(customers.name)\n"
        "    order by:\n"
        "        name\n"
        "query r:\n"
        "    from q\n"
        "    select:\n"
        "        id\n"
        "        name = upper(name)\n"
        "    order by: name\n"
    )
    modern = source.replace(" is postgres", " = postgres").replace(
        "order by: name", "order by name"
    )

    result = migrate_source(source)
    unchanged = migrate_source(modern)

    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
            item.message,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            10,
            9,
            10,
            13,
            "ORDER BY key 'name' names a SELECT output of another value, which a "
            "modern key written alone reads; whether it read an input field over "
            "JOIN inputs needs manual migration: write the key with its input "
            "binding or rename the output. No migrated source was emitted.",
        ),
        (
            "PIE-P1011",
            16,
            15,
            16,
            19,
            "ORDER BY key 'name' names a SELECT output of another value, which a "
            "modern key written alone reads; whether it read an input field over "
            "the input 'q', which is no source with a shape declared in this "
            "file, needs manual migration: write the key with its input binding "
            "or rename the output. No migrated source was emitted.",
        ),
    ]
    # Source that the modern parser accepts stays as written; `check` reports
    # a key that is still ambiguous.
    assert unchanged.source == modern
    assert unchanged.diagnostics == ()


def test_nullability_migrates_every_declared_type_to_two_states() -> None:
    source = (
        "type Age = Int\n"
        "type Code = Text not null\n"
        "shape Person:\n"
        "    id: Int not null\n"
        "    age: Age\n"
        "    price: Decimal(12, 2) nullable\n"
        "    nickname: Text\n"
        'source people: Person is postgres.table("people")\n'
        "constraint adult(value: Age) -> Bool not null:\n"
        "    value >= 18\n"
        "derive label(value: Text) -> Text:\n"
        "    lower(value)\n"
    )

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == (
        "type Age = Int\n"
        "type Code = Text\n"
        "shape Person:\n"
        "    id: Int\n"
        "    age: Age | None\n"
        "    price: Decimal(12, 2) | None\n"
        "    nickname: Text | None\n"
        'source people: Person = postgres.table("people")\n'
        "constraint adult(value: Age | None) -> Bool:\n"
        "    return value >= 18\n"
        "derive label(value: Text | None) -> Text | None:\n"
        "    return lower(value)\n"
    )
    assert migrate_source(result.source).source == result.source


def test_nullable_type_alias_and_dual_valid_bare_types_need_manual_migration() -> None:
    alias = migrate_source(
        'type Maybe = Int nullable\nsource s is postgres.table("s")\n'
    )

    assert alias.source is None
    assert [
        (item.code, item.location.line, item.location.column)
        for item in alias.diagnostics
    ] == [("PIE-P1011", 1, 18)]
    assert "nullable type alias" in alias.diagnostics[0].message

    dual = migrate_source(
        "type Code = Text\nshape Row:\n    id: Int\n    price: Decimal(12, 2)\n"
    )

    assert dual.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
        )
        for item in dual.diagnostics
    ] == [("PIE-P1011", 3, 9, 3, 12), ("PIE-P1011", 4, 12, 4, 26)]
    assert all(
        "0.1.4 reads it as unknown nullability" in item.message
        for item in dual.diagnostics
    )
    assert migrate_source("type Code = Text\n").source == "type Code = Text\n"


_EXISTENCE = (
    "shape Order:\n    id: Int not null\n    customer_id: Int\n"
    "shape Customer:\n    id: Int not null\n"
    'source orders: Order is postgres.table("orders")\n'
    'source customers: Customer is postgres.table("customers")\n'
    "query q:\n"
    "    from customers\n"
)
_EXISTENCE_MIGRATED = (
    "shape Order:\n    id: Int\n    customer_id: Int | None\n"
    "shape Customer:\n    id: Int\n"
    'source orders: Order = postgres.table("orders")\n'
    'source customers: Customer = postgres.table("customers")\n'
    "query q:\n"
    "    from customers\n"
)


def _check_errors(source: str | None) -> list[tuple[str, int, int, str]]:
    """The errors `check` reports for a migrated single file."""

    assert source is not None
    parsed = parse_source(source)
    diagnostics = list(parsed.diagnostics)
    if parsed.ast is not None:
        diagnostics.extend(analyze(parsed.ast).diagnostics)
    return [
        (item.code, item.location.line, item.location.column, item.message)
        for item in diagnostics
        if item.severity is Severity.ERROR
    ]


@pytest.mark.parametrize(("kind", "negation"), [("semi", ""), ("anti", "not ")])
def test_existence_joins_become_any_filters_in_place(kind: str, negation: str) -> None:
    joined = (
        f"    {kind} join orders on orders.customer_id == customers.id # kept\n"
        "    let o = orders\n"
        "    left join o on o.id == customers.id\n"
        "    select: customers.id\n"
    )
    last = f"    {kind} join orders on orders.customer_id == customers.id\n"

    before_join = migrate_source(_EXISTENCE + joined)
    as_where = migrate_source(_EXISTENCE + last + "    select: customers.id\n")

    test = f"{negation}any(orders.customer_id == customers.id for orders in orders)"
    head = _EXISTENCE_MIGRATED
    assert (before_join.diagnostics, as_where.diagnostics) == ((), ())
    assert before_join.source == head + (
        f"    where {test} # kept\n"
        "    let o = orders\n"
        "    left join o on o.id == customers.id\n"
        "    select customers.id\n"
    )
    assert as_where.source == head + f"    where {test}\n    select customers.id\n"
    assert (_check_errors(before_join.source), _check_errors(as_where.source)) == (
        [],
        [],
    )


def test_existence_join_binds_a_named_input_by_its_name_in_modern_source() -> None:
    source = (
        "shape Order:\n    id: Int | None\n    customer_id: Int | None\n"
        "shape Customer:\n    id: Int | None\n"
        'source orders: Order = postgres.table("orders")\n'
        'source customers: Customer = postgres.table("customers")\n'
        "query q:\n"
        "    from customers\n"
        "    let o = orders\n"
        "    anti join o on o.customer_id == customers.id and o.id is not None\n"
        "    select customers.id\n"
    )

    result = migrate_source(source)

    assert result.diagnostics == ()
    assert result.source == source.replace(
        "    anti join o on o.customer_id == customers.id and o.id is not None\n",
        "    where not any(o.customer_id == customers.id and o.id is not None"
        " for o in o)\n",
    )
    assert _check_errors(result.source) == []


@pytest.mark.parametrize(
    ("tail", "reason"),
    [
        ("    let k = 1\n", "lets or a WHERE follow it after the last JOIN"),
        (
            "    where customers.id > 1\n",
            "lets or a WHERE follow it after the last JOIN",
        ),
    ],
)
def test_existence_join_before_later_lets_or_where_needs_manual_migration(
    tail: str, reason: str
) -> None:
    source = (
        _EXISTENCE
        + "    semi join orders on orders.customer_id == customers.id\n"
        + tail
        + "    select: customers.id\n"
    )

    result = migrate_source(source, path="existence.pietto")

    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
            item.message,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            10,
            5,
            10,
            59,
            f"This semi JOIN needs manual migration to `where any(...)` because {reason}; "
            "no migrated source was emitted.",
        )
    ]


@pytest.mark.parametrize(
    ("kind", "rewrite"),
    [
        ("semi", "rewriting it as `where any(predicate for o in orders)`"),
        ("anti", "rewriting it as `where not any(predicate for o in orders)`"),
        ("inner", "introducing let and on"),
        ("cross", "introducing let"),
    ],
)
def test_join_written_with_as_needs_manual_migration_to_its_rewrite(
    kind: str, rewrite: str
) -> None:
    # A semi or anti JOIN becomes `where [not] any(...)`, never a let and on;
    # a CROSS JOIN takes no `on`.
    on = "" if kind == "cross" else ": on o.customer_id == customers.id"
    result = migrate_source(
        _EXISTENCE + f"    {kind} join orders as o{on}\n    select: customers.id\n",
        path="as.pietto",
    )

    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.message,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            10,
            5,
            None,
            "Legacy JOIN bindings need manual migration: preserve the exact input "
            "occurrence, roles, inferred source, and relationship metadata when "
            f"{rewrite}.",
        )
    ]


@pytest.mark.parametrize(("kind", "negation"), [("semi", ""), ("anti", "not ")])
def test_last_existence_join_stays_the_where_after_moved_named_windows(
    kind: str, negation: str
) -> None:
    # The last semi/anti JOIN becomes the relation's WHERE, so the named window
    # moved from after select is a let before it, not after it.
    result = migrate_source(
        _EXISTENCE + f"    {kind} join orders on orders.customer_id == customers.id\n"
        "    select:\n"
        "        customers.id\n"
        "        n = row_number() window w\n"
        "    window w:\n"
        "        order by: customers.id\n"
    )

    assert result.diagnostics == ()
    assert result.source == _EXISTENCE_MIGRATED + (
        "    let w = window(\n"
        "        order by customers.id)\n"
        f"    where {negation}any(orders.customer_id == customers.id for orders in orders)\n"
        "    select:\n"
        "        customers.id\n"
        "        n = row_number() window w\n"
    )
    assert migrate_source(result.source or "").source == result.source
    assert _check_errors(result.source) == []


_CANDIDATES = (
    "shape Row:\n    id: Int | None\n"
    'source rows: Row = postgres.table("rows")\n'
    'source candidates: Row = postgres.table("candidates")\n'
    'source others: Row = postgres.table("others")\n'
    "relationship Matches(row: Row, candidate: Row):\n"
    "    row.id == candidate.id\n"
    "query q:\n"
    "    from rows\n"
)
_LATER_JOIN = "    inner join others on others.id == rows.id\n"


@pytest.mark.parametrize(
    ("before", "after"),
    [
        pytest.param(
            "    semi join candidates on candidates.id == rows.id\n",
            "    where any(candidates.id == rows.id for candidates in candidates)\n",
            id="plain",
        ),
        pytest.param(
            "    anti join candidates on any(o.id == candidates.id for o in others)\n"
            + _LATER_JOIN,
            "    where not any(any(o.id == candidates.id for o in others)"
            " for candidates in candidates)\n" + _LATER_JOIN,
            id="inner_any_over_another_relation",
        ),
        pytest.param(
            "    semi join candidates on"
            " any(candidates.id == rows.id for candidates in others)\n",
            "    where any(any(candidates.id == rows.id for candidates in others)"
            " for candidates in candidates)\n",
            id="inner_binder_of_the_name",
        ),
        pytest.param(
            "    let c = candidates\n"
            "    semi join candidates on any(item.id == candidates.id for item in c)\n",
            "    let c = candidates\n"
            "    where any(any(item.id == candidates.id for item in c)"
            " for candidates in candidates)\n",
            id="inner_any_over_a_let_alias",
        ),
        pytest.param(
            "    anti join candidates on Matches(rows, candidates)\n",
            "    where not any(Matches(rows, candidates) for candidates in candidates)\n",
            id="relationship_row_argument",
        ),
    ],
)
def test_existence_join_reading_its_name_as_the_row_migrates_byte_for_byte(
    before: str, after: str
) -> None:
    # The binder takes the JOIN binding's place: `candidates.id`, an inner
    # binder of that name and a relationship row argument keep their meaning.
    result = migrate_source(_CANDIDATES + before + "    select rows.id\n")

    assert result.diagnostics == ()
    assert result.source == _CANDIDATES + after + "    select rows.id\n"
    assert _check_errors(result.source) == []


_HIDES_RELATION = (
    "its new binder candidates would hide the relation candidates that its "
    "`on` predicate reads in `any(...)`"
)


@pytest.mark.parametrize(
    ("source", "line", "end_column", "kind", "hidden"),
    [
        pytest.param(
            _CANDIDATES
            + "    semi join candidates on any(True for item in candidates)\n",
            10,
            61,
            "semi",
            _HIDES_RELATION,
            id="semi_last",
        ),
        pytest.param(
            _CANDIDATES + "    anti join candidates on"
            " any(item.id == candidates.id for item in candidates)\n",
            10,
            81,
            "anti",
            _HIDES_RELATION,
            id="anti_last",
        ),
        pytest.param(
            _CANDIDATES
            + "    semi join candidates on any(True for item in candidates)\n"
            + _LATER_JOIN,
            10,
            61,
            "semi",
            _HIDES_RELATION,
            id="semi_before_a_join",
        ),
        pytest.param(
            _CANDIDATES + "    anti join candidates on"
            " not any(item.id == rows.id for item in candidates)\n" + _LATER_JOIN,
            10,
            79,
            "anti",
            _HIDES_RELATION,
            id="anti_before_a_join",
        ),
        pytest.param(
            _CANDIDATES + "    semi join candidates on"
            " any(candidates.id == rows.id for candidates in candidates)\n",
            10,
            87,
            "semi",
            _HIDES_RELATION,
            id="inner_binder_over_the_name",
        ),
        pytest.param(
            _CANDIDATES
            + "    let c = candidates\n"
            + "    semi join c on any(True for item in c)\n",
            11,
            43,
            "semi",
            "its new binder c would hide the relation c that its `on` predicate "
            "reads in `any(...)`",
            id="let_alias",
        ),
        pytest.param(
            "shape Row:\n    id: Int | None\n    candidates: Int | None\n"
            "shape Candidate:\n    cid: Int | None\n"
            'source rows: Row = postgres.table("rows")\n'
            'source candidates: Candidate = postgres.table("candidates")\n'
            "query q:\n"
            "    from rows\n"
            "    semi join candidates on candidates == candidates.cid\n",
            10,
            57,
            "semi",
            "its new binder candidates would hide the bare name candidates that its "
            "`on` predicate reads",
            id="bare_input_field",
        ),
        pytest.param(
            "shape Row:\n    id: Int | None\n"
            'source rows: Row = postgres.table("rows")\n'
            "query q:\n"
            "    from rows\n"
            "    anti join rows on rows.id == 1\n",
            6,
            35,
            "anti",
            "its new binder rows would hide the FROM input or another JOIN of this "
            "query named rows",
            id="from_input_name",
        ),
    ],
)
def test_existence_join_whose_binder_would_hide_a_read_needs_manual_migration(
    source: str, line: int, end_column: int, kind: str, hidden: str
) -> None:
    # `any(p for x in x)` binds x over p, so p must read nothing else as x:
    # `check` would refuse an inner `any(... in x)` or a bare x read as the
    # binder, and an input named x would lose its reads to the binder.
    result = migrate_source(source + "    select rows.id\n", path="hidden.pietto")

    negation = "not " if kind == "anti" else ""
    assert result.source is None
    assert [
        (
            item.code,
            item.location.line,
            item.location.column,
            item.location.end_line,
            item.location.end_column,
            item.message,
        )
        for item in result.diagnostics
    ] == [
        (
            "PIE-P1011",
            line,
            5,
            line,
            end_column,
            f"This {kind} JOIN needs manual migration to `where {negation}any(...)` "
            f"because {hidden}; no migrated source was emitted.",
        )
    ]


def test_a_legacy_body_reading_the_name_return_gains_the_keyword() -> None:
    # A 0.1.4 block body has no `return` keyword, so `return * 2` reads the
    # parameter named `return`; the migrated body returns that expression.
    result = migrate_source(
        "derive d(return: Int not null) -> Int not null:\n    return * 2\n"
    )

    assert result.diagnostics == ()
    assert result.source == "derive d(return: Int) -> Int:\n    return return * 2\n"


def test_migrate_reports_no_parse_warning_of_the_source_it_writes() -> None:
    # `check` warns that `--` is two minus signs (PIE-P1009); `migrate` keeps
    # the bytes, of an old source too, and reports only what stops it.
    modern = "type T = Int ensure self > 100 -- 50\n"
    old = "type T = Int not null ensure self > 100 -- 50\n"

    assert [item.code for item in parse_source(modern).diagnostics] == ["PIE-P1009"]
    for source in (modern, old):
        result = migrate_source(source)
        assert (result.source, result.diagnostics) == (modern, ())
