"""Editor overlays: a project check reads an open buffer in place of its file,
and emission, compiled builds and package code refuse that buffer by type."""

from __future__ import annotations

import contextlib
import functools
import io
import json
from pathlib import Path

import pytest

import _pietto_project_package as package
import _pietto_sql_emission as probe
from pietto import cli
from pietto._project import (
    check,
    package_graph,
    project_compiled_build,
    project_sql_emission_cli as emission_cli,
    project_sql_emission_contract,
)
from pietto._project.model import build_empty_project_semantic_result
from pietto._project.package_graph import PackageGraphOutcome, _build_package_graph
from pietto._project.package_inspection import _build_package_inspection_fact_set
from pietto._project.project_sql_emission_cli import emit_project
from pietto._project.project_sql_plan_literals import ProjectSQLLiteralPolicy
from pietto._project.trusted_source import (
    ProjectOverlaySource,
    ProjectSource,
    ProjectTrustedSourceSnapshot,
)

TOML = 'schema_version = 2\n\n[sources]\ninclude = ["*.pietto"]\n'
MODELS = """shape User:
    id: UUID
    email: Text | None
    deleted_at: Timestamp | None

source users: User = postgres.table("public.users")

export (
    shape User,
    source users,
)
"""
A_OK = """from "models.pietto" import (
    source users,
)

table active_users:
    from users
    where deleted_at is None
    select:
        id
        email
"""
A_BAD = A_OK.replace("where deleted_at is None", "where nope_a is None")


def _project(tmp_path: Path, **sources: str) -> Path:
    root = tmp_path / "harbor"
    root.mkdir()
    (root / "pietto.toml").write_text(TOML, encoding="utf-8")
    # Byte-exact on every platform, as the tests compare the texts read.
    for name, text in sources.items():
        (root / f"{name}.pietto").write_text(text, encoding="utf-8", newline="\n")
    return root


def _cli_json(root: Path) -> dict[str, object]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        cli.main(["check", "--project", str(root), "--format", "json"])
    return json.loads(out.getvalue())


def test_an_overlay_replaces_only_the_read_of_its_selected_file(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, models=MODELS, a=A_OK)
    before = check.check_project_diagnostics(root, overlays={})
    assert before.errors == () and before.diagnostics == ()
    assert before.paths == ("a.pietto", "models.pietto")
    assert before.texts == {"a.pietto": A_OK, "models.pietto": MODELS}

    parsed = check.check_project_parse_only(
        root,
        overlays={"a.pietto": A_BAD, "pietto.toml": "broken", "nope.pietto": "x"},
    )
    assert [type(item) for item in parsed.trusted_source_snapshots] == [
        ProjectOverlaySource,
        ProjectTrustedSourceSnapshot,
    ]
    report = check.check_project_diagnostics(root, overlays={"a.pietto": A_BAD})
    assert [(d.code, d.location.path) for d in report.diagnostics] == [
        ("PIE-S2102", "a.pietto")
    ]
    assert report.texts["a.pietto"] == A_BAD
    # The disk is unchanged, and the CLI reads the disk.
    assert (root / "a.pietto").read_text(encoding="utf-8") == A_OK
    assert _cli_json(root)["diagnostics"] == []


def test_diagnostics_only_project_checks_do_not_build_editor_facts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _project(tmp_path, models=MODELS, a=A_OK)

    def unexpected(_: object) -> object:
        raise AssertionError("editor facts must stay out of diagnostics-only checks")

    monkeypatch.setattr(check, "_project_editor_facts", unexpected)
    assert check.check_project_diagnostics(root, overlays={}).diagnostics == ()


def test_an_overlay_reads_a_file_the_disk_cannot_and_keeps_the_size_limit(
    tmp_path: Path,
) -> None:
    root = _project(tmp_path, models=MODELS)
    (root / "a.pietto").write_bytes(b"\xff\xfe")
    assert [e.kind.value for e in _report(root, {}).errors] == ["source_read"]
    assert _report(root, {"a.pietto": A_OK}).diagnostics == ()

    oversized = _report(root, {"a.pietto": "#" * 1_048_577})
    assert [(d.code, d.location.path) for d in oversized.diagnostics] == [
        ("PIE-P1006", "a.pietto")
    ]
    assert "a.pietto" not in oversized.texts


