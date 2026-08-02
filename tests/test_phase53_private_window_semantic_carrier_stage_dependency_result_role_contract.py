from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields, is_dataclass
import hashlib
import inspect
from pathlib import Path
import subprocess
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_active_gate2_manifest_is_active as _phase54_product_repair1_gate2_is_active,
)

import pytest

import pietto
import pietto._project as project_package
import pietto._project.window_semantics as project_window_semantics
import pietto.semantic as semantic_package
import pietto.semantic.window_semantics as semantic_window_semantics
from pietto._project.model import (
    ProjectRowFieldProvenance,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
)
from pietto._project.row_dependency_graph import (
    ProjectRowDependencyNode,
    ProjectRowDependencyNodeKind,
)
from pietto._project.window_semantics import (
    WindowDependencyEdge,
    WindowDependencyOccurrence,
    WindowDependencyRole,
    WindowResultIdentity,
    WindowResultProjectFact,
    deduplicate_window_dependency_edges,
)
from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    FromClause,
    NameExpr,
    QueryDef,
    Span,
    TableDef,
    WindowExpr,
    WindowSpec,
)
from pietto.errors import SourceLocation
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    NavigationWindowSemanticFact,
    WindowExpressionSemanticFact,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowOccurrenceIdentity,
    WindowResultAvailability,
    WindowResultAvailabilityKind,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_PATH = REPO_ROOT / "src/pietto/semantic/window_semantics.py"
