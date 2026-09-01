from __future__ import annotations

from dataclasses import fields, replace
from pathlib import Path

import pytest

from _pietto_repository_facts import REPOSITORY_FACTS
from pietto._project import check as project_check
from pietto._project.model import (
    ProjectRowFieldNullability,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_attribution import (
    ProjectModuleRelationOutputFieldAttribution,
    ProjectModuleSourceFieldOrigin,
)
import pietto._project.project_relationship_conditions as conditions
import pietto._project.project_relationships as relationships
from pietto.ast_nodes import (
    BinaryExpr,
    ComparisonExpr,
    DottedNameExpr,
    RelationshipMatchClause,
    Script,
)
from pietto.ir import build_ir
from pietto.ir.model import ScriptIR
from pietto.parser_api import parse_source
from pietto.semantic import analyze
from pietto.semantic.model import (
    RelationshipSemanticEndpointInfo,
    RelationshipSemanticInfo,
    SemanticModel,
)
from pietto.sql import emit_postgres_sql
from pietto.sql.mysql import emit_mysql_sql

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/phase62-slice3-exact-field-correspondences-on-where-equality-null-behavior-constraint-scope-boundary-v1.md"
)
SOURCE = REPO_ROOT / "src/pietto/_project/project_relationship_conditions.py"

SPEC_HEADINGS = (
    "Answer And Exact Owner",
    "Starting Authority",
    "Frozen Reader And Changed-path Closure",
    "Authored Base-match Syntax And AST",
    "Private Carriers And Identity Laws",
    "Exact Field Resolution Authority",
    "Accepted Shape And Exact Compatibility",
    "Unsupported Conditions And No Partial Extraction",
    "Standard Equality And NULL Laws",
    "Condition And Constraint Scope Boundaries",
    "Condition States Completeness And Ordering",
    "Compatibility And Later-owner Boundaries",
    "Focused Assurance",
    "Slice 4 Handoff",
    "Review And Repair Accounting",
    "Gate Lifecycle And Publication",
)


def _project_files() -> dict[str, str]:
    return {
        "a.pietto": (
            'import "b.pietto":\n    source customers as ImportedCustomers\n'
            "shape OrderRow:\n"
            "    id: Int not null\n"
            "    tenant_id: Int not null\n"
            "    customer_id: Int nullable\n"
            "    label: Text not null\n"
            "    payload: Json nullable\n"
            "    amount: Decimal(10, 2) not null\n"
            'source orders: OrderRow is postgres.table("orders")\n'
            "table order_view:\n"
            "    from orders\n"
            "    select:\n"
            "        id\n"
            "        tenant_id\n"
            "        customer_id\n"
            "        label\n"
            "        payload\n"
            "        amount\n"
            "table order_counts:\n"
            "    from orders\n"
            "    group by:\n"
            "        tenant_id\n"
            "    select:\n"
            "        tenant_id\n"
            "        total = count(id)\n"
            "shape EmployeeRow:\n"
            "    id: Int not null\n"
            'source employees: EmployeeRow is postgres.table("employees")\n'
            "shape UnknownRow:\n"
            "    mystery: MissingType nullable\n"
            'source unknowns: UnknownRow is postgres.table("unknowns")\n'
            "relationship legacy:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "relationship single:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.customer_id == customer.id\n"
            "relationship composite:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.tenant_id == customer.tenant_id and order.customer_id == customer.id\n"
            "relationship reversed_repeated:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on customer.id == order.customer_id and order.customer_id == customer.id\n"
            "relationship self_link:\n"
            "    endpoint employee: employees\n"
            "    endpoint manager: employees\n"
            "    on employee.id == manager.id\n"
            "relationship aggregate_output:\n"
            "    endpoint counts: order_counts\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on counts.total == customer.id\n"
            "relationship unknown_field:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.missing == customer.id\n"
            "relationship both_unknown_fields:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.missing == customer.missing\n"
            "relationship incompatible:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.label == customer.id\n"
            "relationship same_endpoint:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id == order.customer_id\n"
            "relationship unsupported_or:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id == customer.id or order.tenant_id == customer.tenant_id\n"
            "relationship residual:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id == customer.id and len(order.label) == customer.id\n"
            "relationship traversal_path:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.nested.id == customer.id\n"
            "relationship literal_equality:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id == 1\n"
            "relationship greater_than:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id > customer.id\n"
            "relationship unknown_role:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on missing.id == customer.id\n"
            "relationship unavailable_type:\n"
            "    endpoint unknown: unknowns\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on unknown.mystery == customer.id\n"
            "relationship deferred_builtin:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.payload == customer.payload\n"
            "relationship deferred_decimal:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.amount == customer.amount\n"
            "relationship final_valid:\n"
            "    endpoint order: order_view\n"
            "    endpoint customer: ImportedCustomers\n"
            "    on order.id == customer.id\n"
        ),
        "b.pietto": (
            "shape CustomerRow:\n"
            "    id: Int not null\n"
            "    tenant_id: Int not null\n"
            "    payload: Json nullable\n"
            "    amount: Decimal(12, 2) not null\n"
            'source customers: CustomerRow is postgres.table("customers")\n'
            "export:\n    source customers\n"
        ),
    }


