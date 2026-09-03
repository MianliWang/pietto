"""Private semantic carriers for structurally identified window expressions."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field, replace
from enum import StrEnum
from heapq import heappop, heappush
from itertools import chain

from pietto._window_identity import WindowFunctionIdentity, WindowFunctionRole
from pietto.ast_nodes import (
    AuthoredWindowNthDirection,
    AuthoredWindowNullTreatment,
    AuthoredWindowFrame,
    AuthoredWindowFrameExclusion,
    AuthoredWindowFrameKind,
    DottedNameExpr,
    Expression,
    LiteralExpr,
    NameExpr,
    NamedWindowDeclaration,
    NamedWindowReference,
    OrderItem,
    QueryDef,
    Span,
    TableDef,
    WindowExpr,
    WindowFrameBound,
    WindowFrameBoundKind,
    WindowFrameUnit,
    WindowNthDirectionKind,
    WindowNullTreatmentKind,
    WindowSpec,
    WindowUseKind,
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


class WindowFrameExclusion(StrEnum):
    """Concrete effective frame-exclusion semantics."""

    NO_OTHERS = "no_others"
    CURRENT_ROW = "current_row"
    GROUP = "group"
    TIES = "ties"


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


class QueryBlockKind(StrEnum):
    """Existing relation-body kinds that independently own named windows."""

    TABLE = "table"
    QUERY = "query"


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryBlockOccurrence:
    """One exact top-level relation body, independent of its display name."""

    source_id: str
    relation_name: str
    kind: QueryBlockKind
    span: Span

    def __post_init__(self) -> None:
        if type(self.source_id) is not str or not self.source_id:
            raise ValueError("query-block source identity must be nonempty text")
        if type(self.relation_name) is not str or not self.relation_name:
            raise ValueError("query-block relation name must be nonempty text")
        if type(self.kind) is not QueryBlockKind:
            raise TypeError("query-block kind must be exact")
        if type(self.span) is not Span:
            raise TypeError("query-block span must be exact")
        if self.source_id != (self.span.path or self.relation_name):
            raise ValueError(
                "query-block source identity must match its span path or relation name"
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowOccurrence:
    """One declaration occurrence scoped by its exact owning query block."""

    query_block: QueryBlockOccurrence
    declaration_position: int
    span: Span

    def __post_init__(self) -> None:
        if type(self.query_block) is not QueryBlockOccurrence:
            raise TypeError("named-window query block must be exact")
        if type(self.declaration_position) is not int:
            raise TypeError("named-window declaration position must be exact")
        if self.declaration_position < 0:
            raise ValueError("named-window declaration position must be nonnegative")
        if type(self.span) is not Span:
            raise TypeError("named-window declaration span must be exact")
        if self.span.path != self.query_block.span.path:
            raise ValueError("named-window span path must match its query block")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowUseOccurrence:
    """One distinct direct or extended named-window use occurrence."""

    query_block: QueryBlockOccurrence
    selected_output_ordinal: int
    kind: WindowUseKind
    span: Span

    def __post_init__(self) -> None:
        if type(self.query_block) is not QueryBlockOccurrence:
            raise TypeError("window-use query block must be exact")
        if type(self.selected_output_ordinal) is not int:
            raise TypeError("window-use output ordinal must be exact")
        if self.selected_output_ordinal < 0:
            raise ValueError("window-use output ordinal must be nonnegative")
        if type(self.kind) is not WindowUseKind:
            raise TypeError("window-use kind must be exact")
        if self.kind not in {
            WindowUseKind.NAMED_DIRECT,
            WindowUseKind.NAMED_EXTENDED,
        }:
            raise ValueError("named-window use occurrence requires a named use kind")
        if type(self.span) is not Span:
            raise TypeError("window-use span must be exact")
        if self.span.path != self.query_block.span.path:
            raise ValueError("window-use span path must match its query block")


class NamedWindowComponentKind(StrEnum):
    """The exact monotonic named-window composition dimensions."""

    PARTITION = "partition"
    ORDER = "order"
    FRAME = "frame"


NamedWindowComponentSource = NamedWindowOccurrence | WindowUseOccurrence


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowComponentProvenance:
    """Direct local/inherited evidence or use-time absence resolution."""

    component: NamedWindowComponentKind
    origin: WindowComponentOrigin
    source: NamedWindowComponentSource | None

    def __post_init__(self) -> None:
        if type(self.component) is not NamedWindowComponentKind:
            raise TypeError("named-window provenance component must be exact")
        if type(self.origin) is not WindowComponentOrigin:
            raise TypeError("named-window component origin must be exact")
        if (
            self.origin is WindowComponentOrigin.NOT_APPLICABLE
            and self.component is not NamedWindowComponentKind.FRAME
        ):
            raise ValueError("not-applicable provenance requires a frame component")
        if self.source is not None and type(self.source) not in {
            NamedWindowOccurrence,
            WindowUseOccurrence,
        }:
            raise TypeError("named-window component source must be exact or absent")
        if self.origin in {
            WindowComponentOrigin.LOCALLY_AUTHORED,
            WindowComponentOrigin.INHERITED,
        }:
            if self.source is None:
                raise ValueError("local and inherited components require a source")
        elif self.source is not None:
            raise ValueError("default and not-applicable components forbid a source")


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowBaseResolution:
    """One exact authored reference bound to one local declaration occurrence."""

    owner: NamedWindowOccurrence | WindowUseOccurrence
    reference: NamedWindowReference
    target_declaration: NamedWindowDeclaration
    target: NamedWindowOccurrence

    def __post_init__(self) -> None:
        if type(self.owner) not in {NamedWindowOccurrence, WindowUseOccurrence}:
            raise TypeError("named-window base owner must be exact")
        if type(self.reference) is not NamedWindowReference:
            raise TypeError("named-window base reference must be exact")
        if type(self.target_declaration) is not NamedWindowDeclaration:
            raise TypeError("named-window base declaration must be exact")
        if type(self.target) is not NamedWindowOccurrence:
            raise TypeError("named-window base target must be exact")
        if self.owner.query_block != self.target.query_block:
            raise ValueError("named-window reference and target owners must match")
        if self.reference.name != self.target_declaration.name:
            raise ValueError("named-window reference spelling must match its target")
        if self.target.span != self.target_declaration.span:
            raise ValueError("named-window target must retain its exact declaration")
        _require_named_window_reference_owner(
            self.reference,
            self.owner.query_block,
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedNamedWindowTemplate:
    """One function-independent composed declaration without effective defaults."""

    declaration: NamedWindowDeclaration
    occurrence: NamedWindowOccurrence
    base: NamedWindowBaseResolution | None
    base_template: ResolvedNamedWindowTemplate | None
    partition_by: tuple[Expression, ...]
    order_by: tuple[OrderItem, ...]
    frame: AuthoredWindowFrame | None
    partition_provenance: NamedWindowComponentProvenance | None
    ordering_provenance: NamedWindowComponentProvenance | None
    frame_provenance: NamedWindowComponentProvenance | None

    def __post_init__(self) -> None:
        if type(self.declaration) is not NamedWindowDeclaration:
            raise TypeError("resolved named-window declaration must be exact")
        if type(self.occurrence) is not NamedWindowOccurrence:
            raise TypeError("resolved named-window occurrence must be exact")
        if self.occurrence.span != self.declaration.span:
            raise ValueError("named-window occurrence must retain declaration span")
        if self.base is not None and type(self.base) is not NamedWindowBaseResolution:
            raise TypeError("resolved named-window base must be exact or absent")
        if (
            self.base_template is not None
            and type(self.base_template) is not ResolvedNamedWindowTemplate
        ):
            raise TypeError(
                "resolved named-window base template must be exact or absent"
            )
        if self.declaration.base is None:
            if self.base is not None or self.base_template is not None:
                raise ValueError("root named-window templates forbid a resolved base")
        elif (
            self.base is None
            or self.base_template is None
            or self.base.owner != self.occurrence
            or self.base.reference is not self.declaration.base
            or self.base.target_declaration is not self.base_template.declaration
            or self.base.target != self.base_template.occurrence
            or self.base.target.query_block != self.occurrence.query_block
        ):
            raise ValueError(
                "based named-window templates require the exact local base"
            )
        if type(self.partition_by) is not tuple or any(
            not isinstance(item, Expression) for item in self.partition_by
        ):
            raise TypeError("resolved named-window partition must be an exact tuple")
        if type(self.order_by) is not tuple or any(
            type(item) is not OrderItem for item in self.order_by
        ):
            raise TypeError("resolved named-window ordering must be an exact tuple")
        if self.frame is not None:
            if type(self.frame) is not AuthoredWindowFrame:
                raise TypeError("resolved named-window frame must be exact or absent")
            if self.frame.kind is AuthoredWindowFrameKind.OMITTED:
                raise ValueError(
                    "resolved named-window templates retain explicit frames"
                )
        local_partition, local_ordering, local_frame = _local_components(
            self.declaration.spec
        )
        expected_partition = (
            local_partition
            if local_partition
            else ()
            if self.base_template is None
            else self.base_template.partition_by
        )
        expected_ordering = (
            local_ordering
            if local_ordering
            else ()
            if self.base_template is None
            else self.base_template.order_by
        )
        expected_frame = (
            local_frame
            if local_frame is not None
            else None
            if self.base_template is None
            else self.base_template.frame
        )
        if (
            self.partition_by is not expected_partition
            or self.order_by is not expected_ordering
            or self.frame is not expected_frame
        ):
            raise ValueError("named-window template components must be exact")
        _require_template_component_provenance(
            bool(local_partition),
            self.base_template is not None and bool(self.base_template.partition_by),
            NamedWindowComponentKind.PARTITION,
            self.partition_provenance,
            self.occurrence,
            self.base,
            "partition",
        )
        _require_template_component_provenance(
            bool(local_ordering),
            self.base_template is not None and bool(self.base_template.order_by),
            NamedWindowComponentKind.ORDER,
            self.ordering_provenance,
            self.occurrence,
            self.base,
            "ordering",
        )
        _require_template_component_provenance(
            local_frame is not None,
            self.base_template is not None and self.base_template.frame is not None,
            NamedWindowComponentKind.FRAME,
            self.frame_provenance,
            self.occurrence,
            self.base,
            "frame",
        )

    @property
    def component_kinds(self) -> frozenset[NamedWindowComponentKind]:
        """Return explicit composed component presence without defaults."""

        return _component_kinds(self.partition_by, self.order_by, self.frame)


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedNamedWindowNamespace:
    """One complete query-local namespace with source and resolution orders."""

    query_block: QueryBlockOccurrence
    definition: TableDef | QueryDef
    declarations: tuple[NamedWindowDeclaration, ...]
    templates: tuple[ResolvedNamedWindowTemplate, ...]
    resolution_order: tuple[NamedWindowOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.query_block) is not QueryBlockOccurrence:
            raise TypeError("named-window namespace query block must be exact")
        if type(self.definition) not in {TableDef, QueryDef}:
            raise TypeError("named-window namespace definition must be exact")
        if (
            self.definition.span != self.query_block.span
            or self.definition.name != self.query_block.relation_name
            or self.definition.named_windows is not self.declarations
            or (
                type(self.definition) is TableDef
                and self.query_block.kind is not QueryBlockKind.TABLE
            )
            or (
                type(self.definition) is QueryDef
                and self.query_block.kind is not QueryBlockKind.QUERY
            )
        ):
            raise ValueError(
                "named-window namespace must retain its exact relation block"
            )
        if type(self.declarations) is not tuple or any(
            type(item) is not NamedWindowDeclaration for item in self.declarations
        ):
            raise TypeError("named-window declarations must be an exact tuple")
        if type(self.templates) is not tuple or any(
            type(item) is not ResolvedNamedWindowTemplate for item in self.templates
        ):
            raise TypeError("named-window templates must be an exact tuple")
        if len(self.templates) != len(self.declarations) or any(
            template.declaration is not declaration
            for template, declaration in zip(
                self.templates,
                self.declarations,
                strict=True,
            )
        ):
            raise ValueError("named-window templates must retain declaration order")
        if len({item.name for item in self.declarations}) != len(self.declarations):
            raise ValueError("resolved named-window namespaces require unique names")
        for position, (declaration, template) in enumerate(
            zip(self.declarations, self.templates, strict=True)
        ):
            if (
                template.occurrence.query_block != self.query_block
                or template.occurrence.declaration_position != position
                or template.occurrence.span != declaration.span
            ):
                raise ValueError(
                    "named-window template occurrence identity must be exact"
                )
        if type(self.resolution_order) is not tuple or any(
            type(item) is not NamedWindowOccurrence for item in self.resolution_order
        ):
            raise TypeError("named-window resolution order must be exact")
        if len(self.resolution_order) != len(self.templates) or {
            item.occurrence for item in self.templates
        } != set(self.resolution_order):
            raise ValueError("named-window resolution order must cover every template")
        resolution_positions = {
            occurrence: position
            for position, occurrence in enumerate(self.resolution_order)
        }
        templates_by_occurrence = {
            template.occurrence: template for template in self.templates
        }
        templates_by_name = {
            template.declaration.name: template for template in self.templates
        }
        for template in self.templates:
            declaration_base = template.declaration.base
            if declaration_base is None:
                expected_base_template = None
            else:
                expected_base_template = templates_by_name[declaration_base.name]
            if template.base_template is not expected_base_template:
                raise ValueError(
                    "named-window reference spelling must select the exact template"
                )
            if template.base is None:
                base_template = None
            else:
                base_template = templates_by_occurrence.get(template.base.target)
                if (
                    base_template is None
                    or base_template is not expected_base_template
                    or resolution_positions[base_template.occurrence]
                    >= resolution_positions[template.occurrence]
                ):
                    raise ValueError(
                        "named-window resolution order must place every base first"
                    )
            _require_exact_template_components(template, base_template=base_template)

    def template_for_name(self, name: str) -> ResolvedNamedWindowTemplate | None:
        """Resolve one exact local spelling without fallback or winner selection."""

        if type(name) is not str:
            raise TypeError("named-window lookup name must be an exact string")
        return next(
            (
                template
                for declaration, template in zip(
                    self.declarations,
                    self.templates,
                    strict=True,
                )
                if declaration.name == name
            ),
            None,
        )


class NamedWindowResolutionIssueKind(StrEnum):
    """Closed query-local namespace and monotonic composition failures."""

    DUPLICATE_NAME = "duplicate_name"
    DANGLING_REFERENCE = "dangling_reference"
    CYCLE = "cycle"
    COMPONENT_CONFLICT = "component_conflict"


NamedWindowIssueOwner = NamedWindowOccurrence | WindowUseOccurrence


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowResolutionIssue:
    """One typed failure with complete occurrence or witness evidence."""

    kind: NamedWindowResolutionIssueKind
    name: str
    owner: NamedWindowIssueOwner | None = None
    reference: NamedWindowReference | None = None
    occurrences: tuple[NamedWindowOccurrence, ...] = ()
    cycle: tuple[NamedWindowOccurrence, ...] = ()
    component: NamedWindowComponentKind | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not NamedWindowResolutionIssueKind:
            raise TypeError("named-window issue kind must be exact")
        if type(self.name) is not str or not self.name:
            raise ValueError("named-window issue name must be nonempty text")
        if self.owner is not None and type(self.owner) not in {
            NamedWindowOccurrence,
            WindowUseOccurrence,
        }:
            raise TypeError("named-window issue owner must be exact or absent")
        if (
            self.reference is not None
            and type(self.reference) is not NamedWindowReference
        ):
            raise TypeError("named-window issue reference must be exact or absent")
        if type(self.occurrences) is not tuple or any(
            type(item) is not NamedWindowOccurrence for item in self.occurrences
        ):
            raise TypeError("named-window issue occurrences must be exact")
        if type(self.cycle) is not tuple or any(
            type(item) is not NamedWindowOccurrence for item in self.cycle
        ):
            raise TypeError("named-window cycle witness must be exact")
        if (
            self.component is not None
            and type(self.component) is not NamedWindowComponentKind
        ):
            raise TypeError("named-window conflict component must be exact or absent")
        if self.kind is NamedWindowResolutionIssueKind.DUPLICATE_NAME:
            if (
                len(self.occurrences) < 2
                or any(
                    value is not None
                    for value in (self.owner, self.reference, self.component)
                )
                or self.cycle
            ):
                raise ValueError(
                    "duplicate issues require only all duplicate occurrences"
                )
        elif self.kind is NamedWindowResolutionIssueKind.DANGLING_REFERENCE:
            if (
                self.owner is None
                or self.reference is None
                or any((self.occurrences, self.cycle, self.component is not None))
            ):
                raise ValueError("dangling issues require only owner and reference")
        elif self.kind is NamedWindowResolutionIssueKind.CYCLE:
            if (
                len(self.cycle) < 2
                or self.cycle[0] != self.cycle[-1]
                or any(
                    value is not None
                    for value in (self.owner, self.reference, self.component)
                )
                or self.occurrences
            ):
                raise ValueError("cycle issues require only a closed witness")
        elif (
            self.owner is None
            or self.component is None
            or len(self.occurrences) != 1
            or self.reference is not None
            or self.cycle
        ):
            raise ValueError("component conflicts require owner, base, and component")


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowResolutionFailure:
    """Complete query-block failure with no published partial namespace."""

    query_block: QueryBlockOccurrence
    declarations: tuple[NamedWindowDeclaration, ...]
    issues: tuple[NamedWindowResolutionIssue, ...]

    def __post_init__(self) -> None:
        if type(self.query_block) is not QueryBlockOccurrence:
            raise TypeError("named-window failure query block must be exact")
        if type(self.declarations) is not tuple or any(
            type(item) is not NamedWindowDeclaration for item in self.declarations
        ):
            raise TypeError("named-window failure declarations must be exact")
        if (
            type(self.issues) is not tuple
            or not self.issues
            or any(type(item) is not NamedWindowResolutionIssue for item in self.issues)
        ):
            raise ValueError("named-window failure requires ordered typed issues")


@dataclass(frozen=True, slots=True, kw_only=True)
class ComposedNamedWindowUse:
    """One function-independent use after exact monotonic local composition."""

    expression: WindowExpr
    occurrence: WindowUseOccurrence
    namespace: ResolvedNamedWindowNamespace
    base: NamedWindowBaseResolution
    target_template: ResolvedNamedWindowTemplate
    partition_by: tuple[Expression, ...]
    order_by: tuple[OrderItem, ...]
    frame: AuthoredWindowFrame | None
    partition_provenance: NamedWindowComponentProvenance | None
    ordering_provenance: NamedWindowComponentProvenance | None
    frame_provenance: NamedWindowComponentProvenance | None

    def __post_init__(self) -> None:
        if type(self.expression) is not WindowExpr:
            raise TypeError("composed named-window use expression must be exact")
        if self.expression.use_kind is WindowUseKind.INLINE:
            raise ValueError("composed named-window uses require named authorship")
        if type(self.occurrence) is not WindowUseOccurrence:
            raise TypeError("composed named-window use occurrence must be exact")
        if type(self.namespace) is not ResolvedNamedWindowNamespace:
            raise TypeError("composed named-window namespace must be exact")
        if type(self.base) is not NamedWindowBaseResolution:
            raise TypeError("composed named-window base must be exact")
        if type(self.target_template) is not ResolvedNamedWindowTemplate:
            raise TypeError("composed named-window target template must be exact")
        reference = self.expression.base
        assert reference is not None
        if (
            self.occurrence.query_block != self.namespace.query_block
            or self.occurrence.span != self.expression.span
            or self.occurrence.kind is not self.expression.use_kind
            or self.base.owner != self.occurrence
            or reference is not self.base.reference
            or self.base.target_declaration is not self.target_template.declaration
            or self.base.target != self.target_template.occurrence
            or self.occurrence.selected_output_ordinal
            >= len(self.namespace.definition.select_items)
            or self.namespace.definition.select_items[
                self.occurrence.selected_output_ordinal
            ].expression
            is not self.expression
        ):
            raise ValueError(
                "named-window use occurrence and base evidence must be exact"
            )
        exact_target = next(
            (
                template
                for template in self.namespace.templates
                if template.declaration.name == reference.name
            ),
            None,
        )
        if exact_target is None or exact_target is not self.target_template:
            raise ValueError("named-window use base must target its exact namespace")
        if type(self.partition_by) is not tuple or any(
            not isinstance(item, Expression) for item in self.partition_by
        ):
            raise TypeError("composed named-window partition must be exact")
        if type(self.order_by) is not tuple or any(
            type(item) is not OrderItem for item in self.order_by
        ):
            raise TypeError("composed named-window ordering must be exact")
        if self.frame is not None and (
            type(self.frame) is not AuthoredWindowFrame
            or self.frame.kind is AuthoredWindowFrameKind.OMITTED
        ):
            raise ValueError("composed named-window frame must be explicit or absent")
        local_partition, local_ordering, local_frame = _local_components(
            self.expression.spec
        )
        if (
            self.partition_by
            is not (
                local_partition
                if local_partition
                else self.target_template.partition_by
            )
            or self.order_by
            is not (local_ordering if local_ordering else self.target_template.order_by)
            or self.frame
            is not (
                local_frame if local_frame is not None else self.target_template.frame
            )
        ):
            raise ValueError("named-window use components must match exact composition")
        _require_use_component_provenance(
            bool(local_partition),
            bool(self.target_template.partition_by),
            NamedWindowComponentKind.PARTITION,
            self.partition_provenance,
            self.occurrence,
            self.base,
            "partition",
        )
        _require_use_component_provenance(
            bool(local_ordering),
            bool(self.target_template.order_by),
            NamedWindowComponentKind.ORDER,
            self.ordering_provenance,
            self.occurrence,
            self.base,
            "ordering",
        )
        _require_use_component_provenance(
            local_frame is not None,
            self.target_template.frame is not None,
            NamedWindowComponentKind.FRAME,
            self.frame_provenance,
            self.occurrence,
            self.base,
            "frame",
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowUseResolutionFailure:
    """One dangling or conflicting use with no resolved specification."""

    namespace: ResolvedNamedWindowNamespace
    occurrence: WindowUseOccurrence
    issues: tuple[NamedWindowResolutionIssue, ...]

    def __post_init__(self) -> None:
        if type(self.namespace) is not ResolvedNamedWindowNamespace:
            raise TypeError("named-window use failure namespace must be exact")
        if type(self.occurrence) is not WindowUseOccurrence:
            raise TypeError("named-window use failure occurrence must be exact")
        if self.occurrence.query_block != self.namespace.query_block:
            raise ValueError(
                "named-window use failure must retain its exact query block"
            )
        if (
            type(self.issues) is not tuple
            or not self.issues
            or any(type(item) is not NamedWindowResolutionIssue for item in self.issues)
        ):
            raise ValueError("named-window use failure requires ordered issues")


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


def authored_window_specification_from_ast(
    specification: WindowSpec,
) -> AuthoredWindowSpecification:
    """Lift one parsed specification into the existing authored model."""

    if type(specification) is not WindowSpec:
        raise TypeError("authored window construction requires an exact WindowSpec")
    return AuthoredWindowSpecification(
        span=specification.span,
        partition_by=specification.partition_by,
        order_by=specification.order_by,
        frame=specification.frame,
    )


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


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedNamedWindowUse:
    """One concrete named use resolved under its actual frame applicability."""

    composed: ComposedNamedWindowUse
    function_identity: WindowFunctionIdentity
    function_policy: WindowFunctionFramePolicy
    resolved: ResolvedWindowSpecification
    partition_provenance: NamedWindowComponentProvenance
    ordering_provenance: NamedWindowComponentProvenance
    frame_provenance: NamedWindowComponentProvenance

    def __post_init__(self) -> None:
        if type(self.composed) is not ComposedNamedWindowUse:
            raise TypeError("resolved named-window composition must be exact")
        if type(self.function_identity) is not WindowFunctionIdentity:
            raise TypeError("resolved named-window function identity must be exact")
        if type(self.function_policy) is not WindowFunctionFramePolicy:
            raise TypeError("resolved named-window function policy must be exact")
        if (
            self.function_identity != self.composed.expression.identity
            or self.function_policy.identity != self.function_identity
        ):
            raise ValueError("named-window use and function policy identity must match")
        if type(self.resolved) is not ResolvedWindowSpecification:
            raise TypeError("resolved named-window specification must be exact")
        local_specification = self.composed.expression.spec
        authored = self.resolved.authored
        if (
            authored.span != self.composed.expression.span
            or authored.partition_by is not local_specification.partition_by
            or authored.order_by is not local_specification.order_by
            or authored.frame is not local_specification.frame
        ):
            raise ValueError(
                "resolved named-window use must retain exact local authored components"
            )
        for value in (
            self.partition_provenance,
            self.ordering_provenance,
            self.frame_provenance,
        ):
            if type(value) is not NamedWindowComponentProvenance:
                raise TypeError("resolved named-window provenance must be exact")
        if self.resolved.partition_by is not self.composed.partition_by:
            raise ValueError("resolved named-window partition must match composition")
        if self.resolved.order_by is not self.composed.order_by:
            raise ValueError("resolved named-window ordering must match composition")
        if self.resolved.frame.applicability is not (
            self.function_policy.required_frame_applicability
        ):
            raise ValueError("resolved named-window frame must match actual policy")
        if self.resolved.partition_origin is not self.partition_provenance.origin:
            raise ValueError("resolved named-window partition origin must match")
        if self.resolved.ordering_origin is not self.ordering_provenance.origin:
            raise ValueError("resolved named-window ordering origin must match")
        if self.composed.partition_provenance is None:
            if self.partition_provenance.origin is not (
                WindowComponentOrigin.EFFECTIVE_DEFAULT
            ):
                raise ValueError("absent named-window partition must default at use")
        elif self.partition_provenance != self.composed.partition_provenance:
            raise ValueError("explicit named-window partition provenance must survive")
        if self.composed.ordering_provenance is None:
            if self.ordering_provenance.origin is not (
                WindowComponentOrigin.EFFECTIVE_DEFAULT
            ):
                raise ValueError("absent named-window ordering must default at use")
        elif self.ordering_provenance != self.composed.ordering_provenance:
            raise ValueError("explicit named-window ordering provenance must survive")
        explicit_frame_provenance = self.composed.frame_provenance
        if explicit_frame_provenance is None:
            if (
                self.frame_provenance.source is not None
                or self.resolved.frame.origin is not self.frame_provenance.origin
            ):
                raise ValueError("resolved named-window frame origin must match")
        else:
            if self.frame_provenance != explicit_frame_provenance:
                raise ValueError("explicit named-window frame provenance must survive")
            expected_origin = (
                WindowComponentOrigin.NOT_APPLICABLE
                if self.resolved.frame.applicability
                is WindowFrameApplicability.NOT_APPLICABLE
                else explicit_frame_provenance.origin
            )
            if self.resolved.frame.origin is not expected_origin:
                raise ValueError(
                    "explicit named-window frame origin must match provenance and policy"
                )
        _require_provenance_component(
            self.partition_provenance,
            NamedWindowComponentKind.PARTITION,
            "resolved named-window partition",
        )
        _require_provenance_component(
            self.ordering_provenance,
            NamedWindowComponentKind.ORDER,
            "resolved named-window ordering",
        )
        _require_provenance_component(
            self.frame_provenance,
            NamedWindowComponentKind.FRAME,
            "resolved named-window frame",
        )
        expected_frame_authorship = (
            self.composed.frame or self.composed.expression.spec.frame
        )
        if self.resolved.frame.authored is not expected_frame_authorship:
            raise ValueError("resolved named-window frame authorship must be exact")


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


def resolve_named_window_namespace(
    definition: TableDef | QueryDef,
) -> ResolvedNamedWindowNamespace | NamedWindowResolutionFailure:
    """Resolve one complete query-local declaration namespace or fail closed."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("named-window resolution requires an exact relation block")
    return resolve_named_window_namespace_for_query_block(
        definition,
        query_block=_query_block_occurrence(definition),
    )


