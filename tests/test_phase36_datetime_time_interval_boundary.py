from __future__ import annotations

import json
from pathlib import Path

from _static_audit_helpers import (
    git_diff_name_only as _git_diff_name_only,
    normalized_text as _normalized,
    read_text as _read,
)

import pietto.cli as cli
from pietto.ast_nodes import Expression, QueryDef, Script, TableDef
from pietto.errors import Severity
from pietto.parser_api import parse_source
from pietto.semantic import (
    SemanticResult,
    TypeKind,
    ValueTypeKind,
    analyze,
)

REPO_ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = REPO_ROOT / "docs/plan/phase-36-post-v02-core-type-system-expansion.md"
SPEC_PATH = REPO_ROOT / "docs/spec/datetime-time-interval-boundary-v1.md"

CATALOG_PATH = REPO_ROOT / "src/pietto/semantic/catalog.py"
SEMANTIC_MODEL_PATH = REPO_ROOT / "src/pietto/semantic/model.py"
IR_MODEL_PATH = REPO_ROOT / "src/pietto/ir/model.py"
METADATA_MODEL_PATH = REPO_ROOT / "src/pietto/_metadata/model.py"
METADATA_SERIALIZER_PATH = REPO_ROOT / "src/pietto/_metadata/serializer.py"
METADATA_TEXT_PATH = REPO_ROOT / "src/pietto/_metadata/text.py"
CLI_JSON_PATH = REPO_ROOT / "src/pietto/cli_json.py"

FORBIDDEN_DIFF_PATHS = (
    "grammar/Pietto.g4",
    "src/pietto/generated",
    "src/pietto/cli.py",
    "src/pietto/cli_json.py",
    "src/pietto/semantic",
    "src/pietto/ir",
    "src/pietto/sql",
    "src/pietto/_metadata",
    "tests/fixtures",
    "pyproject.toml",
    "uv.lock",
    ".github",
    "scripts",
    "examples",
)

TEMPORAL_CANDIDATES = ("DateTime", "Time", "Interval")


def _phase36_slice6_docs() -> str:
    return f"{_normalized(PLAN_PATH)} {_normalized(SPEC_PATH)}"


def test_slice6_selects_tests_only_option_b() -> None:
    combined = _phase36_slice6_docs()

    for required in (
        "Phase 36 Slice 6 selects Option B: tests-only hardening",
        "DateTime / Time / Interval Boundary",
        "without changing compiler behavior",
        "`Date` and `Timestamp` remain the existing current supported builtins",
        "`DateTime`, `Time`, and `Interval` remain unsupported/deferred",
        "`DateTime` is not an alias of `Timestamp`",
        "`Time` and `Interval` are not builtins",
        "semantic type resolution with existing diagnostic `PIE-S2002`",
        "Slice 6 keeps the broader 12-slice Phase 36 plan intact",
    ):
        assert required in combined, required


def test_datetime_time_interval_are_not_builtin_type_names() -> None:
    catalog = _read(CATALOG_PATH)
    combined = _phase36_slice6_docs()

    assert '"Date"' in catalog
    assert '"Timestamp"' in catalog
    for type_name in TEMPORAL_CANDIDATES:
        assert f'"{type_name}"' not in catalog
        assert f"`{type_name}`" in combined

    assert "`Date` and `Timestamp` are current builtins" in combined
    assert "`DateTime`, `Time`, and `Interval` are not in `BUILTIN_TYPE_NAMES`" in (
        combined
    )


def test_datetime_is_not_silently_treated_as_timestamp() -> None:
    result = analyze(_parse(_source("DateTime", "value")))
    relation = _relation(result)
    source_schema = next(iter(result.model.source_row_schemas.values()))
    projected = result.model.relation_row_schemas[relation].fields["value"]
    expression = _select_expression(relation, "value")

    assert "PIE-S2002" in _error_codes(result)
    assert source_schema.fields["value"].resolved_type.kind is TypeKind.UNKNOWN
    assert source_schema.fields["value"].resolved_type.name == "DateTime"
    assert projected.resolved_type.kind is TypeKind.UNKNOWN
    assert projected.resolved_type.name == "DateTime"
    assert projected.resolved_type.name != "Timestamp"
    assert result.model.expression_value_types[expression].kind is (
        ValueTypeKind.UNKNOWN
    )


