from __future__ import annotations

import dataclasses
from functools import lru_cache
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto.ir as public_ir
import pietto.ir.model as ir_model
import pietto.semantic as public_semantic
import pietto.sql as public_sql
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.ir import build_ir
from pietto.ir.lowering import lower_expr
from pietto.ir.model import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ExpressionIR,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    OrderDirectionIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    TypeKindIR,
    TypeRefIR,
    WindowCallIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowNullTreatmentIR,
    WindowSpecIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
import pietto.semantic.capability_windows as capability_windows
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)
from pietto.semantic.model import SemanticResult
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.postgres import emit_postgres_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = (
    "tests/"
    "test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py"
)
IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)
ZERO_ARGUMENT_IDENTITIES = IDENTITIES[:5]
RESULT_TYPES = {
    "row_number": ("Int", NullabilityIR.NON_NULL),
    "rank": ("Int", NullabilityIR.NON_NULL),
    "dense_rank": ("Int", NullabilityIR.NON_NULL),
    "percent_rank": ("Float", NullabilityIR.NON_NULL),
    "cume_dist": ("Float", NullabilityIR.NON_NULL),
    "ntile": ("Int", NullabilityIR.NON_NULL),
    "lag": ("Int", NullabilityIR.NULLABLE),
    "lead": ("Int", NullabilityIR.NULLABLE),
}
SQL_NAMES = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
}

SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    category: Text nullable\n"
    "    amount: Int nullable\n"
    "    score: Float not null\n"
)
SPAN = SourceSpan("slice15.pietto", 1, 1, 1, 2)
INT_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Unknown",
    canonical_name="Unknown",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
    nullability=NullabilityIR.UNKNOWN,
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _source_connector(dialect: str) -> str:
    connector = "postgres" if dialect == "postgresql" else "mysql"
    return SOURCE_PREFIX + f'source rows: Row is {connector}.table("rows")\n'


def _window_call_source(identity: str) -> str:
    if identity in ZERO_ARGUMENT_IDENTITIES:
        return f"{identity}()"
    if identity == "ntile":
        return "ntile(4)"
    if identity == "lag":
        return "lag(amount, 2, amount)"
    return "lead(amount, 0, amount)"


def _single_window_source(identity: str, *, dialect: str = "postgresql") -> str:
    return (
        _source_connector(dialect) + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {_window_call_source(identity)} window:\n"
        "            partition by:\n"
        "                category\n"
        "            order by:\n"
        "                id desc\n"
    )


@lru_cache(maxsize=None)
def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    parsed = parse_source(source, path="slice15.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(parsed.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return parsed.ast, semantic, ir_result.ir


def _relation(script_ir: ScriptIR, name: str | None = None) -> RelationIR:
    relations = tuple(
        item for item in script_ir.definitions if isinstance(item, RelationIR)
    )
    if name is None:
        assert relations
        return relations[-1]
    return next(item for item in relations if item.name == name)


def _window(expression: ExpressionIR) -> WindowCallIR:
    assert isinstance(expression, WindowCallIR)
    return expression


def _single_window_ir(identity: str) -> WindowCallIR:
    _, _, script_ir = _compile(_single_window_source(identity))
    relation = _relation(script_ir, "windows")
    assert len(relation.projections) == 1
    return _window(relation.projections[0].expression)


def _literal(value: int) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=UNKNOWN_TYPE, value=value)


def _field(name: str, *, qualifier: tuple[str, ...] = ()) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=INT_TYPE,
        name=name,
        qualifier=qualifier,
        field=None,
    )


def _identity(name: str = "row_number") -> WindowFunctionIdentityIR:
    return WindowFunctionIdentityIR(
        namespace=(),
        name=name,
        role=WindowFunctionRoleIR.WINDOW_FUNCTION,
    )


def _order_item(
    expression: ExpressionIR | None = None,
    *,
    direction: OrderDirectionIR = OrderDirectionIR.ASC,
    explicit: bool = False,
) -> WindowOrderItemIR:
    return WindowOrderItemIR(
        expression=_field("id") if expression is None else expression,
        direction=direction,
        direction_is_explicit=explicit,
        span=SPAN,
    )


def _spec(
    *,
    partition_by: tuple[ExpressionIR, ...] = (),
    order_by: tuple[WindowOrderItemIR, ...] | None = None,
) -> WindowSpecIR:
    return WindowSpecIR(
        partition_by=partition_by,
        order_by=(_order_item(),) if order_by is None else order_by,
        span=SPAN,
    )


def _manual_window(
    name: str = "row_number",
    *,
    arguments: tuple[ExpressionIR, ...] | None = None,
    spec: WindowSpecIR | None = None,
) -> WindowCallIR:
    if arguments is None:
        arguments = () if name in ZERO_ARGUMENT_IDENTITIES else (_literal(1),)
    return WindowCallIR(
        span=SPAN,
        value_type=INT_TYPE,
        identity=_identity(name),
        arguments=arguments,
        spec=_spec() if spec is None else spec,
        null_treatment=(
            WindowNullTreatmentIR.RESPECT_NULLS if name in {"lag", "lead"} else None
        ),
    )


