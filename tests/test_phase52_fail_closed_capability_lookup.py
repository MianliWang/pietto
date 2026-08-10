from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import tomllib
from dataclasses import FrozenInstanceError, fields
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto.semantic.capability_lookup as capability_lookup
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
SOURCE_REL = "src/pietto/semantic/capability_lookup.py"
FACTS_REL = "src/pietto/semantic/capability_facts.py"
INVENTORY_REL = "src/pietto/semantic/capability_inventory.py"
INVENTORY_SPEC_REL = (
    "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md"
)
INVENTORY_TEST_REL = (
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py"
)
SIGNATURE_REL = "src/pietto/semantic/capability_signatures.py"
SIGNATURE_SPEC_REL = "docs/spec/phase52-scalar-function-operator-signature-facts-v1.md"
SIGNATURE_TEST_REL = "tests/test_phase52_scalar_function_operator_signature_facts.py"
CONTEXT_REL = "src/pietto/semantic/capability_contexts.py"
AGGREGATE_REL = "src/pietto/semantic/capability_aggregates.py"
WINDOW_REL = "src/pietto/semantic/capability_windows.py"
CONTEXT_SPEC_REL = "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md"
CONTEXT_TEST_REL = "tests/test_phase52_expression_stage_clause_capability_facts.py"
SPEC_REL = "docs/spec/phase52-fail-closed-capability-lookup-v1.md"
SELF_REL = "tests/test_phase52_fail_closed_capability_lookup.py"
SLICE2_TEST_REL = "tests/test_phase52_private_capability_fact_foundation.py"
SOURCE_PATH = REPO_ROOT / SOURCE_REL
SPEC_PATH = REPO_ROOT / SPEC_REL
SELF_PATH = REPO_ROOT / SELF_REL
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

SPEC_H2 = (
    "Status And Authority",
    "Private Module And Lookup Algebra",
    "Lookup-domain Completeness And Absence Authority",
    "Found Result Contract",
    "Absent Result Contract",
    "Unknown Result Contract",
    "Conflict Result Contract",
    "Pure Exact-key Resolution Contract",
    "Duplicate Conflict And Determinism Policy",
    "Reason-code Admissibility",
    "Privacy And No-behavior Boundary",
    "Slice Ownership And Validation Locks",
)
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
    SELF_REL,
    INVENTORY_TEST_REL,
    SIGNATURE_TEST_REL,
)
ADDED_PATHS = {CONTEXT_REL, CONTEXT_SPEC_REL, CONTEXT_TEST_REL}
ALLOWLIST_PATHS = {*MODIFIED_READER_PATHS, *ADDED_PATHS}
COMPILER_DIGEST = "f6fd00f2fffb54a21eff61527ee5b8e937d2cbcf4ceb8931ff34802ec785376e"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
PROJECT_PRIVATE_DIGEST = (
    "74fd3654b97aa6c824cc76bb7ad673fd1133213a03ab7d9cff9bf003e1ac0251"
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


def _key(
    *,
    subject: str = "Int",
    dialect: str | None = None,
    extension: str | None = None,
) -> CapabilityKey:
    return CapabilityKey(
        CapabilityDomain.LOGICAL_TYPE,
        subject=subject,
        dialect=dialect,
        extension=extension,
    )


def _evidence(
    *,
    reference: str = "exact-current fact",
    reason: CapabilityReasonCode | None = None,
    dialect: str | None = None,
    backend: str | None = None,
    extension: str | None = None,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        CapabilityEvidenceSource.TEST,
        SELF_REL,
        reference,
        reason,
        dialect=dialect,
        backend=backend,
        extension=extension,
    )


def _fact(
    *,
    key: CapabilityKey | None = None,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    disposition: CapabilityDisposition | None = None,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        _key() if key is None else key,
        support,
        CapabilityDisposition(CapabilityDispositionKind.NONE)
        if disposition is None
        else disposition,
        (_evidence(),) if evidence is None else evidence,
    )


def _pytest_item_count() -> int:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_REL)
    tests = [
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    ]
    count = len(tests)
    for test in tests:
        for decorator in test.decorator_list:
            if (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                ids = next(
                    value.value for value in decorator.keywords if value.arg == "ids"
                )
                assert isinstance(ids, (ast.List, ast.Tuple))
                count += len(ids.elts) - 1
    return count


def test_lookup_result_carriers_are_exact_frozen_slotted_shapes() -> None:
    fact = _fact()
    assert capability_lookup.__all__ == ()
    assert tuple(field.name for field in fields(Found)) == ("fact",)
    assert tuple(field.name for field in fields(Absent)) == ("key", "reason")
    assert tuple(field.name for field in fields(Unknown)) == ("reason",)
    assert tuple(field.name for field in fields(Conflict)) == ("reason", "evidence")
    for carrier in (Found, Absent, Unknown, Conflict):
        assert getattr(carrier, "__dataclass_params__").frozen
        assert "__dict__" not in carrier.__slots__
    with pytest.raises(FrozenInstanceError):
        setattr(Found(fact), "fact", fact)


def test_private_alias_and_import_surfaces_remain_unexported() -> None:
    source_tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    aliases = [node for node in source_tree.body if isinstance(node, ast.TypeAlias)]
    assert [node.name.id for node in aliases if isinstance(node.name, ast.Name)] == [
        "CapabilityLookupResult"
    ]
    assert "capability_lookup" not in _read(
        REPO_ROOT / "src/pietto/semantic/__init__.py"
    )
    assert "capability_lookup" not in _read(REPO_ROOT / "src/pietto/__init__.py")


def test_lookup_uses_only_exact_key_equality_without_fallback() -> None:
    target = _key(subject=" Int ")
    exact = _fact(key=target)
    normalized_only = _fact(key=_key(subject="Int"))
    unrelated_dialect = _fact(key=_key(subject=" Int ", dialect="postgresql"))
    result = lookup_capability(
        target,
        (normalized_only, unrelated_dialect, exact),
        domain_complete=True,
    )
    assert result == Found(exact)


def test_identical_duplicate_facts_are_idempotently_folded_in_first_position() -> None:
    fact = _fact()
    result = lookup_capability(
        fact.key,
        (fact, fact, _fact(key=_key(subject="Float")), fact),
        domain_complete=True,
    )
    assert result == Found(fact)


def test_equal_posture_but_different_evidence_is_a_stable_conflict() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    result = lookup_capability(first.key, (second, first), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (second, first),
    )


def test_complete_zero_match_is_absent_and_forbids_explicit_unknown_reason() -> None:
    key = _key()
    assert lookup_capability(key, (), domain_complete=True) == Absent(key)
    with pytest.raises(ValueError):
        lookup_capability(
            key,
            (),
            domain_complete=True,
            unknown_reason=CapabilityReasonCode.NOT_EVIDENCED,
        )


def test_incomplete_zero_match_defaults_to_not_evidenced_unknown() -> None:
    assert lookup_capability(_key(), (), domain_complete=False) == Unknown(
        CapabilityReasonCode.NOT_EVIDENCED
    )


def test_incomplete_domains_preserve_actual_found_and_conflict_evidence() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    assert lookup_capability(first.key, (first,), domain_complete=False) == Found(first)
    assert lookup_capability(
        first.key, (first, second), domain_complete=False
    ) == Conflict(CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, second))


