from __future__ import annotations

from pathlib import Path
import subprocess
import tomllib

import pytest

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read
from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto._project.row_expression_schema import (
    ProjectExpressionSchemaOriginKind,
    ProjectExpressionSchemaReason,
    ProjectExpressionSchemaStatus,
    adapt_project_row_expression_schema,
)
from pietto.ast_nodes import (
    BinaryExpr,
    CallExpr,
    DottedNameExpr,
    FieldDef,
    LiteralExpr,
    NameExpr,
    Nullability,
    Span,
    TypeExpr,
)
from pietto.semantic.model import (
    EffectiveNullability,
    ResolvedType,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from test_phase54_local_import_module_export_foundation_scope_lock import (
    phase54_slice5_gate2_manifest_is_active as _slice5_gate2,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-49-row-level-computed-let-schema-lineage.md"
SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md"
)
MODULE_PATH = REPO_ROOT / "src/pietto/_project/row_expression_schema.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"

ALLOWED_SLICE3_GATE2_PATHS = {
    "docs/plan/phase-49-row-level-computed-let-schema-lineage.md",
    "docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md",
    "src/pietto/_project/row_expression_schema.py",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py",
}

ALLOWED_SLICE3_REPAIR_GATE2_PATHS = {
    "tests/test_phase11_ci_workflow.py",
    "tests/test_phase11_completion_audit.py",
    "tests/test_phase11_generated_guard.py",
    "tests/test_phase11_golden_policy.py",
    "tests/test_phase11_packaging_smoke.py",
    "tests/test_phase11_validation_entrypoint.py",
    "tests/test_phase12_completion_audit.py",
    "tests/test_phase12_composition_cli_json_goldens.py",
    "tests/test_phase33_completion_audit.py",
    "tests/test_phase49_project_row_expression_type_nullability_adapter.py",
}


def test_direct_unqualified_field_projection_preserves_source_field() -> None:
    field_def = _field_def("id")
    schema = _project_schema(
        {
            "id": _project_field(
                "id",
                "Int",
                ProjectRowFieldNullability.NON_NULL,
                field_def=field_def,
            )
        }
    )

    result = adapt_project_row_expression_schema(
        expression=_name("id"),
        output_name="id",
        input_schema=schema,
        upstream_state=None,
        relation_qualifier="users",
        expression_value_types={},
        fallback_path="adapter.pietto",
    )

    assert result.status is ProjectExpressionSchemaStatus.CONCRETE
    assert result.reason is ProjectExpressionSchemaReason.DIRECT_FIELD
    assert result.origin is ProjectExpressionSchemaOriginKind.DIRECT_PROJECTION
    assert result.resolved_type == ProjectResolvedType(
        name="Int",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert result.nullability is ProjectRowFieldNullability.NON_NULL
    assert result.field_def is field_def


def test_qualified_direct_projection_uses_immediate_upstream_qualifier() -> None:
    field_def = _field_def("score")
    schema = _project_schema(
        {
            "score": _project_field(
                "score",
                "Float",
                ProjectRowFieldNullability.NULLABLE,
                field_def=field_def,
            )
        }
    )

    result = adapt_project_row_expression_schema(
        expression=_dotted("orders", "score"),
        output_name="score",
        input_schema=schema,
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.CONCRETE
    assert result.origin is ProjectExpressionSchemaOriginKind.DIRECT_PROJECTION
    assert result.resolved_type == ProjectResolvedType(
        name="Float",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert result.nullability is ProjectRowFieldNullability.NULLABLE
    assert result.field_def is field_def


def test_renamed_projection_preserves_source_field_with_rename_origin() -> None:
    field_def = _field_def("id")
    schema = _project_schema(
        {
            "id": _project_field(
                "id",
                "UUID",
                ProjectRowFieldNullability.NON_NULL,
                field_def=field_def,
            )
        }
    )

    result = adapt_project_row_expression_schema(
        expression=_name("id"),
        output_name="user_id",
        input_schema=schema,
        upstream_state=None,
        relation_qualifier=None,
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.CONCRETE
    assert result.reason is ProjectExpressionSchemaReason.RENAMED_PROJECTION
    assert result.origin is ProjectExpressionSchemaOriginKind.RENAMED_PROJECTION
    assert result.field_def is field_def
    assert result.resolved_type == ProjectResolvedType(
        name="UUID",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )


def test_computed_expression_consumes_supplied_known_value_type() -> None:
    expression = _binary_plus("amount", 1)

    result = adapt_project_row_expression_schema(
        expression=expression,
        output_name="total",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={
            expression: _value_type("Int", EffectiveNullability.UNKNOWN)
        },
    )

    assert result.status is ProjectExpressionSchemaStatus.CONCRETE
    assert result.reason is ProjectExpressionSchemaReason.KNOWN_EXPRESSION_VALUE
    assert result.origin is ProjectExpressionSchemaOriginKind.DERIVED_EXPRESSION
    assert result.resolved_type == ProjectResolvedType(
        name="Int",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert result.nullability is ProjectRowFieldNullability.UNKNOWN
    assert result.field_def is None


def test_bare_let_reference_consumes_supplied_private_value_type_only() -> None:
    expression = _name("gross")

    result = adapt_project_row_expression_schema(
        expression=expression,
        output_name="gross_value",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={},
        let_value_types={
            "gross": _value_type("Decimal", EffectiveNullability.UNKNOWN),
        },
    )

    assert result.status is ProjectExpressionSchemaStatus.CONCRETE
    assert result.reason is ProjectExpressionSchemaReason.KNOWN_LET_VALUE
    assert result.origin is ProjectExpressionSchemaOriginKind.LET_DERIVED
    assert result.resolved_type == ProjectResolvedType(
        name="Decimal",
        kind=ProjectResolvedTypeKind.BUILTIN,
    )
    assert result.field_def is None


def test_missing_expression_value_type_returns_non_concrete() -> None:
    result = adapt_project_row_expression_schema(
        expression=_binary_plus("amount", 1),
        output_name="total",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert result.reason is ProjectExpressionSchemaReason.MISSING_VALUE_TYPE
    assert result.resolved_type is None
    assert result.field_def is None


def test_unknown_expression_value_type_returns_non_concrete() -> None:
    expression = _binary_plus("amount", 1)
    result = adapt_project_row_expression_schema(
        expression=expression,
        output_name="total",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={
            expression: _value_type(
                "<unknown>",
                EffectiveNullability.UNKNOWN,
                type_kind=TypeKind.UNKNOWN,
                value_kind=ValueTypeKind.UNKNOWN,
            )
        },
    )

    assert result.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert result.reason is ProjectExpressionSchemaReason.UNKNOWN_VALUE_TYPE


def test_null_literal_without_concrete_supplied_fact_stays_non_concrete() -> None:
    result = adapt_project_row_expression_schema(
        expression=LiteralExpr(span=_span(), value=None),
        output_name="nothing",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier=None,
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert result.reason is ProjectExpressionSchemaReason.MISSING_VALUE_TYPE


def test_binary_division_without_concrete_supplied_fact_stays_non_concrete() -> None:
    result = adapt_project_row_expression_schema(
        expression=BinaryExpr(
            span=_span(),
            left=_name("amount"),
            operator="/",
            right=LiteralExpr(span=_span(column=10), value=2),
        ),
        output_name="ratio",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier="orders",
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.UNKNOWN
    assert result.reason is ProjectExpressionSchemaReason.MISSING_VALUE_TYPE


@pytest.mark.parametrize(
    ("state", "expected_status", "expected_reason"),
    [
        (
            ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.UNKNOWN,
                schema=ProjectRowSchema(is_unknown=True),
                reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
            ),
            ProjectExpressionSchemaStatus.UNKNOWN,
            ProjectExpressionSchemaReason.UPSTREAM_UNKNOWN,
        ),
        (
            ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.DEFERRED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
            ),
            ProjectExpressionSchemaStatus.DEFERRED,
            ProjectExpressionSchemaReason.UPSTREAM_DEFERRED,
        ),
        (
            ProjectRelationRowSchemaState(
                status=ProjectRelationRowSchemaStatus.BLOCKED,
                schema=None,
                reason=ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
            ),
            ProjectExpressionSchemaStatus.BLOCKED,
            ProjectExpressionSchemaReason.UPSTREAM_BLOCKED,
        ),
    ],
)
def test_upstream_non_concrete_states_short_circuit_deterministically(
    state: ProjectRelationRowSchemaState,
    expected_status: ProjectExpressionSchemaStatus,
    expected_reason: ProjectExpressionSchemaReason,
) -> None:
    result = adapt_project_row_expression_schema(
        expression=_name("id"),
        output_name="id",
        input_schema=_project_schema(
            {
                "id": _project_field(
                    "id",
                    "Int",
                    ProjectRowFieldNullability.NON_NULL,
                    field_def=_field_def("id"),
                )
            }
        ),
        upstream_state=state,
        relation_qualifier=None,
        expression_value_types={},
    )

    assert result.status is expected_status
    assert result.reason is expected_reason
    assert result.field_def is None


def test_aggregate_expression_stays_deferred() -> None:
    result = adapt_project_row_expression_schema(
        expression=CallExpr(
            span=_span(),
            callee=_name("count"),
            arguments=(),
        ),
        output_name="count",
        input_schema=_project_schema({}),
        upstream_state=None,
        relation_qualifier=None,
        expression_value_types={},
    )

    assert result.status is ProjectExpressionSchemaStatus.DEFERRED
    assert result.reason is (
        ProjectExpressionSchemaReason.AGGREGATE_OR_GROUPED_DEFERRED
    )
    assert result.origin is ProjectExpressionSchemaOriginKind.AGGREGATE


def test_slice3_module_does_not_call_forbidden_semantic_shortcuts() -> None:
    module = _read(MODULE_PATH)

    assert "semantic_api.analyze" not in module
    assert "infer_row_expression" not in module
    assert "from pietto.semantic import analyze" not in module
    assert "import pietto.semantic as semantic_api" not in module


def test_slice3_keeps_project_model_and_json_serializer_untouched() -> None:
    assert (
        _git_output(["diff", "--", "src/pietto/_project/model.py"]) == ""
    ) or _slice5_gate2()
    assert _git_output(["diff", "--", "src/pietto/_project/json_v2.py"]) == ""


def test_slice3_dirty_paths_are_exactly_gate2_allowlist() -> None:
    assert (
        _dirty_paths()
        in (
            set(),
            ALLOWED_SLICE3_GATE2_PATHS,
            ALLOWED_SLICE3_REPAIR_GATE2_PATHS,
        )
    ) or _slice5_gate2()


def test_slice3_package_version_remains_010() -> None:
    project = tomllib.loads(_read(PYPROJECT_PATH))["project"]
    assert project["version"] == "0.1.0"


def test_slice3_spec_and_plan_lock_boundaries() -> None:
    docs = " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))

    for required in (
        "Phase 49 Slice 3 is Type/nullability adapter for legal row expressions",
        "`src/pietto/_project/row_expression_schema.py`",
        "`docs/spec/phase49-project-row-expression-type-nullability-adapter-v1.md`",
        "does not call full `semantic_api.analyze`",
        "Slice 3 production code does not call `infer_row_expression`",
        "does not integrate computed alias schema output into project row schema construction",
        "Selected `let`-derived output schema remains Slice 7",
        "exposes no Project JSON v2 row schema",
        "changes no parser, grammar, generated files",
        "Aggregate and grouped output schema remain deferred to Phase 50",
        "Row-level dependency cycle diagnostics remain readiness-only",
        "Project JSON v2 privacy is preserved",
    ):
        assert required in docs, required


def _span(*, line: int = 1, column: int = 1) -> Span:
    return Span(
        path="adapter.pietto",
        line=line,
        column=column,
        end_line=line,
        end_column=column + 1,
    )


def _name(name: str) -> NameExpr:
    return NameExpr(span=_span(), name=name)


def _dotted(*parts: str) -> DottedNameExpr:
    return DottedNameExpr(span=_span(), parts=parts)


def _binary_plus(field_name: str, literal: int) -> BinaryExpr:
    return BinaryExpr(
        span=_span(),
        left=_name(field_name),
        operator="+",
        right=LiteralExpr(span=_span(column=10), value=literal),
    )


def _field_def(name: str) -> FieldDef:
    return FieldDef(
        span=_span(),
        name=name,
        type_expr=TypeExpr(
            span=_span(column=4),
            name="Int",
            arguments=(),
            nullability=Nullability.NOT_NULL,
        ),
        derive_expression=None,
        annotations=(),
        ensure_clauses=(),
    )


def _project_field(
    name: str,
    type_name: str,
    nullability: ProjectRowFieldNullability,
    *,
    field_def: FieldDef | None,
) -> ProjectRowField:
    return ProjectRowField(
        name=name,
        resolved_type=ProjectResolvedType(
            name=type_name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        ),
        nullability=nullability,
        field_def=field_def,
    )


def _project_schema(fields: dict[str, ProjectRowField]) -> ProjectRowSchema:
    return ProjectRowSchema(fields=fields)


def _value_type(
    type_name: str,
    nullability: EffectiveNullability,
    *,
    type_kind: TypeKind = TypeKind.BUILTIN,
    value_kind: ValueTypeKind = ValueTypeKind.KNOWN,
) -> ValueType:
    return ValueType(
        resolved_type=ResolvedType(name=type_name, kind=type_kind),
        nullability=nullability,
        kind=value_kind,
    )


def _git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    assert result.stderr == ""
    return result.stdout.strip()


def _dirty_paths() -> set[str]:
    output = _git_output(["status", "--porcelain", "--untracked-files=all"])
    paths: set[str] = set()
    for line in output.splitlines():
        if not line:
            continue
        path = line[3:] if line.startswith("?? ") else line[2:].strip()
        if " -> " in path:
            path = path.split(" -> ", maxsplit=1)[1]
        paths.add(path)
    return paths
