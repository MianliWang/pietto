from __future__ import annotations

from dataclasses import FrozenInstanceError
import hashlib
import inspect
from pathlib import Path
import struct

import pytest

import pietto
import pietto._project as project_package
from pietto._project.model import (
    ProjectDiscoveryError,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_load_plan import (
    PackageLoadPlanBlockerKind,
    PackageLoadPlanResult,
    _build_package_load_plan,
)
from pietto._project.package_loader import LoadedRootPackage, _load_root_package
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
import pietto._project.package_rejection as package_rejection
from pietto._project.package_rejection import (
    PackageConflictReason,
    PackageRejectionDiagnostic,
    PackageRejectionProduct,
    _diagnose_package_load_result,
)
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root


_SOURCE = b"shape Row:\n    id: Int\n"


def test_direct_cycle_diagnostic_preserves_occurrence_and_has_no_host_path(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    root_digest = _write_package(
        project,
        "root",
        name="root",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "."),),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    product = _diagnose_package_load_result(blocked)

    assert (
        blocked.plan is None
        and blocked.blockers[0].kind is PackageLoadPlanBlockerKind.CYCLE
    )
    assert product.rejected and product.plan_result is blocked
    assert len(product.diagnostics) == 1
    diagnostic = product.diagnostics[0]
    assert diagnostic.blocker is blocked.blockers[0]
    assert diagnostic.kind is PackageLoadPlanBlockerKind.CYCLE
    assert diagnostic.occurrences == blocked.blockers[0].occurrences
    assert diagnostic.occurrences[0] is blocked.blockers[0].occurrences[0]
    assert "dependency[0]" in diagnostic.message
    assert "path='.'" in diagnostic.message
    assert "namespace='example', name='root', version='1.0.0'" in diagnostic.message
    assert str(tmp_path) not in diagnostic.message


def test_multi_package_cycle_chain_keeps_dfs_order_and_is_deterministic(
    tmp_path: Path,
) -> None:
    project = tmp_path / "project"
    child_digest = _write_package(
        project,
        "deps/child",
        name="child",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "../../root"),),
    )
    root_digest = _write_package(
        project,
        "root",
        name="root",
        dependencies=(("example", "child", "1.0.0", child_digest, "../deps/child"),),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    first = _diagnose_package_load_result(blocked)
    second = _diagnose_package_load_result(blocked)

    assert first == second
    diagnostic = first.diagnostics[0]
    assert tuple(item.declaration.name for item in diagnostic.occurrences) == (
        "child",
        "root",
    )
    assert diagnostic.message.index("child") < diagnostic.message.rindex("root")
    assert str(tmp_path) not in diagnostic.message


def test_conflict_same_identity_different_physical_roots_is_distinguished(
    tmp_path: Path,
) -> None:
    project = tmp_path / "identity-roots"
    one_digest = _write_package(project, "deps/one", name="same", version="1.0.0")
    two_digest = _write_package(project, "deps/two", name="same", version="2.0.0")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "same", "1.0.0", one_digest, "../deps/one"),
            ("example", "same", "2.0.0", two_digest, "../deps/two"),
        ),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    diagnostic = _diagnose_package_load_result(blocked).diagnostics[0]

    assert diagnostic.kind is PackageLoadPlanBlockerKind.CONFLICT
    assert PackageConflictReason.IDENTITY_DIFFERENT_PHYSICAL_ROOT in (
        diagnostic.conflict_reasons
    )
    assert len(diagnostic.occurrences) == 2
    assert "physical" not in diagnostic.message.lower()
    assert str(tmp_path) not in diagnostic.message


def test_conflict_same_physical_root_incompatible_coordinate_is_distinguished(
    tmp_path: Path,
) -> None:
    project = tmp_path / "coordinate"
    dep_digest = _write_package(project, "dep", name="dep", version="1.0.0")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "dep", "1.0.0", dep_digest, "../dep"),
            ("example", "dep", "2.0.0", dep_digest, "../dep"),
        ),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    diagnostic = _diagnose_package_load_result(blocked).diagnostics[0]

    assert diagnostic.conflict_reasons[0] is (
        PackageConflictReason.PHYSICAL_ROOT_INCOMPATIBLE_COORDINATE
    )
    assert "2.0.0" in diagnostic.message


