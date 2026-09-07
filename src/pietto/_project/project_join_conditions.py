"""Private pre-match condition facts; no JOIN output or operation admission."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType
from collections.abc import Mapping

from pietto._flat_relational_admission import availability_diagnostic
from pietto._project.model import ProjectRowFieldNullability
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputFieldOccurrence,
)
from pietto._project.project_relationship_conditions import (
    ProjectConcreteRelationshipCondition,
    ProjectRelationshipConditionScope,
    _condition_conjuncts,
)
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
    ProjectRefinedMatchBounds,
    ProjectRelationshipMinimumBound,
)
from pietto._project.project_relationship_paths import ProjectRelationshipPathStep
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectJoinUse,
    ProjectJoinUseState,
    ProjectRelationBindingOccurrence,
    ProjectRelationJoinUseLedger,
    ProjectRelationshipUseSet,
    _final_output,
    project_join_combination_error,
    project_join_mode,
    project_join_source_candidates,
    validate_project_join_input_bindings,
)
from pietto._project.project_scalar_references import scalar_field_reference_leaves
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
)
from pietto.ast_nodes import (
    AuthoredJoinKind,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    IsNullExpr,
    NameExpr,
    Span,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind
from pietto.semantic.predicate_checks import _check_bool_expression

__all__: tuple[str, ...] = ()


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
    ProjectIROutputFieldOccurrence,
    ProjectRowFieldNullability,
    tuple[ProjectRelationshipPathStep, ...],
]


def _input_rows(
    roots: ProjectRelationshipUseSet,
    ledger: ProjectRelationJoinUseLedger,
    use: ProjectJoinUse,
) -> tuple[tuple[_InputRow, ...], tuple[ProjectRelationBindingOccurrence, ...]]:
    """Replay only existing input nullability, without allocating prefix IR.

    A prior unavailable JOIN blocks the accumulated left input. Its eventual
    shape/effective output is deliberately not guessed at this boundary.
    """
    bindings = ledger.bindings[: use.identity.join_position + 2]
    inputs = tuple(
        (binding, output)
        for binding in bindings
        for output in (
            binding.output
            if binding.output is not None
            else _final_output(roots.index, binding.target)
            if binding.state is ProjectJoinUseState.AMBIGUOUS
            and binding.target is not None
            else None,
        )
        if output is not None
    )
    nullability = {
        (id(binding), id(item)): item.effective_nullability
        for binding, output in inputs
        for item in output.fields
    }
    nulling: dict[int, tuple[ProjectRelationshipPathStep, ...]] = {}
    blocked = [
        binding
        for binding in bindings
        if binding.state is not ProjectJoinUseState.CONCRETE
    ]
    for prior in ledger.uses[: use.identity.join_position]:
        if type(prior) is not ProjectConcreteJoinUse:
            blocked.extend(bindings[: use.identity.join_position + 1])
            break
        source_nulling = nulling.get(id(prior.source_binding), ())
        for position, step in enumerate(prior.path.steps):
            guarantee = step.guarantee
            right_nulling = (
                (*source_nulling, step)
                if prior.kind is AuthoredJoinKind.LEFT
                and (
                    guarantee.minimum is ProjectRelationshipMinimumBound.ZERO_ALLOWED
                    or source_nulling
                )
                else ()
            )
            if (
                position == 0
                and prior.kind is AuthoredJoinKind.INNER
                and not source_nulling
            ):
                for value_class in guarantee.source_matched_classes:
                    for member in value_class.members:
                        nullability[id(prior.source_binding), id(member)] = (
                            ProjectRowFieldNullability.NON_NULL
                        )
            if position == len(prior.path.steps) - 1:
                nulling[id(prior.target_binding)] = right_nulling
                for member in guarantee.target_output.fields:
                    if right_nulling:
                        nullability[id(prior.target_binding), id(member)] = (
                            ProjectRowFieldNullability.NULLABLE
                        )
                    elif any(
                        _exact_member(member, group.members)
                        for group in guarantee.target_matched_classes
                    ):
                        nullability[id(prior.target_binding), id(member)] = (
                            ProjectRowFieldNullability.NON_NULL
                        )
            source_nulling = right_nulling
    return (
        tuple(
            (
                binding,
                item,
                nullability[id(binding), id(item)],
                nulling.get(id(binding), ()),
            )
            for binding, output in inputs
            for item in output.fields
        ),
        tuple(
            binding for binding in bindings if _exact_member(binding, tuple(blocked))
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionEnvironment:
    root: ProjectJoinConditionSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    use: ProjectJoinUse = field(repr=False)
    bindings: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    source_candidates: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    blocked_bindings: tuple[ProjectRelationBindingOccurrence, ...] = field(init=False)
    fields: tuple[ProjectJoinConditionField, ...] = field(init=False)
    _rows: tuple[_InputRow, ...] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.root) is not ProjectJoinConditionSet
            or not _exact_member(self.ledger, self.root.uses.ledgers)
            or not _exact_member(self.use, self.ledger.uses)
        ):
            raise ValueError(
                "Condition environment requires exact root/ledger/use membership."
            )
        rows, blocked = _input_rows(self.root.uses, self.ledger, self.use)
        object.__setattr__(
            self,
            "bindings",
            self.ledger.bindings[: self.use.identity.join_position + 2],
        )
        object.__setattr__(
            self,
            "source_candidates",
            project_join_source_candidates(self.ledger, self.use),
        )
        object.__setattr__(self, "blocked_bindings", blocked)
        object.__setattr__(self, "_rows", rows)
        object.__setattr__(
            self,
            "fields",
            tuple(
                ProjectJoinConditionField(environment=self, position=i)
                for i in range(len(rows))
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinConditionField:
    environment: ProjectJoinConditionEnvironment = field(repr=False)
    position: int
    binding: ProjectRelationBindingOccurrence = field(init=False)
    input_field: ProjectIROutputFieldOccurrence = field(init=False)
    nullability: ProjectRowFieldNullability = field(init=False)
    null_extensions: tuple[ProjectRelationshipPathStep, ...] = field(init=False)
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
        if (
            type(env) is not ProjectJoinConditionEnvironment
            or env.use.clause.on_clause is None
        ):
            raise ValueError("Reference requires an exact authored ON environment.")
        leaves = scalar_field_reference_leaves(env.use.clause.on_clause.expression)
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


def _base_guarantees(
    env: ProjectJoinConditionEnvironment, mode: str
) -> tuple[ProjectDirectionalRelationshipMatchGuarantee, ...]:
    use = env.use
    if mode in {"M3", "M5"}:
        return ()
    if type(use) is ProjectConcreteJoinUse:
        return tuple(step.guarantee for step in use.path.steps)
    if use.step_uses:
        if any(len(step.directions) != 1 or step.issues for step in use.step_uses):
            return ()
        return tuple(step.directions[0] for step in use.step_uses)
    if len(env.source_candidates) == 1:
        source, target = env.source_candidates[0].output, use.target_binding.output
        if source is not None and target is not None:
            return env.root.uses.index.resolve_direct(source, target).candidates
    return ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinCondition:
    root: ProjectJoinConditionSet = field(repr=False)
    ledger: ProjectRelationJoinUseLedger = field(repr=False)
    use: ProjectJoinUse = field(repr=False)
    environment: ProjectJoinConditionEnvironment = field(init=False)
    mode: str = field(init=False)
    scope: ProjectRelationshipConditionScope | None = field(init=False)
    expression: Expression | None = field(init=False)
    conjuncts: tuple[Expression, ...] = field(init=False)
    references: tuple[ProjectJoinConditionReference, ...] = field(init=False)
    base_conditions: tuple[ProjectConcreteRelationshipCondition, ...] = field(
        init=False
    )
    base_guarantee: ProjectDirectionalRelationshipMatchGuarantee | None = field(
        init=False
    )
    refinement_guarantee: ProjectRefinedMatchBounds | None = field(init=False)
    value_type: ValueType | None = field(init=False)
    value_types: Mapping[Expression, ValueType] = field(init=False, repr=False)
    state: ProjectJoinConditionState = field(init=False)
    ready: bool = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)
    null_rejections: tuple[ProjectJoinNullRejection, ...] = field(init=False)

    def __post_init__(self) -> None:
        env = ProjectJoinConditionEnvironment(
            root=self.root, ledger=self.ledger, use=self.use
        )
        clause = self.use.clause
        mode = project_join_mode(clause)
        expression = (
            clause.on_clause.expression if clause.on_clause is not None else None
        )
        scope = (
            (
                ProjectRelationshipConditionScope.JOIN_LOCAL_ON_REFINEMENT
                if mode == "M4"
                else ProjectRelationshipConditionScope.GENERIC_JOIN_MATCH
            )
            if expression is not None
            else None
        )
        conjuncts = _condition_conjuncts(expression) if expression is not None else ()
        references = (
            tuple(
                ProjectJoinConditionReference(environment=env, position=i)
                for i in range(len(scalar_field_reference_leaves(expression)))
            )
            if expression is not None
            else ()
        )
        diagnostics: list[Diagnostic] = []
        combination = project_join_combination_error(clause)
        if combination is not None:
            diagnostics.append(_diagnostic(clause.span, combination, code="PIE-S2336"))
        guarantees = _base_guarantees(env, mode)
        bases = tuple(
            condition
            for guarantee in guarantees
            for condition in self.root.uses.index.guarantees.conditions.conditions
            if type(condition) is ProjectConcreteRelationshipCondition
            and condition.relationship.occurrence.identity
            == guarantee.direction.declaration
        )
        source_candidates = env.source_candidates
        unavailable = bool(env.blocked_bindings) or len(source_candidates) != 1
        if mode not in {"M3", "M5"}:
            unavailable |= not guarantees or len(bases) != len(guarantees)
            if guarantees and len(source_candidates) == 1:
                unavailable |= (
                    guarantees[0].source_output is not source_candidates[0].output
                    or guarantees[-1].target_output
                    is not self.use.target_binding.output
                )
            if mode == "M1":
                unavailable |= len(guarantees) != 1
        # Existing M1/M2 diagnostics keep their original projection and ordering.
        is_new = expression is not None or clause.kind not in {
            AuthoredJoinKind.INNER,
            AuthoredJoinKind.LEFT,
        }
        unavailable |= not is_new and type(self.use) is not ProjectConcreteJoinUse
        if unavailable and is_new:
            if len(source_candidates) != 1:
                later = tuple(
                    binding
                    for binding in self.ledger.bindings[
                        self.use.identity.join_position + 1 :
                    ]
                    if binding.name == clause.source_binding_name
                )
                reason = (
                    "ambiguous"
                    if source_candidates
                    else "forward"
                    if later
                    else "unknown"
                )
                message = f"JOIN source binding is {reason}."
            else:
                message = (
                    "JOIN pre-match input or relationship authority is unavailable."
                )
            diagnostics.append(_diagnostic(clause.span, message))
        value_types: dict[Expression, ValueType] = {}
        for reference in references:
            if reference.target is None:
                diagnostics.append(
                    _diagnostic(
                        reference.expression.span,
                        f"JOIN ON reference is {reference.state.value}.",
                    )
                )
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
                )
                predicate_diagnostic = _check_bool_expression(
                    expression, context="JOIN ON", expression_value_types=value_types
                )
                if predicate_diagnostic is not None:
                    diagnostics.append(predicate_diagnostic)
                if value_type.kind is ValueTypeKind.UNKNOWN and not diagnostics:
                    diagnostics.append(
                        _diagnostic(
                            expression.span, "JOIN ON expression type is unavailable."
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
        base = guarantees[0] if len(guarantees) == 1 else None
        object.__setattr__(self, "environment", env)
        object.__setattr__(self, "mode", mode)
        object.__setattr__(self, "scope", scope)
        object.__setattr__(self, "expression", expression)
        object.__setattr__(self, "conjuncts", conjuncts)
        object.__setattr__(self, "references", references)
        object.__setattr__(self, "base_conditions", bases)
        object.__setattr__(self, "base_guarantee", base)
        object.__setattr__(
            self,
            "refinement_guarantee",
            ProjectRefinedMatchBounds(base=base)
            if ready and mode == "M4" and base is not None
            else None,
        )
        object.__setattr__(self, "value_type", value_type)
        object.__setattr__(self, "value_types", MappingProxyType(value_types))
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "ready", ready)
        object.__setattr__(self, "diagnostics", tuple(diagnostics))
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

    def __post_init__(self) -> None:
        if type(self.uses) is not ProjectRelationshipUseSet:
            raise TypeError("JOIN conditions require exact use roots.")
        for ledger in self.uses.ledgers:
            validate_project_join_input_bindings(self.uses, ledger)
        entries = tuple(
            ProjectJoinCondition(root=self, ledger=ledger, use=use)
            for ledger in self.uses.ledgers
            for use in ledger.uses
        )
        object.__setattr__(self, "entries", entries)
        object.__setattr__(
            self,
            "diagnostics",
            tuple(diagnostic for entry in entries for diagnostic in entry.diagnostics),
        )


def build_project_join_conditions(
    uses: ProjectRelationshipUseSet,
) -> ProjectJoinConditionSet:
    return ProjectJoinConditionSet(uses=uses)