def test_time_and_interval_are_not_builtins() -> None:
    for type_name in ("Time", "Interval"):
        result = analyze(_parse(_source(type_name, "value")))
        relation = _relation(result)
        field = result.model.relation_row_schemas[relation].fields["value"]

        assert "PIE-S2002" in _error_codes(result)
        assert field.resolved_type.kind is TypeKind.UNKNOWN
        assert field.resolved_type.name == type_name


def test_candidate_field_declarations_emit_pie_s2002_and_unknown_facts() -> None:
    for type_name in TEMPORAL_CANDIDATES:
        result = analyze(_parse(_source(type_name, "value")))
        relation = _relation(result)
        source_schema = next(iter(result.model.source_row_schemas.values()))
        expression = _select_expression(relation, "value")

        assert "PIE-S2002" in _error_codes(result)
        assert source_schema.fields["value"].resolved_type.kind is TypeKind.UNKNOWN
        assert source_schema.fields["value"].resolved_type.name == type_name
        assert result.model.expression_value_types[expression].kind is (
            ValueTypeKind.UNKNOWN
        )


def test_candidate_usage_surfaces_remain_semantic_fail_closed() -> None:
    cases = (
        "value",
        "v = value",
        "same = value == other",
        "before = value < other",
        "c = count(value)",
        "c = count_distinct(value)",
        "c = min(value)",
        "c = max(value)",
        "c = sum(value)",
        "c = avg(value)",
    )

    for type_name in TEMPORAL_CANDIDATES:
        for projection in cases:
            result = analyze(_parse(_source(type_name, projection)))
            relation = _relation(result)
            output_name = projection.split("=", 1)[0].strip()
            field = result.model.relation_row_schemas[relation].fields[output_name]
            source_schema = next(iter(result.model.source_row_schemas.values()))

            assert "PIE-S2002" in _error_codes(result)
            assert source_schema.fields["value"].resolved_type.kind is TypeKind.UNKNOWN
            assert source_schema.fields["value"].resolved_type.name == type_name
            assert not (
                field.resolved_type.kind is TypeKind.BUILTIN
                and field.resolved_type.name in TEMPORAL_CANDIDATES
            )
            if type_name == "DateTime":
                assert field.resolved_type.name != "Timestamp"


def test_order_group_and_satisfying_surfaces_remain_semantic_fail_closed() -> None:
    for type_name in TEMPORAL_CANDIDATES:
        for source in (
            _source_with_order_by(type_name),
            _source_with_group_by(type_name),
            _source_with_satisfying(type_name),
        ):
            result = analyze(_parse(source))

            assert "PIE-S2002" in _error_codes(result)


def test_cli_json_paths_stop_before_temporal_output_expansion(
    tmp_path: Path,
    capsys,
) -> None:
    for command in ("check", "emit-sql", "explain"):
        path = tmp_path / f"{command}-datetime.pietto"
        path.write_text(_source("DateTime", "value"), encoding="utf-8")

        if command == "check":
            argv = ["check", str(path), "--format", "json"]
        elif command == "emit-sql":
            argv = [
                "emit-sql",
                str(path),
                "--dialect",
                "postgres",
                "--format",
                "json",
            ]
        else:
            argv = ["explain", str(path), "--format", "json"]

        assert cli.main(argv) == 1
        output = capsys.readouterr().out
        document = json.loads(output)
        serialized = json.dumps(document, sort_keys=True)

        assert "PIE-S2002" in serialized
        assert "DateTime" in serialized
        assert '"artifacts": []' in serialized or command != "emit-sql"
        for forbidden in (
            "timezone",
            "time_zone",
            "timestamp_precision",
            "duration",
            "interval_units",
            "temporal_native",
            "native_temporal",
        ):
            assert forbidden not in serialized.lower(), forbidden


def test_metadata_and_json_sources_have_no_temporal_schema_expansion() -> None:
    sources = (
        _read(SEMANTIC_MODEL_PATH),
        _read(IR_MODEL_PATH),
        _read(METADATA_MODEL_PATH),
        _read(METADATA_SERIALIZER_PATH),
        _read(METADATA_TEXT_PATH),
        _read(CLI_JSON_PATH),
    )

    for source in sources:
        lowered = source.lower()
        for forbidden in (
            "timezone",
            "time_zone",
            "timestamp_precision",
            "duration",
            "interval_units",
            "temporal_native",
            "native_temporal",
            "native_database_temporal",
        ):
            assert forbidden not in lowered, forbidden


