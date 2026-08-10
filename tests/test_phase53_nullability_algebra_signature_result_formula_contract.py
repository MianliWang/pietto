from __future__ import annotations

import ast
import hashlib
import inspect
import subprocess
from dataclasses import fields, is_dataclass
from pathlib import Path
from typing import cast

from _phase54_active_gate2_manifest import (
    phase54_publication_clean_topic_is_active,
    phase54_publication_topic_branch,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto.semantic.nullability_formulas as nullability_formulas
from pietto.semantic.generic_compatibility import (
    ConcreteTypeExpression,
    GenericSignature,
    LogicalTypeIdentity,
    ParameterDefault,
    SignatureMatch,
    SignatureParameter,
    TypeVariable,
    VariableTypeExpression,
    bind_signature,
)
from pietto.semantic.model import EffectiveNullability, TypeKind
from pietto.semantic.nullability_formulas import (
    AlwaysNullableFormula,
    AnyNullableFormula,
    AnyOfFormula,
    NonNullFormula,
    NullabilityArgumentEvidence,
    NullabilityDefaultEvidence,
    NullabilityEvaluationContext,
    NullabilityEvaluationEvidence,
    NullabilityEvaluationFailureReason,
    NullabilityEvaluationMatch,
    NullabilityEvaluationUnsupported,
    NullabilityFormula,
    NullabilityFormulaKind,
    NullableFormula,
    NullableIfDefaultOmittedFormula,
    SameAsArgumentFormula,
    SignatureResultFormula,
    evaluate_signature_result_nullability,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/nullability_formulas.py"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase53-nullability-algebra-signature-result-formula-contract-v1.md"
)
PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SELF_PATH = Path(__file__).resolve()
GENERIC_TEST_PATH = (
    REPO_ROOT
    / "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py"
)

SPEC_H1 = (
    "Phase 53 Slice 5 Nullability Algebra And Signature Result-formula Foundation v1"
)
SPEC_H2 = (
    "Status And Slice Identity",
    "Existing Concrete Nullability Authority",
    "Existing Slice 4 Generic Signature Authority",
    "Private Module Placement And No-integration Boundary",
    "Signature-result Sibling-wrapper Architecture",
    "Formula Kind And Carrier Inventory",
    "NULLABLE And ALWAYS_NULLABLE Distinction",
    "Argument Index And Ordered Collection Contract",
    "SAME_AS_ARG Truth Table",
    "ANY_NULLABLE Truth Table",
    "NULLABLE_IF_DEFAULT_OMITTED Contract",
    "ANY_OF Composition And Truth Table",
    "Exact Boundedness Contract",
    "Evaluation Context Contract",
    "Evaluation Result And Evidence Contract",
    "UNKNOWN Preservation Contract",
    "Optional/default And Signature Cross-validation",
    "Constructor And Evaluation Failure Boundary",
    "lag And lead Readiness Proof",
    "Current Semantic And Project Non-integration",
    "Phase 64 Exclusions",
    "Public Privacy And Serialization Boundary",
    "Positive Formula Matrix",
    "Negative And Fail-closed Matrix",
    "Grammar AST Generic Generated And Behavior Immutability",
    "Reader Hash Inventory And Repository-state Closure",
    "Validation Depth-one CI And Gate 3 Publication",
    "Deferred Ownership And Stop Conditions",
)
PLAN_H2 = "Slice 5 Nullability Algebra And Signature Result-formula Foundation"
SLICE6_PLAN_H2 = (
    "Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, "
    "And Result Roles"
)
SLICE7_PLAN_H2 = "Slice 7 row_number Direct-field MVP"
SLICE8_PLAN_H2 = "Slice 8 rank / dense_rank And Peer Semantics"
SLICE9_PLAN_H2 = "Slice 9 percent_rank / cume_dist / ntile"
SLICE10_PLAN_H2 = "Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics"
SLICE11_PLAN_H2 = (
    "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism"
)
SLICE12_PLAN_H2 = "Slice 12 lag / lead Navigation, Offset, Default, And Nullability"
SLICE13_PLAN_H2 = (
    "Slice 13 — Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let "
    "Visibility"
)
SLICE14_PLAN_H2 = (
    "Slice 14 — Multiple Window Outputs, Final-order Alias, Downstream Schema, "
    "And Lineage"
)
SLICE15_PLAN_H2 = (
    "Slice 15 — Window IR, Dual-backend Lowering, And Window-function Facts"
)

TEST_FUNCTIONS = (
    "test_slice5_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_private_module_enum_carrier_and_privacy_shapes_are_exact",
    "test_formula_kind_values_and_union_inventory_are_exact",
    "test_constant_formulas_evaluate_with_distinct_ordered_evidence",
    "test_nullable_and_always_nullable_are_distinct_structural_identities",
    "test_argument_index_scalar_validation_is_exact",
    "test_any_nullable_index_tuple_order_duplicates_and_bounds_are_exact",
    "test_any_of_child_tuple_order_duplicates_and_arity_are_exact",
    "test_formula_depth_node_and_child_bounds_are_exact",
    "test_same_as_argument_three_state_truth_table_is_exact",
    "test_any_nullable_all_non_null_and_ordered_evidence_are_exact",
    "test_any_nullable_nullable_precedence_is_exact",
    "test_any_nullable_unknown_precedence_is_exact",
    "test_default_omission_formula_supplied_and_omitted_results_are_exact",
    "test_any_of_complete_three_state_truth_table_is_exact",
    "test_any_of_evaluates_every_child_in_declared_order",
    "test_evaluation_context_container_member_and_order_shapes_are_exact",
    "test_signature_result_wrapper_accepts_valid_formula_references",
    "test_signature_result_wrapper_rejects_out_of_range_references",
    "test_default_reference_requires_optional_omitted_marker",
    "test_incompatible_contexts_return_ordered_structured_unsupported",
    "test_omitted_same_as_arg_fails_closed_and_any_nullable_is_neutral",
    "test_evaluation_evidence_carrier_invariants_are_exact",
    "test_evaluation_unsupported_carrier_invariants_are_exact",
    "test_formula_result_and_evidence_equality_hash_repr_are_repeatable",
    "test_lag_lead_omitted_default_readiness_formula_is_exact",
    "test_lag_lead_supplied_default_truth_matrix_is_exact",
    "test_lag_and_lead_readiness_associations_are_identity_free",
    "test_signature_match_omissions_compose_without_type_binding_changes",
    "test_generic_compatibility_module_and_slice4_contract_are_byte_locked",
    "test_current_semantic_analyzer_and_window_paths_do_not_import_nullability_formulas",
    "test_concrete_semantic_project_and_aggregate_nullability_authority_is_locked",
    "test_project_ir_sql_cli_serializer_and_public_exports_are_unchanged",
    "test_grammar_ast_generated_parser_window_and_generic_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_hash_closure_is_exact",
    "test_slice5_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_and_dirty_overlay_are_exact",
    "test_validation_gate3_and_no_behavior_boundaries_are_locked",
)
TEST_ITEM_COUNTS = (
    1,
    1,
    1,
    3,
    1,
    6,
    7,
    7,
    6,
    3,
    4,
    6,
    5,
    2,
    9,
    4,
    8,
    6,
    4,
    5,
    8,
    4,
    8,
    5,
    4,
    3,
    9,
    2,
    4,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
    1,
)

ADDED_PATHS = (
    "docs/spec/phase53-completion-audit-and-status-lock-v1.md",
    "tests/test_phase53_completion_audit_and_status_lock.py",
)
MODIFIED_PATHS = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md",
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_aggregate_signature_algebra_facts.py",
    "tests/test_phase52_completion_audit_and_status_lock.py",
    "tests/test_phase52_expression_stage_clause_capability_facts.py",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py",
    "tests/test_phase52_scalar_function_operator_signature_facts.py",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_multiple_window_outputs_final_order_alias_downstream_schema_lineage_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
)

BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
FINAL_COMPILER_DIGEST = (
    "4496dd078a2e56b9beb218554b6aa3b6ee6c88e3d85237f19f53b4eb2c5810bb"
)
FINAL_SEMANTIC_DIGEST = (
    "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
)
FINAL_PHASE15_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
FINAL_SOURCE_SHA256 = "f4b39fc1446af80ec223b0043ee3e76700dd83224eea8e2a5f60a609a5dd5933"
FINAL_SPEC_SHA256 = "a37141cd86b32a3325f64d5f0bcda4b6df97c7c89313ba765f24e9f5ee167b2a"
FINAL_PLAN_SHA256 = "3077c2fec0d7e2c4de717973c6403d5a450b8c01fe5846e427363ffcb41a78f5"

INT = LogicalTypeIdentity(name="Int", kind=TypeKind.BUILTIN)
TEXT = LogicalTypeIdentity(name="Text", kind=TypeKind.BUILTIN)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git(*arguments: str, check: bool = True) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def _headings(path: Path) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    h1: list[str] = []
    h2: list[str] = []
    h3: list[str] = []
    for line in path.read_text().splitlines():
        if line.startswith("### "):
            h3.append(line.removeprefix("### "))
        elif line.startswith("## "):
            h2.append(line.removeprefix("## "))
        elif line.startswith("# "):
            h1.append(line.removeprefix("# "))
    return tuple(h1), tuple(h2), tuple(h3)


def _simple_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _two_parameter_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=ConcreteTypeExpression(logical_type=INT),
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _navigation_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=ConcreteTypeExpression(logical_type=INT),
                optional=True,
            ),
            SignatureParameter(
                position=2,
                type_expression=VariableTypeExpression(name="T"),
                optional=True,
                default=ParameterDefault.OMITTED,
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _optional_without_default_signature() -> GenericSignature:
    variable = TypeVariable(name="T", constraints=())
    return GenericSignature(
        type_variables=(variable,),
        parameters=(
            SignatureParameter(
                position=0,
                type_expression=VariableTypeExpression(name="T"),
            ),
            SignatureParameter(
                position=1,
                type_expression=VariableTypeExpression(name="T"),
                optional=True,
            ),
        ),
        result=VariableTypeExpression(name="T"),
    )


def _match(
    formula: NullabilityFormula,
    context: NullabilityEvaluationContext,
    *,
    signature: GenericSignature | None = None,
) -> NullabilityEvaluationMatch:
    association = SignatureResultFormula(
        signature=signature or _simple_signature(),
        nullability=formula,
    )
    result = evaluate_signature_result_nullability(association, context)
    assert type(result) is NullabilityEvaluationMatch
    return cast(NullabilityEvaluationMatch, result)


def _join(
    left: EffectiveNullability,
    right: EffectiveNullability,
) -> EffectiveNullability:
    if EffectiveNullability.NULLABLE in {left, right}:
        return EffectiveNullability.NULLABLE
    if EffectiveNullability.UNKNOWN in {left, right}:
        return EffectiveNullability.UNKNOWN
    return EffectiveNullability.NON_NULL


def _navigation_formula() -> AnyOfFormula:
    return AnyOfFormula(
        children=(
            AnyNullableFormula(argument_indices=(0, 2)),
            NullableIfDefaultOmittedFormula(parameter_index=2),
        )
    )


def _all_repository_paths() -> tuple[str, ...]:
    paths = set(_git("ls-files").splitlines())
    paths.update(_git("ls-files", "--others", "--exclude-standard").splitlines())
    return tuple(sorted(paths))


def _phase54_slice2_paths() -> tuple[frozenset[str], frozenset[str]]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=path.as_posix())
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, frozenset[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in expected
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            assert all(isinstance(item, str) for item in value)
            values[node.targets[0].id] = frozenset(value)
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def _compound_assignment(path: Path) -> tuple[object, ...]:
    tree = ast.parse(path.read_text())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.targets[0], ast.Tuple)
            and tuple(
                element.id
                for element in node.targets[0].elts
                if isinstance(element, ast.Name)
            )
            == ("FOCUSED_OPERANDS", "DIRTY_OVERLAY", "ADDED_PATHS", "MODIFIED_PATHS")
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, tuple)
            return value
    raise AssertionError("compound selector assignment not found")


def test_slice5_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    assert SOURCE_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert SELF_PATH.is_file()
    assert _headings(SPEC_PATH) == ((SPEC_H1,), SPEC_H2, ())
    plan_h1, plan_h2, plan_h3 = _headings(PLAN_PATH)
    assert plan_h1 == (
        "Phase 53 — Window Functions, Generic Signature Compatibility, "
        "And Nullability Foundation",
    )
    assert plan_h2[-12:] == (
        PLAN_H2,
        SLICE6_PLAN_H2,
        SLICE7_PLAN_H2,
        SLICE8_PLAN_H2,
        SLICE9_PLAN_H2,
        SLICE10_PLAN_H2,
        SLICE11_PLAN_H2,
        SLICE12_PLAN_H2,
        SLICE13_PLAN_H2,
        SLICE14_PLAN_H2,
        SLICE15_PLAN_H2,
        "Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, And "
        "No-authority Closure",
    )
    assert plan_h2.count(PLAN_H2) == 1
    assert plan_h2.count(SLICE6_PLAN_H2) == 1
    assert plan_h2.count(SLICE7_PLAN_H2) == 1
    assert plan_h2.count(SLICE8_PLAN_H2) == 1
    assert plan_h2.count(SLICE9_PLAN_H2) == 1
    assert plan_h2.count(SLICE11_PLAN_H2) == 1
    assert plan_h2.count(SLICE12_PLAN_H2) == 1
    assert plan_h2.count(SLICE13_PLAN_H2) == 1
    assert plan_h2.count(SLICE14_PLAN_H2) == 1
    assert plan_h2.count(SLICE15_PLAN_H2) == 1
    assert plan_h3 == ()
    plan = PLAN_PATH.read_text()
    assert "Slice 5 remains `UNSTARTED` throughout Gate 2" in plan
    assert "Phase 53 is `ACTIVE`" in plan


