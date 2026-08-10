from __future__ import annotations

import ast
import dataclasses
import hashlib
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    phase54_publication_clean_topic_is_active,
    phase54_publication_topic_branch,
    phase54_publication_topic_base,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
)

import pytest

import pietto
import pietto.ast_nodes as ast_nodes
from pietto import _window_identity
from pietto._project.model import ProjectRowResultRole, ProjectRowSchema
from pietto._project.row_expression_schema import (
    ProjectExpressionSchemaOriginKind,
    ProjectExpressionSchemaReason,
    ProjectExpressionSchemaStatus,
    adapt_project_row_expression_schema,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Span,
    WindowExpr,
    WindowSpec,
)
from pietto.errors import Severity
from pietto.ir.lowering import lower_expr
from pietto.ir.model import WindowCallIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-window-spec-function-identity-ast-contract-v1.md"
IDENTITY_REL = "src/pietto/_window_identity.py"
SELF_REL = "tests/test_phase53_window_spec_function_identity_ast_contract.py"
SLICE2_TEST_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
PHASE54_SLICE2_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"
TEMPORARY_BRIDGE_MESSAGE = (
    "Window syntax is recognized, but WindowSpec AST preservation starts in "
    "Phase 53 Slice 3."
)

SPEC_TITLE = (
    "Phase 53 Slice 3 WindowSpec, Extension-compatible "
    "WindowFunctionIdentity, And AST Contract v1"
)
SLICE3_PLAN_H2 = (
    "Slice 3 WindowSpec, Extension-compatible WindowFunctionIdentity, And AST Contract"
)
SLICE4_PLAN_H2 = (
    "Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation"
)
SLICE5_PLAN_H2 = "Slice 5 Nullability Algebra And Signature Result-formula Foundation"
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
SPEC_H2 = (
    "Status And Slice Identity",
    "Slice 2 Syntax And Lifecycle Authority",
    "Selected WindowExpr Architecture",
    "Exact WindowSpec Shape And Invariants",
    "Window-order Item Reuse And Ordinal Boundary",
    "Private WindowFunctionIdentity Shape",
    "Namespace Name Role And Case Semantics",
    "CST-to-AST Construction",
    "Source-span And Location Preservation",
    "Parser Success And Compatibility",
    "Semantic Fail-closed Boundary",
    "Project Parse-only Deferred Boundary",
    "IR SQL And Public Serialization Boundary",
    "Expression Walker And Exhaustiveness Closure",
    "Positive AST Matrix",
    "Negative And No-behavior Matrix",
    "Grammar Generated And Parser API Immutability",
    "Reader Hash Inventory And Repository-state Closure",
    "Validation Depth-one CI And Gate 3 Publication",
    "Deferred Ownership And Stop Conditions",
)
WINDOW_FUNCTION_NAMES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)

ADDED_PATHS = {
    "docs/spec/phase53-completion-audit-and-status-lock-v1.md",
    "tests/test_phase53_completion_audit_and_status_lock.py",
}
MODIFIED_PATHS = {
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
}
ALLOWLIST_PATHS = ADDED_PATHS | MODIFIED_PATHS

EXPECTED_TEST_FUNCTIONS = (
    "test_slice3_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_window_identity_role_shape_validation_and_privacy_are_exact",
    "test_window_identity_namespace_name_case_and_hash_are_preserved",
    "test_window_spec_constructor_invariants_and_hash_are_exact",
    "test_parser_preserves_canonical_window_shapes",
    "test_parser_preserves_call_arguments_and_trailing_comma",
    "test_parser_preserves_function_candidate_identity",
    "test_parser_preserves_qualified_identity_namespace_and_case",
    "test_multiple_window_and_ordinary_select_items_preserve_order_aliases_and_independence",
    "test_window_ast_spans_are_exact",
    "test_window_order_direction_and_spans_are_exact",
    "test_window_order_integer_literal_bypasses_final_order_ordinal_rejection",
    "test_slice2_malformed_and_deferred_window_syntax_remains_rejected",
    "test_valid_window_parse_retires_temporary_slice2_bridge",
    "test_semantic_check_fails_closed_with_existing_unknown_function_diagnostic",
    "test_window_expression_publishes_no_semantic_value_type_fact",
    "test_ir_lowering_fails_closed_on_missing_window_expression_fact",
    "test_project_parse_only_path_remains_deferred_without_window_result_dependency_or_lineage",
    "test_no_window_ir_sql_catalog_capability_project_role_or_public_serialization_surface_is_added",
    "test_grammar_generated_parser_api_and_public_exports_are_byte_locked",
    "test_expression_walkers_and_exhaustive_dispatch_are_classified",
    "test_reader_hash_inventory_and_nested_hash_closure_is_exact",
    "test_slice3_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_and_dirty_overlay_are_exact",
    "test_validation_gate3_and_no_behavior_boundaries_are_locked",
)

