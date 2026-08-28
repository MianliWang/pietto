"""Private semantic carriers for structurally identified window expressions."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto._window_identity import WindowFunctionIdentity
from pietto.ast_nodes import (
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    OrderItem,
    Span,
    WindowExpr,
)
from pietto.semantic.aggregates import child_expressions
from pietto.semantic.generic_compatibility import SignatureMatch
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)
from pietto.semantic.nullability_formulas import NullabilityEvaluationMatch

__all__: tuple[str, ...] = ()


class WindowExpressionStage(StrEnum):
    """The standalone private stage carried by one window-expression fact."""

    WINDOW = "WINDOW"


class WindowFrameUnit(StrEnum):
    """Closed frame-unit semantics independent of target SQL support."""

    ROWS = "rows"
    RANGE = "range"
    GROUPS = "groups"


class WindowFrameBoundKind(StrEnum):
    """Closed structural frame-bound variants without legality semantics."""

    UNBOUNDED_PRECEDING = "unbounded_preceding"
    OFFSET_PRECEDING = "offset_preceding"
    CURRENT_ROW = "current_row"
    OFFSET_FOLLOWING = "offset_following"
    UNBOUNDED_FOLLOWING = "unbounded_following"


_OFFSET_WINDOW_FRAME_BOUND_KINDS = frozenset(
    {
        WindowFrameBoundKind.OFFSET_PRECEDING,
        WindowFrameBoundKind.OFFSET_FOLLOWING,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowFrameBound:
    """One typed bound retaining the exact existing expression authority."""

    kind: WindowFrameBoundKind
    offset: Expression | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowFrameBoundKind:
            raise TypeError("frame bound kind must be an exact WindowFrameBoundKind")
        if self.kind in _OFFSET_WINDOW_FRAME_BOUND_KINDS:
            if not isinstance(self.offset, Expression):
                raise TypeError("offset frame bounds require an Expression")
        elif self.offset is not None:
            raise ValueError("non-offset frame bounds forbid an offset expression")


class WindowFrameExclusion(StrEnum):
    """Concrete effective frame-exclusion semantics."""

    NO_OTHERS = "no_others"
    CURRENT_ROW = "current_row"
    GROUP = "group"
    TIES = "ties"


class AuthoredWindowFrameExclusion(StrEnum):
    """Omitted or explicit source exclusion without collapsing authorship."""

    OMITTED = "omitted"
    NO_OTHERS = "no_others"
    CURRENT_ROW = "current_row"
    GROUP = "group"
    TIES = "ties"


class AuthoredWindowFrameKind(StrEnum):
    """Closed authored frame-clause forms."""

    OMITTED = "omitted"
    SHORTHAND = "shorthand"
    BETWEEN = "between"


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthoredWindowFrame:
    """One exact authored frame form with explicit omission evidence."""

    kind: AuthoredWindowFrameKind
    unit: WindowFrameUnit | None = None
    start: WindowFrameBound | None = None
    end: WindowFrameBound | None = None
    exclusion: AuthoredWindowFrameExclusion = AuthoredWindowFrameExclusion.OMITTED

    def __post_init__(self) -> None:
        if type(self.kind) is not AuthoredWindowFrameKind:
            raise TypeError(
                "authored frame kind must be an exact AuthoredWindowFrameKind"
            )
        if self.unit is not None and type(self.unit) is not WindowFrameUnit:
            raise TypeError("authored frame unit must be an exact WindowFrameUnit")
        if self.start is not None and type(self.start) is not WindowFrameBound:
            raise TypeError("authored frame start must be an exact WindowFrameBound")
        if self.end is not None and type(self.end) is not WindowFrameBound:
            raise TypeError("authored frame end must be an exact WindowFrameBound")
        if type(self.exclusion) is not AuthoredWindowFrameExclusion:
            raise TypeError(
                "authored frame exclusion must be an exact AuthoredWindowFrameExclusion"
            )

        if self.kind is AuthoredWindowFrameKind.OMITTED:
            if (
                self.unit is not None
                or self.start is not None
                or self.end is not None
                or self.exclusion is not AuthoredWindowFrameExclusion.OMITTED
            ):
                raise ValueError("omitted frames forbid authored frame components")
            return
        if self.unit is None or self.start is None:
            raise ValueError("explicit frames require a unit and start bound")
        if self.kind is AuthoredWindowFrameKind.SHORTHAND:
            if self.end is not None:
                raise ValueError("shorthand frames require an omitted end bound")
            return
        if self.end is None:
            raise ValueError("BETWEEN frames require an explicit end bound")


class WindowFrameApplicability(StrEnum):
    """Whether the owning function family has frame semantics."""

    APPLICABLE = "applicable"
    NOT_APPLICABLE = "not_applicable"


class WindowComponentOrigin(StrEnum):
    """Authorship provenance for one resolved window component."""

    LOCALLY_AUTHORED = "locally_authored"
    INHERITED = "inherited"
    EFFECTIVE_DEFAULT = "effective_default"
    NOT_APPLICABLE = "not_applicable"


def _effective_window_frame_exclusion(
    authored: AuthoredWindowFrameExclusion,
) -> WindowFrameExclusion:
    return (
        WindowFrameExclusion.NO_OTHERS
        if authored is AuthoredWindowFrameExclusion.OMITTED
        else WindowFrameExclusion(authored.value)
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedWindowFrame:
    """Concrete effective frame or one explicit not-applicable state."""

    applicability: WindowFrameApplicability
    origin: WindowComponentOrigin
    authored: AuthoredWindowFrame
    unit: WindowFrameUnit | None = None
    start: WindowFrameBound | None = None
    end: WindowFrameBound | None = None
    exclusion: WindowFrameExclusion | None = None

    def __post_init__(self) -> None:
        if type(self.applicability) is not WindowFrameApplicability:
            raise TypeError(
                "resolved frame applicability must be an exact WindowFrameApplicability"
            )
        if type(self.origin) is not WindowComponentOrigin:
            raise TypeError(
                "resolved frame origin must be an exact WindowComponentOrigin"
            )
        if type(self.authored) is not AuthoredWindowFrame:
            raise TypeError("resolved frame requires an exact authored frame")
        if self.unit is not None and type(self.unit) is not WindowFrameUnit:
            raise TypeError("resolved frame unit must be an exact WindowFrameUnit")
        if self.start is not None and type(self.start) is not WindowFrameBound:
            raise TypeError("resolved frame start must be an exact WindowFrameBound")
        if self.end is not None and type(self.end) is not WindowFrameBound:
            raise TypeError("resolved frame end must be an exact WindowFrameBound")
        if (
            self.exclusion is not None
            and type(self.exclusion) is not WindowFrameExclusion
        ):
            raise TypeError(
                "resolved frame exclusion must be an exact WindowFrameExclusion"
            )

        if self.applicability is WindowFrameApplicability.NOT_APPLICABLE:
            if self.origin is not WindowComponentOrigin.NOT_APPLICABLE:
                raise ValueError("not-applicable frames require NOT_APPLICABLE origin")
            if any(
                value is not None
                for value in (self.unit, self.start, self.end, self.exclusion)
            ):
                raise ValueError("not-applicable frames forbid effective components")
            return

        if self.origin is WindowComponentOrigin.NOT_APPLICABLE:
            raise ValueError("applicable frames forbid NOT_APPLICABLE origin")
        if any(
            value is None for value in (self.unit, self.start, self.end, self.exclusion)
        ):
            raise ValueError("applicable frames require complete effective components")
        if self.origin is WindowComponentOrigin.EFFECTIVE_DEFAULT:
            if self.authored.kind is not AuthoredWindowFrameKind.OMITTED:
                raise ValueError("defaulted frames require authored omission")
            if (
                self.unit is not WindowFrameUnit.RANGE
                or self.start
                != WindowFrameBound(
                    kind=WindowFrameBoundKind.UNBOUNDED_PRECEDING,
                )
                or self.end != WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)
                or self.exclusion is not WindowFrameExclusion.NO_OTHERS
            ):
                raise ValueError("defaulted frames require Pietto effective defaults")
            return

        if self.authored.kind is AuthoredWindowFrameKind.OMITTED:
            raise ValueError("authored or inherited frames require an explicit frame")
        assert self.authored.unit is not None
        assert self.authored.start is not None
        expected_end = (
            WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)
            if self.authored.kind is AuthoredWindowFrameKind.SHORTHAND
            else self.authored.end
        )
        assert expected_end is not None
        if (
            self.unit is not self.authored.unit
            or self.start is not self.authored.start
            or (
                self.authored.kind is AuthoredWindowFrameKind.BETWEEN
                and self.end is not expected_end
            )
            or (
                self.authored.kind is AuthoredWindowFrameKind.SHORTHAND
                and self.end != expected_end
            )
            or self.exclusion
            is not _effective_window_frame_exclusion(self.authored.exclusion)
        ):
            raise ValueError("resolved frame components must match authored evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthoredWindowSpecification:
    """One source-located authored window specification before resolution."""

    span: Span
    partition_by: tuple[Expression, ...]
    order_by: tuple[OrderItem, ...]
    frame: AuthoredWindowFrame

    def __post_init__(self) -> None:
        if type(self.span) is not Span:
            raise TypeError("authored window span must be an exact Span")
        if type(self.partition_by) is not tuple or any(
            not isinstance(item, Expression) for item in self.partition_by
        ):
            raise TypeError("authored window partition must be an Expression tuple")
        if type(self.order_by) is not tuple or any(
            type(item) is not OrderItem for item in self.order_by
        ):
            raise TypeError("authored window order must be an exact OrderItem tuple")
        if type(self.frame) is not AuthoredWindowFrame:
            raise TypeError("authored window requires an exact authored frame")


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedWindowSpecification:
    """One complete resolved window specification without validation behavior."""

    authored: AuthoredWindowSpecification
    partition_by: tuple[Expression, ...]
    order_by: tuple[OrderItem, ...]
    partition_origin: WindowComponentOrigin
    ordering_origin: WindowComponentOrigin
    frame: ResolvedWindowFrame

    def __post_init__(self) -> None:
        if type(self.authored) is not AuthoredWindowSpecification:
            raise TypeError("resolved window requires an exact authored window")
        if type(self.partition_by) is not tuple or any(
            not isinstance(item, Expression) for item in self.partition_by
        ):
            raise TypeError("resolved window partition must be an Expression tuple")
        if type(self.order_by) is not tuple or any(
            type(item) is not OrderItem for item in self.order_by
        ):
            raise TypeError("resolved window order must be an exact OrderItem tuple")
        _require_resolved_component_origin(
            self.partition_by,
            self.authored.partition_by,
            self.partition_origin,
            "partition",
        )
        _require_resolved_component_origin(
            self.order_by,
            self.authored.order_by,
            self.ordering_origin,
            "ordering",
        )
        if type(self.frame) is not ResolvedWindowFrame:
            raise TypeError("resolved window requires an exact resolved frame")


def _require_resolved_component_origin(
    values: tuple[object, ...],
    authored_values: tuple[object, ...],
    origin: WindowComponentOrigin,
    label: str,
) -> None:
    if type(origin) is not WindowComponentOrigin:
        raise TypeError(f"resolved {label} origin must be exact")
    if origin is WindowComponentOrigin.NOT_APPLICABLE:
        raise ValueError(f"resolved {label} forbids NOT_APPLICABLE origin")
    if origin is WindowComponentOrigin.EFFECTIVE_DEFAULT:
        if values or authored_values:
            raise ValueError(f"defaulted {label} requires authored omission")
    elif origin is WindowComponentOrigin.LOCALLY_AUTHORED:
        if not values or values != authored_values:
            raise ValueError(f"local {label} must equal authored values")
    elif not values or authored_values:
        raise ValueError(f"inherited {label} requires local omission and values")


def resolve_authored_window_specification(
    authored: AuthoredWindowSpecification,
    *,
    frame_applicability: WindowFrameApplicability,
) -> ResolvedWindowSpecification:
    """Resolve only authored omission, shorthand, and effective defaults."""

    if type(authored) is not AuthoredWindowSpecification:
        raise TypeError("window resolution requires an exact authored specification")
    if type(frame_applicability) is not WindowFrameApplicability:
        raise TypeError("window resolution requires exact frame applicability")
    return ResolvedWindowSpecification(
        authored=authored,
        partition_by=authored.partition_by,
        order_by=authored.order_by,
        partition_origin=(
            WindowComponentOrigin.LOCALLY_AUTHORED
            if authored.partition_by
            else WindowComponentOrigin.EFFECTIVE_DEFAULT
        ),
        ordering_origin=(
            WindowComponentOrigin.LOCALLY_AUTHORED
            if authored.order_by
            else WindowComponentOrigin.EFFECTIVE_DEFAULT
        ),
        frame=_resolve_authored_window_frame(
            authored.frame,
            frame_applicability=frame_applicability,
        ),
    )


def _resolve_authored_window_frame(
    authored: AuthoredWindowFrame,
    *,
    frame_applicability: WindowFrameApplicability,
) -> ResolvedWindowFrame:
    if frame_applicability is WindowFrameApplicability.NOT_APPLICABLE:
        return ResolvedWindowFrame(
            applicability=frame_applicability,
            origin=WindowComponentOrigin.NOT_APPLICABLE,
            authored=authored,
        )
    if authored.kind is AuthoredWindowFrameKind.OMITTED:
        return ResolvedWindowFrame(
            applicability=frame_applicability,
            origin=WindowComponentOrigin.EFFECTIVE_DEFAULT,
            authored=authored,
            unit=WindowFrameUnit.RANGE,
            start=WindowFrameBound(
                kind=WindowFrameBoundKind.UNBOUNDED_PRECEDING,
            ),
            end=WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW),
            exclusion=WindowFrameExclusion.NO_OTHERS,
        )

    assert authored.unit is not None
    assert authored.start is not None
    end = (
        WindowFrameBound(kind=WindowFrameBoundKind.CURRENT_ROW)
        if authored.kind is AuthoredWindowFrameKind.SHORTHAND
        else authored.end
    )
    assert end is not None
    return ResolvedWindowFrame(
        applicability=frame_applicability,
        origin=WindowComponentOrigin.LOCALLY_AUTHORED,
        authored=authored,
        unit=authored.unit,
        start=authored.start,
        end=end,
        exclusion=_effective_window_frame_exclusion(authored.exclusion),
    )


class WindowFrameEmptinessClassification(StrEnum):
    """Closed frame-cardinality evidence available at validation time."""

    STRUCTURALLY_INVALID = "structurally_invalid"
    GUARANTEED_NONEMPTY = "guaranteed_nonempty"
    POSSIBLY_EMPTY = "possibly_empty"
    ALWAYS_EMPTY = "always_empty"


class WindowFrameStructuralFailureKind(StrEnum):
    """Closed structural bound failures independent of offset values."""

    START_UNBOUNDED_FOLLOWING = "start_unbounded_following"
    END_UNBOUNDED_PRECEDING = "end_unbounded_preceding"
    REVERSED_BOUND_CATEGORIES = "reversed_bound_categories"


class WindowFunctionFramePolicyKind(StrEnum):
    """Whether one exact function identity admits effective frame semantics."""

    FRAME_SENSITIVE = "frame_sensitive"
    FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN = "frame_insensitive_explicit_forbidden"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowFunctionFramePolicy:
    """Extensible frame authority bound to one exact semantic identity."""

    identity: WindowFunctionIdentity
    kind: WindowFunctionFramePolicyKind

    def __post_init__(self) -> None:
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("frame policy identity must be exact")
        if type(self.kind) is not WindowFunctionFramePolicyKind:
            raise TypeError("frame policy kind must be exact")

    @property
    def required_frame_applicability(self) -> WindowFrameApplicability:
        """Return the exact Slice 2 applicability required by this policy."""

        if self.kind is WindowFunctionFramePolicyKind.FRAME_SENSITIVE:
            return WindowFrameApplicability.APPLICABLE
        return WindowFrameApplicability.NOT_APPLICABLE


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedFrame:
    """One structurally valid applicable frame with exact emptiness evidence."""

    resolved: ResolvedWindowFrame
    classification: WindowFrameEmptinessClassification

    def __post_init__(self) -> None:
        if type(self.resolved) is not ResolvedWindowFrame:
            raise TypeError("validated frame requires an exact resolved frame")
        if type(self.classification) is not WindowFrameEmptinessClassification:
            raise TypeError("validated frame classification must be exact")
        if self.resolved.applicability is not WindowFrameApplicability.APPLICABLE:
            raise ValueError("validated frames require applicable frame semantics")
        if self.classification is (
            WindowFrameEmptinessClassification.STRUCTURALLY_INVALID
        ):
            raise ValueError("validated frames forbid structural invalidity")
        if _structural_frame_failures(self.resolved):
            raise ValueError("structurally invalid frames cannot be validated")
        if self.classification is not _classify_valid_frame(self.resolved):
            raise ValueError("validated frame classification must be strongest known")


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedFrameNotApplicable:
    """One validated typed absence of function-owned frame semantics."""

    resolved: ResolvedWindowFrame

    def __post_init__(self) -> None:
        if type(self.resolved) is not ResolvedWindowFrame:
            raise TypeError("validated frame absence requires an exact resolved frame")
        if self.resolved.applicability is not (WindowFrameApplicability.NOT_APPLICABLE):
            raise ValueError("validated frame absence requires NOT_APPLICABLE")


@dataclass(frozen=True, slots=True, kw_only=True)
class StructurallyInvalidFrame:
    """Complete structural rejection evidence with no validated frame."""

    resolved: ResolvedWindowFrame
    failures: tuple[WindowFrameStructuralFailureKind, ...]
    classification: WindowFrameEmptinessClassification = field(
        init=False,
        default=WindowFrameEmptinessClassification.STRUCTURALLY_INVALID,
    )

    def __post_init__(self) -> None:
        if type(self.resolved) is not ResolvedWindowFrame:
            raise TypeError("invalid frame evidence requires an exact resolved frame")
        if type(self.failures) is not tuple or any(
            type(item) is not WindowFrameStructuralFailureKind for item in self.failures
        ):
            raise TypeError("structural frame failures must be an exact typed tuple")
        expected = _structural_frame_failures(self.resolved)
        if not expected or self.failures != expected:
            raise ValueError("structural frame failures must be complete and ordered")


class WindowValidationIssueKind(StrEnum):
    """Closed reasons a resolved window cannot enter the validated stage."""

    STRUCTURALLY_INVALID_FRAME = "structurally_invalid_frame"
    MISSING_FUNCTION_FRAME_POLICY = "missing_function_frame_policy"
    FUNCTION_FRAME_POLICY_IDENTITY_MISMATCH = "function_frame_policy_identity_mismatch"
    FRAME_APPLICABILITY_MISMATCH = "frame_applicability_mismatch"
    EXPLICIT_FRAME_FORBIDDEN = "explicit_frame_forbidden"
    NESTED_WINDOW_EXPRESSION = "nested_window_expression"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowValidationIssue:
    """One typed issue with exact structural or nested evidence when applicable."""

    kind: WindowValidationIssueKind
    structural_failure: StructurallyInvalidFrame | None = None
    nested_expressions: tuple[WindowExpr, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowValidationIssueKind:
            raise TypeError("window validation issue kind must be exact")
        if (
            self.structural_failure is not None
            and type(self.structural_failure) is not StructurallyInvalidFrame
        ):
            raise TypeError("structural failure evidence must be exact")
        if type(self.nested_expressions) is not tuple or any(
            type(item) is not WindowExpr for item in self.nested_expressions
        ):
            raise TypeError("nested window evidence must be an exact WindowExpr tuple")

        if self.kind is WindowValidationIssueKind.STRUCTURALLY_INVALID_FRAME:
            if self.structural_failure is None or self.nested_expressions:
                raise ValueError("structural issues require only structural evidence")
            return
        if self.kind is WindowValidationIssueKind.NESTED_WINDOW_EXPRESSION:
            if self.structural_failure is not None or not self.nested_expressions:
                raise ValueError("nested issues require only nonempty nested evidence")
            return
        if self.structural_failure is not None or self.nested_expressions:
            raise ValueError("policy issues forbid structural or nested evidence")


@dataclass(frozen=True, slots=True, kw_only=True)
class ValidatedWindowSpecification:
    """One complete immutable Resolved-to-Validated normalization."""

    resolved: ResolvedWindowSpecification
    function_identity: WindowFunctionIdentity
    function_policy: WindowFunctionFramePolicy
    argument_expressions: tuple[Expression, ...]
    frame: ValidatedFrame | ValidatedFrameNotApplicable

    def __post_init__(self) -> None:
        _require_window_validation_inputs(
            self.resolved,
            self.function_identity,
            self.function_policy,
            self.argument_expressions,
        )
        if type(self.frame) not in {ValidatedFrame, ValidatedFrameNotApplicable}:
            raise TypeError("validated window frame evidence must be exact")
        if self.frame.resolved is not self.resolved.frame:
            raise ValueError("validated frame must retain the exact resolved frame")
        if _window_validation_issues(
            self.resolved,
            self.function_identity,
            self.function_policy,
            self.argument_expressions,
        ):
            raise ValueError("invalid resolved windows cannot be validated")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowSpecificationValidationFailure:
    """One complete ordered rejection with no partial validated value."""

    resolved: ResolvedWindowSpecification
    function_identity: WindowFunctionIdentity
    function_policy: WindowFunctionFramePolicy | None
    argument_expressions: tuple[Expression, ...]
    issues: tuple[WindowValidationIssue, ...]

    def __post_init__(self) -> None:
        _require_window_validation_inputs(
            self.resolved,
            self.function_identity,
            self.function_policy,
            self.argument_expressions,
        )
        if type(self.issues) is not tuple or any(
            type(item) is not WindowValidationIssue for item in self.issues
        ):
            raise TypeError("window validation issues must be an exact typed tuple")
        expected = _window_validation_issues(
            self.resolved,
            self.function_identity,
            self.function_policy,
            self.argument_expressions,
        )
        if not expected or self.issues != expected:
            raise ValueError("window validation issues must be complete and ordered")


_WINDOW_FRAME_BOUND_CATEGORY_ORDER = (
    WindowFrameBoundKind.UNBOUNDED_PRECEDING,
    WindowFrameBoundKind.OFFSET_PRECEDING,
    WindowFrameBoundKind.CURRENT_ROW,
    WindowFrameBoundKind.OFFSET_FOLLOWING,
    WindowFrameBoundKind.UNBOUNDED_FOLLOWING,
)


def _structural_frame_failures(
    frame: ResolvedWindowFrame,
) -> tuple[WindowFrameStructuralFailureKind, ...]:
    if frame.applicability is WindowFrameApplicability.NOT_APPLICABLE:
        return ()
    assert frame.start is not None
    assert frame.end is not None
    failures: list[WindowFrameStructuralFailureKind] = []
    if frame.start.kind is WindowFrameBoundKind.UNBOUNDED_FOLLOWING:
        failures.append(WindowFrameStructuralFailureKind.START_UNBOUNDED_FOLLOWING)
    if frame.end.kind is WindowFrameBoundKind.UNBOUNDED_PRECEDING:
        failures.append(WindowFrameStructuralFailureKind.END_UNBOUNDED_PRECEDING)
    if _WINDOW_FRAME_BOUND_CATEGORY_ORDER.index(
        frame.start.kind
    ) > _WINDOW_FRAME_BOUND_CATEGORY_ORDER.index(frame.end.kind):
        failures.append(WindowFrameStructuralFailureKind.REVERSED_BOUND_CATEGORIES)
    return tuple(failures)


def _classify_valid_frame(
    frame: ResolvedWindowFrame,
) -> WindowFrameEmptinessClassification:
    assert frame.unit is not None
    assert frame.start is not None
    assert frame.end is not None
    assert frame.exclusion is not None
    start_kind = frame.start.kind
    end_kind = frame.end.kind

    if (
        start_kind is WindowFrameBoundKind.CURRENT_ROW
        and end_kind is WindowFrameBoundKind.CURRENT_ROW
        and (
            frame.exclusion is WindowFrameExclusion.GROUP
            or (
                frame.unit is WindowFrameUnit.ROWS
                and frame.exclusion is WindowFrameExclusion.CURRENT_ROW
            )
        )
    ):
        return WindowFrameEmptinessClassification.ALWAYS_EMPTY

    current_rank = _WINDOW_FRAME_BOUND_CATEGORY_ORDER.index(
        WindowFrameBoundKind.CURRENT_ROW
    )
    retains_current = _WINDOW_FRAME_BOUND_CATEGORY_ORDER.index(
        start_kind
    ) <= current_rank <= _WINDOW_FRAME_BOUND_CATEGORY_ORDER.index(
        end_kind
    ) and frame.exclusion in {WindowFrameExclusion.NO_OTHERS, WindowFrameExclusion.TIES}
    if retains_current:
        return WindowFrameEmptinessClassification.GUARANTEED_NONEMPTY
    return WindowFrameEmptinessClassification.POSSIBLY_EMPTY


def _require_window_validation_inputs(
    resolved: ResolvedWindowSpecification,
    function_identity: WindowFunctionIdentity,
    function_policy: WindowFunctionFramePolicy | None,
    argument_expressions: tuple[Expression, ...],
) -> None:
    if type(resolved) is not ResolvedWindowSpecification:
        raise TypeError("window validation requires an exact resolved specification")
    if type(function_identity) is not WindowFunctionIdentity:
        raise TypeError("window validation requires an exact function identity")
    if (
        function_policy is not None
        and type(function_policy) is not WindowFunctionFramePolicy
    ):
        raise TypeError("window validation policy must be exact or absent")
    if type(argument_expressions) is not tuple or any(
        not isinstance(item, Expression) for item in argument_expressions
    ):
        raise TypeError("window validation arguments must be an Expression tuple")


def _nested_window_expressions(
    resolved: ResolvedWindowSpecification,
    argument_expressions: tuple[Expression, ...],
) -> tuple[WindowExpr, ...]:
    roots: list[Expression] = [
        *argument_expressions,
        *resolved.partition_by,
        *(item.expression for item in resolved.order_by),
    ]
    for bound in (resolved.frame.start, resolved.frame.end):
        if bound is not None and bound.offset is not None:
            roots.append(bound.offset)
    return tuple(
        nested for root in roots for nested in _window_expressions_in_source_order(root)
    )


def _window_expressions_in_source_order(
    expression: Expression,
) -> tuple[WindowExpr, ...]:
    if type(expression) is WindowExpr:
        return (expression,)
    return tuple(
        nested
        for child in child_expressions(expression)
        for nested in _window_expressions_in_source_order(child)
    )


def _window_validation_issues(
    resolved: ResolvedWindowSpecification,
    function_identity: WindowFunctionIdentity,
    function_policy: WindowFunctionFramePolicy | None,
    argument_expressions: tuple[Expression, ...],
) -> tuple[WindowValidationIssue, ...]:
    issues: list[WindowValidationIssue] = []
    structural_failures = _structural_frame_failures(resolved.frame)
    if structural_failures:
        issues.append(
            WindowValidationIssue(
                kind=WindowValidationIssueKind.STRUCTURALLY_INVALID_FRAME,
                structural_failure=StructurallyInvalidFrame(
                    resolved=resolved.frame,
                    failures=structural_failures,
                ),
            )
        )

    policy_matches = (
        function_policy is not None and function_policy.identity == function_identity
    )
    if function_policy is None:
        issues.append(
            WindowValidationIssue(
                kind=WindowValidationIssueKind.MISSING_FUNCTION_FRAME_POLICY,
            )
        )
    elif not policy_matches:
        issues.append(
            WindowValidationIssue(
                kind=(
                    WindowValidationIssueKind.FUNCTION_FRAME_POLICY_IDENTITY_MISMATCH
                ),
            )
        )
    else:
        if (
            resolved.frame.applicability
            is not function_policy.required_frame_applicability
        ):
            issues.append(
                WindowValidationIssue(
                    kind=WindowValidationIssueKind.FRAME_APPLICABILITY_MISMATCH,
                )
            )
        if (
            function_policy.kind
            is WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN
            and resolved.frame.authored.kind is not AuthoredWindowFrameKind.OMITTED
        ):
            issues.append(
                WindowValidationIssue(
                    kind=WindowValidationIssueKind.EXPLICIT_FRAME_FORBIDDEN,
                )
            )

    nested_expressions = _nested_window_expressions(
        resolved,
        argument_expressions,
    )
    if nested_expressions:
        issues.append(
            WindowValidationIssue(
                kind=WindowValidationIssueKind.NESTED_WINDOW_EXPRESSION,
                nested_expressions=nested_expressions,
            )
        )
    return tuple(issues)


def validate_resolved_window_specification(
    resolved: ResolvedWindowSpecification,
    *,
    function_identity: WindowFunctionIdentity,
    function_policy: WindowFunctionFramePolicy | None,
    argument_expressions: tuple[Expression, ...] = (),
) -> ValidatedWindowSpecification | WindowSpecificationValidationFailure:
    """Validate one complete resolved specification without target behavior."""

    _require_window_validation_inputs(
        resolved,
        function_identity,
        function_policy,
        argument_expressions,
    )
    issues = _window_validation_issues(
        resolved,
        function_identity,
        function_policy,
        argument_expressions,
    )
    if issues:
        return WindowSpecificationValidationFailure(
            resolved=resolved,
            function_identity=function_identity,
            function_policy=function_policy,
            argument_expressions=argument_expressions,
            issues=issues,
        )

    assert function_policy is not None
    frame: ValidatedFrame | ValidatedFrameNotApplicable
    if resolved.frame.applicability is WindowFrameApplicability.NOT_APPLICABLE:
        frame = ValidatedFrameNotApplicable(resolved=resolved.frame)
    else:
        frame = ValidatedFrame(
            resolved=resolved.frame,
            classification=_classify_valid_frame(resolved.frame),
        )
    return ValidatedWindowSpecification(
        resolved=resolved,
        function_identity=function_identity,
        function_policy=function_policy,
        argument_expressions=argument_expressions,
        frame=frame,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowOccurrenceIdentity:
    """Stable structural identity for one selected window occurrence."""

    source_id: str
    relation_name: str
    selected_output_ordinal: int
    span: Span

    def __post_init__(self) -> None:
        if type(self.source_id) is not str:
            raise TypeError("source_id must be an exact string")
        if not self.source_id.strip():
            raise ValueError("source_id must be nonblank")
        if type(self.relation_name) is not str:
            raise TypeError("relation_name must be an exact string")
        if not self.relation_name.strip():
            raise ValueError("relation_name must be nonblank")
        if type(self.selected_output_ordinal) is not int:
            raise TypeError("selected_output_ordinal must be an exact integer")
        if self.selected_output_ordinal < 0:
            raise ValueError("selected_output_ordinal must be nonnegative")
        if type(self.span) is not Span:
            raise TypeError("span must be an exact Span")
        if self.span.path is not None and self.span.path != self.source_id:
            raise ValueError("span path must equal source_id when present")


class WindowResultAvailabilityKind(StrEnum):
    """Private availability states for a future window result."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowResultAvailability:
    """A concrete known value type or one explicit unavailable state."""

    kind: WindowResultAvailabilityKind
    value_type: ValueType | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowResultAvailabilityKind:
            raise TypeError("kind must be an exact WindowResultAvailabilityKind")
        if self.value_type is not None and type(self.value_type) is not ValueType:
            raise TypeError("value_type must be an exact ValueType when present")
        if self.reason is not None and type(self.reason) is not str:
            raise TypeError("reason must be an exact string when present")

        if self.kind is WindowResultAvailabilityKind.CONCRETE:
            if self.value_type is None:
                raise ValueError("CONCRETE availability requires a value_type")
            if self.value_type.kind is not ValueTypeKind.KNOWN:
                raise ValueError("CONCRETE availability requires a known value type")
            if self.value_type.nullability not in {
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NULLABLE,
            }:
                raise ValueError(
                    "CONCRETE availability requires known effective nullability"
                )
            if self.reason is not None:
                raise ValueError("CONCRETE availability forbids a reason")
            return

        if self.value_type is not None:
            raise ValueError("non-concrete availability forbids a value_type")
        if self.reason is None or not self.reason.strip():
            raise ValueError("non-concrete availability requires a nonblank reason")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpressionSemanticFact:
    """Inert private semantic evidence for one parsed window expression."""

    occurrence: WindowOccurrenceIdentity
    expression: WindowExpr
    identity: WindowFunctionIdentity
    result: WindowResultAvailability
    stage: WindowExpressionStage = WindowExpressionStage.WINDOW

    def __post_init__(self) -> None:
        if type(self.occurrence) is not WindowOccurrenceIdentity:
            raise TypeError("occurrence must be an exact WindowOccurrenceIdentity")
        if type(self.expression) is not WindowExpr:
            raise TypeError("expression must be an exact WindowExpr")
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("identity must be an exact WindowFunctionIdentity")
        if type(self.result) is not WindowResultAvailability:
            raise TypeError("result must be an exact WindowResultAvailability")
        if type(self.stage) is not WindowExpressionStage:
            raise TypeError("stage must be an exact WindowExpressionStage")
        if self.expression.identity != self.identity:
            raise ValueError("expression identity must equal supplied identity")
        if self.expression.span != self.occurrence.span:
            raise ValueError("expression and occurrence spans must match")
        if self.stage is not WindowExpressionStage.WINDOW:
            raise ValueError("window semantic fact stage must be WINDOW")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpressionUnsupported:
    """Structurally valid private evidence whose semantics are unavailable."""

    occurrence: WindowOccurrenceIdentity
    expression: WindowExpr
    identity: WindowFunctionIdentity
    reason: str

    def __post_init__(self) -> None:
        if type(self.occurrence) is not WindowOccurrenceIdentity:
            raise TypeError("occurrence must be an exact WindowOccurrenceIdentity")
        if type(self.expression) is not WindowExpr:
            raise TypeError("expression must be an exact WindowExpr")
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("identity must be an exact WindowFunctionIdentity")
        if type(self.reason) is not str:
            raise TypeError("reason must be an exact string")
        if not self.reason.strip():
            raise ValueError("reason must be nonblank")
        if self.expression.identity != self.identity:
            raise ValueError("expression identity must equal supplied identity")
        if self.expression.span != self.occurrence.span:
            raise ValueError("expression and occurrence spans must match")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowPartitionFieldBinding:
    """One source-preserved direct partition field and its concrete type."""

    expression: NameExpr | DottedNameExpr
    value_type: ValueType

    def __post_init__(self) -> None:
        if type(self.expression) not in {NameExpr, DottedNameExpr}:
            raise TypeError("expression must be an exact NameExpr or DottedNameExpr")
        if type(self.expression) is DottedNameExpr and len(self.expression.parts) != 2:
            raise ValueError("qualified partition expression must have two parts")
        if type(self.value_type) is not ValueType:
            raise TypeError("value_type must be an exact ValueType")
        if (
            self.value_type.kind is not ValueTypeKind.KNOWN
            or self.value_type.resolved_type.kind is TypeKind.UNKNOWN
        ):
            raise ValueError("partition field value_type must be concrete")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowPartitionBindingFact:
    """Source-ordered semantic bindings for one window partition tuple."""

    semantic_fact: WindowExpressionSemanticFact
    bindings: tuple[WindowPartitionFieldBinding, ...]

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if type(self.bindings) is not tuple:
            raise TypeError("bindings must be an exact tuple")
        if any(type(item) is not WindowPartitionFieldBinding for item in self.bindings):
            raise TypeError(
                "bindings must contain exact WindowPartitionFieldBinding instances"
            )
        if self.partition_key != self.semantic_fact.expression.spec.partition_by:
            raise ValueError("partition bindings must equal the source partition tuple")

    @property
    def partition_key(self) -> tuple[Expression, ...]:
        """Return the complete source-ordered structural partition tuple."""

        return tuple(item.expression for item in self.bindings)


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowOrderFieldBinding:
    """One source-preserved direct order field and its effective direction."""

    order_item: OrderItem
    value_type: ValueType
    effective_direction: str

    def __post_init__(self) -> None:
        if type(self.order_item) is not OrderItem:
            raise TypeError("order_item must be an exact OrderItem")
        if type(self.order_item.expression) not in {NameExpr, DottedNameExpr}:
            raise TypeError(
                "order_item expression must be an exact NameExpr or DottedNameExpr"
            )
        if (
            type(self.order_item.expression) is DottedNameExpr
            and len(self.order_item.expression.parts) != 2
        ):
            raise ValueError("qualified order expression must have two parts")
        if type(self.value_type) is not ValueType:
            raise TypeError("value_type must be an exact ValueType")
        if (
            self.value_type.kind is not ValueTypeKind.KNOWN
            or self.value_type.resolved_type.kind is TypeKind.UNKNOWN
        ):
            raise ValueError("order field value_type must be concrete")

        source_direction = self.order_item.direction
        if source_direction is not None and type(source_direction) is not str:
            raise TypeError("source direction must be an exact string or None")
        if source_direction not in {None, "asc", "desc"}:
            raise ValueError("source direction must be omitted, asc, or desc")
        if type(self.effective_direction) is not str:
            raise TypeError("effective_direction must be an exact string")
        if self.effective_direction not in {"asc", "desc"}:
            raise ValueError("effective_direction must be asc or desc")
        expected_direction = "asc" if source_direction is None else source_direction
        if self.effective_direction != expected_direction:
            raise ValueError(
                "effective_direction must equal the normalized source direction"
            )

    @property
    def expression(self) -> NameExpr | DottedNameExpr:
        """Return the exact source-preserved direct field expression."""

        expression = self.order_item.expression
        if type(expression) is NameExpr:
            return expression
        if type(expression) is DottedNameExpr:
            return expression
        raise AssertionError("validated order expression must be a direct field")

    @property
    def source_direction(self) -> str | None:
        """Return omitted or explicit source direction without normalization."""

        return self.order_item.direction

    @property
    def direction_is_explicit(self) -> bool:
        """Whether the source spelled either supported direction."""

        return self.source_direction is not None


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowOrderBindingFact:
    """Source-ordered semantic bindings for one nonempty local-order tuple."""

    semantic_fact: WindowExpressionSemanticFact
    bindings: tuple[WindowOrderFieldBinding, ...]

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if type(self.bindings) is not tuple:
            raise TypeError("bindings must be an exact tuple")
        if not self.bindings:
            raise ValueError("order bindings must be nonempty")
        if any(type(item) is not WindowOrderFieldBinding for item in self.bindings):
            raise TypeError(
                "bindings must contain exact WindowOrderFieldBinding instances"
            )
        if self.order_items != self.semantic_fact.expression.spec.order_by:
            raise ValueError("order bindings must equal the source order tuple")

    @property
    def order_items(self) -> tuple[OrderItem, ...]:
        """Return every complete source order item in source order."""

        return tuple(item.order_item for item in self.bindings)

    @property
    def order_key(self) -> tuple[Expression, ...]:
        """Return every structural local-order expression in source order."""

        return tuple(item.expression for item in self.bindings)

    @property
    def effective_directions(self) -> tuple[str, ...]:
        """Return the normalized direction of every source order item."""

        return tuple(item.effective_direction for item in self.bindings)