def test_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert nullability_formulas.__all__ == ()
    carrier_types = (
        NonNullFormula,
        NullableFormula,
        SameAsArgumentFormula,
        AnyNullableFormula,
        AlwaysNullableFormula,
        NullableIfDefaultOmittedFormula,
        AnyOfFormula,
        SignatureResultFormula,
        NullabilityEvaluationContext,
        NullabilityArgumentEvidence,
        NullabilityDefaultEvidence,
        NullabilityEvaluationEvidence,
        NullabilityEvaluationMatch,
        NullabilityEvaluationUnsupported,
    )
    for carrier_type in carrier_types:
        assert is_dataclass(carrier_type)
        assert getattr(carrier_type, "__dataclass_params__").frozen is True
        assert "__dict__" not in carrier_type.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier_type).parameters.values()
        )
    tree = ast.parse(SOURCE_PATH.read_text())
    imported_modules = tuple(
        node.module
        for node in tree.body
        if isinstance(node, ast.ImportFrom) and node.module != "__future__"
    )
    assert imported_modules == (
        "dataclasses",
        "enum",
        "pietto.semantic.generic_compatibility",
        "pietto.semantic.model",
    )


def test_formula_kind_values_and_union_inventory_are_exact() -> None:
    assert tuple(NullabilityFormulaKind) == (
        NullabilityFormulaKind.NON_NULL,
        NullabilityFormulaKind.NULLABLE,
        NullabilityFormulaKind.SAME_AS_ARG,
        NullabilityFormulaKind.ANY_NULLABLE,
        NullabilityFormulaKind.ALWAYS_NULLABLE,
        NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED,
        NullabilityFormulaKind.ANY_OF,
    )
    assert tuple(kind.value for kind in NullabilityFormulaKind) == (
        "non_null",
        "nullable",
        "same_as_arg",
        "any_nullable",
        "always_nullable",
        "nullable_if_default_omitted",
        "any_of",
    )
    variants = (
        NonNullFormula,
        NullableFormula,
        SameAsArgumentFormula,
        AnyNullableFormula,
        AlwaysNullableFormula,
        NullableIfDefaultOmittedFormula,
        AnyOfFormula,
    )
    assert (
        tuple(
            field.name
            for variant in variants
            for field in fields(variant)
            if field.name == "kind"
        )
        == ("kind",) * 7
    )
    assert all(
        next(field for field in fields(variant) if field.name == "kind").init is False
        for variant in variants
    )
    source = SOURCE_PATH.read_text()
    assert "ALL_OF" not in source
    assert "class NullabilityFormulaKind" in source


@pytest.mark.parametrize(
    ("formula", "kind", "expected"),
    (
        (
            NonNullFormula(),
            NullabilityFormulaKind.NON_NULL,
            EffectiveNullability.NON_NULL,
        ),
        (
            NullableFormula(),
            NullabilityFormulaKind.NULLABLE,
            EffectiveNullability.NULLABLE,
        ),
        (
            AlwaysNullableFormula(),
            NullabilityFormulaKind.ALWAYS_NULLABLE,
            EffectiveNullability.NULLABLE,
        ),
    ),
    ids=("non-null", "nullable", "always-nullable"),
)
def test_constant_formulas_evaluate_with_distinct_ordered_evidence(
    formula: NullabilityFormula,
    kind: NullabilityFormulaKind,
    expected: EffectiveNullability,
) -> None:
    match = _match(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=(EffectiveNullability.NON_NULL,),
            omitted_positions=(),
        ),
    )
    assert match == NullabilityEvaluationMatch(
        value=expected,
        evidence=NullabilityEvaluationEvidence(kind=kind, value=expected),
    )


def test_nullable_and_always_nullable_are_distinct_structural_identities() -> None:
    nullable = NullableFormula()
    always = AlwaysNullableFormula()
    assert type(nullable) is not type(always)
    assert nullable != always
    assert nullable.kind is NullabilityFormulaKind.NULLABLE
    assert always.kind is NullabilityFormulaKind.ALWAYS_NULLABLE
    assert repr(nullable) != repr(always)
    assert {
        _match(
            formula,
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.UNKNOWN,),
                omitted_positions=(),
            ),
        ).value
        for formula in (nullable, always)
    } == {EffectiveNullability.NULLABLE}


@pytest.mark.parametrize(
    ("carrier", "case", "expected"),
    (
        ("same", "wrong", TypeError),
        ("same", "bool", TypeError),
        ("same", "negative", ValueError),
        ("default", "wrong", TypeError),
        ("default", "bool", TypeError),
        ("default", "negative", ValueError),
    ),
)
def test_argument_index_scalar_validation_is_exact(
    carrier: str,
    case: str,
    expected: type[Exception],
) -> None:
    value: object = "0" if case == "wrong" else True if case == "bool" else -1
    with pytest.raises(expected):
        if carrier == "same":
            SameAsArgumentFormula(argument_index=cast(int, value))
        else:
            NullableIfDefaultOmittedFormula(parameter_index=cast(int, value))


@pytest.mark.parametrize(
    "case",
    ("one", "ordered", "duplicate", "empty", "too-many", "containers", "members"),
)
def test_any_nullable_index_tuple_order_duplicates_and_bounds_are_exact(
    case: str,
) -> None:
    if case == "one":
        assert AnyNullableFormula(argument_indices=(1,)).argument_indices == (1,)
    elif case == "ordered":
        assert AnyNullableFormula(argument_indices=(1, 0)).argument_indices == (1, 0)
    elif case == "duplicate":
        assert AnyNullableFormula(argument_indices=(0, 0)).argument_indices == (0, 0)
    elif case == "empty":
        with pytest.raises(ValueError):
            AnyNullableFormula(argument_indices=())
    elif case == "too-many":
        with pytest.raises(ValueError):
            AnyNullableFormula(argument_indices=(0, 1, 2))
    elif case == "containers":
        for value in ([0], {0}, {"position": 0}):
            with pytest.raises(TypeError):
                AnyNullableFormula(argument_indices=cast(tuple[int, ...], value))
    else:
        for value in ((True,), (-1,), ("0",)):
            with pytest.raises((TypeError, ValueError)):
                AnyNullableFormula(argument_indices=cast(tuple[int, ...], value))


@pytest.mark.parametrize(
    "case",
    ("ordered", "reverse", "duplicate", "empty", "one", "three", "invalid"),
)
def test_any_of_child_tuple_order_duplicates_and_arity_are_exact(case: str) -> None:
    left = NonNullFormula()
    right = NullableFormula()
    if case == "ordered":
        assert AnyOfFormula(children=(left, right)).children == (left, right)
    elif case == "reverse":
        assert AnyOfFormula(children=(right, left)).children == (right, left)
    elif case == "duplicate":
        assert AnyOfFormula(children=(left, left)).children == (left, left)
    elif case == "empty":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(tuple[NullabilityFormula, NullabilityFormula], ())
            )
    elif case == "one":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(tuple[NullabilityFormula, NullabilityFormula], (left,))
            )
    elif case == "three":
        with pytest.raises(ValueError):
            AnyOfFormula(
                children=cast(
                    tuple[NullabilityFormula, NullabilityFormula], (left, right, left)
                )
            )
    else:
        for value in ([left, right], {left, right}, (left, object())):
            with pytest.raises(TypeError):
                AnyOfFormula(
                    children=cast(tuple[NullabilityFormula, NullabilityFormula], value)
                )


