"""Private total pure boundary for canonical capability inspection records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

__all__: tuple[str, ...] = ()

CAPABILITY_PURE_FORMAT_MARKER = "pietto.capability-inspection.v1"
CAPABILITY_PURE_MAX_INTEGER = 2**63 - 1

_ESCAPES: Mapping[str, str] = MappingProxyType(
    {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}
)


class CapabilityPureTag(StrEnum):
    TEXT = "s"
    ENUMERATION = "e"
    INTEGER = "i"
    BOOLEAN = "b"
    ABSENT = "n"


class CapabilityPureStatus(StrEnum):
    OK = "ok"
    EMPTY_DOCUMENT = "empty_document"
    MISSING_HEADER_RECORD = "missing_header_record"
    DUPLICATE_SINGLETON_RECORD = "duplicate_singleton_record"
    UNKNOWN_RECORD_KIND = "unknown_record_kind"
    UNKNOWN_FORMAT_MARKER = "unknown_format_marker"
    FIELD_ARITY_MISMATCH = "field_arity_mismatch"
    FIELD_KEY_MISMATCH = "field_key_mismatch"
    VALUE_TAG_MISMATCH = "value_tag_mismatch"
    ABSENT_VALUE_NOT_ALLOWED = "absent_value_not_allowed"
    MISSING_VALUE_PAYLOAD = "missing_value_payload"
    EXTRA_VALUE_PAYLOAD = "extra_value_payload"
    NEGATIVE_INTEGER = "negative_integer"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    MISSING_REQUIRED_RECORD = "missing_required_record"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    ORDINAL_SEQUENCE_VIOLATION = "ordinal_sequence_violation"
    CHILD_COUNT_MISMATCH = "child_count_mismatch"
    TRAILING_RECORD_AFTER_DOCUMENT = "trailing_record_after_document"
    INCONSISTENT_DOCUMENT_STATE = "inconsistent_document_state"
    INCONSISTENT_RECORD_STATE = "inconsistent_record_state"
    INCONSISTENT_SCOPE_RELATION = "inconsistent_scope_relation"


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityPureValue:
    tag: CapabilityPureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None

    def __post_init__(self) -> None:
        if type(self.tag) is not CapabilityPureTag:
            raise TypeError("Capability pure values require an exact tag")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Capability pure text must be exact text")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Capability pure integers must be exact integers")
        if self.boolean is not None and type(self.boolean) is not bool:
            raise TypeError("Capability pure booleans must be exact booleans")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityPureField:
    key: str
    value: CapabilityPureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str:
            raise TypeError("Capability pure field keys must be exact text")
        if type(self.value) is not CapabilityPureValue:
            raise TypeError("Capability pure fields require exact values")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityPureRecord:
    kind: str
    fields: tuple[CapabilityPureField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not str:
            raise TypeError("Capability pure record kinds must be exact text")
        if type(self.fields) is not tuple or any(
            type(field) is not CapabilityPureField for field in self.fields
        ):
            raise TypeError("Capability pure records require exact field tuples")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityPureDocument:
    records: tuple[CapabilityPureRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not CapabilityPureRecord for record in self.records
        ):
            raise TypeError("Capability pure documents require exact record tuples")


@dataclass(frozen=True, slots=True, kw_only=True)
class CapabilityPureOutcome:
    status: CapabilityPureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not CapabilityPureStatus:
            raise TypeError("Capability pure outcomes require an exact status")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Capability pure payloads must be exact bytes")
        for coordinate in (self.record_position, self.field_position):
            if coordinate is not None and type(coordinate) is not int:
                raise TypeError("Capability pure coordinates must be integers")
        if self.status is CapabilityPureStatus.OK:
            if self.canonical_bytes is None:
                raise ValueError("Accepted capability outcomes require canonical bytes")
            if self.record_position is not None or self.field_position is not None:
                raise ValueError("Accepted capability outcomes carry no coordinates")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected capability outcomes carry no canonical bytes")
        elif self.field_position is not None and self.record_position is None:
            raise ValueError("A field coordinate requires a record coordinate")


CAPABILITY_PURE_ABSENT = CapabilityPureValue(tag=CapabilityPureTag.ABSENT)


def capability_pure_text(value: str) -> CapabilityPureValue:
    return CapabilityPureValue(tag=CapabilityPureTag.TEXT, text=value)


def capability_pure_integer(value: int) -> CapabilityPureValue:
    return CapabilityPureValue(tag=CapabilityPureTag.INTEGER, integer=value)


def capability_pure_boolean(value: bool) -> CapabilityPureValue:
    return CapabilityPureValue(tag=CapabilityPureTag.BOOLEAN, boolean=value)


def capability_pure_enumeration(value: str) -> CapabilityPureValue:
    return CapabilityPureValue(tag=CapabilityPureTag.ENUMERATION, text=value)


@dataclass(frozen=True, slots=True)
class _KeySpec:
    key: str
    tag: CapabilityPureTag
    optional: bool = False
    vocabulary: tuple[str, ...] | None = None
    non_empty: bool = False


def _key(
    key: str,
    tag: CapabilityPureTag,
    *,
    optional: bool = False,
    vocabulary: tuple[str, ...] | None = None,
    non_empty: bool = False,
) -> _KeySpec:
    return _KeySpec(key, tag, optional, vocabulary, non_empty)


_TEXT = CapabilityPureTag.TEXT
_INTEGER = CapabilityPureTag.INTEGER
_BOOLEAN = CapabilityPureTag.BOOLEAN
_ENUMERATION = CapabilityPureTag.ENUMERATION

_DECLARATIONS = ("undeclared", "declared")
_PACKAGE_ROLES = ("root", "dependency")
_COLUMN_VARIANTS = ("undeclared", "blocked", "checked")
_PROFILE_ORDERS = ("base", "supplied_overlay", "dependency")
_PROFILE_SCHEMAS = ("pietto.capability-profile.v1",)
_PROFILE_KINDS = ("base", "overlay")
_TARGET_KINDS = ("database", "extension")
_OWNER_KINDS = ("compiler", "project")
_BLOCKER_KINDS = (
    "profile_not_declared_available",
    "profile_authority_mismatch",
)
_BLOCKER_PROFILE_ROLES = ("selected", "bucket")
_CAPABILITY_DOMAINS = (
    "logical_type",
    "literal",
    "parameter",
    "scalar_function",
    "unary_operator",
    "binary_operator",
    "comparison",
    "null_test",
    "clause",
    "aggregate",
    "window_function",
    "expression_stage",
    "conversion",
    "dialect_lowering",
    "extension_signature",
)
_CAPABILITY_SUPPORT = ("supported", "explicitly_unsupported")
_DISPOSITIONS = ("none", "deferred", "out_of_scope")
_EVIDENCE_SOURCES = (
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
)
_REASONS = (
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
)
_LOOKUP_VARIANTS = ("found", "absent", "unknown", "conflict")
_REQUIREMENT_STATUSES = (
    "satisfied",
    "unsupported",
    "absent",
    "unknown",
    "conflict",
)

_PROFILE_FIELDS = (
    _key("schema", _ENUMERATION, vocabulary=_PROFILE_SCHEMAS),
    _key("namespace", _TEXT, non_empty=True),
    _key("name", _TEXT, non_empty=True),
    _key("profile_release", _TEXT, non_empty=True),
    _key("kind", _ENUMERATION, vocabulary=_PROFILE_KINDS),
    _key("target_kind", _ENUMERATION, vocabulary=_TARGET_KINDS),
    _key("database_family", _TEXT, non_empty=True),
    _key("target_release", _TEXT, non_empty=True),
    _key("extension_identity", _TEXT, optional=True, non_empty=True),
    _key("extension_release", _TEXT, optional=True, non_empty=True),
)

_KEY_FIELDS = (
    _key("domain", _ENUMERATION, vocabulary=_CAPABILITY_DOMAINS),
    _key("subject", _TEXT, optional=True, non_empty=True),
    _key("operation", _TEXT, optional=True, non_empty=True),
    _key("operands", _INTEGER),
    _key("context", _TEXT, optional=True, non_empty=True),
    _key("dialect", _TEXT, optional=True, non_empty=True),
    _key("extension", _TEXT, optional=True, non_empty=True),
)

_AVAILABILITY_FIELDS = (
    _key("owner_kind", _ENUMERATION, vocabulary=_OWNER_KINDS),
    _key("owner_position", _INTEGER),
    _key("project_path", _TEXT, optional=True),
    *_PROFILE_FIELDS,
)

_FACT_FIELDS = (
    *_KEY_FIELDS,
    _key("support", _ENUMERATION, vocabulary=_CAPABILITY_SUPPORT),
    _key("disposition", _ENUMERATION, vocabulary=_DISPOSITIONS),
    _key("disposition_owner", _TEXT, optional=True, non_empty=True),
    _key("disposition_reason", _TEXT, optional=True, non_empty=True),
    _key("evidence", _INTEGER),
)

_EVIDENCE_FIELDS = (
    _key("source", _ENUMERATION, vocabulary=_EVIDENCE_SOURCES),
    _key("source_path", _TEXT, non_empty=True),
    _key("source_reference", _TEXT, non_empty=True),
    _key("reason", _ENUMERATION, optional=True, vocabulary=_REASONS),
    _key("dialect", _TEXT, optional=True, non_empty=True),
    _key("backend", _TEXT, optional=True, non_empty=True),
    _key("extension", _TEXT, optional=True, non_empty=True),
)

_SCHEMA: Mapping[str, tuple[_KeySpec, ...]] = MappingProxyType(
    {
        "inspection": (
            _key("format", _ENUMERATION),
            _key("declaration", _ENUMERATION, vocabulary=_DECLARATIONS),
            _key("targets", _INTEGER),
            _key("requirements", _INTEGER),
        ),
        "package": (
            _key("role", _ENUMERATION, vocabulary=_PACKAGE_ROLES),
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("release", _TEXT, non_empty=True),
            _key("content_digest", _TEXT, non_empty=True),
        ),
        "requirements": (
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("count", _INTEGER),
        ),
        "target": (
            _key("target", _INTEGER),
            _key("variant", _ENUMERATION, vocabulary=_COLUMN_VARIANTS),
            _key("supplied_overlays", _INTEGER),
            _key("dependency_profiles", _INTEGER),
            _key("availability", _INTEGER),
            _key("blockers", _INTEGER),
        ),
        "target_profile": (
            _key("target", _INTEGER),
            _key("order", _ENUMERATION, vocabulary=_PROFILE_ORDERS),
            _key("profile", _INTEGER),
            *_PROFILE_FIELDS,
        ),
        "availability": (
            _key("target", _INTEGER),
            _key("occurrence", _INTEGER),
            *_AVAILABILITY_FIELDS,
        ),
        "blocker": (
            _key("target", _INTEGER),
            _key("blocker", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary=_BLOCKER_KINDS),
            _key("has_bucket", _BOOLEAN),
            _key("bucket_occurrences", _INTEGER),
        ),
        "blocker_profile": (
            _key("target", _INTEGER),
            _key("blocker", _INTEGER),
            _key("role", _TEXT, vocabulary=_BLOCKER_PROFILE_ROLES),
            *_PROFILE_FIELDS,
        ),
        "blocker_availability": (
            _key("target", _INTEGER),
            _key("blocker", _INTEGER),
            _key("occurrence", _INTEGER),
            *_AVAILABILITY_FIELDS,
        ),
        "requirement": (
            _key("requirement", _INTEGER),
            *_KEY_FIELDS,
        ),
        "requirement_operand": (
            _key("requirement", _INTEGER),
            _key("operand", _INTEGER),
            _key("value", _TEXT, non_empty=True),
        ),
        "cell": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("has_check", _BOOLEAN),
            _key(
                "status",
                _ENUMERATION,
                optional=True,
                vocabulary=_REQUIREMENT_STATUSES,
            ),
            _key("target_occurrences", _INTEGER),
            _key(
                "target_lookup",
                _ENUMERATION,
                optional=True,
                vocabulary=_LOOKUP_VARIANTS,
            ),
            _key("target_reason", _ENUMERATION, optional=True, vocabulary=_REASONS),
            _key("target_lookup_facts", _INTEGER),
            _key("provider_domain_complete", _BOOLEAN, optional=True),
            _key(
                "provider_unknown_reason",
                _ENUMERATION,
                optional=True,
                vocabulary=_REASONS,
            ),
            _key(
                "provider_lookup",
                _ENUMERATION,
                optional=True,
                vocabulary=_LOOKUP_VARIANTS,
            ),
            _key(
                "provider_reason",
                _ENUMERATION,
                optional=True,
                vocabulary=_REASONS,
            ),
            _key("provider_lookup_facts", _INTEGER),
        ),
        "target_occurrence": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("occurrence", _INTEGER),
            _key("profile", _INTEGER),
            _key("profile_namespace", _TEXT, non_empty=True),
            _key("profile_name", _TEXT, non_empty=True),
            _key("profile_release", _TEXT, non_empty=True),
            _key("profile_fact", _INTEGER),
        ),
        "target_fact": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("occurrence", _INTEGER),
            *_FACT_FIELDS,
        ),
        "target_fact_operand": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("occurrence", _INTEGER),
            _key("operand", _INTEGER),
            _key("value", _TEXT, non_empty=True),
        ),
        "target_fact_evidence": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("occurrence", _INTEGER),
            _key("evidence", _INTEGER),
            *_EVIDENCE_FIELDS,
        ),
        "provider_fact": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("fact", _INTEGER),
            *_FACT_FIELDS,
        ),
        "provider_fact_operand": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("fact", _INTEGER),
            _key("operand", _INTEGER),
            _key("value", _TEXT, non_empty=True),
        ),
        "provider_fact_evidence": (
            _key("requirement", _INTEGER),
            _key("target", _INTEGER),
            _key("fact", _INTEGER),
            _key("evidence", _INTEGER),
            *_EVIDENCE_FIELDS,
        ),
    }
)

CAPABILITY_PURE_RECORD_KINDS: tuple[str, ...] = tuple(_SCHEMA)

_Profile = tuple[
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str,
    str | None,
    str | None,
]
_Key = tuple[
    str,
    str | None,
    str | None,
    tuple[str, ...],
    str | None,
    str | None,
    str | None,
]


def _reject(
    status: CapabilityPureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> CapabilityPureOutcome:
    return CapabilityPureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _validate_value(
    value: CapabilityPureValue,
    declared: _KeySpec,
    record_position: int,
    field_position: int,
) -> CapabilityPureOutcome | None:
    payloads = (value.text, value.integer, value.boolean)
    if value.tag is CapabilityPureTag.ABSENT:
        if not declared.optional:
            return _reject(
                CapabilityPureStatus.ABSENT_VALUE_NOT_ALLOWED,
                record_position,
                field_position,
            )
        if any(payload is not None for payload in payloads):
            return _reject(
                CapabilityPureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        return None
    if value.tag is not declared.tag:
        return _reject(
            CapabilityPureStatus.VALUE_TAG_MISMATCH,
            record_position,
            field_position,
        )
    if value.tag in {CapabilityPureTag.TEXT, CapabilityPureTag.ENUMERATION}:
        if value.text is None:
            return _reject(
                CapabilityPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if value.integer is not None or value.boolean is not None:
            return _reject(
                CapabilityPureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if declared.non_empty and not value.text:
            return _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                record_position,
                field_position,
            )
        if declared.vocabulary is not None and value.text not in declared.vocabulary:
            return _reject(
                CapabilityPureStatus.UNKNOWN_ENUMERATION,
                record_position,
                field_position,
            )
        return None
    if value.tag is CapabilityPureTag.INTEGER:
        if value.integer is None:
            return _reject(
                CapabilityPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if value.text is not None or value.boolean is not None:
            return _reject(
                CapabilityPureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if value.integer < 0:
            return _reject(
                CapabilityPureStatus.NEGATIVE_INTEGER,
                record_position,
                field_position,
            )
        if value.integer > CAPABILITY_PURE_MAX_INTEGER:
            return _reject(
                CapabilityPureStatus.INTEGER_OUT_OF_RANGE,
                record_position,
                field_position,
            )
        return None
    if value.boolean is None:
        return _reject(
            CapabilityPureStatus.MISSING_VALUE_PAYLOAD,
            record_position,
            field_position,
        )
    if value.text is not None or value.integer is not None:
        return _reject(
            CapabilityPureStatus.EXTRA_VALUE_PAYLOAD,
            record_position,
            field_position,
        )
    return None


def _validate_fields(
    record: CapabilityPureRecord,
    record_position: int,
) -> CapabilityPureOutcome | None:
    specification = _SCHEMA[record.kind]
    if len(record.fields) != len(specification):
        return _reject(CapabilityPureStatus.FIELD_ARITY_MISMATCH, record_position)
    for field_position, (field, declared) in enumerate(
        zip(record.fields, specification, strict=True)
    ):
        if field.key != declared.key:
            return _reject(
                CapabilityPureStatus.FIELD_KEY_MISMATCH,
                record_position,
                field_position,
            )
        rejection = _validate_value(
            field.value,
            declared,
            record_position,
            field_position,
        )
        if rejection is not None:
            return rejection
    return None


def _expect(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    kind: str,
    parent_position: int,
    *,
    child: bool = False,
) -> tuple[CapabilityPureRecord | None, CapabilityPureOutcome | None]:
    if position >= len(records):
        return None, _reject(
            CapabilityPureStatus.CHILD_COUNT_MISMATCH
            if child
            else CapabilityPureStatus.MISSING_REQUIRED_RECORD,
            parent_position,
        )
    record = records[position]
    if record.kind not in _SCHEMA:
        return None, _reject(CapabilityPureStatus.UNKNOWN_RECORD_KIND, position)
    if record.kind != kind:
        if record.kind in {"inspection", "package", "requirements"}:
            return None, _reject(
                CapabilityPureStatus.DUPLICATE_SINGLETON_RECORD,
                position,
            )
        return None, _reject(
            CapabilityPureStatus.CHILD_COUNT_MISMATCH
            if child
            else CapabilityPureStatus.SECTION_ORDER_VIOLATION,
            parent_position if child else position,
        )
    rejection = _validate_fields(record, position)
    return record, rejection


def _value(record: CapabilityPureRecord, key: str) -> CapabilityPureValue:
    for field in record.fields:
        if field.key == key:
            return field.value
    raise ValueError("A validated capability record always carries its declared key")


def _text_value(record: CapabilityPureRecord, key: str) -> str:
    value = _value(record, key).text
    if value is None:
        raise ValueError("A validated capability text value cannot be absent")
    return value


def _optional_text_value(record: CapabilityPureRecord, key: str) -> str | None:
    value = _value(record, key)
    return None if value.tag is CapabilityPureTag.ABSENT else value.text


def _integer_value(record: CapabilityPureRecord, key: str) -> int:
    value = _value(record, key).integer
    if value is None:
        raise ValueError("A validated capability integer cannot be absent")
    return value


def _boolean_value(record: CapabilityPureRecord, key: str) -> bool:
    value = _value(record, key).boolean
    if value is None:
        raise ValueError("A validated capability boolean cannot be absent")
    return value


def _optional_boolean_value(record: CapabilityPureRecord, key: str) -> bool | None:
    value = _value(record, key)
    return None if value.tag is CapabilityPureTag.ABSENT else value.boolean


def _profile(record: CapabilityPureRecord, offset: int) -> _Profile:
    fields = record.fields[offset:]
    values = tuple(field.value for field in fields)
    return (
        values[0].text or "",
        values[1].text or "",
        values[2].text or "",
        values[3].text or "",
        values[4].text or "",
        values[5].text or "",
        values[6].text or "",
        values[7].text or "",
        None if values[8].tag is CapabilityPureTag.ABSENT else values[8].text,
        None if values[9].tag is CapabilityPureTag.ABSENT else values[9].text,
    )


def _profile_is_coherent(
    profile: _Profile,
    record_position: int,
    field_offset: int,
) -> CapabilityPureOutcome | None:
    (
        _schema,
        _namespace,
        _name,
        _release,
        kind,
        target_kind,
        _family,
        _target_release,
        extension,
        ext_release,
    ) = profile
    if kind == "base":
        if (
            target_kind != "database"
            or extension is not None
            or ext_release is not None
        ):
            return _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                record_position,
                field_offset + 4,
            )
    elif target_kind != "extension" or extension is None or ext_release is None:
        return _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            record_position,
            field_offset + 4,
        )
    return None


def _scope_matches(
    record: CapabilityPureRecord,
    expected: tuple[tuple[str, int], ...],
) -> bool:
    return all(_integer_value(record, key) == value for key, value in expected)


@dataclass(frozen=True, slots=True)
class _TargetLedger:
    variant: str
    dependency_profiles: tuple[_Profile, ...]


@dataclass(frozen=True, slots=True)
class _AvailabilityEntry:
    owner_kind: str
    owner_position: int
    project_path: str | None
    profile: _Profile
    record_position: int


def _parse_profile_record(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    target_position: int,
    order: str,
    profile_position: int,
    parent_position: int,
) -> tuple[int, _Profile | None, CapabilityPureOutcome | None]:
    record, rejection = _expect(
        records,
        position,
        "target_profile",
        parent_position,
        child=True,
    )
    if rejection is not None or record is None:
        return position, None, rejection
    if _integer_value(record, "target") != target_position:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                0,
            ),
        )
    if _text_value(record, "order") != order:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.SECTION_ORDER_VIOLATION,
                position,
                1,
            ),
        )
    if _integer_value(record, "profile") != profile_position:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                2,
            ),
        )
    profile = _profile(record, 3)
    rejection = _profile_is_coherent(profile, position, 3)
    return position + 1, profile, rejection


def _parse_availability_record(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    kind: str,
    scope: tuple[tuple[str, int], ...],
    occurrence_position: int,
    parent_position: int,
) -> tuple[int, _AvailabilityEntry | None, CapabilityPureOutcome | None]:
    record, rejection = _expect(
        records,
        position,
        kind,
        parent_position,
        child=True,
    )
    if rejection is not None or record is None:
        return position, None, rejection
    if not _scope_matches(record, scope):
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
            ),
        )
    ordinal_field = len(scope)
    if _integer_value(record, "occurrence") != occurrence_position:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                ordinal_field,
            ),
        )
    owner_field = ordinal_field + 1
    path_field = owner_field + 2
    owner_kind = _text_value(record, "owner_kind")
    project_path = _optional_text_value(record, "project_path")
    if (owner_kind == "compiler" and project_path is not None) or (
        owner_kind == "project" and project_path is None
    ):
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                position,
                path_field,
            ),
        )
    profile_offset = path_field + 1
    profile = _profile(record, profile_offset)
    rejection = _profile_is_coherent(profile, position, profile_offset)
    return (
        position + 1,
        _AvailabilityEntry(
            owner_kind,
            _integer_value(record, "owner_position"),
            project_path,
            profile,
            position,
        ),
        rejection,
    )


def _profile_reference(profile: _Profile) -> tuple[str, str, str]:
    return profile[1], profile[2], profile[3]


def _availability_authority(
    occurrence: _AvailabilityEntry,
) -> tuple[str, int, str | None, _Profile]:
    return (
        occurrence.owner_kind,
        occurrence.owner_position,
        occurrence.project_path,
        occurrence.profile,
    )


def _parse_blocker(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    target_position: int,
    blocker_position: int,
    dependency_profiles: tuple[_Profile, ...],
    availability: tuple[_AvailabilityEntry, ...],
    parent_position: int,
) -> tuple[int, CapabilityPureOutcome | None]:
    blocker, rejection = _expect(
        records,
        position,
        "blocker",
        parent_position,
        child=True,
    )
    if rejection is not None or blocker is None:
        return position, rejection
    blocker_record_position = position
    if _integer_value(blocker, "target") != target_position:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
            0,
        )
    if _integer_value(blocker, "blocker") != blocker_position:
        return position, _reject(
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            1,
        )
    blocker_kind = _text_value(blocker, "kind")
    has_bucket = _boolean_value(blocker, "has_bucket")
    bucket_count = _integer_value(blocker, "bucket_occurrences")
    position += 1

    selected, rejection = _expect(
        records,
        position,
        "blocker_profile",
        blocker_record_position,
        child=True,
    )
    if rejection is not None or selected is None:
        return position, rejection
    if not _scope_matches(
        selected,
        (("target", target_position), ("blocker", blocker_position)),
    ):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    if _text_value(selected, "role") != "selected":
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            position,
            2,
        )
    selected_profile = _profile(selected, 3)
    rejection = _profile_is_coherent(selected_profile, position, 3)
    if rejection is not None:
        return position, rejection
    if sum(profile == selected_profile for profile in dependency_profiles) != 1:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    position += 1

    bucket_profile: _Profile | None = None
    if has_bucket:
        bucket, rejection = _expect(
            records,
            position,
            "blocker_profile",
            blocker_record_position,
            child=True,
        )
        if rejection is not None or bucket is None:
            return position, rejection
        if not _scope_matches(
            bucket,
            (("target", target_position), ("blocker", blocker_position)),
        ):
            return position, _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
            )
        if _text_value(bucket, "role") != "bucket":
            return position, _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                position,
                2,
            )
        bucket_profile = _profile(bucket, 3)
        rejection = _profile_is_coherent(bucket_profile, position, 3)
        if rejection is not None:
            return position, rejection
        if _profile_reference(bucket_profile) != _profile_reference(selected_profile):
            return position, _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
            )
        position += 1

    bucket_entries: list[_AvailabilityEntry] = []
    for occurrence_position in range(bucket_count):
        position, occurrence, rejection = _parse_availability_record(
            records,
            position,
            "blocker_availability",
            (("target", target_position), ("blocker", blocker_position)),
            occurrence_position,
            blocker_record_position,
        )
        if rejection is not None or occurrence is None:
            return position, rejection
        if bucket_profile is None or occurrence.profile != bucket_profile:
            return position, _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                position - 1,
            )
        bucket_entries.append(occurrence)

    expected_bucket = tuple(
        occurrence
        for occurrence in availability
        if _profile_reference(occurrence.profile)
        == _profile_reference(selected_profile)
    )
    if tuple(map(_availability_authority, bucket_entries)) != tuple(
        map(_availability_authority, expected_bucket)
    ):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            blocker_record_position,
        )

    if blocker_kind == "profile_not_declared_available":
        coherent = not has_bucket and bucket_profile is None and bucket_count == 0
    else:
        coherent = has_bucket and bucket_profile is not None and bucket_count > 0
    if not coherent:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            blocker_record_position,
        )
    return position, None


def _parse_target(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    target_position: int,
    declaration: str,
) -> tuple[int, _TargetLedger | None, CapabilityPureOutcome | None]:
    target, rejection = _expect(records, position, "target", 0)
    if rejection is not None or target is None:
        return position, None, rejection
    target_record_position = position
    if _integer_value(target, "target") != target_position:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                0,
            ),
        )
    variant = _text_value(target, "variant")
    supplied_count = _integer_value(target, "supplied_overlays")
    dependency_count = _integer_value(target, "dependency_profiles")
    availability_count = _integer_value(target, "availability")
    blocker_count = _integer_value(target, "blockers")
    if dependency_count == 0:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                position,
                3,
            ),
        )
    position += 1

    position, base, rejection = _parse_profile_record(
        records,
        position,
        target_position,
        "base",
        0,
        target_record_position,
    )
    if rejection is not None or base is None:
        return position, None, rejection
    if base[4] != "base":
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                position - 1,
                7,
            ),
        )

    supplied: list[_Profile] = []
    for profile_position in range(supplied_count):
        position, profile, rejection = _parse_profile_record(
            records,
            position,
            target_position,
            "supplied_overlay",
            profile_position,
            target_record_position,
        )
        if rejection is not None or profile is None:
            return position, None, rejection
        if profile[4] != "overlay":
            return (
                position,
                None,
                _reject(
                    CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                    position - 1,
                    7,
                ),
            )
        supplied.append(profile)

    dependency_profiles: list[_Profile] = []
    for profile_position in range(dependency_count):
        position, profile, rejection = _parse_profile_record(
            records,
            position,
            target_position,
            "dependency",
            profile_position,
            target_record_position,
        )
        if rejection is not None or profile is None:
            return position, None, rejection
        dependency_profiles.append(profile)
    if dependency_profiles[0] != base or dependency_profiles[0][4] != "base":
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                target_record_position,
            ),
        )
    dependency_overlays = dependency_profiles[1:]
    if len(dependency_overlays) != len(supplied) or any(
        sum(candidate == profile for candidate in dependency_overlays) != 1
        for profile in supplied
    ):
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                target_record_position,
            ),
        )

    availability_entries: list[_AvailabilityEntry] = []
    next_owner_position = {"compiler": 0, "project": 0}
    seen_project = False
    project_path: str | None = None
    for occurrence_position in range(availability_count):
        position, availability_entry, rejection = _parse_availability_record(
            records,
            position,
            "availability",
            (("target", target_position),),
            occurrence_position,
            target_record_position,
        )
        if rejection is not None or availability_entry is None:
            return position, None, rejection
        if availability_entry.owner_kind == "compiler":
            if seen_project:
                return (
                    position,
                    None,
                    _reject(
                        CapabilityPureStatus.SECTION_ORDER_VIOLATION,
                        availability_entry.record_position,
                        2,
                    ),
                )
        else:
            seen_project = True
            if project_path is None:
                project_path = availability_entry.project_path
            elif availability_entry.project_path != project_path:
                return (
                    position,
                    None,
                    _reject(
                        CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                        availability_entry.record_position,
                        4,
                    ),
                )
        expected_position = next_owner_position[availability_entry.owner_kind]
        if availability_entry.owner_position != expected_position:
            return (
                position,
                None,
                _reject(
                    CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
                    availability_entry.record_position,
                    3,
                ),
            )
        next_owner_position[availability_entry.owner_kind] += 1
        availability_entries.append(availability_entry)

    frozen_dependencies = tuple(dependency_profiles)
    frozen_availability = tuple(availability_entries)
    for blocker_position in range(blocker_count):
        position, rejection = _parse_blocker(
            records,
            position,
            target_position,
            blocker_position,
            frozen_dependencies,
            frozen_availability,
            target_record_position,
        )
        if rejection is not None:
            return position, None, rejection

    if declaration == "undeclared":
        coherent = variant == "undeclared" and blocker_count == 0
    elif variant == "blocked":
        coherent = blocker_count > 0
    else:
        coherent = (
            variant == "checked"
            and blocker_count == 0
            and all(
                any(available.profile == profile for available in availability_entries)
                for profile in dependency_profiles
            )
        )
    if not coherent:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
                target_record_position,
            ),
        )
    return position, _TargetLedger(variant, frozen_dependencies), None


def _parse_operands(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    kind: str,
    scope: tuple[tuple[str, int], ...],
    count: int,
    parent_position: int,
) -> tuple[int, tuple[str, ...] | None, CapabilityPureOutcome | None]:
    operands: list[str] = []
    for operand_position in range(count):
        operand, rejection = _expect(
            records,
            position,
            kind,
            parent_position,
            child=True,
        )
        if rejection is not None or operand is None:
            return position, None, rejection
        if not _scope_matches(operand, scope):
            return (
                position,
                None,
                _reject(
                    CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
                    position,
                ),
            )
        if _integer_value(operand, "operand") != operand_position:
            return (
                position,
                None,
                _reject(
                    CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
                    position,
                    len(scope),
                ),
            )
        operands.append(_text_value(operand, "value"))
        position += 1
    return position, tuple(operands), None


def _key_header(
    record: CapabilityPureRecord,
    offset: int,
) -> tuple[str, str | None, str | None, int, str | None, str | None, str | None]:
    fields = record.fields[offset : offset + len(_KEY_FIELDS)]
    return (
        fields[0].value.text or "",
        None
        if fields[1].value.tag is CapabilityPureTag.ABSENT
        else fields[1].value.text,
        None
        if fields[2].value.tag is CapabilityPureTag.ABSENT
        else fields[2].value.text,
        fields[3].value.integer or 0,
        None
        if fields[4].value.tag is CapabilityPureTag.ABSENT
        else fields[4].value.text,
        None
        if fields[5].value.tag is CapabilityPureTag.ABSENT
        else fields[5].value.text,
        None
        if fields[6].value.tag is CapabilityPureTag.ABSENT
        else fields[6].value.text,
    )


def _parse_key(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    record: CapabilityPureRecord,
    offset: int,
    operand_kind: str,
    scope: tuple[tuple[str, int], ...],
    parent_position: int,
) -> tuple[int, _Key | None, CapabilityPureOutcome | None]:
    domain, subject, operation, operand_count, context, dialect, extension = (
        _key_header(record, offset)
    )
    if subject is None and operation is None:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                parent_position,
                offset + 1,
            ),
        )
    if extension is not None and dialect is None:
        return (
            position,
            None,
            _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                parent_position,
                offset + 6,
            ),
        )
    position, operands, rejection = _parse_operands(
        records,
        position,
        operand_kind,
        scope,
        operand_count,
        parent_position,
    )
    if rejection is not None or operands is None:
        return position, None, rejection
    return (
        position,
        (domain, subject, operation, operands, context, dialect, extension),
        None,
    )


def _parse_evidence(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    kind: str,
    scope: tuple[tuple[str, int], ...],
    evidence_position: int,
    parent_position: int,
) -> tuple[int, CapabilityPureOutcome | None]:
    evidence, rejection = _expect(
        records,
        position,
        kind,
        parent_position,
        child=True,
    )
    if rejection is not None or evidence is None:
        return position, rejection
    if not _scope_matches(evidence, scope):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    if _integer_value(evidence, "evidence") != evidence_position:
        return position, _reject(
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            len(scope),
        )
    dialect = _optional_text_value(evidence, "dialect")
    extension = _optional_text_value(evidence, "extension")
    if extension is not None and dialect is None:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            position,
        )
    return position + 1, None


def _parse_fact(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    fact_kind: str,
    operand_kind: str,
    evidence_kind: str,
    scope: tuple[tuple[str, int], ...],
    expected_key: _Key,
    parent_position: int,
) -> tuple[int, CapabilityPureOutcome | None]:
    fact, rejection = _expect(
        records,
        position,
        fact_kind,
        parent_position,
        child=True,
    )
    if rejection is not None or fact is None:
        return position, rejection
    fact_record_position = position
    if not _scope_matches(fact, scope):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    key_offset = len(scope)
    position, key, rejection = _parse_key(
        records,
        position + 1,
        fact,
        key_offset,
        operand_kind,
        scope,
        fact_record_position,
    )
    if rejection is not None or key is None:
        return position, rejection
    if key != expected_key:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            fact_record_position,
        )
    disposition = _text_value(fact, "disposition")
    owner = _optional_text_value(fact, "disposition_owner")
    reason = _optional_text_value(fact, "disposition_reason")
    if disposition == "none":
        coherent = owner is None and reason is None
    else:
        coherent = owner is not None and reason is not None
    if not coherent:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            fact_record_position,
        )
    evidence_count = _integer_value(fact, "evidence")
    if evidence_count == 0:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            fact_record_position,
        )
    for evidence_position in range(evidence_count):
        position, rejection = _parse_evidence(
            records,
            position,
            evidence_kind,
            scope,
            evidence_position,
            fact_record_position,
        )
        if rejection is not None:
            return position, rejection
    return position, None


def _lookup_posture(
    variant: str,
    reason: str | None,
    fact_count: int,
    record_position: int,
) -> CapabilityPureOutcome | None:
    if variant == "found":
        coherent = reason is None and fact_count == 1
    elif variant == "absent":
        coherent = reason == "no_catalog_entry" and fact_count == 0
    elif variant == "unknown":
        coherent = (
            reason is not None
            and reason not in {"no_catalog_entry", "conflicting_evidence"}
            and fact_count == 0
        )
    else:
        coherent = reason == "conflicting_evidence" and fact_count >= 2
    return (
        None
        if coherent
        else _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            record_position,
        )
    )


def _is_absent(record: CapabilityPureRecord, key: str) -> bool:
    return _value(record, key).tag is CapabilityPureTag.ABSENT


def _parse_target_occurrence(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    requirement_position: int,
    target_position: int,
    occurrence_position: int,
    target: _TargetLedger,
    requirement_key: _Key,
    parent_position: int,
) -> tuple[int, CapabilityPureOutcome | None]:
    occurrence, rejection = _expect(
        records,
        position,
        "target_occurrence",
        parent_position,
        child=True,
    )
    if rejection is not None or occurrence is None:
        return position, rejection
    occurrence_record_position = position
    scope = (("requirement", requirement_position), ("target", target_position))
    if not _scope_matches(occurrence, scope):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    if _integer_value(occurrence, "occurrence") != occurrence_position:
        return position, _reject(
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            2,
        )
    profile_position = _integer_value(occurrence, "profile")
    if profile_position >= len(target.dependency_profiles):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
            3,
        )
    profile = target.dependency_profiles[profile_position]
    if (
        _text_value(occurrence, "profile_namespace"),
        _text_value(occurrence, "profile_name"),
        _text_value(occurrence, "profile_release"),
    ) != _profile_reference(profile):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    fact_scope = (
        ("requirement", requirement_position),
        ("target", target_position),
        ("occurrence", occurrence_position),
    )
    return _parse_fact(
        records,
        position + 1,
        "target_fact",
        "target_fact_operand",
        "target_fact_evidence",
        fact_scope,
        requirement_key,
        occurrence_record_position,
    )


def _parse_cell(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    requirement_position: int,
    target_position: int,
    target: _TargetLedger,
    requirement_key: _Key,
    parent_position: int,
) -> tuple[int, CapabilityPureOutcome | None]:
    cell, rejection = _expect(
        records,
        position,
        "cell",
        parent_position,
        child=True,
    )
    if rejection is not None or cell is None:
        return position, rejection
    cell_record_position = position
    if not _scope_matches(
        cell,
        (("requirement", requirement_position), ("target", target_position)),
    ):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_SCOPE_RELATION,
            position,
        )
    has_check = _boolean_value(cell, "has_check")
    target_occurrence_count = _integer_value(cell, "target_occurrences")
    target_fact_count = _integer_value(cell, "target_lookup_facts")
    provider_fact_count = _integer_value(cell, "provider_lookup_facts")
    if target.variant == "blocked":
        expected_check = False
    elif target.variant == "checked":
        expected_check = True
    else:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
            position,
        )
    if has_check is not expected_check:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            position,
            2,
        )
    if not has_check:
        optional_fields = (
            "status",
            "target_lookup",
            "target_reason",
            "provider_domain_complete",
            "provider_unknown_reason",
            "provider_lookup",
            "provider_reason",
        )
        if (
            target_occurrence_count
            or target_fact_count
            or provider_fact_count
            or any(not _is_absent(cell, key) for key in optional_fields)
        ):
            return position, _reject(
                CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
                position,
            )
        return position + 1, None

    required_fields = (
        "status",
        "target_lookup",
        "provider_domain_complete",
        "provider_lookup",
    )
    if any(_is_absent(cell, key) for key in required_fields):
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            position,
        )
    target_lookup = _text_value(cell, "target_lookup")
    target_reason = _optional_text_value(cell, "target_reason")
    rejection = _lookup_posture(
        target_lookup,
        target_reason,
        target_fact_count,
        position,
    )
    if rejection is not None:
        return position, rejection
    if target_fact_count != target_occurrence_count:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            position,
        )
    position += 1
    for occurrence_position in range(target_occurrence_count):
        position, rejection = _parse_target_occurrence(
            records,
            position,
            requirement_position,
            target_position,
            occurrence_position,
            target,
            requirement_key,
            cell_record_position,
        )
        if rejection is not None:
            return position, rejection

    provider_lookup = _text_value(cell, "provider_lookup")
    provider_reason = _optional_text_value(cell, "provider_reason")
    rejection = _lookup_posture(
        provider_lookup,
        provider_reason,
        provider_fact_count,
        cell_record_position,
    )
    if rejection is not None:
        return position, rejection
    domain_complete = _optional_boolean_value(cell, "provider_domain_complete")
    assert domain_complete is not None
    unknown_reason = _optional_text_value(cell, "provider_unknown_reason")
    if unknown_reason in {"no_catalog_entry", "conflicting_evidence"}:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            cell_record_position,
        )
    if domain_complete:
        coherent = unknown_reason is None and provider_lookup != "unknown"
    else:
        coherent = provider_lookup != "absent"
    if provider_lookup == "unknown":
        coherent = coherent and provider_reason == (
            "not_evidenced" if unknown_reason is None else unknown_reason
        )
    if not coherent:
        return position, _reject(
            CapabilityPureStatus.INCONSISTENT_RECORD_STATE,
            cell_record_position,
        )
    for fact_position in range(provider_fact_count):
        fact_scope = (
            ("requirement", requirement_position),
            ("target", target_position),
            ("fact", fact_position),
        )
        position, rejection = _parse_fact(
            records,
            position,
            "provider_fact",
            "provider_fact_operand",
            "provider_fact_evidence",
            fact_scope,
            requirement_key,
            cell_record_position,
        )
        if rejection is not None:
            return position, rejection
    return position, None


def _parse_requirement(
    records: tuple[CapabilityPureRecord, ...],
    position: int,
    requirement_position: int,
    targets: tuple[_TargetLedger, ...],
) -> tuple[int, CapabilityPureOutcome | None]:
    requirement, rejection = _expect(records, position, "requirement", 0)
    if rejection is not None or requirement is None:
        return position, rejection
    requirement_record_position = position
    if _integer_value(requirement, "requirement") != requirement_position:
        return position, _reject(
            CapabilityPureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            0,
        )
    position, key, rejection = _parse_key(
        records,
        position + 1,
        requirement,
        1,
        "requirement_operand",
        (("requirement", requirement_position),),
        requirement_record_position,
    )
    if rejection is not None or key is None:
        return position, rejection
    for target_position, target in enumerate(targets):
        position, rejection = _parse_cell(
            records,
            position,
            requirement_position,
            target_position,
            target,
            key,
            requirement_record_position,
        )
        if rejection is not None:
            return position, rejection
    return position, None


def evaluate_capability_document(
    document: CapabilityPureDocument,
) -> CapabilityPureOutcome:
    """Evaluate one immutable capability document without ambient state."""

    if type(document) is not CapabilityPureDocument:
        raise TypeError("Capability pure evaluation requires an exact document")
    records = document.records
    if not records:
        return _reject(CapabilityPureStatus.EMPTY_DOCUMENT)
    if records[0].kind != "inspection":
        return _reject(CapabilityPureStatus.MISSING_HEADER_RECORD, 0)
    header_rejection = _validate_fields(records[0], 0)
    if header_rejection is not None:
        return header_rejection
    header = records[0]
    if _text_value(header, "format") != CAPABILITY_PURE_FORMAT_MARKER:
        return _reject(CapabilityPureStatus.UNKNOWN_FORMAT_MARKER, 0, 0)
    declaration = _text_value(header, "declaration")
    target_count = _integer_value(header, "targets")
    requirement_count = _integer_value(header, "requirements")
    if target_count == 0 or (declaration == "undeclared" and requirement_count != 0):
        return _reject(CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE, 0)

    position = 1
    package, rejection = _expect(records, position, "package", 0)
    if rejection is not None or package is None:
        return rejection or _reject(CapabilityPureStatus.MISSING_REQUIRED_RECORD, 0)
    position += 1

    if declaration == "declared":
        requirements, rejection = _expect(records, position, "requirements", 0)
        if rejection is not None or requirements is None:
            return rejection or _reject(CapabilityPureStatus.MISSING_REQUIRED_RECORD, 0)
        if _integer_value(requirements, "count") != requirement_count:
            return _reject(
                CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE,
                position,
                2,
            )
        position += 1
    elif position < len(records) and records[position].kind == "requirements":
        return _reject(CapabilityPureStatus.INCONSISTENT_DOCUMENT_STATE, position)

    targets: list[_TargetLedger] = []
    for target_position in range(target_count):
        position, target, rejection = _parse_target(
            records,
            position,
            target_position,
            declaration,
        )
        if rejection is not None or target is None:
            return rejection or _reject(CapabilityPureStatus.MISSING_REQUIRED_RECORD, 0)
        targets.append(target)

    frozen_targets = tuple(targets)
    for requirement_position in range(requirement_count):
        position, rejection = _parse_requirement(
            records,
            position,
            requirement_position,
            frozen_targets,
        )
        if rejection is not None:
            return rejection

    if position < len(records):
        trailing = records[position]
        if trailing.kind not in _SCHEMA:
            return _reject(CapabilityPureStatus.UNKNOWN_RECORD_KIND, position)
        if trailing.kind in {"inspection", "package", "requirements"}:
            return _reject(CapabilityPureStatus.DUPLICATE_SINGLETON_RECORD, position)
        return _reject(CapabilityPureStatus.TRAILING_RECORD_AFTER_DOCUMENT, position)
    return CapabilityPureOutcome(
        status=CapabilityPureStatus.OK,
        canonical_bytes=_encode_document(document),
    )


def _escape_text(value: str) -> str:
    escaped: list[str] = []
    for character in value:
        replacement = _ESCAPES.get(character)
        if replacement is not None:
            escaped.append(replacement)
        elif character < " " or character == "\x7f":
            escaped.append(f"\\x{ord(character):02x}")
        elif "\ud800" <= character <= "\udfff":
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def encode_capability_pure_value(value: CapabilityPureValue) -> str:
    if value.tag is CapabilityPureTag.ABSENT:
        if (
            value.text is not None
            or value.integer is not None
            or value.boolean is not None
        ):
            raise ValueError("Absent capability values carry no payload")
        return "n:"
    if value.tag in {CapabilityPureTag.TEXT, CapabilityPureTag.ENUMERATION}:
        if value.text is None:
            raise ValueError("Capability text values require their payload")
        prefix = "s" if value.tag is CapabilityPureTag.TEXT else "e"
        return f"{prefix}:{_escape_text(value.text)}"
    if value.tag is CapabilityPureTag.INTEGER:
        if value.integer is None or value.integer < 0:
            raise ValueError("Capability integer values require non-negative payloads")
        return f"i:{value.integer}"
    if value.boolean is None:
        raise ValueError("Capability boolean values require their payload")
    return "b:true" if value.boolean else "b:false"


def _encode_document(document: CapabilityPureDocument) -> bytes:
    lines = [
        record.kind
        + "".join(
            f"\t{field.key}={encode_capability_pure_value(field.value)}"
            for field in record.fields
        )
        for record in document.records
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")
