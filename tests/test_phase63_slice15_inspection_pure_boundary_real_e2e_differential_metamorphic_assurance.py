from __future__ import annotations

import ast
from copy import copy
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import cast

import pytest

import _pietto_phase63_query_block_ir_differential_probe as probe
import test_phase63_slice14_query_block_project_ir_composition_verification_invalidation as slice14
import test_phase58_slice16_pure_differential_compatibility_assurance as phase58_diff
from pietto._project import project_query_block_ir_inspection as inspection
from pietto._project import project_query_block_ir_pure_boundary as pure
from pietto._project.project_ir_pure_boundary import PROJECT_IR_INSPECTION_FORMAT
from pietto._project.project_ir import _declaration_identity
from pietto._project.project_phase62_pure_boundary import (
    PROJECT_PHASE62_INSPECTION_FORMAT,
)
from pietto._project.project_query_block_ir import (
    ProjectIRCompletedQueryBlockOutput,
    ProjectIRQueryBlockTerminal,
    ProjectIRReboundExistingOutput,
    ProjectIRReusedEffectiveOutput,
)
from pietto._project.project_query_block_ir_verification import (
    ProjectIRQueryBlockAnalysisBundle,
    ProjectIRQueryBlockVerificationIssue,
    ProjectIRQueryBlockVerificationIssueKind,
    ProjectIRQueryBlockVerificationStatus,
    build_project_query_block_ir_analysis_bundle,
    verify_project_query_block_ir,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
INSPECTION_SOURCE = (
    REPO_ROOT / "src/pietto/_project/project_query_block_ir_inspection.py"
)
PURE_SOURCE = REPO_ROOT / "src/pietto/_project/project_query_block_ir_pure_boundary.py"
PROBE = REPO_ROOT / "tests/_pietto_phase63_query_block_ir_differential_probe.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase63-slice15-inspection-pure-boundary-real-e2e-differential-metamorphic-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))


# Frozen after review of one source-checkout observation. Full observations,
# records, and canonical bytes are compared directly; digests are review aids.
EXPECTED_REVIEW_SUMMARY: dict[str, object] = {
    "observation_format": "pietto.phase63-query-block-ir-differential.v1",
    "package_version": "0.1.0",
    "owner_count": 35,
    "record_count": 1952,
    "canonical_size": 311950,
    "canonical_sha256": "e3ae8967f8fd5ae19e89d00706f5df859a5b12c4208a92f1d77eb980e7e2d9aa",
    "phase61_size": 90142,
    "phase61_sha256": "b01e22a5c6fc603b99da93267ce4f4f5e90a6ccb06e692e3690ca878cc464144",
    "phase62_size": 204055,
    "phase62_sha256": "13218f6e78e5d8cd373477f1823724fb59a9bb70808c5de5d1f7d94c29de5e27",
    "metamorphics": {
        "active_root_invariance": [105, 105, 105, 4, 4],
        "selected_hidden": {
            "selected": [1, 1, True],
            "hidden": [
                1,
                0,
                1,
                ["window_evaluation", "qualify", "final_projection"],
            ],
            "selected_and_hidden": [1, 1],
        },
        "qualify": [
            ["window_evaluation", "final_projection"],
            ["window_evaluation", "qualify", "final_projection"],
            True,
        ],
        "window_vs_relation_order": [None, "ProjectRelationOrdering"],
        "limit": [1, 2, True, "factorized", "factorized"],
        "grouped_global": ["factorized", ["group_domain"], "global", [], 0],
        "downstream": [True, True],
        "reuse_rebound": [
            "ProjectIRReusedEffectiveOutput",
            True,
            "ProjectIRReboundExistingOutput",
            True,
        ],
        "effective_join": [
            "effective_join_input_rebind_unsupported",
            "active_upstream_ir_non_concrete",
            True,
            True,
        ],
        "inner_left": [
            ["non_null", "non_null"],
            ["non_null", "nullable"],
            [0, 1],
        ],
        "multi_join": [7, [0, 0, 1]],
        "duplicate_intermediate_names": [7, 4],
    },
    "negative": {
        "non_verified_admission": "rejected",
        "cross_snapshot_ref": "rejected",
        "terminals": [
            ["semantic_bad", "semantic_output_non_concrete"],
            ["downstream_stale", "active_upstream_ir_non_concrete"],
            ["stale_join", "effective_join_input_rebind_unsupported"],
        ],
        "pure_rejections": [
            ["unknown_format", "unknown_format", 0, 0],
            ["section_order", "invalid_section_order", 0, 0],
            ["dangling_ref", "dangling_ref", 501, 1],
        ],
    },
}


def _unsafe[Value](value: Value, **changes: object) -> Value:
    copied = copy(value)
    for name, replacement in changes.items():
        object.__setattr__(copied, name, replacement)
    return copied


@pytest.fixture(scope="module")
def bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> ProjectIRQueryBlockAnalysisBundle:
    built = slice14._build(tmp_path_factory.mktemp("p63s15"))
    verification = verify_project_query_block_ir(built.snapshot)
    return build_project_query_block_ir_analysis_bundle(verification)


@pytest.fixture(scope="module")
def foreign_bundle(
    tmp_path_factory: pytest.TempPathFactory,
) -> ProjectIRQueryBlockAnalysisBundle:
    built = slice14._build(tmp_path_factory.mktemp("p63s15-foreign"))
    verification = verify_project_query_block_ir(built.snapshot)
    return build_project_query_block_ir_analysis_bundle(verification)


@pytest.fixture(scope="module")
def product(
    bundle: ProjectIRQueryBlockAnalysisBundle,
) -> inspection.ProjectIRQueryBlockInspectionProduct:
    return inspection.build_project_query_block_ir_inspection(bundle)


@pytest.fixture(scope="module")
def observed(
    product: inspection.ProjectIRQueryBlockInspectionProduct,
) -> inspection.ProjectIRQueryBlockInspection:
    return product.inspection


def _entry(
    observed: inspection.ProjectIRQueryBlockInspection,
    name: str,
):
    matches = tuple(
        entry
        for entry in observed.entries
        if entry.owner.identity.declared_name == name
    )
    assert len(matches) == 1
    return matches[0]


def _same_objects(actual: tuple[object, ...], expected: tuple[object, ...]) -> bool:
    return len(actual) == len(expected) and all(
        item is retained for item, retained in zip(actual, expected, strict=True)
    )


def _record_position(
    document: pure.ProjectQueryBlockIRPureDocument,
    kind: pure.ProjectQueryBlockIRRecordKind,
) -> int:
    return next(
        position
        for position, record in enumerate(document.records)
        if record.kind is kind
    )


def _field_position(
    record: pure.ProjectQueryBlockIRPureRecord,
    key: str,
) -> int:
    return next(
        position for position, field in enumerate(record.fields) if field.key == key
    )


def _replace_record(
    document: pure.ProjectQueryBlockIRPureDocument,
    position: int,
    record: pure.ProjectQueryBlockIRPureRecord,
) -> pure.ProjectQueryBlockIRPureDocument:
    return replace(
        document,
        records=(
            *document.records[:position],
            record,
            *document.records[position + 1 :],
        ),
    )


def _replace_field(
    document: pure.ProjectQueryBlockIRPureDocument,
    record_position: int,
    key: str,
    value: pure.ProjectQueryBlockIRPureValue,
) -> pure.ProjectQueryBlockIRPureDocument:
    record = document.records[record_position]
    position = _field_position(record, key)
    replacement = replace(
        record,
        fields=(
            *record.fields[:position],
            replace(record.fields[position], value=value),
            *record.fields[position + 1 :],
        ),
    )
    return _replace_record(document, record_position, replacement)


def _environment(source_root: Path, seed: str, ambient: str) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONNOUSERSITE"] = "1"
    environment[probe.SEED_ENVIRONMENT] = ambient
    environment["PYTHONPATH"] = os.pathsep.join(
        (str(source_root / "src"), phase58_diff._site_packages())
    )
    return environment


def _run_probe(
    executable: str,
    probe_path: Path,
    workspace: Path,
    *,
    source_root: Path,
    seed: str,
    ambient: str,
) -> bytes:
    run_root = workspace.parent / f"run-{workspace.name}"
    run_root.mkdir()
    completed = subprocess.run(
        (executable, str(probe_path), "--workspace", str(workspace)),
        check=True,
        capture_output=True,
        cwd=run_root,
        env=_environment(source_root, seed, ambient),
    )
    assert completed.stderr == b""
    assert completed.stdout.endswith(b"\n")
    assert not completed.stdout.endswith(b"\n\n")
    json.loads(completed.stdout)
    return completed.stdout


def _relocate_source(target: Path) -> Path:
    shutil.copytree(
        REPO_ROOT / "src",
        target / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    tests = target / "tests"
    tests.mkdir()
    shutil.copyfile(PROBE, tests / PROBE.name)
    return tests / PROBE.name


def _import_origin(executable: str, source_root: Path, cwd: Path) -> Path:
    completed = subprocess.run(
        (
            executable,
            "-c",
            "from pathlib import Path; import pietto; "
            "print(Path(pietto.__file__).resolve())",
        ),
        check=True,
        text=True,
        capture_output=True,
        cwd=cwd,
        env=_environment(source_root, "7", "installed-origin"),
    )
    assert completed.stderr == ""
    return Path(completed.stdout.strip())


def _decoded(document: bytes) -> dict[str, object]:
    return cast(dict[str, object], json.loads(document))


def _review_summary(document: bytes) -> dict[str, object]:
    observation = _decoded(document)
    canonical = cast(str, observation["canonical_bytes"]).encode("utf-8")
    phase61 = cast(str, observation["phase61_canonical_bytes"]).encode("utf-8")
    phase62 = cast(str, observation["phase62_canonical_bytes"]).encode("utf-8")
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "owner_count": len(cast(list[object], observation["scenario_manifest"])),
        "record_count": len(cast(list[object], observation["portable_records"])),
        "canonical_size": len(canonical),
        "canonical_sha256": hashlib.sha256(canonical).hexdigest(),
        "phase61_size": len(phase61),
        "phase61_sha256": hashlib.sha256(phase61).hexdigest(),
        "phase62_size": len(phase62),
        "phase62_sha256": hashlib.sha256(phase62).hexdigest(),
        "metamorphics": observation["metamorphics"],
        "negative": observation["negative"],
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    observations: dict[str, bytes] = {}
    interpreters = phase58_diff._available_supported_interpreters()
    for interpreter_version, executable in interpreters.items():
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        for seed in SEEDS:
            key = f"source:{label}:seed:{seed}"
            observations[key] = _run_probe(
                executable,
                PROBE,
                tmp_path_factory.mktemp(key.replace(":", "-")),
                source_root=REPO_ROOT,
                seed=seed,
                ambient=key,
            )

    relocated_root = tmp_path_factory.mktemp("source-relocated")
    relocated_probe = _relocate_source(relocated_root)
    for interpreter_version, executable in interpreters.items():
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"relocated:{label}:seed:7"
        observations[key] = _run_probe(
            executable,
            relocated_probe,
            tmp_path_factory.mktemp(key.replace(":", "-")),
            source_root=relocated_root,
            seed="7",
            ambient=key,
        )

    wheel_root = tmp_path_factory.mktemp("installed-wheel")
    (
        _installed_python,
        _installed_origin,
        installed_source_root,
        empty_install_cache,
    ) = phase58_diff._installed_python(wheel_root)
    installed_probe = wheel_root / PROBE.name
    shutil.copyfile(PROBE, installed_probe)
    installed_origins: dict[tuple[int, int], Path] = {}
    for interpreter_version, executable in interpreters.items():
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        key = f"installed:{label}:seed:7"
        workspace = tmp_path_factory.mktemp(key.replace(":", "-"))
        observations[key] = _run_probe(
            executable,
            installed_probe,
            workspace,
            source_root=installed_source_root,
            seed="7",
            ambient=key,
        )
        installed_origins[interpreter_version] = _import_origin(
            executable,
            installed_source_root,
            workspace.parent,
        )
    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origins": installed_origins,
        "installed_source_root": installed_source_root,
        "empty_install_cache": empty_install_cache,
    }


def _baseline_key() -> str:
    return f"source:python{sys.version_info[0]}.{sys.version_info[1]}:seed:0"


def test_gate_a_private_verified_only_admission_and_exact_root_chain(
    bundle: ProjectIRQueryBlockAnalysisBundle,
    observed: inspection.ProjectIRQueryBlockInspection,
) -> None:
    root = bundle.root
    assert inspection.__all__ == ()
    assert observed.analysis_bundle is bundle
    assert observed.verification is bundle.verification
    assert observed.root is root
    assert observed.completed is root.completed
    assert observed.project_completion is root.completed.completion
    assert observed.effective_output_completion is root.completed.effective_outputs
    assert observed.phase62_verification is root.completed.verification
    assert observed.phase62_root is root.completed.verification.root
    assert observed.join_stage is observed.phase62_root.join_regions
    assert observed.base_plan is observed.phase62_root.evaluation.project_plan
    assert observed.owners is root.owners
    assert observed.dependencies is root.dependencies
    assert observed.schedule is root.schedule
    assert observed.entries is root.entries
    assert observed.combined_reverse_uses is bundle.combined_reverse_uses
    assert observed.combined_topological_order is bundle.combined_topological_order
    assert observed.combined_reachability is bundle.combined_reachability

    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_query_block_ir_inspection(root)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="analysis bundle"):
        inspection.build_project_query_block_ir_inspection(  # type: ignore[arg-type]
            bundle.verification  # pyright: ignore[reportArgumentType]
        )

    invalid = _unsafe(
        bundle.verification,
        status=ProjectIRQueryBlockVerificationStatus.INVALID,
        issues=(
            ProjectIRQueryBlockVerificationIssue(
                kind=ProjectIRQueryBlockVerificationIssueKind.ROOT_CONTINUITY
            ),
        ),
    )
    with pytest.raises(ValueError, match="VERIFIED"):
        inspection.build_project_query_block_ir_inspection(
            _unsafe(bundle, verification=invalid)
        )


