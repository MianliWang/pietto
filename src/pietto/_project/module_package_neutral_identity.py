"""Private package-neutral identity layering, digest, and loader readiness."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from types import MappingProxyType
from typing import TypeVar

from pietto._project.module_attribution import (
    ProjectModuleAttributionFactSet,
    ProjectModuleDeclarationAttribution,
)
from pietto._project.module_carrier import (
    ProjectLogicalModule,
    ProjectModuleIdentity,
)
from pietto._project.module_catalog import (
    ProjectDeclarationOccurrence,
    ProjectModuleCatalogSet,
    ProjectNominalDeclarationIdentity,
)
from pietto._project.module_relation_resolution import (
    ProjectModuleRelationResolutionIssue,
    ProjectModuleRelationResolutionIssueStatus,
)
from pietto._project.module_semantic_fact_preservation import (
    ProjectModuleRelationSemanticFacts,
    ProjectModuleSemanticFactSet,
)
from pietto._project.model import (
    ProjectRelationRowSchemaState,
    ProjectRelationRowSchemaStatus,
    ProjectSymbolNamespace,
)
from pietto._project.selected_input_index import (
    ProjectSelectedInputEntry,
    ProjectSelectedInputIndex,
)
from pietto._project.trusted_source import ProjectTrustedSourceSnapshot

__all__: tuple[str, ...] = ()

_Key = TypeVar("_Key")
_Value = TypeVar("_Value")

_LAYERED_LOCAL_NAMESPACE = ""

_LAYERED_DIGEST_HEX_LENGTH = 64

_LAYERED_DIGEST_HEX_ALPHABET = frozenset("0123456789abcdef")


class ProjectLayeredOwnerKind(StrEnum):
    """Package-neutral owner kinds available inside Phase 54."""

    LOCAL_PROJECT_ROOT = "local_project_root"
    LOCAL_MODULE = "local_module"


class ProjectLayeredAssetKind(StrEnum):
    """Package-neutral asset kinds available inside Phase 54."""

    MODULE_SOURCE = "module_source"
    NOMINAL_DECLARATION = "nominal_declaration"


class ProjectLayeredAvailability(StrEnum):
    """Package-neutral availability of one layered asset fact."""

    CONCRETE = "concrete"
    UNKNOWN = "unknown"
    DEFERRED = "deferred"
    BLOCKED = "blocked"
    ABSENT = "absent"
    AMBIGUOUS = "ambiguous"


class ProjectLayeredLoaderReadiness(StrEnum):
    """Package-neutral loader-readiness states with no loader implemented."""

    READY = "ready"
    BLOCKED = "blocked"


class ProjectLayeredLoaderReadinessReason(StrEnum):
    """Deterministic reason retained beside every loader-readiness status."""

    TRUSTED_LOCAL_SOURCE_RESOLVED = "trusted_local_source_resolved"
    MODULE_CYCLE_BLOCKED = "module_cycle_blocked"


class ProjectLayeredDigestAlgorithm(StrEnum):
    """The exact existing source-digest authority reached through by Slice 13."""

    SHA256_OPENED_BYTES = "sha256_opened_bytes"


_LAYERED_AVAILABILITY_BY_ROW_SCHEMA_STATUS: Mapping[
    ProjectRelationRowSchemaStatus,
    ProjectLayeredAvailability,
] = MappingProxyType(
    {
        ProjectRelationRowSchemaStatus.CONCRETE: ProjectLayeredAvailability.CONCRETE,
        ProjectRelationRowSchemaStatus.UNKNOWN: ProjectLayeredAvailability.UNKNOWN,
        ProjectRelationRowSchemaStatus.DEFERRED: ProjectLayeredAvailability.DEFERRED,
        ProjectRelationRowSchemaStatus.BLOCKED: ProjectLayeredAvailability.BLOCKED,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectLayeredOwnerIdentity:
    """One package-neutral owner identity with no package product field."""

    kind: ProjectLayeredOwnerKind
    namespace: str
    name: str

    def __post_init__(self) -> None:
        """Reject any owner identity that would encode a package identity."""

        if type(self.kind) is not ProjectLayeredOwnerKind:
            raise TypeError("Layered owner identity requires an exact owner kind.")
        if type(self.namespace) is not str:
            raise TypeError("Layered owner namespace must be text.")
        if self.namespace != _LAYERED_LOCAL_NAMESPACE:
            raise ValueError(
                "Layered owner namespace must remain the reserved empty local "
                "namespace."
            )
        if type(self.name) is not str:
            raise TypeError("Layered owner name must be text.")
        if self.kind is ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT:
            if self.name != "":
                raise ValueError("Local project root owner must remain unnamed.")
            return
        ProjectModuleIdentity(path=self.name)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectLayeredSourceDigestIdentity:
    """One content identity derived from the exact trusted source digest."""

    algorithm: ProjectLayeredDigestAlgorithm
    digest: str
    byte_count: int

    def __post_init__(self) -> None:
        """Reject digests outside the exact retained trusted-source domain."""

        if type(self.algorithm) is not ProjectLayeredDigestAlgorithm:
            raise TypeError("Layered source digest requires an exact algorithm.")
        if (
            type(self.digest) is not str
            or len(self.digest) != _LAYERED_DIGEST_HEX_LENGTH
            or any(
                character not in _LAYERED_DIGEST_HEX_ALPHABET
                for character in self.digest
            )
        ):
            raise ValueError("Layered source digest must be lowercase hexadecimal.")
        if type(self.byte_count) is not int or self.byte_count < 0:
            raise ValueError("Layered source digest byte count must be non-negative.")


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectLayeredLoaderReadinessFact:
    """One atomic loader-readiness status, reason, and blocking evidence tuple."""

    status: ProjectLayeredLoaderReadiness
    reason: ProjectLayeredLoaderReadinessReason
    blocking_issues: tuple[ProjectModuleRelationResolutionIssue, ...] = ()

    def __post_init__(self) -> None:
        """Reject every non-atomic loader-readiness combination."""

        if type(self.status) is not ProjectLayeredLoaderReadiness:
            raise TypeError("Loader readiness requires an exact status.")
        if type(self.reason) is not ProjectLayeredLoaderReadinessReason:
            raise TypeError("Loader readiness requires an exact reason.")
        _require_tuple(
            self.blocking_issues,
            ProjectModuleRelationResolutionIssue,
            "Loader readiness blocking issues",
        )
        if self.status is ProjectLayeredLoaderReadiness.READY:
            if (
                self.reason
                is not ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
            ):
                raise ValueError("Ready loader readiness requires its exact reason.")
            if self.blocking_issues:
                raise ValueError("Ready loader readiness forbids blocking evidence.")
            return
        if self.reason is not ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED:
            raise ValueError("Blocked loader readiness requires its exact reason.")
        if not self.blocking_issues:
            raise ValueError("Blocked loader readiness requires blocking evidence.")
        if any(
            issue.status
            is not ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
            for issue in self.blocking_issues
        ):
            raise ValueError(
                "Blocked loader readiness requires exact module-cycle evidence."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectLayeredModuleAsset:
    """One package-neutral module-source asset layered over Slice 3 facts."""

    owner: ProjectLayeredOwnerIdentity
    asset_kind: ProjectLayeredAssetKind
    module: ProjectModuleIdentity
    position: int
    digest: ProjectLayeredSourceDigestIdentity
    readiness: ProjectLayeredLoaderReadinessFact
    selected_input: ProjectSelectedInputEntry = field(
        repr=False,
        compare=False,
        hash=False,
    )
    snapshot: ProjectTrustedSourceSnapshot = field(
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Reject a module asset that does not reach through its exact roots."""

        if type(self.owner) is not ProjectLayeredOwnerIdentity:
            raise TypeError("Layered module asset requires an owner identity.")
        if self.owner.kind is not ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT:
            raise ValueError("Layered module asset owner must be the project root.")
        if self.asset_kind is not ProjectLayeredAssetKind.MODULE_SOURCE:
            raise ValueError("Layered module asset requires the module-source kind.")
        if type(self.module) is not ProjectModuleIdentity:
            raise TypeError("Layered module asset requires a module identity.")
        _validate_position(self.position, "layered module asset")
        if type(self.digest) is not ProjectLayeredSourceDigestIdentity:
            raise TypeError("Layered module asset requires a source digest identity.")
        if type(self.readiness) is not ProjectLayeredLoaderReadinessFact:
            raise TypeError("Layered module asset requires a loader-readiness fact.")
        if type(self.selected_input) is not ProjectSelectedInputEntry:
            raise TypeError("Layered module asset requires a selected input entry.")
        if type(self.snapshot) is not ProjectTrustedSourceSnapshot:
            raise TypeError("Layered module asset requires a trusted source snapshot.")
        if self.snapshot.selected_input is not self.selected_input:
            raise ValueError("Layered module asset requires exact selection evidence.")
        if (
            self.selected_input.identity != self.module
            or self.selected_input.position != self.position
        ):
            raise ValueError("Layered module asset must match its selected entry.")
        if (
            self.digest.algorithm
            is not ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES
            or self.digest.digest != self.snapshot.sha256
            or self.digest.byte_count != self.snapshot.byte_count
        ):
            raise ValueError("Layered module digest must reach through its snapshot.")
        _require_readiness_names_module(self.readiness, self.module.path)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectLayeredDeclarationAsset:
    """One package-neutral declaration asset joining Slice 11 and Slice 12."""

    owner: ProjectLayeredOwnerIdentity
    asset_kind: ProjectLayeredAssetKind
    identity: ProjectNominalDeclarationIdentity
    occurrence: ProjectDeclarationOccurrence = field(
        repr=False,
        compare=False,
        hash=False,
    )
    identity_occurrences: tuple[ProjectDeclarationOccurrence, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    attribution: ProjectModuleDeclarationAttribution = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic_facts: tuple[ProjectModuleRelationSemanticFacts, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    readiness: ProjectLayeredLoaderReadinessFact
    availability: ProjectLayeredAvailability
    relation_state: ProjectRelationRowSchemaState | None = field(
        default=None,
        repr=False,
        compare=False,
        hash=False,
    )
    declaration_position: int

    def __post_init__(self) -> None:
        """Reject every non-atomic or unrooted layered declaration asset."""

        if type(self.owner) is not ProjectLayeredOwnerIdentity:
            raise TypeError("Layered declaration asset requires an owner identity.")
        if self.owner.kind is not ProjectLayeredOwnerKind.LOCAL_MODULE:
            raise ValueError("Layered declaration owner must be the local module.")
        if self.asset_kind is not ProjectLayeredAssetKind.NOMINAL_DECLARATION:
            raise ValueError("Layered declaration asset requires a declaration kind.")
        if type(self.identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Layered declaration asset requires a nominal identity.")
        if self.owner.name != self.identity.module_path:
            raise ValueError("Layered declaration owner must name its exact module.")
        if type(self.occurrence) is not ProjectDeclarationOccurrence:
            raise TypeError("Layered declaration asset requires an exact occurrence.")
        if self.occurrence.identity != self.identity:
            raise ValueError("Layered declaration occurrence must match its identity.")
        _validate_position(self.declaration_position, "layered declaration asset")
        if self.occurrence.declaration_position != self.declaration_position:
            raise ValueError("Layered declaration position must match its occurrence.")
        _require_tuple(
            self.identity_occurrences,
            ProjectDeclarationOccurrence,
            "Layered declaration identity occurrences",
        )
        if not _is_exact_member(self.occurrence, self.identity_occurrences):
            raise ValueError(
                "Layered declaration asset must appear in its own identity bucket."
            )
        if any(
            occurrence.identity != self.identity
            for occurrence in self.identity_occurrences
        ):
            raise ValueError(
                "Layered declaration identity bucket must retain one exact identity."
            )
        if type(self.attribution) is not ProjectModuleDeclarationAttribution:
            raise TypeError("Layered declaration asset requires Slice 11 attribution.")
        if self.attribution.occurrence is not self.occurrence:
            raise ValueError(
                "Layered declaration attribution must retain the exact occurrence."
            )
        _require_tuple(
            self.semantic_facts,
            ProjectModuleRelationSemanticFacts,
            "Layered declaration semantic facts",
        )
        if any(fact.owner is not self.occurrence for fact in self.semantic_facts):
            raise ValueError(
                "Layered declaration semantic facts must retain the exact owner."
            )
        if type(self.readiness) is not ProjectLayeredLoaderReadinessFact:
            raise TypeError("Layered declaration asset requires a readiness fact.")
        if type(self.availability) is not ProjectLayeredAvailability:
            raise TypeError("Layered declaration asset requires an availability.")
        if self.relation_state is not None and (
            type(self.relation_state) is not ProjectRelationRowSchemaState
        ):
            raise TypeError("Layered declaration relation state must be exact.")
        _require_readiness_names_module(self.readiness, self.identity.module_path)
        self._validate_availability_atomicity()

    def _validate_availability_atomicity(self) -> None:
        """Require status, evidence, and derived product to form one tuple."""

        is_relation = self.identity.namespace is ProjectSymbolNamespace.RELATION
        if self.readiness.status is ProjectLayeredLoaderReadiness.BLOCKED:
            if self.availability is not ProjectLayeredAvailability.BLOCKED:
                raise ValueError(
                    "A loader-blocked module publishes only blocked declaration assets."
                )
            if self.semantic_facts or self.relation_state is not None:
                raise ValueError(
                    "A loader-blocked declaration asset publishes no semantic product."
                )
            return
        if len(self.identity_occurrences) > 1:
            if self.availability is not ProjectLayeredAvailability.AMBIGUOUS:
                raise ValueError(
                    "A repeated nominal identity must remain ambiguous without a winner."
                )
            if self.relation_state is not None:
                raise ValueError(
                    "An ambiguous nominal identity publishes no relation state."
                )
            return
        if self.availability is ProjectLayeredAvailability.AMBIGUOUS:
            raise ValueError(
                "Ambiguous availability requires a repeated nominal identity."
            )
        if not is_relation:
            if self.availability is not ProjectLayeredAvailability.ABSENT:
                raise ValueError(
                    "A non-relation declaration asset has no applicable relation fact."
                )
            if self.semantic_facts or self.relation_state is not None:
                raise ValueError(
                    "An absent declaration asset publishes no relation product."
                )
            return
        if len(self.semantic_facts) != 1:
            raise ValueError(
                "A ready relation declaration asset requires one exact semantic fact."
            )
        state = self.semantic_facts[0].state
        if self.relation_state is not state:
            raise ValueError(
                "A relation declaration asset must retain its exact Slice 12 state."
            )
        if (
            self.availability
            is not _LAYERED_AVAILABILITY_BY_ROW_SCHEMA_STATUS[state.status]
        ):
            raise ValueError(
                "A relation declaration availability must map its exact Slice 12 status."
            )


@dataclass(frozen=True, slots=True, kw_only=True)
class _ProjectLayeredIdentityAuthority:
    """Private exact join authority for the Slice 3, 11, and 12 roots.

    The six retained roots are the only constructor inputs. Every layered
    product is derived from them at construction, so a supplied derived tuple
    can never be grafted through this carrier.
    """

    selected_input_index: ProjectSelectedInputIndex = field(
        repr=False,
        compare=False,
        hash=False,
    )
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    modules: tuple[ProjectLogicalModule, ...] = field(
        repr=False,
        compare=False,
        hash=False,
    )
    catalogs: ProjectModuleCatalogSet = field(repr=False, compare=False, hash=False)
    attribution: ProjectModuleAttributionFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    semantic: ProjectModuleSemanticFactSet = field(
        repr=False,
        compare=False,
        hash=False,
    )
    owner: ProjectLayeredOwnerIdentity = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    module_assets: tuple[ProjectLayeredModuleAsset, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    declaration_assets: tuple[ProjectLayeredDeclarationAsset, ...] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )

    def __post_init__(self) -> None:
        """Validate the shared root set as a whole and derive every product."""

        _validate_layered_authority_roots(
            self.selected_input_index,
            self.trusted_source_snapshots,
            self.modules,
            self.catalogs,
            self.attribution,
            self.semantic,
        )
        owner, module_assets, declaration_assets = _derive_layered_collections(
            self.selected_input_index,
            self.trusted_source_snapshots,
            self.modules,
            self.catalogs,
            self.attribution,
            self.semantic,
        )
        object.__setattr__(self, "owner", owner)
        object.__setattr__(self, "module_assets", module_assets)
        object.__setattr__(self, "declaration_assets", declaration_assets)


@dataclass(frozen=True, slots=True, kw_only=True)
class ProjectModulePackageNeutralIdentityFactSet:
    """Complete private Slice 13 package-neutral identity layering product."""

    owner: ProjectLayeredOwnerIdentity
    module_assets: tuple[ProjectLayeredModuleAsset, ...] = ()
    declaration_assets: tuple[ProjectLayeredDeclarationAsset, ...] = ()
    authority: _ProjectLayeredIdentityAuthority = field(
        repr=False,
        compare=False,
        hash=False,
    )
    _module_assets_by_path: Mapping[str, tuple[ProjectLayeredModuleAsset, ...]] = field(
        init=False,
        repr=False,
        compare=False,
        hash=False,
    )
    _declaration_assets_by_identity: Mapping[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectLayeredDeclarationAsset, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)
    _module_assets_by_digest: Mapping[
        ProjectLayeredSourceDigestIdentity,
        tuple[ProjectLayeredModuleAsset, ...],
    ] = field(init=False, repr=False, compare=False, hash=False)

    def __post_init__(self) -> None:
        """Require the exact derived products of the exact retained authority."""

        if type(self.authority) is not _ProjectLayeredIdentityAuthority:
            raise TypeError("Layered fact set requires an exact private authority.")
        if self.owner is not self.authority.owner:
            raise ValueError("Layered fact set must retain the exact derived owner.")
        if self.module_assets is not self.authority.module_assets:
            raise ValueError(
                "Layered fact set must retain the exact derived module assets."
            )
        if self.declaration_assets is not self.authority.declaration_assets:
            raise ValueError(
                "Layered fact set must retain the exact derived declaration assets."
            )

        module_assets_by_path: dict[str, list[ProjectLayeredModuleAsset]] = {}
        module_assets_by_digest: dict[
            ProjectLayeredSourceDigestIdentity,
            list[ProjectLayeredModuleAsset],
        ] = {}
        for asset in self.module_assets:
            module_assets_by_path.setdefault(asset.module.path, []).append(asset)
            module_assets_by_digest.setdefault(asset.digest, []).append(asset)
        declaration_assets_by_identity: dict[
            ProjectNominalDeclarationIdentity,
            list[ProjectLayeredDeclarationAsset],
        ] = {}
        for declaration_asset in self.declaration_assets:
            declaration_assets_by_identity.setdefault(
                declaration_asset.identity, []
            ).append(declaration_asset)

        object.__setattr__(
            self,
            "_module_assets_by_path",
            _frozen_bucket_mapping(module_assets_by_path),
        )
        object.__setattr__(
            self,
            "_module_assets_by_digest",
            _frozen_bucket_mapping(module_assets_by_digest),
        )
        object.__setattr__(
            self,
            "_declaration_assets_by_identity",
            _frozen_bucket_mapping(declaration_assets_by_identity),
        )

    def find_module(
        self,
        module: ProjectModuleIdentity,
    ) -> tuple[ProjectLayeredModuleAsset, ...]:
        """Return the complete module-asset bucket for one exact identity."""

        if type(module) is not ProjectModuleIdentity:
            raise TypeError("Layered module lookup requires a module identity.")
        return self._module_assets_by_path.get(module.path, ())

    def find_declaration(
        self,
        identity: ProjectNominalDeclarationIdentity,
    ) -> tuple[ProjectLayeredDeclarationAsset, ...]:
        """Return the complete declaration-asset bucket without a winner."""

        if type(identity) is not ProjectNominalDeclarationIdentity:
            raise TypeError("Layered declaration lookup requires a nominal identity.")
        return self._declaration_assets_by_identity.get(identity, ())

    def find_digest(
        self,
        digest: ProjectLayeredSourceDigestIdentity,
    ) -> tuple[ProjectLayeredModuleAsset, ...]:
        """Return every module asset that carries one exact content digest."""

        if type(digest) is not ProjectLayeredSourceDigestIdentity:
            raise TypeError("Layered digest lookup requires a digest identity.")
        return self._module_assets_by_digest.get(digest, ())


def _build_project_module_package_neutral_identity_fact_set(
    selected_input_index: ProjectSelectedInputIndex,
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...],
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
) -> ProjectModulePackageNeutralIdentityFactSet:
    """Build the pure Slice 13 layered identity product from exact roots."""

    authority = _ProjectLayeredIdentityAuthority(
        selected_input_index=selected_input_index,
        trusted_source_snapshots=trusted_source_snapshots,
        modules=modules,
        catalogs=catalogs,
        attribution=attribution,
        semantic=semantic,
    )
    return ProjectModulePackageNeutralIdentityFactSet(
        owner=authority.owner,
        module_assets=authority.module_assets,
        declaration_assets=authority.declaration_assets,
        authority=authority,
    )


def _validate_layered_authority_roots(
    selected_input_index: ProjectSelectedInputIndex,
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...],
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
) -> None:
    """Prove the two independently rooted carriers share one exact root set."""

    if type(selected_input_index) is not ProjectSelectedInputIndex:
        raise TypeError("Layered authority requires an exact selected-input index.")
    _require_tuple(
        trusted_source_snapshots,
        ProjectTrustedSourceSnapshot,
        "Layered authority trusted source snapshots",
    )
    _require_tuple(modules, ProjectLogicalModule, "Layered authority modules")
    if type(catalogs) is not ProjectModuleCatalogSet:
        raise TypeError("Layered authority requires exact module catalogs.")
    if type(attribution) is not ProjectModuleAttributionFactSet:
        raise TypeError("Layered authority requires an exact Slice 11 fact set.")
    if type(semantic) is not ProjectModuleSemanticFactSet:
        raise TypeError("Layered authority requires an exact Slice 12 fact set.")

    attribution_authority = attribution._authority
    semantic_authority = semantic.authority
    if (
        attribution_authority.selected_input_index is not selected_input_index
        or attribution_authority.trusted_source_snapshots
        is not trusted_source_snapshots
        or attribution_authority.modules is not modules
        or attribution_authority.catalogs is not catalogs
    ):
        raise ValueError(
            "Layered authority requires the exact Slice 11 input and module roots."
        )
    if (
        semantic_authority.modules is not modules
        or semantic_authority.catalogs is not catalogs
    ):
        raise ValueError(
            "Layered authority requires the exact Slice 12 module and catalog roots."
        )
    relation_resolutions = attribution_authority.relation_resolutions
    if semantic_authority.relation_resolutions is not relation_resolutions:
        raise ValueError(
            "Layered authority requires one shared exact Slice 10 relation root."
        )
    if (
        semantic.dependency_order is not relation_resolutions.dependency_order
        or semantic.issues is not relation_resolutions.issues
    ):
        raise ValueError(
            "Layered authority requires the exact shared dependency order and issues."
        )
    environments = relation_resolutions.environments
    if len(semantic.environments) != len(environments) or any(
        semantic_environment.resolution_environment is not environment
        for semantic_environment, environment in zip(
            semantic.environments,
            environments,
            strict=True,
        )
    ):
        raise ValueError(
            "Layered authority requires the exact shared Slice 10 environments."
        )

    if len(trusted_source_snapshots) != len(modules) or len(
        selected_input_index.entries
    ) != len(modules):
        raise ValueError("Layered authority requires one exact root per module.")
    if len(catalogs.catalogs) != len(modules):
        raise ValueError("Layered authority requires one exact catalog per module.")
    for position, module in enumerate(modules):
        entry = selected_input_index.entries[position]
        snapshot = trusted_source_snapshots[position]
        catalog = catalogs.catalogs[position]
        if (
            entry.identity != module.identity
            or entry.position != position
            or snapshot.selected_input is not entry
            or catalog.module is not module
        ):
            raise ValueError(
                "Layered authority requires aligned module, selection, and catalog "
                "roots."
            )

    expected_declarations = tuple(
        occurrence
        for catalog in catalogs.catalogs
        for occurrence in catalog.occurrences
    )
    if len(attribution.declarations) != len(expected_declarations) or any(
        declaration.occurrence is not occurrence
        for declaration, occurrence in zip(
            attribution.declarations,
            expected_declarations,
            strict=True,
        )
    ):
        raise ValueError(
            "Layered authority requires the complete ordered Slice 11 declarations."
        )


def _derive_layered_collections(
    selected_input_index: ProjectSelectedInputIndex,
    trusted_source_snapshots: tuple[ProjectTrustedSourceSnapshot, ...],
    modules: tuple[ProjectLogicalModule, ...],
    catalogs: ProjectModuleCatalogSet,
    attribution: ProjectModuleAttributionFactSet,
    semantic: ProjectModuleSemanticFactSet,
) -> tuple[
    ProjectLayeredOwnerIdentity,
    tuple[ProjectLayeredModuleAsset, ...],
    tuple[ProjectLayeredDeclarationAsset, ...],
]:
    """Derive the one canonical layered projection from the exact roots."""

    owner = ProjectLayeredOwnerIdentity(
        kind=ProjectLayeredOwnerKind.LOCAL_PROJECT_ROOT,
        namespace=_LAYERED_LOCAL_NAMESPACE,
        name="",
    )
    dependency_paths = frozenset(
        identity.path for identity in semantic.dependency_order
    )
    # Cycle membership is decided by the retained cycle component, never by the
    # owning module of the issue: an acyclic module that merely references a
    # cycle-blocked target also owns a MODULE_GRAPH_CYCLE_BLOCKED issue.
    cycle_issues_by_path: dict[str, list[ProjectModuleRelationResolutionIssue]] = {}
    for issue in semantic.issues:
        if (
            issue.status
            is not ProjectModuleRelationResolutionIssueStatus.MODULE_GRAPH_CYCLE_BLOCKED
            or issue.module_cycle is None
        ):
            continue
        for member in issue.module_cycle.component.members:
            cycle_issues_by_path.setdefault(member.identity.path, []).append(issue)

    module_assets: list[ProjectLayeredModuleAsset] = []
    readiness_by_path: dict[str, ProjectLayeredLoaderReadinessFact] = {}
    for position, module in enumerate(modules):
        entry = selected_input_index.entries[position]
        snapshot = trusted_source_snapshots[position]
        blocking_issues = tuple(cycle_issues_by_path.get(module.path, ()))
        if module.path in dependency_paths:
            if blocking_issues:
                raise ValueError(
                    "A dependency-ordered module cannot be a retained cycle member."
                )
            readiness = ProjectLayeredLoaderReadinessFact(
                status=ProjectLayeredLoaderReadiness.READY,
                reason=(
                    ProjectLayeredLoaderReadinessReason.TRUSTED_LOCAL_SOURCE_RESOLVED
                ),
            )
        else:
            if not blocking_issues:
                raise ValueError(
                    "An unordered module requires exact module-cycle blocking evidence."
                )
            readiness = ProjectLayeredLoaderReadinessFact(
                status=ProjectLayeredLoaderReadiness.BLOCKED,
                reason=ProjectLayeredLoaderReadinessReason.MODULE_CYCLE_BLOCKED,
                blocking_issues=blocking_issues,
            )
        readiness_by_path[module.path] = readiness
        module_assets.append(
            ProjectLayeredModuleAsset(
                owner=owner,
                asset_kind=ProjectLayeredAssetKind.MODULE_SOURCE,
                module=module.identity,
                position=position,
                digest=ProjectLayeredSourceDigestIdentity(
                    algorithm=ProjectLayeredDigestAlgorithm.SHA256_OPENED_BYTES,
                    digest=snapshot.sha256,
                    byte_count=snapshot.byte_count,
                ),
                readiness=readiness,
                selected_input=entry,
                snapshot=snapshot,
            )
        )

    attribution_by_occurrence: dict[int, ProjectModuleDeclarationAttribution] = {
        id(declaration.occurrence): declaration
        for declaration in attribution.declarations
    }
    # The complete identity bucket is a canonical root-derived projection, so it
    # is built once in one pass over the catalog roots. Re-deriving it per
    # declaration would rescan every catalog and allocate a fresh equal tuple for
    # each occurrence of one identity.
    identity_occurrence_lists: dict[
        ProjectNominalDeclarationIdentity,
        list[ProjectDeclarationOccurrence],
    ] = {}
    for catalog in catalogs.catalogs:
        for occurrence in catalog.occurrences:
            identity_occurrence_lists.setdefault(occurrence.identity, []).append(
                occurrence
            )
    identity_buckets: dict[
        ProjectNominalDeclarationIdentity,
        tuple[ProjectDeclarationOccurrence, ...],
    ] = {
        identity: tuple(occurrences)
        for identity, occurrences in identity_occurrence_lists.items()
    }
    declaration_assets: list[ProjectLayeredDeclarationAsset] = []
    for catalog in catalogs.catalogs:
        module_owner = ProjectLayeredOwnerIdentity(
            kind=ProjectLayeredOwnerKind.LOCAL_MODULE,
            namespace=_LAYERED_LOCAL_NAMESPACE,
            name=catalog.module_path,
        )
        readiness = readiness_by_path[catalog.module_path]
        for occurrence in catalog.occurrences:
            declaration = attribution_by_occurrence[id(occurrence)]
            identity_occurrences = identity_buckets[occurrence.identity]
            semantic_facts = semantic.find_owner(occurrence)
            availability, relation_state = _layered_declaration_availability(
                readiness=readiness,
                occurrence=occurrence,
                identity_occurrences=identity_occurrences,
                semantic_facts=semantic_facts,
            )
            declaration_assets.append(
                ProjectLayeredDeclarationAsset(
                    owner=module_owner,
                    asset_kind=ProjectLayeredAssetKind.NOMINAL_DECLARATION,
                    identity=occurrence.identity,
                    occurrence=occurrence,
                    identity_occurrences=identity_occurrences,
                    attribution=declaration,
                    semantic_facts=semantic_facts,
                    readiness=readiness,
                    availability=availability,
                    relation_state=relation_state,
                    declaration_position=occurrence.declaration_position,
                )
            )

    return owner, tuple(module_assets), tuple(declaration_assets)


def _layered_declaration_availability(
    *,
    readiness: ProjectLayeredLoaderReadinessFact,
    occurrence: ProjectDeclarationOccurrence,
    identity_occurrences: tuple[ProjectDeclarationOccurrence, ...],
    semantic_facts: tuple[ProjectModuleRelationSemanticFacts, ...],
) -> tuple[ProjectLayeredAvailability, ProjectRelationRowSchemaState | None]:
    """Reduce one declaration asset only after its complete bucket exists."""

    if readiness.status is ProjectLayeredLoaderReadiness.BLOCKED:
        return ProjectLayeredAvailability.BLOCKED, None
    if len(identity_occurrences) > 1:
        return ProjectLayeredAvailability.AMBIGUOUS, None
    if occurrence.identity.namespace is not ProjectSymbolNamespace.RELATION:
        return ProjectLayeredAvailability.ABSENT, None
    if len(semantic_facts) != 1:
        raise ValueError(
            "A ready relation declaration requires one exact Slice 12 semantic fact."
        )
    state = semantic_facts[0].state
    return _LAYERED_AVAILABILITY_BY_ROW_SCHEMA_STATUS[state.status], state


def _frozen_bucket_mapping(
    buckets: Mapping[_Key, list[_Value]],
) -> Mapping[_Key, tuple[_Value, ...]]:
    """Copy complete buckets into an immutable tuple-valued mapping."""

    return MappingProxyType({key: tuple(values) for key, values in buckets.items()})


def _require_readiness_names_module(
    readiness: ProjectLayeredLoaderReadinessFact,
    module_path: str,
) -> None:
    """Require every retained blocking issue to name this exact module.

    Blocking evidence is admitted only for a module the retained cycle
    component actually lists as a member, so a second, disjoint module cycle's
    evidence can never be grafted onto this asset.
    """

    for issue in readiness.blocking_issues:
        cycle = issue.module_cycle
        if cycle is None or not any(
            member.identity.path == module_path for member in cycle.component.members
        ):
            raise ValueError(
                "Layered loader readiness must retain only this module's cycle "
                "evidence."
            )


def _is_exact_member(value: object, values: tuple[object, ...]) -> bool:
    """Return whether one exact object appears in a tuple by identity."""

    return any(value is candidate for candidate in values)


def _require_tuple(values: object, item_type: type, label: str) -> None:
    """Require an exact tuple of one exact item type."""

    if type(values) is not tuple:
        raise TypeError(f"{label} must be a tuple.")
    if any(type(value) is not item_type for value in values):
        raise TypeError(f"{label} must retain exact items.")


def _validate_position(value: int, label: str) -> None:
    """Require a non-negative integer position."""

    if type(value) is not int or value < 0:
        raise ValueError(f"{label} position must be a non-negative integer.")
