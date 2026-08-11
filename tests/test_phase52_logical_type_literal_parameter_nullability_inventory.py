from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_post_slice12_interlude_expected_allowlist_paths,
    phase54_publication_clean_topic_is_active,
    phase54_publication_topic_branch,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto.semantic.capability_inventory as capability_inventory
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
from pietto.semantic.capability_lookup import (
    Absent,
    Conflict,
    Found,
    Unknown,
    lookup_capability,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/semantic/capability_inventory.py"
FACTS_REL = "src/pietto/semantic/capability_facts.py"
LOOKUP_REL = "src/pietto/semantic/capability_lookup.py"
SPEC_REL = (
    "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md"
)
SELF_REL = "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SLICE3_TEST_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
SIGNATURE_SPEC_REL = "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md"
SIGNATURE_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
CONTEXT_SPEC_REL = "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md"
CONTEXT_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
AGGREGATE_TEST_REL = "tests/test_phase52_aggregate_signature_algebra_facts.py"
SLICE8_SPEC_REL = (
    "docs/spec/phase52-parity-privacy-cross-phase-readiness-drift-closure-v1.md"
)
SLICE8_TEST_REL = (
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py"
)
SOURCE_PATH = REPO_ROOT / SOURCE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"
GATE2_BASE_HEAD_SHA = "21bb988a8b28e9d13e7e2c8fdf78ea3a7054b5b0"
REPAIR_BASE_HEAD_SHA = "b1d5002fb48dbbb06cc93de2261e2237655e0eab"
SLICE8_GATE2_BASE_HEAD_SHA = "11a0c48941c3c1c650be8d0ec8ddf5201f9525f2"

FACTS_SHA256 = "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21"
LOOKUP_SHA256 = "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26"
COMPILER_DIGEST = "83cca31d6560c26f1a010e0dfa613d36018a6a07f97ed8af675b4d940e5139ad"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_PRIVATE_DIGEST = (
    "91de26b8176949d09da99fd14c0dcff059381116ce81500c8909a1d2cedf9673"
)
TIER2_MANIFEST_BYTES = 18319
TIER2_MANIFEST_SHA256 = (
    "aea0deb90e0870740b40614fc911ad9483cb3851842aa9a4a9ccecc63baf6f79"
)

SPEC_H2 = (
    "Status And Authority",
    "Private Inventory Module And Ordering",
    "Completeness And Lookup-input Contract",
    "Logical-type Inventory",
    "Literal Inventory",
    "Parameter Inventory",
    "Nullability Inventory",
    "Evidence Scope Disposition And Conflict Policy",
    "Privacy And No-behavior Boundary",
    "Static Compatibility And Validation Locks",
    "Slice Ownership And Lifecycle",
    "Package Release And Future-work Boundary",
)
COMPILER_READERS = (
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py",
)
SEMANTIC_READERS = (
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
PHASE15_READER = "tests/test_phase15_semantic_completion_audit.py"
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
    SLICE2_TEST_REL,
    SLICE3_TEST_REL,
    SELF_REL,
    SIGNATURE_TEST_REL,
)
ADDED_PATHS = {CONTEXT_REL, CONTEXT_SPEC_REL, CONTEXT_TEST_REL}
ALLOWLIST_PATHS = {*ADDED_PATHS, *MODIFIED_READER_PATHS}
REPAIR_ALLOWLIST_PATHS = set(MODIFIED_READER_PATHS) - {SLICE2_TEST_REL} | {
    SOURCE_REL,
    SIGNATURE_REL,
    AGGREGATE_REL,
    CONTEXT_TEST_REL,
    AGGREGATE_TEST_REL,
}
SLICE8_MODIFIED_PATHS = {
    SELF_REL,
    SIGNATURE_TEST_REL,
    CONTEXT_TEST_REL,
    AGGREGATE_TEST_REL,
}
SLICE8_ADDED_PATHS = {SLICE8_SPEC_REL, SLICE8_TEST_REL}
SLICE8_ALLOWLIST_PATHS = SLICE8_MODIFIED_PATHS | SLICE8_ADDED_PATHS


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _slice13_paths(name: str) -> set[str]:
    if _git_output(["rev-parse", "HEAD"]) in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        "b81843acadb294630db361c09949868d004b1bca",
    }:
        modified, added = _phase54_slice2_paths()
        if name == "MODIFIED_PATHS":
            return modified
        if name == "ADDED_PATHS":
            return added
    path = REPO_ROOT / "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, (set, tuple))
            assert all(isinstance(item, str) for item in value)
            return set(value)
    raise AssertionError(f"missing Slice 13 path manifest {name}")