def resolve_named_window_namespace_for_query_block(
    definition: TableDef | QueryDef,
    *,
    query_block: QueryBlockOccurrence,
) -> ResolvedNamedWindowNamespace | NamedWindowResolutionFailure:
    """Resolve declarations while retaining one supplied exact query block."""

    if type(definition) not in {TableDef, QueryDef}:
        raise TypeError("named-window resolution requires an exact relation block")
    if type(query_block) is not QueryBlockOccurrence:
        raise TypeError("named-window resolution requires an exact query block")
    expected_kind = (
        QueryBlockKind.TABLE if type(definition) is TableDef else QueryBlockKind.QUERY
    )
    if (
        query_block.source_id != (definition.span.path or definition.name)
        or query_block.relation_name != definition.name
        or query_block.kind is not expected_kind
        or query_block.span != definition.span
    ):
        raise ValueError("named-window query block must retain its exact relation")
    declarations = definition.named_windows
    for declaration in declarations:
        if declaration.base is not None:
            _require_named_window_reference_owner(declaration.base, query_block)
    occurrences = tuple(
        NamedWindowOccurrence(
            query_block=query_block,
            declaration_position=position,
            span=declaration.span,
        )
        for position, declaration in enumerate(declarations)
    )
    occurrences_by_name: dict[str, list[NamedWindowOccurrence]] = {}
    for declaration, occurrence in zip(declarations, occurrences, strict=True):
        occurrences_by_name.setdefault(declaration.name, []).append(occurrence)
    duplicate_issues = tuple(
        NamedWindowResolutionIssue(
            kind=NamedWindowResolutionIssueKind.DUPLICATE_NAME,
            name=name,
            occurrences=tuple(matches),
        )
        for name, matches in occurrences_by_name.items()
        if len(matches) > 1
    )
    if duplicate_issues:
        return NamedWindowResolutionFailure(
            query_block=query_block,
            declarations=declarations,
            issues=duplicate_issues,
        )

    declaration_by_name = {
        declaration.name: declaration for declaration in declarations
    }
    occurrence_by_name = {
        declaration.name: occurrence
        for declaration, occurrence in zip(declarations, occurrences, strict=True)
    }
    dangling_issues = tuple(
        NamedWindowResolutionIssue(
            kind=NamedWindowResolutionIssueKind.DANGLING_REFERENCE,
            name=declaration.base.name,
            owner=occurrence,
            reference=declaration.base,
        )
        for declaration, occurrence in zip(declarations, occurrences, strict=True)
        if declaration.base is not None
        and declaration.base.name not in declaration_by_name
    )
    if dangling_issues:
        return NamedWindowResolutionFailure(
            query_block=query_block,
            declarations=declarations,
            issues=dangling_issues,
        )

    resolution_names = _named_window_resolution_order(
        declaration_by_name,
    )
    if len(resolution_names) != len(declarations):
        return NamedWindowResolutionFailure(
            query_block=query_block,
            declarations=declarations,
            issues=_named_window_cycle_issues(
                declaration_by_name,
                occurrence_by_name,
                resolved_names=frozenset(resolution_names),
            ),
        )

    explicit_components: dict[str, frozenset[NamedWindowComponentKind]] = {}
    conflict_issues: list[NamedWindowResolutionIssue] = []
    for name in resolution_names:
        declaration = declaration_by_name[name]
        local = _local_component_kinds(declaration.spec)
        base_components: frozenset[NamedWindowComponentKind] = frozenset()
        base_occurrence: NamedWindowOccurrence | None = None
        if declaration.base is not None:
            base_components = explicit_components[declaration.base.name]
            base_occurrence = occurrence_by_name[declaration.base.name]
        for component in NamedWindowComponentKind:
            if component in local and component in base_components:
                assert base_occurrence is not None
                conflict_issues.append(
                    NamedWindowResolutionIssue(
                        kind=NamedWindowResolutionIssueKind.COMPONENT_CONFLICT,
                        name=name,
                        owner=occurrence_by_name[name],
                        occurrences=(base_occurrence,),
                        component=component,
                    )
                )
        explicit_components[name] = local | base_components
    if conflict_issues:
        return NamedWindowResolutionFailure(
            query_block=query_block,
            declarations=declarations,
            issues=tuple(conflict_issues),
        )

    template_by_name: dict[str, ResolvedNamedWindowTemplate] = {}
    for name in resolution_names:
        declaration = declaration_by_name[name]
        base_template = (
            None
            if declaration.base is None
            else template_by_name[declaration.base.name]
        )
        template_by_name[name] = _compose_named_window_template(
            declaration,
            occurrence=occurrence_by_name[name],
            base_template=base_template,
        )
    return ResolvedNamedWindowNamespace(
        query_block=query_block,
        definition=definition,
        declarations=declarations,
        templates=tuple(
            template_by_name[declaration.name] for declaration in declarations
        ),
        resolution_order=tuple(occurrence_by_name[name] for name in resolution_names),
    )


