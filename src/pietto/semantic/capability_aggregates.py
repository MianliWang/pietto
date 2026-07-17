"""Private aggregate signature and algebra capability facts."""

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
    """Build one exact ordered aggregate-evidence entry."""

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


def _advanced_aggregate_deferred() -> CapabilityDisposition:
    return CapabilityDisposition(
        CapabilityDispositionKind.DEFERRED,
        "POST60_ADVANCED_AGGREGATION_GROUPING",
        "separate syntax-semantic-IR-SQL-portability-diagnostic-validation "
        "decision required",
    )


def _freeze_aggregates(
    facts: Iterable[CapabilityFact],
) -> tuple[CapabilityFact, ...]:
    """Freeze facts while preserving distinct same-key entries in input order."""

    if isinstance(facts, (str, bytes)):
        raise ValueError("Aggregate capabilities require an iterable of facts")
    try:
        frozen = tuple(facts)
    except TypeError as exc:
        raise ValueError("Aggregate capabilities require an iterable of facts") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen):
        raise ValueError("Aggregate capabilities require exact capability facts")
    if len(set(frozen)) != len(frozen):
        raise ValueError("Aggregate capabilities forbid exact duplicate facts")
    return frozen


def _postgres_evidence(source_reference: str) -> CapabilityEvidence:
    return _evidence(
        CapabilityEvidenceSource.BACKEND,
        "src/pietto/sql/expressions.py",
        source_reference,
        dialect="postgresql",
        backend="postgresql",
    )


def _mysql_evidence(source_reference: str) -> CapabilityEvidence:
    return _evidence(
        CapabilityEvidenceSource.BACKEND,
        "src/pietto/sql/mysql_expressions.py",
        source_reference,
        dialect="mysql",
        backend="private-mysql",
    )


def _signature_test_and_spec_evidence(
    subject: str,
    argument_shape: str,
    argument_type: str,
) -> tuple[CapabilityEvidence, ...]:
    """Return family-specific historical tests and contracts in source order."""

    family: tuple[CapabilityEvidence, ...]
    if subject == "count" and argument_shape == "no_argument":
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase38_count_family_semantics_contract.py",
                "test_count_star_and_count_field_semantics_are_documented",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase38-count-family-semantics-contract-v1.md",
                "Current count() Contract",
            ),
        )
    elif subject == "count" and argument_shape == "direct_field":
        boundary: tuple[CapabilityEvidence, ...] = ()
        if argument_type in {"Date", "Timestamp"}:
            boundary = (
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase31_date_timestamp_sql_compatibility.py",
                    "Date and Timestamp direct-field aggregate compatibility",
                ),
            )
        elif argument_type == "UUID":
            boundary = (
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase31_uuid_enum_readiness_decision.py",
                    "UUID direct-field aggregate readiness",
                ),
            )
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase23_count_field_semantics.py",
                "count(field) accepted type and result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase31_aggregate_result_matrix_hardening.py",
                "count direct-field result matrix",
            ),
            *boundary,
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase38-boundary-types-capability-contract-v1.md",
                "Count Boundary",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
                "Aggregate And Grouped Inventory",
            ),
        )
    elif subject == "count":
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase39_count_expression_semantics.py",
                "field-bearing count expression semantic matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase37-count-expression-mvp-decision-v1.md",
                "Accepted Argument Expression Boundary",
            ),
        )
    elif subject == "count_distinct" and argument_shape == "direct_field":
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase24_count_distinct_semantics.py",
                "count_distinct direct-field semantic matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase31_aggregate_result_matrix_hardening.py",
                "count_distinct direct-field result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
                "Current Accepted Baseline",
            ),
        )
    elif subject == "count_distinct":
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase26_count_distinct_text_transform_semantics.py",
                "lower and trim Text transform-chain acceptance",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
                "Current Accepted Baseline",
            ),
        )
    elif subject in {"sum", "avg"} and argument_shape == "direct_field":
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase24_decimal_aggregate_semantics.py",
                "direct-field numeric aggregate result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase31_aggregate_result_matrix_hardening.py",
                "sum and avg direct-field result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase37-decimal-aggregate-expression-boundary-v1.md",
                "Current Decimal Aggregate Baseline",
            ),
        )
    elif (
        subject in {"sum", "avg"} and argument_shape == "field_only_numeric_expression"
    ):
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase26_aggregate_expression_argument_semantics.py",
                "field-only sum and avg expression acceptance",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase51-aggregate-expression-row-let-candidate-"
                "integration-v1.md",
                "Current Accepted Inline Aggregate Expression Matrix",
            ),
        )
    elif subject in {"sum", "avg"}:
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase28_numeric_literal_aggregate_semantics.py",
                "field-plus-literal sum and avg expression acceptance",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/numeric-literal-aggregate-arguments-v1.md",
                "Accepted Numeric Literal Aggregate Argument Boundary",
            ),
        )
    else:
        family = (
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase22_min_max_semantics.py",
                "direct-field min and max semantic result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.TEST,
                "tests/test_phase31_aggregate_result_matrix_hardening.py",
                "min and max direct-field result matrix",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase37-min-max-expression-boundary-v1.md",
                "Current Direct-field Extrema Baseline",
            ),
        )

    tests = tuple(
        item for item in family if item.source is CapabilityEvidenceSource.TEST
    )
    specs = tuple(
        item for item in family if item.source is CapabilityEvidenceSource.SPEC
    )
    return tests + (
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase51_private_result_role_output_identity.py",
            "aggregate_result role identity",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase52_expression_stage_clause_capability_facts.py",
            "aggregate-dependent GROUP-stage capability fact",
        ),
        *specs,
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase51-private-result-role-output-identity-v1.md",
            "Aggregate Result Role",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md",
            "GROUP Stage And Aggregate Result Role",
        ),
    )