def _semantic_project(root: Path) -> ProjectSemanticResult:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in _project_files().items():
        (root / relative).write_text(source, encoding="utf-8")
    parsed = project_check.check_project_parse_only(root)
    assert parsed.ok
    return build_empty_project_semantic_result(parsed)


def _condition_set(root: Path) -> conditions.ProjectRelationshipConditionSet:
    semantic = _semantic_project(root)
    relationship_set = relationships.build_project_relationships(semantic)
    return conditions.build_project_relationship_conditions(relationship_set)


def _named(
    result: conditions.ProjectRelationshipConditionSet,
    name: str,
) -> conditions.ProjectRelationshipCondition:
    matches = tuple(
        condition
        for condition in result.conditions
        if condition.relationship.occurrence.name == name
    )
    assert len(matches) == 1
    return matches[0]


def test_optional_relationship_base_match_reuses_exact_expression_ast() -> None:
    path = Path("relationships/matches.pietto")
    result = parse_source(
        "relationship legacy:\n"
        "    endpoint left: LeftRows\n"
        "    endpoint right: RightRows\n"
        "relationship matched:\n"
        "    endpoint left: LeftRows\n"
        "    endpoint right: RightRows\n"
        "    on left.tenant_id == right.tenant_id and left.id == right.left_id\n",
        path=path,
    )

    assert result.diagnostics == ()
    assert isinstance(result.ast, Script)
    legacy, matched = result.ast.relationships
    assert legacy.base_match is None
    assert isinstance(matched.base_match, RelationshipMatchClause)
    assert matched.base_match.span.path == str(path)
    assert (matched.base_match.span.line, matched.base_match.span.column) == (7, 5)
    assert (matched.base_match.span.end_line, matched.base_match.span.end_column) == (
        7,
        70,
    )
    expression = matched.base_match.expression
    assert isinstance(expression, BinaryExpr)
    assert expression.operator == "and"
    assert isinstance(expression.left, ComparisonExpr)
    assert isinstance(expression.right, ComparisonExpr)
    assert expression.left.operator == expression.right.operator == "=="
    assert isinstance(expression.left.left, DottedNameExpr)
    assert isinstance(expression.left.right, DottedNameExpr)
    assert expression.left.left.parts == ("left", "tenant_id")
    assert expression.left.right.parts == ("right", "tenant_id")


