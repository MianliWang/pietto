"""Private immutable models for project discovery and configuration."""

from __future__ import annotations

from pietto.ast_nodes import (
    SetRelationDef,
    TableFunctionRelationDef,
    UnnestRelationDef,
    ValuesRelationDef,
)
from pietto._flat_relational_admission import (
    _EXPLICIT_MODULES,
    availability_diagnostic,
    legacy_flat_refusals,
    syntax_diagnostics,
)
from pietto._syntax_admission import source_order

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TYPE_CHECKING, TypeVar

from pietto._project.module_carrier import (
    ProjectCompilationMode,
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.path_trust import ProjectPinnedRoot
from pietto._project.selected_input_index import ProjectSelectedInputIndex
from pietto._project.trusted_source import ProjectTrustedSourceSnapshot
from pietto.ast_nodes import (
    BetweenExpr,
    BinaryExpr,
    CallExpr,
    CapturedFieldExpr,
    CastExpr,
    CollectRelationExpr,
    CheckDef,
    ComparisonExpr,
    ConditionalExpr,
    ConstraintDef,
    Definition,
    DeriveDef,
    DottedNameExpr,
    EnumDef,
    Expression,
    FieldDef,
    FromClause,
    FunctionDef,
    IndexDef,
    IsNullExpr,
    LiteralExpr,
    MembershipExpr,
    NameExpr,
    Nullability,
    QueryDef,
    AnyExpr,
    RelationExistsExpr,
    RelationScalarExpr,
    RelationMembershipExpr,
    Script,
    SelectItem,
    ShapeDef,
    SourceDef,
    TableDef,
    TypeDef,
    TypeExpr,
    UnaryExpr,
    WindowExpr,
    inlined_arguments,
)
from pietto.errors import Diagnostic, Severity, SourceLocation
from pietto.semantic.capability_facts import CapabilityKey, CapabilitySupport
from pietto.semantic.capability_profiles import (
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileTarget,
)

if TYPE_CHECKING:
    from pietto.semantic.existence_generators import AnyUseInfo, AnyValueInfo
    from pietto._project.project_final_outputs import ProjectNoJoinScalarExpression
    from pietto.semantic.model import ValueType
    from pietto._project.project_compiled_schema import Address, Description, Record
    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
    from pietto._project.module_attribution import ProjectModuleAttributionFactSet
    from pietto._project.module_bindings import ProjectModuleBindingEnvironmentSet
    from pietto._project.module_catalog import (
        ProjectDeclarationOccurrence,
        ProjectModuleCatalogSet,
    )
    from pietto._project.module_exports import ProjectModuleExportSurfaceSet
    from pietto._project.module_graph import (
        ProjectModuleDiagnosticSet,
        ProjectModuleGraph,
    )
    from pietto._project.module_inspection import ProjectModuleInspectionFactSet
    from pietto._project.module_package_neutral_identity import (
        ProjectModulePackageNeutralIdentityFactSet,
    )
    from pietto._project.module_relation_resolution import (
        ProjectModuleRelationResolutionSet,
    )
    from pietto._project.module_resolution import ProjectTypeSourceResolutionSet
    from pietto._project.module_semantic_fact_preservation import (
        ProjectModuleSemanticFactSet,
    )
    from pietto._project.nested_relation_facts import ProjectNestedRelationFactSet
    from pietto._project.row_dependency_graph import ProjectRelationRowDependencyGraph
    from pietto._project.row_lineage import ProjectRelationRowLineage
    from pietto._project.window_semantics import WindowResultProjectFact

_Key = TypeVar("_Key")
_InnerKey = TypeVar("_InnerKey")
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


_KNOWN_EXPRESSIONS = frozenset(
    {
        LiteralExpr,
        NameExpr,
        DottedNameExpr,
        CallExpr,
        UnaryExpr,
        ConditionalExpr,
        MembershipExpr,
        CastExpr,
        BinaryExpr,
        ComparisonExpr,
        BetweenExpr,
        IsNullExpr,
        WindowExpr,
        AnyExpr,
        RelationExistsExpr,
        RelationScalarExpr,
        RelationMembershipExpr,
    }
)
_KNOWN_DEFINITIONS = frozenset(
    {
        TypeDef,
        EnumDef,
        ShapeDef,
        ConstraintDef,
        DeriveDef,
        SourceDef,
        TableDef,
        QueryDef,
        SetRelationDef,
    }
)


def _readonly_mapping(
    values: Mapping[_Key, _Value] | None = None,
) -> Mapping[_Key, _Value]:
    """Copy values into an immutable private mapping."""

    return MappingProxyType(dict(values or {}))


def _readonly_nested_mapping(
    values: Mapping[_Key, Mapping[_InnerKey, _Value]] | None = None,
) -> Mapping[_Key, Mapping[_InnerKey, _Value]]:
    """Copy both levels of one nested mapping into immutable mappings."""

    if values is None:
        return MappingProxyType({})
    return MappingProxyType(
        {key: _readonly_mapping(inner_values) for key, inner_values in values.items()}
    )


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
    scalar_callables: tuple[FunctionDef, ...] = ()
    existence_generators: tuple[AnyUseInfo, ...] = ()
    existence_values: tuple[AnyValueInfo, ...] = ()
    # The script as parsed when a project resolved its query names into
    # ``script``. A LEGACY_FLAT project's semantic checks analyze the parsed
    # one, and its model refuses each JOIN and any(...) as written there; an
    # EXPLICIT_MODULES project's nested-relation facts read its Unnest lets
    # and JOINs there.
    authored_script: Script | None = None

    def __post_init__(self) -> None:
        if type(self.scalar_callables) is not tuple or any(
            type(item) is not FunctionDef for item in self.scalar_callables
        ):
            raise TypeError(
                "Parsed scalar callables require exact ordered declarations."
            )
        if type(self.existence_values) is not tuple:
            raise TypeError("Project ANY values require an exact tuple.")
        if self.existence_values:
            from pietto.semantic.existence_generators import AnyValueInfo, AnyValueTrace

            if any(type(value) is not AnyValueInfo for value in self.existence_values):
                raise TypeError("Project ANY values require exact occurrence facts.")
            AnyValueTrace(self.script, uses=self.existence_values)
        if type(self.existence_generators) is not tuple:
            raise TypeError("Parsed ANY uses require an exact ordered tuple.")
        if self.existence_generators:
            from pietto.semantic.existence_generators import AnyUseInfo

            if any(
                type(use) is not AnyUseInfo
                or not any(use.owner is owner for owner in self.script.definitions)
                or not 1 <= use.input_ordinal <= len(use.owner.join_clauses)
                or use.owner.join_clauses[use.input_ordinal - 1] is not use.clause
                for use in self.existence_generators
            ):
                raise ValueError(
                    "Parsed ANY uses require exact normalized owner and input occurrences."
                )


@dataclass(frozen=True, slots=True)
class ProjectSourceConfig:
    """Private project source pattern configuration."""

    include_patterns: tuple[str, ...]
    exclude_patterns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProjectRootPackageActivation:
    """Private authored root-package activation for schema-v3/v4 projects."""

    path: str
    namespace: str
    name: str
    version: str
    sha256: str

    def __post_init__(self) -> None:
        """Keep the carrier structural; later slices own field semantics."""

        if not _is_valid_project_root_package_path(self.path):
            raise ValueError(
                "Project root package path must be a normalized project-relative directory."
            )
        if any(
            type(value) is not str or not value
            for value in (self.namespace, self.name, self.version, self.sha256)
        ):
            raise ValueError("Project root package fields must be non-empty strings.")


def _is_valid_project_root_package_path(value: object) -> bool:
    """Return whether one authored package path is structural-only valid."""

    if type(value) is not str or not value or "\x00" in value or "\\" in value:
        return False
    if value == ".":
        return True
    if value.startswith("/") or value.startswith("//") or value.endswith("/"):
        return False
    if len(value) >= 2 and value[0].isalpha() and value[1] == ":":
        return False
    return all(part not in {"", ".", ".."} for part in value.split("/"))


def _require_project_nonblank_text(value: object, label: str) -> None:
    if type(value) is not str or not value.strip():
        raise ValueError(f"{label} requires exact nonblank text.")


def _require_project_position(value: object, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} requires an exact non-negative position.")


@dataclass(frozen=True, slots=True)
class ProjectCapabilityProfileFactDeclaration:
    """One source-ordered project-authored target-side capability fact."""

    position: int
    support: CapabilitySupport
    key: CapabilityKey

    def __post_init__(self) -> None:
        _require_project_position(self.position, "Project capability fact")
        if type(self.support) is not CapabilitySupport:
            raise ValueError("Project capability fact requires an exact support.")
        if type(self.key) is not CapabilityKey:
            raise ValueError("Project capability fact requires an exact key.")


@dataclass(frozen=True, slots=True)
class ProjectCapabilityProfileDeclaration:
    """One source-ordered project-owned static capability profile declaration."""

    position: int
    reference: CapabilityProfileReference
    kind: CapabilityProfileKind
    target: CapabilityProfileTarget
    base: CapabilityProfileReference | None
    facts: tuple[ProjectCapabilityProfileFactDeclaration, ...]

    def __post_init__(self) -> None:
        _require_project_position(self.position, "Project capability profile")
        if type(self.reference) is not CapabilityProfileReference:
            raise ValueError("Project capability profile requires an exact reference.")
        if type(self.kind) is not CapabilityProfileKind:
            raise ValueError("Project capability profile requires an exact kind.")
        if type(self.target) is not CapabilityProfileTarget:
            raise ValueError("Project capability profile requires an exact target.")
        if type(self.facts) is not tuple or any(
            type(fact) is not ProjectCapabilityProfileFactDeclaration
            for fact in self.facts
        ):
            raise ValueError("Project capability profile requires exact facts.")
        if any(fact.position != position for position, fact in enumerate(self.facts)):
            raise ValueError(
                "Project capability profile fact positions must be dense and ordered."
            )
        if self.kind is CapabilityProfileKind.BASE:
            if (
                self.target.extension_identity is not None
                or self.target.extension_release is not None
                or self.base is not None
            ):
                raise ValueError(
                    "BASE project profiles require only a database target."
                )
        elif (
            self.target.extension_identity is None
            or self.target.extension_release is None
            or type(self.base) is not CapabilityProfileReference
        ):
            raise ValueError(
                "OVERLAY project profiles require an extension target and exact base."
            )


@dataclass(frozen=True, slots=True)
class ProjectCapabilityTargetSelection:
    """One explicit source-ordered evaluated-target profile selection."""

    position: int
    database_family: str
    database_release: str
    base_profile: CapabilityProfileReference
    overlay_profiles: tuple[CapabilityProfileReference, ...]

    def __post_init__(self) -> None:
        _require_project_position(self.position, "Project capability target")
        _require_project_nonblank_text(
            self.database_family,
            "Project capability target database family",
        )
        _require_project_nonblank_text(
            self.database_release,
            "Project capability target database release",
        )
        if type(self.base_profile) is not CapabilityProfileReference:
            raise ValueError(
                "Project capability target requires an exact base profile."
            )
        if type(self.overlay_profiles) is not tuple or any(
            type(reference) is not CapabilityProfileReference
            for reference in self.overlay_profiles
        ):
            raise ValueError(
                "Project capability target requires exact ordered overlays."
            )


@dataclass(frozen=True, slots=True)
class ProjectCapabilityEnvironmentConfig:
    """One normalized explicit project capability environment."""

    profiles: tuple[ProjectCapabilityProfileDeclaration, ...]
    targets: tuple[ProjectCapabilityTargetSelection, ...]

    def __post_init__(self) -> None:
        if type(self.profiles) is not tuple or any(
            type(profile) is not ProjectCapabilityProfileDeclaration
            for profile in self.profiles
        ):
            raise ValueError("Project capability environment requires exact profiles.")
        if any(
            profile.position != position
            for position, profile in enumerate(self.profiles)
        ):
            raise ValueError(
                "Project capability profile positions must be dense and ordered."
            )
        if type(self.targets) is not tuple or any(
            type(target) is not ProjectCapabilityTargetSelection
            for target in self.targets
        ):
            raise ValueError("Project capability environment requires exact targets.")
        if any(
            target.position != position for position, target in enumerate(self.targets)
        ):
            raise ValueError(
                "Project capability target positions must be dense and ordered."
            )


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    """Private parsed project configuration."""

    schema_version: int
    sources: ProjectSourceConfig | None
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT
    root_package: ProjectRootPackageActivation | None = None
    capability_environment: ProjectCapabilityEnvironmentConfig | None = None

    def __post_init__(self) -> None:
        """Enforce the exact schema-version/configuration tagged union."""

        if type(self.schema_version) is not int:
            raise TypeError("Project configuration requires an exact schema version.")
        if type(self.compilation_mode) is not ProjectCompilationMode:
            raise TypeError("Project configuration requires an exact compilation mode.")
        if self.schema_version == 1:
            expected_mode = ProjectCompilationMode.LEGACY_FLAT
        elif self.schema_version == 2:
            expected_mode = ProjectCompilationMode.EXPLICIT_MODULES
        elif self.schema_version == 3:
            expected_mode = ProjectCompilationMode.PACKAGE_ROOT
        elif self.schema_version == 4:
            expected_mode = ProjectCompilationMode.PACKAGE_ROOT
        else:
            raise ValueError(
                "Project configuration requires schema version 1, 2, 3, or 4."
            )
        if self.compilation_mode is not expected_mode:
            raise ValueError(
                "Project configuration schema and compilation mode mismatch."
            )
        if self.schema_version == 3:
            if (
                self.sources is not None
                or type(self.root_package) is not ProjectRootPackageActivation
                or self.capability_environment is not None
            ):
                raise ValueError(
                    "Schema-v3 project configuration requires only a root package activation."
                )
            return
        if self.schema_version == 4:
            if (
                self.sources is not None
                or type(self.root_package) is not ProjectRootPackageActivation
                or type(self.capability_environment)
                is not ProjectCapabilityEnvironmentConfig
            ):
                raise ValueError(
                    "Schema-v4 project configuration requires a root package and capability environment."
                )
            return
        if (
            type(self.sources) is not ProjectSourceConfig
            or self.root_package is not None
            or self.capability_environment is not None
        ):
            raise ValueError(
                "Schema-v1/v2 project configuration requires only source selection."
            )


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
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT
    modules: tuple[ProjectLogicalModule, ...] = ()
    pinned_root: ProjectPinnedRoot | None = None
    selected_input_index: ProjectSelectedInputIndex | None = None

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
    pinned_root: ProjectPinnedRoot | None = None

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
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT
    modules: tuple[ProjectLogicalModule, ...] = ()
    pinned_root: ProjectPinnedRoot | None = None
    selected_input_index: ProjectSelectedInputIndex | None = None
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...] = ()
    # The facts, with their related locations, of the module diagnostics a
    # check that stops at a query-local naming error reports.
    module_diagnostic_facts: ProjectModuleDiagnosticSet | None = None

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
    definition: (
        Definition | ValuesRelationDef | TableFunctionRelationDef | UnnestRelationDef
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


class ProjectModuleRowFieldKind(StrEnum):
    """Distinct schema, source-row, and relation-output field identities."""

    SHAPE_FIELD = "shape_field"
    SOURCE_FIELD = "source_field"
    RELATION_OUTPUT = "relation_output"


def _validate_position(value: int, label: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{label} position must be a non-negative integer.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectDeclarationOccurrenceIdentity:
    """Semantic locator for one selected declaration occurrence."""

    identity: ProjectNominalDeclarationIdentity
    module_position: int
    declaration_position: int
    let_position: int | None = None
    # True for the table-function input of the body at these positions.
    table_function: bool = False
    # D-S05-1: the Unnest let at this index of the declaration body's
    # authored `let` declarations; one body may write several.
    unnest_position: int | None = None

    def __post_init__(self) -> None:
        if type(self.identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Declaration occurrence identity requires a nominal ID.")
        _validate_position(self.module_position, "module")
        _validate_position(self.declaration_position, "declaration")
        if self.let_position is not None:
            _validate_position(self.let_position, "let")
        if type(self.table_function) is not bool:
            raise TypeError("Declaration occurrence table-function flag is a bool.")
        if self.unnest_position is not None:
            _validate_position(self.unnest_position, "Unnest")
            if self.let_position is not None or self.table_function:
                raise ValueError(
                    "An Unnest occurrence is neither a relation let nor a "
                    "table-function input."
                )

    @property
    def block_local(self) -> bool:
        """A relation let, table-function input or Unnest, never a declaration."""

        return (
            self.let_position is not None
            or self.table_function
            or self.unnest_position is not None
        )


def project_declaration_occurrence_identity(
    occurrence: ProjectDeclarationOccurrence,
) -> ProjectDeclarationOccurrenceIdentity:
    """The one semantic locator of one catalog occurrence (D-S05-1): every
    reader builds it here, so an Unnest occurrence never takes the identity
    of the declaration whose body writes it."""

    return ProjectDeclarationOccurrenceIdentity(
        identity=occurrence.identity,
        module_position=occurrence.module_position,
        declaration_position=occurrence.declaration_position,
        let_position=occurrence.let_position,
        table_function=occurrence.table_function is not None,
        unnest_position=occurrence.unnest_position,
    )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModuleRowFieldIdentity:
    """One occurrence-safe shape, source, or relation row field identity."""

    owner: ProjectDeclarationOccurrenceIdentity
    kind: ProjectModuleRowFieldKind
    field_position: int
    name: str

    def __post_init__(self) -> None:
        if type(self.owner) is not ProjectDeclarationOccurrenceIdentity:
            raise TypeError("Row field identity requires an owner occurrence.")
        if type(self.kind) is not ProjectModuleRowFieldKind:
            raise TypeError("Row field identity requires an exact kind.")
        _validate_position(self.field_position, "row field")
        if type(self.name) is not str or not self.name:
            raise ValueError("Row field identity requires a name.")
        owner_kind = self.owner.identity.declaration_kind
        expected = {
            ProjectModuleRowFieldKind.SHAPE_FIELD: {ProjectSymbolKind.SHAPE},
            ProjectModuleRowFieldKind.SOURCE_FIELD: {ProjectSymbolKind.SOURCE},
            ProjectModuleRowFieldKind.RELATION_OUTPUT: {
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            },
        }[self.kind]
        if owner_kind not in expected:
            raise ValueError("Row field kind does not match its owner declaration.")


class ProjectResolvedTypeKind(StrEnum):
    """Project-private type resolution fact kind."""

    BUILTIN = "builtin"
    TYPE_ALIAS = "type"
    ENUM = "enum"
    SHAPE = "shape"
    UNKNOWN = "unknown"
    # The value of a Collect read: a collected relation, never a scalar.
    NESTED_RELATION = "nested_relation"


# The kinds of a scalar value. A reader that types, compares, orders or groups
# a value admits only these, so a nested relation (or any later kind) fails
# closed there (D-S04-3).
SCALAR_RESOLVED_TYPE_KINDS = frozenset(
    {
        ProjectResolvedTypeKind.BUILTIN,
        ProjectResolvedTypeKind.TYPE_ALIAS,
        ProjectResolvedTypeKind.ENUM,
        ProjectResolvedTypeKind.SHAPE,
    }
)


# The name of every nested relation type: an internal placeholder, never a
# spelling any public output shows.
NESTED_RELATION_TYPE_NAME = "<nested relation>"


@dataclass(frozen=True, slots=True)
class ProjectResolvedType:
    """One project-private resolved type name fact.

    A NESTED_RELATION type carries its exact ``nested`` descriptor; no other
    kind has one.
    """

    name: str
    kind: ProjectResolvedTypeKind
    symbol: ProjectSymbol | None = None
    nested: ProjectNestedRelationType | None = field(default=None, kw_only=True)

    def __post_init__(self) -> None:
        if (self.kind is ProjectResolvedTypeKind.NESTED_RELATION) != (
            self.nested is not None
        ):
            raise ValueError("Only a nested relation type has a nested descriptor.")
        if self.nested is not None and (
            type(self.nested) is not ProjectNestedRelationType
            or self.name != NESTED_RELATION_TYPE_NAME
            or self.symbol is not None
        ):
            raise TypeError("A nested relation type requires its exact descriptor.")


def nested_relation_type(nested: ProjectNestedRelationType) -> ProjectResolvedType:
    """The resolved type of a Collect read's value (D-S04-1)."""

    return ProjectResolvedType(
        name=NESTED_RELATION_TYPE_NAME,
        kind=ProjectResolvedTypeKind.NESTED_RELATION,
        nested=nested,
    )


class ProjectRowFieldNullability(StrEnum):
    """Project-private row field nullability fact."""

    NON_NULL = "non_null"
    NULLABLE = "nullable"
    UNKNOWN = "unknown"


class ProjectRowResultRole(StrEnum):
    """Project-private calculation-site role for one row field."""

    ORDINARY_ROW_VALUE = "ordinary_row_value"
    GROUP_KEY = "group_key"
    AGGREGATE_RESULT = "aggregate_result"
    WINDOW_RESULT = "window_result"


class ProjectRowFieldProvenanceKind(StrEnum):
    """Project-private row field provenance categories for future slices."""

    SOURCE_FIELD = "source_field"
    DIRECT_PROJECTION = "direct_projection"
    DERIVED_EXPRESSION = "derived_expression"
    LET_DERIVED = "let_derived"
    EXPRESSION = "expression"
    AGGREGATE = "aggregate"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class ProjectRowFieldProvenance:
    """Inert private origin metadata for a future project row field."""

    kind: ProjectRowFieldProvenanceKind
    symbol: ProjectSymbol | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class ProjectRowField:
    """One private project row field scaffold fact."""

    name: str
    resolved_type: ProjectResolvedType
    nullability: ProjectRowFieldNullability
    field_def: FieldDef | None = None
    provenance: ProjectRowFieldProvenance | None = None
    result_role: ProjectRowResultRole = ProjectRowResultRole.ORDINARY_ROW_VALUE


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectNestedRelationElementField:
    """One child field of a collected relation, in its let's output order.

    The child's identity and nullability are its type; its field evidence is
    the let's own field fact, compared by identity where it matters.
    """

    position: int
    identity: ProjectModuleRowFieldIdentity
    field: ProjectRowField = field(compare=False)
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
    """The element relation and ordered child fields of a collected relation.

    Two types are equal when they collect the same let occurrence: equal
    child fields of another let are another type. Whether the collected value
    may be None is its field's nullability: a direct Collect is never None
    (D71.04).
    """

    element_relation: ProjectDeclarationOccurrenceIdentity
    element_fields: tuple[ProjectNestedRelationElementField, ...]
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
        if type(self.collection_depth) is not int or self.collection_depth != 1:
            raise ValueError("Exactly one collection layer is supported.")


def project_collect_output_field(
    name: str, resolved_type: ProjectResolvedType, location: SourceLocation
) -> ProjectRowField:
    """The output field of one typed Collect read: a nested relation that is
    never None (D71.04)."""

    if resolved_type.kind is not ProjectResolvedTypeKind.NESTED_RELATION:
        raise ValueError("A Collect output holds a nested relation.")
    return ProjectRowField(
        name=name,
        resolved_type=resolved_type,
        nullability=ProjectRowFieldNullability.NON_NULL,
        field_def=None,
        provenance=ProjectRowFieldProvenance(
            kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
            location=location,
        ),
    )


@dataclass(frozen=True, slots=True)
class ProjectAggregateResultFact:
    """One inert private aggregate selected-output identity fact."""

    function: str
    output_name: str
    grouped: bool
    argument_count: int
    location: SourceLocation

    def __post_init__(self) -> None:
        """Validate only the structural shape of one aggregate result fact."""

        if type(self.function) is not str or not self.function:
            raise ValueError("Project aggregate result fact requires function")
        if type(self.output_name) is not str or not self.output_name:
            raise ValueError("Project aggregate result fact requires output name")
        if type(self.grouped) is not bool:
            raise ValueError("Project aggregate result fact requires grouped bool")
        if type(self.argument_count) is not int or self.argument_count < 0:
            raise ValueError(
                "Project aggregate result fact requires non-negative argument count"
            )
        if not isinstance(self.location, SourceLocation):
            raise ValueError("Project aggregate result fact requires source location")


@dataclass(frozen=True, slots=True)
class ProjectRowSchema:
    """Ordered private project row schema scaffold."""

    fields: Mapping[str, ProjectRowField] = field(
        default_factory=lambda: _readonly_mapping()
    )
    is_unknown: bool = False

    def __post_init__(self) -> None:
        """Copy row field maps into immutable mappings."""

        object.__setattr__(self, "fields", _readonly_mapping(self.fields))


class ProjectRelationRowSchemaStatus(StrEnum):
    """Private relation row schema availability states for future propagation."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"


class ProjectRelationRowSchemaReason(StrEnum):
    """Private relation row schema availability reasons."""

    DIRECT_SOURCE_CONCRETE = "direct_source_concrete"
    TABLE_UPSTREAM_CONCRETE = "table_upstream_concrete"
    RELATION_UPSTREAM_CONCRETE = "relation_upstream_concrete"
    UNKNOWN_SCHEMA = "unknown_schema"
    DUPLICATE_OUTPUT_NAME = "duplicate_output_name"
    DUPLICATE_GROUP_KEY = "duplicate_group_key"
    UNAVAILABLE_AGGREGATE_OR_GROUPED_FACT = "unavailable_aggregate_or_grouped_fact"
    INVALID_AGGREGATE_OR_GROUPED_OUTPUT = "invalid_aggregate_or_grouped_output"
    AGGREGATE_OR_GROUPED_DEFERRED = "aggregate_grouped_deferred"
    CONFLICTING_AGGREGATE_OR_GROUPED_FACTS = "conflicting_aggregate_or_grouped_facts"
    UNAVAILABLE_WINDOW_RESULT_FACT = "unavailable_window_result_fact"
    INVALID_WINDOW_OUTPUT = "invalid_window_output"
    WINDOW_RESULT_DEFERRED = "window_result_deferred"
    CONFLICTING_WINDOW_RESULT_FACTS = "conflicting_window_result_facts"
    RELATIONAL_SYNTAX_UNSUPPORTED = "relational_syntax_unsupported"
    AUTHORED_JOIN_DEFERRED = "authored_join_deferred"
    DEFERRED_PHASE48_BEHAVIOR = "deferred_phase48_behavior"
    UNRESOLVED_RELATION_BLOCKED = "unresolved_relation_blocked"
    CYCLE_BLOCKED = "cycle_blocked"
    UPSTREAM_UNKNOWN = "upstream_unknown"
    UPSTREAM_DEFERRED = "upstream_deferred"
    UPSTREAM_BLOCKED = "upstream_blocked"


@dataclass(frozen=True, slots=True)
class ProjectRelationRowSchemaState:
    """Private relation row schema availability carrier."""

    status: ProjectRelationRowSchemaStatus
    schema: ProjectRowSchema | None
    reason: ProjectRelationRowSchemaReason

    def __post_init__(self) -> None:
        """Validate private availability carrier invariants."""

        if not isinstance(self.status, ProjectRelationRowSchemaStatus):
            raise ValueError("Project relation row schema state requires a status")
        if not isinstance(self.reason, ProjectRelationRowSchemaReason):
            raise ValueError("Project relation row schema state requires a reason")

        if self.status is ProjectRelationRowSchemaStatus.CONCRETE:
            if self.schema is None:
                raise ValueError("Concrete relation row schema state requires schema")
            if self.schema.is_unknown:
                raise ValueError("Concrete relation row schema state cannot be unknown")
            return

        if self.status is ProjectRelationRowSchemaStatus.UNKNOWN:
            if self.schema is None:
                raise ValueError("Unknown relation row schema state requires schema")
            if not self.schema.is_unknown:
                raise ValueError(
                    "Unknown relation row schema state requires unknown schema"
                )
            return

        if self.schema is not None:
            raise ValueError(
                "Deferred or blocked relation row schema state forbids schema"
            )


class _ProjectDirectFieldProjectionStatus(StrEnum):
    """Private status for one direct-field projection candidate."""

    SUPPORTED = "supported"
    INVALID = "invalid"
    DEFERRED = "deferred"


@dataclass(frozen=True, slots=True)
class _ProjectDirectFieldProjection:
    """Private decoded direct-field projection candidate."""

    status: _ProjectDirectFieldProjectionStatus
    output_name: str | None = None
    lookup_name: str | None = None
    field_text: str | None = None
    location: SourceLocation | None = None


@dataclass(frozen=True, slots=True)
class _ProjectRelationRowSchemaResult:
    """Private result for one relation row schema build attempt."""

    schema: ProjectRowSchema | None
    diagnostics: tuple[Diagnostic, ...] = ()
    state_reason: ProjectRelationRowSchemaReason | None = None


@dataclass(frozen=True, slots=True)
class _ProjectRelationRowSchemasResult:
    """Private result for all project relation row schemas."""

    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema]
    relation_row_schema_states: dict[TableDef | QueryDef, ProjectRelationRowSchemaState]
    relation_let_scope_facts: dict[TableDef | QueryDef, ProjectRelationLetScopeFacts]
    relation_aggregate_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, ProjectAggregateResultFact],
    ]
    relation_window_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, WindowResultProjectFact],
    ]
    relation_row_dependency_graphs: dict[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ]
    relation_row_lineages: dict[TableDef | QueryDef, ProjectRelationRowLineage]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyNode:
    """One private relation dependency graph node."""

    symbol: ProjectSymbol


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencySource:
    """One private source location for a future relation dependency edge."""

    from_clause: FromClause


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyEdge:
    """One private relation dependency graph edge."""

    origin: ProjectRelationDependencyNode
    target: ProjectRelationDependencyNode
    dependency_source: ProjectRelationDependencySource


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyCycle:
    """One private relation dependency cycle fact."""

    nodes: tuple[ProjectRelationDependencyNode, ...]
    edges: tuple[ProjectRelationDependencyEdge, ...]

    def __post_init__(self) -> None:
        """Copy cycle collections into immutable tuples."""

        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))


@dataclass(frozen=True, slots=True)
class ProjectRelationDependencyGraph:
    """Private relation dependency graph scaffold."""

    nodes: tuple[ProjectRelationDependencyNode, ...] = ()
    edges: tuple[ProjectRelationDependencyEdge, ...] = ()
    cycles: tuple[ProjectRelationDependencyCycle, ...] = ()

    def __post_init__(self) -> None:
        """Copy graph collections into immutable tuples."""

        object.__setattr__(self, "nodes", tuple(self.nodes))
        object.__setattr__(self, "edges", tuple(self.edges))
        object.__setattr__(self, "cycles", tuple(self.cycles))


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
    relation_resolutions: Mapping[FromClause, ProjectSymbol] = field(
        default_factory=lambda: _readonly_mapping()
    )
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema] = field(
        default_factory=lambda: _readonly_mapping()
    )
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_let_scope_facts: Mapping[
        TableDef | QueryDef, ProjectRelationLetScopeFacts
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_row_dependency_graphs: Mapping[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_row_lineages: Mapping[TableDef | QueryDef, ProjectRelationRowLineage] = (
        field(default_factory=lambda: _readonly_mapping())
    )
    relation_dependency_graph: ProjectRelationDependencyGraph = field(
        default_factory=ProjectRelationDependencyGraph
    )
    relation_aggregate_result_facts: Mapping[
        TableDef | QueryDef,
        Mapping[str, ProjectAggregateResultFact],
    ] = field(default_factory=lambda: _readonly_mapping())
    relation_window_result_facts: Mapping[
        TableDef | QueryDef,
        Mapping[str, WindowResultProjectFact],
    ] = field(default_factory=lambda: _readonly_mapping())

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
        object.__setattr__(
            self,
            "relation_resolutions",
            _readonly_mapping(self.relation_resolutions),
        )
        object.__setattr__(
            self,
            "source_row_schemas",
            _readonly_mapping(self.source_row_schemas),
        )
        object.__setattr__(
            self,
            "relation_row_schemas",
            _readonly_mapping(self.relation_row_schemas),
        )
        object.__setattr__(
            self,
            "relation_row_schema_states",
            _readonly_mapping(self.relation_row_schema_states),
        )
        object.__setattr__(
            self,
            "relation_let_scope_facts",
            _readonly_mapping(self.relation_let_scope_facts),
        )
        object.__setattr__(
            self,
            "relation_row_dependency_graphs",
            _readonly_mapping(self.relation_row_dependency_graphs),
        )
        object.__setattr__(
            self,
            "relation_row_lineages",
            _readonly_mapping(self.relation_row_lineages),
        )
        object.__setattr__(
            self,
            "relation_aggregate_result_facts",
            _readonly_nested_mapping(self.relation_aggregate_result_facts),
        )
        object.__setattr__(
            self,
            "relation_window_result_facts",
            _readonly_nested_mapping(self.relation_window_result_facts),
        )
        _validate_project_aggregate_result_facts(
            relation_row_schemas=self.relation_row_schemas,
            relation_aggregate_result_facts=self.relation_aggregate_result_facts,
        )
        _validate_project_window_result_facts(
            relation_row_schemas=self.relation_row_schemas,
            relation_window_result_facts=self.relation_window_result_facts,
        )


def _validate_project_aggregate_result_facts(
    *,
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_aggregate_result_facts: Mapping[
        TableDef | QueryDef,
        Mapping[str, ProjectAggregateResultFact],
    ],
) -> None:
    """Validate inert aggregate-result facts against supplied private schemas."""

    for definition, facts in relation_aggregate_result_facts.items():
        if not isinstance(definition, (TableDef, QueryDef)):
            raise ValueError("Project aggregate result facts require relation keys")
        schema = relation_row_schemas.get(definition)
        if schema is None:
            raise ValueError("Project aggregate result facts require relation schema")
        for output_name, fact in facts.items():
            if not isinstance(fact, ProjectAggregateResultFact):
                raise ValueError("Project aggregate result facts require fact values")
            if output_name != fact.output_name:
                raise ValueError("Project aggregate result fact output key mismatch")
            row_field = schema.fields.get(output_name)
            if row_field is None:
                raise ValueError("Project aggregate result fact requires schema field")
            if row_field.result_role is not ProjectRowResultRole.AGGREGATE_RESULT:
                raise ValueError(
                    "Project aggregate result fact requires aggregate result role"
                )
            if fact.grouped is not (definition.group_by_clause is not None):
                raise ValueError("Project aggregate result fact grouped mismatch")

    for definition, schema in relation_row_schemas.items():
        facts = relation_aggregate_result_facts.get(definition)
        for output_name, row_field in schema.fields.items():
            has_fact = facts is not None and output_name in facts
            if row_field.result_role is ProjectRowResultRole.AGGREGATE_RESULT:
                if not has_fact:
                    raise ValueError(
                        "Project aggregate result role requires matching fact"
                    )
            elif has_fact:
                raise ValueError(
                    "Ordinary and group-key project row fields forbid aggregate facts"
                )


def _validate_project_window_result_facts(
    *,
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_window_result_facts: Mapping[
        TableDef | QueryDef,
        Mapping[str, WindowResultProjectFact],
    ],
) -> None:
    """Validate private window-result facts bidirectionally against schemas."""

    from pietto._project.window_semantics import WindowResultProjectFact

    for definition, facts in relation_window_result_facts.items():
        if type(definition) not in {TableDef, QueryDef}:
            raise ValueError("Project window result facts require relation keys")
        schema = relation_row_schemas.get(definition)
        if schema is None:
            raise ValueError("Project window result facts require relation schema")
        for output_name, fact in facts.items():
            if type(fact) is not WindowResultProjectFact:
                raise ValueError("Project window result facts require fact values")
            if (
                fact.result_identity.definition is not definition
                or fact.result_identity.output_name != output_name
            ):
                raise ValueError("Project window result fact output key mismatch")
            row_field = schema.fields.get(output_name)
            if (
                row_field is None
                or row_field.result_role is not ProjectRowResultRole.WINDOW_RESULT
            ):
                raise ValueError("Project window result fact requires schema field")

    for definition, schema in relation_row_schemas.items():
        facts = relation_window_result_facts.get(definition)
        for output_name, row_field in schema.fields.items():
            has_fact = facts is not None and output_name in facts
            if row_field.result_role is ProjectRowResultRole.WINDOW_RESULT:
                if not has_fact:
                    raise ValueError(
                        "Project window result role requires matching fact"
                    )
            elif has_fact:
                raise ValueError("Non-window project row fields forbid window facts")


@dataclass(frozen=True, slots=True)
class ProjectSemanticResult:
    """Private project-wide semantic scaffold result."""

    root: ProjectRoot | None
    config_path: ProjectConfigPath | None
    model: ProjectSemanticModel | None
    diagnostics: tuple[Diagnostic, ...] = ()
    compilation_mode: ProjectCompilationMode = ProjectCompilationMode.LEGACY_FLAT
    modules: tuple[ProjectLogicalModule, ...] = ()
    pinned_root: ProjectPinnedRoot | None = None
    selected_input_index: ProjectSelectedInputIndex | None = None
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...] = ()
    module_catalogs: ProjectModuleCatalogSet | None = None
    module_exports: ProjectModuleExportSurfaceSet | None = None
    module_bindings: ProjectModuleBindingEnvironmentSet | None = None
    module_graph: ProjectModuleGraph | None = None
    module_diagnostic_facts: ProjectModuleDiagnosticSet | None = None
    module_type_source_resolutions: ProjectTypeSourceResolutionSet | None = None
    module_relation_resolutions: ProjectModuleRelationResolutionSet | None = None
    module_semantic_facts: ProjectModuleSemanticFactSet | None = None
    module_attribution_facts: ProjectModuleAttributionFactSet | None = None
    module_package_identity_facts: ProjectModulePackageNeutralIdentityFactSet | None = (
        None
    )
    module_inspection_facts: ProjectModuleInspectionFactSet | None = None
    nested_relation_facts: ProjectNestedRelationFactSet | None = None

    def __post_init__(self) -> None:
        """Keep every module sidecar on its exact independent authority roots."""

        if type(self.compilation_mode) is not ProjectCompilationMode:
            raise TypeError("Project semantics require an exact compilation mode.")
        module_sidecars = (
            self.module_catalogs,
            self.module_exports,
            self.module_bindings,
            self.module_graph,
            self.module_diagnostic_facts,
            self.module_type_source_resolutions,
            self.module_relation_resolutions,
            self.module_semantic_facts,
            self.module_attribution_facts,
            self.module_package_identity_facts,
            self.module_inspection_facts,
            self.nested_relation_facts,
        )
        if self.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT:
            if (
                self.model is not None
                or self.modules
                or self.selected_input_index is not None
                or self.trusted_source_snapshots
                or any(sidecar is not None for sidecar in module_sidecars)
            ):
                raise ValueError(
                    "Package-root project semantics forbid source and module facts."
                )
            return
        if self.compilation_mode is ProjectCompilationMode.LEGACY_FLAT:
            if any(sidecar is not None for sidecar in module_sidecars):
                raise ValueError(
                    "Legacy-flat project semantics forbid module sidecars."
                )
            return
        if self.model is not None:
            raise ValueError("Explicit-module project semantics forbid a legacy model.")
        if all(sidecar is None for sidecar in module_sidecars):
            return
        if any(sidecar is None for sidecar in module_sidecars):
            raise ValueError(
                "Explicit-module project semantics require all module sidecars."
            )

        facts = self.module_attribution_facts
        assert facts is not None
        from pietto._project.module_attribution import (
            ProjectModuleAttributionFactSet,
        )

        if type(facts) is not ProjectModuleAttributionFactSet:
            raise TypeError(
                "Project module attribution requires an exact attribution fact set."
            )
        if self.compilation_mode is not ProjectCompilationMode.EXPLICIT_MODULES:
            raise ValueError(
                "Project module attribution facts require schema-v2 compilation mode."
            )

        authority = facts._authority
        parse_result = authority.parse_result
        if type(parse_result) is not ProjectParseCheckResult:
            raise TypeError(
                "Project module attribution requires an exact parse result root."
            )
        if (
            not parse_result.ok
            or parse_result.compilation_mode
            is not ProjectCompilationMode.EXPLICIT_MODULES
            or parse_result.root is not self.root
            or parse_result.config_path is not self.config_path
            or parse_result.modules is not self.modules
            or parse_result.pinned_root is not self.pinned_root
            or parse_result.selected_input_index is not self.selected_input_index
            or parse_result.trusted_source_snapshots
            is not self.trusted_source_snapshots
        ):
            raise ValueError(
                "Project module attribution facts require exact parse result roots."
            )
        if authority.selected_input_index is not self.selected_input_index or (
            authority.trusted_source_snapshots is not self.trusted_source_snapshots
        ):
            raise ValueError(
                "Project module attribution facts require exact project input authority."
            )
        if self.selected_input_index is None or (
            self.pinned_root is not self.selected_input_index.pinned_root
        ):
            raise ValueError(
                "Project module attribution facts require exact selected-input pinned root."
            )
        if authority.module_diagnostic_facts is not self.module_diagnostic_facts:
            raise ValueError(
                "Project module attribution facts require exact diagnostic authority."
            )
        module_diagnostic_facts = self.module_diagnostic_facts
        module_type_source_resolutions = self.module_type_source_resolutions
        module_relation_resolutions = self.module_relation_resolutions
        assert module_diagnostic_facts is not None
        assert module_type_source_resolutions is not None
        assert module_relation_resolutions is not None
        if facts.binding_authority is not self.module_bindings or (
            authority.binding_authority is not self.module_bindings
        ):
            raise ValueError(
                "Project module attribution facts require exact project binding authority."
            )
        diagnostic_authority = module_diagnostic_facts._canonical_authority
        if (
            diagnostic_authority.graph is not self.module_graph
            or diagnostic_authority.exports is not self.module_exports
            or diagnostic_authority.binding_authority is not self.module_bindings
        ):
            raise ValueError(
                "Project module diagnostics require exact canonical authority roots."
            )
        if any(
            fact_root is not result_root
            for fact_root, result_root in (
                (authority.modules, self.modules),
                (authority.catalogs, self.module_catalogs),
                (authority.exports, self.module_exports),
                (authority.graph, self.module_graph),
                (
                    authority.type_source_resolutions,
                    self.module_type_source_resolutions,
                ),
                (authority.relation_resolutions, self.module_relation_resolutions),
            )
        ):
            raise ValueError(
                "Project module attribution facts require exact project semantic roots."
            )

        semantic_facts = self.module_semantic_facts
        assert semantic_facts is not None
        from pietto._project.module_semantic_fact_preservation import (
            ProjectModuleSemanticFactSet,
        )

        if type(semantic_facts) is not ProjectModuleSemanticFactSet:
            raise TypeError(
                "Project module semantic facts require an exact preservation set."
            )
        if authority.semantic_facts is not semantic_facts:
            raise ValueError(
                "Project module attribution requires exact semantic-fact authority."
            )
        nested = self.nested_relation_facts
        assert nested is not None
        from pietto._project.nested_relation_facts import (
            ProjectNestedRelationFactSet,
        )

        if type(nested) is not ProjectNestedRelationFactSet:
            raise TypeError("Nested relation facts require an exact fact set.")
        if (
            nested.catalogs is not self.module_catalogs
            or nested.semantic is not semantic_facts
        ):
            raise ValueError("Nested relation facts require exact semantic roots.")
        semantic_authority = semantic_facts.authority
        if (
            semantic_authority.modules is not self.modules
            or semantic_authority.catalogs is not self.module_catalogs
            or semantic_authority.relation_resolutions
            is not self.module_relation_resolutions
        ):
            raise ValueError(
                "Project module semantic facts require exact Slice 10 roots."
            )
        if (
            semantic_facts.dependency_order
            is not module_relation_resolutions.dependency_order
            or semantic_facts.issues is not module_relation_resolutions.issues
            or len(semantic_facts.environments)
            != len(module_relation_resolutions.environments)
            or any(
                semantic_environment.resolution_environment is not relation_environment
                for semantic_environment, relation_environment in zip(
                    semantic_facts.environments,
                    module_relation_resolutions.environments,
                    strict=True,
                )
            )
        ):
            raise ValueError(
                "Project module semantic facts require exact ordered Slice 10 facts."
            )

        package_identity_facts = self.module_package_identity_facts
        assert package_identity_facts is not None
        from pietto._project.module_package_neutral_identity import (
            ProjectModulePackageNeutralIdentityFactSet,
        )

        if (
            type(package_identity_facts)
            is not ProjectModulePackageNeutralIdentityFactSet
        ):
            raise TypeError(
                "Project module package identity requires an exact layered fact set."
            )
        layered_authority = package_identity_facts.authority
        if (
            layered_authority.attribution is not facts
            or layered_authority.semantic is not semantic_facts
        ):
            # The layered authority itself anchors the selected-input index,
            # trusted snapshots, modules, and catalogs to those two sidecars,
            # which this result has already bound to its own exact roots.
            raise ValueError(
                "Project module package identity requires both exact sidecar roots."
            )

        inspection_facts = self.module_inspection_facts
        assert inspection_facts is not None
        from pietto._project.module_inspection import ProjectModuleInspectionFactSet

        if type(inspection_facts) is not ProjectModuleInspectionFactSet:
            raise TypeError(
                "Project module inspection requires an exact inspection fact set."
            )
        inspection_authority = inspection_facts.authority
        if any(
            fact_root is not result_root
            for fact_root, result_root in (
                (inspection_authority.modules, self.modules),
                (inspection_authority.catalogs, self.module_catalogs),
                (inspection_authority.exports, self.module_exports),
                (inspection_authority.bindings, self.module_bindings),
                (inspection_authority.graph, self.module_graph),
                (
                    inspection_authority.type_source_resolutions,
                    self.module_type_source_resolutions,
                ),
                (
                    inspection_authority.relation_resolutions,
                    self.module_relation_resolutions,
                ),
                (inspection_authority.attribution, facts),
                (inspection_authority.semantic, semantic_facts),
                (inspection_authority.package_identity, package_identity_facts),
            )
        ):
            raise ValueError(
                "Project module inspection requires the exact ten sidecar roots."
            )

        expected_diagnostics = (
            *module_diagnostic_facts.diagnostics,
            *module_type_source_resolutions.diagnostics,
            *module_relation_resolutions.diagnostics,
            *nested.diagnostics,
        )
        if len(self.diagnostics) != len(expected_diagnostics) or any(
            diagnostic is not expected
            for diagnostic, expected in zip(
                self.diagnostics,
                expected_diagnostics,
                strict=True,
            )
        ):
            raise ValueError(
                "Project module diagnostics require exact ordered root projection."
            )

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

    if type(parse_result) is not ProjectParseCheckResult:
        raise TypeError("Project semantics require an exact parse result carrier.")
    if type(parse_result.compilation_mode) is not ProjectCompilationMode:
        raise TypeError("Project semantics require an exact compilation mode.")
    if parse_result.compilation_mode not in (
        ProjectCompilationMode.PACKAGE_ROOT,
        ProjectCompilationMode.EXPLICIT_MODULES,
        ProjectCompilationMode.LEGACY_FLAT,
    ):
        raise ValueError("Project semantics require a supported compilation mode.")

    if parse_result.compilation_mode is ProjectCompilationMode.PACKAGE_ROOT:
        if (
            parse_result.inputs
            or parse_result.parsed_inputs
            or parse_result.modules
            or parse_result.selected_input_index is not None
            or parse_result.trusted_source_snapshots
        ):
            raise ValueError(
                "Package-root project semantics forbid source and module facts."
            )
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
            diagnostics=(),
            compilation_mode=parse_result.compilation_mode,
            modules=(),
            pinned_root=parse_result.pinned_root,
            selected_input_index=None,
            trusted_source_snapshots=(),
        )

    if (
        not parse_result.ok
        or parse_result.root is None
        or parse_result.config_path is None
    ):
        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
            compilation_mode=parse_result.compilation_mode,
            modules=parse_result.modules,
            pinned_root=parse_result.pinned_root,
            selected_input_index=parse_result.selected_input_index,
            trusted_source_snapshots=parse_result.trusted_source_snapshots,
        )

    if parse_result.compilation_mode is ProjectCompilationMode.EXPLICIT_MODULES:
        from pietto._project.module_attribution import (
            _build_project_module_attribution_fact_set,
        )
        from pietto._project.module_bindings import (
            _build_project_module_binding_environment_set,
        )
        from pietto._project.module_catalog import _build_project_module_catalog_set
        from pietto._project.module_exports import (
            _build_project_module_export_surface_set,
        )
        from pietto._project.module_graph import (
            _build_project_module_diagnostic_set,
            _build_project_module_graph,
        )
        from pietto._project.module_inspection import (
            _build_project_module_inspection_fact_set,
        )
        from pietto._project.module_package_neutral_identity import (
            _build_project_module_package_neutral_identity_fact_set,
        )
        from pietto._project.module_relation_resolution import (
            _build_project_module_relation_resolution_set,
        )
        from pietto._project.module_resolution import (
            _build_project_type_source_resolution_set,
        )
        from pietto._project.module_semantic_fact_preservation import (
            _build_project_module_semantic_fact_set,
        )
        from pietto._project.nested_relation_facts import (
            build_project_nested_relation_facts,
        )

        module_catalogs = _build_project_module_catalog_set(parse_result.modules)
        assert parse_result.selected_input_index is not None
        module_bindings = _build_project_module_binding_environment_set(
            parse_result.selected_input_index,
            parse_result.modules,
            module_catalogs,
        )
        module_exports = _build_project_module_export_surface_set(
            module_catalogs,
            imported_binding_candidates=module_bindings.imported_export_candidates,
        )
        module_graph = _build_project_module_graph(
            parse_result.selected_input_index,
            parse_result.modules,
            module_bindings,
        )
        module_diagnostic_facts = _build_project_module_diagnostic_set(
            module_graph,
            module_exports,
            module_bindings,
        )
        module_type_source_resolutions = _build_project_type_source_resolution_set(
            parse_result.modules,
            module_catalogs,
            module_exports,
            module_bindings,
            module_graph,
            module_diagnostic_facts,
        )
        module_relation_resolutions = _build_project_module_relation_resolution_set(
            parse_result.modules,
            module_catalogs,
            module_exports,
            module_bindings,
            module_graph,
            module_diagnostic_facts,
            module_type_source_resolutions,
        )
        module_semantic_facts = _build_project_module_semantic_fact_set(
            parse_result.modules,
            module_catalogs,
            module_relation_resolutions,
        )
        module_attribution_facts = _build_project_module_attribution_fact_set(
            parse_result,
            parse_result.modules,
            parse_result.selected_input_index,
            parse_result.trusted_source_snapshots,
            module_catalogs,
            module_exports,
            module_bindings,
            module_graph,
            module_diagnostic_facts,
            module_type_source_resolutions,
            module_relation_resolutions,
            module_semantic_facts,
        )
        module_package_identity_facts = (
            _build_project_module_package_neutral_identity_fact_set(
                parse_result.selected_input_index,
                parse_result.trusted_source_snapshots,
                parse_result.modules,
                module_catalogs,
                module_attribution_facts,
                module_semantic_facts,
            )
        )
        module_inspection_facts = _build_project_module_inspection_fact_set(
            parse_result.modules,
            module_catalogs,
            module_exports,
            module_bindings,
            module_graph,
            module_type_source_resolutions,
            module_relation_resolutions,
            module_attribution_facts,
            module_semantic_facts,
            module_package_identity_facts,
        )
        nested_relation_facts = build_project_nested_relation_facts(
            catalogs=module_catalogs, semantic=module_semantic_facts
        )

        return ProjectSemanticResult(
            root=parse_result.root,
            config_path=parse_result.config_path,
            model=None,
            compilation_mode=parse_result.compilation_mode,
            modules=parse_result.modules,
            pinned_root=parse_result.pinned_root,
            selected_input_index=parse_result.selected_input_index,
            trusted_source_snapshots=parse_result.trusted_source_snapshots,
            module_catalogs=module_catalogs,
            module_exports=module_exports,
            module_bindings=module_bindings,
            module_graph=module_graph,
            module_diagnostic_facts=module_diagnostic_facts,
            module_type_source_resolutions=module_type_source_resolutions,
            module_relation_resolutions=module_relation_resolutions,
            module_semantic_facts=module_semantic_facts,
            module_attribution_facts=module_attribution_facts,
            module_package_identity_facts=module_package_identity_facts,
            module_inspection_facts=module_inspection_facts,
            nested_relation_facts=nested_relation_facts,
            # The nested-relation producer follows the relation resolution it
            # reads: project stage, then producer, then module order.
            diagnostics=(
                *module_diagnostic_facts.diagnostics,
                *module_type_source_resolutions.diagnostics,
                *module_relation_resolutions.diagnostics,
                *nested_relation_facts.diagnostics,
            ),
        )

    catalog, catalog_diagnostics = _build_project_semantic_catalog(
        parse_result.parsed_inputs
    )
    relation_dependency_graph = _build_project_relation_dependency_graph(
        parsed_inputs=parse_result.parsed_inputs,
        catalog=catalog,
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
                relation_dependency_graph=relation_dependency_graph,
            ),
            diagnostics=(
                *catalog_diagnostics,
                *(
                    diagnostic
                    for parsed in parse_result.parsed_inputs
                    for diagnostic in legacy_flat_refusals(
                        parsed.authored_script or parsed.script
                    )
                ),
            ),
            compilation_mode=parse_result.compilation_mode,
            modules=parse_result.modules,
            pinned_root=parse_result.pinned_root,
            selected_input_index=parse_result.selected_input_index,
            trusted_source_snapshots=parse_result.trusted_source_snapshots,
        )

    type_resolutions, source_shape_resolutions, type_diagnostics = (
        _build_project_type_namespace_facts(
            parsed_inputs=parse_result.parsed_inputs,
            catalog=catalog,
        )
    )
    source_row_schemas = _build_project_source_row_schemas(
        source_shape_resolutions=source_shape_resolutions,
        type_resolutions=type_resolutions,
    )
    relation_resolutions, relation_diagnostics = (
        _build_project_relation_namespace_facts(
            parsed_inputs=parse_result.parsed_inputs,
            catalog=catalog,
        )
    )
    relation_dependency_graph = _build_project_relation_dependency_graph(
        parsed_inputs=parse_result.parsed_inputs,
        catalog=catalog,
        relation_resolutions=relation_resolutions,
    )
    relation_row_schema_result = _build_project_relation_row_schemas(
        parsed_inputs=parse_result.parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_dependency_graph=relation_dependency_graph,
    )
    cycle_diagnostics = _build_project_relation_cycle_diagnostics(
        relation_dependency_graph
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
            source_row_schemas=source_row_schemas,
            relation_resolutions=relation_resolutions,
            relation_row_schemas=relation_row_schema_result.relation_row_schemas,
            relation_row_schema_states=(
                relation_row_schema_result.relation_row_schema_states
            ),
            relation_let_scope_facts=(
                relation_row_schema_result.relation_let_scope_facts
            ),
            relation_row_dependency_graphs=(
                relation_row_schema_result.relation_row_dependency_graphs
            ),
            relation_row_lineages=relation_row_schema_result.relation_row_lineages,
            relation_dependency_graph=relation_dependency_graph,
            relation_aggregate_result_facts=(
                relation_row_schema_result.relation_aggregate_result_facts
            ),
            relation_window_result_facts=(
                relation_row_schema_result.relation_window_result_facts
            ),
        ),
        diagnostics=(
            *type_diagnostics,
            *relation_diagnostics,
            *relation_row_schema_result.diagnostics,
            *cycle_diagnostics,
            *(
                diagnostic
                for parsed in parse_result.parsed_inputs
                for diagnostic in _legacy_flat_syntax_diagnostics(
                    parsed.authored_script or parsed.script
                )
            ),
        ),
        compilation_mode=parse_result.compilation_mode,
        modules=parse_result.modules,
        pinned_root=parse_result.pinned_root,
        selected_input_index=parse_result.selected_input_index,
        trusted_source_snapshots=parse_result.trusted_source_snapshots,
    )


def _legacy_flat_syntax_diagnostics(script: Script) -> list[Diagnostic]:
    """The syntax availability diagnostics of a LEGACY_FLAT project's script
    and its PIE-S2334 of each JOIN and any(...), in source order."""

    return sorted(
        (
            *(
                diagnostic
                for definition in script.definitions
                for diagnostic in syntax_diagnostics(definition, allow_joins=True)
            ),
            *legacy_flat_refusals(script),
        ),
        key=source_order,
    )


def _build_project_relation_dependency_graph(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
    relation_resolutions: Mapping[FromClause, ProjectSymbol] | None = None,
) -> ProjectRelationDependencyGraph:
    """Build the private relation dependency graph."""

    nodes = tuple(
        ProjectRelationDependencyNode(symbol=symbol)
        for symbol in catalog.relation_symbols.values()
        if symbol.kind in (ProjectSymbolKind.TABLE, ProjectSymbolKind.QUERY)
    )
    node_by_name = {node.symbol.name: node for node in nodes}
    resolutions = relation_resolutions or {}
    edges: list[ProjectRelationDependencyEdge] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            origin = node_by_name.get(definition.name)
            if origin is None:
                continue

            target_symbol = resolutions.get(definition.from_clause)
            if target_symbol is None or target_symbol.kind not in (
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            ):
                continue

            target = node_by_name.get(target_symbol.name)
            if target is None:
                continue

            edges.append(
                ProjectRelationDependencyEdge(
                    origin=origin,
                    target=target,
                    dependency_source=ProjectRelationDependencySource(
                        from_clause=definition.from_clause
                    ),
                )
            )

    graph_edges = tuple(edges)
    cycles = _detect_project_relation_dependency_cycles(
        nodes=nodes,
        edges=graph_edges,
    )
    return ProjectRelationDependencyGraph(nodes=nodes, edges=graph_edges, cycles=cycles)


def _detect_project_relation_dependency_cycles(
    *,
    nodes: tuple[ProjectRelationDependencyNode, ...],
    edges: tuple[ProjectRelationDependencyEdge, ...],
) -> tuple[ProjectRelationDependencyCycle, ...]:
    """Detect private relation dependency cycles without emitting diagnostics."""

    if not nodes or not edges:
        return ()

    node_order = {node.symbol.name: index for index, node in enumerate(nodes)}
    edges_by_origin: dict[str, list[ProjectRelationDependencyEdge]] = {
        node.symbol.name: [] for node in nodes
    }
    for edge in edges:
        origin_name = edge.origin.symbol.name
        target_name = edge.target.symbol.name
        if origin_name not in node_order or target_name not in node_order:
            continue
        edges_by_origin[origin_name].append(edge)

    for origin_edges in edges_by_origin.values():
        origin_edges.sort(key=lambda edge: node_order[edge.target.symbol.name])

    state: dict[str, int] = {}
    stack_nodes: list[ProjectRelationDependencyNode] = []
    stack_edges: list[ProjectRelationDependencyEdge] = []
    stack_indexes: dict[str, int] = {}
    cycles_by_members: dict[tuple[int, ...], ProjectRelationDependencyCycle] = {}

    def visit(node: ProjectRelationDependencyNode) -> None:
        node_name = node.symbol.name
        state[node_name] = 1
        stack_indexes[node_name] = len(stack_nodes)
        stack_nodes.append(node)

        for edge in edges_by_origin[node_name]:
            target_name = edge.target.symbol.name
            target_state = state.get(target_name, 0)
            if target_state == 0:
                stack_edges.append(edge)
                visit(edge.target)
                stack_edges.pop()
            elif target_state == 1:
                cycle_start = stack_indexes[target_name]
                cycle = _canonical_project_relation_dependency_cycle(
                    nodes=tuple(stack_nodes[cycle_start:]),
                    edges=tuple((*stack_edges[cycle_start:], edge)),
                    node_order=node_order,
                )
                cycle_key = tuple(
                    sorted(
                        node_order[cycle_node.symbol.name] for cycle_node in cycle.nodes
                    )
                )
                cycles_by_members.setdefault(cycle_key, cycle)

        stack_nodes.pop()
        stack_indexes.pop(node_name)
        state[node_name] = 2

    for node in nodes:
        if state.get(node.symbol.name, 0) == 0:
            visit(node)

    return tuple(
        sorted(
            cycles_by_members.values(),
            key=lambda cycle: tuple(
                node_order[cycle_node.symbol.name] for cycle_node in cycle.nodes
            ),
        )
    )


def _canonical_project_relation_dependency_cycle(
    *,
    nodes: tuple[ProjectRelationDependencyNode, ...],
    edges: tuple[ProjectRelationDependencyEdge, ...],
    node_order: Mapping[str, int],
) -> ProjectRelationDependencyCycle:
    """Rotate one cycle to its lowest graph-node-order participant."""

    if not nodes:
        raise AssertionError("Relation dependency cycle requires at least one node")
    start = min(
        range(len(nodes)),
        key=lambda index: node_order[nodes[index].symbol.name],
    )
    return ProjectRelationDependencyCycle(
        nodes=(*nodes[start:], *nodes[:start]),
        edges=(*edges[start:], *edges[:start]),
    )


def _build_project_relation_cycle_diagnostics(
    graph: ProjectRelationDependencyGraph,
) -> tuple[Diagnostic, ...]:
    """Build project relation cycle diagnostics from private cycle facts."""

    return tuple(_project_relation_cycle_diagnostic(cycle) for cycle in graph.cycles)


def _project_relation_cycle_diagnostic(
    cycle: ProjectRelationDependencyCycle,
) -> Diagnostic:
    """Build one project relation cycle diagnostic."""

    if not cycle.edges:
        raise AssertionError("Relation dependency cycle requires at least one edge")

    closing_edge = cycle.edges[-1]
    span = closing_edge.dependency_source.from_clause.span
    return Diagnostic(
        code="PIE-S2302",
        severity=Severity.ERROR,
        message=f"Relation cycle detected: {_project_relation_cycle_path(cycle)}",
        location=SourceLocation(
            path=span.path or closing_edge.origin.symbol.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_relation_cycle_path(
    cycle: ProjectRelationDependencyCycle,
) -> str:
    """Return the user-facing relation cycle path."""

    if not cycle.nodes:
        raise AssertionError("Relation dependency cycle requires at least one node")

    node_names = tuple(node.symbol.name for node in cycle.nodes)
    return " -> ".join((*node_names, node_names[0]))


def _build_project_relation_namespace_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    catalog: ProjectSemanticCatalog,
) -> tuple[dict[FromClause, ProjectSymbol], tuple[Diagnostic, ...]]:
    """Resolve top-level project relation namespace references."""

    relation_resolutions: dict[FromClause, ProjectSymbol] = {}
    diagnostics: list[Diagnostic] = []

    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            from_clause = definition.from_clause
            symbol = catalog.relation_symbols.get(from_clause.source_name)
            if symbol is None:
                diagnostics.append(_unknown_project_relation_diagnostic(from_clause))
                continue
            if type(symbol.definition) is SetRelationDef:
                # As in a single file: a set operation, refused itself, is no
                # input either.
                diagnostics.append(
                    availability_diagnostic(
                        from_clause.span,
                        "Set-operation inputs are available only when "
                        f"{_EXPLICIT_MODULES} completes them: {symbol.name}",
                    )
                )
                continue
            relation_resolutions[from_clause] = symbol

    return relation_resolutions, tuple(diagnostics)


def _build_project_relation_row_schemas(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_dependency_graph: ProjectRelationDependencyGraph,
) -> _ProjectRelationRowSchemasResult:
    """Build complete private row bundles in one dependency-first fixpoint."""

    from pietto._project.aggregate_grouped_persistence import (
        _is_project_aggregate_grouped_definition,
        build_project_aggregate_grouped_persistence,
    )
    from pietto._project.let_scope_facts import (
        build_project_relation_let_scope_facts,
    )
    from pietto._project.row_dependency_graph import (
        build_project_relation_row_dependency_graph,
    )
    from pietto._project.row_lineage import build_project_relation_row_lineage
    from pietto._project.window_persistence import (
        build_project_window_persistence,
    )

    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema] = {}
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ] = {}
    relation_let_scope_facts: dict[
        TableDef | QueryDef, ProjectRelationLetScopeFacts
    ] = {}
    relation_aggregate_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, ProjectAggregateResultFact],
    ] = {}
    relation_window_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, WindowResultProjectFact],
    ] = {}
    relation_row_dependency_graphs: dict[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ] = {}
    relation_row_lineages: dict[TableDef | QueryDef, ProjectRelationRowLineage] = {}
    diagnostics: list[Diagnostic] = []
    completed: set[TableDef | QueryDef] = set()

    relation_definitions = tuple(
        definition
        for parsed_input in parsed_inputs
        for definition in parsed_input.script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    )
    definition_paths = {
        definition: parsed_input.path
        for parsed_input in parsed_inputs
        for definition in parsed_input.script.definitions
        if isinstance(definition, (TableDef, QueryDef))
    }
    cycle_relation_names = {
        node.symbol.name
        for cycle in relation_dependency_graph.cycles
        for node in cycle.nodes
    }

    for definition in relation_definitions:
        if definition.name in cycle_relation_names:
            reason = ProjectRelationRowSchemaReason.CYCLE_BLOCKED
        elif definition.from_clause not in relation_resolutions:
            reason = ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED
        else:
            continue

        state = ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=reason,
        )
        upstream_symbol = relation_resolutions.get(definition.from_clause)
        upstream_definition = (
            upstream_symbol.definition if upstream_symbol is not None else None
        )
        if not isinstance(upstream_definition, (SourceDef, TableDef, QueryDef)):
            upstream_definition = None
        let_scope_facts = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=None,
            upstream_definition=upstream_definition,
            upstream_state=state,
        )
        dependency_graph = build_project_relation_row_dependency_graph(
            definition=definition,
            fallback_path=definition_paths[definition],
            upstream_symbol=upstream_symbol,
            input_schema=None,
            output_schema=None,
            state=state,
            let_scope_facts=let_scope_facts,
        )
        lineage = build_project_relation_row_lineage(
            definition=definition,
            upstream_symbol=upstream_symbol,
            row_schema=None,
            state=state,
            dependency_graph=dependency_graph,
            upstream_lineage=None,
        )
        _record_project_relation_terminal_bundle(
            relation_row_schemas=relation_row_schemas,
            relation_row_schema_states=relation_row_schema_states,
            relation_let_scope_facts=relation_let_scope_facts,
            relation_aggregate_result_facts=relation_aggregate_result_facts,
            relation_window_result_facts=relation_window_result_facts,
            relation_row_dependency_graphs=relation_row_dependency_graphs,
            relation_row_lineages=relation_row_lineages,
            definition=definition,
            state=state,
            let_scope_facts=let_scope_facts,
            aggregate_result_facts={},
            window_result_facts={},
            dependency_graph=dependency_graph,
            lineage=lineage,
        )
        completed.add(definition)

    source_round = True
    while True:
        propagated = False
        for definition in relation_definitions:
            if definition in completed:
                continue

            upstream_symbol = relation_resolutions.get(definition.from_clause)
            if upstream_symbol is None:
                continue
            upstream_definition = upstream_symbol.definition
            input_schema: ProjectRowSchema | None
            upstream_state: ProjectRelationRowSchemaState | None = None
            upstream_lineage: ProjectRelationRowLineage | None = None
            if upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
                upstream_definition,
                SourceDef,
            ):
                if not source_round:
                    continue
                input_schema = source_row_schemas.get(upstream_definition)
                if input_schema is None:
                    state = ProjectRelationRowSchemaState(
                        status=ProjectRelationRowSchemaStatus.UNKNOWN,
                        schema=ProjectRowSchema(is_unknown=True),
                        reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
                    )
                    let_scope_facts = build_project_relation_let_scope_facts(
                        definition=definition,
                        input_schema=None,
                        upstream_definition=upstream_definition,
                        upstream_state=state,
                    )
                    dependency_graph = build_project_relation_row_dependency_graph(
                        definition=definition,
                        fallback_path=definition_paths[definition],
                        upstream_symbol=upstream_symbol,
                        input_schema=None,
                        output_schema=state.schema,
                        state=state,
                        let_scope_facts=let_scope_facts,
                    )
                    lineage = build_project_relation_row_lineage(
                        definition=definition,
                        upstream_symbol=upstream_symbol,
                        row_schema=state.schema,
                        state=state,
                        dependency_graph=dependency_graph,
                        upstream_lineage=None,
                    )
                    _record_project_relation_terminal_bundle(
                        relation_row_schemas=relation_row_schemas,
                        relation_row_schema_states=relation_row_schema_states,
                        relation_let_scope_facts=relation_let_scope_facts,
                        relation_aggregate_result_facts=(
                            relation_aggregate_result_facts
                        ),
                        relation_window_result_facts=(relation_window_result_facts),
                        relation_row_dependency_graphs=(relation_row_dependency_graphs),
                        relation_row_lineages=relation_row_lineages,
                        definition=definition,
                        state=state,
                        let_scope_facts=let_scope_facts,
                        aggregate_result_facts={},
                        window_result_facts={},
                        dependency_graph=dependency_graph,
                        lineage=lineage,
                    )
                    completed.add(definition)
                    propagated = True
                    continue
            elif upstream_symbol.kind in {
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            } and isinstance(upstream_definition, (TableDef, QueryDef)):
                if source_round:
                    continue
                if upstream_definition not in completed:
                    continue
                upstream_state = relation_row_schema_states.get(upstream_definition)
                upstream_graph = relation_row_dependency_graphs.get(upstream_definition)
                upstream_lineage = relation_row_lineages.get(upstream_definition)
                if (
                    upstream_state is None
                    or upstream_graph is None
                    or upstream_lineage is None
                    or upstream_graph.status.value != upstream_state.status.value
                    or upstream_graph.reason.value != upstream_state.reason.value
                    or upstream_lineage.status.value != upstream_state.status.value
                    or upstream_lineage.reason.value != upstream_state.reason.value
                ):
                    raise AssertionError(
                        "Completed relation requires one coherent terminal bundle"
                    )
                if upstream_state.status is not ProjectRelationRowSchemaStatus.CONCRETE:
                    state = _project_upstream_non_concrete_state(upstream_state)
                    let_scope_facts = build_project_relation_let_scope_facts(
                        definition=definition,
                        input_schema=upstream_state.schema,
                        upstream_definition=upstream_definition,
                        upstream_state=upstream_state,
                    )
                    dependency_graph = build_project_relation_row_dependency_graph(
                        definition=definition,
                        fallback_path=definition_paths[definition],
                        upstream_symbol=upstream_symbol,
                        input_schema=upstream_state.schema,
                        output_schema=state.schema,
                        state=state,
                        let_scope_facts=let_scope_facts,
                    )
                    lineage = build_project_relation_row_lineage(
                        definition=definition,
                        upstream_symbol=upstream_symbol,
                        row_schema=state.schema,
                        state=state,
                        dependency_graph=dependency_graph,
                        upstream_lineage=None,
                    )
                    _record_project_relation_terminal_bundle(
                        relation_row_schemas=relation_row_schemas,
                        relation_row_schema_states=relation_row_schema_states,
                        relation_let_scope_facts=relation_let_scope_facts,
                        relation_aggregate_result_facts=(
                            relation_aggregate_result_facts
                        ),
                        relation_window_result_facts=(relation_window_result_facts),
                        relation_row_dependency_graphs=(relation_row_dependency_graphs),
                        relation_row_lineages=relation_row_lineages,
                        definition=definition,
                        state=state,
                        let_scope_facts=let_scope_facts,
                        aggregate_result_facts={},
                        window_result_facts={},
                        dependency_graph=dependency_graph,
                        lineage=lineage,
                    )
                    completed.add(definition)
                    propagated = True
                    continue

                input_schema = relation_row_schemas.get(upstream_definition)
                if (
                    input_schema is None
                    or input_schema.is_unknown
                    or upstream_graph.status.value != "concrete"
                    or upstream_lineage.status.value != "concrete"
                ):
                    raise AssertionError(
                        "Concrete upstream requires schema, graph, and lineage"
                    )
            else:
                continue

            if definition.join_clauses:
                state = ProjectRelationRowSchemaState(
                    status=ProjectRelationRowSchemaStatus.DEFERRED,
                    schema=None,
                    reason=ProjectRelationRowSchemaReason.AUTHORED_JOIN_DEFERRED,
                )
                let_scope_facts = build_project_relation_let_scope_facts(
                    definition=definition,
                    input_schema=None,
                    upstream_definition=upstream_definition,
                    upstream_state=state,
                )
                dependency_graph = build_project_relation_row_dependency_graph(
                    definition=definition,
                    fallback_path=definition_paths[definition],
                    upstream_symbol=upstream_symbol,
                    input_schema=None,
                    output_schema=None,
                    state=state,
                    let_scope_facts=let_scope_facts,
                )
                lineage = build_project_relation_row_lineage(
                    definition=definition,
                    upstream_symbol=upstream_symbol,
                    row_schema=None,
                    state=state,
                    dependency_graph=dependency_graph,
                    upstream_lineage=None,
                )
                _record_project_relation_terminal_bundle(
                    relation_row_schemas=relation_row_schemas,
                    relation_row_schema_states=relation_row_schema_states,
                    relation_let_scope_facts=relation_let_scope_facts,
                    relation_aggregate_result_facts=relation_aggregate_result_facts,
                    relation_window_result_facts=relation_window_result_facts,
                    relation_row_dependency_graphs=relation_row_dependency_graphs,
                    relation_row_lineages=relation_row_lineages,
                    definition=definition,
                    state=state,
                    let_scope_facts=let_scope_facts,
                    aggregate_result_facts={},
                    window_result_facts={},
                    dependency_graph=dependency_graph,
                    lineage=lineage,
                )
                completed.add(definition)
                propagated = True
                continue

            if _is_project_aggregate_grouped_definition(definition):
                persistence = build_project_aggregate_grouped_persistence(
                    definition=definition,
                    input_schema=input_schema,
                    upstream_symbol=upstream_symbol,
                    upstream_lineage=upstream_lineage,
                    fallback_path=definition_paths[definition],
                )
                state = persistence.state
                let_scope_facts = persistence.let_scope_facts
                aggregate_result_facts = persistence.aggregate_result_facts
                dependency_graph = (
                    persistence.dependency_lineage_readiness.dependency_graph
                )
                lineage = persistence.dependency_lineage_readiness.lineage
            else:
                let_scope_facts = build_project_relation_let_scope_facts(
                    definition=definition,
                    input_schema=input_schema,
                    upstream_definition=upstream_definition,
                    upstream_state=upstream_state,
                )
                relation_schema_result = _project_direct_relation_row_schema(
                    definition,
                    source_schema=input_schema,
                    source_symbol=upstream_symbol,
                    upstream_definition=upstream_definition,
                    upstream_state=upstream_state,
                    fallback_path=definition_paths[definition],
                    let_scope_facts=let_scope_facts,
                    report_untyped_let_reads=True,
                )
                diagnostics.extend(relation_schema_result.diagnostics)
                state = _project_relation_row_schema_state_from_result(
                    relation_schema_result,
                    concrete_reason=(
                        ProjectRelationRowSchemaReason.DIRECT_SOURCE_CONCRETE
                        if isinstance(upstream_definition, SourceDef)
                        else ProjectRelationRowSchemaReason.RELATION_UPSTREAM_CONCRETE
                    ),
                )
                aggregate_result_facts = {}
                dependency_graph = build_project_relation_row_dependency_graph(
                    definition=definition,
                    fallback_path=definition_paths[definition],
                    upstream_symbol=upstream_symbol,
                    input_schema=input_schema,
                    output_schema=state.schema,
                    state=state,
                    let_scope_facts=let_scope_facts,
                )
                lineage = build_project_relation_row_lineage(
                    definition=definition,
                    upstream_symbol=upstream_symbol,
                    row_schema=state.schema,
                    state=state,
                    dependency_graph=dependency_graph,
                    upstream_lineage=upstream_lineage,
                )

            window_result_facts: Mapping[str, WindowResultProjectFact] = {}
            if any(
                type(item.expression) is WindowExpr for item in definition.select_items
            ):
                window_persistence = build_project_window_persistence(
                    definition=definition,
                    input_schema=input_schema,
                    upstream_symbol=upstream_symbol,
                    upstream_lineage=upstream_lineage,
                    fallback_path=definition_paths[definition],
                    let_scope_facts=let_scope_facts,
                    base_state=state,
                    base_aggregate_result_facts=aggregate_result_facts,
                    base_dependency_graph=dependency_graph,
                    base_lineage=lineage,
                )
                state = window_persistence.state
                aggregate_result_facts = window_persistence.aggregate_result_facts
                window_result_facts = window_persistence.window_result_facts
                dependency_graph = window_persistence.dependency_graph
                lineage = window_persistence.lineage

            _record_project_relation_terminal_bundle(
                relation_row_schemas=relation_row_schemas,
                relation_row_schema_states=relation_row_schema_states,
                relation_let_scope_facts=relation_let_scope_facts,
                relation_aggregate_result_facts=relation_aggregate_result_facts,
                relation_window_result_facts=relation_window_result_facts,
                relation_row_dependency_graphs=relation_row_dependency_graphs,
                relation_row_lineages=relation_row_lineages,
                definition=definition,
                state=state,
                let_scope_facts=let_scope_facts,
                aggregate_result_facts=aggregate_result_facts,
                window_result_facts=window_result_facts,
                dependency_graph=dependency_graph,
                lineage=lineage,
            )
            completed.add(definition)
            propagated = True
        if source_round:
            source_round = False
            continue
        if not propagated:
            break

    if len(completed) != len(relation_definitions):
        raise AssertionError("Every project relation requires one terminal bundle")

    return _ProjectRelationRowSchemasResult(
        relation_row_schemas=relation_row_schemas,
        relation_row_schema_states=relation_row_schema_states,
        relation_let_scope_facts={
            definition: relation_let_scope_facts[definition]
            for definition in relation_definitions
        },
        relation_aggregate_result_facts={
            definition: relation_aggregate_result_facts[definition]
            for definition in relation_definitions
            if definition in relation_aggregate_result_facts
        },
        relation_window_result_facts={
            definition: relation_window_result_facts[definition]
            for definition in relation_definitions
            if definition in relation_window_result_facts
        },
        relation_row_dependency_graphs={
            definition: relation_row_dependency_graphs[definition]
            for definition in relation_definitions
        },
        relation_row_lineages={
            definition: relation_row_lineages[definition]
            for definition in relation_definitions
        },
        diagnostics=tuple(diagnostics),
    )


def _project_upstream_non_concrete_state(
    upstream_state: ProjectRelationRowSchemaState,
) -> ProjectRelationRowSchemaState:
    """Map one completed non-concrete upstream to the local terminal state."""

    if upstream_state.status is ProjectRelationRowSchemaStatus.UNKNOWN:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=ProjectRowSchema(is_unknown=True),
            reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.DEFERRED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_DEFERRED,
        )
    if upstream_state.status is ProjectRelationRowSchemaStatus.BLOCKED:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.BLOCKED,
            schema=None,
            reason=ProjectRelationRowSchemaReason.UPSTREAM_BLOCKED,
        )
    raise ValueError("Concrete upstream cannot use non-concrete propagation")


def _project_relation_row_schema_state_from_result(
    result: _ProjectRelationRowSchemaResult,
    *,
    concrete_reason: ProjectRelationRowSchemaReason,
) -> ProjectRelationRowSchemaState:
    """Normalize one ordinary projector result without publishing it."""

    schema = result.schema
    if schema is None:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=(
                result.state_reason
                or ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
            ),
        )
    if schema.is_unknown:
        return ProjectRelationRowSchemaState(
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=schema,
            reason=result.state_reason or ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )
    return ProjectRelationRowSchemaState(
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=schema,
        reason=concrete_reason,
    )


def _record_project_relation_terminal_bundle(
    *,
    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    relation_let_scope_facts: dict[TableDef | QueryDef, ProjectRelationLetScopeFacts],
    relation_aggregate_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, ProjectAggregateResultFact],
    ],
    relation_window_result_facts: dict[
        TableDef | QueryDef,
        Mapping[str, WindowResultProjectFact],
    ],
    relation_row_dependency_graphs: dict[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ],
    relation_row_lineages: dict[TableDef | QueryDef, ProjectRelationRowLineage],
    definition: TableDef | QueryDef,
    state: ProjectRelationRowSchemaState,
    let_scope_facts: ProjectRelationLetScopeFacts,
    aggregate_result_facts: Mapping[str, ProjectAggregateResultFact],
    window_result_facts: Mapping[str, WindowResultProjectFact],
    dependency_graph: ProjectRelationRowDependencyGraph,
    lineage: ProjectRelationRowLineage,
) -> None:
    """Validate one complete local bundle, then publish every aligned map."""

    from pietto._project.let_scope_facts import ProjectRelationLetScopeFacts
    from pietto._project.row_dependency_graph import (
        ProjectRelationRowDependencyGraph,
    )
    from pietto._project.row_lineage import ProjectRelationRowLineage

    if not isinstance(let_scope_facts, ProjectRelationLetScopeFacts):
        raise ValueError("Terminal bundle requires let facts")
    if not isinstance(dependency_graph, ProjectRelationRowDependencyGraph):
        raise ValueError("Terminal bundle requires dependency graph")
    if not isinstance(lineage, ProjectRelationRowLineage):
        raise ValueError("Terminal bundle requires lineage")
    if (
        dependency_graph.status.value != state.status.value
        or dependency_graph.reason.value != state.reason.value
        or lineage.status.value != state.status.value
        or lineage.reason.value != state.reason.value
    ):
        raise ValueError("Terminal bundle state, graph, and lineage must agree")

    if state.status is ProjectRelationRowSchemaStatus.CONCRETE:
        schema = state.schema
        if schema is None or schema.is_unknown:
            raise ValueError("Concrete terminal bundle requires exact schema")
        _validate_project_aggregate_result_facts(
            relation_row_schemas={definition: schema},
            relation_aggregate_result_facts=(
                {definition: aggregate_result_facts} if aggregate_result_facts else {}
            ),
        )
        _validate_project_window_result_facts(
            relation_row_schemas={definition: schema},
            relation_window_result_facts=(
                {definition: window_result_facts} if window_result_facts else {}
            ),
        )
    else:
        if aggregate_result_facts or window_result_facts:
            raise ValueError("Non-concrete terminal bundle forbids result facts")
        if dependency_graph.nodes or dependency_graph.edges or lineage.facts:
            raise ValueError("Non-concrete terminal bundle must be empty")

    relation_row_schema_states[definition] = state
    if state.schema is None:
        relation_row_schemas.pop(definition, None)
    else:
        relation_row_schemas[definition] = state.schema
    relation_let_scope_facts[definition] = let_scope_facts
    if aggregate_result_facts:
        relation_aggregate_result_facts[definition] = aggregate_result_facts
    else:
        relation_aggregate_result_facts.pop(definition, None)
    if window_result_facts:
        relation_window_result_facts[definition] = window_result_facts
    else:
        relation_window_result_facts.pop(definition, None)
    relation_row_dependency_graphs[definition] = dependency_graph
    relation_row_lineages[definition] = lineage


def _build_project_relation_let_scope_facts(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
) -> dict[TableDef | QueryDef, ProjectRelationLetScopeFacts]:
    """Build private relation-local let scope facts for project relations."""

    from pietto._project.let_scope_facts import build_project_relation_let_scope_facts

    facts: dict[TableDef | QueryDef, ProjectRelationLetScopeFacts] = {}
    for parsed_input in parsed_inputs:
        for definition in parsed_input.script.definitions:
            if not isinstance(definition, (TableDef, QueryDef)):
                continue

            upstream_definition: SourceDef | TableDef | QueryDef | None = None
            input_schema: ProjectRowSchema | None = None
            upstream_state: ProjectRelationRowSchemaState | None = None
            upstream_symbol = relation_resolutions.get(definition.from_clause)
            if upstream_symbol is None:
                upstream_state = ProjectRelationRowSchemaState(
                    status=ProjectRelationRowSchemaStatus.BLOCKED,
                    schema=None,
                    reason=(ProjectRelationRowSchemaReason.UNRESOLVED_RELATION_BLOCKED),
                )
            elif upstream_symbol.kind is ProjectSymbolKind.SOURCE and isinstance(
                upstream_symbol.definition, SourceDef
            ):
                upstream_definition = upstream_symbol.definition
                input_schema = source_row_schemas.get(upstream_definition)
            elif upstream_symbol.kind in (
                ProjectSymbolKind.TABLE,
                ProjectSymbolKind.QUERY,
            ) and isinstance(upstream_symbol.definition, (TableDef, QueryDef)):
                upstream_definition = upstream_symbol.definition
                upstream_state = relation_row_schema_states.get(upstream_definition)
                input_schema = relation_row_schemas.get(upstream_definition)

            facts[definition] = build_project_relation_let_scope_facts(
                definition=definition,
                input_schema=input_schema,
                upstream_definition=upstream_definition,
                upstream_state=upstream_state,
            )

    return facts


def _build_project_relation_row_dependency_graphs(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    source_row_schemas: Mapping[SourceDef, ProjectRowSchema],
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    relation_let_scope_facts: Mapping[
        TableDef | QueryDef, ProjectRelationLetScopeFacts
    ],
) -> dict[TableDef | QueryDef, ProjectRelationRowDependencyGraph]:
    """Build private row-level dependency graphs for project relations."""

    from pietto._project.row_dependency_graph import (
        build_project_relation_row_dependency_graphs,
    )

    return build_project_relation_row_dependency_graphs(
        parsed_inputs=parsed_inputs,
        relation_resolutions=relation_resolutions,
        source_row_schemas=source_row_schemas,
        relation_row_schemas=relation_row_schemas,
        relation_row_schema_states=relation_row_schema_states,
        relation_let_scope_facts=relation_let_scope_facts,
    )


def _build_project_relation_row_lineages(
    *,
    parsed_inputs: tuple[ProjectParsedInput, ...],
    relation_resolutions: Mapping[FromClause, ProjectSymbol],
    relation_row_schemas: Mapping[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: Mapping[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    relation_row_dependency_graphs: Mapping[
        TableDef | QueryDef, ProjectRelationRowDependencyGraph
    ],
) -> dict[TableDef | QueryDef, ProjectRelationRowLineage]:
    """Build private minimal row lineage carriers for project relations."""

    from pietto._project.row_lineage import build_project_relation_row_lineages

    return build_project_relation_row_lineages(
        parsed_inputs=parsed_inputs,
        relation_resolutions=relation_resolutions,
        relation_row_schemas=relation_row_schemas,
        relation_row_schema_states=relation_row_schema_states,
        relation_row_dependency_graphs=relation_row_dependency_graphs,
    )


def _record_project_relation_row_schema_result(
    *,
    relation_row_schemas: dict[TableDef | QueryDef, ProjectRowSchema],
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    definition: TableDef | QueryDef,
    schema: ProjectRowSchema | None,
    state_reason: ProjectRelationRowSchemaReason | None,
    concrete_reason: ProjectRelationRowSchemaReason,
) -> None:
    """Record one private relation row schema and availability state."""

    if schema is None:
        _set_project_relation_row_schema_state(
            relation_row_schema_states,
            definition,
            status=ProjectRelationRowSchemaStatus.DEFERRED,
            schema=None,
            reason=(
                state_reason or ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
            ),
        )
        return

    relation_row_schemas[definition] = schema
    if schema.is_unknown:
        _set_project_relation_row_schema_state(
            relation_row_schema_states,
            definition,
            status=ProjectRelationRowSchemaStatus.UNKNOWN,
            schema=schema,
            reason=state_reason or ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )
        return

    _set_project_relation_row_schema_state(
        relation_row_schema_states,
        definition,
        status=ProjectRelationRowSchemaStatus.CONCRETE,
        schema=schema,
        reason=concrete_reason,
    )


def _set_project_relation_row_schema_state(
    relation_row_schema_states: dict[
        TableDef | QueryDef, ProjectRelationRowSchemaState
    ],
    definition: TableDef | QueryDef,
    *,
    status: ProjectRelationRowSchemaStatus,
    schema: ProjectRowSchema | None,
    reason: ProjectRelationRowSchemaReason,
) -> None:
    """Set one private relation row schema availability state."""

    relation_row_schema_states[definition] = ProjectRelationRowSchemaState(
        status=status,
        schema=schema,
        reason=reason,
    )


def _project_direct_relation_row_schema(
    definition: TableDef | QueryDef,
    *,
    source_schema: ProjectRowSchema,
    source_symbol: ProjectSymbol,
    upstream_definition: SourceDef
    | TableDef
    | QueryDef
    | SetRelationDef
    | ValuesRelationDef
    | TableFunctionRelationDef,
    upstream_state: ProjectRelationRowSchemaState | None = None,
    fallback_path: str,
    let_scope_facts: ProjectRelationLetScopeFacts | None = None,
    read_types: Mapping[Expression, ValueType] | None = None,
    captured_value_types: Mapping[CapturedFieldExpr, ValueType | Diagnostic]
    | None = None,
    report_untyped_let_reads: bool = False,
    pretyped_expressions: Mapping[Expression, ProjectNoJoinScalarExpression]
    | None = None,
    collect_types: Mapping[Expression, ProjectResolvedType] | None = None,
) -> _ProjectRelationRowSchemaResult:
    """Project direct fields and supported computed aliases from one input.

    A read of a let it cannot type is PIE-S2102 only with
    ``report_untyped_let_reads``: a legacy flat project checks no let body, so
    that report is its only refusal of such a read. A Collect read's output
    takes its type from ``collect_types``, its read's own facts; one it does
    not type leaves the row unknown (its read reports why). So does a nested
    field selected from the input: only the relation collecting it outputs it,
    so its selection reports PIE-S2805 here, where an unknown field selected
    reports PIE-S2102, and its nested reference facts report that read once.
    """

    from pietto._project.let_scope_facts import (
        ProjectLetScopeFactsStatus,
        build_project_relation_let_scope_facts,
        checked_let_values,
    )
    from pietto._project.row_expression_schema import (
        ProjectExpressionSchemaOriginKind,
        ProjectExpressionSchemaStatus,
        adapt_project_row_expression_schema,
    )
    from pietto._project.row_expression_type_facts import (
        build_project_row_expression_value_types,
        nested_reference_diagnostic,
        project_row_schema_to_semantic_row_schema,
        reports_unfit_def_argument,
    )

    fields: dict[str, ProjectRowField] = {}
    diagnostics: list[Diagnostic] = []
    is_unknown = False
    unknown_reason: ProjectRelationRowSchemaReason | None = None
    if source_schema.is_unknown:
        return _ProjectRelationRowSchemaResult(
            schema=ProjectRowSchema(is_unknown=True),
            state_reason=ProjectRelationRowSchemaReason.UPSTREAM_UNKNOWN,
        )

    if let_scope_facts is None:
        let_scope_facts = build_project_relation_let_scope_facts(
            definition=definition,
            input_schema=source_schema,
            upstream_definition=upstream_definition,
            upstream_state=upstream_state,
        )
    # A binding of unknown type (such as `k = null`) or with an error of its
    # own leaves the scope non-concrete; reads of the other bindings are
    # still typed, and a read of one bound to `null` takes its type from where
    # it stands, as the value written there does.
    concrete_lets = let_scope_facts.status is ProjectLetScopeFactsStatus.CONCRETE
    let_value_types = (
        let_scope_facts.value_types
        if concrete_lets
        else let_scope_facts.binding_value_types or None
    )
    expression_value_types = build_project_row_expression_value_types(
        expressions=(
            item.expression
            for item in definition.select_items
            if item.alias is not None
            and type(item.expression) not in {WindowExpr, CollectRelationExpr}
        ),
        input_schema=source_schema,
        relation_qualifier=(
            definition.from_clause.binding_name or definition.from_clause.source_name
        ),
        bare_value_types=let_value_types,
        bare_value_expressions=(
            None
            if let_value_types is None
            else {
                name: let_scope_facts.binding_expressions[name]
                for name in let_value_types
            }
        ),
        read_types=read_types,
        captured_value_types=captured_value_types,
    )
    if pretyped_expressions:
        from pietto._project.project_final_outputs import (
            ProjectNoJoinScalarExpression,
            ProjectNoJoinScalarStatus,
        )
        from pietto.semantic.model import ValueTypeKind

        expression_value_types = dict(expression_value_types)
        for expression, analysis in pretyped_expressions.items():
            if type(analysis) is not ProjectNoJoinScalarExpression:
                raise TypeError(
                    "Pretyped projection requires a checked scalar analysis."
                )
            record = analysis.predicate_expression
            predicate_authority = record is not None and (
                record.owner is analysis.owner
                and record.authored is expression
                and not record.diagnostics
                and bool(record.calls)
            )
            any_authority = bool(analysis.existence_values) and all(
                value.input.binding.owner is analysis.owner
                and not value.diagnostics
                and value.value_types.get(value.expression) is value.value_type
                for value in analysis.existence_values
            )
            if (
                type(analysis) is not ProjectNoJoinScalarExpression
                or analysis.owner.definition is not definition
                or analysis.input_schema is not source_schema
                or analysis.expression is not expression
                or not (predicate_authority or any_authority)
                or analysis.status is not ProjectNoJoinScalarStatus.CONCRETE
                or analysis.value_type is None
                or analysis.value_type.kind is not ValueTypeKind.KNOWN
                or analysis.diagnostics
                or analysis.value_types.get(analysis.normalized_expression)
                is not analysis.value_type
                or not any(
                    item.alias is not None and item.expression is expression
                    for item in definition.select_items
                )
            ):
                raise ValueError(
                    "Pretyped projection requires exact checked predicate-expression authority."
                )
            expression_value_types[expression] = analysis.value_type

    deferred = _ProjectRelationRowSchemaResult(
        schema=None,
        state_reason=ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR,
    )

    let_names = (
        []
        if definition.let_clause is None
        else [binding.name for binding in definition.let_clause.bindings]
    )
    # What `passes_unfit_argument` types with, built once for a relation that
    # passes a select item to a def: the input row and one `LetValues` with
    # each `let:` name bound once, which writes each binding once.
    unfit_scope = (
        (
            project_row_schema_to_semantic_row_schema(source_schema),
            checked_let_values(
                let_scope_facts,
                {
                    name: expression
                    for name, expression in let_scope_facts.binding_expressions.items()
                    if let_names.count(name) == 1
                },
            ),
            set(let_names),
        )
        if any(inlined_arguments(item.expression) for item in definition.select_items)
        else None
    )

    def passes_unfit_argument(item: SelectItem) -> bool:
        """Whether ``item`` passes its field or `let:` name to a ``def`` it
        does not fit (`reports_unfit_def_argument`), typed as the select check
        types it: with each `let:` name bound once written in."""

        if unfit_scope is None or not inlined_arguments(item.expression):
            return False
        row_schema, let_values, suppressed_names = unfit_scope
        return reports_unfit_def_argument(
            item.expression,
            row_schema,
            relation_qualifier=(
                definition.from_clause.binding_name
                or definition.from_clause.source_name
            ),
            bare_value_types=let_value_types,
            bare_value_expressions=let_values,
            suppressed_unknown_names=suppressed_names,
            read_types=read_types,
            captured_value_types=captured_value_types,
        )

    for item in definition.select_items:
        if type(item.expression) is WindowExpr:
            continue
        if type(item.expression) is CollectRelationExpr:
            collected = (collect_types or {}).get(item.expression)
            if item.alias is None or collected is None or item.alias in fields:
                is_unknown = True
                unknown_reason = unknown_reason or (
                    ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
                    if item.alias in fields
                    else ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
                )
                continue
            fields[item.alias] = project_collect_output_field(
                item.alias,
                collected,
                _project_expression_location(
                    item.expression, fallback_path=fallback_path
                ),
            )
            continue
        projection = _project_direct_field_projection(
            item,
            source_name=(
                definition.from_clause.binding_name
                or definition.from_clause.source_name
            ),
            fallback_path=fallback_path,
        )
        if projection.status is _ProjectDirectFieldProjectionStatus.DEFERRED:
            if item.alias is None:
                return _ProjectRelationRowSchemaResult(
                    schema=None,
                    state_reason=(
                        ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
                    ),
                )

            result = adapt_project_row_expression_schema(
                expression=item.expression,
                output_name=item.alias,
                input_schema=source_schema,
                upstream_state=None,
                relation_qualifier=(
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                ),
                expression_value_types=expression_value_types,
                fallback_path=fallback_path,
            )
            if result.status is not ProjectExpressionSchemaStatus.CONCRETE:
                return _ProjectRelationRowSchemaResult(
                    schema=None,
                    state_reason=(
                        ProjectRelationRowSchemaReason.DEFERRED_PHASE48_BEHAVIOR
                    ),
                )

            if item.alias in fields:
                is_unknown = True
                unknown_reason = (
                    unknown_reason
                    or ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
                )
                continue

            if result.resolved_type is None or result.nullability is None:
                raise AssertionError("Concrete computed projection requires type facts")

            fields[item.alias] = ProjectRowField(
                name=item.alias,
                resolved_type=result.resolved_type,
                nullability=result.nullability,
                field_def=None,
                provenance=ProjectRowFieldProvenance(
                    kind=ProjectRowFieldProvenanceKind.DERIVED_EXPRESSION,
                    symbol=source_symbol,
                    location=result.location,
                ),
            )
            continue

        if projection.status is _ProjectDirectFieldProjectionStatus.INVALID:
            diagnostics.append(_project_unknown_direct_field_diagnostic(projection))
            is_unknown = True
            unknown_reason = ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
            continue

        output_name = projection.output_name
        lookup_name = projection.lookup_name
        if output_name is None or lookup_name is None:
            raise AssertionError("Supported direct projection requires field names")

        if output_name in fields:
            is_unknown = True
            unknown_reason = (
                unknown_reason or ProjectRelationRowSchemaReason.DUPLICATE_OUTPUT_NAME
            )
            continue

        source_field = source_schema.fields.get(lookup_name)
        if source_field is None:
            result = adapt_project_row_expression_schema(
                expression=item.expression,
                output_name=output_name,
                input_schema=source_schema,
                upstream_state=upstream_state,
                relation_qualifier=(
                    definition.from_clause.binding_name
                    or definition.from_clause.source_name
                ),
                expression_value_types=expression_value_types,
                let_value_types=let_value_types,
                fallback_path=fallback_path,
            )
            if (
                result.status is ProjectExpressionSchemaStatus.CONCRETE
                and result.origin is ProjectExpressionSchemaOriginKind.LET_DERIVED
            ):
                if result.resolved_type is None or result.nullability is None:
                    raise AssertionError(
                        "Concrete let-derived projection requires type facts"
                    )
                if passes_unfit_argument(item):
                    return deferred

                fields[output_name] = ProjectRowField(
                    name=output_name,
                    resolved_type=result.resolved_type,
                    nullability=result.nullability,
                    field_def=None,
                    provenance=ProjectRowFieldProvenance(
                        kind=ProjectRowFieldProvenanceKind.LET_DERIVED,
                        symbol=source_symbol,
                        location=result.location,
                    ),
                )
                continue

            # A read of a let whose value type is not known here is no unknown
            # field: the let's own diagnostics, or its completion, report it.
            if (
                report_untyped_let_reads
                or type(item.expression) is not NameExpr
                or lookup_name not in let_scope_facts.binding_expressions
            ):
                diagnostics.append(_project_unknown_direct_field_diagnostic(projection))
            is_unknown = True
            unknown_reason = ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
            continue
        if source_field.resolved_type.kind is ProjectResolvedTypeKind.NESTED_RELATION:
            diagnostics.append(nested_reference_diagnostic(item.expression, definition))
            is_unknown = True
            unknown_reason = unknown_reason or (
                ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA
            )
            continue
        if passes_unfit_argument(item):
            return deferred

        fields[output_name] = ProjectRowField(
            name=output_name,
            resolved_type=source_field.resolved_type,
            nullability=source_field.nullability,
            field_def=source_field.field_def,
            provenance=ProjectRowFieldProvenance(
                kind=ProjectRowFieldProvenanceKind.DIRECT_PROJECTION,
                symbol=source_symbol,
                location=projection.location,
            ),
        )

    if is_unknown or diagnostics:
        return _ProjectRelationRowSchemaResult(
            schema=ProjectRowSchema(is_unknown=True),
            diagnostics=tuple(diagnostics),
            state_reason=unknown_reason
            or ProjectRelationRowSchemaReason.UNKNOWN_SCHEMA,
        )

    return _ProjectRelationRowSchemaResult(schema=ProjectRowSchema(fields=fields))


def _project_direct_field_projection(
    item: SelectItem,
    *,
    source_name: str,
    fallback_path: str,
) -> _ProjectDirectFieldProjection:
    """Decode one direct field projection or direct field rename candidate."""

    expression = item.expression
    if isinstance(expression, NameExpr):
        lookup_name = expression.name
        return _ProjectDirectFieldProjection(
            status=_ProjectDirectFieldProjectionStatus.SUPPORTED,
            output_name=item.alias or lookup_name,
            lookup_name=lookup_name,
            field_text=lookup_name,
            location=_project_expression_location(
                expression,
                fallback_path=fallback_path,
            ),
        )
    if isinstance(expression, DottedNameExpr):
        if len(expression.parts) != 2 or expression.parts[0] != source_name:
            return _ProjectDirectFieldProjection(
                status=_ProjectDirectFieldProjectionStatus.INVALID,
                field_text=_project_dotted_field_text(expression),
                location=_project_expression_location(
                    expression,
                    fallback_path=fallback_path,
                ),
            )
        field_name = expression.parts[1]
        return _ProjectDirectFieldProjection(
            status=_ProjectDirectFieldProjectionStatus.SUPPORTED,
            output_name=item.alias or field_name,
            lookup_name=field_name,
            field_text=_project_dotted_field_text(expression),
            location=_project_expression_location(
                expression,
                fallback_path=fallback_path,
            ),
        )

    return _ProjectDirectFieldProjection(
        status=_ProjectDirectFieldProjectionStatus.DEFERRED
    )


def _project_dotted_field_text(expression: DottedNameExpr) -> str:
    """Return the user-facing dotted field reference text."""

    return ".".join(expression.parts)


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


def _build_project_source_row_schemas(
    *,
    source_shape_resolutions: Mapping[SourceDef, ProjectSymbol],
    type_resolutions: Mapping[TypeExpr, ProjectResolvedType],
) -> dict[SourceDef, ProjectRowSchema]:
    """Build private source row schemas from already-resolved source shapes."""

    source_row_schemas: dict[SourceDef, ProjectRowSchema] = {}
    for source, shape_symbol in source_shape_resolutions.items():
        shape = shape_symbol.definition
        if not isinstance(shape, ShapeDef):
            continue

        fields: dict[str, ProjectRowField] = {}
        skip_schema = False
        for field_def in shape.fields:
            resolved_type = type_resolutions.get(field_def.type_expr)
            if (
                resolved_type is None
                or resolved_type.kind is ProjectResolvedTypeKind.UNKNOWN
            ):
                skip_schema = True
                break
            if field_def.name in fields:
                continue
            fields[field_def.name] = ProjectRowField(
                name=field_def.name,
                resolved_type=resolved_type,
                nullability=_project_row_field_nullability(field_def.type_expr),
                field_def=field_def,
                provenance=ProjectRowFieldProvenance(
                    kind=ProjectRowFieldProvenanceKind.SOURCE_FIELD,
                    symbol=shape_symbol,
                    location=_project_field_location(
                        field_def,
                        fallback_path=shape_symbol.path,
                    ),
                ),
            )
        if not skip_schema:
            source_row_schemas[source] = ProjectRowSchema(fields=fields)

    return source_row_schemas


def _project_row_field_nullability(
    type_expr: TypeExpr,
) -> ProjectRowFieldNullability:
    """Map parsed type nullability to project-private row field nullability."""

    if type_expr.nullability is Nullability.NOT_NULL:
        return ProjectRowFieldNullability.NON_NULL
    if type_expr.nullability is Nullability.NULLABLE:
        return ProjectRowFieldNullability.NULLABLE
    return ProjectRowFieldNullability.UNKNOWN


def _project_field_location(
    field_def: FieldDef,
    *,
    fallback_path: str,
) -> SourceLocation:
    """Convert one shape field span into a private project source location."""

    span = field_def.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _project_expression_location(
    expression: Expression,
    *,
    fallback_path: str,
) -> SourceLocation:
    """Convert one projection expression span into a private project location."""

    span = expression.span
    return SourceLocation(
        path=span.path or fallback_path,
        line=span.line,
        column=span.column,
        end_line=span.end_line,
        end_column=span.end_column,
    )


def _iter_project_type_expressions(definition: Definition) -> tuple[TypeExpr, ...]:
    """Return declaration and explicit-cast type expressions in source order."""

    if type(definition) not in _KNOWN_DEFINITIONS:
        raise ValueError(f"Unsupported definition: {type(definition).__name__}")
    result: list[TypeExpr] = []

    def add_expression(expression: Expression) -> None:
        if type(expression) not in _KNOWN_EXPRESSIONS:
            raise ValueError(f"Unsupported expression: {type(expression).__name__}")
        if isinstance(expression, AnyExpr):
            add_expression(expression.predicate)
        elif isinstance(expression, CastExpr):
            add_expression(expression.value)
            result.append(expression.target)
        elif isinstance(expression, (BinaryExpr, ComparisonExpr)):
            add_expression(expression.left)
            add_expression(expression.right)
        elif isinstance(expression, UnaryExpr):
            add_expression(expression.operand)
        elif isinstance(expression, IsNullExpr):
            add_expression(expression.value)
        elif isinstance(expression, BetweenExpr):
            add_expression(expression.value)
            add_expression(expression.lower)
            add_expression(expression.upper)
        elif isinstance(expression, ConditionalExpr):
            add_expression(expression.when_true)
            add_expression(expression.condition)
            add_expression(expression.when_false)
        elif isinstance(expression, MembershipExpr):
            add_expression(expression.value)
            for option in expression.options:
                add_expression(option)
        elif isinstance(expression, RelationMembershipExpr):
            add_expression(expression.value)
        elif isinstance(expression, CallExpr):
            for argument in expression.arguments:
                add_expression(argument)
        elif isinstance(expression, WindowExpr):
            add_expression(expression.call)
            for item in expression.spec.partition_by:
                add_expression(item)
            for item in expression.spec.order_by:
                add_expression(item.expression)

    def add_type(type_expr: TypeExpr) -> None:
        result.append(type_expr)
        for argument in type_expr.arguments:
            add_expression(argument.value)

    if isinstance(definition, TypeDef):
        add_type(definition.base)
        for clause in definition.ensures:
            add_expression(clause.expression)
    elif isinstance(definition, (ConstraintDef, DeriveDef)):
        for parameter in definition.parameters:
            add_type(parameter.type)
        add_type(definition.return_type)
        add_expression(definition.body)
    elif isinstance(definition, ShapeDef):
        for item in definition.items:
            if isinstance(item, FieldDef):
                add_type(item.type_expr)
                if item.derive_expression is not None:
                    add_expression(item.derive_expression)
                for clause in item.ensure_clauses:
                    add_expression(clause.expression)
            elif isinstance(item, CheckDef):
                add_expression(item.expression)
            elif isinstance(item, IndexDef) and item.predicate is not None:
                add_expression(item.predicate)
    elif isinstance(definition, SourceDef):
        add_expression(definition.connector)
    elif isinstance(definition, (TableDef, QueryDef)):
        if definition.let_clause is not None:
            for binding in definition.let_clause.bindings:
                add_expression(binding.expression)
        if definition.where_clause is not None:
            add_expression(definition.where_clause.expression)
        for item in definition.select_items:
            add_expression(item.expression)
        if definition.satisfying_clause is not None:
            add_expression(definition.satisfying_clause.expression)
        if definition.qualify_clause is not None:
            add_expression(definition.qualify_clause.expression)
        if definition.order_by_clause is not None:
            for item in definition.order_by_clause.items:
                add_expression(item.expression)
        if definition.limit_clause is not None:
            add_expression(definition.limit_clause.expression)
        for join in definition.join_clauses:
            if join.on_clause is not None:
                add_expression(join.on_clause.expression)
    return tuple(result)


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
    definition: Definition
    | ValuesRelationDef
    | TableFunctionRelationDef
    | UnnestRelationDef,
) -> tuple[ProjectSymbolNamespace, ProjectSymbolKind]:
    """Classify a top-level definition into the Phase 45 hybrid namespace."""

    if isinstance(
        definition,
        (
            SetRelationDef,
            ValuesRelationDef,
            TableFunctionRelationDef,
            UnnestRelationDef,
        ),
    ):
        return ProjectSymbolNamespace.RELATION, ProjectSymbolKind(definition.kind.value)
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


def _unknown_project_relation_diagnostic(from_clause: FromClause) -> Diagnostic:
    """Report an unresolved project relation input at the from-clause span."""

    span = from_clause.span
    return Diagnostic(
        code="PIE-S2301",
        severity=Severity.ERROR,
        message=f"Unknown relation: {from_clause.source_name}",
        location=SourceLocation(
            path=span.path,
            line=span.line,
            column=span.column,
            end_line=span.end_line,
            end_column=span.end_column,
        ),
    )


def _project_unknown_direct_field_diagnostic(
    projection: _ProjectDirectFieldProjection,
) -> Diagnostic:
    """Report an unknown direct field reference at its expression span."""

    if projection.field_text is None or projection.location is None:
        raise AssertionError("Unknown direct field diagnostic requires field text")

    return Diagnostic(
        code="PIE-S2102",
        severity=Severity.ERROR,
        message=f"Unknown field: {projection.field_text}",
        location=projection.location,
    )


@dataclass(frozen=True, slots=True, eq=False)
class CompiledProjectInput:
    """Accepted resolved data with a new scope, never reopened source authority."""

    description: Description = field(repr=False)
    expected_pin: str
    accepted_producer: str
    accepted_compatibility: tuple
    scope: object = field(default_factory=object, init=False, repr=False)
    records: Mapping[Address, Record] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        from pietto._project.project_compiled_schema import (
            CompiledError,
            Description,
            content_pin,
            encode,
        )
        from pietto._project.project_compiled_verification import verify_description

        if type(self.description) is not Description:
            raise CompiledError("COMPILED_INPUT")
        verify_description(self.description)
        if (
            self.description.compatibility != self.accepted_compatibility
            or self.description.producer != self.accepted_producer
            or content_pin(encode(self.description)) != self.expected_pin
        ):
            raise CompiledError("COMPILED_HANDOFF")
        object.__setattr__(
            self,
            "records",
            MappingProxyType({r.address: r for r in self.description.records}),
        )

    def verify(self) -> None:
        """Run the complete description check, then the handoff pin and
        record-identity checks; a repeated check of this exact root inside one
        top-level call relies on the completed one."""
        from pietto._project.project_verification_scope import once

        once(_verify_compiled_input, self)


def _verify_compiled_input(root: CompiledProjectInput) -> None:
    from pietto._project.project_compiled_schema import (
        CompiledError,
        Description,
        content_pin,
        encode,
    )
    from pietto._project.project_compiled_verification import verify_description

    if type(root.description) is not Description:
        raise CompiledError("COMPILED_INPUT")
    verify_description(root.description)
    if (
        root.description.compatibility != root.accepted_compatibility
        or root.description.producer != root.accepted_producer
        or content_pin(encode(root.description)) != root.expected_pin
        or len(root.records) != len(root.description.records)
        or any(root.records.get(r.address) is not r for r in root.description.records)
    ):
        raise CompiledError("COMPILED_INPUT_CHANGED")
