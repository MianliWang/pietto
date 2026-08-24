from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, dataclass, fields
from enum import StrEnum
import inspect
from pathlib import Path
from typing import cast

import pytest

import pietto
import pietto._metadata as metadata_package
import pietto._project as project_package
import pietto._project_explain as project_explain_package
import pietto._project_explain.model as model
import pietto.semantic as semantic_package
import test_phase58_slice1_project_explain_portability_scope_lock as slice1
from pietto._project.capability_inspection import CapabilityInspectionFormat
from pietto._project.extension_catalog_inspection import (
    ExtensionCatalogInspectionFormat,
)
from pietto._project.package_inspection import PackageInspectionFormat
from pietto._project_explain.model import (
    PROJECT_EXPLAIN_ARTIFACT_NAME,
    ProjectExplainDiagnostic,
    ProjectExplainEnvelope,
    ProjectExplainEvidencePosture,
    ProjectExplainFormat,
    ProjectExplainLocation,
    ProjectExplainLogicalPath,
    ProjectExplainLogicalPathKind,
    ProjectExplainRequirementStage,
)
from pietto.errors import Diagnostic, Severity, SourceLocation


REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC = (
    REPO_ROOT / "docs/spec/phase58-slice2-project-explain-common-model-envelope-v1.md"
)
ROADMAP = REPO_ROOT / "docs/roadmap.md"
STATUS = REPO_ROOT / "docs/status.md"
MODEL_SOURCE = REPO_ROOT / "src/pietto/_project_explain/model.py"
PACKAGE_SMOKE = REPO_ROOT / "scripts/package_smoke.py"

EXPECTED_CHANGED_PATHS = frozenset(
    {
        "src/pietto/_project_explain/__init__.py",
        "src/pietto/_project_explain/model.py",
        "docs/spec/phase58-slice2-project-explain-common-model-envelope-v1.md",
        "tests/test_phase58_slice2_project_explain_common_model_envelope.py",
        "docs/roadmap.md",
        "docs/status.md",
        "scripts/package_smoke.py",
        "tests/test_phase58_slice1_project_explain_portability_scope_lock.py",
        *slice1.LIFECYCLE_READERS,
    }
)


@dataclass(frozen=True, slots=True, kw_only=True)
class _PayloadWitness:
    value: str


@dataclass(frozen=True, slots=True, kw_only=True)
class _DiagnosticSubclass(ProjectExplainDiagnostic):
    pass


class _ForeignFormat(StrEnum):
    FOREIGN = "foreign"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _warning(message: str = "warning") -> ProjectExplainDiagnostic:
    return ProjectExplainDiagnostic(
        code="PIE-W0001",
        severity=Severity.WARNING,
        message=message,
        location=None,
        suggestion=None,
    )


def _error(message: str = "error") -> ProjectExplainDiagnostic:
    return ProjectExplainDiagnostic(
        code="PIE-E0001",
        severity=Severity.ERROR,
        message=message,
        location=None,
        suggestion=None,
    )


def test_exact_artifact_identity_and_closed_enum_vocabularies() -> None:
    assert PROJECT_EXPLAIN_ARTIFACT_NAME == "Project Explain Artifact v1"
    assert tuple(ProjectExplainFormat) == (ProjectExplainFormat.PROJECT_EXPLAIN_V1,)
    assert ProjectExplainFormat.PROJECT_EXPLAIN_V1.value == (
        "pietto.project-explain.v1"
    )
    assert [(item.name, item.value) for item in ProjectExplainEvidencePosture] == [
        ("SOURCE_FACT", "source_fact"),
        ("DETERMINISTIC_DERIVATION", "deterministic_derivation"),
        ("UNAVAILABLE", "unavailable"),
        ("CONFLICTING", "conflicting"),
    ]
    assert [(item.name, item.value) for item in ProjectExplainRequirementStage] == [
        ("REQUEST", "request"),
        ("RESOLUTION", "resolution"),
        ("RESULT", "result"),
    ]
    assert [(item.name, item.value) for item in ProjectExplainLogicalPathKind] == [
        ("PROJECT_RELATIVE", "project_relative"),
        ("PACKAGE_RELATIVE", "package_relative"),
        ("UPSTREAM_SOURCE_LOCATOR", "upstream_source_locator"),
    ]


