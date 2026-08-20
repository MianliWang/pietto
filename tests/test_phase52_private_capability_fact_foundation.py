from __future__ import annotations

# Phase 54 Slice 4 mechanical reader-closure identity refresh.

import ast
import hashlib
import re
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any, cast

import pytest

import pietto.semantic.capability_facts as capability_facts
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
INVENTORY_SPEC_REL = (
    "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md"
)
INVENTORY_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
SIGNATURE_SPEC_REL = "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md"
SIGNATURE_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
CONTEXT_SPEC_REL = "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md"
CONTEXT_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
SPEC_REL = (
    "docs/spec/"
    "phase52-private-capability-key-disposition-evidence-fact-foundation-v1.md"
)
SELF_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
LOOKUP_PATH = REPO_ROOT / LOOKUP_REL
INVENTORY_PATH = REPO_ROOT / INVENTORY_REL
SIGNATURE_PATH = REPO_ROOT / SIGNATURE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

SPEC_H2 = (
    "Status And Authority",
    "Private Module And Exact Vocabulary",
    "Capability Key Contract",
    "Current Support And Roadmap Disposition",
    "Atomic Evidence And Generic Fact Contract",
    "Bounded Reason-code Contract",
    "Structural Invariants And Determinism",
    "Privacy And No-behavior Boundary",
    "Conflict-ledger Preservation",
    "Slice Ownership And Validation Locks",
)
BOUNDARY_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
)
COMPILER_LOCK_PATHS = (
    *BOUNDARY_PATHS,
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
)
SEMANTIC_LOCK_PATHS = (
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
)
PHASE15_SUBSET_PATH = "tests/test_phase15_semantic_completion_audit.py"
MODIFIED_READER_PATHS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_planning_audit.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase12_order_limit_contract.py",
    "tests/test_phase12_planning_audit.py",
    "tests/test_phase13_completion_audit.py",
    "tests/test_phase13_planning_audit.py",
    "tests/test_phase14_candidate_decision_audit.py",
    "tests/test_phase14_completion_audit.py",
    "tests/test_phase14_planning_audit.py",
    "tests/test_phase14_relationship_metadata_completion_audit.py",
    "tests/test_phase15_completion_audit.py",
    "tests/test_phase15_semantic_completion_audit.py",
    "tests/test_phase16_completion_audit.py",
    "tests/test_phase16_current_syntax_surface_audit.py",
    "tests/test_phase16_language_direction_audit.py",
    "tests/test_phase16_safety_deferral_sql_portability.py",
    "tests/test_phase21_group_by_hardening_audit.py",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py",
    "tests/test_phase24_cli_json_output_hardening.py",
    "tests/test_phase24_completion_audit.py",
    "tests/test_phase25_completion_audit.py",
    "tests/test_phase26_completion_audit.py",
    "tests/test_phase27_completion_audit.py",
    "tests/test_phase28_completion_audit.py",
    "tests/test_phase29_completion_audit.py",
    "tests/test_phase30_completion_audit.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
    SELF_REL,
    SLICE3_TEST_REL,
    INVENTORY_TEST_REL,
    SIGNATURE_TEST_REL,
)
ADDED_PATHS = {CONTEXT_REL, CONTEXT_SPEC_REL, CONTEXT_TEST_REL}
DIRECT_TIER1_NODES = (
    "tests/test_phase11_completion_audit.py::test_package_configuration_lockfile_makefile_and_compiler_are_unchanged",
    "tests/test_phase11_planning_audit.py::test_slice1_locks_configuration_and_compiler_boundaries",
    "tests/test_phase12_order_limit_contract.py::test_slice6_preserves_configuration_cli_and_golden_boundaries",
    "tests/test_phase12_planning_audit.py::test_slice6_locks_configuration_workflow_and_compiler_boundaries",
    "tests/test_phase13_completion_audit.py::test_production_compiler_and_phase13_implementation_markers_are_absent",
    "tests/test_phase13_planning_audit.py::test_slice1_locks_compiler_workflow_and_golden_boundaries",
    "tests/test_phase14_candidate_decision_audit.py::test_production_generated_dependency_api_json_golden_and_ci_are_locked",
    "tests/test_phase14_completion_audit.py::test_unchanged_compiler_repository_and_golden_surfaces_are_byte_locked",
    "tests/test_phase14_planning_audit.py::test_production_grammar_generated_workflow_and_scripts_are_locked",
    "tests/test_phase14_relationship_metadata_completion_audit.py::test_forbidden_compiler_layers_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_completion_audit.py::test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked",
    "tests/test_phase15_semantic_completion_audit.py::test_frontend_ir_sql_cli_json_dependency_and_ci_boundaries_are_locked",
    "tests/test_phase16_completion_audit.py::test_frontend_compiler_cli_and_repository_surfaces_are_byte_locked",
    "tests/test_phase16_current_syntax_surface_audit.py::test_compiler_repository_and_fixture_surfaces_are_byte_locked",
    "tests/test_phase16_language_direction_audit.py::test_compiler_repository_and_document_contracts_are_byte_locked",
    "tests/test_phase16_safety_deferral_sql_portability.py::test_compiler_repository_and_fixture_surfaces_are_byte_locked",
    "tests/test_phase21_group_by_hardening_audit.py::test_slice8_forbidden_implementation_surfaces_are_unchanged",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py::test_slice7_boundary_surfaces_remain_post_slice6_hash_locked",
    "tests/test_phase24_cli_json_output_hardening.py::test_slice8_boundary_surfaces_remain_post_slice7_hash_locked",
    "tests/test_phase24_completion_audit.py::test_slice9_boundary_surfaces_remain_post_slice8_hash_locked",
    "tests/test_phase25_completion_audit.py::test_slice7_boundary_surfaces_remain_phase25_locked",
    "tests/test_phase26_completion_audit.py::test_slice9_boundary_surfaces_remain_phase26_locked",
    "tests/test_phase27_completion_audit.py::test_boundary_surfaces_remain_phase27_locked",
    "tests/test_phase28_completion_audit.py::test_boundary_surfaces_remain_phase28_locked",
    "tests/test_phase29_completion_audit.py::test_phase29_locked_boundary_surface_hashes_are_unchanged",
    "tests/test_phase30_completion_audit.py::test_phase30_locked_boundary_surface_hashes_are_unchanged",
    "tests/test_phase11_ci_workflow.py::test_ci_and_package_smoke_preserve_metadata_and_compiler_boundaries",
    "tests/test_phase11_generated_guard.py::test_slice3_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase11_golden_policy.py::test_slice4_preserves_golden_and_compiler_boundary_bytes",
    "tests/test_phase11_packaging_smoke.py::test_prior_scripts_and_all_compiler_packaging_boundaries_are_unchanged",
    "tests/test_phase11_validation_entrypoint.py::test_slice2_preserves_compiler_and_configuration_boundary_bytes",
    "tests/test_phase12_completion_audit.py::test_production_compiler_and_configuration_boundary_is_unchanged",
    "tests/test_phase12_composition_cli_json_goldens.py::test_production_api_json_dependency_and_compiler_boundaries_are_unchanged",
    "tests/test_phase51_completion_audit_and_status_lock.py::test_live_compiler_project_private_protected_version_and_tag_locks_are_dirty_safe",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py::test_live_compiler_project_private_and_protected_locks_are_dirty_safe",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_slice1_no_behavior_public_privacy_and_release_boundaries_are_locked",
    "tests/test_phase14_candidate_decision_audit.py::test_slice2_status_inputs_and_single_candidate_decision",
    "tests/test_phase14_planning_audit.py::test_phase13_inputs_are_referenced_and_byte_locked",
    "tests/test_phase15_completion_audit.py::test_slice1_and_slice2_specs_tests_and_behavior_are_byte_locked",
    "tests/test_phase16_completion_audit.py::test_all_phase16_specs_and_focused_audits_are_byte_locked",
    "tests/test_phase49_compatibility_privacy_hash_lock_readiness.py::test_existing_hash_and_private_surface_locks_remain_present",
    "tests/test_phase51_aggregate_only_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "tests/test_phase51_grouped_aggregate_project_row_schema.py::test_forbidden_existing_project_compiler_and_public_surfaces_have_no_diff",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py::test_phase51_compatibility_migrations_preserve_historical_locks",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _compiler_paths() -> tuple[Path, ...]:
    paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
    return tuple(paths)


def _project_private_paths() -> tuple[Path, ...]:
    return tuple(
        path
        for path in (REPO_ROOT / "src/pietto/_project").rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _runtime_source() -> str:
    return _read(SOURCE_PATH)


def _key() -> CapabilityKey:
    return CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")


def _evidence() -> CapabilityEvidence:
    return CapabilityEvidence(
        CapabilityEvidenceSource.SPEC,
        SPEC_REL,
        "Capability Key Contract",
    )


def _fact(
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        _key(),
        support,
        disposition
        if disposition is not None
        else CapabilityDisposition(CapabilityDispositionKind.NONE),
        evidence if evidence is not None else (_evidence(),),
    )


def _pytest_item_count() -> int:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_PATH.as_posix())
    functions = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    item_count = len(functions)
    for function in functions:
        for decorator in function.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                ids = next(
                    (
                        keyword.value
                        for keyword in decorator.keywords
                        if keyword.arg == "ids"
                    ),
                    None,
                )
                if not isinstance(ids, (ast.List, ast.Tuple)):
                    raise AssertionError("Parametrization requires literal IDs")
                item_count += len(ids.elts) - 1
    return item_count


def test_private_module_owns_exact_frozen_slots_carrier_shapes() -> None:
    assert capability_facts.__all__ == ()
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert tuple(field.name for field in fields(CapabilityDisposition)) == (
        "kind",
        "owner",
        "reason",
    )
    assert tuple(field.name for field in fields(CapabilityEvidence)) == (
        "source",
        "source_path",
        "source_reference",
        "reason",
        "dialect",
        "backend",
        "extension",
    )
    assert tuple(field.name for field in fields(CapabilityFact)) == (
        "key",
        "support",
        "disposition",
        "evidence",
    )
    for carrier in (
        CapabilityKey,
        CapabilityDisposition,
        CapabilityEvidence,
        CapabilityFact,
    ):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__


def test_exact_enum_member_inventories_are_locked() -> None:
    assert [(item.name, item.value) for item in CapabilityDomain] == [
        ("LOGICAL_TYPE", "logical_type"),
        ("LITERAL", "literal"),
        ("PARAMETER", "parameter"),
        ("SCALAR_FUNCTION", "scalar_function"),
        ("UNARY_OPERATOR", "unary_operator"),
        ("BINARY_OPERATOR", "binary_operator"),
        ("COMPARISON", "comparison"),
        ("NULL_TEST", "null_test"),
        ("CLAUSE", "clause"),
        ("AGGREGATE", "aggregate"),
        ("WINDOW_FUNCTION", "window_function"),
        ("EXPRESSION_STAGE", "expression_stage"),
        ("CONVERSION", "conversion"),
        ("DIALECT_LOWERING", "dialect_lowering"),
        ("EXTENSION_SIGNATURE", "extension_signature"),
    ]
    assert [(item.name, item.value) for item in CapabilitySupport] == [
        ("SUPPORTED", "supported"),
        ("EXPLICITLY_UNSUPPORTED", "explicitly_unsupported"),
    ]
    assert [(item.name, item.value) for item in CapabilityDispositionKind] == [
        ("NONE", "none"),
        ("DEFERRED", "deferred"),
        ("OUT_OF_SCOPE", "out_of_scope"),
    ]
    assert [item.value for item in CapabilityEvidenceSource] == [
        "grammar_ast",
        "semantic_catalog",
        "semantic_procedure",
        "semantic_model",
        "ir",
        "backend",
        "project",
        "public",
        "roadmap",
        "test",
        "spec",
    ]


def test_capability_key_equality_hash_and_exact_text_identity_are_stable() -> None:
    first = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject=" Int ",
        operation=" + ",
        operands=cast(Any, (item for item in (" Float ", "Float"))),
        context=" select ",
    )
    second = CapabilityKey(
        CapabilityDomain.BINARY_OPERATOR,
        subject=" Int ",
        operation=" + ",
        operands=(" Float ", "Float"),
        context=" select ",
    )
    assert first == second
    assert hash(first) == hash(second)
    assert first.subject == " Int "
    assert first.operation == " + "
    assert first.operands == (" Float ", "Float")
    assert first.context == " select "


