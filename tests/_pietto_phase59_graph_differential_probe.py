"""Emit one exact Phase 59 private-graph differential observation."""

from __future__ import annotations

import argparse
import hashlib
from importlib.metadata import version
import json
import os
from pathlib import Path
import subprocess
import sys

from _pietto_project_explain_scenarios import (
    EXTENSION_REQUIREMENT,
    EXTENSION_SELECTOR,
    _fact,
    _manifest,
    _profile,
    _project_config,
    _target,
    _write_package,
)
import pietto._project.check as project_check
import pietto._project_explain.runtime_builder as runtime_builder
from pietto._project.capability_inspection import (
    CapabilityInspectionFactSet,
    build_capability_inspection,
)
from pietto._project.capability_matrix import (
    CapabilityCheckingTargetContext,
    build_package_capability_checking_matrix,
)
from pietto._project.config import load_project_config
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.module_package_neutral_identity import (
    ProjectModulePackageNeutralIdentityFactSet,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_graph import (
    PackageGraphOutcome,
    PackageGraphSnapshot,
    _build_package_graph,
)
from pietto._project.package_graph_inspection import (
    PackageGraphInspection,
    PackageGraphInspectionField,
    PackageGraphInspectionLink,
    PackageGraphInspectionLinkKind,
    PackageGraphInspectionRecord,
    PackageGraphInspectionRecordKind,
    PackageGraphInspectionRef,
    PackageGraphInspectionState,
    PackageGraphInspectionStateKind,
    PackageGraphPureStatus,
    _evaluate_package_graph_inspection,
    _inspect_package_graph,
    _inspection_ref,
    _query_package_graph_direct_downstream,
    _query_package_graph_direct_upstream,
    _query_package_graph_paths,
    _query_package_graph_why_not,
    _validate_package_graph_integrity,
)
from pietto._project.package_inspection import (
    PackageInspectionFactSet,
    PackageInspectionOutcome,
    _build_package_inspection_fact_set,
)
from pietto._project.package_load_plan import LoadedPackage, _build_package_load_plan
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.project_capability_environment import (
    _build_project_capability_environment,
)
from pietto._project_explain.json_v1 import serialize_project_explain_json_document
from pietto._project_explain.runtime_builder import ProjectExplainRuntimeOutcome
from pietto._project_explain.text import render_project_explain_text


OBSERVATION_FORMAT = "pietto.package-graph-differential.v1"
LOGICAL_REQUIREMENT = """[[capability_requirements.entries]]
domain = "logical_type"
subject = "Int"
operands = []"""
MODULE_SOURCE = (
    "shape Row:\n"
    "    id: Int not null\n"
    "    amount: Int not null\n"
    "    quantity: Int not null\n"
    "    category: Text nullable\n"
    'source rows: Row is postgres.table("rows")\n'
    "query projections:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        renamed = amount\n"
    "query calculations:\n"
    "    from rows\n"
    "    let:\n"
    "        gross = amount * quantity\n"
    "    select:\n"
    "        doubled = amount + amount\n"
    "        gross\n"
    "query aggregates:\n"
    "    from rows\n"
    "    select:\n"
    "        total = sum(amount + amount)\n"
    "query windows:\n"
    "    from rows\n"
    "    select:\n"
    "        id\n"
    "        previous = lag(amount, 2, amount) window:\n"
    "            partition by:\n"
    "                category\n"
    "            order by:\n"
    "                id desc\n"
).encode()
_CLI_CODE = (
    "import sys\nfrom pietto.cli import main\nraise SystemExit(main(sys.argv[1:]))\n"
)


def _write_semantic_config(package_root: Path) -> None:
    (package_root / "pietto.toml").write_text(
        'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )


def _write_real_project(workspace: Path, name: str) -> Path:
    project = workspace / name
    dependency_manifest = _manifest(
        3,
        namespace="example",
        name="dependency",
        requirements=(EXTENSION_REQUIREMENT, LOGICAL_REQUIREMENT),
        selectors=(EXTENSION_SELECTOR,),
    )
    dependency_digest = _write_package(
        project / "dependency",
        dependency_manifest,
        MODULE_SOURCE,
    )
    root_manifest = _manifest(
        1,
        dependencies=(
            (
                "example",
                "dependency",
                "1.0.0",
                dependency_digest,
                "../dependency",
            ),
        ),
    )
    root_digest = _write_package(project / "root", root_manifest, MODULE_SOURCE)
    _write_semantic_config(project / "dependency")
    _write_semantic_config(project / "root")
    extension_fact = _fact(
        "supported",
        "extension_signature",
        operation="vector-native-type",
        dialect="postgresql",
        extension="vector",
    )
    (project / "pietto.toml").write_text(
        _project_config(
            "root",
            root_digest,
            profiles=(
                _profile("base", "18"),
                _profile(
                    "vector",
                    "18",
                    kind="overlay",
                    facts=(extension_fact,),
                ),
            ),
            targets=(_target("base", "18", "vector"),),
        ),
        encoding="utf-8",
    )
    return project


def _semantic_authority(
    package_root: Path,
) -> ProjectModulePackageNeutralIdentityFactSet:
    parse_result = project_check.check_project_parse_only(package_root)
    assert parse_result.ok
    semantic = build_empty_project_semantic_result(parse_result)
    authority = semantic.module_package_identity_facts
    assert authority is not None
    return authority


def _real_graph(
    project_root: Path,
) -> tuple[
    PackageInspectionFactSet,
    tuple[CapabilityInspectionFactSet, ...],
    PackageGraphSnapshot,
]:
    config_result = load_project_config(project_root)
    assert config_result.ok and config_result.config is not None
    assert config_result.root is not None and config_result.pinned_root is not None
    activation = config_result.config.root_package
    assert activation is not None
    location = _locate_root_package(config_result.pinned_root, activation)
    assert location.ok and type(location.located_root) is LocatedRootPackage
    loaded = _load_root_package(location.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    plan = _build_package_load_plan(loaded.loaded_package)
    package_facts = _build_package_inspection_fact_set(plan)
    assert package_facts.inspection.outcome is PackageInspectionOutcome.SUCCESS

    environment_result = _build_project_capability_environment(
        config_result.root,
        config_result.config,
    )
    assert environment_result.ok and environment_result.environment is not None
    environment = environment_result.environment
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
    for package_position, (binding, package_selectors) in enumerate(
        zip(bindings, selectors, strict=True)
    ):
        package_contexts, diagnostics = runtime_builder._package_contexts(
            package_position,
            binding,
            package_selectors,
            environment,
        )
        assert diagnostics == ()
        contexts.append(package_contexts)
    matrices = tuple(
        build_package_capability_checking_matrix(package, binding, package_contexts)
        for package, binding, package_contexts in zip(
            packages,
            bindings,
            contexts,
            strict=True,
        )
    )
    capability_facts = tuple(build_capability_inspection(matrix) for matrix in matrices)
    catalog_facts = runtime_builder._extension_catalog_fact_slots(matrices)
    semantic_facts = tuple(
        _semantic_authority(project_root / package.project_path)
        for package in package_facts.inspection.packages
    )
    result = _build_package_graph(
        package_facts,
        capability_facts=capability_facts,
        extension_catalog_facts=catalog_facts,
        module_identity_facts=semantic_facts,
    )
    assert result.outcome is PackageGraphOutcome.SUCCESS
    assert result.snapshot is not None
    return package_facts, capability_facts, result.snapshot


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _ref_value(ref: PackageGraphInspectionRef) -> dict[str, object]:
    return {"domain": ref.domain.value, "positions": list(ref.positions)}


def _inspection_value(value: object) -> object:
    if value is None or type(value) in {str, int, bool}:
        return value
    if type(value) is bytes:
        return {"bytes_sha256": _digest(value), "size": len(value)}
    if type(value) is PackageGraphInspectionRef:
        return _ref_value(value)
    if type(value) is tuple:
        return [_inspection_value(item) for item in value]
    raise TypeError(f"Unsupported inspection value: {type(value).__name__}")


def _field_values(
    fields: tuple[PackageGraphInspectionField, ...],
) -> list[list[object]]:
    return [[field.name, _inspection_value(field.value)] for field in fields]


def _record_value(record: PackageGraphInspectionRecord) -> dict[str, object]:
    return {
        "ordinal": record.ordinal,
        "kind": record.kind.value,
        "ref": _ref_value(record.ref),
        "fields": _field_values(record.fields),
    }


def _link_value(link: PackageGraphInspectionLink) -> dict[str, object]:
    return {
        "ordinal": link.ordinal,
        "kind": link.kind.value,
        "source": _ref_value(link.source),
        "target": _ref_value(link.target),
        "witness_ref": (
            None if link.witness_ref is None else _ref_value(link.witness_ref)
        ),
        "fields": _field_values(link.fields),
    }


def _state_value(state: PackageGraphInspectionState) -> dict[str, object]:
    return {
        "ordinal": state.ordinal,
        "kind": state.kind.value,
        "owner": _ref_value(state.owner),
        "status": state.status,
        "reason": state.reason,
        "fields": _field_values(state.fields),
    }


def _kind_counts(
    inspection: PackageGraphInspection,
) -> dict[str, list[list[object]]]:
    return {
        "records": [
            [kind.value, sum(record.kind is kind for record in inspection.records)]
            for kind in PackageGraphInspectionRecordKind
            if any(record.kind is kind for record in inspection.records)
        ],
        "links": [
            [kind.value, sum(link.kind is kind for link in inspection.links)]
            for kind in PackageGraphInspectionLinkKind
            if any(link.kind is kind for link in inspection.links)
        ],
        "states": [
            [kind.value, sum(state.kind is kind for state in inspection.states)]
            for kind in PackageGraphInspectionStateKind
            if any(state.kind is kind for state in inspection.states)
        ],
    }


def _field_value(record: PackageGraphInspectionRecord, name: str) -> object:
    return next(field.value for field in record.fields if field.name == name)


def _query_observation(
    snapshot: PackageGraphSnapshot,
    inspection: PackageGraphInspection,
) -> dict[str, object]:
    dependency_package = _inspection_ref(snapshot.packages[0].ref)
    root_package = _inspection_ref(snapshot.packages[1].ref)
    doubled = next(
        record
        for record in inspection.records
        if record.kind is PackageGraphInspectionRecordKind.FIELD
        and record.ref.positions[:3] == (0, 0, 3)
        and _field_value(record, "name") == "doubled"
    )
    amount = next(
        record
        for record in inspection.records
        if record.kind is PackageGraphInspectionRecordKind.FIELD
        and record.ref.positions[:3] == (0, 0, 1)
        and _field_value(record, "name") == "amount"
    )
    catalog = next(
        record
        for record in inspection.records
        if record.kind is PackageGraphInspectionRecordKind.CATALOG_EVIDENCE
    )
    logical = next(
        record
        for record in inspection.records
        if record.kind is PackageGraphInspectionRecordKind.CAPABILITY_EVALUATION
        and _field_value(record, "outcome") != "satisfied"
    )

    def path_ordinals(start: PackageGraphInspectionRef, end: PackageGraphInspectionRef):
        return [
            [link.ordinal for link in path.links]
            for path in _query_package_graph_paths(inspection, start, end)
        ]

    why_not = _query_package_graph_why_not(
        inspection,
        dependency_package,
        logical.ref,
    )
    return {
        "direct_upstream": [
            link.ordinal
            for link in _query_package_graph_direct_upstream(inspection, doubled.ref)
        ],
        "direct_downstream": [
            link.ordinal
            for link in _query_package_graph_direct_downstream(inspection, amount.ref)
        ],
        "all_paths_to_repeated_input": path_ordinals(
            dependency_package,
            amount.ref,
        ),
        "dependency_to_catalog": path_ordinals(dependency_package, catalog.ref),
        "root_to_catalog": path_ordinals(root_package, catalog.ref),
        "why_not": [
            {
                "path": [link.ordinal for link in item.path.links],
                "terminal_ordinal": item.terminal.ordinal,
                "terminal_ref": _ref_value(item.terminal.ref),
                "terminal_outcome": _field_value(item.terminal, "outcome"),
            }
            for item in why_not
        ],
    }


def _inspection_observation(
    snapshot: PackageGraphSnapshot,
    inspection: PackageGraphInspection,
) -> dict[str, object]:
    evaluation = _evaluate_package_graph_inspection(inspection)
    assert evaluation.status is PackageGraphPureStatus.OK
    assert evaluation.canonical_bytes == inspection.canonical_bytes
    return {
        "integrity": "ok",
        "pure_status": evaluation.status.value,
        "canonical_sha256": _digest(inspection.canonical_bytes),
        "canonical_size": len(inspection.canonical_bytes),
        "counts": _kind_counts(inspection),
        "records": [_record_value(record) for record in inspection.records],
        "links": [_link_value(link) for link in inspection.links],
        "states": [_state_value(state) for state in inspection.states],
        "queries": _query_observation(snapshot, inspection),
    }


def _runtime_refs_are_distinct(
    first: PackageGraphSnapshot,
    second: PackageGraphSnapshot,
) -> bool:
    assert first.scope is not second.scope
    for attribute, ref_attribute in (
        ("packages", "ref"),
        ("dependencies", "ref"),
        ("requirement_collections", "package"),
        ("requirements", "ref"),
        ("selectors", "ref"),
        ("capability_evaluations", "ref"),
        ("catalog_evidence", "ref"),
        ("modules", "ref"),
        ("declarations", "ref"),
        ("semantic_authorities", "package"),
        ("fields", "ref"),
        ("let_bindings", "ref"),
    ):
        first_refs = tuple(
            getattr(item, ref_attribute) for item in getattr(first, attribute)
        )
        second_refs = tuple(
            getattr(item, ref_attribute) for item in getattr(second, attribute)
        )
        assert len(first_refs) == len(second_refs) > 0
        assert all(
            first_ref != second_ref
            for first_ref, second_ref in zip(first_refs, second_refs, strict=True)
        )
    return True


def _run_cli(
    arguments: tuple[str, ...], cwd: Path
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        (sys.executable, "-c", _CLI_CODE, *arguments),
        check=False,
        capture_output=True,
        cwd=cwd,
        env=os.environ.copy(),
    )


def _project_explain_observation(project: Path, cwd: Path) -> dict[str, object]:
    result = runtime_builder._build_project_explain_runtime(project)
    assert result.outcome is ProjectExplainRuntimeOutcome.SUCCESS
    json_document = serialize_project_explain_json_document(result.envelope)
    text_document = render_project_explain_text(result.envelope).encode()
    json_cli = _run_cli(
        ("explain", "--project", project.as_posix(), "--format", "json"),
        cwd,
    )
    text_cli = _run_cli(("explain", "--project", project.as_posix()), cwd)
    assert (json_cli.returncode, json_cli.stdout, json_cli.stderr) == (
        0,
        json_document,
        b"",
    )
    assert (text_cli.returncode, text_cli.stdout, text_cli.stderr) == (
        0,
        text_document,
        b"",
    )
    return {
        "runtime_outcome": result.outcome.value,
        "json_sha256": _digest(json_document),
        "json_size": len(json_document),
        "text_sha256": _digest(text_document),
        "text_size": len(text_document),
        "cli_json_exit": json_cli.returncode,
        "cli_text_exit": text_cli.returncode,
    }


def observation(workspace: Path) -> dict[str, object]:
    """Return one ordered observation without environmental metadata."""

    workspace.mkdir(parents=True, exist_ok=True)
    cwd = workspace / "cwd"
    cwd.mkdir()
    first_project = _write_real_project(workspace, "first")
    second_project = _write_real_project(workspace, "second")
    _first_packages, _first_capabilities, first = _real_graph(first_project)
    _second_packages, _second_capabilities, second = _real_graph(second_project)
    _validate_package_graph_integrity(first)
    _validate_package_graph_integrity(second)
    first_inspection = _inspect_package_graph(first)
    second_inspection = _inspect_package_graph(second)
    assert first_inspection == second_inspection
    assert first_inspection.canonical_bytes == second_inspection.canonical_bytes
    assert str(first_project).encode() not in first_inspection.canonical_bytes
    assert str(second_project).encode() not in second_inspection.canonical_bytes
    assert repr(first.scope).encode() not in first_inspection.canonical_bytes
    assert str(id(first.scope)).encode() not in first_inspection.canonical_bytes
    return {
        "observation_format": OBSERVATION_FORMAT,
        "package_version": version("pietto"),
        "runtime_refs_distinct": _runtime_refs_are_distinct(first, second),
        "graph": _inspection_observation(first, first_inspection),
        "project_explain": _project_explain_observation(first_project, cwd),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", type=Path, required=True)
    namespace = parser.parse_args(argv)
    document = (
        json.dumps(
            observation(namespace.workspace),
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=False,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )
    sys.stdout.buffer.write(document)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