def test_exact_dataclass_shapes_are_frozen_slotted_keyword_only_values() -> None:
    expected_fields = {
        ProjectExplainLogicalPath: ("kind", "value"),
        ProjectExplainLocation: (
            "path",
            "line",
            "column",
            "end_line",
            "end_column",
        ),
        ProjectExplainDiagnostic: (
            "code",
            "severity",
            "message",
            "location",
            "suggestion",
        ),
        ProjectExplainEnvelope: ("format", "ok", "diagnostics", "payload"),
    }
    for carrier, names in expected_fields.items():
        assert tuple(field.name for field in fields(carrier)) == names
        assert carrier.__dataclass_params__.frozen
        assert "__dict__" not in carrier.__slots__
        assert all(
            parameter.kind is inspect.Parameter.KEYWORD_ONLY
            for parameter in inspect.signature(carrier).parameters.values()
        )

    path = ProjectExplainLogicalPath(
        kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
        value="models/user.pietto",
    )
    equal_path = ProjectExplainLogicalPath(
        kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
        value="models/user.pietto",
    )
    assert path == equal_path
    assert hash(path) == hash(equal_path)
    with pytest.raises(FrozenInstanceError):
        setattr(path, "value", "changed.pietto")


@pytest.mark.parametrize("kind", tuple(ProjectExplainLogicalPathKind)[:2])
@pytest.mark.parametrize(
    "value",
    (
        ".",
        "models/user.pietto",
        "packages/acme/models.pietto",
        "unicode/模型.pietto",
        "a-b_c/0.pietto",
    ),
)
def test_relative_logical_paths_accept_exact_normalized_values(
    kind: ProjectExplainLogicalPathKind,
    value: str,
) -> None:
    logical_path = ProjectExplainLogicalPath(kind=kind, value=value)
    assert logical_path.kind is kind
    assert logical_path.value == value


@pytest.mark.parametrize("kind", tuple(ProjectExplainLogicalPathKind)[:2])
@pytest.mark.parametrize(
    "value",
    (
        "",
        "/models/user.pietto",
        "//server/share",
        "C:/models/user.pietto",
        "c:models/user.pietto",
        "models\\user.pietto",
        "models/user.pietto/",
        "models//user.pietto",
        "models/./user.pietto",
        "models/../user.pietto",
        "./models.pietto",
        "..",
        "models/.",
        "models/..",
        "models/\x00user.pietto",
        "models/\nuser.pietto",
        "models/\x7fuser.pietto",
        "models/\x85user.pietto",
    ),
)
def test_relative_logical_paths_reject_malformed_or_host_values(
    kind: ProjectExplainLogicalPathKind,
    value: str,
) -> None:
    with pytest.raises(ValueError):
        ProjectExplainLogicalPath(kind=kind, value=value)


@pytest.mark.parametrize(
    "value",
    (
        "https://github.com/MianliWang/pietto/tree/REL_18_6",
        "git@github.com:MianliWang/pietto.git#0504f338",
        "REL_18_6/contrib/pg_trgm/pg_trgm--1.6.sql",
        "docs/spec/catalog.md#Source-Authority",
        "urn:pietto:catalog:pgvector:0.8.6",
        "HTTPS://Example.COM/A%2Fb",
    ),
)
def test_upstream_locators_accept_opaque_relocation_stable_values(value: str) -> None:
    locator = ProjectExplainLogicalPath(
        kind=ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR,
        value=value,
    )
    assert locator.value == value


@pytest.mark.parametrize(
    "value",
    (
        "",
        "/home/user/source.sql",
        "C:/Users/user/source.sql",
        "c:\\Users\\user\\source.sql",
        "//server/share/source.sql",
        "\\\\server\\share\\source.sql",
        "\\rooted\\source.sql",
        "~/source.sql",
        "~user/source.sql",
        "file:///tmp/source.sql",
        "FILE:/C:/source.sql",
        "FiLe://localhost/tmp/source.sql",
        "source\x00locator",
        "source\nlocator",
        "source\x7flocator",
        "source\x85locator",
    ),
)
def test_upstream_locators_reject_control_and_local_host_identity(value: str) -> None:
    with pytest.raises(ValueError):
        ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.UPSTREAM_SOURCE_LOCATOR,
            value=value,
        )


