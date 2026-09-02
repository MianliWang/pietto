"""Pure portable Phase-62 inspection document and canonical evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from heapq import heappop, heappush
from typing import Mapping, cast

__all__: tuple[str, ...] = ()

PROJECT_PHASE62_INSPECTION_FORMAT = "pietto.phase62-inspection.v1"
_MAX_INTEGER = (1 << 63) - 1


class ProjectPhase62PortableRefDomain(StrEnum):
    PLAN_NODE = "plan_node"
    OUTPUT_VALUE = "output_value"
    INPUT_SLOT = "input_slot"
    USE = "use"
    RELATIONSHIP = "relationship"
    RELATIONSHIP_DIRECTION = "relationship_direction"
    CONDITION = "condition"
    CORRESPONDENCE = "correspondence"
    MATCH_GUARANTEE = "match_guarantee"
    BINDING = "binding"
    JOIN_USE = "join_use"
    TRAVERSAL_STEP = "traversal_step"
    RELATIONAL_OUTPUT = "relational_output"
    RELATIONAL_FIELD = "relational_field"
    VALUE_CLASS = "value_class"
    CANDIDATE_KEY = "candidate_key"
    VALUE_FD = "value_fd"
    GRAIN = "grain"
    GRAIN_FACTOR = "grain_factor"
    GRAIN_DEPENDENCY = "grain_dependency"
    JOIN_REGION = "join_region"
    BINARY_JOIN = "binary_join"
    JOIN_MATCH = "join_match"
    JOINED_FIELD = "joined_field"
    NULLING = "nulling"
    AGGREGATE_FACT = "aggregate_fact"
    FACT_LOCALITY = "fact_locality"
    MULTIPLICITY_EXPOSURE = "multiplicity_exposure"
    ACTUAL_GRAIN_CANDIDATE = "actual_grain_candidate"
    COMMON_GRAIN = "common_grain"
    ALIGNMENT = "alignment"
    CHASM = "chasm"
    NON_CONCRETE = "non_concrete"
    ANALYSIS_ENTRY = "analysis_entry"


class ProjectPhase62PureTag(StrEnum):
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


class ProjectPhase62RecordKind(StrEnum):
    HEADER = "header"
    SUMMARY = "summary"
    PROJECT_NODE = "project_node"
    PROJECT_OUTPUT = "project_output"
    PROJECT_SLOT = "project_slot"
    PROJECT_USE = "project_use"
    RELATIONSHIP = "relationship"
    RELATIONSHIP_DIRECTION = "relationship_direction"
    CONDITION = "condition"
    CORRESPONDENCE = "correspondence"
    MATCH_GUARANTEE = "match_guarantee"
    BINDING = "binding"
    JOIN_USE = "join_use"
    TRAVERSAL_STEP = "traversal_step"
    RELATIONAL_OUTPUT = "relational_output"
    RELATIONAL_FIELD = "relational_field"
    VALUE_CLASS = "value_class"
    CANDIDATE_KEY = "candidate_key"
    VALUE_FD = "value_fd"
    GRAIN = "grain"
    GRAIN_FACTOR = "grain_factor"
    GRAIN_DEPENDENCY = "grain_dependency"
    JOIN_REGION = "join_region"
    BINARY_JOIN = "binary_join"
    JOIN_MATCH = "join_match"
    JOINED_FIELD = "joined_field"
    NULLING = "nulling"
    AGGREGATE_FACT = "aggregate_fact"
    FACT_LOCALITY = "fact_locality"
    MULTIPLICITY_EXPOSURE = "multiplicity_exposure"
    ACTUAL_GRAIN_CANDIDATE = "actual_grain_candidate"
    COMMON_GRAIN = "common_grain"
    ALIGNMENT = "alignment"
    CHASM = "chasm"
    NON_CONCRETE = "non_concrete"
    ANALYSIS_REVERSE_USE = "analysis_reverse_use"
    ANALYSIS_TOPOLOGICAL = "analysis_topological"
    ANALYSIS_NULLING = "analysis_nulling"
    ANALYSIS_FACT_LOCALITY = "analysis_fact_locality"
    ANALYSIS_ALIGNMENT = "analysis_alignment"
    END = "end"


class ProjectPhase62PureStatus(StrEnum):
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
    INVALID_RELATIONSHIP = "invalid_relationship"
    INVALID_JOIN = "invalid_join"
    INVALID_RELATIONAL_PROPERTY = "invalid_relational_property"
    INVALID_MULTIFACT = "invalid_multifact"
    INVALID_ANALYSIS = "invalid_analysis"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PortableRef:
    domain: ProjectPhase62PortableRefDomain
    position: int

    def __post_init__(self) -> None:
        if type(self.domain) is not ProjectPhase62PortableRefDomain:
            raise TypeError("Portable ref requires one closed domain.")
        if type(self.position) is not int or not 0 <= self.position <= _MAX_INTEGER:
            raise ValueError("Portable ref position must be a bounded integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PureValue:
    tag: ProjectPhase62PureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None
    enumeration: str | None = None
    ref: ProjectPhase62PortableRef | None = None
    refs: tuple[ProjectPhase62PortableRef, ...] = ()
    texts: tuple[str, ...] = ()
    integers: tuple[int, ...] = ()
    enumerations: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if type(self.tag) is not ProjectPhase62PureTag:
            raise TypeError("Pure value requires one closed tag.")
        populated = {
            ProjectPhase62PureTag.TEXT: self.text is not None,
            ProjectPhase62PureTag.INTEGER: self.integer is not None,
            ProjectPhase62PureTag.BOOLEAN: self.boolean is not None,
            ProjectPhase62PureTag.ENUMERATION: self.enumeration is not None,
            ProjectPhase62PureTag.REF: self.ref is not None,
            ProjectPhase62PureTag.REFS: bool(self.refs),
            ProjectPhase62PureTag.TEXTS: bool(self.texts),
            ProjectPhase62PureTag.INTEGERS: bool(self.integers),
            ProjectPhase62PureTag.ENUMERATIONS: bool(self.enumerations),
            ProjectPhase62PureTag.ABSENT: True,
        }[self.tag]
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
        if (
            not populated
            or (self.tag is ProjectPhase62PureTag.ABSENT and any(payloads))
            or (self.tag is not ProjectPhase62PureTag.ABSENT and sum(payloads) != 1)
        ):
            raise ValueError("Pure value tag and payload disagree.")


PROJECT_PHASE62_PURE_ABSENT = ProjectPhase62PureValue(tag=ProjectPhase62PureTag.ABSENT)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PureField:
    key: str
    value: ProjectPhase62PureValue

    def __post_init__(self) -> None:
        if type(self.key) is not str or not self.key:
            raise ValueError("Pure field key must be non-empty text.")
        if type(self.value) is not ProjectPhase62PureValue:
            raise TypeError("Pure field requires an exact value.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PureRecord:
    kind: ProjectPhase62RecordKind
    fields: tuple[ProjectPhase62PureField, ...]

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectPhase62RecordKind:
            raise TypeError("Pure record requires one closed kind.")
        if type(self.fields) is not tuple or any(
            type(item) is not ProjectPhase62PureField for item in self.fields
        ):
            raise TypeError("Pure record requires an exact field tuple.")
        keys = tuple(item.key for item in self.fields)
        if len(set(keys)) != len(keys):
            raise ValueError("Pure record fields cannot repeat keys.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PureDocument:
    format_marker: str
    records: tuple[ProjectPhase62PureRecord, ...]

    def __post_init__(self) -> None:
        if type(self.format_marker) is not str:
            raise TypeError("Pure document marker must be text.")
        if type(self.records) is not tuple or any(
            type(item) is not ProjectPhase62PureRecord for item in self.records
        ):
            raise TypeError("Pure document requires an exact record tuple.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPhase62PureOutcome:
    status: ProjectPhase62PureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.status) is not ProjectPhase62PureStatus:
            raise TypeError("Pure outcome requires one closed status.")
        if self.status is ProjectPhase62PureStatus.OK:
            if type(self.canonical_bytes) is not bytes:
                raise ValueError("OK outcome requires canonical bytes.")
            if self.record_position is not None or self.field_position is not None:
                raise ValueError("OK outcome cannot retain a rejection coordinate.")
        elif self.canonical_bytes is not None:
            raise ValueError("Rejected outcome cannot expose bytes.")
        for value in (self.record_position, self.field_position):
            if value is not None and (type(value) is not int or value < 0):
                raise ValueError("Rejection coordinates must be non-negative.")


def project_phase62_pure_text(value: str) -> ProjectPhase62PureValue:
    return ProjectPhase62PureValue(tag=ProjectPhase62PureTag.TEXT, text=value)


def project_phase62_pure_integer(value: int) -> ProjectPhase62PureValue:
    return ProjectPhase62PureValue(tag=ProjectPhase62PureTag.INTEGER, integer=value)


def project_phase62_pure_boolean(value: bool) -> ProjectPhase62PureValue:
    return ProjectPhase62PureValue(tag=ProjectPhase62PureTag.BOOLEAN, boolean=value)


def project_phase62_pure_enumeration(value: str) -> ProjectPhase62PureValue:
    return ProjectPhase62PureValue(
        tag=ProjectPhase62PureTag.ENUMERATION,
        enumeration=value,
    )


def project_phase62_pure_ref(
    value: ProjectPhase62PortableRef,
) -> ProjectPhase62PureValue:
    return ProjectPhase62PureValue(tag=ProjectPhase62PureTag.REF, ref=value)


def project_phase62_pure_refs(
    values: tuple[ProjectPhase62PortableRef, ...],
) -> ProjectPhase62PureValue:
    return (
        ProjectPhase62PureValue(tag=ProjectPhase62PureTag.REFS, refs=values)
        if values
        else PROJECT_PHASE62_PURE_ABSENT
    )


def project_phase62_pure_texts(values: tuple[str, ...]) -> ProjectPhase62PureValue:
    return (
        ProjectPhase62PureValue(tag=ProjectPhase62PureTag.TEXTS, texts=values)
        if values
        else PROJECT_PHASE62_PURE_ABSENT
    )


def project_phase62_pure_integers(
    values: tuple[int, ...],
) -> ProjectPhase62PureValue:
    return (
        ProjectPhase62PureValue(tag=ProjectPhase62PureTag.INTEGERS, integers=values)
        if values
        else PROJECT_PHASE62_PURE_ABSENT
    )


def project_phase62_pure_enumerations(
    values: tuple[str, ...],
) -> ProjectPhase62PureValue:
    return (
        ProjectPhase62PureValue(
            tag=ProjectPhase62PureTag.ENUMERATIONS,
            enumerations=values,
        )
        if values
        else PROJECT_PHASE62_PURE_ABSENT
    )


@dataclass(frozen=True, slots=True)
class _FieldSpec:
    key: str
    tags: tuple[ProjectPhase62PureTag, ...]
    domains: tuple[ProjectPhase62PortableRefDomain, ...] = ()


def _spec(
    key: str,
    tag: ProjectPhase62PureTag,
    domain: ProjectPhase62PortableRefDomain | None = None,
    *,
    optional: bool = False,
) -> _FieldSpec:
    return _FieldSpec(
        key=key,
        tags=(tag, ProjectPhase62PureTag.ABSENT) if optional else (tag,),
        domains=() if domain is None else (domain,),
    )


_REF = ProjectPhase62PureTag.REF
_REFS = ProjectPhase62PureTag.REFS
_TEXT = ProjectPhase62PureTag.TEXT
_TEXTS = ProjectPhase62PureTag.TEXTS
_INTEGER = ProjectPhase62PureTag.INTEGER
_INTEGERS = ProjectPhase62PureTag.INTEGERS
_BOOLEAN = ProjectPhase62PureTag.BOOLEAN
_ENUM = ProjectPhase62PureTag.ENUMERATION
_ENUMS = ProjectPhase62PureTag.ENUMERATIONS

_SCHEMAS: dict[ProjectPhase62RecordKind, tuple[_FieldSpec, ...]] = {
    ProjectPhase62RecordKind.HEADER: (
        _spec("format", _TEXT),
        _spec("verification", _ENUM),
        _spec("base_verification", _ENUM),
    ),
    ProjectPhase62RecordKind.SUMMARY: (
        _spec("names", _TEXTS),
        _spec("counts", _INTEGERS),
    ),
    ProjectPhase62RecordKind.PROJECT_NODE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
    ),
    ProjectPhase62RecordKind.PROJECT_OUTPUT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.OUTPUT_VALUE),
        _spec("producer", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
    ),
    ProjectPhase62RecordKind.PROJECT_SLOT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.INPUT_SLOT),
        _spec("consumer", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
        _spec("ordinal", _INTEGER),
    ),
    ProjectPhase62RecordKind.PROJECT_USE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.USE),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.OUTPUT_VALUE),
        _spec("slot", _REF, ProjectPhase62PortableRefDomain.INPUT_SLOT),
    ),
    ProjectPhase62RecordKind.RELATIONSHIP: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.RELATIONSHIP),
        _spec("module_path", _TEXT),
        _spec("module_position", _INTEGER),
        _spec("declaration_position", _INTEGER),
        _spec("source_position", _INTEGER),
        _spec("name", _TEXT),
    ),
    ProjectPhase62RecordKind.RELATIONSHIP_DIRECTION: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION),
        _spec("relationship", _REF, ProjectPhase62PortableRefDomain.RELATIONSHIP),
        _spec("source_endpoint", _INTEGER),
        _spec("target_endpoint", _INTEGER),
        _spec("source_role", _TEXT),
        _spec("target_role", _TEXT),
        _spec("source_relation", _TEXT),
        _spec("target_relation", _TEXT),
    ),
    ProjectPhase62RecordKind.CONDITION: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.CONDITION),
        _spec("relationship", _REF, ProjectPhase62PortableRefDomain.RELATIONSHIP),
        _spec(
            "correspondences",
            _REFS,
            ProjectPhase62PortableRefDomain.CORRESPONDENCE,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.CORRESPONDENCE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.CORRESPONDENCE),
        _spec("condition", _REF, ProjectPhase62PortableRefDomain.CONDITION),
        _spec("position", _INTEGER),
        _spec("left_endpoint", _INTEGER),
        _spec("right_endpoint", _INTEGER),
        _spec("left_field", _TEXT),
        _spec("right_field", _TEXT),
    ),
    ProjectPhase62RecordKind.MATCH_GUARANTEE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.MATCH_GUARANTEE),
        _spec(
            "direction", _REF, ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION
        ),
        _spec("source_output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("target_output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("minimum", _ENUM),
        _spec("maximum", _ENUM),
    ),
    ProjectPhase62RecordKind.BINDING: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.BINDING),
        _spec("owner_module", _TEXT),
        _spec("owner_module_position", _INTEGER),
        _spec("owner_namespace", _ENUM),
        _spec("owner_kind", _ENUM),
        _spec("owner_name", _TEXT),
        _spec("owner_declaration_position", _INTEGER),
        _spec("binding_position", _INTEGER),
        _spec("name", _TEXT),
        _spec("relation_name", _TEXT),
        _spec("state", _ENUM),
        _spec(
            "output",
            _REF,
            ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.JOIN_USE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.JOIN_USE),
        _spec("owner_module", _TEXT),
        _spec("owner_module_position", _INTEGER),
        _spec("owner_namespace", _ENUM),
        _spec("owner_kind", _ENUM),
        _spec("owner_name", _TEXT),
        _spec("owner_declaration_position", _INTEGER),
        _spec("join_position", _INTEGER),
        _spec("kind", _ENUM),
        _spec("state", _ENUM),
        _spec("reasons", _ENUMS, optional=True),
        _spec(
            "source_binding",
            _REF,
            ProjectPhase62PortableRefDomain.BINDING,
            optional=True,
        ),
        _spec("target_binding", _REF, ProjectPhase62PortableRefDomain.BINDING),
        _spec(
            "steps",
            _REFS,
            ProjectPhase62PortableRefDomain.TRAVERSAL_STEP,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.TRAVERSAL_STEP: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.TRAVERSAL_STEP),
        _spec("join_use", _REF, ProjectPhase62PortableRefDomain.JOIN_USE),
        _spec("position", _INTEGER),
        _spec(
            "direction",
            _REF,
            ProjectPhase62PortableRefDomain.RELATIONSHIP_DIRECTION,
        ),
        _spec("fanout", _ENUM, optional=True),
        _spec("inner_survival", _ENUM, optional=True),
        _spec("left_nulling", _ENUM, optional=True),
    ),
    ProjectPhase62RecordKind.RELATIONAL_OUTPUT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("runtime_output", _REF, ProjectPhase62PortableRefDomain.OUTPUT_VALUE),
        _spec("kind", _ENUM),
        _spec(
            "fields",
            _REFS,
            ProjectPhase62PortableRefDomain.RELATIONAL_FIELD,
            optional=True,
        ),
        _spec(
            "classes", _REFS, ProjectPhase62PortableRefDomain.VALUE_CLASS, optional=True
        ),
        _spec(
            "keys", _REFS, ProjectPhase62PortableRefDomain.CANDIDATE_KEY, optional=True
        ),
        _spec("fds", _REFS, ProjectPhase62PortableRefDomain.VALUE_FD, optional=True),
        _spec("grain", _REF, ProjectPhase62PortableRefDomain.GRAIN),
    ),
    ProjectPhase62RecordKind.RELATIONAL_FIELD: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_FIELD),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("position", _INTEGER),
        _spec("name", _TEXT),
        _spec("nullability", _ENUM),
    ),
    ProjectPhase62RecordKind.VALUE_CLASS: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.VALUE_CLASS),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("members", _REFS, ProjectPhase62PortableRefDomain.RELATIONAL_FIELD),
    ),
    ProjectPhase62RecordKind.CANDIDATE_KEY: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.CANDIDATE_KEY),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("determinants", _REFS, ProjectPhase62PortableRefDomain.VALUE_CLASS),
        _spec("strength", _ENUM),
    ),
    ProjectPhase62RecordKind.VALUE_FD: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.VALUE_FD),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("determinants", _REFS, ProjectPhase62PortableRefDomain.VALUE_CLASS),
        _spec("dependents", _REFS, ProjectPhase62PortableRefDomain.VALUE_CLASS),
        _spec("strength", _ENUM),
    ),
    ProjectPhase62RecordKind.GRAIN: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.GRAIN),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("state", _ENUM),
        _spec(
            "factors",
            _REFS,
            ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
            optional=True,
        ),
        _spec(
            "active", _REFS, ProjectPhase62PortableRefDomain.GRAIN_FACTOR, optional=True
        ),
        _spec(
            "dependencies",
            _REFS,
            ProjectPhase62PortableRefDomain.GRAIN_DEPENDENCY,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.GRAIN_FACTOR: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.GRAIN_FACTOR),
        _spec("grain", _REF, ProjectPhase62PortableRefDomain.GRAIN),
        _spec("kind", _ENUM),
        _spec("owner_module", _TEXT),
        _spec("owner_module_position", _INTEGER),
        _spec("owner_declaration_position", _INTEGER),
        _spec("owner_name", _TEXT),
        _spec(
            "operator",
            _REF,
            ProjectPhase62PortableRefDomain.PLAN_NODE,
            optional=True,
        ),
        _spec(
            "introduction_use", _REF, ProjectPhase62PortableRefDomain.USE, optional=True
        ),
        _spec(
            "nulling", _REFS, ProjectPhase62PortableRefDomain.PLAN_NODE, optional=True
        ),
    ),
    ProjectPhase62RecordKind.GRAIN_DEPENDENCY: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.GRAIN_DEPENDENCY),
        _spec("grain", _REF, ProjectPhase62PortableRefDomain.GRAIN),
        _spec("determinants", _REFS, ProjectPhase62PortableRefDomain.GRAIN_FACTOR),
        _spec("dependents", _REFS, ProjectPhase62PortableRefDomain.GRAIN_FACTOR),
    ),
    ProjectPhase62RecordKind.JOIN_REGION: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.JOIN_REGION),
        _spec("state", _ENUM),
        _spec(
            "joins", _REFS, ProjectPhase62PortableRefDomain.BINARY_JOIN, optional=True
        ),
        _spec(
            "blockers", _REFS, ProjectPhase62PortableRefDomain.JOIN_USE, optional=True
        ),
    ),
    ProjectPhase62RecordKind.BINARY_JOIN: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.BINARY_JOIN),
        _spec("region", _REF, ProjectPhase62PortableRefDomain.JOIN_REGION),
        _spec("join_use", _REF, ProjectPhase62PortableRefDomain.JOIN_USE),
        _spec("path_position", _INTEGER),
        _spec("node", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
        _spec("left_output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("right_output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("slots", _REFS, ProjectPhase62PortableRefDomain.INPUT_SLOT),
        _spec("uses", _REFS, ProjectPhase62PortableRefDomain.USE),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("matches", _REFS, ProjectPhase62PortableRefDomain.JOIN_MATCH),
        _spec("kind", _ENUM),
        _spec("fanout", _ENUM),
        _spec("survival", _ENUM),
        _spec("null_extension", _ENUM),
        _spec("barrier", _ENUM),
        _spec("null_property", _ENUM),
    ),
    ProjectPhase62RecordKind.JOIN_MATCH: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.JOIN_MATCH),
        _spec("binary_join", _REF, ProjectPhase62PortableRefDomain.BINARY_JOIN),
        _spec("position", _INTEGER),
        _spec("correspondence", _REF, ProjectPhase62PortableRefDomain.CORRESPONDENCE),
        _spec("left", _REF, ProjectPhase62PortableRefDomain.JOINED_FIELD),
        _spec("right", _REF, ProjectPhase62PortableRefDomain.JOINED_FIELD),
    ),
    ProjectPhase62RecordKind.JOINED_FIELD: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.JOINED_FIELD),
        _spec("binary_join", _REF, ProjectPhase62PortableRefDomain.BINARY_JOIN),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.RELATIONAL_OUTPUT),
        _spec("position", _INTEGER),
        _spec("introduction_use", _REF, ProjectPhase62PortableRefDomain.USE),
        _spec(
            "nulling", _REFS, ProjectPhase62PortableRefDomain.PLAN_NODE, optional=True
        ),
        _spec("nullability", _ENUM),
        _spec("name", _TEXT),
    ),
    ProjectPhase62RecordKind.NULLING: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.NULLING),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.OUTPUT_VALUE),
        _spec("field_position", _INTEGER),
        _spec("joins", _REFS, ProjectPhase62PortableRefDomain.PLAN_NODE, optional=True),
    ),
    ProjectPhase62RecordKind.AGGREGATE_FACT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.AGGREGATE_FACT),
        _spec("aggregate_node", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
        _spec("result_position", _INTEGER),
        _spec("selected_ordinal", _INTEGER),
        _spec("function", _TEXT),
        _spec("output_name", _TEXT),
    ),
    ProjectPhase62RecordKind.FACT_LOCALITY: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
        _spec("fact", _REF, ProjectPhase62PortableRefDomain.AGGREGATE_FACT),
        _spec("kind", _ENUM),
        _spec(
            "introduction_use", _REF, ProjectPhase62PortableRefDomain.USE, optional=True
        ),
        _spec(
            "region", _REF, ProjectPhase62PortableRefDomain.JOIN_REGION, optional=True
        ),
        _spec(
            "factors",
            _REFS,
            ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
            optional=True,
        ),
        _spec(
            "exposures",
            _REFS,
            ProjectPhase62PortableRefDomain.MULTIPLICITY_EXPOSURE,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.MULTIPLICITY_EXPOSURE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.MULTIPLICITY_EXPOSURE),
        _spec("locality", _REF, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
        _spec("join", _REF, ProjectPhase62PortableRefDomain.BINARY_JOIN),
        _spec("factors", _REFS, ProjectPhase62PortableRefDomain.GRAIN_FACTOR),
    ),
    ProjectPhase62RecordKind.ACTUAL_GRAIN_CANDIDATE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE),
        _spec(
            "region",
            _REF,
            ProjectPhase62PortableRefDomain.JOIN_REGION,
            optional=True,
        ),
        _spec(
            "home_alignment",
            _REF,
            ProjectPhase62PortableRefDomain.ALIGNMENT,
            optional=True,
        ),
        _spec(
            "factors",
            _REFS,
            ProjectPhase62PortableRefDomain.GRAIN_FACTOR,
            optional=True,
        ),
        _spec("authority_kinds", _ENUMS),
    ),
    ProjectPhase62RecordKind.COMMON_GRAIN: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.COMMON_GRAIN),
        _spec("status", _ENUM),
        _spec(
            "actual",
            _REFS,
            ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE,
            optional=True,
        ),
        _spec(
            "common",
            _REFS,
            ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE,
            optional=True,
        ),
        _spec(
            "retained",
            _REFS,
            ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.ALIGNMENT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ALIGNMENT),
        _spec("left", _REF, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
        _spec("right", _REF, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
        _spec("structural", _ENUM),
        _spec("risks", _ENUMS, optional=True),
        _spec("requirements", _ENUMS, optional=True),
        _spec("common", _REF, ProjectPhase62PortableRefDomain.COMMON_GRAIN),
        _spec("chasms", _REFS, ProjectPhase62PortableRefDomain.CHASM, optional=True),
    ),
    ProjectPhase62RecordKind.CHASM: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.CHASM),
        _spec("common", _REF, ProjectPhase62PortableRefDomain.ACTUAL_GRAIN_CANDIDATE),
        _spec("participants", _REFS, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
        _spec("joins", _REFS, ProjectPhase62PortableRefDomain.BINARY_JOIN),
    ),
    ProjectPhase62RecordKind.NON_CONCRETE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.NON_CONCRETE),
        _spec("kind", _ENUM),
        _spec("state", _ENUM),
        _spec("reasons", _ENUMS),
        _spec(
            "join_uses", _REFS, ProjectPhase62PortableRefDomain.JOIN_USE, optional=True
        ),
        _spec(
            "facts",
            _REFS,
            ProjectPhase62PortableRefDomain.AGGREGATE_FACT,
            optional=True,
        ),
    ),
    ProjectPhase62RecordKind.ANALYSIS_REVERSE_USE: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY),
        _spec("output", _REF, ProjectPhase62PortableRefDomain.OUTPUT_VALUE),
        _spec("uses", _REFS, ProjectPhase62PortableRefDomain.USE, optional=True),
    ),
    ProjectPhase62RecordKind.ANALYSIS_TOPOLOGICAL: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY),
        _spec("position", _INTEGER),
        _spec("node", _REF, ProjectPhase62PortableRefDomain.PLAN_NODE),
    ),
    ProjectPhase62RecordKind.ANALYSIS_NULLING: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY),
        _spec("nulling", _REF, ProjectPhase62PortableRefDomain.NULLING),
    ),
    ProjectPhase62RecordKind.ANALYSIS_FACT_LOCALITY: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY),
        _spec("fact", _REF, ProjectPhase62PortableRefDomain.AGGREGATE_FACT),
        _spec("localities", _REFS, ProjectPhase62PortableRefDomain.FACT_LOCALITY),
    ),
    ProjectPhase62RecordKind.ANALYSIS_ALIGNMENT: (
        _spec("ref", _REF, ProjectPhase62PortableRefDomain.ANALYSIS_ENTRY),
        _spec(
            "alignments",
            _REFS,
            ProjectPhase62PortableRefDomain.ALIGNMENT,
            optional=True,
        ),
        _spec("chasms", _REFS, ProjectPhase62PortableRefDomain.CHASM, optional=True),
    ),
    ProjectPhase62RecordKind.END: (),
}

_OWNER_DOMAINS: dict[ProjectPhase62RecordKind, ProjectPhase62PortableRefDomain] = {
    kind: schema[0].domains[0]
    for kind, schema in _SCHEMAS.items()
    if schema and schema[0].key == "ref" and schema[0].domains
}

_ENUMERATIONS = frozenset(
    {
        "concrete",
        "unknown",
        "blocked",
        "ambiguous",
        "deferred",
        "inner",
        "left",
        "base",
        "join",
        "type",
        "relation",
        "callable",
        "enum",
        "shape",
        "source",
        "table",
        "query",
        "constraint",
        "derive",
        "strict",
        "lax",
        "non_null",
        "nullable",
        "zero_allowed",
        "at_least_one",
        "at_most_zero",
        "at_most_one",
        "unbounded_by_one",
        "preserves_source_multiplicity",
        "may_multiply",
        "guarantees_left_survival",
        "may_drop_left_rows",
        "no_new_null_extension",
        "may_null_extend_right",
        "present",
        "not_applicable",
        "factorized",
        "global",
        "source_domain",
        "grouped_result",
        "group_domain",
        "home",
        "join",
        "left_input",
        "right_input",
        "fact_locality",
        "join_left_input",
        "join_right_input",
        "join_source_slice",
        "join_output",
        "provided",
        "guarantees_source_survival",
        "may_drop_source_rows",
        "no_missing_match_nulling",
        "may_null_extend",
        "unique",
        "none",
        "conflict",
        "exactly_aligned",
        "structurally_alignable",
        "reaggregation_required",
        "ambiguous_path",
        "insufficient_evidence",
        "incompatible",
        "fanout_risk",
        "cross_fact_multiplication",
        "aggregate_algebra_required",
        "join_use",
        "join_region",
        "multifact_region",
        "verified",
        "unknown_source_binding",
        "forward_source_binding",
        "ambiguous_source_binding",
        "blocked_source_binding",
        "unknown_target_relation",
        "ambiguous_target_relation",
        "blocked_target_relation",
        "direct_relationship_absent",
        "direct_relationship_ambiguous",
        "unknown_relationship",
        "ambiguous_relationship",
        "blocked_relationship",
        "unknown_endpoint_direction",
        "ambiguous_endpoint_direction",
        "blocked_endpoint_direction",
        "non_contiguous_path",
        "path_start_mismatch",
        "path_end_mismatch",
    }
)


def _reject(
    status: ProjectPhase62PureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> ProjectPhase62PureOutcome:
    return ProjectPhase62PureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _field(
    record: ProjectPhase62PureRecord,
    key: str,
) -> ProjectPhase62PureValue:
    return next(item.value for item in record.fields if item.key == key)


def _records(
    document: ProjectPhase62PureDocument,
    kind: ProjectPhase62RecordKind,
) -> tuple[ProjectPhase62PureRecord, ...]:
    return tuple(record for record in document.records if record.kind is kind)


def _ref_value(record: ProjectPhase62PureRecord, key: str) -> ProjectPhase62PortableRef:
    return cast(ProjectPhase62PortableRef, _field(record, key).ref)


def _refs_value(
    record: ProjectPhase62PureRecord,
    key: str,
) -> tuple[ProjectPhase62PortableRef, ...]:
    value = _field(record, key)
    return () if value.tag is ProjectPhase62PureTag.ABSENT else value.refs


def _optional_ref_value(
    record: ProjectPhase62PureRecord,
    key: str,
) -> ProjectPhase62PortableRef | None:
    value = _field(record, key)
    return None if value.tag is ProjectPhase62PureTag.ABSENT else value.ref


def _integer_value(record: ProjectPhase62PureRecord, key: str) -> int:
    return cast(int, _field(record, key).integer)


def _text_value(record: ProjectPhase62PureRecord, key: str) -> str:
    return cast(str, _field(record, key).text)


def _enum_value(record: ProjectPhase62PureRecord, key: str) -> str:
    return cast(str, _field(record, key).enumeration)


def _value_valid(
    value: object,
    spec: _FieldSpec,
) -> bool:
    if (
        type(value) is not ProjectPhase62PureValue
        or type(value.tag) is not ProjectPhase62PureTag
    ):
        return False
    if value.tag not in spec.tags:
        return False
    if value.tag is ProjectPhase62PureTag.ABSENT:
        return not any(
            (
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
        )
    if value.tag is ProjectPhase62PureTag.TEXT:
        return type(value.text) is str
    if value.tag is ProjectPhase62PureTag.INTEGER:
        return type(value.integer) is int and 0 <= value.integer <= _MAX_INTEGER
    if value.tag is ProjectPhase62PureTag.BOOLEAN:
        return type(value.boolean) is bool
    if value.tag is ProjectPhase62PureTag.ENUMERATION:
        return type(value.enumeration) is str and value.enumeration in _ENUMERATIONS
    if value.tag is ProjectPhase62PureTag.REF:
        return type(value.ref) is ProjectPhase62PortableRef and (
            not spec.domains or value.ref.domain in spec.domains
        )
    if value.tag is ProjectPhase62PureTag.REFS:
        return (
            type(value.refs) is tuple
            and bool(value.refs)
            and all(
                type(item) is ProjectPhase62PortableRef
                and (not spec.domains or item.domain in spec.domains)
                for item in value.refs
            )
        )
    if value.tag is ProjectPhase62PureTag.TEXTS:
        return (
            type(value.texts) is tuple
            and bool(value.texts)
            and all(type(item) is str for item in value.texts)
        )
    if value.tag is ProjectPhase62PureTag.INTEGERS:
        return (
            type(value.integers) is tuple
            and bool(value.integers)
            and all(
                type(item) is int and 0 <= item <= _MAX_INTEGER
                for item in value.integers
            )
        )
    return (
        type(value.enumerations) is tuple
        and bool(value.enumerations)
        and all(
            type(item) is str and item in _ENUMERATIONS for item in value.enumerations
        )
    )


def _validate_shape(
    document: ProjectPhase62PureDocument,
) -> ProjectPhase62PureOutcome | None:
    if type(document.records) is not tuple or not document.records:
        return _reject(ProjectPhase62PureStatus.INVALID_HEADER)
    if any(type(record) is not ProjectPhase62PureRecord for record in document.records):
        return _reject(ProjectPhase62PureStatus.INVALID_RECORD_KIND)
    if document.format_marker != PROJECT_PHASE62_INSPECTION_FORMAT:
        return _reject(ProjectPhase62PureStatus.UNKNOWN_FORMAT)
    kinds = tuple(record.kind for record in document.records)
    if (
        kinds[0] is not ProjectPhase62RecordKind.HEADER
        or kinds[-1] is not ProjectPhase62RecordKind.END
        or kinds.count(ProjectPhase62RecordKind.HEADER) != 1
        or kinds.count(ProjectPhase62RecordKind.END) != 1
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_HEADER)
    order = tuple(ProjectPhase62RecordKind)
    positions: list[int] = []
    for record_position, record in enumerate(document.records):
        if type(record.kind) is not ProjectPhase62RecordKind:
            return _reject(
                ProjectPhase62PureStatus.INVALID_RECORD_KIND, record_position
            )
        positions.append(order.index(record.kind))
        schema = _SCHEMAS[record.kind]
        if type(record.fields) is not tuple or len(record.fields) != len(schema):
            return _reject(ProjectPhase62PureStatus.INVALID_FIELD, record_position)
        for field_position, (field, spec) in enumerate(
            zip(record.fields, schema, strict=True)
        ):
            if (
                type(field) is not ProjectPhase62PureField
                or field.key != spec.key
                or not _value_valid(field.value, spec)
            ):
                return _reject(
                    ProjectPhase62PureStatus.INVALID_VALUE,
                    record_position,
                    field_position,
                )
    if positions != sorted(positions):
        return _reject(ProjectPhase62PureStatus.INVALID_SECTION_ORDER)
    header = document.records[0]
    if _text_value(header, "format") != PROJECT_PHASE62_INSPECTION_FORMAT:
        return _reject(ProjectPhase62PureStatus.UNKNOWN_FORMAT, 0, 0)
    if (
        _enum_value(header, "verification") != "verified"
        or _enum_value(header, "base_verification") != "verified"
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_HEADER, 0)
    return None


def _declared_refs(
    document: ProjectPhase62PureDocument,
) -> tuple[
    dict[ProjectPhase62PortableRef, ProjectPhase62PureRecord],
    ProjectPhase62PureOutcome | None,
]:
    declared: dict[ProjectPhase62PortableRef, ProjectPhase62PureRecord] = {}
    for record_position, record in enumerate(document.records):
        domain = _OWNER_DOMAINS.get(record.kind)
        if domain is None:
            continue
        ref = _ref_value(record, "ref")
        if ref.domain is not domain or ref in declared:
            return {}, _reject(ProjectPhase62PureStatus.INVALID_REF, record_position, 0)
        declared[ref] = record
    by_domain = {
        domain: tuple(ref.position for ref in declared if ref.domain is domain)
        for domain in ProjectPhase62PortableRefDomain
    }
    for domain, positions in by_domain.items():
        if not positions:
            continue
        first = (
            min(positions)
            if domain
            in {
                ProjectPhase62PortableRefDomain.PLAN_NODE,
                ProjectPhase62PortableRefDomain.OUTPUT_VALUE,
                ProjectPhase62PortableRefDomain.INPUT_SLOT,
                ProjectPhase62PortableRefDomain.USE,
            }
            else 0
        )
        if positions != tuple(range(first, first + len(positions))):
            return {}, _reject(ProjectPhase62PureStatus.INVALID_REF)
    for record_position, record in enumerate(document.records):
        for field_position, field in enumerate(record.fields):
            refs = (
                (field.value.ref,)
                if field.value.tag is ProjectPhase62PureTag.REF
                else (
                    field.value.refs
                    if field.value.tag is ProjectPhase62PureTag.REFS
                    else ()
                )
            )
            if any(ref not in declared for ref in refs):
                return {}, _reject(
                    ProjectPhase62PureStatus.DANGLING_REF,
                    record_position,
                    field_position,
                )
    return declared, None


def _validate_summary(
    document: ProjectPhase62PureDocument,
) -> ProjectPhase62PureOutcome | None:
    summaries = _records(document, ProjectPhase62RecordKind.SUMMARY)
    if len(summaries) != 1:
        return _reject(ProjectPhase62PureStatus.INVALID_COUNT)
    summary = summaries[0]
    names = _field(summary, "names").texts
    counts = _field(summary, "counts").integers
    expected_names = tuple(kind.value for kind in ProjectPhase62RecordKind)
    expected_counts = tuple(
        len(_records(document, kind)) for kind in ProjectPhase62RecordKind
    )
    if names != expected_names or counts != expected_counts:
        return _reject(ProjectPhase62PureStatus.INVALID_COUNT)
    return None


def _validate_relationships(
    document: ProjectPhase62PureDocument,
) -> ProjectPhase62PureOutcome | None:
    correspondences = _records(document, ProjectPhase62RecordKind.CORRESPONDENCE)
    directions = _records(document, ProjectPhase62RecordKind.RELATIONSHIP_DIRECTION)
    if any(
        {
            _integer_value(direction, "source_endpoint"),
            _integer_value(direction, "target_endpoint"),
        }
        != {0, 1}
        for direction in directions
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_RELATIONSHIP)
    for condition in _records(document, ProjectPhase62RecordKind.CONDITION):
        condition_ref = _ref_value(condition, "ref")
        expected = tuple(
            _ref_value(item, "ref")
            for item in correspondences
            if _ref_value(item, "condition") == condition_ref
        )
        if _refs_value(condition, "correspondences") != expected or tuple(
            _integer_value(item, "position")
            for item in correspondences
            if _ref_value(item, "condition") == condition_ref
        ) != tuple(range(len(expected))):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONSHIP)
    guarantees = _records(document, ProjectPhase62RecordKind.MATCH_GUARANTEE)
    direction_refs = tuple(_ref_value(item, "ref") for item in directions)
    if (
        len(guarantees) != len(directions)
        or tuple(_ref_value(item, "direction") for item in guarantees) != direction_refs
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_RELATIONSHIP)
    return None


def _validate_joins(
    document: ProjectPhase62PureDocument,
    declared: Mapping[ProjectPhase62PortableRef, ProjectPhase62PureRecord],
) -> ProjectPhase62PureOutcome | None:
    steps = _records(document, ProjectPhase62RecordKind.TRAVERSAL_STEP)
    for join_use in _records(document, ProjectPhase62RecordKind.JOIN_USE):
        ref = _ref_value(join_use, "ref")
        expected = tuple(
            _ref_value(step, "ref")
            for step in steps
            if _ref_value(step, "join_use") == ref
        )
        if _refs_value(join_use, "steps") != expected or tuple(
            _integer_value(step, "position")
            for step in steps
            if _ref_value(step, "join_use") == ref
        ) != tuple(range(len(expected))):
            return _reject(ProjectPhase62PureStatus.INVALID_JOIN)

    project_slots = {
        _ref_value(record, "ref"): record
        for record in _records(document, ProjectPhase62RecordKind.PROJECT_SLOT)
    }
    project_uses = {
        _ref_value(record, "ref"): record
        for record in _records(document, ProjectPhase62RecordKind.PROJECT_USE)
    }
    binaries = {
        _ref_value(record, "ref"): record
        for record in _records(document, ProjectPhase62RecordKind.BINARY_JOIN)
    }
    retained_join_refs: list[ProjectPhase62PortableRef] = []
    for region in _records(document, ProjectPhase62RecordKind.JOIN_REGION):
        join_refs = _refs_value(region, "joins")
        blockers = _refs_value(region, "blockers")
        state = _enum_value(region, "state")
        if (state == "concrete") != bool(join_refs) or (state == "concrete") == bool(
            blockers
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
        retained_join_refs.extend(join_refs)
        previous_output: ProjectPhase62PortableRef | None = None
        for join_ref in join_refs:
            join = binaries[join_ref]
            if _ref_value(join, "region") != _ref_value(region, "ref"):
                return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
            slots = _refs_value(join, "slots")
            uses = _refs_value(join, "uses")
            if len(slots) != 2 or len(uses) != 2:
                return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
            node = _ref_value(join, "node")
            if (
                tuple(_integer_value(project_slots[item], "ordinal") for item in slots)
                != (
                    0,
                    1,
                )
                or any(
                    _ref_value(project_slots[item], "consumer") != node
                    for item in slots
                )
                or any(
                    _ref_value(project_uses[use], "slot") != slot
                    for use, slot in zip(uses, slots, strict=True)
                )
                or _ref_value(project_uses[uses[0]], "output")
                != _ref_value(
                    declared[_ref_value(join, "left_output")], "runtime_output"
                )
                or _ref_value(project_uses[uses[1]], "output")
                != _ref_value(
                    declared[_ref_value(join, "right_output")], "runtime_output"
                )
                or _ref_value(
                    declared[
                        _ref_value(
                            declared[_ref_value(join, "output")], "runtime_output"
                        )
                    ],
                    "producer",
                )
                != node
            ):
                return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
            if (
                previous_output is not None
                and _ref_value(join, "left_output") != previous_output
            ):
                return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
            previous_output = _ref_value(join, "output")
    if tuple(retained_join_refs) != tuple(binaries):
        return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
    for join_use in _records(document, ProjectPhase62RecordKind.JOIN_USE):
        join_use_ref = _ref_value(join_use, "ref")
        owned = tuple(
            item
            for item in binaries.values()
            if _ref_value(item, "join_use") == join_use_ref
        )
        path_steps = _refs_value(join_use, "steps")
        if _enum_value(join_use, "state") == "concrete":
            if len(owned) != len(path_steps) or tuple(
                _integer_value(item, "path_position") for item in owned
            ) != tuple(range(len(path_steps))):
                return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
        elif owned:
            return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
    fields = _records(document, ProjectPhase62RecordKind.JOINED_FIELD)
    matches = _records(document, ProjectPhase62RecordKind.JOIN_MATCH)
    for binary_ref, binary in binaries.items():
        owned = tuple(
            item for item in fields if _ref_value(item, "binary_join") == binary_ref
        )
        owned_matches = tuple(
            item for item in matches if _ref_value(item, "binary_join") == binary_ref
        )
        if (
            tuple(_integer_value(item, "position") for item in owned)
            != tuple(range(len(owned)))
            or any(
                _ref_value(item, "output") != _ref_value(binary, "output")
                for item in owned
            )
            or _refs_value(binary, "matches")
            != tuple(_ref_value(item, "ref") for item in owned_matches)
            or tuple(_integer_value(item, "position") for item in owned_matches)
            != tuple(range(len(owned_matches)))
            or any(
                _ref_value(item, side)
                not in tuple(_ref_value(field, "ref") for field in owned)
                for item in owned_matches
                for side in ("left", "right")
            )
            or any(
                _ref_value(item, "left") == _ref_value(item, "right")
                for item in owned_matches
            )
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_JOIN)
    return None


def _validate_relational_properties(
    document: ProjectPhase62PureDocument,
) -> ProjectPhase62PureOutcome | None:
    fields = _records(document, ProjectPhase62RecordKind.RELATIONAL_FIELD)
    classes = _records(document, ProjectPhase62RecordKind.VALUE_CLASS)
    keys = _records(document, ProjectPhase62RecordKind.CANDIDATE_KEY)
    fds = _records(document, ProjectPhase62RecordKind.VALUE_FD)
    grains = _records(document, ProjectPhase62RecordKind.GRAIN)
    factors = _records(document, ProjectPhase62RecordKind.GRAIN_FACTOR)
    dependencies = _records(document, ProjectPhase62RecordKind.GRAIN_DEPENDENCY)
    for output in _records(document, ProjectPhase62RecordKind.RELATIONAL_OUTPUT):
        output_ref = _ref_value(output, "ref")
        expected_fields = tuple(
            _ref_value(item, "ref")
            for item in fields
            if _ref_value(item, "output") == output_ref
        )
        expected_classes = tuple(
            _ref_value(item, "ref")
            for item in classes
            if _ref_value(item, "output") == output_ref
        )
        expected_keys = tuple(
            _ref_value(item, "ref")
            for item in keys
            if _ref_value(item, "output") == output_ref
        )
        expected_fds = tuple(
            _ref_value(item, "ref")
            for item in fds
            if _ref_value(item, "output") == output_ref
        )
        owned_grains = tuple(
            item for item in grains if _ref_value(item, "output") == output_ref
        )
        if (
            _refs_value(output, "fields") != expected_fields
            or _refs_value(output, "classes") != expected_classes
            or _refs_value(output, "keys") != expected_keys
            or _refs_value(output, "fds") != expected_fds
            or len(owned_grains) != 1
            or _ref_value(output, "grain") != _ref_value(owned_grains[0], "ref")
            or tuple(
                _integer_value(item, "position")
                for item in fields
                if _ref_value(item, "output") == output_ref
            )
            != tuple(range(len(expected_fields)))
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    class_owners = {
        _ref_value(item, "ref"): _ref_value(item, "output") for item in classes
    }
    field_owners = {
        _ref_value(item, "ref"): _ref_value(item, "output") for item in fields
    }
    for value_class in classes:
        output = _ref_value(value_class, "output")
        if any(
            field_owners[item] != output for item in _refs_value(value_class, "members")
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    for output in _records(document, ProjectPhase62RecordKind.RELATIONAL_OUTPUT):
        field_refs = _refs_value(output, "fields")
        member_refs = tuple(
            member
            for value_class in classes
            if _ref_value(value_class, "output") == _ref_value(output, "ref")
            for member in _refs_value(value_class, "members")
        )
        if len(member_refs) != len(set(member_refs)) or set(member_refs) != set(
            field_refs
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    for key in keys:
        output = _ref_value(key, "output")
        if any(
            class_owners[item] != output for item in _refs_value(key, "determinants")
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    for fact in fds:
        output = _ref_value(fact, "output")
        if any(
            class_owners[item] != output
            for item in (
                *_refs_value(fact, "determinants"),
                *_refs_value(fact, "dependents"),
            )
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    for grain in grains:
        grain_ref = _ref_value(grain, "ref")
        expected_factors = tuple(
            _ref_value(item, "ref")
            for item in factors
            if _ref_value(item, "grain") == grain_ref
        )
        expected_dependencies = tuple(
            _ref_value(item, "ref")
            for item in dependencies
            if _ref_value(item, "grain") == grain_ref
        )
        if (
            _refs_value(grain, "factors") != expected_factors
            or _refs_value(grain, "dependencies") != expected_dependencies
            or any(
                item not in expected_factors for item in _refs_value(grain, "active")
            )
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    factor_owners = {
        _ref_value(item, "ref"): _ref_value(item, "grain") for item in factors
    }
    for dependency in dependencies:
        grain = _ref_value(dependency, "grain")
        if any(
            factor_owners[item] != grain
            for item in (
                *_refs_value(dependency, "determinants"),
                *_refs_value(dependency, "dependents"),
            )
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_RELATIONAL_PROPERTY)
    return None


def _validate_multifact(
    document: ProjectPhase62PureDocument,
) -> ProjectPhase62PureOutcome | None:
    localities = _records(document, ProjectPhase62RecordKind.FACT_LOCALITY)
    candidates = _records(document, ProjectPhase62RecordKind.ACTUAL_GRAIN_CANDIDATE)
    common = _records(document, ProjectPhase62RecordKind.COMMON_GRAIN)
    alignments = _records(document, ProjectPhase62RecordKind.ALIGNMENT)
    chasms = _records(document, ProjectPhase62RecordKind.CHASM)
    exposures = _records(document, ProjectPhase62RecordKind.MULTIPLICITY_EXPOSURE)
    for fact in _records(document, ProjectPhase62RecordKind.AGGREGATE_FACT):
        fact_ref = _ref_value(fact, "ref")
        owned = tuple(
            item for item in localities if _ref_value(item, "fact") == fact_ref
        )
        if (
            not owned
            or _enum_value(owned[0], "kind") != "home"
            or sum(_enum_value(item, "kind") == "home" for item in owned) != 1
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    for locality in localities:
        locality_ref = _ref_value(locality, "ref")
        expected = tuple(
            _ref_value(item, "ref")
            for item in exposures
            if _ref_value(item, "locality") == locality_ref
        )
        if _refs_value(locality, "exposures") != expected:
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    if any(
        (_optional_ref_value(candidate, "region") is None)
        == (_optional_ref_value(candidate, "home_alignment") is None)
        for candidate in candidates
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    common_refs = tuple(_ref_value(item, "ref") for item in common)
    if tuple(_ref_value(item, "common") for item in alignments) != common_refs:
        return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    locality_by_ref = {_ref_value(item, "ref"): item for item in localities}
    chasm_refs = {_ref_value(item, "ref") for item in chasms}
    for alignment in alignments:
        alignment_ref = _ref_value(alignment, "ref")
        left_ref = _ref_value(alignment, "left")
        right_ref = _ref_value(alignment, "right")
        if left_ref == right_ref or any(
            item not in chasm_refs for item in _refs_value(alignment, "chasms")
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
        left = locality_by_ref[left_ref]
        right = locality_by_ref[right_ref]
        left_region = _optional_ref_value(left, "region")
        right_region = _optional_ref_value(right, "region")
        if left_region is None and right_region is None:
            expected_actual = tuple(
                _ref_value(item, "ref")
                for item in candidates
                if _optional_ref_value(item, "home_alignment") == alignment_ref
            )
        elif left_region is not None and left_region == right_region:
            expected_actual = tuple(
                _ref_value(item, "ref")
                for item in candidates
                if _optional_ref_value(item, "region") == left_region
            )
        else:
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
        result = next(
            item
            for item in common
            if _ref_value(item, "ref") == _ref_value(alignment, "common")
        )
        actual = _refs_value(result, "actual")
        shared = _refs_value(result, "common")
        retained = _refs_value(result, "retained")
        status = _enum_value(result, "status")
        expected_status = (
            "none"
            if not retained
            else ("unique" if len(retained) == 1 else "ambiguous")
        )
        if (
            actual != expected_actual
            or len(set(actual)) != len(actual)
            or any(item not in actual for item in (*shared, *retained))
            or any(item not in shared for item in retained)
            or (status not in {"unknown", "conflict"} and status != expected_status)
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    for chasm in chasms:
        participants = _refs_value(chasm, "participants")
        regions = tuple(
            _optional_ref_value(locality_by_ref[item], "region")
            for item in participants
        )
        common_candidate = next(
            item
            for item in candidates
            if _ref_value(item, "ref") == _ref_value(chasm, "common")
        )
        if (
            len(participants) < 2
            or len(set(participants)) != len(participants)
            or not regions
            or regions[0] is None
            or any(item != regions[0] for item in regions)
            or _optional_ref_value(common_candidate, "region") != regions[0]
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_MULTIFACT)
    return None


def _validate_analysis(
    document: ProjectPhase62PureDocument,
    declared: Mapping[ProjectPhase62PortableRef, ProjectPhase62PureRecord],
) -> ProjectPhase62PureOutcome | None:
    outputs = _records(document, ProjectPhase62RecordKind.PROJECT_OUTPUT)
    uses = _records(document, ProjectPhase62RecordKind.PROJECT_USE)
    reverse = _records(document, ProjectPhase62RecordKind.ANALYSIS_REVERSE_USE)
    if len(reverse) != len(outputs):
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)
    for output, entry in zip(outputs, reverse, strict=True):
        output_ref = _ref_value(output, "ref")
        expected = tuple(
            _ref_value(use, "ref")
            for use in uses
            if _ref_value(use, "output") == output_ref
        )
        if (
            _ref_value(entry, "output") != output_ref
            or _refs_value(entry, "uses") != expected
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)

    node_refs = tuple(
        _ref_value(record, "ref")
        for record in _records(document, ProjectPhase62RecordKind.PROJECT_NODE)
    )
    node_index = {ref: position for position, ref in enumerate(node_refs)}
    successors: list[list[int]] = [[] for _ in node_refs]
    indegree = [0] * len(node_refs)
    for use in uses:
        output = declared[_ref_value(use, "output")]
        slot = declared[_ref_value(use, "slot")]
        producer = node_index[_ref_value(output, "producer")]
        consumer = node_index[_ref_value(slot, "consumer")]
        successors[producer].append(consumer)
        indegree[consumer] += 1
    pending: list[tuple[int, int]] = []
    for position, degree in enumerate(indegree):
        if degree == 0:
            heappush(pending, (node_refs[position].position, position))
    expected_topological: list[ProjectPhase62PortableRef] = []
    while pending:
        _, source = heappop(pending)
        expected_topological.append(node_refs[source])
        for target in successors[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                heappush(pending, (node_refs[target].position, target))
    topological = _records(document, ProjectPhase62RecordKind.ANALYSIS_TOPOLOGICAL)
    if tuple(
        (_integer_value(record, "position"), _ref_value(record, "node"))
        for record in topological
    ) != tuple(enumerate(expected_topological)):
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)

    nulling = _records(document, ProjectPhase62RecordKind.NULLING)
    nulling_analysis = _records(document, ProjectPhase62RecordKind.ANALYSIS_NULLING)
    if tuple(_ref_value(record, "nulling") for record in nulling_analysis) != tuple(
        _ref_value(record, "ref") for record in nulling
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)

    localities = _records(document, ProjectPhase62RecordKind.FACT_LOCALITY)
    facts = _records(document, ProjectPhase62RecordKind.AGGREGATE_FACT)
    locality_analysis = _records(
        document, ProjectPhase62RecordKind.ANALYSIS_FACT_LOCALITY
    )
    if len(locality_analysis) != len(facts):
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)
    for fact, entry in zip(facts, locality_analysis, strict=True):
        fact_ref = _ref_value(fact, "ref")
        expected = tuple(
            _ref_value(locality, "ref")
            for locality in localities
            if _ref_value(locality, "fact") == fact_ref
        )
        if (
            _ref_value(entry, "fact") != fact_ref
            or _refs_value(entry, "localities") != expected
        ):
            return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)

    alignment_analysis = _records(document, ProjectPhase62RecordKind.ANALYSIS_ALIGNMENT)
    if len(alignment_analysis) != 1:
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)
    entry = alignment_analysis[0]
    if _refs_value(entry, "alignments") != tuple(
        _ref_value(record, "ref")
        for record in _records(document, ProjectPhase62RecordKind.ALIGNMENT)
    ) or _refs_value(entry, "chasms") != tuple(
        _ref_value(record, "ref")
        for record in _records(document, ProjectPhase62RecordKind.CHASM)
    ):
        return _reject(ProjectPhase62PureStatus.INVALID_ANALYSIS)
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


def _encode_ref(ref: ProjectPhase62PortableRef) -> str:
    return f"{ref.domain.value}:{ref.position}"


def _encode_value(value: ProjectPhase62PureValue) -> str:
    if value.tag is ProjectPhase62PureTag.ABSENT:
        return "n:"
    if value.tag is ProjectPhase62PureTag.TEXT:
        return f"t:{_escape_text(cast(str, value.text))}"
    if value.tag is ProjectPhase62PureTag.INTEGER:
        return f"i:{value.integer}"
    if value.tag is ProjectPhase62PureTag.BOOLEAN:
        return "b:1" if value.boolean else "b:0"
    if value.tag is ProjectPhase62PureTag.ENUMERATION:
        return f"e:{_escape_text(cast(str, value.enumeration))}"
    if value.tag is ProjectPhase62PureTag.REF:
        return f"r:{_encode_ref(cast(ProjectPhase62PortableRef, value.ref))}"
    if value.tag is ProjectPhase62PureTag.REFS:
        return "q:" + ",".join(_encode_ref(ref) for ref in value.refs)
    if value.tag is ProjectPhase62PureTag.TEXTS:
        return "s:" + ",".join(_escape_text(item) for item in value.texts)
    if value.tag is ProjectPhase62PureTag.INTEGERS:
        return "j:" + ",".join(str(item) for item in value.integers)
    return "z:" + ",".join(_escape_text(item) for item in value.enumerations)


def _encode_document(document: ProjectPhase62PureDocument) -> bytes:
    lines = tuple(
        record.kind.value
        + "".join(
            f"\t{field.key}={_encode_value(field.value)}" for field in record.fields
        )
        for record in document.records
    )
    return ("\n".join(lines) + "\n").encode("utf-8")


def evaluate_project_phase62_document(
    document: object,
) -> ProjectPhase62PureOutcome:
    """Validate and encode one portable document without ambient state."""

    if type(document) is not ProjectPhase62PureDocument:
        return _reject(ProjectPhase62PureStatus.INVALID_DOCUMENT)
    try:
        validation = _validate_shape(document)
        if validation is not None:
            return validation
        validation = _validate_summary(document)
        if validation is not None:
            return validation
        declared, rejection = _declared_refs(document)
        if rejection is not None:
            return rejection
        validation = _validate_relationships(document)
        if validation is not None:
            return validation
        validation = _validate_joins(document, declared)
        if validation is not None:
            return validation
        validation = _validate_relational_properties(document)
        if validation is not None:
            return validation
        validation = _validate_multifact(document)
        if validation is not None:
            return validation
        validation = _validate_analysis(document, declared)
        if validation is not None:
            return validation
        return ProjectPhase62PureOutcome(
            status=ProjectPhase62PureStatus.OK,
            canonical_bytes=_encode_document(document),
        )
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return _reject(ProjectPhase62PureStatus.INVALID_DOCUMENT)
