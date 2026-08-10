"""Private Rust-ready pure boundary over the canonical inspection document.

This module owns one deterministic, total, portable procedure: it turns an
explicitly supplied immutable document value into either the exact canonical
private inspection payload or one normalized rejection.

Three layers stay separate and are never conflated:

1. Python authority-root admission, owned by ``module_inspection`` and the
   settled Slice 5 through Slice 13 carriers, decided by object identity.
2. The Python-side canonical projection, which turns the settled inspection
   into the portable document value below.
3. This portable pure value boundary, where meaning is carried only by explicit
   data. No Python object identity, address, representation string, or ambient
   state participates, and nothing here reads the filesystem, the environment,
   the locale, the clock, randomness, the process, the hash seed, a thread, a
   network, a package, a database, or a runtime.

The boundary is suitable for an independent reimplementation because every
observable result depends only on the supplied immutable value, and every
rejection is an explicit private status rather than an exception class whose
identity can differ between supported interpreters.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType

__all__: tuple[str, ...] = ()

PURE_DOCUMENT_FORMAT_MARKER = "pietto.module-inspection.v1"

# Every integer in the canonical projection is a count, an ordinal, a source
# position, or an opened-byte count. The domain is bounded explicitly because
# rendering an unbounded integer depends on a process-level digit limit, which
# would make the boundary neither total nor process independent.
PURE_MAX_INTEGER = 2**63 - 1

_PURE_ABSENT_TOKEN = "n:"

_PURE_ESCAPES: Mapping[str, str] = MappingProxyType(
    {
        "\\": "\\\\",
        "\t": "\\t",
        "\n": "\\n",
        "\r": "\\r",
    }
)

_PURE_DELETE_CHARACTER = "\x7f"

_PURE_FIRST_PRINTABLE = " "

_PURE_SURROGATE_START = "\ud800"

_PURE_SURROGATE_END = "\udfff"

_PURE_HEX_ALPHABET = frozenset("0123456789abcdef")


class ProjectPureTag(StrEnum):
    """The exact tag vocabulary one portable value may carry."""

    TEXT = "s"
    INTEGER = "i"
    BOOLEAN = "b"
    ENUMERATION = "e"
    ABSENT = "n"


class ProjectPureStatus(StrEnum):
    """The closed normalized outcome vocabulary of the portable boundary.

    Every rejection is one of these values. No standard-library exception class
    is part of the differential contract, so the vocabulary is identical on
    every supported interpreter.
    """

    OK = "ok"
    EMPTY_DOCUMENT = "empty_document"
    MISSING_HEADER_RECORD = "missing_header_record"
    UNEXPECTED_HEADER_RECORD = "unexpected_header_record"
    UNKNOWN_RECORD_KIND = "unknown_record_kind"
    UNKNOWN_FORMAT_MARKER = "unknown_format_marker"
    FIELD_ARITY_MISMATCH = "field_arity_mismatch"
    FIELD_KEY_MISMATCH = "field_key_mismatch"
    VALUE_TAG_MISMATCH = "value_tag_mismatch"
    ABSENT_VALUE_NOT_ALLOWED = "absent_value_not_allowed"
    MISSING_VALUE_PAYLOAD = "missing_value_payload"
    EXTRA_VALUE_PAYLOAD = "extra_value_payload"
    NEGATIVE_INTEGER = "negative_integer"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    ORPHAN_RECORD = "orphan_record"
    SCOPE_ORDINAL_MISMATCH = "scope_ordinal_mismatch"
    SECTION_ORDER_VIOLATION = "section_order_violation"
    CHILD_ORDER_VIOLATION = "child_order_violation"
    ORDINAL_SEQUENCE_VIOLATION = "ordinal_sequence_violation"
    DUPLICATE_SINGLETON_RECORD = "duplicate_singleton_record"
    MISSING_REQUIRED_RECORD = "missing_required_record"
    CHILD_COUNT_MISMATCH = "child_count_mismatch"
    TRAILING_RECORD_AFTER_DOCUMENT = "trailing_record_after_document"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    INCONSISTENT_RECORD_STATE = "inconsistent_record_state"
    INCONSISTENT_SCOPE_RELATION = "inconsistent_scope_relation"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPureValue:
    """One portable tagged scalar.

    Construction enforces exact primitive Python types and nothing else, so
    every corruption the differential contract must reject stays constructible.
    ``bool`` is refused where ``int`` is declared because ``bool`` is an ``int``
    subclass and would otherwise smuggle a boolean into an integer payload.
    """

    tag: ProjectPureTag
    text: str | None = None
    integer: int | None = None
    boolean: bool | None = None

    def __post_init__(self) -> None:
        """Require an exact tag and exact primitive payload types."""

        if type(self.tag) is not ProjectPureTag:
            raise TypeError("Portable value requires an exact tag.")
        if self.text is not None and type(self.text) is not str:
            raise TypeError("Portable text payload must be text.")
        if self.integer is not None and type(self.integer) is not int:
            raise TypeError("Portable integer payload must be an integer.")
        if self.boolean is not None and type(self.boolean) is not bool:
            raise TypeError("Portable boolean payload must be a boolean.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPureField:
    """One portable ``key`` and its tagged value."""

    key: str
    value: ProjectPureValue

    def __post_init__(self) -> None:
        """Require an exact key and an exact portable value."""

        if type(self.key) is not str:
            raise TypeError("Portable field key must be text.")
        if type(self.value) is not ProjectPureValue:
            raise TypeError("Portable field requires an exact portable value.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPureRecord:
    """One portable record: a kind plus its ordered fields."""

    kind: str
    fields: tuple[ProjectPureField, ...] = ()

    def __post_init__(self) -> None:
        """Require an exact kind and an exact ordered field tuple."""

        if type(self.kind) is not str:
            raise TypeError("Portable record kind must be text.")
        if type(self.fields) is not tuple:
            raise TypeError("Portable record fields must be a tuple.")
        if any(type(item) is not ProjectPureField for item in self.fields):
            raise TypeError("Portable record fields must be exact portable fields.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPureDocument:
    """One complete portable inspection document in canonical record order."""

    records: tuple[ProjectPureRecord, ...] = ()

    def __post_init__(self) -> None:
        """Require an exact ordered record tuple."""

        if type(self.records) is not tuple:
            raise TypeError("Portable document records must be a tuple.")
        if any(type(item) is not ProjectPureRecord for item in self.records):
            raise TypeError("Portable document requires exact portable records.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectPureOutcome:
    """The total result of one portable evaluation.

    ``OK`` carries the exact canonical payload and no coordinates. Every
    rejection carries no payload plus the deterministic structural coordinates
    of the first violation in document order. A rejection never echoes a
    supplied text, enumeration, key, or kind, so no content can leak through it.
    """

    status: ProjectPureStatus
    canonical_bytes: bytes | None = None
    record_position: int | None = None
    field_position: int | None = None

    def __post_init__(self) -> None:
        """Keep the outcome status, payload, and coordinates one atomic tuple."""

        if type(self.status) is not ProjectPureStatus:
            raise TypeError("Portable outcome requires an exact status.")
        if self.canonical_bytes is not None and type(self.canonical_bytes) is not bytes:
            raise TypeError("Portable outcome payload must be bytes.")
        if self.record_position is not None and type(self.record_position) is not int:
            raise TypeError("Portable outcome record position must be an integer.")
        if self.field_position is not None and type(self.field_position) is not int:
            raise TypeError("Portable outcome field position must be an integer.")
        if self.status is ProjectPureStatus.OK:
            if self.canonical_bytes is None:
                raise ValueError("An accepted portable outcome carries its payload.")
            if self.record_position is not None or self.field_position is not None:
                raise ValueError("An accepted portable outcome carries no coordinate.")
            return
        if self.canonical_bytes is not None:
            raise ValueError("A rejected portable outcome carries no payload.")
        if self.field_position is not None and self.record_position is None:
            raise ValueError("A field coordinate requires its record coordinate.")


PURE_ABSENT = ProjectPureValue(tag=ProjectPureTag.ABSENT)


def pure_text(value: str) -> ProjectPureValue:
    """Build one portable text value."""

    return ProjectPureValue(tag=ProjectPureTag.TEXT, text=value)


def pure_integer(value: int) -> ProjectPureValue:
    """Build one portable integer value without validating its range."""

    return ProjectPureValue(tag=ProjectPureTag.INTEGER, integer=value)


def pure_boolean(value: bool) -> ProjectPureValue:
    """Build one portable boolean value."""

    return ProjectPureValue(tag=ProjectPureTag.BOOLEAN, boolean=value)


def pure_enumeration(value: str) -> ProjectPureValue:
    """Build one portable enumeration value from its declared text.

    The argument is a plain ``str``. A Python enumeration member is refused by
    ``ProjectPureValue`` construction, so no Python enumeration identity can
    cross the portable boundary.
    """

    return ProjectPureValue(tag=ProjectPureTag.ENUMERATION, text=value)


def escape_pure_text(value: str) -> str:
    """Escape one payload into the canonical single-line representation."""

    escaped: list[str] = []
    for character in value:
        replacement = _PURE_ESCAPES.get(character)
        if replacement is not None:
            escaped.append(replacement)
        elif character < _PURE_FIRST_PRINTABLE or character == _PURE_DELETE_CHARACTER:
            escaped.append(f"\\x{ord(character):02x}")
        elif _PURE_SURROGATE_START <= character <= _PURE_SURROGATE_END:
            # A POSIX path byte that the filesystem encoding cannot decode
            # reaches this projection as a lone surrogate, and UTF-8 refuses to
            # encode one. Escaping it keeps the payload total over every
            # retained text and keeps one unambiguous byte representation.
            escaped.append(f"\\u{ord(character):04x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def encode_pure_value(value: ProjectPureValue) -> str:
    """Render one already validated portable value as its canonical token.

    This helper is reached only after ``evaluate_pure_document`` has accepted
    the whole document, so a malformed value here is an internal construction
    defect rather than part of the differential contract.
    """

    if value.tag is ProjectPureTag.ABSENT:
        if value.text is not None or value.integer is not None:
            raise ValueError("An absent portable value carries no payload.")
        if value.boolean is not None:
            raise ValueError("An absent portable value carries no payload.")
        return _PURE_ABSENT_TOKEN
    if value.tag is ProjectPureTag.TEXT:
        if value.text is None:
            raise ValueError("A portable text value requires its payload.")
        return f"s:{escape_pure_text(value.text)}"
    if value.tag is ProjectPureTag.ENUMERATION:
        if value.text is None:
            raise ValueError("A portable enumeration value requires its payload.")
        return f"e:{escape_pure_text(value.text)}"
    if value.tag is ProjectPureTag.INTEGER:
        if value.integer is None or value.integer < 0:
            raise ValueError(
                "A portable integer value requires a non-negative payload."
            )
        return f"i:{value.integer}"
    if value.boolean is None:
        raise ValueError("A portable boolean value requires its payload.")
    return "b:true" if value.boolean else "b:false"


@dataclass(frozen=True, slots=True, kw_only=True)
class _PureKeySpec:
    """One declared key of one record kind."""

    key: str
    tag: ProjectPureTag
    optional: bool = False
    vocabulary: tuple[str, ...] | None = None


class _PureStateKind(StrEnum):
    """The declared shapes of a cross-field state rule."""

    COMBINATION = "combination"
    PRESENCE_GROUP = "presence_group"
    POSITIVE_REQUIRES_PRESENT = "positive_requires_present"
    POSITIVE = "positive"
    STRICTLY_LESS = "strictly_less"
    LOWERCASE_HEX = "lowercase_hex"
    MODULE_PATH = "module_path"
    MULTI_REQUIRES_TRUE = "multi_requires_true"
    NON_EMPTY_IF_PRESENT = "non_empty_if_present"
    EQUALITY_COMBINATION = "equality_combination"
    EQUAL_IF_PRESENT = "equal_if_present"
    TERMINAL_COMBINATION = "terminal_combination"


@dataclass(frozen=True, slots=True, kw_only=True)
class _PureStateRule:
    """One declared cross-field rule an upstream carrier already validates.

    A rule is data, not code, so an independent implementation reads the same
    declaration. Every rule is derived from one upstream carrier's own
    validation rather than by inspection, so none of them narrows the accepted
    language beyond what the projection can already produce.

    A key listed in ``presence_keys`` contributes ``present`` or ``absent``
    instead of its value, which lets one combination table express a
    correlation between an enumeration and whether an optional group is
    supplied. An admitted cell of ``*`` matches any value, for the rows where
    the authority itself leaves that key unconstrained.

    A rule carrying ``when`` applies only to the records whose named key holds
    the named value, which expresses an upstream guard that one origin variant
    imposes and the others do not.
    """

    rule: _PureStateKind
    keys: tuple[str, ...] = ()
    admitted: tuple[tuple[str, ...], ...] = ()
    presence_keys: tuple[str, ...] = ()
    text_length: int = 0
    terminal: tuple[str, ...] = ()
    when: tuple[str, ...] = ()


class _PureScopeKind(StrEnum):
    """The declared shapes of a relation between one record and its scope."""

    ANCESTOR_EQUAL = "ancestor_equal"
    ANCESTOR_COMBINATION = "ancestor_combination"
    UNCLE_COMBINATION = "uncle_combination"
    PREVIOUS_SIBLING_EQUAL = "previous_sibling_equal"
    PREVIOUS_SIBLING_INCREASING = "previous_sibling_increasing"
    PREVIOUS_SIBLING_NON_DECREASING = "previous_sibling_non_decreasing"
    GROUPED_SEQUENCES_EQUAL = "grouped_sequences_equal"
    COLLECTED_SETS_EQUAL = "collected_sets_equal"
    COLLECTED_SUBSET = "collected_subset"
    SCOPE_REQUIRES_CHILD = "scope_requires_child"
    SIBLING_BUCKETS_COMPLETE = "sibling_buckets_complete"
    DISTINCT_SIBLINGS = "distinct_siblings"
    DISTINCT_SUBTREES = "distinct_subtrees"
    SCOPE_CONTAINS_ANCESTOR = "scope_contains_ancestor"
    SCOPE_EXCLUDES_ANCESTOR = "scope_excludes_ancestor"


@dataclass(frozen=True, slots=True, kw_only=True)
class _PureScopeRule:
    """One declared relation between a record and the scope that encloses it.

    A state rule reads one record. A scope rule reads the enclosing scope chain
    the walk already maintains: an ancestor record's value, the immediately
    preceding sibling of the same kind, or the set of siblings collected so
    far. Nothing else about the document is consulted, so the portable layer
    never rebuilds the projection it validates.

    ``at`` restricts a rule to the first or the last declared sibling of its
    kind, which is how a chain states its two endpoints. ``pairs`` names
    ``(this key, other key)`` couples; ``distinct`` names the keys whose tuple
    must not repeat among siblings; ``child`` and ``child_key`` name the child
    records a scope rule collects. A combination reads each couple as one
    ``(this value, ancestor value)`` cell of ``admitted``, where an ancestor key
    listed in ``presence`` contributes ``present`` or ``absent`` instead of its
    value, so a child value can be restricted by the state of the record that
    owns it.
    """

    rule: _PureScopeKind
    scope: str = ""
    pairs: tuple[tuple[str, str], ...] = ()
    admitted: tuple[tuple[str, ...], ...] = ()
    presence: tuple[str, ...] = ()
    distinct: tuple[str, ...] = ()
    excluded: tuple[str, ...] = ()
    order: tuple[str, ...] = ()
    subset: tuple[tuple[str, tuple[str, ...]], ...] = ()
    child: str = ""
    child_key: str = ""
    at: str = "any"
    when: tuple[str, ...] = ()
    when_all: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class _PureKindSpec:
    """One declared record kind, its scope, its keys, and its child counts."""

    kind: str
    parent: str | None
    child_order: int
    ordinal_key: str | None
    singleton: bool
    keys: tuple[_PureKeySpec, ...]
    counts: tuple[tuple[str, str], ...] = ()
    parent_ordinal_keys: tuple[str, ...] = ()
    is_scope: bool = False
    state_rules: tuple[_PureStateRule, ...] = ()
    scope_rules: tuple[_PureScopeRule, ...] = ()


_VOCABULARY_OWNER_KIND: tuple[str, ...] = ("local_project_root", "local_module")

_VOCABULARY_DIGEST_ALGORITHM: tuple[str, ...] = ("sha256_opened_bytes",)

_VOCABULARY_LOADER_READINESS: tuple[str, ...] = ("ready", "blocked")

_VOCABULARY_LOADER_READINESS_REASON: tuple[str, ...] = (
    "trusted_local_source_resolved",
    "module_cycle_blocked",
)

_VOCABULARY_SYMBOL_NAMESPACE: tuple[str, ...] = ("type", "relation", "callable")

_VOCABULARY_SYMBOL_KIND: tuple[str, ...] = (
    "type",
    "enum",
    "shape",
    "source",
    "table",
    "query",
    "constraint",
    "derive",
)

_VOCABULARY_BINDING_ISSUE_STATUS: tuple[str, ...] = (
    "unresolved_target_module",
    "unknown_exported_name",
    "private_or_unexported_declaration",
    "inconsistent_target_facade",
    "ambiguous_target_facade",
    "local_declaration_collision",
    "import_binding_collision",
    "duplicate_source_request",
)

_VOCABULARY_EXPORT_ENTRY_ORIGIN: tuple[str, ...] = (
    "local_declaration",
    "explicit_reexport",
)

_VOCABULARY_EXPORT_ISSUE_STATUS: tuple[str, ...] = (
    "unresolved_export_binding",
    "ambiguous_local_declaration",
    "ambiguous_candidate_set",
    "ineligible_or_inconsistent_candidate",
    "duplicate_source_request",
)

_VOCABULARY_LAYERED_AVAILABILITY: tuple[str, ...] = (
    "concrete",
    "unknown",
    "deferred",
    "blocked",
    "absent",
    "ambiguous",
)

_VOCABULARY_RELATION_ROW_STATUS: tuple[str, ...] = (
    "concrete",
    "unknown",
    "deferred",
    "blocked",
)

_VOCABULARY_RELATION_ROW_REASON: tuple[str, ...] = (
    "direct_source_concrete",
    "table_upstream_concrete",
    "relation_upstream_concrete",
    "unknown_schema",
    "duplicate_output_name",
    "duplicate_group_key",
    "unavailable_aggregate_or_grouped_fact",
    "invalid_aggregate_or_grouped_output",
    "aggregate_grouped_deferred",
    "conflicting_aggregate_or_grouped_facts",
    "unavailable_window_result_fact",
    "invalid_window_output",
    "window_result_deferred",
    "conflicting_window_result_facts",
    "deferred_phase48_behavior",
    "unresolved_relation_blocked",
    "cycle_blocked",
    "upstream_unknown",
    "upstream_deferred",
    "upstream_blocked",
)

_VOCABULARY_ROW_FIELD_NULLABILITY: tuple[str, ...] = ("non_null", "nullable", "unknown")

_VOCABULARY_ROW_RESULT_ROLE: tuple[str, ...] = (
    "ordinary_row_value",
    "group_key",
    "aggregate_result",
    "window_result",
)

_VOCABULARY_INSPECTION_BINDING: tuple[str, ...] = (
    "local_declaration",
    "imported_binding",
)

_VOCABULARY_DEPENDENCY_KIND: tuple[str, ...] = (
    "type_reference",
    "source_shape_reference",
    "relation_reference",
    "row_field_reference",
)

_VOCABULARY_REFERENCE_ROLE: tuple[str, ...] = (
    "type_alias_base",
    "shape_field_type",
    "source_shape",
    "relation_from",
    "row_field",
)

_VOCABULARY_LINEAGE_FIELD_KIND: tuple[str, ...] = (
    "source_field",
    "relation_output",
)

_VOCABULARY_ROW_FIELD_KIND: tuple[str, ...] = (
    "shape_field",
    "source_field",
    "relation_output",
)

_VOCABULARY_PROJECTION_KIND: tuple[str, ...] = ("direct", "renamed")

_VOCABULARY_TYPE_REFERENCE_ROLE: tuple[str, ...] = (
    "type_alias_base",
    "shape_field_type",
)

_VOCABULARY_RESOLVED_TYPE_KIND: tuple[str, ...] = (
    "builtin",
    "type",
    "enum",
    "shape",
    "unknown",
)

_VOCABULARY_CLAUSE_DEPENDENCY_ROLE: tuple[str, ...] = (
    "group_key",
    "satisfying",
    "grouped_order",
)

_VOCABULARY_CANDIDATE_BUCKET_STATUS: tuple[str, ...] = (
    "concrete",
    "unknown",
    "deferred",
    "blocked",
    "absent",
    "ambiguous",
)

_VOCABULARY_WINDOW_OUTPUT_STATUS: tuple[str, ...] = (
    "concrete",
    "unknown",
    "deferred",
    "blocked",
)

_VOCABULARY_INSPECTION_ISSUE_FAMILY: tuple[str, ...] = (
    "graph",
    "type_source",
    "relation",
)

PURE_ENUMERATION_VOCABULARIES: Mapping[str, tuple[str, ...]] = MappingProxyType(
    {
        "owner_kind": _VOCABULARY_OWNER_KIND,
        "digest_algorithm": _VOCABULARY_DIGEST_ALGORITHM,
        "loader_readiness": _VOCABULARY_LOADER_READINESS,
        "loader_readiness_reason": _VOCABULARY_LOADER_READINESS_REASON,
        "symbol_namespace": _VOCABULARY_SYMBOL_NAMESPACE,
        "symbol_kind": _VOCABULARY_SYMBOL_KIND,
        "binding_issue_status": _VOCABULARY_BINDING_ISSUE_STATUS,
        "export_entry_origin": _VOCABULARY_EXPORT_ENTRY_ORIGIN,
        "export_issue_status": _VOCABULARY_EXPORT_ISSUE_STATUS,
        "layered_availability": _VOCABULARY_LAYERED_AVAILABILITY,
        "relation_row_status": _VOCABULARY_RELATION_ROW_STATUS,
        "relation_row_reason": _VOCABULARY_RELATION_ROW_REASON,
        "row_field_nullability": _VOCABULARY_ROW_FIELD_NULLABILITY,
        "row_result_role": _VOCABULARY_ROW_RESULT_ROLE,
        "inspection_binding": _VOCABULARY_INSPECTION_BINDING,
        "dependency_kind": _VOCABULARY_DEPENDENCY_KIND,
        "reference_role": _VOCABULARY_REFERENCE_ROLE,
        "row_field_kind": _VOCABULARY_ROW_FIELD_KIND,
        "lineage_field_kind": _VOCABULARY_LINEAGE_FIELD_KIND,
        "projection_kind": _VOCABULARY_PROJECTION_KIND,
        "type_reference_role": _VOCABULARY_TYPE_REFERENCE_ROLE,
        "resolved_type_kind": _VOCABULARY_RESOLVED_TYPE_KIND,
        "clause_dependency_role": _VOCABULARY_CLAUSE_DEPENDENCY_ROLE,
        "candidate_bucket_status": _VOCABULARY_CANDIDATE_BUCKET_STATUS,
        "window_output_status": _VOCABULARY_WINDOW_OUTPUT_STATUS,
        "inspection_issue_family": _VOCABULARY_INSPECTION_ISSUE_FAMILY,
    }
)

_TEXT = ProjectPureTag.TEXT
_INTEGER = ProjectPureTag.INTEGER
_BOOLEAN = ProjectPureTag.BOOLEAN
_ENUMERATION = ProjectPureTag.ENUMERATION


def _key(
    key: str,
    tag: ProjectPureTag,
    *,
    optional: bool = False,
    vocabulary: str | None = None,
) -> _PureKeySpec:
    """Declare one key of one record kind."""

    return _PureKeySpec(
        key=key,
        tag=tag,
        optional=optional,
        vocabulary=(
            None if vocabulary is None else PURE_ENUMERATION_VOCABULARIES[vocabulary]
        ),
    )


_PURE_KIND_DECLARATIONS: tuple[_PureKindSpec, ...] = (
    _PureKindSpec(
        kind="inspection",
        parent=None,
        child_order=0,
        ordinal_key=None,
        singleton=True,
        keys=(
            _key("format", _ENUMERATION),
            _key("modules", _INTEGER),
        ),
        counts=(("modules", "module"),),
        is_scope=True,
    ),
    _PureKindSpec(
        kind="owner",
        parent="inspection",
        child_order=0,
        ordinal_key=None,
        singleton=True,
        keys=(
            _key("kind", _ENUMERATION, vocabulary="owner_kind"),
            _key("namespace", _TEXT),
            _key("name", _TEXT),
        ),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("kind", "namespace", "name"),
                admitted=(("local_project_root", "", ""),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="module",
        parent="inspection",
        child_order=1,
        ordinal_key="module",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("path", _TEXT),
        ),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("path",),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.GROUPED_SEQUENCES_EQUAL,
                pairs=(
                    ("readiness_cycle_member", "path"),
                    ("graph_component_member", "path"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="digest",
        parent="module",
        child_order=1,
        ordinal_key=None,
        singleton=True,
        keys=(
            _key("module", _INTEGER),
            _key("algorithm", _ENUMERATION, vocabulary="digest_algorithm"),
            _key("digest", _TEXT),
            _key("byte_count", _INTEGER),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.LOWERCASE_HEX,
                keys=("digest",),
                text_length=64,
            ),
        ),
    ),
    _PureKindSpec(
        kind="readiness",
        parent="module",
        child_order=2,
        ordinal_key=None,
        singleton=True,
        keys=(
            _key("module", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="loader_readiness"),
            _key("reason", _ENUMERATION, vocabulary="loader_readiness_reason"),
            _key("cycles", _INTEGER),
        ),
        counts=(("cycles", "readiness_cycle"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("status", "reason", "cycles"),
                admitted=(
                    ("ready", "trusted_local_source_resolved", "zero"),
                    ("blocked", "module_cycle_blocked", "one"),
                    ("blocked", "module_cycle_blocked", "many"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="readiness_cycle",
        parent="readiness",
        child_order=0,
        ordinal_key="cycle",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("cycle", _INTEGER),
            _key("members", _INTEGER),
        ),
        counts=(("members", "readiness_cycle_member"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(_PureStateRule(rule=_PureStateKind.POSITIVE, keys=("members",)),),
    ),
    _PureKindSpec(
        kind="readiness_cycle_member",
        parent="readiness_cycle",
        child_order=0,
        ordinal_key="member",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("cycle", _INTEGER),
            _key("member", _INTEGER),
            _key("path", _TEXT),
        ),
        parent_ordinal_keys=("module", "cycle"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("path",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="graph",
        parent="module",
        child_order=3,
        ordinal_key=None,
        singleton=True,
        keys=(
            _key("module", _INTEGER),
            _key("component_is_cyclic", _BOOLEAN),
            _key("component_members", _INTEGER),
            _key("dependency_targets", _INTEGER),
            _key("import_evidence", _INTEGER),
        ),
        counts=(
            ("component_members", "graph_component_member"),
            ("dependency_targets", "graph_dependency_target"),
            ("import_evidence", "graph_import_evidence"),
        ),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(rule=_PureStateKind.POSITIVE, keys=("component_members",)),
            _PureStateRule(
                rule=_PureStateKind.MULTI_REQUIRES_TRUE,
                keys=("component_members", "component_is_cyclic"),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.UNCLE_COMBINATION,
                scope="module",
                child="readiness",
                child_key="status",
                pairs=(("component_is_cyclic", "component_is_cyclic"),),
                admitted=(("true", "blocked"), ("false", "ready")),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.SCOPE_CONTAINS_ANCESTOR,
                scope="module",
                child="graph_dependency_target",
                pairs=(("path", "path"),),
                when_all=(
                    ("component_members", "one"),
                    ("component_is_cyclic", "true"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.SCOPE_EXCLUDES_ANCESTOR,
                scope="module",
                child="graph_dependency_target",
                pairs=(("path", "path"),),
                when_all=(
                    ("component_members", "one"),
                    ("component_is_cyclic", "false"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.COLLECTED_SETS_EQUAL,
                pairs=(
                    ("graph_import_evidence", "path"),
                    ("graph_dependency_target", "path"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.SCOPE_CONTAINS_ANCESTOR,
                scope="module",
                child="graph_component_member",
                pairs=(("path", "path"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="graph_component_member",
        parent="graph",
        child_order=0,
        ordinal_key="member",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("member", _INTEGER),
            _key("path", _TEXT),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("path",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="graph_dependency_target",
        parent="graph",
        child_order=1,
        ordinal_key="target",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("target", _INTEGER),
            _key("path", _TEXT),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("path",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="graph_import_evidence",
        parent="graph",
        child_order=2,
        ordinal_key="evidence",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("evidence", _INTEGER),
            _key("path", _TEXT),
            _key("module_statement_position", _INTEGER),
            _key("item_position", _INTEGER),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(
                    ("module_statement_position", "module_statement_position"),
                    ("item_position", "item_position"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="import",
        parent="module",
        child_order=4,
        ordinal_key="request",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("request", _INTEGER),
            _key("local_name", _TEXT),
            _key("namespace", _ENUMERATION, vocabulary="symbol_namespace"),
            _key("declaration_kind", _ENUMERATION, vocabulary="symbol_kind"),
            _key("target_module_path", _TEXT),
            _key("exported_name", _TEXT),
            _key("module_statement_position", _INTEGER),
            _key("item_position", _INTEGER),
            _key("resolved_module_path", _TEXT, optional=True),
            _key(
                "resolved_namespace",
                _ENUMERATION,
                optional=True,
                vocabulary="symbol_namespace",
            ),
            _key(
                "resolved_declaration_kind",
                _ENUMERATION,
                optional=True,
                vocabulary="symbol_kind",
            ),
            _key("resolved_declared_name", _TEXT, optional=True),
            _key("issues", _INTEGER),
        ),
        counts=(("issues", "import_issue"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("local_name", "exported_name", "resolved_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("resolved_module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "declaration_kind"),
                admitted=(
                    ("type", "type"),
                    ("type", "enum"),
                    ("type", "shape"),
                    ("relation", "source"),
                    ("relation", "table"),
                    ("relation", "query"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("namespace", "resolved_namespace"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("declaration_kind", "resolved_declaration_kind"),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=(
                    "resolved_module_path",
                    "resolved_namespace",
                    "resolved_declaration_kind",
                    "resolved_declared_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("resolved_module_path", "issues"),
                presence_keys=("resolved_module_path",),
                admitted=(
                    ("present", "zero"),
                    ("present", "one"),
                    ("absent", "one"),
                    ("absent", "many"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.SCOPE_REQUIRES_CHILD,
                child="import_issue",
                child_key="status",
                excluded=("duplicate_source_request",),
                presence=("resolved_module_path",),
                when=("resolved_module_path", "absent"),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(
                    ("module_statement_position", "module_statement_position"),
                    ("item_position", "item_position"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="import_issue",
        parent="import",
        child_order=0,
        ordinal_key="issue",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("request", _INTEGER),
            _key("issue", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="binding_issue_status"),
        ),
        parent_ordinal_keys=("module", "request"),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING,
                pairs=(("status", "status"),),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_COMBINATION,
                scope="import",
                pairs=(("status", "resolved_module_path"),),
                presence=("resolved_module_path",),
                admitted=(
                    ("duplicate_source_request", "present"),
                    ("*", "absent"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("status",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="export",
        parent="module",
        child_order=5,
        ordinal_key="request",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("request", _INTEGER),
            _key("local_name", _TEXT),
            _key("namespace", _ENUMERATION, vocabulary="symbol_namespace"),
            _key("declaration_kind", _ENUMERATION, vocabulary="symbol_kind"),
            _key("module_statement_position", _INTEGER),
            _key("item_position", _INTEGER),
            _key("exposed_name", _TEXT, optional=True),
            _key(
                "entry_origin",
                _ENUMERATION,
                optional=True,
                vocabulary="export_entry_origin",
            ),
            _key("target_module_path", _TEXT, optional=True),
            _key(
                "target_namespace",
                _ENUMERATION,
                optional=True,
                vocabulary="symbol_namespace",
            ),
            _key(
                "target_declaration_kind",
                _ENUMERATION,
                optional=True,
                vocabulary="symbol_kind",
            ),
            _key("target_declared_name", _TEXT, optional=True),
            _key("issues", _INTEGER),
        ),
        counts=(("issues", "export_issue"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("local_name", "exposed_name", "target_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("target_module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "declaration_kind"),
                admitted=(
                    ("type", "type"),
                    ("type", "enum"),
                    ("type", "shape"),
                    ("relation", "source"),
                    ("relation", "table"),
                    ("relation", "query"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("namespace", "target_namespace"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("declaration_kind", "target_declaration_kind"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("local_name", "exposed_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("local_name", "target_declared_name"),
                when=("entry_origin", "local_declaration"),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=(
                    "exposed_name",
                    "entry_origin",
                    "target_module_path",
                    "target_namespace",
                    "target_declaration_kind",
                    "target_declared_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("entry_origin", "issues"),
                presence_keys=("entry_origin",),
                admitted=(
                    ("present", "zero"),
                    ("present", "one"),
                    ("absent", "one"),
                    ("absent", "many"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.SCOPE_REQUIRES_CHILD,
                child="export_issue",
                child_key="status",
                excluded=("duplicate_source_request",),
                presence=("entry_origin",),
                when=("entry_origin", "absent"),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(
                    ("module_statement_position", "module_statement_position"),
                    ("item_position", "item_position"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="module",
                pairs=(("target_module_path", "path"),),
                when=("entry_origin", "local_declaration"),
            ),
        ),
    ),
    _PureKindSpec(
        kind="export_issue",
        parent="export",
        child_order=0,
        ordinal_key="issue",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("request", _INTEGER),
            _key("issue", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="export_issue_status"),
        ),
        parent_ordinal_keys=("module", "request"),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING,
                pairs=(("status", "status"),),
                order=(
                    "duplicate_source_request",
                    "ambiguous_local_declaration",
                    "ineligible_or_inconsistent_candidate",
                    "ambiguous_candidate_set",
                    "unresolved_export_binding",
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_COMBINATION,
                scope="export",
                pairs=(("status", "entry_origin"),),
                presence=("entry_origin",),
                admitted=(
                    ("duplicate_source_request", "present"),
                    ("*", "absent"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("status",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="declaration",
        parent="module",
        child_order=6,
        ordinal_key="declaration",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("declaration", _INTEGER),
            _key("owner_kind", _ENUMERATION, vocabulary="owner_kind"),
            _key("owner_namespace", _TEXT),
            _key("owner_name", _TEXT),
            _key("namespace", _ENUMERATION, vocabulary="symbol_namespace"),
            _key("declaration_kind", _ENUMERATION, vocabulary="symbol_kind"),
            _key("declared_name", _TEXT),
            _key("availability", _ENUMERATION, vocabulary="layered_availability"),
            _key("occurrence_count", _INTEGER),
            _key("occurrence_index", _INTEGER),
            _key(
                "relation_status",
                _ENUMERATION,
                optional=True,
                vocabulary="relation_row_status",
            ),
            _key(
                "relation_reason",
                _ENUMERATION,
                optional=True,
                vocabulary="relation_row_reason",
            ),
            _key("row_fields", _INTEGER),
        ),
        counts=(("row_fields", "declaration_row_field"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("declared_name",),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "declaration_kind"),
                admitted=(
                    ("type", "type"),
                    ("type", "enum"),
                    ("type", "shape"),
                    ("relation", "source"),
                    ("relation", "table"),
                    ("relation", "query"),
                    ("callable", "constraint"),
                    ("callable", "derive"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("owner_name",),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("owner_kind", "owner_namespace"),
                admitted=(("local_module", ""),),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=("relation_status", "relation_reason"),
            ),
            _PureStateRule(
                rule=_PureStateKind.POSITIVE_REQUIRES_PRESENT,
                keys=("row_fields", "relation_status"),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "availability", "relation_status"),
                admitted=(
                    ("relation", "concrete", "concrete"),
                    ("relation", "unknown", "unknown"),
                    ("relation", "deferred", "deferred"),
                    ("relation", "blocked", "blocked"),
                    ("relation", "blocked", "absent"),
                    ("relation", "ambiguous", "absent"),
                    ("type", "absent", "absent"),
                    ("type", "blocked", "absent"),
                    ("type", "ambiguous", "absent"),
                    ("callable", "absent", "absent"),
                    ("callable", "blocked", "absent"),
                    ("callable", "ambiguous", "absent"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.STRICTLY_LESS,
                keys=("occurrence_index", "occurrence_count"),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.UNCLE_COMBINATION,
                scope="module",
                child="readiness",
                child_key="status",
                pairs=(
                    ("availability", "availability"),
                    ("occurrence_count", "occurrence_count"),
                ),
                admitted=(
                    ("blocked", "one", "blocked"),
                    ("blocked", "many", "blocked"),
                    ("ambiguous", "many", "ready"),
                    ("concrete", "one", "ready"),
                    ("unknown", "one", "ready"),
                    ("deferred", "one", "ready"),
                    ("absent", "one", "ready"),
                    ("blocked", "one", "ready"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.SIBLING_BUCKETS_COMPLETE,
                distinct=("namespace", "declaration_kind", "declared_name"),
                pairs=(("occurrence_index", "occurrence_count"),),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="module",
                pairs=(("owner_name", "path"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="declaration_row_field",
        parent="declaration",
        child_order=0,
        ordinal_key="field",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("declaration", _INTEGER),
            _key("field", _INTEGER),
            _key("name", _TEXT),
            _key("nullability", _ENUMERATION, vocabulary="row_field_nullability"),
            _key("result_role", _ENUMERATION, vocabulary="row_result_role"),
        ),
        parent_ordinal_keys=("module", "declaration"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("name",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("name",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="origin",
        parent="module",
        child_order=7,
        ordinal_key="origin",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("origin", _INTEGER),
            _key("namespace", _ENUMERATION, vocabulary="symbol_namespace"),
            _key("declaration_kind", _ENUMERATION, vocabulary="symbol_kind"),
            _key("local_name", _TEXT),
            _key("binding", _ENUMERATION, vocabulary="inspection_binding"),
            _key("target_module_path", _TEXT),
            _key("target_declaration_position", _INTEGER),
            _key("target_declared_name", _TEXT),
            _key("hops", _INTEGER),
        ),
        counts=(("hops", "origin_hop"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("local_name", "target_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "declaration_kind"),
                admitted=(
                    ("type", "type"),
                    ("type", "enum"),
                    ("type", "shape"),
                    ("relation", "source"),
                    ("relation", "table"),
                    ("relation", "query"),
                    ("callable", "constraint"),
                    ("callable", "derive"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("target_module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("local_name", "target_declared_name"),
                when=("binding", "local_declaration"),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("binding", "hops"),
                admitted=(
                    ("local_declaration", "zero"),
                    ("imported_binding", "one"),
                    ("imported_binding", "many"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SUBTREES,
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="module",
                pairs=(("target_module_path", "path"),),
                when=("binding", "local_declaration"),
            ),
        ),
    ),
    _PureKindSpec(
        kind="origin_hop",
        parent="origin",
        child_order=0,
        ordinal_key="hop",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("origin", _INTEGER),
            _key("hop", _INTEGER),
            _key("import_target_module_path", _TEXT),
            _key("import_exported_name", _TEXT),
            _key("import_module_statement_position", _INTEGER),
            _key("import_item_position", _INTEGER),
            _key("facade_module_path", _TEXT),
            _key("facade_exposed_name", _TEXT),
            _key("facade_origin", _ENUMERATION, vocabulary="export_entry_origin"),
            _key("target_module_path", _TEXT),
            _key("target_declared_name", _TEXT),
        ),
        parent_ordinal_keys=("module", "origin"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=(
                    "import_exported_name",
                    "facade_exposed_name",
                    "target_declared_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("facade_module_path", "target_module_path"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("import_target_module_path", "facade_module_path"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("import_exported_name", "facade_exposed_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("facade_module_path", "target_module_path"),
                when=("facade_origin", "local_declaration"),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("facade_exposed_name", "target_declared_name"),
                when=("facade_origin", "local_declaration"),
            ),
            _PureStateRule(
                rule=_PureStateKind.TERMINAL_COMBINATION,
                keys=("facade_origin",),
                terminal=("local_declaration", "explicit_reexport"),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="origin",
                pairs=(
                    ("target_module_path", "target_module_path"),
                    ("target_declared_name", "target_declared_name"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="dependency",
        parent="module",
        child_order=8,
        ordinal_key="dependency",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("dependency", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary="dependency_kind"),
            _key("reference_owner_declaration_position", _INTEGER),
            _key("reference_role", _ENUMERATION, vocabulary="reference_role"),
            _key("reference_member_position", _INTEGER),
            _key("target_declaration_module_path", _TEXT, optional=True),
            _key("target_declaration_position", _INTEGER, optional=True),
            _key("target_declaration_declared_name", _TEXT, optional=True),
            _key(
                "target_row_field_owner_declaration_position",
                _INTEGER,
                optional=True,
            ),
            _key(
                "target_row_field_kind",
                _ENUMERATION,
                optional=True,
                vocabulary="row_field_kind",
            ),
            _key("target_row_field_position", _INTEGER, optional=True),
            _key("target_row_field_name", _TEXT, optional=True),
        ),
        parent_ordinal_keys=("module",),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=(
                    "kind",
                    "reference_owner_declaration_position",
                    "reference_role",
                    "reference_member_position",
                    "target_declaration_module_path",
                    "target_declaration_position",
                    "target_declaration_declared_name",
                    "target_row_field_owner_declaration_position",
                    "target_row_field_kind",
                    "target_row_field_position",
                    "target_row_field_name",
                ),
            ),
        ),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("target_declaration_declared_name", "target_row_field_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("target_declaration_module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=(
                    "target_declaration_module_path",
                    "target_declaration_position",
                    "target_declaration_declared_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=(
                    "target_row_field_owner_declaration_position",
                    "target_row_field_kind",
                    "target_row_field_position",
                    "target_row_field_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=(
                    "kind",
                    "reference_role",
                    "reference_member_position",
                    "target_declaration_module_path",
                    "target_row_field_owner_declaration_position",
                ),
                presence_keys=(
                    "target_declaration_module_path",
                    "target_row_field_owner_declaration_position",
                ),
                admitted=(
                    (
                        "type_reference",
                        "type_alias_base",
                        "zero",
                        "present",
                        "absent",
                    ),
                    ("type_reference", "shape_field_type", "*", "present", "absent"),
                    (
                        "source_shape_reference",
                        "source_shape",
                        "zero",
                        "present",
                        "absent",
                    ),
                    (
                        "relation_reference",
                        "relation_from",
                        "zero",
                        "present",
                        "absent",
                    ),
                    ("row_field_reference", "row_field", "*", "absent", "present"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="row_lineage",
        parent="module",
        child_order=9,
        ordinal_key="lineage",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("lineage", _INTEGER),
            _key("owner_declaration_position", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="relation_row_status"),
            _key("reason", _ENUMERATION, vocabulary="relation_row_reason"),
            _key("fields", _INTEGER),
        ),
        counts=(("fields", "row_lineage_field"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("status", "fields"),
                admitted=(
                    ("concrete", "zero"),
                    ("concrete", "one"),
                    ("concrete", "many"),
                    ("unknown", "zero"),
                    ("deferred", "zero"),
                    ("blocked", "zero"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("owner_declaration_position", "owner_declaration_position"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="row_lineage_field",
        parent="row_lineage",
        child_order=0,
        ordinal_key="field",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("lineage", _INTEGER),
            _key("field", _INTEGER),
            _key("kind", _ENUMERATION, vocabulary="lineage_field_kind"),
            _key("field_position", _INTEGER),
            _key("name", _TEXT),
            _key("paths", _INTEGER),
        ),
        counts=(("paths", "row_lineage_path"),),
        parent_ordinal_keys=("module", "lineage"),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("name",),
            ),
            _PureStateRule(rule=_PureStateKind.POSITIVE, keys=("paths",)),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("name",),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("field_position", "field_position"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="row_lineage_path",
        parent="row_lineage_field",
        child_order=0,
        ordinal_key="path",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("lineage", _INTEGER),
            _key("field", _INTEGER),
            _key("path", _INTEGER),
            _key("root_module_path", _TEXT),
            _key("root_owner_declaration_position", _INTEGER),
            _key("root_field_position", _INTEGER),
            _key("root_field_name", _TEXT),
            _key("hops", _INTEGER),
        ),
        counts=(("hops", "row_lineage_hop"),),
        parent_ordinal_keys=("module", "lineage", "field"),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("root_field_name",),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("root_module_path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_COMBINATION,
                scope="row_lineage_field",
                pairs=(("hops", "kind"),),
                admitted=(
                    ("zero", "source_field"),
                    ("one", "*"),
                    ("many", "*"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SUBTREES,
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="row_lineage_field",
                pairs=(
                    ("root_field_name", "name"),
                    ("root_field_position", "field_position"),
                ),
                when=("hops", "zero"),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="row_lineage",
                pairs=(
                    (
                        "root_owner_declaration_position",
                        "owner_declaration_position",
                    ),
                ),
                when=("hops", "zero"),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="module",
                pairs=(("root_module_path", "path"),),
                when=("hops", "zero"),
            ),
        ),
    ),
    _PureKindSpec(
        kind="row_lineage_hop",
        parent="row_lineage_path",
        child_order=0,
        ordinal_key="hop",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("lineage", _INTEGER),
            _key("field", _INTEGER),
            _key("path", _INTEGER),
            _key("hop", _INTEGER),
            _key("projection_kind", _ENUMERATION, vocabulary="projection_kind"),
            _key("output_field_name", _TEXT),
            _key("upstream_field_name", _TEXT),
        ),
        parent_ordinal_keys=("module", "lineage", "field", "path"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.EQUALITY_COMBINATION,
                keys=("projection_kind", "output_field_name", "upstream_field_name"),
                admitted=(("direct", "equal"), ("renamed", "distinct")),
            ),
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("output_field_name", "upstream_field_name"),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="row_lineage_field",
                pairs=(("output_field_name", "name"),),
                at="first",
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_EQUAL,
                pairs=(("output_field_name", "upstream_field_name"),),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_EQUAL,
                scope="row_lineage_path",
                pairs=(("upstream_field_name", "root_field_name"),),
                at="last",
            ),
        ),
    ),
    _PureKindSpec(
        kind="type_resolution",
        parent="module",
        child_order=10,
        ordinal_key="resolution",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("resolution", _INTEGER),
            _key("owner_declaration_position", _INTEGER),
            _key("role", _ENUMERATION, vocabulary="type_reference_role"),
            _key("member_position", _INTEGER),
            _key("direct_kind", _ENUMERATION, vocabulary="resolved_type_kind"),
            _key("canonical_kind", _ENUMERATION, vocabulary="resolved_type_kind"),
            _key("canonical_name", _TEXT),
            _key("canonical_target_module_path", _TEXT, optional=True),
            _key("canonical_target_declared_name", _TEXT, optional=True),
            _key("alias_chain", _INTEGER),
        ),
        counts=(("alias_chain", "type_resolution_alias"),),
        parent_ordinal_keys=("module",),
        is_scope=True,
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("role", "member_position"),
                admitted=(("type_alias_base", "zero"), ("shape_field_type", "*")),
            ),
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("canonical_name", "canonical_target_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("canonical_target_module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.PRESENCE_GROUP,
                keys=(
                    "canonical_target_module_path",
                    "canonical_target_declared_name",
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("canonical_kind", "canonical_target_module_path"),
                presence_keys=("canonical_target_module_path",),
                admitted=(
                    ("builtin", "absent"),
                    ("unknown", "absent"),
                    ("enum", "present"),
                    ("shape", "present"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("canonical_name", "canonical_target_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("canonical_kind", "canonical_name"),
                admitted=(
                    ("builtin", "Any"),
                    ("builtin", "Bool"),
                    ("builtin", "Bytes"),
                    ("builtin", "Date"),
                    ("builtin", "Decimal"),
                    ("builtin", "Float"),
                    ("builtin", "Int"),
                    ("builtin", "Json"),
                    ("builtin", "Text"),
                    ("builtin", "Timestamp"),
                    ("builtin", "UUID"),
                    ("unknown", "<unknown>"),
                    ("enum", "*"),
                    ("shape", "*"),
                ),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("direct_kind", "canonical_kind", "alias_chain"),
                admitted=(
                    ("type", "builtin", "one"),
                    ("type", "builtin", "many"),
                    ("type", "enum", "one"),
                    ("type", "enum", "many"),
                    ("type", "shape", "one"),
                    ("type", "shape", "many"),
                    ("type", "unknown", "one"),
                    ("type", "unknown", "many"),
                    ("builtin", "builtin", "zero"),
                    ("enum", "enum", "zero"),
                    ("shape", "shape", "zero"),
                    ("unknown", "unknown", "zero"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(
                    ("owner_declaration_position", "owner_declaration_position"),
                    ("member_position", "member_position"),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="type_resolution_alias",
        parent="type_resolution",
        child_order=0,
        ordinal_key="alias",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("resolution", _INTEGER),
            _key("alias", _INTEGER),
            _key("module_path", _TEXT),
            _key("namespace", _ENUMERATION, vocabulary="symbol_namespace"),
            _key("declaration_kind", _ENUMERATION, vocabulary="symbol_kind"),
            _key("declared_name", _TEXT),
        ),
        parent_ordinal_keys=("module", "resolution"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("declared_name",),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("module_path",),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("namespace", "declaration_kind"),
                admitted=(("type", "type"),),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.DISTINCT_SIBLINGS,
                distinct=("module_path", "declared_name"),
            ),
        ),
    ),
    _PureKindSpec(
        kind="source_shape_resolution",
        parent="module",
        child_order=11,
        ordinal_key="resolution",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("resolution", _INTEGER),
            _key("owner_declaration_position", _INTEGER),
            _key("target_module_path", _TEXT),
            _key("target_declared_name", _TEXT),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("target_declared_name",),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("target_module_path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("owner_declaration_position", "owner_declaration_position"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="relation_resolution",
        parent="module",
        child_order=12,
        ordinal_key="resolution",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("resolution", _INTEGER),
            _key("owner_declaration_position", _INTEGER),
            _key("local_name", _TEXT),
            _key("target_module_path", _TEXT),
            _key("target_declared_name", _TEXT),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("local_name", "target_declared_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.MODULE_PATH,
                keys=("target_module_path",),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("owner_declaration_position", "owner_declaration_position"),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="semantic_facts",
        parent="module",
        child_order=13,
        ordinal_key="facts",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("facts", _INTEGER),
            _key("owner_declaration_position", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="relation_row_status"),
            _key("reason", _ENUMERATION, vocabulary="relation_row_reason"),
            _key("let_bindings", _INTEGER),
            _key("selects", _INTEGER),
            _key("clause_dependencies", _INTEGER),
            _key("window_outputs", _INTEGER),
        ),
        counts=(
            ("let_bindings", "semantic_let_binding"),
            ("selects", "semantic_select"),
            ("clause_dependencies", "semantic_clause_dependency"),
            ("window_outputs", "semantic_window_output"),
        ),
        parent_ordinal_keys=("module",),
        is_scope=True,
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("owner_declaration_position", "owner_declaration_position"),),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.COLLECTED_SUBSET,
                subset=(
                    (
                        "semantic_window_output",
                        ("selected_output_ordinal", "output_name"),
                    ),
                    ("semantic_select", ("selected_output_ordinal", "output_name")),
                ),
            ),
        ),
    ),
    _PureKindSpec(
        kind="semantic_let_binding",
        parent="semantic_facts",
        child_order=0,
        ordinal_key="binding",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("facts", _INTEGER),
            _key("binding", _INTEGER),
            _key("binding_ordinal", _INTEGER),
            _key("has_value_type", _BOOLEAN),
        ),
        parent_ordinal_keys=("module", "facts"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("binding", "binding_ordinal"),
            ),
        ),
    ),
    _PureKindSpec(
        kind="semantic_select",
        parent="semantic_facts",
        child_order=1,
        ordinal_key="select",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("facts", _INTEGER),
            _key("select", _INTEGER),
            _key("selected_output_ordinal", _INTEGER),
            _key("output_name", _TEXT, optional=True),
        ),
        parent_ordinal_keys=("module", "facts"),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.EQUAL_IF_PRESENT,
                keys=("select", "selected_output_ordinal"),
            ),
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT, keys=("output_name",)
            ),
        ),
    ),
    _PureKindSpec(
        kind="semantic_clause_dependency",
        parent="semantic_facts",
        child_order=2,
        ordinal_key="dependency",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("facts", _INTEGER),
            _key("dependency", _INTEGER),
            _key("role", _ENUMERATION, vocabulary="clause_dependency_role"),
            _key("source_ordinal", _INTEGER),
            _key("status", _ENUMERATION, vocabulary="candidate_bucket_status"),
        ),
        parent_ordinal_keys=("module", "facts"),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING,
                pairs=(("role", "role"),),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.SIBLING_BUCKETS_COMPLETE,
                distinct=("role",),
                pairs=(("source_ordinal", ""),),
            ),
        ),
    ),
    _PureKindSpec(
        kind="semantic_window_output",
        parent="semantic_facts",
        child_order=3,
        ordinal_key="output",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("facts", _INTEGER),
            _key("output", _INTEGER),
            _key("selected_output_ordinal", _INTEGER),
            _key("output_name", _TEXT, optional=True),
            _key("status", _ENUMERATION, vocabulary="window_output_status"),
        ),
        parent_ordinal_keys=("module", "facts"),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.ANCESTOR_COMBINATION,
                scope="semantic_facts",
                pairs=(("status", "status"),),
                admitted=(
                    ("concrete", "concrete"),
                    ("*", "unknown"),
                    ("*", "deferred"),
                    ("*", "blocked"),
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_INCREASING,
                pairs=(("selected_output_ordinal", "selected_output_ordinal"),),
            ),
        ),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("output_name",),
            ),
        ),
    ),
    _PureKindSpec(
        kind="issue",
        parent="module",
        child_order=14,
        ordinal_key="issue",
        singleton=False,
        keys=(
            _key("module", _INTEGER),
            _key("issue", _INTEGER),
            _key("family", _ENUMERATION, vocabulary="inspection_issue_family"),
            _key("status", _TEXT),
            _key("local_name", _TEXT, optional=True),
        ),
        parent_ordinal_keys=("module",),
        state_rules=(
            _PureStateRule(
                rule=_PureStateKind.NON_EMPTY_IF_PRESENT,
                keys=("status", "local_name"),
            ),
            _PureStateRule(
                rule=_PureStateKind.COMBINATION,
                keys=("family", "status", "local_name"),
                presence_keys=("local_name",),
                admitted=(
                    ("graph", "unresolved_target_module", "absent"),
                    ("graph", "duplicate_or_conflicting_module_identity", "absent"),
                    ("graph", "module_import_cycle", "absent"),
                    ("graph", "unsupported_explicit_module_reference", "absent"),
                    ("type_source", "ambiguous_local_type_name", "present"),
                    ("type_source", "ambiguous_local_source_name", "present"),
                    ("type_source", "unknown_type_reference", "present"),
                    ("type_source", "type_alias_cycle", "present"),
                    ("type_source", "unknown_source_shape_reference", "present"),
                    ("type_source", "incompatible_source_shape_kind", "present"),
                    ("type_source", "module_graph_cycle_blocked", "*"),
                    ("type_source", "module_diagnostic_blocked", "present"),
                    ("relation", "ambiguous_local_relation_name", "present"),
                    ("relation", "unknown_relation_reference", "present"),
                    ("relation", "unknown_direct_field", "present"),
                    ("relation", "local_relation_cycle", "present"),
                    ("relation", "module_graph_cycle_blocked", "*"),
                    ("relation", "module_diagnostic_blocked", "present"),
                    ("relation", "type_source_diagnostic_blocked", "present"),
                ),
            ),
        ),
        scope_rules=(
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING,
                pairs=(("status", "status"),),
                when=("family", "graph"),
                order=(
                    "unresolved_target_module",
                    "duplicate_or_conflicting_module_identity",
                    "module_import_cycle",
                    "unsupported_explicit_module_reference",
                ),
            ),
            _PureScopeRule(
                rule=_PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING,
                pairs=(("family", "family"),),
            ),
        ),
    ),
)

PURE_RECORD_SCHEMA: Mapping[str, _PureKindSpec] = MappingProxyType(
    {declaration.kind: declaration for declaration in _PURE_KIND_DECLARATIONS}
)

PURE_RECORD_KINDS: tuple[str, ...] = tuple(
    declaration.kind for declaration in _PURE_KIND_DECLARATIONS
)

_PURE_HEADER_KINDS: tuple[str, ...] = ("inspection", "owner")
# A scope whose whole subtree is the identity of one upstream fact, so two
# subtrees that differ only in their portable ordinals are one fact twice. The
# set is derived from the declared rules, never written down twice.
_PURE_SUBTREE_KINDS: frozenset[str] = frozenset(
    kind
    for kind, specification in PURE_RECORD_SCHEMA.items()
    if any(
        rule.rule is _PureScopeKind.DISTINCT_SUBTREES
        for rule in specification.scope_rules
    )
)


_PURE_REQUIRED_MODULE_RECORDS: tuple[str, ...] = ("digest", "readiness", "graph")


class _PureFrame:
    """One open scope during the single validation pass.

    A frame is mutable working state of one evaluation call. It never escapes
    the call, so the boundary stays free of observable global mutable state.
    """

    __slots__ = (
        "child_counts",
        "declared_counts",
        "kind",
        "last_child_order",
        "buckets",
        "collected",
        "identity",
        "grouped_tuples",
        "parent_frame",
        "subtree",
        "membership_required",
        "membership_seen",
        "ordinal",
        "previous_child",
        "record",
        "record_position",
        "seen_children",
    )

    def __init__(
        self,
        *,
        kind: str,
        ordinal: int | None,
        record_position: int,
        declared_counts: tuple[tuple[int, str], ...],
        record: ProjectPureRecord | None = None,
        membership_required: tuple[tuple[str, str, ProjectPureValue, bool], ...] = (),
        identity: tuple[str, ...] = (),
        parent_frame: _PureFrame | None = None,
    ) -> None:
        self.kind = kind
        self.ordinal = ordinal
        self.record_position = record_position
        self.declared_counts = declared_counts
        self.record = record
        self.child_counts: dict[str, int] = {}
        self.last_child_order = -1
        self.previous_child: dict[str, ProjectPureRecord] = {}
        self.seen_children: dict[str, set[tuple[str, ...]]] = {}
        self.membership_required = membership_required
        self.membership_seen: set[tuple[str, str]] = set()
        self.collected: dict[tuple[str, str], list[tuple[int, str]]] = {}
        self.buckets: dict[str, dict[tuple[str, ...], list[tuple[int, int]]]] = {}
        self.subtree: list[tuple[str, ...]] = []
        self.identity = identity
        self.parent_frame = parent_frame
        self.grouped_tuples: dict[
            tuple[str, tuple[str, ...]], list[tuple[str, ...]]
        ] = {}


def _reject(
    status: ProjectPureStatus,
    record_position: int | None = None,
    field_position: int | None = None,
) -> ProjectPureOutcome:
    """Build one normalized rejection with its structural coordinates only."""

    return ProjectPureOutcome(
        status=status,
        record_position=record_position,
        field_position=field_position,
    )


def _validate_fields(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    record_position: int,
) -> ProjectPureOutcome | None:
    """Validate one record's declared arity, keys, tags, and payloads."""

    if len(record.fields) != len(specification.keys):
        return _reject(ProjectPureStatus.FIELD_ARITY_MISMATCH, record_position)
    for position, (supplied, declared) in enumerate(
        zip(record.fields, specification.keys, strict=True)
    ):
        if supplied.key != declared.key:
            return _reject(
                ProjectPureStatus.FIELD_KEY_MISMATCH, record_position, position
            )
        rejection = _validate_value(supplied.value, declared, record_position, position)
        if rejection is not None:
            return rejection
    return None