def _unchecked_dataclass(
    instance_type: type[object], values: dict[str, object]
) -> object:
    instance = object.__new__(instance_type)
    for name, value in values.items():
        object.__setattr__(instance, name, value)
    return instance


def _unchecked_identity(**changes: object) -> WindowFunctionIdentityIR:
    values: dict[str, object] = {
        "namespace": (),
        "name": "row_number",
        "role": WindowFunctionRoleIR.WINDOW_FUNCTION,
    }
    values.update(changes)
    return cast(
        WindowFunctionIdentityIR,
        _unchecked_dataclass(WindowFunctionIdentityIR, values),
    )


def _unchecked_order_item(**changes: object) -> WindowOrderItemIR:
    values: dict[str, object] = {
        "expression": _field("id"),
        "direction": OrderDirectionIR.ASC,
        "direction_is_explicit": False,
        "span": SPAN,
    }
    values.update(changes)
    return cast(
        WindowOrderItemIR,
        _unchecked_dataclass(WindowOrderItemIR, values),
    )


def _unchecked_spec(**changes: object) -> WindowSpecIR:
    values: dict[str, object] = {
        "partition_by": (),
        "order_by": (_order_item(),),
        "span": SPAN,
    }
    values.update(changes)
    return cast(WindowSpecIR, _unchecked_dataclass(WindowSpecIR, values))


def _unchecked_window(**changes: object) -> WindowCallIR:
    values: dict[str, object] = {
        "span": SPAN,
        "value_type": INT_TYPE,
        "identity": _identity(),
        "arguments": (),
        "spec": _spec(),
    }
    values.update(changes)
    return cast(WindowCallIR, _unchecked_dataclass(WindowCallIR, values))


def _replace_only_window(script_ir: ScriptIR, replacement: ExpressionIR) -> ScriptIR:
    target = _relation(script_ir, "windows")
    assert len(target.projections) == 1
    projection = target.projections[0]
    replaced_relation = dataclasses.replace(
        target,
        projections=(dataclasses.replace(projection, expression=replacement),),
    )
    definitions = tuple(
        replaced_relation if item is target else item for item in script_ir.definitions
    )
    return dataclasses.replace(script_ir, definitions=definitions)


def _malformed_script_ir(
    case: int,
    *,
    dialect: str,
    variant: int = 0,
) -> ScriptIR:
    _, _, script_ir = _compile(_single_window_source("row_number", dialect=dialect))
    valid = _window(_relation(script_ir, "windows").projections[0].expression)
    if case == 0:
        replacement = _unchecked_window(
            identity=_unchecked_identity(namespace=("extension",))
        )
    elif case == 1:
        replacement = _unchecked_window(identity=_unchecked_identity(name="ROW_NUMBER"))
    elif case == 2:
        replacement = _unchecked_window(
            identity=_unchecked_identity(role="window_function")
        )
    elif case == 3:
        replacement = _unchecked_window(arguments=(_literal(1),))
    elif case == 4:
        malformed_windows = (
            _unchecked_window(arguments=[_literal(1)]),
            _unchecked_window(spec=_unchecked_spec(partition_by=[_field("category")])),
            _unchecked_window(span=object()),
            _unchecked_window(value_type=object()),
            _unchecked_window(spec=_unchecked_spec(span=object())),
            _unchecked_window(
                spec=_unchecked_spec(order_by=(_unchecked_order_item(span=object()),))
            ),
        )
        replacement = malformed_windows[variant]
    elif case == 5:
        replacement = _unchecked_window(spec=_unchecked_spec(order_by=()))
    elif case == 6:
        malformed_items = (
            _unchecked_order_item(direction="ASC"),
            _unchecked_order_item(direction_is_explicit=1),
            _unchecked_order_item(
                direction=OrderDirectionIR.DESC,
                direction_is_explicit=False,
            ),
            object(),
        )
        replacement = _unchecked_window(
            spec=_unchecked_spec(order_by=(malformed_items[variant],))
        )
    else:
        replacement = CallIR(
            span=valid.span,
            value_type=valid.value_type,
            callee="lower",
            callee_symbol=None,
            arguments=(valid,),
        )
    return _replace_only_window(script_ir, replacement)


def _grouped_source(*, dialect: str, windows_first: bool) -> str:
    group = "        group_name = category\n"
    total = "        total = sum(amount)\n"
    rank = (
        "        group_rank = rank() window:\n"
        "            partition by:\n"
        "                group_name\n"
        "            order by:\n"
        "                total desc\n"
    )
    lag = (
        "        previous_total = lag(total, 0, total) window:\n"
        "            order by:\n"
        "                total\n"
    )
    select_items = (
        rank + lag + group + total if windows_first else group + total + rank + lag
    )
    return (
        _source_connector(dialect) + "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        category\n"
        "    select:\n" + select_items + "    order by:\n"
        "        total desc\n"
        "        group_rank\n"
        "        previous_total asc\n"
    )


def _sql_for(source: str, dialect: str) -> str:
    _, _, script_ir = _compile(source)
    result = (
        emit_postgres_sql(script_ir)
        if dialect == "postgresql"
        else emit_mysql_sql(script_ir)
    )
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    return result.artifacts[0].sql


