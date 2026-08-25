"""Private project capability-environment authority construction."""

from __future__ import annotations

from dataclasses import dataclass

from pietto._project.capability_availability import (
    CapabilityProfileAvailabilityOccurrence,
    CompilerCapabilityProfileAvailabilityLedger,
    DeclaredCapabilityProfileAvailabilityBlocked,
    DeclaredCapabilityProfileAvailabilityReady,
    ProjectCapabilityProfileAvailabilityLedger,
    build_declared_capability_profile_availability,
)
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityDeclaration,
    ExtensionCatalogAvailabilityOwner,
)
from pietto._project.model import (
    ProjectCapabilityEnvironmentConfig,
    ProjectCapabilityProfileDeclaration,
    ProjectCapabilityTargetSelection,
    ProjectConfig,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRoot,
)
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionBlocked,
    CapabilityProfileCompositionSuccess,
    compose_capability_profiles,
)
from pietto.semantic.capability_facts import (
    CapabilityDisposition,
    CapabilityDispositionKind,
    CapabilityEvidence,
    CapabilityEvidenceSource,
    CapabilityFact,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileBaseOccurrence,
    CapabilityProfileFactOccurrence,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileSchemaVersion,
    StaticCapabilityProfile,
)
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)

__all__: tuple[str, ...] = ()

_CONFIG_PATH = "pietto.toml"


@dataclass(frozen=True, slots=True)
class ProjectEvaluatedCapabilityTarget:
    position: int
    database_family: str
    database_release: str
    base_profile: StaticCapabilityProfile
    overlays: tuple[StaticCapabilityProfile, ...]
    composition: CapabilityProfileCompositionSuccess

    def __post_init__(self) -> None:
        if type(self.position) is not int or self.position < 0:
            raise ValueError(
                "Evaluated target requires an exact non-negative position."
            )
        if type(self.database_family) is not str or not self.database_family.strip():
            raise ValueError("Evaluated target requires an exact database family.")
        if type(self.database_release) is not str or not self.database_release.strip():
            raise ValueError("Evaluated target requires an exact database release.")
        if (
            type(self.base_profile) is not StaticCapabilityProfile
            or self.base_profile.kind is not CapabilityProfileKind.BASE
        ):
            raise ValueError("Evaluated target requires an exact BASE profile.")
        if type(self.overlays) is not tuple or any(
            type(profile) is not StaticCapabilityProfile
            or profile.kind is not CapabilityProfileKind.OVERLAY
            for profile in self.overlays
        ):
            raise ValueError(
                "Evaluated target requires exact ordered OVERLAY profiles."
            )
        if type(self.composition) is not CapabilityProfileCompositionSuccess:
            raise ValueError("Evaluated target requires successful exact composition.")
        if (
            self.composition.base is not self.base_profile
            or len(self.composition.overlays) != len(self.overlays)
            or any(
                actual is not expected
                for actual, expected in zip(
                    self.composition.overlays,
                    self.overlays,
                    strict=True,
                )
            )
        ):
            raise ValueError("Evaluated target requires exact composition authority.")
        for profile in (self.base_profile, *self.overlays):
            if (
                profile.target.family != self.database_family
                or profile.target.release != self.database_release
            ):
                raise ValueError(
                    "Evaluated target requires exact profile target agreement."
                )


