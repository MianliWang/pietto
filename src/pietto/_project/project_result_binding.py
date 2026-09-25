"""Producer observations are checked against exact upstream Int realizations."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Any

from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.project_result_contract import (
    PiettoResultContract,
    ResultError,
    ResultField,
    verify_result_contract,
)
from pietto._project.project_sql_emission_ast import SQLColumn, SQLSelect
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission
from pietto._project.project_sql_emission_rows import field_realization

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ProducerObservation:
    ordinal: int
    label: str
    family: str
    storage: str
    lower: int
    upper: int
    # Protocol metadata can be unknown; it is not logical NULL authority.
    protocol_nullable: bool | None = None


@dataclass(frozen=True, slots=True, eq=False)
class ProducerFieldBinding:
    field: ResultField = dc_field(repr=False)
    column: Any = dc_field(repr=False)
    observation: ProducerObservation
    nullable: bool


@dataclass(frozen=True, slots=True, eq=False)
class ProducerResultBinding:
    contract: PiettoResultContract = dc_field(repr=False)
    artifact: Any = dc_field(repr=False)
    fields: tuple[ProducerFieldBinding, ...] = dc_field(repr=False)


def _columns(contract, artifact):
    try:
        view = inspect_project_sql_emission(artifact, artifact.request)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ResultError("PRODUCER_ROOT") from exc
    verify_result_contract(contract, view.request.verification)
    if type(artifact.ast) is not SQLSelect or any(
        type(c) is not SQLColumn for c in view.columns
    ):
        raise ResultError("PRODUCER_UNSUPPORTED")
    return view.columns


def bind_producer(contract, artifact, observations) -> ProducerResultBinding:
    columns = _columns(contract, artifact)
    if type(observations) is not tuple or len(observations) != len(columns):
        raise ResultError("PRODUCER_FIELDS")
    fields = tuple(
        ProducerFieldBinding(
            f, c, o, f.nullability is ProjectRowFieldNullability.NULLABLE
        )
        for f, c, o in zip(contract.shape.fields, columns, observations, strict=True)
    )
    binding = ProducerResultBinding(contract, artifact, fields)
    verify_producer_binding(binding, contract, artifact)
    return binding


def verify_producer_binding(binding, contract, artifact) -> None:
    """Recheck upstream first, including a coordinated binding/Arrow corruption."""
    columns = _columns(contract, artifact)
    if (
        type(binding) is not ProducerResultBinding
        or binding.contract is not contract
        or binding.artifact is not artifact
        or type(binding.fields) is not tuple
        or len(binding.fields) != len(columns)
    ):
        raise ResultError("PRODUCER_ROOT")
    family = artifact.request.family
    storage = {"postgres": "pg_int8", "mysql": "my_bigint"}.get(family)
    for ordinal, (bound, leaf, column) in enumerate(
        zip(binding.fields, contract.shape.fields, columns, strict=True)
    ):
        if (
            type(bound) is not ProducerFieldBinding
            or bound.field is not leaf
            or bound.column is not column
            or column.export is not leaf.port
            or column.ordinal != ordinal
            or column.label != leaf.label
        ):
            raise ResultError("PRODUCER_FIELDS")
        realized = field_realization(column.source_field)
        if (
            realized is None
            or realized.tag != "Int"
            or leaf.shape.canonical.kind is not ProjectResolvedTypeKind.BUILTIN
            or leaf.shape.canonical.name != "Int"
            or realized.storage != {"kind": storage}
            or type(realized.nullable) is not bool
            or realized.domain.get("kind") != "int_range"
            or leaf.nullability
            not in (
                ProjectRowFieldNullability.NULLABLE,
                ProjectRowFieldNullability.NON_NULL,
            )
        ):
            raise ResultError("PRODUCER_UNSUPPORTED")
        nullable = leaf.nullability is ProjectRowFieldNullability.NULLABLE
        lower, upper = int(realized.domain["min"]), int(realized.domain["max"])
        if not -(2**63) <= lower <= upper < 2**63 or realized.nullable is not nullable:
            raise ResultError("PRODUCER_DOMAIN")
        obs = bound.observation
        if (
            type(obs) is not ProducerObservation
            or type(obs.ordinal) is not int
            or obs.ordinal != ordinal
            or obs.label != leaf.label
            or obs.family != family
            or obs.storage != storage
            or type(obs.lower) is not int
            or type(obs.upper) is not int
            or (obs.lower, obs.upper) != (lower, upper)
            or type(bound.nullable) is not bool
            or bound.nullable is not nullable
            or (
                obs.protocol_nullable is not None
                and type(obs.protocol_nullable) is not bool
            )
        ):
            raise ResultError("PRODUCER_OBSERVATION")