def compose_named_window_use(
    namespace: ResolvedNamedWindowNamespace,
    expression: WindowExpr,
    *,
    selected_output_ordinal: int,
) -> ComposedNamedWindowUse | NamedWindowUseResolutionFailure:
    """Bind and monotonically compose one direct or extended named use."""

    if type(namespace) is not ResolvedNamedWindowNamespace:
        raise TypeError("named-window use requires an exact namespace")
    if type(expression) is not WindowExpr:
        raise TypeError("named-window use requires an exact WindowExpr")
    if expression.use_kind is WindowUseKind.INLINE or expression.base is None:
        raise ValueError("named-window composition requires named authorship")
    _require_named_window_reference_owner(expression.base, namespace.query_block)
    if (
        not 0 <= selected_output_ordinal < len(namespace.definition.select_items)
        or namespace.definition.select_items[selected_output_ordinal].expression
        is not expression
    ):
        raise ValueError("named-window use ordinal must select its exact expression")
    occurrence = WindowUseOccurrence(
        query_block=namespace.query_block,
        selected_output_ordinal=selected_output_ordinal,
        kind=expression.use_kind,
        span=expression.span,
    )
    target = namespace.template_for_name(expression.base.name)
    if target is None:
        return NamedWindowUseResolutionFailure(
            namespace=namespace,
            occurrence=occurrence,
            issues=(
                NamedWindowResolutionIssue(
                    kind=NamedWindowResolutionIssueKind.DANGLING_REFERENCE,
                    name=expression.base.name,
                    owner=occurrence,
                    reference=expression.base,
                ),
            ),
        )

    local_components = _local_component_kinds(expression.spec)
    conflicts = tuple(
        NamedWindowResolutionIssue(
            kind=NamedWindowResolutionIssueKind.COMPONENT_CONFLICT,
            name=expression.base.name,
            owner=occurrence,
            occurrences=(target.occurrence,),
            component=component,
        )
        for component in NamedWindowComponentKind
        if component in local_components and component in target.component_kinds
    )
    if conflicts:
        return NamedWindowUseResolutionFailure(
            namespace=namespace,
            occurrence=occurrence,
            issues=conflicts,
        )

    local_partition, local_ordering, local_frame = _local_components(expression.spec)
    base = NamedWindowBaseResolution(
        owner=occurrence,
        reference=expression.base,
        target_declaration=target.declaration,
        target=target.occurrence,
    )
    return ComposedNamedWindowUse(
        expression=expression,
        occurrence=occurrence,
        namespace=namespace,
        base=base,
        target_template=target,
        partition_by=local_partition or target.partition_by,
        order_by=local_ordering or target.order_by,
        frame=local_frame or target.frame,
        partition_provenance=_use_component_provenance(
            bool(local_partition),
            not local_partition and bool(target.partition_by),
            occurrence,
            target.occurrence,
            NamedWindowComponentKind.PARTITION,
        ),
        ordering_provenance=_use_component_provenance(
            bool(local_ordering),
            not local_ordering and bool(target.order_by),
            occurrence,
            target.occurrence,
            NamedWindowComponentKind.ORDER,
        ),
        frame_provenance=_use_component_provenance(
            local_frame is not None,
            local_frame is None and target.frame is not None,
            occurrence,
            target.occurrence,
            NamedWindowComponentKind.FRAME,
        ),
    )


def resolve_composed_named_window_use(
    composed: ComposedNamedWindowUse,
    *,
    function_identity: WindowFunctionIdentity,
    function_policy: WindowFunctionFramePolicy,
) -> ResolvedNamedWindowUse:
    """Apply use-specific defaults only after complete named composition."""

    if type(composed) is not ComposedNamedWindowUse:
        raise TypeError("named-window use resolution requires exact composition")
    if type(function_identity) is not WindowFunctionIdentity:
        raise TypeError("named-window use function identity must be exact")
    if type(function_policy) is not WindowFunctionFramePolicy:
        raise TypeError("named-window use function policy must be exact")
    if (
        function_identity != composed.expression.identity
        or function_policy.identity != function_identity
    ):
        raise ValueError("named-window use requires its actual function policy")
    frame_applicability = function_policy.required_frame_applicability
    local_specification = composed.expression.spec
    authored = AuthoredWindowSpecification(
        span=composed.expression.span,
        partition_by=local_specification.partition_by,
        order_by=local_specification.order_by,
        frame=local_specification.frame,
    )
    partition_provenance = composed.partition_provenance or (
        NamedWindowComponentProvenance(
            component=NamedWindowComponentKind.PARTITION,
            origin=WindowComponentOrigin.EFFECTIVE_DEFAULT,
            source=None,
        )
    )
    ordering_provenance = composed.ordering_provenance or (
        NamedWindowComponentProvenance(
            component=NamedWindowComponentKind.ORDER,
            origin=WindowComponentOrigin.EFFECTIVE_DEFAULT,
            source=None,
        )
    )
    if frame_applicability is WindowFrameApplicability.NOT_APPLICABLE:
        frame_authored = composed.frame or authored.frame
        resolved_frame = ResolvedWindowFrame(
            applicability=frame_applicability,
            origin=WindowComponentOrigin.NOT_APPLICABLE,
            authored=frame_authored,
        )
        frame_provenance = composed.frame_provenance or (
            NamedWindowComponentProvenance(
                component=NamedWindowComponentKind.FRAME,
                origin=WindowComponentOrigin.NOT_APPLICABLE,
                source=None,
            )
        )
    elif composed.frame is None:
        resolved_frame = _resolve_authored_window_frame(
            authored.frame,
            frame_applicability=frame_applicability,
        )
        frame_provenance = NamedWindowComponentProvenance(
            component=NamedWindowComponentKind.FRAME,
            origin=WindowComponentOrigin.EFFECTIVE_DEFAULT,
            source=None,
        )
    else:
        resolved_frame = _resolve_authored_window_frame(
            composed.frame,
            frame_applicability=frame_applicability,
        )
        assert composed.frame_provenance is not None
        if composed.frame_provenance.origin is WindowComponentOrigin.INHERITED:
            resolved_frame = replace(
                resolved_frame,
                origin=WindowComponentOrigin.INHERITED,
            )
        frame_provenance = composed.frame_provenance

    resolved = ResolvedWindowSpecification(
        authored=authored,
        partition_by=composed.partition_by,
        order_by=composed.order_by,
        partition_origin=partition_provenance.origin,
        ordering_origin=ordering_provenance.origin,
        frame=resolved_frame,
    )
    return ResolvedNamedWindowUse(
        composed=composed,
        function_identity=function_identity,
        function_policy=function_policy,
        resolved=resolved,
        partition_provenance=partition_provenance,
        ordering_provenance=ordering_provenance,
        frame_provenance=frame_provenance,
    )


def _effective_named_window_expression(
    resolved_use: ResolvedNamedWindowUse,
) -> WindowExpr:
    """Create one transient effective expression for existing semantic readers."""

    if type(resolved_use) is not ResolvedNamedWindowUse:
        raise TypeError("effective named-window expression requires a resolved use")
    composed = resolved_use.composed
    return WindowExpr(
        span=composed.expression.span,
        call=composed.expression.call,
        spec=WindowSpec(
            span=composed.expression.spec.span,
            partition_by=composed.partition_by,
            order_by=composed.order_by,
            frame=(
                composed.frame
                if composed.frame is not None
                else AuthoredWindowFrame(kind=AuthoredWindowFrameKind.OMITTED)
            ),
        ),
        identity=composed.expression.identity,
        nth_direction=composed.expression.nth_direction,
        null_treatment=composed.expression.null_treatment,
    )


def _query_block_occurrence(
    definition: TableDef | QueryDef,
) -> QueryBlockOccurrence:
    return QueryBlockOccurrence(
        source_id=definition.span.path or definition.name,
        relation_name=definition.name,
        kind=(
            QueryBlockKind.TABLE
            if type(definition) is TableDef
            else QueryBlockKind.QUERY
        ),
        span=definition.span,
    )


def _require_named_window_reference_owner(
    reference: NamedWindowReference,
    query_block: QueryBlockOccurrence,
) -> None:
    if reference.span.path != query_block.span.path:
        raise ValueError("named-window reference must belong to its owner block")


def _named_window_resolution_order(
    declarations: dict[str, NamedWindowDeclaration],
) -> tuple[str, ...]:
    children = {name: [] for name in declarations}
    dependency_counts: dict[str, int] = {}
    for name, declaration in declarations.items():
        dependency_counts[name] = 0 if declaration.base is None else 1
        if declaration.base is not None:
            children[declaration.base.name].append(name)
    ready = [name for name, count in dependency_counts.items() if count == 0]
    ready.sort()
    order: list[str] = []
    while ready:
        name = heappop(ready)
        order.append(name)
        for child in sorted(children[name]):
            dependency_counts[child] -= 1
            if dependency_counts[child] == 0:
                heappush(ready, child)
    return tuple(order)