def test_capability_key_field_types_operand_order_and_scope_invariants_fail_closed() -> (
    None
):
    invalid = (
        {"domain": cast(Any, "logical_type"), "subject": "Int"},
        {"domain": CapabilityDomain.LOGICAL_TYPE},
        {"domain": CapabilityDomain.LOGICAL_TYPE, "subject": ""},
        {"domain": CapabilityDomain.LOGICAL_TYPE, "subject": "  "},
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, "Float"),
        },
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, None),
        },
        {
            "domain": CapabilityDomain.BINARY_OPERATOR,
            "operation": "+",
            "operands": cast(Any, ("Float", "")),
        },
        {
            "domain": CapabilityDomain.EXTENSION_SIGNATURE,
            "operation": "vector",
            "extension": "pgvector",
        },
    )
    for arguments in invalid:
        with pytest.raises(ValueError):
            CapabilityKey(**cast(Any, arguments))

    ordered = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        operation="pair",
        operands=("Text", "Text"),
    )
    reversed_key = CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        operation="pair",
        operands=("Text", "Int"),
    )
    assert ordered.operands == ("Text", "Text")
    assert ordered != reversed_key


def test_none_disposition_requires_absent_owner_and_reason() -> None:
    disposition = CapabilityDisposition(CapabilityDispositionKind.NONE)
    assert disposition.owner is None
    assert disposition.reason is None
    for owner, reason in (("Phase 53", None), (None, "later"), ("Phase 53", "later")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.NONE, owner, reason)


