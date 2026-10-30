"""Private schema-v2 cross-module relation resolution and minimal row facts."""

from __future__ import annotations

from pietto.ast_nodes import (
    SetOperand,
    SetRelationDef,
    TableFunctionRelationDef,
    UnnestRelationDef,
    ValuesRelationDef,
)

from collections.abc import Mapping
from dataclasses import dataclass, field, fields as _dataclass_fields, is_dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar, cast

from pietto._project.model import (
    ProjectRelationRowSchemaReason,
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectResolvedType,
    ProjectResolvedTypeKind,
    ProjectRowField,
    ProjectRowFieldNullability,
    ProjectRowSchema,
    ProjectSymbol,
    ProjectSymbolKind,
    ProjectSymbolNamespace,
)
from pietto._project.module_bindings import (
    ProjectModuleBindingEnvironment,
    ProjectModuleBindingEnvironmentSet,
    ProjectModuleBindingIssue,
    ProjectModuleBindingIssueStatus,
    ProjectResolvedImportedBinding,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalog,
    ProjectModuleCatalogSet,
    ProjectNominalDeclarationIdentity,
    RELATION_READ_EXPRESSIONS,
    RelationReadExpression,
    relation_read_expressions,
    relation_reads,
    table_function_input,
)
from pietto._project.module_exports import (
    ProjectModuleExportIssue,
    ProjectModuleExportIssueStatus,
    ProjectModuleExportSurface,
    ProjectModuleExportSurfaceSet,
)
from pietto._project.module_graph import (
    ProjectModuleCycle,
    ProjectModuleDiagnosticSet,
    ProjectModuleGraph,
)
from pietto._project.module_resolution import (
    ProjectModuleTypeReferenceRole,
    ProjectModuleTypeSourceResolutionEnvironment,
    ProjectResolvedModuleTypeReference,
    ProjectTypeSourceResolutionIssue,
    ProjectTypeSourceResolutionIssueStatus,
    ProjectTypeSourceResolutionSet,
    _dependency_first_vertices,
    _suppressing_diagnostics_for_binding_issues,
    _suppressing_diagnostics_for_cycle,
    _suppressing_diagnostics_for_export_issues,
)
from pietto._project.row_expression_type_facts import (
    project_row_schema_to_semantic_row_schema,
    reports_unfit_def_argument,
)
from pietto._syntax_admission import unnest_lets
from pietto.ast_nodes import (
    AnyExpr,
    AuthoredJoinKind,
    BlockRelationDef,
    CollectRelationExpr,
    DottedNameExpr,
    FromClause,
    NameExpr,
    Node,
    Nullability,
    QueryDef,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    SelectBody,
    SelectItem,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    TypeExpr,
    WindowExpr,
    inlined_arguments,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.aggregates import contains_semantic_aggregate

__all__: tuple[str, ...] = ()

_RELATION_KINDS = frozenset(
    {
        ProjectSymbolKind.SOURCE,
        ProjectSymbolKind.TABLE,
        ProjectSymbolKind.QUERY,
    }
)
_COLLISION_ISSUE_STATUSES = frozenset(
    {
        ProjectModuleBindingIssueStatus.LOCAL_DECLARATION_COLLISION,
        ProjectModuleBindingIssueStatus.IMPORT_BINDING_COLLISION,
    }
)
_DefinitionT = (
    SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | ValuesRelationDef
    | TableFunctionRelationDef
    | UnnestRelationDef
)
_KeyT = TypeVar("_KeyT")
_ObjectT = TypeVar("_ObjectT")
_ValueT = TypeVar("_ValueT")

# Phase70 relation-let errors (D70.07 nesting limit).
LET_UNREAD_CODE = "PIE-S2359"
LET_NESTING_CODE = "PIE-S2360"
LET_NESTING_LIMIT = 16


class ProjectModuleRelationResolutionIssueStatus(StrEnum):
    """Closed private failure and suppression facts for Slice 10."""

    AMBIGUOUS_LOCAL_RELATION_NAME = "ambiguous_local_relation_name"
    UNKNOWN_RELATION_REFERENCE = "unknown_relation_reference"
    UNKNOWN_DIRECT_FIELD = "unknown_direct_field"
    LOCAL_RELATION_CYCLE = "local_relation_cycle"
    MODULE_GRAPH_CYCLE_BLOCKED = "module_graph_cycle_blocked"
    MODULE_DIAGNOSTIC_BLOCKED = "module_diagnostic_blocked"
    TYPE_SOURCE_DIAGNOSTIC_BLOCKED = "type_source_diagnostic_blocked"
    LET_RELATION_NAME_COLLISION = "let_relation_name_collision"
    LET_RELATION_UNREAD = "let_relation_unread"
    LET_RELATION_NESTING_LIMIT = "let_relation_nesting_limit"
    UNKNOWN_RELATION_EXPRESSION_READ = "unknown_relation_expression_read"
    RELATION_EXPRESSION_READ_POSITION = "relation_expression_read_position"
    UNKNOWN_JOIN_INPUT = "unknown_join_input"


_UNKNOWN_READ_ISSUE_STATUSES = frozenset(
    {
        ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE,
        ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_EXPRESSION_READ,
    }
)


class ProjectExpressionBlockPosition(StrEnum):
    """Closed clause family that contains one expression-to-block read."""

    FROM = "from"
    JOIN_ON = "join_on"
    LET = "let"
    WHERE = "where"
    GROUP_BY = "group_by"
    SELECT = "select"
    SATISFYING = "satisfying"
    WINDOW = "window"
    QUALIFY = "qualify"
    ORDER_BY = "order_by"
    LIMIT = "limit"


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectExpressionBlockRead:
    """One authored relation read inside an expression of one block owner.

    The read names a whole relation block; it is never a FROM, JOIN or set
    input of its owner and never occupies one of their input slots.
    """

    owner: ProjectDeclarationOccurrence
    expression: RelationReadExpression
    position: ProjectExpressionBlockPosition
    container_ordinal: int
    ordinal: int

    def __post_init__(self) -> None:
        if (
            type(self.owner) is not ProjectDeclarationOccurrence
            or type(self.expression) not in RELATION_READ_EXPRESSIONS
            or type(self.position) is not ProjectExpressionBlockPosition
            or type(self.container_ordinal) is not int
            or type(self.ordinal) is not int
            or self.container_ordinal < 0
            or self.ordinal < 0
        ):
            raise TypeError("Expression block read requires exact occurrence facts.")

    @property
    def relation_name(self) -> str:
        return self.expression.relation_name


# Every field of a relation body, in source clause order; a field outside this
# closed map fails closed instead of hiding a read.
_CLAUSE_FIELDS = frozenset(
    {
        "span",
        "name",
        "from_clause",
        "join_clauses",
        "let_clause",
        "where_clause",
        "group_by_clause",
        "select_items",
        "satisfying_clause",
        "named_windows",
        "qualify_clause",
        "order_by_clause",
        "limit_clause",
        "distinct_clause",
        "naming_declarations",
        "join_filters",
    }
)


def _expression_read_containers(
    definition: TableDef | QueryDef,
) -> tuple[tuple[ProjectExpressionBlockPosition, int, Node], ...]:
    names = {item.name for item in _dataclass_fields(definition)}
    if type(definition) is QueryDef:
        # An entry-query header declares parameter types; it is not a clause.
        names.discard("parameters")
    if names != _CLAUSE_FIELDS:
        raise ValueError("Expression reads require a closed relation body shape.")
    if definition.naming_declarations:
        raise ValueError(
            "Expression reads require normalized query naming declarations."
        )
    if definition.join_filters:
        raise ValueError("Expression reads require normalized JOIN-prefix filters.")
    P = ProjectExpressionBlockPosition
    containers: list[tuple[ProjectExpressionBlockPosition, int, Node]] = [
        (P.FROM, 0, definition.from_clause)
    ]
    containers.extend(
        (P.JOIN_ON, i, join.on_clause)
        for i, join in enumerate(definition.join_clauses)
        if join.on_clause is not None
    )
    if definition.let_clause is not None:
        containers.extend(
            (P.LET, i, binding)
            for i, binding in enumerate(definition.let_clause.bindings)
        )
    if definition.where_clause is not None:
        containers.append((P.WHERE, 0, definition.where_clause))
    if definition.group_by_clause is not None:
        containers.append((P.GROUP_BY, 0, definition.group_by_clause))
    containers.extend(
        (P.SELECT, i, item) for i, item in enumerate(definition.select_items)
    )
    if definition.satisfying_clause is not None:
        containers.append((P.SATISFYING, 0, definition.satisfying_clause))
    containers.extend(
        (P.WINDOW, i, window) for i, window in enumerate(definition.named_windows)
    )
    if definition.qualify_clause is not None:
        containers.append((P.QUALIFY, 0, definition.qualify_clause))
    if definition.order_by_clause is not None:
        containers.extend(
            (P.ORDER_BY, i, item)
            for i, item in enumerate(definition.order_by_clause.items)
        )
    if definition.limit_clause is not None:
        containers.append((P.LIMIT, 0, definition.limit_clause))
    return tuple(containers)


def expression_block_reads(
    owner: ProjectDeclarationOccurrence,
) -> tuple[ProjectExpressionBlockRead, ...]:
    """Every relation read written in one owner's own clauses, in source order.

    Each occurrence is its own read: equal names or equal expressions are
    never merged, and nested reads keep their own ordinal.
    """

    if type(owner) is not ProjectDeclarationOccurrence:
        raise TypeError("Expression block reads require an owner occurrence.")
    definition = owner.definition
    if type(definition) not in {TableDef, QueryDef}:
        return ()
    reads: list[ProjectExpressionBlockRead] = []
    for position, container_ordinal, container in _expression_read_containers(
        cast(TableDef | QueryDef, definition)
    ):
        for expression in relation_read_expressions(container):
            reads.append(
                ProjectExpressionBlockRead(
                    owner=owner,
                    expression=expression,
                    position=position,
                    container_ordinal=container_ordinal,
                    ordinal=len(reads),
                )
            )
    return tuple(reads)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedExpressionBlockRead:
    """One expression read bound through its owner's scoped relation lookup.

    ``target_symbol`` is absent when the name is unknown, blocked or in a
    collision; the name's own issue is the diagnostic, never a chosen winner.
    """

    read: ProjectExpressionBlockRead
    target_symbol: ProjectResolvedModuleRelationSymbol | None = None

    def __post_init__(self) -> None:
        if type(self.read) is not ProjectExpressionBlockRead:
            raise TypeError("Resolved expression read requires an exact read.")
        symbol = self.target_symbol
        if symbol is not None and (
            type(symbol) is not ProjectResolvedModuleRelationSymbol
            or symbol.owning_module_path != self.read.owner.identity.module_path
            or symbol.local_name != self.read.relation_name
        ):
            raise ValueError("Resolved expression read must use its scoped lookup.")


_LET_ISSUE_CODES = {
    ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NAME_COLLISION: "PIE-S2001",
    ProjectModuleRelationResolutionIssueStatus.LET_RELATION_UNREAD: LET_UNREAD_CODE,
    ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NESTING_LIMIT: (
        LET_NESTING_CODE
    ),
}


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleRelationSymbol:
    """One module-local relation name bound to one exact nominal declaration."""

    owning_module_path: str
    local_name: str
    target_identity: ProjectNominalDeclarationIdentity
    target_occurrence: ProjectDeclarationOccurrence
    local_occurrence: ProjectDeclarationOccurrence | None = None
    imported_binding: ProjectResolvedImportedBinding | None = None

    def __post_init__(self) -> None:
        """Reject facts that collapse a local alias and nominal identity."""

        ProjectModuleIdentity(path=self.owning_module_path)
        if type(self.local_name) is not str or not self.local_name:
            raise ValueError("Resolved relation symbol requires a local name.")
        if type(self.target_identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Resolved relation symbol requires a target identity.")
        if type(self.target_occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Resolved relation symbol requires a target occurrence.")
        _validate_relation_identity(self.target_identity)
        if self.target_occurrence.identity != self.target_identity:
            raise ValueError("Resolved relation target occurrence must match identity.")
        local = self.local_occurrence
        imported = self.imported_binding
        if (local is None) == (imported is None):
            raise ValueError(
                "Resolved relation symbol requires exactly one binding source."
            )
        if local is not None:
            if type(local) is not ProjectDeclarationOccurrence:
                raise TypeError("Local relation symbol requires an occurrence.")
            if (
                local is not self.target_occurrence
                or local.identity != self.target_identity
                or self.target_identity.module_path != self.owning_module_path
                or self.target_identity.declared_name != self.local_name
            ):
                raise ValueError("Local relation symbol must retain local identity.")
        else:
            if type(imported) is not ProjectResolvedImportedBinding:
                raise TypeError("Imported relation symbol requires a binding.")
            if (
                imported.identity.owning_module_path != self.owning_module_path
                or imported.identity.local_binding_name != self.local_name
                or imported.target_identity != self.target_identity
                or imported.identity.namespace is not ProjectSymbolNamespace.RELATION
                or imported.identity.declaration_kind
                is not self.target_identity.declaration_kind
            ):
                raise ValueError(
                    "Imported relation symbol must preserve local and target identity."
                )

    @property
    def declaration_kind(self) -> ProjectSymbolKind:
        """Return the exact relation-producing target declaration kind."""

        return self.target_identity.declaration_kind


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationReference:
    """One exact TableDef or QueryDef from-clause reference."""

    owner: ProjectDeclarationOccurrence
    from_clause: FromClause

    def __post_init__(self) -> None:
        """Require the reference to match its retained relation AST site."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Module relation reference requires an owner occurrence.")
        if type(self.from_clause) is not FromClause:
            raise TypeError("Module relation reference requires a FromClause.")
        definition = self.owner.definition
        if type(definition) not in {TableDef, QueryDef}:
            raise ValueError("Module relation reference must match its retained AST.")
        relation_definition = cast(TableDef | QueryDef, definition)
        if (
            self.owner.identity.declaration_kind
            not in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
            or relation_definition.from_clause is not self.from_clause
        ):
            raise ValueError("Module relation reference must match its retained AST.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectResolvedModuleRelationReference:
    """One exact module relation reference resolved to one nominal target."""

    reference: ProjectModuleRelationReference
    target_symbol: ProjectResolvedModuleRelationSymbol

    def __post_init__(self) -> None:
        """Require relation-namespace lookup through the exact local name."""

        if type(self.reference) is not ProjectModuleRelationReference:
            raise TypeError("Resolved relation reference requires a reference.")
        if type(self.target_symbol) is not ProjectResolvedModuleRelationSymbol:
            raise TypeError("Resolved relation reference requires a target symbol.")
        if (
            self.target_symbol.owning_module_path
            != self.reference.owner.identity.module_path
            or self.target_symbol.local_name != self.reference.from_clause.source_name
        ):
            raise ValueError("Resolved relation reference must use its local lookup.")


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectModuleSetOperandReference:
    """One exact set operand occurrence, distinct from a FROM clause."""

    owner: ProjectDeclarationOccurrence
    operand_ordinal: int
    operand: SetOperand = field(init=False)

    def __post_init__(self) -> None:
        definition = self.owner.definition
        if (
            type(definition) is not SetRelationDef
            or type(self.operand_ordinal) is not int
            or not 0 <= self.operand_ordinal < len(definition.body.operands)
        ):
            raise ValueError("Set reference requires its exact owner/operand ordinal.")
        object.__setattr__(
            self, "operand", definition.body.operands[self.operand_ordinal]
        )


@dataclass(frozen=True, slots=True, kw_only=True, eq=False)
class ProjectResolvedSetOperand:
    """Complete existing binding authority for one authored operand use."""

    environment: ProjectModuleRelationResolutionEnvironment = field(repr=False)
    reference: ProjectModuleSetOperandReference
    candidates: tuple[ProjectResolvedModuleRelationSymbol, ...] = field(init=False)
    blockers: tuple[ProjectModuleRelationResolutionIssue, ...] = field(init=False)
    diagnostics: tuple[Diagnostic, ...] = field(init=False)

    def __post_init__(self) -> None:
        reference = self.reference
        if type(reference) is not ProjectModuleSetOperandReference or not any(
            f.owner is reference.owner for f in self.environment.row_facts
        ):
            raise ValueError(
                "Set operand resolution requires its exact environment owner."
            )
        name = reference.operand.relation_name
        candidates = self.environment.find_scoped_relation_name(reference.owner, name)
        blockers = (
            self.environment.find_scoped_issues(reference.owner, name)
            if not candidates
            else ()
        )
        diagnostics = tuple(
            d
            for issue in blockers
            for d in (
                (issue.diagnostic,)
                if issue.diagnostic is not None
                else issue.suppressing_diagnostics
            )
        )
        if not candidates and not diagnostics:
            location = _location(
                reference.operand.span, fallback_path=self.environment.module.path
            )
            diagnostics = (
                _diagnostic(
                    code="PIE-S2301",
                    message=f"Unknown relation: {name}",
                    location=location,
                ),
            )
        object.__setattr__(self, "candidates", candidates)
        object.__setattr__(self, "blockers", blockers)
        object.__setattr__(self, "diagnostics", diagnostics)

    @property
    def site(self) -> SetOperand:
        return self.reference.operand

    @property
    def target_symbol(self) -> ProjectResolvedModuleRelationSymbol | None:
        return (
            self.candidates[0]
            if len(self.candidates) == 1 and not self.blockers
            else None
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationRowFact:
    """One minimal row availability fact for a relation-producing declaration."""

    owner: ProjectDeclarationOccurrence
    state: ProjectRelationRowSchemaState

    def __post_init__(self) -> None:
        """Require an existing row-state carrier and one relation declaration."""

        if type(self.owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Module relation row fact requires an owner occurrence.")
        _validate_relation_identity(self.owner.identity)
        if type(self.state) is not ProjectRelationRowSchemaState:
            raise TypeError("Module relation row fact requires an exact row state.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionIssue:
    """One typed emitted or root-suppressed Slice 10 relation issue."""

    status: ProjectModuleRelationResolutionIssueStatus
    owning_module_path: str
    local_name: str | None
    location: SourceLocation
    related_locations: tuple[SourceLocation, ...] = ()
    diagnostic: Diagnostic | None = None
    occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    reference: ProjectModuleRelationReference | None = None
    select_item: SelectItem | None = None
    binding_issues: tuple[ProjectModuleBindingIssue, ...] = ()
    module_cycle: ProjectModuleCycle | None = None
    relation_cycle: tuple[ProjectDeclarationOccurrence, ...] = ()
    type_source_issues: tuple[ProjectTypeSourceResolutionIssue, ...] = ()
    suppressing_diagnostics: tuple[Diagnostic, ...] = ()

    def __post_init__(self) -> None:
        """Reject mixed evidence and incorrect one-way diagnostic adaptation."""

        if type(self.status) is not ProjectModuleRelationResolutionIssueStatus:
            raise TypeError("Relation issue requires an exact status.")
        ProjectModuleIdentity(path=self.owning_module_path)
        if self.local_name is not None and (
            type(self.local_name) is not str or not self.local_name
        ):
            raise ValueError("Relation issue local name must be non-empty.")
        if type(self.location) is not SourceLocation:
            raise TypeError("Relation issue requires a source location.")
        _require_tuple_items(
            self.related_locations,
            SourceLocation,
            "Relation issue related locations",
        )
        _require_tuple_items(
            self.occurrences,
            ProjectDeclarationOccurrence,
            "Relation issue occurrences",
        )
        _require_tuple_items(
            self.binding_issues,
            ProjectModuleBindingIssue,
            "Relation issue binding issues",
        )
        _require_tuple_items(
            self.relation_cycle,
            ProjectDeclarationOccurrence,
            "Relation issue cycle",
        )
        _require_tuple_items(
            self.type_source_issues,
            ProjectTypeSourceResolutionIssue,
            "Relation issue type/source roots",
        )
        _require_tuple_items(
            self.suppressing_diagnostics,
            Diagnostic,
            "Relation issue suppressing diagnostics",
        )
        if self.diagnostic is not None:
            if type(self.diagnostic) is not Diagnostic:
                raise TypeError("Relation issue diagnostic must be a Diagnostic.")
            if (
                self.diagnostic.severity is not Severity.ERROR
                or self.diagnostic.location != self.location
                # Only a Collect read refusal says how to write it instead.
                or (
                    self.diagnostic.suggestion is not None
                    and self.diagnostic.code != "PIE-S2803"
                )
                or self.suppressing_diagnostics
            ):
                raise ValueError("Emitted relation diagnostic must be exact.")
        elif not self.suppressing_diagnostics:
            raise ValueError("Suppressed relation issue requires its root.")
        _validate_issue_evidence(self)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionEnvironment:
    """One dependency-ordered module-local relation and row-fact result."""

    module: ProjectLogicalModule
    symbols: tuple[ProjectResolvedModuleRelationSymbol, ...] = ()
    references: tuple[ProjectModuleRelationReference, ...] = ()
    resolutions: tuple[ProjectResolvedModuleRelationReference, ...] = ()
    row_facts: tuple[ProjectModuleRelationRowFact, ...] = ()
    issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()
    let_symbols: tuple[ProjectResolvedModuleRelationSymbol, ...] = ()
    blocked_let_scopes: tuple[tuple[int, str], ...] = ()
    expression_reads: tuple[ProjectResolvedExpressionBlockRead, ...] = ()
    # One symbol per table-function occurrence, bound only to its own reader.
    table_function_symbols: tuple[ProjectResolvedModuleRelationSymbol, ...] = ()
    # One symbol per Unnest occurrence, bound only to its own JOIN by
    # identity (D-S05-1); no scoped name lookup ever returns one.
    unnest_symbols: tuple[ProjectResolvedModuleRelationSymbol, ...] = ()
    _symbols_by_name: Mapping[str, tuple[ProjectResolvedModuleRelationSymbol, ...]] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _let_symbols_by_scope: Mapping[
        tuple[int, str], tuple[ProjectResolvedModuleRelationSymbol, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)
    _resolutions_by_from_clause: Mapping[
        FromClause, tuple[ProjectResolvedModuleRelationReference, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)
    _row_facts_by_definition: Mapping[
        _DefinitionT, tuple[ProjectModuleRelationRowFact, ...]
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Copy lookup buckets and reject reordered or foreign facts."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Relation environment requires a logical module.")
        if (
            self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or self.module.parsed_input is None
        ):
            raise ValueError("Relation environment requires a parsed module.")
        _require_tuple_items(
            self.symbols,
            ProjectResolvedModuleRelationSymbol,
            "Relation environment symbols",
        )
        _require_tuple_items(
            self.references,
            ProjectModuleRelationReference,
            "Relation environment references",
        )
        _require_tuple_items(
            self.resolutions,
            ProjectResolvedModuleRelationReference,
            "Relation environment resolutions",
        )
        _require_tuple_items(
            self.row_facts,
            ProjectModuleRelationRowFact,
            "Relation environment row facts",
        )
        _require_tuple_items(
            self.issues,
            ProjectModuleRelationResolutionIssue,
            "Relation environment issues",
        )
        _require_tuple_items(
            self.let_symbols,
            ProjectResolvedModuleRelationSymbol,
            "Relation environment let symbols",
        )
        _require_tuple_items(
            self.expression_reads,
            ProjectResolvedExpressionBlockRead,
            "Relation environment expression reads",
        )
        if any(
            item.read.owner.identity.module_path != self.module.path
            for item in self.expression_reads
        ):
            raise ValueError("Expression reads must be module-local.")
        _require_tuple_items(
            self.table_function_symbols,
            ProjectResolvedModuleRelationSymbol,
            "Relation environment table-function symbols",
        )
        if any(
            symbol.local_occurrence is None
            or symbol.local_occurrence.table_function is None
            or symbol.owning_module_path != self.module.path
            for symbol in self.table_function_symbols
        ) or len({id(s.local_occurrence) for s in self.table_function_symbols}) != len(
            self.table_function_symbols
        ):
            raise ValueError(
                "Table-function symbols must retain their module-local occurrence."
            )
        _require_tuple_items(
            self.unnest_symbols,
            ProjectResolvedModuleRelationSymbol,
            "Relation environment Unnest symbols",
        )
        if any(
            symbol.local_occurrence is None
            or symbol.local_occurrence.unnest is None
            or symbol.owning_module_path != self.module.path
            for symbol in self.unnest_symbols
        ) or len({id(s.local_occurrence) for s in self.unnest_symbols}) != len(
            self.unnest_symbols
        ):
            raise ValueError(
                "Unnest symbols must retain their module-local occurrence."
            )
        if type(self.blocked_let_scopes) is not tuple or any(
            type(item) is not tuple
            or len(item) != 2
            or type(item[0]) is not int
            or type(item[1]) is not str
            for item in self.blocked_let_scopes
        ):
            raise TypeError("Relation environment blocked let scopes must be exact.")
        let_scopes: dict[
            tuple[int, str], list[ProjectResolvedModuleRelationSymbol]
        ] = {}
        for symbol in self.let_symbols:
            let = symbol.local_occurrence
            if (
                let is None
                or let.let_position is None
                or symbol.owning_module_path != self.module.path
            ):
                raise ValueError("Let symbols must retain their module-local let.")
            let_scopes.setdefault(
                (let.declaration_position, symbol.local_name), []
            ).append(symbol)
        if any(len(items) != 1 for items in let_scopes.values()) or set(
            let_scopes
        ) & set(self.blocked_let_scopes):
            raise ValueError("Let symbol scopes cannot select a winner.")
        object.__setattr__(self, "_let_symbols_by_scope", _tuple_mapping(let_scopes))
        module_path = self.module.path
        if any(symbol.owning_module_path != module_path for symbol in self.symbols):
            raise ValueError("Relation environment symbols must be module-local.")
        if any(
            reference.owner.identity.module_path != module_path
            for reference in self.references
        ):
            raise ValueError("Relation environment references must be module-local.")
        if any(
            resolution.reference not in self.references
            for resolution in self.resolutions
        ):
            raise ValueError("Relation resolutions require retained references.")
        if any(
            fact.owner.identity.module_path != module_path for fact in self.row_facts
        ):
            raise ValueError("Relation row facts must be module-local.")
        if any(issue.owning_module_path != module_path for issue in self.issues):
            raise ValueError("Relation environment issues must be module-local.")

        symbols: dict[str, list[ProjectResolvedModuleRelationSymbol]] = {}
        for symbol in self.symbols:
            symbols.setdefault(symbol.local_name, []).append(symbol)
        if any(len(items) != 1 for items in symbols.values()):
            raise ValueError("Relation symbol buckets cannot select a winner.")
        resolutions: dict[FromClause, list[ProjectResolvedModuleRelationReference]] = {}
        for resolution in self.resolutions:
            resolutions.setdefault(resolution.reference.from_clause, []).append(
                resolution
            )
        row_facts: dict[_DefinitionT, list[ProjectModuleRelationRowFact]] = {}
        for fact in self.row_facts:
            definition = fact.owner.definition
            if type(definition) not in {
                SourceDef,
                TableDef,
                QueryDef,
                SetRelationDef,
                ValuesRelationDef,
                TableFunctionRelationDef,
                UnnestRelationDef,
            }:
                raise ValueError("Relation row fact requires a relation definition.")
            row_facts.setdefault(cast(_DefinitionT, definition), []).append(fact)
        if any(
            len(items) != 1 for items in (*resolutions.values(), *row_facts.values())
        ):
            raise ValueError("Relation AST lookup buckets must be unambiguous.")
        object.__setattr__(self, "_symbols_by_name", _tuple_mapping(symbols))
        object.__setattr__(
            self,
            "_resolutions_by_from_clause",
            _tuple_mapping(resolutions),
        )
        object.__setattr__(
            self,
            "_row_facts_by_definition",
            _tuple_mapping(row_facts),
        )

    def find_relation_name(
        self, local_name: str
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return the complete exact local relation-name bucket."""

        if type(local_name) is not str:
            raise TypeError("Relation-name lookup requires a string.")
        return self._symbols_by_name.get(local_name, ())

    def find_scoped_relation_name(
        self, owner: ProjectDeclarationOccurrence, local_name: str
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return the bucket a relation name read by one owner's body names.

        A declaration's lets and the module namespace share one scope; a let
        name in collision resolves to nothing, never to the module symbol it
        would otherwise hide.
        """

        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Scoped relation lookup requires an owner occurrence.")
        if type(local_name) is not str:
            raise TypeError("Relation-name lookup requires a string.")
        scope = (owner.declaration_position, local_name)
        if scope in self.blocked_let_scopes:
            return ()
        return self._let_symbols_by_scope.get(scope) or self.find_relation_name(
            local_name
        )

    def find_unnest_symbol(
        self, occurrence: ProjectDeclarationOccurrence
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return the one symbol of an exact Unnest occurrence, or empty."""

        return tuple(
            symbol
            for symbol in self.unnest_symbols
            if symbol.local_occurrence is occurrence
        )

    def find_scoped_issues(
        self, owner: ProjectDeclarationOccurrence, local_name: str
    ) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
        """Return the issues naming a relation one owner's body reads.

        An issue whose evidence holds a let (an occurrence, a member of its
        relation cycle or the owner of its reference) belongs to that let's
        declaration only, an unknown JOIN input to its relation only, and an
        unknown FROM or expression read to the declaration that reads it, with
        its lets: another declaration's read of the name reports its own
        error. Every other issue stays visible to the whole module.
        """

        if type(owner) is not ProjectDeclarationOccurrence:
            raise TypeError("Scoped issue lookup requires an owner occurrence.")
        return tuple(
            issue
            for issue in self.issues
            if issue.local_name == local_name
            and (
                issue.status
                is not ProjectModuleRelationResolutionIssueStatus.UNKNOWN_JOIN_INPUT
                or issue.occurrences[0] is owner
            )
            and (
                issue.status not in _UNKNOWN_READ_ISSUE_STATUSES
                or (
                    issue.occurrences[0]
                    if issue.reference is None
                    else issue.reference.owner
                ).declaration_position
                == owner.declaration_position
            )
            and all(
                item.let_position is None
                or item.declaration_position == owner.declaration_position
                for item in (
                    *issue.occurrences,
                    *issue.relation_cycle,
                    *(() if issue.reference is None else (issue.reference.owner,)),
                )
            )
        )

    def find_from_clause(
        self, from_clause: FromClause
    ) -> tuple[ProjectResolvedModuleRelationReference, ...]:
        """Return one exact resolution for a retained from-clause, or empty."""

        if type(from_clause) is not FromClause:
            raise TypeError("From-clause lookup requires a FromClause.")
        return self._resolutions_by_from_clause.get(from_clause, ())

    def find_definition(
        self, definition: _DefinitionT
    ) -> tuple[ProjectModuleRelationRowFact, ...]:
        """Return one exact row fact for a retained relation definition."""

        if type(definition) not in {
            SourceDef,
            TableDef,
            QueryDef,
            SetRelationDef,
            ValuesRelationDef,
            TableFunctionRelationDef,
            UnnestRelationDef,
        }:
            raise TypeError("Row-fact lookup requires a relation definition.")
        return self._row_facts_by_definition.get(definition, ())


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRelationResolutionSet:
    """The complete private schema-v2 Slice 10 resolution product."""

    dependency_order: tuple[ProjectModuleIdentity, ...] = ()
    environments: tuple[ProjectModuleRelationResolutionEnvironment, ...] = ()
    issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    _environments_by_path: Mapping[str, ProjectModuleRelationResolutionEnvironment] = (
        field(init=False, repr=False, compare=False, hash=False)
    )
    _symbols_by_target_identity: Mapping[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectResolvedModuleRelationSymbol, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Require dependency order and exact issue-to-diagnostic projection."""

        _require_tuple_items(
            self.dependency_order,
            ProjectModuleIdentity,
            "Relation dependency order",
        )
        _require_tuple_items(
            self.environments,
            ProjectModuleRelationResolutionEnvironment,
            "Relation environments",
        )
        _require_tuple_items(
            self.issues,
            ProjectModuleRelationResolutionIssue,
            "Relation issues",
        )
        _require_tuple_items(self.diagnostics, Diagnostic, "Relation diagnostics")
        paths = tuple(environment.module.path for environment in self.environments)
        if paths != tuple(identity.path for identity in self.dependency_order):
            raise ValueError("Relation environments must follow dependency order.")
        if len(set(paths)) != len(paths):
            raise ValueError("Relation environment paths must be unique.")
        expected = tuple(
            issue.diagnostic for issue in self.issues if issue.diagnostic is not None
        )
        if self.diagnostics != expected:
            raise ValueError("Relation diagnostics must project exact issues.")
        object.__setattr__(
            self,
            "_environments_by_path",
            MappingProxyType(
                {
                    environment.module.path: environment
                    for environment in self.environments
                }
            ),
        )
        symbols: dict[
            ProjectNominalDeclarationIdentity,
            list[ProjectResolvedModuleRelationSymbol],
        ] = {}
        for environment in self.environments:
            for symbol in environment.symbols:
                symbols.setdefault(symbol.target_identity, []).append(symbol)
        object.__setattr__(
            self,
            "_symbols_by_target_identity",
            _tuple_mapping(symbols),
        )

    def find_module_path(
        self, module_path: str
    ) -> tuple[ProjectModuleRelationResolutionEnvironment, ...]:
        """Return one exact acyclic module environment, or empty."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        environment = self._environments_by_path.get(module_path)
        return () if environment is None else (environment,)

    def find_target_identity(
        self, identity: ProjectNominalDeclarationIdentity
    ) -> tuple[ProjectResolvedModuleRelationSymbol, ...]:
        """Return every local/imported symbol retaining one nominal target."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Target lookup requires a nominal identity.")
        return self._symbols_by_target_identity.get(identity, ())


@dataclass(slots=True)
class _RelationResolutionDraft:
    module: ProjectLogicalModule
    catalog: ProjectModuleCatalog
    binding_environment: ProjectModuleBindingEnvironment
    type_source_environment: ProjectModuleTypeSourceResolutionEnvironment
    symbols: list[ProjectResolvedModuleRelationSymbol]
    references: list[ProjectModuleRelationReference]
    resolutions: list[ProjectResolvedModuleRelationReference]
    row_facts: dict[ProjectDeclarationOccurrence, ProjectModuleRelationRowFact]
    issues: list[ProjectModuleRelationResolutionIssue]
    blocked_names: set[str]
    ambiguous_names: set[str]
    let_symbols: list[ProjectResolvedModuleRelationSymbol] = field(default_factory=list)
    blocked_let_scopes: set[tuple[int, str]] = field(default_factory=set)
    expression_reads: list[ProjectResolvedExpressionBlockRead] = field(
        default_factory=list
    )
    table_function_symbols: list[ProjectResolvedModuleRelationSymbol] = field(
        default_factory=list
    )
    unnest_symbols: list[ProjectResolvedModuleRelationSymbol] = field(
        default_factory=list
    )


@dataclass(frozen=True, slots=True)
class _LocalRelationCycle:
    occurrences: tuple[ProjectDeclarationOccurrence, ...]
    references: tuple[ProjectModuleRelationReference, ...]


def _build_project_module_relation_resolution_set(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> ProjectModuleRelationResolutionSet:
    """Build pure dependency-first schema-v2 relation and minimal row facts."""

    _validate_builder_inputs(
        modules,
        catalogs,
        exports,
        bindings,
        graph,
        module_diagnostics,
        type_source_resolutions,
    )
    dependency_vertices = _dependency_first_vertices(graph)
    dependency_order = tuple(vertex.identity for vertex in dependency_vertices)
    if dependency_order != type_source_resolutions.dependency_order:
        raise ValueError("Slice 10 must reuse the exact Slice 9 dependency order.")

    cyclic_paths = {
        member.identity.path
        for cycle in graph.cycles
        for member in cycle.component.members
    }
    cycle_by_path = {
        member.identity.path: cycle
        for cycle in graph.cycles
        for member in cycle.component.members
    }
    catalog_by_path = {catalog.module_path: catalog for catalog in catalogs.catalogs}
    binding_by_path = {
        environment.module.path: environment for environment in bindings.environments
    }
    type_source_by_path = {
        environment.module.path: environment
        for environment in type_source_resolutions.environments
    }
    surface_by_path = {surface.module.path: surface for surface in exports.surfaces}
    environment_by_path: dict[str, ProjectModuleRelationResolutionEnvironment] = {}
    row_fact_by_identity: dict[
        ProjectNominalDeclarationIdentity, ProjectModuleRelationRowFact
    ] = {}
    environments: list[ProjectModuleRelationResolutionEnvironment] = []
    all_issues: list[ProjectModuleRelationResolutionIssue] = []

    for vertex in dependency_vertices:
        module = vertex.module
        draft = _RelationResolutionDraft(
            module=module,
            catalog=catalog_by_path[module.path],
            binding_environment=binding_by_path[module.path],
            type_source_environment=type_source_by_path[module.path],
            symbols=[],
            references=[],
            resolutions=[],
            row_facts={},
            issues=[],
            blocked_names=set(),
            ambiguous_names=set(),
        )
        _collect_module_diagnostic_blockers(draft, module_diagnostics)
        _collect_local_symbols(draft)
        _collect_imported_symbols(
            draft,
            catalogs=catalogs,
            target_surface_by_path=surface_by_path,
            environment_by_path=environment_by_path,
            cyclic_paths=cyclic_paths,
            cycle_by_path=cycle_by_path,
            module_diagnostics=module_diagnostics,
        )
        _collect_let_symbols(draft)
        _collect_and_resolve_references(draft)
        cycles = _local_relation_cycles(draft)
        _append_local_cycle_issues(draft, cycles)
        _build_module_row_facts(
            draft,
            catalogs=catalogs,
            bindings=bindings,
            type_source_resolutions=type_source_resolutions,
            row_fact_by_identity=row_fact_by_identity,
            cycles=cycles,
        )
        ordered_issues = tuple(sorted(draft.issues, key=_issue_source_key))
        environment = ProjectModuleRelationResolutionEnvironment(
            module=module,
            symbols=tuple(draft.symbols),
            references=tuple(draft.references),
            resolutions=tuple(draft.resolutions),
            row_facts=tuple(
                draft.row_facts[occurrence]
                for occurrence in draft.catalog.relation_owners
                if occurrence in draft.row_facts
            ),
            issues=ordered_issues,
            let_symbols=tuple(draft.let_symbols),
            blocked_let_scopes=tuple(sorted(draft.blocked_let_scopes)),
            expression_reads=tuple(draft.expression_reads),
            table_function_symbols=tuple(draft.table_function_symbols),
            unnest_symbols=tuple(draft.unnest_symbols),
        )
        environments.append(environment)
        environment_by_path[module.path] = environment
        all_issues.extend(ordered_issues)
        for fact in environment.row_facts:
            if len(catalogs.find_identity(fact.owner.identity)) == 1:
                row_fact_by_identity[fact.owner.identity] = fact

    cycle_issues = _module_cycle_issues(graph, module_diagnostics)
    all_issues.extend(cycle_issues)
    issue_tuple = tuple(all_issues)
    return ProjectModuleRelationResolutionSet(
        dependency_order=dependency_order,
        environments=tuple(environments),
        issues=issue_tuple,
        diagnostics=tuple(
            issue.diagnostic for issue in issue_tuple if issue.diagnostic is not None
        ),
    )


def _collect_module_diagnostic_blockers(
    draft: _RelationResolutionDraft,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    binding_buckets: dict[str, list[ProjectModuleBindingIssue]] = {}
    for issue in draft.binding_environment.issues:
        if issue.status is ProjectModuleBindingIssueStatus.DUPLICATE_SOURCE_REQUEST:
            continue
        kind = issue.request.identity.declaration_kind
        if (
            kind not in _RELATION_KINDS
            and issue.status not in _COLLISION_ISSUE_STATUSES
            and not _imports_relation_as_other_kind(draft, issue)
        ):
            continue
        binding_buckets.setdefault(
            issue.request.identity.local_binding_name, []
        ).append(issue)

    for local_name, issues in binding_buckets.items():
        issue_tuple = tuple(issues)
        roots = _suppressing_diagnostics_for_binding_issues(
            issue_tuple,
            module_diagnostics,
        )
        if not roots:
            raise ValueError("Blocked relation binding requires a Slice 8 root.")
        request = min(
            (issue.request for issue in issue_tuple),
            key=lambda item: (item.module_statement_position, item.item_position),
        )
        span = (
            request.source_item.local_name_span
            or request.source_item.exported_name_span
        )
        location = _location(span, fallback_path=draft.module.path)
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                owning_module_path=draft.module.path,
                local_name=local_name,
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(root.location for root in roots),
                ),
                binding_issues=issue_tuple,
                suppressing_diagnostics=roots,
            )
        )
        draft.blocked_names.add(local_name)

    export_buckets: dict[str, list[ProjectModuleExportIssue]] = {}
    for fact in module_diagnostics.facts:
        for issue in fact.export_issues:
            if (
                issue.request.owning_module_path != draft.module.path
                or issue.status
                is not ProjectModuleExportIssueStatus.AMBIGUOUS_LOCAL_DECLARATION
                or issue.request.declaration_kind not in _RELATION_KINDS
            ):
                continue
            export_buckets.setdefault(issue.request.local_name, []).append(issue)

    for local_name, issues in export_buckets.items():
        issue_tuple = tuple(issues)
        roots = _suppressing_diagnostics_for_export_issues(
            issue_tuple,
            module_diagnostics,
        )
        occurrences = tuple(
            occurrence
            for issue in issue_tuple
            for occurrence in issue.local_occurrences
        )
        if not roots or len(occurrences) < 2:
            raise ValueError("Blocked relation export requires its Slice 8 root.")
        location = roots[0].location
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                owning_module_path=draft.module.path,
                local_name=local_name,
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(
                        _location(
                            occurrence.definition.span,
                            fallback_path=draft.module.path,
                        )
                        for occurrence in occurrences
                    ),
                ),
                occurrences=occurrences,
                suppressing_diagnostics=roots,
            )
        )
        draft.blocked_names.add(local_name)


def _imports_relation_as_other_kind(
    draft: _RelationResolutionDraft, issue: ProjectModuleBindingIssue
) -> bool:
    """Whether a failed import asks for a name that its target declares or
    exports only as a relation, with another kind (`shape customers` of a
    source alone), and the module declares no relation of that name: its
    relation reads of the name follow the import's own error, as when the
    import asks for a relation. A target that also has the name in the
    requested namespace, of any kind, does not count: the module never
    imported the relation."""

    name = issue.request.identity.local_binding_name
    return issue.asks_for(ProjectSymbolNamespace.RELATION) and not any(
        item.identity.declared_name == name
        and item.identity.declaration_kind in _RELATION_KINDS
        for item in draft.catalog.occurrences
    )


def _collect_local_symbols(draft: _RelationResolutionDraft) -> None:
    buckets: dict[str, list[ProjectDeclarationOccurrence]] = {}
    for occurrence in draft.catalog.occurrences:
        if occurrence.identity.declaration_kind in _RELATION_KINDS:
            buckets.setdefault(occurrence.identity.declared_name, []).append(occurrence)

    source_duplicate_roots = _source_duplicate_roots(draft.type_source_environment)
    for local_name, occurrences in buckets.items():
        occurrence_tuple = tuple(occurrences)
        if len(occurrences) > 1:
            draft.ambiguous_names.add(local_name)
            if local_name in draft.blocked_names:
                continue
            type_source_issues = source_duplicate_roots.get(local_name, ())
            if type_source_issues:
                roots = tuple(
                    issue.diagnostic
                    for issue in type_source_issues
                    if issue.diagnostic is not None
                )
                if not roots:
                    raise ValueError("Slice 9 source duplicate requires its root.")
                location = roots[0].location
                draft.issues.append(
                    ProjectModuleRelationResolutionIssue(
                        status=ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
                        owning_module_path=draft.module.path,
                        local_name=local_name,
                        location=location,
                        related_locations=_ordered_related_locations(
                            location,
                            tuple(root.location for root in roots),
                        ),
                        occurrences=occurrence_tuple,
                        type_source_issues=type_source_issues,
                        suppressing_diagnostics=roots,
                    )
                )
            else:
                draft.issues.append(
                    _duplicate_relation_issue(
                        draft.module.path,
                        local_name,
                        occurrence_tuple,
                    )
                )
            continue
        if local_name not in draft.blocked_names:
            draft.symbols.append(
                _local_relation_symbol(draft.module.path, occurrences[0])
            )


def _let_scope_reads(
    owners: tuple[ProjectDeclarationOccurrence, ...],
) -> tuple[tuple[ProjectDeclarationOccurrence, str], ...]:
    """Return every relation-name read written in one declaration scope."""

    return tuple((owner, name) for owner in owners for name in relation_reads(owner))


def _let_nesting_depths(
    lets: tuple[ProjectDeclarationOccurrence, ...],
    reads: tuple[tuple[ProjectDeclarationOccurrence, str], ...],
) -> dict[int, int]:
    """Return each let's deepest read-path depth below its declaration body.

    The body (key -1) is depth 0 and a let read by a block at depth ``d`` is at
    least ``d + 1``. A let on or below a cycle, or read by no path from the
    body, has no depth: the cycle or the unread let is its own error.
    """

    position = {let.identity.declared_name: cast(int, let.let_position) for let in lets}
    edges = {
        (-1 if owner.let_position is None else owner.let_position, position[name])
        for owner, name in reads
        if name in position
    }
    pending = {key: 0 for key in (-1, *position.values())}
    for _reader, target in edges:
        pending[target] += 1
    depths: dict[int, int] = {-1: 0}
    ready = [key for key, count in pending.items() if count == 0]
    while ready:
        reader = ready.pop()
        for edge_reader, target in edges:
            if edge_reader != reader:
                continue
            if reader in depths:
                depths[target] = max(depths.get(target, 0), depths[reader] + 1)
            pending[target] -= 1
            if pending[target] == 0:
                ready.append(target)
    depths.pop(-1)
    return depths


def _collect_let_symbols(draft: _RelationResolutionDraft) -> None:
    """Bind each declaration's lets in its own scope, never in the module.

    A let named like another let of the declaration, a local relation or a
    relation import binding, resolved or not, is a collision with no winner.
    Any block of the declaration may read a let any number of times, before or
    after it; a let no block reads, or one nested deeper than the query-block
    limit, is an error. A cycle through lets is a relation cycle (PIE-S2302).
    """

    module_names: dict[str, list[ProjectDeclarationOccurrence]] = {}
    for occurrence in draft.catalog.occurrences:
        if occurrence.identity.namespace is ProjectSymbolNamespace.RELATION:
            module_names.setdefault(occurrence.identity.declared_name, []).append(
                occurrence
            )
    imported: dict[str, list[SourceLocation]] = {}
    for request in draft.binding_environment.requests:
        if request.identity.namespace is ProjectSymbolNamespace.RELATION:
            item = request.source_item
            imported.setdefault(request.identity.local_binding_name, []).append(
                _location(
                    item.local_name_span or item.exported_name_span,
                    fallback_path=draft.module.path,
                )
            )
    for occurrence in draft.catalog.occurrences:
        lets = draft.catalog.find_lets(occurrence.declaration_position)
        if not lets:
            continue
        reads = _let_scope_reads((*lets, occurrence))
        readable: list[ProjectDeclarationOccurrence] = []
        by_name: dict[str, list[ProjectDeclarationOccurrence]] = {}
        for let in lets:
            by_name.setdefault(let.identity.declared_name, []).append(let)
        for name, items in by_name.items():
            scope = (occurrence.declaration_position, name)
            others = tuple(
                _location(item.definition.span, fallback_path=draft.module.path)
                for item in module_names.get(name, ())
            )
            others += tuple(
                _location(join.span, fallback_path=draft.module.path)
                for owner in (*lets, occurrence)
                if type(owner.definition) in {TableDef, QueryDef}
                for join in cast(TableDef | QueryDef, owner.definition).join_clauses
                if join.target_binding_name == name
                and join.target_relation_name != name
            )
            # A table-function binding names rows of its body like a JOIN
            # binding, so it shares this scope too.
            others += tuple(
                _location(clause.span, fallback_path=draft.module.path)
                for owner in (*lets, occurrence)
                if (clause := table_function_input(owner.authored)) is not None
                and clause.binding_name == name
            )
            others += tuple(imported.get(name, ()))
            if len(items) > 1 or others:
                draft.blocked_let_scopes.add(scope)
                primary = items[1] if len(items) > 1 else items[0]
                location = _location(
                    primary.definition.span, fallback_path=draft.module.path
                )
                draft.issues.append(
                    ProjectModuleRelationResolutionIssue(
                        status=ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NAME_COLLISION,
                        owning_module_path=draft.module.path,
                        local_name=name,
                        location=location,
                        related_locations=_ordered_related_locations(
                            location,
                            (
                                *(
                                    _location(
                                        item.definition.span,
                                        fallback_path=draft.module.path,
                                    )
                                    for item in items
                                ),
                                *others,
                            ),
                        ),
                        diagnostic=_diagnostic(
                            code="PIE-S2001",
                            message=(
                                f"Duplicate symbol name in relation namespace: {name}"
                            ),
                            location=location,
                        ),
                        occurrences=tuple(items),
                    )
                )
                continue
            if name in draft.blocked_names or name in draft.ambiguous_names:
                draft.blocked_let_scopes.add(scope)
                continue
            readable.append(items[0])
        # Both errors leave the let readable: the project fails as a whole and
        # every block keeps its own static checks without a cascade.
        depths = _let_nesting_depths(tuple(readable), reads)
        for let in readable:
            draft.let_symbols.append(_local_relation_symbol(draft.module.path, let))
            name = let.identity.declared_name
            depth = depths.get(cast(int, let.let_position), 0)
            if depth > LET_NESTING_LIMIT:
                status = ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NESTING_LIMIT
                message = (
                    f"Let relation {name} is nested {depth} query blocks deep; "
                    f"the limit is {LET_NESTING_LIMIT}."
                )
            elif not any(read == name for _owner, read in reads):
                status = ProjectModuleRelationResolutionIssueStatus.LET_RELATION_UNREAD
                message = f"Let relation {name} is never read."
            else:
                continue
            location = _location(let.definition.span, fallback_path=draft.module.path)
            code = _LET_ISSUE_CODES[status]
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=status,
                    owning_module_path=draft.module.path,
                    local_name=name,
                    location=location,
                    diagnostic=_diagnostic(
                        code=code, message=message, location=location
                    ),
                    occurrences=(let,),
                )
            )


def _collect_imported_symbols(
    draft: _RelationResolutionDraft,
    *,
    catalogs: ProjectModuleCatalogSet,
    target_surface_by_path: Mapping[str, ProjectModuleExportSurface],
    environment_by_path: Mapping[str, ProjectModuleRelationResolutionEnvironment],
    cyclic_paths: set[str],
    cycle_by_path: Mapping[str, ProjectModuleCycle],
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> None:
    for binding in draft.binding_environment.bindings:
        if binding.identity.declaration_kind not in _RELATION_KINDS:
            continue
        local_name = binding.identity.local_binding_name
        if local_name in draft.blocked_names:
            continue
        direct_facade_path = binding.target_module_path
        surface = target_surface_by_path.get(direct_facade_path)
        if surface is None or binding.resolved_entry not in surface.entries:
            raise ValueError("Imported relation requires its exact target facade.")
        nominal_target_path = binding.target_identity.module_path
        cycle_path = None
        if direct_facade_path in cyclic_paths:
            cycle_path = direct_facade_path
        elif nominal_target_path in cyclic_paths:
            cycle_path = nominal_target_path
        if cycle_path is not None:
            cycle = cycle_by_path[cycle_path]
            roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
            if not roots:
                raise ValueError("Cyclic relation target requires PIE-S2703.")
            span = (
                binding.request.source_item.local_name_span
                or binding.request.source_item.exported_name_span
            )
            location = _location(span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    module_cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
            draft.blocked_names.add(local_name)
            continue
        target_environment = environment_by_path.get(nominal_target_path)
        if target_environment is None:
            raise ValueError("Imported nominal relation target must precede importer.")
        target_occurrences = catalogs.find_identity(binding.target_identity)
        if (
            len(target_occurrences) != 1
            or target_occurrences[0].identity is not binding.target_identity
        ):
            raise ValueError("Imported relation target must have one exact occurrence.")
        target_occurrence = target_occurrences[0]
        target_symbols = tuple(
            symbol
            for symbol in target_environment.symbols
            if symbol.local_occurrence is not None
            and symbol.target_identity is binding.target_identity
            and symbol.target_occurrence is target_occurrence
        )
        if len(target_symbols) != 1:
            roots = _exact_imported_target_blocker_roots(
                target_environment.issues,
                target_identity=binding.target_identity,
                target_occurrence=target_occurrence,
            )
            if not roots:
                raise ValueError("Blocked nominal relation target requires its root.")
            span = (
                binding.request.source_item.local_name_span
                or binding.request.source_item.exported_name_span
            )
            location = _location(span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    occurrences=(target_occurrence,),
                    suppressing_diagnostics=roots,
                )
            )
            draft.blocked_names.add(local_name)
            continue
        draft.symbols.append(
            ProjectResolvedModuleRelationSymbol(
                owning_module_path=draft.module.path,
                local_name=local_name,
                target_identity=binding.target_identity,
                target_occurrence=target_occurrence,
                imported_binding=binding,
            )
        )


def _exact_imported_target_blocker_roots(
    issues: tuple[ProjectModuleRelationResolutionIssue, ...],
    *,
    target_identity: ProjectNominalDeclarationIdentity,
    target_occurrence: ProjectDeclarationOccurrence,
) -> tuple[Diagnostic, ...]:
    """Return canonical roots that structurally block one exact import target."""

    if target_occurrence.identity is not target_identity:
        raise ValueError("Imported blocker target must retain its exact identity.")
    roots: list[Diagnostic] = []
    causal_statuses = {
        ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME,
        ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED,
        ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
    }
    for issue in issues:
        if (
            issue.status not in causal_statuses
            or issue.owning_module_path != target_identity.module_path
        ):
            continue
        retains_target = any(
            occurrence is target_occurrence for occurrence in issue.occurrences
        ) or (
            issue.status
            is ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED
            and any(
                occurrence is target_occurrence
                for binding_issue in issue.binding_issues
                for occurrence in binding_issue.local_occurrences
            )
        )
        if not retains_target:
            continue
        issue_roots = (
            (issue.diagnostic,)
            if issue.diagnostic is not None
            else issue.suppressing_diagnostics
        )
        for root in issue_roots:
            if not any(root is retained for retained in roots):
                roots.append(root)
    return tuple(roots)


def _collect_and_resolve_references(draft: _RelationResolutionDraft) -> None:
    draft.unnest_symbols.extend(
        _local_relation_symbol(draft.module.path, occurrence)
        for occurrence in draft.catalog.unnests
    )
    symbols_by_name = {symbol.local_name: symbol for symbol in draft.symbols}
    lets_by_scope = {
        (symbol.target_occurrence.declaration_position, symbol.local_name): symbol
        for symbol in draft.let_symbols
    }
    for occurrence in draft.catalog.relation_owners:
        definition = occurrence.definition
        if type(definition) not in {TableDef, QueryDef}:
            continue
        relation_definition = cast(TableDef | QueryDef, definition)
        reference = ProjectModuleRelationReference(
            owner=occurrence,
            from_clause=relation_definition.from_clause,
        )
        draft.references.append(reference)
        local_name = relation_definition.from_clause.source_name
        function = draft.catalog.find_table_function(occurrence)
        if function is not None:
            # The reader of a table-function input is bound to that exact
            # occurrence; its binding is never looked up in any scope.
            symbol = _local_relation_symbol(draft.module.path, function)
            draft.table_function_symbols.append(symbol)
            draft.resolutions.append(
                ProjectResolvedModuleRelationReference(
                    reference=reference, target_symbol=symbol
                )
            )
            continue
        scope = (occurrence.declaration_position, local_name)
        if scope in draft.blocked_let_scopes:
            continue
        symbol = lets_by_scope.get(scope)
        if symbol is None and (
            local_name in draft.blocked_names or local_name in draft.ambiguous_names
        ):
            continue
        if symbol is None:
            symbol = symbols_by_name.get(local_name)
        if symbol is None:
            location = _location(
                relation_definition.from_clause.span,
                fallback_path=draft.module.path,
            )
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE,
                    owning_module_path=draft.module.path,
                    local_name=local_name,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2301",
                        message=f"Unknown relation: {local_name}",
                        location=location,
                    ),
                    reference=reference,
                )
            )
            continue
        draft.resolutions.append(
            ProjectResolvedModuleRelationReference(
                reference=reference,
                target_symbol=symbol,
            )
        )
    _resolve_join_inputs(draft, symbols_by_name, lets_by_scope)
    _resolve_expression_reads(draft, symbols_by_name, lets_by_scope)


def _resolve_join_inputs(
    draft: _RelationResolutionDraft,
    symbols_by_name: Mapping[str, ProjectResolvedModuleRelationSymbol],
    lets_by_scope: Mapping[tuple[int, str], ProjectResolvedModuleRelationSymbol],
) -> None:
    """Report a named JOIN input that names no relation as a single file
    does, PIE-S2301 at the JOIN, with the same scoped lookup a FROM name uses.
    An Unnest let's JOIN, a SEMI or ANTI JOIN that a lowered `any(...)`
    writes (its read reports its own name) and a name whose error is already
    reported are not."""

    # The JOINs of Unnest lets as written: name normalization has dropped the
    # lets from the bodies resolved here.
    parsed = draft.module.parsed_input
    authored = (
        None
        if parsed is None
        else parsed.script
        if parsed.authored_script is None
        else parsed.authored_script
    )
    # A body with relation lets or a table-function FROM is written as a
    # block, whose own body and relation-let bodies are each one body.
    bodies = [
        body
        for definition in (() if authored is None else authored.definitions)
        for body in (
            (definition.body, *(let.body for let in definition.let_relations))
            if type(definition) is BlockRelationDef
            else (definition,)
        )
        if type(body) in {TableDef, QueryDef, SelectBody}
    ]
    unnested = {
        (join.span.path, join.span.line, join.span.column)
        for body in bodies
        for _, joins in unnest_lets(cast(TableDef | QueryDef | SelectBody, body))
        for join in joins
    }
    for occurrence in draft.catalog.relation_owners:
        definition = occurrence.definition
        if type(definition) not in {TableDef, QueryDef}:
            continue
        body = cast(TableDef | QueryDef, definition)
        for join in body.join_clauses:
            name = join.target_relation_name
            if (
                not join.uses_named_input
                or (join.span.path, join.span.line, join.span.column) in unnested
                or join.kind in {AuthoredJoinKind.SEMI, AuthoredJoinKind.ANTI}
                or (occurrence.declaration_position, name) in draft.blocked_let_scopes
                or name in draft.blocked_names
                or name in draft.ambiguous_names
                or _resolve_scoped_name(
                    draft, occurrence, name, symbols_by_name, lets_by_scope
                )
                is not None
            ):
                continue
            location = _location(join.span, fallback_path=draft.module.path)
            draft.issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_JOIN_INPUT,
                    owning_module_path=draft.module.path,
                    local_name=name,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2301",
                        message=f"Unknown relation: {name}",
                        location=location,
                    ),
                    occurrences=(occurrence,),
                )
            )


def _resolve_expression_reads(
    draft: _RelationResolutionDraft,
    symbols_by_name: Mapping[str, ProjectResolvedModuleRelationSymbol],
    lets_by_scope: Mapping[tuple[int, str], ProjectResolvedModuleRelationSymbol],
) -> None:
    """Resolve every expression read; a read that closes a relation cycle is not.

    The module-local relation graph holds every FROM, JOIN and set input name
    and every read accepted before, in source order. A read whose target
    reaches its owner would make the owner read itself; it is reported once,
    at that read, and resolves to nothing.
    """

    from pietto.semantic.modern_inputs import _lexical_any_scopes

    def local(name: str, owner: ProjectDeclarationOccurrence):
        symbol = _resolve_scoped_name(
            draft, owner, name, symbols_by_name, lets_by_scope
        )
        if symbol is None or symbol.target_occurrence.identity.module_path != (
            draft.module.path
        ):
            return None
        return symbol.target_occurrence

    graph: dict[ProjectDeclarationOccurrence, list[ProjectDeclarationOccurrence]] = {}
    for resolution in draft.resolutions:
        target = resolution.target_symbol.target_occurrence
        if target.identity.module_path == draft.module.path:
            graph.setdefault(resolution.reference.owner, []).append(target)
    for owner in draft.catalog.relation_owners:
        definition = owner.definition
        if type(definition) is SetRelationDef:
            names = tuple(operand.relation_name for operand in definition.body.operands)
        elif type(definition) in {TableDef, QueryDef}:
            names = tuple(
                join.target_relation_name
                for join in cast(TableDef | QueryDef, definition).join_clauses
            )
        else:
            continue
        for name in names:
            target = local(name, owner)
            if target is not None:
                graph.setdefault(owner, []).append(target)
    parsed = draft.module.parsed_input
    # Each ANY's iterable name as written, before a let alias was replaced.
    authored = {
        id(value.expression): value.authored_expression.relation_name
        for value in (() if parsed is None else parsed.existence_values)
    }
    # A WHERE ANY lowered to a hidden SEMI/ANTI input still binds its row
    # name over that input's ON condition.
    lowered = {
        id(use.clause.on_clause): use.expression
        for use in (() if parsed is None else parsed.existence_generators)
    }
    for owner in draft.catalog.relation_owners:
        reads = expression_block_reads(owner)
        refused = _refused_read_positions(owner, reads)
        scopes = _lexical_any_scopes(owner.definition, lowered) if reads else {}
        for read in reads:
            where = refused.get(id(read.expression))
            if where is not None:
                _append_expression_position_issue(draft, read, where)
                draft.expression_reads.append(
                    ProjectResolvedExpressionBlockRead(read=read)
                )
                continue
            # An enclosing ANY binder of the name as written hides every
            # relation of that name from an ANY, as in a single file.
            shadowed = type(read.expression) is AnyExpr and any(
                scope.binding_name
                == authored.get(id(read.expression), read.relation_name)
                for scope in scopes.get(id(read.expression), ())
            )
            symbol = _resolve_expression_read(
                draft, read, symbols_by_name, lets_by_scope, shadowed=shadowed
            )
            target = None if symbol is None else symbol.target_occurrence
            if target is not None and target.identity.module_path == draft.module.path:
                path = _relation_path(graph, target, owner)
                if path is not None:
                    _append_expression_cycle_issue(draft, read, path)
                    symbol = None
                else:
                    graph.setdefault(owner, []).append(target)
            # A read that closes a cycle reports only the cycle (PIE-S2302).
            if (
                type(read.expression) is CollectRelationExpr
                and symbol is not None
                and not _is_relation_let_of(symbol.target_occurrence, owner)
            ):
                _append_collect_target_issue(draft, read)
            draft.expression_reads.append(
                ProjectResolvedExpressionBlockRead(read=read, target_symbol=symbol)
            )


# Each read family keeps its own code: a read is available only in WHERE and
# in the SELECT of an ungrouped query (D70.04); every other place is refused.
_READ_POSITION_DIAGNOSTICS: Mapping[type, tuple[str, str]] = {
    AnyExpr: ("PIE-S2334", "ANY relation reference"),
    RelationExistsExpr: ("PIE-S2349", "EXISTS relation reference"),
    RelationScalarExpr: ("PIE-S2348", "Scalar relation read"),
    RelationMembershipExpr: ("PIE-S2350", "IN relation reference"),
}
_REFUSED_POSITION_LABELS: Mapping[ProjectExpressionBlockPosition, str] = {
    ProjectExpressionBlockPosition.FROM: "FROM",
    ProjectExpressionBlockPosition.JOIN_ON: "JOIN ON",
    ProjectExpressionBlockPosition.LET: "a row let",
    ProjectExpressionBlockPosition.GROUP_BY: "GROUP BY",
    ProjectExpressionBlockPosition.SATISFYING: "SATISFYING",
    ProjectExpressionBlockPosition.WINDOW: "a window",
    ProjectExpressionBlockPosition.QUALIFY: "QUALIFY",
    ProjectExpressionBlockPosition.ORDER_BY: "ORDER BY",
    ProjectExpressionBlockPosition.LIMIT: "LIMIT",
}


def _refused_read_positions(
    owner: ProjectDeclarationOccurrence,
    reads: tuple[ProjectExpressionBlockRead, ...],
) -> dict[int, str]:
    """The place of every read outside WHERE and an ungrouped, unwindowed SELECT."""

    if not reads:
        return {}
    definition = cast(TableDef | QueryDef, owner.definition)
    grouped = definition.group_by_clause is not None or any(
        contains_semantic_aggregate(item.expression) for item in definition.select_items
    )
    windowed = _reads_under_windows(definition.select_items)
    refused: dict[int, str] = {}
    for read in reads:
        position = read.position
        if type(read.expression) is CollectRelationExpr:
            # The grammar writes Collect only as a whole SELECT item (D71.01),
            # available only in the SELECT of an ungrouped table or query.
            if position is not ProjectExpressionBlockPosition.SELECT:
                raise ValueError("A Collect relation read is a SELECT item.")
            if owner.let_position is not None:
                refused[id(read.expression)] = "a relation let"
            elif grouped:
                refused[id(read.expression)] = "the SELECT of a grouped query"
            continue
        if type(read.expression) is AnyExpr and position in {
            ProjectExpressionBlockPosition.JOIN_ON,
            ProjectExpressionBlockPosition.WHERE,
            ProjectExpressionBlockPosition.SELECT,
            ProjectExpressionBlockPosition.LET,
        }:
            continue
        if position is ProjectExpressionBlockPosition.WHERE:
            continue
        if position is ProjectExpressionBlockPosition.SELECT:
            if id(read.expression) in windowed:
                refused[id(read.expression)] = "a window"
            elif grouped:
                refused[id(read.expression)] = "the SELECT of a grouped query"
            continue
        refused[id(read.expression)] = _REFUSED_POSITION_LABELS[position]
    return refused


def _is_relation_let_of(
    target: ProjectDeclarationOccurrence, owner: ProjectDeclarationOccurrence
) -> bool:
    """Whether ``target`` is a relation let declared in ``owner``'s body."""

    return (
        target.let_position is not None
        and target.table_function is None
        and target.identity.module_path == owner.identity.module_path
        and target.module_position == owner.module_position
        and target.declaration_position == owner.declaration_position
    )


def _append_collect_target_issue(
    draft: _RelationResolutionDraft, read: ProjectExpressionBlockRead
) -> None:
    """PIE-S2803 for a Collect read whose target is no relation let of its
    owner's declaration; the read keeps its target."""

    name = read.relation_name
    owner = read.owner.identity.declared_name
    _append_collect_issue(
        draft,
        read,
        f"Collect relation read {name} is not a relation let of {owner}: "
        "collect reads a relation let declared in the same table or query.",
        f"Declare a relation let in {owner} that reads {name} with `from` and "
        "ends in `order by`, and collect that let.",
    )


def _append_collect_issue(
    draft: _RelationResolutionDraft,
    read: ProjectExpressionBlockRead,
    message: str,
    suggestion: str,
) -> None:
    # Where a Collect read stands and what it reads (PIE-S2803) share the
    # closed read-position status: the private vocabulary keeps its members,
    # and the diagnostic says which refusal it is.
    location = _location(read.expression.span, fallback_path=draft.module.path)
    draft.issues.append(
        ProjectModuleRelationResolutionIssue(
            status=ProjectModuleRelationResolutionIssueStatus.RELATION_EXPRESSION_READ_POSITION,
            owning_module_path=draft.module.path,
            local_name=read.relation_name,
            location=location,
            diagnostic=Diagnostic(
                code="PIE-S2803",
                severity=Severity.ERROR,
                message=message,
                location=location,
                suggestion=suggestion,
            ),
            occurrences=(read.owner,),
        )
    )


# Where a Collect read stands outside the SELECT of an ungrouped table or
# query, and how to write it there.
_COLLECT_POSITION_SUGGESTIONS: Mapping[str, str] = {
    "the SELECT of a grouped query": "Group the rows in another table or query, "
    "read it with `from` here, and collect a let that captures it.",
    "a relation let": "Collect in the SELECT of the table or query itself.",
}


def _reads_under_windows(items: tuple[SelectItem, ...]) -> frozenset[int]:
    """Identities of the reads written inside a window call or its window."""

    found: set[int] = set()
    pending: list[tuple[object, bool]] = [(item, False) for item in items]
    while pending:
        value, inside = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend((child, inside) for child in cast(tuple[object, ...], value))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        inside = inside or kind is WindowExpr
        if inside and kind in RELATION_READ_EXPRESSIONS:
            found.add(id(value))
        pending.extend(
            (getattr(value, item.name), inside) for item in _dataclass_fields(value)
        )
    return frozenset(found)


def _append_expression_position_issue(
    draft: _RelationResolutionDraft,
    read: ProjectExpressionBlockRead,
    where: str,
) -> None:
    if type(read.expression) is CollectRelationExpr:
        _append_collect_issue(
            draft,
            read,
            "Collect relation read is available only as a SELECT item of an "
            f"ungrouped table or query, not in {where}.",
            _COLLECT_POSITION_SUGGESTIONS[where],
        )
        return
    code, label = _READ_POSITION_DIAGNOSTICS[type(read.expression)]
    location = _location(read.expression.span, fallback_path=draft.module.path)
    message = (
        f"{label} is available only in JOIN ON, WHERE, SELECT and scalar LET, not in {where}."
        if type(read.expression) is AnyExpr
        else f"{label} is available only in WHERE and in the SELECT of "
        f"an ungrouped query, not in {where}."
    )
    draft.issues.append(
        ProjectModuleRelationResolutionIssue(
            status=ProjectModuleRelationResolutionIssueStatus.RELATION_EXPRESSION_READ_POSITION,
            owning_module_path=draft.module.path,
            local_name=read.relation_name,
            location=location,
            diagnostic=_diagnostic(
                code=code,
                message=message,
                location=location,
            ),
            occurrences=(read.owner,),
        )
    )


def _relation_path(
    graph: Mapping[ProjectDeclarationOccurrence, list[ProjectDeclarationOccurrence]],
    start: ProjectDeclarationOccurrence,
    goal: ProjectDeclarationOccurrence,
) -> tuple[ProjectDeclarationOccurrence, ...] | None:
    """The first breadth-first path from ``start`` to ``goal``, if any."""
    parents: dict[ProjectDeclarationOccurrence, ProjectDeclarationOccurrence | None] = {
        start: None
    }
    queue = [start]
    index = 0
    while index < len(queue):
        node = queue[index]
        index += 1
        if node is goal:
            path = [node]
            while parents[path[-1]] is not None:
                path.append(cast(ProjectDeclarationOccurrence, parents[path[-1]]))
            return tuple(reversed(path))
        for child in graph.get(node, ()):
            if child not in parents:
                parents[child] = node
                queue.append(child)
    return None


def _append_expression_cycle_issue(
    draft: _RelationResolutionDraft,
    read: ProjectExpressionBlockRead,
    path: tuple[ProjectDeclarationOccurrence, ...],
) -> None:
    owner = read.owner
    # The cycle runs owner -> target -> ... -> owner; the path ends at owner.
    members = (owner, *path[:-1]) if len(path) > 1 else (owner,)
    order = {item: i for i, item in enumerate(draft.catalog.relation_owners)}
    start = min(range(len(members)), key=lambda i: order.get(members[i], 0))
    occurrences = (*members[start:], *members[:start])
    location = _location(read.expression.span, fallback_path=draft.module.path)
    names = tuple(item.identity.declared_name for item in occurrences)
    draft.issues.append(
        ProjectModuleRelationResolutionIssue(
            status=ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE,
            owning_module_path=draft.module.path,
            local_name=names[0],
            location=location,
            related_locations=_ordered_related_locations(
                location,
                tuple(
                    _location(item.definition.span, fallback_path=draft.module.path)
                    for item in occurrences
                ),
            ),
            diagnostic=_diagnostic(
                code="PIE-S2302",
                message=f"Relation cycle detected: {' -> '.join((*names, names[0]))}",
                location=location,
            ),
            relation_cycle=occurrences,
        )
    )


def _resolve_scoped_name(
    draft: _RelationResolutionDraft,
    owner: ProjectDeclarationOccurrence,
    name: str,
    symbols_by_name: Mapping[str, ProjectResolvedModuleRelationSymbol],
    lets_by_scope: Mapping[tuple[int, str], ProjectResolvedModuleRelationSymbol],
) -> ProjectResolvedModuleRelationSymbol | None:
    """The FROM-name lookup of one owner's scope; no issue is produced here."""
    scope = (owner.declaration_position, name)
    if scope in draft.blocked_let_scopes:
        return None
    symbol = lets_by_scope.get(scope)
    if symbol is not None:
        return symbol
    if name in draft.blocked_names or name in draft.ambiguous_names:
        return None
    return symbols_by_name.get(name)


def _resolve_expression_read(
    draft: _RelationResolutionDraft,
    read: ProjectExpressionBlockRead,
    symbols_by_name: Mapping[str, ProjectResolvedModuleRelationSymbol],
    lets_by_scope: Mapping[tuple[int, str], ProjectResolvedModuleRelationSymbol],
    *,
    shadowed: bool,
) -> ProjectResolvedModuleRelationSymbol | None:
    """The same scoped lookup a FROM name uses; an unknown or shadowed name is
    an issue."""

    name = read.relation_name
    if not shadowed:
        symbol = _resolve_scoped_name(
            draft, read.owner, name, symbols_by_name, lets_by_scope
        )
        if (
            symbol is not None
            or (read.owner.declaration_position, name) in draft.blocked_let_scopes
            or name in draft.blocked_names
            or name in draft.ambiguous_names
        ):
            return symbol
    location = _location(read.expression.span, fallback_path=draft.module.path)
    draft.issues.append(
        ProjectModuleRelationResolutionIssue(
            status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_EXPRESSION_READ,
            owning_module_path=draft.module.path,
            local_name=name,
            location=location,
            diagnostic=_diagnostic(
                code="PIE-S2301",
                message=f"Unknown relation: {name}",
                location=location,
            ),
            occurrences=(read.owner,),
        )
    )
    return None


def _local_relation_cycles(
    draft: _RelationResolutionDraft,
) -> tuple[_LocalRelationCycle, ...]:
    local_symbols = tuple(
        symbol
        for symbol in (*draft.symbols, *draft.let_symbols)
        if symbol.local_occurrence is not None
        and symbol.declaration_kind
        in {ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY}
    )
    occurrence_order = {
        symbol.target_occurrence: symbol.target_occurrence.source_order
        for symbol in local_symbols
    }
    resolution_by_owner = {
        resolution.reference.owner: resolution for resolution in draft.resolutions
    }
    edge_by_origin: dict[
        ProjectDeclarationOccurrence,
        tuple[ProjectDeclarationOccurrence, ProjectModuleRelationReference],
    ] = {}
    for symbol in local_symbols:
        origin = symbol.target_occurrence
        resolution = resolution_by_owner.get(origin)
        if resolution is None:
            continue
        target = resolution.target_symbol.target_occurrence
        if (
            target in occurrence_order
            and target.identity.module_path == draft.module.path
        ):
            edge_by_origin[origin] = (target, resolution.reference)

    state: dict[ProjectDeclarationOccurrence, int] = {}
    stack: list[ProjectDeclarationOccurrence] = []
    stack_references: list[ProjectModuleRelationReference] = []
    stack_indexes: dict[ProjectDeclarationOccurrence, int] = {}
    cycles_by_members: dict[
        frozenset[ProjectDeclarationOccurrence], _LocalRelationCycle
    ] = {}

    def visit(occurrence: ProjectDeclarationOccurrence) -> None:
        state[occurrence] = 1
        stack_indexes[occurrence] = len(stack)
        stack.append(occurrence)
        edge = edge_by_origin.get(occurrence)
        if edge is not None:
            target, reference = edge
            target_state = state.get(target, 0)
            if target_state == 0:
                stack_references.append(reference)
                visit(target)
                stack_references.pop()
            elif target_state == 1:
                start = stack_indexes[target]
                cycle = _canonical_local_cycle(
                    tuple(stack[start:]),
                    tuple((*stack_references[start:], reference)),
                )
                cycles_by_members.setdefault(frozenset(cycle.occurrences), cycle)
        stack.pop()
        stack_indexes.pop(occurrence)
        state[occurrence] = 2

    for occurrence in sorted(occurrence_order, key=occurrence_order.__getitem__):
        if state.get(occurrence, 0) == 0:
            visit(occurrence)
    return tuple(
        sorted(
            cycles_by_members.values(),
            key=lambda cycle: tuple(
                occurrence_order[item] for item in cycle.occurrences
            ),
        )
    )


def _canonical_local_cycle(
    occurrences: tuple[ProjectDeclarationOccurrence, ...],
    references: tuple[ProjectModuleRelationReference, ...],
) -> _LocalRelationCycle:
    """Start the cycle at its member written first, lets before declarations."""

    if not occurrences or len(occurrences) != len(references):
        raise ValueError("Local relation cycle requires aligned nodes and edges.")
    start = min(
        range(len(occurrences)),
        key=lambda position: occurrences[position].source_order,
    )
    return _LocalRelationCycle(
        occurrences=(*occurrences[start:], *occurrences[:start]),
        references=(*references[start:], *references[:start]),
    )


def _append_local_cycle_issues(
    draft: _RelationResolutionDraft,
    cycles: tuple[_LocalRelationCycle, ...],
) -> None:
    for cycle in cycles:
        closing_reference = cycle.references[-1]
        location = _location(
            closing_reference.from_clause.span,
            fallback_path=draft.module.path,
        )
        names = tuple(item.identity.declared_name for item in cycle.occurrences)
        message = f"Relation cycle detected: {' -> '.join((*names, names[0]))}"
        draft.issues.append(
            ProjectModuleRelationResolutionIssue(
                status=ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE,
                owning_module_path=draft.module.path,
                local_name=names[0],
                location=location,
                related_locations=_ordered_related_locations(
                    location,
                    tuple(
                        _location(
                            occurrence.definition.span,
                            fallback_path=draft.module.path,
                        )
                        for occurrence in cycle.occurrences
                    ),
                ),
                diagnostic=_diagnostic(
                    code="PIE-S2302",
                    message=message,
                    location=location,
                ),
                relation_cycle=cycle.occurrences,
            )
        )


def _build_module_row_facts(
    draft: _RelationResolutionDraft,
    *,
    catalogs: ProjectModuleCatalogSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
    row_fact_by_identity: Mapping[
        ProjectNominalDeclarationIdentity, ProjectModuleRelationRowFact
    ],
    cycles: tuple[_LocalRelationCycle, ...],
) -> None:
    cycle_members = {occurrence for cycle in cycles for occurrence in cycle.occurrences}
    local_symbol_by_occurrence = {
        symbol.local_occurrence: symbol
        for symbol in (*draft.symbols, *draft.let_symbols)
        if symbol.local_occurrence is not None
    }
    resolution_by_owner = {
        resolution.reference.owner: resolution for resolution in draft.resolutions
    }

    for occurrence in draft.catalog.occurrences:
        if type(occurrence.definition) is not SourceDef:
            continue
        if occurrence not in local_symbol_by_occurrence:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        else:
            state = _source_row_state(
                draft,
                occurrence,
                catalogs=catalogs,
                bindings=bindings,
                type_source_resolutions=type_source_resolutions,
            )
        draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
            owner=occurrence,
            state=state,
        )

    for occurrence in draft.catalog.relation_owners:
        if type(occurrence.definition) in {
            SetRelationDef,
            ValuesRelationDef,
            TableFunctionRelationDef,
            UnnestRelationDef,
        }:
            draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
                owner=occurrence,
                state=_blocked_state(
                    ProjectRelationRowSchemaReason.RELATIONAL_SYNTAX_UNSUPPORTED
                ),
            )
    pending: list[ProjectDeclarationOccurrence] = []
    for occurrence in draft.catalog.relation_owners:
        if type(occurrence.definition) not in {TableDef, QueryDef}:
            continue
        if occurrence not in local_symbol_by_occurrence:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        elif occurrence in cycle_members:
            state = _blocked_state(ProjectRelationRowSchemaReason.CYCLE_BLOCKED)
        elif occurrence not in resolution_by_owner:
            state = _blocked_state(
                ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
            )
        else:
            pending.append(occurrence)
            continue
        draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
            owner=occurrence,
            state=state,
        )

    while pending:
        progressed = False
        next_pending: list[ProjectDeclarationOccurrence] = []
        for occurrence in pending:
            resolution = resolution_by_owner[occurrence]
            target_occurrence = resolution.target_symbol.target_occurrence
            target_fact = draft.row_facts.get(target_occurrence)
            if target_fact is None:
                target_fact = row_fact_by_identity.get(
                    resolution.target_symbol.target_identity
                )
            if target_fact is None:
                next_pending.append(occurrence)
                continue
            state = _relation_row_state(
                draft,
                occurrence,
                resolution,
                target_fact.state,
            )
            if (
                occurrence.let_position is not None
                and state.status is ProjectRelationRowSchemaStatus.CONCRETE
            ):
                # Minimal module row facts cover module declarations only; a
                # relation let's rows belong to the completed block semantics.
                state = ProjectRelationRowSchemaState(
                    status=ProjectRelationRowSchemaStatus.DEFERRED,
                    schema=None,
                    reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
                )
            draft.row_facts[occurrence] = ProjectModuleRelationRowFact(
                owner=occurrence,
                state=state,
            )
            progressed = True
        if not progressed:
            raise ValueError("Acyclic local relation graph must make finite progress.")
        pending = next_pending


def _source_row_state(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    *,
    catalogs: ProjectModuleCatalogSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> ProjectRelationRowSchemaState:
    source = occurrence.definition
    assert type(source) is SourceDef
    resolutions = draft.type_source_environment.find_source(source)
    if len(resolutions) != 1:
        _append_type_source_blocker(
            draft,
            occurrence,
            source,
            bindings=bindings,
        )
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    shape_occurrence = resolutions[0].target_symbol.target_occurrence
    shape = shape_occurrence.definition
    if type(shape) is not ShapeDef:
        raise ValueError("Resolved source shape target must be a ShapeDef.")
    type_environments = type_source_resolutions.find_module_path(
        shape_occurrence.identity.module_path
    )
    if len(type_environments) != 1:
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    type_environment = type_environments[0]
    fields: dict[str, ProjectRowField] = {}
    seen_field_names: set[str] = set()
    has_invalid_field = False
    for field_def in shape.fields:
        duplicate_name = field_def.name in seen_field_names
        seen_field_names.add(field_def.name)
        if duplicate_name:
            has_invalid_field = True
        type_facts = type_environment.find_type_expr(field_def.type_expr)
        if len(type_facts) != 1 or (
            type_facts[0].canonical_kind is ProjectResolvedTypeKind.UNKNOWN
        ):
            _append_type_source_blocker(
                draft,
                occurrence,
                source,
                field_def.type_expr,
                bindings=bindings,
                type_source_environment=type_environment,
                type_resolution=None if len(type_facts) != 1 else type_facts[0],
                type_source_resolutions=(
                    None if len(type_facts) != 1 else type_source_resolutions
                ),
            )
            has_invalid_field = True
            continue
        if duplicate_name:
            continue
        fields[field_def.name] = ProjectRowField(
            name=field_def.name,
            resolved_type=_resolved_row_type(type_facts[0], catalogs),
            nullability=_row_field_nullability(field_def.type_expr.nullability),
            field_def=field_def,
        )
    if has_invalid_field:
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=ProjectRowSchema(fields=fields),
        reason=ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE,
    )


def _append_type_source_blocker(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    source: SourceDef,
    type_expr: TypeExpr | None = None,
    *,
    bindings: ProjectModuleBindingEnvironmentSet,
    type_source_environment: ProjectModuleTypeSourceResolutionEnvironment | None = None,
    type_resolution: ProjectResolvedModuleTypeReference | None = None,
    type_source_resolutions: ProjectTypeSourceResolutionSet | None = None,
) -> None:
    if type_resolution is None:
        if type_source_resolutions is not None:
            raise ValueError("Type/source blocker resolution inputs must be paired.")
        issue_environment = (
            draft.type_source_environment
            if type_source_environment is None
            else type_source_environment
        )
        binding_name = source.shape_name if type_expr is None else type_expr.name
        module_binding_keys = (
            frozenset()
            if binding_name is None
            else frozenset({(issue_environment.module.path, binding_name)})
        )
        issues = tuple(
            issue
            for issue in issue_environment.issues
            if (
                issue.source_reference is not None
                and issue.source_reference.source is source
            )
            or (
                type_expr is not None
                and issue.type_reference is not None
                and issue.type_reference.type_expr is type_expr
            )
            or _matches_type_namespace_blocker(
                issue,
                module_binding_keys,
                bindings,
            )
        )
    else:
        if (
            type_source_resolutions is None
            or type_expr is not type_resolution.reference.type_expr
            or type_source_environment is None
            or type_resolution not in type_source_environment.type_resolutions
            or type_source_resolutions.find_module_path(
                type_resolution.reference.owner.identity.module_path
            )
            != (type_source_environment,)
        ):
            raise ValueError("Type/source blocker resolution inputs must be paired.")
        alias_identities = frozenset(type_resolution.alias_chain)
        module_binding_keys = _type_module_binding_keys(
            type_resolution,
            type_source_resolutions,
        )
        issues = tuple(
            issue
            for issue in type_source_resolutions.issues
            if (
                issue.type_reference is not None
                and (
                    issue.type_reference.type_expr
                    is type_resolution.reference.type_expr
                    or issue.type_reference.owner.identity in alias_identities
                )
            )
            or bool(alias_identities.intersection(issue.alias_cycle))
            or _matches_type_namespace_blocker(
                issue,
                module_binding_keys,
                bindings,
            )
        )
    root_items: list[Diagnostic] = []
    for issue in issues:
        issue_roots = (
            (issue.diagnostic,)
            if issue.diagnostic is not None
            else issue.suppressing_diagnostics
        )
        for diagnostic in issue_roots:
            _append_exact_unique(root_items, diagnostic)
    roots = tuple(root_items)
    if not roots:
        return
    location = _location(source.span, fallback_path=draft.module.path)
    candidate = ProjectModuleRelationResolutionIssue(
        status=ProjectModuleRelationResolutionIssueStatus.TYPE_SOURCE_DIAGNOSTIC_BLOCKED,
        owning_module_path=draft.module.path,
        local_name=source.name,
        location=location,
        related_locations=_ordered_related_locations(
            location,
            tuple(root.location for root in roots),
        ),
        occurrences=(occurrence,),
        type_source_issues=issues,
        suppressing_diagnostics=roots,
    )
    component_roots = list(candidate.suppressing_diagnostics)
    overlapping_positions: set[int] = set()
    while True:
        previous_count = len(overlapping_positions)
        for position, issue in enumerate(draft.issues):
            if position in overlapping_positions or (
                issue.status is not candidate.status
                or issue.owning_module_path != candidate.owning_module_path
                or issue.local_name != candidate.local_name
                or issue.location != candidate.location
                or issue.occurrences != candidate.occurrences
                or not any(
                    root is retained_root
                    for root in component_roots
                    for retained_root in issue.suppressing_diagnostics
                )
            ):
                continue
            overlapping_positions.add(position)
            for root in issue.suppressing_diagnostics:
                _append_exact_unique(component_roots, root)
        if len(overlapping_positions) == previous_count:
            break
    if not overlapping_positions:
        draft.issues.append(candidate)
        return

    overlapping = tuple(
        draft.issues[position] for position in sorted(overlapping_positions)
    )
    combined_type_source_issues: list[ProjectTypeSourceResolutionIssue] = []
    combined_roots: list[Diagnostic] = []
    for issue in (*overlapping, candidate):
        for type_source_issue in issue.type_source_issues:
            _append_exact_unique(combined_type_source_issues, type_source_issue)
        for root in issue.suppressing_diagnostics:
            _append_exact_unique(combined_roots, root)
    combined_root_tuple = tuple(combined_roots)
    merged = ProjectModuleRelationResolutionIssue(
        status=candidate.status,
        owning_module_path=candidate.owning_module_path,
        local_name=candidate.local_name,
        location=candidate.location,
        related_locations=_ordered_related_locations(
            candidate.location,
            tuple(root.location for root in combined_root_tuple),
        ),
        occurrences=candidate.occurrences,
        type_source_issues=tuple(combined_type_source_issues),
        suppressing_diagnostics=combined_root_tuple,
    )
    first_position = min(overlapping_positions)
    draft.issues[first_position] = merged
    for position in sorted(overlapping_positions - {first_position}, reverse=True):
        del draft.issues[position]


def _append_exact_unique(items: list[_ObjectT], item: _ObjectT) -> None:
    if not any(item is retained for retained in items):
        items.append(item)


def _matches_type_namespace_blocker(
    issue: ProjectTypeSourceResolutionIssue,
    binding_keys: frozenset[tuple[str, str]],
    bindings: ProjectModuleBindingEnvironmentSet,
) -> bool:
    local_name = issue.local_name
    if local_name is None or (issue.owning_module_path, local_name) not in binding_keys:
        return False
    if issue.status is ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_TYPE_NAME:
        return True
    if issue.status is ProjectTypeSourceResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED:
        namespaces = tuple(
            item.request.identity.namespace for item in issue.binding_issues
        ) + tuple(item.identity.namespace for item in issue.occurrences)
        return (
            bool(namespaces)
            and all(
                namespace is ProjectSymbolNamespace.TYPE for namespace in namespaces
            )
        ) or any(
            item.status in _COLLISION_ISSUE_STATUSES for item in issue.binding_issues
        )
    if (
        issue.status
        is not ProjectTypeSourceResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
    ):
        return False
    environments = bindings.find_module_path(issue.owning_module_path)
    if len(environments) != 1 or issue.cycle is None:
        raise ValueError("Cyclic type binding root requires exact retained inputs.")
    cycle_paths = {member.identity.path for member in issue.cycle.component.members}
    for binding in environments[0].bindings:
        identity = binding.identity
        if (
            identity.namespace is not ProjectSymbolNamespace.TYPE
            or identity.local_binding_name != local_name
            or (
                binding.target_module_path not in cycle_paths
                and binding.target_identity.module_path not in cycle_paths
            )
        ):
            continue
        span = (
            binding.request.source_item.local_name_span
            or binding.request.source_item.exported_name_span
        )
        if _location(span, fallback_path=issue.owning_module_path) == issue.location:
            return True
    return False


def _type_module_binding_keys(
    resolution: ProjectResolvedModuleTypeReference,
    resolutions: ProjectTypeSourceResolutionSet,
) -> frozenset[tuple[str, str]]:
    reference = resolution.reference
    keys = {
        (reference.owner.identity.module_path, reference.type_expr.name),
    }
    for alias_identity in resolution.alias_chain:
        matches = tuple(
            candidate
            for environment in resolutions.environments
            for candidate in environment.type_resolutions
            if candidate.reference.role
            is ProjectModuleTypeReferenceRole.TYPE_ALIAS_BASE
            and candidate.reference.owner.identity == alias_identity
        )
        if len(matches) != 1:
            raise ValueError("Resolved alias chain requires one exact base reference.")
        alias_reference = matches[0].reference
        keys.add(
            (alias_reference.owner.identity.module_path, alias_reference.type_expr.name)
        )
    return frozenset(keys)


def _resolved_row_type(
    resolution: object,
    catalogs: ProjectModuleCatalogSet,
) -> ProjectResolvedType:
    from pietto._project.module_resolution import ProjectResolvedModuleTypeReference

    if type(resolution) is not ProjectResolvedModuleTypeReference:
        raise TypeError("Row type requires a resolved module type reference.")
    if resolution.canonical_kind is ProjectResolvedTypeKind.BUILTIN:
        return ProjectResolvedType(
            name=resolution.canonical_name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        )
    identity = resolution.canonical_target_identity
    if identity is None:
        raise ValueError("Known nominal row type requires a target identity.")
    occurrences = catalogs.find_identity(identity)
    if len(occurrences) != 1:
        raise ValueError("Known nominal row type requires one target occurrence.")
    occurrence = occurrences[0]
    return ProjectResolvedType(
        name=resolution.canonical_name,
        kind=resolution.canonical_kind,
        symbol=ProjectSymbol(
            namespace=identity.namespace,
            kind=identity.declaration_kind,
            name=identity.declared_name,
            path=identity.module_path,
            location=_location(
                occurrence.definition.span,
                fallback_path=identity.module_path,
            ),
            definition=occurrence.definition,
        ),
    )


def _passes_unfit_field(
    definition: TableDef | QueryDef,
    source_schema: ProjectRowSchema,
) -> bool:
    """Whether a select item of ``definition`` passes its field to a ``def``
    it does not fit (`reports_unfit_def_argument`), which is then no direct
    field; the input row is converted once, and only for a relation that
    passes a select item to a def."""

    arguments = [
        item.expression
        for item in definition.select_items
        if inlined_arguments(item.expression)
    ]
    if not arguments:
        return False
    row_schema = project_row_schema_to_semantic_row_schema(source_schema)
    return any(
        reports_unfit_def_argument(
            argument,
            row_schema,
            relation_qualifier=definition.from_clause.binding_name
            or definition.from_clause.source_name,
        )
        for argument in arguments
    )


def _relation_row_state(
    draft: _RelationResolutionDraft,
    occurrence: ProjectDeclarationOccurrence,
    resolution: ProjectResolvedModuleRelationReference,
    upstream_state: ProjectRelationRowSchemaState,
) -> ProjectRelationRowSchemaState:
    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return _unknown_state(ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN)
    if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.BLOCKED:
        return _blocked_state(ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED)
    definition = occurrence.definition
    assert type(definition) in {TableDef, QueryDef}
    relation_definition = cast(TableDef | QueryDef, definition)
    if relation_definition.join_clauses:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED,
        )
    source_schema = upstream_state.schema
    if source_schema is None or source_schema.is_unknown:
        raise ValueError("Concrete upstream row state requires a concrete schema.")
    let_names = (
        frozenset()
        if relation_definition.let_clause is None
        else frozenset(
            binding.name for binding in relation_definition.let_clause.bindings
        )
    )
    has_deferred_behavior = (
        relation_definition.let_clause is not None
        or relation_definition.group_by_clause is not None
        or relation_definition.satisfying_clause is not None
        or any(
            type(item.expression) not in {NameExpr, DottedNameExpr}
            for item in relation_definition.select_items
        )
        or _passes_unfit_field(relation_definition, source_schema)
    )
    output_names: set[str] = set()
    duplicate = False
    for item in relation_definition.select_items:
        output_name = _projection_output_name(item)
        if output_name is None:
            continue
        if output_name in output_names:
            duplicate = True
            continue
        output_names.add(output_name)

    fields: dict[str, ProjectRowField] = {}
    diagnostics: list[ProjectModuleRelationResolutionIssue] = []
    for item in relation_definition.select_items:
        if type(item.expression) not in {NameExpr, DottedNameExpr}:
            continue
        if type(item.expression) is NameExpr and item.expression.name in let_names:
            continue
        decoded = _direct_field_names(
            item,
            source_name=relation_definition.from_clause.binding_name
            or relation_definition.from_clause.source_name,
        )
        if decoded is None:
            field_text = _field_text(item)
            location = _location(item.expression.span, fallback_path=draft.module.path)
            diagnostics.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD,
                    owning_module_path=draft.module.path,
                    local_name=field_text,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2102",
                        message=f"Unknown field: {field_text}",
                        location=location,
                    ),
                    reference=resolution.reference,
                    select_item=item,
                )
            )
            continue
        output_name, lookup_name = decoded
        source_field = source_schema.fields.get(lookup_name)
        if source_field is None:
            field_text = _field_text(item)
            location = _location(item.expression.span, fallback_path=draft.module.path)
            diagnostics.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD,
                    owning_module_path=draft.module.path,
                    local_name=field_text,
                    location=location,
                    diagnostic=_diagnostic(
                        code="PIE-S2102",
                        message=f"Unknown field: {field_text}",
                        location=location,
                    ),
                    reference=resolution.reference,
                    select_item=item,
                )
            )
            continue
        if output_name in fields:
            continue
        fields[output_name] = ProjectRowField(
            name=output_name,
            resolved_type=source_field.resolved_type,
            nullability=source_field.nullability,
            field_def=source_field.field_def,
        )
    draft.issues.extend(diagnostics)
    if diagnostics:
        return _unknown_state(ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA)
    if duplicate:
        return _unknown_state(ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME)
    if has_deferred_behavior:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
        )
    reason = (
        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
        if resolution.target_symbol.declaration_kind is ProjectSymbolKind.SOURCE
        else ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
    )
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=ProjectRowSchema(fields=fields),
        reason=reason,
    )


