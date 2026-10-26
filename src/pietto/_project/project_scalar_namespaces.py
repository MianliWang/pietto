"""Private Phase-63 joined LET and immutable scalar-namespace authority."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import cast

from pietto._project.existence_values import (
    existence_uses_for_owner,
    ProjectAnyField,
    ProjectAnyLetValue,
    ProjectAnyValue,
    analyze_any_values,
    validate_any_values,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCandidateBucketStatus,
)
from pietto._project.project_scalar_bindings import (
    ProjectJoinedScalarBindingEnvironment,
    ProjectVisibleJoinedBinding,
    resolve_project_joined_scalar_reference,
)
from pietto._project.row_expression_type_facts import scalar_read_types_within
from pietto._project.project_scalar_references import (
    ProjectScalarEnvironmentField,
    ProjectScalarReferenceOccurrence,
    ProjectScalarReferenceResolution,
    ProjectScalarTypeNonConcreteReason,
    scalar_field_reference_leaves,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    LetBinding,
    NameExpr,
    QueryDef,
    TableDef,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic import let_bindings as semantic_lets
from pietto.semantic.aggregates import (
    contains_semantic_aggregate,
    invalid_context_diagnostic,
)
from pietto._project.project_relationship_predicates import (
    ProjectRelationshipPredicateExpression,
    select_project_predicate_expression,
)
from pietto.semantic.expressions import LetValues, infer_row_expression
from pietto.semantic.model import RowSchema, ValueType, ValueTypeKind

__all__: tuple[str, ...] = ()


def _definition(
    environment: ProjectJoinedScalarBindingEnvironment,
) -> TableDef | QueryDef:
    if type(environment) is not ProjectJoinedScalarBindingEnvironment:
        raise TypeError("Joined namespace requires an exact Slice-4 root.")
    owner = environment.ledger.owner
    definition = owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("Joined namespace requires a table or query owner.")
    if environment.scalar_environment.query_block.owner_bridge.owner is not owner:
        raise ValueError("Joined namespace root lost its exact query-block owner.")
    return cast(TableDef | QueryDef, definition)


def _authored_bindings(
    environment: ProjectJoinedScalarBindingEnvironment,
) -> tuple[LetBinding, ...]:
    clause = _definition(environment).let_clause
    return () if clause is None else tuple(clause.bindings)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedLetOccurrence:
    """One exact query-block-local authored LET occurrence."""

    binding_environment: ProjectJoinedScalarBindingEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    source_ordinal: int
    binding: LetBinding = field(repr=False, compare=False, hash=False)
    owner: ProjectDeclarationOccurrence = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        bindings = _authored_bindings(self.binding_environment)
        if (
            type(self.source_ordinal) is not int
            or self.source_ordinal < 0
            or self.source_ordinal >= len(bindings)
            or bindings[self.source_ordinal] is not self.binding
        ):
            raise ValueError("LET occurrence must retain exact source order.")
        if type(self.binding) is not LetBinding:
            raise TypeError("LET occurrence requires an exact AST binding.")
        object.__setattr__(self, "owner", self.binding_environment.ledger.owner)
        object.__setattr__(self, "expression", self.binding.expression)


class ProjectScalarNamespaceStage(StrEnum):
    """The Slice-5 portion of the joined-query namespace lattice."""

    POST_JOIN_INPUT = "post_join_input"
    LET_BINDING = "let_binding"
    POST_LET = "post_let"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedScalarNamespace:
    """One immutable occurrence-complete joined scalar namespace."""

    binding_environment: ProjectJoinedScalarBindingEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    occurrences: tuple[ProjectJoinedLetOccurrence, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    stage: ProjectScalarNamespaceStage
    binding_ordinal: int | None = None
    let_values: tuple[ProjectJoinedLetValue, ...] = ()
    # POST_LET's values as a def argument is checked with them written in,
    # shared by every expression typed here so that each is written once.
    written_lets: LetValues | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    projection_aliases: tuple[object, ...] = field(init=False, default=())

    def __post_init__(self) -> None:
        bindings = _authored_bindings(self.binding_environment)
        if type(self.occurrences) is not tuple or len(self.occurrences) != len(
            bindings
        ):
            raise ValueError("Scalar namespace requires every LET occurrence.")
        if any(
            type(occurrence) is not ProjectJoinedLetOccurrence
            or occurrence.binding_environment is not self.binding_environment
            or occurrence.source_ordinal != ordinal
            or occurrence.binding is not binding
            for ordinal, (occurrence, binding) in enumerate(
                zip(self.occurrences, bindings, strict=True)
            )
        ):
            raise ValueError("Scalar namespace LET occurrences lost exact identity.")
        if type(self.stage) is not ProjectScalarNamespaceStage:
            raise TypeError("Scalar namespace requires an exact stage.")
        if type(self.let_values) is not tuple or any(
            type(value) is not ProjectJoinedLetValue for value in self.let_values
        ):
            raise TypeError("Scalar namespace LET values must be an exact tuple.")
        ordinals = tuple(value.occurrence.source_ordinal for value in self.let_values)
        if (
            ordinals != tuple(sorted(ordinals))
            or len(set(ordinals)) != len(ordinals)
            or any(
                value.occurrence.binding_environment is not self.binding_environment
                for value in self.let_values
            )
        ):
            raise ValueError("Scalar namespace values must retain source order.")
        names = tuple(value.occurrence.binding.name for value in self.let_values)
        if len(set(names)) != len(names):
            raise ValueError("Scalar namespace cannot admit duplicate LET names.")

        if self.stage is ProjectScalarNamespaceStage.POST_JOIN_INPUT:
            if self.binding_ordinal is not None or self.let_values:
                raise ValueError("POST_JOIN_INPUT contains no LET values.")
        elif self.stage is ProjectScalarNamespaceStage.LET_BINDING:
            if (
                type(self.binding_ordinal) is not int
                or self.binding_ordinal < 0
                or self.binding_ordinal >= len(self.occurrences)
                or any(ordinal >= self.binding_ordinal for ordinal in ordinals)
            ):
                raise ValueError("LET_BINDING sees only admitted earlier values.")
        elif self.binding_ordinal is not None or ordinals != tuple(
            range(len(self.occurrences))
        ):
            raise ValueError("POST_LET requires every authored LET value.")

    @property
    def bindings(self) -> tuple[ProjectVisibleJoinedBinding, ...]:
        return self.binding_environment.bindings

    @property
    def visible_fields(self) -> tuple[ProjectScalarEnvironmentField, ...]:
        return self.binding_environment.visible_fields

    @property
    def hidden_fields(self) -> tuple[ProjectScalarEnvironmentField, ...]:
        return self.binding_environment.hidden_fields


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedLetValue:
    """One admitted LET occurrence and its exact existing-kernel type evidence."""

    occurrence: ProjectJoinedLetOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    namespace: ProjectJoinedScalarNamespace = field(
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
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...] = field(
        repr=False, compare=False, hash=False
    )
    diagnostics: tuple[Diagnostic, ...] = ()
    existence_values: tuple[ProjectAnyValue, ...] = ()
    predicate_expression: ProjectRelationshipPredicateExpression | None = None

    @property
    def normalized_expression(self) -> Expression:
        record = self.predicate_expression
        if record is None:
            return self.occurrence.expression
        if (
            record.owner is not self.occurrence.owner
            or record.authored is not self.occurrence.expression
        ):
            raise ValueError("LET predicate normalization requires exact ownership.")
        return record.expression

    def __post_init__(self) -> None:
        validate_any_values(
            self.occurrence.owner, self.normalized_expression, self.existence_values
        )
        if type(self.occurrence) is not ProjectJoinedLetOccurrence or (
            type(self.namespace) is not ProjectJoinedScalarNamespace
            or self.namespace.stage is not ProjectScalarNamespaceStage.LET_BINDING
            or self.namespace.binding_ordinal != self.occurrence.source_ordinal
            or self.namespace.binding_environment
            is not self.occurrence.binding_environment
        ):
            raise ValueError("LET value requires its exact immutable prefix.")
        if type(self.value_type) is not ValueType or (
            self.value_type.kind is not ValueTypeKind.KNOWN
        ):
            raise ValueError("Admitted LET value requires a known type.")
        if self.value_types.get(self.occurrence.expression) is not self.value_type:
            raise ValueError("LET value must retain its exact kernel root type.")
        _require_expression_resolution_coverage(
            self.namespace,
            self.normalized_expression,
            self.resolutions,
            self.predicate_expression,
        )
        for resolution in self.resolutions:
            target = resolution.target
            if (
                target is None
                or (
                    type(resolution) is ProjectScalarReferenceResolution
                    and not any(
                        target is item for item in self.namespace.visible_fields
                    )
                )
                or (
                    type(resolution) is ProjectJoinedLetReferenceResolution
                    and not any(target is item for item in self.namespace.let_values)
                )
                or self.value_types.get(resolution.reference.expression)
                is not target.value_type
            ):
                raise ValueError(
                    "LET resolution must retain its exact available target/type."
                )
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("LET value diagnostics must be an exact tuple.")
        if any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        ):
            raise ValueError("Admitted LET values forbid blocking diagnostics.")
        object.__setattr__(
            self,
            "value_types",
            MappingProxyType(dict(self.value_types)),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectJoinedLetReferenceResolution:
    """One bare reference to an exact admitted earlier LET occurrence."""

    namespace: ProjectJoinedScalarNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    reference: ProjectScalarReferenceOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    target: ProjectJoinedLetValue = field(repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        expression = self.reference.expression
        if (
            type(self.namespace) is not ProjectJoinedScalarNamespace
            or self.namespace.stage is ProjectScalarNamespaceStage.POST_JOIN_INPUT
            or self.reference.environment
            is not self.namespace.binding_environment.scalar_environment
            or type(expression) is not NameExpr
            or expression.name != self.target.occurrence.binding.name
            or not any(self.target is value for value in self.namespace.let_values)
        ):
            raise ValueError("LET reference must retain one exact visible target.")


type ProjectJoinedNamespaceReferenceResolution = (
    ProjectJoinedLetReferenceResolution | ProjectScalarReferenceResolution
)


def resolve_project_joined_namespace_reference(
    namespace: ProjectJoinedScalarNamespace,
    reference: ProjectScalarReferenceOccurrence,
) -> ProjectJoinedNamespaceReferenceResolution:
    """Resolve bare LET first or delegate exact field lookup to Slice 4."""

    if type(namespace) is not ProjectJoinedScalarNamespace or (
        type(reference) is not ProjectScalarReferenceOccurrence
        or reference.environment is not namespace.binding_environment.scalar_environment
    ):
        raise ValueError("Namespace lookup requires an exact same-root reference.")
    expression = reference.expression
    if type(expression) is DottedNameExpr:
        return resolve_project_joined_scalar_reference(
            namespace.binding_environment,
            reference,
        )
    if type(expression) is not NameExpr:
        raise AssertionError("namespace reference lost its exact expression variant")
    matches = tuple(
        value
        for value in namespace.let_values
        if value.occurrence.binding.name == expression.name
    )
    fields = resolve_project_joined_scalar_reference(
        namespace.binding_environment,
        reference,
    )
    if len(matches) > 1 or (matches and fields.candidates):
        raise ValueError("Joined scalar namespace is incoherent.")
    if matches:
        return ProjectJoinedLetReferenceResolution(
            namespace=namespace,
            reference=reference,
            target=matches[0],
        )
    return fields


def _require_expression_resolution_coverage(
    namespace: ProjectJoinedScalarNamespace,
    expression: Expression,
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...],
    predicate_expression: ProjectRelationshipPredicateExpression | None = None,
) -> None:
    if type(namespace) is not ProjectJoinedScalarNamespace:
        raise TypeError("Joined expression analysis requires an exact namespace.")
    if not isinstance(expression, Expression):
        raise TypeError("Joined expression analysis requires an expression root.")
    if type(resolutions) is not tuple or any(
        type(resolution)
        not in {
            ProjectJoinedLetReferenceResolution,
            ProjectScalarReferenceResolution,
        }
        for resolution in resolutions
    ):
        raise TypeError("Joined expression resolutions must be an exact tuple.")
    if (
        predicate_expression is not None
        and predicate_expression.expression is not expression
    ):
        raise ValueError(
            "Joined scalar references require their exact normalized expression."
        )
    leaves = (
        scalar_field_reference_leaves(expression)
        if predicate_expression is None
        else predicate_expression.scalar_references
    )
    if len({id(leaf) for leaf in leaves}) != len(leaves):
        raise ValueError("Joined expression leaves must be distinct occurrences.")
    if len(resolutions) != len(leaves) or any(
        resolution.reference.expression is not leaf
        or resolution.reference.environment
        is not namespace.binding_environment.scalar_environment
        or (
            type(resolution) is ProjectJoinedLetReferenceResolution
            and resolution.namespace is not namespace
        )
        for resolution, leaf in zip(resolutions, leaves, strict=True)
    ):
        raise ValueError(
            "Joined expression resolutions must retain exact leaf order and root."
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedNamespaceExpression:
    """One known expression type from an exact joined scalar namespace."""

    namespace: ProjectJoinedScalarNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(repr=False, compare=False, hash=False)
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...] = field(
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
    existence_values: tuple[ProjectAnyValue, ...] = ()
    predicate_expression: ProjectRelationshipPredicateExpression | None = field(
        default=None, repr=False
    )

    @property
    def normalized_expression(self) -> Expression:
        record = self.predicate_expression
        if record is None:
            return self.expression
        region = self.namespace.binding_environment.region
        anchor = record if record.parent is None else record.parent
        if (
            record.owner is not self.namespace.binding_environment.ledger.owner
            or record.authored is not self.expression
            or not any(
                anchor is retained
                for retained in region.conditions.predicate_expressions
            )
        ):
            raise ValueError(
                "Joined predicate normalization requires exact authored ownership."
            )
        return record.expression

    def __post_init__(self) -> None:
        validate_any_values(
            self.namespace.binding_environment.ledger.owner,
            self.normalized_expression,
            self.existence_values,
        )
        _require_expression_resolution_coverage(
            self.namespace,
            self.normalized_expression,
            self.resolutions,
            self.predicate_expression,
        )
        if any(
            type(resolution) is ProjectScalarReferenceResolution
            and resolution.target is None
            for resolution in self.resolutions
        ):
            raise ValueError("Concrete joined expression requires concrete references.")
        if type(self.value_type) is not ValueType or (
            self.value_type.kind is not ValueTypeKind.KNOWN
        ):
            raise ValueError("Concrete joined expression requires one known type.")
        if self.value_types.get(self.expression) is not self.value_type:
            raise ValueError("Concrete joined expression must retain its kernel root.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Joined expression diagnostics must be an exact tuple.")
        if any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        ):
            raise ValueError("Concrete joined expression forbids blocking diagnostics.")
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedNamespaceExpression:
    """One closed joined-namespace expression blocker without a root type."""

    namespace: ProjectJoinedScalarNamespace = field(
        repr=False,
        compare=False,
        hash=False,
    )
    expression: Expression = field(repr=False, compare=False, hash=False)
    resolutions: tuple[ProjectJoinedNamespaceReferenceResolution, ...] = field(
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
    existence_values: tuple[ProjectAnyValue, ...] = ()
    predicate_expression: ProjectRelationshipPredicateExpression | None = field(
        default=None, repr=False
    )

    @property
    def normalized_expression(self) -> Expression:
        record = self.predicate_expression
        if record is None:
            return self.expression
        region = self.namespace.binding_environment.region
        anchor = record if record.parent is None else record.parent
        if (
            record.owner is not self.namespace.binding_environment.ledger.owner
            or record.authored is not self.expression
            or not any(
                anchor is retained
                for retained in region.conditions.predicate_expressions
            )
        ):
            raise ValueError(
                "Joined predicate normalization requires exact authored ownership."
            )
        return record.expression

    value_type: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        validate_any_values(
            self.namespace.binding_environment.ledger.owner,
            self.normalized_expression,
            self.existence_values,
        )
        _require_expression_resolution_coverage(
            self.namespace,
            self.normalized_expression,
            self.resolutions,
            self.predicate_expression,
        )
        if type(self.reason) is not ProjectScalarTypeNonConcreteReason:
            raise TypeError("Joined expression blocker requires an exact reason.")
        if type(self.blocking_resolutions) is not tuple or any(
            type(resolution) is not ProjectScalarReferenceResolution
            for resolution in self.blocking_resolutions
        ):
            raise TypeError("Joined expression blockers must be an exact tuple.")
        if type(self.diagnostics) is not tuple or any(
            type(diagnostic) is not Diagnostic for diagnostic in self.diagnostics
        ):
            raise TypeError("Joined expression diagnostics must be an exact tuple.")
        expected = tuple(
            resolution
            for resolution in self.resolutions
            if type(resolution) is ProjectScalarReferenceResolution
            and resolution.target is None
        )
        if (
            self.reason
            is ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
        ):
            # Reads that resolve to no field are typed around and reported by
            # the kernel; an ambiguous read retains only its lookup facts.
            absent = all(
                resolution.status is ProjectModuleCandidateBucketStatus.ABSENT
                for resolution in expected
            )
            if (
                not expected
                or self.blocking_resolutions != expected
                or (
                    (
                        type(self.kernel_value_type) is not ValueType
                        or self.value_types.get(self.expression)
                        is not self.kernel_value_type
                        or not any(
                            diagnostic.severity is Severity.ERROR
                            for diagnostic in self.diagnostics
                        )
                    )
                    if absent
                    else (
                        self.kernel_value_type is not None
                        or self.value_types
                        or self.diagnostics
                    )
                )
            ):
                raise ValueError(
                    "Joined reference blocker must retain only exact lookup facts."
                )
        elif (
            expected
            or self.blocking_resolutions
            or type(self.kernel_value_type) is not ValueType
            or self.value_types.get(self.expression) is not self.kernel_value_type
            or (
                self.kernel_value_type.kind is ValueTypeKind.KNOWN
                and not any(
                    diagnostic.severity is Severity.ERROR
                    for diagnostic in self.diagnostics
                )
            )
        ):
            raise ValueError("Joined kernel blocker must retain exact kernel evidence.")
        object.__setattr__(
            self, "value_types", MappingProxyType(dict(self.value_types))
        )


type ProjectJoinedNamespaceExpressionResult = (
    ProjectConcreteJoinedNamespaceExpression
    | ProjectNonConcreteJoinedNamespaceExpression
)


def analyze_project_joined_namespace_expression(
    namespace: ProjectJoinedScalarNamespace,
    expression: Expression,
    read_types: Mapping[Expression, ValueType] | None = None,
) -> ProjectJoinedNamespaceExpressionResult:
    """Resolve and type one expression without applying a consumer policy.

    ``read_types`` holds the owner's typed scalar relation reads and the column
    type of each ``in`` read.
    """

    if type(namespace) is not ProjectJoinedScalarNamespace:
        raise TypeError("Joined expression analysis requires an exact namespace.")
    if not isinstance(expression, Expression):
        raise TypeError("Joined expression analysis requires an expression root.")
    region = namespace.binding_environment.region
    record = select_project_predicate_expression(
        region.conditions.predicate_expressions,
        namespace.binding_environment.ledger.owner,
        expression,
    )
    normalized = expression if record is None else record.expression
    any_values = _joined_any_values(namespace, expression, normalized, record)
    leaves = (
        scalar_field_reference_leaves(normalized)
        if record is None
        else record.scalar_references
    )
    resolutions = tuple(
        resolve_project_joined_namespace_reference(
            namespace,
            ProjectScalarReferenceOccurrence(
                environment=namespace.binding_environment.scalar_environment,
                expression=leaf,
            ),
        )
        for leaf in leaves
    )
    blockers = tuple(
        resolution
        for resolution in resolutions
        if type(resolution) is ProjectScalarReferenceResolution
        and resolution.target is None
    )
    if any(
        resolution.status is not ProjectModuleCandidateBucketStatus.ABSENT
        for resolution in blockers
    ):
        return ProjectNonConcreteJoinedNamespaceExpression(
            namespace=namespace,
            expression=expression,
            predicate_expression=record,
            existence_values=any_values,
            resolutions=resolutions,
            reason=(
                ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
            ),
            blocking_resolutions=blockers,
        )

    value_types = scalar_read_types_within(normalized, read_types)
    for value in any_values:
        value_types.update(value.value_types)
    for resolution in resolutions:
        if type(resolution) is ProjectScalarReferenceResolution and (
            resolution.target is not None
        ):
            value_types[resolution.reference.expression] = resolution.target.value_type
    diagnostics: list[Diagnostic] = list(
        record.diagnostics if record is not None else ()
    )
    diagnostics.extend(item for value in any_values for item in value.diagnostics)
    root_value_type = infer_row_expression(
        normalized,
        RowSchema(),
        value_types,
        diagnostics,
        report_unknown_name=True,
        # A field read that resolves to no field stays untyped and is an
        # unknown field, as in a relation without JOIN inputs; no binding
        # qualifies a field here, so a dotted one is reported as a bare one is.
        field_qualifier="" if blockers else None,
        bare_value_types={
            value.occurrence.binding.name: value.value_type
            for value in namespace.let_values
        },
        # A `let:` name is typed as its value; a def argument is checked with
        # the values written in, as emission writes it, and a check that reads
        # a value through its name (a LIKE pattern) follows it.
        bare_value_expressions=namespace.written_lets,
        relation_columns=read_types,
        failed_relationship_calls=() if record is None else record.failed_calls,
    )
    value_types[expression] = root_value_type
    retained_diagnostics = tuple(diagnostics)
    if blockers:
        return ProjectNonConcreteJoinedNamespaceExpression(
            namespace=namespace,
            expression=expression,
            predicate_expression=record,
            existence_values=any_values,
            resolutions=resolutions,
            reason=(
                ProjectScalarTypeNonConcreteReason.REFERENCE_RESOLUTION_NON_CONCRETE
            ),
            blocking_resolutions=blockers,
            kernel_value_type=root_value_type,
            value_types=value_types,
            diagnostics=retained_diagnostics,
        )
    if root_value_type.kind is ValueTypeKind.UNKNOWN or any(
        diagnostic.severity is Severity.ERROR for diagnostic in retained_diagnostics
    ):
        return ProjectNonConcreteJoinedNamespaceExpression(
            namespace=namespace,
            expression=expression,
            predicate_expression=record,
            existence_values=any_values,
            resolutions=resolutions,
            reason=ProjectScalarTypeNonConcreteReason.TYPE_KERNEL_NON_CONCRETE,
            kernel_value_type=root_value_type,
            value_types=value_types,
            diagnostics=retained_diagnostics,
        )
    return ProjectConcreteJoinedNamespaceExpression(
        namespace=namespace,
        expression=expression,
        predicate_expression=record,
        existence_values=any_values,
        resolutions=resolutions,
        value_type=root_value_type,
        value_types=value_types,
        diagnostics=retained_diagnostics,
    )


def _joined_any_values(
    namespace: ProjectJoinedScalarNamespace,
    authored: Expression,
    expression: Expression,
    record: ProjectRelationshipPredicateExpression | None = None,
) -> tuple[ProjectAnyValue, ...]:
    source = namespace.binding_environment.row_source
    region = namespace.binding_environment.region
    return analyze_any_values(
        root=source.base_verification.root.join_regions.uses.semantic_result,
        owner=namespace.binding_environment.ledger.owner,
        authored=authored,
        expression=expression,
        normalized_any=() if record is None else record.any_expressions,
        retained_bindings=None if record is None else record.any_bindings,
        failed_relationship_calls=() if record is None else record.failed_calls,
        outer_fields=tuple(
            ProjectAnyField(binding=binding.binding, source_field=field)
            for binding in namespace.bindings
            for field in binding.fields
        ),
        let_values=tuple(
            ProjectAnyLetValue(
                binding=value.occurrence.binding,
                expression=value.normalized_expression,
                value_type=value.value_type,
                authority=value,
            )
            for value in namespace.let_values
        ),
        available=region.input_scope.available_entries
        if region.input_scope is not None
        else (),
    )


def _name_admissibility(
    environment: ProjectJoinedScalarBindingEnvironment,
    occurrences: tuple[ProjectJoinedLetOccurrence, ...],
) -> tuple[set[str], tuple[Diagnostic, ...]]:
    definition = _definition(environment)
    visible_field_names = {item.evidence.name for item in environment.visible_fields}
    region = environment.region
    generated = {
        id(use.clause)
        for use in existence_uses_for_owner(
            region.conditions.uses.semantic_result, environment.ledger.owner
        )
    }
    input_relation_names = {
        name
        for retained in environment.bindings
        if id(retained.binding.site) not in generated
        for name in (retained.binding.name, retained.binding.relation_name)
    }
    invalid_names: set[str] = set()
    seen_names: set[str] = set()
    diagnostics: list[Diagnostic] = []
    for occurrence in occurrences:
        binding = occurrence.binding
        if binding.name in seen_names:
            diagnostics.append(
                semantic_lets._invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Duplicate let binding name",
                )
            )
            invalid_names.add(binding.name)
            continue
        seen_names.add(binding.name)
        if binding.name in visible_field_names:
            diagnostics.append(
                semantic_lets._invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding cannot shadow input field",
                )
            )
            invalid_names.add(binding.name)
            continue
        if binding.name in input_relation_names:
            diagnostics.append(
                semantic_lets._invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding cannot shadow input relation",
                )
            )
            invalid_names.add(binding.name)
            continue
        if semantic_lets._binding_conflicts_with_projection_output(
            definition,
            binding.name,
            allow_unaliased_selected_let_outputs=True,
        ):
            diagnostics.append(
                semantic_lets._invalid_let_name_diagnostic(
                    binding,
                    binding.name,
                    reason="Let binding conflicts with projection output name",
                )
            )
            invalid_names.add(binding.name)
    return invalid_names, tuple(diagnostics)


def _validate_namespace_chain(
    environment: ProjectJoinedScalarBindingEnvironment,
    occurrences: tuple[ProjectJoinedLetOccurrence, ...],
    post_join_input: ProjectJoinedScalarNamespace,
    binding_namespaces: tuple[ProjectJoinedScalarNamespace, ...],
) -> None:
    if (
        post_join_input.binding_environment is not environment
        or post_join_input.occurrences is not occurrences
        or post_join_input.stage is not ProjectScalarNamespaceStage.POST_JOIN_INPUT
        or len(binding_namespaces) != len(occurrences)
        or any(
            namespace.binding_environment is not environment
            or namespace.occurrences is not occurrences
            or namespace.stage is not ProjectScalarNamespaceStage.LET_BINDING
            or namespace.binding_ordinal != ordinal
            for ordinal, namespace in enumerate(binding_namespaces)
        )
    ):
        raise ValueError("Joined LET namespace chain lost exact stage order.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteJoinedLetNamespaces:
    """One closed successful joined LET analysis with exact POST_LET authority."""

    binding_environment: ProjectJoinedScalarBindingEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    occurrences: tuple[ProjectJoinedLetOccurrence, ...]
    post_join_input: ProjectJoinedScalarNamespace
    binding_namespaces: tuple[ProjectJoinedScalarNamespace, ...]
    values: tuple[ProjectJoinedLetValue, ...]
    post_let: ProjectJoinedScalarNamespace
    diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        _validate_namespace_chain(
            self.binding_environment,
            self.occurrences,
            self.post_join_input,
            self.binding_namespaces,
        )
        if (
            self.post_let.binding_environment is not self.binding_environment
            or self.post_let.occurrences is not self.occurrences
            or self.post_let.stage is not ProjectScalarNamespaceStage.POST_LET
            or len(self.values) != len(self.occurrences)
            or any(
                actual is not expected
                for actual, expected in zip(
                    self.post_let.let_values,
                    self.values,
                    strict=True,
                )
            )
        ):
            raise ValueError("Concrete joined LET analysis requires exact POST_LET.")
        if any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        ):
            raise ValueError("Concrete joined LET analysis forbids errors.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteJoinedLetNamespaces:
    """One closed joined LET blocker with no concrete POST_LET namespace."""

    binding_environment: ProjectJoinedScalarBindingEnvironment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    occurrences: tuple[ProjectJoinedLetOccurrence, ...]
    post_join_input: ProjectJoinedScalarNamespace
    binding_namespaces: tuple[ProjectJoinedScalarNamespace, ...]
    inadmissible_occurrences: tuple[ProjectJoinedLetOccurrence, ...] = ()
    blocked_dependency_references: tuple[NameExpr, ...] = ()
    blocking_resolutions: tuple[ProjectScalarReferenceResolution, ...] = ()
    unknown_type_occurrences: tuple[ProjectJoinedLetOccurrence, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    # The values admitted anyway, their written forms and the type of each
    # binding without an error of its own that is not admitted (`k = null`,
    # unknown, and each binding that reads one), with which a later clause is
    # still typed for its own errors
    # (`project_final_outputs.joined_let_unreached_diagnostics`).
    admitted_values: tuple[ProjectJoinedLetValue, ...] = field(
        default=(), repr=False, compare=False, hash=False
    )
    written_lets: LetValues | None = field(
        default=None, repr=False, compare=False, hash=False
    )
    unadmitted_value_types: Mapping[str, ValueType] = field(
        default_factory=dict, repr=False, compare=False, hash=False
    )
    post_let: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        _validate_namespace_chain(
            self.binding_environment,
            self.occurrences,
            self.post_join_input,
            self.binding_namespaces,
        )
        if not any(
            (
                self.inadmissible_occurrences,
                self.blocked_dependency_references,
                self.blocking_resolutions,
                self.unknown_type_occurrences,
                tuple(
                    diagnostic
                    for diagnostic in self.diagnostics
                    if diagnostic.severity is Severity.ERROR
                ),
            )
        ):
            raise ValueError("Non-concrete joined LET analysis requires a blocker.")


type ProjectJoinedLetNamespaceResult = (
    ProjectConcreteJoinedLetNamespaces | ProjectNonConcreteJoinedLetNamespaces
)


def build_project_joined_let_namespaces(
    binding_environment: ProjectJoinedScalarBindingEnvironment,
) -> ProjectJoinedLetNamespaceResult:
    """Analyze one exact joined LET clause through immutable prefix namespaces."""

    bindings = _authored_bindings(binding_environment)
    occurrences = tuple(
        ProjectJoinedLetOccurrence(
            binding_environment=binding_environment,
            source_ordinal=ordinal,
            binding=binding,
        )
        for ordinal, binding in enumerate(bindings)
    )
    post_join_input = ProjectJoinedScalarNamespace(
        binding_environment=binding_environment,
        occurrences=occurrences,
        stage=ProjectScalarNamespaceStage.POST_JOIN_INPUT,
    )
    invalid_names, name_diagnostics = _name_admissibility(
        binding_environment,
        occurrences,
    )
    diagnostics = list(name_diagnostics)
    values: list[ProjectJoinedLetValue] = []
    binding_namespaces: list[ProjectJoinedScalarNamespace] = []
    blocked_dependencies: list[NameExpr] = []
    blocking_resolutions: list[ProjectScalarReferenceResolution] = []
    unknown_types: list[ProjectJoinedLetOccurrence] = []
    all_names = {binding.name for binding in bindings}
    prior_names: set[str] = set()
    # Bindings without an error of their own whose type is unknown, such as
    # `k = null`, and those that read one, with the type each has as written:
    # written in as above and read with that type, a name bound to `null`
    # taking its type from where it stands, as in a relation without JOIN
    # inputs, so that a later binding is typed and its errors are reported.
    # They are no admitted values, so the namespace stays non-concrete.
    unadmitted: dict[str, ValueType] = {}
    # The type of each field read so far, for a binding written in.
    field_types: dict[Expression, ValueType] = {}
    # The admitted values, which a def argument is checked with written in,
    # each with the types of the fields it reads, and a check that reads a
    # value through its name (a LIKE pattern) follows.
    let_values = LetValues(field_types=field_types)

    for occurrence in occurrences:
        namespace = ProjectJoinedScalarNamespace(
            binding_environment=binding_environment,
            occurrences=occurrences,
            stage=ProjectScalarNamespaceStage.LET_BINDING,
            binding_ordinal=occurrence.source_ordinal,
            let_values=tuple(values),
        )
        binding_namespaces.append(namespace)
        region = binding_environment.region
        record = select_project_predicate_expression(
            region.conditions.predicate_expressions,
            occurrence.owner,
            occurrence.expression,
        )
        normalized = occurrence.expression if record is None else record.expression
        local_diagnostics: list[Diagnostic] = list(
            record.diagnostics if record is not None else ()
        )
        if contains_semantic_aggregate(occurrence.expression):
            local_diagnostics.append(
                invalid_context_diagnostic(
                    occurrence.expression,
                    context="let binding",
                )
            )
        suppressed_names = semantic_lets._dependency_diagnostics(
            occurrence.binding,
            all_name_set=all_names,
            prior_names=set(prior_names),
            diagnostics=local_diagnostics,
            ignored_expression_ids=frozenset(
                id(argument)
                for failure in (() if record is None else record.failed_calls)
                for argument in failure.call.arguments
                if type(argument) is NameExpr
            ),
        )
        leaves = (
            scalar_field_reference_leaves(normalized)
            if record is None
            else record.scalar_references
        )
        if len({id(leaf) for leaf in leaves}) != len(leaves):
            raise ValueError("LET expression references must be exact occurrences.")
        blocked = tuple(
            leaf
            for leaf in leaves
            if type(leaf) is NameExpr and leaf.name in suppressed_names
        )
        blocked_dependencies.extend(blocked)
        value_types: dict[Expression, ValueType] = (
            dict(field_types) if unadmitted else {}
        )
        resolutions: list[ProjectJoinedNamespaceReferenceResolution] = []
        local_blockers: list[ProjectScalarReferenceResolution] = []
        reads_unknown = False
        for leaf in leaves:
            if any(leaf is item for item in blocked):
                continue
            if type(leaf) is NameExpr and leaf.name in unadmitted:
                reads_unknown = True
                continue
            resolution = resolve_project_joined_namespace_reference(
                namespace,
                ProjectScalarReferenceOccurrence(
                    environment=binding_environment.scalar_environment,
                    expression=leaf,
                ),
            )
            resolutions.append(resolution)
            if type(resolution) is ProjectScalarReferenceResolution:
                if resolution.target is None:
                    local_blockers.append(resolution)
                else:
                    value_types[leaf] = resolution.target.value_type
                    field_types[leaf] = resolution.target.value_type
        blocking_resolutions.extend(local_blockers)

        any_values = _joined_any_values(
            namespace, occurrence.expression, normalized, record
        )
        # A typed ANY restates its rejected calls' errors, which the record owns.
        restated = {id(item) for item in (() if record is None else record.diagnostics)}
        for value in any_values:
            value_types.update(value.value_types)
            local_diagnostics.extend(
                item for item in value.diagnostics if id(item) not in restated
            )
        root_type: ValueType | None = None
        # A read that resolves to no field is an unknown field, as in
        # `analyze_project_joined_namespace_expression`; the binding then has
        # an error of its own and is not admitted. A read of a binding with
        # an error of its own is of unknown type.
        if not blocked and all(
            resolution.status is ProjectModuleCandidateBucketStatus.ABSENT
            for resolution in local_blockers
        ):
            root_type = infer_row_expression(
                normalized,
                RowSchema(),
                value_types,
                local_diagnostics,
                report_unknown_name=True,
                field_qualifier="" if local_blockers else None,
                suppressed_unknown_names=all_names,
                bare_value_types={
                    **{
                        value.occurrence.binding.name: value.value_type
                        for value in values
                    },
                    **unadmitted,
                },
                bare_value_expressions=let_values,
                failed_relationship_calls=() if record is None else record.failed_calls,
            )
        if root_type is not None:
            value_types[occurrence.expression] = root_type
        diagnostics.extend(local_diagnostics)
        has_error = any(
            diagnostic.severity is Severity.ERROR for diagnostic in local_diagnostics
        )
        if (
            not local_blockers
            and root_type is not None
            and root_type.kind is ValueTypeKind.UNKNOWN
        ):
            unknown_types.append(occurrence)
        if (
            occurrence.binding.name not in invalid_names
            and not blocked
            and not local_blockers
            and root_type is not None
            and not has_error
        ):
            if reads_unknown or root_type.kind is ValueTypeKind.UNKNOWN:
                unadmitted[occurrence.binding.name] = root_type
            else:
                values.append(
                    ProjectJoinedLetValue(
                        occurrence=occurrence,
                        namespace=namespace,
                        value_type=root_type,
                        value_types=value_types,
                        resolutions=tuple(resolutions),
                        diagnostics=tuple(local_diagnostics),
                        existence_values=any_values,
                        predicate_expression=record,
                    )
                )
            let_values[occurrence.binding.name] = normalized
        if occurrence.binding.name not in invalid_names:
            prior_names.add(occurrence.binding.name)

    namespace_tuple = tuple(binding_namespaces)
    inadmissible = tuple(
        occurrence
        for occurrence in occurrences
        if occurrence.binding.name in invalid_names
    )
    if (
        inadmissible
        or blocked_dependencies
        or blocking_resolutions
        or unknown_types
        or any(diagnostic.severity is Severity.ERROR for diagnostic in diagnostics)
        or len(values) != len(occurrences)
    ):
        return ProjectNonConcreteJoinedLetNamespaces(
            binding_environment=binding_environment,
            occurrences=occurrences,
            post_join_input=post_join_input,
            binding_namespaces=namespace_tuple,
            inadmissible_occurrences=inadmissible,
            blocked_dependency_references=tuple(blocked_dependencies),
            blocking_resolutions=tuple(blocking_resolutions),
            unknown_type_occurrences=tuple(unknown_types),
            diagnostics=tuple(diagnostics),
            admitted_values=tuple(values),
            written_lets=let_values,
            unadmitted_value_types=MappingProxyType(unadmitted),
        )
    value_tuple = tuple(values)
    post_let = ProjectJoinedScalarNamespace(
        binding_environment=binding_environment,
        occurrences=occurrences,
        stage=ProjectScalarNamespaceStage.POST_LET,
        let_values=value_tuple,
        written_lets=let_values,
    )
    return ProjectConcreteJoinedLetNamespaces(
        binding_environment=binding_environment,
        occurrences=occurrences,
        post_join_input=post_join_input,
        binding_namespaces=namespace_tuple,
        values=value_tuple,
        post_let=post_let,
        diagnostics=tuple(diagnostics),
    )