def _validate_value(
    value: ProjectPureValue,
    declared: _PureKeySpec,
    record_position: int,
    field_position: int,
) -> ProjectPureOutcome | None:
    """Validate one supplied value against one declared key."""

    if value.tag is ProjectPureTag.ABSENT:
        if not declared.optional:
            return _reject(
                ProjectPureStatus.ABSENT_VALUE_NOT_ALLOWED,
                record_position,
                field_position,
            )
        if value.text is not None or value.integer is not None:
            return _reject(
                ProjectPureStatus.EXTRA_VALUE_PAYLOAD, record_position, field_position
            )
        if value.boolean is not None:
            return _reject(
                ProjectPureStatus.EXTRA_VALUE_PAYLOAD, record_position, field_position
            )
        return None
    if value.tag is not declared.tag:
        return _reject(
            ProjectPureStatus.VALUE_TAG_MISMATCH, record_position, field_position
        )
    if value.tag in (ProjectPureTag.TEXT, ProjectPureTag.ENUMERATION):
        if value.text is None:
            return _reject(
                ProjectPureStatus.MISSING_VALUE_PAYLOAD, record_position, field_position
            )
        if value.integer is not None or value.boolean is not None:
            return _reject(
                ProjectPureStatus.EXTRA_VALUE_PAYLOAD, record_position, field_position
            )
        if (
            value.tag is ProjectPureTag.ENUMERATION
            and declared.vocabulary is not None
            and value.text not in declared.vocabulary
        ):
            return _reject(
                ProjectPureStatus.UNKNOWN_ENUMERATION, record_position, field_position
            )
        return None
    if value.tag is ProjectPureTag.INTEGER:
        if value.integer is None:
            return _reject(
                ProjectPureStatus.MISSING_VALUE_PAYLOAD, record_position, field_position
            )
        if value.text is not None or value.boolean is not None:
            return _reject(
                ProjectPureStatus.EXTRA_VALUE_PAYLOAD, record_position, field_position
            )
        if value.integer < 0:
            return _reject(
                ProjectPureStatus.NEGATIVE_INTEGER, record_position, field_position
            )
        if value.integer > PURE_MAX_INTEGER:
            return _reject(
                ProjectPureStatus.INTEGER_OUT_OF_RANGE, record_position, field_position
            )
        return None
    if value.boolean is None:
        return _reject(
            ProjectPureStatus.MISSING_VALUE_PAYLOAD, record_position, field_position
        )
    if value.text is not None or value.integer is not None:
        return _reject(
            ProjectPureStatus.EXTRA_VALUE_PAYLOAD, record_position, field_position
        )
    return None


