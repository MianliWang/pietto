"""Deterministic human rendering for Project Explain envelopes."""

from __future__ import annotations

from pietto._project_explain.compatibility_matrix_projection import (
    ProjectExplainCapabilityProfile,
    ProjectExplainLookupSummary,
)
from pietto._project_explain.composition import (
    ProjectExplainArtifactReference,
    ProjectExplainPayload,
)
from pietto._project_explain.extension_catalog_evidence_projection import (
    ProjectExplainExtensionCatalogCallableIdentity,
    ProjectExplainExtensionCatalogCastIdentity,
    ProjectExplainExtensionCatalogOperatorIdentity,
    ProjectExplainExtensionCatalogSelector,
    ProjectExplainExtensionCatalogTypeReference,
)
from pietto._project_explain.model import (
    PROJECT_EXPLAIN_ARTIFACT_NAME,
    ProjectExplainDiagnostic,
    ProjectExplainEnvelope,
)
from pietto._project_explain.package_requirement_projection import (
    ProjectExplainCapabilityKey,
)

__all__: tuple[str, ...] = ()


def _text(value: str | None) -> str:
    if value is None:
        return "-"
    escaped: list[str] = []
    for character in value:
        if character == "\\":
            escaped.append("\\\\")
        elif character == "\t":
            escaped.append("\\t")
        elif character == "\n":
            escaped.append("\\n")
        elif character == "\r":
            escaped.append("\\r")
        elif ord(character) < 0x20 or character == "\x7f":
            escaped.append(f"\\x{ord(character):02x}")
        else:
            escaped.append(character)
    return "".join(escaped)


def _positions(values: tuple[int, ...]) -> str:
    return "[" + ",".join(str(value) for value in values) + "]"


def _reference(reference: ProjectExplainArtifactReference) -> str:
    return f"{reference.kind.value}{_positions(reference.positions)}"


def _key(key: ProjectExplainCapabilityKey) -> str:
    operands = "[" + ",".join(_text(value) for value in key.operands) + "]"
    return (
        f"domain={key.domain.value} subject={_text(key.subject)} "
        f"operation={_text(key.operation)} operands={operands} "
        f"context={_text(key.context)} dialect={_text(key.dialect)} "
        f"extension={_text(key.extension)}"
    )


def _profile(profile: ProjectExplainCapabilityProfile) -> str:
    extension = (
        ""
        if profile.extension_identity is None
        else " extension="
        f"{_text(profile.extension_identity)}@{_text(profile.extension_release)}"
    )
    return (
        f"{_text(profile.namespace)}/{_text(profile.name)}"
        f"@{_text(profile.profile_release)} kind={profile.kind.value} "
        f"target={_text(profile.database_family)}@{_text(profile.target_release)}"
        f"{extension}"
    )


def _lookup(lookup: ProjectExplainLookupSummary) -> str:
    supports = "[" + ",".join(value.value for value in lookup.supports) + "]"
    return f"{lookup.variant.value} reason={_text(lookup.reason)} supports={supports}"


def _type_reference(reference: ProjectExplainExtensionCatalogTypeReference) -> str:
    if reference.logical_name is not None:
        assert reference.logical_kind is not None
        return (
            f"{reference.kind.value}:{_text(reference.logical_name)}"
            f"/{reference.logical_kind.value}"
        )
    owner = (
        ""
        if reference.extension_identity is None
        else f" owner={_text(reference.extension_identity)}"
    )
    return f"{reference.kind.value}:{_text(reference.physical_name)}{owner}"


def _selector(selector: ProjectExplainExtensionCatalogSelector) -> str:
    identity = selector.identity
    if isinstance(identity, ProjectExplainExtensionCatalogTypeReference):
        rendered = _type_reference(identity)
    elif isinstance(identity, ProjectExplainExtensionCatalogCallableIdentity):
        rendered = (
            f"{_text(identity.sql_name)}("
            + ",".join(_type_reference(value) for value in identity.input_types)
            + ")"
        )
    elif isinstance(identity, ProjectExplainExtensionCatalogOperatorIdentity):
        rendered = (
            f"{_text(identity.operator_name)}/{identity.arity.value}("
            + ",".join(_type_reference(value) for value in identity.operand_types)
            + ")"
        )
    elif isinstance(identity, ProjectExplainExtensionCatalogCastIdentity):
        rendered = (
            f"{_type_reference(identity.source_type)}"
            f"->{_type_reference(identity.target_type)}"
        )
    else:
        raise TypeError("Project Explain text requires an exact selector identity.")
    return f"{selector.family.value}:{rendered}"


def _diagnostic(diagnostic: ProjectExplainDiagnostic, position: int) -> str:
    location = diagnostic.location
    if location is None:
        rendered_location = "-"
    else:
        rendered_location = "-" if location.path is None else _text(location.path.value)
        if location.line is not None:
            rendered_location += f":{location.line}:{location.column}"
    suggestion = (
        ""
        if diagnostic.suggestion is None
        else f" suggestion={_text(diagnostic.suggestion)}"
    )
    return (
        f"  [{position}] {diagnostic.severity.value} {_text(diagnostic.code)} "
        f"at={rendered_location}: {_text(diagnostic.message)}{suggestion}"
    )


