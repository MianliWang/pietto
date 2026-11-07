"""Frozen accepted and rejected vectors for the package pure boundary."""

from __future__ import annotations

from dataclasses import dataclass, replace
from enum import StrEnum
from types import MappingProxyType
from collections.abc import Mapping

from pietto._project.package_pure_boundary import (
    PACKAGE_PURE_ABSENT,
    PACKAGE_PURE_FORMAT_MARKER,
    PACKAGE_PURE_MAX_INTEGER,
    PackagePureDocument,
    PackagePureField,
    PackagePureRecord,
    PackagePureStatus,
    PackagePureTag,
    PackagePureValue,
    package_pure_enumeration,
    package_pure_integer,
    package_pure_text,
)

PACKAGE_DIFFERENTIAL_VECTOR_FORMAT = "pietto.package-differential-vectors.v1"

_A = "1" * 64
_B = "2" * 64
_C = "3" * 64


class PackageDifferentialClassification(StrEnum):
    PORTABLE_EVALUATION = "portable_evaluation"
    PORTABLE_REJECTION = "portable_rejection"


@dataclass(frozen=True, slots=True, kw_only=True)
class PackageDifferentialVector:
    vector_format: str
    vector_id: str
    purposes: tuple[str, ...]
    classification: PackageDifferentialClassification
    document: PackagePureDocument
    expected_status: PackagePureStatus
    expected_bytes: bytes | None = None
    expected_record_position: int | None = None
    expected_field_position: int | None = None


def _record(
    kind: str,
    *pairs: tuple[str, PackagePureValue],
) -> PackagePureRecord:
    return PackagePureRecord(
        kind=kind,
        fields=tuple(PackagePureField(key=key, value=value) for key, value in pairs),
    )


def _document(*records: PackagePureRecord) -> PackagePureDocument:
    return PackagePureDocument(records=records)


def _header(
    outcome: str,
    *,
    packages: int = 0,
    errors: int = 0,
    diagnostics: int = 0,
    rejections: int = 0,
    marker: str = PACKAGE_PURE_FORMAT_MARKER,
) -> PackagePureRecord:
    return _record(
        "inspection",
        ("format", package_pure_enumeration(marker)),
        ("outcome", package_pure_enumeration(outcome)),
        ("packages", package_pure_integer(packages)),
        ("errors", package_pure_integer(errors)),
        ("diagnostics", package_pure_integer(diagnostics)),
        ("rejections", package_pure_integer(rejections)),
    )


def _root(
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
) -> PackagePureRecord:
    return _record(
        "root",
        ("namespace", package_pure_text(namespace)),
        ("name", package_pure_text(name)),
        ("version", package_pure_text(version)),
    )


def _package(
    position: int,
    role: str,
    namespace: str,
    name: str,
    version: str,
    project_path: str,
    digest: str,
    *,
    assets: int = 1,
    dependencies: int = 0,
) -> PackagePureRecord:
    return _record(
        "package",
        ("package", package_pure_integer(position)),
        ("role", package_pure_enumeration(role)),
        ("namespace", package_pure_text(namespace)),
        ("name", package_pure_text(name)),
        ("version", package_pure_text(version)),
        ("project_path", package_pure_text(project_path)),
        ("content_digest", package_pure_text(digest)),
        ("assets", package_pure_integer(assets)),
        ("dependencies", package_pure_integer(dependencies)),
    )


def _asset(package: int, position: int, path: str) -> PackagePureRecord:
    return _record(
        "asset",
        ("package", package_pure_integer(package)),
        ("asset", package_pure_integer(position)),
        ("kind", package_pure_enumeration("module_source")),
        ("path", package_pure_text(path)),
    )


def _dependency(
    package: int,
    position: int,
    namespace: str,
    name: str,
    version: str,
    digest: str,
    authored: str,
    resolved: str,
    target: int,
) -> PackagePureRecord:
    return _record(
        "dependency",
        ("package", package_pure_integer(package)),
        ("dependency", package_pure_integer(position)),
        ("namespace", package_pure_text(namespace)),
        ("name", package_pure_text(name)),
        ("version", package_pure_text(version)),
        ("content_digest_pin", package_pure_text(digest)),
        ("locator_kind", package_pure_enumeration("local_directory")),
        ("authored_path", package_pure_text(authored)),
        ("resolved_project_path", package_pure_text(resolved)),
        ("target_package", package_pure_integer(target)),
    )


def _error(
    position: int, kind: str, message: str, path: str | None
) -> PackagePureRecord:
    return _record(
        "error",
        ("error", package_pure_integer(position)),
        ("kind", package_pure_enumeration(kind)),
        ("message", package_pure_text(message)),
        ("path", PACKAGE_PURE_ABSENT if path is None else package_pure_text(path)),
    )