def test_logical_paths_reject_kind_and_value_type_mismatches() -> None:
    with pytest.raises(TypeError):
        ProjectExplainLogicalPath(
            kind=cast(ProjectExplainLogicalPathKind, "project_relative"),
            value="models/user.pietto",
        )
    with pytest.raises(TypeError):
        ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
            value=cast(str, Path("models/user.pietto")),
        )


def test_logical_path_validation_has_no_normalization_filesystem_or_network_seam() -> (
    None
):
    source = _read(MODEL_SOURCE)
    tree = ast.parse(source, filename=MODEL_SOURCE.as_posix())
    imports = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    } | {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert imports == {
        "__future__",
        "dataclasses",
        "enum",
        "unicodedata",
        "pietto.errors",
    }
    for forbidden in (
        "pathlib",
        "os.path",
        ".resolve(",
        "realpath",
        ".stat(",
        "getcwd",
        "socket",
        "requests",
        "urllib.request",
        "casefold(",
        ".lower(",
    ):
        assert forbidden not in source


def test_locations_accept_none_path_only_start_and_complete_coordinates() -> None:
    path = ProjectExplainLogicalPath(
        kind=ProjectExplainLogicalPathKind.PROJECT_RELATIVE,
        value="models/user.pietto",
    )
    no_location = ProjectExplainLocation(
        path=None,
        line=None,
        column=None,
        end_line=None,
        end_column=None,
    )
    path_only = ProjectExplainLocation(
        path=path,
        line=None,
        column=None,
        end_line=None,
        end_column=None,
    )
    start_only = ProjectExplainLocation(
        path=None,
        line=1,
        column=2,
        end_line=None,
        end_column=None,
    )
    complete = ProjectExplainLocation(
        path=path,
        line=2,
        column=3,
        end_line=4,
        end_column=5,
    )
    zero_width = ProjectExplainLocation(
        path=path,
        line=2,
        column=3,
        end_line=2,
        end_column=3,
    )
    assert no_location.path is None
    assert path_only.path is path
    assert (start_only.line, start_only.column) == (1, 2)
    assert (complete.end_line, complete.end_column) == (4, 5)
    assert zero_width.end_column == zero_width.column


def test_locations_reject_unpaired_nonpositive_noninteger_and_reversed_coordinates() -> (
    None
):
    common = {"path": None, "end_line": None, "end_column": None}
    with pytest.raises(ValueError):
        ProjectExplainLocation(line=1, column=None, **common)
    with pytest.raises(ValueError):
        ProjectExplainLocation(line=None, column=1, **common)
    with pytest.raises(ValueError):
        ProjectExplainLocation(
            path=None,
            line=None,
            column=None,
            end_line=1,
            end_column=1,
        )
    with pytest.raises(ValueError):
        ProjectExplainLocation(
            path=None,
            line=0,
            column=1,
            end_line=None,
            end_column=None,
        )
    with pytest.raises(ValueError):
        ProjectExplainLocation(
            path=None,
            line=2,
            column=3,
            end_line=2,
            end_column=2,
        )
    with pytest.raises(ValueError):
        ProjectExplainLocation(
            path=None,
            line=2,
            column=3,
            end_line=1,
            end_column=99,
        )
    with pytest.raises(TypeError):
        ProjectExplainLocation(
            path=None,
            line=cast(int | None, True),
            column=1,
            end_line=None,
            end_column=None,
        )
    with pytest.raises(TypeError):
        ProjectExplainLocation(
            path=None,
            line=cast(int | None, "1"),
            column=1,
            end_line=None,
            end_column=None,
        )
    with pytest.raises(TypeError):
        ProjectExplainLocation(
            path=cast(ProjectExplainLogicalPath | None, "models/user.pietto"),
            line=None,
            column=None,
            end_line=None,
            end_column=None,
        )


def test_detached_diagnostics_validate_exact_fields_and_preserve_spelling() -> None:
    location = ProjectExplainLocation(
        path=ProjectExplainLogicalPath(
            kind=ProjectExplainLogicalPathKind.PACKAGE_RELATIVE,
            value="models/user.pietto",
        ),
        line=3,
        column=4,
        end_line=3,
        end_column=8,
    )
    diagnostic = ProjectExplainDiagnostic(
        code=" PIE-W0001 ",
        severity=Severity.WARNING,
        message=" Keep Exact Case ",
        location=location,
        suggestion=" Keep exact spelling ",
    )
    assert diagnostic.code == " PIE-W0001 "
    assert diagnostic.message == " Keep Exact Case "
    assert diagnostic.location is location
    assert diagnostic.suggestion == " Keep exact spelling "
    assert hash(diagnostic) == hash(
        ProjectExplainDiagnostic(
            code=" PIE-W0001 ",
            severity=Severity.WARNING,
            message=" Keep Exact Case ",
            location=location,
            suggestion=" Keep exact spelling ",
        )
    )


def test_detached_diagnostics_reject_empty_wrong_or_retained_private_values() -> None:
    for field_name in ("code", "message"):
        values = {
            "code": "PIE-E0001",
            "severity": Severity.ERROR,
            "message": "error",
            "location": None,
            "suggestion": None,
        }
        values[field_name] = ""
        with pytest.raises(ValueError):
            ProjectExplainDiagnostic(**values)  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        ProjectExplainDiagnostic(
            code="PIE-E0001",
            severity=Severity.ERROR,
            message="error",
            location=None,
            suggestion="",
        )
    with pytest.raises(TypeError):
        ProjectExplainDiagnostic(
            code="PIE-E0001",
            severity=cast(Severity, "error"),
            message="error",
            location=None,
            suggestion=None,
        )
    original_location = SourceLocation(path="/host/input.pietto", line=1, column=1)
    original_diagnostic = Diagnostic(
        code="PIE-E0001",
        severity=Severity.ERROR,
        message="error",
        location=original_location,
    )
    with pytest.raises(TypeError):
        ProjectExplainDiagnostic(
            code=original_diagnostic.code,
            severity=original_diagnostic.severity,
            message=original_diagnostic.message,
            location=cast(ProjectExplainLocation | None, original_location),
            suggestion=None,
        )


def test_success_envelope_accepts_payload_and_ordered_duplicate_warnings() -> None:
    warning = _warning()
    diagnostics = (warning, warning)
    payload = _PayloadWitness(value="payload")
    envelope: ProjectExplainEnvelope[_PayloadWitness] = ProjectExplainEnvelope(
        format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=True,
        diagnostics=diagnostics,
        payload=payload,
    )
    assert envelope.payload is payload
    assert envelope.diagnostics is diagnostics
    assert envelope.diagnostics == (warning, warning)
    assert hash(envelope) == hash(
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=diagnostics,
            payload=payload,
        )
    )


