"""Immutable public models for Pietto Semantic IR."""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass, replace
from enum import StrEnum

from pietto.errors import Diagnostic

StaticValue = str | int | float | bool | None


class SymbolNamespace(StrEnum):
    """Semantic namespaces used to form stable IR symbol identities."""

    TYPE = "type"
    CALLABLE = "callable"
    RELATION = "relation"


class TypeKindIR(StrEnum):
    """Type declaration kinds copied from resolved semantic facts."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type_alias"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"


class NullabilityIR(StrEnum):
    """Effective nullability preserved independently from parser syntax."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SourceSpan:
    """A parser-independent, 1-based, half-open source range."""

    path: str | None
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True)
class SymbolId:
    """A stable resolved symbol identity within one semantic namespace."""

    namespace: SymbolNamespace
    name: str


@dataclass(frozen=True, slots=True)
class FieldId:
    """A stable field identity within an optional owning semantic symbol."""

    owner: SymbolId | None
    name: str
    input: int | None = None  # input ordinal in a JOIN relation, else None


@dataclass(frozen=True, slots=True)
class TypeRefIR:
    """Declared and canonical type metadata copied from semantic analysis."""

    symbol: SymbolId | None
    canonical_symbol: SymbolId | None
    declared_name: str
    canonical_name: str
    kind: TypeKindIR
    canonical_kind: TypeKindIR
    nullability: NullabilityIR


@dataclass(frozen=True, slots=True)
class RowFieldIR:
    """An ordered row field with canonical type and source metadata."""

    name: str
    type_ref: TypeRefIR
    nullability: NullabilityIR
    span: SourceSpan | None


@dataclass(frozen=True, slots=True)
class RowSchemaIR:
    """An ordered row schema, optionally marked semantically unknown."""

    fields: tuple[RowFieldIR, ...]
    is_unknown: bool = False


@dataclass(frozen=True, slots=True)
class ExpressionIR:
    """Base class for typed, source-located Semantic IR expressions."""

    span: SourceSpan
    value_type: TypeRefIR


@dataclass(frozen=True, slots=True)
class AggregateCallIR(ExpressionIR):
    """A lowered aggregate call expression without SQL rendering behavior."""

    function: str
    arguments: tuple[ExpressionIR, ...]
    order_by: tuple[OrderItemIR, ...] = ()


@dataclass(frozen=True, slots=True)
class LiteralIR(ExpressionIR):
    """A lowered scalar literal."""

    value: StaticValue


@dataclass(frozen=True, slots=True)
class FieldRefIR(ExpressionIR):
    """A lowered bare or dotted field reference."""

    name: str
    qualifier: tuple[str, ...]
    field: FieldId | None


@dataclass(frozen=True, slots=True)
class AnyFieldIR(ExpressionIR):
    """A field of an enclosing scalar ANY binder, separate from outer inputs."""

    binding: str
    source_binding: str
    name: str
    relation: SymbolId

    def __post_init__(self) -> None:
        if (
            not self.binding
            or not self.source_binding
            or not self.name
            or self.relation.namespace is not SymbolNamespace.RELATION
        ):
            raise ValueError("ANY fields require a local binding and relation identity")


@dataclass(frozen=True, slots=True)
class ExistsIR(ExpressionIR):
    """A scalar existential read with its checked local row and predicate."""

    target: SymbolId
    binding: str
    connector: ConnectorIR | None
    authored_span: SourceSpan
    authored_occurrence: int
    current_occurrence: int
    authored_context_span: SourceSpan
    context_span: SourceSpan
    owner: SymbolId
    authored_join_count: int
    join_prefix_count: int
    predicate: ExpressionIR
    captures: tuple[FieldRefIR | AnyFieldIR, ...]

    def __post_init__(self) -> None:
        if (
            self.target.namespace is not SymbolNamespace.RELATION
            or not self.binding
            or not isinstance(self.predicate, ExpressionIR)
            or type(self.authored_span) is not SourceSpan
            or type(self.authored_occurrence) is not int
            or self.authored_occurrence < 0
            or type(self.current_occurrence) is not int
            or self.current_occurrence < 0
            or type(self.authored_context_span) is not SourceSpan
            or type(self.context_span) is not SourceSpan
            or self.owner.namespace is not SymbolNamespace.RELATION
            or type(self.authored_join_count) is not int
            or self.authored_join_count < 0
            or type(self.join_prefix_count) is not int
            or self.join_prefix_count < 0
            or type(self.captures) is not tuple
            or any(type(item) not in {FieldRefIR, AnyFieldIR} for item in self.captures)
            or (self.connector is not None and type(self.connector) is not ConnectorIR)
            or self.value_type.canonical_name != "Bool"
            or self.value_type.nullability is not NullabilityIR.NON_NULL
            or (
                self.predicate.value_type.canonical_name != "Bool"
                and not (
                    isinstance(self.predicate, LiteralIR)
                    and self.predicate.value is None
                )
            )
        ):
            raise ValueError(
                "Scalar ANY requires a resolved relation and Bool predicate"
            )


@dataclass(frozen=True, slots=True)
class CallIR(ExpressionIR):
    """A lowered static call expression without execution behavior."""

    callee: str
    callee_symbol: SymbolId | None
    arguments: tuple[ExpressionIR, ...]


@dataclass(frozen=True, slots=True)
class UnaryIR(ExpressionIR):
    """A lowered unary expression."""

    operator: str
    operand: ExpressionIR


@dataclass(frozen=True, slots=True)
class ConditionalIR(ExpressionIR):
    """A lowered conditional retaining its authored operand order."""

    when_true: ExpressionIR
    condition: ExpressionIR
    when_false: ExpressionIR


@dataclass(frozen=True, slots=True)
class MembershipIR(ExpressionIR):
    """A lowered fixed scalar membership predicate."""

    value: ExpressionIR
    options: tuple[ExpressionIR, ...]
    negated: bool


@dataclass(frozen=True, slots=True)
class CastIR(ExpressionIR):
    """A lowered explicit scalar conversion."""

    value: ExpressionIR
    target: TypeRefIR


@dataclass(frozen=True, slots=True)
class BinaryIR(ExpressionIR):
    """A lowered binary arithmetic or Boolean expression."""

    left: ExpressionIR
    operator: str
    right: ExpressionIR


@dataclass(frozen=True, slots=True)
class ComparisonIR(ExpressionIR):
    """A lowered comparison expression."""

    left: ExpressionIR
    operator: str
    right: ExpressionIR


@dataclass(frozen=True, slots=True)
class BetweenIR(ExpressionIR):
    """A lowered inclusive between expression."""

    value: ExpressionIR
    lower: ExpressionIR
    upper: ExpressionIR


@dataclass(frozen=True, slots=True)
class IsNullIR(ExpressionIR):
    """A lowered is-null predicate, optionally negated."""

    value: ExpressionIR
    negated: bool