def test_concrete_correspondences_retain_order_roles_fields_types_and_scopes(
    tmp_path: Path,
) -> None:
    result = _condition_set(tmp_path)

    legacy = _named(result, "legacy")
    assert type(legacy) is conditions.ProjectNonConcreteRelationshipCondition
    assert legacy.state is conditions.ProjectRelationshipConditionState.ABSENT
    assert legacy.identity is None
    assert type(legacy.relationship) is relationships.ProjectConcreteRelationshipSubject

    single = _named(result, "single")
    assert type(single) is conditions.ProjectConcreteRelationshipCondition
    assert (
        single.scope
        is conditions.ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH
    )
    assert len(single.correspondences) == 1
    correspondence = single.correspondences[0]
    assert correspondence.identity.base_match is single.identity
    assert correspondence.identity.conjunct_position == 0
    assert correspondence.authored_left.authored_endpoint_role == "order"
    assert correspondence.authored_left.authored_field_spelling == "customer_id"
    assert correspondence.authored_right.authored_endpoint_role == "customer"
    assert correspondence.authored_right.authored_field_spelling == "id"
    assert correspondence.endpoint_zero is correspondence.authored_left
    assert correspondence.endpoint_one is correspondence.authored_right
    assert (
        correspondence.semantics
        is conditions.ProjectRelationshipEqualitySemantics.STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING
    )
    assert (
        correspondence.authored_left.semantic_field.nullability
        is ProjectRowFieldNullability.NULLABLE
    )
    assert type(correspondence.authored_left.authority) is (
        ProjectModuleRelationOutputFieldAttribution
    )
    assert type(correspondence.authored_right.authority) is (
        ProjectModuleSourceFieldOrigin
    )
    assert (
        correspondence.authored_left.constraint_scope.kind
        is conditions.ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
    )
    assert (
        correspondence.authored_right.constraint_scope.kind
        is conditions.ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT
    )
    assert correspondence.authored_left.constraint_scope.owner != (
        correspondence.authored_right.constraint_scope.owner
    )

    aggregate_output = _named(result, "aggregate_output")
    assert type(aggregate_output) is conditions.ProjectConcreteRelationshipCondition
    aggregate_field = aggregate_output.correspondences[0].authored_left
    assert aggregate_field.authored_field_spelling == "total"
    assert type(aggregate_field.authority) is (
        ProjectModuleRelationOutputFieldAttribution
    )
    assert aggregate_field.authority.semantic_field is aggregate_field.semantic_field

    composite = _named(result, "composite")
    assert type(composite) is conditions.ProjectConcreteRelationshipCondition
    assert tuple(
        correspondence.identity.conjunct_position
        for correspondence in composite.correspondences
    ) == (0, 1)
    assert tuple(
        (
            correspondence.authored_left.authored_field_spelling,
            correspondence.authored_right.authored_field_spelling,
        )
        for correspondence in composite.correspondences
    ) == (("tenant_id", "tenant_id"), ("customer_id", "id"))


def test_reversed_repeated_and_self_correspondences_never_collapse_identity(
    tmp_path: Path,
) -> None:
    result = _condition_set(tmp_path)
    reversed_repeated = _named(result, "reversed_repeated")
    assert type(reversed_repeated) is conditions.ProjectConcreteRelationshipCondition
    first, second = reversed_repeated.correspondences
    assert first.identity != second.identity
    assert first.authored_left.endpoint.identity.endpoint_position == 1
    assert first.endpoint_zero is first.authored_right
    assert first.endpoint_one is first.authored_left
    assert second.authored_left.endpoint.identity.endpoint_position == 0
    assert first.endpoint_zero.field_identity == second.endpoint_zero.field_identity
    assert first.endpoint_one.field_identity == second.endpoint_one.field_identity
    assert first.authored_left.identity != second.authored_right.identity

    self_link = _named(result, "self_link")
    assert type(self_link) is conditions.ProjectConcreteRelationshipCondition
    self_correspondence = self_link.correspondences[0]
    assert self_correspondence.authored_left.endpoint.target is (
        self_correspondence.authored_right.endpoint.target
    )
    assert self_correspondence.authored_left.field_identity == (
        self_correspondence.authored_right.field_identity
    )
    assert self_correspondence.authored_left.identity != (
        self_correspondence.authored_right.identity
    )