class RankingAdvancePolicy(StrEnum):
    """Private structural advancement policies for ranking windows."""

    PER_ROW = "per_row"
    GAPPED_PEER_RANK = "preceding_row_count_plus_one"
    DENSE_PEER_RANK = "preceding_distinct_peer_group_count_plus_one"


@dataclass(frozen=True, slots=True, kw_only=True)
class RankingWindowSemanticFact:
    """Private sibling ranking policy for one core window semantic fact."""

    semantic_fact: WindowExpressionSemanticFact
    advance_policy: RankingAdvancePolicy

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if type(self.advance_policy) is not RankingAdvancePolicy:
            raise TypeError("advance_policy must be an exact RankingAdvancePolicy")
        if self.peer_sensitive and not self.peer_key:
            raise ValueError(
                "peer-sensitive ranking policy requires a nonempty structural "
                "order tuple"
            )

    @property
    def identity(self) -> WindowFunctionIdentity:
        """Return the exact source-preserved window identity."""

        return self.semantic_fact.identity

    @property
    def peer_sensitive(self) -> bool:
        """Whether advancement depends on equality of the local order key."""

        return self.advance_policy is not RankingAdvancePolicy.PER_ROW

    @property
    def peer_key(self) -> tuple[Expression, ...]:
        """Return the complete structural local order-expression tuple."""

        if not self.peer_sensitive:
            return ()
        return tuple(
            item.expression for item in self.semantic_fact.expression.spec.order_by
        )

    @property
    def gaps_after_multirow_peer_group(self) -> bool:
        """Whether a multirow peer group creates a subsequent rank gap."""

        return self.advance_policy is RankingAdvancePolicy.GAPPED_PEER_RANK


