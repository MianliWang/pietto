"""Private Phase-63 completion schedule and effective-output ledger foundation."""

from __future__ import annotations

from pietto.ast_nodes import SetRelationDef

from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_attribution import ProjectModuleAttributionFactSet
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_relation_resolution import (
    ProjectResolvedModuleRelationReference,
)
from pietto._project.project_ir_composition import ProjectIRProjectPlan
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
)
from pietto._project.project_ir_properties import ProjectIRRelationRowOutput
from pietto._project.project_ir_relational_properties import (
    ProjectIROutputRelationalProperties,
)
from pietto._project.project_joined_row_semantics import (
    ProjectConcreteJoinedRowSemantics,
    ProjectJoinedRowSemanticsResult,
    ProjectNonConcreteJoinedRowSemantics,
    build_project_joined_row_semantics,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
    ProjectPhase62VerificationStatus,
)
from pietto._project.project_query_block import (
    ProjectConcreteQueryBlock,
    ProjectNonConcreteQueryBlock,
    build_project_query_block_from_join_region,
)
from pietto._project.project_relationship_uses import (
    ProjectRelationBindingOccurrence,
)
from pietto._project.project_scalar_bindings import (
    build_project_joined_scalar_binding_environment,
)
from pietto._project.project_scalar_namespaces import (
    build_project_joined_let_namespaces,
)
from pietto._project.project_scalar_references import (
    ProjectConcreteScalarEnvironment,
    build_project_scalar_environment,
)
from pietto.ast_nodes import QueryDef, SourceDef, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletionDependency:
    """One exact retained relation-resolution or JOIN-binding dependency use."""

    consumer: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    target: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    dependency_ordinal: int
    evidence: (
        ProjectResolvedModuleRelationReference | ProjectRelationBindingOccurrence
    ) = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        if (
            type(self.consumer) is not ProjectDeclarationOccurrence
            or type(self.target) is not ProjectDeclarationOccurrence
            or type(self.dependency_ordinal) is not int
            or self.dependency_ordinal < 0
        ):
            raise TypeError("Completion dependency requires exact owners and ordinal.")
        if type(self.evidence) is ProjectResolvedModuleRelationReference:
            if (
                self.dependency_ordinal != 0
                or self.evidence.reference.owner is not self.consumer
                or self.evidence.target_symbol.target_occurrence is not self.target
            ):
                raise ValueError("Resolved completion dependency lost exact endpoints.")
        elif type(self.evidence) is ProjectRelationBindingOccurrence:
            target = self.evidence.target
            if (
                self.evidence.owner is not self.consumer
                or self.evidence.identity.binding_position != self.dependency_ordinal
                or target is None
                or target.target_occurrence is not self.target
            ):
                raise ValueError("JOIN completion dependency lost exact endpoints.")
        else:
            raise TypeError("Completion dependency requires retained use evidence.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectExistingEffectiveOutput:
    """One exact historically concrete relation-final output ledger entry."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    fragment: ProjectIRConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    output: ProjectIRRelationRowOutput
    properties: ProjectIROutputRelationalProperties
    dependencies: tuple[ProjectCompletionDependency, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.fragment) is not ProjectIRConcreteSingleRelationFragment
            or self.fragment.semantic_facts.owner is not self.owner
            or type(self.output) is not ProjectIRRelationRowOutput
            or self.output is not self.fragment.root_relation_output
            or type(self.properties) is not ProjectIROutputRelationalProperties
            or self.properties.output is not self.output
        ):
            raise ValueError("Existing effective output requires exact retained roots.")
        if type(self.dependencies) is not tuple or any(
            type(item) is not ProjectCompletionDependency
            or item.consumer is not self.owner
            for item in self.dependencies
        ):
            raise TypeError("Existing output dependencies must be exact occurrences.")


class ProjectEffectiveOutputTerminalReason(StrEnum):
    """Closed Slice-7 reasons for an absent current effective output."""

    DEPENDENCY_CYCLE = "dependency_cycle"
    UPSTREAM_DEPENDENCY_CYCLE = "upstream_dependency_cycle"
    JOINED_TAIL_PENDING = "joined_tail_pending"
    UPSTREAM_EFFECTIVE_OUTPUT_PENDING = "upstream_effective_output_pending"
    JOINED_COMPLETION_NON_CONCRETE = "joined_completion_non_concrete"
    HISTORICAL_NON_CONCRETE = "historical_non_concrete"
    EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED = "effective_upstream_join_unsupported"


type ProjectJoinedCompletionReadiness = (
    ProjectNonConcreteQueryBlock | ProjectJoinedRowSemanticsResult
)


def _joined_completion_owner(
    readiness: ProjectJoinedCompletionReadiness,
) -> ProjectDeclarationOccurrence:
    if type(readiness) is ProjectNonConcreteQueryBlock:
        return readiness.owner_bridge.owner
    if type(readiness) is ProjectConcreteJoinedRowSemantics:
        return readiness.namespaces.binding_environment.ledger.owner
    if type(readiness) is ProjectNonConcreteJoinedRowSemantics:
        return readiness.namespaces.binding_environment.ledger.owner
    raise TypeError("Joined readiness requires an exact published result.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletionCycle:
    """One exact SCC, all internal uses, and a bounded real-edge witness."""

    members: tuple[ProjectDeclarationOccurrence, ...]
    dependencies: tuple[ProjectCompletionDependency, ...]
    witness: tuple[ProjectCompletionDependency, ...]
    diagnostics: tuple[Diagnostic, ...]


def _cycle_components(
    owners: tuple[ProjectDeclarationOccurrence, ...],
    dependencies: tuple[ProjectCompletionDependency, ...],
    schedule: tuple[ProjectDeclarationOccurrence, ...],
) -> tuple[
    tuple[
        tuple[ProjectDeclarationOccurrence, ...],
        tuple[ProjectCompletionDependency, ...],
        tuple[ProjectCompletionDependency, ...],
    ],
    ...,
]:
    """Iterative Kosaraju on the exact unscheduled relation-use graph."""

    scheduled = {id(owner) for owner in schedule}
    remaining = {id(owner) for owner in owners} - scheduled
    adjacency = {key: [] for key in remaining}
    reverse = {key: [] for key in remaining}
    for edge in dependencies:
        source, target = id(edge.consumer), id(edge.target)
        if source in remaining and target in remaining:
            adjacency[source].append(edge)
            reverse[target].append(source)
    seen = set()
    finished = []
    for owner in owners:
        root = id(owner)
        if root not in remaining or root in seen:
            continue
        seen.add(root)
        stack = [(root, 0)]
        while stack:
            node, position = stack[-1]
            if position == len(adjacency[node]):
                finished.append(node)
                stack.pop()
                continue
            stack[-1] = (node, position + 1)
            target = id(adjacency[node][position].target)
            if target not in seen:
                seen.add(target)
                stack.append((target, 0))
    assigned = set()
    components = []
    for root in reversed(finished):
        if root in assigned:
            continue
        members = set()
        pending = [root]
        assigned.add(root)
        while pending:
            node = pending.pop()
            members.add(node)
            for source in reverse[node]:
                if source not in assigned:
                    assigned.add(source)
                    pending.append(source)
        internal = tuple(
            edge
            for edge in dependencies
            if id(edge.consumer) in members and id(edge.target) in members
        )
        if len(members) == 1 and not internal:
            continue
        canonical = tuple(owner for owner in owners if id(owner) in members)
        # The first internal edge starts at the canonical first member. BFS
        # finds one return path, without enumerating all simple cycles.
        first = internal[0]
        start, target = id(first.consumer), id(first.target)
        parents = {target: None}
        queue = deque((target,))
        while start not in parents:
            node = queue.popleft()
            for edge in adjacency[node]:
                child = id(edge.target)
                if child in members and child not in parents:
                    parents[child] = edge
                    queue.append(child)
        suffix = []
        node = start
        while node != target:
            edge = parents[node]
            if edge is None:
                raise AssertionError("Cycle witness lost its return path.")
            suffix.append(edge)
            node = id(edge.consumer)
        witness = (first, *reversed(suffix))
        components.append((canonical, internal, witness))
    order = {id(owner): position for position, owner in enumerate(owners)}
    return tuple(sorted(components, key=lambda item: order[id(item[0][0])]))


def _cycle_diagnostics(
    verification: ProjectPhase62VerificationResult,
    members: tuple[ProjectDeclarationOccurrence, ...],
    witness: tuple[ProjectCompletionDependency, ...],
) -> tuple[Diagnostic, ...]:
    semantic = verification.root.join_regions.uses.relationships.semantic_result
    resolutions = semantic.module_relation_resolutions
    if resolutions is None:
        raise ValueError("Completion cycle requires retained relation resolution.")
    member_ids = {id(owner) for owner in members}
    existing = tuple(
        issue.diagnostic
        for issue in resolutions.issues
        if issue.relation_cycle
        and {id(owner) for owner in issue.relation_cycle} <= member_ids
        and issue.diagnostic is not None
        and issue.diagnostic.code == "PIE-S2302"
    )
    if existing:
        return existing
    closing = witness[-1].evidence
    site = (
        closing.reference.from_clause
        if type(closing) is ProjectResolvedModuleRelationReference
        else cast(ProjectRelationBindingOccurrence, closing).site
    )
    span = site.span
    cross_module = len({owner.identity.module_path for owner in members}) > 1
    names = tuple(
        (f"{edge.consumer.identity.module_path}:" if cross_module else "")
        + edge.consumer.identity.declared_name
        for edge in witness
    )
    return (
        Diagnostic(
            code="PIE-S2302",
            severity=Severity.ERROR,
            message=f"Relation cycle detected: {' -> '.join((*names, names[0]))}",
            location=SourceLocation(
                path=span.path,
                line=span.line,
                column=span.column,
                end_line=span.end_line,
                end_column=span.end_column,
            ),
        ),
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletionTopology:
    """Derived relation topology; reporting blocked owners is not evaluation."""

    verification: ProjectPhase62VerificationResult = field(repr=False)
    owners: tuple[ProjectDeclarationOccurrence, ...] = field(init=False)
    dependencies: tuple[ProjectCompletionDependency, ...] = field(init=False)
    schedule: tuple[ProjectDeclarationOccurrence, ...] = field(init=False)
    cycles: tuple[ProjectCompletionCycle, ...] = field(init=False)
    blocked_owners: tuple[ProjectDeclarationOccurrence, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.verification) is not ProjectPhase62VerificationResult or (
            self.verification.status is not ProjectPhase62VerificationStatus.VERIFIED
        ):
            raise ValueError("Completion topology requires exact VERIFIED roots.")
        owners = tuple(
            fragment.semantic_facts.owner
            for fragment in self.verification.root.evaluation.project_plan.fragments
        )
        dependencies = _dependencies(self.verification)
        schedule = _schedule(owners, dependencies)
        cycles = tuple(
            ProjectCompletionCycle(
                members=members,
                dependencies=internal,
                witness=witness,
                diagnostics=_cycle_diagnostics(self.verification, members, witness),
            )
            for members, internal, witness in _cycle_components(
                owners, dependencies, schedule
            )
        )
        scheduled = {id(owner) for owner in schedule}
        for name, value in (
            ("owners", owners),
            ("dependencies", dependencies),
            ("schedule", schedule),
            ("cycles", cycles),
            (
                "blocked_owners",
                tuple(owner for owner in owners if id(owner) not in scheduled),
            ),
        ):
            object.__setattr__(self, name, value)

    def validate(self) -> None:
        """Read-only integrity check against retained dependency authority."""

        if type(self.verification) is not ProjectPhase62VerificationResult or (
            self.verification.status is not ProjectPhase62VerificationStatus.VERIFIED
        ):
            raise ValueError("Completion topology requires exact VERIFIED roots.")
        expected_owners = tuple(
            fragment.semantic_facts.owner
            for fragment in self.verification.root.evaluation.project_plan.fragments
        )
        expected_dependencies = _dependencies(self.verification)
        if not _same_objects(self.owners, expected_owners) or (
            type(self.dependencies) is not tuple
            or len(self.dependencies) != len(expected_dependencies)
            or any(
                type(edge) is not ProjectCompletionDependency
                or edge.consumer is not expected.consumer
                or edge.target is not expected.target
                or type(edge.dependency_ordinal) is not int
                or edge.dependency_ordinal != expected.dependency_ordinal
                or edge.evidence is not expected.evidence
                for edge, expected in zip(
                    self.dependencies, expected_dependencies, strict=True
                )
            )
        ):
            raise ValueError("Completion topology lost exact owner/use authority.")
        expected_schedule = _schedule(self.owners, self.dependencies)
        scheduled = {id(owner) for owner in expected_schedule}
        if not _same_objects(self.schedule, expected_schedule) or not _same_objects(
            self.blocked_owners,
            tuple(owner for owner in self.owners if id(owner) not in scheduled),
        ):
            raise ValueError("Completion topology lost its exact acyclic schedule.")
        components = _cycle_components(self.owners, self.dependencies, self.schedule)
        if type(self.cycles) is not tuple or len(self.cycles) != len(components):
            raise ValueError("Completion topology lost a cyclic component.")
        for cycle, (members, internal, witness) in zip(
            self.cycles, components, strict=True
        ):
            if type(cycle) is not ProjectCompletionCycle or not all(
                (
                    _same_objects(cycle.members, members),
                    _same_objects(cycle.dependencies, internal),
                    _same_objects(cycle.witness, witness),
                )
            ):
                raise ValueError("Completion cycle lost canonical member/use evidence.")
            expected = _cycle_diagnostics(self.verification, members, witness)
            if (
                type(cycle.diagnostics) is not tuple
                or cycle.diagnostics != expected
                or any(
                    actual is not retained
                    for actual, retained in zip(
                        cycle.diagnostics, expected, strict=True
                    )
                    if any(
                        retained is item
                        for item in self.verification.root.join_regions.uses.relationships.semantic_result.diagnostics
                    )
                )
            ):
                raise ValueError("Completion cycle lost its precise diagnostics.")

    def causes(
        self,
        owner: ProjectDeclarationOccurrence,
    ) -> tuple[
        tuple[ProjectCompletionCycle, ...], tuple[ProjectCompletionDependency, ...]
    ]:
        if not any(owner is retained for retained in self.blocked_owners):
            raise ValueError("Cycle blocker requires an exact blocked owner.")
        blocked = {id(item) for item in self.blocked_owners}
        outgoing: dict[int, list[ProjectCompletionDependency]] = {}
        for edge in self.dependencies:
            if id(edge.target) in blocked:
                outgoing.setdefault(id(edge.consumer), []).append(edge)
        reachable = {id(owner)}
        queue = deque((owner,))
        while queue:
            current = queue.popleft()
            for edge in outgoing.get(id(current), ()):
                target = id(edge.target)
                if target not in reachable:
                    reachable.add(target)
                    queue.append(edge.target)
        return (
            tuple(cycle for cycle in self.cycles if id(cycle.members[0]) in reachable),
            tuple(
                edge
                for edge in self.dependencies
                if id(edge.consumer) in reachable and id(edge.target) in blocked
            ),
        )


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(
            item is retained for item, retained in zip(actual, expected, strict=True)
        )
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletionCycleBlocker:
    """Non-recursive cause references for a cycle member or affected dependent."""

    topology: ProjectCompletionTopology = field(repr=False)
    owner: ProjectDeclarationOccurrence = field(repr=False)
    cycles: tuple[ProjectCompletionCycle, ...] = field(init=False)
    dependencies: tuple[ProjectCompletionDependency, ...] = field(init=False)
    is_cycle_member: bool = field(init=False)

    def __post_init__(self) -> None:
        if type(self.topology) is not ProjectCompletionTopology:
            raise TypeError("Cycle blocker requires exact topology authority.")
        cycles, dependencies = self.topology.causes(self.owner)
        object.__setattr__(self, "cycles", cycles)
        object.__setattr__(self, "dependencies", dependencies)
        object.__setattr__(
            self,
            "is_cycle_member",
            any(self.owner is member for cycle in cycles for member in cycle.members),
        )

    def validate(self) -> None:
        cycles, dependencies = self.topology.causes(self.owner)
        if (
            not _same_objects(self.cycles, cycles)
            or not _same_objects(self.dependencies, dependencies)
            or (
                self.is_cycle_member
                is not any(
                    self.owner is member for cycle in cycles for member in cycle.members
                )
            )
        ):
            raise ValueError("Cycle blocker lost complete canonical causes.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectEffectiveOutputTerminal:
    """One exact non-concrete effective-output ledger entry with no output."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    fragment: ProjectIRNonConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectEffectiveOutputTerminalReason
    dependencies: tuple[ProjectCompletionDependency, ...] = ()
    joined_completion: ProjectJoinedCompletionReadiness | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    resolution: ProjectResolvedModuleRelationReference | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    pending_dependencies: tuple[ProjectCompletionDependency, ...] = ()
    pending_entries: tuple[ProjectEffectiveOutputTerminal, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    cycle_blocker: ProjectCompletionCycleBlocker | None = field(
        default=None, repr=False
    )
    output: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.fragment) is not ProjectIRNonConcreteSingleRelationFragment
            or self.fragment.semantic_facts.owner is not self.owner
            or type(self.reason) is not ProjectEffectiveOutputTerminalReason
        ):
            raise ValueError("Effective-output terminal requires exact owner roots.")
        if type(self.dependencies) is not tuple or any(
            type(item) is not ProjectCompletionDependency
            or item.consumer is not self.owner
            for item in self.dependencies
        ):
            raise TypeError("Terminal dependencies must be exact occurrences.")
        if (
            type(self.pending_dependencies) is not tuple
            or type(self.pending_entries) is not tuple
            or len(self.pending_dependencies) != len(self.pending_entries)
            or any(
                type(entry) is not ProjectEffectiveOutputTerminal
                or entry.reason not in _RECOVERABLE_PENDING_REASONS
                for entry in self.pending_entries
            )
            or any(
                dependency not in self.dependencies
                or entry.owner is not dependency.target
                for dependency, entry in zip(
                    self.pending_dependencies,
                    self.pending_entries,
                    strict=True,
                )
            )
        ):
            raise ValueError("Pending entries must retain exact dependency evidence.")

        if self.reason in {
            ProjectEffectiveOutputTerminalReason.DEPENDENCY_CYCLE,
            ProjectEffectiveOutputTerminalReason.UPSTREAM_DEPENDENCY_CYCLE,
        }:
            blocker = self.cycle_blocker
            if (
                type(blocker) is not ProjectCompletionCycleBlocker
                or blocker.owner is not self.owner
            ):
                raise ValueError("Cycle terminal requires exact owner-local causes.")
            blocker.validate()
            if (
                self.reason is ProjectEffectiveOutputTerminalReason.DEPENDENCY_CYCLE
            ) is not blocker.is_cycle_member or any(
                (
                    self.joined_completion is not None,
                    self.resolution is not None,
                    bool(self.pending_dependencies),
                    bool(self.pending_entries),
                )
            ):
                raise ValueError("Cycle terminal cannot invent evaluation or replay.")
            return
        if self.cycle_blocker is not None:
            raise ValueError("Acyclic terminal cannot acquire cycle evidence.")

        if self.reason is ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING:
            if (
                type(self.joined_completion) is not ProjectConcreteJoinedRowSemantics
                or _joined_completion_owner(self.joined_completion) is not self.owner
                or self.resolution is not None
                or self.pending_dependencies
            ):
                raise ValueError("Joined-tail terminal requires exact readiness only.")
        elif (
            self.reason
            is ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
        ):
            if (
                type(self.joined_completion)
                not in {
                    ProjectNonConcreteQueryBlock,
                    ProjectNonConcreteJoinedRowSemantics,
                }
                or (
                    self.joined_completion is not None
                    and _joined_completion_owner(self.joined_completion)
                    is not self.owner
                )
                or any((self.resolution is not None, bool(self.pending_dependencies)))
            ):
                raise ValueError("Joined completion terminal requires one blocker.")
        elif (
            self.reason
            is ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING
        ):
            if (
                type(self.resolution) is not ProjectResolvedModuleRelationReference
                or self.fragment.semantic_facts.resolution is not self.resolution
                or len(self.pending_dependencies) != 1
                or self.pending_dependencies[0].evidence is not self.resolution
                or self.joined_completion is not None
            ):
                raise ValueError("Propagation terminal requires one exact upstream.")
        elif (
            self.reason
            is ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED
        ):
            definition = self.owner.definition
            if (
                type(definition) not in {TableDef, QueryDef}
                or not cast(TableDef | QueryDef, definition).join_clauses
                or not self.pending_dependencies
                or self.joined_completion is not None
                or self.resolution is not None
            ):
                raise ValueError("Unsupported effective JOIN requires pending inputs.")
        elif any(
            (
                self.joined_completion is not None,
                self.resolution is not None,
                bool(self.pending_dependencies),
            )
        ):
            raise ValueError("Historical terminal cannot invent completion evidence.")


