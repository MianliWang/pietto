from __future__ import annotations

from dataclasses import FrozenInstanceError, fields, is_dataclass, replace
import inspect
from pathlib import Path
from typing import Any, cast

import pytest

import pietto
import pietto.semantic as semantic_package
import pietto.semantic.window_semantics as window_semantics
from pietto.ast_nodes import LiteralExpr, NameExpr, OrderItem, Span
from pietto.semantic.window_semantics import (
    AuthoredWindowFrame,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    AuthoredWindowSpecification,
    ResolvedWindowFrame,
    ResolvedWindowSpecification,
    WindowComponentOrigin,
    WindowFrameApplicability,
    WindowFrameBound,
    WindowFrameBoundKind,
    WindowFrameExclusion,
    WindowFrameUnit,
    WindowOccurrenceIdentity,
    resolve_authored_window_specification,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = REPO_ROOT / "docs/spec/phase60-slice2-authored-resolved-window-frame-model-v1.md"
SPAN = Span(path="slice2.pietto", line=1, column=1, end_line=1, end_column=2)


def _literal(value: int = 1, *, column: int = 1) -> LiteralExpr:
    return LiteralExpr(
        span=replace(SPAN, column=column, end_column=column + 1),
        value=value,
    )


def _name(name: str, *, column: int = 1) -> NameExpr:
    return NameExpr(
        span=replace(SPAN, column=column, end_column=column + len(name)),
        name=name,
    )


def _order(name: str = "observed_at") -> OrderItem:
    expression = _name(name)
    return OrderItem(span=expression.span, expression=expression, direction=None)


def _bound(
    kind: WindowFrameBoundKind,
    offset: LiteralExpr | None = None,
) -> WindowFrameBound:
    return WindowFrameBound(kind=kind, offset=offset)


def _omitted_spec(
    *,
    partition_by: tuple[NameExpr, ...] = (),
    order_by: tuple[OrderItem, ...] = (),
) -> AuthoredWindowSpecification:
    return AuthoredWindowSpecification(
        span=SPAN,
        partition_by=partition_by,
        order_by=order_by,
        frame=AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED),
    )


def _explicit_default_frame(
    exclusion: AuthoredWindowFrameExclusion,
) -> AuthoredWindowFrame:
    return AuthoredWindowFrame(
        kind=AuthoredWindowFrameKind.BETWEEN,
        unit=WindowFrameUnit.RANGE,
        start=_bound(WindowFrameBoundKind.UNBOUNDED_PRECEDING),
        end=_bound(WindowFrameBoundKind.CURRENT_ROW),
        exclusion=exclusion,
    )


def _effective_frame_key(
    frame: ResolvedWindowFrame,
) -> tuple[
    WindowFrameApplicability,
    WindowFrameUnit | None,
    WindowFrameBound | None,
    WindowFrameBound | None,
    WindowFrameExclusion | None,
]:
    return (
        frame.applicability,
        frame.unit,
        frame.start,
        frame.end,
        frame.exclusion,
    )