def _projection_output_name(item: SelectItem) -> str | None:
    if item.alias is not None:
        return item.alias
    expression = item.expression
    if type(expression) is NameExpr:
        return expression.name
    if type(expression) is DottedNameExpr:
        return expression.parts[-1]
    return None


def _direct_field_names(
    item: SelectItem,
    *,
    source_name: str,
) -> tuple[str, str] | None:
    expression = item.expression
    if type(expression) is NameExpr:
        return item.alias or expression.name, expression.name
    if type(expression) is DottedNameExpr and (
        len(expression.parts) == 2 and expression.parts[0] == source_name
    ):
        return item.alias or expression.parts[1], expression.parts[1]
    return None


def _field_text(item: SelectItem) -> str:
    expression = item.expression
    if type(expression) is NameExpr:
        return expression.name
    if type(expression) is DottedNameExpr:
        return ".".join(expression.parts)
    raise ValueError("Unknown direct field issue requires a name expression.")


def _source_duplicate_roots(
    environment: ProjectModuleTypeSourceResolutionEnvironment,
) -> dict[str, tuple[ProjectTypeSourceResolutionIssue, ...]]:
    result: dict[str, list[ProjectTypeSourceResolutionIssue]] = {}
    for issue in environment.issues:
        if (
            issue.status
            is ProjectTypeSourceResolutionIssueStatus.AMBIGUOUS_LOCAL_SOURCE_NAME
            and issue.local_name is not None
        ):
            result.setdefault(issue.local_name, []).append(issue)
    return {name: tuple(issues) for name, issues in result.items()}