type ProjectEffectiveOutputEntry = (
    ProjectExistingEffectiveOutput | ProjectEffectiveOutputTerminal
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectCompletion:
    """Snapshot-local exact owner schedule and canonical effective-output ledger."""

    verification: ProjectPhase62VerificationResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    plan: ProjectIRProjectPlan = field(repr=False, compare=False, hash=False)
    owners: tuple[ProjectDeclarationOccurrence, ...]
    dependencies: tuple[ProjectCompletionDependency, ...]
    schedule: tuple[ProjectDeclarationOccurrence, ...]
    entries: tuple[ProjectEffectiveOutputEntry, ...]
    topology: ProjectCompletionTopology = field(repr=False)

    def __post_init__(self) -> None:
        if (
            type(self.verification) is not ProjectPhase62VerificationResult
            or self.verification.status is not ProjectPhase62VerificationStatus.VERIFIED
            or type(self.plan) is not ProjectIRProjectPlan
            or self.verification.root.evaluation.project_plan is not self.plan
        ):
            raise ValueError("Completion requires exact VERIFIED Project-plan roots.")
        expected_owners = tuple(
            fragment.semantic_facts.owner for fragment in self.plan.fragments
        )
        if len(self.owners) != len(expected_owners) or any(
            owner is not expected
            for owner, expected in zip(self.owners, expected_owners, strict=True)
        ):
            raise ValueError("Completion owners must retain canonical fragment order.")
        owner_ids = {id(owner) for owner in self.owners}
        if (
            type(self.dependencies) is not tuple
            or any(
                type(item) is not ProjectCompletionDependency
                for item in self.dependencies
            )
            or len(owner_ids) != len(self.owners)
            or any(
                id(item.consumer) not in owner_ids or id(item.target) not in owner_ids
                for item in self.dependencies
            )
        ):
            raise ValueError("Completion dependencies require exact inventory owners.")
        expected_dependencies = tuple(
            dependency
            for owner in self.owners
            for dependency in self.dependencies
            if dependency.consumer is owner
        )
        if self.dependencies != expected_dependencies or any(
            tuple(
                dependency.dependency_ordinal
                for dependency in self.dependencies
                if dependency.consumer is owner
            )
            != tuple(
                sorted(
                    dependency.dependency_ordinal
                    for dependency in self.dependencies
                    if dependency.consumer is owner
                )
            )
            for owner in self.owners
        ):
            raise ValueError("Completion dependencies must retain canonical order.")
        if type(self.topology) is not ProjectCompletionTopology or (
            self.topology.verification is not self.verification
            or self.owners is not self.topology.owners
            or self.dependencies is not self.topology.dependencies
            or self.schedule is not self.topology.schedule
        ):
            raise ValueError("Completion requires exact retained topology authority.")
        self.topology.validate()
        if len(self.entries) != len(self.owners) or any(
            type(entry)
            not in {
                ProjectExistingEffectiveOutput,
                ProjectEffectiveOutputTerminal,
            }
            or entry.owner is not owner
            or entry.dependencies
            != tuple(item for item in self.dependencies if item.consumer is owner)
            for entry, owner in zip(self.entries, self.owners, strict=True)
        ):
            raise ValueError("Completion ledger requires exactly one entry per owner.")

        blocked = {id(owner) for owner in self.topology.blocked_owners}
        for entry in self.entries:
            if id(entry.owner) in blocked:
                if type(entry) is not ProjectEffectiveOutputTerminal or (
                    type(entry.cycle_blocker) is not ProjectCompletionCycleBlocker
                    or entry.cycle_blocker.topology is not self.topology
                ):
                    raise ValueError("Blocked owner must retain its cycle terminal.")
                entry.__post_init__()
            elif (
                type(entry) is ProjectEffectiveOutputTerminal
                and entry.cycle_blocker is not None
            ):
                raise ValueError("Scheduled owner cannot be cycle-blocked.")

    def find_owner(
        self,
        owner: ProjectDeclarationOccurrence,
    ) -> tuple[ProjectEffectiveOutputEntry, ...]:
        """Return one exact owner entry without retaining a normative name index."""

        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Completion lookup requires an exact owner occurrence.")
        return tuple(entry for entry in self.entries if entry.owner is owner)


_RECOVERABLE_PENDING_REASONS = frozenset(
    {
        ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING,
        ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING,
    }
)


def _dependencies(
    verification: ProjectPhase62VerificationResult,
) -> tuple[ProjectCompletionDependency, ...]:
    plan = verification.root.evaluation.project_plan
    ledgers = verification.root.join_regions.uses.ledgers
    dependencies: list[ProjectCompletionDependency] = []
    for fragment in plan.fragments:
        owner = fragment.semantic_facts.owner
        definition = owner.definition
        if type(definition) in {SourceDef, SetRelationDef}:
            continue
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Completion inventory requires relation-producing owners.")
        derived = cast(TableDef | QueryDef, definition)
        if derived.join_clauses:
            matches = tuple(ledger for ledger in ledgers if ledger.owner is owner)
            if len(matches) != 1:
                raise ValueError("JOIN owner requires one exact retained use ledger.")
            for binding in matches[0].bindings:
                if binding.target is None:
                    continue
                dependencies.append(
                    ProjectCompletionDependency(
                        consumer=owner,
                        target=binding.target.target_occurrence,
                        dependency_ordinal=binding.identity.binding_position,
                        evidence=binding,
                    )
                )
            continue
        resolution = fragment.semantic_facts.resolution
        if resolution is not None:
            dependencies.append(
                ProjectCompletionDependency(
                    consumer=owner,
                    target=resolution.target_symbol.target_occurrence,
                    dependency_ordinal=0,
                    evidence=resolution,
                )
            )
    return tuple(dependencies)


def _schedule(
    owners: tuple[ProjectDeclarationOccurrence, ...],
    dependencies: tuple[ProjectCompletionDependency, ...],
) -> tuple[ProjectDeclarationOccurrence, ...]:
    positions = {id(owner): position for position, owner in enumerate(owners)}
    if len(positions) != len(owners):
        raise ValueError("Completion inventory owners must be occurrence-unique.")
    indegree = [0 for _owner in owners]
    successors: list[list[int]] = [[] for _owner in owners]
    for dependency in dependencies:
        consumer = positions.get(id(dependency.consumer))
        target = positions.get(id(dependency.target))
        if consumer is None or target is None:
            raise ValueError("Completion dependency is outside the owner inventory.")
        indegree[consumer] += 1
        successors[target].append(consumer)
    ready = deque(position for position, degree in enumerate(indegree) if degree == 0)
    ordered: list[ProjectDeclarationOccurrence] = []
    while ready:
        position = ready.popleft()
        ordered.append(owners[position])
        for successor in successors[position]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    return tuple(ordered)


def _existing_entry(
    verification: ProjectPhase62VerificationResult,
    fragment: ProjectIRConcreteSingleRelationFragment,
    dependencies: tuple[ProjectCompletionDependency, ...],
) -> ProjectExistingEffectiveOutput:
    matches = tuple(
        item
        for item in verification.root.base_relational.outputs
        if item.output is fragment.root_relation_output
    )
    if len(matches) != 1:
        raise ValueError("Existing output requires one exact relational property.")
    return ProjectExistingEffectiveOutput(
        owner=fragment.semantic_facts.owner,
        fragment=fragment,
        output=fragment.root_relation_output,
        properties=matches[0],
        dependencies=dependencies,
    )


def _joined_completion(
    verification: ProjectPhase62VerificationResult,
    fragment: ProjectIRNonConcreteSingleRelationFragment,
) -> ProjectJoinedCompletionReadiness:
    owner = fragment.semantic_facts.owner
    regions = tuple(
        region
        for region in verification.root.join_regions.regions
        if region.ledger.owner is owner
    )
    if len(regions) != 1:
        raise ValueError("JOIN completion requires one exact Phase-62 region.")
    query_block = build_project_query_block_from_join_region(
        compilation_mode=ProjectCompilationMode.EXPLICIT_MODULES,
        owner=owner,
        verification=verification,
        region=regions[0],
    )
    return build_project_joined_completion(
        query_block, verification.root.evaluation.project_plan.attribution
    )


def build_project_joined_completion(
    query_block: ProjectConcreteQueryBlock | ProjectNonConcreteQueryBlock,
    attribution: ProjectModuleAttributionFactSet,
) -> ProjectJoinedCompletionReadiness:
    """Apply the existing scalar/binding/LET/row bridges to one exact block."""
    if type(query_block) is ProjectNonConcreteQueryBlock:
        return query_block
    if type(query_block) is not ProjectConcreteQueryBlock:
        raise AssertionError("JOIN completion lost its query-block result variant")
    scalar_environment = build_project_scalar_environment(query_block)
    if type(scalar_environment) is not ProjectConcreteScalarEnvironment:
        raise AssertionError("Concrete JOIN lost its scalar environment")
    binding_environment = build_project_joined_scalar_binding_environment(
        scalar_environment
    )
    namespaces = build_project_joined_let_namespaces(binding_environment)
    return build_project_joined_row_semantics(
        namespaces=namespaces,
        attribution=attribution,
    )


def _terminal_entry(
    *,
    verification: ProjectPhase62VerificationResult,
    fragment: ProjectIRNonConcreteSingleRelationFragment,
    dependencies: tuple[ProjectCompletionDependency, ...],
    upstream_entries: tuple[ProjectEffectiveOutputEntry, ...],
) -> ProjectEffectiveOutputTerminal:
    owner = fragment.semantic_facts.owner
    definition = owner.definition
    pending_pairs = tuple(
        (dependency, entry)
        for dependency, entry in zip(
            dependencies,
            upstream_entries,
            strict=True,
        )
        if type(entry) is ProjectEffectiveOutputTerminal
        and entry.reason in _RECOVERABLE_PENDING_REASONS
    )
    pending_dependencies = tuple(item[0] for item in pending_pairs)
    pending_entries = tuple(item[1] for item in pending_pairs)
    if (
        type(definition) in {TableDef, QueryDef}
        and cast(TableDef | QueryDef, definition).join_clauses
    ):
        if pending_pairs:
            return ProjectEffectiveOutputTerminal(
                owner=owner,
                fragment=fragment,
                reason=(
                    ProjectEffectiveOutputTerminalReason.EFFECTIVE_UPSTREAM_JOIN_UNSUPPORTED
                ),
                dependencies=dependencies,
                pending_dependencies=pending_dependencies,
                pending_entries=pending_entries,
            )
        completion = _joined_completion(verification, fragment)
        return ProjectEffectiveOutputTerminal(
            owner=owner,
            fragment=fragment,
            reason=(
                ProjectEffectiveOutputTerminalReason.JOINED_TAIL_PENDING
                if type(completion) is ProjectConcreteJoinedRowSemantics
                else ProjectEffectiveOutputTerminalReason.JOINED_COMPLETION_NON_CONCRETE
            ),
            dependencies=dependencies,
            joined_completion=completion,
        )
    semantic = fragment.semantic_facts
    if (
        type(definition) in {TableDef, QueryDef}
        and semantic.state.status is ProjectRelationRowSchemaStatus.DEFERRED
        and semantic.state.reason is ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED
        and type(semantic.resolution) is ProjectResolvedModuleRelationReference
        and len(pending_pairs) == 1
        and len(dependencies) == 1
    ):
        return ProjectEffectiveOutputTerminal(
            owner=owner,
            fragment=fragment,
            reason=ProjectEffectiveOutputTerminalReason.UPSTREAM_EFFECTIVE_OUTPUT_PENDING,
            dependencies=dependencies,
            resolution=semantic.resolution,
            pending_dependencies=pending_dependencies,
            pending_entries=pending_entries,
        )
    return ProjectEffectiveOutputTerminal(
        owner=owner,
        fragment=fragment,
        reason=ProjectEffectiveOutputTerminalReason.HISTORICAL_NON_CONCRETE,
        dependencies=dependencies,
    )


def build_project_completion(
    verification: ProjectPhase62VerificationResult,
) -> ProjectCompletion:
    """Build one dependency-first schedule and canonical effective-output ledger."""

    if type(verification) is not ProjectPhase62VerificationResult or (
        verification.status is not ProjectPhase62VerificationStatus.VERIFIED
    ):
        raise ValueError("Completion requires an exact VERIFIED Phase-62 root.")
    plan = verification.root.evaluation.project_plan
    topology = ProjectCompletionTopology(verification=verification)
    owners = topology.owners
    dependencies = topology.dependencies
    schedule = topology.schedule
    fragments = {
        id(fragment.semantic_facts.owner): fragment for fragment in plan.fragments
    }
    dependencies_by_owner = {
        id(owner): tuple(item for item in dependencies if item.consumer is owner)
        for owner in owners
    }
    built_by_owner: dict[int, ProjectEffectiveOutputEntry] = {}
    for owner in topology.blocked_owners:
        fragment = fragments[id(owner)]
        if type(fragment) is not ProjectIRNonConcreteSingleRelationFragment:
            raise ValueError(
                "Cyclic dependency cannot have a concrete historical root."
            )
        blocker = ProjectCompletionCycleBlocker(topology=topology, owner=owner)
        built_by_owner[id(owner)] = ProjectEffectiveOutputTerminal(
            owner=owner,
            fragment=fragment,
            reason=(
                ProjectEffectiveOutputTerminalReason.DEPENDENCY_CYCLE
                if blocker.is_cycle_member
                else ProjectEffectiveOutputTerminalReason.UPSTREAM_DEPENDENCY_CYCLE
            ),
            dependencies=dependencies_by_owner[id(owner)],
            cycle_blocker=blocker,
        )
    for owner in schedule:
        fragment = fragments[id(owner)]
        owner_dependencies = dependencies_by_owner[id(owner)]
        upstream_entries = tuple(
            built_by_owner[id(dependency.target)] for dependency in owner_dependencies
        )
        if type(fragment) is ProjectIRConcreteSingleRelationFragment:
            entry: ProjectEffectiveOutputEntry = _existing_entry(
                verification,
                fragment,
                owner_dependencies,
            )
        elif type(fragment) is ProjectIRNonConcreteSingleRelationFragment:
            entry = _terminal_entry(
                verification=verification,
                fragment=fragment,
                dependencies=owner_dependencies,
                upstream_entries=upstream_entries,
            )
        else:
            raise AssertionError("Project plan lost its exact fragment variant")
        built_by_owner[id(owner)] = entry
    entries = tuple(built_by_owner[id(owner)] for owner in owners)
    return ProjectCompletion(
        verification=verification,
        plan=plan,
        owners=owners,
        dependencies=dependencies,
        schedule=schedule,
        entries=entries,
        topology=topology,
    )
