"""Exact original match subjects and private guard/data statement identities."""

from dataclasses import dataclass, field
from typing import Any

from pietto._project.project_guard_preparation import (
    GuardedPreparation,
    prepare_guarded_output,
    verify_preparation,
)
from pietto._project.project_sql_emission_joins import JoinBody

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, eq=False)
class GuardSubject:
    obligation: Any = field(repr=False)
    request_position: int
    boundary_position: int
    unit: Any = field(repr=False)
    inputs: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class GuardProgram:
    preparation: GuardedPreparation = field(repr=False)
    output: Any = field(repr=False)
    refinement: Any = field(repr=False)
    subjects: tuple[GuardSubject, ...] = field(repr=False)
    prefix: str
    source_reads: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class GuardControl:
    kind: str
    value: int


@dataclass(frozen=True, slots=True, eq=False)
class GuardStatement:
    program: GuardProgram = field(repr=False)
    kind: str
    subjects: tuple[GuardSubject, ...] = field(repr=False)
    controls: tuple[GuardControl, ...]


@dataclass(frozen=True, slots=True, eq=False)
class GuardParameterUse:
    domain: str
    owner: Any = field(repr=False)
    index: int
    value: Any = field(repr=False)
    original: Any = field(default=None, repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class NativeGuardStatement:
    statement: GuardStatement = field(repr=False)
    sql: bytes = field(repr=False)
    uses: tuple[GuardParameterUse, ...] = field(repr=False)
    arguments: tuple = field(repr=False)


def prepare_program(preparation, *, binding=None, refinement=None):
    from pietto._project.project_result_output import source_read_columns
    from pietto._project.project_guard_verification import verify_program

    obligations = verify_preparation(preparation)
    output = (
        prepare_guarded_output(preparation, binding=binding)
        if refinement is None
        else refinement.output
    )
    subjects = []
    for i, obligation in enumerate(obligations):
        for j, reference in enumerate(obligation.joins):
            matches = tuple(
                u
                for u in output.units
                if type(u) is JoinBody and u.join.ref is reference
            )
            if len(matches) != 1:
                raise ValueError("GUARD_MATCHING_BOUNDARY")
            unit = matches[0]
            subjects.append(GuardSubject(obligation, i, j, unit, unit.inputs))
    request = preparation.artifact.request
    reserved = {f.column for s in request.sources for f in s.fields}
    reserved.update(c.label for unit in output.units for c in unit.columns)
    reserved.update(
        u.symbol.name for u in output.units if getattr(u, "symbol", None) is not None
    )
    if request.family == "mysql":
        reserved = {s.casefold() for s in reserved}
    prefix, suffix = "__pietto_guard_", 0
    while any(n.startswith(prefix) for n in reserved):
        suffix += 1
        prefix = "__pietto_guard_" + str(suffix) + "_"
    program = GuardProgram(
        preparation,
        output,
        refinement,
        tuple(subjects),
        prefix,
        source_read_columns(output),
    )
    verify_program(program)
    return program


def statement_for(program, kind, *, subjects=None):
    from pietto._project.project_guard_verification import verify_program

    verify_program(program)
    if kind not in ("guard", "combined", "data"):
        raise ValueError("GUARD_STATEMENT_KIND")
    selected = (
        tuple(s for s in program.subjects if not pure_static_proofs(program, s))
        if subjects is None
        else subjects
    )
    # Syntax construction is not live permission to omit any other subject.
    # The owning runtime must separately prove its complete disposition vector.
    if type(selected) is not tuple or any(
        not any(s is expected for expected in program.subjects) for s in selected
    ):
        raise ValueError("GUARD_STATEMENT_SUBJECT")
    controls = (
        GuardControl("witness_limit", 1),
        GuardControl("second_match_offset", 1),
    )
    return GuardStatement(program, kind, selected, controls)


def pure_static_proofs(program, subject):
    """Only upstream-verified source-independent bounds need no native evidence."""
    from pietto._project.project_single_match import ProjectSingleMatchProofKind

    return tuple(
        proof
        for proof in program.preparation.artifact.request.plan.single_match_proofs
        if proof.obligation is subject.obligation.ref
        and any(join is subject.unit.join.ref for join in proof.joins)
        and proof.source.source.kind
        in (
            ProjectSingleMatchProofKind.RIGHT_LIMIT,
            ProjectSingleMatchProofKind.RIGHT_GLOBAL,
        )
    )