@pytest.mark.parametrize(
    "case",
    ("leaf", "maximum", "nested-left", "nested-right", "three-refs", "four-refs"),
)
def test_formula_depth_node_and_child_bounds_are_exact(case: str) -> None:
    signature = _navigation_signature()
    if case == "leaf":
        assert (
            SignatureResultFormula(
                signature=signature, nullability=NonNullFormula()
            ).nullability
            == NonNullFormula()
        )
    elif case == "maximum":
        assert (
            SignatureResultFormula(
                signature=signature, nullability=_navigation_formula()
            ).nullability
            == _navigation_formula()
        )
    elif case == "nested-left":
        nested = AnyOfFormula(
            children=(
                AnyOfFormula(children=(NonNullFormula(), NullableFormula())),
                NonNullFormula(),
            )
        )
        with pytest.raises(ValueError, match="depth"):
            SignatureResultFormula(signature=signature, nullability=nested)
    elif case == "nested-right":
        nested = AnyOfFormula(
            children=(
                NonNullFormula(),
                AnyOfFormula(children=(NullableFormula(), NonNullFormula())),
            )
        )
        with pytest.raises(ValueError, match="depth"):
            SignatureResultFormula(signature=signature, nullability=nested)
    elif case == "three-refs":
        formula = AnyOfFormula(
            children=(
                AnyNullableFormula(argument_indices=(0, 2)),
                SameAsArgumentFormula(argument_index=0),
            )
        )
        with pytest.raises(ValueError, match="references"):
            SignatureResultFormula(signature=signature, nullability=formula)
    else:
        formula = AnyOfFormula(
            children=(
                AnyNullableFormula(argument_indices=(0, 2)),
                AnyNullableFormula(argument_indices=(0, 2)),
            )
        )
        with pytest.raises(ValueError, match="references"):
            SignatureResultFormula(signature=signature, nullability=formula)


@pytest.mark.parametrize("value", tuple(EffectiveNullability))
def test_same_as_argument_three_state_truth_table_is_exact(
    value: EffectiveNullability,
) -> None:
    match = _match(
        SameAsArgumentFormula(argument_index=0),
        NullabilityEvaluationContext(
            argument_nullabilities=(value,), omitted_positions=()
        ),
    )
    assert match.value is value
    assert match.evidence == NullabilityEvaluationEvidence(
        kind=NullabilityFormulaKind.SAME_AS_ARG,
        value=value,
        arguments=(
            NullabilityArgumentEvidence(
                parameter_position=0, supplied=True, value=value, contribution=value
            ),
        ),
    )


@pytest.mark.parametrize("indices", ((0,), (0, 1), (1, 0), (0, 0)))
def test_any_nullable_all_non_null_and_ordered_evidence_are_exact(
    indices: tuple[int, ...],
) -> None:
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=(
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            omitted_positions=(),
        ),
        signature=_two_parameter_signature(),
    )
    assert match.value is EffectiveNullability.NON_NULL
    assert (
        tuple(item.parameter_position for item in match.evidence.arguments) == indices
    )
    assert all(
        item.contribution is EffectiveNullability.NON_NULL
        for item in match.evidence.arguments
    )


@pytest.mark.parametrize(
    "values",
    (
        (EffectiveNullability.NULLABLE,),
        (EffectiveNullability.NULLABLE, EffectiveNullability.NON_NULL),
        (EffectiveNullability.NON_NULL, EffectiveNullability.NULLABLE),
        (EffectiveNullability.NULLABLE, EffectiveNullability.UNKNOWN),
        (EffectiveNullability.UNKNOWN, EffectiveNullability.NULLABLE),
        (EffectiveNullability.NULLABLE, EffectiveNullability.NULLABLE),
    ),
)
def test_any_nullable_nullable_precedence_is_exact(
    values: tuple[EffectiveNullability, ...],
) -> None:
    indices = tuple(range(len(values)))
    signature = _simple_signature() if len(values) == 1 else _two_parameter_signature()
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=values, omitted_positions=()
        ),
        signature=signature,
    )
    assert match.value is EffectiveNullability.NULLABLE
    assert tuple(item.value for item in match.evidence.arguments) == values


@pytest.mark.parametrize(
    ("values", "indices"),
    (
        ((EffectiveNullability.UNKNOWN,), (0,)),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.NON_NULL),
            (0, 1),
        ),
        (
            (EffectiveNullability.NON_NULL, EffectiveNullability.UNKNOWN),
            (0, 1),
        ),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.UNKNOWN),
            (0, 1),
        ),
        (
            (EffectiveNullability.UNKNOWN, EffectiveNullability.NON_NULL),
            (0, 0),
        ),
    ),
)
def test_any_nullable_unknown_precedence_is_exact(
    values: tuple[EffectiveNullability, ...],
    indices: tuple[int, ...],
) -> None:
    signature = _simple_signature() if len(values) == 1 else _two_parameter_signature()
    match = _match(
        AnyNullableFormula(argument_indices=indices),
        NullabilityEvaluationContext(
            argument_nullabilities=values, omitted_positions=()
        ),
        signature=signature,
    )
    assert match.value is EffectiveNullability.UNKNOWN


@pytest.mark.parametrize("omitted", (False, True), ids=("supplied", "omitted"))
def test_default_omission_formula_supplied_and_omitted_results_are_exact(
    omitted: bool,
) -> None:
    context = NullabilityEvaluationContext(
        argument_nullabilities=(
            (EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL)
            if omitted
            else (
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.UNKNOWN,
            )
        ),
        omitted_positions=(2,) if omitted else (),
    )
    match = _match(
        NullableIfDefaultOmittedFormula(parameter_index=2),
        context,
        signature=_navigation_signature(),
    )
    expected = (
        EffectiveNullability.NULLABLE if omitted else EffectiveNullability.NON_NULL
    )
    assert match == NullabilityEvaluationMatch(
        value=expected,
        evidence=NullabilityEvaluationEvidence(
            kind=NullabilityFormulaKind.NULLABLE_IF_DEFAULT_OMITTED,
            value=expected,
            default=NullabilityDefaultEvidence(
                parameter_position=2, omitted=omitted, contribution=expected
            ),
        ),
    )


@pytest.mark.parametrize(
    ("left", "right"),
    tuple(
        (left, right) for left in EffectiveNullability for right in EffectiveNullability
    ),
)
def test_any_of_complete_three_state_truth_table_is_exact(
    left: EffectiveNullability,
    right: EffectiveNullability,
) -> None:
    formula = AnyOfFormula(
        children=(
            SameAsArgumentFormula(argument_index=0),
            SameAsArgumentFormula(argument_index=1),
        )
    )
    match = _match(
        formula,
        NullabilityEvaluationContext(
            argument_nullabilities=(left, right), omitted_positions=()
        ),
        signature=_two_parameter_signature(),
    )
    assert match.value is _join(left, right)
    assert tuple(child.value for child in match.evidence.children) == (left, right)


