from __future__ import annotations

import ast
import hashlib
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Any, cast

from _phase54_active_gate2_manifest import (
    PHASE54_POST_SLICE12_INTERLUDE_BRANCH,
    PHASE54_POST_SLICE12_INTERLUDE_BASE,
    phase54_post_slice12_interlude_clean_topic_is_active,
    PHASE54_ACTIVE_GATE2_BASE,
    PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BASE,
    PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH,
    PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS,
    phase54_active_gate2_manifest_is_active as _phase54_active_gate2_is_active,
    phase54_slice11_substantive_recovery_is_active,
    phase54_slice12_product_repair3_is_active,
    phase54_slice12_product_repair10_is_active,
    phase54_slice12_product_repair11_is_active,
)

import pytest
from antlr4 import CommonTokenStream, InputStream
from antlr4.ListTokenSource import ListTokenSource
from antlr4.Token import Token

from pietto.errors import Diagnostic, DiagnosticErrorListener, Severity
from pietto.generated.PiettoLexer import PiettoLexer
from pietto.generated.PiettoParser import PiettoParser
from pietto.indentation import find_leading_tab_diagnostics, inject_indentation
from pietto.parser_api import parse_source
from pietto.ast_nodes import QueryDef, WindowExpr


REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_REL = (
    "docs/plan/phase-53-window-functions-generic-signature-nullability-foundation.md"
)
SPEC_REL = "docs/spec/phase53-window-syntax-contextual-grammar-contract-v1.md"
GRAMMAR_REL = "grammar/Pietto.g4"
AST_BUILDER_REL = "src/pietto/ast_builder.py"
PARSER_API_REL = "src/pietto/parser_api.py"
AST_NODES_REL = "src/pietto/ast_nodes.py"
TEST_REL = "tests/test_phase53_window_syntax_contextual_grammar_contract.py"

