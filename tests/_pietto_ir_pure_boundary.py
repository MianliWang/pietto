"""Portable total boundary for private Project IR inspection documents."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

__all__: tuple[str, ...] = ()

PROJECT_IR_INSPECTION_FORMAT = "pietto.project-ir-inspection.v1"
PROJECT_IR_PURE_MAX_INTEGER = 2**63 - 1


class ProjectIRPortableRefDomain(StrEnum):
    PLAN_NODE = "plan_node"
    OUTPUT_VALUE = "output_value"
    INPUT_SLOT = "input_slot"
    USE = "use"


class ProjectIRPureTag(StrEnum):
    TEXT = "s"
    INTEGER = "i"
    ENUMERATION = "e"
    REF = "r"
    REFS = "q"
    TEXTS = "t"
    ENUMERATIONS = "v"
    ABSENT = "n"


class ProjectIRPureStatus(StrEnum):
    OK = "ok"
    EMPTY_DOCUMENT = "empty_document"
    MISSING_HEADER_RECORD = "missing_header_record"
    UNKNOWN_FORMAT_MARKER = "unknown_format_marker"
    UNKNOWN_RECORD_KIND = "unknown_record_kind"
    FIELD_ARITY_MISMATCH = "field_arity_mismatch"
    FIELD_KEY_MISMATCH = "field_key_mismatch"
    VALUE_TAG_MISMATCH = "value_tag_mismatch"
    MISSING_VALUE_PAYLOAD = "missing_value_payload"
    EXTRA_VALUE_PAYLOAD = "extra_value_payload"
    ABSENT_VALUE_NOT_ALLOWED = "absent_value_not_allowed"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    NEGATIVE_INTEGER = "negative_integer"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    DUPLICATE_SINGLETON_RECORD = "duplicate_singleton_record"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    NON_DENSE_REF_COORDINATES = "non_dense_ref_coordinates"
    DUPLICATE_REF = "duplicate_ref"
    DANGLING_REF = "dangling_ref"
    REF_DOMAIN_MISMATCH = "ref_domain_mismatch"
    INVALID_ENDPOINT_RELATION = "invalid_endpoint_relation"
    INVALID_FRAGMENT_STATE = "invalid_fragment_state"
    INVALID_ANALYSIS_REFERENCE = "invalid_analysis_reference"
    COUNT_MISMATCH = "count_mismatch"
    TRAILING_RECORD = "trailing_record"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPortableRef:
    domain: ProjectIRPortableRefDomain
    position: int

    def __post_init__(self) -> None:
        if type(self.domain) is not ProjectIRPortableRefDomain:
            raise TypeError("Portable Project IR refs require an exact domain.")
        if type(self.position) is not int:
            raise TypeError("Portable Project IR ref positions must be integers.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPureValue:
    tag: ProjectIRPureTag
    text: str | None = None
    integer: int | None = None
    ref: ProjectIRPortableRef | None = None
    refs: tuple[ProjectIRPortableRef, ...] | None = None
    texts: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if type(self.tag) is not ProjectIRPureTag:
            raise TypeError("Portable Project IR values require an exact tag.")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Portable Project IR text must be exact text.")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Portable Project IR integers must be exact integers.")
        if self.ref is not None and type(self.ref) is not ProjectIRPortableRef:
            raise TypeError("Portable Project IR ref values require exact refs.")
        if self.refs is not None and (
            type(self.refs) is not tuple
            or any(type(ref) is not ProjectIRPortableRef for ref in self.refs)
        ):
            raise TypeError("Portable Project IR ref lists require exact tuples.")
        if self.texts is not None and (
            type(self.texts) is not tuple
            or any(type(text) is not str for text in self.texts)
        ):
            raise TypeError("Portable Project IR text lists require exact tuples.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPureField:
    key: str
    value: ProjectIRPureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str or not self.key:
            raise ValueError("Portable Project IR field keys require text.")
        if type(self.value) is not ProjectIRPureValue:
            raise TypeError("Portable Project IR fields require exact values.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPureRecord:
    kind: str
    fields: tuple[ProjectIRPureField, ...] = ()

    def __post_init__(self) -> None:
        if type(self.kind) is not str or not self.kind:
            raise ValueError("Portable Project IR record kinds require text.")
        if type(self.fields) is not tuple or any(
            type(field) is not ProjectIRPureField for field in self.fields
        ):
            raise TypeError("Portable Project IR records require exact field tuples.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPureDocument:
    records: tuple[ProjectIRPureRecord, ...] = ()

    def __post_init__(self) -> None:
        if type(self.records) is not tuple or any(
            type(record) is not ProjectIRPureRecord for record in self.records
        ):
            raise TypeError("Portable Project IR documents require exact records.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectIRPureOutcome:
    status: ProjectIRPureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not ProjectIRPureStatus:
            raise TypeError("Project IR pure outcomes require an exact status.")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Accepted Project IR payloads must be exact bytes.")
        for coordinate in (self.record_position, self.field_position):
            if coordinate is not None and type(coordinate) is not int:
                raise TypeError("Project IR rejection coordinates must be integers.")
        if self.status is ProjectIRPureStatus.OK:
            if self.canonical_bytes is None or any(
                coordinate is not None
                for coordinate in (self.record_position, self.field_position)
            ):
                raise ValueError("Accepted Project IR outcomes carry only bytes.")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected Project IR outcomes carry no bytes.")
        elif self.field_position is not None and self.record_position is None:
            raise ValueError("A field coordinate requires a record coordinate.")


PROJECT_IR_PURE_ABSENT = ProjectIRPureValue(tag=ProjectIRPureTag.ABSENT)


def project_ir_pure_text(value: str) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.TEXT, text=value)


def project_ir_pure_integer(value: int) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.INTEGER, integer=value)


def project_ir_pure_enumeration(value: str) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.ENUMERATION, text=value)


def project_ir_pure_ref(value: ProjectIRPortableRef) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.REF, ref=value)


def project_ir_pure_refs(
    values: tuple[ProjectIRPortableRef, ...],
) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.REFS, refs=values)


def project_ir_pure_texts(values: tuple[str, ...]) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.TEXTS, texts=values)


def project_ir_pure_enumerations(values: tuple[str, ...]) -> ProjectIRPureValue:
    return ProjectIRPureValue(tag=ProjectIRPureTag.ENUMERATIONS, texts=values)


@dataclass(frozen=True, slots=True)
class _FieldSpec:
    key: str
    tag: ProjectIRPureTag
    optional: bool = False
    vocabulary: tuple[str, ...] | None = None


def _field(
    key: str,
    tag: ProjectIRPureTag,
    *,
    optional: bool = False,
    vocabulary: tuple[str, ...] | None = None,
) -> _FieldSpec:
    return _FieldSpec(key, tag, optional, vocabulary)


_TEXT = ProjectIRPureTag.TEXT
_INTEGER = ProjectIRPureTag.INTEGER
_ENUM = ProjectIRPureTag.ENUMERATION
_REF = ProjectIRPureTag.REF
_REFS = ProjectIRPureTag.REFS
_TEXTS = ProjectIRPureTag.TEXTS
_ENUMS = ProjectIRPureTag.ENUMERATIONS

_CONSTRUCTION_STATES = ("concrete", "unknown", "deferred", "blocked", "ambiguous")
_DECLARATION_KINDS = ("source", "table", "query")
_OPERATORS = (
    "relation_input",
    "row_filter",
    "group_aggregate",
    "result_filter",
    "window_evaluation",
    "final_projection",
    "relation_ordering",
    "limit",
)
_OUTPUT_KINDS = ("relation_row", "scalar_field", "stage_scalar_field")
_CHECKPOINTS = ("input", "base_result", "final")
_FIELD_DOMAINS = ("none", "semantic", "stage")
_USE_KINDS = ("operator_flow", "semantic")
_USE_ROLES = (
    "relation_input",
    "let_value",
    "select_value",
    "group_key",
    "satisfying",
    "grouped_order",
    "window_partition",
    "window_order",
    "window_argument",
    "window_default",
)
_PROPERTY_DIRECTIONS = ("provided", "required")
_PROPERTY_SLOTS = (
    "output_shape",
    "cardinality_bounds",
    "multiplicity",
    "relation_result_ordering",
    "local_grain_evidence",
    "fact_domains",
    "free_bindings",
    "null_extension",
    "policy_evaluation",
    "row_shape",
    "ordering",
)
_PROPERTY_EVIDENCE = ("exact", "unknown", "not_applicable")
_COMPATIBILITY = ("satisfied", "not_satisfied")
_DETERMINISM = ("unknown", "deterministic", "volatile")
_ERROR_BEHAVIOR = ("unknown", "may_error", "cannot_error")
_SIDE_EFFECTS = ("unknown", "has_side_effects", "side_effect_free")
_EVALUATION_COUNT = ("unknown", "sensitive", "insensitive")
_EVALUATION_CONTEXTS = ("aggregate", "window_operator", "window_result")
_POLICY_KINDS = ("frame_sensitive", "frame_insensitive_explicit_forbidden")
_DIMENSION_STATUS = ("evidenced", "incompatible", "not_proven")
_EQUIVALENCE_STATUS = (
    "known_incompatible",
    "candidate_not_disproven",
    "rewrite_equivalence_proven",
)
_REWRITE_STATUS = ("admissible", "blocked")
_DIMENSIONS = (
    "schema_types",
    "values",
    "bag_multiplicity",
    "null_empty_behavior",
    "cardinality_guarantees",
    "ordering",
    "effects_error_behavior",
    "evaluation_count",
    "policy_context",
    "required_capabilities",
    "provenance_traceability",
)
_TYPE_KINDS = ("builtin", "type", "enum", "shape", "unknown")
_NULLABILITIES = ("non_null", "nullable", "unknown")
_RESULT_ROLES = (
    "ordinary_row_value",
    "group_key",
    "aggregate_result",
    "window_result",
)

_HEADER_FIELDS = (
    _field("format", _ENUM),
    _field("verification", _ENUM, vocabulary=("verified",)),
    _field("node_start", _INTEGER),
    _field("node_count", _INTEGER),
    _field("output_start", _INTEGER),
    _field("output_count", _INTEGER),
    _field("slot_start", _INTEGER),
    _field("slot_count", _INTEGER),
    _field("use_start", _INTEGER),
    _field("use_count", _INTEGER),
    _field("fragment_count", _INTEGER),
    _field("cross_edge_count", _INTEGER),
    _field("property_count", _INTEGER),
    _field("compatibility_count", _INTEGER),
    _field("effect_count", _INTEGER),
    _field("evaluation_context_count", _INTEGER),
    _field("reverse_use_count", _INTEGER),
    _field("topological_count", _INTEGER),
    _field("reachability_count", _INTEGER),
    _field("equivalence_count", _INTEGER),
    _field("rewrite_count", _INTEGER),
)

_SCHEMA: Mapping[str, tuple[_FieldSpec, ...]] = MappingProxyType(
    {
        "header": _HEADER_FIELDS,
        "fragment": (
            _field("fragment", _INTEGER),
            _field("module_path", _TEXT),
            _field("module_position", _INTEGER),
            _field("declaration_position", _INTEGER),
            _field("declaration_kind", _ENUM, vocabulary=_DECLARATION_KINDS),
            _field("declared_name", _TEXT),
            _field("state", _ENUM, vocabulary=_CONSTRUCTION_STATES),
            _field("reason", _TEXT, optional=True),
            _field("root", _REF, optional=True),
            _field("nodes", _INTEGER),
            _field("outputs", _INTEGER),
        ),
        "node": (
            _field("node", _REF),
            _field("fragment", _INTEGER),
            _field("operator", _ENUM, vocabulary=_OPERATORS),
        ),
        "output": (
            _field("output", _REF),
            _field("fragment", _INTEGER),
            _field("producer", _REF),
            _field("kind", _ENUM, vocabulary=_OUTPUT_KINDS),
            _field("checkpoint", _ENUM, optional=True, vocabulary=_CHECKPOINTS),
            _field("field_domain", _ENUM, vocabulary=_FIELD_DOMAINS),
            _field("field_position", _INTEGER, optional=True),
            _field("field_name", _TEXT, optional=True),
            _field("field_count", _INTEGER),
            _field("field_names", _TEXTS),
            _field("type_names", _TEXTS),
            _field("type_kinds", _ENUMS, vocabulary=_TYPE_KINDS),
            _field("nullabilities", _ENUMS, vocabulary=_NULLABILITIES),
            _field("result_roles", _ENUMS, vocabulary=_RESULT_ROLES),
        ),
        "input_slot": (
            _field("slot", _REF),
            _field("consumer", _REF),
            _field("input_ordinal", _INTEGER),
        ),
        "use": (
            _field("use", _REF),
            _field("kind", _ENUM, vocabulary=_USE_KINDS),
            _field("output", _REF),
            _field("slot", _REF),
            _field("role", _ENUM, optional=True, vocabulary=_USE_ROLES),
            _field("source_order", _INTEGER, optional=True),
        ),
        "cross_edge": (
            _field("edge", _INTEGER),
            _field("use", _REF),
            _field("producer_fragment", _INTEGER),
            _field("consumer_fragment", _INTEGER),
            _field("compatibility", _ENUM, vocabulary=_COMPATIBILITY),
            _field("origin_kind", _ENUM, vocabulary=("local", "imported")),
            _field("origin_hops", _INTEGER),
        ),
        "property": (
            _field("property", _INTEGER),
            _field("direction", _ENUM, vocabulary=_PROPERTY_DIRECTIONS),
            _field("output", _REF, optional=True),
            _field("input_slot", _REF, optional=True),
            _field("slot", _ENUM, vocabulary=_PROPERTY_SLOTS),
            _field("evidence", _ENUM, vocabulary=_PROPERTY_EVIDENCE),
            _field("value_enum", _ENUM, optional=True),
            _field("value_integer", _INTEGER, optional=True),
        ),
        "compatibility": (
            _field("compatibility", _INTEGER),
            _field("provided_output", _REF),
            _field("required_slot", _REF),
            _field("status", _ENUM, vocabulary=_COMPATIBILITY),
        ),
        "effect": (
            _field("effect", _INTEGER),
            _field("output", _REF),
            _field("determinism", _ENUM, vocabulary=_DETERMINISM),
            _field("error_behavior", _ENUM, vocabulary=_ERROR_BEHAVIOR),
            _field("side_effects", _ENUM, vocabulary=_SIDE_EFFECTS),
            _field("evaluation_count", _ENUM, vocabulary=_EVALUATION_COUNT),
        ),
        "evaluation_context": (
            _field("context", _INTEGER),
            _field("kind", _ENUM, vocabulary=_EVALUATION_CONTEXTS),
            _field("operator", _REF),
            _field("input", _REF, optional=True),
            _field("result", _REF),
            _field("checkpoint", _ENUM, optional=True, vocabulary=_CHECKPOINTS),
            _field("window_ordinal", _INTEGER, optional=True),
            _field("group_keys", _INTEGER, optional=True),
            _field("aggregate_results", _INTEGER, optional=True),
            _field("policy", _ENUM, optional=True, vocabulary=_POLICY_KINDS),
        ),
        "reverse_use": (
            _field("reverse_use", _INTEGER),
            _field("output", _REF),
            _field("uses", _REFS),
        ),
        "topological": (
            _field("topological", _INTEGER),
            _field("node", _REF),
        ),
        "reachability": (
            _field("reachability", _INTEGER),
            _field("node", _REF),
            _field("reachable", _REFS),
        ),
        "equivalence": (
            _field("equivalence", _INTEGER),
            _field("left_fragment", _INTEGER),
            _field("right_fragment", _INTEGER),
            _field("status", _ENUM, vocabulary=_EQUIVALENCE_STATUS),
            *(
                _field(dimension, _ENUM, vocabulary=_DIMENSION_STATUS)
                for dimension in _DIMENSIONS
            ),
        ),
        "rewrite_readiness": (
            _field("rewrite", _INTEGER),
            _field("equivalence", _INTEGER),
            _field("status", _ENUM, vocabulary=_REWRITE_STATUS),
            _field("blockers", _ENUMS, vocabulary=_DIMENSIONS),
        ),
        "end": (),
    }
)

PROJECT_IR_PURE_RECORD_KINDS = tuple(_SCHEMA)


def _reject(
    status: ProjectIRPureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> ProjectIRPureOutcome:
    return ProjectIRPureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _payload_count(value: ProjectIRPureValue) -> int:
    return sum(
        item is not None
        for item in (
            value.text,
            value.integer,
            value.ref,
            value.refs,
            value.texts,
        )
    )


def _validate_ref(
    ref: ProjectIRPortableRef,
    record_position: int,
    field_position: int,
) -> ProjectIRPureOutcome | None:
    if ref.position < 0:
        return _reject(
            ProjectIRPureStatus.NEGATIVE_INTEGER,
            record_position,
            field_position,
        )
    if ref.position > PROJECT_IR_PURE_MAX_INTEGER:
        return _reject(
            ProjectIRPureStatus.INTEGER_OUT_OF_RANGE,
            record_position,
            field_position,
        )
    return None


def _validate_value(
    value: ProjectIRPureValue,
    specification: _FieldSpec,
    record_position: int,
    field_position: int,
) -> ProjectIRPureOutcome | None:
    if value.tag is ProjectIRPureTag.ABSENT:
        if not specification.optional:
            return _reject(
                ProjectIRPureStatus.ABSENT_VALUE_NOT_ALLOWED,
                record_position,
                field_position,
            )
        if _payload_count(value):
            return _reject(
                ProjectIRPureStatus.EXTRA_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        return None
    if value.tag is not specification.tag:
        return _reject(
            ProjectIRPureStatus.VALUE_TAG_MISMATCH,
            record_position,
            field_position,
        )
    if _payload_count(value) != 1:
        return _reject(
            (
                ProjectIRPureStatus.MISSING_VALUE_PAYLOAD
                if _payload_count(value) == 0
                else ProjectIRPureStatus.EXTRA_VALUE_PAYLOAD
            ),
            record_position,
            field_position,
        )
    if value.tag in {ProjectIRPureTag.TEXT, ProjectIRPureTag.ENUMERATION}:
        if value.text is None:
            return _reject(
                ProjectIRPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if specification.vocabulary is not None and (
            value.text not in specification.vocabulary
        ):
            return _reject(
                ProjectIRPureStatus.UNKNOWN_ENUMERATION,
                record_position,
                field_position,
            )
        return None
    if value.tag is ProjectIRPureTag.INTEGER:
        if value.integer is None:
            return _reject(
                ProjectIRPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        if value.integer < 0:
            return _reject(
                ProjectIRPureStatus.NEGATIVE_INTEGER,
                record_position,
                field_position,
            )
        if value.integer > PROJECT_IR_PURE_MAX_INTEGER:
            return _reject(
                ProjectIRPureStatus.INTEGER_OUT_OF_RANGE,
                record_position,
                field_position,
            )
        return None
    if value.tag is ProjectIRPureTag.REF:
        if value.ref is None:
            return _reject(
                ProjectIRPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        return _validate_ref(value.ref, record_position, field_position)
    if value.tag is ProjectIRPureTag.REFS:
        if value.refs is None:
            return _reject(
                ProjectIRPureStatus.MISSING_VALUE_PAYLOAD,
                record_position,
                field_position,
            )
        for ref in value.refs:
            rejection = _validate_ref(ref, record_position, field_position)
            if rejection is not None:
                return rejection
        return None
    if value.texts is None:
        return _reject(
            ProjectIRPureStatus.MISSING_VALUE_PAYLOAD,
            record_position,
            field_position,
        )
    if specification.vocabulary is not None and any(
        item not in specification.vocabulary for item in value.texts
    ):
        return _reject(
            ProjectIRPureStatus.UNKNOWN_ENUMERATION,
            record_position,
            field_position,
        )
    return None


def _validate_fields(
    record: ProjectIRPureRecord,
    record_position: int,
) -> ProjectIRPureOutcome | None:
    specification = _SCHEMA[record.kind]
    if len(record.fields) != len(specification):
        return _reject(ProjectIRPureStatus.FIELD_ARITY_MISMATCH, record_position)
    for field_position, (field, expected) in enumerate(
        zip(record.fields, specification, strict=True)
    ):
        if field.key != expected.key:
            return _reject(
                ProjectIRPureStatus.FIELD_KEY_MISMATCH,
                record_position,
                field_position,
            )
        rejection = _validate_value(
            field.value,
            expected,
            record_position,
            field_position,
        )
        if rejection is not None:
            return rejection
    return None


def _value(record: ProjectIRPureRecord, key: str) -> ProjectIRPureValue:
    matches = tuple(field.value for field in record.fields if field.key == key)
    if len(matches) != 1:
        raise ValueError("Validated Project IR records retain every key exactly once.")
    return matches[0]


def _text(record: ProjectIRPureRecord, key: str) -> str:
    value = _value(record, key).text
    if value is None:
        raise ValueError("Validated Project IR text cannot be absent.")
    return value


def _integer(record: ProjectIRPureRecord, key: str) -> int:
    value = _value(record, key).integer
    if value is None:
        raise ValueError("Validated Project IR integers cannot be absent.")
    return value


def _ref(record: ProjectIRPureRecord, key: str) -> ProjectIRPortableRef:
    value = _value(record, key).ref
    if value is None:
        raise ValueError("Validated Project IR refs cannot be absent.")
    return value


def _optional_ref(
    record: ProjectIRPureRecord,
    key: str,
) -> ProjectIRPortableRef | None:
    return _value(record, key).ref


def _refs(record: ProjectIRPureRecord, key: str) -> tuple[ProjectIRPortableRef, ...]:
    value = _value(record, key).refs
    if value is None:
        raise ValueError("Validated Project IR ref lists cannot be absent.")
    return value


def _texts(record: ProjectIRPureRecord, key: str) -> tuple[str, ...]:
    value = _value(record, key).texts
    if value is None:
        raise ValueError("Validated Project IR text lists cannot be absent.")
    return value


def _records_by_kind(
    records: tuple[ProjectIRPureRecord, ...],
    kind: str,
) -> tuple[ProjectIRPureRecord, ...]:
    return tuple(record for record in records if record.kind == kind)


def _require_count(
    header: ProjectIRPureRecord,
    records: tuple[ProjectIRPureRecord, ...],
    kind: str,
    key: str,
) -> bool:
    return len(_records_by_kind(records, kind)) == _integer(header, key)


def _require_ordinals(
    records: tuple[ProjectIRPureRecord, ...],
    key: str,
) -> bool:
    return tuple(_integer(record, key) for record in records) == tuple(
        range(len(records))
    )


def _definition_refs(
    records: tuple[ProjectIRPureRecord, ...],
) -> Mapping[ProjectIRPortableRef, ProjectIRPureRecord]:
    result: dict[ProjectIRPortableRef, ProjectIRPureRecord] = {}
    for kind, key in (
        ("node", "node"),
        ("output", "output"),
        ("input_slot", "slot"),
        ("use", "use"),
    ):
        for record in _records_by_kind(records, kind):
            result[_ref(record, key)] = record
    return MappingProxyType(result)


def _domain_records(
    records: tuple[ProjectIRPureRecord, ...],
    kind: str,
    key: str,
) -> tuple[ProjectIRPortableRef, ...]:
    return tuple(_ref(record, key) for record in _records_by_kind(records, kind))


def _validate_sections(
    records: tuple[ProjectIRPureRecord, ...],
) -> ProjectIRPureOutcome | None:
    section_order = tuple(_SCHEMA)
    positions: list[int] = []
    header_count = 0
    end_count = 0
    for record_position, record in enumerate(records):
        if record.kind not in _SCHEMA:
            return _reject(ProjectIRPureStatus.UNKNOWN_RECORD_KIND, record_position)
        rejection = _validate_fields(record, record_position)
        if rejection is not None:
            return rejection
        positions.append(section_order.index(record.kind))
        header_count += record.kind == "header"
        end_count += record.kind == "end"
    if header_count > 1 or end_count > 1:
        return _reject(ProjectIRPureStatus.DUPLICATE_SINGLETON_RECORD)
    if end_count == 1 and records[-1].kind != "end":
        end_position = next(
            position for position, record in enumerate(records) if record.kind == "end"
        )
        return _reject(ProjectIRPureStatus.TRAILING_RECORD, end_position + 1)
    if positions != sorted(positions):
        return _reject(ProjectIRPureStatus.SECTION_ORDER_VIOLATION)
    if end_count != 1:
        return _reject(ProjectIRPureStatus.TRAILING_RECORD, len(records))
    return None


def _record_position(
    records: tuple[ProjectIRPureRecord, ...],
    target: ProjectIRPureRecord,
) -> int:
    matches = tuple(
        position for position, record in enumerate(records) if record is target
    )
    if len(matches) != 1:
        raise ValueError("Portable Project IR records require one exact position.")
    return matches[0]


def _validate_counts(
    header: ProjectIRPureRecord,
    records: tuple[ProjectIRPureRecord, ...],
) -> ProjectIRPureOutcome | None:
    count_fields = (
        ("fragment", "fragment_count"),
        ("cross_edge", "cross_edge_count"),
        ("property", "property_count"),
        ("compatibility", "compatibility_count"),
        ("effect", "effect_count"),
        ("evaluation_context", "evaluation_context_count"),
        ("reverse_use", "reverse_use_count"),
        ("topological", "topological_count"),
        ("reachability", "reachability_count"),
        ("equivalence", "equivalence_count"),
        ("rewrite_readiness", "rewrite_count"),
    )
    if any(
        not _require_count(header, records, kind, key) for kind, key in count_fields
    ):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH, 0)
    ordinal_fields = (
        ("fragment", "fragment"),
        ("cross_edge", "edge"),
        ("property", "property"),
        ("compatibility", "compatibility"),
        ("effect", "effect"),
        ("evaluation_context", "context"),
        ("reverse_use", "reverse_use"),
        ("topological", "topological"),
        ("reachability", "reachability"),
        ("equivalence", "equivalence"),
        ("rewrite_readiness", "rewrite"),
    )
    for kind, key in ordinal_fields:
        section = _records_by_kind(records, kind)
        if not _require_ordinals(section, key):
            position = _record_position(records, section[0]) if section else 0
            return _reject(ProjectIRPureStatus.COUNT_MISMATCH, position)
    return None


def _validate_ref_coordinates(
    header: ProjectIRPureRecord,
    records: tuple[ProjectIRPureRecord, ...],
) -> ProjectIRPureOutcome | None:
    specifications = (
        (
            "node",
            "node",
            ProjectIRPortableRefDomain.PLAN_NODE,
            "node_start",
            "node_count",
        ),
        (
            "output",
            "output",
            ProjectIRPortableRefDomain.OUTPUT_VALUE,
            "output_start",
            "output_count",
        ),
        (
            "input_slot",
            "slot",
            ProjectIRPortableRefDomain.INPUT_SLOT,
            "slot_start",
            "slot_count",
        ),
        (
            "use",
            "use",
            ProjectIRPortableRefDomain.USE,
            "use_start",
            "use_count",
        ),
    )
    all_refs: list[ProjectIRPortableRef] = []
    for kind, key, domain, start_key, count_key in specifications:
        section = _records_by_kind(records, kind)
        refs = tuple(_ref(record, key) for record in section)
        if any(ref.domain is not domain for ref in refs):
            record = next(
                record for record in section if _ref(record, key).domain is not domain
            )
            return _reject(
                ProjectIRPureStatus.REF_DOMAIN_MISMATCH,
                _record_position(records, record),
            )
        start = _integer(header, start_key)
        count = _integer(header, count_key)
        if len(set(refs)) != len(refs):
            return _reject(ProjectIRPureStatus.DUPLICATE_REF)
        if len(refs) != count or tuple(ref.position for ref in refs) != tuple(
            range(start, start + count)
        ):
            return _reject(ProjectIRPureStatus.NON_DENSE_REF_COORDINATES, 0)
        all_refs.extend(refs)
    if len(set(all_refs)) != len(all_refs):
        return _reject(ProjectIRPureStatus.DUPLICATE_REF)
    return None


def evaluate_project_ir_document(
    document: ProjectIRPureDocument,
) -> ProjectIRPureOutcome:
    """Validate and encode one explicit portable document without ambient state."""

    if type(document) is not ProjectIRPureDocument:
        raise TypeError("Project IR pure evaluation requires an exact document.")
    records = document.records
    if not records:
        return _reject(ProjectIRPureStatus.EMPTY_DOCUMENT)
    if records[0].kind != "header":
        return _reject(ProjectIRPureStatus.MISSING_HEADER_RECORD, 0)
    sections = _validate_sections(records)
    if sections is not None:
        return sections
    header = records[0]
    if _text(header, "format") != PROJECT_IR_INSPECTION_FORMAT:
        return _reject(ProjectIRPureStatus.UNKNOWN_FORMAT_MARKER, 0, 0)
    counts = _validate_counts(header, records)
    if counts is not None:
        return counts
    coordinates = _validate_ref_coordinates(header, records)
    if coordinates is not None:
        return coordinates
    definitions = _definition_refs(records)
    endpoints = _validate_fragments_and_endpoints(records, definitions)
    if endpoints is not None:
        return endpoints
    facts = _validate_fact_sections(records, definitions)
    if facts is not None:
        return facts
    analyses = _validate_analysis_sections(records, definitions)
    if analyses is not None:
        return analyses
    return ProjectIRPureOutcome(
        status=ProjectIRPureStatus.OK,
        canonical_bytes=_encode_document(document),
    )


_ESCAPES: Mapping[str, str] = MappingProxyType(
    {
        "\\": "\\\\",
        "\t": "\\t",
        "\n": "\\n",
        "\r": "\\r",
        ",": "\\,",
        ":": "\\:",
        "=": "\\=",
    }
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


def _encode_ref(ref: ProjectIRPortableRef) -> str:
    return f"{ref.domain.value}:{ref.position}"


def _encode_value(value: ProjectIRPureValue) -> str:
    if value.tag is ProjectIRPureTag.ABSENT:
        return "n:"
    if value.tag in {ProjectIRPureTag.TEXT, ProjectIRPureTag.ENUMERATION}:
        assert value.text is not None
        return f"{value.tag.value}:{_escape_text(value.text)}"
    if value.tag is ProjectIRPureTag.INTEGER:
        assert value.integer is not None
        return f"i:{value.integer}"
    if value.tag is ProjectIRPureTag.REF:
        assert value.ref is not None
        return f"r:{_encode_ref(value.ref)}"
    if value.tag is ProjectIRPureTag.REFS:
        assert value.refs is not None
        return "q:" + ",".join(_encode_ref(ref) for ref in value.refs)
    assert value.texts is not None
    return value.tag.value + ":" + ",".join(_escape_text(text) for text in value.texts)


def _encode_document(document: ProjectIRPureDocument) -> bytes:
    lines = tuple(
        record.kind
        + "".join(
            f"\t{field.key}={_encode_value(field.value)}" for field in record.fields
        )
        for record in document.records
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def _expect_domain(
    ref: ProjectIRPortableRef,
    domain: ProjectIRPortableRefDomain,
    record_position: int,
    definitions: Mapping[ProjectIRPortableRef, ProjectIRPureRecord],
) -> ProjectIRPureOutcome | None:
    if ref.domain is not domain:
        return _reject(ProjectIRPureStatus.REF_DOMAIN_MISMATCH, record_position)
    if ref not in definitions:
        return _reject(ProjectIRPureStatus.DANGLING_REF, record_position)
    return None


def _validate_fragments_and_endpoints(
    records: tuple[ProjectIRPureRecord, ...],
    definitions: Mapping[ProjectIRPortableRef, ProjectIRPureRecord],
) -> ProjectIRPureOutcome | None:
    fragments = _records_by_kind(records, "fragment")
    nodes = _records_by_kind(records, "node")
    outputs = _records_by_kind(records, "output")
    slots = _records_by_kind(records, "input_slot")
    uses = _records_by_kind(records, "use")
    for fragment in fragments:
        position = _integer(fragment, "fragment")
        state = _text(fragment, "state")
        reason = _value(fragment, "reason").text
        root = _optional_ref(fragment, "root")
        fragment_nodes = tuple(
            record for record in nodes if _integer(record, "fragment") == position
        )
        fragment_outputs = tuple(
            record for record in outputs if _integer(record, "fragment") == position
        )
        if len(fragment_nodes) != _integer(fragment, "nodes") or len(
            fragment_outputs
        ) != _integer(fragment, "outputs"):
            return _reject(
                ProjectIRPureStatus.INVALID_FRAGMENT_STATE,
                _record_position(records, fragment),
            )
        if state == "concrete":
            if (
                reason is not None
                or root is None
                or not fragment_nodes
                or not fragment_outputs
            ):
                return _reject(
                    ProjectIRPureStatus.INVALID_FRAGMENT_STATE,
                    _record_position(records, fragment),
                )
            rejection = _expect_domain(
                root,
                ProjectIRPortableRefDomain.PLAN_NODE,
                _record_position(records, fragment),
                definitions,
            )
            if rejection is not None:
                return rejection
            if root != _ref(fragment_nodes[-1], "node"):
                return _reject(
                    ProjectIRPureStatus.INVALID_FRAGMENT_STATE,
                    _record_position(records, fragment),
                )
        elif (
            reason is None
            or not reason
            or root is not None
            or fragment_nodes
            or fragment_outputs
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_FRAGMENT_STATE,
                _record_position(records, fragment),
            )

    fragment_count = len(fragments)
    for node in nodes:
        if _integer(node, "fragment") >= fragment_count:
            return _reject(
                ProjectIRPureStatus.INVALID_FRAGMENT_STATE,
                _record_position(records, node),
            )
    for output in outputs:
        record_position = _record_position(records, output)
        producer = _ref(output, "producer")
        rejection = _expect_domain(
            producer,
            ProjectIRPortableRefDomain.PLAN_NODE,
            record_position,
            definitions,
        )
        if rejection is not None:
            return rejection
        if _integer(output, "fragment") >= fragment_count or _integer(
            definitions[producer], "fragment"
        ) != _integer(output, "fragment"):
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )
        field_count = _integer(output, "field_count")
        if any(
            len(_texts(output, key)) != field_count
            for key in (
                "field_names",
                "type_names",
                "type_kinds",
                "nullabilities",
                "result_roles",
            )
        ):
            return _reject(ProjectIRPureStatus.COUNT_MISMATCH, record_position)
        output_kind = _text(output, "kind")
        checkpoint = _value(output, "checkpoint").text
        field_domain = _text(output, "field_domain")
        field_position = _value(output, "field_position").integer
        field_name = _value(output, "field_name").text
        if output_kind == "relation_row":
            valid = (
                field_domain == "none" and field_position is None and field_name is None
            )
        else:
            valid = (
                field_domain
                == ("semantic" if output_kind == "scalar_field" else "stage")
                and checkpoint == (None if output_kind == "scalar_field" else "final")
                and field_position is not None
                and field_name is not None
                and field_position < field_count
                and _texts(output, "field_names")[field_position] == field_name
            )
        if not valid:
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )

    for slot in slots:
        record_position = _record_position(records, slot)
        rejection = _expect_domain(
            _ref(slot, "consumer"),
            ProjectIRPortableRefDomain.PLAN_NODE,
            record_position,
            definitions,
        )
        if rejection is not None:
            return rejection
    use_by_slot: dict[ProjectIRPortableRef, ProjectIRPureRecord] = {}
    for use in uses:
        record_position = _record_position(records, use)
        output_ref = _ref(use, "output")
        slot_ref = _ref(use, "slot")
        for ref, domain in (
            (output_ref, ProjectIRPortableRefDomain.OUTPUT_VALUE),
            (slot_ref, ProjectIRPortableRefDomain.INPUT_SLOT),
        ):
            rejection = _expect_domain(ref, domain, record_position, definitions)
            if rejection is not None:
                return rejection
        if slot_ref in use_by_slot:
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION, record_position
            )
        use_by_slot[slot_ref] = use
        kind = _text(use, "kind")
        role = _value(use, "role").text
        source_order = _value(use, "source_order").integer
        producer_node = _ref(definitions[output_ref], "producer")
        consumer_node = _ref(definitions[slot_ref], "consumer")
        input_ordinal = _integer(definitions[slot_ref], "input_ordinal")
        if kind == "operator_flow":
            valid = (
                role is None
                and source_order is None
                and input_ordinal == 0
                and producer_node != consumer_node
                and _integer(definitions[producer_node], "fragment")
                == _integer(definitions[consumer_node], "fragment")
            )
        else:
            valid = role is not None and source_order is not None
        if not valid:
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )
    if len(use_by_slot) != len(slots):
        return _reject(ProjectIRPureStatus.INVALID_ENDPOINT_RELATION)
    return None


def _validate_fact_sections(
    records: tuple[ProjectIRPureRecord, ...],
    definitions: Mapping[ProjectIRPortableRef, ProjectIRPureRecord],
) -> ProjectIRPureOutcome | None:
    fragments = _records_by_kind(records, "fragment")
    fragment_count = len(fragments)
    cross_edges = _records_by_kind(records, "cross_edge")
    semantic_uses = tuple(
        use
        for use in _records_by_kind(records, "use")
        if _text(use, "kind") == "semantic"
    )
    if len(semantic_uses) != len(cross_edges) or any(
        _value(use, "role").text != "relation_input"
        or _value(use, "source_order").integer != 0
        for use in semantic_uses
    ):
        return _reject(ProjectIRPureStatus.INVALID_ENDPOINT_RELATION)
    if tuple(_ref(edge, "use") for edge in cross_edges) != tuple(
        _ref(use, "use") for use in semantic_uses
    ):
        return _reject(ProjectIRPureStatus.INVALID_ENDPOINT_RELATION)
    for edge in cross_edges:
        record_position = _record_position(records, edge)
        use_ref = _ref(edge, "use")
        rejection = _expect_domain(
            use_ref,
            ProjectIRPortableRefDomain.USE,
            record_position,
            definitions,
        )
        if rejection is not None:
            return rejection
        use = definitions[use_ref]
        if (
            _text(use, "kind") != "semantic"
            or _value(use, "role").text != "relation_input"
            or _integer(edge, "producer_fragment") >= fragment_count
            or _integer(edge, "consumer_fragment") >= fragment_count
            or _text(edge, "compatibility") != "satisfied"
            or (
                _text(edge, "origin_kind") == "local"
                and _integer(edge, "origin_hops") != 0
            )
            or (
                _text(edge, "origin_kind") == "imported"
                and _integer(edge, "origin_hops") == 0
            )
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )
        output = definitions[_ref(use, "output")]
        slot = definitions[_ref(use, "slot")]
        producer = definitions[_ref(output, "producer")]
        consumer = definitions[_ref(slot, "consumer")]
        if _integer(producer, "fragment") != _integer(
            edge, "producer_fragment"
        ) or _integer(consumer, "fragment") != _integer(edge, "consumer_fragment"):
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )

    allowed_property_values: Mapping[str, tuple[str, ...]] = MappingProxyType(
        {
            "output_shape": _OUTPUT_KINDS,
            "multiplicity": ("bag",),
            "free_bindings": ("closed",),
            "policy_evaluation": _POLICY_KINDS,
            "row_shape": ("exact",),
        }
    )
    properties = _records_by_kind(records, "property")
    for property_record in properties:
        record_position = _record_position(records, property_record)
        direction = _text(property_record, "direction")
        output_ref = _optional_ref(property_record, "output")
        input_slot = _optional_ref(property_record, "input_slot")
        slot = _text(property_record, "slot")
        value_enum = _value(property_record, "value_enum").text
        value_integer = _value(property_record, "value_integer").integer
        if direction == "provided":
            if output_ref is None or input_slot is not None:
                return _reject(
                    ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                    record_position,
                )
            rejection = _expect_domain(
                output_ref,
                ProjectIRPortableRefDomain.OUTPUT_VALUE,
                record_position,
                definitions,
            )
        else:
            if (
                input_slot is None
                or output_ref is not None
                or slot
                not in {
                    "row_shape",
                    "ordering",
                    "local_grain_evidence",
                }
            ):
                return _reject(
                    ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                    record_position,
                )
            rejection = _expect_domain(
                input_slot,
                ProjectIRPortableRefDomain.INPUT_SLOT,
                record_position,
                definitions,
            )
        if rejection is not None:
            return rejection
        vocabulary = allowed_property_values.get(slot)
        if value_enum is not None and (
            vocabulary is None or value_enum not in vocabulary
        ):
            return _reject(
                ProjectIRPureStatus.UNKNOWN_ENUMERATION,
                record_position,
                6,
            )
        if slot == "cardinality_bounds" and value_integer is None:
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )
        if slot in {"relation_result_ordering", "local_grain_evidence"} and (
            value_integer is None
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )

    provided_records = tuple(
        record for record in properties if _text(record, "direction") == "provided"
    )
    required_records = tuple(
        record for record in properties if _text(record, "direction") == "required"
    )
    if properties != (*provided_records, *required_records):
        return _reject(ProjectIRPureStatus.SECTION_ORDER_VIOLATION)
    provided_keys = tuple(
        (
            _ref(record, "output").position,
            _PROPERTY_SLOTS.index(_text(record, "slot")),
        )
        for record in provided_records
    )
    if len(set(provided_keys)) != len(provided_keys) or provided_keys != tuple(
        sorted(provided_keys)
    ):
        return _reject(ProjectIRPureStatus.SECTION_ORDER_VIOLATION)
    required_positions = tuple(
        _ref(record, "input_slot").position for record in required_records
    )
    if required_positions != tuple(sorted(required_positions)):
        return _reject(ProjectIRPureStatus.SECTION_ORDER_VIOLATION)

    output_records = _records_by_kind(records, "output")
    for output_record in output_records:
        output_ref = _ref(output_record, "output")
        provided = tuple(
            record
            for record in properties
            if _text(record, "direction") == "provided"
            and _optional_ref(record, "output") == output_ref
        )
        slots = tuple(_text(record, "slot") for record in provided)
        required_slots = {"output_shape"}
        if _text(output_record, "kind") == "relation_row":
            required_slots.update({"multiplicity", "free_bindings"})
        if _text(output_record, "kind") == "stage_scalar_field":
            required_slots.add("policy_evaluation")
        if not required_slots.issubset(slots) or any(
            slots.count(slot) != 1 for slot in required_slots
        ):
            return _reject(
                ProjectIRPureStatus.COUNT_MISMATCH,
                _record_position(records, output_record),
            )

    if len(required_records) != len(cross_edges) or any(
        _text(record, "slot") != "row_shape" for record in required_records
    ):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH)

    compatibilities = _records_by_kind(records, "compatibility")
    if len(compatibilities) != len(cross_edges):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH)
    for compatibility, edge in zip(compatibilities, cross_edges, strict=True):
        record_position = _record_position(records, compatibility)
        for ref, domain in (
            (
                _ref(compatibility, "provided_output"),
                ProjectIRPortableRefDomain.OUTPUT_VALUE,
            ),
            (
                _ref(compatibility, "required_slot"),
                ProjectIRPortableRefDomain.INPUT_SLOT,
            ),
        ):
            rejection = _expect_domain(ref, domain, record_position, definitions)
            if rejection is not None:
                return rejection
        use = definitions[_ref(edge, "use")]
        if (
            _ref(compatibility, "provided_output") != _ref(use, "output")
            or _ref(compatibility, "required_slot") != _ref(use, "slot")
            or _text(compatibility, "status") != _text(edge, "compatibility")
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )

    effects = _records_by_kind(records, "effect")
    if len(effects) != len(output_records) or tuple(
        _ref(effect, "output") for effect in effects
    ) != tuple(_ref(output, "output") for output in output_records):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH)
    for effect in effects:
        record_position = _record_position(records, effect)
        rejection = _expect_domain(
            _ref(effect, "output"),
            ProjectIRPortableRefDomain.OUTPUT_VALUE,
            record_position,
            definitions,
        )
        if rejection is not None:
            return rejection

    contexts = _records_by_kind(records, "evaluation_context")
    for context in contexts:
        record_position = _record_position(records, context)
        for ref, domain in (
            (
                _ref(context, "operator"),
                ProjectIRPortableRefDomain.PLAN_NODE,
            ),
            (
                _ref(context, "result"),
                ProjectIRPortableRefDomain.OUTPUT_VALUE,
            ),
        ):
            rejection = _expect_domain(ref, domain, record_position, definitions)
            if rejection is not None:
                return rejection
        input_ref = _optional_ref(context, "input")
        if input_ref is not None:
            rejection = _expect_domain(
                input_ref,
                ProjectIRPortableRefDomain.OUTPUT_VALUE,
                record_position,
                definitions,
            )
            if rejection is not None:
                return rejection
        kind = _text(context, "kind")
        window_ordinal = _value(context, "window_ordinal").integer
        group_keys = _value(context, "group_keys").integer
        aggregate_results = _value(context, "aggregate_results").integer
        policy = _value(context, "policy").text
        checkpoint = _value(context, "checkpoint").text
        operator_kind = _text(definitions[_ref(context, "operator")], "operator")
        result_kind = _text(definitions[_ref(context, "result")], "kind")
        input_kind = (
            None if input_ref is None else _text(definitions[input_ref], "kind")
        )
        if kind == "aggregate":
            valid = (
                input_ref is not None
                and operator_kind == "group_aggregate"
                and input_kind == "relation_row"
                and result_kind == "relation_row"
                and checkpoint == "base_result"
                and window_ordinal is None
                and group_keys is not None
                and aggregate_results is not None
                and policy is None
            )
        elif kind == "window_operator":
            valid = (
                input_ref is not None
                and operator_kind == "window_evaluation"
                and input_kind == "relation_row"
                and result_kind == "relation_row"
                and checkpoint == "base_result"
                and window_ordinal is None
                and group_keys is None
                and aggregate_results is None
                and policy is None
            )
        else:
            valid = (
                input_ref is None
                and operator_kind == "window_evaluation"
                and result_kind == "stage_scalar_field"
                and checkpoint is None
                and window_ordinal is not None
                and group_keys is None
                and aggregate_results is None
                and policy is not None
            )
        if not valid:
            return _reject(
                ProjectIRPureStatus.INVALID_ENDPOINT_RELATION,
                record_position,
            )
    aggregate_nodes = tuple(
        _ref(node, "node")
        for node in _records_by_kind(records, "node")
        if _text(node, "operator") == "group_aggregate"
    )
    window_nodes = tuple(
        _ref(node, "node")
        for node in _records_by_kind(records, "node")
        if _text(node, "operator") == "window_evaluation"
    )
    aggregate_contexts = tuple(
        context for context in contexts if _text(context, "kind") == "aggregate"
    )
    window_contexts = tuple(
        context for context in contexts if _text(context, "kind") == "window_operator"
    )
    result_contexts = tuple(
        context for context in contexts if _text(context, "kind") == "window_result"
    )
    stage_scalar_outputs = tuple(
        _ref(output, "output")
        for output in output_records
        if _text(output, "kind") == "stage_scalar_field"
    )
    if (
        tuple(_ref(context, "operator") for context in aggregate_contexts)
        != aggregate_nodes
        or tuple(_ref(context, "operator") for context in window_contexts)
        != window_nodes
        or tuple(_ref(context, "result") for context in result_contexts)
        != stage_scalar_outputs
    ):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH)
    return None


def _node_graph(
    records: tuple[ProjectIRPureRecord, ...],
    definitions: Mapping[ProjectIRPortableRef, ProjectIRPureRecord],
) -> (
    tuple[
        tuple[ProjectIRPortableRef, ...],
        tuple[tuple[int, ...], ...],
    ]
    | None
):
    nodes = _domain_records(records, "node", "node")
    index = {ref: position for position, ref in enumerate(nodes)}
    successors: list[list[int]] = [[] for _ in nodes]
    for use in _records_by_kind(records, "use"):
        output = definitions.get(_ref(use, "output"))
        slot = definitions.get(_ref(use, "slot"))
        if output is None or slot is None:
            return None
        producer = _ref(output, "producer")
        consumer = _ref(slot, "consumer")
        if producer not in index or consumer not in index:
            return None
        successors[index[producer]].append(index[consumer])
    return nodes, tuple(tuple(items) for items in successors)


def _transitive_reachability(
    successors: tuple[tuple[int, ...], ...],
) -> tuple[tuple[int, ...], ...]:
    result: list[tuple[int, ...]] = []
    for source in range(len(successors)):
        seen = [False] * len(successors)
        pending = deque(successors[source])
        while pending:
            current = pending.popleft()
            if seen[current]:
                continue
            seen[current] = True
            pending.extend(successors[current])
        result.append(tuple(index for index, value in enumerate(seen) if value))
    return tuple(result)


def _validate_analysis_sections(
    records: tuple[ProjectIRPureRecord, ...],
    definitions: Mapping[ProjectIRPortableRef, ProjectIRPureRecord],
) -> ProjectIRPureOutcome | None:
    uses = _records_by_kind(records, "use")
    outputs = _domain_records(records, "output", "output")
    reverse = _records_by_kind(records, "reverse_use")
    if len(reverse) != len(outputs):
        return _reject(ProjectIRPureStatus.COUNT_MISMATCH)
    for output_ref, record in zip(outputs, reverse, strict=True):
        record_position = _record_position(records, record)
        expected = tuple(
            _ref(use, "use") for use in uses if _ref(use, "output") == output_ref
        )
        if _ref(record, "output") != output_ref or _refs(record, "uses") != expected:
            return _reject(
                ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE,
                record_position,
            )
        if any(ref.domain is not ProjectIRPortableRefDomain.USE for ref in expected):
            return _reject(
                ProjectIRPureStatus.REF_DOMAIN_MISMATCH,
                record_position,
            )

    graph = _node_graph(records, definitions)
    if graph is None:
        return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)
    nodes, successors = graph
    topological = _records_by_kind(records, "topological")
    topological_refs = tuple(_ref(record, "node") for record in topological)
    if len(topological_refs) != len(nodes) or set(topological_refs) != set(nodes):
        return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)
    order = {ref: position for position, ref in enumerate(topological_refs)}
    for producer, targets in enumerate(successors):
        if any(order[nodes[producer]] >= order[nodes[target]] for target in targets):
            return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)

    reachability = _records_by_kind(records, "reachability")
    closure = _transitive_reachability(successors)
    if len(reachability) != len(nodes):
        return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)
    for index, record in enumerate(reachability):
        expected = tuple(nodes[target] for target in closure[index])
        if (
            _ref(record, "node") != nodes[index]
            or _refs(record, "reachable") != expected
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE,
                _record_position(records, record),
            )

    fragments = _records_by_kind(records, "fragment")
    concrete = tuple(
        _integer(fragment, "fragment")
        for fragment in fragments
        if _text(fragment, "state") == "concrete"
    )
    expected_pairs = tuple(
        (left, right)
        for left_index, left in enumerate(concrete)
        for right in concrete[left_index + 1 :]
    )
    equivalence = _records_by_kind(records, "equivalence")
    if len(equivalence) != len(expected_pairs):
        return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)
    for record, pair in zip(equivalence, expected_pairs, strict=True):
        statuses = tuple(_text(record, dimension) for dimension in _DIMENSIONS)
        expected_status = (
            "known_incompatible"
            if "incompatible" in statuses
            else (
                "rewrite_equivalence_proven"
                if all(status == "evidenced" for status in statuses)
                else "candidate_not_disproven"
            )
        )
        if (
            _integer(record, "left_fragment"),
            _integer(record, "right_fragment"),
        ) != pair or _text(record, "status") != expected_status:
            return _reject(
                ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE,
                _record_position(records, record),
            )

    rewrite = _records_by_kind(records, "rewrite_readiness")
    if len(rewrite) != len(equivalence):
        return _reject(ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE)
    for index, (record, assessment) in enumerate(
        zip(rewrite, equivalence, strict=True)
    ):
        blockers = tuple(
            dimension
            for dimension in _DIMENSIONS
            if _text(assessment, dimension) != "evidenced"
        )
        expected_status = (
            "admissible"
            if not blockers
            and _text(assessment, "status") == "rewrite_equivalence_proven"
            else "blocked"
        )
        if (
            _integer(record, "equivalence") != index
            or _text(record, "status") != expected_status
            or _texts(record, "blockers") != blockers
        ):
            return _reject(
                ProjectIRPureStatus.INVALID_ANALYSIS_REFERENCE,
                _record_position(records, record),
            )
    return None
