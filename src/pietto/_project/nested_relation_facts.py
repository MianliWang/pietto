"""Private typed nested-relation facts before relational lowering exists."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from pietto import ast_nodes as ast
from pietto._project.model import (
    ProjectRelationRowSchemaStatus,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
)
from pietto._project.module_attribution import (
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleRowFieldIdentity,
    ProjectModuleRowFieldKind,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalogSet,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionEnvironment,
    ProjectResolvedExpressionBlockRead,
    ProjectResolvedModuleRelationSymbol,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSelectFact,
    ProjectModuleSemanticFactEnvironment,
    ProjectModuleSemanticFactSet,
)
from pietto._syntax_admission import unnest_lets
from pietto.errors import Diagnostic, Severity, SourceLocation

__all__: tuple[str, ...] = ()

_ADMITTED_CHILD_LEAF_NAMES = frozenset(
    {"Bool", "Date", "Decimal", "Float", "Int", "Text", "Timestamp", "UUID"}
)
# D71.04: CROSS, INNER and LEFT Unnest; every JOIN but CROSS has an `on`.
_UNNEST_JOIN_KINDS = frozenset(
    {ast.AuthoredJoinKind.CROSS, ast.AuthoredJoinKind.INNER, ast.AuthoredJoinKind.LEFT}
)


class ProjectNestedRelationFactStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"


class ProjectNestedRelationFactReason(StrEnum):
    TARGET_NOT_LOCAL_LET = "target_not_local_let"
    TARGET_UNAVAILABLE = "target_unavailable"
    OUTPUT_UNAVAILABLE = "output_unavailable"
    JOIN_UNAVAILABLE = "join_unavailable"
    SCALAR_BOUNDARY = "scalar_boundary"


def _require_state(
    status: object, reason: object, *, operation: str
) -> ProjectNestedRelationFactStatus:
    """Bind availability to its reason: only SCALAR_BOUNDARY is available."""

    if (
        type(status) is not ProjectNestedRelationFactStatus
        or type(reason) is not ProjectNestedRelationFactReason
    ):
        raise TypeError(f"{operation} fact requires an exact availability state.")
    if (status is ProjectNestedRelationFactStatus.AVAILABLE) != (
        reason is ProjectNestedRelationFactReason.SCALAR_BOUNDARY
    ):
        raise ValueError(f"{operation} fact availability must match its reason.")
    return status


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNestedRelationElementField:
    position: int
    identity: ProjectModuleRowFieldIdentity
    field: ProjectRowField
    effective_nullability: ProjectRowFieldNullability

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise ValueError("Nested relation field position must be non-negative.")
        if type(self.identity) is not ProjectModuleRowFieldIdentity:
            raise TypeError("Nested relation field requires an exact identity.")
        if type(self.field) is not ProjectRowField:
            raise TypeError("Nested relation field requires exact field evidence.")
        if type(self.effective_nullability) is not ProjectRowFieldNullability:
            raise TypeError("Nested relation field requires exact nullability.")
        if (
            self.identity.field_position != self.position
            or self.identity.name != self.field.name
            or self.effective_nullability is not self.field.nullability
        ):
            raise ValueError("Nested relation field must retain its exact child field.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNestedRelationType:
    element_relation: ProjectDeclarationOccurrenceIdentity
    element_fields: tuple[ProjectNestedRelationElementField, ...]
    container_nullability: ProjectRowFieldNullability
    collection_depth: int = 1

    def __post_init__(self) -> None:
        if type(self.element_relation) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Nested relation type requires an exact relation identity.")
        if type(self.element_fields) is not tuple or any(
            type(item) is not ProjectNestedRelationElementField
            for item in self.element_fields
        ):
            raise TypeError("Nested relation type requires exact ordered child fields.")
        if any(
            item.position != position
            or item.identity.owner != self.element_relation
            or item.identity.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
            for position, item in enumerate(self.element_fields)
        ):
            raise ValueError("Nested relation fields must retain dense source order.")
        # D71.04: a Collect of zero rows is `[]`, never None.
        if self.container_nullability is not ProjectRowFieldNullability.NON_NULL:
            raise ValueError("A collected relation value is never None.")
        if type(self.collection_depth) is not int or self.collection_depth != 1:
            raise ValueError("S03 supports exactly one collection layer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectCollectOccurrenceFact:
    owner: ProjectDeclarationOccurrenceIdentity
    selection: ProjectModuleSelectFact
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
            or not _is_local_let(target, self.owner)
            or self.nested_type.element_relation != target
        ):
            raise ValueError(
                "Available Collect facts require their resolved local let."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectUnnestInputFact:
    owner: ProjectDeclarationOccurrenceIdentity
    query_let: ast.QueryLetDeclaration
    binding_name_span: ast.Span
    source_binding_name: str
    source_target: ProjectResolvedModuleRelationSymbol | None
    source_field: ProjectModuleRowFieldIdentity | None
    nested_type: ProjectNestedRelationType | None
    # Every visible FROM or earlier JOIN binding of the authored binding name,
    # in written order: its one resolved relation, or None when its relation
    # is blocked, ambiguous or unknown.
    binding_candidates: tuple[ProjectResolvedModuleRelationSymbol | None, ...]
    join_candidates: tuple[ast.JoinClause, ...]
    status: ProjectNestedRelationFactStatus
    reason: ProjectNestedRelationFactReason

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Unnest fact requires an exact owner identity.")
        if type(self.query_let) is not ast.QueryLetDeclaration:
            raise TypeError("Unnest fact requires its exact query let.")
        if self.binding_name_span is not self.query_let.name_span:
            raise ValueError("Unnest fact must retain its binding-name span.")
        binding, field_name = _unnest_argument(self.query_let)
        if self.source_binding_name != binding:
            raise ValueError("Unnest fact must retain its authored binding name.")
        if type(self.binding_candidates) is not tuple or any(
            item is not None and type(item) is not ProjectResolvedModuleRelationSymbol
            for item in self.binding_candidates
        ):
            raise TypeError("Unnest facts require exact visible binding candidates.")
        if type(self.join_candidates) is not tuple or any(
            type(item) is not ast.JoinClause for item in self.join_candidates
        ):
            raise TypeError("Unnest facts require exact authored JOIN candidates.")
        if self.source_target is not (
            self.binding_candidates[0] if len(self.binding_candidates) == 1 else None
        ):
            raise ValueError("Unnest source target must be its one visible binding.")
        if (self.source_field is None) != (self.nested_type is None):
            raise ValueError("Unnest nested-field evidence must be complete.")
        source_field = self.source_field
        if source_field is not None and (
            type(source_field) is not ProjectModuleRowFieldIdentity
            or type(self.nested_type) is not ProjectNestedRelationType
            or self.source_target is None
            or source_field.owner != _identity(self.source_target.target_occurrence)
            or source_field.kind is not ProjectModuleRowFieldKind.RELATION_OUTPUT
            or source_field.name != field_name
        ):
            raise ValueError("Unnest source field must be its binding's nested output.")
        status = _require_state(self.status, self.reason, operation="Unnest")
        if status is ProjectNestedRelationFactStatus.AVAILABLE and (
            source_field is None
            or len(self.join_candidates) != 1
            or not _valid_unnest_join(self.join_candidates[0])
        ):
            raise ValueError(
                "Available Unnest facts require exact nested input evidence."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNestedRelationFactSet:
    catalogs: ProjectModuleCatalogSet
    semantic: ProjectModuleSemanticFactSet
    collect_facts: tuple[ProjectCollectOccurrenceFact, ...]
    unnest_inputs: tuple[ProjectUnnestInputFact, ...]
    diagnostics: tuple[Diagnostic, ...]

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
            type(item) is not ProjectUnnestInputFact for item in self.unnest_inputs
        ):
            raise TypeError("Nested relation facts require exact Unnest facts.")
        if type(self.diagnostics) is not tuple or any(
            type(item) is not Diagnostic for item in self.diagnostics
        ):
            raise TypeError("Nested relation facts require exact diagnostics.")
        # Every fact is the one the semantic root derives, in authored order;
        # the supplied facts never decide a status, reason, target or type.
        collects, unnests, diagnostics = _derive_nested_facts(self.semantic)
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
        if self.diagnostics != diagnostics:
            raise ValueError(
                "Nested relation diagnostics must project every occurrence in order."
            )


def build_project_nested_relation_facts(
    *, catalogs: ProjectModuleCatalogSet, semantic: ProjectModuleSemanticFactSet
) -> ProjectNestedRelationFactSet:
    """Build S03's closed typed facts without lowering nested values as scalars."""

    if (
        type(catalogs) is not ProjectModuleCatalogSet
        or type(semantic) is not ProjectModuleSemanticFactSet
    ):
        raise TypeError("Nested facts require exact catalog and semantic roots.")
    collects, unnests, diagnostics = _derive_nested_facts(semantic)
    return ProjectNestedRelationFactSet(
        catalogs=catalogs,
        semantic=semantic,
        collect_facts=collects,
        unnest_inputs=unnests,
        diagnostics=diagnostics,
    )