def test_closed_type_and_carrier_inventories_are_exact_private_and_immutable() -> None:
    assert tuple((item.name, item.value) for item in WindowFrameUnit) == (
        ("ROWS", "rows"),
        ("RANGE", "range"),
        ("GROUPS", "groups"),
    )
    assert tuple((item.name, item.value) for item in WindowFrameBoundKind) == (
        ("UNBOUNDED_PRECEDING", "unbounded_preceding"),
        ("OFFSET_PRECEDING", "offset_preceding"),
        ("CURRENT_ROW", "current_row"),
        ("OFFSET_FOLLOWING", "offset_following"),
        ("UNBOUNDED_FOLLOWING", "unbounded_following"),
    )
    assert tuple((item.name, item.value) for item in WindowFrameExclusion) == (
        ("NO_OTHERS", "no_others"),
        ("CURRENT_ROW", "current_row"),
        ("GROUP", "group"),
        ("TIES", "ties"),
    )
    assert tuple((item.name, item.value) for item in AuthoredWindowFrameExclusion) == (
        ("OMITTED", "omitted"),
        ("NO_OTHERS", "no_others"),
        ("CURRENT_ROW", "current_row"),
        ("GROUP", "group"),
        ("TIES", "ties"),
    )
    assert tuple((item.name, item.value) for item in AuthoredWindowFrameKind) == (
        ("OMITTED", "omitted"),
        ("SHORTHAND", "shorthand"),
        ("BETWEEN", "between"),
    )
    assert tuple((item.name, item.value) for item in WindowFrameApplicability) == (
        ("APPLICABLE", "applicable"),
        ("NOT_APPLICABLE", "not_applicable"),
    )
    assert tuple((item.name, item.value) for item in WindowComponentOrigin) == (
        ("LOCALLY_AUTHORED", "locally_authored"),
        ("INHERITED", "inherited"),
        ("EFFECTIVE_DEFAULT", "effective_default"),
        ("NOT_APPLICABLE", "not_applicable"),
    )

    expected = {
        WindowFrameBound: ("kind", "offset"),
        AuthoredWindowFrame: ("kind", "unit", "start", "end", "exclusion"),
        ResolvedWindowFrame: (
            "applicability",
            "origin",
            "authored",
            "unit",
            "start",
            "end",
            "exclusion",
        ),
        AuthoredWindowSpecification: ("span", "partition_by", "order_by", "frame"),
        ResolvedWindowSpecification: (
            "authored",
            "partition_by",
            "order_by",
            "partition_origin",
            "ordering_origin",
            "frame",
        ),
    }
    for carrier, names in expected.items():
        assert is_dataclass(carrier)
        assert hasattr(carrier, "__slots__")
        assert tuple(field.name for field in fields(carrier)) == names
        assert all(field.kw_only for field in fields(carrier))

    symbols = (*expected, resolve_authored_window_specification)
    assert window_semantics.__all__ == ()
    for public in (pietto, semantic_package):
        assert all(not hasattr(public, symbol.__name__) for symbol in symbols)
    assert not hasattr(window_semantics, "TargetLowerableWindowSpecification")


@pytest.mark.parametrize(
    "kind",
    (
        WindowFrameBoundKind.UNBOUNDED_PRECEDING,
        WindowFrameBoundKind.CURRENT_ROW,
        WindowFrameBoundKind.UNBOUNDED_FOLLOWING,
    ),
)
def test_non_offset_bounds_are_typed_hashable_and_forbid_offsets(
    kind: WindowFrameBoundKind,
) -> None:
    bound = _bound(kind)
    assert bound.kind is kind
    assert bound.offset is None
    assert isinstance(hash(bound), int)
    with pytest.raises(ValueError):
        WindowFrameBound(kind=kind, offset=_literal())


@pytest.mark.parametrize(
    "kind",
    (
        WindowFrameBoundKind.OFFSET_PRECEDING,
        WindowFrameBoundKind.OFFSET_FOLLOWING,
    ),
)
def test_offset_bounds_retain_the_exact_existing_expression_object(
    kind: WindowFrameBoundKind,
) -> None:
    expression = _literal(7)
    bound = _bound(kind, expression)
    assert bound.offset is expression
    assert isinstance(hash(bound), int)
    with pytest.raises(TypeError):
        WindowFrameBound(kind=kind)
    with pytest.raises(TypeError):
        WindowFrameBound(kind=kind, offset=cast(Any, object()))


def test_frame_bound_rejects_non_enum_kind() -> None:
    with pytest.raises(TypeError):
        WindowFrameBound(kind=cast(Any, "current_row"))