def test_conflict_incompatible_digest_pin_is_distinguished(tmp_path: Path) -> None:
    project = tmp_path / "digest"
    dep_digest = _write_package(project, "dep", name="dep")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "dep", "1.0.0", dep_digest, "../dep"),
            ("example", "dep", "1.0.0", "0" * 64, "../dep"),
        ),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    diagnostic = _diagnose_package_load_result(blocked).diagnostics[0]

    assert PackageConflictReason.INCOMPATIBLE_CONTENT_DIGEST_PIN in (
        diagnostic.conflict_reasons
    )
    assert "digest pin" in diagnostic.message
    assert dep_digest not in diagnostic.message


def test_conflict_nonidentical_occurrences_same_authority_is_distinguished(
    tmp_path: Path,
) -> None:
    project = tmp_path / "occurrence"
    dep_digest = _write_package(project, "dep", name="dep")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "dep", "1.0.0", dep_digest, "../dep"),
            ("example", "dep", "1.0.0", dep_digest, ".././dep"),
        ),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    diagnostic = _diagnose_package_load_result(blocked).diagnostics[0]

    assert diagnostic.conflict_reasons == (
        PackageConflictReason.INCOMPATIBLE_OCCURRENCES,
    )
    assert tuple(item.declaration.path for item in diagnostic.occurrences) == (
        "../dep",
        ".././dep",
    )