@pytest.mark.parametrize(
    "case", ("match-order", "duplicate", "unsupported-first", "unsupported-second")
)
def test_any_of_evaluates_every_child_in_declared_order(case: str) -> None:
    signature = _navigation_signature()
    if case == "match-order":
        result = _match(
            AnyOfFormula(children=(NullableFormula(), NonNullFormula())),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.NON_NULL,),
                omitted_positions=(1, 2),
            ),
            signature=signature,
        )
        assert tuple(child.kind for child in result.evidence.children) == (
            NullabilityFormulaKind.NULLABLE,
            NullabilityFormulaKind.NON_NULL,
        )
    elif case == "duplicate":
        result = _match(
            AnyOfFormula(children=(AlwaysNullableFormula(), AlwaysNullableFormula())),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.NON_NULL,),
                omitted_positions=(1, 2),
            ),
            signature=signature,
        )
        assert (
            tuple(child.kind for child in result.evidence.children)
            == (NullabilityFormulaKind.ALWAYS_NULLABLE,) * 2
        )
    else:
        omitted = SameAsArgumentFormula(argument_index=2)
        supplied = SameAsArgumentFormula(argument_index=0)
        formula = AnyOfFormula(
            children=(omitted, supplied)
            if case == "unsupported-first"
            else (supplied, omitted)
        )
        outcome = evaluate_signature_result_nullability(
            SignatureResultFormula(signature=signature, nullability=formula),
            NullabilityEvaluationContext(
                argument_nullabilities=(EffectiveNullability.UNKNOWN,),
                omitted_positions=(1, 2),
            ),
        )
        assert outcome == NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED,
            parameter_position=2,
        )
        assert "child_results = tuple(" in SOURCE_PATH.read_text()


@pytest.mark.parametrize(
    "case",
    (
        "arguments-container",
        "argument-member",
        "omissions-container",
        "omission-bool",
        "omission-negative",
        "omission-duplicate",
        "omission-unsorted",
        "valid",
    ),
)
def test_evaluation_context_container_member_and_order_shapes_are_exact(
    case: str,
) -> None:
    if case == "arguments-container":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=cast(tuple[EffectiveNullability, ...], []),
                omitted_positions=(),
            )
    elif case == "argument-member":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=cast(
                    tuple[EffectiveNullability, ...], ("unknown",)
                ),
                omitted_positions=(),
            )
    elif case == "omissions-container":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=cast(tuple[int, ...], [])
            )
    elif case == "omission-bool":
        with pytest.raises(TypeError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(cast(int, True),)
            )
    elif case == "omission-negative":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(-1,)
            )
    elif case == "omission-duplicate":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(1, 1)
            )
    elif case == "omission-unsorted":
        with pytest.raises(ValueError):
            NullabilityEvaluationContext(
                argument_nullabilities=(), omitted_positions=(2, 1)
            )
    else:
        context = NullabilityEvaluationContext(
            argument_nullabilities=(EffectiveNullability.UNKNOWN,),
            omitted_positions=(1, 2),
        )
        assert context.argument_nullabilities == (EffectiveNullability.UNKNOWN,)
        assert context.omitted_positions == (1, 2)


@pytest.mark.parametrize(
    "case", ("non-null", "nullable", "always", "same", "any-nullable", "composed")
)
def test_signature_result_wrapper_accepts_valid_formula_references(case: str) -> None:
    formulas: dict[str, NullabilityFormula] = {
        "non-null": NonNullFormula(),
        "nullable": NullableFormula(),
        "always": AlwaysNullableFormula(),
        "same": SameAsArgumentFormula(argument_index=0),
        "any-nullable": AnyNullableFormula(argument_indices=(0, 2)),
        "composed": _navigation_formula(),
    }
    formula = formulas[case]
    association = SignatureResultFormula(
        signature=_navigation_signature(), nullability=formula
    )
    assert association.signature == _navigation_signature()
    assert association.nullability == formula


@pytest.mark.parametrize("case", ("same", "any-first", "any-second", "default"))
def test_signature_result_wrapper_rejects_out_of_range_references(case: str) -> None:
    formulas: dict[str, NullabilityFormula] = {
        "same": SameAsArgumentFormula(argument_index=3),
        "any-first": AnyNullableFormula(argument_indices=(3,)),
        "any-second": AnyNullableFormula(argument_indices=(0, 3)),
        "default": NullableIfDefaultOmittedFormula(parameter_index=3),
    }
    with pytest.raises(ValueError, match="outside"):
        SignatureResultFormula(
            signature=_navigation_signature(), nullability=formulas[case]
        )


@pytest.mark.parametrize(
    "case",
    (
        "valid-leaf",
        "valid-composed",
        "required",
        "optional-no-marker",
        "duplicate-default",
    ),
)
def test_default_reference_requires_optional_omitted_marker(case: str) -> None:
    if case == "valid-leaf":
        association = SignatureResultFormula(
            signature=_navigation_signature(),
            nullability=NullableIfDefaultOmittedFormula(parameter_index=2),
        )
        assert association.nullability == NullableIfDefaultOmittedFormula(
            parameter_index=2
        )
    elif case == "valid-composed":
        assert (
            SignatureResultFormula(
                signature=_navigation_signature(), nullability=_navigation_formula()
            ).nullability
            == _navigation_formula()
        )
    elif case == "required":
        with pytest.raises(ValueError, match="optional"):
            SignatureResultFormula(
                signature=_two_parameter_signature(),
                nullability=NullableIfDefaultOmittedFormula(parameter_index=1),
            )
    elif case == "optional-no-marker":
        with pytest.raises(ValueError, match="ParameterDefault.OMITTED"):
            SignatureResultFormula(
                signature=_optional_without_default_signature(),
                nullability=NullableIfDefaultOmittedFormula(parameter_index=1),
            )
    else:
        formula = AnyOfFormula(
            children=(
                NullableIfDefaultOmittedFormula(parameter_index=2),
                NullableIfDefaultOmittedFormula(parameter_index=2),
            )
        )
        association = SignatureResultFormula(
            signature=_navigation_signature(), nullability=formula
        )
        assert association.nullability == formula


@pytest.mark.parametrize(
    ("case", "arguments", "omissions", "reason", "position"),
    (
        (
            "too-many",
            (EffectiveNullability.NON_NULL,) * 4,
            (),
            NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH,
            None,
        ),
        (
            "required",
            (),
            (0, 1, 2),
            NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED,
            0,
        ),
        (
            "missing-first",
            (EffectiveNullability.NON_NULL,),
            (2,),
            NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY,
            1,
        ),
        (
            "missing-second",
            (EffectiveNullability.NON_NULL,),
            (1,),
            NullabilityEvaluationFailureReason.MISSING_ARGUMENT_NULLABILITY,
            2,
        ),
        (
            "out-of-range-extra",
            (EffectiveNullability.NON_NULL,) * 2,
            (2, 3),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            3,
        ),
        (
            "supplied-extra",
            (EffectiveNullability.NON_NULL,) * 2,
            (1, 2),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            1,
        ),
        (
            "full-out-of-range",
            (EffectiveNullability.NON_NULL,) * 3,
            (3,),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            3,
        ),
        (
            "full-supplied",
            (EffectiveNullability.NON_NULL,) * 3,
            (2,),
            NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT,
            2,
        ),
    ),
)
def test_incompatible_contexts_return_ordered_structured_unsupported(
    case: str,
    arguments: tuple[EffectiveNullability, ...],
    omissions: tuple[int, ...],
    reason: NullabilityEvaluationFailureReason,
    position: int | None,
) -> None:
    del case
    result = evaluate_signature_result_nullability(
        SignatureResultFormula(
            signature=_navigation_signature(), nullability=NonNullFormula()
        ),
        NullabilityEvaluationContext(
            argument_nullabilities=arguments, omitted_positions=omissions
        ),
    )
    assert result == NullabilityEvaluationUnsupported(
        reason=reason, parameter_position=position
    )


