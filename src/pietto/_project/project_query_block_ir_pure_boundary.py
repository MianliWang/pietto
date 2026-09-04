"""Pure portable Phase-63 query-block IR observation and total evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from heapq import heappop, heappush
from typing import cast

__all__: tuple[str, ...] = ()

PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT = "pietto.phase63-query-block-ir-inspection.v1"
_MAX_INTEGER = (1 << 63) - 1


class ProjectQueryBlockIRPortableRefDomain(StrEnum):
    PLAN_NODE = "plan_node"
    OUTPUT_VALUE = "output_value"
    INPUT_SLOT = "input_slot"
    USE = "use"
    OWNER_ENTRY = "owner_entry"
    OPERATOR = "operator"
    ROW_FIELD = "row_field"
    RELATIONAL_PROPERTY = "relational_property"
    VALUE_CLASS = "value_class"
    CANDIDATE_KEY = "candidate_key"
    VALUE_FD = "value_fd"
    GRAIN_ORIGIN = "grain_origin"
    GRAIN_FACTOR = "grain_factor"
    ANALYSIS_ENTRY = "analysis_entry"


class ProjectQueryBlockIRPureTag(StrEnum):
    TEXT = "text"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ENUMERATION = "enumeration"
    REF = "ref"
    REFS = "refs"
    TEXTS = "texts"
    INTEGERS = "integers"
    ENUMERATIONS = "enumerations"
    ABSENT = "absent"


class ProjectQueryBlockIRRecordKind(StrEnum):
    HEADER = "header"
    OWNER_ENTRY = "owner_entry"
    DEPENDENCY = "dependency"
    NODE = "node"
    OUTPUT = "output"
    INPUT_SLOT = "input_slot"
    USE = "use"
    OPERATOR = "operator"
    ROW_FIELD = "row_field"
    RELATIONAL_PROPERTY = "relational_property"
    VALUE_CLASS = "value_class"
    CANDIDATE_KEY = "candidate_key"
    VALUE_FD = "value_fd"
    GRAIN_ORIGIN = "grain_origin"
    GRAIN_FACTOR = "grain_factor"
    GRAIN_DEPENDENCY = "grain_dependency"
    WINDOW_SELECTED = "window_selected"
    WINDOW_HIDDEN = "window_hidden"
    ANALYSIS_REVERSE_USE = "analysis_reverse_use"
    ANALYSIS_TOPOLOGICAL = "analysis_topological"
    ANALYSIS_REACHABILITY = "analysis_reachability"
    END = "end"


class ProjectQueryBlockIRPureStatus(StrEnum):
    OK = "ok"
    INVALID_DOCUMENT = "invalid_document"
    INVALID_HEADER = "invalid_header"
    UNKNOWN_FORMAT = "unknown_format"
    INVALID_RECORD_KIND = "invalid_record_kind"
    INVALID_SECTION_ORDER = "invalid_section_order"
    INVALID_FIELD = "invalid_field"
    INVALID_VALUE = "invalid_value"
    INVALID_REF = "invalid_ref"
    DANGLING_REF = "dangling_ref"
    INVALID_COUNT = "invalid_count"
    INVALID_ENTRY = "invalid_entry"
    INVALID_ACTIVE_MAPPING = "invalid_active_mapping"
    INVALID_TERMINAL = "invalid_terminal"
    INVALID_TOPOLOGY = "invalid_topology"
    INVALID_OPERATOR = "invalid_operator"
    INVALID_PROPERTY = "invalid_property"
    INVALID_GRAIN = "invalid_grain"
    INVALID_WINDOW = "invalid_window"
    INVALID_ANALYSIS = "invalid_analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPortableRef:
    domain: ProjectQueryBlockIRPortableRefDomain
    position: int

    def __post_init__(self) -> None:
        if type(self.domain) is not ProjectQueryBlockIRPortableRefDomain:
            raise TypeError("Portable ref requires one closed domain.")
        if type(self.position) is not int or not 0 <= self.position <= _MAX_INTEGER:
            raise ValueError("Portable ref position must be a bounded integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPureValue:
    tag: ProjectQueryBlockIRPureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None
    enumeration: str | None = None
    ref: ProjectQueryBlockIRPortableRef | None = None
    refs: tuple[ProjectQueryBlockIRPortableRef, ...] = ()
    texts: tuple[str, ...] = ()
    integers: tuple[int, ...] = ()
    enumerations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.tag) is not ProjectQueryBlockIRPureTag:
            raise TypeError("Pure value requires one closed tag.")
        payloads = (
            self.text is not None,
            self.integer is not None,
            self.boolean is not None,
            self.enumeration is not None,
            self.ref is not None,
            bool(self.refs),
            bool(self.texts),
            bool(self.integers),
            bool(self.enumerations),
        )
        if self.tag is ProjectQueryBlockIRPureTag.ABSENT:
            valid = not any(payloads)
        else:
            expected = {
                ProjectQueryBlockIRPureTag.TEXT: self.text is not None,
                ProjectQueryBlockIRPureTag.INTEGER: self.integer is not None,
                ProjectQueryBlockIRPureTag.BOOLEAN: self.boolean is not None,
                ProjectQueryBlockIRPureTag.ENUMERATION: self.enumeration is not None,
                ProjectQueryBlockIRPureTag.REF: self.ref is not None,
                ProjectQueryBlockIRPureTag.REFS: bool(self.refs),
                ProjectQueryBlockIRPureTag.TEXTS: bool(self.texts),
                ProjectQueryBlockIRPureTag.INTEGERS: bool(self.integers),
                ProjectQueryBlockIRPureTag.ENUMERATIONS: bool(self.enumerations),
            }[self.tag]
            valid = expected and sum(payloads) == 1
        if not valid:
            raise ValueError("Pure value tag and payload disagree.")


PROJECT_QUERY_BLOCK_IR_PURE_ABSENT = ProjectQueryBlockIRPureValue(
    tag=ProjectQueryBlockIRPureTag.ABSENT
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPureField:
    key: str
    value: ProjectQueryBlockIRPureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str or not self.key:
            raise ValueError("Pure field key must be non-empty text.")
        if type(self.value) is not ProjectQueryBlockIRPureValue:
            raise TypeError("Pure field requires one exact value.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPureRecord:
    kind: ProjectQueryBlockIRRecordKind
    fields: tuple[ProjectQueryBlockIRPureField, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectQueryBlockIRRecordKind:
            raise TypeError("Pure record requires one closed kind.")
        if type(self.fields) is not tuple or any(
            type(field) is not ProjectQueryBlockIRPureField for field in self.fields
        ):
            raise TypeError("Pure record requires an exact field tuple.")
        if len({field.key for field in self.fields}) != len(self.fields):
            raise ValueError("Pure record fields cannot repeat keys.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPureDocument:
    format_marker: str
    records: tuple[ProjectQueryBlockIRPureRecord, ...]

    def __post_init__(self) -> None:
        if type(self.format_marker) is not str:
            raise TypeError("Pure document marker must be text.")
        if type(self.records) is not tuple or any(
            type(record) is not ProjectQueryBlockIRPureRecord for record in self.records
        ):
            raise TypeError("Pure document requires an exact record tuple.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectQueryBlockIRPureOutcome:
    status: ProjectQueryBlockIRPureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not ProjectQueryBlockIRPureStatus:
            raise TypeError("Pure outcome requires one closed status.")
        if self.status is ProjectQueryBlockIRPureStatus.OK:
            if type(self.canonical_bytes) is not bytes:
                raise ValueError("OK outcome requires canonical bytes.")
            if self.record_position is not None or self.field_position is not None:
                raise ValueError("OK outcome cannot retain rejection coordinates.")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected outcome cannot expose canonical bytes.")
        for coordinate in (self.record_position, self.field_position):
            if coordinate is not None and (
                type(coordinate) is not int or coordinate < 0
            ):
                raise ValueError("Rejection coordinates must be non-negative.")


def project_query_block_ir_pure_text(value: str) -> ProjectQueryBlockIRPureValue:
    return ProjectQueryBlockIRPureValue(tag=ProjectQueryBlockIRPureTag.TEXT, text=value)


def project_query_block_ir_pure_integer(value: int) -> ProjectQueryBlockIRPureValue:
    return ProjectQueryBlockIRPureValue(
        tag=ProjectQueryBlockIRPureTag.INTEGER, integer=value
    )


def project_query_block_ir_pure_boolean(value: bool) -> ProjectQueryBlockIRPureValue:
    return ProjectQueryBlockIRPureValue(
        tag=ProjectQueryBlockIRPureTag.BOOLEAN, boolean=value
    )


def project_query_block_ir_pure_enumeration(
    value: str,
) -> ProjectQueryBlockIRPureValue:
    return ProjectQueryBlockIRPureValue(
        tag=ProjectQueryBlockIRPureTag.ENUMERATION, enumeration=value
    )


def project_query_block_ir_pure_ref(
    value: ProjectQueryBlockIRPortableRef,
) -> ProjectQueryBlockIRPureValue:
    return ProjectQueryBlockIRPureValue(tag=ProjectQueryBlockIRPureTag.REF, ref=value)


def project_query_block_ir_pure_refs(
    values: tuple[ProjectQueryBlockIRPortableRef, ...],
) -> ProjectQueryBlockIRPureValue:
    return (
        ProjectQueryBlockIRPureValue(tag=ProjectQueryBlockIRPureTag.REFS, refs=values)
        if values
        else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    )


def project_query_block_ir_pure_texts(
    values: tuple[str, ...],
) -> ProjectQueryBlockIRPureValue:
    return (
        ProjectQueryBlockIRPureValue(tag=ProjectQueryBlockIRPureTag.TEXTS, texts=values)
        if values
        else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    )


def project_query_block_ir_pure_integers(
    values: tuple[int, ...],
) -> ProjectQueryBlockIRPureValue:
    return (
        ProjectQueryBlockIRPureValue(
            tag=ProjectQueryBlockIRPureTag.INTEGERS, integers=values
        )
        if values
        else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    )


def project_query_block_ir_pure_enumerations(
    values: tuple[str, ...],
) -> ProjectQueryBlockIRPureValue:
    return (
        ProjectQueryBlockIRPureValue(
            tag=ProjectQueryBlockIRPureTag.ENUMERATIONS, enumerations=values
        )
        if values
        else PROJECT_QUERY_BLOCK_IR_PURE_ABSENT
    )


@dataclass(frozen=True, slots=True)
class _FieldSpec:
    key: str
    tags: tuple[ProjectQueryBlockIRPureTag, ...]
    domain: ProjectQueryBlockIRPortableRefDomain | None = None


def _spec(
    key: str,
    tag: ProjectQueryBlockIRPureTag,
    domain: ProjectQueryBlockIRPortableRefDomain | None = None,
    *,
    optional: bool = False,
) -> _FieldSpec:
    return _FieldSpec(
        key,
        (tag, ProjectQueryBlockIRPureTag.ABSENT) if optional else (tag,),
        domain,
    )


_T = ProjectQueryBlockIRPureTag.TEXT
_I = ProjectQueryBlockIRPureTag.INTEGER
_B = ProjectQueryBlockIRPureTag.BOOLEAN
_E = ProjectQueryBlockIRPureTag.ENUMERATION
_R = ProjectQueryBlockIRPureTag.REF
_RS = ProjectQueryBlockIRPureTag.REFS
_ES = ProjectQueryBlockIRPureTag.ENUMERATIONS

_D = ProjectQueryBlockIRPortableRefDomain
_K = ProjectQueryBlockIRRecordKind

_SCHEMAS: dict[ProjectQueryBlockIRRecordKind, tuple[_FieldSpec, ...]] = {
    _K.HEADER: (
        _spec("format", _T),
        _spec("verification", _E),
        _spec("node_start", _I),
        _spec("output_start", _I),
        _spec("slot_start", _I),
        _spec("use_start", _I),
        _spec("node_end", _I),
        _spec("output_end", _I),
        _spec("slot_end", _I),
        _spec("use_end", _I),
        _spec("schedule", _RS, _D.OWNER_ENTRY, optional=True),
    ),
    _K.OWNER_ENTRY: (
        _spec("ref", _R, _D.OWNER_ENTRY),
        _spec("module_path", _T),
        _spec("module_position", _I),
        _spec("namespace", _E),
        _spec("declaration_kind", _E),
        _spec("declared_name", _T),
        _spec("declaration_position", _I),
        _spec("variant", _E),
        _spec("active_output", _R, _D.OUTPUT_VALUE, optional=True),
        _spec("active_property", _R, _D.RELATIONAL_PROPERTY, optional=True),
        _spec("relation_input_owner", _R, _D.OWNER_ENTRY, optional=True),
        _spec("relation_input_use", _R, _D.USE, optional=True),
        _spec("compatibility", _E, optional=True),
        _spec("terminal_reason", _E, optional=True),
        _spec("blocker_kind", _E, optional=True),
        _spec("blocker_entry", _R, _D.OWNER_ENTRY, optional=True),
        _spec("blocker_uses", _RS, _D.USE, optional=True),
    ),
    _K.DEPENDENCY: (
        _spec("consumer", _R, _D.OWNER_ENTRY),
        _spec("target", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("evidence_kind", _E),
    ),
    _K.NODE: (
        _spec("ref", _R, _D.PLAN_NODE),
        _spec("stage", _E),
    ),
    _K.OUTPUT: (
        _spec("ref", _R, _D.OUTPUT_VALUE),
        _spec("producer", _R, _D.PLAN_NODE),
        _spec("kind", _E),
        _spec("owner", _R, _D.OWNER_ENTRY, optional=True),
        _spec("row_field", _R, _D.ROW_FIELD, optional=True),
    ),
    _K.INPUT_SLOT: (
        _spec("ref", _R, _D.INPUT_SLOT),
        _spec("consumer", _R, _D.PLAN_NODE),
        _spec("ordinal", _I),
    ),
    _K.USE: (
        _spec("ref", _R, _D.USE),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("slot", _R, _D.INPUT_SLOT),
        _spec("kind", _E),
        _spec("owner", _R, _D.OWNER_ENTRY, optional=True),
    ),
    _K.OPERATOR: (
        _spec("ref", _R, _D.OPERATOR),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("node", _R, _D.PLAN_NODE),
        _spec("row_output", _R, _D.OUTPUT_VALUE),
        _spec("kind", _E),
        _spec("evidence_kind", _E),
        _spec("provenance", _E),
        _spec("selected_count", _I),
        _spec("hidden_count", _I),
    ),
    _K.ROW_FIELD: (
        _spec("ref", _R, _D.ROW_FIELD),
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("field_position", _I),
        _spec("name", _T),
        _spec("nullability", _E),
        _spec("provenance", _E),
        _spec("semantic_source_kind", _E),
        _spec("introduction_use", _R, _D.USE, optional=True),
        _spec("nulling_joins", _RS, _D.PLAN_NODE, optional=True),
        _spec("final_owner", _R, _D.OWNER_ENTRY, optional=True),
        _spec("final_kind", _E, optional=True),
        _spec("final_position", _I, optional=True),
        _spec("final_name", _T, optional=True),
    ),
    _K.RELATIONAL_PROPERTY: (
        _spec("ref", _R, _D.RELATIONAL_PROPERTY),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("multiplicity", _E),
        _spec("fields", _RS, _D.ROW_FIELD, optional=True),
        _spec("value_classes", _RS, _D.VALUE_CLASS, optional=True),
        _spec("candidate_keys", _RS, _D.CANDIDATE_KEY, optional=True),
        _spec("value_fds", _RS, _D.VALUE_FD, optional=True),
        _spec("fd_index_universe", _RS, _D.VALUE_CLASS, optional=True),
        _spec("fd_index_facts", _RS, _D.VALUE_FD, optional=True),
        _spec("grain_state", _E),
        _spec("grain_origins", _RS, _D.GRAIN_ORIGIN, optional=True),
        _spec("grain_factors", _RS, _D.GRAIN_FACTOR, optional=True),
        _spec("active_grain_factors", _RS, _D.GRAIN_FACTOR, optional=True),
        _spec("ordering_kind", _E),
        _spec("order_directions", _ES, optional=True),
        _spec("cardinality_bound", _I, optional=True),
        _spec("determinism", _E),
        _spec("error_behavior", _E),
        _spec("side_effects", _E),
        _spec("evaluation_count", _E),
    ),
    _K.VALUE_CLASS: (
        _spec("ref", _R, _D.VALUE_CLASS),
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("members", _RS, _D.ROW_FIELD),
    ),
    _K.CANDIDATE_KEY: (
        _spec("ref", _R, _D.CANDIDATE_KEY),
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("determinants", _RS, _D.VALUE_CLASS),
        _spec("strength", _E),
    ),
    _K.VALUE_FD: (
        _spec("ref", _R, _D.VALUE_FD),
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("determinants", _RS, _D.VALUE_CLASS),
        _spec("dependents", _RS, _D.VALUE_CLASS),
        _spec("strength", _E),
    ),
    _K.GRAIN_ORIGIN: (
        _spec("ref", _R, _D.GRAIN_ORIGIN),
        _spec("operator", _R, _D.PLAN_NODE),
        _spec("kind", _E),
        _spec("factors", _RS, _D.GRAIN_FACTOR, optional=True),
    ),
    _K.GRAIN_FACTOR: (
        _spec("ref", _R, _D.GRAIN_FACTOR),
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("kind", _E),
        _spec("use_kind", _E),
        _spec("owner", _R, _D.OWNER_ENTRY, optional=True),
        _spec("operator", _R, _D.PLAN_NODE, optional=True),
        _spec("introduction_use", _R, _D.USE, optional=True),
        _spec("nulling_joins", _RS, _D.PLAN_NODE, optional=True),
        _spec("active", _B),
    ),
    _K.GRAIN_DEPENDENCY: (
        _spec("property", _R, _D.RELATIONAL_PROPERTY),
        _spec("determinants", _RS, _D.GRAIN_FACTOR),
        _spec("dependents", _RS, _D.GRAIN_FACTOR),
    ),
    _K.WINDOW_SELECTED: (
        _spec("operator", _R, _D.OPERATOR),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("row_field", _R, _D.ROW_FIELD),
        _spec("evidence_kind", _E),
    ),
    _K.WINDOW_HIDDEN: (
        _spec("operator", _R, _D.OPERATOR),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("evidence_kind", _E),
    ),
    _K.ANALYSIS_REVERSE_USE: (
        _spec("ref", _R, _D.ANALYSIS_ENTRY),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("uses", _RS, _D.USE, optional=True),
    ),
    _K.ANALYSIS_TOPOLOGICAL: (
        _spec("ref", _R, _D.ANALYSIS_ENTRY),
        _spec("position", _I),
        _spec("node", _R, _D.PLAN_NODE),
    ),
    _K.ANALYSIS_REACHABILITY: (
        _spec("ref", _R, _D.ANALYSIS_ENTRY),
        _spec("source", _R, _D.PLAN_NODE),
        _spec("reachable", _RS, _D.PLAN_NODE, optional=True),
    ),
    _K.END: (),
}


_DEFINITION_DOMAINS: dict[
    ProjectQueryBlockIRRecordKind, ProjectQueryBlockIRPortableRefDomain
] = {
    _K.OWNER_ENTRY: _D.OWNER_ENTRY,
    _K.NODE: _D.PLAN_NODE,
    _K.OUTPUT: _D.OUTPUT_VALUE,
    _K.INPUT_SLOT: _D.INPUT_SLOT,
    _K.USE: _D.USE,
    _K.OPERATOR: _D.OPERATOR,
    _K.ROW_FIELD: _D.ROW_FIELD,
    _K.RELATIONAL_PROPERTY: _D.RELATIONAL_PROPERTY,
    _K.VALUE_CLASS: _D.VALUE_CLASS,
    _K.CANDIDATE_KEY: _D.CANDIDATE_KEY,
    _K.VALUE_FD: _D.VALUE_FD,
    _K.GRAIN_ORIGIN: _D.GRAIN_ORIGIN,
    _K.GRAIN_FACTOR: _D.GRAIN_FACTOR,
    _K.ANALYSIS_REVERSE_USE: _D.ANALYSIS_ENTRY,
    _K.ANALYSIS_TOPOLOGICAL: _D.ANALYSIS_ENTRY,
    _K.ANALYSIS_REACHABILITY: _D.ANALYSIS_ENTRY,
}


def _reject(
    status: ProjectQueryBlockIRPureStatus,
    record_position: int = 0,
    field_position: int = 0,
) -> ProjectQueryBlockIRPureOutcome:
    return ProjectQueryBlockIRPureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _value_is_closed(value: ProjectQueryBlockIRPureValue) -> bool:
    if (
        type(value) is not ProjectQueryBlockIRPureValue
        or type(value.tag) is not ProjectQueryBlockIRPureTag
    ):
        return False
    if (
        (value.text is not None and type(value.text) is not str)
        or (value.integer is not None and type(value.integer) is not int)
        or (value.boolean is not None and type(value.boolean) is not bool)
        or (value.enumeration is not None and type(value.enumeration) is not str)
        or (
            value.ref is not None
            and type(value.ref) is not ProjectQueryBlockIRPortableRef
        )
        or type(value.refs) is not tuple
        or type(value.texts) is not tuple
        or type(value.integers) is not tuple
        or type(value.enumerations) is not tuple
    ):
        return False
    payloads = (
        value.text is not None,
        value.integer is not None,
        value.boolean is not None,
        value.enumeration is not None,
        value.ref is not None,
        bool(value.refs),
        bool(value.texts),
        bool(value.integers),
        bool(value.enumerations),
    )
    if value.tag is ProjectQueryBlockIRPureTag.ABSENT:
        return not any(payloads)
    selected = {
        ProjectQueryBlockIRPureTag.TEXT: type(value.text) is str,
        ProjectQueryBlockIRPureTag.INTEGER: type(value.integer) is int,
        ProjectQueryBlockIRPureTag.BOOLEAN: type(value.boolean) is bool,
        ProjectQueryBlockIRPureTag.ENUMERATION: type(value.enumeration) is str,
        ProjectQueryBlockIRPureTag.REF: type(value.ref)
        is ProjectQueryBlockIRPortableRef,
        ProjectQueryBlockIRPureTag.REFS: type(value.refs) is tuple
        and bool(value.refs)
        and all(type(ref) is ProjectQueryBlockIRPortableRef for ref in value.refs),
        ProjectQueryBlockIRPureTag.TEXTS: type(value.texts) is tuple
        and bool(value.texts)
        and all(type(text) is str for text in value.texts),
        ProjectQueryBlockIRPureTag.INTEGERS: type(value.integers) is tuple
        and bool(value.integers)
        and all(type(integer) is int for integer in value.integers),
        ProjectQueryBlockIRPureTag.ENUMERATIONS: type(value.enumerations) is tuple
        and bool(value.enumerations)
        and all(type(item) is str for item in value.enumerations),
    }[value.tag]
    integers = (() if value.integer is None else (value.integer,)) + value.integers
    refs = (() if value.ref is None else (value.ref,)) + value.refs
    return (
        selected
        and sum(payloads) == 1
        and all(0 <= integer <= _MAX_INTEGER for integer in integers)
        and all(
            type(ref.domain) is ProjectQueryBlockIRPortableRefDomain
            and type(ref.position) is int
            and 0 <= ref.position <= _MAX_INTEGER
            for ref in refs
        )
    )


def _validate_shape(
    document: ProjectQueryBlockIRPureDocument,
) -> ProjectQueryBlockIRPureOutcome | None:
    if type(document.format_marker) is not str or type(document.records) is not tuple:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT)
    records = document.records
    if not records or records[0].kind is not _K.HEADER:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_HEADER, 0)
    if records[-1].kind is not _K.END:
        return _reject(
            ProjectQueryBlockIRPureStatus.INVALID_SECTION_ORDER, len(records)
        )
    kinds = tuple(_K)
    positions: list[int] = []
    for record_position, record in enumerate(records):
        if (
            type(record) is not ProjectQueryBlockIRPureRecord
            or type(record.kind) is not ProjectQueryBlockIRRecordKind
        ):
            return _reject(
                ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND, record_position
            )
        schema = _SCHEMAS.get(record.kind)
        if schema is None:
            return _reject(
                ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND, record_position
            )
        positions.append(kinds.index(record.kind))
        if type(record.fields) is not tuple or len(record.fields) != len(schema):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_FIELD, record_position)
        for field_position, (field, expected) in enumerate(
            zip(record.fields, schema, strict=True)
        ):
            if (
                type(field) is not ProjectQueryBlockIRPureField
                or field.key != expected.key
                or type(field.value) is not ProjectQueryBlockIRPureValue
            ):
                return _reject(
                    ProjectQueryBlockIRPureStatus.INVALID_FIELD,
                    record_position,
                    field_position,
                )
            if field.value.tag not in expected.tags or not _value_is_closed(
                field.value
            ):
                return _reject(
                    ProjectQueryBlockIRPureStatus.INVALID_VALUE,
                    record_position,
                    field_position,
                )
            refs = (
                () if field.value.ref is None else (field.value.ref,)
            ) + field.value.refs
            if expected.domain is not None and any(
                ref.domain is not expected.domain for ref in refs
            ):
                return _reject(
                    ProjectQueryBlockIRPureStatus.INVALID_REF,
                    record_position,
                    field_position,
                )
    if positions != sorted(positions):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_SECTION_ORDER)
    if sum(record.kind is _K.HEADER for record in records) != 1:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_HEADER)
    if sum(record.kind is _K.END for record in records) != 1:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_SECTION_ORDER)
    return None


def _field(
    record: ProjectQueryBlockIRPureRecord, key: str
) -> ProjectQueryBlockIRPureValue:
    matches = tuple(field.value for field in record.fields if field.key == key)
    if len(matches) != 1:
        raise ValueError("Validated pure record lost one exact field.")
    return matches[0]


def _ref(
    record: ProjectQueryBlockIRPureRecord, key: str
) -> ProjectQueryBlockIRPortableRef:
    return cast(ProjectQueryBlockIRPortableRef, _field(record, key).ref)


def _refs(
    record: ProjectQueryBlockIRPureRecord, key: str
) -> tuple[ProjectQueryBlockIRPortableRef, ...]:
    return _field(record, key).refs


def _integer(record: ProjectQueryBlockIRPureRecord, key: str) -> int:
    return cast(int, _field(record, key).integer)


def _text(record: ProjectQueryBlockIRPureRecord, key: str) -> str:
    return cast(str, _field(record, key).text)


def _enumeration(record: ProjectQueryBlockIRPureRecord, key: str) -> str:
    return cast(str, _field(record, key).enumeration)


def _enumerations(record: ProjectQueryBlockIRPureRecord, key: str) -> tuple[str, ...]:
    return _field(record, key).enumerations


def _boolean(record: ProjectQueryBlockIRPureRecord, key: str) -> bool:
    return cast(bool, _field(record, key).boolean)


def _records(
    document: ProjectQueryBlockIRPureDocument,
    kind: ProjectQueryBlockIRRecordKind,
) -> tuple[ProjectQueryBlockIRPureRecord, ...]:
    return tuple(record for record in document.records if record.kind is kind)


def _declared_refs(
    document: ProjectQueryBlockIRPureDocument,
) -> tuple[
    dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
    ProjectQueryBlockIRPureOutcome | None,
]:
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord] = {}
    by_domain: dict[
        ProjectQueryBlockIRPortableRefDomain,
        list[ProjectQueryBlockIRPortableRef],
    ] = {domain: [] for domain in _D}
    for record_position, record in enumerate(document.records):
        domain = _DEFINITION_DOMAINS.get(record.kind)
        if domain is None:
            continue
        ref = _ref(record, "ref")
        if ref.domain is not domain or ref in declared:
            return declared, _reject(
                ProjectQueryBlockIRPureStatus.INVALID_REF, record_position, 0
            )
        declared[ref] = record
        by_domain[domain].append(ref)
    for refs in by_domain.values():
        if tuple(ref.position for ref in refs) != tuple(range(len(refs))):
            return declared, _reject(ProjectQueryBlockIRPureStatus.INVALID_COUNT)
    for record_position, record in enumerate(document.records):
        for field_position, field in enumerate(record.fields):
            refs = (() if field.value.ref is None else (field.value.ref,)) + (
                field.value.refs
            )
            for ref in refs:
                if ref not in declared:
                    return declared, _reject(
                        ProjectQueryBlockIRPureStatus.DANGLING_REF,
                        record_position,
                        field_position,
                    )
    return declared, None


def _validate_header_and_counts(
    document: ProjectQueryBlockIRPureDocument,
) -> ProjectQueryBlockIRPureOutcome | None:
    header = document.records[0]
    if (
        document.format_marker != PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
        or _text(header, "format") != PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
    ):
        return _reject(ProjectQueryBlockIRPureStatus.UNKNOWN_FORMAT, 0, 0)
    if _enumeration(header, "verification") != "verified":
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_HEADER, 0, 1)
    boundaries = tuple(
        _integer(header, key)
        for key in (
            "node_start",
            "output_start",
            "slot_start",
            "use_start",
            "node_end",
            "output_end",
            "slot_end",
            "use_end",
        )
    )
    starts = boundaries[:4]
    ends = boundaries[4:]
    if any(start > end for start, end in zip(starts, ends, strict=True)):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_COUNT, 0)
    section_specs = (
        (_K.NODE, "ref", _D.PLAN_NODE, ends[0]),
        (_K.OUTPUT, "ref", _D.OUTPUT_VALUE, ends[1]),
        (_K.INPUT_SLOT, "ref", _D.INPUT_SLOT, ends[2]),
        (_K.USE, "ref", _D.USE, ends[3]),
    )
    for kind, key, domain, end in section_specs:
        refs = tuple(_ref(record, key) for record in _records(document, kind))
        if any(ref.domain is not domain for ref in refs) or tuple(
            ref.position for ref in refs
        ) != tuple(range(end)):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_COUNT, 0)
    nodes = _records(document, _K.NODE)
    if any(
        (_enumeration(record, "stage") == "phase63")
        is not (_ref(record, "ref").position >= starts[0])
        for record in nodes
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_COUNT, 0)
    return None


def _validate_entries(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    owners = _records(document, _K.OWNER_ENTRY)
    owner_refs = tuple(_ref(record, "ref") for record in owners)
    schedule = _refs(document.records[0], "schedule")
    if len(schedule) != len(owner_refs) or set(schedule) != set(owner_refs):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY, 0, 10)
    variants = {"reused", "rebound", "completed", "terminal"}
    terminal_reasons = {
        "semantic_output_non_concrete",
        "active_upstream_ir_non_concrete",
        "active_upstream_row_incompatible",
        "effective_join_input_rebind_unsupported",
    }
    dependencies = _records(document, _K.DEPENDENCY)
    for record in owners:
        owner_ref = _ref(record, "ref")
        variant = _enumeration(record, "variant")
        active_output = _field(record, "active_output")
        active_property = _field(record, "active_property")
        terminal_reason = _field(record, "terminal_reason")
        blocker_kind = _field(record, "blocker_kind")
        relation_fields = tuple(
            _field(record, key)
            for key in (
                "relation_input_owner",
                "relation_input_use",
                "compatibility",
            )
        )
        if (
            variant not in variants
            or _enumeration(record, "namespace") != "relation"
            or _enumeration(record, "declaration_kind")
            not in {"source", "table", "query"}
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        if variant == "terminal":
            if (
                active_output.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or active_property.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or any(
                    value.tag is not ProjectQueryBlockIRPureTag.ABSENT
                    for value in relation_fields
                )
                or terminal_reason.tag is not ProjectQueryBlockIRPureTag.ENUMERATION
                or terminal_reason.enumeration not in terminal_reasons
                or blocker_kind.tag is not ProjectQueryBlockIRPureTag.ENUMERATION
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
            reason = cast(str, terminal_reason.enumeration)
            blocker_entry = _field(record, "blocker_entry")
            blocker_uses = _field(record, "blocker_uses")
            if reason == "semantic_output_non_concrete":
                valid_blocker = (
                    blocker_entry.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_uses.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_kind.enumeration
                    in {
                        "ProjectEffectiveOutputTerminal",
                        "ProjectEffectiveOutputCompletionTerminal",
                    }
                )
            elif reason == "active_upstream_ir_non_concrete":
                valid_blocker = (
                    blocker_entry.tag is ProjectQueryBlockIRPureTag.REF
                    and blocker_uses.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_kind.enumeration == "ProjectIRQueryBlockTerminal"
                    and _enumeration(
                        declared[
                            cast(
                                ProjectQueryBlockIRPortableRef,
                                blocker_entry.ref,
                            )
                        ],
                        "variant",
                    )
                    == "terminal"
                )
            elif reason == "active_upstream_row_incompatible":
                valid_blocker = (
                    blocker_entry.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_uses.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_kind.enumeration
                    == "ProjectIRQueryBlockRowCompatibility"
                )
            else:
                valid_blocker = (
                    blocker_entry.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_uses.tag is ProjectQueryBlockIRPureTag.REFS
                    and blocker_kind.enumeration == "tuple"
                    and all(
                        _enumeration(declared[ref], "kind") == "join_input"
                        for ref in blocker_uses.refs
                    )
                )
            if not valid_blocker:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
        else:
            if (
                active_output.tag is not ProjectQueryBlockIRPureTag.REF
                or active_property.tag is not ProjectQueryBlockIRPureTag.REF
                or terminal_reason.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or blocker_kind.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or _field(record, "blocker_entry").tag
                is not ProjectQueryBlockIRPureTag.ABSENT
                or _field(record, "blocker_uses").tag
                is not ProjectQueryBlockIRPureTag.ABSENT
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
            property_record = declared[
                cast(ProjectQueryBlockIRPortableRef, active_property.ref)
            ]
            output_ref = cast(ProjectQueryBlockIRPortableRef, active_output.ref)
            if (
                _ref(property_record, "owner") != owner_ref
                or _ref(property_record, "output") != output_ref
                or _field(declared[output_ref], "row_field").tag
                is not ProjectQueryBlockIRPureTag.ABSENT
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
        present_relation = tuple(
            value.tag is not ProjectQueryBlockIRPureTag.ABSENT
            for value in relation_fields
        )
        if any(present_relation) and not all(present_relation):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        if all(present_relation):
            upstream = cast(ProjectQueryBlockIRPortableRef, relation_fields[0].ref)
            use_ref = cast(ProjectQueryBlockIRPortableRef, relation_fields[1].ref)
            if relation_fields[2].enumeration != "satisfied":
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
            upstream_output = _field(declared[upstream], "active_output").ref
            if (
                upstream_output is None
                or _ref(declared[use_ref], "output") != upstream_output
                or _field(declared[use_ref], "owner").ref != owner_ref
                or not any(
                    _ref(dependency, "consumer") == owner_ref
                    and _ref(dependency, "target") == upstream
                    for dependency in dependencies
                )
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
    by_consumer: dict[ProjectQueryBlockIRPortableRef, list[int]] = {}
    for dependency in dependencies:
        if _enumeration(dependency, "evidence_kind") not in {
            "ProjectResolvedModuleRelationReference",
            "ProjectRelationBindingOccurrence",
        }:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        by_consumer.setdefault(_ref(dependency, "consumer"), []).append(
            _integer(dependency, "ordinal")
        )
    if any(
        values != sorted(values) or len(values) != len(set(values))
        for values in by_consumer.values()
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
    return None


def _validate_topology(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    if any(
        _enumeration(node, "stage") not in {"phase61", "phase62", "phase63"}
        for node in _records(document, _K.NODE)
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    if any(
        _enumeration(output, "kind")
        not in {
            "phase61_output",
            "phase62_output",
            "relation_row",
            "query_block_row",
            "query_block_scalar",
            "rebound_auxiliary",
        }
        for output in _records(document, _K.OUTPUT)
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    if any(
        _enumeration(use, "kind")
        not in {
            "join_input",
            "operator_flow",
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
        }
        for use in _records(document, _K.USE)
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    for output in _records(document, _K.OUTPUT):
        if _ref(output, "producer") not in declared:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    for slot in _records(document, _K.INPUT_SLOT):
        if _ref(slot, "consumer") not in declared:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    for use in _records(document, _K.USE):
        output = declared[_ref(use, "output")]
        slot = declared[_ref(use, "slot")]
        if output.kind is not _K.OUTPUT or slot.kind is not _K.INPUT_SLOT:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    return None


def _grouped_by_owner(
    records: tuple[ProjectQueryBlockIRPureRecord, ...],
) -> dict[ProjectQueryBlockIRPortableRef, list[ProjectQueryBlockIRPureRecord]]:
    grouped: dict[
        ProjectQueryBlockIRPortableRef, list[ProjectQueryBlockIRPureRecord]
    ] = {}
    for record in records:
        grouped.setdefault(_ref(record, "owner"), []).append(record)
    return grouped


def _validate_operators(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    operators = _records(document, _K.OPERATOR)
    allowed = {
        "relation_input",
        "row_filter",
        "group_aggregate",
        "result_filter",
        "window_evaluation",
        "qualify",
        "final_projection",
        "relation_ordering",
        "limit",
    }
    phase63_nodes = {
        _ref(node, "ref")
        for node in _records(document, _K.NODE)
        if _enumeration(node, "stage") == "phase63"
    }
    if {_ref(operator, "node") for operator in operators} != phase63_nodes:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    for operator in operators:
        node_ref = _ref(operator, "node")
        output = declared[_ref(operator, "row_output")]
        if (
            _enumeration(operator, "kind") not in allowed
            or _enumeration(operator, "provenance")
            not in {"joined", "no_join_replay", "rebound_historical"}
            or _ref(output, "producer") != node_ref
            or _field(output, "row_field").tag is not ProjectQueryBlockIRPureTag.ABSENT
            or _field(output, "owner").ref != _ref(operator, "owner")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        if _enumeration(operator, "kind") != "window_evaluation" and (
            _integer(operator, "selected_count") != 0
            or _integer(operator, "hidden_count") != 0
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    for values in _grouped_by_owner(operators).values():
        if tuple(_integer(record, "ordinal") for record in values) != tuple(
            range(len(values))
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        kinds = tuple(_enumeration(record, "kind") for record in values)
        for position, kind in enumerate(kinds):
            if kind != "qualify":
                continue
            if position + 1 >= len(kinds) or kinds[position + 1] != "final_projection":
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
            window_positions = tuple(
                index
                for index, value in enumerate(kinds)
                if value == "window_evaluation"
            )
            if window_positions and window_positions != (position - 1,):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    return None


def _local_refs(
    document: ProjectQueryBlockIRPureDocument,
    kind: ProjectQueryBlockIRRecordKind,
    property_ref: ProjectQueryBlockIRPortableRef,
) -> tuple[ProjectQueryBlockIRPortableRef, ...]:
    return tuple(
        _ref(record, "ref")
        for record in _records(document, kind)
        if _ref(record, "property") == property_ref
    )


def _validate_properties(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    properties = _records(document, _K.RELATIONAL_PROPERTY)
    for values in _grouped_by_owner(properties).values():
        if tuple(_integer(record, "ordinal") for record in values) != tuple(
            range(len(values))
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
    for properties_record in properties:
        property_ref = _ref(properties_record, "ref")
        owner_ref = _ref(properties_record, "owner")
        output_ref = _ref(properties_record, "output")
        if (
            _field(declared[output_ref], "owner").ref != owner_ref
            or _enumeration(properties_record, "multiplicity") != "bag"
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        expected = (
            (_K.ROW_FIELD, "fields"),
            (_K.VALUE_CLASS, "value_classes"),
            (_K.CANDIDATE_KEY, "candidate_keys"),
            (_K.VALUE_FD, "value_fds"),
        )
        for kind, key in expected:
            if _refs(properties_record, key) != _local_refs(
                document, kind, property_ref
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        if _refs(properties_record, "fd_index_universe") != _refs(
            properties_record, "value_classes"
        ) or _refs(properties_record, "fd_index_facts") != _refs(
            properties_record, "value_fds"
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        fields = _refs(properties_record, "fields")
        field_records = tuple(declared[ref] for ref in fields)
        if tuple(
            _integer(record, "field_position") for record in field_records
        ) != tuple(range(len(field_records))):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        for field_record in field_records:
            if (
                _enumeration(field_record, "nullability")
                not in {"non_null", "nullable", "unknown"}
                or _enumeration(field_record, "provenance")
                not in {
                    "source_field",
                    "direct_projection",
                    "derived_expression",
                    "let_derived",
                    "expression",
                    "aggregate",
                    "unknown",
                    "absent",
                }
                or _enumeration(field_record, "semantic_source_kind")
                not in {
                    "ProjectIROutputFieldOccurrence",
                    "ProjectJoinedRowFieldSemantics",
                    "ProjectJoinedStageOutputOccurrence",
                    "ProjectSelectedWindowResultBinding",
                    "ProjectNoJoinGroupedOutput",
                    "ProjectModuleWindowOutputFact",
                    "ProjectCompletedOutputField",
                    "ProjectIRRowField",
                    "ProjectIRStageRowField",
                }
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            if (
                _refs(field_record, "nulling_joins")
                and _enumeration(field_record, "nullability") != "nullable"
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            final_values = tuple(
                _field(field_record, key)
                for key in ("final_owner", "final_kind", "final_position", "final_name")
            )
            present = tuple(
                value.tag is not ProjectQueryBlockIRPureTag.ABSENT
                for value in final_values
            )
            if any(present) and not all(present):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            if all(present):
                if (
                    final_values[0].ref != owner_ref
                    or final_values[1].enumeration
                    not in {"shape_field", "source_field", "relation_output"}
                    or final_values[2].integer
                    != _integer(field_record, "field_position")
                    or final_values[3].text != _text(field_record, "name")
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        for class_ref in _refs(properties_record, "value_classes"):
            value_class = declared[class_ref]
            if _ref(value_class, "property") != property_ref or any(
                member not in fields for member in _refs(value_class, "members")
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        classes = _refs(properties_record, "value_classes")
        for key in ("candidate_keys", "value_fds"):
            for item_ref in _refs(properties_record, key):
                item = declared[item_ref]
                if (
                    _ref(item, "property") != property_ref
                    or _enumeration(item, "strength") not in {"strict", "lax"}
                    or any(ref not in classes for ref in _refs(item, "determinants"))
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
                if item.kind is _K.VALUE_FD and any(
                    ref not in classes for ref in _refs(item, "dependents")
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        ordering_kind = _enumeration(properties_record, "ordering_kind")
        directions = _field(properties_record, "order_directions")
        if (ordering_kind == "absent") is not (
            directions.tag is ProjectQueryBlockIRPureTag.ABSENT
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        if ordering_kind not in {"absent", "historical", "relation"}:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        if any(
            direction not in {"asc", "desc"}
            for direction in _enumerations(properties_record, "order_directions")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        if _enumeration(properties_record, "grain_state") not in {
            "factorized",
            "global",
        }:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        effects = (
            _enumeration(properties_record, "determinism"),
            _enumeration(properties_record, "error_behavior"),
            _enumeration(properties_record, "side_effects"),
            _enumeration(properties_record, "evaluation_count"),
        )
        if effects != ("unknown", "unknown", "unknown", "unknown"):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
    return None


def _validate_grain(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    factors = _records(document, _K.GRAIN_FACTOR)
    for factor in factors:
        property_ref = _ref(factor, "property")
        properties = declared[property_ref]
        if _ref(factor, "ref") not in _refs(properties, "grain_factors"):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        active = _boolean(factor, "active")
        if active is not (
            _ref(factor, "ref") in _refs(properties, "active_grain_factors")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        use_kind = _enumeration(factor, "use_kind")
        introduction = _field(factor, "introduction_use")
        factor_kind = _enumeration(factor, "kind")
        if (use_kind == "join") is not (
            introduction.tag is ProjectQueryBlockIRPureTag.REF
        ) or use_kind not in {"direct", "join"}:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        if (
            factor_kind not in {"source_domain", "group_domain"}
            or _field(factor, "owner").tag is not ProjectQueryBlockIRPureTag.REF
            or (factor_kind == "group_domain")
            is not (_field(factor, "operator").tag is ProjectQueryBlockIRPureTag.REF)
            or (
                use_kind == "direct"
                and _field(factor, "nulling_joins").tag
                is not ProjectQueryBlockIRPureTag.ABSENT
            )
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
    for dependency in _records(document, _K.GRAIN_DEPENDENCY):
        property_ref = _ref(dependency, "property")
        local = set(_refs(declared[property_ref], "grain_factors"))
        determinants = _refs(dependency, "determinants")
        dependents = _refs(dependency, "dependents")
        if (
            not determinants
            or not dependents
            or not set((*determinants, *dependents)) <= local
            or set(determinants) & set(dependents)
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
    for origin in _records(document, _K.GRAIN_ORIGIN):
        kind = _enumeration(origin, "kind")
        factor_refs = _refs(origin, "factors")
        if kind == "grouped_result":
            if not factor_refs or any(
                _enumeration(declared[ref], "kind") != "group_domain"
                or _field(declared[ref], "operator").ref != _ref(origin, "operator")
                for ref in factor_refs
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        elif kind == "global_aggregate":
            if factor_refs:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        else:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        matching_operators = tuple(
            operator
            for operator in _records(document, _K.OPERATOR)
            if _ref(operator, "node") == _ref(origin, "operator")
            and _enumeration(operator, "kind") == "group_aggregate"
        )
        if len(matching_operators) != 1:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
    all_origins = tuple(
        _ref(origin, "ref") for origin in _records(document, _K.GRAIN_ORIGIN)
    )
    for properties in _records(document, _K.RELATIONAL_PROPERTY):
        factor_refs = _refs(properties, "grain_factors")
        if any(
            _ref(declared[ref], "property") != _ref(properties, "ref")
            for ref in factor_refs
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        if _enumeration(properties, "grain_state") == "global" and _refs(
            properties, "active_grain_factors"
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        origins = _refs(properties, "grain_origins")
        if origins and origins != all_origins:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
    return None


def _validate_windows(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    selected = _records(document, _K.WINDOW_SELECTED)
    hidden = _records(document, _K.WINDOW_HIDDEN)
    for operator in _records(document, _K.OPERATOR):
        operator_ref = _ref(operator, "ref")
        selected_for = tuple(
            record for record in selected if _ref(record, "operator") == operator_ref
        )
        hidden_for = tuple(
            record for record in hidden if _ref(record, "operator") == operator_ref
        )
        if (
            len(selected_for) != _integer(operator, "selected_count")
            or len(hidden_for) != _integer(operator, "hidden_count")
            or tuple(_integer(record, "ordinal") for record in selected_for)
            != tuple(range(len(selected_for)))
            or tuple(_integer(record, "ordinal") for record in hidden_for)
            != tuple(range(len(hidden_for)))
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
        if (selected_for or hidden_for) and _enumeration(
            operator, "kind"
        ) != "window_evaluation":
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
    for record in selected:
        owner_ref = _ref(record, "owner")
        output_ref = _ref(record, "output")
        row_field_ref = _ref(record, "row_field")
        output = declared[output_ref]
        row_field = declared[row_field_ref]
        if (
            _enumeration(output, "kind") != "query_block_scalar"
            or _enumeration(record, "evidence_kind")
            not in {
                "ProjectConcreteWindowComputation",
                "ProjectModuleWindowOutputFact",
            }
            or _field(output, "owner").ref != owner_ref
            or _field(output, "row_field").ref != row_field_ref
            or _ref(declared[_ref(row_field, "property")], "owner") != owner_ref
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
        singleton = tuple(
            value_class
            for value_class in _records(document, _K.VALUE_CLASS)
            if _ref(value_class, "property") == _ref(row_field, "property")
            and _refs(value_class, "members") == (row_field_ref,)
        )
        if not singleton:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
    if any(
        _enumeration(record, "evidence_kind")
        not in {
            "ProjectConcreteWindowComputation",
            "ProjectNoJoinHiddenWindowComputation",
        }
        for record in hidden
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
    selected_outputs = tuple(_ref(record, "output") for record in selected)
    for output in _records(document, _K.OUTPUT):
        if _enumeration(output, "kind") != "query_block_scalar":
            continue
        row_field = declared[
            cast(ProjectQueryBlockIRPortableRef, _field(output, "row_field").ref)
        ]
        final = _field(row_field, "final_owner").tag is ProjectQueryBlockIRPureTag.REF
        if (_ref(output, "ref") in selected_outputs) is final:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_WINDOW)
    return None


def _graph(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> (
    tuple[
        tuple[ProjectQueryBlockIRPortableRef, ...],
        tuple[tuple[int, ...], ...],
        tuple[ProjectQueryBlockIRPortableRef, ...],
        tuple[tuple[ProjectQueryBlockIRPortableRef, ...], ...],
    ]
    | None
):
    nodes = tuple(_ref(record, "ref") for record in _records(document, _K.NODE))
    positions = {ref: position for position, ref in enumerate(nodes)}
    successors: list[list[int]] = [[] for _ in nodes]
    indegree = [0] * len(nodes)
    for use in _records(document, _K.USE):
        output = declared[_ref(use, "output")]
        slot = declared[_ref(use, "slot")]
        producer = positions.get(_ref(output, "producer"))
        consumer = positions.get(_ref(slot, "consumer"))
        if producer is None or consumer is None:
            return None
        successors[producer].append(consumer)
        indegree[consumer] += 1
    ready: list[tuple[int, int]] = []
    for position, (ref, degree) in enumerate(zip(nodes, indegree, strict=True)):
        if degree == 0:
            heappush(ready, (ref.position, position))
    order: list[ProjectQueryBlockIRPortableRef] = []
    while ready:
        _, position = heappop(ready)
        order.append(nodes[position])
        for target in successors[position]:
            indegree[target] -= 1
            if indegree[target] == 0:
                heappush(ready, (nodes[target].position, target))
    if len(order) != len(nodes):
        return None
    reachability: list[tuple[ProjectQueryBlockIRPortableRef, ...]] = []
    for source_position in range(len(nodes)):
        seen: set[int] = set()
        pending = list(successors[source_position])
        while pending:
            position = pending.pop()
            if position in seen:
                continue
            seen.add(position)
            pending.extend(successors[position])
        reachability.append(
            tuple(node for position, node in enumerate(nodes) if position in seen)
        )
    return (
        nodes,
        tuple(tuple(items) for items in successors),
        tuple(order),
        tuple(reachability),
    )


def _validate_analysis(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    outputs = _records(document, _K.OUTPUT)
    uses = _records(document, _K.USE)
    reverse = _records(document, _K.ANALYSIS_REVERSE_USE)
    if len(reverse) != len(outputs):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS)
    for output, analysis in zip(outputs, reverse, strict=True):
        output_ref = _ref(output, "ref")
        expected_uses = tuple(
            _ref(use, "ref") for use in uses if _ref(use, "output") == output_ref
        )
        if (
            _ref(analysis, "output") != output_ref
            or _refs(analysis, "uses") != expected_uses
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS)
    graph = _graph(document, declared)
    if graph is None:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS)
    nodes, _, expected_order, expected_reachability = graph
    topological = _records(document, _K.ANALYSIS_TOPOLOGICAL)
    if tuple(
        (_integer(record, "position"), _ref(record, "node")) for record in topological
    ) != tuple(enumerate(expected_order)):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS)
    reachability = _records(document, _K.ANALYSIS_REACHABILITY)
    if tuple(
        (_ref(record, "source"), _refs(record, "reachable")) for record in reachability
    ) != tuple(zip(nodes, expected_reachability, strict=True)):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS)
    return None


_ESCAPES = {
    "\\": "\\\\",
    "\t": "\\t",
    "\n": "\\n",
    "\r": "\\r",
    ",": "\\,",
    ":": "\\:",
    "=": "\\=",
}


def _escape_text(value: str) -> str:
    escaped: list[str] = []
    for character in value:
        replacement = _ESCAPES.get(character)
        if replacement is not None:
            escaped.append(replacement)
        elif ord(character) < 0x20 or 0x7F <= ord(character) <= 0x9F:
            escaped.append(f"\\x{ord(character):02x}")
        elif "\ud800" <= character <= "\udfff":
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def _encode_ref(ref: ProjectQueryBlockIRPortableRef) -> str:
    return f"{ref.domain.value}:{ref.position}"


def _encode_value(value: ProjectQueryBlockIRPureValue) -> str:
    if value.tag is ProjectQueryBlockIRPureTag.ABSENT:
        return "n:"
    if value.tag is ProjectQueryBlockIRPureTag.TEXT:
        return f"t:{_escape_text(cast(str, value.text))}"
    if value.tag is ProjectQueryBlockIRPureTag.INTEGER:
        return f"i:{value.integer}"
    if value.tag is ProjectQueryBlockIRPureTag.BOOLEAN:
        return "b:1" if value.boolean else "b:0"
    if value.tag is ProjectQueryBlockIRPureTag.ENUMERATION:
        return f"e:{_escape_text(cast(str, value.enumeration))}"
    if value.tag is ProjectQueryBlockIRPureTag.REF:
        return f"r:{_encode_ref(cast(ProjectQueryBlockIRPortableRef, value.ref))}"
    if value.tag is ProjectQueryBlockIRPureTag.REFS:
        return "q:" + ",".join(_encode_ref(ref) for ref in value.refs)
    if value.tag is ProjectQueryBlockIRPureTag.TEXTS:
        return "s:" + ",".join(_escape_text(text) for text in value.texts)
    if value.tag is ProjectQueryBlockIRPureTag.INTEGERS:
        return "j:" + ",".join(str(integer) for integer in value.integers)
    return "z:" + ",".join(_escape_text(item) for item in value.enumerations)


def _encode_document(document: ProjectQueryBlockIRPureDocument) -> bytes:
    lines = tuple(
        record.kind.value
        + "".join(
            f"\t{field.key}={_encode_value(field.value)}" for field in record.fields
        )
        for record in document.records
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def evaluate_project_query_block_ir_document(
    document: object,
) -> ProjectQueryBlockIRPureOutcome:
    """Validate and encode one portable document without ambient state."""

    if type(document) is not ProjectQueryBlockIRPureDocument:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT)
    try:
        shape = _validate_shape(document)
        if shape is not None:
            return shape
        header = _validate_header_and_counts(document)
        if header is not None:
            return header
        declared, rejection = _declared_refs(document)
        if rejection is not None:
            return rejection
        for validation in (
            _validate_entries,
            _validate_topology,
            _validate_operators,
            _validate_properties,
            _validate_grain,
            _validate_windows,
            _validate_analysis,
        ):
            rejection = validation(document, declared)
            if rejection is not None:
                return rejection
        return ProjectQueryBlockIRPureOutcome(
            status=ProjectQueryBlockIRPureStatus.OK,
            canonical_bytes=_encode_document(document),
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT)
