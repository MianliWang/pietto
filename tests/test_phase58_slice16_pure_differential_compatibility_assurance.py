from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import site
import subprocess
import sys
from typing import cast

import pytest

import _pietto_project_explain_differential_probe as probe


REPO_ROOT = Path(__file__).resolve().parents[1]
PROBE = REPO_ROOT / "tests/_pietto_project_explain_differential_probe.py"
SCENARIOS = REPO_ROOT / "tests/_pietto_project_explain_scenarios.py"
SPEC = (
    REPO_ROOT
    / "docs/spec/phase58-slice16-pure-differential-compatibility-assurance-v1.md"
)
SEEDS = ("0", "1", "7", "4294967295")
SUPPORTED_INTERPRETERS = ((3, 12), (3, 13))

# One common, named, per-surface authority is consumed unchanged by Python
# 3.12, Python 3.13, every seed, both relocation forms, and the installed wheel.
EXPECTED_SURFACE_SHA256: dict[str, object] = {
    "observation_format": "pietto.project-explain-differential.v1",
    "package_version": "0.1.0",
    "scenarios": {
        "matrix": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "2a0334b7cbe1bf1368f246a4e1412219841d94ac5aa750c011b7c65c9785f9dd"
            ),
            "json_sha256": (
                "b29580fc02151e73d6212712a5e0e3eb86ebad1774ac2d38f33a91ed795b6d10"
            ),
            "text_sha256": (
                "0e4bdda45c8c759f8a5a0fdd4a4fbef20e8ff4679f9198e31935ae96a8a08270"
            ),
        },
        "empty": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "6a6043b2e7514099f00934380b8d7203ea445212abaa4b3b9a7a7c92616a3f49"
            ),
            "json_sha256": (
                "99c05feac5eeb0f0841ef8314530f060cc401e339d281f205b563e07548302d8"
            ),
            "text_sha256": (
                "dd8714d8f5d2fbd4233ca5e09c0cfaa2b8b19561c15431f92cc48c01babb86a8"
            ),
        },
        "portable": {
            "runtime_outcome": "success",
            "cli_json_exit": 0,
            "cli_text_exit": 0,
            "structured_sha256": (
                "981f7f6006446f5a04115421557d4227dcd51b46c26bb918425ca6cb7511e909"
            ),
            "json_sha256": (
                "1761f542e847800e375ec04773f7351bfeeab38d1374808a81e257499f8b7729"
            ),
            "text_sha256": (
                "038d7fe3a7e33c278f12ab15975468f5cac14567adfeee0dfe4f1d3256c7e360"
            ),
        },
        "diagnostic": {
            "runtime_outcome": "diagnostic_error",
            "cli_json_exit": 1,
            "cli_text_exit": 1,
            "structured_sha256": (
                "0e80e0814a37f0243c9d469455d90a070debbe08150aa011e9dfe20508c0328f"
            ),
            "json_sha256": (
                "7bb804c7571a7d3cb922262c20efd293a4027d295fdbee4273aa700d6595e9f3"
            ),
            "text_sha256": (
                "58e57f83817004f922b957a7e29f174d4650b8fa88363cfe7987af27edac55b8"
            ),
        },
        "resource": {
            "runtime_outcome": "usage_or_resource_error",
            "cli_json_exit": 2,
            "cli_text_exit": 2,
            "structured_sha256": (
                "52121819e26899ffd5ccb182a8bce54f59ef6ed0e65b70c9052c47242f169505"
            ),
            "json_sha256": (
                "ba496ad2754a547167b3ac49933d5900156b687fea545977ee935c9e93bf77cd"
            ),
            "text_sha256": (
                "ca57557b8a7e387a5c7b9d1e4fcb31983741b71d4857bd1bdfce4b41ef03a24c"
            ),
        },
    },
    "single_file": {
        "text_exit": 0,
        "json_exit": 0,
        "text_sha256": (
            "2d3e0e50dfa0246ec1bf8269ddae764d23cf111afcd945f6ea1f150ef3008fdc"
        ),
        "json_sha256": (
            "02e6e6cc7eb78370f930c82c881f9728b609dac65e36ec807ce80f8c359c76d3"
        ),
    },
}