def _value_of(record: ProjectPureRecord, key: str) -> ProjectPureValue:
    """Read one already validated value from one record by its declared key."""

    for supplied in record.fields:
        if supplied.key == key:
            return supplied.value
    raise ValueError("A validated record always carries its declared key.")


def _state_token(value: ProjectPureValue) -> str:
    """Classify one validated value for a declared cross-field state rule.

    An integer collapses to ``zero``, ``one``, or ``many`` because a declared
    combination distinguishes emptiness and repetition, never a specific
    magnitude. Repetition is a distinct token because an upstream carrier can
    treat a repeated identity differently from a unique one.
    """

    if value.tag is ProjectPureTag.ABSENT:
        return "absent"
    if value.tag is ProjectPureTag.INTEGER:
        if value.integer == 0:
            return "zero"
        return "one" if value.integer == 1 else "many"
    if value.tag is ProjectPureTag.BOOLEAN:
        return "true" if value.boolean else "false"
    return value.text or ""


def _is_pure_module_path(value: str) -> bool:
    """Return whether one text is a normalized project-relative module path.

    This mirrors ``ProjectModuleIdentity`` without consulting the host: the
    upstream predicate asks ``pathlib`` whether the path is absolute, and on
    every supported platform that is exactly a leading separator or a drive
    letter, both of which are decided here from the characters alone.
    """

    if not value.endswith(".pietto"):
        return False
    if "\x00" in value or "\\" in value or value.startswith("/"):
        return False
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _exact_token(value: ProjectPureValue) -> str:
    """Render one validated value losslessly for a sibling identity tuple.

    A state token collapses an integer to its magnitude class, which is right
    for a declared combination and wrong for an identity: two distinct
    positions must stay distinct. The tag prefix keeps the domains apart.
    """

    if value.tag is ProjectPureTag.ABSENT:
        return "n:"
    if value.tag is ProjectPureTag.INTEGER:
        return f"i:{value.integer}"
    if value.tag is ProjectPureTag.BOOLEAN:
        return f"b:{'true' if value.boolean else 'false'}"
    return f"{'e' if value.tag is ProjectPureTag.ENUMERATION else 's'}:{value.text}"


