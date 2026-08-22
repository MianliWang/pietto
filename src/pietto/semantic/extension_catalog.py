"""Private extension-catalog identity, target, and source-provenance schema."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from enum import StrEnum
from pathlib import PurePosixPath, PureWindowsPath

from pietto.semantic.generic_compatibility import LogicalTypeIdentity

__all__: tuple[str, ...] = ()


class ExtensionCatalogSchemaVersion(StrEnum):
    EXTENSION_CATALOG_V1 = "pietto.extension-catalog.v1"


def _require_text(value: object, label: str) -> str:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires exact nonblank text")
    return value


def _require_source_locator(value: object) -> str:
    locator = _require_text(value, "source locator")
    windows_path = PureWindowsPath(locator)
    if (
        PurePosixPath(locator).is_absolute()
        or windows_path.is_absolute()
        or bool(windows_path.root)
    ):
        raise ValueError("source locator forbids a host absolute path")
    return locator


@dataclass(frozen=True, slots=True)
class ExtensionCatalogIdentity:
    namespace: str
    name: str

    def __post_init__(self) -> None:
        _require_text(self.namespace, "catalog namespace")
        _require_text(self.name, "catalog name")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogReference:
    identity: ExtensionCatalogIdentity
    release: str

    def __post_init__(self) -> None:
        if type(self.identity) is not ExtensionCatalogIdentity:
            raise ValueError("catalog reference requires an exact identity")
        _require_text(self.release, "catalog release")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogTarget:
    database_family: str
    database_release: str
    extension_identity: str
    extension_release: str

    def __post_init__(self) -> None:
        _require_text(self.database_family, "database family")
        _require_text(self.database_release, "database release")
        _require_text(self.extension_identity, "extension identity")
        _require_text(self.extension_release, "extension release")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogSourceProvenance:
    source_authority: str
    source_revision: str
    source_locator: str
    curation: str

    def __post_init__(self) -> None:
        _require_text(self.source_authority, "source authority")
        _require_text(self.source_revision, "source revision")
        _require_source_locator(self.source_locator)
        _require_text(self.curation, "source curation")


@dataclass(frozen=True, slots=True)
class ExtensionCatalogSourceOccurrence:
    owner: ExtensionCatalogReference
    position: int
    provenance: ExtensionCatalogSourceProvenance

    def __post_init__(self) -> None:
        if type(self.owner) is not ExtensionCatalogReference:
            raise ValueError("catalog source occurrence requires an exact owner")
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "catalog source occurrence requires a non-negative position"
            )
        if type(self.provenance) is not ExtensionCatalogSourceProvenance:
            raise ValueError("catalog source occurrence requires exact provenance")


def _freeze_source_occurrences(
    values: Iterable[ExtensionCatalogSourceOccurrence],
) -> tuple[ExtensionCatalogSourceOccurrence, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("catalog source occurrences require an ordered iterable")
    try:
        occurrences = tuple(values)
    except TypeError as exc:
        raise ValueError(
            "catalog source occurrences require an ordered iterable"
        ) from exc
    if any(
        type(value) is not ExtensionCatalogSourceOccurrence for value in occurrences
    ):
        raise ValueError("catalog sources require exact occurrences")
    if any(
        occurrence.position != position
        for position, occurrence in enumerate(occurrences)
    ):
        raise ValueError("catalog source positions must be dense and source ordered")
    return occurrences


@dataclass(frozen=True, slots=True)
class ExtensionCatalogMetadata:
    schema_version: ExtensionCatalogSchemaVersion
    catalog: ExtensionCatalogReference
    target: ExtensionCatalogTarget
    source_occurrences: tuple[ExtensionCatalogSourceOccurrence, ...]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not ExtensionCatalogSchemaVersion:
            raise ValueError("catalog metadata requires an exact schema version")
        if type(self.catalog) is not ExtensionCatalogReference:
            raise ValueError("catalog metadata requires an exact catalog reference")
        if type(self.target) is not ExtensionCatalogTarget:
            raise ValueError("catalog metadata requires an exact target")
        occurrences = _freeze_source_occurrences(self.source_occurrences)
        if any(occurrence.owner is not self.catalog for occurrence in occurrences):
            raise ValueError("catalog sources require exact owner authority")
        object.__setattr__(self, "source_occurrences", occurrences)


class ExtensionCatalogTypeReferenceKind(StrEnum):
    PIETTO_LOGICAL = "pietto_logical"
    POSTGRES_BUILTIN = "postgres_builtin"
    EXTENSION_NATIVE = "extension_native"


@dataclass(frozen=True, slots=True)
class ExtensionCatalogTypeReference:
    kind: ExtensionCatalogTypeReferenceKind
    logical_type: LogicalTypeIdentity | None = None
    physical_name: str | None = None
    extension_identity: str | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ExtensionCatalogTypeReferenceKind:
            raise ValueError("catalog type reference requires an exact kind")
        if self.kind is ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL:
            if type(self.logical_type) is not LogicalTypeIdentity:
                raise ValueError("Pietto logical reference requires exact authority")
            if self.physical_name is not None or self.extension_identity is not None:
                raise ValueError("Pietto logical reference forbids physical identity")
            return
        if self.logical_type is not None:
            raise ValueError("PostgreSQL type reference forbids logical authority")
        _require_text(self.physical_name, "PostgreSQL physical type name")
        if self.kind is ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN:
            if self.extension_identity is not None:
                raise ValueError("PostgreSQL builtin reference forbids extension owner")
            return
        _require_text(self.extension_identity, "extension identity")


def _require_postgresql_type_reference(
    value: object,
    label: str,
) -> ExtensionCatalogTypeReference:
    if type(value) is not ExtensionCatalogTypeReference:
        raise ValueError(f"{label} requires an exact catalog type reference")
    if value.kind is ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL:
        raise ValueError(f"{label} requires a PostgreSQL-side type reference")
    return value


def _freeze_postgresql_type_references(
    values: Iterable[ExtensionCatalogTypeReference],
    label: str,
) -> tuple[ExtensionCatalogTypeReference, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f"{label} requires an ordered iterable")
    try:
        references = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{label} requires an ordered iterable") from exc
    for reference in references:
        _require_postgresql_type_reference(reference, label)
    return references


@dataclass(frozen=True, slots=True)
class PostgreSQLCallableIdentity:
    sql_name: str
    input_types: tuple[ExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.sql_name, "PostgreSQL callable name")
        object.__setattr__(
            self,
            "input_types",
            _freeze_postgresql_type_references(
                self.input_types,
                "PostgreSQL callable input types",
            ),
        )


class PostgreSQLOperatorArity(StrEnum):
    UNARY = "unary"
    BINARY = "binary"


@dataclass(frozen=True, slots=True)
class PostgreSQLOperatorIdentity:
    operator_name: str
    arity: PostgreSQLOperatorArity
    operand_types: tuple[ExtensionCatalogTypeReference, ...]

    def __post_init__(self) -> None:
        _require_text(self.operator_name, "PostgreSQL operator name")
        if type(self.arity) is not PostgreSQLOperatorArity:
            raise ValueError("PostgreSQL operator requires an exact arity")
        operands = _freeze_postgresql_type_references(
            self.operand_types,
            "PostgreSQL operator operand types",
        )
        expected_arity = 1 if self.arity is PostgreSQLOperatorArity.UNARY else 2
        if len(operands) != expected_arity:
            raise ValueError("PostgreSQL operator arity must match its operands")
        object.__setattr__(self, "operand_types", operands)


@dataclass(frozen=True, slots=True)
class PostgreSQLCastIdentity:
    source_type: ExtensionCatalogTypeReference
    target_type: ExtensionCatalogTypeReference

    def __post_init__(self) -> None:
        _require_postgresql_type_reference(
            self.source_type,
            "PostgreSQL cast source",
        )
        _require_postgresql_type_reference(
            self.target_type,
            "PostgreSQL cast target",
        )


class ExtensionCatalogDeclarationTypeUseKind(StrEnum):
    EXACT = "exact"
    UNMODELED = "unmodeled"


class ExtensionCatalogUnmodeledReason(StrEnum):
    UNSUPPORTED_TYPE_FORM = "unsupported_type_form"
    DEFAULT_ARGUMENTS = "default_arguments"
    VARIADIC_ARGUMENTS = "variadic_arguments"
    POLYMORPHIC_OR_PSEUDO_TYPE = "polymorphic_or_pseudo_type"
    SET_RETURNING = "set_returning"
    TABLE_OR_COMPOSITE_RETURN = "table_or_composite_return"
    ORDERED_SET_OR_HYPOTHETICAL_SET_AGGREGATE = (
        "ordered_set_or_hypothetical_set_aggregate"
    )
    DIRECT_ARGUMENTS = "direct_arguments"


def _freeze_unmodeled_reasons(
    values: Iterable[ExtensionCatalogUnmodeledReason],
    label: str,
) -> tuple[ExtensionCatalogUnmodeledReason, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f"{label} requires an ordered iterable")
    try:
        reasons = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{label} requires an ordered iterable") from exc
    if any(type(reason) is not ExtensionCatalogUnmodeledReason for reason in reasons):
        raise ValueError(f"{label} requires exact unmodeled reasons")
    return reasons


@dataclass(frozen=True, slots=True)
class ExtensionCatalogDeclarationTypeUse:
    kind: ExtensionCatalogDeclarationTypeUseKind
    exact_type: ExtensionCatalogTypeReference | None = None
    source_spelling: str | None = None
    unmodeled_reasons: tuple[ExtensionCatalogUnmodeledReason, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not ExtensionCatalogDeclarationTypeUseKind:
            raise ValueError("declaration type use requires an exact kind")
        reasons = _freeze_unmodeled_reasons(
            self.unmodeled_reasons,
            "declaration type-use reasons",
        )
        object.__setattr__(self, "unmodeled_reasons", reasons)
        if self.kind is ExtensionCatalogDeclarationTypeUseKind.EXACT:
            if type(self.exact_type) is not ExtensionCatalogTypeReference:
                raise ValueError("exact declaration type use requires an exact type")
            if self.source_spelling is not None or reasons:
                raise ValueError("exact declaration type use forbids unmodeled data")
            return
        if self.exact_type is not None:
            raise ValueError("unmodeled declaration type use forbids an exact type")
        _require_text(self.source_spelling, "unmodeled source spelling")
        if not reasons:
            raise ValueError("unmodeled declaration type use requires reasons")


class ExtensionCatalogMatchability(StrEnum):
    EXACT_MATCHABLE = "exact_matchable"
    CATALOGED_UNMODELED = "cataloged_unmodeled"


class ExtensionCatalogExposure(StrEnum):
    DIRECT_SQL_SURFACE = "direct_sql_surface"
    IMPLEMENTATION_SUPPORT = "implementation_support"
    UNCLASSIFIED = "unclassified"


def _freeze_source_positions(values: Iterable[int]) -> tuple[int, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError("entry source positions require an ordered iterable")
    try:
        positions = tuple(values)
    except TypeError as exc:
        raise ValueError("entry source positions require an ordered iterable") from exc
    if any(type(position) is not int or position < 0 for position in positions):
        raise ValueError("entry source positions require non-negative exact integers")
    if not positions:
        raise ValueError("catalog entry requires at least one source position")
    return positions


@dataclass(frozen=True, slots=True)
class ExtensionCatalogEntryEvidence:
    matchability: ExtensionCatalogMatchability
    exposure: ExtensionCatalogExposure
    unmodeled_reasons: tuple[ExtensionCatalogUnmodeledReason, ...]
    source_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.matchability) is not ExtensionCatalogMatchability:
            raise ValueError("entry evidence requires exact matchability")
        if type(self.exposure) is not ExtensionCatalogExposure:
            raise ValueError("entry evidence requires exact exposure")
        reasons = _freeze_unmodeled_reasons(
            self.unmodeled_reasons,
            "entry unmodeled reasons",
        )
        positions = _freeze_source_positions(self.source_positions)
        if self.matchability is ExtensionCatalogMatchability.EXACT_MATCHABLE:
            if reasons:
                raise ValueError("exact-matchable entry forbids unmodeled reasons")
        elif not reasons:
            raise ValueError("cataloged-unmodeled entry requires reasons")
        object.__setattr__(self, "unmodeled_reasons", reasons)
        object.__setattr__(self, "source_positions", positions)


def _require_type_use(
    value: object,
    label: str,
) -> ExtensionCatalogDeclarationTypeUse:
    if type(value) is not ExtensionCatalogDeclarationTypeUse:
        raise ValueError(f"{label} requires an exact declaration type use")
    return value


def _freeze_type_uses(
    values: Iterable[ExtensionCatalogDeclarationTypeUse],
    label: str,
) -> tuple[ExtensionCatalogDeclarationTypeUse, ...]:
    if isinstance(values, (str, bytes, Mapping, Set)):
        raise ValueError(f"{label} requires an ordered iterable")
    try:
        uses = tuple(values)
    except TypeError as exc:
        raise ValueError(f"{label} requires an ordered iterable") from exc
    for type_use in uses:
        _require_type_use(type_use, label)
    return uses


def _physical_reference(
    type_use: ExtensionCatalogDeclarationTypeUse,
    label: str,
) -> ExtensionCatalogTypeReference | None:
    _require_type_use(type_use, label)
    if type_use.kind is ExtensionCatalogDeclarationTypeUseKind.UNMODELED:
        return None
    assert type_use.exact_type is not None
    return _require_postgresql_type_reference(type_use.exact_type, label)


def _type_use_reasons(
    type_uses: Iterable[ExtensionCatalogDeclarationTypeUse],
) -> tuple[ExtensionCatalogUnmodeledReason, ...]:
    return tuple(
        reason for type_use in type_uses for reason in type_use.unmodeled_reasons
    )


def _require_entry_evidence(value: object) -> ExtensionCatalogEntryEvidence:
    if type(value) is not ExtensionCatalogEntryEvidence:
        raise ValueError("catalog entry requires exact evidence")
    return value


def _validate_entry_matchability(
    evidence: ExtensionCatalogEntryEvidence,
    required_reasons: tuple[ExtensionCatalogUnmodeledReason, ...],
) -> None:
    _require_entry_evidence(evidence)
    if not required_reasons:
        return
    if evidence.matchability is not ExtensionCatalogMatchability.CATALOGED_UNMODELED:
        raise ValueError("unmodeled declaration cannot be exact-matchable")
    if any(reason not in evidence.unmodeled_reasons for reason in required_reasons):
        raise ValueError("entry evidence omits a required unmodeled reason")


def _require_bool(value: object, label: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{label} requires an exact boolean")
    return value


@dataclass(frozen=True, slots=True)
class PostgreSQLCallableDeclaration:
    sql_name: str
    input_types: tuple[ExtensionCatalogDeclarationTypeUse, ...]
    identity: PostgreSQLCallableIdentity | None

    def __post_init__(self) -> None:
        _require_text(self.sql_name, "PostgreSQL callable declaration name")
        inputs = _freeze_type_uses(
            self.input_types,
            "PostgreSQL callable declaration inputs",
        )
        references = tuple(
            _physical_reference(type_use, "PostgreSQL callable declaration input")
            for type_use in inputs
        )
        if all(reference is not None for reference in references):
            if type(self.identity) is not PostgreSQLCallableIdentity:
                raise ValueError("exact callable declaration requires an identity")
            expected = PostgreSQLCallableIdentity(
                self.sql_name,
                tuple(reference for reference in references if reference is not None),
            )
            if self.identity != expected:
                raise ValueError("callable declaration identity must match its types")
        elif self.identity is not None:
            raise ValueError("unmodeled callable declaration forbids exact identity")
        object.__setattr__(self, "input_types", inputs)


@dataclass(frozen=True, slots=True)
class ExtensionNativeTypeCatalogEntry:
    type_identity: ExtensionCatalogTypeReference
    logical_mapping: ExtensionCatalogTypeReference | None
    evidence: ExtensionCatalogEntryEvidence

    def __post_init__(self) -> None:
        if (
            type(self.type_identity) is not ExtensionCatalogTypeReference
            or self.type_identity.kind
            is not ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE
        ):
            raise ValueError("native type entry requires EXTENSION_NATIVE identity")
        if self.logical_mapping is not None and (
            type(self.logical_mapping) is not ExtensionCatalogTypeReference
            or self.logical_mapping.kind
            is not ExtensionCatalogTypeReferenceKind.PIETTO_LOGICAL
        ):
            raise ValueError("native type mapping requires PIETTO_LOGICAL identity")
        _validate_entry_matchability(_require_entry_evidence(self.evidence), ())


class PostgreSQLNullCallBehavior(StrEnum):
    UNKNOWN = "unknown"
    CALLED_ON_NULL_INPUT = "called_on_null_input"
    STRICT = "strict"


class PostgreSQLVolatility(StrEnum):
    UNKNOWN = "unknown"
    IMMUTABLE = "immutable"
    STABLE = "stable"
    VOLATILE = "volatile"


class PostgreSQLParallelSafety(StrEnum):
    UNKNOWN = "unknown"
    UNSAFE = "unsafe"
    RESTRICTED = "restricted"
    SAFE = "safe"


@dataclass(frozen=True, slots=True)
class ExtensionScalarFunctionCatalogEntry:
    declaration: PostgreSQLCallableDeclaration
    result_type: ExtensionCatalogDeclarationTypeUse
    null_call_behavior: PostgreSQLNullCallBehavior
    volatility: PostgreSQLVolatility
    parallel_safety: PostgreSQLParallelSafety
    has_default_arguments: bool
    is_variadic: bool
    returns_set: bool
    has_polymorphic_or_pseudo_types: bool
    evidence: ExtensionCatalogEntryEvidence

    def __post_init__(self) -> None:
        if type(self.declaration) is not PostgreSQLCallableDeclaration:
            raise ValueError("scalar function entry requires exact declaration")
        _physical_reference(self.result_type, "scalar function result")
        if type(self.null_call_behavior) is not PostgreSQLNullCallBehavior:
            raise ValueError("scalar function entry requires null-call behavior")
        if type(self.volatility) is not PostgreSQLVolatility:
            raise ValueError("scalar function entry requires exact volatility")
        if type(self.parallel_safety) is not PostgreSQLParallelSafety:
            raise ValueError("scalar function entry requires exact parallel safety")
        _require_bool(self.has_default_arguments, "default-argument posture")
        _require_bool(self.is_variadic, "variadic posture")
        _require_bool(self.returns_set, "set-returning posture")
        _require_bool(
            self.has_polymorphic_or_pseudo_types,
            "polymorphic or pseudo-type posture",
        )
        required_reasons = (
            *_type_use_reasons(self.declaration.input_types),
            *_type_use_reasons((self.result_type,)),
            *(
                (ExtensionCatalogUnmodeledReason.DEFAULT_ARGUMENTS,)
                if self.has_default_arguments
                else ()
            ),
            *(
                (ExtensionCatalogUnmodeledReason.VARIADIC_ARGUMENTS,)
                if self.is_variadic
                else ()
            ),
            *(
                (ExtensionCatalogUnmodeledReason.SET_RETURNING,)
                if self.returns_set
                else ()
            ),
            *(
                (ExtensionCatalogUnmodeledReason.POLYMORPHIC_OR_PSEUDO_TYPE,)
                if self.has_polymorphic_or_pseudo_types
                else ()
            ),
        )
        _validate_entry_matchability(self.evidence, required_reasons)


class PostgreSQLAggregateKind(StrEnum):
    ORDINARY = "ordinary"
    ORDERED_SET = "ordered_set"
    HYPOTHETICAL_SET = "hypothetical_set"


@dataclass(frozen=True, slots=True)
class ExtensionAggregateCatalogEntry:
    kind: PostgreSQLAggregateKind
    declaration: PostgreSQLCallableDeclaration
    result_type: ExtensionCatalogDeclarationTypeUse
    parallel_safety: PostgreSQLParallelSafety
    has_direct_arguments: bool
    is_variadic: bool
    evidence: ExtensionCatalogEntryEvidence

    def __post_init__(self) -> None:
        if type(self.kind) is not PostgreSQLAggregateKind:
            raise ValueError("aggregate entry requires an exact kind")
        if type(self.declaration) is not PostgreSQLCallableDeclaration:
            raise ValueError("aggregate entry requires exact declaration")
        _physical_reference(self.result_type, "aggregate result")
        if type(self.parallel_safety) is not PostgreSQLParallelSafety:
            raise ValueError("aggregate entry requires exact parallel safety")
        _require_bool(self.has_direct_arguments, "aggregate direct-argument posture")
        _require_bool(self.is_variadic, "aggregate variadic posture")
        required_reasons = (
            *_type_use_reasons(self.declaration.input_types),
            *_type_use_reasons((self.result_type,)),
            *(
                (
                    ExtensionCatalogUnmodeledReason.ORDERED_SET_OR_HYPOTHETICAL_SET_AGGREGATE,
                )
                if self.kind is not PostgreSQLAggregateKind.ORDINARY
                else ()
            ),
            *(
                (ExtensionCatalogUnmodeledReason.DIRECT_ARGUMENTS,)
                if self.has_direct_arguments
                else ()
            ),
            *(
                (ExtensionCatalogUnmodeledReason.VARIADIC_ARGUMENTS,)
                if self.is_variadic
                else ()
            ),
        )
        _validate_entry_matchability(self.evidence, required_reasons)


@dataclass(frozen=True, slots=True)
class ExtensionOperatorCatalogEntry:
    operator_name: str
    arity: PostgreSQLOperatorArity
    operand_types: tuple[ExtensionCatalogDeclarationTypeUse, ...]
    identity: PostgreSQLOperatorIdentity | None
    result_type: ExtensionCatalogDeclarationTypeUse
    evidence: ExtensionCatalogEntryEvidence

    def __post_init__(self) -> None:
        _require_text(self.operator_name, "operator declaration name")
        if type(self.arity) is not PostgreSQLOperatorArity:
            raise ValueError("operator entry requires an exact arity")
        operands = _freeze_type_uses(
            self.operand_types, "operator declaration operands"
        )
        expected_arity = 1 if self.arity is PostgreSQLOperatorArity.UNARY else 2
        if len(operands) != expected_arity:
            raise ValueError("operator declaration arity must match its operands")
        references = tuple(
            _physical_reference(type_use, "operator declaration operand")
            for type_use in operands
        )
        if all(reference is not None for reference in references):
            if type(self.identity) is not PostgreSQLOperatorIdentity:
                raise ValueError("exact operator declaration requires an identity")
            expected = PostgreSQLOperatorIdentity(
                self.operator_name,
                self.arity,
                tuple(reference for reference in references if reference is not None),
            )
            if self.identity != expected:
                raise ValueError("operator identity must match its declaration")
        elif self.identity is not None:
            raise ValueError("unmodeled operator declaration forbids exact identity")
        _physical_reference(self.result_type, "operator result")
        required_reasons = (
            *_type_use_reasons(operands),
            *_type_use_reasons((self.result_type,)),
        )
        _validate_entry_matchability(self.evidence, required_reasons)
        object.__setattr__(self, "operand_types", operands)


class PostgreSQLCastContext(StrEnum):
    UNKNOWN = "unknown"
    EXPLICIT_ONLY = "explicit_only"
    ASSIGNMENT = "assignment"
    IMPLICIT = "implicit"


class PostgreSQLCastMethod(StrEnum):
    UNKNOWN = "unknown"
    FUNCTION = "function"
    BINARY = "binary"
    INOUT = "inout"


@dataclass(frozen=True, slots=True)
class ExtensionCastCatalogEntry:
    source_type: ExtensionCatalogDeclarationTypeUse
    target_type: ExtensionCatalogDeclarationTypeUse
    identity: PostgreSQLCastIdentity | None
    context: PostgreSQLCastContext
    method: PostgreSQLCastMethod
    evidence: ExtensionCatalogEntryEvidence

    def __post_init__(self) -> None:
        source_reference = _physical_reference(self.source_type, "cast source")
        target_reference = _physical_reference(self.target_type, "cast target")
        if source_reference is not None and target_reference is not None:
            if type(self.identity) is not PostgreSQLCastIdentity:
                raise ValueError("exact cast declaration requires an identity")
            expected = PostgreSQLCastIdentity(source_reference, target_reference)
            if self.identity != expected:
                raise ValueError("cast identity must match its declaration")
        elif self.identity is not None:
            raise ValueError("unmodeled cast declaration forbids exact identity")
        if type(self.context) is not PostgreSQLCastContext:
            raise ValueError("cast entry requires an exact context")
        if type(self.method) is not PostgreSQLCastMethod:
            raise ValueError("cast entry requires an exact method")
        required_reasons = (
            *_type_use_reasons((self.source_type,)),
            *_type_use_reasons((self.target_type,)),
        )
        _validate_entry_matchability(self.evidence, required_reasons)
