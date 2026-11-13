from __future__ import annotations

import ast
import inspect
from pathlib import Path
import sys

import pytest

from _pietto_repo_facts import REPOSITORY_FACTS

import pietto
import pietto._project as project_package
import pietto._project.capability_checking as checking
import pietto._project.capability_inspection as inspection
import pietto._project.capability_matrix as matrix
import pietto._project.package_manifest as package_manifest
import pietto.semantic as semantic_package
import pietto.semantic.capability_aggregates as aggregates
import pietto.semantic.capability_contexts as contexts
import pietto.semantic.capability_inventory as inventory
import pietto.semantic.capability_providers as providers
import pietto.semantic.capability_signatures as signatures
import pietto.semantic.capability_windows as windows
from pietto.semantic.capability_facts import CapabilityFact


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(path: Path) -> str:
    return REPOSITORY_FACTS.text(path)


def _provider_families() -> tuple[tuple[CapabilityFact, ...], ...]:
    return (
        inventory._CAPABILITY_FACTS,
        signatures._CAPABILITY_SIGNATURE_FACTS,
        contexts._CAPABILITY_CONTEXT_FACTS,
        aggregates._AGGREGATE_CAPABILITY_FACTS,
        windows._WINDOW_CAPABILITY_FACTS,
    )


def check_private_catalog_foundation() -> None:
    source_root = REPO_ROOT / "src/pietto"
    catalog_path = source_root / "semantic/extension_catalog.py"
    pg_trgm_catalog_path = source_root / "semantic/extension_catalog_pg_trgm.py"
    pgvector_catalog_path = source_root / "semantic/extension_catalog_pgvector.py"
    catalog_pure_path = source_root / "semantic/extension_catalog_pure_boundary.py"
    availability_path = source_root / "_project/extension_catalog_availability.py"
    inspection_path = source_root / "_project/extension_catalog_inspection.py"
    inspection_pure_path = (
        source_root / "_project/extension_catalog_inspection_pure_boundary.py"
    )
    project_explain_catalog_evidence_path = (
        source_root / "_project_explain/extension_catalog_evidence_projection.py"
    )
    project_explain_composition_path = source_root / "_project_explain/composition.py"
    project_explain_json_path = source_root / "_project_explain/json_v1.py"
    project_explain_runtime_path = source_root / "_project_explain/runtime_builder.py"
    project_explain_text_path = source_root / "_project_explain/text.py"
    capability_facts_path = source_root / "semantic/capability_facts.py"
    capability_pure_path = source_root / "_project/capability_pure_boundary.py"
    project_environment_path = (
        source_root / "_project/project_capability_environment.py"
    )
    package_manifest_path = source_root / "_project/package_manifest.py"
    package_selectors_path = (
        source_root / "_project/package_extension_signature_selectors.py"
    )
    provider_path = source_root / "_project/extension_signature_provider.py"
    selector_path = source_root / "semantic/extension_signature_requirements.py"
    catalog_paths = {
        catalog_path,
        pg_trgm_catalog_path,
        pgvector_catalog_path,
        catalog_pure_path,
        availability_path,
        inspection_path,
        inspection_pure_path,
        project_explain_catalog_evidence_path,
        project_explain_composition_path,
        project_explain_json_path,
        project_explain_runtime_path,
        project_explain_text_path,
        capability_facts_path,
        capability_pure_path,
        project_environment_path,
        package_manifest_path,
        package_selectors_path,
        provider_path,
        selector_path,
    }
    # Namespace is immutable during this invocation; every later assertion
    # enumerates again, including its actual injected path view.
    python_paths = tuple(sorted(source_root.rglob("*.py")))
    extension_catalog_modules = tuple(
        sorted(
            path.relative_to(REPO_ROOT).as_posix()
            for path in python_paths
            if "extension" in path.stem
            and ("catalog" in path.stem or "signature" in path.stem)
        )
    )
    assert extension_catalog_modules == (
        "src/pietto/_project/extension_catalog_availability.py",
        "src/pietto/_project/extension_catalog_inspection.py",
        "src/pietto/_project/extension_catalog_inspection_pure_boundary.py",
        "src/pietto/_project/extension_signature_provider.py",
        "src/pietto/_project/package_extension_signature_selectors.py",
        "src/pietto/_project_explain/extension_catalog_evidence_projection.py",
        "src/pietto/semantic/extension_catalog.py",
        "src/pietto/semantic/extension_catalog_pg_trgm.py",
        "src/pietto/semantic/extension_catalog_pgvector.py",
        "src/pietto/semantic/extension_catalog_pure_boundary.py",
        "src/pietto/semantic/extension_signature_requirements.py",
    )

    facts = tuple(fact for family in _provider_families() for fact in family)
    named_extensions = {"pgvector", "pg_trgm", "PostGIS", "TimescaleDB"}
    assert not any(fact.key.extension in named_extensions for fact in facts)
    assert not any(
        evidence.extension in named_extensions
        for fact in facts
        for evidence in fact.evidence
    )

    # Read-only observation vocabulary does not permit database operations.
    portable_observation_paths = {
        source_root / "_project/project_sql_plan_portable.py",
        source_root / "_project/project_sql_plan_portable_schema.py",
    }
    production_source = tuple(
        (path, REPOSITORY_FACTS.lowercase(_read(path)))
        for path in python_paths
        if path not in catalog_paths
    )
    for forbidden in (
        "create extension",
        "pg_extension",
        "server_version",
        "psycopg",
        "asyncpg",
        "extension_catalog",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        excluded_paths = set()
        if forbidden == "extension_catalog":
            excluded_paths = portable_observation_paths
        if forbidden in {"psycopg", "server_version"}:
            # S03 explicitly owns PG execution, with no other exception.
            execution_path = (
                REPO_ROOT / "src/pietto/_project/project_execution_postgres.py"
            )
            excluded_paths = {execution_path}
        if forbidden == "psycopg":
            # Public composition identifies a caught dependency by its module
            # root; it neither imports nor opens the driver.  Keep that one
            # exact literal in its one classifier, without widening the
            # execution reader reserve to other public or private owners.
            public_execution_path = source_root / "_project/project_public_execution.py"
            public_execution_text = _read(public_execution_path)
            assert public_execution_text.count("psycopg") == 1
            classifier = [
                node
                for node in ast.walk(ast.parse(public_execution_text))
                if isinstance(node, ast.FunctionDef) and node.name == "driver_error"
            ]
            assert len(classifier) == 1
            assert (
                sum(
                    isinstance(node, ast.Constant) and node.value == "psycopg"
                    for node in ast.walk(classifier[0])
                )
                == 1
            )
            excluded_paths.add(public_execution_path)
        if forbidden == "server_version":
            # S06 source admission reads the selected version in this exact
            # read-only context query. A second/comment/injected occurrence is
            # still forbidden, including the retained source-owner negative.
            admission_path = source_root / "_project/project_execution_source.py"
            admission_text = _read(admission_path)
            assert admission_text.count("server_version") == 1
            context_query = "SELECT current_setting('server_version_num'),current_setting('transaction_isolation'),current_setting('transaction_read_only'),current_setting('client_encoding')"
            admitted = [
                node
                for node in ast.walk(ast.parse(admission_text))
                if isinstance(node, ast.FunctionDef)
                and node.name == "admit_postgres_sources"
            ]
            assert len(admitted) == 1
            assert (
                sum(
                    isinstance(node, ast.Constant) and node.value == context_query
                    for node in ast.walk(admitted[0])
                )
                == 1
            )
            excluded_paths.add(admission_path)
        if forbidden == "server_version":
            # S09's exact ADBC native context query; no namespace-wide escape.
            adbc_path = (
                source_root / "_project/project_execution_postgres_adbc_native.py"
            )
            adbc_text = _read(adbc_path)
            assert adbc_text.count("server_version") == 1
            assignments = [
                node
                for node in ast.walk(ast.parse(adbc_text))
                if isinstance(node, ast.Assign)
                and any(
                    isinstance(t, ast.Name) and t.id == "CONTEXT_SQL"
                    for t in node.targets
                )
            ]
            assert len(assignments) == 1
            assert isinstance(assignments[0].value, ast.Constant)
            assert isinstance(assignments[0].value.value, str)
            assert (
                "current_setting('server_version_num')::integer"
                in assignments[0].value.value
            )
            excluded_paths.add(adbc_path)
        # Joining files with '\n' cannot create these newline-free needles
        # across a boundary. Keep substring/lower/comment semantics.
        assert "\n" not in forbidden
        violations = tuple(
            path
            for path, text in production_source
            if path not in excluded_paths and forbidden in text
        )
        assert not violations, (forbidden, violations)
    for path in portable_observation_paths:
        identifiers = set()
        for node in ast.walk(ast.parse(_read(path))):
            if isinstance(node, ast.Name):
                identifiers.add(node.id)
            elif isinstance(node, ast.Attribute):
                identifiers.add(node.attr)
            elif isinstance(node, ast.alias):
                identifiers.add(node.name.rsplit(".", 1)[-1])
        assert identifiers.isdisjoint(
            {
                "construct_extension_catalog",
                "select_extension_catalog",
                "extension_signature_provider_authority",
                "canonical_capability_provider_inputs",
            }
        )
    catalog_source = _read(catalog_path).lower()
    for forbidden in (
        "capabilityfact",
        "canonical_capability_provider_inputs",
        "database connection",
        "installation",
        "create extension",
        "pgvector",
        "pg_trgm",
        "postgis",
        "timescaledb",
    ):
        assert forbidden not in catalog_source
    manifest_source = inspect.getsource(package_manifest)
    assert "select_extension_catalog(" not in manifest_source
    assert "ExtensionCatalogSelectionResult" not in manifest_source

    for module in (pietto, semantic_package, project_package):
        assert not hasattr(module, "ExtensionCatalog")
        assert not hasattr(module, "PostgreSQLExtensionCatalog")
        assert not hasattr(module, "ExtensionCatalogMetadata")
        assert not hasattr(module, "ExtensionCatalogTarget")
        assert not hasattr(module, "ExtensionCatalogTypeReference")
        assert not hasattr(module, "PostgreSQLCallableIdentity")
        assert not hasattr(module, "ExtensionCatalogEntryEvidence")
        assert not hasattr(module, "ExtensionScalarFunctionCatalogEntry")
    assert "extension_catalog" not in inspect.getsource(providers)
    for source in (
        inspect.getsource(checking),
        inspect.getsource(matrix),
        inspect.getsource(inspection),
    ):
        assert "server installation" not in source.lower()
        assert "database connection" not in source.lower()


def check_execution_permission(monkeypatch, owner: str, forbidden: str) -> None:
    check_private_catalog_foundation()
    path = REPO_ROOT / "src/pietto/_project" / owner
    original_read = _read

    def injected_read(candidate: Path) -> str:
        source = original_read(candidate)
        return source + "\n" + forbidden if candidate == path else source

    monkeypatch.setattr(sys.modules[__name__], "_read", injected_read)
    with pytest.raises(AssertionError):
        check_private_catalog_foundation()
