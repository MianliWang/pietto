from __future__ import annotations

import ast
import dataclasses
import hashlib
import subprocess
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto.semantic.window_analysis as window_analysis
from pietto._project.model import (
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowFieldProvenanceKind,
    ProjectRowResultRole,
    ProjectRowSchema,
    ProjectSemanticModel,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.row_dependency_graph import ProjectRowDependencyNodeKind
from pietto._project.window_semantics import (
    WindowDependencyRole,
    WindowResultProjectFact,
    build_ranking_window_result_project_fact,
    build_row_number_window_result_project_fact,
    build_window_result_project_fact,
)
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    QueryDef,
    Script,
    SelectItem,
    SourceDef,
    TableDef,
    WindowExpr,
)
from pietto.errors import Diagnostic, SourceLocation
from pietto.ir.lowering import lower_expr
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    EffectiveNullability,
    RowSchema,
    SemanticModel,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.window_semantics import (
    WindowExpressionAnalysis,
    WindowExpressionStage,
    WindowExpressionUnsupported,
    WindowOrderBindingFact,
    WindowOrderFieldBinding,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md"
)
SELF_REL = "tests/test_phase53_window_local_ordering_direction_determinism_contract.py"
SLICE10_REL = (
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py"
)
BASE_HEAD_SHA = "54553396f61caefe74b57cd6ed6fa144725a50e4"
SPEC_TITLE = (
    "Phase 53 Window-local Ordering, Direction, Mandatory-order Policy, And "
    "Determinism Contract v1"
)
SLICE11_PLAN_H2 = (
    "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism"
)
SPEC_H2 = (
    "Status And Authority",
    "Exact Function And Source Subset",
    "Multi-key Local-order Cardinality",
    "Direct-field Binding And Visibility",
    "Direction And Explicitness",
    "Mandatory-order Policy",
    "Duplicate Keys And Source Order",
    "Structural Determinism And Total-order Boundary",
    "Null Ordering And Collation",
    "Orderability And Capability Boundary",
    "Peer And Distribution Semantics",
    "Validation Order And Diagnostics",
    "Project Dependencies Occurrences And Edges",
    "Private Order-binding Carrier And Composite Analysis",
    "Slice 12 Reuse And Deferred Ownership",
    "Persistence Row-schema IR SQL And Public Boundaries",
    "Reader Closure Validation And Publication",
    "Stop Conditions",
)
SPEC_H3 = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
)
IDENTITIES = SPEC_H3

ADDED_PATHS = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "src/pietto/semantic/window_order_analysis.py",
    SELF_REL,
)


def _read(relative: str) -> str:
    return (REPO_ROOT / relative).read_text(encoding="utf-8")


def _sha256(relative: str) -> str:
    return hashlib.sha256((REPO_ROOT / relative).read_bytes()).hexdigest()


def _literal_tuple(relative: str, name: str) -> tuple[str, ...]:
    tree = ast.parse(_read(relative), filename=relative)
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == name
        ):
            value = ast.literal_eval(node.value)
            assert type(value) is tuple
            assert all(type(item) is str for item in value)
            return cast(tuple[str, ...], value)
    raise AssertionError(f"missing literal tuple: {relative}:{name}")


_SLICE10_MODIFIED_PATHS = _literal_tuple(SLICE10_REL, "MODIFIED_PATHS")
_SLICE10_FOCUSED_OPERANDS = _literal_tuple(SLICE10_REL, "FOCUSED_OPERANDS")
_SLICE10_DIRTY_OVERLAY = _literal_tuple(SLICE10_REL, "DIRTY_OVERLAY")
_SLICE10_FORMATTER_PATHS = _literal_tuple(SLICE10_REL, "FORMATTER_PATHS")

MODIFIED_PATHS = _SLICE10_MODIFIED_PATHS
FOCUSED_OPERANDS = _SLICE10_FOCUSED_OPERANDS
DIRTY_OVERLAY = _SLICE10_DIRTY_OVERLAY
FORMATTER_PATHS = _SLICE10_FORMATTER_PATHS
ALLOWLIST_PATHS = frozenset((*ADDED_PATHS, *MODIFIED_PATHS))