@dataclass(frozen=True, slots=True)
class ProjectCapabilityEnvironmentAuthority:
    project: ProjectRoot
    config: ProjectConfig
    compiler_profile_availability: CompilerCapabilityProfileAvailabilityLedger
    project_profile_availability: ProjectCapabilityProfileAvailabilityLedger
    profile_availability: DeclaredCapabilityProfileAvailabilityReady
    targets: tuple[ProjectEvaluatedCapabilityTarget, ...]
    extension_catalog_availability: DeclaredExtensionCatalogAvailability

    def __post_init__(self) -> None:
        if type(self.project) is not ProjectRoot:
            raise ValueError("Project capability environment requires an exact root.")
        if (
            type(self.config) is not ProjectConfig
            or self.config.schema_version != 4
            or type(self.config.capability_environment)
            is not ProjectCapabilityEnvironmentConfig
        ):
            raise ValueError("Project capability environment requires exact schema v4.")
        if (
            type(self.compiler_profile_availability)
            is not CompilerCapabilityProfileAvailabilityLedger
            or self.compiler_profile_availability.occurrences
        ):
            raise ValueError(
                "Project capability environment forbids compiler profiles."
            )
        if (
            type(self.project_profile_availability)
            is not ProjectCapabilityProfileAvailabilityLedger
            or self.project_profile_availability.project is not self.project
        ):
            raise ValueError(
                "Project capability environment requires project profiles."
            )
        if (
            type(self.profile_availability)
            is not DeclaredCapabilityProfileAvailabilityReady
            or self.profile_availability.compiler
            is not self.compiler_profile_availability
            or self.profile_availability.project
            is not self.project_profile_availability
        ):
            raise ValueError(
                "Project capability environment requires ready availability."
            )

        declarations = self.config.capability_environment.profiles
        occurrences = self.project_profile_availability.occurrences
        if len(declarations) != len(occurrences) or any(
            declaration.position != occurrence.position
            or declaration.reference != occurrence.reference
            for declaration, occurrence in zip(
                declarations,
                occurrences,
                strict=True,
            )
        ):
            raise ValueError("Project profile availability requires config authority.")
        if type(self.targets) is not tuple or any(
            type(target) is not ProjectEvaluatedCapabilityTarget
            or target.position != position
            for position, target in enumerate(self.targets)
        ):
            raise ValueError("Project capability targets must be dense and ordered.")
        selections = self.config.capability_environment.targets
        if len(selections) != len(self.targets) or any(
            selection.position != target.position
            or selection.database_family != target.database_family
            or selection.database_release != target.database_release
            or selection.base_profile != target.base_profile.profile
            or selection.overlay_profiles
            != tuple(profile.profile for profile in target.overlays)
            for selection, target in zip(selections, self.targets, strict=True)
        ):
            raise ValueError("Evaluated targets require exact config authority.")

        if (
            type(self.extension_catalog_availability)
            is not DeclaredExtensionCatalogAvailability
        ):
            raise ValueError(
                "Project capability environment requires bundled catalogs."
            )
        catalog_declarations = self.extension_catalog_availability.declarations
        expected_catalogs = (
            PGVECTOR_V086_POSTGRESQL18_CATALOG,
            PG_TRGM_V16_POSTGRESQL18_CATALOG,
        )
        if (
            len(catalog_declarations) != len(expected_catalogs)
            or any(
                declaration.catalog is not expected
                for declaration, expected in zip(
                    catalog_declarations,
                    expected_catalogs,
                    strict=True,
                )
            )
            or any(
                declaration.owner is not ExtensionCatalogAvailabilityOwner.COMPILER
                or declaration.project is not None
                for declaration in catalog_declarations
            )
        ):
            raise ValueError(
                "Project capability environment requires bundled catalogs."
            )


@dataclass(frozen=True, slots=True, init=False)
class ProjectCapabilityEnvironmentBuildResult:
    environment: ProjectCapabilityEnvironmentAuthority | None
    errors: tuple[ProjectDiscoveryError, ...]

    def __new__(cls) -> ProjectCapabilityEnvironmentBuildResult:
        raise TypeError(
            "Project capability environment results require canonical build."
        )

    @property
    def ok(self) -> bool:
        return self.environment is not None