SPEC_TITLE = (
    "Phase 53 Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract v1"
)
SLICE2_PLAN_H2 = "Slice 2 Pietto-native Window Syntax And Contextual Grammar Contract"
SPEC_H2 = (
    "Status And Slice Identity",
    "Approved Product Authority",
    "Exact Canonical Syntax",
    "Introducer And Case Policy",
    "Clause Shape And Ordering",
    "Function Call Alias And Suffix Binding",
    "Grammar And Semantic Ownership",
    "AST Fail-closed Bridge",
    "Global Identifier Compatibility",
    "Contextual Keyword Compatibility",
    "Positive Grammar Matrix",
    "Negative Grammar Matrix",
    "Diagnostic And Location Contract",
    "Generated Source Contract",
    "Reader Hash And Repository State Closure",
    "Validation CI And Publication Boundary",
    "Public Behavior And Deferred Scope",
    "Stop Conditions",
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
FAIL_CLOSED_MESSAGE = (
    "Window syntax is recognized, but WindowSpec AST preservation starts in "
    "Phase 53 Slice 3."
)
BASE_HEAD_SHA = "3c1feab5bc70d407e9e4d7ccd0c5d489eec0ee68"
PHASE54_SLICE2_BASE_HEAD_SHA = "d8a5e9ab3de70ce30575513c73560c86430eca63"
PHASE54_SLICE4_BASE_HEAD_SHA = "15bae172ee151e370fe59d3bf909d735aee6aa90"
PHASE54_SLICE5_BASE_HEAD_SHA = "0f3c955c5a5fbd8046ef611ad1bef0b636c8be01"
PHASE54_SLICE6_BASE_HEAD_SHA = "c44a4271d9592cb393d2232f127a59d8466cc60a"
PHASE54_SLICE7_BASE_HEAD_SHA = "49e95afcc5ed8c3394e6b19a4ea17679bae1bb16"
PHASE54_SLICE8_BASE_HEAD_SHA = "027b33cafcfd58916a89e299487dad38d24ade6c"
PHASE54_SLICE9_BASE_HEAD_SHA = "0ceb9a476e6592714cdc76845949ba0ae5123eb5"
PHASE54_SLICE2_STATE_REL = "tests/_phase54_active_gate2_manifest.py"

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

GENERATED_PATHS = (
    "src/pietto/generated/Pietto.interp",
    "src/pietto/generated/Pietto.tokens",
    "src/pietto/generated/PiettoLexer.interp",
    "src/pietto/generated/PiettoLexer.py",
    "src/pietto/generated/PiettoLexer.tokens",
    "src/pietto/generated/PiettoParser.py",
    "src/pietto/generated/PiettoVisitor.py",
    "src/pietto/generated/__init__.py",
)
GENERATED_MUTATION_PATHS = set(GENERATED_PATHS) - {"src/pietto/generated/__init__.py"}

EXPECTED_TEST_FUNCTIONS = (
    "test_slice2_artifact_paths_and_heading_contracts_are_exact",
    "test_candidate_b_global_window_and_contextual_keyword_policy_is_locked",
    "test_combined_grammar_rules_and_token_order_are_exact",
    "test_generated_inventory_and_exact_mutation_set_are_locked",
    "test_raw_parser_accepts_canonical_window_shapes",
    "test_partition_and_order_items_accept_generic_expression_shapes",
    "test_raw_parser_rejects_malformed_or_deferred_window_shapes",
    "test_parse_source_fails_closed_before_slice3_ast_preservation",
    "test_fail_closed_diagnostic_code_message_and_window_location_are_exact",
    "test_lowercase_window_is_rejected_in_every_identifier_position",
    "test_case_variant_window_identifiers_remain_accepted",
    "test_partition_and_over_remain_usable_contextual_identifiers",
    "test_approved_function_names_remain_ordinary_identifiers",
    "test_historical_unsupported_window_samples_remain_negative",
    "test_no_ast_semantic_ir_sql_or_public_surface_widening_is_locked",
    "test_slice2_dirty_clean_and_depth_one_repository_states_are_locked",
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
    if result.returncode == 1:
        assert result.stdout == ""
        return None
    lines = result.stdout.splitlines()
    assert len(lines) == 1
    return lines[0]


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


def _raw_tokens(lexer: PiettoLexer) -> list[Token]:
    tokens: list[Token] = []
    while True:
        token = lexer.nextToken()
        assert token is not None
        tokens.append(token)
        if token.type == Token.EOF:
            return tokens


def _raw_parse(
    source: str,
    *,
    path: str = "slice2-window-raw.pietto",
) -> tuple[Any, tuple[Token, ...], tuple[Diagnostic, ...]]:
    lexer_listener = DiagnosticErrorListener(path)
    lexer = PiettoLexer(InputStream(source))
    lexer.removeErrorListeners()
    lexer.addErrorListener(lexer_listener)
    indentation = inject_indentation(
        _raw_tokens(lexer),
        newline_type=PiettoLexer.NEWLINE,
        indent_type=PiettoParser.INDENT,
        dedent_type=PiettoParser.DEDENT,
        path=path,
    )

    parser_listener = DiagnosticErrorListener(path)
    token_source = ListTokenSource(list(indentation.tokens), path)
    token_stream = CommonTokenStream(cast(Any, token_source))
    parser = PiettoParser(token_stream)
    parser.removeErrorListeners()
    parser.addErrorListener(parser_listener)
    tree = parser.script()

    diagnostics = tuple(
        sorted(
            (
                *lexer_listener.diagnostics,
                *find_leading_tab_diagnostics(source, path=path),
                *indentation.diagnostics,
                *parser_listener.diagnostics,
            ),
            key=lambda item: (
                item.location.line,
                item.location.column,
                item.code,
                item.message,
            ),
        )
    )
    return tree, indentation.tokens, diagnostics


def _window_select_items(tree: Any) -> tuple[Any, ...]:
    items: list[Any] = []
    for definition in tree.definition():
        query = definition.queryDefinition()
        table = definition.tableDefinition()
        relation = query if query is not None else table
        if relation is None:
            continue
        items.extend(relation.tableBody().selectClause().selectBody().selectItem())
    return tuple(item for item in items if item.windowExpression() is not None)


RAW_POSITIVE_CASES = (
    (
        "order_only_omitted_direction",
        _window_query("""
            order by:
                observed_at
        """),
        1,
    ),
    (
        "one_partition_one_ascending_order",
        _window_query("""
            partition by:
                account_id
            order by:
                observed_at asc
        """),
        1,
    ),
    (
        "multiple_partition_mixed_order",
        _window_query("""
            partition by:
                account_id
                region
            order by:
                observed_at desc
                sequence_id asc
        """),
        1,
    ),
    (
        "blank_lines",
        _window_query("""

            partition by:

                account_id

            order by:

                observed_at

        """),
        1,
    ),
    (
        "qualified_call",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = analytics.row_number()",
        ),
        1,
    ),
    (
        "arguments_and_trailing_comma",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="previous = lag(value, 1,)",
        ),
        1,
    ),
    (
        "unrelated_function",
        _window_query(
            """
            partition by:
                account_id
            """,
            projection="custom_value = custom(value)",
        ),
        1,
    ),
    (
        "two_independent_windows",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
            "                observed_at\n"
            "        previous = lag(value, 1) window:\n"
            "            partition by:\n"
            "                account_id\n"
            "            order by:\n"
            "                observed_at desc\n"
        ),
        2,
    ),
    (
        "surrounding_ordinary_items",
        _window_query(
            """
            order by:
                observed_at
            """,
            before=("account_id",),
            after=("value",),
        ),
        1,
    ),
)

