from __future__ import annotations

import ast
import dataclasses
from functools import lru_cache
import hashlib
from pathlib import Path
import subprocess
import tomllib
from typing import cast

import pytest

import pietto
import pietto.ir as public_ir
import pietto.semantic as public_semantic
import pietto.sql as public_sql
from pietto.ast_nodes import QueryDef, Script, TableDef
from pietto.ir import build_ir
from pietto.ir.lowering import lower_expr
from pietto.ir.model import (
    AggregateCallIR,
    BinaryIR,
    CallIR,
    ExpressionIR,
    FieldRefIR,
    LiteralIR,
    NullabilityIR,
    OrderDirectionIR,
    RelationIR,
    ScriptIR,
    SourceSpan,
    TypeKindIR,
    TypeRefIR,
    WindowCallIR,
    WindowFunctionIdentityIR,
    WindowFunctionRoleIR,
    WindowOrderItemIR,
    WindowSpecIR,
)
from pietto.parser_api import parse_source
from pietto.semantic import analyze
import pietto.semantic.capability_windows as capability_windows
from pietto.semantic.capability_facts import (
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
from pietto.semantic.model import SemanticResult
from pietto.sql.expressions import render_expression_sql
from pietto.sql.mysql import emit_mysql_sql
from pietto.sql.mysql_expressions import render_mysql_expression
from pietto.sql.postgres import emit_postgres_sql


REPO_ROOT = Path(__file__).resolve().parents[1]
SELF_REL = (
    "tests/"
    "test_phase53_window_ir_dual_backend_lowering_window_function_facts_contract.py"
)
SPEC_REL = (
    "docs/spec/"
    "phase53-window-ir-dual-backend-lowering-window-function-facts-contract-v1.md"
)
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
CAPABILITY_REL = "src/pietto/semantic/capability_windows.py"
BASE_HEAD = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
PUBLICATION_BRANCH = "phase53/slice15-window-ir-dual-backend-lowering"
PUBLICATION_TITLE = "Add Phase 53 window IR and dual-backend lowering"
PHASE54_SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"

IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
)
ZERO_ARGUMENT_IDENTITIES = IDENTITIES[:5]
RESULT_TYPES = {
    "row_number": ("Int", NullabilityIR.NON_NULL),
    "rank": ("Int", NullabilityIR.NON_NULL),
    "dense_rank": ("Int", NullabilityIR.NON_NULL),
    "percent_rank": ("Float", NullabilityIR.NON_NULL),
    "cume_dist": ("Float", NullabilityIR.NON_NULL),
    "ntile": ("Int", NullabilityIR.NON_NULL),
    "lag": ("Int", NullabilityIR.NULLABLE),
    "lead": ("Int", NullabilityIR.NULLABLE),
}
SQL_NAMES = {
    "row_number": "ROW_NUMBER",
    "rank": "RANK",
    "dense_rank": "DENSE_RANK",
    "percent_rank": "PERCENT_RANK",
    "cume_dist": "CUME_DIST",
    "ntile": "NTILE",
    "lag": "LAG",
    "lead": "LEAD",
}