def _presence_token(value: ProjectPureValue) -> str:
    """Classify one validated value by presence alone."""

    return "absent" if value.tag is ProjectPureTag.ABSENT else "present"


def _sibling_is_terminal(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    parent_frame: _PureFrame | None,
) -> bool:
    """Return whether this record is the last declared sibling of its kind."""

    if parent_frame is None or specification.ordinal_key is None:
        return False
    declared = next(
        (
            count
            for count, child_kind in parent_frame.declared_counts
            if child_kind == specification.kind
        ),
        None,
    )
    if declared is None:
        return False
    return _integer_of(record, specification.ordinal_key) == declared - 1


def _identity_tokens(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
) -> tuple[str, ...]:
    """Render one record's identity, dropping the keys that only position it.

    A portable ordinal and the enclosing scope ordinals are positions, not
    identity, so two records that differ only there are the same fact twice.
    """

    positional = set(specification.parent_ordinal_keys)
    if specification.ordinal_key is not None:
        positional.add(specification.ordinal_key)
    return tuple(
        _exact_token(_value_of(record, declared.key))
        for declared in specification.keys
        if declared.key not in positional
    )


def _declared_vocabulary(specification: _PureKindSpec, key: str) -> tuple[str, ...]:
    """Return the declared enumeration order of one key of one record kind."""

    for declared in specification.keys:
        if declared.key == key and declared.vocabulary is not None:
            return declared.vocabulary
    raise ValueError("A declared order rule requires an enumeration key.")


