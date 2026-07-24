from __future__ import annotations

import hashlib
import inspect
import re
import tomllib
from collections.abc import Iterable
from pathlib import Path

import pietto.cli_json as cli_json
import pietto.sql as sql_api

REPO_ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = "docs/spec/current-syntax-surface-audit-v1.md"
LANGUAGE_SPEC_PATH = "docs/spec/language-direction-v1.md"
PORTABILITY_SPEC_PATH = "docs/spec/safety-deferral-and-sql-portability-v1.md"
PLAN_PATH = "docs/plan/phase-16-language-direction-safety-mode.md"
STATUS_PATHS = (
    "README.md",
    "AGENTS.md",
    "docs/spec/pietto-v0.9.md",
)

LOCKED_FILE_HASHES = {
    SPEC_PATH: "580ebcfcc78102d902110d864eb80c7f1a57ffcb6b4b33e1160c9abd17ba07a6",
    LANGUAGE_SPEC_PATH: (
        "6fb738d3ec275f92762b83a2a9f469bcf66be204a7ac762ee5aa8e2780ea307c"
    ),
    PORTABILITY_SPEC_PATH: (
        "cc37df490ed1adf646883d166bc85055552e1a2bf664d65ff5e29c3978bc8570"
    ),
    PLAN_PATH: "adfb0d99075299049c790f465fab7453e0ed73b985e9cff19c6aeb38f94c7f5a",
    "grammar/Pietto.g4": (
        "1c394db1f72561022941e0e937899e2d340880de220ebfa85cf387b86573384e"
    ),
    "src/pietto/__init__.py": (
        "669ac67bb23a0c8179995e0e415d76c46210c12311e29cd89d2612b45b0a194d"
    ),
    "src/pietto/ast_nodes.py": (
        "b0c41070fca75c89534eba75cf2086f41721de740da9a3573d67411d366204f5"
    ),
    "src/pietto/ast_builder.py": (
        "201c74d6a27e57dfc7cd0f9693b388ebe7853b783173a3c4f7191a5f8026e70b"
    ),
    "src/pietto/parser_api.py": (
        "aa744c3ee334c8729917ae2aed2ee906874f927d47e99542d5accb8a98aa456b"
    ),
    "src/pietto/errors.py": (
        "7aa9622bde3eb07bb64bb5c932dc69e48d635e89790b26e8090b9309c5cf62f6"
    ),
    "src/pietto/cli.py": (
        "e9d90d40293db543c4b6c0da829e8b6a122fd2f8b29fcafdc23d4d54b1c42e09"
    ),
    "src/pietto/cli_json.py": (
        "ccee00529ee36b123f70d418105609dbb4906f2ccc1c1f5653527b1168fb6d91"
    ),
    "src/pietto/sql/__init__.py": (
        "e40bd3eee7f76bc68313adb8237a7a6c5d84286197261f70c827a4219c9e3418"
    ),
    "docs/spec/diagnostics.md": (
        "d70d62c76ddb25a8c2000a7cd1cb2f8071e90d3ed62fb6b8cf3b8c0655ff7c98"
    ),
    "Makefile": "dbd38c41e2af5275c379de0b88c92f3861efb90724c7de1a291e0aa007ce2db7",
}

LOCKED_GROUP_HASHES = {
    "generated": (
        8,
        "bc5be46411f947c4d591e81ce8dd8345140fd5e10276f2ff0055eccfc12babe4",
    ),
    "semantic": (
        32,
        "5797637326c467ecabd5e93c5f84982b35cecff140f43f1a21451d86b196bdd2",
    ),
    "ir": (
        5,
        "57097f43ba5e0ffa8d531b827b7029c9104b85ab3dc0657889cccd28caec5249",
    ),
    "sql": (
        10,
        "b18229fbda079d706416119002a70d091e7f5b79e0e4818a5b1292d9b88e898b",
    ),
    "examples": (
        10,
        "230369f90130d7c4b722b75ef2ec264d98e0d6f34ad3b1b5fd7d5fbf04d45a97",
    ),
    "fixtures": (
        68,
        "dbd457dd7e79f41d0e1740187818478941861cabf9ae9f3b06f908bdc81cd11c",
    ),
    "goldens": (
        37,
        "0e26a0b367a2ae849e5ec1e9a239be42765bea2c352242db5da930ab56b43004",
    ),
}