ADDED_PATHS = (
    "docs/spec/phase53-completion-audit-and-status-lock-v1.md",
    "tests/test_phase53_completion_audit_and_status_lock.py",
)
CORE_MODIFIED_PATHS = (PLAN_REL,)
READER_PATHS = (
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
MODIFIED_PATHS = (*CORE_MODIFIED_PATHS, *READER_PATHS)
POST_FORMATTER_READER_REPAIR_PATHS = (
    "tests/test_phase49_minimal_private_lineage_carrier_source_direct_rename.py",
    "tests/test_phase51_completion_audit_and_status_lock.py",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py",
)
FORMATTER_PATHS = tuple(
    path
    for path in (*ADDED_PATHS, *MODIFIED_PATHS)
    if path.endswith(".py") and path not in POST_FORMATTER_READER_REPAIR_PATHS
)
TOPOLOGICAL_PHASE53_READERS = (
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py",
    "tests/test_phase53_grouped_result_ranking_aggregate_result_inputs_bounded_let_visibility_contract.py",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
    "tests/test_phase53_lag_lead_navigation_offset_default_nullability_contract.py",
)

EXPECTED_TEST_NAMES = (
    "test_slice15_artifact_paths_heading_contract_and_lifecycle_are_exact",
    "test_window_ir_carrier_fields_frozen_slots_equality_and_hashing_are_exact",
    "test_window_ir_identity_constructor_validation_is_exact",
    "test_window_ir_order_item_constructor_validation_is_exact",
    "test_window_ir_spec_constructor_validation_is_exact",
    "test_window_ir_call_constructor_validation_and_arity_are_exact",
    "test_all_eight_window_identities_lower_with_source_identity_and_result_type",
    "test_zero_argument_identity_ir_shapes_are_exact",
    "test_ntile_argument_ir_shape_is_exact",
    "test_lag_lead_omitted_and_explicit_argument_shapes_are_exact",
    "test_partition_and_local_order_multiplicity_preserve_source_order_and_duplicates",
    "test_window_order_omitted_asc_desc_direction_facts_are_exact",
    "test_multiple_window_outputs_lower_in_select_order",
    "test_grouped_group_key_and_aggregate_result_operands_lower_underlying_expressions",
    "test_grouped_window_sql_is_same_level_without_subquery_or_alias_operands",
    "test_downstream_window_fields_lower_through_ordinary_row_rules",
    "test_final_order_window_aliases_render_as_aliases",
    "test_postgres_exact_sql_bytes_for_all_identities",
    "test_mysql_exact_sql_bytes_for_all_identities",
    "test_backend_identifier_quoting_and_escaping_differences_are_exact",
    "test_postgres_malformed_window_ir_becomes_pie_b1000",
    "test_mysql_malformed_window_ir_becomes_pie_b1000",
    "test_unrelated_missing_semantic_facts_preserve_pie_i1000",
    "test_window_capability_fact_inventory_keys_evidence_and_privacy_are_exact",
    "test_window_capability_lookup_found_absent_unknown_and_conflict_are_exact",
    "test_window_capability_facts_do_not_authorize_compiler_acceptance",
    "test_public_ir_sql_semantic_cli_json_and_metadata_surfaces_are_unchanged",
    "test_frames_named_windows_qualify_extension_and_later_identity_boundaries_are_locked",
    "test_generated_golden_fixture_package_dependency_and_version_boundaries_are_locked",
    "test_reader_hash_dag_allowlist_and_fixed_point_are_exact",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_dirty_clean_depth_one_shallow_and_negative_topology_boundaries_are_exact",
    "test_gate2_evidence_gate3_publication_and_slice16_stop_contract_are_locked",
)
EXPECTED_CARDINALITIES = (
    1,
    4,
    8,
    8,
    8,
    16,
    8,
    5,
    3,
    8,
    6,
    6,
    4,
    8,
    4,
    4,
    4,
    8,
    8,
    6,
    8,
    8,
    4,
    24,
    8,
    4,
    1,
    12,
    1,
    1,
    1,
    8,
    1,
)

SPEC_HEADINGS = (
    "Status And Ownership",
    "Stage And Authority Contract",
    "Identity, Result, And Argument Contract",
    "Private Window IR Contract",
    "Lowering And Grouped-result Contract",
    "PostgreSQL Rendering Contract",
    "Private-MySQL Rendering Contract",
    "Descriptive WINDOW_FUNCTION Capability Facts",
    "Diagnostics, Compatibility, And Public Boundaries",
    "Unsupported And Future-owned Boundaries",
    "Lifecycle And Gate Boundary",
)

SOURCE_PREFIX = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    category: Text nullable\n"
    "    amount: Int nullable\n"
    "    score: Float not null\n"
)
SPAN = SourceSpan("slice15.pietto", 1, 1, 1, 2)
INT_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Int",
    canonical_name="Int",
    kind=TypeKindIR.BUILTIN,
    canonical_kind=TypeKindIR.BUILTIN,
    nullability=NullabilityIR.NON_NULL,
)
UNKNOWN_TYPE = TypeRefIR(
    symbol=None,
    canonical_symbol=None,
    declared_name="Unknown",
    canonical_name="Unknown",
    kind=TypeKindIR.UNKNOWN,
    canonical_kind=TypeKindIR.UNKNOWN,
    nullability=NullabilityIR.UNKNOWN,
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout.rstrip()


def _repository_paths() -> tuple[str, ...]:
    tracked = _git_output(["ls-files"]).splitlines()
    untracked = _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


def _dirty_paths() -> set[str]:
    return {
        line[3:]
        for line in _git_output(
            ["status", "--porcelain=v1", "--untracked-files=all"]
        ).splitlines()
    }


def _module_literal(relative: str, name: str) -> object:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        value = node.value
        if value is None:
            continue
        targets = node.targets if isinstance(node, ast.Assign) else (node.target,)
        for target in targets:
            if isinstance(target, ast.Name) and target.id == name:
                return ast.literal_eval(value)
            if isinstance(target, (ast.Tuple, ast.List)):
                names = [
                    item.id if isinstance(item, ast.Name) else None
                    for item in target.elts
                ]
                if name in names:
                    combined = ast.literal_eval(value)
                    assert isinstance(combined, tuple)
                    return combined[names.index(name)]
    raise AssertionError(f"missing module literal {relative}:{name}")


def _phase54_slice2_allowlist() -> set[str]:
    added = cast(set[str], _module_literal(PHASE54_SLICE2_STATE_REL, "ADDED_PATHS"))
    non_reader = cast(
        set[str],
        _module_literal(PHASE54_SLICE2_STATE_REL, "NON_READER_MODIFIED_PATHS"),
    )
    readers = cast(
        set[str], _module_literal(PHASE54_SLICE2_STATE_REL, "MECHANICAL_READER_PATHS")
    )
    return added | non_reader | readers


def _test_manifest() -> tuple[tuple[str, ...], tuple[int, ...]]:
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
            if not (
                isinstance(decorator, ast.Call)
                and isinstance(decorator.func, ast.Attribute)
                and decorator.func.attr == "parametrize"
            ):
                continue
            values = decorator.args[1]
            assert isinstance(values, ast.Call)
            assert isinstance(values.func, ast.Name) and values.func.id == "range"
            bound = values.args[0]
            assert isinstance(bound, ast.Constant) and type(bound.value) is int
            cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(item.name for item in functions), tuple(cardinalities)


def _source_connector(dialect: str) -> str:
    connector = "postgres" if dialect == "postgresql" else "mysql"
    return SOURCE_PREFIX + f'source rows: Row is {connector}.table("rows")\n'


def _window_call_source(identity: str) -> str:
    if identity in ZERO_ARGUMENT_IDENTITIES:
        return f"{identity}()"
    if identity == "ntile":
        return "ntile(4)"
    if identity == "lag":
        return "lag(amount, 2, amount)"
    return "lead(amount, 0, amount)"


def _single_window_source(identity: str, *, dialect: str = "postgresql") -> str:
    return (
        _source_connector(dialect) + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        f"        result = {_window_call_source(identity)} window:\n"
        "            partition by:\n"
        "                category\n"
        "            order by:\n"
        "                id desc\n"
    )


@lru_cache(maxsize=None)
def _compile(source: str) -> tuple[Script, SemanticResult, ScriptIR]:
    parsed = parse_source(source, path="slice15.pietto")
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    ir_result = build_ir(parsed.ast, semantic.model)
    assert ir_result.diagnostics == ()
    assert ir_result.ir is not None
    return parsed.ast, semantic, ir_result.ir


def _relation(script_ir: ScriptIR, name: str | None = None) -> RelationIR:
    relations = tuple(
        item for item in script_ir.definitions if isinstance(item, RelationIR)
    )
    if name is None:
        assert relations
        return relations[-1]
    return next(item for item in relations if item.name == name)


def _window(expression: ExpressionIR) -> WindowCallIR:
    assert isinstance(expression, WindowCallIR)
    return expression


def _single_window_ir(identity: str) -> WindowCallIR:
    _, _, script_ir = _compile(_single_window_source(identity))
    relation = _relation(script_ir, "windows")
    assert len(relation.projections) == 1
    return _window(relation.projections[0].expression)


def _literal(value: int) -> LiteralIR:
    return LiteralIR(span=SPAN, value_type=UNKNOWN_TYPE, value=value)


def _field(name: str, *, qualifier: tuple[str, ...] = ()) -> FieldRefIR:
    return FieldRefIR(
        span=SPAN,
        value_type=INT_TYPE,
        name=name,
        qualifier=qualifier,
        field=None,
    )


def _identity(name: str = "row_number") -> WindowFunctionIdentityIR:
    return WindowFunctionIdentityIR(
        namespace=(),
        name=name,
        role=WindowFunctionRoleIR.WINDOW_FUNCTION,
    )


def _order_item(
    expression: ExpressionIR | None = None,
    *,
    direction: OrderDirectionIR = OrderDirectionIR.ASC,
    explicit: bool = False,
) -> WindowOrderItemIR:
    return WindowOrderItemIR(
        expression=_field("id") if expression is None else expression,
        direction=direction,
        direction_is_explicit=explicit,
        span=SPAN,
    )


def _spec(
    *,
    partition_by: tuple[ExpressionIR, ...] = (),
    order_by: tuple[WindowOrderItemIR, ...] | None = None,
) -> WindowSpecIR:
    return WindowSpecIR(
        partition_by=partition_by,
        order_by=(_order_item(),) if order_by is None else order_by,
        span=SPAN,
    )


def _manual_window(
    name: str = "row_number",
    *,
    arguments: tuple[ExpressionIR, ...] | None = None,
    spec: WindowSpecIR | None = None,
) -> WindowCallIR:
    if arguments is None:
        arguments = () if name in ZERO_ARGUMENT_IDENTITIES else (_literal(1),)
    return WindowCallIR(
        span=SPAN,
        value_type=INT_TYPE,
        identity=_identity(name),
        arguments=arguments,
        spec=_spec() if spec is None else spec,
    )


def _unchecked_dataclass(
    instance_type: type[object], values: dict[str, object]
) -> object:
    instance = object.__new__(instance_type)
    for name, value in values.items():
        object.__setattr__(instance, name, value)
    return instance


def _unchecked_identity(**changes: object) -> WindowFunctionIdentityIR:
    values: dict[str, object] = {
        "namespace": (),
        "name": "row_number",
        "role": WindowFunctionRoleIR.WINDOW_FUNCTION,
    }
    values.update(changes)
    return cast(
        WindowFunctionIdentityIR,
        _unchecked_dataclass(WindowFunctionIdentityIR, values),
    )


def _unchecked_order_item(**changes: object) -> WindowOrderItemIR:
    values: dict[str, object] = {
        "expression": _field("id"),
        "direction": OrderDirectionIR.ASC,
        "direction_is_explicit": False,
        "span": SPAN,
    }
    values.update(changes)
    return cast(
        WindowOrderItemIR,
        _unchecked_dataclass(WindowOrderItemIR, values),
    )


def _unchecked_spec(**changes: object) -> WindowSpecIR:
    values: dict[str, object] = {
        "partition_by": (),
        "order_by": (_order_item(),),
        "span": SPAN,
    }
    values.update(changes)
    return cast(WindowSpecIR, _unchecked_dataclass(WindowSpecIR, values))


def _unchecked_window(**changes: object) -> WindowCallIR:
    values: dict[str, object] = {
        "span": SPAN,
        "value_type": INT_TYPE,
        "identity": _identity(),
        "arguments": (),
        "spec": _spec(),
    }
    values.update(changes)
    return cast(WindowCallIR, _unchecked_dataclass(WindowCallIR, values))


def _replace_only_window(script_ir: ScriptIR, replacement: ExpressionIR) -> ScriptIR:
    target = _relation(script_ir, "windows")
    assert len(target.projections) == 1
    projection = target.projections[0]
    replaced_relation = dataclasses.replace(
        target,
        projections=(dataclasses.replace(projection, expression=replacement),),
    )
    definitions = tuple(
        replaced_relation if item is target else item for item in script_ir.definitions
    )
    return dataclasses.replace(script_ir, definitions=definitions)


def _malformed_script_ir(
    case: int,
    *,
    dialect: str,
    variant: int = 0,
) -> ScriptIR:
    _, _, script_ir = _compile(_single_window_source("row_number", dialect=dialect))
    valid = _window(_relation(script_ir, "windows").projections[0].expression)
    if case == 0:
        replacement = _unchecked_window(
            identity=_unchecked_identity(namespace=("extension",))
        )
    elif case == 1:
        replacement = _unchecked_window(identity=_unchecked_identity(name="ROW_NUMBER"))
    elif case == 2:
        replacement = _unchecked_window(
            identity=_unchecked_identity(role="window_function")
        )
    elif case == 3:
        replacement = _unchecked_window(arguments=(_literal(1),))
    elif case == 4:
        malformed_windows = (
            _unchecked_window(arguments=[_literal(1)]),
            _unchecked_window(spec=_unchecked_spec(partition_by=[_field("category")])),
            _unchecked_window(span=object()),
            _unchecked_window(value_type=object()),
            _unchecked_window(spec=_unchecked_spec(span=object())),
            _unchecked_window(
                spec=_unchecked_spec(order_by=(_unchecked_order_item(span=object()),))
            ),
        )
        replacement = malformed_windows[variant]
    elif case == 5:
        replacement = _unchecked_window(spec=_unchecked_spec(order_by=()))
    elif case == 6:
        malformed_items = (
            _unchecked_order_item(direction="ASC"),
            _unchecked_order_item(direction_is_explicit=1),
            _unchecked_order_item(
                direction=OrderDirectionIR.DESC,
                direction_is_explicit=False,
            ),
            object(),
        )
        replacement = _unchecked_window(
            spec=_unchecked_spec(order_by=(malformed_items[variant],))
        )
    else:
        replacement = CallIR(
            span=valid.span,
            value_type=valid.value_type,
            callee="lower",
            callee_symbol=None,
            arguments=(valid,),
        )
    return _replace_only_window(script_ir, replacement)


def _grouped_source(*, dialect: str, windows_first: bool) -> str:
    group = "        group_name = category\n"
    total = "        total = sum(amount)\n"
    rank = (
        "        group_rank = rank() window:\n"
        "            partition by:\n"
        "                group_name\n"
        "            order by:\n"
        "                total desc\n"
    )
    lag = (
        "        previous_total = lag(total, 0, total) window:\n"
        "            order by:\n"
        "                total\n"
    )
    select_items = (
        rank + lag + group + total if windows_first else group + total + rank + lag
    )
    return (
        _source_connector(dialect) + "query grouped:\n"
        "    from rows\n"
        "    group by:\n"
        "        category\n"
        "    select:\n" + select_items + "    order by:\n"
        "        total desc\n"
        "        group_rank\n"
        "        previous_total asc\n"
    )


def _sql_for(source: str, dialect: str) -> str:
    _, _, script_ir = _compile(source)
    result = (
        emit_postgres_sql(script_ir)
        if dialect == "postgresql"
        else emit_mysql_sql(script_ir)
    )
    assert result.diagnostics == ()
    assert len(result.artifacts) == 1
    return result.artifacts[0].sql


def _path_manifest(kind: str, paths: tuple[str, ...]) -> bytes:
    return "".join(
        f"{kind}{index:02d}\t{path}\n" for index, path in enumerate(paths, start=1)
    ).encode("utf-8")


def _top_level_test_function_count(paths: tuple[str, ...]) -> int:
    count = 0
    for relative in paths:
        if not relative.startswith("tests/test_") or not relative.endswith(".py"):
            continue
        tree = ast.parse(_read(relative), filename=relative)
        count += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    return count


def test_slice15_artifact_paths_heading_contract_and_lifecycle_are_exact() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    headings = tuple(
        line.removeprefix("## ") for line in spec.splitlines() if line.startswith("## ")
    )
    assert headings == SPEC_HEADINGS
    assert spec.startswith(
        "# Phase 53 Window IR, Dual-backend Lowering, And Window-function "
        "Facts Contract v1\n"
    )
    assert all((REPO_ROOT / path).is_file() for path in ADDED_PATHS)
    assert (
        plan.count(
            "## Slice 15 — Window IR, Dual-backend Lowering, And Window-function Facts"
        )
        == 1
    )
    for document in (spec, plan):
        normalized = " ".join(document.split())
        assert "Phase 53 remains `ACTIVE`" in normalized
        assert "Slices 1 through 15" in normalized
        assert "Slice 16" in normalized and "UNSTARTED" in normalized
        assert "SLICE16_GATE0_GATE1" in normalized


@pytest.mark.parametrize("_case", range(4))
def test_window_ir_carrier_fields_frozen_slots_equality_and_hashing_are_exact(
    _case: int,
) -> None:
    carrier_types = (
        WindowFunctionIdentityIR,
        WindowOrderItemIR,
        WindowSpecIR,
        WindowCallIR,
    )
    expected_fields = (
        ("namespace", "name", "role"),
        ("expression", "direction", "direction_is_explicit", "span"),
        ("partition_by", "order_by", "span"),
        ("span", "value_type", "identity", "arguments", "spec"),
    )
    instances = (
        _identity(),
        _order_item(),
        _spec(),
        _manual_window(),
    )
    carrier_type = carrier_types[_case]
    instance = instances[_case]
    assert dataclasses.is_dataclass(carrier_type)
    assert (
        tuple(field.name for field in dataclasses.fields(carrier_type))
        == (expected_fields[_case])
    )
    assert "__dict__" not in dir(instance)
    assert instance == instances[_case]
    assert hash(instance) == hash(instances[_case])
    first_field = expected_fields[_case][0]
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(instance, first_field, getattr(instance, first_field))


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_identity_constructor_validation_is_exact(_case: int) -> None:
    if _case == 0:
        identity = _identity()
        assert identity == WindowFunctionIdentityIR(
            (), "row_number", WindowFunctionRoleIR.WINDOW_FUNCTION
        )
        return
    if _case == 1:
        identity = WindowFunctionIdentityIR(
            ("vendor", "analytics"),
            "future_rank",
            WindowFunctionRoleIR.WINDOW_FUNCTION,
        )
        assert identity.namespace == ("vendor", "analytics")
        return
    invalid = (
        {"namespace": ["vendor"]},
        {"namespace": (1,)},
        {"namespace": ("",)},
        {"name": 1},
        {"name": ""},
        {"role": "window_function"},
    )[_case - 2]
    values: dict[str, object] = {
        "namespace": (),
        "name": "rank",
        "role": WindowFunctionRoleIR.WINDOW_FUNCTION,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowFunctionIdentityIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_order_item_constructor_validation_is_exact(_case: int) -> None:
    if _case < 3:
        direction, explicit = (
            (OrderDirectionIR.ASC, False),
            (OrderDirectionIR.ASC, True),
            (OrderDirectionIR.DESC, True),
        )[_case]
        item = _order_item(direction=direction, explicit=explicit)
        assert (item.direction, item.direction_is_explicit) == (
            direction,
            explicit,
        )
        return
    invalid = (
        {"expression": object()},
        {"direction": "ASC"},
        {"direction_is_explicit": 1},
        {"span": object()},
        {
            "direction": OrderDirectionIR.DESC,
            "direction_is_explicit": False,
        },
    )[_case - 3]
    values: dict[str, object] = {
        "expression": _field("id"),
        "direction": OrderDirectionIR.ASC,
        "direction_is_explicit": False,
        "span": SPAN,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowOrderItemIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_window_ir_spec_constructor_validation_is_exact(_case: int) -> None:
    if _case == 0:
        spec = _spec()
        assert spec.partition_by == () and len(spec.order_by) == 1
        return
    if _case == 1:
        field = _field("category")
        item = _order_item(field, direction=OrderDirectionIR.DESC, explicit=True)
        spec = _spec(partition_by=(field, field), order_by=(item, item))
        assert spec.partition_by == (field, field)
        assert spec.order_by == (item, item)
        return
    invalid = (
        {"partition_by": [_field("id")]},
        {"partition_by": (object(),)},
        {"order_by": [_order_item()]},
        {"order_by": (object(),)},
        {"order_by": ()},
        {"span": object()},
    )[_case - 2]
    values: dict[str, object] = {
        "partition_by": (),
        "order_by": (_order_item(),),
        "span": SPAN,
    }
    values.update(invalid)
    with pytest.raises((TypeError, ValueError)):
        WindowSpecIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(16))
def test_window_ir_call_constructor_validation_and_arity_are_exact(
    _case: int,
) -> None:
    if _case < 8:
        name = IDENTITIES[_case]
        if name in ZERO_ARGUMENT_IDENTITIES:
            arguments: tuple[ExpressionIR, ...] = ()
        elif name == "ntile":
            arguments = (_literal(4),)
        else:
            arguments = (_field("amount"),)
        call = _manual_window(name, arguments=arguments)
        assert call.identity.name == name
        assert call.arguments == arguments
        assert call.identity.namespace == ()
        return
    invalid_values: tuple[dict[str, object], ...] = (
        {"identity": _identity("row_number"), "arguments": (_literal(1),)},
        {"identity": _identity("ntile"), "arguments": ()},
        {"identity": _identity("lag"), "arguments": ()},
        {
            "identity": _identity("lead"),
            "arguments": tuple(_literal(index) for index in range(4)),
        },
        {"arguments": []},
        {"arguments": (object(),)},
        {"identity": object()},
        {"spec": object()},
    )
    values: dict[str, object] = {
        "span": SPAN,
        "value_type": INT_TYPE,
        "identity": _identity(),
        "arguments": (),
        "spec": _spec(),
    }
    values.update(invalid_values[_case - 8])
    with pytest.raises((TypeError, ValueError)):
        WindowCallIR(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize("_case", range(8))
def test_all_eight_window_identities_lower_with_source_identity_and_result_type(
    _case: int,
) -> None:
    name = IDENTITIES[_case]
    expression = _single_window_ir(name)
    expected_name, expected_nullability = RESULT_TYPES[name]
    assert expression.identity == WindowFunctionIdentityIR(
        namespace=(),
        name=name,
        role=WindowFunctionRoleIR.WINDOW_FUNCTION,
    )
    assert expression.value_type.canonical_name == expected_name
    assert expression.value_type.nullability is expected_nullability
    assert expression.spec.order_by[0].direction is OrderDirectionIR.DESC


@pytest.mark.parametrize("_case", range(5))
def test_zero_argument_identity_ir_shapes_are_exact(_case: int) -> None:
    name = ZERO_ARGUMENT_IDENTITIES[_case]
    expression = _single_window_ir(name)
    assert expression.identity.name == name
    assert expression.arguments == ()
    assert type(expression.arguments) is tuple
    assert expression.spec.partition_by[0].name == "category"  # type: ignore[attr-defined]
    assert expression.spec.order_by[0].expression.name == "id"  # type: ignore[attr-defined]


@pytest.mark.parametrize("_case", range(3))
def test_ntile_argument_ir_shape_is_exact(_case: int) -> None:
    value = (1, 4, 99)[_case]
    source = _single_window_source("ntile").replace("ntile(4)", f"ntile({value})")
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert len(expression.arguments) == 1
    argument = expression.arguments[0]
    assert isinstance(argument, LiteralIR)
    assert argument.value == value
    assert argument.value_type.canonical_kind is TypeKindIR.UNKNOWN
    assert argument.value_type.nullability is NullabilityIR.UNKNOWN


@pytest.mark.parametrize("_case", range(8))
def test_lag_lead_omitted_and_explicit_argument_shapes_are_exact(_case: int) -> None:
    calls = (
        "lag(amount)",
        "lag(amount, 2)",
        "lag(amount, 2, amount)",
        "lag(amount, 0, amount)",
        "lead(amount)",
        "lead(amount, 2)",
        "lead(amount, 2, amount)",
        "lead(amount, 0, amount)",
    )
    call = calls[_case]
    source = _single_window_source("lag").replace("lag(amount, 2, amount)", call)
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    expected_arity = call.count(",") + 1
    assert expression.identity.name == ("lag" if _case < 4 else "lead")
    assert len(expression.arguments) == expected_arity
    assert isinstance(expression.arguments[0], FieldRefIR)
    if expected_arity >= 2:
        offset = expression.arguments[1]
        assert isinstance(offset, LiteralIR)
        assert offset.value_type.canonical_kind is TypeKindIR.UNKNOWN
    if expected_arity == 3:
        assert isinstance(expression.arguments[2], FieldRefIR)
    function = "LAG" if _case < 4 else "LEAD"
    rendered_arguments = '"amount"'
    if expected_arity >= 2:
        rendered_arguments += f", {cast(LiteralIR, expression.arguments[1]).value}"
    if expected_arity == 3:
        rendered_arguments += ', "amount"'
    expected = (
        f"{function}({rendered_arguments}) OVER "
        '(PARTITION BY "category" ORDER BY "id" DESC)'
    )
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(6))
def test_partition_and_local_order_multiplicity_preserve_source_order_and_duplicates(
    _case: int,
) -> None:
    partitions = (
        (),
        ("category",),
        ("category", "category"),
        ("category", "id", "category"),
        (),
        ("id", "category"),
    )[_case]
    orders = (
        ("id",),
        ("id", "id"),
        ("id", "amount"),
        ("amount", "id", "amount"),
        ("id", "category", "id"),
        ("category", "category"),
    )[_case]
    partition_clause = ""
    if partitions:
        partition_clause = "            partition by:\n" + "".join(
            f"                {name}\n" for name in partitions
        )
    order_clause = "            order by:\n" + "".join(
        f"                {name}\n" for name in orders
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        "        result = row_number() window:\n" + partition_clause + order_clause
    )
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert tuple(item.name for item in expression.spec.partition_by) == partitions  # type: ignore[attr-defined]
    assert tuple(item.expression.name for item in expression.spec.order_by) == orders  # type: ignore[attr-defined]
    partition_sql = (
        ""
        if not partitions
        else "PARTITION BY " + ", ".join(f'"{name}"' for name in partitions) + " "
    )
    order_sql = ", ".join(f'"{name}" ASC' for name in orders)
    expected = f"ROW_NUMBER() OVER ({partition_sql}ORDER BY {order_sql})"
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(6))
def test_window_order_omitted_asc_desc_direction_facts_are_exact(_case: int) -> None:
    directions = (
        (None,),
        ("asc",),
        ("desc",),
        (None, "asc"),
        ("asc", "desc"),
        ("desc", None),
    )[_case]
    order_lines = "".join(
        "                id\n"
        if direction is None
        else f"                id {direction}\n"
        for direction in directions
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n"
        "        result = rank() window:\n"
        "            order by:\n" + order_lines
    )
    _, _, script_ir = _compile(source)
    expression = _window(_relation(script_ir).projections[0].expression)
    assert tuple(item.direction for item in expression.spec.order_by) == tuple(
        OrderDirectionIR.ASC if item in {None, "asc"} else OrderDirectionIR.DESC
        for item in directions
    )
    assert tuple(
        item.direction_is_explicit for item in expression.spec.order_by
    ) == tuple(item is not None for item in directions)
    expected_items = ", ".join(
        f'"id" {"ASC" if item in {None, "asc"} else "DESC"}' for item in directions
    )
    expected = f"RANK() OVER (ORDER BY {expected_items})"
    assert render_expression_sql(expression) == expected
    assert render_mysql_expression(expression) == expected.replace('"', "`")


@pytest.mark.parametrize("_case", range(4))
def test_multiple_window_outputs_lower_in_select_order(_case: int) -> None:
    count = _case + 2
    selected = IDENTITIES[:count]
    items = "".join(
        f"        output_{index} = {name}() window:\n"
        "            order by:\n"
        "                id\n"
        for index, name in enumerate(selected)
    )
    source = (
        _source_connector("postgresql") + "query windows:\n"
        "    from rows\n"
        "    select:\n" + items
    )
    _, _, script_ir = _compile(source)
    relation = _relation(script_ir)
    assert tuple(projection.name for projection in relation.projections) == tuple(
        f"output_{index}" for index in range(count)
    )
    assert (
        tuple(
            _window(projection.expression).identity.name
            for projection in relation.projections
        )
        == selected
    )
    sql = _sql_for(source, "postgresql")
    positions = tuple(sql.index(f"{SQL_NAMES[name]}() OVER") for name in selected)
    assert positions == tuple(sorted(positions))


@pytest.mark.parametrize("_case", range(8))
def test_grouped_group_key_and_aggregate_result_operands_lower_underlying_expressions(
    _case: int,
) -> None:
    windows_first = _case % 2 == 1
    _, _, script_ir = _compile(
        _grouped_source(dialect="postgresql", windows_first=windows_first)
    )
    relation = _relation(script_ir, "grouped")
    by_name = {item.name: item for item in relation.projections}
    group_name = by_name["group_name"].expression
    total = by_name["total"].expression
    group_rank = _window(by_name["group_rank"].expression)
    previous_total = _window(by_name["previous_total"].expression)
    check = _case // 2
    if check == 0:
        assert group_rank.spec.partition_by == (group_name,)
    elif check == 1:
        assert group_rank.spec.order_by[0].expression == total
        assert isinstance(total, AggregateCallIR)
    elif check == 2:
        assert previous_total.arguments == (
            total,
            previous_total.arguments[1],
            total,
        )
        assert isinstance(previous_total.arguments[1], LiteralIR)
    else:
        assert previous_total.spec.order_by[0].expression == total
        assert all(
            not (
                isinstance(item, FieldRefIR)
                and item.field is None
                and item.name in {"group_name", "total"}
            )
            for item in (
                *group_rank.spec.partition_by,
                *(order.expression for order in group_rank.spec.order_by),
                *previous_total.arguments,
                *(order.expression for order in previous_total.spec.order_by),
            )
        )


@pytest.mark.parametrize("_case", range(4))
def test_grouped_window_sql_is_same_level_without_subquery_or_alias_operands(
    _case: int,
) -> None:
    dialect = "postgresql" if _case % 2 == 0 else "mysql"
    windows_first = _case >= 2
    sql = _sql_for(
        _grouped_source(dialect=dialect, windows_first=windows_first), dialect
    )
    quote = '"' if dialect == "postgresql" else "`"
    assert "SELECT\n" in sql
    assert sql.count("SELECT") == 1
    assert "WITH " not in sql and "(SELECT" not in sql
    assert (
        f"RANK() OVER (PARTITION BY {quote}category{quote} "
        f"ORDER BY SUM({quote}amount{quote}) DESC)"
    ) in sql
    assert (
        f"LAG(SUM({quote}amount{quote}), 0, SUM({quote}amount{quote})) "
        f"OVER (ORDER BY SUM({quote}amount{quote}) ASC)"
    ) in sql
    over_clauses = tuple(
        fragment.partition(") AS ")[0]
        for fragment in sql.split("    ")
        if " OVER (" in fragment
    )
    assert over_clauses
    assert all(f"{quote}total{quote}" not in item for item in over_clauses)
    assert all(f"{quote}group_name{quote}" not in item for item in over_clauses)


@pytest.mark.parametrize("_case", range(4))
def test_downstream_window_fields_lower_through_ordinary_row_rules(_case: int) -> None:
    downstream_items = (
        "        result\n",
        "        windows.result\n",
        "        renamed = result\n",
        "        computed = result + 1\n",
    )
    source = (
        _single_window_source("row_number") + "query downstream:\n"
        "    from windows\n"
        "    select:\n" + downstream_items[_case]
    )
    _, _, script_ir = _compile(source)
    downstream = _relation(script_ir, "downstream")
    expression = downstream.projections[0].expression
    if _case < 3:
        assert isinstance(expression, FieldRefIR)
        assert expression.name == "result"
        assert expression.field is not None
        assert expression.field.name == "result"
        assert expression.qualifier == (() if _case != 1 else ("windows",))
    else:
        assert isinstance(expression, BinaryIR)
        assert isinstance(expression.left, FieldRefIR)
        assert expression.left.field is not None
        assert expression.left.name == "result"


@pytest.mark.parametrize("_case", range(4))
def test_final_order_window_aliases_render_as_aliases(_case: int) -> None:
    dialect = "postgresql" if _case % 2 == 0 else "mysql"
    grouped = _case >= 2
    if grouped:
        source = _grouped_source(dialect=dialect, windows_first=False)
        alias = "group_rank"
    else:
        source = (
            _single_window_source("row_number", dialect=dialect) + "    order by:\n"
            "        result desc\n"
        )
        alias = "result"
    _, _, script_ir = _compile(source)
    relation = _relation(script_ir)
    order = next(
        item
        for item in relation.order_by
        if isinstance(item.expression, FieldRefIR) and item.expression.name == alias
    )
    assert isinstance(order.expression, FieldRefIR)
    assert order.expression.field is None
    assert order.expression.qualifier == ()
    quote = '"' if dialect == "postgresql" else "`"
    sql = _sql_for(source, dialect)
    assert f"\n    {quote}{alias}{quote} " in sql
    final_order = sql.rpartition("\nORDER BY\n")[2]
    assert "OVER (" not in final_order


def _expected_single_window_sql(identity: str, *, dialect: str) -> str:
    quote = '"' if dialect == "postgresql" else "`"
    if identity in ZERO_ARGUMENT_IDENTITIES:
        arguments = ""
    elif identity == "ntile":
        arguments = "4"
    elif identity == "lag":
        arguments = f"{quote}amount{quote}, 2, {quote}amount{quote}"
    else:
        arguments = f"{quote}amount{quote}, 0, {quote}amount{quote}"
    expression = (
        f"{SQL_NAMES[identity]}({arguments}) OVER "
        f"(PARTITION BY {quote}category{quote} ORDER BY {quote}id{quote} DESC)"
    )
    return f"SELECT\n    {expression} AS {quote}result{quote}\nFROM {quote}rows{quote}"


@pytest.mark.parametrize("_case", range(8))
def test_postgres_exact_sql_bytes_for_all_identities(_case: int) -> None:
    identity = IDENTITIES[_case]
    source = _single_window_source(identity, dialect="postgresql")
    assert _sql_for(source, "postgresql") == _expected_single_window_sql(
        identity, dialect="postgresql"
    )


@pytest.mark.parametrize("_case", range(8))
def test_mysql_exact_sql_bytes_for_all_identities(_case: int) -> None:
    identity = IDENTITIES[_case]
    source = _single_window_source(identity, dialect="mysql")
    assert _sql_for(source, "mysql") == _expected_single_window_sql(
        identity, dialect="mysql"
    )


@pytest.mark.parametrize("_case", range(6))
def test_backend_identifier_quoting_and_escaping_differences_are_exact(
    _case: int,
) -> None:
    names = (
        "simple",
        'double"quote',
        "back`tick",
        "select",
        "with space",
        "Unicode_λ",
    )
    name = names[_case]
    expression = _manual_window(
        "row_number",
        spec=_spec(
            partition_by=(_field(name),),
            order_by=(
                _order_item(
                    _field(name, qualifier=("owner",)),
                    direction=OrderDirectionIR.DESC,
                    explicit=True,
                ),
            ),
        ),
    )
    postgres = render_expression_sql(expression)
    mysql = render_mysql_expression(expression)
    postgres_name = name.replace('"', '""')
    mysql_name = name.replace("`", "``")
    assert f'PARTITION BY "{postgres_name}"' in postgres
    assert f'ORDER BY "owner"."{postgres_name}" DESC' in postgres
    assert f"PARTITION BY `{mysql_name}`" in mysql
    assert f"ORDER BY `owner`.`{mysql_name}` DESC" in mysql
    assert postgres != mysql


@pytest.mark.parametrize("_case", range(8))
def test_postgres_malformed_window_ir_becomes_pie_b1000(_case: int) -> None:
    variants = range(6) if _case == 4 else range(4) if _case == 6 else range(1)
    for variant in variants:
        result = emit_postgres_sql(
            _malformed_script_ir(
                _case,
                dialect="postgresql",
                variant=variant,
            )
        )
        assert result.artifacts == ()
        assert len(result.diagnostics) == 1
        diagnostic = result.diagnostics[0]
        assert diagnostic.code == "PIE-B1000"
        assert diagnostic.location.path == "slice15.pietto"
        assert "PostgreSQL SQL emission is not implemented" in diagnostic.message


@pytest.mark.parametrize("_case", range(8))
def test_mysql_malformed_window_ir_becomes_pie_b1000(_case: int) -> None:
    variants = range(6) if _case == 4 else range(4) if _case == 6 else range(1)
    for variant in variants:
        result = emit_mysql_sql(
            _malformed_script_ir(_case, dialect="mysql", variant=variant)
        )
        assert result.artifacts == ()
        assert len(result.diagnostics) == 1
        diagnostic = result.diagnostics[0]
        assert diagnostic.code == "PIE-B1000"
        assert diagnostic.location.path == "slice15.pietto"
        assert "MySQL SQL emission is not implemented" in diagnostic.message


@pytest.mark.parametrize("_case", range(4))
def test_unrelated_missing_semantic_facts_preserve_pie_i1000(_case: int) -> None:
    source = (
        _source_connector("postgresql") + "query ordinary:\n"
        "    from rows\n"
        "    select:\n"
        "        id\n"
        "        copied = amount\n"
        "        computed = id + 1\n"
        "        normalized = lower(category)\n"
    )
    parsed = parse_source(source, path="slice15-missing.pietto")
    assert parsed.diagnostics == () and parsed.ast is not None
    semantic = analyze(parsed.ast)
    assert semantic.diagnostics == ()
    relation = cast(QueryDef | TableDef, parsed.ast.definitions[-1])
    expression = relation.select_items[_case].expression
    value_types = dict(semantic.model.expression_value_types)
    assert value_types.pop(expression, None) is not None
    missing_model = dataclasses.replace(
        semantic.model,
        expression_value_types=value_types,
    )
    result = lower_expr(expression, missing_model)
    assert result.expression is None
    assert len(result.diagnostics) == 1
    assert result.diagnostics[0].code == "PIE-I1000"
    assert "expression value type" in result.diagnostics[0].message


SIGNATURE_OPERANDS = (
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Float",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "0",
        "no_argument",
        "Float",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1",
        "positive_int_literal",
        "Int",
        "non_null",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1..3",
        "bounded_value_optional_offset_default",
        "T",
        "any_nullable_0_2_or_default_omitted_2",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
    (
        "1..3",
        "bounded_value_optional_offset_default",
        "T",
        "any_nullable_0_2_or_default_omitted_2",
        "WINDOW",
        "window_result",
        "mandatory_local_order",
    ),
)
LOWERING_OPERANDS = ("WindowCallIR", "OVER", "partition_by", "order_by")


@pytest.mark.parametrize("_case", range(24))
def test_window_capability_fact_inventory_keys_evidence_and_privacy_are_exact(
    _case: int,
) -> None:
    facts = capability_windows._WINDOW_CAPABILITY_FACTS
    assert capability_windows.__all__ == ()
    assert type(facts) is tuple and len(facts) == 24 and len(set(facts)) == 24
    fact = facts[_case]
    assert type(fact) is CapabilityFact
    assert fact.key.domain is CapabilityDomain.WINDOW_FUNCTION
    assert fact.support is CapabilitySupport.SUPPORTED
    assert fact.disposition.kind is CapabilityDispositionKind.NONE
    assert fact.key.extension is None
    identity_index = _case % 8
    assert fact.key.subject == IDENTITIES[identity_index]
    if _case < 8:
        assert fact.key.operation == "signature"
        assert fact.key.context == "window_signature"
        assert fact.key.dialect is None
        assert fact.key.operands == SIGNATURE_OPERANDS[_case]
        assert tuple(item.source for item in fact.evidence) == (
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            CapabilityEvidenceSource.IR,
        )
        assert fact.evidence[-1].source_path == "src/pietto/ir/lowering.py"
        assert fact.evidence[-1].source_reference == "_lower_window_expr"
    else:
        postgres = _case < 16
        dialect = "postgresql" if postgres else "mysql"
        backend = "postgresql" if postgres else "private-mysql"
        source_path = (
            "src/pietto/sql/expressions.py"
            if postgres
            else "src/pietto/sql/mysql_expressions.py"
        )
        source_reference = (
            "_render_window_call" if postgres else "_render_mysql_window_call"
        )
        assert fact.key.operation == "lowering"
        assert fact.key.context == "window_lowering"
        assert fact.key.dialect == dialect
        assert fact.key.operands == LOWERING_OPERANDS
        assert len(fact.evidence) == 1
        evidence = fact.evidence[0]
        assert evidence.source is CapabilityEvidenceSource.BACKEND
        assert (
            evidence.source_path,
            evidence.source_reference,
            evidence.dialect,
            evidence.backend,
        ) == (source_path, source_reference, dialect, backend)


def _lookup(key: CapabilityKey) -> Found | Absent | Unknown | Conflict:
    facts, complete, reason = capability_windows.window_lookup_inputs(key)
    return lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=reason,
    )