def _duplicate_relation_issue(
    module_path: str,
    local_name: str,
    occurrences: tuple[ProjectDeclarationOccurrence, ...],
) -> ProjectModuleRelationResolutionIssue:
    primary = occurrences[1]
    location = _location(primary.definition.span, fallback_path=module_path)
    return ProjectModuleRelationResolutionIssue(
        status=ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME,
        owning_module_path=module_path,
        local_name=local_name,
        location=location,
        related_locations=_ordered_related_locations(
            location,
            tuple(
                _location(occurrence.definition.span, fallback_path=module_path)
                for occurrence in occurrences
            ),
        ),
        diagnostic=_diagnostic(
            code="PIE-S2001",
            message=f"Duplicate symbol name in relation namespace: {local_name}",
            location=location,
        ),
        occurrences=occurrences,
    )


def _local_relation_symbol(
    module_path: str,
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectResolvedModuleRelationSymbol:
    return ProjectResolvedModuleRelationSymbol(
        owning_module_path=module_path,
        local_name=occurrence.identity.declared_name,
        target_identity=occurrence.identity,
        target_occurrence=occurrence,
        local_occurrence=occurrence,
    )


def _module_cycle_issues(
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
) -> tuple[ProjectModuleRelationResolutionIssue, ...]:
    issues: list[ProjectModuleRelationResolutionIssue] = []
    for cycle in graph.cycles:
        roots = _suppressing_diagnostics_for_cycle(cycle, module_diagnostics)
        if not roots:
            raise ValueError("Cyclic module requires one PIE-S2703 root.")
        for member in cycle.component.members:
            location = roots[0].location
            issues.append(
                ProjectModuleRelationResolutionIssue(
                    status=ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED,
                    owning_module_path=member.identity.path,
                    local_name=None,
                    location=location,
                    related_locations=_ordered_related_locations(
                        location,
                        tuple(root.location for root in roots),
                    ),
                    module_cycle=cycle,
                    suppressing_diagnostics=roots,
                )
            )
    return tuple(
        sorted(
            issues,
            key=lambda issue: graph.find_path(issue.owning_module_path)[0].position,
        )
    )


def _unknown_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.UNKNOWN,
        schema=ProjectRowSchema(is_unknown=True),
        reason=reason,
    )