def test_gate_a_sections_retain_complete_slice14_objects_in_canonical_order(
    observed: inspection.ProjectIRQueryBlockInspection,
) -> None:
    root = observed.root
    base = root.base_plan.structural_stage
    join = root.join_stage.structural
    assert _same_objects(observed.entries, root.entries)
    assert _same_objects(
        observed.combined_nodes,
        (*base.nodes, *join.nodes, *root.structural.nodes),
    )
    assert _same_objects(
        observed.combined_outputs,
        (*base.outputs, *join.outputs, *root.structural.outputs),
    )
    assert _same_objects(
        observed.combined_input_slots,
        (*base.input_slots, *join.input_slots, *root.structural.input_slots),
    )
    assert _same_objects(
        observed.combined_uses,
        (*base.uses, *join.uses, *root.structural.uses),
    )
    concrete_entries = cast(
        tuple[
            ProjectIRReusedEffectiveOutput
            | ProjectIRReboundExistingOutput
            | ProjectIRCompletedQueryBlockOutput,
            ...,
        ],
        tuple(
            entry
            for entry in observed.entries
            if type(entry)
            in {
                ProjectIRReusedEffectiveOutput,
                ProjectIRReboundExistingOutput,
                ProjectIRCompletedQueryBlockOutput,
            }
        ),
    )
    assert tuple(entry.active_output for entry in concrete_entries) == (
        observed.active_outputs
    )
    assert (
        tuple(entry.active_properties for entry in concrete_entries)
        == observed.active_properties
    )
    assert all(
        properties.output is output
        for properties, output in zip(
            observed.active_properties, observed.active_outputs, strict=True
        )
    )
    assert all(
        field.final_identity is identity
        for field, identity in zip(
            (
                field
                for field in observed.query_block_row_fields
                if field.final_identity is not None
            ),
            observed.final_field_identities,
            strict=True,
        )
    )
    assert (
        tuple(item.blocker for item in observed.terminals) == observed.terminal_blockers
    )
    assert observed.summary.entry_count == len(observed.entries)
    assert observed.summary.analysis_entry_count == (
        len(observed.combined_reverse_uses)
        + len(observed.combined_topological_order)
        + len(observed.combined_reachability)
    )