@pytest.mark.parametrize("_case", range(8))
def test_window_capability_lookup_found_absent_unknown_and_conflict_are_exact(
    _case: int,
) -> None:
    if _case < 3:
        fact = capability_windows._WINDOW_CAPABILITY_FACTS[(0, 8, 16)[_case]]
        result = _lookup(fact.key)
        assert isinstance(result, Found)
        assert result.fact is fact
        return
    if _case == 3:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="row_number",
            operation="signature",
            operands=(
                "0",
                "no_argument",
                "Float",
                "non_null",
                "WINDOW",
                "window_result",
                "mandatory_local_order",
            ),
            context="window_signature",
        )
        result = _lookup(key)
        assert isinstance(result, Absent)
        assert result.key == key
        assert result.reason is CapabilityReasonCode.NO_CATALOG_ENTRY
        return
    if _case == 4:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="future_rank",
            operation="signature",
            operands=SIGNATURE_OPERANDS[0],
            context="window_signature",
        )
    elif _case == 5:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="sqlite",
        )
    elif _case == 6:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="postgresql",
            extension="vendor.rank",
        )
    else:
        first = capability_windows._WINDOW_CAPABILITY_FACTS[0]
        second = dataclasses.replace(
            first,
            evidence=(
                CapabilityEvidence(
                    CapabilityEvidenceSource.TEST,
                    SELF_REL,
                    "synthetic conflicting window evidence",
                ),
            ),
        )
        result = lookup_capability(
            first.key,
            (first, second),
            domain_complete=True,
        )
        assert isinstance(result, Conflict)
        assert result.reason is CapabilityReasonCode.CONFLICTING_EVIDENCE
        assert result.evidence == (first, second)
        return
    result = _lookup(key)
    assert isinstance(result, Unknown)
    assert result.reason is CapabilityReasonCode.NOT_EVIDENCED