def _derive_nested_facts(
    semantic: ProjectModuleSemanticFactSet,
) -> tuple[
    tuple[ProjectCollectOccurrenceFact, ...],
    tuple[ProjectUnnestInputFact, ...],
    tuple[Diagnostic, ...],
]:
    """Every authored Collect and Unnest occurrence in module and source
    order, and their PIE-S2802 diagnostics: modules in the order of the
    semantic environments, which relation resolution reports in, and each
    module's in source order."""

    semantic_by_owner = {
        id(fact.owner): fact
        for environment in semantic.environments
        for fact in environment.relation_facts
    }
    collects: list[ProjectCollectOccurrenceFact] = []
    bodies: list[
        tuple[
            ProjectModuleSemanticFactEnvironment,
            ProjectModuleRelationSemanticFacts,
            ast.TableDef | ast.QueryDef | ast.SelectBody,
            tuple[tuple[ast.QueryLetDeclaration, tuple[ast.JoinClause, ...]], ...],
        ]
    ] = []
    found: list[tuple[int, Diagnostic]] = []
    for index, environment in enumerate(semantic.environments):
        parsed = environment.module.parsed_input
        if parsed is None:
            continue
        # The bodies as written, before the project normalized their names.
        script = parsed.authored_script or parsed.script
        for semantic_fact in environment.relation_facts:
            # A table-function occurrence's body is its containing relation's.
            if semantic_fact.owner.table_function is not None:
                continue
            own = _collect_facts(
                environment.resolution_environment, semantic_fact, semantic_by_owner
            )
            collects.extend(own)
            found.extend(
                (index, _unsupported(fact.authored_collect.span, "Collect"))
                for fact in own
            )
            body = _authored_body(script, semantic_fact.owner)
            if body is not None:
                lets = unnest_lets(body)
                bodies.append((environment, semantic_fact, body, lets))
                found.extend(
                    (index, _unsupported(item.span, "Unnest")) for item, _ in lets
                )
    available: dict[
        tuple[ProjectDeclarationOccurrenceIdentity, str],
        list[ProjectCollectOccurrenceFact],
    ] = {}
    for fact in collects:
        if fact.status is ProjectNestedRelationFactStatus.AVAILABLE:
            assert fact.output is not None
            available.setdefault((fact.owner, fact.output.name), []).append(fact)
    unnests = tuple(
        _unnest_fact(
            environment.resolution_environment,
            semantic_fact,
            body,
            item,
            joins,
            available,
        )
        for environment, semantic_fact, body, lets in bodies
        for item, joins in lets
    )
    found.sort(
        key=lambda item: (
            item[0],
            item[1].location.line,
            item[1].location.column,
        )
    )
    return (
        tuple(collects),
        unnests,
        tuple(diagnostic for _, diagnostic in found),
    )