def _collected_keys(kind: str) -> tuple[tuple[str, str], ...]:
    """Return the child kind and key pairs one scope kind must collect."""

    specification = PURE_RECORD_SCHEMA.get(kind)
    if specification is None:
        return ()
    collected: list[tuple[str, str]] = []
    for rule in specification.scope_rules:
        if rule.rule in (
            _PureScopeKind.GROUPED_SEQUENCES_EQUAL,
            _PureScopeKind.COLLECTED_SETS_EQUAL,
        ):
            collected.extend(rule.pairs)
        elif rule.rule is _PureScopeKind.SCOPE_REQUIRES_CHILD:
            collected.append((rule.child, rule.child_key))
    collected.extend(
        (rule.child, rule.child_key)
        for other in PURE_RECORD_SCHEMA.values()
        for rule in other.scope_rules
        if rule.rule is _PureScopeKind.UNCLE_COMBINATION and rule.scope == kind
    )
    return tuple(collected)


def _subset_keys(kind: str) -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Return the child kind and key tuples one scope kind must collect."""

    specification = PURE_RECORD_SCHEMA.get(kind)
    if specification is None:
        return ()
    return tuple(
        entry
        for rule in specification.scope_rules
        if rule.rule is _PureScopeKind.COLLECTED_SUBSET
        for entry in rule.subset
    )


def _grouped(collected: list[tuple[int, str]]) -> tuple[tuple[str, ...], ...]:
    """Group one collected child sequence by the scope that owned each item."""

    groups: list[tuple[int, list[str]]] = []
    for owner, value in collected:
        if not groups or groups[-1][0] != owner:
            groups.append((owner, []))
        groups[-1][1].append(value)
    return tuple(tuple(values) for _, values in groups)


def _close_grouped_sequences(frame: _PureFrame) -> ProjectPureOutcome | None:
    """Compare the grouped child sequences one closing scope collected."""

    specification = PURE_RECORD_SCHEMA.get(frame.kind)
    if specification is None:
        return None
    for rule in specification.scope_rules:
        if rule.rule is _PureScopeKind.GROUPED_SEQUENCES_EQUAL:
            grouped, expected = (
                _grouped(frame.collected.get(pair, [])) for pair in rule.pairs
            )
            if len(expected) != 1 or any(group != expected[0] for group in grouped):
                return _reject(
                    ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
                    frame.record_position,
                )
            continue
        if rule.rule is _PureScopeKind.COLLECTED_SETS_EQUAL:
            left, right = (
                {value for _, value in frame.collected.get(pair, [])}
                for pair in rule.pairs
            )
            if left != right:
                return _reject(
                    ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
                    frame.record_position,
                )
            continue
        if rule.rule is _PureScopeKind.COLLECTED_SUBSET:
            contained, container = rule.subset
            if not set(frame.grouped_tuples.get(contained, [])) <= set(
                frame.grouped_tuples.get(container, [])
            ):
                return _reject(
                    ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
                    frame.record_position,
                )
            continue
        if rule.rule is _PureScopeKind.SCOPE_REQUIRES_CHILD:
            if rule.when and frame.record is not None:
                selector, expected_token = rule.when
                supplied = _value_of(frame.record, selector)
                observed = (
                    _presence_token(supplied)
                    if selector in rule.presence
                    else _state_token(supplied)
                )
                if observed != expected_token:
                    continue
            values = frame.collected.get((rule.child, rule.child_key), [])
            if not any(value not in rule.excluded for _, value in values):
                return _reject(
                    ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
                    frame.record_position,
                )
            continue
    if frame.kind in _PURE_SUBTREE_KINDS and frame.parent_frame is not None:
        seen = frame.parent_frame.seen_children.setdefault(frame.kind, set())
        member = (*frame.identity, *(token for item in frame.subtree for token in item))
        if member in seen:
            return _reject(
                ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, frame.record_position
            )
        seen.add(member)
    for child_kind, buckets in frame.buckets.items():
        for members in buckets.values():
            counts = {count for _, count in members}
            indexes = sorted(index for index, _ in members)
            declared = counts.pop() if len(counts) == 1 else None
            if (
                declared is None
                or (declared != len(members) and declared != -1)
                or indexes != list(range(len(members)))
            ):
                return _reject(
                    ProjectPureStatus.INCONSISTENT_SCOPE_RELATION,
                    frame.record_position,
                )
        del child_kind
    return None


def _membership_required(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    stack: list[_PureFrame],
) -> tuple[tuple[str, str, ProjectPureValue, bool], ...]:
    """Resolve the values a closing scope must and must not see in its children."""

    required: list[tuple[str, str, ProjectPureValue, bool]] = []
    for rule in specification.scope_rules:
        if rule.rule not in (
            _PureScopeKind.SCOPE_CONTAINS_ANCESTOR,
            _PureScopeKind.SCOPE_EXCLUDES_ANCESTOR,
        ):
            continue
        if any(
            _state_token(_value_of(record, key)) != expected
            for key, expected in rule.when_all
        ):
            # The scope state this rule is conditioned on does not hold, so the
            # scope requires nothing of its children.
            continue
        ancestor = _ancestor_frame(stack, rule.scope)
        if ancestor is None or ancestor.record is None:
            continue
        key, ancestor_key = rule.pairs[0]
        required.append(
            (
                rule.child,
                key,
                _value_of(ancestor.record, ancestor_key),
                rule.rule is _PureScopeKind.SCOPE_CONTAINS_ANCESTOR,
            )
        )
    return tuple(required)


def _identical_values(left: ProjectPureValue, right: ProjectPureValue) -> bool:
    """Return whether two validated values carry the same tag and payload."""

    return (
        left.tag is right.tag
        and left.text == right.text
        and left.integer == right.integer
        and left.boolean is right.boolean
    )


def _ancestor_frame(stack: list[_PureFrame], kind: str) -> _PureFrame | None:
    """Return the innermost open frame of one declared kind."""

    for frame in reversed(stack):
        if frame.kind == kind:
            return frame
    return None


def _scope_rule_applies(
    rule: _PureScopeRule,
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    parent_frame: _PureFrame,
) -> bool:
    """Return whether one declared scope rule governs this exact record."""

    if rule.when:
        selector, expected = rule.when
        if _state_token(_value_of(record, selector)) != expected:
            return False
    if rule.at == "first":
        return (
            specification.ordinal_key is not None
            and _integer_of(record, specification.ordinal_key) == 0
        )
    if rule.at == "last":
        return _sibling_is_terminal(record, specification, parent_frame)
    return True


def _validate_scope_rules(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    position: int,
    stack: list[_PureFrame],
) -> ProjectPureOutcome | None:
    """Validate every declared relation between one record and its scope.

    Each rule mirrors an invariant an upstream carrier already enforces over a
    retained collection: a child that must repeat its owner's identity, a chain
    whose endpoints and adjacent links must agree, or a collection that forbids
    a duplicate member.
    """

    parent_frame = stack[-1]
    for rule in specification.scope_rules:
        if not _scope_rule_applies(rule, record, specification, parent_frame):
            continue
        if rule.rule is _PureScopeKind.ANCESTOR_EQUAL:
            ancestor = _ancestor_frame(stack, rule.scope)
            if ancestor is None or ancestor.record is None:
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            for key, ancestor_key in rule.pairs:
                if not _identical_values(
                    _value_of(record, key), _value_of(ancestor.record, ancestor_key)
                ):
                    return _reject(
                        ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position
                    )
            continue
        if rule.rule is _PureScopeKind.ANCESTOR_COMBINATION:
            ancestor = _ancestor_frame(stack, rule.scope)
            if ancestor is None or ancestor.record is None:
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            observed: list[str] = []
            for key, ancestor_key in rule.pairs:
                observed.append(_state_token(_value_of(record, key)))
                supplied = _value_of(ancestor.record, ancestor_key)
                observed.append(
                    _presence_token(supplied)
                    if ancestor_key in rule.presence
                    else _state_token(supplied)
                )
            if not any(
                all(
                    cell == "*" or cell == seen
                    for cell, seen in zip(row, observed, strict=True)
                )
                for row in rule.admitted
            ):
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            continue
        if rule.rule is _PureScopeKind.UNCLE_COMBINATION:
            ancestor = _ancestor_frame(stack, rule.scope)
            if ancestor is None:
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            supplied = ancestor.collected.get((rule.child, rule.child_key), [])
            if not supplied:
                # The sibling record this rule reads has not been declared yet,
                # so the scope has nothing to compare and the record stands.
                continue
            uncle_observed = (
                *(_state_token(_value_of(record, key)) for key, _ in rule.pairs),
                supplied[-1][1],
            )
            if not any(
                all(
                    cell == "*" or cell == seen
                    for cell, seen in zip(row, uncle_observed, strict=True)
                )
                for row in rule.admitted
            ):
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            continue
        if rule.rule is _PureScopeKind.PREVIOUS_SIBLING_EQUAL:
            previous = parent_frame.previous_child.get(specification.kind)
            if previous is None:
                continue
            for key, previous_key in rule.pairs:
                if not _identical_values(
                    _value_of(record, key), _value_of(previous, previous_key)
                ):
                    return _reject(
                        ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position
                    )
            continue
        if rule.rule is _PureScopeKind.PREVIOUS_SIBLING_INCREASING:
            previous = parent_frame.previous_child.get(specification.kind)
            if previous is None:
                continue
            seen = tuple(_integer_of(record, key) for key, _ in rule.pairs)
            before = tuple(_integer_of(previous, key) for _, key in rule.pairs)
            if seen <= before:
                return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
            continue
        if rule.rule is _PureScopeKind.PREVIOUS_SIBLING_NON_DECREASING:
            previous = parent_frame.previous_child.get(specification.kind)
            if previous is None:
                continue
            if rule.when:
                selector, expected_token = rule.when
                if _state_token(_value_of(previous, selector)) != expected_token:
                    # The preceding sibling belongs to another declared group,
                    # so this record opens that group rather than continuing one.
                    continue
            for key, previous_key in rule.pairs:
                vocabulary = rule.order or _declared_vocabulary(specification, key)
                if vocabulary.index(_text_of(record, key)) < vocabulary.index(
                    _text_of(previous, previous_key)
                ):
                    return _reject(
                        ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position
                    )
            continue
        if rule.rule is not _PureScopeKind.DISTINCT_SIBLINGS:
            # Every remaining shape is settled when the owning scope closes.
            continue
        seen = parent_frame.seen_children.setdefault(specification.kind, set())
        member = tuple(_exact_token(_value_of(record, key)) for key in rule.distinct)
        if member in seen:
            return _reject(ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, position)
        seen.add(member)
    return None


def _validate_state_rules(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    position: int,
    parent_frame: _PureFrame | None = None,
) -> ProjectPureOutcome | None:
    """Validate every declared cross-field state rule of one record.

    Each rule mirrors an invariant an upstream carrier already enforces
    atomically, so no admitted projection can violate one. Validating the
    enumeration values of a record independently would accept an impossible
    combination that the authority forbids.
    """

    for rule in specification.state_rules:
        if rule.rule is _PureStateKind.COMBINATION:
            observed = tuple(
                _presence_token(_value_of(record, key))
                if key in rule.presence_keys
                else _state_token(_value_of(record, key))
                for key in rule.keys
            )
            if not any(
                all(
                    cell == "*" or cell == seen
                    for cell, seen in zip(row, observed, strict=True)
                )
                for row in rule.admitted
            ):
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.PRESENCE_GROUP:
            present = {
                _value_of(record, key).tag is not ProjectPureTag.ABSENT
                for key in rule.keys
            }
            if len(present) != 1:
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.POSITIVE_REQUIRES_PRESENT:
            counted, required = rule.keys
            if _integer_of(record, counted) and (
                _value_of(record, required).tag is ProjectPureTag.ABSENT
            ):
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.POSITIVE:
            (counted,) = rule.keys
            if _integer_of(record, counted) < 1:
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.EQUAL_IF_PRESENT:
            if rule.when:
                selector, expected = rule.when
                if _state_token(_value_of(record, selector)) != expected:
                    continue
            left, right = (_value_of(record, key) for key in rule.keys)
            if ProjectPureTag.ABSENT in (left.tag, right.tag):
                continue
            if not _identical_values(left, right):
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.NON_EMPTY_IF_PRESENT:
            for key in rule.keys:
                supplied = _value_of(record, key)
                if supplied.tag is not ProjectPureTag.ABSENT and not supplied.text:
                    return _reject(
                        ProjectPureStatus.INCONSISTENT_RECORD_STATE, position
                    )
            continue
        if rule.rule is _PureStateKind.MULTI_REQUIRES_TRUE:
            counted, flag = rule.keys
            if _integer_of(record, counted) > 1 and (
                _value_of(record, flag).boolean is not True
            ):
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.TERMINAL_COMBINATION:
            (terminal_key,) = rule.keys
            observed = _state_token(_value_of(record, terminal_key))
            terminal, interior = rule.terminal
            expected = (
                terminal
                if _sibling_is_terminal(record, specification, parent_frame)
                else interior
            )
            if observed != expected:
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.STRICTLY_LESS:
            smaller, larger = rule.keys
            if _integer_of(record, smaller) >= _integer_of(record, larger):
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.EQUALITY_COMBINATION:
            selector, left_key, right_key = rule.keys
            left = _value_of(record, left_key)
            right = _value_of(record, right_key)
            observed = (
                _state_token(_value_of(record, selector)),
                "equal" if _identical_values(left, right) else "distinct",
            )
            if observed not in rule.admitted:
                return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
            continue
        if rule.rule is _PureStateKind.MODULE_PATH:
            for key in rule.keys:
                supplied = _value_of(record, key)
                if supplied.tag is ProjectPureTag.ABSENT:
                    continue
                if not _is_pure_module_path(supplied.text or ""):
                    return _reject(
                        ProjectPureStatus.INCONSISTENT_RECORD_STATE, position
                    )
            continue
        if rule.rule is not _PureStateKind.LOWERCASE_HEX:
            continue
        (digest_key,) = rule.keys
        text = _value_of(record, digest_key).text or ""
        if len(text) != rule.text_length or any(
            character not in _PURE_HEX_ALPHABET for character in text
        ):
            return _reject(ProjectPureStatus.INCONSISTENT_RECORD_STATE, position)
    return None


def _text_of(record: ProjectPureRecord, key: str) -> str:
    """Read one already validated text payload from one record."""

    for supplied in record.fields:
        if supplied.key == key:
            payload = supplied.value.text
            if payload is None:
                raise ValueError("A validated text payload cannot be absent.")
            return payload
    raise ValueError("A validated record always carries its declared key.")


def _integer_of(record: ProjectPureRecord, key: str) -> int:
    """Read one already validated integer payload from one record."""

    for supplied in record.fields:
        if supplied.key == key:
            payload = supplied.value.integer
            if payload is None:
                raise ValueError("A validated integer payload cannot be absent.")
            return payload
    raise ValueError("A validated record always carries its declared key.")


def _declared_counts(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
) -> tuple[tuple[int, str], ...]:
    """Read the declared child counts of one already validated record."""

    return tuple(
        (_integer_of(record, count_key), child_kind)
        for count_key, child_kind in specification.counts
    )


def _close_frame(frame: _PureFrame) -> ProjectPureOutcome | None:
    """Verify one closing scope's required records, counts, and memberships."""

    for child, child_key, _, expected in frame.membership_required:
        if ((child, child_key) in frame.membership_seen) is not expected:
            return _reject(
                ProjectPureStatus.INCONSISTENT_SCOPE_RELATION, frame.record_position
            )
    if frame.kind == "module":
        for required in _PURE_REQUIRED_MODULE_RECORDS:
            if frame.child_counts.get(required, 0) == 0:
                return _reject(
                    ProjectPureStatus.MISSING_REQUIRED_RECORD, frame.record_position
                )
    for declared, child_kind in frame.declared_counts:
        if frame.child_counts.get(child_kind, 0) != declared:
            return _reject(
                ProjectPureStatus.CHILD_COUNT_MISMATCH, frame.record_position
            )
    # A scope that is structurally incomplete reports that first, so a declared
    # relation between two of its child collections is only compared once both
    # collections are known to be present and complete.
    return _close_grouped_sequences(frame)