def test_deferred_disposition_requires_exact_owner_and_reason() -> None:
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        " Phase 53 ",
        " explicit owner ",
    )
    assert disposition.owner == " Phase 53 "
    assert disposition.reason == " explicit owner "
    for owner, reason in ((None, None), ("Phase 53", None), (None, "later")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.DEFERRED, owner, reason)


def test_out_of_scope_disposition_requires_exact_owner_and_reason() -> None:
    disposition = CapabilityDisposition(
        CapabilityDispositionKind.OUT_OF_SCOPE,
        " runtime ",
        " database-owned ",
    )
    assert disposition.owner == " runtime "
    assert disposition.reason == " database-owned "
    for owner, reason in ((None, None), ("runtime", None), (None, "owned")):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.OUT_OF_SCOPE, owner, reason)


def test_disposition_rejects_blank_text_without_normalizing_valid_text() -> None:
    for owner, reason in (
        ("", "reason"),
        (" ", "reason"),
        ("owner", ""),
        ("owner", " "),
    ):
        with pytest.raises(ValueError):
            CapabilityDisposition(CapabilityDispositionKind.DEFERRED, owner, reason)
    with pytest.raises(ValueError):
        CapabilityDisposition(cast(Any, "deferred"), "owner", "reason")


def test_evidence_carrier_fields_provenance_and_scope_invariants_are_exact() -> None:
    evidence = CapabilityEvidence(
        CapabilityEvidenceSource.BACKEND,
        " src/pietto/sql/mysql/emitter.py ",
        " render_expression ",
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
        dialect=" mysql ",
        backend=" private-mysql ",
        extension=" json ",
    )
    assert evidence.source_path == " src/pietto/sql/mysql/emitter.py "
    assert evidence.source_reference == " render_expression "
    assert evidence.dialect == " mysql "
    assert evidence.backend == " private-mysql "
    assert evidence.extension == " json "
    invalid = (
        (cast(Any, "backend"), "path", "ref", None, None),
        (CapabilityEvidenceSource.BACKEND, "", "ref", None, None),
        (CapabilityEvidenceSource.BACKEND, "path", " ", None, None),
        (CapabilityEvidenceSource.BACKEND, "path", "ref", cast(Any, "gap"), None),
        (CapabilityEvidenceSource.BACKEND, "path", "ref", None, "pgvector"),
    )
    for source, path, reference, reason, extension in invalid:
        with pytest.raises(ValueError):
            CapabilityEvidence(
                source,
                path,
                reference,
                reason,
                extension=extension,
            )


