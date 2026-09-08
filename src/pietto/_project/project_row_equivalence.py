"""Exact DISTINCT type capabilities; no value evaluator or predicate equality."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING

from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.module_resolution import (
    ProjectResolvedModuleTypeReference,
    ProjectTypeSourceResolutionSet,
    ProjectModuleTypeReferenceRole,
)
from pietto.ast_nodes import TypeExpr
from pietto.semantic.analyzer import _decimal_precision_scale_fact
from pietto.semantic.model import DecimalPrecisionScale

if TYPE_CHECKING:
    from pietto._project.project_final_outputs import ProjectCompletedOutputField

__all__: tuple[str, ...] = ()


class ProjectRowEquivalenceReason(StrEnum):
    UNKNOWN_TYPE = "unknown_type"
    FLOAT_EQUIVALENCE_DEFERRED = "float_equivalence_deferred_to_phase72"
    UNSUPPORTED_TYPE = "unsupported_type"
    DECIMAL_PARAMETERS_MISSING = "decimal_parameters_missing_or_unpropagated"
    DECIMAL_PARAMETERS_INVALID = "decimal_parameters_invalid"
    TYPE_EVIDENCE_MISMATCH = "type_evidence_mismatch"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRowEquivalenceField:
    """Capability attached to one exact visible selected field and type root."""

    selected: ProjectCompletedOutputField = field(repr=False)
    types: ProjectTypeSourceResolutionSet = field(repr=False)
    resolution: ProjectResolvedModuleTypeReference | None = field(init=False)
    decimal_type_expr: TypeExpr | None = field(init=False)
    decimal: DecimalPrecisionScale | None = field(init=False)
    reason: ProjectRowEquivalenceReason | None = field(init=False)

    def __post_init__(self) -> None:
        if type(self.types) is not ProjectTypeSourceResolutionSet:
            raise TypeError("Row equivalence requires exact module type authority.")
        selected = self.selected
        selected.__post_init__()
        resolved = selected.field.resolved_type
        definition = selected.field.field_def
        matches = (
            ()
            if definition is None
            else tuple(
                item
                for environment in self.types.environments
                for item in environment.find_type_expr(definition.type_expr)
                if item.reference.type_expr is definition.type_expr
            )
        )
        resolution = matches[0] if len(matches) == 1 else None
        decimal_expr = None
        decimal = None
        reason = None
        if resolved.kind is ProjectResolvedTypeKind.UNKNOWN:
            reason = ProjectRowEquivalenceReason.UNKNOWN_TYPE
        elif definition is not None and (
            resolution is None
            or resolution.canonical_kind is not resolved.kind
            or resolution.canonical_name != resolved.name
        ):
            reason = ProjectRowEquivalenceReason.TYPE_EVIDENCE_MISMATCH
        elif resolved.kind is ProjectResolvedTypeKind.BUILTIN:
            # Canonical builtin names here are existing type-resolution facts.
            if resolved.name == "Float":
                reason = ProjectRowEquivalenceReason.FLOAT_EQUIVALENCE_DEFERRED
            elif resolved.name in {"Any", "Bytes", "Json"}:
                reason = ProjectRowEquivalenceReason.UNSUPPORTED_TYPE
            elif resolved.name == "Decimal":
                if resolution is not None:
                    decimal_expr = resolution.reference.type_expr
                    if resolution.alias_chain:
                        terminal = resolution.alias_chain[-1]
                        bases = tuple(
                            item.reference.type_expr
                            for environment in self.types.environments
                            for item in environment.type_resolutions
                            if item.reference.owner.identity == terminal
                            and item.reference.role
                            is ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE
                            and item.direct_kind is ProjectResolvedTypeKind.BUILTIN
                        )
                        decimal_expr = bases[0] if len(bases) == 1 else None
                if decimal_expr is None:
                    reason = ProjectRowEquivalenceReason.DECIMAL_PARAMETERS_MISSING
                else:
                    decimal, diagnostic = _decimal_precision_scale_fact(decimal_expr)
                    if diagnostic is not None:
                        reason = ProjectRowEquivalenceReason.DECIMAL_PARAMETERS_INVALID
                    elif decimal is None:
                        reason = ProjectRowEquivalenceReason.DECIMAL_PARAMETERS_MISSING
            elif resolved.name not in {
                "Bool",
                "Int",
                "Text",
                "Date",
                "Timestamp",
                "UUID",
            }:
                reason = ProjectRowEquivalenceReason.UNSUPPORTED_TYPE
        elif resolved.kind is not ProjectResolvedTypeKind.ENUM:
            reason = ProjectRowEquivalenceReason.UNSUPPORTED_TYPE
        object.__setattr__(self, "resolution", resolution)
        object.__setattr__(self, "decimal_type_expr", decimal_expr)
        object.__setattr__(self, "decimal", decimal)
        object.__setattr__(self, "reason", reason)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectRowEquivalence:
    """Complete source-ordered capability assessment, confined to visible fields."""

    fields: tuple[ProjectCompletedOutputField, ...] = field(repr=False)
    types: ProjectTypeSourceResolutionSet = field(repr=False)
    evidence: tuple[ProjectRowEquivalenceField, ...] = field(init=False)

    def __post_init__(self) -> None:
        if type(self.fields) is not tuple or not self.fields:
            raise ValueError(
                "Row equivalence requires the complete visible field tuple."
            )
        owner = self.fields[0].owner
        if any(
            item.owner is not owner or item.selected_output_ordinal != i
            for i, item in enumerate(self.fields)
        ):
            raise ValueError("Row equivalence requires exact visible source order.")
        object.__setattr__(
            self,
            "evidence",
            tuple(
                ProjectRowEquivalenceField(selected=item, types=self.types)
                for item in self.fields
            ),
        )

    @property
    def supported(self) -> bool:
        return all(item.reason is None for item in self.evidence)
