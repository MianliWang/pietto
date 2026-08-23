"""Private total pure boundary for extension-catalog inspection values."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Mapping

__all__: tuple[str, ...] = ()

EXTENSION_CATALOG_INSPECTION_PURE_FORMAT_MARKER = (
    "pietto.extension-catalog-inspection.v1"
)
EXTENSION_CATALOG_INSPECTION_PURE_MAX_INTEGER = 2**63 - 1


class ExtensionCatalogInspectionPureTag(StrEnum):
    ABSENT = "n"
    BOOLEAN = "b"
    INTEGER = "i"
    TEXT = "s"
    ENUMERATION = "e"
    TUPLE = "t"
    UNKNOWN = "?"


class ExtensionCatalogInspectionPureStatus(StrEnum):
    OK = "ok"
    MISSING_ROOT = "missing_root"
    UNKNOWN_FORMAT_MARKER = "unknown_format_marker"
    UNKNOWN_VALUE_TAG = "unknown_value_tag"
    VALUE_SHAPE_MISMATCH = "value_shape_mismatch"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    TUPLE_SCHEMA_MISMATCH = "tuple_schema_mismatch"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    ORDINAL_SEQUENCE_VIOLATION = "ordinal_sequence_violation"
    CHILD_COUNT_MISMATCH = "child_count_mismatch"
    INVALID_SHA256 = "invalid_sha256"
    DANGLING_POSITIONAL_LINK = "dangling_positional_link"
    INCONSISTENT_FAMILY_IDENTITY = "inconsistent_family_identity"
    INCONSISTENT_ENTRY_GROUP = "inconsistent_entry_group"
    INCONSISTENT_COMPLETENESS_LINK = "inconsistent_completeness_link"
    INCONSISTENT_SELECTION_LINK = "inconsistent_selection_link"
    INCONSISTENT_PROVIDER_RESULT = "inconsistent_provider_result"
    TRAILING_ITEM = "trailing_item"


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogInspectionPureValue:
    tag: ExtensionCatalogInspectionPureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None
    enum_type: str | None = None
    enum_value: str | None = None
    items: tuple[ExtensionCatalogInspectionPureValue, ...] = ()

    def __post_init__(self) -> None:
        if type(self.tag) is not ExtensionCatalogInspectionPureTag:
            raise TypeError("Inspection portable values require an exact tag")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Inspection portable text must be exact text")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Inspection portable integers must be exact integers")
        if self.boolean is not None and type(self.boolean) is not bool:
            raise TypeError("Inspection portable booleans must be exact booleans")
        for value in (self.enum_type, self.enum_value):
            if value is not None and type(value) is not str:
                raise TypeError("Inspection portable enum labels must be exact text")
        if type(self.items) is not tuple or any(
            type(item) is not ExtensionCatalogInspectionPureValue for item in self.items
        ):
            raise TypeError("Inspection portable items require an exact tuple")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogInspectionPureDocument:
    root: ExtensionCatalogInspectionPureValue | None

    def __post_init__(self) -> None:
        if (
            self.root is not None
            and type(self.root) is not ExtensionCatalogInspectionPureValue
        ):
            raise TypeError("Inspection portable documents require an exact root")


@dataclass(frozen=True, slots=True, kw_only=True)
class ExtensionCatalogInspectionPureOutcome:
    status: ExtensionCatalogInspectionPureStatus
    canonical_bytes: bytes | None = None
    item_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not ExtensionCatalogInspectionPureStatus:
            raise TypeError("Inspection portable outcomes require an exact status")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Inspection portable payloads must be exact bytes")
        for coordinate in (self.item_position, self.field_position):
            if coordinate is not None and type(coordinate) is not int:
                raise TypeError(
                    "Inspection portable coordinates must be exact integers"
                )
        if self.status is ExtensionCatalogInspectionPureStatus.OK:
            if self.canonical_bytes is None:
                raise ValueError("Accepted inspection outcomes require canonical bytes")
            if self.item_position is not None or self.field_position is not None:
                raise ValueError("Accepted inspection outcomes carry no coordinates")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected inspection outcomes carry no canonical bytes")
        elif self.field_position is not None and self.item_position is None:
            raise ValueError("Inspection field coordinates require an item coordinate")


EXTENSION_CATALOG_INSPECTION_PURE_ABSENT = ExtensionCatalogInspectionPureValue(
    tag=ExtensionCatalogInspectionPureTag.ABSENT
)


def extension_catalog_inspection_pure_boolean(
    value: bool,
) -> ExtensionCatalogInspectionPureValue:
    return ExtensionCatalogInspectionPureValue(
        tag=ExtensionCatalogInspectionPureTag.BOOLEAN,
        boolean=value,
    )


def extension_catalog_inspection_pure_integer(
    value: int,
) -> ExtensionCatalogInspectionPureValue:
    return ExtensionCatalogInspectionPureValue(
        tag=ExtensionCatalogInspectionPureTag.INTEGER,
        integer=value,
    )


def extension_catalog_inspection_pure_text(
    value: str,
) -> ExtensionCatalogInspectionPureValue:
    return ExtensionCatalogInspectionPureValue(
        tag=ExtensionCatalogInspectionPureTag.TEXT,
        text=value,
    )


def extension_catalog_inspection_pure_enumeration(
    enum_type: str,
    enum_value: str,
) -> ExtensionCatalogInspectionPureValue:
    return ExtensionCatalogInspectionPureValue(
        tag=ExtensionCatalogInspectionPureTag.ENUMERATION,
        enum_type=enum_type,
        enum_value=enum_value,
    )


def extension_catalog_inspection_pure_tuple(
    *items: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureValue:
    return ExtensionCatalogInspectionPureValue(
        tag=ExtensionCatalogInspectionPureTag.TUPLE,
        items=items,
    )


_ENUMERATIONS: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "ExtensionCatalogInspectionFormat": (
            "pietto.extension-catalog-inspection.v1",
            "pietto.extension-catalog-inspection.invalid",
        ),
        "TypeKind": ("builtin", "enum", "shape"),
        "ExtensionCatalogTypeReferenceKind": (
            "pietto_logical",
            "postgres_builtin",
            "extension_native",
        ),
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
        "PostgreSQLOperatorArity": ("unary", "binary"),
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
        "ExtensionCatalogExactEntryGroupState": (
            "unique",
            "consistent_duplicate",
            "evidence_conflict",
        ),
        "ExtensionCatalogCompletenessClaimKind": ("complete", "incomplete"),
        "ExtensionCatalogCompletenessState": (
            "complete",
            "incomplete",
            "conflict",
        ),
        "CapabilityDomain": ("extension_signature",),
        "CapabilitySupport": ("supported", "explicitly_unsupported"),
        "CapabilityDispositionKind": ("none", "deferred", "out_of_scope"),
        "CapabilityEvidenceSource": (
            "grammar_ast",
            "semantic_catalog",
            "semantic_procedure",
            "semantic_model",
            "ir",
            "backend",
            "project",
            "public",
            "roadmap",
            "test",
            "spec",
        ),
        "CapabilityReasonCode": (
            "no_catalog_entry",
            "not_evidenced",
            "no_current_result_rule",
            "unresolved_expression",
            "null_literal_no_concrete_type",
            "unknown_nullability",
            "sql_three_valued_truth",
            "dialect_lowering_gap",
            "conflicting_evidence",
            "extension_catalog_undeclared",
            "extension_catalog_selection_ambiguous",
            "extension_catalog_selection_conflict",
            "extension_catalog_target_mismatch",
            "extension_catalog_not_provider_eligible",
            "extension_cataloged_unmodeled",
            "extension_catalog_completeness_incomplete",
            "extension_catalog_completeness_conflict",
            "extension_catalog_completeness_unavailable",
        ),
        "ExtensionCatalogAvailabilityOwner": ("compiler", "project"),
        "ExtensionCatalogSelectionOutcome": (
            "undeclared",
            "selected",
            "ambiguous",
            "conflict",
        ),
        "ExtensionCatalogInspectionLookupVariant": (
            "found",
            "absent",
            "unknown",
            "conflict",
        ),
    }
)

_NODE_ARITIES: Mapping[str, int] = MappingProxyType(
    {
        "extension_catalog_inspection": 6,
        "reference": 4,
        "target": 5,
        "type_reference": 6,
        "type_use": 5,
        "callable_identity": 3,
        "operator_identity": 4,
        "cast_identity": 3,
        "scope": 3,
        "declaration": 4,
        "entry_evidence": 5,
        "native_type_entry": 5,
        "scalar_function_entry": 12,
        "aggregate_entry": 9,
        "operator_entry": 8,
        "cast_entry": 8,
        "catalog": 11,
        "source": 6,
        "exact_group": 5,
        "completeness_claim": 5,
        "completeness_group": 5,
        "key": 8,
        "capability_evidence": 8,
        "fact": 7,
        "availability": 8,
        "candidate": 6,
        "selection": 10,
        "provider_inputs": 5,
        "lookup": 4,
        "provider_occurrence": 12,
    }
)

EXTENSION_CATALOG_INSPECTION_PURE_NODE_KINDS: tuple[str, ...] = tuple(_NODE_ARITIES)

_ENTRY_FAMILY = MappingProxyType(
    {
        "native_type_entry": "native_type",
        "scalar_function_entry": "scalar_function",
        "aggregate_entry": "aggregate",
        "operator_entry": "operator",
        "cast_entry": "cast",
    }
)
_FAMILY_IDENTITY_LABEL = MappingProxyType(
    {
        "native_type": "type_reference",
        "scalar_function": "callable_identity",
        "aggregate": "callable_identity",
        "operator": "operator_identity",
        "cast": "cast_identity",
    }
)
_HEX = frozenset("0123456789abcdef")


def _reject(
    status: ExtensionCatalogInspectionPureStatus,
    item_position: int | None = None,
    field_position: int | None = None,
) -> ExtensionCatalogInspectionPureOutcome:
    return ExtensionCatalogInspectionPureOutcome(
        status=status,
        item_position=item_position,
        field_position=field_position,
    )


def _frame(payload: bytes) -> bytes:
    return len(payload).to_bytes(8, "big") + payload


def encode_extension_catalog_inspection_pure_value(
    value: ExtensionCatalogInspectionPureValue,
) -> bytes:
    if type(value) is not ExtensionCatalogInspectionPureValue:
        raise TypeError("Inspection pure encoding requires an exact value")
    if value.tag is ExtensionCatalogInspectionPureTag.ABSENT:
        return b"n"
    if value.tag is ExtensionCatalogInspectionPureTag.BOOLEAN:
        assert value.boolean is not None
        return b"b1" if value.boolean else b"b0"
    if value.tag is ExtensionCatalogInspectionPureTag.INTEGER:
        assert value.integer is not None
        return b"i" + _frame(str(value.integer).encode("ascii"))
    if value.tag is ExtensionCatalogInspectionPureTag.TEXT:
        assert value.text is not None
        return b"s" + _frame(value.text.encode("utf-8"))
    if value.tag is ExtensionCatalogInspectionPureTag.ENUMERATION:
        assert value.enum_type is not None and value.enum_value is not None
        return (
            b"e"
            + _frame(value.enum_type.encode("utf-8"))
            + _frame(value.enum_value.encode("utf-8"))
        )
    if value.tag is ExtensionCatalogInspectionPureTag.TUPLE:
        return (
            b"t"
            + len(value.items).to_bytes(8, "big")
            + b"".join(
                _frame(encode_extension_catalog_inspection_pure_value(item))
                for item in value.items
            )
        )
    raise ValueError("Unknown inspection pure tag cannot be encoded")


def _shape_status(
    value: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureStatus | None:
    if value.tag is ExtensionCatalogInspectionPureTag.UNKNOWN:
        return ExtensionCatalogInspectionPureStatus.UNKNOWN_VALUE_TAG
    if value.tag is ExtensionCatalogInspectionPureTag.ABSENT:
        valid = (
            value.text is None
            and value.integer is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and not value.items
        )
    elif value.tag is ExtensionCatalogInspectionPureTag.BOOLEAN:
        valid = (
            value.boolean is not None
            and value.text is None
            and value.integer is None
            and value.enum_type is None
            and value.enum_value is None
            and not value.items
        )
    elif value.tag is ExtensionCatalogInspectionPureTag.INTEGER:
        integer = value.integer
        valid = (
            integer is not None
            and value.text is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and not value.items
        )
        if not valid:
            return ExtensionCatalogInspectionPureStatus.VALUE_SHAPE_MISMATCH
        assert integer is not None
        if not 0 <= integer <= EXTENSION_CATALOG_INSPECTION_PURE_MAX_INTEGER:
            return ExtensionCatalogInspectionPureStatus.INTEGER_OUT_OF_RANGE
    elif value.tag is ExtensionCatalogInspectionPureTag.TEXT:
        valid = (
            value.text is not None
            and value.integer is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
            and not value.items
        )
    elif value.tag is ExtensionCatalogInspectionPureTag.ENUMERATION:
        enum_type = value.enum_type
        enum_value = value.enum_value
        valid = (
            enum_type is not None
            and enum_value is not None
            and value.text is None
            and value.integer is None
            and value.boolean is None
            and not value.items
        )
        if valid:
            assert enum_type is not None and enum_value is not None
            vocabulary = _ENUMERATIONS.get(enum_type)
            if vocabulary is None or enum_value not in vocabulary:
                return ExtensionCatalogInspectionPureStatus.UNKNOWN_ENUMERATION
    else:
        valid = (
            value.text is None
            and value.integer is None
            and value.boolean is None
            and value.enum_type is None
            and value.enum_value is None
        )
    return None if valid else ExtensionCatalogInspectionPureStatus.VALUE_SHAPE_MISMATCH


def _validate_tree(
    value: ExtensionCatalogInspectionPureValue,
    position: list[int],
) -> ExtensionCatalogInspectionPureOutcome | None:
    item_position = position[0]
    position[0] += 1
    status = _shape_status(value)
    if status is not None:
        return _reject(status, item_position)
    for field_position, child in enumerate(value.items):
        outcome = _validate_tree(child, position)
        if outcome is not None:
            if outcome.field_position is None:
                return _reject(outcome.status, outcome.item_position, field_position)
            return outcome
    return None


def _text(value: ExtensionCatalogInspectionPureValue) -> str | None:
    return value.text if value.tag is ExtensionCatalogInspectionPureTag.TEXT else None


def _integer(value: ExtensionCatalogInspectionPureValue) -> int | None:
    return (
        value.integer
        if value.tag is ExtensionCatalogInspectionPureTag.INTEGER
        else None
    )


def _enum(value: ExtensionCatalogInspectionPureValue) -> str | None:
    return (
        value.enum_value
        if value.tag is ExtensionCatalogInspectionPureTag.ENUMERATION
        else None
    )


def _node_label(value: ExtensionCatalogInspectionPureValue) -> str | None:
    if value.tag is not ExtensionCatalogInspectionPureTag.TUPLE or not value.items:
        return None
    return _text(value.items[0])


def _is_node(
    value: ExtensionCatalogInspectionPureValue,
    label: str,
) -> bool:
    return _node_label(value) == label and len(value.items) == _NODE_ARITIES[label]


def _node_collection(
    value: ExtensionCatalogInspectionPureValue,
    labels: tuple[str, ...],
) -> bool:
    return value.tag is ExtensionCatalogInspectionPureTag.TUPLE and all(
        _validate_node_schema(item, labels) for item in value.items
    )


def _optional_node(
    value: ExtensionCatalogInspectionPureValue,
    labels: tuple[str, ...],
) -> bool:
    return value.tag is ExtensionCatalogInspectionPureTag.ABSENT or (
        _validate_node_schema(value, labels)
    )


def _validate_node_schema(
    value: ExtensionCatalogInspectionPureValue,
    labels: tuple[str, ...],
) -> bool:
    label = _node_label(value)
    if label not in labels or len(value.items) != _NODE_ARITIES[label]:
        return False
    if label in {
        "reference",
        "target",
        "source",
        "entry_evidence",
        "key",
        "capability_evidence",
    }:
        return True
    if label == "type_reference":
        return True
    if label == "type_use":
        return _optional_node(value.items[2], ("type_reference",))
    if label == "callable_identity":
        return _node_collection(value.items[2], ("type_reference",))
    if label == "operator_identity":
        return _node_collection(value.items[3], ("type_reference",))
    if label == "cast_identity":
        return _validate_node_schema(value.items[1], ("type_reference",)) and (
            _validate_node_schema(value.items[2], ("type_reference",))
        )
    if label == "scope":
        return _validate_node_schema(
            value.items[2],
            (
                "type_reference",
                "callable_identity",
                "operator_identity",
                "cast_identity",
            ),
        )
    if label == "declaration":
        return _node_collection(value.items[2], ("type_use",)) and _optional_node(
            value.items[3],
            ("callable_identity",),
        )
    if label == "native_type_entry":
        return (
            _validate_node_schema(value.items[2], ("type_reference",))
            and _optional_node(value.items[3], ("type_reference",))
            and _validate_node_schema(value.items[4], ("entry_evidence",))
        )
    if label == "scalar_function_entry":
        return (
            _validate_node_schema(value.items[2], ("declaration",))
            and _validate_node_schema(value.items[3], ("type_use",))
            and _validate_node_schema(value.items[11], ("entry_evidence",))
        )
    if label == "aggregate_entry":
        return (
            _validate_node_schema(value.items[3], ("declaration",))
            and _validate_node_schema(value.items[4], ("type_use",))
            and _validate_node_schema(value.items[8], ("entry_evidence",))
        )
    if label == "operator_entry":
        return (
            _node_collection(value.items[4], ("type_use",))
            and _optional_node(value.items[5], ("operator_identity",))
            and _validate_node_schema(value.items[6], ("type_use",))
            and _validate_node_schema(value.items[7], ("entry_evidence",))
        )
    if label == "cast_entry":
        return (
            _validate_node_schema(value.items[2], ("type_use",))
            and _validate_node_schema(value.items[3], ("type_use",))
            and _optional_node(value.items[4], ("cast_identity",))
            and _validate_node_schema(value.items[7], ("entry_evidence",))
        )
    if label == "exact_group":
        return _validate_node_schema(value.items[2], ("scope",))
    if label == "completeness_claim":
        return _validate_node_schema(value.items[2], ("scope",))
    if label == "completeness_group":
        return _validate_node_schema(value.items[2], ("scope",))
    if label == "catalog":
        return (
            _validate_node_schema(value.items[2], ("reference",))
            and _validate_node_schema(value.items[3], ("target",))
            and _node_collection(value.items[6], ("source",))
            and _node_collection(value.items[7], tuple(_ENTRY_FAMILY))
            and _node_collection(value.items[8], ("exact_group",))
            and _node_collection(value.items[9], ("completeness_claim",))
            and _node_collection(value.items[10], ("completeness_group",))
        )
    if label == "fact":
        return _validate_node_schema(value.items[1], ("key",)) and _node_collection(
            value.items[6],
            ("capability_evidence",),
        )
    if label == "availability":
        return _validate_node_schema(value.items[5], ("reference",)) and (
            _validate_node_schema(value.items[6], ("target",))
        )
    if label == "candidate":
        return _validate_node_schema(value.items[2], ("reference",)) and (
            _validate_node_schema(value.items[3], ("target",))
        )
    if label == "selection":
        return (
            _validate_node_schema(value.items[1], ("target",))
            and _node_collection(value.items[4], ("availability",))
            and _node_collection(value.items[8], ("candidate",))
        )
    if label == "provider_inputs":
        return _validate_node_schema(value.items[1], ("key",)) and _node_collection(
            value.items[4],
            ("fact",),
        )
    if label == "lookup":
        return _node_collection(value.items[3], ("fact",))
    if label == "provider_occurrence":
        return (
            _validate_node_schema(value.items[2], ("key",))
            and _validate_node_schema(value.items[3], ("scope",))
            and _validate_node_schema(value.items[5], ("selection",))
            and _validate_node_schema(value.items[10], ("provider_inputs",))
            and _validate_node_schema(value.items[11], ("lookup",))
        )
    if label == "extension_catalog_inspection":
        return _node_collection(value.items[4], ("catalog",)) and _node_collection(
            value.items[5],
            ("provider_occurrence",),
        )
    return False


def _valid_sha256(value: ExtensionCatalogInspectionPureValue) -> bool:
    text = _text(value)
    return text is not None and len(text) == 64 and set(text) <= _HEX


def _positions_in_range(
    values: ExtensionCatalogInspectionPureValue,
    upper_bound: int,
) -> bool:
    if values.tag is not ExtensionCatalogInspectionPureTag.TUPLE:
        return False
    for item in values.items:
        position = _integer(item)
        if position is None or position >= upper_bound:
            return False
    return True


def _scope_parts(
    scope: ExtensionCatalogInspectionPureValue,
) -> tuple[str, str] | None:
    if not _is_node(scope, "scope"):
        return None
    family = _enum(scope.items[1])
    identity_label = _node_label(scope.items[2])
    if family is None or identity_label is None:
        return None
    return family, identity_label


def _validate_catalog(
    catalog: ExtensionCatalogInspectionPureValue,
    catalog_count: int,
) -> ExtensionCatalogInspectionPureStatus | None:
    if not _is_node(catalog, "catalog"):
        return ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
    if not _is_node(catalog.items[2], "reference") or not _is_node(
        catalog.items[3], "target"
    ):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    if not _valid_sha256(catalog.items[4]):
        return ExtensionCatalogInspectionPureStatus.INVALID_SHA256
    if _integer(catalog.items[5]) is None:
        return ExtensionCatalogInspectionPureStatus.CHILD_COUNT_MISMATCH
    sources, entries, groups, claims, completeness_groups = catalog.items[6:11]
    if any(
        value.tag is not ExtensionCatalogInspectionPureTag.TUPLE
        for value in (sources, entries, groups, claims, completeness_groups)
    ):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    for position, source in enumerate(sources.items):
        if not _is_node(source, "source") or _integer(source.items[1]) != position:
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
    for position, entry in enumerate(entries.items):
        label = _node_label(entry)
        if label not in _ENTRY_FAMILY or _integer(entry.items[1]) != position:
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
    for position, group in enumerate(groups.items):
        if not _is_node(group, "exact_group") or _integer(group.items[1]) != position:
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
        parts = _scope_parts(group.items[2])
        if parts is None or _FAMILY_IDENTITY_LABEL.get(parts[0]) != parts[1]:
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_FAMILY_IDENTITY
        links = group.items[4]
        if links.tag is not ExtensionCatalogInspectionPureTag.TUPLE or not links.items:
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_ENTRY_GROUP
        positions = tuple(_integer(item) for item in links.items)
        if any(item is None or item >= len(entries.items) for item in positions):
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        if any(
            _ENTRY_FAMILY.get(_node_label(entries.items[item]) or "") != parts[0]
            for item in positions
            if item is not None
        ):
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_ENTRY_GROUP
        state = _enum(group.items[3])
        if (
            state == "unique"
            and len(positions) != 1
            or state != "unique"
            and len(positions) < 2
        ):
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_ENTRY_GROUP
    for position, claim in enumerate(claims.items):
        if (
            not _is_node(claim, "completeness_claim")
            or _integer(claim.items[1]) != position
        ):
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
    for position, group in enumerate(completeness_groups.items):
        if (
            not _is_node(group, "completeness_group")
            or _integer(group.items[1]) != position
        ):
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
        links = group.items[4]
        if links.tag is not ExtensionCatalogInspectionPureTag.TUPLE or not links.items:
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_COMPLETENESS_LINK
        claim_positions = tuple(_integer(item) for item in links.items)
        if any(item is None or item >= len(claims.items) for item in claim_positions):
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        kinds = {
            _enum(claims.items[item].items[3])
            for item in claim_positions
            if item is not None
        }
        expected = (
            "complete"
            if kinds == {"complete"}
            else "incomplete"
            if kinds == {"incomplete"}
            else "conflict"
        )
        if _enum(group.items[3]) != expected:
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_COMPLETENESS_LINK
    del catalog_count
    return None


def _validate_selection(
    selection: ExtensionCatalogInspectionPureValue,
    catalog_count: int,
) -> ExtensionCatalogInspectionPureStatus | None:
    if not _is_node(selection, "selection"):
        return ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
    availability = selection.items[4]
    candidates = selection.items[8]
    if (
        availability.tag is not ExtensionCatalogInspectionPureTag.TUPLE
        or candidates.tag is not ExtensionCatalogInspectionPureTag.TUPLE
    ):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    for position, declaration in enumerate(availability.items):
        if (
            not _is_node(declaration, "availability")
            or _integer(declaration.items[1]) != position
        ):
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
        catalog_position = _integer(declaration.items[4])
        if catalog_position is None or catalog_position >= catalog_count:
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        if not _valid_sha256(declaration.items[7]):
            return ExtensionCatalogInspectionPureStatus.INVALID_SHA256
    for links in selection.items[5:8]:
        if not _positions_in_range(links, len(availability.items)):
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
    for candidate in candidates.items:
        if not _is_node(candidate, "candidate"):
            return ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
        catalog_position = _integer(candidate.items[1])
        if catalog_position is None or catalog_position >= catalog_count:
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        if not _valid_sha256(candidate.items[4]):
            return ExtensionCatalogInspectionPureStatus.INVALID_SHA256
        declaration_links = candidate.items[5]
        if not _positions_in_range(declaration_links, len(availability.items)):
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
    outcome = _enum(selection.items[3])
    selected = selection.items[9]
    if outcome == "selected":
        selected_position = _integer(selected)
        if (
            selected_position is None
            or selected_position >= catalog_count
            or len(candidates.items) != 1
        ):
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_SELECTION_LINK
    elif selected.tag is not ExtensionCatalogInspectionPureTag.ABSENT:
        return ExtensionCatalogInspectionPureStatus.INCONSISTENT_SELECTION_LINK
    return None


def _validate_lookup(
    lookup: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureStatus | None:
    if not _is_node(lookup, "lookup"):
        return ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
    variant = _enum(lookup.items[1])
    reason = lookup.items[2]
    facts = lookup.items[3]
    if facts.tag is not ExtensionCatalogInspectionPureTag.TUPLE:
        return ExtensionCatalogInspectionPureStatus.INCONSISTENT_PROVIDER_RESULT
    if variant == "found":
        valid = (
            reason.tag is ExtensionCatalogInspectionPureTag.ABSENT
            and len(facts.items) == 1
        )
    elif variant == "absent":
        valid = _enum(reason) == "no_catalog_entry" and not facts.items
    elif variant == "unknown":
        valid = (
            reason.tag is ExtensionCatalogInspectionPureTag.ENUMERATION
            and not facts.items
        )
    else:
        valid = _enum(reason) == "conflicting_evidence" and len(facts.items) >= 2
    return (
        None
        if valid
        else ExtensionCatalogInspectionPureStatus.INCONSISTENT_PROVIDER_RESULT
    )


def _validate_inspection_relations(
    root: ExtensionCatalogInspectionPureValue,
) -> ExtensionCatalogInspectionPureStatus | None:
    if root.tag is not ExtensionCatalogInspectionPureTag.TUPLE:
        return ExtensionCatalogInspectionPureStatus.MISSING_ROOT
    if len(root.items) < 6:
        return ExtensionCatalogInspectionPureStatus.MISSING_ROOT
    if len(root.items) > 6:
        return ExtensionCatalogInspectionPureStatus.TRAILING_ITEM
    if not _is_node(root, "extension_catalog_inspection"):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    format_value = root.items[1]
    if (
        format_value.enum_type != "ExtensionCatalogInspectionFormat"
        or format_value.enum_value != EXTENSION_CATALOG_INSPECTION_PURE_FORMAT_MARKER
    ):
        return ExtensionCatalogInspectionPureStatus.UNKNOWN_FORMAT_MARKER
    catalogs, providers = root.items[4], root.items[5]
    if (
        catalogs.tag is not ExtensionCatalogInspectionPureTag.TUPLE
        or providers.tag is not ExtensionCatalogInspectionPureTag.TUPLE
    ):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    catalog_keys: list[tuple[str, ...]] = []
    for position, catalog in enumerate(catalogs.items):
        if _integer(catalog.items[1]) != position:
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
        status = _validate_catalog(catalog, len(catalogs.items))
        if status is not None:
            return status
        reference, target = catalog.items[2], catalog.items[3]
        catalog_keys.append(
            (
                _text(reference.items[1]) or "",
                _text(reference.items[2]) or "",
                _text(reference.items[3]) or "",
                *(_text(item) or "" for item in target.items[1:]),
                _text(catalog.items[4]) or "",
            )
        )
    if catalog_keys != sorted(catalog_keys):
        return ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION
    requirement_positions: list[int] = []
    for provider in providers.items:
        if not _is_node(provider, "provider_occurrence"):
            return ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
        requirement_position = _integer(provider.items[1])
        if (
            requirement_position is None
            or requirement_position in requirement_positions
        ):
            return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
        requirement_positions.append(requirement_position)
        selection_status = _validate_selection(provider.items[5], len(catalogs.items))
        if selection_status is not None:
            return selection_status
        parts = _scope_parts(provider.items[3])
        if parts is None or _FAMILY_IDENTITY_LABEL.get(parts[0]) != parts[1]:
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_FAMILY_IDENTITY
        selected_position = _integer(provider.items[6])
        if selected_position is not None and selected_position >= len(catalogs.items):
            return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        if selected_position is None:
            if (
                any(
                    item.tag is not ExtensionCatalogInspectionPureTag.ABSENT
                    for item in (provider.items[7], provider.items[9])
                )
                or provider.items[8].items
            ):
                return ExtensionCatalogInspectionPureStatus.INCONSISTENT_PROVIDER_RESULT
        else:
            catalog = catalogs.items[selected_position]
            for link, collection_index in (
                (provider.items[7], 8),
                (provider.items[9], 10),
            ):
                position = _integer(link)
                if position is not None and position >= len(
                    catalog.items[collection_index].items
                ):
                    return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
            if not _positions_in_range(
                provider.items[8],
                len(catalog.items[7].items),
            ):
                return ExtensionCatalogInspectionPureStatus.DANGLING_POSITIONAL_LINK
        provider_inputs = provider.items[10]
        if not _is_node(
            provider_inputs, "provider_inputs"
        ) or encode_extension_catalog_inspection_pure_value(
            provider_inputs.items[1]
        ) != encode_extension_catalog_inspection_pure_value(provider.items[2]):
            return ExtensionCatalogInspectionPureStatus.INCONSISTENT_PROVIDER_RESULT
        lookup_status = _validate_lookup(provider.items[11])
        if lookup_status is not None:
            return lookup_status
    if requirement_positions != sorted(requirement_positions):
        return ExtensionCatalogInspectionPureStatus.ORDINAL_SEQUENCE_VIOLATION
    return None


def evaluate_extension_catalog_inspection_document(
    document: ExtensionCatalogInspectionPureDocument,
) -> ExtensionCatalogInspectionPureOutcome:
    if type(document) is not ExtensionCatalogInspectionPureDocument:
        raise TypeError("Inspection pure evaluation requires an exact document")
    if document.root is None:
        return _reject(ExtensionCatalogInspectionPureStatus.MISSING_ROOT)
    structural = _validate_tree(document.root, [0])
    if structural is not None:
        return structural
    if (
        _node_label(document.root) == "extension_catalog_inspection"
        and len(document.root.items) > _NODE_ARITIES["extension_catalog_inspection"]
    ):
        return _reject(ExtensionCatalogInspectionPureStatus.TRAILING_ITEM, 0)
    if (
        document.root.tag is ExtensionCatalogInspectionPureTag.TUPLE
        and len(document.root.items) == _NODE_ARITIES["extension_catalog_inspection"]
        and _node_label(document.root) != "extension_catalog_inspection"
    ):
        return _reject(ExtensionCatalogInspectionPureStatus.SECTION_ORDER_VIOLATION, 0)
    if not _validate_node_schema(document.root, ("extension_catalog_inspection",)):
        return _reject(ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH, 0)
    try:
        relation_status = _validate_inspection_relations(document.root)
    except (IndexError, KeyError, StopIteration):
        relation_status = ExtensionCatalogInspectionPureStatus.TUPLE_SCHEMA_MISMATCH
    if relation_status is not None:
        return _reject(relation_status, 0)
    return ExtensionCatalogInspectionPureOutcome(
        status=ExtensionCatalogInspectionPureStatus.OK,
        canonical_bytes=encode_extension_catalog_inspection_pure_value(document.root),
    )
