"""Private authored relationship JOIN uses over exact Project authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionEnvironment,
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionIssueStatus,
    ProjectResolvedModuleRelationSymbol,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_ir_properties import ProjectIRRowShape
from pietto._project.project_relationship_match_guarantees import (
    ProjectDirectionalRelationshipMatchGuarantee,
    ProjectNonConcreteMatchGuaranteeSubject,
)
from pietto._project.project_relationship_paths import (
    ProjectDirectRelationshipCandidateStatus,
    ProjectRelationshipDirectCandidateResult,
    ProjectRelationshipFanoutEffect,
    ProjectRelationshipInnerSurvivalEffect,
    ProjectRelationshipJoinShapeIndex,
    ProjectRelationshipLeftNullingEffect,
    ProjectRelationshipPath,
    ProjectRelationshipPathAnalysis,
    analyze_relationship_path,
    build_explicit_relationship_path,
)
from pietto._project.project_relationships import (
    ProjectConcreteRelationshipSubject,
    ProjectNonConcreteRelationshipSubject,
    ProjectRelationshipConstructionState,
    ProjectRelationshipSet,
    ProjectRelationshipSubject,
)
from pietto.ast_nodes import (
    AuthoredJoinKind,
    FromClause,
    JoinClause,
    JoinTraversalStep,
    QueryDef,
    TableDef,
)

__all__: tuple[str, ...] = ()


class ProjectJoinUseState(StrEnum):
    """Closed construction states for one binding, step, or authored JOIN use."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


class ProjectJoinUseIssueKind(StrEnum):
    """Typed causal failures retained without a candidate winner."""

    UNKNOWN_SOURCE_BINDING = "unknown_source_binding"
    FORWARD_SOURCE_BINDING = "forward_source_binding"
    AMBIGUOUS_SOURCE_BINDING = "ambiguous_source_binding"
    BLOCKED_SOURCE_BINDING = "blocked_source_binding"
    UNKNOWN_TARGET_RELATION = "unknown_target_relation"
    AMBIGUOUS_TARGET_RELATION = "ambiguous_target_relation"
    BLOCKED_TARGET_RELATION = "blocked_target_relation"
    DIRECT_RELATIONSHIP_ABSENT = "direct_relationship_absent"
    DIRECT_RELATIONSHIP_AMBIGUOUS = "direct_relationship_ambiguous"
    UNKNOWN_RELATIONSHIP = "unknown_relationship"
    AMBIGUOUS_RELATIONSHIP = "ambiguous_relationship"
    BLOCKED_RELATIONSHIP = "blocked_relationship"
    UNKNOWN_ENDPOINT_DIRECTION = "unknown_endpoint_direction"
    AMBIGUOUS_ENDPOINT_DIRECTION = "ambiguous_endpoint_direction"
    BLOCKED_ENDPOINT_DIRECTION = "blocked_endpoint_direction"
    NON_CONTIGUOUS_PATH = "non_contiguous_path"
    PATH_START_MISMATCH = "path_start_mismatch"
    PATH_END_MISMATCH = "path_end_mismatch"


_ISSUE_STATES = {
    ProjectJoinUseIssueKind.UNKNOWN_SOURCE_BINDING: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.FORWARD_SOURCE_BINDING: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.AMBIGUOUS_SOURCE_BINDING: ProjectJoinUseState.AMBIGUOUS,
    ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.UNKNOWN_TARGET_RELATION: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.AMBIGUOUS_TARGET_RELATION: ProjectJoinUseState.AMBIGUOUS,
    ProjectJoinUseIssueKind.BLOCKED_TARGET_RELATION: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_ABSENT: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_AMBIGUOUS: (
        ProjectJoinUseState.AMBIGUOUS
    ),
    ProjectJoinUseIssueKind.UNKNOWN_RELATIONSHIP: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.AMBIGUOUS_RELATIONSHIP: ProjectJoinUseState.AMBIGUOUS,
    ProjectJoinUseIssueKind.BLOCKED_RELATIONSHIP: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.UNKNOWN_ENDPOINT_DIRECTION: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.AMBIGUOUS_ENDPOINT_DIRECTION: (
        ProjectJoinUseState.AMBIGUOUS
    ),
    ProjectJoinUseIssueKind.BLOCKED_ENDPOINT_DIRECTION: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.NON_CONTIGUOUS_PATH: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.PATH_START_MISMATCH: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.PATH_END_MISMATCH: ProjectJoinUseState.BLOCKED,
}

_AMBIGUOUS_RELATION_ISSUES = frozenset(
    {ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME}
)
_BLOCKED_RELATION_ISSUES = frozenset(
    {
        ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE,
        ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
        ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
    }
)


def _require_position(value: object, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} must be an exact non-negative position.")


def _owner_identity(
    owner: ProjectDeclarationOccurrence,
) -> ProjectDeclarationOccurrenceIdentity:
    return ProjectDeclarationOccurrenceIdentity(
        identity=owner.identity,
        module_position=owner.module_position,
        declaration_position=owner.declaration_position,
    )


def _derived_definition(
    owner: ProjectDeclarationOccurrence,
) -> TableDef | QueryDef:
    definition = owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise ValueError("JOIN authority requires a table or query owner.")
    return cast(TableDef | QueryDef, definition)


