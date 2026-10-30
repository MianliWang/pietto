"""Private typed nested-relation facts before relational lowering exists."""

from __future__ import annotations

from dataclasses import dataclass, field

from pietto import ast_nodes as ast
from pietto._project.model import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
    ProjectNestedRelationType,
)
from pietto._project.module_catalog import ProjectModuleCatalogSet
from pietto._project.module_relation_resolution import (
    ProjectResolvedExpressionBlockRead,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleCollectReadFact,
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSelectFact,
    ProjectModuleSemanticFactSet,
    ProjectModuleUnnestOccurrenceFact,
    ProjectNestedRelationFactReason,
    ProjectNestedRelationFactStatus,
    _occurrence_identity as _identity,
    _require_nested_state as _require_state,
)

__all__: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCollectOccurrenceFact:
    """One Collect occurrence as its owner's Collect read fact types it."""

    owner: ProjectDeclarationOccurrenceIdentity
    selection: ProjectModuleSelectFact
    collect_read: ProjectModuleCollectReadFact = field(
        repr=False, compare=False, hash=False
    )
    authored_collect: ast.CollectRelationExpr
    resolution: ProjectResolvedExpressionBlockRead
    output: ProjectModuleRowFieldIdentity | None
    target: ProjectDeclarationOccurrenceIdentity | None
    nested_type: ProjectNestedRelationType | None
    status: ProjectNestedRelationFactStatus
    reason: ProjectNestedRelationFactReason

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Collect fact requires an exact owner identity.")
        if type(self.selection) is not ProjectModuleSelectFact:
            raise TypeError("Collect fact requires an exact select fact.")
        if _identity(self.selection.owner) != self.owner:
            raise ValueError("Collect fact owner must match its selection.")
        if type(self.authored_collect) is not ast.CollectRelationExpr or (
            self.selection.item.expression is not self.authored_collect
        ):
            raise ValueError("Collect fact requires its exact authored expression.")
        if (
            type(self.resolution) is not ProjectResolvedExpressionBlockRead
            or self.resolution.read.expression is not self.authored_collect
            or self.resolution.read.owner is not self.selection.owner
        ):
            raise ValueError("Collect fact requires its exact scoped read resolution.")
        if (
            type(self.collect_read) is not ProjectModuleCollectReadFact
            or self.collect_read.read is not self.resolution
        ):
            raise ValueError("Collect fact is a view of its exact Collect read.")
        output_name = self.selection.output_name
        if (self.output is None) != (output_name is None) or (
            self.output is not None
            and (
                type(self.output) is not ProjectModuleRowFieldIdentity
                or self.output.owner != self.owner
                or self.output.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
                or self.output.field_position != self.selection.selected_output_ordinal
                or self.output.name != output_name
            )
        ):
            raise ValueError("Collect output must retain its selected occurrence.")
        symbol = self.resolution.target_symbol
        if self.target != (
            None if symbol is None else _identity(symbol.target_occurrence)
        ):
            raise ValueError("Collect target must be its resolved relation.")
        if (
            self.nested_type is not None
            and type(self.nested_type) is not ProjectNestedRelationType
        ):
            raise TypeError("Collect fact nested type must be exact.")
        status = _require_state(self.status, self.reason, operation="Collect")
        if status is ProjectNestedRelationFactStatus.UNAVAILABLE:
            if self.nested_type is not None:
                raise ValueError(
                    "Unavailable Collect facts must not guess a nested type."
                )
            return
        target = self.target
        if (
            self.output is None
            or target is None
            or self.nested_type is None
            or self.nested_type is not self.collect_read.nested_type
            or not _is_local_let(target, self.owner)
            or self.nested_type.element_relation != target
        ):
            raise ValueError(
                "Available Collect facts require their resolved local let."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNestedRelationFactSet:
    """S03's Collect facts and, D-S05-7, the semantic root's own Unnest
    input facts: the same objects, which this sidecar only orders and
    checks."""

    catalogs: ProjectModuleCatalogSet
    semantic: ProjectModuleSemanticFactSet
    collect_facts: tuple[ProjectCollectOccurrenceFact, ...]
    unnest_inputs: tuple[ProjectModuleUnnestOccurrenceFact, ...]

    def __post_init__(self) -> None:
        if (
            type(self.catalogs) is not ProjectModuleCatalogSet
            or type(self.semantic) is not ProjectModuleSemanticFactSet
        ):
            raise TypeError("Nested relation facts require exact project roots.")
        authority = self.semantic.authority
        if authority.catalogs is not self.catalogs:
            raise ValueError(
                "Nested relation facts require semantic catalog authority."
            )
        if self.semantic.issues is not authority.relation_resolutions.issues:
            raise ValueError(
                "Nested relation facts require exact semantic issue roots."
            )
        if type(self.collect_facts) is not tuple or any(
            type(item) is not ProjectCollectOccurrenceFact
            for item in self.collect_facts
        ):
            raise TypeError("Nested relation facts require exact Collect facts.")
        if type(self.unnest_inputs) is not tuple or any(
            type(item) is not ProjectModuleUnnestOccurrenceFact
            for item in self.unnest_inputs
        ):
            raise TypeError("Nested relation facts require exact Unnest facts.")
        # Every fact is the one the semantic root derives, in authored order;
        # the supplied facts never decide a status, reason, target or type.
        collects, unnests = _derive_nested_facts(self.semantic)
        if len(self.collect_facts) != len(collects) or not all(
            _same_collect(supplied, expected)
            for supplied, expected in zip(self.collect_facts, collects, strict=True)
        ):
            raise ValueError(
                "Nested relation facts must retain every Collect occurrence in order."
            )
        if len(self.unnest_inputs) != len(unnests) or not all(
            _same_unnest(supplied, expected)
            for supplied, expected in zip(self.unnest_inputs, unnests, strict=True)
        ):
            raise ValueError(
                "Nested relation facts must retain every Unnest occurrence in order."
            )
        _validate_unnest_sources(self.collect_facts, self.unnest_inputs)


def build_project_nested_relation_facts(
    *, catalogs: ProjectModuleCatalogSet, semantic: ProjectModuleSemanticFactSet
) -> ProjectNestedRelationFactSet:
    """Build S03's closed typed facts without lowering nested values as scalars."""

    if (
        type(catalogs) is not ProjectModuleCatalogSet
        or type(semantic) is not ProjectModuleSemanticFactSet
    ):
        raise TypeError("Nested facts require exact catalog and semantic roots.")
    collects, unnests = _derive_nested_facts(semantic)
    return ProjectNestedRelationFactSet(
        catalogs=catalogs,
        semantic=semantic,
        collect_facts=collects,
        unnest_inputs=unnests,
    )


def _derive_nested_facts(
    semantic: ProjectModuleSemanticFactSet,
) -> tuple[
    tuple[ProjectCollectOccurrenceFact, ...],
    tuple[ProjectModuleUnnestOccurrenceFact, ...],
]:
    """Every authored Collect and Unnest occurrence in module and source
    order: modules in the order of the semantic environments and each
    module's in source order. Each Unnest fact is its occurrence's own input
    fact (D-S05-7). A Collect read or an Unnest checks like any other
    relation read or JOIN; emission refuses it where no lowering is admitted
    (D-S06-1)."""

    collects: list[ProjectCollectOccurrenceFact] = []
    unnests: list[ProjectModuleUnnestOccurrenceFact] = []
    for environment in semantic.environments:
        if environment.module.parsed_input is None:
            continue
        for semantic_fact in environment.relation_facts:
            if semantic_fact.unnest_occurrence is not None:
                unnests.append(semantic_fact.unnest_occurrence)
            # A table-function occurrence's body is its containing relation's.
            elif semantic_fact.owner.table_function is None:
                collects.extend(_collect_facts(semantic_fact))
    return tuple(collects), tuple(unnests)


def _collect_facts(
    semantic_fact: ProjectModuleRelationSemanticFacts,
) -> tuple[ProjectCollectOccurrenceFact, ...]:
    """A view of each Collect read fact of one owner, in source order; the
    read facts alone resolve and type them (D-S04-4)."""

    selections = tuple(
        selection
        for selection in semantic_fact.select_facts
        if type(selection.item.expression) is ast.CollectRelationExpr
    )
    reads = semantic_fact.collect_reads
    if len(reads) != len(selections) or any(
        read.expression is not selection.item.expression
        for read, selection in zip(reads, selections, strict=True)
    ):
        raise ValueError("Every Collect occurrence requires its one read fact.")
    owner_identity = _identity(semantic_fact.owner)
    output_names = [selection.output_name for selection in semantic_fact.select_facts]
    found: list[ProjectCollectOccurrenceFact] = []
    for selection, read in zip(selections, reads, strict=True):
        expression = read.expression
        output = (
            None
            if selection.output_name is None
            else ProjectModuleRowFieldIdentity(
                owner=owner_identity,
                kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
                field_position=selection.selected_output_ordinal,
                name=selection.output_name,
            )
        )
        symbol = read.read.target_symbol
        target = None if symbol is None else _identity(symbol.target_occurrence)
        nested = None
        if target is None:
            reason = ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
        elif not _is_local_let(target, owner_identity):
            reason = ProjectNestedRelationFactReason.TARGET_NOT_LOCAL_LET
        elif read.nested_type is None:
            reason = ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
        elif output is None or output_names.count(output.name) != 1:
            # A colliding output name keeps every occurrence; none wins.
            reason = ProjectNestedRelationFactReason.OUTPUT_UNAVAILABLE
        else:
            reason = ProjectNestedRelationFactReason.SCALAR_BOUNDARY
            nested = read.nested_type
        found.append(
            ProjectCollectOccurrenceFact(
                owner=owner_identity,
                selection=selection,
                collect_read=read,
                authored_collect=expression,
                resolution=read.read,
                output=output,
                target=target,
                nested_type=nested,
                status=(
                    ProjectNestedRelationFactStatus.AVAILABLE
                    if nested is not None
                    else ProjectNestedRelationFactStatus.UNAVAILABLE
                ),
                reason=reason,
            )
        )
    return tuple(found)


def _same_collect(
    supplied: ProjectCollectOccurrenceFact, expected: ProjectCollectOccurrenceFact
) -> bool:
    return (
        supplied.selection is expected.selection
        and supplied.collect_read is expected.collect_read
        and supplied.authored_collect is expected.authored_collect
        and supplied.resolution is expected.resolution
        and supplied == expected
        and _same_child_fields(supplied.nested_type, expected.nested_type)
    )


def _same_unnest(
    supplied: ProjectModuleUnnestOccurrenceFact,
    expected: ProjectModuleUnnestOccurrenceFact,
) -> bool:
    """An Unnest fact is its occurrence's own input fact, not an equal copy
    (D-S05-7)."""

    return supplied is expected


def _same_child_fields(
    supplied: ProjectNestedRelationType | None,
    expected: ProjectNestedRelationType | None,
) -> bool:
    """Child fields are the semantic root's own field facts, not equal copies."""

    if supplied is None or expected is None:
        return supplied is expected
    return all(
        item.field is other.field
        for item, other in zip(
            supplied.element_fields, expected.element_fields, strict=True
        )
    )


def _validate_unnest_sources(
    collect_facts: tuple[ProjectCollectOccurrenceFact, ...],
    unnest_inputs: tuple[ProjectModuleUnnestOccurrenceFact, ...],
) -> None:
    """Bind each Unnest nested field to one exact available Collect output."""

    for unnest in unnest_inputs:
        if unnest.source_field is None:
            continue
        matches = tuple(
            collect
            for collect in collect_facts
            if collect.status is ProjectNestedRelationFactStatus.AVAILABLE
            and collect.output == unnest.source_field
            and collect.collect_read is unnest.collect_read
            and collect.nested_type is unnest.nested_type
        )
        if len(matches) != 1:
            raise ValueError(
                "Unnest nested fields require one exact Collect authority."
            )


def _is_local_let(
    target: ProjectDeclarationOccurrenceIdentity,
    owner: ProjectDeclarationOccurrenceIdentity,
) -> bool:
    """S03 collects a relation let of the Collect's own declaration only."""

    return (
        target.let_position is not None
        and not target.table_function
        and target.module_position == owner.module_position
        and target.declaration_position == owner.declaration_position
    )