class DistributionWindowPolicy(StrEnum):
    """Private structural policies for distribution window functions."""

    PERCENT_RANK = "percent_rank"
    CUMULATIVE_DISTRIBUTION = "cumulative_distribution"
    BALANCED_BUCKETS = "balanced_buckets"


@dataclass(frozen=True, slots=True, kw_only=True)
class DistributionWindowSemanticFact:
    """Private sibling distribution policy for one core window semantic fact."""

    semantic_fact: WindowExpressionSemanticFact
    distribution_policy: DistributionWindowPolicy
    ranking_fact: RankingWindowSemanticFact | None
    bucket_count: int | None

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if type(self.distribution_policy) is not DistributionWindowPolicy:
            raise TypeError(
                "distribution_policy must be an exact DistributionWindowPolicy"
            )
        if (
            self.ranking_fact is not None
            and type(self.ranking_fact) is not RankingWindowSemanticFact
        ):
            raise TypeError(
                "ranking_fact must be an exact RankingWindowSemanticFact or None"
            )
        if self.bucket_count is not None and type(self.bucket_count) is not int:
            raise TypeError("bucket_count must be an exact integer or None")
        if not self.structural_order_key:
            raise ValueError(
                "distribution policy requires a nonempty structural order tuple"
            )

        identity_name = self.semantic_fact.identity.name
        if self.distribution_policy is DistributionWindowPolicy.PERCENT_RANK:
            if identity_name != "percent_rank":
                raise ValueError("PERCENT_RANK requires percent_rank identity")
            if self.ranking_fact is None:
                raise ValueError("PERCENT_RANK requires a ranking_fact")
            if self.ranking_fact.semantic_fact is not self.semantic_fact:
                raise ValueError("PERCENT_RANK requires the same semantic core")
            if (
                self.ranking_fact.advance_policy
                is not RankingAdvancePolicy.GAPPED_PEER_RANK
            ):
                raise ValueError("PERCENT_RANK requires GAPPED_PEER_RANK")
            if self.bucket_count is not None:
                raise ValueError("PERCENT_RANK forbids bucket_count")
            return

        if self.distribution_policy is (
            DistributionWindowPolicy.CUMULATIVE_DISTRIBUTION
        ):
            if identity_name != "cume_dist":
                raise ValueError("CUMULATIVE_DISTRIBUTION requires cume_dist identity")
            if self.ranking_fact is not None:
                raise ValueError("CUMULATIVE_DISTRIBUTION forbids ranking_fact")
            if self.bucket_count is not None:
                raise ValueError("CUMULATIVE_DISTRIBUTION forbids bucket_count")
            return

        if identity_name != "ntile":
            raise ValueError("BALANCED_BUCKETS requires ntile identity")
        if self.ranking_fact is not None:
            raise ValueError("BALANCED_BUCKETS forbids ranking_fact")
        if self.bucket_count is None or self.bucket_count <= 0:
            raise ValueError("BALANCED_BUCKETS requires positive bucket_count")

    @property
    def identity(self) -> WindowFunctionIdentity:
        """Return the exact source-preserved window identity."""

        return self.semantic_fact.identity

    @property
    def structural_order_key(self) -> tuple[Expression, ...]:
        """Return the complete structural local order-expression tuple."""

        return tuple(
            item.expression for item in self.semantic_fact.expression.spec.order_by
        )

    @property
    def peer_sensitive(self) -> bool:
        """Whether the distribution result depends on the complete peer key."""

        return self.distribution_policy is not DistributionWindowPolicy.BALANCED_BUCKETS

    @property
    def peer_key(self) -> tuple[Expression, ...]:
        """Return the peer key for peer-sensitive distribution functions."""

        if not self.peer_sensitive:
            return ()
        return self.structural_order_key


