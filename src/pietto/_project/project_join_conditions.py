"""Private pre-match condition facts; no JOIN output or operation admission."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from collections.abc import Mapping

from pietto._flat_relational_admission import availability_diagnostic
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_current_join_inputs import (
    ProjectCurrentPreMatchInputs,
    ProjectCurrentSourceField,
    ProjectCurrentNullingCause,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputCandidateKey,
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_relationship_uses import (
    ProjectJoinUseState,
    ProjectNonConcreteJoinUse,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
    ProjectRelationshipUseSet,
    _final_output,
    project_join_blocking_bindings,
    project_join_combination_error,
    project_join_mode,
    project_join_binding_visible,
    validate_project_join_input_bindings,
)
from pietto._project.existence_values import (
    ProjectAnyField,
    ProjectAnyValue,
    analyze_any_values,
    existence_uses_for_owner,
    validate_any_values,
)
from pietto._project.project_relationship_predicates import (
    ProjectRelationshipPredicateCatalog,
    ProjectRelationshipPredicateExpression,
    bind_project_relationship_predicates,
)
from pietto._project.row_expression_type_facts import (
    is_nested_relation_field,
    nested_value_diagnostic,
    project_row_field_to_semantic_value_type,
    scalar_field_reference_leaves,
)
from pietto.ast_nodes import (
    AuthoredJoinKind,
    BinaryExpr,
    CallExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    NameExpr,
    Span,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic import joins as semantic_joins
from pietto.semantic.aggregates import child_expressions, contains_semantic_aggregate
from pietto.semantic.expressions import (
    _UNKNOWN_VALUE_TYPE,
    infer_row_expression,
    is_unknown_function_call,
)
from pietto.semantic.model import (
    RelationshipCallInfo,
    RowSchema,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.predicate_checks import _check_bool_expression

__all__: tuple[str, ...] = ()


class ProjectRelationshipConditionScope(StrEnum):
    """Condition evaluation scopes reserved by the Phase-62 architecture."""

    RELATIONSHIP_BASE_MATCH = "relationship_base_match"
    JOIN_LOCAL_ON_REFINEMENT = "join_local_on_refinement"
    POST_JOIN_FILTER = "post_join_filter"
    GENERIC_JOIN_MATCH = "generic_join_match"


class ProjectRelationshipMinimumBound(StrEnum):
    ZERO_ALLOWED = "zero_allowed"
    AT_LEAST_ONE = "at_least_one"


class ProjectRelationshipMaximumBound(StrEnum):
    AT_MOST_ZERO = "at_most_zero"
    AT_MOST_ONE = "at_most_one"
    UNBOUNDED_BY_ONE = "unbounded_by_one"


def resolved_matching_keys(keys, matched_classes):
    """All exact target keys covered by the complete matched class vector."""
    matched = frozenset(matched_classes)
    return tuple(key for key in keys if frozenset(key.determinants) <= matched)


def _condition_conjuncts(expression: Expression) -> tuple[Expression, ...]:
    # Iterative, so an `and` chain of any length keeps its source order.
    conjuncts: list[Expression] = []
    pending = [expression]
    while pending:
        current = pending.pop()
        if type(current) is BinaryExpr and current.operator == "and":
            pending.extend((current.right, current.left))
        else:
            conjuncts.append(current)
    return tuple(conjuncts)


class ProjectJoinConditionState(StrEnum):
    READY = "ready"
    INVALID = "invalid"
    UNAVAILABLE = "unavailable"


class ProjectJoinReferenceState(StrEnum):
    RESOLVED = "resolved"
    UNKNOWN = "unknown"
    FORWARD = "forward"
    AMBIGUOUS = "ambiguous"
    UNAVAILABLE = "unavailable"


def _diagnostic(span: Span, message: str, *, code: str = "PIE-S2335") -> Diagnostic:
    return replace(availability_diagnostic(span, message), code=code)


def _exact_member(item: object, retained: tuple[object, ...]) -> bool:
    return any(item is member for member in retained)


type _InputRow = tuple[
    ProjectRelationBindingOccurrence,
    ProjectCurrentSourceField,
    ProjectRowFieldNullability,
    tuple[ProjectCurrentNullingCause, ...],
]


def _unknown_call_rows(
    expression: Expression, bindings: frozenset[str]
) -> tuple[NameExpr, ...]:
    """The bare-name arguments of unknown function calls in ``expression``
    that name a JOIN input, such as the rows of a call of a relationship the
    module does not declare: rows, not field references. Typing reports the
    call (PIE-S2103)."""

    rows: list[NameExpr] = []
    pending = [expression]
    while pending:
        node = pending.pop()
        if type(node) is CallExpr and is_unknown_function_call(node):
            rows.extend(
                argument
                for argument in node.arguments
                if type(argument) is NameExpr and argument.name in bindings
            )
        pending.extend(child_expressions(node))
    return tuple(rows)


def _input_rows(
    roots: ProjectRelationshipUseSet,
    ledger: ProjectRelationJoinUseLedger,
    use: ProjectNonConcreteJoinUse,
) -> tuple[tuple[_InputRow, ...], tuple[ProjectRelationBindingOccurrence, ...]]:
    """Replay only existing input nullability, without allocating prefix IR.

    A prior JOIN blocks the accumulated left input: no authored JOIN joins by
    itself, so its eventual shape/effective output is deliberately not guessed
    at this boundary.
    """
    position = use.identity.join_position
    bindings = ledger.bindings[: position + 2]
    inputs = tuple(
        (binding, output)
        for binding in bindings
        for output in (
            binding.output
            if binding.output is not None
            else _final_output(roots.relational, binding.target)
            if binding.state is ProjectJoinUseState.AMBIGUOUS
            and binding.target is not None
            else None,
        )
        if output is not None
    )
    return (
        tuple(
            (binding, item, item.effective_nullability, ())
            for binding, output in inputs
            if project_join_binding_visible(binding, ledger.uses[:position])
            for item in output.fields
        ),
        tuple(
            binding
            for index, binding in enumerate(bindings)
            if binding.state is not ProjectJoinUseState.CONCRETE
            or (position and index <= position)
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionEnvironment:
    root: ProjectJoinConditionSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    use: ProjectNonConcreteJoinUse = field(repr=False)
    inputs: ProjectCurrentPreMatchInputs | None = field(default=None, repr=False)
    bindings: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    source_candidates: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    blocked_bindings: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    fields: tuple[ProjectJoinConditionField, ...] = field(init=False)
    _rows: tuple[_InputRow, ...] = field(init=False, repr=False)
    predicate_expression: ProjectRelationshipPredicateExpression | None = field(
        init=False
    )
    expression: Expression | None = field(init=False)
    reference_leaves: tuple[NameExpr | DottedNameExpr, ...] = field(init=False)
    # Row arguments of unknown calls: no reference, typed unknown silently.
    unknown_call_rows: tuple[NameExpr, ...] = field(init=False)
    existence_values: tuple[ProjectAnyValue, ...] = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.root) is not ProjectJoinConditionSet
            or not _exact_member(self.ledger, self.root.uses.ledgers)
            or not _exact_member(self.use, self.ledger.uses)
        ):
            raise ValueError(
                "Condition environment requires exact root/ledger/use membership."
            )
        if self.inputs is None:
            rows, blocked = _input_rows(self.root.uses, self.ledger, self.use)
        else:
            if (
                type(self.inputs) is not ProjectCurrentPreMatchInputs
                or self.inputs.scope.uses is not self.root.uses
                or self.inputs.scope.ledger is not self.ledger
                or self.inputs.use is not self.use
            ):
                raise ValueError(
                    "Current condition inputs require exact use/root membership."
                )
            rows, blocked = self.inputs.rows, self.inputs.blocked_bindings
        object.__setattr__(
            self,
            "bindings",
            self.ledger.bindings[: self.use.identity.join_position + 2],
        )
        # A JOIN with `on` and a CROSS JOIN read the accumulated row rooted at
        # the FROM input; a JOIN without `on` has no source input to read.
        object.__setattr__(
            self,
            "source_candidates",
            (self.ledger.bindings[0],)
            if project_join_mode(self.use.clause) in {"M3", "M5"}
            else (),
        )
        object.__setattr__(self, "blocked_bindings", blocked)
        object.__setattr__(self, "_rows", rows)
        matches = tuple(
            item
            for item in self.root.predicate_expressions
            if item.owner is self.ledger.owner
            and item.context is self.use.clause.on_clause
        )
        if len(matches) > 1:
            raise ValueError(
                "JOIN ON requires one exact predicate expression occurrence."
            )
        normalized = matches[0] if matches else None
        object.__setattr__(self, "predicate_expression", normalized)
        object.__setattr__(
            self,
            "expression",
            normalized.expression
            if normalized is not None
            else (
                self.use.clause.on_clause.expression
                if self.use.clause.on_clause is not None
                else None
            ),
        )
        object.__setattr__(
            self,
            "fields",
            tuple(
                ProjectJoinConditionField(environment=self, position=i)
                for i in range(len(rows))
            ),
        )
        unknown_call_rows = (
            ()
            if self.expression is None
            else _unknown_call_rows(
                self.expression, frozenset(binding.name for binding in self.bindings)
            )
        )
        row_ids = {id(row) for row in unknown_call_rows}
        object.__setattr__(self, "unknown_call_rows", unknown_call_rows)
        object.__setattr__(
            self,
            "reference_leaves",
            ()
            if self.expression is None
            else tuple(
                leaf
                for leaf in (
                    normalized.scalar_references
                    if normalized is not None
                    else scalar_field_reference_leaves(self.expression)
                )
                if id(leaf) not in row_ids
            ),
        )
        on = self.use.clause.on_clause
        values = ()
        if on is not None and self.expression is not None:
            values = analyze_any_values(
                root=self.root.uses.semantic_result,
                owner=self.ledger.owner,
                authored=on.expression,
                expression=self.expression,
                normalized_any=() if normalized is None else normalized.any_expressions,
                retained_bindings=None
                if normalized is None
                else normalized.any_bindings,
                failed_relationship_calls=()
                if normalized is None
                else normalized.failed_calls,
                outer_fields=tuple(
                    ProjectAnyField(binding=item.binding, source_field=item)
                    for item in self.fields
                ),
                available=()
                if self.inputs is None
                else self.inputs.scope.available_entries,
            )
        object.__setattr__(self, "existence_values", values)
        if self.expression is not None:
            validate_any_values(self.ledger.owner, self.expression, values)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionField:
    environment: ProjectJoinConditionEnvironment = field(repr=False)
    position: int
    binding: ProjectRelationBindingOccurrence = field(init=False)
    input_field: ProjectCurrentSourceField = field(init=False)
    nullability: ProjectRowFieldNullability = field(init=False)
    null_extensions: tuple[ProjectCurrentNullingCause, ...] = field(init=False)
    value_type: ValueType = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.environment) is not ProjectJoinConditionEnvironment
            or type(self.position) is not int
            or not 0 <= self.position < len(self.environment._rows)
        ):
            raise ValueError("Pre-match field requires an exact input-field position.")
        binding, member, nullability, nulling = self.environment._rows[self.position]
        object.__setattr__(self, "binding", binding)
        object.__setattr__(self, "input_field", member)
        object.__setattr__(self, "nullability", nullability)
        object.__setattr__(self, "null_extensions", nulling)
        object.__setattr__(
            self,
            "value_type",
            project_row_field_to_semantic_value_type(member.evidence, nullability),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionReference:
    environment: ProjectJoinConditionEnvironment = field(repr=False)
    position: int
    expression: NameExpr | DottedNameExpr = field(init=False)
    binding_candidates: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    candidates: tuple[ProjectJoinConditionField, ...] = field(init=False)
    state: ProjectJoinReferenceState = field(init=False)
    target: ProjectJoinConditionField | None = field(init=False)

    def __post_init__(self) -> None:
        env = self.environment
        if type(env) is not ProjectJoinConditionEnvironment or env.expression is None:
            raise ValueError("Reference requires an exact authored ON environment.")
        leaves = env.reference_leaves
        if type(self.position) is not int or not 0 <= self.position < len(leaves):
            raise ValueError("Reference requires an exact expression occurrence.")
        expression = leaves[self.position]
        parts = expression.parts if isinstance(expression, DottedNameExpr) else ()
        qualified = bool(parts)
        name = (
            expression.name
            if isinstance(expression, NameExpr)
            else expression.parts[-1]
        )
        bindings = tuple(
            binding
            for binding in env.bindings
            if not qualified or (len(parts) == 2 and binding.name == parts[0])
        )
        candidates = tuple(
            item
            for item in env.fields
            if _exact_member(item.binding, bindings)
            and item.input_field.evidence.name == name
        )
        later = tuple(
            binding
            for binding in env.ledger.bindings[len(env.bindings) :]
            if len(parts) > 0 and binding.name == parts[0]
        )
        if (qualified and len(bindings) > 1) or len(candidates) > 1:
            state = ProjectJoinReferenceState.AMBIGUOUS
        elif any(_exact_member(binding, env.blocked_bindings) for binding in bindings):
            state = ProjectJoinReferenceState.UNAVAILABLE
        elif not candidates:
            state = (
                ProjectJoinReferenceState.FORWARD
                if later
                else ProjectJoinReferenceState.UNKNOWN
            )
        elif candidates[0].value_type.kind is ValueTypeKind.UNKNOWN:
            state = ProjectJoinReferenceState.UNAVAILABLE
        else:
            state = ProjectJoinReferenceState.RESOLVED
        object.__setattr__(self, "expression", expression)
        object.__setattr__(self, "binding_candidates", bindings or later)
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "state", state)
        object.__setattr__(
            self,
            "target",
            candidates[0]
            if len(candidates) == 1 and state is ProjectJoinReferenceState.RESOLVED
            else None,
        )


def _reference_diagnostic(reference: ProjectJoinConditionReference) -> Diagnostic:
    """An ON read without one target, named as a single file names it."""

    state = reference.state
    if state is ProjectJoinReferenceState.UNAVAILABLE:
        return _diagnostic(
            reference.expression.span, "JOIN ON reference is unavailable."
        )
    message = (
        f"JOIN ON reference is {state.value}: "
        f"{semantic_joins._text(reference.expression)}"
    )
    names = [
        f"{item.binding.name}.{item.input_field.evidence.name}"
        for item in reference.candidates
    ]
    if (
        state is ProjectJoinReferenceState.AMBIGUOUS
        and len(set(names)) == len(names) > 1
    ):
        message += f"; write {semantic_joins._or_names(names)}"
    return _diagnostic(reference.expression.span, message)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinCondition:
    root: ProjectJoinConditionSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    use: ProjectNonConcreteJoinUse = field(repr=False)
    inputs: ProjectCurrentPreMatchInputs | None = field(default=None, repr=False)
    environment: ProjectJoinConditionEnvironment = field(init=False)
    mode: str = field(init=False)
    scope: ProjectRelationshipConditionScope | None = field(init=False)
    expression: Expression | None = field(init=False)
    conjuncts: tuple[Expression, ...] = field(init=False)
    references: tuple[ProjectJoinConditionReference, ...] = field(init=False)
    mandatory_equalities: tuple[ProjectJoinConditionEquality, ...] = field(init=False)
    match_inputs: tuple[
        tuple[ProjectRelationBindingOccurrence, ProjectIROutputRelationalProperties],
        ...,
    ] = field(init=False)
    key_matches: tuple[ProjectJoinConditionKeyMatch, ...] = field(init=False)
    value_type: ValueType | None = field(init=False)
    value_types: Mapping[Expression, ValueType] = field(init=False, repr=False)
    state: ProjectJoinConditionState = field(init=False)
    ready: bool = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    # The diagnostics that only say a blocked input binding is unavailable.
    unavailable_diagnostics: tuple[Diagnostic, ...] = field(init=False, repr=False)
    null_rejections: tuple[ProjectJoinNullRejection, ...] = field(init=False)

    def __post_init__(self) -> None:
        env = ProjectJoinConditionEnvironment(
            root=self.root,
            ledger=self.ledger,
            use=self.use,
            inputs=self.inputs,
        )
        clause = self.use.clause
        mode = project_join_mode(clause)
        expression = env.expression
        scope = (
            ProjectRelationshipConditionScope.GENERIC_JOIN_MATCH
            if expression is not None
            else None
        )
        conjuncts = _condition_conjuncts(expression) if expression is not None else ()
        references = (
            tuple(
                ProjectJoinConditionReference(environment=env, position=i)
                for i in range(len(env.reference_leaves))
            )
            if expression is not None
            else ()
        )
        diagnostics: list[Diagnostic] = list(
            env.predicate_expression.diagnostics
            if env.predicate_expression is not None
            else ()
        )
        # A typed ANY restates its rejected calls' errors, which the record owns.
        owned = {id(item) for item in diagnostics}
        diagnostics.extend(
            item
            for value in env.existence_values
            for item in value.diagnostics
            if id(item) not in owned
        )
        combination = project_join_combination_error(clause)
        if combination is not None:
            diagnostics.append(_diagnostic(clause.span, combination, code="PIE-S2336"))
        # A JOIN with `on` and a CROSS JOIN read the FROM input; a JOIN without
        # `on` has no source input, since no relationship joins by itself.
        unavailable = bool(env.blocked_bindings) or len(env.source_candidates) != 1
        # A relationship call's row argument that names an input with no
        # relation to read only says that input is unavailable.
        blocked_names = {binding.name for binding in env.blocked_bindings}
        unavailable_diagnostics: list[Diagnostic] = [
            diagnostic
            for failure in (
                ()
                if env.predicate_expression is None
                else env.predicate_expression.failed_calls
            )
            for argument in failure.expression.arguments
            if type(argument) is NameExpr and argument.name in blocked_names
            for diagnostic in failure.diagnostics
            if diagnostic.message.startswith("Unavailable row argument for ")
            and diagnostic.location is not None
            and (diagnostic.location.line, diagnostic.location.column)
            == (argument.span.line, argument.span.column)
        ]
        # A JOIN without `on` that is INNER or LEFT keeps its own projection.
        if unavailable and (
            expression is not None
            or clause.kind not in {AuthoredJoinKind.INNER, AuthoredJoinKind.LEFT}
        ):
            if (
                not env.source_candidates
                and self.use.target_binding.output is not None
                and not project_join_blocking_bindings(self.ledger, self.use)
            ):
                diagnostics.append(
                    _diagnostic(clause.span, "JOIN source binding is unknown.")
                )
            else:
                unavailable_diagnostics.append(
                    _diagnostic(
                        clause.span,
                        "JOIN pre-match input or relationship authority is unavailable.",
                    )
                )
                diagnostics.append(unavailable_diagnostics[-1])
        value_types: dict[Expression, ValueType] = {
            expression: value_type
            for value in env.existence_values
            for expression, value_type in value.value_types.items()
        }
        value_types.update(dict.fromkeys(env.unknown_call_rows, _UNKNOWN_VALUE_TYPE))
        for reference in references:
            if len(reference.candidates) == 1 and is_nested_relation_field(
                reference.candidates[0].input_field.evidence
            ):
                # A collected relation has no value to compare (PIE-S2805).
                diagnostics.append(
                    _nested_reference_diagnostic(self, reference.expression)
                )
            elif reference.target is None:
                diagnostics.append(_reference_diagnostic(reference))
                if reference.state is ProjectJoinReferenceState.UNAVAILABLE:
                    unavailable_diagnostics.append(diagnostics[-1])
            else:
                value_types[reference.expression] = reference.target.value_type
        value_type = None
        if expression is not None:
            if contains_semantic_aggregate(expression):
                diagnostics.append(
                    _diagnostic(
                        expression.span,
                        "Aggregate expressions are unavailable in JOIN ON.",
                    )
                )
            elif all(reference.target is not None for reference in references):
                value_type = infer_row_expression(
                    expression,
                    RowSchema(),
                    value_types,
                    diagnostics,
                    report_unknown_name=True,
                    failed_relationship_calls=(
                        ()
                        if env.predicate_expression is None
                        else env.predicate_expression.failed_calls
                    ),
                )
                predicate_diagnostic = _check_bool_expression(
                    expression, context="JOIN ON", expression_value_types=value_types
                )
                if predicate_diagnostic is not None:
                    diagnostics.append(predicate_diagnostic)
                if value_type.kind is ValueTypeKind.UNKNOWN and not diagnostics:
                    # An `any(...)` whose input has no row says why, or
                    # follows a failure that is reported.
                    if any(
                        value.value_type.kind is not ValueTypeKind.KNOWN
                        and not value.diagnostics
                        for value in env.existence_values
                    ):
                        unavailable = True
                    else:
                        diagnostics.append(
                            _diagnostic(
                                expression.span,
                                "JOIN ON expression type is unavailable.",
                            )
                        )
        state = (
            ProjectJoinConditionState.INVALID
            if any(d.severity is Severity.ERROR for d in diagnostics)
            else ProjectJoinConditionState.UNAVAILABLE
            if unavailable
            else ProjectJoinConditionState.READY
        )
        ready = state is ProjectJoinConditionState.READY
        object.__setattr__(self, "environment", env)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "expression", expression)
        object.__setattr__(self, "conjuncts", conjuncts)
        object.__setattr__(self, "references", references)
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "value_types", MappingProxyType(value_types))
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "diagnostics", tuple(diagnostics))
        object.__setattr__(
            self, "unavailable_diagnostics", tuple(unavailable_diagnostics)
        )
        object.__setattr__(
            self,
            "mandatory_equalities",
            tuple(
                ProjectJoinConditionEquality(condition=self, conjunct_position=position)
                for position, conjunct in enumerate(conjuncts)
                if ready and _equality_fields(self, conjunct) is not None
            ),
        )
        object.__setattr__(
            self,
            "match_inputs",
            tuple(
                (binding, properties)
                for binding in env.bindings
                for properties in (_matching_properties(self, binding),)
                if properties is not None
            ),
        )
        object.__setattr__(
            self,
            "key_matches",
            tuple(
                ProjectJoinConditionKeyMatch(condition=self, binding=binding, key=key)
                for binding, properties in self.match_inputs
                if ready and self.mandatory_equalities
                for key in resolved_matching_keys(
                    properties.keys, _matched_classes(self, binding, properties)
                )
            ),
        )
        object.__setattr__(
            self,
            "null_rejections",
            tuple(
                ProjectJoinNullRejection(
                    condition=self, conjunct_position=i, reference=reference
                )
                for i, conjunct in enumerate(conjuncts)
                for reference in references
                if ready and _null_rejection_reason(conjunct, reference) is not None
            ),
        )


def _nested_reference_diagnostic(
    condition: ProjectJoinCondition, leaf: NameExpr | DottedNameExpr
) -> Diagnostic:
    """PIE-S2805 for one read of a nested field in a JOIN condition. The SEMI
    or ANTI JOIN that an ANY before a later JOIN becomes is an ANY test, and
    its row is named as written."""

    for use in existence_uses_for_owner(
        condition.root.uses.semantic_result, condition.ledger.owner
    ):
        if use.clause is condition.use.clause:
            ref = None
            if (
                type(leaf) is DottedNameExpr
                and leaf.parts[0] == use.clause.target_binding_name
            ):
                ref = ".".join((use.expression.binding_name, *leaf.parts[1:]))
            return nested_value_diagnostic(leaf, "an ANY test", ref=ref)
    return nested_value_diagnostic(leaf, "JOIN ON")


def _equality_fields(
    condition: ProjectJoinCondition,
    expression: Expression,
) -> tuple[ProjectJoinConditionField, ProjectJoinConditionField] | None:
    if type(expression) is not ComparisonExpr or expression.operator != "==":
        return None
    sides = tuple(
        tuple(
            reference.target
            for reference in condition.references
            if reference.expression is operand and reference.target is not None
        )
        for operand in (expression.left, expression.right)
    )
    if any(len(side) != 1 for side in sides):
        return None
    return sides[0][0], sides[1][0]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionEquality:
    """One mandatory ON equality with exact fields and every predicate call it
    comes from; a hand-written equality comes from none."""

    condition: ProjectJoinCondition = field(repr=False)
    conjunct_position: int
    comparison: ComparisonExpr = field(init=False)
    left: ProjectJoinConditionField = field(init=False)
    right: ProjectJoinConditionField = field(init=False)
    calls: tuple[RelationshipCallInfo, ...] = field(init=False)

    def __post_init__(self) -> None:
        condition = self.condition
        if (
            type(condition) is not ProjectJoinCondition
            or not condition.ready
            or (
                type(self.conjunct_position) is not int
                or not 0 <= self.conjunct_position < len(condition.conjuncts)
            )
        ):
            raise ValueError("Match equality requires an exact ready ON conjunct.")
        comparison = condition.conjuncts[self.conjunct_position]
        sides = _equality_fields(condition, comparison)
        if sides is None or type(comparison) is not ComparisonExpr:
            raise ValueError(
                "Match equality requires two exactly resolved field reads."
            )
        predicate = condition.environment.predicate_expression
        calls = tuple(
            call
            for call in (() if predicate is None else predicate.calls)
            if any(comparison is item for item in call.mandatory_equalities)
        )
        object.__setattr__(self, "comparison", comparison)
        object.__setattr__(self, "left", sides[0])
        object.__setattr__(self, "right", sides[1])
        object.__setattr__(self, "calls", calls)


def _matching_properties(
    condition: ProjectJoinCondition,
    binding: ProjectRelationBindingOccurrence,
) -> ProjectIROutputRelationalProperties | None:
    properties = binding.output
    if properties is None:
        return None
    if condition.inputs is not None:
        matches = tuple(
            item for item in condition.inputs.scope.bindings if item.binding is binding
        )
        if (
            len(matches) != 1
            or matches[0].authority is None
            or (matches[0].authority.historical_properties is not properties)
        ):
            return None
    return properties


def _binding_equalities(
    condition: ProjectJoinCondition,
    binding: ProjectRelationBindingOccurrence,
) -> tuple[tuple[ProjectJoinConditionEquality, ProjectJoinConditionField], ...]:
    target = condition.use.target_binding
    return tuple(
        (equality, own)
        for equality in condition.mandatory_equalities
        for own, other in (
            (equality.left, equality.right),
            (equality.right, equality.left),
        )
        if own.binding is binding
        and (
            (binding is target and other.binding is not target)
            or (binding is not target and other.binding is target)
        )
    )


def _matched_classes(condition, binding, properties):
    fields = tuple(
        field.input_field for _, field in _binding_equalities(condition, binding)
    )
    return tuple(
        group
        for group in properties.value_classes
        if any(member is field for member in group.members for field in fields)
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionKeyMatch:
    """A complete declared input key constrained by this ON's cross-input equalities.

    Extra filters can only reduce matches; no existence/coverage is asserted.
    """

    condition: ProjectJoinCondition = field(repr=False)
    binding: ProjectRelationBindingOccurrence = field(repr=False)
    key: ProjectIROutputCandidateKey
    properties: ProjectIROutputRelationalProperties = field(init=False, repr=False)
    equalities: tuple[ProjectJoinConditionEquality, ...] = field(init=False)
    minimum: ProjectRelationshipMinimumBound = field(
        default=ProjectRelationshipMinimumBound.ZERO_ALLOWED, init=False
    )
    maximum: ProjectRelationshipMaximumBound = field(
        default=ProjectRelationshipMaximumBound.AT_MOST_ONE, init=False
    )

    def __post_init__(self) -> None:
        condition = self.condition
        if (
            type(condition) is not ProjectJoinCondition
            or not condition.ready
            or not (_exact_member(self.binding, condition.environment.bindings))
        ):
            raise ValueError("Key match requires an exact ready ON input occurrence.")
        candidates = tuple(
            properties
            for binding, properties in condition.match_inputs
            if binding is self.binding
        )
        properties = candidates[0] if len(candidates) == 1 else None
        if (
            properties is None
            or not _exact_member(self.key, properties.keys)
            or not _exact_member(
                self.key,
                resolved_matching_keys(
                    properties.keys,
                    _matched_classes(condition, self.binding, properties),
                ),
            )
        ):
            raise ValueError("Key match requires a complete exact input key.")
        object.__setattr__(self, "properties", properties)
        object.__setattr__(
            self,
            "equalities",
            tuple(
                equality for equality, _ in _binding_equalities(condition, self.binding)
            ),
        )


def _null_rejection_reason(
    conjunct: Expression, reference: ProjectJoinConditionReference
) -> str | None:
    if reference.target is None:
        return None
    leaf = reference.expression
    if conjunct is leaf:
        return "true_boolean_operand"
    if isinstance(conjunct, ComparisonExpr) and (
        conjunct.left is leaf or conjunct.right is leaf
    ):
        return "strict_comparison_operand"
    if isinstance(conjunct, IsNullExpr) and conjunct.negated and conjunct.value is leaf:
        return "is_not_null_operand"
    return None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinNullRejection:
    condition: ProjectJoinCondition = field(repr=False)
    conjunct_position: int
    reference: ProjectJoinConditionReference
    reason: str = field(init=False)
    field: ProjectJoinConditionField = field(init=False)

    def __post_init__(self) -> None:
        condition = self.condition
        if (
            type(condition) is not ProjectJoinCondition
            or not condition.ready
            or not _exact_member(self.reference, condition.references)
            or type(self.conjunct_position) is not int
            or not 0 <= self.conjunct_position < len(condition.conjuncts)
        ):
            raise ValueError(
                "Null rejection requires exact ready condition/reference membership."
            )
        reason = _null_rejection_reason(
            condition.conjuncts[self.conjunct_position], self.reference
        )
        if reason is None or self.reference.target is None:
            raise ValueError(
                "Null rejection requires a sufficient exact conjunct proof."
            )
        object.__setattr__(self, "field", self.reference.target)
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionSet:
    """Rebuilt with exact use roots; consumed by completed semantic results."""

    uses: ProjectRelationshipUseSet = field(repr=False)
    entries: tuple[ProjectJoinCondition, ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    predicates: ProjectRelationshipPredicateCatalog = field(init=False, repr=False)
    predicate_expressions: tuple[ProjectRelationshipPredicateExpression, ...] = field(
        init=False
    )

    def __post_init__(self) -> None:
        if type(self.uses) is not ProjectRelationshipUseSet:
            raise TypeError("JOIN conditions require exact use roots.")
        for ledger in self.uses.ledgers:
            validate_project_join_input_bindings(self.uses, ledger)
        predicates = ProjectRelationshipPredicateCatalog(
            semantic_result=self.uses.semantic_result
        )
        object.__setattr__(self, "predicates", predicates)
        object.__setattr__(
            self,
            "predicate_expressions",
            tuple(
                item
                for ledger in self.uses.ledgers
                for item in bind_project_relationship_predicates(predicates, ledger)
            ),
        )
        entries = tuple(
            ProjectJoinCondition(root=self, ledger=ledger, use=use)
            for ledger in self.uses.ledgers
            for use in ledger.uses
        )
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self,
            "diagnostics",
            (
                *predicates.diagnostics,
                *(diagnostic for entry in entries for diagnostic in entry.diagnostics),
            ),
        )


def build_project_join_conditions(
    uses: ProjectRelationshipUseSet,
) -> ProjectJoinConditionSet:
    return ProjectJoinConditionSet(uses=uses)


def rebuild_project_join_condition(
    historical: ProjectJoinCondition,
    inputs: ProjectCurrentPreMatchInputs,
) -> ProjectJoinCondition:
    """Reuse unchanged evidence, otherwise analyze the exact current input root."""
    if (
        type(historical) is not ProjectJoinCondition
        or type(inputs) is not ProjectCurrentPreMatchInputs
        or inputs.use is not historical.use
        or inputs.scope.uses is not historical.root.uses
    ):
        raise ValueError("Condition rebuild requires exact authored and current roots.")
    old = historical.environment
    unchanged = (
        len(old._rows) == len(inputs.rows)
        and len(old.blocked_bindings) == len(inputs.blocked_bindings)
        and all(
            left is right
            for left, right in zip(
                old.blocked_bindings, inputs.blocked_bindings, strict=True
            )
        )
    )
    unchanged = unchanged and all(
        left[0] is right[0]
        and left[1] is right[1]
        and left[2] is right[2]
        and len(left[3]) == len(right[3])
        and all(a is b for a, b in zip(left[3], right[3], strict=True))
        for left, right in zip(old._rows, inputs.rows, strict=True)
    )
    unchanged = unchanged and all(
        item.authority is not None
        and item.authority.historical_properties is not None
        and item.authority.historical_properties is item.binding.output
        for item in inputs.scope.bindings[: historical.use.identity.join_position + 2]
    )
    if unchanged and not old.existence_values:
        return historical
    return ProjectJoinCondition(
        root=historical.root,
        ledger=historical.ledger,
        use=historical.use,
        inputs=inputs,
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionCompletion:
    """The final operative occurrence tuple, retaining its immutable historical set."""

    historical: ProjectJoinConditionSet = field(repr=False)
    entries: tuple[ProjectJoinCondition, ...]
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.historical) is not ProjectJoinConditionSet or len(
            self.entries
        ) != len(self.historical.entries):
            raise ValueError(
                "Operative conditions require the complete historical occurrence set."
            )
        for entry, old in zip(self.entries, self.historical.entries, strict=True):
            if (
                type(entry) is not ProjectJoinCondition
                or entry.root is not self.historical
                or entry.use is not old.use
                or entry.ledger is not old.ledger
            ):
                raise ValueError("Operative conditions cannot replace authored roots.")
            if entry is not old and (
                entry.inputs is None
                or entry.inputs.scope.uses is not self.historical.uses
            ):
                raise ValueError(
                    "Rebuilt condition requires its exact current input root."
                )
        object.__setattr__(
            self,
            "diagnostics",
            tuple(
                diagnostic for entry in self.entries for diagnostic in entry.diagnostics
            ),
        )

    @property
    def uses(self) -> ProjectRelationshipUseSet:
        return self.historical.uses

    @property
    def predicates(self) -> ProjectRelationshipPredicateCatalog:
        return self.historical.predicates

    @property
    def predicate_expressions(
        self,
    ) -> tuple[ProjectRelationshipPredicateExpression, ...]:
        return self.historical.predicate_expressions