def _site_packages() -> str:
    candidates = tuple(site.getsitepackages())
    assert candidates
    return str(candidates[0])


def _interpreter_version(executable: str) -> tuple[int, int] | None:
    try:
        completed = subprocess.run(
            (
                executable,
                "-c",
                "import sys; print(*sys.version_info[:2])",
            ),
            check=True,
            text=True,
            capture_output=True,
        )
        return cast(tuple[int, int], tuple(map(int, completed.stdout.split())))
    except (OSError, subprocess.CalledProcessError, ValueError):
        return None


def _available_supported_interpreters() -> dict[tuple[int, int], str]:
    current = sys.version_info[:2]
    assert current in SUPPORTED_INTERPRETERS
    available = {current: sys.executable}
    for version in SUPPORTED_INTERPRETERS:
        if version == current:
            continue
        executable = shutil.which(f"python{version[0]}.{version[1]}")
        if executable is not None and _interpreter_version(executable) == version:
            available[version] = executable
    return available


def _environment(source_root: Path | None, seed: str, ambient: str) -> dict[str, str]:
    environment = os.environ.copy()
    for name in ("PYTHONHOME", "PYTHONPATH", "VIRTUAL_ENV"):
        environment.pop(name, None)
    environment["PYTHONHASHSEED"] = seed
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PIETTO_SLICE16_IRRELEVANT"] = ambient
    if source_root is not None:
        environment["PYTHONPATH"] = os.pathsep.join(
            (str(source_root / "src"), _site_packages())
        )
    return environment


def _run_probe(
    executable: str,
    probe_path: Path,
    workspace: Path,
    *,
    source_root: Path | None,
    seed: str,
    ambient: str,
) -> dict[str, object]:
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
    return cast(dict[str, object], json.loads(completed.stdout))


def _relocate_source(target: Path) -> Path:
    shutil.copytree(
        REPO_ROOT / "src",
        target / "src",
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
    )
    tests = target / "tests"
    tests.mkdir()
    shutil.copyfile(PROBE, tests / PROBE.name)
    shutil.copyfile(SCENARIOS, tests / SCENARIOS.name)
    return tests / PROBE.name


def _installed_python(root: Path) -> tuple[str, Path, Path, Path]:
    dist = root / "dist"
    wheel_source_root = root / "wheel-source"
    wheel_target = wheel_source_root / "src"
    empty_cache = root / "empty-uv-cache"
    dist.mkdir()
    wheel_source_root.mkdir()
    empty_cache.mkdir()
    assert not tuple(empty_cache.iterdir())
    subprocess.run(
        ("uv", "build", "--offline", "--wheel", "--out-dir", str(dist)),
        check=True,
        cwd=REPO_ROOT,
        capture_output=True,
        env=_environment(None, "0", "wheel-build"),
    )
    wheels = tuple(dist.glob("pietto-0.1.0-*.whl"))
    assert len(wheels) == 1
    install_environment = _environment(None, "0", "wheel-install")
    install_environment["UV_CACHE_DIR"] = str(empty_cache)
    subprocess.run(
        (
            "uv",
            "pip",
            "install",
            "--offline",
            "--no-deps",
            "--target",
            str(wheel_target),
            str(wheels[0]),
        ),
        check=True,
        capture_output=True,
        cwd=root,
        env=install_environment,
    )
    origin = subprocess.run(
        (
            sys.executable,
            "-c",
            "from pathlib import Path; import pietto; "
            "print(Path(pietto.__file__).resolve())",
        ),
        check=True,
        text=True,
        capture_output=True,
        cwd=root,
        env=_environment(wheel_source_root, "0", "origin"),
    )
    return sys.executable, Path(origin.stdout.strip()), wheel_source_root, empty_cache


