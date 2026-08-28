from __future__ import annotations

from dataclasses import fields, replace
from itertools import product
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto.semantic as semantic_package
import pietto.semantic.window_analysis as window_analysis
import pietto.semantic.window_navigation_analysis as window_navigation_analysis
import pietto.semantic.window_semantics as window_semantics
from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    CallExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    Span,
    WindowExpr,
    WindowSpec,
)
from pietto.semantic.aggregates import contains_semantic_aggregate
from pietto.semantic.window_semantics import (
    AuthoredWindowFrame,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    AuthoredWindowSpecification,
    ResolvedWindowSpecification,
    StructurallyInvalidFrame,
    ValidatedFrame,
    ValidatedFrameNotApplicable,
    ValidatedWindowSpecification,
    WindowComponentOrigin,
    WindowFrameApplicability,
    WindowFrameBound,
    WindowFrameBoundKind,
    WindowFrameEmptinessClassification,
    WindowFrameExclusion,
    WindowFrameStructuralFailureKind,
    WindowFrameUnit,
    WindowFunctionFramePolicy,
    WindowFunctionFramePolicyKind,
    WindowOccurrenceIdentity,
    WindowSpecificationValidationFailure,
    WindowValidationIssueKind,
    resolve_authored_window_specification,
    validate_resolved_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice3-frame-validation-function-policy-v1.md"
SPAN = Span(path="slice3.pietto", line=1, column=1, end_line=1, end_column=2)
FRAME_IDENTITY = WindowFunctionIdentity(
    namespace=("extension",),
    name="moving_value",
    role=WindowFunctionRole.WINDOW_FUNCTION,
)
FRAME_POLICY = WindowFunctionFramePolicy(
    identity=FRAME_IDENTITY,
    kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
)
BOUND_CATEGORY_ORDER = (
    WindowFrameBoundKind.UNBOUNDED_PRECEDING,
    WindowFrameBoundKind.OFFSET_PRECEDING,
    WindowFrameBoundKind.CURRENT_ROW,
    WindowFrameBoundKind.OFFSET_FOLLOWING,
    WindowFrameBoundKind.UNBOUNDED_FOLLOWING,
)


def _span(column: int = 1) -> Span:
    return replace(SPAN, column=column, end_column=column + 1)


def _literal(value: int = 1, *, column: int = 1) -> LiteralExpr:
    return LiteralExpr(span=_span(column), value=value)


def _name(name: str, *, column: int = 1) -> NameExpr:
    return NameExpr(
        span=replace(SPAN, column=column, end_column=column + len(name)),
        name=name,
    )


def _bound(kind: WindowFrameBoundKind, *, column: int = 1) -> WindowFrameBound:
    return WindowFrameBound(
        kind=kind,
        offset=(
            _literal(column, column=column)
            if kind
            in {
                WindowFrameBoundKind.OFFSET_PRECEDING,
                WindowFrameBoundKind.OFFSET_FOLLOWING,
            }
            else None
        ),
    )


def _resolved(
    start: WindowFrameBoundKind = WindowFrameBoundKind.CURRENT_ROW,
    end: WindowFrameBoundKind = WindowFrameBoundKind.CURRENT_ROW,
    *,
    unit: WindowFrameUnit = WindowFrameUnit.ROWS,
    exclusion: WindowFrameExclusion = WindowFrameExclusion.NO_OTHERS,
    partition_by: tuple[Expression, ...] = (),
    order_by: tuple[OrderItem, ...] = (),
    start_bound: WindowFrameBound | None = None,
    end_bound: WindowFrameBound | None = None,
) -> ResolvedWindowSpecification:
    authored = AuthoredWindowSpecification(
        span=SPAN,
        partition_by=partition_by,
        order_by=order_by,
        frame=AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.BETWEEN,
            unit=unit,
            start=start_bound or _bound(start, column=2),
            end=end_bound or _bound(end, column=3),
            exclusion=AuthoredWindowFrameExclusion(exclusion.value),
        ),
    )
    return resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )


def _omitted_resolved(
    applicability: WindowFrameApplicability,
) -> ResolvedWindowSpecification:
    authored = AuthoredWindowSpecification(
        span=SPAN,
        partition_by=(),
        order_by=(),
        frame=AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED),
    )
    return resolve_authored_window_specification(
        authored,
        frame_applicability=applicability,
    )


def _validate(
    resolved: ResolvedWindowSpecification,
    *,
    identity: WindowFunctionIdentity = FRAME_IDENTITY,
    policy: WindowFunctionFramePolicy | None = FRAME_POLICY,
    arguments: tuple[Expression, ...] = (),
) -> ValidatedWindowSpecification | WindowSpecificationValidationFailure:
    return validate_resolved_window_specification(
        resolved,
        function_identity=identity,
        function_policy=policy,
        argument_expressions=arguments,
    )


def _nested_window(column: int = 10) -> WindowExpr:
    identity = WindowFunctionIdentity(
        namespace=(),
        name="row_number",
        role=WindowFunctionRole.WINDOW_FUNCTION,
    )
    return WindowExpr(
        span=_span(column),
        call=CallExpr(
            span=_span(column),
            callee=_name("row_number", column=column),
            arguments=(),
        ),
        spec=WindowSpec(
            span=_span(column),
            partition_by=(_name("account_id", column=column + 1),),
            order_by=(),
        ),
        identity=identity,
    )


def _expected_structural_failures(
    start: WindowFrameBoundKind,
    end: WindowFrameBoundKind,
) -> tuple[WindowFrameStructuralFailureKind, ...]:
    failures: list[WindowFrameStructuralFailureKind] = []
    if start is WindowFrameBoundKind.UNBOUNDED_FOLLOWING:
        failures.append(WindowFrameStructuralFailureKind.START_UNBOUNDED_FOLLOWING)
    if end is WindowFrameBoundKind.UNBOUNDED_PRECEDING:
        failures.append(WindowFrameStructuralFailureKind.END_UNBOUNDED_PRECEDING)
    if BOUND_CATEGORY_ORDER.index(start) > BOUND_CATEGORY_ORDER.index(end):
        failures.append(WindowFrameStructuralFailureKind.REVERSED_BOUND_CATEGORIES)
    return tuple(failures)


def test_validated_stage_types_are_closed_private_frozen_and_exact() -> None:
    assert tuple(
        (item.name, item.value) for item in WindowFrameEmptinessClassification
    ) == (
        ("STRUCTURALLY_INVALID", "structurally_invalid"),
        ("GUARANTEED_NONEMPTY", "guaranteed_nonempty"),
        ("POSSIBLY_EMPTY", "possibly_empty"),
        ("ALWAYS_EMPTY", "always_empty"),
    )
    assert tuple(
        (item.name, item.value) for item in WindowFrameStructuralFailureKind
    ) == (
        ("START_UNBOUNDED_FOLLOWING", "start_unbounded_following"),
        ("END_UNBOUNDED_PRECEDING", "end_unbounded_preceding"),
        ("REVERSED_BOUND_CATEGORIES", "reversed_bound_categories"),
    )
    assert tuple((item.name, item.value) for item in WindowFunctionFramePolicyKind) == (
        ("FRAME_SENSITIVE", "frame_sensitive"),
        (
            "FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN",
            "frame_insensitive_explicit_forbidden",
        ),
    )
    assert tuple((item.name, item.value) for item in WindowValidationIssueKind) == (
        ("STRUCTURALLY_INVALID_FRAME", "structurally_invalid_frame"),
        ("MISSING_FUNCTION_FRAME_POLICY", "missing_function_frame_policy"),
        (
            "FUNCTION_FRAME_POLICY_IDENTITY_MISMATCH",
            "function_frame_policy_identity_mismatch",
        ),
        ("FRAME_APPLICABILITY_MISMATCH", "frame_applicability_mismatch"),
        ("EXPLICIT_FRAME_FORBIDDEN", "explicit_frame_forbidden"),
        ("NESTED_WINDOW_EXPRESSION", "nested_window_expression"),
    )
    assert tuple(field.name for field in fields(ValidatedFrame)) == (
        "resolved",
        "classification",
    )
    assert tuple(field.name for field in fields(ValidatedWindowSpecification)) == (
        "resolved",
        "function_identity",
        "function_policy",
        "argument_expressions",
        "frame",
    )
    symbols = (
        ValidatedFrame,
        ValidatedFrameNotApplicable,
        StructurallyInvalidFrame,
        ValidatedWindowSpecification,
        WindowSpecificationValidationFailure,
        WindowFunctionFramePolicy,
        validate_resolved_window_specification,
    )
    assert window_semantics.__all__ == ()
    for public in (pietto, semantic_package):
        assert all(not hasattr(public, symbol.__name__) for symbol in symbols)
    assert not hasattr(window_semantics, "TargetLowerableWindowSpecification")