def test_gate_a_winner_free_queries_return_complete_identity_buckets(
    observed: inspection.ProjectIRQueryBlockInspection,
) -> None:
    completed = cast(
        ProjectIRCompletedQueryBlockOutput,
        _entry(observed, "left_selected_hidden"),
    )
    owner = _declaration_identity(completed.owner)
    assert inspection.query_project_query_block_entries(observed, owner) == (completed,)
    assert inspection.query_project_query_block_active_roots(observed, owner) == (
        (completed.active_output, completed.active_properties),
    )
    node = completed.operators[0].node
    assert inspection.query_project_query_block_nodes(observed, node.ref) == (node,)
    assert inspection.query_project_query_block_operators(observed, node.ref) == (
        completed.operators[0],
    )
    row_output = completed.row_outputs[0].occurrence
    assert inspection.query_project_query_block_outputs(observed, row_output.ref) == (
        row_output,
    )
    slot = completed.input_slots[0]
    use = completed.uses[0]
    assert inspection.query_project_query_block_input_slots(observed, slot.ref) == (
        slot,
    )
    assert inspection.query_project_query_block_uses(observed, use.ref) == (use,)
    assert use in inspection.query_project_query_block_incoming_uses(
        observed, slot.consumer.ref
    )
    assert use in inspection.query_project_query_block_outgoing_uses(
        observed, use.output.producer.ref
    )
    final_field = next(
        item for item in completed.active_output.row_shape.fields if item.final_identity
    )
    assert inspection.query_project_query_block_final_fields(
        observed,
        cast(object, final_field.final_identity),  # type: ignore[arg-type]
    ) == (final_field,)
    reverse = inspection.query_project_query_block_reverse_uses(
        observed, row_output.ref
    )
    assert reverse and all(item.output is row_output for item in reverse)
    reachability = inspection.query_project_query_block_reachability(observed, node.ref)
    assert reachability and all(item.source is node for item in reachability)

    terminal = cast(ProjectIRQueryBlockTerminal, _entry(observed, "semantic_bad"))
    assert inspection.query_project_query_block_terminals(
        observed, _declaration_identity(terminal.owner)
    ) == (terminal,)
    rebound = cast(ProjectIRReboundExistingOutput, _entry(observed, "rebound_one"))
    assert inspection.query_project_query_block_relation_inputs(
        observed, _declaration_identity(rebound.owner)
    ) == (rebound.relation_input,)
    if observed.grain_origins:
        origin = observed.grain_origins[0]
        assert origin in inspection.query_project_query_block_grain_origins(
            observed, origin.operator.ref
        )
        if origin.factor is not None:
            factors = inspection.query_project_query_block_grain_factors(
                observed, origin.factor
            )
            assert factors and all(item.identity is origin.factor for item in factors)


