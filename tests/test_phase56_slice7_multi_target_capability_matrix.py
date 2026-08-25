from __future__ import annotations

from dataclasses import fields, is_dataclass
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto._project as project_package
import pietto._project.capability_matrix as matrix_module
import test_phase56_slice6_exact_capability_requirement_checking as slice6

from pietto._project.capability_availability import (
    DeclaredCapabilityProfileAvailabilityReady,
    build_declared_capability_profile_availability,
)
from pietto._project.capability_checking import (
    CapabilityRequirementStatus,
    PackageCapabilityRequirementsBlocked,
    PackageCapabilityRequirementsChecked,
    PackageCapabilityRequirementsUndeclared,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingMatrixCell,
    CapabilityCheckingMatrixRow,
    CapabilityCheckingTargetContext,
    CapabilityCheckingTargetColumn,
    PackageCapabilityCheckingMatrix,
    build_package_capability_checking_matrix,
)
from pietto._project.package_load_plan import LoadedDependencyPackage
from pietto._project.package_loader import LoadedRootPackage
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityKey,
    CapabilitySupport,
)


@pytest.fixture(scope="module")
def loaded_packages(
    tmp_path_factory: pytest.TempPathFactory,
) -> tuple[LoadedRootPackage, LoadedDependencyPackage]:
    return slice6.slice5._loaded_packages(tmp_path_factory.mktemp("slice7-packages"))


def _context(
    position: int,
    composition: CapabilityProfileCompositionSuccess,
    availability: DeclaredCapabilityProfileAvailabilityReady | None = None,
) -> CapabilityCheckingTargetContext:
    return CapabilityCheckingTargetContext(
        position,
        composition,
        slice6._availability(composition) if availability is None else availability,
    )


def test_one_target_context_produces_one_canonical_column(tmp_path: Path) -> None:
    package, _dependency = slice6.slice5._loaded_packages(tmp_path)
    composition = slice6._composition()
    availability = slice6._availability(composition)
    context = CapabilityCheckingTargetContext(0, composition, availability)
    matrix = build_package_capability_checking_matrix(
        package,
        None,
        (context,),
    )

    assert isinstance(matrix, PackageCapabilityCheckingMatrix)
    assert matrix.package is package
    assert matrix.binding is None
    assert matrix.contexts == (context,)
    assert matrix.columns[0].context is context
    assert matrix.columns[0].position == 0
    assert matrix.rows == ()