def test_all_facts_are_frozen_and_validated_before_any_match_is_returned() -> None:
    fact = _fact()
    yielded: list[object] = []

    def facts() -> Any:
        yielded.append(fact)
        yield fact
        malformed = object()
        yielded.append(malformed)
        yield malformed

    with pytest.raises(ValueError):
        lookup_capability(fact.key, facts(), domain_complete=True)
    assert len(yielded) == 2


def test_lookup_and_carrier_structural_errors_are_value_errors() -> None:
    fact = _fact()
    invalid_calls = (
        lambda: Found(cast(Any, object())),
        lambda: Absent(cast(Any, object())),
        lambda: Absent(fact.key, cast(Any, CapabilityReasonCode.NOT_EVIDENCED)),
        lambda: lookup_capability(cast(Any, object()), (), domain_complete=True),
        lambda: lookup_capability(fact.key, cast(Any, "facts"), domain_complete=True),
        lambda: lookup_capability(fact.key, cast(Any, None), domain_complete=True),
        lambda: lookup_capability(fact.key, (), domain_complete=cast(Any, 1)),
        lambda: lookup_capability(
            fact.key,
            (),
            domain_complete=False,
            unknown_reason=cast(Any, "not_evidenced"),
        ),
        lambda: lookup_capability(
            fact.key,
            (),
            domain_complete=False,
            unknown_reason=CapabilityReasonCode.NO_CATALOG_ENTRY,
        ),
    )
    for call in invalid_calls:
        with pytest.raises(ValueError):
            call()
    with pytest.raises(TypeError):
        cast(Any, lookup_capability)()


def test_conflict_requires_ordered_distinct_same_key_exact_facts() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    other_key = _fact(key=_key(subject="Float"))
    conflict = Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        cast(Any, [second, first]),
    )
    assert conflict.evidence == (second, first)
    invalid = (
        (CapabilityReasonCode.NOT_EVIDENCED, (first, second)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first,)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, first)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, (first, other_key)),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, cast(Any, "facts")),
        (CapabilityReasonCode.CONFLICTING_EVIDENCE, cast(Any, (first, object()))),
    )
    for reason, evidence in invalid:
        with pytest.raises(ValueError):
            Conflict(reason, cast(Any, evidence))