@pytest.mark.parametrize("unit", tuple(WindowFrameUnit))
@pytest.mark.parametrize("exclusion", tuple(AuthoredWindowFrameExclusion))
def test_shorthand_and_between_forms_exhaustively_represent_authorship(
    unit: WindowFrameUnit,
    exclusion: AuthoredWindowFrameExclusion,
) -> None:
    start = _bound(WindowFrameBoundKind.OFFSET_PRECEDING, _literal(2))
    end = _bound(WindowFrameBoundKind.OFFSET_FOLLOWING, _literal(3))
    shorthand = AuthoredWindowFrame(
        kind=AuthoredWindowFrameKind.SHORTHAND,
        unit=unit,
        start=start,
        exclusion=exclusion,
    )
    between = AuthoredWindowFrame(
        kind=AuthoredWindowFrameKind.BETWEEN,
        unit=unit,
        start=start,
        end=end,
        exclusion=exclusion,
    )
    assert shorthand.end is None
    assert between.end is end
    assert shorthand != between
    assert all(isinstance(hash(frame), int) for frame in (shorthand, between))


@pytest.mark.parametrize(
    "changes",
    (
        {"unit": WindowFrameUnit.ROWS},
        {"start": WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)},
        {"end": WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)},
        {"exclusion": AuthoredWindowFrameExclusion.NO_OTHERS},
    ),
)
def test_omitted_frame_forbids_every_explicit_component(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ValueError):
        AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED, **changes)  # pyright: ignore[reportArgumentType]


@pytest.mark.parametrize(
    "frame",
    (
        AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.SHORTHAND,
            unit=WindowFrameUnit.ROWS,
            start=_bound(WindowFrameBoundKind.CURRENT_ROW),
        ),
        AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.BETWEEN,
            unit=WindowFrameUnit.ROWS,
            start=_bound(WindowFrameBoundKind.CURRENT_ROW),
            end=_bound(WindowFrameBoundKind.CURRENT_ROW),
        ),
    ),
)
def test_explicit_frame_shape_invariants_reject_missing_or_extra_end(
    frame: AuthoredWindowFrame,
) -> None:
    if frame.kind is AuthoredWindowFrameKind.SHORTHAND:
        with pytest.raises(ValueError):
            replace(frame, end=_bound(WindowFrameBoundKind.CURRENT_ROW))
    else:
        with pytest.raises(ValueError):
            replace(frame, end=None)
    with pytest.raises(ValueError):
        replace(frame, unit=None)
    with pytest.raises(ValueError):
        replace(frame, start=None)


def test_authored_specification_requires_exact_tuples_span_and_frame() -> None:
    frame = AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED)
    specification = AuthoredWindowSpecification(
        span=SPAN,
        partition_by=(_name("account_id"),),
        order_by=(_order(),),
        frame=frame,
    )
    assert specification.frame is frame
    with pytest.raises(TypeError):
        replace(specification, span=cast(Any, object()))
    with pytest.raises(TypeError):
        replace(specification, partition_by=cast(Any, []))
    with pytest.raises(TypeError):
        replace(specification, order_by=cast(Any, []))
    with pytest.raises(TypeError):
        replace(specification, frame=cast(Any, object()))


@pytest.mark.parametrize("has_ordering", (False, True))
def test_omitted_applicable_frame_resolves_the_exact_pietto_default(
    has_ordering: bool,
) -> None:
    authored = _omitted_spec(
        partition_by=(_name("account_id"),),
        order_by=(_order(),) if has_ordering else (),
    )
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert resolved.authored is authored
    assert resolved.partition_by is authored.partition_by
    assert resolved.order_by is authored.order_by
    assert resolved.partition_origin is WindowComponentOrigin.LOCALLY_AUTHORED
    assert resolved.ordering_origin is (
        WindowComponentOrigin.LOCALLY_AUTHORED
        if has_ordering
        else WindowComponentOrigin.EFFECTIVE_DEFAULT
    )
    assert resolved.frame.applicability is WindowFrameApplicability.APPLICABLE
    assert resolved.frame.origin is WindowComponentOrigin.EFFECTIVE_DEFAULT
    assert resolved.frame.authored is authored.frame
    assert resolved.frame.unit is WindowFrameUnit.RANGE
    assert resolved.frame.start == _bound(WindowFrameBoundKind.UNBOUNDED_PRECEDING)
    assert resolved.frame.end == _bound(WindowFrameBoundKind.CURRENT_ROW)
    assert resolved.frame.exclusion is WindowFrameExclusion.NO_OTHERS


def test_omitted_and_explicit_default_equivalent_frames_keep_distinct_authorship() -> (
    None
):
    omitted = _omitted_spec(order_by=(_order(),))
    explicit = replace(
        omitted,
        frame=_explicit_default_frame(AuthoredWindowFrameExclusion.NO_OTHERS),
    )
    omitted_resolved = resolve_authored_window_specification(
        omitted,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    explicit_resolved = resolve_authored_window_specification(
        explicit,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert omitted.frame != explicit.frame
    assert omitted_resolved.frame.origin is WindowComponentOrigin.EFFECTIVE_DEFAULT
    assert explicit_resolved.frame.origin is WindowComponentOrigin.LOCALLY_AUTHORED
    assert _effective_frame_key(omitted_resolved.frame) == _effective_frame_key(
        explicit_resolved.frame
    )
    assert omitted_resolved.frame != explicit_resolved.frame


def test_omitted_and_explicit_no_others_have_equal_effective_exclusion_only() -> None:
    omitted_exclusion = _explicit_default_frame(AuthoredWindowFrameExclusion.OMITTED)
    explicit_exclusion = _explicit_default_frame(AuthoredWindowFrameExclusion.NO_OTHERS)
    authored = _omitted_spec(order_by=(_order(),))
    omitted_resolved = resolve_authored_window_specification(
        replace(authored, frame=omitted_exclusion),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    explicit_resolved = resolve_authored_window_specification(
        replace(authored, frame=explicit_exclusion),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert omitted_exclusion.exclusion is AuthoredWindowFrameExclusion.OMITTED
    assert explicit_exclusion.exclusion is AuthoredWindowFrameExclusion.NO_OTHERS
    assert omitted_resolved.frame.exclusion is WindowFrameExclusion.NO_OTHERS
    assert explicit_resolved.frame.exclusion is WindowFrameExclusion.NO_OTHERS
    assert _effective_frame_key(omitted_resolved.frame) == _effective_frame_key(
        explicit_resolved.frame
    )
    assert omitted_resolved.frame != explicit_resolved.frame


@pytest.mark.parametrize(
    ("authored_exclusion", "effective_exclusion"),
    (
        (
            AuthoredWindowFrameExclusion.CURRENT_ROW,
            WindowFrameExclusion.CURRENT_ROW,
        ),
        (AuthoredWindowFrameExclusion.GROUP, WindowFrameExclusion.GROUP),
        (AuthoredWindowFrameExclusion.TIES, WindowFrameExclusion.TIES),
    ),
)
def test_explicit_nondefault_exclusions_resolve_exactly(
    authored_exclusion: AuthoredWindowFrameExclusion,
    effective_exclusion: WindowFrameExclusion,
) -> None:
    authored = replace(
        _omitted_spec(),
        frame=_explicit_default_frame(authored_exclusion),
    )
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert resolved.frame.exclusion is effective_exclusion
    assert resolved.frame.authored.exclusion is authored_exclusion


def test_shorthand_and_explicit_between_current_row_keep_distinct_authorship() -> None:
    start = _bound(WindowFrameBoundKind.OFFSET_PRECEDING, _literal(4))
    shorthand = AuthoredWindowFrame(
        kind=AuthoredWindowFrameKind.SHORTHAND,
        unit=WindowFrameUnit.ROWS,
        start=start,
    )
    between = AuthoredWindowFrame(
        kind=AuthoredWindowFrameKind.BETWEEN,
        unit=WindowFrameUnit.ROWS,
        start=start,
        end=_bound(WindowFrameBoundKind.CURRENT_ROW),
    )
    authored = _omitted_spec(order_by=(_order(),))
    shorthand_resolved = resolve_authored_window_specification(
        replace(authored, frame=shorthand),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    between_resolved = resolve_authored_window_specification(
        replace(authored, frame=between),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert shorthand_resolved.frame.start is start
    assert shorthand_resolved.frame.end == _bound(WindowFrameBoundKind.CURRENT_ROW)
    assert shorthand != between
    assert _effective_frame_key(shorthand_resolved.frame) == _effective_frame_key(
        between_resolved.frame
    )
    assert shorthand_resolved.frame != between_resolved.frame


@pytest.mark.parametrize("explicit", (False, True))
def test_frame_not_applicable_is_typed_and_preserves_authored_evidence(
    explicit: bool,
) -> None:
    authored = _omitted_spec(order_by=(_order(),))
    if explicit:
        authored = replace(
            authored,
            frame=_explicit_default_frame(AuthoredWindowFrameExclusion.OMITTED),
        )
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.NOT_APPLICABLE,
    )
    assert resolved.frame.applicability is WindowFrameApplicability.NOT_APPLICABLE
    assert resolved.frame.origin is WindowComponentOrigin.NOT_APPLICABLE
    assert resolved.frame.authored is authored.frame
    assert (
        resolved.frame.unit,
        resolved.frame.start,
        resolved.frame.end,
        resolved.frame.exclusion,
    ) == (None, None, None, None)
    assert (
        resolved.frame
        != resolve_authored_window_specification(
            authored,
            frame_applicability=WindowFrameApplicability.APPLICABLE,
        ).frame
    )


def test_resolved_frame_applicability_origin_and_payload_invariants_fail_closed() -> (
    None
):
    omitted = AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED)
    default = resolve_authored_window_specification(
        _omitted_spec(),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    ).frame
    with pytest.raises(ValueError):
        replace(default, origin=WindowComponentOrigin.NOT_APPLICABLE)
    with pytest.raises(ValueError):
        replace(default, unit=None)
    with pytest.raises(ValueError):
        replace(default, unit=WindowFrameUnit.ROWS)
    with pytest.raises(ValueError):
        replace(
            default,
            authored=_explicit_default_frame(AuthoredWindowFrameExclusion.OMITTED),
        )
    explicit = resolve_authored_window_specification(
        replace(
            _omitted_spec(),
            frame=_explicit_default_frame(AuthoredWindowFrameExclusion.OMITTED),
        ),
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    ).frame
    with pytest.raises(ValueError):
        replace(
            explicit,
            start=_bound(WindowFrameBoundKind.UNBOUNDED_PRECEDING),
        )
    with pytest.raises(ValueError):
        replace(explicit, exclusion=WindowFrameExclusion.TIES)
    not_applicable = ResolvedWindowFrame(
        applicability=WindowFrameApplicability.NOT_APPLICABLE,
        origin=WindowComponentOrigin.NOT_APPLICABLE,
        authored=omitted,
    )
    with pytest.raises(ValueError):
        replace(not_applicable, unit=WindowFrameUnit.ROWS)
    with pytest.raises(ValueError):
        replace(not_applicable, origin=WindowComponentOrigin.EFFECTIVE_DEFAULT)


def test_component_origin_seam_accepts_exact_inherited_evidence_only() -> None:
    base_authored = replace(
        _omitted_spec(),
        frame=_explicit_default_frame(AuthoredWindowFrameExclusion.OMITTED),
    )
    base = resolve_authored_window_specification(
        base_authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    authored = _omitted_spec()
    partition = (_name("account_id"),)
    ordering = (_order(),)
    inherited = ResolvedWindowSpecification(
        authored=authored,
        partition_by=partition,
        order_by=ordering,
        partition_origin=WindowComponentOrigin.INHERITED,
        ordering_origin=WindowComponentOrigin.INHERITED,
        frame=replace(base.frame, origin=WindowComponentOrigin.INHERITED),
    )
    assert inherited.partition_origin is WindowComponentOrigin.INHERITED
    assert inherited.ordering_origin is WindowComponentOrigin.INHERITED
    assert inherited.frame.origin is WindowComponentOrigin.INHERITED
    with pytest.raises(ValueError):
        replace(inherited, partition_by=())
    with pytest.raises(ValueError):
        replace(inherited, ordering_origin=WindowComponentOrigin.NOT_APPLICABLE)
    with pytest.raises(TypeError):
        replace(inherited, partition_origin=cast(Any, "inherited"))

    local_authored = _omitted_spec(
        partition_by=partition,
        order_by=ordering,
    )
    local = resolve_authored_window_specification(
        local_authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    with pytest.raises(ValueError):
        replace(local, partition_by=(_name("other"),))
    with pytest.raises(ValueError):
        replace(local, partition_origin=WindowComponentOrigin.INHERITED)


def test_slice2_does_not_implement_bound_legality() -> None:
    authored = replace(
        _omitted_spec(),
        frame=AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.BETWEEN,
            unit=WindowFrameUnit.GROUPS,
            start=_bound(WindowFrameBoundKind.UNBOUNDED_FOLLOWING),
            end=_bound(WindowFrameBoundKind.UNBOUNDED_PRECEDING),
        ),
    )
    resolved = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert resolved.frame.start is authored.frame.start
    assert resolved.frame.end is authored.frame.end


def test_resolution_is_pure_deterministic_hashable_and_environment_independent(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    offset = _literal(5)
    authored = AuthoredWindowSpecification(
        span=SPAN,
        partition_by=(_name("account_id"),),
        order_by=(_order(),),
        frame=AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.SHORTHAND,
            unit=WindowFrameUnit.ROWS,
            start=_bound(WindowFrameBoundKind.OFFSET_PRECEDING, offset),
            exclusion=AuthoredWindowFrameExclusion.TIES,
        ),
    )
    first = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PIETTO_WINDOW_FRAME_DEFAULT", "backend-owned")
    second = resolve_authored_window_specification(
        authored,
        frame_applicability=WindowFrameApplicability.APPLICABLE,
    )
    assert first == second
    assert hash(first) == hash(second)
    assert first.frame.start is authored.frame.start
    assert first.frame.start is not None
    assert first.frame.start.offset is offset
    with pytest.raises(FrozenInstanceError):
        first.frame.origin = WindowComponentOrigin.INHERITED  # pyright: ignore[reportAttributeAccessIssue]


def test_existing_window_occurrence_identity_and_resolution_signature_are_unchanged() -> (
    None
):
    assert tuple(field.name for field in fields(WindowOccurrenceIdentity)) == (
        "source_id",
        "relation_name",
        "selected_output_ordinal",
        "span",
    )
    parameters = inspect.signature(resolve_authored_window_specification).parameters
    assert tuple(parameters) == ("authored", "frame_applicability")
    assert parameters["frame_applicability"].kind is inspect.Parameter.KEYWORD_ONLY


def test_spec_freezes_slice2_scope_non_goals_lifecycle_and_subject() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for evidence in (
        "AuthoredWindowSpecification",
        "ResolvedWindowSpecification",
        "RANGE BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW",
        "The exact expression object is retained",
        "WindowFrameApplicability.NOT_APPLICABLE",
        "`INHERITED` requires local omission",
        "no semantic-equivalence key/API",
        "Phase 59 package/module/declaration/field/ current-window identities",
        "A2/M5/D0",
        "Slice 3 is neither implemented nor authorized",
        "Add Phase 60 authored window frame model",
    ):
        assert evidence in document
