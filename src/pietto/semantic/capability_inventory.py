"""Private logical-type, literal, parameter, and nullability facts."""

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
    """Build one exact ordered evidence entry."""

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
        "POST60_ADVANCED_TYPE_NATIVE_MAPPING",
        reason,
    )


def _fact(
    key: CapabilityKey,
    support: CapabilitySupport,
    evidence: tuple[CapabilityEvidence, ...],
    disposition: CapabilityDisposition | None = None,
) -> CapabilityFact:
    return CapabilityFact(
        key,
        support,
        _none() if disposition is None else disposition,
        evidence,
    )


def _freeze_inventory(facts: Iterable[CapabilityFact]) -> tuple[CapabilityFact, ...]:
    """Freeze facts and reject completely identical duplicates."""

    if isinstance(facts, (str, bytes)):
        raise ValueError("Capability inventory requires an iterable of facts")
    try:
        frozen = tuple(facts)
    except TypeError as exc:
        raise ValueError("Capability inventory requires an iterable of facts") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen):
        raise ValueError("Capability inventory requires exact capability facts")
    if len(set(frozen)) != len(frozen):
        raise ValueError("Capability inventory forbids exact duplicate facts")
    return frozen


def _builtin_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    boundary_specs = {
        "Any": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Bytes": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Date": "docs/spec/date-timestamp-formalization-contract-v1.md",
        "Decimal": "docs/spec/decimal-precision-scale-contract-v1.md",
        "Json": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Timestamp": "docs/spec/date-timestamp-formalization-contract-v1.md",
        "UUID": "docs/spec/uuid-support-completion-v1.md",
    }
    specs = [
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/canonical-scalar-type-registry-v1.md",
            "Current Repo Facts",
        )
    ]
    if subject in boundary_specs:
        specs.append(
            _evidence(
                CapabilityEvidenceSource.SPEC,
                boundary_specs[subject],
                f"{subject} support boundary",
            )
        )
    return (
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/catalog.py",
            "BUILTIN_TYPE_NAMES",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            "_resolve_type",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ResolvedType and TypeKind.BUILTIN",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/model.py",
            "TypeRefIR and TypeKindIR.BUILTIN",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            "_resolve_project_type",
        ),
        _evidence(
            CapabilityEvidenceSource.PUBLIC,
            "src/pietto/_metadata/builder.py",
            "_type_metadata and _support_posture",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_types.py",
            "test_builtin_type_catalog_resolves_supported_names",
        ),
        *specs,
    )


def _declaration_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    details = {
        "type_alias": (
            "TypeAliasDef and TypeExpr",
            "_resolve_type and type_aliases.py",
            "TypeKind.ALIAS",
            "TypeKindIR.ALIAS and TypeAliasIR",
            "tests/test_semantic_type_aliases.py",
            "docs/spec/type-alias-domain-refinement-boundary-v1.md",
        ),
        "enum": (
            "EnumDef and TypeExpr",
            "_resolve_type",
            "TypeKind.ENUM",
            "TypeKindIR.ENUM and EnumIR",
            "tests/test_phase36_enum_support_resolution.py",
            "docs/spec/enum-support-resolution-v1.md",
        ),
        "shape": (
            "ShapeDef and TypeExpr",
            "_resolve_type",
            "TypeKind.SHAPE",
            "TypeKindIR.SHAPE and ShapeIR",
            "tests/test_semantic_types.py",
            "docs/spec/canonical-scalar-type-registry-v1.md",
        ),
    }
    ast_ref, procedure_ref, model_ref, ir_ref, test_path, spec_path = details[subject]
    return (
        _evidence(CapabilityEvidenceSource.GRAMMAR_AST, "grammar/Pietto.g4", ast_ref),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            ast_ref,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            procedure_ref,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            model_ref,
        ),
        _evidence(CapabilityEvidenceSource.IR, "src/pietto/ir/model.py", ir_ref),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            f"project {subject} kind",
        ),
        _evidence(
            CapabilityEvidenceSource.PUBLIC,
            "src/pietto/_metadata/builder.py",
            "_support_posture",
        ),
        _evidence(CapabilityEvidenceSource.TEST, test_path, f"{subject} facts"),
        _evidence(CapabilityEvidenceSource.SPEC, spec_path, f"{subject} boundary"),
    )


