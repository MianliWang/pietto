from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, fields
from pathlib import Path

import pytest

import pietto
import pietto._project as project_package
import pietto._project.project_capability_environment as environment_builder
from pietto._project.capability_availability import (
    CompilerCapabilityProfileAvailabilityLedger,
    DeclaredCapabilityProfileAvailabilityReady,
    ProjectCapabilityProfileAvailabilityLedger,
)
from pietto._project.config import load_project_config
from pietto._project.extension_catalog_availability import (
    DeclaredExtensionCatalogAvailability,
    ExtensionCatalogAvailabilityOwner,
)
from pietto._project.model import (
    ProjectCapabilityEnvironmentConfig,
    ProjectCapabilityProfileDeclaration,
    ProjectCapabilityProfileFactDeclaration,
    ProjectCapabilityTargetSelection,
    ProjectConfig,
    ProjectDiscoveryErrorKind,
    ProjectRootPackageActivation,
    ProjectSourceConfig,
)
from pietto._project.module_carrier import ProjectCompilationMode
from pietto._project.project_capability_environment import (
    ProjectCapabilityEnvironmentAuthority,
    ProjectCapabilityEnvironmentBuildResult,
    ProjectEvaluatedCapabilityTarget,
    _build_project_capability_environment,
)
from pietto._project.source_selection import select_project_sources
from pietto.semantic.capability_composition import (
    CapabilityProfileCompositionSuccess,
)
from pietto.semantic.capability_facts import (
    CapabilityDispositionKind,
    CapabilityDomain,
    CapabilityEvidenceSource,
    CapabilityKey,
    CapabilitySupport,
)
from pietto.semantic.capability_profiles import (
    CapabilityProfileIdentity,
    CapabilityProfileKind,
    CapabilityProfileReference,
    CapabilityProfileSchemaVersion,
    CapabilityProfileTarget,
    CapabilityProfileTargetKind,
)
from pietto.semantic.extension_catalog import ExtensionCatalogTarget
from pietto.semantic.extension_catalog_pg_trgm import (
    PG_TRGM_V16_POSTGRESQL18_CATALOG,
)
from pietto.semantic.extension_catalog_pgvector import (
    PGVECTOR_V086_POSTGRESQL18_CATALOG,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
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


def _package_table() -> str:
    return """[package]
path = "."
namespace = "example"
name = "root"
version = "1.0.0"
sha256 = "pin"
"""


def _fact(
    domain: str,
    *,
    support: str = "supported",
    subject: str | None = None,
    operation: str | None = None,
    operands: tuple[str, ...] = (),
    context: str | None = None,
    dialect: str | None = None,
    extension: str | None = None,
) -> str:
    lines = [
        "[[capability_environment.profiles.facts]]",
        f'support = "{support}"',
        f'domain = "{domain}"',
    ]
    if subject is not None:
        lines.append(f'subject = "{subject}"')
    if operation is not None:
        lines.append(f'operation = "{operation}"')
    lines.append("operands = [" + ", ".join(f'"{value}"' for value in operands) + "]")
    if context is not None:
        lines.append(f'context = "{context}"')
    if dialect is not None:
        lines.append(f'dialect = "{dialect}"')
    if extension is not None:
        lines.append(f'extension = "{extension}"')
    return "\n".join(lines)


def _profile(
    name: str,
    *,
    namespace: str = "profiles",
    release: str = "r1",
    kind: str = "base",
    database_family: str = "PostgreSQL",
    database_release: str = "18",
    extension_identity: str = "vector",
    extension_release: str = "0.8.6",
    base_namespace: str = "profiles",
    base_name: str = "base",
    base_release: str = "r1",
    facts: tuple[str, ...] = (),
    extra: tuple[str, ...] = (),
) -> str:
    lines = [
        "[[capability_environment.profiles]]",
        f'namespace = "{namespace}"',
        f'name = "{name}"',
        f'release = "{release}"',
        f'kind = "{kind}"',
        f'database_family = "{database_family}"',
        f'database_release = "{database_release}"',
    ]
    if kind == "overlay":
        lines.extend(
            (
                f'extension_identity = "{extension_identity}"',
                f'extension_release = "{extension_release}"',
                f'base_namespace = "{base_namespace}"',
                f'base_name = "{base_name}"',
                f'base_release = "{base_release}"',
            )
        )
    lines.extend(extra)
    for fact in facts:
        lines.extend(("", fact))
    return "\n".join(lines)


def _target(
    base_name: str = "base",
    *,
    database_family: str = "PostgreSQL",
    database_release: str = "18",
    base_namespace: str = "profiles",
    base_release: str = "r1",
    overlays: tuple[tuple[str, str, str], ...] = (),
) -> str:
    lines = [
        "[[capability_environment.targets]]",
        f'database_family = "{database_family}"',
        f'database_release = "{database_release}"',
        f'base_profile_namespace = "{base_namespace}"',
        f'base_profile_name = "{base_name}"',
        f'base_profile_release = "{base_release}"',
    ]
    for namespace, name, release in overlays:
        lines.extend(
            (
                "",
                "[[capability_environment.targets.overlays]]",
                f'namespace = "{namespace}"',
                f'name = "{name}"',
                f'release = "{release}"',
            )
        )
    return "\n".join(lines)


def _schema4(
    *sections: str, environment_header: str = "[capability_environment]"
) -> str:
    return "\n".join(
        (
            "schema_version = 4",
            "",
            _package_table().rstrip(),
            "",
            environment_header,
            *(part for section in sections for part in ("", section)),
            "",
        )
    )


def _load(tmp_path: Path, text: str, name: str = "project"):
    root = tmp_path / name
    root.mkdir()
    (root / "pietto.toml").write_text(text, encoding="utf-8")
    return root, load_project_config(root)


def _build(tmp_path: Path, text: str, name: str = "project"):
    root, loaded = _load(tmp_path, text, name)
    assert loaded.ok and loaded.config is not None and loaded.root is not None
    return (
        root,
        loaded,
        _build_project_capability_environment(
            loaded.root,
            loaded.config,
        ),
    )


def test_project_model_carriers_and_schema_tagged_union_are_exact() -> None:
    identity = CapabilityProfileIdentity("profiles", "base")
    reference = CapabilityProfileReference(identity, "r1")
    key = CapabilityKey(CapabilityDomain.LOGICAL_TYPE, subject="Int")
    fact = ProjectCapabilityProfileFactDeclaration(0, CapabilitySupport.SUPPORTED, key)
    target = CapabilityProfileTarget(
        CapabilityProfileTargetKind.DATABASE,
        "PostgreSQL",
        "18",
    )
    profile = ProjectCapabilityProfileDeclaration(
        0,
        reference,
        CapabilityProfileKind.BASE,
        target,
        None,
        (fact,),
    )
    selection = ProjectCapabilityTargetSelection(
        0,
        "PostgreSQL",
        "18",
        reference,
        (),
    )
    environment = ProjectCapabilityEnvironmentConfig((profile,), (selection,))
    activation = ProjectRootPackageActivation(".", "example", "root", "1.0.0", "pin")
    source = ProjectSourceConfig(("*.pietto",), ())

    assert tuple(
        field.name for field in fields(ProjectCapabilityProfileFactDeclaration)
    ) == (
        "position",
        "support",
        "key",
    )
    assert tuple(
        field.name for field in fields(ProjectCapabilityProfileDeclaration)
    ) == (
        "position",
        "reference",
        "kind",
        "target",
        "base",
        "facts",
    )
    assert tuple(field.name for field in fields(ProjectCapabilityTargetSelection)) == (
        "position",
        "database_family",
        "database_release",
        "base_profile",
        "overlay_profiles",
    )
    assert tuple(
        field.name for field in fields(ProjectCapabilityEnvironmentConfig)
    ) == (
        "profiles",
        "targets",
    )
    assert tuple(field.name for field in fields(ProjectConfig)) == (
        "schema_version",
        "sources",
        "compilation_mode",
        "root_package",
        "capability_environment",
    )
    assert ProjectConfig(1, source).capability_environment is None
    assert (
        ProjectConfig(
            2,
            source,
            ProjectCompilationMode.EXPLICIT_MODULES,
        ).capability_environment
        is None
    )
    assert (
        ProjectConfig(
            3,
            None,
            ProjectCompilationMode.PACKAGE_ROOT,
            activation,
        ).capability_environment
        is None
    )
    schema4 = ProjectConfig(
        4,
        None,
        ProjectCompilationMode.PACKAGE_ROOT,
        activation,
        environment,
    )
    assert schema4.capability_environment is environment
    for value in (fact, profile, selection, environment, schema4):
        assert hasattr(type(value), "__slots__")
        assert not hasattr(value, "__dict__")
        assert isinstance(hash(value), int)
    with pytest.raises(FrozenInstanceError):
        selection.position = 1  # pyright: ignore[reportAttributeAccessIssue]
    with pytest.raises(ValueError):
        ProjectCapabilityTargetSelection(False, "PostgreSQL", "18", reference, ())
    with pytest.raises(ValueError):
        ProjectConfig(
            3,
            None,
            ProjectCompilationMode.PACKAGE_ROOT,
            activation,
            environment,
        )
    with pytest.raises(
        ValueError,
        match="Schema-v3 project configuration requires only a root package activation",
    ):
        ProjectConfig(3, None, ProjectCompilationMode.PACKAGE_ROOT)
    with pytest.raises(ValueError):
        ProjectConfig(4, None, ProjectCompilationMode.PACKAGE_ROOT, activation)


def test_project_model_semantic_import_policy_is_exact_and_data_only() -> None:
    model_path = REPO_ROOT / "src/pietto/_project/model.py"
    tree = ast.parse(model_path.read_text(encoding="utf-8"), filename=str(model_path))
    semantic_imports: dict[str, list[tuple[str, str | None]]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or not (node.module or "").startswith(
            "pietto.semantic"
        ):
            continue
        assert node.level == 0
        semantic_imports.setdefault(node.module or "", []).extend(
            (alias.name, alias.asname) for alias in node.names
        )
    assert {module: tuple(names) for module, names in semantic_imports.items()} == {
        "pietto.semantic.capability_facts": (
            ("CapabilityKey", None),
            ("CapabilitySupport", None),
        ),
        "pietto.semantic.capability_profiles": (
            ("CapabilityProfileKind", None),
            ("CapabilityProfileReference", None),
            ("CapabilityProfileTarget", None),
        ),
    }
    assert not any(
        alias.name == "pietto.semantic" or alias.name.startswith("pietto.semantic.")
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    )
    assert not any(
        isinstance(node, ast.ImportFrom)
        and node.module == "pietto"
        and any(alias.name == "semantic" for alias in node.names)
        for node in tree.body
    )

    model_symbols = (
        {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
        | {node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)}
        | {
            node.asname or node.name.rsplit(".", 1)[-1]
            for node in ast.walk(tree)
            if isinstance(node, ast.alias)
        }
        | {
            node.name
            for node in ast.walk(tree)
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        }
    )
    forbidden_symbols = {
        "analyze",
        "semantic_api",
        "lookup_capability",
        "compose_capability_profiles",
        "check_package_capability_requirements",
        "build_package_capability_checking_matrix",
        "build_capability_inspection_fact_set",
        "select_extension_catalog",
        "ExtensionSignatureProviderContext",
        "ExtensionSignatureProviderAuthority",
        "PackageCapabilityRequirementBinding",
        "PackageCapabilityCheckingMatrix",
        "CapabilityInspectionFactSet",
        "ProjectExplainPayload",
        "ProjectExplainEnvelope",
        "StaticCapabilityProfile",
        "CapabilityProfileBaseOccurrence",
        "CapabilityProfileFactOccurrence",
        "CapabilityFact",
        "CapabilityEvidence",
    }
    assert forbidden_symbols.isdisjoint(model_symbols)
    imported_modules = {
        alias.name.split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".", 1)[0]
        for node in tree.body
        if isinstance(node, ast.ImportFrom)
    }
    assert {"os", "pathlib", "socket", "subprocess", "urllib"}.isdisjoint(
        imported_modules
    )
    assert not any(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "open"
        for node in ast.walk(tree)
    )


def test_schema_v4_requires_exact_environment_and_preserves_schema_one_to_three(
    tmp_path: Path,
) -> None:
    source_text = '[sources]\ninclude = ["*.pietto"]\n'
    for schema_version, mode in (
        (1, ProjectCompilationMode.LEGACY_FLAT),
        (2, ProjectCompilationMode.EXPLICIT_MODULES),
    ):
        _, result = _load(
            tmp_path,
            f"schema_version = {schema_version}\n\n{source_text}",
            f"schema-{schema_version}",
        )
        assert result.ok and result.config is not None
        assert result.config.compilation_mode is mode
        assert result.config.capability_environment is None

    _, schema3 = _load(
        tmp_path,
        "schema_version = 3\n\n" + _package_table(),
        "schema-3",
    )
    _, schema4 = _load(tmp_path, _schema4(), "schema-4")
    assert schema3.ok and schema3.config is not None
    assert schema4.ok and schema4.config is not None
    assert schema3.config.root_package == schema4.config.root_package
    assert schema3.config.capability_environment is None
    assert schema4.config.capability_environment == ProjectCapabilityEnvironmentConfig(
        (), ()
    )

    _, missing = _load(
        tmp_path,
        "schema_version = 4\n\n" + _package_table(),
        "missing-environment",
    )
    assert not missing.ok
    assert "requires an exact [capability_environment]" in missing.errors[0].message
    _, schema3_environment = _load(
        tmp_path,
        "schema_version = 3\n\n" + _package_table() + "\n[capability_environment]\n",
        "schema3-environment",
    )
    assert not schema3_environment.ok
    assert schema3_environment.errors[0].message.endswith(
        "unsupported top-level key: capability_environment."
    )
    _, sources = _load(
        tmp_path,
        _schema4() + '\n[sources]\ninclude = ["*.pietto"]\n',
        "schema4-sources",
    )
    assert not sources.ok
    assert sources.errors[0].message.endswith("unsupported top-level key: sources.")


@pytest.mark.parametrize(
    "environment",
    (
        "capability_environment = {}\n\n" + _package_table(),
        _package_table() + '\n["capability_environment"]\n',
        _package_table() + "\ncapability_environment.profiles = []\n",
        _package_table() + "\n[owner.capability_environment]\n",
    ),
)
def test_schema_v4_rejects_inline_quoted_dotted_or_nested_environment(
    tmp_path: Path,
    environment: str,
) -> None:
    _, result = _load(
        tmp_path,
        "schema_version = 4\n\n" + environment,
        "alternate",
    )

    assert not result.ok and result.config is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


@pytest.mark.parametrize(
    "section",
    (
        'profiles = [{ namespace = "p", name = "b", release = "r", '
        'kind = "base", database_family = "PostgreSQL", database_release = "18" }]',
        '[capability_environment.profiles]\nnamespace = "p"',
        '[[capability_environment."profiles"]]\nnamespace = "p"',
        _profile("base", extra=("facts = []",)),
        _profile("base")
        + '\n[capability_environment.profiles.facts]\nsupport = "supported"',
        'targets = [{ database_family = "PostgreSQL" }]',
        '[capability_environment.targets]\ndatabase_family = "PostgreSQL"',
        '[[capability_environment."targets"]]\ndatabase_family = "PostgreSQL"',
        _target() + "\noverlays = []",
        _target()
        + '\n[capability_environment.targets.overlays]\nnamespace = "profiles"',
    ),
)
def test_all_new_toml_structures_require_exact_table_or_aot_source(
    tmp_path: Path,
    section: str,
) -> None:
    _, result = _load(
        tmp_path,
        _schema4(section),
        "source-proof",
    )

    assert not result.ok and result.config is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_base_overlay_profiles_preserve_exact_identity_order_and_zero_facts(
    tmp_path: Path,
) -> None:
    document = _schema4(
        _profile("Base 雪", namespace="Exact.NS", release="not-semver"),
        _profile(
            "Overlay",
            namespace="Exact.NS",
            release=" Release ",
            kind="overlay",
            base_namespace="Exact.NS",
            base_name="Base 雪",
            base_release="not-semver",
        ),
    )
    _, result = _load(tmp_path, document)

    assert result.ok and result.config is not None
    environment = result.config.capability_environment
    assert environment is not None
    assert tuple(profile.position for profile in environment.profiles) == (0, 1)
    base, overlay = environment.profiles
    assert base.reference == CapabilityProfileReference(
        CapabilityProfileIdentity("Exact.NS", "Base 雪"),
        "not-semver",
    )
    assert overlay.reference.release == " Release "
    assert base.kind is CapabilityProfileKind.BASE and base.base is None
    assert overlay.kind is CapabilityProfileKind.OVERLAY
    assert overlay.base == base.reference
    assert base.facts == overlay.facts == ()


@pytest.mark.parametrize(
    "profile",
    (
        _profile("bad", kind="unknown"),
        _profile("base", extra=('extension_identity = "vector"',)),
        _profile("overlay", kind="overlay", base_name=""),
        _profile("overlay", kind="overlay").replace('\nbase_release = "r1"', ""),
    ),
)
def test_invalid_profile_kinds_and_base_overlay_shapes_fail_closed(
    tmp_path: Path,
    profile: str,
) -> None:
    _, result = _load(tmp_path, _schema4(profile), "bad-profile")

    assert not result.ok
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA


def test_malformed_target_declaration_fails_closed(tmp_path: Path) -> None:
    malformed = """[[capability_environment.targets]]
database_family = "PostgreSQL"
database_release = "18"
base_profile_namespace = "profiles"
base_profile_name = "base"
"""
    _, result = _load(tmp_path, _schema4(malformed), "malformed-target")

    assert not result.ok and result.config is None
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    assert "base_profile_release" in result.errors[0].message


def test_profile_facts_become_exact_project_evidence_without_provider_copy(
    tmp_path: Path,
) -> None:
    facts = (
        _fact("logical_type", subject=" Int "),
        _fact(
            "scalar_function",
            operation="coalesce",
            operands=("Text", "Text"),
            context=" expression ",
        ),
        _fact("aggregate", operation="sum", operands=("Decimal",)),
        _fact("window_function", operation="row_number"),
        _fact(
            "extension_signature",
            operation="distance",
            operands=("vector", "vector"),
            dialect="PostgreSQL",
            extension="vector",
        ),
        _fact(
            "logical_type",
            support="explicitly_unsupported",
            subject=" Int ",
        ),
    )
    _, loaded, built = _build(tmp_path, _schema4(_profile("base", facts=facts)))

    assert built.ok and type(built.environment) is ProjectCapabilityEnvironmentAuthority
    profile = built.environment.project_profile_availability.occurrences[0].profile
    assert profile.schema_version is CapabilityProfileSchemaVersion.PROFILE_V1
    assert tuple(item.position for item in profile.capability_occurrences) == tuple(
        range(len(facts))
    )
    assert tuple(
        item.fact.key.domain.value for item in profile.capability_occurrences
    ) == (
        "logical_type",
        "scalar_function",
        "aggregate",
        "window_function",
        "extension_signature",
        "logical_type",
    )
    assert profile.capability_occurrences[0].fact.key.subject == " Int "
    assert profile.capability_occurrences[1].fact.key.operands == ("Text", "Text")
    assert tuple(item.fact.support for item in profile.capability_occurrences[-2:]) == (
        CapabilitySupport.SUPPORTED,
        CapabilitySupport.EXPLICITLY_UNSUPPORTED,
    )
    for position, occurrence in enumerate(profile.capability_occurrences):
        fact = occurrence.fact
        assert fact.disposition.kind is CapabilityDispositionKind.NONE
        assert len(fact.evidence) == 1
        evidence = fact.evidence[0]
        assert evidence.source is CapabilityEvidenceSource.PROJECT
        assert evidence.source_path == "pietto.toml"
        assert evidence.source_reference == (
            f"capability_environment.profiles[0].facts[{position}]"
        )
        assert evidence.backend is evidence.reason is None
    extension_evidence = profile.capability_occurrences[4].fact.evidence[0]
    assert extension_evidence.dialect == "PostgreSQL"
    assert extension_evidence.extension == "vector"
    assert loaded.config is built.environment.config
    assert tuple(item.value for item in CapabilityDomain) == DOMAIN_VALUES


@pytest.mark.parametrize(
    "fact",
    (
        _fact("unknown", subject="Int"),
        _fact("logical_type", support="unknown", subject="Int"),
        "[[capability_environment.profiles.facts]]\n"
        'support = "supported"\ndomain = "logical_type"\noperands = []',
        _fact("logical_type", subject="Int", operands=(" ",)),
        _fact(
            "extension_signature",
            operation="distance",
            extension="vector",
        ),
    ),
)
def test_malformed_profile_facts_fail_closed(tmp_path: Path, fact: str) -> None:
    _, result = _load(
        tmp_path,
        _schema4(_profile("base", facts=(fact,))),
        "bad-fact",
    )

    assert not result.ok
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    assert result.errors[0].path == "pietto.toml"


def test_same_support_key_duplicate_rejects_but_opposite_support_is_valid(
    tmp_path: Path,
) -> None:
    exact = _fact("logical_type", subject="Int")
    _, duplicate = _load(
        tmp_path,
        _schema4(_profile("base", facts=(exact, exact))),
        "duplicate-fact",
    )
    assert not duplicate.ok
    assert "duplicates support and CapabilityKey" in duplicate.errors[0].message

    _, _, opposite = _build(
        tmp_path,
        _schema4(
            _profile(
                "base",
                facts=(
                    exact,
                    _fact(
                        "logical_type",
                        support="explicitly_unsupported",
                        subject="Int",
                    ),
                ),
            )
        ),
        "opposite-fact",
    )
    assert opposite.ok and opposite.environment is not None
    facts = opposite.environment.profile_availability.profiles[0].capability_occurrences
    assert facts[0].fact.key == facts[1].fact.key
    assert facts[0].fact.support is not facts[1].fact.support


def test_ordered_targets_overlays_and_distinct_same_database_selections(
    tmp_path: Path,
) -> None:
    profiles = (
        _profile("base"),
        _profile("vector", kind="overlay"),
        _profile(
            "trgm",
            kind="overlay",
            extension_identity="pg_trgm",
            extension_release="1.6",
        ),
    )
    selections = (
        _target(overlays=(("profiles", "vector", "r1"),)),
        _target(overlays=(("profiles", "trgm", "r1"), ("profiles", "vector", "r1"))),
    )
    _, loaded, built = _build(tmp_path, _schema4(*profiles, *selections))

    assert built.ok and built.environment is not None
    assert tuple(target.position for target in built.environment.targets) == (0, 1)
    assert tuple(
        profile.profile.identity.name
        for profile in built.environment.targets[1].overlays
    ) == ("trgm", "vector")
    assert tuple(
        profile.profile.identity.name
        for profile in built.environment.targets[1].composition.dependency_order
    ) == ("base", "trgm", "vector")
    assert loaded.config is not None
    assert loaded.config.capability_environment is not None
    config_targets = loaded.config.capability_environment.targets
    assert config_targets[0] != config_targets[1]

    reordered = _schema4(
        *profiles,
        _target(overlays=(("profiles", "vector", "r1"), ("profiles", "trgm", "r1"))),
    )
    _, reordered_loaded = _load(tmp_path, reordered, "reordered")
    assert reordered_loaded.ok and reordered_loaded.config is not None
    assert reordered_loaded.config.capability_environment is not None
    assert (
        reordered_loaded.config.capability_environment.targets[0] != config_targets[1]
    )


@pytest.mark.parametrize(
    ("profiles", "targets", "message"),
    (
        ((_profile("base"),), (_target("missing"),), "base profile is unresolved"),
        (
            (_profile("base"), _profile("overlay", kind="overlay")),
            (_target("overlay"),),
            "non-BASE",
        ),
        (
            (_profile("base"),),
            (_target(overlays=(("profiles", "base", "r1"),)),),
            "non-OVERLAY",
        ),
        ((_profile("base"),), (_target(database_family="MySQL"),), "family"),
        ((_profile("base"),), (_target(database_release="17"),), "release"),
        (
            (_profile("base"), _profile("vector", kind="overlay")),
            (
                _target(
                    overlays=(
                        ("profiles", "vector", "r1"),
                        ("profiles", "vector", "r1"),
                    )
                ),
            ),
            "duplicates overlays",
        ),
        (
            (
                _profile("base"),
                _profile("vector-a", kind="overlay"),
                _profile("vector-b", kind="overlay", extension_release="0.9.0"),
            ),
            (
                _target(
                    overlays=(
                        ("profiles", "vector-a", "r1"),
                        ("profiles", "vector-b", "r1"),
                    )
                ),
            ),
            "duplicates extension identity",
        ),
        (
            (_profile("base"),),
            (_target(), _target()),
            "duplicates exact selected target",
        ),
    ),
)
def test_target_resolution_kind_agreement_and_duplicate_failures_are_exact(
    tmp_path: Path,
    profiles: tuple[str, ...],
    targets: tuple[str, ...],
    message: str,
) -> None:
    _, _, result = _build(
        tmp_path,
        _schema4(*profiles, *targets),
        "target-error",
    )

    assert not result.ok and result.environment is None
    assert message in result.errors[0].message
    assert result.errors[0].kind is ProjectDiscoveryErrorKind.CONFIG_SCHEMA
    assert result.errors[0].path == "pietto.toml"


def test_duplicate_profile_and_composition_blockers_fail_closed(tmp_path: Path) -> None:
    duplicate_profiles = _schema4(_profile("base"), _profile("base"))
    _, _, duplicate = _build(tmp_path, duplicate_profiles, "duplicate-profile")
    assert not duplicate.ok
    assert "duplicates exact reference" in duplicate.errors[0].message

    unresolved_chain = _schema4(
        _profile("base"),
        _profile("overlay", kind="overlay", base_name="missing"),
        _target(overlays=(("profiles", "overlay", "r1"),)),
    )
    _, _, unresolved = _build(tmp_path, unresolved_chain, "unresolved-chain")
    assert not unresolved.ok
    assert "profile composition blocked" in unresolved.errors[0].message
    assert "unresolved_base" in unresolved.errors[0].message

    cycle = _schema4(
        _profile("base"),
        _profile("one", kind="overlay", base_name="two"),
        _profile(
            "two",
            kind="overlay",
            extension_identity="pg_trgm",
            extension_release="1.6",
            base_name="one",
        ),
        _target(overlays=(("profiles", "one", "r1"), ("profiles", "two", "r1"))),
    )
    _, _, blocked = _build(tmp_path, cycle, "cycle")
    assert not blocked.ok
    assert "cycle" in blocked.errors[0].message


def test_overlay_chain_reuses_existing_composition_dependency_order(
    tmp_path: Path,
) -> None:
    document = _schema4(
        _profile("base"),
        _profile("one", kind="overlay"),
        _profile(
            "two",
            kind="overlay",
            extension_identity="pg_trgm",
            extension_release="1.6",
            base_name="one",
        ),
        _target(overlays=(("profiles", "two", "r1"), ("profiles", "one", "r1"))),
    )
    _, _, result = _build(tmp_path, document)

    assert result.ok and result.environment is not None
    target = result.environment.targets[0]
    assert type(target.composition) is CapabilityProfileCompositionSuccess
    assert tuple(
        profile.profile.identity.name for profile in target.composition.dependency_order
    ) == ("base", "one", "two")
    assert tuple(profile.profile.identity.name for profile in target.overlays) == (
        "two",
        "one",
    )


def test_profile_and_catalog_availability_are_exact_and_never_select(
    tmp_path: Path,
) -> None:
    _, loaded, result = _build(
        tmp_path,
        _schema4(_profile("base"), _target()),
    )

    assert result.ok and result.environment is not None
    environment = result.environment
    assert tuple(field.name for field in fields(ProjectEvaluatedCapabilityTarget)) == (
        "position",
        "database_family",
        "database_release",
        "base_profile",
        "overlays",
        "composition",
    )
    assert tuple(
        field.name for field in fields(ProjectCapabilityEnvironmentAuthority)
    ) == (
        "project",
        "config",
        "compiler_profile_availability",
        "project_profile_availability",
        "profile_availability",
        "targets",
        "extension_catalog_availability",
    )
    assert tuple(
        field.name for field in fields(ProjectCapabilityEnvironmentBuildResult)
    ) == ("environment", "errors")
    assert type(environment.compiler_profile_availability) is (
        CompilerCapabilityProfileAvailabilityLedger
    )
    assert environment.compiler_profile_availability.occurrences == ()
    assert type(environment.project_profile_availability) is (
        ProjectCapabilityProfileAvailabilityLedger
    )
    assert tuple(
        occurrence.owner
        for occurrence in environment.project_profile_availability.occurrences
    ) == (loaded.root,)
    assert tuple(
        occurrence.position
        for occurrence in environment.project_profile_availability.occurrences
    ) == (0,)
    assert type(environment.profile_availability) is (
        DeclaredCapabilityProfileAvailabilityReady
    )
    assert environment.profile_availability.profiles[0] is (
        environment.project_profile_availability.occurrences[0].profile
    )

    catalogs = environment.extension_catalog_availability
    assert type(catalogs) is DeclaredExtensionCatalogAvailability
    assert tuple(declaration.position for declaration in catalogs.declarations) == (
        0,
        1,
    )
    assert tuple(declaration.owner for declaration in catalogs.declarations) == (
        ExtensionCatalogAvailabilityOwner.COMPILER,
        ExtensionCatalogAvailabilityOwner.COMPILER,
    )
    assert tuple(declaration.project for declaration in catalogs.declarations) == (
        None,
        None,
    )
    assert tuple(declaration.catalog for declaration in catalogs.declarations) == (
        PGVECTOR_V086_POSTGRESQL18_CATALOG,
        PG_TRGM_V16_POSTGRESQL18_CATALOG,
    )
    assert catalogs.declarations[0].catalog is PGVECTOR_V086_POSTGRESQL18_CATALOG
    assert catalogs.declarations[1].catalog is PG_TRGM_V16_POSTGRESQL18_CATALOG
    assert tuple(declaration.target for declaration in catalogs.declarations) == (
        ExtensionCatalogTarget("PostgreSQL", "18", "vector", "0.8.6"),
        ExtensionCatalogTarget("PostgreSQL", "18", "pg_trgm", "1.6"),
    )
    assert tuple(
        declaration.content_sha256 for declaration in catalogs.declarations
    ) == (
        PGVECTOR_V086_POSTGRESQL18_CATALOG.content_sha256,
        PG_TRGM_V16_POSTGRESQL18_CATALOG.content_sha256,
    )


def test_explicit_empty_environment_has_zero_targets_and_no_default_profile(
    tmp_path: Path,
) -> None:
    _, _, result = _build(tmp_path, _schema4())

    assert result.ok and result.environment is not None
    assert result.environment.targets == ()
    assert result.environment.compiler_profile_availability.occurrences == ()
    assert result.environment.project_profile_availability.occurrences == ()
    assert result.environment.profile_availability.profiles == ()
    assert len(result.environment.extension_catalog_availability.declarations) == 2


def test_schema_v4_source_selection_message_is_distinct_and_early(
    tmp_path: Path,
) -> None:
    root, loaded = _load(tmp_path, _schema4())
    selected = select_project_sources(root, loaded)

    assert selected.inputs == selected.modules == ()
    assert selected.errors[0].message == (
        "Schema-v4 capability environment does not use project source selection."
    )


def test_builder_is_private_pure_and_keeps_slice12_owners_out() -> None:
    source_path = Path(environment_builder.__file__)
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
    for forbidden in (
        "package_capability_requirements",
        "capability_checking",
        "capability_matrix",
        "capability_inspection",
        "extension_signature_provider",
        "_project_explain",
        "cli",
    ):
        assert not any(forbidden in module for module in imported_modules)
    for forbidden_name in (
        "PackageCapabilityRequirementBinding",
        "PackageCapabilityCheckingMatrix",
        "CapabilityInspectionFactSet",
        "ExtensionCatalogSelectionResult",
        "ExtensionSignatureProviderContext",
        "ProjectExplainPayload",
        "ProjectExplainEnvelope",
        "select_extension_catalog",
    ):
        assert forbidden_name not in source
    assert "tomllib" not in imported_modules
    assert "pathlib" not in imported_modules
    assert "rglob(" not in source and "glob(" not in source and "open(" not in source
    for forbidden_runtime in (
        "create extension",
        "pg_extension",
        "server_version",
        "psycopg",
        "asyncpg",
        "ltree",
        "postgis",
    ):
        assert forbidden_runtime not in source.lower()
    assert function_names == {
        "_build_project_capability_environment",
        "_materialize_project_profile",
        "_target_agreement_error",
        "_composition_error",
        "_failed",
        "_result",
    }
    assert environment_builder.__all__ == ()
    for name in (
        "ProjectCapabilityEnvironmentAuthority",
        "_build_project_capability_environment",
    ):
        assert not hasattr(pietto, name)
        assert not hasattr(project_package, name)
    smoke = (REPO_ROOT / "scripts/package_smoke.py").read_text(encoding="utf-8")
    assert 'f"{prefix}/_project/project_capability_environment.py"' in smoke
    assert "import pietto._project.project_capability_environment" in smoke
