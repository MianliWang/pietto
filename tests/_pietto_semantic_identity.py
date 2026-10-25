from __future__ import annotations

from pathlib import Path


import pietto._project.check as project_check
import pietto._project.module_package_neutral_identity as layering
from pietto._project.model import (
    ProjectParseCheckResult,
    ProjectSemanticResult,
    build_empty_project_semantic_result,
)
from pietto._project.module_carrier import ProjectModuleIdentity


REPO_ROOT = Path(__file__).resolve().parents[1]
SOURCE_REL = "src/pietto/_project/module_package_neutral_identity.py"
TEST_REL = "tests/_pietto_semantic_identity.py"


_SHAPE_PREFIX = (
    "shape Row:\n"
    "    id: Int\n"
    "    amount: Int\n"
    "    category: Text | None\n"
    'source rows: Row = postgres.table("rows")\n'
)


def _configured_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    (root / "pietto.toml").write_text(
        f'schema_version = {schema_version}\n\n[sources]\ninclude = ["*.pietto"]\n',
        encoding="utf-8",
    )
    for relative, source in sources.items():
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
    return root


def _semantic_project(
    root: Path,
    sources: dict[str, str],
    *,
    schema_version: int = 2,
) -> tuple[ProjectParseCheckResult, ProjectSemanticResult]:
    parse_result = project_check.check_project_parse_only(
        _configured_project(root, sources, schema_version=schema_version)
    )
    assert parse_result.ok
    return parse_result, build_empty_project_semantic_result(parse_result)


def _layered(
    semantic: ProjectSemanticResult,
) -> layering.ProjectModulePackageNeutralIdentityFactSet:
    facts = semantic.module_package_identity_facts
    assert facts is not None
    return facts


def _declaration(
    semantic: ProjectSemanticResult,
    module_path: str,
    declared_name: str,
) -> layering.ProjectLayeredDeclarationAsset:
    matches = tuple(
        asset
        for asset in _layered(semantic).declaration_assets
        if asset.identity.module_path == module_path
        and asset.identity.declared_name == declared_name
    )
    assert len(matches) == 1
    return matches[0]


def _module_asset(
    semantic: ProjectSemanticResult,
    module_path: str,
) -> layering.ProjectLayeredModuleAsset:
    matches = _layered(semantic).find_module(ProjectModuleIdentity(path=module_path))
    assert len(matches) == 1
    return matches[0]


def _build_layered(
    result: ProjectSemanticResult,
    **overrides: object,
) -> layering.ProjectModulePackageNeutralIdentityFactSet:
    parse_roots: dict[str, object] = {
        "selected_input_index": result.selected_input_index,
        "trusted_source_snapshots": result.trusted_source_snapshots,
        "modules": result.modules,
        "catalogs": result.module_catalogs,
        "attribution": result.module_attribution_facts,
        "semantic": result.module_semantic_facts,
    }
    parse_roots.update(overrides)
    return layering._build_project_module_package_neutral_identity_fact_set(
        parse_roots["selected_input_index"],  # pyright: ignore[reportArgumentType]
        parse_roots["trusted_source_snapshots"],  # pyright: ignore[reportArgumentType]
        parse_roots["modules"],  # pyright: ignore[reportArgumentType]
        parse_roots["catalogs"],  # pyright: ignore[reportArgumentType]
        parse_roots["attribution"],  # pyright: ignore[reportArgumentType]
        parse_roots["semantic"],  # pyright: ignore[reportArgumentType]
    )


def _query_module(body: str) -> str:
    return _SHAPE_PREFIX + "query result:\n    from rows\n" + body


def _cycle_sources() -> dict[str, str]:
    return {
        "a.pietto": (
            'from "b.pietto" import shape S\nexport shape T\nshape T:\n    id: Int\n'
        ),
        "b.pietto": (
            'from "a.pietto" import shape T\nexport shape S\nshape S:\n    id: Int\n'
        ),
    }