def test_zero_target_input_is_exact_and_unordered_inputs_fail_closed(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    empty = build_package_capability_checking_matrix(package, None, ())
    assert empty.contexts == empty.columns == empty.rows == ()
    composition = slice6._composition()
    context = _context(0, composition)
    with pytest.raises(ValueError, match="ordered target iterable"):
        build_package_capability_checking_matrix(package, None, {context})
    with pytest.raises(ValueError, match="ordered target iterable"):
        build_package_capability_checking_matrix(
            package,
            None,
            cast(Any, {"target": context}),
        )


def test_target_input_order_is_exact_and_not_value_sorted(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    z_target = slice6._composition()
    a_target = slice6._composition()
    contexts = (_context(0, z_target), _context(1, a_target))
    matrix = build_package_capability_checking_matrix(package, None, contexts)

    assert matrix.contexts == contexts
    assert tuple(column.context for column in matrix.columns) == contexts
    assert tuple(column.position for column in matrix.columns) == (0, 1)


def test_exact_duplicate_target_context_is_rejected_with_positions(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    composition = slice6._composition()
    availability = slice6._availability(composition)
    contexts = (
        _context(0, composition, availability),
        _context(1, composition, availability),
    )
    with pytest.raises(ValueError, match="position 1 duplicates position 0"):
        build_package_capability_checking_matrix(package, None, contexts)


def test_distinct_equal_target_authorities_remain_separate_columns(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first = slice6._composition()
    second = slice6._composition()
    assert first == second and first is not second
    contexts = (_context(0, first), _context(1, second))
    matrix = build_package_capability_checking_matrix(package, None, contexts)

    assert len(matrix.columns) == 2
    assert matrix.columns[0].context.composition is first
    assert matrix.columns[1].context.composition is second


def test_binding_none_preserves_all_undeclared_columns_and_zero_rows(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    contexts = (_context(0, slice6._composition()), _context(1, slice6._composition()))
    matrix = build_package_capability_checking_matrix(package, None, contexts)

    assert matrix.binding is None
    assert matrix.rows == ()
    assert all(
        isinstance(column.result, PackageCapabilityRequirementsUndeclared)
        for column in matrix.columns
    )
    assert all(column.result.package is package for column in matrix.columns)


def test_explicit_empty_binding_yields_zero_rows_but_keeps_checked_and_blocked_columns(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    checked_composition = slice6._composition()
    blocked_composition = slice6._composition()
    empty_availability = build_declared_capability_profile_availability(
        slice6.slice5._compiler_ledger()
    )
    assert isinstance(empty_availability, DeclaredCapabilityProfileAvailabilityReady)
    binding = slice6._binding(package)
    contexts = (
        _context(0, checked_composition),
        _context(1, blocked_composition, empty_availability),
    )
    matrix = build_package_capability_checking_matrix(package, binding, contexts)

    assert matrix.binding is binding
    assert matrix.rows == ()
    assert isinstance(matrix.columns[0].result, PackageCapabilityRequirementsChecked)
    assert matrix.columns[0].result.all_satisfied is True
    assert isinstance(matrix.columns[1].result, PackageCapabilityRequirementsBlocked)


def test_nonempty_binding_is_requirement_major_rectangular_and_exact(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    first_key = slice6._SUPPORTED_PROVIDER_FACT.key
    second_key = next(
        fact.key
        for fact in slice6._PROVIDER_FACTS
        if fact.key != first_key and fact.support is CapabilitySupport.SUPPORTED
    )
    first_target = slice6._target_fact(first_key, reference="first")
    second_target = slice6._target_fact(second_key, reference="second")
    first_composition = slice6._composition(first_target, second_target)
    second_composition = slice6._composition(first_target, second_target)
    binding = slice6._binding(package, second_key, first_key)
    contexts = (
        _context(0, first_composition),
        _context(1, second_composition),
    )
    matrix = build_package_capability_checking_matrix(package, binding, contexts)

    assert (
        tuple(row.occurrence for row in matrix.rows) == binding.requirements.occurrences
    )
    assert len(matrix.rows) == 2
    assert all(len(row.cells) == 2 for row in matrix.rows)
    for requirement_position, row in enumerate(matrix.rows):
        for target_position, cell in enumerate(row.cells):
            column = matrix.columns[target_position]
            assert cell.column is column
            assert isinstance(column.result, PackageCapabilityRequirementsChecked)
            assert cell.check is column.result.checks[requirement_position]
            check = cell.check
            assert check is not None
            assert check.occurrence is row.occurrence


def test_blocked_column_contributes_none_cells_without_poisoning_checked_sibling(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    target = slice6._target_fact(key)
    checked_composition = slice6._composition(target)
    blocked_composition = slice6._composition(target)
    empty_availability = build_declared_capability_profile_availability(
        slice6.slice5._compiler_ledger()
    )
    assert isinstance(empty_availability, DeclaredCapabilityProfileAvailabilityReady)
    binding = slice6._binding(package, key)
    matrix = build_package_capability_checking_matrix(
        package,
        binding,
        (
            _context(0, blocked_composition, empty_availability),
            _context(1, checked_composition),
        ),
    )

    assert isinstance(matrix.columns[0].result, PackageCapabilityRequirementsBlocked)
    assert isinstance(matrix.columns[1].result, PackageCapabilityRequirementsChecked)
    assert matrix.rows[0].cells[0].check is None
    assert matrix.rows[0].cells[1].check is matrix.columns[1].result.checks[0]
    check = matrix.rows[0].cells[1].check
    assert check is not None
    assert check.status is CapabilityRequirementStatus.SATISFIED


def test_target_local_extra_availability_is_harmless(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    target = slice6._target_fact(key)
    composition = slice6._composition(target)
    extra = slice6.slice4._base("extra")
    availability = slice6._availability(composition, composition.base, extra)
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, composition, availability),),
    )

    assert matrix.columns[0].context.availability is availability
    assert availability.profiles == (composition.base, extra)
    assert isinstance(matrix.columns[0].result, PackageCapabilityRequirementsChecked)


def _status_vector(
    matrix: PackageCapabilityCheckingMatrix,
) -> tuple[CapabilityRequirementStatus, ...]:
    return tuple(cast(Any, cell.check).status for cell in matrix.rows[0].cells)


def test_cross_target_satisfied_and_unknown_are_retained_as_data(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    satisfied = slice6._composition(slice6._target_fact(key))
    unknown = slice6._composition()
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, satisfied), _context(1, unknown)),
    )

    assert _status_vector(matrix) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNKNOWN,
    )


def test_cross_target_satisfied_and_unsupported_are_retained_as_data(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    satisfied = slice6._composition(slice6._target_fact(key))
    unsupported = slice6._composition(
        slice6._target_fact(key, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    )
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, satisfied), _context(1, unsupported)),
    )

    assert _status_vector(matrix) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.UNSUPPORTED,
    )


def test_cross_target_satisfied_and_conflict_are_retained_as_data(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    satisfied = slice6._composition(slice6._target_fact(key))
    supported = slice6._target_fact(key, reference="supported")
    unsupported = slice6._target_fact(
        key,
        support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        reference="unsupported",
    )
    base = slice6.slice4._base(facts=(supported,))
    overlay = slice6.slice4._overlay("overlay", base.profile, facts=(unsupported,))
    conflict = compose_capability_profiles(base, (overlay,))
    assert isinstance(conflict, CapabilityProfileCompositionSuccess)
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, satisfied), _context(1, conflict)),
    )

    assert _status_vector(matrix) == (
        CapabilityRequirementStatus.SATISFIED,
        CapabilityRequirementStatus.CONFLICT,
    )


