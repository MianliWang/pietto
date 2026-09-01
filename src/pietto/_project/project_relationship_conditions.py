"""Private authored relationship field-correspondence authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleAttributionFactSet,
    ProjectModuleRelationOutputFieldAttribution,
    ProjectModuleRowFieldIdentity,
    ProjectModuleSourceFieldOrigin,
    _declaration_identity,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)
from pietto._project.project_relationships import (
    ProjectConcreteRelationshipSubject,
    ProjectRelationshipDeclarationIdentity,
    ProjectRelationshipEndpointOccurrence,
    ProjectRelationshipSet,
)
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    Expression,
    QueryDef,
    RelationshipMatchClause,
    SourceDef,
    TableDef,
)

__all__: tuple[str, ...] = ()

_DEFERRED_EQUALITY_BUILTINS = frozenset({"Any", "Bytes", "Decimal", "Json"})


class ProjectRelationshipConditionState(StrEnum):
    """Closed construction states independent of relationship construction."""

    ABSENT = "absent"
    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


class ProjectRelationshipConditionScope(StrEnum):
    """Condition evaluation scopes reserved by the Phase-62 architecture."""

    RELATIONSHIP_BASE_MATCH = "relationship_base_match"
    JOIN_LOCAL_ON_REFINEMENT = "join_local_on_refinement"
    POST_JOIN_FILTER = "post_join_filter"


class ProjectRelationshipConstraintScopeKind(StrEnum):
    """Constraint evidence scopes without constructing later evidence."""

    UNCONDITIONAL_ON_EXACT_ROW_OUTPUT = "unconditional_on_exact_row_output"
    UNDER_PREDICATE = "under_predicate"
    UNDER_POLICY = "under_policy"
    UNDER_MATCH_CONTEXT = "under_match_context"


class ProjectRelationshipEqualitySemantics(StrEnum):
    """The sole proof-capable Slice-3 comparison semantics."""

    STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING = (
        "standard_equality_true_only_null_rejecting"
    )


class ProjectRelationshipConditionIssueKind(StrEnum):
    """Exact non-concrete reasons for one authored condition conjunct."""

    UNSUPPORTED_CONDITION_SHAPE = "unsupported_condition_shape"
    UNKNOWN_ENDPOINT_ROLE = "unknown_endpoint_role"
    AMBIGUOUS_ENDPOINT_ROLE = "ambiguous_endpoint_role"
    UNKNOWN_FIELD = "unknown_field"
    UNAVAILABLE_FIELD_AUTHORITY = "unavailable_field_authority"
    AMBIGUOUS_FIELD_AUTHORITY = "ambiguous_field_authority"
    UNKNOWN_FIELD_TYPE = "unknown_field_type"
    INCOMPATIBLE_FIELD_TYPES = "incompatible_field_types"
    SAME_ENDPOINT_EQUALITY = "same_endpoint_equality"


_UNKNOWN_ISSUES = frozenset(
    {
        ProjectRelationshipConditionIssueKind.UNKNOWN_ENDPOINT_ROLE,
        ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD,
        ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY,
        ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD_TYPE,
    }
)
_BLOCKED_ISSUES = frozenset(
    {
        ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ProjectRelationshipConditionIssueKind.INCOMPATIBLE_FIELD_TYPES,
        ProjectRelationshipConditionIssueKind.SAME_ENDPOINT_EQUALITY,
    }
)
_AMBIGUOUS_ISSUES = frozenset(
    {
        ProjectRelationshipConditionIssueKind.AMBIGUOUS_ENDPOINT_ROLE,
        ProjectRelationshipConditionIssueKind.AMBIGUOUS_FIELD_AUTHORITY,
    }
)
_FIELD_REFERENCE_ISSUES = frozenset(
    {
        ProjectRelationshipConditionIssueKind.UNKNOWN_ENDPOINT_ROLE,
        ProjectRelationshipConditionIssueKind.AMBIGUOUS_ENDPOINT_ROLE,
        ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD,
        ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY,
        ProjectRelationshipConditionIssueKind.AMBIGUOUS_FIELD_AUTHORITY,
    }
)
_RESOLVED_COMPARISON_ISSUES = frozenset(
    {
        ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD_TYPE,
        ProjectRelationshipConditionIssueKind.INCOMPATIBLE_FIELD_TYPES,
        ProjectRelationshipConditionIssueKind.SAME_ENDPOINT_EQUALITY,
    }
)


def _require_position(value: object, label: str, *, maximum: int | None = None) -> None:
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f"{label} must be an exact non-negative position.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipBaseMatchIdentity:
    """Nominal identity of one authored condition occurrence."""

    declaration: ProjectRelationshipDeclarationIdentity

    def __post_init__(self) -> None:
        if type(self.declaration) is not ProjectRelationshipDeclarationIdentity:
            raise TypeError("Base-match identity requires a relationship identity.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipCorrespondenceIdentity:
    """Identity of one authored condition conjunct occurrence."""

    base_match: ProjectRelationshipBaseMatchIdentity
    conjunct_position: int

    def __post_init__(self) -> None:
        if type(self.base_match) is not ProjectRelationshipBaseMatchIdentity:
            raise TypeError("Correspondence identity requires a base-match identity.")
        _require_position(self.conjunct_position, "Correspondence conjunct position")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipEndpointFieldReferenceIdentity:
    """Identity of one authored operand subordinate to one conjunct."""

    correspondence: ProjectRelationshipCorrespondenceIdentity
    operand_position: int

    def __post_init__(self) -> None:
        if type(self.correspondence) is not ProjectRelationshipCorrespondenceIdentity:
            raise TypeError("Field reference identity requires a correspondence.")
        _require_position(
            self.operand_position,
            "Field reference operand position",
            maximum=1,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExactRowOutputConstraintScope:
    """One constructible unconditional scope for one exact relation output."""

    kind: ProjectRelationshipConstraintScopeKind
    owner: ProjectDeclarationOccurrenceIdentity
    relation: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if (
            type(self.kind) is not ProjectRelationshipConstraintScopeKind
            or self.kind
            is not ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
        ):
            raise ValueError("Slice 3 constructs only exact-row-output scope.")
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Constraint scope requires an exact output owner.")
        if type(self.relation) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Constraint scope requires exact semantic facts.")
        if (
            _declaration_identity(self.relation.owner) != self.owner
            or self.relation.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        ):
            raise ValueError("Constraint scope must bind one concrete exact output.")


type ProjectRelationshipFieldAuthority = (
    ProjectModuleSourceFieldOrigin | ProjectModuleRelationOutputFieldAttribution
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipEndpointFieldReferenceOccurrence:
    """One exact authored endpoint-field reference and Project field anchor."""

    identity: ProjectRelationshipEndpointFieldReferenceIdentity
    expression: DottedNameExpr = field(repr=False, compare=False, hash=False)
    endpoint: ProjectRelationshipEndpointOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_relation: ProjectModuleRelationSemanticFacts = field(
        repr=False,
        compare=False,
        hash=False,
    )
    field_identity: ProjectModuleRowFieldIdentity
    semantic_field: ProjectRowField = field(repr=False, compare=False, hash=False)
    authority: ProjectRelationshipFieldAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )
    constraint_scope: ProjectExactRowOutputConstraintScope

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipEndpointFieldReferenceIdentity:
            raise TypeError("Endpoint-field reference requires an exact identity.")
        if (
            type(self.expression) is not DottedNameExpr
            or len(self.expression.parts) != 2
        ):
            raise TypeError("Endpoint-field reference requires exactly two name parts.")
        if type(self.endpoint) is not ProjectRelationshipEndpointOccurrence:
            raise TypeError("Endpoint-field reference requires an endpoint occurrence.")
        declaration = self.identity.correspondence.base_match.declaration
        if (
            self.endpoint.identity.declaration != declaration
            or self.endpoint.authored_role != self.expression.parts[0]
            or self.endpoint.target is None
        ):
            raise ValueError("Endpoint-field reference must retain endpoint authority.")
        if type(self.semantic_relation) is not ProjectModuleRelationSemanticFacts:
            raise TypeError("Endpoint-field reference requires semantic facts.")
        target_occurrence = self.endpoint.target.target_occurrence
        schema = self.semantic_relation.state.schema
        if (
            self.semantic_relation.owner is not target_occurrence
            or self.semantic_relation.state.status
            is not ProjectRelationRowSchemaStatus.CONCRETE
            or schema is None
            or schema.fields.get(self.expression.parts[1]) is not self.semantic_field
        ):
            raise ValueError("Endpoint field must retain exact final semantic facts.")
        if type(self.field_identity) is not ProjectModuleRowFieldIdentity or (
            self.field_identity.owner != _declaration_identity(target_occurrence)
            or self.field_identity.name != self.expression.parts[1]
        ):
            raise ValueError("Endpoint field identity must match its exact target.")
        if type(self.semantic_field) is not ProjectRowField:
            raise TypeError("Endpoint field requires exact semantic field evidence.")
        definition = target_occurrence.definition
        if type(definition) is SourceDef:
            if (
                type(self.authority) is not ProjectModuleSourceFieldOrigin
                or self.authority.source_field != self.field_identity
            ):
                raise ValueError("Source endpoint field requires exact source origin.")
        elif type(definition) in {TableDef, QueryDef}:
            if (
                type(self.authority) is not ProjectModuleRelationOutputFieldAttribution
                or self.authority.identity != self.field_identity
                or self.authority.relation is not self.semantic_relation
                or self.authority.semantic_field is not self.semantic_field
            ):
                raise ValueError(
                    "Derived endpoint field requires exact output authority."
                )
        else:
            raise ValueError("Endpoint field target must produce relation rows.")
        if (
            type(self.constraint_scope) is not ProjectExactRowOutputConstraintScope
            or self.constraint_scope.relation is not self.semantic_relation
            or self.constraint_scope.owner != self.field_identity.owner
        ):
            raise ValueError("Endpoint field requires its exact output scope.")

    @property
    def authored_endpoint_role(self) -> str:
        return self.expression.parts[0]

    @property
    def authored_field_spelling(self) -> str:
        return self.expression.parts[1]


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipEqualityCorrespondence:
    """One proof-capable standard-equality conjunct occurrence."""

    identity: ProjectRelationshipCorrespondenceIdentity
    comparison: ComparisonExpr = field(repr=False, compare=False, hash=False)
    authored_left: ProjectRelationshipEndpointFieldReferenceOccurrence
    authored_right: ProjectRelationshipEndpointFieldReferenceOccurrence
    endpoint_zero: ProjectRelationshipEndpointFieldReferenceOccurrence
    endpoint_one: ProjectRelationshipEndpointFieldReferenceOccurrence
    semantics: ProjectRelationshipEqualitySemantics

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipCorrespondenceIdentity:
            raise TypeError("Equality correspondence requires an exact identity.")
        if (
            type(self.comparison) is not ComparisonExpr
            or self.comparison.operator != "=="
        ):
            raise ValueError("Equality correspondence requires standard equality.")
        references = (self.authored_left, self.authored_right)
        if any(
            type(reference) is not ProjectRelationshipEndpointFieldReferenceOccurrence
            or reference.identity.correspondence != self.identity
            or reference.identity.operand_position != position
            or reference.expression
            is not (self.comparison.left, self.comparison.right)[position]
            for position, reference in enumerate(references)
        ):
            raise ValueError("Equality operands must retain authored order.")
        by_endpoint = {
            reference.endpoint.identity.endpoint_position: reference
            for reference in references
        }
        if (
            set(by_endpoint) != {0, 1}
            or self.endpoint_zero is not by_endpoint[0]
            or self.endpoint_one is not by_endpoint[1]
        ):
            raise ValueError("Normalized equality must retain both exact endpoints.")
        if (
            _exact_type_compatibility(
                self.authored_left.semantic_field.resolved_type,
                self.authored_right.semantic_field.resolved_type,
            )
            is not True
        ):
            raise ValueError("Concrete equality requires exact compatible types.")
        if (
            type(self.semantics) is not ProjectRelationshipEqualitySemantics
            or self.semantics
            is not ProjectRelationshipEqualitySemantics.STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING
        ):
            raise ValueError("Slice 3 supports only standard equality semantics.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipConditionIssue:
    """One exact reason that prevents complete correspondence publication."""

    identity: ProjectRelationshipCorrespondenceIdentity
    expression: Expression = field(repr=False, compare=False, hash=False)
    kind: ProjectRelationshipConditionIssueKind
    reference_identity: ProjectRelationshipEndpointFieldReferenceIdentity | None = None
    references: tuple[ProjectRelationshipEndpointFieldReferenceOccurrence, ...] = ()

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipCorrespondenceIdentity:
            raise TypeError("Condition issue requires a correspondence identity.")
        if not isinstance(self.expression, Expression):
            raise TypeError("Condition issue requires exact authored evidence.")
        if type(self.kind) is not ProjectRelationshipConditionIssueKind:
            raise TypeError("Condition issue requires an exact reason.")
        if self.reference_identity is not None and (
            type(self.reference_identity)
            is not ProjectRelationshipEndpointFieldReferenceIdentity
            or self.reference_identity.correspondence != self.identity
        ):
            raise TypeError("Condition issue field identity must retain the conjunct.")
        if (self.kind in _FIELD_REFERENCE_ISSUES) != (
            self.reference_identity is not None
        ):
            raise ValueError("Field-resolution issues require one operand identity.")
        proof_shape = (
            type(self.expression) is ComparisonExpr
            and self.expression.operator == "=="
            and type(self.expression.left) is DottedNameExpr
            and len(self.expression.left.parts) == 2
            and type(self.expression.right) is DottedNameExpr
            and len(self.expression.right.parts) == 2
        )
        if self.kind in (_FIELD_REFERENCE_ISSUES | _RESOLVED_COMPARISON_ISSUES) and (
            not proof_shape
        ):
            raise ValueError("Resolved condition issues require an equality shape.")
        if self.kind in _RESOLVED_COMPARISON_ISSUES and len(self.references) != 2:
            raise ValueError("Resolved comparison issues require both exact fields.")
        if (
            self.kind
            is ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE
            and self.references
        ):
            raise ValueError("Unsupported condition shape forbids partial fields.")
        if type(self.references) is not tuple or any(
            type(reference) is not ProjectRelationshipEndpointFieldReferenceOccurrence
            or reference.identity.correspondence != self.identity
            for reference in self.references
        ):
            raise TypeError("Condition issue references must retain the conjunct.")
        positions = tuple(
            reference.identity.operand_position for reference in self.references
        )
        if len(set(positions)) != len(positions) or any(
            left > right for left, right in zip(positions, positions[1:], strict=False)
        ):
            raise ValueError("Condition issue references must retain operand order.")

    @property
    def state(self) -> ProjectRelationshipConditionState:
        if self.kind in _AMBIGUOUS_ISSUES:
            return ProjectRelationshipConditionState.AMBIGUOUS
        if self.kind in _BLOCKED_ISSUES:
            return ProjectRelationshipConditionState.BLOCKED
        if self.kind in _UNKNOWN_ISSUES:
            return ProjectRelationshipConditionState.UNKNOWN
        raise AssertionError("Unhandled relationship condition issue kind.")


def _references_retain_relationship(
    relationship: ProjectConcreteRelationshipSubject,
    references: tuple[ProjectRelationshipEndpointFieldReferenceOccurrence, ...],
) -> bool:
    endpoints = relationship.occurrence.endpoints
    return all(
        reference.endpoint is endpoints[reference.endpoint.identity.endpoint_position]
        for reference in references
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectConcreteRelationshipCondition:
    """One complete proof-capable authored relationship base match."""

    identity: ProjectRelationshipBaseMatchIdentity
    relationship: ProjectConcreteRelationshipSubject = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: RelationshipMatchClause = field(repr=False, compare=False, hash=False)
    scope: ProjectRelationshipConditionScope
    correspondences: tuple[ProjectRelationshipEqualityCorrespondence, ...]

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipBaseMatchIdentity:
            raise TypeError("Concrete condition requires an exact identity.")
        if type(self.relationship) is not ProjectConcreteRelationshipSubject:
            raise TypeError("Concrete condition requires a concrete relationship.")
        if (
            self.identity.declaration != self.relationship.occurrence.identity
            or type(self.clause) is not RelationshipMatchClause
            or self.relationship.occurrence.relationship.base_match is not self.clause
        ):
            raise ValueError("Concrete condition must retain its authored declaration.")
        if (
            type(self.scope) is not ProjectRelationshipConditionScope
            or self.scope
            is not ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH
        ):
            raise ValueError("Slice 3 constructs only relationship base matches.")
        conjuncts = _condition_conjuncts(self.clause.expression)
        if (
            not conjuncts
            or type(self.correspondences) is not tuple
            or len(self.correspondences) != len(conjuncts)
            or any(
                type(correspondence) is not ProjectRelationshipEqualityCorrespondence
                or correspondence.identity.base_match != self.identity
                or correspondence.identity.conjunct_position != position
                or correspondence.comparison is not conjunct
                for position, (correspondence, conjunct) in enumerate(
                    zip(self.correspondences, conjuncts, strict=True)
                )
            )
        ):
            raise ValueError("Concrete condition must retain every authored conjunct.")
        references = tuple(
            reference
            for correspondence in self.correspondences
            for reference in (
                correspondence.authored_left,
                correspondence.authored_right,
            )
        )
        if not _references_retain_relationship(self.relationship, references):
            raise ValueError("Condition fields must retain exact endpoint occurrences.")

    @property
    def state(self) -> ProjectRelationshipConditionState:
        return ProjectRelationshipConditionState.CONCRETE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteRelationshipCondition:
    """One absent or failed condition without partial correspondence facts."""

    identity: ProjectRelationshipBaseMatchIdentity | None
    relationship: ProjectConcreteRelationshipSubject = field(
        repr=False,
        compare=False,
        hash=False,
    )
    clause: RelationshipMatchClause | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    state: ProjectRelationshipConditionState
    scope: ProjectRelationshipConditionScope
    issues: tuple[ProjectRelationshipConditionIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.relationship) is not ProjectConcreteRelationshipSubject:
            raise TypeError("Non-concrete condition requires a concrete relationship.")
        authored = self.relationship.occurrence.relationship.base_match
        if type(self.state) is not ProjectRelationshipConditionState or self.state in {
            ProjectRelationshipConditionState.CONCRETE,
        }:
            raise ValueError("Non-concrete condition requires a terminal state.")
        if (
            type(self.scope) is not ProjectRelationshipConditionScope
            or self.scope
            is not ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH
        ):
            raise ValueError("Slice 3 constructs only relationship base matches.")
        if self.state is ProjectRelationshipConditionState.ABSENT:
            if (
                self.identity is not None
                or self.clause is not None
                or authored is not None
                or self.issues
            ):
                raise ValueError("ABSENT requires no authored base match or issues.")
            return
        if (
            type(self.identity) is not ProjectRelationshipBaseMatchIdentity
            or self.identity.declaration != self.relationship.occurrence.identity
        ):
            raise ValueError("Failed condition requires its authored identity.")
        if (
            type(self.clause) is not RelationshipMatchClause
            or self.clause is not authored
        ):
            raise ValueError("Failed condition must retain its authored clause.")
        if (
            type(self.issues) is not tuple
            or not self.issues
            or any(
                type(issue) is not ProjectRelationshipConditionIssue
                or issue.identity.base_match != self.identity
                for issue in self.issues
            )
        ):
            raise TypeError("Failed condition requires exact ordered issues.")
        conjuncts = _condition_conjuncts(self.clause.expression)
        if any(
            issue.identity.conjunct_position >= len(conjuncts)
            or issue.expression is not conjuncts[issue.identity.conjunct_position]
            for issue in self.issues
        ):
            raise ValueError("Condition issues must retain exact conjunct evidence.")
        issue_keys = tuple(
            (
                issue.identity.conjunct_position,
                -1
                if issue.reference_identity is None
                else issue.reference_identity.operand_position,
            )
            for issue in self.issues
        )
        if any(
            left > right
            for left, right in zip(issue_keys, issue_keys[1:], strict=False)
        ):
            raise ValueError("Condition issues must retain source and operand order.")
        for issue in self.issues:
            reference_identity = issue.reference_identity
            if reference_identity is None:
                continue
            conjunct = conjuncts[issue.identity.conjunct_position]
            if type(conjunct) is not ComparisonExpr or conjunct.operator != "==":
                raise ValueError("Field issue identity must retain its exact operand.")
            operand = (conjunct.left, conjunct.right)[
                reference_identity.operand_position
            ]
            if type(operand) is not DottedNameExpr or len(operand.parts) != 2:
                raise ValueError("Field issue identity must retain its exact operand.")
        references = tuple(
            reference for issue in self.issues for reference in issue.references
        )
        if not _references_retain_relationship(self.relationship, references):
            raise ValueError("Condition issues must retain exact endpoint occurrences.")
        if _condition_state(self.issues) is not self.state:
            raise ValueError("Condition issues do not support the terminal state.")


type ProjectRelationshipCondition = (
    ProjectConcreteRelationshipCondition | ProjectNonConcreteRelationshipCondition
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipConditionSet:
    """Complete concrete-relationship-ordered authored condition result."""

    relationships: ProjectRelationshipSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    conditions: tuple[ProjectRelationshipCondition, ...] = ()

    def __post_init__(self) -> None:
        if type(self.relationships) is not ProjectRelationshipSet:
            raise TypeError("Relationship conditions require exact relationship roots.")
        if type(self.conditions) is not tuple or any(
            type(condition)
            not in {
                ProjectConcreteRelationshipCondition,
                ProjectNonConcreteRelationshipCondition,
            }
            for condition in self.conditions
        ):
            raise TypeError("Relationship conditions must be an exact typed tuple.")
        expected = tuple(
            subject
            for subject in self.relationships.subjects
            if type(subject) is ProjectConcreteRelationshipSubject
        )
        if len(self.conditions) != len(expected) or any(
            condition.relationship is not relationship
            for condition, relationship in zip(
                self.conditions,
                expected,
                strict=True,
            )
        ):
            raise ValueError("Conditions must retain every concrete relationship.")
        semantic_result = self.relationships.semantic_result
        semantic_facts = semantic_result.module_semantic_facts
        attribution = semantic_result.module_attribution_facts
        if (
            type(semantic_facts) is not ProjectModuleSemanticFactSet
            or type(attribution) is not ProjectModuleAttributionFactSet
        ):
            raise ValueError("Relationship conditions require exact field authority.")
        for condition in self.conditions:
            for reference in _condition_references(condition):
                target = reference.endpoint.target
                assert target is not None
                semantic_bucket = semantic_facts.find_owner(target.target_occurrence)
                if (
                    len(semantic_bucket) != 1
                    or reference.semantic_relation is not semantic_bucket[0]
                ):
                    raise ValueError(
                        "Condition field must retain semantic root authority."
                    )
                authority_bucket = (
                    attribution.find_source_field_origin(reference.field_identity)
                    if type(target.target_occurrence.definition) is SourceDef
                    else attribution.find_relation_output_field(
                        reference.field_identity
                    )
                )
                if (
                    len(authority_bucket) != 1
                    or reference.authority is not authority_bucket[0]
                ):
                    raise ValueError(
                        "Condition field must retain attribution authority."
                    )


def _condition_conjuncts(expression: Expression) -> tuple[Expression, ...]:
    if type(expression) is BinaryExpr and expression.operator == "and":
        return (
            *_condition_conjuncts(expression.left),
            *_condition_conjuncts(expression.right),
        )
    return (expression,)


def _condition_state(
    issues: tuple[ProjectRelationshipConditionIssue, ...],
) -> ProjectRelationshipConditionState:
    states = {issue.state for issue in issues}
    if ProjectRelationshipConditionState.AMBIGUOUS in states:
        return ProjectRelationshipConditionState.AMBIGUOUS
    if ProjectRelationshipConditionState.BLOCKED in states:
        return ProjectRelationshipConditionState.BLOCKED
    if ProjectRelationshipConditionState.UNKNOWN in states:
        return ProjectRelationshipConditionState.UNKNOWN
    raise ValueError("Failed relationship condition requires exact issues.")


def _exact_type_identity(
    resolved_type: ProjectResolvedType,
) -> tuple[object, ...] | None:
    if type(resolved_type) is not ProjectResolvedType or (
        resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
    ):
        return None
    if resolved_type.kind is ProjectResolvedTypeKind.BUILTIN:
        if resolved_type.name in _DEFERRED_EQUALITY_BUILTINS:
            return None
        return (resolved_type.kind, resolved_type.name)
    if resolved_type.kind is ProjectResolvedTypeKind.SHAPE:
        return None
    symbol = resolved_type.symbol
    if symbol is None:
        return None
    return (
        resolved_type.kind,
        resolved_type.name,
        symbol.path,
        symbol.namespace,
        symbol.kind,
        symbol.name,
    )


def _exact_type_compatibility(
    left: ProjectResolvedType,
    right: ProjectResolvedType,
) -> bool | None:
    left_identity = _exact_type_identity(left)
    right_identity = _exact_type_identity(right)
    if left_identity is None or right_identity is None:
        return None
    return left_identity == right_identity


def _field_authority(
    *,
    relationship: ProjectConcreteRelationshipSubject,
    expression: DottedNameExpr,
    identity: ProjectRelationshipEndpointFieldReferenceIdentity,
    semantic_facts: ProjectModuleSemanticFactSet,
    attribution: ProjectModuleAttributionFactSet,
) -> (
    ProjectRelationshipEndpointFieldReferenceOccurrence
    | ProjectRelationshipConditionIssueKind
):
    endpoint_candidates = tuple(
        endpoint
        for endpoint in relationship.occurrence.endpoints
        if endpoint.authored_role == expression.parts[0]
    )
    if not endpoint_candidates:
        return ProjectRelationshipConditionIssueKind.UNKNOWN_ENDPOINT_ROLE
    if len(endpoint_candidates) != 1:
        return ProjectRelationshipConditionIssueKind.AMBIGUOUS_ENDPOINT_ROLE
    endpoint = endpoint_candidates[0]
    target = endpoint.target
    assert target is not None
    semantic_bucket = semantic_facts.find_owner(target.target_occurrence)
    if not semantic_bucket:
        return ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY
    if len(semantic_bucket) != 1:
        return ProjectRelationshipConditionIssueKind.AMBIGUOUS_FIELD_AUTHORITY
    semantic_relation = semantic_bucket[0]
    schema = semantic_relation.state.schema
    if (
        semantic_relation.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or schema is None
    ):
        return ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY
    owner = _declaration_identity(target.target_occurrence)
    field_name = expression.parts[1]
    semantic_field = schema.fields.get(field_name)
    definition = target.target_occurrence.definition
    if type(definition) is SourceDef:
        lineage_bucket = attribution.find_row_lineage(owner)
        if not lineage_bucket:
            return ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY
        if len(lineage_bucket) != 1:
            return ProjectRelationshipConditionIssueKind.AMBIGUOUS_FIELD_AUTHORITY
        lineage = lineage_bucket[0]
        if lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE:
            return ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY
        identity_candidates = tuple(
            field_lineage.field
            for field_lineage in lineage.fields
            if field_lineage.field.name == field_name
        )
        if not identity_candidates and semantic_field is None:
            return ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD
        if len(identity_candidates) != 1 or semantic_field is None:
            raise ValueError("Existing source field authorities disagree.")
        field_identity = identity_candidates[0]
        authority_bucket = attribution.find_source_field_origin(field_identity)
        if len(authority_bucket) != 1:
            raise ValueError("Concrete source field requires one exact origin.")
        authority: ProjectRelationshipFieldAuthority = authority_bucket[0]
    elif type(definition) in {TableDef, QueryDef}:
        output_candidates = tuple(
            output
            for output in attribution.find_relation_output_fields(owner)
            if output.identity.name == field_name
        )
        if not output_candidates and semantic_field is None:
            return ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD
        if (
            len(output_candidates) != 1
            or semantic_field is None
            or output_candidates[0].semantic_field is not semantic_field
        ):
            raise ValueError("Existing relation output authorities disagree.")
        authority = output_candidates[0]
        field_identity = authority.identity
    else:
        raise ValueError("Endpoint target must be a relation declaration.")
    constraint_scope = ProjectExactRowOutputConstraintScope(
        kind=(ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT),
        owner=owner,
        relation=semantic_relation,
    )
    return ProjectRelationshipEndpointFieldReferenceOccurrence(
        identity=identity,
        expression=expression,
        endpoint=endpoint,
        semantic_relation=semantic_relation,
        field_identity=field_identity,
        semantic_field=semantic_field,
        authority=authority,
        constraint_scope=constraint_scope,
    )


def _issue(
    *,
    identity: ProjectRelationshipCorrespondenceIdentity,
    expression: Expression,
    kind: ProjectRelationshipConditionIssueKind,
    reference_identity: (
        ProjectRelationshipEndpointFieldReferenceIdentity | None
    ) = None,
    references: tuple[ProjectRelationshipEndpointFieldReferenceOccurrence, ...] = (),
) -> ProjectRelationshipConditionIssue:
    return ProjectRelationshipConditionIssue(
        identity=identity,
        expression=expression,
        kind=kind,
        reference_identity=reference_identity,
        references=references,
    )


def _correspondence(
    *,
    relationship: ProjectConcreteRelationshipSubject,
    base_match: ProjectRelationshipBaseMatchIdentity,
    conjunct_position: int,
    expression: Expression,
    semantic_facts: ProjectModuleSemanticFactSet,
    attribution: ProjectModuleAttributionFactSet,
) -> (
    ProjectRelationshipEqualityCorrespondence
    | tuple[ProjectRelationshipConditionIssue, ...]
):
    identity = ProjectRelationshipCorrespondenceIdentity(
        base_match=base_match,
        conjunct_position=conjunct_position,
    )
    if (
        type(expression) is not ComparisonExpr
        or expression.operator != "=="
        or type(expression.left) is not DottedNameExpr
        or len(expression.left.parts) != 2
        or type(expression.right) is not DottedNameExpr
        or len(expression.right.parts) != 2
    ):
        return (
            _issue(
                identity=identity,
                expression=expression,
                kind=(
                    ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE
                ),
            ),
        )
    expressions = (expression.left, expression.right)
    reference_identities = tuple(
        ProjectRelationshipEndpointFieldReferenceIdentity(
            correspondence=identity,
            operand_position=operand_position,
        )
        for operand_position in range(2)
    )
    outcomes = tuple(
        _field_authority(
            relationship=relationship,
            expression=operand,
            identity=reference_identities[operand_position],
            semantic_facts=semantic_facts,
            attribution=attribution,
        )
        for operand_position, operand in enumerate(expressions)
    )
    references = tuple(
        outcome
        for outcome in outcomes
        if type(outcome) is ProjectRelationshipEndpointFieldReferenceOccurrence
    )
    issue_positions = tuple(
        (position, outcome)
        for position, outcome in enumerate(outcomes)
        if type(outcome) is ProjectRelationshipConditionIssueKind
    )
    if issue_positions:
        return tuple(
            _issue(
                identity=identity,
                expression=expression,
                kind=kind,
                reference_identity=reference_identities[position],
                references=references,
            )
            for position, kind in issue_positions
        )
    assert len(references) == 2
    left, right = references
    if (
        left.endpoint.identity.endpoint_position
        == right.endpoint.identity.endpoint_position
    ):
        return (
            _issue(
                identity=identity,
                expression=expression,
                kind=ProjectRelationshipConditionIssueKind.SAME_ENDPOINT_EQUALITY,
                references=references,
            ),
        )
    compatibility = _exact_type_compatibility(
        left.semantic_field.resolved_type,
        right.semantic_field.resolved_type,
    )
    if compatibility is None:
        return (
            _issue(
                identity=identity,
                expression=expression,
                kind=ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD_TYPE,
                references=references,
            ),
        )
    if not compatibility:
        return (
            _issue(
                identity=identity,
                expression=expression,
                kind=ProjectRelationshipConditionIssueKind.INCOMPATIBLE_FIELD_TYPES,
                references=references,
            ),
        )
    by_endpoint = {
        reference.endpoint.identity.endpoint_position: reference
        for reference in references
    }
    return ProjectRelationshipEqualityCorrespondence(
        identity=identity,
        comparison=expression,
        authored_left=left,
        authored_right=right,
        endpoint_zero=by_endpoint[0],
        endpoint_one=by_endpoint[1],
        semantics=(
            ProjectRelationshipEqualitySemantics.STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING
        ),
    )


def _condition_references(
    condition: ProjectRelationshipCondition,
) -> tuple[ProjectRelationshipEndpointFieldReferenceOccurrence, ...]:
    if type(condition) is ProjectConcreteRelationshipCondition:
        return tuple(
            reference
            for correspondence in condition.correspondences
            for reference in (
                correspondence.authored_left,
                correspondence.authored_right,
            )
        )
    if type(condition) is ProjectNonConcreteRelationshipCondition:
        return tuple(
            reference for issue in condition.issues for reference in issue.references
        )
    raise AssertionError("Unhandled relationship condition type.")


def build_project_relationship_conditions(
    relationships: ProjectRelationshipSet,
) -> ProjectRelationshipConditionSet:
    """Build exact authored conditions without compiling Project semantics again."""

    if type(relationships) is not ProjectRelationshipSet:
        raise TypeError("Relationship condition construction requires exact roots.")
    semantic_result = relationships.semantic_result
    semantic_facts = semantic_result.module_semantic_facts
    attribution = semantic_result.module_attribution_facts
    if (
        type(semantic_facts) is not ProjectModuleSemanticFactSet
        or type(attribution) is not ProjectModuleAttributionFactSet
    ):
        raise ValueError("Relationship conditions require Project field authority.")

    conditions: list[ProjectRelationshipCondition] = []
    for relationship in relationships.subjects:
        if type(relationship) is not ProjectConcreteRelationshipSubject:
            continue
        clause = relationship.occurrence.relationship.base_match
        if clause is None:
            conditions.append(
                ProjectNonConcreteRelationshipCondition(
                    identity=None,
                    relationship=relationship,
                    state=ProjectRelationshipConditionState.ABSENT,
                    scope=ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH,
                )
            )
            continue
        identity = ProjectRelationshipBaseMatchIdentity(
            declaration=relationship.occurrence.identity
        )
        correspondences: list[ProjectRelationshipEqualityCorrespondence] = []
        issues: list[ProjectRelationshipConditionIssue] = []
        for conjunct_position, expression in enumerate(
            _condition_conjuncts(clause.expression)
        ):
            result = _correspondence(
                relationship=relationship,
                base_match=identity,
                conjunct_position=conjunct_position,
                expression=expression,
                semantic_facts=semantic_facts,
                attribution=attribution,
            )
            if isinstance(result, tuple):
                issues.extend(result)
            else:
                correspondences.append(result)
        if issues:
            issue_tuple = tuple(issues)
            conditions.append(
                ProjectNonConcreteRelationshipCondition(
                    identity=identity,
                    relationship=relationship,
                    clause=clause,
                    state=_condition_state(issue_tuple),
                    scope=ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH,
                    issues=issue_tuple,
                )
            )
            continue
        conditions.append(
            ProjectConcreteRelationshipCondition(
                identity=identity,
                relationship=relationship,
                clause=clause,
                scope=ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH,
                correspondences=tuple(correspondences),
            )
        )
    return ProjectRelationshipConditionSet(
        relationships=relationships,
        conditions=tuple(conditions),
    )