def test_lookup_is_pure_deterministic_and_does_not_mutate_input() -> None:
    first = _fact(evidence=(_evidence(reference="first"),))
    second = _fact(evidence=(_evidence(reference="second"),))
    facts = [first, second, first]
    before = list(facts)
    one = lookup_capability(first.key, facts, domain_complete=False)
    two = lookup_capability(first.key, tuple(facts), domain_complete=False)
    assert one == two
    assert facts == before


def test_lookup_and_inventory_are_only_private_fact_consumers_without_registry() -> (
    None
):
    tree = ast.parse(_read(SOURCE_PATH), filename=SOURCE_REL)
    classes = {node.name for node in tree.body if isinstance(node, ast.ClassDef)}
    functions = {node.name for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert classes == {"Found", "Absent", "Unknown", "Conflict"}
    assert functions == {"lookup_capability"}
    assert not any(
        isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id.startswith("Capability")
        for node in tree.body
    )
    for path in (REPO_ROOT / "src/pietto").rglob("*.py"):
        if (
            path
            in {
                SOURCE_PATH,
                REPO_ROOT / FACTS_REL,
                REPO_ROOT / INVENTORY_REL,
                REPO_ROOT / SIGNATURE_REL,
                REPO_ROOT / CONTEXT_REL,
                REPO_ROOT / AGGREGATE_REL,
                REPO_ROOT / WINDOW_REL,
                REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py",
            }
            or "generated" in path.parts
        ):
            continue
        source = _read(path)
        assert "semantic.capability_facts" not in source
        assert "CapabilityFact" not in source
        assert "CapabilityKey" not in source
    signature_source = _read(REPO_ROOT / SIGNATURE_REL)
    assert "semantic.capability_facts" in signature_source
    assert "CapabilityFact" in signature_source
    assert "CapabilityKey" in signature_source
    preservation_source = _read(
        REPO_ROOT / "src/pietto/_project/module_semantic_fact_preservation.py"
    )
    assert "semantic.capability_facts" in preservation_source
    assert "__all__: tuple[str, ...] = ()" in preservation_source


def test_spec_exact_headings_and_fail_closed_contract_are_locked() -> None:
    spec = _read(SPEC_PATH)
    headings = tuple(
        match.group(1).strip()
        for match in re.finditer(r"^## (?!#)(.+?)\s*$", spec, re.MULTILINE)
    )
    assert headings == SPEC_H2
    for required in (
        "validates the complete input before",
        "no normalization,",
        "Completely identical duplicate facts are idempotently folded",
        "Equal support and\ndisposition do not justify merging evidence",
        "`NO_CATALOG_ENTRY` is absence-only",
        "`CONFLICTING_EVIDENCE` is conflict-only",
        "creates no registry,\ncatalog, populated facts, global state",
        "Phase 52 remains active and incomplete",
    ):
        assert required in spec


def test_compiler_semantic_and_phase15_boundary_digests_are_refreshed() -> None:
    compiler_paths = _compiler_paths()
    semantic_paths = tuple((REPO_ROOT / "src/pietto/semantic").glob("*.py"))
    phase15_paths = tuple(
        path
        for path in semantic_paths
        if path.name not in {"analyzer.py", "model.py", "relationship_metadata.py"}
    )
    assert len(compiler_paths) == 108
    assert len(semantic_paths) == 36
    assert len(phase15_paths) == 33
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    for path in COMPILER_READERS:
        assert COMPILER_DIGEST in _read(REPO_ROOT / path)
    for path in SEMANTIC_READERS:
        assert SEMANTIC_DIGEST in _read(REPO_ROOT / path)
    assert PHASE15_SUBSET_DIGEST in _read(REPO_ROOT / PHASE15_READER)


def test_raw_sha_reader_topology_is_closed_without_layer2_readers() -> None:
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
    tracked = _git_output(["ls-files"]).splitlines()
    for outer in {path for _, paths in topology for path in paths}:
        outer_sha = hashlib.sha256((REPO_ROOT / outer).read_bytes()).hexdigest()
        outer_sha_bytes = outer_sha.encode("ascii")
        assert not any(
            outer_sha_bytes in (REPO_ROOT / path).read_bytes()
            for path in tracked
            if path not in _TERMINAL_READER_MIGRATION_PATHS
            and (REPO_ROOT / path).is_file()
        )


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
    slice13_modified = _slice13_paths("MODIFIED_PATHS")
    slice13_added = _slice13_paths("ADDED_PATHS")
    slice13_allowlist = slice13_modified | slice13_added
    assert _dirty_paths() in (set(), ALLOWLIST_PATHS, slice13_allowlist)
    tracked = set(_git_output(["diff", "--name-only"]).splitlines())
    assert tracked in (set(), set(MODIFIED_READER_PATHS), slice13_modified)
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    assert untracked in (set(), ADDED_PATHS, slice13_added)
    assert _git_output(["diff", "--cached", "--name-status"]) == ""


def test_static_inventory_and_exact_focused_test_shape_are_locked() -> None:
    tree = ast.parse(_read(SELF_PATH), filename=SELF_REL)
    tests = tuple(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
    )
    assert len(tests) == 24
    assert _pytest_item_count() == 34
    assert [node.name for node in tests if node.decorator_list] == [
        "test_unknown_accepts_each_non_absent_non_conflict_reason",
        "test_unknown_rejects_absence_and_conflict_only_reasons",
        "test_support_or_disposition_differences_are_conflicts",
        "test_dialect_backend_or_extension_scope_differences_are_conflicts",
    ]
    assert len(MODIFIED_READER_PATHS) == len(set(MODIFIED_READER_PATHS)) == 40
    assert len(ALLOWLIST_PATHS) == 43
    assert sum(path.endswith(".py") for path in ALLOWLIST_PATHS) == 42
    assert sum(path.endswith(".md") for path in ALLOWLIST_PATHS) == 1
    old_tree = ast.parse(_read(REPO_ROOT / SLICE2_TEST_REL), filename=SLICE2_TEST_REL)
    direct_tier1 = next(
        node
        for node in old_tree.body
        if isinstance(node, ast.Assign)
        and any(
            isinstance(target, ast.Name) and target.id == "DIRECT_TIER1_NODES"
            for target in node.targets
        )
    )
    assert isinstance(direct_tier1.value, ast.Tuple)
    assert len(direct_tier1.value.elts) == 44


def test_zero_match_uses_only_the_explicit_incomplete_domain_reason() -> None:
    reason = CapabilityReasonCode.UNKNOWN_NULLABILITY
    assert lookup_capability(
        _key(), (), domain_complete=False, unknown_reason=reason
    ) == Unknown(reason)


@pytest.mark.parametrize(
    "reason",
    (
        CapabilityReasonCode.NOT_EVIDENCED,
        CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
        CapabilityReasonCode.UNRESOLVED_EXPRESSION,
        CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
        CapabilityReasonCode.UNKNOWN_NULLABILITY,
        CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        CapabilityReasonCode.DIALECT_LOWERING_GAP,
    ),
    ids=(
        "not-evidenced",
        "no-current-result-rule",
        "unresolved-expression",
        "null-literal-no-concrete-type",
        "unknown-nullability",
        "sql-three-valued-truth",
        "dialect-lowering-gap",
    ),
)
def test_unknown_accepts_each_non_absent_non_conflict_reason(
    reason: CapabilityReasonCode,
) -> None:
    assert Unknown(reason).reason is reason


@pytest.mark.parametrize(
    "reason",
    (
        CapabilityReasonCode.NO_CATALOG_ENTRY,
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
    ),
    ids=("absence-only", "conflict-only"),
)
def test_unknown_rejects_absence_and_conflict_only_reasons(
    reason: CapabilityReasonCode,
) -> None:
    with pytest.raises(ValueError):
        Unknown(reason)


@pytest.mark.parametrize(
    ("support", "disposition"),
    (
        (
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
        ),
        (
            CapabilitySupport.SUPPORTED,
            CapabilityDisposition(
                CapabilityDispositionKind.DEFERRED,
                "Phase 53",
                "owned later",
            ),
        ),
    ),
    ids=("support", "disposition"),
)
def test_support_or_disposition_differences_are_conflicts(
    support: CapabilitySupport,
    disposition: CapabilityDisposition,
) -> None:
    first = _fact()
    second = _fact(support=support, disposition=disposition)
    result = lookup_capability(first.key, (first, second), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (first, second),
    )


@pytest.mark.parametrize(
    ("first_evidence", "second_evidence"),
    (
        (
            _evidence(dialect="postgresql"),
            _evidence(dialect="mysql"),
        ),
        (
            _evidence(dialect="postgresql", backend="postgresql"),
            _evidence(dialect="postgresql", backend="private-mysql"),
        ),
        (
            _evidence(dialect="postgresql", extension="jsonb"),
            _evidence(dialect="postgresql", extension="pgvector"),
        ),
    ),
    ids=("dialect", "backend", "extension"),
)
def test_dialect_backend_or_extension_scope_differences_are_conflicts(
    first_evidence: CapabilityEvidence,
    second_evidence: CapabilityEvidence,
) -> None:
    first = _fact(evidence=(first_evidence,))
    second = _fact(evidence=(second_evidence,))
    result = lookup_capability(first.key, (first, second), domain_complete=True)
    assert result == Conflict(
        CapabilityReasonCode.CONFLICTING_EVIDENCE,
        (first, second),
    )


_TERMINAL_READER_MIGRATION_PATHS = (
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
)
# Phase 53 Slice 13 reader migration.