GENERIC_EXPRESSION_CASES = (
    ("qualified", "account.id", "events.observed_at"),
    ("arithmetic", "account_id + region_id", "observed_at + 1"),
    ("calls", "lower(region)", "coalesce(observed_at, fallback_at)"),
    ("parenthesized", "(account_id == owner_id)", "(observed_at + offset)"),
)

RAW_NEGATIVE_CASES = (
    (
        "missing_window_colon",
        _window_query("""
            order by:
                observed_at
        """).replace(" window:\n", " window\n", 1),
    ),
    (
        "missing_outer_window_indent",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "        order by:\n"
            "            observed_at\n"
        ),
    ),
    (
        "inconsistent_nested_indent",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
            "                observed_at\n"
            "              sequence_id\n"
        ),
    ),
    (
        "empty_window",
        "query ranked:\n    from rows\n    select:\n        rn = row_number() window:\n",
    ),
    (
        "empty_partition",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            partition by:\n"
            "            order by:\n"
            "                observed_at\n"
        ),
    ),
    (
        "empty_order",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window:\n"
            "            order by:\n"
        ),
    ),
    (
        "duplicate_partition",
        _window_query("""
            partition by:
                account_id
            partition by:
                region
            order by:
                observed_at
        """),
    ),
    (
        "duplicate_order",
        _window_query("""
            order by:
                observed_at
            order by:
                sequence_id
        """),
    ),
    (
        "partition_after_order",
        _window_query("""
            order by:
                observed_at
            partition by:
                account_id
        """),
    ),
    (
        "unknown_subclause",
        _window_query("""
            cluster by:
                account_id
        """),
    ),
    (
        "named_window_reference",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        rn = row_number() window recent\n"
        ),
    ),
    (
        "named_window_declaration",
        (
            "query ranked:\n"
            "    from rows\n"
            "    select:\n"
            "        id\n"
            "    window recent:\n"
            "        order by:\n"
            "            observed_at\n"
        ),
    ),
    (
        "frame_syntax",
        _window_query("""
            order by:
                observed_at
            rows between unbounded preceding and current row
        """),
    ),
    (
        "nulls_first",
        _window_query("""
            order by:
                observed_at nulls first
        """),
    ),
    (
        "nulls_last",
        _window_query("""
            order by:
                observed_at nulls last
        """),
    ),
    (
        "qualify",
        _window_query("""
            order by:
                observed_at
        """)
        + "    qualify rn == 1\n",
    ),
    (
        "multiple_window_suffixes",
        _window_query("""
            order by:
                observed_at
        """)
        + "        window:\n            order by:\n                sequence_id\n",
    ),
    (
        "suffix_on_non_call_shape",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = (row_number())",
        ),
    ),
    (
        "malformed_order_item",
        _window_query("""
            order by:
                observed_at +
        """),
    ),
    (
        "malformed_partition_item",
        _window_query("""
            partition by:
                account_id +
            order by:
                observed_at
        """),
    ),
)