class NavigationDirection(StrEnum):
    """Private source directions for offset-based navigation windows."""

    LAG = "lag"
    LEAD = "lead"


@dataclass(frozen=True, slots=True, kw_only=True)
class NavigationOffsetFact:
    """One omitted or explicit nonnegative navigation offset."""

    expression: LiteralExpr | None
    effective_value: int
    span: Span

    def __post_init__(self) -> None:
        if self.expression is not None and type(self.expression) is not LiteralExpr:
            raise TypeError("expression must be an exact LiteralExpr or None")
        if type(self.effective_value) is not int:
            raise TypeError("effective_value must be an exact integer")
        if self.effective_value < 0:
            raise ValueError("effective_value must be nonnegative")
        if type(self.span) is not Span:
            raise TypeError("span must be an exact Span")
        if self.expression is None:
            if self.effective_value != 1:
                raise ValueError(
                    "omitted navigation offset must have effective value 1"
                )
            return
        if (
            type(self.expression.value) is not int
            or self.expression.value < 0
            or self.expression.value != self.effective_value
        ):
            raise ValueError(
                "explicit navigation offset must be its nonnegative integer literal"
            )
        if self.span != self.expression.span:
            raise ValueError(
                "explicit navigation offset span must match its expression"
            )

    @property
    def omitted(self) -> bool:
        """Whether the source omitted the offset argument."""

        return self.expression is None