def _diagnostic(position: int) -> PackagePureRecord:
    return _record(
        "diagnostic",
        ("diagnostic", package_pure_integer(position)),
        ("code", package_pure_text("PIE-P1000")),
        ("severity", package_pure_enumeration("error")),
        ("message", package_pure_text("bad\ttoken\n")),
        ("path", package_pure_text("bad.pietto")),
        ("line", package_pure_integer(2)),
        ("column", package_pure_integer(3)),
        ("end_line", PACKAGE_PURE_ABSENT),
        ("end_column", PACKAGE_PURE_ABSENT),
        ("suggestion", package_pure_text("fix 雪")),
    )


def _rejection(
    position: int,
    kind: str,
    *,
    reasons: int,
    occurrences: int,
    message: str,
) -> PackagePureRecord:
    return _record(
        "rejection",
        ("rejection", package_pure_integer(position)),
        ("kind", package_pure_enumeration(kind)),
        ("conflict_reasons", package_pure_integer(reasons)),
        ("occurrences", package_pure_integer(occurrences)),
        ("message", package_pure_text(message)),
    )


def _reason(rejection: int, position: int, value: str) -> PackagePureRecord:
    return _record(
        "rejection_reason",
        ("rejection", package_pure_integer(rejection)),
        ("reason", package_pure_integer(position)),
        ("value", package_pure_enumeration(value)),
    )


def _occurrence(
    rejection: int,
    position: int,
    dependency_position: int,
    declaring: tuple[str, str, str, str, str],
    target: tuple[str, str, str, str, str],
    authored: str,
) -> PackagePureRecord:
    declaring_namespace, declaring_name, declaring_version, declaring_path, digest = (
        declaring
    )
    namespace, name, version, resolved, pin = target
    return _record(
        "rejection_occurrence",
        ("rejection", package_pure_integer(rejection)),
        ("occurrence", package_pure_integer(position)),
        ("dependency_position", package_pure_integer(dependency_position)),
        ("declaring_namespace", package_pure_text(declaring_namespace)),
        ("declaring_name", package_pure_text(declaring_name)),
        ("declaring_version", package_pure_text(declaring_version)),
        ("declaring_project_path", package_pure_text(declaring_path)),
        ("declaring_content_digest", package_pure_text(digest)),
        ("namespace", package_pure_text(namespace)),
        ("name", package_pure_text(name)),
        ("version", package_pure_text(version)),
        ("content_digest_pin", package_pure_text(pin)),
        ("locator_kind", package_pure_enumeration("local_directory")),
        ("authored_path", package_pure_text(authored)),
        ("resolved_project_path", package_pure_text(resolved)),
    )