def _signature_evidence(
    subject: str,
    argument_shape: str,
    argument_type: str,
) -> tuple[CapabilityEvidence, ...]:
    """Return exact compiler-order evidence for one supported signature."""

    if subject == "count":
        backend_reference = "_render_count_aggregate and _is_count_argument_expression"
        roadmap_path = "docs/plan/phase-23-count-field-aggregate-mvp.md"
    elif subject == "count_distinct":
        backend_reference = (
            "_render_count_distinct_aggregate and "
            "_is_count_distinct_text_transform_argument"
        )
        roadmap_path = "docs/plan/phase-24-aggregate-function-expansion-ii.md"
    elif subject in {"sum", "avg"}:
        backend_reference = (
            "_render_numeric_aggregate and _numeric_aggregate_argument_type"
        )
        roadmap_path = (
            "docs/plan/phase-26-aggregate-expression-arguments-numeric-foundation.md"
        )
    else:
        backend_reference = "_render_extrema_aggregate"
        roadmap_path = "docs/plan/phase-22-min-max-aggregate-mvp.md"

    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "primaryExpression and callSuffix",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "CallExpr NameExpr and DottedNameExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/aggregates.py",
            "SEMANTIC_AGGREGATE_NAMES and expected_semantic_aggregate_arities",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/aggregates.py",
            "is_supported_semantic_aggregate_argument_expression and "
            "semantic_aggregate_result_value_type",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "aggregate expression value typing",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/relation_schemas.py",
            "aggregate projection result schema",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/group_by.py",
            "grouped aggregate projection result schema",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/capability_contexts.py",
            "aggregate_dependent_expression GROUP stage",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType and EffectiveNullability",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/model.py",
            "AggregateCallIR",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node aggregate branch",
        ),
        _postgres_evidence(backend_reference),
        _mysql_evidence(backend_reference),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            "ProjectRowResultRole.AGGREGATE_RESULT",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/aggregate_grouped_schema.py",
            "canonical aggregate result construction",
        ),
        _evidence(
            CapabilityEvidenceSource.ROADMAP,
            roadmap_path,
            f"{subject} accepted aggregate surface",
        ),
        *_signature_test_and_spec_evidence(
            subject,
            argument_shape,
            argument_type,
        ),
    )


