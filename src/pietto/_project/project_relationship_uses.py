"""Private authored JOIN uses over exact Project authority.

A use records each authored JOIN occurrence of a join-bearing owner with its
exact relation bindings. No relationship joins by itself: every JOIN's rows
come from its `on` (or CROSS), which the JOIN condition owner analyzes, so a
use is never concrete; its issues say why its input is not a relationship
traversal.
"""

from __future__ import annotations

from pietto._flat_relational_admission import unsupported_join

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.model import (
    ProjectSemanticResult,
    project_declaration_occurrence_identity,
)
from pietto._project.module_attribution import ProjectDeclarationOccurrenceIdentity
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalog,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionEnvironment,
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionIssueStatus,
    ProjectResolvedModuleRelationSymbol,
)
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
    ProjectIRRelationalPropertyStage,
)
from pietto._project.project_ir_properties import ProjectIRRowShape
from pietto.ast_nodes import (
    AuthoredJoinKind,
    FromClause,
    JoinClause,
    QueryDef,
    TableDef,
)

__all__: tuple[str, ...] = ()


class ProjectJoinUseState(StrEnum):
    """Closed construction states for one binding or authored JOIN use."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


class ProjectJoinUseIssueKind(StrEnum):
    """Typed causal failures retained without a candidate winner."""

    SYNTAX_UNSUPPORTED = "syntax_unsupported"
    UNKNOWN_SOURCE_BINDING = "unknown_source_binding"
    BLOCKED_SOURCE_BINDING = "blocked_source_binding"
    UNKNOWN_TARGET_RELATION = "unknown_target_relation"
    AMBIGUOUS_TARGET_RELATION = "ambiguous_target_relation"
    BLOCKED_TARGET_RELATION = "blocked_target_relation"


_ISSUE_STATES = {
    ProjectJoinUseIssueKind.SYNTAX_UNSUPPORTED: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.UNKNOWN_SOURCE_BINDING: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING: ProjectJoinUseState.BLOCKED,
    ProjectJoinUseIssueKind.UNKNOWN_TARGET_RELATION: ProjectJoinUseState.UNKNOWN,
    ProjectJoinUseIssueKind.AMBIGUOUS_TARGET_RELATION: ProjectJoinUseState.AMBIGUOUS,
    ProjectJoinUseIssueKind.BLOCKED_TARGET_RELATION: ProjectJoinUseState.BLOCKED,
}

_AMBIGUOUS_RELATION_ISSUES = frozenset(
    {
        ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME,
        ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NAME_COLLISION,
    }
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
    return project_declaration_occurrence_identity(owner)


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
            expected_name = expected_site.binding_name or expected_site.source_name
            expected_relation = expected_site.source_name
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
    site: JoinClause = field(repr=False, compare=False, hash=False)
    causes: tuple[object, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectJoinUseIssueKind:
            raise TypeError("JOIN-use issue requires an exact kind.")
        if self.state is not _ISSUE_STATES[self.kind]:
            raise ValueError("JOIN-use issue kind and state disagree.")
        if type(self.site) is not JoinClause:
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
class ProjectNonConcreteJoinUse:
    """One authored JOIN occurrence, which no relationship joins by itself."""

    identity: ProjectJoinUseIdentity
    owner: ProjectDeclarationOccurrence = field(repr=False, compare=False, hash=False)
    clause: JoinClause = field(repr=False, compare=False, hash=False)
    target_binding: ProjectRelationBindingOccurrence
    state: ProjectJoinUseState
    issues: tuple[ProjectJoinUseIssue, ...]

    def __post_init__(self) -> None:
        _validate_use_site(self.identity, self.owner, self.clause)
        if type(self.target_binding) is not ProjectRelationBindingOccurrence:
            raise TypeError("Non-concrete JOIN use requires its target binding.")
        if (
            self.target_binding.owner is not self.owner
            or self.target_binding.identity.binding_position
            != self.identity.join_position + 1
        ):
            raise ValueError("Non-concrete JOIN bindings must match authored order.")
        if (
            type(self.issues) is not tuple
            or not self.issues
            or any(type(issue) is not ProjectJoinUseIssue for issue in self.issues)
            or self.state is ProjectJoinUseState.CONCRETE
            or self.state is not _dominant_state(self.issues)
        ):
            raise ValueError("Non-concrete JOIN use requires exact causal state.")
        if any(issue.site is not self.clause for issue in self.issues):
            raise ValueError(
                "Non-concrete JOIN issues must retain exact authored sites."
            )

    @property
    def kind(self) -> AuthoredJoinKind:
        return self.clause.kind


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
    uses: tuple[ProjectNonConcreteJoinUse, ...]

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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipUseSet:
    """Selected-module/declaration-ordered authored JOIN-use product."""

    semantic_result: ProjectSemanticResult = field(
        repr=False, compare=False, hash=False
    )
    relational: ProjectIRRelationalPropertyStage = field(
        repr=False, compare=False, hash=False
    )
    ledgers: tuple[ProjectRelationJoinUseLedger, ...]

    def __post_init__(self) -> None:
        semantic = self.semantic_result
        if (
            type(semantic) is not ProjectSemanticResult
            or semantic.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or semantic.module_relation_resolutions is None
            or type(self.relational) is not ProjectIRRelationalPropertyStage
            or self.relational.analyses.stage.project_plan.semantic_facts
            is not semantic.module_semantic_facts
        ):
            raise ValueError("JOIN uses require one exact semantic snapshot.")
        catalogs = semantic.module_catalogs
        if catalogs is None:
            raise ValueError("JOIN uses require exact module catalog authority.")
        expected = tuple(
            occurrence
            for catalog in catalogs.catalogs
            for occurrence in catalog.relation_owners
            if _is_join_bearing(occurrence)
        )
        if len(self.ledgers) != len(expected) or any(
            type(ledger) is not ProjectRelationJoinUseLedger
            or ledger.owner is not owner
            for ledger, owner in zip(self.ledgers, expected, strict=True)
        ):
            raise ValueError("JOIN-use ledgers must retain module/declaration order.")

    @property
    def uses(self) -> tuple[ProjectNonConcreteJoinUse, ...]:
        return tuple(use for ledger in self.ledgers for use in ledger.uses)


def _relation_issues(
    environment: ProjectModuleRelationResolutionEnvironment,
    owner: ProjectDeclarationOccurrence,
    name: str,
    site: FromClause | None = None,
) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
    scoped = {
        id(issue)
        for issue in environment.find_scoped_issues(owner, name)
        if issue.status
        is not ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD
    }
    return tuple(
        issue
        for issue in environment.issues
        if (
            site is not None
            and issue.reference is not None
            and issue.reference.from_clause is site
        )
        or id(issue) in scoped
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
    relational: ProjectIRRelationalPropertyStage,
    target: ProjectResolvedModuleRelationSymbol,
) -> ProjectIROutputRelationalProperties | None:
    fragments = tuple(
        fragment
        for fragment in relational.analyses.stage.project_plan.concrete_fragments
        if fragment.semantic_facts.owner is target.target_occurrence
    )
    if not fragments:
        return None
    if len(fragments) != 1:
        raise ValueError("Relation binding has multiple concrete Project IR roots.")
    matches = tuple(
        output
        for output in relational.outputs
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
    relational: ProjectIRRelationalPropertyStage,
    duplicate: bool,
    catalog: ProjectModuleCatalog | None,
) -> ProjectRelationBindingOccurrence:
    definition = _derived_definition(owner)
    site: FromClause | JoinClause
    if position == 0:
        site = definition.from_clause
        name = site.binding_name or site.source_name
        relation_name = site.source_name
        resolutions = environment.find_from_clause(site)
        targets = tuple(item.target_symbol for item in resolutions)
        issues = _relation_issues(environment, owner, relation_name, site)
    else:
        site = definition.join_clauses[position - 1]
        name = site.target_binding_name
        relation_name = site.target_relation_name
        # An Unnest JOIN reads its occurrence by identity (D-S05-1); no
        # scoped name lookup reaches it, nor its name another relation.
        unnest = None if catalog is None else catalog.find_unnest(owner, site)
        if unnest is not None:
            targets = environment.find_unnest_symbol(unnest)
            issues = ()
        else:
            targets = environment.find_scoped_relation_name(owner, relation_name)
            issues = _relation_issues(environment, owner, relation_name)
    target = targets[0] if len(targets) == 1 else None
    output = None if target is None else _final_output(relational, target)
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
    site: JoinClause,
    *causes: object,
) -> ProjectJoinUseIssue:
    return ProjectJoinUseIssue(
        kind=kind,
        state=_ISSUE_STATES[kind],
        site=site,
        causes=tuple(causes),
    )


def _target_issue(
    binding: ProjectRelationBindingOccurrence, clause: JoinClause
) -> ProjectJoinUseIssue:
    kinds = {
        ProjectJoinUseState.UNKNOWN: ProjectJoinUseIssueKind.UNKNOWN_TARGET_RELATION,
        ProjectJoinUseState.BLOCKED: ProjectJoinUseIssueKind.BLOCKED_TARGET_RELATION,
        ProjectJoinUseState.AMBIGUOUS: (
            ProjectJoinUseIssueKind.AMBIGUOUS_TARGET_RELATION
        ),
    }
    return _issue(kinds[binding.state], clause, binding)


def project_join_mode(clause: JoinClause) -> str:
    """Classify the authored JOIN: CROSS is M5, a JOIN with `on` M3, and a
    JOIN without `on` M1, which no relationship joins by itself."""
    if clause.kind is AuthoredJoinKind.CROSS:
        return "M5"
    return "M1" if clause.on_clause is None else "M3"


def project_join_combination_error(clause: JoinClause) -> str | None:
    if clause.kind is AuthoredJoinKind.CROSS and clause.on_clause is not None:
        return "CROSS JOIN cannot have ON or VIA."
    return None


def project_join_binding_visible(
    binding: ProjectRelationBindingOccurrence,
    prior_uses: tuple[ProjectNonConcreteJoinUse, ...],
) -> bool:
    """Keep structural dependencies distinct from accumulated-row visibility."""
    return not any(
        use.target_binding is binding
        and use.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
        for use in prior_uses
    )


def project_join_visible_bindings(
    ledger: ProjectRelationJoinUseLedger, use: ProjectNonConcreteJoinUse
) -> tuple[ProjectRelationBindingOccurrence, ...]:
    """The earlier bindings a JOIN may read its source rows from."""
    if not any(use is retained for retained in ledger.uses):
        raise ValueError("Pre-match source requires its exact JOIN ledger.")
    return tuple(
        binding
        for binding in ledger.bindings[: use.identity.join_position + 1]
        if project_join_binding_visible(
            binding, ledger.uses[: use.identity.join_position]
        )
    )


def project_join_blocking_bindings(
    ledger: ProjectRelationJoinUseLedger, use: ProjectNonConcreteJoinUse
) -> tuple[ProjectRelationBindingOccurrence, ...]:
    """Every visible earlier binding whose relation is not resolved, in binding
    order, while the JOIN's target is concrete: such a binding keeps a JOIN
    without `on` from naming the inputs it would match. Empty while the
    target is not concrete."""
    if use.target_binding.output is None:
        return ()
    return tuple(
        binding
        for binding in project_join_visible_bindings(ledger, use)
        if binding.output is None and binding.target is None
    )


def validate_project_join_input_bindings(
    roots: ProjectRelationshipUseSet, ledger: ProjectRelationJoinUseLedger
) -> None:
    """Rebind pre-match inputs to existing exact resolution/output authority."""
    if not any(ledger is retained for retained in roots.ledgers):
        raise ValueError("Pre-match bindings require their exact ledger.")
    resolutions = roots.semantic_result.module_relation_resolutions
    if resolutions is None:
        raise ValueError("Pre-match bindings require exact module resolutions.")
    environments = resolutions.find_module_path(ledger.owner.identity.module_path)
    if len(environments) != 1:
        raise ValueError("Pre-match bindings require one exact module environment.")
    names = tuple(binding.name for binding in ledger.bindings)
    catalogs = roots.semantic_result.module_catalogs
    local = (
        ()
        if catalogs is None
        else catalogs.find_module_path(ledger.owner.identity.module_path)
    )
    for position, binding in enumerate(ledger.bindings):
        expected = _binding(
            owner=ledger.owner,
            position=position,
            environment=environments[0],
            relational=roots.relational,
            duplicate=names.count(binding.name) > 1,
            catalog=local[0] if len(local) == 1 else None,
        )
        if (
            binding.target is not expected.target
            or binding.output is not expected.output
            or binding.state is not expected.state
            or len(binding.relation_issues) != len(expected.relation_issues)
            or any(
                actual is not retained
                for actual, retained in zip(
                    binding.relation_issues, expected.relation_issues, strict=True
                )
            )
        ):
            raise ValueError(
                "Pre-match binding must retain exact resolved input authority."
            )


def _build_use(
    *,
    owner: ProjectDeclarationOccurrence,
    position: int,
    bindings: tuple[ProjectRelationBindingOccurrence, ...],
    prior_uses: tuple[ProjectNonConcreteJoinUse, ...],
) -> ProjectNonConcreteJoinUse:
    definition = _derived_definition(owner)
    clause = definition.join_clauses[position]
    identity = ProjectJoinUseIdentity(
        owner=_owner_identity(owner), join_position=position
    )
    target = bindings[position + 1]
    issues: tuple[ProjectJoinUseIssue, ...]
    if unsupported_join(clause):
        issues = (_issue(ProjectJoinUseIssueKind.SYNTAX_UNSUPPORTED, clause),)
    elif target.state is not ProjectJoinUseState.CONCRETE:
        issues = (_target_issue(target, clause),)
    else:
        # An INNER or LEFT JOIN without `on`: it retains every earlier binding
        # it could have read, or every one whose relation is not resolved.
        visible = tuple(
            binding
            for binding in bindings[: position + 1]
            if project_join_binding_visible(binding, prior_uses)
        )
        blocking = tuple(
            binding
            for binding in visible
            if binding.output is None and binding.target is None
        )
        issues = (
            _issue(ProjectJoinUseIssueKind.BLOCKED_SOURCE_BINDING, clause, *blocking)
            if blocking
            else _issue(
                ProjectJoinUseIssueKind.UNKNOWN_SOURCE_BINDING, clause, *visible
            ),
        )
    return ProjectNonConcreteJoinUse(
        identity=identity,
        owner=owner,
        clause=clause,
        target_binding=target,
        state=_dominant_state(issues),
        issues=issues,
    )


def build_project_relationship_uses(
    semantic_result: ProjectSemanticResult,
    relational: ProjectIRRelationalPropertyStage,
) -> ProjectRelationshipUseSet:
    """Build complete authored JOIN uses without constructing joined row outputs."""

    catalogs = semantic_result.module_catalogs
    resolutions = semantic_result.module_relation_resolutions
    if catalogs is None or resolutions is None:
        raise ValueError("JOIN-use construction requires module resolution authority.")
    ledgers: list[ProjectRelationJoinUseLedger] = []
    for catalog in catalogs.catalogs:
        relation_environments = resolutions.find_module_path(catalog.module_path)
        if len(relation_environments) != 1:
            raise ValueError("JOIN-use module roots must be exact and complete.")
        relation_environment = relation_environments[0]
        for owner in catalog.relation_owners:
            if not _is_join_bearing(owner):
                continue
            definition = _derived_definition(owner)
            names = (
                definition.from_clause.binding_name
                or definition.from_clause.source_name,
                *(clause.target_binding_name for clause in definition.join_clauses),
            )
            duplicates = {name for name in names if names.count(name) > 1}
            bindings = tuple(
                _binding(
                    owner=owner,
                    position=position,
                    environment=relation_environment,
                    relational=relational,
                    duplicate=name in duplicates,
                    catalog=catalog,
                )
                for position, name in enumerate(names)
            )
            uses: list[ProjectNonConcreteJoinUse] = []
            for position in range(len(definition.join_clauses)):
                uses.append(
                    _build_use(
                        owner=owner,
                        position=position,
                        bindings=bindings,
                        prior_uses=tuple(uses),
                    )
                )
            ledgers.append(
                ProjectRelationJoinUseLedger(
                    owner=owner, bindings=bindings, uses=tuple(uses)
                )
            )
    return ProjectRelationshipUseSet(
        semantic_result=semantic_result,
        relational=relational,
        ledgers=tuple(ledgers),
    )
