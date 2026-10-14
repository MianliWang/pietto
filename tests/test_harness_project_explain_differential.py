from __future__ import annotations

from pathlib import Path
import sys
from typing import cast


import _pietto_project_explain_differential_probe as probe


from _pietto_project_explain_differential import (
    REPO_ROOT,
    PROBE,
    SCENARIOS,
    SPEC,
    SEEDS,
    EXPECTED_SURFACE_SHA256,
    _surface_manifest,
    differential_matrix as differential_matrix,
)


# One common, named, per-surface authority is consumed unchanged by Python
# 3.12, Python 3.13, every seed, both relocation forms, and the installed wheel.


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
