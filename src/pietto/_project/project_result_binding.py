"""Producer observations are checked against exact upstream scalar realizations."""

from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import TYPE_CHECKING, Any, cast

from pietto._project.model import ProjectResolvedTypeKind, ProjectRowFieldNullability
from pietto._project.project_result_contract import (
    NestedShape,
    PiettoResultContract,
    ResultError,
    scalar_fields,
    verify_result_contract,
)
from pietto._project.project_sql_emission_ast import SQLColumn, SQLSelect
from pietto._project.project_sql_emission_inspection import inspect_project_sql_emission
from pietto._project.project_sql_emission_rows import field_realization, signed_range

if TYPE_CHECKING:
    from pietto._project.project_result_contract import ResultField, ScalarField

__all__: tuple[str, ...] = ()
# D71.07/S02: child rows per batch and per execution; never a caller knob.
MAX_CHILD_ROWS = 1 << 20
# Child leaves this phase opens; S14/S15 only widen this allowlist.
CHILD_KINDS = ("Int", "Bool", "Text")


@dataclass(frozen=True, slots=True)
class TextObservation:
    max_characters: int
    encoding: str
    collation: str
    padding: str
    storage_length: int | None = None


@dataclass(frozen=True, slots=True)
class DecimalObservation:
    precision: int
    scale: int


@dataclass(frozen=True, slots=True)
class ProducerObservation:
    ordinal: int
    label: str
    family: str
    storage: str
    lower: int | None = None
    upper: int | None = None
    # Protocol metadata can be unknown; it is not logical NULL authority.
    protocol_nullable: bool | None = None
    domain: str = "int_range"
    carrier: str = "int"
    text: TextObservation | None = None
    decimal: DecimalObservation | None = None
    meaning: Any = None
    fractional_seconds: int | None = None


@dataclass(frozen=True, slots=True, eq=False)
class ProducerFieldBinding:
    field: ScalarField = dc_field(repr=False)
    column: Any = dc_field(repr=False)
    observation: ProducerObservation
    nullable: bool


@dataclass(frozen=True, slots=True, eq=False)
class ProducerNestedBinding:
    """One collected child relation: its exact child count and scalar child leaves."""

    field: ResultField = dc_field(repr=False)
    column: Any = dc_field(repr=False)
    count: ProducerObservation
    children: tuple[ProducerFieldBinding, ...] = dc_field(repr=False)
    nullable: bool


@dataclass(frozen=True, slots=True, eq=False)
class ProducerResultBinding:
    contract: PiettoResultContract = dc_field(repr=False)
    artifact: Any = dc_field(repr=False)
    fields: tuple[ProducerFieldBinding | ProducerNestedBinding, ...] = dc_field(
        repr=False
    )
    projection: Any = dc_field(default=None, repr=False)
    output: Any = dc_field(default=None, repr=False)


def _columns(contract, artifact, projection=None, output=None) -> tuple[Any, ...]:
    if output is not None and getattr(output, "guarded", None) is not None:
        from pietto._project.project_result_output import verify_output

        if projection is not None:
            raise ResultError("PRODUCER_ROOT")
        return verify_output(output, artifact, contract, binding=output.binding)
    try:
        view = inspect_project_sql_emission(artifact, artifact.request)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ResultError("PRODUCER_ROOT") from exc
    verify_result_contract(contract, view.request.verification)
    if contract.scalar_meaning is not view.request.scalar_meaning:
        raise ResultError("PRODUCER_ROOT")
    if output is not None:
        from pietto._project.project_result_output import verify_output

        if projection is not None:
            raise ResultError("PRODUCER_ROOT")
        return verify_output(output, artifact, contract, binding=output.binding)
    # Every route below reads scalar leaves: the postgres_rows path without an
    # output and bind_native_projection refuse a nested shape here, before any
    # connection.
    scalar_fields(contract)
    if projection is not None:
        from pietto._project.project_execution_projection import verify_projection

        return verify_projection(projection, artifact)
    if type(artifact.ast) is not SQLSelect or any(
        type(c) is not SQLColumn for c in view.columns
    ):
        raise ResultError("PRODUCER_UNSUPPORTED")
    return view.columns


def bind_producer(
    contract, artifact, observations, *, projection=None, output=None
) -> ProducerResultBinding:
    columns = _columns(contract, artifact, projection, output)
    if type(observations) is not tuple or len(observations) != len(columns):
        raise ResultError("PRODUCER_FIELDS")
    fields = tuple(
        _bound(f, c, o, general=output is not None)
        for f, c, o in zip(contract.shape.fields, columns, observations, strict=True)
    )
    binding = ProducerResultBinding(contract, artifact, fields, projection, output)
    verify_producer_binding(binding, contract, artifact)
    return binding


