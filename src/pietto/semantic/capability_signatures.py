"""Private scalar-function and operator signature facts."""

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
    """Build one exact ordered signature-evidence entry."""

    return CapabilityEvidence(
        source,
        source_path,
        source_reference,
        reason,
        dialect=dialect,
        backend=backend,
    )


def _fact(
    domain: CapabilityDomain,
    subject: str,
    operation: str,
    operands: tuple[str, ...],
    evidence: tuple[CapabilityEvidence, ...],
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            domain,
            subject=subject,
            operation=operation,
            operands=operands,
            context="expression",
        ),
        CapabilitySupport.SUPPORTED,
        CapabilityDisposition(CapabilityDispositionKind.NONE),
        evidence,
    )


def _freeze_signatures(
    facts: Iterable[CapabilityFact],
) -> tuple[CapabilityFact, ...]:
    """Freeze facts while preserving distinct same-key entries in input order."""

    if isinstance(facts, (str, bytes)):
        raise ValueError("Capability signatures require an iterable of facts")
    try:
        frozen = tuple(facts)
    except TypeError as exc:
        raise ValueError("Capability signatures require an iterable of facts") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen):
        raise ValueError("Capability signatures require exact capability facts")
    if len(set(frozen)) != len(frozen):
        raise ValueError("Capability signatures forbid exact duplicate facts")
    return frozen


def _scalar_function_evidence(name: str) -> tuple[CapabilityEvidence, ...]:
    semantic_test = {
        "lower": "test_text_transform_function_returns_text",
        "trim": "test_text_transform_function_returns_text",
        "len": "test_len_returns_int",
        "matches": "test_matches_returns_bool_and_is_valid_where_predicate",
    }[name]
    ir_test = (
        "test_matches_call_lowers_as_bool_expression"
        if name == "matches"
        else "test_builtin_call_lowers_with_callable_symbol"
    )
    postgres_test = {
        "lower": "test_lower_and_trim_calls_render_recursively",
        "trim": "test_lower_and_trim_calls_render_recursively",
        "len": "test_len_call_uses_postgres_length",
        "matches": "test_matches_call_uses_postgres_regex_operator",
    }[name]
    mysql_path = (
        "tests/test_sql_mysql_relations.py"
        if name == "matches"
        else "tests/test_sql_mysql_expressions.py"
    )
    mysql_test = (
        "test_matches_relation_fails_closed_without_approximation"
        if name == "matches"
        else "test_approved_function_mappings_are_uppercase_and_recursive"
    )
    mysql_reference = (
        "_render_call rejects matches"
        if name == "matches"
        else "_FUNCTION_NAMES and _render_call"
    )
    mysql_reason = (
        CapabilityReasonCode.DIALECT_LOWERING_GAP if name == "matches" else None
    )
    postgres_reference = (
        "_FUNCTION_ARITIES and _render_call matches branch"
        if name == "matches"
        else "_FUNCTION_NAMES, _FUNCTION_ARITIES, and _render_call"
    )
    evidence = (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "primaryExpression and callSuffix",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "CallExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/catalog.py",
            f'BuiltinFunction and BUILTIN_FUNCTIONS["{name}"]',
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_call_value_type and _call_argument_types",
            CapabilityReasonCode.UNKNOWN_NULLABILITY,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType and EffectiveNullability.UNKNOWN",
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", "CallIR"),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node CallExpr branch",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            postgres_reference,
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            mysql_reference,
            mysql_reason,
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_functions.py",
            semantic_test,
        ),
        _evidence(
            CapabilityEvidenceSource.TEST, "tests/test_ir_expressions.py", ir_test
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            postgres_test,
        ),
        _evidence(CapabilityEvidenceSource.TEST, mysql_path, mysql_test),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/operator-comparison-matrix-contract-v1.md",
            "Scalar Function Boundary",
        ),
    )
    if name != "matches":
        return evidence
    return (
        *evidence,
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/sql-dialect-dispatch-design-v1.md",
            "Error Classification",
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
        ),
    )


_SCALAR_SIGNATURES = (
    ("Text", "lower", ("Text", "unknown")),
    ("Text", "trim", ("Text", "unknown")),
    ("Text", "len", ("Int", "unknown")),
    ("Text", "matches", ("Text", "Bool", "unknown")),
)

