"""Private total pure boundary for canonical package inspection records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

__all__: tuple[str, ...] = ()

PACKAGE_PURE_FORMAT_MARKER = "pietto.package-inspection.v1"
PACKAGE_PURE_MAX_INTEGER = 2**63 - 1

_HEX = frozenset("0123456789abcdef")
_ESCAPES: Mapping[str, str] = MappingProxyType(
    {"\\": "\\\\", "\t": "\\t", "\n": "\\n", "\r": "\\r"}
)


class PackagePureTag(StrEnum):
    TEXT = "s"
    INTEGER = "i"
    ENUMERATION = "e"
    ABSENT = "n"


class PackagePureStatus(StrEnum):
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
    INVALID_SHA256 = "invalid_sha256"
    MISSING_REQUIRED_RECORD = "missing_required_record"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    ORDINAL_SEQUENCE_VIOLATION = "ordinal_sequence_violation"
    CHILD_COUNT_MISMATCH = "child_count_mismatch"
    TRAILING_RECORD_AFTER_DOCUMENT = "trailing_record_after_document"
    INCONSISTENT_DOCUMENT_STATE = "inconsistent_document_state"
    INCONSISTENT_RECORD_STATE = "inconsistent_record_state"
    INCONSISTENT_SCOPE_RELATION = "inconsistent_scope_relation"


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePureValue:
    tag: PackagePureTag
    text: str | None = None
    integer: int | None = None

    def __post_init__(self) -> None:
        if type(self.tag) is not PackagePureTag:
            raise TypeError("Package portable values require an exact tag.")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Package portable text must be exact text.")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Package portable integers must be exact integers.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePureField:
    key: str
    value: PackagePureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str:
            raise TypeError("Package portable field keys must be exact text.")
        if type(self.value) is not PackagePureValue:
            raise TypeError("Package portable fields require exact values.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePureRecord:
    kind: str
    fields: tuple[PackagePureField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not str:
            raise TypeError("Package portable record kinds must be exact text.")
        if type(self.fields) is not tuple or any(
            type(field) is not PackagePureField for field in self.fields
        ):
            raise TypeError("Package portable records require exact field tuples.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePureDocument:
    records: tuple[PackagePureRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not PackagePureRecord for record in self.records
        ):
            raise TypeError("Package portable documents require exact record tuples.")


@dataclass(frozen=True, slots=True, kw_only=True)
class PackagePureOutcome:
    status: PackagePureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not PackagePureStatus:
            raise TypeError("Package portable outcomes require an exact status.")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Package portable payloads must be exact bytes.")
        for coordinate in (self.record_position, self.field_position):
            if coordinate is not None and type(coordinate) is not int:
                raise TypeError("Package portable coordinates must be integers.")
        if self.status is PackagePureStatus.OK:
            if self.canonical_bytes is None:
                raise ValueError("Accepted package outcomes require canonical bytes.")
            if self.record_position is not None or self.field_position is not None:
                raise ValueError("Accepted package outcomes carry no coordinates.")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected package outcomes carry no canonical bytes.")
        elif self.field_position is not None and self.record_position is None:
            raise ValueError("A field coordinate requires a record coordinate.")


PACKAGE_PURE_ABSENT = PackagePureValue(tag=PackagePureTag.ABSENT)


def package_pure_text(value: str) -> PackagePureValue:
    return PackagePureValue(tag=PackagePureTag.TEXT, text=value)


def package_pure_integer(value: int) -> PackagePureValue:
    return PackagePureValue(tag=PackagePureTag.INTEGER, integer=value)


def package_pure_enumeration(value: str) -> PackagePureValue:
    return PackagePureValue(tag=PackagePureTag.ENUMERATION, text=value)


@dataclass(frozen=True, slots=True)
class _KeySpec:
    key: str
    tag: PackagePureTag
    optional: bool = False
    vocabulary: tuple[str, ...] | None = None
    non_empty: bool = False
    sha256: bool = False


def _key(
    key: str,
    tag: PackagePureTag,
    *,
    optional: bool = False,
    vocabulary: tuple[str, ...] | None = None,
    non_empty: bool = False,
    sha256: bool = False,
) -> _KeySpec:
    return _KeySpec(key, tag, optional, vocabulary, non_empty, sha256)


_TEXT = PackagePureTag.TEXT
_INTEGER = PackagePureTag.INTEGER
_ENUMERATION = PackagePureTag.ENUMERATION

_OUTCOMES = ("success", "rejected", "error")
_PACKAGE_ROLES = ("dependency", "root")
_ASSET_KINDS = ("module_source",)
_LOCATOR_KINDS = ("local_directory",)
_ERROR_KINDS = (
    "project_root",
    "config_read",
    "config_parse",
    "config_schema",
    "project_path",
    "project_glob",
    "project_resource",
    "source_read",
)
_SEVERITIES = ("error", "warning")
_REJECTION_KINDS = ("cycle", "conflict", "diamond")
_CONFLICT_REASONS = (
    "identity_different_physical_root",
    "physical_root_incompatible_coordinate",
    "incompatible_content_digest_pin",
    "incompatible_occurrences",
)
_ALLOWED_CONFLICT_REASON_TUPLES = frozenset(
    {
        ("identity_different_physical_root",),
        (
            "identity_different_physical_root",
            "incompatible_content_digest_pin",
        ),
        ("physical_root_incompatible_coordinate",),
        (
            "physical_root_incompatible_coordinate",
            "incompatible_content_digest_pin",
        ),
        ("incompatible_content_digest_pin",),
        ("incompatible_occurrences",),
    }
)

_SCHEMA: Mapping[str, tuple[_KeySpec, ...]] = MappingProxyType(
    {
        "inspection": (
            _key("format", _ENUMERATION),
            _key("outcome", _ENUMERATION, vocabulary=_OUTCOMES),
            _key("packages", _INTEGER),
            _key("errors", _INTEGER),
            _key("diagnostics", _INTEGER),
            _key("rejections", _INTEGER),
        ),
        "root": (
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("version", _TEXT, non_empty=True),
        ),
        "package": (
            _key("package", _INTEGER),
            _key("role", _ENUMERATION, vocabulary=_PACKAGE_ROLES),
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("version", _TEXT, non_empty=True),
            _key("project_path", _TEXT, non_empty=True),
            _key("content_digest", _TEXT, sha256=True),
            _key("assets", _INTEGER),
            _key("dependencies", _INTEGER),
        ),
        "asset": (
            _key("package", _INTEGER),
            _key("asset", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary=_ASSET_KINDS),
            _key("path", _TEXT, non_empty=True),
        ),
        "dependency": (
            _key("package", _INTEGER),
            _key("dependency", _INTEGER),
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("version", _TEXT, non_empty=True),
            _key("content_digest_pin", _TEXT, sha256=True),
            _key("locator_kind", _ENUMERATION, vocabulary=_LOCATOR_KINDS),
            _key("authored_path", _TEXT, non_empty=True),
            _key("resolved_project_path", _TEXT, non_empty=True),
            _key("target_package", _INTEGER),
        ),
        "error": (
            _key("error", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary=_ERROR_KINDS),
            _key("message", _TEXT),
            _key("path", _TEXT, optional=True),
        ),
        "diagnostic": (
            _key("diagnostic", _INTEGER),
            _key("code", _TEXT),
            _key("severity", _ENUMERATION, vocabulary=_SEVERITIES),
            _key("message", _TEXT),
            _key("path", _TEXT, optional=True),
            _key("line", _INTEGER),
            _key("column", _INTEGER),
            _key("end_line", _INTEGER, optional=True),
            _key("end_column", _INTEGER, optional=True),
            _key("suggestion", _TEXT, optional=True),
        ),
        "rejection": (
            _key("rejection", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary=_REJECTION_KINDS),
            _key("conflict_reasons", _INTEGER),
            _key("occurrences", _INTEGER),
            _key("message", _TEXT, non_empty=True),
        ),
        "rejection_reason": (
            _key("rejection", _INTEGER),
            _key("reason", _INTEGER),
            _key("value", _ENUMERATION, vocabulary=_CONFLICT_REASONS),
        ),
        "rejection_occurrence": (
            _key("rejection", _INTEGER),
            _key("occurrence", _INTEGER),
            _key("dependency_position", _INTEGER),
            _key("declaring_namespace", _TEXT, non_empty=True),
            _key("declaring_name", _TEXT, non_empty=True),
            _key("declaring_version", _TEXT, non_empty=True),
            _key("declaring_project_path", _TEXT, non_empty=True),
            _key("declaring_content_digest", _TEXT, sha256=True),
            _key("namespace", _TEXT, non_empty=True),
            _key("name", _TEXT, non_empty=True),
            _key("version", _TEXT, non_empty=True),
            _key("content_digest_pin", _TEXT, sha256=True),
            _key("locator_kind", _ENUMERATION, vocabulary=_LOCATOR_KINDS),
            _key("authored_path", _TEXT, non_empty=True),
            _key("resolved_project_path", _TEXT, non_empty=True),
        ),
    }
)

PACKAGE_PURE_RECORD_KINDS: tuple[str, ...] = tuple(_SCHEMA)

_Coordinate = tuple[str, str, str]
_PackageLedger = tuple[_Coordinate, str]
_Occurrence = tuple[_Coordinate, str, str, _Coordinate, str, str, int]


def _reject(
    status: PackagePureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> PackagePureOutcome:
    return PackagePureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _validate_value(
    value: PackagePureValue,
    declared: _KeySpec,
    record_position: int,
    field_position: int,
) -> PackagePureOutcome | None:
    if value.tag is PackagePureTag.ABSENT:
        if not declared.optional:
            return _reject(
                PackagePureStatus.ABSENT_VALUE_NOT_ALLOWED,
                record_position,
                field_position,
            )
        if value.text is not None or value.integer is not None:
            return _reject(
                PackagePureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        return None
    if value.tag is not declared.tag:
        return _reject(
            PackagePureStatus.VALUE_TAG_MISMATCH,
            record_position,
            field_position,
        )
    if value.tag in {PackagePureTag.TEXT, PackagePureTag.ENUMERATION}:
        if value.text is None:
            return _reject(
                PackagePureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if value.integer is not None:
            return _reject(
                PackagePureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if declared.non_empty and not value.text:
            return _reject(
                PackagePureStatus.INCONSISTENT_RECORD_STATE,
                record_position,
                field_position,
            )
        if declared.vocabulary is not None and value.text not in declared.vocabulary:
            return _reject(
                PackagePureStatus.UNKNOWN_ENUMERATION,
                record_position,
                field_position,
            )
        if declared.sha256 and (
            len(value.text) != 64
            or any(character not in _HEX for character in value.text)
        ):
            return _reject(
                PackagePureStatus.INVALID_SHA256,
                record_position,
                field_position,
            )
        return None
    if value.integer is None:
        return _reject(
            PackagePureStatus.MISSING_VALUE_PAYLOAD,
            record_position,
            field_position,
        )
    if value.text is not None:
        return _reject(
            PackagePureStatus.EXTRA_VALUE_PAYLOAD,
            record_position,
            field_position,
        )
    if value.integer < 0:
        return _reject(
            PackagePureStatus.NEGATIVE_INTEGER,
            record_position,
            field_position,
        )
    if value.integer > PACKAGE_PURE_MAX_INTEGER:
        return _reject(
            PackagePureStatus.INTEGER_OUT_OF_RANGE,
            record_position,
            field_position,
        )
    return None


def _validate_fields(
    record: PackagePureRecord,
    record_position: int,
) -> PackagePureOutcome | None:
    specification = _SCHEMA[record.kind]
    if len(record.fields) != len(specification):
        return _reject(PackagePureStatus.FIELD_ARITY_MISMATCH, record_position)
    for field_position, (field, declared) in enumerate(
        zip(record.fields, specification, strict=True)
    ):
        if field.key != declared.key:
            return _reject(
                PackagePureStatus.FIELD_KEY_MISMATCH,
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
    records: tuple[PackagePureRecord, ...],
    position: int,
    kind: str,
    parent_position: int,
    *,
    child: bool = False,
) -> tuple[PackagePureRecord | None, PackagePureOutcome | None]:
    if position >= len(records):
        return None, _reject(
            PackagePureStatus.CHILD_COUNT_MISMATCH
            if child
            else PackagePureStatus.MISSING_REQUIRED_RECORD,
            parent_position,
        )
    record = records[position]
    if record.kind not in _SCHEMA:
        return None, _reject(PackagePureStatus.UNKNOWN_RECORD_KIND, position)
    if record.kind != kind:
        if record.kind in {"inspection", "root"}:
            return None, _reject(
                PackagePureStatus.DUPLICATE_SINGLETON_RECORD,
                position,
            )
        return None, _reject(
            PackagePureStatus.CHILD_COUNT_MISMATCH
            if child
            else PackagePureStatus.SECTION_ORDER_VIOLATION,
            parent_position if child else position,
        )
    rejection = _validate_fields(record, position)
    return record, rejection


def _value(record: PackagePureRecord, key: str) -> PackagePureValue:
    for field in record.fields:
        if field.key == key:
            return field.value
    raise ValueError("A validated package record always carries its declared key.")


def _text_value(record: PackagePureRecord, key: str) -> str:
    value = _value(record, key).text
    if value is None:
        raise ValueError("A validated package text value cannot be absent.")
    return value


def _integer_value(record: PackagePureRecord, key: str) -> int:
    value = _value(record, key).integer
    if value is None:
        raise ValueError("A validated package integer cannot be absent.")
    return value


def _coordinate(record: PackagePureRecord, prefix: str = "") -> _Coordinate:
    return (
        _text_value(record, f"{prefix}namespace"),
        _text_value(record, f"{prefix}name"),
        _text_value(record, f"{prefix}version"),
    )


def _parse_package(
    records: tuple[PackagePureRecord, ...],
    position: int,
    package_position: int,
    package_count: int,
    ledger: list[_PackageLedger],
) -> tuple[int, PackagePureOutcome | None]:
    package, rejection = _expect(records, position, "package", 0)
    if rejection is not None or package is None:
        return position, rejection
    package_record_position = position
    if _integer_value(package, "package") != package_position:
        return position, _reject(
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            0,
        )
    expected_role = "root" if package_position == package_count - 1 else "dependency"
    if _text_value(package, "role") != expected_role:
        return position, _reject(
            PackagePureStatus.INCONSISTENT_RECORD_STATE,
            position,
            1,
        )
    asset_count = _integer_value(package, "assets")
    dependency_count = _integer_value(package, "dependencies")
    if asset_count == 0:
        return position, _reject(
            PackagePureStatus.INCONSISTENT_RECORD_STATE,
            position,
            7,
        )
    position += 1
    for asset_position in range(asset_count):
        asset, rejection = _expect(
            records,
            position,
            "asset",
            package_record_position,
            child=True,
        )
        if rejection is not None or asset is None:
            return position, rejection
        if _integer_value(asset, "package") != package_position:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                0,
            )
        if _integer_value(asset, "asset") != asset_position:
            return position, _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                1,
            )
        position += 1

    for dependency_position in range(dependency_count):
        dependency, rejection = _expect(
            records,
            position,
            "dependency",
            package_record_position,
            child=True,
        )
        if rejection is not None or dependency is None:
            return position, rejection
        if _integer_value(dependency, "package") != package_position:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                0,
            )
        if _integer_value(dependency, "dependency") != dependency_position:
            return position, _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                1,
            )
        target = _integer_value(dependency, "target_package")
        if target >= package_position or target >= len(ledger):
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                9,
            )
        target_coordinate, target_digest = ledger[target]
        if _coordinate(dependency) != target_coordinate or (
            _text_value(dependency, "content_digest_pin") != target_digest
        ):
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
            )
        position += 1

    ledger.append((_coordinate(package), _text_value(package, "content_digest")))
    return position, None


def _parse_rejection(
    records: tuple[PackagePureRecord, ...],
    position: int,
    rejection_position: int,
) -> tuple[int, PackagePureOutcome | None]:
    projected, rejection = _expect(records, position, "rejection", 0)
    if rejection is not None or projected is None:
        return position, rejection
    rejection_record_position = position
    if _integer_value(projected, "rejection") != rejection_position:
        return position, _reject(
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            position,
            0,
        )
    kind = _text_value(projected, "kind")
    reason_count = _integer_value(projected, "conflict_reasons")
    occurrence_count = _integer_value(projected, "occurrences")
    position += 1
    reasons: list[str] = []
    for reason_position in range(reason_count):
        reason, rejection = _expect(
            records,
            position,
            "rejection_reason",
            rejection_record_position,
            child=True,
        )
        if rejection is not None or reason is None:
            return position, rejection
        if _integer_value(reason, "rejection") != rejection_position:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                0,
            )
        if _integer_value(reason, "reason") != reason_position:
            return position, _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                1,
            )
        reasons.append(_text_value(reason, "value"))
        position += 1

    occurrences: list[_Occurrence] = []
    for occurrence_position in range(occurrence_count):
        occurrence, rejection = _expect(
            records,
            position,
            "rejection_occurrence",
            rejection_record_position,
            child=True,
        )
        if rejection is not None or occurrence is None:
            return position, rejection
        if _integer_value(occurrence, "rejection") != rejection_position:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                position,
                0,
            )
        if _integer_value(occurrence, "occurrence") != occurrence_position:
            return position, _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                1,
            )
        occurrences.append(
            (
                _coordinate(occurrence, "declaring_"),
                _text_value(occurrence, "declaring_project_path"),
                _text_value(occurrence, "declaring_content_digest"),
                _coordinate(occurrence),
                _text_value(occurrence, "content_digest_pin"),
                _text_value(occurrence, "resolved_project_path"),
                position,
            )
        )
        position += 1

    reason_tuple = tuple(reasons)
    if kind == "cycle":
        if reason_tuple or not occurrences:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_RECORD_STATE,
                rejection_record_position,
            )
        for occurrence_position, occurrence in enumerate(occurrences):
            next_occurrence = occurrences[(occurrence_position + 1) % len(occurrences)]
            if occurrence[3] != next_occurrence[0]:
                return position, _reject(
                    PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                    occurrence[6],
                )
    elif kind == "conflict":
        if reason_tuple not in _ALLOWED_CONFLICT_REASON_TUPLES or not (
            1 <= len(occurrences) <= 2
        ):
            return position, _reject(
                PackagePureStatus.INCONSISTENT_RECORD_STATE,
                rejection_record_position,
            )
    elif reason_tuple or len(occurrences) != 2:
        return position, _reject(
            PackagePureStatus.INCONSISTENT_RECORD_STATE,
            rejection_record_position,
        )
    else:
        first, second = occurrences
        if first[3:6] != second[3:6] or first[:3] == second[:3]:
            return position, _reject(
                PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
                second[6],
            )
    return position, None


def evaluate_package_document(document: PackagePureDocument) -> PackagePureOutcome:
    """Evaluate one immutable portable document without ambient state."""

    if type(document) is not PackagePureDocument:
        raise TypeError("Package pure evaluation requires an exact document.")
    records = document.records
    if not records:
        return _reject(PackagePureStatus.EMPTY_DOCUMENT)
    if records[0].kind != "inspection":
        return _reject(PackagePureStatus.MISSING_HEADER_RECORD, 0)
    header_rejection = _validate_fields(records[0], 0)
    if header_rejection is not None:
        return header_rejection
    header = records[0]
    if _text_value(header, "format") != PACKAGE_PURE_FORMAT_MARKER:
        return _reject(PackagePureStatus.UNKNOWN_FORMAT_MARKER, 0, 0)

    outcome = _text_value(header, "outcome")
    package_count = _integer_value(header, "packages")
    error_count = _integer_value(header, "errors")
    diagnostic_count = _integer_value(header, "diagnostics")
    rejection_count = _integer_value(header, "rejections")
    if (outcome == "success") is (package_count == 0):
        return _reject(PackagePureStatus.INCONSISTENT_DOCUMENT_STATE, 0)
    if outcome != "success" and package_count:
        return _reject(PackagePureStatus.INCONSISTENT_DOCUMENT_STATE, 0)

    position = 1
    root_coordinate: _Coordinate | None = None
    if outcome == "success":
        root, rejection = _expect(records, position, "root", 0)
        if rejection is not None or root is None:
            return rejection or _reject(PackagePureStatus.MISSING_REQUIRED_RECORD, 0)
        root_coordinate = _coordinate(root)
        position += 1
    elif position < len(records) and records[position].kind == "root":
        return _reject(PackagePureStatus.INCONSISTENT_DOCUMENT_STATE, position)

    ledger: list[_PackageLedger] = []
    for package_position in range(package_count):
        position, rejection = _parse_package(
            records,
            position,
            package_position,
            package_count,
            ledger,
        )
        if rejection is not None:
            return rejection
    if root_coordinate is not None and root_coordinate != ledger[-1][0]:
        return _reject(PackagePureStatus.INCONSISTENT_SCOPE_RELATION, 1)

    for error_position in range(error_count):
        error, rejection = _expect(records, position, "error", 0)
        if rejection is not None or error is None:
            return rejection or _reject(PackagePureStatus.MISSING_REQUIRED_RECORD, 0)
        if _integer_value(error, "error") != error_position:
            return _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                0,
            )
        position += 1

    has_error_diagnostic = False
    for diagnostic_position in range(diagnostic_count):
        diagnostic, rejection = _expect(records, position, "diagnostic", 0)
        if rejection is not None or diagnostic is None:
            return rejection or _reject(PackagePureStatus.MISSING_REQUIRED_RECORD, 0)
        if _integer_value(diagnostic, "diagnostic") != diagnostic_position:
            return _reject(
                PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
                position,
                0,
            )
        has_error_diagnostic |= _text_value(diagnostic, "severity") == "error"
        position += 1

    for rejection_position in range(rejection_count):
        position, rejection = _parse_rejection(
            records,
            position,
            rejection_position,
        )
        if rejection is not None:
            return rejection

    if position < len(records):
        trailing = records[position]
        if trailing.kind not in _SCHEMA:
            return _reject(PackagePureStatus.UNKNOWN_RECORD_KIND, position)
        if trailing.kind in {"inspection", "root"}:
            return _reject(PackagePureStatus.DUPLICATE_SINGLETON_RECORD, position)
        return _reject(PackagePureStatus.TRAILING_RECORD_AFTER_DOCUMENT, position)

    has_error_evidence = bool(error_count) or has_error_diagnostic
    if outcome == "success":
        consistent = not has_error_evidence and rejection_count == 0
    elif outcome == "error":
        consistent = has_error_evidence and rejection_count == 0
    else:
        consistent = (
            rejection_count > 0 and error_count == 0 and not has_error_diagnostic
        )
    if not consistent:
        return _reject(PackagePureStatus.INCONSISTENT_DOCUMENT_STATE, 0)
    return PackagePureOutcome(
        status=PackagePureStatus.OK,
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


def encode_package_pure_value(value: PackagePureValue) -> str:
    if value.tag is PackagePureTag.ABSENT:
        if value.text is not None or value.integer is not None:
            raise ValueError("Absent package values carry no payload.")
        return "n:"
    if value.tag in {PackagePureTag.TEXT, PackagePureTag.ENUMERATION}:
        if value.text is None:
            raise ValueError("Package text values require their payload.")
        prefix = "s" if value.tag is PackagePureTag.TEXT else "e"
        return f"{prefix}:{_escape_text(value.text)}"
    if value.integer is None or value.integer < 0:
        raise ValueError("Package integer values require non-negative payloads.")
    return f"i:{value.integer}"


def _encode_document(document: PackagePureDocument) -> bytes:
    lines = [
        record.kind
        + "".join(
            f"\t{field.key}={encode_package_pure_value(field.value)}"
            for field in record.fields
        )
        for record in document.records
    ]
    return ("\n".join(lines) + "\n").encode("utf-8")
