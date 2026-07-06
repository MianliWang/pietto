"""Private immutable models for project discovery and configuration."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto.ast_nodes import (
    ConstraintDef,
    Definition,
    DeriveDef,
    EnumDef,
    QueryDef,
    Script,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
)
from pietto.errors import Diagnostic, Severity, SourceLocation

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_PROJECT_BUILTIN_TYPE_NAMES = frozenset(
    {
        "Any",
        "Bool",
        "Bytes",
        "Date",
        "Decimal",
        "Float",
        "Int",
        "Json",
        "Text",
        "Timestamp",
        "UUID",
    }
)


def _readonly_mapping(
    values: Mapping[_Key, _Value] | None = None,
) -> Mapping[_Key, _Value]:
    """Copy values into an immutable private mapping."""

    return MappingProxyType(dict(values or {}))


class ProjectDiscoveryErrorKind(StrEnum):
    """Private project discovery error categories."""

    PROJECT_ROOT = "project_root"
    CONFIG_READ = "config_read"
    CONFIG_PARSE = "config_parse"
    CONFIG_SCHEMA = "config_schema"
    PROJECT_PATH = "project_path"
    PROJECT_GLOB = "project_glob"
    PROJECT_RESOURCE = "project_resource"
    SOURCE_READ = "source_read"


@dataclass(frozen=True, slots=True)
class ProjectRoot:
    """Established project root as a project-relative identity."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectConfigPath:
    """Project configuration path relative to the established root."""

    path: str


@dataclass(frozen=True, slots=True)
class ProjectInput:
    """One explicitly selected project input."""

    path: str
    status: str


@dataclass(frozen=True, slots=True)
class ProjectParsedInput:
    """One successfully parsed selected project input for later semantics."""

    path: str
    script: Script