PROJECT_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/window_semantics.py"
MODEL_PATH = REPO_ROOT / "src/pietto/_project/model.py"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase53-private-window-semantic-carrier-stage-dependency-result-role-contract-v1.md"
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
    "Phase 53 Slice 6 Private Window Semantic Carrier, WINDOW Stage, "
    "Dependency, And Result Roles v1"
)
SPEC_H2 = (
    "Status And Slice Identity",
    "Existing Window AST And Identity Authority",
    "Existing Generic And Nullability Authority",
    "Private Module Placement And Layering",
    "Semantic Carrier Architecture",
    "WINDOW Stage Contract",
    "Result Availability And Type-nullability Posture",
    "Stable Window Occurrence Identity",
    "Project Result Identity And Output Alias Contract",
    "Result-role Architecture",
    "Dependency-role Inventory",
    "Occurrence Evidence And Deduplicated Edge Contract",
    "Relation-input And Zero-argument Readiness",
    "Nested And Same-select Non-representability",
    "Provenance And Derived-origin Contract",
    "Project Fact Composition And Ordering",
    "Constructor And Failure Boundary",
    "Current Analyzer Catalog And Capability Non-integration",
    "Project-model Non-integration",
    "Public Privacy And Serialization Boundary",
    "Positive Carrier Matrix",
    "Negative And Fail-closed Matrix",
    "Grammar AST Generated Generic Nullability IR SQL And Behavior Immutability",
    "Reader Hash Inventory And Repository-state Closure",
    "Validation Depth-one CI And Gate 3 Publication",
    "Deferred Ownership And Stop Conditions",
)
PLAN_H2 = (
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
    "test_slice6_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_semantic_private_module_enum_carrier_and_privacy_shapes_are_exact",
    "test_project_private_module_enum_carrier_and_privacy_shapes_are_exact",
    "test_window_occurrence_identity_valid_matrix_is_exact",
    "test_window_occurrence_identity_equality_hash_repr_and_repeatability_are_exact",
    "test_window_occurrence_identity_malformed_matrix_fails_closed",
    "test_concrete_window_result_availability_matrix_is_exact",
    "test_nonconcrete_window_result_availability_matrix_is_exact",
    "test_window_result_availability_malformed_matrix_fails_closed",
    "test_window_semantic_fact_has_fixed_stage_and_exact_identity",
    "test_window_semantic_unsupported_evidence_is_structural_only",
    "test_window_semantic_fact_mismatch_matrix_fails_closed",
    "test_window_carriers_do_not_store_generic_or_nullability_formula_evidence",
    "test_window_result_identity_requires_explicit_alias_and_occurrence",
    "test_project_row_result_role_window_result_extension_is_exact",
    "test_window_dependency_role_inventory_and_phase60_frame_absence_are_exact",
    "test_window_dependency_occurrence_positive_role_target_matrix_is_exact",
    "test_window_dependency_occurrence_role_payload_negative_matrix_fails_closed",
    "test_window_dependency_global_and_role_local_ordering_matrix_is_exact",
    "test_repeated_dependency_occurrences_are_preserved_and_edges_first_deduped",
    "test_same_target_across_dependency_roles_remains_distinct",
    "test_zero_argument_relation_input_readiness_and_failure_matrix_is_exact",
    "test_same_select_and_nested_window_dependencies_are_nonrepresentable",
    "test_window_result_uses_existing_derived_expression_provenance",
    "test_window_result_provenance_mismatch_matrix_fails_closed",
    "test_window_result_project_fact_is_frozen_hashable_and_repeatable",
    "test_slice7_and_slice12_construction_readiness_matrix_is_exact",
    "test_current_analyzer_catalog_and_diagnostic_nonintegration_is_exact",
    "test_project_model_checker_and_serializers_have_no_window_population",
    "test_grammar_ast_parser_identity_generic_and_nullability_hashes_are_locked",
    "test_ir_sql_capability_public_runtime_and_package_surfaces_are_locked",
    "test_slice6_spec_heading_scope_and_no_h3_contract_is_exact",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice6_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_and_dirty_overlay_are_exact",
    "test_validation_gate3_and_no_behavior_boundaries_are_locked",
)
TEST_ITEM_COUNTS = (
    1,
    1,
    1,
    4,
    2,
    16,
    3,
    3,
    12,
    2,
    2,
    8,
    1,
    3,
    1,
    1,
    8,
    16,
    6,
    5,
    3,
    4,
    4,
    3,
    6,
    2,
    4,
    3,
    4,
    10,
    12,
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

# Filled after the single write formatter; later edits are literal-only.
FINAL_SOURCE_SHA256 = "d6a514bddffee9f53ca1405d28a2dcd9cc84a395a152aacc1ccb9e5b716a5905"
FINAL_PROJECT_SOURCE_SHA256 = (
    "c08a42066a71a3ee13be9feddff5e28a910b216226d7e0b8869ee52a90dea2ad"
)
FINAL_MODEL_SHA256 = "965342eb72c1089b315e598666410605dcf4adf8ddc50a0fc695fb82e3b8df1c"
FINAL_SPEC_SHA256 = "e3cddc36974cc2d21bd3e0aec8d03c4f56bc4a68091780d9965207f07ea960e7"
FINAL_PLAN_SHA256 = "3077c2fec0d7e2c4de717973c6403d5a450b8c01fe5846e427363ffcb41a78f5"
FINAL_COMPILER_DIGEST = (
    "0ad4101136a87f2d1ad19c845bff69a97fb01b02428e3c36ff0999b3b9e8bcfa"
)
FINAL_SEMANTIC_DIGEST = (
    "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
)
FINAL_PHASE15_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
FINAL_PROJECT_DIGEST = (
    "240e1528b5c524107d8ab5d2edc476083bcd08e391acbfd399a73528a102cd55"
)

BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
CI_REPAIR_BASE_HEAD_SHA = "321ec6f80737015648bc1f81b0561fdd34610e92"
CI_REPAIR_MODIFIED_PATHS = frozenset(
    {
        "tests/test_phase51_aggregate_grouped_downstream_propagation.py",
        "tests/test_phase51_aggregate_grouped_origin_dependency_lineage.py",
        "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    }
)

ANALYZER_CATALOG_DIAGNOSTIC_LOCKS = (
    (
        "src/pietto/semantic/analyzer.py",
        "7a6f2830bf3710edab3ba5a8c4a72e90c6e44de19fe19ddd2b54b5d703277b32",
    ),
    (
        "src/pietto/semantic/catalog.py",
        "f566f39395e3bdc933e60d15e740749255dd3749cf3907684240e4b43dfc9e40",
    ),
    (
        "src/pietto/semantic/expressions.py",
        "37b198f72b0c71c90a82d746671be8528a9ea5c2d4818ff7ef4ba55e30e9c595",
    ),
)

GRAMMAR_AST_GENERIC_NULLABILITY_LOCKS = (
    (
        "grammar/Pietto.g4",
        "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
    ),
    (
        "src/pietto/ast_nodes.py",
        "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2",
    ),
    (
        "src/pietto/ast_builder.py",
        "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb",
    ),
    (
        "src/pietto/parser_api.py",
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
    ),
    (
        "src/pietto/_window_identity.py",
        "d1223f7095790dc08ffc176c103ae6180cd9e03773ddf9763448d482d6984c9b",
    ),
    (
        "src/pietto/semantic/model.py",
        "55f1d110854073ec3f9b47ecffd3e41c6c2bc3b606da61e8b271a23e736bd4ba",
    ),
    (
        "src/pietto/semantic/generic_compatibility.py",
        "340703267a6185f0b37401c1097a1f246d34d3d0d46c1f583b5ce5134e5090f8",
    ),
    (
        "src/pietto/semantic/nullability_formulas.py",
        "f4b39fc1446af80ec223b0043ee3e76700dd83224eea8e2a5f60a609a5dd5933",
    ),
    (
        "src/pietto/generated/__init__.py",
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    ),
    (
        "src/pietto/generated",
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1",
    ),
)

IR_SQL_CAPABILITY_PUBLIC_LOCKS = (
    (
        "src/pietto/ir",
        "04cb667ff3c9cdf0189d9fd0caa5dc0f9db74ca78dd86e965f020b4523f543e9",
    ),
    (
        "src/pietto/sql",
        "72a23f954c49337192effe005c9b3331359b132cc06f494fd4922b9718d1c026",
    ),
    (
        "src/pietto/semantic/capability_facts.py",
        "bd68bad4e13a2b945962458fc47359a408d27b1563ba25f5713a8f8099671d21",
    ),
    (
        "src/pietto/semantic/capability_lookup.py",
        "4d4c2676b3181758f01c95ca312fd0f76cebcb74ac1bcab0deefb15fc04abf26",
    ),
    (
        "src/pietto/semantic/capability_inventory.py",
        "f11eee2a53fda26057c35be047bfa265c68794ad76054bc5636781f0b5164b26",
    ),
    (
        "src/pietto/semantic/capability_signatures.py",
        "810f347080e0bb7dc674821aa6387c5f7618ac216832194ef19820326eef71d2",
    ),
    (
        "src/pietto/semantic/capability_contexts.py",
        "132371eccca00ca9f8722a34f1ea0f540933515e560639ee12e53aee6594c60c",
    ),
    (
        "src/pietto/semantic/capability_aggregates.py",
        "d7d69fa4b97924ef5462af9c871a910b73cad43a21431e98a72c8bdab8996c80",
    ),
    (
        "src/pietto/cli.py",
        "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09",
    ),
    (
        "src/pietto/cli_json.py",
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91",
    ),
    (
        "src/pietto/_metadata",
        "cd49c38e64e6a89fa165896bdecbffcc50c68fc9ed94dcf1d50db90b1819f86d",
    ),
    (
        "pyproject.toml",
        "36aa8e1d19a8409e56e0163a465b9608a88c1bffe644165ba49db49bf5ec3d01",
    ),
)


def _span(
    *,
    path: str | None = "query.pietto",
    line: int = 3,
    column: int = 9,
    end_line: int = 3,
    end_column: int = 43,
) -> Span:
    return Span(
        path=path,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )


def _identity(name: str = "row_number") -> WindowFunctionIdentity:
    return WindowFunctionIdentity(
        namespace=(),
        name=name,
        role=WindowFunctionRole.WINDOW_FUNCTION,
    )


def _window_expression(
    *,
    span: Span | None = None,
    identity: WindowFunctionIdentity | None = None,
    argument_count: int = 0,
) -> WindowExpr:
    expression_span = span or _span()
    function_identity = identity or _identity()
    callee = NameExpr(span=expression_span, name=function_identity.name)
    arguments = tuple(
        NameExpr(span=expression_span, name=f"arg_{index}")
        for index in range(argument_count)
    )
    call = CallExpr(
        span=expression_span,
        callee=callee,
        arguments=arguments,
    )
    partition = NameExpr(span=expression_span, name="account_id")
    spec = WindowSpec(
        span=expression_span,
        partition_by=(partition,),
        order_by=(),
    )
    return WindowExpr(
        span=expression_span,
        call=call,
        spec=spec,
        identity=function_identity,
    )


def _occurrence(
    *,
    source_id: str = "query.pietto",
    relation_name: str = "ranked",
    ordinal: int = 0,
    span: Span | None = None,
) -> WindowOccurrenceIdentity:
    return WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=relation_name,
        selected_output_ordinal=ordinal,
        span=span or _span(path=source_id),
    )


def _value_type(
    *,
    name: str = "Int",
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
    kind: ValueTypeKind = ValueTypeKind.KNOWN,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=name, kind=TypeKind.BUILTIN),
        nullability=nullability,
        kind=kind,
    )


def _availability(
    *,
    nullability: EffectiveNullability = EffectiveNullability.NON_NULL,
) -> WindowResultAvailability:
    return WindowResultAvailability(
        kind=WindowResultAvailabilityKind.CONCRETE,
        value_type=_value_type(nullability=nullability),
    )


def _semantic_fact(
    *,
    occurrence: WindowOccurrenceIdentity | None = None,
    expression: WindowExpr | None = None,
    result: WindowResultAvailability | None = None,
    argument_count: int = 0,
) -> WindowExpressionSemanticFact:
    actual_occurrence = occurrence or _occurrence()
    actual_expression = expression or _window_expression(
        span=actual_occurrence.span,
        argument_count=argument_count,
    )
    return WindowExpressionSemanticFact(
        occurrence=actual_occurrence,
        expression=actual_expression,
        identity=actual_expression.identity,
        result=result or _availability(),
    )


def _definition(
    *,
    kind: str = "query",
    name: str = "ranked",
    span: Span | None = None,
) -> TableDef | QueryDef:
    definition_span = span or _span()
    values: dict[str, object] = {
        "span": definition_span,
        "name": name,
        "from_clause": FromClause(span=definition_span, source_name="rows"),
        "where_clause": None,
        "group_by_clause": None,
        "select_items": (),
    }
    if kind == "table":
        return TableDef(**cast(Any, values))
    return QueryDef(**cast(Any, values))