def _accepted_documents() -> tuple[
    tuple[str, tuple[str, ...], PackagePureDocument], ...
]:
    zero = _document(
        _header("success", packages=1),
        _root(),
        _package(0, "root", "example", "root", "1.0.0", "root", _A),
        _asset(0, 0, "main.pietto"),
    )
    one = _document(
        _header("success", packages=2),
        _root(),
        _package(0, "dependency", "例", "depé", "2.0.0", "deps/依存", _A),
        _asset(0, 0, "models/main.pietto"),
        _package(
            1,
            "root",
            "example",
            "root",
            "1.0.0",
            "root",
            _B,
            dependencies=1,
        ),
        _asset(1, 0, "models/main.pietto"),
        _dependency(1, 0, "例", "depé", "2.0.0", _A, "../deps/依存", "deps/依存", 0),
    )
    multiple = _document(
        _header("success", packages=3),
        _root(),
        _package(0, "dependency", "example", "one", "1.0.0", "deps/one", _A),
        _asset(0, 0, "one.pietto"),
        _package(1, "dependency", "example", "two", "1.0.0", "deps/two", _B),
        _asset(1, 0, "two.pietto"),
        _package(
            2,
            "root",
            "example",
            "root",
            "1.0.0",
            "root",
            _C,
            dependencies=2,
        ),
        _asset(2, 0, "root.pietto"),
        _dependency(2, 0, "example", "one", "1.0.0", _A, "../deps/one", "deps/one", 0),
        _dependency(2, 1, "example", "two", "1.0.0", _B, "../deps/two", "deps/two", 1),
    )
    multihop = _document(
        _header("success", packages=3),
        _root(),
        _package(0, "dependency", "example", "leaf", "1.0.0", "deps/leaf", _A),
        _asset(0, 0, "main.pietto"),
        _package(
            1,
            "dependency",
            "example",
            "middle",
            "1.0.0",
            "deps/middle",
            _B,
            dependencies=1,
        ),
        _asset(1, 0, "main.pietto"),
        _dependency(1, 0, "example", "leaf", "1.0.0", _A, "../leaf", "deps/leaf", 0),
        _package(
            2,
            "root",
            "example",
            "root",
            "1.0.0",
            "root",
            _C,
            dependencies=1,
        ),
        _asset(2, 0, "main.pietto"),
        _dependency(
            2, 0, "example", "middle", "1.0.0", _B, "../deps/middle", "deps/middle", 1
        ),
    )
    duplicate = _document(
        _header("success", packages=2),
        _root(),
        _package(0, "dependency", "example", "dep", "1.0.0", "dep", _A),
        _asset(0, 0, "main.pietto"),
        _package(
            1,
            "root",
            "example",
            "root",
            "1.0.0",
            "root",
            _B,
            dependencies=2,
        ),
        _asset(1, 0, "main.pietto"),
        _dependency(1, 0, "example", "dep", "1.0.0", _A, "../dep", "dep", 0),
        _dependency(1, 1, "example", "dep", "1.0.0", _A, "../dep", "dep", 0),
    )
    controls = _document(
        _header("success", packages=1),
        _root("雪", "根", "1.0.0"),
        _package(0, "root", "雪", "根", "1.0.0", "根", _A, assets=3),
        _asset(0, 0, "a.pietto"),
        _asset(0, 1, "ctrl\tline\n雪.pietto"),
        _asset(0, 2, "z.pietto"),
    )
    errors = _document(
        _header("error", errors=2),
        _error(0, "config_schema", "first", "pietto-package.toml"),
        _error(1, "project_path", "second", None),
    )
    diagnostic = _document(
        _header("error", diagnostics=1),
        _diagnostic(0),
    )
    cycle = _document(
        _header("rejected", rejections=1),
        _rejection(0, "cycle", reasons=0, occurrences=2, message="cycle"),
        _occurrence(
            0,
            0,
            0,
            ("example", "root", "1.0.0", "root", _A),
            ("example", "child", "1.0.0", "deps/child", _B),
            "../deps/child",
        ),
        _occurrence(
            0,
            1,
            0,
            ("example", "child", "1.0.0", "deps/child", _B),
            ("example", "root", "1.0.0", "root", _A),
            "../../root",
        ),
    )
    physical_conflict = _document(
        _header("rejected", rejections=1),
        _rejection(0, "conflict", reasons=1, occurrences=2, message="physical"),
        _reason(0, 0, "physical_root_incompatible_coordinate"),
        _occurrence(
            0,
            0,
            0,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "dep", _A),
            "../dep",
        ),
        _occurrence(
            0,
            1,
            1,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "2.0.0", "dep", _A),
            "../dep",
        ),
    )
    identity_digest_conflict = _document(
        _header("rejected", rejections=1),
        _rejection(0, "conflict", reasons=2, occurrences=2, message="identity digest"),
        _reason(0, 0, "identity_different_physical_root"),
        _reason(0, 1, "incompatible_content_digest_pin"),
        _occurrence(
            0,
            0,
            0,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "deps/one", _A),
            "../deps/one",
        ),
        _occurrence(
            0,
            1,
            1,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "2.0.0", "deps/two", _B),
            "../deps/two",
        ),
    )
    digest_conflict = _document(
        _header("rejected", rejections=1),
        _rejection(0, "conflict", reasons=1, occurrences=2, message="digest"),
        _reason(0, 0, "incompatible_content_digest_pin"),
        _occurrence(
            0,
            0,
            0,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "dep", _A),
            "../dep",
        ),
        _occurrence(
            0,
            1,
            1,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "dep", _B),
            "../dep",
        ),
    )
    occurrence_conflict = _document(
        _header("rejected", rejections=1),
        _rejection(0, "conflict", reasons=1, occurrences=2, message="occurrences"),
        _reason(0, 0, "incompatible_occurrences"),
        _occurrence(
            0,
            0,
            0,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "dep", _A),
            "../dep",
        ),
        _occurrence(
            0,
            1,
            1,
            ("example", "root", "1.0.0", "root", _C),
            ("example", "dep", "1.0.0", "dep", _A),
            ".././dep",
        ),
    )
    diamond = _document(
        _header("rejected", rejections=1),
        _rejection(0, "diamond", reasons=0, occurrences=2, message="diamond"),
        _occurrence(
            0,
            0,
            0,
            ("example", "left", "1.0.0", "deps/left", _B),
            ("example", "leaf", "1.0.0", "deps/leaf", _A),
            "../leaf",
        ),
        _occurrence(
            0,
            1,
            0,
            ("example", "right", "1.0.0", "deps/right", _C),
            ("example", "leaf", "1.0.0", "deps/leaf", _A),
            "../leaf",
        ),
    )
    return (
        ("zero_dependency_root", ("zero_dependency_root",), zero),
        (
            "one_dependency_owner_isolation",
            ("one_dependency", "owner_distinct_same_module_path", "non_ascii_text"),
            one,
        ),
        ("multiple_dependencies", ("multiple_dependencies",), multiple),
        ("multihop_dependency_chain", ("multihop_dependency_chain",), multihop),
        (
            "duplicate_dependency_occurrences",
            ("duplicate_dependency_occurrences",),
            duplicate,
        ),
        (
            "several_assets_control_text",
            ("several_assets", "control_character_text", "escaping"),
            controls,
        ),
        ("ordered_project_errors", ("ordered_project_errors",), errors),
        ("parser_diagnostic", ("parser_diagnostic",), diagnostic),
        ("cycle", ("cycle",), cycle),
        (
            "physical_version_conflict",
            ("physical_conflict_reason", "version_conflict_reason"),
            physical_conflict,
        ),
        (
            "identity_digest_conflict",
            (
                "identity_conflict_reason",
                "digest_conflict_reason",
                "ordered_multi_cause_conflict",
            ),
            identity_digest_conflict,
        ),
        ("digest_conflict", ("digest_conflict_reason",), digest_conflict),
        ("occurrence_conflict", ("occurrence_conflict_reason",), occurrence_conflict),
        ("diamond", ("diamond",), diamond),
    )


