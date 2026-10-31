"""Private neutral result fields over retained, verified completed output."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, cast

from pietto._project.model import ProjectResolvedTypeKind
from pietto._project.project_sql_plan import ProjectSQLPlan
from pietto._project.project_query_block_ir import ProjectIRQueryBlockTerminal
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
)

__all__: tuple[str, ...] = ()


class ResultError(ValueError):
    """Stable private boundary category; not a public compiler diagnostic."""

    def __init__(self, category: str):
        self.category = category
        super().__init__(category)


@dataclass(frozen=True, slots=True, eq=False)
class ScalarShape:
    declared: Any = field(repr=False)
    canonical: Any = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class NestedShape:
    """One collected child relation: retained element facts and scalar child leaves."""

    collect: Any = field(repr=False)
    owner: Any = field(repr=False)
    output: Any = field(repr=False)
    multiplicity: Any = field(repr=False)
    ordering: Any = field(repr=False)
    fields: tuple[ResultField, ...] = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ResultField:
    ordinal: int
    label: str
    port: Any = field(repr=False)
    shape: ScalarShape | NestedShape
    nullability: Any = field(repr=False)
    provenance: Any = field(repr=False)
    meaning: Any = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class ResultShape:
    """Ordered top-level fields: a scalar leaf, or one level of scalar leaves."""

    fields: tuple[ResultField, ...] = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class PiettoResultContract:
    authority: ProjectSQLPlanVerification = field(repr=False)
    owner: Any = field(repr=False)
    output: Any = field(repr=False)
    shape: ResultShape
    multiplicity: Any = field(repr=False)
    ordering: Any = field(repr=False)
    scalar_meaning: Any = field(default=None, repr=False)


if TYPE_CHECKING:

    @dataclass(frozen=True, slots=True, eq=False)
    class ScalarField(ResultField):
        """Static view only: a verified leaf whose shape is scalar."""

        shape: ScalarShape


# An allowlist: a new resolved kind is never a scalar leaf by default.
_SCALAR_KINDS = frozenset(
    (
        ProjectResolvedTypeKind.BUILTIN,
        ProjectResolvedTypeKind.TYPE_ALIAS,
        ProjectResolvedTypeKind.ENUM,
    )
)


def scalar_fields(contract) -> tuple[ScalarField, ...]:
    """The verified fields of a reader that is not open to nested shapes yet."""
    fields = contract.shape.fields
    if any(type(leaf.shape) is not ScalarShape for leaf in fields):
        raise ResultError("NESTED_UNAVAILABLE")
    return cast("tuple[ScalarField, ...]", fields)


def _neutral(checked):
    from pietto._project.project_sql_plan_verification import (
        CompiledSQLPlanVerification,
        verify_compiled_sql_plan,
    )

    if type(checked) is CompiledSQLPlanVerification:
        verify_compiled_sql_plan(checked.plan)
        if (
            checked.completed is not checked.plan.ir.completed
            or checked.selected_owner is not checked.plan.ir.selected.owner
        ):
            raise ResultError("ROOT")
        return checked.plan.ir.selected
    if (
        type(checked) is not ProjectSQLPlanVerification
        or type(checked.plan) is not ProjectSQLPlan
    ):
        raise ResultError("ROOT")
    if not verify_project_sql_plan(
        checked.plan,
        checked.completed,
        checked.analysis_bundle,
        checked.selected_owner,
        literal_policy=checked.literal_policy,
        envelope=checked.envelope,
    ).verified:
        raise ResultError("ROOT")
    entries = checked.analysis_bundle.root.find_owner(checked.selected_owner)
    if len(entries) != 1 or isinstance(entries[0], ProjectIRQueryBlockTerminal):
        raise ResultError("ROOT")
    return entries[0]


def build_result_contract(
    checked: ProjectSQLPlanVerification, *, scalar_meaning=None
) -> PiettoResultContract:
    entry = _neutral(checked)
    from pietto._project.project_scalar_meaning import (
        verify_scalar_meaning,
        ScalarMeaningError,
    )

    try:
        if scalar_meaning is not None:
            verify_scalar_meaning(scalar_meaning, checked)
    except ScalarMeaningError as exc:
        raise ResultError(exc.category) from exc
    plan: Any = checked.plan
    leaves = []
    for ordinal, port in enumerate(plan.exports):
        kind = port.field.evidence.resolved_type.kind
        if kind in _SCALAR_KINDS:
            leaves.append(_scalar_leaf(ordinal, port, scalar_meaning))
        elif kind is ProjectResolvedTypeKind.NESTED_RELATION:
            leaves.append(_nested_leaf(checked, ordinal, port, scalar_meaning))
        else:
            raise ResultError("SCALAR_UNAVAILABLE")
    contract = PiettoResultContract(
        checked,
        checked.selected_owner,
        entry.active_output,
        ResultShape(tuple(leaves)),
        entry.active_properties.multiplicity,
        entry.active_properties.ordering,
        scalar_meaning,
    )
    verify_result_contract(contract, checked)
    return contract


def verify_result_contract(contract, checked) -> None:
    """Compare every retained occurrence to upstream; never rebuild a contract."""
    entry = _neutral(checked)
    if (
        type(contract) is not PiettoResultContract
        or contract.authority is not checked
        or contract.owner is not checked.selected_owner
        or contract.output is not entry.active_output
        or contract.multiplicity is not entry.active_properties.multiplicity
        or contract.ordering is not entry.active_properties.ordering
    ):
        raise ResultError("ROOT")
    if (
        type(contract.shape) is not ResultShape
        or type(contract.shape.fields) is not tuple
    ):
        raise ResultError("FIELD")
    from pietto._project.project_scalar_meaning import (
        verify_scalar_meaning,
        ScalarMeaningError,
    )

    try:
        if contract.scalar_meaning is not None:
            verify_scalar_meaning(contract.scalar_meaning, checked)
    except ScalarMeaningError as exc:
        raise ResultError(exc.category) from exc
    ports = checked.plan.exports
    if len(contract.shape.fields) != len(ports):
        raise ResultError("FIELD")
    for ordinal, (leaf, port) in enumerate(
        zip(contract.shape.fields, ports, strict=True)
    ):
        if not _same_leaf(leaf, ordinal, port, contract.scalar_meaning):
            raise ResultError("FIELD")
        if type(leaf.shape) is NestedShape:
            _verify_nested(checked, leaf, port, contract.scalar_meaning)


def _scalar_leaf(ordinal, port, scalar_meaning):
    from pietto._project.project_scalar_meaning import _output_entry

    evidence = port.field.evidence
    declared = evidence.field_def.type_expr if evidence.field_def is not None else None
    return ResultField(
        ordinal,
        port.identity.name,
        port,
        ScalarShape(declared, evidence.resolved_type),
        port.field.effective_nullability,
        evidence.provenance,
        _output_entry(scalar_meaning, port),
    )


def _same_leaf(leaf, ordinal, port, scalar_meaning) -> bool:
    """One leaf's own facts against its port: a scalar leaf, or a container."""
    from pietto._project.project_scalar_meaning import _output_entry

    evidence = port.field.evidence
    if (
        type(leaf) is not ResultField
        or type(leaf.ordinal) is not int
        or leaf.ordinal != ordinal
        or leaf.label != port.identity.name
        or leaf.port is not port
        or leaf.nullability is not port.field.effective_nullability
        or leaf.provenance is not evidence.provenance
    ):
        return False
    if type(leaf.shape) is NestedShape:
        return (
            evidence.resolved_type.kind is ProjectResolvedTypeKind.NESTED_RELATION
            and leaf.meaning is None
        )
    declared = evidence.field_def.type_expr if evidence.field_def is not None else None
    return (
        type(leaf.shape) is ScalarShape
        and leaf.shape.declared is declared
        and leaf.shape.canonical is evidence.resolved_type
        and evidence.resolved_type.kind in _SCALAR_KINDS
        and leaf.meaning is _output_entry(scalar_meaning, port)
    )