@pytest.mark.parametrize("_case", range(4))
def test_window_capability_facts_do_not_authorize_compiler_acceptance(
    _case: int,
) -> None:
    production_paths = (
        "src/pietto/semantic/expressions.py",
        "src/pietto/semantic/window_analysis.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/expressions.py",
    )
    source = _read(production_paths[_case])
    assert "capability_windows" not in source
    assert "window_lookup_inputs" not in source
    if _case == 0:
        unsupported = (
            _source_connector("postgresql") + "query invalid:\n"
            "    from rows\n"
            "    select:\n"
            "        result = row_number()\n"
        )
        parsed = parse_source(unsupported, path="slice15-nonauthority.pietto")
        assert parsed.ast is not None
        semantic = analyze(parsed.ast)
        assert semantic.diagnostics


def test_public_ir_sql_semantic_cli_json_and_metadata_surfaces_are_unchanged() -> None:
    private_names = {
        "WindowFunctionRoleIR",
        "WindowFunctionIdentityIR",
        "WindowOrderItemIR",
        "WindowSpecIR",
        "WindowCallIR",
    }
    assert private_names.isdisjoint(public_ir.__all__)
    assert all(not hasattr(public_ir, name) for name in private_names)
    assert "emit_mysql_sql" not in public_sql.__all__
    assert not hasattr(public_sql, "emit_mysql_sql")
    assert "CapabilityDomain" not in public_semantic.__all__
    assert "window_lookup_inputs" not in public_semantic.__all__
    assert capability_windows.__all__ == ()
    assert all(
        "WindowCallIR" not in _read(path)
        for path in (
            "src/pietto/cli.py",
            "src/pietto/_metadata/model.py",
            "src/pietto/_project/model.py",
        )
    )
    assert not hasattr(pietto, "__version__")