def _named_window_cycle_issues(
    declarations: dict[str, NamedWindowDeclaration],
    occurrences: dict[str, NamedWindowOccurrence],
    *,
    resolved_names: frozenset[str],
) -> tuple[NamedWindowResolutionIssue, ...]:
    unresolved = frozenset(declarations) - resolved_names
    completed: set[str] = set()
    witnesses: list[tuple[str, ...]] = []
    for start in sorted(unresolved):
        if start in completed:
            continue
        path: list[str] = []
        positions: dict[str, int] = {}
        current = start
        while current in unresolved and current not in positions:
            if current in completed:
                break
            positions[current] = len(path)
            path.append(current)
            base = declarations[current].base
            assert base is not None
            current = base.name
        if current in positions:
            cycle = path[positions[current] :]
            first = min(range(len(cycle)), key=lambda index: cycle[index])
            canonical = tuple(cycle[first:] + cycle[:first])
            witnesses.append((*canonical, canonical[0]))
        completed.update(path)
    return tuple(
        NamedWindowResolutionIssue(
            kind=NamedWindowResolutionIssueKind.CYCLE,
            name=" -> ".join(witness),
            cycle=tuple(occurrences[name] for name in witness),
        )
        for witness in witnesses
    )


def _compose_named_window_template(
    declaration: NamedWindowDeclaration,
    *,
    occurrence: NamedWindowOccurrence,
    base_template: ResolvedNamedWindowTemplate | None,
) -> ResolvedNamedWindowTemplate:
    local_partition, local_ordering, local_frame = _local_components(declaration.spec)
    if base_template is None:
        base = None
    else:
        reference = declaration.base
        assert reference is not None
        base = NamedWindowBaseResolution(
            owner=occurrence,
            reference=reference,
            target_declaration=base_template.declaration,
            target=base_template.occurrence,
        )
    return ResolvedNamedWindowTemplate(
        declaration=declaration,
        occurrence=occurrence,
        base=base,
        base_template=base_template,
        partition_by=(
            local_partition
            if local_partition
            else ()
            if base_template is None
            else base_template.partition_by
        ),
        order_by=(
            local_ordering
            if local_ordering
            else ()
            if base_template is None
            else base_template.order_by
        ),
        frame=(
            local_frame
            if local_frame is not None
            else None
            if base_template is None
            else base_template.frame
        ),
        partition_provenance=_template_component_provenance(
            bool(local_partition),
            not local_partition
            and base_template is not None
            and bool(base_template.partition_by),
            occurrence,
            None if base_template is None else base_template.occurrence,
            NamedWindowComponentKind.PARTITION,
        ),
        ordering_provenance=_template_component_provenance(
            bool(local_ordering),
            not local_ordering
            and base_template is not None
            and bool(base_template.order_by),
            occurrence,
            None if base_template is None else base_template.occurrence,
            NamedWindowComponentKind.ORDER,
        ),
        frame_provenance=_template_component_provenance(
            local_frame is not None,
            local_frame is None
            and base_template is not None
            and base_template.frame is not None,
            occurrence,
            None if base_template is None else base_template.occurrence,
            NamedWindowComponentKind.FRAME,
        ),
    )


def _local_components(
    specification: WindowSpec | None,
) -> tuple[
    tuple[Expression, ...],
    tuple[OrderItem, ...],
    AuthoredWindowFrame | None,
]:
    if specification is None:
        return (), (), None
    return (
        specification.partition_by,
        specification.order_by,
        (
            None
            if specification.frame.kind is AuthoredWindowFrameKind.OMITTED
            else specification.frame
        ),
    )


def _local_component_kinds(
    specification: WindowSpec | None,
) -> frozenset[NamedWindowComponentKind]:
    return _component_kinds(*_local_components(specification))


def _component_kinds(
    partition_by: tuple[Expression, ...],
    order_by: tuple[OrderItem, ...],
    frame: AuthoredWindowFrame | None,
) -> frozenset[NamedWindowComponentKind]:
    return frozenset(
        component
        for component, present in (
            (NamedWindowComponentKind.PARTITION, bool(partition_by)),
            (NamedWindowComponentKind.ORDER, bool(order_by)),
            (NamedWindowComponentKind.FRAME, frame is not None),
        )
        if present
    )


def _template_component_provenance(
    local: bool,
    inherited: bool,
    occurrence: NamedWindowOccurrence,
    base_occurrence: NamedWindowOccurrence | None,
    component: NamedWindowComponentKind,
) -> NamedWindowComponentProvenance | None:
    if local:
        return NamedWindowComponentProvenance(
            component=component,
            origin=WindowComponentOrigin.LOCALLY_AUTHORED,
            source=occurrence,
        )
    if inherited:
        assert base_occurrence is not None
        return NamedWindowComponentProvenance(
            component=component,
            origin=WindowComponentOrigin.INHERITED,
            source=base_occurrence,
        )
    return None


def _use_component_provenance(
    local: bool,
    inherited: bool,
    occurrence: WindowUseOccurrence,
    base_occurrence: NamedWindowOccurrence,
    component: NamedWindowComponentKind,
) -> NamedWindowComponentProvenance | None:
    if local:
        return NamedWindowComponentProvenance(
            component=component,
            origin=WindowComponentOrigin.LOCALLY_AUTHORED,
            source=occurrence,
        )
    if inherited:
        return NamedWindowComponentProvenance(
            component=component,
            origin=WindowComponentOrigin.INHERITED,
            source=base_occurrence,
        )
    return None


def _require_exact_template_components(
    template: ResolvedNamedWindowTemplate,
    *,
    base_template: ResolvedNamedWindowTemplate | None,
) -> None:
    local_partition, local_ordering, local_frame = _local_components(
        template.declaration.spec
    )
    expected_partition = (
        local_partition
        if local_partition
        else ()
        if base_template is None
        else base_template.partition_by
    )
    expected_ordering = (
        local_ordering
        if local_ordering
        else ()
        if base_template is None
        else base_template.order_by
    )
    expected_frame = (
        local_frame
        if local_frame is not None
        else None
        if base_template is None
        else base_template.frame
    )
    if (
        template.partition_by is not expected_partition
        or template.order_by is not expected_ordering
        or template.frame is not expected_frame
    ):
        raise ValueError("named-window template components must be exact")
    if base_template is not None and (
        template.base is None or template.base.target != base_template.occurrence
    ):
        raise ValueError("named-window template must retain its exact direct base")


def _require_template_component_provenance(
    local: bool,
    inherited: bool,
    component: NamedWindowComponentKind,
    provenance: NamedWindowComponentProvenance | None,
    occurrence: NamedWindowOccurrence,
    base: NamedWindowBaseResolution | None,
    label: str,
) -> None:
    if local and inherited:
        raise ValueError(f"template {label} cannot be local and inherited")
    if not local and not inherited:
        if provenance is not None:
            raise ValueError(f"absent template {label} forbids provenance")
        return
    if type(provenance) is not NamedWindowComponentProvenance:
        raise TypeError(f"present template {label} requires exact provenance")
    _require_provenance_component(provenance, component, f"template {label}")
    if local:
        if (
            provenance.origin is not WindowComponentOrigin.LOCALLY_AUTHORED
            or provenance.source != occurrence
        ):
            raise ValueError(f"local template {label} must name its occurrence")
    elif (
        not inherited
        or provenance.origin is not WindowComponentOrigin.INHERITED
        or base is None
        or provenance.source != base.target
    ):
        raise ValueError(f"inherited template {label} must name its direct base")


def _require_use_component_provenance(
    local: bool,
    inherited: bool,
    component: NamedWindowComponentKind,
    provenance: NamedWindowComponentProvenance | None,
    occurrence: WindowUseOccurrence,
    base: NamedWindowBaseResolution,
    label: str,
) -> None:
    if local and inherited:
        raise ValueError(f"use {label} cannot be local and inherited")
    if not local and not inherited:
        if provenance is not None:
            raise ValueError(f"absent use {label} forbids provenance")
        return
    if type(provenance) is not NamedWindowComponentProvenance:
        raise TypeError(f"present use {label} requires exact provenance")
    _require_provenance_component(provenance, component, f"use {label}")
    if local:
        if (
            provenance.origin is not WindowComponentOrigin.LOCALLY_AUTHORED
            or provenance.source != occurrence
        ):
            raise ValueError(f"local use {label} must name its occurrence")
    elif (
        not inherited
        or provenance.origin is not WindowComponentOrigin.INHERITED
        or provenance.source != base.target
    ):
        raise ValueError(f"inherited use {label} must name its direct base")


def _require_provenance_component(
    provenance: NamedWindowComponentProvenance,
    component: NamedWindowComponentKind,
    label: str,
) -> None:
    if provenance.component is not component:
        raise ValueError(
            f"{label} provenance must name its component; "
            "component kind must match its slot"
        )


class WindowNullTreatment(StrEnum):
    """Effective NULL treatment for applicable value/navigation functions."""

    RESPECT_NULLS = "respect_nulls"
    IGNORE_NULLS = "ignore_nulls"


class WindowNthDirection(StrEnum):
    """Effective nth-value candidate traversal direction."""

    FROM_FIRST = "from_first"
    FROM_LAST = "from_last"


@dataclass(frozen=True, slots=True, kw_only=True)
class ResolvedWindowFunctionModifiers:
    """Exact authored and effective use-local modifier evidence."""

    identity: WindowFunctionIdentity
    authored_null_treatment: AuthoredWindowNullTreatment | None
    null_treatment: WindowNullTreatment | None
    authored_nth_direction: AuthoredWindowNthDirection | None
    nth_direction: WindowNthDirection | None

    def __post_init__(self) -> None:
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("window modifier identity must be exact")
        if (
            self.identity.namespace != ()
            or self.identity.role is not WindowFunctionRole.WINDOW_FUNCTION
            or self.identity.name
            not in {
                "row_number",
                "rank",
                "dense_rank",
                "percent_rank",
                "cume_dist",
                "ntile",
                "lag",
                "lead",
                "first_value",
                "last_value",
                "nth_value",
            }
        ):
            raise ValueError("window modifier identity must be one exact builtin")
        if (
            self.authored_null_treatment is not None
            and type(self.authored_null_treatment) is not AuthoredWindowNullTreatment
        ):
            raise TypeError("authored NULL treatment must be exact or absent")
        if (
            self.null_treatment is not None
            and type(self.null_treatment) is not WindowNullTreatment
        ):
            raise TypeError("effective NULL treatment must be exact or absent")
        if (
            self.authored_nth_direction is not None
            and type(self.authored_nth_direction) is not AuthoredWindowNthDirection
        ):
            raise TypeError("authored nth direction must be exact or absent")
        if (
            self.nth_direction is not None
            and type(self.nth_direction) is not WindowNthDirection
        ):
            raise TypeError("effective nth direction must be exact or absent")

        name = self.identity.name
        null_treatment_applies = name in {
            "lag",
            "lead",
            "first_value",
            "last_value",
            "nth_value",
        }
        if null_treatment_applies:
            expected_null_treatment = (
                WindowNullTreatment.RESPECT_NULLS
                if self.authored_null_treatment is None
                or self.authored_null_treatment.kind is WindowNullTreatmentKind.RESPECT
                else WindowNullTreatment.IGNORE_NULLS
            )
            if self.null_treatment is not expected_null_treatment:
                raise ValueError("effective NULL treatment must match authorship")
        elif (
            self.authored_null_treatment is not None or self.null_treatment is not None
        ):
            raise ValueError("function identity forbids NULL treatment")

        if name == "nth_value":
            expected_nth_direction = (
                WindowNthDirection.FROM_FIRST
                if self.authored_nth_direction is None
                or self.authored_nth_direction.kind is WindowNthDirectionKind.FIRST
                else WindowNthDirection.FROM_LAST
            )
            if self.nth_direction is not expected_nth_direction:
                raise ValueError("effective nth direction must match authorship")
        elif self.authored_nth_direction is not None or self.nth_direction is not None:
            raise ValueError("function identity forbids nth direction")

    @property
    def null_treatment_is_explicit(self) -> bool:
        return self.authored_null_treatment is not None

    @property
    def nth_direction_is_explicit(self) -> bool:
        return self.authored_nth_direction is not None


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
class RowsFramePositionInterval:
    """One lazy half-open ROWS base-frame view over partition positions."""

    partition_size: int
    start: int
    stop: int

    def __post_init__(self) -> None:
        if type(self.partition_size) is not int:
            raise TypeError("ROWS partition size must be an exact integer")
        if self.partition_size <= 0:
            raise ValueError("ROWS partition size must be positive")
        if type(self.start) is not int or type(self.stop) is not int:
            raise TypeError("ROWS interval bounds must be exact integers")
        if not 0 <= self.start <= self.partition_size:
            raise ValueError("ROWS interval start must be a partition boundary")
        if not 0 <= self.stop <= self.partition_size:
            raise ValueError("ROWS interval stop must be a partition boundary")

    @property
    def positions(self) -> range:
        """Return the lazy physical-position view without row allocation."""

        return range(self.start, self.stop)

    @property
    def empty(self) -> bool:
        """Whether the intersected half-open interval contains no positions."""

        return self.start >= self.stop


def rows_frame_position_interval(
    frame: ValidatedFrame,
    *,
    partition_size: int,
    current_position: int,
) -> RowsFramePositionInterval:
    """Intersect one validated ROWS base frame with its partition positions."""

    if type(frame) is not ValidatedFrame:
        raise TypeError("ROWS interval evaluation requires an exact ValidatedFrame")
    if type(partition_size) is not int:
        raise TypeError("ROWS partition size must be an exact integer")
    if partition_size <= 0:
        raise ValueError("ROWS partition size must be positive")
    if type(current_position) is not int:
        raise TypeError("ROWS current position must be an exact integer")
    if not 0 <= current_position < partition_size:
        raise ValueError("ROWS current position must belong to the partition")

    resolved = frame.resolved
    if resolved.unit is not WindowFrameUnit.ROWS:
        raise ValueError("ROWS interval evaluation requires ROWS frame semantics")
    assert resolved.start is not None
    assert resolved.end is not None
    raw_start = _rows_frame_bound_position(
        resolved.start,
        partition_size=partition_size,
        current_position=current_position,
    )
    raw_end = _rows_frame_bound_position(
        resolved.end,
        partition_size=partition_size,
        current_position=current_position,
    )
    return RowsFramePositionInterval(
        partition_size=partition_size,
        start=min(max(raw_start, 0), partition_size),
        stop=min(max(raw_end + 1, 0), partition_size),
    )