def test_the_report_without_overlays_is_the_cli_project_check(tmp_path: Path) -> None:
    b_bad = A_BAD.replace("active_users", "other").replace("nope_a", "nope_b")
    root = _project(tmp_path, models=MODELS, a=A_BAD, b=b_bad)
    report = _report(root, {})
    expected = _cli_json(root)["diagnostics"]
    assert isinstance(expected, list)
    assert [
        (d.code, d.location.path, d.location.line, d.location.column)
        for d in report.diagnostics
    ] == [
        (
            item["code"],
            item["location"]["path"],
            item["location"]["line"],
            item["location"]["column"],
        )
        for item in expected
    ]


def test_emission_refuses_an_overlay_by_type_even_with_the_disk_text(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = probe.fixture("postgres")
    root = tmp_path / "project"
    root.mkdir()
    (root / "pietto.toml").write_text(probe.CONFIG, encoding="utf-8")
    sources = probe.source_files(item["source"])
    # Byte-exact on every platform, so the overlays equal the disk text.
    for file, content in sources.items():
        (root / file).write_text(content, encoding="utf-8", newline="\n")
    (root / "contract.json").write_text(item["contract"], encoding="utf-8")

    def emit() -> tuple[str, list[str]]:
        outcome, _ = emit_project(
            root,
            "main.pietto",
            "table",
            "result",
            "postgres",
            "contract.json",
            ProjectSQLLiteralPolicy(item["policy"]),
        )
        return outcome.status, [error.message for error in outcome.cli_errors]

    assert emit() == ("VERIFIED", [])
    monkeypatch.setattr(
        emission_cli,
        "check_project_parse_only",
        functools.partial(check.check_project_parse_only, overlays=sources),
    )
    assert emit() == ("INPUT_REJECTED", ["Invalid current planning roots."])


def test_a_compiled_build_refuses_an_overlay_by_type_past_emission(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    item = probe.fixture("postgres")
    monkeypatch.setattr(
        check,
        "check_project_parse_only",
        functools.partial(
            check.check_project_parse_only,
            overlays=probe.source_files(item["source"]),
        ),
    )
    # Without emission's own refusal, an artifact reaches the compiled build.
    monkeypatch.setattr(project_sql_emission_contract, "require_trusted_sources", _all)
    _, outcome = probe.build_case(
        tmp_path / "project", item["source"], item["contract"], item["policy"]
    )
    with pytest.raises(TypeError, match="not editor buffers"):
        project_compiled_build.build_compiled(outcome.artifact)
    monkeypatch.setattr(project_compiled_build, "require_trusted_sources", _all)
    project_compiled_build.build_compiled(outcome.artifact)


def test_a_package_graph_refuses_overlay_lineage_by_type(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    digest = package._write_package(tmp_path / "packages", "root")
    inspection = _build_package_inspection_fact_set(
        package._plan(tmp_path / "packages", "root", digest)
    )
    text = package._SOURCE_A.decode("utf-8")
    root = _project(tmp_path, main=text)

    def graph() -> tuple[PackageGraphOutcome, list[str]]:
        parsed = check.check_project_parse_only(root, overlays={"main.pietto": text})
        facts = build_empty_project_semantic_result(parsed)
        assert facts.module_package_identity_facts is not None
        result = _build_package_graph(
            inspection, module_identity_facts=(facts.module_package_identity_facts,)
        )
        return result.outcome, [error.message for error in result.errors]

    assert graph() == (
        PackageGraphOutcome.ERROR,
        [
            "Package graph construction failed: "
            "Project sources must be trusted reads, not editor buffers."
        ],
    )
    monkeypatch.setattr(package_graph, "require_trusted_sources", _all)
    assert graph() == (PackageGraphOutcome.SUCCESS, [])


def _all(sources: tuple[ProjectSource, ...]) -> tuple[ProjectSource, ...]:
    """`require_trusted_sources` without its refusal, to show it is the cause."""

    return sources


def _report(root: Path, overlays: dict[str, str]) -> check.ProjectDiagnosticsReport:
    return check.check_project_diagnostics(root, overlays=overlays)
