"""Private Phase-63 scalar-reference facts over exact query-block row sources."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType

from pietto._project.model import ProjectRowField, ProjectRowFieldNullability
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
    ProjectIRRowField,
    ProjectIRRowShape,
    ProjectIRStageRowField,
    ProjectIRStageRowShape,
)
from pietto._project.project_ir import ProjectIRRelationConstructionState
from pietto._project.project_query_block import (
    ProjectConcreteQueryBlock,
    ProjectExistingRelationRowSource,
    ProjectNonConcreteQueryBlock,
    ProjectQueryBlockConstructionResult,
    ProjectQueryBlockRowSource,
    ProjectVerifiedJoinedRowSource,
)
from pietto._project.row_expression_type_facts import (
    project_row_field_to_semantic_value_type,
)
from pietto.ast_nodes import DottedNameExpr, Expression, NameExpr
from pietto.errors import Diagnostic, Severity
from pietto.semantic.aggregates import child_expressions
from pietto.semantic.expressions import infer_row_expression
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind

__all__: tuple[str, ...] = ()


type ProjectScalarSourceField = (
    ProjectIRRowField | ProjectIRStageRowField | ProjectIRJoinedRowField
)


def _source_field_parts(
    source_field: ProjectScalarSourceField,
) -> tuple[int, ProjectRowField, ProjectRowFieldNullability]:
    if type(source_field) is ProjectIRRowField:
        return (
            source_field.anchor.identity.field_position,
            source_field.evidence,
            source_field.evidence.nullability,
        )
    if type(source_field) is ProjectIRStageRowField:
        return (
            source_field.field_position,
            source_field.evidence,
            source_field.evidence.nullability,
        )
    if type(source_field) is ProjectIRJoinedRowField:
        return (
            source_field.field_position,
            source_field.evidence,
            source_field.effective_nullability,
        )
    raise TypeError("Scalar environment requires an exact row-field occurrence.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectScalarEnvironmentField:
    """One exact ordered source-field occurrence adapted for scalar typing."""

    source_field: ProjectScalarSourceField = field(
        repr=False,
        compare=False,
        hash=False,
    )
    position: int = field(init=False)
    evidence: ProjectRowField = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    value_type: ValueType = field(init=False)

    def __post_init__(self) -> None:
        position, evidence, effective_nullability = _source_field_parts(
            self.source_field
        )
        object.__setattr__(self, "position", position)
        object.__setattr__(self, "evidence", evidence)
        object.__setattr__(
            self,
            "value_type",
            project_row_field_to_semantic_value_type(
                evidence,
                effective_nullability,
            ),
        )


def _ordinary_source_fields(
    row_source: ProjectExistingRelationRowSource,
) -> tuple[ProjectIRRowField | ProjectIRStageRowField, ...]:
    row_shape = row_source.output.row_shape
    if type(row_shape) is ProjectIRRowShape:
        return row_shape.fields
    if type(row_shape) is ProjectIRStageRowShape:
        return row_shape.fields
    raise AssertionError("existing relation output lost its exact row shape")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteScalarEnvironment:
    """Occurrence-complete scalar fields for one concrete Slice-2 query block."""

    query_block: ProjectConcreteQueryBlock = field(
        repr=False,
        compare=False,
        hash=False,
    )
    row_source: ProjectQueryBlockRowSource = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    fields: tuple[ProjectScalarEnvironmentField, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.query_block) is not ProjectConcreteQueryBlock:
            raise TypeError("Concrete scalar environment requires a concrete block.")
        row_source = self.query_block.row_source
        if type(row_source) is ProjectExistingRelationRowSource:
            source_fields: tuple[ProjectScalarSourceField, ...] = (
                _ordinary_source_fields(row_source)
            )
        elif type(row_source) is ProjectVerifiedJoinedRowSource:
            source_fields = row_source.fields
        else:
            raise AssertionError("concrete query block lost its row-source variant")
        fields = tuple(
            ProjectScalarEnvironmentField(source_field=source_field)
            for source_field in source_fields
        )
        if tuple(item.position for item in fields) != tuple(range(len(fields))):
            raise ValueError("Scalar environment fields must retain occurrence order.")
        object.__setattr__(self, "row_source", row_source)
        object.__setattr__(self, "fields", fields)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteScalarEnvironment:
    """One exact Slice-2 terminal with no partial scalar field environment."""

    query_block: ProjectNonConcreteQueryBlock = field(
        repr=False,
        compare=False,
        hash=False,
    )
    state: ProjectIRRelationConstructionState = field(init=False)
    fields: tuple[ProjectScalarEnvironmentField, ...] = field(
        init=False,
        default=(),
    )

    def __post_init__(self) -> None:
        if type(self.query_block) is not ProjectNonConcreteQueryBlock:
            raise TypeError("Non-concrete environment requires a Slice-2 terminal.")
        object.__setattr__(self, "state", self.query_block.state)


type ProjectScalarEnvironment = (
    ProjectConcreteScalarEnvironment | ProjectNonConcreteScalarEnvironment
)


def build_project_scalar_environment(
    query_block: ProjectQueryBlockConstructionResult,
) -> ProjectScalarEnvironment:
    """Project one exact Slice-2 construction result into scalar availability."""

    if type(query_block) is ProjectConcreteQueryBlock:
        return ProjectConcreteScalarEnvironment(query_block=query_block)
    if type(query_block) is ProjectNonConcreteQueryBlock:
        return ProjectNonConcreteScalarEnvironment(query_block=query_block)
    raise TypeError("Scalar environment requires an exact Slice-2 result.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectScalarReferenceOccurrence:
    """One exact authored scalar field-reference use in one concrete environment."""

    environment: ProjectConcreteScalarEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: NameExpr | DottedNameExpr = field(
        repr=False,
        compare=False,
        hash=False,
    )
    query_block: ProjectConcreteQueryBlock = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        if type(self.environment) is not ProjectConcreteScalarEnvironment:
            raise TypeError("Scalar reference requires a concrete environment.")
        if type(self.expression) not in {NameExpr, DottedNameExpr}:
            raise TypeError("Scalar reference requires a name expression occurrence.")
        object.__setattr__(self, "query_block", self.environment.query_block)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectScalarReferenceResolution:
    """One caller-supplied complete candidate bucket without name lookup."""

    reference: ProjectScalarReferenceOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    candidates: tuple[ProjectScalarEnvironmentField, ...]
    status: ProjectModuleCandidateBucketStatus = field(init=False)
    target: ProjectScalarEnvironmentField | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.reference) is not ProjectScalarReferenceOccurrence:
            raise TypeError("Scalar resolution requires an exact reference occurrence.")
        if type(self.candidates) is not tuple or any(
            type(candidate) is not ProjectScalarEnvironmentField
            for candidate in self.candidates
        ):
            raise TypeError("Scalar resolution candidates must be an exact tuple.")
        environment_fields = self.reference.environment.fields
        positions: list[int] = []
        for candidate in self.candidates:
            matches = tuple(
                position
                for position, retained in enumerate(environment_fields)
                if candidate is retained
            )
            if len(matches) != 1:
                raise ValueError(
                    "Scalar candidate must belong to its exact environment."
                )
            positions.append(matches[0])
        if len(set(positions)) != len(positions):
            raise ValueError("Scalar candidate bucket cannot repeat an occurrence.")
        if positions != sorted(positions):
            raise ValueError("Scalar candidates must retain environment order.")
        status = (
            ProjectModuleCandidateBucketStatus.ABSENT
            if not self.candidates
            else (
                ProjectModuleCandidateBucketStatus.CONCRETE
                if len(self.candidates) == 1
                else ProjectModuleCandidateBucketStatus.AMBIGUOUS
            )
        )
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "target",
            self.candidates[0] if len(self.candidates) == 1 else None,
        )


def scalar_field_reference_leaves(
    expression: Expression,
) -> tuple[NameExpr | DottedNameExpr, ...]:
    """Enumerate exact scalar-reference leaves without treating call callees as rows."""

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


class ProjectScalarTypeNonConcreteReason(StrEnum):
    """The two Slice-3 scalar-type blocker families."""

    REFERENCE_RESOLUTION_NON_CONCRETE = "reference_resolution_non_concrete"
    TYPE_KERNEL_NON_CONCRETE = "type_kernel_non_concrete"


def _require_resolution_coverage(
    environment: ProjectConcreteScalarEnvironment,
    expression: Expression,
    resolutions: tuple[ProjectScalarReferenceResolution, ...],
) -> None:
    if type(environment) is not ProjectConcreteScalarEnvironment:
        raise TypeError("Scalar typing requires a concrete environment.")
    if not isinstance(expression, Expression):
        raise TypeError("Scalar typing requires an exact expression root.")
    if type(resolutions) is not tuple or any(
        type(resolution) is not ProjectScalarReferenceResolution
        for resolution in resolutions
    ):
        raise TypeError("Scalar typing resolutions must be an exact tuple.")
    leaves = scalar_field_reference_leaves(expression)
    if len({id(leaf) for leaf in leaves}) != len(leaves):
        raise ValueError("Scalar reference leaves must be distinct occurrences.")
    if len(resolutions) != len(leaves) or len(
        {id(item) for item in resolutions}
    ) != len(resolutions):
        raise ValueError("Scalar typing requires one fact per reference occurrence.")
    if any(
        resolution.reference.environment is not environment
        or resolution.reference.expression is not leaf
        for resolution, leaf in zip(resolutions, leaves, strict=True)
    ):
        raise ValueError(
            "Scalar resolution facts must retain exact leaf order and root."
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteScalarTypeResult:
    """One known root type produced by the existing semantic expression kernel."""

    environment: ProjectConcreteScalarEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(repr=False, compare=False, hash=False)
    resolutions: tuple[ProjectScalarReferenceResolution, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    value_type: ValueType
    value_types: Mapping[Expression, ValueType] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _require_resolution_coverage(
            self.environment,
            self.expression,
            self.resolutions,
        )
        if any(
            resolution.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            or resolution.target is None
            for resolution in self.resolutions
        ):
            raise ValueError("Concrete scalar typing requires concrete references.")
        if type(self.value_type) is not ValueType or (
            self.value_type.kind is not ValueTypeKind.KNOWN
        ):
            raise ValueError("Concrete scalar typing requires one known root type.")
        if self.value_types.get(self.expression) is not self.value_type:
            raise ValueError("Concrete scalar typing must retain its kernel root.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Scalar diagnostics must be an exact tuple.")
        if any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        ):
            raise ValueError("Concrete scalar typing forbids blocking diagnostics.")
        object.__setattr__(
            self,
            "value_types",
            MappingProxyType(dict(self.value_types)),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteScalarTypeResult:
    """One typed blocker terminal with no concrete root value type."""

    environment: ProjectConcreteScalarEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(repr=False, compare=False, hash=False)
    resolutions: tuple[ProjectScalarReferenceResolution, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reason: ProjectScalarTypeNonConcreteReason
    blocking_resolutions: tuple[ProjectScalarReferenceResolution, ...] = field(
        default=(),
        repr=False,
        compare=False,
        hash=False,
    )
    kernel_value_type: ValueType | None = None
    value_types: Mapping[Expression, ValueType] = field(
        default_factory=dict,
        repr=False,
        compare=False,
        hash=False,
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    value_type: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        _require_resolution_coverage(
            self.environment,
            self.expression,
            self.resolutions,
        )
        if type(self.reason) is not ProjectScalarTypeNonConcreteReason:
            raise TypeError("Non-concrete scalar typing requires an exact reason.")
        if type(self.blocking_resolutions) is not tuple or any(
            type(resolution) is not ProjectScalarReferenceResolution
            for resolution in self.blocking_resolutions
        ):
            raise TypeError("Scalar blockers must be an exact resolution tuple.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Scalar diagnostics must be an exact tuple.")
        if (
            self.reason
            is ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
        ):
            expected = tuple(
                resolution
                for resolution in self.resolutions
                if resolution.status is not ProjectModuleCandidateBucketStatus.CONCRETE
            )
            if (
                not expected
                or self.blocking_resolutions != expected
                or self.kernel_value_type is not None
                or self.value_types
                or self.diagnostics
            ):
                raise ValueError("Reference blocker terminal must retain exact facts.")
        else:
            if (
                self.blocking_resolutions
                or any(
                    resolution.status is not ProjectModuleCandidateBucketStatus.CONCRETE
                    for resolution in self.resolutions
                )
                or type(self.kernel_value_type) is not ValueType
                or (
                    self.value_types.get(self.expression) is not self.kernel_value_type
                    and not any(
                        diagnostic.severity is Severity.ERROR
                        for diagnostic in self.diagnostics
                    )
                )
                or (
                    self.kernel_value_type.kind is ValueTypeKind.KNOWN
                    and not any(
                        diagnostic.severity is Severity.ERROR
                        for diagnostic in self.diagnostics
                    )
                )
            ):
                raise ValueError("Kernel blocker terminal must retain exact evidence.")
        object.__setattr__(
            self,
            "value_types",
            MappingProxyType(dict(self.value_types)),
        )


type ProjectScalarTypeResult = (
    ProjectConcreteScalarTypeResult | ProjectNonConcreteScalarTypeResult
)


def analyze_project_scalar_expression(
    *,
    environment: ProjectConcreteScalarEnvironment,
    expression: Expression,
    resolutions: tuple[ProjectScalarReferenceResolution, ...],
) -> ProjectScalarTypeResult:
    """Type one pre-resolved scalar expression through the existing kernel."""

    _require_resolution_coverage(environment, expression, resolutions)
    blockers = tuple(
        resolution
        for resolution in resolutions
        if resolution.status is not ProjectModuleCandidateBucketStatus.CONCRETE
    )
    if blockers:
        return ProjectNonConcreteScalarTypeResult(
            environment=environment,
            expression=expression,
            resolutions=resolutions,
            reason=(
                ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
            ),
            blocking_resolutions=blockers,
        )

    value_types: dict[Expression, ValueType] = {}
    for resolution in resolutions:
        target = resolution.target
        if target is None:
            raise AssertionError("concrete scalar resolution lost its unique target")
        value_types[resolution.reference.expression] = target.value_type
    diagnostics: list[Diagnostic] = []
    root_value_type = infer_row_expression(
        expression,
        RowSchema(),
        value_types,
        diagnostics,
        report_unknown_name=True,
    )
    retained_diagnostics = tuple(diagnostics)
    if root_value_type.kind is ValueTypeKind.UNKNOWN or any(
        diagnostic.severity is Severity.ERROR for diagnostic in retained_diagnostics
    ):
        return ProjectNonConcreteScalarTypeResult(
            environment=environment,
            expression=expression,
            resolutions=resolutions,
            reason=ProjectScalarTypeNonConcreteReason.TYPE_KERNEL_NON_CONCRETE,
            kernel_value_type=root_value_type,
            value_types=value_types,
            diagnostics=retained_diagnostics,
        )
    return ProjectConcreteScalarTypeResult(
        environment=environment,
        expression=expression,
        resolutions=resolutions,
        value_type=root_value_type,
        value_types=value_types,
        diagnostics=retained_diagnostics,
    )