def test_gate_a_foreign_grafts_trailing_members_and_reordering_fail_closed(
    observed: inspection.ProjectIRQueryBlockInspection,
    foreign_bundle: ProjectIRQueryBlockAnalysisBundle,
) -> None:
    foreign = inspection.build_project_query_block_ir_inspection(
        foreign_bundle
    ).inspection
    local_completed = cast(
        ProjectIRCompletedQueryBlockOutput,
        _entry(observed, "left_selected_hidden"),
    )
    foreign_completed = cast(
        ProjectIRCompletedQueryBlockOutput,
        _entry(foreign, "left_selected_hidden"),
    )
    with pytest.raises(ValueError, match="VERIFIED analysis bundle"):
        replace(observed, analysis_bundle=foreign_bundle)
    with pytest.raises(ValueError, match="active_outputs"):
        replace(
            observed,
            active_outputs=(
                foreign_completed.active_output,
                *observed.active_outputs[1:],
            ),
        )
    with pytest.raises(ValueError, match="entries"):
        replace(
            observed,
            entries=(foreign_completed, *observed.entries[1:]),
        )
    with pytest.raises(ValueError, match="combined_outputs"):
        replace(
            observed,
            combined_outputs=(*observed.combined_outputs, foreign.combined_outputs[-1]),
        )
    with pytest.raises(ValueError, match="entries"):
        replace(observed, entries=tuple(reversed(observed.entries)))
    assert local_completed.active_output is not foreign_completed.active_output
    with pytest.raises(ValueError, match="snapshot scope"):
        inspection.query_project_query_block_outputs(
            observed, foreign_completed.active_output.occurrence.ref
        )
    foreign_grouped = tuple(
        origin.factor for origin in foreign.grain_origins if origin.factor is not None
    )
    if foreign_grouped:
        with pytest.raises(ValueError, match="snapshot scope"):
            inspection.query_project_query_block_grain_factors(
                observed, foreign_grouped[0]
            )