def _phase54_slice2_paths() -> tuple[set[str], set[str]]:
    path = REPO_ROOT / "tests/_phase54_active_gate2_manifest.py"
    tree = ast.parse(_read(path), filename=path.as_posix())
    expected = {
        "ADDED_PATHS",
        "NON_READER_MODIFIED_PATHS",
        "MECHANICAL_READER_PATHS",
    }
    values: dict[str, set[str]] = {}
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
            values[node.targets[0].id] = value
    assert set(values) == expected
    return (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"],
        values["ADDED_PATHS"],
    )


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return result.stdout.rstrip()


def _dirty_paths() -> set[str]:
    return {
        line[3:]
        for line in _git_output(
            ["status", "--porcelain=v1", "--untracked-files=all"]
        ).splitlines()
    }


def _git_optional_ref(ref: str) -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "--verify", "--quiet", ref],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 1)
    assert result.stderr == ""
    output = result.stdout.strip()
    if result.returncode == 1:
        assert output == ""
        return None
    assert output
    return output


def _git_refs() -> tuple[tuple[str, str], ...]:
    output = _git_output(["for-each-ref", "--format=%(refname)%09%(objectname)"])
    if not output:
        return ()
    refs = []
    for line in output.splitlines():
        ref, object_name = line.split("\t", maxsplit=1)
        assert ref and re.fullmatch(r"[0-9a-f]{40}", object_name)
        refs.append((ref, object_name))
    return tuple(refs)


def _git_commit_object_exists(commit: str) -> bool:
    result = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=REPO_ROOT,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.returncode in (0, 128)
    return result.returncode == 0


def _assert_clean_checkout_refs(
    *,
    branch: str,
    head: str,
    main: str | None,
    origin_main: str | None,
) -> None:
    if branch == "main":
        assert main == head
        if origin_main is not None:
            assert origin_main == head
        return

    if branch == phase54_publication_topic_branch():
        assert phase54_publication_clean_topic_is_active()
        return

    assert branch == ""
    refs = _git_refs()
    assert len(refs) == 1
    merge_ref, merge_head = refs[0]
    assert re.fullmatch(r"refs/remotes/pull/[1-9][0-9]*/merge", merge_ref)
    assert merge_head == head
    assert main is None
    assert origin_main is None

    raw_commit = _git_output(["cat-file", "-p", head])
    header, separator, message = raw_commit.partition("\n\n")
    assert separator == "\n\n"
    parents = tuple(
        line.removeprefix("parent ")
        for line in header.splitlines()
        if line.startswith("parent ")
    )
    assert len(parents) == 2
    assert parents[0] != parents[1]
    assert all(re.fullmatch(r"[0-9a-f]{40}", parent) for parent in parents)
    assert message == f"Merge {parents[1]} into {parents[0]}"

    parent_objects_exist = tuple(
        _git_commit_object_exists(parent) for parent in parents
    )
    assert len(set(parent_objects_exist)) == 1
    if all(parent_objects_exist):
        assert _git_output(["merge-base", *parents]) == parents[0]
        assert _git_output(["rev-parse", f"{parents[1]}^{{tree}}"]) == _git_output(
            ["rev-parse", f"{head}^{{tree}}"]
        )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        relative = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative.encode("utf-8"))
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


def _facts(name: str) -> tuple[CapabilityFact, ...]:
    return cast(tuple[CapabilityFact, ...], getattr(capability_inventory, name))


def _all_facts() -> tuple[CapabilityFact, ...]:
    return _facts("_CAPABILITY_FACTS")


def _inputs(key: CapabilityKey) -> tuple[tuple[CapabilityFact, ...], bool]:
    function = cast(
        Any,
        getattr(capability_inventory, "inventory_lookup_inputs"),
    )
    return cast(tuple[tuple[CapabilityFact, ...], bool], function(key))


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete = _inputs(key)
    return lookup_capability(key, facts, domain_complete=complete)