def _collect_facts(
    resolution_environment: ProjectModuleRelationResolutionEnvironment,
    semantic_fact: ProjectModuleRelationSemanticFacts,
    semantic_by_owner: dict[int, ProjectModuleRelationSemanticFacts],
) -> tuple[ProjectCollectOccurrenceFact, ...]:
    selections = tuple(
        selection
        for selection in semantic_fact.select_facts
        if type(selection.item.expression) is ast.CollectRelationExpr
    )
    if not selections:
        return ()
    owner = semantic_fact.owner
    owner_identity = _identity(owner)
    resolutions = {
        id(item.read.expression): item
        for item in resolution_environment.expression_reads
        if item.read.owner is owner
    }
    output_names = [selection.output_name for selection in semantic_fact.select_facts]
    found: list[ProjectCollectOccurrenceFact] = []
    for selection in selections:
        expression = selection.item.expression
        assert type(expression) is ast.CollectRelationExpr
        resolution = resolutions.get(id(expression))
        if resolution is None:
            raise ValueError("Collect fact requires one scoped read resolution.")
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
        symbol = resolution.target_symbol
        target = None if symbol is None else _identity(symbol.target_occurrence)
        target_fact = (
            None
            if symbol is None
            else semantic_by_owner.get(id(symbol.target_occurrence))
        )
        schema = None if target_fact is None else _concrete_schema(target_fact)
        nested = None
        if target is None:
            reason = ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
        elif not _is_local_let(target, owner_identity):
            reason = ProjectNestedRelationFactReason.TARGET_NOT_LOCAL_LET
        elif schema is None or not _supported_child_fields(schema):
            reason = ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
        elif output is None or output_names.count(output.name) != 1:
            # A colliding output name keeps every occurrence; none wins.
            reason = ProjectNestedRelationFactReason.OUTPUT_UNAVAILABLE
        else:
            reason = ProjectNestedRelationFactReason.SCALAR_BOUNDARY
            nested = ProjectNestedRelationType(
                element_relation=target,
                element_fields=tuple(
                    ProjectNestedRelationElementField(
                        position=position,
                        identity=ProjectModuleRowFieldIdentity(
                            owner=target,
                            kind=ProjectModuleRowFieldKind.RELATION_OUTPUT,
                            field_position=position,
                            name=field.name,
                        ),
                        field=field,
                        effective_nullability=field.nullability,
                    )
                    for position, field in enumerate(schema.fields.values())
                ),
                container_nullability=ProjectRowFieldNullability.NON_NULL,
            )
        found.append(
            ProjectCollectOccurrenceFact(
                owner=owner_identity,
                selection=selection,
                authored_collect=expression,
                resolution=resolution,
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


def _unnest_fact(
    resolution_environment: ProjectModuleRelationResolutionEnvironment,
    semantic_fact: ProjectModuleRelationSemanticFacts,
    body: ast.TableDef | ast.QueryDef | ast.SelectBody,
    item: ast.QueryLetDeclaration,
    joins: tuple[ast.JoinClause, ...],
    available: dict[
        tuple[ProjectDeclarationOccurrenceIdentity, str],
        list[ProjectCollectOccurrenceFact],
    ],
) -> ProjectUnnestInputFact:
    """One Unnest let with all its visible bindings and JOINs; never a winner."""

    binding, field_name = _unnest_argument(item)
    candidates = tuple(
        target
        for name, target in _visible_bindings(
            resolution_environment, semantic_fact.owner, body, before=item.span
        )
        if name == binding
    )
    source_target = candidates[0] if len(candidates) == 1 else None
    collected = (
        ()
        if source_target is None
        else available.get((_identity(source_target.target_occurrence), field_name), ())
    )
    source = collected[0] if len(collected) == 1 else None
    owner = _identity(semantic_fact.owner)
    if source_target is None:
        # No visible binding, or none with exactly one relation.
        reason = ProjectNestedRelationFactReason.TARGET_UNAVAILABLE
    elif source is None:
        reason = ProjectNestedRelationFactReason.OUTPUT_UNAVAILABLE
    elif len(joins) != 1 or not _valid_unnest_join(joins[0]):
        reason = ProjectNestedRelationFactReason.JOIN_UNAVAILABLE
    else:
        reason = ProjectNestedRelationFactReason.SCALAR_BOUNDARY
    return ProjectUnnestInputFact(
        owner=owner,
        query_let=item,
        binding_name_span=item.name_span,
        source_binding_name=binding,
        source_target=source_target,
        source_field=None if source is None else source.output,
        nested_type=None if source is None else source.nested_type,
        binding_candidates=candidates,
        join_candidates=joins,
        status=(
            ProjectNestedRelationFactStatus.AVAILABLE
            if reason is ProjectNestedRelationFactReason.SCALAR_BOUNDARY
            else ProjectNestedRelationFactStatus.UNAVAILABLE
        ),
        reason=reason,
    )


def _same_collect(
    supplied: ProjectCollectOccurrenceFact, expected: ProjectCollectOccurrenceFact
) -> bool:
    return (
        supplied.selection is expected.selection
        and supplied.authored_collect is expected.authored_collect
        and supplied.resolution is expected.resolution
        and supplied == expected
        and _same_child_fields(supplied.nested_type, expected.nested_type)
    )


def _same_unnest(
    supplied: ProjectUnnestInputFact, expected: ProjectUnnestInputFact
) -> bool:
    return (
        supplied.query_let is expected.query_let
        and supplied.source_target is expected.source_target
        and len(supplied.binding_candidates) == len(expected.binding_candidates)
        and all(
            item is other
            for item, other in zip(
                supplied.binding_candidates, expected.binding_candidates, strict=True
            )
        )
        and len(supplied.join_candidates) == len(expected.join_candidates)
        and all(
            item is other
            for item, other in zip(
                supplied.join_candidates, expected.join_candidates, strict=True
            )
        )
        and supplied == expected
        and _same_child_fields(supplied.nested_type, expected.nested_type)
    )


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
    unnest_inputs: tuple[ProjectUnnestInputFact, ...],
) -> None:
    """Bind each Unnest nested field to one exact available Collect output."""

    for unnest in unnest_inputs:
        if unnest.source_field is None:
            continue
        matches = tuple(
            collect
            for collect in collect_facts
            if collect.status is ProjectNestedRelationFactStatus.AVAILABLE
            and collect.output is unnest.source_field
            and collect.nested_type is unnest.nested_type
        )
        if len(matches) != 1:
            raise ValueError(
                "Unnest nested fields require one exact Collect authority."
            )


def _identity(
    owner: ProjectDeclarationOccurrence,
) -> ProjectDeclarationOccurrenceIdentity:
    return ProjectDeclarationOccurrenceIdentity(
        identity=owner.identity,
        module_position=owner.module_position,
        declaration_position=owner.declaration_position,
        let_position=owner.let_position,
        table_function=owner.table_function is not None,
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


def _concrete_schema(
    fact: ProjectModuleRelationSemanticFacts,
) -> ProjectRowSchema | None:
    state = fact.state
    if (
        state.status is not ProjectRelationRowSchemaStatus.CONCRETE
        or state.schema is None
        or state.schema.is_unknown
    ):
        return None
    return state.schema


def _supported_child_fields(schema: ProjectRowSchema) -> bool:
    return all(
        field.nullability is not ProjectRowFieldNullability.UNKNOWN
        and field.resolved_type.kind is ProjectResolvedTypeKind.BUILTIN
        and field.resolved_type.name in _ADMITTED_CHILD_LEAF_NAMES
        for field in schema.fields.values()
    )


def _unnest_argument(item: ast.QueryLetDeclaration) -> tuple[str, str]:
    """The `binding.field` of one classified `unnest(binding.field)` let."""

    call = item.expression
    if type(call) is not ast.CallExpr or len(call.arguments) != 1:
        raise ValueError("Unnest facts require an exact unnest call.")
    argument = call.arguments[0]
    if type(argument) is not ast.DottedNameExpr or len(argument.parts) != 2:
        raise ValueError("Unnest facts require one binding.field argument.")
    return argument.parts[0], argument.parts[1]


def _valid_unnest_join(join: ast.JoinClause) -> bool:
    return join.kind in _UNNEST_JOIN_KINDS and (
        (join.kind is ast.AuthoredJoinKind.CROSS) == (join.on_clause is None)
    )


def _authored_body(
    script: ast.Script, owner: ProjectDeclarationOccurrence
) -> ast.TableDef | ast.QueryDef | ast.SelectBody | None:
    """The owner's FROM-based body as written in its module's script."""

    definition = script.definitions[owner.declaration_position]
    if type(definition) is ast.BlockRelationDef:
        body = (
            definition.body
            if owner.let_position is None
            else definition.let_relations[owner.let_position].body
        )
        return body if type(body) is ast.SelectBody else None
    if type(definition) is ast.TableDef or type(definition) is ast.QueryDef:
        return definition
    return None


def _visible_bindings(
    environment: ProjectModuleRelationResolutionEnvironment,
    owner: ProjectDeclarationOccurrence,
    body: ast.TableDef | ast.QueryDef | ast.SelectBody,
    *,
    before: ast.Span,
) -> tuple[tuple[str, ProjectResolvedModuleRelationSymbol | None], ...]:
    """Reuse normalized FROM/JOIN resolution authority in written input order."""

    definition = owner.definition
    if type(definition) is not ast.TableDef and type(definition) is not ast.QueryDef:
        return ()
    position = (before.line, before.column)
    result: list[tuple[str, ProjectResolvedModuleRelationSymbol | None]] = []
    authored_from = body.from_clause
    from_clause = definition.from_clause
    if (authored_from.span.line, authored_from.span.column) < position:
        if type(from_clause) is ast.FromClause:
            targets = tuple(
                item.target_symbol for item in environment.find_from_clause(from_clause)
            )
            result.append(
                (
                    from_clause.binding_name or from_clause.source_name,
                    targets[0] if len(targets) == 1 else None,
                )
            )
        elif type(from_clause) is ast.TableFunctionFromClause:
            result.append((from_clause.binding_name, None))
    for join in definition.join_clauses:
        if (join.span.line, join.span.column) >= position:
            break
        targets = environment.find_scoped_relation_name(
            owner, join.target_relation_name
        )
        result.append(
            (join.target_binding_name, targets[0] if len(targets) == 1 else None)
        )
    return tuple(result)


def is_unnest_join(
    facts: ProjectNestedRelationFactSet,
    owner: ProjectDeclarationOccurrence,
    join: ast.JoinClause,
) -> bool:
    """Whether ``join``, a JOIN of ``owner``'s relation as its row reads it,
    joins one of that relation's Unnest lets (D71.02)."""

    identity = _identity(owner)
    position = (join.span.path, join.span.line, join.span.column)
    return any(
        (candidate.span.path, candidate.span.line, candidate.span.column) == position
        for fact in facts.unnest_inputs
        if fact.owner == identity
        for candidate in fact.join_candidates
    )


def _unsupported(span: ast.Span, operation: str) -> Diagnostic:
    return _error(
        "PIE-S2802",
        f"{operation} relation reads are not supported by the current "
        "scalar-only project boundary.",
        span,
        "Nested relation values are typed but cannot yet be lowered or returned.",
    )


def _error(
    code: str, message: str, span: ast.Span, suggestion: str | None = None
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
        suggestion=suggestion,
    )
