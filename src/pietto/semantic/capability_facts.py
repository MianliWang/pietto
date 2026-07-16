"""Private descriptive capability fact carriers."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__: tuple[str, ...] = ()


class CapabilityDomain(StrEnum):
    """Private capability lookup domains."""

    LOGICAL_TYPE = "logical_type"
    LITERAL = "literal"
    PARAMETER = "parameter"
    SCALAR_FUNCTION = "scalar_function"
    UNARY_OPERATOR = "unary_operator"
    BINARY_OPERATOR = "binary_operator"
    COMPARISON = "comparison"
    NULL_TEST = "null_test"
    CLAUSE = "clause"
    AGGREGATE = "aggregate"
    EXPRESSION_STAGE = "expression_stage"
    CONVERSION = "conversion"
    DIALECT_LOWERING = "dialect_lowering"
    EXTENSION_SIGNATURE = "extension_signature"


class CapabilitySupport(StrEnum):
    """Exact-current support postures for evidenced facts."""

    SUPPORTED = "supported"
    EXPLICITLY_UNSUPPORTED = "explicitly_unsupported"


class CapabilityDispositionKind(StrEnum):
    """Independent roadmap disposition kinds."""

    NONE = "none"
    DEFERRED = "deferred"
    OUT_OF_SCOPE = "out_of_scope"


class CapabilityEvidenceSource(StrEnum):
    """Atomic sources of private capability evidence."""

    GRAMMAR_AST = "grammar_ast"
    SEMANTIC_CATALOG = "semantic_catalog"
    SEMANTIC_PROCEDURE = "semantic_procedure"
    SEMANTIC_MODEL = "semantic_model"
    IR = "ir"
    BACKEND = "backend"
    PROJECT = "project"
    PUBLIC = "public"
    ROADMAP = "roadmap"
    TEST = "test"
    SPEC = "spec"


class CapabilityReasonCode(StrEnum):
    """Bounded private evidence and lookup-ready reason vocabulary."""

    NO_CATALOG_ENTRY = "no_catalog_entry"
    NOT_EVIDENCED = "not_evidenced"
    NO_CURRENT_RESULT_RULE = "no_current_result_rule"
    UNRESOLVED_EXPRESSION = "unresolved_expression"
    NULL_LITERAL_NO_CONCRETE_TYPE = "null_literal_no_concrete_type"
    UNKNOWN_NULLABILITY = "unknown_nullability"
    SQL_THREE_VALUED_TRUTH = "sql_three_valued_truth"
    DIALECT_LOWERING_GAP = "dialect_lowering_gap"
    CONFLICTING_EVIDENCE = "conflicting_evidence"


def _require_nonblank_text(value: object, field_name: str) -> str:
    """Return exact text after validating its local structural shape."""

    if type(value) is not str or not value.strip():
        raise ValueError(f"{field_name} requires exact nonblank text")
    return value


def _require_optional_nonblank_text(
    value: object | None,
    field_name: str,
) -> str | None:
    """Validate optional exact text without normalizing it."""

    if value is None:
        return None
    return _require_nonblank_text(value, field_name)


@dataclass(frozen=True, slots=True)
class CapabilityKey:
    """One exact private capability identity."""

    domain: CapabilityDomain
    subject: str | None = None
    operation: str | None = None
    operands: tuple[str, ...] = ()
    context: str | None = None
    dialect: str | None = None
    extension: str | None = None

    def __post_init__(self) -> None:
        """Freeze ordered operands and enforce key-shape invariants."""

        if type(self.domain) is not CapabilityDomain:
            raise ValueError("Capability key requires an exact domain")
        subject = _require_optional_nonblank_text(self.subject, "subject")
        operation = _require_optional_nonblank_text(self.operation, "operation")
        if subject is None and operation is None:
            raise ValueError("Capability key requires subject or operation")

        if isinstance(self.operands, (str, bytes)):
            raise ValueError("Capability key operands require an iterable of text")
        try:
            operands = tuple(self.operands)
        except TypeError as exc:
            raise ValueError(
                "Capability key operands require an iterable of text"
            ) from exc
        for operand in operands:
            _require_nonblank_text(operand, "operand")
        object.__setattr__(self, "operands", operands)

        _require_optional_nonblank_text(self.context, "context")
        dialect = _require_optional_nonblank_text(self.dialect, "dialect")
        extension = _require_optional_nonblank_text(self.extension, "extension")
        if extension is not None and dialect is None:
            raise ValueError("Capability key extension requires a dialect")


@dataclass(frozen=True, slots=True)
class CapabilityDisposition:
    """One independent roadmap disposition."""

    kind: CapabilityDispositionKind
    owner: str | None = None
    reason: str | None = None

    def __post_init__(self) -> None:
        """Enforce complete disposition ownership without inference."""

        if type(self.kind) is not CapabilityDispositionKind:
            raise ValueError("Capability disposition requires an exact kind")
        owner = _require_optional_nonblank_text(self.owner, "owner")
        reason = _require_optional_nonblank_text(self.reason, "reason")
        if self.kind is CapabilityDispositionKind.NONE:
            if owner is not None or reason is not None:
                raise ValueError("NONE disposition forbids owner and reason")
            return
        if owner is None or reason is None:
            raise ValueError("Deferred dispositions require owner and reason")


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    """One ordered atomic capability evidence entry."""

    source: CapabilityEvidenceSource
    source_path: str
    source_reference: str
    reason: CapabilityReasonCode | None = None
    dialect: str | None = None
    backend: str | None = None
    extension: str | None = None

    def __post_init__(self) -> None:
        """Validate atomic provenance and optional scope dimensions."""

        if type(self.source) is not CapabilityEvidenceSource:
            raise ValueError("Capability evidence requires an exact source")
        _require_nonblank_text(self.source_path, "source_path")
        _require_nonblank_text(self.source_reference, "source_reference")
        if self.reason is not None and type(self.reason) is not CapabilityReasonCode:
            raise ValueError("Capability evidence requires an exact reason")
        dialect = _require_optional_nonblank_text(self.dialect, "dialect")
        _require_optional_nonblank_text(self.backend, "backend")
        extension = _require_optional_nonblank_text(self.extension, "extension")
        if extension is not None and dialect is None:
            raise ValueError("Capability evidence extension requires a dialect")


@dataclass(frozen=True, slots=True)
class CapabilityFact:
    """One immutable composed private descriptive capability fact."""

    key: CapabilityKey
    support: CapabilitySupport
    disposition: CapabilityDisposition
    evidence: tuple[CapabilityEvidence, ...]

    def __post_init__(self) -> None:
        """Freeze ordered evidence and reject incomplete or duplicate facts."""

        if type(self.key) is not CapabilityKey:
            raise ValueError("Capability fact requires an exact key")
        if type(self.support) is not CapabilitySupport:
            raise ValueError("Capability fact requires an exact support posture")
        if type(self.disposition) is not CapabilityDisposition:
            raise ValueError("Capability fact requires an exact disposition")
        if isinstance(self.evidence, (str, bytes)):
            raise ValueError("Capability fact evidence requires an iterable")
        try:
            evidence = tuple(self.evidence)
        except TypeError as exc:
            raise ValueError("Capability fact evidence requires an iterable") from exc
        if not evidence:
            raise ValueError("Capability fact requires evidence")
        if any(type(entry) is not CapabilityEvidence for entry in evidence):
            raise ValueError("Capability fact requires exact evidence entries")
        if len(set(evidence)) != len(evidence):
            raise ValueError("Capability fact forbids duplicate evidence")
        object.__setattr__(self, "evidence", evidence)
