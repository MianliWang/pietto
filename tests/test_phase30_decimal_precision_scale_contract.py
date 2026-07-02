from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-30-core-type-system-stabilization-i.md"
SPEC_PATH = REPO_ROOT / "docs/spec/decimal-precision-scale-contract-v1.md"
CORE_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/core-type-system-stabilization-contract-v1.md"
)
REGISTRY_CONTRACT_PATH = REPO_ROOT / "docs/spec/canonical-scalar-type-registry-v1.md"
NULLABILITY_CONTRACT_PATH = (
    REPO_ROOT / "docs/spec/nullability-propagation-contract-v1.md"
)
BOOL_CONTRACT_PATH = REPO_ROOT / "docs/spec/bool-predicate-semantics-contract-v1.md"
DATE_CONTRACT_PATH = REPO_ROOT / "docs/spec/date-timestamp-formalization-contract-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/semantic/expressions.py"
AGGREGATES_PATH = REPO_ROOT / "src/pietto/semantic/aggregates.py"
ANALYZER_PATH = REPO_ROOT / "src/pietto/semantic/analyzer.py"
AST_NODES_PATH = REPO_ROOT / "src/pietto/ast_nodes.py"
AST_BUILDER_PATH = REPO_ROOT / "src/pietto/ast_builder.py"
GRAMMAR_PATH = REPO_ROOT / "grammar/Pietto.g4"
POSTGRES_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/expressions.py"
MYSQL_EXPRESSIONS_PATH = REPO_ROOT / "src/pietto/sql/mysql_expressions.py"

PHASE24_DECIMAL_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase24_decimal_aggregate_semantics.py"
)
PHASE24_DECIMAL_IR_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_ir.py"
PHASE24_DECIMAL_SQL_PATH = REPO_ROOT / "tests/test_phase24_decimal_aggregate_sql.py"
PHASE26_DECIMAL_SCALAR_TEST_PATH = (
    REPO_ROOT / "tests/test_phase26_decimal_scalar_expression_semantics.py"
)
PHASE26_ARGUMENT_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_semantics.py"
)
PHASE26_ARGUMENT_IR_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_ir.py"
)
PHASE26_ARGUMENT_SQL_PATH = (
    REPO_ROOT / "tests/test_phase26_aggregate_expression_argument_sql.py"
)
PHASE28_LITERAL_SEMANTICS_PATH = (
    REPO_ROOT / "tests/test_phase28_numeric_literal_aggregate_semantics.py"
)
PHASE28_COMPLETION_AUDIT_PATH = REPO_ROOT / "tests/test_phase28_completion_audit.py"

PHASE30_HARD_NON_GOALS = (
    "source implementation changes",
    "grammar, generated ANTLR, AST, or parser changes",
    "semantic implementation or semantic behavior changes",
    "type-system behavior changes",
    "diagnostic behavior changes",
    "predicate behavior changes",
    "IR implementation or IR model changes",
    "SQL backend or SQL lowering changes",
    "CLI behavior, command, option, help, exit-code, or output changes",
    "JSON v1 changes or JSON v2 implementation",
    "public API changes or public MySQL API expansion",
    "aggregate expansion or aggregate behavior changes",
    "fixture, golden, script, dependency, lockfile, package metadata, CI, or",
    "package version changes",
    "project or multi-file implementation",
    "schema introspection, database pull, SQL execution, connector execution, or",
    "runtime/database behavior",
    "relationship or JOIN implementation",
    "Decimal precision/scale syntax semantics",
    "Decimal precision/scale carrier",
    "Decimal precision/scale propagation",
    "Decimal precision/scale validation",
    "SQL precision guarantees",
    "native database type metadata",
    "Decimal literal syntax",
    "Decimal multiplication or division expansion",
    "mixed Decimal promotion expansion",
    "casts",
    "Money or Currency primitives",
    "exchange-rate, accounting, rounding, or minor-unit semantics",
    "semantic annotation syntax",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(path: Path) -> str:
    return " ".join(_read(path).split())


def test_slice6_artifacts_baseline_and_status_are_locked() -> None:
    assert SPEC_PATH.is_file()

    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)
    bool_contract = _normalized(BOOL_CONTRACT_PATH)
    date_contract = _normalized(DATE_CONTRACT_PATH)

    for required in (
        "Phase 30 Slice 6 is complete as Decimal precision / scale contract, "
        "static audit, and status work only",
        "HEAD: `fa7437e8141ed68daa988623cab25955237064cb`",
        "commit: `Document Date and Timestamp formalization`",
        "CI run: `27888353617 success`",
        "v0.2 is not complete yet",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan
        assert required in spec

    assert "decimal-precision-scale-contract-v1.md" in plan
    assert "decimal-precision-scale-contract-v1.md" in core_contract
    assert "Slice 6 Decimal Precision / Scale Contract" in registry_contract
    assert "Slice 6 Decimal Precision / Scale Contract" in nullability_contract
    assert "Slice 6 Decimal Precision / Scale Contract" in bool_contract
    assert "Slice 6 Decimal Precision / Scale Contract" in date_contract


def test_slice6_candidate_decision_is_docs_static_audit_status_only() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "| Candidate | Fit | Risk | Decision |",
        "Slice 6 docs/spec/static-audit/status only",
        "Chosen",
        "Tests-only hardening",
        "Rejected for Slice 6",
        "Minimal implementation artifact",
        "Rejected; no consumer needs a precision/scale carrier, registry "
        "object, helper, or SQL metadata type before the contract is accepted",
        "Broad behavior implementation",
        "Rejected; it could change grammar, semantic typing, diagnostics, IR, "
        "SQL, CLI/JSON, aggregate, fixture/golden, and public API behavior",
        "The selected Slice 6 direction is contract-first",
        "does not add Decimal precision/scale syntax semantics",
        "precision/scale carriers",
        "SQL precision guarantees",
        "Decimal literals",
        "Money/Currency primitives",
    ):
        assert required in spec

    for forbidden in (
        "Slice 6 implements Decimal precision",
        "Slice 6 changes Decimal behavior",
        "Slice 6 changes SQL lowering",
        "Slice 6 adds Decimal literals",
        "Slice 6 adds Money",
        "Slice 6 adds Currency",
    ):
        assert forbidden not in spec


def test_decimal_scalar_registry_and_model_facts_are_locked() -> None:
    spec = _normalized(SPEC_PATH)
    registry_contract = _normalized(REGISTRY_CONTRACT_PATH)
    catalog = _read(CATALOG_PATH)
    model = _read(MODEL_PATH)

    for required in (
        "`Decimal` is a current built-in scalar name",
        "`Decimal` is the current logical v0.2 exact numeric scalar",
        "not as a dialect-native physical type fact",
        "The Slice 2 canonical scalar registry contract records `Decimal` "
        "under the `numeric` and `exact numeric` traits",
    ):
        assert required in spec

    for required in (
        "BUILTIN_TYPE_NAMES = frozenset(",
        '"Decimal"',
    ):
        assert required in catalog

    for required in (
        "| numeric | `Int`, `Float`, `Decimal` |",
        "| exact numeric | `Int`, `Decimal` |",
        "These traits are contract vocabulary only in Slice 2",
        "do not authorize new operators, comparisons, aggregate forms, SQL "
        "lowering behavior",
    ):
        assert required in registry_contract

    for required in (
        "class ResolvedType:",
        "name: str",
        "kind: TypeKind",
        "definition: Node | None = None",
        "class ValueType:",
        "resolved_type: ResolvedType",
        "nullability: EffectiveNullability",
        "kind: ValueTypeKind = ValueTypeKind.KNOWN",
    ):
        assert required in model

    for forbidden in ("precision", "scale"):
        assert forbidden not in _class_body(model, "class ResolvedType:")
        assert forbidden not in _class_body(model, "class ValueType:")


def test_current_decimal_scalar_behavior_is_narrow_and_deferred() -> None:
    spec = _normalized(SPEC_PATH)
    expressions = _read(EXPRESSIONS_PATH)
    decimal_tests = _read(PHASE26_DECIMAL_SCALAR_TEST_PATH)

    for required in (
        "Decimal fields resolve as logical `Decimal`",
        "`Decimal + Decimal` returns logical `Decimal UNKNOWN`",
        "`Decimal - Decimal` returns logical `Decimal UNKNOWN`",
        "`EffectiveNullability.UNKNOWN`",
        "Decimal multiplication",
        "Decimal division",
        "mixed Decimal/Int promotion",
        "mixed Decimal/Float promotion",
        "Decimal literal syntax",
        "casts",
        "Slice 6 does not widen scalar arithmetic",
    ):
        assert required in spec

    for required in (
        'if expression.operator == "/":',
        "return _UNKNOWN_VALUE_TYPE",
        'if expression.operator in {"+", "-", "*"}:',
        "return_type = _binary_arithmetic_result_type(",
        'operator in {"+", "-"}',
        '_is_builtin(left_type, "Decimal")',
        '_is_builtin(right_type, "Decimal")',
        'return "Decimal"',
        "return None",
    ):
        assert required in expressions

    for required in (
        "test_decimal_add_subtract_computed_projection_schema_is_locked",
        "test_invalid_decimal_arithmetic_forms_reuse_s2105",
        "test_decimal_division_remains_deferred_without_diagnostic",
        "price + price",
        "price - price",
        "price * price",
        "price + score",
        "ValueTypeKind.UNKNOWN",
    ):
        assert required in decimal_tests