@dataclass(frozen=True, slots=True)
class ExpressionLoweringResult:
    """A lowered expression and its ordered IR diagnostics."""

    expression: ExpressionIR | None
    diagnostics: tuple[Diagnostic, ...]


@dataclass(frozen=True, slots=True)
class DefinitionIR:
    """Marker base for definition IR nodes added by later lowering slices."""


@dataclass(frozen=True, slots=True)
class TypeIR(DefinitionIR):
    """A lowered type alias with declared and canonical targets."""

    symbol: SymbolId
    name: str
    declared_type: TypeRefIR
    canonical_type: TypeRefIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class EnumIR(DefinitionIR):
    """A lowered enum preserving member source order."""

    symbol: SymbolId
    name: str
    members: tuple[str, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeFieldDeriveIR:
    """A lowered field derive expression."""

    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeFieldIR:
    """A lowered shape field with resolved type metadata."""

    name: str
    type_ref: TypeRefIR
    nullability: NullabilityIR
    span: SourceSpan
    derive: ShapeFieldDeriveIR | None = None


@dataclass(frozen=True, slots=True)
class ShapeCheckIR:
    """A lowered named shape predicate."""

    name: str
    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeUniqueIR:
    """A lowered named uniqueness declaration over ordered fields."""

    name: str
    fields: tuple[str, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ShapeIndexIR:
    """A lowered named index declaration with an optional predicate."""

    name: str
    fields: tuple[str, ...]
    predicate: ExpressionIR | None
    span: SourceSpan


ShapeItemIR = ShapeFieldIR | ShapeCheckIR | ShapeUniqueIR | ShapeIndexIR


@dataclass(frozen=True, slots=True)
class ShapeIR(DefinitionIR):
    """A lowered shape containing fields and source-ordered metadata."""

    symbol: SymbolId
    name: str
    fields: tuple[ShapeFieldIR, ...]
    span: SourceSpan
    items: tuple[ShapeItemIR, ...] = ()


@dataclass(frozen=True, slots=True)
class ParameterIR:
    """A lowered callable parameter with resolved type metadata."""

    name: str
    type_ref: TypeRefIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ConstraintIR(DefinitionIR):
    """A lowered top-level constraint declaration."""

    symbol: SymbolId
    name: str
    parameters: tuple[ParameterIR, ...]
    return_type: TypeRefIR
    body: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class DeriveIR(DefinitionIR):
    """A lowered top-level derive declaration."""

    symbol: SymbolId
    name: str
    parameters: tuple[ParameterIR, ...]
    return_type: TypeRefIR
    body: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ConnectorIR:
    """Static source connector metadata without runtime behavior."""

    name: str
    arguments: tuple[StaticValue, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SourceIR(DefinitionIR):
    """A lowered source declaration with static connector and row metadata."""

    symbol: SymbolId
    name: str
    shape_symbol: SymbolId | None
    row_schema: RowSchemaIR
    connector: ConnectorIR
    span: SourceSpan


class RelationKindIR(StrEnum):
    """Kinds of derived relations supported by the minimal IR."""

    TABLE = "table"
    QUERY = "query"


@dataclass(frozen=True, slots=True)
class RelationSourceIR:
    """A resolved input relation reference."""

    target: SymbolId
    name: str
    span: SourceSpan


class RelationInputRoleIR(StrEnum):
    """How an input occurrence enters a JOIN relation."""

    FROM = "from"
    TARGET = "target"  # HOP is added with multi-hop VIA (post-MVP)


@dataclass(frozen=True, slots=True)
class RelationInputIR:
    """One input occurrence of a JOIN relation: the FROM input or a JOIN target."""

    ordinal: int
    role: RelationInputRoleIR
    target: SymbolId  # SymbolId(RELATION, <relation name>)
    binding: str  # the SQL alias
    visible: bool  # False for SEMI and ANTI targets
    span: SourceSpan  # FROM clause span, or the JoinClause span


class JoinKindIR(StrEnum):
    """The kinds of a lowered JOIN."""

    INNER = "inner"
    LEFT = "left"
    RIGHT = "right"
    FULL = "full"
    CROSS = "cross"
    SEMI = "semi"
    ANTI = "anti"


@dataclass(frozen=True, slots=True)
class JoinEqualityIR:
    """One relationship equality of a JOIN hop, source side first."""

    left: FieldRefIR  # source side
    right: FieldRefIR  # target side


@dataclass(frozen=True, slots=True)
class JoinHopIR:
    """One relationship hop of a JOIN with its equalities."""

    relationship: str
    left_input: int
    right_input: int
    equalities: tuple[JoinEqualityIR, ...]
    span: SourceSpan  # the `via` step, or the JoinClause for M1


@dataclass(frozen=True, slots=True)
class JoinIR:
    """One lowered JOIN of a relation, in source order."""

    ordinal: int
    kind: JoinKindIR
    source_input: int
    source_inferred: bool
    target_input: int
    hops: tuple[JoinHopIR, ...]  # M1, M2, M4: one hop; M3, M5: ()
    condition: ExpressionIR | None  # M3, M4: the lowered `on`, typed Bool
    null_extends: tuple[int, ...]
    span: SourceSpan  # the JoinClause


@dataclass(frozen=True, slots=True)
class FilterIR:
    """A lowered relation filter."""

    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ResultPredicateIR:
    """A lowered post-aggregate relation result predicate."""

    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class QualifyIR:
    """A typed predicate evaluated after the relation window stage."""

    expression: ExpressionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class ProjectionIR:
    """An ordered relation projection and its stable output metadata."""

    name: str | None
    expression: ExpressionIR
    type_ref: TypeRefIR | None
    span: SourceSpan


class OrderDirectionIR(StrEnum):
    """Normalized SQL sorting directions."""

    ASC = "ASC"
    DESC = "DESC"


class WindowFunctionRoleIR(StrEnum):
    """The private role of a lowered window-function identity."""

    WINDOW_FUNCTION = "window_function"


@dataclass(frozen=True, slots=True)
class WindowFunctionIdentityIR:
    """A private, source-preserving lowered window-function identity."""

    namespace: tuple[str, ...]
    name: str
    role: WindowFunctionRoleIR

    def __post_init__(self) -> None:
        """Reject malformed identities without normalizing source text."""

        if type(self.namespace) is not tuple:
            raise TypeError("namespace must be an exact tuple")
        if any(type(component) is not str for component in self.namespace):
            raise TypeError("namespace components must be exact strings")
        if any(not component for component in self.namespace):
            raise ValueError("namespace components must be non-empty")
        if type(self.name) is not str:
            raise TypeError("name must be an exact string")
        if not self.name:
            raise ValueError("name must be non-empty")
        if type(self.role) is not WindowFunctionRoleIR:
            raise TypeError("role must be an exact WindowFunctionRoleIR")
        if self.role is not WindowFunctionRoleIR.WINDOW_FUNCTION:
            raise ValueError("window identity role must be WINDOW_FUNCTION")


@dataclass(frozen=True, slots=True)
class WindowOrderItemIR:
    """A source-preserving window-local order expression."""

    expression: ExpressionIR
    direction: OrderDirectionIR
    direction_is_explicit: bool
    span: SourceSpan

    def __post_init__(self) -> None:
        """Keep omitted direction distinct from explicit ascending order."""

        if not isinstance(self.expression, ExpressionIR):
            raise TypeError("expression must be an ExpressionIR instance")
        if type(self.direction) is not OrderDirectionIR:
            raise TypeError("direction must be an exact OrderDirectionIR")
        if type(self.direction_is_explicit) is not bool:
            raise TypeError("direction_is_explicit must be an exact bool")
        if type(self.span) is not SourceSpan:
            raise TypeError("span must be an exact SourceSpan")
        if (
            not self.direction_is_explicit
            and self.direction is not OrderDirectionIR.ASC
        ):
            raise ValueError("an omitted direction must have effective ASC direction")


class WindowFrameUnitIR(StrEnum):
    ROWS = "ROWS"
    RANGE = "RANGE"
    GROUPS = "GROUPS"


class WindowFrameBoundKindIR(StrEnum):
    UNBOUNDED_PRECEDING = "UNBOUNDED PRECEDING"
    OFFSET_PRECEDING = "OFFSET PRECEDING"
    CURRENT_ROW = "CURRENT ROW"
    OFFSET_FOLLOWING = "OFFSET FOLLOWING"
    UNBOUNDED_FOLLOWING = "UNBOUNDED FOLLOWING"


class WindowFrameExclusionIR(StrEnum):
    NO_OTHERS = "NO OTHERS"
    CURRENT_ROW = "CURRENT ROW"
    GROUP = "GROUP"
    TIES = "TIES"


class WindowNullTreatmentIR(StrEnum):
    RESPECT_NULLS = "respect_nulls"
    IGNORE_NULLS = "ignore_nulls"


class WindowNthDirectionIR(StrEnum):
    FROM_FIRST = "from_first"
    FROM_LAST = "from_last"


class WindowUseKindIR(StrEnum):
    NAMED_DIRECT = "named_direct"
    NAMED_EXTENDED = "named_extended"


@dataclass(frozen=True, slots=True)
class WindowFrameBoundIR:
    kind: WindowFrameBoundKindIR
    offset: ExpressionIR | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowFrameBoundKindIR:
            raise TypeError("window frame bound kind must be exact")
        offset_kind = self.kind in {
            WindowFrameBoundKindIR.OFFSET_PRECEDING,
            WindowFrameBoundKindIR.OFFSET_FOLLOWING,
        }
        if offset_kind and not isinstance(self.offset, ExpressionIR):
            raise TypeError("offset frame bounds require expression IR")
        if not offset_kind and self.offset is not None:
            raise ValueError("non-offset frame bounds forbid offset IR")


@dataclass(frozen=True, slots=True)
class WindowFrameIR:
    unit: WindowFrameUnitIR
    start: WindowFrameBoundIR
    end: WindowFrameBoundIR
    exclusion: WindowFrameExclusionIR
    frame_is_explicit: bool
    end_is_explicit: bool
    exclusion_is_explicit: bool

    def __post_init__(self) -> None:
        if type(self.unit) is not WindowFrameUnitIR:
            raise TypeError("window frame unit must be exact")
        if type(self.start) is not WindowFrameBoundIR:
            raise TypeError("window frame start must be exact")
        if type(self.end) is not WindowFrameBoundIR:
            raise TypeError("window frame end must be exact")
        if type(self.exclusion) is not WindowFrameExclusionIR:
            raise TypeError("window frame exclusion must be exact")
        if any(
            type(value) is not bool
            for value in (
                self.frame_is_explicit,
                self.end_is_explicit,
                self.exclusion_is_explicit,
            )
        ):
            raise TypeError("window frame explicitness flags must be exact bools")
        if not self.frame_is_explicit and (
            self.end_is_explicit or self.exclusion_is_explicit
        ):
            raise ValueError("default frames forbid authored subcomponent flags")
        if not self.frame_is_explicit and (
            self.unit is not WindowFrameUnitIR.RANGE
            or self.start.kind is not WindowFrameBoundKindIR.UNBOUNDED_PRECEDING
            or self.end.kind is not WindowFrameBoundKindIR.CURRENT_ROW
            or self.exclusion is not WindowFrameExclusionIR.NO_OTHERS
        ):
            raise ValueError("default frame IR must retain Pietto effective defaults")
        if (
            self.frame_is_explicit
            and not self.end_is_explicit
            and self.end.kind is not WindowFrameBoundKindIR.CURRENT_ROW
        ):
            raise ValueError("shorthand frame IR requires an effective CURRENT ROW end")
        if (
            not self.exclusion_is_explicit
            and self.exclusion is not WindowFrameExclusionIR.NO_OTHERS
        ):
            raise ValueError("omitted frame exclusion must mean NO OTHERS")


@dataclass(frozen=True, slots=True)
class WindowRelationOccurrenceIR:
    symbol: SymbolId
    span: SourceSpan

    def __post_init__(self) -> None:
        if type(self.symbol) is not SymbolId:
            raise TypeError("window relation owner must be an exact symbol")
        if self.symbol.namespace is not SymbolNamespace.RELATION:
            raise ValueError("window relation owner must use the relation namespace")
        if type(self.span) is not SourceSpan:
            raise TypeError("window relation owner must retain an exact span")


@dataclass(frozen=True, slots=True)
class NamedWindowOccurrenceIR:
    owner: WindowRelationOccurrenceIR
    ordinal: int
    span: SourceSpan

    def __post_init__(self) -> None:
        if type(self.owner) is not WindowRelationOccurrenceIR:
            raise TypeError("named window occurrence must retain its exact owner")
        if type(self.ordinal) is not int or self.ordinal < 0:
            raise ValueError("named window occurrence ordinal must be nonnegative")
        if type(self.span) is not SourceSpan:
            raise TypeError("named window occurrence span must be exact")


@dataclass(frozen=True, slots=True)
class NamedWindowBaseIR:
    spelling: str
    target: NamedWindowOccurrenceIR

    def __post_init__(self) -> None:
        if type(self.spelling) is not str or not self.spelling:
            raise ValueError("named window base spelling must be nonempty")
        if type(self.target) is not NamedWindowOccurrenceIR:
            raise TypeError("named window base target must be exact")


@dataclass(frozen=True, slots=True)
class NamedWindowLocalSpecIR:
    partition_by: tuple[ExpressionIR, ...]
    order_by: tuple[WindowOrderItemIR, ...]
    frame: WindowFrameIR | None
    span: SourceSpan

    def __post_init__(self) -> None:
        if type(self.partition_by) is not tuple or any(
            not isinstance(expression, ExpressionIR) for expression in self.partition_by
        ):
            raise TypeError("named window local partition must be an exact tuple")
        if type(self.order_by) is not tuple or any(
            type(item) is not WindowOrderItemIR for item in self.order_by
        ):
            raise TypeError("named window local order must be an exact tuple")
        if self.frame is not None and type(self.frame) is not WindowFrameIR:
            raise TypeError("named window local frame must be exact or absent")
        if self.frame is not None and not self.frame.frame_is_explicit:
            raise ValueError("named window local frames require authored evidence")
        if type(self.span) is not SourceSpan:
            raise TypeError("named window local specification span must be exact")

    @property
    def has_components(self) -> bool:
        return bool(self.partition_by or self.order_by or self.frame is not None)


@dataclass(frozen=True, slots=True)
class NamedWindowDeclarationIR:
    occurrence: NamedWindowOccurrenceIR
    name: str
    base: NamedWindowBaseIR | None
    local_spec: NamedWindowLocalSpecIR
    span: SourceSpan

    def __post_init__(self) -> None:
        if type(self.occurrence) is not NamedWindowOccurrenceIR:
            raise TypeError("named window declaration occurrence must be exact")
        if type(self.name) is not str or not self.name:
            raise ValueError("named window declaration name must be nonempty")
        if self.base is not None and type(self.base) is not NamedWindowBaseIR:
            raise TypeError("named window declaration base must be exact or absent")
        if type(self.local_spec) is not NamedWindowLocalSpecIR:
            raise TypeError("named window declaration local spec must be exact")
        if type(self.span) is not SourceSpan or self.span != self.occurrence.span:
            raise ValueError("named window declaration span must match its occurrence")
        if self.base is not None and self.base.target.owner != self.occurrence.owner:
            raise ValueError("named window declaration base must stay relation-local")


@dataclass(frozen=True, slots=True)
class WindowUseOccurrenceIR:
    owner: WindowRelationOccurrenceIR
    selected_output_ordinal: int
    kind: WindowUseKindIR
    span: SourceSpan

    def __post_init__(self) -> None:
        if type(self.owner) is not WindowRelationOccurrenceIR:
            raise TypeError("named window use must retain its exact owner")
        if (
            type(self.selected_output_ordinal) is not int
            or self.selected_output_ordinal < 0
        ):
            raise ValueError("named window use ordinal must be nonnegative")
        if type(self.kind) is not WindowUseKindIR:
            raise TypeError("named window use kind must be exact")
        if type(self.span) is not SourceSpan:
            raise TypeError("named window use span must be exact")


@dataclass(frozen=True, slots=True)
class NamedWindowUseIR:
    occurrence: WindowUseOccurrenceIR
    target: NamedWindowOccurrenceIR
    reference_spelling: str
    local_spec: NamedWindowLocalSpecIR

    def __post_init__(self) -> None:
        if type(self.occurrence) is not WindowUseOccurrenceIR:
            raise TypeError("named window use occurrence must be exact")
        if type(self.target) is not NamedWindowOccurrenceIR:
            raise TypeError("named window use target must be exact")
        if type(self.reference_spelling) is not str or not self.reference_spelling:
            raise ValueError("named window reference spelling must be nonempty")
        if type(self.local_spec) is not NamedWindowLocalSpecIR:
            raise TypeError("named window use local spec must be exact")
        if self.target.owner != self.occurrence.owner:
            raise ValueError("named window use target must stay relation-local")
        if (
            self.occurrence.kind is WindowUseKindIR.NAMED_DIRECT
            and self.local_spec.has_components
        ):
            raise ValueError("named window use kind must match local components")


@dataclass(frozen=True, slots=True)
class WindowSpecIR:
    """A source-ordered inline window specification with optional frame."""

    partition_by: tuple[ExpressionIR, ...]
    order_by: tuple[WindowOrderItemIR, ...]
    span: SourceSpan
    frame: WindowFrameIR | None = None

    def __post_init__(self) -> None:
        """Require exact ordered tuples and mandatory local ordering."""

        if type(self.partition_by) is not tuple:
            raise TypeError("partition_by must be an exact tuple")
        if any(
            not isinstance(expression, ExpressionIR) for expression in self.partition_by
        ):
            raise TypeError("partition_by items must be ExpressionIR instances")
        if type(self.order_by) is not tuple:
            raise TypeError("order_by must be an exact tuple")
        if any(type(item) is not WindowOrderItemIR for item in self.order_by):
            raise TypeError("order_by items must be exact WindowOrderItemIR instances")
        if type(self.span) is not SourceSpan:
            raise TypeError("span must be an exact SourceSpan")
        if self.frame is not None and type(self.frame) is not WindowFrameIR:
            raise TypeError("window frame IR must be exact or absent")


_WINDOW_ARGUMENT_ARITIES = {
    "row_number": frozenset({0}),
    "rank": frozenset({0}),
    "dense_rank": frozenset({0}),
    "percent_rank": frozenset({0}),
    "cume_dist": frozenset({0}),
    "ntile": frozenset({1}),
    "lag": frozenset({1, 2, 3}),
    "lead": frozenset({1, 2, 3}),
    "first_value": frozenset({1}),
    "last_value": frozenset({1}),
    "nth_value": frozenset({2}),
}


@dataclass(frozen=True, slots=True)
class WindowCallIR(ExpressionIR):
    """A lowered builtin window call with its complete inline specification."""

    identity: WindowFunctionIdentityIR
    arguments: tuple[ExpressionIR, ...]
    spec: WindowSpecIR
    null_treatment: WindowNullTreatmentIR | None = None
    null_treatment_is_explicit: bool = False
    nth_direction: WindowNthDirectionIR | None = None
    nth_direction_is_explicit: bool = False
    named_use: NamedWindowUseIR | None = None

    def __post_init__(self) -> None:
        """Fail closed for malformed or unsupported window-call IR."""

        if type(self.span) is not SourceSpan:
            raise TypeError("span must be an exact SourceSpan")
        if type(self.value_type) is not TypeRefIR:
            raise TypeError("value_type must be an exact TypeRefIR")
        if type(self.identity) is not WindowFunctionIdentityIR:
            raise TypeError("identity must be an exact WindowFunctionIdentityIR")
        if type(self.arguments) is not tuple:
            raise TypeError("arguments must be an exact tuple")
        if any(not isinstance(argument, ExpressionIR) for argument in self.arguments):
            raise TypeError("arguments must be ExpressionIR instances")
        if type(self.spec) is not WindowSpecIR:
            raise TypeError("spec must be an exact WindowSpecIR")
        if not self.spec.order_by:
            raise ValueError("window call requires at least one order item")
        if (
            self.null_treatment is not None
            and type(self.null_treatment) is not WindowNullTreatmentIR
        ):
            raise TypeError("window NULL treatment IR must be exact or absent")
        if type(self.null_treatment_is_explicit) is not bool:
            raise TypeError("window NULL treatment explicitness must be exact")
        if (
            self.nth_direction is not None
            and type(self.nth_direction) is not WindowNthDirectionIR
        ):
            raise TypeError("window nth direction IR must be exact or absent")
        if type(self.nth_direction_is_explicit) is not bool:
            raise TypeError("window nth direction explicitness must be exact")
        if self.named_use is not None and type(self.named_use) is not NamedWindowUseIR:
            raise TypeError("named window use IR must be exact or absent")
        if self.identity.namespace != ():
            raise ValueError("builtin window call identity namespace must be empty")
        arities = _WINDOW_ARGUMENT_ARITIES.get(self.identity.name)
        if arities is None:
            raise ValueError("window call identity is unsupported")
        if len(self.arguments) not in arities:
            raise ValueError("window call argument arity is invalid")
        name = self.identity.name
        null_applies = name in {
            "lag",
            "lead",
            "first_value",
            "last_value",
            "nth_value",
        }
        if null_applies is (self.null_treatment is None):
            raise ValueError("window NULL treatment must match function policy")
        if not null_applies and self.null_treatment_is_explicit:
            raise ValueError("inapplicable NULL treatment cannot be explicit")
        if (
            self.null_treatment is WindowNullTreatmentIR.IGNORE_NULLS
            and not self.null_treatment_is_explicit
        ):
            raise ValueError("IGNORE NULLS cannot have omitted authorship")
        if name == "nth_value":
            if self.nth_direction is None:
                raise ValueError("nth_value IR requires a direction")
            if (
                self.nth_direction is WindowNthDirectionIR.FROM_LAST
                and not self.nth_direction_is_explicit
            ):
                raise ValueError("FROM LAST cannot have omitted authorship")
        elif self.nth_direction is not None or self.nth_direction_is_explicit:
            raise ValueError("non-nth window IR forbids nth direction")
        frame_sensitive = name in {"first_value", "last_value", "nth_value"}
        if frame_sensitive is (self.spec.frame is None):
            raise ValueError("window frame IR must match function policy")
        if frame_sensitive:
            if self.value_type.nullability is not NullabilityIR.NULLABLE:
                raise ValueError("frame-value IR requires a nullable result")
            # A grouped window reads a selected aggregate output as its call.
            if type(self.arguments[0]) not in {FieldRefIR, LiteralIR, AggregateCallIR}:
                raise ValueError("frame-value IR requires one bounded value input")
            value_type = self.arguments[0].value_type
            if type(value_type) is not TypeRefIR:
                raise TypeError("frame-value input requires an exact value type")
            # A type alias input binds T to the builtin type it expands to.
            canonical = replace(
                value_type,
                symbol=value_type.canonical_symbol,
                declared_name=value_type.canonical_name,
                kind=value_type.canonical_kind,
            )
            if self.value_type not in (
                replace(value_type, nullability=self.value_type.nullability),
                replace(canonical, nullability=self.value_type.nullability),
            ):
                raise ValueError("frame-value input and result must share exact T")
        if name == "nth_value":
            position = self.arguments[1]
            if (
                type(position) is not LiteralIR
                or type(position.value) is not int
                or position.value < 1
            ):
                raise ValueError("nth_value IR requires a positive integer literal")
            position_type = position.value_type
            int_symbol = SymbolId(SymbolNamespace.TYPE, "Int")
            if (
                type(position_type) is not TypeRefIR
                or position_type.symbol != int_symbol
                or position_type.canonical_symbol != int_symbol
                or position_type.declared_name != "Int"
                or position_type.canonical_name != "Int"
                or position_type.kind is not TypeKindIR.BUILTIN
                or position_type.canonical_kind is not TypeKindIR.BUILTIN
                or position_type.nullability is not NullabilityIR.NON_NULL
            ):
                raise ValueError("nth_value IR requires exact non-null Int typing")


@dataclass(frozen=True, slots=True)
class AggregateWindowCallIR(ExpressionIR):
    """A separately validated ordinary aggregate evaluated over a window."""

    function: str
    arguments: tuple[ExpressionIR, ...]
    spec: WindowSpecIR
    named_use: NamedWindowUseIR | None = None

    def __post_init__(self) -> None:
        if type(self.span) is not SourceSpan or type(self.value_type) is not TypeRefIR:
            raise TypeError("aggregate window requires exact source and type")
        if type(self.function) is not str or self.function not in {
            "sum",
            "count",
            "avg",
            "min",
            "max",
        }:
            raise ValueError("aggregate window function is unsupported")
        if type(self.arguments) is not tuple or any(
            not isinstance(argument, ExpressionIR) for argument in self.arguments
        ):
            raise TypeError("aggregate window arguments must be exact expressions")
        arities = {"count": {0, 1}, "sum": {1}, "avg": {1}, "min": {1}, "max": {1}}
        if len(self.arguments) not in arities[self.function]:
            raise ValueError("aggregate window argument arity is invalid")
        if type(self.spec) is not WindowSpecIR:
            raise TypeError("aggregate window specification must be exact")
        if (
            self.spec.frame is not None
            and self.spec.frame.unit is WindowFrameUnitIR.GROUPS
            and not self.spec.order_by
        ):
            raise ValueError("GROUPS aggregate windows require an ORDER BY")
        if self.named_use is not None and type(self.named_use) is not NamedWindowUseIR:
            raise TypeError("aggregate named window use must be exact or absent")
        if self.named_use is not None and self.named_use.occurrence.span != self.span:
            raise ValueError("aggregate named window use must retain its source span")
        if any(
            _aggregate_window_contains_window(item)
            for item in (*self.arguments, *self.spec.partition_by)
        ) or any(
            _aggregate_window_contains_window(item.expression)
            for item in self.spec.order_by
        ):
            raise ValueError("aggregate windows cannot contain nested window calls")
        if not aggregate_call_contract(
            self.function,
            self.arguments,
            self.value_type,
            allow_grouped_value=True,
        ):
            raise ValueError(
                "aggregate window arguments or result violate its contract"
            )


def _aggregate_window_builtin_type(expression: ExpressionIR) -> str | None:
    value_type = expression.value_type
    if (
        type(value_type) is not TypeRefIR
        or value_type.canonical_kind is not TypeKindIR.BUILTIN
    ):
        return None
    return value_type.canonical_name


def _aggregate_window_has_type(
    value_type: TypeRefIR,
    name: str,
    nullability: NullabilityIR,
) -> bool:
    return (
        value_type.canonical_kind is TypeKindIR.BUILTIN
        and value_type.canonical_name == name
        and value_type.nullability is nullability
    )


def aggregate_call_contract(
    function: str,
    arguments: tuple[ExpressionIR, ...],
    value_type: TypeRefIR,
    *,
    order_by: tuple[OrderItemIR, ...] = (),
    allow_grouped_value: bool = False,
) -> bool:
    """Validate the shared ordinary aggregate contract at an IR boundary."""

    if (
        type(function) is not str
        or type(arguments) is not tuple
        or type(order_by) is not tuple
        or any(
            type(item) is not OrderItemIR
            or not isinstance(item.expression, ExpressionIR)
            or type(item.direction) is not OrderDirectionIR
            for item in order_by
        )
    ):
        return False
    if any(not isinstance(argument, ExpressionIR) for argument in arguments):
        return False
    if function == "string_agg":
        return (
            len(arguments) == 2
            and bool(order_by)
            and all(
                _aggregate_window_builtin_type(argument) == "Text"
                for argument in arguments
            )
            and all(
                not _aggregate_call_contains_nested_stage(argument)
                for argument in (*arguments, *(item.expression for item in order_by))
            )
            and _aggregate_window_has_type(value_type, "Text", NullabilityIR.NULLABLE)
        )
    if order_by:
        return False
    if function == "count":
        return _aggregate_window_has_type(
            value_type, "Int", NullabilityIR.NON_NULL
        ) and (
            not arguments
            or len(arguments) == 1
            and _aggregate_window_is_count_argument(
                arguments[0], allow_grouped_value=allow_grouped_value
            )
        )
    if function == "count_distinct":
        return (
            len(arguments) == 1
            and _aggregate_window_has_type(value_type, "Int", NullabilityIR.NON_NULL)
            and _aggregate_window_is_count_distinct_argument(arguments[0])
        )
    if function in {"sum", "avg"} and len(arguments) == 1:
        argument = arguments[0]
        argument_type = _aggregate_window_builtin_type(argument)
        valid, has_input, has_literal = _aggregate_window_numeric_argument_shape(
            argument, allow_grouped_value=allow_grouped_value
        )
        result = (
            "Decimal"
            if argument_type == "Decimal"
            else "Int"
            if function == "sum" and argument_type == "Int"
            else "Float"
        )
        return (
            argument_type in {"Int", "Float", "Decimal"}
            and valid
            and has_input
            and (not has_literal or argument_type in {"Int", "Float"})
            and _aggregate_window_has_type(value_type, result, NullabilityIR.NULLABLE)
        )
    if function in {"min", "max"} and len(arguments) == 1:
        argument = arguments[0]
        argument_type = _aggregate_window_builtin_type(argument)
        return (
            _aggregate_window_is_extrema_argument(
                argument, allow_grouped_value=allow_grouped_value
            )
            and argument_type in {"Int", "Float", "Decimal", "Date", "Timestamp"}
            and _aggregate_window_has_type(
                value_type, argument_type, NullabilityIR.NULLABLE
            )
        )
    return False


def _aggregate_window_contains_window(expression: ExpressionIR) -> bool:
    pending = [expression]
    while pending:
        item = pending.pop()
        if isinstance(item, (WindowCallIR, AggregateWindowCallIR)):
            return True
        if isinstance(item, ExpressionIR):
            for field in fields(item):
                value = getattr(item, field.name)
                if isinstance(value, ExpressionIR):
                    pending.append(value)
                elif type(value) is tuple:
                    pending.extend(
                        child for child in value if isinstance(child, ExpressionIR)
                    )
    return False


def _aggregate_call_contains_nested_stage(expression: ExpressionIR) -> bool:
    pending = [expression]
    while pending:
        item = pending.pop()
        if isinstance(item, (AggregateCallIR, WindowCallIR, AggregateWindowCallIR)):
            return True
        for field in fields(item):
            value = getattr(item, field.name)
            if isinstance(value, ExpressionIR):
                pending.append(value)
            elif type(value) is tuple:
                pending.extend(
                    child for child in value if isinstance(child, ExpressionIR)
                )
    return False


def _aggregate_window_is_grouped_value(expression: ExpressionIR) -> bool:
    if not isinstance(expression, AggregateCallIR):
        return False
    return aggregate_call_contract(
        expression.function,
        expression.arguments,
        expression.value_type,
        order_by=expression.order_by,
    )


def _aggregate_window_numeric_argument_shape(
    expression: ExpressionIR,
    *,
    allow_grouped_value: bool = True,
) -> tuple[bool, bool, bool]:
    expression_type = _aggregate_window_builtin_type(expression)
    if expression_type not in {"Int", "Float", "Decimal"}:
        return False, False, False
    if isinstance(expression, FieldRefIR):
        valid = expression.field is not None
        return valid, valid, False
    if allow_grouped_value and _aggregate_window_is_grouped_value(expression):
        return True, True, False
    if isinstance(expression, LiteralIR):
        return (
            (type(expression.value) is int and expression_type == "Int")
            or (type(expression.value) is float and expression_type == "Float"),
            False,
            True,
        )
    if isinstance(expression, UnaryIR):
        valid, has_input, has_literal = _aggregate_window_numeric_argument_shape(
            expression.operand, allow_grouped_value=allow_grouped_value
        )
        return (
            expression.operator in {"+", "-"}
            and valid
            and (_aggregate_window_builtin_type(expression.operand) == expression_type),
            has_input,
            has_literal,
        )
    if isinstance(expression, BinaryIR):
        if expression.operator not in {"+", "-", "*"}:
            return False, False, False
        left_valid, left_input, left_literal = _aggregate_window_numeric_argument_shape(
            expression.left, allow_grouped_value=allow_grouped_value
        )
        right_valid, right_input, right_literal = (
            _aggregate_window_numeric_argument_shape(
                expression.right, allow_grouped_value=allow_grouped_value
            )
        )
        left_type = _aggregate_window_builtin_type(expression.left)
        right_type = _aggregate_window_builtin_type(expression.right)
        if not left_valid or not right_valid:
            return False, False, False
        if expression_type == "Decimal":
            allowed = {"Decimal"} if expression.operator == "*" else {"Decimal", "Int"}
            valid = (
                left_type in allowed
                and right_type in allowed
                and "Decimal" in {left_type, right_type}
            )
        elif expression_type == "Int":
            valid = left_type == right_type == "Int"
        else:
            valid = {left_type, right_type} <= {"Int", "Float"}
        return valid, left_input or right_input, left_literal or right_literal
    return False, False, False


def _aggregate_window_is_count_argument(
    expression: ExpressionIR,
    *,
    allow_grouped_value: bool = True,
) -> bool:
    valid, has_input = _aggregate_window_count_argument_shape(
        expression, allow_grouped_value=allow_grouped_value
    )
    return valid and has_input


def _aggregate_window_count_argument_shape(
    expression: ExpressionIR,
    *,
    allow_grouped_value: bool = True,
) -> tuple[bool, bool]:
    if _aggregate_window_builtin_type(expression) in {None, "Any"}:
        return False, False
    if isinstance(expression, FieldRefIR):
        valid = (
            expression.field is not None
            and expression.value_type.canonical_kind is TypeKindIR.BUILTIN
            and _aggregate_window_builtin_type(expression) != "Any"
        )
        return valid, valid
    if allow_grouped_value and _aggregate_window_is_grouped_value(expression):
        return True, True
    if isinstance(expression, LiteralIR):
        return _aggregate_window_builtin_type(expression) not in {None, "Any"}, False
    if isinstance(expression, UnaryIR):
        valid, has_input = _aggregate_window_count_argument_shape(
            expression.operand, allow_grouped_value=allow_grouped_value
        )
        return expression.operator in {"+", "-", "not"} and valid, has_input
    if isinstance(expression, BinaryIR):
        left_valid, left_input = _aggregate_window_count_argument_shape(
            expression.left, allow_grouped_value=allow_grouped_value
        )
        right_valid, right_input = _aggregate_window_count_argument_shape(
            expression.right, allow_grouped_value=allow_grouped_value
        )
        return (
            expression.operator in {"+", "-", "*", "%", "and", "or"}
            and left_valid
            and right_valid,
            left_input or right_input,
        )
    if isinstance(expression, CallIR):
        valid = (
            expression.callee in {"lower", "trim", "len"}
            and expression.callee_symbol
            == SymbolId(SymbolNamespace.CALLABLE, expression.callee)
            and len(expression.arguments) == 1
        )
        argument_valid, has_input = (
            _aggregate_window_count_argument_shape(
                expression.arguments[0], allow_grouped_value=allow_grouped_value
            )
            if valid
            else (False, False)
        )
        return valid and argument_valid, has_input
    return False, False


def _aggregate_window_is_count_distinct_argument(expression: ExpressionIR) -> bool:
    allowed = {"Bool", "Int", "Float", "Decimal", "Text", "Date", "Timestamp", "UUID"}
    if isinstance(expression, FieldRefIR):
        return (
            expression.field is not None
            and _aggregate_window_builtin_type(expression) in allowed
        )
    return _aggregate_window_is_count_distinct_text_transform(expression)


def _aggregate_window_is_count_distinct_text_transform(
    expression: ExpressionIR,
) -> bool:
    if isinstance(expression, FieldRefIR):
        return (
            expression.field is not None
            and _aggregate_window_builtin_type(expression) == "Text"
        )
    if not isinstance(expression, CallIR):
        return False
    if (
        expression.callee not in {"lower", "trim"}
        or expression.callee_symbol
        != SymbolId(SymbolNamespace.CALLABLE, expression.callee)
        or len(expression.arguments) != 1
        or _aggregate_window_builtin_type(expression) != "Text"
    ):
        return False
    return _aggregate_window_is_count_distinct_text_transform(expression.arguments[0])


def _aggregate_window_is_extrema_argument(
    expression: ExpressionIR,
    *,
    allow_grouped_value: bool = True,
) -> bool:
    return (isinstance(expression, FieldRefIR) and expression.field is not None) or (
        allow_grouped_value and _aggregate_window_is_grouped_value(expression)
    )


@dataclass(frozen=True, slots=True)
class OrderItemIR:
    """A typed sorting expression with an explicit direction."""

    expression: ExpressionIR
    direction: OrderDirectionIR
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class LimitIR:
    """A validated static relation row-count limit."""

    value: int
    span: SourceSpan


_EXISTENCE_JOIN_KINDS = frozenset({JoinKindIR.SEMI, JoinKindIR.ANTI})
# IR values that never hold a field reference.
_FIELDLESS_TYPES = frozenset({SourceSpan, SymbolId, TypeRefIR})


def _field_refs(*values: object) -> list[FieldRefIR]:
    """Every field reference inside the given IR values.

    Malformed IR, such as a list or an unset field, is walked as far as it goes:
    the SQL emitters report it, not relation construction.
    """

    found: list[FieldRefIR] = []
    pending = list(values)
    while pending:
        value = pending.pop()
        if isinstance(value, FieldRefIR):
            found.append(value)
        elif isinstance(value, tuple | list):
            pending.extend(value)
        elif is_dataclass(value) and type(value) not in _FIELDLESS_TYPES:
            pending.extend(getattr(value, item.name, None) for item in fields(value))
    return found


def _input_of(reference: FieldRefIR) -> int | None:
    return getattr(getattr(reference, "field", None), "input", None)


def _output_aliases(relation: RelationIR) -> dict[str, TypeRefIR]:
    counts: dict[str, int] = {}
    values: dict[str, TypeRefIR] = {}
    for projection in relation.projections:
        if projection.name is None:
            continue
        counts[projection.name] = counts.get(projection.name, 0) + 1
        values[projection.name] = projection.expression.value_type
    return {name: values[name] for name, count in counts.items() if count == 1}


def _check_any_scopes(relation: RelationIR) -> None:
    """Keep scalar ANY binders distinct from outer and sibling input identities."""
    outer = {item.binding for item in relation.inputs} or {relation.source.name}
    pending: list[tuple[object, dict[str, SymbolId]]] = [(relation, {})]
    while pending:
        value, scopes = pending.pop()
        if isinstance(value, AnyFieldIR):
            if scopes.get(value.binding) != value.relation:
                raise ValueError("ANY field must belong to a visible local binder")
        elif isinstance(value, ExistsIR):
            if value.binding in outer or value.binding in scopes:
                raise ValueError("ANY binder must not shadow a visible input")
            pending.extend((capture, scopes) for capture in value.captures)
            pending.append((value.predicate, {**scopes, value.binding: value.target}))
        elif isinstance(value, tuple | list):
            pending.extend((item, scopes) for item in value)
        elif is_dataclass(value) and type(value) not in _FIELDLESS_TYPES:
            pending.extend(
                (getattr(value, item.name, None), scopes) for item in fields(value)
            )


def _check_join_invariants(relation: RelationIR) -> None:
    """Raise ValueError for the first JOIN invariant the relation violates."""

    inputs, joins = relation.inputs, relation.joins
    tail = (
        relation.projections,
        relation.filter,
        relation.group_keys,
        relation.result_predicate,
        relation.named_windows,
    )
    # 1. Inputs and joins come together; join-free fields name no input.
    if inputs or joins:
        mismatched = not joins or len(inputs) != len(joins) + 1
    else:
        mismatched = any(
            _input_of(item) is not None
            for item in _field_refs(tail, relation.qualify, relation.order_by)
        )
    if mismatched:
        raise ValueError(
            "relation inputs must be one more than its joins; "
            "join-free fields name no input"
        )
    aliases = _output_aliases(relation)

    def is_output_alias(reference: FieldRefIR) -> bool:
        return (
            reference.field is None
            and reference.qualifier == ()
            and aliases.get(reference.name) == reference.value_type
        )

    if not joins:
        for reference in _field_refs(relation.qualify, relation.order_by):
            if reference.field is None and not is_output_alias(reference):
                raise ValueError(
                    "relation output aliases must retain exact projection identity"
                )
        return
    # 2. The relation's source as FROM, then one target per JOIN, with unique
    #    bindings.
    if (
        any(item.ordinal != ordinal for ordinal, item in enumerate(inputs))
        or inputs[0].role is not RelationInputRoleIR.FROM
        or inputs[0].target != relation.source.target
        or inputs[0].binding != relation.source.name
        or inputs[0].span != relation.source.span
        or any(item.role is not RelationInputRoleIR.TARGET for item in inputs[1:])
        or len({item.binding for item in inputs}) != len(inputs)
    ):
        raise ValueError(
            "relation inputs must be its source as FROM then JOIN targets "
            "in ordinal order, uniquely bound"
        )
    # 3. Each JOIN reads an earlier input that is visible before it.
    hidden: set[int] = set()
    for ordinal, join in enumerate(joins, start=1):
        if (
            join.ordinal != ordinal
            or join.target_input != ordinal
            or not 0 <= join.source_input < ordinal
            or join.source_input in hidden
        ):
            raise ValueError(
                "relation joins must be in ordinal order and read an earlier "
                "visible input"
            )
        if join.kind in _EXISTENCE_JOIN_KINDS:
            hidden.add(ordinal)
    # 4. CROSS has nothing to match on; every other JOIN has something.
    for join in joins:
        matches = bool(join.hops) or join.condition is not None
        if join.kind == JoinKindIR.CROSS:
            invalid = matches or bool(join.null_extends)
        else:
            invalid = not matches
        if invalid:
            raise ValueError(
                "CROSS joins must have no hops, condition or null extension; "
                "others need a hop or condition"
            )
    # 5. At most one hop, from the source to the target, by equalities that all
    #    run that way.
    for join in joins:
        if len(join.hops) > 1 or any(
            hop.left_input != join.source_input
            or hop.right_input != join.target_input
            or not hop.equalities
            or not all(
                _input_of(equality.left) == hop.left_input
                and _input_of(equality.right) == hop.right_input
                for equality in hop.equalities
            )
            for hop in join.hops
        ):
            raise ValueError(
                "relation joins must have at most one hop, from source input "
                "to target input by equalities that all run that way"
            )
    # 6. Null extension per kind; SEMI and ANTI targets are not row inputs.
    rows = [0]
    for join in joins:
        expected = {
            JoinKindIR.LEFT: (join.target_input,),
            JoinKindIR.RIGHT: tuple(rows),
            JoinKindIR.FULL: (*rows, join.target_input),
        }.get(join.kind, ())
        if join.null_extends != expected:
            raise ValueError("relation join null extensions must match the join kind")
        if join.kind not in _EXISTENCE_JOIN_KINDS:
            rows.append(join.target_input)
    # 7. SEMI and ANTI targets are hidden; every other input is visible.
    if tuple(item.visible for item in inputs) != (
        True,
        *(join.kind not in _EXISTENCE_JOIN_KINDS for join in joins),
    ):
        raise ValueError(
            "relation inputs must be visible except SEMI and ANTI join targets"
        )
    # 8. Every field reference names a readable input, that input's relation as
    #    owner and its binding as qualifier.
    readable = {ordinal for ordinal, item in enumerate(inputs) if item.visible}
    regions: list[tuple[object, set[int], bool]] = [(tail, readable, False)]
    if relation.qualify is not None:
        regions.append(((relation.qualify,), readable, True))
    if relation.order_by:
        regions.append((relation.order_by, readable, True))
    visible_before = {0}
    for join in joins:
        regions.append(
            ((join.condition, join.hops), visible_before | {join.target_input}, False)
        )
        if join.kind not in _EXISTENCE_JOIN_KINDS:
            visible_before = visible_before | {join.target_input}
    for values, allowed, allow_output_aliases in regions:
        for reference in _field_refs(values):
            ordinal = _input_of(reference)
            if allow_output_aliases and ordinal is None and is_output_alias(reference):
                continue
            if (
                ordinal is None
                or ordinal not in allowed
                or getattr(reference.field, "owner", None) != inputs[ordinal].target
                or getattr(reference, "qualifier", None) != (inputs[ordinal].binding,)
            ):
                raise ValueError(
                    "relation field references must name a visible input, be owned "
                    "by its relation and qualify with its binding"
                )


@dataclass(frozen=True, slots=True)
class RelationIR(DefinitionIR):
    """A lowered table or query relation."""

    symbol: SymbolId
    name: str
    kind: RelationKindIR
    source: RelationSourceIR
    filter: FilterIR | None
    projections: tuple[ProjectionIR, ...]
    row_schema: RowSchemaIR
    span: SourceSpan
    order_by: tuple[OrderItemIR, ...] = ()
    limit: LimitIR | None = None
    group_keys: tuple[FieldRefIR, ...] = ()
    result_predicate: ResultPredicateIR | None = None
    qualify: QualifyIR | None = None
    named_windows: tuple[NamedWindowDeclarationIR, ...] = ()
    inputs: tuple[RelationInputIR, ...] = ()
    joins: tuple[JoinIR, ...] = ()

    def __post_init__(self) -> None:
        if type(self.named_windows) is not tuple or any(
            type(item) is not NamedWindowDeclarationIR for item in self.named_windows
        ):
            raise TypeError("relation named windows must be an exact tuple")
        owner = WindowRelationOccurrenceIR(self.symbol, self.span)
        if any(
            declaration.occurrence.owner != owner
            or declaration.occurrence.ordinal != ordinal
            for ordinal, declaration in enumerate(self.named_windows)
        ):
            raise ValueError(
                "relation named windows must retain source order and owner"
            )
        if len({item.name for item in self.named_windows}) != len(self.named_windows):
            raise ValueError("relation named window names must be unique")
        declarations = {
            declaration.occurrence: declaration for declaration in self.named_windows
        }
        for declaration in self.named_windows:
            if declaration.base is None:
                continue
            target = declarations.get(declaration.base.target)
            if (
                target is None
                or target is declaration
                or target.name != declaration.base.spelling
            ):
                raise ValueError("named window base must target its exact declaration")
        for ordinal, projection in enumerate(self.projections):
            expression = projection.expression
            named_use = (
                None
                if not isinstance(expression, (WindowCallIR, AggregateWindowCallIR))
                else getattr(expression, "named_use", None)
            )
            if named_use is None:
                continue
            target = declarations.get(named_use.target)
            if (
                named_use.occurrence.owner != owner
                or named_use.occurrence.selected_output_ordinal != ordinal
                or named_use.occurrence.span != expression.span
                or target is None
                or target.name != named_use.reference_spelling
            ):
                raise ValueError("named window call must retain its exact relation use")
        _check_any_scopes(self)
        _check_join_invariants(self)


@dataclass(frozen=True, slots=True)
class ScriptIR:
    """Top-level Semantic IR container preserving definition order."""

    definitions: tuple[DefinitionIR, ...]


@dataclass(frozen=True, slots=True)
class IrResult:
    """A Semantic IR result and its ordered lowering diagnostics."""

    ir: ScriptIR | None
    diagnostics: tuple[Diagnostic, ...]