def _shape_supported_evidence() -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "primaryExpression and callSuffix",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "CallExpr NameExpr and DottedNameExpr",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/aggregates.py",
            "SEMANTIC_AGGREGATE_NAMES and expected_semantic_aggregate_arities",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/aggregates.py",
            "is_supported_count_argument and aggregate_result_value_type",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/capability_contexts.py",
            "aggregate_dependent_expression GROUP stage",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "TypeKind.SHAPE ValueType and EffectiveNullability",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            "ProjectRowResultRole.AGGREGATE_RESULT",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/aggregate_grouped_schema.py",
            "canonical aggregate result construction",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase38_boundary_types_capability_contract.py",
            "Shape count semantic capability evidence",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase51_private_result_role_output_identity.py",
            "aggregate_result role identity",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase52_expression_stage_clause_capability_facts.py",
            "aggregate-dependent GROUP-stage capability fact",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase38-boundary-types-capability-contract-v1.md",
            "Shape Count Conflict Boundary",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase51-private-result-role-output-identity-v1.md",
            "Aggregate Result Role",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase52-expression-stage-clause-capability-facts-v1.md",
            "GROUP Stage And Aggregate Result Role",
        ),
    )


def _shape_backend_gap_evidence() -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "primaryExpression and callSuffix",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/aggregates.py",
            "SEMANTIC_AGGREGATE_NAMES",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/aggregates.py",
            "is_supported_count_argument and aggregate_result_value_type",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/expressions.py",
            "_render_count_aggregate canonical TypeKindIR.BUILTIN rejection",
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_expressions.py",
            "_render_count_aggregate canonical TypeKindIR.BUILTIN rejection",
            CapabilityReasonCode.DIALECT_LOWERING_GAP,
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase31_aggregate_result_matrix_hardening.py",
            "non-builtin count backend fail-closed boundary",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase38-boundary-types-capability-contract-v1.md",
            "Shape Count Conflict Boundary",
        ),
    )


def _signature_fact(
    subject: str,
    operands: tuple[str, ...],
    *,
    support: CapabilitySupport = CapabilitySupport.SUPPORTED,
    evidence: tuple[CapabilityEvidence, ...] | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject=subject,
            operation="signature",
            operands=operands,
            context="aggregate_signature",
        ),
        support,
        _none(),
        (
            _signature_evidence(subject, operands[1], operands[2])
            if evidence is None
            else evidence
        ),
    )


def _signature_operands(
    argument_shape: str,
    argument_type: str,
    result_type: str,
    result_nullability: str,
    *,
    arity: str = "1",
) -> tuple[str, ...]:
    return (
        arity,
        argument_shape,
        argument_type,
        result_type,
        result_nullability,
        "GROUP",
        "aggregate_result",
    )


