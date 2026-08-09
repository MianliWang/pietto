"""Deterministic private differential harness for the Rust-ready pure boundary.

The harness loads the frozen private vector corpus, validates its schema, runs
the portable pure boundary, and compares the exact canonical bytes or the exact
normalized rejection with its structural coordinates.

It is a test asset, not a product. It performs no network access, no version
control access, and no repository-file mutation, and it never regenerates an
expected value during normal validation. Expected-value changes go through
``propose_expected_updates``, which returns a proposed report and writes
nothing.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto._project.module_pure_boundary import (
    ProjectPureDocument,
    ProjectPureOutcome,
    ProjectPureStatus,
    evaluate_pure_document,
)

DIFFERENTIAL_VECTOR_FORMAT = "pietto.differential-vectors.v1"


class DifferentialVectorError(Exception):
    """Raised when the vector corpus itself is malformed or ambiguous."""


class DifferentialClassification(StrEnum):
    """Which portable behaviour one vector exercises.

    Python authority-root admission is deliberately absent. It is decided by
    object identity, which must never be encoded as cross-language data, so the
    end-to-end suite exercises that layer instead of a portable vector. A
    declared member no vector could ever carry would make the schema and the
    contract disagree.
    """

    PORTABLE_EVALUATION = "portable_evaluation"
    PORTABLE_REJECTION = "portable_rejection"


class DifferentialPurpose(StrEnum):
    """The frozen property dimension one vector exercises."""

    EMPTY_PROJECT = "empty_project"
    SINGLE_MODULE = "single_module"
    SEVERAL_MODULES = "several_modules"
    DECLARATION_ORDER_AND_MULTIPLICITY = "declaration_order_and_multiplicity"
    SAME_SPELLING_DISTINCT_MODULES = "same_spelling_distinct_modules"
    SAME_SPELLING_DISTINCT_NAMESPACES = "same_spelling_distinct_namespaces"
    ALIAS_DISTINCT_FROM_TARGET = "alias_distinct_from_target"
    TWO_ALIASES_ONE_TARGET = "two_aliases_one_target"
    EXPLICIT_REEXPORT = "explicit_reexport"
    AVAILABILITY_STATES = "availability_states"
    MODULE_CYCLE_AND_BLOCKED_READINESS = "module_cycle_and_blocked_readiness"
    DUPLICATE_NOMINAL_IDENTITY_BUCKET = "duplicate_nominal_identity_bucket"
    EQUAL_DIGEST_DISTINCT_MODULES = "equal_digest_distinct_modules"
    DIRECT_AND_RENAMED_LINEAGE = "direct_and_renamed_lineage"
    PRESERVED_SEMANTIC_FACTS = "preserved_semantic_facts"
    NULLABILITY_AND_RESULT_ROLE = "nullability_and_result_role"
    SURROGATE_TEXT = "surrogate_text"
    CONTROL_CHARACTER_TEXT = "control_character_text"
    NON_ASCII_TEXT = "non_ascii_text"
    ABSENT_VERSUS_EMPTY_TEXT = "absent_versus_empty_text"
    BOUNDARY_CARDINALITIES = "boundary_cardinalities"
    LARGE_REPEATED_BUCKET = "large_repeated_bucket"
    ISSUE_FAMILIES = "issue_families"
    TYPE_ALIAS_CHAIN = "type_alias_chain"
    ISSUE_BUCKETS = "issue_buckets"
    DEPENDENCY_TARGET_VARIANTS = "dependency_target_variants"
    BOOLEAN_VALUES = "boolean_values"
    UNRESOLVED_IMPORT = "unresolved_import"
    RESOLUTION_SECTIONS = "resolution_sections"
    EMPTY_DOCUMENT = "empty_document"
    MISSING_HEADER = "missing_header"
    ABSENT_HEADER_RECORD = "absent_header_record"
    UNEXPECTED_HEADER = "unexpected_header"
    TRAILING_RECORD = "trailing_record"
    WRONG_FORMAT_MARKER = "wrong_format_marker"
    UNKNOWN_RECORD_KIND = "unknown_record_kind"
    UNKNOWN_KEY = "unknown_key"
    MISSING_KEY = "missing_key"
    EXTRA_KEY = "extra_key"
    WRONG_KEY_ORDER = "wrong_key_order"
    WRONG_VALUE_TAG = "wrong_value_tag"
    ABSENT_NOT_ALLOWED = "absent_not_allowed"
    MISSING_PAYLOAD = "missing_payload"
    EXTRA_PAYLOAD = "extra_payload"
    NEGATIVE_INTEGER = "negative_integer"
    UNKNOWN_ENUMERATION = "unknown_enumeration"
    ORPHAN_RECORD = "orphan_record"
    WRONG_PARENT_ORDINAL = "wrong_parent_ordinal"
    REORDERED_SECTIONS = "reordered_sections"
    REORDERED_SIBLING_KINDS = "reordered_sibling_kinds"
    DUPLICATED_RECORD = "duplicated_record"
    MISSING_RECORD = "missing_record"
    NON_DENSE_ORDINAL = "non_dense_ordinal"
    NON_DENSE_DECLARATION_ORDINAL = "non_dense_declaration_ordinal"
    CHILD_COUNT_TOO_LARGE = "child_count_too_large"
    MISSING_REQUIRED_SINGLETON = "missing_required_singleton"
    DUPLICATE_SINGLETON = "duplicate_singleton"
    MODULE_COUNT_MISMATCH = "module_count_mismatch"
    IMPOSSIBLE_STATE_COMBINATION = "impossible_state_combination"
    STALE_FORMAT_MARKER = "stale_format_marker"
    INCONSISTENT_READINESS_STATE = "inconsistent_readiness_state"
    INTEGER_OUT_OF_RANGE = "integer_out_of_range"
    PARTIAL_PRESENCE_GROUP = "partial_presence_group"
    EXCLUSIVE_TARGET_GROUPS = "exclusive_target_groups"
    DEPENDENCY_WITHOUT_A_TARGET = "dependency_without_a_target"
    DEPENDENCY_KIND_TARGET_MISMATCH = "dependency_kind_target_mismatch"
    CANONICAL_KIND_TARGET_MISMATCH = "canonical_kind_target_mismatch"
    ISSUE_STATUS_OUTSIDE_ITS_FAMILY = "issue_status_outside_its_family"
    NON_CONCRETE_LINEAGE_WITH_FIELDS = "non_concrete_lineage_with_fields"
    IMPORTED_ORIGIN_WITHOUT_HOPS = "imported_origin_without_hops"
    LINEAGE_FIELD_WITHOUT_PATHS = "lineage_field_without_paths"
    DIGEST_NOT_LOWERCASE_HEX = "digest_not_lowercase_hex"
    NAMED_PROJECT_ROOT_OWNER = "named_project_root_owner"
    AVAILABILITY_RELATION_STATE_MISMATCH = "availability_relation_state_mismatch"
    INELIGIBLE_NAMESPACE_KIND_PAIR = "ineligible_namespace_kind_pair"
    MULTI_MEMBER_ACYCLIC_COMPONENT = "multi_member_acyclic_component"
    UNTERMINATED_ORIGIN_HOP_CHAIN = "unterminated_origin_hop_chain"
    CANONICAL_KIND_NAME_MISMATCH = "canonical_kind_name_mismatch"
    ALIAS_IDENTITY_NOT_A_TYPE_ALIAS = "alias_identity_not_a_type_alias"
    EMPTY_SELECT_OUTPUT_NAME = "empty_select_output_name"
    RESOLVED_IMPORT_KIND_MISMATCH = "resolved_import_kind_mismatch"
    CANONICAL_TARGET_NAME_MISMATCH = "canonical_target_name_mismatch"
    NON_RELATION_RELATION_AVAILABILITY = "non_relation_relation_availability"
    AMBIGUOUS_WITHOUT_REPETITION = "ambiguous_without_repetition"
    HOP_ENDPOINTS_DISAGREE = "hop_endpoints_disagree"
    CLAUSE_ROLE_OUTSIDE_SUBSET = "clause_role_outside_subset"
    WINDOW_OUTPUT_STATUS_OUTSIDE_SUBSET = "window_output_status_outside_subset"
    POSITIVE_REQUIRES_PRESENT = "positive_requires_present"
    OCCURRENCE_INDEX_OUTSIDE_BUCKET = "occurrence_index_outside_bucket"


@dataclass(frozen=True, slots=True, kw_only=True)
class DifferentialVector:
    """One frozen private differential vector.

    A vector carries a complete portable input plus its stored expected result.
    It contains no absolute path, temporary directory, memory address, object
    identifier, host metadata, timestamp, or version-control state.
    """

    vector_format: str
    vector_id: str
    purpose: DifferentialPurpose
    classification: DifferentialClassification
    document: ProjectPureDocument
    expected_status: ProjectPureStatus
    expected_bytes: bytes | None = None
    expected_record_position: int | None = None
    expected_field_position: int | None = None


@dataclass(frozen=True, slots=True, kw_only=True)
class DifferentialResult:
    """The comparison outcome of one vector."""

    vector_id: str
    matched: bool
    expected_status: ProjectPureStatus
    observed_status: ProjectPureStatus
    detail: str = ""


@dataclass(frozen=True, slots=True, kw_only=True)
class DifferentialReport:
    """The complete deterministic result of one corpus run."""

    total: int
    matched: int
    results: tuple[DifferentialResult, ...]

    @property
    def failed(self) -> tuple[DifferentialResult, ...]:
        """Return every vector whose observed result differed."""

        return tuple(result for result in self.results if not result.matched)

    def summary(self) -> str:
        """Return one concise machine-readable summary line."""

        return (
            f"vector_format={DIFFERENTIAL_VECTOR_FORMAT} "
            f"vectors={self.total} matched={self.matched} "
            f"failed={len(self.failed)}"
        )


_VECTOR_IDENTIFIER_CHARACTERS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789_")

# A rejection names the record it failed on, except where the violation is the
# absence of a record and there is no position in the stream to name.
_COORDINATE_FREE_STATUSES = frozenset(
    {
        ProjectPureStatus.EMPTY_DOCUMENT,
        ProjectPureStatus.MISSING_HEADER_RECORD,
    }
)


def validate_vector(vector: DifferentialVector) -> tuple[str, ...]:
    """Return every schema violation of one vector, empty when it is exact."""

    violations: list[str] = []
    if type(vector) is not DifferentialVector:
        return ("vector is not an exact differential vector",)
    if vector.vector_format != DIFFERENTIAL_VECTOR_FORMAT:
        violations.append("vector format marker is not the frozen marker")
    if type(vector.vector_id) is not str:
        violations.append("vector identifier is not text")
    elif not vector.vector_id:
        violations.append("vector identifier is empty")
    elif set(vector.vector_id) - _VECTOR_IDENTIFIER_CHARACTERS:
        violations.append("vector identifier is not lowercase ascii")
    if type(vector.purpose) is not DifferentialPurpose:
        violations.append("vector purpose is not an exact purpose")
    if type(vector.classification) is not DifferentialClassification:
        violations.append("vector classification is not an exact classification")
    if type(vector.document) is not ProjectPureDocument:
        violations.append("vector document is not an exact portable document")
    if type(vector.expected_status) is not ProjectPureStatus:
        violations.append("vector expected status is not an exact status")
        return tuple(violations)
    accepted = vector.expected_status is ProjectPureStatus.OK
    if accepted:
        if vector.classification is not DifferentialClassification.PORTABLE_EVALUATION:
            violations.append("an accepted vector must be a portable evaluation")
        if vector.expected_bytes is None:
            violations.append("an accepted vector must store its expected payload")
        elif type(vector.expected_bytes) is not bytes:
            violations.append("an accepted vector payload must be bytes")
        elif not vector.expected_bytes.endswith(b"\n"):
            violations.append("an accepted vector payload must end with one newline")
        if vector.expected_record_position is not None:
            violations.append("an accepted vector carries no record coordinate")
        if vector.expected_field_position is not None:
            violations.append("an accepted vector carries no field coordinate")
        return tuple(violations)
    if vector.classification is not DifferentialClassification.PORTABLE_REJECTION:
        violations.append("a rejected vector must be a portable rejection")
    if vector.expected_bytes is not None:
        violations.append("a rejected vector stores no payload")
    if vector.expected_field_position is not None and (
        vector.expected_record_position is None
    ):
        violations.append("a field coordinate requires its record coordinate")
    if (
        vector.expected_record_position is None
        and vector.expected_status not in _COORDINATE_FREE_STATUSES
    ):
        violations.append("this rejection status requires a record coordinate")
    for coordinate in (
        vector.expected_record_position,
        vector.expected_field_position,
    ):
        if coordinate is not None and (type(coordinate) is not int or coordinate < 0):
            violations.append("a coordinate must be a non-negative integer")
    return tuple(violations)


def validate_corpus(vectors: tuple[DifferentialVector, ...]) -> None:
    """Fail closed on a malformed vector or a duplicate vector identifier."""

    if type(vectors) is not tuple:
        raise DifferentialVectorError("the vector corpus must be a tuple")
    if not vectors:
        raise DifferentialVectorError("the vector corpus must not be empty")
    seen: dict[str, int] = {}
    for position, vector in enumerate(vectors):
        violations = validate_vector(vector)
        if violations:
            raise DifferentialVectorError(
                f"vector at position {position} is malformed: {'; '.join(violations)}"
            )
        if vector.vector_id in seen:
            raise DifferentialVectorError(
                f"duplicate vector identifier at position {position}"
            )
        seen[vector.vector_id] = position


def _compare(
    vector: DifferentialVector,
    outcome: ProjectPureOutcome,
) -> DifferentialResult:
    """Compare one observed outcome with one vector's stored expectation."""

    if outcome.status is not vector.expected_status:
        return DifferentialResult(
            vector_id=vector.vector_id,
            matched=False,
            expected_status=vector.expected_status,
            observed_status=outcome.status,
            detail="status",
        )
    if vector.expected_status is ProjectPureStatus.OK:
        if outcome.canonical_bytes != vector.expected_bytes:
            return DifferentialResult(
                vector_id=vector.vector_id,
                matched=False,
                expected_status=vector.expected_status,
                observed_status=outcome.status,
                detail="canonical_bytes",
            )
        return DifferentialResult(
            vector_id=vector.vector_id,
            matched=True,
            expected_status=vector.expected_status,
            observed_status=outcome.status,
        )
    if outcome.record_position != vector.expected_record_position:
        return DifferentialResult(
            vector_id=vector.vector_id,
            matched=False,
            expected_status=vector.expected_status,
            observed_status=outcome.status,
            detail="record_position",
        )
    if outcome.field_position != vector.expected_field_position:
        return DifferentialResult(
            vector_id=vector.vector_id,
            matched=False,
            expected_status=vector.expected_status,
            observed_status=outcome.status,
            detail="field_position",
        )
    return DifferentialResult(
        vector_id=vector.vector_id,
        matched=True,
        expected_status=vector.expected_status,
        observed_status=outcome.status,
    )