def _bound(field, column, observation, *, general):
    """One field's binding; a nested field observes ``(count, children)``."""
    nullable = (
        field.nullability is not ProjectRowFieldNullability.NON_NULL
        if general
        else field.nullability is ProjectRowFieldNullability.NULLABLE
    )
    if type(field.shape) is not NestedShape:
        return ProducerFieldBinding(field, column, observation, nullable)
    children = getattr(column, "children", None)
    if (
        type(observation) is not tuple
        or len(observation) != 2
        or type(observation[1]) is not tuple
        or type(children) is not tuple
        or not len(observation[1]) == len(children) == len(field.shape.fields)
    ):
        raise ResultError("PRODUCER_FIELDS")
    count, observed = observation
    return ProducerNestedBinding(
        field,
        column,
        count,
        tuple(
            ProducerFieldBinding(
                cast("ScalarField", leaf),
                child,
                child_observation,
                leaf.nullability is not ProjectRowFieldNullability.NON_NULL,
            )
            for leaf, child, child_observation in zip(
                field.shape.fields, children, observed, strict=True
            )
        ),
        nullable,
    )


def verify_producer_binding(binding, contract, artifact) -> None:
    """Recheck upstream first, including a coordinated binding/Arrow corruption."""
    if type(binding) is not ProducerResultBinding:
        raise ResultError("PRODUCER_ROOT")
    columns = _columns(contract, artifact, binding.projection, binding.output)
    if (
        type(binding) is not ProducerResultBinding
        or binding.contract is not contract
        or binding.artifact is not artifact
        or type(binding.fields) is not tuple
        or len(binding.fields) != len(columns)
    ):
        raise ResultError("PRODUCER_ROOT")
    family = artifact.request.family
    general = binding.output is not None
    storages = _storages(family, general)
    for ordinal, (bound, leaf, column) in enumerate(
        zip(binding.fields, contract.shape.fields, columns, strict=True)
    ):
        if type(leaf.shape) is NestedShape:
            _verify_nested(contract, family, storages, ordinal, bound, leaf, column)
            continue
        if (
            type(bound) is not ProducerFieldBinding
            or bound.field is not leaf
            or bound.column is not column
            or column.export is not leaf.port
            or column.ordinal != ordinal
            or column.label != leaf.label
        ):
            raise ResultError("PRODUCER_FIELDS")
        _verify_leaf(contract, family, storages, general, ordinal, bound, leaf, column)


def _verify_nested(contract, family, storages, ordinal, bound, leaf, column):
    """A collected field: its exact child count, then each child by the leaf law.

    Only an exact output reaches here (``_columns``); its carrier descriptor is
    the output's own column, compared by identity.
    """
    from pietto._project.project_result_output import NestedOutputColumn

    children = leaf.shape.fields
    if (
        type(bound) is not ProducerNestedBinding
        or bound.field is not leaf
        or bound.column is not column
        or type(column) is not NestedOutputColumn
        or column.export is not leaf.port
        or column.ordinal != ordinal
        or column.label != leaf.label
        or type(bound.children) is not tuple
        or not len(bound.children) == len(column.children) == len(children)
    ):
        raise ResultError("PRODUCER_FIELDS")
    if any(child.shape.canonical.name not in CHILD_KINDS for child in children):
        raise ResultError("PRODUCER_UNSUPPORTED")
    count = bound.count
    if (
        type(count) is not ProducerObservation
        or any(
            type(value) is not kind
            for value, kind in (
                (count.ordinal, int),
                (count.label, str),
                (count.family, str),
                (count.storage, str),
                (count.lower, int),
                (count.upper, int),
                (count.domain, str),
                (count.carrier, str),
            )
        )
        or (
            count.ordinal,
            count.label,
            count.family,
            count.storage,
            count.lower,
            count.upper,
            count.domain,
            count.carrier,
        )
        != (
            ordinal,
            leaf.label,
            family,
            "pg_int8",
            0,
            MAX_CHILD_ROWS,
            "child_count",
            "int",
        )
        or any(
            value is not None
            for value in (
                count.text,
                count.decimal,
                count.meaning,
                count.fractional_seconds,
            )
        )
        or (
            count.protocol_nullable is not None
            and type(count.protocol_nullable) is not bool
        )
        or type(bound.nullable) is not bool
        or bound.nullable
        is not (leaf.nullability is not ProjectRowFieldNullability.NON_NULL)
    ):
        raise ResultError("PRODUCER_OBSERVATION")
    for k, (child, child_leaf, child_column) in enumerate(
        zip(bound.children, children, column.children, strict=True)
    ):
        if (
            type(child) is not ProducerFieldBinding
            or child.field is not child_leaf
            or child.column is not child_column
            or child_column.export is not child_leaf.port
            or child_column.ordinal != k
            or child_column.label != child_leaf.label
        ):
            raise ResultError("PRODUCER_FIELDS")
        _verify_leaf(
            contract, family, storages, True, k, child, child_leaf, child_column
        )