def evaluate_pure_document(document: ProjectPureDocument) -> ProjectPureOutcome:
    """Evaluate one portable document into canonical bytes or one rejection.

    The procedure is total over well-typed documents: it always returns an
    outcome and never raises.

    Violations are reported strictly in document order. No rule about a later
    record may pre-empt a violation in an earlier one, so every scope a record
    ends is settled against its declared child counts before anything about that
    record is reported. Inside one record the declared field contract is checked
    before every structural rule, so an independent implementation that walks
    the stream once reports the exact same status and coordinates. A record of
    an unknown kind, a record that declares no parent scope, and a record whose
    declared parent scope is not open all end no scope, so each is reported
    where it stands. A coordinate is always a position that exists in the
    supplied stream; the absence of a required record carries no coordinate.
    """

    records = document.records
    if not records:
        return _reject(ProjectPureStatus.EMPTY_DOCUMENT)

    header_rejection = _validate_header(records)
    if header_rejection is not None:
        return header_rejection

    structure_rejection = _validate_structure(records)
    if structure_rejection is not None:
        return structure_rejection

    return ProjectPureOutcome(
        status=ProjectPureStatus.OK,
        canonical_bytes=_encode_document(document),
    )


def _validate_header(
    records: tuple[ProjectPureRecord, ...],
) -> ProjectPureOutcome | None:
    """Validate record zero and prove the mandatory ``owner`` record exists.

    Only record zero is decided here. Record one is validated by the ordered
    walk, so a malformed ``owner`` never loses its place in document order.
    """

    if records[0].kind != "inspection":
        return _reject(ProjectPureStatus.MISSING_HEADER_RECORD, 0)
    rejection = _validate_fields(records[0], PURE_RECORD_SCHEMA["inspection"], 0)
    if rejection is not None:
        return rejection
    if records[0].fields[0].value.text != PURE_DOCUMENT_FORMAT_MARKER:
        return _reject(ProjectPureStatus.UNKNOWN_FORMAT_MARKER, 0, 0)
    if len(records) < 2:
        # The record is absent, so there is no position in the stream to name.
        return _reject(ProjectPureStatus.MISSING_HEADER_RECORD)
    if records[1].kind != "owner":
        return _reject(ProjectPureStatus.MISSING_HEADER_RECORD, 1)
    return None


