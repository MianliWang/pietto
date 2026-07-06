from __future__ import annotations

from pathlib import Path

from _static_audit_helpers import normalized_text as _normalized
from _static_audit_helpers import read_text as _read

REPO_ROOT = Path(__file__).resolve().parents[1]

PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md"
)
SPEC_PATH = REPO_ROOT / "docs/spec/phase44-project-source-selection-scope-lock-v1.md"
PHASE37_PLAN_PATH = (
    REPO_ROOT / "docs/plan/phase-37-post-v02-aggregate-surface-expansion.md"
)
PHASE43_PLAN_PATH = (
    REPO_ROOT
    / "docs/plan/phase-43-let-binding-aggregate-and-grouped-query-integration-mvp.md"
)
PHASE43_SPEC_PATH = (
    REPO_ROOT
    / "docs/spec/phase43-let-binding-aggregate-grouped-integration-scope-lock-v1.md"
)
PHASE33_COMPLETION_TEST_PATH = REPO_ROOT / "tests/test_phase33_completion_audit.py"
PROJECT_EXPLAIN_SPEC_PATH = (
    REPO_ROOT / "docs/spec/project-explain-metadata-aggregation-boundary-v1.md"
)
PROJECT_ROOT_SPEC_PATH = (
    REPO_ROOT / "docs/spec/project-root-config-path-discovery-v1.md"
)
PROJECT_JSON_SPEC_PATH = REPO_ROOT / "docs/spec/project-json-v2-result-envelope-v1.md"
PROJECT_MULTIFILE_SPEC_PATH = REPO_ROOT / "docs/spec/project-multifile-semantics-v1.md"
PROJECT_PATH_SPEC_PATH = REPO_ROOT / "docs/spec/project-path-semantics-v1.md"
CLI_PATH = REPO_ROOT / "src/pietto/cli.py"
PROJECT_CONFIG_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/config.py"
PROJECT_SOURCE_SELECTION_SOURCE_PATH = (
    REPO_ROOT / "src/pietto/_project/source_selection.py"
)
PROJECT_CHECK_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/check.py"
PROJECT_JSON_SOURCE_PATH = REPO_ROOT / "src/pietto/_project/json_v2.py"
PROJECT_COMPAT_TEST_PATH = (
    REPO_ROOT / "tests/test_phase44_project_cli_package_compatibility.py"
)
PACKAGE_SMOKE_PATH = REPO_ROOT / "scripts/package_smoke.py"
PYPROJECT_PATH = REPO_ROOT / "pyproject.toml"


def _phase44_docs() -> str:
    return " ".join(_normalized(path) for path in (PLAN_PATH, SPEC_PATH))


def _parser_section(source: str, function_name: str) -> str:
    start = source.index(f"def _configure_{function_name}_parser")
    next_marker = source.find("\ndef ", start + 1)
    if next_marker == -1:
        return source[start:]
    return source[start:next_marker]


def test_slice1_artifacts_baseline_and_candidate_identity_are_locked() -> None:
    assert PLAN_PATH.is_file()
    assert SPEC_PATH.is_file()

    docs = _phase44_docs()
    for required in (
        "Phase 44 Slice 1 is Project Source Selection Scope Lock",
        "docs/spec/plan/static-audit/status planning work only and implements no behavior change",
        "baseline HEAD: `898764b4d85c3f3907d868a6b955be6735908887`",
        "baseline branch: `main`",
        "baseline subject: `Bump actions/setup-python from 6.2.0 to 6.3.0`",
        "latest completed language phase: Phase 43 Let Binding Aggregate And Grouped Query Integration MVP",
        "package version remains `0.1.0`",
        "no tag/release/publish/upload/signing/attestation is authorized by Slice 1",
        "Project Source Selection And Parse-only Project Check MVP",
        "Slice 1 does not implement config loading, source selection, glob expansion",
        "source reading, parser aggregation, Project JSON v2 input reporting",
        "Phase 44 Slice 4 is Deterministic Source Selection MVP",
        "implements only private deterministic source selection",
        "does not wire source selection into CLI behavior, Project JSON v2 output",
    ):
        assert required in docs, required

    for forbidden in (
        "Slice 1 implements config loading",
        "Slice 1 implements source selection",
        "Slice 1 implements parser aggregation",
        "Phase 44 is Arrow / PyArrow Schema Bridge MVP",
    ):
        assert forbidden not in docs, forbidden