@pytest.mark.parametrize(
    ("start", "end"), tuple(product(BOUND_CATEGORY_ORDER, repeat=2))
)
def test_all_bound_category_pairs_have_exact_structural_outcomes(
    start: WindowFrameBoundKind,
    end: WindowFrameBoundKind,
) -> None:
    result = _validate(_resolved(start, end))
    expected = _expected_structural_failures(start, end)
    if not expected:
        assert type(result) is ValidatedWindowSpecification
        assert type(result.frame) is ValidatedFrame
        return

    assert type(result) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in result.issues) == (
        WindowValidationIssueKind.STRUCTURALLY_INVALID_FRAME,
    )
    failure = result.issues[0].structural_failure
    assert type(failure) is StructurallyInvalidFrame
    assert failure.failures == expected
    assert (
        failure.classification
        is WindowFrameEmptinessClassification.STRUCTURALLY_INVALID
    )


def test_structurally_invalid_frames_cannot_construct_validated_frames() -> None:
    resolved = _resolved(
        WindowFrameBoundKind.UNBOUNDED_FOLLOWING,
        WindowFrameBoundKind.UNBOUNDED_PRECEDING,
    )
    with pytest.raises(ValueError, match="structurally invalid"):
        ValidatedFrame(
            resolved=resolved.frame,
            classification=WindowFrameEmptinessClassification.POSSIBLY_EMPTY,
        )
    valid = cast(ValidatedWindowSpecification, _validate(_resolved()))
    with pytest.raises(ValueError, match="forbid structural invalidity"):
        replace(
            cast(ValidatedFrame, valid.frame),
            classification=WindowFrameEmptinessClassification.STRUCTURALLY_INVALID,
        )