def test_date_timestamp_existing_behavior_is_not_redefined() -> None:
    combined = _phase36_slice6_docs()

    for required in (
        "`Date` and `Timestamp` are current builtins",
        "direct `count(Date field)` and `count(Timestamp field)`",
        "direct `count_distinct(Date field)` and `count_distinct(Timestamp field)`",
        "direct `min(Date field)`, `max(Date field)`, `min(Timestamp field)`, and",
        "`max(Timestamp field)`",
        "generic known-child comparison behavior",
        "Slice 6 does not redefine or expand Date/Timestamp behavior",
    ):
        assert required in combined, required


def test_future_prerequisites_and_non_authorization_are_documented() -> None:
    spec = _normalized(SPEC_PATH)

    for required in (
        "whether `DateTime` is an alias, primitive, or remains unsupported",
        "timezone semantics",
        "timestamp precision semantics",
        "time-of-day semantics",
        "interval/duration units and normalization",
        "temporal arithmetic policy",
        "comparison and ordering policy",
        "group-key and satisfying/result predicate policy",
        "PostgreSQL and private MySQL dialect portability policy",
        "public output compatibility policy for CLI text, JSON v1, Project JSON v2, and Semantic Metadata Artifact v1",
        "does not authorize behavior implementation",
        "does not authorize `DateTime` as a primitive or alias",
        "`Time` as a builtin",
        "`Interval` as a builtin",
        "fixture/golden changes",
        "tags, release, publish/upload, signing, or attestation",
    ):
        assert required in spec, required


def test_forbidden_surfaces_are_not_modified_by_slice6() -> None:
    diff_output = _git_diff_name_only(REPO_ROOT, FORBIDDEN_DIFF_PATHS)

    assert diff_output == ""


def _source(type_name: str, projection: str) -> str:
    return (
        "shape TemporalBoundary:\n"
        f"    value: {type_name} not null\n"
        f"    other: {type_name} nullable\n"
        "    amount: Int not null\n"
        'source events: TemporalBoundary is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    select:\n"
        f"        {projection}\n"
    )


def _source_with_order_by(type_name: str) -> str:
    return (
        "shape TemporalBoundary:\n"
        f"    value: {type_name} not null\n"
        'source events: TemporalBoundary is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    select:\n"
        "        value\n"
        "    order by:\n"
        "        value\n"
    )


def _source_with_group_by(type_name: str) -> str:
    return (
        "shape TemporalBoundary:\n"
        f"    value: {type_name} not null\n"
        'source events: TemporalBoundary is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    group by:\n"
        "        value\n"
        "    select:\n"
        "        value\n"
        "        c = count()\n"
    )


def _source_with_satisfying(type_name: str) -> str:
    return (
        "shape TemporalBoundary:\n"
        f"    value: {type_name} not null\n"
        'source events: TemporalBoundary is postgres.table("events")\n'
        "table projected:\n"
        "    from events\n"
        "    group by:\n"
        "        value\n"
        "    select:\n"
        "        value\n"
        "        c = count()\n"
        "    satisfying:\n"
        "        value == value\n"
    )


def _parse(source: str) -> Script:
    result = parse_source(source)
    assert result.diagnostics == ()
    assert result.ast is not None
    return result.ast


def _relation(result: SemanticResult) -> TableDef | QueryDef:
    relation = next(iter(result.model.relation_row_schemas))
    assert isinstance(relation, (TableDef, QueryDef))
    return relation


def _select_expression(relation: TableDef | QueryDef, alias: str) -> Expression:
    for item in relation.select_items:
        if item.alias == alias:
            return item.expression
        if item.alias is None and getattr(item.expression, "name", None) == alias:
            return item.expression
    raise AssertionError(f"Missing select item: {alias}")


def _error_codes(result: SemanticResult) -> list[str]:
    return [
        diagnostic.code
        for diagnostic in result.diagnostics
        if diagnostic.severity is Severity.ERROR
    ]