def _blocked_state(
    reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.BLOCKED,
        schema=None,
        reason=reason,
    )


def _row_field_nullability(nullability: Nullability) -> ProjectRowFieldNullability:
    if nullability is Nullability.NOT_NULL:
        return ProjectRowFieldNullability.NON_NULL
    if nullability is Nullability.NULLABLE:
        return ProjectRowFieldNullability.NULLABLE
    return ProjectRowFieldNullability.UNKNOWN


def _validate_builder_inputs(
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    exports: ProjectModuleExportSurfaceSet,
    bindings: ProjectModuleBindingEnvironmentSet,
    graph: ProjectModuleGraph,
    module_diagnostics: ProjectModuleDiagnosticSet,
    type_source_resolutions: ProjectTypeSourceResolutionSet,
) -> None:
    if type(modules) is not tuple or any(
        type(module) is not ProjectLogicalModule for module in modules
    ):
        raise TypeError("Relation resolver requires a logical-module tuple.")
    expected_types = (
        (catalogs, ProjectModuleCatalogSet),
        (exports, ProjectModuleExportSurfaceSet),
        (bindings, ProjectModuleBindingEnvironmentSet),
        (graph, ProjectModuleGraph),
        (module_diagnostics, ProjectModuleDiagnosticSet),
        (type_source_resolutions, ProjectTypeSourceResolutionSet),
    )
    for value, expected_type in expected_types:
        if type(value) is not expected_type:
            raise TypeError(f"Relation resolver requires {expected_type.__name__}.")
    lengths = {
        len(modules),
        len(catalogs.catalogs),
        len(exports.surfaces),
        len(bindings.environments),
        len(graph.vertices),
    }
    if len(lengths) != 1:
        raise ValueError("Relation resolver inputs must cover every module.")
    for position, (module, catalog, surface, environment, vertex) in enumerate(
        zip(
            modules,
            catalogs.catalogs,
            exports.surfaces,
            bindings.environments,
            graph.vertices,
            strict=True,
        )
    ):
        if (
            module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES
            or module.position != position
            or module.parsed_input is None
            or catalog.module is not module
            or surface.module is not module
            or environment.module is not module
            or vertex.module is not module
        ):
            raise ValueError("Relation resolver inputs must retain module order.")