def _rows_frame_bound_position(
    bound: WindowFrameBound,
    *,
    partition_size: int,
    current_position: int,
) -> int:
    if bound.kind is WindowFrameBoundKind.UNBOUNDED_PRECEDING:
        return 0
    if bound.kind is WindowFrameBoundKind.CURRENT_ROW:
        return current_position
    if bound.kind is WindowFrameBoundKind.UNBOUNDED_FOLLOWING:
        return partition_size - 1

    offset = bound.offset
    if (
        type(offset) is not LiteralExpr
        or type(offset.value) is not int
        or offset.value < 0
    ):
        raise ValueError("ROWS offsets require nonnegative integer literal evidence")
    if bound.kind is WindowFrameBoundKind.OFFSET_PRECEDING:
        return current_position - offset.value
    if bound.kind is WindowFrameBoundKind.OFFSET_FOLLOWING:
        return current_position + offset.value
    raise AssertionError("validated ROWS bound kind must be complete")


class RangeOrderDirection(StrEnum):
    """Resolved ordering directions relevant to RANGE offset orientation."""

    ASC = "asc"
    DESC = "desc"


class RangeOffsetOrientation(StrEnum):
    """Logical movement in the ordering-value domain without arithmetic."""

    LOWER_ORDERING_VALUES = "lower_ordering_values"
    HIGHER_ORDERING_VALUES = "higher_ordering_values"


class RangeFrameBoundRole(StrEnum):
    """Whether one logical RANGE request supplies the start or end bound."""

    START = "start"
    END = "end"


class RangePeerBoundaryKind(StrEnum):
    """Peer boundary required by RANGE CURRENT ROW for one bound role."""

    FIRST_PEER = "first_peer"
    LAST_PEER = "last_peer"


@dataclass(frozen=True, slots=True, kw_only=True)
class RangeOffsetArithmeticRequirement:
    """Unresolved Phase 64 request retaining exact RANGE ordering evidence."""

    role: RangeFrameBoundRole
    bound: WindowFrameBound
    ordering: OrderItem
    direction: RangeOrderDirection
    orientation: RangeOffsetOrientation

    def __post_init__(self) -> None:
        if type(self.role) is not RangeFrameBoundRole:
            raise TypeError("RANGE offset role must be exact")
        if type(self.bound) is not WindowFrameBound:
            raise TypeError("RANGE offset bound must be exact")
        if self.bound.kind not in {
            WindowFrameBoundKind.OFFSET_PRECEDING,
            WindowFrameBoundKind.OFFSET_FOLLOWING,
        }:
            raise ValueError("RANGE arithmetic requirements need an offset bound")
        if type(self.ordering) is not OrderItem:
            raise TypeError("RANGE offset ordering must be exact")
        if type(self.direction) is not RangeOrderDirection:
            raise TypeError("RANGE offset direction must be exact")
        if type(self.orientation) is not RangeOffsetOrientation:
            raise TypeError("RANGE offset orientation must be exact")
        if self.direction is not _range_order_direction(self.ordering):
            raise ValueError("RANGE offset direction must match resolved ordering")
        if self.orientation is not _range_offset_orientation(
            self.bound.kind,
            self.direction,
        ):
            raise ValueError("RANGE offset orientation must match bound and direction")

    @property
    def offset_expression(self) -> Expression:
        """Return the exact authored offset expression for Phase 64 evidence."""

        assert self.bound.offset is not None
        return self.bound.offset

    @property
    def ordering_expression(self) -> Expression:
        """Return the exact resolved ordering expression for Phase 64 evidence."""

        return self.ordering.expression


@dataclass(frozen=True, slots=True, kw_only=True)
class RangeFrameLogicalView:
    """Lazy RANGE boundary request without peer comparison or typed arithmetic."""

    specification: ValidatedWindowSpecification
    offset_requirements: tuple[RangeOffsetArithmeticRequirement, ...]

    def __post_init__(self) -> None:
        _require_range_specification(self.specification)
        if type(self.offset_requirements) is not tuple or any(
            type(item) is not RangeOffsetArithmeticRequirement
            for item in self.offset_requirements
        ):
            raise TypeError("RANGE offset requirements must be an exact typed tuple")
        expected = _range_offset_requirements(self.specification)
        if self.offset_requirements != expected:
            raise ValueError("RANGE offset requirements must be complete and ordered")

    @property
    def frame(self) -> ValidatedFrame:
        """Return the exact validated RANGE frame."""

        frame = self.specification.frame
        assert type(frame) is ValidatedFrame
        return frame

    @property
    def order_by(self) -> tuple[OrderItem, ...]:
        """Return complete resolved ordering evidence without winner selection."""

        return self.specification.resolved.order_by

    @property
    def start_peer_boundary(self) -> RangePeerBoundaryKind | None:
        """Return RANGE CURRENT ROW start peer authority when required."""

        assert self.frame.resolved.start is not None
        if self.frame.resolved.start.kind is WindowFrameBoundKind.CURRENT_ROW:
            return RangePeerBoundaryKind.FIRST_PEER
        return None

    @property
    def end_peer_boundary(self) -> RangePeerBoundaryKind | None:
        """Return RANGE CURRENT ROW end peer authority when required."""

        assert self.frame.resolved.end is not None
        if self.frame.resolved.end.kind is WindowFrameBoundKind.CURRENT_ROW:
            return RangePeerBoundaryKind.LAST_PEER
        return None

    @property
    def requires_phase64_arithmetic(self) -> bool:
        """Whether unresolved offset/order compatibility evidence is required."""

        return bool(self.offset_requirements)

    @property
    def requires_whole_partition_peer_evidence(self) -> bool:
        """Whether no ordering makes the entire partition one peer group."""

        return not self.order_by


@dataclass(frozen=True, slots=True, kw_only=True)
class RangeOffsetOrderingFailure:
    """Typed failure when offset RANGE lacks exactly one ordering key."""

    specification: ValidatedWindowSpecification
    order_key_count: int

    def __post_init__(self) -> None:
        _require_range_specification(self.specification)
        if type(self.order_key_count) is not int:
            raise TypeError("RANGE order-key count must be an exact integer")
        actual = len(self.specification.resolved.order_by)
        if self.order_key_count != actual:
            raise ValueError("RANGE order-key failure must retain the exact count")
        if actual == 1 or not _range_offset_bounds(self.specification):
            raise ValueError(
                "RANGE order-key failure requires offset bounds and 0 or 2+ keys"
            )


class PeerComparisonOutcome(StrEnum):
    """Typed Phase 64 comparison evidence consumed by peer semantics."""

    EQUAL = "equal"
    NOT_EQUAL = "not_equal"
    UNRESOLVED = "unresolved"


@dataclass(frozen=True, slots=True, kw_only=True)
class PeerComparisonEvidence:
    """One adjacent-row comparison for one exact window ordering key."""

    left_row_position: int
    right_row_position: int
    order_key_position: int
    ordering: OrderItem
    outcome: PeerComparisonOutcome

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (
                self.left_row_position,
                self.right_row_position,
                self.order_key_position,
            )
        ):
            raise TypeError("peer comparison positions must be exact integers")
        if self.left_row_position < 0 or self.order_key_position < 0:
            raise ValueError("peer comparison positions must be nonnegative")
        if self.right_row_position != self.left_row_position + 1:
            raise ValueError("peer comparison rows must be adjacent")
        if type(self.ordering) is not OrderItem:
            raise TypeError("peer comparison ordering must be exact")
        if type(self.outcome) is not PeerComparisonOutcome:
            raise TypeError("peer comparison outcome must be exact")


@dataclass(frozen=True, slots=True, kw_only=True)
class PeerGroupInterval:
    """One maximal nonempty half-open peer-group span."""

    group_index: int
    start: int
    stop: int

    def __post_init__(self) -> None:
        if any(
            type(value) is not int
            for value in (self.group_index, self.start, self.stop)
        ):
            raise TypeError("peer-group positions must be exact integers")
        if self.group_index < 0 or self.start < 0 or self.stop <= self.start:
            raise ValueError("peer groups require nonnegative index and nonempty span")

    @property
    def positions(self) -> range:
        """Return the lazy row-position view preserving multiplicity."""

        return range(self.start, self.stop)


@dataclass(frozen=True, slots=True, kw_only=True)
class PeerGroupPartition:
    """Canonical ordered peer groups derived only from typed comparisons."""

    partition_size: int
    order_by: tuple[OrderItem, ...]
    comparisons: tuple[PeerComparisonEvidence, ...]
    groups: tuple[PeerGroupInterval, ...]

    def __post_init__(self) -> None:
        _validate_peer_inputs(self.partition_size, self.order_by, self.comparisons)
        if type(self.groups) is not tuple or any(
            type(group) is not PeerGroupInterval for group in self.groups
        ):
            raise TypeError("peer groups must be an exact typed tuple")
        if _blocking_unresolved_peer_comparisons(self.order_by, self.comparisons):
            raise ValueError(
                "resolved peer groups forbid blocking unresolved comparisons"
            )
        expected = _peer_groups_from_comparisons(
            self.partition_size,
            self.order_by,
            self.comparisons,
        )
        if self.groups != expected:
            raise ValueError("peer groups must be complete, maximal, and ordered")

    def group_for_position(self, position: int) -> PeerGroupInterval:
        """Return the sole canonical group containing one current row."""

        if type(position) is not int:
            raise TypeError("peer lookup position must be an exact integer")
        if not 0 <= position < self.partition_size:
            raise ValueError("peer lookup position must belong to the partition")
        return next(group for group in self.groups if position in group.positions)


@dataclass(frozen=True, slots=True, kw_only=True)
class PeerGroupConstructionFailure:
    """Complete unresolved comparison evidence with no partial peer groups."""

    partition_size: int
    order_by: tuple[OrderItem, ...]
    comparisons: tuple[PeerComparisonEvidence, ...]
    unresolved: tuple[PeerComparisonEvidence, ...]

    def __post_init__(self) -> None:
        _validate_peer_inputs(self.partition_size, self.order_by, self.comparisons)
        if type(self.unresolved) is not tuple or any(
            type(item) is not PeerComparisonEvidence for item in self.unresolved
        ):
            raise TypeError("unresolved peer evidence must be an exact typed tuple")
        expected = _blocking_unresolved_peer_comparisons(
            self.order_by,
            self.comparisons,
        )
        if not expected or self.unresolved != expected:
            raise ValueError("unresolved peer evidence must be complete and ordered")


def build_peer_group_partition(
    *,
    partition_size: int,
    order_by: tuple[OrderItem, ...],
    comparisons: tuple[PeerComparisonEvidence, ...],
) -> PeerGroupPartition | PeerGroupConstructionFailure:
    """Build maximal contiguous groups without evaluating ordering values."""

    _validate_peer_inputs(partition_size, order_by, comparisons)
    unresolved = _blocking_unresolved_peer_comparisons(order_by, comparisons)
    if unresolved:
        return PeerGroupConstructionFailure(
            partition_size=partition_size,
            order_by=order_by,
            comparisons=comparisons,
            unresolved=unresolved,
        )
    return PeerGroupPartition(
        partition_size=partition_size,
        order_by=order_by,
        comparisons=comparisons,
        groups=_peer_groups_from_comparisons(partition_size, order_by, comparisons),
    )


def _validate_peer_inputs(
    partition_size: int,
    order_by: tuple[OrderItem, ...],
    comparisons: tuple[PeerComparisonEvidence, ...],
) -> None:
    if type(partition_size) is not int:
        raise TypeError("peer partition size must be an exact integer")
    if partition_size <= 0:
        raise ValueError("peer partition size must be positive")
    if type(order_by) is not tuple or any(
        type(item) is not OrderItem for item in order_by
    ):
        raise TypeError("peer ordering must be an exact OrderItem tuple")
    if type(comparisons) is not tuple or any(
        type(item) is not PeerComparisonEvidence for item in comparisons
    ):
        raise TypeError("peer comparisons must be an exact typed tuple")
    expected_count = (partition_size - 1) * len(order_by)
    if len(comparisons) != expected_count:
        raise ValueError("peer comparisons must cover every adjacent row and key")
    for left_position in range(partition_size - 1):
        for key_position, ordering in enumerate(order_by):
            comparison = comparisons[left_position * len(order_by) + key_position]
            if (
                comparison.left_row_position != left_position
                or comparison.right_row_position != left_position + 1
                or comparison.order_key_position != key_position
                or comparison.ordering is not ordering
            ):
                raise ValueError(
                    "peer comparisons must preserve adjacent-row and complete-key order"
                )