_AGGREGATE_SIGNATURE_FACTS: tuple[CapabilityFact, ...] = _freeze_aggregates(
    (
        _signature_fact(
            "count",
            _signature_operands(
                "no_argument",
                "NO_ARGUMENT",
                "Int",
                "non_null",
                arity="0",
            ),
        ),
        *(
            _signature_fact(
                "count",
                _signature_operands("direct_field", subject, "Int", "non_null"),
            )
            for subject in (
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
        ),
        *(
            _signature_fact(
                "count",
                _signature_operands(
                    "field_bearing_expression",
                    subject,
                    "Int",
                    "non_null",
                ),
            )
            for subject in ("Bool", "Int", "Float", "Decimal", "Text")
        ),
        _signature_fact(
            "count",
            _signature_operands("direct_field", "Shape", "Int", "non_null"),
            evidence=_shape_supported_evidence(),
        ),
        _signature_fact(
            "count",
            _signature_operands("direct_field", "Shape", "Int", "non_null"),
            support=CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            evidence=_shape_backend_gap_evidence(),
        ),
        *(
            _signature_fact(
                "count_distinct",
                _signature_operands("direct_field", subject, "Int", "non_null"),
            )
            for subject in (
                "Bool",
                "Int",
                "Float",
                "Decimal",
                "Text",
                "Date",
                "Timestamp",
                "UUID",
            )
        ),
        _signature_fact(
            "count_distinct",
            _signature_operands(
                "lower_trim_text_transform_chain",
                "Text",
                "Int",
                "non_null",
            ),
        ),
        *(
            _signature_fact(
                "sum",
                _signature_operands("direct_field", subject, result, "nullable"),
            )
            for subject, result in (
                ("Int", "Int"),
                ("Float", "Float"),
                ("Decimal", "Decimal"),
            )
        ),
        *(
            _signature_fact(
                "sum",
                _signature_operands(
                    "field_only_numeric_expression",
                    subject,
                    result,
                    "nullable",
                ),
            )
            for subject, result in (
                ("Int", "Int"),
                ("Float", "Float"),
                ("Decimal", "Decimal"),
            )
        ),
        *(
            _signature_fact(
                "sum",
                _signature_operands(
                    "field_and_literal_numeric_expression",
                    subject,
                    result,
                    "nullable",
                ),
            )
            for subject, result in (("Int", "Int"), ("Float", "Float"))
        ),
        *(
            _signature_fact(
                "avg",
                _signature_operands("direct_field", subject, result, "nullable"),
            )
            for subject, result in (
                ("Int", "Float"),
                ("Float", "Float"),
                ("Decimal", "Decimal"),
            )
        ),
        *(
            _signature_fact(
                "avg",
                _signature_operands(
                    "field_only_numeric_expression",
                    subject,
                    result,
                    "nullable",
                ),
            )
            for subject, result in (
                ("Int", "Float"),
                ("Float", "Float"),
                ("Decimal", "Decimal"),
            )
        ),
        *(
            _signature_fact(
                "avg",
                _signature_operands(
                    "field_and_literal_numeric_expression",
                    subject,
                    "Float",
                    "nullable",
                ),
            )
            for subject in ("Int", "Float")
        ),
        *(
            _signature_fact(
                "min",
                _signature_operands("direct_field", subject, subject, "nullable"),
            )
            for subject in ("Int", "Float", "Decimal", "Date", "Timestamp")
        ),
        *(
            _signature_fact(
                "max",
                _signature_operands("direct_field", subject, subject, "nullable"),
            )
            for subject in ("Int", "Float", "Decimal", "Date", "Timestamp")
        ),
    )
)


def _algebra_fact(
    subject: str,
    operation: str,
    operands: tuple[str, str],
    support: CapabilitySupport,
    evidence: tuple[CapabilityEvidence, ...],
    disposition: CapabilityDisposition | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            CapabilityDomain.AGGREGATE,
            subject=subject,
            operation=operation,
            operands=operands,
            context="aggregate_algebra",
        ),
        support,
        _none() if disposition is None else disposition,
        evidence,
    )


def _semantic_count_evidence() -> CapabilityEvidence:
    return _evidence(
        CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
        "src/pietto/semantic/aggregates.py",
        "COUNT_VALUE_TYPE and semantic_aggregate_result_value_type",
    )


def _modifier_evidence(
    operation: str,
    spec_reference: str,
) -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "primaryExpression callSuffix closed aggregate call surface",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "CallExpr has only callee arguments and span",
        ),
        _evidence(
            CapabilityEvidenceSource.ROADMAP,
            "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md",
            f"{operation} remains deferred",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase37_aggregate_filter_distinct_modifier_deferral.py",
            "test_sql_like_aggregate_modifier_syntax_remains_parser_rejected",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase37-aggregate-filter-distinct-modifier-deferral-v1.md",
            spec_reference,
        ),
    )


