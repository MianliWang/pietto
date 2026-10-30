"""Private JSON v2 serializers for project check results."""

from __future__ import annotations

import json
from dataclasses import asdict
from collections.abc import Mapping, Sequence
from types import MappingProxyType

from pietto import cli_json
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryResult,
    ProjectInput,
    ProjectParseCheckResult,
    ProjectSemanticResult,
)
from pietto.errors import Diagnostic, SourceLocation

type RelatedLocations = Mapping[Diagnostic, tuple[SourceLocation, ...]]

_PROJECT_JSON_V2_VERSION = 2
_COMMAND = "check"
_MODE = "project"
_JSON_INPUT_KIND = "source"
_JSON_INPUT_STATUSES = frozenset({"parsed", "error"})


def project_check_result_to_json_dict(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
    *,
    semantic_diagnostics: Sequence[Diagnostic] = (),
    related_locations: RelatedLocations = MappingProxyType({}),
) -> dict[str, object]:
    """Build one project JSON v2 check result."""

    if isinstance(result, ProjectParseCheckResult):
        # A check that stops before semantics carries its module facts.
        related_locations = {**module_related_locations(result), **related_locations}
    inputs = _inputs_to_json_list(result)
    diagnostics = _diagnostics_to_json_list(
        result,
        semantic_diagnostics=semantic_diagnostics,
        related_locations=related_locations,
    )
    counters = _check_counters(inputs, diagnostics)

    return {
        "schema_version": _PROJECT_JSON_V2_VERSION,
        "command": _COMMAND,
        "mode": _MODE,
        "ok": result.ok and not _has_error_diagnostics(semantic_diagnostics),
        "project": _project_to_json_dict(result),
        "inputs": inputs,
        "diagnostics": diagnostics,
        "cli_errors": [_cli_error_to_json_dict(error) for error in result.errors],
        "result": {
            "check": counters,
        },
    }


def module_related_locations(
    result: ProjectParseCheckResult | ProjectSemanticResult,
) -> RelatedLocations:
    """The related locations the explicit-module graph, binding and resolution
    owners computed for each diagnostic they emitted, in their order."""

    related: dict[Diagnostic, tuple[SourceLocation, ...]] = {}
    pairs: list[tuple[Diagnostic | None, tuple[SourceLocation, ...]]] = []
    if result.module_diagnostic_facts is not None:
        pairs.extend(
            (fact.diagnostic, fact.related_locations)
            for fact in result.module_diagnostic_facts.facts
        )
    if isinstance(result, ProjectSemanticResult):
        for resolutions in (
            result.module_type_source_resolutions,
            result.module_relation_resolutions,
        ):
            if resolutions is not None:
                pairs.extend(
                    (issue.diagnostic, issue.related_locations)
                    for issue in resolutions.issues
                )
    for diagnostic, locations in pairs:
        if diagnostic is not None and locations:
            related[diagnostic] = tuple(
                dict.fromkeys((*related.get(diagnostic, ()), *locations))
            )
    return MappingProxyType(related)


def render_project_json_document(document: Mapping[str, object]) -> str:
    """Render exactly one ASCII project JSON v2 document plus one newline."""

    return f"{json.dumps(document, ensure_ascii=True)}\n"


def _project_to_json_dict(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> dict[str, object]:
    root = result.root.path if result.root is not None else None
    config_path = result.config_path.path if result.config_path is not None else None
    return {
        "root": root,
        "config_path": config_path,
    }


def _inputs_to_json_list(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
) -> list[dict[str, object]]:
    if isinstance(result, ProjectDiscoveryResult):
        if result.inputs:
            raise ValueError(
                "project input JSON serialization requires parse-only project check"
            )
        return []

    inputs: list[dict[str, object]] = []
    for project_input in result.inputs:
        if project_input.status not in _JSON_INPUT_STATUSES:
            if result.errors:
                return []
            raise ValueError(
                f"project input status is not JSON-reportable: {project_input.status}"
            )
        inputs.append(_input_to_json_dict(project_input))
    return inputs


def _input_to_json_dict(project_input: ProjectInput) -> dict[str, object]:
    return {
        "path": project_input.path,
        "kind": _JSON_INPUT_KIND,
        "status": project_input.status,
    }


def _diagnostics_to_json_list(
    result: ProjectDiscoveryResult | ProjectParseCheckResult,
    *,
    semantic_diagnostics: Sequence[Diagnostic],
    related_locations: RelatedLocations,
) -> list[dict[str, object]]:
    if not isinstance(result, ProjectParseCheckResult):
        return []
    return [
        _diagnostic_to_json_dict(diagnostic, related_locations.get(diagnostic, ()))
        for diagnostic in (*result.diagnostics, *semantic_diagnostics)
    ]


def _has_error_diagnostics(diagnostics: Sequence[Diagnostic]) -> bool:
    return any(diagnostic.severity.value == "error" for diagnostic in diagnostics)


def _diagnostic_to_json_dict(
    diagnostic: Diagnostic,
    related_locations: tuple[SourceLocation, ...],
) -> dict[str, object]:
    diagnostic_json = cli_json.diagnostic_to_json_dict(diagnostic)
    diagnostic_json["related_locations"] = [
        {"message": None, "location": asdict(location)}
        for location in related_locations
    ]
    return diagnostic_json


def _check_counters(
    inputs: list[dict[str, object]],
    diagnostics: list[dict[str, object]],
) -> dict[str, int]:
    """Count the inputs with an error: a failed parse or read, or the primary
    location of any error diagnostic, parse or semantic."""

    error_paths = {
        location["path"]
        for diagnostic in diagnostics
        if diagnostic["severity"] == "error"
        and isinstance(location := diagnostic["location"], dict)
    }
    files_with_errors = sum(
        1
        for project_input in inputs
        if project_input["status"] == "error" or project_input["path"] in error_paths
    )
    return {
        "files_total": len(inputs),
        "files_ok": len(inputs) - files_with_errors,
        "files_with_errors": files_with_errors,
    }


def _cli_error_to_json_dict(error: ProjectDiscoveryError) -> dict[str, object]:
    return {
        "kind": error.kind.value,
        "message": error.message,
        "path": error.path,
    }