def test_current_decimal_aggregate_behavior_is_frozen_logical_decimal() -> None:
    spec = _normalized(SPEC_PATH)
    nullability_contract = _normalized(NULLABILITY_CONTRACT_PATH)
    aggregates = _read(AGGREGATES_PATH)
    phase24_semantics = _read(PHASE24_DECIMAL_SEMANTICS_PATH)
    phase24_ir = _read(PHASE24_DECIMAL_IR_PATH)
    phase24_sql = _read(PHASE24_DECIMAL_SQL_PATH)
    phase26_semantics = _read(PHASE26_ARGUMENT_SEMANTICS_PATH)
    phase26_ir = _read(PHASE26_ARGUMENT_IR_PATH)
    phase26_sql = _read(PHASE26_ARGUMENT_SQL_PATH)
    phase28_semantics = _read(PHASE28_LITERAL_SEMANTICS_PATH)

    for required in (
        "| `sum(Decimal)` | `Decimal NULLABLE` |",
        "| `avg(Decimal)` | `Decimal NULLABLE` |",
        "| `min(Decimal)` / `max(Decimal)` | `Decimal NULLABLE` |",
        "Accepted field-only Decimal expression arguments for `sum(...)` and "
        "`avg(...)` remain current behavior",
        "`sum(price + discount)`",
        "`avg(price - discount)`",
        "Current Decimal aggregate result facts are logical Pietto Decimal facts",
        "do not carry precision, scale, native database type metadata, rounding "
        "policy, or SQL precision guarantees",
        "does not widen aggregate names, aggregate argument shapes",
    ):
        assert required in spec

    for required in (
        "| `sum(Decimal)` | `Decimal NULLABLE` |",
        "| `avg(Decimal)` | `Decimal NULLABLE` |",
        "| `min(Decimal)` / `max(Decimal)` | `Decimal NULLABLE` |",
    ):
        assert required in nullability_contract

    for required in (
        "def is_supported_numeric_argument(value_type: ValueType) -> bool:",
        'for name in ("Int", "Float", "Decimal")',
        "DECIMAL_NULLABLE_VALUE_TYPE",
        'if _is_builtin(argument_type, "Decimal"):',
        "return DECIMAL_NULLABLE_VALUE_TYPE",
        "def is_supported_extrema_argument(value_type: ValueType) -> bool:",
        'for name in ("Int", "Float", "Decimal", "Date", "Timestamp")',
        "resolved_type=argument_type.resolved_type",
        "nullability=EffectiveNullability.NULLABLE",
    ):
        assert required in aggregates

    for required in (
        "sum(amount)",
        "avg(amount)",
        "min(amount)",
        "max(amount)",
        "Decimal",
        "EffectiveNullability.NULLABLE",
    ):
        assert required in phase24_semantics

    for required in (
        '("total_amount", "Decimal", NullabilityIR.NULLABLE)',
        '("average_amount", "Decimal", NullabilityIR.NULLABLE)',
        '("smallest_amount", "Decimal", NullabilityIR.NULLABLE)',
        '("largest_amount", "Decimal", NullabilityIR.NULLABLE)',
        'expression.value_type.canonical_name == "Decimal"',
    ):
        assert required in phase24_ir

    for required in (
        'SUM("amount")',
        'AVG("amount")',
        'MIN("amount")',
        'MAX("amount")',
        "SUM(`amount`)",
        "AVG(`amount`)",
        "MIN(`amount`)",
        "MAX(`amount`)",
        "field-only Int, Float, or Decimal expression argument",
    ):
        assert required in phase24_sql

    for required in ('result_type="Decimal"', 'argument_type="Decimal"'):
        assert required in phase26_ir

    for required in (
        "value = sum(price + price)",
        "price + discount",
        "price - discount",
    ):
        assert required in phase26_semantics

    for required in (
        "decimal_total = sum(price + price)",
        "decimal_average = avg(price - price)",
        "price + price",
        "price - price",
    ):
        assert required in phase26_sql

    for required in (
        "test_phase26_decimal_field_only_expression_arguments_remain_accepted",
        "total = sum(price + discount)",
        "average = avg(price - discount)",
        "test_decimal_literal_multiplication_and_mixed_promotion_remain_deferred",
        "value = sum(price * discount)",
        "value = sum(price + 1)",
        "value = sum(price + score)",
    ):
        assert required in phase28_semantics