# Reviewed bytes literals. Normal tests never regenerate these expectations.
_EXPECTED_CANONICAL_BYTES_LITERAL: dict[str, bytes] = {
    "zero_dependency_root": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:1\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:root\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tproject_path=s:root\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\n",
    "one_dependency_owner_isolation": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:2\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:dependency\tnamespace=s:\xe4\xbe\x8b\tname=s:dep\xc3\xa9\tversion=s:2.0.0\tproject_path=s:deps/\xe4\xbe\x9d\xe5\xad\x98\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:models/main.pietto\npackage\tpackage=i:1\trole=e:root\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tproject_path=s:root\tcontent_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tassets=i:1\tdependencies=i:1\nasset\tpackage=i:1\tasset=i:0\tkind=e:module_source\tpath=s:models/main.pietto\ndependency\tpackage=i:1\tdependency=i:0\tnamespace=s:\xe4\xbe\x8b\tname=s:dep\xc3\xa9\tversion=s:2.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../deps/\xe4\xbe\x9d\xe5\xad\x98\tresolved_project_path=s:deps/\xe4\xbe\x9d\xe5\xad\x98\ttarget_package=i:0\n",
    "multiple_dependencies": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:3\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:dependency\tnamespace=s:example\tname=s:one\tversion=s:1.0.0\tproject_path=s:deps/one\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:one.pietto\npackage\tpackage=i:1\trole=e:dependency\tnamespace=s:example\tname=s:two\tversion=s:1.0.0\tproject_path=s:deps/two\tcontent_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:1\tasset=i:0\tkind=e:module_source\tpath=s:two.pietto\npackage\tpackage=i:2\trole=e:root\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tproject_path=s:root\tcontent_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tassets=i:1\tdependencies=i:2\nasset\tpackage=i:2\tasset=i:0\tkind=e:module_source\tpath=s:root.pietto\ndependency\tpackage=i:2\tdependency=i:0\tnamespace=s:example\tname=s:one\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../deps/one\tresolved_project_path=s:deps/one\ttarget_package=i:0\ndependency\tpackage=i:2\tdependency=i:1\tnamespace=s:example\tname=s:two\tversion=s:1.0.0\tcontent_digest_pin=s:2222222222222222222222222222222222222222222222222222222222222222\tlocator_kind=e:local_directory\tauthored_path=s:../deps/two\tresolved_project_path=s:deps/two\ttarget_package=i:1\n",
    "multihop_dependency_chain": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:3\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:dependency\tnamespace=s:example\tname=s:leaf\tversion=s:1.0.0\tproject_path=s:deps/leaf\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\npackage\tpackage=i:1\trole=e:dependency\tnamespace=s:example\tname=s:middle\tversion=s:1.0.0\tproject_path=s:deps/middle\tcontent_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tassets=i:1\tdependencies=i:1\nasset\tpackage=i:1\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\ndependency\tpackage=i:1\tdependency=i:0\tnamespace=s:example\tname=s:leaf\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../leaf\tresolved_project_path=s:deps/leaf\ttarget_package=i:0\npackage\tpackage=i:2\trole=e:root\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tproject_path=s:root\tcontent_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tassets=i:1\tdependencies=i:1\nasset\tpackage=i:2\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\ndependency\tpackage=i:2\tdependency=i:0\tnamespace=s:example\tname=s:middle\tversion=s:1.0.0\tcontent_digest_pin=s:2222222222222222222222222222222222222222222222222222222222222222\tlocator_kind=e:local_directory\tauthored_path=s:../deps/middle\tresolved_project_path=s:deps/middle\ttarget_package=i:1\n",
    "duplicate_dependency_occurrences": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:2\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:dependency\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tproject_path=s:dep\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:1\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\npackage\tpackage=i:1\trole=e:root\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tproject_path=s:root\tcontent_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tassets=i:1\tdependencies=i:2\nasset\tpackage=i:1\tasset=i:0\tkind=e:module_source\tpath=s:main.pietto\ndependency\tpackage=i:1\tdependency=i:0\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\ttarget_package=i:0\ndependency\tpackage=i:1\tdependency=i:1\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\ttarget_package=i:0\n",
    "several_assets_control_text": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:success\tpackages=i:1\terrors=i:0\tdiagnostics=i:0\trejections=i:0\nroot\tnamespace=s:\xe9\x9b\xaa\tname=s:\xe6\xa0\xb9\tversion=s:1.0.0\npackage\tpackage=i:0\trole=e:root\tnamespace=s:\xe9\x9b\xaa\tname=s:\xe6\xa0\xb9\tversion=s:1.0.0\tproject_path=s:\xe6\xa0\xb9\tcontent_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tassets=i:3\tdependencies=i:0\nasset\tpackage=i:0\tasset=i:0\tkind=e:module_source\tpath=s:a.pietto\nasset\tpackage=i:0\tasset=i:1\tkind=e:module_source\tpath=s:ctrl\\tline\\n\xe9\x9b\xaa.pietto\nasset\tpackage=i:0\tasset=i:2\tkind=e:module_source\tpath=s:z.pietto\n",
    "ordered_project_errors": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:error\tpackages=i:0\terrors=i:2\tdiagnostics=i:0\trejections=i:0\nerror\terror=i:0\tkind=e:config_schema\tmessage=s:first\tpath=s:pietto-package.toml\nerror\terror=i:1\tkind=e:project_path\tmessage=s:second\tpath=n:\n",
    "parser_diagnostic": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:error\tpackages=i:0\terrors=i:0\tdiagnostics=i:1\trejections=i:0\ndiagnostic\tdiagnostic=i:0\tcode=s:PIE-P1000\tseverity=e:error\tmessage=s:bad\\ttoken\\n\tpath=s:bad.pietto\tline=i:2\tcolumn=i:3\tend_line=n:\tend_column=n:\tsuggestion=s:fix \xe9\x9b\xaa\n",
    "cycle": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:cycle\tconflict_reasons=i:0\toccurrences=i:2\tmessage=s:cycle\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:1111111111111111111111111111111111111111111111111111111111111111\tnamespace=s:example\tname=s:child\tversion=s:1.0.0\tcontent_digest_pin=s:2222222222222222222222222222222222222222222222222222222222222222\tlocator_kind=e:local_directory\tauthored_path=s:../deps/child\tresolved_project_path=s:deps/child\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:child\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:deps/child\tdeclaring_content_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tnamespace=s:example\tname=s:root\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../../root\tresolved_project_path=s:root\n",
    "physical_version_conflict": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:conflict\tconflict_reasons=i:1\toccurrences=i:2\tmessage=s:physical\nrejection_reason\trejection=i:0\treason=i:0\tvalue=e:physical_root_incompatible_coordinate\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:1\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:2.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\n",
    "identity_digest_conflict": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:conflict\tconflict_reasons=i:2\toccurrences=i:2\tmessage=s:identity digest\nrejection_reason\trejection=i:0\treason=i:0\tvalue=e:identity_different_physical_root\nrejection_reason\trejection=i:0\treason=i:1\tvalue=e:incompatible_content_digest_pin\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../deps/one\tresolved_project_path=s:deps/one\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:1\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:2.0.0\tcontent_digest_pin=s:2222222222222222222222222222222222222222222222222222222222222222\tlocator_kind=e:local_directory\tauthored_path=s:../deps/two\tresolved_project_path=s:deps/two\n",
    "digest_conflict": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:conflict\tconflict_reasons=i:1\toccurrences=i:2\tmessage=s:digest\nrejection_reason\trejection=i:0\treason=i:0\tvalue=e:incompatible_content_digest_pin\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:1\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:2222222222222222222222222222222222222222222222222222222222222222\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\n",
    "occurrence_conflict": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:conflict\tconflict_reasons=i:1\toccurrences=i:2\tmessage=s:occurrences\nrejection_reason\trejection=i:0\treason=i:0\tvalue=e:incompatible_occurrences\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../dep\tresolved_project_path=s:dep\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:1\tdeclaring_namespace=s:example\tdeclaring_name=s:root\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:root\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:dep\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:.././dep\tresolved_project_path=s:dep\n",
    "diamond": b"inspection\tformat=e:pietto.package-inspection.v1\toutcome=e:rejected\tpackages=i:0\terrors=i:0\tdiagnostics=i:0\trejections=i:1\nrejection\trejection=i:0\tkind=e:diamond\tconflict_reasons=i:0\toccurrences=i:2\tmessage=s:diamond\nrejection_occurrence\trejection=i:0\toccurrence=i:0\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:left\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:deps/left\tdeclaring_content_digest=s:2222222222222222222222222222222222222222222222222222222222222222\tnamespace=s:example\tname=s:leaf\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../leaf\tresolved_project_path=s:deps/leaf\nrejection_occurrence\trejection=i:0\toccurrence=i:1\tdependency_position=i:0\tdeclaring_namespace=s:example\tdeclaring_name=s:right\tdeclaring_version=s:1.0.0\tdeclaring_project_path=s:deps/right\tdeclaring_content_digest=s:3333333333333333333333333333333333333333333333333333333333333333\tnamespace=s:example\tname=s:leaf\tversion=s:1.0.0\tcontent_digest_pin=s:1111111111111111111111111111111111111111111111111111111111111111\tlocator_kind=e:local_directory\tauthored_path=s:../leaf\tresolved_project_path=s:deps/leaf\n",
}
EXPECTED_CANONICAL_BYTES: Mapping[str, bytes] = MappingProxyType(
    _EXPECTED_CANONICAL_BYTES_LITERAL
)


