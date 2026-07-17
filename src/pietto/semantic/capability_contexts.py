"""Private expression-stage and clause capability facts."""

from __future__ import annotations

from collections.abc import Iterable

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

__all__: tuple[str, ...] = ()


def _evidence(
    source: CapabilityEvidenceSource,
    source_path: str,
    source_reference: str,
    reason: CapabilityReasonCode | None = None,
    *,
    dialect: str | None = None,
    backend: str | None = None,
) -> CapabilityEvidence:
    """Build one exact ordered context-evidence entry."""

    return CapabilityEvidence(
        source,
        source_path,
        source_reference,
        reason,
        dialect=dialect,
        backend=backend,
    )


def _none() -> CapabilityDisposition:
    return CapabilityDisposition(CapabilityDispositionKind.NONE)


def _deferred(reason: str) -> CapabilityDisposition:
    return CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        reason,
    )


def _fact(
    domain: CapabilityDomain,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
    context: str,
    support: CapabilitySupport,
    evidence: tuple[CapabilityEvidence, ...],
    disposition: CapabilityDisposition | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            domain,
            subject=subject,
            operation=operation,
            operands=operands,
            context=context,
        ),
        support,
        _none() if disposition is None else disposition,
        evidence,
    )


def _freeze_contexts(
    facts: Iterable[CapabilityFact],
) -> tuple[CapabilityFact, ...]:
    """Freeze facts while preserving distinct same-key entries in input order."""

    if isinstance(facts, (str, bytes)):
        raise ValueError("Capability contexts require an iterable of facts")
    try:
        frozen = tuple(facts)
    except TypeError as exc:
        raise ValueError("Capability contexts require an iterable of facts") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen):
        raise ValueError("Capability contexts require exact capability facts")
    if len(set(frozen)) != len(frozen):
        raise ValueError("Capability contexts forbid exact duplicate facts")
    return frozen