def _unsupported_logical_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    if subject == "<unknown>":
        return (
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                "src/pietto/semantic/expressions.py",
                "_UNKNOWN_VALUE_TYPE",
                CapabilityReasonCode.UNRESOLVED_EXPRESSION,
            ),
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                "src/pietto/semantic/analyzer.py",
                "_unknown_type_diagnostic",
                CapabilityReasonCode.UNRESOLVED_EXPRESSION,
            ),
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_MODEL,
                "src/pietto/semantic/model.py",
                "TypeKind.UNKNOWN and ValueTypeKind.UNKNOWN",
            ),
            _evidence(
                CapabilityEvidenceSource.IR,
                "src/pietto/ir/lowering.py",
                "_unknown_type",
            ),
            _evidence(
                CapabilityEvidenceSource.PROJECT,
                "src/pietto/_project/model.py",
                "ProjectResolvedTypeKind.UNKNOWN",
            ),
            _evidence(
                CapabilityEvidenceSource.PUBLIC,
                "src/pietto/_metadata/builder.py",
                "_type_is_unknown",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/phase52-private-capability-key-disposition-evidence-fact-foundation-v1.md",
                "Bounded Reason-code Contract",
            ),
        )
    if subject == "Null":
        return (
            _evidence(
                CapabilityEvidenceSource.GRAMMAR_AST,
                "grammar/Pietto.g4",
                "literal NULL",
            ),
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_CATALOG,
                "src/pietto/semantic/catalog.py",
                "BUILTIN_TYPE_NAMES closed-set absence",
            ),
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
                "src/pietto/semantic/expressions.py",
                "_literal_value_type",
                CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE,
            ),
            _evidence(
                CapabilityEvidenceSource.SEMANTIC_MODEL,
                "src/pietto/semantic/model.py",
                "ValueTypeKind.UNKNOWN",
            ),
            _evidence(
                CapabilityEvidenceSource.IR,
                "src/pietto/ir/model.py",
                "LiteralIR",
            ),
            _evidence(
                CapabilityEvidenceSource.SPEC,
                "docs/spec/nullability-propagation-contract-v1.md",
                "null literal boundary",
            ),
        )
    temporal = subject in {"DateTime", "Time", "Interval"}
    spec_path = (
        "docs/spec/datetime-time-interval-boundary-v1.md"
        if temporal
        else "docs/spec/type-alias-domain-refinement-boundary-v1.md"
    )
    test_path = (
        "tests/test_phase36_datetime_time_interval_boundary.py"
        if temporal
        else "tests/test_phase36_type_alias_domain_refinement_boundary.py"
    )
    return (
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            "src/pietto/semantic/catalog.py",
            "BUILTIN_TYPE_NAMES closed-set absence",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            "_resolve_type and _unknown_type_diagnostic",
            CapabilityReasonCode.NO_CATALOG_ENTRY,
        ),
        _evidence(
            CapabilityEvidenceSource.ROADMAP,
            "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
            "Type-System Inventory",
        ),
        _evidence(CapabilityEvidenceSource.TEST, test_path, f"{subject} boundary"),
        _evidence(CapabilityEvidenceSource.SPEC, spec_path, f"{subject} boundary"),
    )


def _decimal_precision_scale_evidence() -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "TypeExpr and TypeArgument",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            "_decimal_precision_scale_fact and _propagate_decimal_precision_scale_aliases",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "DecimalPrecisionScale",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase41_decimal_precision_scale_type_carrier.py",
            "Decimal precision-scale carrier",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase41_decimal_precision_scale_semantic_validation.py",
            "Decimal precision-scale validation",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/phase36-core-type-resolution-matrix-v1.md",
            "Decimal precision-scale boundary",
        ),
    )