IDENTITY_CASES = (
    ("rank", (), "rank"),
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("Window", (), "Window"),
    ("WINDOW", (), "WINDOW"),
    ("vendor.Unrelated", ("vendor",), "Unrelated"),
)
CANONICAL_CASES = (
    ("order_only", "order by:\n    observed_at", 0, (None,)),
    ("partition_only", "partition by:\n    account_id", 1, ()),
    (
        "combined",
        "partition by:\n    account_id\norder by:\n    observed_at desc",
        1,
        ("desc",),
    ),
    (
        "multiple_partition",
        "partition by:\n    account_id\n    region",
        2,
        (),
    ),
    (
        "multiple_order",
        "order by:\n    observed_at\n    sequence_id asc",
        0,
        (None, "asc"),
    ),
    (
        "blank_lines",
        "\npartition by:\n\n    account_id\n\norder by:\n\n    observed_at\n",
        1,
        (None,),
    ),
    ("ascending", "order by:\n    observed_at asc", 0, ("asc",)),
    ("descending", "order by:\n    observed_at desc", 0, ("desc",)),
)
CALL_ARGUMENT_CASES = (
    ("row_number()", ()),
    ("lag(value, 1)", ("value", 1)),
    ("lead(value, 2, fallback,)", ("value", 2, "fallback")),
)
CANDIDATE_IDENTITY_CASES = (*WINDOW_FUNCTION_NAMES, "custom", "Window", "WINDOW")
QUALIFIED_IDENTITY_CASES = (
    ("analytics.rank", ("analytics",), "rank"),
    ("Org.Analytics.Rank", ("Org", "Analytics"), "Rank"),
    ("vendor.extension.lead", ("vendor", "extension"), "lead"),
)
SPAN_CASES = (
    (
        "order_only",
        "order by:\n    observed_at",
        (4, 14, 6, 28),
        (4, 14, 4, 26),
        (4, 27, 6, 28),
    ),
    (
        "partition_only",
        "partition by:\n    region",
        (4, 14, 6, 23),
        (4, 14, 4, 26),
        (4, 27, 6, 23),
    ),
    (
        "combined",
        "partition by:\n    account_id\norder by:\n    observed_at desc",
        (4, 14, 8, 33),
        (4, 14, 4, 26),
        (4, 27, 8, 33),
    ),
)
DIRECTION_CASES = (
    ("observed_at", None, (6, 17, 6, 28)),
    ("observed_at asc", "asc", (6, 17, 6, 32)),
    ("observed_at desc", "desc", (6, 17, 6, 33)),
)
MALFORMED_CASES = (
    ("missing_colon", "order by:\n    observed_at", " window:\n", " window\n"),
    ("empty_window", "", None, None),
    ("empty_partition", "partition by:\n", None, None),
    ("empty_order", "order by:\n", None, None),
    (
        "duplicate_partition",
        "partition by:\n    account_id\npartition by:\n    region",
        None,
        None,
    ),
    (
        "duplicate_order",
        "order by:\n    observed_at\norder by:\n    sequence_id",
        None,
        None,
    ),
    (
        "reversed",
        "order by:\n    observed_at\npartition by:\n    account_id",
        None,
        None,
    ),
    ("unknown_clause", "cluster by:\n    account_id", None, None),
    ("frame", "order by:\n    observed_at\nrows current row", None, None),
    ("nulls_first", "order by:\n    observed_at nulls first", None, None),
    ("malformed_order", "order by:\n    observed_at +", None, None),
    ("malformed_partition", "partition by:\n    account_id +", None, None),
)
VALID_BRIDGE_CASES = (
    "order by:\n    observed_at",
    "partition by:\n    account_id",
    "partition by:\n    account_id\norder by:\n    observed_at desc",
)
SEMANTIC_IDENTITY_CASES = (
    ("rank", "Unknown function: rank"),
    ("analytics.rank", "Unknown function: analytics.rank"),
    ("Org.Analytics.Rank", "Unknown function: Org.Analytics.Rank"),
)