def _build_project_capability_environment(
    project: ProjectRoot,
    config: ProjectConfig,
) -> ProjectCapabilityEnvironmentBuildResult:
    if type(project) is not ProjectRoot:
        raise TypeError("Project capability environment requires an exact root.")
    if (
        type(config) is not ProjectConfig
        or config.schema_version != 4
        or type(config.capability_environment) is not ProjectCapabilityEnvironmentConfig
    ):
        raise TypeError("Project capability environment requires exact schema v4.")
    environment_config = config.capability_environment

    profiles = tuple(
        _materialize_project_profile(declaration)
        for declaration in environment_config.profiles
    )
    profile_positions: dict[CapabilityProfileReference, int] = {}
    for position, profile in enumerate(profiles):
        first_position = profile_positions.setdefault(profile.profile, position)
        if first_position != position:
            return _failed(
                "Project capability profile["
                f"{position}] duplicates exact reference from profile[{first_position}]."
            )

    compiler_availability = CompilerCapabilityProfileAvailabilityLedger(())
    project_availability = ProjectCapabilityProfileAvailabilityLedger(
        project,
        tuple(
            CapabilityProfileAvailabilityOccurrence(project, position, profile)
            for position, profile in enumerate(profiles)
        ),
    )
    profile_availability = build_declared_capability_profile_availability(
        compiler_availability,
        project_availability,
    )
    if type(profile_availability) is DeclaredCapabilityProfileAvailabilityBlocked:
        kinds = ",".join(
            blocker.kind.value for blocker in profile_availability.blockers
        )
        return _failed(f"Project capability profile availability blocked: {kinds}.")
    assert type(profile_availability) is DeclaredCapabilityProfileAvailabilityReady

    profiles_by_reference = {profile.profile: profile for profile in profiles}
    evaluated_targets: list[ProjectEvaluatedCapabilityTarget] = []
    first_target_position: dict[
        tuple[
            str,
            str,
            CapabilityProfileReference,
            tuple[CapabilityProfileReference, ...],
        ],
        int,
    ] = {}
    for selection in environment_config.targets:
        base = profiles_by_reference.get(selection.base_profile)
        if base is None:
            return _failed(
                f"Project capability target[{selection.position}] base profile is unresolved."
            )
        if base.kind is not CapabilityProfileKind.BASE:
            return _failed(
                f"Project capability target[{selection.position}] selected a non-BASE base profile."
            )
        agreement_error = _target_agreement_error(selection, base, "base")
        if agreement_error is not None:
            return _failed(agreement_error)

        overlays: list[StaticCapabilityProfile] = []
        first_overlay_position: dict[CapabilityProfileReference, int] = {}
        first_extension_position: dict[str, int] = {}
        for overlay_position, reference in enumerate(selection.overlay_profiles):
            first_position = first_overlay_position.setdefault(
                reference,
                overlay_position,
            )
            if first_position != overlay_position:
                return _failed(
                    f"Project capability target[{selection.position}].overlays["
                    f"{overlay_position}] duplicates overlays[{first_position}]."
                )
            overlay = profiles_by_reference.get(reference)
            if overlay is None:
                return _failed(
                    f"Project capability target[{selection.position}].overlays["
                    f"{overlay_position}] is unresolved."
                )
            if overlay.kind is not CapabilityProfileKind.OVERLAY:
                return _failed(
                    f"Project capability target[{selection.position}].overlays["
                    f"{overlay_position}] selected a non-OVERLAY profile."
                )
            agreement_error = _target_agreement_error(
                selection,
                overlay,
                f"overlays[{overlay_position}]",
            )
            if agreement_error is not None:
                return _failed(agreement_error)
            extension_identity = overlay.target.extension_identity
            assert extension_identity is not None
            first_extension = first_extension_position.setdefault(
                extension_identity,
                overlay_position,
            )
            if first_extension != overlay_position:
                return _failed(
                    f"Project capability target[{selection.position}].overlays["
                    f"{overlay_position}] duplicates extension identity from overlays["
                    f"{first_extension}]."
                )
            overlays.append(overlay)

        composition = compose_capability_profiles(base, tuple(overlays))
        if type(composition) is CapabilityProfileCompositionBlocked:
            return _failed(
                _composition_error(selection.position, composition, profile_positions)
            )
        assert type(composition) is CapabilityProfileCompositionSuccess

        target_identity = (
            selection.database_family,
            selection.database_release,
            selection.base_profile,
            selection.overlay_profiles,
        )
        first_position = first_target_position.setdefault(
            target_identity,
            selection.position,
        )
        if first_position != selection.position:
            return _failed(
                f"Project capability target[{selection.position}] duplicates exact "
                f"selected target[{first_position}]."
            )
        evaluated_targets.append(
            ProjectEvaluatedCapabilityTarget(
                selection.position,
                selection.database_family,
                selection.database_release,
                base,
                tuple(overlays),
                composition,
            )
        )

    extension_catalog_availability = DeclaredExtensionCatalogAvailability(
        (
            ExtensionCatalogAvailabilityDeclaration(
                ExtensionCatalogAvailabilityOwner.COMPILER,
                0,
                PGVECTOR_V086_POSTGRESQL18_CATALOG,
            ),
            ExtensionCatalogAvailabilityDeclaration(
                ExtensionCatalogAvailabilityOwner.COMPILER,
                1,
                PG_TRGM_V16_POSTGRESQL18_CATALOG,
            ),
        )
    )
    environment = ProjectCapabilityEnvironmentAuthority(
        project,
        config,
        compiler_availability,
        project_availability,
        profile_availability,
        tuple(evaluated_targets),
        extension_catalog_availability,
    )
    return _result(environment, ())