def test_old_phase44_arrow_label_is_historical_only() -> None:
    phase37 = _normalized(PHASE37_PLAN_PATH)
    phase43_docs = " ".join(
        _normalized(path) for path in (PHASE43_PLAN_PATH, PHASE43_SPEC_PATH)
    )
    phase44_docs = _phase44_docs()

    for required in (
        "The following roadmap note is planning-only",
        "Phase 44: Arrow / PyArrow Schema Bridge MVP",
        "These future labels do not change current package metadata",
    ):
        assert required in phase37, required

    for required in (
        "old planning-only labels remain historical, non-authoritative context",
        "Phase 44: Arrow / PyArrow Schema Bridge MVP",
        "does not start Phase 44",
    ):
        assert required in phase43_docs, required

    for required in (
        "old Phase 37 planning-only label",
        "`Phase 44: Arrow / PyArrow Schema Bridge MVP` remains historical",
        "does not authorize Arrow, PyArrow, dataframe, materialization",
    ):
        assert required in phase44_docs, required


def test_current_project_mode_text_semantic_gate_and_json_parse_only_boundary() -> None:
    docs = _phase44_docs()
    phase33 = _normalized(PHASE33_COMPLETION_TEST_PATH)
    project_explain = _normalized(PROJECT_EXPLAIN_SPEC_PATH)
    cli_source = _read(CLI_PATH)
    json_source = _normalized(PROJECT_JSON_SOURCE_PATH)

    for required in (
        "Phase 33 delivered a conservative project-mode foundation",
        "text-mode `pietto check --project ROOT` root/config validation",
        "project JSON v2 for `pietto check --project ROOT --format json`",
        "Phase 33 did not implement source selection, TOML schema parsing, glob",
        "expansion, project source reading/parsing, multi-file semantic analysis",
        "project IR/SQL, project emit-sql, project explain, metadata aggregation",
    ):
        assert required in phase33, required

    for required in (
        "Current implemented project behavior remains limited to:",
        "pietto check --project ROOT",
        "That behavior validates only the explicit project root and direct `pietto.toml` presence",
        "It does not select, read, parse, analyze, or aggregate source files",
    ):
        assert required in project_explain, required

    for required in (
        "text-mode `pietto check --project ROOT` now routes through the private",
        "parse-only project check frontend",
        "`pietto check --project ROOT --format json` now routes through the private",
        "parse-only project check result",
        "Project JSON v2 `inputs[]` plus",
        "`result.check` counters for parsed/error selected sources",
        "root/config/source-selection failures that stop",
        "before parsing at `inputs: []` plus zero file counters",
        "`emit-sql --project` and `explain --project` remain rejected",
        "Project check OK: .",
        "Files checked: N",
        'status: "parsed"',
        "result.check.files_total: N",
    ):
        assert required in docs, required

    assert "check_project_parse_only(root)" in cli_source
    assert "Files checked: {len(parse_result.inputs)}" in cli_source
    for required in (
        '_JSON_INPUT_KIND = "source"',
        '_JSON_INPUT_STATUSES = frozenset({"parsed", "error"})',
        '"inputs": inputs',
        '"diagnostics": diagnostics',
        '"cli_errors": [_cli_error_to_json_dict(error) for error in result.errors]',
        '"files_total": len(inputs)',
        '"files_ok": files_ok',
        '"files_with_errors": files_with_errors',
    ):
        assert required in json_source, required
    assert "build_empty_project_semantic_result(parse_result)" in cli_source
    assert "_print_project_check_json(parse_result)" in cli_source