def test_capability_fact_evidence_is_nonempty_ordered_immutable_and_unique() -> None:
    first = _evidence()
    second = CapabilityEvidence(
        CapabilityEvidenceSource.TEST,
        SELF_REL,
        "test_capability_fact_evidence_is_nonempty_ordered_immutable_and_unique",
    )
    fact = _fact(evidence=cast(Any, [first, second]))
    assert fact.evidence == (first, second)
    with pytest.raises(ValueError):
        _fact(evidence=())
    with pytest.raises(ValueError):
        _fact(evidence=cast(Any, (first, first)))
    with pytest.raises(ValueError):
        _fact(evidence=cast(Any, "not evidence"))


def test_capability_fact_composition_is_frozen_hashable_and_has_no_lookup_state() -> (
    None
):
    fact = _fact()
    assert hash(fact) == hash(_fact())
    assert tuple(field.name for field in fields(fact)) == (
        "key",
        "support",
        "disposition",
        "evidence",
    )
    with pytest.raises(FrozenInstanceError):
        setattr(fact, "support", CapabilitySupport.EXPLICITLY_UNSUPPORTED)


@pytest.mark.parametrize(
    ("support", "disposition"),
    (
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED, "Phase 53", "later"
            ),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.OUT_OF_SCOPE, "runtime", "owned"
            ),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED, "Phase 53", "later"
            ),
        ),
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.OUT_OF_SCOPE, "runtime", "owned"
            ),
        ),
    ),
    ids=(
        "supported-none",
        "supported-deferred",
        "supported-out-of-scope",
        "explicitly-unsupported-none",
        "explicitly-unsupported-deferred",
        "explicitly-unsupported-out-of-scope",
    ),
)
def test_support_and_disposition_are_orthogonal(
    support: CapabilitySupport,
    disposition: CapabilityDisposition,
) -> None:
    fact = _fact(support=support, disposition=disposition)
    assert fact.support is support
    assert fact.disposition is disposition