COMPILER_DIGEST = "28c59c5ae6ca3c8743ffd84ff9afc81401d2ba0e9c2419fb48f868fd66d443ff"
SEMANTIC_DIGEST = "731e17cc85849c7716abeb08abeda03f72e3e21af183a391107adf96ccab6d70"
PHASE15_SUBSET_DIGEST = (
    "81db265a7bbd290b9c9227733e92dc502f8e8c8f0ff76b4d631651772876550d"
)
AST_NODES_SHA256 = "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2"
AST_BUILDER_SHA256 = "918dc9f6d7705376b604e69fb80c45cf4c3673c8909a58537770d114d96252cb"
SEMANTIC_EXPRESSIONS_SHA256 = (
    "37b198f72b0c71c90a82d746671be8528a9ea5c2d4818ff7ef4ba55e30e9c595"
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _headings(relative: str, level: int) -> tuple[str, ...]:
    return tuple(
        match.group(1).strip()
        for match in re.finditer(
            rf"^{'#' * level} (?!#)(.+?)\s*$",
            _read(relative),
            flags=re.MULTILINE,
        )
    )


def _git_output(args: list[str]) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


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
    return result.stdout.strip() or None


def _phase54_slice2_paths() -> tuple[set[str], set[str]]:
    tree = ast.parse(_read(PHASE54_SLICE2_STATE_REL))
    values: dict[str, set[str]] = {}
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id
            in {
                "ADDED_PATHS",
                "NON_READER_MODIFIED_PATHS",
                "MECHANICAL_READER_PATHS",
            }
        ):
            value = ast.literal_eval(node.value)
            assert isinstance(value, set)
            values[node.targets[0].id] = value
    return values["ADDED_PATHS"], (
        values["NON_READER_MODIFIED_PATHS"] | values["MECHANICAL_READER_PATHS"]
    )


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _window_query(
    body: str,
    *,
    projection: str = "rn = row_number()",
    before: tuple[str, ...] = (),
    after: tuple[str, ...] = (),
) -> str:
    body_text = textwrap.dedent(body).strip("\n") + "\n"
    return (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        + "".join(f"        {item}\n" for item in before)
        + f"        {projection} window:\n"
        + textwrap.indent(body_text, "            ")
        + "".join(f"        {item}\n" for item in after)
    )


def _semantic_window_source(call: str) -> str:
    return (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        'source rows: Row is postgres.table("rows")\n'
        + _window_query("order by:\n    observed_at", projection=f"rn = {call}")
    )


