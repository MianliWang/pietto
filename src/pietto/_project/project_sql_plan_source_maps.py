"""Immutable source associations and explanations of the retained origin graph."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, fields
from enum import StrEnum
from types import MappingProxyType
from typing import Never, TypedDict

from pietto import ast_nodes as ast
from pietto.errors import Diagnostic, SourceLocation
from pietto._project import project_sql_plan as sql
from pietto._project import project_sql_plan_windows as windows
from pietto._project import project_sql_plan_literals as literals
from pietto._project.model import ProjectParsedInput, ProjectRowField
from pietto._project.module_catalog import ProjectDeclarationOccurrence
from pietto._project.module_carrier import ProjectLogicalModule
from pietto._project.module_attribution import (
    ProjectModuleOriginPath,
    ProjectModuleAccessHop,
    ProjectDeclarationOccurrenceIdentity,
    ProjectModuleImportOccurrenceIdentity,
    ProjectModuleFacadeOccurrenceIdentity,
    ProjectModuleReferenceOccurrenceIdentity,
    ProjectModuleImportAttribution,
    ProjectModuleFacadeAttribution,
    ProjectModuleReferenceAttribution,
    ProjectModuleReferenceProvenance,
)
from pietto._project.project_sql_plan_verification import (
    ProjectSQLPlanVerification,
    verify_project_sql_plan,
)
from pietto.semantic.model import ValueType

__all__: tuple[str, ...] = ()


class ProjectSQLSourceNature(StrEnum):
    SYNTAX_CORRESPONDENCE = "syntax_correspondence"
    GENERATED = "generated_structure"


R = sql.ProjectSQLOriginRole
SYNTAX_ROLES = (
    R.EXPRESSION,
    R.LET_VALUE,
    R.FILTER,
    R.PROJECTION,
    R.GROUP_KEY,
    R.AGGREGATE,
    R.AGGREGATE_PROJECTION,
    R.WINDOW,
    R.WINDOW_USE,
    R.WINDOW_ARGUMENT,
    R.WINDOW_PROJECTION,
    R.RELATIONSHIP_MATCH,
    R.DISTINCT,
    R.ORDER,
    R.ORDER_ITEM,
    R.ORDER_EXPRESSION,
    R.RESULT_LIMIT,
)
GENERATED_ROLES = (
    R.SELECTED_OWNER,
    R.DEFINITION,
    R.SOURCE_DESCRIPTOR,
    R.SOURCE_PORT,
    R.INPUT_USE,
    R.INPUT_PORT,
    R.STAGE_EXPORT,
    R.EXPORT,
    R.BOUNDARY,
    R.SYMBOL,
    R.DEMAND,
    R.SELECT_BLOCK,
    R.STAGE_PORT,
    R.EXPRESSION_SITE,
    R.OPERAND,
    R.JOIN,
    R.JOIN_INPUT,
    R.JOIN_PORT,
    R.JOIN_TAIL,
    R.SINGLE_MATCH,
    R.SINGLE_MATCH_PROOF,
    R.AGGREGATION,
    R.AGGREGATE_RISK,
    R.WINDOW_POLICY,
    R.RESULT_BOUNDARY,
    R.RESULT_PORT,
    R.QUOTIENT_FIELD,
    R.ORDER_USE,
    R.HIDDEN_ORDER_REQUIREMENT,
    R.RESULT_EXPORT,
    R.SET_BODY,
    R.SET_OPERAND,
    R.SET_INPUT,
    R.SET_COLUMN,
    R.LITERAL_SITE,
    R.LITERAL_SLOT,
    R.FIXED_LITERAL_VALUE,
    R.BIND_USE,
)


class ProjectSQLSourceAssociationKind(StrEnum):
    CAUSE = "authored_cause"
    EXPRESSION_BODY = "expression_body"
    FIELD_DECLARATION = "field_declaration"
    TYPE_REFERENCE = "type_reference"
    REFERENCED_DECLARATION = "referenced_declaration"
    IMPORT = "import_item"
    EXPORT = "export_item"
    CONNECTOR = "source_connector"
    EFFECTIVE_WINDOW = "effective_to_authored_window"
    WINDOW_COMPONENT = "authored_or_inherited_window_component"
    NAMED_WINDOW = "named_window_declaration"


class ProjectSQLPositionAvailability(StrEnum):
    COMPLETE = "complete"
    PARTIAL = "partial"
    UNAVAILABLE = "unavailable"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourcePosition:
    original: ast.Span | SourceLocation | None
    path: str | None
    line: int | None
    column: int | None
    end_line: int | None
    end_column: int | None
    availability: ProjectSQLPositionAvailability


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLMappedSource:
    position: int
    module: ProjectLogicalModule
    parsed: ProjectParsedInput

    @property
    def display_path(self) -> str:
        return self.module.path


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceSite:
    position: int
    source: ProjectSQLMappedSource
    occurrence: ast.Node
    container: ast.Node
    declaration: ProjectDeclarationOccurrence | None
    location: ProjectSQLSourcePosition


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceMapEntry:
    position: int
    original: sql.ProjectSQLOrigin
    nature: ProjectSQLSourceNature
    # A closed original role plus its original evidence/antecedents is the reason.
    generated_reason: sql.ProjectSQLOriginRole | None
    consuming_definition: sql.ProjectSQLPlanRef

    @property
    def ref(self) -> sql.ProjectSQLPlanRef:
        return self.original.ref

    @property
    def subject(self) -> sql.ProjectSQLPlanScope | sql.ProjectSQLPlanRef:
        return self.original.subject


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceAssociation:
    position: int
    entry: ProjectSQLSourceMapEntry
    site: ProjectSQLSourceSite
    kind: ProjectSQLSourceAssociationKind
    observed: ast.Node
    evidence: object
    path: ProjectModuleOriginPath | None
    hop: ProjectModuleAccessHop | None


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLLegacySourcePosition:
    position: int
    entry: ProjectSQLSourceMapEntry
    field: ProjectRowField
    location: ProjectSQLSourcePosition


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLMappedSubject:
    ref: sql.ProjectSQLPlanScope | sql.ProjectSQLPlanRef
    origins: tuple[ProjectSQLSourceMapEntry, ...]


class ProjectSQLSourceEndpointKind(StrEnum):
    ORIGIN = "origin_ref"
    SUBJECT = "subject_ref"


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceLink:
    position: int
    ordinal: int
    origin: ProjectSQLSourceMapEntry
    kind: ProjectSQLSourceEndpointKind
    target: ProjectSQLSourceMapEntry | ProjectSQLMappedSubject


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class _Member:
    module: ProjectLogicalModule
    node: ast.Node
    container: ast.Node
    declaration: ProjectDeclarationOccurrence | None


class _SourceTables(TypedDict):
    members_by_node: dict[int, tuple[_Member, ...]]
    uses: dict[sql.ProjectSQLPlanRef, sql.ProjectSQLInputUse]
    sources: dict[sql.ProjectSQLPlanRef, sql.ProjectSQLSourceBinding]
    windows: dict[sql.ProjectSQLPlanRef, windows.ProjectSQLWindow]
    declarations: dict[
        ProjectDeclarationOccurrenceIdentity, ProjectDeclarationOccurrence
    ]
    imports: dict[
        ProjectModuleImportOccurrenceIdentity,
        tuple[ProjectModuleImportAttribution, ...],
    ]
    exports: dict[
        ProjectModuleFacadeOccurrenceIdentity,
        tuple[ProjectModuleFacadeAttribution, ...],
    ]
    references: dict[
        ProjectModuleReferenceOccurrenceIdentity, ProjectModuleReferenceAttribution
    ]
    references_by_node: dict[int, tuple[ProjectModuleReferenceAttribution, ...]]
    provenance: dict[
        ProjectModuleReferenceOccurrenceIdentity,
        tuple[ProjectModuleReferenceProvenance, ...],
    ]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceMapIndexes:
    origins: Mapping[sql.ProjectSQLPlanRef, ProjectSQLSourceMapEntry]
    subjects: Mapping[
        sql.ProjectSQLPlanScope | sql.ProjectSQLPlanRef, ProjectSQLMappedSubject
    ]
    associations: Mapping[
        sql.ProjectSQLPlanRef, tuple[ProjectSQLSourceAssociation, ...]
    ]
    by_site: Mapping[ProjectSQLSourceSite, tuple[ProjectSQLSourceAssociation, ...]]
    by_source: Mapping[ProjectSQLMappedSource, tuple[ProjectSQLSourceAssociation, ...]]
    occurrences: Mapping[tuple[int, int], tuple[_Member, ...]]
    reverse: Mapping[tuple[int, int], tuple[ProjectSQLSourceAssociation, ...]]
    antecedents: Mapping[sql.ProjectSQLPlanRef, tuple[ProjectSQLSourceLink, ...]]
    dependents: Mapping[
        sql.ProjectSQLPlanScope | sql.ProjectSQLPlanRef,
        tuple[ProjectSQLSourceLink, ...],
    ]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False, init=False)
class ProjectSQLSourceMap:
    source_verification: ProjectSQLPlanVerification
    plan: sql.ProjectSQLPlan
    literal_policy: literals.ProjectSQLLiteralPolicy
    envelope: literals.ProjectSQLFixedEnvelope
    diagnostics: tuple[Diagnostic, ...]
    sources: tuple[ProjectSQLMappedSource, ...]
    sites: tuple[ProjectSQLSourceSite, ...]
    entries: tuple[ProjectSQLSourceMapEntry, ...]
    subjects: tuple[ProjectSQLMappedSubject, ...]
    associations: tuple[ProjectSQLSourceAssociation, ...]
    legacy_positions: tuple[ProjectSQLLegacySourcePosition, ...]
    links: tuple[ProjectSQLSourceLink, ...]
    indexes: ProjectSQLSourceMapIndexes

    def __init__(self) -> Never:
        raise TypeError("Source maps are closed; use build_project_sql_source_map.")


def _require_plan(verification: ProjectSQLPlanVerification) -> sql.ProjectSQLPlan:
    try:
        if (
            type(verification) is ProjectSQLPlanVerification
            and verification.verified
            and type(verification.plan) is sql.ProjectSQLPlan
            and verify_project_sql_plan(
                verification.plan,
                verification.completed,
                verification.analysis_bundle,
                verification.selected_owner,
                literal_policy=verification.literal_policy,
                envelope=verification.envelope,
            ).verified
            and verification.envelope is verification.plan.fixed_envelope
            and verification.literal_policy is verification.plan.literal_policy
        ):
            return verification.plan
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        pass
    raise ValueError("Source maps require an exact current VERIFIED plan request.")


def _children(value):
    """Closed AST containers only; never descend into semantic evidence objects."""
    if isinstance(value, (ast.Node, ast.AuthoredWindowFrame, ast.WindowFrameBound)):
        return tuple(
            getattr(value, item.name) for item in fields(value) if item.name != "span"
        )
    if type(value) is tuple:
        return value
    return ()


def membership(plan):
    """Read the retained parsed modules once. No loading, parsing or name lookup."""
    authority = plan.scope.analysis_bundle.root.base_plan.attribution._authority
    owners = {
        (id(catalog.module), id(owner.definition)): owner
        for catalog in authority.catalogs.catalogs
        for owner in catalog.occurrences
    }
    members = {}
    containers = (
        ast.FieldDef,
        ast.NamedWindowDeclaration,
        ast.ImportStatement,
        ast.ExportStatement,
        ast.RelationshipMetadata,
    )
    for module in authority.modules:
        if module.parsed_input is None:
            raise ValueError("Mapped sources require their original parsed input.")
        script = module.parsed_input.script
        pending = [(script, None, script)]
        seen = set()
        while pending:
            value, owner, container = pending.pop()
            declaration = owners.get((id(module), id(value)))
            if declaration is not None:
                owner, container = declaration, value
            elif isinstance(value, containers):
                container = value
            if isinstance(value, ast.Node):
                key = (id(value), id(container), id(owner))
                if key in seen:
                    continue
                seen.add(key)
                members.setdefault((module.position, id(value)), []).append(
                    _Member(
                        module=module,
                        node=value,
                        container=container,
                        declaration=owner,
                    )
                )
            pending.extend(
                (child, owner, container) for child in reversed(_children(value))
            )
    return authority.modules, {key: tuple(values) for key, values in members.items()}


def _coordinates(location):
    if location is None:
        return None, None, None, None, None
    if type(location) not in (ast.Span, SourceLocation):
        raise ValueError("Source coordinates require retained position evidence.")
    values = (
        location.path,
        location.line,
        location.column,
        location.end_line,
        location.end_column,
    )
    if values[0] is not None and type(values[0]) is not str:
        raise ValueError("Malformed source path evidence.")
    if any(type(v) is not int or v < 1 for v in values[1:3]):
        raise ValueError("Source coordinates require positive exact integers.")
    if any(v is not None and (type(v) is not int or v < 1) for v in values[3:]):
        raise ValueError(
            "Source end coordinates require exact integers or original absence."
        )
    if type(location) is ast.Span and any(v is None for v in values[3:]):
        raise ValueError("Authored AST spans require complete original coordinates.")
    if values[3] is not None and values[3] < values[1]:
        raise ValueError("Source range ends before its start.")
    if all(v is not None for v in values[1:]) and values[3:] < values[1:3]:
        raise ValueError("Source range ends before its start.")
    return values


def allocate_position(location):
    values = _coordinates(location)
    A = ProjectSQLPositionAvailability
    return ProjectSQLSourcePosition(
        original=location,
        path=values[0],
        line=values[1],
        column=values[2],
        end_line=values[3],
        end_column=values[4],
        availability=A.UNAVAILABLE
        if location is None
        else A.PARTIAL
        if None in values[1:]
        else A.COMPLETE,
    )


def _position_matches(actual, original):
    if type(actual) is not ProjectSQLSourcePosition or actual.original is not original:
        return False
    values = _coordinates(original)
    given = (
        actual.path,
        actual.line,
        actual.column,
        actual.end_line,
        actual.end_column,
    )
    A = ProjectSQLPositionAvailability
    expected = (
        A.UNAVAILABLE
        if original is None
        else A.COMPLETE
        if all(v is not None for v in values[1:])
        else A.PARTIAL
    )
    return actual.availability is expected and all(
        type(a) is type(b) and a == b for a, b in zip(given, values, strict=True)
    )


def classify_origin(origin):
    if any(origin.role is role for role in SYNTAX_ROLES):
        return ProjectSQLSourceNature.SYNTAX_CORRESPONDENCE, None
    if any(origin.role is role for role in GENERATED_ROLES):
        return ProjectSQLSourceNature.GENERATED, origin.role
    raise ValueError("Unhandled source-map origin role.")


def _buckets(values, key):
    result = {}
    for value in values:
        result.setdefault(key(value), []).append(value)
    return {key: tuple(items) for key, items in result.items()}


def source_tables(plan, members) -> _SourceTables:
    attribution = plan.scope.analysis_bundle.root.base_plan.attribution
    return _SourceTables(
        members_by_node=_buckets(
            (m for values in members.values() for m in values), lambda m: id(m.node)
        ),
        uses={use.ref: use for use in plan.input_uses},
        sources={source.ref: source for source in plan.sources},
        windows={window.ref: window for window in plan.windows},
        declarations={
            value.identity: value.occurrence for value in attribution.declarations
        },
        imports=_buckets(attribution.imports, lambda value: value.identity),
        exports=_buckets(attribution.facades, lambda value: value.identity),
        references={value.identity: value for value in attribution.references},
        references_by_node=_buckets(
            attribution.references, lambda value: id(value.site)
        ),
        provenance=_buckets(
            attribution.reference_provenance, lambda value: value.reference
        ),
    )


def _one(values):
    if len(values) != 1:
        raise ValueError(
            "Source correspondence requires one exact retained attribution."
        )
    return values[0]


def access_sites(path, tables):
    """Read original access hops and their rooted request/facade AST objects."""
    K = ProjectSQLSourceAssociationKind
    for hop in path.hops:
        imported = _one(tables["imports"].get(hop.import_occurrence, ()))
        exported = _one(tables["exports"].get(hop.facade_occurrence, ()))
        yield (
            K.IMPORT,
            imported.request.source_item,
            imported.request.source_item,
            imported,
            path,
            hop,
        )
        yield (
            K.EXPORT,
            exported.entry.request.source_item,
            exported.entry.request.source_item,
            exported,
            path,
            hop,
        )
    declaration = tables["declarations"][path.target_occurrence]
    yield (
        K.REFERENCED_DECLARATION,
        declaration.definition,
        declaration.definition,
        declaration,
        path,
        None,
    )


def reference_sites(node, tables):
    K = ProjectSQLSourceAssociationKind
    for reference in tables["references_by_node"].get(id(node), ()):
        if reference.site is not node:
            raise ValueError("Reference attribution does not own this AST occurrence.")
        for provenance in tables["provenance"].get(reference.identity, ()):
            for path in provenance.paths:
                for hop in path.hops:
                    yield from access_sites(hop.origin, tables)
                if path.terminal_reference is not None:
                    terminal = tables["references"][path.terminal_reference]
                    if terminal.site is not node:
                        yield (
                            K.TYPE_REFERENCE,
                            terminal.site,
                            terminal.site,
                            terminal,
                            None,
                            None,
                        )


def evidence_fields(origin):
    evidence = origin.evidence
    if isinstance(evidence, sql.ProjectIROutputFieldOccurrence):
        return (evidence.evidence,)
    if isinstance(evidence, ProjectRowField):
        return (evidence,)
    return ()


def association_routes(origin, tables):
    """Pure traversal of closed retained witnesses, before any site allocation."""
    K = ProjectSQLSourceAssociationKind
    yield K.CAUSE, origin.cause, origin.cause, origin.evidence, None, None
    yield from reference_sites(origin.cause, tables)
    if isinstance(
        origin.cause,
        (
            ast.SelectItem,
            ast.LetBinding,
            ast.WhereClause,
            ast.SatisfyingClause,
            ast.QualifyClause,
            ast.JoinOnClause,
            ast.OrderItem,
        ),
    ):
        node = origin.cause.expression
        yield K.EXPRESSION_BODY, node, node, origin.cause, None, None
    for value in evidence_fields(origin):
        definition = value.field_def
        if definition is not None:
            yield K.FIELD_DECLARATION, definition, definition, value, None, None
            yield (
                K.TYPE_REFERENCE,
                definition.type_expr,
                definition.type_expr,
                value,
                None,
                None,
            )
            yield from reference_sites(definition.type_expr, tables)
    if (
        isinstance(origin.evidence, ValueType)
        and origin.evidence.resolved_type.definition is not None
    ):
        node = origin.evidence.resolved_type.definition
        yield K.REFERENCED_DECLARATION, node, node, origin.evidence, None, None
    if origin.role is R.INPUT_USE:
        yield from access_sites(tables["uses"][origin.subject].origin_path, tables)
    if origin.role is R.SOURCE_DESCRIPTOR:
        source = tables["sources"][origin.subject]
        yield K.CONNECTOR, source.connector, source.connector, source, None, None
    evidence = origin.evidence
    window = (
        evidence
        if type(evidence) is windows.ProjectSQLWindow
        else tables["windows"][evidence.window]
        if type(evidence) is windows.ProjectSQLWindowPolicy
        else None
    )
    if window is not None and window.effective is not window.authored:
        yield K.EFFECTIVE_WINDOW, window.authored, window.effective, window, None, None
    if type(evidence) is windows.ProjectSQLWindowPolicy:
        assert window is not None
        if evidence.named_use is not None:
            composed = evidence.named_use.composed
            declaration = composed.target_template.declaration
            yield K.NAMED_WINDOW, declaration, declaration, composed.base, None, None
            yield (
                K.WINDOW_COMPONENT,
                composed.base.reference,
                composed.base.reference,
                composed.base,
                None,
                None,
            )
        spec = window.effective.spec
        components = [*spec.partition_by, *spec.order_by]
        for bound in (spec.frame.start, spec.frame.end):
            if bound is not None and bound.offset is not None:
                components.append(bound.offset)
        for node in components:
            yield K.WINDOW_COMPONENT, node, node, evidence, None, None
            for member in tables["members_by_node"].get(id(node), ()):
                if type(member.container) is ast.NamedWindowDeclaration:
                    yield (
                        K.NAMED_WINDOW,
                        member.container,
                        member.container,
                        evidence,
                        None,
                        None,
                    )


def _routes(origin, tables):
    # Repeated mentions of one exact route are not new association occurrences.
    seen = set()
    for route in association_routes(origin, tables):
        key = tuple(id(value) for value in route)
        if key not in seen:
            seen.add(key)
            yield route


def _consumer(origin, definitions):
    evidence = origin.evidence
    if isinstance(evidence, literals.ProjectSQLLiteralSite):
        return evidence.position.definition
    if isinstance(evidence, literals.ProjectSQLLiteralSlot):
        return evidence.site.position.definition
    if isinstance(
        evidence, (literals.ProjectSQLFixedLiteralValue, literals.ProjectSQLBindUse)
    ):
        return evidence.slot.site.position.definition
    return definitions[id(origin.owner)]


def _group(domain, values, key):
    groups = {value: [] for value in domain}
    for value in values:
        groups[key(value)].append(value)
    return MappingProxyType({key: tuple(items) for key, items in groups.items()})


def index_members(sources, sites, entries, subjects, associations, links, members):
    origin_map = {entry.ref: entry for entry in entries}
    subject_map = {subject.ref: subject for subject in subjects}
    return ProjectSQLSourceMapIndexes(
        origins=MappingProxyType(origin_map),
        subjects=MappingProxyType(subject_map),
        associations=_group(origin_map, associations, lambda value: value.entry.ref),
        by_site=_group(sites, associations, lambda value: value.site),
        by_source=_group(sources, associations, lambda value: value.site.source),
        occurrences=MappingProxyType(members),
        reverse=_group(
            members,
            associations,
            lambda value: (
                value.site.source.module.position,
                id(value.site.occurrence),
            ),
        ),
        antecedents=_group(origin_map, links, lambda value: value.origin.ref),
        dependents=_group(
            (*subject_map, *origin_map), links, lambda value: value.target.ref
        ),
    )


def _build_map(verification):
    plan = _require_plan(verification)
    modules, members = membership(plan)
    tables = source_tables(plan, members)
    source_values = []
    for i, module in enumerate(modules):
        assert module.parsed_input is not None
        source_values.append(
            ProjectSQLMappedSource(
                position=i, module=module, parsed=module.parsed_input
            )
        )
    sources = tuple(source_values)
    source_by_module = {id(source.module): source for source in sources}
    definitions = {id(d.entry.owner): d.ref for d in plan.bindings.definitions}
    entries = []
    for i, origin in enumerate(plan.origins):
        nature, reason = classify_origin(origin)
        entries.append(
            ProjectSQLSourceMapEntry(
                position=i,
                original=origin,
                nature=nature,
                generated_reason=reason,
                consuming_definition=_consumer(origin, definitions),
            )
        )
    entries = tuple(entries)
    sites, associations, legacy = [], [], []
    allocated = {}
    for entry in entries:
        for kind, node, observed, evidence, path, hop in _routes(
            entry.original, tables
        ):
            candidates = tables["members_by_node"].get(id(node), ())
            if not candidates:
                raise ValueError(
                    "Source association lost its required authored correspondence."
                )
            for member in candidates:
                if member.node is not node:
                    raise ValueError("Source association has a foreign AST occurrence.")
                key = (
                    id(member.module),
                    id(node),
                    id(member.container),
                    id(member.declaration),
                )
                if key not in allocated:
                    site = ProjectSQLSourceSite(
                        position=len(sites),
                        source=source_by_module[id(member.module)],
                        occurrence=node,
                        container=member.container,
                        declaration=member.declaration,
                        location=allocate_position(node.span),
                    )
                    allocated[key] = site
                    sites.append(site)
                associations.append(
                    ProjectSQLSourceAssociation(
                        position=len(associations),
                        entry=entry,
                        site=allocated[key],
                        kind=kind,
                        observed=observed,
                        evidence=evidence,
                        path=path,
                        hop=hop,
                    )
                )
        for value in evidence_fields(entry.original):
            position = None if value.provenance is None else value.provenance.location
            legacy.append(
                ProjectSQLLegacySourcePosition(
                    position=len(legacy),
                    entry=entry,
                    field=value,
                    location=allocate_position(position),
                )
            )
    grouped = _buckets(entries, lambda entry: entry.subject)
    subjects = tuple(
        ProjectSQLMappedSubject(ref=ref, origins=values)
        for ref, values in grouped.items()
    )
    by_subject, by_origin = {s.ref: s for s in subjects}, {e.ref: e for e in entries}
    links = []
    for entry in entries:
        for ordinal, ref in enumerate(entry.original.antecedents):
            origin_endpoint = ref.kind is sql.ProjectSQLPlanRefKind.ORIGIN
            target = by_origin[ref] if origin_endpoint else by_subject[ref]
            links.append(
                ProjectSQLSourceLink(
                    position=len(links),
                    ordinal=ordinal,
                    origin=entry,
                    kind=ProjectSQLSourceEndpointKind.ORIGIN
                    if origin_endpoint
                    else ProjectSQLSourceEndpointKind.SUBJECT,
                    target=target,
                )
            )
    sites, associations, legacy, links = (
        tuple(sites),
        tuple(associations),
        tuple(legacy),
        tuple(links),
    )
    product = object.__new__(ProjectSQLSourceMap)
    for name, value in dict(
        source_verification=verification,
        plan=plan,
        literal_policy=verification.literal_policy,
        envelope=plan.fixed_envelope,
        diagnostics=plan.diagnostics,
        sources=sources,
        sites=sites,
        entries=entries,
        subjects=subjects,
        associations=associations,
        legacy_positions=legacy,
        links=links,
        indexes=index_members(
            sources, sites, entries, subjects, associations, links, members
        ),
    ).items():
        object.__setattr__(product, name, value)
    return product


def build_project_sql_source_map(
    verification: ProjectSQLPlanVerification,
) -> ProjectSQLSourceMap:
    try:
        return _build_map(verification)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        raise ValueError(
            "Source-map construction requires complete original correspondence."
        ) from None


class ProjectSQLSourceMapIssue(StrEnum):
    PLAN = "plan_request"
    ROOTS = "source_map_roots"
    ORIGINS = "origin_correspondence"
    SITES = "authored_source_sites"
    ASSOCIATIONS = "source_associations"
    POSITIONS = "source_positions"
    LINKS = "antecedent_endpoints"
    INDEXES = "source_map_indexes"
    STRUCTURE = "source_map_structure"


def _same(actual, expected):
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(a is b for a, b in zip(actual, expected, strict=True))
    )


def _same_members(actual, expected):
    return (
        type(actual) is tuple
        and len(actual) == len(expected)
        and all(
            type(a) is _Member
            and a.module is b.module
            and a.node is b.node
            and a.container is b.container
            and a.declaration is b.declaration
            for a, b in zip(actual, expected, strict=True)
        )
    )


def _verify_map(product, verification):
    Issue = ProjectSQLSourceMapIssue
    try:
        plan = _require_plan(verification)
    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        return (Issue.PLAN,)
    if type(product) is not ProjectSQLSourceMap:
        return (Issue.STRUCTURE,)
    if (
        product.source_verification is not verification
        or product.plan is not plan
        or product.literal_policy is not verification.literal_policy
        or product.envelope is not verification.envelope
        or product.diagnostics is not plan.diagnostics
    ):
        return (Issue.ROOTS,)
    modules, members = membership(plan)
    tables = source_tables(plan, members)
    if type(product.sources) is not tuple or len(product.sources) != len(modules):
        return (Issue.ROOTS,)
    for i, (source, module) in enumerate(zip(product.sources, modules, strict=True)):
        if (
            type(source) is not ProjectSQLMappedSource
            or type(source.position) is not int
            or source.position != i
            or source.module is not module
            or source.parsed is not module.parsed_input
        ):
            return (Issue.ROOTS,)
    source_by_module = {id(s.module): s for s in product.sources}
    if type(product.entries) is not tuple or len(product.entries) != len(plan.origins):
        return (Issue.ORIGINS,)
    definitions = {id(d.entry.owner): d.ref for d in plan.bindings.definitions}
    for i, (entry, origin) in enumerate(
        zip(product.entries, plan.origins, strict=True)
    ):
        # Independent classification from the closed original-role taxonomy.
        if any(origin.role is role for role in SYNTAX_ROLES):
            nature, reason = ProjectSQLSourceNature.SYNTAX_CORRESPONDENCE, None
        elif any(origin.role is role for role in GENERATED_ROLES):
            nature, reason = ProjectSQLSourceNature.GENERATED, origin.role
        else:
            return (Issue.ORIGINS,)
        if (
            type(entry) is not ProjectSQLSourceMapEntry
            or type(entry.position) is not int
            or entry.position != i
            or entry.original is not origin
            or entry.nature is not nature
            or entry.generated_reason is not reason
            or entry.consuming_definition is not _consumer(origin, definitions)
        ):
            return (Issue.ORIGINS,)
    if (
        type(product.sites) is not tuple
        or type(product.associations) is not tuple
        or type(product.legacy_positions) is not tuple
    ):
        return (Issue.SITES,)
    site_keys, cursor, legacy_cursor = {}, 0, 0
    for entry in product.entries:
        for kind, node, observed, evidence, path, hop in _routes(
            entry.original, tables
        ):
            candidates = tables["members_by_node"].get(id(node), ())
            if not candidates:
                return (Issue.SITES,)
            for member in candidates:
                key = (
                    id(member.module),
                    id(node),
                    id(member.container),
                    id(member.declaration),
                )
                if key not in site_keys:
                    site = product.sites[len(site_keys)]
                    if (
                        type(site) is not ProjectSQLSourceSite
                        or type(site.position) is not int
                        or site.position != len(site_keys)
                        or site.source is not source_by_module[id(member.module)]
                        or site.occurrence is not node
                        or site.container is not member.container
                        or site.declaration is not member.declaration
                        or not _position_matches(site.location, node.span)
                    ):
                        return (Issue.SITES,)
                    site_keys[key] = site
                association = product.associations[cursor]
                if (
                    type(association) is not ProjectSQLSourceAssociation
                    or type(association.position) is not int
                    or association.position != cursor
                    or association.entry is not entry
                    or association.site is not site_keys[key]
                    or association.kind is not kind
                    or association.observed is not observed
                    or association.evidence is not evidence
                    or association.path is not path
                    or association.hop is not hop
                ):
                    return (Issue.ASSOCIATIONS,)
                cursor += 1
        for value in evidence_fields(entry.original):
            original = None if value.provenance is None else value.provenance.location
            legacy = product.legacy_positions[legacy_cursor]
            if (
                type(legacy) is not ProjectSQLLegacySourcePosition
                or type(legacy.position) is not int
                or legacy.position != legacy_cursor
                or legacy.entry is not entry
                or legacy.field is not value
                or not _position_matches(legacy.location, original)
            ):
                return (Issue.POSITIONS,)
            legacy_cursor += 1
    if (
        len(site_keys) != len(product.sites)
        or cursor != len(product.associations)
        or legacy_cursor != len(product.legacy_positions)
    ):
        return (Issue.ASSOCIATIONS,)
    grouped = _buckets(product.entries, lambda entry: entry.subject)
    if type(product.subjects) is not tuple or len(product.subjects) != len(grouped):
        return (Issue.LINKS,)
    for subject, (ref, entries) in zip(product.subjects, grouped.items(), strict=True):
        if (
            type(subject) is not ProjectSQLMappedSubject
            or subject.ref is not ref
            or not _same(subject.origins, entries)
        ):
            return (Issue.LINKS,)
    by_subject, by_origin = (
        {s.ref: s for s in product.subjects},
        {e.ref: e for e in product.entries},
    )
    if type(product.links) is not tuple:
        return (Issue.LINKS,)
    cursor = 0
    for entry in product.entries:
        for ordinal, ref in enumerate(entry.original.antecedents):
            link = product.links[cursor]
            kind = (
                ProjectSQLSourceEndpointKind.ORIGIN
                if ref.kind is sql.ProjectSQLPlanRefKind.ORIGIN
                else ProjectSQLSourceEndpointKind.SUBJECT
            )
            target = (
                by_origin[ref]
                if kind is ProjectSQLSourceEndpointKind.ORIGIN
                else by_subject[ref]
            )
            if (
                type(link) is not ProjectSQLSourceLink
                or type(link.position) is not int
                or link.position != cursor
                or type(link.ordinal) is not int
                or link.ordinal != ordinal
                or link.origin is not entry
                or link.kind is not kind
                or link.target is not target
            ):
                return (Issue.LINKS,)
            cursor += 1
    if cursor != len(product.links):
        return (Issue.LINKS,)
    expected_indexes = index_members(
        product.sources,
        product.sites,
        product.entries,
        product.subjects,
        product.associations,
        product.links,
        members,
    )
    if type(product.indexes) is not ProjectSQLSourceMapIndexes:
        return (Issue.INDEXES,)
    for name in ProjectSQLSourceMapIndexes.__dataclass_fields__:
        actual, expected = (
            getattr(product.indexes, name),
            getattr(expected_indexes, name),
        )
        if type(actual) is not MappingProxyType or len(actual) != len(expected):
            return (Issue.INDEXES,)
        for (key, value), (wanted, items) in zip(
            actual.items(), expected.items(), strict=True
        ):
            if name in ("occurrences", "reverse"):
                if (
                    type(key) is not tuple
                    or len(key) != 2
                    or any(type(k) is not int for k in key)
                    or key != wanted
                ):
                    return (Issue.INDEXES,)
            elif key is not wanted:
                return (Issue.INDEXES,)
            if (
                not _same_members(value, items)
                if name == "occurrences"
                else value is not items
                if name in ("origins", "subjects")
                else not _same(value, items)
            ):
                return (Issue.INDEXES,)
    return ()


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceMapVerification:
    source_map: ProjectSQLSourceMap
    source_verification: ProjectSQLPlanVerification
    issues: tuple[ProjectSQLSourceMapIssue, ...] = field(init=False)

    def __post_init__(self) -> None:
        try:
            issues = _verify_map(self.source_map, self.source_verification)
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            issues = (ProjectSQLSourceMapIssue.STRUCTURE,)
        object.__setattr__(self, "issues", issues)

    @property
    def verified(self) -> bool:
        return not self.issues


def verify_project_sql_source_map(
    source_map: ProjectSQLSourceMap, source_verification: ProjectSQLPlanVerification
) -> ProjectSQLSourceMapVerification:
    return ProjectSQLSourceMapVerification(
        source_map=source_map, source_verification=source_verification
    )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceExplanation:
    root: ProjectSQLMappedSubject | ProjectSQLSourceMapEntry
    transitive: bool
    visited: tuple[ProjectSQLSourceMapEntry, ...]
    origins: tuple[ProjectSQLSourceMapEntry, ...]
    associations: tuple[ProjectSQLSourceAssociation, ...]
    links: tuple[ProjectSQLSourceLink, ...]


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectSQLSourceMapInspection:
    verification: ProjectSQLSourceMapVerification
    source_map: ProjectSQLSourceMap = field(init=False)

    def __post_init__(self) -> None:
        checked = self.verification
        try:
            valid = (
                type(checked) is ProjectSQLSourceMapVerification
                and checked.verified
                and verify_project_sql_source_map(
                    checked.source_map, checked.source_verification
                ).verified
            )
        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            valid = False
        if not valid:
            raise ValueError(
                "Source-map inspection requires an exact current VERIFIED map."
            )
        object.__setattr__(self, "source_map", checked.source_map)

    def subject(
        self, ref: sql.ProjectSQLPlanScope | sql.ProjectSQLPlanRef
    ) -> ProjectSQLMappedSubject:
        if (
            type(ref) not in (sql.ProjectSQLPlanScope, sql.ProjectSQLPlanRef)
            or ref not in self.source_map.indexes.subjects
        ):
            raise ValueError("Reference is not an owned source-map subject.")
        return self.source_map.indexes.subjects[ref]

    def origin(self, ref: sql.ProjectSQLPlanRef) -> ProjectSQLSourceMapEntry:
        if (
            type(ref) is not sql.ProjectSQLPlanRef
            or ref not in self.source_map.indexes.origins
        ):
            raise ValueError("Reference is not an owned source-map origin.")
        return self.source_map.indexes.origins[ref]

    def _endpoint(self, ref):
        return (
            self.origin(ref)
            if type(ref) is sql.ProjectSQLPlanRef
            and ref.kind is sql.ProjectSQLPlanRefKind.ORIGIN
            else self.subject(ref)
        )

    def associations(self, ref) -> tuple[ProjectSQLSourceAssociation, ...]:
        endpoint = self._endpoint(ref)
        entries = (
            (endpoint,)
            if isinstance(endpoint, ProjectSQLSourceMapEntry)
            else endpoint.origins
        )
        return tuple(
            a
            for entry in entries
            for a in self.source_map.indexes.associations[entry.ref]
        )

    def antecedents(self, ref) -> tuple[ProjectSQLSourceLink, ...]:
        endpoint = self._endpoint(ref)
        entries = (
            (endpoint,)
            if isinstance(endpoint, ProjectSQLSourceMapEntry)
            else endpoint.origins
        )
        return tuple(
            link
            for entry in entries
            for link in self.source_map.indexes.antecedents[entry.ref]
        )

    def dependents(self, ref) -> tuple[ProjectSQLSourceLink, ...]:
        endpoint = self._endpoint(ref)
        return self.source_map.indexes.dependents[endpoint.ref]

    def _source(self, source):
        if type(source) is not ProjectSQLMappedSource or not any(
            source is item for item in self.source_map.sources
        ):
            raise ValueError("Source does not belong to this exact source map.")

    def reverse(
        self, source: ProjectSQLMappedSource, occurrence: ast.Node
    ) -> tuple[ProjectSQLSourceAssociation, ...]:
        self._source(source)
        key = (source.module.position, id(occurrence))
        members = self.source_map.indexes.occurrences.get(key, ())
        if not members or any(
            member.node is not occurrence or member.module is not source.module
            for member in members
        ):
            raise ValueError(
                "Occurrence is not authored in this exact retained source."
            )
        return self.source_map.indexes.reverse[key]

    @staticmethod
    def _point(line, column):
        if type(line) is not int or type(column) is not int or line < 1 or column < 1:
            raise ValueError(
                "Position queries require positive exact parser coordinates."
            )
        return line, column

    def at(
        self, source: ProjectSQLMappedSource, line: int, column: int
    ) -> tuple[ProjectSQLSourceAssociation, ...]:
        self._source(source)
        point = self._point(line, column)
        return tuple(
            a
            for a in self.source_map.indexes.by_source[source]
            if (a.site.location.line, a.site.location.column)
            <= point
            < (a.site.location.end_line, a.site.location.end_column)
        )

    def overlapping(
        self,
        source: ProjectSQLMappedSource,
        start: tuple[int, int],
        end: tuple[int, int],
    ) -> tuple[ProjectSQLSourceAssociation, ...]:
        self._source(source)
        if (
            type(start) is not tuple
            or len(start) != 2
            or type(end) is not tuple
            or len(end) != 2
        ):
            raise ValueError("Range queries require two parser-coordinate pairs.")
        low, high = self._point(*start), self._point(*end)
        if high < low:
            raise ValueError("Range ends before its start.")
        return (
            ()
            if low == high
            else tuple(
                a
                for a in self.source_map.indexes.by_source[source]
                if (a.site.location.line, a.site.location.column) < high
                and low < (a.site.location.end_line, a.site.location.end_column)
            )
        )

    def explain(
        self,
        ref,
        *,
        transitive: bool = False,
        provenance: sql.ProjectSQLOriginProvenance | None = None,
    ) -> ProjectSQLSourceExplanation:
        if type(transitive) is not bool or (
            provenance is not None
            and type(provenance) is not sql.ProjectSQLOriginProvenance
        ):
            raise ValueError(
                "Explanation mode and provenance require exact typed values."
            )
        endpoint = self._endpoint(ref)
        pending = (
            [endpoint]
            if isinstance(endpoint, ProjectSQLSourceMapEntry)
            else list(endpoint.origins)
        )
        visited = set()
        while pending:
            entry = pending.pop()
            if entry.ref in visited:
                continue
            visited.add(entry.ref)
            if transitive:
                for link in self.source_map.indexes.antecedents[entry.ref]:
                    pending.extend(
                        (link.target,)
                        if isinstance(link.target, ProjectSQLSourceMapEntry)
                        else link.target.origins
                    )
        ordered = tuple(
            entry for entry in self.source_map.entries if entry.ref in visited
        )
        selected = tuple(
            entry
            for entry in ordered
            if provenance is None or entry.original.provenance is provenance
        )
        return ProjectSQLSourceExplanation(
            root=endpoint,
            transitive=transitive,
            visited=ordered,
            origins=selected,
            associations=tuple(
                a
                for entry in selected
                for a in self.source_map.indexes.associations[entry.ref]
            ),
            links=tuple(
                link
                for entry in ordered
                for link in self.source_map.indexes.antecedents[entry.ref]
            ),
        )


def inspect_project_sql_source_map(
    verification: ProjectSQLSourceMapVerification,
) -> ProjectSQLSourceMapInspection:
    return ProjectSQLSourceMapInspection(verification=verification)