FAIL_CLOSED_CASES = (
    (
        "order_only",
        _window_query("""
            order by:
                observed_at
        """),
        27,
    ),
    (
        "qualified",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="rn = analytics.row_number()",
        ),
        37,
    ),
    (
        "arguments",
        _window_query(
            """
            order by:
                observed_at
            """,
            projection="previous = lag(value, 1)",
        ),
        34,
    ),
    (
        "unrelated",
        _window_query(
            """
            partition by:
                account_id
            """,
            projection="custom_value = custom(value)",
        ),
        38,
    ),
)

LOWERCASE_WINDOW_IDENTIFIER_CASES = (
    ("query_name", "query window:\n    from rows\n    select:\n        id\n"),
    ("source_name", 'source window is postgres.table("rows")\n'),
    ("table_name", "table window:\n    from rows\n    select:\n        id\n"),
    ("from_relation", "query q:\n    from window\n    select:\n        id\n"),
    ("shape_field", "shape Row:\n    window: Int\n"),
    (
        "selected_alias",
        "query q:\n    from rows\n    select:\n        window = value\n",
    ),
    (
        "let_name",
        "query q:\n    from rows\n    let:\n        window = value\n    select:\n        value\n",
    ),
    ("derive_parameter", "derive f(window: Int) -> Int:\n    window\n"),
    ("dotted_part", 'source s is postgres.window("rows")\n'),
    ("function_name", "source s is window()\n"),
    (
        "relationship_name",
        "relationship window:\n    endpoint left: rows\n    endpoint right: rows\n",
    ),
    (
        "endpoint_local_name",
        "relationship r:\n    endpoint window: rows\n    endpoint right: rows\n",
    ),
)

CASE_VARIANT_IDENTIFIERS = ("Window", "WINDOW")
CONTEXTUAL_IDENTIFIERS = ("partition", "over")
HISTORICAL_NEGATIVE_SOURCES = (
    (
        "window_clause",
        (
            "query projected:\n"
            "    from input_relation\n"
            "    window recent\n"
            "    select:\n"
            "        id\n"
        ),
    ),
    (
        "sql_over_shape",
        (
            "query projected:\n"
            "    from input_relation\n"
            "    select:\n"
            "        total = sum(amount) over (region)\n"
        ),
    ),
)


def test_slice2_artifact_paths_and_heading_contracts_are_exact() -> None:
    assert (REPO_ROOT / PLAN_REL).is_file()
    assert (REPO_ROOT / SPEC_REL).is_file()
    assert (REPO_ROOT / TEST_REL).is_file()
    assert _headings(SPEC_REL, 1) == (SPEC_TITLE,)
    assert _headings(SPEC_REL, 2) == SPEC_H2
    assert _headings(SPEC_REL, 3) == ()
    assert _headings(PLAN_REL, 2)[-15:] == (
        SLICE2_PLAN_H2,
        "Slice 3 WindowSpec, Extension-compatible WindowFunctionIdentity, And AST "
        "Contract",
        "Slice 4 Generic Type-variable, Constraint, And Exact Compatibility Foundation",
        "Slice 5 Nullability Algebra And Signature Result-formula Foundation",
        "Slice 6 Private Window Semantic Carrier, WINDOW Stage, Dependency, And Result Roles",
        "Slice 7 row_number Direct-field MVP",
        "Slice 8 rank / dense_rank And Peer Semantics",
        "Slice 9 percent_rank / cume_dist / ntile",
        "Slice 10 Partition Binding, Multi-key Visibility, And Diagnostics",
        "Slice 11 Window-local Ordering, Direction, Mandatory-order Policy, And Determinism",
        "Slice 12 lag / lead Navigation, Offset, Default, And Nullability",
        "Slice 13 — Grouped-result Ranking, Aggregate-result Inputs, And Bounded Let Visibility",
        "Slice 14 — Multiple Window Outputs, Final-order Alias, Downstream Schema, And Lineage",
        "Slice 15 — Window IR, Dual-backend Lowering, And Window-function Facts",
        "Slice 16 — Completion Audit, Status Lock, Dialect, Privacy, And "
        "No-authority Closure",
    )
    assert _headings(PLAN_REL, 2).count(SLICE2_PLAN_H2) == 1

    tree = ast.parse(_read(TEST_REL), filename=TEST_REL)
    test_functions = tuple(
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    )
    assert test_functions == EXPECTED_TEST_FUNCTIONS
    item_counts = (
        1,
        1,
        1,
        1,
        len(RAW_POSITIVE_CASES),
        len(GENERIC_EXPRESSION_CASES),
        len(RAW_NEGATIVE_CASES),
        len(FAIL_CLOSED_CASES),
        1,
        len(LOWERCASE_WINDOW_IDENTIFIER_CASES),
        len(CASE_VARIANT_IDENTIFIERS),
        len(CONTEXTUAL_IDENTIFIERS),
        len(WINDOW_FUNCTION_NAMES),
        len(HISTORICAL_NEGATIVE_SOURCES),
        1,
        1,
    )
    assert len(test_functions) == len(item_counts) == 16
    assert sum(item_counts) == 70


