"""Immutable public models for Pietto Semantic IR."""

from __future__ import annotations

from dataclasses import dataclass, replace
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
        ) is self.local_spec.has_components:
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
        if not self.order_by:
            raise ValueError("window IR requires at least one order item")
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
            if type(self.arguments[0]) not in {FieldRefIR, LiteralIR}:
                raise ValueError("frame-value IR requires one bounded value input")
            value_type = self.arguments[0].value_type
            if type(value_type) is not TypeRefIR:
                raise TypeError("frame-value input requires an exact value type")
            if (
                replace(value_type, nullability=self.value_type.nullability)
                != self.value_type
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
    named_windows: tuple[NamedWindowDeclarationIR, ...] = ()

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
                if not isinstance(expression, WindowCallIR)
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


@dataclass(frozen=True, slots=True)
class ScriptIR:
    """Top-level Semantic IR container preserving definition order."""

    definitions: tuple[DefinitionIR, ...]


@dataclass(frozen=True, slots=True)
class IrResult:
    """A Semantic IR result and its ordered lowering diagnostics."""

    ir: ScriptIR | None
    diagnostics: tuple[Diagnostic, ...]