def run_corpus(vectors: tuple[DifferentialVector, ...]) -> DifferentialReport:
    """Validate the corpus, run every vector, and report deterministic results.

    Nothing here writes a file or regenerates an expectation. A stored expected
    value that disagrees with the boundary is reported as a failure.
    """

    validate_corpus(vectors)
    results = tuple(
        _compare(vector, evaluate_pure_document(vector.document)) for vector in vectors
    )
    return DifferentialReport(
        total=len(results),
        matched=sum(1 for result in results if result.matched),
        results=results,
    )


def propose_expected_updates(
    vectors: tuple[DifferentialVector, ...],
) -> tuple[str, ...]:
    """Return a reviewed proposal for every disagreeing accepted expectation.

    This is the only authoring path. It returns proposed literal lines for a
    human to review and apply by hand; it writes nothing and mutates nothing, so
    an expected value can never be silently regenerated.
    """

    validate_corpus(vectors)
    proposals: list[str] = []
    for vector in vectors:
        outcome = evaluate_pure_document(vector.document)
        if outcome.status is not ProjectPureStatus.OK:
            disagrees = (
                outcome.status is not vector.expected_status
                or outcome.record_position != vector.expected_record_position
                or outcome.field_position != vector.expected_field_position
            )
            if disagrees:
                proposals.append(
                    f'    "{vector.vector_id}": rejected with '
                    f"{outcome.status.value} at record "
                    f"{outcome.record_position} field {outcome.field_position},"
                )
            continue
        if outcome.canonical_bytes == vector.expected_bytes:
            continue
        payload = outcome.canonical_bytes
        if payload is None:  # pragma: no cover - an accepted outcome always has one
            continue
        proposals.append(f'    "{vector.vector_id}": {payload!r},')
    return tuple(proposals)