@dataclass(frozen=True, slots=True, kw_only=True)
class NavigationDefaultFact:
    """One omitted or bounded navigation default expression and its type."""

    expression: NameExpr | DottedNameExpr | LiteralExpr | None
    value_type: ValueType | None
    always_null: bool
    span: Span

    def __post_init__(self) -> None:
        if self.expression is not None and type(self.expression) not in {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
        }:
            raise TypeError(
                "expression must be an exact direct field, LiteralExpr, or None"
            )
        if type(self.expression) is DottedNameExpr and len(self.expression.parts) != 2:
            raise ValueError("qualified default expression must have two parts")
        if self.value_type is not None and type(self.value_type) is not ValueType:
            raise TypeError("value_type must be an exact ValueType or None")
        if type(self.always_null) is not bool:
            raise TypeError("always_null must be an exact bool")
        if type(self.span) is not Span:
            raise TypeError("span must be an exact Span")

        if self.expression is None:
            if self.value_type is not None or self.always_null:
                raise ValueError("omitted default forbids value type and NULL evidence")
            return

        if self.value_type is None:
            raise ValueError("supplied default requires a value type")
        if self.span != self.expression.span:
            raise ValueError("supplied default span must match its expression")
        expression_is_null = (
            type(self.expression) is LiteralExpr and self.expression.value is None
        )
        if self.always_null is not expression_is_null:
            raise ValueError("always_null must match an exact NULL literal")
        if self.always_null:
            if self.value_type.kind is not ValueTypeKind.UNKNOWN:
                raise ValueError("NULL default must retain an unknown value type")
            return
        if (
            self.value_type.kind is not ValueTypeKind.KNOWN
            or self.value_type.resolved_type.kind
            not in {TypeKind.BUILTIN, TypeKind.ENUM, TypeKind.SHAPE}
            or self.value_type.nullability
            not in {
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NULLABLE,
            }
        ):
            raise ValueError("non-NULL default value type must be concrete")

    @property
    def omitted(self) -> bool:
        """Whether the source omitted the default argument."""

        return self.expression is None