def _canonical_bytes(value: object) -> bytes:
    if type(value) is str:
        return value.encode("utf-8")
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=False,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _surface_manifest(observation: dict[str, object]) -> dict[str, object]:
    scenarios = cast(dict[str, dict[str, object]], observation["scenarios"])
    single = cast(dict[str, object], observation["single_file"])
    return {
        "observation_format": observation["observation_format"],
        "package_version": observation["package_version"],
        "scenarios": {
            name: {
                "runtime_outcome": scenarios[name]["runtime_outcome"],
                "cli_json_exit": scenarios[name]["cli_json_exit"],
                "cli_text_exit": scenarios[name]["cli_text_exit"],
                "structured_sha256": _digest(scenarios[name]["structured"]),
                "json_sha256": _digest(scenarios[name]["json_document"]),
                "text_sha256": _digest(scenarios[name]["text_document"]),
            }
            for name in probe.SCENARIO_ORDER
        },
        "single_file": {
            "text_exit": single["text_exit"],
            "json_exit": single["json_exit"],
            "text_sha256": _digest(single["text_document"]),
            "json_sha256": _digest(single["json_document"]),
        },
    }


@pytest.fixture(scope="module")
def differential_matrix(
    tmp_path_factory: pytest.TempPathFactory,
) -> dict[str, object]:
    observations: dict[str, dict[str, object]] = {}
    for seed in SEEDS:
        observations[f"seed:{seed}"] = _run_probe(
            sys.executable,
            PROBE,
            tmp_path_factory.mktemp(f"seed-{seed}"),
            source_root=REPO_ROOT,
            seed=seed,
            ambient=f"seed-{seed}",
        )

    interpreters = _available_supported_interpreters()
    for version, executable in interpreters.items():
        key = f"python{version[0]}.{version[1]}"
        observations[key] = (
            observations["seed:0"]
            if executable == sys.executable
            else _run_probe(
                executable,
                PROBE,
                tmp_path_factory.mktemp(key),
                source_root=REPO_ROOT,
                seed="0",
                ambient=key,
            )
        )

    observations["project-relocated"] = _run_probe(
        sys.executable,
        PROBE,
        tmp_path_factory.mktemp("project-relocated"),
        source_root=REPO_ROOT,
        seed="0",
        ambient="project-relocated",
    )
    relocated_root = tmp_path_factory.mktemp("source-relocated")
    relocated_probe = _relocate_source(relocated_root)
    observations["source-relocated"] = _run_probe(
        sys.executable,
        relocated_probe,
        tmp_path_factory.mktemp("source-relocated-project"),
        source_root=relocated_root,
        seed="0",
        ambient="source-relocated",
    )

    wheel_root = tmp_path_factory.mktemp("installed-wheel")
    (
        installed_python,
        installed_origin,
        installed_source_root,
        empty_install_cache,
    ) = _installed_python(wheel_root)
    observations["installed-wheel"] = _run_probe(
        installed_python,
        PROBE,
        tmp_path_factory.mktemp("installed-project"),
        source_root=installed_source_root,
        seed="0",
        ambient="installed-wheel",
    )
    return {
        "observations": observations,
        "interpreters": interpreters,
        "installed_origin": installed_origin,
        "installed_source_root": installed_source_root,
        "empty_install_cache": empty_install_cache,
    }