def test_success_envelope_rejects_missing_payload_or_error_diagnostic() -> None:
    with pytest.raises(ValueError):
        ProjectExplainEnvelope[_PayloadWitness](
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=(),
            payload=None,
        )
    with pytest.raises(ValueError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=(_error(),),
            payload=_PayloadWitness(value="payload"),
        )


def test_failure_envelope_accepts_ordered_warnings_and_errors_without_payload() -> None:
    first_warning = _warning("first")
    error = _error()
    last_warning = _warning("last")
    diagnostics = (first_warning, error, last_warning, error)
    envelope: ProjectExplainEnvelope[_PayloadWitness] = ProjectExplainEnvelope(
        format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
        ok=False,
        diagnostics=diagnostics,
        payload=None,
    )
    assert envelope.payload is None
    assert envelope.diagnostics is diagnostics
    assert envelope.diagnostics == (first_warning, error, last_warning, error)


def test_failure_envelope_rejects_payload_or_missing_error() -> None:
    with pytest.raises(ValueError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=False,
            diagnostics=(_error(),),
            payload=_PayloadWitness(value="payload"),
        )
    for diagnostics in ((), (_warning(),)):
        with pytest.raises(ValueError):
            ProjectExplainEnvelope[_PayloadWitness](
                format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
                ok=False,
                diagnostics=diagnostics,
                payload=None,
            )