@pytest.mark.parametrize(
    ("case", "value", "expected"),
    (
        ("same", EffectiveNullability.NON_NULL, None),
        ("any-non-null", EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL),
        ("any-unknown", EffectiveNullability.UNKNOWN, EffectiveNullability.UNKNOWN),
        ("any-nullable", EffectiveNullability.NULLABLE, EffectiveNullability.NULLABLE),
    ),
)
def test_omitted_same_as_arg_fails_closed_and_any_nullable_is_neutral(
    case: str,
    value: EffectiveNullability,
    expected: EffectiveNullability | None,
) -> None:
    context = NullabilityEvaluationContext(
        argument_nullabilities=(value,), omitted_positions=(1, 2)
    )
    signature = _navigation_signature()
    if case == "same":
        result = evaluate_signature_result_nullability(
            SignatureResultFormula(
                signature=signature, nullability=SameAsArgumentFormula(argument_index=2)
            ),
            context,
        )
        assert result == NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.OMITTED_ARGUMENT_REFERENCED,
            parameter_position=2,
        )
    else:
        match = _match(
            AnyNullableFormula(argument_indices=(0, 2)),
            context,
            signature=signature,
        )
        assert match.value is expected
        assert match.evidence.arguments[1] == NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        )


@pytest.mark.parametrize(
    "case",
    (
        "argument-supplied",
        "argument-omitted",
        "supplied-none",
        "supplied-mismatch",
        "omitted-value",
        "omitted-contribution",
        "default-mismatch",
        "evidence-shape",
    ),
)
def test_evaluation_evidence_carrier_invariants_are_exact(case: str) -> None:
    if case == "argument-supplied":
        row = NullabilityArgumentEvidence(
            parameter_position=0,
            supplied=True,
            value=EffectiveNullability.UNKNOWN,
            contribution=EffectiveNullability.UNKNOWN,
        )
        assert row.value is row.contribution
    elif case == "argument-omitted":
        row = NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        )
        assert row.value is None
    elif case == "supplied-none":
        with pytest.raises(TypeError):
            NullabilityArgumentEvidence(
                parameter_position=0,
                supplied=True,
                value=None,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "supplied-mismatch":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=0,
                supplied=True,
                value=EffectiveNullability.UNKNOWN,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "omitted-value":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=2,
                supplied=False,
                value=EffectiveNullability.UNKNOWN,
                contribution=EffectiveNullability.NON_NULL,
            )
    elif case == "omitted-contribution":
        with pytest.raises(ValueError):
            NullabilityArgumentEvidence(
                parameter_position=2,
                supplied=False,
                value=None,
                contribution=EffectiveNullability.UNKNOWN,
            )
    elif case == "default-mismatch":
        with pytest.raises(ValueError):
            NullabilityDefaultEvidence(
                parameter_position=2,
                omitted=True,
                contribution=EffectiveNullability.NON_NULL,
            )
    else:
        with pytest.raises(ValueError):
            NullabilityEvaluationEvidence(
                kind=NullabilityFormulaKind.ANY_OF,
                value=EffectiveNullability.NON_NULL,
            )


@pytest.mark.parametrize(
    "case",
    (
        "arity-valid",
        "arity-position",
        "required-position",
        "invalid-none",
        "wrong-reason",
    ),
)
def test_evaluation_unsupported_carrier_invariants_are_exact(case: str) -> None:
    if case == "arity-valid":
        result = NullabilityEvaluationUnsupported(
            reason=NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH
        )
        assert result.parameter_position is None
    elif case == "arity-position":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.CONTEXT_ARITY_MISMATCH,
                parameter_position=0,
            )
    elif case == "required-position":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.REQUIRED_PARAMETER_OMITTED
            )
    elif case == "invalid-none":
        with pytest.raises(ValueError):
            NullabilityEvaluationUnsupported(
                reason=NullabilityEvaluationFailureReason.INVALID_OMISSION_CONTEXT
            )
    else:
        with pytest.raises(TypeError):
            NullabilityEvaluationUnsupported(
                reason=cast(NullabilityEvaluationFailureReason, "invalid")
            )


@pytest.mark.parametrize("case", ("formula", "wrapper", "context", "result"))
def test_formula_result_and_evidence_equality_hash_repr_are_repeatable(
    case: str,
) -> None:
    formula = _navigation_formula()
    wrapper = SignatureResultFormula(
        signature=_navigation_signature(), nullability=formula
    )
    context = NullabilityEvaluationContext(
        argument_nullabilities=(EffectiveNullability.UNKNOWN,),
        omitted_positions=(1, 2),
    )
    result = evaluate_signature_result_nullability(wrapper, context)
    values: dict[str, object] = {
        "formula": formula,
        "wrapper": wrapper,
        "context": context,
        "result": result,
    }
    value = values[case]
    assert value == value
    assert hash(value) == hash(value)
    assert repr(value) == repr(value)
    assert "object at" not in repr(value)


@pytest.mark.parametrize("value", tuple(EffectiveNullability))
def test_lag_lead_omitted_default_readiness_formula_is_exact(
    value: EffectiveNullability,
) -> None:
    match = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=(value,), omitted_positions=(1, 2)
        ),
        signature=_navigation_signature(),
    )
    assert match.value is EffectiveNullability.NULLABLE
    any_nullable, omission = match.evidence.children
    assert any_nullable.arguments == (
        NullabilityArgumentEvidence(
            parameter_position=0, supplied=True, value=value, contribution=value
        ),
        NullabilityArgumentEvidence(
            parameter_position=2,
            supplied=False,
            value=None,
            contribution=EffectiveNullability.NON_NULL,
        ),
    )
    assert omission.default == NullabilityDefaultEvidence(
        parameter_position=2,
        omitted=True,
        contribution=EffectiveNullability.NULLABLE,
    )


@pytest.mark.parametrize(
    ("value", "default"),
    tuple(
        (value, default)
        for value in EffectiveNullability
        for default in EffectiveNullability
    ),
)
def test_lag_lead_supplied_default_truth_matrix_is_exact(
    value: EffectiveNullability,
    default: EffectiveNullability,
) -> None:
    match = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=(value, EffectiveNullability.UNKNOWN, default),
            omitted_positions=(),
        ),
        signature=_navigation_signature(),
    )
    assert match.value is _join(value, default)
    any_nullable, omission = match.evidence.children
    assert tuple(row.parameter_position for row in any_nullable.arguments) == (0, 2)
    assert tuple(row.value for row in any_nullable.arguments) == (value, default)
    assert omission.default == NullabilityDefaultEvidence(
        parameter_position=2,
        omitted=False,
        contribution=EffectiveNullability.NON_NULL,
    )


