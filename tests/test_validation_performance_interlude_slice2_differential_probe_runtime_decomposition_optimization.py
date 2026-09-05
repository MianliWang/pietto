from __future__ import annotations

import inspect
from pathlib import Path
import subprocess

import _pietto_differential_process_acquisition as acquisition_owner
import _pietto_phase59_graph_differential_probe as phase59_probe
import _pietto_phase60_window_differential_probe as phase60_probe
import _pietto_phase61_project_ir_differential_probe as phase61_probe
import _pietto_phase62_join_differential_probe as phase62_probe
import _pietto_phase63_query_block_ir_differential_probe as phase63_probe
import _pietto_project_explain_differential_probe as phase58_probe
import _pietto_project_explain_scenarios as scenarios
import test_phase58_slice16_pure_differential_compatibility_assurance as phase58
import test_phase59_slice11_differential_compatibility_assurance as phase59
import test_phase60_slice12_differential_compatibility as phase60
import test_phase61_slice11_differential_compatibility as phase61
import test_phase62_slice15_real_authored_e2e_python_differential_metamorphic_join_assurance as phase62
import test_phase63_slice15_inspection_pure_boundary_real_e2e_differential_metamorphic_assurance as phase63


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT
    / "docs/spec/validation-performance-interlude-slice2-differential-probe-runtime-decomposition-optimization-v1.md"
)


def _section(document: str, heading: str) -> str:
    marker = f"## {heading}\n"
    assert document.count(marker) == 1
    start = document.index(marker) + len(marker)
    end = document.find("\n## ", start)
    return document[start:] if end == -1 else document[start:end]


def _two_interpreters() -> dict[tuple[int, int], str]:
    """Evaluate the frozen logical matrices on the published two-interpreter set."""

    return {(3, 13): "python3.13", (3, 12): "python3.12"}


def _result(process: subprocess.CompletedProcess[bytes]) -> tuple[int, bytes, bytes]:
    return process.returncode, process.stdout, process.stderr


def test_cli_pair_preserves_order_failures_and_has_no_observation_cache() -> None:
    good = ("--version",)
    bad = ("not-a-command",)
    forward_good, forward_bad = scenarios._run_cli_pair(good, bad, REPO_ROOT)
    reverse_bad, reverse_good = scenarios._run_cli_pair(bad, good, REPO_ROOT)

    assert _result(forward_good) == _result(reverse_good)
    assert _result(forward_bad) == _result(reverse_bad)
    assert forward_good.returncode == 0
    assert forward_good.stdout == b"pietto 0.1.0\n"
    assert forward_good.stderr == b""
    assert forward_bad.returncode != 0
    assert forward_bad.stdout == b""
    assert forward_bad.stderr

    source = inspect.getsource(scenarios._run_cli_pair) + scenarios._CLI_PAIR_CODE
    for forbidden in ("lru_cache", "functools.cache", "shelve", "pickle"):
        assert forbidden not in source
    assert "len(commands) == 2" in source
    assert "main(arguments)" in source


def test_project_cli_pair_is_order_independent_for_the_same_variant(
    tmp_path: Path,
) -> None:
    project = scenarios._write_single_project(
        tmp_path,
        scenarios._manifest(1),
        profiles=(scenarios._profile("base", "18"),),
        targets=(scenarios._target("base", "18", None),),
        name="project",
    )
    cwd = tmp_path / "cwd"
    cwd.mkdir()
    json_command = ("explain", "--project", project.as_posix(), "--format", "json")
    text_command = ("explain", "--project", project.as_posix())

    forward_json, forward_text = scenarios._run_cli_pair(
        json_command,
        text_command,
        cwd,
    )
    reverse_text, reverse_json = scenarios._run_cli_pair(
        text_command,
        json_command,
        cwd,
    )

    assert _result(forward_json) == _result(reverse_json)
    assert _result(forward_text) == _result(reverse_text)
    assert forward_json.returncode == forward_text.returncode == 0
    assert forward_json.stderr == forward_text.stderr == b""