def test_non_concrete_conditions_fail_closed_without_partial_correspondences(
    tmp_path: Path,
) -> None:
    result = _condition_set(tmp_path)
    expected = {
        "unknown_field": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD,
        ),
        "both_unknown_fields": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD,
        ),
        "incompatible": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.INCOMPATIBLE_FIELD_TYPES,
        ),
        "same_endpoint": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.SAME_ENDPOINT_EQUALITY,
        ),
        "unsupported_or": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ),
        "residual": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ),
        "traversal_path": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ),
        "literal_equality": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ),
        "greater_than": (
            conditions.ProjectRelationshipConditionState.BLOCKED,
            conditions.ProjectRelationshipConditionIssueKind.UNSUPPORTED_CONDITION_SHAPE,
        ),
        "unknown_role": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNKNOWN_ENDPOINT_ROLE,
        ),
        "unavailable_type": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNAVAILABLE_FIELD_AUTHORITY,
        ),
        "deferred_builtin": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD_TYPE,
        ),
        "deferred_decimal": (
            conditions.ProjectRelationshipConditionState.UNKNOWN,
            conditions.ProjectRelationshipConditionIssueKind.UNKNOWN_FIELD_TYPE,
        ),
    }
    for name, (state, issue_kind) in expected.items():
        condition = _named(result, name)
        assert type(condition) is conditions.ProjectNonConcreteRelationshipCondition
        assert (
            type(condition.relationship)
            is relationships.ProjectConcreteRelationshipSubject
        )
        assert condition.state is state
        assert issue_kind in {issue.kind for issue in condition.issues}
        assert not hasattr(condition, "correspondences")

    unsupported_or = _named(result, "unsupported_or")
    residual = _named(result, "residual")
    assert type(unsupported_or) is conditions.ProjectNonConcreteRelationshipCondition
    assert type(residual) is conditions.ProjectNonConcreteRelationshipCondition
    assert len(unsupported_or.issues) == 1
    assert unsupported_or.issues[0].identity.conjunct_position == 0
    assert tuple(issue.identity.conjunct_position for issue in residual.issues) == (1,)

    both_unknown = _named(result, "both_unknown_fields")
    assert type(both_unknown) is conditions.ProjectNonConcreteRelationshipCondition
    assert len(both_unknown.issues) == 2
    assert tuple(
        issue.reference_identity.operand_position  # type: ignore[union-attr]
        for issue in both_unknown.issues
    ) == (0, 1)
    assert both_unknown.issues[0] != both_unknown.issues[1]

    final_valid = _named(result, "final_valid")
    assert type(final_valid) is conditions.ProjectConcreteRelationshipCondition
    assert len(final_valid.correspondences) == 1


def test_condition_and_constraint_scope_vocabularies_remain_separate(
    tmp_path: Path,
) -> None:
    result = _condition_set(tmp_path)
    single = _named(result, "single")
    assert type(single) is conditions.ProjectConcreteRelationshipCondition
    assert tuple(conditions.ProjectRelationshipConditionScope) == (
        conditions.ProjectRelationshipConditionScope.RELATIONSHIP_BASE_MATCH,
        conditions.ProjectRelationshipConditionScope.JOIN_LOCAL_ON_REFINEMENT,
        conditions.ProjectRelationshipConditionScope.POST_JOIN_FILTER,
    )
    assert tuple(conditions.ProjectRelationshipConstraintScopeKind) == (
        conditions.ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT,
        conditions.ProjectRelationshipConstraintScopeKind.UNDER_PREDICATE,
        conditions.ProjectRelationshipConstraintScopeKind.UNDER_POLICY,
        conditions.ProjectRelationshipConstraintScopeKind.UNDER_MATCH_CONTEXT,
    )
    assert type(single.scope) is conditions.ProjectRelationshipConditionScope
    assert type(single.correspondences[0].authored_left.constraint_scope.kind) is (
        conditions.ProjectRelationshipConstraintScopeKind
    )
    with pytest.raises(ValueError, match="only exact-row-output"):
        conditions.ProjectExactRowOutputConstraintScope(
            kind=conditions.ProjectRelationshipConstraintScopeKind.UNDER_PREDICATE,
            owner=single.correspondences[0].authored_left.constraint_scope.owner,
            relation=single.correspondences[0].authored_left.semantic_relation,
        )