@dataclass(frozen=True, slots=True, kw_only=True)
class NavigationWindowSemanticFact:
    """Private sibling navigation evidence for one core window semantic fact."""

    semantic_fact: WindowExpressionSemanticFact
    direction: NavigationDirection
    value_expression: NameExpr | DottedNameExpr | LiteralExpr
    value_type: ValueType
    value_always_null: bool
    offset_fact: NavigationOffsetFact
    default_fact: NavigationDefaultFact
    signature_match: SignatureMatch
    nullability_match: NullabilityEvaluationMatch

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if type(self.direction) is not NavigationDirection:
            raise TypeError("direction must be an exact NavigationDirection")
        if type(self.value_expression) not in {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
        }:
            raise TypeError("value_expression must be an exact bounded expression")
        if (
            type(self.value_expression) is DottedNameExpr
            and len(self.value_expression.parts) != 2
        ):
            raise ValueError("qualified value expression must have two parts")
        if type(self.value_type) is not ValueType:
            raise TypeError("value_type must be an exact ValueType")
        if type(self.value_always_null) is not bool:
            raise TypeError("value_always_null must be an exact bool")
        if type(self.offset_fact) is not NavigationOffsetFact:
            raise TypeError("offset_fact must be an exact NavigationOffsetFact")
        if type(self.default_fact) is not NavigationDefaultFact:
            raise TypeError("default_fact must be an exact NavigationDefaultFact")
        if type(self.signature_match) is not SignatureMatch:
            raise TypeError("signature_match must be an exact SignatureMatch")
        if type(self.nullability_match) is not NullabilityEvaluationMatch:
            raise TypeError(
                "nullability_match must be an exact NullabilityEvaluationMatch"
            )

        expression = self.semantic_fact.expression
        if self.semantic_fact.identity.name != self.direction.value:
            raise ValueError("navigation direction must equal the window identity")
        if not expression.spec.order_by:
            raise ValueError("navigation fact requires nonempty local order")
        arguments = expression.call.arguments
        if len(arguments) not in {1, 2, 3}:
            raise ValueError("navigation fact requires one through three arguments")
        if self.value_expression != arguments[0]:
            raise ValueError("value_expression must equal argument zero")
        expression_is_null = (
            type(self.value_expression) is LiteralExpr
            and self.value_expression.value is None
        )
        if self.value_always_null is not expression_is_null:
            raise ValueError("value_always_null must match an exact NULL literal")
        if self.value_always_null:
            if self.value_type.kind is not ValueTypeKind.UNKNOWN:
                raise ValueError("NULL value must retain an unknown value type")
        elif (
            self.value_type.kind is not ValueTypeKind.KNOWN
            or self.value_type.resolved_type.kind
            not in {TypeKind.BUILTIN, TypeKind.ENUM, TypeKind.SHAPE}
            or self.value_type.nullability
            not in {
                EffectiveNullability.NON_NULL,
                EffectiveNullability.NULLABLE,
            }
        ):
            raise ValueError("non-NULL navigation value type must be concrete")

        if len(arguments) == 1:
            if not self.offset_fact.omitted or not self.default_fact.omitted:
                raise ValueError("one-argument navigation must omit offset and default")
        else:
            if self.offset_fact.expression != arguments[1]:
                raise ValueError("offset fact must retain argument one")
            if len(arguments) == 2 and not self.default_fact.omitted:
                raise ValueError("two-argument navigation must omit default")
            if len(arguments) == 3 and self.default_fact.expression != arguments[2]:
                raise ValueError("default fact must retain argument two")

        expected_omitted = tuple(range(len(arguments), 3))
        if self.signature_match.omitted_positions != expected_omitted:
            raise ValueError("signature omission evidence must match source arity")
        result = self.semantic_fact.result
        if (
            result.kind is not WindowResultAvailabilityKind.CONCRETE
            or result.value_type is None
        ):
            raise ValueError("navigation semantic result must be concrete")
        if (
            result.value_type.resolved_type.name
            != self.signature_match.result_type.name
            or result.value_type.resolved_type.kind
            is not self.signature_match.result_type.kind
        ):
            raise ValueError("navigation result type must equal signature result")
        if result.value_type.nullability is not self.nullability_match.value:
            raise ValueError("navigation result nullability must equal formula result")

    @property
    def identity(self) -> WindowFunctionIdentity:
        """Return the exact source-preserved navigation identity."""

        return self.semantic_fact.identity

    @property
    def structural_order_key(self) -> tuple[Expression, ...]:
        """Return the complete structural local order-expression tuple."""

        return tuple(
            item.expression for item in self.semantic_fact.expression.spec.order_by
        )

    @property
    def peer_sensitive(self) -> bool:
        """Navigation offsets never derive peer-sensitive semantics."""

        return False

    @property
    def peer_key(self) -> tuple[Expression, ...]:
        """Return no peer key for peer-insensitive navigation."""

        return ()


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpressionAnalysis:
    """One core fact joined to its family and partition sibling evidence."""

    semantic_fact: WindowExpressionSemanticFact
    ranking_fact: RankingWindowSemanticFact | None
    distribution_fact: DistributionWindowSemanticFact | None
    partition_binding_fact: WindowPartitionBindingFact
    order_binding_fact: WindowOrderBindingFact
    navigation_fact: NavigationWindowSemanticFact | None = None

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError(
                "semantic_fact must be an exact WindowExpressionSemanticFact"
            )
        if (
            self.ranking_fact is not None
            and type(self.ranking_fact) is not RankingWindowSemanticFact
        ):
            raise TypeError(
                "ranking_fact must be an exact RankingWindowSemanticFact or None"
            )
        if (
            self.distribution_fact is not None
            and type(self.distribution_fact) is not DistributionWindowSemanticFact
        ):
            raise TypeError(
                "distribution_fact must be an exact "
                "DistributionWindowSemanticFact or None"
            )
        if type(self.partition_binding_fact) is not WindowPartitionBindingFact:
            raise TypeError(
                "partition_binding_fact must be an exact WindowPartitionBindingFact"
            )
        if self.partition_binding_fact.semantic_fact is not self.semantic_fact:
            raise ValueError("partition fact must share the semantic core")
        if type(self.order_binding_fact) is not WindowOrderBindingFact:
            raise TypeError(
                "order_binding_fact must be an exact WindowOrderBindingFact"
            )
        if self.order_binding_fact.semantic_fact is not self.semantic_fact:
            raise ValueError("order fact must share the semantic core")
        if (
            self.ranking_fact is not None
            and self.ranking_fact.semantic_fact is not self.semantic_fact
        ):
            raise ValueError("ranking fact must share the semantic core")
        if (
            self.distribution_fact is not None
            and self.distribution_fact.semantic_fact is not self.semantic_fact
        ):
            raise ValueError("distribution fact must share the semantic core")
        if (
            self.navigation_fact is not None
            and type(self.navigation_fact) is not NavigationWindowSemanticFact
        ):
            raise TypeError(
                "navigation_fact must be an exact NavigationWindowSemanticFact or None"
            )
        if (
            self.navigation_fact is not None
            and self.navigation_fact.semantic_fact is not self.semantic_fact
        ):
            raise ValueError("navigation fact must share the semantic core")
        if (
            self.ranking_fact is None
            and self.distribution_fact is None
            and self.navigation_fact is None
        ):
            raise ValueError("window analysis requires a family fact")

        identity_name = self.semantic_fact.identity.name
        if identity_name in {"row_number", "rank", "dense_rank"}:
            if (
                self.ranking_fact is None
                or self.distribution_fact is not None
                or self.navigation_fact is not None
            ):
                raise ValueError("ranking identity requires only a ranking fact")
            return
        if identity_name == "percent_rank":
            if (
                self.ranking_fact is None
                or self.distribution_fact is None
                or self.navigation_fact is not None
            ):
                raise ValueError("percent_rank requires both family facts")
            if self.distribution_fact.ranking_fact is not self.ranking_fact:
                raise ValueError(
                    "percent_rank distribution must reference the ranking fact"
                )
            return
        if identity_name in {"cume_dist", "ntile"}:
            if (
                self.ranking_fact is not None
                or self.distribution_fact is None
                or self.navigation_fact is not None
            ):
                raise ValueError(
                    "non-ranking distribution identity requires only a "
                    "distribution fact"
                )
            return
        if identity_name in {"lag", "lead"}:
            if (
                self.ranking_fact is not None
                or self.distribution_fact is not None
                or self.navigation_fact is None
            ):
                raise ValueError("navigation identity requires only a navigation fact")
            return
        raise ValueError("window analysis identity must be one completed identity")