_BUILTIN_SUBJECTS = (
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

_LOGICAL_TYPE_FACTS: tuple[CapabilityFact, ...] = _freeze_inventory(
    (
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LOGICAL_TYPE,
                    subject=subject,
                    operation="catalog_membership",
                    context="builtin_registry",
                ),
                CapabilitySupport.SUPPORTED,
                _builtin_evidence(subject),
            )
            for subject in _BUILTIN_SUBJECTS
        ),
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LOGICAL_TYPE,
                    subject=subject,
                    operation="declaration_kind",
                    context="semantic_model",
                ),
                CapabilitySupport.SUPPORTED,
                _declaration_evidence(subject),
            )
            for subject in ("type_alias", "enum", "shape")
        ),
        _fact(
            CapabilityKey(
                CapabilityDomain.LOGICAL_TYPE,
                subject="<unknown>",
                operation="catalog_membership",
                context="builtin_registry",
            ),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _unsupported_logical_evidence("<unknown>"),
        ),
        _fact(
            CapabilityKey(
                CapabilityDomain.LOGICAL_TYPE,
                subject="Null",
                operation="catalog_membership",
                context="builtin_registry",
            ),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            _unsupported_logical_evidence("Null"),
        ),
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LOGICAL_TYPE,
                    subject=subject,
                    operation="catalog_membership",
                    context="builtin_registry",
                ),
                CapabilitySupport.EXPLICITLY_UNSUPPORTED,
                _unsupported_logical_evidence(subject),
                _deferred("post-Phase-60 temporal type decision"),
            )
            for subject in ("DateTime", "Time", "Interval")
        ),
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LOGICAL_TYPE,
                    subject=subject,
                    operation="catalog_membership",
                    context="builtin_registry",
                ),
                CapabilitySupport.EXPLICITLY_UNSUPPORTED,
                _unsupported_logical_evidence(subject),
                _deferred("post-Phase-60 currency/domain decision"),
            )
            for subject in ("Money", "Currency")
        ),
        _fact(
            CapabilityKey(
                CapabilityDomain.LOGICAL_TYPE,
                subject="Decimal",
                operation="precision_scale",
                operands=("Int", "Int"),
                context="type_expression",
            ),
            CapabilitySupport.SUPPORTED,
            _decimal_precision_scale_evidence(),
        ),
    )
)


def _supported_literal_evidence(
    subject: str,
    reason: CapabilityReasonCode | None = None,
) -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "literal",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_builder.py",
            "visitLiteral and _decode_*",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_literal_value_type",
            reason,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/satisfying.py",
            "_literal_value_type",
            reason,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "ValueType",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/model.py",
            "LiteralIR",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_expr_node",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/render.py",
            "render_literal",
            dialect="postgresql",
            backend="postgresql",
        ),
        _evidence(
            CapabilityEvidenceSource.BACKEND,
            "src/pietto/sql/mysql_render.py",
            "render_literal",
            dialect="mysql",
            backend="private-mysql",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_expressions.py",
            f"{subject} literal semantic type",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_postgres_expressions.py",
            f"{subject} literal PostgreSQL rendering",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_sql_mysql_rendering.py",
            f"{subject} literal private MySQL rendering",
        ),
    )


def _unsupported_literal_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    spec_paths = {
        "Any": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Bytes": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Date": "docs/spec/datetime-time-interval-boundary-v1.md",
        "Decimal": "docs/spec/decimal-precision-scale-contract-v1.md",
        "Json": "docs/spec/any-bytes-json-support-posture-v1.md",
        "Timestamp": "docs/spec/datetime-time-interval-boundary-v1.md",
        "UUID": "docs/spec/uuid-support-completion-v1.md",
        "Enum": "docs/spec/enum-support-resolution-v1.md",
    }
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "closed literal rule",
            CapabilityReasonCode.NOT_EVIDENCED,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_literal_value_type closed mapping",
            CapabilityReasonCode.NOT_EVIDENCED,
        ),
        _evidence(
            CapabilityEvidenceSource.ROADMAP,
            "docs/spec/phase50-post-v02-deferred-readiness-inventory-v1.md",
            f"{subject} readiness boundary",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_expressions.py",
            f"no {subject} literal category",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            spec_paths[subject],
            f"{subject} literal boundary",
        ),
    )


_SUPPORTED_LITERALS = (
    ("integer", ("Int", "non_null")),
    ("float", ("Float", "non_null")),
    ("text", ("Text", "non_null")),
    ("boolean", ("Bool", "non_null")),
    ("null", ("no_concrete_type", "unknown")),
)

_UNSUPPORTED_LITERALS = (
    "Any",
    "Bytes",
    "Date",
    "Decimal",
    "Json",
    "Timestamp",
    "UUID",
    "Enum",
)