def _compiled_element(plan, port):
    """The compiled authority's counterpart of ``_element`` (Phase71 S09):
    the Collect a nested export carries (through the parent's result unit),
    its let's terminal result unit and that unit's ports, which the rebuilt
    S04 descriptor must name in order."""
    from pietto._project.project_compiled_schema import Address

    records = plan.ir.completed.root.records
    current = Address(port.ref.kind, port.ref.position)
    source = records[records[current].get("source")]
    if source.address.kind == "read":
        current = source.get("port")
    collects = tuple(c for c in plan.collects if c.export is plan.references[current])
    definitions = tuple(
        d
        for d in plan.definitions
        if len(collects) == 1 and d.ref is collects[0].producer
    )
    if len(collects) != 1 or len(definitions) != 1:
        raise ResultError("NESTED_ELEMENT")
    collect, entry, children = collects[0], definitions[0].entry, definitions[0].exports
    nested = port.field.evidence.resolved_type.nested
    if (
        len(collect.children) != len(children)
        or any(a is not b.ref for a, b in zip(collect.children, children, strict=True))
        or entry.kind != "result"
        or len(nested.element_fields) != len(children)
        or any(
            child.identity.name != item.identity.name
            or child.field.effective_nullability is not item.effective_nullability
            or child.field.evidence.resolved_type.kind not in _SCALAR_KINDS
            for child, item in zip(children, nested.element_fields, strict=True)
        )
        or type(entry.owner.let_position) is not int
        or nested.element_relation.let_position != entry.owner.let_position
        or entry.active_properties.multiplicity.value != ("bag",)
    ):
        raise ResultError("NESTED_ELEMENT")
    if not entry.active_properties.ordering.value:
        raise ResultError("NESTED_ORDER")
    return collect, entry, children