@pytest.mark.parametrize("_case", range(4))
def test_window_ir_carrier_fields_frozen_slots_equality_and_hashing_are_exact(
    _case: int,
) -> None:
    carrier_types = (
        WindowFunctionIdentityIR,
        WindowOrderItemIR,
        WindowSpecIR,
        WindowCallIR,
    )
    expected_fields = (
        ("namespace", "name", "role"),
        ("expression", "direction", "direction_is_explicit", "span"),
        ("partition_by", "order_by", "span", "frame"),
        (
            "span",
            "value_type",
            "identity",
            "arguments",
            "spec",
            "null_treatment",
            "null_treatment_is_explicit",
            "nth_direction",
            "nth_direction_is_explicit",
            "named_use",
        ),
    )
    instances = (
        _identity(),
        _order_item(),
        _spec(),
        _manual_window(),
    )
    carrier_type = carrier_types[_case]
    instance = instances[_case]
    assert dataclasses.is_dataclass(carrier_type)
    assert (
        tuple(field.name for field in dataclasses.fields(carrier_type))
        == (expected_fields[_case])
    )
    assert "__dict__" not in dir(instance)
    assert instance == instances[_case]
    assert hash(instance) == hash(instances[_case])
    first_field = expected_fields[_case][0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first_field, getattr(instance, first_field))


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_identity_constructor_validation_is_exact(_case: int) -> None:
    if _case == 0:
        identity = _identity()
        assert identity == WindowFunctionIdentityIR(
            (), "row_number", WindowFunctionRoleIR.WINDOW_FUNCTION
        )
        return
    if _case == 1:
        identity = WindowFunctionIdentityIR(
            ("vendor", "analytics"),
            "future_rank",
            WindowFunctionRoleIR.WINDOW_FUNCTION,
        )
        assert identity.namespace == ("vendor", "analytics")
        return
    invalid = (
        {"namespace": ["vendor"]},
        {"namespace": (1,)},
        {"namespace": ("",)},
        {"name": 1},
        {"name": ""},
        {"role": "window_function"},
    )[_case - 2]
    values: dict[str, object] = {
        "namespace": (),
        "name": "rank",
        "role": WindowFunctionRoleIR.WINDOW_FUNCTION,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowFunctionIdentityIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_order_item_constructor_validation_is_exact(_case: int) -> None:
    if _case < 3:
        direction, explicit = (
            (OrderDirectionIR.ASC, False),
            (OrderDirectionIR.ASC, True),
            (OrderDirectionIR.DESC, True),
        )[_case]
        item = _order_item(direction=direction, explicit=explicit)
        assert (item.direction, item.direction_is_explicit) == (
            direction,
            explicit,
        )
        return
    invalid = (
        {"expression": object()},
        {"direction": "ASC"},
        {"direction_is_explicit": 1},
        {"span": object()},
        {
            "direction": OrderDirectionIR.DESC,
            "direction_is_explicit": False,
        },
    )[_case - 3]
    values: dict[str, object] = {
        "expression": _field("id"),
        "direction": OrderDirectionIR.ASC,
        "direction_is_explicit": False,
        "span": SPAN,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowOrderItemIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_spec_constructor_validation_is_exact(_case: int) -> None:
    if _case == 0:
        spec = _spec()
        assert spec.partition_by == () and len(spec.order_by) == 1
        return
    if _case == 1:
        field = _field("category")
        item = _order_item(field, direction=OrderDirectionIR.DESC, explicit=True)
        spec = _spec(partition_by=(field, field), order_by=(item, item))
        assert spec.partition_by == (field, field)
        assert spec.order_by == (item, item)
        return
    invalid = (
        {"partition_by": [_field("id")]},
        {"partition_by": (object(),)},
        {"order_by": [_order_item()]},
        {"order_by": (object(),)},
        {"order_by": ()},
        {"span": object()},
    )[_case - 2]
    values: dict[str, object] = {
        "partition_by": (),
        "order_by": (_order_item(),),
        "span": SPAN,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowSpecIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(16))
def test_window_ir_call_constructor_validation_and_arity_are_exact(
    _case: int,
) -> None:
    if _case < 8:
        name = IDENTITIES[_case]
        if name in ZERO_ARGUMENT_IDENTITIES:
            arguments: tuple[ExpressionIR, ...] = ()
        elif name == "ntile":
            arguments = (_literal(4),)
        else:
            arguments = (_field("amount"),)
        call = _manual_window(name, arguments=arguments)
        assert call.identity.name == name
        assert call.arguments == arguments
        assert call.identity.namespace == ()
        return
    invalid_values: tuple[dict[str, object], ...] = (
        {"identity": _identity("row_number"), "arguments": (_literal(1),)},
        {"identity": _identity("ntile"), "arguments": ()},
        {"identity": _identity("lag"), "arguments": ()},
        {
            "identity": _identity("lead"),
            "arguments": tuple(_literal(index) for index in range(4)),
        },
        {"arguments": []},
        {"arguments": (object(),)},
        {"identity": object()},
        {"spec": object()},
    )
    values: dict[str, object] = {
        "span": SPAN,
        "value_type": INT_TYPE,
        "identity": _identity(),
        "arguments": (),
        "spec": _spec(),
    }
    values.update(invalid_values[_case - 8])
    with pytest.raises((TypeError, ValueError)):
        WindowCallIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_all_eight_window_identities_lower_with_source_identity_and_result_type(
    _case: int,
) -> None:
    name = IDENTITIES[_case]
    expression = _single_window_ir(name)
    expected_name, expected_nullability = RESULT_TYPES[name]
    assert expression.identity == WindowFunctionIdentityIR(
        namespace=(),
        name=name,
        role=WindowFunctionRoleIR.WINDOW_FUNCTION,
    )
    assert expression.value_type.canonical_name == expected_name
    assert expression.value_type.nullability is expected_nullability
    assert expression.spec.order_by[0].direction is OrderDirectionIR.DESC


@pytest.mark.parametrize("_case", range(5))
def test_zero_argument_identity_ir_shapes_are_exact(_case: int) -> None:
    name = ZERO_ARGUMENT_IDENTITIES[_case]
    expression = _single_window_ir(name)
    assert expression.identity.name == name
    assert expression.arguments == ()
    assert type(expression.arguments) is tuple
    assert expression.spec.partition_by[0].name == "category"  # type: ignore[attr-defined]
    assert expression.spec.order_by[0].expression.name == "id"  # type: ignore[attr-defined]


@pytest.mark.parametrize("_case", range(3))
def test_ntile_argument_ir_shape_is_exact(_case: int) -> None:
    value = (1, 4, 99)[_case]
    source = _single_window_source("ntile").replace("ntile(4)", f"ntile({value})")
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, LiteralIR)
    assert argument.value == value
    assert argument.value_type.canonical_kind is TypeKindIR.UNKNOWN
    assert argument.value_type.nullability is NullabilityIR.UNKNOWN


@pytest.mark.parametrize("_case", range(8))
def test_lag_lead_omitted_and_explicit_argument_shapes_are_exact(_case: int) -> None:
    calls = (
        "lag(amount)",
        "lag(amount, 2)",
        "lag(amount, 2, amount)",
        "lag(amount, 0, amount)",
        "lead(amount)",
        "lead(amount, 2)",
        "lead(amount, 2, amount)",
        "lead(amount, 0, amount)",
    )
    call = calls[_case]
    source = _single_window_source("lag").replace("lag(amount, 2, amount)", call)
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    expected_arity = call.count(",") + 1
    assert expression.identity.name == ("lag" if _case < 4 else "lead")
    assert len(expression.arguments) == expected_arity
    assert isinstance(expression.arguments[0], FieldRefIR)
    if expected_arity >= 2:
        offset = expression.arguments[1]
        assert isinstance(offset, LiteralIR)
        assert offset.value_type.canonical_kind is TypeKindIR.UNKNOWN
    if expected_arity == 3:
        assert isinstance(expression.arguments[2], FieldRefIR)
    function = "LAG" if _case < 4 else "LEAD"
    rendered_arguments = '"amount"'
    if expected_arity >= 2:
        rendered_arguments += f", {cast(LiteralIR, expression.arguments[1]).value}"
    if expected_arity == 3:
        rendered_arguments += ', "amount"'
    expected = (
        f"{function}({rendered_arguments}) OVER "
        '(PARTITION BY "category" ORDER BY "id" DESC)'
    )
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(6))
def test_partition_and_local_order_multiplicity_preserve_source_order_and_duplicates(
    _case: int,
) -> None:
    partitions = (
        (),
        ("category",),
        ("category", "category"),
        ("category", "id", "category"),
        (),
        ("id", "category"),
    )[_case]
    orders = (
        ("id",),
        ("id", "id"),
        ("id", "amount"),
        ("amount", "id", "amount"),
        ("id", "category", "id"),
        ("category", "category"),
    )[_case]
    partition_clause = ""
    if partitions:
        partition_clause = "            partition by:\n" + "".join(
            f"                {name}\n" for name in partitions
        )
    order_clause = "            order by:\n" + "".join(
        f"                {name}\n" for name in orders
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window:\n" + partition_clause + order_clause
    )
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert tuple(item.name for item in expression.spec.partition_by) == partitions  # type: ignore[attr-defined]
    assert tuple(item.expression.name for item in expression.spec.order_by) == orders  # type: ignore[attr-defined]
    partition_sql = (
        ""
        if not partitions
        else "PARTITION BY " + ", ".join(f'"{name}"' for name in partitions) + " "
    )
    order_sql = ", ".join(f'"{name}" ASC' for name in orders)
    expected = f"ROW_NUMBER() OVER ({partition_sql}ORDER BY {order_sql})"
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(6))
def test_window_order_omitted_asc_desc_direction_facts_are_exact(_case: int) -> None:
    directions = (
        (None,),
        ("asc",),
        ("desc",),
        (None, "asc"),
        ("asc", "desc"),
        ("desc", None),
    )[_case]
    order_lines = "".join(
        "                id\n"
        if direction is None
        else f"                id {direction}\n"
        for direction in directions
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        "        result = rank() window:\n"
        "            order by:\n" + order_lines
    )
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert tuple(item.direction for item in expression.spec.order_by) == tuple(
        OrderDirectionIR.ASC if item in {None, "asc"} else OrderDirectionIR.DESC
        for item in directions
    )
    assert tuple(
        item.direction_is_explicit for item in expression.spec.order_by
    ) == tuple(item is not None for item in directions)
    expected_items = ", ".join(
        f'"id" {"ASC" if item in {None, "asc"} else "DESC"}' for item in directions
    )
    expected = f"RANK() OVER (ORDER BY {expected_items})"
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(4))
def test_multiple_window_outputs_lower_in_select_order(_case: int) -> None:
    count = _case + 2
    selected = IDENTITIES[:count]
    items = "".join(
        f"        output_{index} = {name}() window:\n"
        "            order by:\n"
        "                id\n"
        for index, name in enumerate(selected)
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n" + items
    )
    _, _, script_ir = _compile(source)
    relation = _relation(script_ir)
    assert tuple(projection.name for projection in relation.projections) == tuple(
        f"output_{index}" for index in range(count)
    )
    assert (
        tuple(
            _window(projection.expression).identity.name
            for projection in relation.projections
        )
        == selected
    )
    sql = _sql_for(source, "postgresql")
    positions = tuple(sql.index(f"{SQL_NAMES[name]}() OVER") for name in selected)
    assert positions == tuple(sorted(positions))