def _validate_structure(
    records: tuple[ProjectPureRecord, ...],
) -> ProjectPureOutcome | None:
    """Walk the document once and validate every declared structural rule.

    The mandatory ``inspection`` header opens the document scope, so the
    declared module count, the module ordinal density, and every nested count
    are all verified by the same scope machinery rather than by a special case.
    """

    declared_modules = _integer_of(records[0], "modules")
    stack: list[_PureFrame] = [
        _PureFrame(
            kind="inspection",
            ordinal=None,
            record_position=0,
            declared_counts=_declared_counts(
                records[0], PURE_RECORD_SCHEMA["inspection"]
            ),
            record=records[0],
        )
    ]
    for position in range(1, len(records)):
        record = records[position]
        specification = PURE_RECORD_SCHEMA.get(record.kind)
        if specification is None:
            # An unknown kind has no declared field contract to check first.
            return _reject(ProjectPureStatus.UNKNOWN_RECORD_KIND, position)
        parent = specification.parent
        settles = parent is not None and any(frame.kind == parent for frame in stack)
        if settles:
            # Every frame this record ends is settled before anything about the
            # record itself is reported, so a successor never pre-empts an
            # earlier scope that already failed its declared child count.
            while stack[-1].kind != parent:
                rejection = _close_frame(stack.pop())
                if rejection is not None:
                    return rejection
        rejection = _validate_fields(record, specification, position)
        if rejection is not None:
            return rejection
        if not settles:
            # A record that declares no parent scope, or whose declared parent
            # is not open, ends no frame, so it is reported where it stands.
            if record.kind in _PURE_HEADER_KINDS:
                return _reject(ProjectPureStatus.UNEXPECTED_HEADER_RECORD, position)
            return _reject(ProjectPureStatus.ORPHAN_RECORD, position)
        if position > 1:
            if record.kind in _PURE_HEADER_KINDS:
                return _reject(ProjectPureStatus.UNEXPECTED_HEADER_RECORD, position)
            if declared_modules == 0:
                return _reject(
                    ProjectPureStatus.TRAILING_RECORD_AFTER_DOCUMENT, position
                )

        parent_frame = stack[-1]
        rejection = _validate_state_rules(record, specification, position, parent_frame)
        if rejection is not None:
            return rejection
        rejection = _validate_scope(record, specification, stack, position)
        if rejection is not None:
            return rejection
        rejection = _validate_order_and_ordinal(
            record, specification, parent_frame, position
        )
        if rejection is not None:
            return rejection
        rejection = _validate_scope_rules(record, specification, position, stack)
        if rejection is not None:
            return rejection

        parent_frame.child_counts[record.kind] = (
            parent_frame.child_counts.get(record.kind, 0) + 1
        )
        parent_frame.previous_child[record.kind] = record
        identity = _identity_tokens(record, specification)
        for frame in stack:
            if frame.kind in _PURE_SUBTREE_KINDS:
                frame.subtree.append((record.kind, *identity))
        for rule in specification.scope_rules:
            if rule.rule is not _PureScopeKind.SIBLING_BUCKETS_COMPLETE:
                continue
            bucket = tuple(_text_of(record, key) for key in rule.distinct)
            index_key, count_key = rule.pairs[0]
            index = _integer_of(record, index_key)
            count = -1 if not count_key else _integer_of(record, count_key)
            parent_frame.buckets.setdefault(record.kind, {}).setdefault(
                bucket, []
            ).append((index, count))
        for frame in stack:
            for entry in _subset_keys(frame.kind):
                if entry[0] != record.kind:
                    continue
                frame.grouped_tuples.setdefault(entry, []).append(
                    tuple(_exact_token(_value_of(record, key)) for key in entry[1])
                )
            for collected_kind, collected_key in _collected_keys(frame.kind):
                if collected_kind != record.kind:
                    continue
                frame.collected.setdefault((collected_kind, collected_key), []).append(
                    (parent_frame.record_position, _text_of(record, collected_key))
                )
        for frame in stack:
            for child, child_key, required, _expected in frame.membership_required:
                if child == record.kind and _identical_values(
                    _value_of(record, child_key), required
                ):
                    frame.membership_seen.add((child, child_key))
        if specification.is_scope:
            stack.append(
                _PureFrame(
                    kind=record.kind,
                    ordinal=(
                        None
                        if specification.ordinal_key is None
                        else _integer_of(record, specification.ordinal_key)
                    ),
                    record_position=position,
                    declared_counts=_declared_counts(record, specification),
                    record=record,
                    membership_required=_membership_required(
                        record, specification, stack
                    ),
                    identity=identity,
                    parent_frame=parent_frame,
                )
            )

    while stack:
        rejection = _close_frame(stack.pop())
        if rejection is not None:
            return rejection
    return None


