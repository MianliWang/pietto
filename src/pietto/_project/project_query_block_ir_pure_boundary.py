"""Pure portable Phase-63 query-block IR observation and total evaluator."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import json
from heapq import heappop, heappush
from typing import Any, cast

__all__: tuple[str, ...] = ()

PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT = "pietto.phase63-query-block-ir-inspection.v1"
PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT = (
    "pietto.phase64-flat-relational-ir-inspection.v1"
)
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
    TYPE_EVIDENCE = "type_evidence"
    TYPE_PARAMETER_SOURCE = "type_parameter_source"
    ORDER_SOURCE = "order_source"
    ORDER_BINDING = "order_binding"
    ORDER_PROOF = "order_proof"
    REQUIREMENT = "requirement"
    PROOF = "proof"
    DIAGNOSTIC = "diagnostic"
    PREDICATE_EXPRESSION = "predicate_expression"
    PREDICATE_CALL = "predicate_call"
    PREDICATE_EQUALITY = "predicate_equality"
    PREDICATE_INPUT_KEY = "predicate_input_key"
    PREDICATE_KEY_MATCH = "predicate_key_match"
    EXISTENCE_USE = "existence_use"
    SCALAR_ANY_USE = "scalar_any_use"
    SCALAR_ANY_VALUE = "scalar_any_value"
    SCALAR_ANY_FIELD = "scalar_any_field"
    SCALAR_ANY_REFERENCE = "scalar_any_reference"
    SCALAR_ANY_CANDIDATE = "scalar_any_candidate"
    PREDICATE_ANY_SCOPE = "predicate_any_scope"


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
    OWNER_LET = "owner_let"
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
    ALGEBRA = "algebra"
    CONDITION = "condition"
    INPUT_CORRESPONDENCE = "input_correspondence"
    PREDICATE_EXPRESSION = "predicate_expression"
    PREDICATE_CALL = "predicate_call"
    PREDICATE_ARGUMENT = "predicate_argument"
    PREDICATE_JOIN = "predicate_join"
    PREDICATE_EQUALITY = "predicate_equality"
    PREDICATE_INPUT_KEY = "predicate_input_key"
    PREDICATE_KEY_MATCH = "predicate_key_match"
    EXISTENCE_USE = "existence_use"
    SCALAR_ANY_USE = "scalar_any_use"
    SCALAR_ANY_VALUE = "scalar_any_value"
    SCALAR_ANY_FIELD = "scalar_any_field"
    SCALAR_ANY_REFERENCE = "scalar_any_reference"
    SCALAR_ANY_CANDIDATE = "scalar_any_candidate"
    PREDICATE_ANY_SCOPE = "predicate_any_scope"
    DISTINCT = "distinct"
    SET = "set"
    SET_OPERAND = "set_operand"
    SET_FIELD_MAP = "set_field_map"
    TYPE_EQUIVALENCE = "type_equivalence"
    TYPE_PARAMETER_SOURCE = "type_parameter_source"
    ORDER_SOURCE = "order_source"
    ORDER_BINDING = "order_binding"
    ORDER_PROOF = "order_proof"
    DIAGNOSTIC = "diagnostic"
    REQUIREMENT = "requirement"
    PROOF = "proof"
    TERMINAL_INPUT = "terminal_input"
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
    _K.DIAGNOSTIC: (
        _spec("ref", _R, _D.DIAGNOSTIC),
        _spec("code", _T),
        _spec("severity", _E),
        _spec("message", _T),
        _spec("path", _T, optional=True),
        _spec("line", _I),
        _spec("column", _I),
        _spec("end_line", _I, optional=True),
        _spec("end_column", _I, optional=True),
    ),
    _K.REQUIREMENT: (
        _spec("ref", _R, _D.REQUIREMENT),
        _spec("owner", _R, _D.OWNER_ENTRY, optional=True),
        _spec("scope", _E),
        _spec("unit", _E),
        _spec("state", _E),
        _spec("enforcement_required", _B),
        _spec("represented", _B),
        _spec("joins", _RS, _D.PLAN_NODE, optional=True),
        _spec("inputs", _RS, _D.USE, optional=True),
        _spec("proofs", _RS, _D.PROOF, optional=True),
        _spec("diagnostic", _R, _D.DIAGNOSTIC, optional=True),
        _spec("site", _T, optional=True),
        _spec("problems", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
    ),
    _K.PROOF: (
        _spec("ref", _R, _D.PROOF),
        _spec("requirement", _R, _D.REQUIREMENT),
        _spec("kind", _E),
        _spec("joins", _RS, _D.PLAN_NODE, optional=True),
        _spec("inputs", _RS, _D.USE, optional=True),
        _spec("producers", _RS, _D.OWNER_ENTRY, optional=True),
        _spec("premise_nodes", _RS, _D.PLAN_NODE, optional=True),
        _spec("children", _RS, _D.PROOF, optional=True),
        _spec("roots", ProjectQueryBlockIRPureTag.TEXTS),
    ),
    _K.TERMINAL_INPUT: (
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordinal", _I),
        _spec("blocker", _R, _D.OWNER_ENTRY),
    ),
    _K.SET: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("kind", _E),
        _spec("quantifier", _E),
        _spec("operand_count", _I),
        _spec("requires_equivalence", _B),
        _spec("full_row_unique", _B),
        _spec("origin", _R, _D.GRAIN_ORIGIN),
        _spec("span", _T),
    ),
    _K.SET_OPERAND: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("ordinal", _I),
        _spec("use", _R, _D.USE),
        _spec("producer", _R, _D.OWNER_ENTRY),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("fields", _RS, _D.ROW_FIELD, optional=True),
        _spec("types", _RS, _D.TYPE_EVIDENCE, optional=True),
    ),
    _K.SET_FIELD_MAP: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("position", _I),
        _spec("output", _R, _D.ROW_FIELD),
        _spec("inputs", _RS, _D.ROW_FIELD),
        _spec("value_uses", _RS, _D.USE),
        _spec("membership_uses", _RS, _D.USE),
    ),
    _K.DISTINCT: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("input", _R, _D.OUTPUT_VALUE),
        _spec("fields", _RS, _D.ROW_FIELD),
        _spec("types", _RS, _D.TYPE_EVIDENCE),
        _spec("origin", _R, _D.GRAIN_ORIGIN),
        _spec("nulls_equal", _B),
        _spec("full_row_unique", _B),
        _spec("clause", _T),
        _spec("order_proofs", _RS, _D.ORDER_PROOF, optional=True),
    ),
    _K.ORDER_SOURCE: (
        _spec("ref", _R, _D.ORDER_SOURCE),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("source_kind", _T),
        _spec("fields", _RS, _D.ROW_FIELD, optional=True),
        _spec("site", _T, optional=True),
    ),
    _K.ORDER_BINDING: (
        _spec("ref", _R, _D.ORDER_BINDING),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("ordering", _R, _D.PLAN_NODE),
        _spec("ordinal", _I),
        _spec("item", _T),
        _spec("mode", _E),
        _spec("visible", _RS, _D.ORDER_SOURCE, optional=True),
        _spec("targets", _RS, _D.ORDER_SOURCE, optional=True),
        _spec("property", _R, _D.RELATIONAL_PROPERTY, optional=True),
        _spec("seed", _RS, _D.VALUE_CLASS, optional=True),
        _spec("requested", _RS, _D.VALUE_CLASS, optional=True),
    ),
    _K.ORDER_PROOF: (
        _spec("ref", _R, _D.ORDER_PROOF),
        _spec("binding", _R, _D.ORDER_BINDING),
        _spec("mode", _E),
        _spec("visible", _RS, _D.ORDER_SOURCE, optional=True),
        _spec("targets", _RS, _D.ORDER_SOURCE, optional=True),
        _spec("property", _R, _D.RELATIONAL_PROPERTY, optional=True),
        _spec("seed", _RS, _D.VALUE_CLASS, optional=True),
        _spec("requested", _RS, _D.VALUE_CLASS, optional=True),
        _spec("closure", _RS, _D.VALUE_CLASS, optional=True),
        _spec("steps", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
    ),
    _K.TYPE_EQUIVALENCE: (
        _spec("ref", _R, _D.TYPE_EVIDENCE),
        _spec("field", _R, _D.ROW_FIELD),
        _spec("capability", _T),
        _spec("parents", _RS, _D.TYPE_EVIDENCE, optional=True),
        _spec("parameter_source", _R, _D.TYPE_PARAMETER_SOURCE, optional=True),
    ),
    _K.TYPE_PARAMETER_SOURCE: (
        _spec("ref", _R, _D.TYPE_PARAMETER_SOURCE),
        _spec("capability", _R, _D.TYPE_EVIDENCE),
        _spec("owner", _T),
        _spec("role", _E),
        _spec("type_name", _E),
        _spec("site", _T),
        _spec("parameters", ProjectQueryBlockIRPureTag.INTEGERS),
        _spec("argument_sites", ProjectQueryBlockIRPureTag.TEXTS),
    ),
    _K.ALGEBRA: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("output", _R, _D.OUTPUT_VALUE),
        _spec("kind", _E),
        _spec("inputs", _RS, _D.USE),
        _spec("span", _T),
    ),
    _K.CONDITION: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("mode", _E),
        _spec("scope", _E, optional=True),
        _spec("expression", _T, optional=True),
        _spec("conjuncts", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
        _spec("base", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
        _spec("references", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
    ),
    _K.INPUT_CORRESPONDENCE: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("ordinal", _I),
        _spec("use", _R, _D.USE),
        _spec("producer", _R, _D.OWNER_ENTRY, optional=True),
        _spec("output", _R, _D.OUTPUT_VALUE),
    ),
    _K.SCALAR_ANY_USE: (
        _spec("ref", _R, _D.SCALAR_ANY_USE),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("authored", _T),
        _spec("authored_owner", _T),
        _spec("authored_context", _T),
        _spec("current", _T),
        _spec("context", _T),
        _spec("owner_definition", _T),
        _spec("authored_prefix", _I),
        _spec("current_prefix", _I),
        _spec("values", _RS, _D.SCALAR_ANY_VALUE, optional=True),
    ),
    _K.SCALAR_ANY_VALUE: (
        _spec("ref", _R, _D.SCALAR_ANY_VALUE),
        _spec("use", _R, _D.SCALAR_ANY_USE),
        _spec("parent", _R, _D.SCALAR_ANY_VALUE, optional=True),
        _spec("target", _R, _D.OWNER_ENTRY, optional=True),
        _spec("context", _T),
        _spec("expression", _T),
        _spec("type", _T),
        _spec("nullability", _E),
        _spec("field_count", _I),
        _spec("input_names", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
        _spec("fields", _RS, _D.SCALAR_ANY_FIELD, optional=True),
        _spec("reference_count", _I),
        _spec("references", _RS, _D.SCALAR_ANY_REFERENCE, optional=True),
        _spec("nested", _RS, _D.SCALAR_ANY_VALUE, optional=True),
    ),
    _K.SCALAR_ANY_FIELD: (
        _spec("ref", _R, _D.SCALAR_ANY_FIELD),
        _spec("value", _R, _D.SCALAR_ANY_VALUE),
        _spec("ordinal", _I),
        _spec("name", _T),
        _spec("type", _T),
        _spec("nullability", _E),
        _spec("definition", _T),
    ),
    _K.SCALAR_ANY_REFERENCE: (
        _spec("ref", _R, _D.SCALAR_ANY_REFERENCE),
        _spec("value", _R, _D.SCALAR_ANY_VALUE),
        _spec("ordinal", _I),
        _spec("expression", _T),
        _spec("candidate_count", _I),
        _spec("candidates", _RS, _D.SCALAR_ANY_CANDIDATE, optional=True),
    ),
    _K.SCALAR_ANY_CANDIDATE: (
        _spec("ref", _R, _D.SCALAR_ANY_CANDIDATE),
        _spec("reference", _R, _D.SCALAR_ANY_REFERENCE),
        _spec("ordinal", _I),
        _spec("kind", _E),
        _spec("binding", _T),
        _spec("name", _T),
        _spec("field_name", _T),
        _spec("type", _T),
        _spec("nullability", _E),
        _spec("field", _T),
        _spec("local", _R, _D.SCALAR_ANY_USE, optional=True),
        _spec("target", _R, _D.OWNER_ENTRY, optional=True),
        _spec("position", _I, optional=True),
        _spec("field_position", _I, optional=True),
        _spec("input_names", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
        _spec("let_expression", _T, optional=True),
    ),
    _K.PREDICATE_ANY_SCOPE: (
        _spec("expression", _R, _D.PREDICATE_EXPRESSION),
        _spec("ordinal", _I),
        _spec("use", _R, _D.SCALAR_ANY_USE),
        _spec("target", _R, _D.OWNER_ENTRY, optional=True),
        _spec("relation", _T, optional=True),
        _spec("position", _E),
        _spec("container_ordinal", _I),
        _spec("read_ordinal", _I),
        _spec("before", _T),
        _spec("after", _T),
    ),
    _K.EXISTENCE_USE: (
        _spec("ref", _R, _D.EXISTENCE_USE),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("authored_owner", _T),
        _spec("context", _T),
        _spec("any", _T),
        _spec("clause", _T),
        _spec("input_ordinal", _I),
        _spec("preceding_join_count", _I),
        _spec("node", _R, _D.PLAN_NODE, optional=True),
    ),
    _K.PREDICATE_EXPRESSION: (
        _spec("ref", _R, _D.PREDICATE_EXPRESSION),
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("role", _E),
        _spec("context", _T),
        _spec("authored", _T),
        _spec("normalized", _T),
        _spec("calls", _RS, _D.PREDICATE_CALL, optional=True),
    ),
    _K.PREDICATE_CALL: (
        _spec("ref", _R, _D.PREDICATE_CALL),
        _spec("expression", _R, _D.PREDICATE_EXPRESSION),
        _spec("ordinal", _I),
        _spec("call", _T),
        _spec("template", _T),
        _spec("shapes", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
        _spec("expanded", _T),
        _spec("mandatory", ProjectQueryBlockIRPureTag.TEXTS, optional=True),
    ),
    _K.PREDICATE_ARGUMENT: (
        _spec("call", _R, _D.PREDICATE_CALL),
        _spec("ordinal", _I),
        _spec("binding", _I),
        _spec("target", _R, _D.OWNER_ENTRY),
        _spec("parameter", _T),
        _spec("argument", _T),
        _spec("occurrence", _T),
        _spec("relation", _T),
        _spec("shape", _T),
    ),
    _K.PREDICATE_JOIN: (
        _spec("node", _R, _D.PLAN_NODE),
        _spec("expression", _R, _D.PREDICATE_EXPRESSION),
        _spec("equalities", _RS, _D.PREDICATE_EQUALITY, optional=True),
        _spec("bindings", ProjectQueryBlockIRPureTag.INTEGERS),
        _spec("key_counts", ProjectQueryBlockIRPureTag.INTEGERS),
        _spec("keys", _RS, _D.PREDICATE_INPUT_KEY, optional=True),
        _spec("matches", _RS, _D.PREDICATE_KEY_MATCH, optional=True),
    ),
    _K.PREDICATE_EQUALITY: (
        _spec("ref", _R, _D.PREDICATE_EQUALITY),
        _spec("node", _R, _D.PLAN_NODE),
        _spec("position", _I),
        _spec("comparison", _T),
        _spec("left_binding", _I),
        _spec("left_field", _I),
        _spec("right_binding", _I),
        _spec("right_field", _I),
        _spec("calls", _RS, _D.PREDICATE_CALL),
    ),
    _K.PREDICATE_INPUT_KEY: (
        _spec("ref", _R, _D.PREDICATE_INPUT_KEY),
        _spec("node", _R, _D.PLAN_NODE),
        _spec("binding", _I),
        _spec("ordinal", _I),
        _spec("strength", _E),
        _spec("class_sizes", ProjectQueryBlockIRPureTag.INTEGERS),
        _spec("fields", ProjectQueryBlockIRPureTag.INTEGERS),
    ),
    _K.PREDICATE_KEY_MATCH: (
        _spec("ref", _R, _D.PREDICATE_KEY_MATCH),
        _spec("node", _R, _D.PLAN_NODE),
        _spec("key", _R, _D.PREDICATE_INPUT_KEY),
        _spec("equalities", _RS, _D.PREDICATE_EQUALITY),
        _spec("minimum", _E),
        _spec("maximum", _E),
    ),
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
    # A relation let shares its declaration's module and declaration
    # positions; this record carries the let coordinate of one let owner.
    _K.OWNER_LET: (
        _spec("owner", _R, _D.OWNER_ENTRY),
        _spec("let_position", _I),
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
    _K.SCALAR_ANY_USE: _D.SCALAR_ANY_USE,
    _K.SCALAR_ANY_VALUE: _D.SCALAR_ANY_VALUE,
    _K.SCALAR_ANY_FIELD: _D.SCALAR_ANY_FIELD,
    _K.SCALAR_ANY_REFERENCE: _D.SCALAR_ANY_REFERENCE,
    _K.SCALAR_ANY_CANDIDATE: _D.SCALAR_ANY_CANDIDATE,
    _K.EXISTENCE_USE: _D.EXISTENCE_USE,
    _K.PREDICATE_EXPRESSION: _D.PREDICATE_EXPRESSION,
    _K.PREDICATE_CALL: _D.PREDICATE_CALL,
    _K.PREDICATE_EQUALITY: _D.PREDICATE_EQUALITY,
    _K.PREDICATE_INPUT_KEY: _D.PREDICATE_INPUT_KEY,
    _K.PREDICATE_KEY_MATCH: _D.PREDICATE_KEY_MATCH,
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
    _K.TYPE_EQUIVALENCE: _D.TYPE_EVIDENCE,
    _K.TYPE_PARAMETER_SOURCE: _D.TYPE_PARAMETER_SOURCE,
    _K.ORDER_SOURCE: _D.ORDER_SOURCE,
    _K.ORDER_BINDING: _D.ORDER_BINDING,
    _K.ORDER_PROOF: _D.ORDER_PROOF,
    _K.DIAGNOSTIC: _D.DIAGNOSTIC,
    _K.REQUIREMENT: _D.REQUIREMENT,
    _K.PROOF: _D.PROOF,
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


def _let_positions(
    document: ProjectQueryBlockIRPureDocument,
) -> dict[ProjectQueryBlockIRPortableRef, int]:
    return {
        _ref(record, "owner"): _integer(record, "let_position")
        for record in _records(document, _K.OWNER_LET)
    }


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
        document.format_marker
        not in {
            PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
            PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT,
        }
        or _text(header, "format") != document.format_marker
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
        (_enumeration(record, "stage") in {"phase63", "phase64"})
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
    let_owners = tuple(
        _ref(record, "owner") for record in _records(document, _K.OWNER_LET)
    )
    if any(
        later.position <= earlier.position
        for earlier, later in zip(let_owners, let_owners[1:])
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    # A relation let shares its declaration's positions; only the let
    # coordinate tells the two owners apart.
    lets = _let_positions(document)
    if len(
        {
            (
                _text(record, "module_path"),
                _integer(record, "module_position"),
                _integer(record, "declaration_position"),
                lets.get(_ref(record, "ref")),
            )
            for record in owners
        }
    ) != len(owners):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
    schedule = _refs(document.records[0], "schedule")
    dependencies = _records(document, _K.DEPENDENCY)
    remaining = set(owner_refs)
    indegree = dict.fromkeys(owner_refs, 0)
    successors: dict[
        ProjectQueryBlockIRPortableRef, list[ProjectQueryBlockIRPortableRef]
    ] = {owner: [] for owner in owner_refs}
    for edge in dependencies:
        consumer, target = _ref(edge, "consumer"), _ref(edge, "target")
        indegree[consumer] += 1
        successors[target].append(consumer)
    ready = [owner for owner in owner_refs if indegree[owner] == 0]
    available: set[ProjectQueryBlockIRPortableRef] = set()
    # Independently check the evaluable domain using complete dependency uses.
    # Cyclic and transitively blocked owners must remain non-concrete records.
    while ready:
        owner = ready.pop()
        available.add(owner)
        remaining.remove(owner)
        for consumer in successors[owner]:
            indegree[consumer] -= 1
            if indegree[consumer] == 0:
                ready.append(consumer)
    if (
        len(schedule) != len(available)
        or set(schedule) != available
        or any(
            _enumeration(declared[owner], "variant") != "terminal"
            or _enumeration(declared[owner], "terminal_reason")
            != "semantic_output_non_concrete"
            or _enumeration(declared[owner], "blocker_kind")
            != "ProjectEffectiveOutputTerminal"
            for owner in remaining
        )
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY, 0, 10)
    positions = {owner: position for position, owner in enumerate(schedule)}
    if any(
        positions[_ref(edge, "target")] >= positions[_ref(edge, "consumer")]
        for edge in dependencies
        if _ref(edge, "consumer") in available
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY, 0, 10)
    variants = {"reused", "rebound", "completed", "terminal"}
    if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        variants.add("set")
    terminal_reasons = {
        "semantic_output_non_concrete",
        "active_upstream_ir_non_concrete",
        "active_upstream_row_incompatible",
        "effective_join_input_rebind_unsupported",
    }
    if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        terminal_reasons.update(
            ("invalid_single_match", "active_inputs_ir_non_concrete")
        )
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
            if reason in {"invalid_single_match", "active_inputs_ir_non_concrete"}:
                valid_blocker = (
                    blocker_kind.enumeration == "tuple"
                    and blocker_entry.tag is ProjectQueryBlockIRPureTag.ABSENT
                    and blocker_uses.tag is ProjectQueryBlockIRPureTag.ABSENT
                )
            elif reason == "semantic_output_non_concrete":
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
        } | (
            {"ProjectResolvedSetOperand"}
            if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
            else set()
        ):
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
        _enumeration(node, "stage")
        not in (
            {"phase61", "phase62", "phase63", "phase64"}
            if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
            else {"phase61", "phase62", "phase63"}
        )
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
        | (
            {"set_input"}
            if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
            else set()
        )
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
    if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        allowed.update(("distinct", "set_operation"))
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
            | (
                {"set_operation"}
                if document.format_marker
                == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
                else set()
            )
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
                | (
                    {"ProjectIRJoinedRowField", "ProjectCompletedSetOutputField"}
                    if document.format_marker
                    == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
                    else set()
                )
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
            if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
                canonical = tuple(
                    operator
                    for operator in _records(document, _K.OPERATOR)
                    if _ref(operator, "row_output") == output_ref
                    and _enumeration(operator, "kind")
                    in {"final_projection", "set_operation"}
                )
                if canonical and (
                    len(canonical) != 1
                    or not all(present)
                    or final_values[1].enumeration != "relation_output"
                    or _ref(canonical[0], "owner") != owner_ref
                    or _ref(canonical[0], "node")
                    != _ref(declared[output_ref], "producer")
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
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
        } | (
            {"unknown"}
            if document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
            else set()
        ):
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
            factor_kind
            not in (
                {"source_domain", "group_domain", "distinct_domain", "set_domain"}
                if document.format_marker
                == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
                else {"source_domain", "group_domain"}
            )
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
        elif (
            kind in {"set_alternatives", "set_quotient", "set_subset"}
            and document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
        ):
            if (kind == "set_subset" and factor_refs) or any(
                _enumeration(declared[ref], "kind") != "set_domain"
                for ref in factor_refs
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        elif (
            kind == "distinct_quotient"
            and document.format_marker == PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT
        ):
            if any(
                _enumeration(declared[ref], "kind") != "distinct_domain"
                for ref in factor_refs
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        else:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        matching_operators = tuple(
            operator
            for operator in _records(document, _K.OPERATOR)
            if _ref(operator, "node") == _ref(origin, "operator")
            and _enumeration(operator, "kind")
            == (
                "distinct"
                if kind == "distinct_quotient"
                else "set_operation"
                if kind.startswith("set_")
                else "group_aggregate"
            )
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
            _validate_algebra,
            _validate_predicates,
            _validate_existence,
            _validate_scalar_any,
            _validate_predicate_any_scopes,
            _validate_distincts,
            _validate_sets,
            _validate_requirements,
            _validate_analysis,
        ):
            rejection = validation(document, declared)
            if rejection is not None:
                return rejection
        return ProjectQueryBlockIRPureOutcome(
            status=ProjectQueryBlockIRPureStatus.OK,
            canonical_bytes=_encode_document(document),
        )
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        RecursionError,
        OverflowError,
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT)


def _authored_field_leaves(value: object) -> tuple[object, ...]:
    """Read ordered portable syntax occurrences, excluding function callees."""
    if type(value) is dict:
        if value.get("node") == "AnyExpr":
            return ()
        if value.get("node") in {"NameExpr", "DottedNameExpr"}:
            return (value,)
        return tuple(
            leaf
            for key, child in value.items()
            if key not in {"span", "callee"}
            for leaf in _authored_field_leaves(child)
        )
    if type(value) is list:
        return tuple(leaf for child in value for leaf in _authored_field_leaves(child))
    return ()


def _validate_algebra(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    algebra = _records(document, _K.ALGEBRA)
    conditions = _records(document, _K.CONDITION)
    inputs = _records(document, _K.INPUT_CORRESPONDENCE)
    active_nodes: set[ProjectQueryBlockIRPortableRef] = set()
    pending = [
        _ref(declared[ref], "producer")
        for owner in _records(document, _K.OWNER_ENTRY)
        if (ref := _field(owner, "active_output").ref) is not None
    ]
    by_consumer: dict[
        ProjectQueryBlockIRPortableRef, list[ProjectQueryBlockIRPureRecord]
    ] = {}
    for use in _records(document, _K.USE):
        by_consumer.setdefault(
            _ref(declared[_ref(use, "slot")], "consumer"), []
        ).append(use)
    while pending:
        node = pending.pop()
        if node in active_nodes:
            continue
        active_nodes.add(node)
        pending.extend(
            _ref(declared[_ref(use, "output")], "producer")
            for use in by_consumer.get(node, ())
        )
    nodes = tuple(
        _ref(record, "ref")
        for record in _records(document, _K.NODE)
        if _ref(record, "ref") in active_nodes
        and any(
            _enumeration(use, "kind") == "join_input"
            for use in by_consumer.get(_ref(record, "ref"), ())
        )
    )
    if document.format_marker == PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT:
        return (
            _reject(ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND)
            if algebra or conditions or inputs
            else None
        )
    if (
        tuple(_ref(record, "node") for record in algebra) != nodes
        or tuple(_ref(record, "node") for record in conditions) != nodes
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    if len(inputs) != 2 * len(algebra):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
    previous_by_owner: dict[
        ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord
    ] = {}
    for index, (operator, condition) in enumerate(
        zip(algebra, conditions, strict=True)
    ):
        kind = _enumeration(operator, "kind")
        node, owner, output = (
            _ref(operator, "node"),
            _ref(operator, "owner"),
            _ref(operator, "output"),
        )
        uses = _refs(operator, "inputs")
        if (
            kind not in {"inner", "left", "right", "full", "cross", "semi", "anti"}
            or len(uses) != 2
            or len(set(uses)) != 2
            or _ref(declared[output], "producer") != node
            or _ref(declared[output], "owner") != owner
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        actual_uses = tuple(
            _ref(use, "ref")
            for use in _records(document, _K.USE)
            if _ref(declared[_ref(use, "slot")], "consumer") == node
        )
        if actual_uses != uses:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        for ordinal, image in enumerate(inputs[2 * index : 2 * index + 2]):
            use = declared[uses[ordinal]]
            slot = declared[_ref(use, "slot")]
            if (
                _ref(image, "node") != node
                or _integer(image, "ordinal") != ordinal
                or _ref(image, "use") != uses[ordinal]
                or _ref(image, "output") != _ref(use, "output")
                or _integer(slot, "ordinal") != ordinal
                or _ref(slot, "consumer") != node
                or _field(use, "owner").ref != owner
                or _enumeration(use, "kind") != "join_input"
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
            producer = _field(image, "producer").ref
            incoming_ref = _ref(image, "output")
            incoming = declared[incoming_ref]
            previous = previous_by_owner.get(owner)
            if ordinal == 0 and previous is not None:
                # The accumulated left input is the actual preceding JOIN result.
                if (
                    producer is not None
                    or incoming_ref != _ref(previous, "output")
                    or _ref(incoming, "producer") != _ref(previous, "node")
                    or _field(incoming, "owner").ref != owner
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
            else:
                if (
                    producer is None
                    or producer == owner
                    or _field(incoming, "owner").ref != producer
                    or _enumeration(declared[producer], "variant") == "terminal"
                    or _field(declared[producer], "active_output").ref != incoming_ref
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
                property_ref = _ref(declared[producer], "active_property")
                if (
                    _ref(declared[property_ref], "owner") != producer
                    or _ref(declared[property_ref], "output") != incoming_ref
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
        mode = _enumeration(condition, "mode")
        expression = _field(condition, "expression")
        scope = _field(condition, "scope")
        base = _field(condition, "base").texts
        conjuncts = _field(condition, "conjuncts").texts
        references = _field(condition, "references").texts
        if kind == "cross":
            if (
                mode != "M5"
                or expression.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or scope.tag is not ProjectQueryBlockIRPureTag.ABSENT
                or base
                or conjuncts
                or references
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        elif (
            mode not in {"M1", "M2", "M3", "M4"}
            or (mode in {"M3", "M4"})
            != (expression.tag is ProjectQueryBlockIRPureTag.TEXT)
            or (mode in {"M1", "M2", "M4"}) != bool(base)
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        expected_scope = {
            "M3": "generic_join_match",
            "M4": "join_local_on_refinement",
        }.get(mode)
        if scope.enumeration != expected_scope:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        span = json.loads(_text(operator, "span"))
        if (
            type(span) is not dict
            or set(span) != {"path", "line", "column", "end_line", "end_column"}
            or type(span["path"]) is not str
            or span["path"].startswith("/")
            or any(
                type(span[key]) is not int or span[key] < 1
                for key in ("line", "column", "end_line", "end_column")
            )
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        expression_data = (
            None if expression.text is None else json.loads(expression.text)
        )
        if tuple(
            json.loads(reference)["expression"] for reference in references
        ) != _authored_field_leaves(expression_data):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        for ordinal, reference in enumerate(references):
            item = json.loads(reference)
            if (
                type(item) is not dict
                or set(item)
                != {
                    "position",
                    "expression",
                    "state",
                    "binding_candidates",
                    "candidates",
                    "target",
                }
                or item["position"] != ordinal
                or item["state"] != "resolved"
                or type(item["candidates"]) is not list
                or len(item["candidates"]) != 1
                or item["target"] != item["candidates"][0]["position"]
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        for encoded in (
            *base,
            *conjuncts,
            *((expression.text,) if expression.text is not None else ()),
        ):
            if type(json.loads(encoded)) is not dict:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        previous_by_owner[owner] = operator
    return None


def _validate_distincts(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    operators = tuple(
        operator
        for operator in _records(document, _K.OPERATOR)
        if _enumeration(operator, "kind") == "distinct"
    )
    records = _records(document, _K.DISTINCT)
    types = _records(document, _K.TYPE_EQUIVALENCE)
    lets = _let_positions(document)
    if document.format_marker != PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        return (
            _reject(ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND)
            if records
            or types
            or any(
                _records(document, kind)
                for kind in (
                    _K.TYPE_PARAMETER_SOURCE,
                    _K.ORDER_SOURCE,
                    _K.ORDER_BINDING,
                    _K.ORDER_PROOF,
                )
            )
            else None
        )
    if tuple(_ref(record, "node") for record in records) != tuple(
        _ref(operator, "node") for operator in operators
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    all_types = tuple(
        ref
        for record in (*records, *_records(document, _K.SET_OPERAND))
        for ref in _refs(record, "types")
    )
    problem = _validate_type_evidence(document, declared, all_types)
    if problem is not None:
        return problem
    for operator, record in zip(operators, records, strict=True):
        node = _ref(record, "node")
        uses = tuple(
            use
            for use in _records(document, _K.USE)
            if _ref(declared[_ref(use, "slot")], "consumer") == node
        )
        if (
            len(uses) != 1
            or _ref(uses[0], "output") != _ref(record, "input")
            or not _boolean(record, "nulls_equal")
            or not _boolean(record, "full_row_unique")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        inputs = tuple(
            p
            for p in _records(document, _K.RELATIONAL_PROPERTY)
            if _ref(p, "output") == _ref(record, "input")
        )
        if (
            len(inputs) != 1
            or _refs(record, "fields") != _refs(inputs[0], "fields")
            or len(_refs(record, "fields")) != len(_refs(record, "types"))
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        input_node = _ref(declared[_ref(record, "input")], "producer")
        projection = tuple(
            op
            for op in _records(document, _K.OPERATOR)
            if _ref(op, "node") == input_node
            and _enumeration(op, "kind") == "final_projection"
            and _ref(op, "owner") == _ref(operator, "owner")
        )
        if len(projection) != 1:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        origin = declared[_ref(record, "origin")]
        if (
            origin.kind is not _K.GRAIN_ORIGIN
            or _ref(origin, "operator") != node
            or _enumeration(origin, "kind") != "distinct_quotient"
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        for field_ref, type_ref in zip(
            _refs(record, "fields"), _refs(record, "types"), strict=True
        ):
            evidence = declared[type_ref]
            if (
                evidence.kind is not _K.TYPE_EQUIVALENCE
                or _ref(evidence, "field") != field_ref
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
            data = json.loads(_text(evidence, "capability"))
            _type_capability_key(evidence, declared, True)
            if not _capability_field_matches(data, field_ref, declared, lets):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        if type(json.loads(_text(record, "clause"))) is not dict:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        owner_ref = _ref(operator, "owner")
        orderings = tuple(
            item
            for item in _records(document, _K.OPERATOR)
            if _ref(item, "owner") == owner_ref
            and _enumeration(item, "kind") == "relation_ordering"
        )
        ordering_properties = tuple(
            item
            for item in _records(document, _K.RELATIONAL_PROPERTY)
            if orderings and _ref(item, "output") == _ref(orderings[0], "row_output")
        )
        expected_count = (
            len(_enumerations(ordering_properties[0], "order_directions"))
            if len(orderings) == len(ordering_properties) == 1
            else 0
        )
        if (
            len(orderings) > 1
            or orderings
            and len(ordering_properties) != 1
            or len(_refs(record, "order_proofs")) != expected_count
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        ordering_node = _ref(orderings[0], "node") if len(orderings) == 1 else None
        for ordinal, ref in enumerate(_refs(record, "order_proofs")):
            proof = declared[ref]
            binding = declared[_ref(proof, "binding")]
            if (
                _integer(binding, "ordinal") != ordinal
                or _ref(binding, "owner") != owner_ref
                or _ref(binding, "ordering") != ordering_node
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    return _validate_order_proofs(document, declared)


def _validate_order_proofs(document, declared) -> ProjectQueryBlockIRPureOutcome | None:
    proofs = _records(document, _K.ORDER_PROOF)
    bindings = _records(document, _K.ORDER_BINDING)
    sources = _records(document, _K.ORDER_SOURCE)
    if tuple(
        ref
        for record in _records(document, _K.DISTINCT)
        for ref in _refs(record, "order_proofs")
    ) != tuple(_ref(proof, "ref") for proof in proofs):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    if tuple(_ref(proof, "binding") for proof in proofs) != tuple(
        _ref(binding, "ref") for binding in bindings
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    seen_sources = []
    for proof, binding in zip(proofs, bindings, strict=True):
        mode = _enumeration(proof, "mode")
        if mode not in {"visible", "strict_fd"} or any(
            _field(proof, key) != _field(binding, key)
            for key in ("mode", "visible", "targets", "property", "seed", "requested")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        if type(json.loads(_text(binding, "item"))) is not dict:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        visible, targets = _refs(proof, "visible"), _refs(proof, "targets")
        for ref in (*visible, *targets):
            if _ref(declared[ref], "owner") != _ref(binding, "owner"):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
            if ref not in seen_sources:
                seen_sources.append(ref)
        if mode == "visible":
            if any(ref not in visible for ref in targets) or any(
                _field(proof, key).tag is not ProjectQueryBlockIRPureTag.ABSENT
                for key in ("property", "seed", "requested", "closure", "steps")
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            continue
        if visible or targets or _field(proof, "property").ref is None:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        prop_ref = _ref(proof, "property")
        prop = declared[prop_ref]
        producer = _ref(declared[_ref(prop, "output")], "producer")
        projections = tuple(
            _ref(declared[_ref(distinct, "input")], "producer")
            for distinct in _records(document, _K.DISTINCT)
            if _ref(proof, "ref") in _refs(distinct, "order_proofs")
        )
        reachability = tuple(
            _refs(analysis, "reachable")
            for analysis in _records(document, _K.ANALYSIS_REACHABILITY)
            if _ref(analysis, "source") == producer
        )
        if len(projections) != 1 or len(reachability) != 1:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        if projections[0] != producer and projections[0] not in reachability[0]:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        universe = _refs(prop, "value_classes")
        seed, requested, closure = (
            _refs(proof, key) for key in ("seed", "requested", "closure")
        )
        if any(ref not in universe for ref in (*seed, *requested, *closure)) or any(
            tuple(ref for ref in universe if ref in values) != values
            for values in (seed, requested, closure)
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        known = set(seed)
        for encoded in _field(proof, "steps").texts:
            step = json.loads(encoded)
            if (
                type(step) is not dict
                or set(step) != {"fact", "derived"}
                or type(step["fact"]) is not int
                or type(step["derived"]) is not list
                or any(type(i) is not int for i in step["derived"])
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
            fact_ref = ProjectQueryBlockIRPortableRef(
                domain=_D.VALUE_FD, position=step["fact"]
            )
            derived = tuple(
                ProjectQueryBlockIRPortableRef(domain=_D.VALUE_CLASS, position=i)
                for i in step["derived"]
            )
            if fact_ref not in _refs(prop, "value_fds"):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
            fact = declared[fact_ref]
            if (
                _ref(fact, "property") != prop_ref
                or _enumeration(fact, "strength") != "strict"
                or any(ref not in known for ref in _refs(fact, "determinants"))
                or derived
                != tuple(ref for ref in _refs(fact, "dependents") if ref not in known)
                or not derived
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            known.update(derived)
        if closure != tuple(ref for ref in universe if ref in known) or any(
            ref not in known for ref in requested
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
    if tuple(seen_sources) != tuple(_ref(source, "ref") for source in sources):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    return None


def _field_identity_valid(value: object) -> bool:
    if type(value) is not dict or set(value) != {
        "owner",
        "kind",
        "field_position",
        "name",
    }:
        return False
    owner = value["owner"]
    # Only a relation let's owner carries a let coordinate.
    if type(owner) is not dict or set(owner) - {"let_position"} != {
        "identity",
        "module_position",
        "declaration_position",
    }:
        return False
    identity = owner["identity"]
    if type(identity) is not dict or set(identity) != {
        "module_path",
        "namespace",
        "declaration_kind",
        "declared_name",
    }:
        return False
    return (
        all(type(identity[key]) is str and identity[key] for key in identity)
        and not identity["module_path"].startswith("/")
        and "\\" not in identity["module_path"]
        and all(
            type(owner[key]) is int and owner[key] >= 0
            for key in owner
            if key != "identity"
        )
        and type(value["field_position"]) is int
        and value["field_position"] >= 0
        and type(value["name"]) is str
        and bool(value["name"])
        and value["kind"] in {"shape_field", "source_field", "relation_output"}
    )


def _capability_field_matches(data, field_ref, declared, lets) -> bool:
    field_record = declared[field_ref]
    owner_ref = _field(field_record, "final_owner").ref
    if owner_ref is None:
        return False
    owner = declared[owner_ref]
    expected_owner: dict[str, object] = {
        "identity": {
            key: _text(owner, key)
            if key in {"module_path", "declared_name"}
            else _enumeration(owner, key)
            for key in (
                "module_path",
                "namespace",
                "declaration_kind",
                "declared_name",
            )
        },
        "module_position": _integer(owner, "module_position"),
        "declaration_position": _integer(owner, "declaration_position"),
    }
    if owner_ref in lets:
        expected_owner["let_position"] = lets[owner_ref]
    expected = {
        "owner": expected_owner,
        "kind": _enumeration(field_record, "final_kind"),
        "field_position": _integer(field_record, "final_position"),
        "name": _text(field_record, "final_name"),
    }
    return data["selected"] == expected


def _capability_key(
    data: object,
    requires_equivalence: bool,
    parents: tuple[tuple[object, ...], ...] = (),
) -> tuple[object, ...]:
    if type(data) is not dict or set(data) != {
        "selected",
        "kind",
        "name",
        "nominal",
        "declared",
        "aliases",
        "decimal",
        "reason",
        "declaration_owner",
        "declaration_role",
    }:
        raise ValueError("Unrecognized type capability fields.")
    if not _field_identity_valid(data["selected"]):
        raise ValueError("Type evidence requires its closed selected field identity.")
    kind, name, reason = data["kind"], data["name"], data["reason"]
    if (
        kind not in {"builtin", "enum"}
        or type(name) is not str
        or reason
        not in {None, "unsupported_type", "float_equivalence_deferred_to_phase72"}
    ):
        raise ValueError("Set requires concrete canonical type evidence.")
    if requires_equivalence and reason is not None:
        raise ValueError("Operation requires approved row equivalence.")
    if kind == "builtin" and name not in {
        "Bool",
        "Int",
        "Text",
        "Date",
        "Timestamp",
        "UUID",
        "Decimal",
        "Float",
        "Any",
        "Bytes",
        "Json",
    }:
        raise ValueError("Unknown builtin type capability.")
    if (
        requires_equivalence
        and kind == "builtin"
        and name in {"Float", "Any", "Bytes", "Json"}
    ):
        raise ValueError("Unsupported row-equivalence domain.")
    decimal = data["decimal"]
    if name == "Decimal":
        if (
            type(decimal) is not list
            or len(decimal) != 2
            or any(type(v) is not int for v in decimal)
            or not 0 <= decimal[1] <= decimal[0]
            or decimal[0] < 1
        ):
            raise ValueError("Decimal requires validated exact precision and scale.")
    elif decimal is not None:
        raise ValueError("Only Decimal carries parameter evidence.")
    if type(data["aliases"]) is not list or type(data["selected"]) is not dict:
        raise ValueError("Type source evidence must be closed and complete.")
    nominal = data["nominal"]
    if kind == "enum" and nominal is None:
        if not parents:
            raise ValueError("Nominal type requires its exact source identity.")
        nominal = parents[0][2]
    key = (kind, name, nominal, None if decimal is None else tuple(decimal))
    if any(parent != key for parent in parents):
        raise ValueError("Inherited type sources disagree.")
    return key


def _type_capability_key(record, declared, requires):
    parents = tuple(
        _type_capability_key(declared[ref], declared, requires)
        for ref in _refs(record, "parents")
    )
    return _capability_key(json.loads(_text(record, "capability")), requires, parents)


def _source_site_valid(value: object) -> bool:
    if type(value) is not dict or set(value) != {
        "path",
        "line",
        "column",
        "end_line",
        "end_column",
    }:
        return False
    if (
        type(value["path"]) is not str
        or not value["path"]
        or value["path"].startswith("/")
        or "\\" in value["path"]
    ):
        return False
    if any(
        type(value[key]) is not int or value[key] < 1
        for key in ("line", "column", "end_line", "end_column")
    ):
        return False
    return (value["line"], value["column"]) <= (value["end_line"], value["end_column"])


def _validate_type_evidence(document, declared, roots):
    types = _records(document, _K.TYPE_EQUIVALENCE)
    lets = _let_positions(document)
    sources = _records(document, _K.TYPE_PARAMETER_SOURCE)
    refs = tuple(_ref(record, "ref") for record in types)
    parents = tuple(ref for record in types for ref in _refs(record, "parents"))
    if (*roots, *parents) != refs:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    linked_sources = []
    for record in types:
        ref = _ref(record, "ref")
        if any(parent.position <= ref.position for parent in _refs(record, "parents")):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        data = json.loads(_text(record, "capability"))
        _type_capability_key(record, declared, False)
        if not _capability_field_matches(data, _ref(record, "field"), declared, lets):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        source_ref = _field(record, "parameter_source").ref
        has_parents = bool(_refs(record, "parents"))
        decimal = data["decimal"]
        if decimal is None:
            if source_ref is not None:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
            continue
        if has_parents:
            if source_ref is not None:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
            continue
        if source_ref is None:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        source = declared[source_ref]
        linked_sources.append(source_ref)
        if (
            _ref(source, "capability") != ref
            or _enumeration(source, "type_name") != "Decimal"
            or list(_field(source, "parameters").integers) != decimal
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        owner = json.loads(_text(source, "owner"))
        site = json.loads(_text(source, "site"))
        if (
            type(owner) is not dict
            or set(owner) != {"identity", "module_position", "declaration_position"}
            or type(owner["identity"]) is not dict
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        identity = owner["identity"]
        role = _enumeration(source, "role")
        declaration_kind = {"type_alias_base": "type", "shape_field_type": "shape"}.get(
            role
        )
        if (
            declaration_kind is None
            or set(identity)
            != {"module_path", "namespace", "declaration_kind", "declared_name"}
            or identity["namespace"] != "type"
            or identity["declaration_kind"] != declaration_kind
            or type(identity["declared_name"]) is not str
            or not identity["declared_name"]
            or any(
                type(owner[key]) is not int or owner[key] < 0
                for key in ("module_position", "declaration_position")
            )
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        aliases = data["aliases"]
        if aliases:
            if (
                owner["identity"] != aliases[-1]
                or _enumeration(source, "role") != "type_alias_base"
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        elif (
            owner != data["declaration_owner"]
            or _enumeration(source, "role") != data["declaration_role"]
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if not _source_site_valid(site) or site.get("path") != identity["module_path"]:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        argument_sites = tuple(
            json.loads(item) for item in _field(source, "argument_sites").texts
        )
        if len(argument_sites) != 2 or any(
            not _source_site_valid(item)
            or item.get("path") != site.get("path")
            or (item["line"], item["column"]) < (site["line"], site["column"])
            or (item["end_line"], item["end_column"])
            > (site["end_line"], site["end_column"])
            for item in argument_sites
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        starts = tuple((item["line"], item["column"]) for item in argument_sites)
        if starts[0] >= starts[1]:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
    if tuple(linked_sources) != tuple(_ref(source, "ref") for source in sources):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    return None


def _validate_sets(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    sets = _records(document, _K.SET)
    operands = _records(document, _K.SET_OPERAND)
    mappings = _records(document, _K.SET_FIELD_MAP)
    lets = _let_positions(document)
    if document.format_marker != PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        return (
            _reject(ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND)
            if sets or operands or mappings
            else None
        )
    operators = tuple(
        operator
        for operator in _records(document, _K.OPERATOR)
        if _enumeration(operator, "kind") == "set_operation"
    )
    if tuple(_ref(record, "node") for record in sets) != tuple(
        _ref(operator, "node") for operator in operators
    ):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
    if len(operands) != sum(_integer(record, "operand_count") for record in sets):
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_COUNT)
    seen_operands: list[ProjectQueryBlockIRPureRecord] = []
    seen_mappings: list[ProjectQueryBlockIRPureRecord] = []
    for operator, record in zip(operators, sets, strict=True):
        node, owner = _ref(record, "node"), _ref(operator, "owner")
        kind, quantifier = (
            _enumeration(record, "kind"),
            _enumeration(record, "quantifier"),
        )
        count = _integer(record, "operand_count")
        requires = not (kind == "union" and quantifier == "all")
        if (
            kind not in {"union", "intersect", "except"}
            or quantifier not in {"all", "distinct"}
            or count < 2
            or _boolean(record, "requires_equivalence") != requires
            or _boolean(record, "full_row_unique") != (quantifier == "distinct")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_OPERATOR)
        result = tuple(
            p
            for p in _records(document, _K.RELATIONAL_PROPERTY)
            if _ref(p, "output") == _ref(record, "output")
        )
        if len(result) != 1 or _ref(result[0], "owner") != owner:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        fields = _refs(result[0], "fields")
        local = tuple(item for item in operands if _ref(item, "node") == node)
        seen_operands.extend(local)
        if len(local) != count or tuple(
            _integer(item, "ordinal") for item in local
        ) != tuple(range(count)):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        uses = tuple(_ref(item, "use") for item in local)
        actual_uses = tuple(
            _ref(use, "ref")
            for use in _records(document, _K.USE)
            if _ref(declared[_ref(use, "slot")], "consumer") == node
        )
        if uses != actual_uses or len(set(uses)) != count:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        type_keys: list[tuple[object, ...]] = []
        for ordinal, operand in enumerate(local):
            use = declared[_ref(operand, "use")]
            producer = declared[_ref(operand, "producer")]
            if (
                _enumeration(use, "kind") != "set_input"
                or _integer(declared[_ref(use, "slot")], "ordinal") != ordinal
                or _ref(use, "output") != _ref(operand, "output")
                or _field(producer, "active_output").ref != _ref(operand, "output")
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING)
            provided = declared[_ref(producer, "active_property")]
            input_fields = _refs(operand, "fields")
            input_types = _refs(operand, "types")
            if (
                len(input_fields) != len(fields)
                or len(input_types) != len(fields)
                or input_fields != _refs(provided, "fields")
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
            if not any(
                _ref(d, "consumer") == owner
                and _ref(d, "target") == _ref(operand, "producer")
                and _integer(d, "ordinal") == ordinal
                and _enumeration(d, "evidence_kind") == "ProjectResolvedSetOperand"
                for d in _records(document, _K.DEPENDENCY)
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
            keys = []
            for field, cap in zip(input_fields, input_types, strict=True):
                evidence = declared[cap]
                if (
                    evidence.kind is not _K.TYPE_EQUIVALENCE
                    or _ref(evidence, "field") != field
                ):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
                data = json.loads(_text(evidence, "capability"))
                if not _capability_field_matches(data, field, declared, lets):
                    return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
                keys.append(_type_capability_key(evidence, declared, requires))
            type_keys.append(tuple(keys))
        if any(keys != type_keys[0] for keys in type_keys):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        local_maps = tuple(item for item in mappings if _ref(item, "node") == node)
        seen_mappings.extend(local_maps)
        if len(local_maps) != len(fields):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        for position, image in enumerate(local_maps):
            expected_inputs = tuple(
                _refs(operand, "fields")[position] for operand in local
            )
            output = declared[fields[position]]
            if (
                _integer(image, "position") != position
                or _ref(image, "output") != fields[position]
                or _refs(image, "inputs") != expected_inputs
                or _refs(image, "membership_uses") != uses
                or _refs(image, "value_uses")
                != (uses[:1] if kind == "except" else uses)
                or _text(output, "name") != _text(declared[expected_inputs[0]], "name")
                or _ref(output, "final_owner") != owner
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_PROPERTY)
        origin = declared[_ref(record, "origin")]
        expected_origin = (
            "set_quotient"
            if quantifier == "distinct"
            else "set_alternatives"
            if kind == "union"
            else "set_subset"
        )
        if (
            origin.kind is not _K.GRAIN_ORIGIN
            or _ref(origin, "operator") != node
            or _enumeration(origin, "kind") != expected_origin
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_GRAIN)
        if type(json.loads(_text(record, "span"))) is not dict:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
    if tuple(seen_operands) != operands or tuple(seen_mappings) != mappings:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_SECTION_ORDER)
    return None


def _proof_root_valid(data, proof, requirement, declared) -> bool:
    schemas = {
        "ProjectExistingEffectiveOutput": {"owner"},
        "ProjectCompletedEffectiveOutput": {"owner"},
        "ProjectCompletedSetOutput": {"owner"},
        "ProjectSingleMatchProof": {"child", "proof_kind"},
        "ProjectRelationshipPath": {"steps"},
        "ProjectRelationshipPathStep": {"position", "guarantee"},
        "ProjectRefinedMatchBounds": {"base", "maximum", "minimum"},
        "ProjectDirectionalRelationshipMatchGuarantee": {
            "module",
            "relationship_position",
            "source_endpoint",
            "target_endpoint",
            "maximum",
            "minimum",
            "maximum_evidence",
            "source_matched",
            "target_matched",
        },
        "ProjectJoinCondition": {"mode", "clause"},
        "ProjectJoinConditionKeyMatch": {"key_match"},
        "ProjectJoinConditionEquality": {"equality"},
        "ProjectIROutputCandidateKey": {"key_matches"},
        "ProjectRelationLimit": {"owner", "bound", "clause"},
        "ProjectIRBinaryJoinOccurrence": {"nodes"},
        "ProjectCurrentBinaryJoin": {"nodes"},
        "ProjectIRJoinInputUseOccurrence": {"uses"},
        "ProjectIRLogicalOperatorOccurrence": {"operator_kind", "premise_nodes"},
        "ProjectConcreteNoJoinReplay": {"owner", "mode"},
        "ProjectConcreteJoinedAggregation": {"owner", "mode"},
    }
    if type(data) is not dict or type(data.get("kind")) is not str:
        return False
    kind = data["kind"]
    if kind not in schemas or set(data) != {"kind", *schemas[kind]}:
        return False
    for name, domain in (
        ("key_match", _D.PREDICATE_KEY_MATCH),
        ("equality", _D.PREDICATE_EQUALITY),
    ):
        if name in data:
            position = data[name]
            if type(position) is not int or position < 0:
                return False
            ref = ProjectQueryBlockIRPortableRef(domain=domain, position=position)
            if ref not in declared or _ref(declared[ref], "node") not in _refs(
                proof, "joins"
            ):
                return False
    if "key_matches" in data:
        values = data["key_matches"]
        if (
            type(values) is not list
            or not values
            or any(type(value) is not int or value < 0 for value in values)
        ):
            return False
        for position in values:
            ref = ProjectQueryBlockIRPortableRef(
                domain=_D.PREDICATE_KEY_MATCH, position=position
            )
            if ref not in declared or _ref(declared[ref], "node") not in _refs(
                proof, "joins"
            ):
                return False
    if "owner" in data:
        owner = data["owner"]
        allowed = (*_refs(proof, "producers"), _ref(requirement, "owner"))
        if type(owner) is not int or owner not in {ref.position for ref in allowed}:
            return False
    for key, field in (
        ("nodes", "joins"),
        ("uses", "inputs"),
        ("premise_nodes", "premise_nodes"),
    ):
        if key in data and (
            type(data[key]) is not list
            or any(
                type(position) is not int
                or position not in {ref.position for ref in _refs(proof, field)}
                for position in data[key]
            )
        ):
            return False
    if kind == "ProjectSingleMatchProof":
        child = data["child"]
        children = _refs(proof, "children")
        if (
            type(child) is not int
            or not 0 <= child < len(children)
            or _enumeration(declared[children[child]], "kind") != data["proof_kind"]
        ):
            return False
    for key in ("base", "guarantee"):
        if key in data and not _proof_root_valid(
            data[key], proof, requirement, declared
        ):
            return False
    if kind == "ProjectRelationshipPath" and (
        type(data["steps"]) is not list
        or not data["steps"]
        or any(
            not _proof_root_valid(step, proof, requirement, declared)
            or step["kind"] != "ProjectRelationshipPathStep"
            or step["position"] != position
            for position, step in enumerate(data["steps"])
        )
    ):
        return False
    return True


def _validate_requirements(
    document: ProjectQueryBlockIRPureDocument,
    declared: dict[ProjectQueryBlockIRPortableRef, ProjectQueryBlockIRPureRecord],
) -> ProjectQueryBlockIRPureOutcome | None:
    requirements = _records(document, _K.REQUIREMENT)
    proofs = _records(document, _K.PROOF)
    diagnostics = _records(document, _K.DIAGNOSTIC)
    failures = _records(document, _K.TERMINAL_INPUT)
    if document.format_marker != PROJECT_FLAT_RELATIONAL_IR_INSPECTION_FORMAT:
        return (
            _reject(ProjectQueryBlockIRPureStatus.INVALID_RECORD_KIND)
            if requirements or proofs or diagnostics or failures
            else None
        )
    for diagnostic in diagnostics:
        if (
            _enumeration(diagnostic, "severity") not in {"warning", "error"}
            or _integer(diagnostic, "line") < 1
            or _integer(diagnostic, "column") < 1
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        path = _field(diagnostic, "path").text
        if path is not None and (path.startswith("/") or "\\" in path):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
    incoming: dict[
        ProjectQueryBlockIRPortableRef, tuple[ProjectQueryBlockIRPortableRef, ...]
    ] = {}
    for operator in _records(document, _K.ALGEBRA):
        incoming[_ref(operator, "node")] = _refs(operator, "inputs")
    roots: list[ProjectQueryBlockIRPortableRef] = []
    for requirement in requirements:
        owner_ref = _field(requirement, "owner").ref
        if owner_ref is None:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        owner = declared[owner_ref]
        state, scope, unit = (
            _enumeration(requirement, key) for key in ("state", "scope", "unit")
        )
        represented = _boolean(requirement, "represented")
        joins, inputs, source_proofs = (
            _refs(requirement, key) for key in ("joins", "inputs", "proofs")
        )
        roots.extend(source_proofs)
        if state not in {"proved", "legal_unproved", "invalid"} or _boolean(
            requirement, "enforcement_required"
        ) != (state == "legal_unproved"):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if state != "invalid" and (
            scope not in {"direct_binary", "path_hop", "whole_path"}
            or unit != "actual_matched_bag_occurrence"
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if represented != (
            _enumeration(owner, "variant") != "terminal" and state != "invalid"
        ) or (state == "proved") != bool(source_proofs):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        if represented:
            if (
                not joins
                or (scope != "whole_path" and len(joins) != 1)
                or inputs
                != tuple(use for node in joins for use in incoming.get(node, ()))
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
            if len(inputs) != 2 * len(joins) or len(set(joins)) != len(joins):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        elif joins or inputs:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_ENTRY)
        diagnostic = _field(requirement, "diagnostic").ref
        if state == "proved":
            if diagnostic is not None:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        elif (
            diagnostic is None
            or _text(declared[diagnostic], "code")
            != ("PIE-S2338" if state == "invalid" else "PIE-S2337")
            or _enumeration(declared[diagnostic], "severity")
            != ("error" if state == "invalid" else "warning")
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if state == "invalid" and _enumeration(owner, "variant") != "terminal":
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
        for proof_ref in source_proofs:
            if _ref(declared[proof_ref], "requirement") != _ref(requirement, "ref"):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    reached: set[ProjectQueryBlockIRPortableRef] = set()
    pending = list(roots)
    while pending:
        proof_ref = pending.pop()
        if proof_ref in reached:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        reached.add(proof_ref)
        proof = declared[proof_ref]
        if proof.kind is not _K.PROOF:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        requirement = declared[_ref(proof, "requirement")]
        kind = _enumeration(proof, "kind")
        joins = _refs(proof, "joins")
        if kind not in {
            "relationship",
            "refinement",
            "matched_key",
            "whole_path",
            "right_limit",
            "right_global",
        }:
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if _boolean(requirement, "represented"):
            if (
                not joins
                or any(node not in _refs(requirement, "joins") for node in joins)
                or (kind != "whole_path" and len(joins) != 1)
                or _refs(proof, "inputs")
                != tuple(use for node in joins for use in incoming.get(node, ()))
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
            if kind == "whole_path" and joins != _refs(requirement, "joins"):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        elif joins or _refs(proof, "inputs"):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        children = _refs(proof, "children")
        if (kind == "whole_path") != bool(children) or any(
            _ref(declared[child], "requirement") != _ref(proof, "requirement")
            for child in children
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        if (
            children
            and _boolean(requirement, "represented")
            and {node for child in children for node in _refs(declared[child], "joins")}
            != set(joins)
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        pending.extend(children)
        if (
            kind in {"right_limit", "right_global"}
            and _boolean(requirement, "represented")
            and (not _refs(proof, "producers") or not _refs(proof, "premise_nodes"))
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
        if (
            any(
                node.position >= min(join.position for join in joins)
                for node in _refs(proof, "premise_nodes")
            )
            if joins
            else False
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TOPOLOGY)
        root_data = [json.loads(encoded) for encoded in _field(proof, "roots").texts]
        if kind == "matched_key":
            if len(root_data) < 4 or [item.get("kind") for item in root_data[:3]] != [
                "ProjectJoinCondition",
                "ProjectJoinConditionKeyMatch",
                "ProjectIROutputCandidateKey",
            ]:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
            position = root_data[1].get("key_match")
            if type(position) is not int or position < 0:
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
            match_ref = ProjectQueryBlockIRPortableRef(
                domain=_D.PREDICATE_KEY_MATCH, position=position
            )
            match = declared.get(match_ref)
            if (
                match is None
                or root_data[2].get("key_matches") != [position]
                or tuple(item.get("equality") for item in root_data[3:])
                != tuple(ref.position for ref in _refs(match, "equalities"))
                or any(
                    item.get("kind") != "ProjectJoinConditionEquality"
                    for item in root_data[3:]
                )
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
        if not root_data or any(
            not _proof_root_valid(item, proof, requirement, declared)
            for item in root_data
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_VALUE)
    if reached != {_ref(proof, "ref") for proof in proofs}:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    if {
        _ref(diagnostic, "ref")
        for diagnostic in diagnostics
        if _text(diagnostic, "code") in {"PIE-S2337", "PIE-S2338"}
    } != {
        ref
        for requirement in requirements
        if (ref := _field(requirement, "diagnostic").ref) is not None
    }:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_REF)
    observed_failures: list[ProjectQueryBlockIRPureRecord] = []
    for owner in _records(document, _K.OWNER_ENTRY):
        if _enumeration(owner, "variant") != "terminal":
            continue
        reason = _enumeration(owner, "terminal_reason")
        owner_ref = _ref(owner, "ref")
        if reason == "invalid_single_match" and not any(
            _field(req, "owner").ref == owner_ref
            and _enumeration(req, "state") == "invalid"
            for req in requirements
        ):
            return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
        if reason == "active_inputs_ir_non_concrete":
            local = tuple(
                record for record in failures if _ref(record, "owner") == owner_ref
            )
            expected = tuple(
                _ref(dependency, "target")
                for dependency in _records(document, _K.DEPENDENCY)
                if _ref(dependency, "consumer") == owner_ref
                and _enumeration(declared[_ref(dependency, "target")], "variant")
                == "terminal"
            )
            if (
                not expected
                or tuple(_integer(record, "ordinal") for record in local)
                != tuple(range(len(expected)))
                or tuple(_ref(record, "blocker") for record in local) != expected
            ):
                return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
            observed_failures.extend(local)
    if tuple(observed_failures) != failures:
        return _reject(ProjectQueryBlockIRPureStatus.INVALID_TERMINAL)
    return None


def _validate_predicates(document, declared):
    expressions = _records(document, _K.PREDICATE_EXPRESSION)
    calls = _records(document, _K.PREDICATE_CALL)
    arguments = _records(document, _K.PREDICATE_ARGUMENT)
    joins = _records(document, _K.PREDICATE_JOIN)
    equalities = _records(document, _K.PREDICATE_EQUALITY)
    keys = _records(document, _K.PREDICATE_INPUT_KEY)
    matches = _records(document, _K.PREDICATE_KEY_MATCH)
    if not any((expressions, calls, arguments, joins, equalities, keys, matches)):
        return None

    def need(condition):
        if not condition:
            raise ValueError("Predicate observation lost complete ordered authority.")

    def syntax(record, field):
        value = json.loads(_text(record, field))
        need(type(value) is dict)
        return value

    def conjuncts(value):
        if value.get("node") == "BinaryExpr" and value.get("operator") == "and":
            return (*conjuncts(value["left"]), *conjuncts(value["right"]))
        return (value,)

    def mandatory(value):
        return tuple(
            item
            for item in conjuncts(value)
            if item.get("node") == "ComparisonExpr"
            and item.get("operator") == "=="
            and item["left"].get("node")
            == item["right"].get("node")
            == "DottedNameExpr"
        )

    def strip(value, spans=False):
        if type(value) is list:
            return [strip(item, spans) for item in value]
        if type(value) is dict:
            return {
                key: strip(item, spans)
                for key, item in value.items()
                if key != "occurrence" and not (spans and key == "span")
            }
        return value

    def substituted(value, names):
        if type(value) is list:
            return [substituted(item, names) for item in value]
        if type(value) is not dict:
            return value
        result = {
            key: substituted(item, names)
            for key, item in value.items()
            if key != "span"
        }
        if result.get("node") == "DottedNameExpr" and result["parts"][0] in names:
            result["parts"] = [names[result["parts"][0]], *result["parts"][1:]]
        return result

    retained = []
    ordinals = {}
    argument_cursor = 0
    for expression in expressions:
        owner = _ref(expression, "owner")
        authored, normalized, context = (
            syntax(expression, field) for field in ("authored", "normalized", "context")
        )
        role = _enumeration(expression, "role")
        need(
            context.get("node")
            == {
                "on": "JoinOnClause",
                "where": "WhereClause",
                "select": "SelectItem",
                "let": "LetBinding",
            }.get(role)
        )
        need(context["expression"] == authored)
        local = tuple(declared[ref] for ref in _refs(expression, "calls"))
        retained.extend(local)
        call_data = []
        for call in local:
            need(_ref(call, "expression") == _ref(expression, "ref"))
            ordinal = _integer(call, "ordinal")
            ordinals.setdefault(owner, []).append(ordinal)
            original, template, expanded = (
                syntax(call, field) for field in ("call", "template", "expanded")
            )
            need(
                original.get("node") == "CallExpr"
                and template.get("node") == "RelationshipTemplate"
            )
            shapes = tuple(json.loads(value) for value in _field(call, "shapes").texts)
            parameters = template["parameters"]
            need(len(parameters) == len(shapes) == len(original["arguments"]))
            names = {}
            for i, (parameter, shape, actual) in enumerate(
                zip(parameters, shapes, original["arguments"], strict=True)
            ):
                argument = arguments[argument_cursor]
                argument_cursor += 1
                need(
                    _ref(argument, "call") == _ref(call, "ref")
                    and _integer(argument, "ordinal") == i
                )
                need(
                    syntax(argument, "parameter") == parameter
                    and syntax(argument, "shape") == shape
                    and syntax(argument, "argument") == actual
                )
                occurrence = syntax(argument, "occurrence")
                relation = syntax(argument, "relation")
                binding = _integer(argument, "binding")
                need(binding >= 0 and actual.get("node") == "NameExpr")
                if occurrence.get("node") == "FromClause":
                    need(
                        binding == 0
                        and actual["name"]
                        == (occurrence.get("binding_name") or occurrence["source_name"])
                    )
                elif occurrence.get("node") == "AnyExpr":
                    need(binding == 0 and actual["name"] == occurrence["binding_name"])
                else:
                    need(
                        occurrence.get("node") == "JoinClause"
                        and binding > 0
                        and actual["name"] == occurrence["target_binding_name"]
                    )
                target = declared[_ref(argument, "target")]
                need(relation["name"] == _text(target, "declared_name"))
                need(relation["span"]["path"] == _text(target, "module_path"))
                names[parameter["name"]] = actual["name"]
            need(substituted(template["body"], names) == strip(expanded, spans=True))
            required = tuple(
                json.loads(value) for value in _field(call, "mandatory").texts
            )
            need(
                required
                == (
                    mandatory(expanded)
                    if role in {"on", "where"} and original in conjuncts(authored)
                    else ()
                )
            )
            call_data.append((original, expanded))
        cursor = 0

        def normalized_copy(before, after):
            nonlocal cursor
            if cursor < len(call_data) and before == call_data[cursor][0]:
                need(after == call_data[cursor][1])
                cursor += 1
                return
            need(type(before) is type(after))
            if type(before) is dict:
                need(tuple(before) == tuple(after))
                for key in before:
                    normalized_copy(before[key], after[key])
            elif type(before) is list:
                need(len(before) == len(after))
                for left, right in zip(before, after, strict=True):
                    normalized_copy(left, right)
            else:
                need(before == after)

        normalized_copy(authored, normalized)
        need(cursor == len(call_data))
    need(tuple(retained) == calls and argument_cursor == len(arguments))
    need(all(values == list(range(len(values))) for values in ordinals.values()))
    represented_on = tuple(
        _ref(expression, "ref")
        for expression in expressions
        if _enumeration(expression, "role") == "on"
        and _enumeration(declared[_ref(expression, "owner")], "variant") != "terminal"
    )
    observed_on = tuple(_ref(join, "expression") for join in joins)
    need(
        len(observed_on) == len(represented_on)
        and set(observed_on) == set(represented_on)
    )
    positions = tuple(_ref(join, "node").position for join in joins)
    need(positions == tuple(sorted(set(positions))))
    equality_cursor = key_cursor = match_cursor = 0
    conditions = {
        _ref(value, "node"): value for value in _records(document, _K.CONDITION)
    }
    algebra = {_ref(value, "node"): value for value in _records(document, _K.ALGEBRA)}
    for join in joins:
        node = _ref(join, "node")
        expression = declared[_ref(join, "expression")]
        need(
            node in algebra
            and _ref(expression, "owner") == _ref(algebra[node], "owner")
        )
        need(_enumeration(expression, "role") == "on" and node in conditions)
        normalized = syntax(expression, "normalized")
        need(strip(normalized) == syntax(conditions[node], "expression"))
        local_calls = tuple(declared[ref] for ref in _refs(expression, "calls"))
        required = tuple(
            (i, value)
            for i, value in enumerate(conjuncts(normalized))
            if any(
                value in tuple(json.loads(e) for e in _field(call, "mandatory").texts)
                for call in local_calls
            )
        )
        local_equalities = equalities[equality_cursor : equality_cursor + len(required)]
        equality_cursor += len(required)
        need(
            _refs(join, "equalities") == tuple(_ref(e, "ref") for e in local_equalities)
        )
        for equality, (position, value) in zip(local_equalities, required, strict=True):
            need(
                _ref(equality, "node") == node
                and _integer(equality, "position") == position
                and syntax(equality, "comparison") == value
            )
            need(
                _refs(equality, "calls")
                == tuple(
                    _ref(call, "ref")
                    for call in local_calls
                    if value
                    in tuple(json.loads(e) for e in _field(call, "mandatory").texts)
                )
            )
            references = tuple(
                json.loads(value)
                for value in _field(conditions[node], "references").texts
            )
            leaves = _authored_field_leaves(normalized)
            for side in ("left", "right"):
                positions = tuple(
                    i for i, leaf in enumerate(leaves) if leaf == value[side]
                )
                need(len(positions) == 1 and positions[0] < len(references))
                resolved = references[positions[0]]
                need(
                    resolved["expression"] == strip(value[side])
                    and len(resolved["candidates"]) == 1
                )
                field = resolved["candidates"][0]
                need(
                    _integer(equality, side + "_binding") == field["binding"]
                    and _integer(equality, side + "_field") == field["field_position"]
                )
        bindings, counts = (
            _field(join, "bindings").integers,
            _field(join, "key_counts").integers,
        )
        need(
            len(bindings) == len(counts)
            and bindings == tuple(sorted(set(bindings)))
            and all(count >= 0 for count in counts)
        )
        local_keys = keys[key_cursor : key_cursor + sum(counts)]
        key_cursor += sum(counts)
        need(_refs(join, "keys") == tuple(_ref(key, "ref") for key in local_keys))
        cursor = 0
        expected_matches = []
        target = max(bindings)
        for binding, count in zip(bindings, counts, strict=True):
            supporting = tuple(
                equality
                for equality in local_equalities
                if any(
                    _integer(equality, side + "_binding") == binding
                    and (
                        (_integer(equality, other + "_binding") != target)
                        if binding == target
                        else (_integer(equality, other + "_binding") == target)
                    )
                    for side, other in (("left", "right"), ("right", "left"))
                )
            )
            matched = {
                _integer(equality, side + "_field")
                for equality in supporting
                for side in ("left", "right")
                if _integer(equality, side + "_binding") == binding
            }
            for ordinal in range(count):
                key = local_keys[cursor]
                cursor += 1
                sizes, key_fields = (
                    _field(key, "class_sizes").integers,
                    _field(key, "fields").integers,
                )
                need(
                    _ref(key, "node") == node
                    and _integer(key, "binding") == binding
                    and _integer(key, "ordinal") == ordinal
                )
                need(_enumeration(key, "strength") in {"strict", "lax"})
                need(
                    bool(sizes)
                    and all(size > 0 for size in sizes)
                    and sum(sizes) == len(key_fields)
                )
                offset = 0
                covered = True
                for size in sizes:
                    covered = covered and bool(
                        matched.intersection(key_fields[offset : offset + size])
                    )
                    offset += size
                if covered:
                    expected_matches.append((key, supporting))
        local_matches = matches[match_cursor : match_cursor + len(expected_matches)]
        match_cursor += len(expected_matches)
        need(
            _refs(join, "matches")
            == tuple(_ref(match, "ref") for match in local_matches)
        )
        for match, (key, supporting) in zip(
            local_matches, expected_matches, strict=True
        ):
            need(
                _ref(match, "node") == node
                and _ref(match, "key") == _ref(key, "ref")
                and _refs(match, "equalities")
                == tuple(_ref(e, "ref") for e in supporting)
            )
            need(
                _enumeration(match, "minimum") == "zero_allowed"
                and _enumeration(match, "maximum") == "at_most_one"
            )
    need(
        (equality_cursor, key_cursor, match_cursor)
        == (len(equalities), len(keys), len(matches))
    )
    return None


def _validate_existence(document, declared):
    """Check ordered inter-JOIN filters without claiming generated JOIN authorship."""
    uses = _records(document, _K.EXISTENCE_USE)
    if not uses:
        return None

    def need(condition):
        if not condition:
            raise ValueError("Inter-JOIN ANY observation lost ordered authority.")

    def syntax(record, name):
        return json.loads(_text(record, name))

    def conjuncts(value):
        if value.get("node") == "BinaryExpr" and value.get("operator") == "and":
            return (*conjuncts(value["left"]), *conjuncts(value["right"]))
        return (value,)

    algebra = {_ref(item, "node"): item for item in _records(document, _K.ALGEBRA)}
    owner_counts = {}
    nodes = set()
    for use in uses:
        owner, context, expression, clause = (
            syntax(use, key) for key in ("authored_owner", "context", "any", "clause")
        )
        need(
            owner.get("node") in {"TableDef", "QueryDef"}
            and context.get("node") == "JoinFilterClause"
        )
        need(
            context in owner["join_filters"]
            and expression.get("node") == "AnyExpr"
            and clause.get("node") == "JoinClause"
        )
        parts = conjuncts(context["expression"])
        positive = [part for part in parts if part == expression]
        negative = [
            part
            for part in parts
            if part.get("node") == "UnaryExpr"
            and part.get("operator") == "not"
            and part.get("operand") == expression
        ]
        need(
            len(positive) + len(negative) == 1
            and clause["kind"] == ("anti" if negative else "semi")
        )
        prefix, ordinal = (
            _integer(use, "preceding_join_count"),
            _integer(use, "input_ordinal"),
        )
        owner_ref = _ref(use, "owner")
        owner_counts[owner_ref] = owner_counts.get(owner_ref, 0) + 1
        need(
            context["preceding_join_count"] == prefix
            and ordinal == prefix + owner_counts[owner_ref]
            and prefix < len(owner["join_clauses"])
        )
        if _field(use, "node").tag is ProjectQueryBlockIRPureTag.ABSENT:
            need(_enumeration(declared[owner_ref], "variant") == "terminal")
        else:
            node = _ref(use, "node")
            need(
                node in algebra
                and node not in nodes
                and _ref(algebra[node], "owner") == owner_ref
                and _enumeration(algebra[node], "kind") == clause["kind"]
            )
            nodes.add(node)
    for owner_ref in owner_counts:
        owned = tuple(use for use in uses if _ref(use, "owner") == owner_ref)
        authored = syntax(owned[0], "authored_owner")
        need(all(syntax(use, "authored_owner") == authored for use in owned))
        expected = []
        for context in authored["join_filters"]:
            for term in conjuncts(context["expression"]):
                expression = (
                    term["operand"]
                    if term.get("node") == "UnaryExpr" and term.get("operator") == "not"
                    else term
                )
                need(expression.get("node") == "AnyExpr")
                expected.append((context, expression))
        need(
            tuple((syntax(use, "context"), syntax(use, "any")) for use in owned)
            == tuple(expected)
        )
    return None


def _validate_scalar_any(document, declared):
    """Validate ordered scalar scopes and their actual field/LET candidates."""
    uses = _records(document, _K.SCALAR_ANY_USE)
    values = _records(document, _K.SCALAR_ANY_VALUE)
    fields = _records(document, _K.SCALAR_ANY_FIELD)
    references = _records(document, _K.SCALAR_ANY_REFERENCE)
    candidates = _records(document, _K.SCALAR_ANY_CANDIDATE)
    if not any((uses, values, fields, references, candidates)):
        return None
    dependencies = _records(document, _K.DEPENDENCY)
    algebra = _records(document, _K.ALGEBRA)
    images = _records(document, _K.INPUT_CORRESPONDENCE)
    properties = _records(document, _K.RELATIONAL_PROPERTY)

    def need(value):
        if not value:
            raise ValueError("Scalar ANY observation lost its ordered scope authority.")

    def syntax(record, key):
        return json.loads(_text(record, key))

    def absent(record, key):
        return _field(record, key).tag is ProjectQueryBlockIRPureTag.ABSENT

    def bound(use, position, context):
        """The verified producer of one FROM/JOIN binding and its row in scope."""
        owner = _ref(use, "owner")
        joins = tuple(join for join in algebra if _ref(join, "owner") == owner)
        need(len(joins) == len(syntax(use, "owner_definition")["join_clauses"]))
        if not joins:
            producer = _field(declared[owner], "relation_input_owner").ref
            need(producer is not None)
            output, use_ref = _ref(declared[producer], "active_output"), None
        else:
            pairs = tuple(
                tuple(
                    item for item in images if _ref(item, "node") == _ref(join, "node")
                )
                for join in joins
            )
            image = (pairs[0][0], *(pair[1] for pair in pairs))[position]
            producer, use_ref = _field(image, "producer").ref, _ref(image, "use")
            prefix = _integer(use, "current_prefix")
            output = (
                _ref(pairs[prefix - 1][int(position == prefix)], "output")
                if context.get("node") == "JoinOnClause"
                else _ref(joins[-1], "output")
            )
        (row,) = (item for item in properties if _ref(item, "output") == output)
        row_fields = tuple(declared[ref] for ref in _refs(row, "fields"))
        if _ref(row, "owner") == owner:
            row_fields = tuple(
                item
                for item in row_fields
                if _field(item, "introduction_use").ref == use_ref
            )
        return producer, row_fields

    def children(node):
        kind = node.get("node")
        names = {
            "CallExpr": ("arguments",),
            "UnaryExpr": ("operand",),
            "ConditionalExpr": ("when_true", "condition", "when_false"),
            "MembershipExpr": ("value", "options"),
            "RelationMembershipExpr": ("value",),
            "CastExpr": ("value",),
            "BinaryExpr": ("left", "right"),
            "ComparisonExpr": ("left", "right"),
            "BetweenExpr": ("value", "lower", "upper"),
            "IsNullExpr": ("value",),
        }.get(kind, ())
        return tuple(
            child
            for name in names
            for child in (node[name] if type(node[name]) is list else [node[name]])
        )

    def direct(predicate):
        found, nested = [], []
        pending = [predicate]
        while pending:
            node = pending.pop()
            need(type(node) is dict and "node" in node)
            if node["node"] == "AnyExpr":
                nested.append(node)
            elif node["node"] in {"NameExpr", "DottedNameExpr"}:
                found.append(node)
            else:
                pending.extend(reversed(children(node)))
        return tuple(found), tuple(nested)

    def contains(root, target):
        pending = [root]
        while pending:
            node = pending.pop()
            if node == target:
                return True
            if type(node) is dict:
                pending.extend(node.values())
            elif type(node) is list:
                pending.extend(node)
        return False

    def root_context(use):
        context = syntax(use, "context")
        owner = _ref(use, "owner")
        prefix = _integer(use, "current_prefix")
        seen = set()
        while context.get("node") == "AnyExpr":
            matches = tuple(
                parent
                for parent in uses
                if _ref(parent, "owner") == owner
                and syntax(parent, "current") == context
            )
            need(len(matches) == 1)
            parent = matches[0]
            need(
                _ref(parent, "ref") not in seen
                and _integer(parent, "current_prefix") == prefix
            )
            seen.add(_ref(parent, "ref"))
            context = syntax(parent, "context")
        return context

    retained = []
    for use in uses:
        authored, current = syntax(use, "authored"), syntax(use, "current")
        need(authored.get("node") == current.get("node") == "AnyExpr")
        need(
            type(syntax(use, "authored_context")) is dict
            and type(syntax(use, "context")) is dict
        )
        owner, context = syntax(use, "owner_definition"), syntax(use, "context")
        authored_owner = syntax(use, "authored_owner")
        need(owner.get("node") in {"TableDef", "QueryDef"})
        need(
            authored_owner.get("node") in {"TableDef", "QueryDef"}
            and authored_owner["name"] == owner["name"]
        )
        need(owner["name"] == _text(declared[_ref(use, "owner")], "declared_name"))
        need(contains(context, current) and contains(owner, context))
        joins = owner["join_clauses"]
        context = root_context(use)
        if context.get("node") == "JoinOnClause":
            matches = tuple(
                i for i, join in enumerate(joins, 1) if join["on_clause"] == context
            )
            need(len(matches) == 1 and _integer(use, "current_prefix") == matches[0])
        else:
            need(_integer(use, "current_prefix") == len(joins))
        need(_integer(use, "current_prefix") <= len(owner["join_clauses"]))
        local = tuple(declared[ref] for ref in _refs(use, "values"))
        need(all(_ref(item, "use") == _ref(use, "ref") for item in local))
        retained.extend(local)
    need(tuple(retained) == values)

    all_fields, all_references, all_candidates = [], [], []
    for value in values:
        use = declared[_ref(value, "use")]
        expression = syntax(value, "expression")
        current = syntax(use, "current")
        need(expression.get("node") == "AnyExpr")
        need(
            expression["binding_name"] == current["binding_name"]
            and expression["relation_name"] == current["relation_name"]
        )
        normalized = tuple(
            item
            for item in _records(document, _K.PREDICATE_EXPRESSION)
            if _ref(item, "owner") == _ref(use, "owner")
            and syntax(item, "context") == root_context(use)
        )
        need(len(normalized) <= 1)
        need(
            expression == current
            or any(
                contains(syntax(record, "normalized"), expression)
                for record in normalized
            )
        )
        need(
            _text(value, "type") == "Bool"
            and _enumeration(value, "nullability") == "non_null"
            and not absent(value, "target")
        )
        local_fields = tuple(declared[ref] for ref in _refs(value, "fields"))
        local_refs = tuple(declared[ref] for ref in _refs(value, "references"))
        nested = tuple(declared[ref] for ref in _refs(value, "nested"))
        need(
            len(local_fields) == _integer(value, "field_count")
            and len(local_refs) == _integer(value, "reference_count")
        )
        need(
            all(
                _ref(item, "value") == _ref(value, "ref")
                and _integer(item, "ordinal") == i
                for i, item in enumerate(local_fields)
            )
        )
        need(
            all(
                _ref(item, "value") == _ref(value, "ref")
                and _integer(item, "ordinal") == i
                for i, item in enumerate(local_refs)
            )
        )
        need(
            tuple(_text(item, "name") for item in local_fields)
            == _field(value, "input_names").texts
        )
        need(len({_text(item, "name") for item in local_fields}) == len(local_fields))
        leaves, nested_syntax = direct(expression["predicate"])
        need(tuple(syntax(item, "expression") for item in local_refs) == leaves)
        need(tuple(syntax(item, "expression") for item in nested) == nested_syntax)
        need(
            all(
                not absent(item, "parent")
                and _ref(item, "parent") == _ref(value, "ref")
                for item in nested
            )
        )
        need(all(syntax(item, "context") == expression for item in nested))
        if not absent(value, "parent"):
            parent = declared[_ref(value, "parent")]
            need(_ref(value, "ref") in _refs(parent, "nested"))
        all_fields.extend(local_fields)
        all_references.extend(local_refs)
        for reference in local_refs:
            leaf = syntax(reference, "expression")
            options = tuple(declared[ref] for ref in _refs(reference, "candidates"))
            need(len(options) == _integer(reference, "candidate_count") == 1)
            all_candidates.extend(options)
            for ordinal, candidate in enumerate(options):
                need(
                    _ref(candidate, "reference") == _ref(reference, "ref")
                    and _integer(candidate, "ordinal") == ordinal
                )
                binding = syntax(candidate, "binding")
                name, field_name = (
                    _text(candidate, "name"),
                    _text(candidate, "field_name"),
                )
                kind = _enumeration(candidate, "kind")
                need(kind in {"let", "field"})
                if kind == "let":
                    need(
                        binding.get("node") == "LetBinding"
                        and binding["name"] == name == field_name
                    )
                    definition = syntax(use, "owner_definition")
                    clause = definition["let_clause"]
                    context = root_context(use)
                    if clause is None:
                        raise ValueError("ANY LET capture requires its exact scope.")
                    need(binding in clause["bindings"])
                    if context.get("node") == "LetBinding":
                        need(
                            context in clause["bindings"]
                            and clause["bindings"].index(binding)
                            < clause["bindings"].index(context)
                        )
                    else:
                        need(context.get("node") in {"WhereClause", "SelectItem"})
                    need(leaf.get("node") == "NameExpr" and leaf["name"] == name)
                    scope = value
                    seen = set()
                    while True:
                        need(
                            _ref(scope, "ref") not in seen
                            and syntax(scope, "expression")["binding_name"] != name
                        )
                        seen.add(_ref(scope, "ref"))
                        if absent(scope, "parent"):
                            break
                        scope = declared[_ref(scope, "parent")]
                    need(
                        absent(candidate, "local")
                        and absent(candidate, "target")
                        and absent(candidate, "position")
                        and absent(candidate, "field_position")
                        and not _field(candidate, "input_names").texts
                        and not absent(candidate, "let_expression")
                    )
                    continue
                need(
                    absent(candidate, "let_expression")
                    and not absent(candidate, "target")
                    and not absent(candidate, "field_position")
                )
                input_names = _field(candidate, "input_names").texts
                field_position = _integer(candidate, "field_position")
                need(
                    field_position < len(input_names)
                    and input_names[field_position] == field_name
                )
                if leaf.get("node") == "DottedNameExpr":
                    need(leaf["parts"] == [name, field_name])
                else:
                    need(leaf.get("node") == "NameExpr" and leaf["name"] == field_name)
                if not absent(candidate, "local"):
                    local_use = _ref(candidate, "local")
                    scope = value
                    seen = set()
                    while _ref(scope, "use") != local_use:
                        need(
                            _ref(scope, "ref") not in seen
                            and not absent(scope, "parent")
                            and syntax(scope, "expression")["binding_name"] != name
                        )
                        seen.add(_ref(scope, "ref"))
                        scope = declared[_ref(scope, "parent")]
                    local_current = syntax(declared[local_use], "current")
                    need(
                        binding == local_current
                        and name == local_current["binding_name"]
                    )
                    need(
                        not absent(candidate, "position")
                        and not absent(candidate, "target")
                        and not absent(scope, "target")
                    )
                    need(_ref(candidate, "target") == _ref(scope, "target"))
                    position = _integer(candidate, "position")
                    need(
                        not absent(candidate, "field_position")
                        and _integer(candidate, "field_position") == position
                    )
                    scoped_fields = _refs(scope, "fields")
                    need(
                        position < len(scoped_fields)
                        and input_names == _field(scope, "input_names").texts
                    )
                    source = declared[scoped_fields[position]]
                    need(
                        _text(source, "name") == field_name
                        and _text(source, "type") == _text(candidate, "type")
                        and _enumeration(source, "nullability")
                        == _enumeration(candidate, "nullability")
                        and syntax(source, "definition") == syntax(candidate, "field")
                    )
                else:
                    need(
                        binding.get("node") in {"FromClause", "JoinClause"}
                        and not absent(candidate, "position")
                    )
                    need(
                        name
                        == (
                            binding.get("target_binding_name")
                            if binding["node"] == "JoinClause"
                            else binding.get("binding_name") or binding["source_name"]
                        )
                    )
                    definition = syntax(use, "owner_definition")
                    position = _integer(candidate, "position")
                    need(
                        tuple(
                            _ref(edge, "target")
                            for edge in dependencies
                            if _ref(edge, "consumer") == _ref(use, "owner")
                            and _integer(edge, "ordinal") == position
                        )
                        == (_ref(candidate, "target"),)
                    )
                    if binding["node"] == "FromClause":
                        need(position == 0 and binding == definition["from_clause"])
                    else:
                        joins = definition["join_clauses"]
                        need(
                            0 < position <= _integer(use, "current_prefix")
                            and position <= len(joins)
                            and binding == joins[position - 1]
                        )
                        if binding["kind"] in {"semi", "anti"}:
                            need(binding["on_clause"] == root_context(use))
                    producer, row = bound(use, position, root_context(use))
                    need(
                        producer == _ref(candidate, "target")
                        and tuple(_text(item, "name") for item in row) == input_names
                        and _enumeration(row[field_position], "nullability")
                        == _enumeration(candidate, "nullability")
                    )
                    scope = value
                    seen = set()
                    while True:
                        need(_ref(scope, "ref") not in seen)
                        seen.add(_ref(scope, "ref"))
                        need(syntax(scope, "expression")["binding_name"] != name)
                        if absent(scope, "parent"):
                            break
                        scope = declared[_ref(scope, "parent")]
    need(
        tuple(all_fields) == fields
        and tuple(all_references) == references
        and tuple(all_candidates) == candidates
    )
    return None


def _validate_predicate_any_scopes(document, declared):
    """Replay each actual predicate's complete ordered ANY binding images."""
    scopes = _records(document, _K.PREDICATE_ANY_SCOPE)
    active = _records(document, _K.PREDICATE_EXPRESSION)
    if not scopes and not active:
        return None

    def need(value):
        if not value:
            raise ValueError("Predicate ANY scope lost ordered authority.")

    def syntax(record, name):
        return json.loads(_text(record, name))

    def absent(record, name):
        return _field(record, name).tag is ProjectQueryBlockIRPureTag.ABSENT

    def root_context(use):
        context = syntax(use, "context")
        seen = set()
        while context.get("node") == "AnyExpr":
            parents = tuple(
                item
                for item in _records(document, _K.SCALAR_ANY_USE)
                if _ref(item, "owner") == _ref(use, "owner")
                and syntax(item, "current") == context
            )
            if len(parents) != 1:
                raise ValueError("ANY scope requires one exact parent.")
            need(_ref(parents[0], "ref") not in seen)
            seen.add(_ref(parents[0], "ref"))
            context = syntax(parents[0], "context")
        return context

    def replay(record):
        pending = [(syntax(record, "authored"), syntax(record, "normalized"))]
        calls = tuple(
            (syntax(declared[ref], "call"), syntax(declared[ref], "expanded"))
            for ref in _refs(record, "calls")
        )
        cursor, pairs = 0, []
        while pending:
            before, after = pending.pop()
            if cursor < len(calls) and before == calls[cursor][0]:
                need(after == calls[cursor][1])
                cursor += 1
            elif type(before) is dict:
                need(type(after) is dict and tuple(before) == tuple(after))
                if before.get("node") == "AnyExpr":
                    pairs.append((before, after))
                pending.extend(
                    (before[key], after[key]) for key in reversed(tuple(before))
                )
            elif type(before) is list:
                need(type(after) is list and len(before) == len(after))
                pending.extend(reversed(tuple(zip(before, after, strict=True))))
            else:
                need(before == after)
        need(cursor == len(calls))
        return tuple(pairs)

    retained = []
    for record in active:
        own = tuple(
            item for item in scopes if _ref(item, "expression") == _ref(record, "ref")
        )
        retained.extend(own)
        need(
            tuple((syntax(item, "before"), syntax(item, "after")) for item in own)
            == replay(record)
        )
        ordinals = tuple(_integer(item, "read_ordinal") for item in own)
        need(len(set(ordinals)) == len(ordinals))
        for ordinal, item in enumerate(own):
            use = declared[_ref(item, "use")]
            before, after = syntax(item, "before"), syntax(item, "after")
            need(
                _integer(item, "ordinal") == ordinal
                and _ref(use, "owner") == _ref(record, "owner")
                and before == syntax(use, "current")
            )
            need(
                after["binding_name"] == before["binding_name"]
                and after["relation_name"] == before["relation_name"]
            )
            context = root_context(use)
            expected = {
                "JoinOnClause": "join_on",
                "WhereClause": "where",
                "SelectItem": "select",
                "LetBinding": "let",
            }.get(context.get("node"))
            need(
                expected is not None
                and _enumeration(item, "position") == expected
                and syntax(record, "context") == context
            )
            definition = syntax(use, "owner_definition")
            if expected == "join_on":
                containers = tuple(
                    join["on_clause"] for join in definition["join_clauses"]
                )
            elif expected == "select":
                containers = tuple(definition["select_items"])
            elif expected == "let":
                clause = definition["let_clause"]
                containers = () if clause is None else tuple(clause["bindings"])
            else:
                containers = (definition["where_clause"],)
            position = _integer(item, "container_ordinal")
            need(position < len(containers) and containers[position] == context)
            if absent(item, "target"):
                need(absent(item, "relation"))
            else:
                need(not absent(item, "relation"))
                relation, target = (
                    syntax(item, "relation"),
                    declared[_ref(item, "target")],
                )
                need(
                    relation["name"] == _text(target, "declared_name")
                    and relation["span"]["path"] == _text(target, "module_path")
                )
                related = tuple(declared[ref] for ref in _refs(use, "values"))
                need(
                    not related
                    or any(
                        not absent(value, "target")
                        and _ref(value, "target") == _ref(item, "target")
                        for value in related
                    )
                )
    need(tuple(retained) == scopes)
    arguments = _records(document, _K.PREDICATE_ARGUMENT)
    for record in active:
        own = tuple(
            item for item in scopes if _ref(item, "expression") == _ref(record, "ref")
        )
        if not own:
            continue
        pending: list[tuple[Any, tuple[dict[str, Any], ...]]] = [
            (syntax(record, "authored"), ())
        ]
        lexical = []
        while pending:
            node, visible = pending.pop()
            if type(node) is list:
                pending.extend((child, visible) for child in reversed(node))
            elif type(node) is dict and "node" in node:
                if node["node"] == "CallExpr":
                    lexical.append((node, visible))
                if node["node"] == "AnyExpr":
                    visible = (*visible, node)
                pending.extend(
                    (child, visible)
                    for key, child in reversed(tuple(node.items()))
                    if key != "span"
                    and not (node["node"] == "CallExpr" and key == "callee")
                )
        for call_ref in _refs(record, "calls"):
            call = declared[call_ref]
            matches = tuple(
                visible for node, visible in lexical if node == syntax(call, "call")
            )
            need(len(matches) == 1)
            for argument in arguments:
                if _ref(argument, "call") != call_ref:
                    continue
                actual, occurrence = (
                    syntax(argument, "argument"),
                    syntax(argument, "occurrence"),
                )
                visible = tuple(
                    item
                    for item in reversed(matches[0])
                    if item["binding_name"] == actual["name"]
                )
                if occurrence.get("node") == "AnyExpr":
                    need(bool(visible) and visible[0] == occurrence)
                    target_scopes = tuple(
                        item for item in own if syntax(item, "before") == occurrence
                    )
                    need(
                        len(target_scopes) == 1
                        and not absent(target_scopes[0], "target")
                        and _ref(target_scopes[0], "target") == _ref(argument, "target")
                    )
                else:
                    need(not visible)
    return None