_SCALAR_FUNCTION_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    _fact(
        CapabilityDomain.SCALAR_FUNCTION,
        subject,
        operation,
        operands,
        _scalar_function_evidence(operation),
    )
    for subject, operation, operands in _SCALAR_SIGNATURES
)


def _unary_evidence() -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "unaryExpression",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "UnaryExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_unary_value_type and _is_numeric",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType and EffectiveNullability",
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", "UnaryIR"),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node UnaryExpr branch",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            "_UNARY_OPERATORS and _render_expression_sql UnaryIR branch",
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            "_UNARY_OPERATORS and _render_mysql_expression UnaryIR branch",
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase26_numeric_scalar_expression_semantics.py",
            "test_unary_numeric_semantics_remain_unchanged",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_ir_expressions.py",
            "test_scalar_expression_forms_lower_with_semantic_types",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            "test_unary_ir_renders_supported_operators",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_mysql_expressions.py",
            "test_unary_ir_renders_approved_operators",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/operator-comparison-matrix-contract-v1.md",
            "Operator Result Matrix",
        ),
    )


_UNARY_SIGNATURES = (
    ("Int", "+", ("Int", "preserve_operand")),
    ("Float", "+", ("Float", "preserve_operand")),
    ("Int", "-", ("Int", "preserve_operand")),
    ("Float", "-", ("Float", "preserve_operand")),
)

_UNARY_OPERATOR_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    _fact(
        CapabilityDomain.UNARY_OPERATOR,
        subject,
        operation,
        operands,
        _unary_evidence(),
    )
    for subject, operation, operands in _UNARY_SIGNATURES
)


def _binary_evidence(kind: str) -> tuple[CapabilityEvidence, ...]:
    grammar_reference = (
        "orExpression and andExpression"
        if kind == "bool"
        else "multiplicativeExpression"
        if kind == "modulo"
        else "additiveExpression and multiplicativeExpression"
    )
    semantic_reference = {
        "int_float": "_binary_value_type, _binary_arithmetic_result_type, and _is_numeric",
        "decimal": "_binary_value_type and _binary_arithmetic_result_type Decimal/Decimal branch",
        "decimal_int": "_binary_value_type, _binary_arithmetic_result_type, and _is_decimal_int_pair",
        "modulo": "_binary_value_type modulo branch",
        "bool": "_binary_value_type Boolean branch",
    }[kind]
    semantic_test_path = {
        "int_float": "tests/test_phase26_numeric_scalar_expression_semantics.py",
        "decimal": "tests/test_phase26_decimal_scalar_expression_semantics.py",
        "decimal_int": "tests/test_phase42_decimal_int_exact_arithmetic.py",
        "modulo": "tests/test_phase17_core_scalar_expression_semantics.py",
        "bool": "tests/test_phase17_core_scalar_expression_semantics.py",
    }[kind]
    semantic_test = {
        "int_float": "test_int_float_binary_arithmetic_computed_projection_schema_is_locked",
        "decimal": "test_decimal_add_subtract_computed_projection_schema_is_locked",
        "decimal_int": "test_decimal_int_add_subtract_scalar_matrix_returns_logical_decimal",
        "modulo": "test_modulo_projection_requires_int_and_returns_int",
        "bool": "test_boolean_binary_where_resolves_to_known_bool",
    }[kind]
    evidence = (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            grammar_reference,
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "BinaryExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            semantic_reference,
            CapabilityReasonCode.UNKNOWN_NULLABILITY,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType and EffectiveNullability.UNKNOWN",
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", "BinaryIR"),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node BinaryExpr branch",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            "_BINARY_OPERATORS and _render_expression_sql BinaryIR branch",
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            "_BINARY_OPERATORS and _render_mysql_expression BinaryIR branch",
            dialect="mysql",
            backend="private-mysql",
        ),
    )
    roadmap = (
        (
            _evidence(
                CapabilityEvidenceSource.ROADMAP,
                "docs/plan/phase-42-aggregate-function-typeclasses-and-decimal-arithmetic-scope-lock.md",
                "Slice 1 Through Slice 7 Status Lock",
            ),
        )
        if kind == "decimal_int"
        else ()
    )
    tests = (
        _evidence(
            CapabilityEvidenceSource.TEST,
            semantic_test_path,
            semantic_test,
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_ir_expressions.py",
            "test_scalar_expression_forms_lower_with_semantic_types",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            "test_binary_ir_renders_supported_operators",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_mysql_expressions.py",
            "test_binary_ir_renders_approved_operators",
        ),
    )
    specs = (
        *(
            (
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/bool-predicate-semantics-contract-v1.md",
                    "Expression Facts",
                ),
            )
            if kind == "bool"
            else ()
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/operator-comparison-matrix-contract-v1.md",
            "Operator Result Matrix",
        ),
    )
    return (*evidence, *roadmap, *tests, *specs)