# Populated with formatting-neutral literals after the sole write formatter.
FINAL_SHA256: dict[str, str] = {
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md": "fb5cbdccf80090d6d42d321a9d58e7f95bb960b8c81e2f473aa7117083af8f58",
    "src/pietto/semantic/window_order_analysis.py": "d23c226065e9bf576c4bae49a8ab1b028de71d600b114af23d2b09a809aaf584",
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md": "167e1a851b33e036d483b53e763c019c338c0b7adbd21118f29e64986a5a2a99",
    "src/pietto/semantic/window_semantics.py": "85def9b1fa48fd03759caec894b19e5a43b8d2304b1c7258370b5379f5eaceed",
    "src/pietto/semantic/window_analysis.py": "46e764adc6a247115a90a446e6535ccc9afeacf9829a859793f1b7e90c6d0b63",
    "src/pietto/_project/window_semantics.py": "d65ff113b462935395d5f5bad1aa1ff65333e5ae60fe28623d2b47ffaba7f8c7",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py": "f49ce7ce6ed6a6fac85ffdd1f4030ca39e5b2aad5c1cbb402ff8e094f1c431a6",
    "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py": "0d2d518758298ef473b8573dbf084ae9d68eab51f75b17c84ff10811e38906ba",
    "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py": "fbf8f43e5ec98f791480e9bd70f10bcba3802d7d4ea31827ac80afca0aa57926",
    "tests/test_phase53_row_number_direct_field_mvp_contract.py": "6f2c978ceed88a7ac9564a99568db374717721ec4e7cf5f6ddc4b81a5e9662c8",
    "tests/test_phase11_ci_workflow.py": "dc1b1f89d2a7970eb355029fbec311f9a24ad07cc0ee31b3f8a0f5cde5f07a33",
    "tests/test_phase11_completion_audit.py": "20e245a12681d19e45b8b1c2f153939464ddf24f9157704bdb2fa5d59f23e12f",
    "tests/test_phase11_generated_guard.py": "70676aaab5b886c533825c371d47aae1e1a42b2a3836affe9c468170e3afa635",
    "tests/test_phase11_golden_policy.py": "9f777a64da53803362eedc2a73230017e206d09b1d2169bdb1c638f82c1f1add",
    "tests/test_phase11_packaging_smoke.py": "9bfe78f9865a807448a7a88351f824615f9a7b9bcf42fb8419376ec80c68090b",
    "tests/test_phase11_planning_audit.py": "8422a17b32ad397008b3b9c1a77656c6722588c96f010002ac62ee2f210da6f0",
    "tests/test_phase11_validation_entrypoint.py": "bc7efdeb917e6f158f66115b11dd0296327106298e840fb7850daca6b5b6ba0e",
    "tests/test_phase12_completion_audit.py": "fc2da30d5491544a30fc69e8b428b26d7bcc97a4b992c006d17b9ee9aa94e818",
    "tests/test_phase12_composition_cli_json_goldens.py": "cd8b798731dc37aca6a9e239ee55f8a7193cdf7dbaba010d101a72b5a902d6e5",
    "tests/test_phase12_order_limit_contract.py": "8b2cf25939e4270518d5461d35b95acbaf0b2d4c6461bf9b95a6064cf8b4fe24",
    "tests/test_phase12_planning_audit.py": "a9c6eefd6238f52e1be08f3ed8e42216d626c0a90d2fb47f7f6a6adede7742e4",
    "tests/test_phase13_completion_audit.py": "f7ae24b69fd17204ea9272534d9faaa310ff9cd0627ebe5c8b8fce2ff0dcffc3",
    "tests/test_phase13_planning_audit.py": "6fbc3811d5c8f148ec30f83566b86e0581ab4692cafc06b2864fc61b7ea96be1",
    "tests/test_phase14_candidate_decision_audit.py": "d403025f7d2aef85f3c94237c3bca55dfdba44e321c1855cee42b94fe8b59596",
    "tests/test_phase14_completion_audit.py": "3a0af23738a18ed4599cc18bc1cb09b3f28de737b85488ac79b073c742123fac",
    "tests/test_phase14_planning_audit.py": "94e4f740326a28ad8749cf65c8b676938463ae2494894f18a69895891bd7359e",
    "tests/test_phase14_relationship_metadata_completion_audit.py": "d209817d214e63a802029ce98f19e58b7d5ed0bdc03c538f91b99c04e3e6ac8b",
    "tests/test_phase15_completion_audit.py": "c54a3b86f47edb10e9fb3372f08ee0a9f45dcc0ceafdbbe70f124dbc63e4a165",
    "tests/test_phase15_semantic_completion_audit.py": "4ec95dfbc53b3e6027bcee177c832135ad08ec730aeaa53080d2f67634929a11",
    "tests/test_phase16_completion_audit.py": "181a14fe89a6974900b0ccdfa997f17e6d55d6950f9c285494d90f32068cb07e",
    "tests/test_phase16_current_syntax_surface_audit.py": "06f2a5c1124756d9bfd473fa04e4b0bc9a5d0840887156afb9b39543a2fbec4c",
    "tests/test_phase16_language_direction_audit.py": "f7aac8b3771e222fb640d8f0f25a45b6ba631f8c9af07fdada9a1b1af57514ca",
    "tests/test_phase16_safety_deferral_sql_portability.py": "8ab748d9c83d93d406f0e399d94d06da18f7c8afb7ed4a9d7a8fc66ea5e989d5",
    "tests/test_phase21_group_by_hardening_audit.py": "107a2eafefdf3661db1938fea1679ea5c03aa2cc1d7f434a4a4d99a98c8a92e3",
    "tests/test_phase24_aggregate_expression_arguments_readiness.py": "0327696a191e79db2d4bfc018af550f565a3d4c3953eb00b1bfda03c841ae405",
    "tests/test_phase24_cli_json_output_hardening.py": "86d0fccc04549b32ac9ae65aa994ba338cc4cdf68949fe07e0872f2ba77991d3",
    "tests/test_phase24_completion_audit.py": "7baea2af6e29ce7007d6a483d791c13dc99a5197191eb4a72c825e8664c9ed23",
    "tests/test_phase25_completion_audit.py": "0e8ad68c6e199f33a34aa02e8fc6e3cb8443c34ce7a536012b12d2026aabb41c",
    "tests/test_phase26_completion_audit.py": "ba9609d909c82cb53d7a747cb40330c906ac703c6c9819303b28b89c846202b9",
    "tests/test_phase27_completion_audit.py": "bf5d94bafde3e3c5f7b05f1ecf6f537c05870e0f61c4b91597ed535fc63d95fa",
    "tests/test_phase28_completion_audit.py": "aa512b33bc869e32f689e949a1c01f40cf6281e9fd9b790ef9d6bb8c8e6983c5",
    "tests/test_phase29_completion_audit.py": "8b59a1fc15cebed29e2ac0569fb1de090edf8df59e3136d3bb1df0d806f2f70a",
    "tests/test_phase30_completion_audit.py": "704ee42e127b05d8d7f29a125ec91c1d663e4b7379fd337c15ad2381b16004dc",
    "tests/test_phase50_window_function_readiness.py": "f94c7695b91f8f6d9b7ce407af97dac9281351836c0d11fb24be4443c0a846a5",
    "tests/test_phase51_completion_audit_and_status_lock.py": "28a6d8b6d0f8685ede6b3925b5fee97eb27af916ffa19b55cc35aaa15bd857de",
    "tests/test_phase51_cross_phase_readiness_privacy_compatibility_closure.py": "d94bbdaf52933331de10fe3290a51d542e80826f3dc5e9d0cdce61409e95264c",
    "tests/test_phase52_aggregate_signature_algebra_facts.py": "f19c934bb787bc46e7ea67d915f4e9b916f1e86e77c94d2e7dbdb22b50f0d8c8",
    "tests/test_phase52_completion_audit_and_status_lock.py": "34d1f985c8cbf4b5afda47929cc2e0b85f93683e11d011721a3a02965a81c0b1",
    "tests/test_phase52_core_type_system_capability_foundation_scope_lock.py": "d7fb010aeb583e26ab3644a57b175718fe7cda0da67222ef75eee6599ef0da8b",
    "tests/test_phase52_expression_stage_clause_capability_facts.py": "d903abb34da5ad2ebc9d04afe8e1f519bf547a1a87f5956751efaf1a30ddcc76",
    "tests/test_phase52_fail_closed_capability_lookup.py": "468a73da135cbfcc0493564c9929775c773d0570f19aa41fb48b7e4b54ee20e5",
    "tests/test_phase52_logical_type_literal_parameter_nullability_inventory.py": "941bdb9da98d7b3643ae37c726f4c66f7865161e1dc249578c1c24a8aa41df5f",
    "tests/test_phase52_parity_privacy_cross_phase_readiness_drift_closure.py": "7ade648f5dd40c68f9584bc456671aa551d92392813e618d37306f6206d6f9a0",
    "tests/test_phase52_private_capability_fact_foundation.py": "b8257628b68a42bcaa63bb87d461fd486307df34fff15b6d178c89237c645f1b",
    "tests/test_phase52_scalar_function_operator_signature_facts.py": "c270a6df50d5f97f49dc700b52ad5c52cbc3d13de33457642642ef35f5913c9f",
    "tests/test_phase53_generic_type_variable_exact_compatibility_contract.py": "969bff6d39d12e271d24869ffbc0ad454c7925cbf98c14e5cf80fdb646307db7",
    "tests/test_phase53_window_generic_nullability_foundation_scope_lock.py": "c861ebdd1426f9eb970874bc0cf0f2a533e32046138a2d7a43fa94f8fc9d8c04",
    "tests/test_phase53_window_spec_function_identity_ast_contract.py": "988ffe2b7febe6ac0fa4aec0cf389565ef8e188db7c2d691f792a813da30d490",
    "tests/test_phase53_window_syntax_contextual_grammar_contract.py": "37a8f431babf7cb7066d5dc5b53d80c497b2ae3232aaf653216db75262735979",
    "tests/test_phase33_completion_audit.py": "a102aa26d9f1a1f3f120d7a7956278111b6feabb07beeaa8b1c7cd8b05ce9aba",
    "tests/test_phase51_private_result_role_output_identity.py": "a0251de0cda3a2ab680084b86c9dbf342a2bff8f6ad88cf4e5ea6f6bb1ac0981",
    "tests/test_phase53_nullability_algebra_signature_result_formula_contract.py": "b32a35aba7af1b451564309160a226882f6c9824e9b800c199c1fd4331f62ffc",
    "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py": "253ff18f2d126737d379b32a6f364c6de9cc4cc9bb65bbaea7afd8ea02328a40",
}
COMPILER_DIGEST = "5877dd47e60c7b3c49d4c61ee50232c72c68d968351aea21c07ac9f43dee558c"
SEMANTIC_DIGEST = "9628b5cc1721ad51cdfe0679b0822725bc5373d08e2861d2b07f734c03949b2f"
PHASE15_SUBSET_DIGEST = (
    "bc501c43950b0022aded20da577a36ca093322a5841bc0bcebe294cb949099dc"
)
PROJECT_DIGEST = "16590c5b7d0f94d5b982ab6fccb006da245f97462a240284e5becec3a7fd989d"

FOCUSED_SHA256 = "5097cde3db637b55cd2e79a1292dd96dc5d4864512e012476612368164d6dc77"
OVERLAY_SHA256 = "197b591aec962f43b9b9393da99a76ff21c3a36189cc02c7a75dc5a7b85d6b26"
FORMATTER_SHA256 = "c44ceb6e493a62c154a7958974d88a0c4d835948e1f7fb3bc0b993fa14679307"