def _is_join_bearing(owner: ProjectDeclarationOccurrence) -> bool:
    definition = owner.definition
    return type(definition) in {TableDef, QueryDef} and bool(
        cast(TableDef | QueryDef, definition).join_clauses
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationBindingIdentity:
    """One owner-local relation binding occurrence identity."""

    owner: ProjectDeclarationOccurrenceIdentity
    binding_position: int

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Relation binding identity requires an owner occurrence.")
        _require_position(self.binding_position, "Relation binding")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectJoinUseIdentity:
    """One authored JOIN occurrence under its exact owner."""

    owner: ProjectDeclarationOccurrenceIdentity
    join_position: int

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("JOIN-use identity requires an owner occurrence.")
        _require_position(self.join_position, "JOIN use")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTraversalStepUseIdentity:
    """One authored VIA occurrence subordinate to one JOIN use."""

    join: ProjectJoinUseIdentity
    step_position: int

    def __post_init__(self) -> None:
        if type(self.join) is not ProjectJoinUseIdentity:
            raise TypeError("Traversal-step use requires a JOIN-use identity.")
        _require_position(self.step_position, "Traversal-step use")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationBindingOccurrence:
    """One base or JOIN-target binding with exact relation authority."""

    identity: ProjectRelationBindingIdentity
    owner: ProjectDeclarationOccurrence = field(repr=False, compare=False, hash=False)
    site: FromClause | JoinClause = field(repr=False, compare=False, hash=False)
    name: str
    relation_name: str
    state: ProjectJoinUseState
    target: ProjectResolvedModuleRelationSymbol | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    output: ProjectIROutputRelationalProperties | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    relation_issues: tuple[ProjectModuleRelationResolutionIssue, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationBindingIdentity:
            raise TypeError("Relation binding requires an exact identity.")
        if type(self.owner) is not ProjectDeclarationOccurrence or (
            self.identity.owner != _owner_identity(self.owner)
        ):
            raise ValueError("Relation binding must retain its exact owner.")
        definition = _derived_definition(self.owner)
        if self.identity.binding_position == 0:
            expected_site = definition.from_clause
            expected_name = expected_relation = expected_site.source_name
        else:
            position = self.identity.binding_position - 1
            if position >= len(definition.join_clauses):
                raise ValueError("JOIN binding position is outside its owner.")
            expected_site = definition.join_clauses[position]
            expected_name = expected_site.target_binding_name
            expected_relation = expected_site.target_relation_name
        if (
            self.site is not expected_site
            or self.name != expected_name
            or self.relation_name != expected_relation
        ):
            raise ValueError(
                "Relation binding must retain exact source order and names."
            )
        if type(self.state) is not ProjectJoinUseState:
            raise TypeError("Relation binding requires an exact state.")
        if self.target is not None and (
            type(self.target) is not ProjectResolvedModuleRelationSymbol
            or self.target.local_name != self.relation_name
        ):
            raise ValueError("Relation binding target must use the authored lookup.")
        if type(self.relation_issues) is not tuple or any(
            type(item) is not ProjectModuleRelationResolutionIssue
            for item in self.relation_issues
        ):
            raise TypeError("Relation binding issues must be an exact tuple.")
        if self.state is ProjectJoinUseState.CONCRETE:
            if (
                self.target is None
                or type(self.output) is not ProjectIROutputRelationalProperties
            ):
                raise ValueError(
                    "Concrete relation binding requires target and output."
                )
            shape = self.output.output.row_shape
            if (
                type(shape) is not ProjectIRRowShape
                or shape.evidence.owner is not self.target.target_occurrence
            ):
                raise ValueError(
                    "Concrete relation binding output must match its exact target."
                )
        elif self.output is not None:
            raise ValueError("Non-concrete relation binding cannot expose an output.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectJoinUseIssue:
    """One typed failure plus its complete retained causal objects."""

    kind: ProjectJoinUseIssueKind
    state: ProjectJoinUseState
    site: JoinClause | JoinTraversalStep = field(repr=False, compare=False, hash=False)
    causes: tuple[object, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectJoinUseIssueKind:
            raise TypeError("JOIN-use issue requires an exact kind.")
        if self.state is not _ISSUE_STATES[self.kind]:
            raise ValueError("JOIN-use issue kind and state disagree.")
        if type(self.site) not in {JoinClause, JoinTraversalStep}:
            raise TypeError("JOIN-use issue requires an authored site.")
        if type(self.causes) is not tuple or any(item is None for item in self.causes):
            raise TypeError("JOIN-use issue causes must be an exact object tuple.")


def _dominant_state(issues: tuple[ProjectJoinUseIssue, ...]) -> ProjectJoinUseState:
    states = {issue.state for issue in issues}
    if ProjectJoinUseState.AMBIGUOUS in states:
        return ProjectJoinUseState.AMBIGUOUS
    if ProjectJoinUseState.BLOCKED in states:
        return ProjectJoinUseState.BLOCKED
    if ProjectJoinUseState.UNKNOWN in states:
        return ProjectJoinUseState.UNKNOWN
    raise ValueError("Non-concrete JOIN use requires typed issues.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectTraversalStepUse:
    """One authored VIA occurrence and its exact direction outcome."""

    identity: ProjectTraversalStepUseIdentity
    step: JoinTraversalStep = field(repr=False, compare=False, hash=False)
    state: ProjectJoinUseState
    relationships: tuple[ProjectRelationshipSubject, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )
    directions: tuple[ProjectDirectionalRelationshipMatchGuarantee, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )
    issues: tuple[ProjectJoinUseIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectTraversalStepUseIdentity:
            raise TypeError("Traversal-step use requires an exact identity.")
        if type(self.step) is not JoinTraversalStep:
            raise TypeError("Traversal-step use requires an authored VIA step.")
        for values, expected in (
            (
                self.relationships,
                (
                    ProjectConcreteRelationshipSubject,
                    ProjectNonConcreteRelationshipSubject,
                ),
            ),
            (self.directions, (ProjectDirectionalRelationshipMatchGuarantee,)),
            (self.issues, (ProjectJoinUseIssue,)),
        ):
            if type(values) is not tuple or any(
                type(item) not in expected for item in values
            ):
                raise TypeError("Traversal-step evidence must be exact typed tuples.")
        if self.state is ProjectJoinUseState.CONCRETE:
            if len(self.relationships) != 1 or len(self.directions) != 1 or self.issues:
                raise ValueError(
                    "Concrete traversal step requires one exact direction."
                )
        elif not self.issues or self.state is not _dominant_state(self.issues):
            raise ValueError("Non-concrete traversal step requires causal evidence.")
        if any(
            relationship.occurrence.name != self.step.relationship_name
            for relationship in self.relationships
        ):
            raise ValueError("Traversal relationship candidates must match its name.")
        if any(
            direction.direction.source.authored_role != self.step.source_endpoint_role
            or direction.direction.target.authored_role
            != self.step.target_endpoint_role
            or not any(
                type(relationship) is ProjectConcreteRelationshipSubject
                and relationship.occurrence.identity == direction.direction.declaration
                for relationship in self.relationships
            )
            for direction in self.directions
        ):
            raise ValueError(
                "Traversal directions must match relationship and endpoint roles."
            )
        if any(issue.site is not self.step for issue in self.issues):
            raise ValueError("Traversal-step issues must retain their exact VIA site.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectConcreteJoinUse:
    """One exact relationship traversal use without a joined row output."""

    identity: ProjectJoinUseIdentity
    owner: ProjectDeclarationOccurrence = field(repr=False, compare=False, hash=False)
    clause: JoinClause = field(repr=False, compare=False, hash=False)
    kind: AuthoredJoinKind
    source_binding: ProjectRelationBindingOccurrence
    target_binding: ProjectRelationBindingOccurrence
    target_relation: ProjectResolvedModuleRelationSymbol = field(
        repr=False, compare=False, hash=False
    )
    path: ProjectRelationshipPath
    analysis: ProjectRelationshipPathAnalysis
    step_uses: tuple[ProjectTraversalStepUse, ...] = ()

    def __post_init__(self) -> None:
        _validate_use_site(self.identity, self.owner, self.clause)
        if self.kind is not self.clause.kind:
            raise ValueError("Concrete JOIN use must retain its authored kind.")
        if (
            self.source_binding.state is not ProjectJoinUseState.CONCRETE
            or self.target_binding.state is not ProjectJoinUseState.CONCRETE
            or self.source_binding.owner is not self.owner
            or self.source_binding.name != self.clause.source_binding_name
            or self.source_binding.identity.binding_position
            > self.identity.join_position
            or self.target_binding.owner is not self.owner
            or self.target_binding.identity.binding_position
            != self.identity.join_position + 1
            or self.target_binding.target is not self.target_relation
            or self.analysis.path is not self.path
        ):
            raise ValueError("Concrete JOIN use requires exact binding and path roots.")
        if (
            type(self.target_relation) is not ProjectResolvedModuleRelationSymbol
            or self.source_binding.output is None
            or self.target_binding.output is None
            or self.path.steps[0].guarantee.source_output
            is not self.source_binding.output
            or self.path.steps[-1].guarantee.target_output
            is not self.target_binding.output
        ):
            raise ValueError("Concrete JOIN path must match its exact binding outputs.")
        if len(self.step_uses) != len(self.clause.traversal_steps) or any(
            use.identity.join != self.identity
            or use.identity.step_position != position
            or use.step is not step
            or use.state is not ProjectJoinUseState.CONCRETE
            for position, (use, step) in enumerate(
                zip(self.step_uses, self.clause.traversal_steps, strict=True)
            )
        ):
            raise ValueError("Concrete JOIN use must retain every authored VIA use.")
        if self.step_uses:
            if len(self.path.steps) != len(self.step_uses) or any(
                path_step.guarantee is not step_use.directions[0]
                for path_step, step_use in zip(
                    self.path.steps, self.step_uses, strict=True
                )
            ):
                raise ValueError("Explicit JOIN path must match every exact VIA use.")
        else:
            direct = self.path.index.resolve_direct(
                self.source_binding.output,
                self.target_binding.output,
            )
            if (
                len(self.path.steps) != 1
                or direct.status
                is not ProjectDirectRelationshipCandidateStatus.CONCRETE
                or next(iter(direct.candidates)) is not self.path.steps[0].guarantee
            ):
                raise ValueError(
                    "Direct JOIN path must retain its sole exact candidate."
                )

    @property
    def fanout_readiness(self) -> ProjectRelationshipFanoutEffect:
        return self.analysis.fanout

    @property
    def inner_survival_readiness(
        self,
    ) -> ProjectRelationshipInnerSurvivalEffect | None:
        return (
            self.analysis.inner_survival
            if self.kind is AuthoredJoinKind.INNER
            else None
        )

    @property
    def left_null_readiness(self) -> ProjectRelationshipLeftNullingEffect | None:
        return (
            self.analysis.left_nulling if self.kind is AuthoredJoinKind.LEFT else None
        )

    @property
    def left_source_preserved(self) -> bool:
        return self.kind is AuthoredJoinKind.LEFT

    @property
    def left_potential_null_target(
        self,
    ) -> ProjectRelationBindingOccurrence | None:
        return self.target_binding if self.kind is AuthoredJoinKind.LEFT else None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteJoinUse:
    """One failed authored JOIN occurrence with no partial path winner."""

    identity: ProjectJoinUseIdentity
    owner: ProjectDeclarationOccurrence = field(repr=False, compare=False, hash=False)
    clause: JoinClause = field(repr=False, compare=False, hash=False)
    source_binding: ProjectRelationBindingOccurrence | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    target_binding: ProjectRelationBindingOccurrence
    state: ProjectJoinUseState
    step_uses: tuple[ProjectTraversalStepUse, ...] = ()
    issues: tuple[ProjectJoinUseIssue, ...]
    direct_result: ProjectRelationshipDirectCandidateResult | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    path: ProjectRelationshipPath | None = field(
        default=None, repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        _validate_use_site(self.identity, self.owner, self.clause)
        if type(self.target_binding) is not ProjectRelationBindingOccurrence:
            raise TypeError("Non-concrete JOIN use requires its target binding.")
        if (
            self.target_binding.owner is not self.owner
            or self.target_binding.identity.binding_position
            != self.identity.join_position + 1
            or (
                self.source_binding is not None
                and (
                    self.source_binding.owner is not self.owner
                    or self.source_binding.name != self.clause.source_binding_name
                    or self.source_binding.identity.binding_position
                    > self.identity.join_position
                )
            )
        ):
            raise ValueError("Non-concrete JOIN bindings must match authored order.")
        if len(self.step_uses) != len(self.clause.traversal_steps) or any(
            use.identity.join != self.identity
            or use.identity.step_position != position
            or use.step is not step
            for position, (use, step) in enumerate(
                zip(self.step_uses, self.clause.traversal_steps, strict=True)
            )
        ):
            raise ValueError("Non-concrete JOIN use must retain every VIA occurrence.")
        if (
            type(self.issues) is not tuple
            or not self.issues
            or any(type(issue) is not ProjectJoinUseIssue for issue in self.issues)
            or self.state is ProjectJoinUseState.CONCRETE
            or self.state is not _dominant_state(self.issues)
        ):
            raise ValueError("Non-concrete JOIN use requires exact causal state.")
        allowed_sites = (self.clause, *self.clause.traversal_steps)
        if any(
            not any(issue.site is site for site in allowed_sites)
            for issue in self.issues
        ) or any(
            not any(retained is issue for retained in self.issues)
            for step_use in self.step_uses
            for issue in step_use.issues
        ):
            raise ValueError(
                "Non-concrete JOIN issues must retain exact authored sites."
            )
        if self.direct_result is not None:
            if (
                type(self.direct_result) is not ProjectRelationshipDirectCandidateResult
                or self.clause.traversal_steps
                or self.source_binding is None
                or self.source_binding.output is None
                or self.target_binding.output is None
                or self.direct_result.source is not self.source_binding.output
                or self.direct_result.target is not self.target_binding.output
                or self.direct_result.status
                is ProjectDirectRelationshipCandidateStatus.CONCRETE
                or self.path is not None
            ):
                raise ValueError("Non-concrete direct JOIN evidence is detached.")
        if self.path is not None:
            if (
                type(self.path) is not ProjectRelationshipPath
                or not self.clause.traversal_steps
                or self.direct_result is not None
                or any(
                    step.state is not ProjectJoinUseState.CONCRETE
                    for step in self.step_uses
                )
                or len(self.path.steps) != len(self.step_uses)
                or any(
                    path_step.guarantee is not step_use.directions[0]
                    for path_step, step_use in zip(
                        self.path.steps, self.step_uses, strict=True
                    )
                )
            ):
                raise ValueError("Non-concrete explicit path evidence is detached.")

    @property
    def kind(self) -> AuthoredJoinKind:
        return self.clause.kind


type ProjectJoinUse = ProjectConcreteJoinUse | ProjectNonConcreteJoinUse


def _validate_use_site(
    identity: ProjectJoinUseIdentity,
    owner: ProjectDeclarationOccurrence,
    clause: JoinClause,
) -> None:
    if type(identity) is not ProjectJoinUseIdentity:
        raise TypeError("JOIN use requires an exact identity.")
    if type(owner) is not ProjectDeclarationOccurrence or (
        identity.owner != _owner_identity(owner)
    ):
        raise ValueError("JOIN use must retain its exact owner.")
    definition = _derived_definition(owner)
    if (
        identity.join_position >= len(definition.join_clauses)
        or definition.join_clauses[identity.join_position] is not clause
    ):
        raise ValueError("JOIN use must retain exact authored order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationJoinUseLedger:
    """One join-bearing owner with complete binding and use occurrences."""

    owner: ProjectDeclarationOccurrence = field(repr=False, compare=False, hash=False)
    bindings: tuple[ProjectRelationBindingOccurrence, ...]
    uses: tuple[ProjectJoinUse, ...]

    def __post_init__(self) -> None:
        definition = _derived_definition(self.owner)
        if not definition.join_clauses:
            raise ValueError("JOIN-use ledger requires a join-bearing relation owner.")
        if len(self.bindings) != len(definition.join_clauses) + 1 or any(
            binding.owner is not self.owner
            or binding.identity.binding_position != position
            for position, binding in enumerate(self.bindings)
        ):
            raise ValueError("JOIN-use ledger must retain every binding in order.")
        if len(self.uses) != len(definition.join_clauses) or any(
            use.owner is not self.owner
            or use.identity.join_position != position
            or use.clause is not clause
            for position, (use, clause) in enumerate(
                zip(self.uses, definition.join_clauses, strict=True)
            )
        ):
            raise ValueError(
                "JOIN-use ledger must retain every authored JOIN in order."
            )
        for position, use in enumerate(self.uses):
            if use.target_binding is not self.bindings[position + 1]:
                raise ValueError("JOIN use must retain its exact target binding.")
            source = use.source_binding
            if source is not None and not any(
                source is binding for binding in self.bindings[: position + 1]
            ):
                raise ValueError("JOIN use source must be one exact earlier binding.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipUseSet:
    """Selected-module/declaration-ordered authored JOIN-use product."""

    relationships: ProjectRelationshipSet = field(repr=False, compare=False, hash=False)
    index: ProjectRelationshipJoinShapeIndex = field(
        repr=False, compare=False, hash=False
    )
    ledgers: tuple[ProjectRelationJoinUseLedger, ...]

    def __post_init__(self) -> None:
        if (
            type(self.relationships) is not ProjectRelationshipSet
            or type(self.index) is not ProjectRelationshipJoinShapeIndex
            or self.index.guarantees.conditions.relationships is not self.relationships
        ):
            raise ValueError(
                "JOIN uses require one exact Slice-2 through Slice-9 root."
            )
        catalogs = self.relationships.semantic_result.module_catalogs
        if catalogs is None:
            raise ValueError("JOIN uses require exact module catalog authority.")
        expected = tuple(
            occurrence
            for catalog in catalogs.catalogs
            for occurrence in catalog.occurrences
            if _is_join_bearing(occurrence)
        )
        if len(self.ledgers) != len(expected) or any(
            type(ledger) is not ProjectRelationJoinUseLedger
            or ledger.owner is not owner
            for ledger, owner in zip(self.ledgers, expected, strict=True)
        ):
            raise ValueError("JOIN-use ledgers must retain module/declaration order.")
        subjects = self.relationships.subjects
        for ledger in self.ledgers:
            for use in ledger.uses:
                if use.path is not None and use.path.index is not self.index:
                    raise ValueError("JOIN path must retain the exact Slice-9 index.")
                if (
                    type(use) is ProjectNonConcreteJoinUse
                    and use.direct_result is not None
                    and any(
                        not any(
                            candidate is retained for retained in self.index.directions
                        )
                        for candidate in use.direct_result.candidates
                    )
                ):
                    raise ValueError(
                        "Direct candidates must belong to the exact index."
                    )
                for step_use in use.step_uses:
                    if any(
                        not any(relationship is retained for retained in subjects)
                        for relationship in step_use.relationships
                    ) or any(
                        not any(
                            direction is retained for retained in self.index.directions
                        )
                        for direction in step_use.directions
                    ):
                        raise ValueError(
                            "Traversal-step evidence must retain exact shared roots."
                        )

    @property
    def uses(self) -> tuple[ProjectJoinUse, ...]:
        return tuple(use for ledger in self.ledgers for use in ledger.uses)


def _relation_issues(
    environment: ProjectModuleRelationResolutionEnvironment,
    name: str,
    site: FromClause | None = None,
) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
    return tuple(
        issue
        for issue in environment.issues
        if (
            site is not None
            and issue.reference is not None
            and issue.reference.from_clause is site
        )
        or (
            issue.local_name == name
            and issue.status
            is not ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD
        )
    )


def _state_from_relation_issues(
    issues: tuple[ProjectModuleRelationResolutionIssue, ...],
) -> ProjectJoinUseState:
    statuses = {issue.status for issue in issues}
    if statuses & _AMBIGUOUS_RELATION_ISSUES:
        return ProjectJoinUseState.AMBIGUOUS
    if statuses & _BLOCKED_RELATION_ISSUES:
        return ProjectJoinUseState.BLOCKED
    return ProjectJoinUseState.UNKNOWN


def _final_output(
    index: ProjectRelationshipJoinShapeIndex,
    target: ProjectResolvedModuleRelationSymbol,
) -> ProjectIROutputRelationalProperties | None:
    stage = index.guarantees.relational
    fragments = tuple(
        fragment
        for fragment in stage.analyses.stage.project_plan.concrete_fragments
        if fragment.semantic_facts.owner is target.target_occurrence
    )
    if not fragments:
        return None
    if len(fragments) != 1:
        raise ValueError("Relation binding has multiple concrete Project IR roots.")
    matches = tuple(
        output
        for output in stage.outputs
        if output.output is fragments[0].root_relation_output
    )
    if len(matches) != 1:
        raise ValueError("Relation binding requires one exact final output.")
    return matches[0]


def _binding(
    *,
    owner: ProjectDeclarationOccurrence,
    position: int,
    environment: ProjectModuleRelationResolutionEnvironment,
    index: ProjectRelationshipJoinShapeIndex,
    duplicate: bool,
) -> ProjectRelationBindingOccurrence:
    definition = _derived_definition(owner)
    site: FromClause | JoinClause
    if position == 0:
        site = definition.from_clause
        name = relation_name = site.source_name
        resolutions = environment.find_from_clause(site)
        targets = tuple(item.target_symbol for item in resolutions)
        issues = _relation_issues(environment, relation_name, site)
    else:
        site = definition.join_clauses[position - 1]
        name = site.target_binding_name
        relation_name = site.target_relation_name
        targets = environment.find_relation_name(relation_name)
        issues = _relation_issues(environment, relation_name)
    target = targets[0] if len(targets) == 1 else None
    output = None if target is None else _final_output(index, target)
    if duplicate or len(targets) > 1:
        state = ProjectJoinUseState.AMBIGUOUS
    elif target is None:
        state = _state_from_relation_issues(issues)
    elif output is None:
        state = ProjectJoinUseState.BLOCKED
    else:
        state = ProjectJoinUseState.CONCRETE
    return ProjectRelationBindingOccurrence(
        identity=ProjectRelationBindingIdentity(
            owner=_owner_identity(owner), binding_position=position
        ),
        owner=owner,
        site=site,
        name=name,
        relation_name=relation_name,
        state=state,
        target=target,
        output=output if state is ProjectJoinUseState.CONCRETE else None,
        relation_issues=issues,
    )


def _issue(
    kind: ProjectJoinUseIssueKind,
    site: JoinClause | JoinTraversalStep,
    *causes: object,
) -> ProjectJoinUseIssue:
    return ProjectJoinUseIssue(
        kind=kind,
        state=_ISSUE_STATES[kind],
        site=site,
        causes=tuple(causes),
    )


def _binding_issue(
    binding: ProjectRelationBindingOccurrence,
    clause: JoinClause,
    *,
    source: bool,
) -> ProjectJoinUseIssue:
    kinds = {
        (
            True,
            ProjectJoinUseState.UNKNOWN,
        ): ProjectJoinUseIssueKind.UNKNOWN_SOURCE_BINDING,
        (
            True,
            ProjectJoinUseState.BLOCKED,
        ): ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING,
        (
            True,
            ProjectJoinUseState.AMBIGUOUS,
        ): ProjectJoinUseIssueKind.AMBIGUOUS_SOURCE_BINDING,
        (
            False,
            ProjectJoinUseState.UNKNOWN,
        ): ProjectJoinUseIssueKind.UNKNOWN_TARGET_RELATION,
        (
            False,
            ProjectJoinUseState.BLOCKED,
        ): ProjectJoinUseIssueKind.BLOCKED_TARGET_RELATION,
        (
            False,
            ProjectJoinUseState.AMBIGUOUS,
        ): ProjectJoinUseIssueKind.AMBIGUOUS_TARGET_RELATION,
    }
    return _issue(kinds[(source, binding.state)], clause, binding)


def _step_use(
    *,
    identity: ProjectTraversalStepUseIdentity,
    step: JoinTraversalStep,
    relationships: tuple[ProjectRelationshipSubject, ...],
    index: ProjectRelationshipJoinShapeIndex,
) -> ProjectTraversalStepUse:
    candidates: tuple[ProjectRelationshipSubject, ...] = tuple(
        relationship
        for relationship in relationships
        if relationship.occurrence.name == step.relationship_name
    )
    if not candidates:
        issues = (_issue(ProjectJoinUseIssueKind.UNKNOWN_RELATIONSHIP, step),)
        return ProjectTraversalStepUse(
            identity=identity,
            step=step,
            state=ProjectJoinUseState.UNKNOWN,
            relationships=(),
            issues=issues,
        )
    if len(candidates) > 1:
        issues = (
            _issue(ProjectJoinUseIssueKind.AMBIGUOUS_RELATIONSHIP, step, *candidates),
        )
        return ProjectTraversalStepUse(
            identity=identity,
            step=step,
            state=ProjectJoinUseState.AMBIGUOUS,
            relationships=candidates,
            issues=issues,
        )
    relationship = next(iter(candidates))
    if type(relationship) is ProjectNonConcreteRelationshipSubject:
        kind = {
            ProjectRelationshipConstructionState.UNKNOWN: ProjectJoinUseIssueKind.UNKNOWN_RELATIONSHIP,
            ProjectRelationshipConstructionState.BLOCKED: ProjectJoinUseIssueKind.BLOCKED_RELATIONSHIP,
            ProjectRelationshipConstructionState.AMBIGUOUS: ProjectJoinUseIssueKind.AMBIGUOUS_RELATIONSHIP,
        }[relationship.state]
        issue = _issue(kind, step, relationship)
        return ProjectTraversalStepUse(
            identity=identity,
            step=step,
            state=issue.state,
            relationships=candidates,
            issues=(issue,),
        )
    endpoints = relationship.occurrence.endpoints
    sources = tuple(
        endpoint
        for endpoint in endpoints
        if endpoint.authored_role == step.source_endpoint_role
    )
    targets = tuple(
        endpoint
        for endpoint in endpoints
        if endpoint.authored_role == step.target_endpoint_role
    )
    if len(sources) != 1 or len(targets) != 1 or sources[0] is targets[0]:
        issue = _issue(
            ProjectJoinUseIssueKind.UNKNOWN_ENDPOINT_DIRECTION, step, relationship
        )
        return ProjectTraversalStepUse(
            identity=identity,
            step=step,
            state=issue.state,
            relationships=candidates,
            issues=(issue,),
        )
    directions = tuple(
        direction
        for direction in index.by_declaration.get(relationship.occurrence.identity, ())
        if direction.direction.source is sources[0]
        and direction.direction.target is targets[0]
    )
    if len(directions) == 1:
        return ProjectTraversalStepUse(
            identity=identity,
            step=step,
            state=ProjectJoinUseState.CONCRETE,
            relationships=candidates,
            directions=directions,
        )
    if len(directions) > 1:
        issue = _issue(
            ProjectJoinUseIssueKind.AMBIGUOUS_ENDPOINT_DIRECTION, step, *directions
        )
    else:
        fallbacks = tuple(
            item
            for item in index.non_concrete
            if type(item) is ProjectNonConcreteMatchGuaranteeSubject
            and item.relationship is relationship
        )
        issue = _issue(
            (
                ProjectJoinUseIssueKind.BLOCKED_ENDPOINT_DIRECTION
                if fallbacks
                else ProjectJoinUseIssueKind.UNKNOWN_ENDPOINT_DIRECTION
            ),
            step,
            *(fallbacks or (relationship,)),
        )
    return ProjectTraversalStepUse(
        identity=identity,
        step=step,
        state=issue.state,
        relationships=candidates,
        directions=directions,
        issues=(issue,),
    )


def _non_concrete_use(
    *,
    identity: ProjectJoinUseIdentity,
    owner: ProjectDeclarationOccurrence,
    clause: JoinClause,
    target: ProjectRelationBindingOccurrence,
    issues: tuple[ProjectJoinUseIssue, ...],
    source: ProjectRelationBindingOccurrence | None = None,
    step_uses: tuple[ProjectTraversalStepUse, ...] = (),
    direct_result: ProjectRelationshipDirectCandidateResult | None = None,
    path: ProjectRelationshipPath | None = None,
) -> ProjectNonConcreteJoinUse:
    return ProjectNonConcreteJoinUse(
        identity=identity,
        owner=owner,
        clause=clause,
        source_binding=source,
        target_binding=target,
        state=_dominant_state(issues),
        step_uses=step_uses,
        issues=issues,
        direct_result=direct_result,
        path=path,
    )


def _build_use(
    *,
    owner: ProjectDeclarationOccurrence,
    position: int,
    bindings: tuple[ProjectRelationBindingOccurrence, ...],
    prior_uses: tuple[ProjectJoinUse, ...],
    relationship_subjects: tuple[ProjectRelationshipSubject, ...],
    index: ProjectRelationshipJoinShapeIndex,
) -> ProjectJoinUse:
    definition = _derived_definition(owner)
    clause = definition.join_clauses[position]
    identity = ProjectJoinUseIdentity(
        owner=_owner_identity(owner), join_position=position
    )
    target = bindings[position + 1]
    step_uses = tuple(
        _step_use(
            identity=ProjectTraversalStepUseIdentity(
                join=identity, step_position=step_position
            ),
            step=step,
            relationships=relationship_subjects,
            index=index,
        )
        for step_position, step in enumerate(clause.traversal_steps)
    )
    step_issues = tuple(issue for use in step_uses for issue in use.issues)
    earlier = bindings[: position + 1]
    matches: tuple[ProjectRelationBindingOccurrence, ...] = tuple(
        binding for binding in earlier if binding.name == clause.source_binding_name
    )
    if not matches:
        later = tuple(
            binding
            for binding in bindings[position + 1 :]
            if binding.name == clause.source_binding_name
        )
        issue = _issue(
            (
                ProjectJoinUseIssueKind.FORWARD_SOURCE_BINDING
                if later
                else ProjectJoinUseIssueKind.UNKNOWN_SOURCE_BINDING
            ),
            clause,
            *later,
        )
        return _non_concrete_use(
            identity=identity,
            owner=owner,
            clause=clause,
            target=target,
            step_uses=step_uses,
            issues=(issue, *step_issues),
        )
    if len(matches) > 1:
        issue = _issue(
            ProjectJoinUseIssueKind.AMBIGUOUS_SOURCE_BINDING, clause, *matches
        )
        return _non_concrete_use(
            identity=identity,
            owner=owner,
            clause=clause,
            target=target,
            step_uses=step_uses,
            issues=(issue, *step_issues),
        )
    source = next(iter(matches))
    issues: list[ProjectJoinUseIssue] = []
    if source.state is not ProjectJoinUseState.CONCRETE:
        issues.append(_binding_issue(source, clause, source=True))
    elif source.identity.binding_position > 0:
        producer = prior_uses[source.identity.binding_position - 1]
        if type(producer) is ProjectNonConcreteJoinUse:
            issues.append(
                _issue(
                    ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING,
                    clause,
                    source,
                    producer,
                )
            )
    if target.state is not ProjectJoinUseState.CONCRETE:
        issues.append(_binding_issue(target, clause, source=False))
    if issues:
        return _non_concrete_use(
            identity=identity,
            owner=owner,
            clause=clause,
            source=source,
            target=target,
            step_uses=step_uses,
            issues=(*issues, *step_issues),
        )
    assert source.output is not None and target.output is not None
    assert target.target is not None

    if step_uses:
        if step_issues:
            return _non_concrete_use(
                identity=identity,
                owner=owner,
                clause=clause,
                source=source,
                target=target,
                step_uses=step_uses,
                issues=step_issues,
            )
        directions = tuple(use.directions[0] for use in step_uses)
        try:
            path = build_explicit_relationship_path(index, directions)
        except ValueError:
            issue = _issue(
                ProjectJoinUseIssueKind.NON_CONTIGUOUS_PATH, clause, *directions
            )
            return _non_concrete_use(
                identity=identity,
                owner=owner,
                clause=clause,
                source=source,
                target=target,
                step_uses=step_uses,
                issues=(issue,),
            )
        endpoint_issues: list[ProjectJoinUseIssue] = []
        if path.steps[0].guarantee.source_output is not source.output:
            endpoint_issues.append(
                _issue(ProjectJoinUseIssueKind.PATH_START_MISMATCH, clause, path)
            )
        if path.steps[-1].guarantee.target_output is not target.output:
            endpoint_issues.append(
                _issue(ProjectJoinUseIssueKind.PATH_END_MISMATCH, clause, path)
            )
        if endpoint_issues:
            return _non_concrete_use(
                identity=identity,
                owner=owner,
                clause=clause,
                source=source,
                target=target,
                step_uses=step_uses,
                issues=tuple(endpoint_issues),
                path=path,
            )
    else:
        direct = index.resolve_direct(source.output, target.output)
        if direct.status is not ProjectDirectRelationshipCandidateStatus.CONCRETE:
            issue = _issue(
                (
                    ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_ABSENT
                    if direct.status is ProjectDirectRelationshipCandidateStatus.ABSENT
                    else ProjectJoinUseIssueKind.DIRECT_RELATIONSHIP_AMBIGUOUS
                ),
                clause,
                direct,
            )
            return _non_concrete_use(
                identity=identity,
                owner=owner,
                clause=clause,
                source=source,
                target=target,
                issues=(issue,),
                direct_result=direct,
            )
        path = build_explicit_relationship_path(index, direct.candidates)

    analysis = analyze_relationship_path(path)
    return ProjectConcreteJoinUse(
        identity=identity,
        owner=owner,
        clause=clause,
        kind=clause.kind,
        source_binding=source,
        target_binding=target,
        target_relation=target.target,
        path=path,
        analysis=analysis,
        step_uses=step_uses,
    )


def build_project_relationship_uses(
    relationships: ProjectRelationshipSet,
    index: ProjectRelationshipJoinShapeIndex,
) -> ProjectRelationshipUseSet:
    """Build complete authored JOIN uses without constructing joined row outputs."""

    if (
        type(relationships) is not ProjectRelationshipSet
        or type(index) is not ProjectRelationshipJoinShapeIndex
        or index.guarantees.conditions.relationships is not relationships
    ):
        raise ValueError(
            "JOIN-use construction requires exact Slice-2 through Slice-9 roots."
        )
    semantic = relationships.semantic_result
    catalogs = semantic.module_catalogs
    resolutions = semantic.module_relation_resolutions
    if catalogs is None or resolutions is None:
        raise ValueError("JOIN-use construction requires module resolution authority.")
    ledgers: list[ProjectRelationJoinUseLedger] = []
    for catalog in catalogs.catalogs:
        relation_environments = resolutions.find_module_path(catalog.module_path)
        relationship_environments = relationships.find_module_path(catalog.module_path)
        if len(relation_environments) != 1 or len(relationship_environments) != 1:
            raise ValueError("JOIN-use module roots must be exact and complete.")
        relation_environment = relation_environments[0]
        relationship_subjects = relationship_environments[0].subjects
        for owner in catalog.occurrences:
            if not _is_join_bearing(owner):
                continue
            definition = _derived_definition(owner)
            names = (
                definition.from_clause.source_name,
                *(clause.target_binding_name for clause in definition.join_clauses),
            )
            duplicates = {name for name in names if names.count(name) > 1}
            bindings = tuple(
                _binding(
                    owner=owner,
                    position=position,
                    environment=relation_environment,
                    index=index,
                    duplicate=name in duplicates,
                )
                for position, name in enumerate(names)
            )
            uses: list[ProjectJoinUse] = []
            for position in range(len(definition.join_clauses)):
                uses.append(
                    _build_use(
                        owner=owner,
                        position=position,
                        bindings=bindings,
                        prior_uses=tuple(uses),
                        relationship_subjects=relationship_subjects,
                        index=index,
                    )
                )
            ledgers.append(
                ProjectRelationJoinUseLedger(
                    owner=owner, bindings=bindings, uses=tuple(uses)
                )
            )
    return ProjectRelationshipUseSet(
        relationships=relationships,
        index=index,
        ledgers=tuple(ledgers),
    )