def test_absent_and_target_omission_remain_single_target_truth(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    absent_key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="FutureScalar",
        operation="catalog_membership",
        context="builtin_registry",
    )
    absent_target = slice6._composition(slice6._target_fact(absent_key))
    absent_matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, absent_key),
        (_context(0, absent_target),),
    )
    unknown_key = slice6._SUPPORTED_PROVIDER_FACT.key
    unknown_matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, unknown_key),
        (_context(0, slice6._composition()),),
    )

    assert _status_vector(absent_matrix) == (CapabilityRequirementStatus.ABSENT,)
    assert _status_vector(unknown_matrix) == (CapabilityRequirementStatus.UNKNOWN,)


@pytest.mark.parametrize(
    "domain",
    (CapabilityDomain.CONVERSION, CapabilityDomain.EXTENSION_SIGNATURE),
)
def test_reserved_provider_unknown_remains_visible_per_target(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    domain: CapabilityDomain,
) -> None:
    package, _dependency = loaded_packages
    key = CapabilityKey(domain, subject="future", operation="lookup")
    target = slice6._composition(slice6._target_fact(key))
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, target),),
    )

    assert _status_vector(matrix) == (CapabilityRequirementStatus.UNKNOWN,)


def test_count_shape_provider_conflict_remains_visible_in_matrix_cell(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._COUNT_CONFLICT_KEY
    target = slice6._composition(slice6._target_fact(key))
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, target),),
    )
    check = matrix.rows[0].cells[0].check

    assert check is not None
    assert check.status is CapabilityRequirementStatus.CONFLICT