_BINARY_SIGNATURES = (
    ("Int", "+", "Int", "Int", "int_float"),
    ("Int", "+", "Float", "Float", "int_float"),
    ("Float", "+", "Int", "Float", "int_float"),
    ("Float", "+", "Float", "Float", "int_float"),
    ("Decimal", "+", "Decimal", "Decimal", "decimal"),
    ("Decimal", "+", "Int", "Decimal", "decimal_int"),
    ("Int", "+", "Decimal", "Decimal", "decimal_int"),
    ("Int", "-", "Int", "Int", "int_float"),
    ("Int", "-", "Float", "Float", "int_float"),
    ("Float", "-", "Int", "Float", "int_float"),
    ("Float", "-", "Float", "Float", "int_float"),
    ("Decimal", "-", "Decimal", "Decimal", "decimal"),
    ("Decimal", "-", "Int", "Decimal", "decimal_int"),
    ("Int", "-", "Decimal", "Decimal", "decimal_int"),
    ("Int", "*", "Int", "Int", "int_float"),
    ("Int", "*", "Float", "Float", "int_float"),
    ("Float", "*", "Int", "Float", "int_float"),
    ("Float", "*", "Float", "Float", "int_float"),
    ("Int", "%", "Int", "Int", "modulo"),
    ("Bool", "and", "Bool", "Bool", "bool"),
    ("Bool", "or", "Bool", "Bool", "bool"),
)

_BINARY_OPERATOR_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    _fact(
        CapabilityDomain.BINARY_OPERATOR,
        subject,
        operation,
        (right, result, "unknown"),
        _binary_evidence(kind),
    )
    for subject, operation, right, result, kind in _BINARY_SIGNATURES
)


def _comparison_evidence(kind: str) -> tuple[CapabilityEvidence, ...]:
    ast_name = "BetweenExpr" if kind == "between" else "ComparisonExpr"
    procedure_reference = (
        "_between_value_type" if kind == "between" else "_infer ComparisonExpr branch"
    )
    ir_name = "BetweenIR" if kind == "between" else "ComparisonIR"
    lowering_reference = f"_lower_expr_node {ast_name} branch"
    if kind == "between":
        postgres_reference = "_render_expression_sql BetweenIR branch"
        mysql_reference = "_render_mysql_expression BetweenIR branch"
        semantic_path = "tests/test_phase17_core_scalar_expression_semantics.py"
        semantic_test = "test_between_where_resolves_to_known_bool"
        ir_test = "test_scalar_expression_forms_lower_with_semantic_types"
        postgres_test = "test_between_ir_renders_inclusive_predicate"
        mysql_test = "test_between_ir_renders_inclusive_predicate"
    elif kind == "like":
        postgres_reference = (
            "_COMPARISON_OPERATORS omission and _supported_operator rejection"
        )
        mysql_reference = (
            "_COMPARISON_OPERATORS omission and _supported_operator rejection"
        )
        semantic_path = "tests/test_phase30_operator_comparison_matrix_contract.py"
        semantic_test = (
            "test_comparison_between_and_is_null_boundaries_are_generic_only"
        )
        ir_test = "test_comparison_lowers_recursively"
        postgres_test = (
            "test_unsupported_calls_kinds_and_operators_are_not_silently_rendered"
        )
        mysql_test = "test_unsupported_expressions_fail_closed"
    else:
        postgres_reference = (
            "_COMPARISON_OPERATORS and _render_expression_sql ComparisonIR branch"
        )
        mysql_reference = (
            "_COMPARISON_OPERATORS and _render_mysql_expression ComparisonIR branch"
        )
        semantic_path = "tests/test_semantic_expressions.py"
        semantic_test = "test_simple_comparison_maps_to_bool_and_types_operands"
        ir_test = "test_comparison_lowers_recursively"
        postgres_test = "test_comparison_ir_maps_supported_operators"
        mysql_test = "test_comparison_ir_maps_approved_operators"
    backend_reason = (
        CapabilityReasonCode.DIALECT_LOWERING_GAP if kind == "like" else None
    )
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "comparisonExpression"
            if kind == "between"
            else "comparisonExpression and comparisonOperator",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            ast_name,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            procedure_reference,
            CapabilityReasonCode.UNKNOWN_NULLABILITY,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType, ValueTypeKind, and EffectiveNullability.UNKNOWN",
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", ir_name),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            lowering_reference,
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            postgres_reference,
            backend_reason,
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            mysql_reference,
            backend_reason,
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(CapabilityEvidenceSource.TEST, semantic_path, semantic_test),
        _evidence(
            CapabilityEvidenceSource.TEST, "tests/test_ir_expressions.py", ir_test
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            postgres_test,
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_mysql_expressions.py",
            mysql_test,
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/operator-comparison-matrix-contract-v1.md",
            "Comparison And Predicate Matrix",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/bool-predicate-semantics-contract-v1.md",
            "Three UNKNOWN Concepts",
            CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        ),
    )