@pytest.mark.parametrize("_case", range(8))
def test_grouped_group_key_and_aggregate_result_operands_lower_underlying_expressions(
    _case: int,
) -> None:
    windows_first = _case % 2 == 1
    _, _, script_ir = _compile(
        _grouped_source(dialect="postgresql", windows_first=windows_first)
    )
    relation = _relation(script_ir, "grouped")
    by_name = {item.name: item for item in relation.projections}
    group_name = by_name["group_name"].expression
    total = by_name["total"].expression
    group_rank = _window(by_name["group_rank"].expression)
    previous_total = _window(by_name["previous_total"].expression)
    check = _case // 2
    if check == 0:
        assert group_rank.spec.partition_by == (group_name,)
    elif check == 1:
        assert group_rank.spec.order_by[0].expression == total
        assert isinstance(total, AggregateCallIR)
    elif check == 2:
        assert previous_total.arguments == (
            total,
            previous_total.arguments[1],
            total,
        )
        assert isinstance(previous_total.arguments[1], LiteralIR)
    else:
        assert previous_total.spec.order_by[0].expression == total
        assert all(
            not (
                isinstance(item, FieldRefIR)
                and item.field is None
                and item.name in {"group_name", "total"}
            )
            for item in (
                *group_rank.spec.partition_by,
                *(order.expression for order in group_rank.spec.order_by),
                *previous_total.arguments,
                *(order.expression for order in previous_total.spec.order_by),
            )
        )