_EXPRESSION_STAGE_FACTS: tuple[CapabilityFact, ...] = _freeze_contexts(
    (
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "literal_expression",
            "observed_stage",
            ("CONSTANT",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "primaryExpression and literal",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "LiteralExpr",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "_infer LiteralExpr branch and _literal_value_type",
                    CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueType and SemanticModel.expression_value_types",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "LiteralIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/lowering.py",
                    "_lower_expr_node LiteralExpr branch",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_expressions.py",
                    "test_literal_expression_maps_to_builtin_type",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-logical-type-literal-parameter-"
                    "nullability-inventory-v1.md",
                    "Literal Inventory",
                    CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "Expression Stage Contract",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "constant_scalar_expression",
            "observed_stage",
            ("CONSTANT",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "expression through primaryExpression",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "CallExpr UnaryExpr BinaryExpr ComparisonExpr BetweenExpr "
                    "IsNullExpr",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_CATALOG,
                    "src/pietto/semantic/catalog.py",
                    "BUILTIN_FUNCTIONS",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "_infer and recursive scalar result procedures",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueType and SemanticModel.expression_value_types",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "CallIR UnaryIR BinaryIR ComparisonIR BetweenIR IsNullIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/lowering.py",
                    "_lower_expr_node scalar branches",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_functions.py",
                    "scalar function result tests",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase17_core_scalar_expression_semantics.py",
                    "scalar operator result tests",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/operator-comparison-matrix-contract-v1.md",
                    "Scalar Function And Operator Matrix",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "Expression Stage Contract",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "resolved_row_reference",
            "observed_stage",
            ("ROW",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "dottedName",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "NameExpr and DottedNameExpr",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "_callable_row_schema _shape_row_schema _name_value_type "
                    "_qualified_name_value_type",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/let_bindings.py",
                    "_analyze_relation_let_clause and infer_row_expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "RowSchema and LetScopeSemanticInfo",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "FieldRefIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/lowering.py",
                    "_lower_expr_node NameExpr and DottedNameExpr branches",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_expressions.py",
                    "test_bare_field_uses_row_field_type_and_nullability",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_callable_bodies.py",
                    "test_valid_derive_body_uses_parameter_environment",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_field_derives.py",
                    "test_valid_field_derive_uses_same_shape_fields_and_builtins",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase40_let_binding_row_level_semantics.py",
                    "test_valid_table_and_query_let_validate_row_scope_and_succeed",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_group_by_keys.py",
                    "test_group_by_direct_field_row_let_is_semantically_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
                    "Row-level Scope",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "row_scalar_expression",
            "observed_stage",
            ("ROW",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "composite expression rules",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "scalar composite Expression classes",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_CATALOG,
                    "src/pietto/semantic/catalog.py",
                    "BUILTIN_FUNCTIONS",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "recursive inference plus row and name resolution",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/let_bindings.py",
                    "row-let inference and dependency walk",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueType RowSchema and expression_value_types",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "scalar ExpressionIR classes",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/lowering.py",
                    "scalar branches and admitted let expansion",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_functions.py",
                    "test_nested_lower_trim_returns_text_and_records_inner_call",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase17_core_scalar_expression_semantics.py",
                    "scalar expression semantics",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase40_let_binding_row_level_semantics.py",
                    "test_unary_binary_comparison_and_is_null_value_types_are_"
                    "preserved",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
                    "Row-level Scope",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "Expression Stage Contract",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "aggregate_dependent_expression",
            "observed_stage",
            ("GROUP",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "callSuffix and composite expression rules",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "CallExpr and composite Expression classes",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_CATALOG,
                    "src/pietto/semantic/aggregates.py",
                    "SEMANTIC_AGGREGATE_NAMES",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "semantic_aggregate_call_name contains_semantic_aggregate "
                    "child_expressions",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/relation_schemas.py",
                    "_aggregate_projection_diagnostics",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "project_grouped_schema and _aggregate_output_field",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueType and relation_row_schemas",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "AggregateCallIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/lowering.py",
                    "aggregate projection lowering",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "Expression Stage And Clause Capability Boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase19_count_semantics.py",
                    "test_direct_aliased_count_projection_is_semantically_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase21_group_by_semantic_validation.py",
                    "test_grouped_semantic_schema_for_bare_key_and_aggregates",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "Expression Stage Contract",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "group_output_reference",
            "observed_stage",
            ("GROUP",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "selectClause satisfyingClause orderByClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "SelectItem SatisfyingClause OrderItem",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/satisfying.py",
                    "_satisfying_output_scope and _name_value_type",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "_grouped_order_by_diagnostics",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "SatisfyingResultPredicateInfo",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "ResultPredicateIR and OrderItemIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "grouped result predicate and grouped order lowering",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_grouped_satisfying_over_aggregate_alias_is_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_grouped_satisfying_over_group_key_alias_is_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase27_grouped_order_semantics.py",
                    "test_grouped_order_accepts_supported_selected_outputs",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/v02-aggregate-surface-freeze-v1.md",
                    "grouped satisfying and ordering result scope",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
                    "grouped result scope",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.EXPRESSION_STAGE,
            "unresolved_reference_expression",
            "observed_stage",
            ("UNKNOWN",),
            "expression",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "dottedName callSuffix",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "NameExpr DottedNameExpr CallExpr",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "_UNKNOWN_VALUE_TYPE _name_value_type "
                    "_qualified_name_value_type _call_value_type",
                    CapabilityReasonCode.UNRESOLVED_EXPRESSION,
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueTypeKind.UNKNOWN",
                    CapabilityReasonCode.UNRESOLVED_EXPRESSION,
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_expressions.py",
                    "test_unknown_bare_field_reports_pie_s2102_and_records_unknown",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_functions.py",
                    "test_unknown_function_reports_pie_s2103",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-private-capability-key-disposition-evidence-"
                    "fact-foundation-v1.md",
                    "Bounded Reason-code Contract",
                    CapabilityReasonCode.UNRESOLVED_EXPRESSION,
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "conflict ledger and Expression Stage Contract",
                ),
            ),
        ),
    )
)


_CLAUSE_CAPABILITY_FACTS: tuple[CapabilityFact, ...] = _freeze_contexts(
    (
        _fact(
            CapabilityDomain.CLAUSE,
            "where",
            "admit",
            (
                "ROW",
                "Bool_when_known",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "pre_group_filter",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "tableBody and whereClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "WhereClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "type_relation_expressions where branch and _infer",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/predicate_checks.py",
                    "_check_bool_expression rejects known non-Bool only",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "division UNKNOWN result case",
                    CapabilityReasonCode.NO_CURRENT_RESULT_RULE,
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "null-literal no-concrete-type case",
                    CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "ValueType ValueTypeKind and RowSchema",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "FilterIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "relation where lowering",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "WHERE rendering",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "WHERE rendering",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "Clause Capability Boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_semantic_where.py",
                    "known Bool non-Bool and unknown predicate cases",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase17_single_input_qualified_field_binding.py",
                    "test_qualified_fields_bind_in_where_and_input_scope_ordering",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase40_let_binding_row_level_semantics.py",
                    "test_valid_table_and_query_let_validate_row_scope_and_succeed",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/bool-predicate-semantics-contract-v1.md",
                    "Known Bool And Three UNKNOWN Concepts",
                    CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "group_by",
            "admit",
            (
                "ROW",
                "no_result_type_constraint",
                "direct_input_field_or_direct_field_row_let",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "group_key",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "groupByClause and groupByItem dottedName",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "GroupByClause GroupByItem",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "_resolve_group_keys _effective_group_key_expression "
                    "_field_identity",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "RowSchema RowField",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "FieldRefIR and RelationIR.group_keys",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "_lower_group_keys",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "GROUP BY rendering and validation",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "GROUP BY rendering and validation",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.PROJECT,
                    "src/pietto/_project/aggregate_grouped_clause_facts.py",
                    "retained grouped-key evidence",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                    "POST60 advanced grouping owner slot",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase21_group_by_semantic_validation.py",
                    "test_grouped_semantic_schema_for_bare_key_and_aggregates",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_group_by_keys.py",
                    "test_group_by_qualified_and_chained_field_row_lets_are_"
                    "semantically_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase43-let-binding-aggregate-grouped-integration-"
                    "scope-lock-v1.md",
                    "Group-by row-let scope",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "satisfying",
            "admit",
            (
                "GROUP",
                "Bool",
                "bounded_result_predicate",
                "selected_group_key_and_aggregate_outputs",
                "selected_output_names_with_matching_aggregate_let_exception",
            ),
            "grouped_result_filter",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "satisfyingClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "SatisfyingClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/satisfying.py",
                    "check_satisfying_clauses _satisfying_output_scope "
                    "_infer_predicate _matching_aggregate_let_output",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "SatisfyingResultPredicateInfo",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "ResultPredicateIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "_lower_satisfying_expression and aggregate-let normalization",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "HAVING rendering after GROUP BY",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "HAVING rendering after GROUP BY",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.PROJECT,
                    "src/pietto/_project/aggregate_grouped_clause_facts.py",
                    "satisfying selected-output dependencies",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "Clause Capability Boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_grouped_satisfying_over_aggregate_alias_is_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_grouped_satisfying_over_group_key_alias_is_accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_satisfying_aggregate_wrapped.py",
                    "test_satisfying_aggregate_wrapped_row_let_is_semantically_"
                    "accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/v02-aggregate-surface-freeze-v1.md",
                    "GROUP BY-only satisfying result scope",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase43-let-binding-aggregate-grouped-integration-"
                    "scope-lock-v1.md",
                    "matching aggregate-let exception",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "order_by",
            "admit",
            (
                "ROW",
                "no_result_type_constraint",
                "current_nonaggregate_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "input_order",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "orderByClause and orderItem expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "OrderByClause OrderItem",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "no-GROUP order branch and row expression inference",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "RowSchema",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "OrderItemIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "_lower_order_by",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "ORDER BY rendering",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "ORDER BY rendering",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "Clause Capability Boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase12_order_by.py",
                    "test_semantic_accepts_input_fields_and_existing_expression_typing",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase12_order_by.py",
                    "test_projection_alias_is_not_an_order_by_name_scope",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase17_single_input_qualified_field_binding.py",
                    "test_qualified_fields_bind_in_where_and_input_scope_ordering",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase40_let_binding_row_level_semantics.py",
                    "test_valid_table_and_query_let_validate_row_scope_and_succeed",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/order-limit-contract-v1.md",
                    "Input-scope ORDER BY",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase40-let-binding-syntax-and-scope-contract-v1.md",
                    "no-GROUP input order let scope",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "order_by",
            "admit",
            (
                "GROUP",
                "no_result_type_constraint",
                "bare_selected_output_or_matching_group_key_row_let",
                "selected_group_key_and_aggregate_outputs",
                "selected_output_names_with_matching_group_key_let_exception",
            ),
            "grouped_result_order",
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "orderByClause and orderItem expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "OrderByClause OrderItem",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "_grouped_order_by_diagnostics and "
                    "_grouped_order_let_field_identity",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_MODEL,
                    "src/pietto/semantic/model.py",
                    "grouped relation RowSchema",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/model.py",
                    "OrderItemIR",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "_lower_grouped_order_by and selected-expression normalization",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "grouped ORDER BY validation and rendering",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "grouped ORDER BY validation and rendering",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.PROJECT,
                    "src/pietto/_project/aggregate_grouped_clause_facts.py",
                    "grouped order selected-output dependencies",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                    "POST60 advanced aggregation ordering slot",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase27_grouped_order_semantics.py",
                    "test_grouped_order_accepts_supported_selected_outputs",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_grouped_order_by.py",
                    "test_grouped_order_by_direct_field_row_let_is_semantically_"
                    "accepted",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/grouped-result-ordering-v1.md",
                    "bounded grouped selected-output ordering",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase43-let-binding-aggregate-grouped-integration-"
                    "scope-lock-v1.md",
                    "grouped order let exception",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "where",
            "admit",
            (
                "ROW",
                "Bool_when_known",
                "aggregate_dependent_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "pre_group_filter",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "whereClause expression grammar",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "WhereClause and CallExpr/composites",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "contains_semantic_aggregate and invalid_context_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "where branch and _append_invalid_count_context_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "row-level versus group-level tension",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase19_count_semantics.py",
                    "test_count_aggregate_diagnostics",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/aggregate-semantic-contract-v1.md",
                    "aggregate context boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/v02-aggregate-surface-freeze-v1.md",
                    "where remains row-level pre-aggregate filtering",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "group_by",
            "admit",
            (
                "ROW",
                "no_result_type_constraint",
                "non_field_group_key",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "group_key",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "groupByItem is dottedName only",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "GroupByItem key union",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "_resolve_group_keys and _resolve_input_field",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                    "POST60_ADVANCED_AGGREGATION_GROUPING broad expressions and "
                    "grouping",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase21_group_by_parser_ast_fail_closed.py",
                    "test_invalid_group_by_shapes_are_parser_errors",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_group_by_keys.py",
                    "test_non_slice4_group_by_let_consumers_remain_rejected",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase43-let-binding-aggregate-grouped-integration-"
                    "scope-lock-v1.md",
                    "exact field-row-let group-key boundary",
                ),
            ),
            _deferred("broad expression group keys require separate authorization"),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "satisfying",
            "admit",
            (
                "GROUP",
                "Bool",
                "global_aggregate_postfilter",
                "no_group_aggregate_outputs",
                "selected_output_aliases_do_not_create_satisfying_scope",
            ),
            "no_group_result_filter",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "optional satisfyingClause without syntactic group requirement",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "SatisfyingClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/satisfying.py",
                    "early no-GROUP and aggregate rejection",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                    "exact no-GROUP global aggregate post-filter ledger, existing "
                    "POST60 aggregate-filter owner, and no-new-owner lock",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-25-result-predicate-satisfying-mvp.md",
                    "GROUP BY-Only Boundary and Deferred Forms",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_no_group_satisfying_is_rejected",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_no_group_direct_aggregate_call_in_satisfying_uses_"
                    "aggregate_context_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/v02-aggregate-surface-freeze-v1.md",
                    "no-GROUP satisfying remains rejected",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase52-core-type-system-capability-foundation-"
                    "scope-lock-v1.md",
                    "no-GROUP post-filter conflict entry",
                ),
            ),
            _deferred(
                "global aggregate post-filtering requires separate authorization"
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "satisfying",
            "admit",
            (
                "GROUP",
                "Bool",
                "bounded_result_predicate",
                "unselected_raw_input_fields",
                "selected_output_names_required",
            ),
            "grouped_result_filter",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "satisfyingClause",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "SatisfyingClause NameExpr",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/satisfying.py",
                    "_satisfying_output_scope _name_value_type "
                    "_input_field_reference_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.PROJECT,
                    "src/pietto/_project/aggregate_grouped_clause_facts.py",
                    "selected versus unselected satisfying dependency classification",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "grouped result-scope tension",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_input_field_reference_in_satisfying_must_use_select_output",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase25_satisfying_semantics.py",
                    "test_renamed_group_key_exposes_only_alias_to_satisfying",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/v02-aggregate-surface-freeze-v1.md",
                    "result-scope names and unselected input rejection",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "order_by",
            "admit",
            (
                "ROW",
                "no_result_type_constraint",
                "aggregate_dependent_expression",
                "input_fields_and_row_lets",
                "select_output_aliases_forbidden",
            ),
            "input_order",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "orderItem expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "OrderItem and aggregate-dependent Expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "contains_semantic_aggregate and invalid_context_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/expressions.py",
                    "no-GROUP order branch and "
                    "_append_invalid_count_context_diagnostic",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-52-core-type-system-capability-foundation.md",
                    "row-level versus group-level tension",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase19_count_semantics.py",
                    "test_count_aggregate_diagnostics",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/aggregate-semantic-contract-v1.md",
                    "aggregate context boundary",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/grouped-result-ordering-v1.md",
                    "direct aggregate calls inside source order by remain out of scope",
                ),
            ),
        ),
        _fact(
            CapabilityDomain.CLAUSE,
            "order_by",
            "admit",
            (
                "GROUP",
                "no_result_type_constraint",
                "non_bare_or_unselected_grouped_order_expression",
                "grouped_input_or_unselected_outputs",
                "selected_output_names_required",
            ),
            "grouped_result_order",
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "orderItem expression",
                ),
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "src/pietto/ast_nodes.py",
                    "OrderItem",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/group_by.py",
                    "_grouped_order_by_diagnostics and PIE-S2321",
                ),
                _evidence(
                    CapabilityEvidenceSource.IR,
                    "src/pietto/ir/builder.py",
                    "_lower_grouped_order_by fail-closed normalization",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/relations.py",
                    "_validate_grouped_order_by requires match with selected GROUP "
                    "BY key or aggregate projection",
                    dialect="postgresql",
                    backend="postgresql",
                ),
                _evidence(
                    CapabilityEvidenceSource.BACKEND,
                    "src/pietto/sql/mysql_relations.py",
                    "_validate_grouped_order_by requires match with selected GROUP "
                    "BY key or aggregate projection",
                    dialect="mysql",
                    backend="private-mysql",
                ),
                _evidence(
                    CapabilityEvidenceSource.PROJECT,
                    "src/pietto/_project/aggregate_grouped_clause_facts.py",
                    "grouped order selected/unselected classification",
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/spec/pietto-active-roadmap-phase51-60-v1.md",
                    "POST60_ADVANCED_AGGREGATION_GROUPING ordering scope",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase21_group_by_semantic_validation.py",
                    "test_unsupported_grouped_order_by_items_emit_s2321",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase27_grouped_order_semantics.py",
                    "test_grouped_order_rejects_unsupported_item_shapes",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase43_let_binding_grouped_order_by.py",
                    "test_non_slice5_grouped_order_let_consumers_remain_rejected",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/grouped-result-ordering-v1.md",
                    "arbitrary grouped order expressions remain deferred",
                ),
            ),
            _deferred("broad grouped result ordering requires separate authorization"),
        ),
    )
)