@pytest.mark.parametrize("_case", range(12))
def test_frames_named_windows_qualify_extension_and_later_identity_boundaries_are_locked(
    _case: int,
) -> None:
    spec = _read(SPEC_REL)
    normalized = " ".join(spec.split())
    boundary_terms = (
        "Frames",
        "`ROWS`",
        "`RANGE`",
        "`GROUPS`",
        "named windows",
        "window inheritance",
        "`QUALIFY`",
        "`first_value`",
        "`last_value`",
        "`nth_value`",
        "extension-specific lowering",
        "third or additional dialects",
    )
    assert boundary_terms[_case] in normalized
    if _case == 0:
        assert tuple(field.name for field in dataclasses.fields(WindowSpecIR)) == (
            "partition_by",
            "order_by",
            "span",
        )
    elif 1 <= _case <= 5:
        assert all(
            token not in {field.name for field in dataclasses.fields(WindowSpecIR)}
            for token in ("frame", "rows", "range", "groups", "name", "inherits")
        )
    elif _case == 6:
        assert "QUALIFY" not in _read("grammar/Pietto.g4")
    elif 7 <= _case <= 9:
        assert boundary_terms[_case].strip("`") not in IDENTITIES
    else:
        key = CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject="rank",
            operation="lowering",
            operands=LOWERING_OPERANDS,
            context="window_lowering",
            dialect="postgresql" if _case == 10 else "sqlite",
            extension="vendor.rank" if _case == 10 else None,
        )
        result = _lookup(key)
        assert isinstance(result, Unknown)
        assert result.reason is CapabilityReasonCode.NOT_EVIDENCED