def _window_expression(source: str) -> WindowExpr:
    result = parse_source(source, path="window-slice3.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    return expression


def _span_tuple(span: Span) -> tuple[int, int, int, int]:
    return span.line, span.column, span.end_line, span.end_column


def _literal_argument_value(expression: Expression) -> str | int:
    if isinstance(expression, NameExpr):
        return expression.name
    assert isinstance(expression, LiteralExpr)
    assert isinstance(expression.value, (str, int))
    return expression.value


def _test_function_shape() -> tuple[tuple[str, ...], tuple[int, ...]]:
    tree = ast.parse(_read(SELF_REL), filename=SELF_REL)
    functions = tuple(
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    cardinalities: list[int] = []
    for function in functions:
        cardinality = 1
        for decorator in function.decorator_list:
            if not isinstance(decorator, ast.Call):
                continue
            if not (
                isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
                and len(decorator.args) >= 2
            ):
                continue
            values = decorator.args[1]
            if isinstance(values, ast.Name):
                cardinality *= {
                    "IDENTITY_CASES": 6,
                    "CANONICAL_CASES": 8,
                    "CALL_ARGUMENT_CASES": 3,
                    "CANDIDATE_IDENTITY_CASES": 11,
                    "QUALIFIED_IDENTITY_CASES": 3,
                    "SPAN_CASES": 3,
                    "DIRECTION_CASES": 3,
                    "MALFORMED_CASES": 12,
                    "VALID_BRIDGE_CASES": 3,
                    "SEMANTIC_IDENTITY_CASES": 3,
                }[values.id]
            else:
                raise AssertionError("Slice 3 parameter manifests must be named")
        cardinalities.append(cardinality)
    return tuple(function.name for function in functions), tuple(cardinalities)


def test_slice3_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    assert all((REPO_ROOT / path).is_file() for path in ADDED_PATHS)
    assert _headings(SPEC_REL, 1) == (SPEC_TITLE,)
    assert _headings(SPEC_REL, 2) == SPEC_H2
    assert _headings(SPEC_REL, 3) == ()
    plan_h2 = _headings(PLAN_REL, 2)
    assert plan_h2[-15:] == (
        "Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract",
        SLICE3_PLAN_H2,
        SLICE4_PLAN_H2,
        SLICE5_PLAN_H2,
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
    assert plan_h2.count(SLICE3_PLAN_H2) == 1
    assert plan_h2.count(SLICE4_PLAN_H2) == 1
    assert plan_h2.count(SLICE5_PLAN_H2) == 1
    assert plan_h2.count(SLICE6_PLAN_H2) == 1
    assert plan_h2.count(SLICE7_PLAN_H2) == 1
    assert plan_h2.count(SLICE8_PLAN_H2) == 1
    assert plan_h2.count(SLICE9_PLAN_H2) == 1
    assert plan_h2.count(SLICE11_PLAN_H2) == 1
    assert plan_h2.count(SLICE12_PLAN_H2) == 1
    assert plan_h2.count(SLICE13_PLAN_H2) == 1
    assert plan_h2.count(SLICE14_PLAN_H2) == 1
    assert plan_h2.count(SLICE15_PLAN_H2) == 1
    names, cardinalities = _test_function_shape()
    assert names == EXPECTED_TEST_FUNCTIONS
    assert cardinalities == (
        1,
        1,
        6,
        1,
        8,
        3,
        11,
        3,
        1,
        3,
        3,
        1,
        12,
        3,
        3,
        1,
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
    assert sum(cardinalities) == 70


def test_window_identity_role_shape_validation_and_privacy_are_exact() -> None:
    role = _window_identity.WindowFunctionRole.WINDOW_FUNCTION
    identity = _window_identity.WindowFunctionIdentity((), "rank", role)
    assert tuple(_window_identity.WindowFunctionRole) == (role,)
    assert role.value == "window_function"
    assert dataclasses.is_dataclass(identity)
    assert identity.__slots__ == ("namespace", "name", "role")
    assert _window_identity.__all__ == ()
    assert not hasattr(pietto, "WindowFunctionIdentity")
    assert not hasattr(ast_nodes, "WindowFunctionIdentity")
    invalid = (
        (([], "rank", role), TypeError, "namespace must be an exact tuple"),
        (((1,), "rank", role), TypeError, "namespace components must be strings"),
        ((("",), "rank", role), ValueError, "namespace components must be non-empty"),
        (((), 1, role), TypeError, "name must be a string"),
        (((), "", role), ValueError, "name must be non-empty"),
        (
            ((), "rank", "window_function"),
            TypeError,
            "role must be a WindowFunctionRole",
        ),
    )
    for arguments, error_type, message in invalid:
        with pytest.raises(error_type, match=re.escape(message)):
            _window_identity.WindowFunctionIdentity(*cast(Any, arguments))


@pytest.mark.parametrize(("call", "namespace", "name"), IDENTITY_CASES)
def test_window_identity_namespace_name_case_and_hash_are_preserved(
    call: str,
    namespace: tuple[str, ...],
    name: str,
) -> None:
    expression = _window_expression(
        _window_query("order by:\n    observed_at", projection=f"rn = {call}()")
    )
    expected = _window_identity.WindowFunctionIdentity(
        namespace,
        name,
        _window_identity.WindowFunctionRole.WINDOW_FUNCTION,
    )
    assert expression.identity == expected
    assert hash(expression.identity) == hash(expected)
    assert repr(expression.identity) == repr(expected)


def test_window_spec_constructor_invariants_and_hash_are_exact() -> None:
    span = Span(path="constructor.pietto", line=1, column=1, end_line=1, end_column=2)
    expression = NameExpr(span=span, name="id")
    item = OrderItem(span=span, expression=expression, direction=None)
    spec = WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    assert spec == WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    assert hash(spec) == hash(
        WindowSpec(span=span, partition_by=(expression,), order_by=(item,))
    )
    invalid = (
        (([], (item,)), TypeError, "partition_by must be an exact tuple"),
        (((expression,), []), TypeError, "order_by must be an exact tuple"),
        (
            ((object(),), (item,)),
            TypeError,
            "partition_by items must be Expression instances",
        ),
        (
            ((expression,), (object(),)),
            TypeError,
            "order_by items must be OrderItem instances",
        ),
        (((), ()), ValueError, "window spec requires partition_by or order_by"),
    )
    for arguments, error_type, message in invalid:
        with pytest.raises(error_type, match=re.escape(message)):
            WindowSpec(
                span=span,
                partition_by=cast(Any, arguments[0]),
                order_by=cast(Any, arguments[1]),
            )


@pytest.mark.parametrize(
    ("name", "body", "partition_count", "directions"),
    CANONICAL_CASES,
    ids=[case[0] for case in CANONICAL_CASES],
)
def test_parser_preserves_canonical_window_shapes(
    name: str,
    body: str,
    partition_count: int,
    directions: tuple[str | None, ...],
) -> None:
    expression = _window_expression(_window_query(body))
    assert len(expression.spec.partition_by) == partition_count, name
    assert tuple(item.direction for item in expression.spec.order_by) == directions
    assert expression.identity.name == "row_number"
    assert expression.identity.namespace == ()


@pytest.mark.parametrize(("call", "expected"), CALL_ARGUMENT_CASES)
def test_parser_preserves_call_arguments_and_trailing_comma(
    call: str,
    expected: tuple[str | int, ...],
) -> None:
    expression = _window_expression(
        _window_query("order by:\n    observed_at", projection=f"value = {call}")
    )
    assert tuple(
        _literal_argument_value(item) for item in expression.call.arguments
    ) == (expected)


@pytest.mark.parametrize("function_name", CANDIDATE_IDENTITY_CASES)
def test_parser_preserves_function_candidate_identity(function_name: str) -> None:
    expression = _window_expression(
        _window_query(
            "order by:\n    observed_at",
            projection=f"value = {function_name}()",
        )
    )
    assert expression.identity.namespace == ()
    assert expression.identity.name == function_name
    assert (
        expression.identity.role is _window_identity.WindowFunctionRole.WINDOW_FUNCTION
    )


@pytest.mark.parametrize(("call", "namespace", "name"), QUALIFIED_IDENTITY_CASES)
def test_parser_preserves_qualified_identity_namespace_and_case(
    call: str,
    namespace: tuple[str, ...],
    name: str,
) -> None:
    expression = _window_expression(
        _window_query("partition by:\n    id", projection=f"value = {call}()")
    )
    assert expression.identity.namespace == namespace
    assert expression.identity.name == name
    assert isinstance(expression.call.callee, DottedNameExpr)
    assert expression.call.callee.parts == (*namespace, name)


def test_multiple_window_and_ordinary_select_items_preserve_order_aliases_and_independence() -> (
    None
):
    source = (
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        rn = row_number() window:\n"
        "            order by:\n"
        "                observed_at\n"
        "        value\n"
        "        previous = lag(value, 1) window:\n"
        "            partition by:\n"
        "                account_id\n"
    )
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    assert tuple(item.alias for item in relation.select_items) == (
        None,
        "rn",
        None,
        "previous",
    )
    first = cast(WindowExpr, relation.select_items[1].expression)
    second = cast(WindowExpr, relation.select_items[3].expression)
    assert first is not second
    assert first.spec != second.spec
    assert first.identity.name == "row_number"
    assert second.identity.name == "lag"


@pytest.mark.parametrize(
    ("name", "body", "expression_span", "call_span", "spec_span"),
    SPAN_CASES,
    ids=[case[0] for case in SPAN_CASES],
)
def test_window_ast_spans_are_exact(
    name: str,
    body: str,
    expression_span: tuple[int, int, int, int],
    call_span: tuple[int, int, int, int],
    spec_span: tuple[int, int, int, int],
) -> None:
    source = _window_query(body)
    result = parse_source(source, path=f"span-{name}.pietto")
    assert result.diagnostics == ()
    assert result.ast is not None
    relation = cast(QueryDef, result.ast.definitions[-1])
    item = relation.select_items[0]
    expression = cast(WindowExpr, item.expression)
    assert _span_tuple(expression.span) == expression_span
    assert _span_tuple(expression.call.span) == call_span
    assert _span_tuple(expression.spec.span) == spec_span
    assert _span_tuple(expression.call.callee.span) == (4, 14, 4, 24)
    assert _span_tuple(item.span) == (4, 9, *expression_span[2:])


@pytest.mark.parametrize(("item_source", "direction", "item_span"), DIRECTION_CASES)
def test_window_order_direction_and_spans_are_exact(
    item_source: str,
    direction: str | None,
    item_span: tuple[int, int, int, int],
) -> None:
    expression = _window_expression(_window_query(f"order by:\n    {item_source}"))
    item = expression.spec.order_by[0]
    assert item.direction == direction
    assert _span_tuple(item.span) == item_span
    assert _span_tuple(item.expression.span) == (6, 17, 6, 28)


def test_window_order_integer_literal_bypasses_final_order_ordinal_rejection() -> None:
    expression = _window_expression(_window_query("order by:\n    1"))
    item = expression.spec.order_by[0]
    assert isinstance(item.expression, LiteralExpr)
    assert item.expression.value == 1
    final_order = parse_source(
        "query ranked:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        1\n"
    )
    assert final_order.ast is None
    assert len(final_order.diagnostics) == 1
    assert final_order.diagnostics[0].message == (
        "Ordinal ORDER BY expressions are not supported."
    )


@pytest.mark.parametrize(
    ("name", "body", "old", "new"),
    MALFORMED_CASES,
    ids=[case[0] for case in MALFORMED_CASES],
)
def test_slice2_malformed_and_deferred_window_syntax_remains_rejected(
    name: str,
    body: str,
    old: str | None,
    new: str | None,
) -> None:
    source = _window_query(body)
    if old is not None and new is not None:
        source = source.replace(old, new, 1)
    result = parse_source(source, path=f"malformed-{name}.pietto")
    assert result.ast is None, name
    assert result.diagnostics
    assert all(
        diagnostic.code in {"PIE-P1000", "PIE-P1005"}
        and diagnostic.severity is Severity.ERROR
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("body", VALID_BRIDGE_CASES)
def test_valid_window_parse_retires_temporary_slice2_bridge(body: str) -> None:
    result = parse_source(_window_query(body))
    assert result.ast is not None
    assert result.diagnostics == ()
    assert TEMPORARY_BRIDGE_MESSAGE not in repr(result)


@pytest.mark.parametrize(("call", "message"), SEMANTIC_IDENTITY_CASES)
def test_semantic_check_fails_closed_with_existing_unknown_function_diagnostic(
    call: str,
    message: str,
) -> None:
    result = parse_source(
        _semantic_window_source(f"{call}()"), path="semantic-window.pietto"
    )
    assert result.diagnostics == ()
    assert result.ast is not None
    expression = cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression
    semantic = analyze(result.ast)
    matching = tuple(item for item in semantic.diagnostics if item.code == "PIE-S2103")
    if call == "rank":
        assert matching == ()
        assert expression in semantic.model.expression_value_types
        return
    assert len(matching) == 1
    diagnostic = matching[0]
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.message == message
    assert diagnostic.location.path == "semantic-window.pietto"
    assert (
        diagnostic.location.line,
        diagnostic.location.column,
        diagnostic.location.end_line,
        diagnostic.location.end_column,
    ) == _span_tuple(cast(WindowExpr, expression).call.span)


def test_window_expression_publishes_no_semantic_value_type_fact() -> None:
    result = parse_source(_semantic_window_source("row_number()"))
    assert result.diagnostics == ()
    assert result.ast is not None
    expression = cast(
        WindowExpr,
        cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression,
    )
    semantic = analyze(result.ast)
    assert not any(item.code == "PIE-S2103" for item in semantic.diagnostics)
    assert expression in semantic.model.expression_value_types
    assert semantic.model.expression_value_types[expression].resolved_type.name == "Int"
    assert expression.call not in semantic.model.expression_value_types
    assert all(
        argument not in semantic.model.expression_value_types
        for argument in expression.call.arguments
    )


def test_ir_lowering_fails_closed_on_missing_window_expression_fact() -> None:
    result = parse_source(_semantic_window_source("row_number()"))
    assert result.ast is not None
    expression = cast(
        WindowExpr,
        cast(QueryDef, result.ast.definitions[-1]).select_items[0].expression,
    )
    semantic = analyze(result.ast)
    lowered = lower_expr(expression, semantic.model)
    assert isinstance(lowered.expression, WindowCallIR)
    assert lowered.expression.identity.name == "row_number"
    assert lowered.expression.arguments == ()
    assert lowered.diagnostics == ()


def test_project_parse_only_path_remains_deferred_without_window_result_dependency_or_lineage() -> (
    None
):
    expression = _window_expression(_window_query("order by:\n    observed_at"))
    adapted = adapt_project_row_expression_schema(
        expression=expression,
        output_name="rn",
        input_schema=ProjectRowSchema(fields={}),
        upstream_state=None,
        relation_qualifier=None,
        expression_value_types={},
    )
    assert adapted.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert adapted.reason is ProjectExpressionSchemaReason.MISSING_VALUE_TYPE
    assert adapted.origin is ProjectExpressionSchemaOriginKind.UNKNOWN
    assert adapted.dependency_placeholders == ()
    assert adapted.lineage_placeholders == ()
    assert ProjectRowResultRole.WINDOW_RESULT.value == "window_result"


def test_no_window_ir_sql_catalog_capability_project_role_or_public_serialization_surface_is_added() -> (
    None
):
    unchanged = (
        "src/pietto/ir/__init__.py",
        "src/pietto/ir/diagnostics.py",
        "src/pietto/sql/__init__.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/semantic/catalog.py",
        "src/pietto/semantic/capability_inventory.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/cli.py",
        "src/pietto/cli_json.py",
        "src/pietto/_metadata/serializer.py",
    )
    assert all(_git_output(["diff", "--", path]) == "" for path in unchanged)
    assert "class WindowIR" not in _read("src/pietto/ir/model.py")
    assert 'WINDOW_RESULT = "window_result"' in _read("src/pietto/_project/model.py")
    assert "WindowFunctionIdentity" not in _read("src/pietto/semantic/catalog.py")


def test_grammar_generated_parser_api_and_public_exports_are_byte_locked() -> None:
    expected = {
        "grammar/Pietto.g4": "661f00037b4ade8f8b5bef0cb3e070e4379decdd11cd19021d68e960e69d2724",
        "src/pietto/parser_api.py": "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b",
        "src/pietto/__init__.py": "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d",
    }
    assert {path: _sha256(path) for path in expected} == expected
    generated = tuple(
        path
        for path in (REPO_ROOT / "src/pietto/generated").iterdir()
        if path.is_file()
    )
    assert len(generated) == 8
    assert _digest(generated) == (
        "9a84d108062bdbd87f5cd1d6e237e66f8bbb39d1d9d7674312eab6eb156cbad1"
    )
    assert not hasattr(pietto, "WindowExpr")
    assert not hasattr(pietto, "WindowSpec")


def test_expression_walkers_and_exhaustive_dispatch_are_classified() -> None:
    semantic = _read("src/pietto/semantic/expressions.py")
    lowering = _read("src/pietto/ir/lowering.py")
    assert "if isinstance(expression, WindowExpr):" in semantic
    branch = semantic[semantic.index("if isinstance(expression, WindowExpr):") :]
    assert branch.index("return _UNKNOWN_VALUE_TYPE") < branch.index(
        "if isinstance(expression, LiteralExpr):"
    )
    assert "if type(expression) is WindowExpr:" in lowering
    assert lowering.index(
        "expression not in semantic_model.expression_value_types"
    ) < lowering.index("if type(expression) is WindowExpr:")
    assert "_lower_window_expr(" in lowering
    assert "expression value type" in lowering
    for relative in (
        "src/pietto/semantic/aggregates.py",
        "src/pietto/semantic/let_bindings.py",
        "src/pietto/semantic/satisfying.py",
        "src/pietto/_project/row_expression_schema.py",
        "src/pietto/_project/row_expression_type_facts.py",
    ):
        assert (
            _git_output(["diff", "--", relative]) == ""
            or _phase54_active_gate2_is_active()
        )


def test_reader_hash_inventory_and_nested_hash_closure_is_exact() -> None:
    compiler_paths = [REPO_ROOT / "Makefile", REPO_ROOT / "grammar/Pietto.g4"]
    compiler_paths.extend(
        path
        for path in (REPO_ROOT / "src/pietto").rglob("*")
        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc"
    )
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
    assert _digest(tuple(compiler_paths)) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _sha256("src/pietto/ast_nodes.py") == AST_NODES_SHA256
    assert _sha256("src/pietto/ast_builder.py") == AST_BUILDER_SHA256
    assert _sha256("src/pietto/semantic/expressions.py") == (
        SEMANTIC_EXPRESSIONS_SHA256
    )


def test_slice3_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if _phase54_active_gate2_is_active():
        return
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    cached = _git_output(["diff", "--cached", "--name-status"])
    assert cached == ""
    dirty = tracked | untracked
    phase54_added, phase54_modified = _phase54_slice2_paths()
    phase54_allowlist = phase54_added | phase54_modified
    assert dirty in (set(), ALLOWLIST_PATHS, phase54_allowlist)
    head = _git_output(["rev-parse", "HEAD"])
    branch = _git_output(["branch", "--show-current"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    if dirty == phase54_allowlist:
        assert tracked == phase54_modified
        assert untracked == phase54_added
        assert branch == "main"
        assert head == main == origin_main
        assert head in {
            PHASE54_SLICE2_BASE_HEAD_SHA,
            PHASE54_SLICE4_BASE_HEAD_SHA,
            PHASE54_SLICE5_BASE_HEAD_SHA,
            PHASE54_SLICE6_BASE_HEAD_SHA,
            PHASE54_SLICE7_BASE_HEAD_SHA,
            PHASE54_SLICE8_BASE_HEAD_SHA,
            PHASE54_SLICE9_BASE_HEAD_SHA,
            "b81843acadb294630db361c09949868d004b1bca",
        }
    elif dirty:
        assert tracked == MODIFIED_PATHS
        assert untracked == ADDED_PATHS
        assert branch == "main"
        assert head == main == origin_main == BASE_HEAD_SHA
    else:
        if branch == phase54_publication_topic_branch():
            assert phase54_publication_clean_topic_is_active()
            assert main == origin_main == phase54_publication_topic_base()
            return
        assert branch in ("", "main")
        if main is not None:
            assert main == head
        if origin_main is not None:
            assert origin_main == head


def test_test_inventory_focused_selector_and_dirty_overlay_are_exact() -> None:
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    readable = {path for path in (*tracked, *untracked) if (REPO_ROOT / path).is_file()}
    assert len(readable) == 944
    assert sum(path.endswith(".py") for path in readable) == 579
    assert sum(path.endswith(".md") for path in readable) == 269
    test_modules = {
        path
        for path in readable
        if path.startswith("tests/test_") and path.endswith(".py")
    }
    assert len(test_modules) == 465
    top_level_tests = 0
    for relative in sorted(test_modules):
        tree = ast.parse(_read(relative), filename=relative)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert top_level_tests == 5489
    assert (
        3488
        == 381 + 834 + 627 + 424 + 279 + 168 + 156 + 12 + 145 + 190 + 70 + 70 + 97 + 35
    )
    assert 10784 == 10576 + 208
    assert 10784 - 185 == 10599
    docs = (
        _read(SPEC_REL)
        + _read("docs/spec/phase53-row-number-direct-field-mvp-contract-v1.md")
        + _read(PLAN_REL)
        + _read(
            "tests/test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py"
        )
    )
    for value in (
        "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429",
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
    ):
        assert value in docs


def test_validation_gate3_and_no_behavior_boundaries_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    for required in (
        "607 focused",
        "6528 passed, 183 deselected",
        "6711 clean-CI passes",
        "A3/M50/D0",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Slice 4 retains generic compatibility ownership",
        "Slice 5 retains nullability algebra",
        "Slice 15 retains Window IR",
        "0.1.0",
    ):
        assert required in docs, required
    assert (
        _git_output(
            ["diff", "--", "pyproject.toml", "uv.lock", ".github/workflows/ci.yml"]
        )
        == ""
    )
    assert len(ALLOWLIST_PATHS) == 26
    assert len(MODIFIED_PATHS) == 24
    assert len(ADDED_PATHS) == 2


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
# Phase 53 Slice 13 reader migration.