def test_slice3_spec_and_plan_status_are_exact() -> None:
    spec = _normalized(SPEC_PATH)
    plan = _normalized(PLAN_PATH)

    assert (REPO_ROOT / SPEC_PATH).is_file()
    assert "Phase 16 Slice 3 is complete as syntax-surface audit only" in spec
    assert (
        "Phase 16 Slice 3: Current Syntax Surface Audit is complete as "
        "syntax-surface audit only"
    ) in plan
    assert (
        "Phase 16 Slice 4: Phase 16 Completion Audit is complete as final audit "
        "and status work only"
    ) in plan
    assert (
        "Phase 16 Language Direction And Safety Mode is complete as design, "
        "specification, and audit work only"
    ) in plan
    assert SPEC_PATH in plan
    assert "The accepted syntax is unchanged by Phase 16" in spec


def test_spec_lists_the_current_accepted_syntax_surface() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "`mode strict`",
        "`type` declarations",
        "`enum` declarations",
        "Constraint",
        "Derive",
        "Shape",
        "Source",
        "Table",
        "Query",
        "One required `from` clause",
        "One optional `where` expression",
        "indentation-block `select` clause",
        "`alias = expression` inside `select` only",
        "indentation-block `order by` items",
        "Optional `limit` expression",
        "Top-level `relationship` with exactly two source-ordered `endpoint`",
        "Literals, dotted names and calls, parentheses, unary signs, arithmetic, "
        "comparisons, `like`, `between`, `is null`, `is not null`, `and`, and `or`",
    ):
        assert required in spec

    assert "typed SQL authoring DSL" in spec
    assert "documented mainstream SQL backend subsets" in spec
    assert "every accepted definition emits SQL" in spec


def test_source_connector_and_strict_mode_boundaries_are_exact() -> None:
    spec = _normalized(SPEC_PATH)
    grammar = _normalized("grammar/Pietto.g4")
    source_rule = re.search(r"sourceDefinition : (?P<body>.*?) ;", grammar)

    assert source_rule is not None
    assert source_rule.group("body") == (
        "SOURCE identifier (COLON identifier)? IS expression NEWLINE"
    )
    assert "ASSIGN" not in source_rule.group("body")
    assert (
        "current accepted typed source connector syntax remains "
        "`source name: Shape is connector`"
    ) in spec
    assert "`source name: Shape = connector` is not accepted syntax" in spec
    assert "remains deferred and speculative" in spec
    assert (
        "The existing header form `mode strict` remains compile-time checking" in spec
    )
    assert "It is not a safety mode, policy mode, permission mode" in spec