def test_generated_golden_fixture_package_dependency_and_version_boundaries_are_locked() -> (
    None
):
    paths = _repository_paths()
    assert (
        len(paths),
        sum(path.endswith(".py") for path in paths),
        sum(path.endswith(".md") for path in paths),
        sum(path.startswith("tests/test_") and path.endswith(".py") for path in paths),
        _top_level_test_function_count(paths),
    ) == (912, 561, 255, 458, 5088)
    generated = tuple(
        path for path in paths if path.startswith("src/pietto/generated/")
    )
    goldens = tuple(path for path in paths if path.startswith("tests/fixtures/golden/"))
    assert len(generated) == 8
    assert (
        len(goldens),
        sum(path.endswith(".sql") for path in goldens),
        sum(path.endswith(".json") for path in goldens),
    ) == (37, 32, 5)
    project = tomllib.loads(_read("pyproject.toml"))
    assert project["project"]["version"] == "0.1.0"
    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["build-system"] == {
        "requires": ["uv_build>=0.11.32,<0.12.0"],
        "build-backend": "uv_build",
    }


def test_reader_hash_dag_allowlist_and_fixed_point_are_exact() -> None:
    assert (
        len(ADDED_PATHS),
        len(CORE_MODIFIED_PATHS),
        len(READER_PATHS),
        len(MODIFIED_PATHS),
        len(set((*ADDED_PATHS, *MODIFIED_PATHS))),
    ) == (2, 1, 23, 24, 26)
    assert set(ADDED_PATHS).isdisjoint(MODIFIED_PATHS)
    assert all((REPO_ROOT / path).is_file() for path in (*ADDED_PATHS, *MODIFIED_PATHS))
    added_manifest = _path_manifest("A", ADDED_PATHS)
    modified_manifest = _path_manifest("M", MODIFIED_PATHS)
    assert (len(added_manifest), hashlib.sha256(added_manifest).hexdigest()) == (
        120,
        "9512adfa6b71173d89b1a49066ab53a072ef43667245a809dd8dcc3994b75046",
    )
    assert (len(modified_manifest), hashlib.sha256(modified_manifest).hexdigest()) == (
        1832,
        "bdc6ca87af8ec954bd2e2db19f9b887a128c2eb2415043f63af6021a9abcd903",
    )
    combined = added_manifest + modified_manifest
    assert (len(combined), hashlib.sha256(combined).hexdigest()) == (
        1952,
        "5b4b7fa64e84a498437e466d6f96087ce4ebb1503d9215d9b016cbe2013be088",
    )
    assert len(TOPOLOGICAL_PHASE53_READERS) == 13
    assert len(set(TOPOLOGICAL_PHASE53_READERS)) == 13
    assert set(TOPOLOGICAL_PHASE53_READERS) < set(READER_PATHS)
    dirty = _dirty_paths()
    assert dirty in (
        set(),
        set((*ADDED_PATHS, *MODIFIED_PATHS)),
        _phase54_slice2_allowlist(),
    )
    assert _git_output(["diff", "--cached", "--name-only"]) == ""