@pytest.mark.parametrize(
    ("unit", "start", "end", "exclusion", "expected"),
    (
        (
            WindowFrameUnit.ROWS,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameExclusion.NO_OTHERS,
            WindowFrameEmptinessClassification.GUARANTEED_NONEMPTY,
        ),
        (
            WindowFrameUnit.RANGE,
            WindowFrameBoundKind.UNBOUNDED_PRECEDING,
            WindowFrameBoundKind.UNBOUNDED_FOLLOWING,
            WindowFrameExclusion.TIES,
            WindowFrameEmptinessClassification.GUARANTEED_NONEMPTY,
        ),
        (
            WindowFrameUnit.ROWS,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameExclusion.CURRENT_ROW,
            WindowFrameEmptinessClassification.ALWAYS_EMPTY,
        ),
        (
            WindowFrameUnit.RANGE,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameExclusion.CURRENT_ROW,
            WindowFrameEmptinessClassification.POSSIBLY_EMPTY,
        ),
        (
            WindowFrameUnit.GROUPS,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameExclusion.GROUP,
            WindowFrameEmptinessClassification.ALWAYS_EMPTY,
        ),
        (
            WindowFrameUnit.ROWS,
            WindowFrameBoundKind.UNBOUNDED_PRECEDING,
            WindowFrameBoundKind.CURRENT_ROW,
            WindowFrameExclusion.GROUP,
            WindowFrameEmptinessClassification.POSSIBLY_EMPTY,
        ),
        (
            WindowFrameUnit.ROWS,
            WindowFrameBoundKind.OFFSET_PRECEDING,
            WindowFrameBoundKind.OFFSET_PRECEDING,
            WindowFrameExclusion.NO_OTHERS,
            WindowFrameEmptinessClassification.POSSIBLY_EMPTY,
        ),
        (
            WindowFrameUnit.GROUPS,
            WindowFrameBoundKind.OFFSET_FOLLOWING,
            WindowFrameBoundKind.OFFSET_FOLLOWING,
            WindowFrameExclusion.NO_OTHERS,
            WindowFrameEmptinessClassification.POSSIBLY_EMPTY,
        ),
    ),
)
def test_valid_emptiness_classification_is_strongest_conservative_evidence(
    unit: WindowFrameUnit,
    start: WindowFrameBoundKind,
    end: WindowFrameBoundKind,
    exclusion: WindowFrameExclusion,
    expected: WindowFrameEmptinessClassification,
) -> None:
    resolved = _resolved(start, end, unit=unit, exclusion=exclusion)
    first = _validate(resolved)
    second = _validate(resolved)
    assert type(first) is ValidatedWindowSpecification
    assert type(first.frame) is ValidatedFrame
    assert first.frame.classification is expected
    assert first == second
    assert hash(first) == hash(second)


def test_authorship_default_and_component_origin_survive_validation() -> None:
    omitted = _omitted_resolved(WindowFrameApplicability.APPLICABLE)
    explicit = _resolved(
        WindowFrameBoundKind.UNBOUNDED_PRECEDING,
        WindowFrameBoundKind.CURRENT_ROW,
        unit=WindowFrameUnit.RANGE,
    )
    omitted_validated = cast(ValidatedWindowSpecification, _validate(omitted))
    explicit_validated = cast(ValidatedWindowSpecification, _validate(explicit))
    assert type(omitted_validated.frame) is ValidatedFrame
    assert type(explicit_validated.frame) is ValidatedFrame
    assert omitted_validated.resolved is omitted
    assert omitted_validated.frame.resolved is omitted.frame
    assert omitted_validated.resolved.authored is omitted.authored
    assert omitted_validated.resolved.frame.authored is omitted.authored.frame
    assert omitted_validated.resolved.frame.origin is (
        WindowComponentOrigin.EFFECTIVE_DEFAULT
    )
    assert explicit_validated.resolved.frame.origin is (
        WindowComponentOrigin.LOCALLY_AUTHORED
    )
    assert omitted_validated.resolved.frame.authored != (
        explicit_validated.resolved.frame.authored
    )
    assert omitted_validated.frame.classification is (
        explicit_validated.frame.classification
    )


def test_builtin_policies_derive_from_exact_live_identity_metadata() -> None:
    identities = (
        *(identity for identity, _policy in window_analysis._RANKING_POLICIES),
        *(definition[0] for definition in window_analysis._DISTRIBUTION_FUNCTIONS),
        *(
            identity
            for identity, _direction in (
                window_navigation_analysis._NAVIGATION_IDENTITIES
            )
        ),
    )
    policies = tuple(
        window_analysis.builtin_window_function_frame_policy(identity)
        for identity in identities
    )
    assert tuple(identity.name for identity in identities) == (
        "row_number",
        "rank",
        "dense_rank",
        "percent_rank",
        "cume_dist",
        "ntile",
        "lag",
        "lead",
    )
    assert all(type(policy) is WindowFunctionFramePolicy for policy in policies)
    assert all(
        cast(WindowFunctionFramePolicy, policy).identity is identity
        for identity, policy in zip(identities, policies, strict=True)
    )
    assert all(
        cast(WindowFunctionFramePolicy, policy).kind
        is WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN
        for policy in policies
    )