def _replace_field(
    record: PackagePureRecord,
    key: str,
    value: PackagePureValue,
) -> PackagePureRecord:
    return replace(
        record,
        fields=tuple(
            replace(field, value=value) if field.key == key else field
            for field in record.fields
        ),
    )


def _replace_record(
    document: PackagePureDocument,
    position: int,
    record: PackagePureRecord,
) -> PackagePureDocument:
    records = list(document.records)
    records[position] = record
    return replace(document, records=tuple(records))


def _rejected_vectors() -> tuple[PackageDifferentialVector, ...]:
    accepted = {vector_id: document for vector_id, _, document in _accepted_documents()}
    zero = accepted["zero_dependency_root"]
    one = accepted["one_dependency_owner_isolation"]
    multiple = accepted["multiple_dependencies"]
    duplicate = accepted["duplicate_dependency_occurrences"]
    errors = accepted["ordered_project_errors"]
    cycle = accepted["cycle"]
    diamond = accepted["diamond"]

    def rejected(
        vector_id: str,
        purpose: str,
        document: PackagePureDocument,
        status: PackagePureStatus,
        record: int | None = None,
        field: int | None = None,
    ) -> PackageDifferentialVector:
        return PackageDifferentialVector(
            vector_format=PACKAGE_DIFFERENTIAL_VECTOR_FORMAT,
            vector_id=vector_id,
            purposes=(purpose,),
            classification=PackageDifferentialClassification.PORTABLE_REJECTION,
            document=document,
            expected_status=status,
            expected_record_position=record,
            expected_field_position=field,
        )

    wrong_key_header = replace(
        zero.records[0],
        fields=(
            zero.records[0].fields[1],
            zero.records[0].fields[0],
            *zero.records[0].fields[2:],
        ),
    )
    extra_field_header = replace(
        zero.records[0],
        fields=(
            *zero.records[0].fields,
            PackagePureField(key="extra", value=package_pure_text("x")),
        ),
    )
    optional_extra = PackagePureValue(tag=PackagePureTag.ABSENT, text="x")
    sparse_rejections = _document(
        _header("rejected", rejections=2),
        *cycle.records[1:],
        _rejection(2, "cycle", reasons=0, occurrences=1, message="later"),
        _occurrence(
            2,
            0,
            0,
            ("example", "root", "1.0.0", "root", _A),
            ("example", "root", "1.0.0", "root", _A),
            ".",
        ),
    )
    conflicting_families = _document(
        _header("error", errors=1, rejections=1),
        _error(0, "project_resource", "failed", None),
        *cycle.records[1:],
    )
    return (
        rejected(
            "empty_document",
            "empty_document",
            PackagePureDocument(),
            PackagePureStatus.EMPTY_DOCUMENT,
        ),
        rejected(
            "missing_root_record",
            "missing_required_record",
            _document(_header("success", packages=1)),
            PackagePureStatus.MISSING_REQUIRED_RECORD,
            0,
        ),
        rejected(
            "missing_header",
            "missing_header",
            _document(_root()),
            PackagePureStatus.MISSING_HEADER_RECORD,
            0,
        ),
        rejected(
            "wrong_format_marker",
            "wrong_format_marker",
            _replace_record(zero, 0, _header("success", packages=1, marker="stale")),
            PackagePureStatus.UNKNOWN_FORMAT_MARKER,
            0,
            0,
        ),
        rejected(
            "unknown_record_kind",
            "unknown_record_kind",
            replace(zero, records=(*zero.records, _record("unknown"))),
            PackagePureStatus.UNKNOWN_RECORD_KIND,
            4,
        ),
        rejected(
            "wrong_key_order",
            "wrong_key_order",
            _replace_record(zero, 0, wrong_key_header),
            PackagePureStatus.FIELD_KEY_MISMATCH,
            0,
            0,
        ),
        rejected(
            "missing_field",
            "missing_field",
            _replace_record(
                zero, 0, replace(zero.records[0], fields=zero.records[0].fields[:-1])
            ),
            PackagePureStatus.FIELD_ARITY_MISMATCH,
            0,
        ),
        rejected(
            "extra_field",
            "extra_field",
            _replace_record(zero, 0, extra_field_header),
            PackagePureStatus.FIELD_ARITY_MISMATCH,
            0,
        ),
        rejected(
            "wrong_scalar_tag",
            "wrong_scalar_tag",
            _replace_record(
                zero,
                0,
                _replace_field(zero.records[0], "packages", package_pure_text("1")),
            ),
            PackagePureStatus.VALUE_TAG_MISMATCH,
            0,
            2,
        ),
        rejected(
            "malformed_optional",
            "malformed_optional",
            _replace_record(
                errors, 1, _replace_field(errors.records[1], "path", optional_extra)
            ),
            PackagePureStatus.EXTRA_VALUE_PAYLOAD,
            1,
            3,
        ),
        rejected(
            "negative_ordinal",
            "negative_ordinal",
            _replace_record(
                zero,
                2,
                _replace_field(zero.records[2], "package", package_pure_integer(-1)),
            ),
            PackagePureStatus.NEGATIVE_INTEGER,
            2,
            0,
        ),
        rejected(
            "sparse_package_ordinal",
            "sparse_package_ordinal",
            _replace_record(
                one,
                4,
                _replace_field(one.records[4], "package", package_pure_integer(2)),
            ),
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            4,
            0,
        ),
        rejected(
            "integer_out_of_range",
            "integer_out_of_range",
            _replace_record(
                zero,
                0,
                _replace_field(
                    zero.records[0],
                    "packages",
                    package_pure_integer(PACKAGE_PURE_MAX_INTEGER + 1),
                ),
            ),
            PackagePureStatus.INTEGER_OUT_OF_RANGE,
            0,
            2,
        ),
        rejected(
            "invalid_enumeration",
            "invalid_enumeration",
            _replace_record(
                zero,
                2,
                _replace_field(
                    zero.records[2], "role", package_pure_enumeration("winner")
                ),
            ),
            PackagePureStatus.UNKNOWN_ENUMERATION,
            2,
            1,
        ),
        rejected(
            "invalid_sha256",
            "invalid_sha256",
            _replace_record(
                zero,
                2,
                _replace_field(
                    zero.records[2], "content_digest", package_pure_text("A" * 64)
                ),
            ),
            PackagePureStatus.INVALID_SHA256,
            2,
            6,
        ),
        rejected(
            "duplicate_header",
            "duplicate_singleton_header",
            replace(zero, records=(*zero.records, zero.records[0])),
            PackagePureStatus.DUPLICATE_SINGLETON_RECORD,
            4,
        ),
        rejected(
            "duplicate_root",
            "duplicate_singleton_root",
            replace(zero, records=(*zero.records, zero.records[1])),
            PackagePureStatus.DUPLICATE_SINGLETON_RECORD,
            4,
        ),
        rejected(
            "wrong_section_order",
            "wrong_section_order",
            replace(
                zero,
                records=(
                    zero.records[0],
                    zero.records[1],
                    zero.records[3],
                    zero.records[2],
                ),
            ),
            PackagePureStatus.SECTION_ORDER_VIOLATION,
            2,
        ),
        rejected(
            "wrong_child_count",
            "wrong_child_count",
            _replace_record(
                zero,
                2,
                _replace_field(zero.records[2], "assets", package_pure_integer(2)),
            ),
            PackagePureStatus.CHILD_COUNT_MISMATCH,
            2,
        ),
        rejected(
            "package_count_mismatch",
            "package_count_mismatch",
            _replace_record(
                zero,
                0,
                _replace_field(zero.records[0], "packages", package_pure_integer(2)),
            ),
            PackagePureStatus.INCONSISTENT_RECORD_STATE,
            2,
            1,
        ),
        rejected(
            "root_not_final",
            "root_not_final",
            _replace_record(
                multiple,
                2,
                _replace_field(
                    multiple.records[2], "role", package_pure_enumeration("root")
                ),
            ),
            PackagePureStatus.INCONSISTENT_RECORD_STATE,
            2,
            1,
        ),
        rejected(
            "target_outside_ledger",
            "target_outside_ledger",
            _replace_record(
                one,
                6,
                _replace_field(
                    one.records[6], "target_package", package_pure_integer(99)
                ),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            6,
            9,
        ),
        rejected(
            "target_self",
            "target_self_or_later",
            _replace_record(
                one,
                6,
                _replace_field(
                    one.records[6], "target_package", package_pure_integer(1)
                ),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            6,
            9,
        ),
        rejected(
            "duplicate_package_position",
            "duplicate_package_position",
            _replace_record(
                multiple,
                4,
                _replace_field(multiple.records[4], "package", package_pure_integer(0)),
            ),
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            4,
            0,
        ),
        rejected(
            "sparse_asset_position",
            "sparse_asset_position",
            _replace_record(
                zero,
                3,
                _replace_field(zero.records[3], "asset", package_pure_integer(1)),
            ),
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            3,
            1,
        ),
        rejected(
            "sparse_dependency_position",
            "sparse_dependency_position",
            _replace_record(
                duplicate,
                7,
                _replace_field(
                    duplicate.records[7], "dependency", package_pure_integer(2)
                ),
            ),
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            7,
            1,
        ),
        rejected(
            "sparse_error_position",
            "sparse_error_position",
            _replace_record(
                errors,
                2,
                _replace_field(errors.records[2], "error", package_pure_integer(2)),
            ),
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            2,
            0,
        ),
        rejected(
            "sparse_rejection_position",
            "sparse_rejection_position",
            sparse_rejections,
            PackagePureStatus.ORDINAL_SEQUENCE_VIOLATION,
            4,
            0,
        ),
        rejected(
            "success_with_error",
            "success_with_failure_evidence",
            _document(
                _header("success", packages=1, errors=1),
                *zero.records[1:],
                _error(0, "project_resource", "failed", None),
            ),
            PackagePureStatus.INCONSISTENT_DOCUMENT_STATE,
            0,
        ),
        rejected(
            "failed_without_evidence",
            "failed_without_evidence",
            _document(_header("error")),
            PackagePureStatus.INCONSISTENT_DOCUMENT_STATE,
            0,
        ),
        rejected(
            "conflicting_failure_families",
            "conflicting_failure_families",
            conflicting_families,
            PackagePureStatus.INCONSISTENT_DOCUMENT_STATE,
            0,
        ),
        rejected(
            "cycle_occurrence_count_mismatch",
            "cycle_occurrence_count_mismatch",
            _replace_record(
                cycle,
                1,
                _replace_field(
                    cycle.records[1], "occurrences", package_pure_integer(3)
                ),
            ),
            PackagePureStatus.CHILD_COUNT_MISMATCH,
            1,
        ),
        rejected(
            "unknown_conflict_reason",
            "unknown_conflict_reason",
            _replace_record(
                accepted["physical_version_conflict"],
                2,
                _replace_field(
                    accepted["physical_version_conflict"].records[2],
                    "value",
                    package_pure_enumeration("winner"),
                ),
            ),
            PackagePureStatus.UNKNOWN_ENUMERATION,
            2,
            2,
        ),
        rejected(
            "broken_cycle_authority_chain",
            "malformed_declaring_authority_relation",
            _replace_record(
                cycle,
                2,
                _replace_field(cycle.records[2], "name", package_pure_text("other")),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            2,
        ),
        rejected(
            "dependency_target_mismatch",
            "dependency_target_authority_mismatch",
            _replace_record(
                one,
                6,
                _replace_field(one.records[6], "name", package_pure_text("other")),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            6,
        ),
        rejected(
            "diamond_target_mismatch",
            "diamond_target_authority_mismatch",
            _replace_record(
                diamond,
                3,
                _replace_field(diamond.records[3], "name", package_pure_text("other")),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            3,
        ),
        rejected(
            "root_coordinate_mismatch",
            "root_coordinate_mismatch",
            _replace_record(
                zero,
                1,
                _replace_field(zero.records[1], "name", package_pure_text("other")),
            ),
            PackagePureStatus.INCONSISTENT_SCOPE_RELATION,
            1,
        ),
        rejected(
            "trailing_record",
            "trailing_record",
            replace(
                zero,
                records=(*zero.records, _error(0, "project_resource", "late", None)),
            ),
            PackagePureStatus.TRAILING_RECORD_AFTER_DOCUMENT,
            4,
        ),
        rejected(
            "missing_payload",
            "missing_payload",
            _replace_record(
                zero,
                0,
                _replace_field(
                    zero.records[0],
                    "format",
                    PackagePureValue(tag=PackagePureTag.ENUMERATION),
                ),
            ),
            PackagePureStatus.MISSING_VALUE_PAYLOAD,
            0,
            0,
        ),
        rejected(
            "extra_payload",
            "extra_payload",
            _replace_record(
                zero,
                0,
                _replace_field(
                    zero.records[0],
                    "format",
                    PackagePureValue(
                        tag=PackagePureTag.ENUMERATION,
                        text=PACKAGE_PURE_FORMAT_MARKER,
                        integer=1,
                    ),
                ),
            ),
            PackagePureStatus.EXTRA_VALUE_PAYLOAD,
            0,
            0,
        ),
        rejected(
            "absent_required",
            "absent_not_allowed",
            _replace_record(
                zero, 0, _replace_field(zero.records[0], "format", PACKAGE_PURE_ABSENT)
            ),
            PackagePureStatus.ABSENT_VALUE_NOT_ALLOWED,
            0,
            0,
        ),
    )


def differential_vectors() -> tuple[PackageDifferentialVector, ...]:
    accepted = tuple(
        PackageDifferentialVector(
            vector_format=PACKAGE_DIFFERENTIAL_VECTOR_FORMAT,
            vector_id=vector_id,
            purposes=purposes,
            classification=PackageDifferentialClassification.PORTABLE_EVALUATION,
            document=document,
            expected_status=PackagePureStatus.OK,
            expected_bytes=EXPECTED_CANONICAL_BYTES[vector_id],
        )
        for vector_id, purposes, document in _accepted_documents()
    )
    return accepted + _rejected_vectors()