def test_current_source_matches_one_human_reviewable_common_reference(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    assert _surface_manifest(observations["seed:0"]) == EXPECTED_SURFACE_SHA256


def test_four_fixed_hash_seeds_preserve_exact_values_and_authoritative_order(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    assert SEEDS == ("0", "1", "7", "4294967295")
    assert all(observations[f"seed:{seed}"] == observations["seed:0"] for seed in SEEDS)


def test_available_supported_interpreters_consume_the_same_reference(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    interpreters = cast(dict[tuple[int, int], str], differential_matrix["interpreters"])
    assert sys.version_info[:2] in interpreters
    for version in interpreters:
        assert _surface_manifest(observations[f"python{version[0]}.{version[1]}"]) == (
            EXPECTED_SURFACE_SHA256
        )


def test_project_and_source_relocation_ignore_cwd_and_unrelated_ambient_state(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    for key in ("project-relocated", "source-relocated"):
        assert observations[key] == observations["seed:0"]


def test_installed_wheel_matches_source_from_fresh_cache_and_wheel_target(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    origin = cast(Path, differential_matrix["installed_origin"])
    source_root = cast(Path, differential_matrix["installed_source_root"])
    empty_cache = cast(Path, differential_matrix["empty_install_cache"])
    assert origin.is_relative_to(source_root / "src")
    assert not origin.is_relative_to(REPO_ROOT)
    assert empty_cache.is_dir()
    assert observations["installed-wheel"] == observations["seed:0"]


def test_structured_json_text_status_and_order_surfaces_are_not_normalized(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    baseline = observations["seed:0"]
    scenarios = cast(dict[str, dict[str, object]], baseline["scenarios"])
    matrix = cast(dict[str, object], scenarios["matrix"]["structured"])
    payload = cast(dict[str, object], matrix["payload"])
    packages = cast(dict[str, object], payload["package_requirements"])
    compatibility = cast(dict[str, object], payload["compatibility"])
    package_rows = cast(list[dict[str, object]], packages["packages"])
    target_rows = cast(list[dict[str, object]], compatibility["targets"])
    rows = cast(list[dict[str, object]], compatibility["rows"])
    assert [
        cast(dict[str, object], package["coordinate"])["name"]
        for package in package_rows
    ] == [
        "dependency",
        "root",
    ]
    assert [target["database_release"] for target in target_rows] == [
        "18",
        "17",
    ]
    assert [
        [cell["checked_status"] for cell in cast(list[dict[str, object]], row["cells"])]
        for row in rows
    ] == [
        ["satisfied", "unknown"],
        ["satisfied", "unknown"],
        ["unsupported", "unknown"],
        ["absent", "absent"],
        ["conflict", "unknown"],
    ]
    for scenario in probe.SCENARIO_ORDER:
        document = cast(str, scenarios[scenario]["json_document"])
        text = cast(str, scenarios[scenario]["text_document"])
        assert document.endswith("\n") and not document.endswith("\n\n")
        assert text.endswith("\n") and not text.endswith("\n\n")


def test_failure_and_single_file_surfaces_share_the_same_cross_environment_contract(
    differential_matrix: dict[str, object],
) -> None:
    observations = cast(
        dict[str, dict[str, object]], differential_matrix["observations"]
    )
    baseline = observations["seed:0"]
    scenarios = cast(dict[str, dict[str, object]], baseline["scenarios"])
    assert (
        scenarios["diagnostic"]["runtime_outcome"],
        scenarios["diagnostic"]["cli_json_exit"],
        scenarios["diagnostic"]["cli_text_exit"],
    ) == ("diagnostic_error", 1, 1)
    assert (
        scenarios["resource"]["runtime_outcome"],
        scenarios["resource"]["cli_json_exit"],
        scenarios["resource"]["cli_text_exit"],
    ) == ("usage_or_resource_error", 2, 2)
    single = cast(dict[str, object], baseline["single_file"])
    assert single["text_exit"] == single["json_exit"] == 0
    assert cast(str, single["text_document"]).startswith(
        "Semantic Metadata Artifact v1\n"
    )


def test_spec_and_harness_lock_owners_without_artificial_normalization() -> None:
    document = " ".join(SPEC.read_text(encoding="utf-8").split())
    for required in (
        "BYTE_EXACT_INVARIANT",
        "STRUCTURAL_EXACT_INVARIANT",
        "SEMANTIC_INVARIANT_WITH_AUTHORIZED_LOCATION_VARIATION",
        "ENVIRONMENT_SPECIFIC_BY_CONTRACT",
        "PYTHONHASHSEED = 0, 1, 7, 4294967295",
        "scripts/check_generated.py",
        "scripts/check_goldens.py",
        "scripts/package_smoke.py",
        "PHASE58_SLICE16_SELF_OWNED_OPEN = 0",
    ):
        assert required in document
    source = "\n".join(path.read_text(encoding="utf-8") for path in (PROBE, SCENARIOS))
    for forbidden in (
        "sort_keys=True",
        ".sort(",
        "sorted(",
        "replace(str(workspace)",
        ".strip()",
        "ProjectExplainPayload(",
        "ProjectExplainEnvelope(",
    ):
        assert forbidden not in source