def _location(span: Span | None = None) -> SourceLocation:
    source_span = span or _span()
    return SourceLocation(
        path=source_span.path,
        line=source_span.line,
        column=source_span.column,
        end_line=source_span.end_line,
        end_column=source_span.end_column,
    )


def _node(kind: ProjectRowDependencyNodeKind) -> ProjectRowDependencyNode:
    if kind is ProjectRowDependencyNodeKind.RELATION_INPUT:
        return ProjectRowDependencyNode(
            kind=kind,
            name="rows",
            relation_name="rows",
            source_name="rows",
        )
    if kind is ProjectRowDependencyNodeKind.LET_BINDING:
        return ProjectRowDependencyNode(
            kind=kind,
            name="local_score",
            relation_name="ranked",
            binding_name="local_score",
        )
    if kind is ProjectRowDependencyNodeKind.OUTPUT_FIELD:
        return ProjectRowDependencyNode(
            kind=kind,
            name="ranked.rn",
            relation_name="ranked",
            output_name="rn",
        )
    return ProjectRowDependencyNode(
        kind=kind,
        name="rows.score",
        relation_name="rows",
        field_name="score",
    )


def _dependency(
    *,
    global_ordinal: int,
    role_ordinal: int,
    role: WindowDependencyRole,
    kind: ProjectRowDependencyNodeKind | None = None,
) -> WindowDependencyOccurrence:
    target_kind = kind
    if target_kind is None:
        target_kind = (
            ProjectRowDependencyNodeKind.RELATION_INPUT
            if role is WindowDependencyRole.RELATION_INPUT
            else ProjectRowDependencyNodeKind.UPSTREAM_FIELD
        )
    return WindowDependencyOccurrence(
        global_ordinal=global_ordinal,
        role_ordinal=role_ordinal,
        role=role,
        target=_node(target_kind),
        location=_location(),
    )


def _project_fact(
    *,
    argument_count: int,
    occurrences: tuple[WindowDependencyOccurrence, ...],
    provenance: ProjectRowFieldProvenance | None = None,
    semantic_fact: WindowExpressionSemanticFact | None = None,
) -> WindowResultProjectFact:
    fact = semantic_fact or _semantic_fact(argument_count=argument_count)
    result_identity = WindowResultIdentity(
        definition=_definition(name=fact.occurrence.relation_name),
        output_name="rn",
        occurrence=fact.occurrence,
    )
    return WindowResultProjectFact(
        semantic_fact=fact,
        result_identity=result_identity,
        dependency_occurrences=occurrences,
        dependency_edges=deduplicate_window_dependency_edges(occurrences),
        provenance=provenance
        or ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
            location=_location(fact.occurrence.span),
        ),
    )


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


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr)
    return result.stdout.strip()


def _literal_tuple(path: Path, name: str) -> tuple[str, ...]:
    tree = ast.parse(path.read_text(), filename=path.as_posix())
    for node in tree.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    value = node.value
                    break
                if isinstance(target, ast.Tuple):
                    names = tuple(
                        item.id for item in target.elts if isinstance(item, ast.Name)
                    )
                    if name in names:
                        compound = ast.literal_eval(node.value)
                        if type(compound) is not tuple or len(compound) != len(names):
                            raise AssertionError("malformed compound tuple assignment")
                        result = compound[names.index(name)]
                        if type(result) is not tuple or any(
                            type(item) is not str for item in result
                        ):
                            raise AssertionError(
                                f"{name} must be an exact string tuple"
                            )
                        return cast(tuple[str, ...], result)
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is not None:
            result = ast.literal_eval(value)
            if type(result) is not tuple or any(
                type(item) is not str for item in result
            ):
                raise AssertionError(f"{name} must be an exact string tuple")
            return cast(tuple[str, ...], result)
    raise AssertionError(f"missing tuple {name}")


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


def test_slice6_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    assert SOURCE_PATH.is_file()
    assert PROJECT_SOURCE_PATH.is_file()
    assert MODEL_PATH.is_file()
    assert SPEC_PATH.is_file()
    assert SELF_PATH.is_file()
    assert _headings(SPEC_PATH) == ((SPEC_H1,), SPEC_H2, ())
    plan_h1, plan_h2, plan_h3 = _headings(PLAN_PATH)
    assert plan_h1 == (
        "Phase 53 — Window Functions, Generic Signature Compatibility, "
        "And Nullability Foundation",
    )
    assert plan_h2.count(PLAN_H2) == 1
    assert plan_h2[-11:] == (
        PLAN_H2,
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
    assert "Phase 53 is `ACTIVE`; Slices 1 through 5 are `COMPLETED`" in plan
    assert "Slice 6 remains `UNSTARTED` throughout Gate 2" in plan


def test_semantic_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert semantic_window_semantics.__all__ == ()
    assert tuple(WindowExpressionStage) == (WindowExpressionStage.WINDOW,)
    assert WindowExpressionStage.WINDOW.value == "WINDOW"
    expected = {
        WindowOccurrenceIdentity: (
            "source_id",
            "relation_name",
            "selected_output_ordinal",
            "span",
        ),
        WindowResultAvailability: ("kind", "value_type", "reason"),
        WindowExpressionSemanticFact: (
            "occurrence",
            "expression",
            "identity",
            "result",
            "stage",
        ),
        WindowExpressionUnsupported: (
            "occurrence",
            "expression",
            "identity",
            "reason",
        ),
    }
    for carrier, names in expected.items():
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
        assert tuple(field.name for field in fields(carrier)) == names
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )
    occurrence = _occurrence()
    with pytest.raises(FrozenInstanceError):
        setattr(occurrence, "relation_name", "other")


def test_project_private_module_enum_carrier_and_privacy_shapes_are_exact() -> None:
    assert project_window_semantics.__all__ == ()
    assert tuple((item.name, item.value) for item in WindowDependencyRole) == (
        ("RELATION_INPUT", "relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    expected = {
        WindowResultIdentity: ("definition", "output_name", "occurrence", "role"),
        WindowDependencyOccurrence: (
            "global_ordinal",
            "role_ordinal",
            "role",
            "target",
            "location",
            "target_result_role",
        ),
        WindowDependencyEdge: ("role", "target", "target_result_role"),
        WindowResultProjectFact: (
            "semantic_fact",
            "result_identity",
            "dependency_occurrences",
            "dependency_edges",
            "provenance",
        ),
    }
    for carrier, names in expected.items():
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
        assert tuple(field.name for field in fields(carrier)) == names
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(cast(Any, carrier)).parameters.values()
        )
    with pytest.raises(TypeError):
        deduplicate_window_dependency_edges(cast(Any, []))
    with pytest.raises(TypeError):
        deduplicate_window_dependency_edges(cast(Any, (object(),)))


@pytest.mark.parametrize(
    ("source_id", "relation_name", "ordinal", "span"),
    (
        ("query.pietto", "ranked", 0, _span()),
        ("query.pietto", "Ranked", 7, _span(line=10, end_line=12)),
        ("memory://unit", "r", 2, _span(path="memory://unit")),
        ("anonymous", "result", 99, _span(path=None)),
    ),
)
def test_window_occurrence_identity_valid_matrix_is_exact(
    source_id: str,
    relation_name: str,
    ordinal: int,
    span: Span,
) -> None:
    occurrence = WindowOccurrenceIdentity(
        source_id=source_id,
        relation_name=relation_name,
        selected_output_ordinal=ordinal,
        span=span,
    )
    assert (
        occurrence.source_id,
        occurrence.relation_name,
        occurrence.selected_output_ordinal,
        occurrence.span,
    ) == (source_id, relation_name, ordinal, span)


