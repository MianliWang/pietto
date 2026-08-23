"""Private ordered multi-target capability-checking matrix."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass

from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_checking import (
    CapabilityRequirementCheck,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
    PackageCapabilityRequirementsResult,
    PackageCapabilityRequirementsUndeclared,
    check_package_capability_requirements,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
)
from pietto._project.package_load_plan import LoadedDependencyPackage, LoadedPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import CapabilityProfileCompositionSuccess
from pietto.semantic.capability_profiles import CapabilityRequirementOccurrence

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CapabilityCheckingTargetContext:
    position: int
    composition: CapabilityProfileCompositionSuccess
    availability: DeclaredCapabilityProfileAvailabilityReady
    extension_signature_provider_context: ExtensionSignatureProviderContext | None = (
        None
    )

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise ValueError("matrix target context requires a non-negative position")
        if type(self.composition) is not CapabilityProfileCompositionSuccess:
            raise ValueError("matrix target context requires an exact composition")
        if type(self.availability) is not DeclaredCapabilityProfileAvailabilityReady:
            raise ValueError("matrix target context requires exact availability")
        if (
            self.extension_signature_provider_context is not None
            and type(self.extension_signature_provider_context)
            is not ExtensionSignatureProviderContext
        ):
            raise ValueError("matrix target context requires an exact provider context")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityCheckingTargetColumn:
    position: int
    context: CapabilityCheckingTargetContext
    result: PackageCapabilityRequirementsResult

    def __new__(cls) -> CapabilityCheckingTargetColumn:
        raise TypeError("matrix columns are created only by canonical matrix building")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityCheckingMatrixCell:
    column: CapabilityCheckingTargetColumn
    check: CapabilityRequirementCheck | None

    def __new__(cls) -> CapabilityCheckingMatrixCell:
        raise TypeError("matrix cells are created only by canonical matrix building")


@dataclass(frozen=True, slots=True, init=False)
class CapabilityCheckingMatrixRow:
    occurrence: CapabilityRequirementOccurrence
    cells: tuple[CapabilityCheckingMatrixCell, ...]

    def __new__(cls) -> CapabilityCheckingMatrixRow:
        raise TypeError("matrix rows are created only by canonical matrix building")


@dataclass(frozen=True, slots=True, init=False)
class PackageCapabilityCheckingMatrix:
    package: LoadedPackage
    binding: PackageCapabilityRequirementBinding | None
    contexts: tuple[CapabilityCheckingTargetContext, ...]
    columns: tuple[CapabilityCheckingTargetColumn, ...]
    rows: tuple[CapabilityCheckingMatrixRow, ...]

    def __new__(cls) -> PackageCapabilityCheckingMatrix:
        raise TypeError(
            "capability matrices are created only by canonical matrix building"
        )


def _freeze_contexts(
    contexts: Iterable[CapabilityCheckingTargetContext],
) -> tuple[CapabilityCheckingTargetContext, ...]:
    if isinstance(contexts, (str, bytes, Mapping, Set)):
        raise ValueError("capability matrix requires an ordered target iterable")
    try:
        frozen = tuple(contexts)
    except TypeError as exc:
        raise ValueError(
            "capability matrix requires an ordered target iterable"
        ) from exc
    if not frozen or any(
        type(context) is not CapabilityCheckingTargetContext for context in frozen
    ):
        raise ValueError("capability matrix requires exact target contexts")
    if any(context.position != position for position, context in enumerate(frozen)):
        raise ValueError("matrix target positions must be dense and caller ordered")
    seen: dict[tuple[int, int, int], int] = {}
    for context in frozen:
        key = (
            id(context.composition),
            id(context.availability),
            id(context.extension_signature_provider_context),
        )
        first = seen.setdefault(key, context.position)
        if first != context.position:
            raise ValueError(
                f"matrix target position {context.position} duplicates position {first}"
            )
    return frozen


def _column(
    context: CapabilityCheckingTargetContext,
    result: PackageCapabilityRequirementsResult,
) -> CapabilityCheckingTargetColumn:
    column = object.__new__(CapabilityCheckingTargetColumn)
    object.__setattr__(column, "position", context.position)
    object.__setattr__(column, "context", context)
    object.__setattr__(column, "result", result)
    return column


def _canonical_column(
    package: LoadedPackage,
    binding: PackageCapabilityRequirementBinding | None,
    context: CapabilityCheckingTargetContext,
) -> CapabilityCheckingTargetColumn:
    result = check_package_capability_requirements(
        package,
        binding,
        context.composition,
        context.availability,
        context.extension_signature_provider_context,
    )
    if (
        result.package is not package
        or result.composition is not context.composition
        or result.availability is not context.availability
    ):
        raise ValueError("matrix column requires exact Slice 6 authority")
    if binding is None:
        if type(result) is not PackageCapabilityRequirementsUndeclared:
            raise ValueError("binding-free matrix column requires UNDECLARED result")
    elif (
        not isinstance(
            result,
            (
                PackageCapabilityRequirementsBlocked,
                PackageCapabilityRequirementsChecked,
            ),
        )
        or result.binding is not binding
    ):
        raise ValueError("bound matrix column requires exact binding authority")
    return _column(context, result)


def _cell(
    column: CapabilityCheckingTargetColumn,
    check: CapabilityRequirementCheck | None,
) -> CapabilityCheckingMatrixCell:
    cell = object.__new__(CapabilityCheckingMatrixCell)
    object.__setattr__(cell, "column", column)
    object.__setattr__(cell, "check", check)
    return cell


def _row(
    occurrence: CapabilityRequirementOccurrence,
    cells: tuple[CapabilityCheckingMatrixCell, ...],
) -> CapabilityCheckingMatrixRow:
    row = object.__new__(CapabilityCheckingMatrixRow)
    object.__setattr__(row, "occurrence", occurrence)
    object.__setattr__(row, "cells", cells)
    return row


def build_package_capability_checking_matrix(
    package: LoadedPackage,
    binding: PackageCapabilityRequirementBinding | None,
    contexts: Iterable[CapabilityCheckingTargetContext],
) -> PackageCapabilityCheckingMatrix:
    if type(package) not in {LoadedRootPackage, LoadedDependencyPackage}:
        raise ValueError("capability matrix requires an exact loaded package")
    if binding is not None:
        if type(binding) is not PackageCapabilityRequirementBinding:
            raise ValueError("capability matrix requires an exact optional binding")
        if binding.package is not package:
            raise ValueError(
                "capability matrix rejects foreign package binding authority"
            )
    frozen_contexts = _freeze_contexts(contexts)
    columns = tuple(
        _canonical_column(package, binding, context) for context in frozen_contexts
    )

    rows: tuple[CapabilityCheckingMatrixRow, ...]
    if binding is None:
        if any(
            type(column.result) is not PackageCapabilityRequirementsUndeclared
            for column in columns
        ):
            raise AssertionError("binding-free matrix columns must remain undeclared")
        rows = ()
    else:
        matrix_rows: list[CapabilityCheckingMatrixRow] = []
        for requirement_position, occurrence in enumerate(
            binding.requirements.occurrences
        ):
            cells: list[CapabilityCheckingMatrixCell] = []
            for column in columns:
                result = column.result
                if type(result) is PackageCapabilityRequirementsChecked:
                    check = result.checks[requirement_position]
                    if check.occurrence is not occurrence:
                        raise AssertionError(
                            "checked matrix cells must retain exact requirement authority"
                        )
                    cells.append(_cell(column, check))
                elif type(result) is PackageCapabilityRequirementsBlocked:
                    cells.append(_cell(column, None))
                else:
                    raise AssertionError(
                        "bound matrix columns must be checked or blocked"
                    )
            matrix_rows.append(_row(occurrence, tuple(cells)))
        rows = tuple(matrix_rows)

    matrix = object.__new__(PackageCapabilityCheckingMatrix)
    object.__setattr__(matrix, "package", package)
    object.__setattr__(matrix, "binding", binding)
    object.__setattr__(matrix, "contexts", frozen_contexts)
    object.__setattr__(matrix, "columns", columns)
    object.__setattr__(matrix, "rows", rows)
    return matrix
