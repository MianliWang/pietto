"""Private transient input scopes for bounded window analysis."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

from pietto.ast_nodes import (
    CallExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    QueryDef,
    SelectItem,
    TableDef,
    WindowExpr,
)
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    is_semantic_aggregate_call,
    semantic_aggregate_call_name,
    semantic_projection_aggregate_result_value_type,
)
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.group_by import project_grouped_schema
from pietto.semantic.model import (
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

__all__: tuple[str, ...] = ()

DerivedRelation = TableDef | QueryDef


class WindowInputScopeKind(StrEnum):
    """The already-completed stage exposed to one window expression."""

    ROW = "row"
    GROUPED_RESULT = "grouped_result"


class WindowInputOriginKind(StrEnum):
    """Private origin used only while translating window dependencies."""

    UPSTREAM_FIELD = "upstream_field"
    LET_BINDING = "let_binding"
    GROUP_KEY = "group_key"
    AGGREGATE_RESULT = "aggregate_result"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowInputBinding:
    """One bare input identity admitted by the bounded window contract."""

    name: str
    value_type: ValueType
    origin: WindowInputOriginKind
    target_name: str
    source_field_name: str | None = None

    def __post_init__(self) -> None:
        if type(self.name) is not str or not self.name:
            raise ValueError("window input binding name must be nonblank")
        if type(self.value_type) is not ValueType:
            raise TypeError("window input binding value_type must be exact ValueType")
        if type(self.origin) is not WindowInputOriginKind:
            raise TypeError("window input binding origin must be exact")
        if type(self.target_name) is not str or not self.target_name:
            raise ValueError("window input binding target_name must be nonblank")
        if self.source_field_name is not None and (
            type(self.source_field_name) is not str or not self.source_field_name
        ):
            raise ValueError("source_field_name must be None or nonblank")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowInputScope:
    """One immutable, non-persisted ROW or GROUP-to-WINDOW scope."""

    kind: WindowInputScopeKind
    row_schema: RowSchema
    bindings: tuple[WindowInputBinding, ...]
    allows_qualified_fields: bool
    has_valid_group_aggregate: bool

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowInputScopeKind:
            raise TypeError("window input scope kind must be exact")
        if type(self.row_schema) is not RowSchema:
            raise TypeError("window input row_schema must be exact RowSchema")
        if type(self.bindings) is not tuple or any(
            type(item) is not WindowInputBinding for item in self.bindings
        ):
            raise TypeError("window input bindings must contain exact carriers")
        if type(self.allows_qualified_fields) is not bool:
            raise TypeError("allows_qualified_fields must be an exact bool")
        if type(self.has_valid_group_aggregate) is not bool:
            raise TypeError("has_valid_group_aggregate must be an exact bool")
        if self.kind is WindowInputScopeKind.ROW:
            if not self.allows_qualified_fields or self.has_valid_group_aggregate:
                raise ValueError("ROW scope flags are inconsistent")
        elif self.allows_qualified_fields:
            raise ValueError("grouped-result scope forbids qualified inputs")

    @property
    def bare_value_types(self) -> Mapping[str, ValueType]:
        """Return first-winner bare bindings without exposing mutable state."""

        values: dict[str, ValueType] = {}
        for binding in self.bindings:
            values.setdefault(binding.name, binding.value_type)
        return MappingProxyType(values)

    def resolve(
        self,
        expression: Expression,
        *,
        field_qualifier: str,
    ) -> WindowInputBinding | None:
        """Resolve one already-validated direct window input to its origin."""

        if type(expression) is NameExpr:
            name = expression.name
        elif (
            type(expression) is DottedNameExpr
            and self.allows_qualified_fields
            and len(expression.parts) == 2
            and expression.parts[0] == field_qualifier
        ):
            name = expression.parts[1]
        else:
            return None
        return next((item for item in self.bindings if item.name == name), None)


def build_window_input_scope(
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: Mapping[Expression, ValueType],
    let_value_types: Mapping[str, ValueType] | None = None,
    let_expressions: Mapping[str, Expression] | None = None,
) -> WindowInputScope:
    """Build the exact transient input scope for one relation's window stage."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("definition must be an exact TableDef or QueryDef")
    if type(input_schema) is not RowSchema:
        raise TypeError("input_schema must be an exact RowSchema")
    if type(field_qualifier) is not str:
        raise TypeError("field_qualifier must be an exact string")

    if definition.group_by_clause is None:
        return _build_row_scope(
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            let_value_types=let_value_types,
            let_expressions=let_expressions,
        )
    return _build_grouped_scope(
        definition=definition,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=value_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )


def _build_row_scope(
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    let_value_types: Mapping[str, ValueType] | None,
    let_expressions: Mapping[str, Expression] | None,
) -> WindowInputScope:
    bindings = [
        WindowInputBinding(
            name=field.name,
            value_type=_field_value_type(field),
            origin=WindowInputOriginKind.UPSTREAM_FIELD,
            target_name=field.name,
            source_field_name=field.name,
        )
        for field in input_schema.fields.values()
        if _is_concrete_field(field)
    ]
    for name, value_type in (let_value_types or {}).items():
        source_field_name = _resolve_field_backed_let(
            name,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            let_expressions=let_expressions or {},
            stack=frozenset(),
        )
        if source_field_name is None or not _is_concrete_value_type(value_type):
            continue
        bindings.append(
            WindowInputBinding(
                name=name,
                value_type=value_type,
                origin=WindowInputOriginKind.LET_BINDING,
                target_name=name,
                source_field_name=source_field_name,
            )
        )
    return WindowInputScope(
        kind=WindowInputScopeKind.ROW,
        row_schema=input_schema,
        bindings=tuple(bindings),
        allows_qualified_fields=True,
        has_valid_group_aggregate=False,
    )


def _build_grouped_scope(
    *,
    definition: DerivedRelation,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: Mapping[Expression, ValueType],
    let_value_types: Mapping[str, ValueType] | None,
    let_expressions: Mapping[str, Expression] | None,
) -> WindowInputScope:
    scratch_types = dict(value_types)
    _populate_aggregate_value_types(
        definition,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        value_types=scratch_types,
        let_value_types=let_value_types,
        let_expressions=let_expressions,
    )
    grouped_schema, _ = project_grouped_schema(
        definition,
        input_schema,
        expression_value_types=scratch_types,
        let_expansions=let_expressions,
    )
    output_names = tuple(
        _projection_output_name(item) for item in definition.select_items
    )
    counts = Counter(name for name in output_names if name is not None)
    group_key_identities = _group_key_identities(
        definition,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        let_expressions=let_expressions or {},
    )

    output_bindings: list[WindowInputBinding] = []
    for item, output_name in zip(definition.select_items, output_names, strict=True):
        if (
            output_name is None
            or counts[output_name] != 1
            or type(item.expression) is WindowExpr
        ):
            continue
        field = grouped_schema.fields.get(output_name)
        if field is None or not _is_concrete_field(field):
            continue
        if contains_semantic_aggregate(item.expression):
            if not (
                type(item.expression) is CallExpr
                and is_semantic_aggregate_call(item.expression)
                and item.alias is not None
            ):
                continue
            origin = WindowInputOriginKind.AGGREGATE_RESULT
            source_field_name = None
        else:
            source_field_name = _resolve_field_expression(
                item.expression,
                input_schema=input_schema,
                field_qualifier=field_qualifier,
                let_expressions=let_expressions or {},
                stack=frozenset(),
            )
            if source_field_name not in group_key_identities:
                continue
            origin = WindowInputOriginKind.GROUP_KEY
        output_bindings.append(
            WindowInputBinding(
                name=output_name,
                value_type=_field_value_type(field),
                origin=origin,
                target_name=output_name,
                source_field_name=source_field_name,
            )
        )

    bindings = list(output_bindings)
    occupied = {item.name for item in bindings}
    group_key_outputs = tuple(
        item
        for item in output_bindings
        if item.origin is WindowInputOriginKind.GROUP_KEY
    )
    for name, value_type in (let_value_types or {}).items():
        if name in occupied or not _is_concrete_value_type(value_type):
            continue
        source_field_name = _resolve_field_backed_let(
            name,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            let_expressions=let_expressions or {},
            stack=frozenset(),
        )
        matched = next(
            (
                item
                for item in group_key_outputs
                if item.source_field_name == source_field_name
            ),
            None,
        )
        if matched is None:
            continue
        bindings.append(
            WindowInputBinding(
                name=name,
                value_type=matched.value_type,
                origin=WindowInputOriginKind.GROUP_KEY,
                target_name=matched.target_name,
                source_field_name=source_field_name,
            )
        )
        occupied.add(name)

    grouped_fields = {
        item.name: RowField(
            name=item.name,
            resolved_type=item.value_type.resolved_type,
            nullability=item.value_type.nullability,
        )
        for item in output_bindings
    }
    return WindowInputScope(
        kind=WindowInputScopeKind.GROUPED_RESULT,
        row_schema=RowSchema(fields=grouped_fields),
        bindings=tuple(bindings),
        allows_qualified_fields=False,
        has_valid_group_aggregate=any(
            item.origin is WindowInputOriginKind.AGGREGATE_RESULT
            for item in output_bindings
        ),
    )


