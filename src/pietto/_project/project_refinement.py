"""Explicit live refinement authority, distinct from an original emission.

An original artifact never acquires different SQL. Source capabilities, the
pre-attempt choice policy, and the full original output remain separate roots.
"""

from dataclasses import dataclass, field
from typing import Any
import weakref

from pietto._project.project_execution_source import (
    RetainedSourceRequirement,
    requirement_state,
    verify_requirement,
)
from pietto._project.project_result_output import GeneralOutput, prepare_output
from pietto._project.project_refinement_order import Coordinate
from pietto._project.project_refinement_rendering import CTE, Statement
from pietto._project.project_verification_scope import entry

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class TieRefinement:
    """Caller opt-in before any attempt; no mutable chooser or callback."""

    choice: str = "structural_occurrence_ascending"


@dataclass(frozen=True, slots=True, eq=False)
class UnitRefinement:
    original: Any = field(repr=False)
    address: int
    rule: str
    dependencies: tuple[int, ...]
    ctes: tuple[CTE, ...] = field(repr=False)
    terminal: str
    public_names: tuple[str, ...]
    key_names: tuple[str, ...]
    coordinates: tuple[Coordinate, ...]
    order_names: tuple[str, ...]
    order_coordinates: tuple[Coordinate, ...]
    directions: tuple[str, ...]
    capacity: str


@dataclass(frozen=True, slots=True, eq=False)
class RefinedQuery:
    original: Any = field(repr=False)
    output: GeneralOutput = field(repr=False)
    policy: TieRefinement
    sources: tuple[RetainedSourceRequirement, ...] = field(repr=False)
    source_states: tuple = field(repr=False)
    units: tuple[UnitRefinement, ...] = field(repr=False)
    statement: Statement = field(repr=False)
    prefix: str
    erasure: tuple[tuple[int, Any], ...] = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False, weakref_slot=True)
class LiveR2Witness:
    """Private proof that one live caller supplied this R2 refinement."""

    template: Any = field(repr=False)
    binding: Any = field(repr=False)
    refinement: RefinedQuery = field(repr=False)
    requirements: tuple[RetainedSourceRequirement, ...] = field(repr=False)
    reanchored: bool = field(repr=False)


_LIVE_R2_WITNESSES: weakref.WeakSet[LiveR2Witness] = weakref.WeakSet()


def verify_sources(requirements, sources, *, family="postgres"):
    """Exact ordered complete collection; repeated uses share their source root."""
    if type(requirements) is not tuple or len(requirements) != len(sources):
        raise ValueError("REFINEMENT_SOURCE_CLOSURE")
    for requirement, source in zip(requirements, sources, strict=True):
        if (
            type(requirement) is not RetainedSourceRequirement
            or requirement.source is not source
        ):
            raise ValueError("REFINEMENT_SOURCE_CORRESPONDENCE")
        verify_requirement(requirement, sources, family=family)
    if len({id(s.source) for s in requirements}) != len(requirements):
        # This set checks live root duplication only; its values never become
        # coordinates, structural addresses, or reopen authority.
        raise ValueError("REFINEMENT_DUPLICATE_SOURCE")


def prepare_refinement(
    artifact,
    sources,
    *,
    policy,
    output=None,
    binding=None,
):
    from pietto._project.project_refinement_lowering import lower
    from pietto._project.project_refinement_verification import verify_refinement

    if (
        type(policy) is not TieRefinement
        or policy.choice != "structural_occurrence_ascending"
    ):
        raise ValueError("REFINEMENT_POLICY")
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(artifact.request) is CompiledPreparedEmission:
        expected = compiled_source_requirements(artifact)
        if type(sources) is not tuple or tuple(
            requirement_state(s) for s in sources
        ) != tuple(requirement_state(s) for s in expected):
            raise ValueError("COMPILED_REFINEMENT_REQUIREMENTS")
    if output is None:
        output = prepare_output(artifact, binding=binding)
    verify_sources(sources, artifact.request.sources, family=artifact.request.family)
    refuse_block_reads(artifact)
    units, statement, prefix = lower(output, sources)
    value = RefinedQuery(
        artifact,
        output,
        policy,
        sources,
        tuple(requirement_state(s) for s in sources),
        units,
        statement,
        prefix,
        tuple((i, c) for i, c in enumerate(output.columns)),
    )
    verify_refinement(value)
    return value