def _materialize_project_profile(
    declaration: ProjectCapabilityProfileDeclaration,
) -> StaticCapabilityProfile:
    facts = tuple(
        CapabilityFact(
            fact.key,
            fact.support,
            CapabilityDisposition(CapabilityDispositionKind.NONE),
            (
                CapabilityEvidence(
                    CapabilityEvidenceSource.PROJECT,
                    _CONFIG_PATH,
                    "capability_environment.profiles["
                    f"{declaration.position}].facts[{fact.position}]",
                    dialect=fact.key.dialect,
                    extension=fact.key.extension,
                ),
            ),
        )
        for fact in declaration.facts
    )
    base_occurrences = (
        ()
        if declaration.base is None
        else (
            CapabilityProfileBaseOccurrence(
                declaration.reference,
                0,
                declaration.base,
            ),
        )
    )
    return StaticCapabilityProfile(
        CapabilityProfileSchemaVersion.PROFILE_V1,
        declaration.reference,
        declaration.target,
        declaration.kind,
        base_occurrences,
        tuple(
            CapabilityProfileFactOccurrence(
                declaration.reference,
                fact_declaration.position,
                fact,
            )
            for fact_declaration, fact in zip(
                declaration.facts,
                facts,
                strict=True,
            )
        ),
    )


def _target_agreement_error(
    selection: ProjectCapabilityTargetSelection,
    profile: StaticCapabilityProfile,
    label: str,
) -> str | None:
    if profile.target.family != selection.database_family:
        return (
            f"Project capability target[{selection.position}].{label} database family "
            "does not match the target declaration."
        )
    if profile.target.release != selection.database_release:
        return (
            f"Project capability target[{selection.position}].{label} database release "
            "does not match the target declaration."
        )
    return None


def _composition_error(
    target_position: int,
    composition: CapabilityProfileCompositionBlocked,
    profile_positions: dict[CapabilityProfileReference, int],
) -> str:
    blockers = ";".join(
        blocker.kind.value
        + "@"
        + ",".join(
            str(profile_positions.get(reference, "unresolved"))
            for reference in blocker.reference_chain
        )
        for blocker in composition.blockers
    )
    return (
        f"Project capability target[{target_position}] profile composition blocked: "
        f"{blockers}."
    )


def _failed(message: str) -> ProjectCapabilityEnvironmentBuildResult:
    return _result(
        None,
        (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                message,
                _CONFIG_PATH,
            ),
        ),
    )


def _result(
    environment: ProjectCapabilityEnvironmentAuthority | None,
    errors: tuple[ProjectDiscoveryError, ...],
) -> ProjectCapabilityEnvironmentBuildResult:
    if (environment is None) is (not errors):
        raise ValueError("Project capability environment requires result XOR errors.")
    result = object.__new__(ProjectCapabilityEnvironmentBuildResult)
    object.__setattr__(result, "environment", environment)
    object.__setattr__(result, "errors", errors)
    return result
