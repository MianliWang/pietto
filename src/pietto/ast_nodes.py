"""ANTLR-independent abstract syntax tree nodes for Pietto source."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from pietto import _window_identity


@dataclass(frozen=True, slots=True, kw_only=True)
class Span:
    """A 1-based, half-open source range: [line:column, end_line:end_column)."""

    path: str | None
    line: int
    column: int
    end_line: int
    end_column: int


@dataclass(frozen=True, slots=True, kw_only=True)
class Node:
    """Base class for source-located Pietto AST nodes."""

    span: Span


@dataclass(frozen=True, slots=True, kw_only=True)
class Header(Node):
    """Optional file-level language and backend settings."""

    version: str | None = None
    mode: str | None = None
    dialect: str | None = None
    encoding: str | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class Expression(Node):
    """Base class for parsed expressions without semantic typing."""

    pass


@dataclass(frozen=True, slots=True, kw_only=True)
class LiteralExpr(Expression):
    """A scalar literal expression."""

    value: str | int | float | bool | None


@dataclass(frozen=True, slots=True, kw_only=True)
class NameExpr(Expression):
    """A reference to one identifier."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class DottedNameExpr(Expression):
    """A qualified identifier reference such as ``user.email``."""

    parts: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CallExpr(Expression):
    """A call whose callee is a name or dotted name."""

    callee: NameExpr | DottedNameExpr
    arguments: tuple[Expression, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class UnaryExpr(Expression):
    """A prefix arithmetic expression."""

    operator: str
    operand: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BinaryExpr(Expression):
    """A binary arithmetic or Boolean expression."""

    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class ComparisonExpr(Expression):
    """A comparison between two expressions."""

    left: Expression
    operator: str
    right: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class BetweenExpr(Expression):
    """An inclusive ``between`` comparison."""

    value: Expression
    lower: Expression
    upper: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class IsNullExpr(Expression):
    """An ``is null`` or ``is not null`` predicate."""

    value: Expression
    negated: bool


class WindowFrameUnit(StrEnum):
    """Closed frame units shared by authored AST and semantic stages."""

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


class WindowUseKind(StrEnum):
    """Closed authored inline, direct-name, and extended-name use forms."""

    INLINE = "inline"
    NAMED_DIRECT = "named_direct"
    NAMED_EXTENDED = "named_extended"


class WindowNullTreatmentKind(StrEnum):
    """Closed explicit NULL-treatment spellings on one function use."""

    RESPECT = "respect"
    IGNORE = "ignore"


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthoredWindowNullTreatment(Node):
    """One explicit source-located NULL-treatment modifier."""

    kind: WindowNullTreatmentKind

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowNullTreatmentKind:
            raise TypeError("window NULL treatment kind must be exact")


class WindowNthDirectionKind(StrEnum):
    """Closed explicit nth-value traversal-direction spellings."""

    FIRST = "first"
    LAST = "last"


@dataclass(frozen=True, slots=True, kw_only=True)
class AuthoredWindowNthDirection(Node):
    """One explicit source-located nth-value traversal modifier."""

    kind: WindowNthDirectionKind

    def __post_init__(self) -> None:
        if type(self.kind) is not WindowNthDirectionKind:
            raise TypeError("window nth direction kind must be exact")


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowReference(Node):
    """One exact source occurrence of a query-local named-window lookup."""

    name: str

    def __post_init__(self) -> None:
        if type(self.name) is not str:
            raise TypeError("named-window reference name must be an exact string")
        if not self.name:
            raise ValueError("named-window reference name must be nonempty")


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeArgument(Node):
    """A positional or named argument in a type expression."""

    name: str | None
    value: Expression


class Nullability(StrEnum):
    """Explicit syntax state recorded for a parsed type expression."""

    IMPLICIT = "implicit"
    NULLABLE = "nullable"
    NOT_NULL = "not_null"


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeExpr(Node):
    """A parsed type reference with arguments and three-state nullability."""

    name: str
    arguments: tuple[TypeArgument, ...]
    nullability: Nullability


@dataclass(frozen=True, slots=True, kw_only=True)
class Parameter(Node):
    """A named parameter with its declared type."""

    name: str
    type: TypeExpr


@dataclass(frozen=True, slots=True, kw_only=True)
class EnsureClause(Node):
    """A parsed value guarantee attached to a type or field."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class Annotation(Node):
    """A parse-only bare annotation attached to a declaration."""

    name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class TypeDef(Node):
    """A named type definition and its parsed guarantees."""

    name: str
    base: TypeExpr
    ensures: tuple[EnsureClause, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class EnumDef(Node):
    """A named enumeration definition."""

    name: str
    members: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class FieldDef(Node):
    """A parse-only shape field with an optional derived value expression."""

    name: str
    type_expr: TypeExpr
    derive_expression: Expression | None
    annotations: tuple[Annotation, ...]
    ensure_clauses: tuple[EnsureClause, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class CheckDef(Node):
    """A named, parse-only shape invariant containing one expression."""

    name: str
    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class UniqueDef(Node):
    """A named, parse-only uniqueness clause over ordered field names."""

    name: str
    field_names: tuple[str, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class IndexDef(Node):
    """A named, parse-only index hint with an optional predicate."""

    name: str
    field_names: tuple[str, ...]
    predicate: Expression | None


ShapeItem = FieldDef | CheckDef | UniqueDef | IndexDef


@dataclass(frozen=True, slots=True, kw_only=True)
class ShapeDef(Node):
    """A parse-only shape definition containing source-ordered items."""

    name: str
    items: tuple[ShapeItem, ...]

    @property
    def fields(self) -> tuple[FieldDef, ...]:
        """Return fields in source order for compatibility and convenience."""

        return tuple(item for item in self.items if isinstance(item, FieldDef))

    @property
    def checks(self) -> tuple[CheckDef, ...]:
        """Return shape checks in source order."""

        return tuple(item for item in self.items if isinstance(item, CheckDef))

    @property
    def uniques(self) -> tuple[UniqueDef, ...]:
        """Return unique clauses in source order."""

        return tuple(item for item in self.items if isinstance(item, UniqueDef))

    @property
    def indexes(self) -> tuple[IndexDef, ...]:
        """Return index clauses in source order."""

        return tuple(item for item in self.items if isinstance(item, IndexDef))


@dataclass(frozen=True, slots=True, kw_only=True)
class ConstraintDef(Node):
    """A parse-only constraint whose return type remains a syntax-level TypeExpr."""

    name: str
    parameters: tuple[Parameter, ...]
    return_type: TypeExpr
    body: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class DeriveDef(Node):
    """A parse-only derive whose return type remains a syntax-level TypeExpr."""

    name: str
    parameters: tuple[Parameter, ...]
    return_type: TypeExpr
    body: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class SourceDef(Node):
    """A parse-only binding from a Pietto name to a connector expression."""

    name: str
    shape_name: str | None
    connector: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipEndpoint(Node):
    """One parse-only endpoint in a relationship metadata declaration."""

    local_name: str
    relation_name: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipMatchClause(Node):
    """One optional authored relationship base-match expression."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class RelationshipMetadata(Node):
    """Relationship metadata with two endpoints and an optional base match."""

    name: str
    endpoints: tuple[RelationshipEndpoint, RelationshipEndpoint]
    base_match: RelationshipMatchClause | None = None


class ModuleDeclarationKind(StrEnum):
    """The closed declaration-kind vocabulary accepted by module items."""

    TYPE = "type"
    ENUM = "enum"
    SHAPE = "shape"
    SOURCE = "source"
    TABLE = "table"
    QUERY = "query"


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportItem(Node):
    """One source-ordered declaration requested from an import target."""

    declaration_kind: ModuleDeclarationKind
    exported_name: str
    local_name: str | None
    declaration_kind_span: Span
    exported_name_span: Span
    local_name_span: Span | None


@dataclass(frozen=True, slots=True, kw_only=True)
class ImportStatement(Node):
    """One parser-only import block without resolution or binding facts."""

    target: str
    target_span: Span
    items: tuple[ImportItem, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class ExportItem(Node):
    """One source-ordered local declaration named by an export block."""

    declaration_kind: ModuleDeclarationKind
    local_name: str
    declaration_kind_span: Span
    local_name_span: Span


@dataclass(frozen=True, slots=True, kw_only=True)
class ExportStatement(Node):
    """One parser-only export block without visibility or binding facts."""

    items: tuple[ExportItem, ...]


ModuleStatement = ImportStatement | ExportStatement


@dataclass(frozen=True, slots=True, kw_only=True)
class FromClause(Node):
    """A parse-only relation input reference."""

    source_name: str


class AuthoredJoinKind(StrEnum):
    """The two authored JOIN forms owned by Phase 62."""

    INNER = "inner"
    LEFT = "left"


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinTraversalStep(Node):
    """One exact authored relationship traversal step."""

    relationship_name: str
    source_endpoint_role: str
    target_endpoint_role: str


@dataclass(frozen=True, slots=True, kw_only=True)
class JoinClause(Node):
    """One authored INNER or LEFT relationship JOIN occurrence."""

    kind: AuthoredJoinKind
    target_relation_name: str
    target_binding_name: str
    source_binding_name: str
    traversal_steps: tuple[JoinTraversalStep, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not AuthoredJoinKind:
            raise TypeError("join kind must be an exact authored JOIN kind")
        if type(self.traversal_steps) is not tuple or any(
            type(step) is not JoinTraversalStep for step in self.traversal_steps
        ):
            raise TypeError("join traversal steps must be an exact tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class LetBinding(Node):
    """One parse-only relation-local let binding."""

    name: str
    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class LetClause(Node):
    """A parse-only relation let block with source-ordered bindings."""

    bindings: tuple[LetBinding, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class WhereClause(Node):
    """A parse-only relation row filter."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupByItem(Node):
    """One source-ordered parse-only grouping key."""

    key: NameExpr | DottedNameExpr


@dataclass(frozen=True, slots=True, kw_only=True)
class GroupByClause(Node):
    """A non-empty parse-only relation grouping block."""

    items: tuple[GroupByItem, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class SelectItem(Node):
    """An ordered relation projection with an optional local alias."""

    alias: str | None
    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class SatisfyingClause(Node):
    """A parse-only relation result predicate."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class QualifyClause(Node):
    """A parse-only post-window relation predicate."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderItem(Node):
    """One source-ordered sorting expression and optional direction."""

    expression: Expression
    direction: str | None


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowSpec(Node):
    """A source-located authored window-component bundle."""

    partition_by: tuple[Expression, ...]
    order_by: tuple[OrderItem, ...]
    frame: AuthoredWindowFrame = field(
        default_factory=lambda: AuthoredWindowFrame(
            kind=AuthoredWindowFrameKind.OMITTED
        )
    )

    def __post_init__(self) -> None:
        """Enforce the immutable component tuple and frame shapes."""

        if type(self.partition_by) is not tuple:
            raise TypeError("partition_by must be an exact tuple")
        if type(self.order_by) is not tuple:
            raise TypeError("order_by must be an exact tuple")
        if not all(isinstance(item, Expression) for item in self.partition_by):
            raise TypeError("partition_by items must be Expression instances")
        if not all(isinstance(item, OrderItem) for item in self.order_by):
            raise TypeError("order_by items must be OrderItem instances")
        if type(self.frame) is not AuthoredWindowFrame:
            raise TypeError("window frame must be an exact AuthoredWindowFrame")

    @property
    def has_components(self) -> bool:
        """Whether this bundle explicitly authors any component."""

        return bool(
            self.partition_by
            or self.order_by
            or self.frame.kind is not AuthoredWindowFrameKind.OMITTED
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class NamedWindowDeclaration(Node):
    """One query-local named-window declaration in exact source order."""

    name: str
    base: NamedWindowReference | None
    spec: WindowSpec | None

    def __post_init__(self) -> None:
        if type(self.name) is not str:
            raise TypeError("named-window declaration name must be an exact string")
        if not self.name:
            raise ValueError("named-window declaration name must be nonempty")
        if self.base is not None and type(self.base) is not NamedWindowReference:
            raise TypeError("named-window declaration base must be exact or absent")
        if self.spec is not None and type(self.spec) is not WindowSpec:
            raise TypeError("named-window declaration spec must be exact or absent")
        if self.spec is not None and not self.spec.has_components:
            raise ValueError("named-window declaration colon blocks must be nonempty")


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpr(Expression):
    """A direct call paired with one authored inline or named window use."""

    call: CallExpr
    spec: WindowSpec
    identity: _window_identity.WindowFunctionIdentity
    use_kind: WindowUseKind = WindowUseKind.INLINE
    base: NamedWindowReference | None = None
    nth_direction: AuthoredWindowNthDirection | None = None
    null_treatment: AuthoredWindowNullTreatment | None = None

    def __post_init__(self) -> None:
        """Enforce the indivisible parsed window-expression shape."""

        if not isinstance(self.call, CallExpr):
            raise TypeError("call must be a CallExpr")
        if not isinstance(self.spec, WindowSpec):
            raise TypeError("spec must be a WindowSpec")
        if type(self.identity) is not _window_identity.WindowFunctionIdentity:
            raise TypeError("identity must be a WindowFunctionIdentity")
        if type(self.use_kind) is not WindowUseKind:
            raise TypeError("window use kind must be an exact WindowUseKind")
        if self.base is not None and type(self.base) is not NamedWindowReference:
            raise TypeError("window use base must be exact or absent")
        if (
            self.nth_direction is not None
            and type(self.nth_direction) is not AuthoredWindowNthDirection
        ):
            raise TypeError("window nth direction must be exact or absent")
        if (
            self.null_treatment is not None
            and type(self.null_treatment) is not AuthoredWindowNullTreatment
        ):
            raise TypeError("window NULL treatment must be exact or absent")
        if self.use_kind is WindowUseKind.INLINE:
            if self.base is not None or not self.spec.has_components:
                raise ValueError("inline window uses require only local components")
        elif self.base is None:
            raise ValueError("named window uses require one exact base reference")
        elif self.use_kind is WindowUseKind.NAMED_DIRECT:
            if self.spec.has_components:
                raise ValueError("direct named-window uses forbid local components")
        elif not self.spec.has_components:
            raise ValueError("extended named-window uses require local components")


@dataclass(frozen=True, slots=True, kw_only=True)
class OrderByClause(Node):
    """A non-empty relation sorting block."""

    items: tuple[OrderItem, ...]


@dataclass(frozen=True, slots=True, kw_only=True)
class LimitClause(Node):
    """A relation row-count clause whose operand awaits semantic validation."""

    expression: Expression


@dataclass(frozen=True, slots=True, kw_only=True)
class TableDef(Node):
    """A parse-only table definition."""

    name: str
    from_clause: FromClause
    where_clause: WhereClause | None
    group_by_clause: GroupByClause | None
    select_items: tuple[SelectItem, ...]
    order_by_clause: OrderByClause | None = None
    limit_clause: LimitClause | None = None
    satisfying_clause: SatisfyingClause | None = None
    qualify_clause: QualifyClause | None = None
    let_clause: LetClause | None = None
    named_windows: tuple[NamedWindowDeclaration, ...] = ()
    join_clauses: tuple[JoinClause, ...] = ()

    def __post_init__(self) -> None:
        if type(self.named_windows) is not tuple or any(
            type(item) is not NamedWindowDeclaration for item in self.named_windows
        ):
            raise TypeError("table named windows must be an exact declaration tuple")
        if type(self.join_clauses) is not tuple or any(
            type(item) is not JoinClause for item in self.join_clauses
        ):
            raise TypeError("table joins must be an exact clause tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class QueryDef(Node):
    """A parse-only query definition."""

    name: str
    from_clause: FromClause
    where_clause: WhereClause | None
    group_by_clause: GroupByClause | None
    select_items: tuple[SelectItem, ...]
    order_by_clause: OrderByClause | None = None
    limit_clause: LimitClause | None = None
    satisfying_clause: SatisfyingClause | None = None
    qualify_clause: QualifyClause | None = None
    let_clause: LetClause | None = None
    named_windows: tuple[NamedWindowDeclaration, ...] = ()
    join_clauses: tuple[JoinClause, ...] = ()

    def __post_init__(self) -> None:
        if type(self.named_windows) is not tuple or any(
            type(item) is not NamedWindowDeclaration for item in self.named_windows
        ):
            raise TypeError("query named windows must be an exact declaration tuple")
        if type(self.join_clauses) is not tuple or any(
            type(item) is not JoinClause for item in self.join_clauses
        ):
            raise TypeError("query joins must be an exact clause tuple")


Definition = (
    TypeDef
    | EnumDef
    | ConstraintDef
    | DeriveDef
    | ShapeDef
    | SourceDef
    | TableDef
    | QueryDef
)


@dataclass(frozen=True, slots=True, kw_only=True)
class Script(Node):
    """The root node for one parsed Pietto source file."""

    header: Header | None
    definitions: tuple[Definition, ...]
    relationships: tuple[RelationshipMetadata, ...] = ()
    module_statements: tuple[ModuleStatement, ...] = ()
