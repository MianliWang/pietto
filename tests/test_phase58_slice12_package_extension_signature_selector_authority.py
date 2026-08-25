from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import pietto
import pietto._project as project_package
import pietto._project.package_extension_signature_selectors as package_selectors
from pietto._project.capability_availability import PackageCapabilityRequirementBinding
from pietto._project.model import ProjectRootPackageActivation
from pietto._project.package_capability_requirements import (
    _package_capability_requirement_binding,
)
from pietto._project.package_extension_signature_selectors import (
    _package_extension_signature_requirement_selectors,
)
from pietto._project.package_inspection import PackageInspectionPackage
from pietto._project.package_loader import (
    LoadedRootPackage,
    _compute_package_content_sha256,
    _load_root_package,
)
from pietto._project.package_locator import LocatedRootPackage, _locate_root_package
from pietto._project.package_manifest import (
    PackageManifest,
    PackageManifestCapabilityRequirements,
    PackageManifestExtensionSignatureSelectorOccurrence,
    _normalize_package_manifest,
)
from pietto._project.path_trust import ProjectPinnedRoot, _pin_project_root
from pietto.semantic.capability_facts import CapabilityDomain, CapabilityKey
from pietto.semantic.extension_catalog import (
    ExtensionCatalogEntryFamily,
    ExtensionCatalogLookupScope,
    ExtensionCatalogTypeReference,
    ExtensionCatalogTypeReferenceKind,
    PostgreSQLCallableIdentity,
    PostgreSQLCastIdentity,
    PostgreSQLOperatorArity,
    PostgreSQLOperatorIdentity,
)
from pietto.semantic.capability_profiles import CapabilityRequirementCollectionIdentity
from pietto.semantic.extension_signature_requirements import (
    ExtensionSignatureRequirementSelector,
    ExtensionSignatureRequirementSelectors,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE = b"shape Row:\n    id: Int\n"


def _requirement(
    domain: str = "extension_signature",
    *,
    operation: str = "distance",
    dialect: str | None = "postgresql",
    extension: str | None = "vector",
) -> str:
    lines = [
        "[[capability_requirements.entries]]",
        f'domain = "{domain}"',
        f'operation = "{operation}"',
        'operands = ["left", "right"]',
    ]
    if dialect is not None:
        lines.append(f'dialect = "{dialect}"')
    if extension is not None:
        lines.append(f'extension = "{extension}"')
    return "\n".join(lines)


def _type(kind: str, physical_name: str) -> tuple[str, str]:
    return kind, physical_name


def _selector(
    position: int,
    family: str,
    *,
    physical_name: str = "vector",
    sql_name: str = "distance",
    arity: str = "binary",
    input_types: tuple[tuple[str, str], ...] = (),
    operand_types: tuple[tuple[str, str], ...] = (),
    source_type: tuple[str, str] = ("postgres_builtin", "text"),
    target_type: tuple[str, str] = ("extension_native", "vector"),
) -> str:
    lines = [
        "[[extension_signature_selectors]]",
        f"requirement_position = {position}",
        f'family = "{family}"',
    ]
    if family == "native_type":
        lines.append(f'physical_name = "{physical_name}"')
    elif family in {"scalar_function", "aggregate"}:
        lines.append(f'sql_name = "{sql_name}"')
        for kind, name in input_types:
            lines.extend(
                (
                    "",
                    "[[extension_signature_selectors.input_types]]",
                    f'kind = "{kind}"',
                    f'physical_name = "{name}"',
                )
            )
    elif family == "operator":
        lines.extend((f'operator_name = "{sql_name}"', f'arity = "{arity}"'))
        for kind, name in operand_types:
            lines.extend(
                (
                    "",
                    "[[extension_signature_selectors.operand_types]]",
                    f'kind = "{kind}"',
                    f'physical_name = "{name}"',
                )
            )
    elif family == "cast":
        lines.extend(
            (
                "",
                "[extension_signature_selectors.source_type]",
                f'kind = "{source_type[0]}"',
                f'physical_name = "{source_type[1]}"',
                "",
                "[extension_signature_selectors.target_type]",
                f'kind = "{target_type[0]}"',
                f'physical_name = "{target_type[1]}"',
            )
        )
    return "\n".join(lines)


def _manifest(
    *,
    schema_version: int = 3,
    requirements: tuple[str, ...] | None = None,
    selectors: tuple[str, ...] = (),
) -> bytes:
    lines = [
        f"schema_version = {schema_version}",
        'namespace = "example"',
        'name = "root"',
        'version = "1.0.0"',
        "",
        "[[assets]]",
        'kind = "module_source"',
        'path = "main.pietto"',
    ]
    if requirements is not None:
        lines.extend(
            (
                "",
                "[capability_requirements]",
                'namespace = "requirements"',
                'name = "runtime"',
            )
        )
        for requirement in requirements:
            lines.extend(("", requirement))
    for selector in selectors:
        lines.extend(("", selector))
    return ("\n".join(lines) + "\n").encode()


def _normalize(manifest: bytes):
    return _normalize_package_manifest(
        ProjectRootPackageActivation(".", "example", "root", "1.0.0", "a" * 64),
        manifest,
    )


def _write_package(root: Path, name: str, manifest: bytes) -> tuple[Path, str]:
    package_root = root / name
    package_root.mkdir(parents=True)
    (package_root / "pietto-package.toml").write_bytes(manifest)
    (package_root / "main.pietto").write_bytes(SOURCE)
    return package_root, _compute_package_content_sha256(
        manifest,
        (("main.pietto", SOURCE),),
    )


def _load(root: Path, package_path: str, digest: str) -> LoadedRootPackage:
    pinned = _pin_project_root(root)
    assert type(pinned) is ProjectPinnedRoot
    located = _locate_root_package(
        pinned,
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


def test_manifest_model_and_schema_compatibility_are_exact() -> None:
    v1 = _normalize(_manifest(schema_version=1, requirements=None))
    v2 = _normalize(_manifest(schema_version=2, requirements=(_requirement(),)))
    v3 = _normalize(_manifest(schema_version=3, requirements=None))
    for result in (v1, v2, v3):
        assert result.ok and type(result.manifest) is PackageManifest
    v1_manifest = v1.manifest
    v2_manifest = v2.manifest
    v3_manifest = v3.manifest
    assert type(v1_manifest) is PackageManifest
    assert type(v2_manifest) is PackageManifest
    assert type(v3_manifest) is PackageManifest
    assert v1_manifest.capability_requirements is None
    assert v2_manifest.capability_requirements is not None
    assert v2_manifest.capability_requirements.extension_signature_selectors == ()
    assert v3_manifest.capability_requirements is None

    key = CapabilityKey(
        CapabilityDomain.EXTENSION_SIGNATURE,
        operation="distance",
        dialect="postgresql",
        extension="vector",
    )
    selector = ExtensionSignatureRequirementSelector(
        ExtensionCatalogLookupScope(
            ExtensionCatalogEntryFamily.NATIVE_TYPE,
            ExtensionCatalogTypeReference(
                ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE,
                physical_name="vector",
                extension_identity="vector",
            ),
        )
    )
    occurrence = PackageManifestExtensionSignatureSelectorOccurrence(0, selector)
    declaration = PackageManifestCapabilityRequirements(
        CapabilityRequirementCollectionIdentity("r", "n"),
        (key,),
        (occurrence,),
    )
    assert tuple(
        field.name
        for field in fields(PackageManifestExtensionSignatureSelectorOccurrence)
    ) == ("requirement_position", "selector")
    assert tuple(
        field.name for field in fields(PackageManifestCapabilityRequirements)
    ) == ("identity", "keys", "extension_signature_selectors")
    assert tuple(field.name for field in fields(CapabilityKey)) == (
        "domain",
        "subject",
        "operation",
        "operands",
        "context",
        "dialect",
        "extension",
    )
    assert declaration.extension_signature_selectors == (occurrence,)
    assert hasattr(type(occurrence), "__slots__") and not hasattr(
        occurrence, "__dict__"
    )
    with pytest.raises(FrozenInstanceError):
        occurrence.requirement_position = 1  # pyright: ignore[reportAttributeAccessIssue]


@pytest.mark.parametrize("schema_version", (1, 2))
def test_schema_one_and_two_reject_selector_sidecar(schema_version: int) -> None:
    result = _normalize(
        _manifest(
            schema_version=schema_version,
            requirements=(_requirement(),) if schema_version == 2 else None,
            selectors=(_selector(0, "native_type"),),
        )
    )

    assert not result.ok
    assert "unsupported top-level key: extension_signature_selectors" in (
        result.errors[0].message
    )


@pytest.mark.parametrize("replacement", ("true", "0", "4", '"3"', "3.0"))
def test_schema_version_accepts_only_exact_one_two_or_three(replacement: str) -> None:
    manifest = _manifest().replace(
        b"schema_version = 3",
        f"schema_version = {replacement}".encode(),
        1,
    )
    result = _normalize(manifest)

    assert not result.ok
    assert result.errors[0].message == (
        "Package manifest schema_version must be exact integer 1, 2, or 3."
    )


def test_schema_three_without_extension_requirements_requires_empty_selectors() -> None:
    no_requirements = _normalize(_manifest(requirements=None))
    non_extension = _normalize(
        _manifest(
            requirements=(
                _requirement(
                    "logical_type",
                    operation="Int",
                    dialect=None,
                    extension=None,
                ),
            )
        )
    )

    assert no_requirements.ok
    assert non_extension.ok and non_extension.manifest is not None
    declaration = non_extension.manifest.capability_requirements
    assert declaration is not None
    assert declaration.extension_signature_selectors == ()


def test_all_five_selector_families_and_physical_types_are_exact() -> None:
    requirements = tuple(
        _requirement(operation=f"semantic-{position}") for position in range(5)
    )
    selectors = (
        _selector(0, "native_type", physical_name="vector"),
        _selector(
            1,
            "scalar_function",
            sql_name="distance",
            input_types=(
                _type("extension_native", "vector"),
                _type("postgres_builtin", "float8"),
            ),
        ),
        _selector(2, "aggregate", sql_name="avg"),
        _selector(
            3,
            "operator",
            sql_name="<->",
            arity="binary",
            operand_types=(
                _type("extension_native", "vector"),
                _type("extension_native", "vector"),
            ),
        ),
        _selector(
            4,
            "cast",
            source_type=_type("postgres_builtin", "text"),
            target_type=_type("extension_native", "vector"),
        ),
    )
    result = _normalize(_manifest(requirements=requirements, selectors=selectors))

    assert result.ok and result.manifest is not None
    declaration = result.manifest.capability_requirements
    assert declaration is not None
    scopes = tuple(
        item.selector.scope for item in declaration.extension_signature_selectors
    )
    assert tuple(scope.family.value for scope in scopes) == (
        "native_type",
        "scalar_function",
        "aggregate",
        "operator",
        "cast",
    )
    native = scopes[0].identity
    assert type(native) is ExtensionCatalogTypeReference
    assert native.kind is ExtensionCatalogTypeReferenceKind.EXTENSION_NATIVE
    assert native.extension_identity == "vector"
    scalar = scopes[1].identity
    aggregate = scopes[2].identity
    assert type(scalar) is PostgreSQLCallableIdentity
    assert type(aggregate) is PostgreSQLCallableIdentity
    assert scalar.input_types[0].extension_identity == "vector"
    assert (
        scalar.input_types[1].kind is ExtensionCatalogTypeReferenceKind.POSTGRES_BUILTIN
    )
    assert aggregate.input_types == ()
    assert scopes[1] != scopes[2]
    operator = scopes[3].identity
    assert type(operator) is PostgreSQLOperatorIdentity
    assert operator.arity is PostgreSQLOperatorArity.BINARY
    assert len(operator.operand_types) == 2
    cast_identity = scopes[4].identity
    assert type(cast_identity) is PostgreSQLCastIdentity
    assert cast_identity.source_type.physical_name == "text"
    assert cast_identity.target_type.physical_name == "vector"


@pytest.mark.parametrize(
    ("requirements", "selectors"),
    (
        ((_requirement(),), ()),
        ((_requirement(),), (_selector(0, "native_type"), _selector(0, "native_type"))),
        (
            (_requirement("logical_type", dialect=None, extension=None),),
            (_selector(0, "native_type"),),
        ),
        (
            (_requirement(), _requirement()),
            (_selector(1, "native_type"), _selector(0, "native_type")),
        ),
        ((_requirement(),), (_selector(1, "native_type"),)),
    ),
)
def test_selector_coverage_missing_extra_duplicate_order_and_position_fail_closed(
    requirements: tuple[str, ...],
    selectors: tuple[str, ...],
) -> None:
    result = _normalize(_manifest(requirements=requirements, selectors=selectors))

    assert not result.ok
    assert any(error.kind.value == "config_schema" for error in result.errors)


@pytest.mark.parametrize(
    "selector",
    (
        _selector(
            0,
            "operator",
            arity="unary",
            operand_types=(
                _type("extension_native", "vector"),
                _type("extension_native", "vector"),
            ),
        ),
        _selector(0, "cast").replace(
            '\n[extension_signature_selectors.target_type]\nkind = "extension_native"\nphysical_name = "vector"',
            "",
        ),
        _selector(
            0,
            "scalar_function",
            input_types=(_type("pietto_logical", "Text"),),
        ),
        _selector(0, "native_type") + '\nextension_identity = "foreign"',
    ),
)
def test_invalid_physical_type_arity_cast_and_separate_owner_fail_closed(
    selector: str,
) -> None:
    result = _normalize(
        _manifest(requirements=(_requirement(),), selectors=(selector,))
    )
    assert not result.ok


@pytest.mark.parametrize(
    "requirement",
    (
        _requirement(dialect="PostgreSQL"),
        _requirement(extension=None),
    ),
)
def test_selector_binding_requires_exact_postgresql_extension_owner(
    requirement: str,
) -> None:
    result = _normalize(
        _manifest(
            requirements=(requirement,),
            selectors=(_selector(0, "native_type"),),
        )
    )
    assert not result.ok


def test_unary_operator_and_cast_direction_are_exact() -> None:
    forward = _normalize(
        _manifest(
            requirements=(_requirement(), _requirement(operation="cast")),
            selectors=(
                _selector(
                    0,
                    "operator",
                    sql_name="-",
                    arity="unary",
                    operand_types=(_type("extension_native", "vector"),),
                ),
                _selector(1, "cast"),
            ),
        )
    )
    reverse = _normalize(
        _manifest(
            requirements=(_requirement(operation="cast"),),
            selectors=(
                _selector(
                    0,
                    "cast",
                    source_type=_type("extension_native", "vector"),
                    target_type=_type("postgres_builtin", "text"),
                ),
            ),
        )
    )
    assert forward.ok and forward.manifest is not None
    assert reverse.ok and reverse.manifest is not None
    forward_declaration = forward.manifest.capability_requirements
    reverse_declaration = reverse.manifest.capability_requirements
    assert forward_declaration is not None and reverse_declaration is not None
    unary = forward_declaration.extension_signature_selectors[0].selector.scope.identity
    assert type(unary) is PostgreSQLOperatorIdentity
    assert unary.arity is PostgreSQLOperatorArity.UNARY
    assert len(unary.operand_types) == 1
    forward_cast = forward_declaration.extension_signature_selectors[
        1
    ].selector.scope.identity
    reverse_cast = reverse_declaration.extension_signature_selectors[
        0
    ].selector.scope.identity
    assert type(forward_cast) is type(reverse_cast) is PostgreSQLCastIdentity
    assert forward_cast != reverse_cast


@pytest.mark.parametrize(
    "selector",
    (
        "extension_signature_selectors = []",
        "[extension_signature_selectors]\nrequirement_position = 0",
        '[["extension_signature_selectors"]]\nrequirement_position = 0',
        _selector(0, "scalar_function") + "\ninput_types = []",
        _selector(0, "operator", operand_types=())
        + '\n[extension_signature_selectors.operand_types]\nkind = "extension_native"',
        _selector(0, "cast").replace(
            "[extension_signature_selectors.source_type]",
            "[[extension_signature_selectors.source_type]]",
        ),
    ),
)
def test_selector_and_nested_source_forms_are_exact(selector: str) -> None:
    result = _normalize(
        _manifest(requirements=(_requirement(),), selectors=(selector,))
    )
    assert not result.ok


def test_adapter_witnesses_v1_v2_and_v3_states(tmp_path: Path) -> None:
    manifests = {
        "v1": _manifest(schema_version=1, requirements=None),
        "v2": _manifest(schema_version=2, requirements=(_requirement(),)),
        "v3-empty": _manifest(
            requirements=(_requirement("logical_type", dialect=None, extension=None),)
        ),
        "v3-bound": _manifest(
            requirements=(_requirement(),),
            selectors=(_selector(0, "native_type"),),
        ),
    }
    loaded: dict[str, LoadedRootPackage] = {}
    for name, manifest in manifests.items():
        _, digest = _write_package(tmp_path, name, manifest)
        loaded[name] = _load(tmp_path, name, digest)

    v1_binding = _package_capability_requirement_binding(loaded["v1"])
    v2_binding = _package_capability_requirement_binding(loaded["v2"])
    empty_binding = _package_capability_requirement_binding(loaded["v3-empty"])
    bound_binding = _package_capability_requirement_binding(loaded["v3-bound"])
    assert v1_binding is None
    assert type(v2_binding) is PackageCapabilityRequirementBinding
    assert type(empty_binding) is PackageCapabilityRequirementBinding
    assert type(bound_binding) is PackageCapabilityRequirementBinding
    assert (
        _package_extension_signature_requirement_selectors(loaded["v1"], v1_binding)
        is None
    )
    assert (
        _package_extension_signature_requirement_selectors(loaded["v2"], v2_binding)
        is None
    )
    empty = _package_extension_signature_requirement_selectors(
        loaded["v3-empty"], empty_binding
    )
    bound = _package_extension_signature_requirement_selectors(
        loaded["v3-bound"], bound_binding
    )
    assert type(empty) is ExtensionSignatureRequirementSelectors
    assert empty.requirements is empty_binding.requirements
    assert empty.occurrences == ()
    assert type(bound) is ExtensionSignatureRequirementSelectors
    assert bound.requirements is bound_binding.requirements
    assert tuple(item.requirement_position for item in bound.occurrences) == (0,)
    with pytest.raises(ValueError, match="exact package ownership"):
        _package_extension_signature_requirement_selectors(
            loaded["v3-bound"],
            v2_binding,
        )


def test_semantic_and_physical_selector_identity_are_independent() -> None:
    first = _normalize(
        _manifest(
            requirements=(_requirement(operation="semantic-one"),),
            selectors=(_selector(0, "native_type", physical_name="vector"),),
        )
    )
    second = _normalize(
        _manifest(
            requirements=(_requirement(operation="semantic-two"),),
            selectors=(_selector(0, "native_type", physical_name="vector"),),
        )
    )
    third = _normalize(
        _manifest(
            requirements=(_requirement(operation="semantic-one"),),
            selectors=(_selector(0, "native_type", physical_name="halfvec"),),
        )
    )
    assert first.ok and second.ok and third.ok
    assert first.manifest is not None and second.manifest is not None
    assert third.manifest is not None
    first_declaration = first.manifest.capability_requirements
    second_declaration = second.manifest.capability_requirements
    third_declaration = third.manifest.capability_requirements
    assert first_declaration is not None and second_declaration is not None
    assert third_declaration is not None
    assert first_declaration.keys[0] != second_declaration.keys[0]
    assert (
        first_declaration.extension_signature_selectors[0].selector
        == second_declaration.extension_signature_selectors[0].selector
    )
    assert first_declaration.keys[0] == third_declaration.keys[0]
    assert (
        first_declaration.extension_signature_selectors[0].selector
        != third_declaration.extension_signature_selectors[0].selector
    )


def test_selector_only_manifest_change_changes_existing_package_digest() -> None:
    first = _manifest(
        requirements=(_requirement(),),
        selectors=(_selector(0, "native_type", physical_name="vector"),),
    )
    second = _manifest(
        requirements=(_requirement(),),
        selectors=(_selector(0, "native_type", physical_name="halfvec"),),
    )
    first_digest = _compute_package_content_sha256(first, (("main.pietto", SOURCE),))
    second_digest = _compute_package_content_sha256(second, (("main.pietto", SOURCE),))

    assert first_digest != second_digest


def test_adapter_is_private_pure_and_keeps_runtime_owners_out() -> None:
    source_path = Path(package_selectors.__file__)
    source = source_path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(source_path))
    imported_modules = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    for forbidden in (
        "extension_catalog_availability",
        "extension_signature_provider",
        "capability_checking",
        "capability_matrix",
        "capability_inspection",
        "_project_explain",
        "cli",
    ):
        assert not any(forbidden in module for module in imported_modules)
    for forbidden_name in (
        "select_extension_catalog",
        "ExtensionCatalogSelectionResult",
        "ExtensionSignatureProviderContext",
        "check_package_capability_requirements",
        "PackageCapabilityCheckingMatrix",
        "CapabilityInspectionFactSet",
        "ProjectExplainPayload",
    ):
        assert forbidden_name not in source
    assert "tomllib" not in imported_modules and "pathlib" not in imported_modules
    assert (
        "open(" not in source
        and "read_text(" not in source
        and "read_bytes(" not in source
    )
    assert package_selectors.__all__ == ()
    assert "extension_signature_selectors" not in {
        field.name for field in fields(PackageInspectionPackage)
    }
    for name in (
        "PackageManifestExtensionSignatureSelectorOccurrence",
        "_package_extension_signature_requirement_selectors",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/package_extension_signature_selectors.py"' in smoke
    assert "import pietto._project.package_extension_signature_selectors" in smoke
