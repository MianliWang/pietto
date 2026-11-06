"""Private project row expression type fact helpers."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping, Sequence
from types import MappingProxyType
from typing import TYPE_CHECKING, cast

from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    CapturedFieldExpr,
    CollectRelationExpr,
    DottedNameExpr,
    Expression,
    NameExpr,
    Node,
    QueryDef,
    RelationScalarExpr,
    TableDef,
    WindowExpr,
    inlined_arguments,
)
from pietto.errors import (
    Diagnostic,
    Severity,
    SourceLocation,
)
from pietto.semantic.aggregates import child_expressions, contains_semantic_aggregate
from pietto.semantic.expressions import (
    _reads_only_null,
    always_null,
    infer_row_expression,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    RowField,
    RowSchema,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

if TYPE_CHECKING:
    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts

_PROJECT_BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)
_UNKNOWN_PROJECT_FIELD_VALUE_TYPE = ValueType(
    resolved_type=ResolvedType(name="<unknown>", kind=TypeKind.UNKNOWN),
    nullability=EffectiveNullability.UNKNOWN,
    kind=ValueTypeKind.UNKNOWN,
)


# The closed places a nested relation field may be read in (PIE-S2805).
NESTED_IN_SCALAR_READ = "a scalar read"
NESTED_IN_IN_READ = "an in read"


def is_nested_relation_field(field: ProjectRowField | None) -> bool:
    """Whether ``field`` holds a collected relation, which no scalar reads."""

    return (
        field is not None
        and field.resolved_type.kind is ProjectResolvedTypeKind.NESTED_RELATION
    )


def nested_reference_positions(
    definition: TableDef | QueryDef,
) -> dict[int, str]:
    """The PIE-S2805 place of each expression node of one body, by identity.

    A window call, its window and a named window are ``a window`` and an ANY
    test is ``an ANY test`` wherever they are written.
    """

    positions: dict[int, str] = {}

    def mark(expression: Expression, label: str) -> None:
        pending = [(expression, label)]
        while pending:
            node, place = pending.pop()
            if type(node) is WindowExpr:
                place = "a window"
            elif type(node) is AnyExpr:
                place = "an ANY test"
            positions.setdefault(id(node), place)
            if type(node) is WindowExpr:
                children: tuple[Expression, ...] = (
                    *node.call.arguments,
                    *node.spec.partition_by,
                    *(item.expression for item in node.spec.order_by),
                )
            elif type(node) is AnyExpr:
                children = (node.predicate,)
            else:
                children = child_expressions(node)
            pending.extend((child, place) for child in children)

    if definition.let_clause is not None:
        for binding in definition.let_clause.bindings:
            mark(binding.expression, "a row let")
    for join in definition.join_clauses:
        if join.on_clause is not None:
            mark(join.on_clause.expression, "JOIN ON")
    if definition.where_clause is not None:
        mark(definition.where_clause.expression, "WHERE")
    for item in definition.select_items:
        mark(item.expression, "a SELECT expression")
    if definition.group_by_clause is not None:
        for key in definition.group_by_clause.items:
            mark(key.key, "GROUP BY")
    if definition.satisfying_clause is not None:
        mark(definition.satisfying_clause.expression, "HAVING")
    for window in definition.named_windows:
        if window.spec is not None:
            for value in window.spec.partition_by:
                mark(value, "a window")
            for order in window.spec.order_by:
                mark(order.expression, "a window")
    if definition.qualify_clause is not None:
        mark(definition.qualify_clause.expression, "QUALIFY")
    if definition.order_by_clause is not None:
        for order in definition.order_by_clause.items:
            mark(order.expression, "ORDER BY")
    return positions


def nested_reference_text(leaf: Expression) -> str:
    """A nested field reference as written."""

    if type(leaf) is NameExpr:
        return leaf.name
    if type(leaf) is DottedNameExpr:
        return ".".join(leaf.parts)
    if type(leaf) is CapturedFieldExpr:
        return f"{leaf.capture}.{leaf.field}"
    if type(leaf) is RelationScalarExpr:
        return f"{leaf.relation_name}.{leaf.column_name}"
    raise TypeError("A nested field reference is a name or a read.")


NESTED_CARRY_REFUSALS: Mapping[str, tuple[str, str]] = MappingProxyType(
    {
        "relation let": (
            "cannot be selected in a relation let: select it in the table or query itself.",
            "Select only the scalar fields you need in the let.",
        ),
        "right or full join": (
            "cannot be selected beside a RIGHT or FULL JOIN: such a JOIN does not carry a collected relation.",
            "Use a cross, inner or left join to keep the nested field.",
        ),
        "grouped": (
            "cannot be selected in a table or query with GROUP BY or an aggregate: it is no group key and has no aggregate.",
            "Group in another table or query and join it here.",
        ),
        "distinct": (
            "cannot be part of SELECT DISTINCT: a collected relation has no equality.",
            "Make the scalar rows distinct in another table or query and join it here.",
        ),
        "window": (
            "cannot be selected beside a window or QUALIFY yet.",
            "Compute the window in another table or query and join it here.",
        ),
    }
)


def is_nested_carry_item(leaf: Expression, definition: TableDef | QueryDef) -> bool:
    return not inlined_arguments(leaf) and any(
        item.expression is leaf for item in definition.select_items
    )


def is_nested_group_key(leaf: Expression, definition: TableDef | QueryDef) -> bool:
    """Whether ``leaf`` is a whole GROUP BY key, or names the field of one, of
    a body without JOIN inputs: the one place a nested field is a key."""

    if type(leaf) not in {NameExpr, DottedNameExpr} or definition.join_clauses:
        return False
    if definition.group_by_clause is None:
        return False
    name = nested_reference_text(leaf).split(".")[-1]
    return any(
        item.key is leaf
        or (
            type(item.key) in {NameExpr, DottedNameExpr}
            and nested_reference_text(item.key).split(".")[-1] == name
        )
        for item in definition.group_by_clause.items
    )


def nested_carry_refusal(
    definition: TableDef | QueryDef,
    *,
    relation_let: bool,
    leaf: Expression | None = None,
) -> str | None:
    """Why a SELECT item may not carry a nested field here; a nested GROUP BY
    key and a SELECT DISTINCT item of a body without JOIN inputs are carried
    (D73.05), compared by their decoded child values."""

    if relation_let:
        return "relation let"
    if any(
        join.kind in {AuthoredJoinKind.RIGHT, AuthoredJoinKind.FULL}
        for join in definition.join_clauses
    ):
        return "right or full join"
    expressions = [item.expression for item in definition.select_items]
    if definition.let_clause is not None:
        expressions.extend(item.expression for item in definition.let_clause.bindings)
    expressions.extend(
        join.on_clause.expression
        for join in definition.join_clauses
        if join.on_clause is not None
    )
    if definition.where_clause is not None:
        expressions.append(definition.where_clause.expression)
    if definition.satisfying_clause is not None:
        expressions.append(definition.satisfying_clause.expression)
    if definition.order_by_clause is not None:
        expressions.extend(item.expression for item in definition.order_by_clause.items)
    keyed = leaf is not None and not definition.join_clauses
    if (
        definition.group_by_clause is not None
        or any(contains_semantic_aggregate(item) for item in expressions)
    ) and not (keyed and is_nested_group_key(cast(Expression, leaf), definition)):
        return "grouped"
    if definition.distinct_clause is not None and not keyed:
        return "distinct"
    if definition.qualify_clause is not None or any(
        _contains_window(item) for item in expressions
    ):
        return "window"
    return None


def admits_nested_carry(
    leaf: Expression, definition: TableDef | QueryDef, *, relation_let: bool
) -> bool:
    return (
        type(leaf) in {NameExpr, DottedNameExpr}
        and is_nested_carry_item(leaf, definition)
        and nested_carry_refusal(definition, relation_let=relation_let, leaf=leaf)
        is None
    )


def admits_nested_key(
    leaf: Expression, definition: TableDef | QueryDef, *, relation_let: bool
) -> bool:
    """A GROUP BY key that is a nested input field as written, in a body that
    may carry it (no JOIN input, relation let, window or QUALIFY)."""

    return (
        not relation_let
        and type(leaf) in {NameExpr, DottedNameExpr}
        and definition.group_by_clause is not None
        and any(item.key is leaf for item in definition.group_by_clause.items)
        and is_nested_group_key(leaf, definition)
        and nested_carry_refusal(definition, relation_let=False, leaf=leaf) is None
    )


def _contains_window(expression: Expression) -> bool:
    pending = [expression]
    while pending:
        node = pending.pop()
        if type(node) is WindowExpr:
            return True
        pending.extend(child_expressions(node))
    return False


def nested_reference_diagnostic(
    leaf: Expression,
    definition: TableDef | QueryDef,
    *,
    root: Expression | None = None,
    relation_let: bool = False,
) -> Diagnostic:
    """PIE-S2805 for one read of a nested field in ``definition``'s body.

    A SELECT item that is the field itself would pass it through, which only
    the relation collecting it does yet; any other read, such as the argument
    a `def` call inlines as the item, has no value to read.
    """

    if is_nested_carry_item(leaf, definition):
        refusal = nested_carry_refusal(definition, relation_let=relation_let, leaf=leaf)
        if refusal is not None:
            message, suggestion = NESTED_CARRY_REFUSALS[refusal]
            return _error(
                "PIE-S2805",
                f"Nested relation field {nested_reference_text(leaf)} {message}",
                leaf,
                suggestion,
            )
        if type(leaf) in {NameExpr, DottedNameExpr}:
            raise ValueError("A carried nested field has no PIE-S2805.")
    if not inlined_arguments(leaf) and any(
        item.expression is leaf for item in definition.select_items
    ):
        return _error(
            "PIE-S2805",
            f"Nested relation field {nested_reference_text(leaf)} cannot be "
            "selected here yet: only the table or query that collects it "
            "outputs it.",
            leaf,
            "Select only the scalar fields you need here.",
        )
    positions = nested_reference_positions(definition)
    position = positions.get(id(leaf)) or (
        None if root is None else positions.get(id(root))
    )
    return nested_value_diagnostic(leaf, position or "a SELECT expression")


def nested_value_diagnostic(
    leaf: Expression, position: str, *, ref: str | None = None
) -> Diagnostic:
    """PIE-S2805: a collected relation has no scalar value at ``position``."""

    return _error(
        "PIE-S2805",
        f"Nested relation field {ref or nested_reference_text(leaf)} cannot be "
        f"read in {position}: a collected relation has no comparison, ordering, "
        "grouping or scalar value.",
        leaf,
        "Filter, order or group the collected rows inside the let that is collected.",
    )


def nested_order_diagnostic(leaf: Expression, place: str) -> Diagnostic:
    """PIE-S2805: a nested GROUP BY key or SELECT DISTINCT field compares the
    rows of its collected let in order, and that order may tie (D73.05)."""

    role = "a GROUP BY key" if place == "GROUP BY" else "part of SELECT DISTINCT"
    return _error(
        "PIE-S2805",
        f"Nested relation field {nested_reference_text(leaf)} cannot be {role}: "
        "the ORDER BY of its collected let does not end in a declared unique "
        "key, so rows that tie have no promised order.",
        leaf,
        "End the `order by` of the collected let with the fields of a "
        "`unique(...)` key of its source, such as `id`.",
    )


def nested_distinct_diagnostic(expression: CollectRelationExpr) -> Diagnostic:
    """PIE-S2805: SELECT DISTINCT compares rows, and a Collect value has no
    equality."""

    name = expression.relation_name
    return _error(
        "PIE-S2805",
        f"Collect relation read {name} cannot be part of SELECT DISTINCT: a "
        "collected relation has no equality.",
        expression,
        "Make the rows distinct in another table or query, read it with `from` "
        "here, and collect without DISTINCT.",
    )


def nested_set_operand_diagnostic(
    operand: Node, operand_name: str, field_name: str
) -> Diagnostic:
    """PIE-S2805: a set operation compares rows, and a nested field has no
    equality."""

    return _error(
        "PIE-S2805",
        f"Set operand {operand_name} outputs nested relation field {field_name}: "
        "a set operation over a collected relation is not available.",
        operand,
        "Leave the nested field out of the set operands.",
    )


def without_nested_window_refusal(
    diagnostics: Iterable[Diagnostic],
    window: WindowExpr,
    reason: str,
    nested: Iterable[SourceLocation | None],
) -> tuple[Diagnostic, ...]:
    """A refused window computation's diagnostics without the refusal the
    kernel derives from a nested field read (located in ``nested``), whose
    value it does not know. As at an unknown name, the kernel stops at the
    step that reads the field, and the read's PIE-S2805 is that step's error;
    what the kernel reported before reaching that step stays."""

    kept = tuple(diagnostics)
    arguments = window.call.arguments
    # The values read by each step `analyze_window_computation` refuses for a
    # value of no concrete type, by that refusal's reason.
    step = {
        "window partition field type must be concrete": window.spec.partition_by,
        "window order field type must be concrete": tuple(
            item.expression for item in window.spec.order_by
        ),
        "navigation value type must be concrete": arguments[:1],
        "navigation default type must be concrete": arguments[2:3],
        "frame-value input type must be concrete": arguments[:1],
    }.get(reason, ())
    leaves = set(nested)
    if (
        kept
        and kept[-1].location == node_location(window.call)
        and any(
            node_location(leaf) in leaves
            for value in step
            for leaf in scalar_field_reference_leaves(value)
        )
    ):
        return kept[:-1]
    return kept


def node_location(node: Node) -> SourceLocation:
    span = node.span
    return SourceLocation(
        path=span.path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _error(code: str, message: str, node: Node, suggestion: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=node_location(node),
        suggestion=suggestion,
    )


def scalar_field_reference_leaves(
    expression: Expression,
) -> tuple[NameExpr | DottedNameExpr, ...]:
    """Enumerate original row-reference occurrences, excluding call callees."""
    if not isinstance(expression, Expression):
        raise TypeError("Scalar reference traversal requires an expression.")
    if type(expression) is NameExpr:
        return (expression,)
    if type(expression) is DottedNameExpr:
        return (expression,)
    return tuple(
        leaf
        for child in child_expressions(expression)
        for leaf in scalar_field_reference_leaves(child)
    )


def scalar_read_types_within(
    expression: Expression, read_types: Mapping[Expression, ValueType] | None
) -> dict[Expression, ValueType]:
    """The owner's typed scalar relation reads written inside one expression."""
    result: dict[Expression, ValueType] = {}
    pending = [expression]
    while read_types and pending:
        node = pending.pop()
        typed = read_types.get(node) if type(node) is RelationScalarExpr else None
        if typed is not None:
            result[node] = typed
        pending.extend(child_expressions(node))
    return result