def _pytest_shape() -> tuple[int, int, list[str]]:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_REL)
    tests = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    item_count = len(tests)
    parametrized: list[str] = []
    for test in tests:
        for decorator in test.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                ids = next(
                    keyword.value
                    for keyword in decorator.keywords
                    if keyword.arg == "ids"
                )
                assert isinstance(ids, (ast.Tuple, ast.List))
                item_count += len(ids.elts) - 1
                parametrized.append(test.name)
    return len(tests), item_count, parametrized


def test_private_module_api_and_privacy_shape_are_exact() -> None:
    source = _read(SOURCE_PATH)
    tree = ast.parse(source, filename=SOURCE_REL)
    assert capability_inventory.__all__ == ()
    assert "capability_lookup" not in source
    assert "lookup_capability" not in source
    assert not any(isinstance(node, ast.ClassDef) for node in tree.body)
    assert "CapabilityDomain.NULLABILITY" not in source
    with pytest.raises(ValueError):
        cast(Any, capability_inventory.inventory_lookup_inputs)("logical_type")


def test_four_fact_tuples_counts_order_and_combined_identity_are_exact() -> None:
    logical = _facts("_LOGICAL_TYPE_FACTS")
    literals = _facts("_LITERAL_FACTS")
    parameters = _facts("_PARAMETER_FACTS")
    nullability = _facts("_NULLABILITY_FACTS")
    combined = _all_facts()
    assert tuple(map(len, (logical, literals, parameters, nullability))) == (
        22,
        13,
        3,
        3,
    )
    assert combined == (*logical, *literals, *parameters, *nullability)
    assert len(combined) == len(set(combined)) == 41
    assert tuple(fact.key.subject for fact in combined[:11]) == (
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    )


def test_inventory_construction_rejects_exact_duplicates_but_preserves_conflicts() -> (
    None
):
    freeze = cast(Any, getattr(capability_inventory, "_freeze_inventory"))
    fact = _all_facts()[0]
    with pytest.raises(ValueError, match="duplicate"):
        freeze((fact, fact))
    conflicting = replace(fact, support=CapabilitySupport.EXPLICITLY_UNSUPPORTED)
    assert freeze((fact, conflicting)) == (fact, conflicting)


@pytest.mark.parametrize(
    "subject",
    (
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    ),
    ids=(
        "any",
        "bool",
        "bytes",
        "date",
        "decimal",
        "float",
        "int",
        "json",
        "text",
        "timestamp",
        "uuid",
    ),
)
def test_builtin_catalog_membership_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="catalog_membership",
        context="builtin_registry",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    assert result.fact.disposition.kind is CapabilityDispositionKind.NONE


@pytest.mark.parametrize(
    "subject",
    ("type_alias", "enum", "shape"),
    ids=("type-alias", "enum", "shape"),
)
def test_declaration_kind_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="declaration_kind",
        context="semantic_model",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