_COMPARISON_SIGNATURES = (
    ("Expression", "==", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", "!=", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", "<", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", "<=", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", ">", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", ">=", ("Expression", "Bool", "unknown"), "simple"),
    ("Expression", "like", ("Expression", "Bool", "unknown"), "like"),
    (
        "ValueTypeKind.KNOWN",
        "between",
        (
            "ValueTypeKind.KNOWN",
            "ValueTypeKind.KNOWN",
            "Bool",
            "unknown",
        ),
        "between",
    ),
)

_COMPARISON_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    _fact(
        CapabilityDomain.COMPARISON,
        subject,
        operation,
        operands,
        _comparison_evidence(kind),
    )
    for subject, operation, operands, kind in _COMPARISON_SIGNATURES
)


def _null_test_evidence() -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "comparisonExpression IS NOT? NULL",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "IsNullExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_infer IsNullExpr branch",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_literal_value_type None branch and _infer IsNullExpr branch",
            CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType and EffectiveNullability.NON_NULL",
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", "IsNullIR"),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node IsNullExpr branch",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            "_render_expression_sql IsNullIR branch",
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            "_render_mysql_expression IsNullIR branch",
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_expressions.py",
            "test_is_null_expression_maps_to_non_null_bool",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_ir_expressions.py",
            "test_is_null_forms_lower_with_negation",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            "test_is_null_ir_renders_both_forms",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_mysql_expressions.py",
            "test_is_null_ir_renders_both_forms",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/operator-comparison-matrix-contract-v1.md",
            "Comparison And Predicate Matrix",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/bool-predicate-semantics-contract-v1.md",
            "Three UNKNOWN Concepts",
            CapabilityReasonCode.SQL_THREE_VALUED_TRUTH,
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase52-logical-type-literal-parameter-nullability-inventory-v1.md",
            "Literal Inventory",
            CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
        ),
    )


_NULL_TEST_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    _fact(
        CapabilityDomain.NULL_TEST,
        "Expression",
        operation,
        ("Bool", "non_null"),
        _null_test_evidence(),
    )
    for operation in ("is null", "is not null")
)

_CAPABILITY_SIGNATURE_FACTS: tuple[CapabilityFact, ...] = _freeze_signatures(
    (
        *_SCALAR_FUNCTION_FACTS,
        *_UNARY_OPERATOR_FACTS,
        *_BINARY_OPERATOR_FACTS,
        *_COMPARISON_FACTS,
        *_NULL_TEST_FACTS,
    )
)

_UNARY_IDENTITIES = frozenset(
    (subject, operation) for subject, operation, _ in _UNARY_SIGNATURES
)
_BINARY_IDENTITIES = frozenset(
    (subject, operation, right)
    for subject, operation, right, _, _ in _BINARY_SIGNATURES
)
_COMPARISON_OPERATIONS = frozenset(("==", "!=", "<", "<=", ">", ">=", "like"))
_LOGICAL_TYPE_ATOMS = frozenset(("Int", "Float", "Decimal", "Text", "Bool"))
_RESULT_NULLABILITY_POSTURES = frozenset(("unknown", "non_null", "preserve_operand"))