def test_sql_renderers_keep_decimal_as_logical_shape_not_precision_contract() -> None:
    spec = _normalized(SPEC_PATH)
    postgres = _read(POSTGRES_EXPRESSIONS_PATH)
    mysql = _read(MYSQL_EXPRESSIONS_PATH)

    for required in (
        "PostgreSQL/MySQL portability in Slice 6 means only current SQL "
        "generation compatibility",
        "already accepted logical Decimal aggregate and expression shapes",
        "SQL `DECIMAL(p, s)` or `NUMERIC(p, s)` emission",
        "dialect precision/scale normalization",
        "precision widening or narrowing",
        "rounding behavior",
        "overflow behavior",
        "native database type metadata",
        "schema introspection",
        "runtime/database execution",
    ):
        assert required in spec

    for source in (postgres, mysql):
        for required in (
            "_SUPPORTED_NUMERIC_AGGREGATE_ARGUMENT_TYPES = "
            'frozenset({"Int", "Float", "Decimal"})',
            "expects a field-only ",
            "Float, or Decimal expression argument",
            'if argument_type == "Decimal":',
            'expected_result_type = "Decimal"',
            "approved logical shape",
        ):
            assert required in source

        for forbidden in ("DECIMAL(", "NUMERIC(", "precision", "scale"):
            assert forbidden not in source


def test_generic_type_arguments_have_phase41_decimal_validation_boundary() -> None:
    spec = _normalized(SPEC_PATH)
    grammar = _read(GRAMMAR_PATH)
    ast_nodes = _read(AST_NODES_PATH)
    ast_builder = _read(AST_BUILDER_PATH)
    analyzer = _read(ANALYZER_PATH)
    parser_tests = _read(REPO_ROOT / "tests/test_parser_types.py")

    for required in (
        "There are no stable v0.2 Decimal precision/scale semantics",
        "Generic type arguments may currently parse",
        "`Decimal(12, 2)` may parse as a generic `TypeExpr` with arguments",
        "current semantic resolution treats the type name as logical builtin `Decimal`",
        "Those parsed arguments are not a Decimal precision/scale contract",
        "Current semantic resolution ignores those arguments for builtin type "
        "resolution",
        "a precision/scale carrier",
        "a precision/scale validation rule",
        "a precision/scale propagation rule",
        "a row-schema fact",
        "an aggregate result fact",
        "an IR fact",
        "a SQL precision guarantee",
        "a JSON or CLI output field",
        "a public API field",
        "a native database metadata fact",
        "Future Decimal precision/scale work must be explicit",
        "must not rely on database implicit behavior",
        "must not rely on accidentally parsed but semantically ignored type arguments",
    ):
        assert required in spec

    for required in (
        "typeReference",
        ": identifier typeArguments?",
        "typeArguments",
        ": LPAREN (typeArgument (COMMA typeArgument)* COMMA?)? RPAREN",
    ):
        assert required in grammar

    for required in (
        "class TypeExpr(Node):",
        "arguments: tuple[TypeArgument, ...]",
        "class TypeArgument(Node):",
    ):
        assert required in ast_nodes

    for required in (
        "if ctx.typeArguments() is not None:",
        "ctx.typeArguments().typeArgument()",
        "arguments=arguments",
    ):
        assert required in ast_builder

    for required in (
        "def _resolve_type(",
        "if type_expr.name in BUILTIN_TYPE_NAMES:",
        "return ResolvedType(name=type_expr.name, kind=TypeKind.BUILTIN)",
        "def _decimal_precision_scale_diagnostic(",
        'if type_expr.name != "Decimal":',
        "arguments = type_expr.arguments",
        "_DECIMAL_PRECISION_MAX = 38",
        "PIE-S2004",
    ):
        assert required in analyzer

    assert "type_expr.arguments" not in _function_body(analyzer, "def _resolve_type(")
    decimal_validator = _function_body(
        analyzer,
        "def _decimal_precision_scale_diagnostic(",
    )
    assert "arguments = type_expr.arguments" in decimal_validator
    assert 'if type_expr.name != "Decimal":' in decimal_validator
    assert "if not arguments:" in decimal_validator

    for required in (
        "test_nullable_parameterized_type_definition_parses",
        "Text(max = 32, encoding = utf8)",
        "definition.base.arguments",
        "test_maximum_supported_integer_literal_length_parses",
    ):
        assert required in parser_tests