def _verify_leaf(contract, family, storages, general, ordinal, bound, leaf, column):
    """The per-leaf law of one scalar field, top-level or a collected child."""
    realized = column.realization if general else field_realization(column.source_field)
    if (
        realized is None
        or realized.tag not in storages
        or leaf.shape.canonical.kind is not ProjectResolvedTypeKind.BUILTIN
        or leaf.shape.canonical.name != realized.tag
        or realized.storage.get("kind") not in storages[realized.tag]
        or set(realized.storage)
        != (
            {"kind", "fractional_seconds"}
            if realized.tag == "Timestamp"
            else {"kind", "precision", "scale"}
            if realized.tag == "Decimal"
            else {"kind", "length"}
            if realized.tag == "Text" and realized.storage.get("kind") == "my_varchar"
            else {"kind"}
        )
        or (
            type(realized.nullable) is not bool
            and not (general and realized.nullable == "unknown")
        )
        or leaf.nullability
        not in (
            ProjectRowFieldNullability.NULLABLE,
            ProjectRowFieldNullability.NON_NULL,
            *((ProjectRowFieldNullability.UNKNOWN,) if general else ()),
        )
    ):
        raise ResultError("PRODUCER_UNSUPPORTED")
    nullable = (
        leaf.nullability is not ProjectRowFieldNullability.NON_NULL
        if general
        else leaf.nullability is ProjectRowFieldNullability.NULLABLE
    )
    storage = realized.storage["kind"]
    lower = upper = None
    text = None
    decimal = None
    meaning = None
    fractional_seconds = None
    if realized.tag == "Int":
        if (
            set(realized.domain) != {"kind", "min", "max"}
            or realized.domain["kind"] != "int_range"
        ):
            raise ResultError("PRODUCER_DOMAIN")
        lower, upper = int(realized.domain["min"]), int(realized.domain["max"])
        bounds = signed_range(realized.storage)
        if bounds is None or not bounds[0] <= lower <= upper <= bounds[1]:
            raise ResultError("PRODUCER_DOMAIN")
        domain, carrier = "int_range", "int"
    elif realized.tag == "Bool":
        if realized.domain != {"kind": "bool01"}:
            raise ResultError("PRODUCER_DOMAIN")
        domain, carrier = "bool01", "bool" if family == "postgres" else "int01"
    elif realized.tag == "Text":
        expected = (
            ("UTF8", "C", "NO PAD")
            if family == "postgres"
            else ("utf8mb4", "utf8mb4_0900_bin", "NO PAD")
        )
        maximum = realized.domain.get("max_characters")
        length = realized.storage.get("length")
        if (
            set(realized.domain)
            != {"kind", "max_characters", "encoding", "collation", "padding"}
            or realized.domain["kind"] != "text"
            or type(maximum) is not int
            or maximum < 0
            or tuple(realized.domain[k] for k in ("encoding", "collation", "padding"))
            != expected
            or (
                storage == "my_varchar"
                and (type(length) is not int or not maximum <= length <= 16383)
            )
        ):
            raise ResultError("PRODUCER_DOMAIN")
        text = TextObservation(maximum, *expected, length)
        domain, carrier = "text", "str"
    elif realized.tag == "Decimal":
        if general:
            precision = realized.domain.get("precision")
            scale = realized.domain.get("scale")
        else:
            fact = column.source_field.decimal
            precision = None if fact is None else fact.precision
            scale = None if fact is None else fact.scale
        if (
            type(precision) is not int
            or type(scale) is not int
            or not 1 <= precision <= 65
            or not 0 <= scale <= min(precision, 30)
            or realized.domain
            != {"kind": "decimal", "precision": precision, "scale": scale}
            or any(
                type(v[k]) is not int
                for v in (realized.storage, realized.domain)
                for k in ("precision", "scale")
            )
            or (realized.storage["precision"], realized.storage["scale"])
            != (precision, scale)
        ):
            raise ResultError("PRODUCER_DOMAIN")
        decimal = DecimalObservation(precision, scale)
        domain, carrier = "decimal", "decimal"
    elif realized.tag == "Date":
        if realized.domain != {"kind": "date"}:
            raise ResultError("PRODUCER_DOMAIN")
        domain, carrier = "date", "date"
    elif realized.tag in ("Timestamp", "UUID"):
        from pietto._project.project_scalar_meaning import _source_entry

        entry = (
            leaf.meaning
            if general
            else _source_entry(contract.scalar_meaning, column.source_field.field)
        )
        if entry is None or leaf.meaning is not entry:
            raise ResultError("PRODUCER_DOMAIN")
        meaning = entry.law
        if realized.tag == "Timestamp":
            if (
                realized.domain != {"kind": "timestamp"}
                or type(realized.storage["fractional_seconds"]) is not int
                or realized.storage["fractional_seconds"] != 6
            ):
                raise ResultError("PRODUCER_DOMAIN")
            domain, carrier, fractional_seconds = "timestamp", "datetime", 6
        else:
            if realized.domain != {"kind": "uuid", "encoding": "standard_bytes"}:
                raise ResultError("PRODUCER_DOMAIN")
            domain, carrier = "uuid", "uuid" if family == "postgres" else "bytes16"
    else:
        if realized.domain != {
            "kind": "finite_float",
            "format": "binary64",
        } and not (general and realized.domain == {"kind": "float64"}):
            raise ResultError("PRODUCER_DOMAIN")
        domain, carrier = "finite_float", "float"
    if realized.nullable is not nullable and not (
        general and leaf.nullability is ProjectRowFieldNullability.UNKNOWN
    ):
        raise ResultError("PRODUCER_DOMAIN")
    obs = bound.observation
    if (
        type(obs) is not ProducerObservation
        or type(obs.ordinal) is not int
        or obs.ordinal != ordinal
        or type(obs.label) is not str
        or obs.label != leaf.label
        or type(obs.family) is not str
        or obs.family != family
        or type(obs.storage) is not str
        or obs.storage != storage
        or type(obs.domain) is not str
        or obs.domain != domain
        or type(obs.carrier) is not str
        or obs.carrier != carrier
        or (type(obs.lower) is not int if lower is not None else obs.lower is not None)
        or (type(obs.upper) is not int if upper is not None else obs.upper is not None)
        or (obs.lower, obs.upper) != (lower, upper)
        or (
            obs.text is not None
            if text is None
            else (
                type(obs.text) is not TextObservation
                or type(obs.text.max_characters) is not int
                or any(
                    type(v) is not str
                    for v in (
                        obs.text.encoding,
                        obs.text.collation,
                        obs.text.padding,
                    )
                )
                or (
                    type(obs.text.storage_length) is not int
                    if text.storage_length is not None
                    else obs.text.storage_length is not None
                )
                or obs.text != text
            )
        )
        or (
            obs.decimal is not None
            if decimal is None
            else (
                type(obs.decimal) is not DecimalObservation
                or type(obs.decimal.precision) is not int
                or type(obs.decimal.scale) is not int
                or obs.decimal != decimal
            )
        )
        or (
            obs.meaning is not None
            if meaning is None
            else type(obs.meaning) is not type(meaning) or obs.meaning != meaning
        )
        or (
            type(obs.fractional_seconds) is not int
            if fractional_seconds is not None
            else obs.fractional_seconds is not None
        )
        or obs.fractional_seconds != fractional_seconds
        or type(bound.nullable) is not bool
        or bound.nullable is not nullable
        or (
            obs.protocol_nullable is not None
            and type(obs.protocol_nullable) is not bool
        )
    ):
        raise ResultError("PRODUCER_OBSERVATION")

    if meaning is not None:
        from pietto._project.project_scalar_meaning import (
            verify_law,
            ScalarMeaningError,
        )

        try:
            verify_law(obs.meaning, realized.tag)
        except ScalarMeaningError as exc:
            raise ResultError("PRODUCER_OBSERVATION") from exc


def _storages(family, general):
    """The closed storage kinds of each scalar tag on one target family."""
    storages = {
        "postgres": {
            "Int": ("pg_int2", "pg_int4", "pg_int8"),
            "Bool": ("pg_bool",),
            "Float": ("pg_float8",),
            "Text": ("pg_text",),
            "Decimal": ("pg_numeric",),
            "Date": ("pg_date",),
            "Timestamp": ("pg_timestamp",),
            "UUID": ("pg_uuid",),
        },
        "mysql": {
            "Int": ("my_smallint", "my_int", "my_bigint"),
            "Bool": ("my_bool01",),
            "Float": ("my_double",),
            "Text": ("my_varchar",),
            "Decimal": ("my_decimal",),
            "Date": ("my_date",),
            "Timestamp": ("my_datetime",),
            "UUID": ("my_uuid_bytes",),
        },
    }.get(family, {})
    if general and family == "mysql":
        storages = {
            **storages,
            "Int": (*storages["Int"], "my_signed_int"),
            "Bool": (*storages["Bool"], "my_signed_bool"),
            "Text": (*storages["Text"], "my_utf8mb4_text"),
        }
    return storages