def test_provider_authority_is_target_independent_while_target_lookup_differs(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    found_target = slice6._composition(slice6._target_fact(key))
    omitted_target = slice6._composition()
    matrix = build_package_capability_checking_matrix(
        package,
        slice6._binding(package, key),
        (_context(0, found_target), _context(1, omitted_target)),
    )
    first = matrix.rows[0].cells[0].check
    second = matrix.rows[0].cells[1].check
    assert first is not None and second is not None

    assert first.provider_inputs.key is second.provider_inputs.key
    assert len(first.provider_inputs.facts) == len(second.provider_inputs.facts)
    assert all(
        left is right
        for left, right in zip(
            first.provider_inputs.facts,
            second.provider_inputs.facts,
            strict=True,
        )
    )
    assert first.provider_result == second.provider_result
    assert first.target_result != second.target_result


def test_every_column_retains_same_exact_package_and_binding_authority(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, _dependency = loaded_packages
    key = slice6._SUPPORTED_PROVIDER_FACT.key
    binding = slice6._binding(package, key)
    contexts = (
        _context(0, slice6._composition(slice6._target_fact(key))),
        _context(1, slice6._composition()),
    )
    matrix = build_package_capability_checking_matrix(package, binding, contexts)

    for column in matrix.columns:
        assert column.result.package is package
        assert isinstance(column.result, PackageCapabilityRequirementsChecked)
        assert column.result.binding is binding


def test_foreign_binding_authority_fails_before_column_construction(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
) -> None:
    package, dependency = loaded_packages
    context = _context(0, slice6._composition())
    with pytest.raises(ValueError, match="foreign package binding authority"):
        build_package_capability_checking_matrix(
            package,
            slice6._binding(dependency),
            (context,),
        )


def test_foreign_slice6_result_authority_is_rejected_at_column_boundary(
    loaded_packages: tuple[LoadedRootPackage, LoadedDependencyPackage],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    package, _dependency = loaded_packages
    expected_composition = slice6._composition()
    expected_context = _context(0, expected_composition)
    foreign_composition = slice6._composition()
    foreign_availability = slice6._availability(foreign_composition)
    foreign_result = slice6.check_package_capability_requirements(
        package,
        None,
        foreign_composition,
        foreign_availability,
    )

    monkeypatch.setattr(
        matrix_module,
        "check_package_capability_requirements",
        lambda *_args: foreign_result,
    )
    with pytest.raises(ValueError, match="exact Slice 6 authority"):
        build_package_capability_checking_matrix(
            package,
            None,
            (expected_context,),
        )


def test_matrix_products_are_private_frozen_slotted_and_non_freely_constructible() -> (
    None
):
    carriers = (
        CapabilityCheckingTargetContext,
        CapabilityCheckingTargetColumn,
        CapabilityCheckingMatrixCell,
        CapabilityCheckingMatrixRow,
        PackageCapabilityCheckingMatrix,
    )
    for carrier in carriers:
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
    assert tuple(field.name for field in fields(PackageCapabilityCheckingMatrix)) == (
        "package",
        "binding",
        "contexts",
        "columns",
        "rows",
    )
    for carrier in carriers[1:]:
        with pytest.raises(TypeError):
            carrier()  # type: ignore[call-arg]
    assert matrix_module.__all__ == ()
    for name in (
        "CapabilityCheckingTargetContext",
        "CapabilityCheckingTargetColumn",
        "PackageCapabilityCheckingMatrix",
        "build_package_capability_checking_matrix",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)


def test_matrix_builder_accepts_authorities_not_caller_supplied_results() -> None:
    parameters = tuple(
        inspect.signature(build_package_capability_checking_matrix).parameters
    )
    assert parameters == ("package", "binding", "contexts")
    assert "result" not in parameters
    assert "status" not in parameters


def test_matrix_has_no_portability_classifier_normalization_or_runtime_io() -> None:
    source = inspect.getsource(matrix_module).lower()
    for forbidden in (
        "portable",
        "portability",
        "worst_status",
        "best_target",
        "target.family",
        "dialect=",
        "database connection",
        "installed",
        "pathlib",
        "import os",
        "subprocess",
        "requests",
        "urllib",
        "socket",
        "open(",
        "getcwd",
        "environ",
        "ranking",
        "fallback",
    ):
        assert forbidden not in source