def test_source_selection_and_parse_only_readiness_is_repo_grounded() -> None:
    docs = _phase44_docs()
    project_root = _normalized(PROJECT_ROOT_SPEC_PATH)
    project_json = _normalized(PROJECT_JSON_SPEC_PATH)
    project_multifile = _normalized(PROJECT_MULTIFILE_SPEC_PATH)
    project_path = _normalized(PROJECT_PATH_SPEC_PATH)

    for required in (
        "Initial project discovery is a deterministic project-input reporting boundary",
        "configured source selection only",
        "deterministic file discovery/reporting",
        "normalized project-relative paths",
        "duplicate physical identity rejection",
        "An empty final source set is a project input error",
    ):
        assert required in project_root, required

    for required in (
        "The `inputs` array contains selected project sources in stable reporting order",
        "`path` | string | Normalized project-relative path",
        '`kind` | string | Initially `"source"`',
        '`status` | string | Initially `"parsed"` or `"error"`',
        "Source-read failures are reported as `cli_errors`",
        "Parser failures are reported as compiler `diagnostics`",
    ):
        assert required in project_json, required

    for required in (
        "read every selected file within the approved project budgets",
        "parse each readable file through the existing single-file parser boundary",
        "aggregate parser diagnostics without entering project semantic analysis",
        "It does not authorize semantic analysis of a partial project",
    ):
        assert required in project_multifile, required

    for required in (
        "The planned `[sources]` selection pipeline is:",
        "retain only regular files whose normalized path ends in `.pietto`",
        "Exclude patterns always win over include patterns",
        "`**` only as a complete segment",
        "There are no implicit default include patterns",
    ):
        assert required in project_path, required

    for required in (
        "deterministic project source selection",
        "source read plus parse-only project check",
        "Project JSON v2 `inputs[]` and `result.check` counters for project check",
        "stop before project semantic analysis",
    ):
        assert required in docs, required