def test_envelope_rejects_wrong_marker_ok_collection_and_diagnostic_types() -> None:
    warning = _warning()
    with pytest.raises(TypeError):
        ProjectExplainEnvelope(
            format=cast(ProjectExplainFormat, _ForeignFormat.FOREIGN),
            ok=True,
            diagnostics=(),
            payload=_PayloadWitness(value="payload"),
        )
    with pytest.raises(TypeError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=cast(bool, 1),
            diagnostics=(),
            payload=_PayloadWitness(value="payload"),
        )
    with pytest.raises(TypeError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=cast(tuple[ProjectExplainDiagnostic, ...], [warning]),
            payload=_PayloadWitness(value="payload"),
        )
    subclass = _DiagnosticSubclass(
        code="PIE-W0001",
        severity=Severity.WARNING,
        message="warning",
        location=None,
        suggestion=None,
    )
    with pytest.raises(TypeError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=(subclass,),
            payload=_PayloadWitness(value="payload"),
        )
    with pytest.raises(TypeError):
        ProjectExplainEnvelope(
            format=ProjectExplainFormat.PROJECT_EXPLAIN_V1,
            ok=True,
            diagnostics=cast(tuple[ProjectExplainDiagnostic, ...], (object(),)),
            payload=_PayloadWitness(value="payload"),
        )


def test_generic_payload_is_typed_without_production_placeholder_or_object_escape() -> (
    None
):
    assert tuple(
        parameter.__name__ for parameter in ProjectExplainEnvelope.__type_params__
    ) == ("PayloadT",)
    source = _read(MODEL_SOURCE)
    assert "class ProjectExplainEnvelope[PayloadT]" in source
    assert "payload: PayloadT | None" in source
    assert "payload: object" not in source
    for forbidden in (
        "ProjectExplainPayload",
        "ProjectExplainPackage",
        "ProjectExplainRequirement",
        "ProjectExplainTarget",
        "ProjectExplainMatrix",
        "ProjectExplainCatalog",
        "ProjectExplainPortability",
        "ProjectExplainReference",
    ):
        assert not hasattr(model, forbidden)


def test_model_package_is_private_and_has_no_serializer_text_json_or_cli_surface() -> (
    None
):
    assert project_explain_package.__all__ == model.__all__ == ()
    for public_module in (
        pietto,
        project_package,
        metadata_package,
        semantic_package,
    ):
        for name in (
            "ProjectExplainEnvelope",
            "ProjectExplainFormat",
            "ProjectExplainLogicalPath",
            "PROJECT_EXPLAIN_ARTIFACT_NAME",
        ):
            assert not hasattr(public_module, name)
    source = _read(MODEL_SOURCE)
    for forbidden in (
        "import json",
        "to_json",
        "as_dict",
        "serialize",
        "render_",
        "argparse",
        "pietto.cli",
        "pietto._metadata",
        "pietto._project",
    ):
        assert forbidden not in source


def test_package_smoke_requires_and_imports_the_installed_private_model() -> None:
    source = _read(PACKAGE_SMOKE)
    for required in (
        'f"{prefix}/_project_explain/__init__.py"',
        'f"{prefix}/_project_explain/model.py"',
        '"installed private project explain model import"',
        "import pietto._project_explain.model as project_explain_model",
        "project_explain_model.PROJECT_EXPLAIN_ARTIFACT_NAME",
        "project_explain_model.ProjectExplainFormat.",
        "PROJECT_EXPLAIN_V1.value == 'pietto.project-explain.v1'",
    ):
        assert required in source


def test_existing_artifacts_project_json_and_private_authorities_are_zero_delta() -> (
    None
):
    cli_source = _read(REPO_ROOT / "src/pietto/cli.py")
    assert slice1._argument_names(cli_source, "_configure_explain_parser") == (
        "path",
        "--format",
    )
    assert "pietto._project_explain" not in cli_source
    for relative_path in (
        "src/pietto/_metadata/model.py",
        "src/pietto/_metadata/serializer.py",
        "src/pietto/_metadata/text.py",
        "src/pietto/_project/json_v2.py",
        "src/pietto/cli_json.py",
    ):
        assert "Project Explain Artifact v1" not in _read(REPO_ROOT / relative_path)
    assert PackageInspectionFormat.PACKAGE_INSPECTION_V1.value == (
        "pietto.package-inspection.v1"
    )
    assert CapabilityInspectionFormat.CAPABILITY_INSPECTION_V1.value == (
        "pietto.capability-inspection.v1"
    )
    assert ExtensionCatalogInspectionFormat.EXTENSION_CATALOG_INSPECTION_V1.value == (
        "pietto.extension-catalog-inspection.v1"
    )