def project_row_field_to_semantic_value_type(
    field: ProjectRowField,
    effective_nullability: ProjectRowFieldNullability,
    *,
    shapes: bool = False,
) -> ValueType:
    """Adapt one exact Project field occurrence for the semantic type kernel,
    a shape too with ``shapes`` (`project_row_schema_to_semantic_row_schema`)."""

    if type(field) is not ProjectRowField:
        raise TypeError("Project field adaptation requires an exact row field.")
    if type(effective_nullability) is not ProjectRowFieldNullability:
        raise TypeError("Project field adaptation requires exact nullability.")
    resolved_type = _semantic_resolved_type(field.resolved_type, shapes=shapes)
    if resolved_type.kind is TypeKind.UNKNOWN:
        return _UNKNOWN_PROJECT_FIELD_VALUE_TYPE
    return ValueType(
        resolved_type=resolved_type,
        nullability=_semantic_nullability(effective_nullability),
    )


def build_project_row_expression_value_types(
    *,
    expressions: Iterable[Expression],
    input_schema: ProjectRowSchema,
    relation_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    read_types: Mapping[Expression, ValueType] | None = None,
    captured_value_types: (
        Mapping[CapturedFieldExpr, ValueType | Diagnostic] | None
    ) = None,
) -> Mapping[Expression, ValueType]:
    """Infer known row expression value types from a concrete project schema.

    ``read_types`` holds the owner's typed scalar relation reads and the column
    type of each ``in`` read; the kernel takes each from there and never types
    a relation read on its own.
    """

    if input_schema.is_unknown:
        return MappingProxyType({})

    row_schema = project_row_schema_to_semantic_row_schema(input_schema)
    value_types: dict[Expression, ValueType] = {}
    for expression in tuple(expressions):
        if contains_semantic_aggregate(expression):
            continue
        scratch_value_types = scalar_read_types_within(expression, read_types)
        diagnostics: list[Diagnostic] = []
        root_value_type = infer_row_expression(
            expression,
            row_schema,
            scratch_value_types,
            diagnostics,
            report_unknown_name=not isinstance(expression, NameExpr),
            field_qualifier=relation_qualifier,
            bare_value_types=bare_value_types,
            bare_value_expressions=bare_value_expressions,
            relation_columns=read_types,
            captured_value_types=captured_value_types,
        )
        if (
            diagnostics
            or root_value_type.kind is not ValueTypeKind.KNOWN
            or expression not in scratch_value_types
            or any(
                value_type.kind is not ValueTypeKind.KNOWN
                for value_type in scratch_value_types.values()
            )
        ):
            continue
        value_types.update(scratch_value_types)

    return MappingProxyType(value_types)