def _element(checked, port):
    """The one Collect read a nested export carries, its producer's entry and
    exports; the S04 descriptor must name exactly those children. A rebuilt
    producer row (DISTINCT, QUALIFY) has other field evidence than the
    descriptor, so the children are the Collect read's own."""
    from pietto._project.project_joined_row_filter import ProjectJoinedRowMultiplicity
    from pietto._project.project_sql_plan_nested import collect_of

    plan = checked.plan
    if type(checked) is not ProjectSQLPlanVerification:
        return _compiled_element(plan, port)
    try:
        collect = collect_of(plan, port.ref)
    except ValueError as exc:
        raise ResultError("NESTED_ELEMENT") from exc
    definitions = tuple(
        d for d in plan.bindings.definitions if d.ref is collect.producer
    )
    if len(definitions) != 1:
        raise ResultError("NESTED_ELEMENT")
    entry, children = definitions[0].entry, definitions[0].exports
    nested = port.field.evidence.resolved_type.nested
    owner = entry.owner
    if (
        len(collect.children) != len(children)
        or any(a is not b.ref for a, b in zip(collect.children, children, strict=True))
        or len(nested.element_fields) != len(children)
        or any(
            child.identity != item.identity
            or child.field.effective_nullability is not item.effective_nullability
            or child.field.output is not entry.active_output
            for child, item in zip(children, nested.element_fields, strict=True)
        )
        or type(owner.let_position) is not int
        or owner.table_function is not None
        or owner.unnest_position is not None
        or entry.active_properties.multiplicity is not ProjectJoinedRowMultiplicity.BAG
    ):
        raise ResultError("NESTED_ELEMENT")
    # Every collected let orders its rows (D71.03); a missing order is a broken
    # invariant, never a new refusal.
    if entry.active_properties.ordering is None:
        raise ResultError("NESTED_ORDER")
    return collect, entry, children


def _nested_leaf(checked, ordinal, port, scalar_meaning):
    from pietto._project.project_scalar_meaning import ScalarMeaningError

    collect, entry, children = _element(checked, port)
    fields = []
    for position, child in enumerate(children):
        kind = child.field.evidence.resolved_type.kind
        if kind is ProjectResolvedTypeKind.NESTED_RELATION:
            raise ResultError("NESTED_DEPTH")
        if kind not in _SCALAR_KINDS:
            raise ResultError("SCALAR_UNAVAILABLE")
        try:
            fields.append(_scalar_leaf(position, child, scalar_meaning))
        except ScalarMeaningError as exc:
            # Never a child Timestamp or UUID without its meaning.
            raise ResultError("MEANING_UNAVAILABLE") from exc
    shape = NestedShape(
        collect,
        entry.owner,
        entry.active_output,
        entry.active_properties.multiplicity,
        entry.active_properties.ordering,
        tuple(fields),
    )
    evidence = port.field.evidence
    return ResultField(
        ordinal,
        port.identity.name,
        port,
        shape,
        port.field.effective_nullability,
        evidence.provenance,
    )


def _verify_nested(checked, leaf, port, scalar_meaning) -> None:
    shape = leaf.shape
    try:
        collect, entry, children = _element(checked, port)
        same = (
            shape.collect is collect
            and shape.owner is entry.owner
            and shape.output is entry.active_output
            and shape.multiplicity is entry.active_properties.multiplicity
            and shape.ordering is entry.active_properties.ordering
            and type(shape.fields) is tuple
            and len(shape.fields) == len(children)
            and all(
                _same_leaf(field, position, child, scalar_meaning)
                and type(field.shape) is ScalarShape
                for position, (field, child) in enumerate(
                    zip(shape.fields, children, strict=True)
                )
            )
        )
    except ValueError as exc:
        # ResultError and ScalarMeaningError: a child is judged as its container.
        raise ResultError("FIELD") from exc
    if not same:
        raise ResultError("FIELD")