def test_candidate_b_global_window_and_contextual_keyword_policy_is_locked() -> None:
    grammar = _read(GRAMMAR_REL)
    spec = _read(SPEC_REL)
    assert "Candidate B is canonical" in spec
    assert "function(arguments) window:" in spec
    assert "WINDOW: 'window';" in grammar
    assert "PARTITION: 'partition';" in grammar
    identifier_token = grammar.index("IDENTIFIER\n    :")
    assert grammar.index("WINDOW: 'window';") < identifier_token
    assert grammar.index("PARTITION: 'partition';") < identifier_token
    identifier_start = grammar.index("\nidentifier\n") + 1
    call_suffix_start = grammar.index("\ncallSuffix\n") + 1
    name_part_start = grammar.index("\nnamePart\n") + 1
    identifier_rule = grammar[identifier_start:call_suffix_start]
    name_part_rule = grammar[name_part_start:identifier_start]
    assert "| PARTITION" in identifier_rule
    assert "WINDOW" not in identifier_rule
    assert "WINDOW" not in name_part_rule
    assert "OVER:" not in grammar
    for name in WINDOW_FUNCTION_NAMES:
        assert f"{name.upper()}:" not in grammar


def test_combined_grammar_rules_and_token_order_are_exact() -> None:
    grammar = _read(GRAMMAR_REL)
    normalized = " ".join(grammar.split())
    for rule in (
        "selectItem : identifier ASSIGN windowExpression | identifier ASSIGN expression NEWLINE | expression NEWLINE ;",
        "windowExpression : dottedName callSuffix windowSpec ;",
        "windowSpec : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT ;",
        "windowSpecBody : NEWLINE* partitionByClause NEWLINE* orderByClause? NEWLINE* | NEWLINE* orderByClause NEWLINE* ;",
        "partitionByClause : PARTITION BY COLON NEWLINE NEWLINE* INDENT windowPartitionBody DEDENT ;",
        "windowPartitionBody : NEWLINE* windowPartitionItem (windowPartitionItem | NEWLINE)* ;",
        "windowPartitionItem : expression NEWLINE ;",
    ):
        assert rule in normalized, rule
    assert normalized.count("windowExpression :") == 1
    assert normalized.count("windowSpec :") == 1
    assert normalized.count("partitionByClause :") == 1


def test_generated_inventory_and_exact_mutation_set_are_locked() -> None:
    generated = tuple(
        f"src/pietto/generated/{path.name}"
        for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
        if path.is_file()
    )
    assert generated == tuple(sorted(GENERATED_PATHS))
    assert len(generated) == 8
    assert (REPO_ROOT / "src/pietto/generated/__init__.py").read_bytes() == b""
    changed = set(
        _git_output(["diff", "--name-only", "--", "src/pietto/generated"]).splitlines()
    ) - {""}
    assert changed in (set(), GENERATED_MUTATION_PATHS)