@pytest.mark.parametrize("navigation_name", ("lag", "lead"))
def test_lag_and_lead_readiness_associations_are_identity_free(
    navigation_name: str,
) -> None:
    association = SignatureResultFormula(
        signature=_navigation_signature(),
        nullability=_navigation_formula(),
    )
    assert association == SignatureResultFormula(
        signature=_navigation_signature(),
        nullability=_navigation_formula(),
    )
    assert navigation_name not in {field.name for field in fields(association)}
    assert tuple(field.name for field in fields(association)) == (
        "signature",
        "nullability",
    )


@pytest.mark.parametrize(
    ("arguments", "facts", "expected_omitted", "expected_value"),
    (
        (
            (TEXT,),
            (EffectiveNullability.NON_NULL,),
            (1, 2),
            EffectiveNullability.NULLABLE,
        ),
        (
            (TEXT, INT),
            (EffectiveNullability.NON_NULL, EffectiveNullability.NON_NULL),
            (2,),
            EffectiveNullability.NULLABLE,
        ),
        (
            (TEXT, INT, TEXT),
            (
                EffectiveNullability.UNKNOWN,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            (),
            EffectiveNullability.UNKNOWN,
        ),
        (
            (INT, INT, INT),
            (
                EffectiveNullability.NULLABLE,
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NON_NULL,
            ),
            (),
            EffectiveNullability.NULLABLE,
        ),
    ),
)
def test_signature_match_omissions_compose_without_type_binding_changes(
    arguments: tuple[LogicalTypeIdentity, ...],
    facts: tuple[EffectiveNullability, ...],
    expected_omitted: tuple[int, ...],
    expected_value: EffectiveNullability,
) -> None:
    signature = _navigation_signature()
    binding = bind_signature(signature, arguments)
    assert type(binding) is SignatureMatch
    match = cast(SignatureMatch, binding)
    assert match.result_type == arguments[0]
    assert match.omitted_positions == expected_omitted
    result = _match(
        _navigation_formula(),
        NullabilityEvaluationContext(
            argument_nullabilities=facts,
            omitted_positions=match.omitted_positions,
        ),
        signature=signature,
    )
    assert result.value is expected_value


def test_generic_compatibility_module_and_slice4_contract_are_byte_locked() -> None:
    assert _sha256(REPO_ROOT / "src/pietto/semantic/generic_compatibility.py") == (
        "340703267a6185f0b37401c1097a1f246d34d3d0d46c1f583b5ce5134e5090f8"
    )
    assert _sha256(
        REPO_ROOT
        / "docs/spec/phase53-generic-type-variable-exact-compatibility-contract-v1.md"
    ) == ("194ee730b88782afd6f84d90b52cb4f02a3f5efb386155fae062978f3dfe5bd9")
    source = (REPO_ROOT / "src/pietto/semantic/generic_compatibility.py").read_text()
    assert "nullability_formulas" not in source
    assert "result_nullability" not in source


def test_current_semantic_analyzer_and_window_paths_do_not_import_nullability_formulas() -> (
    None
):
    protected_consumers = (
        "src/pietto/semantic/analyzer.py",
        "src/pietto/semantic/catalog.py",
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/aggregates.py",
        "src/pietto/_window_identity.py",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
    )
    assert all(
        "nullability_formulas" not in (REPO_ROOT / path).read_text()
        for path in protected_consumers
    )
    window_analysis = (REPO_ROOT / "src/pietto/semantic/window_analysis.py").read_text()
    assert "pietto.semantic.nullability_formulas import" in window_analysis
    assert "SignatureResultFormula(" in window_analysis
    assert "nullability=NonNullFormula()" in window_analysis
    source = SOURCE_PATH.read_text()
    assert "pietto.semantic.generic_compatibility import" in source
    assert "pietto.semantic.model import EffectiveNullability" in source
    for forbidden in (
        "analyzer",
        "catalog",
        "capability",
        "_window",
        "_project",
        "pietto.ir",
        "pietto.sql",
        "cli",
        "serializer",
    ):
        assert f"import {forbidden}" not in source


def test_concrete_semantic_project_and_aggregate_nullability_authority_is_locked() -> (
    None
):
    expected = {
        "src/pietto/semantic/model.py": "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
        "src/pietto/semantic/analyzer.py": "7a6f2830bf3710edab3ba5a8c4a72e90c6e44de19fe19ddd2b54b5d703277b32",
        "src/pietto/semantic/expressions.py": "37b198f72b0c71c90a82d746671be8528a9ea5c2d4818ff7ef4ba55e30e9c595",
        "src/pietto/semantic/aggregates.py": "f5d5be237960e50f62f539d76e09be425980c9f8e657846333b5ef1aaa948333",
        "src/pietto/semantic/catalog.py": "f566f39395e3bdc933e60d15e740749255dd3749cf3907684240e4b43dfc9e40",
        "src/pietto/_project/model.py": "da4853f95c41b85482381a442a217354f0b47abe76f09c90c8587004dd59bf21",
        "src/pietto/_project/row_expression_schema.py": "fc968a628592640012d59521627c91ee0a0017bc640fab27e8cbd756e4aa1e7d",
        "src/pietto/_project/row_expression_type_facts.py": "2c04a335fe594a599df7bced676fd8767688eaa91045c90473a494bafc7d9278",
        "src/pietto/_project/aggregate_grouped_schema.py": "406fa28ec27a574576508a075305c28f07a495cf91f300d529c62b84a0aa519b",
    }
    assert {path: _sha256(REPO_ROOT / path) for path in expected} == expected


def test_project_ir_sql_cli_serializer_and_public_exports_are_unchanged() -> None:
    expected = {
        "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
        "src/pietto/semantic/__init__.py": "21dbef77211fa5dbf0a64c050d5751718d70e990498bebc3b1ba4590b6086cfb",
        "src/pietto/ir/model.py": "b257f671861604d0e2828c88bbd001f708312e254ac6129f9c35d6483124019d",
        "src/pietto/sql/postgres.py": "9b89550ddaf1759e8066d02590288f545eace484e4633f6f6e37b1fa8c194790",
        "src/pietto/sql/mysql.py": "ef9c80266f8d9aa210ed5e77de4cc4994d06a9cda346548980ba8a2c444183ec",
        "src/pietto/cli.py": "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09",
        "src/pietto/cli_json.py": "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91",
        "src/pietto/_metadata/serializer.py": "dd1264f9c49e7f9bfe694d185b9ee30e775374cce2969d6e9ddb7796bbb4ae4b",
        "src/pietto/_project/json_v2.py": "74251e684a22de4dcdc7e1822a6843ca89cbdfa7e136a046676d848b57953bd5",
        "uv.lock": "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea",
        ".github/workflows/ci.yml": "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94",
    }
    assert {path: _sha256(REPO_ROOT / path) for path in expected} == expected


def test_grammar_ast_generated_parser_window_and_generic_bytes_are_locked() -> None:
    expected = {
        "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
        "src/pietto/ast_nodes.py": "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
        "src/pietto/ast_builder.py": "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
        "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
        "src/pietto/_window_identity.py": "d1223f7095790dc08ffc176c103ae6180cd9e03773ddf9763448d482d6984c9b",
        "src/pietto/semantic/generic_compatibility.py": "340703267a6185f0b37401c1097a1f246d34d3d0d46c1f583b5ce5134e5090f8",
        "src/pietto/semantic/model.py": "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
    }
    assert {path: _sha256(REPO_ROOT / path) for path in expected} == expected
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").iterdir()
        if path.is_file()
    )
    assert len(generated) == 8
    assert (
        _digest(generated)
        == "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1"
    )