def test_slice_sequence_allowlist_validation_and_stop_conditions_are_locked() -> None:
    docs = _phase44_docs()

    for required in (
        "| 1 | Project Source Selection Scope Lock |",
        "| 2 | Project Config Schema Contract |",
        "| 3 | Private Project Config Loader MVP |",
        "private config loader/schema validator only; no CLI or JSON behavior",
        "| 4 | Deterministic Source Selection MVP |",
        "private deterministic source selection only; no CLI or JSON behavior",
        "| 5 | Parse-only Project Check Frontend |",
        "| 6 | Project JSON v2 Inputs And Counters |",
        "| 7 | CLI / Package / Compatibility Hardening |",
        "tests/docs/static-audit compatibility hardening only; no production or package-smoke source changes",
        "| 8 | Completion Audit And Status Lock |",
        "complete docs/spec/static-audit/status lock only; no new behavior",
        "Phase 44 Slice 8 is Completion Audit And Status Lock",
        "Slice 8 is docs/spec/static-audit/status-lock work only and implements no behavior change",
        "Phase 44 is complete as an internal Project Source Selection And Parse-only Project Check MVP status lock after Slice 8",
        "does not claim Gate 3 natural CI success inside this document",
        "Sequence may change only through a later Gate 1",
        "Phase 44 Slice 1 Gate 2 is limited to:",
        "docs/plan/phase-44-project-source-selection-parse-only-project-check-mvp.md",
        "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
        "tests/test_phase44_project_source_selection_scope_lock.py",
        "No other file is approved in this Gate 2",
        "The deferred register is not touched by Slice 1",
        "git diff --check",
        "uv run pytest tests/test_phase44_project_source_selection_scope_lock.py",
        "Phase 44 Slice 3 Gate 2 is limited to:",
        "src/pietto/_project/config.py",
        "src/pietto/_project/model.py",
        "tests/test_phase44_project_config_loader.py",
        "tests/test_phase44_project_config_schema_contract.py",
        "tests/test_phase44_project_source_selection_scope_lock.py",
        "tests/test_phase33_completion_audit.py",
        "uv run pyright --project pyrightconfig.json",
        "uv run pyright --project pyrightconfig.tests.json",
        "Phase 44 Slice 4 Gate 2 is limited to:",
        "docs/spec/phase44-project-source-selection-scope-lock-v1.md",
        "src/pietto/_project/source_selection.py",
        "tests/test_phase44_project_source_selection.py",
        "tests/test_phase9_completion_audit.py",
        "tests/test_phase33_cli_package_compatibility_hardening.py",
        "source selection accepts an already loaded private config result",
        "source selection does not call `Path.glob`, `Path.rglob`, or `os.walk`",
        "Phase 44 Slice 6 Gate 2 is limited to:",
        "src/pietto/_project/json_v2.py",
        "tests/test_phase44_project_json_v2_inputs_counters.py",
        "tests/test_phase33_json_v2_project_envelope_contract.py",
        "tests/test_phase33_project_root_config_path_discovery_contract.py",
        "tests/test_phase12_order_limit_contract.py",
        "tests/test_phase32_completion_audit.py",
        "Project JSON v2 reports parse-only project inputs",
        "Project JSON v2 counters reflect serialized parse-attempted inputs",
        "uv run pytest tests/test_phase44_project_json_v2_inputs_counters.py",
        "uv run python scripts/package_smoke.py",
        "Phase 44 Slice 7 Gate 2 is limited to:",
        "tests/test_phase44_project_cli_package_compatibility.py",
        "tests/test_phase11_packaging_smoke.py",
        "No other file is approved in this Gate 2",
        "Slice 7 must not change `src/**`",
        "`scripts/package_smoke.py`, package metadata, workflows, dependencies",
        "uv run ruff format --check tests/test_phase44_project_cli_package_compatibility.py",
        "uv run pytest tests/test_phase44_project_cli_package_compatibility.py",
        "Phase 44 Slice 8 Gate 2 is limited to:",
        "tests/test_phase44_completion_audit.py",
        "tests/test_phase44_project_json_v2_inputs_counters.py",
        "Slice 8 must not change `src/**`",
        "`scripts/**`, `README.md`, `AGENTS.md`, `docs/spec/pietto-v0.9.md`",
        "uv run ruff format --check tests/test_phase44_completion_audit.py",
        "uv run pytest tests/test_phase44_completion_audit.py",
    ):
        assert required in docs, required

    for required in (
        "stop and request a Repair Gate 1",
        "production source, CLI behavior, Project JSON v2 serializer",
        "grammar/generated, fixture, golden, package, workflow, lockfile",
        "implementation of config loader, source selection, parser aggregation",
        "project semantic, IR, SQL, `emit-sql --project`, or `explain --project`",
        "JOIN/relationship behavior, `RelationLayerIR`, `LetBindingIR`, Arrow/PyArrow",
        "LSP/UI, runtime/database, schema introspection, or db pull",
        "production source, `scripts/package_smoke.py`, CLI behavior, Project JSON v2",
        "narrow Slice 7 compatibility-hardening package",
        "narrow Slice 8 completion-audit/status-lock package",
    ):
        assert required in docs, required


def test_slice7_cli_package_compatibility_hardening_is_locked() -> None:
    docs = _phase44_docs()
    compat_test = _read(PROJECT_COMPAT_TEST_PATH)
    package_smoke = _read(PACKAGE_SMOKE_PATH)

    assert PROJECT_COMPAT_TEST_PATH.is_file()

    for required in (
        "Phase 44 Slice 7 is CLI / Package / Compatibility Hardening",
        "tests/docs/static-audit compatibility hardening only",
        "keeps `scripts/package_smoke.py` unchanged",
        "Slice 7 compatibility hardening must:",
        "lock current text-mode `pietto check --project ROOT` success and failure",
        "lock current Project JSON v2 success, parser-diagnostic, source-read, config",
        "prove single-file `check` and `emit-sql` still use CLI JSON v1",
        "prove single-file `explain` still uses Semantic Metadata Artifact v1",
        "prove `emit-sql --project` and `explain --project` remain rejected",
        "lock that installed package smoke already covers project text and JSON success",
        "Slice 7 does not authorize `src/**` changes",
        "Project JSON v2 schema expansion beyond Slice 6",
    ):
        assert required in docs, required

    for required in (
        "test_project_check_text_and_json_success_remain_compatible",
        "test_project_check_json_parser_diagnostics_do_not_enter_semantics",
        "test_project_check_json_source_read_and_config_errors_stay_cli_errors",
        "test_single_file_json_v1_and_artifact_v1_surfaces_remain_separate",
        "test_project_flag_remains_rejected_outside_check",
        "test_installed_package_smoke_locks_project_text_and_json_success",
        "_forbid_project_compiler_pipeline",
        "semantic_api",
        "ir_api",
        "sql_api",
        "mysql_backend",
        "build_semantic_metadata_artifact",
    ):
        assert required in compat_test, required

    for required in (
        '"installed CLI project check text"',
        '"installed CLI project check JSON v2"',
        "Project check OK: .",
        "Files checked: 1",
        '"schema_version": 2',
        '"status": "parsed"',
        '"files_total": 1',
        '"files_ok": 1',
        '"files_with_errors": 0',
    ):
        assert required in package_smoke, required