def test_reason_codes_are_exact_private_non_diagnostic_vocabulary() -> None:
    assert [(item.name, item.value) for item in CapabilityReasonCode] == [
        ("NO_CATALOG_ENTRY", "no_catalog_entry"),
        ("NOT_EVIDENCED", "not_evidenced"),
        ("NO_CURRENT_RESULT_RULE", "no_current_result_rule"),
        ("UNRESOLVED_EXPRESSION", "unresolved_expression"),
        ("NULL_LITERAL_NO_CONCRETE_TYPE", "null_literal_no_concrete_type"),
        ("UNKNOWN_NULLABILITY", "unknown_nullability"),
        ("SQL_THREE_VALUED_TRUTH", "sql_three_valued_truth"),
        ("DIALECT_LOWERING_GAP", "dialect_lowering_gap"),
        ("CONFLICTING_EVIDENCE", "conflicting_evidence"),
    ]
    assert all(not item.value.startswith("PIE-") for item in CapabilityReasonCode)


def test_slice2_has_no_lookup_result_carriers_registry_or_populated_facts() -> None:
    tree = ast.parse(_runtime_source(), filename=SOURCE_REL)
    class_names = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    assert class_names == {
        "CapabilityDomain",
        "CapabilitySupport",
        "CapabilityDispositionKind",
        "CapabilityEvidenceSource",
        "CapabilityReasonCode",
        "CapabilityKey",
        "CapabilityDisposition",
        "CapabilityEvidence",
        "CapabilityFact",
    }
    assert class_names.isdisjoint(
        {"Found", "Absent", "Unknown", "Conflict", "CapabilityLookupResult"}
    )
    function_names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    assert function_names == {
        "_require_nonblank_text",
        "_require_optional_nonblank_text",
    }
    assert not any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith("Capability")
        for node in tree.body
    )


def test_private_module_has_no_public_compiler_project_or_serializer_consumers() -> (
    None
):
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if (
            path
            in {
                SOURCE_PATH,
                LOOKUP_PATH,
                INVENTORY_PATH,
                SIGNATURE_PATH,
                REPO_ROOT / CONTEXT_REL,
                REPO_ROOT / AGGREGATE_REL,
                REPO_ROOT / "src/pietto/semantic/capability_windows.py",
                REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py",
            }
            or "generated" in path.parts
        ):
            continue
        source = _read(path)
        assert "semantic.capability_facts" not in source
        assert "CapabilityFact" not in source
        assert "CapabilityKey" not in source
    assert "capability_facts" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_facts" not in _read(REPO_ROOT / "src/pietto/__init__.py")
    lookup_source = _read(LOOKUP_PATH)
    assert "semantic.capability_facts" in lookup_source
    assert "CapabilityFact" in lookup_source
    assert "CapabilityKey" in lookup_source
    inventory_source = _read(INVENTORY_PATH)
    assert "semantic.capability_facts" in inventory_source
    assert "CapabilityFact" in inventory_source
    assert "CapabilityKey" in inventory_source
    signature_source = _read(SIGNATURE_PATH)
    assert "semantic.capability_facts" in signature_source
    assert "CapabilityFact" in signature_source
    preservation_source = _read(
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    assert "semantic.capability_facts" in preservation_source
    assert "__all__: tuple[str, ...] = ()" in preservation_source
    assert "CapabilityKey" in signature_source


def test_slice2_spec_locks_read_model_non_authority_and_conflict_preservation() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "private, descriptive,\nnon-authoritative capability fact foundation",
        "Current support and roadmap disposition are orthogonal",
        "Slice 3 owns fail-closed lookup results and precedence",
        "Slices 4-7 own concrete fact families and population",
        "count(alias/Shape)",
        "semantic `LIKE` versus PostgreSQL/private MySQL lowering",
        "matches(Text, Text)",
        "non-Decimal type arguments",
        "division `/`",
        "null literal versus unresolved-expression unknown carriers",
        "generic comparison compatibility",
        "global aggregate post-filtering",
    ):
        assert required in spec
    combined = "\n".join(
        _read(REPO_ROOT / path)
        for path in (
            "docs/plan/phase-52-core-type-system-capability-foundation.md",
            "docs/spec/phase52-core-type-system-capability-foundation-scope-lock-v1.md",
            "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
        )
    )
    assert (
        "Private Capability Key, Disposition, Evidence, And Fact Foundation" in combined
    )