def _schema_is_complete(key: CapabilityKey) -> bool:
    if (
        key.context != "expression"
        or key.dialect is not None
        or key.extension is not None
    ):
        return False
    if key.domain is CapabilityDomain.SCALAR_FUNCTION:
        return (
            key.subject in _LOGICAL_TYPE_ATOMS
            and key.operation is not None
            and len(key.operands) >= 2
            and all(operand in _LOGICAL_TYPE_ATOMS for operand in key.operands[:-1])
            and key.operands[-1] in _RESULT_NULLABILITY_POSTURES
        )
    if key.domain is CapabilityDomain.UNARY_OPERATOR:
        return (
            (key.subject, key.operation) in _UNARY_IDENTITIES
            and len(key.operands) == 2
            and key.operands[0] in _LOGICAL_TYPE_ATOMS
            and key.operands[-1] == "preserve_operand"
        )
    if key.domain is CapabilityDomain.BINARY_OPERATOR:
        return (
            len(key.operands) == 3
            and (key.subject, key.operation, key.operands[0]) in _BINARY_IDENTITIES
            and key.operands[1] in _LOGICAL_TYPE_ATOMS
            and key.operands[-1] == "unknown"
        )
    if key.domain is CapabilityDomain.COMPARISON:
        if key.subject == "Expression" and key.operation in _COMPARISON_OPERATIONS:
            return (
                len(key.operands) == 3
                and key.operands[0] == "Expression"
                and key.operands[1] in _LOGICAL_TYPE_ATOMS
                and key.operands[-1] == "unknown"
            )
        return (
            key.subject == "ValueTypeKind.KNOWN"
            and key.operation == "between"
            and len(key.operands) == 4
            and key.operands[:2] == ("ValueTypeKind.KNOWN", "ValueTypeKind.KNOWN")
            and key.operands[2] in _LOGICAL_TYPE_ATOMS
            and key.operands[-1] == "unknown"
        )
    if key.domain is CapabilityDomain.NULL_TEST:
        return (
            key.subject == "Expression"
            and key.operation in {"is null", "is not null"}
            and len(key.operands) == 2
            and key.operands[0] in _LOGICAL_TYPE_ATOMS
            and key.operands[-1] == "non_null"
        )
    return False


def _unknown_reason(key: CapabilityKey) -> CapabilityReasonCode | None:
    if (
        key.domain is CapabilityDomain.BINARY_OPERATOR
        and key.operation == "/"
        and key.context == "expression"
        and key.dialect is None
        and key.extension is None
        and key.subject in _LOGICAL_TYPE_ATOMS
        and len(key.operands) == 3
        and key.operands[0] in _LOGICAL_TYPE_ATOMS
        and key.operands[1] in _LOGICAL_TYPE_ATOMS
        and key.operands[-1] == "unknown"
    ):
        return CapabilityReasonCode.NO_CURRENT_RESULT_RULE
    if key == CapabilityKey(
        CapabilityDomain.SCALAR_FUNCTION,
        subject="Text",
        operation="matches",
        operands=("Text", "Bool", "unknown"),
        context="expression",
        dialect="mysql",
    ):
        return CapabilityReasonCode.DIALECT_LOWERING_GAP
    if (
        key.domain is CapabilityDomain.COMPARISON
        and key.subject == "Expression"
        and key.operation == "like"
        and key.operands == ("Expression", "Bool", "unknown")
        and key.context == "expression"
        and key.dialect in {"postgresql", "mysql"}
        and key.extension is None
    ):
        return CapabilityReasonCode.DIALECT_LOWERING_GAP
    return None


def signature_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]:
    """Return one signature family, exact completeness, and bounded uncertainty."""

    if type(key) is not CapabilityKey:
        raise ValueError("Capability signatures require an exact capability key")
    if key.domain is CapabilityDomain.SCALAR_FUNCTION:
        facts = _SCALAR_FUNCTION_FACTS
    elif key.domain is CapabilityDomain.UNARY_OPERATOR:
        facts = _UNARY_OPERATOR_FACTS
    elif key.domain is CapabilityDomain.BINARY_OPERATOR:
        facts = _BINARY_OPERATOR_FACTS
    elif key.domain is CapabilityDomain.COMPARISON:
        facts = _COMPARISON_FACTS
    elif key.domain is CapabilityDomain.NULL_TEST:
        facts = _NULL_TEST_FACTS
    else:
        facts = ()
    complete = _schema_is_complete(key)
    return facts, complete, None if complete else _unknown_reason(key)