def test_grammar_surface_matches_the_documented_inventory() -> None:
    grammar = _normalized("grammar/Pietto.g4")

    for required in (
        "modeDecl : MODE (LOOSE | CHECKED | STRICT) NEWLINE ;",
        "definition : typeDefinition | enumDefinition | constraintDefinition | "
        "deriveDefinition | shapeDefinition | sourceDefinition | tableDefinition "
        "| queryDefinition ;",
        "relationshipBody : NEWLINE* relationshipEndpoint NEWLINE* "
        "relationshipEndpoint NEWLINE* ;",
        "tableBody : NEWLINE* fromClause NEWLINE* letClause? NEWLINE* "
        "whereClause? NEWLINE* groupByClause? NEWLINE* selectClause NEWLINE* "
        "satisfyingClause? NEWLINE* orderByClause? NEWLINE* limitClause? "
        "NEWLINE* ;",
        "letClause : LET COLON NEWLINE NEWLINE* INDENT letBody DEDENT ;",
        "letBody : NEWLINE* letBinding (letBinding | NEWLINE)* ;",
        "letBinding : identifier ASSIGN expression NEWLINE ;",
        "groupByClause : GROUP BY COLON NEWLINE NEWLINE* INDENT groupByBody DEDENT ;",
        "groupByItem : dottedName NEWLINE ;",
        "selectItem : identifier ASSIGN windowExpression | identifier ASSIGN "
        "expression NEWLINE | expression NEWLINE ;",
        "windowExpression : dottedName callSuffix windowSpec ;",
        "windowSpec : WINDOW COLON NEWLINE NEWLINE* INDENT windowSpecBody DEDENT ;",
        "windowSpecBody : NEWLINE* partitionByClause NEWLINE* orderByClause? "
        "NEWLINE* | NEWLINE* orderByClause NEWLINE* ;",
        "partitionByClause : PARTITION BY COLON NEWLINE NEWLINE* INDENT "
        "windowPartitionBody DEDENT ;",
        "windowPartitionItem : expression NEWLINE ;",
        "satisfyingClause : SATISFYING COLON NEWLINE NEWLINE* INDENT expression "
        "NEWLINE NEWLINE* DEDENT ;",
        "orderItem : expression (ASC | DESC)? NEWLINE ;",
        "limitClause : LIMIT expression NEWLINE ;",
        "comparisonOperator : EQ | NE | LT | LE | GT | GE | LIKE ;",
        "primaryExpression : literal | dottedName callSuffix? | LPAREN expression "
        "RPAREN ;",
        "literal : NUMBER | STRING | TRUE | FALSE | NULL ;",
    ):
        assert required in grammar


def test_relationship_metadata_and_speculative_syntax_remain_deferred() -> None:
    spec = _normalized(SPEC_PATH)
    grammar = _read("grammar/Pietto.g4")

    for required in (
        "Relationship metadata remains frozen as secondary read-only metadata",
        "does not provide or imply",
        "JOIN or JOIN lowering",
        "relationship composition",
        "endpoint-qualified lookup",
        "multi-input query behavior",
        "relation-role or endpoint-role enforcement",
        "SQL lowering",
        "permission, policy, authorization, privacy, or security model",
    ):
        assert required in spec

    for candidate in (
        "`exposure`",
        "`purpose`",
        "`for <purpose>`",
        "Rust-like `impl` or evidence",
        "Permission, authority, or capability-token forms",
        "JOIN forms",
        "Relationship composition forms",
        "Endpoint-qualified lookup forms",
        "Runtime, policy, privacy, or security forms",
        "A new safety/policy strict mode",
    ):
        assert candidate in spec

    for token_or_rule in (
        "EXPOSURE:",
        "PURPOSE:",
        "FOR:",
        "PERMISSION:",
        "AUTHORITY:",
        "CAPABILITY:",
        "IMPL:",
        "JOIN:",
        "exposureClause",
        "purposeClause",
        "permissionClause",
        "implEvidence",
        "joinClause",
        "endpointQualified",
    ):
        assert token_or_rule not in grammar


def test_deferred_examples_cannot_be_read_as_accepted_syntax() -> None:
    spec = _read(SPEC_PATH)
    normalized = " ".join(spec.split())

    assert "```pietto" not in spec
    assert "## Deferred And Unaccepted Syntax" in spec
    for required in (
        "`source name: Shape = connector` is not accepted syntax",
        "Future-only concept; not accepted syntax",
        "Future-only purpose-like sugar; not accepted syntax",
        "No concrete candidate in this table is a planned syntax design",
    ):
        assert required in normalized