@pytest.mark.parametrize("_case", range(4))
def test_grouped_window_sql_is_same_level_without_subquery_or_alias_operands(
    _case: int,
) -> None:
    dialect = "postgresql" if _case % 2 == 0 else "mysql"
    windows_first = _case >= 2
    sql = _sql_for(
        _grouped_source(dialect=dialect, windows_first=windows_first), dialect
    )
    quote = '"' if dialect == "postgresql" else "`"
    assert "SELECT\n" in sql
    assert sql.count("SELECT") == 1
    assert "WITH " not in sql and "(SELECT" not in sql
    assert (
        f"RANK() OVER (PARTITION BY {quote}category{quote} "
        f"ORDER BY SUM({quote}amount{quote}) DESC)"
    ) in sql
    assert (
        f"LAG(SUM({quote}amount{quote}), 0, SUM({quote}amount{quote})) "
        f"OVER (ORDER BY SUM({quote}amount{quote}) ASC)"
    ) in sql
    over_clauses = tuple(
        fragment.partition(") AS ")[0]
        for fragment in sql.split("    ")
        if " OVER (" in fragment
    )
    assert over_clauses
    assert all(f"{quote}total{quote}" not in item for item in over_clauses)
    assert all(f"{quote}group_name{quote}" not in item for item in over_clauses)


@pytest.mark.parametrize("_case", range(4))
def test_downstream_window_fields_lower_through_ordinary_row_rules(_case: int) -> None:
    downstream_items = (
        "        result\n",
        "        windows.result\n",
        "        renamed = result\n",
        "        computed = result + 1\n",
    )
    source = (
        _single_window_source("row_number") + "query downstream:\n"
        "    from windows\n"
        "    select:\n" + downstream_items[_case]
    )
    _, _, script_ir = _compile(source)
    downstream = _relation(script_ir, "downstream")
    expression = downstream.projections[0].expression
    if _case < 3:
        assert isinstance(expression, FieldRefIR)
        assert expression.name == "result"
        assert expression.field is not None
        assert expression.field.name == "result"
        assert expression.qualifier == (() if _case != 1 else ("windows",))
    else:
        assert isinstance(expression, BinaryIR)
        assert isinstance(expression.left, FieldRefIR)
        assert expression.left.field is not None
        assert expression.left.name == "result"