def test_omitted_and_explicit_frames_remain_distinct_for_insensitive_policy() -> None:
    identity = window_analysis._RANKING_POLICIES[0][0]
    policy = window_analysis.builtin_window_function_frame_policy(identity)
    assert type(policy) is WindowFunctionFramePolicy
    omitted = _omitted_resolved(policy.required_frame_applicability)
    omitted_result = _validate(omitted, identity=identity, policy=policy)
    assert type(omitted_result) is ValidatedWindowSpecification
    assert type(omitted_result.frame) is ValidatedFrameNotApplicable

    explicit_authored = _resolved().authored
    explicit = resolve_authored_window_specification(
        explicit_authored,
        frame_applicability=policy.required_frame_applicability,
    )
    explicit_result = _validate(explicit, identity=identity, policy=policy)
    assert type(explicit_result) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in explicit_result.issues) == (
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )
    assert explicit_result.resolved.frame.authored is explicit_authored.frame


def test_inherited_explicit_frame_is_not_silently_ignored() -> None:
    identity = window_analysis._RANKING_POLICIES[0][0]
    policy = window_analysis.builtin_window_function_frame_policy(identity)
    assert type(policy) is WindowFunctionFramePolicy
    applicable = _resolved()
    inherited = replace(
        applicable,
        frame=replace(
            applicable.frame,
            origin=WindowComponentOrigin.INHERITED,
        ),
    )
    result = _validate(inherited, identity=identity, policy=policy)
    assert type(result) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in result.issues) == (
        WindowValidationIssueKind.FRAME_APPLICABILITY_MISMATCH,
        WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
    )


def test_missing_mismatched_and_wrong_applicability_policy_fail_closed() -> None:
    resolved = _resolved()
    missing = _validate(resolved, policy=None)
    assert type(missing) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in missing.issues) == (
        WindowValidationIssueKind.MISSING_FUNCTION_FRAME_POLICY,
    )

    other_identity = WindowFunctionIdentity(
        namespace=("extension",),
        name="other",
        role=WindowFunctionRole.WINDOW_FUNCTION,
    )
    mismatched = _validate(
        resolved,
        policy=WindowFunctionFramePolicy(
            identity=other_identity,
            kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
        ),
    )
    assert type(mismatched) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in mismatched.issues) == (
        WindowValidationIssueKind.FUNCTION_FRAME_POLICY_IDENTITY_MISMATCH,
    )

    wrong_applicability = _validate(
        _omitted_resolved(WindowFrameApplicability.NOT_APPLICABLE)
    )
    assert type(wrong_applicability) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in wrong_applicability.issues) == (
        WindowValidationIssueKind.FRAME_APPLICABILITY_MISMATCH,
    )


def test_extension_policy_uses_exact_identity_not_a_builtin_name_switch() -> None:
    extension_identity = WindowFunctionIdentity(
        namespace=("vendor",),
        name="row_number",
        role=WindowFunctionRole.WINDOW_FUNCTION,
    )
    assert (
        window_analysis.builtin_window_function_frame_policy(extension_identity) is None
    )
    extension_policy = WindowFunctionFramePolicy(
        identity=extension_identity,
        kind=WindowFunctionFramePolicyKind.FRAME_SENSITIVE,
    )
    result = _validate(
        _resolved(),
        identity=extension_identity,
        policy=extension_policy,
    )
    assert type(result) is ValidatedWindowSpecification
    assert result.function_identity is extension_identity
    assert result.function_policy is extension_policy


