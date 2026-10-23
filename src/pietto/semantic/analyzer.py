"""Semantic analysis entry point."""

from __future__ import annotations

from pietto.ast_nodes import SetRelationDef
from pietto._flat_relational_admission import syntax_diagnostics
from pietto._syntax_admission import unadmitted_syntax_diagnostics

from collections.abc import Callable, Iterator, Mapping
from dataclasses import fields, is_dataclass, replace
from heapq import heappop, heappush
from typing import TYPE_CHECKING, cast

from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CastExpr,
    CallExpr,
    CheckDef,
    ConditionalExpr,
    ComparisonExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    Expression,
    FieldDef,
    FromClause,
    GroupByClause,
    IsNullExpr,
    IndexDef,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Node,
    Nullability,
    QueryDef,
    RelationshipMatchClause,
    Script,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
    WindowSpec,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import (
    MAX_AGGREGATE_NAME,
    MIN_AGGREGATE_NAME,
    is_semantic_aggregate_call,
    semantic_aggregate_call_name,
)
from pietto.semantic.callables import (
    check_callable_bodies,
    check_callable_signatures,
)
from pietto.semantic.catalog import BUILTIN_TYPE_NAMES
from pietto.semantic.expressions import (
    type_callable_bodies,
    type_relation_expressions,
    type_shape_field_derives,
    type_shape_predicates,
    type_source_connector_arguments,
)
from pietto.semantic.field_derive_cycles import check_field_derive_cycles
from pietto.semantic.inline_functions import (
    drop_repeated_call_diagnostics,
    inline_functions,
)
from pietto.semantic.join_fanout import join_fanout_diagnostics
from pietto.semantic.joins import (
    JoinStructure,
    build_join_structures,
    check_join_semantics,
    join_input_row,
    join_post_pass,
    joined_input_rows,
)
from pietto.semantic.let_bindings import (
    analyze_relation_let_bindings,
    join_reserved_let_names,
    let_expansion_diagnostics,
)
from pietto.semantic.model import (
    CheckMode,
    DecimalPrecisionScale,
    EffectiveNullability,
    LetScopeSemanticInfo,
    ResolvedType,
    RowField,
    RowSchema,
    SemanticModel,
    SemanticResult,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.relation_cycles import check_relation_cycles
from pietto.semantic.relation_limits import check_relation_limits
from pietto.semantic.relation_schemas import (
    JoinedInputBuilder,
    project_relation_schema,
    propagate_relation_schemas,
    reads_relation_input,
)
from pietto.semantic.relationship_metadata import (
    check_relationship_conditions,
    check_relationship_metadata,
)
from pietto.semantic.relations import check_join_references, resolve_relation_inputs
from pietto.semantic.shapes import check_field_derives, check_shape_structures
from pietto.semantic.source_connectors import (
    check_source_connectors,
    check_table_names,
)
from pietto.semantic.satisfying import check_satisfying_clauses
from pietto.semantic.row_lookup import bare_field, qualified_field
from pietto.semantic.sources import check_sources
from pietto.semantic.type_aliases import expand_type_aliases

if TYPE_CHECKING:
    from pietto.semantic.window_semantics import (
        ResolvedNamedWindowNamespace,
        WindowExpressionAnalysis,
    )

_DECIMAL_PRECISION_MAX = 65
# Analysis spends up to two Python frames per nested expression level, so an
# expression at this bound takes about 910 of the interpreter's default 1000
# frames. Only the refusal is independent of the caller: a deeper expression is
# PIE-S2006 for every command and caller alike, while one at the bound is
# accepted only when the caller is at most about 85 frames deeper than a
# top-level call, and each level less leaves the caller about two more frames.
# RecursionError stays the guard for other deep chains, such as type aliases.
_MAX_EXPRESSION_LEVELS = 450
# How PIE-S2103 starts, before the called name.
_UNKNOWN_FUNCTION = "Unknown function: "


def analyze(
    script: Script,
    *,
    mode_override: CheckMode | None = None,
) -> SemanticResult:
    """Build the incremental semantic model and ordered diagnostics."""

    return _analyze_script(script, mode_override=mode_override, single_file=True)


def analyze_project_namespace(script: Script) -> SemanticResult:
    """Analyze the shared namespace of a LEGACY_FLAT project as one script.

    Such a project emits no SQL, so the analysis types as an explicit-module
    project check does and omits the checks that only single-file SQL needs:
    a field of an alias of an enum is typed as that enum, a `let:` name may be
    selected unaliased, and there is no let inline expansion limit
    (PIE-S2328), no refusal of a bare constant ungrouped ORDER BY key other
    than an integer literal (which the parser refuses, PIE-P1000), no ROWS
    or GROUPS frame offset or window count literal range check (a RANGE
    offset of a selected window is checked, as in an explicit-module check,
    and one of a QUALIFY window is not, as in a single file), no refusal of
    a `min` or `max` whose argument is a `let:` name in a relation without
    GROUP BY (PIE-S2315) and no connector table-name check, so source
    connectors get the diagnostics of an explicit-module check. An ungrouped
    ORDER BY key still reads input fields and `let:` bindings but no SELECT
    output other than a selected window result named alone (`w`, not
    `w + 1`). It has no JOIN binding fields, computed `let:` group keys or
    aggregates of `let:` names in grouped relations, so it reports nothing
    inside a table or query that reads one or reads such a relation. LOOSE
    omits the diagnostics that a check mode selects, which project commands
    do not take.
    """

    return _analyze_script(script, mode_override=CheckMode.LOOSE, single_file=False)


def _analyze_script(
    script: Script,
    *,
    mode_override: CheckMode | None,
    single_file: bool,
) -> SemanticResult:
    mode = mode_override or CheckMode.CHECKED
    try:
        mode = mode_override or _mode_from_script(script)
        unadmitted = unadmitted_syntax_diagnostics(script, single_file=single_file)
        if unadmitted:
            return SemanticResult(
                model=SemanticModel(mode=mode), diagnostics=unadmitted, script=script
            )
        parsed = script
        script, inline_diagnostics = inline_functions(script)
        if inline_diagnostics:
            return SemanticResult(
                model=SemanticModel(mode=mode),
                diagnostics=name_uncallable_calls(
                    inline_diagnostics, parsed, shared=not single_file
                ),
                script=script,
            )
        # Measured with every def call inlined, as analysis reads the script:
        # an expansion can nest deeper than its call. The checks above walk
        # the parsed script without recursion, so their errors come first.
        if _expression_levels(script) <= _MAX_EXPRESSION_LEVELS:
            result = _analyze(script, mode=mode, single_file=single_file)
            return replace(
                result,
                diagnostics=name_uncallable_calls(
                    drop_repeated_call_diagnostics(parsed, result.diagnostics),
                    parsed,
                    shared=not single_file,
                ),
            )
    except RecursionError:
        pass
    return SemanticResult(
        script=script,
        model=SemanticModel(mode=mode),
        diagnostics=(recursion_limit_diagnostic(script),),
    )


def name_uncallable_calls(
    diagnostics: tuple[Diagnostic, ...], *scripts: Script, shared: bool = False
) -> tuple[Diagnostic, ...]:
    """Say that an unknown call names a constraint or derive of its own source
    file, which cannot be called, in place of any other hint; keep code, span
    and order. With ``shared`` the scripts' files are one callable namespace,
    as a LEGACY_FLAT project's are, so the name may be declared in any of
    them. The first declaration of a name in a file, or in the shared
    namespace, holds it, as in the callable namespace. With no such call the
    same tuple is returned, since readers may compare diagnostics by
    identity."""

    kinds: dict[tuple[str | None, str], str] = {}
    for script in scripts:
        for definition in script.definitions:
            if type(definition) in (ConstraintDef, DeriveDef):
                kinds.setdefault(
                    (None if shared else definition.span.path, definition.name),
                    "constraint" if type(definition) is ConstraintDef else "derive",
                )
    named = list(diagnostics)
    for position, diagnostic in enumerate(diagnostics):
        # The called name, before any hint for it.
        name = diagnostic.message.removeprefix(_UNKNOWN_FUNCTION).partition(";")[0]
        kind = kinds.get((None if shared else diagnostic.location.path, name))
        if (
            diagnostic.code == "PIE-S2103"
            and diagnostic.message.startswith(_UNKNOWN_FUNCTION)
            and kind is not None
        ):
            named[position] = replace(
                diagnostic,
                message=f"{_UNKNOWN_FUNCTION}{name}; {name} is a {kind}, which "
                "cannot be called; write a `def` instead",
            )
    if all(new is old for new, old in zip(named, diagnostics, strict=True)):
        return diagnostics
    return tuple(named)


def _expression_levels(script: Script) -> int:
    """Return the most expressions nested one in another anywhere in a script."""

    deepest = 0
    pending: list[tuple[object, int]] = [(script, 0)]
    while pending:
        value, levels = pending.pop()
        if type(value) is tuple:
            pending.extend((item, levels) for item in value)
        elif type(value) is not Span and is_dataclass(value):
            # Every AST dataclass, a window frame and its bounds included.
            if isinstance(value, Expression):
                levels += 1
                deepest = max(deepest, levels)
            pending.extend(
                (getattr(value, field.name), levels) for field in fields(value)
            )
    return deepest


def recursion_limit_diagnostic(*scripts: Script) -> Diagnostic:
    """Report PIE-S2006 over the whole file of the script that nests deepest,
    the first such script."""

    span = max(scripts, key=_nesting_depth).span
    return Diagnostic(
        code="PIE-S2006",
        severity=Severity.ERROR,
        message="Semantic analysis recursion limit exceeded while processing source.",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _nesting_depth(script: Script) -> int:
    deepest = 0
    # A project reads each conjunct of a relationship `on` one at a time and
    # only at its top, so the condition adds no depth.
    pending: list[tuple[object, int]] = [(script, 0)]
    while pending:
        value, depth = pending.pop()
        if type(value) is tuple:
            pending.extend((item, depth) for item in cast(tuple[object, ...], value))
        elif isinstance(value, Node):
            deepest = max(deepest, depth)
            if type(value) is not RelationshipMatchClause:
                pending.extend(
                    (getattr(value, item.name), depth + 1) for item in fields(value)
                )
    return deepest


def _analyze(script: Script, *, mode: CheckMode, single_file: bool) -> SemanticResult:
    """Implement semantic analysis inside the public recursion boundary."""

    type_symbols: dict[str, Definition] = {}
    callable_symbols: dict[str, Definition] = {}
    relation_symbols: dict[str, Definition] = {}
    type_resolutions: dict[TypeExpr, ResolvedType] = {}
    type_expansions: dict[TypeExpr, ResolvedType] = {}
    type_nullability: dict[TypeExpr, EffectiveNullability] = {}
    decimal_precision_scales: dict[TypeExpr, DecimalPrecisionScale] = {}
    diagnostics: list[Diagnostic] = []

    for definition in script.definitions:
        namespace_name, namespace = _namespace_for(
            definition,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
        )
        if isinstance(definition, EnumDef):
            diagnostics.extend(_duplicate_enum_member_diagnostics(definition))
        if definition.name in namespace:
            diagnostics.append(_duplicate_diagnostic(definition, namespace_name))
            continue
        namespace[definition.name] = definition

    relationships, relationship_diagnostics = check_relationship_metadata(
        script,
        relation_symbols,
    )
    diagnostics.extend(relationship_diagnostics)

    for type_expr in _iter_type_expressions(script):
        _record_type_expression(
            type_expr,
            type_symbols=type_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            diagnostics=diagnostics,
            mode=mode,
            report_implicit_nullability=True,
        )
    for type_expr in _iter_cast_target_type_expressions(script):
        _record_type_expression(
            type_expr,
            type_symbols=type_symbols,
            type_resolutions=type_resolutions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            diagnostics=diagnostics,
            mode=mode,
            report_implicit_nullability=False,
        )

    type_expansions, alias_diagnostics = expand_type_aliases(
        script,
        type_symbols=type_symbols,
        type_resolutions=type_resolutions,
    )
    diagnostics.extend(alias_diagnostics)
    decimal_precision_scales.update(
        _propagate_decimal_precision_scale_aliases(
            type_resolutions=type_resolutions,
            decimal_precision_scales=decimal_precision_scales,
        )
    )
    diagnostics.extend(check_callable_signatures(script, type_expansions))
    diagnostics.extend(check_shape_structures(script))
    diagnostics.extend(check_field_derive_cycles(script))
    source_row_schemas, source_diagnostics = check_sources(
        script,
        mode=mode,
        type_symbols=type_symbols,
        type_resolutions=type_resolutions,
        type_nullability=type_nullability,
    )
    diagnostics.extend(source_diagnostics)
    if not single_file:
        source_row_schemas = {
            source: _enum_alias_fields_as_enums(schema, type_expansions)
            for source, schema in source_row_schemas.items()
        }
    from_resolutions, relation_diagnostics = resolve_relation_inputs(
        script,
        relation_symbols,
    )
    diagnostics.extend(relation_diagnostics)
    if single_file:
        structures, join_resolutions, join_diagnostics = build_join_structures(
            script,
            relation_symbols=relation_symbols,
            relationships=relationships,
            source_row_schemas=source_row_schemas,
            type_expansions=type_expansions,
        )
        diagnostics.extend(join_diagnostics)
    else:
        structures = {}
        join_resolutions = None
        diagnostics.extend(check_join_references(script, relation_symbols))
    cyclic_relations, cycle_diagnostics = check_relation_cycles(
        script,
        from_resolutions,
        join_resolutions=join_resolutions,
    )
    diagnostics.extend(cycle_diagnostics)
    structures = {
        definition: structure
        for definition, structure in structures.items()
        if definition not in cyclic_relations
    }
    (
        relation_row_schemas,
        schema_diagnostics,
        relation_value_types,
        relation_expression_diagnostics,
        let_scopes,
        window_expression_analyses,
        named_window_namespaces,
    ) = _analyze_relation_schema_expressions(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        type_expansions=type_expansions,
        single_file=single_file,
        join_structures=structures,
    )
    diagnostics.extend(schema_diagnostics)
    diagnostics.extend(
        check_relationship_conditions(
            script,
            relationships,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            type_expansions=type_expansions,
        )
    )
    expression_value_types, expression_diagnostics = type_shape_predicates(
        script,
        type_resolutions=type_resolutions,
        type_expansions=type_expansions,
        type_nullability=type_nullability,
    )
    connector_value_types, connector_expression_diagnostics = (
        type_source_connector_arguments(script)
    )
    expression_value_types.update(connector_value_types)
    expression_diagnostics.extend(connector_expression_diagnostics)
    field_derive_value_types, field_derive_diagnostics = type_shape_field_derives(
        script,
        type_expansions=type_expansions,
        type_nullability=type_nullability,
    )
    expression_value_types.update(field_derive_value_types)
    expression_diagnostics.extend(field_derive_diagnostics)
    callable_value_types, callable_expression_diagnostics = type_callable_bodies(
        script,
        type_expansions=type_expansions,
        type_nullability=type_nullability,
    )
    expression_value_types.update(callable_value_types)
    expression_diagnostics.extend(callable_expression_diagnostics)
    expression_value_types.update(relation_value_types)
    expression_diagnostics.extend(relation_expression_diagnostics)
    diagnostics.extend(expression_diagnostics)
    diagnostics.extend(check_relation_limits(script))
    connector_diagnostics = check_source_connectors(script, expression_value_types)
    diagnostics.extend(connector_diagnostics)
    if single_file:
        diagnostics.extend(
            check_table_names(
                script, (*connector_expression_diagnostics, *connector_diagnostics)
            )
        )
    joined_inputs = (
        joined_input_rows(
            script.definitions,
            structures,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        if single_file
        else None
    )
    relation_let_expressions = _relation_let_expressions_for_satisfying(let_scopes)
    result_predicates, satisfying_diagnostics = check_satisfying_clauses(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_expressions=relation_let_expressions,
        relation_let_value_types={
            definition: scope.value_types for definition, scope in let_scopes.items()
        },
        type_expansions=type_expansions,
        record_unknown=True,
        projection_value_types=expression_value_types,
        joined_inputs=joined_inputs,
    )
    diagnostics.extend(satisfying_diagnostics)
    diagnostics.extend(
        check_callable_bodies(
            script,
            type_expansions=type_expansions,
            expression_value_types=expression_value_types,
        )
    )
    diagnostics.extend(
        check_field_derives(
            script,
            type_expansions=type_expansions,
            expression_value_types=expression_value_types,
        )
    )
    decimal_expression_precision_scales = _decimal_expression_precision_scales(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        expression_value_types=expression_value_types,
        decimal_precision_scales=decimal_precision_scales,
        joined_inputs=joined_inputs,
    )

    checks = None
    if single_file:
        checks = check_join_semantics(
            script,
            structures,
            relation_symbols=relation_symbols,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            expression_value_types=expression_value_types,
            type_expansions=type_expansions,
        )
        diagnostics.extend(checks.diagnostics)
        for definition, info in checks.facts.items():
            diagnostics.extend(
                join_fanout_diagnostics(
                    definition,
                    info,
                    type_symbols=type_symbols,
                    source_row_schemas=source_row_schemas,
                    let_expressions=relation_let_expressions.get(definition, {}),
                )
            )

    diagnostics.extend(
        diagnostic
        for definition in script.definitions
        for diagnostic in syntax_diagnostics(definition, allow_joins=single_file)
    )
    return SemanticResult(
        script=script,
        model=SemanticModel(
            mode=mode,
            type_symbols=type_symbols,
            callable_symbols=callable_symbols,
            relation_symbols=relation_symbols,
            type_resolutions=type_resolutions,
            type_expansions=type_expansions,
            type_nullability=type_nullability,
            decimal_precision_scales=decimal_precision_scales,
            decimal_expression_precision_scales=decimal_expression_precision_scales,
            source_row_schemas=source_row_schemas,
            from_resolutions=from_resolutions,
            relation_row_schemas=relation_row_schemas,
            expression_value_types=expression_value_types,
            window_expression_analyses=window_expression_analyses,
            named_window_namespaces=named_window_namespaces,
            result_predicates=result_predicates,
            let_scopes=let_scopes,
            relation_joins={} if checks is None else checks.facts,
            relationships=relationships,
        ),
        diagnostics=tuple(
            sorted(
                join_post_pass(diagnostics, checks)
                if checks is not None
                else _without_relations_only_projects_type(script, diagnostics),
                key=_diagnostic_order,
            )
        ),
    )


def _without_relations_only_projects_type(
    script: Script,
    diagnostics: list[Diagnostic],
) -> list[Diagnostic]:
    """Drop the diagnostics of the relations a project types and this cannot.

    This analysis has no JOIN binding fields, no computed `let:` group key and
    no aggregate of a `let:` name in a grouped relation, so the diagnostics
    inside a table or query that reads a field of one of its JOIN bindings or
    reads a `let:` name in a GROUP BY key or an aggregate of a relation with
    GROUP BY, or that reads such a relation with FROM or a JOIN, directly or
    through others, are dropped. So is the PIE-S2315 of a `min` or `max` whose
    argument is a `let:` name in a relation without GROUP BY, which only
    single-file SQL refuses.
    """

    relations = [
        definition
        for definition in script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    ]
    readers: dict[str, list[DerivedRelation]] = {}
    for relation in relations:
        for name in {
            relation.from_clause.source_name,
            *(clause.target_relation_name for clause in relation.join_clauses),
        }:
            readers.setdefault(name, []).append(relation)
    pending = [
        relation
        for relation in relations
        if _reads_join_binding(relation) or _groups_by_let(relation)
    ]
    dropped: dict[int, Span] = {}
    while pending:
        relation = pending.pop()
        if id(relation) not in dropped:
            dropped[id(relation)] = relation.span
            pending.extend(readers.get(relation.name, ()))
    # The dropped spans by path and line, so each diagnostic is one lookup.
    lines: dict[tuple[str | None, int], list[Span]] = {}
    for span in dropped.values():
        for line in range(span.line, span.end_line + 1):
            lines.setdefault((span.path, line), []).append(span)
    extrema = {
        (span.path, span.line, span.column)
        for relation in relations
        for span in _let_extrema(relation)
    }
    return [
        diagnostic
        for diagnostic in diagnostics
        if not any(
            _within(diagnostic.location, span)
            for span in lines.get(
                (diagnostic.location.path, diagnostic.location.line), ()
            )
        )
        and not (
            diagnostic.code == "PIE-S2315"
            and (
                diagnostic.location.path,
                diagnostic.location.line,
                diagnostic.location.column,
            )
            in extrema
        )
    ]


def _reads_join_binding(relation: DerivedRelation) -> bool:
    bindings = {clause.target_binding_name for clause in relation.join_clauses}
    pending: list[object] = [relation] if bindings else []
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(value)
        elif type(value) is DottedNameExpr:
            if value.parts[0] in bindings:
                return True
        elif isinstance(value, Node):
            pending.extend(getattr(value, field.name) for field in fields(value))
    return False


def _groups_by_let(relation: DerivedRelation) -> bool:
    if relation.let_clause is None or relation.group_by_clause is None:
        return False
    names = {binding.name for binding in relation.let_clause.bindings}
    # Each value with whether it lies in a GROUP BY key or an aggregate.
    pending: list[tuple[object, bool]] = [(relation, False)]
    while pending:
        value, grouped = pending.pop()
        if type(value) is tuple:
            pending.extend((item, grouped) for item in value)
        elif type(value) is NameExpr:
            if grouped and value.name in names:
                return True
        elif isinstance(value, Node):
            grouped = (
                grouped
                or type(value) is GroupByClause
                or (isinstance(value, Expression) and is_semantic_aggregate_call(value))
            )
            pending.extend(
                (getattr(value, field.name), grouped) for field in fields(value)
            )
    return False


def _let_extrema(relation: DerivedRelation) -> list[Span]:
    """The spans of the `min` and `max` calls whose argument is a `let:` name
    in a relation without GROUP BY."""

    if relation.let_clause is None or relation.group_by_clause is not None:
        return []
    names = {binding.name for binding in relation.let_clause.bindings}
    spans: list[Span] = []
    pending: list[object] = [relation]
    while pending:
        value = pending.pop()
        if type(value) is tuple:
            pending.extend(value)
        elif isinstance(value, Node):
            if (
                type(value) is CallExpr
                and semantic_aggregate_call_name(value)
                in {MIN_AGGREGATE_NAME, MAX_AGGREGATE_NAME}
                and len(value.arguments) == 1
                and type(value.arguments[0]) is NameExpr
                and value.arguments[0].name in names
            ):
                spans.append(value.span)
            pending.extend(getattr(value, field.name) for field in fields(value))
    return spans


def _within(location: SourceLocation, span: Span) -> bool:
    start = (span.line, span.column)
    end = (span.end_line, span.end_column)
    return (
        location.path == span.path and start <= (location.line, location.column) < end
    )


RelationDefinition = SourceDef | TableDef | QueryDef
DerivedRelation = TableDef | QueryDef


def _decimal_expression_precision_scales(
    script: Script,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
    joined_inputs: Mapping[DerivedRelation, RowSchema] | None = None,
) -> dict[Expression, DecimalPrecisionScale]:
    """Collect private Decimal precision facts for safe direct field leaves."""

    facts: dict[Expression, DecimalPrecisionScale] = {}
    for definition in script.definitions:
        if not isinstance(definition, (TableDef, QueryDef)):
            continue
        input_schema = _relation_input_schema(
            definition,
            from_resolutions=from_resolutions,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
            joined_inputs=joined_inputs,
        )
        if definition.let_clause is not None:
            for binding in definition.let_clause.bindings:
                _collect_decimal_expression_precision_scales(
                    binding.expression,
                    input_schema=input_schema,
                    field_qualifier=definition.from_clause.source_name,
                    expression_value_types=expression_value_types,
                    decimal_precision_scales=decimal_precision_scales,
                    facts=facts,
                )
        if definition.where_clause is not None:
            _collect_decimal_expression_precision_scales(
                definition.where_clause.expression,
                input_schema=input_schema,
                field_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                decimal_precision_scales=decimal_precision_scales,
                facts=facts,
            )
        for item in definition.select_items:
            _collect_decimal_expression_precision_scales(
                item.expression,
                input_schema=input_schema,
                field_qualifier=definition.from_clause.source_name,
                expression_value_types=expression_value_types,
                decimal_precision_scales=decimal_precision_scales,
                facts=facts,
            )
        if definition.order_by_clause is not None:
            for item in definition.order_by_clause.items:
                _collect_decimal_expression_precision_scales(
                    item.expression,
                    input_schema=input_schema,
                    field_qualifier=definition.from_clause.source_name,
                    expression_value_types=expression_value_types,
                    decimal_precision_scales=decimal_precision_scales,
                    facts=facts,
                )
    return facts


def _relation_input_schema(
    definition: DerivedRelation,
    *,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    relation_row_schemas: Mapping[DerivedRelation, RowSchema],
    joined_inputs: Mapping[DerivedRelation, RowSchema] | None = None,
) -> RowSchema:
    """Return a relation input schema for private post-analysis fact collection."""

    if joined_inputs is not None and definition in joined_inputs:
        return joined_inputs[definition]
    target = from_resolutions.get(definition.from_clause)
    if isinstance(target, SourceDef):
        return source_row_schemas[target]
    if isinstance(target, (TableDef, QueryDef)):
        return relation_row_schemas[target]
    return RowSchema(is_unknown=True)


def _collect_decimal_expression_precision_scales(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
    facts: dict[Expression, DecimalPrecisionScale],
) -> None:
    """Walk expression children while assigning facts only to direct fields."""

    direct_fact = _direct_decimal_expression_precision_scale(
        expression,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
        expression_value_types=expression_value_types,
        decimal_precision_scales=decimal_precision_scales,
    )
    if direct_fact is not None:
        facts[expression] = direct_fact
        return

    for child in _expression_children(expression):
        _collect_decimal_expression_precision_scales(
            child,
            input_schema=input_schema,
            field_qualifier=field_qualifier,
            expression_value_types=expression_value_types,
            decimal_precision_scales=decimal_precision_scales,
            facts=facts,
        )


def _direct_decimal_expression_precision_scale(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
    expression_value_types: Mapping[Expression, ValueType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> DecimalPrecisionScale | None:
    """Return a Decimal precision fact only for direct Decimal field references."""

    row_field = _direct_expression_row_field(
        expression,
        input_schema=input_schema,
        field_qualifier=field_qualifier,
    )
    if row_field is None or row_field.definition is None:
        return None

    expression_type = expression_value_types.get(expression)
    if expression_type is None or expression_type.kind is not ValueTypeKind.KNOWN:
        return None
    if (
        expression_type.resolved_type.kind is not TypeKind.BUILTIN
        or expression_type.resolved_type.name != "Decimal"
    ):
        return None

    type_expr = row_field.definition.type_expr
    if type_expr.name != "Decimal":
        return None
    return decimal_precision_scales.get(type_expr)


def _direct_expression_row_field(
    expression: Expression,
    *,
    input_schema: RowSchema,
    field_qualifier: str,
) -> RowField | None:
    if input_schema.is_unknown:
        return None
    if isinstance(expression, NameExpr):
        return bare_field(input_schema, expression.name)
    if isinstance(expression, DottedNameExpr):
        return qualified_field(input_schema, expression.parts, field_qualifier)
    return None


def _expression_children(expression: Expression) -> tuple[Expression, ...]:
    if isinstance(expression, CallExpr):
        return expression.arguments
    if isinstance(expression, UnaryExpr):
        return (expression.operand,)
    if isinstance(expression, ConditionalExpr):
        return (expression.when_true, expression.condition, expression.when_false)
    if isinstance(expression, MembershipExpr):
        return (expression.value, *expression.options)
    if isinstance(expression, CastExpr):
        return (expression.value,)
    if isinstance(expression, BinaryExpr):
        return (expression.left, expression.right)
    if isinstance(expression, ComparisonExpr):
        return (expression.left, expression.right)
    if isinstance(expression, BetweenExpr):
        return (expression.value, expression.lower, expression.upper)
    if isinstance(expression, IsNullExpr):
        return (expression.value,)
    if isinstance(expression, (LiteralExpr, NameExpr, DottedNameExpr, WindowExpr)):
        return ()
    raise AssertionError(f"Unsupported expression: {type(expression).__name__}")


def _analyze_relation_schema_expressions(
    script: Script,
    *,
    mode: CheckMode,
    from_resolutions: Mapping[FromClause, RelationDefinition],
    source_row_schemas: Mapping[SourceDef, RowSchema],
    cyclic_relations: set[DerivedRelation],
    type_expansions: Mapping[TypeExpr, ResolvedType],
    single_file: bool,
    join_structures: Mapping[DerivedRelation, JoinStructure],
) -> tuple[
    dict[DerivedRelation, RowSchema],
    list[Diagnostic],
    dict[Expression, ValueType],
    list[Diagnostic],
    dict[DerivedRelation, LetScopeSemanticInfo],
    dict[WindowExpr, WindowExpressionAnalysis],
    dict[DerivedRelation, ResolvedNamedWindowNamespace],
]:
    """Refine relation schemas from computed projection expression types."""

    def build_joined_input(
        definition: DerivedRelation,
        schema_of: Callable[[RelationDefinition], RowSchema],
    ) -> RowSchema | None:
        structure = join_structures.get(definition)
        return None if structure is None else join_input_row(structure, schema_of)

    joined_input_builder: JoinedInputBuilder | None = (
        build_joined_input if single_file else None
    )
    reserved_names = (
        {
            definition: join_reserved_let_names(definition)
            for definition in script.definitions
            if isinstance(definition, (TableDef, QueryDef)) and definition.join_clauses
        }
        if single_file
        else None
    )
    relation_row_schemas, _ = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        joined_input_builder=joined_input_builder,
        type_expansions=type_expansions,
    )
    derived_relation_count = sum(
        isinstance(definition, (TableDef, QueryDef))
        for definition in script.definitions
    )
    iteration_limit = derived_relation_count + 1
    stabilized = False

    # Each pass types every relation against the previous pass's schemas, then
    # projects every relation after the relation it reads. A pass redoes only a
    # relation whose input changed, so a chain of tables that settles one level
    # per pass costs linear rather than quadratic time, with the same passes
    # and schemas as redoing every relation. Expressions belong to one relation
    # each, so its value types replace the ones it had.
    ordered = list(relation_row_schemas)
    positions = {definition: index for index, definition in enumerate(ordered)}
    readers: dict[DerivedRelation, list[DerivedRelation]] = {}
    for definition in ordered:
        targets = [from_resolutions.get(definition.from_clause)]
        if definition in join_structures:
            targets.extend(
                item.relation for item in join_structures[definition].inputs[1:]
            )
        for target in dict.fromkeys(targets):
            if isinstance(target, (TableDef, QueryDef)):
                readers.setdefault(target, []).append(definition)
    temporary_value_types: dict[Expression, ValueType] = {}
    typed: dict[DerivedRelation, tuple[Expression, ...]] = {}
    retyped = ordered
    for _ in range(iteration_limit):
        for definition in dict.fromkeys(retyped):
            joined_inputs = (
                joined_input_rows(
                    (definition,),
                    join_structures,
                    source_row_schemas=source_row_schemas,
                    relation_row_schemas=relation_row_schemas,
                )
                if single_file
                else None
            )
            for expression in typed.pop(definition, ()):
                del temporary_value_types[expression]
            (
                temporary_let_scopes,
                temporary_let_value_types,
                temporary_let_diagnostics,
            ) = analyze_relation_let_bindings(
                (definition,),
                from_resolutions=from_resolutions,
                source_row_schemas=source_row_schemas,
                relation_row_schemas=relation_row_schemas,
                allow_unaliased_selected_let_outputs=not single_file,
                joined_inputs=joined_inputs,
                reserved_let_names=reserved_names,
                type_expansions=type_expansions,
            )
            relation_value_types, _, _, _ = type_relation_expressions(
                replace(script, definitions=(definition,)),
                from_resolutions=from_resolutions,
                source_row_schemas=source_row_schemas,
                relation_row_schemas=relation_row_schemas,
                relation_let_value_types={
                    relation: scope.value_types
                    for relation, scope in temporary_let_scopes.items()
                },
                type_expansions=type_expansions,
                let_diagnostics=temporary_let_diagnostics,
                single_file=single_file,
                joined_inputs=joined_inputs,
                let_part_types=temporary_let_value_types,
            )
            relation_value_types.update(temporary_let_value_types)
            typed[definition] = tuple(relation_value_types)
            temporary_value_types.update(relation_value_types)
        pending = sorted({positions[definition] for definition in retyped})
        queued = set(pending)
        retyped = []
        stabilized = True
        while pending:
            definition = ordered[heappop(pending)]
            input_schema = (
                _relation_input_schema(
                    definition,
                    from_resolutions=from_resolutions,
                    source_row_schemas=source_row_schemas,
                    relation_row_schemas=relation_row_schemas,
                    joined_inputs=(
                        joined_input_rows(
                            (definition,),
                            join_structures,
                            source_row_schemas=source_row_schemas,
                            relation_row_schemas=relation_row_schemas,
                        )
                        if single_file
                        else None
                    ),
                )
                if reads_relation_input(
                    definition,
                    cyclic_relations,
                    joined_input_builder=joined_input_builder,
                )
                else RowSchema(is_unknown=True)
            )
            schema = project_relation_schema(
                definition,
                input_schema,
                mode=mode,
                expression_value_types=temporary_value_types,
                joined_input_builder=joined_input_builder,
                type_expansions=type_expansions,
            )
            previous = relation_row_schemas[definition]
            if schema == previous:
                continue
            relation_row_schemas[definition] = schema
            if _schema_fingerprint(schema) != _schema_fingerprint(previous):
                stabilized = False
            for reader in readers.get(definition, ()):
                retyped.append(reader)
                position = positions[reader]
                if (
                    reads_relation_input(
                        reader,
                        cyclic_relations,
                        joined_input_builder=joined_input_builder,
                    )
                    and position not in queued
                ):
                    queued.add(position)
                    heappush(pending, position)
        if stabilized:
            break

    joined_inputs = (
        joined_input_rows(
            script.definitions,
            join_structures,
            source_row_schemas=source_row_schemas,
            relation_row_schemas=relation_row_schemas,
        )
        if single_file
        else None
    )
    let_scopes, let_value_types, let_diagnostics = analyze_relation_let_bindings(
        script.definitions,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        allow_unaliased_selected_let_outputs=not single_file,
        joined_inputs=joined_inputs,
        reserved_let_names=reserved_names,
        type_expansions=type_expansions,
    )
    (
        relation_value_types,
        relation_expression_diagnostics,
        window_expression_analyses,
        named_window_namespaces,
    ) = type_relation_expressions(
        script,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_let_value_types={
            definition: scope.value_types for definition, scope in let_scopes.items()
        },
        type_expansions=type_expansions,
        let_diagnostics=let_diagnostics,
        single_file=single_file,
        joined_inputs=joined_inputs,
        let_part_types=let_value_types,
    )
    relation_value_types.update(let_value_types)
    relation_expression_diagnostics.extend(let_diagnostics)
    expansion_diagnostics = [
        diagnostic
        for definition, scope in let_scopes.items()
        if single_file
        for diagnostic in let_expansion_diagnostics(definition, scope.value_types)
    ]
    # A key over the let inlining limit already has that error: no PIE-S2380.
    over_limit = {diagnostic.location for diagnostic in expansion_diagnostics}
    relation_expression_diagnostics[:] = [
        diagnostic
        for diagnostic in relation_expression_diagnostics
        if not (diagnostic.code == "PIE-S2380" and diagnostic.location in over_limit)
    ]
    relation_expression_diagnostics.extend(expansion_diagnostics)
    final_schemas, schema_diagnostics = propagate_relation_schemas(
        script,
        mode=mode,
        from_resolutions=from_resolutions,
        source_row_schemas=source_row_schemas,
        cyclic_relations=cyclic_relations,
        joined_input_builder=joined_input_builder,
        expression_value_types=relation_value_types,
        type_expansions=type_expansions,
        reported_errors=frozenset(relation_expression_diagnostics),
    )
    if stabilized:
        relation_row_schemas = final_schemas

    return (
        relation_row_schemas,
        schema_diagnostics,
        relation_value_types,
        relation_expression_diagnostics,
        let_scopes,
        window_expression_analyses,
        named_window_namespaces,
    )


def _enum_alias_fields_as_enums(
    schema: RowSchema,
    type_expansions: Mapping[TypeExpr, ResolvedType],
) -> RowSchema:
    """Type each field of an alias of an enum as that enum, as a project does."""

    fields: dict[str, RowField] = {}
    for name, row_field in schema.fields.items():
        definition = row_field.resolved_type.definition
        expanded = (
            type_expansions.get(definition.base)
            if row_field.resolved_type.kind is TypeKind.TYPE_ALIAS
            and isinstance(definition, TypeDef)
            else None
        )
        fields[name] = (
            replace(row_field, resolved_type=expanded)
            if expanded is not None and expanded.kind is TypeKind.ENUM
            else row_field
        )
    return replace(schema, fields=fields)


def _schema_fingerprint(
    schema: RowSchema,
) -> tuple[bool, tuple[tuple[str, str, TypeKind, EffectiveNullability], ...]]:
    """Compare relation schemas by stable semantic facts instead of identity."""

    return (
        schema.is_unknown,
        tuple(
            (
                name,
                field.resolved_type.name,
                field.resolved_type.kind,
                field.nullability,
            )
            for name, field in schema.fields.items()
        ),
    )


def _relation_let_expressions_for_satisfying(
    let_scopes: Mapping[DerivedRelation, LetScopeSemanticInfo],
) -> dict[DerivedRelation, dict[str, Expression]]:
    """Return admitted relation-local let expressions for satisfying checks."""

    return {
        definition: {
            binding.name: binding.expression
            for binding in scope.bindings
            if binding.name in scope.value_types
        }
        for definition, scope in let_scopes.items()
    }


def _mode_from_script(script: Script) -> CheckMode:
    """Select the declared mode or the checked default."""

    if script.header is None or script.header.mode is None:
        return CheckMode.CHECKED
    return CheckMode(script.header.mode)


def _namespace_for(
    definition: Definition,
    *,
    type_symbols: dict[str, Definition],
    callable_symbols: dict[str, Definition],
    relation_symbols: dict[str, Definition],
) -> tuple[str, dict[str, Definition]]:
    """Return the namespace assigned to a top-level definition."""

    if isinstance(definition, (TypeDef, EnumDef, ShapeDef)):
        return "type", type_symbols
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return "callable", callable_symbols
    if isinstance(definition, (SourceDef, TableDef, QueryDef, SetRelationDef)):
        return "relation", relation_symbols
    raise AssertionError(f"Unsupported definition: {type(definition).__name__}")


def _duplicate_diagnostic(
    definition: Definition,
    namespace_name: str,
) -> Diagnostic:
    """Report a duplicate at the later definition's complete source span."""

    span = definition.span
    return Diagnostic(
        code="PIE-S2001",
        severity=Severity.ERROR,
        message=(
            f"Duplicate symbol name in {namespace_name} namespace: {definition.name}"
        ),
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _duplicate_enum_member_diagnostics(definition: EnumDef) -> list[Diagnostic]:
    """Report each repeated member name once at the enum declaration.

    Members carry no spans of their own.
    """

    seen: set[str] = set()
    repeated: list[str] = []
    for member in definition.members:
        if member in seen and member not in repeated:
            repeated.append(member)
        seen.add(member)
    span = definition.span
    return [
        Diagnostic(
            code="PIE-S2001",
            severity=Severity.ERROR,
            message=f"Duplicate member name in enum {definition.name}: {member}",
            location=SourceLocation(
                path=span.path,
                line=span.line,
                column=span.column,
                end_line=span.end_line,
                end_column=span.end_column,
            ),
        )
        for member in repeated
    ]


def _iter_type_expressions(script: Script) -> Iterator[TypeExpr]:
    """Yield supported type expressions in source order."""

    for definition in script.definitions:
        if isinstance(definition, TypeDef):
            yield definition.base
        elif isinstance(definition, (ConstraintDef, DeriveDef)):
            for parameter in definition.parameters:
                yield parameter.type
            yield definition.return_type
        elif isinstance(definition, ShapeDef):
            for field in definition.fields:
                yield field.type_expr


def _iter_cast_target_type_expressions(script: Script) -> Iterator[TypeExpr]:
    """Yield cast targets without applying declaration-nullability policy."""

    for definition in script.definitions:
        if isinstance(definition, TypeDef):
            yield from _cast_targets_in_type_arguments(definition.base)
            for ensure in definition.ensures:
                yield from _cast_targets_in_expression(ensure.expression)
        elif isinstance(definition, (ConstraintDef, DeriveDef)):
            for parameter in definition.parameters:
                yield from _cast_targets_in_type_arguments(parameter.type)
            yield from _cast_targets_in_type_arguments(definition.return_type)
            yield from _cast_targets_in_expression(definition.body)
        elif isinstance(definition, ShapeDef):
            for item in definition.items:
                if isinstance(item, FieldDef):
                    yield from _cast_targets_in_type_arguments(item.type_expr)
                    if item.derive_expression is not None:
                        yield from _cast_targets_in_expression(item.derive_expression)
                    for ensure in item.ensure_clauses:
                        yield from _cast_targets_in_expression(ensure.expression)
                elif isinstance(item, CheckDef):
                    yield from _cast_targets_in_expression(item.expression)
                elif isinstance(item, IndexDef) and item.predicate is not None:
                    yield from _cast_targets_in_expression(item.predicate)
        elif isinstance(definition, SourceDef):
            yield from _cast_targets_in_expression(definition.connector)
        elif isinstance(definition, (TableDef, QueryDef)):
            yield from _relation_cast_targets(definition)
    for relationship in script.relationships:
        if relationship.base_match is not None:
            yield from _cast_targets_in_expression(relationship.base_match.expression)


def _cast_targets_in_type_arguments(type_expr: TypeExpr) -> Iterator[TypeExpr]:
    """Yield casts written in one declaration type's value arguments."""

    for argument in type_expr.arguments:
        yield from _cast_targets_in_expression(argument.value)


def _record_type_expression(
    type_expr: TypeExpr,
    *,
    type_symbols: dict[str, Definition],
    type_resolutions: dict[TypeExpr, ResolvedType],
    type_nullability: dict[TypeExpr, EffectiveNullability],
    decimal_precision_scales: dict[TypeExpr, DecimalPrecisionScale],
    diagnostics: list[Diagnostic],
    mode: CheckMode,
    report_implicit_nullability: bool,
) -> None:
    """Resolve one declared or cast-target type without weakening validation."""

    resolved_type = _resolve_type(type_expr, type_symbols)
    type_resolutions[type_expr] = resolved_type
    type_nullability[type_expr] = _effective_nullability(type_expr)
    if resolved_type.kind is TypeKind.UNKNOWN:
        diagnostics.append(_unknown_type_diagnostic(type_expr))
    decimal_precision_scale, decimal_diagnostic = _decimal_precision_scale_fact(
        type_expr
    )
    if decimal_precision_scale is not None:
        decimal_precision_scales[type_expr] = decimal_precision_scale
    if decimal_diagnostic is not None:
        diagnostics.append(decimal_diagnostic)
    if report_implicit_nullability:
        implicit_diagnostic = _implicit_nullability_diagnostic(type_expr, mode)
        if implicit_diagnostic is not None:
            diagnostics.append(implicit_diagnostic)


def _relation_cast_targets(definition: TableDef | QueryDef) -> Iterator[TypeExpr]:
    """Yield casts from one relation body in authored clause order."""

    if definition.let_clause is not None:
        for binding in definition.let_clause.bindings:
            yield from _cast_targets_in_expression(binding.expression)
    if definition.where_clause is not None:
        yield from _cast_targets_in_expression(definition.where_clause.expression)
    if definition.group_by_clause is not None:
        for item in definition.group_by_clause.items:
            yield from _cast_targets_in_expression(item.key)
    for item in definition.select_items:
        yield from _cast_targets_in_expression(item.expression)
    if definition.satisfying_clause is not None:
        yield from _cast_targets_in_expression(definition.satisfying_clause.expression)
    if definition.qualify_clause is not None:
        yield from _cast_targets_in_expression(definition.qualify_clause.expression)
    if definition.order_by_clause is not None:
        for item in definition.order_by_clause.items:
            yield from _cast_targets_in_expression(item.expression)
    if definition.limit_clause is not None:
        yield from _cast_targets_in_expression(definition.limit_clause.expression)
    for join in definition.join_clauses:
        if join.on_clause is not None:
            yield from _cast_targets_in_expression(join.on_clause.expression)
    for named_window in definition.named_windows:
        if named_window.spec is not None:
            yield from _window_spec_cast_targets(named_window.spec)


def _cast_targets_in_expression(expression: Expression) -> Iterator[TypeExpr]:
    """Yield every cast target while preserving expression source order."""

    if isinstance(expression, CastExpr):
        yield from _cast_targets_in_expression(expression.value)
        yield expression.target
        return
    if isinstance(expression, WindowExpr):
        yield from _cast_targets_in_expression(expression.call)
        yield from _window_spec_cast_targets(expression.spec)
        return
    for child in _expression_children(expression):
        yield from _cast_targets_in_expression(child)


def _window_spec_cast_targets(spec: WindowSpec) -> Iterator[TypeExpr]:
    """Yield casts in a parsed window spec without widening its semantics."""

    for expression in spec.partition_by:
        yield from _cast_targets_in_expression(expression)
    for item in spec.order_by:
        yield from _cast_targets_in_expression(item.expression)
    frame = spec.frame
    for bound in (frame.start, frame.end):
        if bound is not None and bound.offset is not None:
            yield from _cast_targets_in_expression(bound.offset)


def _resolve_type(
    type_expr: TypeExpr,
    type_symbols: dict[str, Definition],
) -> ResolvedType:
    """Resolve one type name without alias expansion."""

    if type_expr.name in BUILTIN_TYPE_NAMES:
        return ResolvedType(name=type_expr.name, kind=TypeKind.BUILTIN)

    definition = type_symbols.get(type_expr.name)
    if isinstance(definition, TypeDef):
        kind = TypeKind.TYPE_ALIAS
    elif isinstance(definition, EnumDef):
        kind = TypeKind.ENUM
    elif isinstance(definition, ShapeDef):
        kind = TypeKind.SHAPE
    else:
        return ResolvedType(name=type_expr.name, kind=TypeKind.UNKNOWN)
    return ResolvedType(
        name=type_expr.name,
        kind=kind,
        definition=definition,
    )


def _decimal_precision_scale_fact(
    type_expr: TypeExpr,
) -> tuple[DecimalPrecisionScale | None, Diagnostic | None]:
    """Validate and return internal Decimal precision-scale facts."""

    if type_expr.name != "Decimal":
        return None, None

    arguments = type_expr.arguments
    if not arguments:
        return None, None

    if len(arguments) != 2 or any(argument.name is not None for argument in arguments):
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal precision-scale requires exactly two positional integer literal arguments",
            ),
        )

    precision = _integer_literal_value(arguments[0].value)
    scale = _integer_literal_value(arguments[1].value)
    if precision is None or scale is None:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal precision and scale must be integer literals",
            ),
        )

    if precision < 1 or precision > _DECIMAL_PRECISION_MAX:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                f"Decimal precision must be an integer from 1 to {_DECIMAL_PRECISION_MAX}",
            ),
        )

    if scale < 0 or scale > precision:
        return (
            None,
            _invalid_decimal_type_arguments_diagnostic(
                type_expr,
                "Decimal scale must be an integer from 0 to precision",
            ),
        )

    return DecimalPrecisionScale(precision=precision, scale=scale), None


