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
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
    "grammar/Pietto.g4": (
        "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
    ),
    "scripts/validate.py": (
        "567c9ea1836c39d4e2037012e2b6e7795ceb3a9f54e9e3f7d951ae39155a5987"
    ),
    "scripts/check_generated.py": (
        "b126059cd0aebe9535fceb9b0a1b1c09ee1ba22af13f70d276d7e013c49c60e7"
    ),
    "scripts/check_goldens.py": (
        "23e271e0138e6b7ac189e27f33c557e04300301adff8f49747999e0c4b50c2e9"
    ),
    "scripts/package_smoke.py": (
        "aa6ab2ddf8ed8e889e8d75de224467565b7e6034cf068b44d602807fdd554924"
    ),
}

GROUP_HASHES = {
    "frontend": "cd28ccecc82f9d3f0bfa85fe886490e81d7260e9fe61919a4913ff8d6b21c52f",
    "semantic": "b90c0b4f78f54754802c43f50ff8e04c5f84c69e1571826559cccd64e4a702a4",
    "ir": "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    "sql": "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    "generated": "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4",
    "cli": "30e6e4cedfe91b4e52a5cad3e13b302a8617476c2a48dd92361e5fa5d6183019",
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

    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
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
