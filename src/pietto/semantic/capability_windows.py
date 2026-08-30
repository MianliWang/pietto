"""Private window-function signature and backend-lowering capability facts."""

from __future__ import annotations

from collections.abc import Iterable

from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
    CapabilityKey,
    CapabilityReasonCode,
    CapabilitySupport,
)

__all__: tuple[str, ...] = ()

_WINDOW_IDENTITIES = (
    "row_number",
    "rank",
    "dense_rank",
    "percent_rank",
    "cume_dist",
    "ntile",
    "lag",
    "lead",
    "first_value",
    "last_value",
    "nth_value",
)

_SIGNATURE_OPERANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "row_number",
        (
            "0",
            "no_argument",
            "Int",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "rank",
        (
            "0",
            "no_argument",
            "Int",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "dense_rank",
        (
            "0",
            "no_argument",
            "Int",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "percent_rank",
        (
            "0",
            "no_argument",
            "Float",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "cume_dist",
        (
            "0",
            "no_argument",
            "Float",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "ntile",
        (
            "1",
            "positive_int_literal",
            "Int",
            "non_null",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "lag",
        (
            "1..3",
            "bounded_value_optional_offset_default",
            "T",
            "any_nullable_0_2_or_default_omitted_2",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "lead",
        (
            "1..3",
            "bounded_value_optional_offset_default",
            "T",
            "any_nullable_0_2_or_default_omitted_2",
            "WINDOW",
            "window_result",
            "mandatory_local_order",
        ),
    ),
    (
        "first_value",
        (
            "1",
            "bounded_value",
            "T",
            "nullable",
            "WINDOW",
            "window_result",
            "mandatory_resolved_order",
        ),
    ),
    (
        "last_value",
        (
            "1",
            "bounded_value",
            "T",
            "nullable",
            "WINDOW",
            "window_result",
            "mandatory_resolved_order",
        ),
    ),
    (
        "nth_value",
        (
            "2",
            "bounded_value_positive_int_literal",
            "T",
            "nullable",
            "WINDOW",
            "window_result",
            "mandatory_resolved_order",
        ),
    ),
)

_LOWERING_OPERANDS = ("WindowCallIR", "OVER", "partition_by", "order_by")
_NAVIGATION_LOWERING_OPERANDS = (*_LOWERING_OPERANDS, "respect_nulls")
_SIGNATURE_RESULT_TYPES = frozenset({"Int", "Float", "T"})
_SIGNATURE_NULLABILITIES = frozenset(
    {"non_null", "nullable", "any_nullable_0_2_or_default_omitted_2"}
)


def _none() -> CapabilityDisposition:
    return CapabilityDisposition(CapabilityDispositionKind.NONE)


def _evidence(
    source: CapabilityEvidenceSource,
    source_path: str,
    source_reference: str,
    *,
    dialect: str | None = None,
    backend: str | None = None,
) -> CapabilityEvidence:
    return CapabilityEvidence(
        source,
        source_path,
        source_reference,
        dialect=dialect,
        backend=backend,
    )


def _freeze_windows(facts: Iterable[CapabilityFact]) -> tuple[CapabilityFact, ...]:
    """Freeze exact facts without collapsing distinct same-key evidence."""

    if isinstance(facts, (str, bytes)):
        raise ValueError("Window capabilities require an iterable of facts")
    try:
        frozen = tuple(facts)
    except TypeError as exc:
        raise ValueError("Window capabilities require an iterable of facts") from exc
    if any(type(fact) is not CapabilityFact for fact in frozen):
        raise ValueError("Window capabilities require exact capability facts")
    if len(set(frozen)) != len(frozen):
        raise ValueError("Window capabilities forbid exact duplicate facts")
    return frozen


def _signature_evidence(subject: str) -> tuple[CapabilityEvidence, ...]:
    if subject in {"lag", "lead", "first_value", "last_value", "nth_value"}:
        catalog_path = "src/pietto/semantic/window_navigation_analysis.py"
        catalog_reference = (
            "_NAVIGATION_IDENTITIES"
            if subject in {"lag", "lead"}
            else "_FRAME_VALUE_IDENTITIES"
        )
        procedure_path = catalog_path
        procedure_reference = (
            "analyze_navigation_arguments"
            if subject in {"lag", "lead"}
            else "analyze_frame_value_arguments"
        )
    else:
        catalog_path = "src/pietto/semantic/window_analysis.py"
        catalog_reference = (
            "_RANKING_POLICIES"
            if subject in {"row_number", "rank", "dense_rank"}
            else "_DISTRIBUTION_FUNCTIONS"
        )
        procedure_path = catalog_path
        procedure_reference = "_analyze_recognized_window_expression"
    return (
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_CATALOG,
            catalog_path,
            catalog_reference,
        ),
        _evidence(
            CapabilityEvidenceSource.SEMANTIC_PROCEDURE,
            procedure_path,
            procedure_reference,
        ),
        _evidence(
            CapabilityEvidenceSource.IR,
            "src/pietto/ir/lowering.py",
            "_lower_window_expr",
        ),
    )


def _signature_fact(subject: str, operands: tuple[str, ...]) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject=subject,
            operation="signature",
            operands=operands,
            context="window_signature",
        ),
        CapabilitySupport.SUPPORTED,
        _none(),
        _signature_evidence(subject),
    )


def _lowering_operands(subject: str, dialect: str) -> tuple[str, ...]:
    if subject in {"lag", "lead"}:
        return _NAVIGATION_LOWERING_OPERANDS
    if subject in {"first_value", "last_value", "nth_value"}:
        frame_shape = (
            "rows_groups_offset_free_range_all_exclude"
            if dialect == "postgresql"
            else "rows_offset_free_range_omitted_exclude"
        )
        from_policy = "from_first" if subject == "nth_value" else "from_forbidden"
        return (*_LOWERING_OPERANDS, frame_shape, "respect_nulls", from_policy)
    return _LOWERING_OPERANDS


def _lowering_fact(
    subject: str,
    *,
    dialect: str,
    source_path: str,
    source_reference: str,
    backend: str,
) -> CapabilityFact:
    return CapabilityFact(
        CapabilityKey(
            CapabilityDomain.WINDOW_FUNCTION,
            subject=subject,
            operation="lowering",
            operands=_lowering_operands(subject, dialect),
            context="window_lowering",
            dialect=dialect,
        ),
        CapabilitySupport.SUPPORTED,
        _none(),
        (
            _evidence(
                CapabilityEvidenceSource.BACKEND,
                source_path,
                source_reference,
                dialect=dialect,
                backend=backend,
            ),
        ),
    )


_WINDOW_SIGNATURE_FACTS: tuple[CapabilityFact, ...] = _freeze_windows(
    _signature_fact(subject, operands) for subject, operands in _SIGNATURE_OPERANDS
)

_WINDOW_LOWERING_FACTS: tuple[CapabilityFact, ...] = _freeze_windows(
    (
        *(
            _lowering_fact(
                subject,
                dialect="postgresql",
                source_path="src/pietto/sql/expressions.py",
                source_reference="_render_window_call",
                backend="postgresql",
            )
            for subject in _WINDOW_IDENTITIES
        ),
        *(
            _lowering_fact(
                subject,
                dialect="mysql",
                source_path="src/pietto/sql/mysql_expressions.py",
                source_reference="_render_mysql_window_call",
                backend="private-mysql",
            )
            for subject in _WINDOW_IDENTITIES
        ),
    )
)

_WINDOW_CAPABILITY_FACTS: tuple[CapabilityFact, ...] = (
    _WINDOW_SIGNATURE_FACTS + _WINDOW_LOWERING_FACTS
)


def _signature_schema_is_complete(key: CapabilityKey) -> bool:
    if (
        key.operation != "signature"
        or key.context != "window_signature"
        or key.dialect is not None
        or key.extension is not None
        or len(key.operands) != 7
    ):
        return False
    (
        arity,
        argument_shape,
        result_type,
        result_nullability,
        stage,
        result_role,
        local_order_policy,
    ) = key.operands
    if (
        result_type not in _SIGNATURE_RESULT_TYPES
        or result_nullability not in _SIGNATURE_NULLABILITIES
        or stage != "WINDOW"
        or result_role != "window_result"
        or local_order_policy
        not in {"mandatory_local_order", "mandatory_resolved_order"}
    ):
        return False
    return any(
        subject == key.subject and operands[:2] == (arity, argument_shape)
        for subject, operands in _SIGNATURE_OPERANDS
    )


def _lowering_schema_is_complete(key: CapabilityKey) -> bool:
    return (
        key.operation == "lowering"
        and key.context == "window_lowering"
        and key.extension is None
        and key.subject in _WINDOW_IDENTITIES
        and key.dialect in {"postgresql", "mysql"}
        and key.operands == _lowering_operands(key.subject, key.dialect)
    )


def window_lookup_inputs(
    key: CapabilityKey,
) -> tuple[
    tuple[CapabilityFact, ...],
    bool,
    CapabilityReasonCode | None,
]:
    """Return window facts, exact completeness, and bounded uncertainty."""

    if type(key) is not CapabilityKey:
        raise ValueError("Window capabilities require an exact capability key")
    if key.domain is not CapabilityDomain.WINDOW_FUNCTION:
        return (), False, None
    if key.context == "window_signature":
        facts = _WINDOW_SIGNATURE_FACTS
        complete = _signature_schema_is_complete(key)
    elif key.context == "window_lowering":
        facts = _WINDOW_LOWERING_FACTS
        complete = _lowering_schema_is_complete(key)
    else:
        return (), False, CapabilityReasonCode.NOT_EVIDENCED
    return (
        facts,
        complete,
        None if complete else CapabilityReasonCode.NOT_EVIDENCED,
    )
