"""Private Phase-63 query-block owner and row-source construction."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import cast

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaStatus,
)
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
)
from pietto._project.project_ir import ProjectIRRelationConstructionState
from pietto._project.project_ir_construction import (
    ProjectIRConcreteSingleRelationFragment,
    ProjectIRNonConcreteSingleRelationFragment,
    ProjectIRSingleRelationFragment,
)
from pietto._project.project_ir_joins import (
    ProjectIRConcreteJoinRegion,
    ProjectIRJoinRegion,
    ProjectIRNonConcreteJoinRegion,
)
from pietto._project.project_ir_properties import (
    ProjectIRJoinedRowField,
    ProjectIRJoinRowOutput,
    ProjectIRRelationRowOutput,
)
from pietto._project.project_phase62_verification import (
    ProjectPhase62VerificationResult,
    ProjectPhase62VerificationStatus,
)
from pietto._project.project_relationship_uses import ProjectJoinUseState
from pietto.ast_nodes import QueryDef, TableDef
from pietto.semantic.window_semantics import (
    QueryBlockOccurrence,
    _query_block_occurrence,
)

__all__: tuple[str, ...] = ()


class ProjectQueryBlockNonConcreteReason(StrEnum):
    """Exact reasons why Slice-2 query-block construction has no row source."""

    LEGACY_FLAT_MODE = "legacy_flat_mode"
    PACKAGE_ROOT_MODE = "package_root_mode"
    RELATION_SOURCE_NON_CONCRETE = "relation_source_non_concrete"
    PHASE62_VERIFICATION_INVALID = "phase62_verification_invalid"
    JOIN_REGION_NON_CONCRETE = "join_region_non_concrete"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectQueryBlockOwnerBridge:
    """The exact bridge between existing declaration and query-block occurrences."""

    owner: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    query_block: QueryBlockOccurrence = field(init=False)

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Query-block bridge requires an exact declaration owner.")
        definition = self.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise TypeError("Query-block bridge requires a TableDef or QueryDef owner.")
        object.__setattr__(
            self,
            "query_block",
            _query_block_occurrence(cast(TableDef | QueryDef, definition)),
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectExistingRelationRowSource:
    """One existing concrete relation output with its exact semantic evidence."""

    fragment: ProjectIRConcreteSingleRelationFragment = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_facts: ProjectModuleRelationSemanticFacts = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    output: ProjectIRRelationRowOutput = field(init=False)

    def __post_init__(self) -> None:
        if type(self.fragment) is not ProjectIRConcreteSingleRelationFragment:
            raise TypeError("Existing row source requires a concrete fragment.")
        semantic_facts = self.fragment.semantic_facts
        output = self.fragment.root_relation_output
        if (
            semantic_facts.state.status is not ProjectRelationRowSchemaStatus.CONCRETE
            or type(output) is not ProjectIRRelationRowOutput
        ):
            raise ValueError("Existing row source requires exact concrete evidence.")
        object.__setattr__(self, "semantic_facts", semantic_facts)
        object.__setattr__(self, "output", output)


def _require_join_region_root(
    verification: ProjectPhase62VerificationResult,
    region: ProjectIRJoinRegion,
) -> None:
    if type(verification) is not ProjectPhase62VerificationResult:
        raise TypeError("Joined row source requires an exact Phase-62 verification.")
    if type(region) not in {
        ProjectIRConcreteJoinRegion,
        ProjectIRNonConcreteJoinRegion,
    }:
        raise TypeError("Joined row source requires an exact Phase-62 JOIN region.")
    if not any(
        region is retained for retained in verification.root.join_regions.regions
    ):
        raise ValueError("JOIN region must belong to the exact verification root.")


def _require_join_owner(
    bridge: ProjectQueryBlockOwnerBridge,
    region: ProjectIRJoinRegion,
) -> None:
    if region.ledger.owner is not bridge.owner:
        raise ValueError("JOIN region must retain the exact query-block owner.")


def _historical_join_semantic_facts(
    verification: ProjectPhase62VerificationResult,
    region: ProjectIRConcreteJoinRegion,
) -> ProjectModuleRelationSemanticFacts:
    matches = verification.root.evaluation.project_plan.semantic_facts.find_owner(
        region.ledger.owner
    )
    if len(matches) != 1:
        raise ValueError("Joined row source requires one exact historical fact root.")
    historical = matches[0]
    if (
        historical.state.status is not ProjectRelationRowSchemaStatus.DEFERRED
        or historical.state.reason
        is not ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED
    ):
        raise ValueError("Joined row source requires exact historical JOIN deferral.")
    return historical


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectVerifiedJoinedRowSource:
    """One VERIFIED Phase-62 JOIN region's exact final occurrence-complete row."""

    verification: ProjectPhase62VerificationResult = field(
        repr=False,
        compare=False,
        hash=False,
    )
    region: ProjectIRConcreteJoinRegion = field(
        repr=False,
        compare=False,
        hash=False,
    )
    historical_semantic_facts: ProjectModuleRelationSemanticFacts = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    final_output: ProjectIRJoinRowOutput = field(init=False)
    fields: tuple[ProjectIRJoinedRowField, ...] = field(init=False)

    def __post_init__(self) -> None:
        _require_join_region_root(self.verification, self.region)
        if (
            self.verification.status is not ProjectPhase62VerificationStatus.VERIFIED
            or type(self.region) is not ProjectIRConcreteJoinRegion
        ):
            raise ValueError("Joined row source requires VERIFIED concrete authority.")
        historical = _historical_join_semantic_facts(self.verification, self.region)
        final_output = self.region.joins[-1].output
        fields = final_output.row_shape.fields
        object.__setattr__(self, "historical_semantic_facts", historical)
        object.__setattr__(self, "final_output", final_output)
        object.__setattr__(self, "fields", fields)