def test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact() -> (
    None
):
    names, cardinalities = _test_manifest()
    assert names == EXPECTED_TEST_NAMES
    assert cardinalities == EXPECTED_CARDINALITIES
    assert sum(cardinalities) == 208

    source_reader = (
        "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py"
    )
    focused = cast(tuple[str, ...], _module_literal(source_reader, "FOCUSED_OPERANDS"))
    overlay = cast(tuple[str, ...], _module_literal(source_reader, "DIRTY_OVERLAY"))
    assert focused[0] == SELF_REL
    focused_payload = ("\n".join(focused) + "\n").encode("utf-8")
    assert (
        len(focused),
        len({item.split("::", 1)[0] for item in focused}),
        sum("::" not in item for item in focused),
        sum("::" in item for item in focused),
        len(focused_payload),
        hashlib.sha256(focused_payload).hexdigest(),
    ) == (
        134,
        80,
        14,
        120,
        15130,
        "fb685c521c70d879e0e3e751c434cf142700d82a66976961ca8036e8965b3429",
    )
    overlay_payload = ("\n".join(overlay) + "\n").encode("utf-8")
    assert (
        len(overlay),
        len({item.split("::", 1)[0] for item in overlay}),
        len(overlay_payload),
        hashlib.sha256(overlay_payload).hexdigest(),
    ) == (
        185,
        137,
        23628,
        "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26",
    )
    formatter_manifest = _path_manifest("F", FORMATTER_PATHS)
    assert (
        len(FORMATTER_PATHS),
        len(formatter_manifest),
        hashlib.sha256(formatter_manifest).hexdigest(),
    ) == (
        21,
        1591,
        "f907acc7860688d52621283a1c54c88cec6c26cb1346059f31d5540f895f3697",
    )
    assert 10784 - len(overlay) == 10599
    assert 4557 + sum(cardinalities) == 4765


