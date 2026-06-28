from __future__ import annotations

import hashlib
import inspect
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pietto.cli_json as cli_json
import pietto.sql as sql_api
from pietto.parser_api import parse_source

REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = "docs/spec/order-limit-contract-v1.md"
PLAN_PATH = "docs/plan/phase-12-sql-feature-expansion-i.md"

FILE_HASHES = {
    "pyproject.toml": "021682ef880fe748f1655d4d70fcc549db4336ac39db2b29a835762ab1723d50",
    "uv.lock": "996f7bcb04c380c2b3855167d33ffbd462c902245e63bee6e626ab1789d65071",
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "d75052cfc4c5de426388cc9d8a34eef607e8023a5e1789f2e497979ea2dde9f6"
    ),
    ".github/workflows/ci.yml": (
        "c2ba73d04dab3331ca19577f2cf4250274671aa37ec4f84f293429e118b6c4c5"
    ),
    "scripts/validate.py": (
        "6a52494385d5c010101e2304b554ff76afcd9bb44d101783c43b205af688e6a4"
    ),
    "scripts/check_generated.py": (
        "b126059cd0aebe9535fceb9b0a1b1c09ee1ba22af13f70d276d7e013c49c60e7"
    ),
    "scripts/check_goldens.py": (
        "23e271e0138e6b7ac189e27f33c557e04300301adff8f49747999e0c4b50c2e9"
    ),
    "scripts/package_smoke.py": (
        "2cd2ae8ec3ad5fdd87fd85099def9796ea0dca38e6480bfedadfec5f70b49de4"
    ),
}

GROUP_HASHES = {
    "frontend": "06ff1d647427b4e937321ed525866059266ddc2bc292c050a458647365d95123",
    "semantic": "dfa4af8c0dd699431ac068f1ee007e3a744d9384fe1b602aa5ab682a1f42579b",
    "ir": "7438c72875751eeadf8b12b3aad1825499061f3f4e0dd73d8c1a339c614ae884",
    "sql": "67aeafa622d3147b08930cebcf18862322eec692d547d328b18966afa81f3530",
    "generated": "25bd5df39d46749ad59e2b805bd85cce52e708cdf56bda6ee365615c419e17d1",
    "cli": "bab5a160ac57ad45045836f2f4396e7383baf03c20bb8a18d51e9fd2476a716f",
}

GOLDENS_HASH = "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004"


def test_contract_exists_and_phase12_status_is_exact() -> None:
    contract = _read(CONTRACT_PATH)
    normalized_contract = " ".join(contract.split())
    plan = _read(PLAN_PATH)

    assert "# ORDER BY / LIMIT Contract Version 1" in contract
    assert (
        "Phase 12 is complete. Slice 3 static `LIMIT`, Slice 4 input-scope "
        "`ORDER BY`, and Slice 5 composition and presentation coverage are "
        "complete" in normalized_contract
    )
    assert "**Slice 1: Master Plan And Baseline Audit is complete.**" in plan
    assert "**Slice 2: ORDER BY / LIMIT Language Contract is complete.**" in plan
    assert "**Slice 3: LIMIT Vertical Slice is complete.**" in plan
    assert "**Slice 4: ORDER BY Vertical Slice is complete.**" in plan
    assert "**Slice 5: Composition, CLI/JSON And Goldens is complete.**" in plan
    assert "**Slice 6: Completion Audit And Documentation is complete.**" in plan


def test_limit_literal_range_and_diagnostic_contract_are_fixed() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "static ASCII decimal integer literal matching `[0-9]+`",
        "0 <= limit <= 9223372036854775807",
        "`limit 0` is valid",
        "`limit 9223372036854775807` is valid",
        "`limit 9223372036854775808` is invalid",
        "negative, decimal, string, identifier, and expression-valued limits",
        "PIE-S2307 error: Limit must be a static integer from 0 to 9223372036854775807",
        "severity: `error` in loose, checked, and strict modes",
        "span excludes the `limit` keyword, separating whitespace, and newline",
        "exactly one diagnostic",
    ):
        assert required in contract