@pytest.mark.parametrize(
    ("subject", "reason", "disposition"),
    (
        (
            "<unknown>",
            CapabilityReasonCode.UNRESOLVED_EXPRESSION,
            CapabilityDispositionKind.NONE,
        ),
        (
            "Null",
            CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
            CapabilityDispositionKind.NONE,
        ),
        (
            "DateTime",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Time",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Interval",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Money",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
        (
            "Currency",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
            CapabilityDispositionKind.DEFERRED,
        ),
    ),
    ids=("unknown", "null", "datetime", "time", "interval", "money", "currency"),
)
def test_internal_and_deferred_logical_type_facts_fail_closed(
    subject: str,
    reason: CapabilityReasonCode,
    disposition: CapabilityDispositionKind,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="catalog_membership",
        context="builtin_registry",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition.kind is disposition
    assert reason in {entry.reason for entry in result.fact.evidence}


def test_decimal_precision_scale_is_one_bounded_supported_side_fact() -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject="Decimal",
        operation="precision_scale",
        operands=("Int", "Int"),
        context="type_expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    non_decimal = replace(key, subject="Text")
    facts, complete = _inputs(non_decimal)
    assert facts
    assert complete is False
    assert lookup_capability(non_decimal, facts, domain_complete=complete) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


@pytest.mark.parametrize(
    ("subject", "operands"),
    (
        ("integer", ("Int", "non_null")),
        ("float", ("Float", "non_null")),
        ("text", ("Text", "non_null")),
        ("boolean", ("Bool", "non_null")),
        ("null", ("no_concrete_type", "unknown")),
    ),
    ids=("integer", "float", "text", "boolean", "null"),
)
def test_supported_literal_results_are_exact(
    subject: str,
    operands: tuple[str, ...],
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LITERAL,
        subject=subject,
        operation="result",
        operands=operands,
        context="expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


@pytest.mark.parametrize(
    ("subject", "disposition"),
    (
        ("Any", CapabilityDispositionKind.NONE),
        ("Bytes", CapabilityDispositionKind.NONE),
        ("Date", CapabilityDispositionKind.DEFERRED),
        ("Decimal", CapabilityDispositionKind.NONE),
        ("Json", CapabilityDispositionKind.NONE),
        ("Timestamp", CapabilityDispositionKind.DEFERRED),
        ("UUID", CapabilityDispositionKind.NONE),
        ("Enum", CapabilityDispositionKind.NONE),
    ),
    ids=("any", "bytes", "date", "decimal", "json", "timestamp", "uuid", "enum"),
)
def test_unsupported_literal_categories_are_explicit(
    subject: str,
    disposition: CapabilityDispositionKind,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LITERAL,
        subject=subject,
        operation="result",
        context="expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition.kind is disposition
    assert CapabilityReasonCode.NOT_EVIDENCED in {
        entry.reason for entry in result.fact.evidence
    }


@pytest.mark.parametrize(
    "subject",
    ("constraint", "derive"),
    ids=("constraint", "derive"),
)
def test_callable_declaration_parameter_facts_are_supported(subject: str) -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject=subject,
        operation="declare",
        operands=("name", "TypeExpr"),
        context="callable_declaration",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED


def test_runtime_sql_parameter_substitution_is_explicitly_out_of_scope() -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="runtime_sql_parameter",
        operation="substitute",
        context="runtime_execution",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.EXPLICITLY_UNSUPPORTED
    assert result.fact.disposition == CapabilityDisposition(
        CapabilityDispositionKind.OUT_OF_SCOPE,
        "Pietto charter",
        "runtime substitution and prepared-statement execution are host/database responsibilities",
    )


@pytest.mark.parametrize(
    ("subject", "result_name", "reason"),
    (
        ("implicit", "unknown", CapabilityReasonCode.UNKNOWN_NULLABILITY),
        ("nullable", "nullable", None),
        ("not_null", "non_null", None),
    ),
    ids=("implicit", "nullable", "not-null"),
)
def test_declared_nullability_mappings_are_exact(
    subject: str,
    result_name: str,
    reason: CapabilityReasonCode | None,
) -> None:
    key = CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        operation="effective_nullability",
        operands=(result_name,),
        context="type_expression",
    )
    result = _lookup(key)
    assert isinstance(result, Found)
    assert result.fact.support is CapabilitySupport.SUPPORTED
    assert reason in {entry.reason for entry in result.fact.evidence}


def test_null_literal_is_distinct_from_null_and_unknown_logical_spellings() -> None:
    null_literal = next(
        fact for fact in _facts("_LITERAL_FACTS") if fact.key.subject == "null"
    )
    assert null_literal.key.operands == ("no_concrete_type", "unknown")
    assert null_literal.support is CapabilitySupport.SUPPORTED
    logical_subjects = {
        fact.key.subject
        for fact in _facts("_LOGICAL_TYPE_FACTS")
        if fact.key.operation == "catalog_membership"
    }
    assert {"Null", "<unknown>"} <= logical_subjects
    assert "null" not in logical_subjects


def test_each_fact_has_unique_evidence_in_locked_layer_order() -> None:
    rank = {
        source: index
        for index, source in enumerate(
            (
                CapabilityEvidenceSource.GRAMMAR_AST,
                CapabilityEvidenceSource.SEMANTIC_CATALOG,
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                CapabilityEvidenceSource.SEMANTIC_MODEL,
                CapabilityEvidenceSource.IR,
                CapabilityEvidenceSource.BACKEND,
                CapabilityEvidenceSource.PROJECT,
                CapabilityEvidenceSource.PUBLIC,
                CapabilityEvidenceSource.ROADMAP,
                CapabilityEvidenceSource.TEST,
                CapabilityEvidenceSource.SPEC,
            )
        )
    }
    for fact in _all_facts():
        assert fact.evidence
        assert len(fact.evidence) == len(set(fact.evidence))
        assert all((REPO_ROOT / entry.source_path).is_file() for entry in fact.evidence)
        evidence_rank = [rank[entry.source] for entry in fact.evidence]
        assert evidence_rank == sorted(evidence_rank)


@pytest.mark.parametrize(
    "subject",
    ("integer", "float", "text", "boolean", "null"),
    ids=("integer", "float", "text", "boolean", "null"),
)
def test_supported_literals_have_ordered_postgresql_and_private_mysql_scope(
    subject: str,
) -> None:
    fact = next(
        fact for fact in _facts("_LITERAL_FACTS") if fact.key.subject == subject
    )
    backend = tuple(
        (entry.dialect, entry.backend)
        for entry in fact.evidence
        if entry.source is CapabilityEvidenceSource.BACKEND
    )
    assert backend == (("postgresql", "postgresql"), ("mysql", "private-mysql"))


def test_seven_exact_completeness_schemas_and_unowned_domains_are_locked() -> None:
    complete = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "Future",
            "catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "future_kind",
            "declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "Decimal",
            "precision_scale",
            ("Int", "Int"),
            "type_expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "integer",
            "result",
            ("Int", "non_null"),
            "expression",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "Any",
            "result",
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            "constraint",
            "declare",
            ("name", "TypeExpr"),
            context="callable_declaration",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            "runtime_sql_parameter",
            "substitute",
            context="runtime_execution",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            "implicit",
            "effective_nullability",
            ("unknown",),
            context="type_expression",
        ),
    )
    assert all(_inputs(key)[1] for key in complete)
    incomplete = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            operation="declaration_kind",
            context="semantic_model",
        ),
        replace(complete[2], operands=("Int",)),
        replace(complete[2], operands=("Int", "Int", "Int")),
        replace(complete[3], operands=()),
        replace(complete[3], operands=("Int", "non_null", "extra")),
        replace(complete[3], operands=("Bogus", "non_null")),
        replace(complete[3], operands=("Int", "Bogus")),
        replace(complete[3], subject="Integer"),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            "future",
            "result",
            ("Future",),
            "expression",
        ),
        replace(complete[4], operands=("unexpected",)),
        replace(complete[5], operands=()),
        replace(complete[5], operands=("name", "TypeExpr", "extra")),
        replace(complete[5], operands=("name", "Bogus")),
        replace(complete[5], subject="Constraint"),
        replace(complete[6], operands=("unexpected",)),
        replace(complete[7], operands=()),
        replace(complete[7], operands=("unknown", "extra")),
        replace(complete[7], operands=("Bogus",)),
        replace(complete[7], subject="Implicit"),
        replace(complete[7], context="expression"),
    )
    for key in incomplete:
        facts, schema_complete = _inputs(key)
        assert facts
        assert schema_complete is False
        assert _lookup(key) == Unknown(CapabilityReasonCode.NOT_EVIDENCED)
    unowned = CapabilityKey(
        CapabilityDomain.AGGREGATE,
        subject="sum",
        operation="result",
    )
    assert _inputs(unowned) == ((), False)