def test_all_differential_dimensions_and_independent_builds_remain_exact() -> None:
    assert (
        phase58.SEEDS
        == phase59.SEEDS
        == phase60.SEEDS
        == phase61.SEEDS
        == phase62.SEEDS
        == phase63.SEEDS
        == (
            "0",
            "1",
            "7",
            "4294967295",
        )
    )
    assert (
        phase58.SUPPORTED_INTERPRETERS
        == phase59.SUPPORTED_INTERPRETERS
        == phase60.SUPPORTED_INTERPRETERS
        == phase61.SUPPORTED_INTERPRETERS
        == phase62.SUPPORTED_INTERPRETERS
        == phase63.SUPPORTED_INTERPRETERS
        == (
            (3, 12),
            (3, 13),
        )
    )
    assert phase58_probe.SCENARIO_ORDER == (
        "matrix",
        "empty",
        "portable",
        "diagnostic",
        "resource",
    )

    phase58_fixture = inspect.getsource(phase58.differential_matrix)
    for dimension in (
        'observations[f"seed:{seed}"]',
        'observations["project-relocated"]',
        'observations["source-relocated"]',
        'observations["installed-wheel"]',
    ):
        assert dimension in phase58_fixture

    phase59_fixture = inspect.getsource(phase59.differential_matrix)
    for dimension in (
        'observations[f"seed:{seed}"]',
        'observations["project-relocated"]',
        'observations["source-relocated"]',
        'observations["installed-wheel"]',
        'key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"',
    ):
        assert dimension in phase59_fixture

    graph_observation = inspect.getsource(phase59_probe.observation)
    assert graph_observation.count("_real_graph(") == 2
    assert "first_inspection == second_inspection" in graph_observation
    assert "_runtime_refs_are_distinct(first, second)" in graph_observation

    phase60_fixture = inspect.getsource(phase60.differential_matrix)
    for dimension in (
        'observations[f"seed:{seed}"]',
        'observations["project-relocated"]',
        'observations["source-relocated"]',
        'observations["installed-wheel"]',
        'key = f"combined:python{version[0]}.{version[1]}:seed{seed}:relocated"',
    ):
        assert dimension in phase60_fixture
    window_observation = inspect.getsource(phase60_probe.observation)
    assert window_observation.count("_construction(") == 2
    assert "first == second" in window_observation
    assert "first_call.named_use.occurrence != second_call.named_use.occurrence" in (
        window_observation
    )

    phase61_fixture = inspect.getsource(phase61.differential_matrix)
    for dimension in (
        'observations[f"seed:{seed}"]',
        'observations["project-relocated"]',
        'observations["source-relocated"]',
        'observations["installed-wheel"]',
        'f"seed{seed}:relocated"',
    ):
        assert dimension in phase61_fixture
    project_ir_observation = inspect.getsource(phase61_probe.observation)
    assert project_ir_observation.count("_construction(") == 2
    assert "first_value == second_value" in project_ir_observation
    assert "shifted.canonical_bytes != first.canonical_bytes" in (
        project_ir_observation
    )

    phase62_fixture = inspect.getsource(phase62.differential_matrix)
    for dimension in (
        'key = f"source:{label}:seed:{seed}"',
        'key = f"relocated:{label}:seed:7"',
        'key = f"installed:{label}:seed:7"',
    ):
        assert dimension in phase62_fixture
    join_observation = inspect.getsource(phase62_probe.observation)
    assert join_observation.count("_construction(") == 2
    assert "first == second" in join_observation
    assert "runtime_identities_distinct" in join_observation

    phase63_fixture = inspect.getsource(phase63.differential_matrix)
    for dimension in (
        'key = f"source:{label}:seed:{seed}"',
        'key = f"relocated:{label}:seed:7"',
        'key = f"installed:{label}:seed:7"',
    ):
        assert dimension in phase63_fixture
    query_block_observation = inspect.getsource(phase63_probe.observation)
    assert query_block_observation.count("_construction(") == 2
    assert "first_product.canonical_bytes != second_product.canonical_bytes" in (
        query_block_observation
    )
    assert "normal_queries != reverse_queries" in query_block_observation


