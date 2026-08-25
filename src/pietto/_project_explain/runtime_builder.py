"""Private explicit-root Project Explain runtime orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.capability_checking import (
    PackageCapabilityRequirementsChecked,
)
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    PackageCapabilityCheckingMatrix,
    build_package_capability_checking_matrix,
)
from pietto._project.config import load_project_config
from pietto._project.extension_catalog_availability import select_extension_catalog
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFactSet,
    build_extension_catalog_inspection,
)
from pietto._project.extension_signature_provider import (
    ExtensionSignatureProviderContext,
    ExtensionSignatureProviderSelectionOccurrence,
)
from pietto._project.model import (
    ProjectConfig,
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRoot,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    PackageInspectionRejection,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import (
    LoadedPackage,
    _build_package_load_plan,
)
from pietto._project.package_loader import _load_root_package
from pietto._project.package_locator import _locate_root_package
from pietto._project.project_capability_environment import (
    ProjectCapabilityEnvironmentAuthority,
    ProjectEvaluatedCapabilityTarget,
    _build_project_capability_environment,
)
from pietto._project_explain.compatibility_matrix_projection import (
    _project_empty_requirement_target_matrix,
    _project_requirement_target_matrix,
)
from pietto._project_explain.composition import (
    ProjectExplainPayload,
    _compose_project_explain_payload,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    _project_extension_catalog_evidence,
)
from pietto._project_explain.model import (
    ProjectExplainDiagnostic,
    ProjectExplainEnvelope,
    ProjectExplainFormat,
    ProjectExplainLocation,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
)
from pietto._project_explain.package_requirement_projection import (
    _project_package_requirement_provenance,
)
from pietto._project_explain.portability_projection import (
    _derive_project_portability,
)
from pietto.errors import Diagnostic, Severity
from pietto.semantic.capability_facts import (
    CapabilityDomain,
    CapabilityReasonCode,
)
from pietto.semantic.extension_catalog import ExtensionCatalogTarget
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelectors,
)

__all__: tuple[str, ...] = ()

_CONFIG_PATH = "pietto.toml"
_PACKAGE_MANIFEST_PATH = "pietto-package.toml"


class ProjectExplainRuntimeOutcome(StrEnum):
    SUCCESS = "success"
    DIAGNOSTIC_ERROR = "diagnostic_error"
    USAGE_OR_RESOURCE_ERROR = "usage_or_resource_error"


@dataclass(frozen=True, slots=True, init=False)
class ProjectExplainRuntimeBuildResult:
    outcome: ProjectExplainRuntimeOutcome
    envelope: ProjectExplainEnvelope[ProjectExplainPayload]

    def __new__(cls) -> ProjectExplainRuntimeBuildResult:
        raise TypeError("Project Explain runtime results require canonical building.")


def _runtime_result(
    outcome: ProjectExplainRuntimeOutcome,
    envelope: ProjectExplainEnvelope[ProjectExplainPayload],
) -> ProjectExplainRuntimeBuildResult:
    if type(outcome) is not ProjectExplainRuntimeOutcome:
        raise TypeError("Project Explain runtime requires an exact outcome.")
    if type(envelope) is not ProjectExplainEnvelope:
        raise TypeError("Project Explain runtime requires an exact envelope.")
    if (outcome is ProjectExplainRuntimeOutcome.SUCCESS) is (not envelope.ok):
        raise ValueError(
            "Project Explain runtime outcome must agree with its envelope."
        )
    result = object.__new__(ProjectExplainRuntimeBuildResult)
    object.__setattr__(result, "outcome", outcome)
    object.__setattr__(result, "envelope", envelope)
    return result


def _failed(
    outcome: ProjectExplainRuntimeOutcome,
    diagnostics: tuple[ProjectExplainDiagnostic, ...],
) -> ProjectExplainRuntimeBuildResult:
    return _runtime_result(
        outcome,
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=False,
            diagnostics=diagnostics,
            payload=None,
        ),
    )


def _logical_path(
    value: str | None,
    kind: ProjectExplainLogicalPathKind,
) -> ProjectExplainLogicalPath | None:
    if value is None:
        return None
    try:
        return ProjectExplainLogicalPath(kind=kind, value=value)
    except ValueError:
        return None


def _location(
    path: str | None,
    kind: ProjectExplainLogicalPathKind,
    *,
    line: int | None = None,
    column: int | None = None,
    end_line: int | None = None,
    end_column: int | None = None,
) -> ProjectExplainLocation | None:
    logical_path = _logical_path(path, kind)
    if logical_path is None and line is None:
        return None
    return ProjectExplainLocation(
        path=logical_path,
        line=line,
        column=column,
        end_line=end_line,
        end_column=end_column,
    )


def _project_error_diagnostic(
    error: ProjectDiscoveryError,
    kind: ProjectExplainLogicalPathKind,
) -> ProjectExplainDiagnostic:
    return ProjectExplainDiagnostic(
        code=error.kind.value,
        severity=Severity.ERROR,
        message=error.message,
        location=_location(error.path, kind),
        suggestion=None,
    )


def _source_diagnostic(
    diagnostic: Diagnostic,
    kind: ProjectExplainLogicalPathKind,
) -> ProjectExplainDiagnostic:
    location = diagnostic.location
    return ProjectExplainDiagnostic(
        code=diagnostic.code,
        severity=diagnostic.severity,
        message=diagnostic.message,
        location=_location(
            location.path,
            kind,
            line=location.line,
            column=location.column,
            end_line=location.end_line,
            end_column=location.end_column,
        ),
        suggestion=diagnostic.suggestion,
    )


def _runtime_diagnostic(
    reason: CapabilityReasonCode,
    message: str,
    *,
    path: str = _PACKAGE_MANIFEST_PATH,
    path_kind: ProjectExplainLogicalPathKind = (
        ProjectExplainLogicalPathKind.PACKAGE_RELATIVE
    ),
) -> ProjectExplainDiagnostic:
    return ProjectExplainDiagnostic(
        code=reason.value,
        severity=Severity.ERROR,
        message=message,
        location=_location(path, path_kind),
        suggestion=None,
    )


def _package_inspection_diagnostics(
    facts: PackageInspectionFactSet,
) -> tuple[ProjectExplainDiagnostic, ...]:
    inspection = facts.inspection
    diagnostics: list[ProjectExplainDiagnostic] = [
        _project_error_diagnostic(
            error.error,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
        )
        for error in inspection.errors
    ]
    diagnostics.extend(
        _source_diagnostic(
            diagnostic.diagnostic,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
        )
        for diagnostic in inspection.diagnostics
    )
    diagnostics.extend(
        _rejection_diagnostic(rejection) for rejection in inspection.rejections
    )
    return tuple(diagnostics)


def _rejection_diagnostic(
    rejection: PackageInspectionRejection,
) -> ProjectExplainDiagnostic:
    return ProjectExplainDiagnostic(
        code=rejection.kind.value,
        severity=Severity.ERROR,
        message=rejection.message,
        location=None,
        suggestion=None,
    )


def _provider_context(
    package_position: int,
    selectors: ExtensionSignatureRequirementSelectors | None,
    target: ProjectEvaluatedCapabilityTarget,
    environment: ProjectCapabilityEnvironmentAuthority,
) -> tuple[
    ExtensionSignatureProviderContext | None,
    tuple[ProjectExplainDiagnostic, ...],
]:
    if selectors is None or not selectors.occurrences:
        return None, ()
    selections: list[ExtensionSignatureProviderSelectionOccurrence] = []
    diagnostics: list[ProjectExplainDiagnostic] = []
    for selector_occurrence in selectors.occurrences:
        requirement = selectors.requirements.occurrences[
            selector_occurrence.requirement_position
        ]
        extension_identity = requirement.key.extension
        assert extension_identity is not None
        overlays = tuple(
            profile
            for profile in target.overlays
            if profile.target.extension_identity == extension_identity
        )
        if len(overlays) != 1:
            diagnostics.append(
                _runtime_diagnostic(
                    CapabilityReasonCode.EXTENSION_CATALOG_TARGET_MISMATCH,
                    "Project Explain package["
                    f"{package_position}] target[{target.position}] requirement["
                    f"{requirement.position}] has no exact project-owned extension "
                    "release authority.",
                    path=_CONFIG_PATH,
                    path_kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                )
            )
            continue
        extension_release = overlays[0].target.extension_release
        assert extension_release is not None
        selection = select_extension_catalog(
            environment.extension_catalog_availability,
            ExtensionCatalogTarget(
                target.database_family,
                target.database_release,
                extension_identity,
                extension_release,
            ),
            environment.project,
        )
        selections.append(
            ExtensionSignatureProviderSelectionOccurrence(
                requirement.position,
                selection,
            )
        )
    if diagnostics:
        return None, tuple(diagnostics)
    return ExtensionSignatureProviderContext(selectors, tuple(selections)), ()


def _package_contexts(
    package_position: int,
    binding: PackageCapabilityRequirementBinding | None,
    selectors: ExtensionSignatureRequirementSelectors | None,
    environment: ProjectCapabilityEnvironmentAuthority,
) -> tuple[
    tuple[CapabilityCheckingTargetContext, ...],
    tuple[ProjectExplainDiagnostic, ...],
]:
    extension_requirements = (
        ()
        if binding is None
        else tuple(
            occurrence
            for occurrence in binding.requirements.occurrences
            if occurrence.key.domain is CapabilityDomain.EXTENSION_SIGNATURE
        )
    )
    if environment.targets and extension_requirements and selectors is None:
        return (), (
            _runtime_diagnostic(
                CapabilityReasonCode.NOT_EVIDENCED,
                "Project Explain package["
                f"{package_position}] has EXTENSION_SIGNATURE requirements without "
                "schema-v3 typed selector authority.",
            ),
        )
    contexts: list[CapabilityCheckingTargetContext] = []
    diagnostics: list[ProjectExplainDiagnostic] = []
    for target in environment.targets:
        provider_context, target_diagnostics = _provider_context(
            package_position,
            selectors,
            target,
            environment,
        )
        diagnostics.extend(target_diagnostics)
        if not target_diagnostics:
            contexts.append(
                CapabilityCheckingTargetContext(
                    target.position,
                    target.composition,
                    environment.profile_availability,
                    provider_context,
                )
            )
    return tuple(contexts), tuple(diagnostics)


def _extension_catalog_fact_slots(
    matrices: tuple[PackageCapabilityCheckingMatrix, ...],
) -> tuple[ExtensionCatalogInspectionFactSet | None, ...]:
    return tuple(
        (
            build_extension_catalog_inspection(provider_context)
            if type(column.result) is PackageCapabilityRequirementsChecked
            and provider_context is not None
            and provider_context.selectors.occurrences
            else None
        )
        for matrix in matrices
        for column in matrix.columns
        for provider_context in (column.context.extension_signature_provider_context,)
    )


def _build_project_explain_runtime(
    project_root: str | Path,
) -> ProjectExplainRuntimeBuildResult:
    """Build one complete Project Explain envelope from one explicit root."""

    config_result = load_project_config(project_root)
    if not config_result.ok:
        return _failed(
            ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR,
            tuple(
                _project_error_diagnostic(
                    error,
                    ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                )
                for error in config_result.errors
            ),
        )
    project = config_result.root
    config = config_result.config
    pinned_root = config_result.pinned_root
    assert type(project) is ProjectRoot
    assert type(config) is ProjectConfig
    assert pinned_root is not None
    if config.schema_version != 4:
        return _failed(
            ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR,
            (
                _project_error_diagnostic(
                    ProjectDiscoveryError(
                        ProjectDiscoveryErrorKind.CONFIG_SCHEMA,
                        "Project Explain runtime requires project schema version 4.",
                        _CONFIG_PATH,
                    ),
                    ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                ),
            ),
        )
    activation = config.root_package
    assert activation is not None
    location_result = _locate_root_package(pinned_root, activation)
    if not location_result.ok:
        return _failed(
            ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR,
            tuple(
                _project_error_diagnostic(
                    error,
                    ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                )
                for error in location_result.errors
            ),
        )
    located_root = location_result.located_root
    assert located_root is not None
    load_result = _load_root_package(located_root)
    if not load_result.ok:
        load_diagnostics = tuple(
            _project_error_diagnostic(
                error,
                ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
            )
            for error in load_result.errors
        ) + tuple(
            _source_diagnostic(
                diagnostic,
                ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
            )
            for diagnostic in load_result.diagnostics
        )
        return _failed(
            (
                ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR
                if load_result.errors
                else ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
            ),
            load_diagnostics,
        )
    root_package = load_result.loaded_package
    assert root_package is not None
    root_diagnostics = tuple(
        _source_diagnostic(
            diagnostic,
            ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
        )
        for diagnostic in load_result.diagnostics
    )
    plan_result = _build_package_load_plan(root_package)
    package_facts = _build_package_inspection_fact_set(plan_result)
    if package_facts.inspection.outcome is not PackageInspectionOutcome.SUCCESS:
        package_diagnostics = root_diagnostics + _package_inspection_diagnostics(
            package_facts
        )
        return _failed(
            (
                ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR
                if package_facts.inspection.errors
                else ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR
            ),
            package_diagnostics,
        )

    environment_result = _build_project_capability_environment(project, config)
    prior_diagnostics = root_diagnostics + _package_inspection_diagnostics(
        package_facts
    )
    if not environment_result.ok:
        return _failed(
            ProjectExplainRuntimeOutcome.USAGE_OR_RESOURCE_ERROR,
            prior_diagnostics
            + tuple(
                _project_error_diagnostic(
                    error,
                    ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
                )
                for error in environment_result.errors
            ),
        )
    environment = environment_result.environment
    assert environment is not None
    packages: tuple[LoadedPackage, ...] = tuple(
        package.entry.package for package in package_facts.inspection.packages
    )
    bindings = tuple(
        _package_capability_requirement_binding(package) for package in packages
    )
    selectors = tuple(
        _package_extension_signature_requirement_selectors(package, binding)
        for package, binding in zip(packages, bindings, strict=True)
    )
    contexts: list[tuple[CapabilityCheckingTargetContext, ...]] = []
    runtime_diagnostics: list[ProjectExplainDiagnostic] = []
    for package_position, (binding, package_selectors) in enumerate(
        zip(bindings, selectors, strict=True)
    ):
        package_contexts, context_diagnostics = _package_contexts(
            package_position,
            binding,
            package_selectors,
            environment,
        )
        contexts.append(package_contexts)
        runtime_diagnostics.extend(context_diagnostics)
    if runtime_diagnostics:
        return _failed(
            ProjectExplainRuntimeOutcome.DIAGNOSTIC_ERROR,
            prior_diagnostics + tuple(runtime_diagnostics),
        )

    matrices = tuple(
        build_package_capability_checking_matrix(package, binding, package_contexts)
        for package, binding, package_contexts in zip(
            packages,
            bindings,
            contexts,
            strict=True,
        )
    )
    capability_facts: tuple[CapabilityInspectionFactSet, ...] = tuple(
        build_capability_inspection(matrix) for matrix in matrices
    )
    package_projection = _project_package_requirement_provenance(
        package_facts,
        capability_facts,
    )
    compatibility = (
        _project_requirement_target_matrix(
            package_projection,
            package_facts,
            capability_facts,
        )
        if environment.targets
        else _project_empty_requirement_target_matrix(package_projection)
    )
    extension_catalog_facts = (
        _extension_catalog_fact_slots(matrices) if environment.targets else ()
    )
    extension_catalog_evidence = _project_extension_catalog_evidence(
        package_projection,
        compatibility,
        package_facts,
        capability_facts,
        extension_catalog_facts,
    )
    portability = _derive_project_portability(package_projection, compatibility)
    payload = _compose_project_explain_payload(
        package_projection,
        compatibility,
        extension_catalog_evidence,
        portability,
    )
    return _runtime_result(
        ProjectExplainRuntimeOutcome.SUCCESS,
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=prior_diagnostics,
            payload=payload,
        ),
    )