_AGGREGATE_ALGEBRA_FACTS: tuple[CapabilityFact, ...] = _freeze_aggregates(
    (
        _algebra_fact(
            "count",
            "empty_input_result",
            ("arity_0", "zero"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_aggregate COUNT(*) branch"),
                _mysql_evidence("_render_count_aggregate COUNT(*) branch"),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase38_count_family_semantics_contract.py",
                    "test_count_star_and_count_field_semantics_are_documented",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-count-family-semantics-contract-v1.md",
                    "COUNT(*) Empty Input Result",
                ),
            ),
        ),
        _algebra_fact(
            "count",
            "empty_input_result",
            ("arity_1", "zero"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_aggregate COUNT(expression) branch"),
                _mysql_evidence("_render_count_aggregate COUNT(expression) branch"),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-23-count-field-aggregate-mvp.md",
                    "count(field) returns zero when no values are counted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase38_count_family_semantics_contract.py",
                    "test_count_star_and_count_field_semantics_are_documented",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-count-family-semantics-contract-v1.md",
                    "COUNT(expression) Empty Input Result",
                ),
            ),
        ),
        _algebra_fact(
            "count_distinct",
            "empty_input_result",
            ("arity_1", "zero"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_distinct_aggregate"),
                _mysql_evidence("_render_count_distinct_aggregate"),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-24-aggregate-function-expansion-ii.md",
                    "count_distinct returns zero when no values are counted",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase24_aggregate_function_expansion_candidate_decision.py",
                    "test_count_distinct_result_and_type_allowlist_are_locked",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
                    "Current Count-distinct Result Contract",
                ),
            ),
        ),
        _algebra_fact(
            "sum",
            "empty_input_result",
            ("all_supported_signatures", "sql_null"),
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "aggregate_result_value_type sum nullable result",
                ),
                _postgres_evidence("_render_numeric_aggregate SUM"),
                _mysql_evidence("_render_numeric_aggregate SUM"),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase42_literal_only_aggregate_candidate_readiness.py",
                    "test_literal_only_aggregate_arguments_currently_fail_closed",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/aggregate-function-typeclasses-and-decimal-arithmetic-"
                    "scope-lock-v1.md",
                    "Current Aggregate Empty-input Boundary",
                ),
            ),
        ),
        _algebra_fact(
            "min",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "semantic_aggregate_result_value_type extrema nullable result",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase22_min_max_candidate_decision.py",
                    "min result is nullable same logical type",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase37-min-max-expression-boundary-v1.md",
                    "Current Direct-field Extrema Baseline",
                ),
            ),
        ),
        _algebra_fact(
            "max",
            "empty_input_result",
            ("all_supported_signatures", "nullable_on_empty_input"),
            CapabilitySupport.SUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "semantic_aggregate_result_value_type extrema nullable result",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase22_min_max_candidate_decision.py",
                    "max result is nullable same logical type",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase37-min-max-expression-boundary-v1.md",
                    "Current Direct-field Extrema Baseline",
                ),
            ),
        ),
        _algebra_fact(
            "count",
            "argument_inspection",
            ("arity_0", "does_not_inspect_values"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_aggregate COUNT(*) branch"),
                _mysql_evidence("_render_count_aggregate COUNT(*) branch"),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase38_count_family_semantics_contract.py",
                    "test_count_star_and_count_field_semantics_are_documented",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-count-family-semantics-contract-v1.md",
                    "COUNT(*) Argument Inspection",
                ),
            ),
        ),
        _algebra_fact(
            "count",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_aggregate COUNT(expression) branch"),
                _mysql_evidence("_render_count_aggregate COUNT(expression) branch"),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase38_count_family_semantics_contract.py",
                    "test_sql_null_and_json_null_distinction_is_documented",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-count-family-semantics-contract-v1.md",
                    "SQL NULL Treatment",
                ),
            ),
        ),
        _algebra_fact(
            "count_distinct",
            "null_treatment",
            ("arity_1", "eliminates_sql_null_results"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_distinct_aggregate"),
                _mysql_evidence("_render_count_distinct_aggregate"),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-24-aggregate-function-expansion-ii.md",
                    "count_distinct counts unique non-null values",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase24_aggregate_function_expansion_candidate_decision.py",
                    "test_count_distinct_accepted_shapes_contexts_and_sql_are_locked",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
                    "Current Count-distinct Null Treatment",
                ),
            ),
        ),
        _algebra_fact(
            "count_distinct",
            "duplicate_treatment",
            ("arity_1", "eliminates_duplicates"),
            CapabilitySupport.SUPPORTED,
            (
                _semantic_count_evidence(),
                _postgres_evidence("_render_count_distinct_aggregate COUNT DISTINCT"),
                _mysql_evidence("_render_count_distinct_aggregate COUNT DISTINCT"),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-24-aggregate-function-expansion-ii.md",
                    "count_distinct counts unique non-null values",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase24_aggregate_function_expansion_candidate_decision.py",
                    "test_count_distinct_accepted_shapes_contexts_and_sql_are_locked",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase37-count-distinct-expression-widening-boundary-v1.md",
                    "Current Count-distinct Duplicate Treatment",
                ),
            ),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_filter",
            ("all_current_aggregates", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _modifier_evidence("aggregate_filter", "Aggregate FILTER Deferral"),
            _advanced_aggregate_deferred(),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "inline_distinct_modifier",
            ("all_current_aggregates", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _modifier_evidence(
                "inline_distinct_modifier",
                "Inline DISTINCT Modifier Deferral",
            ),
            _advanced_aggregate_deferred(),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "aggregate_internal_ordering",
            ("all_current_aggregates", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _modifier_evidence(
                "aggregate_internal_ordering",
                "WITHIN GROUP And Aggregate-internal Ordering Deferral",
            ),
            _advanced_aggregate_deferred(),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "generic_aggregate_modifier",
            ("all_current_aggregates", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _modifier_evidence(
                "generic_aggregate_modifier",
                "Generic Aggregate Modifier Deferral",
            ),
            _advanced_aggregate_deferred(),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "nested_aggregate",
            ("aggregate_argument", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_CATALOG,
                    "src/pietto/semantic/aggregates.py",
                    "SEMANTIC_AGGREGATE_NAMES",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "nested_semantic_aggregate and PIE-S2311",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase37_nested_aggregate_composition_hardening.py",
                    "nested aggregate rejection matrix",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md",
                    "Nested Aggregate Boundary",
                ),
            ),
        ),
        _algebra_fact(
            "SEMANTIC_AGGREGATE_NAMES",
            "scalar_wrapping",
            ("direct_aggregate_projection", "not_supported"),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_CATALOG,
                    "src/pietto/semantic/aggregates.py",
                    "SEMANTIC_AGGREGATE_NAMES",
                ),
                _evidence(
                    CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                    "src/pietto/semantic/aggregates.py",
                    "contains_semantic_aggregate and PIE-S2310",
                ),
                _evidence(
                    CapabilityEvidenceSource.TEST,
                    "tests/test_phase37_nested_aggregate_composition_hardening.py",
                    "direct aggregate projection composition rejection matrix",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "docs/spec/phase38-binding-filter-post-aggregate-roadmap-v1.md",
                    "Direct Aggregate Projection Composition Boundary",
                ),
            ),
        ),
    )
)