@pytest.mark.parametrize("different", (False, True))
def test_window_occurrence_identity_equality_hash_repr_and_repeatability_are_exact(
    different: bool,
) -> None:
    first = _occurrence(ordinal=1)
    second = _occurrence(ordinal=2 if different else 1)
    assert (first == second) is (not different)
    assert (hash(first) == hash(second)) is (not different)
    assert repr(_occurrence(ordinal=1)) == repr(first)


@pytest.mark.parametrize(
    "scenario",
    (
        "source_none",
        "source_int",
        "source_empty",
        "source_blank",
        "relation_none",
        "relation_int",
        "relation_empty",
        "relation_blank",
        "ordinal_bool",
        "ordinal_float",
        "ordinal_string",
        "ordinal_none",
        "ordinal_negative",
        "span_none",
        "span_object",
        "span_path_mismatch",
    ),
)
def test_window_occurrence_identity_malformed_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "source_id": "query.pietto",
        "relation_name": "ranked",
        "selected_output_ordinal": 0,
        "span": _span(),
    }
    replacements: dict[str, tuple[str, object]] = {
        "source_none": ("source_id", None),
        "source_int": ("source_id", 1),
        "source_empty": ("source_id", ""),
        "source_blank": ("source_id", "  "),
        "relation_none": ("relation_name", None),
        "relation_int": ("relation_name", 1),
        "relation_empty": ("relation_name", ""),
        "relation_blank": ("relation_name", "\t"),
        "ordinal_bool": ("selected_output_ordinal", True),
        "ordinal_float": ("selected_output_ordinal", 1.0),
        "ordinal_string": ("selected_output_ordinal", "1"),
        "ordinal_none": ("selected_output_ordinal", None),
        "ordinal_negative": ("selected_output_ordinal", -1),
        "span_none": ("span", None),
        "span_object": ("span", object()),
        "span_path_mismatch": ("span", _span(path="other.pietto")),
    }
    key, value = replacements[scenario]
    values[key] = value
    error = (
        ValueError
        if scenario
        in {
            "source_empty",
            "source_blank",
            "relation_empty",
            "relation_blank",
            "ordinal_negative",
            "span_path_mismatch",
        }
        else TypeError
    )
    with pytest.raises(error):
        WindowOccurrenceIdentity(**cast(Any, values))


@pytest.mark.parametrize(
    ("name", "nullability"),
    (
        ("Int", EffectiveNullability.NON_NULL),
        ("Text", EffectiveNullability.NULLABLE),
        ("Timestamp", EffectiveNullability.NON_NULL),
    ),
)
def test_concrete_window_result_availability_matrix_is_exact(
    name: str,
    nullability: EffectiveNullability,
) -> None:
    value_type = _value_type(name=name, nullability=nullability)
    result = WindowResultAvailability(
        kind=WindowResultAvailabilityKind.CONCRETE,
        value_type=value_type,
    )
    assert result.value_type is value_type
    assert result.reason is None


@pytest.mark.parametrize(
    "kind",
    (
        WindowResultAvailabilityKind.UNKNOWN,
        WindowResultAvailabilityKind.DEFERRED,
        WindowResultAvailabilityKind.BLOCKED,
    ),
)
def test_nonconcrete_window_result_availability_matrix_is_exact(
    kind: WindowResultAvailabilityKind,
) -> None:
    result = WindowResultAvailability(kind=kind, reason=f"private {kind.value}")
    assert result.kind is kind
    assert result.value_type is None
    assert result.reason == f"private {kind.value}"


@pytest.mark.parametrize(
    "scenario",
    (
        "kind_string",
        "concrete_missing_value",
        "concrete_unknown_kind",
        "concrete_unknown_nullability",
        "concrete_reason",
        "unknown_with_value",
        "deferred_with_value",
        "blocked_with_value",
        "unknown_missing_reason",
        "deferred_blank_reason",
        "value_wrong_type",
        "reason_wrong_type",
    ),
)
def test_window_result_availability_malformed_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "kind": WindowResultAvailabilityKind.CONCRETE,
        "value_type": _value_type(),
        "reason": None,
    }
    if scenario == "kind_string":
        values["kind"] = "concrete"
    elif scenario == "concrete_missing_value":
        values["value_type"] = None
    elif scenario == "concrete_unknown_kind":
        values["value_type"] = _value_type(kind=ValueTypeKind.UNKNOWN)
    elif scenario == "concrete_unknown_nullability":
        values["value_type"] = _value_type(nullability=EffectiveNullability.UNKNOWN)
    elif scenario == "concrete_reason":
        values["reason"] = "not allowed"
    elif scenario in {
        "unknown_with_value",
        "deferred_with_value",
        "blocked_with_value",
    }:
        values["kind"] = WindowResultAvailabilityKind(
            scenario.removesuffix("_with_value")
        )
        values["reason"] = "private"
    elif scenario == "unknown_missing_reason":
        values.update(kind=WindowResultAvailabilityKind.UNKNOWN, value_type=None)
    elif scenario == "deferred_blank_reason":
        values.update(
            kind=WindowResultAvailabilityKind.DEFERRED,
            value_type=None,
            reason=" ",
        )
    elif scenario == "value_wrong_type":
        values["value_type"] = object()
    elif scenario == "reason_wrong_type":
        values.update(
            kind=WindowResultAvailabilityKind.BLOCKED,
            value_type=None,
            reason=1,
        )
    error = (
        TypeError
        if scenario in {"kind_string", "value_wrong_type", "reason_wrong_type"}
        else ValueError
    )
    with pytest.raises(error):
        WindowResultAvailability(**cast(Any, values))


@pytest.mark.parametrize("deferred", (False, True))
def test_window_semantic_fact_has_fixed_stage_and_exact_identity(
    deferred: bool,
) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    result = (
        WindowResultAvailability(
            kind=WindowResultAvailabilityKind.DEFERRED,
            reason="binding belongs to a future slice",
        )
        if deferred
        else _availability()
    )
    fact = WindowExpressionSemanticFact(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        result=result,
    )
    assert fact.stage is WindowExpressionStage.WINDOW
    assert fact.identity == expression.identity
    assert fact.result is result


@pytest.mark.parametrize("reason", ("unknown function", "future binding"))
def test_window_semantic_unsupported_evidence_is_structural_only(
    reason: str,
) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    unsupported = WindowExpressionUnsupported(
        occurrence=occurrence,
        expression=expression,
        identity=expression.identity,
        reason=reason,
    )
    assert unsupported.reason == reason
    assert not hasattr(unsupported, "diagnostic")
    assert not hasattr(unsupported, "result")