@pytest.mark.parametrize("_case", range(4))
def test_final_order_window_aliases_render_as_aliases(_case: int) -> None:
    dialect = "postgresql" if _case % 2 == 0 else "mysql"
    grouped = _case >= 2
    if grouped:
        source = _grouped_source(dialect=dialect, windows_first=False)
        alias = "group_rank"
    else:
        source = (
            _single_window_source("row_number", dialect=dialect) + "    order by:\n"
            "        result desc\n"
        )
        alias = "result"
    _, _, script_ir = _compile(source)
    relation = _relation(script_ir)
    order = next(
        item
        for item in relation.order_by
        if isinstance(item.expression, FieldRefIR) and item.expression.name == alias
    )
    assert isinstance(order.expression, FieldRefIR)
    assert order.expression.field is None
    assert order.expression.qualifier == ()
    quote = '"' if dialect == "postgresql" else "`"
    sql = _sql_for(source, dialect)
    assert f"\n    {quote}{alias}{quote} " in sql
    final_order = sql.rpartition("\nORDER BY\n")[2]
    assert "OVER (" not in final_order


def _expected_single_window_sql(identity: str, *, dialect: str) -> str:
    quote = '"' if dialect == "postgresql" else "`"
    if identity in ZERO_ARGUMENT_IDENTITIES:
        arguments = ""
    elif identity == "ntile":
        arguments = "4"
    elif identity == "lag":
        arguments = f"{quote}amount{quote}, 2, {quote}amount{quote}"
    else:
        arguments = f"{quote}amount{quote}, 0, {quote}amount{quote}"
    expression = (
        f"{SQL_NAMES[identity]}({arguments}) OVER "
        f"(PARTITION BY {quote}category{quote} ORDER BY {quote}id{quote} DESC)"
    )
    return f"SELECT\n    {expression} AS {quote}result{quote}\nFROM {quote}rows{quote}"


@pytest.mark.parametrize("_case", range(8))
def test_postgres_exact_sql_bytes_for_all_identities(_case: int) -> None:
    identity = IDENTITIES[_case]
    source = _single_window_source(identity, dialect="postgresql")
    assert _sql_for(source, "postgresql") == _expected_single_window_sql(
        identity, dialect="postgresql"
    )


@pytest.mark.parametrize("_case", range(8))
def test_mysql_exact_sql_bytes_for_all_identities(_case: int) -> None:
    identity = IDENTITIES[_case]
    source = _single_window_source(identity, dialect="mysql")
    assert _sql_for(source, "mysql") == _expected_single_window_sql(
        identity, dialect="mysql"
    )


@pytest.mark.parametrize("_case", range(6))
def test_backend_identifier_quoting_and_escaping_differences_are_exact(
    _case: int,
) -> None:
    names = (
        "simple",
        'double"quote',
        "back`tick",
        "select",
        "with space",
        "Unicode_λ",
    )
    name = names[_case]
    expression = _manual_window(
        "row_number",
        spec=_spec(
            partition_by=(_field(name),),
            order_by=(
                _order_item(
                    _field(name, qualifier=("owner",)),
                    direction=OrderDirectionIR.DESC,
                    explicit=True,
                ),
            ),
        ),
    )
    postgres = render_expression_sql(expression)
    mysql = render_mysql_expression(expression)
    postgres_name = name.replace('"', '""')
    mysql_name = name.replace("`", "``")
    assert f'PARTITION BY "{postgres_name}"' in postgres
    assert f'ORDER BY "owner"."{postgres_name}" DESC' in postgres
    assert f"PARTITION BY `{mysql_name}`" in mysql
    assert f"ORDER BY `owner`.`{mysql_name}` DESC" in mysql
    assert postgres != mysql


@pytest.mark.parametrize("_case", range(8))
def test_postgres_malformed_window_ir_becomes_pie_b1000(_case: int) -> None:
    variants = range(6) if _case == 4 else range(4) if _case == 6 else range(1)
    for variant in variants:
        result = emit_postgres_sql(
            _malformed_script_ir(
                _case,
                dialect="postgresql",
                variant=variant,
            )
        )
        assert result.artifacts == ()
        assert len(result.diagnostics) == 1
        diagnostic = result.diagnostics[0]
        assert diagnostic.code == "PIE-B1000"
        assert diagnostic.location.path == "slice15.pietto"
        assert "PostgreSQL SQL emission is not implemented" in diagnostic.message


@pytest.mark.parametrize("_case", range(8))
def test_mysql_malformed_window_ir_becomes_pie_b1000(_case: int) -> None:
    variants = range(6) if _case == 4 else range(4) if _case == 6 else range(1)
    for variant in variants:
        result = emit_mysql_sql(
            _malformed_script_ir(_case, dialect="mysql", variant=variant)
        )
        assert result.artifacts == ()
        assert len(result.diagnostics) == 1
        diagnostic = result.diagnostics[0]
        assert diagnostic.code == "PIE-B1000"
        assert diagnostic.location.path == "slice15.pietto"
        assert "MySQL SQL emission is not implemented" in diagnostic.message