def test_gate_a_static_boundary_has_no_winner_or_reconstruction_escape() -> None:
    source = INSPECTION_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    names = {
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert not any(
        name.startswith(("get_best_", "get_latest_", "get_last_")) for name in names
    )
    assert "row_outputs[-1]" not in source
    assert "row_properties[-1]" not in source
    assert "verify_project_query_block_ir(" not in source
    assert "build_project_query_block_ir(" not in source


def test_gate_b_private_stdlib_owner_single_encoder_and_additive_marker() -> None:
    assert pure.__all__ == ()
    assert (
        pure.PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT
        == "pietto.phase63-query-block-ir-inspection.v1"
    )
    assert PROJECT_IR_INSPECTION_FORMAT == "pietto.project-ir-inspection.v1"
    assert PROJECT_PHASE62_INSPECTION_FORMAT == "pietto.phase62-inspection.v1"
    assert (
        len(
            {
                pure.PROJECT_QUERY_BLOCK_IR_INSPECTION_FORMAT,
                PROJECT_IR_INSPECTION_FORMAT,
                PROJECT_PHASE62_INSPECTION_FORMAT,
            }
        )
        == 3
    )
    source = PURE_SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)
    }
    assert imports <= {"__future__", "dataclasses", "enum", "heapq", "typing"}
    assert not tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        and (
            isinstance(node, ast.Import)
            or node.module
            not in {"__future__", "dataclasses", "enum", "heapq", "typing"}
        )
    )
    assert (
        sum(
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == "_encode_document"
            for node in ast.walk(tree)
        )
        == 1
    )
    assert "import json" not in source
    assert "hashlib" not in source
    assert "ProjectIRSnapshotScope" not in source


def test_gate_b_document_observes_explicit_roots_properties_windows_and_analyses(
    product: inspection.ProjectIRQueryBlockInspectionProduct,
) -> None:
    document = product.document
    outcome = pure.evaluate_project_query_block_ir_document(document)
    assert outcome.status is pure.ProjectQueryBlockIRPureStatus.OK
    assert outcome.canonical_bytes == product.canonical_bytes
    assert (
        inspection.serialize_project_query_block_ir_inspection(product.inspection)
        == product.canonical_bytes
    )
    assert product.canonical_bytes.startswith(
        b"header\tformat=t:pietto.phase63-query-block-ir-inspection.v1"
    )
    assert str(REPO_ROOT).encode() not in product.canonical_bytes
    assert b"0x" not in product.canonical_bytes

    records = document.records
    owners = tuple(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
    )
    operators = tuple(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OPERATOR
    )
    selected = tuple(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.WINDOW_SELECTED
    )
    hidden = tuple(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.WINDOW_HIDDEN
    )
    assert len(owners) == len(product.inspection.entries)
    assert len(operators) == len(product.inspection.operators)
    assert len(selected) == len(product.inspection.selected_window_scalars)
    assert len(hidden) == len(product.inspection.hidden_window_evidence)
    assert all(
        tuple(field.key for field in record.fields)
        == (
            "operator",
            "owner",
            "ordinal",
            "evidence_kind",
        )
        for record in hidden
    )
    assert any(
        record.fields[_field_position(record, "kind")].value.enumeration == "qualify"
        for record in operators
    )
    assert all(
        record.fields[_field_position(record, "active_output")].value.tag
        is pure.ProjectQueryBlockIRPureTag.ABSENT
        for record in owners
        if record.fields[_field_position(record, "variant")].value.enumeration
        == "terminal"
    )
    origins = tuple(
        record
        for record in records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.GRAIN_ORIGIN
    )
    assert any(
        record.fields[_field_position(record, "kind")].value.enumeration
        == "grouped_result"
        and record.fields[_field_position(record, "factors")].value.refs
        for record in origins
    )
    assert any(
        record.fields[_field_position(record, "kind")].value.enumeration
        == "global_aggregate"
        and record.fields[_field_position(record, "factors")].value.tag
        is pure.ProjectQueryBlockIRPureTag.ABSENT
        for record in origins
    )
    assert sum(
        record.kind is pure.ProjectQueryBlockIRRecordKind.ANALYSIS_REVERSE_USE
        for record in records
    ) == len(product.inspection.combined_outputs)
    assert sum(
        record.kind is pure.ProjectQueryBlockIRRecordKind.ANALYSIS_TOPOLOGICAL
        for record in records
    ) == len(product.inspection.combined_nodes)
    assert sum(
        record.kind is pure.ProjectQueryBlockIRRecordKind.ANALYSIS_REACHABILITY
        for record in records
    ) == len(product.inspection.combined_nodes)