def untyped_null_parts(
    expression: Expression,
    value_types: Mapping[Expression, ValueType],
    lets: Mapping[str, Expression],
) -> bool:
    """Whether ``expression``, each part of it typed in ``value_types``, has
    a part of no known type and each outermost such part is NULL on every row
    by NULL propagation: `always_null` (a `None`; a sign, arithmetic or
    comparison with such an operand; a conditional or `coalesce` whose every
    value is one) with the `let:` names of ``lets`` written in, or a value
    that reads only `None` (`_reads_only_null`, as `nullif(None, None)`). So
    are `-None`, `amount + (-None)` and the `coalesce(None, None)` of
    `same_value(coalesce(None, None), amount)`; `amount + None` has none, as
    its `None` takes the type of `amount`."""

    names: dict[str, bool] = {}
    for name, value in lets.items():
        names[name] = always_null(value, names)
    untyped = False
    pending = [expression]
    while pending:
        node = pending.pop()
        value_type = value_types.get(node)
        if value_type is None:
            return False
        if value_type.kind is ValueTypeKind.KNOWN:
            pending.extend(child_expressions(node))
        elif _reads_only_null(node, lets) or always_null(node, names):
            untyped = True
        else:
            return False
    return untyped


def untyped_null_type(
    expression: Expression,
    input_schema: ProjectRowSchema,
    let_scope: ProjectRelationLetScopeFacts | None,
    *,
    relation_qualifier: str | None,
    read_types: Mapping[Expression, ValueType] | None,
    captured_value_types: Mapping[CapturedFieldExpr, ValueType | Diagnostic] | None,
) -> tuple[ProjectResolvedType, ProjectRowFieldNullability] | None:
    """The type and nullability of ``expression``, a SELECT output over
    ``input_schema`` with the bindings of ``let_scope`` that have no error of
    their own, typed as `build_project_row_expression_value_types` types it
    (with the owner's relation reads and capture environment), when it is
    typed without an error and its parts of no type are always NULL
    (`untyped_null_parts`), as a single file completes it: no type for
    `None`, `-None` or `amount + (-None)`, a Bool for
    `same_value(coalesce(None, None), amount)`. Its readers see that type;
    the relation's completion asks this for an output its row typing leaves
    open and marks the field it builds (`ProjectRowFieldProvenance`), which
    its PIE-S2385 warning reads, and SQL emission refuses it."""

    if input_schema.is_unknown:
        return None
    let_types = None if let_scope is None else let_scope.binding_value_types or None
    lets = (
        {}
        if let_scope is None
        else {name: let_scope.binding_expressions[name] for name in let_types or ()}
    )
    diagnostics: list[Diagnostic] = []
    value_types = scalar_read_types_within(expression, read_types)
    value_type = infer_row_expression(
        expression,
        project_row_schema_to_semantic_row_schema(input_schema),
        value_types,
        diagnostics,
        report_unknown_name=True,
        field_qualifier=relation_qualifier,
        bare_value_types=let_types,
        bare_value_expressions=None if let_types is None else lets,
        relation_columns=read_types,
        captured_value_types=captured_value_types,
    )
    value_types[expression] = value_type
    if diagnostics or not untyped_null_parts(expression, value_types, lets):
        return None
    if value_type.kind is ValueTypeKind.UNKNOWN:
        return ProjectResolvedType(
            name=_UNKNOWN_PROJECT_FIELD_VALUE_TYPE.resolved_type.name,
            kind=ProjectResolvedTypeKind.UNKNOWN,
        ), ProjectRowFieldNullability.NULLABLE
    resolved = value_type.resolved_type
    if (
        resolved.kind is not TypeKind.BUILTIN
        or resolved.name not in _PROJECT_BUILTIN_TYPE_NAMES
    ):
        return None
    return ProjectResolvedType(
        name=resolved.name, kind=ProjectResolvedTypeKind.BUILTIN
    ), ProjectRowFieldNullability(value_type.nullability.value)