@pytest.mark.parametrize(
    ("name", "source", "expected_windows"),
    RAW_POSITIVE_CASES,
    ids=[case[0] for case in RAW_POSITIVE_CASES],
)
def test_raw_parser_accepts_canonical_window_shapes(
    name: str,
    source: str,
    expected_windows: int,
) -> None:
    tree, tokens, diagnostics = _raw_parse(source)
    assert diagnostics == (), name
    window_items = _window_select_items(tree)
    assert len(window_items) == expected_windows
    window_tokens = tuple(token for token in tokens if token.type == PiettoLexer.WINDOW)
    assert len(window_tokens) == expected_windows
    assert all(
        item.windowExpression().windowSpec().WINDOW() is not None
        for item in window_items
    )
    if name == "surrounding_ordinary_items":
        assert (window_tokens[0].line, window_tokens[0].column + 1) == (5, 27)


@pytest.mark.parametrize(
    ("name", "partition_expression", "order_expression"),
    GENERIC_EXPRESSION_CASES,
    ids=[case[0] for case in GENERIC_EXPRESSION_CASES],
)
def test_partition_and_order_items_accept_generic_expression_shapes(
    name: str,
    partition_expression: str,
    order_expression: str,
) -> None:
    source = _window_query(
        f"""
        partition by:
            {partition_expression}
        order by:
            {order_expression}
        """
    )
    tree, _, diagnostics = _raw_parse(source)
    assert diagnostics == (), name
    window_spec = _window_select_items(tree)[0].windowExpression().windowSpec()
    assert (
        len(
            window_spec.windowSpecBody()
            .partitionByClause()
            .windowPartitionBody()
            .windowPartitionItem()
        )
        == 1
    )
    assert (
        len(window_spec.windowSpecBody().orderByClause().orderByBody().orderItem()) == 1
    )


@pytest.mark.parametrize(
    ("name", "source"),
    RAW_NEGATIVE_CASES,
    ids=[case[0] for case in RAW_NEGATIVE_CASES],
)
def test_raw_parser_rejects_malformed_or_deferred_window_shapes(
    name: str,
    source: str,
) -> None:
    _, _, diagnostics = _raw_parse(source)
    _, _, repeated = _raw_parse(source)
    assert diagnostics, name
    assert diagnostics == repeated
    assert all(
        diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == "slice2-window-raw.pietto"
        and diagnostic.location.line >= 1
        and diagnostic.location.column >= 1
        for diagnostic in diagnostics
    )


@pytest.mark.parametrize(
    ("name", "source", "expected_column"),
    FAIL_CLOSED_CASES,
    ids=[case[0] for case in FAIL_CLOSED_CASES],
)
def test_parse_source_fails_closed_before_slice3_ast_preservation(
    name: str,
    source: str,
    expected_column: int,
) -> None:
    result = parse_source(source, path="slice2-window.pietto")
    assert result.ast is not None, name
    assert result.diagnostics == ()
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    assert (expression.spec.span.line, expression.spec.span.column) == (
        4,
        expected_column,
    )
    assert FAIL_CLOSED_MESSAGE not in repr(result)


def test_fail_closed_diagnostic_code_message_and_window_location_are_exact() -> None:
    source = _window_query("""
        partition by:
            account_id
            region
        order by:
            observed_at desc
            sequence_id
    """)
    result = parse_source(source, path="slice2-window.pietto")
    assert result.ast is not None
    assert result.diagnostics == ()
    relation = cast(QueryDef, result.ast.definitions[-1])
    expression = relation.select_items[0].expression
    assert isinstance(expression, WindowExpr)
    assert expression.span.path == "slice2-window.pietto"
    assert (expression.spec.span.line, expression.spec.span.column) == (4, 27)
    assert FAIL_CLOSED_MESSAGE not in repr(result)


@pytest.mark.parametrize(
    ("position", "source"),
    LOWERCASE_WINDOW_IDENTIFIER_CASES,
    ids=[case[0] for case in LOWERCASE_WINDOW_IDENTIFIER_CASES],
)
def test_lowercase_window_is_rejected_in_every_identifier_position(
    position: str,
    source: str,
) -> None:
    result = parse_source(source, path=f"window-{position}.pietto")
    assert result.ast is None, position
    assert result.diagnostics
    assert all(
        diagnostic.code == "PIE-P1000"
        and diagnostic.severity is Severity.ERROR
        and diagnostic.location.path == f"window-{position}.pietto"
        for diagnostic in result.diagnostics
    )