def test_compiler_repository_and_fixture_surfaces_are_byte_locked() -> None:
    for path, expected_hash in LOCKED_FILE_HASHES.items():
        assert _sha256(REPO_ROOT / path) == expected_hash

    groups = {
        "generated": tuple(
            path
            for path in sorted((REPO_ROOT / "src/pietto/generated").iterdir())
            if path.is_file()
        ),
        "semantic": _python_files("src/pietto/semantic"),
        "ir": _python_files("src/pietto/ir"),
        "sql": _python_files("src/pietto/sql"),
        "examples": _all_files("examples"),
        "fixtures": _all_files("tests/fixtures"),
        "goldens": _all_files("tests/fixtures/golden"),
    }
    for name, paths in groups.items():
        expected_count, expected_hash = LOCKED_GROUP_HASHES[name]
        assert len(paths) == expected_count
        assert _aggregate_files(paths) == expected_hash


def test_public_sql_mysql_json_dependency_and_ci_boundaries_are_locked() -> None:
    project = tomllib.loads(_read("pyproject.toml"))
    sql_source = _read("src/pietto/sql/__init__.py")
    mysql_source = _read("src/pietto/sql/mysql.py")
    workflow = _read(".github/workflows/ci.yml")
    all_block = re.search(r"(?s)__all__ = \[(?P<body>.*?)\]", sql_source)

    assert all_block is not None
    assert tuple(re.findall(r'"([^"]+)"', all_block.group("body"))) == (
        "SqlArtifact",
        "SqlArtifactKind",
        "SqlResult",
        "emit_postgres_sql",
    )
    assert tuple(inspect.signature(sql_api.emit_postgres_sql).parameters) == (
        "script_ir",
    )
    assert "emit_mysql_sql" not in sql_source
    assert "def emit_mysql_sql(" in mysql_source
    assert "def emit_sql(" not in sql_source
    assert cli_json._SCHEMA_VERSION == 1
    assert project["project"]["version"] == "0.1.0"
    assert [
        dependency.split(">", 1)[0].split("=", 1)[0].split("<", 1)[0]
        for dependency in project["project"]["dependencies"]
    ] == ["antlr4-python3-runtime"]
    assert "sqlglot" not in _read("uv.lock").lower()
    assert re.search(r"(?m)^permissions:\n  contents: read$", workflow)


def test_status_and_diagnostic_boundaries_are_exact() -> None:
    for path in STATUS_PATHS:
        normalized = _normalized(path)
        assert "Phase 16 Slice 3" in normalized
        assert "syntax-surface audit only" in normalized
        assert "Phase 16 is complete" in normalized
        assert "Future work requires separate explicit authorization" in normalized
        assert SPEC_PATH in normalized
        assert PLAN_PATH in normalized

    docs = _read(SPEC_PATH) + _read(PLAN_PATH)
    assert re.findall(r"\bPIE-[PSIBR]\d{4}\b", docs) == []
    assert "introduces no diagnostic code and reserves no diagnostic code" in (
        _normalized(SPEC_PATH)
    )


def _read(path: str) -> str:
    return (REPO_ROOT / path).read_text(encoding="utf-8")


def _normalized(path: str) -> str:
    return " ".join(_read(path).split())


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _python_files(root: str) -> tuple[Path, ...]:
    return tuple(sorted((REPO_ROOT / root).glob("*.py")))


def _all_files(root: str) -> tuple[Path, ...]:
    return tuple(
        path for path in sorted((REPO_ROOT / root).rglob("*")) if path.is_file()
    )


def _runtime_text(root: str) -> str:
    return "\n".join(path.read_text(encoding="utf-8") for path in _python_files(root))


def _aggregate_files(paths: Iterable[Path]) -> str:
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative_path = path.relative_to(REPO_ROOT).as_posix()
        digest.update(relative_path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


_SLICE10_READER_MIGRATION_PATHS = (
    "docs/spec/phase53-partition-binding-multi-key-visibility-diagnostics-contract-v1.md",
    "src/pietto/semantic/window_partition_analysis.py",
    "tests/test_phase53_partition_binding_multi_key_visibility_diagnostics_contract.py",
)