def reports_unfit_def_argument(
    expression: Expression,
    row_schema: RowSchema,
    *,
    relation_qualifier: str | None,
    bare_value_types: Mapping[str, ValueType] | None = None,
    bare_value_expressions: Mapping[str, Expression] | None = None,
    suppressed_unknown_names: set[str] | None = None,
    read_types: Mapping[Expression, ValueType] | None = None,
    captured_value_types: (
        Mapping[CapturedFieldExpr, ValueType | Diagnostic] | None
    ) = None,
) -> bool:
    """Whether ``expression``, a field or `let:` name selected as passed to a
    ``def``, reports an error typed as the select check types it, over
    ``row_schema``, the relation's input as the select check reads it
    (`project_row_schema_to_semantic_row_schema`), as PIE-S2395 for one that
    does not fit its parameter. Its column is then no copy of the field or
    `let:` value: the relation's rows are deferred, as for a computed
    expression whose typing fails."""

    if not inlined_arguments(expression):
        return False
    diagnostics: list[Diagnostic] = []
    infer_row_expression(
        expression,
        row_schema,
        scalar_read_types_within(expression, read_types),
        diagnostics,
        report_unknown_name=True,
        field_qualifier=relation_qualifier,
        bare_value_types=bare_value_types,
        bare_value_expressions=bare_value_expressions,
        suppressed_unknown_names=suppressed_unknown_names,
        relation_columns=read_types,
        captured_value_types=captured_value_types,
    )
    return any(item.severity is Severity.ERROR for item in diagnostics)