@pytest.mark.parametrize(
    "role",
    ("argument", "partition", "ordering", "frame_start", "frame_end"),
)
def test_nested_windows_fail_in_every_current_validation_input_role(role: str) -> None:
    nested = _nested_window()
    arguments: tuple[Expression, ...] = ()
    partition: tuple[Expression, ...] = ()
    ordering: tuple[OrderItem, ...] = ()
    start = _bound(WindowFrameBoundKind.CURRENT_ROW)
    end = _bound(WindowFrameBoundKind.CURRENT_ROW)
    if role == "argument":
        arguments = (
            CallExpr(
                span=SPAN,
                callee=_name("identity"),
                arguments=(nested,),
            ),
        )
    elif role == "partition":
        partition = (nested,)
    elif role == "ordering":
        ordering = (OrderItem(span=nested.span, expression=nested, direction=None),)
    elif role == "frame_start":
        start = WindowFrameBound(
            kind=WindowFrameBoundKind.OFFSET_PRECEDING,
            offset=nested,
        )
    else:
        end = WindowFrameBound(
            kind=WindowFrameBoundKind.OFFSET_FOLLOWING,
            offset=nested,
        )

    result = _validate(
        _resolved(
            partition_by=partition,
            order_by=ordering,
            start_bound=start,
            end_bound=end,
        ),
        arguments=arguments,
    )
    assert type(result) is WindowSpecificationValidationFailure
    assert tuple(issue.kind for issue in result.issues) == (
        WindowValidationIssueKind.NESTED_WINDOW_EXPRESSION,
    )
    assert result.issues[0].nested_expressions == (nested,)


def test_nested_window_evidence_preserves_source_order_and_multiplicity() -> None:
    first = _nested_window(10)
    second = _nested_window(20)
    result = _validate(
        _resolved(partition_by=(second, first)),
        arguments=(first, first),
    )
    assert type(result) is WindowSpecificationValidationFailure
    assert result.issues[0].nested_expressions == (first, first, second, first)


def test_legal_aggregate_before_window_input_is_not_blanket_rejected() -> None:
    aggregate = CallExpr(
        span=SPAN,
        callee=_name("sum"),
        arguments=(_name("amount", column=5),),
    )
    assert contains_semantic_aggregate(aggregate)
    result = _validate(_resolved(), arguments=(aggregate,))
    assert type(result) is ValidatedWindowSpecification


def test_validation_preserves_existing_identity_shapes_and_occurrence_distinction() -> (
    None
):
    assert tuple(field.name for field in fields(WindowFunctionIdentity)) == (
        "namespace",
        "name",
        "role",
    )
    assert tuple(field.name for field in fields(WindowOccurrenceIdentity)) == (
        "source_id",
        "relation_name",
        "selected_output_ordinal",
        "span",
    )
    first = cast(ValidatedWindowSpecification, _validate(_resolved()))
    second = cast(ValidatedWindowSpecification, _validate(_resolved()))
    assert type(first.frame) is ValidatedFrame
    assert type(second.frame) is ValidatedFrame
    assert first.resolved is not second.resolved
    assert first.resolved.authored is not second.resolved.authored
    assert first.frame.classification is second.frame.classification


def test_validation_rejects_untyped_inputs_without_partial_results() -> None:
    resolved = _resolved()
    with pytest.raises(TypeError):
        validate_resolved_window_specification(
            cast(Any, object()),
            function_identity=FRAME_IDENTITY,
            function_policy=FRAME_POLICY,
        )
    with pytest.raises(TypeError):
        validate_resolved_window_specification(
            resolved,
            function_identity=cast(Any, "moving_value"),
            function_policy=FRAME_POLICY,
        )
    with pytest.raises(TypeError):
        validate_resolved_window_specification(
            resolved,
            function_identity=FRAME_IDENTITY,
            function_policy=cast(Any, "frame_sensitive"),
        )
    with pytest.raises(TypeError):
        validate_resolved_window_specification(
            resolved,
            function_identity=FRAME_IDENTITY,
            function_policy=FRAME_POLICY,
            argument_expressions=cast(Any, []),
        )


def test_spec_freezes_scope_reader_closure_lifecycle_and_subject() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "Authored -> Resolved -> Validated",
        "STRUCTURALLY_INVALID",
        "GUARANTEED_NONEMPTY",
        "POSSIBLY_EMPTY",
        "ALWAYS_EMPTY",
        "WindowFunctionIdentity",
        "no source-name switch",
        "Existing aggregate-before-window behavior remains valid",
        "A2/M8/D0",
        "Slice 4 is neither implemented nor authorized",
        "Add Phase 60 frame validation and policy",
    ):
        assert evidence in document