_AGGREGATE_CAPABILITY_FACTS: tuple[CapabilityFact, ...] = (
    _AGGREGATE_SIGNATURE_FACTS + _AGGREGATE_ALGEBRA_FACTS
)

_ALGEBRA_PROPERTY_VALUES = frozenset(
    (
        "zero",
        "sql_null",
        "nullable_on_empty_input",
        "does_not_inspect_values",
        "eliminates_sql_null_results",
        "eliminates_duplicates",
        "not_supported",
    )
)


def _signature_schema_is_complete(key: CapabilityKey) -> bool:
    if (
        key.operation != "signature"
        or key.context != "aggregate_signature"
        or key.dialect is not None
        or key.extension is not None
        or len(key.operands) != 7
    ):
        return False
    arity, argument_shape, argument_type, result_type, nullability, stage, role = (
        key.operands
    )
    if (
        result_type not in {"Int", "Float", "Decimal", "Date", "Timestamp"}
        or nullability not in {"non_null", "nullable"}
        or stage != "GROUP"
        or role != "aggregate_result"
    ):
        return False
    return any(
        fact.key.subject == key.subject
        and fact.key.operands[:3] == (arity, argument_shape, argument_type)
        for fact in _AGGREGATE_SIGNATURE_FACTS
    )


def _algebra_schema_is_complete(key: CapabilityKey) -> bool:
    return (
        key.context == "aggregate_algebra"
        and key.dialect is None
        and key.extension is None
        and len(key.operands) == 2
        and key.operands[1] in _ALGEBRA_PROPERTY_VALUES
        and any(
            fact.key.subject == key.subject
            and fact.key.operation == key.operation
            and fact.key.operands[0] == key.operands[0]
            for fact in _AGGREGATE_ALGEBRA_FACTS
        )
    )


def aggregate_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]:
    """Return aggregate facts, exact completeness, and bounded uncertainty."""

    if type(key) is not CapabilityKey:
        raise ValueError("Aggregate capabilities require an exact capability key")
    if key.domain is not CapabilityDomain.AGGREGATE:
        return (), False, None
    if key.context == "aggregate_signature":
        facts = _AGGREGATE_SIGNATURE_FACTS
        complete = _signature_schema_is_complete(key)
    elif key.context == "aggregate_algebra":
        facts = _AGGREGATE_ALGEBRA_FACTS
        complete = _algebra_schema_is_complete(key)
    else:
        return (), False, CapabilityReasonCode.NOT_EVIDENCED
    return (
        facts,
        complete,
        None if complete else CapabilityReasonCode.NOT_EVIDENCED,
    )