@pytest.mark.parametrize("_case", range(8))
def test_dirty_clean_depth_one_shallow_and_negative_topology_boundaries_are_exact(
    _case: int,
) -> None:
    plan = _read(PLAN_REL)
    clauses = (
        "full-history clean",
        "genuine depth-one",
        "`pull_request` checkout",
        "genuine shallow",
        "stale",
        "dirty",
        "staged",
        "mismatched variants fail closed",
    )
    normalized = " ".join(plan.split())
    assert " ".join(clauses[_case].split()) in normalized
    if _case == 0:
        dirty = _dirty_paths()
        assert dirty in (
            set(),
            set((*ADDED_PATHS, *MODIFIED_PATHS)),
            _phase54_slice2_allowlist(),
        )
        assert _git_output(["diff", "--cached", "--name-only"]) == ""


def test_gate2_evidence_gate3_publication_and_slice16_stop_contract_are_locked() -> (
    None
):
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    normalized_spec = " ".join(spec.split())
    normalized_plan = " ".join(plan.split())
    assert "Gate 2 final scope is exactly `A3/M73/D0`" in normalized_plan
    assert "exactly one write-mode Ruff invocation" in spec
    assert "leaves exactly 76 paths unstaged" in plan
    assert PUBLICATION_BRANCH in spec and PUBLICATION_BRANCH in plan
    assert spec.count(PUBLICATION_TITLE) == 1
    assert plan.count(PUBLICATION_TITLE) == 1
    assert "unique natural exact-head PR CI" in normalized_spec
    assert "unique natural exact-head main CI" in normalized_spec
    assert "No direct-main push, amend, rebase, force-push" in normalized_spec
    assert "Phase 53 remains `ACTIVE`" in normalized_spec
    assert "Slice 16 remains `UNSTARTED`" in normalized_spec
    assert "SLICE16_GATE0_GATE1" in normalized_spec
    assert BASE_HEAD == "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