@dataclass(frozen=True, slots=True)
class ProjectSourceConfig:
    """Private project source pattern configuration."""

    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Private parsed project configuration."""

    schema_version: int
    sources: ProjectSourceConfig


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryError:
    """One private project discovery error."""

    kind: ProjectDiscoveryErrorKind
    message: str
    path: str | None = None


@dataclass(frozen=True, slots=True)
class ProjectDiscoveryResult:
    """Private project discovery result for future project-mode orchestration."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether discovery completed without private project errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class ProjectConfigLoadResult:
    """Private project configuration load result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    config: ProjectConfig | None
    errors: tuple[ProjectDiscoveryError, ...]

    @property
    def ok(self) -> bool:
        """Return whether configuration loading completed without errors."""

        return not self.errors


@dataclass(frozen=True, slots=True)
class ProjectParseCheckResult:
    """Private parse-only project check result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    inputs: tuple[ProjectInput, ...]
    errors: tuple[ProjectDiscoveryError, ...]
    diagnostics: tuple[Diagnostic, ...]
    parsed_inputs: tuple[ProjectParsedInput, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether parse-only project check completed without errors."""

        return not self.errors and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


class ProjectSymbolNamespace(StrEnum):
    """Project-wide namespace assigned to a top-level symbol."""

    TYPE = "type"
    RELATION = "relation"
    CALLABLE = "callable"


class ProjectSymbolKind(StrEnum):
    """Project-wide kind assigned to a top-level symbol."""

    TYPE_ALIAS = "type"
    ENUM = "enum"
    SHAPE = "shape"
    SOURCE = "source"
    TABLE = "table"
    QUERY = "query"
    CONSTRAINT = "constraint"
    DERIVE = "derive"


@dataclass(frozen=True, slots=True)
class ProjectSymbol:
    """One private project-wide top-level symbol."""

    namespace: ProjectSymbolNamespace
    kind: ProjectSymbolKind
    name: str
    path: str
    location: SourceLocation
    definition: Definition


class ProjectResolvedTypeKind(StrEnum):
    """Project-private type resolution fact kind."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProjectResolvedType:
    """One project-private resolved type name fact."""

    name: str
    kind: ProjectResolvedTypeKind
    symbol: ProjectSymbol | None = None


@dataclass(frozen=True, slots=True)
class ProjectSemanticCatalog:
    """Private project semantic catalog populated before reference resolution."""

    type_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    callable_symbols: Mapping[str, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )

    def __post_init__(self) -> None:
        """Copy symbol maps into immutable mappings."""

        object.__setattr__(
            self,
            "type_symbols",
            _readonly_mapping(self.type_symbols),
        )
        object.__setattr__(
            self,
            "relation_symbols",
            _readonly_mapping(self.relation_symbols),
        )
        object.__setattr__(
            self,
            "callable_symbols",
            _readonly_mapping(self.callable_symbols),
        )


@dataclass(frozen=True, slots=True)
class ProjectSemanticModel:
    """Private project-wide semantic model scaffold."""

    root: ProjectRoot
    config_path: ProjectConfigPath
    inputs: tuple[ProjectParsedInput, ...]
    catalog: ProjectSemanticCatalog
    type_resolutions: Mapping[TypeExpr, ProjectResolvedType] = field(
        default_factory=lambda: _readonly_mapping()
    )
    source_shape_resolutions: Mapping[SourceDef, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )

    def __post_init__(self) -> None:
        """Copy private project semantic maps into immutable mappings."""

        object.__setattr__(
            self,
            "type_resolutions",
            _readonly_mapping(self.type_resolutions),
        )
        object.__setattr__(
            self,
            "source_shape_resolutions",
            _readonly_mapping(self.source_shape_resolutions),
        )


@dataclass(frozen=True, slots=True)
class ProjectSemanticResult:
    """Private project-wide semantic scaffold result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    model: ProjectSemanticModel | None
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def ok(self) -> bool:
        """Return whether project semantic scaffolding completed without errors."""

        return self.model is not None and not any(
            diagnostic.severity is Severity.ERROR for diagnostic in self.diagnostics
        )


def build_empty_project_semantic_result(
    parse_result: ProjectParseCheckResult,
) -> ProjectSemanticResult:
    """Build the private project semantic scaffold from parse-only input."""

    if (
        not parse_result.ok
        or parse_result.root is None
        or parse_result.config_path is None
    ):
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
        )

    catalog, catalog_diagnostics = _build_project_semantic_catalog(
        parse_result.parsed_inputs
    )
    if catalog_diagnostics:
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=ProjectSemanticModel(
                root=parse_result.root,
                config_path=parse_result.config_path,
                inputs=parse_result.parsed_inputs,
                catalog=catalog,
            ),
            diagnostics=catalog_diagnostics,
        )

    type_resolutions, source_shape_resolutions, type_diagnostics = (
        _build_project_type_namespace_facts(
            parsed_inputs=parse_result.parsed_inputs,
            catalog=catalog,
        )
    )
    return ProjectSemanticResult(
        root=parse_result.root,
        config_path=parse_result.config_path,
        model=ProjectSemanticModel(
            root=parse_result.root,
            config_path=parse_result.config_path,
            inputs=parse_result.parsed_inputs,
            catalog=catalog,
            type_resolutions=type_resolutions,
            source_shape_resolutions=source_shape_resolutions,
        ),
        diagnostics=type_diagnostics,
    )


def _build_project_type_namespace_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
) -> tuple[
    dict[TypeExpr, ProjectResolvedType],
    dict[SourceDef, ProjectSymbol],
    tuple[Diagnostic, ...],
]:
    """Resolve top-level project type namespace references."""

    type_resolutions: dict[TypeExpr, ProjectResolvedType] = {}
    source_shape_resolutions: dict[SourceDef, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            for type_expr in _iter_project_type_expressions(definition):
                resolved_type = _resolve_project_type(type_expr, catalog)
                type_resolutions[type_expr] = resolved_type
                if resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN:
                    diagnostics.append(_unknown_project_type_diagnostic(type_expr))

            if isinstance(definition, SourceDef):
                symbol, diagnostic = _resolve_project_source_shape(
                    definition,
                    catalog,
                )
                if symbol is not None:
                    source_shape_resolutions[definition] = symbol
                if diagnostic is not None:
                    diagnostics.append(diagnostic)

    return type_resolutions, source_shape_resolutions, tuple(diagnostics)


def _iter_project_type_expressions(definition: Definition) -> tuple[TypeExpr, ...]:
    """Return supported top-level type expressions in source order."""

    if isinstance(definition, TypeDef):
        return (definition.base,)
    if isinstance(definition, (ConstraintDef, DeriveDef)):
        return tuple(parameter.type for parameter in definition.parameters) + (
            definition.return_type,
        )
    if isinstance(definition, ShapeDef):
        return tuple(field.type_expr for field in definition.fields)
    return ()


def _resolve_project_type(
    type_expr: TypeExpr,
    catalog: ProjectSemanticCatalog,
) -> ProjectResolvedType:
    """Resolve one project type reference without alias expansion."""

    if type_expr.name in _PROJECT_BUILTIN_TYPE_NAMES:
        return ProjectResolvedType(
            name=type_expr.name,
            kind=ProjectResolvedTypeKind.BUILTIN,
        )

    symbol = catalog.type_symbols.get(type_expr.name)
    if symbol is None:
        return ProjectResolvedType(
            name=type_expr.name,
            kind=ProjectResolvedTypeKind.UNKNOWN,
        )

    if symbol.kind is ProjectSymbolKind.TYPE_ALIAS:
        kind = ProjectResolvedTypeKind.TYPE_ALIAS
    elif symbol.kind is ProjectSymbolKind.ENUM:
        kind = ProjectResolvedTypeKind.ENUM
    elif symbol.kind is ProjectSymbolKind.SHAPE:
        kind = ProjectResolvedTypeKind.SHAPE
    else:
        raise AssertionError(f"Unsupported project type symbol kind: {symbol.kind}")
    return ProjectResolvedType(name=type_expr.name, kind=kind, symbol=symbol)


def _resolve_project_source_shape(
    source: SourceDef,
    catalog: ProjectSemanticCatalog,
) -> tuple[ProjectSymbol | None, Diagnostic | None]:
    """Resolve a source shape binding against the project type namespace."""

    if source.shape_name is None:
        return None, None

    symbol = catalog.type_symbols.get(source.shape_name)
    if symbol is None:
        return None, _project_source_shape_diagnostic(
            source,
            message=f"Unknown source shape: {source.shape_name}",
        )
    if symbol.kind is not ProjectSymbolKind.SHAPE:
        return None, _project_source_shape_diagnostic(
            source,
            message=f"Source shape must refer to a shape: {source.shape_name}",
        )
    return symbol, None


def _build_project_semantic_catalog(
    parsed_inputs: tuple[ProjectParsedInput, ...],
) -> tuple[ProjectSemanticCatalog, tuple[Diagnostic, ...]]:
    """Collect deterministic top-level project symbols before resolution."""

    type_symbols: dict[str, ProjectSymbol] = {}
    relation_symbols: dict[str, ProjectSymbol] = {}
    callable_symbols: dict[str, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            symbol = _project_symbol(parsed_input, definition)
            namespace = _symbol_map(
                symbol,
                type_symbols=type_symbols,
                relation_symbols=relation_symbols,
                callable_symbols=callable_symbols,
            )
            if symbol.name in namespace:
                diagnostics.append(_duplicate_project_symbol_diagnostic(symbol))
                continue
            namespace[symbol.name] = symbol

    return (
        ProjectSemanticCatalog(
            type_symbols=type_symbols,
            relation_symbols=relation_symbols,
            callable_symbols=callable_symbols,
        ),
        tuple(diagnostics),
    )


def _project_symbol(
    parsed_input: ProjectParsedInput,
    definition: Definition,
) -> ProjectSymbol:
    """Create one private project symbol for a top-level definition."""

    namespace, kind = _classify_project_definition(definition)
    location = _definition_location(definition, path=parsed_input.path)
    return ProjectSymbol(
        namespace=namespace,
        kind=kind,
        name=definition.name,
        path=parsed_input.path,
        location=location,
        definition=definition,
    )


def _classify_project_definition(
    definition: Definition,
) -> tuple[ProjectSymbolNamespace, ProjectSymbolKind]:
    """Classify a top-level definition into the Phase 45 hybrid namespace."""

    if isinstance(definition, TypeDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.TYPE_ALIAS
    if isinstance(definition, EnumDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.ENUM
    if isinstance(definition, ShapeDef):
        return ProjectSymbolNamespace.TYPE, ProjectSymbolKind.SHAPE
    if isinstance(definition, SourceDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.SOURCE
    if isinstance(definition, TableDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.TABLE
    if isinstance(definition, QueryDef):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind.QUERY
    if isinstance(definition, ConstraintDef):
        return ProjectSymbolNamespace.CALLABLE, ProjectSymbolKind.CONSTRAINT
    if isinstance(definition, DeriveDef):
        return ProjectSymbolNamespace.CALLABLE, ProjectSymbolKind.DERIVE
    raise AssertionError(f"Unsupported project definition: {type(definition).__name__}")


def _symbol_map(
    symbol: ProjectSymbol,
    *,
    type_symbols: dict[str, ProjectSymbol],
    relation_symbols: dict[str, ProjectSymbol],
    callable_symbols: dict[str, ProjectSymbol],
) -> dict[str, ProjectSymbol]:
    """Return the mutable catalog map for a classified project symbol."""

    if symbol.namespace is ProjectSymbolNamespace.TYPE:
        return type_symbols
    if symbol.namespace is ProjectSymbolNamespace.RELATION:
        return relation_symbols
    if symbol.namespace is ProjectSymbolNamespace.CALLABLE:
        return callable_symbols
    raise AssertionError(f"Unsupported project namespace: {symbol.namespace}")


def _definition_location(definition: Definition, *, path: str) -> SourceLocation:
    """Convert a top-level definition span into a project diagnostic location."""

    span = definition.span
    return SourceLocation(
        path=span.path or path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _duplicate_project_symbol_diagnostic(symbol: ProjectSymbol) -> Diagnostic:
    """Report a duplicate at the later project definition's complete span."""

    return Diagnostic(
        code="PIE-S2001",
        severity=Severity.ERROR,
        message=(
            "Duplicate symbol name in "
            f"{symbol.namespace.value} namespace: {symbol.name}"
        ),
        location=symbol.location,
    )


def _unknown_project_type_diagnostic(type_expr: TypeExpr) -> Diagnostic:
    """Report an unresolved project type name at the type expression span."""

    span = type_expr.span
    return Diagnostic(
        code="PIE-S2002",
        severity=Severity.ERROR,
        message=f"Unknown type: {type_expr.name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_source_shape_diagnostic(
    source: SourceDef,
    *,
    message: str,
) -> Diagnostic:
    """Report an invalid project source shape binding."""

    span = source.span
    return Diagnostic(
        code="PIE-S2303",
        severity=Severity.ERROR,
        message=message,
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )
