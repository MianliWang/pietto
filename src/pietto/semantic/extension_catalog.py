"""Private extension-catalog schema, entries, and constructed artifact."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass, field, fields, is_dataclass, replace
from enum import StrEnum
import hashlib
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
        if any(occurrence.owner != self.catalog for occurrence in occurrences):
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


type _ExtensionCatalogEntry = (
    ExtensionNativeTypeCatalogEntry
    | ExtensionScalarFunctionCatalogEntry
    | ExtensionAggregateCatalogEntry
    | ExtensionOperatorCatalogEntry
    | ExtensionCastCatalogEntry
)
type _ExtensionCatalogLookupIdentity = (
    ExtensionCatalogTypeReference
    | PostgreSQLCallableIdentity
    | PostgreSQLOperatorIdentity
    | PostgreSQLCastIdentity
)


class ExtensionCatalogEntryFamily(StrEnum):
    NATIVE_TYPE = "native_type"
    SCALAR_FUNCTION = "scalar_function"
    AGGREGATE = "aggregate"
    OPERATOR = "operator"
    CAST = "cast"


def _validate_lookup_identity(
    family: ExtensionCatalogEntryFamily,
    identity: object,
) -> _ExtensionCatalogLookupIdentity:
    if family is ExtensionCatalogEntryFamily.NATIVE_TYPE:
        if (
            type(identity) is not ExtensionCatalogTypeReference
            or identity.kind is not ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE
        ):
            raise ValueError("native-type lookup scope requires exact native identity")
    elif family in {
        ExtensionCatalogEntryFamily.SCALAR_FUNCTION,
        ExtensionCatalogEntryFamily.AGGREGATE,
    }:
        if type(identity) is not PostgreSQLCallableIdentity:
            raise ValueError("callable lookup scope requires exact callable identity")
    elif family is ExtensionCatalogEntryFamily.OPERATOR:
        if type(identity) is not PostgreSQLOperatorIdentity:
            raise ValueError("operator lookup scope requires exact operator identity")
    elif type(identity) is not PostgreSQLCastIdentity:
        raise ValueError("cast lookup scope requires exact cast identity")
    return identity


@dataclass(frozen=True, slots=True)
class ExtensionCatalogLookupScope:
    family: ExtensionCatalogEntryFamily
    identity: _ExtensionCatalogLookupIdentity

    def __post_init__(self) -> None:
        if type(self.family) is not ExtensionCatalogEntryFamily:
            raise ValueError("catalog lookup scope requires an exact entry family")
        _validate_lookup_identity(self.family, self.identity)


class ExtensionCatalogCompletenessClaimKind(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"


@dataclass(frozen=True, slots=True)
class ExtensionCatalogCompletenessClaim:
    scope: ExtensionCatalogLookupScope
    kind: ExtensionCatalogCompletenessClaimKind
    source_positions: tuple[int, ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not ExtensionCatalogLookupScope:
            raise ValueError("completeness claim requires an exact lookup scope")
        if type(self.kind) is not ExtensionCatalogCompletenessClaimKind:
            raise ValueError("completeness claim requires an exact kind")
        object.__setattr__(
            self,
            "source_positions",
            _freeze_source_positions(self.source_positions),
        )


class ExtensionCatalogExactEntryGroupState(StrEnum):
    UNIQUE = "unique"
    CONSISTENT_DUPLICATE = "consistent_duplicate"
    EVIDENCE_CONFLICT = "evidence_conflict"


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogExactEntryGroup:
    scope: ExtensionCatalogLookupScope
    state: ExtensionCatalogExactEntryGroupState
    entries: tuple[_ExtensionCatalogEntry, ...]

    def __new__(cls) -> ExtensionCatalogExactEntryGroup:
        raise TypeError("exact entry groups require canonical construction")


class ExtensionCatalogCompletenessState(StrEnum):
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    CONFLICT = "conflict"


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogCompletenessGroup:
    scope: ExtensionCatalogLookupScope
    state: ExtensionCatalogCompletenessState
    claims: tuple[ExtensionCatalogCompletenessClaim, ...]

    def __new__(cls) -> ExtensionCatalogCompletenessGroup:
        raise TypeError("completeness groups require canonical construction")


class ExtensionCatalogStructuralFailureKind(StrEnum):
    INVALID_METADATA = "invalid_metadata"
    INVALID_ENTRY_COLLECTION = "invalid_entry_collection"
    INVALID_ENTRY = "invalid_entry"
    INVALID_COMPLETENESS_COLLECTION = "invalid_completeness_collection"
    INVALID_COMPLETENESS_DECLARATION = "invalid_completeness_declaration"
    SOURCE_POSITION_SEQUENCE_MISMATCH = "source_position_sequence_mismatch"
    SOURCE_OWNER_MISMATCH = "source_owner_mismatch"
    ENTRY_SOURCE_POSITION_OUT_OF_RANGE = "entry_source_position_out_of_range"
    COMPLETENESS_SOURCE_POSITION_OUT_OF_RANGE = (
        "completeness_source_position_out_of_range"
    )


@dataclass(frozen=True, slots=True)
class ExtensionCatalogStructuralFailure:
    kind: ExtensionCatalogStructuralFailureKind
    item_position: int | None = None
    source_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.kind) is not ExtensionCatalogStructuralFailureKind:
            raise ValueError("catalog structural failure requires an exact kind")
        for value in (self.item_position, self.source_position):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("catalog structural failure positions must be exact")


@dataclass(frozen=True, slots=True, init=False)
class ConstructedExtensionCatalog:
    metadata: ExtensionCatalogMetadata
    entries: tuple[_ExtensionCatalogEntry, ...]
    exact_entry_groups: tuple[ExtensionCatalogExactEntryGroup, ...]
    completeness_claims: tuple[ExtensionCatalogCompletenessClaim, ...]
    completeness_groups: tuple[ExtensionCatalogCompletenessGroup, ...]
    canonical_bytes: bytes = field(repr=False)
    content_sha256: str

    def __new__(cls) -> ConstructedExtensionCatalog:
        raise TypeError("constructed extension catalogs require canonical construction")


@dataclass(frozen=True, slots=True, init=False)
class ExtensionCatalogConstructionResult:
    catalog: ConstructedExtensionCatalog | None
    failures: tuple[ExtensionCatalogStructuralFailure, ...]

    def __new__(cls) -> ExtensionCatalogConstructionResult:
        raise TypeError("catalog construction results require canonical construction")

    @property
    def ok(self) -> bool:
        return self.catalog is not None


def _entry_family(entry: _ExtensionCatalogEntry) -> ExtensionCatalogEntryFamily:
    if isinstance(entry, ExtensionNativeTypeCatalogEntry):
        return ExtensionCatalogEntryFamily.NATIVE_TYPE
    if isinstance(entry, ExtensionScalarFunctionCatalogEntry):
        return ExtensionCatalogEntryFamily.SCALAR_FUNCTION
    if isinstance(entry, ExtensionAggregateCatalogEntry):
        return ExtensionCatalogEntryFamily.AGGREGATE
    if isinstance(entry, ExtensionOperatorCatalogEntry):
        return ExtensionCatalogEntryFamily.OPERATOR
    if isinstance(entry, ExtensionCastCatalogEntry):
        return ExtensionCatalogEntryFamily.CAST
    raise TypeError("catalog entry requires one exact entry family")


def _entry_scope(
    entry: _ExtensionCatalogEntry,
) -> ExtensionCatalogLookupScope | None:
    if entry.evidence.matchability is not ExtensionCatalogMatchability.EXACT_MATCHABLE:
        return None
    family = _entry_family(entry)
    if isinstance(entry, ExtensionNativeTypeCatalogEntry):
        identity: _ExtensionCatalogLookupIdentity | None = entry.type_identity
    elif isinstance(
        entry,
        (ExtensionScalarFunctionCatalogEntry, ExtensionAggregateCatalogEntry),
    ):
        identity = entry.declaration.identity
    elif isinstance(entry, (ExtensionOperatorCatalogEntry, ExtensionCastCatalogEntry)):
        identity = entry.identity
    else:
        raise TypeError("catalog entry requires one exact entry family")
    if identity is None:
        raise ValueError("exact-matchable entry requires an exact lookup identity")
    return ExtensionCatalogLookupScope(family, identity)


def _entry_semantic_payload(entry: _ExtensionCatalogEntry) -> tuple[object, ...]:
    evidence = entry.evidence
    common: tuple[object, ...] = (
        evidence.matchability,
        evidence.exposure,
        evidence.unmodeled_reasons,
    )
    if isinstance(entry, ExtensionNativeTypeCatalogEntry):
        return (entry.type_identity, entry.logical_mapping, *common)
    if isinstance(entry, ExtensionScalarFunctionCatalogEntry):
        return (
            entry.declaration,
            entry.result_type,
            entry.null_call_behavior,
            entry.volatility,
            entry.parallel_safety,
            entry.has_default_arguments,
            entry.is_variadic,
            entry.returns_set,
            entry.has_polymorphic_or_pseudo_types,
            *common,
        )
    if isinstance(entry, ExtensionAggregateCatalogEntry):
        return (
            entry.kind,
            entry.declaration,
            entry.result_type,
            entry.parallel_safety,
            entry.has_direct_arguments,
            entry.is_variadic,
            *common,
        )
    if isinstance(entry, ExtensionOperatorCatalogEntry):
        return (
            entry.operator_name,
            entry.arity,
            entry.operand_types,
            entry.identity,
            entry.result_type,
            *common,
        )
    if isinstance(entry, ExtensionCastCatalogEntry):
        return (
            entry.source_type,
            entry.target_type,
            entry.identity,
            entry.context,
            entry.method,
            *common,
        )
    raise TypeError("catalog entry requires one exact entry family")


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "big") + payload


def _encode_catalog_value(value: object) -> bytes:
    if value is None:
        return b"n"
    if type(value) is bool:
        return b"b1" if value else b"b0"
    if type(value) is int:
        return b"i" + _frame(str(value).encode("ascii"))
    if isinstance(value, StrEnum):
        return (
            b"e"
            + _frame(type(value).__qualname__.encode("utf-8"))
            + _frame(value.value.encode("utf-8"))
        )
    if type(value) is str:
        return b"s" + _frame(value.encode("utf-8"))
    if type(value) is tuple:
        return (
            b"t"
            + len(value).to_bytes(8, "big")
            + b"".join(_frame(_encode_catalog_value(item)) for item in value)
        )
    if is_dataclass(value) and not isinstance(value, type):
        data_fields = fields(value)
        return (
            b"d"
            + _frame(type(value).__qualname__.encode("utf-8"))
            + len(data_fields).to_bytes(8, "big")
            + b"".join(
                _frame(item.name.encode("utf-8"))
                + _frame(_encode_catalog_value(getattr(value, item.name)))
                for item in data_fields
            )
        )
    raise TypeError("catalog canonical encoding received an unsupported value")


def _entry_sort_key(entry: _ExtensionCatalogEntry) -> bytes:
    return _encode_catalog_value((_entry_family(entry), entry))


def _freeze_construction_collection(
    values: Iterable[object],
) -> tuple[object, ...] | None:
    if isinstance(values, (str, bytes, Mapping, Set)):
        return None
    try:
        return tuple(values)
    except TypeError:
        return None


def _construction_result(
    catalog: ConstructedExtensionCatalog | None,
    failures: tuple[ExtensionCatalogStructuralFailure, ...],
) -> ExtensionCatalogConstructionResult:
    result = object.__new__(ExtensionCatalogConstructionResult)
    object.__setattr__(result, "catalog", catalog)
    object.__setattr__(result, "failures", failures)
    return result


def _new_exact_entry_group(
    scope: ExtensionCatalogLookupScope,
    entries: tuple[_ExtensionCatalogEntry, ...],
) -> ExtensionCatalogExactEntryGroup:
    payloads = tuple(_entry_semantic_payload(entry) for entry in entries)
    if len(entries) == 1:
        state = ExtensionCatalogExactEntryGroupState.UNIQUE
    elif all(payload == payloads[0] for payload in payloads[1:]):
        state = ExtensionCatalogExactEntryGroupState.CONSISTENT_DUPLICATE
    else:
        state = ExtensionCatalogExactEntryGroupState.EVIDENCE_CONFLICT
    group = object.__new__(ExtensionCatalogExactEntryGroup)
    object.__setattr__(group, "scope", scope)
    object.__setattr__(group, "state", state)
    object.__setattr__(group, "entries", entries)
    return group


def _new_completeness_group(
    scope: ExtensionCatalogLookupScope,
    claims: tuple[ExtensionCatalogCompletenessClaim, ...],
) -> ExtensionCatalogCompletenessGroup:
    kinds = {claim.kind for claim in claims}
    if kinds == {ExtensionCatalogCompletenessClaimKind.COMPLETE}:
        state = ExtensionCatalogCompletenessState.COMPLETE
    elif kinds == {ExtensionCatalogCompletenessClaimKind.INCOMPLETE}:
        state = ExtensionCatalogCompletenessState.INCOMPLETE
    else:
        state = ExtensionCatalogCompletenessState.CONFLICT
    group = object.__new__(ExtensionCatalogCompletenessGroup)
    object.__setattr__(group, "scope", scope)
    object.__setattr__(group, "state", state)
    object.__setattr__(group, "claims", claims)
    return group


def _construct_extension_catalog(
    metadata: ExtensionCatalogMetadata,
    entries: Iterable[_ExtensionCatalogEntry],
    completeness_claims: Iterable[ExtensionCatalogCompletenessClaim],
) -> ExtensionCatalogConstructionResult:
    failures: list[ExtensionCatalogStructuralFailure] = []

    if type(metadata) is not ExtensionCatalogMetadata:
        return _construction_result(
            None,
            (
                ExtensionCatalogStructuralFailure(
                    ExtensionCatalogStructuralFailureKind.INVALID_METADATA
                ),
            ),
        )
    if (
        type(metadata.schema_version) is not ExtensionCatalogSchemaVersion
        or type(metadata.catalog) is not ExtensionCatalogReference
        or type(metadata.target) is not ExtensionCatalogTarget
        or type(metadata.source_occurrences) is not tuple
    ):
        failures.append(
            ExtensionCatalogStructuralFailure(
                ExtensionCatalogStructuralFailureKind.INVALID_METADATA
            )
        )
    else:
        for position, occurrence in enumerate(metadata.source_occurrences):
            if type(occurrence) is not ExtensionCatalogSourceOccurrence:
                failures.append(
                    ExtensionCatalogStructuralFailure(
                        ExtensionCatalogStructuralFailureKind.INVALID_METADATA,
                        item_position=position,
                    )
                )
                continue
            if occurrence.position != position:
                failures.append(
                    ExtensionCatalogStructuralFailure(
                        ExtensionCatalogStructuralFailureKind.SOURCE_POSITION_SEQUENCE_MISMATCH,
                        item_position=position,
                        source_position=occurrence.position,
                    )
                )
            if occurrence.owner != metadata.catalog:
                failures.append(
                    ExtensionCatalogStructuralFailure(
                        ExtensionCatalogStructuralFailureKind.SOURCE_OWNER_MISMATCH,
                        item_position=position,
                    )
                )

    frozen_entries = _freeze_construction_collection(entries)
    if frozen_entries is None:
        failures.append(
            ExtensionCatalogStructuralFailure(
                ExtensionCatalogStructuralFailureKind.INVALID_ENTRY_COLLECTION
            )
        )
    frozen_claims = _freeze_construction_collection(completeness_claims)
    if frozen_claims is None:
        failures.append(
            ExtensionCatalogStructuralFailure(
                ExtensionCatalogStructuralFailureKind.INVALID_COMPLETENESS_COLLECTION
            )
        )
    if frozen_entries is None or frozen_claims is None:
        return _construction_result(None, tuple(failures))

    valid_entries: list[_ExtensionCatalogEntry] = []
    for item_position, entry in enumerate(frozen_entries):
        if type(entry) not in {
            ExtensionNativeTypeCatalogEntry,
            ExtensionScalarFunctionCatalogEntry,
            ExtensionAggregateCatalogEntry,
            ExtensionOperatorCatalogEntry,
            ExtensionCastCatalogEntry,
        }:
            failures.append(
                ExtensionCatalogStructuralFailure(
                    ExtensionCatalogStructuralFailureKind.INVALID_ENTRY,
                    item_position=item_position,
                )
            )
            continue
        try:
            assert isinstance(
                entry,
                (
                    ExtensionNativeTypeCatalogEntry,
                    ExtensionScalarFunctionCatalogEntry,
                    ExtensionAggregateCatalogEntry,
                    ExtensionOperatorCatalogEntry,
                    ExtensionCastCatalogEntry,
                ),
            )
            replace(entry)
            replace(entry.evidence)
        except (TypeError, ValueError):
            failures.append(
                ExtensionCatalogStructuralFailure(
                    ExtensionCatalogStructuralFailureKind.INVALID_ENTRY,
                    item_position=item_position,
                )
            )
            continue
        valid_entries.append(entry)
        for source_position in entry.evidence.source_positions:
            if source_position >= len(metadata.source_occurrences):
                failures.append(
                    ExtensionCatalogStructuralFailure(
                        ExtensionCatalogStructuralFailureKind.ENTRY_SOURCE_POSITION_OUT_OF_RANGE,
                        item_position=item_position,
                        source_position=source_position,
                    )
                )

    valid_claims: list[ExtensionCatalogCompletenessClaim] = []
    for item_position, claim in enumerate(frozen_claims):
        if type(claim) is not ExtensionCatalogCompletenessClaim:
            failures.append(
                ExtensionCatalogStructuralFailure(
                    ExtensionCatalogStructuralFailureKind.INVALID_COMPLETENESS_DECLARATION,
                    item_position=item_position,
                )
            )
            continue
        try:
            replace(claim)
            replace(claim.scope)
        except (TypeError, ValueError):
            failures.append(
                ExtensionCatalogStructuralFailure(
                    ExtensionCatalogStructuralFailureKind.INVALID_COMPLETENESS_DECLARATION,
                    item_position=item_position,
                )
            )
            continue
        valid_claims.append(claim)
        for source_position in claim.source_positions:
            if source_position >= len(metadata.source_occurrences):
                failures.append(
                    ExtensionCatalogStructuralFailure(
                        ExtensionCatalogStructuralFailureKind.COMPLETENESS_SOURCE_POSITION_OUT_OF_RANGE,
                        item_position=item_position,
                        source_position=source_position,
                    )
                )

    if failures:
        return _construction_result(None, tuple(failures))

    canonical_entries = tuple(sorted(valid_entries, key=_entry_sort_key))
    entries_by_scope: dict[
        ExtensionCatalogLookupScope, list[_ExtensionCatalogEntry]
    ] = {}
    for entry in canonical_entries:
        scope = _entry_scope(entry)
        if scope is not None:
            entries_by_scope.setdefault(scope, []).append(entry)
    exact_entry_groups = tuple(
        _new_exact_entry_group(
            scope,
            tuple(sorted(entries_by_scope[scope], key=_entry_sort_key)),
        )
        for scope in sorted(entries_by_scope, key=_encode_catalog_value)
    )

    canonical_claims = tuple(sorted(valid_claims, key=_encode_catalog_value))
    claims_by_scope: dict[
        ExtensionCatalogLookupScope, list[ExtensionCatalogCompletenessClaim]
    ] = {}
    for claim in canonical_claims:
        claims_by_scope.setdefault(claim.scope, []).append(claim)
    completeness_groups = tuple(
        _new_completeness_group(
            scope,
            tuple(sorted(claims_by_scope[scope], key=_encode_catalog_value)),
        )
        for scope in sorted(claims_by_scope, key=_encode_catalog_value)
    )

    canonical_bytes = _encode_catalog_value(
        (
            "extension_catalog",
            metadata,
            canonical_entries,
            exact_entry_groups,
            canonical_claims,
            completeness_groups,
        )
    )
    catalog = object.__new__(ConstructedExtensionCatalog)
    object.__setattr__(catalog, "metadata", metadata)
    object.__setattr__(catalog, "entries", canonical_entries)
    object.__setattr__(catalog, "exact_entry_groups", exact_entry_groups)
    object.__setattr__(catalog, "completeness_claims", canonical_claims)
    object.__setattr__(catalog, "completeness_groups", completeness_groups)
    object.__setattr__(catalog, "canonical_bytes", canonical_bytes)
    object.__setattr__(
        catalog, "content_sha256", hashlib.sha256(canonical_bytes).hexdigest()
    )
    return _construction_result(catalog, ())