def project_row_schema_to_semantic_row_schema(
    input_schema: ProjectRowSchema,
    *,
    shapes: bool = False,
) -> RowSchema:
    """Convert a private project row schema into semantic row-schema facts.

    With ``shapes``, as for the input of a selected window, a field of a shape
    is typed as that shape, as in a single file; elsewhere its type is unknown.
    """

    fields: dict[str, RowField] = {}
    for name, field in input_schema.fields.items():
        fields[name] = RowField(
            name=name,
            resolved_type=_semantic_resolved_type(field.resolved_type, shapes=shapes),
            nullability=_semantic_nullability(field.nullability),
            definition=field.field_def,
        )
    return RowSchema(fields=fields)


def add_shape_typed_diagnostics(
    input_schema: ProjectRowSchema,
    reported: list[Diagnostic],
    start: int,
    infer: Callable[[RowSchema, list[Diagnostic]], object],
) -> None:
    """Type the expression of ``input_schema`` whose diagnostics are
    ``reported[start:]`` again, with each field of a shape typed as that
    shape, as in a single file: a project types such a field as unknown,
    which no operator or function refuses, so `home + 1` is PIE-S2105 here
    too."""

    if input_schema.is_unknown or not any(
        field.resolved_type.kind is ProjectResolvedTypeKind.SHAPE
        for field in input_schema.fields.values()
    ):
        return
    found: list[Diagnostic] = []
    infer(project_row_schema_to_semantic_row_schema(input_schema, shapes=True), found)
    merge_shape_typed_diagnostics(reported, start, found)


