"""Private Project relationship occurrences over existing module authority."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._project.model import ProjectSemanticResult
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionEnvironment,
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionIssueStatus,
    ProjectResolvedModuleRelationSymbol,
)
from pietto.ast_nodes import (
    Definition,
    RelationshipEndpoint,
    RelationshipMetadata,
    Span,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.semantic.model import (
    RelationshipSemanticEndpointInfo,
    RelationshipSemanticInfo,
)
from pietto.semantic.relationship_metadata import check_relationship_metadata

__all__: tuple[str, ...] = ()

_AMBIGUOUS_RELATION_ISSUES = frozenset(
    {ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME}
)
_BLOCKED_RELATION_ISSUES = frozenset(
    {
        ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
        ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
        ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
    }
)
_RELATIONSHIP_RESOLUTION_ISSUES = _AMBIGUOUS_RELATION_ISSUES | _BLOCKED_RELATION_ISSUES


class ProjectRelationshipConstructionState(StrEnum):
    """Closed availability states for one Project relationship occurrence."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    AMBIGUOUS = "ambiguous"


def _require_position(value: object, label: str, *, maximum: int | None = None) -> None:
    if type(value) is not int or value < 0 or (maximum is not None and value > maximum):
        raise ValueError(f"{label} must be an exact non-negative position.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipDeclarationIdentity:
    """Nominal identity of one module-owned relationship declaration occurrence."""

    module: ProjectModuleIdentity
    module_position: int
    relationship_position: int

    def __post_init__(self) -> None:
        if type(self.module) is not ProjectModuleIdentity:
            raise TypeError("Relationship identity requires a module identity.")
        _require_position(self.module_position, "Relationship module position")
        _require_position(
            self.relationship_position,
            "Relationship declaration position",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipEndpointIdentity:
    """Identity of one endpoint subordinate to one declaration occurrence."""

    declaration: ProjectRelationshipDeclarationIdentity
    endpoint_position: int

    def __post_init__(self) -> None:
        if type(self.declaration) is not ProjectRelationshipDeclarationIdentity:
            raise TypeError("Endpoint identity requires a relationship identity.")
        _require_position(
            self.endpoint_position,
            "Relationship endpoint position",
            maximum=1,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipEndpointOccurrence:
    """One authored endpoint plus exact Project and semantic provenance."""

    identity: ProjectRelationshipEndpointIdentity
    endpoint: RelationshipEndpoint = field(repr=False, compare=False, hash=False)
    target: ProjectResolvedModuleRelationSymbol | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    semantic: RelationshipSemanticEndpointInfo | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipEndpointIdentity:
            raise TypeError("Endpoint occurrence requires an endpoint identity.")
        if type(self.endpoint) is not RelationshipEndpoint:
            raise TypeError("Endpoint occurrence requires an authored endpoint.")
        target = self.target
        if target is not None:
            if type(target) is not ProjectResolvedModuleRelationSymbol:
                raise TypeError("Endpoint target requires an exact relation symbol.")
            if (
                target.owning_module_path != self.identity.declaration.module.path
                or target.local_name != self.endpoint.relation_name
            ):
                raise ValueError("Endpoint target must use declaring-module authority.")
        semantic = self.semantic
        if semantic is not None:
            if type(semantic) is not RelationshipSemanticEndpointInfo:
                raise TypeError("Endpoint semantic provenance has the wrong type.")
            if (
                target is None
                or semantic.local_name != self.endpoint.local_name
                or semantic.relation_name != self.endpoint.relation_name
                or semantic.relation is not target.target_occurrence.definition
            ):
                raise ValueError("Endpoint semantic provenance must match its target.")

    @property
    def authored_role(self) -> str:
        """Return the authored endpoint-local role without interpreting it."""

        return self.endpoint.local_name

    @property
    def authored_relation_spelling(self) -> str:
        """Return the exact authored relation spelling."""

        return self.endpoint.relation_name

    @property
    def span(self) -> Span:
        """Return the exact authored endpoint span."""

        return self.endpoint.span


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipDeclarationOccurrence:
    """One complete authored declaration and its two endpoint occurrences."""

    identity: ProjectRelationshipDeclarationIdentity
    module: ProjectLogicalModule = field(repr=False, compare=False, hash=False)
    relationship: RelationshipMetadata = field(
        repr=False,
        compare=False,
        hash=False,
    )
    endpoints: tuple[
        ProjectRelationshipEndpointOccurrence,
        ProjectRelationshipEndpointOccurrence,
    ]
    semantic: RelationshipSemanticInfo | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectRelationshipDeclarationIdentity:
            raise TypeError("Relationship occurrence requires an exact identity.")
        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Relationship occurrence requires a logical module.")
        if (
            self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.module.parsed_input is None
            or self.module.identity != self.identity.module
            or self.module.position != self.identity.module_position
        ):
            raise ValueError("Relationship occurrence requires its declaring module.")
        if type(self.relationship) is not RelationshipMetadata:
            raise TypeError("Relationship occurrence requires authored metadata.")
        relationships = self.module.parsed_input.script.relationships
        if (
            self.identity.relationship_position >= len(relationships)
            or relationships[self.identity.relationship_position]
            is not self.relationship
        ):
            raise ValueError("Relationship occurrence must retain exact source order.")
        if type(self.endpoints) is not tuple or len(self.endpoints) != 2:
            raise TypeError("Relationship occurrence requires exactly two endpoints.")
        for position, (occurrence, endpoint) in enumerate(
            zip(self.endpoints, self.relationship.endpoints, strict=True)
        ):
            if (
                type(occurrence) is not ProjectRelationshipEndpointOccurrence
                or occurrence.identity.declaration != self.identity
                or occurrence.identity.endpoint_position != position
                or occurrence.endpoint is not endpoint
            ):
                raise ValueError("Relationship endpoints must retain source order.")
        semantic = self.semantic
        if semantic is None:
            if any(endpoint.semantic is not None for endpoint in self.endpoints):
                raise ValueError("Endpoint semantics require declaration semantics.")
            return
        if type(semantic) is not RelationshipSemanticInfo:
            raise TypeError("Relationship semantic provenance has the wrong type.")
        if semantic.name != self.relationship.name:
            raise ValueError("Relationship semantic name must match authored metadata.")
        if any(
            endpoint.semantic is not semantic_endpoint
            for endpoint, semantic_endpoint in zip(
                self.endpoints,
                semantic.endpoints,
                strict=True,
            )
        ):
            raise ValueError("Relationship semantic endpoints must be exact objects.")

    @property
    def name(self) -> str:
        """Return the authored name without using it as identity."""

        return self.relationship.name


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectConcreteRelationshipSubject:
    """One concrete relationship with semantic and endpoint target authority."""

    occurrence: ProjectRelationshipDeclarationOccurrence

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectRelationshipDeclarationOccurrence:
            raise TypeError("Concrete relationship requires an occurrence.")
        if self.occurrence.semantic is None or any(
            endpoint.target is None or endpoint.semantic is None
            for endpoint in self.occurrence.endpoints
        ):
            raise ValueError("Concrete relationship requires complete exact evidence.")

    @property
    def state(self) -> ProjectRelationshipConstructionState:
        return ProjectRelationshipConstructionState.CONCRETE


def _inferred_non_concrete_state(
    occurrence: ProjectRelationshipDeclarationOccurrence,
    diagnostics: tuple[Diagnostic, ...],
    relation_issues: tuple[ProjectModuleRelationResolutionIssue, ...],
) -> ProjectRelationshipConstructionState | None:
    codes = {diagnostic.code for diagnostic in diagnostics}
    issue_statuses = {issue.status for issue in relation_issues}
    if "PIE-S2602" in codes or issue_statuses & _AMBIGUOUS_RELATION_ISSUES:
        return ProjectRelationshipConstructionState.AMBIGUOUS
    if "PIE-S2603" in codes or issue_statuses & _BLOCKED_RELATION_ISSUES:
        return ProjectRelationshipConstructionState.BLOCKED
    if "PIE-S2601" in codes or any(
        endpoint.target is None for endpoint in occurrence.endpoints
    ):
        return ProjectRelationshipConstructionState.UNKNOWN
    return None


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNonConcreteRelationshipSubject:
    """One typed relationship terminal without a fake concrete occurrence."""

    occurrence: ProjectRelationshipDeclarationOccurrence
    state: ProjectRelationshipConstructionState
    diagnostics: tuple[Diagnostic, ...] = ()
    relation_issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.occurrence) is not ProjectRelationshipDeclarationOccurrence:
            raise TypeError("Non-concrete relationship requires an occurrence.")
        if type(self.state) is not ProjectRelationshipConstructionState:
            raise TypeError("Non-concrete relationship requires an exact state.")
        if self.state is ProjectRelationshipConstructionState.CONCRETE:
            raise ValueError("Non-concrete relationship cannot claim CONCRETE.")
        if self.occurrence.semantic is not None:
            raise ValueError(
                "Non-concrete relationship cannot retain admitted semantics."
            )
        if type(self.diagnostics) is not tuple or any(
            type(item) is not Diagnostic for item in self.diagnostics
        ):
            raise TypeError("Relationship diagnostics must be an exact tuple.")
        if type(self.relation_issues) is not tuple or any(
            type(item) is not ProjectModuleRelationResolutionIssue
            for item in self.relation_issues
        ):
            raise TypeError("Relationship relation issues must be an exact tuple.")
        relationship_span = self.occurrence.relationship.span
        if any(
            not _span_contains(diagnostic.location, relationship_span)
            for diagnostic in self.diagnostics
        ):
            raise ValueError("Relationship diagnostics must belong to the occurrence.")
        missing_names = {
            endpoint.authored_relation_spelling
            for endpoint in self.occurrence.endpoints
            if endpoint.target is None
        }
        if any(
            issue.owning_module_path != self.occurrence.module.path
            or issue.local_name not in missing_names
            or issue.status not in _RELATIONSHIP_RESOLUTION_ISSUES
            for issue in self.relation_issues
        ):
            raise ValueError("Relationship issues must belong to unresolved endpoints.")
        if self.state is ProjectRelationshipConstructionState.DEFERRED:
            raise ValueError("Slice 2 has no reachable DEFERRED relationship evidence.")
        inferred = _inferred_non_concrete_state(
            self.occurrence,
            self.diagnostics,
            self.relation_issues,
        )
        if inferred is not self.state:
            raise ValueError("Relationship evidence does not support its state.")


type ProjectRelationshipSubject = (
    ProjectConcreteRelationshipSubject | ProjectNonConcreteRelationshipSubject
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationshipEnvironment:
    """Complete source-ordered relationships owned by one exact module."""

    module: ProjectLogicalModule = field(repr=False, compare=False, hash=False)
    relation_environment: ProjectModuleRelationResolutionEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_relationships: tuple[RelationshipSemanticInfo, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_diagnostics: tuple[Diagnostic, ...] = ()
    subjects: tuple[ProjectRelationshipSubject, ...] = ()

    def __post_init__(self) -> None:
        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Relationship environment requires a logical module.")
        if (
            type(self.relation_environment)
            is not ProjectModuleRelationResolutionEnvironment
        ):
            raise TypeError("Relationship environment requires relation authority.")
        if self.relation_environment.module is not self.module:
            raise ValueError("Relationship environment roots must share one module.")
        if type(self.semantic_relationships) is not tuple or any(
            type(item) is not RelationshipSemanticInfo
            for item in self.semantic_relationships
        ):
            raise TypeError("Semantic relationships must be an exact tuple.")
        if type(self.semantic_diagnostics) is not tuple or any(
            type(item) is not Diagnostic for item in self.semantic_diagnostics
        ):
            raise TypeError("Semantic diagnostics must be an exact tuple.")
        if type(self.subjects) is not tuple or any(
            type(item)
            not in {
                ProjectConcreteRelationshipSubject,
                ProjectNonConcreteRelationshipSubject,
            }
            for item in self.subjects
        ):
            raise TypeError("Relationship subjects must be an exact typed tuple.")
        assert self.module.parsed_input is not None
        relationships = self.module.parsed_input.script.relationships
        if len(self.subjects) != len(relationships):
            raise ValueError("Relationship subjects must retain every declaration.")
        for position, (subject, relationship) in enumerate(
            zip(self.subjects, relationships, strict=True)
        ):
            occurrence = subject.occurrence
            if (
                occurrence.module is not self.module
                or occurrence.identity.relationship_position != position
                or occurrence.relationship is not relationship
            ):
                raise ValueError("Relationship subjects must retain source order.")
            for endpoint in occurrence.endpoints:
                bucket = self.relation_environment.find_relation_name(
                    endpoint.authored_relation_spelling
                )
                if endpoint.target is None:
                    if bucket:
                        raise ValueError(
                            "Unresolved relationship endpoint has resolved authority."
                        )
                elif len(bucket) != 1 or endpoint.target is not bucket[0]:
                    raise ValueError(
                        "Relationship endpoint must retain its exact relation target."
                    )
            if type(subject) is ProjectNonConcreteRelationshipSubject:
                expected_issues = _relation_issues(
                    occurrence.endpoints,
                    self.relation_environment,
                )
                if len(subject.relation_issues) != len(expected_issues) or any(
                    retained is not expected
                    for retained, expected in zip(
                        subject.relation_issues,
                        expected_issues,
                        strict=True,
                    )
                ):
                    raise ValueError(
                        "Relationship issues must retain exact resolution authority."
                    )
        semantic = tuple(
            subject.occurrence.semantic
            for subject in self.subjects
            if type(subject) is ProjectConcreteRelationshipSubject
        )
        if len(semantic) != len(self.semantic_relationships) or any(
            retained is not expected
            for retained, expected in zip(
                semantic,
                self.semantic_relationships,
                strict=True,
            )
        ):
            raise ValueError("Concrete subjects must retain every semantic fact.")
        diagnostics = tuple(
            diagnostic
            for subject in self.subjects
            if type(subject) is ProjectNonConcreteRelationshipSubject
            for diagnostic in subject.diagnostics
        )
        if len(diagnostics) != len(self.semantic_diagnostics) or any(
            retained is not expected
            for retained, expected in zip(
                diagnostics,
                self.semantic_diagnostics,
                strict=True,
            )
        ):
            raise ValueError("Subjects must retain every exact semantic diagnostic.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectRelationshipSet:
    """Selected-module-ordered Project relationship construction result."""

    semantic_result: ProjectSemanticResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    environments: tuple[ProjectModuleRelationshipEnvironment, ...] = ()

    def __post_init__(self) -> None:
        if type(self.semantic_result) is not ProjectSemanticResult:
            raise TypeError("Project relationships require a semantic result.")
        if (
            self.semantic_result.compilation_mode
            is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.semantic_result.module_relation_resolutions is None
        ):
            raise ValueError("Project relationships require explicit module authority.")
        if type(self.environments) is not tuple or any(
            type(item) is not ProjectModuleRelationshipEnvironment
            for item in self.environments
        ):
            raise TypeError("Project relationship environments must be a tuple.")
        if len(self.environments) != len(self.semantic_result.modules) or any(
            environment.module is not module
            for environment, module in zip(
                self.environments,
                self.semantic_result.modules,
                strict=True,
            )
        ):
            raise ValueError("Relationship environments must retain module order.")
        resolutions = self.semantic_result.module_relation_resolutions
        for environment in self.environments:
            matches = resolutions.find_module_path(environment.module.path)
            if len(matches) != 1 or environment.relation_environment is not matches[0]:
                raise ValueError(
                    "Relationship environment must retain exact resolution authority."
                )

    @property
    def subjects(self) -> tuple[ProjectRelationshipSubject, ...]:
        """Return every relationship in selected-module and source order."""

        return tuple(
            subject
            for environment in self.environments
            for subject in environment.subjects
        )

    def find_module_path(
        self,
        module_path: str,
    ) -> tuple[ProjectModuleRelationshipEnvironment, ...]:
        """Return one exact module environment, or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        return tuple(
            environment
            for environment in self.environments
            if environment.module.path == module_path
        )


def _span_contains(location: SourceLocation, span: Span) -> bool:
    if (
        location.path != span.path
        or location.end_line is None
        or location.end_column is None
    ):
        return False
    return (span.line, span.column) <= (location.line, location.column) and (
        location.end_line,
        location.end_column,
    ) <= (span.end_line, span.end_column)


def _semantic_matches(
    semantic: RelationshipSemanticInfo,
    relationship: RelationshipMetadata,
    targets: tuple[
        ProjectResolvedModuleRelationSymbol | None,
        ProjectResolvedModuleRelationSymbol | None,
    ],
) -> bool:
    return semantic.name == relationship.name and all(
        target is not None
        and semantic_endpoint.local_name == endpoint.local_name
        and semantic_endpoint.relation_name == endpoint.relation_name
        and semantic_endpoint.relation is target.target_occurrence.definition
        for semantic_endpoint, endpoint, target in zip(
            semantic.endpoints,
            relationship.endpoints,
            targets,
            strict=True,
        )
    )


def _relationship_diagnostics(
    relationship: RelationshipMetadata,
    diagnostics: tuple[Diagnostic, ...],
) -> tuple[Diagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if _span_contains(diagnostic.location, relationship.span)
    )


def _relation_issues(
    endpoints: tuple[
        ProjectRelationshipEndpointOccurrence,
        ProjectRelationshipEndpointOccurrence,
    ],
    environment: ProjectModuleRelationResolutionEnvironment,
) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
    issues: list[ProjectModuleRelationResolutionIssue] = []
    missing_names = {
        endpoint.authored_relation_spelling
        for endpoint in endpoints
        if endpoint.target is None
    }
    for issue in environment.issues:
        if (
            issue.status in _RELATIONSHIP_RESOLUTION_ISSUES
            and issue.local_name in missing_names
        ):
            issues.append(issue)
    return tuple(issues)


def build_project_relationships(
    semantic_result: ProjectSemanticResult,
) -> ProjectRelationshipSet:
    """Build complete Project relationships from exact existing authority."""

    if type(semantic_result) is not ProjectSemanticResult:
        raise TypeError("Project relationship construction requires semantic roots.")
    if (
        semantic_result.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
        or semantic_result.module_relation_resolutions is None
    ):
        raise ValueError("Project relationship construction requires module semantics.")

    resolutions = semantic_result.module_relation_resolutions
    environments: list[ProjectModuleRelationshipEnvironment] = []
    for module in semantic_result.modules:
        matches = resolutions.find_module_path(module.path)
        if len(matches) != 1 or matches[0].module is not module:
            raise ValueError("Relationship construction requires one module authority.")
        relation_environment = matches[0]
        relation_symbols: dict[str, Definition] = {
            symbol.local_name: symbol.target_occurrence.definition
            for symbol in relation_environment.symbols
        }
        assert module.parsed_input is not None
        script = module.parsed_input.script
        semantic_relationships, semantic_diagnostics = check_relationship_metadata(
            script,
            relation_symbols,
        )

        subjects: list[ProjectRelationshipSubject] = []
        semantic_position = 0
        for relationship_position, relationship in enumerate(script.relationships):
            identity = ProjectRelationshipDeclarationIdentity(
                module=module.identity,
                module_position=module.position,
                relationship_position=relationship_position,
            )
            target_buckets = tuple(
                relation_environment.find_relation_name(endpoint.relation_name)
                for endpoint in relationship.endpoints
            )
            if any(len(bucket) > 1 for bucket in target_buckets):
                raise ValueError("Relationship target lookup cannot choose a winner.")
            targets = tuple(bucket[0] if bucket else None for bucket in target_buckets)
            target_pair = (targets[0], targets[1])

            semantic = None
            if semantic_position < len(semantic_relationships):
                candidate = semantic_relationships[semantic_position]
                if _semantic_matches(candidate, relationship, target_pair):
                    semantic = candidate
                    semantic_position += 1
            endpoint_occurrences = tuple(
                ProjectRelationshipEndpointOccurrence(
                    identity=ProjectRelationshipEndpointIdentity(
                        declaration=identity,
                        endpoint_position=endpoint_position,
                    ),
                    endpoint=endpoint,
                    target=target,
                    semantic=(
                        None
                        if semantic is None
                        else semantic.endpoints[endpoint_position]
                    ),
                )
                for endpoint_position, (endpoint, target) in enumerate(
                    zip(relationship.endpoints, target_pair, strict=True)
                )
            )
            endpoint_pair = (endpoint_occurrences[0], endpoint_occurrences[1])
            occurrence = ProjectRelationshipDeclarationOccurrence(
                identity=identity,
                module=module,
                relationship=relationship,
                endpoints=endpoint_pair,
                semantic=semantic,
            )
            if semantic is not None:
                subjects.append(
                    ProjectConcreteRelationshipSubject(occurrence=occurrence)
                )
                continue

            diagnostics = _relationship_diagnostics(
                relationship,
                semantic_diagnostics,
            )
            relation_issues = _relation_issues(
                endpoint_pair,
                relation_environment,
            )
            state = _inferred_non_concrete_state(
                occurrence,
                diagnostics,
                relation_issues,
            )
            if state is None:
                raise ValueError("Non-concrete relationship requires exact evidence.")
            subjects.append(
                ProjectNonConcreteRelationshipSubject(
                    occurrence=occurrence,
                    state=state,
                    diagnostics=diagnostics,
                    relation_issues=relation_issues,
                )
            )
        if semantic_position != len(semantic_relationships):
            raise ValueError("Every semantic relationship requires one occurrence.")
        environments.append(
            ProjectModuleRelationshipEnvironment(
                module=module,
                relation_environment=relation_environment,
                semantic_relationships=semantic_relationships,
                semantic_diagnostics=semantic_diagnostics,
                subjects=tuple(subjects),
            )
        )
    return ProjectRelationshipSet(
        semantic_result=semantic_result,
        environments=tuple(environments),
    )