@pytest.mark.parametrize(
    "scenario",
    (
        "occurrence_type",
        "expression_type",
        "identity_type",
        "result_type",
        "stage_type",
        "identity_mismatch",
        "span_mismatch",
        "unsupported_blank_reason",
    ),
)
def test_window_semantic_fact_mismatch_matrix_fails_closed(scenario: str) -> None:
    occurrence = _occurrence()
    expression = _window_expression(span=occurrence.span)
    values: dict[str, object] = {
        "occurrence": occurrence,
        "expression": expression,
        "identity": expression.identity,
        "result": _availability(),
        "stage": WindowExpressionStage.WINDOW,
    }
    if scenario == "occurrence_type":
        values["occurrence"] = object()
    elif scenario == "expression_type":
        values["expression"] = expression.call
    elif scenario == "identity_type":
        values["identity"] = object()
    elif scenario == "result_type":
        values["result"] = object()
    elif scenario == "stage_type":
        values["stage"] = "WINDOW"
    elif scenario == "identity_mismatch":
        values["identity"] = _identity("rank")
    elif scenario == "span_mismatch":
        values["expression"] = _window_expression(span=_span(line=7))
    else:
        with pytest.raises(ValueError):
            WindowExpressionUnsupported(
                occurrence=occurrence,
                expression=expression,
                identity=expression.identity,
                reason=" ",
            )
        return
    error = (
        ValueError if scenario in {"identity_mismatch", "span_mismatch"} else TypeError
    )
    with pytest.raises(error):
        WindowExpressionSemanticFact(**cast(Any, values))


def test_window_carriers_do_not_store_generic_or_nullability_formula_evidence() -> None:
    assert tuple(field.name for field in fields(WindowExpressionSemanticFact)) == (
        "occurrence",
        "expression",
        "identity",
        "result",
        "stage",
    )
    assert tuple(field.name for field in fields(NavigationWindowSemanticFact))[-2:] == (
        "signature_match",
        "nullability_match",
    )
    base_source = inspect.getsource(WindowExpressionSemanticFact)
    assert "signature_match" not in base_source
    assert "nullability_match" not in base_source


@pytest.mark.parametrize("scenario", ("table", "blank_alias", "wrong_occurrence"))
def test_window_result_identity_requires_explicit_alias_and_occurrence(
    scenario: str,
) -> None:
    occurrence = _occurrence()
    if scenario == "table":
        identity = WindowResultIdentity(
            definition=_definition(kind="table"),
            output_name="rn",
            occurrence=occurrence,
        )
        assert type(identity.definition) is TableDef
        assert identity.output_name == "rn"
        assert identity.occurrence is occurrence
        assert identity.role is ProjectRowResultRole.WINDOW_RESULT
        return
    if scenario == "blank_alias":
        with pytest.raises(ValueError):
            WindowResultIdentity(
                definition=_definition(),
                output_name=" ",
                occurrence=occurrence,
            )
        return
    with pytest.raises(TypeError):
        WindowResultIdentity(
            definition=_definition(),
            output_name="rn",
            occurrence=cast(Any, object()),
        )


def test_project_row_result_role_window_result_extension_is_exact() -> None:
    assert tuple((role.name, role.value) for role in ProjectRowResultRole) == (
        ("ORDINARY_ROW_VALUE", "ordinary_row_value"),
        ("GROUP_KEY", "group_key"),
        ("AGGREGATE_RESULT", "aggregate_result"),
        ("WINDOW_RESULT", "window_result"),
    )
    assert MODEL_PATH.read_text().count('WINDOW_RESULT = "window_result"') == 1
    occurrence = _occurrence()
    with pytest.raises(ValueError):
        WindowResultIdentity(
            definition=_definition(),
            output_name="rn",
            occurrence=occurrence,
            role=ProjectRowResultRole.AGGREGATE_RESULT,
        )


def test_window_dependency_role_inventory_and_phase60_frame_absence_are_exact() -> None:
    assert tuple((role.name, role.value) for role in WindowDependencyRole) == (
        ("RELATION_INPUT", "relation_input"),
        ("WINDOW_ARGUMENT", "window_argument"),
        ("WINDOW_DEFAULT", "window_default"),
        ("WINDOW_PARTITION", "window_partition"),
        ("WINDOW_ORDER", "window_order"),
    )
    assert not hasattr(WindowDependencyRole, "WINDOW_FRAME")
    assert not hasattr(WindowDependencyRole, "RESULT_ROLE")


@pytest.mark.parametrize(
    ("role", "kind"),
    (
        (
            WindowDependencyRole.RELATION_INPUT,
            ProjectRowDependencyNodeKind.RELATION_INPUT,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
        (
            WindowDependencyRole.WINDOW_DEFAULT,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            ProjectRowDependencyNodeKind.UPSTREAM_FIELD,
        ),
        (
            WindowDependencyRole.WINDOW_ORDER,
            ProjectRowDependencyNodeKind.LET_BINDING,
        ),
    ),
)
def test_window_dependency_occurrence_positive_role_target_matrix_is_exact(
    role: WindowDependencyRole,
    kind: ProjectRowDependencyNodeKind,
) -> None:
    occurrence = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=role,
        kind=kind,
    )
    edge = WindowDependencyEdge(role=role, target=occurrence.target)
    assert occurrence.role is role
    assert occurrence.target.kind is kind
    assert edge == deduplicate_window_dependency_edges((occurrence,))[0]


@pytest.mark.parametrize(
    "scenario",
    (
        "global_bool",
        "global_float",
        "global_negative",
        "role_bool",
        "role_float",
        "role_negative",
        "role_string",
        "target_object",
        "location_object",
        "relation_upstream",
        "relation_let",
        "argument_relation",
        "default_relation",
        "partition_relation",
        "order_relation",
        "argument_output",
    ),
)
def test_window_dependency_occurrence_role_payload_negative_matrix_fails_closed(
    scenario: str,
) -> None:
    values: dict[str, object] = {
        "global_ordinal": 0,
        "role_ordinal": 0,
        "role": WindowDependencyRole.WINDOW_ARGUMENT,
        "target": _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD),
        "location": _location(),
    }
    if scenario == "global_bool":
        values["global_ordinal"] = True
    elif scenario == "global_float":
        values["global_ordinal"] = 1.0
    elif scenario == "global_negative":
        values["global_ordinal"] = -1
    elif scenario == "role_bool":
        values["role_ordinal"] = True
    elif scenario == "role_float":
        values["role_ordinal"] = 1.0
    elif scenario == "role_negative":
        values["role_ordinal"] = -1
    elif scenario == "role_string":
        values["role"] = "window_argument"
    elif scenario == "target_object":
        values["target"] = object()
    elif scenario == "location_object":
        values["location"] = object()
    elif scenario == "relation_upstream":
        values.update(
            role=WindowDependencyRole.RELATION_INPUT,
            target=_node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD),
        )
    elif scenario == "relation_let":
        values.update(
            role=WindowDependencyRole.RELATION_INPUT,
            target=_node(ProjectRowDependencyNodeKind.LET_BINDING),
        )
    elif scenario in {
        "argument_relation",
        "default_relation",
        "partition_relation",
        "order_relation",
    }:
        role_name = scenario.removesuffix("_relation")
        values.update(
            role={
                "argument": WindowDependencyRole.WINDOW_ARGUMENT,
                "default": WindowDependencyRole.WINDOW_DEFAULT,
                "partition": WindowDependencyRole.WINDOW_PARTITION,
                "order": WindowDependencyRole.WINDOW_ORDER,
            }[role_name],
            target=_node(ProjectRowDependencyNodeKind.RELATION_INPUT),
        )
    else:
        values["target"] = _node(ProjectRowDependencyNodeKind.OUTPUT_FIELD)
    error = (
        TypeError
        if scenario
        in {
            "global_bool",
            "global_float",
            "role_bool",
            "role_float",
            "role_string",
            "target_object",
            "location_object",
        }
        else ValueError
    )
    with pytest.raises(error):
        WindowDependencyOccurrence(**cast(Any, values))


