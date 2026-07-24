"""Private semantic carriers for structurally identified window expressions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._window_identity import WindowFunctionIdentity
from pietto.ast_nodes import DottedNameExpr, Expression, NameExpr, Span, WindowExpr
from pietto.semantic.model import (
    EffectiveNullability,
    TypeKind,
    ValueType,
    ValueTypeKind,
)

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


@dataclass(frozen=True, slots=True, kw_only=True)
class WindowExpressionAnalysis:
    """One core fact joined to its family and partition sibling evidence."""

    semantic_fact: WindowExpressionSemanticFact
    ranking_fact: RankingWindowSemanticFact | None
    distribution_fact: DistributionWindowSemanticFact | None
    partition_binding_fact: WindowPartitionBindingFact

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
        if self.ranking_fact is None and self.distribution_fact is None:
            raise ValueError("window analysis requires a family fact")

        identity_name = self.semantic_fact.identity.name
        if identity_name in {"row_number", "rank", "dense_rank"}:
            if self.ranking_fact is None or self.distribution_fact is not None:
                raise ValueError("ranking identity requires only a ranking fact")
            return
        if identity_name == "percent_rank":
            if self.ranking_fact is None or self.distribution_fact is None:
                raise ValueError("percent_rank requires both family facts")
            if self.distribution_fact.ranking_fact is not self.ranking_fact:
                raise ValueError(
                    "percent_rank distribution must reference the ranking fact"
                )
            return
        if identity_name in {"cume_dist", "ntile"}:
            if self.ranking_fact is not None or self.distribution_fact is None:
                raise ValueError(
                    "non-ranking distribution identity requires only a "
                    "distribution fact"
                )
            return
        raise ValueError("window analysis identity must be one completed identity")
