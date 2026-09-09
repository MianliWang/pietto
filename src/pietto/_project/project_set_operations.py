"""Private set-operation evidence over exact completed visible operand fields."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_relation_resolution import ProjectResolvedSetOperand
from pietto._project.project_completion import (
    ProjectCompletion,
    ProjectEffectiveOutputEntry,
    ProjectCompletionDependency,
)
from pietto._project.project_row_equivalence import (
    ProjectRowEquivalenceInput,
    ProjectRowEquivalenceField,
    compatible_row_types,
)
from pietto._project.model import ProjectRowFieldNullability, ProjectResolvedType
from pietto.ast_nodes import SetRelationDef, SetOperationKind, SetOperationQuantifier
from pietto.errors import Diagnostic, Severity, SourceLocation

if TYPE_CHECKING:
    from pietto._project.project_final_outputs import (
        ProjectEffectiveOutputCompletionEntry,
        ProjectEffectiveJoinInputAuthority,
    )

__all__: tuple[str, ...] = ()


class ProjectSetFailureReason(StrEnum):
    QUANTIFIER_REQUIRED = "quantifier_required"
    OPERAND_ARITY = "operand_arity"
    INPUT_UNAVAILABLE = "input_unavailable"
    WIDTH_MISMATCH = "width_mismatch"
    TYPE_MISMATCH = "type_mismatch"
    EQUIVALENCE_UNSUPPORTED = "equivalence_unsupported"


class ProjectSetMultiplicityLaw(StrEnum):
    UNION_ALL = "union_all"
    UNION_DISTINCT = "union_distinct"
    INTERSECT_ALL = "intersect_all"
    INTERSECT_DISTINCT = "intersect_distinct"
    EXCEPT_ALL = "except_all"
    EXCEPT_DISTINCT = "except_distinct"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetInputScope:
    completion: ProjectCompletion = field(repr=False)
    base_entry: ProjectEffectiveOutputEntry = field(repr=False)
    available: tuple[ProjectEffectiveOutputCompletionEntry, ...] = field(repr=False)
    references: tuple[ProjectResolvedSetOperand, ...] = field(init=False)

    def __post_init__(self) -> None:
        from pietto._project.project_final_outputs import (
            ProjectCompletedEffectiveOutput,
            ProjectCompletedSetOutput,
            ProjectEffectiveOutputCompletionTerminal,
        )
        from pietto._project.project_completion import (
            ProjectExistingEffectiveOutput,
            ProjectEffectiveOutputTerminal,
        )

        owner = self.base_entry.owner
        if not isinstance(owner.definition, SetRelationDef) or not any(
            self.base_entry is e for e in self.completion.entries
        ):
            raise ValueError("Set scope requires its exact completion owner.")
        if any(owner is item for item in self.completion.topology.blocked_owners):
            raise ValueError("Cyclic set scope cannot be constructed.")
        prefix = list(self.completion.topology.blocked_owners)
        for predecessor in self.completion.schedule:
            if predecessor is owner:
                break
            prefix.append(predecessor)
        if (
            type(self.available) is not tuple
            or len(self.available) != len(prefix)
            or any(
                type(entry)
                not in {
                    ProjectExistingEffectiveOutput,
                    ProjectEffectiveOutputTerminal,
                    ProjectCompletedEffectiveOutput,
                    ProjectCompletedSetOutput,
                    ProjectEffectiveOutputCompletionTerminal,
                }
                or entry.owner is not expected
                for entry, expected in zip(self.available, prefix, strict=True)
            )
        ):
            raise ValueError(
                "Set scope requires the exact dependency-first available prefix."
            )
        for entry in self.available:
            retained = self.completion.find_owner(entry.owner)
            base = (
                entry
                if isinstance(
                    entry,
                    (ProjectExistingEffectiveOutput, ProjectEffectiveOutputTerminal),
                )
                else entry.base_entry
            )
            if len(retained) != 1 or retained[0] is not base:
                raise ValueError("Set scope cannot retain a foreign producer entry.")
        refs = tuple(
            r
            for r in self.completion.topology.set_operands
            if r.reference.owner is owner
        )
        if len(refs) != len(owner.definition.body.operands):
            raise ValueError("Set scope must retain every exact operand occurrence.")
        object.__setattr__(self, "references", refs)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetOperandUse:
    scope: ProjectSetInputScope = field(repr=False)
    resolution: ProjectResolvedSetOperand = field(repr=False)
    dependency: ProjectCompletionDependency = field(repr=False)
    authority: ProjectEffectiveJoinInputAuthority = field(repr=False)
    fields: tuple[ProjectRowEquivalenceField, ...] = field(init=False)

    def __post_init__(self) -> None:
        from pietto._project.project_final_outputs import (
            ProjectEffectiveJoinInputAuthority,
        )

        if type(self.authority) is not ProjectEffectiveJoinInputAuthority:
            raise TypeError("Set use requires an exact completed-entry authority.")
        reference = self.resolution.reference
        target = self.resolution.target_symbol
        if (
            not any(self.resolution is r for r in self.scope.references)
            or not any(self.dependency is d for d in self.scope.base_entry.dependencies)
            or self.dependency.evidence is not self.resolution
            or target is None
            or self.authority.owner is not target.target_occurrence
            or self.authority.completion is not self.scope.completion
            or not any(self.authority.entry is e for e in self.scope.available)
            or self.dependency.dependency_ordinal != reference.operand_ordinal
        ):
            raise ValueError(
                "Set use lost exact operand/dependency/current-entry authority."
            )
        self.authority.validate()
        types = (
            self.scope.completion.plan.attribution._authority.type_source_resolutions
        )
        object.__setattr__(
            self,
            "fields",
            tuple(
                ProjectRowEquivalenceField(
                    selected=ProjectRowEquivalenceInput(
                        authority=self.authority, field_position=i
                    ),
                    types=types,
                )
                for i in range(len(self.authority.field_parts()))
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetColumn:
    uses: tuple[ProjectSetOperandUse, ...] = field(repr=False)
    position: int
    kind: SetOperationKind
    inputs: tuple[ProjectRowEquivalenceField, ...] = field(init=False)
    nullability: ProjectRowFieldNullability = field(init=False)
    resolved_type: ProjectResolvedType = field(init=False)

    def __post_init__(self) -> None:
        if (
            not self.uses
            or type(self.position) is not int
            or any(not 0 <= self.position < len(use.fields) for use in self.uses)
        ):
            raise ValueError("Set column requires a complete positional field map.")
        inputs = tuple(use.fields[self.position] for use in self.uses)
        if not all(compatible_row_types(inputs[0], item) for item in inputs):
            raise ValueError("Set column requires exact compatible type evidence.")
        states = tuple(item.selected.field.nullability for item in inputs)
        if self.kind is SetOperationKind.EXCEPT:
            state = states[0]
        elif (
            self.kind is SetOperationKind.INTERSECT
            and ProjectRowFieldNullability.NON_NULL in states
        ):
            state = ProjectRowFieldNullability.NON_NULL
        elif all(state is ProjectRowFieldNullability.NON_NULL for state in states):
            state = ProjectRowFieldNullability.NON_NULL
        elif ProjectRowFieldNullability.UNKNOWN in states:
            state = ProjectRowFieldNullability.UNKNOWN
        else:
            state = ProjectRowFieldNullability.NULLABLE
        object.__setattr__(self, "inputs", inputs)
        object.__setattr__(self, "nullability", state)
        resolved = inputs[0].selected.field.resolved_type
        object.__setattr__(
            self,
            "resolved_type",
            ProjectResolvedType(
                name=resolved.name, kind=resolved.kind, symbol=resolved.symbol
            ),
        )

    @property
    def membership_sources(
        self,
    ) -> tuple[tuple[ProjectSetOperandUse, ProjectRowEquivalenceField], ...]:
        return tuple(zip(self.uses, self.inputs, strict=True))

    @property
    def value_sources(
        self,
    ) -> tuple[tuple[ProjectSetOperandUse, ProjectRowEquivalenceField], ...]:
        sources = self.membership_sources
        return sources[:1] if self.kind is SetOperationKind.EXCEPT else sources


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetOperation:
    scope: ProjectSetInputScope = field(repr=False)
    uses: tuple[ProjectSetOperandUse, ...]
    columns: tuple[ProjectSetColumn, ...] = field(init=False)
    owner: ProjectDeclarationOccurrence = field(init=False)
    multiplicity: ProjectSetMultiplicityLaw = field(init=False)
    requires_equivalence: bool = field(init=False)
    full_row_unique: bool = field(init=False)

    def __post_init__(self) -> None:
        owner = self.scope.base_entry.owner
        definition = owner.definition
        if not isinstance(definition, SetRelationDef):
            raise TypeError("Set operation requires an exact set body.")
        body = definition.body
        if (
            body.quantifier is None
            or len(body.operands) < 2
            or len(self.uses) != len(body.operands)
        ):
            raise ValueError(
                "Set operation requires explicit quantifier and complete arity."
            )
        if any(
            use.scope is not self.scope or use.resolution is not resolution
            for use, resolution in zip(self.uses, self.scope.references, strict=True)
        ):
            raise ValueError(
                "Set operation cannot reorder or deduplicate operand uses."
            )
        width = len(self.uses[0].fields)
        if any(len(use.fields) != width for use in self.uses):
            raise ValueError("Set operation requires equal concrete widths.")
        requires = (
            body.kind is not SetOperationKind.UNION
            or body.quantifier is SetOperationQuantifier.DISTINCT
        )
        if requires and any(
            f.reason is not None for use in self.uses for f in use.fields
        ):
            raise ValueError("Set operation lacks required row-equivalence capability.")
        object.__setattr__(self, "owner", owner)
        object.__setattr__(
            self,
            "multiplicity",
            ProjectSetMultiplicityLaw(f"{body.kind.value}_{body.quantifier.value}"),
        )
        object.__setattr__(self, "requires_equivalence", requires)
        object.__setattr__(
            self, "full_row_unique", body.quantifier is SetOperationQuantifier.DISTINCT
        )
        object.__setattr__(
            self,
            "columns",
            tuple(
                ProjectSetColumn(uses=self.uses, position=i, kind=body.kind)
                for i in range(width)
            ),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSetFailure:
    scope: ProjectSetInputScope = field(repr=False)
    reason: ProjectSetFailureReason
    blockers: tuple[object, ...] = field(repr=False)
    diagnostics: tuple[Diagnostic, ...]


def set_diagnostic(
    scope: ProjectSetInputScope, code: str, message: str, position: int | None = None
) -> Diagnostic:
    definition = scope.base_entry.owner.definition
    assert isinstance(definition, SetRelationDef)
    span = (
        definition.body.operator_span
        if position is None
        else definition.body.operands[position].span
    )
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