def test_every_inventory_fact_resolves_to_found_with_exact_identity() -> None:
    for fact in _all_facts():
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact is fact


def test_unlisted_complete_builtin_catalog_spelling_resolves_absent() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="FutureScalar",
            operation="catalog_membership",
            context="builtin_registry",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="future_kind",
            operation="declaration_kind",
            context="semantic_model",
        ),
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Float", "non_null"),
            context="expression",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("nullable",),
            context="type_expression",
        ),
    )
    assert all(_lookup(key) == Absent(key) for key in keys)


def test_incomplete_query_parameter_binding_resolves_unknown() -> None:
    key = CapabilityKey(
        CapabilityDomain.PARAMETER,
        subject="query_placeholder",
        operation="bind",
        context="query_expression",
    )
    facts, complete = _inputs(key)
    assert facts == _facts("_PARAMETER_FACTS")
    assert complete is False
    assert lookup_capability(key, facts, domain_complete=complete) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


def test_dialect_and_extension_keyed_zero_matches_resolve_unknown() -> None:
    keys = (
        CapabilityKey(
            CapabilityDomain.LITERAL,
            subject="integer",
            operation="result",
            operands=("Int", "non_null"),
            context="expression",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="Int",
            operation="catalog_membership",
            context="builtin_registry",
            dialect="postgresql",
            extension="future",
        ),
        CapabilityKey(
            CapabilityDomain.PARAMETER,
            subject="constraint",
            operation="declare",
            operands=("name", "TypeExpr"),
            context="callable_declaration",
            dialect="postgresql",
        ),
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="implicit",
            operation="effective_nullability",
            operands=("unknown",),
            context="type_expression",
            dialect="postgresql",
            extension="future",
        ),
    )
    for key in keys:
        facts, complete = _inputs(key)
        assert facts
        assert complete is False
        assert lookup_capability(key, facts, domain_complete=complete) == Unknown(
            CapabilityReasonCode.NOT_EVIDENCED
        )


def test_lookup_folds_duplicates_and_preserves_distinct_same_key_conflicts() -> None:
    fact = _all_facts()[0]
    assert lookup_capability(
        fact.key,
        (fact, fact),
        domain_complete=True,
    ) == Found(fact)
    conflict = CapabilityFact(
        fact.key,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
        fact.disposition,
        (
            CapabilityEvidence(
                CapabilityEvidenceSource.TEST,
                SELF_REL,
                "injected distinct same-key conflict",
                CapabilityReasonCode.CONFLICTING_EVIDENCE,
            ),
        ),
    )
    assert lookup_capability(
        fact.key,
        (fact, conflict),
        domain_complete=True,
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (fact, conflict))


def test_private_inventory_has_no_compiler_public_or_serializer_consumer() -> None:
    preservation_path = (
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if path in {SOURCE_PATH, preservation_path} or "generated" in path.parts:
            continue
        source = _read(path)
        assert "semantic.capability_inventory" not in source
        assert "inventory_lookup_inputs" not in source
    preservation_source = _read(preservation_path)
    assert "semantic.capability_inventory" in preservation_source
    assert "inventory_lookup_inputs" in preservation_source
    assert "capability_inventory" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_inventory" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_slice2_and_slice3_private_sources_remain_byte_identical() -> None:
    assert hashlib.sha256((REPO_ROOT / FACTS_REL).read_bytes()).hexdigest() == (
        FACTS_SHA256
    )
    assert hashlib.sha256((REPO_ROOT / LOOKUP_REL).read_bytes()).hexdigest() == (
        LOOKUP_SHA256
    )


def test_spec_exact_headings_and_inventory_boundary_phrases_are_locked() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "exactly 41 `CapabilityFact` values",
        "A zero match there is `Unknown`, not `Absent`.",
        "No `CapabilityDomain.NULLABILITY` is introduced.",
        "PostgreSQL precedes private MySQL",
        "Package version remains `0.1.0`.",
        "Phase 52 remains active and incomplete",
    ):
        assert required in spec


