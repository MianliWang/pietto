"""Private module-qualified declaration identities and per-module catalogs."""

from __future__ import annotations

from pietto.ast_nodes import (
    SetRelationDef,
    TableFunctionFromClause,
    TableFunctionRelationDef,
    ValuesBody,
    ValuesRelationDef,
)

from dataclasses import dataclass, field, fields, is_dataclass
import heapq
from typing import cast

from pietto._project.model import (
    ProjectSymbolKind,
    ProjectSymbolNamespace,
    _classify_project_definition,
)
from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto.ast_nodes import (
    BlockRelationDef,
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    FromClause,
    LetRelationDef,
    ModuleDeclarationKind,
    QueryDef,
    QueryParameter,
    RelationBody,
    RelationExistsExpr,
    RelationMembershipExpr,
    RelationScalarExpr,
    SelectBody,
    SetOperationBody,
    ShapeDef,
    SourceDef,
    Span,
    TableDef,
    TypeDef,
)

__all__: tuple[str, ...] = ()

_DEFINITION_TYPES = (
    SetRelationDef,
    ValuesRelationDef,
    TableFunctionRelationDef,
    TypeDef,
    EnumDef,
    ShapeDef,
    SourceDef,
    TableDef,
    QueryDef,
    ConstraintDef,
    DeriveDef,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNominalDeclarationIdentity:
    """The exact private four-component identity of one local declaration."""

    module_path: str
    namespace: ProjectSymbolNamespace
    declaration_kind: ProjectSymbolKind
    declared_name: str

    def __post_init__(self) -> None:
        """Reject values outside the exact nominal identity domains."""

        ProjectModuleIdentity(path=self.module_path)
        if type(self.namespace) is not ProjectSymbolNamespace:
            raise TypeError("Nominal declaration identity requires a namespace.")
        if type(self.declaration_kind) is not ProjectSymbolKind:
            raise TypeError("Nominal declaration identity requires a declaration kind.")
        if type(self.declared_name) is not str or not self.declared_name:
            raise ValueError(
                "Nominal declaration identity requires a non-empty declared name."
            )


_SELECT_FIELDS = (
    "from_clause",
    "where_clause",
    "group_by_clause",
    "select_items",
    "order_by_clause",
    "limit_clause",
    "satisfying_clause",
    "qualify_clause",
    "let_clause",
    "named_windows",
    "join_clauses",
    "distinct_clause",
)


def _relation_block_view(
    *,
    span: Span,
    name: str,
    kind: ModuleDeclarationKind,
    body: RelationBody,
    parameters: tuple[QueryParameter, ...] = (),
) -> TableDef | QueryDef | SetRelationDef | ValuesRelationDef:
    """Present one authored block body in the existing relation-definition shape.

    The view owns no clause of its own: every clause is the authored node, so
    spans and AST identities are those of the source. An entry query keeps its
    authored header, which only a FROM-based query body carries.
    """

    if type(body) is SetOperationBody and not parameters:
        return SetRelationDef(span=span, name=name, kind=kind, body=body)
    if type(body) is ValuesBody and not parameters:
        return ValuesRelationDef(span=span, name=name, kind=kind, body=body)
    if type(body) is SelectBody and type(body.from_clause) in {
        FromClause,
        TableFunctionFromClause,
    }:
        clauses = {item: getattr(body, item) for item in _SELECT_FIELDS}
        clauses["from_clause"] = _from_view(body.from_clause)
        if kind is ModuleDeclarationKind.TABLE:
            if parameters:
                raise ValueError("Only an entry query declares parameters.")
            return TableDef(span=span, name=name, **clauses)
        return QueryDef(span=span, name=name, parameters=parameters, **clauses)
    raise ValueError(f"Unadmitted relation block body: {type(body).__name__}")


def _from_view(clause: FromClause | TableFunctionFromClause) -> FromClause:
    """A table-function input is read through its binding at its own span.

    The binding is never looked up by name: the reader is bound to the
    function occurrence of this exact clause (see ``table_function_input``).
    """

    if isinstance(clause, TableFunctionFromClause):
        return FromClause(span=clause.span, source_name=clause.binding_name)
    return clause


def table_function_input(
    authored: object,
) -> TableFunctionFromClause | None:
    """Return the table-function FROM input written by one authored body owner."""

    body = getattr(authored, "body", None)
    if (
        type(authored) in {BlockRelationDef, LetRelationDef}
        and type(body) is SelectBody
    ):
        clause = body.from_clause
        if type(clause) is TableFunctionFromClause:
            return clause
    return None


def _is_relation_block_view(
    view: Definition | ValuesRelationDef | TableFunctionRelationDef,
    *,
    span: Span,
    name: str,
    kind: ModuleDeclarationKind,
    body: RelationBody,
    parameters: tuple[QueryParameter, ...] = (),
) -> bool:
    if view.span != span or view.name != name:
        return False
    if type(body) is SetOperationBody:
        return (
            not parameters
            and type(view) is SetRelationDef
            and view.kind is kind
            and view.body is body
        )
    if type(body) is ValuesBody:
        return (
            not parameters
            and type(view) is ValuesRelationDef
            and view.kind is kind
            and view.body is body
        )
    expected = TableDef if kind is ModuleDeclarationKind.TABLE else QueryDef
    return (
        type(body) is SelectBody
        and type(view) is expected
        and all(
            getattr(view, item) is getattr(body, item)
            for item in _SELECT_FIELDS
            if item != "from_clause"
        )
        and (
            view.from_clause is body.from_clause
            if type(body.from_clause) is FromClause
            else view.from_clause == _from_view(body.from_clause)
        )
        and getattr(view, "parameters", ()) is parameters
    )


def _block_kind(authored: BlockRelationDef | LetRelationDef) -> ModuleDeclarationKind:
    """A declaration keeps its own kind; a relation let is always a query."""

    if type(authored) is BlockRelationDef:
        return authored.kind
    return ModuleDeclarationKind.QUERY


def _block_view_of(
    authored: BlockRelationDef | LetRelationDef,
) -> TableDef | QueryDef | SetRelationDef | ValuesRelationDef:
    return _relation_block_view(
        span=authored.span,
        name=authored.name,
        kind=_block_kind(authored),
        body=authored.body,
        parameters=_block_parameters(authored),
    )


type RelationReadExpression = (
    RelationExistsExpr | RelationMembershipExpr | RelationScalarExpr
)
RELATION_READ_EXPRESSIONS = frozenset(
    {RelationExistsExpr, RelationMembershipExpr, RelationScalarExpr}
)


def relation_read_expressions(node: object) -> tuple[RelationReadExpression, ...]:
    """Every `exists`, `scalar` and `in` relation read under one AST value.

    Reads come in source order, a read before the reads nested in it.
    """

    found: list[RelationReadExpression] = []
    pending: list[object] = [node]
    while pending:
        value = pending.pop()
        kind = type(value)
        if kind is tuple:
            pending.extend(reversed(cast(tuple[object, ...], value)))
            continue
        if (
            kind is Span
            or kind.__module__ != "pietto.ast_nodes"
            or not is_dataclass(value)
        ):
            continue
        if kind in RELATION_READ_EXPRESSIONS:
            found.append(cast(RelationReadExpression, value))
        pending.extend(
            reversed(tuple(getattr(value, item.name) for item in fields(value)))
        )
    # Preorder, then stable source order.
    found.sort(key=lambda item: (item.span.line, item.span.column))
    return tuple(found)


def relation_reads(owner: ProjectDeclarationOccurrence) -> tuple[str, ...]:
    """Every relation name one relation body reads.

    These are its FROM and JOIN targets, set operands and the relations of its
    `exists`, `scalar` and `in` reads. A typed VALUES body or a table function
    is a zero-input relation and reads none; a table-function FROM input is
    bound by identity, never read by name.
    """

    definition = owner.definition
    if type(definition) in {ValuesRelationDef, TableFunctionRelationDef}:
        return ()
    if type(definition) is SetRelationDef:
        return tuple(operand.relation_name for operand in definition.body.operands)
    if type(definition) is TableDef or type(definition) is QueryDef:
        return (
            *(
                ()
                if table_function_input(owner.authored) is not None
                else (definition.from_clause.source_name,)
            ),
            *(join.target_relation_name for join in definition.join_clauses),
            *(read.relation_name for read in relation_read_expressions(definition)),
        )
    raise ValueError("Relation reads require a relation body.")


def _read_ordered(
    lets: list[ProjectDeclarationOccurrence],
) -> tuple[ProjectDeclarationOccurrence, ...]:
    """Order one declaration's lets so each follows every sibling it reads.

    Ties keep source order; lets that no order can place (cycle members and
    their readers) follow in source order. Duplicate names read nothing.
    """

    names = [let.identity.declared_name for let in lets]
    unique = {name: i for i, name in enumerate(names) if names.count(name) == 1}
    readers: list[list[int]] = [[] for _ in lets]
    pending = [0] * len(lets)
    for i, let in enumerate(lets):
        for j in {unique[n] for n in relation_reads(let) if n in unique}:
            if j != i:
                readers[j].append(i)
                pending[i] += 1
    ready = [i for i, count in enumerate(pending) if count == 0]
    ordered: list[int] = []
    while ready:
        i = heapq.heappop(ready)
        ordered.append(i)
        for reader in readers[i]:
            pending[reader] -= 1
            if pending[reader] == 0:
                heapq.heappush(ready, reader)
    placed = set(ordered)
    ordered.extend(i for i in range(len(lets)) if i not in placed)
    return tuple(lets[i] for i in ordered)


def _block_parameters(
    authored: BlockRelationDef | LetRelationDef,
) -> tuple[QueryParameter, ...]:
    """The authored header of an entry query; a relation let has none."""

    return authored.parameters if type(authored) is BlockRelationDef else ()


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDeclarationOccurrence:
    """One source-ordered AST occurrence of a nominal declaration identity.

    A declaration written with relation lets is retained as ``authored_block``
    and presented through ``definition`` as the existing relation shape of its
    body. Each ``let NAME:`` of it is its own occurrence: it shares the parent's
    module and declaration positions, is told apart by ``let_position``, and
    never enters a module namespace, so its nominal identity is display only.
    """

    identity: ProjectNominalDeclarationIdentity
    module_position: int
    declaration_position: int
    definition: Definition | ValuesRelationDef | TableFunctionRelationDef
    let_position: int | None = None
    authored_block: BlockRelationDef | LetRelationDef | None = field(
        default=None, compare=False, hash=False, repr=False
    )
    # A table-function occurrence: the zero-input relation of one FROM input,
    # in the body of the declaration at ``declaration_position`` or of its let
    # at ``let_position``. Its nominal identity is display only.
    table_function: TableFunctionFromClause | None = None

    @property
    def block_local(self) -> bool:
        """A relation let or table-function occurrence, never a declaration."""

        return self.let_position is not None or self.table_function is not None

    @property
    def authored(
        self,
    ) -> (
        Definition
        | ValuesRelationDef
        | TableFunctionRelationDef
        | LetRelationDef
        | TableFunctionFromClause
    ):
        """Return the exact source node this occurrence was built from."""

        if self.table_function is not None:
            return self.table_function
        return self.definition if self.authored_block is None else self.authored_block

    @property
    def source_order(self) -> tuple[int, int, bool, int]:
        """Return the written order, each declaration's lets before it."""

        return (
            self.module_position,
            self.declaration_position,
            self.let_position is None,
            self.let_position or 0,
        )

    def __post_init__(self) -> None:
        """Reject occurrence facts inconsistent with the retained definition."""

        if type(self.identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Declaration occurrence requires a nominal identity.")
        if type(self.module_position) is not int or self.module_position < 0:
            raise ValueError(
                "Declaration occurrence module position must be non-negative."
            )
        if type(self.declaration_position) is not int or self.declaration_position < 0:
            raise ValueError("Declaration occurrence position must be non-negative.")
        if type(self.definition) not in _DEFINITION_TYPES:
            raise TypeError("Declaration occurrence requires a top-level definition.")
        namespace, declaration_kind = _classify_project_definition(self.definition)
        if (
            namespace is not self.identity.namespace
            or declaration_kind is not self.identity.declaration_kind
            or self.definition.name != self.identity.declared_name
        ):
            raise ValueError("Declaration occurrence must match its nominal identity.")
        block = self.authored_block
        if self.table_function is not None or (
            type(self.definition) is TableFunctionRelationDef
        ):
            if (
                type(self.definition) is not TableFunctionRelationDef
                or self.definition.source is not self.table_function
                or block is not None
                or (
                    self.let_position is not None
                    and (type(self.let_position) is not int or self.let_position < 0)
                )
            ):
                raise ValueError(
                    "Table-function occurrence requires its exact FROM input."
                )
            return
        if self.let_position is not None and (
            type(self.let_position) is not int
            or self.let_position < 0
            or type(block) is not LetRelationDef
            or declaration_kind is not ProjectSymbolKind.QUERY
        ):
            raise ValueError("Let occurrence requires its exact let declaration.")
        if block is not None and (
            type(block)
            is not (BlockRelationDef if self.let_position is None else LetRelationDef)
            or not _is_relation_block_view(
                self.definition,
                span=block.span,
                name=block.name,
                kind=_block_kind(block),
                body=block.body,
                parameters=_block_parameters(block),
            )
        ):
            raise ValueError("Block occurrence must present its authored body.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCatalog:
    """All local declaration occurrences owned by one parsed logical module."""

    module: ProjectLogicalModule
    occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()
    lets: tuple[ProjectDeclarationOccurrence, ...] = ()
    table_functions: tuple[ProjectDeclarationOccurrence, ...] = ()

    def __post_init__(self) -> None:
        """Reject incomplete, reordered, or mismatched module catalogs."""

        if type(self.module) is not ProjectLogicalModule:
            raise TypeError("Module catalog requires a logical module.")
        if self.module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError("Module catalog requires explicit-module mode.")
        if self.module.parsed_input is None:
            raise ValueError("Module catalog requires a parsed logical module.")
        if type(self.occurrences) is not tuple:
            raise TypeError("Module catalog occurrences must be a tuple.")

        definitions = self.module.parsed_input.script.definitions
        if len(self.occurrences) != len(definitions):
            raise ValueError("Module catalog must retain every local definition.")
        for position, (occurrence, definition) in enumerate(
            zip(self.occurrences, definitions, strict=True)
        ):
            if type(occurrence) is not ProjectDeclarationOccurrence:
                raise TypeError("Module catalog requires declaration occurrences.")
            if (
                occurrence.identity.module_path != self.module.path
                or occurrence.module_position != self.module.position
                or occurrence.declaration_position != position
                or occurrence.let_position is not None
                or occurrence.authored is not definition
            ):
                raise ValueError(
                    "Module catalog occurrences must match source-ordered definitions."
                )
        expected_lets = tuple(
            (position, let_position, let)
            for position, definition in enumerate(definitions)
            if type(definition) is BlockRelationDef
            for let_position, let in enumerate(definition.let_relations)
        )
        if type(self.lets) is not tuple or len(self.lets) != len(expected_lets):
            raise ValueError("Module catalog must retain every relation let.")
        for occurrence, (position, let_position, let) in zip(
            self.lets, expected_lets, strict=True
        ):
            if (
                type(occurrence) is not ProjectDeclarationOccurrence
                or occurrence.identity.module_path != self.module.path
                or occurrence.module_position != self.module.position
                or occurrence.declaration_position != position
                or occurrence.let_position != let_position
                or occurrence.authored is not let
            ):
                raise ValueError("Module catalog lets must match source-ordered lets.")
        expected_functions = tuple(
            (position, let_position, clause)
            for position, definition in enumerate(definitions)
            for let_position, authored in (
                *enumerate(
                    definition.let_relations
                    if type(definition) is BlockRelationDef
                    else ()
                ),
                (None, definition),
            )
            if (clause := table_function_input(authored)) is not None
        )
        if type(self.table_functions) is not tuple or len(self.table_functions) != len(
            expected_functions
        ):
            raise ValueError("Module catalog must retain every table-function input.")
        for occurrence, (position, let_position, clause) in zip(
            self.table_functions, expected_functions, strict=True
        ):
            if (
                type(occurrence) is not ProjectDeclarationOccurrence
                or occurrence.identity.module_path != self.module.path
                or occurrence.module_position != self.module.position
                or occurrence.declaration_position != position
                or occurrence.let_position != let_position
                or occurrence.table_function is not clause
            ):
                raise ValueError(
                    "Module catalog table functions must match their FROM inputs."
                )

    @property
    def relation_owners(self) -> tuple[ProjectDeclarationOccurrence, ...]:
        """Return every relation-body owner: each declaration after its lets.

        A declaration's lets come in read order: each after every other let
        of the declaration it reads, otherwise (and inside a cycle) in source
        order. A table-function occurrence comes right before the body that
        reads it. Module-level readers (namespaces, exports, packages) keep
        reading ``occurrences``; relation-body readers read this sequence.
        """

        if not self.lets and not self.table_functions:
            return self.occurrences
        lets_by_position: dict[int, list[ProjectDeclarationOccurrence]] = {}
        for let in self.lets:
            lets_by_position.setdefault(let.declaration_position, []).append(let)
        functions = {
            (item.declaration_position, item.let_position): item
            for item in self.table_functions
        }

        def with_function(
            reader: ProjectDeclarationOccurrence, let_position: int | None
        ) -> tuple[ProjectDeclarationOccurrence, ...]:
            function = functions.get((reader.declaration_position, let_position))
            return (reader,) if function is None else (function, reader)

        return tuple(
            owner
            for occurrence in self.occurrences
            for owner in (
                *(
                    item
                    for let in _read_ordered(
                        lets_by_position.get(occurrence.declaration_position, [])
                    )
                    for item in with_function(let, let.let_position)
                ),
                *with_function(occurrence, None),
            )
        )

    def find_table_function(
        self, reader: ProjectDeclarationOccurrence
    ) -> ProjectDeclarationOccurrence | None:
        """Return the table-function occurrence one body reads, if it reads one."""

        clause = table_function_input(reader.authored)
        if clause is None:
            return None
        matches = tuple(
            item for item in self.table_functions if item.table_function is clause
        )
        if len(matches) != 1:
            raise ValueError("Table-function input requires one exact occurrence.")
        return matches[0]

    def find_lets(
        self, declaration_position: int
    ) -> tuple[ProjectDeclarationOccurrence, ...]:
        """Return the source-ordered let occurrences of one declaration."""

        return tuple(
            let for let in self.lets if let.declaration_position == declaration_position
        )

    @property
    def module_path(self) -> str:
        """Return the exact logical path of the owning module."""

        return self.module.path

    def find_namespace_name(
        self,
        namespace: ProjectSymbolNamespace,
        declared_name: str,
    ) -> tuple[ProjectDeclarationOccurrence, ...]:
        """Return every occurrence in one exact namespace/name bucket."""

        if type(namespace) is not ProjectSymbolNamespace:
            raise TypeError("Module catalog lookup requires a namespace.")
        if type(declared_name) is not str:
            raise TypeError("Module catalog lookup requires a declared name.")
        return tuple(
            occurrence
            for occurrence in self.occurrences
            if occurrence.identity.namespace is namespace
            and occurrence.identity.declared_name == declared_name
        )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCatalogSet:
    """An immutable selected-input-ordered set of per-module catalogs."""

    catalogs: tuple[ProjectModuleCatalog, ...] = ()

    def __post_init__(self) -> None:
        """Reject reordered, duplicate, or malformed project catalog sets."""

        if type(self.catalogs) is not tuple:
            raise TypeError("Project module catalogs must be a tuple.")
        module_paths: set[str] = set()
        for position, catalog in enumerate(self.catalogs):
            if type(catalog) is not ProjectModuleCatalog:
                raise TypeError("Project catalog set requires module catalogs.")
            if catalog.module.position != position:
                raise ValueError(
                    "Project module catalogs must retain selected-input order."
                )
            if catalog.module_path in module_paths:
                raise ValueError("Project module catalog paths must be unique.")
            module_paths.add(catalog.module_path)

    def find_identity(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectDeclarationOccurrence, ...]:
        """Return every source-ordered occurrence of an exact nominal identity."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Project catalog lookup requires a nominal identity.")
        return tuple(
            occurrence
            for catalog in self.catalogs
            for occurrence in catalog.occurrences
            if occurrence.identity == identity
        )

    def find_module_path(self, module_path: str) -> tuple[ProjectModuleCatalog, ...]:
        """Return the exact catalog for a valid logical path, or an empty tuple."""

        try:
            ProjectModuleIdentity(path=module_path)
        except (TypeError, ValueError):
            return ()
        return tuple(
            catalog for catalog in self.catalogs if catalog.module_path == module_path
        )


def _build_project_module_catalog_set(
    modules: tuple[ProjectLogicalModule, ...],
) -> ProjectModuleCatalogSet:
    """Build complete local declaration catalogs without resolving module syntax."""

    if type(modules) is not tuple:
        raise TypeError("Project module catalog builder requires a module tuple.")

    catalogs: list[ProjectModuleCatalog] = []
    module_paths: set[str] = set()
    for module_position, module in enumerate(modules):
        if type(module) is not ProjectLogicalModule:
            raise TypeError("Project module catalog builder requires logical modules.")
        if module.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError("Project module catalog builder rejects legacy modules.")
        if module.position != module_position:
            raise ValueError(
                "Project module catalog builder requires contiguous module positions."
            )
        if module.path in module_paths:
            raise ValueError("Project module catalog builder rejects duplicate paths.")
        if module.parsed_input is None:
            raise ValueError(
                "Project module catalog builder requires every module to be parsed."
            )
        module_paths.add(module.path)

        occurrences: list[ProjectDeclarationOccurrence] = []
        lets: list[ProjectDeclarationOccurrence] = []
        functions: list[ProjectDeclarationOccurrence] = []
        for declaration_position, definition in enumerate(
            module.parsed_input.script.definitions
        ):
            block = definition if type(definition) is BlockRelationDef else None
            view = definition if block is None else _block_view_of(block)
            namespace, declaration_kind = _classify_project_definition(view)
            occurrences.append(
                ProjectDeclarationOccurrence(
                    identity=ProjectNominalDeclarationIdentity(
                        module_path=module.path,
                        namespace=namespace,
                        declaration_kind=declaration_kind,
                        declared_name=view.name,
                    ),
                    module_position=module.position,
                    declaration_position=declaration_position,
                    definition=view,
                    authored_block=block,
                )
            )
            for let_position, authored in (
                *enumerate(() if block is None else block.let_relations),
                (None, block),
            ):
                clause = table_function_input(authored)
                if clause is not None:
                    functions.append(
                        ProjectDeclarationOccurrence(
                            identity=ProjectNominalDeclarationIdentity(
                                module_path=module.path,
                                namespace=ProjectSymbolNamespace.RELATION,
                                declaration_kind=ProjectSymbolKind.QUERY,
                                declared_name=clause.binding_name,
                            ),
                            module_position=module.position,
                            declaration_position=declaration_position,
                            definition=TableFunctionRelationDef(
                                span=clause.span,
                                name=clause.binding_name,
                                kind=ModuleDeclarationKind.QUERY,
                                source=clause,
                            ),
                            let_position=let_position,
                            table_function=clause,
                        )
                    )
            for let_position, let in enumerate(
                () if block is None else block.let_relations
            ):
                lets.append(
                    ProjectDeclarationOccurrence(
                        identity=ProjectNominalDeclarationIdentity(
                            module_path=module.path,
                            namespace=ProjectSymbolNamespace.RELATION,
                            declaration_kind=ProjectSymbolKind.QUERY,
                            declared_name=let.name,
                        ),
                        module_position=module.position,
                        declaration_position=declaration_position,
                        definition=_block_view_of(let),
                        let_position=let_position,
                        authored_block=let,
                    )
                )
        catalogs.append(
            ProjectModuleCatalog(
                module=module,
                occurrences=tuple(occurrences),
                lets=tuple(lets),
                table_functions=tuple(functions),
            )
        )

    return ProjectModuleCatalogSet(catalogs=tuple(catalogs))