def _render_packages(lines: list[str], payload: ProjectExplainPayload) -> None:
    section = payload.package_requirements
    lines.extend(("", f"Packages ({len(section.packages)})"))
    for package in section.packages:
        coordinate = package.coordinate
        lines.append(
            f"  [{package.position}] {package.role.value} "
            f"{_text(coordinate.namespace)}/{_text(coordinate.name)}"
            f"@{_text(coordinate.release)} project_path={_text(package.project_path.value)} "
            f"content_sha256={package.content_digest}"
        )
        lines.append(f"    Assets ({len(package.assets)})")
        if not package.assets:
            lines.append("      none")
        for asset in package.assets:
            lines.append(
                f"      [{asset.position}] {asset.kind.value} {_text(asset.path.value)}"
            )
        lines.append(f"    Dependencies ({len(package.dependencies)})")
        if not package.dependencies:
            lines.append("      none")
        for dependency in package.dependencies:
            coordinate = dependency.coordinate
            lines.append(
                f"      [{dependency.position}] package[{dependency.target_package_position}] "
                f"{_text(coordinate.namespace)}/{_text(coordinate.name)}"
                f"@{_text(coordinate.release)} locator={dependency.locator_kind.value} "
                f"project_path={_text(dependency.project_path.value)} "
                f"sha256={dependency.content_digest_pin}"
            )


def _render_requirements(lines: list[str], payload: ProjectExplainPayload) -> None:
    section = payload.package_requirements
    lines.extend(("", "Capability Requirements"))
    lines.append(f"  Collections ({len(section.requirement_collections)})")
    if not section.requirement_collections:
        lines.append("    none")
    for collection in section.requirement_collections:
        lines.append(
            f"    package[{collection.declared_by}] requested_by=package["
            f"{collection.requested_by}] role={collection.package_role.value} "
            f"identity={_text(collection.identity.namespace)}/"
            f"{_text(collection.identity.name)} "
            f"requirements={_positions(collection.requirement_positions)}"
        )
    lines.append(f"  Requests ({len(section.requirements)})")
    if not section.requirements:
        lines.append("    none")
    for request in section.requirements:
        lines.append(
            f"    [{request.position}] package[{request.declared_by}] "
            f"requested_by=package[{request.requested_by}] "
            f"occurrence={request.occurrence_position} {_key(request.key)}"
        )


def _render_compatibility(lines: list[str], payload: ProjectExplainPayload) -> None:
    section = payload.compatibility
    lines.extend(("", "Compatibility"))
    lines.append(f"  Targets ({len(section.targets)})")
    if not section.targets:
        lines.append("    none")
    for target in section.targets:
        overlays = (
            "[" + ",".join(_profile(value) for value in target.supplied_overlays) + "]"
        )
        lines.append(
            f"    [{target.position}] {_text(target.database_family)}"
            f"@{_text(target.database_release)} base={_profile(target.base_profile)} "
            f"overlays={overlays}"
        )
    lines.append(
        f"  Package Target Evaluations ({len(section.package_target_evaluations)})"
    )
    if not section.package_target_evaluations:
        lines.append("    none")
    for evaluation in section.package_target_evaluations:
        lines.append(
            f"    package[{evaluation.package_position}] target["
            f"{evaluation.target_position}] state={evaluation.state.value} "
            f"posture={evaluation.evidence_posture.value} "
            f"availability={len(evaluation.availability)} blockers={len(evaluation.blockers)}"
        )
    lines.append(f"  Matrix Rows ({len(section.rows)})")
    if not section.rows:
        lines.append("    none")
    for row in section.rows:
        lines.append(f"    requirement[{row.requirement_position}]")
        if not row.cells:
            lines.append("      cells: none")
        for cell in row.cells:
            detail = ""
            if cell.checked_evidence is not None:
                evidence = cell.checked_evidence
                detail = (
                    f" target_lookup=({_lookup(evidence.target_lookup)})"
                    f" provider_complete={str(evidence.provider_domain_complete).lower()}"
                    f" provider_unknown={_text(evidence.provider_unknown_reason)}"
                    f" provider_lookup=({_lookup(evidence.provider_lookup)})"
                )
            status = "-" if cell.checked_status is None else cell.checked_status.value
            lines.append(
                f"      target[{cell.target_position}] state={cell.state.value} "
                f"status={status} posture={cell.evidence_posture.value}{detail}"
            )