def test_clause_order_and_order_by_source_contract_are_fixed() -> None:
    contract = _normalized(CONTRACT_PATH)
    clause_order = "from optional where select optional order by optional limit"

    assert clause_order in contract
    for required in (
        "`order by` must appear before `limit`",
        "`order by` uses Pietto's colon and indentation block syntax",
        "block must contain at least one sorting item",
        "Each sorting item occupies one source line",
        "expression [asc | desc]",
        "Direction is optional and defaults to `asc`",
        "every direction is emitted explicitly as `ASC` or `DESC`",
        "Sorting items preserve source order exactly",
    ):
        assert required in contract


def test_order_by_input_scope_and_projection_alias_exclusion_are_fixed() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "relation input row schema",
        "Projection aliases are not members of the `ORDER BY` name-resolution scope",
        "sorting name `created_at` resolves to the input field",
        "does not resolve to the projection alias",
        "no input field has that name, the existing unknown-field semantic "
        "diagnostic applies",
        "does not add output-schema lookup, alias fallback, ordinal lookup",
    ):
        assert required in contract


def test_ir_and_dual_backend_formatting_contract_are_fixed() -> None:
    contract = _read(CONTRACT_PATH)
    normalized = " ".join(contract.split())

    for required in (
        "RelationIR.order_by",
        "RelationIR.limit",
        "OrderItemIR",
        "LimitIR",
        "PostgreSQL and MySQL must be delivered together",
        "PostgreSQL uses its existing expression and double-quoted identifier renderer",
        "MySQL uses its existing expression and backtick identifier renderer",
        "one SQL artifact has no final newline",
        "existing SQL without these clauses remains byte-for-byte unchanged",
    ):
        assert required in normalized

    assert 'ORDER BY\n    "created_at" DESC,\n    "id" ASC\nLIMIT 100' in contract
    assert "ORDER BY\n    `created_at` DESC,\n    `id` ASC\nLIMIT 100" in contract


def test_cli_json_api_dependency_and_suffix_contracts_are_unchanged() -> None:
    contract = _normalized(CONTRACT_PATH)
    project = tomllib.loads(_read("pyproject.toml"))
    signature = inspect.signature(sql_api.emit_postgres_sql)

    for required in (
        "JSON schema version 1",
        "`emit_postgres_sql(ScriptIR) -> SqlResult` as the public PostgreSQL emitter",
        "`pietto.sql.mysql.emit_mysql_sql` as a private emitter",
        "absence of a generic public `emit_sql(...)`",
        "SQLGlot",
        "`.pietto` remains the only official source suffix",
        "`PIE-Pxxxx`, `PIE-Sxxxx`, `PIE-Ixxxx`, and `PIE-Bxxxx`",
    ):
        assert required in contract

    assert project["project"]["dependencies"] == ["antlr4-python3-runtime>=4.13.2"]
    assert project["project"]["version"] == "0.1.0"
    assert tuple(signature.parameters) == ("script_ir",)
    assert signature.return_annotation == "SqlResult"
    assert set(sql_api.__all__) == {
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    }
    assert not hasattr(sql_api, "emit_mysql_sql")
    assert not hasattr(sql_api, "emit_sql")
    assert cli_json._SCHEMA_VERSION == 1


def test_deferred_capabilities_are_explicit() -> None:
    contract = _normalized(CONTRACT_PATH)

    for required in (
        "projection-alias ordering",
        "ordinal ordering",
        "`NULLS FIRST` or `NULLS LAST`",
        "collation",
        "`OFFSET`",
        "`FETCH`",
        "expression-valued limits",
        "joins",
        "grouping",
        "aggregates",
        "windows",
        "CTEs",
        "subqueries",
        "DDL",
        "DML",
        "SQL execution",
        "database connections",
        "schema introspection",
        "project or multi-file mode",
        "`pietto.toml`",
        "watch mode",
        "LSP/editor support",
        "Web UI",
        "online playground",
        "JSON v2",
        "package version change",
    ):
        assert required in contract


