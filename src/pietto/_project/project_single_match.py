"""Explicit private single-match requests over exact completed matching roots."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import StrEnum

from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.project_completion import ProjectExistingEffectiveOutput
from pietto._project.project_current_join_inputs import ProjectCurrentMaterializedInput
from pietto._project.project_current_joins import ProjectCurrentBinaryJoin
from pietto._project.project_final_outputs import (
    ProjectCompletedEffectiveOutput,
    ProjectConcreteNoJoinReplay,
    ProjectCompletedSetOutput,
    ProjectEffectiveOutputCompletion,
    ProjectRelationLimit,
    _relation_limit,
)
from pietto._project.project_ir import ProjectIRJoinInputUseOccurrence
from pietto._project.project_ir_joins import (
    ProjectIRBinaryJoinOccurrence,
    ProjectIRConcreteJoinRegion,
)
from pietto._project.project_ir_operators import ProjectIRLogicalOperatorKind
from pietto._project.project_join_conditions import ProjectJoinCondition, _diagnostic
from pietto._project.project_joined_aggregation import ProjectJoinedAggregationMode
from pietto._project.project_joined_qualify import ProjectConcreteJoinedQualify
from pietto._project.project_relationship_match_guarantees import (
    ProjectRelationshipMaximumBound,
)
from pietto._project.project_relationship_paths import (
    ProjectRelationshipPath,
    ProjectRelationshipPathStep,
)
from pietto._project.project_relationship_uses import (
    ProjectConcreteJoinUse,
    ProjectNonConcreteJoinUse,
    ProjectJoinUse,
    ProjectTraversalStepUse,
)
from pietto.ast_nodes import AuthoredJoinKind, QueryDef, TableDef
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()


class ProjectSingleMatchScope(StrEnum):
    DIRECT_BINARY = "direct_binary"
    PATH_HOP = "path_hop"
    WHOLE_PATH = "whole_path"


class ProjectSingleMatchUnit(StrEnum):
    ACTUAL_MATCHED_BAG_OCCURRENCE = "actual_matched_bag_occurrence"


class ProjectSingleMatchState(StrEnum):
    PROVED = "proved"
    LEGAL_UNPROVED = "legal_unproved"
    INVALID = "invalid"


class ProjectSingleMatchProofKind(StrEnum):
    RELATIONSHIP = "relationship"
    REFINEMENT = "refinement"
    WHOLE_PATH = "whole_path"
    RIGHT_LIMIT = "right_limit"
    RIGHT_GLOBAL = "right_global"


type _Join = ProjectCurrentBinaryJoin | ProjectIRBinaryJoinOccurrence
type _InputPair = tuple[
    ProjectIRJoinInputUseOccurrence, ProjectIRJoinInputUseOccurrence
]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSingleMatchRequest:
    owner: ProjectDeclarationOccurrence
    use: ProjectJoinUse
    scope: ProjectSingleMatchScope = ProjectSingleMatchScope.DIRECT_BINARY
    unit: ProjectSingleMatchUnit = ProjectSingleMatchUnit.ACTUAL_MATCHED_BAG_OCCURRENCE
    path: ProjectRelationshipPath | None = None
    hop: ProjectRelationshipPathStep | ProjectTraversalStepUse | None = None
    condition: ProjectJoinCondition | None = None
    input_pairs: tuple[_InputPair, ...] | None = None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSingleMatchProof:
    kind: ProjectSingleMatchProofKind
    roots: tuple[object, ...] = field(repr=False)

    def __post_init__(self) -> None:
        if type(self.kind) is not ProjectSingleMatchProofKind or not self.roots:
            raise ValueError("Single-match proof requires typed retained evidence.")


def _same_pairs(left: tuple[_InputPair, ...], right: tuple[_InputPair, ...]) -> bool:
    return (
        type(left) is tuple
        and len(left) == len(right)
        and all(
            type(a) is tuple
            and len(a) == len(b) == 2
            and all(x is y for x, y in zip(a, b, strict=True))
            for a, b in zip(left, right, strict=True)
        )
    )


def _boundaries(
    root: ProjectEffectiveOutputCompletion, condition: ProjectJoinCondition
) -> tuple[_Join, ...]:
    regions = tuple(
        region for region in root.current_regions if region.ledger is condition.ledger
    )
    if regions:
        if len(regions) != 1:
            return ()
        return tuple(
            join
            for join in regions[0].joins
            if join.use
            is (
                condition.use
                if isinstance(join, ProjectCurrentBinaryJoin)
                else condition.effective_use
            )
        )
    if any(scope.ledger is condition.ledger for scope in root.input_scopes):
        return ()  # Current acquisition failure cannot fall back to historical output.
    return tuple(
        join
        for region in root.base.verification.root.join_regions.regions
        if isinstance(region, ProjectIRConcreteJoinRegion)
        and region.ledger is condition.ledger
        for join in region.joins
        if join.use is condition.effective_use
    )


def _right_proofs(
    root: ProjectEffectiveOutputCompletion, join: _Join
) -> tuple[ProjectSingleMatchProof, ...]:
    output = join.right_input.output
    if isinstance(output, ProjectCurrentMaterializedInput):
        entry = output.authority.entry
        if output.properties is not join.right_input:
            return ()
    else:
        entries = tuple(
            entry
            for entry in root.entries
            if isinstance(entry, ProjectExistingEffectiveOutput)
            and entry.properties is join.right_input
        )
        if len(entries) != 1:
            return ()
        entry = entries[0]
    if not any(entry is item for item in root.entries):
        return ()
    retained: list[object] = [entry, join.input_uses[1]]
    proofs: list[ProjectSingleMatchProof] = []
    # Only exact no-JOIN replay carries an upstream bound to this right input.
    while True:
        if isinstance(entry, ProjectCompletedSetOutput):
            break  # A generic set/grain label is not a Slice-7 cardinality proof.
        if isinstance(entry, ProjectCompletedEffectiveOutput):
            limit = entry.limit
            producer = entry.root
            aggregation = (
                producer.window_stage.input_aggregation
                if isinstance(producer, ProjectConcreteJoinedQualify)
                else producer
            )
            if aggregation.mode is ProjectJoinedAggregationMode.GLOBAL:
                proofs.append(
                    ProjectSingleMatchProof(
                        kind=ProjectSingleMatchProofKind.RIGHT_GLOBAL,
                        roots=(*retained, aggregation),
                    )
                )
        else:
            assert isinstance(entry, ProjectExistingEffectiveOutput)
            definition = entry.owner.definition
            limit = (
                _relation_limit(entry.owner)
                if isinstance(definition, (TableDef, QueryDef))
                else None
            )
            if isinstance(limit, ProjectRelationLimit):
                operators = tuple(
                    operator
                    for operator in entry.fragment.logical_stage.operators
                    if operator.kind is ProjectIRLogicalOperatorKind.LIMIT
                    and operator.node is entry.fragment.root
                )
                if len(operators) != 1:
                    limit = None
                else:
                    retained.append(operators[0])
        if isinstance(limit, ProjectRelationLimit) and limit.row_count_upper_bound <= 1:
            proofs.append(
                ProjectSingleMatchProof(
                    kind=ProjectSingleMatchProofKind.RIGHT_LIMIT,
                    roots=(*retained, limit),
                )
            )
        if (
            not isinstance(entry, ProjectCompletedEffectiveOutput)
            or not isinstance(entry.root, ProjectConcreteNoJoinReplay)
            or entry.root.mode is not ProjectJoinedAggregationMode.ABSENT
        ):
            break
        replay = entry.root
        entry = replay.upstream_entry
        if not any(entry is item for item in root.entries):
            break
        retained.extend((replay, entry))
    return tuple(proofs)


def _single_boundary_proofs(
    root: ProjectEffectiveOutputCompletion, condition: ProjectJoinCondition, join: _Join
) -> tuple[ProjectSingleMatchProof, ...]:
    proofs: list[ProjectSingleMatchProof] = []
    if isinstance(join, ProjectIRBinaryJoinOccurrence):
        guarantee = join.guarantee
        if guarantee.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE:
            proofs.append(
                ProjectSingleMatchProof(
                    kind=ProjectSingleMatchProofKind.RELATIONSHIP,
                    roots=(join.path_step, guarantee),
                )
            )
    else:
        refined, base = condition.refinement_guarantee, condition.base_guarantee
        if (
            refined is not None
            and refined.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        ):
            proofs.append(
                ProjectSingleMatchProof(
                    kind=ProjectSingleMatchProofKind.REFINEMENT,
                    roots=(condition, refined),
                )
            )
        elif (
            base is not None
            and base.maximum is ProjectRelationshipMaximumBound.AT_MOST_ONE
        ):
            proofs.append(
                ProjectSingleMatchProof(
                    kind=ProjectSingleMatchProofKind.RELATIONSHIP,
                    roots=(condition, base),
                )
            )
    return (*proofs, *_right_proofs(root, join))


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSingleMatchAssessment:
    root: ProjectEffectiveOutputCompletion = field(repr=False)
    request: ProjectSingleMatchRequest
    state: ProjectSingleMatchState = field(init=False)
    condition: ProjectJoinCondition | None = field(init=False, repr=False)
    joins: tuple[_Join, ...] = field(init=False, repr=False)
    input_pairs: tuple[_InputPair, ...] = field(init=False)
    proofs: tuple[ProjectSingleMatchProof, ...] = field(init=False, repr=False)
    problems: tuple[str, ...] = field(init=False)
    diagnostic: Diagnostic | None = field(init=False)
    downstream_enforcement_required: bool = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.root) is not ProjectEffectiveOutputCompletion
            or type(self.request) is not ProjectSingleMatchRequest
        ):
            raise TypeError(
                "Single-match assessment requires exact root and request types."
            )
        request = self.request
        authority = self.root.operative_conditions
        if authority is None:
            raise ValueError("Single-match root requires operative conditions.")
        problems: list[str] = []
        if not any(request.owner is owner for owner in self.root.owners):
            problems.append("foreign owner")
        if type(request.scope) is not ProjectSingleMatchScope:
            problems.append("unsupported scope")
        if request.unit is not ProjectSingleMatchUnit.ACTUAL_MATCHED_BAG_OCCURRENCE:
            problems.append("unsupported counting unit")
        candidates = tuple(
            condition for condition in authority.entries if condition.use is request.use
        )
        condition = candidates[0] if len(candidates) == 1 else None
        joins: tuple[_Join, ...] = ()
        if condition is None:
            problems.append("foreign JOIN use")
        elif condition.use.owner is not request.owner:
            problems.append("owner/use mismatch")
        elif request.condition is not None and request.condition is not condition:
            problems.append("foreign or stale condition")
        elif not condition.ready or not any(
            request.owner is owner for owner in self.root.schedule
        ):
            problems.append("matching operation unavailable")
        elif condition.use.kind is AuthoredJoinKind.CROSS:
            problems.append("CROSS has no matching boundary")
        else:
            joins = _boundaries(self.root, condition)
            if not joins:
                problems.append("no completed matching boundary")
        if joins and condition is not None:
            path = condition.effective_use.path
            if request.scope is ProjectSingleMatchScope.DIRECT_BINARY:
                if (
                    len(joins) != 1
                    or request.path is not None
                    or request.hop is not None
                ):
                    problems.append("direct-binary scope requires one exact boundary")
            elif request.scope is ProjectSingleMatchScope.WHOLE_PATH:
                if (
                    path is None
                    or request.path is not path
                    or request.hop is not None
                    or len(joins) != len(path.steps)
                ):
                    problems.append(
                        "whole-path scope requires the complete exact path/use"
                    )
            elif request.scope is ProjectSingleMatchScope.PATH_HOP:
                if isinstance(request.hop, ProjectRelationshipPathStep):
                    selected = tuple(
                        join
                        for join in joins
                        if isinstance(join, ProjectIRBinaryJoinOccurrence)
                        and join.path_step is request.hop
                    )
                    if path is None or request.path is not path:
                        problems.append("foreign hop path")
                elif isinstance(request.hop, ProjectTraversalStepUse):
                    positions = tuple(
                        i
                        for i, hop in enumerate(condition.use.step_uses)
                        if hop is request.hop
                    )
                    selected = (
                        (joins[positions[0]],)
                        if len(positions) == 1 and positions[0] < len(joins)
                        else ()
                    )
                    if request.path is not None and request.path is not path:
                        problems.append("foreign hop path")
                else:
                    selected = ()
                if len(selected) != 1:
                    problems.append("foreign or missing path hop")
                joins = selected
        pairs = tuple((join.input_uses[0], join.input_uses[1]) for join in joins)
        if request.input_pairs is not None and not _same_pairs(
            request.input_pairs, pairs
        ):
            problems.append("foreign or reversed input roles")
        proofs: tuple[ProjectSingleMatchProof, ...] = ()
        if not problems and condition is not None:
            per_join = tuple(
                _single_boundary_proofs(self.root, condition, join) for join in joins
            )
            if request.scope is ProjectSingleMatchScope.WHOLE_PATH:
                if all(per_join):
                    proofs = (
                        ProjectSingleMatchProof(
                            kind=ProjectSingleMatchProofKind.WHOLE_PATH,
                            roots=(
                                request.path,
                                *joins,
                                *tuple(proof for group in per_join for proof in group),
                            ),
                        ),
                    )
            else:
                proofs = per_join[0]
        state = (
            ProjectSingleMatchState.INVALID
            if problems
            else ProjectSingleMatchState.PROVED
            if proofs
            else ProjectSingleMatchState.LEGAL_UNPROVED
        )
        diagnostic = None
        if state is not ProjectSingleMatchState.PROVED:
            message = (
                "Invalid single-match request: " + "; ".join(problems) + "."
                if problems
                else "Single-match requirement is not statically proved; downstream enforcement remains required."
            )
            code = "PIE-S2338" if problems else "PIE-S2337"
            severity = Severity.ERROR if problems else Severity.WARNING
            diagnostic = (
                replace(
                    _diagnostic(request.use.clause.span, message, code=code),
                    severity=severity,
                )
                if isinstance(
                    request.use, (ProjectConcreteJoinUse, ProjectNonConcreteJoinUse)
                )
                else Diagnostic(
                    code=code,
                    severity=severity,
                    message=message,
                    location=SourceLocation(path=None, line=1, column=1),
                )
            )
        for name, value in (
            ("state", state),
            ("condition", condition),
            ("joins", joins),
            ("input_pairs", pairs),
            ("proofs", proofs),
            ("problems", tuple(problems)),
            ("diagnostic", diagnostic),
            (
                "downstream_enforcement_required",
                state is ProjectSingleMatchState.LEGAL_UNPROVED,
            ),
        ):
            object.__setattr__(self, name, value)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSingleMatchSet:
    root: ProjectEffectiveOutputCompletion = field(repr=False)
    requests: tuple[ProjectSingleMatchRequest, ...] = ()
    entries: tuple[ProjectSingleMatchAssessment, ...] = field(init=False)
    obligations: tuple[ProjectSingleMatchAssessment, ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        if (
            type(self.root) is not ProjectEffectiveOutputCompletion
            or type(self.requests) is not tuple
            or any(
                type(request) is not ProjectSingleMatchRequest
                for request in self.requests
            )
        ):
            raise TypeError(
                "Single-match set requires exact root and request occurrences."
            )
        authority = self.root.operative_conditions
        if authority is None:
            raise ValueError("Single-match set requires operative conditions.")
        # Source/use authority order; same-use requests retain caller order.
        ordered = tuple(
            request
            for condition in authority.entries
            for request in self.requests
            if request.use is condition.use
        )
        ordered += tuple(
            request
            for request in self.requests
            if not any(request.use is condition.use for condition in authority.entries)
        )
        assessments: dict[int, ProjectSingleMatchAssessment] = {}
        entries: list[ProjectSingleMatchAssessment] = []
        diagnostics: list[Diagnostic] = []
        for request in ordered:
            entry = assessments.get(id(request))
            if entry is None:
                entry = ProjectSingleMatchAssessment(root=self.root, request=request)
                assessments[id(request)] = entry
                if entry.diagnostic is not None:
                    diagnostics.append(entry.diagnostic)
            entries.append(entry)
        object.__setattr__(self, "entries", tuple(entries))
        object.__setattr__(
            self,
            "obligations",
            tuple(
                entry
                for entry in entries
                if entry.state is not ProjectSingleMatchState.INVALID
            ),
        )
        object.__setattr__(self, "diagnostics", tuple(diagnostics))


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSingleMatchRequest:
    """One resolved request identity owned by a compiled input, with no AST."""

    root: object = field(repr=False)
    address: object
    owner: object = field(repr=False)
    use: object = field(repr=False)
    scope: ProjectSingleMatchScope
    unit: ProjectSingleMatchUnit
    path: object = field(repr=False)
    hop: tuple | None
    input_pairs: tuple = field(repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSingleMatchProof:
    kind: ProjectSingleMatchProofKind
    boundaries: tuple = field(repr=False)
    roots: tuple = field(repr=False)
    children: tuple = field(default=(), repr=False)


@dataclass(frozen=True, slots=True, eq=False)
class CompiledSingleMatchAssessment:
    request: CompiledSingleMatchRequest = field(repr=False)
    joins: tuple = field(repr=False)
    input_pairs: tuple = field(repr=False)
    proofs: tuple[CompiledSingleMatchProof, ...] = field(repr=False)
    state: ProjectSingleMatchState

    @property
    def downstream_enforcement_required(self):
        return self.state is ProjectSingleMatchState.LEGAL_UNPROVED


def compiled_requests(root, declarations):
    from pietto._project.project_compiled_schema import CompiledError
    from pietto._project.model import CompiledProjectInput

    if type(root) is not CompiledProjectInput:
        raise CompiledError("COMPILED_REQUEST_ROOT")
    owners = {d.address: d for d in declarations}
    records = root.records
    unique = {}
    for address in records[root.description.query].get("requests"):
        if address not in unique:
            record = records[address]
            unique[address] = CompiledSingleMatchRequest(
                root,
                address,
                owners[record.get("owner")],
                records[record.get("use")],
                ProjectSingleMatchScope(record.get("scope")),
                ProjectSingleMatchUnit(record.get("unit")),
                None if record.get("path") is None else records[record.get("path")],
                record.get("hop"),
                record.get("pairs"),
            )
    return tuple(unique[a] for a in records[root.description.query].get("requests"))


def _compiled_right_bounds(ir, address):
    """Original RIGHT_GLOBAL/RIGHT_LIMIT applicability, over resolved stages."""
    records = ir.completed.root.records
    retained, proofs, seen = [], [], set()
    while address.kind != "source":
        if address in seen:
            raise ValueError("COMPILED_CARDINALITY_CYCLE")
        owner = records[address].get("owner")
        limits, global_stage = [], None
        stop = False
        while address.kind != "source" and records[address].get("owner") == owner:
            if address in seen:
                raise ValueError("COMPILED_CARDINALITY_CYCLE")
            seen.add(address)
            record = records[address]
            retained.append(record)
            if address.kind == "result" and record.get("limit") is not None:
                if record.get("limit") <= 1:
                    limits.append(record)
            if address.kind == "aggregate":
                global_stage = record if record.get("mode") == "global" else None
                stop = True
                break
            if address.kind in ("join", "set"):
                stop = True
                break
            address = record.get("input")
        if global_stage is not None:
            proofs.append((ProjectSingleMatchProofKind.RIGHT_GLOBAL, tuple(retained)))
        proofs.extend(
            (
                ProjectSingleMatchProofKind.RIGHT_LIMIT,
                (*retained, records[limit.get("limit_literal")]),
            )
            for limit in limits
        )
        if stop:
            break
    return tuple(proofs)


def compiled_boundary_proofs(ir, address):
    from pietto._project.project_relationship_match_guarantees import (
        resolved_matching_keys,
    )

    records = ir.completed.root.records
    by_address = {op.record.address: op for op in ir.operators}
    join = records[address]
    right_use = records[join.get("inputs")[1]]
    right = by_address[right_use.get("producer")].properties.relational
    proofs = []
    if join.get("equalities"):
        positions = tuple(
            records[records[records[a].get("right")].get("port")].get("ordinal")
            for a in join.get("equalities")
        )
        matched = tuple(
            c
            for c in right.value_classes
            if any(m.field_position in positions for m in c.members)
        )
        keys = resolved_matching_keys(right.keys, matched)
        if keys:
            proofs.append(
                CompiledSingleMatchProof(
                    ProjectSingleMatchProofKind.REFINEMENT
                    if join.get("predicate") is not None
                    else ProjectSingleMatchProofKind.RELATIONSHIP,
                    (address,),
                    (
                        join,
                        right_use,
                        *keys,
                        *tuple(records[a] for a in join.get("equalities")),
                    ),
                )
            )
    for kind, roots in _compiled_right_bounds(ir, right_use.get("producer")):
        proofs.append(CompiledSingleMatchProof(kind, (address,), (right_use, *roots)))
    return tuple(proofs)


def assess_compiled_requests(ir):
    """Derive fresh proof state from complete current typed properties."""
    requests = ir.completed.single_match_requests
    records = ir.completed.root.records
    ordered = tuple(
        sorted(
            enumerate(requests), key=lambda item: (item[1].use.get("position"), item[0])
        )
    )
    assessments = {}
    for _position, request in ordered:
        if request.address in assessments:
            continue
        boundaries = request.use.get("boundaries")
        if request.scope is ProjectSingleMatchScope.PATH_HOP:
            boundaries = (boundaries[request.hop[1]],)
        pairs = tuple(records[a].get("inputs") for a in boundaries)
        if pairs != request.input_pairs:
            raise ValueError("COMPILED_REQUEST_INPUT_PAIRS")
        per_boundary = tuple(compiled_boundary_proofs(ir, a) for a in boundaries)
        if request.scope is ProjectSingleMatchScope.WHOLE_PATH:
            children = tuple(p for group in per_boundary for p in group)
            proofs = (
                (
                    CompiledSingleMatchProof(
                        ProjectSingleMatchProofKind.WHOLE_PATH,
                        boundaries,
                        (request.path, *tuple(records[a] for a in boundaries)),
                        children,
                    ),
                )
                if all(per_boundary)
                else ()
            )
        else:
            proofs = per_boundary[0]
        assessments[request.address] = CompiledSingleMatchAssessment(
            request,
            boundaries,
            pairs,
            proofs,
            ProjectSingleMatchState.PROVED
            if proofs
            else ProjectSingleMatchState.LEGAL_UNPROVED,
        )
    return tuple(assessments[request.address] for _, request in ordered)