def refuse_block_reads(artifact):
    """R2 has no proven row coordinates for an expression block read yet.

    The complete source closure, including every source reached only through
    such a read, is checked first; the refusal precedes any connection.
    """
    from pietto._project import project_sql_emission_rows as rows
    from pietto._project.project_sql_emission_ast import (
        SQLSelect,
        inline_body,
        row_value_roots,
    )
    from pietto._project.project_sql_emission_joins import JoinBody

    if type(artifact.ast) is SQLSelect:
        return
    if any(
        type(node) is rows.SQLBlockRead
        for root in row_value_roots(artifact.ast)
        for node in rows.value_nodes(root)
    ):
        raise ValueError("REFINEMENT_EXPRESSION_BLOCK_READ")
    # A LATERAL JOIN input (a let with capture lines) has no row coordinates.
    if any(
        type(unit) is JoinBody and inline_body(unit.inputs[1].producer)
        for unit in getattr(artifact.ast, "units", artifact.ast.bodies)
    ):
        raise ValueError("REFINEMENT_LATERAL_JOIN")


def _live_root(template, binding, *, reanchor):
    """Validate the current live template before an R2-only refinement."""
    from pietto._project.project_execution_binding_verification import verify_binding
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    verify_binding(binding)
    if binding.template is not template and not reanchor:
        raise ValueError("PUBLIC_R2_BINDING_TEMPLATE")
    current = template.artifact.request
    stored = binding.artifact.request
    if (
        type(current) is not CompiledPreparedEmission
        or type(stored) is not CompiledPreparedEmission
    ):
        raise ValueError("PUBLIC_R2_COMPILED_ROOT")
    current_root = current.verification.completed.root
    stored_root = stored.verification.completed.root
    if reanchor:
        if (
            current_root.expected_pin,
            current_root.accepted_producer,
            current_root.accepted_compatibility,
        ) != (
            stored_root.expected_pin,
            stored_root.accepted_producer,
            stored_root.accepted_compatibility,
        ):
            raise ValueError("PUBLIC_R2_RECOVERY_ROOT")
    elif binding.template is not template:
        raise ValueError("PUBLIC_R2_BINDING_TEMPLATE")
    return binding.artifact


def _computed_group_key(artifact):
    """Whether the statement groups by a value that its own `let:` computes.

    R2 does not take this shape yet (D70.05), so it is refused before any
    workspace or connection.
    """
    from pietto._project.project_compiled_schema import selected_relations

    root = artifact.request.verification.completed.root
    records = root.records
    for address in selected_relations(records, records[root.description.query]):
        if address.kind != "aggregate":
            continue
        aggregate = records[address]
        for key in aggregate.get("keys"):
            port = records[records[key].get("port")]
            # A later `where:` or `let:` stage carries the key on by a read;
            # the value is computed where that read chain ends.
            while port.get("source").kind == "read":
                port = records[records[port.get("source")].get("port")]
            unit = records[port.get("owner")]
            if (
                unit.address.kind == "row"
                and unit.get("stage") == "let"
                and unit.get("owner") == aggregate.get("owner")
            ):
                return True
    return False


def _live_shape(artifact, requirements):
    """The R2 checks of the template's own structure, which read no value;
    a policy refinement's complete requirements, or None."""
    from pietto._project.project_compiled_schema import Address

    records = artifact.request.verification.completed.root.records
    if _computed_group_key(artifact):
        raise ValueError("PUBLIC_R2_COMPUTED_GROUP_KEY")
    if any(address.kind == "values" for address in records):
        # A fixed VALUES row has no source position or token column, so no
        # recovery coordinate can identify it, even beside a physical source.
        raise ValueError("PUBLIC_R2_VALUES_COORDINATE_BASIS")
    if any(address.kind == "table_function" for address in records):
        # A generated series row has no source position or token column either.
        raise ValueError("PUBLIC_R2_TABLE_FUNCTION_COORDINATE_BASIS")
    policy = records[Address("policy", 0)]
    if policy.get("refinement") is not None:
        expected = compiled_source_requirements(artifact)
        if tuple(requirement_state(r) for r in requirements) != tuple(
            requirement_state(r) for r in expected
        ):
            raise ValueError("COMPILED_REFINEMENT_REQUIREMENTS")
        return expected
    verify_sources(
        requirements, artifact.request.sources, family=artifact.request.family
    )
    return None


def check_live_r2_refinement(template, requirements):
    """`prepare_live_r2_refinement`'s checks for a template without a binding,
    its shape refusals included; none reads a value."""
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(template.artifact.request) is not CompiledPreparedEmission:
        raise ValueError("PUBLIC_R2_COMPILED_ROOT")
    _live_shape(template.artifact, requirements)
    refuse_block_reads(template.artifact)