def merge_shape_typed_diagnostics(
    reported: list[Diagnostic], start: int, found: Sequence[Diagnostic]
) -> None:
    """Merge into ``reported``, where ``reported[start:]`` came from typing an
    expression with each field of a shape unknown, the diagnostics ``found``
    by typing it with each such field a shape. When that adds an error, the
    expression's diagnostics become ``found``, in its order, as a single file
    reports them; otherwise what it adds follows them."""

    added = [item for item in found if item not in reported]
    if any(item.severity is Severity.ERROR for item in added):
        earlier = reported[:start]
        reported[start:] = [item for item in found if item not in earlier]
    else:
        reported.extend(added)


def _semantic_resolved_type(
    resolved_type: ProjectResolvedType, *, shapes: bool = False
) -> ResolvedType:
    if resolved_type.kind is ProjectResolvedTypeKind.NESTED_RELATION:
        # A collected relation has no scalar value: the kernel never types it,
        # and the reference authorities refuse each read of it (PIE-S2805).
        return _UNKNOWN_PROJECT_FIELD_VALUE_TYPE.resolved_type
    if (
        resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
        and resolved_type.name in _PROJECT_BUILTIN_TYPE_NAMES
    ):
        return ResolvedType(name=resolved_type.name, kind=TypeKind.BUILTIN)
    kind = {
        ProjectResolvedTypeKind.ENUM: TypeKind.ENUM,
        ProjectResolvedTypeKind.SHAPE: TypeKind.SHAPE if shapes else None,
    }.get(resolved_type.kind)
    if kind is not None and resolved_type.symbol is not None:
        # An enum or shape, also through an alias of it, is that declaration,
        # as in a single file.
        return ResolvedType(
            name=resolved_type.name,
            kind=kind,
            definition=resolved_type.symbol.definition,
        )
    return ResolvedType(name=resolved_type.name, kind=TypeKind.UNKNOWN)


def _semantic_nullability(
    nullability: ProjectRowFieldNullability,
) -> EffectiveNullability:
    if nullability is ProjectRowFieldNullability.NON_NULL:
        return EffectiveNullability.NON_NULL
    if nullability is ProjectRowFieldNullability.NULLABLE:
        return EffectiveNullability.NULLABLE
    return EffectiveNullability.UNKNOWN