def _propagate_decimal_precision_scale_aliases(
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> dict[TypeExpr, DecimalPrecisionScale]:
    """Copy Decimal precision-scale facts to safe alias-use type expressions."""

    propagated: dict[TypeExpr, DecimalPrecisionScale] = {}
    for type_expr, resolved_type in type_resolutions.items():
        if type_expr in decimal_precision_scales:
            continue
        if resolved_type.kind is not TypeKind.TYPE_ALIAS:
            continue
        fact = _decimal_precision_scale_for_alias_target(
            resolved_type,
            type_resolutions=type_resolutions,
            decimal_precision_scales=decimal_precision_scales,
        )
        if fact is not None:
            propagated[type_expr] = fact
    return propagated


def _decimal_precision_scale_for_alias_target(
    resolved_type: ResolvedType,
    *,
    type_resolutions: Mapping[TypeExpr, ResolvedType],
    decimal_precision_scales: Mapping[TypeExpr, DecimalPrecisionScale],
) -> DecimalPrecisionScale | None:
    """Resolve an alias target to existing Decimal precision-scale facts."""

    visited: set[TypeDef] = set()
    current = resolved_type.definition
    while isinstance(current, TypeDef) and current not in visited:
        visited.add(current)
        fact = decimal_precision_scales.get(current.base)
        if fact is not None:
            return fact
        direct = type_resolutions.get(current.base)
        if direct is None or direct.kind is not TypeKind.TYPE_ALIAS:
            return None
        current = direct.definition
    return None


def _integer_literal_value(expression: Expression) -> int | None:
    if isinstance(expression, LiteralExpr) and type(expression.value) is int:
        return expression.value
    return None


def _effective_nullability(type_expr: TypeExpr) -> EffectiveNullability:
    """Map parsed nullability syntax to the initial semantic state."""

    if type_expr.nullability is Nullability.NULLABLE:
        return EffectiveNullability.NULLABLE
    if type_expr.nullability is Nullability.NOT_NULL:
        return EffectiveNullability.NON_NULL
    return EffectiveNullability.UNKNOWN


def _unknown_type_diagnostic(type_expr: TypeExpr) -> Diagnostic:
    """Report an unresolved type name at its complete type-expression span."""

    return _type_diagnostic(
        type_expr,
        code="PIE-S2002",
        severity=Severity.ERROR,
        message=f"Unknown type: {type_expr.name}",
    )


def _invalid_decimal_type_arguments_diagnostic(
    type_expr: TypeExpr,
    message: str,
) -> Diagnostic:
    """Report invalid Decimal precision-scale arguments."""

    return _type_diagnostic(
        type_expr,
        code="PIE-S2004",
        severity=Severity.ERROR,
        message=message,
    )


def _implicit_nullability_diagnostic(
    type_expr: TypeExpr,
    mode: CheckMode,
) -> Diagnostic | None:
    """Apply the mode-sensitive policy for omitted nullability."""

    if type_expr.nullability is not Nullability.IMPLICIT or mode is CheckMode.LOOSE:
        return None
    severity = Severity.WARNING if mode is CheckMode.CHECKED else Severity.ERROR
    return _type_diagnostic(
        type_expr,
        code="PIE-S2005",
        severity=severity,
        message=(
            f"Implicit nullability for type {type_expr.name}; "
            "use `nullable` or `not null`"
        ),
    )


def _type_diagnostic(
    type_expr: TypeExpr,
    *,
    code: str,
    severity: Severity,
    message: str,
) -> Diagnostic:
    """Create a semantic diagnostic from a type-expression span."""

    span = type_expr.span
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _diagnostic_order(diagnostic: Diagnostic) -> tuple[str, int, int, str]:
    """Order diagnostics deterministically by source position and code."""

    location = diagnostic.location
    return (
        location.path or "",
        location.line,
        location.column,
        diagnostic.code,
    )