_CAPABILITY_CONTEXT_FACTS: tuple[CapabilityFact, ...] = (
    _EXPRESSION_STAGE_FACTS + _CLAUSE_CAPABILITY_FACTS
)

_EXPRESSION_STAGE_SUBJECTS = (
    "literal_expression",
    "constant_scalar_expression",
    "resolved_row_reference",
    "row_scalar_expression",
    "aggregate_dependent_expression",
    "group_output_reference",
    "unresolved_reference_expression",
)
_EXPRESSION_STAGES = ("CONSTANT", "ROW", "GROUP", "UNKNOWN")

_CLAUSE_CONTEXTS = (
    ("where", "pre_group_filter"),
    ("group_by", "group_key"),
    ("satisfying", "grouped_result_filter"),
    ("satisfying", "no_group_result_filter"),
    ("order_by", "input_order"),
    ("order_by", "grouped_result_order"),
)
_CLAUSE_STAGES = ("ROW", "GROUP")
_CLAUSE_RESULTS = ("Bool_when_known", "Bool", "no_result_type_constraint")
_CLAUSE_SHAPES = (
    "current_nonaggregate_expression",
    "direct_input_field_or_direct_field_row_let",
    "bounded_result_predicate",
    "bare_selected_output_or_matching_group_key_row_let",
    "aggregate_dependent_expression",
    "non_field_group_key",
    "global_aggregate_postfilter",
    "non_bare_or_unselected_grouped_order_expression",
)
_CLAUSE_SCOPES = (
    "input_fields_and_row_lets",
    "selected_group_key_and_aggregate_outputs",
    "no_group_aggregate_outputs",
    "unselected_raw_input_fields",
    "grouped_input_or_unselected_outputs",
)
_CLAUSE_ALIAS_POLICIES = (
    "select_output_aliases_forbidden",
    "selected_output_names_with_matching_aggregate_let_exception",
    "selected_output_names_with_matching_group_key_let_exception",
    "selected_output_aliases_do_not_create_satisfying_scope",
    "selected_output_names_required",
)