def test_carriers_reject_detached_endpoint_and_field_authority(tmp_path: Path) -> None:
    result = _condition_set(tmp_path)
    single = _named(result, "single")
    assert type(single) is conditions.ProjectConcreteRelationshipCondition
    correspondence = single.correspondences[0]
    left = correspondence.authored_left

    detached_endpoint = replace(left.endpoint)
    detached_reference = replace(left, endpoint=detached_endpoint)
    detached_correspondence = replace(
        correspondence,
        authored_left=detached_reference,
        endpoint_zero=detached_reference,
    )
    with pytest.raises(ValueError, match="exact endpoint occurrences"):
        replace(single, correspondences=(detached_correspondence,))

    detached_authority = replace(left.authority)
    detached_reference = replace(left, authority=detached_authority)
    detached_correspondence = replace(
        correspondence,
        authored_left=detached_reference,
        endpoint_zero=detached_reference,
    )
    detached_condition = replace(single, correspondences=(detached_correspondence,))
    with pytest.raises(ValueError, match="attribution authority"):
        replace(
            result,
            conditions=tuple(
                detached_condition if condition is single else condition
                for condition in result.conditions
            ),
        )


def test_condition_construction_is_cwd_and_environment_independent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    semantic = _semantic_project(tmp_path / "project")
    relationship_set = relationships.build_project_relationships(semantic)
    first = conditions.build_project_relationship_conditions(relationship_set)
    unrelated = tmp_path / "unrelated"
    unrelated.mkdir()
    monkeypatch.chdir(unrelated)
    monkeypatch.setenv("PIETTO_UNRELATED_RELATIONSHIP_CONDITION", "ignored")
    second = conditions.build_project_relationship_conditions(relationship_set)

    def observation(
        result: conditions.ProjectRelationshipConditionSet,
    ) -> tuple[object, ...]:
        def correspondence_identities(
            condition: conditions.ProjectRelationshipCondition,
        ) -> tuple[conditions.ProjectRelationshipCorrespondenceIdentity, ...]:
            if type(condition) is conditions.ProjectConcreteRelationshipCondition:
                return tuple(
                    correspondence.identity
                    for correspondence in condition.correspondences
                )
            return ()

        return tuple(
            (
                condition.relationship.occurrence.identity,
                condition.state,
                correspondence_identities(condition),
            )
            for condition in result.conditions
        )

    assert observation(first) == observation(second)


def test_relationship_on_has_zero_public_semantic_ir_and_sql_delta() -> None:
    program = (
        "shape Row:\n"
        "    id: Int not null\n"
        'source left_rows: Row is postgres.table("left_rows")\n'
        'source right_rows: Row is postgres.table("right_rows")\n'
        "table selected:\n"
        "    from left_rows\n"
        "    select:\n"
        "        id\n"
    )
    endpoint_only = (
        "relationship link:\n"
        "    endpoint left: left_rows\n"
        "    endpoint right: right_rows\n"
    )
    with_match = endpoint_only + "    on left.id == right.id\n"
    baseline = parse_source(program + endpoint_only)
    matched = parse_source(program + with_match)
    assert baseline.diagnostics == matched.diagnostics == ()
    assert baseline.ast is not None and matched.ast is not None
    baseline_semantic = analyze(baseline.ast)
    matched_semantic = analyze(matched.ast)
    assert baseline_semantic.diagnostics == matched_semantic.diagnostics == ()
    assert baseline_semantic.model.relationships == matched_semantic.model.relationships
    baseline_ir = build_ir(baseline.ast, baseline_semantic.model)
    matched_ir = build_ir(matched.ast, matched_semantic.model)
    assert baseline_ir == matched_ir
    assert isinstance(baseline_ir.ir, ScriptIR)
    assert isinstance(matched_ir.ir, ScriptIR)
    assert emit_postgres_sql(baseline_ir.ir) == emit_postgres_sql(matched_ir.ir)
    assert emit_mysql_sql(baseline_ir.ir) == emit_mysql_sql(matched_ir.ir)


