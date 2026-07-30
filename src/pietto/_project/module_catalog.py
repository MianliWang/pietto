"""Private module-qualified declaration identities and per-module catalogs."""

from __future__ import annotations

from dataclasses import dataclass

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
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
)

__all__: tuple[str, ...] = ()

_DEFINITION_TYPES = (
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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDeclarationOccurrence:
    """One source-ordered AST occurrence of a nominal declaration identity."""

    identity: ProjectNominalDeclarationIdentity
    module_position: int
    declaration_position: int
    definition: Definition

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


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleCatalog:
    """All local declaration occurrences owned by one parsed logical module."""

    module: ProjectLogicalModule
    occurrences: tuple[ProjectDeclarationOccurrence, ...] = ()

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
                or occurrence.definition is not definition
            ):
                raise ValueError(
                    "Module catalog occurrences must match source-ordered definitions."
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
        for declaration_position, definition in enumerate(
            module.parsed_input.script.definitions
        ):
            namespace, declaration_kind = _classify_project_definition(definition)
            occurrences.append(
                ProjectDeclarationOccurrence(
                    identity=ProjectNominalDeclarationIdentity(
                        module_path=module.path,
                        namespace=namespace,
                        declaration_kind=declaration_kind,
                        declared_name=definition.name,
                    ),
                    module_position=module.position,
                    declaration_position=declaration_position,
                    definition=definition,
                )
            )
        catalogs.append(
            ProjectModuleCatalog(module=module, occurrences=tuple(occurrences))
        )

    return ProjectModuleCatalogSet(catalogs=tuple(catalogs))
