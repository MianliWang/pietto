"""Private strict/lax value-FD facts and targeted strict closure."""

from __future__ import annotations

from collections import deque
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from heapq import heappop, heappush
from types import MappingProxyType

from pietto._project.model import ProjectRelationRowSchemaStatus
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleAttributionFactSet,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
    _declaration_identity,
)
from pietto._project.module_catalog import ProjectModuleCatalogSet
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)
from pietto._project.project_relationship_conditions import (
    ProjectExactRowOutputConstraintScope,
    ProjectRelationshipConstraintScopeKind,
)
from pietto._project.project_row_keys import (
    ProjectCandidateKeyFact,
    ProjectCandidateKeyIdentity,
    ProjectConstraintEnforcementPosture,
    ProjectConstraintEvidenceOrigin,
    ProjectConstraintEvidenceTrust,
    ProjectRowKeySet,
    ProjectRowUniquenessStrength,
)
from pietto.ast_nodes import SourceDef

__all__: tuple[str, ...] = ()


def _require_fields(
    values: object,
    *,
    owner: ProjectDeclarationOccurrenceIdentity,
    label: str,
    allow_empty: bool,
) -> tuple[ProjectModuleRowFieldIdentity, ...]:
    if type(values) is not tuple or any(
        type(value) is not ProjectModuleRowFieldIdentity
        or value.kind is not ProjectModuleRowFieldKind.SOURCE_FIELD
        or value.owner != owner
        for value in values
    ):
        raise TypeError(f"{label} require exact source-output field identities.")
    fields = values
    if not allow_empty and not fields:
        raise ValueError(f"{label} cannot be empty.")
    positions = tuple(value.field_position for value in fields)
    if len(set(fields)) != len(fields) or any(
        left >= right for left, right in zip(positions, positions[1:], strict=False)
    ):
        raise ValueError(f"{label} must follow exact output order without repeats.")
    return fields


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDFieldUniverse:
    """One exact source-row field universe in output order."""

    scope: ProjectExactRowOutputConstraintScope
    fields: tuple[ProjectModuleRowFieldIdentity, ...]

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectExactRowOutputConstraintScope or (
            type(self.scope.relation.owner.definition) is not SourceDef
        ):
            raise TypeError("Value-FD universe requires one exact source output.")
        exact_fields = _require_fields(
            self.fields,
            owner=self.scope.owner,
            label="Value-FD universe fields",
            allow_empty=True,
        )
        schema = self.scope.relation.state.schema
        assert schema is not None
        if tuple(field.field_position for field in exact_fields) != tuple(
            range(len(exact_fields))
        ) or tuple(field.name for field in exact_fields) != tuple(schema.fields):
            raise ValueError("Value-FD universe must retain complete output order.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDIdentity:
    """One exact directional value-FD theorem identity."""

    scope: ProjectExactRowOutputConstraintScope
    determinants: tuple[ProjectModuleRowFieldIdentity, ...]
    dependents: tuple[ProjectModuleRowFieldIdentity, ...]
    strength: ProjectRowUniquenessStrength
    premise: ProjectCandidateKeyIdentity

    def __post_init__(self) -> None:
        if type(self.scope) is not ProjectExactRowOutputConstraintScope or (
            type(self.scope.relation.owner.definition) is not SourceDef
        ):
            raise TypeError("Value FD requires one exact source-output scope.")
        if type(self.premise) is not ProjectCandidateKeyIdentity or (
            self.premise.owner != self.scope.owner
        ):
            raise TypeError("Value FD requires one exact candidate-key premise.")
        determinants = _require_fields(
            self.determinants,
            owner=self.scope.owner,
            label="Value-FD determinants",
            allow_empty=False,
        )
        dependents = _require_fields(
            self.dependents,
            owner=self.scope.owner,
            label="Value-FD dependents",
            allow_empty=False,
        )
        if determinants != self.premise.determinants:
            raise ValueError("Value-FD determinants must retain the key premise.")
        if type(self.strength) is not ProjectRowUniquenessStrength or (
            self.strength is not self.premise.strength
        ):
            raise ValueError("Value-FD strength must retain the key premise.")
        if set(determinants) & set(dependents):
            raise ValueError("Non-trivial value FDs forbid self-dependencies.")
        schema = self.scope.relation.state.schema
        assert schema is not None
        schema_names = tuple(schema.fields)
        if any(
            field.field_position >= len(schema_names)
            or schema_names[field.field_position] != field.name
            for field in (*determinants, *dependents)
        ):
            raise ValueError("Value-FD fields must belong to the exact row output.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDFact:
    """One trusted derived theorem with its exact candidate-key premise."""

    identity: ProjectValueFDIdentity
    premise: ProjectCandidateKeyFact = field(
        repr=False,
        compare=False,
        hash=False,
    )
    origin: ProjectConstraintEvidenceOrigin
    trust: ProjectConstraintEvidenceTrust
    enforcement: ProjectConstraintEnforcementPosture

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectValueFDIdentity:
            raise TypeError("Value-FD fact requires an exact identity.")
        if type(self.premise) is not ProjectCandidateKeyFact or (
            self.premise.identity is not self.identity.premise
        ):
            raise ValueError("Value-FD fact requires its exact candidate-key premise.")
        if (
            self.origin is not ProjectConstraintEvidenceOrigin.DERIVED_THEOREM
            or self.trust is not ProjectConstraintEvidenceTrust.TRUSTED
            or self.enforcement
            is not ProjectConstraintEnforcementPosture.MODEL_CONTRACT
        ):
            raise ValueError("Slice 5 constructs trusted model-derived FDs only.")


def _field_mask(
    universe: ProjectValueFDFieldUniverse,
    fields: tuple[ProjectModuleRowFieldIdentity, ...],
) -> int:
    positions = {field: position for position, field in enumerate(universe.fields)}
    try:
        return sum(1 << positions[field] for field in fields)
    except KeyError as error:
        raise ValueError("Value-FD field is outside the exact universe.") from error


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCompiledValueFDRule:
    """One snapshot-local compiled coordinate for a normative FD fact."""

    fact: ProjectValueFDFact = field(repr=False, compare=False, hash=False)
    lhs_mask: int
    rhs_mask: int

    def __post_init__(self) -> None:
        if type(self.fact) is not ProjectValueFDFact:
            raise TypeError("Compiled value-FD rule requires one normative fact.")
        if (
            type(self.lhs_mask) is not int
            or type(self.rhs_mask) is not int
            or self.lhs_mask <= 0
            or self.rhs_mask <= 0
            or self.lhs_mask & self.rhs_mask
        ):
            raise ValueError(
                "Compiled value-FD masks must be non-trivial and disjoint."
            )


def _compiled_rule(
    universe: ProjectValueFDFieldUniverse,
    fact: ProjectValueFDFact,
) -> ProjectCompiledValueFDRule:
    if fact.identity.scope is not universe.scope:
        raise ValueError("Compiled value FD requires the exact field universe.")
    return ProjectCompiledValueFDRule(
        fact=fact,
        lhs_mask=_field_mask(universe, fact.identity.determinants),
        rhs_mask=_field_mask(universe, fact.identity.dependents),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDIndex:
    """Immutable direct-FD masks and strict-rule incident index."""

    universe: ProjectValueFDFieldUniverse
    facts: tuple[ProjectValueFDFact, ...]
    positions: Mapping[ProjectModuleRowFieldIdentity, int] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    strict_rules: tuple[ProjectCompiledValueFDRule, ...] = ()
    lax_rules: tuple[ProjectCompiledValueFDRule, ...] = ()
    strict_incidents: tuple[tuple[int, ...], ...] = ()

    def __post_init__(self) -> None:
        if type(self.universe) is not ProjectValueFDFieldUniverse:
            raise TypeError("Value-FD index requires one exact field universe.")
        if type(self.facts) is not tuple or any(
            type(fact) is not ProjectValueFDFact for fact in self.facts
        ):
            raise TypeError("Value-FD index facts must be an exact tuple.")
        expected_positions = {
            field: position for position, field in enumerate(self.universe.fields)
        }
        if dict(self.positions) != expected_positions:
            raise ValueError("Value-FD dense positions must match exact output order.")
        object.__setattr__(self, "positions", MappingProxyType(expected_positions))
        expected_strict = tuple(
            _compiled_rule(self.universe, fact)
            for fact in self.facts
            if fact.identity.strength is ProjectRowUniquenessStrength.STRICT
        )
        expected_lax = tuple(
            _compiled_rule(self.universe, fact)
            for fact in self.facts
            if fact.identity.strength is ProjectRowUniquenessStrength.LAX
        )
        for supplied, expected, label in (
            (self.strict_rules, expected_strict, "STRICT"),
            (self.lax_rules, expected_lax, "LAX"),
        ):
            if (
                type(supplied) is not tuple
                or len(supplied) != len(expected)
                or any(
                    actual.fact is not expected_rule.fact
                    or actual.lhs_mask != expected_rule.lhs_mask
                    or actual.rhs_mask != expected_rule.rhs_mask
                    for actual, expected_rule in zip(supplied, expected, strict=True)
                )
            ):
                raise ValueError(f"Compiled {label} rules must retain normative order.")
        incident_lists: list[list[int]] = [list() for _field in self.universe.fields]
        for rule_position, rule in enumerate(expected_strict):
            for field_position in range(len(self.universe.fields)):
                if rule.lhs_mask & (1 << field_position):
                    incident_lists[field_position].append(rule_position)
        expected_incidents = tuple(tuple(values) for values in incident_lists)
        if self.strict_incidents != expected_incidents:
            raise ValueError("STRICT incidents must retain exact direct-rule order.")


def _compile_project_value_fd_index(
    universe: ProjectValueFDFieldUniverse,
    facts: tuple[ProjectValueFDFact, ...],
) -> ProjectValueFDIndex:
    """Compile typed direct facts into snapshot-local masks."""

    if type(universe) is not ProjectValueFDFieldUniverse:
        raise TypeError("Value-FD compilation requires an exact universe.")
    if type(facts) is not tuple or any(
        type(fact) is not ProjectValueFDFact for fact in facts
    ):
        raise TypeError("Value-FD compilation requires exact normative facts.")
    rules = tuple(_compiled_rule(universe, fact) for fact in facts)
    strict_rules = tuple(
        rule
        for rule in rules
        if rule.fact.identity.strength is ProjectRowUniquenessStrength.STRICT
    )
    lax_rules = tuple(
        rule
        for rule in rules
        if rule.fact.identity.strength is ProjectRowUniquenessStrength.LAX
    )
    incident_lists: list[list[int]] = [list() for _field in universe.fields]
    for rule_position, rule in enumerate(strict_rules):
        for field_position in range(len(universe.fields)):
            if rule.lhs_mask & (1 << field_position):
                incident_lists[field_position].append(rule_position)
    return ProjectValueFDIndex(
        universe=universe,
        facts=facts,
        positions={field: position for position, field in enumerate(universe.fields)},
        strict_rules=strict_rules,
        lax_rules=lax_rules,
        strict_incidents=tuple(tuple(values) for values in incident_lists),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDFieldSet:
    """One typed field set plus its universe-local computational mask."""

    universe: ProjectValueFDFieldUniverse
    fields: tuple[ProjectModuleRowFieldIdentity, ...]
    mask: int = field(init=False)

    def __post_init__(self) -> None:
        if type(self.universe) is not ProjectValueFDFieldUniverse:
            raise TypeError("Value-FD field set requires one exact universe.")
        exact_fields = _require_fields(
            self.fields,
            owner=self.universe.scope.owner,
            label="Value-FD field set",
            allow_empty=True,
        )
        mask = _field_mask(self.universe, exact_fields)
        expected = tuple(
            field
            for field in self.universe.fields
            if mask & (1 << field.field_position)
        )
        if exact_fields != expected:
            raise ValueError("Value-FD field set must follow exact universe order.")
        object.__setattr__(self, "mask", mask)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectStrictClosureProofStep:
    """The first normative direct STRICT fact deriving exact new fields."""

    fact: ProjectValueFDFact = field(repr=False, compare=False, hash=False)
    derived_fields: tuple[ProjectModuleRowFieldIdentity, ...]

    def __post_init__(self) -> None:
        if type(self.fact) is not ProjectValueFDFact or (
            self.fact.identity.strength is not ProjectRowUniquenessStrength.STRICT
        ):
            raise TypeError("STRICT proof step requires one direct STRICT FD.")
        fields = _require_fields(
            self.derived_fields,
            owner=self.fact.identity.scope.owner,
            label="STRICT proof derived fields",
            allow_empty=False,
        )
        if any(field not in self.fact.identity.dependents for field in fields):
            raise ValueError("STRICT proof step must derive direct dependent fields.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectStrictClosureResult:
    """One targeted strict fixed point and a single deterministic witness."""

    seed: ProjectValueFDFieldSet
    fields: ProjectValueFDFieldSet
    witness: tuple[ProjectStrictClosureProofStep, ...] = ()

    def __post_init__(self) -> None:
        if (
            type(self.seed) is not ProjectValueFDFieldSet
            or type(self.fields) is not ProjectValueFDFieldSet
            or self.seed.universe is not self.fields.universe
            or self.seed.mask & self.fields.mask != self.seed.mask
        ):
            raise ValueError("STRICT closure must retain its exact seed universe.")
        if type(self.witness) is not tuple or any(
            type(step) is not ProjectStrictClosureProofStep
            or step.fact.identity.scope is not self.seed.universe.scope
            for step in self.witness
        ):
            raise ValueError("STRICT closure witness must use exact direct facts.")
        replay_mask = self.seed.mask
        for step in self.witness:
            lhs_mask = _field_mask(
                self.seed.universe,
                step.fact.identity.determinants,
            )
            if lhs_mask & replay_mask != lhs_mask:
                raise ValueError("STRICT closure witness requires satisfied premises.")
            new_mask = (
                _field_mask(self.seed.universe, step.fact.identity.dependents)
                & ~replay_mask
            )
            expected_fields = tuple(
                field
                for position, field in enumerate(self.seed.universe.fields)
                if new_mask & (1 << position)
            )
            if step.derived_fields != expected_fields:
                raise ValueError("STRICT closure witness must retain exact new fields.")
            replay_mask |= new_mask
        if replay_mask != self.fields.mask:
            raise ValueError(
                "STRICT closure witness must replay the exact fixed point."
            )


class ProjectValueFDDeterminationStatus(StrEnum):
    """Proof availability; NOT_PROVEN is not a counterexample."""

    PROVEN = "proven"
    NOT_PROVEN = "not_proven"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDDeterminationResult:
    """One typed targeted strict-determination answer."""

    seed: ProjectValueFDFieldSet
    targets: ProjectValueFDFieldSet
    closure: ProjectStrictClosureResult
    status: ProjectValueFDDeterminationStatus

    def __post_init__(self) -> None:
        if (
            type(self.seed) is not ProjectValueFDFieldSet
            or type(self.targets) is not ProjectValueFDFieldSet
            or type(self.closure) is not ProjectStrictClosureResult
            or self.seed.universe is not self.targets.universe
            or self.closure.seed is not self.seed
        ):
            raise ValueError("Determination query requires one exact field universe.")
        expected = (
            ProjectValueFDDeterminationStatus.PROVEN
            if self.targets.mask & self.closure.fields.mask == self.targets.mask
            else ProjectValueFDDeterminationStatus.NOT_PROVEN
        )
        if type(self.status) is not ProjectValueFDDeterminationStatus or (
            self.status is not expected
        ):
            raise ValueError("Determination status must match the strict fixed point.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDBasis:
    """Normative direct FD facts plus one derived compiled index."""

    universe: ProjectValueFDFieldUniverse
    facts: tuple[ProjectValueFDFact, ...]
    index: ProjectValueFDIndex

    def __post_init__(self) -> None:
        if type(self.universe) is not ProjectValueFDFieldUniverse:
            raise TypeError("Value-FD basis requires one exact field universe.")
        if type(self.facts) is not tuple or any(
            type(fact) is not ProjectValueFDFact for fact in self.facts
        ):
            raise TypeError("Value-FD basis facts must be an exact tuple.")
        if type(self.index) is not ProjectValueFDIndex or (
            self.index.universe is not self.universe
            or len(self.index.facts) != len(self.facts)
            or any(
                indexed is not fact
                for indexed, fact in zip(self.index.facts, self.facts, strict=True)
            )
        ):
            raise ValueError("Value-FD basis requires its exact compiled projection.")


def _concrete_source_rows(
    row_keys: ProjectRowKeySet,
) -> tuple[
    tuple[
        ProjectDeclarationOccurrenceIdentity,
        ProjectModuleRelationSemanticFacts,
        tuple[ProjectModuleRowFieldIdentity, ...],
    ],
    ...,
]:
    semantic_result = row_keys.semantic_result
    catalogs = semantic_result.module_catalogs
    semantic_facts = semantic_result.module_semantic_facts
    attribution = semantic_result.module_attribution_facts
    if (
        type(catalogs) is not ProjectModuleCatalogSet
        or type(semantic_facts) is not ProjectModuleSemanticFactSet
        or type(attribution) is not ProjectModuleAttributionFactSet
    ):
        raise ValueError("Value FDs require exact existing Project sidecars.")
    rows: list[
        tuple[
            ProjectDeclarationOccurrenceIdentity,
            ProjectModuleRelationSemanticFacts,
            tuple[ProjectModuleRowFieldIdentity, ...],
        ]
    ] = []
    for catalog in catalogs.catalogs:
        for occurrence in catalog.occurrences:
            if type(occurrence.definition) is not SourceDef:
                continue
            semantic_bucket = semantic_facts.find_owner(occurrence)
            if len(semantic_bucket) != 1 or (
                semantic_bucket[0].state.status
                is not ProjectRelationRowSchemaStatus.CONCRETE
            ):
                continue
            semantic = semantic_bucket[0]
            owner = _declaration_identity(occurrence)
            lineage_bucket = attribution.find_row_lineage(owner)
            if len(lineage_bucket) != 1:
                raise ValueError("Concrete source requires exact row-field authority.")
            lineage = lineage_bucket[0]
            fields = tuple(item.field for item in lineage.fields)
            schema = semantic.state.schema
            assert schema is not None
            if lineage.status is not ProjectRelationRowSchemaStatus.CONCRETE or tuple(
                field.name for field in fields
            ) != tuple(schema.fields):
                raise ValueError("Concrete source field authority must be complete.")
            rows.append((owner, semantic, fields))
    return tuple(rows)


def _source_scope(
    owner: ProjectDeclarationOccurrenceIdentity,
    semantic: ProjectModuleRelationSemanticFacts,
    candidates: tuple[ProjectCandidateKeyFact, ...],
) -> ProjectExactRowOutputConstraintScope:
    if candidates:
        scope = candidates[0].supports[0].scope
        if scope.owner != owner or scope.relation is not semantic:
            raise ValueError("Candidate key scope must match its exact source output.")
        return scope
    return ProjectExactRowOutputConstraintScope(
        kind=ProjectRelationshipConstraintScopeKind.UNCONDITIONAL_ON_EXACT_ROW_OUTPUT,
        owner=owner,
        relation=semantic,
    )


def _basis_for_source(
    row_keys: ProjectRowKeySet,
    owner: ProjectDeclarationOccurrenceIdentity,
    semantic: ProjectModuleRelationSemanticFacts,
    fields: tuple[ProjectModuleRowFieldIdentity, ...],
) -> ProjectValueFDBasis:
    candidates = tuple(
        candidate
        for candidate in row_keys.candidate_keys
        if candidate.identity.owner == owner
    )
    universe = ProjectValueFDFieldUniverse(
        scope=_source_scope(owner, semantic, candidates),
        fields=fields,
    )
    facts: list[ProjectValueFDFact] = []
    for candidate in candidates:
        determinant_set = set(candidate.identity.determinants)
        dependents = tuple(field for field in fields if field not in determinant_set)
        if not dependents:
            continue
        facts.append(
            ProjectValueFDFact(
                identity=ProjectValueFDIdentity(
                    scope=universe.scope,
                    determinants=candidate.identity.determinants,
                    dependents=dependents,
                    strength=candidate.identity.strength,
                    premise=candidate.identity,
                ),
                premise=candidate,
                origin=ProjectConstraintEvidenceOrigin.DERIVED_THEOREM,
                trust=ProjectConstraintEvidenceTrust.TRUSTED,
                enforcement=ProjectConstraintEnforcementPosture.MODEL_CONTRACT,
            )
        )
    fact_tuple = tuple(facts)
    return ProjectValueFDBasis(
        universe=universe,
        facts=fact_tuple,
        index=_compile_project_value_fd_index(universe, fact_tuple),
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectValueFDBasisSet:
    """Complete direct value-FD bases for every exact concrete Source output."""

    row_keys: ProjectRowKeySet = field(repr=False, compare=False, hash=False)
    bases: tuple[ProjectValueFDBasis, ...] = ()

    def __post_init__(self) -> None:
        if type(self.row_keys) is not ProjectRowKeySet:
            raise TypeError("Value-FD basis set requires exact Slice-4 row keys.")
        if type(self.bases) is not tuple or any(
            type(basis) is not ProjectValueFDBasis for basis in self.bases
        ):
            raise TypeError("Value-FD bases must be an exact tuple.")
        rows = _concrete_source_rows(self.row_keys)
        if len(self.bases) != len(rows):
            raise ValueError("Value-FD bases must cover every concrete source output.")
        for basis, (owner, semantic, fields) in zip(self.bases, rows, strict=True):
            if (
                basis.universe.scope.owner != owner
                or basis.universe.scope.relation is not semantic
                or len(basis.universe.fields) != len(fields)
                or any(
                    actual != expected
                    for actual, expected in zip(
                        basis.universe.fields,
                        fields,
                        strict=True,
                    )
                )
            ):
                raise ValueError("Value-FD universe must retain exact source order.")
            candidates = tuple(
                candidate
                for candidate in self.row_keys.candidate_keys
                if candidate.identity.owner == owner
                and set(candidate.identity.determinants) != set(fields)
            )
            if len(basis.facts) != len(candidates):
                raise ValueError("Value-FD facts must cover every non-trivial key.")
            for fact, candidate in zip(basis.facts, candidates, strict=True):
                determinant_set = set(candidate.identity.determinants)
                expected_dependents = tuple(
                    field for field in fields if field not in determinant_set
                )
                if (
                    fact.premise is not candidate
                    or fact.identity.scope is not basis.universe.scope
                    or fact.identity.dependents != expected_dependents
                ):
                    raise ValueError("Value-FD facts must retain exact key derivation.")

    def find_owner(
        self,
        owner: ProjectDeclarationOccurrenceIdentity,
    ) -> tuple[ProjectValueFDBasis, ...]:
        """Return one exact source-output basis or an empty tuple."""

        if type(owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Value-FD lookup requires an exact output owner.")
        return tuple(
            basis for basis in self.bases if basis.universe.scope.owner == owner
        )


def build_project_value_fds(row_keys: ProjectRowKeySet) -> ProjectValueFDBasisSet:
    """Derive the complete direct key-implied value-FD basis."""

    if type(row_keys) is not ProjectRowKeySet:
        raise TypeError("Value-FD construction requires exact Slice-4 row keys.")
    return ProjectValueFDBasisSet(
        row_keys=row_keys,
        bases=tuple(
            _basis_for_source(row_keys, owner, semantic, fields)
            for owner, semantic, fields in _concrete_source_rows(row_keys)
        ),
    )


def strict_value_fd_closure(
    index: ProjectValueFDIndex,
    seed: ProjectValueFDFieldSet,
) -> ProjectStrictClosureResult:
    """Reach one STRICT-only fixed point with an indexed worklist."""

    if type(index) is not ProjectValueFDIndex or (
        type(seed) is not ProjectValueFDFieldSet
    ):
        raise TypeError("STRICT closure requires an exact index and typed seed.")
    if seed.universe is not index.universe:
        raise ValueError("STRICT closure requires one exact field universe.")
    closure_mask = seed.mask
    unsatisfied = [rule.lhs_mask.bit_count() for rule in index.strict_rules]
    fired = [False] * len(index.strict_rules)
    pending: deque[int] = deque(index.positions[field] for field in seed.fields)
    ready: list[int] = []
    witness: list[ProjectStrictClosureProofStep] = []
    while pending or ready:
        while pending:
            field_position = pending.popleft()
            for rule_position in index.strict_incidents[field_position]:
                if fired[rule_position]:
                    continue
                unsatisfied[rule_position] -= 1
                if unsatisfied[rule_position] == 0:
                    heappush(ready, rule_position)
        if not ready:
            break
        rule_position = heappop(ready)
        fired[rule_position] = True
        rule = index.strict_rules[rule_position]
        new_mask = rule.rhs_mask & ~closure_mask
        if not new_mask:
            continue
        closure_mask |= new_mask
        derived_fields = tuple(
            field
            for position, field in enumerate(index.universe.fields)
            if new_mask & (1 << position)
        )
        witness.append(
            ProjectStrictClosureProofStep(
                fact=rule.fact,
                derived_fields=derived_fields,
            )
        )
        pending.extend(index.positions[field] for field in derived_fields)
    closure_fields = ProjectValueFDFieldSet(
        universe=index.universe,
        fields=tuple(
            field
            for position, field in enumerate(index.universe.fields)
            if closure_mask & (1 << position)
        ),
    )
    return ProjectStrictClosureResult(
        seed=seed,
        fields=closure_fields,
        witness=tuple(witness),
    )


def strictly_determines(
    index: ProjectValueFDIndex,
    seed: ProjectValueFDFieldSet,
    targets: ProjectValueFDFieldSet,
) -> ProjectValueFDDeterminationResult:
    """Answer whether current STRICT evidence proves the requested targets."""

    if type(targets) is not ProjectValueFDFieldSet or (
        type(index) is not ProjectValueFDIndex
        or seed.universe is not index.universe
        or targets.universe is not index.universe
    ):
        raise ValueError("Determination query requires one exact field universe.")
    closure = strict_value_fd_closure(index, seed)
    status = (
        ProjectValueFDDeterminationStatus.PROVEN
        if targets.mask & closure.fields.mask == targets.mask
        else ProjectValueFDDeterminationStatus.NOT_PROVEN
    )
    return ProjectValueFDDeterminationResult(
        seed=seed,
        targets=targets,
        closure=closure,
        status=status,
    )