@pytest.mark.parametrize(
    "scenario",
    (
        "valid",
        "global_starts_one",
        "global_gap",
        "role_starts_one",
        "role_duplicate",
        "role_block_reverse",
    ),
)
def test_window_dependency_global_and_role_local_ordering_matrix_is_exact(
    scenario: str,
) -> None:
    first = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ARGUMENT,
    )
    second = _dependency(
        global_ordinal=1,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_PARTITION,
    )
    occurrences = (first, second)
    if scenario == "global_starts_one":
        occurrences = (
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "global_gap":
        occurrences = (
            first,
            _dependency(
                global_ordinal=2,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
        )
    elif scenario == "role_starts_one":
        occurrences = (
            _dependency(
                global_ordinal=0,
                role_ordinal=1,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "role_duplicate":
        occurrences = (
            first,
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    elif scenario == "role_block_reverse":
        occurrences = (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ORDER,
            ),
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
        )
    if scenario == "valid":
        fact = _project_fact(argument_count=1, occurrences=occurrences)
        assert fact.dependency_occurrences == occurrences
        return
    with pytest.raises(ValueError):
        _project_fact(argument_count=1, occurrences=occurrences)


@pytest.mark.parametrize("repeat_count", (1, 2, 3, 4, 5))
def test_repeated_dependency_occurrences_are_preserved_and_edges_first_deduped(
    repeat_count: int,
) -> None:
    target = _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD)
    occurrences = tuple(
        WindowDependencyOccurrence(
            global_ordinal=index,
            role_ordinal=index,
            role=WindowDependencyRole.WINDOW_ARGUMENT,
            target=target,
            location=_location(),
        )
        for index in range(repeat_count)
    )
    edges = deduplicate_window_dependency_edges(occurrences)
    assert len(occurrences) == repeat_count
    assert edges == (
        WindowDependencyEdge(
            role=WindowDependencyRole.WINDOW_ARGUMENT,
            target=target,
        ),
    )
    fact = _project_fact(argument_count=1, occurrences=occurrences)
    assert fact.dependency_edges == edges


@pytest.mark.parametrize(
    ("first_role", "second_role"),
    (
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_DEFAULT,
        ),
        (
            WindowDependencyRole.WINDOW_ARGUMENT,
            WindowDependencyRole.WINDOW_PARTITION,
        ),
        (
            WindowDependencyRole.WINDOW_PARTITION,
            WindowDependencyRole.WINDOW_ORDER,
        ),
    ),
)
def test_same_target_across_dependency_roles_remains_distinct(
    first_role: WindowDependencyRole,
    second_role: WindowDependencyRole,
) -> None:
    target = _node(ProjectRowDependencyNodeKind.UPSTREAM_FIELD)
    occurrences = (
        WindowDependencyOccurrence(
            global_ordinal=0,
            role_ordinal=0,
            role=first_role,
            target=target,
            location=_location(),
        ),
        WindowDependencyOccurrence(
            global_ordinal=1,
            role_ordinal=0,
            role=second_role,
            target=target,
            location=_location(),
        ),
    )
    edges = deduplicate_window_dependency_edges(occurrences)
    assert tuple(edge.role for edge in edges) == (first_role, second_role)
    assert edges[0].target == edges[1].target


@pytest.mark.parametrize(
    "scenario",
    ("relation_only", "relation_partition_order", "missing_relation", "two_relations"),
)
def test_zero_argument_relation_input_readiness_and_failure_matrix_is_exact(
    scenario: str,
) -> None:
    relation = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.RELATION_INPUT,
    )
    occurrences: tuple[WindowDependencyOccurrence, ...] = (relation,)
    if scenario == "relation_partition_order":
        occurrences = (
            relation,
            _dependency(
                global_ordinal=1,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_PARTITION,
            ),
            _dependency(
                global_ordinal=2,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ORDER,
            ),
        )
    elif scenario == "missing_relation":
        occurrences = ()
    elif scenario == "two_relations":
        occurrences = (
            relation,
            _dependency(
                global_ordinal=1,
                role_ordinal=1,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
    if scenario.startswith("relation_"):
        fact = _project_fact(argument_count=0, occurrences=occurrences)
        assert (
            sum(
                item.role is WindowDependencyRole.RELATION_INPUT
                for item in fact.dependency_occurrences
            )
            == 1
        )
        return
    with pytest.raises(ValueError):
        _project_fact(argument_count=0, occurrences=occurrences)


@pytest.mark.parametrize(
    "role",
    (
        WindowDependencyRole.WINDOW_ARGUMENT,
        WindowDependencyRole.WINDOW_DEFAULT,
        WindowDependencyRole.WINDOW_PARTITION,
        WindowDependencyRole.WINDOW_ORDER,
    ),
)
def test_same_select_and_nested_window_dependencies_are_nonrepresentable(
    role: WindowDependencyRole,
) -> None:
    with pytest.raises(ValueError):
        WindowDependencyOccurrence(
            global_ordinal=0,
            role_ordinal=0,
            role=role,
            target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
            location=_location(),
        )
    with pytest.raises(ValueError):
        WindowDependencyEdge(
            role=role,
            target=_node(ProjectRowDependencyNodeKind.OUTPUT_FIELD),
        )


@pytest.mark.parametrize("argument_count", (0, 1, 3))
def test_window_result_uses_existing_derived_expression_provenance(
    argument_count: int,
) -> None:
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if argument_count == 0
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    fact = _project_fact(argument_count=argument_count, occurrences=occurrences)
    assert fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    assert fact.provenance.location == _location(fact.semantic_fact.occurrence.span)
    assert not hasattr(ProjectRowFieldProvenanceKind, "WINDOW_RESULT")


@pytest.mark.parametrize(
    "scenario",
    (
        "wrong_type",
        "wrong_kind",
        "missing_location",
        "wrong_path",
        "wrong_line",
        "wrong_symbol_type",
    ),
)
def test_window_result_provenance_mismatch_matrix_fails_closed(scenario: str) -> None:
    occurrence = _dependency(
        global_ordinal=0,
        role_ordinal=0,
        role=WindowDependencyRole.WINDOW_ARGUMENT,
    )
    if scenario == "wrong_type":
        with pytest.raises(TypeError):
            _project_fact(
                argument_count=1,
                occurrences=(occurrence,),
                provenance=cast(Any, object()),
            )
        return
    location = _location()
    kind = ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
    symbol: object | None = None
    if scenario == "wrong_kind":
        kind = ProjectRowFieldProvenanceKind.AGGREGATE
    elif scenario == "missing_location":
        location = cast(Any, None)
    elif scenario == "wrong_path":
        location = SourceLocation(
            path="other.pietto", line=3, column=9, end_line=3, end_column=43
        )
    elif scenario == "wrong_line":
        location = SourceLocation(
            path="query.pietto", line=4, column=9, end_line=4, end_column=43
        )
    elif scenario == "wrong_symbol_type":
        symbol = object()
    provenance = ProjectRowFieldProvenance(
        kind=kind,
        symbol=cast(Any, symbol),
        location=location,
    )
    error = TypeError if scenario == "wrong_symbol_type" else ValueError
    with pytest.raises(error):
        _project_fact(
            argument_count=1,
            occurrences=(occurrence,),
            provenance=provenance,
        )


@pytest.mark.parametrize("argument_count", (0, 1))
def test_window_result_project_fact_is_frozen_hashable_and_repeatable(
    argument_count: int,
) -> None:
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if argument_count == 0
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    first = _project_fact(argument_count=argument_count, occurrences=occurrences)
    second = _project_fact(argument_count=argument_count, occurrences=occurrences)
    assert first == second
    assert hash(first) == hash(second)
    assert repr(first) == repr(second)
    with pytest.raises(FrozenInstanceError):
        setattr(first, "dependency_edges", ())


@pytest.mark.parametrize(
    "scenario",
    ("ranking_concrete", "navigation_nullable", "slice12_unknown", "slice12_deferred"),
)
def test_slice7_and_slice12_construction_readiness_matrix_is_exact(
    scenario: str,
) -> None:
    zero_argument = scenario == "ranking_concrete"
    result = _availability(
        nullability=(
            EffectiveNullability.NULLABLE
            if scenario == "navigation_nullable"
            else EffectiveNullability.NON_NULL
        )
    )
    if scenario == "slice12_unknown":
        result = WindowResultAvailability(
            kind=WindowResultAvailabilityKind.UNKNOWN,
            reason="future generic binding unavailable",
        )
    elif scenario == "slice12_deferred":
        result = WindowResultAvailability(
            kind=WindowResultAvailabilityKind.DEFERRED,
            reason="future nullability evaluation unavailable",
        )
    semantic_fact = _semantic_fact(
        argument_count=0 if zero_argument else 1,
        result=result,
    )
    occurrences = (
        (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.RELATION_INPUT,
            ),
        )
        if zero_argument
        else (
            _dependency(
                global_ordinal=0,
                role_ordinal=0,
                role=WindowDependencyRole.WINDOW_ARGUMENT,
            ),
        )
    )
    fact = _project_fact(
        argument_count=0 if zero_argument else 1,
        occurrences=occurrences,
        semantic_fact=semantic_fact,
    )
    assert fact.semantic_fact.result is result


@pytest.mark.parametrize(
    ("relative", "expected_sha256"),
    ANALYZER_CATALOG_DIAGNOSTIC_LOCKS,
)
def test_current_analyzer_catalog_and_diagnostic_nonintegration_is_exact(
    relative: str,
    expected_sha256: str,
) -> None:
    path = REPO_ROOT / relative
    source = path.read_text()
    assert _sha256(path) == expected_sha256
    if relative == "src/pietto/semantic/expressions.py":
        assert "semantic.window_semantics" in source
        assert "WindowExpressionAnalysis" in source
        assert "WindowResultAvailabilityKind" in source
        assert "analyze_window_expression(" in source
        window_analysis = (
            REPO_ROOT / "src/pietto/semantic/window_analysis.py"
        ).read_text()
        assert "def analyze_row_number_window_expression(" in window_analysis
        assert "WindowExpressionSemanticFact" in window_analysis
        assert "WindowExpressionUnsupported" in window_analysis
    else:
        assert "semantic.window_semantics" not in source
        assert "WindowExpressionSemanticFact" not in source
        assert "WindowExpressionUnsupported" not in source


@pytest.mark.parametrize(
    ("relative", "expected_sha256"),
    (
        ("src/pietto/_project/model.py", FINAL_MODEL_SHA256),
        (
            "src/pietto/_project/check.py",
            "6f2f2805249cc86a8ff3510a03abc702d2a029186cf16b50cabd11dbaf1da9e1",
        ),
        (
            "src/pietto/_project/json_v2.py",
            "74251e684a22de4dcdc7e1822a6843ca89cbdfa7e136a046676d848b57953bd5",
        ),
        (
            "src/pietto/_project/__init__.py",
            "d6aacd3fa60162b7c86efc37e052790a48b87462ffe46467f945a55b0d3f4169",
        ),
    ),
)
def test_project_model_checker_and_serializers_have_no_window_population(
    relative: str,
    expected_sha256: str,
) -> None:
    path = REPO_ROOT / relative
    source = path.read_text()
    assert _sha256(path) == expected_sha256
    if relative == "src/pietto/_project/model.py":
        assert "WindowResultProjectFact" in source
        assert "relation_window_result_facts" in source
        assert "_validate_project_window_result_facts(" in source
        assert "build_window_result_project_fact(" not in source
    else:
        assert "WindowResultProjectFact" not in source
        assert "relation_window_result_facts" not in source
        assert "window_semantics" not in source
    assert not hasattr(project_package, "WindowResultProjectFact")


@pytest.mark.parametrize(
    ("relative", "expected_sha256"),
    GRAMMAR_AST_GENERIC_NULLABILITY_LOCKS,
)
def test_grammar_ast_parser_identity_generic_and_nullability_hashes_are_locked(
    relative: str,
    expected_sha256: str,
) -> None:
    path = REPO_ROOT / relative
    if path.is_dir():
        tracked = tuple(
            REPO_ROOT / item for item in _git("ls-files", relative).splitlines()
        )
        assert len(tracked) == 8
        assert _digest(tracked) == expected_sha256
        return
    assert _sha256(path) == expected_sha256


@pytest.mark.parametrize(
    ("relative", "expected_sha256"),
    IR_SQL_CAPABILITY_PUBLIC_LOCKS,
)
def test_ir_sql_capability_public_runtime_and_package_surfaces_are_locked(
    relative: str,
    expected_sha256: str,
) -> None:
    path = REPO_ROOT / relative
    if path.is_dir():
        tracked = tuple(
            REPO_ROOT / item for item in _git("ls-files", relative).splitlines()
        )
        assert _digest(tracked) == expected_sha256
    else:
        assert _sha256(path) == expected_sha256
    assert not hasattr(pietto, "WindowExpressionSemanticFact")
    assert not hasattr(semantic_package, "WindowExpressionSemanticFact")
    assert not hasattr(project_package, "WindowResultProjectFact")


def test_slice6_spec_heading_scope_and_no_h3_contract_is_exact() -> None:
    assert _headings(SPEC_PATH) == ((SPEC_H1,), SPEC_H2, ())
    spec = SPEC_PATH.read_text()
    assert spec.count("# Phase 53 Slice 6 ") == 1
    assert spec.count("\n## ") == 26
    assert "\n### " not in spec
    assert "WINDOW_FRAME" in spec
    assert "same-select" in spec
    assert "nested-window" in spec


def test_reader_hash_inventory_and_nested_closure_is_exact() -> None:
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
    project_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if Path(path).parent.as_posix() == "src/pietto/_project"
        and path.endswith(".py")
    )
    assert (
        len(compiler_paths),
        len(semantic_paths),
        len(phase15_paths),
        len(project_paths),
    ) == (103, 36, 33, 28)
    assert _digest(tuple(compiler_paths)) == FINAL_COMPILER_DIGEST
    assert _digest(semantic_paths) == FINAL_SEMANTIC_DIGEST
    assert _digest(phase15_paths) == FINAL_PHASE15_DIGEST
    assert _digest(project_paths) == FINAL_PROJECT_DIGEST
    assert _sha256(SOURCE_PATH) == FINAL_SOURCE_SHA256
    assert _sha256(PROJECT_SOURCE_PATH) == FINAL_PROJECT_SOURCE_SHA256
    assert _sha256(MODEL_PATH) == FINAL_MODEL_SHA256
    assert _sha256(SPEC_PATH) == FINAL_SPEC_SHA256
    assert _sha256(PLAN_PATH) == FINAL_PLAN_SHA256

    added = _literal_tuple(GENERIC_TEST_PATH, "ADDED_PATHS")
    modified = _literal_tuple(GENERIC_TEST_PATH, "MODIFIED_PATHS")
    assert added == ADDED_PATHS
    assert len(modified) == 24
    assert modified[-16:-2] == (
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
    )
    assert modified[-2:] == (
        "tests/test_phase53_window_spec_function_identity_ast_contract.py",
        "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    )
    assert set(added).isdisjoint(modified)


def test_slice6_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_product_repair1_gate2_is_active():
        return
    tracked = frozenset(_git("diff", "--name-only").splitlines()) - {""}
    untracked = frozenset(
        _git("ls-files", "--others", "--exclude-standard").splitlines()
    ) - {""}
    cached = frozenset(_git("diff", "--cached", "--name-only").splitlines()) - {""}
    assert cached == frozenset()
    head = _git("rev-parse", "HEAD")
    branch_result = subprocess.run(
        ("git", "symbolic-ref", "--quiet", "--short", "HEAD"),
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    branch = branch_result.stdout.strip() if branch_result.returncode == 0 else ""
    if not tracked and not untracked:
        assert branch in {"", "main"}
        return
    if head in {
        "d8a5e9ab3de70ce30575513c73560c86430eca63",
        "15bae172ee151e370fe59d3bf909d735aee6aa90",
        "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
        "c44a4271d9592cb393d2232f127a59d8466cc60a",
        "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
        "027b33cafcfd58916a89e299487dad38d24ade6c",
        "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
    }:
        expected_modified, expected_added = _phase54_slice2_paths()
        expected_base = head
    else:
        expected_modified = frozenset(
            _literal_tuple(GENERIC_TEST_PATH, "MODIFIED_PATHS")
        )
        expected_added = frozenset(ADDED_PATHS)
        expected_base = BASE_HEAD
    assert branch == "main"
    assert head == expected_base
    assert tracked == expected_modified
    assert untracked == expected_added
    assert _git("rev-parse", "refs/heads/main") == expected_base
    assert _git("rev-parse", "refs/remotes/origin/main") == expected_base


def test_test_inventory_focused_selector_and_dirty_overlay_are_exact() -> None:
    repository_paths = _all_repository_paths()
    python_paths = tuple(path for path in repository_paths if path.endswith(".py"))
    markdown_paths = tuple(path for path in repository_paths if path.endswith(".md"))
    test_paths = tuple(
        path for path in repository_paths if path.startswith("tests/test_")
    )
    top_level_functions = sum(
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in ast.parse((REPO_ROOT / path).read_text()).body
        )
        for path in test_paths
    )
    assert (
        len(repository_paths),
        len(python_paths),
        len(markdown_paths),
        len(test_paths),
        top_level_functions,
    ) == (915, 563, 256, 459, 5127)
    assert len(TEST_FUNCTIONS) == len(TEST_ITEM_COUNTS) == 36
    assert sum(TEST_ITEM_COUNTS) == 156
    assert 10599 + 185 == 10784

    focused = _literal_tuple(GENERIC_TEST_PATH, "FOCUSED_OPERANDS")
    overlay = _literal_tuple(GENERIC_TEST_PATH, "DIRTY_OVERLAY")
    focused_payload = ("\n".join(focused) + "\n").encode()
    overlay_payload = ("\n".join(overlay) + "\n").encode()
    assert len(focused) == 134
    assert len({operand.split("::", 1)[0] for operand in focused}) == 80
    assert sum("::" not in operand for operand in focused) == 14
    assert sum("::" in operand for operand in focused) == 120
    assert (len(focused_payload), hashlib.sha256(focused_payload).hexdigest()) == (
        15130,
        "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429",
    )
    assert len(overlay) == 185
    assert (
        len(
            {
                operand.removeprefix("--deselect=").split("::", 1)[0]
                for operand in overlay
            }
        )
        == 137
    )
    assert (len(overlay_payload), hashlib.sha256(overlay_payload).hexdigest()) == (
        23628,
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
    )


def test_validation_gate3_and_no_behavior_boundaries_are_locked() -> None:
    changed = frozenset(_git("diff", "--name-only").splitlines()) - {""}
    untracked = frozenset(
        _git("ls-files", "--others", "--exclude-standard").splitlines()
    ) - {""}
    allowed = frozenset(
        (*ADDED_PATHS, *_literal_tuple(GENERIC_TEST_PATH, "MODIFIED_PATHS"))
    )
    repair_state = changed == CI_REPAIR_MODIFIED_PATHS and not untracked
    phase54_modified, phase54_added = _phase54_slice2_paths()
    phase54_state = (
        _phase54_product_repair1_gate2_is_active()
        or changed == phase54_modified
        and untracked == phase54_added
        and _git("rev-parse", "HEAD")
        in {
            "d8a5e9ab3de70ce30575513c73560c86430eca63",
            "15bae172ee151e370fe59d3bf909d735aee6aa90",
            "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01",
            "c44a4271d9592cb393d2232f127a59d8466cc60a",
            "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16",
            "027b33cafcfd58916a89e299487dad38d24ade6c",
            "0ceb9a476e6592714cdc76845949ba0ae5123eb5",
        }
    )
    assert (
        (not changed and not untracked)
        or changed | untracked == allowed
        or repair_state
        or phase54_state
    )
    if repair_state:
        assert _git("diff", "--cached", "--name-only") == ""
        assert _git("branch", "--show-current") == "main"
        assert (
            tuple(
                _git("rev-parse", reference)
                for reference in ("HEAD", "main", "origin/main")
            )
            == (CI_REPAIR_BASE_HEAD_SHA,) * 3
        )
    assert _sha256(REPO_ROOT / "uv.lock") == (
        "a7d9125995e98a8a74d3664ceae7801cc1f4cce74ec323933da67838be199cea"
    )
    assert _sha256(REPO_ROOT / ".github/workflows/ci.yml") == (
        "4db1c9a49b0af230bae3f088bf84524e210e0afcd6a87250322e5036a69e8d94"
    )
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    plan = PLAN_PATH.read_text()
    spec = SPEC_PATH.read_text()
    assert 'version = "0.1.0"' in pyproject
    assert "Gate 3" in plan
    assert "Slice 6 remains `UNSTARTED` throughout Gate 2" in plan
    assert "Slice 6 adds no analyzer branch, catalog entry, capability domain" in spec
    assert "No field or mapping is added to `ProjectSemanticModel`" in spec


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