@pytest.mark.parametrize("identifier", CASE_VARIANT_IDENTIFIERS)
def test_case_variant_window_identifiers_remain_accepted(identifier: str) -> None:
    result = parse_source(f"type {identifier} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == identifier


@pytest.mark.parametrize("identifier", CONTEXTUAL_IDENTIFIERS)
def test_partition_and_over_remain_usable_contextual_identifiers(
    identifier: str,
) -> None:
    result = parse_source(f"type {identifier} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == identifier


@pytest.mark.parametrize("function_name", WINDOW_FUNCTION_NAMES)
def test_approved_function_names_remain_ordinary_identifiers(
    function_name: str,
) -> None:
    result = parse_source(f"type {function_name} = Int\n")
    assert result.diagnostics == ()
    assert result.ast is not None
    assert result.ast.definitions[0].name == function_name


@pytest.mark.parametrize(
    ("name", "source"),
    HISTORICAL_NEGATIVE_SOURCES,
    ids=[case[0] for case in HISTORICAL_NEGATIVE_SOURCES],
)
def test_historical_unsupported_window_samples_remain_negative(
    name: str,
    source: str,
) -> None:
    result = parse_source(source, path=f"historical-{name}.pietto")
    assert result.ast is None
    assert result.diagnostics
    assert any(diagnostic.code == "PIE-P1000" for diagnostic in result.diagnostics)


def test_no_ast_semantic_ir_sql_or_public_surface_widening_is_locked() -> None:
    assert _sha256(PARSER_API_REL) == (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    )
    assert (
        _sha256(AST_NODES_REL)
        == "bbfd121446d62d33c7990b80d17579d3f8b55763ce1b5f93ee17247cbd2ce0c2"
    )
    assert "class WindowSpec" in _read(AST_NODES_REL)
    assert "class WindowExpr" in _read(AST_NODES_REL)
    changed_source = set(
        _git_output(["diff", "--name-only", "--", "src/pietto"]).splitlines()
    ) - {""}
    allowed_source = {
        "src/pietto/ir/model.py",
        "src/pietto/ir/lowering.py",
        "src/pietto/ir/builder.py",
        "src/pietto/sql/expressions.py",
        "src/pietto/sql/relations.py",
        "src/pietto/sql/mysql_expressions.py",
        "src/pietto/sql/mysql_relations.py",
        "src/pietto/semantic/capability_facts.py",
    }
    _, phase54_modified = _phase54_slice2_paths()
    phase54_changed_source = {
        path for path in phase54_modified if path.startswith("src/pietto/")
    }
    recovery_changed_source = {
        path
        for path in PHASE54_SLICE11_SUBSTANTIVE_RECOVERY_MODIFIED_PATHS
        if path.startswith("src/pietto/")
    }
    product_repair3_changed_source = {
        path
        for path in PHASE54_SLICE12_PRODUCT_REPAIR3_MODIFIED_PATHS
        if path.startswith("src/pietto/")
    }
    product_repair10_changed_source = {
        path
        for path in PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS
        if path.startswith("src/pietto/")
    }
    product_repair11_changed_source = {
        path
        for path in PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS
        if path.startswith("src/pietto/")
    }
    assert changed_source in (
        set(),
        allowed_source,
        phase54_changed_source,
        recovery_changed_source,
        product_repair3_changed_source,
        product_repair10_changed_source,
        product_repair11_changed_source,
    )
    if changed_source == recovery_changed_source:
        assert phase54_slice11_substantive_recovery_is_active()
    elif changed_source == product_repair3_changed_source:
        assert phase54_slice12_product_repair3_is_active()
    elif (
        changed_source == product_repair11_changed_source
        and phase54_slice12_product_repair11_is_active()
    ):
        assert phase54_slice12_product_repair11_is_active()
    elif changed_source == product_repair10_changed_source:
        assert phase54_slice12_product_repair10_is_active()


def test_slice2_dirty_clean_and_depth_one_repository_states_are_locked() -> None:
    if phase54_slice12_product_repair11_is_active():
        tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
        untracked = set(
            _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
        ) - {""}
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR11_MODIFIED_PATHS)
        assert untracked == set()
        assert _git_output(["diff", "--cached", "--name-status"]) == ""
        assert _git_output(["branch", "--show-current"]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR11_BRANCH
        )
        assert (
            _git_output(["rev-parse", "HEAD"]) == PHASE54_SLICE12_PRODUCT_REPAIR11_BASE
        )
        assert _git_optional_ref("refs/heads/main") == PHASE54_ACTIVE_GATE2_BASE
        assert (
            _git_optional_ref("refs/remotes/origin/main") == PHASE54_ACTIVE_GATE2_BASE
        )
        return
    if phase54_slice12_product_repair10_is_active():
        tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
        untracked = set(
            _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
        ) - {""}
        assert tracked == set(PHASE54_SLICE12_PRODUCT_REPAIR10_MODIFIED_PATHS)
        assert untracked == set()
        assert _git_output(["diff", "--cached", "--name-status"]) == ""
        assert _git_output(["branch", "--show-current"]) == (
            PHASE54_SLICE12_PRODUCT_REPAIR10_BRANCH
        )
        assert (
            _git_output(["rev-parse", "HEAD"]) == PHASE54_SLICE12_PRODUCT_REPAIR10_BASE
        )
        assert _git_optional_ref("refs/heads/main") == PHASE54_ACTIVE_GATE2_BASE
        assert (
            _git_optional_ref("refs/remotes/origin/main") == PHASE54_ACTIVE_GATE2_BASE
        )
        return
    if _phase54_active_gate2_is_active():
        return
    tracked = set(_git_output(["diff", "--name-only"]).splitlines()) - {""}
    name_status = tuple(_git_output(["diff", "--name-status"]).splitlines())
    untracked = set(
        _git_output(["ls-files", "--others", "--exclude-standard"]).splitlines()
    ) - {""}
    cached = tuple(_git_output(["diff", "--cached", "--name-status"]).splitlines())
    assert cached == ()
    assert name_status == tuple(f"M\t{path}" for path in sorted(tracked))

    branch = _git_output(["branch", "--show-current"])
    head = _git_output(["rev-parse", "HEAD"])
    main = _git_optional_ref("refs/heads/main")
    origin_main = _git_optional_ref("refs/remotes/origin/main")
    dirty = tracked | untracked
    phase54_added, phase54_modified = _phase54_slice2_paths()
    phase54_allowlist = phase54_added | phase54_modified
    assert dirty in (set(), ALLOWLIST_PATHS, phase54_allowlist)

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
        assert tracked == untracked == set()
        if branch == PHASE54_POST_SLICE12_INTERLUDE_BRANCH:
            # The clean topic projection keeps its own topology assertions and
            # then continues into the shared inventory below: returning early
            # would leave the refreshed counts unverified in exactly the
            # projection the publication lifecycle checks out.
            assert phase54_post_slice12_interlude_clean_topic_is_active()
            assert main == origin_main == PHASE54_POST_SLICE12_INTERLUDE_BASE
        else:
            assert branch in ("", "main")
            if branch == "main":
                assert main == head
            if main is not None:
                assert main == head
            if origin_main is not None:
                assert origin_main == head

    readable_paths = set(_git_output(["ls-files"]).splitlines()) | untracked
    assert len(readable_paths) == 933
    assert sum(path.endswith(".py") for path in readable_paths) == 571
    assert sum(path.endswith(".md") for path in readable_paths) == 266
    test_modules = {
        path
        for path in readable_paths
        if path.startswith("tests/test_") and path.endswith(".py")
    }
    assert len(test_modules) == 462
    top_level_tests = 0
    for relative in sorted(test_modules):
        tree = ast.parse(_read(relative), filename=relative)
        top_level_tests += sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name.startswith("test_")
            for node in tree.body
        )
    assert top_level_tests == 5330
    assert len(GENERATED_PATHS) == 8
    goldens = {
        path
        for path in readable_paths
        if path.startswith("tests/fixtures/golden/")
        and (path.endswith(".sql") or path.endswith(".json"))
    }
    assert len(goldens) == 37


_SLICE11_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-window-local-ordering-direction-determinism-contract-v1.md",
    "src/pietto/semantic/window_order_analysis.py",
    "tests/test_phase53_window_local_ordering_direction_determinism_contract.py",
)
# Phase 53 Slice 13 reader migration.