@pytest.mark.parametrize("_case", range(4))
def test_unrelated_missing_semantic_facts_preserve_pie_i1000(_case: int) -> None:
    source = (
        _source_connector("postgresql") + "query ordinary:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        copied = amount\n"
        "        computed = id + 1\n"
        "        normalized = lower(category)\n"
    )
    parsed = parse_source(source, path="slice15-missing.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    relation = cast(QueryDef | TableDef, parsed.ast.definitions[-1])
    expression = relation.select_items[_case].expression
    value_types = dict(semantic.model.expression_value_types)
    assert value_types.pop(expression, None) is not None
    missing_model = dataclasses.replace(
        semantic.model,
        expression_value_types=value_types,
    )
    result = lower_expr(expression, missing_model)
    assert result.expression is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-I1000"
    assert "expression value type" in result.diagnostics[0].message


SIGNATURE_OPERANDS = (
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Float",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Float",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1",
        "positive_int_literal",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1..3",
        "bounded_value_optional_offset_default",
        "T",
        "any_nullable_0_2_or_default_omitted_2",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1..3",
        "bounded_value_optional_offset_default",
        "T",
        "any_nullable_0_2_or_default_omitted_2",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1",
        "bounded_value",
        "T",
        "nullable",
        "WINDOW",
        "window_result",
        "mandatory_resolved_order",
    ),
    (
        "1",
        "bounded_value",
        "T",
        "nullable",
        "WINDOW",
        "window_result",
        "mandatory_resolved_order",
    ),
    (
        "2",
        "bounded_value_positive_int_literal",
        "T",
        "nullable",
        "WINDOW",
        "window_result",
        "mandatory_resolved_order",
    ),
)
LOWERING_OPERANDS = ("WindowCallIR", "OVER", "partition_by", "order_by")
NAVIGATION_LOWERING_OPERANDS = (*LOWERING_OPERANDS, "respect_nulls")
POSTGRESQL_FRAME_VALUE_LOWERING_OPERANDS = (
    "WindowCallIR",
    "OVER",
    "partition_by",
    "order_by",
    "rows_groups_offset_free_range_all_exclude",
    "respect_nulls",
    "from_first",
)
MYSQL_FRAME_VALUE_LOWERING_OPERANDS = (
    "WindowCallIR",
    "OVER",
    "partition_by",
    "order_by",
    "rows_offset_free_range_omitted_exclude",
    "respect_nulls",
    "from_first",
)
CAPABILITY_IDENTITIES = (*IDENTITIES, "first_value", "last_value", "nth_value")


@pytest.mark.parametrize("_case", range(33))
def test_window_capability_fact_inventory_keys_evidence_and_privacy_are_exact(
    _case: int,
) -> None:
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    assert capability_windows.__all__ == ()
    assert type(facts) is tuple and len(facts) == 33 and len(set(facts)) == 33
    fact = facts[_case]
    assert type(fact) is CapabilityFact
    assert fact.key.domain is CapabilityDomain.WINDOW_FUNCTION
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert fact.key.extension is None
    identity_index = _case % 11
    assert fact.key.subject == CAPABILITY_IDENTITIES[identity_index]
    if _case < 11:
        assert fact.key.operation == "signature"
        assert fact.key.context == "window_signature"
        assert fact.key.dialect is None
        assert fact.key.operands == SIGNATURE_OPERANDS[_case]
        assert tuple(item.source for item in fact.evidence) == (
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            CapabilityEvidenceSource.IR,
        )
        assert fact.evidence[-1].source_path == "src/pietto/ir/lowering.py"
        assert fact.evidence[-1].source_reference == "_lower_window_expr"
    else:
        postgres = _case < 22
        dialect = "postgresql" if postgres else "mysql"
        backend = "postgresql" if postgres else "private-mysql"
        source_path = (
            "src/pietto/sql/expressions.py"
            if postgres
            else "src/pietto/sql/mysql_expressions.py"
        )
        source_reference = (
            "render_window_call_sql" if postgres else "render_mysql_window_call"
        )
        assert fact.key.operation == "lowering"
        assert fact.key.context == "window_lowering"
        assert fact.key.dialect == dialect
        assert fact.key.operands == (
            (
                POSTGRESQL_FRAME_VALUE_LOWERING_OPERANDS
                if fact.key.subject == "nth_value"
                else (*POSTGRESQL_FRAME_VALUE_LOWERING_OPERANDS[:-1], "from_forbidden")
            )
            if fact.key.subject in {"first_value", "last_value", "nth_value"}
            and dialect == "postgresql"
            else (
                MYSQL_FRAME_VALUE_LOWERING_OPERANDS
                if fact.key.subject == "nth_value"
                else (*MYSQL_FRAME_VALUE_LOWERING_OPERANDS[:-1], "from_forbidden")
            )
            if fact.key.subject in {"first_value", "last_value", "nth_value"}
            else NAVIGATION_LOWERING_OPERANDS
            if fact.key.subject in {"lag", "lead"}
            else LOWERING_OPERANDS
        )
        assert len(fact.evidence) == 1
        evidence = fact.evidence[0]
        assert evidence.source is CapabilityEvidenceSource.BACKEND
        assert (
            evidence.source_path,
            evidence.source_reference,
            evidence.dialect,
            evidence.backend,
        ) == (source_path, source_reference, dialect, backend)


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = capability_windows.window_lookup_inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