def _blocking_unresolved_peer_comparisons(
    order_by: tuple[OrderItem, ...],
    comparisons: tuple[PeerComparisonEvidence, ...],
) -> tuple[PeerComparisonEvidence, ...]:
    if not order_by:
        return ()
    blocking: list[PeerComparisonEvidence] = []
    for left_position in range(len(comparisons) // len(order_by)):
        pair = comparisons[
            left_position * len(order_by) : (left_position + 1) * len(order_by)
        ]
        if any(
            comparison.outcome is PeerComparisonOutcome.NOT_EQUAL for comparison in pair
        ):
            continue
        blocking.extend(
            comparison
            for comparison in pair
            if comparison.outcome is PeerComparisonOutcome.UNRESOLVED
        )
    return tuple(blocking)


def _peer_groups_from_comparisons(
    partition_size: int,
    order_by: tuple[OrderItem, ...],
    comparisons: tuple[PeerComparisonEvidence, ...],
) -> tuple[PeerGroupInterval, ...]:
    boundaries = [0]
    if order_by:
        for left_position in range(partition_size - 1):
            pair = comparisons[
                left_position * len(order_by) : (left_position + 1) * len(order_by)
            ]
            if any(
                comparison.outcome is PeerComparisonOutcome.NOT_EQUAL
                for comparison in pair
            ):
                boundaries.append(left_position + 1)
            elif any(
                comparison.outcome is PeerComparisonOutcome.UNRESOLVED
                for comparison in pair
            ):
                raise ValueError("resolved peer groups require complete comparisons")
    boundaries.append(partition_size)
    return tuple(
        PeerGroupInterval(group_index=index, start=start, stop=stop)
        for index, (start, stop) in enumerate(zip(boundaries, boundaries[1:]))
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ExcludedFrameMembershipView:
    """Lazy post-clipping frame membership after one exact exclusion."""

    specification: ValidatedWindowSpecification
    partition_size: int
    base_positions: range
    current_position: int
    peers: PeerGroupPartition | None
    spans: tuple[range, ...]

    def __post_init__(self) -> None:
        _validate_frame_exclusion_base(
            self.specification,
            partition_size=self.partition_size,
            base_positions=self.base_positions,
            current_position=self.current_position,
        )
        exclusion = _validated_frame_exclusion(self.specification)
        if exclusion in {WindowFrameExclusion.GROUP, WindowFrameExclusion.TIES}:
            if type(self.peers) is not PeerGroupPartition:
                raise TypeError("GROUP and TIES require canonical peer authority")
            _require_matching_peer_authority(
                self.specification,
                partition_size=self.partition_size,
                authority=self.peers,
            )
        elif self.peers is not None:
            raise ValueError("NO OTHERS and CURRENT ROW forbid unused peer authority")
        if type(self.spans) is not tuple or any(
            type(span) is not range or span.step != 1 for span in self.spans
        ):
            raise TypeError("excluded frame spans must be an exact unit-range tuple")
        expected = _excluded_frame_spans(
            self.base_positions,
            current_position=self.current_position,
            exclusion=exclusion,
            peers=self.peers,
        )
        if self.spans != expected:
            raise ValueError(
                "excluded frame spans must be complete, ordered, and exact"
            )

    @property
    def frame(self) -> ValidatedFrame:
        """Return the unchanged validated frame evidence."""

        frame = self.specification.frame
        assert type(frame) is ValidatedFrame
        return frame

    @property
    def current_peer_group(self) -> PeerGroupInterval | None:
        """Return the canonical current group only when exclusion needs peers."""

        if self.peers is None:
            return None
        return self.peers.group_for_position(self.current_position)

    @property
    def positions(self) -> Iterator[int]:
        """Iterate retained physical positions without materializing rows."""

        return chain.from_iterable(self.spans)

    @property
    def empty(self) -> bool:
        """Whether exclusion removed every clipped base-frame position."""

        return not self.spans


def exclude_frame_membership(
    specification: ValidatedWindowSpecification,
    *,
    partition_size: int,
    base_positions: range,
    current_position: int,
    peer_authority: PeerGroupPartition | PeerGroupConstructionFailure | None = None,
) -> ExcludedFrameMembershipView | PeerGroupConstructionFailure:
    """Apply exclusion to one already clipped contiguous base-frame span."""

    _validate_frame_exclusion_base(
        specification,
        partition_size=partition_size,
        base_positions=base_positions,
        current_position=current_position,
    )
    if peer_authority is not None and type(peer_authority) not in {
        PeerGroupPartition,
        PeerGroupConstructionFailure,
    }:
        raise TypeError("frame exclusion peer authority must be exact or absent")

    exclusion = _validated_frame_exclusion(specification)
    peers: PeerGroupPartition | None = None
    if exclusion in {WindowFrameExclusion.GROUP, WindowFrameExclusion.TIES}:
        if peer_authority is None:
            raise TypeError("GROUP and TIES require canonical peer authority")
        _require_matching_peer_authority(
            specification,
            partition_size=partition_size,
            authority=peer_authority,
        )
        if type(peer_authority) is PeerGroupConstructionFailure:
            return peer_authority
        assert type(peer_authority) is PeerGroupPartition
        peers = peer_authority

    return ExcludedFrameMembershipView(
        specification=specification,
        partition_size=partition_size,
        base_positions=base_positions,
        current_position=current_position,
        peers=peers,
        spans=_excluded_frame_spans(
            base_positions,
            current_position=current_position,
            exclusion=exclusion,
            peers=peers,
        ),
    )


def _validate_frame_exclusion_base(
    specification: ValidatedWindowSpecification,
    *,
    partition_size: int,
    base_positions: range,
    current_position: int,
) -> None:
    if type(specification) is not ValidatedWindowSpecification:
        raise TypeError("frame exclusion requires an exact validated specification")
    if type(specification.frame) is not ValidatedFrame:
        raise ValueError("frame exclusion requires applicable frame semantics")
    if type(partition_size) is not int:
        raise TypeError("frame exclusion partition size must be an exact integer")
    if partition_size <= 0:
        raise ValueError("frame exclusion partition size must be positive")
    if type(base_positions) is not range or base_positions.step != 1:
        raise TypeError("frame exclusion base positions must be one exact unit range")
    if not 0 <= base_positions.start <= partition_size or not (
        0 <= base_positions.stop <= partition_size
    ):
        raise ValueError("frame exclusion base span must use partition boundaries")
    if type(current_position) is not int:
        raise TypeError("frame exclusion current position must be an exact integer")
    if not 0 <= current_position < partition_size:
        raise ValueError(
            "frame exclusion current position must belong to the partition"
        )


def _validated_frame_exclusion(
    specification: ValidatedWindowSpecification,
) -> WindowFrameExclusion:
    frame = specification.frame
    assert type(frame) is ValidatedFrame
    exclusion = frame.resolved.exclusion
    assert type(exclusion) is WindowFrameExclusion
    return exclusion


def _require_matching_peer_authority(
    specification: ValidatedWindowSpecification,
    *,
    partition_size: int,
    authority: PeerGroupPartition | PeerGroupConstructionFailure,
) -> None:
    if authority.partition_size != partition_size:
        raise ValueError("frame exclusion and peers must use the same partition size")
    if authority.order_by is not specification.resolved.order_by:
        raise ValueError("frame exclusion and peers must share exact ordering evidence")


def _excluded_frame_spans(
    base_positions: range,
    *,
    current_position: int,
    exclusion: WindowFrameExclusion,
    peers: PeerGroupPartition | None,
) -> tuple[range, ...]:
    if exclusion is WindowFrameExclusion.NO_OTHERS:
        return (base_positions,) if base_positions else ()
    if exclusion is WindowFrameExclusion.CURRENT_ROW:
        return _subtract_position_span(
            base_positions,
            current_position,
            current_position + 1,
        )

    assert peers is not None
    group = peers.group_for_position(current_position)
    if exclusion is WindowFrameExclusion.GROUP:
        return _subtract_position_span(base_positions, group.start, group.stop)

    spans = _subtract_position_span(base_positions, group.start, current_position)
    return tuple(
        retained
        for span in spans
        for retained in _subtract_position_span(span, current_position + 1, group.stop)
    )


def _subtract_position_span(
    base_positions: range,
    removed_start: int,
    removed_stop: int,
) -> tuple[range, ...]:
    if not base_positions:
        return ()
    cut_start = max(base_positions.start, removed_start)
    cut_stop = min(base_positions.stop, removed_stop)
    if cut_start >= cut_stop:
        return (base_positions,)
    return tuple(
        span
        for span in (
            range(base_positions.start, cut_start),
            range(cut_stop, base_positions.stop),
        )
        if span
    )


def range_frame_logical_view(
    specification: ValidatedWindowSpecification,
) -> RangeFrameLogicalView | RangeOffsetOrderingFailure:
    """Build one RANGE request or fail its offset ordering cardinality rule."""

    _require_range_specification(specification)
    order_key_count = len(specification.resolved.order_by)
    if _range_offset_bounds(specification) and order_key_count != 1:
        return RangeOffsetOrderingFailure(
            specification=specification,
            order_key_count=order_key_count,
        )
    return RangeFrameLogicalView(
        specification=specification,
        offset_requirements=_range_offset_requirements(specification),
    )


def resolve_range_current_row_boundary(
    view: RangeFrameLogicalView,
    *,
    role: RangeFrameBoundRole,
    peers: PeerGroupPartition,
    current_position: int,
) -> int:
    """Resolve RANGE CURRENT ROW through the canonical peer-group authority."""

    if type(view) is not RangeFrameLogicalView:
        raise TypeError("RANGE peer resolution requires an exact logical view")
    if type(role) is not RangeFrameBoundRole:
        raise TypeError("RANGE peer resolution role must be exact")
    if type(peers) is not PeerGroupPartition:
        raise TypeError("RANGE peer resolution requires exact peer groups")
    if peers.order_by is not view.order_by:
        raise ValueError("RANGE and peer groups must share exact ordering evidence")
    bound = (
        view.frame.resolved.start
        if role is RangeFrameBoundRole.START
        else view.frame.resolved.end
    )
    assert bound is not None
    if bound.kind is not WindowFrameBoundKind.CURRENT_ROW:
        raise ValueError("RANGE peer resolution requires a CURRENT ROW bound")
    group = peers.group_for_position(current_position)
    if view.requires_whole_partition_peer_evidence and (
        len(peers.groups) != 1 or group.start != 0 or group.stop != peers.partition_size
    ):
        raise ValueError("unordered RANGE requires one whole-partition peer group")
    return group.start if role is RangeFrameBoundRole.START else group.stop - 1


def _require_range_specification(
    specification: ValidatedWindowSpecification,
) -> None:
    if type(specification) is not ValidatedWindowSpecification:
        raise TypeError("RANGE semantics require an exact validated specification")
    frame = specification.frame
    if type(frame) is not ValidatedFrame:
        raise ValueError("RANGE semantics require an applicable validated frame")
    if frame.resolved.unit is not WindowFrameUnit.RANGE:
        raise ValueError("RANGE semantics require a RANGE frame")


def _range_offset_bounds(
    specification: ValidatedWindowSpecification,
) -> tuple[tuple[RangeFrameBoundRole, WindowFrameBound], ...]:
    frame = specification.frame
    assert type(frame) is ValidatedFrame
    assert frame.resolved.start is not None
    assert frame.resolved.end is not None
    return tuple(
        (role, bound)
        for role, bound in (
            (RangeFrameBoundRole.START, frame.resolved.start),
            (RangeFrameBoundRole.END, frame.resolved.end),
        )
        if bound.kind
        in {
            WindowFrameBoundKind.OFFSET_PRECEDING,
            WindowFrameBoundKind.OFFSET_FOLLOWING,
        }
    )


def _range_offset_requirements(
    specification: ValidatedWindowSpecification,
) -> tuple[RangeOffsetArithmeticRequirement, ...]:
    offset_bounds = _range_offset_bounds(specification)
    if not offset_bounds:
        return ()
    order_by = specification.resolved.order_by
    if len(order_by) != 1:
        raise ValueError("offset RANGE requirements need exactly one ordering key")
    ordering = order_by[0]
    direction = _range_order_direction(ordering)
    return tuple(
        RangeOffsetArithmeticRequirement(
            role=role,
            bound=bound,
            ordering=ordering,
            direction=direction,
            orientation=_range_offset_orientation(bound.kind, direction),
        )
        for role, bound in offset_bounds
    )


def _range_order_direction(ordering: OrderItem) -> RangeOrderDirection:
    if ordering.direction is None or ordering.direction == "asc":
        return RangeOrderDirection.ASC
    if ordering.direction == "desc":
        return RangeOrderDirection.DESC
    raise ValueError("RANGE ordering direction must be omitted, asc, or desc")


def _range_offset_orientation(
    kind: WindowFrameBoundKind,
    direction: RangeOrderDirection,
) -> RangeOffsetOrientation:
    if (
        kind is WindowFrameBoundKind.OFFSET_PRECEDING
        and direction is RangeOrderDirection.ASC
    ) or (
        kind is WindowFrameBoundKind.OFFSET_FOLLOWING
        and direction is RangeOrderDirection.DESC
    ):
        return RangeOffsetOrientation.LOWER_ORDERING_VALUES
    if kind in {
        WindowFrameBoundKind.OFFSET_PRECEDING,
        WindowFrameBoundKind.OFFSET_FOLLOWING,
    }:
        return RangeOffsetOrientation.HIGHER_ORDERING_VALUES
    raise ValueError("RANGE orientation requires an offset bound")


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupsFrameLogicalView:
    """One validated GROUPS frame bound to canonical peer groups."""

    specification: ValidatedWindowSpecification
    peers: PeerGroupPartition

    def __post_init__(self) -> None:
        if type(self.specification) is not ValidatedWindowSpecification:
            raise TypeError("GROUPS semantics require an exact validated specification")
        frame = self.specification.frame
        if type(frame) is not ValidatedFrame:
            raise ValueError("GROUPS semantics require an applicable validated frame")
        if frame.resolved.unit is not WindowFrameUnit.GROUPS:
            raise ValueError("GROUPS semantics require a GROUPS frame")
        if type(self.peers) is not PeerGroupPartition:
            raise TypeError("GROUPS semantics require exact peer groups")
        if self.peers.order_by is not self.specification.resolved.order_by:
            raise ValueError(
                "GROUPS and peer groups must share exact ordering evidence"
            )

    @property
    def frame(self) -> ValidatedFrame:
        """Return the exact validated GROUPS frame."""

        frame = self.specification.frame
        assert type(frame) is ValidatedFrame
        return frame


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupsFrameInterval:
    """Lazy intersected GROUPS and contributed-row boundary view."""

    peers: PeerGroupPartition
    start_group: int
    stop_group: int

    def __post_init__(self) -> None:
        if type(self.peers) is not PeerGroupPartition:
            raise TypeError("GROUPS interval requires exact peer groups")
        if type(self.start_group) is not int or type(self.stop_group) is not int:
            raise TypeError("GROUPS interval bounds must be exact integers")
        if not 0 <= self.start_group <= self.group_count:
            raise ValueError("GROUPS interval start must be a group boundary")
        if not 0 <= self.stop_group <= self.group_count:
            raise ValueError("GROUPS interval stop must be a group boundary")

    @property
    def partition_size(self) -> int:
        """Return the exact canonical partition size."""

        return self.peers.partition_size

    @property
    def group_count(self) -> int:
        """Return the exact canonical peer-group count."""

        return len(self.peers.groups)

    @property
    def row_start(self) -> int:
        """Return the selected half-open row-start boundary."""

        return _peer_group_boundary_position(self.peers, self.start_group)

    @property
    def row_stop(self) -> int:
        """Return the selected half-open row-stop boundary."""

        return _peer_group_boundary_position(self.peers, self.stop_group)

    @property
    def group_indices(self) -> range:
        """Return selected group positions without materializing groups."""

        return range(self.start_group, self.stop_group)

    @property
    def row_positions(self) -> range:
        """Return every contributed row position without duplicating rows."""

        return range(self.row_start, self.row_stop)

    @property
    def empty(self) -> bool:
        """Whether the intersected group interval contains no groups."""

        return self.start_group >= self.stop_group


def groups_frame_interval(
    view: GroupsFrameLogicalView,
    *,
    current_position: int,
) -> GroupsFrameInterval:
    """Intersect one GROUPS request with canonical peer-group positions."""

    if type(view) is not GroupsFrameLogicalView:
        raise TypeError("GROUPS interval evaluation requires an exact logical view")
    current_group = view.peers.group_for_position(current_position)
    assert view.frame.resolved.start is not None
    assert view.frame.resolved.end is not None
    raw_start = _groups_frame_bound_index(
        view.frame.resolved.start,
        group_count=len(view.peers.groups),
        current_group_index=current_group.group_index,
    )
    raw_end = _groups_frame_bound_index(
        view.frame.resolved.end,
        group_count=len(view.peers.groups),
        current_group_index=current_group.group_index,
    )
    group_count = len(view.peers.groups)
    start_group = min(max(raw_start, 0), group_count)
    stop_group = min(max(raw_end + 1, 0), group_count)
    return GroupsFrameInterval(
        peers=view.peers,
        start_group=start_group,
        stop_group=stop_group,
    )


def _groups_frame_bound_index(
    bound: WindowFrameBound,
    *,
    group_count: int,
    current_group_index: int,
) -> int:
    if bound.kind is WindowFrameBoundKind.UNBOUNDED_PRECEDING:
        return 0
    if bound.kind is WindowFrameBoundKind.CURRENT_ROW:
        return current_group_index
    if bound.kind is WindowFrameBoundKind.UNBOUNDED_FOLLOWING:
        return group_count - 1
    offset = bound.offset
    if (
        type(offset) is not LiteralExpr
        or type(offset.value) is not int
        or offset.value < 0
    ):
        raise ValueError("GROUPS offsets require nonnegative integer literal evidence")
    if bound.kind is WindowFrameBoundKind.OFFSET_PRECEDING:
        return current_group_index - offset.value
    if bound.kind is WindowFrameBoundKind.OFFSET_FOLLOWING:
        return current_group_index + offset.value
    raise AssertionError("validated GROUPS bound kind must be complete")


def _peer_group_boundary_position(
    peers: PeerGroupPartition,
    boundary: int,
) -> int:
    if boundary == len(peers.groups):
        return peers.partition_size
    return peers.groups[boundary].start


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
class WindowComputationUnsupported:
    """Occurrence-neutral rejection for one authored window computation."""

    expression: WindowExpr
    identity: WindowFunctionIdentity
    reason: str

    def __post_init__(self) -> None:
        if type(self.expression) is not WindowExpr:
            raise TypeError("window computation expression must be exact")
        if type(self.identity) is not WindowFunctionIdentity:
            raise TypeError("window computation identity must be exact")
        if type(self.reason) is not str or not self.reason.strip():
            raise ValueError("window computation rejection requires a reason")
        if self.expression.identity != self.identity:
            raise ValueError("window computation identity must retain authorship")


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


class FrameValueFunctionKind(StrEnum):
    """Closed frame-relative value selection functions."""

    FIRST_VALUE = "first_value"
    LAST_VALUE = "last_value"
    NTH_VALUE = "nth_value"


@dataclass(frozen=True, slots=True, kw_only=True)
class NthValuePositionFact:
    """One exact positive integer literal position for nth_value."""

    expression: LiteralExpr
    effective_value: int

    def __post_init__(self) -> None:
        if type(self.expression) is not LiteralExpr:
            raise TypeError("nth_value position must be an exact literal")
        if (
            type(self.effective_value) is not int
            or self.effective_value < 1
            or type(self.expression.value) is not int
            or self.expression.value != self.effective_value
        ):
            raise ValueError("nth_value position must be its positive integer literal")


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameValueWindowComputation:
    """Occurrence-neutral frame-value signature and result evidence."""

    expression: WindowExpr
    function: FrameValueFunctionKind
    value_expression: NameExpr | DottedNameExpr | LiteralExpr
    value_type: ValueType
    position_fact: NthValuePositionFact | None
    modifiers: ResolvedWindowFunctionModifiers
    signature_match: SignatureMatch
    result: WindowResultAvailability

    def __post_init__(self) -> None:
        if type(self.expression) is not WindowExpr:
            raise TypeError("frame-value computation expression must be exact")
        if type(self.function) is not FrameValueFunctionKind:
            raise TypeError("frame-value computation function must be exact")
        if type(self.value_expression) not in {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
        }:
            raise TypeError("frame-value computation input must be bounded")
        if type(self.value_type) is not ValueType:
            raise TypeError("frame-value computation input type must be exact")
        if self.position_fact is not None and type(self.position_fact) is not (
            NthValuePositionFact
        ):
            raise TypeError("frame-value computation position must be exact")
        if type(self.modifiers) is not ResolvedWindowFunctionModifiers:
            raise TypeError("frame-value computation modifiers must be exact")
        if type(self.signature_match) is not SignatureMatch:
            raise TypeError("frame-value computation signature must be exact")
        if type(self.result) is not WindowResultAvailability:
            raise TypeError("frame-value computation result must be exact")
        arguments = self.expression.call.arguments
        if (
            self.expression.identity.name != self.function.value
            or self.modifiers.identity != self.expression.identity
            or self.modifiers.authored_null_treatment
            is not self.expression.null_treatment
            or self.modifiers.authored_nth_direction
            is not self.expression.nth_direction
            or self.value_expression is not arguments[0]
            or not self.expression.spec.order_by
        ):
            raise ValueError("frame-value computation must retain exact semantics")
        if self.function is FrameValueFunctionKind.NTH_VALUE:
            if (
                len(arguments) != 2
                or self.position_fact is None
                or self.position_fact.expression is not arguments[1]
            ):
                raise ValueError("nth_value computation requires its exact position")
        elif len(arguments) != 1 or self.position_fact is not None:
            raise ValueError("first/last computation forbids an nth position")
        if (
            self.result.kind is not WindowResultAvailabilityKind.CONCRETE
            or self.result.value_type is None
            or self.result.value_type.resolved_type is not self.value_type.resolved_type
            or self.result.value_type.resolved_type.name
            != self.signature_match.result_type.name
            or self.result.value_type.resolved_type.kind
            is not self.signature_match.result_type.kind
            or self.result.value_type.nullability is not EffectiveNullability.NULLABLE
        ):
            raise ValueError("frame-value computation result must be nullable T")


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameValueWindowSemanticFact:
    """One frame-sensitive value-function semantic result."""

    semantic_fact: WindowExpressionSemanticFact
    function: FrameValueFunctionKind
    value_expression: NameExpr | DottedNameExpr | LiteralExpr
    value_type: ValueType
    position_fact: NthValuePositionFact | None
    modifiers: ResolvedWindowFunctionModifiers
    signature_match: SignatureMatch

    def __post_init__(self) -> None:
        if type(self.semantic_fact) is not WindowExpressionSemanticFact:
            raise TypeError("frame-value semantic fact must retain an exact core")
        if type(self.function) is not FrameValueFunctionKind:
            raise TypeError("frame-value function kind must be exact")
        if type(self.value_expression) not in {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
        }:
            raise TypeError("frame-value input must be an exact bounded expression")
        if type(self.value_type) is not ValueType:
            raise TypeError("frame-value input type must be exact")
        if (
            self.position_fact is not None
            and type(self.position_fact) is not NthValuePositionFact
        ):
            raise TypeError("frame-value position fact must be exact or absent")
        if type(self.modifiers) is not ResolvedWindowFunctionModifiers:
            raise TypeError("frame-value modifiers must be exact")
        if type(self.signature_match) is not SignatureMatch:
            raise TypeError("frame-value signature match must be exact")

        expression = self.semantic_fact.expression
        arguments = expression.call.arguments
        if self.semantic_fact.identity.name != self.function.value:
            raise ValueError("frame-value function must match its identity")
        if self.modifiers.identity != self.semantic_fact.identity:
            raise ValueError("frame-value modifiers must match its identity")
        if (
            self.modifiers.authored_null_treatment is not expression.null_treatment
            or self.modifiers.authored_nth_direction is not expression.nth_direction
        ):
            raise ValueError("frame-value modifiers must retain exact authorship")
        if self.value_expression is not arguments[0]:
            raise ValueError("frame-value input must retain argument zero")
        if not expression.spec.order_by:
            raise ValueError("frame-value functions require resolved ordering")
        if self.function is FrameValueFunctionKind.NTH_VALUE:
            if (
                len(arguments) != 2
                or self.position_fact is None
                or self.position_fact.expression is not arguments[1]
            ):
                raise ValueError("nth_value requires its exact position fact")
        elif len(arguments) != 1 or self.position_fact is not None:
            raise ValueError("first_value and last_value forbid a position fact")
        result = self.semantic_fact.result
        if (
            result.kind is not WindowResultAvailabilityKind.CONCRETE
            or result.value_type is None
            or result.value_type.resolved_type is not self.value_type.resolved_type
            or result.value_type.resolved_type.name
            != self.signature_match.result_type.name
            or result.value_type.resolved_type.kind
            is not self.signature_match.result_type.kind
            or result.value_type.nullability is not EffectiveNullability.NULLABLE
        ):
            raise ValueError("frame-value result must be the nullable signature type")


@dataclass(frozen=True, slots=True, kw_only=True)
class FrameValueCandidateView:
    """Post-EXCLUDE candidate positions under one effective NULL treatment."""

    membership: ExcludedFrameMembershipView
    values: tuple[object, ...]
    null_treatment: WindowNullTreatment
    positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.membership) is not ExcludedFrameMembershipView:
            raise TypeError("frame-value candidates require exact membership")
        if type(self.values) is not tuple:
            raise TypeError("frame-value candidate values must be an exact tuple")
        if len(self.values) != self.membership.partition_size:
            raise ValueError("frame-value values must cover the exact partition")
        if type(self.null_treatment) is not WindowNullTreatment:
            raise TypeError("frame-value NULL treatment must be exact")
        if type(self.positions) is not tuple or any(
            type(position) is not int for position in self.positions
        ):
            raise TypeError("frame-value positions must be an exact integer tuple")
        expected = tuple(
            position
            for position in self.membership.positions
            if self.null_treatment is WindowNullTreatment.RESPECT_NULLS
            or self.values[position] is not None
        )
        if self.positions != expected:
            raise ValueError("frame-value positions must be the exact filtered view")


def frame_value_candidate_view(
    membership: ExcludedFrameMembershipView,
    values: tuple[object, ...],
    null_treatment: WindowNullTreatment,
) -> FrameValueCandidateView:
    """Filter only post-EXCLUDE value candidates, never frame membership."""

    if type(membership) is not ExcludedFrameMembershipView:
        raise TypeError("frame-value candidates require exact membership")
    if type(values) is not tuple or len(values) != membership.partition_size:
        raise ValueError("frame-value values must cover the exact partition")
    if type(null_treatment) is not WindowNullTreatment:
        raise TypeError("frame-value NULL treatment must be exact")
    return FrameValueCandidateView(
        membership=membership,
        values=values,
        null_treatment=null_treatment,
        positions=tuple(
            position
            for position in membership.positions
            if null_treatment is WindowNullTreatment.RESPECT_NULLS
            or values[position] is not None
        ),
    )


def select_frame_value_candidate(
    view: FrameValueCandidateView,
    function: FrameValueFunctionKind,
    *,
    nth_position: int | None = None,
    nth_direction: WindowNthDirection | None = None,
) -> int | None:
    """Select one physical candidate position or return no candidate."""

    if type(view) is not FrameValueCandidateView:
        raise TypeError("frame-value selection requires an exact candidate view")
    if type(function) is not FrameValueFunctionKind:
        raise TypeError("frame-value selection function must be exact")
    if function is FrameValueFunctionKind.FIRST_VALUE:
        if nth_position is not None or nth_direction is not None:
            raise ValueError("first_value forbids nth selection evidence")
        return view.positions[0] if view.positions else None
    if function is FrameValueFunctionKind.LAST_VALUE:
        if nth_position is not None or nth_direction is not None:
            raise ValueError("last_value forbids nth selection evidence")
        return view.positions[-1] if view.positions else None
    if type(nth_position) is not int or nth_position < 1:
        raise ValueError("nth_value selection requires a positive position")
    if type(nth_direction) is not WindowNthDirection:
        raise TypeError("nth_value selection requires an exact direction")
    if nth_position > len(view.positions):
        return None
    return (
        view.positions[nth_position - 1]
        if nth_direction is WindowNthDirection.FROM_FIRST
        else view.positions[-nth_position]
    )


class NavigationDirection(StrEnum):
    """Private source directions for offset-based navigation windows."""

    LAG = "lag"
    LEAD = "lead"


def navigation_candidate_position(
    values: tuple[object, ...],
    *,
    current_position: int,
    direction: NavigationDirection,
    offset: int,
    null_treatment: WindowNullTreatment,
) -> int | None:
    """Resolve one lag/lead physical candidate without changing its anchor."""

    if type(values) is not tuple:
        raise TypeError("navigation values must be an exact tuple")
    if type(current_position) is not int or not 0 <= current_position < len(values):
        raise ValueError("navigation current position must be inside the partition")
    if type(direction) is not NavigationDirection:
        raise TypeError("navigation direction must be exact")
    if type(offset) is not int or offset < 0:
        raise ValueError("navigation offset must be nonnegative")
    if type(null_treatment) is not WindowNullTreatment:
        raise TypeError("navigation NULL treatment must be exact")
    if offset == 0:
        return current_position

    step = -1 if direction is NavigationDirection.LAG else 1
    seen = 0
    position = current_position + step
    while 0 <= position < len(values):
        if (
            null_treatment is WindowNullTreatment.RESPECT_NULLS
            or values[position] is not None
        ):
            seen += 1
            if seen == offset:
                return position
        position += step
    return None


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
class NavigationWindowComputation:
    """Occurrence-neutral lag/lead signature and nullability evidence."""

    expression: WindowExpr
    direction: NavigationDirection
    value_expression: NameExpr | DottedNameExpr | LiteralExpr
    value_type: ValueType
    value_always_null: bool
    modifiers: ResolvedWindowFunctionModifiers
    offset_fact: NavigationOffsetFact
    default_fact: NavigationDefaultFact
    signature_match: SignatureMatch
    nullability_match: NullabilityEvaluationMatch
    result: WindowResultAvailability

    def __post_init__(self) -> None:
        if type(self.expression) is not WindowExpr:
            raise TypeError("navigation computation expression must be exact")
        if type(self.direction) is not NavigationDirection:
            raise TypeError("navigation computation direction must be exact")
        if type(self.value_expression) not in {
            NameExpr,
            DottedNameExpr,
            LiteralExpr,
        }:
            raise TypeError("navigation computation value must be bounded")
        if type(self.value_type) is not ValueType:
            raise TypeError("navigation computation value type must be exact")
        if type(self.value_always_null) is not bool:
            raise TypeError("navigation computation NULL evidence must be exact")
        if type(self.modifiers) is not ResolvedWindowFunctionModifiers:
            raise TypeError("navigation computation modifiers must be exact")
        if type(self.offset_fact) is not NavigationOffsetFact:
            raise TypeError("navigation computation offset must be exact")
        if type(self.default_fact) is not NavigationDefaultFact:
            raise TypeError("navigation computation default must be exact")
        if type(self.signature_match) is not SignatureMatch:
            raise TypeError("navigation computation signature must be exact")
        if type(self.nullability_match) is not NullabilityEvaluationMatch:
            raise TypeError("navigation computation nullability must be exact")
        if type(self.result) is not WindowResultAvailability:
            raise TypeError("navigation computation result must be exact")
        arguments = self.expression.call.arguments
        expression_is_null = (
            type(self.value_expression) is LiteralExpr
            and self.value_expression.value is None
        )
        if (
            self.expression.identity.name != self.direction.value
            or self.modifiers.identity != self.expression.identity
            or self.modifiers.authored_null_treatment
            is not self.expression.null_treatment
            or self.modifiers.authored_nth_direction
            is not self.expression.nth_direction
            or not self.expression.spec.order_by
            or len(arguments) not in {1, 2, 3}
            or self.value_expression is not arguments[0]
            or self.value_always_null is not expression_is_null
        ):
            raise ValueError("navigation computation must retain exact semantics")
        if len(arguments) == 1:
            if not self.offset_fact.omitted or not self.default_fact.omitted:
                raise ValueError("one-argument navigation must omit offset and default")
        else:
            if self.offset_fact.expression is not arguments[1]:
                raise ValueError("navigation offset must retain argument one")
            if len(arguments) == 2 and not self.default_fact.omitted:
                raise ValueError("two-argument navigation must omit default")
            if len(arguments) == 3 and self.default_fact.expression is not arguments[2]:
                raise ValueError("navigation default must retain argument two")
        if self.signature_match.omitted_positions != tuple(range(len(arguments), 3)):
            raise ValueError("navigation signature omission must match source arity")
        if (
            self.result.kind is not WindowResultAvailabilityKind.CONCRETE
            or self.result.value_type is None
            or self.result.value_type.resolved_type.name
            != self.signature_match.result_type.name
            or self.result.value_type.resolved_type.kind
            is not self.signature_match.result_type.kind
            or self.result.value_type.nullability is not self.nullability_match.value
        ):
            raise ValueError("navigation computation result must match its formulas")


@dataclass(frozen=True, slots=True, kw_only=True)
class NavigationWindowSemanticFact:
    """Private sibling navigation evidence for one core window semantic fact."""

    semantic_fact: WindowExpressionSemanticFact
    direction: NavigationDirection
    value_expression: NameExpr | DottedNameExpr | LiteralExpr
    value_type: ValueType
    value_always_null: bool
    modifiers: ResolvedWindowFunctionModifiers
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
        if type(self.modifiers) is not ResolvedWindowFunctionModifiers:
            raise TypeError("navigation modifiers must be exact")
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
        if (
            self.modifiers.identity != self.semantic_fact.identity
            or self.modifiers.null_treatment is None
            or self.modifiers.nth_direction is not None
        ):
            raise ValueError("navigation modifiers must match lag/lead policy")
        if (
            self.modifiers.authored_null_treatment is not expression.null_treatment
            or self.modifiers.authored_nth_direction is not expression.nth_direction
        ):
            raise ValueError("navigation modifiers must retain exact authorship")
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
class WindowComputationAnalysis:
    """Occurrence-neutral semantic result shared by selected and hidden sites."""

    expression: WindowExpr
    result: WindowResultAvailability
    modifiers: ResolvedWindowFunctionModifiers
    ranking_advance_policy: RankingAdvancePolicy | None
    distribution_policy: DistributionWindowPolicy | None
    bucket_count: int | None
    partition_bindings: tuple[WindowPartitionFieldBinding, ...]
    order_bindings: tuple[WindowOrderFieldBinding, ...]
    validated_specification: ValidatedWindowSpecification
    navigation: NavigationWindowComputation | None = None
    frame_value: FrameValueWindowComputation | None = None
    resolved_named_use: ResolvedNamedWindowUse | None = None

    def __post_init__(self) -> None:
        if type(self.expression) is not WindowExpr:
            raise TypeError("window computation expression must be exact")
        if type(self.result) is not WindowResultAvailability or (
            self.result.kind is not WindowResultAvailabilityKind.CONCRETE
        ):
            raise ValueError("window computation result must be concrete")
        if type(self.modifiers) is not ResolvedWindowFunctionModifiers or (
            self.modifiers.identity != self.expression.identity
        ):
            raise ValueError("window computation modifiers must match its identity")
        if (
            self.ranking_advance_policy is not None
            and type(self.ranking_advance_policy) is not RankingAdvancePolicy
        ):
            raise TypeError("window ranking policy must be exact or absent")
        if (
            self.distribution_policy is not None
            and type(self.distribution_policy) is not DistributionWindowPolicy
        ):
            raise TypeError("window distribution policy must be exact or absent")
        if self.bucket_count is not None and type(self.bucket_count) is not int:
            raise TypeError("window bucket count must be exact or absent")
        if type(self.partition_bindings) is not tuple or any(
            type(item) is not WindowPartitionFieldBinding
            for item in self.partition_bindings
        ):
            raise TypeError("window partition bindings must be exact")
        if (
            type(self.order_bindings) is not tuple
            or not self.order_bindings
            or any(
                type(item) is not WindowOrderFieldBinding
                for item in self.order_bindings
            )
        ):
            raise ValueError("window order bindings must be a nonempty exact tuple")
        if tuple(item.expression for item in self.partition_bindings) != (
            self.expression.spec.partition_by
        ) or tuple(item.order_item for item in self.order_bindings) != (
            self.expression.spec.order_by
        ):
            raise ValueError("window bindings must retain the effective specification")
        if type(self.validated_specification) is not ValidatedWindowSpecification or (
            self.validated_specification.function_identity != self.expression.identity
            or self.validated_specification.argument_expressions
            is not self.expression.call.arguments
        ):
            raise ValueError("window validation must retain the exact computation")
        if self.navigation is not None and type(self.navigation) is not (
            NavigationWindowComputation
        ):
            raise TypeError("window navigation computation must be exact or absent")
        if self.frame_value is not None and type(self.frame_value) is not (
            FrameValueWindowComputation
        ):
            raise TypeError("window frame-value computation must be exact or absent")
        for family in (self.navigation, self.frame_value):
            if family is not None and (
                family.expression is not self.expression
                or family.result is not self.result
            ):
                raise ValueError("window family computation must share the common core")
        if self.resolved_named_use is None:
            if self.expression.use_kind is not WindowUseKind.INLINE:
                raise ValueError("standalone computation requires inline authorship")
        else:
            authored = self.resolved_named_use.composed.expression
            if (
                authored.use_kind is WindowUseKind.INLINE
                or self.resolved_named_use.function_identity != self.expression.identity
                or self.resolved_named_use.resolved
                is not self.validated_specification.resolved
                or self.expression.call is not authored.call
                or self.expression.span != authored.span
            ):
                raise ValueError("named computation must retain exact authorship")

    @property
    def authored_expression(self) -> WindowExpr:
        """Return the exact authored expression for this computation."""

        if self.resolved_named_use is None:
            return self.expression
        return self.resolved_named_use.composed.expression


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpressionAnalysis:
    """One core fact joined to its family and partition sibling evidence."""

    semantic_fact: WindowExpressionSemanticFact
    ranking_fact: RankingWindowSemanticFact | None
    distribution_fact: DistributionWindowSemanticFact | None
    partition_binding_fact: WindowPartitionBindingFact
    order_binding_fact: WindowOrderBindingFact
    validated_specification: ValidatedWindowSpecification
    navigation_fact: NavigationWindowSemanticFact | None = None
    frame_value_fact: FrameValueWindowSemanticFact | None = None
    resolved_named_use: ResolvedNamedWindowUse | None = None

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
        if type(self.validated_specification) is not ValidatedWindowSpecification:
            raise TypeError("validated window specification must be exact")
        if (
            self.validated_specification.function_identity
            != self.semantic_fact.identity
        ):
            raise ValueError("validated window specification must match the identity")
        expression = self.semantic_fact.expression
        if self.validated_specification.argument_expressions is not (
            expression.call.arguments
        ):
            raise ValueError("validated arguments must retain the exact window use")
        authored = self.validated_specification.resolved.authored
        if authored.span == expression.spec.span:
            if (
                authored.partition_by is not expression.spec.partition_by
                or authored.order_by is not expression.spec.order_by
                or authored.frame is not expression.spec.frame
            ):
                raise ValueError(
                    "validated inline specification must retain exact authorship"
                )
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
            self.frame_value_fact is not None
            and type(self.frame_value_fact) is not FrameValueWindowSemanticFact
        ):
            raise TypeError(
                "frame_value_fact must be an exact FrameValueWindowSemanticFact or None"
            )
        if (
            self.frame_value_fact is not None
            and self.frame_value_fact.semantic_fact is not self.semantic_fact
        ):
            raise ValueError("frame-value fact must share the semantic core")
        if (
            self.resolved_named_use is not None
            and type(self.resolved_named_use) is not ResolvedNamedWindowUse
        ):
            raise TypeError("resolved named use must be exact or absent")
        if self.resolved_named_use is None:
            if expression.use_kind is not WindowUseKind.INLINE:
                raise ValueError("inline analysis requires inline effective authorship")
        else:
            named = self.resolved_named_use
            authored_expression = named.composed.expression
            if (
                authored_expression.use_kind is WindowUseKind.INLINE
                or named.function_identity != self.semantic_fact.identity
                or named.resolved is not self.validated_specification.resolved
                or expression.call is not authored_expression.call
                or expression.nth_direction is not authored_expression.nth_direction
                or expression.null_treatment is not authored_expression.null_treatment
                or self.semantic_fact.occurrence.span != authored_expression.span
            ):
                raise ValueError(
                    "named analysis must retain exact authored and resolved authority"
                )
        if (
            self.ranking_fact is None
            and self.distribution_fact is None
            and self.navigation_fact is None
            and self.frame_value_fact is None
        ):
            raise ValueError("window analysis requires a family fact")

        identity_name = self.semantic_fact.identity.name
        frame_sensitive = identity_name in {
            "first_value",
            "last_value",
            "nth_value",
        }
        if frame_sensitive:
            if (
                type(self.validated_specification.frame) is not ValidatedFrame
                or self.validated_specification.function_policy.kind
                is not WindowFunctionFramePolicyKind.FRAME_SENSITIVE
            ):
                raise ValueError(
                    "frame-value identity requires applicable frame policy"
                )
        elif (
            type(self.validated_specification.frame) is not ValidatedFrameNotApplicable
            or self.validated_specification.function_policy.kind
            is not WindowFunctionFramePolicyKind.FRAME_INSENSITIVE_EXPLICIT_FORBIDDEN
        ):
            raise ValueError(
                "frame-insensitive identity requires absent frame semantics"
            )
        if identity_name in {"row_number", "rank", "dense_rank"}:
            if (
                self.ranking_fact is None
                or self.distribution_fact is not None
                or self.navigation_fact is not None
                or self.frame_value_fact is not None
            ):
                raise ValueError("ranking identity requires only a ranking fact")
            return
        if identity_name == "percent_rank":
            if (
                self.ranking_fact is None
                or self.distribution_fact is None
                or self.navigation_fact is not None
                or self.frame_value_fact is not None
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
                or self.frame_value_fact is not None
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
                or self.frame_value_fact is not None
            ):
                raise ValueError("navigation identity requires only a navigation fact")
            return
        if identity_name in {"first_value", "last_value", "nth_value"}:
            if (
                self.ranking_fact is not None
                or self.distribution_fact is not None
                or self.navigation_fact is not None
                or self.frame_value_fact is None
            ):
                raise ValueError("frame-value identity requires only its family fact")
            return
        raise ValueError("window analysis identity must be one completed identity")

    @property
    def authored_expression(self) -> WindowExpr:
        """Return the exact parsed use, never the transient effective expression."""

        if self.resolved_named_use is None:
            return self.semantic_fact.expression
        return self.resolved_named_use.composed.expression