def _render_catalogs(lines: list[str], payload: ProjectExplainPayload) -> None:
    contexts = payload.extension_catalog_evidence.contexts
    lines.extend(("", f"Extension Catalog Evidence ({len(contexts)})"))
    if not contexts:
        lines.append("  none")
    for context in contexts:
        lines.append(
            f"  package[{context.package_position}] target[{context.target_position}] "
            f"collection={_text(context.collection.namespace)}/"
            f"{_text(context.collection.name)}"
        )
        lines.append(f"    Catalogs ({len(context.catalogs)})")
        if not context.catalogs:
            lines.append("      none")
        for catalog in context.catalogs:
            reference = catalog.reference
            target = catalog.target
            lines.append(
                f"      [{catalog.position}] {_text(reference.namespace)}/"
                f"{_text(reference.name)}@{_text(reference.release)} "
                f"target={_text(target.database_family)}@{_text(target.database_release)} "
                f"extension={_text(target.extension_identity)}@"
                f"{_text(target.extension_release)} sha256={catalog.content_sha256} "
                f"sources={len(catalog.source_occurrences)}"
            )
        lines.append(f"    Requirements ({len(context.requirements)})")
        for requirement in context.requirements:
            exact_group = (
                "-"
                if requirement.exact_group is None
                else requirement.exact_group.state.value
            )
            completeness = (
                "-"
                if requirement.completeness is None
                else requirement.completeness.state.value
            )
            lines.append(
                f"      requirement[{requirement.requirement_position}] "
                f"selector={_selector(requirement.selector)} "
                f"selection={requirement.selection.outcome.value} "
                f"selected_catalog={_text(None if requirement.selected_catalog_position is None else str(requirement.selected_catalog_position))} "
                f"exact_group={exact_group} unmodeled={len(requirement.unmodeled_blockers)} "
                f"completeness={completeness}"
            )


def _render_portability(lines: list[str], payload: ProjectExplainPayload) -> None:
    portability = payload.portability
    lines.extend(("", "Portability"))
    lines.append(
        f"  project: {portability.classification.value} "
        f"reason={_text(None if portability.reason is None else portability.reason.value)} "
        f"requirements={portability.requirements_evaluated}"
    )
    lines.append(f"  Requirements ({len(portability.requirements)})")
    if not portability.requirements:
        lines.append("    none")
    for requirement in portability.requirements:
        gaps = (
            "["
            + ",".join(
                f"target[{gap.target_position}]={gap.status.value}"
                for gap in requirement.definite_gaps
            )
            + "]"
        )
        lines.append(
            f"    [{requirement.requirement_position}] "
            f"{requirement.classification.value} "
            f"reason={_text(None if requirement.reason is None else requirement.reason.value)} "
            f"definite_gaps={gaps}"
        )


def _render_explanations(lines: list[str], payload: ProjectExplainPayload) -> None:
    explanations = payload.requirement_explanations
    lines.extend(("", f"Requirement Explanations ({len(explanations)})"))
    if not explanations:
        lines.append("  none")
    for position, explanation in enumerate(explanations):
        lines.append(
            f"  [{position}] request={_reference(explanation.request)} "
            f"declared_by={_reference(explanation.declared_by)} "
            f"requested_by={_reference(explanation.requested_by)} "
            f"portability={_reference(explanation.portability)}"
        )
        if not explanation.targets:
            lines.append("    targets: none")
        for target in explanation.targets:
            extension = (
                "-"
                if target.extension_evidence is None
                else _reference(target.extension_evidence)
            )
            sources = (
                "["
                + ",".join(
                    _reference(reference) for reference in target.source_evidence
                )
                + "]"
            )
            lines.append(
                f"    target={_reference(target.target)} "
                f"evaluation={_reference(target.evaluation)} "
                f"cell={_reference(target.matrix_cell)} "
                f"extension={extension} sources={sources}"
            )


def render_project_explain_text(
    envelope: ProjectExplainEnvelope[ProjectExplainPayload],
) -> str:
    """Render one exact Project Explain envelope with one final LF."""

    if type(envelope) is not ProjectExplainEnvelope:
        raise TypeError("Project Explain text requires an exact envelope.")
    envelope.__post_init__()
    lines = [
        PROJECT_EXPLAIN_ARTIFACT_NAME,
        f"format: {envelope.format.value}",
        f"status: {'success' if envelope.ok else 'failure'}",
        "",
        f"Diagnostics ({len(envelope.diagnostics)})",
    ]
    if not envelope.diagnostics:
        lines.append("  none")
    else:
        lines.extend(
            _diagnostic(diagnostic, position)
            for position, diagnostic in enumerate(envelope.diagnostics)
        )
    if not envelope.ok:
        lines.extend(("", "Payload", "  unavailable"))
        return "\n".join(lines) + "\n"
    payload = envelope.payload
    if type(payload) is not ProjectExplainPayload:
        raise TypeError("Successful Project Explain text requires an exact payload.")
    _render_packages(lines, payload)
    _render_requirements(lines, payload)
    _render_compatibility(lines, payload)
    _render_catalogs(lines, payload)
    _render_portability(lines, payload)
    _render_explanations(lines, payload)
    return "\n".join(lines) + "\n"