def test_reader_hash_inventory_and_nested_hash_closure_is_exact() -> None:
    repository_paths = _all_repository_paths()
    compiler_paths = (
        REPO_ROOT / "Makefile",
        REPO_ROOT / "grammar/Pietto.g4",
        *(
            REPO_ROOT / path
            for path in repository_paths
            if path.startswith("src/pietto/")
        ),
    )
    semantic_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/semantic"
        and path.endswith(".py")
    )
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    assert (len(compiler_paths), len(semantic_paths), len(phase15_paths)) == (
        108,
        36,
        33,
    )
    assert _digest(tuple(compiler_paths)) == FINAL_COMPILER_DIGEST
    assert _digest(semantic_paths) == FINAL_SEMANTIC_DIGEST
    assert _digest(phase15_paths) == FINAL_PHASE15_DIGEST
    assert _sha256(SOURCE_PATH) == FINAL_SOURCE_SHA256
    assert _sha256(SPEC_PATH) == FINAL_SPEC_SHA256
    assert _sha256(PLAN_PATH) == FINAL_PLAN_SHA256
    test_paths = tuple((REPO_ROOT / "tests").glob("test_*.py"))
    assert sum(FINAL_COMPILER_DIGEST in path.read_text() for path in test_paths) == 28
    assert sum(FINAL_SEMANTIC_DIGEST in path.read_text() for path in test_paths) == 42
    assert sum(FINAL_PHASE15_DIGEST in path.read_text() for path in test_paths) == 17
    assert (
        sum(
            f'BOUNDARY_HASH = "{FINAL_COMPILER_DIGEST}"' in path.read_text()
            for path in test_paths
        )
        == 8
    )


def test_slice5_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_active_gate2_is_active():
        return
    tracked = frozenset(_git("diff", "--name-only").splitlines()) - {""}
    untracked = frozenset(
        _git("ls-files", "--others", "--exclude-standard").splitlines()
    ) - {""}
    cached = frozenset(_git("diff", "--cached", "--name-only").splitlines()) - {""}
    assert cached == frozenset()
    head = _git("rev-parse", "HEAD")
    branch = _git("symbolic-ref", "--quiet", "--short", "HEAD", check=False)
    if not tracked and not untracked:
        if branch == phase54_publication_topic_branch():
            assert phase54_publication_clean_topic_is_active()
            return
        assert branch in {"", "main"}
        for reference in ("refs/heads/main", "refs/remotes/origin/main"):
            result = subprocess.run(
                ("git", "show-ref", "--verify", "--quiet", reference),
                cwd=REPO_ROOT,
                check=False,
            )
            if result.returncode == 0:
                assert _git("rev-parse", reference) == head
        return
    if head in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        "b81843acadb294630db361c09949868d004b1bca",
    }:
        expected_modified, expected_added = _phase54_slice2_paths()
        expected_base = head
    else:
        expected_modified = frozenset(MODIFIED_PATHS)
        expected_added = frozenset(ADDED_PATHS)
        expected_base = BASE_HEAD
    assert branch == "main"
    assert head == expected_base
    assert tracked == expected_modified
    assert untracked == expected_added
    status = subprocess.run(
        ("git", "status", "--porcelain=v1"),
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert {line[3:] for line in status if line.startswith(" M ")} == set(
        expected_modified
    )
    assert {line[3:] for line in status if line.startswith("?? ")} == set(
        expected_added
    )
    assert all(not line.startswith((" D ", "R ")) for line in status)
    for reference in ("refs/heads/main", "refs/remotes/origin/main"):
        assert _git("rev-parse", reference) == expected_base


def test_test_inventory_focused_selector_and_dirty_overlay_are_exact() -> None:
    repository_paths = _all_repository_paths()
    assert len(repository_paths) == 944
    assert sum(path.endswith(".py") for path in repository_paths) == 579
    assert sum(path.endswith(".md") for path in repository_paths) == 269
    test_paths = tuple(sorted((REPO_ROOT / "tests").glob("test_*.py")))
    assert len(test_paths) == 465
    functions = tuple(
        node.name
        for path in test_paths
        for node in ast.parse(path.read_text()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert len(functions) == 5489
    self_functions = tuple(
        node.name
        for node in ast.parse(SELF_PATH.read_text()).body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert self_functions == TEST_FUNCTIONS
    assert len(TEST_ITEM_COUNTS) == 38
    assert sum(TEST_ITEM_COUNTS) == 145
    assert 10599 + 185 == 10784
    focused_value, overlay_value, added_value, modified_value = _compound_assignment(
        GENERIC_TEST_PATH
    )
    focused = cast(tuple[str, ...], focused_value)
    overlay = cast(tuple[str, ...], overlay_value)
    assert cast(tuple[str, ...], added_value) == ADDED_PATHS
    assert cast(tuple[str, ...], modified_value) == MODIFIED_PATHS
    focused_payload = ("\n".join(focused) + "\n").encode()
    overlay_payload = ("\n".join(overlay) + "\n").encode()
    assert (len(focused), len({item.split("::")[0] for item in focused})) == (
        134,
        80,
    )
    assert (
        sum("::" not in item for item in focused),
        sum("::" in item for item in focused),
    ) == (14, 120)
    assert len(focused_payload) == 15130
    assert (
        hashlib.sha256(focused_payload).hexdigest()
        == "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429"
    )
    assert len(focused) == len(set(focused))
    assert (
        len(overlay),
        len({item.split("=", 1)[1].split("::")[0] for item in overlay}),
    ) == (185, 137)
    assert len(overlay_payload) == 23628
    assert (
        hashlib.sha256(overlay_payload).hexdigest()
        == "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
    )
    assert len(overlay) == len(set(overlay))


def test_validation_gate3_and_no_behavior_boundaries_are_locked() -> None:
    spec = SPEC_PATH.read_text()
    plan = PLAN_PATH.read_text()
    assert "607 focused items" in spec
    assert "6528 passes and 183 deselections" in spec
    assert "6711 passes per Python job" in spec
    assert "Gate 2 leaves all 53 paths unstaged and uncommitted" in plan
    assert (
        "Slice 5 becomes `COMPLETED` only after a separately authorized Gate 3" in plan
    )
    assert "Add Phase 53 nullability formula foundation" not in SOURCE_PATH.read_text()
    assert 'version = "0.1.0"' in (REPO_ROOT / "pyproject.toml").read_text()
    validate = (REPO_ROOT / "scripts/validate.py").read_text()
    for command in (
        '("uv", "lock", "--check")',
        '("uv", "run", "ruff", "format", "--check", ".")',
        '("uv", "run", "ruff", "check", ".")',
        '("uv", "run", "pyright")',
        '("uv", "run", "pyright", "--project", "pyrightconfig.tests.json")',
    ):
        assert command in validate
    assert _git("tag", "--list") == ""


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
