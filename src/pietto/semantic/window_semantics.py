"""Private semantic carriers for structurally identified window expressions."""

from __future__ import annotations

from dataclasses import dataclass
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