def _expression_stage_complete(key: CapabilityKey) -> bool:
    return (
        key.subject in _EXPRESSION_STAGE_SUBJECTS
        and key.operation == "observed_stage"
        and len(key.operands) == 1
        and key.operands[0] in _EXPRESSION_STAGES
        and key.context == "expression"
        and key.dialect is None
        and key.extension is None
    )


def _clause_complete(key: CapabilityKey) -> bool:
    if (
        (key.subject, key.context) not in _CLAUSE_CONTEXTS
        or key.operation != "admit"
        or len(key.operands) != 5
        or key.dialect is not None
        or key.extension is not None
    ):
        return False
    stage, result, shape, scope, alias_policy = key.operands
    return (
        stage in _CLAUSE_STAGES
        and result in _CLAUSE_RESULTS
        and shape in _CLAUSE_SHAPES
        and scope in _CLAUSE_SCOPES
        and alias_policy in _CLAUSE_ALIAS_POLICIES
    )


def stage_clause_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]:
    """Return exact fact inputs and schema completeness for one context key."""

    if type(key) is not CapabilityKey:
        raise ValueError("Capability context lookup requires an exact key")
    if key.domain is CapabilityDomain.EXPRESSION_STAGE:
        return _EXPRESSION_STAGE_FACTS, _expression_stage_complete(key), None
    if key.domain is CapabilityDomain.CLAUSE:
        return _CLAUSE_CAPABILITY_FACTS, _clause_complete(key), None
    return (), False, None
