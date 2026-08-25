from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
import inspect
from pathlib import Path

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_capability_requirements as package_requirements
from pietto._project.capability_availability import (
    PackageCapabilityRequirementBinding,
)
from pietto._project.model import (
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
)
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_inspection import PackageInspectionPackage
from pietto._project.package_load_plan import (
    LoadedDependencyPackage,
    PackageLoadPlan,
    _build_package_load_plan,
)
from pietto._project.package_loader import (
    LoadedRootPackage,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.package_manifest import (
    PackageManifest,
    PackageManifestAsset,
    PackageManifestCapabilityRequirements,
    PackageManifestNormalizationResult,
    _normalize_package_manifest,
)
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.capability_profiles import (
    CapabilityRequirementCollection,
    CapabilityRequirementCollectionIdentity,
    CapabilityRequirementOccurrence,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"
DOMAIN_VALUES = (
    "logical_type",
    "literal",
    "parameter",
    "scalar_function",
    "unary_operator",
    "binary_operator",
    "comparison",
    "null_test",
    "clause",
    "aggregate",
    "window_function",
    "expression_stage",
    "conversion",
    "dialect_lowering",
    "extension_signature",
)


def _entry(
    domain: str,
    *,
    subject: str | None = None,
    operation: str | None = None,
    operands: tuple[str, ...] = (),
    context: str | None = None,
    dialect: str | None = None,
    extension: str | None = None,
) -> str:
    lines = [f'domain = "{domain}"']
    for field_name, value in (
        ("subject", subject),
        ("operation", operation),
    ):
        if value is not None:
            lines.append(f'{field_name} = "{value}"')
    lines.append("operands = [" + ", ".join(f'"{value}"' for value in operands) + "]")
    for field_name, value in (
        ("context", context),
        ("dialect", dialect),
        ("extension", extension),
    ):
        if value is not None:
            lines.append(f'{field_name} = "{value}"')
    return "\n".join(lines)


def _declaration(
    *entries: str,
    root_body: tuple[str, ...] = (),
) -> str:
    lines = [
        "[capability_requirements]",
        'namespace = "exact.requirements"',
        'name = "runtime"',
        *root_body,
    ]
    for entry in entries:
        lines.extend(("", "[[capability_requirements.entries]]", entry))
    return "\n".join(lines)


def _manifest(
    *,
    schema_version: int = 2,
    name: str = "root",
    declaration: str = "",
    root_extra: tuple[str, ...] = (),
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        'namespace = "example"',
        f'name = "{name}"',
        'version = "1.0.0"',
        *root_extra,
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    for namespace, dep_name, version, sha256, path in dependencies:
        lines.extend(
            (
                "",
                "[[dependencies]]",
                f'namespace = "{namespace}"',
                f'name = "{dep_name}"',
                f'version = "{version}"',
                f'sha256 = "{sha256}"',
                f'path = "{path}"',
            )
        )
    if declaration:
        lines.extend(("", declaration))
    return ("\n".join(lines) + "\n").encode()


def test_exact_private_model_reuses_existing_semantic_carriers() -> None:
    identity = CapabilityRequirementCollectionIdentity("exact.ns", "runtime")
    key = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
    declaration = PackageManifestCapabilityRequirements(identity, (key,))
    asset = PackageManifestAsset("module_source", "main.pietto")
    manifest = PackageManifest(2, "example", "root", "1.0.0", (asset,), (), declaration)

    assert tuple(
        field.name for field in fields(PackageManifestCapabilityRequirements)
    ) == ("identity", "keys", "extension_signature_selectors")
    assert tuple(field.name for field in fields(PackageManifest)) == (
        "schema_version",
        "namespace",
        "name",
        "version",
        "assets",
        "dependencies",
        "capability_requirements",
    )
    assert manifest.capability_requirements is declaration
    assert declaration.identity is identity
    assert declaration.keys[0] is key
    assert type(declaration.keys[0]) is CapabilityKey
    assert not hasattr(declaration, "digest")
    assert package_requirements.__all__ == ()
    for value in (declaration, manifest):
        assert hasattr(type(value), "__slots__")
        assert not hasattr(value, "__dict__")
        assert isinstance(hash(value), int)
    with pytest.raises(FrozenInstanceError):
        declaration.keys = ()  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(TypeError):
        PackageManifestCapabilityRequirements(identity, [key])  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="duplicates key 0"):
        PackageManifestCapabilityRequirements(identity, (key, key))
    with pytest.raises(ValueError, match="version 1 forbids"):
        PackageManifest(1, "example", "root", "1.0.0", (asset,), (), declaration)
    assert (
        PackageManifest(
            2, "example", "root", "1.0.0", (asset,), ()
        ).capability_requirements
        is None
    )


def test_schema_one_and_two_are_valid_and_schema_one_rejects_the_new_key() -> None:
    v1 = _normalize(_manifest(schema_version=1))
    v2 = _normalize(_manifest(schema_version=2))
    rejected = _normalize(_manifest(schema_version=1, declaration=_declaration()))

    assert v1.ok and v1.manifest is not None
    assert v2.ok and v2.manifest is not None
    assert v1.manifest.capability_requirements is None
    assert v2.manifest.capability_requirements is None
    assert not rejected.ok
    assert _messages(rejected) == (
        "Package manifest contains unsupported top-level key: capability_requirements.",
    )


@pytest.mark.parametrize(
    "replacement",
    (
        "true",
        "0",
        "4",
        "-1",
        '"2"',
        "2.0",
        "1979-05-27",
    ),
)
def test_schema_version_is_only_exact_non_boolean_integer_one_two_or_three(
    replacement: str,
) -> None:
    result = _normalize(
        _manifest(schema_version=2).replace(
            b"schema_version = 2",
            f"schema_version = {replacement}".encode(),
            1,
        )
    )

    assert not result.ok
    assert _messages(result)[0] == (
        "Package manifest schema_version must be exact integer 1, 2, or 3."
    )


def test_undeclared_declared_empty_and_ordered_binding_states(
    tmp_path: Path,
) -> None:
    entries = (
        _entry("aggregate", operation="sum", operands=("Int",)),
        _entry("logical_type", subject="Text"),
    )
    cases = (
        ("v1", 1, "", None),
        ("v2-absent", 2, "", None),
        ("v2-empty", 2, _declaration(), 0),
        ("v2-entries", 2, _declaration(*entries), 2),
    )
    loaded_packages: dict[str, LoadedRootPackage] = {}
    for package_path, schema_version, declaration, expected_count in cases:
        digest = _write_package(
            tmp_path,
            package_path,
            schema_version=schema_version,
            declaration=declaration,
        )
        loaded = _load_root(tmp_path, package_path, digest)
        loaded_packages[package_path] = loaded
        binding = _package_capability_requirement_binding(loaded)
        if expected_count is None:
            assert binding is None
            continue
        assert type(binding) is PackageCapabilityRequirementBinding
        assert binding.package is loaded
        assert type(binding.requirements) is CapabilityRequirementCollection
        assert len(binding.requirements.occurrences) == expected_count

    loaded = loaded_packages["v2-entries"]
    declaration = loaded.catalog.root_package.manifest.capability_requirements
    binding = _package_capability_requirement_binding(loaded)
    assert declaration is not None and binding is not None
    assert binding.requirements.identity is declaration.identity
    assert tuple(item.position for item in binding.requirements.occurrences) == (0, 1)
    assert all(
        type(item) is CapabilityRequirementOccurrence
        for item in binding.requirements.occurrences
    )
    assert tuple(item.owner for item in binding.requirements.occurrences) == (
        declaration.identity,
        declaration.identity,
    )
    assert tuple(item.key for item in binding.requirements.occurrences) == (
        declaration.keys
    )
    assert all(
        occurrence.key is declaration.keys[position]
        for position, occurrence in enumerate(binding.requirements.occurrences)
    )


def test_exact_root_and_nested_aot_syntax_are_accepted() -> None:
    empty = _normalize(_manifest(declaration=_declaration()))
    populated = _normalize(
        _manifest(declaration=_declaration(_entry("logical_type", subject="Int")))
    )

    assert empty.ok and empty.manifest is not None
    assert empty.manifest.capability_requirements is not None
    assert empty.manifest.capability_requirements.keys == ()
    assert populated.ok and populated.manifest is not None
    assert populated.manifest.capability_requirements is not None
    assert len(populated.manifest.capability_requirements.keys) == 1


@pytest.mark.parametrize(
    ("declaration", "field_name"),
    (
        ('[capability_requirements]\nname = "runtime"', "namespace"),
        (
            '[capability_requirements]\nnamespace = " "\nname = "runtime"',
            "namespace",
        ),
        ('[capability_requirements]\nnamespace = "req"', "name"),
        (
            '[capability_requirements]\nnamespace = "req"\nname = " "',
            "name",
        ),
    ),
)
def test_collection_identity_fields_are_required_nonblank_text(
    declaration: str,
    field_name: str,
) -> None:
    result = _normalize(_manifest(declaration=declaration))

    assert not result.ok
    assert (
        f"Package manifest capability_requirements.{field_name} "
        "must be a nonblank string."
    ) in _messages(result)


@pytest.mark.parametrize(
    ("manifest", "message"),
    (
        (
            _manifest(
                root_extra=(
                    'capability_requirements = { namespace = "req", '
                    'name = "runtime", entries = [] }',
                )
            ),
            "must use exact root [capability_requirements] syntax",
        ),
        (
            _manifest(declaration=_declaration(root_body=("entries = []",))),
            "entries must be omitted or use one or more exact nested",
        ),
        (
            _manifest(
                declaration=_declaration(
                    root_body=(
                        'entries = [{ domain = "logical_type", subject = "Int", '
                        "operands = [] }]",
                    )
                )
            ),
            "entries must use exact [[capability_requirements.entries]] syntax",
        ),
        (
            _manifest(
                declaration=(
                    _declaration()
                    + "\n[capability_requirements.entries]\n"
                    + 'domain = "logical_type"\nsubject = "Int"\noperands = []'
                )
            ),
            "entries must be omitted or use one or more exact nested",
        ),
        (
            _manifest(
                declaration='["capability_requirements"]\nnamespace = "req"\nname = "runtime"'
            ),
            "must use exact root [capability_requirements] syntax",
        ),
        (
            _manifest(
                declaration=(
                    _declaration()
                    + '\n[[capability_requirements."entries"]]\n'
                    + 'domain = "logical_type"\nsubject = "Int"\noperands = []'
                )
            ),
            "entries must use exact [[capability_requirements.entries]] syntax",
        ),
        (
            _manifest(
                declaration=(
                    '[owner.capability_requirements]\nnamespace = "req"\n'
                    'name = "runtime"'
                )
            ),
            "unsupported top-level key: owner",
        ),
    ),
)
def test_alternate_declaration_and_entry_shapes_fail_closed(
    manifest: bytes,
    message: str,
) -> None:
    result = _normalize(manifest)

    assert not result.ok and result.manifest is None
    assert any(message in item for item in _messages(result))
    assert all(
        error.kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA for error in result.errors
    )
    assert all(error.path == "pietto-package.toml" for error in result.errors)


def test_capability_key_mapping_preserves_closed_domains_spelling_and_order() -> None:
    entries = (
        _entry("logical_type", subject=" Int "),
        _entry(
            "scalar_function",
            operation="Coalesce",
            operands=("Text", "Text", " Int "),
            context=" Expression ",
        ),
        _entry("aggregate", operation="sum", operands=("Decimal",)),
        _entry("window_function", operation="row_number"),
        _entry(
            "extension_signature",
            operation="distance",
            operands=("vector", "vector"),
            dialect="PostgreSQL",
            extension="vector",
        ),
    )
    first = _normalize(_manifest(declaration=_declaration(*entries)))
    reordered = _normalize(
        _manifest(declaration=_declaration(entries[1], entries[0], *entries[2:]))
    )

    assert tuple(item.value for item in CapabilityDomain) == DOMAIN_VALUES
    assert first.ok and first.manifest is not None
    assert reordered.ok and reordered.manifest is not None
    declaration = first.manifest.capability_requirements
    other = reordered.manifest.capability_requirements
    assert declaration is not None and other is not None
    assert declaration != other
    assert tuple(key.domain.value for key in declaration.keys) == (
        "logical_type",
        "scalar_function",
        "aggregate",
        "window_function",
        "extension_signature",
    )
    assert declaration.keys[0].subject == " Int "
    assert declaration.keys[0].operation is None
    assert declaration.keys[0].operands == ()
    assert declaration.keys[0].context is None
    assert declaration.keys[1].operation == "Coalesce"
    assert declaration.keys[1].operands == ("Text", "Text", " Int ")
    assert declaration.keys[1].context == " Expression "
    assert declaration.keys[-1].dialect == "PostgreSQL"
    assert declaration.keys[-1].extension == "vector"


@pytest.mark.parametrize(
    ("entries", "message"),
    (
        (('subject = "Int"\noperands = []',), ".domain is required"),
        (
            ('domain = "LOGICAL_TYPE"\nsubject = "Int"\noperands = []',),
            ".domain must be one exact current CapabilityDomain value",
        ),
        (('domain = "logical_type"\nsubject = "Int"',), ".operands is required"),
        (
            ('domain = "logical_type"\nsubject = "Int"\noperands = "Int"',),
            ".operands must be an array of strings",
        ),
        (
            ('domain = "logical_type"\nsubject = "Int"\noperands = [1]',),
            ".operands[0] must be a string",
        ),
        (
            ('domain = "logical_type"\nsubject = "Int"\noperands = [" "]',),
            ".operands[0] must be nonblank",
        ),
        (
            ('domain = "logical_type"\noperands = []',),
            "requires subject or operation",
        ),
        (
            ('domain = "logical_type"\nsubject = ""\noperands = []',),
            ".subject must be nonblank when present",
        ),
        (
            ('domain = "logical_type"\nsubject = 1\noperands = []',),
            ".subject must be a string when present",
        ),
        (
            (
                'domain = "extension_signature"\noperation = "distance"\n'
                'operands = []\nextension = "vector"',
            ),
            ".extension requires dialect",
        ),
        (
            ('domain = "logical_type"\nsubject = "Int"\noperands = []\nextra = "x"',),
            "contains unsupported key: extra",
        ),
        (
            (
                'domain = "logical_type"\nsubject = "Int"\noperands = []',
                'domain = "logical_type"\nsubject = "Int"\noperands = []',
            ),
            "duplicates exact CapabilityKey",
        ),
    ),
)
def test_invalid_entries_are_distinct_deterministic_schema_errors(
    entries: tuple[str, ...],
    message: str,
) -> None:
    result = _normalize(_manifest(declaration=_declaration(*entries)))

    assert not result.ok and result.manifest is None
    assert any(message in item for item in _messages(result))
    assert all(
        error.kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA for error in result.errors
    )


def test_root_and_dependency_packages_retain_only_their_own_declarations(
    tmp_path: Path,
) -> None:
    dependency_digest = _write_package(
        tmp_path,
        "dep",
        name="dep",
        declaration=_declaration(_entry("logical_type", subject="Dependency")),
    )
    root_digest = _write_package(
        tmp_path,
        "root",
        declaration=_declaration(_entry("logical_type", subject="Root")),
        dependencies=(("example", "dep", "1.0.0", dependency_digest, "../dep"),),
    )
    root = _load_root(tmp_path, "root", root_digest)
    result = _build_package_load_plan(root)
    assert result.ok and type(result.plan) is PackageLoadPlan
    dependency = result.plan.entries[0].package
    assert type(dependency) is LoadedDependencyPackage

    root_binding = _package_capability_requirement_binding(root)
    dependency_binding = _package_capability_requirement_binding(dependency)
    assert root_binding is not None and dependency_binding is not None
    assert root_binding.package is root
    assert dependency_binding.package is dependency
    assert root_binding.requirements.occurrences[0].key.subject == "Root"
    assert dependency_binding.requirements.occurrences[0].key.subject == "Dependency"
    root_declaration = root.catalog.root_package.manifest.capability_requirements
    dependency_declaration = (
        dependency.catalog.root_package.manifest.capability_requirements
    )
    assert root_declaration is not None and dependency_declaration is not None
    assert root_binding.requirements.identity is root_declaration.identity
    assert dependency_binding.requirements.identity is dependency_declaration.identity
    with pytest.raises(TypeError, match="exact loaded package"):
        _package_capability_requirement_binding(object())  # type: ignore[arg-type]


def test_schema_v1_root_and_dependency_bindings_are_both_undeclared(
    tmp_path: Path,
) -> None:
    dependency_digest = _write_package(
        tmp_path,
        "legacy/dep",
        schema_version=1,
        name="dep",
    )
    root_digest = _write_package(
        tmp_path,
        "legacy/root",
        schema_version=1,
        dependencies=(("example", "dep", "1.0.0", dependency_digest, "../dep"),),
    )
    root = _load_root(tmp_path, "legacy/root", root_digest)
    result = _build_package_load_plan(root)
    assert result.ok and type(result.plan) is PackageLoadPlan
    dependency = result.plan.entries[0].package
    assert type(dependency) is LoadedDependencyPackage
    assert _package_capability_requirement_binding(root) is None
    assert _package_capability_requirement_binding(dependency) is None


def test_requirement_only_manifest_change_changes_existing_loaded_digest(
    tmp_path: Path,
) -> None:
    first_digest = _write_package(
        tmp_path,
        "one",
        declaration=_declaration(_entry("logical_type", subject="Int")),
    )
    second_digest = _write_package(
        tmp_path,
        "two",
        declaration=_declaration(_entry("logical_type", subject="Text")),
    )
    first = _load_root(tmp_path, "one", first_digest)
    second = _load_root(tmp_path, "two", second_digest)

    assert first.content_digest == first_digest
    assert second.content_digest == second_digest
    assert first.content_digest != second.content_digest
    assert not hasattr(
        first.catalog.root_package.manifest.capability_requirements,
        "content_digest",
    )


def test_adapter_and_packaging_preserve_slice10_non_scope() -> None:
    source_path = Path(package_requirements.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    function_names = {
        node.name for node in tree.body if isinstance(node, ast.FunctionDef)
    }
    forbidden_imports = (
        "config",
        "capability_checking",
        "capability_matrix",
        "capability_inspection",
        "capability_providers",
        "extension_catalog",
        "_project_explain",
        "cli",
        "package_inspection",
    )

    assert function_names == {"_package_capability_requirement_binding"}
    assert not any(
        forbidden in module
        for module in imported_modules
        for forbidden in forbidden_imports
    )
    assert "tomllib" not in imported_modules
    assert "pathlib" not in imported_modules
    assert "open(" not in source
    assert tuple(
        inspect.signature(_package_capability_requirement_binding).parameters
    ) == ("package",)
    assert "capability_requirements" not in {
        field.name for field in fields(PackageInspectionPackage)
    }
    for public_name in (
        "PackageManifestCapabilityRequirements",
        "_package_capability_requirement_binding",
    ):
        assert not hasattr(pietto, public_name)
        assert not hasattr(project_package, public_name)

    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/package_capability_requirements.py"' in smoke
    assert "import pietto._project.package_capability_requirements" in smoke


def _normalize(manifest: bytes) -> PackageManifestNormalizationResult:
    return _normalize_package_manifest(
        ProjectRootPackageActivation(".", "example", "root", "1.0.0", "a" * 64),
        manifest,
    )


def _messages(result: PackageManifestNormalizationResult) -> tuple[str, ...]:
    return tuple(error.message for error in result.errors)


def _write_package(
    project: Path,
    package_path: str,
    *,
    schema_version: int = 2,
    name: str = "root",
    declaration: str = "",
    dependencies: tuple[tuple[str, str, str, str, str], ...] = (),
) -> str:
    package_root = project / package_path
    package_root.mkdir(parents=True)
    manifest = _manifest(
        schema_version=schema_version,
        name=name,
        declaration=declaration,
        dependencies=dependencies,
    )
    (package_root / "pietto-package.toml").write_bytes(manifest)
    (package_root / "main.pietto").write_bytes(SOURCE)
    return _compute_package_content_sha256(manifest, (("main.pietto", SOURCE),))


def _load_root(
    project: Path,
    package_path: str,
    digest: str,
) -> LoadedRootPackage:
    pinned_root = _pin_project_root(project)
    assert type(pinned_root) is ProjectPinnedRoot
    located = _locate_root_package(
        pinned_root,
        ProjectRootPackageActivation(
            package_path,
            "example",
            "root",
            "1.0.0",
            digest,
        ),
    )
    assert located.ok and type(located.located_root) is LocatedRootPackage
    loaded = _load_root_package(located.located_root)
    assert loaded.ok and type(loaded.loaded_package) is LoadedRootPackage
    return loaded.loaded_package