def test_limit_and_order_by_are_implemented_while_ordinals_are_rejected() -> None:
    grammar = _read("grammar/Pietto.g4")

    assert "LIMIT: 'limit';" in grammar
    for token in (
        "ORDER: 'order';",
        "BY: 'by';",
        "ASC: 'asc';",
        "DESC: 'desc';",
    ):
        assert token in grammar

    limit_result = parse_source(
        "query projected:\n"
        "    from input_relation\n"
        "    select:\n"
        "        id\n"
        "    limit 10\n",
        path="phase12-slice4.pietto",
    )
    assert limit_result.diagnostics == ()
    assert limit_result.ast is not None

    order_result = parse_source(
        "query projected:\n"
        "    from input_relation\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        id\n",
        path="phase12-slice3.pietto",
    )
    assert order_result.diagnostics == ()
    assert order_result.ast is not None

    ordinal_result = parse_source(
        "query projected:\n"
        "    from input_relation\n"
        "    select:\n"
        "        id\n"
        "    order by:\n"
        "        1\n",
        path="phase12-slice4.pietto",
    )
    assert ordinal_result.ast is None
    assert [diagnostic.code for diagnostic in ordinal_result.diagnostics] == [
        "PIE-P1000"
    ]


def test_slice6_preserves_configuration_cli_and_golden_boundaries() -> None:
    for path, expected_hash in FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "frontend": (
            "src/pietto/__init__.py",
            "src/pietto/ast_nodes.py",
            "src/pietto/ast_builder.py",
            "src/pietto/errors.py",
            "src/pietto/indentation.py",
            "src/pietto/parser_api.py",
        ),
        "semantic": _module_paths("src/pietto/semantic"),
        "ir": _module_paths("src/pietto/ir"),
        "sql": _module_paths("src/pietto/sql"),
        "generated": tuple(
            path.relative_to(REPO_ROOT).as_posix()
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "cli": (
            "src/pietto/cli.py",
            "src/pietto/cli_json.py",
        ),
    }
    for name, paths in groups.items():
        assert _aggregate_sha256(paths) == GROUP_HASHES[name]

    assert (
        _aggregate_files(
            path
            for path in (REPO_ROOT / "tests/fixtures/golden").iterdir()
            if path.is_file()
        )
        == GOLDENS_HASH
    )


def test_repository_has_no_new_public_emitter_or_bare_diagnostic_codes() -> None:
    runtime_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted((REPO_ROOT / "src/pietto").rglob("*.py"))
        if "generated" not in path.parts
    )
    repository_text = _repository_text()

    assert "def emit_mysql_sql(" in runtime_text
    assert "def emit_sql(" not in runtime_text
    assert re.search(r"\." + "pie" + r"\b", repository_text) is None
    assert re.search(r"(?<!PIE-)\b[PSIB][0-9]{4}\b", repository_text) is None


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _module_paths(directory: str) -> tuple[str, ...]:
    root = REPO_ROOT / directory
    return tuple(
        path.relative_to(REPO_ROOT).as_posix() for path in sorted(root.glob("*.py"))
    )


def _aggregate_sha256(paths: tuple[str, ...]) -> str:
    digest = hashlib.sha256()
    for relative_path in sorted(paths):
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update((REPO_ROOT / relative_path).read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _repository_text() -> str:
    paths = [
        REPO_ROOT / "README.md",
        REPO_ROOT / "AGENTS.md",
        REPO_ROOT / "pyproject.toml",
        REPO_ROOT / "uv.lock",
        REPO_ROOT / CONTRACT_PATH,
        REPO_ROOT / PLAN_PATH,
    ]
    for directory in ("src", "tests", "docs", "examples", "grammar", ".github"):
        paths.extend(
            path
            for path in (REPO_ROOT / directory).rglob("*")
            if path.is_file()
            and "__pycache__" not in path.parts
            and path.suffix
            in {".py", ".md", ".json", ".sql", ".toml", ".lock", ".g4", ".yml"}
        )
    return "\n".join(path.read_text(encoding="utf-8") for path in sorted(set(paths)))