def test_process_reduction_preserves_variants_cli_calls_and_graph_builds() -> None:
    phase58_variants = 8
    phase59_variants = 10
    outer_probes = phase58_variants + phase59_variants
    phase58_cli_calls = phase58_variants * (len(phase58_probe.SCENARIO_ORDER) + 1) * 2
    phase59_cli_calls = phase59_variants * 2
    semantic_cli_calls = phase58_cli_calls + phase59_cli_calls

    assert (phase58_variants, phase59_variants, outer_probes) == (8, 10, 18)
    assert semantic_cli_calls == 116
    assert phase59_variants * 2 == 20
    assert (
        len(acquisition_owner.family_requests("phase58", _two_interpreters()))
        == phase58_variants
    )
    assert (
        len(acquisition_owner.family_requests("phase59", _two_interpreters()))
        == phase59_variants
    )

    # Later acquisition batching may lower the physical process count further,
    # so the durable law is one separate `main(arguments)` call per semantic
    # command with its own fresh capture, not a fixed number of children.
    pair_source = inspect.getsource(scenarios._run_cli_pair)
    assert "session.run(first, cwd), session.run(second, cwd)" in pair_source
    assert scenarios._CLI_PAIR_CODE.count("main(arguments)") == 1
    assert scenarios._CLI_WORKER_CODE.count("main(arguments)") == 1
    session_source = inspect.getsource(scenarios.CliWorkerSession) + inspect.getsource(
        scenarios.cli_worker_session
    )
    for forbidden in ("lru_cache", "functools.cache", "shelve", "pickle"):
        assert forbidden not in session_source
        assert forbidden not in scenarios._CLI_WORKER_CODE

    phase58_source = inspect.getsource(phase58_probe)
    phase59_source = inspect.getsource(phase59_probe)
    phase60_source = inspect.getsource(phase60_probe)
    phase61_source = inspect.getsource(phase61_probe)
    phase62_source = inspect.getsource(phase62_probe)
    phase63_source = inspect.getsource(phase63_probe)
    assert phase58_source.count("_run_cli_pair(") == 2
    assert phase59_source.count("_run_cli_pair(") == 1
    assert "subprocess.run(" not in phase58_source
    assert "subprocess.run(" not in phase59_source
    assert phase60_source.count("_run_cli_pair(") == 1
    assert "subprocess.run(" not in phase60_source
    assert "subprocess.run(" not in phase61_source
    assert phase61_source.count("build_project_ir_pipeline(") == 2
    assert "subprocess.run(" not in phase62_source
    assert phase62_source.count("build_project_multifact_analysis(") == 1
    assert phase62_source.count("build_project_phase62_inspection(") == 1
    assert "subprocess.run(" not in phase63_source
    assert phase63_source.count("build_project_query_block_ir_inspection(") == 2
    assert phase63_source.count("build_project_phase62_inspection(") == 1
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "lru_cache",
        "functools.cache",
        "shelve",
        "pickle",
    ):
        assert forbidden not in phase61_source
        assert forbidden not in phase62_source
        assert forbidden not in phase63_source


def test_slice2_evidence_scope_and_handoff_are_exact() -> None:
    document = SPEC.read_text(encoding="utf-8")
    decomposition = " ".join(_section(document, "Runtime Decomposition").split())
    execution = " ".join(_section(document, "Execution Classification").split())
    optimization = " ".join(_section(document, "Optimization").split())
    performance = " ".join(
        _section(document, "Like-For-Like Performance Proof").split()
    )
    lifecycle = " ".join(_section(document, "Changed-Path And Lifecycle Lock").split())

    assert "repeated CLI startup/import" in decomposition
    for category in (
        "A — required independent variants",
        "B — deliberate independent reconstruction",
        "C — mechanically duplicated acquisition",
    ):
        assert category in execution
    assert "There is no cache, persistent observation, fallback" in optimization
    assert "median decreased" in performance
    assert "materially larger than observed timing noise" in performance
    assert "sole mutable lifecycle document reader" in lifecycle
    assert "Phase 60 = NOT ACTIVATED" in lifecycle
    assert (
        "VALIDATION_PERFORMANCE_INTERLUDE_SLICE3_REPOSITORY_READER_ACQUISITION_REUSE"
        in lifecycle
    )