def _validate_scope(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    stack: list[_PureFrame],
    position: int,
) -> ProjectPureOutcome | None:
    """Require every parent ordinal in the record to equal its open scope."""

    open_ordinals = tuple(frame.ordinal for frame in stack if frame.ordinal is not None)
    if len(open_ordinals) != len(specification.parent_ordinal_keys):
        return _reject(ProjectPureStatus.SCOPE_ORDINAL_MISMATCH, position)
    for expected, key in zip(
        open_ordinals, specification.parent_ordinal_keys, strict=True
    ):
        if _integer_of(record, key) != expected:
            return _reject(ProjectPureStatus.SCOPE_ORDINAL_MISMATCH, position)
    return None


def _validate_order_and_ordinal(
    record: ProjectPureRecord,
    specification: _PureKindSpec,
    parent_frame: _PureFrame,
    position: int,
) -> ProjectPureOutcome | None:
    """Validate sibling-kind order, singleton uniqueness, and ordinal rules."""

    if specification.child_order < parent_frame.last_child_order:
        return _reject(
            ProjectPureStatus.SECTION_ORDER_VIOLATION
            if parent_frame.kind == "module"
            else ProjectPureStatus.CHILD_ORDER_VIOLATION,
            position,
        )
    parent_frame.last_child_order = specification.child_order
    if specification.singleton:
        if parent_frame.child_counts.get(record.kind, 0) != 0:
            return _reject(ProjectPureStatus.DUPLICATE_SINGLETON_RECORD, position)
        return None
    if specification.ordinal_key is None:
        return None
    # Every ordinal in the canonical projection is dense. The enumeration-indexed
    # kinds are dense by construction, and ``declaration`` is dense because a
    # module catalog validates ``declaration_position == position`` over its
    # complete source-ordered occurrence tuple and the inspection authority
    # requires exactly that complete ordered projection.
    if _integer_of(record, specification.ordinal_key) != parent_frame.child_counts.get(
        record.kind, 0
    ):
        return _reject(ProjectPureStatus.ORDINAL_SEQUENCE_VIOLATION, position)
    return None


def _encode_document(document: ProjectPureDocument) -> bytes:
    """Render one accepted document as the exact canonical private payload."""

    lines: list[str] = []
    for record in document.records:
        rendered = "".join(
            f"\t{supplied.key}={encode_pure_value(supplied.value)}"
            for supplied in record.fields
        )
        lines.append(record.kind + rendered)
    return ("\n".join(lines) + "\n").encode("utf-8")