def test_money_currency_and_later_handoff_are_locked() -> None:
    plan = _normalized(PLAN_PATH)
    spec = _normalized(SPEC_PATH)
    core_contract = _normalized(CORE_CONTRACT_PATH)
    plan_and_specs = f"{plan} {spec} {core_contract}"

    for required in (
        "Money and Currency remain future semantic/domain annotation territory",
        "a `Money` primitive",
        "a `Currency` primitive",
        "exchange-rate semantics",
        "accounting semantics",
        "rounding policy",
        "minor-unit policy",
        "semantic annotation syntax",
        "Slice 7 Operator And Comparison Matrix owns the supported, rejected, "
        "and deferred Decimal operator and comparison matrix",
        "Phase 31 may harden numeric and Decimal boundaries",
        "Slice 7 is complete as operator and comparison matrix contract, "
        "static audit, and status work only",
        "Slice 8 is complete as completion audit and status lock work only",
        "Phase 30 is complete as docs/spec/static-audit/status work only",
        "v0.2 is not complete",
        "Phase 31 and Phase 32 remain required before v0.2 stable completion",
    ):
        assert required in plan_and_specs

    for required in PHASE30_HARD_NON_GOALS:
        assert required in plan_and_specs


def test_status_docs_record_slice6_without_behavior_change() -> None:
    for relative_path in ("README.md", "AGENTS.md", "docs/spec/pietto-v0.9.md"):
        status_doc = _normalized(REPO_ROOT / relative_path)
        for required in (
            "Phase 30 Core Type System Stabilization I",
            "Slice 6 is complete as Decimal precision / scale contract, static "
            "audit, and status work only",
            "`Decimal` remains logical v0.2 exact numeric",
            "generic `TypeExpr.arguments`, including currently parsed "
            "`Decimal(12, 2)`, do not create accepted precision/scale semantics",
            "no Decimal precision/scale carrier, propagation, validation, SQL "
            "precision guarantee, native DB metadata, JSON/API exposure, or "
            "public contract",
            "no Decimal literal syntax, Decimal multiplication/division "
            "expansion, mixed Decimal promotion expansion, casts, "
            "Money/Currency primitive, or semantic annotation syntax",
            "Slice 7 is complete as operator and comparison matrix contract, "
            "static audit, and status work only",
            "current comparison behavior is generic known-child typing",
            "not a final pair-specific semantic compatibility guarantee",
            "no Text concatenation",
            "no Date/Timestamp-specific comparison matrix",
            "no UUID comparison, cast, literal, storage, DDL, wider SQL, or "
            "public API behavior",
            "Bytes and Json remain deferred/unsupported behavior built-ins",
            "Slice 8 is complete as completion audit and status lock work only",
            "Phase 30 is complete",
            "Phase 31 v0.2 Hardening And Stable Completion is complete",
            "Pietto v0.2 single-file stable complete",
            "Phase 31 Slice 8 complete",
            "Phase 32 has started",
            "Phase 32 Slice 1 Candidate Decision, Roadmap Alignment, And v0.2 "
            "Handoff Audit is complete as docs/spec/static-audit/status-only work",
            "Phase 32 as a whole is not complete",
            "Phase 32: Semantic Explain And Metadata Output MVP",
        ):
            assert required in status_doc
        assert "Phase 32 remains post-v0.2 and has not started" not in status_doc

        for forbidden in (
            "v0.2 is complete",
            "Phase 30 implementation",
            "Phase 31 implementation is complete",
            "Decimal precision/scale is implemented",
            "Decimal precision/scale carrier is implemented",
            "Decimal literals are implemented",
            "Decimal multiplication is implemented",
            "Decimal division is implemented",
            "Money primitive is allowed",
            "Currency primitive is allowed",
            "Phase 30 changes SQL lowering",
            "Phase 30 expands aggregate",
            "Phase 30 changes JSON v1",
            "Phase 30 implements JSON v2",
        ):
            assert forbidden not in status_doc


def _class_body(source: str, marker: str) -> str:
    start = source.index(marker)
    rest = source[start:]
    end = rest.find("\n\n@dataclass", len(marker))
    if end == -1:
        end = rest.find("\n\n\ndef ", len(marker))
    return rest[:end]


def _function_body(source: str, marker: str) -> str:
    start = source.index(marker)
    rest = source[start:]
    next_def = rest.find("\n\ndef ", len(marker))
    return rest if next_def == -1 else rest[:next_def]