def test_gate_b_total_evaluator_rejects_all_adversarial_document_mutations(
    product: inspection.ProjectIRQueryBlockInspectionProduct,
) -> None:
    document = product.document
    mutations: list[
        tuple[
            str,
            pure.ProjectQueryBlockIRPureDocument | object,
            pure.ProjectQueryBlockIRPureStatus,
        ]
    ] = []
    mutations.append(
        (
            "non_document",
            object(),
            pure.ProjectQueryBlockIRPureStatus.INVALID_DOCUMENT,
        )
    )
    mutations.append(
        (
            "unknown_format",
            replace(document, format_marker="untrusted\nformat"),
            pure.ProjectQueryBlockIRPureStatus.UNKNOWN_FORMAT,
        )
    )
    dependency_position = _record_position(
        document, pure.ProjectQueryBlockIRRecordKind.DEPENDENCY
    )
    node_position = _record_position(document, pure.ProjectQueryBlockIRRecordKind.NODE)
    mutations.append(
        (
            "section_order",
            replace(
                document,
                records=(
                    *document.records[:dependency_position],
                    document.records[node_position],
                    *document.records[dependency_position + 1 : node_position],
                    document.records[dependency_position],
                    *document.records[node_position + 1 :],
                ),
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_SECTION_ORDER,
        )
    )
    use_position = _record_position(document, pure.ProjectQueryBlockIRRecordKind.USE)
    mutations.append(
        (
            "dangling_ref",
            _replace_field(
                document,
                use_position,
                "output",
                pure.project_query_block_ir_pure_ref(
                    pure.ProjectQueryBlockIRPortableRef(
                        domain=pure.ProjectQueryBlockIRPortableRefDomain.OUTPUT_VALUE,
                        position=10**6,
                    )
                ),
            ),
            pure.ProjectQueryBlockIRPureStatus.DANGLING_REF,
        )
    )
    mutations.append(
        (
            "wrong_ref_domain",
            _replace_field(
                document,
                use_position,
                "output",
                pure.project_query_block_ir_pure_ref(
                    pure.ProjectQueryBlockIRPortableRef(
                        domain=pure.ProjectQueryBlockIRPortableRefDomain.PLAN_NODE,
                        position=0,
                    )
                ),
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_REF,
        )
    )
    owner_positions = tuple(
        position
        for position, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
        and record.fields[_field_position(record, "variant")].value.enumeration
        != "terminal"
    )
    first_owner = document.records[owner_positions[0]]
    mutations.append(
        (
            "duplicate_active_mapping",
            _replace_field(
                _replace_field(
                    document,
                    owner_positions[1],
                    "active_output",
                    first_owner.fields[
                        _field_position(first_owner, "active_output")
                    ].value,
                ),
                owner_positions[1],
                "active_property",
                first_owner.fields[
                    _field_position(first_owner, "active_property")
                ].value,
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_ACTIVE_MAPPING,
        )
    )
    terminal_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
        and record.fields[_field_position(record, "variant")].value.enumeration
        == "terminal"
    )
    mutations.append(
        (
            "terminal_active_output",
            _replace_field(
                document,
                terminal_position,
                "active_output",
                first_owner.fields[_field_position(first_owner, "active_output")].value,
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_TERMINAL,
        )
    )
    operator_position = _record_position(
        document, pure.ProjectQueryBlockIRRecordKind.OPERATOR
    )
    operator = document.records[operator_position]
    wrong_node = next(
        record.fields[0].value
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.NODE
        and record.fields[0].value.ref
        != operator.fields[_field_position(operator, "node")].value.ref
        and record.fields[_field_position(record, "stage")].value.enumeration
        == "phase63"
    )
    mutations.append(
        (
            "operator_wrong_node",
            _replace_field(document, operator_position, "node", wrong_node),
            pure.ProjectQueryBlockIRPureStatus.INVALID_OPERATOR,
        )
    )
    mixed_owner = next(
        record.fields[0].value.ref
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OWNER_ENTRY
        and record.fields[_field_position(record, "declared_name")].value.text
        == "mixed"
    )
    mixed_row_filter_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.OPERATOR
        and record.fields[_field_position(record, "owner")].value.ref == mixed_owner
        and record.fields[_field_position(record, "kind")].value.enumeration
        == "row_filter"
    )
    mutations.append(
        (
            "qualify_misplaced",
            _replace_field(
                document,
                mixed_row_filter_position,
                "kind",
                pure.project_query_block_ir_pure_enumeration("qualify"),
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_OPERATOR,
        )
    )
    hidden_position = _record_position(
        document, pure.ProjectQueryBlockIRRecordKind.WINDOW_HIDDEN
    )
    hidden = document.records[hidden_position]
    fake_hidden = replace(
        hidden,
        fields=(
            *hidden.fields,
            pure.ProjectQueryBlockIRPureField(
                key="output",
                value=first_owner.fields[
                    _field_position(first_owner, "active_output")
                ].value,
            ),
        ),
    )
    mutations.append(
        (
            "hidden_fake_output",
            _replace_record(document, hidden_position, fake_hidden),
            pure.ProjectQueryBlockIRPureStatus.INVALID_FIELD,
        )
    )
    grouped_origin_position = next(
        position
        for position, record in enumerate(document.records)
        if record.kind is pure.ProjectQueryBlockIRRecordKind.GRAIN_ORIGIN
        and record.fields[_field_position(record, "kind")].value.enumeration
        == "grouped_result"
    )
    origin = document.records[grouped_origin_position]
    foreign_factor = next(
        record.fields[0].value.ref
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.GRAIN_FACTOR
        and record.fields[_field_position(record, "operator")].value.ref
        != origin.fields[_field_position(origin, "operator")].value.ref
    )
    mutations.append(
        (
            "invalid_grain_factor",
            _replace_field(
                document,
                grouped_origin_position,
                "factors",
                pure.project_query_block_ir_pure_refs((cast(object, foreign_factor),)),  # type: ignore[arg-type]
            ),
            pure.ProjectQueryBlockIRPureStatus.INVALID_GRAIN,
        )
    )
    reachability_position = _record_position(
        document, pure.ProjectQueryBlockIRRecordKind.ANALYSIS_REACHABILITY
    )
    reachability = document.records[reachability_position]
    other_node = next(
        record.fields[0].value
        for record in document.records
        if record.kind is pure.ProjectQueryBlockIRRecordKind.NODE
        and record.fields[0].value.ref
        != reachability.fields[_field_position(reachability, "source")].value.ref
    )
    mutations.append(
        (
            "invalid_analysis_ref",
            _replace_field(document, reachability_position, "source", other_node),
            pure.ProjectQueryBlockIRPureStatus.INVALID_ANALYSIS,
        )
    )

    for label, mutated, expected in mutations:
        result = pure.evaluate_project_query_block_ir_document(mutated)
        assert result.status is expected, label
        assert result.canonical_bytes is None, label
        assert type(result.record_position) is int, label
        assert type(result.field_position) is int, label
        assert not hasattr(result, "message"), label


def test_gate_c_real_authored_manifest_full_records_and_metamorphics_are_frozen(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = observations[_baseline_key()]
    observation = _decoded(baseline)
    expected_manifest = json.loads(
        json.dumps(probe.SCENARIO_MANIFEST, separators=(",", ":"))
    )
    assert observation["scenario_manifest"] == expected_manifest
    assert _review_summary(baseline) == EXPECTED_REVIEW_SUMMARY
    assert observation["runtime_identities_distinct"] is True
    assert observation["second_bundle_distinct"] is True
    assert observation["query_order_invariant"] is True
    assert observation["file_creation_order_invariant"] is True
    assert observation["continuity"] == [True, True, True, True, True]
    metamorphics = cast(dict[str, object], observation["metamorphics"])
    assert (
        metamorphics["selected_hidden"]
        == cast(dict[str, object], EXPECTED_REVIEW_SUMMARY["metamorphics"])[
            "selected_hidden"
        ]
    )
    assert metamorphics["qualify"] == [
        ["window_evaluation", "final_projection"],
        ["window_evaluation", "qualify", "final_projection"],
        True,
    ]
    assert metamorphics["window_vs_relation_order"] == [
        None,
        "ProjectRelationOrdering",
    ]
    assert metamorphics["limit"] == [
        1,
        2,
        True,
        "factorized",
        "factorized",
    ]
    assert metamorphics["grouped_global"] == [
        "factorized",
        ["group_domain"],
        "global",
        [],
        0,
    ]
    assert metamorphics["downstream"] == [True, True]
    assert metamorphics["effective_join"] == [
        "effective_join_input_rebind_unsupported",
        "active_upstream_ir_non_concrete",
        True,
        True,
    ]
    assert metamorphics["inner_left"] == [
        ["non_null", "non_null"],
        ["non_null", "nullable"],
        [0, 1],
    ]
    assert metamorphics["multi_join"] == [7, [0, 0, 1]]
    assert metamorphics["duplicate_intermediate_names"] == [7, 4]


def test_gate_d_all_interpreters_seeds_relocation_and_wheel_match_exactly(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert SEEDS == ("0", "1", "7", "4294967295")
    assert SUPPORTED_INTERPRETERS == ((3, 12), (3, 13))
    assert sys.version_info[:2] in SUPPORTED_INTERPRETERS
    assert sys.version_info[:2] in interpreters
    baseline = observations[_baseline_key()]
    baseline_observation = _decoded(baseline)
    baseline_records = baseline_observation["portable_records"]
    baseline_bytes = baseline_observation["canonical_bytes"]
    for interpreter_version in interpreters:
        label = f"python{interpreter_version[0]}.{interpreter_version[1]}"
        for seed in SEEDS:
            document = observations[f"source:{label}:seed:{seed}"]
            assert document == baseline
            decoded = _decoded(document)
            assert decoded["portable_records"] == baseline_records
            assert decoded["canonical_bytes"] == baseline_bytes
        assert observations[f"relocated:{label}:seed:7"] == baseline
        assert observations[f"installed:{label}:seed:7"] == baseline


def test_gate_d_installed_origins_are_isolated_and_ambient_paths_do_not_leak(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = observations[_baseline_key()]
    for forbidden in (
        str(REPO_ROOT).encode(),
        b"source-relocated",
        b"installed-wheel",
        probe.SEED_ENVIRONMENT.encode(),
        b".venv",
        b"0x",
    ):
        assert forbidden not in baseline
    origins = cast(
        dict[tuple[int, int], Path], differential_matrix["installed_origins"]
    )
    source_root = cast(Path, differential_matrix["installed_source_root"])
    empty_cache = cast(Path, differential_matrix["empty_install_cache"])
    assert empty_cache.is_dir()
    assert tuple(empty_cache.iterdir())
    assert all(
        origin.is_relative_to(source_root / "src") for origin in origins.values()
    )
    assert all(not origin.is_relative_to(REPO_ROOT) for origin in origins.values())


def test_gate_d_negative_results_are_typed_stable_and_message_free(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = _decoded(observations[_baseline_key()])
    assert baseline["negative"] == EXPECTED_REVIEW_SUMMARY["negative"]
    negative = cast(dict[str, object], baseline["negative"])
    assert negative["non_verified_admission"] == "rejected"
    assert negative["cross_snapshot_ref"] == "rejected"
    assert all(
        type(item[2]) is int and type(item[3]) is int
        for item in cast(list[list[object]], negative["pure_rejections"])
    )


def test_gate_c_historical_formats_and_canonical_bytes_are_zero_delta(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(dict[str, bytes], differential_matrix["observations"])
    baseline = _decoded(observations[_baseline_key()])
    assert baseline["phase61_marker"] == ("format=e:pietto.project-ir-inspection.v1")
    assert baseline["phase62_marker"] == "format=t:pietto.phase62-inspection.v1"
    phase61 = cast(str, baseline["phase61_canonical_bytes"]).encode("utf-8")
    phase62 = cast(str, baseline["phase62_canonical_bytes"]).encode("utf-8")
    assert len(phase61) == EXPECTED_REVIEW_SUMMARY["phase61_size"]
    assert (
        hashlib.sha256(phase61).hexdigest() == EXPECTED_REVIEW_SUMMARY["phase61_sha256"]
    )
    assert len(phase62) == EXPECTED_REVIEW_SUMMARY["phase62_size"]
    assert (
        hashlib.sha256(phase62).hexdigest() == EXPECTED_REVIEW_SUMMARY["phase62_sha256"]
    )


def test_gate_c_probe_is_self_contained_batched_and_uses_only_normal_builders() -> None:
    source = PROBE.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert not any(module.startswith("test_") for module in imported_modules)
    assert all(module != "subprocess" for module in imported_modules)
    assert "subprocess.run(" not in source
    for builder in (
        "check_project_parse_only",
        "build_empty_project_semantic_result",
        "build_project_completed_semantic_result",
        "build_project_query_block_ir",
        "verify_project_query_block_ir",
        "build_project_query_block_ir_analysis_bundle",
        "build_project_query_block_ir_inspection",
        "build_project_ir_inspection",
        "build_project_phase62_inspection",
    ):
        assert builder in source
    assert source.count("_construction(") == 3
    assert len(probe.SCENARIO_MANIFEST) == 35
    for scenario in (
        "plain",
        "joined",
        "multi_join",
        "filtered",
        "grouped",
        "global",
        "satisfying",
        "hidden_qualify",
        "left_selected_hidden",
        "mixed",
        "rebound_two",
        "left_joined",
        "semantic_bad",
        "stale_join",
    ):
        assert scenario in probe.MAIN_SOURCE
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "lru_cache",
        "functools.cache",
        "shelve",
        "pickle",
    ):
        assert forbidden not in source


def test_authority_closure_matrix_precedes_production_and_freezes_roots() -> None:
    document = SPEC.read_text(encoding="utf-8")
    for phrase in (
        "## Authority Closure Matrix",
        "active output -> entry.active_output",
        "not row_outputs[-1]",
        "active properties -> entry.active_properties",
        "not row_properties[-1]",
        "final field -> retained Slice12 identity",
        "not name/ordinal reconstruction",
        "pietto.phase63-query-block-ir-inspection.v1",
        "Slice 16 is `NEXT / NOT IMPLEMENTED`",
    ):
        assert phrase in document