def _validate_relation_identity(
    identity: ProjectNominalDeclarationIdentity,
) -> None:
    if (
        identity.namespace is not ProjectSymbolNamespace.RELATION
        or identity.declaration_kind not in _RELATION_KINDS
    ):
        raise ValueError("Resolved identity is not relation-producing.")


def _validate_issue_evidence(issue: ProjectModuleRelationResolutionIssue) -> None:
    status = issue.status
    code = None if issue.diagnostic is None else issue.diagnostic.code
    if (
        status
        is ProjectModuleRelationResolutionIssueStatus.AMBIGUOUS_LOCAL_RELATION_NAME
    ):
        valid = (
            len(issue.occurrences) > 1
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2001"
        )
    elif (
        status is ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_REFERENCE
    ):
        valid = (
            issue.reference is not None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2301"
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.UNKNOWN_DIRECT_FIELD:
        valid = (
            issue.reference is not None
            and issue.select_item is not None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2102"
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.LOCAL_RELATION_CYCLE:
        valid = (
            len(issue.relation_cycle) > 0
            and issue.reference is None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.type_source_issues
            and code == "PIE-S2302"
        )
    elif (
        status is ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
    ):
        valid = (
            issue.module_cycle is not None
            and issue.reference is None
            and issue.select_item is None
            and not issue.occurrences
            and not issue.binding_issues
            and not issue.relation_cycle
            and not issue.type_source_issues
            and issue.diagnostic is None
            and tuple(root.code for root in issue.suppressing_diagnostics)
            == ("PIE-S2703",)
        )
    elif status in _LET_ISSUE_CODES:
        valid = (
            bool(issue.occurrences)
            and all(
                item.let_position is not None
                and item.declaration_position
                == issue.occurrences[0].declaration_position
                for item in issue.occurrences
            )
            and (
                len(issue.occurrences) == 1
                or status
                is ProjectModuleRelationResolutionIssueStatus.LET_RELATION_NAME_COLLISION
            )
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == _LET_ISSUE_CODES[status]
        )
    elif status in {
        ProjectModuleRelationResolutionIssueStatus.UNKNOWN_RELATION_EXPRESSION_READ,
        ProjectModuleRelationResolutionIssueStatus.UNKNOWN_JOIN_INPUT,
    }:
        valid = (
            issue.local_name is not None
            and len(issue.occurrences) == 1
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code == "PIE-S2301"
        )
    elif (
        status
        is ProjectModuleRelationResolutionIssueStatus.RELATION_EXPRESSION_READ_POSITION
    ):
        valid = (
            issue.local_name is not None
            and len(issue.occurrences) == 1
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and code in {"PIE-S2348", "PIE-S2349", "PIE-S2350", "PIE-S2803"}
        )
    elif status is ProjectModuleRelationResolutionIssueStatus.MODULE_DIAGNOSTIC_BLOCKED:
        valid = (
            issue.local_name is not None
            and (bool(issue.binding_issues) != bool(issue.occurrences))
            and issue.reference is None
            and issue.select_item is None
            and issue.module_cycle is None
            and not issue.relation_cycle
            and not issue.type_source_issues
            and issue.diagnostic is None
            and bool(issue.suppressing_diagnostics)
        )
    else:
        valid = (
            issue.local_name is not None
            and bool(issue.occurrences)
            and bool(issue.type_source_issues)
            and issue.reference is None
            and issue.select_item is None
            and not issue.binding_issues
            and issue.module_cycle is None
            and not issue.relation_cycle
            and issue.diagnostic is None
            and bool(issue.suppressing_diagnostics)
        )
    if not valid:
        raise ValueError("Relation issue evidence must prove its exact status.")


def _diagnostic(*, code: str, message: str, location: SourceLocation) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=Severity.ERROR,
        message=message,
        location=location,
    )


def _location(span: Span, *, fallback_path: str) -> SourceLocation:
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _ordered_related_locations(
    primary: SourceLocation,
    locations: tuple[SourceLocation, ...],
) -> tuple[SourceLocation, ...]:
    unique = {
        (
            location.path or "",
            location.line,
            location.column,
            location.end_line if location.end_line is not None else -1,
            location.end_column if location.end_column is not None else -1,
        ): location
        for location in locations
        if location != primary
    }
    return tuple(unique[key] for key in sorted(unique))


def _issue_source_key(
    issue: ProjectModuleRelationResolutionIssue,
) -> tuple[object, ...]:
    rank = {
        status: position
        for position, status in enumerate(ProjectModuleRelationResolutionIssueStatus)
    }
    location = issue.location
    return (
        location.line,
        location.column,
        location.end_line if location.end_line is not None else -1,
        location.end_column if location.end_column is not None else -1,
        rank[issue.status],
        issue.local_name or "",
    )


def _tuple_mapping(
    values: Mapping[_KeyT, list[_ValueT]],
) -> Mapping[_KeyT, tuple[_ValueT, ...]]:
    return MappingProxyType({key: tuple(items) for key, items in values.items()})


def _require_tuple_items(
    values: tuple[object, ...], item_type: type, label: str
) -> None:
    if type(values) is not tuple or any(type(item) is not item_type for item in values):
        raise TypeError(f"{label} must be a tuple of {item_type.__name__} values.")