def test_slice2_spec_headings_model_contract_and_retained_owners_are_exact() -> None:
    document = _read(SPEC)
    assert slice1._headings(document) == (
        "Answer And Authority",
        "Private Python Surface",
        "Artifact Identity",
        "Closed Vocabularies",
        "Immutable Model Shapes",
        "Logical Path Contract",
        "Location Contract",
        "Diagnostic Contract",
        "Type-safe Success And Failure Envelope",
        "Ordering And Multiplicity",
        "Privacy And Relocation",
        "Compatibility And Retained Ownership",
        "Non-goals",
        "Lifecycle And Slice 3 Handoff",
    )
    assert slice1._table_rows(slice1._section(document, "Immutable Model Shapes"))[
        1:
    ] == (
        ("`ProjectExplainLogicalPath`", "`kind`, `value`"),
        (
            "`ProjectExplainLocation`",
            "`path`, `line`, `column`, `end_line`, `end_column`",
        ),
        (
            "`ProjectExplainDiagnostic`",
            "`code`, `severity`, `message`, `location`, `suggestion`",
        ),
        (
            "`ProjectExplainEnvelope[PayloadT]`",
            "`format`, `ok`, `diagnostics`, `payload`",
        ),
    )
    retained = slice1._table_rows(
        slice1._section(document, "Compatibility And Retained Ownership")
    )[1:]
    assert tuple(row[0] for row in retained) == tuple(
        str(item) for item in range(3, 10)
    )
    assert "PHASE58_SLICE2_SELF_OWNED_OPEN = 0" in document


def test_route_lifecycle_inventory_and_slice3_handoff_are_exact() -> None:
    assert (
        slice1._table_rows(slice1._section(_read(ROADMAP), "Phase 58 route"))[1:]
        == slice1.EXPECTED_ROUTE
    )
    assert slice1._table_rows(_read(STATUS))[1:] == (
        ("Package and CLI", "`0.1.0`"),
        ("Phase 55", "`COMPLETED`"),
        ("Phase 56", "`COMPLETED`"),
        ("Phase 57", "`COMPLETED`"),
        ("Phase 58", "`ACTIVE`"),
        ("Slice 1", "`COMPLETED`"),
        ("Slice 2", "`CURRENT`"),
        ("Slice 3", "`NEXT / UNSTARTED`"),
        ("Next", "`PHASE58_SLICE3_END_TO_END`"),
    )
    document = _read(SPEC)
    for required in (
        "package coordinates/assets/direct dependencies",
        "`declared_by`",
        "`requested_by`",
        "requirement occurrences",
        "bounded why chain",
        "Slice 3 remains `UNSTARTED / NOT AUTHORIZED`",
    ):
        assert required in document

    production_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (REPO_ROOT / "src/pietto/_project_explain").iterdir()
        if path.is_file()
    }
    assert production_paths == {
        "src/pietto/_project_explain/__init__.py",
        "src/pietto/_project_explain/model.py",
    }
    phase58_paths = {
        path.relative_to(REPO_ROOT).as_posix()
        for path in (
            *(REPO_ROOT / "docs/spec").glob("phase58-*"),
            *(REPO_ROOT / "tests").glob("test_phase58_*"),
        )
    }
    assert phase58_paths == {
        "docs/spec/phase58-project-explain-portability-scope-lock-v1.md",
        "docs/spec/phase58-slice2-project-explain-common-model-envelope-v1.md",
        "tests/test_phase58_slice1_project_explain_portability_scope_lock.py",
        "tests/test_phase58_slice2_project_explain_common_model_envelope.py",
    }
    assert len(EXPECTED_CHANGED_PATHS) == 22
    assert all((REPO_ROOT / path).exists() for path in EXPECTED_CHANGED_PATHS)