def test_forbidden_surfaces_and_public_outputs_remain_locked() -> None:
    docs = _phase44_docs()
    project_root = _normalized(PROJECT_ROOT_SPEC_PATH)
    cli_source = _read(CLI_PATH)
    config_source = _read(PROJECT_CONFIG_SOURCE_PATH)
    source_selection_source = _read(PROJECT_SOURCE_SELECTION_SOURCE_PATH)
    check_source = _read(PROJECT_CHECK_SOURCE_PATH)
    project_json_source = _read(PROJECT_JSON_SOURCE_PATH)
    emit_section = _parser_section(cli_source, "emit_sql")
    explain_section = _parser_section(cli_source, "explain")

    for required in (
        "implements only a private `pietto.toml` loader and schema validator",
        "does not wire the loader into CLI behavior, Project JSON v2 output",
        "implements only private deterministic source selection",
        "does not wire source selection into CLI behavior, Project JSON v2 output",
        "`src/pietto/_project/source_selection.py`",
        "parser aggregation implementation",
        "CLI behavior changes",
        "`src/pietto/**` changes",
        "Project JSON v2 serializer changes",
        "full project semantic analysis",
        "project IR or SQL",
        "`emit-sql --project`",
        "`explain --project`",
        "imports, includes, modules, export",
        "CLI JSON v1 mutation",
        "Semantic Metadata Artifact v1 mutation",
        "JOIN or relationship behavior",
        "`RelationLayerIR`",
        "`LetBindingIR`",
        "runtime or database execution",
        "schema introspection",
        "db pull",
        "Arrow or PyArrow integration",
        "LSP, editor server, playground, or UI behavior",
        "tag, release, publish, upload, signing, or attestation",
    ):
        assert required in docs, required

    for required in (
        "`pietto check --format json` remains single-file CLI JSON v1",
        "`pietto emit-sql --format json` remains single-file CLI JSON v1",
        "`pietto explain --format json` remains Semantic Metadata Artifact v1",
        "Single-file CLI JSON v1 remains unchanged",
        "Semantic Metadata Artifact v1 remains unchanged",
    ):
        assert required in project_root, required

    assert "def load_project_config" in config_source
    assert "tomllib" in config_source
    assert "def select_project_sources" in source_selection_source
    assert "load_project_config" not in source_selection_source
    assert "tomllib" not in source_selection_source
    assert "def check_project_parse_only" in check_source
    assert "load_project_config" in check_source
    assert "select_project_sources" in check_source
    assert "parse_source" in check_source
    assert "path=selected_input.path" in check_source
    assert "parse_file" not in check_source
    for forbidden in (
        ".glob(",
        ".rglob(",
        "os.walk",
        "read_text(",
        "read_bytes(",
        "open(",
        "parse_file",
    ):
        assert forbidden not in source_selection_source, forbidden
    assert "load_project_config" not in cli_source
    assert "select_project_sources" not in cli_source
    assert "tomllib" not in cli_source
    assert "build_empty_project_semantic_result(parse_result)" in cli_source
    assert "load_project_config" not in project_json_source
    assert "select_project_sources" not in project_json_source
    assert "tomllib" not in project_json_source
    assert "--project" not in emit_section
    assert "--project" not in explain_section


def test_package_version_remains_010() -> None:
    pyproject = _read(PYPROJECT_PATH)
    docs = _phase44_docs()

    assert 'version = "0.1.0"' in pyproject
    assert 'version = "0.2.0"' not in pyproject
    assert "package version remains `0.1.0`" in docs
