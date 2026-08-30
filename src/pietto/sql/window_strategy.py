"""Private exact target decisions for named and inline window lowering."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import StrEnum

from pietto.ir.model import (
    LiteralIR,
    NamedWindowDeclarationIR,
    NamedWindowOccurrenceIR,
    RelationIR,
    WindowCallIR,
    WindowFrameBoundKindIR,
    WindowFrameExclusionIR,
    WindowFrameUnitIR,
    WindowNthDirectionIR,
    WindowNullTreatmentIR,
)
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityFact,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.capability_lookup import Found, lookup_capability
from pietto.semantic.capability_windows import (
    _lowering_operands,
    window_lookup_inputs,
)

__all__: tuple[str, ...] = ()


class WindowTargetDialect(StrEnum):
    POSTGRESQL = "postgresql"
    MYSQL = "mysql"


class NamedWindowLoweringStrategy(StrEnum):
    NATIVE_PRESERVE = "native_preserve"
    NATIVE_REORDER = "native_reorder"
    INLINE_EXACT = "inline_exact"
    NOT_LOWERABLE = "not_lowerable"


class WindowTargetEvidenceKind(StrEnum):
    INLINE_CAPABILITY = "inline_capability"
    FRAME_SHAPE = "frame_shape"
    EXCLUSION = "exclusion"
    NULL_TREATMENT = "null_treatment"
    NTH_DIRECTION = "nth_direction"
    USE_KIND = "use_kind"
    DECLARATION_GRAPH = "declaration_graph"
    FORWARD_REFERENCE = "forward_reference"
    FRAMED_BASE = "framed_base"
    EFFECTIVE_DEFAULT = "effective_default"


class WindowTargetEvidenceOutcome(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True, slots=True)
class WindowTargetEvidence:
    kind: WindowTargetEvidenceKind
    outcome: WindowTargetEvidenceOutcome
    detail: str
    occurrence_ordinal: int | None = None
    capability_fact: CapabilityFact | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowTargetEvidenceKind:
            raise TypeError("window target evidence kind must be exact")
        if type(self.outcome) is not WindowTargetEvidenceOutcome:
            raise TypeError("window target evidence outcome must be exact")
        if type(self.detail) is not str or not self.detail:
            raise ValueError("window target evidence detail must be nonempty")
        if self.occurrence_ordinal is not None and (
            type(self.occurrence_ordinal) is not int or self.occurrence_ordinal < 0
        ):
            raise ValueError("window target evidence ordinal must be nonnegative")
        if self.capability_fact is not None and (
            type(self.capability_fact) is not CapabilityFact
        ):
            raise TypeError("window target capability fact must be exact or absent")
        if self.kind is WindowTargetEvidenceKind.INLINE_CAPABILITY:
            if (
                self.outcome is WindowTargetEvidenceOutcome.SUPPORTED
                and self.capability_fact is None
            ):
                raise ValueError("supported inline evidence must retain its exact fact")
        elif self.capability_fact is not None:
            raise ValueError("non-capability evidence forbids a capability fact")


@dataclass(frozen=True, slots=True)
class InlineWindowTargetDecision:
    dialect: WindowTargetDialect
    call: WindowCallIR
    evidence: tuple[WindowTargetEvidence, ...]

    def __post_init__(self) -> None:
        if type(self.dialect) is not WindowTargetDialect:
            raise TypeError("inline window decision dialect must be exact")
        if type(self.call) is not WindowCallIR:
            raise TypeError("inline window decision call must be exact")
        if type(self.evidence) is not tuple or any(
            type(item) is not WindowTargetEvidence for item in self.evidence
        ):
            raise TypeError("inline window decision evidence must be exact")
        if not self.evidence or self.evidence[0].kind is not (
            WindowTargetEvidenceKind.INLINE_CAPABILITY
        ):
            raise ValueError(
                "inline window decision requires capability evidence first"
            )

    @property
    def supported(self) -> bool:
        return all(
            item.outcome is WindowTargetEvidenceOutcome.SUPPORTED
            for item in self.evidence
        )

    @property
    def failure_reason(self) -> str | None:
        return next(
            (
                item.detail
                for item in self.evidence
                if item.outcome is WindowTargetEvidenceOutcome.UNSUPPORTED
            ),
            None,
        )


@dataclass(frozen=True, slots=True)
class NamedWindowLoweringDecision:
    relation: RelationIR
    dialect: WindowTargetDialect
    strategy: NamedWindowLoweringStrategy
    reachable_declarations: tuple[NamedWindowDeclarationIR, ...]
    emission_declarations: tuple[NamedWindowDeclarationIR, ...]
    inline_decisions: tuple[InlineWindowTargetDecision, ...]
    evidence: tuple[WindowTargetEvidence, ...]
    reason: str | None = None

    def __post_init__(self) -> None:
        if type(self.relation) is not RelationIR:
            raise TypeError("named window decision relation must be exact")
        if type(self.dialect) is not WindowTargetDialect:
            raise TypeError("named window decision dialect must be exact")
        if type(self.strategy) is not NamedWindowLoweringStrategy:
            raise TypeError("named window decision strategy must be exact")
        for values in (
            self.reachable_declarations,
            self.emission_declarations,
        ):
            if type(values) is not tuple or any(
                type(item) is not NamedWindowDeclarationIR for item in values
            ):
                raise TypeError("named window decision declarations must be exact")
        if type(self.inline_decisions) is not tuple or any(
            type(item) is not InlineWindowTargetDecision
            for item in self.inline_decisions
        ):
            raise TypeError("named window inline decisions must be exact")
        if type(self.evidence) is not tuple or any(
            type(item) is not WindowTargetEvidence for item in self.evidence
        ):
            raise TypeError("named window decision evidence must be exact")
        if self.strategy is NamedWindowLoweringStrategy.NOT_LOWERABLE:
            if self.reason is None or not self.reason:
                raise ValueError("not-lowerable decisions require a reason")
            if self.emission_declarations:
                raise ValueError("not-lowerable decisions forbid emission declarations")
        elif self.reason is not None:
            raise ValueError("lowerable named window decisions forbid a reason")
        if self.strategy is NamedWindowLoweringStrategy.INLINE_EXACT:
            if self.emission_declarations:
                raise ValueError("inline decisions forbid native declarations")
        elif self.strategy is NamedWindowLoweringStrategy.NATIVE_PRESERVE:
            if self.emission_declarations != self.reachable_declarations:
                raise ValueError("native preserve decisions require source order")
        elif self.strategy is NamedWindowLoweringStrategy.NATIVE_REORDER and (
            self.emission_declarations
            != _stable_topological_order(self.reachable_declarations)
        ):
            raise ValueError("native reorder decisions require stable topology")


def decide_inline_window_target(
    call: WindowCallIR,
    dialect: WindowTargetDialect,
) -> InlineWindowTargetDecision:
    """Decide one exact effective call from capability facts and typed shape laws."""

    if type(call) is not WindowCallIR:
        raise TypeError("inline window target decision requires an exact call")
    if type(dialect) is not WindowTargetDialect:
        raise TypeError("inline window target dialect must be exact")
    key = CapabilityKey(
        CapabilityDomain.WINDOW_FUNCTION,
        subject=call.identity.name,
        operation="lowering",
        operands=_lowering_operands(call.identity.name, dialect.value),
        context="window_lowering",
        dialect=dialect.value,
    )
    facts, complete, unknown_reason = window_lookup_inputs(key)
    lookup = lookup_capability(
        key,
        facts,
        domain_complete=complete,
        unknown_reason=unknown_reason,
    )
    capability_fact = lookup.fact if type(lookup) is Found else None
    capability_supported = (
        capability_fact is not None
        and capability_fact.support is CapabilitySupport.SUPPORTED
    )
    evidence = [
        WindowTargetEvidence(
            WindowTargetEvidenceKind.INLINE_CAPABILITY,
            (
                WindowTargetEvidenceOutcome.SUPPORTED
                if capability_supported
                else WindowTargetEvidenceOutcome.UNSUPPORTED
            ),
            (
                "exact inline lowering capability"
                if capability_supported
                else "missing exact inline lowering capability"
            ),
            capability_fact=capability_fact,
        )
    ]
    frame_supported, frame_detail = _frame_is_supported(call, dialect)
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.FRAME_SHAPE,
            frame_supported,
            frame_detail,
        )
    )
    exclusion_supported, exclusion_detail = _exclusion_is_supported(call, dialect)
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.EXCLUSION,
            exclusion_supported,
            exclusion_detail,
        )
    )
    null_supported = call.null_treatment is not WindowNullTreatmentIR.IGNORE_NULLS
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.NULL_TREATMENT,
            null_supported,
            (
                "effective NULL treatment is target-equivalent"
                if null_supported
                else (
                    "PostgreSQL does not support IGNORE NULLS"
                    if dialect is WindowTargetDialect.POSTGRESQL
                    else "MySQL does not execute IGNORE NULLS"
                )
            ),
        )
    )
    direction_supported = call.nth_direction is not WindowNthDirectionIR.FROM_LAST
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.NTH_DIRECTION,
            direction_supported,
            (
                "effective nth direction is target-equivalent"
                if direction_supported
                else (
                    "PostgreSQL does not support FROM LAST"
                    if dialect is WindowTargetDialect.POSTGRESQL
                    else "MySQL does not execute FROM LAST"
                )
            ),
        )
    )
    return InlineWindowTargetDecision(dialect, call, tuple(evidence))


def decide_named_window_lowering(
    relation: RelationIR,
    dialect: WindowTargetDialect,
) -> NamedWindowLoweringDecision | None:
    """Choose exactly one relation-level named strategy with complete evidence."""

    if type(relation) is not RelationIR:
        raise TypeError("named window strategy requires an exact relation")
    if type(dialect) is not WindowTargetDialect:
        raise TypeError("named window strategy dialect must be exact")
    calls = tuple(
        expression
        for projection in relation.projections
        if isinstance((expression := projection.expression), WindowCallIR)
        and getattr(expression, "named_use", None) is not None
    )
    if not calls:
        return None
    reachable = _reachable_declarations(relation, calls)
    inline_decisions = tuple(
        decide_inline_window_target(call, dialect) for call in calls
    )
    evidence: list[WindowTargetEvidence] = [
        WindowTargetEvidence(
            WindowTargetEvidenceKind.USE_KIND,
            WindowTargetEvidenceOutcome.SUPPORTED,
            call.named_use.occurrence.kind.value,
            occurrence_ordinal=call.named_use.occurrence.selected_output_ordinal,
        )
        for call in calls
        if call.named_use is not None
    ]
    graph_supported, graph_detail = _native_graph_is_supported(reachable, dialect)
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.DECLARATION_GRAPH,
            graph_supported,
            graph_detail,
        )
    )
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.FORWARD_REFERENCE,
            True,
            (
                "mysql preserves source-order forward and backward references"
                if dialect is WindowTargetDialect.MYSQL
                else "postgresql uses stable base-first ordering"
            ),
        )
    )
    framed_base_supported, framed_base_detail = _framed_bases_are_supported(
        reachable,
        dialect,
    )
    evidence.append(
        _shape_evidence(
            WindowTargetEvidenceKind.FRAMED_BASE,
            framed_base_supported,
            framed_base_detail,
        )
    )
    for call in calls:
        frame = call.spec.frame
        evidence.append(
            _shape_evidence(
                WindowTargetEvidenceKind.EFFECTIVE_DEFAULT,
                True,
                (
                    "no effective frame extension required"
                    if frame is None or frame.frame_is_explicit
                    else "emit exact use-local effective default frame"
                ),
                occurrence_ordinal=(
                    None
                    if call.named_use is None
                    else call.named_use.occurrence.selected_output_ordinal
                ),
            )
        )

    inline_supported = all(item.supported for item in inline_decisions)
    native_supported = graph_supported and framed_base_supported and inline_supported
    if native_supported and dialect is WindowTargetDialect.MYSQL:
        strategy = NamedWindowLoweringStrategy.NATIVE_PRESERVE
        emission = reachable
    elif native_supported:
        strategy = NamedWindowLoweringStrategy.NATIVE_REORDER
        emission = _stable_topological_order(reachable)
    elif inline_supported:
        strategy = NamedWindowLoweringStrategy.INLINE_EXACT
        emission = ()
    else:
        strategy = NamedWindowLoweringStrategy.NOT_LOWERABLE
        emission = ()
    reason = None
    if strategy is NamedWindowLoweringStrategy.NOT_LOWERABLE:
        reason = next(
            item.failure_reason for item in inline_decisions if not item.supported
        )
        assert reason is not None
    return NamedWindowLoweringDecision(
        relation,
        dialect,
        strategy,
        reachable,
        emission,
        inline_decisions,
        tuple(evidence),
        reason,
    )


def window_runtime_semantically_equal(
    left: WindowCallIR,
    right: WindowCallIR,
) -> bool:
    """Compare runtime semantics while excluding authorship and provenance."""

    if type(left) is not WindowCallIR or type(right) is not WindowCallIR:
        raise TypeError("window semantic equivalence requires exact calls")
    return _runtime_semantic_value(left) == _runtime_semantic_value(right)


def _shape_evidence(
    kind: WindowTargetEvidenceKind,
    supported: bool,
    detail: str,
    *,
    occurrence_ordinal: int | None = None,
) -> WindowTargetEvidence:
    return WindowTargetEvidence(
        kind,
        (
            WindowTargetEvidenceOutcome.SUPPORTED
            if supported
            else WindowTargetEvidenceOutcome.UNSUPPORTED
        ),
        detail,
        occurrence_ordinal,
    )


def _offset_bounds(call: WindowCallIR):
    frame = call.spec.frame
    if frame is None:
        return ()
    return tuple(
        bound
        for bound in (frame.start, frame.end)
        if bound.kind
        in {
            WindowFrameBoundKindIR.OFFSET_PRECEDING,
            WindowFrameBoundKindIR.OFFSET_FOLLOWING,
        }
    )


def _frame_is_supported(
    call: WindowCallIR,
    dialect: WindowTargetDialect,
) -> tuple[bool, str]:
    frame = call.spec.frame
    if frame is None:
        return True, "function has no applicable frame"
    offsets = _offset_bounds(call)
    target_name = "PostgreSQL" if dialect is WindowTargetDialect.POSTGRESQL else "MySQL"
    if frame.unit is WindowFrameUnitIR.RANGE and offsets:
        return False, f"{target_name} RANGE offsets require Phase 64 evidence"
    if dialect is WindowTargetDialect.MYSQL and frame.unit is WindowFrameUnitIR.GROUPS:
        return False, "MySQL does not support GROUPS frames"
    if any(
        type(bound.offset) is not LiteralIR
        or type(bound.offset.value) is not int
        or bound.offset.value < 0
        for bound in offsets
    ):
        return False, f"{target_name} frame offsets require nonnegative Int literals"
    return True, "effective frame shape is target-representable"


def _exclusion_is_supported(
    call: WindowCallIR,
    dialect: WindowTargetDialect,
) -> tuple[bool, str]:
    frame = call.spec.frame
    if frame is None or dialect is WindowTargetDialect.POSTGRESQL:
        return True, "effective exclusion is target-representable"
    supported = (
        frame.exclusion is WindowFrameExclusionIR.NO_OTHERS
        and not frame.exclusion_is_explicit
    )
    return (
        supported,
        (
            "mysql fixed NO OTHERS behavior is exact"
            if supported
            else "MySQL does not support authored EXCLUDE frames"
        ),
    )


def _reachable_declarations(
    relation: RelationIR,
    calls: tuple[WindowCallIR, ...],
) -> tuple[NamedWindowDeclarationIR, ...]:
    by_occurrence = {item.occurrence: item for item in relation.named_windows}
    reachable: set[NamedWindowOccurrenceIR] = set()
    pending = [call.named_use.target for call in calls if call.named_use is not None]
    while pending:
        occurrence = pending.pop()
        if occurrence in reachable:
            continue
        declaration = by_occurrence.get(occurrence)
        if declaration is None:
            raise ValueError("named use target is absent from relation IR")
        reachable.add(occurrence)
        if declaration.base is not None:
            pending.append(declaration.base.target)
    return tuple(
        item for item in relation.named_windows if item.occurrence in reachable
    )


def _native_graph_is_supported(
    declarations: tuple[NamedWindowDeclarationIR, ...],
    dialect: WindowTargetDialect,
) -> tuple[bool, str]:
    occurrences = {item.occurrence for item in declarations}
    if any(
        item.base is not None and item.base.target not in occurrences
        for item in declarations
    ):
        return False, "reachable named declaration closure is incomplete"
    return (
        True,
        (
            "source-order declaration graph is mysql-representable"
            if dialect is WindowTargetDialect.MYSQL
            else "declaration graph has a stable postgresql topological order"
        ),
    )


def _framed_bases_are_supported(
    declarations: tuple[NamedWindowDeclarationIR, ...],
    dialect: WindowTargetDialect,
) -> tuple[bool, str]:
    if dialect is WindowTargetDialect.MYSQL:
        return True, "mysql native inheritance admits the resolved graph"
    by_occurrence = {item.occurrence: item for item in declarations}

    def carries_frame(declaration: NamedWindowDeclarationIR) -> bool:
        if declaration.local_spec.frame is not None:
            return True
        if declaration.base is None:
            return False
        return carries_frame(by_occurrence[declaration.base.target])

    blocked = tuple(
        item
        for item in declarations
        if item.base is not None and carries_frame(by_occurrence[item.base.target])
    )
    return (
        not blocked,
        (
            "postgresql copied bases are frame-free"
            if not blocked
            else "postgresql cannot copy a named base carrying a frame"
        ),
    )


def _stable_topological_order(
    declarations: tuple[NamedWindowDeclarationIR, ...],
) -> tuple[NamedWindowDeclarationIR, ...]:
    pending = list(declarations)
    emitted: list[NamedWindowDeclarationIR] = []
    emitted_occurrences: set[NamedWindowOccurrenceIR] = set()
    while pending:
        ready = next(
            (
                item
                for item in pending
                if item.base is None or item.base.target in emitted_occurrences
            ),
            None,
        )
        if ready is None:
            raise ValueError("named declaration graph has no topological order")
        pending.remove(ready)
        emitted.append(ready)
        emitted_occurrences.add(ready.occurrence)
    return tuple(emitted)


_RUNTIME_PROVENANCE_FIELDS = {
    "span",
    "named_use",
    "direction_is_explicit",
    "frame_is_explicit",
    "end_is_explicit",
    "exclusion_is_explicit",
    "null_treatment_is_explicit",
    "nth_direction_is_explicit",
}


def _runtime_semantic_value(value: object) -> object:
    if isinstance(value, StrEnum):
        return (type(value).__name__, value.value)
    if type(value) is tuple:
        return tuple(_runtime_semantic_value(item) for item in value)
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (item.name, _runtime_semantic_value(getattr(value, item.name)))
                for item in fields(value)
                if item.name not in _RUNTIME_PROVENANCE_FIELDS
            ),
        )
    return value