def prepare_live_r2_refinement(template, binding, requirements, *, reanchor=False):
    """Create the sole non-policy compiled refinement authority.

    ``template`` is retained by the public live entry.  Recovery may bind the
    stored copy only after its current caller template and trust records have
    already been checked, so it uses the narrow re-anchor case.
    """
    artifact = _live_root(template, binding, reanchor=reanchor)
    expected = _live_shape(artifact, requirements)
    output = None
    if binding.guarded is not None:
        from pietto._project.project_guard_preparation import prepare_guarded_output

        output = prepare_guarded_output(binding.guarded, binding=binding)
    if expected is not None:
        return (
            prepare_refinement(
                artifact,
                expected,
                policy=TieRefinement(),
                output=output,
                binding=binding,
            ),
            None,
        )
    value = _prepare_refinement(
        artifact,
        requirements,
        policy=TieRefinement(),
        output=output,
        binding=binding,
    )
    witness = LiveR2Witness(template, binding, value, requirements, reanchor)
    _LIVE_R2_WITNESSES.add(witness)
    return value, witness


def _prepare_refinement(artifact, sources, *, policy, output, binding):
    """The shared checked construction; public callers use the narrow wrapper."""
    from pietto._project.project_refinement_lowering import lower
    from pietto._project.project_refinement_verification import verify_refinement

    if (
        type(policy) is not TieRefinement
        or policy.choice != "structural_occurrence_ascending"
    ):
        raise ValueError("REFINEMENT_POLICY")
    if output is None:
        output = prepare_output(artifact, binding=binding)
    verify_sources(sources, artifact.request.sources, family=artifact.request.family)
    refuse_block_reads(artifact)
    units, statement, prefix = lower(output, sources)
    value = RefinedQuery(
        artifact,
        output,
        policy,
        sources,
        tuple(requirement_state(s) for s in sources),
        units,
        statement,
        prefix,
        tuple((i, c) for i, c in enumerate(output.columns)),
    )
    verify_refinement(value)
    return value


def verify_live_r2_witness(witness, request):
    """Reject constructed, copied, stale and cross-request R2 witnesses."""
    from pietto._project.project_execution_binding_verification import verify_binding

    if type(witness) is not LiveR2Witness or witness not in _LIVE_R2_WITNESSES:
        raise ValueError("PUBLIC_R2_WITNESS")
    verify_binding(witness.binding)
    if (
        witness.binding is not request.execution.binding
        or witness.refinement is not request.refinement
        or witness.refinement.output is not request.execution.output
        or witness.binding.artifact is not request.execution.artifact
        or tuple(witness.refinement.sources) != witness.requirements
    ):
        raise ValueError("PUBLIC_R2_WITNESS_CORRESPONDENCE")
    _live_root(witness.template, witness.binding, reanchor=witness.reanchored)
    verify_sources(
        witness.requirements,
        witness.binding.artifact.request.sources,
        family=witness.binding.artifact.request.family,
    )


def compiled_source_requirements(artifact):
    """Rebind the complete immutable descriptions to this fresh artifact only."""
    from pietto._project.project_compiled_schema import Address
    from pietto._project.project_sql_emission_contract import CompiledPreparedEmission

    if type(artifact.request) is not CompiledPreparedEmission:
        raise ValueError("COMPILED_REFINEMENT_ROOT")
    request = artifact.request
    records = request.verification.completed.root.records
    policy = records[Address("policy", 0)]
    if policy.get("refinement") != "structural_occurrence_ascending":
        raise ValueError("COMPILED_REFINEMENT_POLICY")
    from pietto._project.project_compiled_schema import selected_relations

    active = selected_relations(
        records, records[request.verification.completed.root.description.query]
    )
    sources = tuple(a for a in records if a.kind == "source" and a in active)
    if len(sources) != len(request.sources):
        raise ValueError("COMPILED_REFINEMENT_SOURCES")
    by_address = dict(zip(sources, request.sources, strict=True))
    requirements = tuple(
        RetainedSourceRequirement(
            by_address[r.get("source")],
            r.get("provider"),
            r.get("version"),
            r.get("revision"),
            r.get("registry")[0],
            r.get("registry")[1],
            r.get("definition"),
            r.get("tokens"),
            r.get("role"),
            r.get("guarantee"),
        )
        for r in (records[a] for a in policy.get("sources"))
    )
    verify_sources(requirements, request.sources, family=request.family)
    return requirements


@entry
def prepare_compiled_refinement(artifact, *, binding=None, guarded=None):
    if guarded is None:
        output = prepare_output(artifact, binding=binding)
    else:
        from pietto._project.project_guard_preparation import prepare_guarded_output

        if guarded.artifact is not artifact:
            raise ValueError("COMPILED_REFINEMENT_GUARD")
        output = prepare_guarded_output(guarded, binding=binding)
    return prepare_refinement(
        artifact,
        compiled_source_requirements(artifact),
        policy=TieRefinement(),
        output=output,
        binding=binding,
    )