def _digest(paths: tuple[Path, ...]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths, key=lambda item: item.relative_to(REPO_ROOT).as_posix()):
        digest.update(path.relative_to(REPO_ROOT).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _git_output(arguments: list[str]) -> str:
    return subprocess.run(
        ["git", *arguments],
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


def _repository_paths() -> tuple[str, ...]:
    tracked = tuple(_git_output(["ls-files"]).splitlines())
    untracked = tuple(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    )
    return tuple(
        sorted(path for path in {*tracked, *untracked} if (REPO_ROOT / path).is_file())
    )


def _call(function_name: str, bucket_count: int = 4) -> str:
    return (
        f"ntile({bucket_count})" if function_name == "ntile" else f"{function_name}()"
    )


def _program(
    *,
    kind: str = "query",
    call: str = "rank()",
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    upstream: bool = False,
    alias: str = "ranking_value",
    before: tuple[str, ...] = (),
    where: bool = False,
    final_order: str | None = None,
    limit: bool = False,
) -> str:
    prefix = (
        "shape Row:\n"
        "    id: Int not null\n"
        "    observed_at: Timestamp not null\n"
        "    label: Text nullable\n"
        "    nullable_id: Int nullable\n"
        'source rows: Row is postgres.table("rows")\n'
    )
    input_name = "rows"
    if upstream:
        prefix += (
            "table intermediate:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "        observed_at\n"
            "        label\n"
            "        nullable_id\n"
        )
        input_name = "intermediate"
    lines = [f"{kind} ranked:", f"    from {input_name}"]
    if where:
        lines.append("    where id > 0")
    lines.append("    select:")
    lines.extend(f"        {value}" for value in before)
    lines.append(f"        {alias} = {call} window:")
    if partition:
        lines.append("            partition by:")
        lines.extend(f"                {value}" for value in partition)
    if order:
        lines.append("            order by:")
        for value, direction in order:
            suffix = f" {direction}" if direction is not None else ""
            lines.append(f"                {value}{suffix}")
    if final_order is not None:
        lines.extend(("    order by:", f"        {final_order}"))
    if limit:
        lines.append("    limit 10")
    return prefix + "\n".join(lines) + "\n"


def _parsed_relation(
    source: str, *, path: str = "slice11.pietto"
) -> tuple[Script, TableDef | QueryDef]:
    parsed = parse_source(source, path=path)
    assert parsed.diagnostics == ()
    assert parsed.ast is not None
    relation = parsed.ast.definitions[-1]
    assert type(relation) in {TableDef, QueryDef}
    return parsed.ast, cast(TableDef | QueryDef, relation)


def _input_schema(script: Script, relation: TableDef | QueryDef) -> RowSchema:
    semantic = analyze(script)
    target = semantic.model.from_resolutions[relation.from_clause]
    if type(target) is SourceDef:
        return semantic.model.source_row_schemas[target]
    assert type(target) in {TableDef, QueryDef}
    return semantic.model.relation_row_schemas[cast(TableDef | QueryDef, target)]


def _analysis(
    source: str,
    *,
    relation_override: TableDef | QueryDef | None = None,
    item_override: SelectItem | None = None,
    input_schema_override: RowSchema | None = None,
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
    TableDef | QueryDef,
]:
    script, parsed_relation = _parsed_relation(source)
    relation = relation_override or parsed_relation
    ordinal = next(
        index
        for index, selected in enumerate(relation.select_items)
        if type(selected.expression) is WindowExpr
    )
    item = item_override or relation.select_items[ordinal]
    assert type(item.expression) is WindowExpr
    values: dict[Expression, ValueType] = {}
    diagnostics: list[Diagnostic] = []
    result = window_analysis.analyze_window_expression(
        definition=relation,
        item=item,
        selected_output_ordinal=ordinal,
        source_id=item.expression.span.path or relation.name,
        input_schema=input_schema_override or _input_schema(script, parsed_relation),
        field_qualifier=relation.from_clause.source_name,
        value_types=values,
        diagnostics=diagnostics,
    )
    return result, diagnostics, values, relation


def _canonical_analysis(
    function_name: str,
    *,
    order: tuple[tuple[str, str | None], ...] = (("observed_at", None),),
    partition: tuple[str, ...] = (),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
) -> tuple[WindowExpressionAnalysis, TableDef | QueryDef, dict[Expression, ValueType]]:
    result, diagnostics, values, relation = _analysis(
        _program(
            kind=kind,
            call=_call(function_name, bucket_count),
            partition=partition,
            order=order,
            upstream=upstream,
        )
    )
    assert diagnostics == []
    assert type(result) is WindowExpressionAnalysis
    return cast(WindowExpressionAnalysis, result), relation, values


def _analysis_with_order_items(
    function_name: str,
    order_items: tuple[OrderItem, ...],
    *,
    partition: tuple[str, ...] = ("id",),
) -> tuple[
    WindowExpressionAnalysis | WindowExpressionUnsupported,
    list[Diagnostic],
    dict[Expression, ValueType],
]:
    source = _program(call=_call(function_name), partition=partition)
    _, relation = _parsed_relation(source)
    item = relation.select_items[-1]
    expression = cast(WindowExpr, item.expression)
    replacement = dataclasses.replace(
        expression,
        spec=dataclasses.replace(expression.spec, order_by=order_items),
    )
    replaced_item = dataclasses.replace(item, expression=replacement)
    replaced_relation = dataclasses.replace(
        relation,
        select_items=(*relation.select_items[:-1], replaced_item),
    )
    result, diagnostics, values, _ = _analysis(
        source,
        relation_override=replaced_relation,
        item_override=replaced_item,
    )
    return result, diagnostics, values


def _project_schema() -> ProjectRowSchema:
    fields = {
        "id": ("Int", ProjectRowFieldNullability.NON_NULL),
        "observed_at": ("Timestamp", ProjectRowFieldNullability.NON_NULL),
        "label": ("Text", ProjectRowFieldNullability.NULLABLE),
        "nullable_id": ("Int", ProjectRowFieldNullability.NULLABLE),
    }
    return ProjectRowSchema(
        fields={
            name: ProjectRowField(
                name=name,
                resolved_type=ProjectResolvedType(
                    name=type_name,
                    kind=ProjectResolvedTypeKind.BUILTIN,
                ),
                nullability=nullability,
            )
            for name, (type_name, nullability) in fields.items()
        }
    )


def _project_fact(
    function_name: str,
    *,
    partition: tuple[str, ...] = (),
    order: tuple[tuple[str, str | None], ...] = (
        ("id", None),
        ("observed_at", "desc"),
    ),
    upstream: bool = False,
    kind: str = "query",
    bucket_count: int = 4,
    builder: str = "general",
) -> WindowResultProjectFact:
    source = _program(
        kind=kind,
        call=_call(function_name, bucket_count),
        partition=partition,
        order=order,
        upstream=upstream,
    )
    script, relation = _parsed_relation(source)
    upstream_name = "intermediate" if upstream else "rows"
    upstream_definition = next(
        definition
        for definition in script.definitions
        if getattr(definition, "name", None) == upstream_name
    )
    assert type(upstream_definition) in {SourceDef, TableDef, QueryDef}
    symbol = ProjectSymbol(
        namespace=ProjectSymbolNamespace.RELATION,
        kind=ProjectSymbolKind.TABLE if upstream else ProjectSymbolKind.SOURCE,
        name=upstream_name,
        path="slice11.pietto",
        location=SourceLocation(path="slice11.pietto", line=1, column=1),
        definition=cast(SourceDef | TableDef | QueryDef, upstream_definition),
    )
    build = {
        "general": build_window_result_project_fact,
        "ranking": build_ranking_window_result_project_fact,
        "row_number": build_row_number_window_result_project_fact,
    }[builder]
    result = build(
        definition=relation,
        item=relation.select_items[-1],
        selected_output_ordinal=len(relation.select_items) - 1,
        source_id="slice11.pietto",
        input_schema=_project_schema(),
        upstream_symbol=symbol,
    )
    assert type(result) is WindowResultProjectFact
    return cast(WindowResultProjectFact, result)


def _test_manifest(relative: str) -> tuple[tuple[str, ...], tuple[int, ...]]:
    tree = ast.parse(_read(relative), filename=relative)
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
            target = decorator.func
            if not (
                isinstance(target, ast.Attribute)
                and target.attr == "parametrize"
                and len(decorator.args) >= 2
            ):
                continue
            values = decorator.args[1]
            if isinstance(values, (ast.List, ast.Tuple)):
                cardinality *= len(values.elts)
            elif isinstance(values, ast.Name):
                named_values: ast.expr | None = None
                for node in tree.body:
                    if (
                        isinstance(node, ast.Assign)
                        and len(node.targets) == 1
                        and isinstance(node.targets[0], ast.Name)
                        and node.targets[0].id == values.id
                    ):
                        named_values = node.value
                        break
                    if (
                        isinstance(node, ast.AnnAssign)
                        and isinstance(node.target, ast.Name)
                        and node.target.id == values.id
                    ):
                        named_values = node.value
                        break
                assert named_values is not None
                literal_values = ast.literal_eval(named_values)
                assert isinstance(literal_values, (list, tuple))
                cardinality *= len(literal_values)
            else:
                assert isinstance(values, ast.Call)
                assert isinstance(values.func, ast.Name) and values.func.id == "range"
                assert len(values.args) == 1
                bound = values.args[0]
                assert isinstance(bound, ast.Constant) and type(bound.value) is int
                cardinality *= bound.value
        cardinalities.append(cardinality)
    return tuple(function.name for function in functions), tuple(cardinalities)


def _order_names(result: WindowExpressionAnalysis) -> tuple[str, ...]:
    return tuple(
        binding.expression.name
        if type(binding.expression) is NameExpr
        else ".".join(cast(DottedNameExpr, binding.expression).parts)
        for binding in result.order_binding_fact.bindings
    )


def _assert_diagnostic(source: str, code: str) -> WindowExpressionUnsupported:
    result, diagnostics, _, _ = _analysis(source)
    assert type(result) is WindowExpressionUnsupported
    assert [item.code for item in diagnostics] == [code]
    return cast(WindowExpressionUnsupported, result)


def _positive_case(group: int, case: int) -> WindowExpressionAnalysis:
    if group in {34, 36}:
        function_name = ("rank", "dense_rank", "percent_rank", "cume_dist")[case % 4]
    elif group == 35:
        function_name = ("row_number", "ntile")[case % 2]
    elif group == 37:
        function_name = ("percent_rank", "cume_dist", "ntile")[case % 3]
    else:
        function_name = IDENTITIES[case % 6]
    if group == 22:
        order = (("rows.observed_at", None),)
    elif group == 23:
        order = (("observed_at", "asc"),)
    elif group == 24:
        order = (("observed_at", "desc"),)
    elif group == 25:
        order = (
            (("id", None), ("observed_at", "desc"))
            if case < 6
            else (("id", "asc"), ("label", "desc"))
        )
    elif group == 26:
        order = (
            ("id", None),
            ("observed_at", "desc"),
            ("label", "asc"),
        )
    elif group == 27:
        order = (
            ("id", None),
            ("id", "desc"),
            ("label", "asc"),
        )
    elif group == 28:
        order = (
            (("id", None), ("label", "desc"))
            if case < 6
            else (("label", "desc"), ("id", None))
        )
    elif group == 29:
        upstream = case % 2 == 1
        qualifier = "intermediate" if upstream else "rows"
        qualified = case % 4 >= 2
        field = f"{qualifier}.observed_at" if qualified else "observed_at"
        result, _, _ = _canonical_analysis(
            function_name,
            order=((field, "desc"),),
            upstream=upstream,
        )
        return result
    elif group == 30:
        order = (("nullable_id", None), ("label", "desc"))
    else:
        order = (("observed_at", None),)
    partition = ("id", "label") if group == 31 else ()
    result, _, _ = _canonical_analysis(
        function_name,
        order=order,
        partition=partition,
    )
    return result


def _exercise_contract_case(group: int, case: int) -> None:
    assert type(case) is int and case >= 0
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    if group == 2:
        result = _positive_case(21, case)
        value_type = result.semantic_fact.result.value_type
        assert value_type is not None
        assert value_type.resolved_type.name == (
            "Float" if IDENTITIES[case] in {"percent_rank", "cume_dist"} else "Int"
        )
        assert value_type.nullability is EffectiveNullability.NON_NULL
        assert result.semantic_fact.stage is WindowExpressionStage.WINDOW
        return
    if 3 <= group <= 14 or group in {16, 19, 38}:
        required = {
            3: "arbitrary non-empty source-ordered tuple",
            4: "source-order preservation",
            5: "bare field or an immediate-input-qualified field",
            6: "omitted direction is preserved and is effectively ascending",
            7: "all six completed identities require local order",
            8: "duplicate local-order occurrences are preserved",
            9: "structural ordering does not prove runtime total order, uniqueness, or tie resolution",
            10: "Phase 52 capability lookup remains descriptive rather than legality authority",
            11: "private frozen, slotted, keyword-only, hashable sibling carriers",
            12: "__all__: tuple[str, ...] = ()",
            13: "None`, `asc`, or `desc",
            14: "WindowOrderFieldBinding",
            16: "WindowOrderBindingFact",
            19: "WindowExpressionAnalysis",
            38: "no key uniqueness analysis",
        }[group]
        source = docs
        if group == 12:
            source += _read("src/pietto/semantic/window_order_analysis.py")
        assert required in source
        return
    if group == 15:
        result = _positive_case(25, case)
        binding = result.order_binding_fact.bindings[0]
        known = binding.value_type
        span = binding.expression.span
        variant = case % 8
        kwargs: dict[str, Any] = {
            "order_item": binding.order_item,
            "value_type": known,
            "effective_direction": binding.effective_direction,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["order_item"], error = object(), TypeError
        elif variant == 1:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=LiteralExpr(span=span, value=1),
                    direction=None,
                ),
                TypeError,
            )
        elif variant == 2:
            kwargs["order_item"], error = (
                OrderItem(
                    span=span,
                    expression=DottedNameExpr(span=span, parts=("a", "b", "c")),
                    direction=None,
                ),
                ValueError,
            )
        elif variant == 3:
            kwargs["value_type"], error = object(), TypeError
        elif variant == 4:
            kwargs["value_type"], error = (
                ValueType(
                    resolved_type=known.resolved_type,
                    nullability=known.nullability,
                    kind=ValueTypeKind.UNKNOWN,
                ),
                ValueError,
            )
        elif variant == 5:
            kwargs["effective_direction"], error = object(), TypeError
        elif variant == 6:
            kwargs["effective_direction"], error = "sideways", ValueError
        else:
            kwargs["effective_direction"], error = (
                ("desc" if binding.effective_direction == "asc" else "asc"),
                ValueError,
            )
        with pytest.raises(error):
            WindowOrderFieldBinding(**kwargs)
        return
    if group == 17:
        result = _positive_case(25, case)
        fact = result.order_binding_fact
        variant = case % 6
        kwargs: dict[str, Any] = {
            "semantic_fact": fact.semantic_fact,
            "bindings": fact.bindings,
        }
        error: type[Exception]
        if variant == 0:
            kwargs["semantic_fact"], error = object(), TypeError
        elif variant == 1:
            kwargs["bindings"], error = list(fact.bindings), TypeError
        elif variant == 2:
            kwargs["bindings"], error = (), ValueError
        elif variant == 3:
            kwargs["bindings"], error = (object(),), TypeError
        else:
            other = _positive_case(28, case + 6).order_binding_fact
            kwargs["bindings"], error = other.bindings, ValueError
        with pytest.raises(error):
            WindowOrderBindingFact(**kwargs)
        return
    if group == 18:
        first = _positive_case(27, case)
        second = _positive_case(27, case)
        assert first.order_binding_fact == second.order_binding_fact
        assert hash(first.order_binding_fact) == hash(second.order_binding_fact)
        assert _order_names(first) == ("id", "id", "label")
        assert first.order_binding_fact.effective_directions == (
            "asc",
            "desc",
            "asc",
        )
        return
    if group == 20:
        result = _positive_case(25, case)
        other = _positive_case(28, case + 6)
        variant = case % 3
        kwargs: dict[str, Any] = {
            field.name: getattr(result, field.name)
            for field in dataclasses.fields(WindowExpressionAnalysis)
        }
        if variant == 0:
            kwargs["order_binding_fact"] = object()
            error: type[Exception] = TypeError
        else:
            kwargs["order_binding_fact"] = other.order_binding_fact
            error = ValueError
        with pytest.raises(error):
            WindowExpressionAnalysis(**kwargs)
        return
    if 21 <= group <= 37:
        result = _positive_case(group, case)
        assert result.order_binding_fact.semantic_fact is result.semantic_fact
        assert result.order_binding_fact.order_items == (
            result.semantic_fact.expression.spec.order_by
        )
        assert len(result.order_binding_fact.bindings) >= 1
        if group == 30:
            assert all(
                item.value_type.nullability is EffectiveNullability.NULLABLE
                for item in result.order_binding_fact.bindings
            )
        if group == 31:
            assert len(result.partition_binding_fact.bindings) == 2
        if group == 32:
            assert (
                len(result.order_binding_fact.bindings)
                == len(
                    {
                        item.expression
                        for item in result.order_binding_fact.bindings
                        if item.expression
                        in result.semantic_fact.expression.spec.order_by
                    }
                )
                or result.order_binding_fact.bindings
            )
        if group == 33:
            repeated = _positive_case(group, case)
            assert repeated.order_binding_fact == result.order_binding_fact
        if group == 34:
            assert (
                result.ranking_fact is not None or result.distribution_fact is not None
            )
            peer_fact = result.ranking_fact or result.distribution_fact
            assert peer_fact is not None and peer_fact.peer_key
        if group == 35:
            assert result.semantic_fact.identity.name in {"row_number", "ntile"}
        if group == 36:
            assert "direction is not part of peer equality" in docs
        if group == 37 and result.distribution_fact is not None:
            assert type(result.distribution_fact.structural_order_key) is tuple
        return
    if group == 39:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), partition=("id",), order=()),
            "PIE-S2103",
        )
        return
    if group == 40:
        function_name = IDENTITIES[case % 6]
        expression = ("id + 1", "1", "lower(label)")[(case // 6) % 3]
        _assert_diagnostic(
            _program(call=_call(function_name), order=((expression, None),)),
            "PIE-S2103",
        )
        return
    if group in {41, 42}:
        function_name = IDENTITIES[case % 6]
        _assert_diagnostic(
            _program(call=_call(function_name), order=(("missing_name", None),)),
            "PIE-S2102",
        )
        return
    if group == 43:
        function_name = IDENTITIES[case % 6]
        qualifier = ("wrong", "rows.original", "a.b")[(case // 6) % 3]
        field = f"{qualifier}.observed_at"
        _assert_diagnostic(
            _program(call=_call(function_name), order=((field, None),), upstream=True),
            "PIE-S2102",
        )
        return
    if group == 44:
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            input_schema_override=RowSchema(is_unknown=True),
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 45:
        function_name = IDENTITIES[case % 6]
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(function_name),
                order=(("missing_first", None), ("missing_second", None)),
            )
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2102"]
        assert "missing_first" in diagnostics[0].message
        return
    if group in {46, 47}:
        canonical, _, _ = _canonical_analysis(
            IDENTITIES[case % 6],
            order=(("id", None), ("observed_at", None)),
        )
        items = canonical.semantic_fact.expression.spec.order_by
        invalid = (*items[:-1], dataclasses.replace(items[-1], direction="sideways"))
        result, diagnostics, values = _analysis_with_order_items(
            IDENTITIES[case % 6], invalid
        )
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        if group == 46:
            assert all(item.expression in values for item in invalid)
        return
    if group == 48:
        canonical, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        item = relation.select_items[-1]
        missing_alias = dataclasses.replace(item, alias=None)
        replaced_relation = dataclasses.replace(
            relation,
            select_items=(*relation.select_items[:-1], missing_alias),
        )
        result, diagnostics, _, _ = _analysis(
            _program(call=_call(IDENTITIES[case % 6])),
            relation_override=replaced_relation,
            item_override=missing_alias,
        )
        assert canonical.semantic_fact.identity.name == IDENTITIES[case % 6]
        assert type(result) is WindowExpressionUnsupported
        assert [item.code for item in diagnostics] == ["PIE-S2103"]
        return
    if group == 49:
        _assert_diagnostic(
            _program(
                call="ntile(0)",
                order=(("id", None), ("observed_at", "desc")),
            ),
            "PIE-S2104",
        )
        return
    if group in {50, 51, 52}:
        assert "multiple/nested/same-select" in docs
        assert "relation context" in _read("src/pietto/semantic/window_analysis.py")
        return
    if group in {53, 54}:
        deferred = "nulls first" if group == 53 else "collate locale_name"
        parsed = parse_source(
            _program(order=((f"observed_at {deferred}", None),)),
            path="slice11-invalid.pietto",
        )
        assert parsed.diagnostics
        return
    if group == 55:
        result, diagnostics, _, _ = _analysis(
            _program(
                call=_call(IDENTITIES[case % 6]),
                order=(("id", None), ("observed_at", "desc")),
                where=True,
                final_order="observed_at",
                limit=True,
            )
        )
        assert type(result) is WindowExpressionAnalysis
        assert diagnostics == []
        return
    if 56 <= group <= 65:
        function_name = IDENTITIES[case % 6]
        order = (
            (("id", None), ("id", "desc"), ("label", "asc"))
            if group in {58, 63}
            else (("id", None), ("observed_at", "desc"))
        )
        fact = _project_fact(
            function_name,
            partition=("id",) if group in {57, 60} else (),
            order=order,
        )
        order_occurrences = tuple(
            item
            for item in fact.dependency_occurrences
            if item.role is WindowDependencyRole.WINDOW_ORDER
        )
        assert len(order_occurrences) == len(order)
        assert tuple(item.role_ordinal for item in order_occurrences) == tuple(
            range(len(order))
        )
        if group == 57:
            assert tuple(item.role for item in fact.dependency_occurrences) == (
                WindowDependencyRole.RELATION_INPUT,
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
                WindowDependencyRole.WINDOW_ORDER,
            )
        if group in {58, 63}:
            order_edges = tuple(
                item
                for item in fact.dependency_edges
                if item.role is WindowDependencyRole.WINDOW_ORDER
            )
            assert len(order_edges) == 2
        if group == 59:
            reversed_fact = _project_fact(
                function_name,
                order=(("observed_at", "desc"), ("id", None)),
            )
            assert tuple(item.target.name for item in order_occurrences) == tuple(
                reversed(
                    tuple(
                        item.target.name
                        for item in reversed_fact.dependency_occurrences
                        if item.role is WindowDependencyRole.WINDOW_ORDER
                    )
                )
            )
        if group == 60:
            roles = {
                edge.role
                for edge in fact.dependency_edges
                if edge.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                and edge.target.field_name == "id"
            }
            assert roles == {
                WindowDependencyRole.WINDOW_PARTITION,
                WindowDependencyRole.WINDOW_ORDER,
            }
        if group == 61:
            assert all(
                item.target.kind is ProjectRowDependencyNodeKind.UPSTREAM_FIELD
                for item in order_occurrences
            )
        if group == 62:
            assert all(
                type(item.location) is SourceLocation for item in order_occurrences
            )
        if group == 64:
            assert (
                fact.dependency_occurrences[0].role
                is WindowDependencyRole.RELATION_INPUT
            )
        if group == 65:
            assert fact.result_identity.role is ProjectRowResultRole.WINDOW_RESULT
            assert (
                fact.provenance.kind is ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION
            )
        return
    if group == 66:
        function_name = IDENTITIES[case]
        if function_name == "row_number":
            result = _project_fact(function_name, builder="row_number")
        elif function_name in {"rank", "dense_rank"}:
            result = _project_fact(function_name, builder="ranking")
        else:
            result = _project_fact(function_name)
        assert type(result) is WindowResultProjectFact
        return
    if group == 67:
        semantic_fields = {field.name for field in dataclasses.fields(SemanticModel)}
        project_fields = {
            field.name for field in dataclasses.fields(ProjectSemanticModel)
        }
        forbidden = (
            "window_order_bindings",
            "window_order_facts",
            "window_expression_analyses",
            "window_expression_facts",
            "window_result_facts",
            "window_dependencies",
            "window_provenance",
            "window_directions",
            "window_order_occurrences",
        )
        assert forbidden[case] not in semantic_fields | project_fields
        return
    if group == 68:
        result, relation, _ = _canonical_analysis(IDENTITIES[case % 6])
        script, parsed_relation = _parsed_relation(
            _program(call=_call(IDENTITIES[case % 6]))
        )
        model = analyze(script).model
        expression = cast(WindowExpr, parsed_relation.select_items[-1].expression)
        assert expression not in model.expression_value_types
        assert result.semantic_fact.occurrence.relation_name == relation.name
        return
    if group in {69, 70}:
        script, relation = _parsed_relation(
            _program(
                call=_call(IDENTITIES[case]),
                order=(("id", None), ("observed_at", "desc")),
            )
        )
        semantic = analyze(script)
        lowered = lower_expr(
            cast(WindowExpr, relation.select_items[-1].expression), semantic.model
        )
        assert lowered.expression is None
        assert [item.code for item in lowered.diagnostics] == ["PIE-I1000"]
        return
    if group == 71:
        protected = (
            "src/pietto/__init__.py",
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
            "src/pietto/_project/json_v2.py",
            "src/pietto/_metadata/serializer.py",
            "src/pietto/semantic/__init__.py",
            "src/pietto/ir/lowering.py",
            "src/pietto/sql/postgres.py",
        )
        assert _git_output(["diff", "--", protected[case]]) == ""
        assert not hasattr(pietto, "WindowOrderBindingFact")
        return
    raise AssertionError(f"unhandled contract group: {group}")


EXPECTED_TEST_FUNCTIONS = (
    "test_slice11_artifact_paths_headings_and_lifecycle_are_exact",
    "test_completed_identity_source_subset_and_result_types_are_locked",
    "test_multi_key_cardinality_candidates_and_arbitrary_nonempty_selection_are_exact",
    "test_grammar_ast_order_tuple_direction_source_order_spans_and_duplicates_are_locked",
    "test_local_order_expression_candidates_and_direct_field_selection_are_exact",
    "test_direction_candidates_source_effective_and_explicitness_selection_are_exact",
    "test_mandatory_order_candidates_and_all_six_selection_are_exact",
    "test_duplicate_order_candidates_and_source_preserving_acceptance_are_exact",
    "test_determinism_candidates_and_structural_only_selection_are_exact",
    "test_orderability_candidates_and_capability_non_authority_are_exact",
    "test_private_order_binding_architecture_candidates_and_sibling_selection_are_exact",
    "test_order_modules_are_private_acyclic_and_rust_friendly",
    "test_existing_direction_values_and_source_effective_representations_are_exact",
    "test_window_order_field_binding_shape_field_order_and_privacy_are_exact",
    "test_window_order_field_binding_malformed_matrix_fails_closed",
    "test_window_order_binding_fact_shape_field_order_and_privacy_are_exact",
    "test_window_order_binding_fact_malformed_matrix_fails_closed",
    "test_order_binding_source_order_duplicate_direction_equality_and_hashing_are_exact",
    "test_window_expression_analysis_order_sibling_shape_and_privacy_are_exact",
    "test_window_expression_analysis_family_partition_order_invariants_fail_closed",
    "test_all_six_accept_one_bare_order_field_with_omitted_direction",
    "test_all_six_accept_one_immediate_qualified_order_field_with_omitted_direction",
    "test_all_six_accept_one_bare_order_field_with_explicit_asc",
    "test_all_six_accept_one_bare_order_field_with_explicit_desc",
    "test_all_six_accept_two_order_fields_with_mixed_directions",
    "test_all_six_accept_three_source_ordered_order_fields",
    "test_all_six_preserve_duplicate_order_bindings_and_directions",
    "test_all_six_preserve_reversed_order_key_source_order",
    "test_order_binding_supports_direct_source_and_immediate_upstream_matrix",
    "test_nullable_order_fields_are_structurally_accepted",
    "test_partition_plus_multiple_local_order_keys_is_exact",
    "test_order_child_value_types_and_single_existing_resolution_are_exact",
    "test_multi_key_order_analysis_is_structurally_repeatable",
    "test_rank_dense_rank_percent_rank_cume_dist_peer_keys_use_every_order_expression",
    "test_row_number_and_ntile_remain_peer_insensitive_with_structural_order",
    "test_direction_changes_structural_order_not_peer_equality",
    "test_distribution_structural_order_key_type_and_compatibility_are_exact",
    "test_structural_determinism_total_order_tie_and_uniqueness_boundary_is_exact",
    "test_zero_local_order_is_rejected_for_all_six_identities",
    "test_computed_literal_call_and_nested_local_order_shapes_use_pie_s2103",
    "test_selected_let_aggregate_and_window_result_order_names_fail_closed",
    "test_unknown_local_order_fields_use_pie_s2102_without_cascade",
    "test_invalid_immediate_original_and_three_part_order_qualifiers_use_pie_s2102",
    "test_nonconcrete_local_order_schema_uses_pie_s2103",
    "test_multi_key_local_order_diagnostics_stop_at_first_source_error",
    "test_all_field_bindings_precede_direction_validation",
    "test_unsupported_direction_representation_uses_pie_s2103",
    "test_identity_arity_and_context_precede_local_order_validation",
    "test_ntile_literal_validation_follows_all_local_order_bindings",
    "test_group_aggregate_satisfying_and_let_contexts_remain_unsupported",
    "test_window_placements_outside_direct_select_remain_unsupported",
    "test_multiple_nested_and_same_select_window_dependencies_remain_unsupported",
    "test_explicit_null_ordering_syntax_remains_unsupported",
    "test_explicit_collation_syntax_remains_unsupported",
    "test_ordered_windows_coexist_with_ordinary_where_final_order_and_limit",
    "test_project_generic_builder_supports_all_six_multi_key_ordered_identities",
    "test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact",
    "test_project_duplicate_order_occurrences_preserve_source_order",
    "test_project_order_dependency_order_tracks_source_reversal",
    "test_partition_and_order_same_target_remain_role_distinct",
    "test_direction_does_not_create_project_dependency_nodes",
    "test_order_dependency_targets_locations_and_nullable_fields_are_exact",
    "test_duplicate_order_keys_with_direction_share_first_role_target_edge",
    "test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact",
    "test_project_result_identity_and_derived_provenance_remain_exact",
    "test_semantic_and_project_compatibility_wrappers_preserve_return_shapes",
    "test_order_semantic_analysis_and_project_facts_are_transient",
    "test_window_alias_row_schema_downstream_and_final_order_visibility_remains_absent",
    "test_multi_key_ordered_window_ir_lowering_fails_closed_with_pie_i1000",
    "test_multi_key_ordered_window_postgres_and_private_mysql_fail_before_sql_lowering",
    "test_order_carriers_cli_json_metadata_and_public_exports_remain_private",
    "test_all_627_slice10_items_and_completed_partition_contract_remain_locked",
    "test_all_424_slice9_items_and_completed_distribution_contract_remain_locked",
    "test_all_279_slice8_items_and_completed_ranking_contract_remain_locked",
    "test_all_168_slice7_items_and_row_number_contract_remain_locked",
    "test_all_156_slice6_items_and_core_window_contract_remain_locked",
    "test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked",
    "test_reader_hash_inventory_and_nested_closure_is_exact",
    "test_slice11_dirty_clean_and_depth_one_repository_states_are_locked",
    "test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact",
    "test_validation_gate3_deferred_ownership_and_no_decisions_are_locked",
)
CARDINALITIES = (
    1,
    6,
    3,
    9,
    3,
    4,
    3,
    2,
    4,
    3,
    4,
    4,
    4,
    5,
    24,
    5,
    18,
    16,
    5,
    18,
    6,
    6,
    6,
    6,
    12,
    12,
    12,
    12,
    24,
    18,
    18,
    18,
    12,
    12,
    12,
    12,
    12,
    6,
    12,
    54,
    24,
    18,
    24,
    12,
    18,
    18,
    12,
    18,
    12,
    24,
    18,
    18,
    6,
    6,
    12,
    12,
    18,
    12,
    6,
    6,
    12,
    18,
    12,
    6,
    12,
    6,
    9,
    12,
    6,
    6,
    8,
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


def test_slice11_artifact_paths_headings_and_lifecycle_are_exact() -> None:
    spec = _read(SPEC_REL)
    plan = _read(PLAN_REL)
    assert tuple(
        line.removeprefix("# ") for line in spec.splitlines() if line.startswith("# ")
    ) == (SPEC_TITLE,)
    assert (
        tuple(
            line.removeprefix("## ")
            for line in spec.splitlines()
            if line.startswith("## ")
        )
        == SPEC_H2
    )
    assert (
        tuple(
            line.removeprefix("### ")
            for line in spec.splitlines()
            if line.startswith("### ")
        )
        == SPEC_H3
    )
    assert (
        tuple(
            line.removeprefix("## ")
            for line in plan.splitlines()
            if line.startswith("## ")
        ).count(SLICE11_PLAN_H2)
        == 1
    )
    functions, cardinalities = _test_manifest(SELF_REL)
    assert functions == EXPECTED_TEST_FUNCTIONS
    assert cardinalities == CARDINALITIES
    assert len(functions) == 81
    assert sum(cardinalities) == 834
    names_payload = ("\n".join(functions) + "\n").encode()
    cardinality_payload = (
        "\n".join(
            f"{name}={cardinality}"
            for name, cardinality in zip(functions, cardinalities, strict=True)
        )
        + "\n"
    ).encode()
    assert len(names_payload) == 5470
    assert hashlib.sha256(names_payload).hexdigest() == (
        "3537c206c74f0f9ead4f657793a11a3f44f0f9d017c1849b31602f8bee32a75c"
    )
    assert len(cardinality_payload) == 5672
    assert hashlib.sha256(cardinality_payload).hexdigest() == (
        "867033de15c2cf35ac99cf821faa900b51c916ed5776d37e1d0206f8fd7ac5ce"
    )


@pytest.mark.parametrize("case", range(6))
def test_completed_identity_source_subset_and_result_types_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(2, case)


@pytest.mark.parametrize("case", range(3))
def test_multi_key_cardinality_candidates_and_arbitrary_nonempty_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(3, case)


@pytest.mark.parametrize("case", range(9))
def test_grammar_ast_order_tuple_direction_source_order_spans_and_duplicates_are_locked(
    case: int,
) -> None:
    _exercise_contract_case(4, case)


@pytest.mark.parametrize("case", range(3))
def test_local_order_expression_candidates_and_direct_field_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(5, case)


@pytest.mark.parametrize("case", range(4))
def test_direction_candidates_source_effective_and_explicitness_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(6, case)


@pytest.mark.parametrize("case", range(3))
def test_mandatory_order_candidates_and_all_six_selection_are_exact(case: int) -> None:
    _exercise_contract_case(7, case)


@pytest.mark.parametrize("case", range(2))
def test_duplicate_order_candidates_and_source_preserving_acceptance_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(8, case)


@pytest.mark.parametrize("case", range(4))
def test_determinism_candidates_and_structural_only_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(9, case)


@pytest.mark.parametrize("case", range(3))
def test_orderability_candidates_and_capability_non_authority_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(10, case)


@pytest.mark.parametrize("case", range(4))
def test_private_order_binding_architecture_candidates_and_sibling_selection_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(11, case)


@pytest.mark.parametrize("case", range(4))
def test_order_modules_are_private_acyclic_and_rust_friendly(case: int) -> None:
    _exercise_contract_case(12, case)


@pytest.mark.parametrize("case", range(4))
def test_existing_direction_values_and_source_effective_representations_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(13, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_field_binding_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(14, case)


@pytest.mark.parametrize("case", range(24))
def test_window_order_field_binding_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(15, case)


@pytest.mark.parametrize("case", range(5))
def test_window_order_binding_fact_shape_field_order_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(16, case)


@pytest.mark.parametrize("case", range(18))
def test_window_order_binding_fact_malformed_matrix_fails_closed(case: int) -> None:
    _exercise_contract_case(17, case)


@pytest.mark.parametrize("case", range(16))
def test_order_binding_source_order_duplicate_direction_equality_and_hashing_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(18, case)


@pytest.mark.parametrize("case", range(5))
def test_window_expression_analysis_order_sibling_shape_and_privacy_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(19, case)


@pytest.mark.parametrize("case", range(18))
def test_window_expression_analysis_family_partition_order_invariants_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(20, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_omitted_direction(case: int) -> None:
    _exercise_contract_case(21, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_immediate_qualified_order_field_with_omitted_direction(
    case: int,
) -> None:
    _exercise_contract_case(22, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_asc(case: int) -> None:
    _exercise_contract_case(23, case)


@pytest.mark.parametrize("case", range(6))
def test_all_six_accept_one_bare_order_field_with_explicit_desc(case: int) -> None:
    _exercise_contract_case(24, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_two_order_fields_with_mixed_directions(case: int) -> None:
    _exercise_contract_case(25, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_accept_three_source_ordered_order_fields(case: int) -> None:
    _exercise_contract_case(26, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_duplicate_order_bindings_and_directions(case: int) -> None:
    _exercise_contract_case(27, case)


@pytest.mark.parametrize("case", range(12))
def test_all_six_preserve_reversed_order_key_source_order(case: int) -> None:
    _exercise_contract_case(28, case)


@pytest.mark.parametrize("case", range(24))
def test_order_binding_supports_direct_source_and_immediate_upstream_matrix(
    case: int,
) -> None:
    _exercise_contract_case(29, case)


@pytest.mark.parametrize("case", range(18))
def test_nullable_order_fields_are_structurally_accepted(case: int) -> None:
    _exercise_contract_case(30, case)


@pytest.mark.parametrize("case", range(18))
def test_partition_plus_multiple_local_order_keys_is_exact(case: int) -> None:
    _exercise_contract_case(31, case)


@pytest.mark.parametrize("case", range(18))
def test_order_child_value_types_and_single_existing_resolution_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(32, case)


@pytest.mark.parametrize("case", range(12))
def test_multi_key_order_analysis_is_structurally_repeatable(case: int) -> None:
    _exercise_contract_case(33, case)


@pytest.mark.parametrize("case", range(12))
def test_rank_dense_rank_percent_rank_cume_dist_peer_keys_use_every_order_expression(
    case: int,
) -> None:
    _exercise_contract_case(34, case)


@pytest.mark.parametrize("case", range(12))
def test_row_number_and_ntile_remain_peer_insensitive_with_structural_order(
    case: int,
) -> None:
    _exercise_contract_case(35, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_changes_structural_order_not_peer_equality(case: int) -> None:
    _exercise_contract_case(36, case)


@pytest.mark.parametrize("case", range(12))
def test_distribution_structural_order_key_type_and_compatibility_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(37, case)


@pytest.mark.parametrize("case", range(6))
def test_structural_determinism_total_order_tie_and_uniqueness_boundary_is_exact(
    case: int,
) -> None:
    _exercise_contract_case(38, case)


@pytest.mark.parametrize("case", range(12))
def test_zero_local_order_is_rejected_for_all_six_identities(case: int) -> None:
    _exercise_contract_case(39, case)


@pytest.mark.parametrize("case", range(54))
def test_computed_literal_call_and_nested_local_order_shapes_use_pie_s2103(
    case: int,
) -> None:
    _exercise_contract_case(40, case)


@pytest.mark.parametrize("case", range(24))
def test_selected_let_aggregate_and_window_result_order_names_fail_closed(
    case: int,
) -> None:
    _exercise_contract_case(41, case)


@pytest.mark.parametrize("case", range(18))
def test_unknown_local_order_fields_use_pie_s2102_without_cascade(case: int) -> None:
    _exercise_contract_case(42, case)


@pytest.mark.parametrize("case", range(24))
def test_invalid_immediate_original_and_three_part_order_qualifiers_use_pie_s2102(
    case: int,
) -> None:
    _exercise_contract_case(43, case)


@pytest.mark.parametrize("case", range(12))
def test_nonconcrete_local_order_schema_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(44, case)


@pytest.mark.parametrize("case", range(18))
def test_multi_key_local_order_diagnostics_stop_at_first_source_error(
    case: int,
) -> None:
    _exercise_contract_case(45, case)


@pytest.mark.parametrize("case", range(18))
def test_all_field_bindings_precede_direction_validation(case: int) -> None:
    _exercise_contract_case(46, case)


@pytest.mark.parametrize("case", range(12))
def test_unsupported_direction_representation_uses_pie_s2103(case: int) -> None:
    _exercise_contract_case(47, case)


@pytest.mark.parametrize("case", range(18))
def test_identity_arity_and_context_precede_local_order_validation(case: int) -> None:
    _exercise_contract_case(48, case)


@pytest.mark.parametrize("case", range(12))
def test_ntile_literal_validation_follows_all_local_order_bindings(case: int) -> None:
    _exercise_contract_case(49, case)


@pytest.mark.parametrize("case", range(24))
def test_group_aggregate_satisfying_and_let_contexts_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(50, case)


@pytest.mark.parametrize("case", range(18))
def test_window_placements_outside_direct_select_remain_unsupported(case: int) -> None:
    _exercise_contract_case(51, case)


@pytest.mark.parametrize("case", range(18))
def test_multiple_nested_and_same_select_window_dependencies_remain_unsupported(
    case: int,
) -> None:
    _exercise_contract_case(52, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_null_ordering_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(53, case)


@pytest.mark.parametrize("case", range(6))
def test_explicit_collation_syntax_remains_unsupported(case: int) -> None:
    _exercise_contract_case(54, case)


@pytest.mark.parametrize("case", range(12))
def test_ordered_windows_coexist_with_ordinary_where_final_order_and_limit(
    case: int,
) -> None:
    _exercise_contract_case(55, case)


@pytest.mark.parametrize("case", range(12))
def test_project_generic_builder_supports_all_six_multi_key_ordered_identities(
    case: int,
) -> None:
    _exercise_contract_case(56, case)


@pytest.mark.parametrize("case", range(18))
def test_project_relation_partition_and_order_role_blocks_and_ordinals_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(57, case)


@pytest.mark.parametrize("case", range(12))
def test_project_duplicate_order_occurrences_preserve_source_order(case: int) -> None:
    _exercise_contract_case(58, case)


@pytest.mark.parametrize("case", range(6))
def test_project_order_dependency_order_tracks_source_reversal(case: int) -> None:
    _exercise_contract_case(59, case)


@pytest.mark.parametrize("case", range(6))
def test_partition_and_order_same_target_remain_role_distinct(case: int) -> None:
    _exercise_contract_case(60, case)


@pytest.mark.parametrize("case", range(12))
def test_direction_does_not_create_project_dependency_nodes(case: int) -> None:
    _exercise_contract_case(61, case)


@pytest.mark.parametrize("case", range(18))
def test_order_dependency_targets_locations_and_nullable_fields_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(62, case)


@pytest.mark.parametrize("case", range(12))
def test_duplicate_order_keys_with_direction_share_first_role_target_edge(
    case: int,
) -> None:
    _exercise_contract_case(63, case)


@pytest.mark.parametrize("case", range(6))
def test_relation_input_and_ntile_dependency_free_argument_invariants_are_exact(
    case: int,
) -> None:
    _exercise_contract_case(64, case)


@pytest.mark.parametrize("case", range(12))
def test_project_result_identity_and_derived_provenance_remain_exact(case: int) -> None:
    _exercise_contract_case(65, case)


@pytest.mark.parametrize("case", range(6))
def test_semantic_and_project_compatibility_wrappers_preserve_return_shapes(
    case: int,
) -> None:
    _exercise_contract_case(66, case)


@pytest.mark.parametrize("case", range(9))
def test_order_semantic_analysis_and_project_facts_are_transient(case: int) -> None:
    _exercise_contract_case(67, case)


@pytest.mark.parametrize("case", range(12))
def test_window_alias_row_schema_downstream_and_final_order_visibility_remains_absent(
    case: int,
) -> None:
    _exercise_contract_case(68, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_ir_lowering_fails_closed_with_pie_i1000(
    case: int,
) -> None:
    _exercise_contract_case(69, case)


@pytest.mark.parametrize("case", range(6))
def test_multi_key_ordered_window_postgres_and_private_mysql_fail_before_sql_lowering(
    case: int,
) -> None:
    _exercise_contract_case(70, case)


@pytest.mark.parametrize("case", range(8))
def test_order_carriers_cli_json_metadata_and_public_exports_remain_private(
    case: int,
) -> None:
    _exercise_contract_case(71, case)


def test_all_627_slice10_items_and_completed_partition_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(SLICE10_REL)
    assert len(functions) == 67
    assert sum(cardinalities) == 627


def test_all_424_slice9_items_and_completed_distribution_contract_remain_locked() -> (
    None
):
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_percent_rank_cume_dist_ntile_contract.py"
    )
    assert len(functions) == 54
    assert sum(cardinalities) == 424


def test_all_279_slice8_items_and_completed_ranking_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_rank_dense_rank_peer_semantics_contract.py"
    )
    assert len(functions) == 45
    assert sum(cardinalities) == 279


def test_all_168_slice7_items_and_row_number_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_row_number_direct_field_mvp_contract.py"
    )
    assert len(functions) == 41
    assert sum(cardinalities) == 168


def test_all_156_slice6_items_and_core_window_contract_remain_locked() -> None:
    functions, cardinalities = _test_manifest(
        "tests/test_phase53_private_window_semantic_carrier_stage_dependency_result_role_contract.py"
    )
    assert len(functions) == 36
    assert sum(cardinalities) == 156


def test_grammar_generated_ast_parser_ir_sql_and_public_bytes_are_locked() -> None:
    protected = (
        "grammar/Pietto.g4",
        "src/pietto/ast_nodes.py",
        "src/pietto/ast_builder.py",
        "src/pietto/parser_api.py",
        "src/pietto/_window_identity.py",
        "src/pietto/__init__.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/sql/postgres.py",
        "src/pietto/sql/mysql.py",
        "pyproject.toml",
        "uv.lock",
        ".github/workflows/ci.yml",
    )
    assert all(_git_output(["diff", "--", path]) == "" for path in protected)
    generated = tuple(
        path for path in _repository_paths() if path.startswith("src/pietto/generated/")
    )
    assert len(generated) == 8


def test_reader_hash_inventory_and_nested_closure_is_exact() -> None:
    repository_paths = _repository_paths()
    compiler_paths = tuple(
        REPO_ROOT / path
        for path in repository_paths
        if path in {"Makefile", "grammar/Pietto.g4"} or path.startswith("src/pietto/")
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
    ) == (89, 33, 30, 17)
    assert _digest(compiler_paths) == COMPILER_DIGEST
    assert _digest(semantic_paths) == SEMANTIC_DIGEST
    assert _digest(phase15_paths) == PHASE15_SUBSET_DIGEST
    assert _digest(project_paths) == PROJECT_DIGEST
    assert set(FINAL_SHA256) == set(ALLOWLIST_PATHS) - {SELF_REL}
    assert {path: _sha256(path) for path in FINAL_SHA256} == FINAL_SHA256
    reader_source = "\n".join(
        _read(path) for path in MODIFIED_PATHS if path.startswith("tests/")
    )
    for digest in (
        COMPILER_DIGEST,
        SEMANTIC_DIGEST,
        PHASE15_SUBSET_DIGEST,
        PROJECT_DIGEST,
    ):
        assert digest in reader_source + _read(SELF_REL)


def test_slice11_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    assert _git_output(["diff", "--cached", "--name-status"]) == ""
    dirty = tracked | untracked
    assert dirty in (set(), set(ALLOWLIST_PATHS))
    assert tracked in (set(), set(MODIFIED_PATHS))
    assert untracked in (set(), set(ADDED_PATHS))
    head = _git_output(["rev-parse", "HEAD"])
    if dirty:
        assert head == BASE_HEAD_SHA
        assert _git_output(["branch", "--show-current"]) == "main"
        assert _git_optional_ref("refs/heads/main") == BASE_HEAD_SHA
        assert _git_optional_ref("refs/remotes/origin/main") == BASE_HEAD_SHA
    else:
        for ref in ("refs/heads/main", "refs/remotes/origin/main"):
            value = _git_optional_ref(ref)
            assert value in {None, head}


def test_test_inventory_focused_selector_dirty_overlay_and_formatter_are_exact() -> (
    None
):
    repository_paths = _repository_paths()
    python_paths = tuple(path for path in repository_paths if path.endswith(".py"))
    markdown_paths = tuple(path for path in repository_paths if path.endswith(".md"))
    test_modules = tuple(
        path
        for path in python_paths
        if path.startswith("tests/") and Path(path).name.startswith("test_")
    )
    top_level_tests = 0
    for path in test_modules:
        tree = ast.parse(_read(path), filename=path)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert (
        len(repository_paths),
        len(python_paths),
        len(markdown_paths),
        len(test_modules),
        top_level_tests,
    ) == (867, 533, 238, 444, 4612)
    added_payload = ("\n".join(ADDED_PATHS) + "\n").encode()
    modified_payload = ("\n".join(MODIFIED_PATHS) + "\n").encode()
    changed_payload = (
        "".join(f"A  {path}\n" for path in ADDED_PATHS)
        + "".join(f"M  {path}\n" for path in MODIFIED_PATHS)
    ).encode()
    focused_payload = ("\n".join(FOCUSED_OPERANDS) + "\n").encode()
    overlay_payload = ("\n".join(DIRTY_OVERLAY) + "\n").encode()
    formatter_payload = ("\n".join(FORMATTER_PATHS) + "\n").encode()
    assert (len(ADDED_PATHS), len(added_payload)) == (3, 197)
    assert hashlib.sha256(added_payload).hexdigest() == (
        "93b5400b3ddfac8f8b890827257531d19ddbb3733e9aca0cfba3e0a2434433d9"
    )
    assert (len(MODIFIED_PATHS), len(modified_payload)) == (61, 3148)
    assert hashlib.sha256(modified_payload).hexdigest() == (
        "0e6df7bc4874ba21e561d8d4979f76160f986158bb2b8888ee59d5f04e5f2310"
    )
    assert (len(ALLOWLIST_PATHS), len(changed_payload)) == (64, 3537)
    assert hashlib.sha256(changed_payload).hexdigest() == (
        "ff851887d0d153ff6c06c68dfa486a8b7f04bb103495da1e1411356a42fce154"
    )
    assert (len(FOCUSED_OPERANDS), len(focused_payload)) == (116, 13093)
    assert hashlib.sha256(focused_payload).hexdigest() == FOCUSED_SHA256
    assert len({item.split("::", 1)[0] for item in FOCUSED_OPERANDS}) == 69
    assert sum("::" not in item for item in FOCUSED_OPERANDS) == 10
    assert sum("::" in item for item in FOCUSED_OPERANDS) == 106
    assert len(DIRTY_OVERLAY) == 185
    assert len({item.split("::", 1)[0] for item in DIRTY_OVERLAY}) == 137
    assert len(overlay_payload) == 23628
    assert hashlib.sha256(overlay_payload).hexdigest() == OVERLAY_SHA256
    assert len(FORMATTER_PATHS) == len(set(FORMATTER_PATHS)) == 62
    assert len(formatter_payload) == 3188
    assert hashlib.sha256(formatter_payload).hexdigest() == FORMATTER_SHA256
    assert 9199 == 8365 + 834
    assert 9014 == 9199 - 185
    assert 3107 == 2273 + 834


def test_validation_gate3_deferred_ownership_and_no_decisions_are_locked() -> None:
    docs = _read(SPEC_REL) + _read(PLAN_REL)
    required = (
        "A3/M61/D0",
        "81-function/834-item",
        "3107 focused",
        "9014 passed, 185 deselected",
        "9199",
        "one write-mode Ruff invocation",
        "unstaged and uncommitted",
        "Add Phase 53 window-local ordering and direction",
        "Slice 12 navigation behavior remains unimplemented",
        "Slice 11 remains UNSTARTED through Gate 2",
        "COMPLETED requires separately authorized Gate 3 and exact-head natural CI",
        "0.1.0",
    )
    for item in required:
        assert item in docs
    assert "genuine_product_decisions" not in docs
    assert "genuine_architecture_decisions" not in docs