def _populate_aggregate_value_types(
    definition: DerivedRelation,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    value_types: dict[Expression, ValueType],
    let_value_types: Mapping[str, ValueType] | None,
    let_expressions: Mapping[str, Expression] | None,
) -> None:
    for item in definition.select_items:
        expression = item.expression
        if type(expression) is not CallExpr or not is_semantic_aggregate_call(
            expression
        ):
            continue
        function_name = semantic_aggregate_call_name(expression)
        assert function_name is not None
        argument_type: ValueType | None = None
        if len(expression.arguments) == 1:
            argument = expression.arguments[0]
            argument_type = infer_row_expression(
                argument,
                input_schema,
                value_types,
                [],
                report_unknown_name=True,
                field_qualifier=field_qualifier,
                bare_value_types=let_value_types,
                bare_value_expressions=let_expressions,
            )
        result = semantic_projection_aggregate_result_value_type(
            function_name,
            argument_type,
        )
        if result is not None:
            value_types[expression] = result


def _group_key_identities(
    definition: DerivedRelation,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    let_expressions: Mapping[str, Expression],
) -> frozenset[str]:
    assert definition.group_by_clause is not None
    identities = {
        identity
        for item in definition.group_by_clause.items
        if (
            identity := _resolve_field_expression(
                item.key,
                input_schema=input_schema,
                field_qualifier=field_qualifier,
                let_expressions=let_expressions,
                stack=frozenset(),
            )
        )
        is not None
    }
    return frozenset(identities)


def _resolve_field_backed_let(
    name: str,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    let_expressions: Mapping[str, Expression],
    stack: frozenset[str],
) -> str | None:
    if name in stack:
        return None
    expression = let_expressions.get(name)
    if expression is None:
        return None
    return _resolve_field_expression(
        expression,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        let_expressions=let_expressions,
        stack=stack | frozenset((name,)),
    )


def _resolve_field_expression(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    let_expressions: Mapping[str, Expression],
    stack: frozenset[str],
) -> str | None:
    if type(expression) is NameExpr:
        if expression.name in input_schema.fields:
            return expression.name
        return _resolve_field_backed_let(
            expression.name,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            let_expressions=let_expressions,
            stack=stack,
        )
    if (
        type(expression) is DottedNameExpr
        and len(expression.parts) == 2
        and expression.parts[0] == field_qualifier
        and expression.parts[1] in input_schema.fields
    ):
        return expression.parts[1]
    return None


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    if type(item.expression) is NameExpr:
        return item.expression.name
    if type(item.expression) is DottedNameExpr:
        return item.expression.parts[-1]
    return None


def _is_concrete_field(field: RowField) -> bool:
    return field.resolved_type.kind is not TypeKind.UNKNOWN


def _is_concrete_value_type(value_type: ValueType) -> bool:
    return (
        value_type.kind is ValueTypeKind.KNOWN
        and value_type.resolved_type.kind is not TypeKind.UNKNOWN
    )


def _field_value_type(field: RowField) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(
            name=field.resolved_type.name,
            kind=field.resolved_type.kind,
            definition=field.resolved_type.definition,
        ),
        nullability=field.nullability,
    )