@pytest.mark.parametrize("_case", range(8))
def test_window_capability_lookup_found_absent_unknown_and_conflict_are_exact(
    _case: int,
) -> None:
    if _case < 3:
        fact = capability_windows._WINDOW_CAPABILITY_FACTS[(0, 11, 22)[_case]]
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact is fact
        return
    if _case == 3:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="row_number",
            operation="signature",
            operands=(
                "0",
                "no_argument",
                "Float",
                "non_null",
                "WINDOW",
                "window_result",
                "mandatory_local_order",
            ),
            context="window_signature",
        )
        result = _lookup(key)
        assert isinstance(result, Absent)
        assert result.key == key
        assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY
        return
    if _case == 4:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="future_rank",
            operation="signature",
            operands=SIGNATURE_OPERANDS[0],
            context="window_signature",
        )
    elif _case == 5:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="sqlite",
        )
    elif _case == 6:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="postgresql",
            extension="vendor.rank",
        )
    else:
        first = capability_windows._WINDOW_CAPABILITY_FACTS[0]
        second = dataclasses.replace(
            first,
            evidence=(
                CapabilityEvidence(
                    CapabilityEvidenceSource.TEST,
                    SELF_REL,
                    "synthetic conflicting window evidence",
                ),
            ),
        )
        result = lookup_capability(
            first.key,
            (first, second),
            domain_complete=True,
        )
        assert isinstance(result, Conflict)
        assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
        assert result.evidence == (first, second)
        return
    result = _lookup(key)
    assert isinstance(result, Unknown)
    assert result.reason is CapabilityReasonCode.NOT_EVIDENCED


@pytest.mark.parametrize("_case", range(4))
def test_window_capability_facts_do_not_authorize_compiler_acceptance(
    _case: int,
) -> None:
    production_paths = (
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/expressions.py",
    )
    source = _read(production_paths[_case])
    assert "capability_windows" not in source
    assert "window_lookup_inputs" not in source
    if _case == 0:
        unsupported = (
            _source_connector("postgresql") + "query invalid:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number()\n"
        )
        parsed = parse_source(unsupported, path="slice15-nonauthority.pietto")
        assert parsed.ast is not None
        semantic = analyze(parsed.ast)
        assert semantic.diagnostics


def test_public_ir_sql_semantic_cli_json_and_metadata_surfaces_are_unchanged() -> None:
    private_names = {
        "WindowFunctionRoleIR",
        "WindowFunctionIdentityIR",
        "WindowOrderItemIR",
        "WindowSpecIR",
        "WindowCallIR",
    }
    assert private_names.isdisjoint(public_ir.__all__)
    assert all(not hasattr(public_ir, name) for name in private_names)
    assert "emit_mysql_sql" not in public_sql.__all__
    assert not hasattr(public_sql, "emit_mysql_sql")
    assert "CapabilityDomain" not in public_semantic.__all__
    assert "window_lookup_inputs" not in public_semantic.__all__
    assert capability_windows.__all__ == ()
    assert all(
        "WindowCallIR" not in _read(path)
        for path in (
            "src/pietto/cli.py",
            "src/pietto/_metadata/model.py",
            "src/pietto/_project/model.py",
        )
    )
    assert not hasattr(pietto, "__version__")


@pytest.mark.parametrize("_case", range(12))
def test_frames_named_windows_qualify_extension_and_later_identity_boundaries_are_locked(
    _case: int,
) -> None:
    if _case == 0:
        assert tuple(field.name for field in dataclasses.fields(WindowSpecIR)) == (
            "partition_by",
            "order_by",
            "span",
            "frame",
        )
    elif 1 <= _case <= 5:
        assert all(
            token not in {field.name for field in dataclasses.fields(WindowSpecIR)}
            for token in ("rows", "range", "groups", "name", "inherits")
        )
    elif _case == 6:
        grammar = " ".join(_read("grammar/Pietto.g4").split())
        assert "qualifyClause : QUALIFY" in grammar
        assert "QUALIFY: 'qualify';" in grammar
        assert "qualify" not in {field.name for field in dataclasses.fields(RelationIR)}
    elif 7 <= _case <= 9:
        identity = ("first_value", "last_value", "nth_value")[_case - 7]
        assert identity in capability_windows._WINDOW_IDENTITIES
        assert identity in ir_model._WINDOW_ARGUMENT_ARITIES
    else:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="postgresql" if _case == 10 else "sqlite",
            extension="vendor.rank" if _case == 10 else None,
        )
        result = _lookup(key)
        assert isinstance(result, Unknown)
        assert result.reason is CapabilityReasonCode.NOT_EVIDENCED
