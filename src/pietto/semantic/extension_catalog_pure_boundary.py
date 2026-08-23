"""Private total pure boundary for extension-catalog canonical values."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

__all__: tuple[str, ...] = ()

EXTENSION_CATALOG_PURE_FORMAT_MARKER = "pietto.extension-catalog.v1"
EXTENSION_CATALOG_PURE_MAX_INTEGER = 2**63 - 1


class ExtensionCatalogPureTag(StrEnum):
    ABSENT = "n"
    BOOLEAN = "b"
    INTEGER = "i"
    TEXT = "s"
    ENUMERATION = "e"
    TUPLE = "t"
    RECORD = "d"
    UNKNOWN = "?"


class ExtensionCatalogPureStatus(StrEnum):
    OK = "ok"
    MISSING_ROOT = "missing_root"
    UNKNOWN_FORMAT_MARKER = "unknown_format_marker"
    UNKNOWN_VALUE_TAG = "unknown_value_tag"
    VALUE_SHAPE_MISMATCH = "value_shape_mismatch"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    RECORD_SCHEMA_MISMATCH = "record_schema_mismatch"
    MISSING_REQUIRED_SECTION = "missing_required_section"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    ORDINAL_SEQUENCE_VIOLATION = "ordinal_sequence_violation"
    CHILD_COUNT_MISMATCH = "child_count_mismatch"
    INCONSISTENT_FAMILY_IDENTITY = "inconsistent_family_identity"
    INCONSISTENT_ENTRY_GROUP = "inconsistent_entry_group"
    INCONSISTENT_COMPLETENESS_LINK = "inconsistent_completeness_link"
    TRAILING_ITEM = "trailing_item"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogPureField:
    key: str
    value: ExtensionCatalogPureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str:
            raise TypeError("Catalog portable field keys must be exact text")
        if type(self.value) is not ExtensionCatalogPureValue:
            raise TypeError("Catalog portable fields require exact values")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogPureValue:
    tag: ExtensionCatalogPureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None
    enum_type: str | None = None
    enum_value: str | None = None
    items: tuple[ExtensionCatalogPureValue, ...] = ()
    record_kind: str | None = None
    fields: tuple[ExtensionCatalogPureField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.tag) is not ExtensionCatalogPureTag:
            raise TypeError("Catalog portable values require an exact tag")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Catalog portable text must be exact text")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Catalog portable integers must be exact integers")
        if self.boolean is not None and type(self.boolean) is not bool:
            raise TypeError("Catalog portable booleans must be exact booleans")
        for value in (self.enum_type, self.enum_value, self.record_kind):
            if value is not None and type(value) is not str:
                raise TypeError("Catalog portable labels must be exact text")
        if type(self.items) is not tuple or any(
            type(item) is not ExtensionCatalogPureValue for item in self.items
        ):
            raise TypeError("Catalog portable items require an exact tuple")
        if type(self.fields) is not tuple or any(
            type(item) is not ExtensionCatalogPureField for item in self.fields
        ):
            raise TypeError("Catalog portable fields require an exact tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogPureDocument:
    root: ExtensionCatalogPureValue | None

    def __post_init__(self) -> None:
        if self.root is not None and type(self.root) is not ExtensionCatalogPureValue:
            raise TypeError("Catalog portable documents require an exact root")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogPureOutcome:
    status: ExtensionCatalogPureStatus
    canonical_bytes: bytes | None = None
    item_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not ExtensionCatalogPureStatus:
            raise TypeError("Catalog portable outcomes require an exact status")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Catalog portable payloads must be exact bytes")
        for coordinate in (self.item_position, self.field_position):
            if coordinate is not None and type(coordinate) is not int:
                raise TypeError("Catalog portable coordinates must be exact integers")
        if self.status is ExtensionCatalogPureStatus.OK:
            if self.canonical_bytes is None:
                raise ValueError("Accepted catalog outcomes require canonical bytes")
            if self.item_position is not None or self.field_position is not None:
                raise ValueError("Accepted catalog outcomes carry no coordinates")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected catalog outcomes carry no canonical bytes")
        elif self.field_position is not None and self.item_position is None:
            raise ValueError("Catalog field coordinates require an item coordinate")


EXTENSION_CATALOG_PURE_ABSENT = ExtensionCatalogPureValue(
    tag=ExtensionCatalogPureTag.ABSENT
)


def extension_catalog_pure_boolean(value: bool) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(tag=ExtensionCatalogPureTag.BOOLEAN, boolean=value)


def extension_catalog_pure_integer(value: int) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(tag=ExtensionCatalogPureTag.INTEGER, integer=value)


def extension_catalog_pure_text(value: str) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(tag=ExtensionCatalogPureTag.TEXT, text=value)


def extension_catalog_pure_enumeration(
    enum_type: str,
    enum_value: str,
) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(
        tag=ExtensionCatalogPureTag.ENUMERATION,
        enum_type=enum_type,
        enum_value=enum_value,
    )


def extension_catalog_pure_tuple(
    *items: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(tag=ExtensionCatalogPureTag.TUPLE, items=items)


def extension_catalog_pure_record(
    record_kind: str,
    *fields: tuple[str, ExtensionCatalogPureValue],
) -> ExtensionCatalogPureValue:
    return ExtensionCatalogPureValue(
        tag=ExtensionCatalogPureTag.RECORD,
        record_kind=record_kind,
        fields=tuple(
            ExtensionCatalogPureField(key=key, value=value) for key, value in fields
        ),
    )


_RECORD_FIELDS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "ExtensionCatalogIdentity": ("namespace", "name"),
        "ExtensionCatalogReference": ("identity", "release"),
        "ExtensionCatalogTarget": (
            "database_family",
            "database_release",
            "extension_identity",
            "extension_release",
        ),
        "ExtensionCatalogSourceProvenance": (
            "source_authority",
            "source_revision",
            "source_locator",
            "curation",
        ),
        "ExtensionCatalogSourceOccurrence": ("owner", "position", "provenance"),
        "ExtensionCatalogMetadata": (
            "schema_version",
            "catalog",
            "target",
            "source_occurrences",
        ),
        "LogicalTypeIdentity": ("name", "kind"),
        "ExtensionCatalogTypeReference": (
            "kind",
            "logical_type",
            "physical_name",
            "extension_identity",
        ),
        "PostgreSQLCallableIdentity": ("sql_name", "input_types"),
        "PostgreSQLOperatorIdentity": (
            "operator_name",
            "arity",
            "operand_types",
        ),
        "PostgreSQLCastIdentity": ("source_type", "target_type"),
        "ExtensionCatalogDeclarationTypeUse": (
            "kind",
            "exact_type",
            "source_spelling",
            "unmodeled_reasons",
        ),
        "ExtensionCatalogEntryEvidence": (
            "matchability",
            "exposure",
            "unmodeled_reasons",
            "source_positions",
        ),
        "PostgreSQLCallableDeclaration": ("sql_name", "input_types", "identity"),
        "ExtensionNativeTypeCatalogEntry": (
            "type_identity",
            "logical_mapping",
            "evidence",
        ),
        "ExtensionScalarFunctionCatalogEntry": (
            "declaration",
            "result_type",
            "null_call_behavior",
            "volatility",
            "parallel_safety",
            "has_default_arguments",
            "is_variadic",
            "returns_set",
            "has_polymorphic_or_pseudo_types",
            "evidence",
        ),
        "ExtensionAggregateCatalogEntry": (
            "kind",
            "declaration",
            "result_type",
            "parallel_safety",
            "has_direct_arguments",
            "is_variadic",
            "evidence",
        ),
        "ExtensionOperatorCatalogEntry": (
            "operator_name",
            "arity",
            "operand_types",
            "identity",
            "result_type",
            "evidence",
        ),
        "ExtensionCastCatalogEntry": (
            "source_type",
            "target_type",
            "identity",
            "context",
            "method",
            "evidence",
        ),
        "ExtensionCatalogLookupScope": ("family", "identity"),
        "ExtensionCatalogCompletenessClaim": ("scope", "kind", "source_positions"),
        "ExtensionCatalogExactEntryGroup": ("scope", "state", "entries"),
        "ExtensionCatalogCompletenessGroup": ("scope", "state", "claims"),
    }
)

EXTENSION_CATALOG_PURE_RECORD_KINDS: tuple[str, ...] = tuple(_RECORD_FIELDS)

_ENUMERATIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "ExtensionCatalogSchemaVersion": (
            "pietto.extension-catalog.v1",
            "pietto.extension-catalog.invalid",
        ),
        "TypeKind": ("builtin", "enum", "shape"),
        "ExtensionCatalogTypeReferenceKind": (
            "pietto_logical",
            "postgres_builtin",
            "extension_native",
        ),
        "PostgreSQLOperatorArity": ("unary", "binary"),
        "ExtensionCatalogDeclarationTypeUseKind": ("exact", "unmodeled"),
        "ExtensionCatalogUnmodeledReason": (
            "unsupported_type_form",
            "default_arguments",
            "variadic_arguments",
            "polymorphic_or_pseudo_type",
            "set_returning",
            "table_or_composite_return",
            "ordered_set_or_hypothetical_set_aggregate",
            "direct_arguments",
        ),
        "ExtensionCatalogMatchability": ("exact_matchable", "cataloged_unmodeled"),
        "ExtensionCatalogExposure": (
            "direct_sql_surface",
            "implementation_support",
            "unclassified",
        ),
        "PostgreSQLNullCallBehavior": (
            "unknown",
            "called_on_null_input",
            "strict",
        ),
        "PostgreSQLVolatility": ("unknown", "immutable", "stable", "volatile"),
        "PostgreSQLParallelSafety": (
            "unknown",
            "unsafe",
            "restricted",
            "safe",
        ),
        "PostgreSQLAggregateKind": ("ordinary", "ordered_set", "hypothetical_set"),
        "PostgreSQLCastContext": (
            "unknown",
            "explicit_only",
            "assignment",
            "implicit",
        ),
        "PostgreSQLCastMethod": ("unknown", "function", "binary", "inout"),
        "ExtensionCatalogEntryFamily": (
            "native_type",
            "scalar_function",
            "aggregate",
            "operator",
            "cast",
        ),
        "ExtensionCatalogCompletenessClaimKind": ("complete", "incomplete"),
        "ExtensionCatalogExactEntryGroupState": (
            "unique",
            "consistent_duplicate",
            "evidence_conflict",
        ),
        "ExtensionCatalogCompletenessState": (
            "complete",
            "incomplete",
            "conflict",
        ),
    }
)

_ENTRY_KINDS = (
    "ExtensionNativeTypeCatalogEntry",
    "ExtensionScalarFunctionCatalogEntry",
    "ExtensionAggregateCatalogEntry",
    "ExtensionOperatorCatalogEntry",
    "ExtensionCastCatalogEntry",
)
_FAMILY_IDENTITY_KIND = MappingProxyType(
    {
        "native_type": "ExtensionCatalogTypeReference",
        "scalar_function": "PostgreSQLCallableIdentity",
        "aggregate": "PostgreSQLCallableIdentity",
        "operator": "PostgreSQLOperatorIdentity",
        "cast": "PostgreSQLCastIdentity",
    }
)
_ENTRY_FAMILY = MappingProxyType(
    {
        "ExtensionNativeTypeCatalogEntry": "native_type",
        "ExtensionScalarFunctionCatalogEntry": "scalar_function",
        "ExtensionAggregateCatalogEntry": "aggregate",
        "ExtensionOperatorCatalogEntry": "operator",
        "ExtensionCastCatalogEntry": "cast",
    }
)


def _reject(
    status: ExtensionCatalogPureStatus,
    item_position: int | None = None,
    field_position: int | None = None,
) -> ExtensionCatalogPureOutcome:
    return ExtensionCatalogPureOutcome(
        status=status,
        item_position=item_position,
        field_position=field_position,
    )


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "big") + payload


def encode_extension_catalog_pure_value(value: ExtensionCatalogPureValue) -> bytes:
    if type(value) is not ExtensionCatalogPureValue:
        raise TypeError("Catalog pure encoding requires an exact value")
    if value.tag is ExtensionCatalogPureTag.ABSENT:
        return b"n"
    if value.tag is ExtensionCatalogPureTag.BOOLEAN:
        assert value.boolean is not None
        return b"b1" if value.boolean else b"b0"
    if value.tag is ExtensionCatalogPureTag.INTEGER:
        assert value.integer is not None
        return b"i" + _frame(str(value.integer).encode("ascii"))
    if value.tag is ExtensionCatalogPureTag.TEXT:
        assert value.text is not None
        return b"s" + _frame(value.text.encode("utf-8"))
    if value.tag is ExtensionCatalogPureTag.ENUMERATION:
        assert value.enum_type is not None and value.enum_value is not None
        return (
            b"e"
            + _frame(value.enum_type.encode("utf-8"))
            + _frame(value.enum_value.encode("utf-8"))
        )
    if value.tag is ExtensionCatalogPureTag.TUPLE:
        return (
            b"t"
            + len(value.items).to_bytes(8, "big")
            + b"".join(
                _frame(encode_extension_catalog_pure_value(item))
                for item in value.items
            )
        )
    if value.tag is ExtensionCatalogPureTag.RECORD:
        assert value.record_kind is not None
        return (
            b"d"
            + _frame(value.record_kind.encode("utf-8"))
            + len(value.fields).to_bytes(8, "big")
            + b"".join(
                _frame(item.key.encode("utf-8"))
                + _frame(encode_extension_catalog_pure_value(item.value))
                for item in value.fields
            )
        )
    raise ValueError("Unknown catalog pure tag cannot be encoded")


def _shape_status(
    value: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureStatus | None:
    empty_scalars = (
        value.text is None
        and value.integer is None
        and value.boolean is None
        and value.enum_type is None
        and value.enum_value is None
        and value.record_kind is None
        and not value.items
        and not value.fields
    )
    if value.tag is ExtensionCatalogPureTag.UNKNOWN:
        return ExtensionCatalogPureStatus.UNKNOWN_VALUE_TAG
    if value.tag is ExtensionCatalogPureTag.ABSENT:
        return (
            None if empty_scalars else ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
        )
    if value.tag is ExtensionCatalogPureTag.BOOLEAN:
        valid = (
            value.boolean is not None
            and value.text is None
            and value.integer is None
            and value.enum_type is None
            and value.enum_value is None
            and value.record_kind is None
            and not value.items
            and not value.fields
        )
        return None if valid else ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
    if value.tag is ExtensionCatalogPureTag.INTEGER:
        integer = value.integer
        valid = (
            integer is not None
            and value.text is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and value.record_kind is None
            and not value.items
            and not value.fields
        )
        if not valid:
            return ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
        assert integer is not None
        if not 0 <= integer <= EXTENSION_CATALOG_PURE_MAX_INTEGER:
            return ExtensionCatalogPureStatus.INTEGER_OUT_OF_RANGE
        return None
    if value.tag is ExtensionCatalogPureTag.TEXT:
        valid = (
            value.text is not None
            and value.integer is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and value.record_kind is None
            and not value.items
            and not value.fields
        )
        return None if valid else ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
    if value.tag is ExtensionCatalogPureTag.ENUMERATION:
        enum_type = value.enum_type
        enum_value = value.enum_value
        valid = (
            enum_type is not None
            and enum_value is not None
            and value.text is None
            and value.integer is None
            and value.boolean is None
            and value.record_kind is None
            and not value.items
            and not value.fields
        )
        if not valid:
            return ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
        assert enum_type is not None and enum_value is not None
        vocabulary = _ENUMERATIONS.get(enum_type)
        if vocabulary is None or enum_value not in vocabulary:
            return ExtensionCatalogPureStatus.UNKNOWN_ENUMERATION
        return None
    if value.tag is ExtensionCatalogPureTag.TUPLE:
        valid = (
            value.text is None
            and value.integer is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and value.record_kind is None
            and not value.fields
        )
        return None if valid else ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH
    valid = (
        value.record_kind is not None
        and value.text is None
        and value.integer is None
        and value.boolean is None
        and value.enum_type is None
        and value.enum_value is None
        and not value.items
    )
    return None if valid else ExtensionCatalogPureStatus.VALUE_SHAPE_MISMATCH


def _validate_tree(
    value: ExtensionCatalogPureValue,
    position: list[int],
) -> ExtensionCatalogPureOutcome | None:
    item_position = position[0]
    position[0] += 1
    status = _shape_status(value)
    if status is not None:
        return _reject(status, item_position)
    if value.tag is ExtensionCatalogPureTag.RECORD:
        expected = _RECORD_FIELDS.get(value.record_kind or "")
        if expected is None or tuple(field.key for field in value.fields) != expected:
            return _reject(
                ExtensionCatalogPureStatus.RECORD_SCHEMA_MISMATCH, item_position
            )
        children = tuple(field.value for field in value.fields)
    elif value.tag is ExtensionCatalogPureTag.TUPLE:
        children = value.items
    else:
        children = ()
    for field_position, child in enumerate(children):
        outcome = _validate_tree(child, position)
        if outcome is not None:
            if outcome.field_position is None:
                return _reject(
                    outcome.status,
                    outcome.item_position,
                    field_position
                    if value.tag is ExtensionCatalogPureTag.RECORD
                    else None,
                )
            return outcome
    return None


def _field(record: ExtensionCatalogPureValue, key: str) -> ExtensionCatalogPureValue:
    return next(field.value for field in record.fields if field.key == key)


def _text(value: ExtensionCatalogPureValue) -> str | None:
    return value.text if value.tag is ExtensionCatalogPureTag.TEXT else None


def _integer(value: ExtensionCatalogPureValue) -> int | None:
    return value.integer if value.tag is ExtensionCatalogPureTag.INTEGER else None


def _enum(value: ExtensionCatalogPureValue) -> str | None:
    return (
        value.enum_value if value.tag is ExtensionCatalogPureTag.ENUMERATION else None
    )


def _record_kind(value: ExtensionCatalogPureValue) -> str | None:
    return value.record_kind if value.tag is ExtensionCatalogPureTag.RECORD else None


def _positions_in_range(
    values: ExtensionCatalogPureValue,
    upper_bound: int,
) -> bool:
    if values.tag is not ExtensionCatalogPureTag.TUPLE:
        return False
    for item in values.items:
        position = _integer(item)
        if position is None or position >= upper_bound:
            return False
    return True


def _scope_parts(scope: ExtensionCatalogPureValue) -> tuple[str, str] | None:
    if _record_kind(scope) != "ExtensionCatalogLookupScope":
        return None
    family = _enum(_field(scope, "family"))
    identity_kind = _record_kind(_field(scope, "identity"))
    if family is None or identity_kind is None:
        return None
    return family, identity_kind


def _entry_identity(
    entry: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureValue | None:
    kind = _record_kind(entry)
    if kind == "ExtensionNativeTypeCatalogEntry":
        return _field(entry, "type_identity")
    if kind in {
        "ExtensionScalarFunctionCatalogEntry",
        "ExtensionAggregateCatalogEntry",
    }:
        declaration = _field(entry, "declaration")
        return _field(declaration, "identity")
    if kind in {"ExtensionOperatorCatalogEntry", "ExtensionCastCatalogEntry"}:
        return _field(entry, "identity")
    return None


def _entry_semantic_bytes(entry: ExtensionCatalogPureValue) -> bytes:
    evidence = _field(entry, "evidence")
    replacement = extension_catalog_pure_record(
        "ExtensionCatalogEntryEvidence",
        ("matchability", _field(evidence, "matchability")),
        ("exposure", _field(evidence, "exposure")),
        ("unmodeled_reasons", _field(evidence, "unmodeled_reasons")),
        ("source_positions", extension_catalog_pure_tuple()),
    )
    fields = tuple(
        (field.key, replacement if field.key == "evidence" else field.value)
        for field in entry.fields
    )
    return encode_extension_catalog_pure_value(
        extension_catalog_pure_record(entry.record_kind or "", *fields)
    )


def _record_child(
    record: ExtensionCatalogPureValue,
    key: str,
    kinds: tuple[str, ...],
    *,
    optional: bool = False,
) -> bool:
    value = _field(record, key)
    return (
        optional
        and value.tag is ExtensionCatalogPureTag.ABSENT
        or (_record_kind(value) in kinds and _validate_record_relations(value))
    )


def _record_children(
    record: ExtensionCatalogPureValue,
    key: str,
    kinds: tuple[str, ...],
) -> bool:
    value = _field(record, key)
    return value.tag is ExtensionCatalogPureTag.TUPLE and all(
        _record_kind(item) in kinds and _validate_record_relations(item)
        for item in value.items
    )


def _validate_record_relations(value: ExtensionCatalogPureValue) -> bool:
    kind = _record_kind(value)
    if kind in {
        "ExtensionCatalogIdentity",
        "ExtensionCatalogTarget",
        "ExtensionCatalogSourceProvenance",
        "LogicalTypeIdentity",
        "ExtensionCatalogEntryEvidence",
    }:
        return True
    if kind == "ExtensionCatalogReference":
        return _record_child(value, "identity", ("ExtensionCatalogIdentity",))
    if kind == "ExtensionCatalogSourceOccurrence":
        return _record_child(
            value,
            "owner",
            ("ExtensionCatalogReference",),
        ) and _record_child(
            value,
            "provenance",
            ("ExtensionCatalogSourceProvenance",),
        )
    if kind == "ExtensionCatalogMetadata":
        return (
            _record_child(value, "catalog", ("ExtensionCatalogReference",))
            and _record_child(value, "target", ("ExtensionCatalogTarget",))
            and _record_children(
                value,
                "source_occurrences",
                ("ExtensionCatalogSourceOccurrence",),
            )
        )
    if kind == "ExtensionCatalogTypeReference":
        return _record_child(
            value,
            "logical_type",
            ("LogicalTypeIdentity",),
            optional=True,
        )
    if kind == "PostgreSQLCallableIdentity":
        return _record_children(
            value,
            "input_types",
            ("ExtensionCatalogTypeReference",),
        )
    if kind == "PostgreSQLOperatorIdentity":
        return _record_children(
            value,
            "operand_types",
            ("ExtensionCatalogTypeReference",),
        )
    if kind == "PostgreSQLCastIdentity":
        return _record_child(
            value,
            "source_type",
            ("ExtensionCatalogTypeReference",),
        ) and _record_child(
            value,
            "target_type",
            ("ExtensionCatalogTypeReference",),
        )
    if kind == "ExtensionCatalogDeclarationTypeUse":
        return _record_child(
            value,
            "exact_type",
            ("ExtensionCatalogTypeReference",),
            optional=True,
        )
    if kind == "PostgreSQLCallableDeclaration":
        return _record_children(
            value,
            "input_types",
            ("ExtensionCatalogDeclarationTypeUse",),
        ) and _record_child(
            value,
            "identity",
            ("PostgreSQLCallableIdentity",),
            optional=True,
        )
    if kind == "ExtensionNativeTypeCatalogEntry":
        return (
            _record_child(value, "type_identity", ("ExtensionCatalogTypeReference",))
            and _record_child(
                value,
                "logical_mapping",
                ("ExtensionCatalogTypeReference",),
                optional=True,
            )
            and _record_child(value, "evidence", ("ExtensionCatalogEntryEvidence",))
        )
    if kind == "ExtensionScalarFunctionCatalogEntry":
        return (
            _record_child(value, "declaration", ("PostgreSQLCallableDeclaration",))
            and _record_child(
                value,
                "result_type",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(value, "evidence", ("ExtensionCatalogEntryEvidence",))
        )
    if kind == "ExtensionAggregateCatalogEntry":
        return (
            _record_child(value, "declaration", ("PostgreSQLCallableDeclaration",))
            and _record_child(
                value,
                "result_type",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(value, "evidence", ("ExtensionCatalogEntryEvidence",))
        )
    if kind == "ExtensionOperatorCatalogEntry":
        return (
            _record_children(
                value,
                "operand_types",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(
                value,
                "identity",
                ("PostgreSQLOperatorIdentity",),
                optional=True,
            )
            and _record_child(
                value,
                "result_type",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(value, "evidence", ("ExtensionCatalogEntryEvidence",))
        )
    if kind == "ExtensionCastCatalogEntry":
        return (
            _record_child(
                value,
                "source_type",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(
                value,
                "target_type",
                ("ExtensionCatalogDeclarationTypeUse",),
            )
            and _record_child(
                value,
                "identity",
                ("PostgreSQLCastIdentity",),
                optional=True,
            )
            and _record_child(value, "evidence", ("ExtensionCatalogEntryEvidence",))
        )
    if kind == "ExtensionCatalogLookupScope":
        return _record_child(
            value,
            "identity",
            (
                "ExtensionCatalogTypeReference",
                "PostgreSQLCallableIdentity",
                "PostgreSQLOperatorIdentity",
                "PostgreSQLCastIdentity",
            ),
        )
    if kind == "ExtensionCatalogCompletenessClaim":
        return _record_child(value, "scope", ("ExtensionCatalogLookupScope",))
    if kind == "ExtensionCatalogExactEntryGroup":
        return _record_child(
            value,
            "scope",
            ("ExtensionCatalogLookupScope",),
        ) and _record_children(value, "entries", _ENTRY_KINDS)
    if kind == "ExtensionCatalogCompletenessGroup":
        return _record_child(
            value,
            "scope",
            ("ExtensionCatalogLookupScope",),
        ) and _record_children(
            value,
            "claims",
            ("ExtensionCatalogCompletenessClaim",),
        )
    return False


def _validate_catalog_relations(
    root: ExtensionCatalogPureValue,
) -> ExtensionCatalogPureStatus | None:
    if root.tag is not ExtensionCatalogPureTag.TUPLE:
        return ExtensionCatalogPureStatus.MISSING_REQUIRED_SECTION
    if len(root.items) < 6:
        return ExtensionCatalogPureStatus.MISSING_REQUIRED_SECTION
    if len(root.items) > 6:
        return ExtensionCatalogPureStatus.TRAILING_ITEM
    role, metadata, entries, exact_groups, claims, completeness_groups = root.items
    if _text(role) != "extension_catalog":
        return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
    if _record_kind(metadata) != "ExtensionCatalogMetadata" or any(
        value.tag is not ExtensionCatalogPureTag.TUPLE
        for value in (entries, exact_groups, claims, completeness_groups)
    ):
        return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
    if not _validate_record_relations(metadata) or any(
        not _validate_record_relations(item)
        for collection in (entries, exact_groups, claims, completeness_groups)
        for item in collection.items
    ):
        return ExtensionCatalogPureStatus.RECORD_SCHEMA_MISMATCH
    schema = _field(metadata, "schema_version")
    if (
        schema.enum_type != "ExtensionCatalogSchemaVersion"
        or schema.enum_value != EXTENSION_CATALOG_PURE_FORMAT_MARKER
    ):
        return ExtensionCatalogPureStatus.UNKNOWN_FORMAT_MARKER
    sources = _field(metadata, "source_occurrences")
    if sources.tag is not ExtensionCatalogPureTag.TUPLE:
        return ExtensionCatalogPureStatus.CHILD_COUNT_MISMATCH
    for position, source in enumerate(sources.items):
        if (
            _record_kind(source) != "ExtensionCatalogSourceOccurrence"
            or _integer(_field(source, "position")) != position
        ):
            return ExtensionCatalogPureStatus.ORDINAL_SEQUENCE_VIOLATION
    source_count = len(sources.items)
    if any(_record_kind(entry) not in _ENTRY_KINDS for entry in entries.items):
        return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
    entry_bytes = tuple(
        encode_extension_catalog_pure_value(item) for item in entries.items
    )
    entry_sort_bytes = tuple(
        encode_extension_catalog_pure_value(
            extension_catalog_pure_tuple(
                extension_catalog_pure_enumeration(
                    "ExtensionCatalogEntryFamily",
                    _ENTRY_FAMILY[record_kind],
                ),
                item,
            )
        )
        for item in entries.items
        for record_kind in (_record_kind(item),)
        if record_kind is not None
    )
    if entry_sort_bytes != tuple(sorted(entry_sort_bytes)):
        return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
    for entry in entries.items:
        evidence = _field(entry, "evidence")
        positions = _field(evidence, "source_positions")
        if not _positions_in_range(positions, source_count):
            return ExtensionCatalogPureStatus.CHILD_COUNT_MISMATCH
        if _record_kind(entry) == "ExtensionOperatorCatalogEntry":
            arity = _enum(_field(entry, "arity"))
            operands = _field(entry, "operand_types")
            expected = 1 if arity == "unary" else 2 if arity == "binary" else -1
            if (
                operands.tag is not ExtensionCatalogPureTag.TUPLE
                or len(operands.items) != expected
            ):
                return ExtensionCatalogPureStatus.CHILD_COUNT_MISMATCH
    entry_counter = Counter(entry_bytes)
    for group in exact_groups.items:
        if _record_kind(group) != "ExtensionCatalogExactEntryGroup":
            return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
        scope = _field(group, "scope")
        parts = _scope_parts(scope)
        if parts is None or _FAMILY_IDENTITY_KIND.get(parts[0]) != parts[1]:
            return ExtensionCatalogPureStatus.INCONSISTENT_FAMILY_IDENTITY
        members = _field(group, "entries")
        if members.tag is not ExtensionCatalogPureTag.TUPLE or not members.items:
            return ExtensionCatalogPureStatus.INCONSISTENT_ENTRY_GROUP
        member_counter = Counter(
            encode_extension_catalog_pure_value(item) for item in members.items
        )
        if any(member_counter[item] > entry_counter[item] for item in member_counter):
            return ExtensionCatalogPureStatus.INCONSISTENT_ENTRY_GROUP
        for member in members.items:
            kind = _record_kind(member)
            if _ENTRY_FAMILY.get(kind or "") != parts[0]:
                return ExtensionCatalogPureStatus.INCONSISTENT_FAMILY_IDENTITY
            identity = _entry_identity(member)
            if identity is None or identity.tag is ExtensionCatalogPureTag.ABSENT:
                return ExtensionCatalogPureStatus.INCONSISTENT_FAMILY_IDENTITY
            if encode_extension_catalog_pure_value(
                identity
            ) != encode_extension_catalog_pure_value(_field(scope, "identity")):
                return ExtensionCatalogPureStatus.INCONSISTENT_FAMILY_IDENTITY
        state = _enum(_field(group, "state"))
        semantic = tuple(_entry_semantic_bytes(item) for item in members.items)
        expected_state = (
            "unique"
            if len(members.items) == 1
            else "consistent_duplicate"
            if all(item == semantic[0] for item in semantic[1:])
            else "evidence_conflict"
        )
        if state != expected_state:
            return ExtensionCatalogPureStatus.INCONSISTENT_ENTRY_GROUP
    claim_bytes = tuple(
        encode_extension_catalog_pure_value(item) for item in claims.items
    )
    if claim_bytes != tuple(sorted(claim_bytes)):
        return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
    for claim in claims.items:
        if _record_kind(claim) != "ExtensionCatalogCompletenessClaim":
            return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
        positions = _field(claim, "source_positions")
        if not _positions_in_range(positions, source_count):
            return ExtensionCatalogPureStatus.CHILD_COUNT_MISMATCH
    claim_counter = Counter(claim_bytes)
    for group in completeness_groups.items:
        if _record_kind(group) != "ExtensionCatalogCompletenessGroup":
            return ExtensionCatalogPureStatus.SECTION_ORDER_VIOLATION
        members = _field(group, "claims")
        if members.tag is not ExtensionCatalogPureTag.TUPLE or not members.items:
            return ExtensionCatalogPureStatus.INCONSISTENT_COMPLETENESS_LINK
        member_counter = Counter(
            encode_extension_catalog_pure_value(item) for item in members.items
        )
        if any(member_counter[item] > claim_counter[item] for item in member_counter):
            return ExtensionCatalogPureStatus.INCONSISTENT_COMPLETENESS_LINK
        kinds = {_enum(_field(item, "kind")) for item in members.items}
        expected_state = (
            "complete"
            if kinds == {"complete"}
            else "incomplete"
            if kinds == {"incomplete"}
            else "conflict"
        )
        if _enum(_field(group, "state")) != expected_state:
            return ExtensionCatalogPureStatus.INCONSISTENT_COMPLETENESS_LINK
        scope_bytes = encode_extension_catalog_pure_value(_field(group, "scope"))
        if any(
            encode_extension_catalog_pure_value(_field(item, "scope")) != scope_bytes
            for item in members.items
        ):
            return ExtensionCatalogPureStatus.INCONSISTENT_COMPLETENESS_LINK
    return None


def evaluate_extension_catalog_document(
    document: ExtensionCatalogPureDocument,
) -> ExtensionCatalogPureOutcome:
    if type(document) is not ExtensionCatalogPureDocument:
        raise TypeError("Catalog pure evaluation requires an exact document")
    if document.root is None:
        return _reject(ExtensionCatalogPureStatus.MISSING_ROOT)
    structural = _validate_tree(document.root, [0])
    if structural is not None:
        return structural
    try:
        relation_status = _validate_catalog_relations(document.root)
    except (IndexError, KeyError, StopIteration):
        relation_status = ExtensionCatalogPureStatus.RECORD_SCHEMA_MISMATCH
    if relation_status is not None:
        return _reject(relation_status, 0)
    return ExtensionCatalogPureOutcome(
        status=ExtensionCatalogPureStatus.OK,
        canonical_bytes=encode_extension_catalog_pure_value(document.root),
    )