def test_diamond_retains_both_incoming_authorities_without_winner(
    tmp_path: Path,
) -> None:
    project = tmp_path / "diamond"
    leaf_digest = _write_package(project, "deps/leaf", name="leaf")
    left_digest = _write_package(
        project,
        "deps/left",
        name="left",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    right_digest = _write_package(
        project,
        "deps/right",
        name="right",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    root_digest = _write_package(
        project,
        "root",
        dependencies=(
            ("example", "left", "1.0.0", left_digest, "../deps/left"),
            ("example", "right", "1.0.0", right_digest, "../deps/right"),
        ),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))

    diagnostic = _diagnose_package_load_result(blocked).diagnostics[0]

    assert diagnostic.kind is PackageLoadPlanBlockerKind.DIAMOND
    assert diagnostic.blocker is blocked.blockers[0]
    assert diagnostic.occurrences == blocked.blockers[0].occurrences
    assert tuple(
        package_rejection._package_coordinate(item.declaring_package).identity.name
        for item in diagnostic.occurrences
    ) == ("left", "right")
    assert "no-winner" in diagnostic.message
    assert str(tmp_path) not in diagnostic.message


def test_success_and_exact_duplicates_have_no_rejection_diagnostics(
    tmp_path: Path,
) -> None:
    project = tmp_path / "accepted"
    dep_digest = _write_package(project, "dep", name="dep")
    declaration = ("example", "dep", "1.0.0", dep_digest, "../dep")
    root_digest = _write_package(
        project,
        "root",
        dependencies=(declaration, declaration),
    )
    planned = _build_package_load_plan(_load_root(project, "root", root_digest))

    product = _diagnose_package_load_result(planned)

    assert planned.ok and product.plan_result is planned
    assert not product.rejected and product.diagnostics == ()
    assert len(planned.plan.entries[-1].dependencies) == 2  # type: ignore[union-attr]


def test_zero_one_and_multihop_successes_remain_unchanged(tmp_path: Path) -> None:
    zero_project = tmp_path / "zero"
    zero_digest = _write_package(zero_project, "root")
    zero_plan = _build_package_load_plan(_load_root(zero_project, "root", zero_digest))

    hop_project = tmp_path / "hop"
    leaf_digest = _write_package(hop_project, "deps/leaf", name="leaf")
    middle_digest = _write_package(
        hop_project,
        "deps/middle",
        name="middle",
        dependencies=(("example", "leaf", "1.0.0", leaf_digest, "../leaf"),),
    )
    root_digest = _write_package(
        hop_project,
        "root",
        dependencies=(("example", "middle", "1.0.0", middle_digest, "../deps/middle"),),
    )
    hop_plan = _build_package_load_plan(_load_root(hop_project, "root", root_digest))

    for result in (zero_plan, hop_plan):
        product = _diagnose_package_load_result(result)
        assert result.ok and not product.rejected and product.diagnostics == ()
    assert len(zero_plan.plan.entries) == 1  # type: ignore[union-attr]
    assert len(hop_plan.plan.entries) == 3  # type: ignore[union-attr]


def test_all_blockers_are_diagnosed_in_exact_future_authority_order(
    tmp_path: Path,
) -> None:
    project = tmp_path / "multiple"
    root_digest = _write_package(
        project,
        "root",
        name="root",
        dependencies=(("example", "root", "1.0.0", "a" * 64, "."),),
    )
    blocked = _build_package_load_plan(_load_root(project, "root", root_digest))
    blocker = blocked.blockers[0]
    multiple = object.__new__(PackageLoadPlanResult)
    object.__setattr__(multiple, "plan", None)
    object.__setattr__(multiple, "errors", ())
    object.__setattr__(multiple, "blockers", (blocker, blocker))
    object.__setattr__(multiple, "diagnostics", ())

    product = _diagnose_package_load_result(multiple)

    assert tuple(item.blocker for item in product.diagnostics) == (blocker, blocker)


def test_diagnostic_boundary_is_private_canonical_pure_and_nonrecovering(
    tmp_path: Path,
) -> None:
    project = tmp_path / "private"
    root_digest = _write_package(project, "root")
    planned = _build_package_load_plan(_load_root(project, "root", root_digest))
    product = _diagnose_package_load_result(planned)

    assert package_rejection.__all__ == ()
    for carrier in (PackageRejectionDiagnostic, PackageRejectionProduct):
        assert hasattr(carrier, "__slots__")
        with pytest.raises(TypeError):
            carrier()  # type: ignore[call-arg]
    with pytest.raises(FrozenInstanceError):
        product.diagnostics = ()  # pyright: ignore[reportAttributeAccessIssue]

    contradictory = object.__new__(PackageLoadPlanResult)
    object.__setattr__(contradictory, "plan", planned.plan)
    object.__setattr__(
        contradictory,
        "errors",
        (
            ProjectDiscoveryError(
                ProjectDiscoveryErrorKind.PROJECT_RESOURCE,
                "contradictory",
            ),
        ),
    )
    object.__setattr__(contradictory, "blockers", ())
    object.__setattr__(contradictory, "diagnostics", ())
    with pytest.raises(ValueError, match="forbid rejection evidence"):
        _diagnose_package_load_result(contradictory)
    for name in (
        "PackageConflictReason",
        "PackageRejectionDiagnostic",
        "PackageRejectionProduct",
        "_diagnose_package_load_result",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)

    source = inspect.getsource(package_rejection)
    for forbidden in (
        "open(",
        "pathlib",
        "import os",
        "requests",
        "urllib",
        "http://",
        "https://",
        "_build_package_load_plan",
        "_load_dependency_package",
        "canonical_path",
        "device",
        "inode",
        "id(",
        "json",
    ):
        assert forbidden not in source


def _write_package(
    project: Path,
    package_path: str,
    *,
    namespace: str = "example",
    name: str = "root",
    version: str = "1.0.0",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True, exist_ok=True)
    manifest = _manifest(
        namespace=namespace,
        name=name,
        version=version,
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    (package_root / "main.pietto").write_bytes(_SOURCE)
    return _digest(manifest)


def _load_root(project: Path, package_path: str, digest: str) -> LoadedRootPackage:
    pinned_root = _pin_project_root(project)
    assert type(pinned_root) is ProjectPinnedRoot
    activation = ProjectRootPackageActivation(
        path=package_path,
        namespace="example",
        name="root",
        version="1.0.0",
        sha256=digest,
    )
    located = _locate_root_package(pinned_root, activation)
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return loaded.loaded_package


def _manifest(
    *,
    namespace: str,
    name: str,
    version: str,
    dependencies: tuple[tuple[str, str, str, str, str], ...],
) -> bytes:
    lines = [
        "schema_version = 1",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        f'version = "{version}"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    for dep_namespace, dep_name, dep_version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{dep_namespace}"',
                f'name = "{dep_name}"',
                f'version = "{dep_version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    return ("\n".join(lines) + "\n").encode()


def _digest(manifest: bytes) -> str:
    stream = bytearray(b"pietto-package-content-v1\0")
    for path, content in (
        ("pietto-package.toml", manifest),
        ("main.pietto", _SOURCE),
    ):
        path_bytes = path.encode()
        stream.extend(struct.pack(">Q", len(path_bytes)))
        stream.extend(path_bytes)
        stream.extend(struct.pack(">Q", len(content)))
        stream.extend(content)
    return hashlib.sha256(stream).hexdigest()