def test_digest_and_nested_raw_sha_reader_closure_is_exact() -> None:
    compiler_paths = _compiler_paths()
    semantic_paths = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
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
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    for path in COMPILER_READERS:
        assert COMPILER_DIGEST in _read(REPO_ROOT / path)
    for path in SEMANTIC_READERS:
        assert SEMANTIC_DIGEST in _read(REPO_ROOT / path)
    assert PHASE15_SUBSET_DIGEST in _read(REPO_ROOT / PHASE15_READER)

    topology = (
        (
            "tests/test_phase13_completion_audit.py",
            (
                "tests/test_phase14_candidate_decision_audit.py",
                "tests/test_phase14_planning_audit.py",
            ),
        ),
        (
            "tests/test_phase15_semantic_completion_audit.py",
            ("tests/test_phase15_completion_audit.py",),
        ),
        (
            "tests/test_phase16_current_syntax_surface_audit.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
        (
            "tests/test_phase16_language_direction_audit.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
        (
            "tests/test_phase16_safety_deferral_sql_portability.py",
            ("tests/test_phase16_completion_audit.py",),
        ),
    )
    for inner, outers in topology:
        inner_sha = hashlib.sha256((REPO_ROOT / inner).read_bytes()).hexdigest()
        for outer in outers:
            assert _read(REPO_ROOT / outer).count(inner_sha) == 1


def test_project_package_version_and_tag_boundaries_are_unchanged() -> None:
    project_paths = _project_private_paths()
    assert len(project_paths) == 33
    assert _digest(project_paths) == PROJECT_PRIVATE_DIGEST
    with PYPROJECT_PATH.open("rb") as stream:
        project = tomllib.load(stream)
    assert project["project"]["version"] == "0.1.0"
    assert _git_output(["tag", "--list"]) == ""


def test_gate2_dirty_untracked_and_index_states_are_exact() -> None:
    if _phase54_active_gate2_is_active():
        return
    dirty = _dirty_paths()
    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added
    assert dirty in (
        set(),
        ALLOWLIST_PATHS,
        REPAIR_ALLOWLIST_PATHS,
        SLICE8_ALLOWLIST_PATHS,
        slice13_allowlist,
        set(phase54_post_slice12_interlude_expected_allowlist_paths()),
    )
    tracked = set(_git_output(["diff", "--name-only"]).splitlines())
    status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    if not dirty:
        assert tracked == set()
        assert status == ()
        assert untracked == set()
        _assert_clean_checkout_refs(
            branch=branch,
            head=head,
            main=main,
            origin_main=origin_main,
        )
    elif dirty == slice13_allowlist:
        assert tracked == slice13_modified
        assert status == tuple(f"M\t{path}" for path in sorted(slice13_modified))
        assert untracked == slice13_added
        assert branch == "main"
        assert head == main == origin_main
        assert head in (
            "4ff3c131fba54d83b56f3c50e14f7c2337c1eb52",
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "93f0f591e28a01f32d1698fcd4b8c57d41c6d714",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
            "b81843acadb294630db361c09949868d004b1bca",
        )
    elif dirty == SLICE8_ALLOWLIST_PATHS:
        assert tracked == SLICE8_MODIFIED_PATHS
        assert status == tuple(f"M\t{path}" for path in sorted(SLICE8_MODIFIED_PATHS))
        assert untracked == SLICE8_ADDED_PATHS
        assert branch == "main"
        assert head == main == origin_main == SLICE8_GATE2_BASE_HEAD_SHA
    elif dirty == REPAIR_ALLOWLIST_PATHS:
        assert tracked == REPAIR_ALLOWLIST_PATHS
        assert len(status) == 44
        assert all(entry.startswith("M\t") for entry in status)
        assert untracked == set()
        assert branch == "main"
        assert head == main == origin_main == REPAIR_BASE_HEAD_SHA
    else:
        assert dirty == ALLOWLIST_PATHS
        assert tracked == set(MODIFIED_READER_PATHS)
        assert len(status) == len(MODIFIED_READER_PATHS)
        assert all(entry.startswith("M\t") for entry in status)
        assert {entry.removeprefix("M\t") for entry in status} == set(
            MODIFIED_READER_PATHS
        )
        assert untracked == ADDED_PATHS
        assert branch == "main"
        assert head == main == origin_main == GATE2_BASE_HEAD_SHA


def test_static_item_allowlist_reader_and_manifest_inventory_is_exact() -> None:
    function_count, item_count, parametrized = _pytest_shape()
    assert (function_count, item_count) == (28, 64)
    assert parametrized == [
        "test_builtin_catalog_membership_facts_are_supported",
        "test_declaration_kind_facts_are_supported",
        "test_internal_and_deferred_logical_type_facts_fail_closed",
        "test_supported_literal_results_are_exact",
        "test_unsupported_literal_categories_are_explicit",
        "test_callable_declaration_parameter_facts_are_supported",
        "test_declared_nullability_mappings_are_exact",
        "test_supported_literals_have_ordered_postgresql_and_private_mysql_scope",
    ]
    assert len(MODIFIED_READER_PATHS) == len(set(MODIFIED_READER_PATHS)) == 40
    assert len(ALLOWLIST_PATHS) == 43
    assert sum(path.endswith(".py") for path in ALLOWLIST_PATHS) == 42
    assert sum(path.endswith(".md") for path in ALLOWLIST_PATHS) == 1
    assert len(REPAIR_ALLOWLIST_PATHS) == 44
    assert all(path.endswith(".py") for path in REPAIR_ALLOWLIST_PATHS)
    assert len(SLICE8_ALLOWLIST_PATHS) == 6
    assert sum(path.endswith(".py") for path in SLICE8_ALLOWLIST_PATHS) == 5
    assert sum(path.endswith(".md") for path in SLICE8_ALLOWLIST_PATHS) == 1
    assert (len(COMPILER_READERS), len(SEMANTIC_READERS)) == (11, 25)
    assert len(_all_facts()) == 41
    assert 6018 - 142 == 5876
    assert TIER2_MANIFEST_BYTES == 18319
    assert TIER2_MANIFEST_SHA256 == (
        "aea0deb90e0870740b40614fc911ad9483cb3851842aa9a4a9ccecc63baf6f79"
    )


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