_SUPPORTED_LITERAL_SUBJECTS = frozenset(subject for subject, _ in _SUPPORTED_LITERALS)
_SUPPORTED_LITERAL_RESULTS = frozenset(
    ("Int", "Float", "Text", "Bool", "no_concrete_type")
)
_LITERAL_NULLABILITY_POSTURES = frozenset(("non_null", "unknown"))
_UNSUPPORTED_LITERAL_SUBJECTS = frozenset(_UNSUPPORTED_LITERALS)
_CALLABLE_PARAMETER_SUBJECTS = frozenset(("constraint", "derive"))
_NULLABILITY_SUBJECTS = frozenset(("implicit", "nullable", "not_null"))
_NULLABILITY_RESULTS = frozenset(("unknown", "nullable", "non_null"))

_LITERAL_FACTS: tuple[CapabilityFact, ...] = _freeze_inventory(
    (
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LITERAL,
                    subject=subject,
                    operation="result",
                    operands=operands,
                    context="expression",
                ),
                CapabilitySupport.SUPPORTED,
                _supported_literal_evidence(
                    subject,
                    CapabilityReasonCode.NULL_LITERAL_NO_CONCRETE_TYPE
                    if subject == "null"
                    else None,
                ),
            )
            for subject, operands in _SUPPORTED_LITERALS
        ),
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.LITERAL,
                    subject=subject,
                    operation="result",
                    context="expression",
                ),
                CapabilitySupport.EXPLICITLY_UNSUPPORTED,
                _unsupported_literal_evidence(subject),
                _deferred("temporal literal contract")
                if subject in {"Date", "Timestamp"}
                else None,
            )
            for subject in _UNSUPPORTED_LITERALS
        ),
    )
)


def _callable_parameter_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "parameterList and parameter",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "Parameter",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/expressions.py",
            "_callable_row_schema",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/callables.py",
            "callable validation",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            "callable type validation",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "type resolution and nullability maps",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/model.py",
            f"ParameterIR and {subject.title()}IR",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            f"{subject} lowering",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            "_iter_project_type_expressions",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            f"tests/test_parser_{subject}s.py",
            f"{subject} parameters",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_callables.py",
            f"{subject} callable semantics",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_ir_callables.py",
            f"{subject} callable lowering",
        ),
    )


_PARAMETER_FACTS: tuple[CapabilityFact, ...] = _freeze_inventory(
    (
        *(
            _fact(
                CapabilityKey(
                    CapabilityDomain.PARAMETER,
                    subject=subject,
                    operation="declare",
                    operands=("name", "TypeExpr"),
                    context="callable_declaration",
                ),
                CapabilitySupport.SUPPORTED,
                _callable_parameter_evidence(subject),
            )
            for subject in ("constraint", "derive")
        ),
        _fact(
            CapabilityKey(
                CapabilityDomain.PARAMETER,
                subject="runtime_sql_parameter",
                operation="substitute",
                context="runtime_execution",
            ),
            CapabilitySupport.EXPLICITLY_UNSUPPORTED,
            (
                _evidence(
                    CapabilityEvidenceSource.GRAMMAR_AST,
                    "grammar/Pietto.g4",
                    "closed primary/literal surface",
                    CapabilityReasonCode.NOT_EVIDENCED,
                ),
                _evidence(
                    CapabilityEvidenceSource.ROADMAP,
                    "docs/plan/phase-12-sql-feature-expansion-i.md",
                    "Hard Boundaries",
                ),
                _evidence(
                    CapabilityEvidenceSource.SPEC,
                    "AGENTS.md",
                    "Project and Non-goals",
                ),
            ),
            CapabilityDisposition(
                CapabilityDispositionKind.OUT_OF_SCOPE,
                "Pietto charter",
                "runtime substitution and prepared-statement execution are host/database responsibilities",
            ),
        ),
    )
)