type ProjectQueryBlockRowSource = (
    ProjectExistingRelationRowSource | ProjectVerifiedJoinedRowSource
)


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectConcreteQueryBlock:
    """One exact owner bridge with one closed concrete Slice-2 row source."""

    compilation_mode: ProjectCompilationMode
    owner_bridge: ProjectQueryBlockOwnerBridge
    row_source: ProjectQueryBlockRowSource
    state: ProjectIRRelationConstructionState = field(
        init=False,
        default=ProjectIRRelationConstructionState.CONCRETE,
    )

    def __post_init__(self) -> None:
        if self.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError("Concrete query blocks require explicit-module mode.")
        if type(self.owner_bridge) is not ProjectQueryBlockOwnerBridge:
            raise TypeError("Concrete query block requires an exact owner bridge.")
        if type(self.row_source) is ProjectExistingRelationRowSource:
            owner = self.row_source.semantic_facts.owner
        elif type(self.row_source) is ProjectVerifiedJoinedRowSource:
            owner = self.row_source.region.ledger.owner
            if self.row_source.historical_semantic_facts.owner is not owner:
                raise ValueError("Joined row source lost its historical owner.")
        else:
            raise TypeError(
                "Concrete query block requires a closed row-source variant."
            )
        if owner is not self.owner_bridge.owner:
            raise ValueError("Concrete row source must retain its exact owner bridge.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectNonConcreteQueryBlock:
    """One typed Slice-2 terminal that carries no partial concrete row source."""

    compilation_mode: ProjectCompilationMode
    owner_bridge: ProjectQueryBlockOwnerBridge
    reason: ProjectQueryBlockNonConcreteReason
    relation_fragment: ProjectIRNonConcreteSingleRelationFragment | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    verification: ProjectPhase62VerificationResult | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    join_region: ProjectIRJoinRegion | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    state: ProjectIRRelationConstructionState = field(init=False)
    row_source: None = field(init=False, default=None)

    def __post_init__(self) -> None:
        if type(self.compilation_mode) is not ProjectCompilationMode:
            raise TypeError("Query-block terminal requires an exact compilation mode.")
        if type(self.owner_bridge) is not ProjectQueryBlockOwnerBridge:
            raise TypeError("Query-block terminal requires an exact owner bridge.")
        if type(self.reason) is not ProjectQueryBlockNonConcreteReason:
            raise TypeError("Query-block terminal requires an exact reason.")

        if self.reason in {
            ProjectQueryBlockNonConcreteReason.LEGACY_FLAT_MODE,
            ProjectQueryBlockNonConcreteReason.PACKAGE_ROOT_MODE,
        }:
            expected_mode = {
                ProjectQueryBlockNonConcreteReason.LEGACY_FLAT_MODE: (
                    ProjectCompilationMode.LEGACY_FLAT
                ),
                ProjectQueryBlockNonConcreteReason.PACKAGE_ROOT_MODE: (
                    ProjectCompilationMode.PACKAGE_ROOT
                ),
            }[self.reason]
            if (
                self.compilation_mode is not expected_mode
                or self.relation_fragment is not None
                or self.verification is not None
                or self.join_region is not None
            ):
                raise ValueError("Mode terminal must retain only its exact mode.")
            state = ProjectIRRelationConstructionState.BLOCKED
        elif (
            self.reason
            is ProjectQueryBlockNonConcreteReason.RELATION_SOURCE_NON_CONCRETE
        ):
            fragment = self.relation_fragment
            if (
                self.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
                or type(fragment) is not ProjectIRNonConcreteSingleRelationFragment
                or self.verification is not None
                or self.join_region is not None
                or fragment.semantic_facts.owner is not self.owner_bridge.owner
            ):
                raise ValueError("Relation terminal requires one exact fragment root.")
            state = fragment.subject.state
        else:
            verification = self.verification
            region = self.join_region
            if (
                self.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
                or self.relation_fragment is not None
                or verification is None
                or region is None
            ):
                raise ValueError("JOIN terminal requires exact verification roots.")
            _require_join_region_root(verification, region)
            _require_join_owner(self.owner_bridge, region)
            if (
                self.reason
                is ProjectQueryBlockNonConcreteReason.PHASE62_VERIFICATION_INVALID
            ):
                if verification.status is not ProjectPhase62VerificationStatus.INVALID:
                    raise ValueError("Invalid terminal requires INVALID verification.")
                state = ProjectIRRelationConstructionState.BLOCKED
            elif (
                self.reason
                is ProjectQueryBlockNonConcreteReason.JOIN_REGION_NON_CONCRETE
            ):
                if (
                    verification.status is not ProjectPhase62VerificationStatus.VERIFIED
                    or type(region) is not ProjectIRNonConcreteJoinRegion
                ):
                    raise ValueError(
                        "Non-concrete JOIN terminal requires VERIFIED blocker roots."
                    )
                state = {
                    ProjectJoinUseState.UNKNOWN: (
                        ProjectIRRelationConstructionState.UNKNOWN
                    ),
                    ProjectJoinUseState.BLOCKED: (
                        ProjectIRRelationConstructionState.BLOCKED
                    ),
                    ProjectJoinUseState.AMBIGUOUS: (
                        ProjectIRRelationConstructionState.AMBIGUOUS
                    ),
                }[region.state]
            else:
                raise AssertionError("unhandled query-block terminal reason")
        object.__setattr__(self, "state", state)


type ProjectQueryBlockConstructionResult = (
    ProjectConcreteQueryBlock | ProjectNonConcreteQueryBlock
)


def _mode_terminal(
    compilation_mode: ProjectCompilationMode,
    bridge: ProjectQueryBlockOwnerBridge,
) -> ProjectNonConcreteQueryBlock | None:
    if type(compilation_mode) is not ProjectCompilationMode:
        raise TypeError("Query-block construction requires an exact mode.")
    if compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        return None
    return ProjectNonConcreteQueryBlock(
        compilation_mode=compilation_mode,
        owner_bridge=bridge,
        reason=(
            ProjectQueryBlockNonConcreteReason.LEGACY_FLAT_MODE
            if compilation_mode is ProjectCompilationMode.LEGACY_FLAT
            else ProjectQueryBlockNonConcreteReason.PACKAGE_ROOT_MODE
        ),
    )


def build_project_query_block_from_relation(
    *,
    compilation_mode: ProjectCompilationMode,
    owner: ProjectDeclarationOccurrence,
    fragment: ProjectIRSingleRelationFragment,
) -> ProjectQueryBlockConstructionResult:
    """Build one query block from an existing relation fragment without fallback."""

    if type(fragment) not in {
        ProjectIRConcreteSingleRelationFragment,
        ProjectIRNonConcreteSingleRelationFragment,
    }:
        raise TypeError("Relation row source requires an exact fragment.")
    bridge = ProjectQueryBlockOwnerBridge(owner=owner)
    if fragment.semantic_facts.owner is not bridge.owner:
        raise ValueError("Relation fragment must retain the exact query-block owner.")
    mode_terminal = _mode_terminal(compilation_mode, bridge)
    if mode_terminal is not None:
        return mode_terminal
    if type(fragment) is ProjectIRNonConcreteSingleRelationFragment:
        return ProjectNonConcreteQueryBlock(
            compilation_mode=compilation_mode,
            owner_bridge=bridge,
            reason=(ProjectQueryBlockNonConcreteReason.RELATION_SOURCE_NON_CONCRETE),
            relation_fragment=fragment,
        )
    if type(fragment) is not ProjectIRConcreteSingleRelationFragment:
        raise AssertionError("concrete relation branch lost its exact fragment")
    return ProjectConcreteQueryBlock(
        compilation_mode=compilation_mode,
        owner_bridge=bridge,
        row_source=ProjectExistingRelationRowSource(fragment=fragment),
    )


def build_project_query_block_from_join_region(
    *,
    compilation_mode: ProjectCompilationMode,
    owner: ProjectDeclarationOccurrence,
    verification: ProjectPhase62VerificationResult,
    region: ProjectIRJoinRegion,
) -> ProjectQueryBlockConstructionResult:
    """Build one query block only from a retained VERIFIED Phase-62 JOIN region."""

    bridge = ProjectQueryBlockOwnerBridge(owner=owner)
    _require_join_region_root(verification, region)
    _require_join_owner(bridge, region)
    mode_terminal = _mode_terminal(compilation_mode, bridge)
    if mode_terminal is not None:
        return mode_terminal
    if verification.status is ProjectPhase62VerificationStatus.INVALID:
        return ProjectNonConcreteQueryBlock(
            compilation_mode=compilation_mode,
            owner_bridge=bridge,
            reason=ProjectQueryBlockNonConcreteReason.PHASE62_VERIFICATION_INVALID,
            verification=verification,
            join_region=region,
        )
    if type(region) is ProjectIRNonConcreteJoinRegion:
        return ProjectNonConcreteQueryBlock(
            compilation_mode=compilation_mode,
            owner_bridge=bridge,
            reason=ProjectQueryBlockNonConcreteReason.JOIN_REGION_NON_CONCRETE,
            verification=verification,
            join_region=region,
        )
    if type(region) is not ProjectIRConcreteJoinRegion:
        raise AssertionError("concrete JOIN branch lost its exact region")
    return ProjectConcreteQueryBlock(
        compilation_mode=compilation_mode,
        owner_bridge=bridge,
        row_source=ProjectVerifiedJoinedRowSource(
            verification=verification,
            region=region,
        ),
    )