def test_private_condition_model_adds_no_later_or_public_authority() -> None:
    assert conditions.__all__ == ()
    assert tuple(field.name for field in fields(RelationshipSemanticInfo)) == (
        "name",
        "endpoints",
    )
    assert tuple(field.name for field in fields(RelationshipSemanticEndpointInfo)) == (
        "local_name",
        "relation_name",
        "relation",
    )
    assert tuple(field.name for field in fields(SemanticModel))[-1] == "relationships"
    assert tuple(field.name for field in fields(ScriptIR)) == ("definitions",)
    forbidden = {
        "key",
        "functional_dependency",
        "grain",
        "cardinality",
        "fanout",
        "join",
        "path",
    }
    assert not forbidden & {
        field.name
        for carrier in (
            conditions.ProjectRelationshipBaseMatchIdentity,
            conditions.ProjectRelationshipCorrespondenceIdentity,
            conditions.ProjectRelationshipEndpointFieldReferenceIdentity,
            conditions.ProjectRelationshipEndpointFieldReferenceOccurrence,
            conditions.ProjectRelationshipEqualityCorrespondence,
            conditions.ProjectConcreteRelationshipCondition,
            conditions.ProjectNonConcreteRelationshipCondition,
        )
        for field in fields(carrier)
    }


def test_source_reuses_exact_project_authority_without_global_scans() -> None:
    facts = REPOSITORY_FACTS.python(SOURCE)
    assert {
        "pietto._project.model",
        "pietto._project.module_attribution",
        "pietto._project.module_semantic_fact_preservation",
        "pietto._project.project_relationships",
    } <= facts.imported_modules
    assert not {"pietto.ir", "pietto.sql", "pathlib", "os"} & facts.imported_modules
    for forbidden in (
        "sorted",
        "sort",
        "glob",
        "rglob",
        "getcwd",
        "cwd",
        "sha256",
        "hash",
    ):
        assert forbidden not in facts.identifiers
    for required in (
        "find_owner",
        "find_row_lineage",
        "find_source_field_origin",
        "find_relation_output_field",
        "target_occurrence",
        "semantic_field",
    ):
        assert required in facts.identifiers


def test_contract_locks_syntax_identity_null_scopes_non_goals_and_handoff() -> None:
    document = SPEC.read_text(encoding="utf-8")
    assert (
        tuple(
            line.removeprefix("## ")
            for line in document.splitlines()
            if line.startswith("## ")
        )
        == SPEC_HEADINGS
    )
    normalized = " ".join(document.split())
    for evidence in (
        "18baeb56b3c27488a4fc4791ff274213386c43f9",
        "f96c34da8b4b7345babe0a8567433f88fec92971",
        "33466301585",
        "A3/M12/D0",
        "Pietto's existing standard-equality spelling is `==`",
        "relationship declaration occurrence != base-match condition occurrence != equality-correspondence occurrence != endpoint-field reference occurrence",
        "STANDARD_EQUALITY_TRUE_ONLY_NULL_REJECTING",
        "TRUE -> match FALSE -> no match UNKNOWN -> no match NULL on either operand prevents TRUE",
        "RELATIONSHIP_BASE_MATCH JOIN_LOCAL_ON_REFINEMENT POST_JOIN_FILTER",
        "UNCONDITIONAL_ON_EXACT_ROW_OUTPUT UNDER_PREDICATE UNDER_POLICY UNDER_MATCH_CONTEXT",
        "`ABSENT` carries no `ProjectRelationshipBaseMatchIdentity`",
        "`Any`/`Bytes`/`Decimal`/`Json` equality authority remain conservative `UNKNOWN`",
        "field correspondence != key evidence != cardinality evidence",
        "SLICE3_PROOF_MODEL_USES_CONVENIENT_RESULT_SHAPES_INSTEAD_OF_EXACT_OPTIONAL_OCCURRENCE_AND_FINAL_OUTPUT_AUTHORITY",
        "Phase 62 Slice 4 — UNIQUE Null Policy, Evidence Trust, Strict/Lax Row Uniqueness, And Candidate Keys",
        "Add Phase 62 relationship field correspondences",
        "PASS — PHASE62_SLICE3_EXACT_FIELD_CORRESPONDENCES_ON_WHERE_EQUALITY_NULL_BEHAVIOR_CONSTRAINT_SCOPE_BOUNDARY_END_TO_END",
    ):
        assert evidence in normalized