def _nullability_evidence(
    subject: str,
    reason: CapabilityReasonCode | None = None,
) -> tuple[CapabilityEvidence, ...]:
    return (
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "grammar/Pietto.g4",
            "nullabilityModifier",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_nodes.py",
            "Nullability",
        ),
        _evidence(
            CapabilityEvidenceSource.GRAMMAR_AST,
            "src/pietto/ast_builder.py",
            "_nullability",
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            "src/pietto/semantic/analyzer.py",
            "_effective_nullability",
            reason,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_MODEL,
            "src/pietto/semantic/model.py",
            "EffectiveNullability",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/model.py",
            "NullabilityIR",
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "nullability lowering",
        ),
        _evidence(
            CapabilityEvidenceSource.PROJECT,
            "src/pietto/_project/model.py",
            "_project_row_field_nullability and row-expression adapters",
        ),
        _evidence(
            CapabilityEvidenceSource.PUBLIC,
            "src/pietto/_metadata/builder.py",
            "_type_metadata",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_semantic_types.py",
            f"{subject} semantic nullability mapping",
        ),
        _evidence(
            CapabilityEvidenceSource.TEST,
            "tests/test_phase30_nullability_propagation_contract.py",
            f"{subject} nullability contract",
        ),
        _evidence(
            CapabilityEvidenceSource.SPEC,
            "docs/spec/nullability-propagation-contract-v1.md",
            f"{subject} mapping",
        ),
    )


_NULLABILITY_FACTS: tuple[CapabilityFact, ...] = _freeze_inventory(
    _fact(
        CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject=subject,
            operation="effective_nullability",
            operands=(result,),
            context="type_expression",
        ),
        CapabilitySupport.SUPPORTED,
        _nullability_evidence(
            subject,
            CapabilityReasonCode.UNKNOWN_NULLABILITY if subject == "implicit" else None,
        ),
    )
    for subject, result in (
        ("implicit", "unknown"),
        ("nullable", "nullable"),
        ("not_null", "non_null"),
    )
)

_CAPABILITY_FACTS: tuple[CapabilityFact, ...] = _freeze_inventory(
    (*_LOGICAL_TYPE_FACTS, *_LITERAL_FACTS, *_PARAMETER_FACTS, *_NULLABILITY_FACTS)
)


def _schema_is_complete(key: CapabilityKey) -> bool:
    if key.dialect is not None or key.extension is not None:
        return False
    if key.domain is CapabilityDomain.LOGICAL_TYPE:
        if (
            key.subject is not None
            and key.operation == "catalog_membership"
            and key.context == "builtin_registry"
            and key.operands == ()
        ):
            return True
        if (
            key.subject is not None
            and key.operation == "declaration_kind"
            and key.context == "semantic_model"
            and key.operands == ()
        ):
            return True
        if key == CapabilityKey(
            CapabilityDomain.LOGICAL_TYPE,
            subject="Decimal",
            operation="precision_scale",
            operands=("Int", "Int"),
            context="type_expression",
        ):
            return True
        return (
            key.operation == "effective_nullability"
            and key.context == "type_expression"
            and key.subject in _NULLABILITY_SUBJECTS
            and len(key.operands) == 1
            and key.operands[0] in _NULLABILITY_RESULTS
        )
    if key.domain is CapabilityDomain.LITERAL:
        if key.operation != "result" or key.context != "expression":
            return False
        if key.subject in _SUPPORTED_LITERAL_SUBJECTS:
            return (
                len(key.operands) == 2
                and key.operands[0] in _SUPPORTED_LITERAL_RESULTS
                and key.operands[1] in _LITERAL_NULLABILITY_POSTURES
            )
        return key.subject in _UNSUPPORTED_LITERAL_SUBJECTS and key.operands == ()
    if key.domain is CapabilityDomain.PARAMETER:
        if (
            key.subject in _CALLABLE_PARAMETER_SUBJECTS
            and key.operation == "declare"
            and key.operands == ("name", "TypeExpr")
            and key.context == "callable_declaration"
        ):
            return True
        return key == CapabilityKey(
            CapabilityDomain.PARAMETER,
            subject="runtime_sql_parameter",
            operation="substitute",
            context="runtime_execution",
        )
    return False


def inventory_lookup_inputs(
    key: CapabilityKey,
) -> tuple[tuple[CapabilityFact, ...], bool]:
    """Return one domain's raw facts and exact-schema completeness."""

    if type(key) is not CapabilityKey:
        raise ValueError("Capability inventory requires an exact capability key")
    if key.domain is CapabilityDomain.LOGICAL_TYPE:
        facts = (*_LOGICAL_TYPE_FACTS, *_NULLABILITY_FACTS)
    elif key.domain is CapabilityDomain.LITERAL:
        facts = _LITERAL_FACTS
    elif key.domain is CapabilityDomain.PARAMETER:
        facts = _PARAMETER_FACTS
    else:
        return (), False
    return facts, _schema_is_complete(key)
